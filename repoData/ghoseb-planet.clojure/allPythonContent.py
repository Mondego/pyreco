__FILENAME__ = admin_cb
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cgi
import cgitb
cgitb.enable()

from urllib import unquote
import sys, os

# Modify this to point to where you usually run planet.
BASE_DIR = '..'

# Modify this to point to your venus installation dir, relative to planet dir above.
VENUS_INSTALL = "venus"

# Config file, relative to planet dir above
CONFIG_FILE = "config/live"

# Admin page URL, relative to this script's URL
ADMIN_URL = "admin.html"


# chdir to planet dir - config may be relative from there
os.chdir(os.path.abspath(BASE_DIR))

# Add venus to path.
sys.path.append(VENUS_INSTALL)

# Add shell dir to path - auto detection does not work
sys.path.append(os.path.join(VENUS_INSTALL, "planet", "shell"))

# import necessary planet items 
from planet import config
from planet.spider import filename


# Load config
config.load(CONFIG_FILE)

# parse query parameters
form = cgi.FieldStorage()


# Start HTML output at once
print "Content-Type: text/html;charset=utf-8"     # HTML is following
print                                             # blank line, end of headers


print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'
print '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="sv"><head><meta http-equiv="Content-Type" content="text/html;charset=utf-8" /><title>Admin results</title></head><body>'
print '<div>'

# Cache and blacklist dirs

cache = config.cache_directory()
blacklist = config.cache_blacklist_directory()

# Must have command parameter
if not "command" in form:
  print "<p>Unknown command</p>"

elif form['command'].value == "blacklist":


  # Create the blacklist dir if it does not exist
  if not os.path.exists(blacklist):
    os.mkdir(blacklist)
    print "<p>Created directory %s</p>" % blacklist
  
  # find list of urls, in the form bl[n]=url

  for key in form.keys():

    if not key.startswith("bl"): continue

    url = unquote(form[key].value)

    # find corresponding files
    cache_file = filename(cache, url)
    blacklist_file = filename(blacklist, url)

    # move to blacklist if found
    if os.path.exists(cache_file):

      os.rename(cache_file, blacklist_file)

      print "<p>Blacklisted <a href='%s'>%s</a></p>" % (url, url)

    else:

      print "<p>Unknown file: %s</p>" % cache_file

    print """
<p>Note that blacklisting does not automatically 
refresh the planet. You will need to either wait for
a scheduled planet run, or refresh manually from the admin interface.</p>
"""


elif form['command'].value == "run":

  # run spider and refresh

  from planet import spider, splice
  try:
     spider.spiderPlanet(only_if_new=False)
     print "<p>Successfully ran spider</p>"
  except Exception, e:
     print e

  doc = splice.splice()
  splice.apply(doc.toxml('utf-8'))

elif form['command'].value == "refresh":

  # only refresh

  from planet import splice

  doc = splice.splice()
  splice.apply(doc.toxml('utf-8'))

  print "<p>Successfully refreshed</p>"

elif form['command'].value == "expunge":

  # only expunge
  from planet import expunge
  expunge.expungeCache()

  print "<p>Successfully expunged</p>"




print "<p><strong><a href='" + ADMIN_URL + "'>Return</a> to admin interface</strong></p>"



print "</body></html>"

########NEW FILE########
__FILENAME__ = guess-language
#!/usr/bin/env python
"""A filter to guess languages.

This filter guesses whether an Atom entry is written
in English or French. It should be trivial to chose between
two other languages, easy to extend to more than two languages
and useful to pass these languages as Venus configuration
parameters.

(See the REAME file for more details).

Requires Python 2.1, recommends 2.4.
"""
__authors__ = [ "Eric van der Vlist <vdv@dyomedea.com>"]
__license__ = "Python"

import amara
from sys import stdin, stdout
from trigram import Trigram
from xml.dom import XML_NAMESPACE as XML_NS
import cPickle

ATOM_NSS = {
    u'atom': u'http://www.w3.org/2005/Atom',
    u'xml': XML_NS
}

langs = {}

def tri(lang):
    if not langs.has_key(lang):
	f = open('filters/guess-language/%s.data' % lang, 'r')
	t = cPickle.load(f)
	f.close()
	langs[lang] = t
    return langs[lang]
    

def guess_language(entry):
    text = u'';
    for child in entry.xml_xpath(u'atom:title|atom:summary|atom:content'):
	text = text + u' '+ child.__unicode__()
    t = Trigram()
    t.parseString(text)
    if tri('fr') - t > tri('en') - t:
	lang=u'en'
    else:
	lang=u'fr'
    entry.xml_set_attribute((u'xml:lang', XML_NS), lang)

def main():
    feed = amara.parse(stdin, prefixes=ATOM_NSS)
    for entry in feed.xml_xpath(u'//atom:entry[not(@xml:lang)]'):
	guess_language(entry)
    feed.xml(stdout)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = learn-language
#!/usr/bin/env python
"""A filter to guess languages.

This utility saves a Trigram object on file.

(See the REAME file for more details).

Requires Python 2.1, recommends 2.4.
"""
__authors__ = [ "Eric van der Vlist <vdv@dyomedea.com>"]
__license__ = "Python"

from trigram import Trigram
from sys import argv
from cPickle import dump


def main():
    tri = Trigram(argv[1])
    out = open(argv[2], 'w')
    dump(tri, out)
    out.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = trigram
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
    This class is based on the Python recipe titled
    "Language detection using character trigrams"
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/326576
    by Douglas Bagnall.
    It has been (slightly) adapted by Eric van der Vlist to support
    Unicode and accept a method to parse strings.
"""
__authors__ = [ "Douglas Bagnall", "Eric van der Vlist <vdv@dyomedea.com>"]
__license__ = "Python"

import random
from urllib import urlopen

class Trigram:
    """
    From one or more text files, the frequency of three character
    sequences is calculated.  When treated as a vector, this information
    can be compared to other trigrams, and the difference between them
    seen as an angle.  The cosine of this angle varies between 1 for
    complete similarity, and 0 for utter difference.  Since letter
    combinations are characteristic to a language, this can be used to
    determine the language of a body of text. For example:

        >>> reference_en = Trigram('/path/to/reference/text/english')
        >>> reference_de = Trigram('/path/to/reference/text/german')
        >>> unknown = Trigram('url://pointing/to/unknown/text')
        >>> unknown.similarity(reference_de)
        0.4
        >>> unknown.similarity(reference_en)
        0.95

    would indicate the unknown text is almost cetrtainly English.  As
    syntax sugar, the minus sign is overloaded to return the difference
    between texts, so the above objects would give you:

        >>> unknown - reference_de
        0.6
        >>> reference_en - unknown    # order doesn't matter.
        0.05

    As it stands, the Trigram ignores character set information, which
    means you can only accurately compare within a single encoding
    (iso-8859-1 in the examples).  A more complete implementation might
    convert to unicode first.

    As an extra bonus, there is a method to make up nonsense words in the
    style of the Trigram's text.

        >>> reference_en.makeWords(30)
        My withillonquiver and ald, by now wittlectionsurper, may sequia,
        tory, I ad my notter. Marriusbabilly She lady for rachalle spen
        hat knong al elf

    Beware when using urls: HTML won't be parsed out.

    Most methods chatter away to standard output, to let you know they're
    still there.
    """

    length = 0

    def __init__(self, fn=None):
        self.lut = {}
        if fn is not None:
            self.parseFile(fn)

    def _parseAFragment(self, line, pair='  '):
	for letter in line:
	    d = self.lut.setdefault(pair, {})
            d[letter] = d.get(letter, 0) + 1
            pair = pair[1] + letter
	return pair

    def parseString(self, string):
	self._parseAFragment(string)
        self.measure()
    
    def parseFile(self, fn, encoding="iso-8859-1"):
        pair = '  '
        if '://' in fn:
            #print "trying to fetch url, may take time..."
            f = urlopen(fn)
        else:
            f = open(fn)
        for z, line in enumerate(f):
            #if not z % 1000:
            #    print "line %s" % z
            # \n's are spurious in a prose context
            pair = self._parseAFragment(line.strip().decode(encoding) + ' ')
        f.close()
        self.measure()


    def measure(self):
        """calculates the scalar length of the trigram vector and
        stores it in self.length."""
        total = 0
        for y in self.lut.values():
            total += sum([ x * x for x in y.values() ])
        self.length = total ** 0.5

    def similarity(self, other):
        """returns a number between 0 and 1 indicating similarity.
        1 means an identical ratio of trigrams;
        0 means no trigrams in common.
        """
        if not isinstance(other, Trigram):
            raise TypeError("can't compare Trigram with non-Trigram")
        lut1 = self.lut
        lut2 = other.lut
        total = 0
        for k in lut1.keys():
            if k in lut2:
                a = lut1[k]
                b = lut2[k]
                for x in a:
                    if x in b:
                        total += a[x] * b[x]

        return float(total) / (self.length * other.length)

    def __sub__(self, other):
        """indicates difference between trigram sets; 1 is entirely
        different, 0 is entirely the same."""
        return 1 - self.similarity(other)


    def makeWords(self, count):
        """returns a string of made-up words based on the known text."""
        text = []
        k = '  '
        while count:
            n = self.likely(k)
            text.append(n)
            k = k[1] + n
            if n in ' \t':
                count -= 1
        return ''.join(text)


    def likely(self, k):
        """Returns a character likely to follow the given string
        two character string, or a space if nothing is found."""
        if k not in self.lut:
            return ' '
        # if you were using this a lot, caching would a good idea.
        letters = []
        for k, v in self.lut[k].items():
            letters.append(k * v)
        letters = ''.join(letters)
        return random.choice(letters)


def test():
    en = Trigram('http://gutenberg.net/dirs/etext97/lsusn11.txt')
   #NB fr and some others have English license text.
    #   no has english excerpts.
    fr = Trigram('http://gutenberg.net/dirs/etext03/candi10.txt')
    fi = Trigram('http://gutenberg.net/dirs/1/0/4/9/10492/10492-8.txt')
    no = Trigram('http://gutenberg.net/dirs/1/2/8/4/12844/12844-8.txt')
    se = Trigram('http://gutenberg.net/dirs/1/0/1/1/10117/10117-8.txt')
    no2 = Trigram('http://gutenberg.net/dirs/1/3/0/4/13041/13041-8.txt')
    en2 = Trigram('http://gutenberg.net/dirs/etext05/cfgsh10.txt')
    fr2 = Trigram('http://gutenberg.net/dirs/1/3/7/0/13704/13704-8.txt')
    print "calculating difference:"
    print "en - fr is %s" % (en - fr)
    print "fr - en is %s" % (fr - en)
    print "en - en2 is %s" % (en - en2)
    print "en - fr2 is %s" % (en - fr2)
    print "fr - en2 is %s" % (fr - en2)
    print "fr - fr2 is %s" % (fr - fr2)
    print "fr2 - en2 is %s" % (fr2 - en2)
    print "fi - fr  is %s" % (fi - fr)
    print "fi - en  is %s" % (fi - en)
    print "fi - se  is %s" % (fi - se)
    print "no - se  is %s" % (no - se)
    print "en - no  is %s" % (en - no)
    print "no - no2  is %s" % (no - no2)
    print "se - no2  is %s" % (se - no2)
    print "en - no2  is %s" % (en - no2)
    print "fr - no2  is %s" % (fr - no2)


if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = expunge
#!/usr/bin/env python
"""
Main program to run just the expunge portion of planet
"""

import os.path
import sys
from planet import expunge, config

if __name__ == '__main__':

    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        config.load(sys.argv[1])
        expunge.expungeCache()
    else:
        print "Usage:"
        print "  python %s config.ini" % sys.argv[0]

########NEW FILE########
__FILENAME__ = coral_cdn_filter
"""
Remap all images to take advantage of the Coral Content Distribution
Network <http://www.coralcdn.org/>.
"""

import re, sys, urlparse, xml.dom.minidom

entry = xml.dom.minidom.parse(sys.stdin).documentElement

for node in entry.getElementsByTagName('img'):
    if node.hasAttribute('src'):
        component = list(urlparse.urlparse(node.getAttribute('src')))
        if component[0] == 'http':
            component[1] = re.sub(r':(\d+)$', r'.\1', component[1])
            component[1] += '.nyud.net:8080'
            node.setAttribute('src', urlparse.urlunparse(component))

print entry.toxml('utf-8')

########NEW FILE########
__FILENAME__ = excerpt
"""
Generate an excerpt from either the summary or a content of an entry.

Parameters:
  width:  maximum number of characters in the excerpt.  Default: 500
  omit:   whitespace delimited list of html tags to remove.  Default: none
  target: name of element created.  Default: planet:excerpt

Notes:
 * if 'img' is in the list of tags to be omitted <img> tags are replaced with
   hypertext links associated with the value of the 'alt' attribute.  If there
   is no alt attribute value, <img> is used instead.  If the parent element
   of the img tag is already an <a> tag, no additional hypertext links are
   added.
"""

import sys, xml.dom.minidom, textwrap
from xml.dom import Node, minidom

atomNS = 'http://www.w3.org/2005/Atom'
planetNS = 'http://planet.intertwingly.net/'

args = dict(zip([name.lstrip('-') for name in sys.argv[1::2]], sys.argv[2::2]))

wrapper = textwrap.TextWrapper(width=int(args.get('width','500')))
omit = args.get('omit', '').split()
target = args.get('target', 'planet:excerpt')

class copy:
    """ recursively copy a source to a target, up to a given width """

    def __init__(self, dom, source, target):
        self.dom = dom
        self.full = False
        self.text = []
        self.textlen = 0
        self.copyChildren(source, target)

    def copyChildren(self, source, target):
        """ copy child nodes of a source to the target """
        for child in source.childNodes:
            if child.nodeType == Node.ELEMENT_NODE:
                 self.copyElement(child, target)
            elif child.nodeType == Node.TEXT_NODE:
                 self.copyText(child.data, target)
            if self.full: break

    def copyElement(self, source, target):
        """ copy source element to the target """

        # check the omit list
        if source.nodeName in omit:
            if source.nodeName == 'img':
               return self.elideImage(source, target)
            return self.copyChildren(source, target)

        # copy element, attributes, and children
        child = self.dom.createElementNS(source.namespaceURI, source.nodeName)
        target.appendChild(child)
        for i in range(0, source.attributes.length):
            attr = source.attributes.item(i)
            child.setAttributeNS(attr.namespaceURI, attr.name, attr.value)
        self.copyChildren(source, child)

    def elideImage(self, source, target):
        """ copy an elided form of the image element to the target """
        alt = source.getAttribute('alt') or '<img>'
        src = source.getAttribute('src')

        if target.nodeName == 'a' or not src:
            self.copyText(alt, target)
        else:
            child = self.dom.createElement('a')
            child.setAttribute('href', src)
            self.copyText(alt, child)
            target.appendChild(child)

    def copyText(self, source, target):
        """ copy text to the target, until the point where it would wrap """
        if not source.isspace() and source.strip():
            self.text.append(source.strip())
        lines = wrapper.wrap(' '.join(self.text))
        if len(lines) == 1:
            target.appendChild(self.dom.createTextNode(source))
            self.textlen = len(lines[0])
        elif lines:
            excerpt = source[:len(lines[0])-self.textlen] + u' \u2026'
            target.appendChild(dom.createTextNode(excerpt))
            self.full = True

# select summary or content element
dom = minidom.parse(sys.stdin)
source = dom.getElementsByTagNameNS(atomNS, 'summary')
if not source:
    source = dom.getElementsByTagNameNS(atomNS, 'content')

# if present, recursively copy it to a planet:excerpt element
if source:
    if target.startswith('planet:'):
        dom.documentElement.setAttribute('xmlns:planet', planetNS)
    if target.startswith('atom:'): target = target.split(':',1)[1]
    excerpt = dom.createElementNS(planetNS, target)
    source[0].parentNode.appendChild(excerpt)
    copy(dom, source[0], excerpt)
    if source[0].nodeName == excerpt.nodeName:
        source[0].parentNode.removeChild(source[0])

# print out results
print dom.toxml('utf-8')

########NEW FILE########
__FILENAME__ = minhead
#
# Ensure that all headings are below a permissible maximum (like h3).
# If not, all heading levels will be changed to conform.
# Note: this may create "illegal" heading levels, like h7 and beyond.
#

import sys
from xml.dom import minidom, XHTML_NAMESPACE

# determine permissible minimimum heading
if '--min' in sys.argv:
  minhead = int(sys.argv[sys.argv.index('--min')+1])
else:
  minhead=3

# parse input stream
doc = minidom.parse(sys.stdin)

# search for headings below the permissable minimum
first=minhead
for i in range(1,minhead):
  if doc.getElementsByTagName('h%d' % i):
    first=i
    break

# if found, bump all headings so that the top is the permissible minimum
if first < minhead:
  for i in range(6,0,-1):
    for oldhead in doc.getElementsByTagName('h%d' % i):
      newhead = doc.createElementNS(XHTML_NAMESPACE, 'h%d' % (i+minhead-first))
      for child in oldhead.childNodes[:]:
        newhead.appendChild(child)
      oldhead.parentNode.replaceChild(newhead, oldhead)

# return (possibly modified) document
print doc.toxml('utf-8')

########NEW FILE########
__FILENAME__ = nopipeerrors
#remove all entries with Yahoo! Pipes error
import sys

data = sys.stdin.read()
if data.find('No such pipe, or this pipe has been deleted') < 0:
  sys.stdout.write(data)

########NEW FILE########
__FILENAME__ = notweets
#remove all tweets
import sys

data = sys.stdin.read()
if data.find('<id>tag:twitter.com,') < 0:
  sys.stdout.write(data)

########NEW FILE########
__FILENAME__ = regexp_sifter
import sys, re

# parse options
options = dict(zip(sys.argv[1::2],sys.argv[2::2]))

# read entry
doc = data = sys.stdin.read()

# Apply a sequence of patterns which turn a normalized Atom entry into
# a stream of text, after removal of non-human metadata.
for pattern,replacement in [
  (re.compile('<id>.*?</id>'),' '),
  (re.compile('<url>.*?</url>'),' '),
  (re.compile('<source>.*?</source>'),' '),
  (re.compile('<updated.*?</updated>'),' '),
  (re.compile('<published.*?</published>'),' '),
  (re.compile('<link .*?>'),' '),
  (re.compile('''<[^>]* alt=['"]([^'"]*)['"].*?>'''),r' \1 '),
  (re.compile('''<[^>]* title=['"]([^'"]*)['"].*?>'''),r' \1 '),
  (re.compile('''<[^>]* label=['"]([^'"]*)['"].*?>'''),r' \1 '),
  (re.compile('''<[^>]* term=['"]([^'"]*)['"].*?>'''),r' \1 '),
  (re.compile('<.*?>'),' '),
  (re.compile('\s+'),' '),
  (re.compile('&gt;'),'>'),
  (re.compile('&lt;'),'<'),
  (re.compile('&apos;'),"'"),
  (re.compile('&quot;'),'"'),
  (re.compile('&amp;'),'&'),
  (re.compile('\s+'),' ')
]:
  data=pattern.sub(replacement,data)

# process requirements
if options.has_key('--require'):
  for regexp in options['--require'].split('\n'):
     if regexp and not re.search(regexp,data): sys.exit(1)

# process exclusions
if options.has_key('--exclude'):
  for regexp in options['--exclude'].split('\n'):
     if regexp and re.search(regexp,data): sys.exit(1)

# if we get this far, the feed is to be included
print doc

########NEW FILE########
__FILENAME__ = xpath_sifter
import sys, libxml2

# parse options
options = dict(zip(sys.argv[1::2],sys.argv[2::2]))

# parse entry
doc = libxml2.parseDoc(sys.stdin.read())
ctxt = doc.xpathNewContext()
ctxt.xpathRegisterNs('atom','http://www.w3.org/2005/Atom')
ctxt.xpathRegisterNs('xhtml','http://www.w3.org/1999/xhtml')

# process requirements
if options.has_key('--require'):
  for xpath in options['--require'].split('\n'):
     if xpath and not ctxt.xpathEval(xpath): sys.exit(1)

# process exclusions
if options.has_key('--exclude'):
  for xpath in options['--exclude'].split('\n'):
     if xpath and ctxt.xpathEval(xpath): sys.exit(1)

# if we get this far, the feed is to be included
print doc

########NEW FILE########
__FILENAME__ = config
"""
Planet Configuration

This module encapsulates all planet configuration.  This is not a generic
configuration parser, it knows everything about configuring a planet - from
the structure of the ini file, to knowledge of data types, even down to
what are the defaults.

Usage:
  import config
  config.load('config.ini')

  # administrative / structural information
  print config.template_files()
  print config.subscriptions()

  # planet wide configuration
  print config.name()
  print config.link()

  # per template configuration
  print config.days_per_page('atom.xml.tmpl')
  print config.encoding('index.html.tmpl')

Todo:
  * error handling (example: no planet section)
"""

import os, sys, re, urllib
from ConfigParser import ConfigParser
from urlparse import urljoin

parser = ConfigParser()

planet_predefined_options = ['filters']

def __init__():
    """define the struture of an ini file"""
    import config

    # get an option from a section
    def get(section, option, default):
        if section and parser.has_option(section, option):
            return parser.get(section, option)
        elif parser.has_option('Planet', option):
            if option == 'log_format':
                return parser.get('Planet', option, raw=True)
            return parser.get('Planet', option)
        else:
            return default

    # expand %(var) in lists
    def expand(list):
        output = []
        wild = re.compile('^(.*)#{(\w+)}(.*)$')
        for file in list.split():
            match = wild.match(file)
            if match:
                pre,var,post = match.groups()
                for sub in subscriptions():
                    value = feed_options(sub).get(var,None)
                    if value:
                        output.append(pre+value+post)
            else:
                output.append(file)
        return output

    # define a string planet-level variable
    def define_planet(name, default):
        setattr(config, name, lambda default=default: get(None,name,default))
        planet_predefined_options.append(name)

    # define a list planet-level variable
    def define_planet_int(name, default=0):
        setattr(config, name, lambda : int(get(None,name,default)))
        planet_predefined_options.append(name)

    # define a list planet-level variable
    def define_planet_list(name, default=''):
        setattr(config, name, lambda : expand(get(None,name,default)))
        planet_predefined_options.append(name)

    # define a string template-level variable
    def define_tmpl(name, default):
        setattr(config, name, lambda section, default=default:
            get(section,name,default))

    # define an int template-level variable
    def define_tmpl_int(name, default):
        setattr(config, name, lambda section, default=default:
            int(get(section,name,default)))

    # planet wide options
    define_planet('name', "Unconfigured Planet")
    define_planet('link', '')
    define_planet('cache_directory', "cache")
    define_planet('log_level', "WARNING")
    define_planet('log_format', "%(levelname)s:%(name)s:%(message)s")
    define_planet('date_format', "%B %d, %Y %I:%M %p")
    define_planet('new_date_format', "%B %d, %Y")
    define_planet('generator', 'Venus')
    define_planet('generator_uri', 'http://intertwingly.net/code/venus/')
    define_planet('owner_name', 'Anonymous Coward')
    define_planet('owner_email', '')
    define_planet('output_theme', '')
    define_planet('output_dir', 'output')
    define_planet('spider_threads', 0) 
    define_planet('pubsubhubbub_hub', '')
    define_planet_list('pubsubhubbub_feeds', 'atom.xml rss10.xml rss20.xml')

    define_planet_int('new_feed_items', 0) 
    define_planet_int('feed_timeout', 20)
    define_planet_int('cache_keep_entries', 10)

    define_planet_list('template_files')
    define_planet_list('bill_of_materials')
    define_planet_list('template_directories', '.')
    define_planet_list('filter_directories')

    # template options
    define_tmpl_int('days_per_page', 0)
    define_tmpl_int('items_per_page', 60)
    define_tmpl_int('activity_threshold', 0)
    define_tmpl('encoding', 'utf-8')
    define_tmpl('content_type', 'utf-8')
    define_tmpl('ignore_in_feed', '')
    define_tmpl('name_type', '')
    define_tmpl('title_type', '')
    define_tmpl('summary_type', '')
    define_tmpl('content_type', '')
    define_tmpl('future_dates', 'keep')
    define_tmpl('xml_base', '')
    define_tmpl('filter', None) 
    define_tmpl('exclude', None) 

def load(config_file):
    """ initialize and load a configuration"""
    global parser
    parser = ConfigParser()
    parser.read(config_file)

    import config, planet
    from planet import opml, foaf, csv_config
    log = planet.logger
    if not log:
        log = planet.getLogger(config.log_level(),config.log_format())

    # Theme support
    theme = config.output_theme()
    if theme:
        for path in ("", os.path.join(sys.path[0],'themes')):
            theme_dir = os.path.join(path,theme)
            theme_file = os.path.join(theme_dir,'config.ini')
            if os.path.exists(theme_file):
                # initial search list for theme directories
                dirs = config.template_directories()
                if theme_dir not in dirs:
                    dirs.append(theme_dir)
                if os.path.dirname(config_file) not in dirs:
                    dirs.append(os.path.dirname(config_file))

                # read in the theme
                parser = ConfigParser()
                parser.read(theme_file)
                bom = config.bill_of_materials()

                # complete search list for theme directories
                dirs += [os.path.join(theme_dir,dir) for dir in 
                    config.template_directories() if dir not in dirs]

                # merge configurations, allowing current one to override theme
                template_files = config.template_files()
                parser.set('Planet','template_files','')
                parser.read(config_file)
                for file in config.bill_of_materials():
                    if not file in bom: bom.append(file)
                parser.set('Planet', 'bill_of_materials', ' '.join(bom))
                parser.set('Planet', 'template_directories', ' '.join(dirs))
                parser.set('Planet', 'template_files',
                   ' '.join(template_files + config.template_files()))
                break
        else:
            log.error('Unable to find theme %s', theme)

    # Filter support
    dirs = config.filter_directories()
    filter_dir = os.path.join(sys.path[0],'filters')
    if filter_dir not in dirs and os.path.exists(filter_dir):
        parser.set('Planet', 'filter_directories', ' '.join(dirs+[filter_dir]))

    # Reading list support
    reading_lists = config.reading_lists()
    if reading_lists:
        if not os.path.exists(config.cache_lists_directory()):
            os.makedirs(config.cache_lists_directory())

        def data2config(data, cached_config):
            if content_type(list).find('opml')>=0:
                opml.opml2config(data, cached_config)
            elif content_type(list).find('foaf')>=0:
                foaf.foaf2config(data, cached_config)
            elif content_type(list).find('csv')>=0:
                csv_config.csv2config(data, cached_config)
            elif content_type(list).find('config')>=0:
                cached_config.readfp(data)
            else:
                from planet import shell
                import StringIO
                cached_config.readfp(StringIO.StringIO(shell.run(
                    content_type(list), data.getvalue(), mode="filter")))

            if cached_config.sections() in [[], [list]]: 
                raise Exception

        for list in reading_lists:
            downloadReadingList(list, parser, data2config)

def downloadReadingList(list, orig_config, callback, use_cache=True, re_read=True):
    from planet import logger
    import config
    try:

        import urllib2, StringIO
        from planet.spider import filename

        # list cache file name
        cache_filename = filename(config.cache_lists_directory(), list)

        # retrieve list options (e.g., etag, last-modified) from cache
        options = {}

        # add original options
        for key in orig_config.options(list):
            options[key] = orig_config.get(list, key)
            
        try:
            if use_cache:
                cached_config = ConfigParser()
                cached_config.read(cache_filename)
                for option in cached_config.options(list):
                     options[option] = cached_config.get(list,option)
        except:
            pass

        cached_config = ConfigParser()
        cached_config.add_section(list)
        for key, value in options.items():
            cached_config.set(list, key, value)

        # read list
        curdir=getattr(os.path, 'curdir', '.')
        if sys.platform.find('win') < 0:
            base = urljoin('file:', os.path.abspath(curdir))
        else:
            path = os.path.abspath(os.path.curdir)
            base = urljoin('file:///', path.replace(':','|').replace('\\','/'))

        request = urllib2.Request(urljoin(base + '/', list))
        if options.has_key("etag"):
            request.add_header('If-None-Match', options['etag'])
        if options.has_key("last-modified"):
            request.add_header('If-Modified-Since',
                options['last-modified'])
        response = urllib2.urlopen(request)
        if response.headers.has_key('etag'):
            cached_config.set(list, 'etag', response.headers['etag'])
        if response.headers.has_key('last-modified'):
            cached_config.set(list, 'last-modified',
                response.headers['last-modified'])

        # convert to config.ini
        data = StringIO.StringIO(response.read())

        if callback: callback(data, cached_config)

        # write to cache
        if use_cache:
            cache = open(cache_filename, 'w')
            cached_config.write(cache)
            cache.close()

        # re-parse and proceed
        logger.debug("Using %s readinglist", list) 
        if re_read:
            if use_cache:  
                orig_config.read(cache_filename)
            else:
                cdata = StringIO.StringIO()
                cached_config.write(cdata)
                cdata.seek(0)
                orig_config.readfp(cdata)
    except:
        try:
            if re_read:
                if use_cache:  
                    if not orig_config.read(cache_filename): raise Exception()
                else:
                    cdata = StringIO.StringIO()
                    cached_config.write(cdata)
                    cdata.seek(0)
                    orig_config.readfp(cdata)
                logger.info("Using cached %s readinglist", list)
        except:
            logger.exception("Unable to read %s readinglist", list)

def http_cache_directory():
    if parser.has_option('Planet', 'http_cache_directory'):
        return os.path.join(cache_directory(), 
            parser.get('Planet', 'http_cache_directory'))
    else:
        return os.path.join(cache_directory(), "cache")

def cache_sources_directory():
    if parser.has_option('Planet', 'cache_sources_directory'):
        return os.path.join(cache_directory(),
            parser.get('Planet', 'cache_sources_directory'))
    else:
        return os.path.join(cache_directory(), 'sources')

def cache_blacklist_directory():
    if parser.has_option('Planet', 'cache_blacklist_directory'):
        return os.path.join(cache_directory(),
            parser.get('Planet', 'cache_blacklist_directory'))
    else:
        return os.path.join(cache_directory(), 'blacklist')

def cache_lists_directory():
    if parser.has_option('Planet', 'cache_lists_directory'):
        return parser.get('Planet', 'cache_lists_directory')
    else:
        return os.path.join(cache_directory(), 'lists')

def feed():
    if parser.has_option('Planet', 'feed'):
        return parser.get('Planet', 'feed')
    elif link():
        for template_file in template_files():
            name = os.path.splitext(os.path.basename(template_file))[0]
            if name.find('atom')>=0 or name.find('rss')>=0:
                return urljoin(link(), name)

def feedtype():
    if parser.has_option('Planet', 'feedtype'):
        return parser.get('Planet', 'feedtype')
    elif feed() and feed().find('atom')>=0:
        return 'atom'
    elif feed() and feed().find('rss')>=0:
        return 'rss'

def subscriptions():
    """ list the feed subscriptions """
    return __builtins__['filter'](lambda feed: feed!='Planet' and 
        feed not in template_files()+filters()+reading_lists(),
        parser.sections())

def reading_lists():
    """ list of lists of feed subscriptions """
    result = []
    for section in parser.sections():
        if parser.has_option(section, 'content_type'):
            type = parser.get(section, 'content_type')
            if type.find('opml')>=0 or type.find('foaf')>=0 or \
               type.find('csv')>=0 or type.find('config')>=0 or \
               type.find('.')>=0:
                result.append(section)
    return result

def filters(section=None):
    filters = []
    if parser.has_option('Planet', 'filters'):
        filters += parser.get('Planet', 'filters').split()
    if filter(section):
        filters.append('regexp_sifter.py?require=' +
            urllib.quote(filter(section)))
    if exclude(section):
        filters.append('regexp_sifter.py?exclude=' +
            urllib.quote(exclude(section)))
    for section in section and [section] or template_files():
        if parser.has_option(section, 'filters'):
            filters += parser.get(section, 'filters').split()
    return filters

def planet_options():
    """ dictionary of planet wide options"""
    return dict(map(lambda opt: (opt,
        parser.get('Planet', opt, raw=(opt=="log_format"))),
        parser.options('Planet')))

def feed_options(section):
    """ dictionary of feed specific options"""
    import config
    options = dict([(key,value) for key,value in planet_options().items()
        if key not in planet_predefined_options])
    if parser.has_section(section):
        options.update(dict(map(lambda opt: (opt, parser.get(section,opt)),
            parser.options(section))))
    return options

def template_options(section):
    """ dictionary of template specific options"""
    return feed_options(section)

def filter_options(section):
    """ dictionary of filter specific options"""
    return feed_options(section)

def write(file=sys.stdout):
    """ write out an updated template """
    print parser.write(file)

########NEW FILE########
__FILENAME__ = csv_config
from ConfigParser import ConfigParser
import csv

# input = csv, output = ConfigParser
def csv2config(input, config=None):

    if not hasattr(input, 'read'):
        input = csv.StringIO(input)

    if not config:
        config = ConfigParser()

    reader = csv.DictReader(input)
    for row in reader:
        section = row[reader.fieldnames[0]]
        config.add_section(section)
        for name, value in row.items():
            if value and name != reader.fieldnames[0]:
                config.set(section, name, value) 

    return config

if __name__ == "__main__":
    # small main program which converts CSV into config.ini format
    import sys, urllib
    config = ConfigParser()
    for input in sys.argv[1:]:
        csv2config(urllib.urlopen(input), config)
    config.write(sys.stdout)

########NEW FILE########
__FILENAME__ = expunge
""" Expunge old entries from a cache of entries """
import glob, os, planet, config, feedparser
from xml.dom import minidom
from spider import filename

def expungeCache():
    """ Expunge old entries from a cache of entries """
    log = planet.logger

    log.info("Determining feed subscriptions")
    entry_count = {}
    sources = config.cache_sources_directory()
    for sub in config.subscriptions():
        data=feedparser.parse(filename(sources,sub))
        if not data.feed.has_key('id'): continue
        if config.feed_options(sub).has_key('cache_keep_entries'):
            entry_count[data.feed.id] = int(config.feed_options(sub)['cache_keep_entries'])
        else:
            entry_count[data.feed.id] = config.cache_keep_entries()

    log.info("Listing cached entries")
    cache = config.cache_directory()
    dir=[(os.stat(file).st_mtime,file) for file in glob.glob(cache+"/*")
        if not os.path.isdir(file)]
    dir.sort()
    dir.reverse()

    for mtime,file in dir:

        try:
            entry=minidom.parse(file)
            # determine source of entry
            entry.normalize()
            sources = entry.getElementsByTagName('source')
            if not sources:
                # no source determined, do not delete
                log.debug("No source found for %s", file)
                continue
            ids = sources[0].getElementsByTagName('id')
            if not ids:
                # feed id not found, do not delete
                log.debug("No source feed id found for %s", file)
                continue
            if ids[0].childNodes[0].nodeValue in entry_count:
                # subscribed to feed, update entry count
                entry_count[ids[0].childNodes[0].nodeValue] = entry_count[
                    ids[0].childNodes[0].nodeValue] - 1
                if entry_count[ids[0].childNodes[0].nodeValue] >= 0:
                    # maximum not reached, do not delete
                    log.debug("Maximum not reached for %s from %s",
                        file, ids[0].childNodes[0].nodeValue)
                    continue
                else:
                    # maximum reached
                    log.debug("Removing %s, maximum reached for %s",
                        file, ids[0].childNodes[0].nodeValue)
            else:
                # not subscribed
                log.debug("Removing %s, not subscribed to %s",
                    file, ids[0].childNodes[0].nodeValue)
            # remove old entry
            os.unlink(file)

        except:
            log.error("Error parsing %s", file)

# end of expungeCache()

########NEW FILE########
__FILENAME__ = foaf
from ConfigParser import ConfigParser

inheritable_options = [ 'online_accounts' ]

def load_accounts(config, section):
    accounts = {}
    if(config.has_option(section, 'online_accounts')):
        values = config.get(section, 'online_accounts')
        for account_map in values.split('\n'):
            try:
                homepage, map = account_map.split('|')
                accounts[homepage] = map
            except:
                pass

    return accounts

def load_model(rdf, base_uri):

    if hasattr(rdf, 'find_statements'):
        return rdf

    if hasattr(rdf, 'read'):
        rdf = rdf.read()

    def handler(code, level, facility, message, line, column, byte, file, uri):
        pass

    from RDF import Model, Parser

    model = Model()

    Parser().parse_string_into_model(model,rdf,base_uri,handler)

    return model

# input = foaf, output = ConfigParser
def foaf2config(rdf, config, subject=None, section=None):

    if not config or not config.sections():
        return

    # there should be only be 1 section
    if not section: section = config.sections().pop()

    try:
        from RDF import Model, NS, Parser, Statement
    except:
        return

    # account mappings, none by default
    # form: accounts = {url to service homepage (as found in FOAF)}|{URI template}\n*
    # example: http://del.icio.us/|http://del.icio.us/rss/{foaf:accountName}
    accounts = load_accounts(config, section)

    depth = 0

    if(config.has_option(section, 'depth')):
        depth = config.getint(section, 'depth')

    model = load_model(rdf, section)

    dc   = NS('http://purl.org/dc/elements/1.1/')
    foaf = NS('http://xmlns.com/foaf/0.1/')
    rdfs = NS('http://www.w3.org/2000/01/rdf-schema#')
    rdf = NS('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
    rss = NS('http://purl.org/rss/1.0/')

    for statement in model.find_statements(Statement(subject,foaf.weblog,None)):

        # feed owner
        person = statement.subject

        # title is required (at the moment)
        title = model.get_target(person,foaf.name)
        if not title: title = model.get_target(statement.object,dc.title)
        if not title: 
            continue

        # blog is optional
        feed = model.get_target(statement.object,rdfs.seeAlso)
        if feed and rss.channel == model.get_target(feed, rdf.type):
            feed = str(feed.uri)
            if not config.has_section(feed):
                config.add_section(feed)
                config.set(feed, 'name', str(title))

        # now look for OnlineAccounts for the same person
        if accounts.keys():
            for statement in model.find_statements(Statement(person,foaf.holdsAccount,None)):
                rdfaccthome = model.get_target(statement.object,foaf.accountServiceHomepage)
                rdfacctname = model.get_target(statement.object,foaf.accountName)

                if not rdfaccthome or not rdfacctname: continue

                if not rdfaccthome.is_resource() or not accounts.has_key(str(rdfaccthome.uri)): continue

                if not rdfacctname.is_literal(): continue

                rdfacctname = rdfacctname.literal_value['string']
                rdfaccthome = str(rdfaccthome.uri)

                # shorten feed title a bit
                try:
                    servicetitle = rdfaccthome.replace('http://','').split('/')[0]
                except:
                    servicetitle = rdfaccthome

                feed = accounts[rdfaccthome].replace("{foaf:accountName}", rdfacctname)
                if not config.has_section(feed):
                    config.add_section(feed)
                    config.set(feed, 'name', "%s (%s)" % (title, servicetitle))

        if depth > 0:

            # now the fun part, let's go after more friends
            for statement in model.find_statements(Statement(person,foaf.knows,None)):
                friend = statement.object

                # let's be safe
                if friend.is_literal(): continue
                
                seeAlso = model.get_target(friend,rdfs.seeAlso)

                # nothing to see
                if not seeAlso or not seeAlso.is_resource(): continue

                seeAlso = str(seeAlso.uri)

                if not config.has_section(seeAlso):
                    config.add_section(seeAlso)
                    copy_options(config, section, seeAlso, 
                            { 'content_type' : 'foaf', 
                              'depth' : str(depth - 1) })
                try:
                    from planet.config import downloadReadingList
                    downloadReadingList(seeAlso, config,
                        lambda data, subconfig : friend2config(model, friend, seeAlso, subconfig, data), 
                        False)
                except:
                    pass

    return

def copy_options(config, parent_section, child_section, overrides = {}):
    global inheritable_options
    for option in [x for x in config.options(parent_section) if x in inheritable_options]:
        if not overrides.has_key(option):
            config.set(child_section, option, config.get(parent_section, option))

    for option, value in overrides.items():
        config.set(child_section, option, value)


def friend2config(friend_model, friend, seeAlso, subconfig, data):

    try:
        from RDF import Model, NS, Parser, Statement
    except:
        return

    dc   = NS('http://purl.org/dc/elements/1.1/')
    foaf = NS('http://xmlns.com/foaf/0.1/')
    rdf = NS('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
    rdfs = NS('http://www.w3.org/2000/01/rdf-schema#')

    # FOAF InverseFunctionalProperties
    ifps = [foaf.mbox, foaf.mbox_sha1sum, foaf.jabberID, foaf.aimChatID, 
        foaf.icqChatID, foaf.yahooChatID, foaf.msnChatID, foaf.homepage, foaf.weblog]

    model = load_model(data, seeAlso)

    for statement in model.find_statements(Statement(None,rdf.type,foaf.Person)):

        samefriend = statement.subject
        
        # maybe they have the same uri
        if friend.is_resource() and samefriend.is_resource() and friend == samefriend:
            foaf2config(model, subconfig, samefriend)
            return

        for ifp in ifps:
            object = model.get_target(samefriend,ifp)
            if object and object == friend_model.get_target(friend, ifp):
                foaf2config(model, subconfig, samefriend)
                return

if __name__ == "__main__":
    import sys, urllib
    config = ConfigParser()

    for uri in sys.argv[1:]:
        config.add_section(uri)
        foaf2config(urllib.urlopen(uri), config, section=uri)
        config.remove_section(uri)

    config.write(sys.stdout)

########NEW FILE########
__FILENAME__ = idindex
from glob import glob
import os, sys

if __name__ == '__main__':
    rootdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, rootdir)

from planet.spider import filename
from planet import config

def open():
    try:
        cache = config.cache_directory()
        index=os.path.join(cache,'index')
        if not os.path.exists(index): return None
        import dbhash
        return dbhash.open(filename(index, 'id'),'w')
    except Exception, e:
        if e.__class__.__name__ == 'DBError': e = e.args[-1]
        from planet import logger as log
        log.error(str(e))

def destroy():
    from planet import logger as log
    cache = config.cache_directory()
    index=os.path.join(cache,'index')
    if not os.path.exists(index): return None
    idindex = filename(index, 'id')
    if os.path.exists(idindex): os.unlink(idindex)
    os.removedirs(index)
    log.info(idindex + " deleted")

def create():
    from planet import logger as log
    cache = config.cache_directory()
    index=os.path.join(cache,'index')
    if not os.path.exists(index): os.makedirs(index)
    import dbhash
    index = dbhash.open(filename(index, 'id'),'c')

    try:
        import libxml2
    except:
        libxml2 = False
        from xml.dom import minidom

    for file in glob(cache+"/*"):
        if os.path.isdir(file):
            continue
        elif libxml2:
            try:
                doc = libxml2.parseFile(file)
                ctxt = doc.xpathNewContext()
                ctxt.xpathRegisterNs('atom','http://www.w3.org/2005/Atom')
                entry = ctxt.xpathEval('/atom:entry/atom:id')
                source = ctxt.xpathEval('/atom:entry/atom:source/atom:id')
                if entry and source:
                    index[filename('',entry[0].content)] = source[0].content
                doc.freeDoc()
            except:
                log.error(file)
        else:
            try:
                doc = minidom.parse(file)
                doc.normalize()
                ids = doc.getElementsByTagName('id')
                entry = [e for e in ids if e.parentNode.nodeName == 'entry']
                source = [e for e in ids if e.parentNode.nodeName == 'source']
                if entry and source:
                    index[filename('',entry[0].childNodes[0].nodeValue)] = \
                        source[0].childNodes[0].nodeValue
                doc.freeDoc()
            except:
                log.error(file)

    log.info(str(len(index.keys())) + " entries indexed")
    index.close()

    return open()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage: %s [-c|-d]' % sys.argv[0]
        sys.exit(1)

    config.load(sys.argv[1])

    if len(sys.argv) > 2 and sys.argv[2] == '-c':
        create()
    elif len(sys.argv) > 2 and sys.argv[2] == '-d':
        destroy()
    else:
        from planet import logger as log
        index = open()
        if index:
            log.info(str(len(index.keys())) + " entries indexed")
            index.close()
        else:
            log.info("no entries indexed")

########NEW FILE########
__FILENAME__ = opml
from xml.sax import ContentHandler, make_parser, SAXParseException
from xml.sax.xmlreader import InputSource
from sgmllib import SGMLParser
from cStringIO import StringIO
from ConfigParser import ConfigParser
from htmlentitydefs import entitydefs
import re

# input = opml, output = ConfigParser
def opml2config(opml, config=None):

    if hasattr(opml, 'read'):
        opml = opml.read()

    if not config:
        config = ConfigParser()

    opmlParser = OpmlParser(config)

    try:
        # try SAX
        source = InputSource()
        source.setByteStream(StringIO(opml))
        parser = make_parser()
        parser.setContentHandler(opmlParser)
        parser.parse(source)
    except SAXParseException:
        # try as SGML
        opmlParser.feed(opml)

    return config

# Parse OPML via either SAX or SGML
class OpmlParser(ContentHandler,SGMLParser):
    entities = re.compile('&(#?\w+);')

    def __init__(self, config):
        ContentHandler.__init__(self)
        SGMLParser.__init__(self)
        self.config = config

    def startElement(self, name, attrs):

        # we are only looking for data in 'outline' nodes.
        if name != 'outline': return

        # A type of 'rss' is meant to be used generically to indicate that
        # this is an entry in a subscription list, but some leave this
        # attribute off, and others have placed 'atom' in here
        if attrs.has_key('type'):
            if attrs['type'] == 'link' and not attrs.has_key('url'):
                # Auto-correct WordPress link manager OPML files
                attrs = dict(attrs.items())
                attrs['type'] = 'rss'
            if attrs['type'].lower() not in['rss','atom']: return

        # The feed itself is supposed to be in an attribute named 'xmlUrl'
        # (note the camel casing), but this has proven to be problematic,
        # with the most common misspelling being in all lower-case
        if not attrs.has_key('xmlUrl') or not attrs['xmlUrl'].strip():
            for attribute in attrs.keys():
                if attribute.lower() == 'xmlurl' and attrs[attribute].strip():
                    attrs = dict(attrs.items())
                    attrs['xmlUrl'] = attrs[attribute]
                    break
            else:
                return

        # the text attribute is nominally required in OPML, but this
        # data is often found in a title attribute instead
        if not attrs.has_key('text') or not attrs['text'].strip():
            if not attrs.has_key('title') or not attrs['title'].strip(): return
            attrs = dict(attrs.items())
            attrs['text'] = attrs['title']

        # if we get this far, we either have a valid subscription list entry,
        # or one with a correctable error.  Add it to the configuration, if
        # it is not already there.
        xmlUrl = attrs['xmlUrl']
        if not self.config.has_section(xmlUrl):
            self.config.add_section(xmlUrl)
            self.config.set(xmlUrl, 'name', self.unescape(attrs['text']))

    def unescape(self, text):
        parsed = self.entities.split(text)

        for i in range(1,len(parsed),2):

            if parsed[i] in entitydefs.keys():
                # named entities
                codepoint=entitydefs[parsed[i]]
                match=self.entities.match(codepoint)
                if match:
                    parsed[i]=match.group(1)
                else:
                    parsed[i]=unichr(ord(codepoint))

                # numeric entities
                if parsed[i].startswith('#'):
                    if parsed[i].startswith('#x'):
                        parsed[i]=unichr(int(parsed[i][2:],16))
                    else:
                        parsed[i]=unichr(int(parsed[i][1:]))

        return u''.join(parsed).encode('utf-8')
    # SGML => SAX
    def unknown_starttag(self, name, attrs):
        attrs = dict(attrs)
        for attribute in attrs:
            try:
                attrs[attribute] = attrs[attribute].decode('utf-8')
            except:
                work = attrs[attribute].decode('iso-8859-1')
                work = u''.join([c in cp1252 and cp1252[c] or c for c in work])
                attrs[attribute] = work
        self.startElement(name, attrs)

# http://www.intertwingly.net/stories/2004/04/14/i18n.html#CleaningWindows
cp1252 = {
  unichr(128): unichr(8364), # euro sign
  unichr(130): unichr(8218), # single low-9 quotation mark
  unichr(131): unichr( 402), # latin small letter f with hook
  unichr(132): unichr(8222), # double low-9 quotation mark
  unichr(133): unichr(8230), # horizontal ellipsis
  unichr(134): unichr(8224), # dagger
  unichr(135): unichr(8225), # double dagger
  unichr(136): unichr( 710), # modifier letter circumflex accent
  unichr(137): unichr(8240), # per mille sign
  unichr(138): unichr( 352), # latin capital letter s with caron
  unichr(139): unichr(8249), # single left-pointing angle quotation mark
  unichr(140): unichr( 338), # latin capital ligature oe
  unichr(142): unichr( 381), # latin capital letter z with caron
  unichr(145): unichr(8216), # left single quotation mark
  unichr(146): unichr(8217), # right single quotation mark
  unichr(147): unichr(8220), # left double quotation mark
  unichr(148): unichr(8221), # right double quotation mark
  unichr(149): unichr(8226), # bullet
  unichr(150): unichr(8211), # en dash
  unichr(151): unichr(8212), # em dash
  unichr(152): unichr( 732), # small tilde
  unichr(153): unichr(8482), # trade mark sign
  unichr(154): unichr( 353), # latin small letter s with caron
  unichr(155): unichr(8250), # single right-pointing angle quotation mark
  unichr(156): unichr( 339), # latin small ligature oe
  unichr(158): unichr( 382), # latin small letter z with caron
  unichr(159): unichr( 376)} # latin capital letter y with diaeresis

if __name__ == "__main__":
    # small main program which converts OPML into config.ini format
    import sys, urllib
    config = ConfigParser()
    for opml in sys.argv[1:]:
        opml2config(urllib.urlopen(opml), config)
    config.write(sys.stdout)

########NEW FILE########
__FILENAME__ = publish
import os, sys
import urlparse
import planet
import pubsubhubbub_publisher as PuSH

def publish(config):
    log = planet.logger
    hub = config.pubsubhubbub_hub()
    link = config.link()

    # identify feeds
    feeds = []
    if hub and link:
        for root, dirs, files in os.walk(config.output_dir()):
            for file in files:
                 if file in config.pubsubhubbub_feeds():
                     feeds.append(urlparse.urljoin(link, file))

    # publish feeds
    if feeds:
        try:
            PuSH.publish(hub, feeds)
            for feed in feeds:
                log.info("Published %s to %s\n" % (feed, hub))
        except PuSH.PublishError, e:
            log.error("PubSubHubbub publishing error: %s\n" % e)

########NEW FILE########
__FILENAME__ = reconstitute
"""
Reconstitute an entry document from the output of the Universal Feed Parser.

The main entry point is called 'reconstitute'.  Input parameters are:

  results: this is the entire hash table return by the UFP
  entry:   this is the entry in the hash that you want reconstituted

The value returned is an XML DOM.  Every effort is made to convert
everything to unicode, and text fields into either plain text or
well formed XHTML.

Todo:
  * extension elements
"""
import re, time, sgmllib
from xml.sax.saxutils import escape
from xml.dom import minidom, Node
from html5lib import html5parser
from html5lib.treebuilders import dom
import planet, config

try:
  from hashlib import md5
except:
  from md5 import new as md5

illegal_xml_chars = re.compile("[\x01-\x08\x0B\x0C\x0E-\x1F]", re.UNICODE)

def createTextElement(parent, name, value):
    """ utility function to create a child element with the specified text"""
    if not value: return
    if isinstance(value,str):
        try:
            value=value.decode('utf-8')
        except:
            value=value.decode('iso-8859-1')
    value = illegal_xml_chars.sub(invalidate, value)
    xdoc = parent.ownerDocument
    xelement = xdoc.createElement(name)
    xelement.appendChild(xdoc.createTextNode(value))
    parent.appendChild(xelement)
    return xelement

def invalidate(c): 
    """ replace invalid characters """
    return u'<abbr title="U+%s">\ufffd</abbr>' % \
        ('000' + hex(ord(c.group(0)))[2:])[-4:]

def ncr2c(value):
    """ convert numeric character references to characters """
    value=value.group(1)
    if value.startswith('x'):
        value=unichr(int(value[1:],16))
    else:
        value=unichr(int(value))
    return value

nonalpha=re.compile('\W+',re.UNICODE)
def cssid(name):
    """ generate a css id from a name """
    try:
        name = nonalpha.sub('-',name.decode('utf-8')).lower().encode('utf-8')
    except:
        name = nonalpha.sub('-',name).lower()
    return name.strip('-')

def id(xentry, entry):
    """ copy or compute an id for the entry """

    if entry.has_key("id") and entry.id:
        entry_id = entry.id
    elif entry.has_key("link") and entry.link:
        entry_id = entry.link
    elif entry.has_key("title") and entry.title:
        entry_id = (entry.title_detail.base + "/" +
            md5(entry.title).hexdigest())
    elif entry.has_key("summary") and entry.summary:
        entry_id = (entry.summary_detail.base + "/" +
            md5(entry.summary).hexdigest())
    elif entry.has_key("content") and entry.content:

        entry_id = (entry.content[0].base + "/" + 
            md5(entry.content[0].value).hexdigest())
    else:
        return

    if xentry: createTextElement(xentry, 'id', entry_id)
    return entry_id

def links(xentry, entry):
    """ copy links to the entry """
    if not entry.has_key('links'):
       entry['links'] = []
       if entry.has_key('link'):
         entry['links'].append({'rel':'alternate', 'href':entry.link}) 
    xdoc = xentry.ownerDocument
    for link in entry['links']:
        if not 'href' in link.keys(): continue
        xlink = xdoc.createElement('link')
        xlink.setAttribute('href', link.get('href'))
        if link.has_key('type'):
            xlink.setAttribute('type', link.get('type'))
        if link.has_key('rel'):
            xlink.setAttribute('rel', link.get('rel',None))
        if link.has_key('title'):
            xlink.setAttribute('title', link.get('title'))
        if link.has_key('length'):
            xlink.setAttribute('length', link.get('length'))
        xentry.appendChild(xlink)

def date(xentry, name, parsed):
    """ insert a date-formated element into the entry """
    if not parsed: return
    formatted = time.strftime("%Y-%m-%dT%H:%M:%SZ", parsed)
    xdate = createTextElement(xentry, name, formatted)
    formatted = time.strftime(config.date_format(), parsed)
    xdate.setAttribute('planet:format', formatted.decode('utf-8'))

def category(xentry, tag):
    xtag = xentry.ownerDocument.createElement('category')
    if not tag.has_key('term') or not tag.term: return
    xtag.setAttribute('term', tag.get('term'))
    if tag.has_key('scheme') and tag.scheme:
        xtag.setAttribute('scheme', tag.get('scheme'))
    if tag.has_key('label') and tag.label:
        xtag.setAttribute('label', tag.get('label'))
    xentry.appendChild(xtag)

def author(xentry, name, detail):
    """ insert an author-like element into the entry """
    if not detail: return
    xdoc = xentry.ownerDocument
    xauthor = xdoc.createElement(name)

    if detail.get('name', None):
        createTextElement(xauthor, 'name', detail.get('name'))
    else:
        xauthor.appendChild(xdoc.createElement('name'))

    createTextElement(xauthor, 'email', detail.get('email', None))
    createTextElement(xauthor, 'uri', detail.get('href', None))
        
    xentry.appendChild(xauthor)

def content(xentry, name, detail, bozo):
    """ insert a content-like element into the entry """
    if not detail or not detail.value: return

    data = None
    xdiv = '<div xmlns="http://www.w3.org/1999/xhtml">%s</div>'
    xdoc = xentry.ownerDocument
    xcontent = xdoc.createElement(name)

    if isinstance(detail.value,unicode):
        detail.value=detail.value.encode('utf-8')

    if not detail.has_key('type') or detail.type.lower().find('html')<0:
        detail['value'] = escape(detail.value)
        detail['type'] = 'text/html'

    if detail.type.find('xhtml')>=0 and not bozo:
        try:
            data = minidom.parseString(xdiv % detail.value).documentElement
            xcontent.setAttribute('type', 'xhtml')
        except:
            bozo=1

    if detail.type.find('xhtml')<0 or bozo:
        parser = html5parser.HTMLParser(tree=dom.TreeBuilder)
        html = parser.parse(xdiv % detail.value, encoding="utf-8")
        for body in html.documentElement.childNodes:
            if body.nodeType != Node.ELEMENT_NODE: continue
            if body.nodeName != 'body': continue
            for div in body.childNodes:
                if div.nodeType != Node.ELEMENT_NODE: continue
                if div.nodeName != 'div': continue
                try:
                    div.normalize()
                    if len(div.childNodes) == 1 and \
                        div.firstChild.nodeType == Node.TEXT_NODE:
                        data = div.firstChild
                        if illegal_xml_chars.search(data.data):
                            data = xdoc.createTextNode(
                                illegal_xml_chars.sub(invalidate, data.data))
                    else:
                        data = div
                        xcontent.setAttribute('type', 'xhtml')
                    break
                except:
                    # in extremely nested cases, the Python runtime decides
                    # that normalize() must be in an infinite loop; mark
                    # the content as escaped html and proceed on...
                    xcontent.setAttribute('type', 'html')
                    data = xdoc.createTextNode(detail.value.decode('utf-8'))

    if data: xcontent.appendChild(data)

    if detail.get("language"):
        xcontent.setAttribute('xml:lang', detail.language)

    xentry.appendChild(xcontent)

def location(xentry, long, lat):
    """ insert geo location into the entry """
    if not lat or not long: return

    xlat = createTextElement(xentry, '%s:%s' % ('geo','lat'), '%f' % lat)
    xlat.setAttribute('xmlns:%s' % 'geo', 'http://www.w3.org/2003/01/geo/wgs84_pos#')
    xlong = createTextElement(xentry, '%s:%s' % ('geo','long'), '%f' % long)
    xlong.setAttribute('xmlns:%s' % 'geo', 'http://www.w3.org/2003/01/geo/wgs84_pos#')

    xentry.appendChild(xlat)
    xentry.appendChild(xlong)

def source(xsource, source, bozo, format):
    """ copy source information to the entry """
    xdoc = xsource.ownerDocument

    createTextElement(xsource, 'id', source.get('id', source.get('link',None)))
    createTextElement(xsource, 'icon', source.get('icon', None))
    createTextElement(xsource, 'logo', source.get('logo', None))

    if not source.has_key('logo') and source.has_key('image'):
        createTextElement(xsource, 'logo', source.image.get('href',None))

    for tag in source.get('tags',[]):
        category(xsource, tag)

    author(xsource, 'author', source.get('author_detail',{}))
    for contributor in source.get('contributors',[]):
        author(xsource, 'contributor', contributor)

    if not source.has_key('links') and source.has_key('href'): #rss
        source['links'] = [{ 'href': source.get('href') }]
        if source.has_key('title'): 
            source['links'][0]['title'] = source.get('title')
    links(xsource, source)

    content(xsource, 'rights', source.get('rights_detail',None), bozo)
    content(xsource, 'subtitle', source.get('subtitle_detail',None), bozo)
    content(xsource, 'title', source.get('title_detail',None), bozo)

    date(xsource, 'updated', source.get('updated_parsed',time.gmtime()))

    if format: source['planet_format'] = format
    if not bozo == None: source['planet_bozo'] = bozo and 'true' or 'false'

    # propagate planet inserted information
    if source.has_key('planet_name') and not source.has_key('planet_css-id'):
        source['planet_css-id'] = cssid(source['planet_name'])
    for key, value in source.items():
        if key.startswith('planet_'):
            createTextElement(xsource, key.replace('_',':',1), value)

def reconstitute(feed, entry):
    """ create an entry document from a parsed feed """
    xdoc=minidom.parseString('<entry xmlns="http://www.w3.org/2005/Atom"/>\n')
    xentry=xdoc.documentElement
    xentry.setAttribute('xmlns:planet',planet.xmlns)

    if entry.has_key('language'):
        xentry.setAttribute('xml:lang', entry.language)
    elif feed.feed.has_key('language'):
        xentry.setAttribute('xml:lang', feed.feed.language)

    id(xentry, entry)
    links(xentry, entry)

    bozo = feed.bozo
    if not entry.has_key('title') or not entry.title:
        xentry.appendChild(xdoc.createElement('title'))

    content(xentry, 'title', entry.get('title_detail',None), bozo)
    content(xentry, 'summary', entry.get('summary_detail',None), bozo)
    content(xentry, 'content', entry.get('content',[None])[0], bozo)
    content(xentry, 'rights', entry.get('rights_detail',None), bozo)

    date(xentry, 'updated', entry_updated(feed.feed, entry, time.gmtime()))
    date(xentry, 'published', entry.get('published_parsed',None))

    if entry.has_key('dc_date.taken'):
        date_Taken = createTextElement(xentry, '%s:%s' % ('dc','date_Taken'), '%s' % entry.get('dc_date.taken', None))
        date_Taken.setAttribute('xmlns:%s' % 'dc', 'http://purl.org/dc/elements/1.1/')
        xentry.appendChild(date_Taken)

    for tag in entry.get('tags',[]):
        category(xentry, tag)

    # known, simple text extensions
    for ns,name in [('feedburner','origLink')]:
        if entry.has_key('%s_%s' % (ns,name.lower())) and \
            feed.namespaces.has_key(ns):
            xoriglink = createTextElement(xentry, '%s:%s' % (ns,name),
                entry['%s_%s' % (ns,name.lower())])
            xoriglink.setAttribute('xmlns:%s' % ns, feed.namespaces[ns])

    # geo location
    if entry.has_key('where') and \
        entry.get('where',[]).has_key('type') and \
        entry.get('where',[]).has_key('coordinates'):
        where = entry.get('where',[])
        type = where.get('type',None)
        coordinates = where.get('coordinates',None)
        if type == 'Point':
            location(xentry, coordinates[0], coordinates[1])
        elif type == 'Box' or type == 'LineString' or type == 'Polygon':
            location(xentry, coordinates[0][0], coordinates[0][1])
    if entry.has_key('geo_lat') and \
        entry.has_key('geo_long'):
        location(xentry, (float)(entry.get('geo_long',None)), (float)(entry.get('geo_lat',None)))
    if entry.has_key('georss_point'):
        coordinates = re.split('[,\s]', entry.get('georss_point'))
        location(xentry, (float)(coordinates[1]), (float)(coordinates[0]))
    elif entry.has_key('georss_line'):
        coordinates = re.split('[,\s]', entry.get('georss_line'))
        location(xentry, (float)(coordinates[1]), (float)(coordinates[0]))
    elif entry.has_key('georss_circle'):
        coordinates = re.split('[,\s]', entry.get('georss_circle'))
        location(xentry, (float)(coordinates[1]), (float)(coordinates[0]))
    elif entry.has_key('georss_box'):
        coordinates = re.split('[,\s]', entry.get('georss_box'))
        location(xentry, ((float)(coordinates[1])+(float)(coordinates[3]))/2, ((float)(coordinates[0])+(float)(coordinates[2]))/2)
    elif entry.has_key('georss_polygon'):
        coordinates = re.split('[,\s]', entry.get('georss_polygon'))
        location(xentry, (float)(coordinates[1]), (float)(coordinates[0]))

    # author / contributor
    author_detail = entry.get('author_detail',{})
    if author_detail and not author_detail.has_key('name') and \
        feed.feed.has_key('planet_name'):
        author_detail['name'] = feed.feed['planet_name']
    author(xentry, 'author', author_detail)
    for contributor in entry.get('contributors',[]):
        author(xentry, 'contributor', contributor)

    # merge in planet:* from feed (or simply use the feed if no source)
    src = entry.get('source')
    if src:
        for name,value in feed.feed.items():
            if name.startswith('planet_'): src[name]=value
        if feed.feed.has_key('id'):
            src['planet_id'] = feed.feed.id
    else:
        src = feed.feed

    # source:author
    src_author = src.get('author_detail',{})
    if (not author_detail or not author_detail.has_key('name')) and \
       not src_author.has_key('name') and  feed.feed.has_key('planet_name'):
       if src_author: src_author = src_author.__class__(src_author.copy())
       src['author_detail'] = src_author
       src_author['name'] = feed.feed['planet_name']

    # source
    xsource = xdoc.createElement('source')
    source(xsource, src, bozo, feed.version)
    xentry.appendChild(xsource)

    return xdoc

def entry_updated(feed, entry, default = None):
    chks = ((entry, 'updated_parsed'),
            (entry, 'published_parsed'),
            (feed,  'updated_parsed'),)
    for node, field in chks:
        if node.has_key(field) and node[field]:
            return node[field]
    return default

########NEW FILE########
__FILENAME__ = scrub
"""
Process a set of configuration defined sanitations on a given feed.
"""

# Standard library modules
import time
# Planet modules
import planet, config, shell
from planet import feedparser

type_map = {'text': 'text/plain', 'html': 'text/html',
    'xhtml': 'application/xhtml+xml'}

def scrub(feed_uri, data):

    # some data is not trustworthy
    for tag in config.ignore_in_feed(feed_uri).split():
        if tag.find('lang')>=0: tag='language'
        if data.feed.has_key(tag): del data.feed[tag]
        for entry in data.entries:
            if entry.has_key(tag): del entry[tag]
            if entry.has_key(tag + "_detail"): del entry[tag + "_detail"]
            if entry.has_key(tag + "_parsed"): del entry[tag + "_parsed"]
            for key in entry.keys():
                if not key.endswith('_detail'): continue
                for detail in entry[key].copy():
                    if detail == tag: del entry[key][detail]

    # adjust title types
    if config.title_type(feed_uri):
        title_type = config.title_type(feed_uri)
        title_type = type_map.get(title_type, title_type)
        for entry in data.entries:
            if entry.has_key('title_detail'):
                entry.title_detail['type'] = title_type

    # adjust summary types
    if config.summary_type(feed_uri):
        summary_type = config.summary_type(feed_uri)
        summary_type = type_map.get(summary_type, summary_type)
        for entry in data.entries:
            if entry.has_key('summary_detail'):
                entry.summary_detail['type'] = summary_type

    # adjust content types
    if config.content_type(feed_uri):
        content_type = config.content_type(feed_uri)
        content_type = type_map.get(content_type, content_type)
        for entry in data.entries:
            if entry.has_key('content'):
                entry.content[0]['type'] = content_type

    # some people put html in author names
    if config.name_type(feed_uri).find('html')>=0:
        from shell.tmpl import stripHtml
        if data.feed.has_key('author_detail') and \
            data.feed.author_detail.has_key('name'):
            data.feed.author_detail['name'] = \
                str(stripHtml(data.feed.author_detail.name))
        for entry in data.entries:
            if entry.has_key('author_detail') and \
                entry.author_detail.has_key('name'):
                entry.author_detail['name'] = \
                    str(stripHtml(entry.author_detail.name))
            if entry.has_key('source'):
                source = entry.source
                if source.has_key('author_detail') and \
                    source.author_detail.has_key('name'):
                    source.author_detail['name'] = \
                        str(stripHtml(source.author_detail.name))

    # handle dates in the future
    future_dates = config.future_dates(feed_uri).lower()
    if future_dates == 'ignore_date':
      now = time.gmtime()
      if data.feed.has_key('updated_parsed') and data.feed['updated_parsed']:
        if data.feed['updated_parsed'] > now: del data.feed['updated_parsed']
      for entry in data.entries:
        if entry.has_key('published_parsed') and entry['published_parsed']:
          if entry['published_parsed'] > now:
            del entry['published_parsed']
            del entry['published']
        if entry.has_key('updated_parsed') and entry['updated_parsed']:
          if entry['updated_parsed'] > now:
            del entry['updated_parsed']
            del entry['updated']
    elif future_dates == 'ignore_entry':
      now = time.time()
      if data.feed.has_key('updated_parsed') and data.feed['updated_parsed']:
        if data.feed['updated_parsed'] > now: del data.feed['updated_parsed']
      data.entries = [entry for entry in data.entries if 
        (not entry.has_key('published_parsed') or not entry['published_parsed']
          or entry['published_parsed'] <= now) and
        (not entry.has_key('updated_parsed') or not entry['updated_parsed']
          or entry['updated_parsed'] <= now)]

    scrub_xmlbase = config.xml_base(feed_uri)

    # resolve relative URIs and sanitize
    for entry in data.entries + [data.feed]:
        for key in entry.keys():
            if key == 'content'and not entry.has_key('content_detail'):
                node = entry.content[0]
            elif key.endswith('_detail'):
                node = entry[key]
            else:
                continue

            if not node.has_key('type'): continue
            if not 'html' in node['type']: continue
            if not node.has_key('value'): continue

            if node.has_key('base'):
                if scrub_xmlbase:
                    if scrub_xmlbase == 'feed_alternate':
                        if entry.has_key('source') and \
                            entry.source.has_key('link'):
                            node['base'] = entry.source.link
                        elif data.feed.has_key('link'):
                            node['base'] = data.feed.link
                    elif scrub_xmlbase == 'entry_alternate':
                        if entry.has_key('link'):
                            node['base'] = entry.link
                    else:
                        node['base'] = feedparser._urljoin(
                            node['base'], scrub_xmlbase)

                node['value'] = feedparser._resolveRelativeURIs(
                    node.value, node.base, 'utf-8', node.type)

            # Run this through HTML5's sanitizer
            doc = None
            if 'xhtml' in node['type']:
              try:
                from xml.dom import minidom
                doc = minidom.parseString(node['value'])
              except:
                node['type']='text/html'

            if not doc:
              from html5lib import html5parser, treebuilders
              p=html5parser.HTMLParser(tree=treebuilders.getTreeBuilder('dom'))
              doc = p.parseFragment(node['value'], encoding='utf-8')

            from html5lib import treewalkers, serializer
            from html5lib.filters import sanitizer
            walker = sanitizer.Filter(treewalkers.getTreeWalker('dom')(doc))
            xhtml = serializer.XHTMLSerializer(inject_meta_charset = False)
            tree = xhtml.serialize(walker, encoding='utf-8')

            node['value'] = ''.join([str(token) for token in tree])

########NEW FILE########
__FILENAME__ = dj
import os.path
import urlparse
import datetime

import tmpl
from planet import config

def DjangoPlanetDate(value):
    return datetime.datetime(*value[:6])

# remap PlanetDate to be a datetime, so Django template authors can use 
# the "date" filter on these values
tmpl.PlanetDate = DjangoPlanetDate

def run(script, doc, output_file=None, options={}):
    """process a Django template file"""

    # this is needed to use the Django template system as standalone
    # I need to re-import the settings at every call because I have to 
    # set the TEMPLATE_DIRS variable programmatically
    from django.conf import settings
    settings._wrapped=None
    try:
        settings.configure(
            DEBUG=True, TEMPLATE_DEBUG=True, 
            TEMPLATE_DIRS=(os.path.dirname(script),)
            )
    except EnvironmentError:
        pass
    from django.template import Context
    from django.template.loader import get_template

    # set up the Django context by using the default htmltmpl 
    # datatype converters
    context = Context()
    context.update(tmpl.template_info(doc))
    context['Config'] = config.planet_options()
    t = get_template(script)

    if output_file:
        reluri = os.path.splitext(os.path.basename(output_file))[0]
        context['url'] = urlparse.urljoin(config.link(),reluri)
        f = open(output_file, 'w')
        ss = t.render(context)
        if isinstance(ss,unicode): ss=ss.encode('utf-8')
        f.write(ss)
        f.close()
    else:
        # @@this is useful for testing purposes, but does it 
        # belong here?
        return t.render(context)

########NEW FILE########
__FILENAME__ = plugin
import os, sys, imp
from StringIO import StringIO

def run(script, doc, output_file=None, options={}):
    """ process an Python script using imp """
    save_sys = (sys.stdin, sys.stdout, sys.stderr, sys.argv)
    plugin_stdout = StringIO()
    plugin_stderr = StringIO()

    try:
        # redirect stdin
        sys.stdin = StringIO(doc)

        # redirect stdout
        if output_file:
            sys.stdout = open(output_file, 'w')
        else:
            sys.stdout = plugin_stdout

        # redirect stderr
        sys.stderr = plugin_stderr

        # determine __file__ value
        if options.has_key("__file__"):
            plugin_file = options["__file__"]
            del options["__file__"]
        else:
            plugin_file = script

        # set sys.argv
        options = sum([['--'+key, value] for key,value in options.items()], [])
        sys.argv = [plugin_file] + options

        # import script
        handle = open(script, 'r')
        cwd = os.getcwd()
        try:
            try:
                try:
                    description=('.plugin', 'rb', imp.PY_SOURCE)
                    imp.load_module('__main__',handle,plugin_file,description)
                except SystemExit,e:
                    if e.code: log.error('%s exit rc=%d',(plugin_file,e.code))
            except Exception, e:
                import traceback
                type, value, tb = sys.exc_info()
                plugin_stderr.write(''.join(
                   traceback.format_exception_only(type,value) +
                   traceback.format_tb(tb)))
        finally:
            handle.close()
            if cwd != os.getcwd(): os.chdir(cwd)

    finally:
        # restore system state
        sys.stdin, sys.stdout, sys.stderr, sys.argv = save_sys

    # log anything sent to stderr
    if plugin_stderr.getvalue():
        import planet
        planet.logger.error(plugin_stderr.getvalue())

    # return stdout
    return plugin_stdout.getvalue()

########NEW FILE########
__FILENAME__ = py
from subprocess import Popen, PIPE
import sys 

def run(script, doc, output_file=None, options={}):
    """ process an Python script """

    if output_file:
        out = open(output_file, 'w')
    else:
        out = PIPE

    options = sum([['--'+key, value] for key,value in options.items()], [])

    proc = Popen([sys.executable, script] + options,
        stdin=PIPE, stdout=out, stderr=PIPE)

    stdout, stderr = proc.communicate(doc)
    if stderr:
        import planet
        planet.logger.error(stderr)

    return stdout

########NEW FILE########
__FILENAME__ = sed
from subprocess import Popen, PIPE

def run(script, doc, output_file=None, options={}):
    """ process an Python script """

    if output_file:
        out = open(output_file, 'w')
    else:
        out = PIPE

    proc = Popen(['sed', '-f', script],
        stdin=PIPE, stdout=out, stderr=PIPE)

    stdout, stderr = proc.communicate(doc)
    if stderr:
        import planet
        planet.logger.error(stderr)

    return stdout

########NEW FILE########
__FILENAME__ = tmpl
from xml.sax.saxutils import escape
import sgmllib, time, os, sys, new, urlparse, re
from planet import config, feedparser
import htmltmpl

voids=feedparser._BaseHTMLProcessor.elements_no_end_tag
empty=re.compile(r"<((%s)[^>]*)></\2>" % '|'.join(voids))

class stripHtml(sgmllib.SGMLParser):
    "remove all tags from the data"
    def __init__(self, data):
        sgmllib.SGMLParser.__init__(self)
        self.result=''
        if isinstance(data, str):
            try:
                self.feed(data.decode('utf-8'))
            except:
                self.feed(data)
        else:
            self.feed(data)
        self.close()
    def __str__(self):
        if isinstance(self.result, unicode):
            return self.result.encode('utf-8')
        return self.result
    def handle_entityref(self, ref):
        import htmlentitydefs
        if ref in htmlentitydefs.entitydefs:
            ref=htmlentitydefs.entitydefs[ref]
            if len(ref)==1:
                self.result+=unichr(ord(ref))
            elif ref.startswith('&#') and ref.endswith(';'):
                self.handle_charref(ref[2:-1])
            else:
                self.result+='&%s;' % ref
        else:
            self.result+='&%s;' % ref
    def handle_charref(self, ref):
        try:
            if ref.startswith('x'):
                self.result+=unichr(int(ref[1:],16))
            else:
                self.result+=unichr(int(ref))
        except:
            self.result+='&#%s;' % ref
    def handle_data(self, data):
        if data: self.result+=data

# Data format mappers

def String(value):
    if isinstance(value, unicode): return value.encode('utf-8')
    return value

def Plain(value):
    return str(stripHtml(value))

def PlanetDate(value):
    return time.strftime(config.date_format(), value)

def NewDate(value):
    return time.strftime(config.new_date_format(), value)

def Rfc822(value):
    return time.strftime("%a, %d %b %Y %H:%M:%S +0000", value)

def Rfc3399(value):
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", value)

# Map from FeedParser path to Planet tmpl names
Base = [
    ['author', String, 'author'],
    ['author_name', String, 'author_detail', 'name'],
    ['generator', String, 'generator'],
    ['id', String, 'id'],
    ['icon', String, 'icon'],
    ['last_updated_822', Rfc822, 'updated_parsed'],
    ['last_updated_iso', Rfc3399, 'updated_parsed'],
    ['last_updated', PlanetDate, 'updated_parsed'],
    ['link', String, 'link'],
    ['logo', String, 'logo'],
    ['rights', String, 'rights_detail', 'value'],
    ['subtitle', String, 'subtitle_detail', 'value'],
    ['title', String, 'title_detail', 'value'],
    ['title_plain', Plain, 'title_detail', 'value'],
    ['url', String, 'links', {'rel':'self'}, 'href'],
    ['url', String, 'planet_http_location'],
]

Items = [
    ['author', String, 'author'],
    ['author_email', String, 'author_detail', 'email'],
    ['author_name', String, 'author_detail', 'name'],
    ['author_uri', String, 'author_detail', 'href'],
    ['content_language', String, 'content', 0, 'language'],
    ['content', String, 'summary_detail', 'value'],
    ['content', String, 'content', 0, 'value'],
    ['date', PlanetDate, 'published_parsed'],
    ['date', PlanetDate, 'updated_parsed'],
    ['date_822', Rfc822, 'published_parsed'],
    ['date_822', Rfc822, 'updated_parsed'],
    ['date_iso', Rfc3399, 'published_parsed'],
    ['date_iso', Rfc3399, 'updated_parsed'],
    ['enclosure_href', String, 'links', {'rel': 'enclosure'}, 'href'],
    ['enclosure_length', String, 'links', {'rel': 'enclosure'}, 'length'],
    ['enclosure_type', String, 'links', {'rel': 'enclosure'}, 'type'],
    ['id', String, 'id'],
    ['link', String, 'links', {'rel': 'alternate'}, 'href'],
    ['new_channel', String, 'source', 'id'],
    ['new_date', NewDate, 'published_parsed'],
    ['new_date', NewDate, 'updated_parsed'],
    ['rights', String, 'rights_detail', 'value'],
    ['title_language', String, 'title_detail', 'language'],
    ['title_plain', Plain, 'title_detail', 'value'],
    ['title', String, 'title_detail', 'value'],
    ['summary_language', String, 'summary_detail', 'language'],
    ['updated', PlanetDate, 'updated_parsed'],
    ['updated_822', Rfc822, 'updated_parsed'],
    ['updated_iso', Rfc3399, 'updated_parsed'],
    ['published', PlanetDate, 'published_parsed'],
    ['published_822', Rfc822, 'published_parsed'],
    ['published_iso', Rfc3399, 'published_parsed'],
]

# Add additional rules for source information
for rule in Base:
    Items.append(['channel_'+rule[0], rule[1], 'source'] + rule[2:])

def tmpl_mapper(source, rules):
    "Apply specified rules to the source, and return a template dictionary"
    output = {}

    for rule in rules:
        node = source
        for path in rule[2:]:
            if isinstance(path, str) and path in node:
                if path == 'value':
                    if node.get('type','')=='text/plain':
                        node['value'] = escape(node['value'])
                        node['type'] = 'text/html'
                    elif node.get('type','')=='application/xhtml+xml':
                        node['value'] = empty.sub(r"<\1 />", node['value'])
                node = node[path]
            elif isinstance(path, int):
                node = node[path]
            elif isinstance(path, dict):
                for test in node:
                    for key, value in path.items():
                        if test.get(key,None) != value: break
                    else:
                        node = test
                        break
                else:
                    break
            else:
                break
        else:
            if node: output[rule[0]] = rule[1](node)
        
    # copy over all planet namespaced elements from parent source
    for name,value in source.items():
        if name.startswith('planet_'):
            output[name[7:]] = String(value)
        if not output.get('name') and source.has_key('title_detail'):
            output['name'] = Plain(source.title_detail.value)

    # copy over all planet namespaced elements from child source element
    if 'source' in source:
        for name,value in source.source.items():
            if name.startswith('planet_'):
                output['channel_' + name[7:]] = String(value)
            if not output.get('channel_name') and \
                source.source.has_key('title_detail'):
                output['channel_name'] = Plain(source.source.title_detail.value)

    return output

def _end_planet_source(self):
    self._end_source()
    context = self._getContext()
    if not context.has_key('sources'): context['sources'] = []
    context.sources.append(context.source)
    del context['source']

def template_info(source):
    """ get template information from a feedparser output """

    # wire in support for planet:source, call feedparser, unplug planet:source
    mixin=feedparser._FeedParserMixin
    mixin._start_planet_source = mixin._start_source
    mixin._end_planet_source = \
        new.instancemethod(_end_planet_source, None, mixin)
    data=feedparser.parse(source)
    del mixin._start_planet_source
    del mixin._end_planet_source

    # apply rules to convert feed parser output to htmltmpl input
    output = {'Channels': [], 'Items': []}
    output.update(tmpl_mapper(data.feed, Base))
    sources = []
    for feed in data.feed.get('sources',[]):
        source = tmpl_mapper(feed, Base)
        sources.append([source.get('name'), source])
    sources.sort()
    output['Channels'] = [source for name,source in sources]
    for entry in data.entries:
        output['Items'].append(tmpl_mapper(entry, Items))

    # synthesize isPermaLink attribute
    for item in output['Items']:
        if item.get('id') == item.get('link'):
            item['guid_isPermaLink']='true'
        else:
            item['guid_isPermaLink']='false'

    # feed level information
    output['generator'] = config.generator_uri()
    output['name'] = config.name()
    output['link'] = config.link()
    output['owner_name'] = config.owner_name()
    output['owner_email'] = config.owner_email()
    output['pubsubhubbub_hub'] = config.pubsubhubbub_hub()
    if config.feed():
        output['feed'] = config.feed()
        output['feedtype'] = config.feed().find('rss')>=0 and 'rss' or 'atom'

    # date/time information
    date = time.gmtime()
    output['date'] = PlanetDate(date)
    output['date_iso'] = Rfc3399(date)
    output['date_822'] = Rfc822(date)

    # remove new_dates and new_channels that aren't "new"
    date = channel = None
    for item in output['Items']:
        if item.has_key('new_date'):
            if item['new_date'] == date:
                del item['new_date']
            else:
                date = item['new_date']

        if item.has_key('new_channel'):
            if item['new_channel'] == channel and not item.has_key('new_date'):
                del item['new_channel']
            else:
                channel = item['new_channel']

    return output

def run(script, doc, output_file=None, options={}):
    """ process an HTMLTMPL file """
    manager = htmltmpl.TemplateManager()
    template = manager.prepare(script)
    tp = htmltmpl.TemplateProcessor(html_escape=0)
    for key,value in template_info(doc).items():
        tp.set(key, value)

    if output_file:
        basename = os.path.basename(output_file)
        reluri = os.path.splitext(os.path.basename(output_file))[0]
        tp.set('url', urlparse.urljoin(config.link(),reluri))
        tp.set('fullurl', urlparse.urljoin(config.link(),basename))

        output = open(output_file, "w")
        output.write(tp.process(template))
        output.close()
    else:
        return tp.process(template)

if __name__ == '__main__':
    sys.path.insert(0, os.path.split(sys.path[0])[0])

    for test in sys.argv[1:]:
        from pprint import pprint
        pprint(template_info('/home/rubys/bzr/venus/tests/data/filter/tmpl/'+test))


########NEW FILE########
__FILENAME__ = xslt
import os

def quote(string, apos):
    """ quote a string so that it can be passed as a parameter """
    if type(string) == unicode:
        string=string.encode('utf-8')
    if apos.startswith("\\"): string.replace('\\','\\\\')

    if string.find("'")<0:
        return "'" + string + "'"
    elif string.find('"')<0:
        return '"' + string + '"'
    else:
        # unclear how to quote strings with both types of quotes for libxslt
        return "'" + string.replace("'",apos) + "'"

def run(script, doc, output_file=None, options={}):
    """ process an XSLT stylesheet """

    try:
        # if available, use the python interface to libxslt
        import libxml2
        import libxslt
        dom = libxml2.parseDoc(doc)
        docfile = None
    except:
        # otherwise, use the command line interface
        dom = None

    # do it
    result = None
    if dom:
        styledoc = libxml2.parseFile(script)
        style = libxslt.parseStylesheetDoc(styledoc)
        for key in options.keys():
            options[key] = quote(options[key], apos="\xe2\x80\x99")
        output = style.applyStylesheet(dom, options)
        if output_file:
            style.saveResultToFilename(output_file, output, 0)
        else:
            result = output.serialize('utf-8')
        style.freeStylesheet()
        output.freeDoc()
    elif output_file:
        import warnings
        if hasattr(warnings, 'simplefilter'):
            warnings.simplefilter('ignore', RuntimeWarning)
        docfile = os.tmpnam()
        file = open(docfile,'w')
        file.write(doc)
        file.close()

        cmdopts = []
        for key,value in options.items():
           if value.find("'")>=0 and value.find('"')>=0: continue
           cmdopts += ['--stringparam', key, quote(value, apos=r"\'")]

        os.system('xsltproc %s %s %s > %s' %
            (' '.join(cmdopts), script, docfile, output_file))
        os.unlink(docfile)
    else:
        import sys
        from subprocess import Popen, PIPE

        options = sum([['--stringparam', key, value]
            for key,value in options.items()], [])

        proc = Popen(['xsltproc'] + options + [script, '-'],
            stdin=PIPE, stdout=PIPE, stderr=PIPE)

        result, stderr = proc.communicate(doc)
        if stderr:
            import planet
            planet.logger.error(stderr)

    if dom: dom.freeDoc()

    return result

########NEW FILE########
__FILENAME__ = _genshi
from StringIO import StringIO
from xml.sax.saxutils import escape

from genshi.input import HTMLParser, XMLParser
from genshi.template import Context, MarkupTemplate

subscriptions = []
feed_types = [
    'application/atom+xml',
    'application/rss+xml',
    'application/rdf+xml'
]

def norm(value):
    """ Convert to Unicode """
    if hasattr(value,'items'):
        return dict([(norm(n),norm(v)) for n,v in value.items()])

    try:
        return value.decode('utf-8')
    except:
        return value.decode('iso-8859-1')

def find_config(config, feed):
    # match based on self link
    for link in feed.links:
        if link.has_key('rel') and link.rel=='self':
            if link.has_key('type') and link.type in feed_types:
                if link.has_key('href') and link.href in subscriptions:
                    return norm(dict(config.parser.items(link.href)))

    # match based on name
    for sub in subscriptions:
        if config.parser.has_option(sub, 'name') and \
            norm(config.parser.get(sub, 'name')) == feed.planet_name:
            return norm(dict(config.parser.items(sub)))

    return {}

class XHTMLParser(object):
    """ parse an XHTML fragment """
    def __init__(self, text):
        self.parser = XMLParser(StringIO("<div>%s</div>" % text))
        self.depth = 0
    def __iter__(self):
        self.iter = self.parser.__iter__()
        return self
    def next(self):
        object = self.iter.next()
        if object[0] == 'END': self.depth = self.depth - 1
        predepth = self.depth
        if object[0] == 'START': self.depth = self.depth + 1
        if predepth: return object
        return self.next()

def streamify(text,bozo):
    """ add a .stream to a _detail textConstruct """
    if text.type == 'text/plain':
        text.stream = HTMLParser(StringIO(escape(text.value)))
    elif text.type == 'text/html' or bozo != 'false':
        text.stream = HTMLParser(StringIO(text.value))
    else:
        text.stream = XHTMLParser(text.value)

def run(script, doc, output_file=None, options={}):
    """ process an Genshi template """

    context = Context(**options)

    tmpl_fileobj = open(script)
    tmpl = MarkupTemplate(tmpl_fileobj, script, lookup="lenient")
    tmpl_fileobj.close()

    if not output_file: 
        # filter
        context.push({'input':XMLParser(StringIO(doc))})
    else:
        # template
        import time
        from planet import config,feedparser
        from planet.spider import filename

        # gather a list of subscriptions, feeds
        global subscriptions
        feeds = []
        sources = config.cache_sources_directory()
        for sub in config.subscriptions():
            data=feedparser.parse(filename(sources,sub))
            data.feed.config = norm(dict(config.parser.items(sub)))
            if data.feed.has_key('link'):
                feeds.append((data.feed.config.get('name',''),data.feed))
            subscriptions.append(norm(sub))
        feeds.sort()

        # annotate each entry
        new_date_format = config.new_date_format()
        vars = feedparser.parse(StringIO(doc))
        vars.feeds = [value for name,value in feeds]
        last_feed = None
        last_date = None
        for entry in vars.entries:
             entry.source.config = find_config(config, entry.source)

             # add new_feed and new_date fields
             entry.new_feed = entry.source.id
             entry.new_date = date = None
             if entry.has_key('published_parsed'): date=entry.published_parsed
             if entry.has_key('updated_parsed'): date=entry.updated_parsed
             if date: entry.new_date = time.strftime(new_date_format, date)

             # remove new_feed and new_date fields if not "new"
             if entry.new_date == last_date:
                 entry.new_date = None
                 if entry.new_feed == last_feed:
                     entry.new_feed = None
                 else:
                     last_feed = entry.new_feed
             elif entry.new_date:
                 last_date = entry.new_date
                 last_feed = None

             # add streams for all text constructs
             for key in entry.keys():
                 if key.endswith("_detail") and entry[key].has_key('type') and \
                     entry[key].has_key('value'):
                     streamify(entry[key],entry.source.planet_bozo)
             if entry.has_key('content'):
                 for content in entry.content:
                     streamify(content,entry.source.planet_bozo)
     
        # add cumulative feed information to the Genshi context
        vars.feed.config = dict(config.parser.items('Planet',True))
        context.push(vars)

    # apply template
    output=tmpl.generate(context).render('xml')

    if output_file:
        out_file = open(output_file,'w')
        out_file.write(output)
        out_file.close()
    else:
        return output

########NEW FILE########
__FILENAME__ = spider
"""
Fetch either a single feed, or a set of feeds, normalize to Atom and XHTML,
and write each as a set of entries in a cache directory.
"""

# Standard library modules
import time, calendar, re, os, urlparse
from xml.dom import minidom
# Planet modules
import planet, config, feedparser, reconstitute, shell, socket, scrub
from StringIO import StringIO 

try:
  from hashlib import md5
except:
  from md5 import new as md5

# Regular expressions to sanitise cache filenames
re_url_scheme    = re.compile(r'^\w+:/*(\w+:|www\.)?')
re_slash         = re.compile(r'[?/:|]+')
re_initial_cruft = re.compile(r'^[,.]*')
re_final_cruft   = re.compile(r'[,.]*$')

index = True

def filename(directory, filename):
    """Return a filename suitable for the cache.

    Strips dangerous and common characters to create a filename we
    can use to store the cache in.
    """
    try:
        if re_url_scheme.match(filename):
            if isinstance(filename,str):
                filename=filename.decode('utf-8').encode('idna')
            else:
                filename=filename.encode('idna')
    except:
        pass
    if isinstance(filename,unicode):
        filename=filename.encode('utf-8')
    filename = re_url_scheme.sub("", filename)
    filename = re_slash.sub(",", filename)
    filename = re_initial_cruft.sub("", filename)
    filename = re_final_cruft.sub("", filename)

    # limit length of filename
    if len(filename)>250:
        parts=filename.split(',')
        for i in range(len(parts),0,-1):
            if len(','.join(parts[:i])) < 220:
                filename = ','.join(parts[:i]) + ',' + \
                    md5(','.join(parts[i:])).hexdigest()
                break
  
    return os.path.join(directory, filename)

def write(xdoc, out, mtime=None):
    """ write the document out to disk """
    file = open(out,'w')
    file.write(xdoc)
    file.close()
    if mtime: os.utime(out, (mtime, mtime))

def _is_http_uri(uri):
    parsed = urlparse.urlparse(uri)
    return parsed[0] in ['http', 'https']

def writeCache(feed_uri, feed_info, data):
    log = planet.logger
    sources = config.cache_sources_directory()
    blacklist = config.cache_blacklist_directory()

    # capture http status
    if not data.has_key("status"):
        if data.has_key("entries") and len(data.entries)>0:
            data.status = 200
        elif data.bozo and \
            data.bozo_exception.__class__.__name__.lower()=='timeout':
            data.status = 408
        else:
            data.status = 500

    activity_horizon = \
        time.gmtime(time.time()-86400*config.activity_threshold(feed_uri))

    # process based on the HTTP status code
    if data.status == 200 and data.has_key("url"):
        feed_info.feed['planet_http_location'] = data.url
        if data.has_key("entries") and len(data.entries) == 0:
            log.warning("No data %s", feed_uri)
            feed_info.feed['planet_message'] = 'no data'
        elif feed_uri == data.url:
            log.info("Updating feed %s", feed_uri)
        else:
            log.info("Updating feed %s @ %s", feed_uri, data.url)
    elif data.status == 301 and data.has_key("entries") and len(data.entries)>0:
        log.warning("Feed has moved from <%s> to <%s>", feed_uri, data.url)
        data.feed['planet_http_location'] = data.url
    elif data.status == 304 and data.has_key("url"):
        feed_info.feed['planet_http_location'] = data.url
        if feed_uri == data.url:
            log.info("Feed %s unchanged", feed_uri)
        else:
            log.info("Feed %s unchanged @ %s", feed_uri, data.url)

        if not feed_info.feed.has_key('planet_message'):
            if feed_info.feed.has_key('planet_updated'):
                updated = feed_info.feed.planet_updated
                if feedparser._parse_date_iso8601(updated) >= activity_horizon:
                    return
        else:
            if feed_info.feed.planet_message.startswith("no activity in"):
               return
            if not feed_info.feed.planet_message.startswith("duplicate") and \
               not feed_info.feed.planet_message.startswith("no data"):
               del feed_info.feed['planet_message']

    elif data.status == 410:
        log.info("Feed %s gone", feed_uri)
    elif data.status == 408:
        log.warning("Feed %s timed out", feed_uri)
    elif data.status >= 400:
        log.error("Error %d while updating feed %s", data.status, feed_uri)
    else:
        log.info("Updating feed %s", feed_uri)

    # if read failed, retain cached information
    if not data.get('version') and feed_info.get('version'):
        data.feed = feed_info.feed
        data.bozo = feed_info.feed.get('planet_bozo','true') == 'true'
        data.version = feed_info.feed.get('planet_format')
    data.feed['planet_http_status'] = str(data.status)

    # capture etag and last-modified information
    if data.has_key('headers'):
        if data.has_key('etag') and data.etag:
            data.feed['planet_http_etag'] = data.etag
        elif data.headers.has_key('etag') and data.headers['etag']:
            data.feed['planet_http_etag'] =  data.headers['etag']

        if data.headers.has_key('last-modified'):
            data.feed['planet_http_last_modified']=data.headers['last-modified']
        elif data.has_key('modified') and data.modified:
            data.feed['planet_http_last_modified'] = time.asctime(data.modified)

        if data.headers.has_key('-content-hash'):
            data.feed['planet_content_hash'] = data.headers['-content-hash']

    # capture feed and data from the planet configuration file
    if data.get('version'):
        if not data.feed.has_key('links'): data.feed['links'] = list()
        feedtype = 'application/atom+xml'
        if data.version.startswith('rss'): feedtype = 'application/rss+xml'
        if data.version in ['rss090','rss10']: feedtype = 'application/rdf+xml'
        for link in data.feed.links:
            if link.rel == 'self':
                link['type'] = feedtype
                break
        else:
            data.feed.links.append(feedparser.FeedParserDict(
                {'rel':'self', 'type':feedtype, 'href':feed_uri}))
    for name, value in config.feed_options(feed_uri).items():
        data.feed['planet_'+name] = value

    # perform user configured scrub operations on the data
    scrub.scrub(feed_uri, data)

    from planet import idindex
    global index
    if index != None: index = idindex.open()
 
    # select latest entry for each unique id
    ids = {}
    for entry in data.entries:
        # generate an id, if none is present
        if not entry.has_key('id') or not entry.id:
            entry['id'] = reconstitute.id(None, entry)
            if not entry['id']: continue

        # determine updated date for purposes of selection
        updated = ''
        if entry.has_key('published'): updated=entry.published
        if entry.has_key('updated'):   updated=entry.updated

        # if not seen or newer than last seen, select it
        if updated >= ids.get(entry.id,('',))[0]:
            ids[entry.id] = (updated, entry)

    # write each entry to the cache
    cache = config.cache_directory()
    for updated, entry in ids.values():

        # compute blacklist file name based on the id
        blacklist_file = filename(blacklist, entry.id)  

        # check if blacklist file exists. If so, skip it. 
        if os.path.exists(blacklist_file):
           continue

        # compute cache file name based on the id
        cache_file = filename(cache, entry.id)

        # get updated-date either from the entry or the cache (default to now)
        mtime = None
        if not entry.has_key('updated_parsed') or not entry['updated_parsed']:
            entry['updated_parsed'] = entry.get('published_parsed',None)
        if entry.has_key('updated_parsed'):
            try:
                mtime = calendar.timegm(entry.updated_parsed)
            except:
                pass
        if not mtime:
            try:
                mtime = os.stat(cache_file).st_mtime
            except:
                if data.feed.has_key('updated_parsed'):
                    try:
                        mtime = calendar.timegm(data.feed.updated_parsed)
                    except:
                        pass
        if not mtime: mtime = time.time()
        entry['updated_parsed'] = time.gmtime(mtime)

        # apply any filters
        xdoc = reconstitute.reconstitute(data, entry)
        output = xdoc.toxml().encode('utf-8')
        xdoc.unlink()
        for filter in config.filters(feed_uri):
            output = shell.run(filter, output, mode="filter")
            if not output: break
        if not output:
          if os.path.exists(cache_file): os.remove(cache_file)
          continue

        # write out and timestamp the results
        write(output, cache_file, mtime) 
    
        # optionally index
        if index != None: 
            feedid = data.feed.get('id', data.feed.get('link',None))
            if feedid:
                if type(feedid) == unicode: feedid = feedid.encode('utf-8')
                index[filename('', entry.id)] = feedid

    if index: index.close()

    # identify inactive feeds
    if config.activity_threshold(feed_uri):
        updated = [entry.updated_parsed for entry in data.entries
            if entry.has_key('updated_parsed')]
        updated.sort()

        if updated:
            data.feed['planet_updated'] = \
                time.strftime("%Y-%m-%dT%H:%M:%SZ", updated[-1])
        elif data.feed.has_key('planet_updated'):
           updated = [feedparser._parse_date_iso8601(data.feed.planet_updated)]

        if not updated or updated[-1] < activity_horizon:
            msg = "no activity in %d days" % config.activity_threshold(feed_uri)
            log.info(msg)
            data.feed['planet_message'] = msg

    # report channel level errors
    if data.status == 226:
        if data.feed.has_key('planet_message'): del data.feed['planet_message']
        if feed_info.feed.has_key('planet_updated'):
            data.feed['planet_updated'] = feed_info.feed['planet_updated']
    elif data.status == 403:
        data.feed['planet_message'] = "403: forbidden"
    elif data.status == 404:
        data.feed['planet_message'] = "404: not found"
    elif data.status == 408:
        data.feed['planet_message'] = "408: request timeout"
    elif data.status == 410:
        data.feed['planet_message'] = "410: gone"
    elif data.status == 500:
        data.feed['planet_message'] = "internal server error"
    elif data.status >= 400:
        data.feed['planet_message'] = "http status %s" % data.status

    # write the feed info to the cache
    if not os.path.exists(sources): os.makedirs(sources)
    xdoc=minidom.parseString('''<feed xmlns:planet="%s"
      xmlns="http://www.w3.org/2005/Atom"/>\n''' % planet.xmlns)
    reconstitute.source(xdoc.documentElement,data.feed,data.bozo, data.get('version'))
    write(xdoc.toxml().encode('utf-8'), filename(sources, feed_uri))
    xdoc.unlink()

def httpThread(thread_index, input_queue, output_queue, log):
    import httplib2
    from httplib import BadStatusLine

    h = httplib2.Http(config.http_cache_directory())
    uri, feed_info = input_queue.get(block=True)
    while uri:
        log.info("Fetching %s via %d", uri, thread_index)
        feed = StringIO('')
        setattr(feed, 'url', uri)
        setattr(feed, 'headers', 
            feedparser.FeedParserDict({'status':'500'}))
        try:
            # map IRI => URI
            try:
                if isinstance(uri,unicode):
                    idna = uri.encode('idna')
                else:
                    idna = uri.decode('utf-8').encode('idna')
                if idna != uri: log.info("IRI %s mapped to %s", uri, idna)
            except:
                log.info("unable to map %s to a URI", uri)
                idna = uri

            # cache control headers
            headers = {}
            if feed_info.feed.has_key('planet_http_etag'):
                headers['If-None-Match'] = feed_info.feed['planet_http_etag']
            if feed_info.feed.has_key('planet_http_last_modified'):
                headers['If-Modified-Since'] = \
                    feed_info.feed['planet_http_last_modified']

            # issue request
            (resp, content) = h.request(idna, 'GET', headers=headers)

            # unchanged detection
            resp['-content-hash'] = md5(content or '').hexdigest()
            if resp.status == 200:
                if resp.fromcache:
                    resp.status = 304
                elif feed_info.feed.has_key('planet_content_hash') and \
                    feed_info.feed['planet_content_hash'] == \
                    resp['-content-hash']:
                    resp.status = 304

            # build a file-like object
            feed = StringIO(content) 
            setattr(feed, 'url', resp.get('content-location', uri))
            if resp.has_key('content-encoding'):
                del resp['content-encoding']
            setattr(feed, 'headers', resp)
        except BadStatusLine:
            log.error("Bad Status Line received for %s via %d",
                uri, thread_index)
        except httplib2.HttpLib2Error, e:
            log.error("HttpLib2Error: %s via %d", str(e), thread_index)
        except socket.error, e:
            if e.__class__.__name__.lower()=='timeout':
                feed.headers['status'] = '408'
                log.warn("Timeout in thread-%d", thread_index)
            else:
                log.error("HTTP Error: %s in thread-%d", str(e), thread_index)
        except Exception, e:
            import sys, traceback
            type, value, tb = sys.exc_info()
            log.error('Error processing %s', uri)
            for line in (traceback.format_exception_only(type, value) +
                traceback.format_tb(tb)):
                log.error(line.rstrip())

        output_queue.put(block=True, item=(uri, feed_info, feed))
        uri, feed_info = input_queue.get(block=True)

def spiderPlanet(only_if_new = False):
    """ Spider (fetch) an entire planet """
    log = planet.logger

    global index
    index = True

    timeout = config.feed_timeout()
    try:
        socket.setdefaulttimeout(float(timeout))
        log.info("Socket timeout set to %d seconds", timeout)
    except:
        try:
            import timeoutsocket
            timeoutsocket.setDefaultSocketTimeout(float(timeout))
            log.info("Socket timeout set to %d seconds", timeout)
        except:
            log.warning("Timeout set to invalid value '%s', skipping", timeout)

    from Queue import Queue
    from threading import Thread

    fetch_queue = Queue()
    parse_queue = Queue()

    threads = {}
    http_cache = config.http_cache_directory()
    # Should this be done in config?
    if http_cache and not os.path.exists(http_cache):
        os.makedirs(http_cache)


    if int(config.spider_threads()):
        # Start all the worker threads
        for i in range(int(config.spider_threads())):
            threads[i] = Thread(target=httpThread,
                args=(i,fetch_queue, parse_queue, log))
            threads[i].start()
    else:
        log.info("Building work queue")

    # Load the fetch and parse work queues
    for uri in config.subscriptions():
        # read cached feed info
        sources = config.cache_sources_directory()
        feed_source = filename(sources, uri)
        feed_info = feedparser.parse(feed_source)

        if feed_info.feed and only_if_new:
            log.info("Feed %s already in cache", uri)
            continue
        if feed_info.feed.get('planet_http_status',None) == '410':
            log.info("Feed %s gone", uri)
            continue

        if threads and _is_http_uri(uri):
            fetch_queue.put(item=(uri, feed_info))
        else:
            parse_queue.put(item=(uri, feed_info, uri))

    # Mark the end of the fetch queue
    for thread in threads.keys():
        fetch_queue.put(item=(None, None))

    # Process the results as they arrive
    feeds_seen = {}
    while fetch_queue.qsize() or parse_queue.qsize() or threads:
        while parse_queue.qsize():
            (uri, feed_info, feed) = parse_queue.get(False)
            try:

                if not hasattr(feed,'headers') or int(feed.headers.status)<300:
                    options = {}
                    if hasattr(feed_info,'feed'):
                        options['etag'] = \
                            feed_info.feed.get('planet_http_etag',None)
                        try:
                            modified=time.strptime(
                                feed_info.feed.get('planet_http_last_modified',
                                None))
                        except:
                            pass

                    data = feedparser.parse(feed, **options)
                else:
                    data = feedparser.FeedParserDict({'version': None,
                        'headers': feed.headers, 'entries': [], 'feed': {},
                        'href': feed.url, 'bozo': 0,
                        'status': int(feed.headers.status)})

                # duplicate feed?
                id = data.feed.get('id', None)
                if not id: id = feed_info.feed.get('id', None)

                href=uri
                if data.has_key('href'): href=data.href

                duplicate = None
                if id and id in feeds_seen:
                   duplicate = id
                elif href and href in feeds_seen:
                   duplicate = href

                if duplicate:
                    feed_info.feed['planet_message'] = \
                        'duplicate subscription: ' + feeds_seen[duplicate]
                    log.warn('Duplicate subscription: %s and %s' %
                        (uri, feeds_seen[duplicate]))
                    if href: feed_info.feed['planet_http_location'] = href

                if id: feeds_seen[id] = uri
                if href: feeds_seen[href] = uri

                # complete processing for the feed
                writeCache(uri, feed_info, data)

            except Exception, e:
                import sys, traceback
                type, value, tb = sys.exc_info()
                log.error('Error processing %s', uri)
                for line in (traceback.format_exception_only(type, value) +
                    traceback.format_tb(tb)):
                    log.error(line.rstrip())

        time.sleep(0.1)

        for index in threads.keys():
            if not threads[index].isAlive():
                del threads[index]
                if not threads:
                    log.info("Finished threaded part of processing.")

########NEW FILE########
__FILENAME__ = splice
""" Splice together a planet from a cache of feed entries """
import glob, os, time, shutil
from xml.dom import minidom
import planet, config, feedparser, reconstitute, shell
from reconstitute import createTextElement, date
from spider import filename
from planet import idindex

def splice():
    """ Splice together a planet from a cache of entries """
    import planet
    log = planet.logger

    log.info("Loading cached data")
    cache = config.cache_directory()
    dir=[(os.stat(file).st_mtime,file) for file in glob.glob(cache+"/*")
        if not os.path.isdir(file)]
    dir.sort()
    dir.reverse()

    max_items=max([config.items_per_page(templ)
        for templ in config.template_files() or ['Planet']])

    doc = minidom.parseString('<feed xmlns="http://www.w3.org/2005/Atom"/>')
    feed = doc.documentElement

    # insert feed information
    createTextElement(feed, 'title', config.name())
    date(feed, 'updated', time.gmtime())    
    gen = createTextElement(feed, 'generator', config.generator())
    gen.setAttribute('uri', config.generator_uri())

    author = doc.createElement('author')
    createTextElement(author, 'name', config.owner_name())
    createTextElement(author, 'email', config.owner_email())
    feed.appendChild(author)

    if config.feed():
        createTextElement(feed, 'id', config.feed())
        link = doc.createElement('link')
        link.setAttribute('rel', 'self')
        link.setAttribute('href', config.feed())
        if config.feedtype():
            link.setAttribute('type', "application/%s+xml" % config.feedtype())
        feed.appendChild(link)

    if config.pubsubhubbub_hub():
        hub = doc.createElement('link')
        hub.setAttribute('rel', 'hub')
        hub.setAttribute('href', config.pubsubhubbub_hub())
        feed.appendChild(hub)

    if config.link():
        link = doc.createElement('link')
        link.setAttribute('rel', 'alternate')
        link.setAttribute('href', config.link())
        feed.appendChild(link)

    # insert subscription information
    sub_ids = []
    feed.setAttribute('xmlns:planet',planet.xmlns)
    sources = config.cache_sources_directory()
    for sub in config.subscriptions():
        data=feedparser.parse(filename(sources,sub))
        if data.feed.has_key('id'): sub_ids.append(data.feed.id)
        if not data.feed: continue

        # warn on missing links
        if not data.feed.has_key('planet_message'):
            if not data.feed.has_key('links'): data.feed['links'] = []

            for link in data.feed.links:
              if link.rel == 'self': break
            else:
              log.debug('missing self link for ' + sub)

            for link in data.feed.links:
              if link.rel == 'alternate' and 'html' in link.type: break
            else:
              log.debug('missing html link for ' + sub)

        xdoc=minidom.parseString('''<planet:source xmlns:planet="%s"
             xmlns="http://www.w3.org/2005/Atom"/>\n''' % planet.xmlns)
        reconstitute.source(xdoc.documentElement, data.feed, None, None)
        feed.appendChild(xdoc.documentElement)

    index = idindex.open()

    # insert entry information
    items = 0
    count = {}
    atomNS='http://www.w3.org/2005/Atom'
    new_feed_items = config.new_feed_items()
    for mtime,file in dir:
        if index != None:
            base = os.path.basename(file)
            if index.has_key(base) and index[base] not in sub_ids: continue

        try:
            entry=minidom.parse(file)

            # verify that this entry is currently subscribed to and that the
            # number of entries contributed by this feed does not exceed
            # config.new_feed_items
            entry.normalize()
            sources = entry.getElementsByTagNameNS(atomNS, 'source')
            if sources:
                ids = sources[0].getElementsByTagName('id')
                if ids:
                    id = ids[0].childNodes[0].nodeValue
                    count[id] = count.get(id,0) + 1
                    if new_feed_items and count[id] > new_feed_items: continue

                    if id not in sub_ids:
                        ids = sources[0].getElementsByTagName('planet:id')
                        if not ids: continue
                        id = ids[0].childNodes[0].nodeValue
                        if id not in sub_ids:
                          log.warn('Skipping: ' + id)
                        if id not in sub_ids: continue

            # add entry to feed
            feed.appendChild(entry.documentElement)
            items = items + 1
            if items >= max_items: break
        except:
            log.error("Error parsing %s", file)

    if index: index.close()

    return doc

def apply(doc):
    output_dir = config.output_dir()
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    log = planet.logger

    planet_filters = config.filters('Planet')

    # Go-go-gadget-template
    for template_file in config.template_files():
        output_file = shell.run(template_file, doc)

        # run any template specific filters
        if config.filters(template_file) != planet_filters:
            output = open(output_file).read()
            for filter in config.filters(template_file):
                if filter in planet_filters: continue
                if filter.find('>')>0:
                    # tee'd output
                    filter,dest = filter.split('>',1)
                    tee = shell.run(filter.strip(), output, mode="filter")
                    if tee:
                        output_dir = planet.config.output_dir()
                        dest_file = os.path.join(output_dir, dest.strip())
                        dest_file = open(dest_file,'w')
                        dest_file.write(tee)
                        dest_file.close()
                else:
                    # pipe'd output
                    output = shell.run(filter, output, mode="filter")
                    if not output:
                        os.unlink(output_file)
                        break
            else:
                handle = open(output_file,'w')
                handle.write(output)
                handle.close()

    # Process bill of materials
    for copy_file in config.bill_of_materials():
        dest = os.path.join(output_dir, copy_file)
        for template_dir in config.template_directories():
            source = os.path.join(template_dir, copy_file)
            if os.path.exists(source): break
        else:
            log.error('Unable to locate %s', copy_file)
            log.info("Template search path:")
            for template_dir in config.template_directories():
                log.info("    %s", os.path.realpath(template_dir))
            continue

        mtime = os.stat(source).st_mtime
        if not os.path.exists(dest) or os.stat(dest).st_mtime < mtime:
            dest_dir = os.path.split(dest)[0]
            if not os.path.exists(dest_dir): os.makedirs(dest_dir)

            log.info("Copying %s to %s", source, dest)
            if os.path.exists(dest): os.chmod(dest, 0644)
            shutil.copyfile(source, dest)
            shutil.copystat(source, dest)

########NEW FILE########
__FILENAME__ = config
# Copyright 2001-2002 by Vinay Sajip. All Rights Reserved.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation, and that the name of Vinay Sajip
# not be used in advertising or publicity pertaining to distribution
# of the software without specific, written prior permission.
# VINAY SAJIP DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING
# ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# VINAY SAJIP BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR
# ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
# IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Logging package for Python. Based on PEP 282 and comments thereto in
comp.lang.python, and influenced by Apache's log4j system.

Should work under Python versions >= 1.5.2, except that source line
information is not available unless 'inspect' is.

Copyright (C) 2001-2002 Vinay Sajip. All Rights Reserved.

To use, simply 'import logging' and log away!
"""

import sys, logging, logging.handlers, string, thread, threading, socket, struct, os

from SocketServer import ThreadingTCPServer, StreamRequestHandler


DEFAULT_LOGGING_CONFIG_PORT = 9030
if sys.platform == "win32":
    RESET_ERROR = 10054   #WSAECONNRESET
else:
    RESET_ERROR = 104     #ECONNRESET

#
#   The following code implements a socket listener for on-the-fly
#   reconfiguration of logging.
#
#   _listener holds the server object doing the listening
_listener = None

def fileConfig(fname, defaults=None):
    """
    Read the logging configuration from a ConfigParser-format file.

    This can be called several times from an application, allowing an end user
    the ability to select from various pre-canned configurations (if the
    developer provides a mechanism to present the choices and load the chosen
    configuration).
    In versions of ConfigParser which have the readfp method [typically
    shipped in 2.x versions of Python], you can pass in a file-like object
    rather than a filename, in which case the file-like object will be read
    using readfp.
    """
    import ConfigParser

    cp = ConfigParser.ConfigParser(defaults)
    if hasattr(cp, 'readfp') and hasattr(fname, 'readline'):
        cp.readfp(fname)
    else:
        cp.read(fname)
    #first, do the formatters...
    flist = cp.get("formatters", "keys")
    if len(flist):
        flist = string.split(flist, ",")
        formatters = {}
        for form in flist:
            sectname = "formatter_%s" % form
            opts = cp.options(sectname)
            if "format" in opts:
                fs = cp.get(sectname, "format", 1)
            else:
                fs = None
            if "datefmt" in opts:
                dfs = cp.get(sectname, "datefmt", 1)
            else:
                dfs = None
            f = logging.Formatter(fs, dfs)
            formatters[form] = f
    #next, do the handlers...
    #critical section...
    logging._acquireLock()
    try:
        try:
            #first, lose the existing handlers...
            logging._handlers.clear()
            #now set up the new ones...
            hlist = cp.get("handlers", "keys")
            if len(hlist):
                hlist = string.split(hlist, ",")
                handlers = {}
                fixups = [] #for inter-handler references
                for hand in hlist:
                    sectname = "handler_%s" % hand
                    klass = cp.get(sectname, "class")
                    opts = cp.options(sectname)
                    if "formatter" in opts:
                        fmt = cp.get(sectname, "formatter")
                    else:
                        fmt = ""
                    klass = eval(klass, vars(logging))
                    args = cp.get(sectname, "args")
                    args = eval(args, vars(logging))
                    h = apply(klass, args)
                    if "level" in opts:
                        level = cp.get(sectname, "level")
                        h.setLevel(logging._levelNames[level])
                    if len(fmt):
                        h.setFormatter(formatters[fmt])
                    #temporary hack for FileHandler and MemoryHandler.
                    if klass == logging.handlers.MemoryHandler:
                        if "target" in opts:
                            target = cp.get(sectname,"target")
                        else:
                            target = ""
                        if len(target): #the target handler may not be loaded yet, so keep for later...
                            fixups.append((h, target))
                    handlers[hand] = h
                #now all handlers are loaded, fixup inter-handler references...
                for fixup in fixups:
                    h = fixup[0]
                    t = fixup[1]
                    h.setTarget(handlers[t])
            #at last, the loggers...first the root...
            llist = cp.get("loggers", "keys")
            llist = string.split(llist, ",")
            llist.remove("root")
            sectname = "logger_root"
            root = logging.root
            log = root
            opts = cp.options(sectname)
            if "level" in opts:
                level = cp.get(sectname, "level")
                log.setLevel(logging._levelNames[level])
            for h in root.handlers[:]:
                root.removeHandler(h)
            hlist = cp.get(sectname, "handlers")
            if len(hlist):
                hlist = string.split(hlist, ",")
                for hand in hlist:
                    log.addHandler(handlers[hand])
            #and now the others...
            #we don't want to lose the existing loggers,
            #since other threads may have pointers to them.
            #existing is set to contain all existing loggers,
            #and as we go through the new configuration we
            #remove any which are configured. At the end,
            #what's left in existing is the set of loggers
            #which were in the previous configuration but
            #which are not in the new configuration.
            existing = root.manager.loggerDict.keys()
            #now set up the new ones...
            for log in llist:
                sectname = "logger_%s" % log
                qn = cp.get(sectname, "qualname")
                opts = cp.options(sectname)
                if "propagate" in opts:
                    propagate = cp.getint(sectname, "propagate")
                else:
                    propagate = 1
                logger = logging.getLogger(qn)
                if qn in existing:
                    existing.remove(qn)
                if "level" in opts:
                    level = cp.get(sectname, "level")
                    logger.setLevel(logging._levelNames[level])
                for h in logger.handlers[:]:
                    logger.removeHandler(h)
                logger.propagate = propagate
                logger.disabled = 0
                hlist = cp.get(sectname, "handlers")
                if len(hlist):
                    hlist = string.split(hlist, ",")
                    for hand in hlist:
                        logger.addHandler(handlers[hand])
            #Disable any old loggers. There's no point deleting
            #them as other threads may continue to hold references
            #and by disabling them, you stop them doing any logging.
            for log in existing:
                root.manager.loggerDict[log].disabled = 1
        except:
            import traceback
            ei = sys.exc_info()
            traceback.print_exception(ei[0], ei[1], ei[2], None, sys.stderr)
            del ei
    finally:
        logging._releaseLock()

def listen(port=DEFAULT_LOGGING_CONFIG_PORT):
    """
    Start up a socket server on the specified port, and listen for new
    configurations.

    These will be sent as a file suitable for processing by fileConfig().
    Returns a Thread object on which you can call start() to start the server,
    and which you can join() when appropriate. To stop the server, call
    stopListening().
    """
    if not thread:
        raise NotImplementedError, "listen() needs threading to work"

    class ConfigStreamHandler(StreamRequestHandler):
        """
        Handler for a logging configuration request.

        It expects a completely new logging configuration and uses fileConfig
        to install it.
        """
        def handle(self):
            """
            Handle a request.

            Each request is expected to be a 4-byte length,
            followed by the config file. Uses fileConfig() to do the
            grunt work.
            """
            import tempfile
            try:
                conn = self.connection
                chunk = conn.recv(4)
                if len(chunk) == 4:
                    slen = struct.unpack(">L", chunk)[0]
                    chunk = self.connection.recv(slen)
                    while len(chunk) < slen:
                        chunk = chunk + conn.recv(slen - len(chunk))
                    #Apply new configuration. We'd like to be able to
                    #create a StringIO and pass that in, but unfortunately
                    #1.5.2 ConfigParser does not support reading file
                    #objects, only actual files. So we create a temporary
                    #file and remove it later.
                    file = tempfile.mktemp(".ini")
                    f = open(file, "w")
                    f.write(chunk)
                    f.close()
                    fileConfig(file)
                    os.remove(file)
            except socket.error, e:
                if type(e.args) != types.TupleType:
                    raise
                else:
                    errcode = e.args[0]
                    if errcode != RESET_ERROR:
                        raise

    class ConfigSocketReceiver(ThreadingTCPServer):
        """
        A simple TCP socket-based logging config receiver.
        """

        allow_reuse_address = 1

        def __init__(self, host='localhost', port=DEFAULT_LOGGING_CONFIG_PORT,
                     handler=None):
            ThreadingTCPServer.__init__(self, (host, port), handler)
            logging._acquireLock()
            self.abort = 0
            logging._releaseLock()
            self.timeout = 1

        def serve_until_stopped(self):
            import select
            abort = 0
            while not abort:
                rd, wr, ex = select.select([self.socket.fileno()],
                                           [], [],
                                           self.timeout)
                if rd:
                    self.handle_request()
                logging._acquireLock()
                abort = self.abort
                logging._releaseLock()

    def serve(rcvr, hdlr, port):
        server = rcvr(port=port, handler=hdlr)
        global _listener
        logging._acquireLock()
        _listener = server
        logging._releaseLock()
        server.serve_until_stopped()

    return threading.Thread(target=serve,
                            args=(ConfigSocketReceiver,
                                  ConfigStreamHandler, port))

def stopListening():
    """
    Stop the listening server which was created with a call to listen().
    """
    global _listener
    if _listener:
        logging._acquireLock()
        _listener.abort = 1
        _listener = None
        logging._releaseLock()

########NEW FILE########
__FILENAME__ = handlers
# Copyright 2001-2002 by Vinay Sajip. All Rights Reserved.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation, and that the name of Vinay Sajip
# not be used in advertising or publicity pertaining to distribution
# of the software without specific, written prior permission.
# VINAY SAJIP DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING
# ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# VINAY SAJIP BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR
# ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
# IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Logging package for Python. Based on PEP 282 and comments thereto in
comp.lang.python, and influenced by Apache's log4j system.

Should work under Python versions >= 1.5.2, except that source line
information is not available unless 'inspect' is.

Copyright (C) 2001-2002 Vinay Sajip. All Rights Reserved.

To use, simply 'import logging' and log away!
"""

import sys, logging, socket, types, os, string, cPickle, struct, time

from SocketServer import ThreadingTCPServer, StreamRequestHandler

#
# Some constants...
#

DEFAULT_TCP_LOGGING_PORT    = 9020
DEFAULT_UDP_LOGGING_PORT    = 9021
DEFAULT_HTTP_LOGGING_PORT   = 9022
DEFAULT_SOAP_LOGGING_PORT   = 9023
SYSLOG_UDP_PORT             = 514


class RotatingFileHandler(logging.FileHandler):
    def __init__(self, filename, mode="a", maxBytes=0, backupCount=0):
        """
        Open the specified file and use it as the stream for logging.

        By default, the file grows indefinitely. You can specify particular
        values of maxBytes and backupCount to allow the file to rollover at
        a predetermined size.

        Rollover occurs whenever the current log file is nearly maxBytes in
        length. If backupCount is >= 1, the system will successively create
        new files with the same pathname as the base file, but with extensions
        ".1", ".2" etc. appended to it. For example, with a backupCount of 5
        and a base file name of "app.log", you would get "app.log",
        "app.log.1", "app.log.2", ... through to "app.log.5". The file being
        written to is always "app.log" - when it gets filled up, it is closed
        and renamed to "app.log.1", and if files "app.log.1", "app.log.2" etc.
        exist, then they are renamed to "app.log.2", "app.log.3" etc.
        respectively.

        If maxBytes is zero, rollover never occurs.
        """
        logging.FileHandler.__init__(self, filename, mode)
        self.maxBytes = maxBytes
        self.backupCount = backupCount
        if maxBytes > 0:
            self.mode = "a"

    def doRollover(self):
        """
        Do a rollover, as described in __init__().
        """

        self.stream.close()
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = "%s.%d" % (self.baseFilename, i)
                dfn = "%s.%d" % (self.baseFilename, i + 1)
                if os.path.exists(sfn):
                    #print "%s -> %s" % (sfn, dfn)
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.baseFilename + ".1"
            if os.path.exists(dfn):
                os.remove(dfn)
            os.rename(self.baseFilename, dfn)
            #print "%s -> %s" % (self.baseFilename, dfn)
        self.stream = open(self.baseFilename, "w")

    def emit(self, record):
        """
        Emit a record.

        Output the record to the file, catering for rollover as described
        in doRollover().
        """
        if self.maxBytes > 0:                   # are we rolling over?
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)  #due to non-posix-compliant Windows feature
            if self.stream.tell() + len(msg) >= self.maxBytes:
                self.doRollover()
        logging.FileHandler.emit(self, record)


class SocketHandler(logging.Handler):
    """
    A handler class which writes logging records, in pickle format, to
    a streaming socket. The socket is kept open across logging calls.
    If the peer resets it, an attempt is made to reconnect on the next call.
    The pickle which is sent is that of the LogRecord's attribute dictionary
    (__dict__), so that the receiver does not need to have the logging module
    installed in order to process the logging event.

    To unpickle the record at the receiving end into a LogRecord, use the
    makeLogRecord function.
    """

    def __init__(self, host, port):
        """
        Initializes the handler with a specific host address and port.

        The attribute 'closeOnError' is set to 1 - which means that if
        a socket error occurs, the socket is silently closed and then
        reopened on the next logging call.
        """
        logging.Handler.__init__(self)
        self.host = host
        self.port = port
        self.sock = None
        self.closeOnError = 0

    def makeSocket(self):
        """
        A factory method which allows subclasses to define the precise
        type of socket they want.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        return s

    def send(self, s):
        """
        Send a pickled string to the socket.

        This function allows for partial sends which can happen when the
        network is busy.
        """
        if hasattr(self.sock, "sendall"):
            self.sock.sendall(s)
        else:
            sentsofar = 0
            left = len(s)
            while left > 0:
                sent = self.sock.send(s[sentsofar:])
                sentsofar = sentsofar + sent
                left = left - sent

    def makePickle(self, record):
        """
        Pickles the record in binary format with a length prefix, and
        returns it ready for transmission across the socket.
        """
        s = cPickle.dumps(record.__dict__, 1)
        #n = len(s)
        #slen = "%c%c" % ((n >> 8) & 0xFF, n & 0xFF)
        slen = struct.pack(">L", len(s))
        return slen + s

    def handleError(self, record):
        """
        Handle an error during logging.

        An error has occurred during logging. Most likely cause -
        connection lost. Close the socket so that we can retry on the
        next event.
        """
        if self.closeOnError and self.sock:
            self.sock.close()
            self.sock = None        #try to reconnect next time
        else:
            logging.Handler.handleError(self, record)

    def emit(self, record):
        """
        Emit a record.

        Pickles the record and writes it to the socket in binary format.
        If there is an error with the socket, silently drop the packet.
        If there was a problem with the socket, re-establishes the
        socket.
        """
        try:
            s = self.makePickle(record)
            if not self.sock:
                self.sock = self.makeSocket()
            self.send(s)
        except:
            self.handleError(record)

    def close(self):
        """
        Closes the socket.
        """
        if self.sock:
            self.sock.close()
            self.sock = None

class DatagramHandler(SocketHandler):
    """
    A handler class which writes logging records, in pickle format, to
    a datagram socket.  The pickle which is sent is that of the LogRecord's
    attribute dictionary (__dict__), so that the receiver does not need to
    have the logging module installed in order to process the logging event.

    To unpickle the record at the receiving end into a LogRecord, use the
    makeLogRecord function.

    """
    def __init__(self, host, port):
        """
        Initializes the handler with a specific host address and port.
        """
        SocketHandler.__init__(self, host, port)
        self.closeOnError = 0

    def makeSocket(self):
        """
        The factory method of SocketHandler is here overridden to create
        a UDP socket (SOCK_DGRAM).
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return s

    def send(self, s):
        """
        Send a pickled string to a socket.

        This function no longer allows for partial sends which can happen
        when the network is busy - UDP does not guarantee delivery and
        can deliver packets out of sequence.
        """
        self.sock.sendto(s, (self.host, self.port))

class SysLogHandler(logging.Handler):
    """
    A handler class which sends formatted logging records to a syslog
    server. Based on Sam Rushing's syslog module:
    http://www.nightmare.com/squirl/python-ext/misc/syslog.py
    Contributed by Nicolas Untz (after which minor refactoring changes
    have been made).
    """

    # from <linux/sys/syslog.h>:
    # ======================================================================
    # priorities/facilities are encoded into a single 32-bit quantity, where
    # the bottom 3 bits are the priority (0-7) and the top 28 bits are the
    # facility (0-big number). Both the priorities and the facilities map
    # roughly one-to-one to strings in the syslogd(8) source code.  This
    # mapping is included in this file.
    #
    # priorities (these are ordered)

    LOG_EMERG     = 0       #  system is unusable
    LOG_ALERT     = 1       #  action must be taken immediately
    LOG_CRIT      = 2       #  critical conditions
    LOG_ERR       = 3       #  error conditions
    LOG_WARNING   = 4       #  warning conditions
    LOG_NOTICE    = 5       #  normal but significant condition
    LOG_INFO      = 6       #  informational
    LOG_DEBUG     = 7       #  debug-level messages

    #  facility codes
    LOG_KERN      = 0       #  kernel messages
    LOG_USER      = 1       #  random user-level messages
    LOG_MAIL      = 2       #  mail system
    LOG_DAEMON    = 3       #  system daemons
    LOG_AUTH      = 4       #  security/authorization messages
    LOG_SYSLOG    = 5       #  messages generated internally by syslogd
    LOG_LPR       = 6       #  line printer subsystem
    LOG_NEWS      = 7       #  network news subsystem
    LOG_UUCP      = 8       #  UUCP subsystem
    LOG_CRON      = 9       #  clock daemon
    LOG_AUTHPRIV  = 10  #  security/authorization messages (private)

    #  other codes through 15 reserved for system use
    LOG_LOCAL0    = 16      #  reserved for local use
    LOG_LOCAL1    = 17      #  reserved for local use
    LOG_LOCAL2    = 18      #  reserved for local use
    LOG_LOCAL3    = 19      #  reserved for local use
    LOG_LOCAL4    = 20      #  reserved for local use
    LOG_LOCAL5    = 21      #  reserved for local use
    LOG_LOCAL6    = 22      #  reserved for local use
    LOG_LOCAL7    = 23      #  reserved for local use

    priority_names = {
        "alert":    LOG_ALERT,
        "crit":     LOG_CRIT,
        "critical": LOG_CRIT,
        "debug":    LOG_DEBUG,
        "emerg":    LOG_EMERG,
        "err":      LOG_ERR,
        "error":    LOG_ERR,        #  DEPRECATED
        "info":     LOG_INFO,
        "notice":   LOG_NOTICE,
        "panic":    LOG_EMERG,      #  DEPRECATED
        "warn":     LOG_WARNING,    #  DEPRECATED
        "warning":  LOG_WARNING,
        }

    facility_names = {
        "auth":     LOG_AUTH,
        "authpriv": LOG_AUTHPRIV,
        "cron":     LOG_CRON,
        "daemon":   LOG_DAEMON,
        "kern":     LOG_KERN,
        "lpr":      LOG_LPR,
        "mail":     LOG_MAIL,
        "news":     LOG_NEWS,
        "security": LOG_AUTH,       #  DEPRECATED
        "syslog":   LOG_SYSLOG,
        "user":     LOG_USER,
        "uucp":     LOG_UUCP,
        "local0":   LOG_LOCAL0,
        "local1":   LOG_LOCAL1,
        "local2":   LOG_LOCAL2,
        "local3":   LOG_LOCAL3,
        "local4":   LOG_LOCAL4,
        "local5":   LOG_LOCAL5,
        "local6":   LOG_LOCAL6,
        "local7":   LOG_LOCAL7,
        }

    def __init__(self, address=('localhost', SYSLOG_UDP_PORT), facility=LOG_USER):
        """
        Initialize a handler.

        If address is specified as a string, UNIX socket is used.
        If facility is not specified, LOG_USER is used.
        """
        logging.Handler.__init__(self)

        self.address = address
        self.facility = facility
        if type(address) == types.StringType:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            # syslog may require either DGRAM or STREAM sockets
            try:
                self.socket.connect(address)
            except socket.error:
                self.socket.close()
                self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(address)
            self.unixsocket = 1
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.unixsocket = 0

        self.formatter = None

    # curious: when talking to the unix-domain '/dev/log' socket, a
    #   zero-terminator seems to be required.  this string is placed
    #   into a class variable so that it can be overridden if
    #   necessary.
    log_format_string = '<%d>%s\000'

    def encodePriority (self, facility, priority):
        """
        Encode the facility and priority. You can pass in strings or
        integers - if strings are passed, the facility_names and
        priority_names mapping dictionaries are used to convert them to
        integers.
        """
        if type(facility) == types.StringType:
            facility = self.facility_names[facility]
        if type(priority) == types.StringType:
            priority = self.priority_names[priority]
        return (facility << 3) | priority

    def close (self):
        """
        Closes the socket.
        """
        if self.unixsocket:
            self.socket.close()

    def emit(self, record):
        """
        Emit a record.

        The record is formatted, and then sent to the syslog server. If
        exception information is present, it is NOT sent to the server.
        """
        msg = self.format(record)
        """
        We need to convert record level to lowercase, maybe this will
        change in the future.
        """
        msg = self.log_format_string % (
            self.encodePriority(self.facility,
                                string.lower(record.levelname)),
            msg)
        try:
            if self.unixsocket:
                self.socket.send(msg)
            else:
                self.socket.sendto(msg, self.address)
        except:
            self.handleError(record)

class SMTPHandler(logging.Handler):
    """
    A handler class which sends an SMTP email for each logging event.
    """
    def __init__(self, mailhost, fromaddr, toaddrs, subject):
        """
        Initialize the handler.

        Initialize the instance with the from and to addresses and subject
        line of the email. To specify a non-standard SMTP port, use the
        (host, port) tuple format for the mailhost argument.
        """
        logging.Handler.__init__(self)
        if type(mailhost) == types.TupleType:
            host, port = mailhost
            self.mailhost = host
            self.mailport = port
        else:
            self.mailhost = mailhost
            self.mailport = None
        self.fromaddr = fromaddr
        if type(toaddrs) == types.StringType:
            toaddrs = [toaddrs]
        self.toaddrs = toaddrs
        self.subject = subject

    def getSubject(self, record):
        """
        Determine the subject for the email.

        If you want to specify a subject line which is record-dependent,
        override this method.
        """
        return self.subject

    weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    monthname = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def date_time(self):
        """Return the current date and time formatted for a MIME header."""
        year, month, day, hh, mm, ss, wd, y, z = time.gmtime(time.time())
        s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
                self.weekdayname[wd],
                day, self.monthname[month], year,
                hh, mm, ss)
        return s

    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified addressees.
        """
        try:
            import smtplib
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port)
            msg = self.format(record)
            msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\nDate: %s\r\n\r\n%s" % (
                            self.fromaddr,
                            string.join(self.toaddrs, ","),
                            self.getSubject(record),
                            self.date_time(), msg)
            smtp.sendmail(self.fromaddr, self.toaddrs, msg)
            smtp.quit()
        except:
            self.handleError(record)

class NTEventLogHandler(logging.Handler):
    """
    A handler class which sends events to the NT Event Log. Adds a
    registry entry for the specified application name. If no dllname is
    provided, win32service.pyd (which contains some basic message
    placeholders) is used. Note that use of these placeholders will make
    your event logs big, as the entire message source is held in the log.
    If you want slimmer logs, you have to pass in the name of your own DLL
    which contains the message definitions you want to use in the event log.
    """
    def __init__(self, appname, dllname=None, logtype="Application"):
        logging.Handler.__init__(self)
        try:
            import win32evtlogutil, win32evtlog
            self.appname = appname
            self._welu = win32evtlogutil
            if not dllname:
                dllname = os.path.split(self._welu.__file__)
                dllname = os.path.split(dllname[0])
                dllname = os.path.join(dllname[0], r'win32service.pyd')
            self.dllname = dllname
            self.logtype = logtype
            self._welu.AddSourceToRegistry(appname, dllname, logtype)
            self.deftype = win32evtlog.EVENTLOG_ERROR_TYPE
            self.typemap = {
                logging.DEBUG   : win32evtlog.EVENTLOG_INFORMATION_TYPE,
                logging.INFO    : win32evtlog.EVENTLOG_INFORMATION_TYPE,
                logging.WARNING : win32evtlog.EVENTLOG_WARNING_TYPE,
                logging.ERROR   : win32evtlog.EVENTLOG_ERROR_TYPE,
                logging.CRITICAL: win32evtlog.EVENTLOG_ERROR_TYPE,
         }
        except ImportError:
            print "The Python Win32 extensions for NT (service, event "\
                        "logging) appear not to be available."
            self._welu = None

    def getMessageID(self, record):
        """
        Return the message ID for the event record. If you are using your
        own messages, you could do this by having the msg passed to the
        logger being an ID rather than a formatting string. Then, in here,
        you could use a dictionary lookup to get the message ID. This
        version returns 1, which is the base message ID in win32service.pyd.
        """
        return 1

    def getEventCategory(self, record):
        """
        Return the event category for the record.

        Override this if you want to specify your own categories. This version
        returns 0.
        """
        return 0

    def getEventType(self, record):
        """
        Return the event type for the record.

        Override this if you want to specify your own types. This version does
        a mapping using the handler's typemap attribute, which is set up in
        __init__() to a dictionary which contains mappings for DEBUG, INFO,
        WARNING, ERROR and CRITICAL. If you are using your own levels you will
        either need to override this method or place a suitable dictionary in
        the handler's typemap attribute.
        """
        return self.typemap.get(record.levelno, self.deftype)

    def emit(self, record):
        """
        Emit a record.

        Determine the message ID, event category and event type. Then
        log the message in the NT event log.
        """
        if self._welu:
            try:
                id = self.getMessageID(record)
                cat = self.getEventCategory(record)
                type = self.getEventType(record)
                msg = self.format(record)
                self._welu.ReportEvent(self.appname, id, cat, type, [msg])
            except:
                self.handleError(record)

    def close(self):
        """
        Clean up this handler.

        You can remove the application name from the registry as a
        source of event log entries. However, if you do this, you will
        not be able to see the events as you intended in the Event Log
        Viewer - it needs to be able to access the registry to get the
        DLL name.
        """
        #self._welu.RemoveSourceFromRegistry(self.appname, self.logtype)
        pass

class HTTPHandler(logging.Handler):
    """
    A class which sends records to a Web server, using either GET or
    POST semantics.
    """
    def __init__(self, host, url, method="GET"):
        """
        Initialize the instance with the host, the request URL, and the method
        ("GET" or "POST")
        """
        logging.Handler.__init__(self)
        method = string.upper(method)
        if method not in ["GET", "POST"]:
            raise ValueError, "method must be GET or POST"
        self.host = host
        self.url = url
        self.method = method

    def mapLogRecord(self, record):
        """
        Default implementation of mapping the log record into a dict
        that is send as the CGI data. Overwrite in your class.
        Contributed by Franz  Glasner.
        """
        return record.__dict__

    def emit(self, record):
        """
        Emit a record.

        Send the record to the Web server as an URL-encoded dictionary
        """
        try:
            import httplib, urllib
            h = httplib.HTTP(self.host)
            url = self.url
            data = urllib.urlencode(self.mapLogRecord(record))
            if self.method == "GET":
                if (string.find(url, '?') >= 0):
                    sep = '&'
                else:
                    sep = '?'
                url = url + "%c%s" % (sep, data)
            h.putrequest(self.method, url)
            if self.method == "POST":
                h.putheader("Content-length", str(len(data)))
            h.endheaders()
            if self.method == "POST":
                h.send(data)
            h.getreply()    #can't do anything with the result
        except:
            self.handleError(record)

class BufferingHandler(logging.Handler):
    """
  A handler class which buffers logging records in memory. Whenever each
  record is added to the buffer, a check is made to see if the buffer should
  be flushed. If it should, then flush() is expected to do what's needed.
    """
    def __init__(self, capacity):
        """
        Initialize the handler with the buffer size.
        """
        logging.Handler.__init__(self)
        self.capacity = capacity
        self.buffer = []

    def shouldFlush(self, record):
        """
        Should the handler flush its buffer?

        Returns true if the buffer is up to capacity. This method can be
        overridden to implement custom flushing strategies.
        """
        return (len(self.buffer) >= self.capacity)

    def emit(self, record):
        """
        Emit a record.

        Append the record. If shouldFlush() tells us to, call flush() to process
        the buffer.
        """
        self.buffer.append(record)
        if self.shouldFlush(record):
            self.flush()

    def flush(self):
        """
        Override to implement custom flushing behaviour.

        This version just zaps the buffer to empty.
        """
        self.buffer = []

class MemoryHandler(BufferingHandler):
    """
    A handler class which buffers logging records in memory, periodically
    flushing them to a target handler. Flushing occurs whenever the buffer
    is full, or when an event of a certain severity or greater is seen.
    """
    def __init__(self, capacity, flushLevel=logging.ERROR, target=None):
        """
        Initialize the handler with the buffer size, the level at which
        flushing should occur and an optional target.

        Note that without a target being set either here or via setTarget(),
        a MemoryHandler is no use to anyone!
        """
        BufferingHandler.__init__(self, capacity)
        self.flushLevel = flushLevel
        self.target = target

    def shouldFlush(self, record):
        """
        Check for buffer full or a record at the flushLevel or higher.
        """
        return (len(self.buffer) >= self.capacity) or \
                (record.levelno >= self.flushLevel)

    def setTarget(self, target):
        """
        Set the target handler for this handler.
        """
        self.target = target

    def flush(self):
        """
        For a MemoryHandler, flushing means just sending the buffered
        records to the target, if there is one. Override if you want
        different behaviour.
        """
        if self.target:
            for record in self.buffer:
                self.target.handle(record)
            self.buffer = []

    def close(self):
        """
        Flush, set the target to None and lose the buffer.
        """
        self.flush()
        self.target = None
        self.buffer = []

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

__version__ = "4.2-pre-" + "$Revision: 314 $"[11:14] + "-svn"
__license__ = """Copyright (c) 2002-2008, Mark Pilgrim, All rights reserved.

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
                    "Kevin Marks <http://epeus.blogspot.com/>",
                    "Sam Ruby <http://intertwingly.net/>",
                    "Ade Oshineye <http://blog.oshineye.com/>"]
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

# If you want feedparser to automatically resolve all relative URIs, set this
# to 1.
RESOLVE_RELATIVE_URIS = 1

# If you want feedparser to automatically sanitize all potentially unsafe
# HTML content, set this to 1.
SANITIZE_HTML = 1

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
    def _xmlescape(data,entities={}):
        data = data.replace('&', '&amp;')
        data = data.replace('>', '&gt;')
        data = data.replace('<', '&lt;')
        for char, entity in entities:
            data = data.replace(char, entity)
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

# reversable htmlentitydefs mappings for Python 2.2
try:
  from htmlentitydefs import name2codepoint, codepoint2name
except:
  import htmlentitydefs
  name2codepoint={}
  codepoint2name={}
  for (name,codepoint) in htmlentitydefs.entitydefs.iteritems():
    if codepoint.startswith('&#'): codepoint=unichr(int(codepoint[2:-1]))
    name2codepoint[name]=ord(codepoint)
    codepoint2name[ord(codepoint)]=name

# BeautifulSoup parser used for parsing microformats from embedded HTML content
# http://www.crummy.com/software/BeautifulSoup/
# feedparser is tested with BeautifulSoup 3.0.x, but it might work with the
# older 2.x series.  If it doesn't, and you can figure out why, I'll accept a
# patch and modify the compatibility statement accordingly.
try:
    import BeautifulSoup
except:
    BeautifulSoup = None

# ---------- don't touch these ----------
class ThingsNobodyCaresAboutButMe(Exception): pass
class CharacterEncodingOverride(ThingsNobodyCaresAboutButMe): pass
class CharacterEncodingUnknown(ThingsNobodyCaresAboutButMe): pass
class NonXMLContentType(ThingsNobodyCaresAboutButMe): pass
class UndeclaredNamespace(Exception): pass

sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
sgmllib.special = re.compile('<!')
sgmllib.charref = re.compile('&#(\d+|x[0-9a-fA-F]+);')

if sgmllib.endbracket.search(' <').start(0):
    class EndBracketMatch:
        endbracket = re.compile('''([^'"<>]|"[^"]*"(?=>|/|\s|\w+=)|'[^']*'(?=>|/|\s|\w+=))*(?=[<>])|.*?(?=[<>])''')
        def search(self,string,index=0):
            self.match = self.endbracket.match(string,index)
            if self.match: return self
        def start(self,n):
            return self.match.end(n)
    sgmllib.endbracket = EndBracketMatch()

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
        if key == 'enclosures':
            norel = lambda link: FeedParserDict([(name,value) for (name,value) in link.items() if name!='rel'])
            return [norel(link) for link in UserDict.__getitem__(self, 'links') if link['rel']=='enclosure']
        if key == 'license':
            for link in UserDict.__getitem__(self, 'links'):
                if link['rel']=='license' and link.has_key('href'):
                    return link['href']
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
 
_cp1252 = {
  unichr(128): unichr(8364), # euro sign
  unichr(130): unichr(8218), # single low-9 quotation mark
  unichr(131): unichr( 402), # latin small letter f with hook
  unichr(132): unichr(8222), # double low-9 quotation mark
  unichr(133): unichr(8230), # horizontal ellipsis
  unichr(134): unichr(8224), # dagger
  unichr(135): unichr(8225), # double dagger
  unichr(136): unichr( 710), # modifier letter circumflex accent
  unichr(137): unichr(8240), # per mille sign
  unichr(138): unichr( 352), # latin capital letter s with caron
  unichr(139): unichr(8249), # single left-pointing angle quotation mark
  unichr(140): unichr( 338), # latin capital ligature oe
  unichr(142): unichr( 381), # latin capital letter z with caron
  unichr(145): unichr(8216), # left single quotation mark
  unichr(146): unichr(8217), # right single quotation mark
  unichr(147): unichr(8220), # left double quotation mark
  unichr(148): unichr(8221), # right double quotation mark
  unichr(149): unichr(8226), # bullet
  unichr(150): unichr(8211), # en dash
  unichr(151): unichr(8212), # em dash
  unichr(152): unichr( 732), # small tilde
  unichr(153): unichr(8482), # trade mark sign
  unichr(154): unichr( 353), # latin small letter s with caron
  unichr(155): unichr(8250), # single right-pointing angle quotation mark
  unichr(156): unichr( 339), # latin small ligature oe
  unichr(158): unichr( 382), # latin small letter z with caron
  unichr(159): unichr( 376)} # latin capital letter y with diaeresis

_urifixer = re.compile('^([A-Za-z][A-Za-z0-9+-.]*://)(/*)(.*?)')
def _urljoin(base, uri):
    uri = _urifixer.sub(r'\1\3', uri)
    try:
        return urlparse.urljoin(base, uri)
    except:
        uri = urlparse.urlunparse([urllib.quote(part) for part in urlparse.urlparse(uri)])
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
                  #Version 1.1.2 of the Media RSS spec added the trailing slash on the namespace
                  'http://search.yahoo.com/mrss/':                         'media',
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
                  'http://schemas.pocketsoap.com/rss/myDescModule/':      'szf',
                  'http://purl.org/rss/1.0/modules/taxonomy/':            'taxo',
                  'http://purl.org/rss/1.0/modules/threading/':           'thr',
                  'http://purl.org/rss/1.0/modules/textinput/':           'ti',
                  'http://madskills.com/public/xml/rss/module/trackback/':'trackback',
                  'http://wellformedweb.org/commentAPI/':                 'wfw',
                  'http://purl.org/rss/1.0/modules/wiki/':                'wiki',
                  'http://www.w3.org/1999/xhtml':                         'xhtml',
                  'http://www.w3.org/1999/xlink':                         'xlink',
                  'http://www.w3.org/XML/1998/namespace':                 'xml'
}
    _matchnamespaces = {}

    can_be_relative_uri = ['link', 'id', 'wfw_comment', 'wfw_commentrss', 'docs', 'url', 'href', 'comments', 'icon', 'logo']
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
        self.svgOK = 0
        self.hasTitle = 0
        if baselang:
            self.feeddata['language'] = baselang.replace('_','-')

    def unknown_starttag(self, tag, attrs):
        if _debug: sys.stderr.write('start %s with %s\n' % (tag, attrs))
        # normalize attrs
        attrs = [(k.lower(), v) for k, v in attrs]
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        
        # track xml:base and xml:lang
        attrsD = dict(attrs)
        baseuri = attrsD.get('xml:base', attrsD.get('base')) or self.baseuri
        if type(baseuri) != type(u''):
            try:
                baseuri = unicode(baseuri, self.encoding)
            except:
                baseuri = unicode(baseuri, 'iso-8859-1')
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
                self.feeddata['language'] = lang.replace('_','-')
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
            if tag in ['xhtml:div', 'div']: return # typepad does this 10/2007
            # element declared itself as escaped markup, but it isn't really
            self.contentparams['type'] = 'application/xhtml+xml'
        if self.incontent and self.contentparams.get('type') == 'application/xhtml+xml':
            if tag.find(':') <> -1:
                prefix, tag = tag.split(':', 1)
                namespace = self.namespacesInUse.get(prefix, '')
                if tag=='math' and namespace=='http://www.w3.org/1998/Math/MathML':
                    attrs.append(('xmlns',namespace))
                if tag=='svg' and namespace=='http://www.w3.org/2000/svg':
                    attrs.append(('xmlns',namespace))
            if tag == 'svg': self.svgOK += 1
            return self.handle_data('<%s%s>' % (tag, self.strattrs(attrs)), escape=0)

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
            # Since there's no handler or something has gone wrong we explicitly add the element and its attributes
            unknown_tag = prefix + suffix
            if len(attrsD) == 0:
                # No attributes so merge it into the encosing dictionary
                return self.push(unknown_tag, 1)
            else:
                # Has attributes so create it in its own dictionary
                context = self._getContext()
                context[unknown_tag] = attrsD

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
        if suffix == 'svg' and self.svgOK: self.svgOK -= 1

        # call special handler (if defined) or default handler
        methodname = '_end_' + prefix + suffix
        try:
            if self.svgOK: raise AttributeError()
            method = getattr(self, methodname)
            method()
        except AttributeError:
            self.pop(prefix + suffix)

        # track inline content
        if self.incontent and self.contentparams.has_key('type') and not self.contentparams.get('type', 'xml').endswith('xml'):
            # element declared itself as escaped markup, but it isn't really
            if tag in ['xhtml:div', 'div']: return # typepad does this 10/2007
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
        elif ref in self.entities.keys():
            text = self.entities[ref]
            if text.startswith('&#') and text.endswith(';'):
                return self.handle_entityref(text)
        else:
            try: name2codepoint[ref]
            except KeyError: text = '&%s;' % ref
            else: text = unichr(name2codepoint[ref]).encode('utf-8')
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
            if k == -1:
                # CDATA block began but didn't finish
                k = len(self.rawdata)
                return k
            self.handle_data(_xmlescape(self.rawdata[i+9:k]), 0)
            return k+3
        else:
            k = self.rawdata.find('>', i)
            if k >= 0:
                return k+1
            else:
                # We have an incomplete CDATA block.
                return k

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

    def strattrs(self, attrs):
        return ''.join([' %s="%s"' % (t[0],_xmlescape(t[1],{'"':'&quot;'})) for t in attrs])

    def push(self, element, expectingText):
        self.elementstack.append([element, expectingText, []])

    def pop(self, element, stripWhitespace=1):
        if not self.elementstack: return
        if self.elementstack[-1][0] != element: return
        
        element, expectingText, pieces = self.elementstack.pop()

        if self.version == 'atom10' and self.contentparams.get('type','text') == 'application/xhtml+xml':
            # remove enclosing child element, but only if it is a <div> and
            # only if all the remaining content is nested underneath it.
            # This means that the divs would be retained in the following:
            #    <div>foo</div><div>bar</div>
            while pieces and len(pieces)>1 and not pieces[-1].strip():
                del pieces[-1]
            while pieces and len(pieces)>1 and not pieces[0].strip():
                del pieces[0]
            if pieces and (pieces[0] == '<div>' or pieces[0].startswith('<div ')) and pieces[-1]=='</div>':
                depth = 0
                for piece in pieces[:-1]:
                    if piece.startswith('</'):
                        depth -= 1
                        if depth == 0: break
                    elif piece.startswith('<') and not piece.endswith('/>'):
                        depth += 1
                else:
                    pieces = pieces[1:-1]

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

        if self.lookslikehtml(output):
            self.contentparams['type']='text/html'

        # remove temporary cruft from contentparams
        try:
            del self.contentparams['mode']
        except KeyError:
            pass
        try:
            del self.contentparams['base64']
        except KeyError:
            pass

        is_htmlish = self.mapContentType(self.contentparams.get('type', 'text/html')) in self.html_types
        # resolve relative URIs within embedded markup
        if is_htmlish and RESOLVE_RELATIVE_URIS:
            if element in self.can_contain_relative_uris:
                output = _resolveRelativeURIs(output, self.baseuri, self.encoding, self.contentparams.get('type', 'text/html'))
                
        # parse microformats
        # (must do this before sanitizing because some microformats
        # rely on elements that we sanitize)
        if is_htmlish and element in ['content', 'description', 'summary']:
            mfresults = _parseMicroformats(output, self.baseuri, self.encoding)
            if mfresults:
                for tag in mfresults.get('tags', []):
                    self._addTag(tag['term'], tag['scheme'], tag['label'])
                for enclosure in mfresults.get('enclosures', []):
                    self._start_enclosure(enclosure)
                for xfn in mfresults.get('xfn', []):
                    self._addXFN(xfn['relationships'], xfn['href'], xfn['name'])
                vcard = mfresults.get('vcard')
                if vcard:
                    self._getContext()['vcard'] = vcard
        
        # sanitize embedded markup
        if is_htmlish and SANITIZE_HTML:
            if element in self.can_contain_dangerous_markup:
                output = _sanitizeHTML(output, self.encoding, self.contentparams.get('type', 'text/html'))

        if self.encoding and type(output) != type(u''):
            try:
                output = unicode(output, self.encoding)
            except:
                pass

        # address common error where people take data that is already
        # utf-8, presume that it is iso-8859-1, and re-encode it.
        if self.encoding=='utf-8' and type(output) == type(u''):
            try:
                output = unicode(output.encode('iso-8859-1'), 'utf-8')
            except:
                pass

        # map win-1252 extensions to the proper code points
        if type(output) == type(u''):
            output = u''.join([c in _cp1252.keys() and _cp1252[c] or c for c in output])

        # categories/tags/keywords/whatever are handled in _end_category
        if element == 'category':
            return output

        if element == 'title' and self.hasTitle:
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
        elif (self.infeed or self.insource):# and (not self.intextinput) and (not self.inimage):
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
        if self.lang: self.lang=self.lang.replace('_','-')
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
        
    # a number of elements in a number of RSS variants are nominally plain
    # text, but this is routinely ignored.  This is an attempt to detect
    # the most common cases.  As false positives often result in silent
    # data loss, this function errs on the conservative side.
    def lookslikehtml(self, str):
        if self.version.startswith('atom'): return
        if self.contentparams.get('type','text/html') != 'text/plain': return

        # must have a close tag or a entity reference to qualify
        if not (re.search(r'</(\w+)>',str) or re.search("&#?\w+;",str)): return

        # all tags must be in a restricted subset of valid HTML tags
        if filter(lambda t: t.lower() not in _HTMLSanitizer.acceptable_elements,
            re.findall(r'</?(\w+)',str)): return

        # all entities must have been defined as valid HTML entities
        from htmlentitydefs import entitydefs
        if filter(lambda e: e not in entitydefs.keys(),
            re.findall(r'&(\w+);',str)): return

        return 1

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
        #If we're here then this is an RSS feed.
        #If we don't have a version or have a version that starts with something
        #other than RSS then there's been a mistake. Correct it.
        if not self.version or not self.version.startswith('rss'):
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
        context = self._getContext()
        context.setdefault('image', FeedParserDict())
        self.inimage = 1
        self.hasTitle = 0
        self.push('image', 0)
            
    def _end_image(self):
        self.pop('image')
        self.inimage = 0

    def _start_textinput(self, attrsD):
        context = self._getContext()
        context.setdefault('textinput', FeedParserDict())
        self.intextinput = 1
        self.hasTitle = 0
        self.push('textinput', 0)
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
            context['name'] = value
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
            context['width'] = value

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
            context['height'] = value

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
        elif self.inimage and self.feeddata.has_key('image'):
            context = self.feeddata['image']
        elif self.intextinput:
            context = self.feeddata['textinput']
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
            author, email = context.get(key), None
            if not author: return
            emailmatch = re.search(r'''(([a-zA-Z0-9\_\-\.\+]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([a-zA-Z0-9\-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?))(\?subject=\S+)?''', author)
            if emailmatch:
                email = emailmatch.group(0)
                # probably a better way to do the following, but it passes all the tests
                author = author.replace(email, '')
                author = author.replace('()', '')
                author = author.replace('<>', '')
                author = author.replace('&lt;&gt;', '')
                author = author.strip()
                if author and (author[0] == '('):
                    author = author[1:]
                if author and (author[-1] == ')'):
                    author = author[:-1]
                author = author.strip()
            if author or email:
                context.setdefault('%s_detail' % key, FeedParserDict())
            if author:
                context['%s_detail' % key]['name'] = author
            if email:
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
        self.hasTitle = 0
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
        context = self._getContext()
        value = self._getAttribute(attrsD, 'rdf:resource')
        attrsD = FeedParserDict()
        attrsD['rel']='license'
        if value: attrsD['href']=value
        context.setdefault('links', []).append(attrsD)
        
    def _start_creativecommons_license(self, attrsD):
        self.push('license', 1)
    _start_creativeCommons_license = _start_creativecommons_license

    def _end_creativecommons_license(self):
        value = self.pop('license')
        context = self._getContext()
        attrsD = FeedParserDict()
        attrsD['rel']='license'
        if value: attrsD['href']=value
        context.setdefault('links', []).append(attrsD)
        del context['license']
    _end_creativeCommons_license = _end_creativecommons_license

    def _addXFN(self, relationships, href, name):
        context = self._getContext()
        xfn = context.setdefault('xfn', [])
        value = FeedParserDict({'relationships': relationships, 'href': href, 'name': name})
        if value not in xfn:
            xfn.append(value)
        
    def _addTag(self, term, scheme, label):
        context = self._getContext()
        tags = context.setdefault('tags', [])
        if (not term) and (not scheme) and (not label): return
        value = FeedParserDict({'term': term, 'scheme': scheme, 'label': label})
        if value not in tags:
            tags.append(value)

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
        if attrsD['rel'] == 'self':
            attrsD.setdefault('type', 'application/atom+xml')
        else:
            attrsD.setdefault('type', 'text/html')
        context = self._getContext()
        attrsD = self._itsAnHrefDamnIt(attrsD)
        if attrsD.has_key('href'):
            attrsD['href'] = self.resolveURI(attrsD['href'])
            if attrsD.get('rel')=='enclosure' and not context.get('id'):
                context['id'] = attrsD.get('href')
        expectingText = self.infeed or self.inentry or self.insource
        context.setdefault('links', [])
        context['links'].append(FeedParserDict(attrsD))
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
        if self.svgOK: return self.unknown_starttag('title', attrsD.items())
        self.pushContent('title', attrsD, 'text/plain', self.infeed or self.inentry or self.insource)
    _start_dc_title = _start_title
    _start_media_title = _start_title

    def _end_title(self):
        if self.svgOK: return
        value = self.popContent('title')
        if not value: return
        context = self._getContext()
        self.hasTitle = 1
    _end_dc_title = _end_title

    def _end_media_title(self):
        hasTitle = self.hasTitle
        self._end_title()
        self.hasTitle = hasTitle

    def _start_description(self, attrsD):
        context = self._getContext()
        if context.has_key('summary'):
            self._summaryKey = 'content'
            self._start_content(attrsD)
        else:
            self.pushContent('description', attrsD, 'text/html', self.infeed or self.inentry or self.insource)
    _start_dc_description = _start_description

    def _start_abstract(self, attrsD):
        self.pushContent('description', attrsD, 'text/plain', self.infeed or self.inentry or self.insource)

    def _end_description(self):
        if self._summaryKey == 'content':
            self._end_content()
        else:
            value = self.popContent('description')
        self._summaryKey = None
    _end_abstract = _end_description
    _end_dc_description = _end_description

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
        context = self._getContext()
        attrsD['rel']='enclosure'
        context.setdefault('links', []).append(FeedParserDict(attrsD))
        href = attrsD.get('href')
        if href and not context.get('id'):
            context['id'] = href
            
    def _start_source(self, attrsD):
        if 'url' in attrsD:
          # This means that we're processing a source element from an RSS 2.0 feed
          self.sourcedata['href'] = attrsD[u'url']
        self.push('source', 1)
        self.insource = 1
        self.hasTitle = 0

    def _end_source(self):
        self.insource = 0
        value = self.pop('source')
        if value:
          self.sourcedata['title'] = value
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

    def _start_media_content(self, attrsD):
        context = self._getContext()
        context.setdefault('media_content', [])
        context['media_content'].append(attrsD)

    def _start_media_thumbnail(self, attrsD):
        context = self._getContext()
        context.setdefault('media_thumbnail', [])
        self.push('url', 1) # new
        context['media_thumbnail'].append(attrsD)

    def _end_media_thumbnail(self):
        url = self.pop('url')
        context = self._getContext()
        if url != None and len(url.strip()) != 0:
            if not context['media_thumbnail'][-1].has_key('url'):
                context['media_thumbnail'][-1]['url'] = url

    def _start_media_player(self, attrsD):
        self.push('media_player', 0)
        self._getContext()['media_player'] = FeedParserDict(attrsD)

    def _end_media_player(self):
        value = self.pop('media_player')
        context = self._getContext()
        context['media_player']['content'] = value

if _XML_AVAILABLE:
    class _StrictFeedParser(_FeedParserMixin, xml.sax.handler.ContentHandler):
        def __init__(self, baseuri, baselang, encoding):
            if _debug: sys.stderr.write('trying StrictFeedParser\n')
            xml.sax.handler.ContentHandler.__init__(self)
            _FeedParserMixin.__init__(self, baseuri, baselang, encoding)
            self.bozo = 0
            self.exc = None
            self.decls = {}
        
        def startPrefixMapping(self, prefix, uri):
            self.trackNamespace(prefix, uri)
            if uri == 'http://www.w3.org/1999/xlink':
              self.decls['xmlns:'+prefix] = uri
        
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
            localname = str(localname).lower()

            # qname implementation is horribly broken in Python 2.1 (it
            # doesn't report any), and slightly broken in Python 2.2 (it
            # doesn't report the xml: namespace). So we match up namespaces
            # with a known list first, and then possibly override them with
            # the qnames the SAX parser gives us (if indeed it gives us any
            # at all).  Thanks to MatejC for helping me test this and
            # tirelessly telling me that it didn't work yet.
            attrsD, self.decls = self.decls, {}
            if localname=='math' and namespace=='http://www.w3.org/1998/Math/MathML':
                attrsD['xmlns']=namespace
            if localname=='svg' and namespace=='http://www.w3.org/2000/svg':
                attrsD['xmlns']=namespace

            if prefix:
                localname = prefix.lower() + ':' + localname
            elif namespace and not qname: #Expat
                for name,value in self.namespacesInUse.items():
                     if name and value == namespace:
                         localname = name + ':' + localname
                         break
            if _debug: sys.stderr.write('startElementNS: qname = %s, namespace = %s, givenprefix = %s, prefix = %s, attrs = %s, localname = %s\n' % (qname, namespace, givenprefix, prefix, attrs.items(), localname))

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
            elif namespace and not qname: #Expat
                for name,value in self.namespacesInUse.items():
                     if name and value == namespace:
                         localname = name + ':' + localname
                         break
            localname = str(localname).lower()
            self.unknown_endtag(localname)

        def error(self, exc):
            self.bozo = 1
            self.exc = exc

        def fatalError(self, exc):
            self.error(exc)
            raise exc

class _BaseHTMLProcessor(sgmllib.SGMLParser):
    special = re.compile('''[<>'"]''')
    bare_ampersand = re.compile("&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)")
    elements_no_end_tag = [
      'area', 'base', 'basefont', 'br', 'col', 'command', 'embed', 'frame', 
      'hr', 'img', 'input', 'isindex', 'keygen', 'link', 'meta', 'param',
      'source', 'track', 'wbr'
    ]

    def __init__(self, encoding, type):
        self.encoding = encoding
        self.type = type
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

    def parse_starttag(self,i):
        j=sgmllib.SGMLParser.parse_starttag(self, i)
        if self.type == 'application/xhtml+xml':
            if j>2 and self.rawdata[j-2:j]=='/>':
                self.unknown_endtag(self.lasttag)
        return j

    def feed(self, data):
        data = re.compile(r'<!((?!DOCTYPE|--|\[))', re.IGNORECASE).sub(r'&lt;!\1', data)
        #data = re.sub(r'<(\S+?)\s*?/>', self._shorttag_replace, data) # bug [ 1399464 ] Bad regexp for _shorttag_replace
        data = re.sub(r'<([^<>\s]+?)\s*/>', self._shorttag_replace, data) 
        data = data.replace('&#39;', "'")
        data = data.replace('&#34;', '"')
        if self.encoding and type(data) == type(u''):
            data = data.encode(self.encoding)
        sgmllib.SGMLParser.feed(self, data)
        sgmllib.SGMLParser.close(self)

    def normalize_attrs(self, attrs):
        if not attrs: return attrs
        # utility method to be called by descendants
        attrs = dict([(k.lower(), v) for k, v in attrs]).items()
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        attrs.sort()
        return attrs

    def unknown_starttag(self, tag, attrs):
        # called for each start tag
        # attrs is a list of (attr, value) tuples
        # e.g. for <pre class='screen'>, tag='pre', attrs=[('class', 'screen')]
        if _debug: sys.stderr.write('_BaseHTMLProcessor, unknown_starttag, tag=%s\n' % tag)
        uattrs = []
        strattrs=''
        if attrs:
            for key, value in attrs:
                value=value.replace('>','&gt;').replace('<','&lt;').replace('"','&quot;')
                value = self.bare_ampersand.sub("&amp;", value)
                # thanks to Kevin Marks for this breathtaking hack to deal with (valid) high-bit attribute values in UTF-8 feeds
                if type(value) != type(u''):
                    try:
                        value = unicode(value, self.encoding)
                    except:
                        value = unicode(value, 'iso-8859-1')
                uattrs.append((unicode(key, self.encoding), value))
            strattrs = u''.join([u' %s="%s"' % (key, value) for key, value in uattrs])
            if self.encoding:
                try:
                    strattrs=strattrs.encode(self.encoding)
                except:
                    pass
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
        if ref.startswith('x'):
            value = unichr(int(ref[1:],16))
        else:
            value = unichr(int(ref))

        if value in _cp1252.keys():
            self.pieces.append('&#%s;' % hex(ord(_cp1252[value]))[1:])
        else:
            self.pieces.append('&#%(ref)s;' % locals())
        
    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        # Reconstruct the original entity reference.
        if name2codepoint.has_key(ref):
            self.pieces.append('&%(ref)s;' % locals())
        else:
            self.pieces.append('&amp;%(ref)s' % locals())

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        # Store the original text verbatim.
        if _debug: sys.stderr.write('_BaseHTMLProcessor, handle_data, text=%s\n' % text)
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

    def convert_charref(self, name):
        return '&#%s;' % name

    def convert_entityref(self, name):
        return '&%s;' % name

    def output(self):
        '''Return processed HTML as a single string'''
        return ''.join([str(p) for p in self.pieces])

class _LooseFeedParser(_FeedParserMixin, _BaseHTMLProcessor):
    def __init__(self, baseuri, baselang, encoding, entities):
        sgmllib.SGMLParser.__init__(self)
        _FeedParserMixin.__init__(self, baseuri, baselang, encoding)
        _BaseHTMLProcessor.__init__(self, encoding, 'application/xhtml+xml')
        self.entities=entities

    def decodeEntities(self, element, data):
        data = data.replace('&#60;', '&lt;')
        data = data.replace('&#x3c;', '&lt;')
        data = data.replace('&#x3C;', '&lt;')
        data = data.replace('&#62;', '&gt;')
        data = data.replace('&#x3e;', '&gt;')
        data = data.replace('&#x3E;', '&gt;')
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
        
    def strattrs(self, attrs):
        return ''.join([' %s="%s"' % (n,v.replace('"','&quot;')) for n,v in attrs])

class _MicroformatsParser:
    STRING = 1
    DATE = 2
    URI = 3
    NODE = 4
    EMAIL = 5

    known_xfn_relationships = ['contact', 'acquaintance', 'friend', 'met', 'co-worker', 'coworker', 'colleague', 'co-resident', 'coresident', 'neighbor', 'child', 'parent', 'sibling', 'brother', 'sister', 'spouse', 'wife', 'husband', 'kin', 'relative', 'muse', 'crush', 'date', 'sweetheart', 'me']
    known_binary_extensions =  ['zip','rar','exe','gz','tar','tgz','tbz2','bz2','z','7z','dmg','img','sit','sitx','hqx','deb','rpm','bz2','jar','rar','iso','bin','msi','mp2','mp3','ogg','ogm','mp4','m4v','m4a','avi','wma','wmv']

    def __init__(self, data, baseuri, encoding):
        self.document = BeautifulSoup.BeautifulSoup(data)
        self.baseuri = baseuri
        self.encoding = encoding
        if type(data) == type(u''):
            data = data.encode(encoding)
        self.tags = []
        self.enclosures = []
        self.xfn = []
        self.vcard = None
    
    def vcardEscape(self, s):
        if type(s) in (type(''), type(u'')):
            s = s.replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')
        return s
    
    def vcardFold(self, s):
        s = re.sub(';+$', '', s)
        sFolded = ''
        iMax = 75
        sPrefix = ''
        while len(s) > iMax:
            sFolded += sPrefix + s[:iMax] + '\n'
            s = s[iMax:]
            sPrefix = ' '
            iMax = 74
        sFolded += sPrefix + s
        return sFolded

    def normalize(self, s):
        return re.sub(r'\s+', ' ', s).strip()
    
    def unique(self, aList):
        results = []
        for element in aList:
            if element not in results:
                results.append(element)
        return results
    
    def toISO8601(self, dt):
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', dt)

    def getPropertyValue(self, elmRoot, sProperty, iPropertyType=4, bAllowMultiple=0, bAutoEscape=0):
        all = lambda x: 1
        sProperty = sProperty.lower()
        bFound = 0
        bNormalize = 1
        propertyMatch = {'class': re.compile(r'\b%s\b' % sProperty)}
        if bAllowMultiple and (iPropertyType != self.NODE):
            snapResults = []
            containers = elmRoot(['ul', 'ol'], propertyMatch)
            for container in containers:
                snapResults.extend(container('li'))
            bFound = (len(snapResults) != 0)
        if not bFound:
            snapResults = elmRoot(all, propertyMatch)
            bFound = (len(snapResults) != 0)
        if (not bFound) and (sProperty == 'value'):
            snapResults = elmRoot('pre')
            bFound = (len(snapResults) != 0)
            bNormalize = not bFound
            if not bFound:
                snapResults = [elmRoot]
                bFound = (len(snapResults) != 0)
        arFilter = []
        if sProperty == 'vcard':
            snapFilter = elmRoot(all, propertyMatch)
            for node in snapFilter:
                if node.findParent(all, propertyMatch):
                    arFilter.append(node)
        arResults = []
        for node in snapResults:
            if node not in arFilter:
                arResults.append(node)
        bFound = (len(arResults) != 0)
        if not bFound:
            if bAllowMultiple: return []
            elif iPropertyType == self.STRING: return ''
            elif iPropertyType == self.DATE: return None
            elif iPropertyType == self.URI: return ''
            elif iPropertyType == self.NODE: return None
            else: return None
        arValues = []
        for elmResult in arResults:
            sValue = None
            if iPropertyType == self.NODE:
                if bAllowMultiple:
                    arValues.append(elmResult)
                    continue
                else:
                    return elmResult
            sNodeName = elmResult.name.lower()
            if (iPropertyType == self.EMAIL) and (sNodeName == 'a'):
                sValue = (elmResult.get('href') or '').split('mailto:').pop().split('?')[0]
            if sValue:
                sValue = bNormalize and self.normalize(sValue) or sValue.strip()
            if (not sValue) and (sNodeName == 'abbr'):
                sValue = elmResult.get('title')
            if sValue:
                sValue = bNormalize and self.normalize(sValue) or sValue.strip()
            if (not sValue) and (iPropertyType == self.URI):
                if sNodeName == 'a': sValue = elmResult.get('href')
                elif sNodeName == 'img': sValue = elmResult.get('src')
                elif sNodeName == 'object': sValue = elmResult.get('data')
            if sValue:
                sValue = bNormalize and self.normalize(sValue) or sValue.strip()
            if (not sValue) and (sNodeName == 'img'):
                sValue = elmResult.get('alt')
            if sValue:
                sValue = bNormalize and self.normalize(sValue) or sValue.strip()
            if not sValue:
                sValue = elmResult.renderContents()
                sValue = re.sub(r'<\S[^>]*>', '', sValue)
                sValue = sValue.replace('\r\n', '\n')
                sValue = sValue.replace('\r', '\n')
            if sValue:
                sValue = bNormalize and self.normalize(sValue) or sValue.strip()
            if not sValue: continue
            if iPropertyType == self.DATE:
                sValue = _parse_date_iso8601(sValue)
            if bAllowMultiple:
                arValues.append(bAutoEscape and self.vcardEscape(sValue) or sValue)
            else:
                return bAutoEscape and self.vcardEscape(sValue) or sValue
        return arValues

    def findVCards(self, elmRoot, bAgentParsing=0):
        sVCards = ''
        
        if not bAgentParsing:
            arCards = self.getPropertyValue(elmRoot, 'vcard', bAllowMultiple=1)
        else:
            arCards = [elmRoot]
            
        for elmCard in arCards:
            arLines = []
            
            def processSingleString(sProperty):
                sValue = self.getPropertyValue(elmCard, sProperty, self.STRING, bAutoEscape=1)
                if sValue:
                    arLines.append(self.vcardFold(sProperty.upper() + ':' + sValue))
                return sValue or ''
            
            def processSingleURI(sProperty):
                sValue = self.getPropertyValue(elmCard, sProperty, self.URI)
                if sValue:
                    sContentType = ''
                    sEncoding = ''
                    sValueKey = ''
                    if sValue.startswith('data:'):
                        sEncoding = ';ENCODING=b'
                        sContentType = sValue.split(';')[0].split('/').pop()
                        sValue = sValue.split(',', 1).pop()
                    else:
                        elmValue = self.getPropertyValue(elmCard, sProperty)
                        if elmValue:
                            if sProperty != 'url':
                                sValueKey = ';VALUE=uri'
                            sContentType = elmValue.get('type', '').strip().split('/').pop().strip()
                    sContentType = sContentType.upper()
                    if sContentType == 'OCTET-STREAM':
                        sContentType = ''
                    if sContentType:
                        sContentType = ';TYPE=' + sContentType.upper()
                    arLines.append(self.vcardFold(sProperty.upper() + sEncoding + sContentType + sValueKey + ':' + sValue))
    
            def processTypeValue(sProperty, arDefaultType, arForceType=None):
                arResults = self.getPropertyValue(elmCard, sProperty, bAllowMultiple=1)
                for elmResult in arResults:
                    arType = self.getPropertyValue(elmResult, 'type', self.STRING, 1, 1)
                    if arForceType:
                        arType = self.unique(arForceType + arType)
                    if not arType:
                        arType = arDefaultType
                    sValue = self.getPropertyValue(elmResult, 'value', self.EMAIL, 0)
                    if sValue:
                        arLines.append(self.vcardFold(sProperty.upper() + ';TYPE=' + ','.join(arType) + ':' + sValue))
            
            # AGENT
            # must do this before all other properties because it is destructive
            # (removes nested class="vcard" nodes so they don't interfere with
            # this vcard's other properties)
            arAgent = self.getPropertyValue(elmCard, 'agent', bAllowMultiple=1)
            for elmAgent in arAgent:
                if re.compile(r'\bvcard\b').search(elmAgent.get('class')):
                    sAgentValue = self.findVCards(elmAgent, 1) + '\n'
                    sAgentValue = sAgentValue.replace('\n', '\\n')
                    sAgentValue = sAgentValue.replace(';', '\\;')
                    if sAgentValue:
                        arLines.append(self.vcardFold('AGENT:' + sAgentValue))
                    elmAgent['class'] = ''
                    elmAgent.contents = []
                else:
                    sAgentValue = self.getPropertyValue(elmAgent, 'value', self.URI, bAutoEscape=1);
                    if sAgentValue:
                        arLines.append(self.vcardFold('AGENT;VALUE=uri:' + sAgentValue))
    
            # FN (full name)
            sFN = processSingleString('fn')
            
            # N (name)
            elmName = self.getPropertyValue(elmCard, 'n')
            if elmName:
                sFamilyName = self.getPropertyValue(elmName, 'family-name', self.STRING, bAutoEscape=1)
                sGivenName = self.getPropertyValue(elmName, 'given-name', self.STRING, bAutoEscape=1)
                arAdditionalNames = self.getPropertyValue(elmName, 'additional-name', self.STRING, 1, 1) + self.getPropertyValue(elmName, 'additional-names', self.STRING, 1, 1)
                arHonorificPrefixes = self.getPropertyValue(elmName, 'honorific-prefix', self.STRING, 1, 1) + self.getPropertyValue(elmName, 'honorific-prefixes', self.STRING, 1, 1)
                arHonorificSuffixes = self.getPropertyValue(elmName, 'honorific-suffix', self.STRING, 1, 1) + self.getPropertyValue(elmName, 'honorific-suffixes', self.STRING, 1, 1)
                arLines.append(self.vcardFold('N:' + sFamilyName + ';' + 
                                         sGivenName + ';' +
                                         ','.join(arAdditionalNames) + ';' +
                                         ','.join(arHonorificPrefixes) + ';' +
                                         ','.join(arHonorificSuffixes)))
            elif sFN:
                # implied "N" optimization
                # http://microformats.org/wiki/hcard#Implied_.22N.22_Optimization
                arNames = self.normalize(sFN).split()
                if len(arNames) == 2:
                    bFamilyNameFirst = (arNames[0].endswith(',') or
                                        len(arNames[1]) == 1 or
                                        ((len(arNames[1]) == 2) and (arNames[1].endswith('.'))))
                    if bFamilyNameFirst:
                        arLines.append(self.vcardFold('N:' + arNames[0] + ';' + arNames[1]))
                    else:
                        arLines.append(self.vcardFold('N:' + arNames[1] + ';' + arNames[0]))
    
            # SORT-STRING
            sSortString = self.getPropertyValue(elmCard, 'sort-string', self.STRING, bAutoEscape=1)
            if sSortString:
                arLines.append(self.vcardFold('SORT-STRING:' + sSortString))
            
            # NICKNAME
            arNickname = self.getPropertyValue(elmCard, 'nickname', self.STRING, 1, 1)
            if arNickname:
                arLines.append(self.vcardFold('NICKNAME:' + ','.join(arNickname)))
            
            # PHOTO
            processSingleURI('photo')
            
            # BDAY
            dtBday = self.getPropertyValue(elmCard, 'bday', self.DATE)
            if dtBday:
                arLines.append(self.vcardFold('BDAY:' + self.toISO8601(dtBday)))
            
            # ADR (address)
            arAdr = self.getPropertyValue(elmCard, 'adr', bAllowMultiple=1)
            for elmAdr in arAdr:
                arType = self.getPropertyValue(elmAdr, 'type', self.STRING, 1, 1)
                if not arType:
                    arType = ['intl','postal','parcel','work'] # default adr types, see RFC 2426 section 3.2.1
                sPostOfficeBox = self.getPropertyValue(elmAdr, 'post-office-box', self.STRING, 0, 1)
                sExtendedAddress = self.getPropertyValue(elmAdr, 'extended-address', self.STRING, 0, 1)
                sStreetAddress = self.getPropertyValue(elmAdr, 'street-address', self.STRING, 0, 1)
                sLocality = self.getPropertyValue(elmAdr, 'locality', self.STRING, 0, 1)
                sRegion = self.getPropertyValue(elmAdr, 'region', self.STRING, 0, 1)
                sPostalCode = self.getPropertyValue(elmAdr, 'postal-code', self.STRING, 0, 1)
                sCountryName = self.getPropertyValue(elmAdr, 'country-name', self.STRING, 0, 1)
                arLines.append(self.vcardFold('ADR;TYPE=' + ','.join(arType) + ':' +
                                         sPostOfficeBox + ';' +
                                         sExtendedAddress + ';' +
                                         sStreetAddress + ';' +
                                         sLocality + ';' +
                                         sRegion + ';' +
                                         sPostalCode + ';' +
                                         sCountryName))
            
            # LABEL
            processTypeValue('label', ['intl','postal','parcel','work'])
            
            # TEL (phone number)
            processTypeValue('tel', ['voice'])
            
            # EMAIL
            processTypeValue('email', ['internet'], ['internet'])
            
            # MAILER
            processSingleString('mailer')
            
            # TZ (timezone)
            processSingleString('tz')
    
            # GEO (geographical information)
            elmGeo = self.getPropertyValue(elmCard, 'geo')
            if elmGeo:
                sLatitude = self.getPropertyValue(elmGeo, 'latitude', self.STRING, 0, 1)
                sLongitude = self.getPropertyValue(elmGeo, 'longitude', self.STRING, 0, 1)
                arLines.append(self.vcardFold('GEO:' + sLatitude + ';' + sLongitude))
    
            # TITLE
            processSingleString('title')
    
            # ROLE
            processSingleString('role')

            # LOGO
            processSingleURI('logo')
    
            # ORG (organization)
            elmOrg = self.getPropertyValue(elmCard, 'org')
            if elmOrg:
                sOrganizationName = self.getPropertyValue(elmOrg, 'organization-name', self.STRING, 0, 1)
                if not sOrganizationName:
                    # implied "organization-name" optimization
                    # http://microformats.org/wiki/hcard#Implied_.22organization-name.22_Optimization
                    sOrganizationName = self.getPropertyValue(elmCard, 'org', self.STRING, 0, 1)
                    if sOrganizationName:
                        arLines.append(self.vcardFold('ORG:' + sOrganizationName))
                else:
                    arOrganizationUnit = self.getPropertyValue(elmOrg, 'organization-unit', self.STRING, 1, 1)
                    arLines.append(self.vcardFold('ORG:' + sOrganizationName + ';' + ';'.join(arOrganizationUnit)))
    
            # CATEGORY
            arCategory = self.getPropertyValue(elmCard, 'category', self.STRING, 1, 1) + self.getPropertyValue(elmCard, 'categories', self.STRING, 1, 1)
            if arCategory:
                arLines.append(self.vcardFold('CATEGORIES:' + ','.join(arCategory)))
    
            # NOTE
            processSingleString('note')
    
            # REV
            processSingleString('rev')
    
            # SOUND
            processSingleURI('sound')
    
            # UID
            processSingleString('uid')
    
            # URL
            processSingleURI('url')
    
            # CLASS
            processSingleString('class')
    
            # KEY
            processSingleURI('key')
    
            if arLines:
                arLines = ['BEGIN:vCard','VERSION:3.0'] + arLines + ['END:vCard']
                sVCards += '\n'.join(arLines) + '\n'
    
        return sVCards.strip()
    
    def isProbablyDownloadable(self, elm):
        attrsD = elm.attrMap
        if not attrsD.has_key('href'): return 0
        linktype = attrsD.get('type', '').strip()
        if linktype.startswith('audio/') or \
           linktype.startswith('video/') or \
           (linktype.startswith('application/') and not linktype.endswith('xml')):
            return 1
        path = urlparse.urlparse(attrsD['href'])[2]
        if path.find('.') == -1: return 0
        fileext = path.split('.').pop().lower()
        return fileext in self.known_binary_extensions

    def findTags(self):
        all = lambda x: 1
        for elm in self.document(all, {'rel': re.compile(r'\btag\b')}):
            href = elm.get('href')
            if not href: continue
            urlscheme, domain, path, params, query, fragment = \
                       urlparse.urlparse(_urljoin(self.baseuri, href))
            segments = path.split('/')
            tag = segments.pop()
            if not tag:
                tag = segments.pop()
            tagscheme = urlparse.urlunparse((urlscheme, domain, '/'.join(segments), '', '', ''))
            if not tagscheme.endswith('/'):
                tagscheme += '/'
            self.tags.append(FeedParserDict({"term": tag, "scheme": tagscheme, "label": elm.string or ''}))

    def findEnclosures(self):
        all = lambda x: 1
        enclosure_match = re.compile(r'\benclosure\b')
        for elm in self.document(all, {'href': re.compile(r'.+')}):
            if not enclosure_match.search(elm.get('rel', '')) and not self.isProbablyDownloadable(elm): continue
            if elm.attrMap not in self.enclosures:
                self.enclosures.append(elm.attrMap)
                if elm.string and not elm.get('title'):
                    self.enclosures[-1]['title'] = elm.string

    def findXFN(self):
        all = lambda x: 1
        for elm in self.document(all, {'rel': re.compile('.+'), 'href': re.compile('.+')}):
            rels = elm.get('rel', '').split()
            xfn_rels = []
            for rel in rels:
                if rel in self.known_xfn_relationships:
                    xfn_rels.append(rel)
            if xfn_rels:
                self.xfn.append({"relationships": xfn_rels, "href": elm.get('href', ''), "name": elm.string})

def _parseMicroformats(htmlSource, baseURI, encoding):
    if not BeautifulSoup: return
    if _debug: sys.stderr.write('entering _parseMicroformats\n')
    p = _MicroformatsParser(htmlSource, baseURI, encoding)
    p.vcard = p.findVCards(p.document)
    p.findTags()
    p.findEnclosures()
    p.findXFN()
    return {"tags": p.tags, "enclosures": p.enclosures, "xfn": p.xfn, "vcard": p.vcard}

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

    def __init__(self, baseuri, encoding, type):
        _BaseHTMLProcessor.__init__(self, encoding, type)
        self.baseuri = baseuri

    def resolveURI(self, uri):
        return _urljoin(self.baseuri, uri.strip())
    
    def unknown_starttag(self, tag, attrs):
        if _debug:
            sys.stderr.write('tag: [%s] with attributes: [%s]\n' % (tag, str(attrs)))
        attrs = self.normalize_attrs(attrs)
        attrs = [(key, ((tag, key) in self.relative_uris) and self.resolveURI(value) or value) for key, value in attrs]
        _BaseHTMLProcessor.unknown_starttag(self, tag, attrs)

def _resolveRelativeURIs(htmlSource, baseURI, encoding, type):
    if _debug:
        sys.stderr.write('entering _resolveRelativeURIs\n')

    p = _RelativeURIResolver(baseURI, encoding, type)
    p.feed(htmlSource)
    return p.output()

class _HTMLSanitizer(_BaseHTMLProcessor):
    acceptable_elements = ['a', 'abbr', 'acronym', 'address', 'area', 'article',
      'aside', 'audio', 'b', 'big', 'blockquote', 'br', 'button', 'canvas',
      'caption', 'center', 'cite', 'code', 'col', 'colgroup', 'command',
      'datagrid', 'datalist', 'dd', 'del', 'details', 'dfn', 'dialog', 'dir',
      'div', 'dl', 'dt', 'em', 'event-source', 'fieldset', 'figure', 'footer',
      'font', 'form', 'header', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i',
      'img', 'input', 'ins', 'keygen', 'kbd', 'label', 'legend', 'li', 'm', 'map',
      'menu', 'meter', 'multicol', 'nav', 'nextid', 'ol', 'output', 'optgroup',
      'option', 'p', 'pre', 'progress', 'q', 's', 'samp', 'section', 'select',
      'small', 'sound', 'source', 'spacer', 'span', 'strike', 'strong', 'sub',
      'sup', 'table', 'tbody', 'td', 'textarea', 'time', 'tfoot', 'th', 'thead',
      'tr', 'tt', 'u', 'ul', 'var', 'video', 'noscript']

    acceptable_attributes = ['abbr', 'accept', 'accept-charset', 'accesskey',
      'action', 'align', 'alt', 'autocomplete', 'autofocus', 'axis',
      'background', 'balance', 'bgcolor', 'bgproperties', 'border',
      'bordercolor', 'bordercolordark', 'bordercolorlight', 'bottompadding',
      'cellpadding', 'cellspacing', 'ch', 'challenge', 'char', 'charoff',
      'choff', 'charset', 'checked', 'cite', 'class', 'clear', 'color', 'cols',
      'colspan', 'compact', 'contenteditable', 'controls', 'coords', 'data',
      'datafld', 'datapagesize', 'datasrc', 'datetime', 'default', 'delay',
      'dir', 'disabled', 'draggable', 'dynsrc', 'enctype', 'end', 'face', 'for',
      'form', 'frame', 'galleryimg', 'gutter', 'headers', 'height', 'hidefocus',
      'hidden', 'high', 'href', 'hreflang', 'hspace', 'icon', 'id', 'inputmode',
      'ismap', 'keytype', 'label', 'leftspacing', 'lang', 'list', 'longdesc',
      'loop', 'loopcount', 'loopend', 'loopstart', 'low', 'lowsrc', 'max',
      'maxlength', 'media', 'method', 'min', 'multiple', 'name', 'nohref',
      'noshade', 'nowrap', 'open', 'optimum', 'pattern', 'ping', 'point-size',
      'prompt', 'pqg', 'radiogroup', 'readonly', 'rel', 'repeat-max',
      'repeat-min', 'replace', 'required', 'rev', 'rightspacing', 'rows',
      'rowspan', 'rules', 'scope', 'selected', 'shape', 'size', 'span', 'src',
      'start', 'step', 'summary', 'suppress', 'tabindex', 'target', 'template',
      'title', 'toppadding', 'type', 'unselectable', 'usemap', 'urn', 'valign',
      'value', 'variable', 'volume', 'vspace', 'vrml', 'width', 'wrap',
      'xml:lang']

    unacceptable_elements_with_end_tag = ['script', 'applet', 'style']

    acceptable_css_properties = ['azimuth', 'background-color',
      'border-bottom-color', 'border-collapse', 'border-color',
      'border-left-color', 'border-right-color', 'border-top-color', 'clear',
      'color', 'cursor', 'direction', 'display', 'elevation', 'float', 'font',
      'font-family', 'font-size', 'font-style', 'font-variant', 'font-weight',
      'height', 'letter-spacing', 'line-height', 'overflow', 'pause',
      'pause-after', 'pause-before', 'pitch', 'pitch-range', 'richness',
      'speak', 'speak-header', 'speak-numeral', 'speak-punctuation',
      'speech-rate', 'stress', 'text-align', 'text-decoration', 'text-indent',
      'unicode-bidi', 'vertical-align', 'voice-family', 'volume',
      'white-space', 'width']

    # survey of common keywords found in feeds
    acceptable_css_keywords = ['auto', 'aqua', 'black', 'block', 'blue',
      'bold', 'both', 'bottom', 'brown', 'center', 'collapse', 'dashed',
      'dotted', 'fuchsia', 'gray', 'green', '!important', 'italic', 'left',
      'lime', 'maroon', 'medium', 'none', 'navy', 'normal', 'nowrap', 'olive',
      'pointer', 'purple', 'red', 'right', 'solid', 'silver', 'teal', 'top',
      'transparent', 'underline', 'white', 'yellow']

    valid_css_values = re.compile('^(#[0-9a-f]+|rgb\(\d+%?,\d*%?,?\d*%?\)?|' +
      '\d{0,2}\.?\d{0,2}(cm|em|ex|in|mm|pc|pt|px|%|,|\))?)$')

    mathml_elements = ['annotation', 'annotation-xml', 'maction', 'math',
      'merror', 'mfenced', 'mfrac', 'mi', 'mmultiscripts', 'mn', 'mo', 'mover', 'mpadded',
      'mphantom', 'mprescripts', 'mroot', 'mrow', 'mspace', 'msqrt', 'mstyle',
      'msub', 'msubsup', 'msup', 'mtable', 'mtd', 'mtext', 'mtr', 'munder',
      'munderover', 'none', 'semantics']

    mathml_attributes = ['actiontype', 'align', 'columnalign', 'columnalign',
      'columnalign', 'close', 'columnlines', 'columnspacing', 'columnspan', 'depth',
      'display', 'displaystyle', 'encoding', 'equalcolumns', 'equalrows',
      'fence', 'fontstyle', 'fontweight', 'frame', 'height', 'linethickness',
      'lspace', 'mathbackground', 'mathcolor', 'mathvariant', 'mathvariant',
      'maxsize', 'minsize', 'open', 'other', 'rowalign', 'rowalign', 'rowalign',
      'rowlines', 'rowspacing', 'rowspan', 'rspace', 'scriptlevel', 'selection',
      'separator', 'separators', 'stretchy', 'width', 'width', 'xlink:href',
      'xlink:show', 'xlink:type', 'xmlns', 'xmlns:xlink']

    # svgtiny - foreignObject + linearGradient + radialGradient + stop
    svg_elements = ['a', 'animate', 'animateColor', 'animateMotion',
      'animateTransform', 'circle', 'defs', 'desc', 'ellipse', 'foreignObject',
      'font-face', 'font-face-name', 'font-face-src', 'g', 'glyph', 'hkern', 
      'linearGradient', 'line', 'marker', 'metadata', 'missing-glyph', 'mpath',
      'path', 'polygon', 'polyline', 'radialGradient', 'rect', 'set', 'stop',
      'svg', 'switch', 'text', 'title', 'tspan', 'use']

    # svgtiny + class + opacity + offset + xmlns + xmlns:xlink
    svg_attributes = ['accent-height', 'accumulate', 'additive', 'alphabetic',
       'arabic-form', 'ascent', 'attributeName', 'attributeType',
       'baseProfile', 'bbox', 'begin', 'by', 'calcMode', 'cap-height',
       'class', 'color', 'color-rendering', 'content', 'cx', 'cy', 'd', 'dx',
       'dy', 'descent', 'display', 'dur', 'end', 'fill', 'fill-opacity',
       'fill-rule', 'font-family', 'font-size', 'font-stretch', 'font-style',
       'font-variant', 'font-weight', 'from', 'fx', 'fy', 'g1', 'g2',
       'glyph-name', 'gradientUnits', 'hanging', 'height', 'horiz-adv-x',
       'horiz-origin-x', 'id', 'ideographic', 'k', 'keyPoints', 'keySplines',
       'keyTimes', 'lang', 'mathematical', 'marker-end', 'marker-mid',
       'marker-start', 'markerHeight', 'markerUnits', 'markerWidth', 'max',
       'min', 'name', 'offset', 'opacity', 'orient', 'origin',
       'overline-position', 'overline-thickness', 'panose-1', 'path',
       'pathLength', 'points', 'preserveAspectRatio', 'r', 'refX', 'refY',
       'repeatCount', 'repeatDur', 'requiredExtensions', 'requiredFeatures',
       'restart', 'rotate', 'rx', 'ry', 'slope', 'stemh', 'stemv',
       'stop-color', 'stop-opacity', 'strikethrough-position',
       'strikethrough-thickness', 'stroke', 'stroke-dasharray',
       'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin',
       'stroke-miterlimit', 'stroke-opacity', 'stroke-width', 'systemLanguage',
       'target', 'text-anchor', 'to', 'transform', 'type', 'u1', 'u2',
       'underline-position', 'underline-thickness', 'unicode', 'unicode-range',
       'units-per-em', 'values', 'version', 'viewBox', 'visibility', 'width',
       'widths', 'x', 'x-height', 'x1', 'x2', 'xlink:actuate', 'xlink:arcrole',
       'xlink:href', 'xlink:role', 'xlink:show', 'xlink:title', 'xlink:type',
       'xml:base', 'xml:lang', 'xml:space', 'xmlns', 'xmlns:xlink', 'y', 'y1',
       'y2', 'zoomAndPan']

    svg_attr_map = None
    svg_elem_map = None

    acceptable_svg_properties = [ 'fill', 'fill-opacity', 'fill-rule',
      'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin',
      'stroke-opacity']

    def reset(self):
        _BaseHTMLProcessor.reset(self)
        self.unacceptablestack = 0
        self.mathmlOK = 0
        self.svgOK = 0
        
    def unknown_starttag(self, tag, attrs):
        acceptable_attributes = self.acceptable_attributes
        keymap = {}
        if not tag in self.acceptable_elements or self.svgOK:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack += 1

            # add implicit namespaces to html5 inline svg/mathml
            if self.type.endswith('html'):
                if tag=='svg':
                    if not dict(attrs).get('xmlns'):
                        attrs.append( ('xmlns','http://www.w3.org/2000/svg') )
                if tag=='math':
                    if not dict(attrs).get('xmlns'):
                        attrs.append( ('xmlns','http://www.w3.org/1998/Math/MathML') )

            # not otherwise acceptable, perhaps it is MathML or SVG?
            if tag=='math' and ('xmlns','http://www.w3.org/1998/Math/MathML') in attrs:
                self.mathmlOK += 1
            if tag=='svg' and ('xmlns','http://www.w3.org/2000/svg') in attrs:
                self.svgOK += 1

            # chose acceptable attributes based on tag class, else bail
            if  self.mathmlOK and tag in self.mathml_elements:
                acceptable_attributes = self.mathml_attributes
            elif self.svgOK and tag in self.svg_elements:
                # for most vocabularies, lowercasing is a good idea.  Many
                # svg elements, however, are camel case
                if not self.svg_attr_map:
                    lower=[attr.lower() for attr in self.svg_attributes]
                    mix=[a for a in self.svg_attributes if a not in lower]
                    self.svg_attributes = lower
                    self.svg_attr_map = dict([(a.lower(),a) for a in mix])

                    lower=[attr.lower() for attr in self.svg_elements]
                    mix=[a for a in self.svg_elements if a not in lower]
                    self.svg_elements = lower
                    self.svg_elem_map = dict([(a.lower(),a) for a in mix])
                acceptable_attributes = self.svg_attributes
                tag = self.svg_elem_map.get(tag,tag)
                keymap = self.svg_attr_map
            elif not tag in self.acceptable_elements:
                return

        # declare xlink namespace, if needed
        if self.mathmlOK or self.svgOK:
            if filter(lambda (n,v): n.startswith('xlink:'),attrs):
                if not ('xmlns:xlink','http://www.w3.org/1999/xlink') in attrs:
                    attrs.append(('xmlns:xlink','http://www.w3.org/1999/xlink'))

        clean_attrs = []
        for key, value in self.normalize_attrs(attrs):
            if key in acceptable_attributes:
                key=keymap.get(key,key)
                clean_attrs.append((key,value))
            elif key=='style':
                clean_value = self.sanitize_style(value)
                if clean_value: clean_attrs.append((key,clean_value))
        _BaseHTMLProcessor.unknown_starttag(self, tag, clean_attrs)
        
    def unknown_endtag(self, tag):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack -= 1
            if self.mathmlOK and tag in self.mathml_elements:
                if tag == 'math' and self.mathmlOK: self.mathmlOK -= 1
            elif self.svgOK and tag in self.svg_elements:
                tag = self.svg_elem_map.get(tag,tag)
                if tag == 'svg' and self.svgOK: self.svgOK -= 1
            else:
                return
        _BaseHTMLProcessor.unknown_endtag(self, tag)

    def handle_pi(self, text):
        pass

    def handle_decl(self, text):
        pass

    def handle_data(self, text):
        if not self.unacceptablestack:
            _BaseHTMLProcessor.handle_data(self, text)

    def sanitize_style(self, style):
        # disallow urls
        style=re.compile('url\s*\(\s*[^\s)]+?\s*\)\s*').sub(' ',style)

        # gauntlet
        if not re.match("""^([:,;#%.\sa-zA-Z0-9!]|\w-\w|'[\s\w]+'|"[\s\w]+"|\([\d,\s]+\))*$""", style): return ''
        # This replaced a regexp that used re.match and was prone to pathological back-tracking.
        if re.sub("\s*[-\w]+\s*:\s*[^:;]*;?", '', style).strip(): return ''

        clean = []
        for prop,value in re.findall("([-\w]+)\s*:\s*([^:;]*)",style):
          if not value: continue
          if prop.lower() in self.acceptable_css_properties:
              clean.append(prop + ': ' + value + ';')
          elif prop.split('-')[0].lower() in ['background','border','margin','padding']:
              for keyword in value.split():
                  if not keyword in self.acceptable_css_keywords and \
                      not self.valid_css_values.match(keyword):
                      break
              else:
                  clean.append(prop + ': ' + value + ';')
          elif self.svgOK and prop.lower() in self.acceptable_svg_properties:
              clean.append(prop + ': ' + value + ';')

        return ' '.join(clean)


def _sanitizeHTML(htmlSource, encoding, type):
    p = _HTMLSanitizer(encoding, type)
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

    If the modified argument is supplied, it can be a tuple of 9 integers
    (as returned by gmtime() in the standard Python time module) or a date
    string in any format supported by feedparser. Regardless, it MUST
    be in GMT (Greenwich Mean Time). It will be reformatted into an
    RFC 1123-compliant date and used as the value of an If-Modified-Since
    request header.

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

        # iri support
        try:
            if isinstance(url_file_stream_or_string,unicode):
                url_file_stream_or_string = url_file_stream_or_string.encode('idna')
            else:
                url_file_stream_or_string = url_file_stream_or_string.decode('utf-8').encode('idna')
        except:
            pass

        # try to open with urllib2 (to use optional headers)
        request = urllib2.Request(url_file_stream_or_string)
        request.add_header('User-Agent', agent)
        if etag:
            request.add_header('If-None-Match', etag)
        if type(modified) == type(''):
            modified = _parse_date(modified)
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
_iso8601_tmpl = ['YYYY-?MM-?DD', 'YYYY-0MM?-?DD', 'YYYY-MM', 'YYYY-?OOO',
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
    + r'(\.(?P<fracsecond>\d+))?'
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
    second = int(float(params.get('second', 0)))
    # weekday is normalized by mktime(), we can ignore it
    weekday = 0
    daylight_savings_flag = -1
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

def _parse_date_perforce(aDateString):
	"""parse a date in yyyy/mm/dd hh:mm:ss TTT format"""
	# Fri, 2006/09/15 08:19:53 EDT
	_my_date_pattern = re.compile( \
		r'(\w{,3}), (\d{,4})/(\d{,2})/(\d{2}) (\d{,2}):(\d{2}):(\d{2}) (\w{,3})')

	dow, year, month, day, hour, minute, second, tz = \
		_my_date_pattern.search(aDateString).groups()
	months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
	dateString = "%s, %s %s %s %s:%s:%s %s" % (dow, day, months[int(month) - 1], year, hour, minute, second, tz)
	tm = rfc822.parsedate_tz(dateString)
	if tm:
		return time.gmtime(rfc822.mktime_tz(tm))
registerDateHandler(_parse_date_perforce)

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
    # some feeds claim to be gb2312 but are actually gb18030.
    # apparently MSIE and Firefox both do the following switch:
    if true_encoding.lower() == 'gb2312':
        true_encoding = 'gb18030'
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
    start = re.search('<\w',data)
    start = start and start.start() or -1
    head,data = data[:start+1], data[start+1:]
    
    entity_pattern = re.compile(r'^\s*<!ENTITY([^>]*?)>', re.MULTILINE)
    entity_results=entity_pattern.findall(head)
    head = entity_pattern.sub('', head)
    doctype_pattern = re.compile(r'^\s*<!DOCTYPE([^>]*?)>', re.MULTILINE)
    doctype_results = doctype_pattern.findall(head)
    doctype = doctype_results and doctype_results[0] or ''
    if doctype.lower().count('netscape'):
        version = 'rss091n'
    else:
        version = None

    # only allow in 'safe' inline entity definitions
    replacement=''
    if len(doctype_results)==1 and entity_results:
       safe_pattern=re.compile('\s+(\w+)\s+"(&#\w+;|[^&"]*)"')
       safe_entities=filter(lambda e: safe_pattern.match(e),entity_results)
       if safe_entities:
           replacement='<!DOCTYPE feed [\n  <!ENTITY %s>\n]>' % '>\n  <!ENTITY '.join(safe_entities)
    data = doctype_pattern.sub(replacement, head) + data

    return version, data, dict(replacement and safe_pattern.findall(replacement))
    
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
        data = None
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
        etag = info.getheader('ETag')
        if etag:
            result['etag'] = etag
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

    if data is not None:
        result['version'], data, entities = _stripDoctype(data)

    baseuri = http_headers.get('content-location', result.get('href'))
    baselang = http_headers.get('content-language', None)

    # if server sent 304, we're done
    if result.get('status', 0) == 304:
        result['version'] = ''
        result['debug_message'] = 'The feed has not changed since you last checked, ' + \
            'so the server sent no data.  This is a feature, not a bug!'
        return result

    # if there was a problem downloading, we're done
    if data is None:
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
    # if still no luck and we haven't tried iso-8859-2 yet, try that.
    if (not known_encoding) and ('iso-8859-2' not in tried_encodings):
        try:
            proposed_encoding = 'iso-8859-2'
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
            '%s, %s, utf-8, windows-1252, and iso-8859-2 but nothing worked' % \
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
        feedparser = _LooseFeedParser(baseuri, baselang, known_encoding and 'utf-8' or '', entities)
        feedparser.feed(data)
    result['feed'] = feedparser.feeddata
    result['entries'] = feedparser.entries
    result['version'] = result['version'] or feedparser.version
    result['namespaces'] = feedparser.namespacesInUse
    return result

class Serializer:
    def __init__(self, results):
        self.results = results

class TextSerializer(Serializer):
    def write(self, stream=sys.stdout):
        self._writer(stream, self.results, '')

    def _writer(self, stream, node, prefix):
        if not node: return
        if hasattr(node, 'keys'):
            keys = node.keys()
            keys.sort()
            for k in keys:
                if k in ('description', 'link'): continue
                if node.has_key(k + '_detail'): continue
                if node.has_key(k + '_parsed'): continue
                self._writer(stream, node[k], prefix + k + '.')
        elif type(node) == types.ListType:
            index = 0
            for n in node:
                self._writer(stream, n, prefix[:-1] + '[' + str(index) + '].')
                index += 1
        else:
            try:
                s = str(node).encode('utf-8')
                s = s.replace('\\', '\\\\')
                s = s.replace('\r', '')
                s = s.replace('\n', r'\n')
                stream.write(prefix[:-1])
                stream.write('=')
                stream.write(s)
                stream.write('\n')
            except:
                pass
        
class PprintSerializer(Serializer):
    def write(self, stream=sys.stdout):
        if self.results.has_key('href'):
            stream.write(self.results['href'] + '\n\n')
        from pprint import pprint
        pprint(self.results, stream)
        stream.write('\n')
        
if __name__ == '__main__':
    try:
        from optparse import OptionParser
    except:
        OptionParser = None

    if OptionParser:
        optionParser = OptionParser(version=__version__, usage="%prog [options] url_or_filename_or_-")
        optionParser.set_defaults(format="pprint")
        optionParser.add_option("-A", "--user-agent", dest="agent", metavar="AGENT", help="User-Agent for HTTP URLs")
        optionParser.add_option("-e", "--referer", "--referrer", dest="referrer", metavar="URL", help="Referrer for HTTP URLs")
        optionParser.add_option("-t", "--etag", dest="etag", metavar="TAG", help="ETag/If-None-Match for HTTP URLs")
        optionParser.add_option("-m", "--last-modified", dest="modified", metavar="DATE", help="Last-modified/If-Modified-Since for HTTP URLs (any supported date format)")
        optionParser.add_option("-f", "--format", dest="format", metavar="FORMAT", help="output results in FORMAT (text, pprint)")
        optionParser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="write debugging information to stderr")
        (options, urls) = optionParser.parse_args()
        if options.verbose:
            _debug = 1
        if not urls:
            optionParser.print_help()
            sys.exit(0)
    else:
        if not sys.argv[1:]:
            print __doc__
            sys.exit(0)
        class _Options:
            etag = modified = agent = referrer = None
            format = 'pprint'
        options = _Options()
        urls = sys.argv[1:]

    zopeCompatibilityHack()

    serializer = globals().get(options.format.capitalize() + 'Serializer', Serializer)
    for url in urls:
        results = parse(url, etag=options.etag, modified=options.modified, agent=options.agent, referrer=options.referrer)
        serializer(results).write(sys.stdout)

########NEW FILE########
__FILENAME__ = constants
import string, gettext
_ = gettext.gettext

try:
    frozenset
except NameError:
    # Import from the sets module for python 2.3
    from sets import Set as set
    from sets import ImmutableSet as frozenset

EOF = None

E = {
    "null-character": 
       _(u"Null character in input stream, replaced with U+FFFD."),
    "invalid-character": 
       _(u"Invalid codepoint in stream."),
    "incorrectly-placed-solidus":
       _(u"Solidus (/) incorrectly placed in tag."),
    "incorrect-cr-newline-entity":
       _(u"Incorrect CR newline entity, replaced with LF."),
    "illegal-windows-1252-entity":
       _(u"Entity used with illegal number (windows-1252 reference)."),
    "cant-convert-numeric-entity":
       _(u"Numeric entity couldn't be converted to character "
         u"(codepoint U+%(charAsInt)08x)."),
    "illegal-codepoint-for-numeric-entity":
       _(u"Numeric entity represents an illegal codepoint: "
         u"U+%(charAsInt)08x."),
    "numeric-entity-without-semicolon":
       _(u"Numeric entity didn't end with ';'."),
    "expected-numeric-entity-but-got-eof":
       _(u"Numeric entity expected. Got end of file instead."),
    "expected-numeric-entity":
       _(u"Numeric entity expected but none found."),
    "named-entity-without-semicolon":
       _(u"Named entity didn't end with ';'."),
    "expected-named-entity":
       _(u"Named entity expected. Got none."),
    "attributes-in-end-tag":
       _(u"End tag contains unexpected attributes."),
    "expected-tag-name-but-got-right-bracket":
       _(u"Expected tag name. Got '>' instead."),
    "expected-tag-name-but-got-question-mark":
       _(u"Expected tag name. Got '?' instead. (HTML doesn't "
         u"support processing instructions.)"),
    "expected-tag-name":
       _(u"Expected tag name. Got something else instead"),
    "expected-closing-tag-but-got-right-bracket":
       _(u"Expected closing tag. Got '>' instead. Ignoring '</>'."),
    "expected-closing-tag-but-got-eof":
       _(u"Expected closing tag. Unexpected end of file."),
    "expected-closing-tag-but-got-char":
       _(u"Expected closing tag. Unexpected character '%(data)s' found."),
    "eof-in-tag-name":
       _(u"Unexpected end of file in the tag name."),
    "expected-attribute-name-but-got-eof":
       _(u"Unexpected end of file. Expected attribute name instead."),
    "eof-in-attribute-name":
       _(u"Unexpected end of file in attribute name."),
    "invalid-character-in-attribute-name":
        _(u"Invalid chracter in attribute name"),
    "duplicate-attribute":
       _(u"Dropped duplicate attribute on tag."),
    "expected-end-of-tag-name-but-got-eof":
       _(u"Unexpected end of file. Expected = or end of tag."),
    "expected-attribute-value-but-got-eof":
       _(u"Unexpected end of file. Expected attribute value."),
    "expected-attribute-value-but-got-right-bracket":
       _(u"Expected attribute value. Got '>' instead."),
    "eof-in-attribute-value-double-quote":
       _(u"Unexpected end of file in attribute value (\")."),
    "eof-in-attribute-value-single-quote":
       _(u"Unexpected end of file in attribute value (')."),
    "eof-in-attribute-value-no-quotes":
       _(u"Unexpected end of file in attribute value."),
    "unexpected-EOF-after-solidus-in-tag":
        _(u"Unexpected end of file in tag. Expected >"),
    "unexpected-character-after-soldius-in-tag":
        _(u"Unexpected character after / in tag. Expected >"),
    "expected-dashes-or-doctype":
       _(u"Expected '--' or 'DOCTYPE'. Not found."),
    "incorrect-comment":
       _(u"Incorrect comment."),
    "eof-in-comment":
       _(u"Unexpected end of file in comment."),
    "eof-in-comment-end-dash":
       _(u"Unexpected end of file in comment (-)"),
    "unexpected-dash-after-double-dash-in-comment":
       _(u"Unexpected '-' after '--' found in comment."),
    "eof-in-comment-double-dash":
       _(u"Unexpected end of file in comment (--)."),
    "unexpected-char-in-comment":
       _(u"Unexpected character in comment found."),
    "need-space-after-doctype":
       _(u"No space after literal string 'DOCTYPE'."),
    "expected-doctype-name-but-got-right-bracket":
       _(u"Unexpected > character. Expected DOCTYPE name."),
    "expected-doctype-name-but-got-eof":
       _(u"Unexpected end of file. Expected DOCTYPE name."),
    "eof-in-doctype-name":
       _(u"Unexpected end of file in DOCTYPE name."),
    "eof-in-doctype":
       _(u"Unexpected end of file in DOCTYPE."),
    "expected-space-or-right-bracket-in-doctype":
       _(u"Expected space or '>'. Got '%(data)s'"),
    "unexpected-end-of-doctype":
       _(u"Unexpected end of DOCTYPE."),
    "unexpected-char-in-doctype":
       _(u"Unexpected character in DOCTYPE."),
    "eof-in-innerhtml":
       _(u"XXX innerHTML EOF"),
    "unexpected-doctype":
       _(u"Unexpected DOCTYPE. Ignored."),
    "non-html-root":
       _(u"html needs to be the first start tag."),
    "expected-doctype-but-got-eof":
       _(u"Unexpected End of file. Expected DOCTYPE."),
    "unknown-doctype":
       _(u"Erroneous DOCTYPE."),
    "expected-doctype-but-got-chars":
       _(u"Unexpected non-space characters. Expected DOCTYPE."),
    "expected-doctype-but-got-start-tag":
       _(u"Unexpected start tag (%(name)s). Expected DOCTYPE."),
    "expected-doctype-but-got-end-tag":
       _(u"Unexpected end tag (%(name)s). Expected DOCTYPE."),
    "end-tag-after-implied-root":
       _(u"Unexpected end tag (%(name)s) after the (implied) root element."),
    "expected-named-closing-tag-but-got-eof":
       _(u"Unexpected end of file. Expected end tag (%(name)s)."),
    "two-heads-are-not-better-than-one":
       _(u"Unexpected start tag head in existing head. Ignored."),
    "unexpected-end-tag":
       _(u"Unexpected end tag (%(name)s). Ignored."),
    "unexpected-start-tag-out-of-my-head":
       _(u"Unexpected start tag (%(name)s) that can be in head. Moved."),
    "unexpected-start-tag":
       _(u"Unexpected start tag (%(name)s)."),
    "missing-end-tag":
       _(u"Missing end tag (%(name)s)."),
    "missing-end-tags":
       _(u"Missing end tags (%(name)s)."),
    "unexpected-start-tag-implies-end-tag":
       _(u"Unexpected start tag (%(startName)s) "
         u"implies end tag (%(endName)s)."),
    "unexpected-start-tag-treated-as":
       _(u"Unexpected start tag (%(originalName)s). Treated as %(newName)s."),
    "deprecated-tag":
       _(u"Unexpected start tag %(name)s. Don't use it!"),
    "unexpected-start-tag-ignored":
       _(u"Unexpected start tag %(name)s. Ignored."),
    "expected-one-end-tag-but-got-another":
       _(u"Unexpected end tag (%(gotName)s). "
         u"Missing end tag (%(expectedName)s)."),
    "end-tag-too-early":
       _(u"End tag (%(name)s) seen too early. Expected other end tag."),
    "end-tag-too-early-named":
       _(u"Unexpected end tag (%(gotName)s). Expected end tag (%(expectedName)s)."),
    "end-tag-too-early-ignored":
       _(u"End tag (%(name)s) seen too early. Ignored."),
    "adoption-agency-1.1":
       _(u"End tag (%(name)s) violates step 1, "
         u"paragraph 1 of the adoption agency algorithm."),
    "adoption-agency-1.2":
       _(u"End tag (%(name)s) violates step 1, "
         u"paragraph 2 of the adoption agency algorithm."),
    "adoption-agency-1.3":
       _(u"End tag (%(name)s) violates step 1, "
         u"paragraph 3 of the adoption agency algorithm."),
    "unexpected-end-tag-treated-as":
       _(u"Unexpected end tag (%(originalName)s). Treated as %(newName)s."),
    "no-end-tag":
       _(u"This element (%(name)s) has no end tag."),
    "unexpected-implied-end-tag-in-table":
       _(u"Unexpected implied end tag (%(name)s) in the table phase."),
    "unexpected-implied-end-tag-in-table-body":
       _(u"Unexpected implied end tag (%(name)s) in the table body phase."),
    "unexpected-char-implies-table-voodoo":
       _(u"Unexpected non-space characters in "
         u"table context caused voodoo mode."),
    "unexpected-hidden-input-in-table":
       _(u"Unexpected input with type hidden in table context."),
    "unexpected-form-in-table":
       _(u"Unexpected form in table context."),
    "unexpected-start-tag-implies-table-voodoo":
       _(u"Unexpected start tag (%(name)s) in "
         u"table context caused voodoo mode."),
    "unexpected-end-tag-implies-table-voodoo":
       _(u"Unexpected end tag (%(name)s) in "
         u"table context caused voodoo mode."),
    "unexpected-cell-in-table-body":
       _(u"Unexpected table cell start tag (%(name)s) "
         u"in the table body phase."),
    "unexpected-cell-end-tag":
       _(u"Got table cell end tag (%(name)s) "
         u"while required end tags are missing."),
    "unexpected-end-tag-in-table-body":
       _(u"Unexpected end tag (%(name)s) in the table body phase. Ignored."),
    "unexpected-implied-end-tag-in-table-row":
       _(u"Unexpected implied end tag (%(name)s) in the table row phase."),
    "unexpected-end-tag-in-table-row":
       _(u"Unexpected end tag (%(name)s) in the table row phase. Ignored."),
    "unexpected-select-in-select":
       _(u"Unexpected select start tag in the select phase "
         u"treated as select end tag."),
    "unexpected-input-in-select":
       _(u"Unexpected input start tag in the select phase."),
    "unexpected-start-tag-in-select":
       _(u"Unexpected start tag token (%(name)s in the select phase. "
         u"Ignored."),
    "unexpected-end-tag-in-select":
       _(u"Unexpected end tag (%(name)s) in the select phase. Ignored."),
    "unexpected-table-element-start-tag-in-select-in-table":
       _(u"Unexpected table element start tag (%(name)s) in the select in table phase."),
    "unexpected-table-element-end-tag-in-select-in-table":
       _(u"Unexpected table element end tag (%(name)s) in the select in table phase."),
    "unexpected-char-after-body":
       _(u"Unexpected non-space characters in the after body phase."),
    "unexpected-start-tag-after-body":
       _(u"Unexpected start tag token (%(name)s)"
         u" in the after body phase."),
    "unexpected-end-tag-after-body":
       _(u"Unexpected end tag token (%(name)s)"
         u" in the after body phase."),
    "unexpected-char-in-frameset":
       _(u"Unepxected characters in the frameset phase. Characters ignored."),
    "unexpected-start-tag-in-frameset":
       _(u"Unexpected start tag token (%(name)s)"
         u" in the frameset phase. Ignored."),
    "unexpected-frameset-in-frameset-innerhtml":
       _(u"Unexpected end tag token (frameset) "
         u"in the frameset phase (innerHTML)."),
    "unexpected-end-tag-in-frameset":
       _(u"Unexpected end tag token (%(name)s)"
         u" in the frameset phase. Ignored."),
    "unexpected-char-after-frameset":
       _(u"Unexpected non-space characters in the "
         u"after frameset phase. Ignored."),
    "unexpected-start-tag-after-frameset":
       _(u"Unexpected start tag (%(name)s)"
         u" in the after frameset phase. Ignored."),
    "unexpected-end-tag-after-frameset":
       _(u"Unexpected end tag (%(name)s)"
         u" in the after frameset phase. Ignored."),
    "unexpected-end-tag-after-body-innerhtml":
       _(u"Unexpected end tag after body(innerHtml)"),
    "expected-eof-but-got-char":
       _(u"Unexpected non-space characters. Expected end of file."),
    "expected-eof-but-got-start-tag":
       _(u"Unexpected start tag (%(name)s)"
         u". Expected end of file."),
    "expected-eof-but-got-end-tag":
       _(u"Unexpected end tag (%(name)s)"
         u". Expected end of file."),
    "eof-in-table":
       _(u"Unexpected end of file. Expected table content."),
    "eof-in-select":
       _(u"Unexpected end of file. Expected select content."),
    "eof-in-frameset":
       _(u"Unexpected end of file. Expected frameset content."),
    "eof-in-script-in-script":
       _(u"Unexpected end of file. Expected script content."),
    "non-void-element-with-trailing-solidus":
       _(u"Trailing solidus not allowed on element %(name)s"),
    "unexpected-html-element-in-foreign-content":
       _(u"Element %(name)s not allowed in a non-html context"),
    "unexpected-end-tag-before-html":
        _(u"Unexpected end tag (%(name)s) before html."),
    "XXX-undefined-error":
        (u"Undefined error (this sucks and should be fixed)"),
}

namespaces = {
    "html":"http://www.w3.org/1999/xhtml",
    "mathml":"http://www.w3.org/1998/Math/MathML",
    "svg":"http://www.w3.org/2000/svg",
    "xlink":"http://www.w3.org/1999/xlink",
    "xml":"http://www.w3.org/XML/1998/namespace",
    "xmlns":"http://www.w3.org/2000/xmlns/"
}

scopingElements = frozenset((
    (namespaces["html"], "applet"),
    (namespaces["html"], "button"),
    (namespaces["html"], "caption"),
    (namespaces["html"], "html"),
    (namespaces["html"], "marquee"),
    (namespaces["html"], "object"),
    (namespaces["html"], "table"),
    (namespaces["html"], "td"),
    (namespaces["html"], "th"),
    (namespaces["svg"], "foreignObject")
))

formattingElements = frozenset((
    (namespaces["html"], "a"),
    (namespaces["html"], "b"),
    (namespaces["html"], "big"),
    (namespaces["html"], "code"),
    (namespaces["html"], "em"),
    (namespaces["html"], "font"),
    (namespaces["html"], "i"),
    (namespaces["html"], "nobr"),
    (namespaces["html"], "s"),
    (namespaces["html"], "small"),
    (namespaces["html"], "strike"),
    (namespaces["html"], "strong"),
    (namespaces["html"], "tt"),
    (namespaces["html"], "u")
))

specialElements = frozenset((
    (namespaces["html"], "address"),
    (namespaces["html"], "area"),
    (namespaces["html"], "article"),
    (namespaces["html"], "aside"),
    (namespaces["html"], "base"),
    (namespaces["html"], "basefont"),
    (namespaces["html"], "bgsound"),
    (namespaces["html"], "blockquote"),
    (namespaces["html"], "body"),
    (namespaces["html"], "br"),
    (namespaces["html"], "center"),
    (namespaces["html"], "col"),
    (namespaces["html"], "colgroup"),
    (namespaces["html"], "command"),
    (namespaces["html"], "datagrid"),
    (namespaces["html"], "dd"),
    (namespaces["html"], "details"),
    (namespaces["html"], "dialog"),
    (namespaces["html"], "dir"),
    (namespaces["html"], "div"),
    (namespaces["html"], "dl"),
    (namespaces["html"], "dt"),
    (namespaces["html"], "embed"),
    (namespaces["html"], "event-source"),
    (namespaces["html"], "fieldset"),
    (namespaces["html"], "figure"),
    (namespaces["html"], "footer"),
    (namespaces["html"], "form"),
    (namespaces["html"], "frame"),
    (namespaces["html"], "frameset"),
    (namespaces["html"], "h1"),
    (namespaces["html"], "h2"),
    (namespaces["html"], "h3"),
    (namespaces["html"], "h4"),
    (namespaces["html"], "h5"),
    (namespaces["html"], "h6"),
    (namespaces["html"], "head"),
    (namespaces["html"], "header"),
    (namespaces["html"], "hr"),
    (namespaces["html"], "iframe"),
    # Note that image is commented out in the spec as "this isn't an
    # element that can end up on the stack, so it doesn't matter,"
    (namespaces["html"], "image"), 
    (namespaces["html"], "img"),
    (namespaces["html"], "input"),
    (namespaces["html"], "isindex"),
    (namespaces["html"], "li"),
    (namespaces["html"], "link"),
    (namespaces["html"], "listing"),
    (namespaces["html"], "menu"),
    (namespaces["html"], "meta"),
    (namespaces["html"], "nav"),
    (namespaces["html"], "noembed"),
    (namespaces["html"], "noframes"),
    (namespaces["html"], "noscript"),
    (namespaces["html"], "ol"),
    (namespaces["html"], "optgroup"),
    (namespaces["html"], "option"),
    (namespaces["html"], "p"),
    (namespaces["html"], "param"),
    (namespaces["html"], "plaintext"),
    (namespaces["html"], "pre"),
    (namespaces["html"], "script"),
    (namespaces["html"], "section"),
    (namespaces["html"], "select"),
    (namespaces["html"], "spacer"),
    (namespaces["html"], "style"),
    (namespaces["html"], "tbody"),
    (namespaces["html"], "textarea"),
    (namespaces["html"], "tfoot"),
    (namespaces["html"], "thead"),
    (namespaces["html"], "title"),
    (namespaces["html"], "tr"),
    (namespaces["html"], "ul"),
    (namespaces["html"], "wbr")
))

spaceCharacters = frozenset((
    u"\t",
    u"\n",
    u"\u000C",
    u" ",
    u"\r"
))

tableInsertModeElements = frozenset((
    "table",
    "tbody",
    "tfoot",
    "thead",
    "tr"
))

asciiLowercase = frozenset(string.ascii_lowercase)
asciiUppercase = frozenset(string.ascii_uppercase)
asciiLetters = frozenset(string.ascii_letters)
digits = frozenset(string.digits)
hexDigits = frozenset(string.hexdigits)

asciiUpper2Lower = dict([(ord(c),ord(c.lower()))
    for c in string.ascii_uppercase])

# Heading elements need to be ordered
headingElements = (
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6"
)

voidElements = frozenset((
    "base",
    "command",
    "event-source",
    "link",
    "meta",
    "hr",
    "br",
    "img",
    "embed",
    "param",
    "area",
    "col",
    "input",
    "source"
))

cdataElements = frozenset(('title', 'textarea'))

rcdataElements = frozenset((
    'style',
    'script',
    'xmp',
    'iframe',
    'noembed',
    'noframes',
    'noscript'
))

booleanAttributes = {
    "": frozenset(("irrelevant",)),
    "style": frozenset(("scoped",)),
    "img": frozenset(("ismap",)),
    "audio": frozenset(("autoplay","controls")),
    "video": frozenset(("autoplay","controls")),
    "script": frozenset(("defer", "async")),
    "details": frozenset(("open",)),
    "datagrid": frozenset(("multiple", "disabled")),
    "command": frozenset(("hidden", "disabled", "checked", "default")),
    "menu": frozenset(("autosubmit",)),
    "fieldset": frozenset(("disabled", "readonly")),
    "option": frozenset(("disabled", "readonly", "selected")),
    "optgroup": frozenset(("disabled", "readonly")),
    "button": frozenset(("disabled", "autofocus")),
    "input": frozenset(("disabled", "readonly", "required", "autofocus", "checked", "ismap")),
    "select": frozenset(("disabled", "readonly", "autofocus", "multiple")),
    "output": frozenset(("disabled", "readonly")),
}

# entitiesWindows1252 has to be _ordered_ and needs to have an index. It
# therefore can't be a frozenset.
entitiesWindows1252 = (
    8364,  # 0x80  0x20AC  EURO SIGN
    65533, # 0x81          UNDEFINED
    8218,  # 0x82  0x201A  SINGLE LOW-9 QUOTATION MARK
    402,   # 0x83  0x0192  LATIN SMALL LETTER F WITH HOOK
    8222,  # 0x84  0x201E  DOUBLE LOW-9 QUOTATION MARK
    8230,  # 0x85  0x2026  HORIZONTAL ELLIPSIS
    8224,  # 0x86  0x2020  DAGGER
    8225,  # 0x87  0x2021  DOUBLE DAGGER
    710,   # 0x88  0x02C6  MODIFIER LETTER CIRCUMFLEX ACCENT
    8240,  # 0x89  0x2030  PER MILLE SIGN
    352,   # 0x8A  0x0160  LATIN CAPITAL LETTER S WITH CARON
    8249,  # 0x8B  0x2039  SINGLE LEFT-POINTING ANGLE QUOTATION MARK
    338,   # 0x8C  0x0152  LATIN CAPITAL LIGATURE OE
    65533, # 0x8D          UNDEFINED
    381,   # 0x8E  0x017D  LATIN CAPITAL LETTER Z WITH CARON
    65533, # 0x8F          UNDEFINED
    65533, # 0x90          UNDEFINED
    8216,  # 0x91  0x2018  LEFT SINGLE QUOTATION MARK
    8217,  # 0x92  0x2019  RIGHT SINGLE QUOTATION MARK
    8220,  # 0x93  0x201C  LEFT DOUBLE QUOTATION MARK
    8221,  # 0x94  0x201D  RIGHT DOUBLE QUOTATION MARK
    8226,  # 0x95  0x2022  BULLET
    8211,  # 0x96  0x2013  EN DASH
    8212,  # 0x97  0x2014  EM DASH
    732,   # 0x98  0x02DC  SMALL TILDE
    8482,  # 0x99  0x2122  TRADE MARK SIGN
    353,   # 0x9A  0x0161  LATIN SMALL LETTER S WITH CARON
    8250,  # 0x9B  0x203A  SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
    339,   # 0x9C  0x0153  LATIN SMALL LIGATURE OE
    65533, # 0x9D          UNDEFINED
    382,   # 0x9E  0x017E  LATIN SMALL LETTER Z WITH CARON
    376    # 0x9F  0x0178  LATIN CAPITAL LETTER Y WITH DIAERESIS
)

xmlEntities = frozenset(('lt;', 'gt;', 'amp;', 'apos;', 'quot;'))

entities = {
    "AElig;": u"\u00C6",
    "AElig": u"\u00C6",
    "AMP;": u"\u0026",
    "AMP": u"\u0026",
    "Aacute;": u"\u00C1",
    "Aacute": u"\u00C1",
    "Acirc;": u"\u00C2",
    "Acirc": u"\u00C2",
    "Agrave;": u"\u00C0",
    "Agrave": u"\u00C0",
    "Alpha;": u"\u0391",
    "Aring;": u"\u00C5",
    "Aring": u"\u00C5",
    "Atilde;": u"\u00C3",
    "Atilde": u"\u00C3",
    "Auml;": u"\u00C4",
    "Auml": u"\u00C4",
    "Beta;": u"\u0392",
    "COPY;": u"\u00A9",
    "COPY": u"\u00A9",
    "Ccedil;": u"\u00C7",
    "Ccedil": u"\u00C7",
    "Chi;": u"\u03A7",
    "Dagger;": u"\u2021",
    "Delta;": u"\u0394",
    "ETH;": u"\u00D0",
    "ETH": u"\u00D0",
    "Eacute;": u"\u00C9",
    "Eacute": u"\u00C9",
    "Ecirc;": u"\u00CA",
    "Ecirc": u"\u00CA",
    "Egrave;": u"\u00C8",
    "Egrave": u"\u00C8",
    "Epsilon;": u"\u0395",
    "Eta;": u"\u0397",
    "Euml;": u"\u00CB",
    "Euml": u"\u00CB",
    "GT;": u"\u003E",
    "GT": u"\u003E",
    "Gamma;": u"\u0393",
    "Iacute;": u"\u00CD",
    "Iacute": u"\u00CD",
    "Icirc;": u"\u00CE",
    "Icirc": u"\u00CE",
    "Igrave;": u"\u00CC",
    "Igrave": u"\u00CC",
    "Iota;": u"\u0399",
    "Iuml;": u"\u00CF",
    "Iuml": u"\u00CF",
    "Kappa;": u"\u039A",
    "LT;": u"\u003C",
    "LT": u"\u003C",
    "Lambda;": u"\u039B",
    "Mu;": u"\u039C",
    "Ntilde;": u"\u00D1",
    "Ntilde": u"\u00D1",
    "Nu;": u"\u039D",
    "OElig;": u"\u0152",
    "Oacute;": u"\u00D3",
    "Oacute": u"\u00D3",
    "Ocirc;": u"\u00D4",
    "Ocirc": u"\u00D4",
    "Ograve;": u"\u00D2",
    "Ograve": u"\u00D2",
    "Omega;": u"\u03A9",
    "Omicron;": u"\u039F",
    "Oslash;": u"\u00D8",
    "Oslash": u"\u00D8",
    "Otilde;": u"\u00D5",
    "Otilde": u"\u00D5",
    "Ouml;": u"\u00D6",
    "Ouml": u"\u00D6",
    "Phi;": u"\u03A6",
    "Pi;": u"\u03A0",
    "Prime;": u"\u2033",
    "Psi;": u"\u03A8",
    "QUOT;": u"\u0022",
    "QUOT": u"\u0022",
    "REG;": u"\u00AE",
    "REG": u"\u00AE",
    "Rho;": u"\u03A1",
    "Scaron;": u"\u0160",
    "Sigma;": u"\u03A3",
    "THORN;": u"\u00DE",
    "THORN": u"\u00DE",
    "TRADE;": u"\u2122",
    "Tau;": u"\u03A4",
    "Theta;": u"\u0398",
    "Uacute;": u"\u00DA",
    "Uacute": u"\u00DA",
    "Ucirc;": u"\u00DB",
    "Ucirc": u"\u00DB",
    "Ugrave;": u"\u00D9",
    "Ugrave": u"\u00D9",
    "Upsilon;": u"\u03A5",
    "Uuml;": u"\u00DC",
    "Uuml": u"\u00DC",
    "Xi;": u"\u039E",
    "Yacute;": u"\u00DD",
    "Yacute": u"\u00DD",
    "Yuml;": u"\u0178",
    "Zeta;": u"\u0396",
    "aacute;": u"\u00E1",
    "aacute": u"\u00E1",
    "acirc;": u"\u00E2",
    "acirc": u"\u00E2",
    "acute;": u"\u00B4",
    "acute": u"\u00B4",
    "aelig;": u"\u00E6",
    "aelig": u"\u00E6",
    "agrave;": u"\u00E0",
    "agrave": u"\u00E0",
    "alefsym;": u"\u2135",
    "alpha;": u"\u03B1",
    "amp;": u"\u0026",
    "amp": u"\u0026",
    "and;": u"\u2227",
    "ang;": u"\u2220",
    "apos;": u"\u0027",
    "aring;": u"\u00E5",
    "aring": u"\u00E5",
    "asymp;": u"\u2248",
    "atilde;": u"\u00E3",
    "atilde": u"\u00E3",
    "auml;": u"\u00E4",
    "auml": u"\u00E4",
    "bdquo;": u"\u201E",
    "beta;": u"\u03B2",
    "brvbar;": u"\u00A6",
    "brvbar": u"\u00A6",
    "bull;": u"\u2022",
    "cap;": u"\u2229",
    "ccedil;": u"\u00E7",
    "ccedil": u"\u00E7",
    "cedil;": u"\u00B8",
    "cedil": u"\u00B8",
    "cent;": u"\u00A2",
    "cent": u"\u00A2",
    "chi;": u"\u03C7",
    "circ;": u"\u02C6",
    "clubs;": u"\u2663",
    "cong;": u"\u2245",
    "copy;": u"\u00A9",
    "copy": u"\u00A9",
    "crarr;": u"\u21B5",
    "cup;": u"\u222A",
    "curren;": u"\u00A4",
    "curren": u"\u00A4",
    "dArr;": u"\u21D3",
    "dagger;": u"\u2020",
    "darr;": u"\u2193",
    "deg;": u"\u00B0",
    "deg": u"\u00B0",
    "delta;": u"\u03B4",
    "diams;": u"\u2666",
    "divide;": u"\u00F7",
    "divide": u"\u00F7",
    "eacute;": u"\u00E9",
    "eacute": u"\u00E9",
    "ecirc;": u"\u00EA",
    "ecirc": u"\u00EA",
    "egrave;": u"\u00E8",
    "egrave": u"\u00E8",
    "empty;": u"\u2205",
    "emsp;": u"\u2003",
    "ensp;": u"\u2002",
    "epsilon;": u"\u03B5",
    "equiv;": u"\u2261",
    "eta;": u"\u03B7",
    "eth;": u"\u00F0",
    "eth": u"\u00F0",
    "euml;": u"\u00EB",
    "euml": u"\u00EB",
    "euro;": u"\u20AC",
    "exist;": u"\u2203",
    "fnof;": u"\u0192",
    "forall;": u"\u2200",
    "frac12;": u"\u00BD",
    "frac12": u"\u00BD",
    "frac14;": u"\u00BC",
    "frac14": u"\u00BC",
    "frac34;": u"\u00BE",
    "frac34": u"\u00BE",
    "frasl;": u"\u2044",
    "gamma;": u"\u03B3",
    "ge;": u"\u2265",
    "gt;": u"\u003E",
    "gt": u"\u003E",
    "hArr;": u"\u21D4",
    "harr;": u"\u2194",
    "hearts;": u"\u2665",
    "hellip;": u"\u2026",
    "iacute;": u"\u00ED",
    "iacute": u"\u00ED",
    "icirc;": u"\u00EE",
    "icirc": u"\u00EE",
    "iexcl;": u"\u00A1",
    "iexcl": u"\u00A1",
    "igrave;": u"\u00EC",
    "igrave": u"\u00EC",
    "image;": u"\u2111",
    "infin;": u"\u221E",
    "int;": u"\u222B",
    "iota;": u"\u03B9",
    "iquest;": u"\u00BF",
    "iquest": u"\u00BF",
    "isin;": u"\u2208",
    "iuml;": u"\u00EF",
    "iuml": u"\u00EF",
    "kappa;": u"\u03BA",
    "lArr;": u"\u21D0",
    "lambda;": u"\u03BB",
    "lang;": u"\u27E8",
    "laquo;": u"\u00AB",
    "laquo": u"\u00AB",
    "larr;": u"\u2190",
    "lceil;": u"\u2308",
    "ldquo;": u"\u201C",
    "le;": u"\u2264",
    "lfloor;": u"\u230A",
    "lowast;": u"\u2217",
    "loz;": u"\u25CA",
    "lrm;": u"\u200E",
    "lsaquo;": u"\u2039",
    "lsquo;": u"\u2018",
    "lt;": u"\u003C",
    "lt": u"\u003C",
    "macr;": u"\u00AF",
    "macr": u"\u00AF",
    "mdash;": u"\u2014",
    "micro;": u"\u00B5",
    "micro": u"\u00B5",
    "middot;": u"\u00B7",
    "middot": u"\u00B7",
    "minus;": u"\u2212",
    "mu;": u"\u03BC",
    "nabla;": u"\u2207",
    "nbsp;": u"\u00A0",
    "nbsp": u"\u00A0",
    "ndash;": u"\u2013",
    "ne;": u"\u2260",
    "ni;": u"\u220B",
    "not;": u"\u00AC",
    "not": u"\u00AC",
    "notin;": u"\u2209",
    "nsub;": u"\u2284",
    "ntilde;": u"\u00F1",
    "ntilde": u"\u00F1",
    "nu;": u"\u03BD",
    "oacute;": u"\u00F3",
    "oacute": u"\u00F3",
    "ocirc;": u"\u00F4",
    "ocirc": u"\u00F4",
    "oelig;": u"\u0153",
    "ograve;": u"\u00F2",
    "ograve": u"\u00F2",
    "oline;": u"\u203E",
    "omega;": u"\u03C9",
    "omicron;": u"\u03BF",
    "oplus;": u"\u2295",
    "or;": u"\u2228",
    "ordf;": u"\u00AA",
    "ordf": u"\u00AA",
    "ordm;": u"\u00BA",
    "ordm": u"\u00BA",
    "oslash;": u"\u00F8",
    "oslash": u"\u00F8",
    "otilde;": u"\u00F5",
    "otilde": u"\u00F5",
    "otimes;": u"\u2297",
    "ouml;": u"\u00F6",
    "ouml": u"\u00F6",
    "para;": u"\u00B6",
    "para": u"\u00B6",
    "part;": u"\u2202",
    "permil;": u"\u2030",
    "perp;": u"\u22A5",
    "phi;": u"\u03C6",
    "pi;": u"\u03C0",
    "piv;": u"\u03D6",
    "plusmn;": u"\u00B1",
    "plusmn": u"\u00B1",
    "pound;": u"\u00A3",
    "pound": u"\u00A3",
    "prime;": u"\u2032",
    "prod;": u"\u220F",
    "prop;": u"\u221D",
    "psi;": u"\u03C8",
    "quot;": u"\u0022",
    "quot": u"\u0022",
    "rArr;": u"\u21D2",
    "radic;": u"\u221A",
    "rang;": u"\u27E9",
    "raquo;": u"\u00BB",
    "raquo": u"\u00BB",
    "rarr;": u"\u2192",
    "rceil;": u"\u2309",
    "rdquo;": u"\u201D",
    "real;": u"\u211C",
    "reg;": u"\u00AE",
    "reg": u"\u00AE",
    "rfloor;": u"\u230B",
    "rho;": u"\u03C1",
    "rlm;": u"\u200F",
    "rsaquo;": u"\u203A",
    "rsquo;": u"\u2019",
    "sbquo;": u"\u201A",
    "scaron;": u"\u0161",
    "sdot;": u"\u22C5",
    "sect;": u"\u00A7",
    "sect": u"\u00A7",
    "shy;": u"\u00AD",
    "shy": u"\u00AD",
    "sigma;": u"\u03C3",
    "sigmaf;": u"\u03C2",
    "sim;": u"\u223C",
    "spades;": u"\u2660",
    "sub;": u"\u2282",
    "sube;": u"\u2286",
    "sum;": u"\u2211",
    "sup1;": u"\u00B9",
    "sup1": u"\u00B9",
    "sup2;": u"\u00B2",
    "sup2": u"\u00B2",
    "sup3;": u"\u00B3",
    "sup3": u"\u00B3",
    "sup;": u"\u2283",
    "supe;": u"\u2287",
    "szlig;": u"\u00DF",
    "szlig": u"\u00DF",
    "tau;": u"\u03C4",
    "there4;": u"\u2234",
    "theta;": u"\u03B8",
    "thetasym;": u"\u03D1",
    "thinsp;": u"\u2009",
    "thorn;": u"\u00FE",
    "thorn": u"\u00FE",
    "tilde;": u"\u02DC",
    "times;": u"\u00D7",
    "times": u"\u00D7",
    "trade;": u"\u2122",
    "uArr;": u"\u21D1",
    "uacute;": u"\u00FA",
    "uacute": u"\u00FA",
    "uarr;": u"\u2191",
    "ucirc;": u"\u00FB",
    "ucirc": u"\u00FB",
    "ugrave;": u"\u00F9",
    "ugrave": u"\u00F9",
    "uml;": u"\u00A8",
    "uml": u"\u00A8",
    "upsih;": u"\u03D2",
    "upsilon;": u"\u03C5",
    "uuml;": u"\u00FC",
    "uuml": u"\u00FC",
    "weierp;": u"\u2118",
    "xi;": u"\u03BE",
    "yacute;": u"\u00FD",
    "yacute": u"\u00FD",
    "yen;": u"\u00A5",
    "yen": u"\u00A5",
    "yuml;": u"\u00FF",
    "yuml": u"\u00FF",
    "zeta;": u"\u03B6",
    "zwj;": u"\u200D",
    "zwnj;": u"\u200C"
}

replacementCharacters = {
    0x0:u"\uFFFD",
    0x0d:u"\u000A",
    0x80:u"\u20AC",
    0x81:u"\u0081",
    0x81:u"\u0081",
    0x82:u"\u201A",
    0x83:u"\u0192",
    0x84:u"\u201E",
    0x85:u"\u2026",
    0x86:u"\u2020",
    0x87:u"\u2021",
    0x88:u"\u02C6",
    0x89:u"\u2030",
    0x8A:u"\u0160",
    0x8B:u"\u2039",
    0x8C:u"\u0152",
    0x8D:u"\u008D",
    0x8E:u"\u017D",
    0x8F:u"\u008F",
    0x90:u"\u0090",
    0x91:u"\u2018",
    0x92:u"\u2019",
    0x93:u"\u201C",
    0x94:u"\u201D",
    0x95:u"\u2022",
    0x96:u"\u2013",
    0x97:u"\u2014",
    0x98:u"\u02DC",
    0x99:u"\u2122",
    0x9A:u"\u0161",
    0x9B:u"\u203A",
    0x9C:u"\u0153",
    0x9D:u"\u009D",
    0x9E:u"\u017E",
    0x9F:u"\u0178",
}

encodings = {
    '437': 'cp437',
    '850': 'cp850',
    '852': 'cp852',
    '855': 'cp855',
    '857': 'cp857',
    '860': 'cp860',
    '861': 'cp861',
    '862': 'cp862',
    '863': 'cp863',
    '865': 'cp865',
    '866': 'cp866',
    '869': 'cp869',
    'ansix341968': 'ascii',
    'ansix341986': 'ascii',
    'arabic': 'iso8859-6',
    'ascii': 'ascii',
    'asmo708': 'iso8859-6',
    'big5': 'big5',
    'big5hkscs': 'big5hkscs',
    'chinese': 'gbk',
    'cp037': 'cp037',
    'cp1026': 'cp1026',
    'cp154': 'ptcp154',
    'cp367': 'ascii',
    'cp424': 'cp424',
    'cp437': 'cp437',
    'cp500': 'cp500',
    'cp775': 'cp775',
    'cp819': 'windows-1252',
    'cp850': 'cp850',
    'cp852': 'cp852',
    'cp855': 'cp855',
    'cp857': 'cp857',
    'cp860': 'cp860',
    'cp861': 'cp861',
    'cp862': 'cp862',
    'cp863': 'cp863',
    'cp864': 'cp864',
    'cp865': 'cp865',
    'cp866': 'cp866',
    'cp869': 'cp869',
    'cp936': 'gbk',
    'cpgr': 'cp869',
    'cpis': 'cp861',
    'csascii': 'ascii',
    'csbig5': 'big5',
    'cseuckr': 'cp949',
    'cseucpkdfmtjapanese': 'euc_jp',
    'csgb2312': 'gbk',
    'cshproman8': 'hp-roman8',
    'csibm037': 'cp037',
    'csibm1026': 'cp1026',
    'csibm424': 'cp424',
    'csibm500': 'cp500',
    'csibm855': 'cp855',
    'csibm857': 'cp857',
    'csibm860': 'cp860',
    'csibm861': 'cp861',
    'csibm863': 'cp863',
    'csibm864': 'cp864',
    'csibm865': 'cp865',
    'csibm866': 'cp866',
    'csibm869': 'cp869',
    'csiso2022jp': 'iso2022_jp',
    'csiso2022jp2': 'iso2022_jp_2',
    'csiso2022kr': 'iso2022_kr',
    'csiso58gb231280': 'gbk',
    'csisolatin1': 'windows-1252',
    'csisolatin2': 'iso8859-2',
    'csisolatin3': 'iso8859-3',
    'csisolatin4': 'iso8859-4',
    'csisolatin5': 'windows-1254',
    'csisolatin6': 'iso8859-10',
    'csisolatinarabic': 'iso8859-6',
    'csisolatincyrillic': 'iso8859-5',
    'csisolatingreek': 'iso8859-7',
    'csisolatinhebrew': 'iso8859-8',
    'cskoi8r': 'koi8-r',
    'csksc56011987': 'cp949',
    'cspc775baltic': 'cp775',
    'cspc850multilingual': 'cp850',
    'cspc862latinhebrew': 'cp862',
    'cspc8codepage437': 'cp437',
    'cspcp852': 'cp852',
    'csptcp154': 'ptcp154',
    'csshiftjis': 'shift_jis',
    'csunicode11utf7': 'utf-7',
    'cyrillic': 'iso8859-5',
    'cyrillicasian': 'ptcp154',
    'ebcdiccpbe': 'cp500',
    'ebcdiccpca': 'cp037',
    'ebcdiccpch': 'cp500',
    'ebcdiccphe': 'cp424',
    'ebcdiccpnl': 'cp037',
    'ebcdiccpus': 'cp037',
    'ebcdiccpwt': 'cp037',
    'ecma114': 'iso8859-6',
    'ecma118': 'iso8859-7',
    'elot928': 'iso8859-7',
    'eucjp': 'euc_jp',
    'euckr': 'cp949',
    'extendedunixcodepackedformatforjapanese': 'euc_jp',
    'gb18030': 'gb18030',
    'gb2312': 'gbk',
    'gb231280': 'gbk',
    'gbk': 'gbk',
    'greek': 'iso8859-7',
    'greek8': 'iso8859-7',
    'hebrew': 'iso8859-8',
    'hproman8': 'hp-roman8',
    'hzgb2312': 'hz',
    'ibm037': 'cp037',
    'ibm1026': 'cp1026',
    'ibm367': 'ascii',
    'ibm424': 'cp424',
    'ibm437': 'cp437',
    'ibm500': 'cp500',
    'ibm775': 'cp775',
    'ibm819': 'windows-1252',
    'ibm850': 'cp850',
    'ibm852': 'cp852',
    'ibm855': 'cp855',
    'ibm857': 'cp857',
    'ibm860': 'cp860',
    'ibm861': 'cp861',
    'ibm862': 'cp862',
    'ibm863': 'cp863',
    'ibm864': 'cp864',
    'ibm865': 'cp865',
    'ibm866': 'cp866',
    'ibm869': 'cp869',
    'iso2022jp': 'iso2022_jp',
    'iso2022jp2': 'iso2022_jp_2',
    'iso2022kr': 'iso2022_kr',
    'iso646irv1991': 'ascii',
    'iso646us': 'ascii',
    'iso88591': 'windows-1252',
    'iso885910': 'iso8859-10',
    'iso8859101992': 'iso8859-10',
    'iso885911987': 'windows-1252',
    'iso885913': 'iso8859-13',
    'iso885914': 'iso8859-14',
    'iso8859141998': 'iso8859-14',
    'iso885915': 'iso8859-15',
    'iso885916': 'iso8859-16',
    'iso8859162001': 'iso8859-16',
    'iso88592': 'iso8859-2',
    'iso885921987': 'iso8859-2',
    'iso88593': 'iso8859-3',
    'iso885931988': 'iso8859-3',
    'iso88594': 'iso8859-4',
    'iso885941988': 'iso8859-4',
    'iso88595': 'iso8859-5',
    'iso885951988': 'iso8859-5',
    'iso88596': 'iso8859-6',
    'iso885961987': 'iso8859-6',
    'iso88597': 'iso8859-7',
    'iso885971987': 'iso8859-7',
    'iso88598': 'iso8859-8',
    'iso885981988': 'iso8859-8',
    'iso88599': 'windows-1254',
    'iso885991989': 'windows-1254',
    'isoceltic': 'iso8859-14',
    'isoir100': 'windows-1252',
    'isoir101': 'iso8859-2',
    'isoir109': 'iso8859-3',
    'isoir110': 'iso8859-4',
    'isoir126': 'iso8859-7',
    'isoir127': 'iso8859-6',
    'isoir138': 'iso8859-8',
    'isoir144': 'iso8859-5',
    'isoir148': 'windows-1254',
    'isoir149': 'cp949',
    'isoir157': 'iso8859-10',
    'isoir199': 'iso8859-14',
    'isoir226': 'iso8859-16',
    'isoir58': 'gbk',
    'isoir6': 'ascii',
    'koi8r': 'koi8-r',
    'koi8u': 'koi8-u',
    'korean': 'cp949',
    'ksc5601': 'cp949',
    'ksc56011987': 'cp949',
    'ksc56011989': 'cp949',
    'l1': 'windows-1252',
    'l10': 'iso8859-16',
    'l2': 'iso8859-2',
    'l3': 'iso8859-3',
    'l4': 'iso8859-4',
    'l5': 'windows-1254',
    'l6': 'iso8859-10',
    'l8': 'iso8859-14',
    'latin1': 'windows-1252',
    'latin10': 'iso8859-16',
    'latin2': 'iso8859-2',
    'latin3': 'iso8859-3',
    'latin4': 'iso8859-4',
    'latin5': 'windows-1254',
    'latin6': 'iso8859-10',
    'latin8': 'iso8859-14',
    'latin9': 'iso8859-15',
    'ms936': 'gbk',
    'mskanji': 'shift_jis',
    'pt154': 'ptcp154',
    'ptcp154': 'ptcp154',
    'r8': 'hp-roman8',
    'roman8': 'hp-roman8',
    'shiftjis': 'shift_jis',
    'tis620': 'cp874',
    'unicode11utf7': 'utf-7',
    'us': 'ascii',
    'usascii': 'ascii',
    'utf16': 'utf-16',
    'utf16be': 'utf-16-be',
    'utf16le': 'utf-16-le',
    'utf8': 'utf-8',
    'windows1250': 'cp1250',
    'windows1251': 'cp1251',
    'windows1252': 'cp1252',
    'windows1253': 'cp1253',
    'windows1254': 'cp1254',
    'windows1255': 'cp1255',
    'windows1256': 'cp1256',
    'windows1257': 'cp1257',
    'windows1258': 'cp1258',
    'windows936': 'gbk',
    'x-x-big5': 'big5'}

tokenTypes = {
    "Doctype":0,
    "Characters":1,
    "SpaceCharacters":2,
    "StartTag":3,
    "EndTag":4,
    "EmptyTag":5,
    "Comment":6,
    "ParseError":7
}

tagTokenTypes = frozenset((tokenTypes["StartTag"], tokenTypes["EndTag"], 
                           tokenTypes["EmptyTag"]))


prefixes = dict([(v,k) for k,v in namespaces.iteritems()])
prefixes["http://www.w3.org/1998/Math/MathML"] = "math"

class DataLossWarning(UserWarning):
    pass

class ReparseException(Exception):
    pass

########NEW FILE########
__FILENAME__ = formfiller
#
# The goal is to finally have a form filler where you pass data for
# each form, using the algorithm for "Seeding a form with initial values"
# See http://www.whatwg.org/specs/web-forms/current-work/#seeding
#

import _base

from html5lib.constants import spaceCharacters
spaceCharacters = u"".join(spaceCharacters)

class SimpleFilter(_base.Filter):
    def __init__(self, source, fieldStorage):
        _base.Filter.__init__(self, source)
        self.fieldStorage = fieldStorage

    def __iter__(self):
        field_indices = {}
        state = None
        field_name = None
        for token in _base.Filter.__iter__(self):
            type = token["type"]
            if type in ("StartTag", "EmptyTag"):
                name = token["name"].lower()
                if name == "input":
                    field_name = None
                    field_type = None
                    input_value_index = -1
                    input_checked_index = -1
                    for i,(n,v) in enumerate(token["data"]):
                        n = n.lower()
                        if n == u"name":
                            field_name = v.strip(spaceCharacters)
                        elif n == u"type":
                            field_type = v.strip(spaceCharacters)
                        elif n == u"checked":
                            input_checked_index = i
                        elif n == u"value":
                            input_value_index = i

                    value_list = self.fieldStorage.getlist(field_name)
                    field_index = field_indices.setdefault(field_name, 0)
                    if field_index < len(value_list):
                        value = value_list[field_index]
                    else:
                        value = ""

                    if field_type in (u"checkbox", u"radio"):
                        if value_list:
                            if token["data"][input_value_index][1] == value:
                                if input_checked_index < 0:
                                    token["data"].append((u"checked", u""))
                                field_indices[field_name] = field_index + 1
                            elif input_checked_index >= 0:
                                del token["data"][input_checked_index]

                    elif field_type not in (u"button", u"submit", u"reset"):
                        if input_value_index >= 0:
                            token["data"][input_value_index] = (u"value", value)
                        else:
                            token["data"].append((u"value", value))
                        field_indices[field_name] = field_index + 1

                    field_type = None
                    field_name = None

                elif name == "textarea":
                    field_type = "textarea"
                    field_name = dict((token["data"])[::-1])["name"]

                elif name == "select":
                    field_type = "select"
                    attributes = dict(token["data"][::-1])
                    field_name = attributes.get("name")
                    is_select_multiple = "multiple" in attributes
                    is_selected_option_found = False

                elif field_type == "select" and field_name and name == "option":
                    option_selected_index = -1
                    option_value = None
                    for i,(n,v) in enumerate(token["data"]):
                        n = n.lower()
                        if n == "selected":
                            option_selected_index = i
                        elif n == "value":
                            option_value = v.strip(spaceCharacters)
                    if option_value is None:
                        raise NotImplementedError("<option>s without a value= attribute")
                    else:
                        value_list = self.fieldStorage.getlist(field_name)
                        if value_list:
                            field_index = field_indices.setdefault(field_name, 0)
                            if field_index < len(value_list):
                                value = value_list[field_index]
                            else:
                                value = ""
                            if (is_select_multiple or not is_selected_option_found) and option_value == value:
                                if option_selected_index < 0:
                                    token["data"].append((u"selected", u""))
                                field_indices[field_name] = field_index + 1
                                is_selected_option_found = True
                            elif option_selected_index >= 0:
                                del token["data"][option_selected_index]

            elif field_type is not None and field_name and type == "EndTag":
                name = token["name"].lower()
                if name == field_type:
                    if name == "textarea":
                        value_list = self.fieldStorage.getlist(field_name)
                        if value_list:
                            field_index = field_indices.setdefault(field_name, 0)
                            if field_index < len(value_list):
                                value = value_list[field_index]
                            else:
                                value = ""
                            yield {"type": "Characters", "data": value}
                            field_indices[field_name] = field_index + 1

                    field_name = None

                elif name == "option" and field_type == "select":
                    pass # TODO: part of "option without value= attribute" processing

            elif field_type == "textarea":
                continue # ignore token

            yield token

########NEW FILE########
__FILENAME__ = inject_meta_charset
import _base

class Filter(_base.Filter):
    def __init__(self, source, encoding):
        _base.Filter.__init__(self, source)
        self.encoding = encoding

    def __iter__(self):
        state = "pre_head"
        meta_found = (self.encoding is None)
        pending = []

        for token in _base.Filter.__iter__(self):
            type = token["type"]
            if type == "StartTag":
                if token["name"].lower() == "head":
                    state = "in_head"

            elif type == "EmptyTag":
                if token["name"].lower() == "meta":
                   # replace charset with actual encoding
                   has_http_equiv_content_type = False
                   content_index = -1
                   for i,(name,value) in enumerate(token["data"]):
                       if name.lower() == 'charset':
                          token["data"][i] = (u'charset', self.encoding)
                          meta_found = True
                          break
                       elif name == 'http-equiv' and value.lower() == 'content-type':
                           has_http_equiv_content_type = True
                       elif name == 'content':
                           content_index = i
                   else:
                       if has_http_equiv_content_type and content_index >= 0:
                           token["data"][content_index] = (u'content', u'text/html; charset=%s' % self.encoding)
                           meta_found = True

                elif token["name"].lower() == "head" and not meta_found:
                    # insert meta into empty head
                    yield {"type": "StartTag", "name": "head",
                           "data": token["data"]}
                    yield {"type": "EmptyTag", "name": "meta",
                           "data": [["charset", self.encoding]]}
                    yield {"type": "EndTag", "name": "head"}
                    meta_found = True
                    continue

            elif type == "EndTag":
                if token["name"].lower() == "head" and pending:
                    # insert meta into head (if necessary) and flush pending queue
                    yield pending.pop(0)
                    if not meta_found:
                        yield {"type": "EmptyTag", "name": "meta",
                               "data": [["charset", self.encoding]]}
                    while pending:
                        yield pending.pop(0)
                    meta_found = True
                    state = "post_head"

            if state == "in_head":
                pending.append(token)
            else:
                yield token

########NEW FILE########
__FILENAME__ = lint
from gettext import gettext
_ = gettext

import _base
from html5lib.constants import cdataElements, rcdataElements, voidElements

from html5lib.constants import spaceCharacters
spaceCharacters = u"".join(spaceCharacters)

class LintError(Exception): pass

class Filter(_base.Filter):
    def __iter__(self):
        open_elements = []
        contentModelFlag = "PCDATA"
        for token in _base.Filter.__iter__(self):
            type = token["type"]
            if type in ("StartTag", "EmptyTag"):
                name = token["name"]
                if contentModelFlag != "PCDATA":
                    raise LintError(_("StartTag not in PCDATA content model flag: %s") % name)
                if not isinstance(name, unicode):
                    raise LintError(_(u"Tag name is not a string: %r") % name)
                if not name:
                    raise LintError(_(u"Empty tag name"))
                if type == "StartTag" and name in voidElements:
                    raise LintError(_(u"Void element reported as StartTag token: %s") % name)
                elif type == "EmptyTag" and name not in voidElements:
                    raise LintError(_(u"Non-void element reported as EmptyTag token: %s") % token["name"])
                if type == "StartTag":
                    open_elements.append(name)
                for name, value in token["data"]:
                    if not isinstance(name, unicode):
                        raise LintError(_("Attribute name is not a string: %r") % name)
                    if not name:
                        raise LintError(_(u"Empty attribute name"))
                    if not isinstance(value, unicode):
                        raise LintError(_("Attribute value is not a string: %r") % value)
                if name in cdataElements:
                    contentModelFlag = "CDATA"
                elif name in rcdataElements:
                    contentModelFlag = "RCDATA"
                elif name == "plaintext":
                    contentModelFlag = "PLAINTEXT"

            elif type == "EndTag":
                name = token["name"]
                if not isinstance(name, unicode):
                    raise LintError(_(u"Tag name is not a string: %r") % name)
                if not name:
                    raise LintError(_(u"Empty tag name"))
                if name in voidElements:
                    raise LintError(_(u"Void element reported as EndTag token: %s") % name)
                start_name = open_elements.pop()
                if start_name != name:
                    raise LintError(_(u"EndTag (%s) does not match StartTag (%s)") % (name, start_name))
                contentModelFlag = "PCDATA"

            elif type == "Comment":
                if contentModelFlag != "PCDATA":
                    raise LintError(_("Comment not in PCDATA content model flag"))

            elif type in ("Characters", "SpaceCharacters"):
                data = token["data"]
                if not isinstance(data, unicode):
                    raise LintError(_("Attribute name is not a string: %r") % data)
                if not data:
                    raise LintError(_(u"%s token with empty data") % type)
                if type == "SpaceCharacters":
                    data = data.strip(spaceCharacters)
                    if data:
                        raise LintError(_(u"Non-space character(s) found in SpaceCharacters token: ") % data)

            elif type == "Doctype":
                name = token["name"]
                if contentModelFlag != "PCDATA":
                    raise LintError(_("Doctype not in PCDATA content model flag: %s") % name)
                if not isinstance(name, unicode):
                    raise LintError(_(u"Tag name is not a string: %r") % name)
                # XXX: what to do with token["data"] ?

            elif type in ("ParseError", "SerializeError"):
                pass

            else:
                raise LintError(_(u"Unknown token type: %s") % type)

            yield token

########NEW FILE########
__FILENAME__ = optionaltags
import _base

class Filter(_base.Filter):
    def slider(self):
        previous1 = previous2 = None
        for token in self.source:
            if previous1 is not None:
                yield previous2, previous1, token
            previous2 = previous1
            previous1 = token
        yield previous2, previous1, None

    def __iter__(self):
        for previous, token, next in self.slider():
            type = token["type"]
            if type == "StartTag":
                if (token["data"] or 
                    not self.is_optional_start(token["name"], previous, next)):
                    yield token
            elif type == "EndTag":
                if not self.is_optional_end(token["name"], next):
                    yield token
            else:
                yield token

    def is_optional_start(self, tagname, previous, next):
        type = next and next["type"] or None
        if tagname in 'html':
            # An html element's start tag may be omitted if the first thing
            # inside the html element is not a space character or a comment.
            return type not in ("Comment", "SpaceCharacters")
        elif tagname == 'head':
            # A head element's start tag may be omitted if the first thing
            # inside the head element is an element.
            # XXX: we also omit the start tag if the head element is empty
            if type in ("StartTag", "EmptyTag"):
                return True
            elif type == "EndTag":
                return next["name"] == "head"
        elif tagname == 'body':
            # A body element's start tag may be omitted if the first thing
            # inside the body element is not a space character or a comment,
            # except if the first thing inside the body element is a script
            # or style element and the node immediately preceding the body
            # element is a head element whose end tag has been omitted.
            if type in ("Comment", "SpaceCharacters"):
                return False
            elif type == "StartTag":
                # XXX: we do not look at the preceding event, so we never omit
                # the body element's start tag if it's followed by a script or
                # a style element.
                return next["name"] not in ('script', 'style')
            else:
                return True
        elif tagname == 'colgroup':
            # A colgroup element's start tag may be omitted if the first thing
            # inside the colgroup element is a col element, and if the element
            # is not immediately preceeded by another colgroup element whose
            # end tag has been omitted.
            if type in ("StartTag", "EmptyTag"):
                # XXX: we do not look at the preceding event, so instead we never
                # omit the colgroup element's end tag when it is immediately
                # followed by another colgroup element. See is_optional_end.
                return next["name"] == "col"
            else:
                return False
        elif tagname == 'tbody':
            # A tbody element's start tag may be omitted if the first thing
            # inside the tbody element is a tr element, and if the element is
            # not immediately preceeded by a tbody, thead, or tfoot element
            # whose end tag has been omitted.
            if type == "StartTag":
                # omit the thead and tfoot elements' end tag when they are
                # immediately followed by a tbody element. See is_optional_end.
                if previous and previous['type'] == 'EndTag' and \
                  previous['name'] in ('tbody','thead','tfoot'):
                    return False
                return next["name"] == 'tr'
            else:
                return False
        return False

    def is_optional_end(self, tagname, next):
        type = next and next["type"] or None
        if tagname in ('html', 'head', 'body'):
            # An html element's end tag may be omitted if the html element
            # is not immediately followed by a space character or a comment.
            return type not in ("Comment", "SpaceCharacters")
        elif tagname in ('li', 'optgroup', 'tr'):
            # A li element's end tag may be omitted if the li element is
            # immediately followed by another li element or if there is
            # no more content in the parent element.
            # An optgroup element's end tag may be omitted if the optgroup
            # element is immediately followed by another optgroup element,
            # or if there is no more content in the parent element.
            # A tr element's end tag may be omitted if the tr element is
            # immediately followed by another tr element, or if there is
            # no more content in the parent element.
            if type == "StartTag":
                return next["name"] == tagname
            else:
                return type == "EndTag" or type is None
        elif tagname in ('dt', 'dd'):
            # A dt element's end tag may be omitted if the dt element is
            # immediately followed by another dt element or a dd element.
            # A dd element's end tag may be omitted if the dd element is
            # immediately followed by another dd element or a dt element,
            # or if there is no more content in the parent element.
            if type == "StartTag":
                return next["name"] in ('dt', 'dd')
            elif tagname == 'dd':
                return type == "EndTag" or type is None
            else:
                return False
        elif tagname == 'p':
            # A p element's end tag may be omitted if the p element is
            # immediately followed by an address, article, aside,
            # blockquote, datagrid, dialog, dir, div, dl, fieldset,
            # footer, form, h1, h2, h3, h4, h5, h6, header, hr, menu,
            # nav, ol, p, pre, section, table, or ul, element, or if
            # there is no more content in the parent element.
            if type in ("StartTag", "EmptyTag"):
                return next["name"] in ('address', 'article', 'aside',
                                        'blockquote', 'datagrid', 'dialog', 
                                        'dir', 'div', 'dl', 'fieldset', 'footer',
                                        'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                        'header', 'hr', 'menu', 'nav', 'ol', 
                                        'p', 'pre', 'section', 'table', 'ul')
            else:
                return type == "EndTag" or type is None
        elif tagname == 'option':
            # An option element's end tag may be omitted if the option
            # element is immediately followed by another option element,
            # or if it is immediately followed by an <code>optgroup</code>
            # element, or if there is no more content in the parent
            # element.
            if type == "StartTag":
                return next["name"] in ('option', 'optgroup')
            else:
                return type == "EndTag" or type is None
        elif tagname in ('rt', 'rp'):
            # An rt element's end tag may be omitted if the rt element is
            # immediately followed by an rt or rp element, or if there is
            # no more content in the parent element.
            # An rp element's end tag may be omitted if the rp element is
            # immediately followed by an rt or rp element, or if there is
            # no more content in the parent element.
            if type == "StartTag":
                return next["name"] in ('rt', 'rp')
            else:
                return type == "EndTag" or type is None
        elif tagname == 'colgroup':
            # A colgroup element's end tag may be omitted if the colgroup
            # element is not immediately followed by a space character or
            # a comment.
            if type in ("Comment", "SpaceCharacters"):
                return False
            elif type == "StartTag":
                # XXX: we also look for an immediately following colgroup
                # element. See is_optional_start.
                return next["name"] != 'colgroup'
            else:
                return True
        elif tagname in ('thead', 'tbody'):
            # A thead element's end tag may be omitted if the thead element
            # is immediately followed by a tbody or tfoot element.
            # A tbody element's end tag may be omitted if the tbody element
            # is immediately followed by a tbody or tfoot element, or if
            # there is no more content in the parent element.
            # A tfoot element's end tag may be omitted if the tfoot element
            # is immediately followed by a tbody element, or if there is no
            # more content in the parent element.
            # XXX: we never omit the end tag when the following element is
            # a tbody. See is_optional_start.
            if type == "StartTag":
                return next["name"] in ['tbody', 'tfoot']
            elif tagname == 'tbody':
                return type == "EndTag" or type is None
            else:
                return False
        elif tagname == 'tfoot':
            # A tfoot element's end tag may be omitted if the tfoot element
            # is immediately followed by a tbody element, or if there is no
            # more content in the parent element.
            # XXX: we never omit the end tag when the following element is
            # a tbody. See is_optional_start.
            if type == "StartTag":
                return next["name"] == 'tbody'
            else:
                return type == "EndTag" or type is None
        elif tagname in ('td', 'th'):
            # A td element's end tag may be omitted if the td element is
            # immediately followed by a td or th element, or if there is
            # no more content in the parent element.
            # A th element's end tag may be omitted if the th element is
            # immediately followed by a td or th element, or if there is
            # no more content in the parent element.
            if type == "StartTag":
                return next["name"] in ('td', 'th')
            else:
                return type == "EndTag" or type is None
        return False

########NEW FILE########
__FILENAME__ = sanitizer
import _base
from html5lib.sanitizer import HTMLSanitizerMixin

class Filter(_base.Filter, HTMLSanitizerMixin):
    def __iter__(self):
        for token in _base.Filter.__iter__(self):
            token = self.sanitize_token(token)
            if token: yield token

########NEW FILE########
__FILENAME__ = whitespace
try:
    frozenset
except NameError:
    # Import from the sets module for python 2.3
    from sets import ImmutableSet as frozenset

import re

import _base
from html5lib.constants import rcdataElements, spaceCharacters
spaceCharacters = u"".join(spaceCharacters)

SPACES_REGEX = re.compile(u"[%s]+" % spaceCharacters)

class Filter(_base.Filter):

    spacePreserveElements = frozenset(["pre", "textarea"] + list(rcdataElements))

    def __iter__(self):
        preserve = 0
        for token in _base.Filter.__iter__(self):
            type = token["type"]
            if type == "StartTag" \
              and (preserve or token["name"] in self.spacePreserveElements):
                preserve += 1

            elif type == "EndTag" and preserve:
                preserve -= 1

            elif not preserve and type == "SpaceCharacters" and token["data"]:
                # Test on token["data"] above to not introduce spaces where there were not
                token["data"] = u" "

            elif not preserve and type == "Characters":
                token["data"] = collapse_spaces(token["data"])

            yield token

def collapse_spaces(text):
    return SPACES_REGEX.sub(' ', text)


########NEW FILE########
__FILENAME__ = _base

class Filter(object):
    def __init__(self, source):
        self.source = source

    def __iter__(self):
        return iter(self.source)

    def __getattr__(self, name):
        return getattr(self.source, name)

########NEW FILE########
__FILENAME__ = html5parser
try:
    frozenset
except NameError:
    # Import from the sets module for python 2.3
    from sets import Set as set
    from sets import ImmutableSet as frozenset

try:
    any
except:
    # Implement 'any' for python 2.4 and previous
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False
        
try:
    "abc".startswith(("a", "b"))
    def startswithany(str, prefixes):
        return str.startswith(prefixes)
except:
    # Python 2.4 doesn't accept a tuple as argument to string startswith
    def startswithany(str, prefixes):
        for prefix in prefixes:
            if str.startswith(prefix):
                return True
        return False

import sys

import inputstream
import tokenizer

import treebuilders
from treebuilders._base import Marker
from treebuilders import simpletree

import utils
from constants import spaceCharacters, asciiUpper2Lower
from constants import scopingElements, formattingElements, specialElements
from constants import headingElements, tableInsertModeElements
from constants import cdataElements, rcdataElements, voidElements
from constants import tokenTypes, ReparseException, namespaces

def parse(doc, treebuilder="simpletree", encoding=None, 
          namespaceHTMLElements=True):
    tb = treebuilders.getTreeBuilder(treebuilder)
    p = HTMLParser(tb, namespaceHTMLElements=namespaceHTMLElements)
    return p.parse(doc, encoding=encoding)

def parseFragment(doc, container="div", treebuilder="simpletree", encoding=None, 
                  namespaceHTMLElements=True):
    tb = treebuilders.getTreeBuilder(treebuilder)
    p = HTMLParser(tb, namespaceHTMLElements=namespaceHTMLElements)
    return p.parseFragment(doc, container=container, encoding=encoding)

class HTMLParser(object):
    """HTML parser. Generates a tree structure from a stream of (possibly
        malformed) HTML"""

    def __init__(self, tree = simpletree.TreeBuilder,
                 tokenizer = tokenizer.HTMLTokenizer, strict = False,
                 namespaceHTMLElements = True):
        """
        strict - raise an exception when a parse error is encountered

        tree - a treebuilder class controlling the type of tree that will be
        returned. Built in treebuilders can be accessed through
        html5lib.treebuilders.getTreeBuilder(treeType)
        
        tokenizer - a class that provides a stream of tokens to the treebuilder.
        This may be replaced for e.g. a sanitizer which converts some tags to
        text
        """

        # Raise an exception on the first error encountered
        self.strict = strict

        self.tree = tree(namespaceHTMLElements)
        self.tokenizer_class = tokenizer
        self.errors = []

        self.phases = {
            "initial": InitialPhase(self, self.tree),
            "beforeHtml": BeforeHtmlPhase(self, self.tree),
            "beforeHead": BeforeHeadPhase(self, self.tree),
            "inHead": InHeadPhase(self, self.tree),
            # XXX "inHeadNoscript": InHeadNoScriptPhase(self, self.tree),
            "afterHead": AfterHeadPhase(self, self.tree),
            "inBody": InBodyPhase(self, self.tree),
            "text": TextPhase(self, self.tree),
            "inTable": InTablePhase(self, self.tree),
            "inTableText": InTableTextPhase(self, self.tree),
            "inCaption": InCaptionPhase(self, self.tree),
            "inColumnGroup": InColumnGroupPhase(self, self.tree),
            "inTableBody": InTableBodyPhase(self, self.tree),
            "inRow": InRowPhase(self, self.tree),
            "inCell": InCellPhase(self, self.tree),
            "inSelect": InSelectPhase(self, self.tree),
            "inSelectInTable": InSelectInTablePhase(self, self.tree),
            "inForeignContent": InForeignContentPhase(self, self.tree),
            "afterBody": AfterBodyPhase(self, self.tree),
            "inFrameset": InFramesetPhase(self, self.tree),
            "afterFrameset": AfterFramesetPhase(self, self.tree),
            "afterAfterBody": AfterAfterBodyPhase(self, self.tree),
            "afterAfterFrameset": AfterAfterFramesetPhase(self, self.tree),
            # XXX after after frameset
        }

    def _parse(self, stream, innerHTML=False, container="div",
               encoding=None, parseMeta=True, useChardet=True, **kwargs):

        self.innerHTMLMode = innerHTML
        self.container = container
        self.tokenizer = self.tokenizer_class(stream, encoding=encoding,
                                              parseMeta=parseMeta,
                                              useChardet=useChardet, **kwargs)
        self.reset()

        while True:
            try:
                self.mainLoop()
                break
            except ReparseException, e:
                self.reset()

    def reset(self):
        self.tree.reset()
        self.firstStartTag = False
        self.errors = []
        # "quirks" / "limited quirks" / "no quirks"
        self.compatMode = "no quirks"

        if self.innerHTMLMode:
            self.innerHTML = self.container.lower()

            if self.innerHTML in cdataElements:
                self.tokenizer.state = self.tokenizer.rcdataState
            elif self.innerHTML in rcdataElements:
                self.tokenizer.state = self.tokenizer.rawtextState
            elif self.innerHTML == 'plaintext':
                self.tokenizer.state = self.tokenizer.plaintextState
            else:
                # state already is data state
                # self.tokenizer.state = self.tokenizer.dataState
                pass
            self.phase = self.phases["beforeHtml"]
            self.phase.insertHtmlElement()
            self.resetInsertionMode()
        else:
            self.innerHTML = False
            self.phase = self.phases["initial"]

        self.lastPhase = None
        self.secondaryPhase = None

        self.beforeRCDataPhase = None

        self.framesetOK = True
        
    def mainLoop(self):
        (CharactersToken, 
         SpaceCharactersToken, 
         StartTagToken,
         EndTagToken, 
         CommentToken,
         DoctypeToken) = (tokenTypes["Characters"],
                          tokenTypes["SpaceCharacters"],
                          tokenTypes["StartTag"],
                          tokenTypes["EndTag"],
                          tokenTypes["Comment"],
                          tokenTypes["Doctype"])

        CharactersToken = tokenTypes["Characters"]
        SpaceCharactersToken = tokenTypes["SpaceCharacters"]
        StartTagToken = tokenTypes["StartTag"]
        EndTagToken = tokenTypes["EndTag"]
        CommentToken = tokenTypes["Comment"]
        DoctypeToken = tokenTypes["Doctype"]
        
        
        for token in self.normalizedTokens():
            type = token["type"]
            if type == CharactersToken:
                self.phase.processCharacters(token)
            elif type == SpaceCharactersToken:
                self.phase.processSpaceCharacters(token)
            elif type == StartTagToken:
                self.selfClosingAcknowledged = False
                self.phase.processStartTag(token)
                if (token["selfClosing"]
                    and not self.selfClosingAcknowledged):
                    self.parseError("non-void-element-with-trailing-solidus",
                                    {"name":token["name"]})
            elif type == EndTagToken:
                self.phase.processEndTag(token)
            elif type == CommentToken:
                self.phase.processComment(token)
            elif type == DoctypeToken:
                self.phase.processDoctype(token)
            else:
                self.parseError(token["data"], token.get("datavars", {}))

        # When the loop finishes it's EOF
        self.phase.processEOF()

    def normalizedTokens(self):
        for token in self.tokenizer:
            yield self.normalizeToken(token)

    def parse(self, stream, encoding=None, parseMeta=True, useChardet=True):
        """Parse a HTML document into a well-formed tree

        stream - a filelike object or string containing the HTML to be parsed

        The optional encoding parameter must be a string that indicates
        the encoding.  If specified, that encoding will be used,
        regardless of any BOM or later declaration (such as in a meta
        element)
        """
        self._parse(stream, innerHTML=False, encoding=encoding, 
                    parseMeta=parseMeta, useChardet=useChardet)
        return self.tree.getDocument()
    
    def parseFragment(self, stream, container="div", encoding=None,
                      parseMeta=False, useChardet=True):
        """Parse a HTML fragment into a well-formed tree fragment
        
        container - name of the element we're setting the innerHTML property
        if set to None, default to 'div'

        stream - a filelike object or string containing the HTML to be parsed

        The optional encoding parameter must be a string that indicates
        the encoding.  If specified, that encoding will be used,
        regardless of any BOM or later declaration (such as in a meta
        element)
        """
        self._parse(stream, True, container=container, encoding=encoding)
        return self.tree.getFragment()

    def parseError(self, errorcode="XXX-undefined-error", datavars={}):
        # XXX The idea is to make errorcode mandatory.
        self.errors.append((self.tokenizer.stream.position(), errorcode, datavars))
        if self.strict:
            raise ParseError

    def normalizeToken(self, token):
        """ HTML5 specific normalizations to the token stream """

        if token["type"] == tokenTypes["StartTag"]:
            token["data"] = dict(token["data"][::-1])

        return token

    def adjustMathMLAttributes(self, token):
        replacements = {"definitionurl":"definitionURL"}
        for k,v in replacements.iteritems():
            if k in token["data"]:
                token["data"][v] = token["data"][k]
                del token["data"][k]

    def adjustSVGAttributes(self, token):
        replacements = {
            "attributename" : "attributeName",
            "attributetype" : "attributeType",
            "basefrequency" : "baseFrequency",
            "baseprofile" : "baseProfile",
            "calcmode" : "calcMode",
            "clippathunits" : "clipPathUnits",
            "contentscripttype" : "contentScriptType",
            "contentstyletype" : "contentStyleType",
            "diffuseconstant" : "diffuseConstant",
            "edgemode" : "edgeMode",
            "externalresourcesrequired" : "externalResourcesRequired",
            "filterres" : "filterRes",
            "filterunits" : "filterUnits",
            "glyphref" : "glyphRef",
            "gradienttransform" : "gradientTransform",
            "gradientunits" : "gradientUnits",
            "kernelmatrix" : "kernelMatrix",
            "kernelunitlength" : "kernelUnitLength",
            "keypoints" : "keyPoints",
            "keysplines" : "keySplines",
            "keytimes" : "keyTimes",
            "lengthadjust" : "lengthAdjust",
            "limitingconeangle" : "limitingConeAngle",
            "markerheight" : "markerHeight",
            "markerunits" : "markerUnits",
            "markerwidth" : "markerWidth",
            "maskcontentunits" : "maskContentUnits",
            "maskunits" : "maskUnits",
            "numoctaves" : "numOctaves",
            "pathlength" : "pathLength",
            "patterncontentunits" : "patternContentUnits",
            "patterntransform" : "patternTransform",
            "patternunits" : "patternUnits",
            "pointsatx" : "pointsAtX",
            "pointsaty" : "pointsAtY",
            "pointsatz" : "pointsAtZ",
            "preservealpha" : "preserveAlpha",
            "preserveaspectratio" : "preserveAspectRatio",
            "primitiveunits" : "primitiveUnits",
            "refx" : "refX",
            "refy" : "refY",
            "repeatcount" : "repeatCount",
            "repeatdur" : "repeatDur",
            "requiredextensions" : "requiredExtensions",
            "requiredfeatures" : "requiredFeatures",
            "specularconstant" : "specularConstant",
            "specularexponent" : "specularExponent",
            "spreadmethod" : "spreadMethod",
            "startoffset" : "startOffset",
            "stddeviation" : "stdDeviation",
            "stitchtiles" : "stitchTiles",
            "surfacescale" : "surfaceScale",
            "systemlanguage" : "systemLanguage",
            "tablevalues" : "tableValues",
            "targetx" : "targetX",
            "targety" : "targetY",
            "textlength" : "textLength",
            "viewbox" : "viewBox",
            "viewtarget" : "viewTarget",
            "xchannelselector" : "xChannelSelector",
            "ychannelselector" : "yChannelSelector",
            "zoomandpan" : "zoomAndPan"
            }
        for originalName in token["data"].keys():
            if originalName in replacements:
                svgName = replacements[originalName]
                token["data"][svgName] = token["data"][originalName]
                del token["data"][originalName]

    def adjustForeignAttributes(self, token):
        replacements = {
            "xlink:actuate":("xlink", "actuate", namespaces["xlink"]),
            "xlink:arcrole":("xlink", "arcrole", namespaces["xlink"]),
            "xlink:href":("xlink", "href", namespaces["xlink"]),
            "xlink:role":("xlink", "role", namespaces["xlink"]),
            "xlink:show":("xlink", "show", namespaces["xlink"]),
            "xlink:title":("xlink", "title", namespaces["xlink"]),
            "xlink:type":("xlink", "type", namespaces["xlink"]),
            "xml:base":("xml", "base", namespaces["xml"]),
            "xml:lang":("xml", "lang", namespaces["xml"]),
            "xml:space":("xml", "space", namespaces["xml"]),
            "xmlns":(None, "xmlns", namespaces["xmlns"]),
            "xmlns:xlink":("xmlns", "xlink", namespaces["xmlns"])
            }

        for originalName in token["data"].iterkeys():
            if originalName in replacements:
                foreignName = replacements[originalName]
                token["data"][foreignName] = token["data"][originalName]
                del token["data"][originalName]

    def resetInsertionMode(self):
        # The name of this method is mostly historical. (It's also used in the
        # specification.)
        last = False
        newModes = {
            "select":"inSelect",
            "td":"inCell",
            "th":"inCell",
            "tr":"inRow",
            "tbody":"inTableBody",
            "thead":"inTableBody",
            "tfoot":"inTableBody",
            "caption":"inCaption",
            "colgroup":"inColumnGroup",
            "table":"inTable",
            "head":"inBody",
            "body":"inBody",
            "frameset":"inFrameset"
        }
        for node in self.tree.openElements[::-1]:
            nodeName = node.name
            if node == self.tree.openElements[0]:
                last = True
                if nodeName not in ['td', 'th']:
                    # XXX
                    assert self.innerHTML
                    nodeName = self.innerHTML
            # Check for conditions that should only happen in the innerHTML
            # case
            if nodeName in ("select", "colgroup", "head", "frameset"):
                # XXX
                assert self.innerHTML
            if nodeName in newModes:
                self.phase = self.phases[newModes[nodeName]]
                break
            elif node.namespace in (namespaces["mathml"], namespaces["svg"]):
                self.phase = self.phases["inForeignContent"]
                self.secondaryPhase = self.phases["inBody"]
                break
            elif nodeName == "html":
                if self.tree.headPointer is None:
                    self.phase = self.phases["beforeHead"]
                else:
                   self.phase = self.phases["afterHead"]
                break
            elif last:
                self.phase = self.phases["inBody"]
                break

    def parseRCDataRawtext(self, token, contentType):
        """Generic RCDATA/RAWTEXT Parsing algorithm
        contentType - RCDATA or RAWTEXT
        """
        assert contentType in ("RAWTEXT", "RCDATA")
        
        element = self.tree.insertElement(token)
        
        if contentType == "RAWTEXT":
            self.tokenizer.state = self.tokenizer.rawtextState
        else:
            self.tokenizer.state = self.tokenizer.rcdataState

        self.originalPhase = self.phase

        self.phase = self.phases["text"]

class Phase(object):
    """Base class for helper object that implements each phase of processing
    """
    # Order should be (they can be omitted):
    # * EOF
    # * Comment
    # * Doctype
    # * SpaceCharacters
    # * Characters
    # * StartTag
    #   - startTag* methods
    # * EndTag
    #   - endTag* methods

    def __init__(self, parser, tree):
        self.parser = parser
        self.tree = tree

    def processEOF(self):
        raise NotImplementedError

    def processComment(self, token):
        # For most phases the following is correct. Where it's not it will be
        # overridden.
        self.tree.insertComment(token, self.tree.openElements[-1])

    def processDoctype(self, token):
        self.parser.parseError("unexpected-doctype")

    def processCharacters(self, token):
        self.tree.insertText(token["data"])

    def processSpaceCharacters(self, token):
        self.tree.insertText(token["data"])

    def processStartTag(self, token):
        self.startTagHandler[token["name"]](token)

    def startTagHtml(self, token):
        if self.parser.firstStartTag == False and token["name"] == "html":
           self.parser.parseError("non-html-root")
        # XXX Need a check here to see if the first start tag token emitted is
        # this token... If it's not, invoke self.parser.parseError().
        for attr, value in token["data"].iteritems():
            if attr not in self.tree.openElements[0].attributes:
                self.tree.openElements[0].attributes[attr] = value
        self.parser.firstStartTag = False

    def processEndTag(self, token):
        self.endTagHandler[token["name"]](token)

class InitialPhase(Phase):
    def processSpaceCharacters(self, token):
        pass
    
    def processComment(self, token):
        self.tree.insertComment(token, self.tree.document)

    def processDoctype(self, token):
        name = token["name"]
        publicId = token["publicId"]
        systemId = token["systemId"]
        correct = token["correct"]

        if (name != "html" or publicId != None or
            systemId != None and systemId != "about:legacy-compat"):
            self.parser.parseError("unknown-doctype")
        
        if publicId is None:
            publicId = ""
            
        self.tree.insertDoctype(token)

        if publicId != "":
            publicId = publicId.translate(asciiUpper2Lower)

        if (not correct or token["name"] != "html"
            or startswithany(publicId,
            ("+//silmaril//dtd html pro v0r11 19970101//",
             "-//advasoft ltd//dtd html 3.0 aswedit + extensions//",
             "-//as//dtd html 3.0 aswedit + extensions//",
             "-//ietf//dtd html 2.0 level 1//",
             "-//ietf//dtd html 2.0 level 2//",
             "-//ietf//dtd html 2.0 strict level 1//",
             "-//ietf//dtd html 2.0 strict level 2//",
             "-//ietf//dtd html 2.0 strict//",
             "-//ietf//dtd html 2.0//",
             "-//ietf//dtd html 2.1e//",
             "-//ietf//dtd html 3.0//",
             "-//ietf//dtd html 3.2 final//",
             "-//ietf//dtd html 3.2//",
             "-//ietf//dtd html 3//",
             "-//ietf//dtd html level 0//",
             "-//ietf//dtd html level 1//",
             "-//ietf//dtd html level 2//",
             "-//ietf//dtd html level 3//",
             "-//ietf//dtd html strict level 0//",
             "-//ietf//dtd html strict level 1//",
             "-//ietf//dtd html strict level 2//",
             "-//ietf//dtd html strict level 3//",
             "-//ietf//dtd html strict//",
             "-//ietf//dtd html//",
             "-//metrius//dtd metrius presentational//",
             "-//microsoft//dtd internet explorer 2.0 html strict//",
             "-//microsoft//dtd internet explorer 2.0 html//",
             "-//microsoft//dtd internet explorer 2.0 tables//",
             "-//microsoft//dtd internet explorer 3.0 html strict//",
             "-//microsoft//dtd internet explorer 3.0 html//",
             "-//microsoft//dtd internet explorer 3.0 tables//",
             "-//netscape comm. corp.//dtd html//",
             "-//netscape comm. corp.//dtd strict html//",
             "-//o'reilly and associates//dtd html 2.0//",
             "-//o'reilly and associates//dtd html extended 1.0//",
             "-//o'reilly and associates//dtd html extended relaxed 1.0//",
             "-//softquad software//dtd hotmetal pro 6.0::19990601::extensions to html 4.0//",
             "-//softquad//dtd hotmetal pro 4.0::19971010::extensions to html 4.0//",
             "-//spyglass//dtd html 2.0 extended//",
             "-//sq//dtd html 2.0 hotmetal + extensions//",
             "-//sun microsystems corp.//dtd hotjava html//",
             "-//sun microsystems corp.//dtd hotjava strict html//",
             "-//w3c//dtd html 3 1995-03-24//",
             "-//w3c//dtd html 3.2 draft//",
             "-//w3c//dtd html 3.2 final//",
             "-//w3c//dtd html 3.2//",
             "-//w3c//dtd html 3.2s draft//",
             "-//w3c//dtd html 4.0 frameset//",
             "-//w3c//dtd html 4.0 transitional//",
             "-//w3c//dtd html experimental 19960712//",
             "-//w3c//dtd html experimental 970421//",
             "-//w3c//dtd w3 html//",
             "-//w3o//dtd w3 html 3.0//",
             "-//webtechs//dtd mozilla html 2.0//",
             "-//webtechs//dtd mozilla html//"))
            or publicId in
                ("-//w3o//dtd w3 html strict 3.0//en//",
                 "-/w3c/dtd html 4.0 transitional/en",
                 "html")
            or startswithany(publicId,
                ("-//w3c//dtd html 4.01 frameset//",
                 "-//w3c//dtd html 4.01 transitional//")) and 
                systemId == None
            or systemId and systemId.lower() == "http://www.ibm.com/data/dtd/v11/ibmxhtml1-transitional.dtd"):
            self.parser.compatMode = "quirks"
        elif (startswithany(publicId,
                ("-//w3c//dtd xhtml 1.0 frameset//",
                 "-//w3c//dtd xhtml 1.0 transitional//"))
              or startswithany(publicId,
                  ("-//w3c//dtd html 4.01 frameset//",
                   "-//w3c//dtd html 4.01 transitional//")) and 
                  systemId != None):
            self.parser.compatMode = "limited quirks"

        self.parser.phase = self.parser.phases["beforeHtml"]
    
    def anythingElse(self):
        self.parser.compatMode = "quirks"
        self.parser.phase = self.parser.phases["beforeHtml"]

    def processCharacters(self, token):
        self.parser.parseError("expected-doctype-but-got-chars")
        self.anythingElse()
        self.parser.phase.processCharacters(token)

    def processStartTag(self, token):
        self.parser.parseError("expected-doctype-but-got-start-tag",
          {"name": token["name"]})
        self.anythingElse()
        self.parser.phase.processStartTag(token)

    def processEndTag(self, token):
        self.parser.parseError("expected-doctype-but-got-end-tag",
          {"name": token["name"]})
        self.anythingElse()
        self.parser.phase.processEndTag(token)
        
    def processEOF(self):
        self.parser.parseError("expected-doctype-but-got-eof")
        self.anythingElse()
        self.parser.phase.processEOF()


class BeforeHtmlPhase(Phase):
    # helper methods
    def insertHtmlElement(self):
        self.tree.insertRoot(impliedTagToken("html", "StartTag"))
        self.parser.phase = self.parser.phases["beforeHead"]

    # other
    def processEOF(self):
        self.insertHtmlElement()
        self.parser.phase.processEOF()

    def processComment(self, token):
        self.tree.insertComment(token, self.tree.document)

    def processSpaceCharacters(self, token):
        pass

    def processCharacters(self, token):
        self.insertHtmlElement()
        self.parser.phase.processCharacters(token)

    def processStartTag(self, token):
        if token["name"] == "html":
            self.parser.firstStartTag = True
        self.insertHtmlElement()
        self.parser.phase.processStartTag(token)

    def processEndTag(self, token):
        if token["name"] not in ("head", "body", "html", "br"):
            self.parser.parseError("unexpected-end-tag-before-html",
              {"name": token["name"]})
        else:
            self.insertHtmlElement()
            self.parser.phase.processEndTag(token)


class BeforeHeadPhase(Phase):
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            ("head", self.startTagHead)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            (("head", "body", "html", "br"), self.endTagImplyHead)
        ])
        self.endTagHandler.default = self.endTagOther

    def processEOF(self):
        self.startTagHead(impliedTagToken("head", "StartTag"))
        self.parser.phase.processEOF()

    def processSpaceCharacters(self, token):
        pass

    def processCharacters(self, token):
        self.startTagHead(impliedTagToken("head", "StartTag"))
        self.parser.phase.processCharacters(token)

    def startTagHtml(self, token):
        self.parser.phases["inBody"].processStartTag(token)

    def startTagHead(self, token):
        self.tree.insertElement(token)
        self.tree.headPointer = self.tree.openElements[-1]
        self.parser.phase = self.parser.phases["inHead"]

    def startTagOther(self, token):
        self.startTagHead(impliedTagToken("head", "StartTag"))
        self.parser.phase.processStartTag(token)

    def endTagImplyHead(self, token):
        self.startTagHead(impliedTagToken("head", "StartTag"))
        self.parser.phase.processEndTag(token)

    def endTagOther(self, token):
        self.parser.parseError("end-tag-after-implied-root",
          {"name": token["name"]})

class InHeadPhase(Phase):
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler =  utils.MethodDispatcher([
            ("html", self.startTagHtml),
            ("title", self.startTagTitle),
            (("noscript", "noframes", "style"), self.startTagNoScriptNoFramesStyle),
            ("script", self.startTagScript),
            (("base", "link", "command"), 
             self.startTagBaseLinkCommand),
            ("meta", self.startTagMeta),
            ("head", self.startTagHead)
        ])
        self.startTagHandler.default = self.startTagOther

        self. endTagHandler = utils.MethodDispatcher([
            ("head", self.endTagHead),
            (("br", "html", "body"), self.endTagHtmlBodyBr)
        ])
        self.endTagHandler.default = self.endTagOther

    # helper
    def appendToHead(self, element):
        if self.tree.headPointer is not None:
            self.tree.headPointer.appendChild(element)
        else:
            assert self.parser.innerHTML
            self.tree.openElementsw[-1].appendChild(element)

    # the real thing
    def processEOF (self):
        self.anythingElse()
        self.parser.phase.processEOF()

    def processCharacters(self, token):
        self.anythingElse()
        self.parser.phase.processCharacters(token)

    def startTagHtml(self, token):
        self.parser.phases["inBody"].processStartTag(token)

    def startTagHead(self, token):
        self.parser.parseError("two-heads-are-not-better-than-one")

    def startTagBaseLinkCommand(self, token):
        self.tree.insertElement(token)
        self.tree.openElements.pop()
        token["selfClosingAcknowledged"] = True

    def startTagMeta(self, token):
        self.tree.insertElement(token)
        self.tree.openElements.pop()
        token["selfClosingAcknowledged"] = True

        attributes = token["data"]
        if self.parser.tokenizer.stream.charEncoding[1] == "tentative":
            if "charset" in attributes:
                self.parser.tokenizer.stream.changeEncoding(attributes["charset"])
            elif "content" in attributes:
                # Encoding it as UTF-8 here is a hack, as really we should pass
                # the abstract Unicode string, and just use the
                # ContentAttrParser on that, but using UTF-8 allows all chars
                # to be encoded and as a ASCII-superset works.
                data = inputstream.EncodingBytes(attributes["content"].encode("utf-8"))
                parser = inputstream.ContentAttrParser(data)
                codec = parser.parse()
                self.parser.tokenizer.stream.changeEncoding(codec)

    def startTagTitle(self, token):
        self.parser.parseRCDataRawtext(token, "RCDATA")

    def startTagNoScriptNoFramesStyle(self, token):
        #Need to decide whether to implement the scripting-disabled case
        self.parser.parseRCDataRawtext(token, "RAWTEXT")

    def startTagScript(self, token):
        self.tree.insertElement(token)
        self.parser.tokenizer.state = self.parser.tokenizer.scriptDataState
        self.parser.originalPhase = self.parser.phase
        self.parser.phase = self.parser.phases["text"]

    def startTagOther(self, token):
        self.anythingElse()
        self.parser.phase.processStartTag(token)

    def endTagHead(self, token):
        node = self.parser.tree.openElements.pop()
        assert node.name == "head", "Expected head got %s"%node.name
        self.parser.phase = self.parser.phases["afterHead"]

    def endTagHtmlBodyBr(self, token):
        self.anythingElse()
        self.parser.phase.processEndTag(token)

    def endTagOther(self, token):
        self.parser.parseError("unexpected-end-tag", {"name": token["name"]})

    def anythingElse(self):
        self.endTagHead(impliedTagToken("head"))
        

# XXX If we implement a parser for which scripting is disabled we need to
# implement this phase.
#
# class InHeadNoScriptPhase(Phase):

class AfterHeadPhase(Phase):
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            ("body", self.startTagBody),
            ("frameset", self.startTagFrameset),
            (("base", "link", "meta", "noframes", "script", "style", "title"),
              self.startTagFromHead),
            ("head", self.startTagHead)
        ])
        self.startTagHandler.default = self.startTagOther
        self.endTagHandler = utils.MethodDispatcher([(("body", "html", "br"), 
                                                      self.endTagHtmlBodyBr)])
        self.endTagHandler.default = self.endTagOther

    def processEOF(self):
        self.anythingElse()
        self.parser.phase.processEOF()

    def processCharacters(self, token):
        self.anythingElse()
        self.parser.phase.processCharacters(token)

    def startTagBody(self, token):
        self.parser.framesetOK = False
        self.tree.insertElement(token)
        self.parser.phase = self.parser.phases["inBody"]

    def startTagFrameset(self, token):
        self.tree.insertElement(token)
        self.parser.phase = self.parser.phases["inFrameset"]

    def startTagFromHead(self, token):
        self.parser.parseError("unexpected-start-tag-out-of-my-head",
          {"name": token["name"]})
        self.tree.openElements.append(self.tree.headPointer)
        self.parser.phases["inHead"].processStartTag(token)
        for node in self.tree.openElements[::-1]:
            if node.name == "head":
                self.tree.openElements.remove(node)
                break

    def startTagHead(self, token):
        self.parser.parseError("unexpected-start-tag", {"name":token["name"]})

    def startTagOther(self, token):
        self.anythingElse()
        self.parser.phase.processStartTag(token)

    def endTagHtmlBodyBr(self, token):
        self.anythingElse()
        self.parser.phase.processEndTag(token)

    def endTagOther(self, token):
        self.parser.parseError("unexpected-end-tag", {"name":token["name"]})

    def anythingElse(self):
        self.tree.insertElement(impliedTagToken("body", "StartTag"))
        self.parser.phase = self.parser.phases["inBody"]
        self.parser.framesetOK = True


class InBodyPhase(Phase):
    # http://www.whatwg.org/specs/web-apps/current-work/#parsing-main-inbody
    # the really-really-really-very crazy mode
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        #Keep a ref to this for special handling of whitespace in <pre>
        self.processSpaceCharactersNonPre = self.processSpaceCharacters

        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            (("base", "command", "link", "meta", "noframes", "script", "style", 
              "title"), self.startTagProcessInHead),
            ("body", self.startTagBody),
            ("frameset", self.startTagFrameset),
            (("address", "article", "aside", "blockquote", "center", "datagrid",
              "details", "dir", "div", "dl", "fieldset", "figure",
              "footer", "header", "hgroup", "menu", "nav", "ol", "p",
              "section", "ul"),
              self.startTagCloseP),
            (("pre", "listing"), self.startTagPreListing),
            ("form", self.startTagForm),
            (("li", "dd", "dt"), self.startTagListItem),
            ("plaintext",self.startTagPlaintext),
            (headingElements, self.startTagHeading),
            ("a", self.startTagA),
            (("b", "big", "code", "em", "font", "i", "s", "small", "strike", 
              "strong", "tt", "u"),self.startTagFormatting),
            ("nobr", self.startTagNobr),
            ("button", self.startTagButton),
            (("applet", "marquee", "object"), self.startTagAppletMarqueeObject),
            ("xmp", self.startTagXmp),
            ("table", self.startTagTable),
            (("area", "basefont", "bgsound", "br", "embed", "img", "input",
              "keygen", "spacer", "wbr"), self.startTagVoidFormatting),
            (("param", "source"), self.startTagParamSource),
            ("hr", self.startTagHr),
            ("image", self.startTagImage),
            ("isindex", self.startTagIsIndex),
            ("textarea", self.startTagTextarea),
            ("iframe", self.startTagIFrame),
            (("noembed", "noframes", "noscript"), self.startTagRawtext),
            ("select", self.startTagSelect),
            (("rp", "rt"), self.startTagRpRt),
            (("option", "optgroup"), self.startTagOpt),
            (("math"), self.startTagMath),
            (("svg"), self.startTagSvg),
            (("caption", "col", "colgroup", "frame", "head",
              "tbody", "td", "tfoot", "th", "thead",
              "tr"), self.startTagMisplaced)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            ("body",self.endTagBody),
            ("html",self.endTagHtml),
            (("address", "article", "aside", "blockquote", "center", "datagrid",
              "details", "dir", "div", "dl", "fieldset", "figure",
              "footer", "header", "hgroup", "listing", "menu", "nav", "ol", "pre", 
              "section", "ul"), self.endTagBlock),
            ("form", self.endTagForm),
            ("p",self.endTagP),
            (("dd", "dt", "li"), self.endTagListItem),
            (headingElements, self.endTagHeading),
            (("a", "b", "big", "code", "em", "font", "i", "nobr", "s", "small",
              "strike", "strong", "tt", "u"), self.endTagFormatting),
            (("applet", "button", "marquee", "object"), self.endTagAppletButtonMarqueeObject),
            ("br", self.endTagBr),
            ])
        self.endTagHandler.default = self.endTagOther

    # helper
    def addFormattingElement(self, token):
        self.tree.insertElement(token)
        self.tree.activeFormattingElements.append(
            self.tree.openElements[-1])

    # the real deal
    def processEOF(self):
        allowed_elements = frozenset(("dd", "dt", "li", "p", "tbody", "td",
                                      "tfoot", "th", "thead", "tr", "body",
                                      "html"))
        for node in self.tree.openElements[::-1]:
            if node.name not in allowed_elements:
                self.parser.parseError("expected-closing-tag-but-got-eof")
                break
        #Stop parsing
    
    def processSpaceCharactersDropNewline(self, token):
        # Sometimes (start of <pre>, <listing>, and <textarea> blocks) we
        # want to drop leading newlines
        data = token["data"]
        self.processSpaceCharacters = self.processSpaceCharactersNonPre
        if (data.startswith("\n") and
            self.tree.openElements[-1].name in ("pre", "listing", "textarea")
            and not self.tree.openElements[-1].hasContent()):
            data = data[1:]
        if data:
            self.tree.reconstructActiveFormattingElements()
            self.tree.insertText(data)

    def processCharacters(self, token):
        self.tree.reconstructActiveFormattingElements()
        self.tree.insertText(token["data"])
        self.parser.framesetOK = False

    def processSpaceCharacters(self, token):
        self.tree.reconstructActiveFormattingElements()
        self.tree.insertText(token["data"])

    def startTagProcessInHead(self, token):
        self.parser.phases["inHead"].processStartTag(token)

    def startTagBody(self, token):
        self.parser.parseError("unexpected-start-tag", {"name": "body"})
        if (len(self.tree.openElements) == 1
            or self.tree.openElements[1].name != "body"):
            assert self.parser.innerHTML
        else:
            for attr, value in token["data"].iteritems():
                if attr not in self.tree.openElements[1].attributes:
                    self.tree.openElements[1].attributes[attr] = value

    def startTagFrameset(self, token):
        self.parser.parseError("unexpected-start-tag", {"name": "frameset"})
        if (len(self.tree.openElements) == 1 or self.tree.openElements[1].name != "body"):
            assert self.parser.innerHTML
        elif not self.parser.framesetOK:
            pass
        else:
            if self.tree.openElements[1].parent:
                self.tree.openElements[1].parent.removeChild(self.tree.openElements[1])
            while self.tree.openElements[-1].name != "html":
                self.tree.openElements.pop()
            self.tree.insertElement(token)
            self.parser.phase = self.parser.phases["inFrameset"]

    def startTagCloseP(self, token):
        if self.tree.elementInScope("p"):
            self.endTagP(impliedTagToken("p"))
        self.tree.insertElement(token)
    
    def startTagPreListing(self, token):
        if self.tree.elementInScope("p"):
            self.endTagP(impliedTagToken("p"))
        self.tree.insertElement(token)
        self.parser.framesetOK = False
        self.processSpaceCharacters = self.processSpaceCharactersDropNewline

    def startTagForm(self, token):
        if self.tree.formPointer:
            self.parser.parseError(u"unexpected-start-tag", {"name": "form"})
        else:
            if self.tree.elementInScope("p"):
                self.endTagP("p")
            self.tree.insertElement(token)
            self.tree.formPointer = self.tree.openElements[-1]

    def startTagListItem(self, token):
        self.parser.framesetOK = False

        stopNamesMap = {"li":["li"],
                        "dt":["dt", "dd"],
                        "dd":["dt", "dd"]}
        stopNames = stopNamesMap[token["name"]]
        for node in reversed(self.tree.openElements):
            if node.name in stopNames:
                self.parser.phase.processEndTag(
                    impliedTagToken(node.name, "EndTag"))
                break
            if (node.nameTuple in (scopingElements | specialElements) and
                node.name not in ("address", "div", "p")):
                break
            
        if self.tree.elementInScope("p"):
            self.parser.phase.processEndTag(
                impliedTagToken("p", "EndTag"))

        self.tree.insertElement(token)

    def startTagPlaintext(self, token):
        if self.tree.elementInScope("p"):
            self.endTagP(impliedTagToken("p"))
        self.tree.insertElement(token)
        self.parser.tokenizer.state = self.parser.tokenizer.plaintextState

    def startTagHeading(self, token):
        if self.tree.elementInScope("p"):
            self.endTagP(impliedTagToken("p"))
        if self.tree.openElements[-1].name in headingElements:
            self.parser.parseError("unexpected-start-tag", {"name": token["name"]})
            self.tree.openElements.pop()
        self.tree.insertElement(token)

    def startTagA(self, token):
        afeAElement = self.tree.elementInActiveFormattingElements("a")
        if afeAElement:
            self.parser.parseError("unexpected-start-tag-implies-end-tag",
              {"startName": "a", "endName": "a"})
            self.endTagFormatting(impliedTagToken("a"))
            if afeAElement in self.tree.openElements:
                self.tree.openElements.remove(afeAElement)
            if afeAElement in self.tree.activeFormattingElements:
                self.tree.activeFormattingElements.remove(afeAElement)
        self.tree.reconstructActiveFormattingElements()
        self.addFormattingElement(token)

    def startTagFormatting(self, token):
        self.tree.reconstructActiveFormattingElements()
        self.addFormattingElement(token)

    def startTagNobr(self, token):
        self.tree.reconstructActiveFormattingElements()
        if self.tree.elementInScope("nobr"):
            self.parser.parseError("unexpected-start-tag-implies-end-tag",
              {"startName": "nobr", "endName": "nobr"})
            self.processEndTag(impliedTagToken("nobr"))
            # XXX Need tests that trigger the following
            self.tree.reconstructActiveFormattingElements()
        self.addFormattingElement(token)

    def startTagButton(self, token):
        if self.tree.elementInScope("button"):
            self.parser.parseError("unexpected-start-tag-implies-end-tag",
              {"startName": "button", "endName": "button"})
            self.processEndTag(impliedTagToken("button"))
            self.parser.phase.processStartTag(token)
        else:
            self.tree.reconstructActiveFormattingElements()
            self.tree.insertElement(token)
            self.tree.activeFormattingElements.append(Marker)
            self.parser.framesetOK = False

    def startTagAppletMarqueeObject(self, token):
        self.tree.reconstructActiveFormattingElements()
        self.tree.insertElement(token)
        self.tree.activeFormattingElements.append(Marker)
        self.parser.framesetOK = False

    def startTagXmp(self, token):
        if self.tree.elementInScope("p"):
            self.endTagP(impliedTagToken("p"))
        self.tree.reconstructActiveFormattingElements()
        self.parser.framesetOK = False
        self.parser.parseRCDataRawtext(token, "RAWTEXT")

    def startTagTable(self, token):
        if self.parser.compatMode != "quirks":
            if self.tree.elementInScope("p"):
                self.processEndTag(impliedTagToken("p"))
        self.tree.insertElement(token)
        self.parser.framesetOK = False
        self.parser.phase = self.parser.phases["inTable"]

    def startTagVoidFormatting(self, token):
        self.tree.reconstructActiveFormattingElements()
        self.tree.insertElement(token)
        self.tree.openElements.pop()
        token["selfClosingAcknowledged"] = True
        self.parser.framesetOK = False

    def startTagParamSource(self, token):
        self.tree.insertElement(token)
        self.tree.openElements.pop()
        token["selfClosingAcknowledged"] = True

    def startTagHr(self, token):
        if self.tree.elementInScope("p"):
            self.endTagP(impliedTagToken("p"))
        self.tree.insertElement(token)
        self.tree.openElements.pop()
        token["selfClosingAcknowledged"] = True
        self.parser.framesetOK = False

    def startTagImage(self, token):
        # No really...
        self.parser.parseError("unexpected-start-tag-treated-as",
          {"originalName": "image", "newName": "img"})
        self.processStartTag(impliedTagToken("img", "StartTag",
                                             attributes=token["data"],
                                             selfClosing=token["selfClosing"]))

    def startTagIsIndex(self, token):
        self.parser.parseError("deprecated-tag", {"name": "isindex"})
        if self.tree.formPointer:
            return
        form_attrs = {}
        if "action" in token["data"]:
            form_attrs["action"] = token["data"]["action"]
        self.processStartTag(impliedTagToken("form", "StartTag",
                                             attributes=form_attrs))
        self.processStartTag(impliedTagToken("hr", "StartTag"))
        self.processStartTag(impliedTagToken("label", "StartTag"))
        # XXX Localization ...
        if "prompt" in token["data"]:
            prompt = token["data"]["prompt"]
        else:
            prompt = "This is a searchable index. Insert your search keywords here: "
        self.processCharacters(
            {"type":tokenTypes["Characters"], "data":prompt})
        attributes = token["data"].copy()
        if "action" in attributes:
            del attributes["action"]
        if "prompt" in attributes:
            del attributes["prompt"]
        attributes["name"] = "isindex"
        self.processStartTag(impliedTagToken("input", "StartTag", 
                                             attributes = attributes,
                                             selfClosing = 
                                             token["selfClosing"]))
        self.processEndTag(impliedTagToken("label"))
        self.processStartTag(impliedTagToken("hr", "StartTag"))
        self.processEndTag(impliedTagToken("form"))

    def startTagTextarea(self, token):
        self.tree.insertElement(token)
        self.parser.tokenizer.state = self.parser.tokenizer.rcdataState
        self.processSpaceCharacters = self.processSpaceCharactersDropNewline
        self.parser.framesetOK = False

    def startTagIFrame(self, token):
        self.parser.framesetOK = False
        self.startTagRawtext(token)

    def startTagRawtext(self, token):
        """iframe, noembed noframes, noscript(if scripting enabled)"""
        self.parser.parseRCDataRawtext(token, "RAWTEXT")

    def startTagOpt(self, token):
        if self.tree.elementInScope("option"):
            self.parser.phase.processEndTag(impliedTagToken("option"))
        self.tree.reconstructActiveFormattingElements()
        self.parser.tree.insertElement(token)

    def startTagSelect(self, token):
        self.tree.reconstructActiveFormattingElements()
        self.tree.insertElement(token)
        self.parser.framesetOK = False
        if self.parser.phase in (self.parser.phases["inTable"],
                                 self.parser.phases["inCaption"],
                                 self.parser.phases["inColumnGroup"],
                                 self.parser.phases["inTableBody"], 
                                 self.parser.phases["inRow"],
                                 self.parser.phases["inCell"]):
            self.parser.phase = self.parser.phases["inSelectInTable"]
        else:
            self.parser.phase = self.parser.phases["inSelect"]

    def startTagRpRt(self, token):
        if self.tree.elementInScope("ruby"):
            self.tree.generateImpliedEndTags()
            if self.tree.openElements[-1].name != "ruby":
                self.parser.parseError()
                while self.tree.openElements[-1].name != "ruby":
                    self.tree.openElements.pop()
        self.tree.insertElement(token)

    def startTagMath(self, token):
        self.tree.reconstructActiveFormattingElements()
        self.parser.adjustMathMLAttributes(token)
        self.parser.adjustForeignAttributes(token)
        token["namespace"] = namespaces["mathml"]
        self.tree.insertElement(token)
        #Need to get the parse error right for the case where the token 
        #has a namespace not equal to the xmlns attribute
        if self.parser.phase != self.parser.phases["inForeignContent"]:
            self.parser.secondaryPhase = self.parser.phase
        self.parser.phase = self.parser.phases["inForeignContent"]
        if token["selfClosing"]:
            self.tree.openElements.pop()
            token["selfClosingAcknowledged"] = True

    def startTagSvg(self, token):
        self.tree.reconstructActiveFormattingElements()
        self.parser.adjustSVGAttributes(token)
        self.parser.adjustForeignAttributes(token)
        token["namespace"] = namespaces["svg"]
        self.tree.insertElement(token)
        #Need to get the parse error right for the case where the token 
        #has a namespace not equal to the xmlns attribute
        if self.parser.phase != self.parser.phases["inForeignContent"]:
            self.parser.secondaryPhase = self.parser.phase
        self.parser.phase = self.parser.phases["inForeignContent"]
        if token["selfClosing"]:
            self.tree.openElements.pop()
            token["selfClosingAcknowledged"] = True

    def startTagMisplaced(self, token):
        """ Elements that should be children of other elements that have a
        different insertion mode; here they are ignored
        "caption", "col", "colgroup", "frame", "frameset", "head",
        "option", "optgroup", "tbody", "td", "tfoot", "th", "thead",
        "tr", "noscript"
        """
        self.parser.parseError("unexpected-start-tag-ignored", {"name": token["name"]})

    def startTagOther(self, token):
        self.tree.reconstructActiveFormattingElements()
        self.tree.insertElement(token)

    def endTagP(self, token):
        if not self.tree.elementInScope("p"):
            self.startTagCloseP(impliedTagToken("p", "StartTag"))
            self.parser.parseError("unexpected-end-tag", {"name": "p"})
            self.endTagP(impliedTagToken("p", "EndTag"))
        else:
            self.tree.generateImpliedEndTags("p")
            if self.tree.openElements[-1].name != "p":
                self.parser.parseError("unexpected-end-tag", {"name": "p"})
            node = self.tree.openElements.pop()
            while node.name != "p":
                node = self.tree.openElements.pop()

    def endTagBody(self, token):
        if not self.tree.elementInScope("body"):
            self.parser.parseError()
            return
        elif self.tree.openElements[-1].name != "body":
            for node in self.tree.openElements[2:]:
                if node.name not in frozenset(("dd", "dt", "li", "optgroup",
                                               "option", "p", "rp", "rt",
                                               "tbody", "td", "tfoot",
                                               "th", "thead", "tr", "body",
                                               "html")):
                    #Not sure this is the correct name for the parse error
                    self.parser.parseError(
                        "expected-one-end-tag-but-got-another",
                        {"expectedName": "body", "gotName": node.name})
                    break
        self.parser.phase = self.parser.phases["afterBody"]

    def endTagHtml(self, token):
        #We repeat the test for the body end tag token being ignored here
        if self.tree.elementInScope("body"):
            self.endTagBody(impliedTagToken("body"))
            self.parser.phase.processEndTag(token)

    def endTagBlock(self, token):
        #Put us back in the right whitespace handling mode
        if token["name"] == "pre":
            self.processSpaceCharacters = self.processSpaceCharactersNonPre
        inScope = self.tree.elementInScope(token["name"])
        if inScope:
            self.tree.generateImpliedEndTags()
        if self.tree.openElements[-1].name != token["name"]:
             self.parser.parseError("end-tag-too-early", {"name": token["name"]})
        if inScope:
            node = self.tree.openElements.pop()
            while node.name != token["name"]:
                node = self.tree.openElements.pop()

    def endTagForm(self, token):
        node = self.tree.formPointer
        self.tree.formPointer = None
        if node is None or not self.tree.elementInScope(node.name):
            self.parser.parseError("unexpected-end-tag",
                                   {"name":"form"})
        else:
            self.tree.generateImpliedEndTags()
            if self.tree.openElements[-1].name != node:
                self.parser.parseError("end-tag-too-early-ignored",
                                       {"name": "form"})
            self.tree.openElements.remove(node)

    def endTagListItem(self, token):
        if token["name"] == "li":
            variant = "list"
        else:
            variant = None
        if not self.tree.elementInScope(token["name"], variant=variant):
            self.parser.parseError("unexpected-end-tag", {"name": token["name"]})
        else:
            self.tree.generateImpliedEndTags(exclude = token["name"])
            if self.tree.openElements[-1].name != token["name"]:
                self.parser.parseError(
                    "end-tag-too-early",
                    {"name": token["name"]})
            node = self.tree.openElements.pop()
            while node.name != token["name"]:
                node = self.tree.openElements.pop()

    def endTagHeading(self, token):
        for item in headingElements:
            if self.tree.elementInScope(item):
                self.tree.generateImpliedEndTags()
                break
        if self.tree.openElements[-1].name != token["name"]:
            self.parser.parseError("end-tag-too-early", {"name": token["name"]})

        for item in headingElements:
            if self.tree.elementInScope(item):
                item = self.tree.openElements.pop()
                while item.name not in headingElements:
                    item = self.tree.openElements.pop()
                break

    def endTagFormatting(self, token):
        """The much-feared adoption agency algorithm"""
        # http://www.whatwg.org/specs/web-apps/current-work/#adoptionAgency
        # XXX Better parseError messages appreciated.
        name = token["name"]
        while True:
            # Step 1 paragraph 1
            formattingElement = self.tree.elementInActiveFormattingElements(
                token["name"])
            if not formattingElement or (formattingElement in 
                                        self.tree.openElements and
                                        not self.tree.elementInScope(
                    formattingElement.name)):
                self.parser.parseError("adoption-agency-1.1", {"name": token["name"]})
                return

            # Step 1 paragraph 2
            elif formattingElement not in self.tree.openElements:
                self.parser.parseError("adoption-agency-1.2", {"name": token["name"]})
                self.tree.activeFormattingElements.remove(formattingElement)
                return

            # Step 1 paragraph 3
            if formattingElement != self.tree.openElements[-1]:
                self.parser.parseError("adoption-agency-1.3", {"name": token["name"]})

            # Step 2
            # Start of the adoption agency algorithm proper
            afeIndex = self.tree.openElements.index(formattingElement)
            furthestBlock = None
            for element in self.tree.openElements[afeIndex:]:
                if (element.nameTuple in
                    specialElements | scopingElements):
                    furthestBlock = element
                    break

            # Step 3
            if furthestBlock is None:
                element = self.tree.openElements.pop()
                while element != formattingElement:
                    element = self.tree.openElements.pop()
                self.tree.activeFormattingElements.remove(element)
                return
            commonAncestor = self.tree.openElements[afeIndex-1]

            # Step 5
            #if furthestBlock.parent:
            #    furthestBlock.parent.removeChild(furthestBlock)

            # Step 5
            # The bookmark is supposed to help us identify where to reinsert
            # nodes in step 12. We have to ensure that we reinsert nodes after
            # the node before the active formatting element. Note the bookmark
            # can move in step 7.4
            bookmark = self.tree.activeFormattingElements.index(formattingElement)

            # Step 6
            lastNode = node = furthestBlock
            while True:
                # AT replace this with a function and recursion?
                # Node is element before node in open elements
                node = self.tree.openElements[
                    self.tree.openElements.index(node)-1]
                while node not in self.tree.activeFormattingElements:
                    tmpNode = node
                    node = self.tree.openElements[
                        self.tree.openElements.index(node)-1]
                    self.tree.openElements.remove(tmpNode)
                # Step 6.3
                if node == formattingElement:
                    break
                # Step 6.4
                if lastNode == furthestBlock:
                    bookmark = (self.tree.activeFormattingElements.index(node)
                                + 1)
                # Step 6.5
                #cite = node.parent
                #if node.hasContent():
                clone = node.cloneNode()
                # Replace node with clone
                self.tree.activeFormattingElements[
                    self.tree.activeFormattingElements.index(node)] = clone
                self.tree.openElements[
                    self.tree.openElements.index(node)] = clone
                node = clone
                
                # Step 6.6
                # Remove lastNode from its parents, if any
                if lastNode.parent:
                    lastNode.parent.removeChild(lastNode)
                node.appendChild(lastNode)
                # Step 7.7
                lastNode = node
                # End of inner loop 

            # Step 7
            # Foster parent lastNode if commonAncestor is a
            # table, tbody, tfoot, thead, or tr we need to foster parent the 
            # lastNode
            if lastNode.parent:
                lastNode.parent.removeChild(lastNode)
            commonAncestor.appendChild(lastNode)

            # Step 8
            clone = formattingElement.cloneNode()

            # Step 9
            furthestBlock.reparentChildren(clone)

            # Step 10
            furthestBlock.appendChild(clone)

            # Step 11
            self.tree.activeFormattingElements.remove(formattingElement)
            self.tree.activeFormattingElements.insert(bookmark, clone)

            # Step 12
            self.tree.openElements.remove(formattingElement)
            self.tree.openElements.insert(
              self.tree.openElements.index(furthestBlock) + 1, clone)

    def endTagAppletButtonMarqueeObject(self, token):
        if self.tree.elementInScope(token["name"]):
            self.tree.generateImpliedEndTags()
        if self.tree.openElements[-1].name != token["name"]:
            self.parser.parseError("end-tag-too-early", {"name": token["name"]})

        if self.tree.elementInScope(token["name"]):
            element = self.tree.openElements.pop()
            while element.name != token["name"]:
                element = self.tree.openElements.pop()
            self.tree.clearActiveFormattingElements()

    def endTagBr(self, token):
        self.parser.parseError("unexpected-end-tag-treated-as",
          {"originalName": "br", "newName": "br element"})
        self.tree.reconstructActiveFormattingElements()
        self.tree.insertElement(impliedTagToken("br", "StartTag"))
        self.tree.openElements.pop()

    def endTagOther(self, token):
        for node in self.tree.openElements[::-1]:
            if node.name == token["name"]:
                self.tree.generateImpliedEndTags()
                if self.tree.openElements[-1].name != token["name"]:
                    self.parser.parseError("unexpected-end-tag", {"name": token["name"]})
                while self.tree.openElements.pop() != node:
                    pass
                break
            else:
                if (node.nameTuple in
                    specialElements | scopingElements):
                    self.parser.parseError("unexpected-end-tag", {"name": token["name"]})
                    break

class TextPhase(Phase):
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)
        self.startTagHandler = utils.MethodDispatcher([])
        self.startTagHandler.default = self.startTagOther
        self.endTagHandler = utils.MethodDispatcher([
                ("script", self.endTagScript)])
        self.endTagHandler.default = self.endTagOther

    def processCharacters(self, token):
        self.tree.insertText(token["data"])
    
    def processEOF(self):
        self.parser.parseError("expected-named-closing-tag-but-got-eof", 
                               self.tree.openElements[-1].name)
        self.tree.openElements.pop()
        self.parser.phase = self.parser.originalPhase
        self.parser.phase.processEOF()

    def startTagOther(self, token):
        assert False, "Tried to process start tag %s in RCDATA/RAWTEXT mode"%name

    def endTagScript(self, token):
        node = self.tree.openElements.pop()
        assert node.name == "script"
        self.parser.phase = self.parser.originalPhase
        #The rest of this method is all stuff that only happens if
        #document.write works
    
    def endTagOther(self, token):
        node = self.tree.openElements.pop()
        self.parser.phase = self.parser.originalPhase

class InTablePhase(Phase):
    # http://www.whatwg.org/specs/web-apps/current-work/#in-table
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)
        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            ("caption", self.startTagCaption),
            ("colgroup", self.startTagColgroup),
            ("col", self.startTagCol),
            (("tbody", "tfoot", "thead"), self.startTagRowGroup),
            (("td", "th", "tr"), self.startTagImplyTbody),
            ("table", self.startTagTable),
            (("style", "script"), self.startTagStyleScript),
            ("input", self.startTagInput),
            ("form", self.startTagForm)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            ("table", self.endTagTable),
            (("body", "caption", "col", "colgroup", "html", "tbody", "td",
              "tfoot", "th", "thead", "tr"), self.endTagIgnore)
        ])
        self.endTagHandler.default = self.endTagOther

    # helper methods
    def clearStackToTableContext(self):
        # "clear the stack back to a table context"
        while self.tree.openElements[-1].name not in ("table", "html"):
            #self.parser.parseError("unexpected-implied-end-tag-in-table",
            #  {"name":  self.tree.openElements[-1].name})
            self.tree.openElements.pop()
        # When the current node is <html> it's an innerHTML case

    def getCurrentTable(self):
        i = -1
        while -i <= len(self.tree.openElements) and self.tree.openElements[i].name != "table":
             i -= 1
        if -i > len(self.tree.openElements):
            return self.tree.openElements[0]
        else:
            return self.tree.openElements[i]

    # processing methods
    def processEOF(self):
        if self.tree.openElements[-1].name != "html":
            self.parser.parseError("eof-in-table")
        else:
            assert self.parser.innerHTML
        #Stop parsing

    def processSpaceCharacters(self, token):
        originalPhase = self.parser.phase
        self.parser.phase = self.parser.phases["inTableText"]
        self.parser.phase.originalPhase = originalPhase
        self.parser.phase.characterTokens.append(token)

    def processCharacters(self, token):
        #If we get here there must be at least one non-whitespace character
        # Do the table magic!
        self.tree.insertFromTable = True
        self.parser.phases["inBody"].processCharacters(token)
        self.tree.insertFromTable = False

    def startTagCaption(self, token):
        self.clearStackToTableContext()
        self.tree.activeFormattingElements.append(Marker)
        self.tree.insertElement(token)
        self.parser.phase = self.parser.phases["inCaption"]

    def startTagColgroup(self, token):
        self.clearStackToTableContext()
        self.tree.insertElement(token)
        self.parser.phase = self.parser.phases["inColumnGroup"]

    def startTagCol(self, token):
        self.startTagColgroup(impliedTagToken("colgroup", "StartTag"))
        self.parser.phase.processStartTag(token)

    def startTagRowGroup(self, token):
        self.clearStackToTableContext()
        self.tree.insertElement(token)
        self.parser.phase = self.parser.phases["inTableBody"]

    def startTagImplyTbody(self, token):
        self.startTagRowGroup(impliedTagToken("tbody", "StartTag"))
        self.parser.phase.processStartTag(token)

    def startTagTable(self, token):
        self.parser.parseError("unexpected-start-tag-implies-end-tag",
          {"startName": "table", "endName": "table"})
        self.parser.phase.processEndTag(impliedTagToken("table"))
        if not self.parser.innerHTML:
            self.parser.phase.processStartTag(token)

    def startTagStyleScript(self, token):
        self.parser.phases["inHead"].processStartTag(token)

    def startTagInput(self, token):
        if ("type" in token["data"] and 
            token["data"]["type"].translate(asciiUpper2Lower) == "hidden"):
            self.parser.parseError("unexpected-hidden-input-in-table")
            self.tree.insertElement(token)
            # XXX associate with form
            self.tree.openElements.pop()
        else:
            self.startTagOther(token)

    def startTagForm(self, token):
        self.parser.parseError("unexpected-form-in-table")
        self.tree.insertElement(token)
        self.tree.openElements.pop()

    def startTagOther(self, token):
        self.parser.parseError("unexpected-start-tag-implies-table-voodoo", {"name": token["name"]})
        if "tainted" not in self.getCurrentTable()._flags:
            self.getCurrentTable()._flags.append("tainted")
        # Do the table magic!
        self.tree.insertFromTable = True
        self.parser.phases["inBody"].processStartTag(token)
        self.tree.insertFromTable = False

    def endTagTable(self, token):
        if self.tree.elementInScope("table", variant="table"):
            self.tree.generateImpliedEndTags()
            if self.tree.openElements[-1].name != "table":
                self.parser.parseError("end-tag-too-early-named",
                  {"gotName": "table",
                   "expectedName": self.tree.openElements[-1].name})
            while self.tree.openElements[-1].name != "table":
                self.tree.openElements.pop()
            self.tree.openElements.pop()
            self.parser.resetInsertionMode()
        else:
            # innerHTML case
            assert self.parser.innerHTML
            self.parser.parseError()

    def endTagIgnore(self, token):
        self.parser.parseError("unexpected-end-tag", {"name": token["name"]})

    def endTagOther(self, token):
        self.parser.parseError("unexpected-end-tag-implies-table-voodoo", {"name": token["name"]})
        if "tainted" not in self.getCurrentTable()._flags:
            self.getCurrentTable()._flags.append("tainted")
        # Do the table magic!
        self.tree.insertFromTable = True
        self.parser.phases["inBody"].processEndTag(token)
        self.tree.insertFromTable = False

class InTableTextPhase(Phase):
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)
        self.originalPhase = None
        self.characterTokens = []

    def flushCharacters(self):
        data = "".join([item["data"] for item in self.characterTokens])
        if any([item not in spaceCharacters for item in data]):
            token = {"type":tokenTypes["Characters"], "data":data}
            self.originalPhase.processCharacters(token)
        elif data:
            self.tree.insertText(data)
        self.characterTokens = []

    def processComment(self, token):
        self.flushCharacters()
        self.phase = self.originalPhase
        self.phase.processComment(token)

    def processEOF(self):
        self.flushCharacters()
        self.phase = self.originalPhase
        self.phase.processEOF()

    def processCharacters(self, token):
        self.characterTokens.append(token)

    def processSpaceCharacters(self, token):
        #pretty sure we should never reach here
        self.characterTokens.append(token)
#        assert False

    def processStartTag(self, token):        
        self.flushCharacters()
        self.phase = self.originalPhase
        self.phase.processStartTag(token)

    def processEndTag(self, token):
        self.flushCharacters()
        self.phase = self.originalPhase
        self.phase.processEndTag(token)
    

class InCaptionPhase(Phase):
    # http://www.whatwg.org/specs/web-apps/current-work/#in-caption
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            (("caption", "col", "colgroup", "tbody", "td", "tfoot", "th",
              "thead", "tr"), self.startTagTableElement)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            ("caption", self.endTagCaption),
            ("table", self.endTagTable),
            (("body", "col", "colgroup", "html", "tbody", "td", "tfoot", "th",
              "thead", "tr"), self.endTagIgnore)
        ])
        self.endTagHandler.default = self.endTagOther

    def ignoreEndTagCaption(self):
        return not self.tree.elementInScope("caption", variant="table")

    def processEOF(self):
        self.parser.phases["inBody"].processEOF()

    def processCharacters(self, token):
        self.parser.phases["inBody"].processCharacters(token)

    def startTagTableElement(self, token):
        self.parser.parseError()
        #XXX Have to duplicate logic here to find out if the tag is ignored
        ignoreEndTag = self.ignoreEndTagCaption()
        self.parser.phase.processEndTag(impliedTagToken("caption"))
        if not ignoreEndTag:
            self.parser.phase.processStartTag(token)

    def startTagOther(self, token):
        self.parser.phases["inBody"].processStartTag(token)

    def endTagCaption(self, token):
        if not self.ignoreEndTagCaption():
            # AT this code is quite similar to endTagTable in "InTable"
            self.tree.generateImpliedEndTags()
            if self.tree.openElements[-1].name != "caption":
                self.parser.parseError("expected-one-end-tag-but-got-another",
                  {"gotName": "caption",
                   "expectedName": self.tree.openElements[-1].name})
            while self.tree.openElements[-1].name != "caption":
                self.tree.openElements.pop()
            self.tree.openElements.pop()
            self.tree.clearActiveFormattingElements()
            self.parser.phase = self.parser.phases["inTable"]
        else:
            # innerHTML case
            assert self.parser.innerHTML
            self.parser.parseError()

    def endTagTable(self, token):
        self.parser.parseError()
        ignoreEndTag = self.ignoreEndTagCaption()
        self.parser.phase.processEndTag(impliedTagToken("caption"))
        if not ignoreEndTag:
            self.parser.phase.processEndTag(token)

    def endTagIgnore(self, token):
        self.parser.parseError("unexpected-end-tag", {"name": token["name"]})

    def endTagOther(self, token):
        self.parser.phases["inBody"].processEndTag(token)


class InColumnGroupPhase(Phase):
    # http://www.whatwg.org/specs/web-apps/current-work/#in-column

    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            ("col", self.startTagCol)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            ("colgroup", self.endTagColgroup),
            ("col", self.endTagCol)
        ])
        self.endTagHandler.default = self.endTagOther

    def ignoreEndTagColgroup(self):
        return self.tree.openElements[-1].name == "html"

    def processEOF(self):
        if self.tree.openElements[-1].name == "html":
            assert self.parser.innerHTML
            return
        else:
            ignoreEndTag = self.ignoreEndTagColgroup()
            self.endTagColgroup("colgroup")
            if not ignoreEndTag:
                self.parser.phase.processEOF()

    def processCharacters(self, token):
        ignoreEndTag = self.ignoreEndTagColgroup()
        self.endTagColgroup(impliedTagToken("colgroup"))
        if not ignoreEndTag:
            self.parser.phase.processCharacters(token)

    def startTagCol(self, token):
        self.tree.insertElement(token)
        self.tree.openElements.pop()

    def startTagOther(self, token):
        ignoreEndTag = self.ignoreEndTagColgroup()
        self.endTagColgroup("colgroup")
        if not ignoreEndTag:
            self.parser.phase.processStartTag(token)

    def endTagColgroup(self, token):
        if self.ignoreEndTagColgroup():
            # innerHTML case
            assert self.parser.innerHTML
            self.parser.parseError()
        else:
            self.tree.openElements.pop()
            self.parser.phase = self.parser.phases["inTable"]

    def endTagCol(self, token):
        self.parser.parseError("no-end-tag", {"name": "col"})

    def endTagOther(self, token):
        ignoreEndTag = self.ignoreEndTagColgroup()
        self.endTagColgroup("colgroup")
        if not ignoreEndTag:
            self.parser.phase.processEndTag(token)


class InTableBodyPhase(Phase):
    # http://www.whatwg.org/specs/web-apps/current-work/#in-table0
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)
        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            ("tr", self.startTagTr),
            (("td", "th"), self.startTagTableCell),
            (("caption", "col", "colgroup", "tbody", "tfoot", "thead"),
             self.startTagTableOther)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            (("tbody", "tfoot", "thead"), self.endTagTableRowGroup),
            ("table", self.endTagTable),
            (("body", "caption", "col", "colgroup", "html", "td", "th",
              "tr"), self.endTagIgnore)
        ])
        self.endTagHandler.default = self.endTagOther

    # helper methods
    def clearStackToTableBodyContext(self):
        while self.tree.openElements[-1].name not in ("tbody", "tfoot",
          "thead", "html"):
            #self.parser.parseError("unexpected-implied-end-tag-in-table",
            #  {"name": self.tree.openElements[-1].name})
            self.tree.openElements.pop()
        if self.tree.openElements[-1].name == "html":
            assert self.parser.innerHTML

    # the rest
    def processEOF(self):
        self.parser.phases["inTable"].processEOF()
    
    def processSpaceCharacters(self, token):
        self.parser.phases["inTable"].processSpaceCharacters(token)

    def processCharacters(self, token):
        self.parser.phases["inTable"].processCharacters(token)

    def startTagTr(self, token):
        self.clearStackToTableBodyContext()
        self.tree.insertElement(token)
        self.parser.phase = self.parser.phases["inRow"]

    def startTagTableCell(self, token):
        self.parser.parseError("unexpected-cell-in-table-body", 
                               {"name": token["name"]})
        self.startTagTr(impliedTagToken("tr", "StartTag"))
        self.parser.phase.processStartTag(token)

    def startTagTableOther(self, token):
        # XXX AT Any ideas on how to share this with endTagTable?
        if (self.tree.elementInScope("tbody", variant="table") or
            self.tree.elementInScope("thead", variant="table") or
            self.tree.elementInScope("tfoot", variant="table")):
            self.clearStackToTableBodyContext()
            self.endTagTableRowGroup(
                impliedTagToken(self.tree.openElements[-1].name))
            self.parser.phase.processStartTag(token)
        else:
            # innerHTML case
            self.parser.parseError()

    def startTagOther(self, token):
        self.parser.phases["inTable"].processStartTag(token)

    def endTagTableRowGroup(self, token):
        if self.tree.elementInScope(token["name"], variant="table"):
            self.clearStackToTableBodyContext()
            self.tree.openElements.pop()
            self.parser.phase = self.parser.phases["inTable"]
        else:
            self.parser.parseError("unexpected-end-tag-in-table-body",
              {"name": token["name"]})

    def endTagTable(self, token):
        if (self.tree.elementInScope("tbody", variant="table") or
            self.tree.elementInScope("thead", variant="table") or
            self.tree.elementInScope("tfoot", variant="table")):
            self.clearStackToTableBodyContext()
            self.endTagTableRowGroup(
                impliedTagToken(self.tree.openElements[-1].name))
            self.parser.phase.processEndTag(token)
        else:
            # innerHTML case
            self.parser.parseError()

    def endTagIgnore(self, token):
        self.parser.parseError("unexpected-end-tag-in-table-body",
          {"name": token["name"]})

    def endTagOther(self, token):
        self.parser.phases["inTable"].processEndTag(token)


class InRowPhase(Phase):
    # http://www.whatwg.org/specs/web-apps/current-work/#in-row
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)
        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            (("td", "th"), self.startTagTableCell),
            (("caption", "col", "colgroup", "tbody", "tfoot", "thead",
              "tr"), self.startTagTableOther)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            ("tr", self.endTagTr),
            ("table", self.endTagTable),
            (("tbody", "tfoot", "thead"), self.endTagTableRowGroup),
            (("body", "caption", "col", "colgroup", "html", "td", "th"),
              self.endTagIgnore)
        ])
        self.endTagHandler.default = self.endTagOther

    # helper methods (XXX unify this with other table helper methods)
    def clearStackToTableRowContext(self):
        while self.tree.openElements[-1].name not in ("tr", "html"):
            self.parser.parseError("unexpected-implied-end-tag-in-table-row",
              {"name": self.tree.openElements[-1].name})
            self.tree.openElements.pop()

    def ignoreEndTagTr(self):
        return not self.tree.elementInScope("tr", variant="table")

    # the rest
    def processEOF(self):
        self.parser.phases["inTable"].processEOF()
    
    def processSpaceCharacters(self, token):
        self.parser.phases["inTable"].processSpaceCharacters(token)        

    def processCharacters(self, token):
        self.parser.phases["inTable"].processCharacters(token)

    def startTagTableCell(self, token):
        self.clearStackToTableRowContext()
        self.tree.insertElement(token)
        self.parser.phase = self.parser.phases["inCell"]
        self.tree.activeFormattingElements.append(Marker)

    def startTagTableOther(self, token):
        ignoreEndTag = self.ignoreEndTagTr()
        self.endTagTr("tr")
        # XXX how are we sure it's always ignored in the innerHTML case?
        if not ignoreEndTag:
            self.parser.phase.processStartTag(token)

    def startTagOther(self, token):
        self.parser.phases["inTable"].processStartTag(token)

    def endTagTr(self, token):
        if not self.ignoreEndTagTr():
            self.clearStackToTableRowContext()
            self.tree.openElements.pop()
            self.parser.phase = self.parser.phases["inTableBody"]
        else:
            # innerHTML case
            assert self.parser.innerHTML
            self.parser.parseError()

    def endTagTable(self, token):
        ignoreEndTag = self.ignoreEndTagTr()
        self.endTagTr("tr")
        # Reprocess the current tag if the tr end tag was not ignored
        # XXX how are we sure it's always ignored in the innerHTML case?
        if not ignoreEndTag:
            self.parser.phase.processEndTag(token)

    def endTagTableRowGroup(self, token):
        if self.tree.elementInScope(token["name"], variant="table"):
            self.endTagTr("tr")
            self.parser.phase.processEndTag(token)
        else:
            # innerHTML case
            self.parser.parseError()

    def endTagIgnore(self, token):
        self.parser.parseError("unexpected-end-tag-in-table-row",
            {"name": token["name"]})

    def endTagOther(self, token):
        self.parser.phases["inTable"].processEndTag(token)

class InCellPhase(Phase):
    # http://www.whatwg.org/specs/web-apps/current-work/#in-cell
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)
        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            (("caption", "col", "colgroup", "tbody", "td", "tfoot", "th",
              "thead", "tr"), self.startTagTableOther)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            (("td", "th"), self.endTagTableCell),
            (("body", "caption", "col", "colgroup", "html"), self.endTagIgnore),
            (("table", "tbody", "tfoot", "thead", "tr"), self.endTagImply)
        ])
        self.endTagHandler.default = self.endTagOther

    # helper
    def closeCell(self):
        if self.tree.elementInScope("td", variant="table"):
            self.endTagTableCell(impliedTagToken("td"))
        elif self.tree.elementInScope("th", variant="table"):
            self.endTagTableCell(impliedTagToken("th"))

    # the rest
    def processEOF(self):
        self.parser.phases["inBody"].processEOF()
        
    def processCharacters(self, token):
        self.parser.phases["inBody"].processCharacters(token)

    def startTagTableOther(self, token):
        if (self.tree.elementInScope("td", variant="table") or
            self.tree.elementInScope("th", variant="table")):
            self.closeCell()
            self.parser.phase.processStartTag(token)
        else:
            # innerHTML case
            self.parser.parseError()

    def startTagOther(self, token):
        self.parser.phases["inBody"].processStartTag(token)
        # Optimize this for subsequent invocations. Can't do this initially
        # because self.phases doesn't really exist at that point.
        self.startTagHandler.default =\
          self.parser.phases["inBody"].processStartTag

    def endTagTableCell(self, token):
        if self.tree.elementInScope(token["name"], variant="table"):
            self.tree.generateImpliedEndTags(token["name"])
            if self.tree.openElements[-1].name != token["name"]:
                self.parser.parseError("unexpected-cell-end-tag",
                  {"name": token["name"]})
                while True:
                    node = self.tree.openElements.pop()
                    if node.name == token["name"]:
                        break
            else:
                self.tree.openElements.pop()
            self.tree.clearActiveFormattingElements()
            self.parser.phase = self.parser.phases["inRow"]
        else:
            self.parser.parseError("unexpected-end-tag", {"name": token["name"]})

    def endTagIgnore(self, token):
        self.parser.parseError("unexpected-end-tag", {"name": token["name"]})

    def endTagImply(self, token):
        if self.tree.elementInScope(token["name"], variant="table"):
            self.closeCell()
            self.parser.phase.processEndTag(token)
        else:
            # sometimes innerHTML case
            self.parser.parseError()

    def endTagOther(self, token):
        self.parser.phases["inBody"].processEndTag(token)
        # Optimize this for subsequent invocations. Can't do this initially
        # because self.phases doesn't really exist at that point.
        self.endTagHandler.default = self.parser.phases["inBody"].processEndTag


class InSelectPhase(Phase):
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            ("option", self.startTagOption),
            ("optgroup", self.startTagOptgroup),
            ("select", self.startTagSelect),
            (("input", "keygen", "textarea"), self.startTagInput)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            ("option", self.endTagOption),
            ("optgroup", self.endTagOptgroup),
            ("select", self.endTagSelect),
            (("caption", "table", "tbody", "tfoot", "thead", "tr", "td",
              "th"), self.endTagTableElements)
        ])
        self.endTagHandler.default = self.endTagOther

    # http://www.whatwg.org/specs/web-apps/current-work/#in-select
    def processEOF(self):
        if self.tree.openElements[-1].name != "html":
            self.parser.parseError("eof-in-select")
        else:
            assert self.parser.innerHTML

    def processCharacters(self, token):
        self.tree.insertText(token["data"])

    def startTagOption(self, token):
        # We need to imply </option> if <option> is the current node.
        if self.tree.openElements[-1].name == "option":
            self.tree.openElements.pop()
        self.tree.insertElement(token)

    def startTagOptgroup(self, token):
        if self.tree.openElements[-1].name == "option":
            self.tree.openElements.pop()
        if self.tree.openElements[-1].name == "optgroup":
            self.tree.openElements.pop()
        self.tree.insertElement(token)

    def startTagSelect(self, token):
        self.parser.parseError("unexpected-select-in-select")
        self.endTagSelect("select")

    def startTagInput(self, token):
        self.parser.parseError("unexpected-input-in-select")
        if self.tree.elementInScope("select", variant="table"):
            self.endTagSelect("select")
            self.parser.phase.processStartTag(token)

    def startTagOther(self, token):
        self.parser.parseError("unexpected-start-tag-in-select",
          {"name": token["name"]})

    def endTagOption(self, token):
        if self.tree.openElements[-1].name == "option":
            self.tree.openElements.pop()
        else:
            self.parser.parseError("unexpected-end-tag-in-select",
              {"name": "option"})

    def endTagOptgroup(self, token):
        # </optgroup> implicitly closes <option>
        if (self.tree.openElements[-1].name == "option" and
            self.tree.openElements[-2].name == "optgroup"):
            self.tree.openElements.pop()
        # It also closes </optgroup>
        if self.tree.openElements[-1].name == "optgroup":
            self.tree.openElements.pop()
        # But nothing else
        else:
            self.parser.parseError("unexpected-end-tag-in-select",
              {"name": "optgroup"})

    def endTagSelect(self, token):
        if self.tree.elementInScope("select", variant="table"):
            node = self.tree.openElements.pop()
            while node.name != "select":
                node = self.tree.openElements.pop()
            self.parser.resetInsertionMode()
        else:
            # innerHTML case
            self.parser.parseError()

    def endTagTableElements(self, token):
        self.parser.parseError("unexpected-end-tag-in-select",
          {"name": token["name"]})
        if self.tree.elementInScope(token["name"], variant="table"):
            self.endTagSelect("select")
            self.parser.phase.processEndTag(token)

    def endTagOther(self, token):
        self.parser.parseError("unexpected-end-tag-in-select",
          {"name": token["name"]})


class InSelectInTablePhase(Phase):
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
            (("caption", "table", "tbody", "tfoot", "thead", "tr", "td", "th"),
             self.startTagTable)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            (("caption", "table", "tbody", "tfoot", "thead", "tr", "td", "th"),
             self.endTagTable)
        ])
        self.endTagHandler.default = self.endTagOther

    def processEOF(self):
        self.parser.phases["inSelect"].processEOF()

    def processCharacters(self, token):
        self.parser.phases["inSelect"].processCharacters(token)
    
    def startTagTable(self, token):
        self.parser.parseError("unexpected-table-element-start-tag-in-select-in-table", {"name": token["name"]})
        self.endTagOther(impliedTagToken("select"))
        self.parser.phase.processStartTag(token)

    def startTagOther(self, token):
        self.parser.phases["inSelect"].processStartTag(token)

    def endTagTable(self, token):
        self.parser.parseError("unexpected-table-element-end-tag-in-select-in-table", {"name": token["name"]})
        if self.tree.elementInScope(token["name"], variant="table"):
            self.endTagOther(impliedTagToken("select"))
            self.parser.phase.processEndTag(token)

    def endTagOther(self, token):
        self.parser.phases["inSelect"].processEndTag(token)


class InForeignContentPhase(Phase):
    breakoutElements = frozenset(["b", "big", "blockquote", "body", "br", 
                                  "center", "code", "dd", "div", "dl", "dt",
                                  "em", "embed", "font", "h1", "h2", "h3", 
                                  "h4", "h5", "h6", "head", "hr", "i", "img",
                                  "li", "listing", "menu", "meta", "nobr", 
                                  "ol", "p", "pre", "ruby", "s",  "small", 
                                  "span", "strong", "strike",  "sub", "sup", 
                                  "table", "tt", "u", "ul", "var"])
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

    def nonHTMLElementInScope(self):
        for element in self.tree.openElements[::-1]:
            if element.namespace == self.tree.defaultNamespace:
                return self.tree.elementInScope(element)
        assert False
        for item in self.tree.openElements[::-1]:
            if item.namespace == self.tree.defaultNamespace:
                return True
            elif item.nameTuple in scopingElements:
                return False
        return False

    def adjustSVGTagNames(self, token):
        replacements = {"altglyph":"altGlyph",
                        "altglyphdef":"altGlyphDef",
                        "altglyphitem":"altGlyphItem",
                        "animatecolor":"animateColor",
                        "animatemotion":"animateMotion",
                        "animatetransform":"animateTransform",
                        "clippath":"clipPath",
                        "feblend":"feBlend",
                        "fecolormatrix":"feColorMatrix",
                        "fecomponenttransfer":"feComponentTransfer",
                        "fecomposite":"feComposite",
                        "feconvolvematrix":"feConvolveMatrix",
                        "fediffuselighting":"feDiffuseLighting",
                        "fedisplacementmap":"feDisplacementMap",
                        "fedistantlight":"feDistantLight",
                        "feflood":"feFlood",
                        "fefunca":"feFuncA",
                        "fefuncb":"feFuncB",
                        "fefuncg":"feFuncG",
                        "fefuncr":"feFuncR",
                        "fegaussianblur":"feGaussianBlur",
                        "feimage":"feImage",
                        "femerge":"feMerge",
                        "femergenode":"feMergeNode",
                        "femorphology":"feMorphology",
                        "feoffset":"feOffset",
                        "fepointlight":"fePointLight",
                        "fespecularlighting":"feSpecularLighting",
                        "fespotlight":"feSpotLight",
                        "fetile":"feTile",
                        "feturbulence":"feTurbulence",
                        "foreignobject":"foreignObject",
                        "glyphref":"glyphRef",
                        "lineargradient":"linearGradient",
                        "radialgradient":"radialGradient",
                        "textpath":"textPath"}

        if token["name"] in replacements:
            token["name"] = replacements[token["name"]]

    def processCharacters(self, token):
        self.parser.framesetOK = False
        Phase.processCharacters(self, token)

    def processEOF(self):
        pass

    def processStartTag(self, token):
        currentNode = self.tree.openElements[-1]
        if (currentNode.namespace == self.tree.defaultNamespace or
            (currentNode.namespace == namespaces["mathml"] and 
             token["name"] not in frozenset(["mglyph", "malignmark"]) and
             currentNode.name in frozenset(["mi", "mo", "mn", 
                                            "ms", "mtext"])) or
            (currentNode.namespace == namespaces["mathml"] and
             currentNode.name == "annotation-xml" and
             token["name"] == "svg") or
            (currentNode.namespace == namespaces["svg"] and 
             currentNode.name in frozenset(["foreignObject", 
                                            "desc", "title"])
             )):
            assert self.parser.secondaryPhase != self
            self.parser.secondaryPhase.processStartTag(token)
            if self.parser.phase == self and self.nonHTMLElementInScope():
                self.parser.phase = self.parser.secondaryPhase
        elif token["name"] in self.breakoutElements:
            self.parser.parseError("unexpected-html-element-in-foreign-content",
                                   token["name"])
            while (self.tree.openElements[-1].namespace !=
                   self.tree.defaultNamespace):
                self.tree.openElements.pop()
            self.parser.phase = self.parser.secondaryPhase
            self.parser.phase.processStartTag(token)
        else:
            if currentNode.namespace == namespaces["mathml"]:
                self.parser.adjustMathMLAttributes(token)
            elif currentNode.namespace == namespaces["svg"]:
                self.adjustSVGTagNames(token)
                self.parser.adjustSVGAttributes(token)
            self.parser.adjustForeignAttributes(token)
            token["namespace"] = currentNode.namespace
            self.tree.insertElement(token)
            if token["selfClosing"]:
                self.tree.openElements.pop()
                token["selfClosingAcknowledged"] = True

    def processEndTag(self, token):
        self.adjustSVGTagNames(token)
        self.parser.secondaryPhase.processEndTag(token)
        if self.parser.phase == self and self.nonHTMLElementInScope():
            self.parser.phase = self.parser.secondaryPhase

class AfterBodyPhase(Phase):
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
                ("html", self.startTagHtml)
                ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([("html", self.endTagHtml)])
        self.endTagHandler.default = self.endTagOther

    def processEOF(self):
        #Stop parsing
        pass
    
    def processComment(self, token):
        # This is needed because data is to be appended to the <html> element
        # here and not to whatever is currently open.
        self.tree.insertComment(token, self.tree.openElements[0])

    def processCharacters(self, token):
        self.parser.parseError("unexpected-char-after-body")
        self.parser.phase = self.parser.phases["inBody"]
        self.parser.phase.processCharacters(token)

    def startTagHtml(self, token):
        self.parser.phases["inBody"].processStartTag(token)

    def startTagOther(self, token):
        self.parser.parseError("unexpected-start-tag-after-body",
          {"name": token["name"]})
        self.parser.phase = self.parser.phases["inBody"]
        self.parser.phase.processStartTag(token)

    def endTagHtml(self,name):
        if self.parser.innerHTML:
            self.parser.parseError("unexpected-end-tag-after-body-innerhtml")
        else:
            self.parser.phase = self.parser.phases["afterAfterBody"]

    def endTagOther(self, token):
        self.parser.parseError("unexpected-end-tag-after-body",
          {"name": token["name"]})
        self.parser.phase = self.parser.phases["inBody"]
        self.parser.phase.processEndTag(token)

class InFramesetPhase(Phase):
    # http://www.whatwg.org/specs/web-apps/current-work/#in-frameset
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            ("frameset", self.startTagFrameset),
            ("frame", self.startTagFrame),
            ("noframes", self.startTagNoframes)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            ("frameset", self.endTagFrameset),
            ("noframes", self.endTagNoframes)
        ])
        self.endTagHandler.default = self.endTagOther

    def processEOF(self):
        if self.tree.openElements[-1].name != "html":
            self.parser.parseError("eof-in-frameset")
        else:
            assert self.parser.innerHTML

    def processCharacters(self, token):
        self.parser.parseError("unexpected-char-in-frameset")

    def startTagFrameset(self, token):
        self.tree.insertElement(token)

    def startTagFrame(self, token):
        self.tree.insertElement(token)
        self.tree.openElements.pop()

    def startTagNoframes(self, token):
        self.parser.phases["inBody"].processStartTag(token)

    def startTagOther(self, token):
        self.parser.parseError("unexpected-start-tag-in-frameset",
          {"name": token["name"]})

    def endTagFrameset(self, token):
        if self.tree.openElements[-1].name == "html":
            # innerHTML case
            self.parser.parseError("unexpected-frameset-in-frameset-innerhtml")
        else:
            self.tree.openElements.pop()
        if (not self.parser.innerHTML and
            self.tree.openElements[-1].name != "frameset"):
            # If we're not in innerHTML mode and the the current node is not a
            # "frameset" element (anymore) then switch.
            self.parser.phase = self.parser.phases["afterFrameset"]

    def endTagNoframes(self, token):
        self.parser.phases["inBody"].processEndTag(token)

    def endTagOther(self, token):
        self.parser.parseError("unexpected-end-tag-in-frameset",
          {"name": token["name"]})


class AfterFramesetPhase(Phase):
    # http://www.whatwg.org/specs/web-apps/current-work/#after3
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            ("noframes", self.startTagNoframes)
        ])
        self.startTagHandler.default = self.startTagOther

        self.endTagHandler = utils.MethodDispatcher([
            ("html", self.endTagHtml)
        ])
        self.endTagHandler.default = self.endTagOther

    def processEOF(self):
        #Stop parsing
        pass

    def processCharacters(self, token):
        self.parser.parseError("unexpected-char-after-frameset")

    def startTagNoframes(self, token):
        self.parser.phases["inHead"].processStartTag(token)

    def startTagOther(self, token):
        self.parser.parseError("unexpected-start-tag-after-frameset",
          {"name": token["name"]})

    def endTagHtml(self, token):
        self.parser.phase = self.parser.phases["afterAfterFrameset"]

    def endTagOther(self, token):
        self.parser.parseError("unexpected-end-tag-after-frameset",
          {"name": token["name"]})


class AfterAfterBodyPhase(Phase):
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml)
        ])
        self.startTagHandler.default = self.startTagOther

    def processEOF(self):
        pass

    def processComment(self, token):
        self.tree.insertComment(token, self.tree.document)

    def processSpaceCharacters(self, token):
        self.parser.phases["inBody"].processSpaceCharacters(token)

    def processCharacters(self, token):
        self.parser.parseError("expected-eof-but-got-char")
        self.parser.phase = self.parser.phases["inBody"]
        self.parser.phase.processCharacters(token)

    def startTagHtml(self, token):
        self.parser.phases["inBody"].processStartTag(token)

    def startTagOther(self, token):
        self.parser.parseError("expected-eof-but-got-start-tag",
          {"name": token["name"]})
        self.parser.phase = self.parser.phases["inBody"]
        self.parser.phase.processStartTag(token)

    def processEndTag(self, token):
        self.parser.parseError("expected-eof-but-got-end-tag",
          {"name": token["name"]})
        self.parser.phase = self.parser.phases["inBody"]
        self.parser.phase.processEndTag(token)

class AfterAfterFramesetPhase(Phase):
    def __init__(self, parser, tree):
        Phase.__init__(self, parser, tree)

        self.startTagHandler = utils.MethodDispatcher([
            ("html", self.startTagHtml),
            ("noframes", self.startTagNoFrames)
        ])
        self.startTagHandler.default = self.startTagOther

    def processEOF(self):
        pass

    def processComment(self, token):
        self.tree.insertComment(token, self.tree.document)

    def processSpaceCharacters(self, token):
        self.parser.phases["inBody"].processSpaceCharacters(token)

    def processCharacters(self, token):
        self.parser.parseError("expected-eof-but-got-char")
        self.parser.phase = self.parser.phases["inBody"]
        self.parser.phase.processCharacters(token)

    def startTagHtml(self, token):
        self.parser.phases["inBody"].processStartTag(token)

    def startTagNoFrames(self, token):
        self.parser.phases["inHead"].processStartTag(token)

    def startTagOther(self, token):
        self.parser.parseError("expected-eof-but-got-start-tag",
          {"name": token["name"]})
        self.parser.phase = self.parser.phases["inBody"]
        self.parser.phase.processStartTag(token)

    def processEndTag(self, token):
        self.parser.parseError("expected-eof-but-got-end-tag",
          {"name": token["name"]})
        self.parser.phase = self.parser.phases["inBody"]
        self.parser.phase.processEndTag(token)

def impliedTagToken(name, type="EndTag", attributes = None, 
                    selfClosing = False):
    if attributes is None:
        attributes = {}
    return {"type":tokenTypes[type], "name":name, "data":attributes,
            "selfClosing":selfClosing}

class ParseError(Exception):
    """Error in parsed document"""
    pass

########NEW FILE########
__FILENAME__ = ihatexml
import re

baseChar = """[#x0041-#x005A] | [#x0061-#x007A] | [#x00C0-#x00D6] | [#x00D8-#x00F6] | [#x00F8-#x00FF] | [#x0100-#x0131] | [#x0134-#x013E] | [#x0141-#x0148] | [#x014A-#x017E] | [#x0180-#x01C3] | [#x01CD-#x01F0] | [#x01F4-#x01F5] | [#x01FA-#x0217] | [#x0250-#x02A8] | [#x02BB-#x02C1] | #x0386 | [#x0388-#x038A] | #x038C | [#x038E-#x03A1] | [#x03A3-#x03CE] | [#x03D0-#x03D6] | #x03DA | #x03DC | #x03DE | #x03E0 | [#x03E2-#x03F3] | [#x0401-#x040C] | [#x040E-#x044F] | [#x0451-#x045C] | [#x045E-#x0481] | [#x0490-#x04C4] | [#x04C7-#x04C8] | [#x04CB-#x04CC] | [#x04D0-#x04EB] | [#x04EE-#x04F5] | [#x04F8-#x04F9] | [#x0531-#x0556] | #x0559 | [#x0561-#x0586] | [#x05D0-#x05EA] | [#x05F0-#x05F2] | [#x0621-#x063A] | [#x0641-#x064A] | [#x0671-#x06B7] | [#x06BA-#x06BE] | [#x06C0-#x06CE] | [#x06D0-#x06D3] | #x06D5 | [#x06E5-#x06E6] | [#x0905-#x0939] | #x093D | [#x0958-#x0961] | [#x0985-#x098C] | [#x098F-#x0990] | [#x0993-#x09A8] | [#x09AA-#x09B0] | #x09B2 | [#x09B6-#x09B9] | [#x09DC-#x09DD] | [#x09DF-#x09E1] | [#x09F0-#x09F1] | [#x0A05-#x0A0A] | [#x0A0F-#x0A10] | [#x0A13-#x0A28] | [#x0A2A-#x0A30] | [#x0A32-#x0A33] | [#x0A35-#x0A36] | [#x0A38-#x0A39] | [#x0A59-#x0A5C] | #x0A5E | [#x0A72-#x0A74] | [#x0A85-#x0A8B] | #x0A8D | [#x0A8F-#x0A91] | [#x0A93-#x0AA8] | [#x0AAA-#x0AB0] | [#x0AB2-#x0AB3] | [#x0AB5-#x0AB9] | #x0ABD | #x0AE0 | [#x0B05-#x0B0C] | [#x0B0F-#x0B10] | [#x0B13-#x0B28] | [#x0B2A-#x0B30] | [#x0B32-#x0B33] | [#x0B36-#x0B39] | #x0B3D | [#x0B5C-#x0B5D] | [#x0B5F-#x0B61] | [#x0B85-#x0B8A] | [#x0B8E-#x0B90] | [#x0B92-#x0B95] | [#x0B99-#x0B9A] | #x0B9C | [#x0B9E-#x0B9F] | [#x0BA3-#x0BA4] | [#x0BA8-#x0BAA] | [#x0BAE-#x0BB5] | [#x0BB7-#x0BB9] | [#x0C05-#x0C0C] | [#x0C0E-#x0C10] | [#x0C12-#x0C28] | [#x0C2A-#x0C33] | [#x0C35-#x0C39] | [#x0C60-#x0C61] | [#x0C85-#x0C8C] | [#x0C8E-#x0C90] | [#x0C92-#x0CA8] | [#x0CAA-#x0CB3] | [#x0CB5-#x0CB9] | #x0CDE | [#x0CE0-#x0CE1] | [#x0D05-#x0D0C] | [#x0D0E-#x0D10] | [#x0D12-#x0D28] | [#x0D2A-#x0D39] | [#x0D60-#x0D61] | [#x0E01-#x0E2E] | #x0E30 | [#x0E32-#x0E33] | [#x0E40-#x0E45] | [#x0E81-#x0E82] | #x0E84 | [#x0E87-#x0E88] | #x0E8A | #x0E8D | [#x0E94-#x0E97] | [#x0E99-#x0E9F] | [#x0EA1-#x0EA3] | #x0EA5 | #x0EA7 | [#x0EAA-#x0EAB] | [#x0EAD-#x0EAE] | #x0EB0 | [#x0EB2-#x0EB3] | #x0EBD | [#x0EC0-#x0EC4] | [#x0F40-#x0F47] | [#x0F49-#x0F69] | [#x10A0-#x10C5] | [#x10D0-#x10F6] | #x1100 | [#x1102-#x1103] | [#x1105-#x1107] | #x1109 | [#x110B-#x110C] | [#x110E-#x1112] | #x113C | #x113E | #x1140 | #x114C | #x114E | #x1150 | [#x1154-#x1155] | #x1159 | [#x115F-#x1161] | #x1163 | #x1165 | #x1167 | #x1169 | [#x116D-#x116E] | [#x1172-#x1173] | #x1175 | #x119E | #x11A8 | #x11AB | [#x11AE-#x11AF] | [#x11B7-#x11B8] | #x11BA | [#x11BC-#x11C2] | #x11EB | #x11F0 | #x11F9 | [#x1E00-#x1E9B] | [#x1EA0-#x1EF9] | [#x1F00-#x1F15] | [#x1F18-#x1F1D] | [#x1F20-#x1F45] | [#x1F48-#x1F4D] | [#x1F50-#x1F57] | #x1F59 | #x1F5B | #x1F5D | [#x1F5F-#x1F7D] | [#x1F80-#x1FB4] | [#x1FB6-#x1FBC] | #x1FBE | [#x1FC2-#x1FC4] | [#x1FC6-#x1FCC] | [#x1FD0-#x1FD3] | [#x1FD6-#x1FDB] | [#x1FE0-#x1FEC] | [#x1FF2-#x1FF4] | [#x1FF6-#x1FFC] | #x2126 | [#x212A-#x212B] | #x212E | [#x2180-#x2182] | [#x3041-#x3094] | [#x30A1-#x30FA] | [#x3105-#x312C] | [#xAC00-#xD7A3]"""

ideographic = """[#x4E00-#x9FA5] | #x3007 | [#x3021-#x3029]"""

combiningCharacter = """[#x0300-#x0345] | [#x0360-#x0361] | [#x0483-#x0486] | [#x0591-#x05A1] | [#x05A3-#x05B9] | [#x05BB-#x05BD] | #x05BF | [#x05C1-#x05C2] | #x05C4 | [#x064B-#x0652] | #x0670 | [#x06D6-#x06DC] | [#x06DD-#x06DF] | [#x06E0-#x06E4] | [#x06E7-#x06E8] | [#x06EA-#x06ED] | [#x0901-#x0903] | #x093C | [#x093E-#x094C] | #x094D | [#x0951-#x0954] | [#x0962-#x0963] | [#x0981-#x0983] | #x09BC | #x09BE | #x09BF | [#x09C0-#x09C4] | [#x09C7-#x09C8] | [#x09CB-#x09CD] | #x09D7 | [#x09E2-#x09E3] | #x0A02 | #x0A3C | #x0A3E | #x0A3F | [#x0A40-#x0A42] | [#x0A47-#x0A48] | [#x0A4B-#x0A4D] | [#x0A70-#x0A71] | [#x0A81-#x0A83] | #x0ABC | [#x0ABE-#x0AC5] | [#x0AC7-#x0AC9] | [#x0ACB-#x0ACD] | [#x0B01-#x0B03] | #x0B3C | [#x0B3E-#x0B43] | [#x0B47-#x0B48] | [#x0B4B-#x0B4D] | [#x0B56-#x0B57] | [#x0B82-#x0B83] | [#x0BBE-#x0BC2] | [#x0BC6-#x0BC8] | [#x0BCA-#x0BCD] | #x0BD7 | [#x0C01-#x0C03] | [#x0C3E-#x0C44] | [#x0C46-#x0C48] | [#x0C4A-#x0C4D] | [#x0C55-#x0C56] | [#x0C82-#x0C83] | [#x0CBE-#x0CC4] | [#x0CC6-#x0CC8] | [#x0CCA-#x0CCD] | [#x0CD5-#x0CD6] | [#x0D02-#x0D03] | [#x0D3E-#x0D43] | [#x0D46-#x0D48] | [#x0D4A-#x0D4D] | #x0D57 | #x0E31 | [#x0E34-#x0E3A] | [#x0E47-#x0E4E] | #x0EB1 | [#x0EB4-#x0EB9] | [#x0EBB-#x0EBC] | [#x0EC8-#x0ECD] | [#x0F18-#x0F19] | #x0F35 | #x0F37 | #x0F39 | #x0F3E | #x0F3F | [#x0F71-#x0F84] | [#x0F86-#x0F8B] | [#x0F90-#x0F95] | #x0F97 | [#x0F99-#x0FAD] | [#x0FB1-#x0FB7] | #x0FB9 | [#x20D0-#x20DC] | #x20E1 | [#x302A-#x302F] | #x3099 | #x309A"""

digit = """[#x0030-#x0039] | [#x0660-#x0669] | [#x06F0-#x06F9] | [#x0966-#x096F] | [#x09E6-#x09EF] | [#x0A66-#x0A6F] | [#x0AE6-#x0AEF] | [#x0B66-#x0B6F] | [#x0BE7-#x0BEF] | [#x0C66-#x0C6F] | [#x0CE6-#x0CEF] | [#x0D66-#x0D6F] | [#x0E50-#x0E59] | [#x0ED0-#x0ED9] | [#x0F20-#x0F29]"""

extender = """#x00B7 | #x02D0 | #x02D1 | #x0387 | #x0640 | #x0E46 | #x0EC6 | #x3005 | [#x3031-#x3035] | [#x309D-#x309E] | [#x30FC-#x30FE]"""

letter = " | ".join([baseChar, ideographic])

#Without the 
name = " | ".join([letter, digit, ".", "-", "_", combiningCharacter, 
                       extender])
nameFirst = " | ".join([letter, "_"])

reChar = re.compile(r"#x([\d|A-F]{4,4})")
reCharRange = re.compile(r"\[#x([\d|A-F]{4,4})-#x([\d|A-F]{4,4})\]")

def charStringToList(chars):
    charRanges = [item.strip() for item in chars.split(" | ")]
    rv = []
    for item in charRanges:
        foundMatch = False
        for regexp in (reChar, reCharRange):
            match = regexp.match(item)
            if match is not None:
                rv.append([hexToInt(item) for item in match.groups()])
                if len(rv[-1]) == 1:
                    rv[-1] = rv[-1]*2
                foundMatch = True
                break
        if not foundMatch:
            assert len(item) == 1
            
            rv.append([ord(item)] * 2)
    rv = normaliseCharList(rv)
    return rv

def normaliseCharList(charList):
    charList = sorted(charList)
    for item in charList:
        assert item[1] >= item[0]
    rv = []
    i = 0
    while i < len(charList):
        j = 1
        rv.append(charList[i])
        while i + j < len(charList) and charList[i+j][0] <= rv[-1][1] + 1:
            rv[-1][1] = charList[i+j][1]
            j += 1
        i += j
    return rv

#We don't really support characters above the BMP :(
max_unicode = int("FFFF", 16)
    
def missingRanges(charList):
    rv = []
    if charList[0] != 0:
        rv.append([0, charList[0][0] - 1])
    for i, item in enumerate(charList[:-1]):
        rv.append([item[1]+1, charList[i+1][0] - 1])
    if charList[-1][1] != max_unicode:
        rv.append([charList[-1][1] + 1, max_unicode])
    return rv

def listToRegexpStr(charList):
    rv = []
    for item in charList:
        if item[0] == item[1]:
           rv.append(escapeRegexp(unichr(item[0])))
        else:
            rv.append(escapeRegexp(unichr(item[0])) + "-" +
                      escapeRegexp(unichr(item[1])))
    return "[%s]"%"".join(rv)

def hexToInt(hex_str):
    return int(hex_str, 16)

def escapeRegexp(string):
    specialCharacters = (".", "^", "$", "*", "+", "?", "{", "}",
                          "[", "]", "|", "(", ")", "-")
    for char in specialCharacters:
        string = string.replace(char, "\\" + char)
        if char in string:
            print string

    return string

#output from the above
nonXmlNameBMPRegexp = re.compile(u'[\x00-,/:-@\\[-\\^`\\{-\xb6\xb8-\xbf\xd7\xf7\u0132-\u0133\u013f-\u0140\u0149\u017f\u01c4-\u01cc\u01f1-\u01f3\u01f6-\u01f9\u0218-\u024f\u02a9-\u02ba\u02c2-\u02cf\u02d2-\u02ff\u0346-\u035f\u0362-\u0385\u038b\u038d\u03a2\u03cf\u03d7-\u03d9\u03db\u03dd\u03df\u03e1\u03f4-\u0400\u040d\u0450\u045d\u0482\u0487-\u048f\u04c5-\u04c6\u04c9-\u04ca\u04cd-\u04cf\u04ec-\u04ed\u04f6-\u04f7\u04fa-\u0530\u0557-\u0558\u055a-\u0560\u0587-\u0590\u05a2\u05ba\u05be\u05c0\u05c3\u05c5-\u05cf\u05eb-\u05ef\u05f3-\u0620\u063b-\u063f\u0653-\u065f\u066a-\u066f\u06b8-\u06b9\u06bf\u06cf\u06d4\u06e9\u06ee-\u06ef\u06fa-\u0900\u0904\u093a-\u093b\u094e-\u0950\u0955-\u0957\u0964-\u0965\u0970-\u0980\u0984\u098d-\u098e\u0991-\u0992\u09a9\u09b1\u09b3-\u09b5\u09ba-\u09bb\u09bd\u09c5-\u09c6\u09c9-\u09ca\u09ce-\u09d6\u09d8-\u09db\u09de\u09e4-\u09e5\u09f2-\u0a01\u0a03-\u0a04\u0a0b-\u0a0e\u0a11-\u0a12\u0a29\u0a31\u0a34\u0a37\u0a3a-\u0a3b\u0a3d\u0a43-\u0a46\u0a49-\u0a4a\u0a4e-\u0a58\u0a5d\u0a5f-\u0a65\u0a75-\u0a80\u0a84\u0a8c\u0a8e\u0a92\u0aa9\u0ab1\u0ab4\u0aba-\u0abb\u0ac6\u0aca\u0ace-\u0adf\u0ae1-\u0ae5\u0af0-\u0b00\u0b04\u0b0d-\u0b0e\u0b11-\u0b12\u0b29\u0b31\u0b34-\u0b35\u0b3a-\u0b3b\u0b44-\u0b46\u0b49-\u0b4a\u0b4e-\u0b55\u0b58-\u0b5b\u0b5e\u0b62-\u0b65\u0b70-\u0b81\u0b84\u0b8b-\u0b8d\u0b91\u0b96-\u0b98\u0b9b\u0b9d\u0ba0-\u0ba2\u0ba5-\u0ba7\u0bab-\u0bad\u0bb6\u0bba-\u0bbd\u0bc3-\u0bc5\u0bc9\u0bce-\u0bd6\u0bd8-\u0be6\u0bf0-\u0c00\u0c04\u0c0d\u0c11\u0c29\u0c34\u0c3a-\u0c3d\u0c45\u0c49\u0c4e-\u0c54\u0c57-\u0c5f\u0c62-\u0c65\u0c70-\u0c81\u0c84\u0c8d\u0c91\u0ca9\u0cb4\u0cba-\u0cbd\u0cc5\u0cc9\u0cce-\u0cd4\u0cd7-\u0cdd\u0cdf\u0ce2-\u0ce5\u0cf0-\u0d01\u0d04\u0d0d\u0d11\u0d29\u0d3a-\u0d3d\u0d44-\u0d45\u0d49\u0d4e-\u0d56\u0d58-\u0d5f\u0d62-\u0d65\u0d70-\u0e00\u0e2f\u0e3b-\u0e3f\u0e4f\u0e5a-\u0e80\u0e83\u0e85-\u0e86\u0e89\u0e8b-\u0e8c\u0e8e-\u0e93\u0e98\u0ea0\u0ea4\u0ea6\u0ea8-\u0ea9\u0eac\u0eaf\u0eba\u0ebe-\u0ebf\u0ec5\u0ec7\u0ece-\u0ecf\u0eda-\u0f17\u0f1a-\u0f1f\u0f2a-\u0f34\u0f36\u0f38\u0f3a-\u0f3d\u0f48\u0f6a-\u0f70\u0f85\u0f8c-\u0f8f\u0f96\u0f98\u0fae-\u0fb0\u0fb8\u0fba-\u109f\u10c6-\u10cf\u10f7-\u10ff\u1101\u1104\u1108\u110a\u110d\u1113-\u113b\u113d\u113f\u1141-\u114b\u114d\u114f\u1151-\u1153\u1156-\u1158\u115a-\u115e\u1162\u1164\u1166\u1168\u116a-\u116c\u116f-\u1171\u1174\u1176-\u119d\u119f-\u11a7\u11a9-\u11aa\u11ac-\u11ad\u11b0-\u11b6\u11b9\u11bb\u11c3-\u11ea\u11ec-\u11ef\u11f1-\u11f8\u11fa-\u1dff\u1e9c-\u1e9f\u1efa-\u1eff\u1f16-\u1f17\u1f1e-\u1f1f\u1f46-\u1f47\u1f4e-\u1f4f\u1f58\u1f5a\u1f5c\u1f5e\u1f7e-\u1f7f\u1fb5\u1fbd\u1fbf-\u1fc1\u1fc5\u1fcd-\u1fcf\u1fd4-\u1fd5\u1fdc-\u1fdf\u1fed-\u1ff1\u1ff5\u1ffd-\u20cf\u20dd-\u20e0\u20e2-\u2125\u2127-\u2129\u212c-\u212d\u212f-\u217f\u2183-\u3004\u3006\u3008-\u3020\u3030\u3036-\u3040\u3095-\u3098\u309b-\u309c\u309f-\u30a0\u30fb\u30ff-\u3104\u312d-\u4dff\u9fa6-\uabff\ud7a4-\uffff]')

nonXmlNameFirstBMPRegexp = re.compile(u'[\x00-@\\[-\\^`\\{-\xbf\xd7\xf7\u0132-\u0133\u013f-\u0140\u0149\u017f\u01c4-\u01cc\u01f1-\u01f3\u01f6-\u01f9\u0218-\u024f\u02a9-\u02ba\u02c2-\u0385\u0387\u038b\u038d\u03a2\u03cf\u03d7-\u03d9\u03db\u03dd\u03df\u03e1\u03f4-\u0400\u040d\u0450\u045d\u0482-\u048f\u04c5-\u04c6\u04c9-\u04ca\u04cd-\u04cf\u04ec-\u04ed\u04f6-\u04f7\u04fa-\u0530\u0557-\u0558\u055a-\u0560\u0587-\u05cf\u05eb-\u05ef\u05f3-\u0620\u063b-\u0640\u064b-\u0670\u06b8-\u06b9\u06bf\u06cf\u06d4\u06d6-\u06e4\u06e7-\u0904\u093a-\u093c\u093e-\u0957\u0962-\u0984\u098d-\u098e\u0991-\u0992\u09a9\u09b1\u09b3-\u09b5\u09ba-\u09db\u09de\u09e2-\u09ef\u09f2-\u0a04\u0a0b-\u0a0e\u0a11-\u0a12\u0a29\u0a31\u0a34\u0a37\u0a3a-\u0a58\u0a5d\u0a5f-\u0a71\u0a75-\u0a84\u0a8c\u0a8e\u0a92\u0aa9\u0ab1\u0ab4\u0aba-\u0abc\u0abe-\u0adf\u0ae1-\u0b04\u0b0d-\u0b0e\u0b11-\u0b12\u0b29\u0b31\u0b34-\u0b35\u0b3a-\u0b3c\u0b3e-\u0b5b\u0b5e\u0b62-\u0b84\u0b8b-\u0b8d\u0b91\u0b96-\u0b98\u0b9b\u0b9d\u0ba0-\u0ba2\u0ba5-\u0ba7\u0bab-\u0bad\u0bb6\u0bba-\u0c04\u0c0d\u0c11\u0c29\u0c34\u0c3a-\u0c5f\u0c62-\u0c84\u0c8d\u0c91\u0ca9\u0cb4\u0cba-\u0cdd\u0cdf\u0ce2-\u0d04\u0d0d\u0d11\u0d29\u0d3a-\u0d5f\u0d62-\u0e00\u0e2f\u0e31\u0e34-\u0e3f\u0e46-\u0e80\u0e83\u0e85-\u0e86\u0e89\u0e8b-\u0e8c\u0e8e-\u0e93\u0e98\u0ea0\u0ea4\u0ea6\u0ea8-\u0ea9\u0eac\u0eaf\u0eb1\u0eb4-\u0ebc\u0ebe-\u0ebf\u0ec5-\u0f3f\u0f48\u0f6a-\u109f\u10c6-\u10cf\u10f7-\u10ff\u1101\u1104\u1108\u110a\u110d\u1113-\u113b\u113d\u113f\u1141-\u114b\u114d\u114f\u1151-\u1153\u1156-\u1158\u115a-\u115e\u1162\u1164\u1166\u1168\u116a-\u116c\u116f-\u1171\u1174\u1176-\u119d\u119f-\u11a7\u11a9-\u11aa\u11ac-\u11ad\u11b0-\u11b6\u11b9\u11bb\u11c3-\u11ea\u11ec-\u11ef\u11f1-\u11f8\u11fa-\u1dff\u1e9c-\u1e9f\u1efa-\u1eff\u1f16-\u1f17\u1f1e-\u1f1f\u1f46-\u1f47\u1f4e-\u1f4f\u1f58\u1f5a\u1f5c\u1f5e\u1f7e-\u1f7f\u1fb5\u1fbd\u1fbf-\u1fc1\u1fc5\u1fcd-\u1fcf\u1fd4-\u1fd5\u1fdc-\u1fdf\u1fed-\u1ff1\u1ff5\u1ffd-\u2125\u2127-\u2129\u212c-\u212d\u212f-\u217f\u2183-\u3006\u3008-\u3020\u302a-\u3040\u3095-\u30a0\u30fb-\u3104\u312d-\u4dff\u9fa6-\uabff\ud7a4-\uffff]')

class InfosetFilter(object):
    replacementRegexp = re.compile(r"U[\dA-F]{5,5}")
    def __init__(self, replaceChars = None,  
                 dropXmlnsLocalName = False, 
                 dropXmlnsAttrNs = False,
                 preventDoubleDashComments = False,
                 preventDashAtCommentEnd = False,
                 replaceFormFeedCharacters = True):

        self.dropXmlnsLocalName = dropXmlnsLocalName
        self.dropXmlnsAttrNs = dropXmlnsAttrNs

        self.preventDoubleDashComments = preventDoubleDashComments
        self.preventDashAtCommentEnd = preventDashAtCommentEnd

        self.replaceFormFeedCharacters = replaceFormFeedCharacters

        self.replaceCache = {}

    def coerceAttribute(self, name, namespace=None):
        if self.dropXmlnsLocalName and name.startswith("xmlns:"):
            #Need a datalosswarning here
            return None
        elif (self.dropXmlnsAttrNs and 
              namespace == "http://www.w3.org/2000/xmlns/"):
            return None
        else:
            return self.toXmlName(name)

    def coerceElement(self, name, namespace=None):
        return self.toXmlName(name)

    def coerceComment(self, data):
        if self.preventDoubleDashComments:
            while "--" in data:
                data = data.replace("--", "- -")
        return data
    
    def coerceCharacters(self, data):
        if self.replaceFormFeedCharacters:
            data = data.replace("\x0C", " ")
        #Other non-xml characters
        return data

    def toXmlName(self, name):
        nameFirst = name[0]
        nameRest = name[1:]
        m = nonXmlNameFirstBMPRegexp.match(nameFirst)
        if m:
            nameFirstOutput = self.getReplacementCharacter(nameFirst)
        else:
            nameFirstOutput = nameFirst

        nameRestOutput = nameRest
        replaceChars = set(nonXmlNameBMPRegexp.findall(nameRest))
        for char in replaceChars:
            replacement = self.getReplacementCharacter(char)
            nameRestOutput = nameRestOutput.replace(char, replacement)
        return nameFirstOutput + nameRestOutput
    
    def getReplacementCharacter(self, char):
        if char in self.replaceCache:
            replacement = self.replaceCache[char]
        else:
            replacement = self.escapeChar(char)
        return replacement

    def fromXmlName(self, name):
        for item in set(self.replacementRegexp.findall(name)):
            name = name.replace(item, self.unescapeChar(item))
        return name

    def escapeChar(self, char):
        replacement = "U" + hex(ord(char))[2:].upper().rjust(5, "0")
        self.replaceCache[char] = replacement
        return replacement

    def unescapeChar(self, charcode):
        return unichr(int(charcode[1:], 16))

########NEW FILE########
__FILENAME__ = inputstream
import codecs
import re
import types
import sys

from constants import EOF, spaceCharacters, asciiLetters, asciiUppercase
from constants import encodings, ReparseException
import utils

#Non-unicode versions of constants for use in the pre-parser
spaceCharactersBytes = frozenset([str(item) for item in spaceCharacters])
asciiLettersBytes = frozenset([str(item) for item in asciiLetters])
asciiUppercaseBytes = frozenset([str(item) for item in asciiUppercase])
spacesAngleBrackets = spaceCharactersBytes | frozenset([">", "<"])

invalid_unicode_re = re.compile(u"[\u0001-\u0008\u000B\u000E-\u001F\u007F-\u009F\uD800-\uDFFF\uFDD0-\uFDEF\uFFFE\uFFFF\U0001FFFE\U0001FFFF\U0002FFFE\U0002FFFF\U0003FFFE\U0003FFFF\U0004FFFE\U0004FFFF\U0005FFFE\U0005FFFF\U0006FFFE\U0006FFFF\U0007FFFE\U0007FFFF\U0008FFFE\U0008FFFF\U0009FFFE\U0009FFFF\U000AFFFE\U000AFFFF\U000BFFFE\U000BFFFF\U000CFFFE\U000CFFFF\U000DFFFE\U000DFFFF\U000EFFFE\U000EFFFF\U000FFFFE\U000FFFFF\U0010FFFE\U0010FFFF]")

non_bmp_invalid_codepoints = set([0x1FFFE, 0x1FFFF, 0x2FFFE, 0x2FFFF, 0x3FFFE,
                                  0x3FFFF, 0x4FFFE, 0x4FFFF, 0x5FFFE, 0x5FFFF,
                                  0x6FFFE, 0x6FFFF, 0x7FFFE, 0x7FFFF, 0x8FFFE,
                                  0x8FFFF, 0x9FFFE, 0x9FFFF, 0xAFFFE, 0xAFFFF,
                                  0xBFFFE, 0xBFFFF, 0xCFFFE, 0xCFFFF, 0xDFFFE,
                                  0xDFFFF, 0xEFFFE, 0xEFFFF, 0xFFFFE, 0xFFFFF,
                                  0x10FFFE, 0x10FFFF])

ascii_punctuation_re = re.compile(ur"[\u0009-\u000D\u0020-\u002F\u003A-\u0040\u005B-\u0060\u007B-\u007E]")

# Cache for charsUntil()
charsUntilRegEx = {}
        
class BufferedStream:
    """Buffering for streams that do not have buffering of their own

    The buffer is implemented as a list of chunks on the assumption that 
    joining many strings will be slow since it is O(n**2)
    """
    
    def __init__(self, stream):
        self.stream = stream
        self.buffer = []
        self.position = [-1,0] #chunk number, offset

    def tell(self):
        pos = 0
        for chunk in self.buffer[:self.position[0]]:
            pos += len(chunk)
        pos += self.position[1]
        return pos

    def seek(self, pos):
        assert pos < self._bufferedBytes()
        offset = pos
        i = 0
        while len(self.buffer[i]) < offset:
            offset -= pos
            i += 1
        self.position = [i, offset]

    def read(self, bytes):
        if not self.buffer:
            return self._readStream(bytes)
        elif (self.position[0] == len(self.buffer) and
              self.position[1] == len(self.buffer[-1])):
            return self._readStream(bytes)
        else:
            return self._readFromBuffer(bytes)
    
    def _bufferedBytes(self):
        return sum([len(item) for item in self.buffer])

    def _readStream(self, bytes):
        data = self.stream.read(bytes)
        self.buffer.append(data)
        self.position[0] += 1
        self.position[1] = len(data)
        return data

    def _readFromBuffer(self, bytes):
        remainingBytes = bytes
        rv = []
        bufferIndex = self.position[0]
        bufferOffset = self.position[1]
        while bufferIndex < len(self.buffer) and remainingBytes != 0:
            assert remainingBytes > 0
            bufferedData = self.buffer[bufferIndex]
            
            if remainingBytes <= len(bufferedData) - bufferOffset:
                bytesToRead = remainingBytes
                self.position = [bufferIndex, bufferOffset + bytesToRead]
            else:
                bytesToRead = len(bufferedData) - bufferOffset
                self.position = [bufferIndex, len(bufferedData)]
                bufferIndex += 1
            data = rv.append(bufferedData[bufferOffset: 
                                          bufferOffset + bytesToRead])
            remainingBytes -= bytesToRead

            bufferOffset = 0

        if remainingBytes:
            rv.append(self._readStream(remainingBytes))
        
        return "".join(rv)
        


class HTMLInputStream:
    """Provides a unicode stream of characters to the HTMLTokenizer.

    This class takes care of character encoding and removing or replacing
    incorrect byte-sequences and also provides column and line tracking.

    """

    _defaultChunkSize = 10240

    def __init__(self, source, encoding=None, parseMeta=True, chardet=True):
        """Initialises the HTMLInputStream.

        HTMLInputStream(source, [encoding]) -> Normalized stream from source
        for use by html5lib.

        source can be either a file-object, local filename or a string.

        The optional encoding parameter must be a string that indicates
        the encoding.  If specified, that encoding will be used,
        regardless of any BOM or later declaration (such as in a meta
        element)
        
        parseMeta - Look for a <meta> element containing encoding information

        """

        #Craziness
        if len(u"\U0010FFFF") == 1:
            self.reportCharacterErrors = self.characterErrorsUCS4
        else:
            self.reportCharacterErrors = self.characterErrorsUCS2

        # List of where new lines occur
        self.newLines = [0]

        self.charEncoding = (codecName(encoding), "certain")

        # Raw Stream - for unicode objects this will encode to utf-8 and set
        #              self.charEncoding as appropriate
        self.rawStream = self.openStream(source)

        # Encoding Information
        #Number of bytes to use when looking for a meta element with
        #encoding information
        self.numBytesMeta = 512
        #Number of bytes to use when using detecting encoding using chardet
        self.numBytesChardet = 100
        #Encoding to use if no other information can be found
        self.defaultEncoding = "windows-1252"
        
        #Detect encoding iff no explicit "transport level" encoding is supplied
        if (self.charEncoding[0] is None):
            self.charEncoding = self.detectEncoding(parseMeta, chardet)

        self.reset()

    def reset(self):
        self.dataStream = codecs.getreader(self.charEncoding[0])(self.rawStream,
                                                                 'replace')

        self.chunk = u""
        self.chunkSize = 0
        self.chunkOffset = 0
        self.errors = []

        # number of (complete) lines in previous chunks
        self.prevNumLines = 0
        # number of columns in the last line of the previous chunk
        self.prevNumCols = 0
        
        #Flag to indicate we may have a CR LF broken across a data chunk
        self._lastChunkEndsWithCR = False

    def openStream(self, source):
        """Produces a file object from source.

        source can be either a file object, local filename or a string.

        """
        # Already a file object
        if hasattr(source, 'read'):
            stream = source
        else:
            # Otherwise treat source as a string and convert to a file object
            if isinstance(source, unicode):
                source = source.encode('utf-8')
                self.charEncoding = ("utf-8", "certain")
            import cStringIO
            stream = cStringIO.StringIO(str(source))

        if (not(hasattr(stream, "tell") and hasattr(stream, "seek")) or
            stream is sys.stdin):
            stream = BufferedStream(stream)

        return stream

    def detectEncoding(self, parseMeta=True, chardet=True):
        #First look for a BOM
        #This will also read past the BOM if present
        encoding = self.detectBOM()
        confidence = "certain"
        #If there is no BOM need to look for meta elements with encoding 
        #information
        if encoding is None and parseMeta:
            encoding = self.detectEncodingMeta()
            confidence = "tentative"
        #Guess with chardet, if avaliable
        if encoding is None and chardet:
            confidence = "tentative"
            try:
                from chardet.universaldetector import UniversalDetector
                buffers = []
                detector = UniversalDetector()
                while not detector.done:
                    buffer = self.rawStream.read(self.numBytesChardet)
                    if not buffer:
                        break
                    buffers.append(buffer)
                    detector.feed(buffer)
                detector.close()
                encoding = detector.result['encoding']
                self.rawStream.seek(0)
            except ImportError:
                pass
        # If all else fails use the default encoding
        if encoding is None:
            confidence="tentative"
            encoding = self.defaultEncoding
        
        #Substitute for equivalent encodings:
        encodingSub = {"iso-8859-1":"windows-1252"}

        if encoding.lower() in encodingSub:
            encoding = encodingSub[encoding.lower()]

        return encoding, confidence

    def changeEncoding(self, newEncoding):
        newEncoding = codecName(newEncoding)
        if newEncoding in ("utf-16", "utf-16-be", "utf-16-le"):
            newEncoding = "utf-8"
        if newEncoding is None:
            return
        elif newEncoding == self.charEncoding[0]:
            self.charEncoding = (self.charEncoding[0], "certain")
        else:
            self.rawStream.seek(0)
            self.reset()
            self.charEncoding = (newEncoding, "certain")
            raise ReparseException, "Encoding changed from %s to %s"%(self.charEncoding[0], newEncoding)
            
    def detectBOM(self):
        """Attempts to detect at BOM at the start of the stream. If
        an encoding can be determined from the BOM return the name of the
        encoding otherwise return None"""
        bomDict = {
            codecs.BOM_UTF8: 'utf-8',
            codecs.BOM_UTF16_LE: 'utf-16-le', codecs.BOM_UTF16_BE: 'utf-16-be',
            codecs.BOM_UTF32_LE: 'utf-32-le', codecs.BOM_UTF32_BE: 'utf-32-be'
        }

        # Go to beginning of file and read in 4 bytes
        string = self.rawStream.read(4)

        # Try detecting the BOM using bytes from the string
        encoding = bomDict.get(string[:3])         # UTF-8
        seek = 3
        if not encoding:
            # Need to detect UTF-32 before UTF-16
            encoding = bomDict.get(string)         # UTF-32
            seek = 4
            if not encoding:
                encoding = bomDict.get(string[:2]) # UTF-16
                seek = 2

        # Set the read position past the BOM if one was found, otherwise
        # set it to the start of the stream
        self.rawStream.seek(encoding and seek or 0)

        return encoding

    def detectEncodingMeta(self):
        """Report the encoding declared by the meta element
        """
        buffer = self.rawStream.read(self.numBytesMeta)
        parser = EncodingParser(buffer)
        self.rawStream.seek(0)
        encoding = parser.getEncoding()
        
        if encoding in ("utf-16", "utf-16-be", "utf-16-le"):
            encoding = "utf-8"

        return encoding

    def _position(self, offset):
        chunk = self.chunk
        nLines = chunk.count(u'\n', 0, offset)
        positionLine = self.prevNumLines + nLines
        lastLinePos = chunk.rfind(u'\n', 0, offset)
        if lastLinePos == -1:
            positionColumn = self.prevNumCols + offset
        else:
            positionColumn = offset - (lastLinePos + 1)
        return (positionLine, positionColumn)

    def position(self):
        """Returns (line, col) of the current position in the stream."""
        line, col = self._position(self.chunkOffset)
        return (line+1, col)

    def char(self):
        """ Read one character from the stream or queue if available. Return
            EOF when EOF is reached.
        """
        # Read a new chunk from the input stream if necessary
        if self.chunkOffset >= self.chunkSize:
            if not self.readChunk():
                return EOF

        chunkOffset = self.chunkOffset
        char = self.chunk[chunkOffset]
        self.chunkOffset = chunkOffset + 1

        return char

    def readChunk(self, chunkSize=None):
        if chunkSize is None:
            chunkSize = self._defaultChunkSize

        self.prevNumLines, self.prevNumCols = self._position(self.chunkSize)

        self.chunk = u""
        self.chunkSize = 0
        self.chunkOffset = 0

        data = self.dataStream.read(chunkSize)

        if not data:
            return False
        
        self.reportCharacterErrors(data)

        data = data.replace(u"\u0000", u"\ufffd")
        #Check for CR LF broken across chunks
        if (self._lastChunkEndsWithCR and data[0] == u"\n"):
            data = data[1:]
            # Stop if the chunk is now empty
            if not data:
                return False
        self._lastChunkEndsWithCR = data[-1] == u"\r"
        data = data.replace(u"\r\n", u"\n")
        data = data.replace(u"\r", u"\n")

        self.chunk = data
        self.chunkSize = len(data)

        return True

    def characterErrorsUCS4(self, data):
        for i in xrange(data.count(u"\u0000")):
            self.errors.append("null-character")
        for i in xrange(len(invalid_unicode_re.findall(data))):
            self.errors.append("invalid-codepoint")

    def characterErrorsUCS2(self, data):
        #Someone picked the wrong compile option
        #You lose
        for i in xrange(data.count(u"\u0000")):
            self.errors.append("null-character")
        skip = False
        import sys
        for match in invalid_unicode_re.finditer(data):
            if skip:
                continue
            codepoint = ord(match.group())
            pos = match.start()
            #Pretty sure there should be endianness issues here
            if utils.isSurrogatePair(data[pos:pos+2]):
                #We have a surrogate pair!
                char_val = utils.surrogatePairToCodepoint(data[pos:pos+2])
                if char_val in non_bmp_invalid_codepoints:
                    self.errors.append("invalid-codepoint")
                skip = True
            elif (codepoint >= 0xD800 and codepoint <= 0xDFFF and
                  pos == len(data) - 1):
                self.errors.append("invalid-codepoint")
            else:
                skip = False
                self.errors.append("invalid-codepoint")
        #This is still wrong if it is possible for a surrogate pair to break a
        #chunk boundary

    def charsUntil(self, characters, opposite = False):
        """ Returns a string of characters from the stream up to but not
        including any character in 'characters' or EOF. 'characters' must be
        a container that supports the 'in' method and iteration over its
        characters.
        """

        # Use a cache of regexps to find the required characters
        try:
            chars = charsUntilRegEx[(characters, opposite)]
        except KeyError:
            if __debug__:
                for c in characters: 
                    assert(ord(c) < 128)
            regex = u"".join([u"\\x%02x" % ord(c) for c in characters])
            if not opposite:
                regex = u"^%s" % regex
            chars = charsUntilRegEx[(characters, opposite)] = re.compile(u"[%s]+" % regex)

        rv = []

        while True:
            # Find the longest matching prefix
            m = chars.match(self.chunk, self.chunkOffset)
            if m is None:
                # If nothing matched, and it wasn't because we ran out of chunk,
                # then stop
                if self.chunkOffset != self.chunkSize:
                    break
            else:
                end = m.end()
                # If not the whole chunk matched, return everything
                # up to the part that didn't match
                if end != self.chunkSize:
                    rv.append(self.chunk[self.chunkOffset:end])
                    self.chunkOffset = end
                    break
            # If the whole remainder of the chunk matched,
            # use it all and read the next chunk
            rv.append(self.chunk[self.chunkOffset:])
            if not self.readChunk():
                # Reached EOF
                break

        r = u"".join(rv)
        return r

    def charsUntilEOF(self):
        """ Returns a string of characters from the stream up to EOF."""

        rv = []

        while True:
            rv.append(self.chunk[self.chunkOffset:])
            if not self.readChunk():
                # Reached EOF
                break

        r = u"".join(rv)
        return r

    def unget(self, char):
        # Only one character is allowed to be ungotten at once - it must
        # be consumed again before any further call to unget

        if char is not None:
            if self.chunkOffset == 0:
                # unget is called quite rarely, so it's a good idea to do
                # more work here if it saves a bit of work in the frequently
                # called char and charsUntil.
                # So, just prepend the ungotten character onto the current
                # chunk:
                self.chunk = char + self.chunk
                self.chunkSize += 1
            else:
                self.chunkOffset -= 1
                assert self.chunk[self.chunkOffset] == char

class EncodingBytes(str):
    """String-like object with an associated position and various extra methods
    If the position is ever greater than the string length then an exception is
    raised"""
    def __new__(self, value):
        return str.__new__(self, value.lower())

    def __init__(self, value):
        self._position=-1
    
    def __iter__(self):
        return self
    
    def next(self):
        p = self._position = self._position + 1
        if p >= len(self):
            raise StopIteration
        elif p < 0:
            raise TypeError
        return self[p]

    def previous(self):
        p = self._position
        if p >= len(self):
            raise StopIteration
        elif p < 0:
            raise TypeError
        self._position = p = p - 1
        return self[p]
    
    def setPosition(self, position):
        if self._position >= len(self):
            raise StopIteration
        self._position = position
    
    def getPosition(self):
        if self._position >= len(self):
            raise StopIteration
        if self._position >= 0:
            return self._position
        else:
            return None
    
    position = property(getPosition, setPosition)

    def getCurrentByte(self):
        return self[self.position]
    
    currentByte = property(getCurrentByte)

    def skip(self, chars=spaceCharactersBytes):
        """Skip past a list of characters"""
        p = self.position               # use property for the error-checking
        while p < len(self):
            c = self[p]
            if c not in chars:
                self._position = p
                return c
            p += 1
        self._position = p
        return None

    def skipUntil(self, chars):
        p = self.position
        while p < len(self):
            c = self[p]
            if c in chars:
                self._position = p
                return c
            p += 1
        self._position = p
        return None

    def matchBytes(self, bytes):
        """Look for a sequence of bytes at the start of a string. If the bytes 
        are found return True and advance the position to the byte after the 
        match. Otherwise return False and leave the position alone"""
        p = self.position
        data = self[p:p+len(bytes)]
        rv = data.startswith(bytes)
        if rv:
            self.position += len(bytes)
        return rv
    
    def jumpTo(self, bytes):
        """Look for the next sequence of bytes matching a given sequence. If
        a match is found advance the position to the last byte of the match"""
        newPosition = self[self.position:].find(bytes)
        if newPosition > -1:
            # XXX: This is ugly, but I can't see a nicer way to fix this.
            if self._position == -1:
                self._position = 0
            self._position += (newPosition + len(bytes)-1)
            return True
        else:
            raise StopIteration

class EncodingParser(object):
    """Mini parser for detecting character encoding from meta elements"""

    def __init__(self, data):
        """string - the data to work on for encoding detection"""
        self.data = EncodingBytes(data)
        self.encoding = None

    def getEncoding(self):
        methodDispatch = (
            ("<!--",self.handleComment),
            ("<meta",self.handleMeta),
            ("</",self.handlePossibleEndTag),
            ("<!",self.handleOther),
            ("<?",self.handleOther),
            ("<",self.handlePossibleStartTag))
        for byte in self.data:
            keepParsing = True
            for key, method in methodDispatch:
                if self.data.matchBytes(key):
                    try:
                        keepParsing = method()    
                        break
                    except StopIteration:
                        keepParsing=False
                        break
            if not keepParsing:
                break
        
        return self.encoding

    def handleComment(self):
        """Skip over comments"""
        return self.data.jumpTo("-->")

    def handleMeta(self):
        if self.data.currentByte not in spaceCharactersBytes:
            #if we have <meta not followed by a space so just keep going
            return True
        #We have a valid meta element we want to search for attributes
        while True:
            #Try to find the next attribute after the current position
            attr = self.getAttribute()
            if attr is None:
                return True
            else:
                if attr[0] == "charset":
                    tentativeEncoding = attr[1]
                    codec = codecName(tentativeEncoding)
                    if codec is not None:
                        self.encoding = codec
                        return False
                elif attr[0] == "content":
                    contentParser = ContentAttrParser(EncodingBytes(attr[1]))
                    tentativeEncoding = contentParser.parse()
                    codec = codecName(tentativeEncoding)
                    if codec is not None:
                        self.encoding = codec
                        return False

    def handlePossibleStartTag(self):
        return self.handlePossibleTag(False)

    def handlePossibleEndTag(self):
        self.data.next()
        return self.handlePossibleTag(True)

    def handlePossibleTag(self, endTag):
        data = self.data
        if data.currentByte not in asciiLettersBytes:
            #If the next byte is not an ascii letter either ignore this
            #fragment (possible start tag case) or treat it according to 
            #handleOther
            if endTag:
                data.previous()
                self.handleOther()
            return True
        
        c = data.skipUntil(spacesAngleBrackets)
        if c == "<":
            #return to the first step in the overall "two step" algorithm
            #reprocessing the < byte
            data.previous()
        else:
            #Read all attributes
            attr = self.getAttribute()
            while attr is not None:
                attr = self.getAttribute()
        return True

    def handleOther(self):
        return self.data.jumpTo(">")

    def getAttribute(self):
        """Return a name,value pair for the next attribute in the stream, 
        if one is found, or None"""
        data = self.data
        # Step 1 (skip chars)
        c = data.skip(spaceCharactersBytes | frozenset("/"))
        # Step 2
        if c in (">", None):
            return None
        # Step 3
        attrName = []
        attrValue = []
        #Step 4 attribute name
        while True:
            if c == "=" and attrName:   
                break
            elif c in spaceCharactersBytes:
                #Step 6!
                c = data.skip()
                c = data.next()
                break
            elif c in ("/", ">"):
                return "".join(attrName), ""
            elif c in asciiUppercaseBytes:
                attrName.append(c.lower())
            elif c == None:
                return None
            else:
                attrName.append(c)
            #Step 5
            c = data.next()
        #Step 7
        if c != "=":
            data.previous()
            return "".join(attrName), ""
        #Step 8
        data.next()
        #Step 9
        c = data.skip()
        #Step 10
        if c in ("'", '"'):
            #10.1
            quoteChar = c
            while True:
                #10.2
                c = data.next()
                #10.3
                if c == quoteChar:
                    data.next()
                    return "".join(attrName), "".join(attrValue)
                #10.4
                elif c in asciiUppercaseBytes:
                    attrValue.append(c.lower())
                #10.5
                else:
                    attrValue.append(c)
        elif c == ">":
            return "".join(attrName), ""
        elif c in asciiUppercaseBytes:
            attrValue.append(c.lower())
        elif c is None:
            return None
        else:
            attrValue.append(c)
        # Step 11
        while True:
            c = data.next()
            if c in spacesAngleBrackets:
                return "".join(attrName), "".join(attrValue)
            elif c in asciiUppercaseBytes:
                attrValue.append(c.lower())
            elif c is None:
                return None
            else:
                attrValue.append(c)


class ContentAttrParser(object):
    def __init__(self, data):
        self.data = data
    def parse(self):
        try:
            #Check if the attr name is charset 
            #otherwise return
            self.data.jumpTo("charset")
            self.data.position += 1
            self.data.skip()
            if not self.data.currentByte == "=":
                #If there is no = sign keep looking for attrs
                return None
            self.data.position += 1
            self.data.skip()
            #Look for an encoding between matching quote marks
            if self.data.currentByte in ('"', "'"):
                quoteMark = self.data.currentByte
                self.data.position += 1
                oldPosition = self.data.position
                if self.data.jumpTo(quoteMark):
                    return self.data[oldPosition:self.data.position]
                else:
                    return None
            else:
                #Unquoted value
                oldPosition = self.data.position
                try:
                    self.data.skipUntil(spaceCharactersBytes)
                    return self.data[oldPosition:self.data.position]
                except StopIteration:
                    #Return the whole remaining value
                    return self.data[oldPosition:]
        except StopIteration:
            return None


def codecName(encoding):
    """Return the python codec name corresponding to an encoding or None if the
    string doesn't correspond to a valid encoding."""
    if (encoding is not None and type(encoding) in types.StringTypes):
        canonicalName = ascii_punctuation_re.sub("", encoding).lower()
        return encodings.get(canonicalName, None)
    else:
        return None

########NEW FILE########
__FILENAME__ = sanitizer
import re
from xml.sax.saxutils import escape, unescape

from tokenizer import HTMLTokenizer
from constants import tokenTypes

class HTMLSanitizerMixin(object):
    """ sanitization of XHTML+MathML+SVG and of inline style attributes."""

    acceptable_elements = ['a', 'abbr', 'acronym', 'address', 'area',
        'article', 'aside', 'audio', 'b', 'big', 'blockquote', 'br', 'button',
        'canvas', 'caption', 'center', 'cite', 'code', 'col', 'colgroup',
        'command', 'datagrid', 'datalist', 'dd', 'del', 'details', 'dfn',
        'dialog', 'dir', 'div', 'dl', 'dt', 'em', 'event-source', 'fieldset',
        'figure', 'footer', 'font', 'form', 'header', 'h1', 'h2', 'h3', 'h4',
        'h5', 'h6', 'hr', 'i', 'img', 'input', 'ins', 'keygen', 'kbd',
        'label', 'legend', 'li', 'm', 'map', 'menu', 'meter', 'multicol',
        'nav', 'nextid', 'ol', 'output', 'optgroup', 'option', 'p', 'pre',
        'progress', 'q', 's', 'samp', 'section', 'select', 'small', 'sound',
        'source', 'spacer', 'span', 'strike', 'strong', 'sub', 'sup', 'table',
        'tbody', 'td', 'textarea', 'time', 'tfoot', 'th', 'thead', 'tr', 'tt',
        'u', 'ul', 'var', 'video']
      
    mathml_elements = ['maction', 'math', 'merror', 'mfrac', 'mi',
        'mmultiscripts', 'mn', 'mo', 'mover', 'mpadded', 'mphantom',
        'mprescripts', 'mroot', 'mrow', 'mspace', 'msqrt', 'mstyle', 'msub',
        'msubsup', 'msup', 'mtable', 'mtd', 'mtext', 'mtr', 'munder',
        'munderover', 'none']
      
    svg_elements = ['a', 'animate', 'animateColor', 'animateMotion',
        'animateTransform', 'clipPath', 'circle', 'defs', 'desc', 'ellipse',
        'font-face', 'font-face-name', 'font-face-src', 'g', 'glyph', 'hkern',
        'linearGradient', 'line', 'marker', 'metadata', 'missing-glyph',
        'mpath', 'path', 'polygon', 'polyline', 'radialGradient', 'rect',
        'set', 'stop', 'svg', 'switch', 'text', 'title', 'tspan', 'use']
        
    acceptable_attributes = ['abbr', 'accept', 'accept-charset', 'accesskey',
        'action', 'align', 'alt', 'autocomplete', 'autofocus', 'axis',
        'background', 'balance', 'bgcolor', 'bgproperties', 'border',
        'bordercolor', 'bordercolordark', 'bordercolorlight', 'bottompadding',
        'cellpadding', 'cellspacing', 'ch', 'challenge', 'char', 'charoff',
        'choff', 'charset', 'checked', 'cite', 'class', 'clear', 'color',
        'cols', 'colspan', 'compact', 'contenteditable', 'controls', 'coords',
        'data', 'datafld', 'datapagesize', 'datasrc', 'datetime', 'default',
        'delay', 'dir', 'disabled', 'draggable', 'dynsrc', 'enctype', 'end',
        'face', 'for', 'form', 'frame', 'galleryimg', 'gutter', 'headers',
        'height', 'hidefocus', 'hidden', 'high', 'href', 'hreflang', 'hspace',
        'icon', 'id', 'inputmode', 'ismap', 'keytype', 'label', 'leftspacing',
        'lang', 'list', 'longdesc', 'loop', 'loopcount', 'loopend',
        'loopstart', 'low', 'lowsrc', 'max', 'maxlength', 'media', 'method',
        'min', 'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'open',
        'optimum', 'pattern', 'ping', 'point-size', 'prompt', 'pqg',
        'radiogroup', 'readonly', 'rel', 'repeat-max', 'repeat-min',
        'replace', 'required', 'rev', 'rightspacing', 'rows', 'rowspan',
        'rules', 'scope', 'selected', 'shape', 'size', 'span', 'src', 'start',
        'step', 'style', 'summary', 'suppress', 'tabindex', 'target',
        'template', 'title', 'toppadding', 'type', 'unselectable', 'usemap',
        'urn', 'valign', 'value', 'variable', 'volume', 'vspace', 'vrml',
        'width', 'wrap', 'xml:lang']

    mathml_attributes = ['actiontype', 'align', 'columnalign', 'columnalign',
        'columnalign', 'columnlines', 'columnspacing', 'columnspan', 'depth',
        'display', 'displaystyle', 'equalcolumns', 'equalrows', 'fence',
        'fontstyle', 'fontweight', 'frame', 'height', 'linethickness', 'lspace',
        'mathbackground', 'mathcolor', 'mathvariant', 'mathvariant', 'maxsize',
        'minsize', 'other', 'rowalign', 'rowalign', 'rowalign', 'rowlines',
        'rowspacing', 'rowspan', 'rspace', 'scriptlevel', 'selection',
        'separator', 'stretchy', 'width', 'width', 'xlink:href', 'xlink:show',
        'xlink:type', 'xmlns', 'xmlns:xlink']
  
    svg_attributes = ['accent-height', 'accumulate', 'additive', 'alphabetic',
        'arabic-form', 'ascent', 'attributeName', 'attributeType',
        'baseProfile', 'bbox', 'begin', 'by', 'calcMode', 'cap-height',
        'class', 'clip-path', 'color', 'color-rendering', 'content', 'cx',
        'cy', 'd', 'dx', 'dy', 'descent', 'display', 'dur', 'end', 'fill',
        'fill-opacity', 'fill-rule', 'font-family', 'font-size',
        'font-stretch', 'font-style', 'font-variant', 'font-weight', 'from',
        'fx', 'fy', 'g1', 'g2', 'glyph-name', 'gradientUnits', 'hanging',
        'height', 'horiz-adv-x', 'horiz-origin-x', 'id', 'ideographic', 'k',
        'keyPoints', 'keySplines', 'keyTimes', 'lang', 'marker-end',
        'marker-mid', 'marker-start', 'markerHeight', 'markerUnits',
        'markerWidth', 'mathematical', 'max', 'min', 'name', 'offset',
        'opacity', 'orient', 'origin', 'overline-position',
        'overline-thickness', 'panose-1', 'path', 'pathLength', 'points',
        'preserveAspectRatio', 'r', 'refX', 'refY', 'repeatCount',
        'repeatDur', 'requiredExtensions', 'requiredFeatures', 'restart',
        'rotate', 'rx', 'ry', 'slope', 'stemh', 'stemv', 'stop-color',
        'stop-opacity', 'strikethrough-position', 'strikethrough-thickness',
        'stroke', 'stroke-dasharray', 'stroke-dashoffset', 'stroke-linecap',
        'stroke-linejoin', 'stroke-miterlimit', 'stroke-opacity',
        'stroke-width', 'systemLanguage', 'target', 'text-anchor', 'to',
        'transform', 'type', 'u1', 'u2', 'underline-position',
        'underline-thickness', 'unicode', 'unicode-range', 'units-per-em',
        'values', 'version', 'viewBox', 'visibility', 'width', 'widths', 'x',
        'x-height', 'x1', 'x2', 'xlink:actuate', 'xlink:arcrole',
        'xlink:href', 'xlink:role', 'xlink:show', 'xlink:title', 'xlink:type',
        'xml:base', 'xml:lang', 'xml:space', 'xmlns', 'xmlns:xlink', 'y',
        'y1', 'y2', 'zoomAndPan']

    attr_val_is_uri = ['href', 'src', 'cite', 'action', 'longdesc',
        'xlink:href', 'xml:base']

    svg_attr_val_allows_ref = ['clip-path', 'color-profile', 'cursor', 'fill',
        'filter', 'marker', 'marker-start', 'marker-mid', 'marker-end',
        'mask', 'stroke']

    svg_allow_local_href = ['altGlyph', 'animate', 'animateColor',
        'animateMotion', 'animateTransform', 'cursor', 'feImage', 'filter',
        'linearGradient', 'pattern', 'radialGradient', 'textpath', 'tref',
        'set', 'use']
  
    acceptable_css_properties = ['azimuth', 'background-color',
        'border-bottom-color', 'border-collapse', 'border-color',
        'border-left-color', 'border-right-color', 'border-top-color', 'clear',
        'color', 'cursor', 'direction', 'display', 'elevation', 'float', 'font',
        'font-family', 'font-size', 'font-style', 'font-variant', 'font-weight',
        'height', 'letter-spacing', 'line-height', 'overflow', 'pause',
        'pause-after', 'pause-before', 'pitch', 'pitch-range', 'richness',
        'speak', 'speak-header', 'speak-numeral', 'speak-punctuation',
        'speech-rate', 'stress', 'text-align', 'text-decoration', 'text-indent',
        'unicode-bidi', 'vertical-align', 'voice-family', 'volume',
        'white-space', 'width']
  
    acceptable_css_keywords = ['auto', 'aqua', 'black', 'block', 'blue',
        'bold', 'both', 'bottom', 'brown', 'center', 'collapse', 'dashed',
        'dotted', 'fuchsia', 'gray', 'green', '!important', 'italic', 'left',
        'lime', 'maroon', 'medium', 'none', 'navy', 'normal', 'nowrap', 'olive',
        'pointer', 'purple', 'red', 'right', 'solid', 'silver', 'teal', 'top',
        'transparent', 'underline', 'white', 'yellow']
  
    acceptable_svg_properties = [ 'fill', 'fill-opacity', 'fill-rule',
        'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin',
        'stroke-opacity']
  
    acceptable_protocols = [ 'ed2k', 'ftp', 'http', 'https', 'irc',
        'mailto', 'news', 'gopher', 'nntp', 'telnet', 'webcal',
        'xmpp', 'callto', 'feed', 'urn', 'aim', 'rsync', 'tag',
        'ssh', 'sftp', 'rtsp', 'afs' ]
  
    # subclasses may define their own versions of these constants
    allowed_elements = acceptable_elements + mathml_elements + svg_elements
    allowed_attributes = acceptable_attributes + mathml_attributes + svg_attributes
    allowed_css_properties = acceptable_css_properties
    allowed_css_keywords = acceptable_css_keywords
    allowed_svg_properties = acceptable_svg_properties
    allowed_protocols = acceptable_protocols

    # Sanitize the +html+, escaping all elements not in ALLOWED_ELEMENTS, and
    # stripping out all # attributes not in ALLOWED_ATTRIBUTES. Style
    # attributes are parsed, and a restricted set, # specified by
    # ALLOWED_CSS_PROPERTIES and ALLOWED_CSS_KEYWORDS, are allowed through.
    # attributes in ATTR_VAL_IS_URI are scanned, and only URI schemes specified
    # in ALLOWED_PROTOCOLS are allowed.
    #
    #   sanitize_html('<script> do_nasty_stuff() </script>')
    #    => &lt;script> do_nasty_stuff() &lt;/script>
    #   sanitize_html('<a href="javascript: sucker();">Click here for $100</a>')
    #    => <a>Click here for $100</a>
    def sanitize_token(self, token):

        # accommodate filters which use token_type differently
        token_type = token["type"]
        if token_type in tokenTypes.keys():
          token_type = tokenTypes[token_type]

        if token_type in (tokenTypes["StartTag"], tokenTypes["EndTag"], 
                             tokenTypes["EmptyTag"]):
            if token["name"] in self.allowed_elements:
                if token.has_key("data"):
                    attrs = dict([(name,val) for name,val in
                                  token["data"][::-1] 
                                  if name in self.allowed_attributes])
                    for attr in self.attr_val_is_uri:
                        if not attrs.has_key(attr):
                            continue
                        val_unescaped = re.sub("[`\000-\040\177-\240\s]+", '',
                                               unescape(attrs[attr])).lower()
                        #remove replacement characters from unescaped characters
                        val_unescaped = val_unescaped.replace(u"\ufffd", "")
                        if (re.match("^[a-z0-9][-+.a-z0-9]*:",val_unescaped) and
                            (val_unescaped.split(':')[0] not in 
                             self.allowed_protocols)):
                            del attrs[attr]
                    for attr in self.svg_attr_val_allows_ref:
                        if attr in attrs:
                            attrs[attr] = re.sub(r'url\s*\(\s*[^#\s][^)]+?\)',
                                                 ' ',
                                                 unescape(attrs[attr]))
                    if (token["name"] in self.svg_allow_local_href and
                        'xlink:href' in attrs and re.search('^\s*[^#\s].*',
                                                            attrs['xlink:href'])):
                        del attrs['xlink:href']
                    if attrs.has_key('style'):
                        attrs['style'] = self.sanitize_css(attrs['style'])
                    token["data"] = [[name,val] for name,val in attrs.items()]
                return token
            else:
                if token_type == tokenTypes["EndTag"]:
                    token["data"] = "</%s>" % token["name"]
                elif token["data"]:
                    attrs = ''.join([' %s="%s"' % (k,escape(v)) for k,v in token["data"]])
                    token["data"] = "<%s%s>" % (token["name"],attrs)
                else:
                    token["data"] = "<%s>" % token["name"]
                if token.get("selfClosing"):
                    token["data"]=token["data"][:-1] + "/>"

                if token["type"] in tokenTypes.keys():
                    token["type"] = "Characters"
                else:
                    token["type"] = tokenTypes["Characters"]

                del token["name"]
                return token
        elif token_type == tokenTypes["Comment"]:
            pass
        else:
            return token

    def sanitize_css(self, style):
        # disallow urls
        style=re.compile('url\s*\(\s*[^\s)]+?\s*\)\s*').sub(' ',style)

        # gauntlet
        if not re.match("""^([:,;#%.\sa-zA-Z0-9!]|\w-\w|'[\s\w]+'|"[\s\w]+"|\([\d,\s]+\))*$""", style): return ''
        if not re.match("^\s*([-\w]+\s*:[^:;]*(;\s*|$))*$", style): return ''

        clean = []
        for prop,value in re.findall("([-\w]+)\s*:\s*([^:;]*)",style):
          if not value: continue
          if prop.lower() in self.allowed_css_properties:
              clean.append(prop + ': ' + value + ';')
          elif prop.split('-')[0].lower() in ['background','border','margin',
                                              'padding']:
              for keyword in value.split():
                  if not keyword in self.acceptable_css_keywords and \
                      not re.match("^(#[0-9a-f]+|rgb\(\d+%?,\d*%?,?\d*%?\)?|\d{0,2}\.?\d{0,2}(cm|em|ex|in|mm|pc|pt|px|%|,|\))?)$",keyword):
                      break
              else:
                  clean.append(prop + ': ' + value + ';')
          elif prop.lower() in self.allowed_svg_properties:
              clean.append(prop + ': ' + value + ';')

        return ' '.join(clean)

class HTMLSanitizer(HTMLTokenizer, HTMLSanitizerMixin):
    def __init__(self, stream, encoding=None, parseMeta=True, useChardet=True,
                 lowercaseElementName=False, lowercaseAttrName=False):
        #Change case matching defaults as we only output lowercase html anyway
        #This solution doesn't seem ideal...
        HTMLTokenizer.__init__(self, stream, encoding, parseMeta, useChardet,
                               lowercaseElementName, lowercaseAttrName)

    def __iter__(self):
        for token in HTMLTokenizer.__iter__(self):
            token = self.sanitize_token(token)
            if token:
                yield token

########NEW FILE########
__FILENAME__ = htmlserializer
try:
    frozenset
except NameError:
    # Import from the sets module for python 2.3
    from sets import ImmutableSet as frozenset

import gettext
_ = gettext.gettext

from html5lib.constants import voidElements, booleanAttributes, spaceCharacters
from html5lib.constants import rcdataElements, entities, xmlEntities
from html5lib import utils
from xml.sax.saxutils import escape

spaceCharacters = u"".join(spaceCharacters)

try:
    from codecs import register_error, xmlcharrefreplace_errors
except ImportError:
    unicode_encode_errors = "strict"
else:
    unicode_encode_errors = "htmlentityreplace"

    from html5lib.constants import entities

    encode_entity_map = {}
    for k, v in entities.items():
        if v != "&" and encode_entity_map.get(v) != k.lower():
            # prefer &lt; over &LT; and similarly for &amp;, &gt;, etc.
            encode_entity_map[ord(v)] = k

    def htmlentityreplace_errors(exc):
        if isinstance(exc, (UnicodeEncodeError, UnicodeTranslateError)):
            res = []
            codepoints = []
            skip = False
            for i, c in enumerate(exc.object[exc.start:exc.end]):
                if skip:
                    skip = False
                    continue
                index = i + exc.start
                if utils.isSurrogatePair(exc.object[index:min([exc.end, index+2])]):
                    codepoint = utils.surrogatePairToCodepoint(exc.object[index:index+2])
                    skip = True
                else:
                    codepoint = ord(c)
                codepoints.append(codepoint)
            for cp in codepoints:
                e = encode_entity_map.get(cp)
                if e:
                    res.append("&")
                    res.append(e)
                    if not e.endswith(";"):
                        res.append(";")
                else:
                    res.append("&#x%s;"%(hex(cp)[2:]))
            return (u"".join(res), exc.end)
        else:
            return xmlcharrefreplace_errors(exc)

    register_error(unicode_encode_errors, htmlentityreplace_errors)

    del register_error

def encode(text, encoding):
    return text.encode(encoding, unicode_encode_errors)

class HTMLSerializer(object):

    # attribute quoting options
    quote_attr_values = False
    quote_char = '"'
    use_best_quote_char = True

    # tag syntax options
    omit_optional_tags = True
    minimize_boolean_attributes = True
    use_trailing_solidus = False
    space_before_trailing_solidus = True

    # escaping options
    escape_lt_in_attrs = False
    escape_rcdata = False
    resolve_entities = True

    # miscellaneous options
    inject_meta_charset = True
    strip_whitespace = False
    sanitize = False

    options = ("quote_attr_values", "quote_char", "use_best_quote_char",
          "minimize_boolean_attributes", "use_trailing_solidus",
          "space_before_trailing_solidus", "omit_optional_tags",
          "strip_whitespace", "inject_meta_charset", "escape_lt_in_attrs",
          "escape_rcdata", "resolve_entities", "sanitize")

    def __init__(self, **kwargs):
        if kwargs.has_key('quote_char'):
            self.use_best_quote_char = False
        for attr in self.options:
            setattr(self, attr, kwargs.get(attr, getattr(self, attr)))
        self.errors = []
        self.strict = False

    def serialize(self, treewalker, encoding=None):
        in_cdata = False
        self.errors = []
        if encoding and self.inject_meta_charset:
            from html5lib.filters.inject_meta_charset import Filter
            treewalker = Filter(treewalker, encoding)
        # XXX: WhitespaceFilter should be used before OptionalTagFilter
        # for maximum efficiently of this latter filter
        if self.strip_whitespace:
            from html5lib.filters.whitespace import Filter
            treewalker = Filter(treewalker)
        if self.sanitize:
            from html5lib.filters.sanitizer import Filter
            treewalker = Filter(treewalker)
        if self.omit_optional_tags:
            from html5lib.filters.optionaltags import Filter
            treewalker = Filter(treewalker)
        for token in treewalker:
            type = token["type"]
            if type == "Doctype":
                doctype = u"<!DOCTYPE %s" % token["name"]
                
                if token["publicId"]:
                    doctype += u' PUBLIC "%s"' % token["publicId"]
                elif token["systemId"]:
                    doctype += u" SYSTEM"
                if token["systemId"]:                
                    if token["systemId"].find(u'"') >= 0:
                        if token["systemId"].find(u"'") >= 0:
                            self.serializeError(_("System identifer contains both single and double quote characters"))
                        quote_char = u"'"
                    else:
                        quote_char = u'"'
                    doctype += u" %s%s%s" % (quote_char, token["systemId"], quote_char)
                
                doctype += u">"
                
                if encoding:
                    yield doctype.encode(encoding)
                else:
                    yield doctype

            elif type in ("Characters", "SpaceCharacters"):
                if type == "SpaceCharacters" or in_cdata:
                    if in_cdata and token["data"].find("</") >= 0:
                        self.serializeError(_("Unexpected </ in CDATA"))
                    if encoding:
                        yield token["data"].encode(encoding, "strict")
                    else:
                        yield token["data"]
                elif encoding:
                    yield encode(escape(token["data"]), encoding)
                else:
                    yield escape(token["data"])

            elif type in ("StartTag", "EmptyTag"):
                name = token["name"]
                if name in rcdataElements and not self.escape_rcdata:
                    in_cdata = True
                elif in_cdata:
                    self.serializeError(_("Unexpected child element of a CDATA element"))
                attrs = token["data"]
                if hasattr(attrs, "items"):
                    attrs = attrs.items()
                attrs.sort()
                attributes = []
                for k,v in attrs:
                    if encoding:
                        k = k.encode(encoding, "strict")
                    attributes.append(' ')

                    attributes.append(k)
                    if not self.minimize_boolean_attributes or \
                      (k not in booleanAttributes.get(name, tuple()) \
                      and k not in booleanAttributes.get("", tuple())):
                        attributes.append("=")
                        if self.quote_attr_values or not v:
                            quote_attr = True
                        else:
                            quote_attr = reduce(lambda x,y: x or (y in v),
                                spaceCharacters + ">\"'=", False)
                        v = v.replace("&", "&amp;")
                        if self.escape_lt_in_attrs: v = v.replace("<", "&lt;")
                        if encoding:
                            v = encode(v, encoding)
                        if quote_attr:
                            quote_char = self.quote_char
                            if self.use_best_quote_char:
                                if "'" in v and '"' not in v:
                                    quote_char = '"'
                                elif '"' in v and "'" not in v:
                                    quote_char = "'"
                            if quote_char == "'":
                                v = v.replace("'", "&#39;")
                            else:
                                v = v.replace('"', "&quot;")
                            attributes.append(quote_char)
                            attributes.append(v)
                            attributes.append(quote_char)
                        else:
                            attributes.append(v)
                if name in voidElements and self.use_trailing_solidus:
                    if self.space_before_trailing_solidus:
                        attributes.append(" /")
                    else:
                        attributes.append("/")
                if encoding:
                    yield "<%s%s>" % (name.encode(encoding, "strict"), "".join(attributes))
                else:
                    yield u"<%s%s>" % (name, u"".join(attributes))

            elif type == "EndTag":
                name = token["name"]
                if name in rcdataElements:
                    in_cdata = False
                elif in_cdata:
                    self.serializeError(_("Unexpected child element of a CDATA element"))
                end_tag = u"</%s>" % name
                if encoding:
                    end_tag = end_tag.encode(encoding, "strict")
                yield end_tag

            elif type == "Comment":
                data = token["data"]
                if data.find("--") >= 0:
                    self.serializeError(_("Comment contains --"))
                comment = u"<!--%s-->" % token["data"]
                if encoding:
                    comment = comment.encode(encoding, unicode_encode_errors)
                yield comment

            elif type == "Entity":
                name = token["name"]
                key = name + ";"
                if not key in entities:
                    self.serializeError(_("Entity %s not recognized" % name))
                if self.resolve_entities and key not in xmlEntities:
                    data = entities[key]
                else:
                    data = u"&%s;" % name
                if encoding:
                    data = data.encode(encoding, unicode_encode_errors)
                yield data

            else:
                self.serializeError(token["data"])

    def render(self, treewalker, encoding=None):
        if encoding:
            return "".join(list(self.serialize(treewalker, encoding)))
        else:
            return u"".join(list(self.serialize(treewalker)))

    def serializeError(self, data="XXX ERROR MESSAGE NEEDED"):
        # XXX The idea is to make data mandatory.
        self.errors.append(data)
        if self.strict:
            raise SerializeError

def SerializeError(Exception):
    """Error in serialized tree"""
    pass

########NEW FILE########
__FILENAME__ = xhtmlserializer
from htmlserializer import HTMLSerializer

class XHTMLSerializer(HTMLSerializer):
    quote_attr_values = True
    minimize_boolean_attributes = False
    use_trailing_solidus = True
    escape_lt_in_attrs = True
    omit_optional_tags = False
    escape_rcdata = True

########NEW FILE########
__FILENAME__ = tokenizer
try:
    frozenset
except NameError:
    # Import from the sets module for python 2.3
    from sets import Set as set
    from sets import ImmutableSet as frozenset
try:
    from collections import deque
except ImportError:
    from utils import deque
    
from constants import spaceCharacters
from constants import entitiesWindows1252, entities
from constants import asciiLowercase, asciiLetters, asciiUpper2Lower
from constants import digits, hexDigits, EOF
from constants import tokenTypes, tagTokenTypes
from constants import replacementCharacters

from inputstream import HTMLInputStream

# Group entities by their first character, for faster lookups
entitiesByFirstChar = {}
for e in entities:
    entitiesByFirstChar.setdefault(e[0], []).append(e)

class HTMLTokenizer:
    """ This class takes care of tokenizing HTML.

    * self.currentToken
      Holds the token that is currently being processed.

    * self.state
      Holds a reference to the method to be invoked... XXX

    * self.stream
      Points to HTMLInputStream object.
    """

    # XXX need to fix documentation

    def __init__(self, stream, encoding=None, parseMeta=True, useChardet=True,
                 lowercaseElementName=True, lowercaseAttrName=True):

        self.stream = HTMLInputStream(stream, encoding, parseMeta, useChardet)
        
        #Perform case conversions?
        self.lowercaseElementName = lowercaseElementName
        self.lowercaseAttrName = lowercaseAttrName
        
        # Setup the initial tokenizer state
        self.escapeFlag = False
        self.lastFourChars = []
        self.state = self.dataState
        self.escape = False

        # The current token being created
        self.currentToken = None

    def __iter__(self):
        """ This is where the magic happens.

        We do our usually processing through the states and when we have a token
        to return we yield the token which pauses processing until the next token
        is requested.
        """
        self.tokenQueue = deque([])
        # Start processing. When EOF is reached self.state will return False
        # instead of True and the loop will terminate.
        while self.state():
            while self.stream.errors:
                yield {"type": tokenTypes["ParseError"], "data": self.stream.errors.pop(0)}
            while self.tokenQueue:
                yield self.tokenQueue.popleft()

    def consumeNumberEntity(self, isHex):
        """This function returns either U+FFFD or the character based on the
        decimal or hexadecimal representation. It also discards ";" if present.
        If not present self.tokenQueue.append({"type": tokenTypes["ParseError"]}) is invoked.
        """

        allowed = digits
        radix = 10
        if isHex:
            allowed = hexDigits
            radix = 16

        charStack = []

        # Consume all the characters that are in range while making sure we
        # don't hit an EOF.
        c = self.stream.char()
        while c in allowed and c is not EOF:
            charStack.append(c)
            c = self.stream.char()

        # Convert the set of characters consumed to an int.
        charAsInt = int("".join(charStack), radix)

        # Certain characters get replaced with others
        if charAsInt in replacementCharacters:
            char = replacementCharacters[charAsInt]
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "illegal-codepoint-for-numeric-entity",
              "datavars": {"charAsInt": charAsInt}})
        elif ((0xD800 <= charAsInt <= 0xDFFF) or 
              (charAsInt > 0x10FFFF)):
            char = u"\uFFFD"
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "illegal-codepoint-for-numeric-entity",
              "datavars": {"charAsInt": charAsInt}})
        else:
            #Should speed up this check somehow (e.g. move the set to a constant)
            if ((0x0001 <= charAsInt <= 0x0008) or 
                (0x000E <= charAsInt <= 0x001F) or 
                (0x007F  <= charAsInt <= 0x009F) or
                (0xFDD0  <= charAsInt <= 0xFDEF) or 
                charAsInt in frozenset([0x000B, 0xFFFE, 0xFFFF, 0x1FFFE, 
                                        0x1FFFF, 0x2FFFE, 0x2FFFF, 0x3FFFE,
                                        0x3FFFF, 0x4FFFE, 0x4FFFF, 0x5FFFE, 
                                        0x5FFFF, 0x6FFFE, 0x6FFFF, 0x7FFFE,
                                        0x7FFFF, 0x8FFFE, 0x8FFFF, 0x9FFFE,
                                        0x9FFFF, 0xAFFFE, 0xAFFFF, 0xBFFFE, 
                                        0xBFFFF, 0xCFFFE, 0xCFFFF, 0xDFFFE, 
                                        0xDFFFF, 0xEFFFE, 0xEFFFF, 0xFFFFE, 
                                        0xFFFFF, 0x10FFFE, 0x10FFFF])):
                self.tokenQueue.append({"type": tokenTypes["ParseError"], 
                                        "data":
                                            "illegal-codepoint-for-numeric-entity",
                                        "datavars": {"charAsInt": charAsInt}})
            try:
                # Try/except needed as UCS-2 Python builds' unichar only works
                # within the BMP.
                char = unichr(charAsInt)
            except ValueError:
                char = eval("u'\\U%08x'" % charAsInt)

        # Discard the ; if present. Otherwise, put it back on the queue and
        # invoke parseError on parser.
        if c != u";":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "numeric-entity-without-semicolon"})
            self.stream.unget(c)

        return char

    def consumeEntity(self, allowedChar=None, fromAttribute=False):
        # Initialise to the default output for when no entity is matched
        output = u"&"

        charStack = [self.stream.char()]
        if (charStack[0] in spaceCharacters or charStack[0] in (EOF, u"<", u"&") 
            or (allowedChar is not None and allowedChar == charStack[0])):
            self.stream.unget(charStack[0])

        elif charStack[0] == u"#":
            # Read the next character to see if it's hex or decimal
            hex = False
            charStack.append(self.stream.char())
            if charStack[-1] in (u"x", u"X"):
                hex = True
                charStack.append(self.stream.char())

            # charStack[-1] should be the first digit
            if (hex and charStack[-1] in hexDigits) \
             or (not hex and charStack[-1] in digits):
                # At least one digit found, so consume the whole number
                self.stream.unget(charStack[-1])
                output = self.consumeNumberEntity(hex)
            else:
                # No digits found
                self.tokenQueue.append({"type": tokenTypes["ParseError"],
                    "data": "expected-numeric-entity"})
                self.stream.unget(charStack.pop())
                output = u"&" + u"".join(charStack)

        else:
            # At this point in the process might have named entity. Entities
            # are stored in the global variable "entities".
            #
            # Consume characters and compare to these to a substring of the
            # entity names in the list until the substring no longer matches.
            filteredEntityList = entitiesByFirstChar.get(charStack[0], [])

            def entitiesStartingWith(name):
                return [e for e in filteredEntityList if e.startswith(name)]

            while charStack[-1] is not EOF and\
              entitiesStartingWith("".join(charStack)):
                charStack.append(self.stream.char())

            # At this point we have a string that starts with some characters
            # that may match an entity
            entityName = None

            # Try to find the longest entity the string will match to take care
            # of &noti for instance.
            for entityLength in xrange(len(charStack)-1, 1, -1):
                possibleEntityName = "".join(charStack[:entityLength])
                if possibleEntityName in entities:
                    entityName = possibleEntityName
                    break

            if entityName is not None:
                if entityName[-1] != ";":
                    self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
                      "named-entity-without-semicolon"})
                if entityName[-1] != ";" and fromAttribute and \
                  (charStack[entityLength] in asciiLetters
                  or charStack[entityLength] in digits):
                    self.stream.unget(charStack.pop())
                    output = u"&" + u"".join(charStack)
                else:
                    output = entities[entityName]
                    self.stream.unget(charStack.pop())
                    output += u"".join(charStack[entityLength:])
            else:
                self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
                  "expected-named-entity"})
                self.stream.unget(charStack.pop())
                output = u"&" + u"".join(charStack)

        if fromAttribute:
            self.currentToken["data"][-1][1] += output
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": output})

    def processEntityInAttribute(self, allowedChar):
        """This method replaces the need for "entityInAttributeValueState".
        """
        self.consumeEntity(allowedChar=allowedChar, fromAttribute=True)

    def emitCurrentToken(self):
        """This method is a generic handler for emitting the tags. It also sets
        the state to "data" because that's what's needed after a token has been
        emitted.
        """
        token = self.currentToken
        # Add token to the queue to be yielded
        if (token["type"] in tagTokenTypes):
            if self.lowercaseElementName:
                token["name"] = token["name"].translate(asciiUpper2Lower)
            if token["type"] == tokenTypes["EndTag"]:
                if token["data"]:
                    self.tokenQueue.append({"type":tokenTypes["ParseError"],
                                            "data":"attributes-in-end-tag"})
                if token["selfClosing"]:
                    self.tokenQueue.append({"type":tokenTypes["ParseError"],
                                            "data":"self-closing-flag-on-end-tag"})
        self.tokenQueue.append(token)
        self.state = self.dataState


    # Below are the various tokenizer states worked out.

    def dataState(self):
        data = self.stream.char()
        if data == "&":
            self.state = self.entityDataState
        elif data == "<":
            self.state = self.tagOpenState
        elif data is EOF:
            # Tokenization ends.
            return False
        elif data in spaceCharacters:
            # Directly after emitting a token you switch back to the "data
            # state". At that point spaceCharacters are important so they are
            # emitted separately.
            self.tokenQueue.append({"type": tokenTypes["SpaceCharacters"], "data":
              data + self.stream.charsUntil(spaceCharacters, True)})
            # No need to update lastFourChars here, since the first space will
            # have already been appended to lastFourChars and will have broken
            # any <!-- or --> sequences
        else:
            chars = self.stream.charsUntil((u"&", u"<"))
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": 
              data + chars})
        return True

    def entityDataState(self):
        self.consumeEntity()
        self.state = self.dataState
        return True
    
    def rcdataState(self):
        data = self.stream.char()
        if data == "&":
            self.state = self.characterReferenceInRcdata
        elif data == "<":
            self.state = self.rcdataLessThanSignState
        elif data == EOF:
            # Tokenization ends.
            return False
        elif data in spaceCharacters:
            # Directly after emitting a token you switch back to the "data
            # state". At that point spaceCharacters are important so they are
            # emitted separately.
            self.tokenQueue.append({"type": tokenTypes["SpaceCharacters"], "data":
              data + self.stream.charsUntil(spaceCharacters, True)})
            # No need to update lastFourChars here, since the first space will
            # have already been appended to lastFourChars and will have broken
            # any <!-- or --> sequences
        else:
            chars = self.stream.charsUntil((u"&", u"<"))
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": 
              data + chars})
        return True

    def characterReferenceInRcdata(self):
        self.consumeEntity()
        self.state = self.rcdataState
        return True
    
    def rawtextState(self):
        data = self.stream.char()
        if data == "<":
            self.state = self.rawtextLessThanSignState
        elif data == EOF:
            # Tokenization ends.
            return False
        else:
            chars = self.stream.charsUntil((u"<"))
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": 
              data + chars})
        return True
    
    def scriptDataState(self):
        data = self.stream.char()
        if data == "<":
            self.state = self.scriptDataLessThanSignState
        elif data == EOF:
            # Tokenization ends.
            return False
        else:
            chars = self.stream.charsUntil((u"<"))
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": 
              data + chars})
        return True
    
    def plaintextState(self):
        data = self.stream.char()
        if data == EOF:
            # Tokenization ends.
            return False
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": 
              data + self.stream.charsUntilEOF()})
            return True

    def tagOpenState(self):
        data = self.stream.char()
        if data == u"!":
            self.state = self.markupDeclarationOpenState
        elif data == u"/":
            self.state = self.closeTagOpenState
        elif data in asciiLetters:
            self.currentToken = {"type": tokenTypes["StartTag"], 
                                 "name": data, "data": [],
                                 "selfClosing": False,
                                 "selfClosingAcknowledged": False}
            self.state = self.tagNameState
        elif data == u">":
            # XXX In theory it could be something besides a tag name. But
            # do we really care?
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-tag-name-but-got-right-bracket"})
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<>"})
            self.state = self.dataState
        elif data == u"?":
            # XXX In theory it could be something besides a tag name. But
            # do we really care?
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-tag-name-but-got-question-mark"})
            self.stream.unget(data)
            self.state = self.bogusCommentState
        else:
            # XXX
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-tag-name"})
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<"})
            self.stream.unget(data)
            self.state = self.dataState
        return True

    def closeTagOpenState(self):
        data = self.stream.char()
        if data in asciiLetters:
            self.currentToken = {"type": tokenTypes["EndTag"], "name": data,
                                 "data": [], "selfClosing":False}
            self.state = self.tagNameState
        elif data == u">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-closing-tag-but-got-right-bracket"})
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-closing-tag-but-got-eof"})
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"</"})
            self.state = self.dataState
        else:
            # XXX data can be _'_...
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-closing-tag-but-got-char",
              "datavars": {"data": data}})
            self.stream.unget(data)
            self.state = self.bogusCommentState
        return True

    def tagNameState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.state = self.beforeAttributeNameState
        elif data == u">":
            self.emitCurrentToken()
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-tag-name"})
            self.state = self.dataState
        elif data == u"/":
            self.state = self.selfClosingStartTagState
        else:
            self.currentToken["name"] += data
            # (Don't use charsUntil here, because tag names are
            # very short and it's faster to not do anything fancy)
        return True
    
    def rcdataLessThanSignState(self):
        data = self.stream.char()
        if data == "/":
            self.temporaryBuffer = ""
            self.state = self.rcdataEndTagOpenState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<"})
            self.stream.unget(data)
            self.state = self.rcdataState
        return True
    
    def rcdataEndTagOpenState(self):
        data = self.stream.char()
        if data in asciiLetters:
            self.temporaryBuffer += data
            self.state = self.rcdataEndTagNameState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"</"})
            self.stream.unget(data)
            self.state = self.rcdataState
        return True
    
    def rcdataEndTagNameState(self):
        appropriate = self.currentToken and self.currentToken["name"].lower() == self.temporaryBuffer.lower()
        data = self.stream.char()
        if data in spaceCharacters and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.state = self.beforeAttributeNameState
        elif data == "/" and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.state = self.selfClosingStartTagState
        elif data == ">" and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.emitCurrentToken()
            self.state = self.dataState
        elif data in asciiLetters:
            self.temporaryBuffer += data
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"],
                                    "data": u"</" + self.temporaryBuffer})
            self.stream.unget(data)
            self.state = self.rcdataState
        return True
    
    def rawtextLessThanSignState(self):
        data = self.stream.char()
        if data == "/":
            self.temporaryBuffer = ""
            self.state = self.rawtextEndTagOpenState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<"})
            self.stream.unget(data)
            self.state = self.rawtextState
        return True
    
    def rawtextEndTagOpenState(self):
        data = self.stream.char()
        if data in asciiLetters:
            self.temporaryBuffer += data
            self.state = self.rawtextEndTagNameState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"</"})
            self.stream.unget(data)
            self.state = self.rawtextState
        return True
    
    def rawtextEndTagNameState(self):
        appropriate = self.currentToken and self.currentToken["name"].lower() == self.temporaryBuffer.lower()
        data = self.stream.char()
        if data in spaceCharacters and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.state = self.beforeAttributeNameState
        elif data == "/" and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.state = self.selfClosingStartTagState
        elif data == ">" and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.emitCurrentToken()
            self.state = self.dataState
        elif data in asciiLetters:
            self.temporaryBuffer += data
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"],
                                    "data": u"</" + self.temporaryBuffer})
            self.stream.unget(data)
            self.state = self.rawtextState
        return True
    
    def scriptDataLessThanSignState(self):
        data = self.stream.char()
        if data == "/":
            self.temporaryBuffer = ""
            self.state = self.scriptDataEndTagOpenState
        elif data == "!":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<!"})
            self.state = self.scriptDataEscapeStartState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<"})
            self.stream.unget(data)
            self.state = self.scriptDataState
        return True
    
    def scriptDataEndTagOpenState(self):
        data = self.stream.char()
        if data in asciiLetters:
            self.temporaryBuffer += data
            self.state = self.scriptDataEndTagNameState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"</"})
            self.stream.unget(data)
            self.state = self.scriptDataState
        return True
    
    def scriptDataEndTagNameState(self):
        appropriate = self.currentToken and self.currentToken["name"].lower() == self.temporaryBuffer.lower()
        data = self.stream.char()
        if data in spaceCharacters and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.state = self.beforeAttributeNameState
        elif data == "/" and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.state = self.selfClosingStartTagState
        elif data == ">" and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.emitCurrentToken()
            self.state = self.dataState
        elif data in asciiLetters:
            self.temporaryBuffer += data
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"],
                                    "data": u"</" + self.temporaryBuffer})
            self.stream.unget(data)
            self.state = self.scriptDataState
        return True
    
    def scriptDataEscapeStartState(self):
        data = self.stream.char()
        if data == "-":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"-"})
            self.state = self.scriptDataEscapeStartDashState
        else:
            self.stream.unget(data)
            self.state = self.scriptDataState
        return True
    
    def scriptDataEscapeStartDashState(self):
        data = self.stream.char()
        if data == "-":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"-"})
            self.state = self.scriptDataEscapedDashDashState
        else:
            self.stream.unget(data)
            self.state = self.scriptDataState
        return True
    
    def scriptDataEscapedState(self):
        data = self.stream.char()
        if data == "-":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"-"})
            self.state = self.scriptDataEscapedDashState
        elif data == "<":
            self.state = self.scriptDataEscapedLessThanSignState
        elif data == EOF:
            self.state = self.dataState
        else:
            chars = self.stream.charsUntil((u"<-"))
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": 
              data + chars})
        return True
    
    def scriptDataEscapedDashState(self):
        data = self.stream.char()
        if data == "-":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"-"})
            self.state = self.scriptDataEscapedDashDashState
        elif data == "<":
            self.state = self.scriptDataEscapedLessThanSignState
        elif data == EOF:
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": data})
            self.state = self.scriptDataEscapedState
        return True
    
    def scriptDataEscapedDashDashState(self):
        data = self.stream.char()
        if data == "-":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"-"})
        elif data == "<":
            self.state = self.scriptDataEscapedLessThanSignState
        elif data == ">":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u">"})
            self.state = self.scriptDataState
        elif data == EOF:
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": data})
            self.state = self.scriptDataEscapedState
        return True
    
    def scriptDataEscapedLessThanSignState(self):
        data = self.stream.char()
        if data == "/":
            self.temporaryBuffer = ""
            self.state = self.scriptDataEscapedEndTagOpenState
        elif data in asciiLetters:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<" + data})
            self.temporaryBuffer = data
            self.state = self.scriptDataDoubleEscapeStartState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<"})
            self.stream.unget(data)
            self.state = self.scriptDataEscapedState
        return True
    
    def scriptDataEscapedEndTagOpenState(self):
        data = self.stream.char()
        if data in asciiLetters:
            self.temporaryBuffer = data
            self.state = self.scriptDataEscapedEndTagNameState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"</"})
            self.stream.unget(data)
            self.state = self.scriptDataEscapedState
        return True
    
    def scriptDataEscapedEndTagNameState(self):
        appropriate = self.currentToken and self.currentToken["name"].lower() == self.temporaryBuffer.lower()
        data = self.stream.char()
        if data in spaceCharacters and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.state = self.beforeAttributeNameState
        elif data == "/" and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.state = self.selfClosingStartTagState
        elif data == ">" and appropriate:
            self.currentToken = {"type": tokenTypes["EndTag"],
                                 "name": self.temporaryBuffer,
                                 "data": [], "selfClosing":False}
            self.emitCurrentToken()
            self.state = self.dataState
        elif data in asciiLetters:
            self.temporaryBuffer += data
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"],
                                    "data": u"</" + self.temporaryBuffer})
            self.stream.unget(data)
            self.state = self.scriptDataEscapedState
        return True
    
    def scriptDataDoubleEscapeStartState(self):
        data = self.stream.char()
        if data in (spaceCharacters | frozenset(("/", ">"))):
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": data})
            if self.temporaryBuffer.lower() == "script":
                self.state = self.scriptDataDoubleEscapedState
            else:
                self.state = self.scriptDataEscapedState
        elif data in asciiLetters:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": data})
            self.temporaryBuffer += data
        else:
            self.stream.unget(data)
            self.state = self.scriptDataEscapedState
        return True
    
    def scriptDataDoubleEscapedState(self):
        data = self.stream.char()
        if data == "-":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"-"})
            self.state = self.scriptDataDoubleEscapedDashState
        elif data == "<":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<"})
            self.state = self.scriptDataDoubleEscapedLessThanSignState
        elif data == EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-script-in-script"})
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": data})
        return True
    
    def scriptDataDoubleEscapedDashState(self):
        data = self.stream.char()
        if data == "-":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"-"})
            self.state = self.scriptDataDoubleEscapedDashDashState
        elif data == "<":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<"})
            self.state = self.scriptDataDoubleEscapedLessThanSignState
        elif data == EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-script-in-script"})
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": data})
            self.state = self.scriptDataDoubleEscapedState
        return True
    
    def scriptDataDoubleEscapedDashState(self):
        data = self.stream.char()
        if data == "-":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"-"})
        elif data == "<":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"<"})
            self.state = self.scriptDataDoubleEscapedLessThanSignState
        elif data == ">":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u">"})
            self.state = self.scriptDataState
        elif data == EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-script-in-script"})
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": data})
            self.state = self.scriptDataDoubleEscapedState
        return True
    
    def scriptDataDoubleEscapedLessThanSignState(self):
        data = self.stream.char()
        if data == "/":
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": u"/"})
            self.temporaryBuffer = ""
            self.state = self.scriptDataDoubleEscapeEndState
        else:
            self.stream.unget(data)
            self.state = self.scriptDataDoubleEscapedState
        return True
    
    def scriptDataDoubleEscapeEndState(self):
        data = self.stream.char()
        if data in (spaceCharacters | frozenset(("/", ">"))):
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": data})
            if self.temporaryBuffer.lower() == "script":
                self.state = self.scriptDataEscapedState
            else:
                self.state = self.scriptDataDoubleEscapedState
        elif data in asciiLetters:
            self.tokenQueue.append({"type": tokenTypes["Characters"], "data": data})
            self.temporaryBuffer += data
        else:
            self.stream.unget(data)
            self.state = self.scriptDataDoubleEscapedState
        return True

    def beforeAttributeNameState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.stream.charsUntil(spaceCharacters, True)
        elif data in asciiLetters:
            self.currentToken["data"].append([data, ""])
            self.state = self.attributeNameState
        elif data == u">":
            self.emitCurrentToken()
        elif data == u"/":
            self.state = self.selfClosingStartTagState
        elif data in (u"'", u'"', u"=", u"<"):
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "invalid-character-in-attribute-name"})
            self.currentToken["data"].append([data, ""])
            self.state = self.attributeNameState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-attribute-name-but-got-eof"})
            self.state = self.dataState
        else:
            self.currentToken["data"].append([data, ""])
            self.state = self.attributeNameState
        return True

    def attributeNameState(self):
        data = self.stream.char()
        leavingThisState = True
        emitToken = False
        if data == u"=":
            self.state = self.beforeAttributeValueState
        elif data in asciiLetters:
            self.currentToken["data"][-1][0] += data +\
              self.stream.charsUntil(asciiLetters, True)
            leavingThisState = False
        elif data == u">":
            # XXX If we emit here the attributes are converted to a dict
            # without being checked and when the code below runs we error
            # because data is a dict not a list
            emitToken = True
        elif data in spaceCharacters:
            self.state = self.afterAttributeNameState
        elif data == u"/":
            self.state = self.selfClosingStartTagState
        elif data in (u"'", u'"', u"<"):
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "invalid-character-in-attribute-name"})
            self.currentToken["data"][-1][0] += data
            leavingThisState = False
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-attribute-name"})
            self.state = self.dataState
            emitToken = True
        else:
            self.currentToken["data"][-1][0] += data
            leavingThisState = False

        if leavingThisState:
            # Attributes are not dropped at this stage. That happens when the
            # start tag token is emitted so values can still be safely appended
            # to attributes, but we do want to report the parse error in time.
            if self.lowercaseAttrName:
                self.currentToken["data"][-1][0] = (
                    self.currentToken["data"][-1][0].translate(asciiUpper2Lower))
            for name, value in self.currentToken["data"][:-1]:
                if self.currentToken["data"][-1][0] == name:
                    self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
                      "duplicate-attribute"})
                    break
            # XXX Fix for above XXX
            if emitToken:
                self.emitCurrentToken()
        return True

    def afterAttributeNameState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.stream.charsUntil(spaceCharacters, True)
        elif data == u"=":
            self.state = self.beforeAttributeValueState
        elif data == u">":
            self.emitCurrentToken()
        elif data in asciiLetters:
            self.currentToken["data"].append([data, ""])
            self.state = self.attributeNameState
        elif data == u"/":
            self.state = self.selfClosingStartTagState
        elif data in (u"'", u'"', u"<"):
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "invalid-character-after-attribute-name"})
            self.currentToken["data"].append([data, ""])
            self.state = self.attributeNameState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-end-of-tag-but-got-eof"})
            self.emitCurrentToken()
        else:
            self.currentToken["data"].append([data, ""])
            self.state = self.attributeNameState
        return True

    def beforeAttributeValueState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.stream.charsUntil(spaceCharacters, True)
        elif data == u"\"":
            self.state = self.attributeValueDoubleQuotedState
        elif data == u"&":
            self.state = self.attributeValueUnQuotedState
            self.stream.unget(data);
        elif data == u"'":
            self.state = self.attributeValueSingleQuotedState
        elif data == u">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-attribute-value-but-got-right-bracket"})
            self.emitCurrentToken()
        elif data in (u"=", u"<", u"`"):
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "equals-in-unquoted-attribute-value"})
            self.currentToken["data"][-1][1] += data
            self.state = self.attributeValueUnQuotedState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-attribute-value-but-got-eof"})
            self.emitCurrentToken()
        else:
            self.currentToken["data"][-1][1] += data
            self.state = self.attributeValueUnQuotedState
        return True

    def attributeValueDoubleQuotedState(self):
        data = self.stream.char()
        if data == "\"":
            self.state = self.afterAttributeValueState
        elif data == u"&":
            self.processEntityInAttribute(u'"')
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-attribute-value-double-quote"})
            self.emitCurrentToken()
        else:
            self.currentToken["data"][-1][1] += data +\
              self.stream.charsUntil(("\"", u"&"))
        return True

    def attributeValueSingleQuotedState(self):
        data = self.stream.char()
        if data == "'":
            self.state = self.afterAttributeValueState
        elif data == u"&":
            self.processEntityInAttribute(u"'")
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-attribute-value-single-quote"})
            self.emitCurrentToken()
        else:
            self.currentToken["data"][-1][1] += data +\
              self.stream.charsUntil(("'", u"&"))
        return True

    def attributeValueUnQuotedState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.state = self.beforeAttributeNameState
        elif data == u"&":
            self.processEntityInAttribute(">")
        elif data == u">":
            self.emitCurrentToken()
        elif data in (u'"', u"'", u"=", u"<", u"`"):
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-character-in-unquoted-attribute-value"})
            self.currentToken["data"][-1][1] += data
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-attribute-value-no-quotes"})
            self.emitCurrentToken()
        else:
            self.currentToken["data"][-1][1] += data + self.stream.charsUntil(
              frozenset((u"&", u">", u'"', u"'", u"=", u"<", u"`")) | spaceCharacters)
        return True

    def afterAttributeValueState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.state = self.beforeAttributeNameState
        elif data == u">":
            self.emitCurrentToken()
        elif data == u"/":
            self.state = self.selfClosingStartTagState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-EOF-after-attribute-value"})
            self.emitCurrentToken()
            self.stream.unget(data)
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-character-after-attribute-value"})
            self.stream.unget(data)
            self.state = self.beforeAttributeNameState
        return True

    def selfClosingStartTagState(self):
        data = self.stream.char()
        if data == ">":
            self.currentToken["selfClosing"] = True
            self.emitCurrentToken()
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], 
                                    "data":
                                        "unexpected-EOF-after-solidus-in-tag"})
            self.stream.unget(data)
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-character-after-soldius-in-tag"})
            self.stream.unget(data)
            self.state = self.beforeAttributeNameState
        return True

    def bogusCommentState(self):
        # Make a new comment token and give it as value all the characters
        # until the first > or EOF (charsUntil checks for EOF automatically)
        # and emit it.
        self.tokenQueue.append(
          {"type": tokenTypes["Comment"], "data": self.stream.charsUntil(u">")})

        # Eat the character directly after the bogus comment which is either a
        # ">" or an EOF.
        self.stream.char()
        self.state = self.dataState
        return True

    def bogusCommentContinuationState(self):
        # Like bogusCommentState, but the caller must create the comment token
        # and this state just adds more characters to it
        self.currentToken["data"] += self.stream.charsUntil(u">")
        self.tokenQueue.append(self.currentToken)

        # Eat the character directly after the bogus comment which is either a
        # ">" or an EOF.
        self.stream.char()
        self.state = self.dataState
        return True

    def markupDeclarationOpenState(self):
        charStack = [self.stream.char()]
        if charStack[-1] == u"-":
            charStack.append(self.stream.char())
            if charStack[-1] == u"-":
                self.currentToken = {"type": tokenTypes["Comment"], "data": u""}
                self.state = self.commentStartState
                return True
        elif charStack[-1] in (u'd', u'D'):
            matched = True
            for expected in ((u'o', u'O'), (u'c', u'C'), (u't', u'T'),
                             (u'y', u'Y'), (u'p', u'P'), (u'e', u'E')):
                charStack.append(self.stream.char())
                if charStack[-1] not in expected:
                    matched = False
                    break
            if matched:
                self.currentToken = {"type": tokenTypes["Doctype"],
                                     "name": u"",
                                     "publicId": None, "systemId": None, 
                                     "correct": True}
                self.state = self.doctypeState
                return True

        self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
          "expected-dashes-or-doctype"})
        # charStack[:-2] consists of 'safe' characters ('-', 'd', 'o', etc)
        # so they can be copied directly into the bogus comment data, and only
        # the last character might be '>' or EOF and needs to be ungetted
        self.stream.unget(charStack.pop())
        self.currentToken = {"type": tokenTypes["Comment"], 
                             "data": u"".join(charStack)}
        self.state = self.bogusCommentContinuationState
        return True

    def commentStartState(self):
        data = self.stream.char()
        if data == "-":
            self.state = self.commentStartDashState
        elif data == ">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "incorrect-comment"})
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-comment"})
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["data"] += data + self.stream.charsUntil(u"-")
            self.state = self.commentState
        return True
    
    def commentStartDashState(self):
        data = self.stream.char()
        if data == "-":
            self.state = self.commentEndState
        elif data == ">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "incorrect-comment"})
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-comment"})
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["data"] += "-" + data + self.stream.charsUntil(u"-")
            self.state = self.commentState
        return True

    
    def commentState(self):
        data = self.stream.char()
        if data == u"-":
            self.state = self.commentEndDashState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-comment"})
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["data"] += data + self.stream.charsUntil(u"-")
        return True

    def commentEndDashState(self):
        data = self.stream.char()
        if data == u"-":
            self.state = self.commentEndState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-comment-end-dash"})
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["data"] += u"-" + data +\
              self.stream.charsUntil(u"-")
            # Consume the next character which is either a "-" or an EOF as
            # well so if there's a "-" directly after the "-" we go nicely to
            # the "comment end state" without emitting a ParseError() there.
            self.stream.char()
        return True

    def commentEndState(self):
        data = self.stream.char()
        if data == u">":
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data == u"-":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
             "unexpected-dash-after-double-dash-in-comment"})
            self.currentToken["data"] += data
        elif data in spaceCharacters:
            self.currentToken["data"] += "--" + data
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-space-after-double-dash-in-comment"})
            self.state = self.commentEndSpaceState
        elif data == "!":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-bang-after-double-dash-in-comment"})
            self.state = self.commentEndBangState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-comment-double-dash"})
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            # XXX
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-comment"})
            self.currentToken["data"] += u"--" + data
            self.state = self.commentState
        return True

    def commentEndBangState(self):
        data = self.stream.char()
        if data == u">":
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data == u"-":
            self.currentToken["data"] += "--!"
            self.state = self.commentEndDashState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-comment-end-bang-state"})
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["data"] += u"--!" + data
            self.state = self.commentState
        return True

    def commentEndSpaceState(self):
        data = self.stream.char()
        if data == u">":
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data == u"-":
            self.state = self.commentEndDashState
        elif data in spaceCharacters:
            self.currentToken["data"] += data
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-comment-end-space-state"})
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["data"] += data
            self.state = self.commentState
        return True

    def doctypeState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.state = self.beforeDoctypeNameState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-doctype-name-but-got-eof"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "need-space-after-doctype"})
            self.stream.unget(data)
            self.state = self.beforeDoctypeNameState
        return True

    def beforeDoctypeNameState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            pass
        elif data == u">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-doctype-name-but-got-right-bracket"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "expected-doctype-name-but-got-eof"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["name"] = data
            self.state = self.doctypeNameState
        return True

    def doctypeNameState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.currentToken["name"] = self.currentToken["name"].translate(asciiUpper2Lower)
            self.state = self.afterDoctypeNameState
        elif data == u">":
            self.currentToken["name"] = self.currentToken["name"].translate(asciiUpper2Lower)
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype-name"})
            self.currentToken["correct"] = False
            self.currentToken["name"] = self.currentToken["name"].translate(asciiUpper2Lower)
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["name"] += data
        return True

    def afterDoctypeNameState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            pass
        elif data == u">":
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.currentToken["correct"] = False
            self.stream.unget(data)
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            if data in (u"p", u"P"):
                matched = True
                for expected in ((u"u", u"U"), (u"b", u"B"), (u"l", u"L"),
                                 (u"i", u"I"), (u"c", u"C")):
                    data = self.stream.char()
                    if data not in expected:
                        matched = False
                        break
                if matched:
                    self.state = self.afterDoctypePublicKeywordState
                    return True
            elif data in (u"s", u"S"):
                matched = True
                for expected in ((u"y", u"Y"), (u"s", u"S"), (u"t", u"T"),
                                 (u"e", u"E"), (u"m", u"M")):
                    data = self.stream.char()
                    if data not in expected:
                        matched = False
                        break
                if matched:
                    self.state = self.afterDoctypeSystemKeywordState
                    return True

            # All the characters read before the current 'data' will be
            # [a-zA-Z], so they're garbage in the bogus doctype and can be
            # discarded; only the latest character might be '>' or EOF
            # and needs to be ungetted
            self.stream.unget(data)
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
                "expected-space-or-right-bracket-in-doctype", "datavars":
                {"data": data}})
            self.currentToken["correct"] = False
            self.state = self.bogusDoctypeState

        return True
    
    def afterDoctypePublicKeywordState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.state = self.beforeDoctypePublicIdentifierState
        elif data in ("'", '"'):
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-doctype"})
            self.stream.unget(data)
            self.state = self.beforeDoctypePublicIdentifierState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.stream.unget(data)
            self.state = self.beforeDoctypePublicIdentifierState
        return True

    def beforeDoctypePublicIdentifierState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            pass
        elif data == "\"":
            self.currentToken["publicId"] = u""
            self.state = self.doctypePublicIdentifierDoubleQuotedState
        elif data == "'":
            self.currentToken["publicId"] = u""
            self.state = self.doctypePublicIdentifierSingleQuotedState
        elif data == ">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-end-of-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-doctype"})
            self.currentToken["correct"] = False
            self.state = self.bogusDoctypeState
        return True

    def doctypePublicIdentifierDoubleQuotedState(self):
        data = self.stream.char()
        if data == "\"":
            self.state = self.afterDoctypePublicIdentifierState
        elif data == ">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-end-of-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["publicId"] += data
        return True

    def doctypePublicIdentifierSingleQuotedState(self):
        data = self.stream.char()
        if data == "'":
            self.state = self.afterDoctypePublicIdentifierState
        elif data == ">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-end-of-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["publicId"] += data
        return True

    def afterDoctypePublicIdentifierState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.state = self.betweenDoctypePublicAndSystemIdentifiersState
        elif data == ">":
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data == '"':
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-doctype"})
            self.currentToken["systemId"] = u""
            self.state = self.doctypeSystemIdentifierDoubleQuotedState
        elif data == "'":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-doctype"})
            self.currentToken["systemId"] = u""
            self.state = self.doctypeSystemIdentifierSingleQuotedState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-doctype"})
            self.currentToken["correct"] = False
            self.state = self.bogusDoctypeState
        return True
    
    def betweenDoctypePublicAndSystemIdentifiersState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            pass
        elif data == ">":
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data == '"':
            self.currentToken["systemId"] = u""
            self.state = self.doctypeSystemIdentifierDoubleQuotedState
        elif data == "'":
            self.currentToken["systemId"] = u""
            self.state = self.doctypeSystemIdentifierSingleQuotedState
        elif data == EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-doctype"})
            self.currentToken["correct"] = False
            self.state = self.bogusDoctypeState
        return True
    
    def afterDoctypeSystemKeywordState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            self.state = self.beforeDoctypeSystemIdentifierState
        elif data in ("'", '"'):
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-doctype"})
            self.stream.unget(data)
            self.state = self.beforeDoctypeSystemIdentifierState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.stream.unget(data)
            self.state = self.beforeDoctypeSystemIdentifierState
        return True
    
    def beforeDoctypeSystemIdentifierState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            pass
        elif data == "\"":
            self.currentToken["systemId"] = u""
            self.state = self.doctypeSystemIdentifierDoubleQuotedState
        elif data == "'":
            self.currentToken["systemId"] = u""
            self.state = self.doctypeSystemIdentifierSingleQuotedState
        elif data == ">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-doctype"})
            self.currentToken["correct"] = False
            self.state = self.bogusDoctypeState
        return True

    def doctypeSystemIdentifierDoubleQuotedState(self):
        data = self.stream.char()
        if data == "\"":
            self.state = self.afterDoctypeSystemIdentifierState
        elif data == ">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-end-of-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["systemId"] += data
        return True

    def doctypeSystemIdentifierSingleQuotedState(self):
        data = self.stream.char()
        if data == "'":
            self.state = self.afterDoctypeSystemIdentifierState
        elif data == ">":
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-end-of-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.currentToken["systemId"] += data
        return True

    def afterDoctypeSystemIdentifierState(self):
        data = self.stream.char()
        if data in spaceCharacters:
            pass
        elif data == ">":
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "eof-in-doctype"})
            self.currentToken["correct"] = False
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            self.tokenQueue.append({"type": tokenTypes["ParseError"], "data":
              "unexpected-char-in-doctype"})
            self.state = self.bogusDoctypeState
        return True

    def bogusDoctypeState(self):
        data = self.stream.char()
        if data == u">":
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        elif data is EOF:
            # XXX EMIT
            self.stream.unget(data)
            self.tokenQueue.append(self.currentToken)
            self.state = self.dataState
        else:
            pass
        return True

########NEW FILE########
__FILENAME__ = dom

from xml.dom import minidom, Node, XML_NAMESPACE, XMLNS_NAMESPACE
import new
import re
import weakref

import _base
from html5lib import constants, ihatexml
from html5lib.constants import namespaces

moduleCache = {}

def getDomModule(DomImplementation):
    name = "_" + DomImplementation.__name__+"builder"
    if name in moduleCache:
        return moduleCache[name]
    else:
        mod = new.module(name)
        objs = getDomBuilder(DomImplementation)
        mod.__dict__.update(objs)
        moduleCache[name] = mod    
        return mod

def getDomBuilder(DomImplementation):
    Dom = DomImplementation
    class AttrList:
        def __init__(self, element):
            self.element = element
        def __iter__(self):
            return self.element.attributes.items().__iter__()
        def __setitem__(self, name, value):
            self.element.setAttribute(name, value)
        def items(self):
            return [(item[0], item[1]) for item in
                     self.element.attributes.items()]
        def keys(self):
            return self.element.attributes.keys()
        def __getitem__(self, name):
            return self.element.getAttribute(name)

        def __contains__(self, name):
            if isinstance(name, tuple):
                raise NotImplementedError
            else:
                return self.element.hasAttribute(name)
    
    class NodeBuilder(_base.Node):
        def __init__(self, element):
            _base.Node.__init__(self, element.nodeName)
            self.element = element

        namespace = property(lambda self:hasattr(self.element, "namespaceURI")
                             and self.element.namespaceURI or None)

        def appendChild(self, node):
            node.parent = self
            self.element.appendChild(node.element)
    
        def insertText(self, data, insertBefore=None):
            text = self.element.ownerDocument.createTextNode(data)
            if insertBefore:
                self.element.insertBefore(text, insertBefore.element)
            else:
                self.element.appendChild(text)
    
        def insertBefore(self, node, refNode):
            self.element.insertBefore(node.element, refNode.element)
            node.parent = self
    
        def removeChild(self, node):
            if node.element.parentNode == self.element:
                self.element.removeChild(node.element)
            node.parent = None
    
        def reparentChildren(self, newParent):
            while self.element.hasChildNodes():
                child = self.element.firstChild
                self.element.removeChild(child)
                newParent.element.appendChild(child)
            self.childNodes = []
    
        def getAttributes(self):
            return AttrList(self.element)
    
        def setAttributes(self, attributes):
            if attributes:
                for name, value in attributes.items():
                    if isinstance(name, tuple):
                        if name[0] is not None:
                            qualifiedName = (name[0] + ":" + name[1])
                        else:
                            qualifiedName = name[1]
                        self.element.setAttributeNS(name[2], qualifiedName, 
                                                    value)
                    else:
                        self.element.setAttribute(
                            name, value)
        attributes = property(getAttributes, setAttributes)
    
        def cloneNode(self):
            return NodeBuilder(self.element.cloneNode(False))
    
        def hasContent(self):
            return self.element.hasChildNodes()

        def getNameTuple(self):
            if self.namespace == None:
                return namespaces["html"], self.name
            else:
                return self.namespace, self.name

        nameTuple = property(getNameTuple)

    class TreeBuilder(_base.TreeBuilder):
        def documentClass(self):
            self.dom = Dom.getDOMImplementation().createDocument(None,None,None)
            return weakref.proxy(self)
    
        def insertDoctype(self, token):
            name = token["name"]
            publicId = token["publicId"]
            systemId = token["systemId"]

            domimpl = Dom.getDOMImplementation()
            doctype = domimpl.createDocumentType(name, publicId, systemId)
            self.document.appendChild(NodeBuilder(doctype))
            if Dom == minidom:
                doctype.ownerDocument = self.dom
    
        def elementClass(self, name, namespace=None):
            if namespace is None and self.defaultNamespace is None:
                node = self.dom.createElement(name)
            else:
                node = self.dom.createElementNS(namespace, name)

            return NodeBuilder(node)
            
        def commentClass(self, data):
            return NodeBuilder(self.dom.createComment(data))
        
        def fragmentClass(self):
            return NodeBuilder(self.dom.createDocumentFragment())
    
        def appendChild(self, node):
            self.dom.appendChild(node.element)
    
        def testSerializer(self, element):
            return testSerializer(element)
    
        def getDocument(self):
            return self.dom
        
        def getFragment(self):
            return _base.TreeBuilder.getFragment(self).element
    
        def insertText(self, data, parent=None):
            data=data
            if parent <> self:
                _base.TreeBuilder.insertText(self, data, parent)
            else:
                # HACK: allow text nodes as children of the document node
                if hasattr(self.dom, '_child_node_types'):
                    if not Node.TEXT_NODE in self.dom._child_node_types:
                        self.dom._child_node_types=list(self.dom._child_node_types)
                        self.dom._child_node_types.append(Node.TEXT_NODE)
                self.dom.appendChild(self.dom.createTextNode(data))
    
        name = None
    
    def testSerializer(element):
        element.normalize()
        rv = []
        def serializeElement(element, indent=0):
            if element.nodeType == Node.DOCUMENT_TYPE_NODE:
                if element.name:
                    if element.publicId or element.systemId:
                        publicId = element.publicId or ""
                        systemId = element.systemId or ""
                        rv.append( """|%s<!DOCTYPE %s "%s" "%s">"""%(
                                ' '*indent, element.name, publicId, systemId))
                    else:
                        rv.append("|%s<!DOCTYPE %s>"%(' '*indent, element.name))
                else:
                    rv.append("|%s<!DOCTYPE >"%(' '*indent,))
            elif element.nodeType == Node.DOCUMENT_NODE:
                rv.append("#document")
            elif element.nodeType == Node.DOCUMENT_FRAGMENT_NODE:
                rv.append("#document-fragment")
            elif element.nodeType == Node.COMMENT_NODE:
                rv.append("|%s<!-- %s -->"%(' '*indent, element.nodeValue))
            elif element.nodeType == Node.TEXT_NODE:
                rv.append("|%s\"%s\"" %(' '*indent, element.nodeValue))
            else:
                if (hasattr(element, "namespaceURI") and
                    element.namespaceURI != None):
                    name = "%s %s"%(constants.prefixes[element.namespaceURI],
                                    element.nodeName)
                else:
                    name = element.nodeName
                rv.append("|%s<%s>"%(' '*indent, name))
                if element.hasAttributes():
                    i = 0
                    attr = element.attributes.item(i)
                    while attr:
                        name = attr.nodeName
                        value = attr.value
                        ns = attr.namespaceURI
                        if ns:
                            name = "%s %s"%(constants.prefixes[ns], attr.localName)
                        else:
                            name = attr.nodeName
                        i += 1
                        attr = element.attributes.item(i)

                        rv.append('|%s%s="%s"' % (' '*(indent+2), name, value))
            indent += 2
            for child in element.childNodes:
                serializeElement(child, indent)
        serializeElement(element, 0)
    
        return "\n".join(rv)
    
    def dom2sax(node, handler, nsmap={'xml':XML_NAMESPACE}):
      if node.nodeType == Node.ELEMENT_NODE:
        if not nsmap:
          handler.startElement(node.nodeName, node.attributes)
          for child in node.childNodes: dom2sax(child, handler, nsmap)
          handler.endElement(node.nodeName)
        else:
          attributes = dict(node.attributes.itemsNS()) 
    
          # gather namespace declarations
          prefixes = []
          for attrname in node.attributes.keys():
            attr = node.getAttributeNode(attrname)
            if (attr.namespaceURI == XMLNS_NAMESPACE or
               (attr.namespaceURI == None and attr.nodeName.startswith('xmlns'))):
              prefix = (attr.nodeName != 'xmlns' and attr.nodeName or None)
              handler.startPrefixMapping(prefix, attr.nodeValue)
              prefixes.append(prefix)
              nsmap = nsmap.copy()
              nsmap[prefix] = attr.nodeValue
              del attributes[(attr.namespaceURI, attr.nodeName)]
    
          # apply namespace declarations
          for attrname in node.attributes.keys():
            attr = node.getAttributeNode(attrname)
            if attr.namespaceURI == None and ':' in attr.nodeName:
              prefix = attr.nodeName.split(':')[0]
              if nsmap.has_key(prefix):
                del attributes[(attr.namespaceURI, attr.nodeName)]
                attributes[(nsmap[prefix],attr.nodeName)]=attr.nodeValue
    
          # SAX events
          ns = node.namespaceURI or nsmap.get(None,None)
          handler.startElementNS((ns,node.nodeName), node.nodeName, attributes)
          for child in node.childNodes: dom2sax(child, handler, nsmap)
          handler.endElementNS((ns, node.nodeName), node.nodeName)
          for prefix in prefixes: handler.endPrefixMapping(prefix)
    
      elif node.nodeType in [Node.TEXT_NODE, Node.CDATA_SECTION_NODE]:
        handler.characters(node.nodeValue)
    
      elif node.nodeType == Node.DOCUMENT_NODE:
        handler.startDocument()
        for child in node.childNodes: dom2sax(child, handler, nsmap)
        handler.endDocument()
    
      elif node.nodeType == Node.DOCUMENT_FRAGMENT_NODE:
        for child in node.childNodes: dom2sax(child, handler, nsmap)
    
      else:
        # ATTRIBUTE_NODE
        # ENTITY_NODE
        # PROCESSING_INSTRUCTION_NODE
        # COMMENT_NODE
        # DOCUMENT_TYPE_NODE
        # NOTATION_NODE
        pass
        
    return locals()

# Keep backwards compatibility with things that directly load 
# classes/functions from this module
for key, value in getDomModule(minidom).__dict__.items():
	globals()[key] = value

########NEW FILE########
__FILENAME__ = etree
import new
import re

import _base
from html5lib import ihatexml
from html5lib import constants
from html5lib.constants import namespaces

tag_regexp = re.compile("{([^}]*)}(.*)")

moduleCache = {}

def getETreeModule(ElementTreeImplementation, fullTree=False):
    name = "_" + ElementTreeImplementation.__name__+"builder"
    if name in moduleCache:
        return moduleCache[name]
    else:
        mod = new.module("_" + ElementTreeImplementation.__name__+"builder")
        objs = getETreeBuilder(ElementTreeImplementation, fullTree)
        mod.__dict__.update(objs)
        moduleCache[name] = mod    
        return mod

def getETreeBuilder(ElementTreeImplementation, fullTree=False):
    ElementTree = ElementTreeImplementation
    class Element(_base.Node):
        def __init__(self, name, namespace=None):
            self._name = name
            self._namespace = namespace
            self._element = ElementTree.Element(self._getETreeTag(name,
                                                                  namespace))
            if namespace is None:
                self.nameTuple = namespaces["html"], self._name
            else:
                self.nameTuple = self._namespace, self._name
            self.parent = None
            self._childNodes = []
            self._flags = []

        def _getETreeTag(self, name, namespace):
            if namespace is None:
                etree_tag = name
            else:
                etree_tag = "{%s}%s"%(namespace, name)
            return etree_tag
    
        def _setName(self, name):
            self._name = name
            self._element.tag = self._getETreeTag(self._name, self._namespace)
        
        def _getName(self):
            return self._name
        
        name = property(_getName, _setName)

        def _setNamespace(self, namespace):
            self._namespace = namespace
            self._element.tag = self._getETreeTag(self._name, self._namespace)

        def _getNamespace(self):
            return self._namespace

        namespace = property(_getNamespace, _setNamespace)
    
        def _getAttributes(self):
            return self._element.attrib
    
        def _setAttributes(self, attributes):
            #Delete existing attributes first
            #XXX - there may be a better way to do this...
            for key in self._element.attrib.keys():
                del self._element.attrib[key]
            for key, value in attributes.iteritems():
                if isinstance(key, tuple):
                    name = "{%s}%s"%(key[2], key[1])
                else:
                    name = key
                self._element.set(name, value)
    
        attributes = property(_getAttributes, _setAttributes)
    
        def _getChildNodes(self):
            return self._childNodes    
        def _setChildNodes(self, value):
            del self._element[:]
            self._childNodes = []
            for element in value:
                self.insertChild(element)
    
        childNodes = property(_getChildNodes, _setChildNodes)
    
        def hasContent(self):
            """Return true if the node has children or text"""
            return bool(self._element.text or self._element.getchildren())
    
        def appendChild(self, node):
            self._childNodes.append(node)
            self._element.append(node._element)
            node.parent = self
    
        def insertBefore(self, node, refNode):
            index = self._element.getchildren().index(refNode._element)
            self._element.insert(index, node._element)
            node.parent = self
    
        def removeChild(self, node):
            self._element.remove(node._element)
            node.parent=None
    
        def insertText(self, data, insertBefore=None):
            if not(len(self._element)):
                if not self._element.text:
                    self._element.text = ""
                self._element.text += data
            elif insertBefore is None:
                #Insert the text as the tail of the last child element
                if not self._element[-1].tail:
                    self._element[-1].tail = ""
                self._element[-1].tail += data
            else:
                #Insert the text before the specified node
                children = self._element.getchildren()
                index = children.index(insertBefore._element)
                if index > 0:
                    if not self._element[index-1].tail:
                        self._element[index-1].tail = ""
                    self._element[index-1].tail += data
                else:
                    if not self._element.text:
                        self._element.text = ""
                    self._element.text += data
    
        def cloneNode(self):
            element = Element(self.name, self.namespace)
            for name, value in self.attributes.iteritems():
                element.attributes[name] = value
            return element
    
        def reparentChildren(self, newParent):
            if newParent.childNodes:
                newParent.childNodes[-1]._element.tail += self._element.text
            else:
                if not newParent._element.text:
                    newParent._element.text = ""
                if self._element.text is not None:
                    newParent._element.text += self._element.text
            self._element.text = ""
            _base.Node.reparentChildren(self, newParent)
    
    class Comment(Element):
        def __init__(self, data):
            #Use the superclass constructor to set all properties on the 
            #wrapper element
            self._element = ElementTree.Comment(data)
            self.parent = None
            self._childNodes = []
            self._flags = []
            
        def _getData(self):
            return self._element.text
    
        def _setData(self, value):
            self._element.text = value
    
        data = property(_getData, _setData)
    
    class DocumentType(Element):
        def __init__(self, name, publicId, systemId):
            Element.__init__(self, "<!DOCTYPE>") 
            self._element.text = name
            self.publicId = publicId
            self.systemId = systemId

        def _getPublicId(self):
            return self._element.get(u"publicId", "")

        def _setPublicId(self, value):
            if value is not None:
                self._element.set(u"publicId", value)

        publicId = property(_getPublicId, _setPublicId)
    
        def _getSystemId(self):
            return self._element.get(u"systemId", "")

        def _setSystemId(self, value):
            if value is not None:
                self._element.set(u"systemId", value)

        systemId = property(_getSystemId, _setSystemId)
    
    class Document(Element):
        def __init__(self):
            Element.__init__(self, "<DOCUMENT_ROOT>") 
    
    class DocumentFragment(Element):
        def __init__(self):
            Element.__init__(self, "<DOCUMENT_FRAGMENT>")
    
    def testSerializer(element):
        rv = []
        finalText = None
        def serializeElement(element, indent=0):
            if not(hasattr(element, "tag")):
                element = element.getroot()
            if element.tag == "<!DOCTYPE>":
                if element.get("publicId") or element.get("systemId"):
                    publicId = element.get("publicId") or ""
                    systemId = element.get("systemId") or ""
                    rv.append( """<!DOCTYPE %s "%s" "%s">"""%(
                            element.text, publicId, systemId))
                else:     
                    rv.append("<!DOCTYPE %s>"%(element.text,))
            elif element.tag == "<DOCUMENT_ROOT>":
                rv.append("#document")
                if element.text:
                    rv.append("|%s\"%s\""%(' '*(indent+2), element.text))
                if element.tail:
                    finalText = element.tail
            elif type(element.tag) == type(ElementTree.Comment):
                rv.append("|%s<!-- %s -->"%(' '*indent, element.text))
            else:
                nsmatch = tag_regexp.match(element.tag)

                if nsmatch is None:
                    name = element.tag
                else:
                    ns, name = nsmatch.groups()
                    prefix = constants.prefixes[ns]
                    name = "%s %s"%(prefix, name)
                rv.append("|%s<%s>"%(' '*indent, name))

                if hasattr(element, "attrib"):
                    for name, value in element.attrib.iteritems():
                        nsmatch = tag_regexp.match(name)
                        if nsmatch is not None:
                            ns, name = nsmatch.groups()
                            prefix = constants.prefixes[ns]
                            name = "%s %s"%(prefix, name)
                        rv.append('|%s%s="%s"' % (' '*(indent+2), name, value))
                if element.text:
                    rv.append("|%s\"%s\"" %(' '*(indent+2), element.text))
            indent += 2
            for child in element.getchildren():
                serializeElement(child, indent)
            if element.tail:
                rv.append("|%s\"%s\"" %(' '*(indent-2), element.tail))
        serializeElement(element, 0)
    
        if finalText is not None:
            rv.append("|%s\"%s\""%(' '*2, finalText))
    
        return "\n".join(rv)
    
    def tostring(element):
        """Serialize an element and its child nodes to a string"""
        rv = []
        finalText = None
        filter = ihatexml.InfosetFilter()
        def serializeElement(element):
            if type(element) == type(ElementTree.ElementTree):
                element = element.getroot()
            
            if element.tag == "<!DOCTYPE>":
                if element.get("publicId") or element.get("systemId"):
                    publicId = element.get("publicId") or ""
                    systemId = element.get("systemId") or ""
                    rv.append( """<!DOCTYPE %s PUBLIC "%s" "%s">"""%(
                            element.text, publicId, systemId))
                else:     
                    rv.append("<!DOCTYPE %s>"%(element.text,))
            elif element.tag == "<DOCUMENT_ROOT>":
                if element.text:
                    rv.append(element.text)
                if element.tail:
                    finalText = element.tail
    
                for child in element.getchildren():
                    serializeElement(child)
    
            elif type(element.tag) == type(ElementTree.Comment):
                rv.append("<!--%s-->"%(element.text,))
            else:
                #This is assumed to be an ordinary element
                if not element.attrib:
                    rv.append("<%s>"%(filter.fromXmlName(element.tag),))
                else:
                    attr = " ".join(["%s=\"%s\""%(
                                filter.fromXmlName(name), value) 
                                     for name, value in element.attrib.iteritems()])
                    rv.append("<%s %s>"%(element.tag, attr))
                if element.text:
                    rv.append(element.text)
    
                for child in element.getchildren():
                    serializeElement(child)
    
                rv.append("</%s>"%(element.tag,))
    
            if element.tail:
                rv.append(element.tail)
    
        serializeElement(element)
    
        if finalText is not None:
            rv.append("%s\""%(' '*2, finalText))
    
        return "".join(rv)
    
    class TreeBuilder(_base.TreeBuilder):
        documentClass = Document
        doctypeClass = DocumentType
        elementClass = Element
        commentClass = Comment
        fragmentClass = DocumentFragment
    
        def testSerializer(self, element):
            return testSerializer(element)
    
        def getDocument(self):
            if fullTree:
                return self.document._element
            else:
                if self.defaultNamespace is not None:
                    return self.document._element.find(
                        "{%s}html"%self.defaultNamespace)
                else:
                    return self.document._element.find("html")
        
        def getFragment(self):
            return _base.TreeBuilder.getFragment(self)._element
        
    return locals()

########NEW FILE########
__FILENAME__ = etree_lxml
import new
import warnings
import re

import _base
from html5lib.constants import DataLossWarning
import html5lib.constants as constants
import etree as etree_builders
from html5lib import ihatexml

try:
    import lxml.etree as etree
except ImportError:
    pass

fullTree = True

"""Module for supporting the lxml.etree library. The idea here is to use as much
of the native library as possible, without using fragile hacks like custom element
names that break between releases. The downside of this is that we cannot represent
all possible trees; specifically the following are known to cause problems:

Text or comments as siblings of the root element
Docypes with no name

When any of these things occur, we emit a DataLossWarning
"""

class DocumentType(object):
    def __init__(self, name, publicId, systemId):
        self.name = name         
        self.publicId = publicId
        self.systemId = systemId

class Document(object):
    def __init__(self):
        self._elementTree = None
        self._childNodes = []

    def appendChild(self, element):
        self._elementTree.getroot().addnext(element._element)

    def _getChildNodes(self):
        return self._childNodes
    
    childNodes = property(_getChildNodes)

def testSerializer(element):
    rv = []
    finalText = None
    filter = ihatexml.InfosetFilter()
    def serializeElement(element, indent=0):
        if not hasattr(element, "tag"):
            if  hasattr(element, "getroot"):
                #Full tree case
                rv.append("#document")
                if element.docinfo.internalDTD:
                    if not (element.docinfo.public_id or 
                            element.docinfo.system_url):
                        dtd_str = "<!DOCTYPE %s>"%element.docinfo.root_name
                    else:
                        dtd_str = """<!DOCTYPE %s "%s" "%s">"""%(
                            element.docinfo.root_name, 
                            element.docinfo.public_id,
                            element.docinfo.system_url)
                    rv.append("|%s%s"%(' '*(indent+2), dtd_str))
                next_element = element.getroot()
                while next_element.getprevious() is not None:
                    next_element = next_element.getprevious()
                while next_element is not None:
                    serializeElement(next_element, indent+2)
                    next_element = next_element.getnext()
            elif isinstance(element, basestring):
                #Text in a fragment
                rv.append("|%s\"%s\""%(' '*indent, element))
            else:
                #Fragment case
                rv.append("#document-fragment")
                for next_element in element:
                    serializeElement(next_element, indent+2)
        elif type(element.tag) == type(etree.Comment):
            rv.append("|%s<!-- %s -->"%(' '*indent, element.text))
        else:
            nsmatch = etree_builders.tag_regexp.match(element.tag)
            if nsmatch is not None:
                ns = nsmatch.group(1)
                tag = nsmatch.group(2)
                prefix = constants.prefixes[ns]
                rv.append("|%s<%s %s>"%(' '*indent, prefix,
                                        filter.fromXmlName(tag)))
            else:
                rv.append("|%s<%s>"%(' '*indent,
                                     filter.fromXmlName(element.tag)))

            if hasattr(element, "attrib"):
                for name, value in element.attrib.iteritems():
                    nsmatch = etree_builders.tag_regexp.match(name)
                    if nsmatch:
                        ns = nsmatch.group(1)
                        name = nsmatch.group(2)
                        prefix = constants.prefixes[ns]
                        rv.append('|%s%s %s="%s"' % (' '*(indent+2), 
                                                  prefix,
                                                  filter.fromXmlName(name),
                                                  value))
                    else:        
                        rv.append('|%s%s="%s"' % (' '*(indent+2), 
                                                  filter.fromXmlName(name),
                                                  value))
            if element.text:
                rv.append("|%s\"%s\"" %(' '*(indent+2), element.text))
            indent += 2
            for child in element.getchildren():
                serializeElement(child, indent)
        if hasattr(element, "tail") and element.tail:
            rv.append("|%s\"%s\"" %(' '*(indent-2), element.tail))
    serializeElement(element, 0)

    if finalText is not None:
        rv.append("|%s\"%s\""%(' '*2, finalText))

    return "\n".join(rv)

def tostring(element):
    """Serialize an element and its child nodes to a string"""
    rv = []
    finalText = None
    def serializeElement(element):
        if not hasattr(element, "tag"):
            if element.docinfo.internalDTD:
                if element.docinfo.doctype:
                    dtd_str = element.docinfo.doctype
                else:
                    dtd_str = "<!DOCTYPE %s>"%element.docinfo.root_name
                rv.append(dtd_str)
            serializeElement(element.getroot())
            
        elif type(element.tag) == type(etree.Comment):
            rv.append("<!--%s-->"%(element.text,))
        
        else:
            #This is assumed to be an ordinary element
            if not element.attrib:
                rv.append("<%s>"%(element.tag,))
            else:
                attr = " ".join(["%s=\"%s\""%(name, value) 
                                 for name, value in element.attrib.iteritems()])
                rv.append("<%s %s>"%(element.tag, attr))
            if element.text:
                rv.append(element.text)

            for child in element.getchildren():
                serializeElement(child)

            rv.append("</%s>"%(element.tag,))

        if hasattr(element, "tail") and element.tail:
            rv.append(element.tail)

    serializeElement(element)

    if finalText is not None:
        rv.append("%s\""%(' '*2, finalText))

    return "".join(rv)
        

class TreeBuilder(_base.TreeBuilder):
    documentClass = Document
    doctypeClass = DocumentType
    elementClass = None
    commentClass = None
    fragmentClass = Document    

    def __init__(self, namespaceHTMLElements, fullTree = False):
        builder = etree_builders.getETreeModule(etree, fullTree=fullTree)
        filter = self.filter = ihatexml.InfosetFilter()
        self.namespaceHTMLElements = namespaceHTMLElements

        class Attributes(dict):
            def __init__(self, element, value={}):
                self._element = element
                dict.__init__(self, value)
                for key, value in self.iteritems():
                    if isinstance(key, tuple):
                        name = "{%s}%s"%(key[2], filter.coerceAttribute(key[1]))
                    else:
                        name = filter.coerceAttribute(key)
                    self._element._element.attrib[name] = value

            def __setitem__(self, key, value):
                dict.__setitem__(self, key, value)
                if isinstance(key, tuple):
                    name = "{%s}%s"%(key[2], filter.coerceAttribute(key[1]))
                else:
                    name = filter.coerceAttribute(key)
                self._element._element.attrib[name] = value

        class Element(builder.Element):
            def __init__(self, name, namespace):
                name = filter.coerceElement(name)
                builder.Element.__init__(self, name, namespace=namespace)
                self._attributes = Attributes(self)

            def _setName(self, name):
                self._name = filter.coerceElement(name)
                self._element.tag = self._getETreeTag(
                    self._name, self._namespace)
        
            def _getName(self):
                return filter.fromXmlName(self._name)
        
            name = property(_getName, _setName)

            def _getAttributes(self):
                return self._attributes

            def _setAttributes(self, attributes):
                self._attributes = Attributes(self, attributes)
    
            attributes = property(_getAttributes, _setAttributes)

            def insertText(self, data, insertBefore=None):
                data = filter.coerceCharacters(data)
                builder.Element.insertText(self, data, insertBefore)

            def appendChild(self, child):
                builder.Element.appendChild(self, child)
                

        class Comment(builder.Comment):
            def __init__(self, data):
                data = filter.coerceComment(data)
                builder.Comment.__init__(self, data)

            def _setData(self, data):
                data = filter.coerceComment(data)
                self._element.text = data

            def _getData(self):
                return self._element.text

            data = property(_getData, _setData)

        self.elementClass = Element
        self.commentClass = builder.Comment
        #self.fragmentClass = builder.DocumentFragment
        _base.TreeBuilder.__init__(self, namespaceHTMLElements)
    
    def reset(self):
        _base.TreeBuilder.reset(self)
        self.insertComment = self.insertCommentInitial
        self.initial_comments = []
        self.doctype = None

    def testSerializer(self, element):
        return testSerializer(element)

    def getDocument(self):
        if fullTree:
            return self.document._elementTree
        else:
            return self.document._elementTree.getroot()
    
    def getFragment(self):
        fragment = []
        element = self.openElements[0]._element
        if element.text:
            fragment.append(element.text)
        fragment.extend(element.getchildren())
        if element.tail:
            fragment.append(element.tail)
        return fragment

    def insertDoctype(self, token):
        name = token["name"]
        publicId = token["publicId"]
        systemId = token["systemId"]

        if not name or ihatexml.nonXmlNameBMPRegexp.search(name) or name[0] == '"':
            warnings.warn("lxml cannot represent null or non-xml doctype", DataLossWarning)

        doctype = self.doctypeClass(name, publicId, systemId)
        self.doctype = doctype
    
    def insertCommentInitial(self, data, parent=None):
        self.initial_comments.append(data)
    
    def insertRoot(self, token):
        """Create the document root"""
        #Because of the way libxml2 works, it doesn't seem to be possible to
        #alter information like the doctype after the tree has been parsed. 
        #Therefore we need to use the built-in parser to create our iniial 
        #tree, after which we can add elements like normal
        docStr = ""
        if self.doctype and self.doctype.name and not self.doctype.name.startswith('"'):
            docStr += "<!DOCTYPE %s"%self.doctype.name
            if (self.doctype.publicId is not None or 
                self.doctype.systemId is not None):
                docStr += ' PUBLIC "%s" "%s"'%(self.doctype.publicId or "",
                                               self.doctype.systemId or "")
            docStr += ">"
        docStr += "<THIS_SHOULD_NEVER_APPEAR_PUBLICLY/>"
        
        try:
            root = etree.fromstring(docStr)
        except etree.XMLSyntaxError:
            print docStr
            raise
        
        #Append the initial comments:
        for comment_token in self.initial_comments:
            root.addprevious(etree.Comment(comment_token["data"]))
        
        #Create the root document and add the ElementTree to it
        self.document = self.documentClass()
        self.document._elementTree = root.getroottree()
        
        # Give the root element the right name
        name = token["name"]
        namespace = token.get("namespace", self.defaultNamespace)
        if namespace is None:
            etree_tag = name
        else:
            etree_tag = "{%s}%s"%(namespace, name)
        root.tag = etree_tag
        
        #Add the root element to the internal child/open data structures
        root_element = self.elementClass(name, namespace)
        root_element._element = root
        self.document._childNodes.append(root_element)
        self.openElements.append(root_element)
    
        #Reset to the default insert comment function
        self.insertComment = super(TreeBuilder, self).insertComment

########NEW FILE########
__FILENAME__ = simpletree
import _base
from html5lib.constants import voidElements, namespaces, prefixes
from xml.sax.saxutils import escape

# Really crappy basic implementation of a DOM-core like thing
class Node(_base.Node):
    type = -1
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.value = None
        self.childNodes = []
        self._flags = []

    def __iter__(self):
        for node in self.childNodes:
            yield node
            for item in node:
                yield item

    def __unicode__(self):
        return self.name

    def toxml(self):
        raise NotImplementedError

    def printTree(self, indent=0):
        tree = '\n|%s%s' % (' '* indent, unicode(self))
        for child in self.childNodes:
            tree += child.printTree(indent + 2)
        return tree

    def appendChild(self, node):
        if (isinstance(node, TextNode) and self.childNodes and
          isinstance(self.childNodes[-1], TextNode)):
            self.childNodes[-1].value += node.value
        else:
            self.childNodes.append(node)
        node.parent = self

    def insertText(self, data, insertBefore=None):
        if insertBefore is None:
            self.appendChild(TextNode(data))
        else:
            self.insertBefore(TextNode(data), insertBefore)

    def insertBefore(self, node, refNode):
        index = self.childNodes.index(refNode)
        if (isinstance(node, TextNode) and index > 0 and
          isinstance(self.childNodes[index - 1], TextNode)):
            self.childNodes[index - 1].value += node.value
        else:
            self.childNodes.insert(index, node)
        node.parent = self

    def removeChild(self, node):
        try:
            self.childNodes.remove(node)
        except:
            # XXX
            raise
        node.parent = None

    def cloneNode(self):
        raise NotImplementedError

    def hasContent(self):
        """Return true if the node has children or text"""
        return bool(self.childNodes)

    def getNameTuple(self):
        if self.namespace == None:
            return namespaces["html"], self.name
        else:
            return self.namespace, self.name

    nameTuple = property(getNameTuple)

class Document(Node):
    type = 1
    def __init__(self):
        Node.__init__(self, None)

    def __unicode__(self):
        return "#document"

    def appendChild(self, child):
        Node.appendChild(self, child)

    def toxml(self, encoding="utf=8"):
        result = ""
        for child in self.childNodes:
            result += child.toxml()
        return result.encode(encoding)

    def hilite(self, encoding="utf-8"):
        result = "<pre>"
        for child in self.childNodes:
            result += child.hilite()
        return result.encode(encoding) + "</pre>"
    
    def printTree(self):
        tree = unicode(self)
        for child in self.childNodes:
            tree += child.printTree(2)
        return tree

    def cloneNode(self):
        return Document()

class DocumentFragment(Document):
    type = 2
    def __unicode__(self):
        return "#document-fragment"

    def cloneNode(self):
        return DocumentFragment()

class DocumentType(Node):
    type = 3
    def __init__(self, name, publicId, systemId):
        Node.__init__(self, name)
        self.publicId = publicId
        self.systemId = systemId

    def __unicode__(self):
        if self.publicId or self.systemId:
            publicId = self.publicId or ""
            systemId = self.systemId or ""
            return """<!DOCTYPE %s "%s" "%s">"""%(
                self.name, publicId, systemId)
                            
        else:
            return u"<!DOCTYPE %s>" % self.name
    

    toxml = __unicode__
    
    def hilite(self):
        return '<code class="markup doctype">&lt;!DOCTYPE %s></code>' % self.name

    def cloneNode(self):
        return DocumentType(self.name, self.publicId, self.systemId)

class TextNode(Node):
    type = 4
    def __init__(self, value):
        Node.__init__(self, None)
        self.value = value

    def __unicode__(self):
        return u"\"%s\"" % self.value

    def toxml(self):
        return escape(self.value)
    
    hilite = toxml

    def cloneNode(self):
        return TextNode(self.value)

class Element(Node):
    type = 5
    def __init__(self, name, namespace=None):
        Node.__init__(self, name)
        self.namespace = namespace
        self.attributes = {}

    def __unicode__(self):
        if self.namespace == None:
            return u"<%s>" % self.name
        else:
            return u"<%s %s>"%(prefixes[self.namespace], self.name)

    def toxml(self):
        result = '<' + self.name
        if self.attributes:
            for name,value in self.attributes.iteritems():
                result += u' %s="%s"' % (name, escape(value,{'"':'&quot;'}))
        if self.childNodes:
            result += '>'
            for child in self.childNodes:
                result += child.toxml()
            result += u'</%s>' % self.name
        else:
            result += u'/>'
        return result
    
    def hilite(self):
        result = '&lt;<code class="markup element-name">%s</code>' % self.name
        if self.attributes:
            for name, value in self.attributes.iteritems():
                result += ' <code class="markup attribute-name">%s</code>=<code class="markup attribute-value">"%s"</code>' % (name, escape(value, {'"':'&quot;'}))
        if self.childNodes:
            result += ">"
            for child in self.childNodes:
                result += child.hilite()
        elif self.name in voidElements:
            return result + ">"
        return result + '&lt;/<code class="markup element-name">%s</code>>' % self.name

    def printTree(self, indent):
        tree = '\n|%s%s' % (' '*indent, unicode(self))
        indent += 2
        if self.attributes:
            for name, value in self.attributes.iteritems():
                if isinstance(name, tuple):
                    name = "%s %s"%(name[0], name[1])
                tree += '\n|%s%s="%s"' % (' ' * indent, name, value)
        for child in self.childNodes:
            tree += child.printTree(indent)
        return tree

    def cloneNode(self):
        newNode = Element(self.name)
        if hasattr(self, 'namespace'):
            newNode.namespace = self.namespace
        for attr, value in self.attributes.iteritems():
            newNode.attributes[attr] = value
        return newNode

class CommentNode(Node):
    type = 6
    def __init__(self, data):
        Node.__init__(self, None)
        self.data = data

    def __unicode__(self):
        return "<!-- %s -->" % self.data
    
    def toxml(self):
        return "<!--%s-->" % self.data

    def hilite(self):
        return '<code class="markup comment">&lt;!--%s--></code>' % escape(self.data)

    def cloneNode(self):
        return CommentNode(self.data)

class TreeBuilder(_base.TreeBuilder):
    documentClass = Document
    doctypeClass = DocumentType
    elementClass = Element
    commentClass = CommentNode
    fragmentClass = DocumentFragment
    
    def testSerializer(self, node):
        return node.printTree()

########NEW FILE########
__FILENAME__ = soup
import warnings

warnings.warn("BeautifulSoup 3.x (as of 3.1) is not fully compatible with html5lib and support will be removed in the future", DeprecationWarning)

from BeautifulSoup import BeautifulSoup, Tag, NavigableString, Comment, Declaration

import _base
from html5lib.constants import namespaces, DataLossWarning

class AttrList(object):
    def __init__(self, element):
        self.element = element
        self.attrs = dict(self.element.attrs)
    def __iter__(self):
        return self.attrs.items().__iter__()
    def __setitem__(self, name, value):
        "set attr", name, value
        self.element[name] = value
    def items(self):
        return self.attrs.items()
    def keys(self):
        return self.attrs.keys()
    def __getitem__(self, name):
        return self.attrs[name]
    def __contains__(self, name):
        return name in self.attrs.keys()


class Element(_base.Node):
    def __init__(self, element, soup, namespace):
        _base.Node.__init__(self, element.name)
        self.element = element
        self.soup = soup
        self.namespace = namespace

    def _nodeIndex(self, node, refNode):
        # Finds a node by identity rather than equality
        for index in range(len(self.element.contents)):
            if id(self.element.contents[index]) == id(refNode.element):
                return index
        return None

    def appendChild(self, node):
        if (node.element.__class__ == NavigableString and self.element.contents
            and self.element.contents[-1].__class__ == NavigableString):
            # Concatenate new text onto old text node
            # (TODO: This has O(n^2) performance, for input like "a</a>a</a>a</a>...")
            newStr = NavigableString(self.element.contents[-1]+node.element)

            # Remove the old text node
            # (Can't simply use .extract() by itself, because it fails if
            # an equal text node exists within the parent node)
            oldElement = self.element.contents[-1]
            del self.element.contents[-1]
            oldElement.parent = None
            oldElement.extract()

            self.element.insert(len(self.element.contents), newStr)
        else:
            self.element.insert(len(self.element.contents), node.element)
            node.parent = self

    def getAttributes(self):
        return AttrList(self.element)

    def setAttributes(self, attributes):
        if attributes:
            for name, value in attributes.items():
                self.element[name] =  value

    attributes = property(getAttributes, setAttributes)
    
    def insertText(self, data, insertBefore=None):
        text = TextNode(NavigableString(data), self.soup)
        if insertBefore:
            self.insertBefore(text, insertBefore)
        else:
            self.appendChild(text)

    def insertBefore(self, node, refNode):
        index = self._nodeIndex(node, refNode)
        if (node.element.__class__ == NavigableString and self.element.contents
            and self.element.contents[index-1].__class__ == NavigableString):
            # (See comments in appendChild)
            newStr = NavigableString(self.element.contents[index-1]+node.element)
            oldNode = self.element.contents[index-1]
            del self.element.contents[index-1]
            oldNode.parent = None
            oldNode.extract()

            self.element.insert(index-1, newStr)
        else:
            self.element.insert(index, node.element)
            node.parent = self

    def removeChild(self, node):
        index = self._nodeIndex(node.parent, node)
        del node.parent.element.contents[index]
        node.element.parent = None
        node.element.extract()
        node.parent = None

    def reparentChildren(self, newParent):
        while self.element.contents:
            child = self.element.contents[0]
            child.extract()
            if isinstance(child, Tag):
                newParent.appendChild(Element(child, self.soup, namespaces["html"]))
            else:
                newParent.appendChild(TextNode(child, self.soup))

    def cloneNode(self):
        node = Element(Tag(self.soup, self.element.name), self.soup, self.namespace)
        for key,value in self.attributes:
            node.attributes[key] = value
        return node

    def hasContent(self):
        return self.element.contents

    def getNameTuple(self):
        if self.namespace == None:
            return namespaces["html"], self.name
        else:
            return self.namespace, self.name

    nameTuple = property(getNameTuple)

class TextNode(Element):
    def __init__(self, element, soup):
        _base.Node.__init__(self, None)
        self.element = element
        self.soup = soup
    
    def cloneNode(self):
        raise NotImplementedError

class TreeBuilder(_base.TreeBuilder):
    def __init__(self, namespaceHTMLElements):
        if namespaceHTMLElements:
            warnings.warn("BeautifulSoup cannot represent elements in any namespace", DataLossWarning)
        _base.TreeBuilder.__init__(self, namespaceHTMLElements)
        
    def documentClass(self):
        self.soup = BeautifulSoup("")
        return Element(self.soup, self.soup, None)
    
    def insertDoctype(self, token):
        name = token["name"]
        publicId = token["publicId"]
        systemId = token["systemId"]

        if publicId:
            self.soup.insert(0, Declaration("DOCTYPE %s PUBLIC \"%s\" \"%s\""%(name, publicId, systemId or "")))
        elif systemId:
            self.soup.insert(0, Declaration("DOCTYPE %s SYSTEM \"%s\""%
                                            (name, systemId)))
        else:
            self.soup.insert(0, Declaration("DOCTYPE %s"%name))
    
    def elementClass(self, name, namespace):
        if namespace is not None:
            warnings.warn("BeautifulSoup cannot represent elements in any namespace", DataLossWarning)
        return Element(Tag(self.soup, name), self.soup, namespace)
        
    def commentClass(self, data):
        return TextNode(Comment(data), self.soup)
    
    def fragmentClass(self):
        self.soup = BeautifulSoup("")
        self.soup.name = "[document_fragment]"
        return Element(self.soup, self.soup, None) 

    def appendChild(self, node):
        self.soup.insert(len(self.soup.contents), node.element)

    def testSerializer(self, element):
        return testSerializer(element)

    def getDocument(self):
        return self.soup
    
    def getFragment(self):
        return _base.TreeBuilder.getFragment(self).element
    
def testSerializer(element):
    import re
    rv = []
    def serializeElement(element, indent=0):
        if isinstance(element, Declaration):
            doctype_regexp = r'DOCTYPE\s+(?P<name>[^\s]*)( PUBLIC "(?P<publicId>.*)" "(?P<systemId1>.*)"| SYSTEM "(?P<systemId2>.*)")?'
            m = re.compile(doctype_regexp).match(element.string)
            assert m is not None, "DOCTYPE did not match expected format"
            name = m.group('name')
            publicId = m.group('publicId')
            if publicId is not None:
                systemId = m.group('systemId1') or ""
            else:
                systemId = m.group('systemId2')

            if publicId is not None or systemId is not None:
                rv.append("""|%s<!DOCTYPE %s "%s" "%s">"""%
                          (' '*indent, name, publicId or "", systemId or ""))
            else:
                rv.append("|%s<!DOCTYPE %s>"%(' '*indent, name))
            
        elif isinstance(element, BeautifulSoup):
            if element.name == "[document_fragment]":
                rv.append("#document-fragment")                
            else:
                rv.append("#document")

        elif isinstance(element, Comment):
            rv.append("|%s<!-- %s -->"%(' '*indent, element.string))
        elif isinstance(element, unicode):
            rv.append("|%s\"%s\"" %(' '*indent, element))
        else:
            rv.append("|%s<%s>"%(' '*indent, element.name))
            if element.attrs:
                for name, value in element.attrs:
                    rv.append('|%s%s="%s"' % (' '*(indent+2), name, value))
        indent += 2
        if hasattr(element, "contents"):
            for child in element.contents:
                serializeElement(child, indent)
    serializeElement(element, 0)

    return "\n".join(rv)

########NEW FILE########
__FILENAME__ = _base
from html5lib.constants import scopingElements, tableInsertModeElements, namespaces
try:
    frozenset
except NameError:
    # Import from the sets module for python 2.3
    from sets import Set as set
    from sets import ImmutableSet as frozenset

# The scope markers are inserted when entering buttons, object elements,
# marquees, table cells, and table captions, and are used to prevent formatting
# from "leaking" into tables, buttons, object elements, and marquees.
Marker = None

class Node(object):
    def __init__(self, name):
        """Node representing an item in the tree.
        name - The tag name associated with the node
        parent - The parent of the current node (or None for the document node)
        value - The value of the current node (applies to text nodes and 
        comments
        attributes - a dict holding name, value pairs for attributes of the node
        childNodes - a list of child nodes of the current node. This must 
        include all elements but not necessarily other node types
        _flags - A list of miscellaneous flags that can be set on the node
        """
        self.name = name
        self.parent = None
        self.value = None
        self.attributes = {}
        self.childNodes = []
        self._flags = []

    def __unicode__(self):
        attributesStr =  " ".join(["%s=\"%s\""%(name, value) 
                                   for name, value in 
                                   self.attributes.iteritems()])
        if attributesStr:
            return "<%s %s>"%(self.name,attributesStr)
        else:
            return "<%s>"%(self.name)

    def __repr__(self):
        return "<%s>" % (self.name)

    def appendChild(self, node):
        """Insert node as a child of the current node
        """
        raise NotImplementedError

    def insertText(self, data, insertBefore=None):
        """Insert data as text in the current node, positioned before the 
        start of node insertBefore or to the end of the node's text.
        """
        raise NotImplementedError

    def insertBefore(self, node, refNode):
        """Insert node as a child of the current node, before refNode in the 
        list of child nodes. Raises ValueError if refNode is not a child of 
        the current node"""
        raise NotImplementedError

    def removeChild(self, node):
        """Remove node from the children of the current node
        """
        raise NotImplementedError

    def reparentChildren(self, newParent):
        """Move all the children of the current node to newParent. 
        This is needed so that trees that don't store text as nodes move the 
        text in the correct way
        """
        #XXX - should this method be made more general?
        for child in self.childNodes:
            newParent.appendChild(child)
        self.childNodes = []

    def cloneNode(self):
        """Return a shallow copy of the current node i.e. a node with the same
        name and attributes but with no parent or child nodes
        """
        raise NotImplementedError


    def hasContent(self):
        """Return true if the node has children or text, false otherwise
        """
        raise NotImplementedError

class TreeBuilder(object):
    """Base treebuilder implementation
    documentClass - the class to use for the bottommost node of a document
    elementClass - the class to use for HTML Elements
    commentClass - the class to use for comments
    doctypeClass - the class to use for doctypes
    """

    #Document class
    documentClass = None

    #The class to use for creating a node
    elementClass = None

    #The class to use for creating comments
    commentClass = None

    #The class to use for creating doctypes
    doctypeClass = None
    
    #Fragment class
    fragmentClass = None

    def __init__(self, namespaceHTMLElements):
        if namespaceHTMLElements:
            self.defaultNamespace = "http://www.w3.org/1999/xhtml"
        else:
            self.defaultNamespace = None
        self.reset()
    
    def reset(self):
        self.openElements = []
        self.activeFormattingElements = []

        #XXX - rename these to headElement, formElement
        self.headPointer = None
        self.formPointer = None

        self.insertFromTable = False

        self.document = self.documentClass()

    def elementInScope(self, target, variant=None):
        # Exit early when possible.
        listElementsMap = {
            None:scopingElements,
            "list":scopingElements | set([(namespaces["html"], "ol"),
                                          (namespaces["html"], "ul")]),
            "table":set([(namespaces["html"], "html"),
                         (namespaces["html"], "table")])
            }
        listElements = listElementsMap[variant]

        for node in reversed(self.openElements):
            if node.name == target:
                return True
            elif node.nameTuple in listElements:
                return False

        assert False # We should never reach this point

    def reconstructActiveFormattingElements(self):
        # Within this algorithm the order of steps described in the
        # specification is not quite the same as the order of steps in the
        # code. It should still do the same though.

        # Step 1: stop the algorithm when there's nothing to do.
        if not self.activeFormattingElements:
            return

        # Step 2 and step 3: we start with the last element. So i is -1.
        i = len(self.activeFormattingElements) - 1
        entry = self.activeFormattingElements[i]
        if entry == Marker or entry in self.openElements:
            return

        # Step 6
        while entry != Marker and entry not in self.openElements:
            if i == 0:
                #This will be reset to 0 below
                i = -1
                break
            i -= 1
            # Step 5: let entry be one earlier in the list.
            entry = self.activeFormattingElements[i]

        while True:
            # Step 7
            i += 1

            # Step 8
            entry = self.activeFormattingElements[i]
            clone = entry.cloneNode() #Mainly to get a new copy of the attributes

            # Step 9
            element = self.insertElement({"type":"StartTag", 
                                          "name":clone.name, 
                                          "namespace":clone.namespace, 
                                          "data":clone.attributes})

            # Step 10
            self.activeFormattingElements[i] = element

            # Step 11
            if element == self.activeFormattingElements[-1]:
                break

    def clearActiveFormattingElements(self):
        entry = self.activeFormattingElements.pop()
        while self.activeFormattingElements and entry != Marker:
            entry = self.activeFormattingElements.pop()

    def elementInActiveFormattingElements(self, name):
        """Check if an element exists between the end of the active
        formatting elements and the last marker. If it does, return it, else
        return false"""

        for item in self.activeFormattingElements[::-1]:
            # Check for Marker first because if it's a Marker it doesn't have a
            # name attribute.
            if item == Marker:
                break
            elif item.name == name:
                return item
        return False

    def insertRoot(self, token):
        element = self.createElement(token)
        self.openElements.append(element)
        self.document.appendChild(element)

    def insertDoctype(self, token):
        name = token["name"]
        publicId = token["publicId"]
        systemId = token["systemId"]

        doctype = self.doctypeClass(name, publicId, systemId)
        self.document.appendChild(doctype)

    def insertComment(self, token, parent=None):
        if parent is None:
            parent = self.openElements[-1]
        parent.appendChild(self.commentClass(token["data"]))
                           
    def createElement(self, token):
        """Create an element but don't insert it anywhere"""
        name = token["name"]
        namespace = token.get("namespace", self.defaultNamespace)
        element = self.elementClass(name, namespace)
        element.attributes = token["data"]
        return element

    def _getInsertFromTable(self):
        return self._insertFromTable

    def _setInsertFromTable(self, value):
        """Switch the function used to insert an element from the
        normal one to the misnested table one and back again"""
        self._insertFromTable = value
        if value:
            self.insertElement = self.insertElementTable
        else:
            self.insertElement = self.insertElementNormal

    insertFromTable = property(_getInsertFromTable, _setInsertFromTable)
        
    def insertElementNormal(self, token):
        name = token["name"]
        namespace = token.get("namespace", self.defaultNamespace)
        element = self.elementClass(name, namespace)
        element.attributes = token["data"]
        self.openElements[-1].appendChild(element)
        self.openElements.append(element)
        return element

    def insertElementTable(self, token):
        """Create an element and insert it into the tree""" 
        element = self.createElement(token)
        if self.openElements[-1].name not in tableInsertModeElements:
            return self.insertElementNormal(token)
        else:
            #We should be in the InTable mode. This means we want to do
            #special magic element rearranging
            parent, insertBefore = self.getTableMisnestedNodePosition()
            if insertBefore is None:
                parent.appendChild(element)
            else:
                parent.insertBefore(element, insertBefore)
            self.openElements.append(element)
        return element

    def insertText(self, data, parent=None):
        """Insert text data."""
        if parent is None:
            parent = self.openElements[-1]

        if (not self.insertFromTable or (self.insertFromTable and
                                         self.openElements[-1].name 
                                         not in tableInsertModeElements)):
            parent.insertText(data)
        else:
            # We should be in the InTable mode. This means we want to do
            # special magic element rearranging
            parent, insertBefore = self.getTableMisnestedNodePosition()
            parent.insertText(data, insertBefore)
            
    def getTableMisnestedNodePosition(self):
        """Get the foster parent element, and sibling to insert before
        (or None) when inserting a misnested table node"""
        # The foster parent element is the one which comes before the most
        # recently opened table element
        # XXX - this is really inelegant
        lastTable=None
        fosterParent = None
        insertBefore = None
        for elm in self.openElements[::-1]:
            if elm.name == "table":
                lastTable = elm
                break
        if lastTable:
            # XXX - we should really check that this parent is actually a
            # node here
            if lastTable.parent:
                fosterParent = lastTable.parent
                insertBefore = lastTable
            else:
                fosterParent = self.openElements[
                    self.openElements.index(lastTable) - 1]
        else:
            fosterParent = self.openElements[0]
        return fosterParent, insertBefore

    def generateImpliedEndTags(self, exclude=None):
        name = self.openElements[-1].name
        # XXX td, th and tr are not actually needed
        if (name in frozenset(("dd", "dt", "li", "p", "td", "th", "tr"))
            and name != exclude):
            self.openElements.pop()
            # XXX This is not entirely what the specification says. We should
            # investigate it more closely.
            self.generateImpliedEndTags(exclude)

    def getDocument(self):
        "Return the final tree"
        return self.document
    
    def getFragment(self):
        "Return the final fragment"
        #assert self.innerHTML
        fragment = self.fragmentClass()
        self.openElements[0].reparentChildren(fragment)
        return fragment

    def testSerializer(self, node):
        """Serialize the subtree of node in the format required by unit tests
        node - the node from which to start serializing"""
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = dom
from xml.dom import Node

import gettext
_ = gettext.gettext

import _base
from html5lib.constants import voidElements

class TreeWalker(_base.NonRecursiveTreeWalker):
    def getNodeDetails(self, node):
        if node.nodeType == Node.DOCUMENT_TYPE_NODE:
            return _base.DOCTYPE, node.name, node.publicId, node.systemId

        elif node.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
            return _base.TEXT, node.nodeValue

        elif node.nodeType == Node.ELEMENT_NODE:
            return (_base.ELEMENT, node.namespaceURI, node.nodeName, 
                    node.attributes.items(), node.hasChildNodes)

        elif node.nodeType == Node.COMMENT_NODE:
            return _base.COMMENT, node.nodeValue

        elif node.nodeType in (Node.DOCUMENT_NODE, Node.DOCUMENT_FRAGMENT_NODE):
            return (_base.DOCUMENT,)

        else:
            return _base.UNKNOWN, node.nodeType

    def getFirstChild(self, node):
        return node.firstChild

    def getNextSibling(self, node):
        return node.nextSibling

    def getParentNode(self, node):
        return node.parentNode

########NEW FILE########
__FILENAME__ = etree
import gettext
_ = gettext.gettext

import new
import copy
import re

import _base
from html5lib.constants import voidElements

tag_regexp = re.compile("{([^}]*)}(.*)")

moduleCache = {}

def getETreeModule(ElementTreeImplementation):
    name = "_" + ElementTreeImplementation.__name__+"builder"
    if name in moduleCache:
        return moduleCache[name]
    else:
        mod = new.module("_" + ElementTreeImplementation.__name__+"builder")
        objs = getETreeBuilder(ElementTreeImplementation)
        mod.__dict__.update(objs)
        moduleCache[name] = mod
        return mod

def getETreeBuilder(ElementTreeImplementation):
    ElementTree = ElementTreeImplementation

    class TreeWalker(_base.NonRecursiveTreeWalker):
        """Given the particular ElementTree representation, this implementation,
        to avoid using recursion, returns "nodes" as tuples with the following
        content:

        1. The current element
        
        2. The index of the element relative to its parent
        
        3. A stack of ancestor elements
        
        4. A flag "text", "tail" or None to indicate if the current node is a
           text node; either the text or tail of the current element (1)
        """
        def getNodeDetails(self, node):
            if isinstance(node, tuple): # It might be the root Element
                elt, key, parents, flag = node
                if flag in ("text", "tail"):
                    return _base.TEXT, getattr(elt, flag)
                else:
                    node = elt

            if not(hasattr(node, "tag")):
                node = node.getroot()

            if node.tag in ("<DOCUMENT_ROOT>", "<DOCUMENT_FRAGMENT>"):
                return (_base.DOCUMENT,)

            elif node.tag == "<!DOCTYPE>":
                return (_base.DOCTYPE, node.text, 
                        node.get("publicId"), node.get("systemId"))

            elif type(node.tag) == type(ElementTree.Comment):
                return _base.COMMENT, node.text

            else:
                #This is assumed to be an ordinary element
                match = tag_regexp.match(node.tag)
                if match:
                    namespace, tag = match.groups()
                else:
                    namespace = None
                    tag = node.tag
                return (_base.ELEMENT, namespace, tag, 
                        node.attrib.items(), len(node) or node.text)
    
        def getFirstChild(self, node):
            if isinstance(node, tuple):
                element, key, parents, flag = node
            else:
                element, key, parents, flag = node, None, [], None
                
            if flag in ("text", "tail"):
                return None
            else:
                if element.text:
                    return element, key, parents, "text"
                elif len(element):
                    parents.append(element)
                    return element[0], 0, parents, None
                else:
                    return None
        
        def getNextSibling(self, node):
            if isinstance(node, tuple):
                element, key, parents, flag = node
            else:
                return None
                
            if flag == "text":
                if len(element):
                    parents.append(element)
                    return element[0], 0, parents, None
                else:
                    return None
            else:
                if element.tail and flag != "tail":
                    return element, key, parents, "tail"
                elif key < len(parents[-1]) - 1:
                    return parents[-1][key+1], key+1, parents, None
                else:
                    return None
        
        def getParentNode(self, node):
            if isinstance(node, tuple):
                element, key, parents, flag = node
            else:
                return None
            
            if flag == "text":
                if not parents:
                    return element
                else:
                    return element, key, parents, None
            else:
                parent = parents.pop()
                if not parents:
                    return parent
                else:
                    return parent, list(parents[-1]).index(parent), parents, None

    return locals()

########NEW FILE########
__FILENAME__ = genshistream
from genshi.core import START, END, XML_NAMESPACE, DOCTYPE, TEXT
from genshi.core  import  START_NS, END_NS, START_CDATA, END_CDATA, PI, COMMENT
from genshi.output import NamespaceFlattener

import _base

from html5lib.constants import voidElements

class TreeWalker(_base.TreeWalker):
    def __iter__(self):
        depth = 0
        ignore_until = None
        previous = None
        for event in self.tree:
            if previous is not None:
                if previous[0] == START:
                    depth += 1
                if ignore_until <= depth:
                    ignore_until = None
                if ignore_until is None:
                    for token in self.tokens(previous, event):
                        yield token
                        if token["type"] == "EmptyTag":
                            ignore_until = depth
                if previous[0] == END:
                    depth -= 1
            previous = event
        if previous is not None:
            if ignore_until is None or ignore_until <= depth:
                for token in self.tokens(previous, None):
                    yield token
            elif ignore_until is not None:
                raise ValueError("Illformed DOM event stream: void element without END_ELEMENT")

    def tokens(self, event, next):
        kind, data, pos = event
        if kind == START:
            tag, attrib = data
            name = tag.localname
            namespace = tag.namespace
            if tag in voidElements:
                for token in self.emptyTag(namespace, name, list(attrib),
                                           not next or next[0] != END 
                                           or next[1] != tag):
                    yield token
            else:
                yield self.startTag(namespace, name, list(attrib))

        elif kind == END:
            name = data.localname
            namespace = data.namespace
            if name not in voidElements:
                yield self.endTag(namespace, name)

        elif kind == COMMENT:
            yield self.comment(data)

        elif kind == TEXT:
            for token in self.text(data):
                yield token

        elif kind == DOCTYPE:
            yield self.doctype(*data)

        elif kind in (XML_NAMESPACE, DOCTYPE, START_NS, END_NS, \
          START_CDATA, END_CDATA, PI):
            pass

        else:
            yield self.unknown(kind)

########NEW FILE########
__FILENAME__ = lxmletree
from lxml import etree
from html5lib.treebuilders.etree import tag_regexp

from gettext import gettext
_ = gettext

import _base

from html5lib.constants import voidElements
from html5lib import ihatexml

class Root(object):
    def __init__(self, et):
        self.elementtree = et
        self.children = []
        if et.docinfo.internalDTD:
            self.children.append(Doctype(self, et.docinfo.root_name, 
                                         et.docinfo.public_id, 
                                         et.docinfo.system_url))
        root = et.getroot()
        node = root

        while node.getprevious() is not None:
            node = node.getprevious()
        while node is not None:
            self.children.append(node)
            node = node.getnext()

        self.text = None
        self.tail = None
    
    def __getitem__(self, key):
        return self.children[key]

    def getnext(self):
        return None

    def __len__(self):
        return 1

class Doctype(object):
    def __init__(self, root_node, name, public_id, system_id):
        self.root_node = root_node
        self.name = name
        self.public_id = public_id
        self.system_id = system_id
        
        self.text = None
        self.tail = None

    def getnext(self):
        return self.root_node.children[1]

class FragmentRoot(Root):
    def __init__(self, children):
        self.children = [FragmentWrapper(self, child) for child in children]
        self.text = self.tail = None

    def getnext(self):
        return None

class FragmentWrapper(object):
    def __init__(self, fragment_root, obj):
        self.root_node = fragment_root
        self.obj = obj
        if hasattr(self.obj, 'text'):
            self.text = self.obj.text
        else:
            self.text = None
        if hasattr(self.obj, 'tail'):
            self.tail = self.obj.tail
        else:
            self.tail = None
        self.isstring = isinstance(obj, basestring)
        
    def __getattr__(self, name):
        return getattr(self.obj, name)
    
    def getnext(self):
        siblings = self.root_node.children
        idx = siblings.index(self)
        if idx < len(siblings) - 1:
            return siblings[idx + 1]
        else:
            return None

    def __getitem__(self, key):
        return self.obj[key]

    def __nonzero__(self):
        return bool(self.obj)

    def getparent(self):
        return None

    def __str__(self):
        return str(self.obj)

    def __unicode__(self):
        return unicode(self.obj)

    def __len__(self):
        return len(self.obj)

        
class TreeWalker(_base.NonRecursiveTreeWalker):
    def __init__(self, tree):
        if hasattr(tree, "getroot"):
            tree = Root(tree)
        elif isinstance(tree, list):
            tree = FragmentRoot(tree)
        _base.NonRecursiveTreeWalker.__init__(self, tree)
        self.filter = ihatexml.InfosetFilter()
    def getNodeDetails(self, node):
        if isinstance(node, tuple): # Text node
            node, key = node
            assert key in ("text", "tail"), _("Text nodes are text or tail, found %s") % key
            return _base.TEXT, getattr(node, key)

        elif isinstance(node, Root):
            return (_base.DOCUMENT,)

        elif isinstance(node, Doctype):
            return _base.DOCTYPE, node.name, node.public_id, node.system_id

        elif isinstance(node, FragmentWrapper) and node.isstring:
            return _base.TEXT, node

        elif node.tag == etree.Comment:
            return _base.COMMENT, node.text

        elif node.tag == etree.Entity:
            return _base.ENTITY, node.text[1:-1] # strip &;

        else:
            #This is assumed to be an ordinary element
            match = tag_regexp.match(node.tag)
            if match:
                namespace, tag = match.groups()
            else:
                namespace = None
                tag = node.tag
            return (_base.ELEMENT, namespace, self.filter.fromXmlName(tag), 
                    [(self.filter.fromXmlName(name), value) for 
                     name,value in node.attrib.iteritems()], 
                     len(node) > 0 or node.text)

    def getFirstChild(self, node):
        assert not isinstance(node, tuple), _("Text nodes have no children")

        assert len(node) or node.text, "Node has no children"
        if node.text:
            return (node, "text")
        else:
            return node[0]

    def getNextSibling(self, node):
        if isinstance(node, tuple): # Text node
            node, key = node
            assert key in ("text", "tail"), _("Text nodes are text or tail, found %s") % key
            if key == "text":
                # XXX: we cannot use a "bool(node) and node[0] or None" construct here
                # because node[0] might evaluate to False if it has no child element
                if len(node):
                    return node[0]
                else:
                    return None
            else: # tail
                return node.getnext()

        return node.tail and (node, "tail") or node.getnext()

    def getParentNode(self, node):
        if isinstance(node, tuple): # Text node
            node, key = node
            assert key in ("text", "tail"), _("Text nodes are text or tail, found %s") % key
            if key == "text":
                return node
            # else: fallback to "normal" processing

        return node.getparent()

########NEW FILE########
__FILENAME__ = pulldom
from xml.dom.pulldom import START_ELEMENT, END_ELEMENT, \
    COMMENT, IGNORABLE_WHITESPACE, CHARACTERS

import _base

from html5lib.constants import voidElements

class TreeWalker(_base.TreeWalker):
    def __iter__(self):
        ignore_until = None
        previous = None
        for event in self.tree:
            if previous is not None and \
              (ignore_until is None or previous[1] is ignore_until):
                if previous[1] is ignore_until:
                    ignore_until = None
                for token in self.tokens(previous, event):
                    yield token
                    if token["type"] == "EmptyTag":
                        ignore_until = previous[1]
            previous = event
        if ignore_until is None or previous[1] is ignore_until:
            for token in self.tokens(previous, None):
                yield token
        elif ignore_until is not None:
            raise ValueError("Illformed DOM event stream: void element without END_ELEMENT")

    def tokens(self, event, next):
        type, node = event
        if type == START_ELEMENT:
            name = node.nodeName
            namespace = node.namespaceURI
            if name in voidElements:
                for token in self.emptyTag(namespace,
                                           name,
                                           node.attributes.items(), 
                                           not next or next[1] is not node):
                    yield token
            else:
                yield self.startTag(namespace, name, node.attributes.items())

        elif type == END_ELEMENT:
            name = node.nodeName
            namespace = node.namespaceURI
            if name not in voidElements:
                yield self.endTag(namespace, name)

        elif type == COMMENT:
            yield self.comment(node.nodeValue)

        elif type in (IGNORABLE_WHITESPACE, CHARACTERS):
            for token in self.text(node.nodeValue):
                yield token

        else:
            yield self.unknown(type)

########NEW FILE########
__FILENAME__ = simpletree
import gettext
_ = gettext.gettext

import _base

class TreeWalker(_base.NonRecursiveTreeWalker):
    """Given that simpletree has no performant way of getting a node's
    next sibling, this implementation returns "nodes" as tuples with the
    following content:

    1. The parent Node (Element, Document or DocumentFragment)

    2. The child index of the current node in its parent's children list

    3. A list used as a stack of all ancestors. It is a pair tuple whose
       first item is a parent Node and second item is a child index.
    """

    def getNodeDetails(self, node):
        if isinstance(node, tuple): # It might be the root Node
            parent, idx, parents = node
            node = parent.childNodes[idx]

        # testing node.type allows us not to import treebuilders.simpletree
        if node.type in (1, 2): # Document or DocumentFragment
            return (_base.DOCUMENT,)

        elif node.type == 3: # DocumentType
            return _base.DOCTYPE, node.name, node.publicId, node.systemId

        elif node.type == 4: # TextNode
            return _base.TEXT, node.value

        elif node.type == 5: # Element
            return (_base.ELEMENT, node.namespace, node.name, 
                    node.attributes.items(), node.hasContent())

        elif node.type == 6: # CommentNode
            return _base.COMMENT, node.data

        else:
            return _node.UNKNOWN, node.type

    def getFirstChild(self, node):
        if isinstance(node, tuple): # It might be the root Node
            parent, idx, parents = node
            parents.append((parent, idx))
            node = parent.childNodes[idx]
        else:
            parents = []

        assert node.hasContent(), "Node has no children"
        return (node, 0, parents)

    def getNextSibling(self, node):
        assert isinstance(node, tuple), "Node is not a tuple: " + str(node)
        parent, idx, parents = node
        idx += 1
        if len(parent.childNodes) > idx:
            return (parent, idx, parents)
        else:
            return None

    def getParentNode(self, node):
        assert isinstance(node, tuple)
        parent, idx, parents = node
        if parents:
            parent, idx = parents.pop()
            return parent, idx, parents
        else:
            # HACK: We could return ``parent`` but None will stop the algorithm the same way
            return None

########NEW FILE########
__FILENAME__ = soup
import re
import gettext
_ = gettext.gettext

from BeautifulSoup import BeautifulSoup, Declaration, Comment, Tag
from html5lib.constants import namespaces
import _base

class TreeWalker(_base.NonRecursiveTreeWalker):
    doctype_regexp = re.compile(
        r'DOCTYPE\s+(?P<name>[^\s]*)(\s*PUBLIC\s*"(?P<publicId>.*)"\s*"(?P<systemId1>.*)"|\s*SYSTEM\s*"(?P<systemId2>.*)")?')
    def getNodeDetails(self, node):
        if isinstance(node, BeautifulSoup): # Document or DocumentFragment
            return (_base.DOCUMENT,)

        elif isinstance(node, Declaration): # DocumentType
            string = unicode(node.string)
            #Slice needed to remove markup added during unicode conversion,
            #but only in some versions of BeautifulSoup/Python
            if string.startswith('<!') and string.endswith('>'):
                string = string[2:-1]
            m = self.doctype_regexp.match(string)
            #This regexp approach seems wrong and fragile
            #but beautiful soup stores the doctype as a single thing and we want the seperate bits
            #It should work as long as the tree is created by html5lib itself but may be wrong if it's
            #been modified at all
            #We could just feed to it a html5lib tokenizer, I guess...
            assert m is not None, "DOCTYPE did not match expected format"

            name = m.group('name')
            publicId = m.group('publicId')
            if publicId is not None:
                systemId = m.group('systemId1')
            else:
                systemId = m.group('systemId2')
            return _base.DOCTYPE, name, publicId or "", systemId or ""

        elif isinstance(node, Comment):
            string = unicode(node.string)
            if string.startswith('<!--') and string.endswith('-->'):
                string = string[4:-3]
            return _base.COMMENT, string

        elif isinstance(node, unicode): # TextNode
            return _base.TEXT, node

        elif isinstance(node, Tag): # Element
            return (_base.ELEMENT, namespaces["html"], node.name,
                    dict(node.attrs).items(), node.contents)
        else:
            return _base.UNKNOWN, node.__class__.__name__

    def getFirstChild(self, node):
        return node.contents[0]

    def getNextSibling(self, node):
        return node.nextSibling

    def getParentNode(self, node):
        return node.parent

########NEW FILE########
__FILENAME__ = _base
import gettext
_ = gettext.gettext

from html5lib.constants import voidElements, spaceCharacters
spaceCharacters = u"".join(spaceCharacters)

class TreeWalker(object):
    def __init__(self, tree):
        self.tree = tree

    def __iter__(self):
        raise NotImplementedError

    def error(self, msg):
        return {"type": "SerializeError", "data": msg}

    def normalizeAttrs(self, attrs):
        if not attrs:
            attrs = []
        elif hasattr(attrs, 'items'):
            attrs = attrs.items()
        return [(unicode(name),unicode(value)) for name,value in attrs]

    def emptyTag(self, namespace, name, attrs, hasChildren=False):
        yield {"type": "EmptyTag", "name": unicode(name), 
               "namespace":unicode(namespace),
               "data": self.normalizeAttrs(attrs)}
        if hasChildren:
            yield self.error(_("Void element has children"))

    def startTag(self, namespace, name, attrs):
        return {"type": "StartTag", 
                "name": unicode(name),
                "namespace":unicode(namespace),
                "data": self.normalizeAttrs(attrs)}

    def endTag(self, namespace, name):
        return {"type": "EndTag", 
                "name": unicode(name),
                "namespace":unicode(namespace),
                "data": []}

    def text(self, data):
        data = unicode(data)
        middle = data.lstrip(spaceCharacters)
        left = data[:len(data)-len(middle)]
        if left:
            yield {"type": "SpaceCharacters", "data": left}
        data = middle
        middle = data.rstrip(spaceCharacters)
        right = data[len(middle):]
        if middle:
            yield {"type": "Characters", "data": middle}
        if right:
            yield {"type": "SpaceCharacters", "data": right}

    def comment(self, data):
        return {"type": "Comment", "data": unicode(data)}

    def doctype(self, name, publicId=None, systemId=None, correct=True):
        return {"type": "Doctype",
                "name": name is not None and unicode(name) or u"",
                "publicId": publicId,
                "systemId": systemId,
                "correct": correct}

    def entity(self, name):
        return {"type": "Entity", "name": unicode(name)}

    def unknown(self, nodeType):
        return self.error(_("Unknown node type: ") + nodeType)

class RecursiveTreeWalker(TreeWalker):
    def walkChildren(self, node):
        raise NodeImplementedError

    def element(self, node, namespace, name, attrs, hasChildren):
        if name in voidElements:
            for token in self.emptyTag(namespace, name, attrs, hasChildren):
                yield token
        else:
            yield self.startTag(name, attrs)
            if hasChildren:
                for token in self.walkChildren(node):
                    yield token
            yield self.endTag(name)

from xml.dom import Node

DOCUMENT = Node.DOCUMENT_NODE
DOCTYPE = Node.DOCUMENT_TYPE_NODE
TEXT = Node.TEXT_NODE
ELEMENT = Node.ELEMENT_NODE
COMMENT = Node.COMMENT_NODE
ENTITY = Node.ENTITY_NODE
UNKNOWN = "<#UNKNOWN#>"

class NonRecursiveTreeWalker(TreeWalker):
    def getNodeDetails(self, node):
        raise NotImplementedError
    
    def getFirstChild(self, node):
        raise NotImplementedError
    
    def getNextSibling(self, node):
        raise NotImplementedError
    
    def getParentNode(self, node):
        raise NotImplementedError

    def __iter__(self):
        currentNode = self.tree
        while currentNode is not None:
            details = self.getNodeDetails(currentNode)
            type, details = details[0], details[1:]
            hasChildren = False
            endTag = None

            if type == DOCTYPE:
                yield self.doctype(*details)

            elif type == TEXT:
                for token in self.text(*details):
                    yield token

            elif type == ELEMENT:
                namespace, name, attributes, hasChildren = details
                if name in voidElements:
                    for token in self.emptyTag(namespace, name, attributes, 
                                               hasChildren):
                        yield token
                    hasChildren = False
                else:
                    endTag = name
                    yield self.startTag(namespace, name, attributes)

            elif type == COMMENT:
                yield self.comment(details[0])

            elif type == ENTITY:
                yield self.entity(details[0])

            elif type == DOCUMENT:
                hasChildren = True

            else:
                yield self.unknown(details[0])
            
            if hasChildren:
                firstChild = self.getFirstChild(currentNode)
            else:
                firstChild = None
            
            if firstChild is not None:
                currentNode = firstChild
            else:
                while currentNode is not None:
                    details = self.getNodeDetails(currentNode)
                    type, details = details[0], details[1:]
                    if type == ELEMENT:
                        namespace, name, attributes, hasChildren = details
                        if name not in voidElements:
                            yield self.endTag(namespace, name)
                    if self.tree is currentNode:
                        currentNode = None
                        break
                    nextSibling = self.getNextSibling(currentNode)
                    if nextSibling is not None:
                        currentNode = nextSibling
                        break
                    else:
                        currentNode = self.getParentNode(currentNode)

########NEW FILE########
__FILENAME__ = utils
try:
    frozenset
except NameError:
    #Import from the sets module for python 2.3
    from sets import Set as set
    from sets import ImmutableSet as frozenset

class MethodDispatcher(dict):
    """Dict with 2 special properties:

    On initiation, keys that are lists, sets or tuples are converted to
    multiple keys so accessing any one of the items in the original
    list-like object returns the matching value

    md = MethodDispatcher({("foo", "bar"):"baz"})
    md["foo"] == "baz"

    A default value which can be set through the default attribute.
    """

    def __init__(self, items=()):
        # Using _dictEntries instead of directly assigning to self is about
        # twice as fast. Please do careful performance testing before changing
        # anything here.
        _dictEntries = []
        for name,value in items:
            if type(name) in (list, tuple, frozenset, set):
                for item in name:
                    _dictEntries.append((item, value))
            else:
                _dictEntries.append((name, value))
        dict.__init__(self, _dictEntries)
        self.default = None

    def __getitem__(self, key):
        return dict.get(self, key, self.default)

#Pure python implementation of deque taken from the ASPN Python Cookbook
#Original code by Raymond Hettinger

class deque(object):

    def __init__(self, iterable=(), maxsize=-1):
        if not hasattr(self, 'data'):
            self.left = self.right = 0
            self.data = {}
        self.maxsize = maxsize
        self.extend(iterable)

    def append(self, x):
        self.data[self.right] = x
        self.right += 1
        if self.maxsize != -1 and len(self) > self.maxsize:
            self.popleft()
        
    def appendleft(self, x):
        self.left -= 1        
        self.data[self.left] = x
        if self.maxsize != -1 and len(self) > self.maxsize:
            self.pop()      
        
    def pop(self):
        if self.left == self.right:
            raise IndexError('cannot pop from empty deque')
        self.right -= 1
        elem = self.data[self.right]
        del self.data[self.right]         
        return elem
    
    def popleft(self):
        if self.left == self.right:
            raise IndexError('cannot pop from empty deque')
        elem = self.data[self.left]
        del self.data[self.left]
        self.left += 1
        return elem

    def clear(self):
        self.data.clear()
        self.left = self.right = 0

    def extend(self, iterable):
        for elem in iterable:
            self.append(elem)

    def extendleft(self, iterable):
        for elem in iterable:
            self.appendleft(elem)

    def rotate(self, n=1):
        if self:
            n %= len(self)
            for i in xrange(n):
                self.appendleft(self.pop())

    def __getitem__(self, i):
        if i < 0:
            i += len(self)
        try:
            return self.data[i + self.left]
        except KeyError:
            raise IndexError

    def __setitem__(self, i, value):
        if i < 0:
            i += len(self)        
        try:
            self.data[i + self.left] = value
        except KeyError:
            raise IndexError

    def __delitem__(self, i):
        size = len(self)
        if not (-size <= i < size):
            raise IndexError
        data = self.data
        if i < 0:
            i += size
        for j in xrange(self.left+i, self.right-1):
            data[j] = data[j+1]
        self.pop()
    
    def __len__(self):
        return self.right - self.left

    def __cmp__(self, other):
        if type(self) != type(other):
            return cmp(type(self), type(other))
        return cmp(list(self), list(other))
            
    def __repr__(self, _track=[]):
        if id(self) in _track:
            return '...'
        _track.append(id(self))
        r = 'deque(%r)' % (list(self),)
        _track.remove(id(self))
        return r
    
    def __getstate__(self):
        return (tuple(self),)
    
    def __setstate__(self, s):
        self.__init__(s[0])
        
    def __hash__(self):
        raise TypeError
    
    def __copy__(self):
        return self.__class__(self)
    
    def __deepcopy__(self, memo={}):
        from copy import deepcopy
        result = self.__class__()
        memo[id(self)] = result
        result.__init__(deepcopy(tuple(self), memo))
        return result

#Some utility functions to dal with weirdness around UCS2 vs UCS4
#python builds

def encodingType():
    if len() == 2:
        return "UCS2"
    else:
        return "UCS4"

def isSurrogatePair(data):   
    return (len(data) == 2 and
            ord(data[0]) >= 0xD800 and ord(data[0]) <= 0xDBFF and
            ord(data[1]) >= 0xDC00 and ord(data[1]) <= 0xDFFF)

def surrogatePairToCodepoint(data):
    char_val = (0x10000 + (ord(data[0]) - 0xD800) * 0x400 + 
                (ord(data[1]) - 0xDC00))
    return char_val

########NEW FILE########
__FILENAME__ = htmltmpl

""" A templating engine for separation of code and HTML.

    The documentation of this templating engine is separated to two parts:
    
        1. Description of the templating language.
           
        2. Documentation of classes and API of this module that provides
           a Python implementation of the templating language.
    
    All the documentation can be found in 'doc' directory of the
    distribution tarball or at the homepage of the engine.
    Latest versions of this module are also available at that website.

    You can use and redistribute this module under conditions of the
    GNU General Public License that can be found either at
    [ http://www.gnu.org/ ] or in file "LICENSE" contained in the
    distribution tarball of this module.

    Copyright (c) 2001 Tomas Styblo, tripie@cpan.org

    @name           htmltmpl
    @version        1.22
    @author-name    Tomas Styblo
    @author-email   tripie@cpan.org
    @website        http://htmltmpl.sourceforge.net/
    @license-name   GNU GPL
    @license-url    http://www.gnu.org/licenses/gpl.html
"""

__version__ = 1.22
__author__ = "Tomas Styblo (tripie@cpan.org)"

# All imported modules are part of the standard Python library.

from types import *
import re
import os
import os.path
import pprint       # only for debugging
import sys
import copy
import cgi          # for HTML escaping of variables
import urllib       # for URL escaping of variables
import cPickle      # for template compilation
import gettext
import portalocker  # for locking

INCLUDE_DIR = "inc"

# Total number of possible parameters.
# Increment if adding a parameter to any statement.
PARAMS_NUMBER = 3

# Relative positions of parameters in TemplateCompiler.tokenize().
PARAM_NAME = 1
PARAM_ESCAPE = 2
PARAM_GLOBAL = 3
PARAM_GETTEXT_STRING = 1

##############################################
#          CLASS: TemplateManager            #
##############################################

class TemplateManager:
    """  Class that manages compilation and precompilation of templates.
    
         You should use this class whenever you work with templates
         that are stored in a file. The class can create a compiled
         template and transparently manage its precompilation. It also
         keeps the precompiled templates up-to-date by modification times
         comparisons. 
    """

    def __init__(self, include=1, max_include=5, precompile=1, comments=1,
                 gettext=0, debug=0):
        """ Constructor.
        
            @header
            __init__(include=1, max_include=5, precompile=1, comments=1,
                     gettext=0, debug=0)
            
            @param include Enable or disable included templates.
            This optional parameter can be used to enable or disable
            <em>TMPL_INCLUDE</em> inclusion of templates. Disabling of
            inclusion can improve performance a bit. The inclusion is
            enabled by default.
      
            @param max_include Maximum depth of nested inclusions.
            This optional parameter can be used to specify maximum depth of
            nested <em>TMPL_INCLUDE</em> inclusions. It defaults to 5.
            This setting prevents infinite recursive inclusions.
            
            @param precompile Enable or disable precompilation of templates.
            This optional parameter can be used to enable or disable
            creation and usage of precompiled templates.
      
            A precompiled template is saved to the same directory in
            which the main template file is located. You need write
            permissions to that directory.

            Precompilation provides a significant performance boost because
            it's not necessary to parse the templates over and over again.
            The boost is especially noticeable when templates that include
            other templates are used.
            
            Comparison of modification times of the main template and all
            included templates is used to ensure that the precompiled
            templates are up-to-date. Templates are also recompiled if the
            htmltmpl module is updated.

            The <em>TemplateError</em>exception is raised when the precompiled
            template cannot be saved. Precompilation is enabled by default.
            
            @param comments Enable or disable template comments.
            This optional parameter can be used to enable or disable
            template comments.
            Disabling of the comments can improve performance a bit.
            Comments are enabled by default.
            
            @param gettext Enable or disable gettext support.

            @param debug Enable or disable debugging messages.
            This optional parameter is a flag that can be used to enable
            or disable debugging messages which are printed to the standard
            error output. The debugging messages are disabled by default.
        """
        # Save the optional parameters.
        # These values are not modified by any method.
        self._include = include
        self._max_include = max_include
        self._precompile = precompile
        self._comments = comments
        self._gettext = gettext
        self._debug = debug

        self.DEB("INIT DONE")

    def prepare(self, file):
        """ Preprocess, parse, tokenize and compile the template.
            
            If precompilation is enabled then this method tries to load
            a precompiled form of the template from the same directory
            in which the template source file is located. If it succeeds,
            then it compares modification times stored in the precompiled
            form to modification times of source files of the template,
            including source files of all templates included via the
            <em>TMPL_INCLUDE</em> statements. If any of the modification times
            differs, then the template is recompiled and the precompiled
            form updated.
            
            If precompilation is disabled, then this method parses and
            compiles the template.
            
            @header prepare(file)
            
            @return Compiled template.
            The methods returns an instance of the <em>Template</em> class
            which is a compiled form of the template. This instance can be
            used as input for the <em>TemplateProcessor</em>.
            
            @param file Path to the template file to prepare.
            The method looks for the template file in current directory
            if the parameter is a relative path. All included templates must
            be placed in subdirectory <strong>'inc'</strong> of the 
            directory in which the main template file is located.
        """
        compiled = None
        if self._precompile:
            if self.is_precompiled(file):
                try:
                    precompiled = self.load_precompiled(file)
                except PrecompiledError, template:
                    print >> sys.stderr, "Htmltmpl: bad precompiled "\
                                         "template '%s' removed" % template
                    compiled = self.compile(file)
                    self.save_precompiled(compiled)
                else:
                    precompiled.debug(self._debug)
                    compile_params = (self._include, self._max_include,
                                      self._comments, self._gettext)
                    if precompiled.is_uptodate(compile_params):
                        self.DEB("PRECOMPILED: UPTODATE")
                        compiled = precompiled
                    else:
                        self.DEB("PRECOMPILED: NOT UPTODATE")
                        compiled = self.update(precompiled)
            else:
                self.DEB("PRECOMPILED: NOT PRECOMPILED")
                compiled = self.compile(file)
                self.save_precompiled(compiled)
        else:
            self.DEB("PRECOMPILATION DISABLED")
            compiled = self.compile(file)
        return compiled
    
    def update(self, template):
        """ Update (recompile) a compiled template.
        
            This method recompiles a template compiled from a file.
            If precompilation is enabled then the precompiled form saved on
            disk is also updated.
            
            @header update(template)
            
            @return Recompiled template.
            It's ensured that the returned template is up-to-date.
            
            @param template A compiled template.
            This parameter should be an instance of the <em>Template</em>
            class, created either by the <em>TemplateManager</em> or by the
            <em>TemplateCompiler</em>. The instance must represent a template
            compiled from a file on disk.
        """
        self.DEB("UPDATE")
        updated = self.compile(template.file())
        if self._precompile:
            self.save_precompiled(updated)
        return updated

    ##############################################
    #              PRIVATE METHODS               #
    ##############################################    

    def DEB(self, str):
        """ Print debugging message to stderr if debugging is enabled. 
            @hidden
        """
        if self._debug: print >> sys.stderr, str

    def compile(self, file):
        """ Compile the template.
            @hidden
        """
        return TemplateCompiler(self._include, self._max_include,
                                self._comments, self._gettext,
                                self._debug).compile(file)
    
    def is_precompiled(self, file):
        """ Return true if the template is already precompiled on the disk.
            This method doesn't check whether the compiled template is
            uptodate.
            @hidden
        """
        filename = file + "c"   # "template.tmplc"
        if os.path.isfile(filename):
            return 1
        else:
            return 0
        
    def load_precompiled(self, file):
        """ Load precompiled template from disk.

            Remove the precompiled template file and recompile it
            if the file contains corrupted or unpicklable data.
            
            @hidden
        """
        filename = file + "c"   # "template.tmplc"
        self.DEB("LOADING PRECOMPILED")
        try:
            remove_bad = 0
            file = None
            try:
                file = open(filename, "rb")
                portalocker.lock(file, portalocker.LOCK_SH)
                precompiled = cPickle.load(file)
            except IOError, (errno, errstr):
                raise TemplateError, "IO error in load precompiled "\
                                     "template '%s': (%d) %s"\
                                     % (filename, errno, errstr)
            except cPickle.UnpicklingError:
                remove_bad = 1
                raise PrecompiledError, filename
            except:
                remove_bad = 1
                raise
            else:
                return precompiled
        finally:
            if file:
                portalocker.unlock(file)
                file.close()
            if remove_bad and os.path.isfile(filename):
                # X: We may lose the original exception here, raising OSError.
                os.remove(filename)
                
    def save_precompiled(self, template):
        """ Save compiled template to disk in precompiled form.
            
            Associated metadata is also saved. It includes: filename of the
            main template file, modification time of the main template file,
            modification times of all included templates and version of the
            htmltmpl module which compiled the template.
            
            The method removes a file which is saved only partially because
            of some error.
            
            @hidden
        """
        filename = template.file() + "c"   # creates "template.tmplc"
        # Check if we have write permission to the template's directory.
        template_dir = os.path.dirname(os.path.abspath(filename))
        if not os.access(template_dir, os.W_OK):
            raise TemplateError, "Cannot save precompiled templates "\
                                 "to '%s': write permission denied."\
                                 % template_dir
        try:
            remove_bad = 0
            file = None
            try:
                file = open(filename, "wb")   # may truncate existing file
                portalocker.lock(file, portalocker.LOCK_EX)
                BINARY = 1
                READABLE = 0
                if self._debug:
                    cPickle.dump(template, file, READABLE)
                else:
                    cPickle.dump(template, file, BINARY)
            except IOError, (errno, errstr):
                remove_bad = 1
                raise TemplateError, "IO error while saving precompiled "\
                                     "template '%s': (%d) %s"\
                                      % (filename, errno, errstr)
            except cPickle.PicklingError, error:
                remove_bad = 1
                raise TemplateError, "Pickling error while saving "\
                                     "precompiled template '%s': %s"\
                                     % (filename, error)
            except:
                remove_bad = 1
                raise
            else:
                self.DEB("SAVING PRECOMPILED")
        finally:
            if file:
                portalocker.unlock(file)
                file.close()
            if remove_bad and os.path.isfile(filename):
                # X: We may lose the original exception here, raising OSError.
                os.remove(filename)


##############################################
#          CLASS: TemplateProcessor          #
##############################################

class TemplateProcessor:
    """ Fill the template with data and process it.

        This class provides actual processing of a compiled template.
        Use it to set template variables and loops and then obtain
        result of the processing.
    """

    def __init__(self, html_escape=1, magic_vars=1, global_vars=0, debug=0):
        """ Constructor.

            @header __init__(html_escape=1, magic_vars=1, global_vars=0,
                             debug=0)

            @param html_escape Enable or disable HTML escaping of variables.
            This optional parameter is a flag that can be used to enable or
            disable automatic HTML escaping of variables.
            All variables are by default automatically HTML escaped. 
            The escaping process substitutes HTML brackets, ampersands and
            double quotes with appropriate HTML entities.
            
            @param magic_vars Enable or disable loop magic variables.
            This parameter can be used to enable or disable
            "magic" context variables, that are automatically defined inside
            loops. Magic variables are enabled by default.

            Refer to the language specification for description of these
            magic variables.
      
            @param global_vars Globally activate global lookup of variables.
            This optional parameter is a flag that can be used to specify
            whether variables which cannot be found in the current scope
            should be automatically looked up in enclosing scopes.

            Automatic global lookup is disabled by default. Global lookup
            can be overriden on a per-variable basis by the
            <strong>GLOBAL</strong> parameter of a <strong>TMPL_VAR</strong>
            statement.

            @param debug Enable or disable debugging messages.
        """
        self._html_escape = html_escape
        self._magic_vars = magic_vars
        self._global_vars = global_vars
        self._debug = debug        

        # Data structure containing variables and loops set by the
        # application. Use debug=1, process some template and
        # then check stderr to see how the structure looks.
        # It's modified only by set() and reset() methods.
        self._vars = {}        

        # Following variables are for multipart templates.
        self._current_part = 1
        self._current_pos = 0

    def set(self, var, value):
        """ Associate a value with top-level template variable or loop.

            A template identifier can represent either an ordinary variable
            (string) or a loop.

            To assign a value to a string identifier pass a scalar
            as the 'value' parameter. This scalar will be automatically
            converted to string.

            To assign a value to a loop identifier pass a list of mappings as
            the 'value' parameter. The engine iterates over this list and
            assigns values from the mappings to variables in a template loop
            block if a key in the mapping corresponds to a name of a variable
            in the loop block. The number of mappings contained in this list
            is equal to number of times the loop block is repeated in the
            output.
      
            @header set(var, value)
            @return No return value.

            @param var Name of template variable or loop.
            @param value The value to associate.
            
        """
        # The correctness of character case is verified only for top-level
        # variables.
        if self.is_ordinary_var(value):
            # template top-level ordinary variable
            if not var.islower():
                raise TemplateError, "Invalid variable name '%s'." % var
        elif type(value) == ListType:
            # template top-level loop
            if var != var.capitalize():
                raise TemplateError, "Invalid loop name '%s'." % var
        else:
            raise TemplateError, "Value of toplevel variable '%s' must "\
                                 "be either a scalar or a list." % var
        self._vars[var] = value
        self.DEB("VALUE SET: " + str(var))
        
    def reset(self, keep_data=0):
        """ Reset the template data.

            This method resets the data contained in the template processor
            instance. The template processor instance can be used to process
            any number of templates, but this method must be called after
            a template is processed to reuse the instance,

            @header reset(keep_data=0)
            @return No return value.

            @param keep_data Do not reset the template data.
            Use this flag if you do not want the template data to be erased.
            This way you can reuse the data contained in the instance of
            the <em>TemplateProcessor</em>.
        """
        self._current_part = 1
        self._current_pos = 0
        if not keep_data:
            self._vars.clear()
        self.DEB("RESET")

    def process(self, template, part=None):
        """ Process a compiled template. Return the result as string.

            This method actually processes a template and returns
            the result.

            @header process(template, part=None)
            @return Result of the processing as string.

            @param template A compiled template.
            Value of this parameter must be an instance of the
            <em>Template</em> class created either by the
            <em>TemplateManager</em> or by the <em>TemplateCompiler</em>.

            @param part The part of a multipart template to process.
            This parameter can be used only together with a multipart
            template. It specifies the number of the part to process.
            It must be greater than zero, because the parts are numbered
            from one.

            The parts must be processed in the right order. You
            cannot process a part which precedes an already processed part.

            If this parameter is not specified, then the whole template
            is processed, or all remaining parts are processed.
        """
        self.DEB("APP INPUT:")
        if self._debug: pprint.pprint(self._vars, sys.stderr)
        if part != None and (part == 0 or part < self._current_part):
            raise TemplateError, "process() - invalid part number"

        # This flag means "jump behind the end of current statement" or
        # "skip the parameters of current statement".
        # Even parameters that actually are not present in the template
        # do appear in the list of tokens as empty items !
        skip_params = 0 

        # Stack for enabling or disabling output in response to TMPL_IF,
        # TMPL_UNLESS, TMPL_ELSE and TMPL_LOOPs with no passes.
        output_control = []
        ENABLE_OUTPUT = 1
        DISABLE_OUTPUT = 0
        
        # Stacks for data related to loops.
        loop_name = []        # name of a loop
        loop_pass = []        # current pass of a loop (counted from zero)
        loop_start = []       # index of loop start in token list
        loop_total = []       # total number of passes in a loop
        
        tokens = template.tokens()
        len_tokens = len(tokens)
        out = ""              # buffer for processed output

        # Recover position at which we ended after processing of last part.
        i = self._current_pos
            
        # Process the list of tokens.
        while 1:
            if i == len_tokens: break            
            if skip_params:   
                # Skip the parameters following a statement.
                skip_params = 0
                i += PARAMS_NUMBER
                continue

            token = tokens[i]
            if token.startswith("<TMPL_") or \
               token.startswith("</TMPL_"):
                if token == "<TMPL_VAR":
                    # TMPL_VARs should be first. They are the most common.
                    var = tokens[i + PARAM_NAME]
                    if not var:
                        raise TemplateError, "No identifier in <TMPL_VAR>."
                    escape = tokens[i + PARAM_ESCAPE]
                    globalp = tokens[i + PARAM_GLOBAL]
                    skip_params = 1
                    
                    # If output of current block is not disabled then append
                    # the substitued and escaped variable to the output.
                    if DISABLE_OUTPUT not in output_control:
                        value = str(self.find_value(var, loop_name, loop_pass,
                                                    loop_total, globalp))
                        out += self.escape(value, escape)
                        self.DEB("VAR: " + str(var))

                elif token == "<TMPL_LOOP":
                    var = tokens[i + PARAM_NAME]
                    if not var:
                        raise TemplateError, "No identifier in <TMPL_LOOP>."
                    skip_params = 1

                    # Find total number of passes in this loop.
                    passtotal = self.find_value(var, loop_name, loop_pass,
                                                loop_total)
                    if not passtotal: passtotal = 0
                    # Push data for this loop on the stack.
                    loop_total.append(passtotal)
                    loop_start.append(i)
                    loop_pass.append(0)
                    loop_name.append(var)

                    # Disable output of loop block if the number of passes
                    # in this loop is zero.
                    if passtotal == 0:
                        # This loop is empty.
                        output_control.append(DISABLE_OUTPUT)
                        self.DEB("LOOP: DISABLE: " + str(var))
                    else:
                        output_control.append(ENABLE_OUTPUT)
                        self.DEB("LOOP: FIRST PASS: %s TOTAL: %d"\
                                 % (var, passtotal))

                elif token == "<TMPL_IF":
                    var = tokens[i + PARAM_NAME]
                    if not var:
                        raise TemplateError, "No identifier in <TMPL_IF>."
                    globalp = tokens[i + PARAM_GLOBAL]
                    skip_params = 1
                    if self.find_value(var, loop_name, loop_pass,
                                       loop_total, globalp):
                        output_control.append(ENABLE_OUTPUT)
                        self.DEB("IF: ENABLE: " + str(var))
                    else:
                        output_control.append(DISABLE_OUTPUT)
                        self.DEB("IF: DISABLE: " + str(var))
     
                elif token == "<TMPL_UNLESS":
                    var = tokens[i + PARAM_NAME]
                    if not var:
                        raise TemplateError, "No identifier in <TMPL_UNLESS>."
                    globalp = tokens[i + PARAM_GLOBAL]
                    skip_params = 1
                    if self.find_value(var, loop_name, loop_pass,
                                      loop_total, globalp):
                        output_control.append(DISABLE_OUTPUT)
                        self.DEB("UNLESS: DISABLE: " + str(var))
                    else:
                        output_control.append(ENABLE_OUTPUT)
                        self.DEB("UNLESS: ENABLE: " + str(var))
     
                elif token == "</TMPL_LOOP":
                    skip_params = 1
                    if not loop_name:
                        raise TemplateError, "Unmatched </TMPL_LOOP>."
                    
                    # If this loop was not disabled, then record the pass.
                    if loop_total[-1] > 0: loop_pass[-1] += 1
                    
                    if loop_pass[-1] == loop_total[-1]:
                        # There are no more passes in this loop. Pop
                        # the loop from stack.
                        loop_pass.pop()
                        loop_name.pop()
                        loop_start.pop()
                        loop_total.pop()
                        output_control.pop()
                        self.DEB("LOOP: END")
                    else:
                        # Jump to the beggining of this loop block 
                        # to process next pass of the loop.
                        i = loop_start[-1]
                        self.DEB("LOOP: NEXT PASS")
     
                elif token == "</TMPL_IF":
                    skip_params = 1
                    if not output_control:
                        raise TemplateError, "Unmatched </TMPL_IF>."
                    output_control.pop()
                    self.DEB("IF: END")
     
                elif token == "</TMPL_UNLESS":
                    skip_params = 1
                    if not output_control:
                        raise TemplateError, "Unmatched </TMPL_UNLESS>."
                    output_control.pop()
                    self.DEB("UNLESS: END")
     
                elif token == "<TMPL_ELSE":
                    skip_params = 1
                    if not output_control:
                        raise TemplateError, "Unmatched <TMPL_ELSE>."
                    if output_control[-1] == DISABLE_OUTPUT:
                        # Condition was false, activate the ELSE block.
                        output_control[-1] = ENABLE_OUTPUT
                        self.DEB("ELSE: ENABLE")
                    elif output_control[-1] == ENABLE_OUTPUT:
                        # Condition was true, deactivate the ELSE block.
                        output_control[-1] = DISABLE_OUTPUT
                        self.DEB("ELSE: DISABLE")
                    else:
                        raise TemplateError, "BUG: ELSE: INVALID FLAG"

                elif token == "<TMPL_BOUNDARY":
                    if part and part == self._current_part:
                        self.DEB("BOUNDARY ON")
                        self._current_part += 1
                        self._current_pos = i + 1 + PARAMS_NUMBER
                        break
                    else:
                        skip_params = 1
                        self.DEB("BOUNDARY OFF")
                        self._current_part += 1

                elif token == "<TMPL_INCLUDE":
                    # TMPL_INCLUDE is left in the compiled template only
                    # when it was not replaced by the parser.
                    skip_params = 1
                    filename = tokens[i + PARAM_NAME]
                    out += """
                        <br />
                        <p>
                        <strong>HTMLTMPL WARNING:</strong><br />
                        Cannot include template: <strong>%s</strong>
                        </p>
                        <br />
                    """ % filename
                    self.DEB("CANNOT INCLUDE WARNING")

                elif token == "<TMPL_GETTEXT":
                    skip_params = 1
                    if DISABLE_OUTPUT not in output_control:
                        text = tokens[i + PARAM_GETTEXT_STRING]
                        out += gettext.gettext(text)
                        self.DEB("GETTEXT: " + text)
                    
                else:
                    # Unknown processing directive.
                    raise TemplateError, "Invalid statement %s>." % token
                     
            elif DISABLE_OUTPUT not in output_control:
                # Raw textual template data.
                # If output of current block is not disabled, then 
                # append template data to the output buffer.
                out += token
                
            i += 1
            # end of the big while loop
        
        # Check whether all opening statements were closed.
        if loop_name: raise TemplateError, "Missing </TMPL_LOOP>."
        if output_control: raise TemplateError, "Missing </TMPL_IF> or </TMPL_UNLESS>"
        return out

    ##############################################
    #              PRIVATE METHODS               #
    ##############################################

    def DEB(self, str):
        """ Print debugging message to stderr if debugging is enabled.
            @hidden
        """
        if self._debug: print >> sys.stderr, str

    def find_value(self, var, loop_name, loop_pass, loop_total,
                   global_override=None):
        """ Search the self._vars data structure to find variable var
            located in currently processed pass of a loop which
            is currently being processed. If the variable is an ordinary
            variable, then return it.
            
            If the variable is an identificator of a loop, then 
            return the total number of times this loop will
            be executed.
            
            Return an empty string, if the variable is not
            found at all.

            @hidden
        """
        # Search for the requested variable in magic vars if the name
        # of the variable starts with "__" and if we are inside a loop.
        if self._magic_vars and var.startswith("__") and loop_name:
            return self.magic_var(var, loop_pass[-1], loop_total[-1])
                    
        # Search for an ordinary variable or for a loop.
        # Recursively search in self._vars for the requested variable.
        scope = self._vars
        globals = []
        for i in range(len(loop_name)):            
            # If global lookup is on then push the value on the stack.
            if ((self._global_vars and global_override != "0") or \
                 global_override == "1") and scope.has_key(var) and \
               self.is_ordinary_var(scope[var]):
                globals.append(scope[var])
            
            # Descent deeper into the hierarchy.
            if scope.has_key(loop_name[i]) and scope[loop_name[i]]:
                scope = scope[loop_name[i]][loop_pass[i]]
            else:
                return ""
            
        if scope.has_key(var):
            # Value exists in current loop.
            if type(scope[var]) == ListType:
                # The requested value is a loop.
                # Return total number of its passes.
                return len(scope[var])
            else:
                return scope[var]
        elif globals and \
             ((self._global_vars and global_override != "0") or \
               global_override == "1"):
            # Return globally looked up value.
            return globals.pop()
        else:
            # No value found.
            if var[0].isupper():
                # This is a loop name.
                # Return zero, because the user wants to know number
                # of its passes.
                return 0
            else:
                return ""

    def magic_var(self, var, loop_pass, loop_total):
        """ Resolve and return value of a magic variable.
            Raise an exception if the magic variable is not recognized.

            @hidden
        """
        self.DEB("MAGIC: '%s', PASS: %d, TOTAL: %d"\
                 % (var, loop_pass, loop_total))
        if var == "__FIRST__":
            if loop_pass == 0:
                return 1
            else:
                return 0
        elif var == "__LAST__":
            if loop_pass == loop_total - 1:
                return 1
            else:
                return 0
        elif var == "__INNER__":
            # If this is neither the first nor the last pass.
            if loop_pass != 0 and loop_pass != loop_total - 1:
                return 1
            else:
                return 0        
        elif var == "__PASS__":
            # Magic variable __PASS__ counts passes from one.
            return loop_pass + 1
        elif var == "__PASSTOTAL__":
            return loop_total
        elif var == "__ODD__":
            # Internally pass numbers stored in loop_pass are counted from
            # zero. But the template language presents them counted from one.
            # Therefore we must add one to the actual loop_pass value to get
            # the value we present to the user.
            if (loop_pass + 1) % 2 != 0:
                return 1
            else:
                return 0
        elif var.startswith("__EVERY__"):
            # Magic variable __EVERY__x is never true in first or last pass.
            if loop_pass != 0 and loop_pass != loop_total - 1:
                # Check if an integer follows the variable name.
                try:
                    every = int(var[9:])   # nine is length of "__EVERY__"
                except ValueError:
                    raise TemplateError, "Magic variable __EVERY__x: "\
                                         "Invalid pass number."
                else:
                    if not every:
                        raise TemplateError, "Magic variable __EVERY__x: "\
                                             "Pass number cannot be zero."
                    elif (loop_pass + 1) % every == 0:
                        self.DEB("MAGIC: EVERY: " + str(every))
                        return 1
                    else:
                        return 0
            else:
                return 0
        else:
            raise TemplateError, "Invalid magic variable '%s'." % var

    def escape(self, str, override=""):
        """ Escape a string either by HTML escaping or by URL escaping.
            @hidden
        """
        ESCAPE_QUOTES = 1
        if (self._html_escape and override != "NONE" and override != "0" and \
            override != "URL") or override == "HTML" or override == "1":
            return cgi.escape(str, ESCAPE_QUOTES)
        elif override == "URL":
            return urllib.quote_plus(str)
        else:
            return str

    def is_ordinary_var(self, var):
        """ Return true if var is a scalar. (not a reference to loop)
            @hidden
        """
        if type(var) == StringType or type(var) == IntType or \
           type(var) == LongType or type(var) == FloatType:
            return 1
        else:
            return 0


##############################################
#          CLASS: TemplateCompiler           #
##############################################

class TemplateCompiler:
    """ Preprocess, parse, tokenize and compile the template.

        This class parses the template and produces a 'compiled' form
        of it. This compiled form is an instance of the <em>Template</em>
        class. The compiled form is used as input for the TemplateProcessor
        which uses it to actually process the template.

        This class should be used direcly only when you need to compile
        a template from a string. If your template is in a file, then you
        should use the <em>TemplateManager</em> class which provides
        a higher level interface to this class and also can save the
        compiled template to disk in a precompiled form.
    """

    def __init__(self, include=1, max_include=5, comments=1, gettext=0,
                 debug=0):
        """ Constructor.

        @header __init__(include=1, max_include=5, comments=1, gettext=0,
                         debug=0)

        @param include Enable or disable included templates.
        @param max_include Maximum depth of nested inclusions.
        @param comments Enable or disable template comments.
        @param gettext Enable or disable gettext support.
        @param debug Enable or disable debugging messages.
        """
        
        self._include = include
        self._max_include = max_include
        self._comments = comments
        self._gettext = gettext
        self._debug = debug
        
        # This is a list of filenames of all included templates.
        # It's modified by the include_templates() method.
        self._include_files = []

        # This is a counter of current inclusion depth. It's used to prevent
        # infinite recursive includes.
        self._include_level = 0
    
    def compile(self, file):
        """ Compile template from a file.

            @header compile(file)
            @return Compiled template.
            The return value is an instance of the <em>Template</em>
            class.

            @param file Filename of the template.
            See the <em>prepare()</em> method of the <em>TemplateManager</em>
            class for exaplanation of this parameter.
        """
        
        self.DEB("COMPILING FROM FILE: " + file)
        self._include_path = os.path.join(os.path.dirname(file), INCLUDE_DIR)
        tokens = self.parse(self.read(file))
        compile_params = (self._include, self._max_include, self._comments,
                          self._gettext)
        return Template(__version__, file, self._include_files,
                        tokens, compile_params, self._debug)

    def compile_string(self, data):
        """ Compile template from a string.

            This method compiles a template from a string. The
            template cannot include any templates.
            <strong>TMPL_INCLUDE</strong> statements are turned into warnings.

            @header compile_string(data)
            @return Compiled template.
            The return value is an instance of the <em>Template</em>
            class.

            @param data String containing the template data.        
        """
        self.DEB("COMPILING FROM STRING")
        self._include = 0
        tokens = self.parse(data)
        compile_params = (self._include, self._max_include, self._comments,
                          self._gettext)
        return Template(__version__, None, None, tokens, compile_params,
                        self._debug)

    ##############################################
    #              PRIVATE METHODS               #
    ##############################################
                
    def DEB(self, str):
        """ Print debugging message to stderr if debugging is enabled.
            @hidden
        """
        if self._debug: print >> sys.stderr, str
    
    def read(self, filename):
        """ Read content of file and return it. Raise an error if a problem
            occurs.
            @hidden
        """
        self.DEB("READING: " + filename)
        try:
            f = None
            try:
                f = open(filename, "r")
                data = f.read()
            except IOError, (errno, errstr):
                raise TemplateError, "IO error while reading template '%s': "\
                                     "(%d) %s" % (filename, errno, errstr)
            else:
                return data
        finally:
            if f: f.close()
               
    def parse(self, template_data):
        """ Parse the template. This method is recursively called from
            within the include_templates() method.

            @return List of processing tokens.
            @hidden
        """
        if self._comments:
            self.DEB("PREPROCESS: COMMENTS")
            template_data = self.remove_comments(template_data)
        tokens = self.tokenize(template_data)
        if self._include:
            self.DEB("PREPROCESS: INCLUDES")
            self.include_templates(tokens)
        return tokens

    def remove_comments(self, template_data):
        """ Remove comments from the template data.
            @hidden
        """
        pattern = r"### .*"
        return re.sub(pattern, "", template_data)
           
    def include_templates(self, tokens):
        """ Process TMPL_INCLUDE statements. Use the include_level counter
            to prevent infinite recursion. Record paths to all included
            templates to self._include_files.
            @hidden
        """
        i = 0
        out = ""    # buffer for output
        skip_params = 0
        
        # Process the list of tokens.
        while 1:
            if i == len(tokens): break
            if skip_params:
                skip_params = 0
                i += PARAMS_NUMBER
                continue

            token = tokens[i]
            if token == "<TMPL_INCLUDE":
                filename = tokens[i + PARAM_NAME]
                if not filename:
                    raise TemplateError, "No filename in <TMPL_INCLUDE>."
                self._include_level += 1
                if self._include_level > self._max_include:
                    # Do not include the template.
                    # Protection against infinite recursive includes.
                    skip_params = 1
                    self.DEB("INCLUDE: LIMIT REACHED: " + filename)
                else:
                    # Include the template.
                    skip_params = 0
                    include_file = os.path.join(self._include_path, filename)
                    self._include_files.append(include_file)
                    include_data = self.read(include_file)
                    include_tokens = self.parse(include_data)

                    # Append the tokens from the included template to actual
                    # position in the tokens list, replacing the TMPL_INCLUDE
                    # token and its parameters.
                    tokens[i:i+PARAMS_NUMBER+1] = include_tokens
                    i = i + len(include_tokens)
                    self.DEB("INCLUDED: " + filename)
                    continue   # Do not increment 'i' below.
            i += 1
            # end of the main while loop

        if self._include_level > 0: self._include_level -= 1
        return out
    
    def tokenize(self, template_data):
        """ Split the template into tokens separated by template statements.
            The statements itself and associated parameters are also
            separately  included in the resulting list of tokens.
            Return list of the tokens.

            @hidden
        """
        self.DEB("TOKENIZING TEMPLATE")
        # NOTE: The TWO double quotes in character class in the regexp below
        # are there only to prevent confusion of syntax highlighter in Emacs.
        pattern = r"""
            (?:^[ \t]+)?               # eat spaces, tabs (opt.)
            (<
             (?:!--[ ])?               # comment start + space (opt.)
             /?TMPL_[A-Z]+             # closing slash / (opt.) + statement
             [ a-zA-Z0-9""/.=:_\\-]*   # this spans also comments ending (--)
             >)
            [%s]?                      # eat trailing newline (opt.)
        """ % os.linesep
        rc = re.compile(pattern, re.VERBOSE | re.MULTILINE)
        split = rc.split(template_data)
        tokens = []
        for statement in split:
            if statement.startswith("<TMPL_") or \
               statement.startswith("</TMPL_") or \
               statement.startswith("<!-- TMPL_") or \
               statement.startswith("<!-- /TMPL_"):
                # Processing statement.
                statement = self.strip_brackets(statement)
                params = re.split(r"\s+", statement)
                tokens.append(self.find_directive(params))
                tokens.append(self.find_name(params))
                tokens.append(self.find_param("ESCAPE", params))
                tokens.append(self.find_param("GLOBAL", params))
            else:
                # "Normal" template data.
                if self._gettext:
                    self.DEB("PARSING GETTEXT STRINGS")
                    self.gettext_tokens(tokens, statement)
                else:
                    tokens.append(statement)
        return tokens
    
    def gettext_tokens(self, tokens, str):
        """ Find gettext strings and return appropriate array of
            processing tokens.
            @hidden
        """
        escaped = 0
        gt_mode = 0
        i = 0
        buf = ""
        while(1):
            if i == len(str): break
            if str[i] == "\\":
                escaped = 0
                if str[i+1] == "\\":
                    buf += "\\"
                    i += 2
                    continue
                elif str[i+1] == "[" or str[i+1] == "]":
                    escaped = 1
                else:
                    buf += "\\"
            elif str[i] == "[" and str[i+1] == "[":
                if gt_mode:
                    if escaped:
                        escaped = 0
                        buf += "["
                    else:
                        buf += "["
                else:
                    if escaped:
                        escaped = 0
                        buf += "["
                    else:
                        tokens.append(buf)
                        buf = ""
                        gt_mode = 1
                        i += 2
                        continue
            elif str[i] == "]" and str[i+1] == "]":
                if gt_mode:
                    if escaped:
                        escaped = 0
                        buf += "]"
                    else:
                        self.add_gettext_token(tokens, buf)
                        buf = ""
                        gt_mode = 0
                        i += 2
                        continue
                else:
                    if escaped:
                        escaped = 0
                        buf += "]"
                    else:
                        buf += "]"
            else:
                escaped = 0
                buf += str[i]
            i += 1
            # end of the loop
        
        if buf:
            tokens.append(buf)
                
    def add_gettext_token(self, tokens, str):
        """ Append a gettext token and gettext string to the tokens array.
            @hidden
        """
        self.DEB("GETTEXT PARSER: TOKEN: " + str)
        tokens.append("<TMPL_GETTEXT")
        tokens.append(str)
        tokens.append(None)
        tokens.append(None)
    
    def strip_brackets(self, statement):
        """ Strip HTML brackets (with optional HTML comments) from the
            beggining and from the end of a statement.
            @hidden
        """
        if statement.startswith("<!-- TMPL_") or \
           statement.startswith("<!-- /TMPL_"):
            return statement[5:-4]
        else:
            return statement[1:-1]

    def find_directive(self, params):
        """ Extract processing directive (TMPL_*) from a statement.
            @hidden
        """
        directive = params[0]
        del params[0]
        self.DEB("TOKENIZER: DIRECTIVE: " + directive)
        return "<" + directive

    def find_name(self, params):
        """ Extract identifier from a statement. The identifier can be
            specified both implicitely or explicitely as a 'NAME' parameter.
            @hidden
        """
        if len(params) > 0 and '=' not in params[0]:
            # implicit identifier
            name = params[0]
            del params[0]
        else:
            # explicit identifier as a 'NAME' parameter
            name = self.find_param("NAME", params)
        self.DEB("TOKENIZER: NAME: " + str(name))
        return name

    def find_param(self, param, params):
        """ Extract value of parameter from a statement.
            @hidden
        """
        for pair in params:
            name, value = pair.split("=")
            if not name or not value:
                raise TemplateError, "Syntax error in template."
            if name == param:
                if value[0] == '"':
                    # The value is in double quotes.
                    ret_value = value[1:-1]
                else:
                    # The value is without double quotes.
                    ret_value = value
                self.DEB("TOKENIZER: PARAM: '%s' => '%s'" % (param, ret_value))
                return ret_value
        else:
            self.DEB("TOKENIZER: PARAM: '%s' => NOT DEFINED" % param)
            return None


##############################################
#              CLASS: Template               #
##############################################

class Template:
    """ This class represents a compiled template.

        This class provides storage and methods for the compiled template
        and associated metadata. It's serialized by pickle if we need to
        save the compiled template to disk in a precompiled form.

        You should never instantiate this class directly. Always use the
        <em>TemplateManager</em> or <em>TemplateCompiler</em> classes to
        create the instances of this class.

        The only method which you can directly use is the <em>is_uptodate</em>
        method.
    """
    
    def __init__(self, version, file, include_files, tokens, compile_params,
                 debug=0):
        """ Constructor.
            @hidden
        """
        self._version = version
        self._file = file
        self._tokens = tokens
        self._compile_params = compile_params
        self._debug = debug
        self._mtime = None        
        self._include_mtimes = {}

        if not file:
            self.DEB("TEMPLATE WAS COMPILED FROM A STRING")
            return

        # Save modifitcation time of the main template file.           
        if os.path.isfile(file):
            self._mtime = os.path.getmtime(file)
        else:
            raise TemplateError, "Template: file does not exist: '%s'" % file

        # Save modificaton times of all included template files.
        for inc_file in include_files:
            if os.path.isfile(inc_file):
                self._include_mtimes[inc_file] = os.path.getmtime(inc_file)
            else:
                raise TemplateError, "Template: file does not exist: '%s'"\
                                     % inc_file
            
        self.DEB("NEW TEMPLATE CREATED")

    def is_uptodate(self, compile_params=None):
        """ Check whether the compiled template is uptodate.

            Return true if this compiled template is uptodate.
            Return false, if the template source file was changed on the
            disk since it was compiled.
            Works by comparison of modification times.
            Also takes modification times of all included templates
            into account.

            @header is_uptodate(compile_params=None)
            @return True if the template is uptodate, false otherwise.

            @param compile_params Only for internal use.
            Do not use this optional parameter. It's intended only for
            internal use by the <em>TemplateManager</em>.
        """
        if not self._file:
            self.DEB("TEMPLATE COMPILED FROM A STRING")
            return 0
        
        if self._version != __version__:
            self.DEB("TEMPLATE: VERSION NOT UPTODATE")
            return 0

        if compile_params != None and compile_params != self._compile_params:
            self.DEB("TEMPLATE: DIFFERENT COMPILATION PARAMS")
            return 0
    
        # Check modification times of the main template and all included
        # templates. If the included template no longer exists, then
        # the problem will be resolved when the template is recompiled.

        # Main template file.
        if not (os.path.isfile(self._file) and \
                self._mtime == os.path.getmtime(self._file)):
            self.DEB("TEMPLATE: NOT UPTODATE: " + self._file)
            return 0        

        # Included templates.
        for inc_file in self._include_mtimes.keys():
            if not (os.path.isfile(inc_file) and \
                    self._include_mtimes[inc_file] == \
                    os.path.getmtime(inc_file)):
                self.DEB("TEMPLATE: NOT UPTODATE: " + inc_file)
                return 0
        else:
            self.DEB("TEMPLATE: UPTODATE")
            return 1       
    
    def tokens(self):
        """ Get tokens of this template.
            @hidden
        """
        return self._tokens

    def file(self):
        """ Get filename of the main file of this template.
            @hidden
        """
        return self._file

    def debug(self, debug):
        """ Get debugging state.
            @hidden
        """
        self._debug = debug

    ##############################################
    #              PRIVATE METHODS               #
    ##############################################

    def __getstate__(self):
        """ Used by pickle when the class is serialized.
            Remove the 'debug' attribute before serialization.
            @hidden
        """
        dict = copy.copy(self.__dict__)
        del dict["_debug"]
        return dict

    def __setstate__(self, dict):
        """ Used by pickle when the class is unserialized.
            Add the 'debug' attribute.
            @hidden
        """
        dict["_debug"] = 0
        self.__dict__ = dict


    def DEB(self, str):
        """ Print debugging message to stderr.
            @hidden
        """
        if self._debug: print >> sys.stderr, str


##############################################
#                EXCEPTIONS                  #
##############################################

class TemplateError(Exception):
    """ Fatal exception. Raised on runtime or template syntax errors.

        This exception is raised when a runtime error occurs or when a syntax
        error in the template is found. It has one parameter which always
        is a string containing a description of the error.

        All potential IOError exceptions are handled by the module and are
        converted to TemplateError exceptions. That means you should catch the
        TemplateError exception if there is a possibility that for example
        the template file will not be accesssible.

        The exception can be raised by constructors or by any method of any
        class.
        
        The instance is no longer usable when this exception is raised. 
    """

    def __init__(self, error):
        """ Constructor.
            @hidden
        """
        Exception.__init__(self, "Htmltmpl error: " + error)


class PrecompiledError(Exception):
    """ This exception is _PRIVATE_ and non fatal.
        @hidden
    """

    def __init__(self, template):
        """ Constructor.
            @hidden
        """
        Exception.__init__(self, template)


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
__FILENAME__ = portalocker
# portalocker.py - Cross-platform (posix/nt) API for flock-style file locking.
#                  Requires python 1.5.2 or better.
# See http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/65203/index_txt
# Except where otherwise noted, recipes in the Python Cookbook are 
# published under the Python license.

"""Cross-platform (posix/nt) API for flock-style file locking.

Synopsis:

   import portalocker
   file = open("somefile", "r+")
   portalocker.lock(file, portalocker.LOCK_EX)
   file.seek(12)
   file.write("foo")
   file.close()

If you know what you're doing, you may choose to

   portalocker.unlock(file)

before closing the file, but why?

Methods:

   lock( file, flags )
   unlock( file )

Constants:

   LOCK_EX
   LOCK_SH
   LOCK_NB

I learned the win32 technique for locking files from sample code
provided by John Nielsen <nielsenjf@my-deja.com> in the documentation
that accompanies the win32 modules.

Author: Jonathan Feinberg <jdf@pobox.com>
Version: $Id: portalocker.py,v 1.3 2001/05/29 18:47:55 Administrator Exp $
"""

import os

if os.name == 'nt':
	import win32con
	import win32file
	import pywintypes
	LOCK_EX = win32con.LOCKFILE_EXCLUSIVE_LOCK
	LOCK_SH = 0 # the default
	LOCK_NB = win32con.LOCKFILE_FAIL_IMMEDIATELY
	# is there any reason not to reuse the following structure?
	__overlapped = pywintypes.OVERLAPPED()
elif os.name == 'posix':
	import fcntl
	LOCK_EX = fcntl.LOCK_EX
	LOCK_SH = fcntl.LOCK_SH
	LOCK_NB = fcntl.LOCK_NB
else:
	raise RuntimeError("PortaLocker only defined for nt and posix platforms")

if os.name == 'nt':
	def lock(file, flags):
		hfile = win32file._get_osfhandle(file.fileno())
		win32file.LockFileEx(hfile, flags, 0, -0x10000, __overlapped)

	def unlock(file):
		hfile = win32file._get_osfhandle(file.fileno())
		win32file.UnlockFileEx(hfile, 0, -0x10000, __overlapped)

elif os.name =='posix':
	def lock(file, flags):
		fcntl.flock(file.fileno(), flags)

	def unlock(file):
		fcntl.flock(file.fileno(), fcntl.LOCK_UN)

if __name__ == '__main__':
	from time import time, strftime, localtime
	import sys
	import portalocker

	log = open('log.txt', "a+")
	portalocker.lock(log, portalocker.LOCK_EX)

	timestamp = strftime("%m/%d/%Y %H:%M:%S\n", localtime(time()))
	log.write( timestamp )

	print "Wrote lines. Hit enter to release lock."
	dummy = sys.stdin.readline()

	log.close()


########NEW FILE########
__FILENAME__ = pubsubhubbub_publish
#!/usr/bin/env python
#
# Copyright 2009 Google Inc.
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

"""Simple Publisher client for PubSubHubbub.

Example usage:

  from pubsubhubbub_publish import *
  try:
    publish('http://pubsubhubbub.appspot.com',
            'http://example.com/feed1/atom.xml',
            'http://example.com/feed2/atom.xml',
            'http://example.com/feed3/atom.xml')
  except PublishError, e:
    # handle exception...

Set the 'http_proxy' environment variable on *nix or Windows to use an
HTTP proxy.
"""

__author__ = 'bslatkin@gmail.com (Brett Slatkin)'

import urllib
import urllib2


class PublishError(Exception):
  """An error occurred while trying to publish to the hub."""


URL_BATCH_SIZE = 100


def publish(hub, *urls):
  """Publishes an event to a hub.

  Args:
    hub: The hub to publish the event to.
    **urls: One or more URLs to publish to. If only a single URL argument is
      passed and that item is an iterable that is not a string, the contents of
      that iterable will be used to produce the list of published URLs. If
      more than URL_BATCH_SIZE URLs are supplied, this function will batch them
      into chunks across multiple requests.

  Raises:
    PublishError if anything went wrong during publishing.
  """
  if len(urls) == 1 and not isinstance(urls[0], basestring):
    urls = list(urls[0])

  for i in xrange(0, len(urls), URL_BATCH_SIZE):
    chunk = urls[i:i+URL_BATCH_SIZE]
    data = urllib.urlencode(
        {'hub.url': chunk, 'hub.mode': 'publish'}, doseq=True)
    try:
      response = urllib2.urlopen(hub, data)
    except (IOError, urllib2.HTTPError), e:
      if hasattr(e, 'code') and e.code == 204:
        continue
      error = ''
      if hasattr(e, 'read'):
        error = e.read()
      raise PublishError('%s, Response: "%s"' % (e, error))

########NEW FILE########
__FILENAME__ = timeoutsocket

####
# Copyright 2000,2001 by Timothy O'Malley <timo@alum.mit.edu>
# 
#                All Rights Reserved
# 
# Permission to use, copy, modify, and distribute this software
# and its documentation for any purpose and without fee is hereby
# granted, provided that the above copyright notice appear in all
# copies and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Timothy O'Malley  not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission. 
# 
# Timothy O'Malley DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS, IN NO EVENT SHALL Timothy O'Malley BE LIABLE FOR
# ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE. 
#
####

"""Timeout Socket

This module enables a timeout mechanism on all TCP connections.  It
does this by inserting a shim into the socket module.  After this module
has been imported, all socket creation goes through this shim.  As a
result, every TCP connection will support a timeout.

The beauty of this method is that it immediately and transparently
enables the entire python library to support timeouts on TCP sockets.
As an example, if you wanted to SMTP connections to have a 20 second
timeout:

    import timeoutsocket
    import smtplib
    timeoutsocket.setDefaultSocketTimeout(20)


The timeout applies to the socket functions that normally block on
execution:  read, write, connect, and accept.  If any of these 
operations exceeds the specified timeout, the exception Timeout
will be raised.

The default timeout value is set to None.  As a result, importing
this module does not change the default behavior of a socket.  The
timeout mechanism only activates when the timeout has been set to
a numeric value.  (This behavior mimics the behavior of the
select.select() function.)

This module implements two classes: TimeoutSocket and TimeoutFile.

The TimeoutSocket class defines a socket-like object that attempts to
avoid the condition where a socket may block indefinitely.  The
TimeoutSocket class raises a Timeout exception whenever the
current operation delays too long. 

The TimeoutFile class defines a file-like object that uses the TimeoutSocket
class.  When the makefile() method of TimeoutSocket is called, it returns
an instance of a TimeoutFile.

Each of these objects adds two methods to manage the timeout value:

    get_timeout()   -->  returns the timeout of the socket or file
    set_timeout()   -->  sets the timeout of the socket or file


As an example, one might use the timeout feature to create httplib
connections that will timeout after 30 seconds:

    import timeoutsocket
    import httplib
    H = httplib.HTTP("www.python.org")
    H.sock.set_timeout(30)

Note:  When used in this manner, the connect() routine may still
block because it happens before the timeout is set.  To avoid
this, use the 'timeoutsocket.setDefaultSocketTimeout()' function.

Good Luck!

"""

__version__ = "$Revision: 1.1.1.1 $"
__author__  = "Timothy O'Malley <timo@alum.mit.edu>"

#
# Imports
#
import select, string
import socket
if not hasattr(socket, "_no_timeoutsocket"):
    _socket = socket.socket
else:
    _socket = socket._no_timeoutsocket


#
# Set up constants to test for Connected and Blocking operations.
# We delete 'os' and 'errno' to keep our namespace clean(er).
# Thanks to Alex Martelli and G. Li for the Windows error codes.
#
import os
if os.name == "nt":
    _IsConnected = ( 10022, 10056 )
    _ConnectBusy = ( 10035, )
    _AcceptBusy  = ( 10035, )
else:
    import errno
    _IsConnected = ( errno.EISCONN, )
    _ConnectBusy = ( errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK )
    _AcceptBusy  = ( errno.EAGAIN, errno.EWOULDBLOCK )
    del errno
del os


#
# Default timeout value for ALL TimeoutSockets
#
_DefaultTimeout = None
def setDefaultSocketTimeout(timeout):
    global _DefaultTimeout
    _DefaultTimeout = timeout
def getDefaultSocketTimeout():
    return _DefaultTimeout

#
# Exceptions for socket errors and timeouts
#
Error = socket.error
class Timeout(Exception):
    pass


#
# Factory function
#
from socket import AF_INET, SOCK_STREAM
def timeoutsocket(family=AF_INET, type=SOCK_STREAM, proto=None):
    if family != AF_INET or type != SOCK_STREAM:
        if proto:
            return _socket(family, type, proto)
        else:
            return _socket(family, type)
    return TimeoutSocket( _socket(family, type), _DefaultTimeout )
# end timeoutsocket

#
# The TimeoutSocket class definition
#
class TimeoutSocket:
    """TimeoutSocket object
    Implements a socket-like object that raises Timeout whenever
    an operation takes too long.
    The definition of 'too long' can be changed using the
    set_timeout() method.
    """

    _copies = 0
    _blocking = 1
    
    def __init__(self, sock, timeout):
        self._sock     = sock
        self._timeout  = timeout
    # end __init__

    def __getattr__(self, key):
        return getattr(self._sock, key)
    # end __getattr__

    def get_timeout(self):
        return self._timeout
    # end set_timeout

    def set_timeout(self, timeout=None):
        self._timeout = timeout
    # end set_timeout

    def setblocking(self, blocking):
        self._blocking = blocking
        return self._sock.setblocking(blocking)
    # end set_timeout

    def connect_ex(self, addr):
        errcode = 0
        try:
            self.connect(addr)
        except Error, why:
            errcode = why[0]
        return errcode
    # end connect_ex
        
    def connect(self, addr, port=None, dumbhack=None):
        # In case we were called as connect(host, port)
        if port != None:  addr = (addr, port)

        # Shortcuts
        sock    = self._sock
        timeout = self._timeout
        blocking = self._blocking

        # First, make a non-blocking call to connect
        try:
            sock.setblocking(0)
            sock.connect(addr)
            sock.setblocking(blocking)
            return
        except Error, why:
            # Set the socket's blocking mode back
            sock.setblocking(blocking)
            
            # If we are not blocking, re-raise
            if not blocking:
                raise
            
            # If we are already connected, then return success.
            # If we got a genuine error, re-raise it.
            errcode = why[0]
            if dumbhack and errcode in _IsConnected:
                return
            elif errcode not in _ConnectBusy:
                raise
            
        # Now, wait for the connect to happen
        # ONLY if dumbhack indicates this is pass number one.
        #   If select raises an error, we pass it on.
        #   Is this the right behavior?
        if not dumbhack:
            r,w,e = select.select([], [sock], [], timeout)
            if w:
                return self.connect(addr, dumbhack=1)

        # If we get here, then we should raise Timeout
        raise Timeout("Attempted connect to %s timed out." % str(addr) )
    # end connect

    def accept(self, dumbhack=None):
        # Shortcuts
        sock     = self._sock
        timeout  = self._timeout
        blocking = self._blocking

        # First, make a non-blocking call to accept
        #  If we get a valid result, then convert the
        #  accept'ed socket into a TimeoutSocket.
        # Be carefult about the blocking mode of ourselves.
        try:
            sock.setblocking(0)
            newsock, addr = sock.accept()
            sock.setblocking(blocking)
            timeoutnewsock = self.__class__(newsock, timeout)
            timeoutnewsock.setblocking(blocking)
            return (timeoutnewsock, addr)
        except Error, why:
            # Set the socket's blocking mode back
            sock.setblocking(blocking)

            # If we are not supposed to block, then re-raise
            if not blocking:
                raise
            
            # If we got a genuine error, re-raise it.
            errcode = why[0]
            if errcode not in _AcceptBusy:
                raise
            
        # Now, wait for the accept to happen
        # ONLY if dumbhack indicates this is pass number one.
        #   If select raises an error, we pass it on.
        #   Is this the right behavior?
        if not dumbhack:
            r,w,e = select.select([sock], [], [], timeout)
            if r:
                return self.accept(dumbhack=1)

        # If we get here, then we should raise Timeout
        raise Timeout("Attempted accept timed out.")
    # end accept

    def send(self, data, flags=0):
        sock = self._sock
        if self._blocking:
            r,w,e = select.select([],[sock],[], self._timeout)
            if not w:
                raise Timeout("Send timed out")
        return sock.send(data, flags)
    # end send

    def recv(self, bufsize, flags=0):
        sock = self._sock
        if self._blocking:
            r,w,e = select.select([sock], [], [], self._timeout)
            if not r:
                raise Timeout("Recv timed out")
        return sock.recv(bufsize, flags)
    # end recv

    def makefile(self, flags="r", bufsize=-1):
        self._copies = self._copies +1
        return TimeoutFile(self, flags, bufsize)
    # end makefile

    def close(self):
        if self._copies <= 0:
            self._sock.close()
        else:
            self._copies = self._copies -1
    # end close

# end TimeoutSocket


class TimeoutFile:
    """TimeoutFile object
    Implements a file-like object on top of TimeoutSocket.
    """
    
    def __init__(self, sock, mode="r", bufsize=4096):
        self._sock          = sock
        self._bufsize       = 4096
        if bufsize > 0: self._bufsize = bufsize
        if not hasattr(sock, "_inqueue"): self._sock._inqueue = ""

    # end __init__

    def __getattr__(self, key):
        return getattr(self._sock, key)
    # end __getattr__

    def close(self):
        self._sock.close()
        self._sock = None
    # end close
    
    def write(self, data):
        self.send(data)
    # end write

    def read(self, size=-1):
        _sock = self._sock
        _bufsize = self._bufsize
        while 1:
            datalen = len(_sock._inqueue)
            if datalen >= size >= 0:
                break
            bufsize = _bufsize
            if size > 0:
                bufsize = min(bufsize, size - datalen )
            buf = self.recv(bufsize)
            if not buf:
                break
            _sock._inqueue = _sock._inqueue + buf
        data = _sock._inqueue
        _sock._inqueue = ""
        if size > 0 and datalen > size:
            _sock._inqueue = data[size:]
            data = data[:size]
        return data
    # end read

    def readline(self, size=-1):
        _sock = self._sock
        _bufsize = self._bufsize
        while 1:
            idx = string.find(_sock._inqueue, "\n")
            if idx >= 0:
                break
            datalen = len(_sock._inqueue)
            if datalen >= size >= 0:
                break
            bufsize = _bufsize
            if size > 0:
                bufsize = min(bufsize, size - datalen )
            buf = self.recv(bufsize)
            if not buf:
                break
            _sock._inqueue = _sock._inqueue + buf

        data = _sock._inqueue
        _sock._inqueue = ""
        if idx >= 0:
            idx = idx + 1
            _sock._inqueue = data[idx:]
            data = data[:idx]
        elif size > 0 and datalen > size:
            _sock._inqueue = data[size:]
            data = data[:size]
        return data
    # end readline

    def readlines(self, sizehint=-1):
        result = []
        data = self.read()
        while data:
            idx = string.find(data, "\n")
            if idx >= 0:
                idx = idx + 1
                result.append( data[:idx] )
                data = data[idx:]
            else:
                result.append( data )
                data = ""
        return result
    # end readlines

    def flush(self):  pass

# end TimeoutFile


#
# Silently replace the socket() builtin function with
# our timeoutsocket() definition.
#
if not hasattr(socket, "_no_timeoutsocket"):
    socket._no_timeoutsocket = socket.socket
    socket.socket = timeoutsocket
del socket
socket = timeoutsocket
# Finis

########NEW FILE########
__FILENAME__ = planet
#!/usr/bin/env python
"""The Planet aggregator.

A flexible and easy-to-use aggregator for generating websites.

Visit http://www.planetplanet.org/ for more information and to download
the latest version.

Requires Python 2.1, recommends 2.3.
"""

__authors__ = [ "Scott James Remnant <scott@netsplit.com>",
                "Jeff Waugh <jdub@perkypants.org>" ]
__license__ = "Python"


import os, sys

if __name__ == "__main__":
    config_file = "config.ini"
    offline = 0
    verbose = 0
    only_if_new = 0
    expunge = 0
    debug_splice = 0
    no_publish = 0

    for arg in sys.argv[1:]:
        if arg == "-h" or arg == "--help":
            print "Usage: planet [options] [CONFIGFILE]"
            print
            print "Options:"
            print " -v, --verbose       DEBUG level logging during update"
            print " -o, --offline       Update the Planet from the cache only"
            print " -h, --help          Display this help message and exit"
            print " -n, --only-if-new   Only spider new feeds"
            print " -x, --expunge       Expunge old entries from cache"
            print " --no-publish        Do not publish feeds using PubSubHubbub"
            print
            sys.exit(0)
        elif arg == "-v" or arg == "--verbose":
            verbose = 1
        elif arg == "-o" or arg == "--offline":
            offline = 1
        elif arg == "-n" or arg == "--only-if-new":
            only_if_new = 1
        elif arg == "-x" or arg == "--expunge":
            expunge = 1
        elif arg == "-d" or arg == "--debug-splice":
            debug_splice = 1
        elif arg == "--no-publish":
            no_publish = 1
        elif arg.startswith("-"):
            print >>sys.stderr, "Unknown option:", arg
            sys.exit(1)
        else:
            config_file = arg

    from planet import config
    config.load(config_file)

    if verbose:
        import planet
        planet.getLogger('DEBUG',config.log_format())

    if not offline:
        from planet import spider
        try:
            spider.spiderPlanet(only_if_new=only_if_new)
        except Exception, e:
            print e

    from planet import splice
    doc = splice.splice()

    if debug_splice:
        from planet import logger
        logger.info('writing debug.atom')
        debug=open('debug.atom','w')
        try:
            from lxml import etree
            from StringIO import StringIO
            tree = etree.tostring(etree.parse(StringIO(doc.toxml())))
            debug.write(etree.tostring(tree, pretty_print=True))
        except:
            debug.write(doc.toprettyxml(indent='  ', encoding='utf-8'))
        debug.close

    splice.apply(doc.toxml('utf-8'))

    if config.pubsubhubbub_hub() and not no_publish:
        from planet import publish
        publish.publish(config)

    if expunge:
        from planet import expunge
        expunge.expungeCache

########NEW FILE########
__FILENAME__ = publish
#!/usr/bin/env python
"""
Main program to run just the splice portion of planet
"""

import os.path
import sys
from planet import publish, config

if __name__ == '__main__':

    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        config.load(sys.argv[1])
        publish.publish(config)
    else:
        print "Usage:"
        print "  python %s config.ini" % sys.argv[0]

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import glob, unittest, os, sys

# python 2.2 accomodations
try:
    from trace import fullmodname
except:
    def fullmodname(path):
        return os.path.splitext(path)[0].replace(os.sep, '.')

# more python 2.2 accomodations
if not hasattr(unittest.TestCase, 'assertTrue'):
    unittest.TestCase.assertTrue = unittest.TestCase.assert_
if not hasattr(unittest.TestCase, 'assertFalse'):
    unittest.TestCase.assertFalse = unittest.TestCase.failIf

# try to start in a consistent, predictable location
if sys.path[0]: os.chdir(sys.path[0])
sys.path[0] = os.getcwd()

# determine verbosity
verbosity = 1
for arg,value in (('-q',0),('--quiet',0),('-v',2),('--verbose',2)):
    if arg in sys.argv: 
        verbosity = value
        sys.argv.remove(arg)

# find all of the planet test modules
modules = []
for pattern in sys.argv[1:] or ['test_*.py']:
    modules += map(fullmodname, glob.glob(os.path.join('tests', pattern)))

# enable logging
import planet
if verbosity == 0: planet.getLogger("FATAL",None)
if verbosity == 1: planet.getLogger("WARNING",None)
if verbosity == 2: planet.getLogger("DEBUG",None)

# load all of the tests into a suite
try:
    suite = unittest.TestLoader().loadTestsFromNames(modules)
except Exception, exception:
    # attempt to produce a more specific message
    for module in modules: __import__(module)
    raise

# run test suite
unittest.TextTestRunner(verbosity=verbosity).run(suite)

########NEW FILE########
__FILENAME__ = spider
#!/usr/bin/env python
"""
Main program to run just the spider portion of planet
"""

import sys
from planet import spider, config

if __name__ == '__main__':

    config.load(sys.argv[1])

    if len(sys.argv) == 2:
        # spider all feeds 
        spider.spiderPlanet()
    elif len(sys.argv) > 2:
        # spider selected feeds 
        for feed in sys.argv[2:]:
            spider.spiderFeed(feed)
    else:
        print "Usage:"
        print "  python %s config.ini [URI URI ...]" % sys.argv[0]

########NEW FILE########
__FILENAME__ = splice
#!/usr/bin/env python
"""
Main program to run just the splice portion of planet
"""

import os.path
import sys
from planet import splice, config

if __name__ == '__main__':

    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        config.load(sys.argv[1])
        doc = splice.splice()
        splice.apply(doc.toxml('utf-8'))
    else:
        print "Usage:"
        print "  python %s config.ini" % sys.argv[0]

########NEW FILE########
__FILENAME__ = capture
#!/usr/bin/env python

"""
While unit tests are intended to be independently executable, it often
is helpful to ensure that some downstream tasks can be run with the
exact output produced by upstream tasks.

This script captures such output.  It should be run whenever there is
a major change in the contract between stages
"""

import shutil, os, sys

# move up a directory
sys.path.insert(0, os.path.split(sys.path[0])[0])
os.chdir(sys.path[0])

# copy spider output to splice input
import planet
from planet import spider, config
planet.getLogger('CRITICAL',None)

config.load('tests/data/spider/config.ini')
spider.spiderPlanet()
if os.path.exists('tests/data/splice/cache'):
    shutil.rmtree('tests/data/splice/cache')
shutil.move('tests/work/spider/cache', 'tests/data/splice/cache')

source=open('tests/data/spider/config.ini')
dest1=open('tests/data/splice/config.ini', 'w')
dest1.write(source.read().replace('/work/spider/', '/data/splice/'))
dest1.close()

source.seek(0)
dest2=open('tests/work/apply_config.ini', 'w')
dest2.write(source.read().replace('[Planet]', '''[Planet]
output_theme = asf
output_dir = tests/work/apply'''))
dest2.close()
source.close()

# copy splice output to apply input
from planet import splice
file=open('tests/data/apply/feed.xml', 'w')
config.load('tests/data/splice/config.ini')
data=splice.splice().toxml('utf-8')
file.write(data)
file.close()

# copy apply output to config/reading-list input
config.load('tests/work/apply_config.ini')
splice.apply(data)
shutil.move('tests/work/apply/opml.xml', 'tests/data/config')

shutil.rmtree('tests/work')

import runtests

########NEW FILE########
__FILENAME__ = rebase
# make href attributes absolute, using base argument passed in

import sys
try:
  base = sys.argv[sys.argv.index('--base')+1]
except:
  sys.stderr.write('Missing required argument: base\n')
  sys.exit()

from xml.dom import minidom, Node
from urlparse import urljoin

def rebase(node, newbase):
  if node.hasAttribute('href'):
    href=node.getAttribute('href')
    if href != urljoin(base,href):
      node.setAttribute('href', urljoin(base,href))
  for child in node.childNodes:
    if child.nodeType == Node.ELEMENT_NODE:
      rebase(child, newbase)

doc = minidom.parse(sys.stdin)
rebase(doc.documentElement, base)
print doc.toxml('utf-8')

########NEW FILE########
__FILENAME__ = reconstitute
#!/usr/bin/env python
import os, sys, ConfigParser, shutil, glob
venus_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,venus_base)

if __name__ == "__main__":
    import planet
    planet.getLogger('WARN',None)

    hide_planet_ns = True

    while len(sys.argv) > 1:
        if sys.argv[1] == '-v' or sys.argv[1] == '--verbose':
            del sys.argv[1]
        elif sys.argv[1] == '-p' or sys.argv[1] == '--planet':
            hide_planet_ns = False
            del sys.argv[1]
        else:
            break

    parser = ConfigParser.ConfigParser()
    parser.add_section('Planet')
    parser.add_section(sys.argv[1])
    work = reduce(os.path.join, ['tests','work','reconsititute'], venus_base)
    output = os.path.join(work, 'output')
    filters = os.path.join(venus_base,'filters')
    parser.set('Planet','cache_directory',work)
    parser.set('Planet','output_dir',output)
    parser.set('Planet','filter_directories',filters)
    if hide_planet_ns:
        parser.set('Planet','template_files','themes/common/atom.xml.xslt')
    else:
        parser.set('Planet','template_files','tests/data/reconstitute.xslt')

    for name, value in zip(sys.argv[2::2],sys.argv[3::2]):
        parser.set(sys.argv[1], name.lstrip('-'), value)

    from planet import config
    config.parser = parser

    from planet import spider
    spider.spiderPlanet(only_if_new=False)

    import feedparser
    for source in glob.glob(os.path.join(work, 'sources/*')):
        feed = feedparser.parse(source).feed
        if feed.has_key('title'):
            config.parser.set('Planet','name',feed.title_detail.value)
        if feed.has_key('link'):
            config.parser.set('Planet','link',feed.link)
        if feed.has_key('author_detail'):
            if feed.author_detail.has_key('name'):
                config.parser.set('Planet','owner_name',feed.author_detail.name)
            if feed.author_detail.has_key('email'):
                config.parser.set('Planet','owner_email',feed.author_detail.email)

    from planet import splice
    doc = splice.splice()

    sources = doc.getElementsByTagName('planet:source')
    if hide_planet_ns and len(sources) == 1:
        source = sources[0]
        feed = source.parentNode
        child = feed.firstChild
        while child:
            next = child.nextSibling
            if child.nodeName not in ['planet:source','entry']:
                feed.removeChild(child)
            child = next
        while source.hasChildNodes():
            child = source.firstChild
            source.removeChild(child)
            feed.insertBefore(child, source)
        atomNS='http://www.w3.org/2005/Atom'
        for source in doc.getElementsByTagNameNS(atomNS, 'source'):
            source.parentNode.removeChild(source)

    splice.apply(doc.toxml('utf-8'))

    if hide_planet_ns:
        atom = open(os.path.join(output,'atom.xml')).read()
    else:
        atom = open(os.path.join(output,'reconstitute')).read()

    shutil.rmtree(work)
    os.removedirs(os.path.dirname(work))

    print atom

########NEW FILE########
__FILENAME__ = test_apply
#!/usr/bin/env python

import unittest, os, shutil
from planet import config, splice, logger
from xml.dom import minidom

workdir = 'tests/work/apply'
configfile = 'tests/data/apply/config-%s.ini'
testfeed = 'tests/data/apply/feed.xml'

class ApplyTest(unittest.TestCase):
    def setUp(self):
        testfile = open(testfeed)
        self.feeddata = testfile.read()
        testfile.close()

        try:
             os.makedirs(workdir)
        except:
             self.tearDown()
             os.makedirs(workdir)
    
    def tearDown(self):
        shutil.rmtree(os.path.split(workdir)[0])

    def apply_asf(self):
        splice.apply(self.feeddata)

        # verify that selected files are there
        for file in ['index.html', 'default.css', 'images/foaf.png']:
            path = os.path.join(workdir, file)
            self.assertTrue(os.path.exists(path))
            self.assertTrue(os.stat(path).st_size > 0, file + ' has size 0')

        # verify that index.html is well formed, has content, and xml:lang
        html = open(os.path.join(workdir, 'index.html'))
        doc = minidom.parse(html)
        list = []
        content = lang = 0
        for div in doc.getElementsByTagName('div'):
            if div.getAttribute('class') != 'content': continue
            content += 1
            if div.getAttribute('xml:lang') == 'en-us': lang += 1
        html.close()
        self.assertEqual(12, content)
        self.assertEqual(3, lang)

    def test_apply_asf(self):
        config.load(configfile % 'asf')
        self.apply_asf()

    def test_apply_classic_fancy(self):
        config.load(configfile % 'fancy')
        self.apply_fancy()

    def test_apply_genshi_fancy(self):
        config.load(configfile % 'genshi')
        self.apply_fancy()

    def test_apply_filter_html(self):
        config.load(configfile % 'html')
        self.apply_asf()

        output = open(os.path.join(workdir, 'index.html')).read()
        self.assertTrue(output.find('/>')>=0)

        output = open(os.path.join(workdir, 'index.html4')).read()
        self.assertTrue(output.find('/>')<0)

    def test_apply_filter_mememe(self):
        config.load(configfile % 'mememe')
        self.apply_fancy()
    
        output = open(os.path.join(workdir, 'index.html')).read()
        self.assertTrue(output.find('<div class="sidebar"><h2>Memes <a href="memes.atom">')>=0)

    def apply_fancy(self):
        # drop slow templates unrelated to test at hand
        templates = config.parser.get('Planet','template_files').split()
        templates.remove('rss10.xml.tmpl')
        templates.remove('rss20.xml.tmpl')
        config.parser.set('Planet','template_files',' '.join(templates))
        
        splice.apply(self.feeddata)

        # verify that selected files are there
        for file in ['index.html', 'planet.css', 'images/jdub.png']:
            path = os.path.join(workdir, file)
            self.assertTrue(os.path.exists(path), path)
            self.assertTrue(os.stat(path).st_size > 0)

        # verify that index.html is well formed, has content, and xml:lang
        html = open(os.path.join(workdir, 'index.html')).read()
        self.assertTrue(html.find('<h1>test planet</h1>')>=0)
        self.assertTrue(html.find(
          '<h4><a href="http://example.com/2">Venus</a></h4>')>=0)

    def test_apply_filter(self):
        config.load(configfile % 'filter')
        splice.apply(self.feeddata)

        # verify that index.html is well formed, has content, and xml:lang
        html = open(os.path.join(workdir, 'index.html')).read()
        self.assertTrue(html.find(' href="http://example.com/default.css"')>=0)

import test_filter_genshi
for method in dir(test_filter_genshi.GenshiFilterTests):
    if method.startswith('test_'): break
else:
    delattr(ApplyTest,'test_apply_genshi_fancy')

try:
    import libxml2
except ImportError:

    delattr(ApplyTest,'test_apply_filter_mememe')

    try:
        import win32pipe
        (stdin,stdout) = win32pipe.popen4('xsltproc -V', 't')
        stdin.close()
        stdout.read()
        try:
            exitcode = stdout.close()
        except IOError:
            exitcode = -1
    except:
        import commands
        (exitstatus,output) = commands.getstatusoutput('xsltproc -V')
        exitcode = ((exitstatus>>8) & 0xFF)

    if exitcode:
        logger.warn("xsltproc is not available => can't test XSLT templates")
        for method in dir(ApplyTest):
            if method.startswith('test_'):  delattr(ApplyTest,method)

########NEW FILE########
__FILENAME__ = test_config
#!/usr/bin/env python

import unittest
from planet import config

class ConfigTest(unittest.TestCase):
    def setUp(self):
        config.load('tests/data/config/basic.ini')

    # administrivia

    def test_template(self):
        self.assertEqual(['index.html.tmpl', 'atom.xml.tmpl'], 
            config.template_files())

    def test_feeds(self):
        feeds = config.subscriptions()
        feeds.sort()
        self.assertEqual(['feed1', 'feed2'], feeds)

    def test_feed(self):
        self.assertEqual('http://example.com/atom.xml', config.feed())
        self.assertEqual('atom', config.feedtype())

    # planet wide configuration

    def test_name(self):
        self.assertEqual('Test Configuration', config.name())

    def test_link(self):
        self.assertEqual('http://example.com/', config.link())

    def test_pubsubhubbub_hub(self):
        self.assertEqual('http://pubsubhubbub.appspot.com', config.pubsubhubbub_hub())

    # per template configuration

    def test_days_per_page(self):
        self.assertEqual(7, config.days_per_page('index.html.tmpl'))
        self.assertEqual(0, config.days_per_page('atom.xml.tmpl'))

    def test_items_per_page(self):
        self.assertEqual(50, config.items_per_page('index.html.tmpl'))
        self.assertEqual(50, config.items_per_page('atom.xml.tmpl'))

    def test_encoding(self):
        self.assertEqual('utf-8', config.encoding('index.html.tmpl'))
        self.assertEqual('utf-8', config.encoding('atom.xml.tmpl'))

    # dictionaries

    def test_feed_options(self):
        self.assertEqual('one', config.feed_options('feed1')['name'])
        self.assertEqual('two', config.feed_options('feed2')['name'])

    def test_template_options(self):
        option = config.template_options('index.html.tmpl')
        self.assertEqual('7',  option['days_per_page'])
        self.assertEqual('50', option['items_per_page'])

    def test_filters(self):
        self.assertEqual(['foo','bar'], config.filters('feed2'))
        self.assertEqual(['foo'], config.filters('feed1'))

    # ints

    def test_timeout(self):
        self.assertEqual(30,
            config.feed_timeout())



########NEW FILE########
__FILENAME__ = test_config_csv
#!/usr/bin/env python

import os, shutil, unittest
from planet import config

workdir = os.path.join('tests', 'work', 'config', 'cache')

class ConfigCsvTest(unittest.TestCase):
    def setUp(self):
        config.load('tests/data/config/rlist-csv.ini')

    def tearDown(self):
        shutil.rmtree(workdir)
        os.removedirs(os.path.split(workdir)[0])

    # administrivia

    def test_feeds(self):
        feeds = config.subscriptions()
        feeds.sort()
        self.assertEqual(['feed1', 'feed2'], feeds)

    def test_filters(self):
        self.assertEqual(['foo','bar'], config.filters('feed2'))
        self.assertEqual(['foo'], config.filters('feed1'))

########NEW FILE########
__FILENAME__ = test_docs
#!/usr/bin/env python

import unittest, os, re
from xml.dom import minidom
from glob import glob
from htmlentitydefs import name2codepoint as n2cp

class DocsTest(unittest.TestCase):

    def test_well_formed(self):
        def substitute_entity(match):
            ent = match.group(1)
            try:
                  return "&#%d;" % n2cp[ent]
            except:
                  return "&%s;" % ent

        for doc in glob('docs/*'):
            if os.path.isdir(doc): continue
            if doc.endswith('.css') or doc.endswith('.js'): continue

            source = open(doc).read()
            source = re.sub('&(\w+);', substitute_entity, source)

            try:
                minidom.parseString(source)
            except:
                self.fail('Not well formed: ' + doc);
                break
        else:
            self.assertTrue(True);

########NEW FILE########
__FILENAME__ = test_expunge
#!/usr/bin/env python
import unittest, os, glob, shutil, time
from planet.spider import filename
from planet import feedparser, config
from planet.expunge import expungeCache
from xml.dom import minidom
import planet

workdir = 'tests/work/expunge/cache'
sourcesdir = 'tests/work/expunge/cache/sources'
testentries = 'tests/data/expunge/test*.entry'
testfeeds = 'tests/data/expunge/test*.atom'
configfile = 'tests/data/expunge/config.ini'

class ExpungeTest(unittest.TestCase):
    def setUp(self):
        # silence errors
        self.original_logger = planet.logger
        planet.getLogger('CRITICAL',None)

        try:
            os.makedirs(workdir)
            os.makedirs(sourcesdir)
        except:
            self.tearDown()
            os.makedirs(workdir)
            os.makedirs(sourcesdir)
             
    def tearDown(self):
        shutil.rmtree(workdir)
        os.removedirs(os.path.split(workdir)[0])
        planet.logger = self.original_logger

    def test_expunge(self):
        config.load(configfile)

        # create test entries in cache with correct timestamp
        for entry in glob.glob(testentries):
            e=minidom.parse(entry)
            e.normalize()
            eid = e.getElementsByTagName('id')
            efile = filename(workdir, eid[0].childNodes[0].nodeValue)
            eupdated = e.getElementsByTagName('updated')[0].childNodes[0].nodeValue
            emtime = time.mktime(feedparser._parse_date_w3dtf(eupdated))
            if not eid or not eupdated: continue
            shutil.copyfile(entry, efile)
            os.utime(efile, (emtime, emtime))
  
        # create test feeds in cache
        sources = config.cache_sources_directory()
        for feed in glob.glob(testfeeds):
                f=minidom.parse(feed)
                f.normalize()
                fid = f.getElementsByTagName('id')
                if not fid: continue
                ffile = filename(sources, fid[0].childNodes[0].nodeValue)
                shutil.copyfile(feed, ffile)

        # verify that exactly nine entries + one source dir were produced
        files = glob.glob(workdir+"/*")
        self.assertEqual(10, len(files))

        # verify that exactly four feeds were produced in source dir
        files = glob.glob(sources+"/*")
        self.assertEqual(4, len(files))

        # expunge...
        expungeCache()

        # verify that five entries and one source dir are left
        files = glob.glob(workdir+"/*")
        self.assertEqual(6, len(files))

        # verify that the right five entries are left
        self.assertTrue(os.path.join(workdir,
            'bzr.mfd-consult.dk,2007,venus-expunge-test1,1') in files)
        self.assertTrue(os.path.join(workdir,
            'bzr.mfd-consult.dk,2007,venus-expunge-test2,1') in files)
        self.assertTrue(os.path.join(workdir,
            'bzr.mfd-consult.dk,2007,venus-expunge-test3,3') in files)
        self.assertTrue(os.path.join(workdir,
            'bzr.mfd-consult.dk,2007,venus-expunge-test4,2') in files)
        self.assertTrue(os.path.join(workdir,
            'bzr.mfd-consult.dk,2007,venus-expunge-test4,3') in files)

########NEW FILE########
__FILENAME__ = test_filters
#!/usr/bin/env python

import unittest, xml.dom.minidom
from planet import shell, config, logger

class FilterTests(unittest.TestCase):

    def test_coral_cdn(self):
        testfile = 'tests/data/filter/coral_cdn.xml'
        filter = 'coral_cdn_filter.py'

        output = shell.run(filter, open(testfile).read(), mode="filter")
        dom = xml.dom.minidom.parseString(output)
        imgsrcs = [img.getAttribute('src') for img in dom.getElementsByTagName('img')]
        self.assertEqual('http://example.com.nyud.net:8080/foo.png', imgsrcs[0])
        self.assertEqual('http://example.com.1234.nyud.net:8080/foo.png', imgsrcs[1])
        self.assertEqual('http://u:p@example.com.nyud.net:8080/foo.png', imgsrcs[2])
        self.assertEqual('http://u:p@example.com.1234.nyud.net:8080/foo.png', imgsrcs[3])

    def test_excerpt_images1(self):
        config.load('tests/data/filter/excerpt-images.ini')
        self.verify_images()

    def test_excerpt_images2(self):
        config.load('tests/data/filter/excerpt-images2.ini')
        self.verify_images()

    def verify_images(self):
        testfile = 'tests/data/filter/excerpt-images.xml'
        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        dom = xml.dom.minidom.parseString(output)
        excerpt = dom.getElementsByTagName('planet:excerpt')[0]
        anchors = excerpt.getElementsByTagName('a')
        hrefs = [a.getAttribute('href') for a in anchors]
        texts = [a.lastChild.nodeValue for a in anchors]

        self.assertEqual(['inner','outer1','outer2'], hrefs)
        self.assertEqual(['bar','bar','<img>'], texts)

    def test_excerpt_lorem_ipsum(self):
        testfile = 'tests/data/filter/excerpt-lorem-ipsum.xml'
        config.load('tests/data/filter/excerpt-lorem-ipsum.ini')

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        dom = xml.dom.minidom.parseString(output)
        excerpt = dom.getElementsByTagName('planet:excerpt')[0]
        self.assertEqual(u'Lorem ipsum dolor sit amet, consectetuer ' +
            u'adipiscing elit. Nullam velit. Vivamus tincidunt, erat ' +
            u'in \u2026', excerpt.firstChild.firstChild.nodeValue)

    def test_excerpt_lorem_ipsum_summary(self):
        testfile = 'tests/data/filter/excerpt-lorem-ipsum.xml'
        config.load('tests/data/filter/excerpt-lorem-ipsum.ini')
        config.parser.set('excerpt.py', 'target', 'atom:summary')

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        dom = xml.dom.minidom.parseString(output)
        excerpt = dom.getElementsByTagName('summary')[0]
        self.assertEqual(u'Lorem ipsum dolor sit amet, consectetuer ' +
            u'adipiscing elit. Nullam velit. Vivamus tincidunt, erat ' +
            u'in \u2026', excerpt.firstChild.firstChild.nodeValue)

    def test_stripAd_yahoo(self):
        testfile = 'tests/data/filter/stripAd-yahoo.xml'
        config.load('tests/data/filter/stripAd-yahoo.ini')

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        dom = xml.dom.minidom.parseString(output)
        excerpt = dom.getElementsByTagName('content')[0]
        self.assertEqual(u'before--after',
            excerpt.firstChild.firstChild.nodeValue)

    def test_xpath_filter1(self):
        config.load('tests/data/filter/xpath-sifter.ini')
        self.verify_xpath()

    def test_xpath_filter2(self):
        config.load('tests/data/filter/xpath-sifter2.ini')
        self.verify_xpath()

    def verify_xpath(self):
        testfile = 'tests/data/filter/category-one.xml'

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        self.assertEqual('', output)

        testfile = 'tests/data/filter/category-two.xml'

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        self.assertNotEqual('', output)

    def test_regexp_filter(self):
        config.load('tests/data/filter/regexp-sifter.ini')

        testfile = 'tests/data/filter/category-one.xml'

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        self.assertEqual('', output)

        testfile = 'tests/data/filter/category-two.xml'

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        self.assertNotEqual('', output)

    def test_regexp_filter2(self):
        config.load('tests/data/filter/regexp-sifter2.ini')

        testfile = 'tests/data/filter/category-one.xml'

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        self.assertNotEqual('', output)

        testfile = 'tests/data/filter/category-two.xml'

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        self.assertEqual('', output)

    def test_xhtml2html_filter(self):
        testfile = 'tests/data/filter/index.html'
        filter = 'xhtml2html.plugin?quote_attr_values=True'
        output = shell.run(filter, open(testfile).read(), mode="filter")
        self.assertTrue(output.find('/>')<0)
        self.assertTrue(output.find('</script>')>=0)

try:
    from subprocess import Popen, PIPE

    _no_sed = True
    if _no_sed:
        try:
            # Python 2.5 bug 1704790 workaround (alas, Unix only)
            import commands
            if commands.getstatusoutput('sed --version')[0]==0: _no_sed = False 
        except:
            pass

    if _no_sed:
        try:
            sed = Popen(['sed','--version'],stdout=PIPE,stderr=PIPE)
            sed.communicate()
            if sed.returncode == 0: _no_sed = False
        except WindowsError:
            pass

    if _no_sed:
        logger.warn("sed is not available => can't test stripAd_yahoo")
        del FilterTests.test_stripAd_yahoo      

    try:
        import libxml2
    except:
        logger.warn("libxml2 is not available => can't test xpath_sifter")
        del FilterTests.test_xpath_filter1
        del FilterTests.test_xpath_filter2

except ImportError:
    logger.warn("Popen is not available => can't test standard filters")
    for method in dir(FilterTests):
        if method.startswith('test_'):  delattr(FilterTests,method)

########NEW FILE########
__FILENAME__ = test_filter_django
#!/usr/bin/env python

import os.path
import unittest, xml.dom.minidom, datetime

from planet import config, logger
from planet.shell import dj

class DjangoFilterTests(unittest.TestCase):

    def test_django_filter(self):
        config.load('tests/data/filter/django/test.ini')
        results = dj.tmpl.template_info("<feed/>")
        self.assertEqual(results['name'], 'Django on Venus')

    def test_django_date_type(self):
        config.load('tests/data/filter/django/test.ini')
        results = dj.tmpl.template_info("<feed/>")
        self.assertEqual(type(results['date']), datetime.datetime)

    def test_django_entry_title(self):
        config.load('tests/data/filter/django/test.ini')
        feed = open('tests/data/filter/django/test.xml')
        input = feed.read(); feed.close()
        results = dj.run(
            os.path.realpath('tests/data/filter/django/title.html.dj'), input)
        self.assertEqual(results, u"\xa1Atom-Powered Robots Run Amok!\n")

    def test_django_config_context(self):
        config.load('tests/data/filter/django/test.ini')
        feed = open('tests/data/filter/django/test.xml')
        input = feed.read(); feed.close()
        results = dj.run(
            os.path.realpath('tests/data/filter/django/config.html.dj'), input)
        self.assertEqual(results, "Django on Venus\n")
        

try:
    from django.conf import settings
except ImportError:
    logger.warn("Django is not available => can't test django filters")
    for method in dir(DjangoFilterTests):
        if method.startswith('test_'):  delattr(DjangoFilterTests,method)

########NEW FILE########
__FILENAME__ = test_filter_genshi
#!/usr/bin/env python

import unittest, xml.dom.minidom
from planet import shell, config, logger

class GenshiFilterTests(unittest.TestCase):

    def test_addsearch_filter(self):
        testfile = 'tests/data/filter/index.html'
        filter = 'addsearch.genshi'
        output = shell.run(filter, open(testfile).read(), mode="filter")
        self.assertTrue(output.find('<h2>Search</h2>')>=0)
        self.assertTrue(output.find('<form><input name="q"/></form>')>=0)
        self.assertTrue(output.find(' href="http://planet.intertwingly.net/opensearchdescription.xml"')>=0)
        self.assertTrue(output.find('</script>')>=0)

try:
    import genshi
except:
    logger.warn("Genshi is not available => can't test genshi filters")
    for method in dir(GenshiFilterTests):
        if method.startswith('test_'):  delattr(GenshiFilterTests,method)

########NEW FILE########
__FILENAME__ = test_filter_tmpl
#!/usr/bin/env python

import unittest, os, sys, glob, new, re, StringIO, time
from planet import config
from planet.shell import tmpl

testfiles = 'tests/data/filter/tmpl/%s.%s'

class FilterTmplTest(unittest.TestCase):
    desc_feed_re = re.compile("Description:\s*(.*?)\s*Expect:\s*(.*)\s*-->")
    desc_config_re = re.compile(";\s*Description:\s*(.*?)\s*;\s*Expect:\s*(.*)")
    simple_re = re.compile("^(\S+) == (u?'[^']*'|\([0-9, ]+\))$")

    def eval_feed(self, name):
        # read the test case
        try:
            testcase = open(testfiles % (name,'xml'))
            data = testcase.read()
            description, expect = self.desc_feed_re.search(data).groups()
            testcase.close()
        except:
            raise RuntimeError, "can't parse %s" % name

        # map to template info
        results = tmpl.template_info(data)

        # verify the results
        if not self.simple_re.match(expect):
            self.assertTrue(eval(expect, results), expect)
        else:
            lhs, rhs = self.simple_re.match(expect).groups()
            self.assertEqual(eval(rhs), eval(lhs, results))

    def eval_config(self, name):
        # read the test case
        try:
            testcase = open(testfiles % (name,'ini'))
            data = testcase.read()
            description, expect = self.desc_config_re.search(data).groups()
            testcase.close()
        except:
            raise RuntimeError, "can't parse %s" % name

        # map to template info
        config.load(testfiles % (name,'ini'))
        results = tmpl.template_info("<feed/>")

        # verify the results
        if not self.simple_re.match(expect):
            self.assertTrue(eval(expect, results), expect)
        else:
            lhs, rhs = self.simple_re.match(expect).groups()
            self.assertEqual(eval(rhs), eval(lhs, results))

# build a test method for each xml test file
for testcase in glob.glob(testfiles % ('*','xml')):
    root = os.path.splitext(os.path.basename(testcase))[0]
    func = lambda self, name=root: self.eval_feed(name)
    method = new.instancemethod(func, None, FilterTmplTest)
    setattr(FilterTmplTest, "test_" + root, method)

# build a test method for each ini test file
for testcase in glob.glob(testfiles % ('*','ini')):
    root = os.path.splitext(os.path.basename(testcase))[0]
    func = lambda self, name=root: self.eval_config(name)
    method = new.instancemethod(func, None, FilterTmplTest)
    setattr(FilterTmplTest, "test_" + root, method)

########NEW FILE########
__FILENAME__ = test_filter_xslt
#!/usr/bin/env python

import unittest, xml.dom.minidom
from planet import shell, config, logger

class XsltFilterTests(unittest.TestCase):

    def test_xslt_filter(self):
        config.load('tests/data/filter/translate.ini')
        testfile = 'tests/data/filter/category-one.xml'

        input = open(testfile).read()
        output = shell.run(config.filters()[0], input, mode="filter")
        dom = xml.dom.minidom.parseString(output)
        catterm = dom.getElementsByTagName('category')[0].getAttribute('term')
        self.assertEqual('OnE', catterm)

    def test_addsearch_filter(self):
        testfile = 'tests/data/filter/index.html'
        filter = 'addsearch.xslt'
        output = shell.run(filter, open(testfile).read(), mode="filter")
        self.assertTrue(output.find('<h2>Search</h2>')>=0)
        self.assertTrue(output.find('<form><input name="q"/></form>')>=0)
        self.assertTrue(output.find(' href="http://planet.intertwingly.net/opensearchdescription.xml"')>=0)
        self.assertTrue(output.find('</script>')>=0)

try:
    import libxslt
except:
    try:
        try:
            # Python 2.5 bug 1704790 workaround (alas, Unix only)
            import commands
            if commands.getstatusoutput('xsltproc --version')[0] != 0:
                raise ImportError
        except:
            from subprocess import Popen, PIPE
            xsltproc=Popen(['xsltproc','--version'],stdout=PIPE,stderr=PIPE)
            xsltproc.communicate()
            if xsltproc.returncode != 0: raise ImportError
    except:
        logger.warn("libxslt is not available => can't test xslt filters")
        del XsltFilterTests.test_xslt_filter
        del XsltFilterTests.test_addsearch_filter

########NEW FILE########
__FILENAME__ = test_foaf
#!/usr/bin/env python

import unittest, os, shutil
from planet.foaf import foaf2config
from ConfigParser import ConfigParser
from planet import config, logger

workdir = 'tests/work/config/cache'

blogroll = 'http://journal.dajobe.org/journal/2003/07/semblogs/bloggers.rdf'
testfeed = "http://dannyayers.com/feed/rdf"
test_foaf_document = '''
<rdf:RDF
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:foaf="http://xmlns.com/foaf/0.1/"
  xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
  xmlns:rss="http://purl.org/rss/1.0/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">

<foaf:Agent rdf:nodeID="id2245354"> 
<foaf:name>Danny Ayers</foaf:name> 
<rdf:type rdf:resource="http://xmlns.com/foaf/0.1/Person"/> 
<foaf:weblog> 
<foaf:Document rdf:about="http://dannyayers.com/"> 
<dc:title>Raw Blog by Danny Ayers</dc:title> 
<rdfs:seeAlso> 
<rss:channel rdf:about="http://dannyayers.com/feed/rdf"> 
<foaf:maker rdf:nodeID="id2245354"/> 
<foaf:topic rdf:resource="http://www.w3.org/2001/sw/"/> 
<foaf:topic rdf:resource="http://www.w3.org/RDF/"/> 
</rss:channel> 
</rdfs:seeAlso> 
</foaf:Document> 
</foaf:weblog> 
<foaf:interest rdf:resource="http://www.w3.org/2001/sw/"/> 
<foaf:interest rdf:resource="http://www.w3.org/RDF/"/> 
</foaf:Agent> 

</rdf:RDF> 
'''.strip()

class FoafTest(unittest.TestCase):
    """
    Test the foaf2config function
    """

    def setUp(self):
        self.config = ConfigParser()
        self.config.add_section(blogroll)

    def tearDown(self):
        if os.path.exists(workdir):
            shutil.rmtree(workdir)
            os.removedirs(os.path.split(workdir)[0])

    #
    # Tests
    #

    def test_foaf_document(self):
        foaf2config(test_foaf_document, self.config)
        self.assertEqual('Danny Ayers', self.config.get(testfeed, 'name'))

    def test_no_foaf_name(self):
        test = test_foaf_document.replace('foaf:name','foaf:title')
        foaf2config(test, self.config)
        self.assertEqual('Raw Blog by Danny Ayers',
           self.config.get(testfeed, 'name'))

    def test_no_weblog(self):
        test = test_foaf_document.replace('rdfs:seeAlso','rdfs:seealso')
        foaf2config(test, self.config)
        self.assertFalse(self.config.has_section(testfeed))

    def test_invalid_xml_before(self):
        test = '\n<?xml version="1.0" encoding="UTF-8"?>' + test_foaf_document
        foaf2config(test, self.config)
        self.assertFalse(self.config.has_section(testfeed))

    def test_invalid_xml_after(self):
        test = test_foaf_document.strip()[:-1]
        foaf2config(test, self.config)
        self.assertEqual('Danny Ayers', self.config.get(testfeed, 'name'))

    def test_online_accounts(self):
        config.load('tests/data/config/foaf.ini')
        feeds = config.subscriptions()
        feeds.sort()
        self.assertEqual(['http://api.flickr.com/services/feeds/' +
            'photos_public.gne?id=77366516@N00',
            'http://del.icio.us/rss/eliast',
            'http://torrez.us/feed/rdf'], feeds)

    def test_multiple_subscriptions(self):
        config.load('tests/data/config/foaf-multiple.ini')
        self.assertEqual(2,len(config.reading_lists()))
        feeds = config.subscriptions()
        feeds.sort()
        self.assertEqual(5,len(feeds))
        self.assertEqual(['http://api.flickr.com/services/feeds/' +
            'photos_public.gne?id=77366516@N00',
            'http://api.flickr.com/services/feeds/' +
            'photos_public.gne?id=SOMEID',
            'http://del.icio.us/rss/SOMEID',
            'http://del.icio.us/rss/eliast',
            'http://torrez.us/feed/rdf'], feeds)

    def test_recursive(self):
        config.load('tests/data/config/foaf-deep.ini')
        feeds = config.subscriptions()
        feeds.sort()
        self.assertEqual(['http://api.flickr.com/services/feeds/photos_public.gne?id=77366516@N00',
        'http://del.icio.us/rss/eliast', 'http://del.icio.us/rss/leef',
        'http://del.icio.us/rss/rubys', 'http://intertwingly.net/blog/atom.xml',
        'http://thefigtrees.net/lee/life/atom.xml',
        'http://torrez.us/feed/rdf'], feeds)

# these tests only make sense if libRDF is installed
try:
    import RDF
except:
    logger.warn("Redland RDF is not available => can't test FOAF reading lists")
    for key in FoafTest.__dict__.keys():
        if key.startswith('test_'): delattr(FoafTest, key)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_idindex
#!/usr/bin/env python

import unittest, planet
from planet import idindex, config

class idIndexTest(unittest.TestCase):

    def setUp(self):
        # silence errors
        self.original_logger = planet.logger
        planet.getLogger('CRITICAL',None)

    def tearDown(self):
        idindex.destroy()
        planet.logger = self.original_logger

    def test_unicode(self):
        from planet.spider import filename
        index = idindex.create()
        iri = 'http://www.\xe8\xa9\xb9\xe5\xa7\x86\xe6\x96\xaf.com/'
        index[filename('', iri)] = 'data'
        index[filename('', iri.decode('utf-8'))] = 'data'
        index[filename('', u'1234')] = 'data'
        index.close()
        
    def test_index_spider(self):
        import test_spider
        config.load(test_spider.configfile)

        index = idindex.create()
        self.assertEqual(0, len(index))
        index.close()

        from planet.spider import spiderPlanet
        try:
            spiderPlanet()

            index = idindex.open()
            self.assertEqual(12, len(index))
            self.assertEqual('tag:planet.intertwingly.net,2006:testfeed1', index['planet.intertwingly.net,2006,testfeed1,1'])
            self.assertEqual('http://intertwingly.net/code/venus/tests/data/spider/testfeed3.rss', index['planet.intertwingly.net,2006,testfeed3,1'])
            index.close()
        finally:
            import os, shutil
            shutil.rmtree(test_spider.workdir)
            os.removedirs(os.path.split(test_spider.workdir)[0])

    def test_index_splice(self):
        import test_splice
        config.load(test_splice.configfile)
        index = idindex.create()

        self.assertEqual(12, len(index))
        self.assertEqual('tag:planet.intertwingly.net,2006:testfeed1', index['planet.intertwingly.net,2006,testfeed1,1'])
        self.assertEqual('http://intertwingly.net/code/venus/tests/data/spider/testfeed3.rss', index['planet.intertwingly.net,2006,testfeed3,1'])

        for key in index.keys():
            value = index[key]
            if value.find('testfeed2')>0: index[key] = value.swapcase()
        index.close()

        from planet.splice import splice
        doc = splice()

        self.assertEqual(8,len(doc.getElementsByTagName('entry')))
        self.assertEqual(4,len(doc.getElementsByTagName('planet:source')))
        self.assertEqual(12,len(doc.getElementsByTagName('planet:name')))

try:
    module = 'dbhash'
except ImportError:
    planet.logger.warn("dbhash is not available => can't test id index")
    for method in dir(idIndexTest):
        if method.startswith('test_'):  delattr(idIndexTest,method)

########NEW FILE########
__FILENAME__ = test_opml
#!/usr/bin/env python

import unittest
from planet.opml import opml2config
from ConfigParser import ConfigParser

class OpmlTest(unittest.TestCase):
    """
    Test the opml2config function
    """

    def setUp(self):
        self.config = ConfigParser()

    #
    # Element
    #

    def test_outline_element(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text="sample feed"/>''', self.config)
        self.assertEqual('sample feed',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_wrong_element(self):
        opml2config('''<feed    type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text="sample feed"/>''', self.config)
        self.assertFalse(self.config.has_section("http://example.com/feed.xml"))

    def test_illformed_xml_before(self):
        opml2config('''<bad stuff before>
                       <outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text="sample feed"/>''', self.config)
        self.assertEqual('sample feed',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_illformed_xml_after(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text="sample feed"/>
                       <bad stuff after>''', self.config)
        self.assertEqual('sample feed',
           self.config.get("http://example.com/feed.xml", 'name'))

    #
    # Type
    #

    def test_type_missing(self):
        opml2config('''<outline
                                xmlUrl="http://example.com/feed.xml"
                                text="sample feed"/>''', self.config)
        self.assertEqual('sample feed',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_type_uppercase(self):
        opml2config('''<outline type="RSS"
                                xmlUrl="http://example.com/feed.xml"
                                text="sample feed"/>''', self.config)
        self.assertEqual('sample feed',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_type_atom(self):
        opml2config('''<outline type="atom"
                                xmlUrl="http://example.com/feed.xml"
                                text="sample feed"/>''', self.config)
        self.assertEqual('sample feed',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_wrong_type(self):
        opml2config('''<outline type="other"
                                xmlUrl="http://example.com/feed.xml"
                                text="sample feed"/>''', self.config)
        self.assertFalse(self.config.has_section("http://example.com/feed.xml"))

    def test_WordPress_link_manager(self):
        # http://www.wasab.dk/morten/blog/archives/2006/10/22/wp-venus
        opml2config('''<outline type="link"
                                xmlUrl="http://example.com/feed.xml"
                                text="sample feed"/>''', self.config)
        self.assertEqual('sample feed',
           self.config.get("http://example.com/feed.xml", 'name'))

    #
    # xmlUrl
    #

    def test_xmlurl_wrong_case(self):
        opml2config('''<outline type="rss"
                                xmlurl="http://example.com/feed.xml"
                                text="sample feed"/>''', self.config)
        self.assertEqual('sample feed',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_missing_xmlUrl(self):
        opml2config('''<outline type="rss"
                                text="sample feed"/>''', self.config)
        self.assertFalse(self.config.has_section("http://example.com/feed.xml"))

    def test_blank_xmlUrl(self):
        opml2config('''<outline type="rss"
                                xmlUrl=""
                                text="sample feed"/>''', self.config)
        self.assertFalse(self.config.has_section(""))

    #
    # text
    #

    def test_title_attribute(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                title="sample feed"/>''', self.config)
        self.assertEqual('sample feed',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_missing_text(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                />''', self.config)
        self.assertFalse(self.config.has_section("http://example.com/feed.xml"))

    def test_blank_text_no_title(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text=""/>''', self.config)
        self.assertFalse(self.config.has_section("http://example.com/feed.xml"))

    def test_blank_text_with_title(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text=""
                                title="sample feed"/>''', self.config)
        self.assertEqual('sample feed',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_blank_text_blank_title(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text=""
                                title=""/>''', self.config)
        self.assertFalse(self.config.has_section("http://example.com/feed.xml"))

    def test_text_utf8(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text="Se\xc3\xb1or Frog\xe2\x80\x99s"/>''',
                    self.config)
        self.assertEqual('Se\xc3\xb1or Frog\xe2\x80\x99s',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_text_win_1252(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text="Se\xf1or Frog\x92s"/>''', self.config)
        self.assertEqual('Se\xc3\xb1or Frog\xe2\x80\x99s',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_text_entity(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text="Se&ntilde;or Frog&rsquo;s"/>''', self.config)
        self.assertEqual('Se\xc3\xb1or Frog\xe2\x80\x99s',
           self.config.get("http://example.com/feed.xml", 'name'))

    def test_text_double_escaped(self):
        opml2config('''<outline type="rss"
                                xmlUrl="http://example.com/feed.xml"
                                text="Se&amp;ntilde;or Frog&amp;rsquo;s"/>''', self.config)
        self.assertEqual('Se\xc3\xb1or Frog\xe2\x80\x99s',
           self.config.get("http://example.com/feed.xml", 'name'))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_reconstitute
#!/usr/bin/env python

import unittest, os, sys, glob, new, re, StringIO, time
from planet import feedparser
from planet.reconstitute import reconstitute
from planet.scrub import scrub

testfiles = 'tests/data/reconstitute/%s.xml'

class ReconstituteTest(unittest.TestCase):
    desc_re = re.compile("Description:\s*(.*?)\s*Expect:\s*(.*)\s*-->")
    simple_re = re.compile("^(\S+) == (u?'[^']*'|\([0-9, ]+\))$")

    def eval(self, name):
        # read the test case
        try:
            testcase = open(testfiles % name)
            data = testcase.read()
            description, expect = self.desc_re.search(data).groups()
            testcase.close()
        except:
            raise RuntimeError, "can't parse %s" % name

        # parse and reconstitute to a string
        work = StringIO.StringIO()
        results = feedparser.parse(data)
        scrub(testfiles%name, results)
        reconstitute(results, results.entries[0]).writexml(work)

        # verify the results
        results = feedparser.parse(work.getvalue().encode('utf-8'))
        if 'illegal' not in name:
            self.assertFalse(results.bozo, 'xml is well formed')
        if not self.simple_re.match(expect):
            self.assertTrue(eval(expect, results.entries[0]), expect)
        else:
            lhs, rhs = self.simple_re.match(expect).groups()
            self.assertEqual(eval(rhs), eval(lhs, results.entries[0]))

# build a test method for each test file
for testcase in glob.glob(testfiles % '*'):
    root = os.path.splitext(os.path.basename(testcase))[0]
    func = lambda self, name=root: self.eval(name)
    method = new.instancemethod(func, None, ReconstituteTest)
    setattr(ReconstituteTest, "test_" + root, method)

########NEW FILE########
__FILENAME__ = test_rlists
#!/usr/bin/env python

import unittest, os, shutil
from planet import config, opml
from os.path import split
from glob import glob
from ConfigParser import ConfigParser

workdir = os.path.join('tests', 'work', 'config', 'cache')

class ReadingListTest(unittest.TestCase):
    def setUp(self):
        config.load('tests/data/config/rlist.ini')

    def tearDown(self):
        shutil.rmtree(workdir)
        os.removedirs(os.path.split(workdir)[0])

    # administrivia

    def test_feeds(self):
        feeds = [split(feed)[1] for feed in config.subscriptions()]
        feeds.sort()
        self.assertEqual(['testfeed0.atom', 'testfeed1a.atom',
            'testfeed2.atom', 'testfeed3.rss'], feeds)

    # dictionaries

    def test_feed_options(self):
        feeds = dict([(split(feed)[1],feed) for feed in config.subscriptions()])
        feed1 = feeds['testfeed1a.atom']
        self.assertEqual('one', config.feed_options(feed1)['name'])

        feed2 = feeds['testfeed2.atom']
        self.assertEqual('two', config.feed_options(feed2)['name'])

    # dictionaries

    def test_cache(self):
        cache = glob(os.path.join(workdir,'lists','*'))
        self.assertEqual(1,len(cache))

        parser = ConfigParser()
        parser.read(cache[0])

        feeds = [split(feed)[1] for feed in parser.sections()]
        feeds.sort()
        self.assertEqual(['opml.xml', 'testfeed0.atom', 'testfeed1a.atom',
            'testfeed2.atom', 'testfeed3.rss'], feeds)

########NEW FILE########
__FILENAME__ = test_scrub
#!/usr/bin/env python

import unittest, StringIO, time
from copy import deepcopy
from planet.scrub import scrub
from planet import feedparser, config

feed = '''
<feed xmlns='http://www.w3.org/2005/Atom' xml:base="http://example.com/">
  <author><name>F&amp;ouml;o</name></author>
  <entry xml:lang="en">
    <id>ignoreme</id>
    <author><name>F&amp;ouml;o</name></author>
    <updated>%d-12-31T23:59:59Z</updated>
    <title>F&amp;ouml;o</title>
    <summary>F&amp;ouml;o</summary>
    <content>F&amp;ouml;o</content>
    <link href="http://example.com/entry/1/"/>
    <source>
      <link href="http://example.com/feed/"/>
      <author><name>F&amp;ouml;o</name></author>
    </source>
  </entry>
</feed>
''' % (time.gmtime()[0] + 1)

configData = '''
[testfeed]
ignore_in_feed = 
future_dates = 

name_type = html
title_type = html
summary_type = html
content_type = html
'''

class ScrubTest(unittest.TestCase):

    def test_scrub_ignore(self):
        base = feedparser.parse(feed)

        self.assertTrue(base.entries[0].has_key('author'))
        self.assertTrue(base.entries[0].has_key('author_detail'))
        self.assertTrue(base.entries[0].has_key('id'))
        self.assertTrue(base.entries[0].has_key('updated'))
        self.assertTrue(base.entries[0].has_key('updated_parsed'))
        self.assertTrue(base.entries[0].summary_detail.has_key('language'))

        config.parser.readfp(StringIO.StringIO(configData))
        config.parser.set('testfeed', 'ignore_in_feed',
          'author id updated xml:lang')
        data = deepcopy(base)
        scrub('testfeed', data)

        self.assertFalse(data.entries[0].has_key('author'))
        self.assertFalse(data.entries[0].has_key('author_detail'))
        self.assertFalse(data.entries[0].has_key('id'))
        self.assertFalse(data.entries[0].has_key('updated'))
        self.assertFalse(data.entries[0].has_key('updated_parsed'))
        self.assertFalse(data.entries[0].summary_detail.has_key('language'))

    def test_scrub_type(self):
        base = feedparser.parse(feed)

        self.assertEqual('F&ouml;o', base.feed.author_detail.name)

        config.parser.readfp(StringIO.StringIO(configData))
        data = deepcopy(base)
        scrub('testfeed', data)

        self.assertEqual('F\xc3\xb6o', data.feed.author_detail.name)
        self.assertEqual('F\xc3\xb6o', data.entries[0].author_detail.name)
        self.assertEqual('F\xc3\xb6o', data.entries[0].source.author_detail.name)

        self.assertEqual('text/html', data.entries[0].title_detail.type)
        self.assertEqual('text/html', data.entries[0].summary_detail.type)
        self.assertEqual('text/html', data.entries[0].content[0].type)

    def test_scrub_future(self):
        base = feedparser.parse(feed)
        self.assertEqual(1, len(base.entries))
        self.assertTrue(base.entries[0].has_key('updated'))

        config.parser.readfp(StringIO.StringIO(configData))
        config.parser.set('testfeed', 'future_dates', 'ignore_date')
        data = deepcopy(base)
        scrub('testfeed', data)
        self.assertFalse(data.entries[0].has_key('updated'))

        config.parser.set('testfeed', 'future_dates', 'ignore_entry')
        data = deepcopy(base)
        scrub('testfeed', data)
        self.assertEqual(0, len(data.entries))

    def test_scrub_xmlbase(self):
        base = feedparser.parse(feed)
        self.assertEqual('http://example.com/',
             base.entries[0].title_detail.base)

        config.parser.readfp(StringIO.StringIO(configData))
        config.parser.set('testfeed', 'xml_base', 'feed_alternate')
        data = deepcopy(base)
        scrub('testfeed', data)
        self.assertEqual('http://example.com/feed/',
             data.entries[0].title_detail.base)

        config.parser.set('testfeed', 'xml_base', 'entry_alternate')
        data = deepcopy(base)
        scrub('testfeed', data)
        self.assertEqual('http://example.com/entry/1/',
             data.entries[0].title_detail.base)

        config.parser.set('testfeed', 'xml_base', 'base/')
        data = deepcopy(base)
        scrub('testfeed', data)
        self.assertEqual('http://example.com/base/',
             data.entries[0].title_detail.base)

        config.parser.set('testfeed', 'xml_base', 'http://example.org/data/')
        data = deepcopy(base)
        scrub('testfeed', data)
        self.assertEqual('http://example.org/data/',
             data.entries[0].title_detail.base)

########NEW FILE########
__FILENAME__ = test_spider
#!/usr/bin/env python

import unittest, os, glob, calendar, shutil, time
from planet.spider import filename, spiderPlanet, writeCache
from planet import feedparser, config
import planet

workdir = 'tests/work/spider/cache'
testfeed = 'tests/data/spider/testfeed%s.atom'
configfile = 'tests/data/spider/config.ini'

class SpiderTest(unittest.TestCase):
    def setUp(self):
        # silence errors
        self.original_logger = planet.logger
        planet.getLogger('CRITICAL',None)

        try:
             os.makedirs(workdir)
        except:
             self.tearDown()
             os.makedirs(workdir)
    
    def tearDown(self):
        shutil.rmtree(workdir)
        os.removedirs(os.path.split(workdir)[0])
        planet.logger = self.original_logger

    def test_filename(self):
        self.assertEqual(os.path.join('.', 'example.com,index.html'),
            filename('.', 'http://example.com/index.html'))
        self.assertEqual(os.path.join('.',
            'planet.intertwingly.net,2006,testfeed1,1'),
            filename('.', u'tag:planet.intertwingly.net,2006:testfeed1,1'))
        self.assertEqual(os.path.join('.',
            '00000000-0000-0000-0000-000000000000'),
            filename('.', u'urn:uuid:00000000-0000-0000-0000-000000000000'))

        # Requires Python 2.3
        try:
            import encodings.idna
        except:
            return
        self.assertEqual(os.path.join('.', 'xn--8ws00zhy3a.com'),
            filename('.', u'http://www.\u8a79\u59c6\u65af.com/'))

    def spiderFeed(self, feed_uri):
        feed_info = feedparser.parse('<feed/>')
        data = feedparser.parse(feed_uri)
        writeCache(feed_uri, feed_info, data)

    def verify_spiderFeed(self):
        files = glob.glob(workdir+"/*")
        files.sort()

        # verify that exactly four files + one sources dir were produced
        self.assertEqual(5, len(files))

        # verify that the file names are as expected
        self.assertTrue(os.path.join(workdir,
            'planet.intertwingly.net,2006,testfeed1,1') in files)

        # verify that the file timestamps match atom:updated
        data = feedparser.parse(files[2])
        self.assertEqual(['application/atom+xml'], [link.type
            for link in data.entries[0].source.links if link.rel=='self'])
        self.assertEqual('one', data.entries[0].source.planet_name)
        self.assertEqual('2006-01-03T00:00:00Z', data.entries[0].updated)
        self.assertEqual(os.stat(files[2]).st_mtime,
            calendar.timegm(data.entries[0].updated_parsed))

    def test_spiderFeed(self):
        config.load(configfile)
        self.spiderFeed(testfeed % '1b')
        self.verify_spiderFeed()

    def test_spiderFeed_retroactive_filter(self):
        config.load(configfile)
        self.spiderFeed(testfeed % '1b')
        self.assertEqual(5, len(glob.glob(workdir+"/*")))
        config.parser.set('Planet', 'filter', 'two')
        self.spiderFeed(testfeed % '1b')
        self.assertEqual(1, len(glob.glob(workdir+"/*")))

    def test_spiderFeed_blacklist(self):
        config.load(configfile)
        self.spiderFeed(testfeed % '1b')

        # verify that exactly four entries were produced
        self.assertEqual(4, len(glob.glob(workdir+"/planet*")))

        # verify that the file names are as expected
        self.assertTrue(os.path.exists(os.path.join(workdir,
            'planet.intertwingly.net,2006,testfeed1,1')))
        
        os.mkdir(os.path.join(workdir, "blacklist"))

        os.rename(os.path.join(workdir,
            'planet.intertwingly.net,2006,testfeed1,1'),
                  os.path.join(workdir, "blacklist", 
            'planet.intertwingly.net,2006,testfeed1,1'))

	self.spiderFeed(testfeed % '1b')
        self.assertEqual(3, len(glob.glob(workdir+"/planet*")))

    def test_spiderUpdate(self):
        config.load(configfile)
        self.spiderFeed(testfeed % '1a')
        self.spiderFeed(testfeed % '1b')
        self.verify_spiderFeed()

    def test_spiderFeedUpdatedEntries(self):
        config.load(configfile)
        self.spiderFeed(testfeed % '4')
        self.assertEqual(2, len(glob.glob(workdir+"/*")))
        data = feedparser.parse(workdir + 
            '/planet.intertwingly.net,2006,testfeed4')
        self.assertEqual(u'three', data.entries[0].content[0].value)

    def verify_spiderPlanet(self):
        files = glob.glob(workdir+"/*")

        # verify that exactly eight files + 1 source dir were produced
        self.assertEqual(14, len(files))

        # verify that the file names are as expected
        self.assertTrue(os.path.join(workdir,
            'planet.intertwingly.net,2006,testfeed1,1') in files)
        self.assertTrue(os.path.join(workdir,
            'planet.intertwingly.net,2006,testfeed2,1') in files)

        data = feedparser.parse(workdir + 
            '/planet.intertwingly.net,2006,testfeed3,1')
        self.assertEqual(['application/rss+xml'], [link.type
            for link in data.entries[0].source.links if link.rel=='self'])
        self.assertEqual('three', data.entries[0].source.author_detail.name)
        self.assertEqual('three', data.entries[0].source['planet_css-id'])

    def test_spiderPlanet(self):
        config.load(configfile)
        spiderPlanet()
        self.verify_spiderPlanet()

    def test_spiderThreads(self):
        config.load(configfile.replace('config','threaded'))
        _PORT = config.parser.getint('Planet','test_port')

        log = []
        from SimpleHTTPServer import SimpleHTTPRequestHandler
        class TestRequestHandler(SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                log.append(args)

        from threading import Thread
        class TestServerThread(Thread):
          def __init__(self):
              self.ready = 0
              self.done = 0
              Thread.__init__(self)
          def run(self):
              from BaseHTTPServer import HTTPServer
              httpd = HTTPServer(('',_PORT), TestRequestHandler)
              self.ready = 1
              while not self.done:
                  httpd.handle_request()

        httpd = TestServerThread()
        httpd.start()
        while not httpd.ready:
            time.sleep(0.1)

        try:
            spiderPlanet()
        finally:
            httpd.done = 1
            import urllib
            urllib.urlopen('http://127.0.0.1:%d/' % _PORT).read()

        status = [int(rec[1]) for rec in log if str(rec[0]).startswith('GET ')]
        status.sort()
        self.assertEqual([200,200,200,200,404], status)

        self.verify_spiderPlanet()

########NEW FILE########
__FILENAME__ = test_splice
#!/usr/bin/env python

import unittest
from planet.splice import splice, config

configfile = 'tests/data/splice/config.ini'

class SpliceTest(unittest.TestCase):

    def test_splice(self):
        config.load(configfile)
        doc = splice()
        self.assertEqual(12,len(doc.getElementsByTagName('entry')))
        self.assertEqual(4,len(doc.getElementsByTagName('planet:source')))
        self.assertEqual(16,len(doc.getElementsByTagName('planet:name')))

        self.assertEqual('test planet',
            doc.getElementsByTagName('title')[0].firstChild.nodeValue)

    def test_splice_unsub(self):
        config.load(configfile)
        config.parser.remove_section('tests/data/spider/testfeed2.atom')
        doc = splice()
        self.assertEqual(8,len(doc.getElementsByTagName('entry')))
        self.assertEqual(3,len(doc.getElementsByTagName('planet:source')))
        self.assertEqual(11,len(doc.getElementsByTagName('planet:name')))

    def test_splice_new_feed_items(self):
        config.load(configfile)
        config.parser.set('Planet','new_feed_items','3')
        doc = splice()
        self.assertEqual(9,len(doc.getElementsByTagName('entry')))
        self.assertEqual(4,len(doc.getElementsByTagName('planet:source')))
        self.assertEqual(13,len(doc.getElementsByTagName('planet:name')))

########NEW FILE########
__FILENAME__ = test_subconfig
#!/usr/bin/env python

from test_config_csv import ConfigCsvTest
from planet import config

class SubConfigTest(ConfigCsvTest):
    def setUp(self):
        config.load('tests/data/config/rlist-config.ini')

########NEW FILE########
__FILENAME__ = test_themes
#!/usr/bin/env python

import unittest
from planet import config
from os.path import split

class ThemesTest(unittest.TestCase):
    def setUp(self):
        config.load('tests/data/config/themed.ini')

    # template directories

    def test_template_directories(self):
        self.assertEqual(['foo', 'bar', 'asf', 'config', 'common'],
            [split(dir)[1] for dir in config.template_directories()])

    # administrivia

    def test_template(self):
        self.assertEqual(1, len([1 for file in config.template_files()
            if file == 'index.html.xslt']))

    def test_feeds(self):
        feeds = config.subscriptions()
        feeds.sort()
        self.assertEqual(['feed1', 'feed2'], feeds)

    # planet wide configuration

    def test_name(self):
        self.assertEqual('Test Configuration', config.name())

    def test_link(self):
        self.assertEqual('', config.link())

    # per template configuration

    def test_days_per_page(self):
        self.assertEqual(7, config.days_per_page('index.html.xslt'))
        self.assertEqual(0, config.days_per_page('atom.xml.xslt'))

    def test_items_per_page(self):
        self.assertEqual(50, config.items_per_page('index.html.xslt'))
        self.assertEqual(50, config.items_per_page('atom.xml.xslt'))

    def test_encoding(self):
        self.assertEqual('utf-8', config.encoding('index.html.xslt'))
        self.assertEqual('utf-8', config.encoding('atom.xml.xslt'))

    # dictionaries

    def test_feed_options(self):
        self.assertEqual('one', config.feed_options('feed1')['name'])
        self.assertEqual('two', config.feed_options('feed2')['name'])

    def test_template_options(self):
        option = config.template_options('index.html.xslt')
        self.assertEqual('7',  option['days_per_page'])
        self.assertEqual('50', option['items_per_page'])

########NEW FILE########
