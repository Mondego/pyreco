__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

# parsing arguments
parser = OptionParser()
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="distribute", default=False,
                   help="Use Distribute rather than Setuptools.")

parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

USE_DISTRIBUTE = options.distribute
args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    if USE_DISTRIBUTE:
        exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)
    else:
        exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                             ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if USE_DISTRIBUTE:
    requirement = 'distribute'
else:
    requirement = 'setuptools'

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse(requirement)).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse(requirement)).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import sys, os
import restkit

CURDIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(CURDIR, '..', '..'))
sys.path.append(os.path.join(CURDIR, '..'))
sys.path.append(os.path.join(CURDIR, '.'))

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinxtogithub']

templates_path = ['_templates']

source_suffix = '.rst'
master_doc = 'index'

project = u'restkit'
copyright = u'2008-2013 Benoît Chesneau <benoitc@e-engura.org>'

version = restkit.__version__
release = version


exclude_trees = ['_build']

if on_rtd:
    pygments_style = 'sphinx'
    html_theme = 'default'
else:
    pygments_style = 'fruity'
    html_theme = 'basic'
    html_theme_path = [""]


html_static_path = ['_static']

htmlhelp_basename = 'restkitdoc'

latex_documents = [
  ('index', 'restkit.tex', u'restkit Documentation',
   u'Benoît Chesneau', 'manual'),
]

########NEW FILE########
__FILENAME__ = sitemap_gen
#!/usr/bin/env python
#
# Copyright (c) 2004, 2005 Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
#
# * Neither the name of Google nor the names of its contributors may
#   be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#
# The sitemap_gen.py script is written in Python 2.2 and released to
# the open source community for continuous improvements under the BSD
# 2.0 new license, which can be found at:
#
#   http://www.opensource.org/licenses/bsd-license.php
#

__usage__ = \
"""A simple script to automatically produce sitemaps for a webserver,
in the Google Sitemap Protocol (GSP).

Usage: python sitemap_gen.py --config=config.xml [--help] [--testing]
            --config=config.xml, specifies config file location
            --help, displays usage message
            --testing, specified when user is experimenting
"""

# Please be careful that all syntax used in this file can be parsed on
# Python 1.5 -- this version check is not evaluated until after the
# entire file has been parsed.
import sys
if sys.hexversion < 0x02020000:
  print 'This script requires Python 2.2 or later.'
  print 'Currently run with version: %s' % sys.version
  sys.exit(1)

import fnmatch
import glob
import gzip
import md5
import os
import re
import stat
import time
import types
import urllib
import urlparse
import xml.sax

# True and False were introduced in Python2.2.2
try:
  testTrue=True
  del testTrue
except NameError:
  True=1
  False=0

# Text encodings
ENC_ASCII = 'ASCII'
ENC_UTF8  = 'UTF-8'
ENC_IDNA  = 'IDNA'
ENC_ASCII_LIST = ['ASCII', 'US-ASCII', 'US', 'IBM367', 'CP367', 'ISO646-US'
                  'ISO_646.IRV:1991', 'ISO-IR-6', 'ANSI_X3.4-1968',
                  'ANSI_X3.4-1986', 'CPASCII' ]
ENC_DEFAULT_LIST = ['ISO-8859-1', 'ISO-8859-2', 'ISO-8859-5']

# Available Sitemap types
SITEMAP_TYPES = ['web', 'mobile', 'news']

# General Sitemap tags
GENERAL_SITEMAP_TAGS = ['loc', 'changefreq', 'priority', 'lastmod']

# News specific tags
NEWS_SPECIFIC_TAGS = ['keywords', 'publication_date', 'stock_tickers']

# News Sitemap tags
NEWS_SITEMAP_TAGS = GENERAL_SITEMAP_TAGS + NEWS_SPECIFIC_TAGS

# Maximum number of urls in each sitemap, before next Sitemap is created
MAXURLS_PER_SITEMAP = 50000

# Suffix on a Sitemap index file
SITEINDEX_SUFFIX = '_index.xml'

# Regular expressions tried for extracting URLs from access logs.
ACCESSLOG_CLF_PATTERN = re.compile(
  r'.+\s+"([^\s]+)\s+([^\s]+)\s+HTTP/\d+\.\d+"\s+200\s+.*'
  )

# Match patterns for lastmod attributes
DATE_PATTERNS = map(re.compile, [
  r'^\d\d\d\d$',
  r'^\d\d\d\d-\d\d$',
  r'^\d\d\d\d-\d\d-\d\d$',
  r'^\d\d\d\d-\d\d-\d\dT\d\d:\d\dZ$',
  r'^\d\d\d\d-\d\d-\d\dT\d\d:\d\d[+-]\d\d:\d\d$',
  r'^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z$',
  r'^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?[+-]\d\d:\d\d$',
  ])

# Match patterns for changefreq attributes
CHANGEFREQ_PATTERNS = [
  'always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never'
  ]

# XML formats
GENERAL_SITEINDEX_HEADER   = \
  '<?xml version="1.0" encoding="UTF-8"?>\n' \
  '<sitemapindex\n' \
  '  xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n' \
  '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n' \
  '  xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9\n' \
  '                      http://www.sitemaps.org/schemas/sitemap/0.9/' \
  'siteindex.xsd">\n'

NEWS_SITEINDEX_HEADER   = \
  '<?xml version="1.0" encoding="UTF-8"?>\n' \
  '<sitemapindex\n' \
  '  xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n' \
  '  xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"\n' \
  '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n' \
  '  xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9\n' \
  '                      http://www.sitemaps.org/schemas/sitemap/0.9/' \
  'siteindex.xsd">\n'

SITEINDEX_FOOTER   = '</sitemapindex>\n'
SITEINDEX_ENTRY    = \
  ' <sitemap>\n' \
  '  <loc>%(loc)s</loc>\n' \
  '  <lastmod>%(lastmod)s</lastmod>\n' \
  ' </sitemap>\n'
GENERAL_SITEMAP_HEADER     = \
  '<?xml version="1.0" encoding="UTF-8"?>\n' \
  '<urlset\n' \
  '  xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n' \
  '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n' \
  '  xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9\n' \
  '                      http://www.sitemaps.org/schemas/sitemap/0.9/' \
  'sitemap.xsd">\n'

NEWS_SITEMAP_HEADER	= \
  '<?xml version="1.0" encoding="UTF-8"?>\n' \
  '<urlset\n' \
  '  xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n' \
  '  xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"\n' \
  '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n' \
  '  xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9\n' \
  '                      http://www.sitemaps.org/schemas/sitemap/0.9/' \
  'sitemap.xsd">\n'

SITEMAP_FOOTER     = '</urlset>\n'
SITEURL_XML_PREFIX = ' <url>\n'
SITEURL_XML_SUFFIX = ' </url>\n'

NEWS_TAG_XML_PREFIX	= '  <news:news>\n'
NEWS_TAG_XML_SUFFIX	= '  </news:news>\n'

# Search engines to notify with the updated sitemaps
#
# This list is very non-obvious in what's going on.  Here's the gist:
# Each item in the list is a 6-tuple of items.  The first 5 are "almost"
# the same as the input arguments to urlparse.urlunsplit():
#   0 - schema
#   1 - netloc
#   2 - path
#   3 - query    <-- EXCEPTION: specify a query map rather than a string
#   4 - fragment
# Additionally, add item 5:
#   5 - query attribute that should be set to the new Sitemap URL
# Clear as mud, I know.
NOTIFICATION_SITES = [
  ('http', 'www.google.com', 'webmasters/sitemaps/ping', {}, '', 'sitemap'),
  ]


class Error(Exception):
  """
  Base exception class.  In this module we tend not to use our own exception
  types for very much, but they come in very handy on XML parsing with SAX.
  """
  pass
#end class Error


class SchemaError(Error):
  """Failure to process an XML file according to the schema we know."""
  pass
#end class SchemeError


class Encoder:
  """
  Manages wide-character/narrow-character conversions for just about all
  text that flows into or out of the script.

  You should always use this class for string coercion, as opposed to
  letting Python handle coercions automatically.  Reason: Python
  usually assumes ASCII (7-bit) as a default narrow character encoding,
  which is not the kind of data we generally deal with.

  General high-level methodologies used in sitemap_gen:

  [PATHS]
  File system paths may be wide or narrow, depending on platform.
  This works fine, just be aware of it and be very careful to not
  mix them.  That is, if you have to pass several file path arguments
  into a library call, make sure they are all narrow or all wide.
  This class has MaybeNarrowPath() which should be called on every
  file system path you deal with.

  [URLS]
  URL locations are stored in Narrow form, already escaped.  This has the
  benefit of keeping escaping and encoding as close as possible to the format
  we read them in.  The downside is we may end up with URLs that have
  intermingled encodings -- the root path may be encoded in one way
  while the filename is encoded in another.  This is obviously wrong, but
  it should hopefully be an issue hit by very few users.  The workaround
  from the user level (assuming they notice) is to specify a default_encoding
  parameter in their config file.

  [OTHER]
  Other text, such as attributes of the URL class, configuration options,
  etc, are generally stored in Unicode for simplicity.
  """

  def __init__(self):
    self._user      = None                  # User-specified default encoding
    self._learned   = []                    # Learned default encodings
    self._widefiles = False                 # File system can be wide

    # Can the file system be Unicode?
    try:
      self._widefiles = os.path.supports_unicode_filenames
    except AttributeError:
      try:
        self._widefiles = sys.getwindowsversion() == os.VER_PLATFORM_WIN32_NT
      except AttributeError:
        pass

    # Try to guess a working default
    try:
      encoding = sys.getfilesystemencoding()
      if encoding and not (encoding.upper() in ENC_ASCII_LIST):
        self._learned = [ encoding ]
    except AttributeError:
      pass

    if not self._learned:
      encoding = sys.getdefaultencoding()
      if encoding and not (encoding.upper() in ENC_ASCII_LIST):
        self._learned = [ encoding ]

    # If we had no guesses, start with some European defaults
    if not self._learned:
      self._learned = ENC_DEFAULT_LIST
  #end def __init__

  def SetUserEncoding(self, encoding):
    self._user = encoding
  #end def SetUserEncoding

  def NarrowText(self, text, encoding):
    """ Narrow a piece of arbitrary text """
    if type(text) != types.UnicodeType:
      return text

    # Try the passed in preference
    if encoding:
      try:
        result = text.encode(encoding)
        if not encoding in self._learned:
          self._learned.append(encoding)
        return result
      except UnicodeError:
        pass
      except LookupError:
        output.Warn('Unknown encoding: %s' % encoding)

    # Try the user preference
    if self._user:
      try:
        return text.encode(self._user)
      except UnicodeError:
        pass
      except LookupError:
        temp = self._user
        self._user = None
        output.Warn('Unknown default_encoding: %s' % temp)

    # Look through learned defaults, knock any failing ones out of the list
    while self._learned:
      try:
        return text.encode(self._learned[0])
      except:
        del self._learned[0]

    # When all other defaults are exhausted, use UTF-8
    try:
      return text.encode(ENC_UTF8)
    except UnicodeError:
      pass

    # Something is seriously wrong if we get to here
    return text.encode(ENC_ASCII, 'ignore')
  #end def NarrowText
  
  def MaybeNarrowPath(self, text):
    """ Paths may be allowed to stay wide """
    if self._widefiles:
      return text
    return self.NarrowText(text, None)
  #end def MaybeNarrowPath

  def WidenText(self, text, encoding):
    """ Widen a piece of arbitrary text """
    if type(text) != types.StringType:
      return text

    # Try the passed in preference
    if encoding:
      try:
        result = unicode(text, encoding)
        if not encoding in self._learned:
          self._learned.append(encoding)
        return result
      except UnicodeError:
        pass
      except LookupError:
        output.Warn('Unknown encoding: %s' % encoding)

    # Try the user preference
    if self._user:
      try:
        return unicode(text, self._user)
      except UnicodeError:
        pass
      except LookupError:
        temp = self._user
        self._user = None
        output.Warn('Unknown default_encoding: %s' % temp)

    # Look through learned defaults, knock any failing ones out of the list
    while self._learned:
      try:
        return unicode(text, self._learned[0])
      except:
        del self._learned[0]

    # When all other defaults are exhausted, use UTF-8
    try:
      return unicode(text, ENC_UTF8)
    except UnicodeError:
      pass

    # Getting here means it wasn't UTF-8 and we had no working default.
    # We really don't have anything "right" we can do anymore.
    output.Warn('Unrecognized encoding in text: %s' % text)
    if not self._user:
      output.Warn('You may need to set a default_encoding in your '
                  'configuration file.')
    return text.decode(ENC_ASCII, 'ignore')
  #end def WidenText
#end class Encoder
encoder = Encoder()


class Output:
  """
  Exposes logging functionality, and tracks how many errors
  we have thus output.

  Logging levels should be used as thus:
    Fatal     -- extremely sparingly
    Error     -- config errors, entire blocks of user 'intention' lost
    Warn      -- individual URLs lost
    Log(,0)   -- Un-suppressable text that's not an error
    Log(,1)   -- touched files, major actions
    Log(,2)   -- parsing notes, filtered or duplicated URLs
    Log(,3)   -- each accepted URL
  """

  def __init__(self):
    self.num_errors    = 0                   # Count of errors
    self.num_warns     = 0                   # Count of warnings

    self._errors_shown = {}                  # Shown errors
    self._warns_shown  = {}                  # Shown warnings
    self._verbose      = 0                   # Level of verbosity
  #end def __init__

  def Log(self, text, level):
    """ Output a blurb of diagnostic text, if the verbose level allows it """
    if text:
      text = encoder.NarrowText(text, None)
      if self._verbose >= level:
        print text
  #end def Log

  def Warn(self, text):
    """ Output and count a warning.  Suppress duplicate warnings. """
    if text:
      text = encoder.NarrowText(text, None)
      hash = md5.new(text).digest()
      if not self._warns_shown.has_key(hash):
        self._warns_shown[hash] = 1
        print '[WARNING] ' + text
      else:
        self.Log('(suppressed) [WARNING] ' + text, 3)
      self.num_warns = self.num_warns + 1
  #end def Warn

  def Error(self, text):
    """ Output and count an error.  Suppress duplicate errors. """
    if text:
      text = encoder.NarrowText(text, None)
      hash = md5.new(text).digest()
      if not self._errors_shown.has_key(hash):
        self._errors_shown[hash] = 1
        print '[ERROR] ' + text
      else:
        self.Log('(suppressed) [ERROR] ' + text, 3)
      self.num_errors = self.num_errors + 1
  #end def Error

  def Fatal(self, text):
    """ Output an error and terminate the program. """
    if text:
      text = encoder.NarrowText(text, None)
      print '[FATAL] ' + text
    else:
      print 'Fatal error.'
    sys.exit(1)
  #end def Fatal

  def SetVerbose(self, level):
    """ Sets the verbose level. """
    try:
      if type(level) != types.IntType:
        level = int(level)
      if (level >= 0) and (level <= 3):
        self._verbose = level
        return
    except ValueError:
      pass
    self.Error('Verbose level (%s) must be between 0 and 3 inclusive.' % level)
  #end def SetVerbose
#end class Output
output = Output()


class URL(object):
  """ URL is a smart structure grouping together the properties we
  care about for a single web reference. """
  __slots__ = 'loc', 'lastmod', 'changefreq', 'priority'

  def __init__(self):
    self.loc        = None                  # URL -- in Narrow characters
    self.lastmod    = None                  # ISO8601 timestamp of last modify
    self.changefreq = None                  # Text term for update frequency
    self.priority   = None                  # Float between 0 and 1 (inc)
  #end def __init__

  def __cmp__(self, other):
    if self.loc < other.loc:
      return -1
    if self.loc > other.loc:
      return 1
    return 0
  #end def __cmp__

  def TrySetAttribute(self, attribute, value):
    """ Attempt to set the attribute to the value, with a pretty try
    block around it.  """
    if attribute == 'loc':
      self.loc = self.Canonicalize(value)
    else:
      try:
        setattr(self, attribute, value)
      except AttributeError:
        output.Warn('Unknown URL attribute: %s' % attribute)
  #end def TrySetAttribute

  def IsAbsolute(loc):
    """ Decide if the URL is absolute or not """
    if not loc:
      return False
    narrow = encoder.NarrowText(loc, None)
    (scheme, netloc, path, query, frag) = urlparse.urlsplit(narrow)
    if (not scheme) or (not netloc):
      return False
    return True
  #end def IsAbsolute
  IsAbsolute = staticmethod(IsAbsolute)

  def Canonicalize(loc):
    """ Do encoding and canonicalization on a URL string """
    if not loc:
      return loc
    
    # Let the encoder try to narrow it
    narrow = encoder.NarrowText(loc, None)

    # Escape components individually
    (scheme, netloc, path, query, frag) = urlparse.urlsplit(narrow)
    unr    = '-._~'
    sub    = '!$&\'()*+,;='
    netloc = urllib.quote(netloc, unr + sub + '%:@/[]')
    path   = urllib.quote(path,   unr + sub + '%:@/')
    query  = urllib.quote(query,  unr + sub + '%:@/?')
    frag   = urllib.quote(frag,   unr + sub + '%:@/?')

    # Try built-in IDNA encoding on the netloc
    try:
      (ignore, widenetloc, ignore, ignore, ignore) = urlparse.urlsplit(loc)
      for c in widenetloc:
        if c >= unichr(128):
          netloc = widenetloc.encode(ENC_IDNA)
          netloc = urllib.quote(netloc, unr + sub + '%:@/[]')
          break
    except UnicodeError:
      # urlsplit must have failed, based on implementation differences in the
      # library.  There is not much we can do here, except ignore it.
      pass
    except LookupError:
      output.Warn('An International Domain Name (IDN) is being used, but this '
                  'version of Python does not have support for IDNA encoding. '
                  ' (IDNA support was introduced in Python 2.3)  The encoding '
                  'we have used instead is wrong and will probably not yield '
                  'valid URLs.')
    bad_netloc = False
    if '%' in netloc:
      bad_netloc = True

    # Put it all back together
    narrow = urlparse.urlunsplit((scheme, netloc, path, query, frag))

    # I let '%' through.  Fix any that aren't pre-existing escapes.
    HEXDIG = '0123456789abcdefABCDEF'
    list   = narrow.split('%')
    narrow = list[0]
    del list[0]
    for item in list:
      if (len(item) >= 2) and (item[0] in HEXDIG) and (item[1] in HEXDIG):
        narrow = narrow + '%' + item
      else:
        narrow = narrow + '%25' + item

    # Issue a warning if this is a bad URL
    if bad_netloc:
      output.Warn('Invalid characters in the host or domain portion of a URL: '
                  + narrow)

    return narrow
  #end def Canonicalize
  Canonicalize = staticmethod(Canonicalize)

  def VerifyDate(self, date, metatag):
    """Verify the date format is valid"""
    match = False
    if date:
      date = date.upper()
      for pattern in DATE_PATTERNS:
        match = pattern.match(date)
        if match:
          return True
      if not match:
        output.Warn('The value for %s does not appear to be in ISO8601 '
		    'format on URL: %s' % (metatag, self.loc))
        return False
  #end of VerifyDate

  def Validate(self, base_url, allow_fragment):
    """ Verify the data in this URL is well-formed, and override if not. """
    assert type(base_url) == types.StringType
    
    # Test (and normalize) the ref
    if not self.loc:
      output.Warn('Empty URL')
      return False
    if allow_fragment:
      self.loc = urlparse.urljoin(base_url, self.loc)
    if not self.loc.startswith(base_url):
      output.Warn('Discarded URL for not starting with the base_url: %s' %
                  self.loc)
      self.loc = None
      return False

    # Test the lastmod
    if self.lastmod:
      if not self.VerifyDate(self.lastmod, "lastmod"):
        self.lastmod = None

    # Test the changefreq
    if self.changefreq:
      match = False
      self.changefreq = self.changefreq.lower()
      for pattern in CHANGEFREQ_PATTERNS:
        if self.changefreq == pattern:
          match = True
          break
      if not match:
        output.Warn('Changefreq "%s" is not a valid change frequency on URL '
                    ': %s' % (self.changefreq, self.loc))
        self.changefreq = None

    # Test the priority
    if self.priority:
      priority = -1.0
      try:
        priority = float(self.priority)
      except ValueError:
        pass
      if (priority < 0.0) or (priority > 1.0):
        output.Warn('Priority "%s" is not a number between 0 and 1 inclusive '
                    'on URL: %s' % (self.priority, self.loc))
        self.priority = None

    return True
  #end def Validate

  def MakeHash(self):
    """ Provides a uniform way of hashing URLs """
    if not self.loc:
      return None
    if self.loc.endswith('/'):
      return md5.new(self.loc[:-1]).digest()
    return md5.new(self.loc).digest()
  #end def MakeHash

  def Log(self, prefix='URL', level=3):
    """ Dump the contents, empty or not, to the log. """
    out = prefix + ':'
    
    for attribute in self.__slots__:
      value = getattr(self, attribute)
      if not value:
        value = ''
      out = out + ('  %s=[%s]' % (attribute, value))

    output.Log('%s' % encoder.NarrowText(out, None), level)
  #end def Log

  def WriteXML(self, file):
    """ Dump non-empty contents to the output file, in XML format. """
    if not self.loc:
      return
    out = SITEURL_XML_PREFIX

    for attribute in self.__slots__:
      value = getattr(self, attribute)
      if value:
        if type(value) == types.UnicodeType:
          value = encoder.NarrowText(value, None)
        elif type(value) != types.StringType:
          value = str(value)
        value = xml.sax.saxutils.escape(value)
        out = out + ('  <%s>%s</%s>\n' % (attribute, value, attribute))
    
    out = out + SITEURL_XML_SUFFIX
    file.write(out)
  #end def WriteXML
#end class URL

class NewsURL(URL):
  """ NewsURL is a subclass of URL with News-Sitemap specific properties. """
  __slots__ = 'loc', 'lastmod', 'changefreq', 'priority', 'publication_date', \
	      'keywords', 'stock_tickers'

  def __init__(self):
    URL.__init__(self)
    self.publication_date	= None	# ISO8601 timestamp of publication date
    self.keywords 		= None  # Text keywords
    self.stock_tickers   	= None  # Text stock
  #end def __init__

  def Validate(self, base_url, allow_fragment):
    """ Verify the data in this News URL is well-formed, and override if not. """
    assert type(base_url) == types.StringType

    if not URL.Validate(self, base_url, allow_fragment):
      return False
 
    if not URL.VerifyDate(self, self.publication_date, "publication_date"):
      self.publication_date = None
 
    return True
  #end def Validate

  def WriteXML(self, file):
    """ Dump non-empty contents to the output file, in XML format. """
    if not self.loc:
      return
    out = SITEURL_XML_PREFIX
 
    # printed_news_tag indicates if news-specific metatags are present
    printed_news_tag = False
    for attribute in self.__slots__:
      value = getattr(self, attribute)
      if value:
        if type(value) == types.UnicodeType:
          value = encoder.NarrowText(value, None)
        elif type(value) != types.StringType:
          value = str(value)
          value = xml.sax.saxutils.escape(value)
        if attribute in NEWS_SPECIFIC_TAGS:
          if not printed_news_tag:
	    printed_news_tag = True
	    out = out + NEWS_TAG_XML_PREFIX
	  out = out + ('    <news:%s>%s</news:%s>\n' % (attribute, value, attribute))
        else:
	  out = out + ('  <%s>%s</%s>\n' % (attribute, value, attribute))
 
    if printed_news_tag:
      out = out + NEWS_TAG_XML_SUFFIX
    out = out + SITEURL_XML_SUFFIX
    file.write(out)
  #end def WriteXML
#end class NewsURL


class Filter:
  """
  A filter on the stream of URLs we find.  A filter is, in essence,
  a wildcard applied to the stream.  You can think of this as an
  operator that returns a tri-state when given a URL:

    True  -- this URL is to be included in the sitemap
    None  -- this URL is undecided
    False -- this URL is to be dropped from the sitemap
  """

  def __init__(self, attributes):
    self._wildcard  = None                  # Pattern for wildcard match
    self._regexp    = None                  # Pattern for regexp match
    self._pass      = False                 # "Drop" filter vs. "Pass" filter

    if not ValidateAttributes('FILTER', attributes,
                              ('pattern', 'type', 'action')):
      return

    # Check error count on the way in
    num_errors = output.num_errors

    # Fetch the attributes
    pattern = attributes.get('pattern')
    type    = attributes.get('type', 'wildcard')
    action  = attributes.get('action', 'drop')
    if type:
      type = type.lower()
    if action:
      action = action.lower()

    # Verify the attributes
    if not pattern:
      output.Error('On a filter you must specify a "pattern" to match')
    elif (not type) or ((type != 'wildcard') and (type != 'regexp')):
      output.Error('On a filter you must specify either \'type="wildcard"\' '
                   'or \'type="regexp"\'')
    elif (action != 'pass') and (action != 'drop'):
      output.Error('If you specify a filter action, it must be either '
                   '\'action="pass"\' or \'action="drop"\'')

    # Set the rule
    if action == 'drop':
      self._pass = False
    elif action == 'pass':
      self._pass = True

    if type == 'wildcard':
      self._wildcard = pattern
    elif type == 'regexp':
      try:
        self._regexp = re.compile(pattern)
      except re.error:
        output.Error('Bad regular expression: %s' %  pattern)

    # Log the final results iff we didn't add any errors
    if num_errors == output.num_errors:
      output.Log('Filter: %s any URL that matches %s "%s"' %
                 (action, type, pattern), 2)
  #end def __init__

  def Apply(self, url):
    """ Process the URL, as above. """
    if (not url) or (not url.loc):
      return None
    
    if self._wildcard:
      if fnmatch.fnmatchcase(url.loc, self._wildcard):
        return self._pass
      return None

    if self._regexp:
      if self._regexp.search(url.loc):
        return self._pass
      return None

    assert False # unreachable
  #end def Apply
#end class Filter


class InputURL:
  """
  Each Input class knows how to yield a set of URLs from a data source.

  This one handles a single URL, manually specified in the config file.
  """

  def __init__(self, attributes):
    self._url = None                        # The lonely URL

    if not ValidateAttributes('URL', attributes,
                                ('href', 'lastmod', 'changefreq', 'priority')):
      return
    
    url = URL()
    for attr in attributes.keys():
      if attr == 'href':
        url.TrySetAttribute('loc', attributes[attr])
      else:
        url.TrySetAttribute(attr, attributes[attr])

    if not url.loc:
      output.Error('Url entries must have an href attribute.')
      return
    
    self._url = url
    output.Log('Input: From URL "%s"' % self._url.loc, 2)
  #end def __init__

  def ProduceURLs(self, consumer):
    """ Produces URLs from our data source, hands them in to the consumer. """
    if self._url:
      consumer(self._url, True)
  #end def ProduceURLs
#end class InputURL


class InputURLList:
  """
  Each Input class knows how to yield a set of URLs from a data source.

  This one handles a text file with a list of URLs
  """

  def __init__(self, attributes):
    self._path      = None                  # The file path
    self._encoding  = None                  # Encoding of that file

    if not ValidateAttributes('URLLIST', attributes, ('path', 'encoding')):
      return
    
    self._path      = attributes.get('path')
    self._encoding  = attributes.get('encoding', ENC_UTF8)
    if self._path:
      self._path    = encoder.MaybeNarrowPath(self._path)
      if os.path.isfile(self._path):
        output.Log('Input: From URLLIST "%s"' % self._path, 2)
      else:
        output.Error('Can not locate file: %s' % self._path)
        self._path = None
    else:
      output.Error('Urllist entries must have a "path" attribute.')
  #end def __init__

  def ProduceURLs(self, consumer):
    """ Produces URLs from our data source, hands them in to the consumer. """

    # Open the file
    (frame, file) = OpenFileForRead(self._path, 'URLLIST')
    if not file:
      return

    # Iterate lines
    linenum = 0
    for line in file.readlines():
      linenum = linenum + 1

      # Strip comments and empty lines
      if self._encoding:
        line = encoder.WidenText(line, self._encoding)
      line = line.strip()
      if (not line) or line[0] == '#':
        continue
      
      # Split the line on space
      url = URL()
      cols = line.split(' ')
      for i in range(0,len(cols)):
        cols[i] = cols[i].strip()
      url.TrySetAttribute('loc', cols[0])

      # Extract attributes from the other columns
      for i in range(1,len(cols)):
        if cols[i]:
          try:
            (attr_name, attr_val) = cols[i].split('=', 1)
            url.TrySetAttribute(attr_name, attr_val)
          except ValueError:
            output.Warn('Line %d: Unable to parse attribute: %s' %
                        (linenum, cols[i]))

      # Pass it on
      consumer(url, False)

    file.close()
    if frame:
      frame.close()
  #end def ProduceURLs
#end class InputURLList


class InputNewsURLList:
  """
  Each Input class knows how to yield a set of URLs from a data source.

  This one handles a text file with a list of News URLs and their metadata
  """

  def __init__(self, attributes):
    self._path      = None                  # The file path
    self._encoding  = None                  # Encoding of that file
    self._tag_order = []                    # Order of URL metadata
 
    if not ValidateAttributes('URLLIST', attributes, ('path', 'encoding', \
		              'tag_order')):
      return
 
    self._path      = attributes.get('path')
    self._encoding  = attributes.get('encoding', ENC_UTF8)
    self._tag_order = attributes.get('tag_order')
 
    if self._path:
      self._path    = encoder.MaybeNarrowPath(self._path)
      if os.path.isfile(self._path):
        output.Log('Input: From URLLIST "%s"' % self._path, 2)
      else:
        output.Error('Can not locate file: %s' % self._path)
        self._path = None
    else:
      output.Error('Urllist entries must have a "path" attribute.')

    # parse tag_order into an array
    # tag_order_ascii created for more readable logging
    tag_order_ascii = []
    if self._tag_order:
      self._tag_order = self._tag_order.split(",")
      for i in range(0, len(self._tag_order)):
        element = self._tag_order[i].strip().lower()
	self._tag_order[i]= element
	tag_order_ascii.append(element.encode('ascii'))
      output.Log('Input: From URLLIST tag order is "%s"' % tag_order_ascii, 0)
    else:
      output.Error('News Urllist configuration file must contain tag_order '
		   'to define Sitemap metatags.')

    # verify all tag_order inputs are valid
    tag_order_dict = {}
    for tag in self._tag_order:
      tag_order_dict[tag] = ""
    if not ValidateAttributes('URLLIST', tag_order_dict, \
		    NEWS_SITEMAP_TAGS): 
      return

    # loc tag must be present
    loc_tag = False
    for tag in self._tag_order:
      if tag == 'loc':
        loc_tag = True
        break
    if not loc_tag:
      output.Error('News Urllist tag_order in configuration file '
		   'does not contain "loc" value: %s' % tag_order_ascii)
  #end def __init__

  def ProduceURLs(self, consumer):
    """ Produces URLs from our data source, hands them in to the consumer. """

    # Open the file
    (frame, file) = OpenFileForRead(self._path, 'URLLIST')
    if not file:
      return

    # Iterate lines
    linenum = 0
    for line in file.readlines():
      linenum = linenum + 1

      # Strip comments and empty lines
      if self._encoding:
        line = encoder.WidenText(line, self._encoding)
      line = line.strip()
      if (not line) or line[0] == '#':
        continue
      
      # Split the line on tabs
      url = NewsURL()
      cols = line.split('\t')
      for i in range(0,len(cols)):
        cols[i] = cols[i].strip()

      for i in range(0,len(cols)):
        if cols[i]:
          attr_value = cols[i]
	  if i < len(self._tag_order):
            attr_name = self._tag_order[i]
            try:
              url.TrySetAttribute(attr_name, attr_value)
            except ValueError:
              output.Warn('Line %d: Unable to parse attribute: %s' %
                        (linenum, cols[i]))

      # Pass it on
      consumer(url, False)

    file.close()
    if frame:
      frame.close()
  #end def ProduceURLs
#end class InputNewsURLList


class InputDirectory:
  """
  Each Input class knows how to yield a set of URLs from a data source.

  This one handles a directory that acts as base for walking the filesystem.
  """

  def __init__(self, attributes, base_url):
    self._path         = None               # The directory
    self._url          = None               # The URL equivalent
    self._default_file = None
    self._remove_empty_directories = False 

    if not ValidateAttributes('DIRECTORY', attributes, ('path', 'url',
                              'default_file', 'remove_empty_directories')):
      return

    # Prep the path -- it MUST end in a sep
    path = attributes.get('path')
    if not path:
      output.Error('Directory entries must have both "path" and "url" '
                  'attributes')
      return
    path = encoder.MaybeNarrowPath(path)
    if not path.endswith(os.sep):
      path = path + os.sep
    if not os.path.isdir(path):
      output.Error('Can not locate directory: %s' % path)
      return
    
    # Prep the URL -- it MUST end in a sep
    url = attributes.get('url')
    if not url:
      output.Error('Directory entries must have both "path" and "url" '
                  'attributes')
      return
    url = URL.Canonicalize(url)
    if not url.endswith('/'):
      url = url + '/'
    if not url.startswith(base_url):
      url = urlparse.urljoin(base_url, url)
      if not url.startswith(base_url):
        output.Error('The directory URL "%s" is not relative to the '
                    'base_url: %s' % (url, base_url))
        return

    # Prep the default file -- it MUST be just a filename
    file = attributes.get('default_file')
    if file:
      file = encoder.MaybeNarrowPath(file)
      if os.sep in file:
        output.Error('The default_file "%s" can not include path information.'
                     % file)
        file = None

    # Prep the remove_empty_directories -- default is false
    remove_empty_directories = attributes.get('remove_empty_directories')
    if remove_empty_directories:
      if (remove_empty_directories == '1') or \
         (remove_empty_directories.lower() == 'true'):
        remove_empty_directories = True
      elif (remove_empty_directories == '0') or \
	   (remove_empty_directories.lower() == 'false'):
        remove_empty_directories = False
      # otherwise the user set a non-default value
      else:
        output.Error('Configuration file remove_empty_directories '
		     'value is not recognized.  Value must be true or false.')
        return
    else:
      remove_empty_directories = False

    self._path         = path
    self._url          = url
    self._default_file = file
    self._remove_empty_directories = remove_empty_directories

    if file:
      output.Log('Input: From DIRECTORY "%s" (%s) with default file "%s"'
                 % (path, url, file), 2)
    else:
      output.Log('Input: From DIRECTORY "%s" (%s) with no default file'
                 % (path, url), 2)
  #end def __init__
  
     
  def ProduceURLs(self, consumer):
    """ Produces URLs from our data source, hands them in to the consumer. """
    if not self._path:
      return

    root_path = self._path
    root_URL  = self._url
    root_file = self._default_file
    remove_empty_directories = self._remove_empty_directories

    def HasReadPermissions(path):
      """ Verifies a given path has read permissions. """  
      stat_info = os.stat(path)
      mode = stat_info[stat.ST_MODE]
      if mode & stat.S_IREAD:
        return True
      else:
        return None

    def PerFile(dirpath, name):
      """
      Called once per file.
      Note that 'name' will occasionally be None -- for a directory itself
      """
      # Pull a timestamp
      url           = URL()
      isdir         = False
      try:
        if name:
          path      = os.path.join(dirpath, name)
        else:
          path      = dirpath
        isdir       = os.path.isdir(path)
        time        = None
        if isdir and root_file:
          file      = os.path.join(path, root_file)
          try:
            time    = os.stat(file)[stat.ST_MTIME];
          except OSError:
            pass
        if not time:
          time      = os.stat(path)[stat.ST_MTIME];
        url.lastmod = TimestampISO8601(time)
      except OSError:
        pass
      except ValueError:
        pass

      # Build a URL
      middle        = dirpath[len(root_path):]
      if os.sep != '/':
        middle = middle.replace(os.sep, '/')
      if middle:
        middle      = middle + '/'
      if name:
        middle      = middle + name
        if isdir:
          middle    = middle + '/'
      url.TrySetAttribute('loc', root_URL + encoder.WidenText(middle, None))

      # Suppress default files.  (All the way down here so we can log it.)
      if name and (root_file == name):
        url.Log(prefix='IGNORED (default file)', level=2)
        return
  
      # Suppress directories when remove_empty_directories="true"
      try:
        if isdir:
	  if HasReadPermissions(path):
            if remove_empty_directories == 'true' and \
	       len(os.listdir(path)) == 0:
              output.Log('IGNORED empty directory %s' % str(path), level=1)
              return
          elif path == self._path:
            output.Error('IGNORED configuration file directory input %s due '
			 'to file permissions' % self._path)
          else:
            output.Log('IGNORED files within directory %s due to file '
		       'permissions' % str(path), level=0)
      except OSError:
        pass
      except ValueError:
        pass
 
      consumer(url, False)
    #end def PerFile

    def PerDirectory(ignore, dirpath, namelist):
      """
      Called once per directory with a list of all the contained files/dirs.
      """
      ignore = ignore  # Avoid warnings of an unused parameter

      if not dirpath.startswith(root_path):
        output.Warn('Unable to decide what the root path is for directory: '
                    '%s' % dirpath)
        return

      for name in namelist:
        PerFile(dirpath, name)
    #end def PerDirectory

    output.Log('Walking DIRECTORY "%s"' % self._path, 1)
    PerFile(self._path, None)
    os.path.walk(self._path, PerDirectory, None)
  #end def ProduceURLs
#end class InputDirectory


class InputAccessLog:
  """
  Each Input class knows how to yield a set of URLs from a data source.

  This one handles access logs.  It's non-trivial in that we want to
  auto-detect log files in the Common Logfile Format (as used by Apache,
  for instance) and the Extended Log File Format (as used by IIS, for
  instance).
  """

  def __init__(self, attributes):
    self._path         = None               # The file path
    self._encoding     = None               # Encoding of that file
    self._is_elf       = False              # Extended Log File Format?
    self._is_clf       = False              # Common Logfile Format?
    self._elf_status   = -1                 # ELF field: '200'
    self._elf_method   = -1                 # ELF field: 'HEAD'
    self._elf_uri      = -1                 # ELF field: '/foo?bar=1'
    self._elf_urifrag1 = -1                 # ELF field: '/foo'
    self._elf_urifrag2 = -1                 # ELF field: 'bar=1'

    if not ValidateAttributes('ACCESSLOG', attributes, ('path', 'encoding')):
      return

    self._path      = attributes.get('path')
    self._encoding  = attributes.get('encoding', ENC_UTF8)
    if self._path:
      self._path    = encoder.MaybeNarrowPath(self._path)
      if os.path.isfile(self._path):
        output.Log('Input: From ACCESSLOG "%s"' % self._path, 2)
      else:
        output.Error('Can not locate file: %s' % self._path)
        self._path = None
    else:
      output.Error('Accesslog entries must have a "path" attribute.')
  #end def __init__

  def RecognizeELFLine(self, line):
    """ Recognize the Fields directive that heads an ELF file """
    if not line.startswith('#Fields:'):
      return False
    fields = line.split(' ')
    del fields[0]
    for i in range(0, len(fields)):
      field = fields[i].strip()
      if field == 'sc-status':
        self._elf_status   = i
      elif field == 'cs-method':
        self._elf_method   = i
      elif field == 'cs-uri':
        self._elf_uri      = i
      elif field == 'cs-uri-stem':
        self._elf_urifrag1 = i
      elif field == 'cs-uri-query':
        self._elf_urifrag2 = i
    output.Log('Recognized an Extended Log File Format file.', 2)
    return True
  #end def RecognizeELFLine

  def GetELFLine(self, line):
    """ Fetch the requested URL from an ELF line """
    fields = line.split(' ')
    count  = len(fields)

    # Verify status was Ok
    if self._elf_status >= 0:
      if self._elf_status >= count:
        return None
      if not fields[self._elf_status].strip() == '200':
        return None

    # Verify method was HEAD or GET
    if self._elf_method >= 0:
      if self._elf_method >= count:
        return None
      if not fields[self._elf_method].strip() in ('HEAD', 'GET'):
        return None

    # Pull the full URL if we can
    if self._elf_uri >= 0:
      if self._elf_uri >= count:
        return None
      url = fields[self._elf_uri].strip()
      if url != '-':
        return url

    # Put together a fragmentary URL
    if self._elf_urifrag1 >= 0:
      if self._elf_urifrag1 >= count or self._elf_urifrag2 >= count:
        return None
      urlfrag1 = fields[self._elf_urifrag1].strip()
      urlfrag2 = None
      if self._elf_urifrag2 >= 0:
        urlfrag2 = fields[self._elf_urifrag2]
      if urlfrag1 and (urlfrag1 != '-'):
        if urlfrag2 and (urlfrag2 != '-'):
          urlfrag1 = urlfrag1 + '?' + urlfrag2
        return urlfrag1

    return None
  #end def GetELFLine

  def RecognizeCLFLine(self, line):
    """ Try to tokenize a logfile line according to CLF pattern and see if
    it works. """
    match = ACCESSLOG_CLF_PATTERN.match(line)
    recognize = match and (match.group(1) in ('HEAD', 'GET'))
    if recognize:
      output.Log('Recognized a Common Logfile Format file.', 2)
    return recognize
  #end def RecognizeCLFLine

  def GetCLFLine(self, line):
    """ Fetch the requested URL from a CLF line """
    match = ACCESSLOG_CLF_PATTERN.match(line)
    if match:
      request = match.group(1)
      if request in ('HEAD', 'GET'):
        return match.group(2)
    return None
  #end def GetCLFLine

  def ProduceURLs(self, consumer):
    """ Produces URLs from our data source, hands them in to the consumer. """

    # Open the file
    (frame, file) = OpenFileForRead(self._path, 'ACCESSLOG')
    if not file:
      return

    # Iterate lines
    for line in file.readlines():
      if self._encoding:
        line = encoder.WidenText(line, self._encoding)
      line = line.strip()

      # If we don't know the format yet, try them both
      if (not self._is_clf) and (not self._is_elf):
        self._is_elf = self.RecognizeELFLine(line)
        self._is_clf = self.RecognizeCLFLine(line)

      # Digest the line
      match = None
      if self._is_elf:
        match = self.GetELFLine(line)
      elif self._is_clf:
        match = self.GetCLFLine(line)
      if not match:
        continue

      # Pass it on
      url = URL()
      url.TrySetAttribute('loc', match)
      consumer(url, True)

    file.close()
    if frame:
      frame.close()
  #end def ProduceURLs
#end class InputAccessLog


class FilePathGenerator:
  """
  This class generates filenames in a series, upon request.
  You can request any iteration number at any time, you don't
  have to go in order.

  Example of iterations for '/path/foo.xml.gz':
    0           --> /path/foo.xml.gz
    1           --> /path/foo1.xml.gz
    2           --> /path/foo2.xml.gz
    _index.xml  --> /path/foo_index.xml
  """

  def __init__(self):
    self.is_gzip     = False                 # Is this a  GZIP file?

    self._path       = None                  # '/path/'
    self._prefix     = None                  # 'foo'
    self._suffix     = None                  # '.xml.gz'
  #end def __init__

  def Preload(self, path):
    """ Splits up a path into forms ready for recombination. """
    path = encoder.MaybeNarrowPath(path)

    # Get down to a base name
    path = os.path.normpath(path)
    base = os.path.basename(path).lower()
    if not base:
      output.Error('Couldn\'t parse the file path: %s' % path)
      return False
    lenbase = len(base)

    # Recognize extension
    lensuffix = 0
    compare_suffix = ['.xml', '.xml.gz', '.gz']
    for suffix in compare_suffix:
      if base.endswith(suffix):
        lensuffix = len(suffix)
        break
    if not lensuffix:
      output.Error('The path "%s" doesn\'t end in a supported file '
                   'extension.' % path)
      return False
    self.is_gzip = suffix.endswith('.gz')

    # Split the original path
    lenpath = len(path)
    self._path   = path[:lenpath-lenbase]
    self._prefix = path[lenpath-lenbase:lenpath-lensuffix]
    self._suffix = path[lenpath-lensuffix:]

    return True
  #end def Preload

  def GeneratePath(self, instance):
    """ Generates the iterations, as described above. """
    prefix = self._path + self._prefix
    if type(instance) == types.IntType:
      if instance:
        return '%s%d%s' % (prefix, instance, self._suffix)
      return prefix + self._suffix
    return prefix + instance
  #end def GeneratePath

  def GenerateURL(self, instance, root_url):
    """ Generates iterations, but as a URL instead of a path. """
    prefix = root_url + self._prefix
    retval = None
    if type(instance) == types.IntType:
      if instance:
        retval = '%s%d%s' % (prefix, instance, self._suffix)
      else:
        retval = prefix + self._suffix
    else:
      retval = prefix + instance
    return URL.Canonicalize(retval)
  #end def GenerateURL

  def GenerateWildURL(self, root_url):
    """ Generates a wildcard that should match all our iterations """
    prefix = URL.Canonicalize(root_url + self._prefix)
    temp   = URL.Canonicalize(prefix + self._suffix)
    suffix = temp[len(prefix):]
    return prefix + '*' + suffix
  #end def GenerateURL
#end class FilePathGenerator


class PerURLStatistics:
  """ Keep track of some simple per-URL statistics, like file extension. """

  def __init__(self):
    self._extensions  = {}                  # Count of extension instances
  #end def __init__

  def Consume(self, url):
    """ Log some stats for the URL.  At the moment, that means extension. """
    if url and url.loc:
      (scheme, netloc, path, query, frag) = urlparse.urlsplit(url.loc)
      if not path:
        return

      # Recognize directories
      if path.endswith('/'):
        if self._extensions.has_key('/'):
          self._extensions['/'] = self._extensions['/'] + 1
        else:
          self._extensions['/'] = 1
        return

      # Strip to a filename
      i = path.rfind('/')
      if i >= 0:
        assert i < len(path)
        path = path[i:]

      # Find extension
      i = path.rfind('.')
      if i > 0:
        assert i < len(path)
        ext = path[i:].lower()
        if self._extensions.has_key(ext):
          self._extensions[ext] = self._extensions[ext] + 1
        else:
          self._extensions[ext] = 1
      else:
        if self._extensions.has_key('(no extension)'):
          self._extensions['(no extension)'] = self._extensions[
            '(no extension)'] + 1
        else:
          self._extensions['(no extension)'] = 1
  #end def Consume

  def Log(self):
    """ Dump out stats to the output. """
    if len(self._extensions):
      output.Log('Count of file extensions on URLs:', 1)
      set = self._extensions.keys()
      set.sort()
      for ext in set:
        output.Log(' %7d  %s' % (self._extensions[ext], ext), 1)
  #end def Log

class Sitemap(xml.sax.handler.ContentHandler):
  """
  This is the big workhorse class that processes your inputs and spits
  out sitemap files.  It is built as a SAX handler for set up purposes.
  That is, it processes an XML stream to bring itself up.
  """

  def __init__(self, suppress_notify):
    xml.sax.handler.ContentHandler.__init__(self)
    self._filters      = []                  # Filter objects
    self._inputs       = []                  # Input objects
    self._urls         = {}                  # Maps URLs to count of dups
    self._set          = []                  # Current set of URLs
    self._filegen      = None                # Path generator for output files
    self._wildurl1     = None                # Sitemap URLs to filter out
    self._wildurl2     = None                # Sitemap URLs to filter out
    self._sitemaps     = 0                   # Number of output files
    # We init _dup_max to 2 so the default priority is 0.5 instead of 1.0
    self._dup_max      = 2                   # Max number of duplicate URLs
    self._stat         = PerURLStatistics()  # Some simple stats
    self._in_site      = False               # SAX: are we in a Site node?
    self._in_Site_ever = False               # SAX: were we ever in a Site?

    self._default_enc  = None                # Best encoding to try on URLs
    self._base_url     = None                # Prefix to all valid URLs
    self._store_into   = None                # Output filepath
    self._sitemap_type = None		     # Sitemap type (web, mobile or news)
    self._suppress     = suppress_notify     # Suppress notify of servers
  #end def __init__

  def ValidateBasicConfig(self):
    """ Verifies (and cleans up) the basic user-configurable options. """
    all_good = True

    if self._default_enc:
      encoder.SetUserEncoding(self._default_enc)

    # Canonicalize the base_url
    if all_good and not self._base_url:
      output.Error('A site needs a "base_url" attribute.')
      all_good = False
    if all_good and not URL.IsAbsolute(self._base_url):
        output.Error('The "base_url" must be absolute, not relative: %s' %
                     self._base_url)
        all_good = False
    if all_good:
      self._base_url = URL.Canonicalize(self._base_url)
      if not self._base_url.endswith('/'):
        self._base_url = self._base_url + '/'
      output.Log('BaseURL is set to: %s' % self._base_url, 2)

    # Load store_into into a generator
    if all_good:
      if self._store_into:
        self._filegen = FilePathGenerator()
        if not self._filegen.Preload(self._store_into):
          all_good = False
      else:
        output.Error('A site needs a "store_into" attribute.')
        all_good = False

    # Ask the generator for patterns on what its output will look like
    if all_good:
      self._wildurl1 = self._filegen.GenerateWildURL(self._base_url)
      self._wildurl2 = self._filegen.GenerateURL(SITEINDEX_SUFFIX,
                                                 self._base_url)

    # Unify various forms of False
    if all_good:
      if self._suppress:
        if (type(self._suppress) == types.StringType) or (type(self._suppress)
                                 == types.UnicodeType):
          if (self._suppress == '0') or (self._suppress.lower() == 'false'):
            self._suppress = False

    # Clean up the sitemap_type
    if all_good:
      match = False
      # If sitemap_type is not specified, default to web sitemap
      if not self._sitemap_type:
        self._sitemap_type = 'web'
      else:
	self._sitemap_type = self._sitemap_type.lower()
        for pattern in SITEMAP_TYPES:
          if self._sitemap_type == pattern:
            match = True
            break
        if not match:
          output.Error('The "sitemap_type" value must be "web", "mobile" '
		       'or "news": %s' % self._sitemap_type)
          all_good = False
      output.Log('The Sitemap type is %s Sitemap.' % \
		        self._sitemap_type.upper(), 0)

    # Done
    if not all_good:
      output.Log('See "example_config.xml" for more information.', 0)
    return all_good
  #end def ValidateBasicConfig

  def Generate(self):
    """ Run over all the Inputs and ask them to Produce """
    # Run the inputs
    for input in self._inputs:
      input.ProduceURLs(self.ConsumeURL)

    # Do last flushes
    if len(self._set):
      self.FlushSet()
    if not self._sitemaps:
      output.Warn('No URLs were recorded, writing an empty sitemap.')
      self.FlushSet()

    # Write an index as needed
    if self._sitemaps > 1:
      self.WriteIndex()

    # Notify
    self.NotifySearch()

    # Dump stats
    self._stat.Log()
  #end def Generate

  def ConsumeURL(self, url, allow_fragment):
    """
    All per-URL processing comes together here, regardless of Input.
    Here we run filters, remove duplicates, spill to disk as needed, etc.
    
    """
    if not url:
      return

    # Validate
    if not url.Validate(self._base_url, allow_fragment):
      return

    # Run filters
    accept = None
    for filter in self._filters:
      accept = filter.Apply(url)
      if accept != None:
        break
    if not (accept or (accept == None)):
      url.Log(prefix='FILTERED', level=2)
      return

    # Ignore our out output URLs
    if fnmatch.fnmatchcase(url.loc, self._wildurl1) or fnmatch.fnmatchcase(
      url.loc, self._wildurl2):
      url.Log(prefix='IGNORED (output file)', level=2)
      return

    # Note the sighting
    hash = url.MakeHash()
    if self._urls.has_key(hash):
      dup = self._urls[hash]
      if dup > 0:
        dup = dup + 1
        self._urls[hash] = dup
        if self._dup_max < dup:
          self._dup_max = dup
      url.Log(prefix='DUPLICATE')
      return

    # Acceptance -- add to set
    self._urls[hash] = 1
    self._set.append(url)
    self._stat.Consume(url)
    url.Log()

    # Flush the set if needed
    if len(self._set) >= MAXURLS_PER_SITEMAP:
      self.FlushSet()
  #end def ConsumeURL

  def FlushSet(self):
    """
    Flush the current set of URLs to the output.  This is a little
    slow because we like to sort them all and normalize the priorities
    before dumping.
    """
    
    # Determine what Sitemap header to use (News or General)
    if self._sitemap_type == 'news':
      sitemap_header = NEWS_SITEMAP_HEADER
    else:
      sitemap_header = GENERAL_SITEMAP_HEADER
      
    # Sort and normalize
    output.Log('Sorting and normalizing collected URLs.', 1)
    self._set.sort()
    for url in self._set:
      hash = url.MakeHash()
      dup = self._urls[hash]
      if dup > 0:
        self._urls[hash] = -1
        if not url.priority:
          url.priority = '%.4f' % (float(dup) / float(self._dup_max))

    # Get the filename we're going to write to
    filename = self._filegen.GeneratePath(self._sitemaps)
    if not filename:
      output.Fatal('Unexpected: Couldn\'t generate output filename.')
    self._sitemaps = self._sitemaps + 1
    output.Log('Writing Sitemap file "%s" with %d URLs' %
        (filename, len(self._set)), 1)

    # Write to it
    frame = None
    file  = None

    try:
      if self._filegen.is_gzip:
        basename = os.path.basename(filename);
        frame = open(filename, 'wb')
        file = gzip.GzipFile(fileobj=frame, filename=basename, mode='wt')
      else:
        file = open(filename, 'wt')

      file.write(sitemap_header)
      for url in self._set:
        url.WriteXML(file)
      file.write(SITEMAP_FOOTER)

      file.close()
      if frame:
        frame.close()

      frame = None
      file  = None
    except IOError:
      output.Fatal('Couldn\'t write out to file: %s' % filename)
    os.chmod(filename, 0644)

    # Flush
    self._set = []
  #end def FlushSet

  def WriteIndex(self):
    """ Write the master index of all Sitemap files """
    # Make a filename
    filename = self._filegen.GeneratePath(SITEINDEX_SUFFIX)
    if not filename:
      output.Fatal('Unexpected: Couldn\'t generate output index filename.')
    output.Log('Writing index file "%s" with %d Sitemaps' %
        (filename, self._sitemaps), 1)

   # Determine what Sitemap index header to use (News or General)
    if self._sitemap_type == 'news':
      sitemap_index_header = NEWS_SITEMAP_HEADER
    else:
      sitemap__index_header = GENERAL_SITEMAP_HEADER
 
    # Make a lastmod time
    lastmod = TimestampISO8601(time.time())

    # Write to it
    try:
      fd = open(filename, 'wt')
      fd.write(sitemap_index_header)

      for mapnumber in range(0,self._sitemaps):
        # Write the entry
        mapurl = self._filegen.GenerateURL(mapnumber, self._base_url)
        mapattributes = { 'loc' : mapurl, 'lastmod' : lastmod }
        fd.write(SITEINDEX_ENTRY % mapattributes)

      fd.write(SITEINDEX_FOOTER)

      fd.close()
      fd = None
    except IOError:
      output.Fatal('Couldn\'t write out to file: %s' % filename)
    os.chmod(filename, 0644)
  #end def WriteIndex

  def NotifySearch(self):
    """ Send notification of the new Sitemap(s) to the search engines. """
    if self._suppress:
      output.Log('Search engine notification is suppressed.', 1)
      return

    output.Log('Notifying search engines.', 1)

    # Override the urllib's opener class with one that doesn't ignore 404s
    class ExceptionURLopener(urllib.FancyURLopener):
      def http_error_default(self, url, fp, errcode, errmsg, headers):
        output.Log('HTTP error %d: %s' % (errcode, errmsg), 2)
        raise IOError
      #end def http_error_default
    #end class ExceptionURLOpener
    old_opener = urllib._urlopener
    urllib._urlopener = ExceptionURLopener()

    # Build the URL we want to send in
    if self._sitemaps > 1:
      url = self._filegen.GenerateURL(SITEINDEX_SUFFIX, self._base_url)
    else:
      url = self._filegen.GenerateURL(0, self._base_url)

    # Test if we can hit it ourselves
    try:
      u = urllib.urlopen(url)
      u.close()
    except IOError:
      output.Error('When attempting to access our generated Sitemap at the '
                   'following URL:\n    %s\n  we failed to read it.  Please '
                   'verify the store_into path you specified in\n'
                   '  your configuration file is web-accessable.  Consult '
                   'the FAQ for more\n  information.' % url)
      output.Warn('Proceeding to notify with an unverifyable URL.')

    # Cycle through notifications
    # To understand this, see the comment near the NOTIFICATION_SITES comment
    for ping in NOTIFICATION_SITES:
      query_map             = ping[3]
      query_attr            = ping[5]
      query_map[query_attr] = url
      query = urllib.urlencode(query_map)
      notify = urlparse.urlunsplit((ping[0], ping[1], ping[2], query, ping[4]))

      # Send the notification
      output.Log('Notifying: %s' % ping[1], 0)
      output.Log('Notification URL: %s' % notify, 2)
      try:
        u = urllib.urlopen(notify)
        u.read()
        u.close()
      except IOError:
        output.Warn('Cannot contact: %s' % ping[1])

    if old_opener:
      urllib._urlopener = old_opener
  #end def NotifySearch

  def startElement(self, tag, attributes):
    """ SAX processing, called per node in the config stream. """
    if tag == 'site':
      if self._in_site:
        output.Error('Can not nest Site entries in the configuration.')
      else:
        self._in_site     = True

        if not ValidateAttributes('SITE', attributes,
          ('verbose', 'default_encoding', 'base_url', 'store_into',
           'suppress_search_engine_notify', 'sitemap_type')):
          return

        verbose           = attributes.get('verbose', 0)
        if verbose:
          output.SetVerbose(verbose)

        self._default_enc = attributes.get('default_encoding')
        self._base_url    = attributes.get('base_url')
        self._store_into  = attributes.get('store_into')
	self._sitemap_type= attributes.get('sitemap_type')
        if not self._suppress:
          self._suppress  = attributes.get('suppress_search_engine_notify',
                                            False)
        self.ValidateBasicConfig()
    elif tag == 'filter':
      self._filters.append(Filter(attributes))

    elif tag == 'url':
     print type(attributes)
     self._inputs.append(InputURL(attributes))

    elif tag == 'urllist':
      for attributeset in ExpandPathAttribute(attributes, 'path'):
        if self._sitemap_type == 'news':
          self._inputs.append(InputNewsURLList(attributeset))
        else:
	  self._inputs.append(InputURLList(attributeset))

    elif tag == 'directory':
      self._inputs.append(InputDirectory(attributes, self._base_url))

    elif tag == 'accesslog':
      for attributeset in ExpandPathAttribute(attributes, 'path'):
        self._inputs.append(InputAccessLog(attributeset))
    else:
      output.Error('Unrecognized tag in the configuration: %s' % tag)
  #end def startElement

  def endElement(self, tag):
    """ SAX processing, called per node in the config stream. """
    if tag == 'site':
      assert self._in_site
      self._in_site      = False
      self._in_site_ever = True
  #end def endElement

  def endDocument(self):
    """ End of SAX, verify we can proceed. """
    if not self._in_site_ever:
      output.Error('The configuration must specify a "site" element.')
    else:
      if not self._inputs:
        output.Warn('There were no inputs to generate a sitemap from.')
  #end def endDocument
#end class Sitemap


def ValidateAttributes(tag, attributes, goodattributes):
  """ Makes sure 'attributes' does not contain any attribute not
      listed in 'goodattributes' """
  all_good = True
  for attr in attributes.keys():
    if not attr in goodattributes:
      output.Error('Unknown %s attribute: %s' % (tag, attr))
      all_good = False
  return all_good
#end def ValidateAttributes

def ExpandPathAttribute(src, attrib):
  """ Given a dictionary of attributes, return a list of dictionaries
      with all the same attributes except for the one named attrib.
      That one, we treat as a file path and expand into all its possible
      variations. """
  # Do the path expansion.  On any error, just return the source dictionary.
  path = src.get(attrib)
  if not path:
    return [src]
  path = encoder.MaybeNarrowPath(path);
  pathlist = glob.glob(path)
  if not pathlist:
    return [src]

  # If this isn't actually a dictionary, make it one
  if type(src) != types.DictionaryType:
    tmp = {}
    for key in src.keys():
      tmp[key] = src[key]
    src = tmp
  # Create N new dictionaries
  retval = []
  for path in pathlist:
    dst = src.copy()
    dst[attrib] = path
    retval.append(dst)

  return retval
#end def ExpandPathAttribute

def OpenFileForRead(path, logtext):
  """ Opens a text file, be it GZip or plain """

  frame = None
  file  = None

  if not path:
    return (frame, file)

  try:
    if path.endswith('.gz'):
      frame = open(path, 'rb')
      file = gzip.GzipFile(fileobj=frame, mode='rt')
    else:
      file = open(path, 'rt')

    if logtext:
      output.Log('Opened %s file: %s' % (logtext, path), 1)
    else:
      output.Log('Opened file: %s' % path, 1)
  except IOError:
    output.Error('Can not open file: %s' % path)

  return (frame, file)
#end def OpenFileForRead

def TimestampISO8601(t):
  """Seconds since epoch (1970-01-01) --> ISO 8601 time string."""
  return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))
#end def TimestampISO8601

def CreateSitemapFromFile(configpath, suppress_notify):
  """ Sets up a new Sitemap object from the specified configuration file.  """

  # Remember error count on the way in
  num_errors = output.num_errors

  # Rev up SAX to parse the config
  sitemap = Sitemap(suppress_notify)
  try:
    output.Log('Reading configuration file: %s' % configpath, 0)
    xml.sax.parse(configpath, sitemap)
  except IOError:
    output.Error('Cannot read configuration file: %s' % configpath)
  except xml.sax._exceptions.SAXParseException, e:
    output.Error('XML error in the config file (line %d, column %d): %s' %
                 (e._linenum, e._colnum, e.getMessage()))
  except xml.sax._exceptions.SAXReaderNotAvailable:
    output.Error('Some installs of Python 2.2 did not include complete support'
                 ' for XML.\n  Please try upgrading your version of Python'
                 ' and re-running the script.')

  # If we added any errors, return no sitemap
  if num_errors == output.num_errors:
    return sitemap
  return None
#end def CreateSitemapFromFile

def ProcessCommandFlags(args):
  """
  Parse command line flags per specified usage, pick off key, value pairs
  All flags of type "--key=value" will be processed as __flags[key] = value,
                    "--option" will be processed as __flags[option] = option
  """

  flags   = {}
  rkeyval = '--(?P<key>\S*)[=](?P<value>\S*)' # --key=val
  roption = '--(?P<option>\S*)'               # --key
  r = '(' + rkeyval + ')|(' + roption + ')'
  rc = re.compile(r)
  for a in args:
    try:
      rcg = rc.search(a).groupdict()
      if rcg.has_key('key'):
        flags[rcg['key']] = rcg['value']
      if rcg.has_key('option'):
        flags[rcg['option']] = rcg['option']
    except AttributeError:
      return None
  return flags
#end def ProcessCommandFlags


#
# __main__
#

if __name__ == '__main__':
  flags = ProcessCommandFlags(sys.argv[1:])
  if not flags or not flags.has_key('config') or flags.has_key('help'):
    output.Log(__usage__, 0)
  else:
    suppress_notify = flags.has_key('testing')
    sitemap = CreateSitemapFromFile(flags['config'], suppress_notify)
    if not sitemap:
      output.Log('Configuration file errors -- exiting.', 0)
    else:
      sitemap.Generate()
      output.Log('Number of errors: %d' % output.num_errors, 1)
      output.Log('Number of warnings: %d' % output.num_warns, 1)

########NEW FILE########
__FILENAME__ = sphinxtogithub
#! /usr/bin/env python
 
import optparse as op
import os
import re
import sphinx
import sys
import shutil


def get_number(text):
    m = re.match("[0-9]+", text)
    if m:
        return int(m.group(0))
    else:
        return 0

def get_sphinx_version():
    return tuple(get_number(x) for x in sphinx.__version__.split("."))

class NoDirectoriesError(Exception):
    "Error thrown when no directories starting with an underscore are found"

class DirHelper(object):

    def __init__(self, is_dir, list_dir, walk, rmtree):

        self.is_dir = is_dir
        self.list_dir = list_dir
        self.walk = walk
        self.rmtree = rmtree

class FileSystemHelper(object):

    def __init__(self, open_, path_join, move, exists):

        self.open_ = open_
        self.path_join = path_join
        self.move = move
        self.exists = exists

class Replacer(object):
    "Encapsulates a simple text replace"

    def __init__(self, from_, to):

        self.from_ = from_
        self.to = to

    def process(self, text):

        return text.replace( self.from_, self.to )

class FileHandler(object):
    "Applies a series of replacements the contents of a file inplace"

    def __init__(self, name, replacers, opener):

        self.name = name
        self.replacers = replacers
        self.opener = opener

    def process(self):

        text = self.opener(self.name).read()
        if get_sphinx_version() >= (1, 2):
            text = text.decode("utf-8")

        for replacer in self.replacers:
            text = replacer.process( text )

        if get_sphinx_version() >= (1, 2):
            text = text.encode("utf-8")
        self.opener(self.name, "w").write(text)

class Remover(object):

    def __init__(self, exists, remove):
        self.exists = exists
        self.remove = remove

    def __call__(self, name):

        if self.exists(name):
            self.remove(name)

class ForceRename(object):

    def __init__(self, renamer, remove):

        self.renamer = renamer
        self.remove = remove

    def __call__(self, from_, to):

        self.remove(to)
        self.renamer(from_, to)

class VerboseRename(object):

    def __init__(self, renamer, stream):

        self.renamer = renamer
        self.stream = stream

    def __call__(self, from_, to):

        self.stream.write(
                "Renaming directory '%s' -> '%s'\n"
                    % (os.path.basename(from_), os.path.basename(to))
                )

        self.renamer(from_, to)


class DirectoryHandler(object):
    "Encapsulates renaming a directory by removing its first character"

    def __init__(self, name, root, renamer):

        self.name = name
        self.new_name = name[1:]
        self.root = root + os.sep
        self.renamer = renamer

    def path(self):
        
        return os.path.join(self.root, self.name)

    def relative_path(self, directory, filename):

        path = directory.replace(self.root, "", 1)
        return os.path.join(path, filename)

    def new_relative_path(self, directory, filename):

        path = self.relative_path(directory, filename)
        return path.replace(self.name, self.new_name, 1)

    def process(self):

        from_ = os.path.join(self.root, self.name)
        to = os.path.join(self.root, self.new_name)
        self.renamer(from_, to)


class HandlerFactory(object):

    def create_file_handler(self, name, replacers, opener):

        return FileHandler(name, replacers, opener)

    def create_dir_handler(self, name, root, renamer):

        return DirectoryHandler(name, root, renamer)


class OperationsFactory(object):

    def create_force_rename(self, renamer, remover):

        return ForceRename(renamer, remover)

    def create_verbose_rename(self, renamer, stream):

        return VerboseRename(renamer, stream)

    def create_replacer(self, from_, to):

        return Replacer(from_, to)

    def create_remover(self, exists, remove):

        return Remover(exists, remove)


class Layout(object):
    """
    Applies a set of operations which result in the layout
    of a directory changing
    """

    def __init__(self, directory_handlers, file_handlers):

        self.directory_handlers = directory_handlers
        self.file_handlers = file_handlers

    def process(self):

        for handler in self.file_handlers:
            handler.process()

        for handler in self.directory_handlers:
            handler.process()


class LayoutFactory(object):
    "Creates a layout object"

    def __init__(self, operations_factory, handler_factory, file_helper, dir_helper, verbose, stream, force):

        self.operations_factory = operations_factory
        self.handler_factory = handler_factory

        self.file_helper = file_helper
        self.dir_helper = dir_helper

        self.verbose = verbose
        self.output_stream = stream
        self.force = force

    def create_layout(self, path):

        contents = self.dir_helper.list_dir(path)

        renamer = self.file_helper.move

        if self.force:
            remove = self.operations_factory.create_remover(self.file_helper.exists, self.dir_helper.rmtree)
            renamer = self.operations_factory.create_force_rename(renamer, remove) 

        if self.verbose:
            renamer = self.operations_factory.create_verbose_rename(renamer, self.output_stream) 

        # Build list of directories to process
        directories = [d for d in contents if self.is_underscore_dir(path, d)]
        underscore_directories = [
                self.handler_factory.create_dir_handler(d, path, renamer)
                    for d in directories
                ]

        if not underscore_directories:
            raise NoDirectoriesError()

        # Build list of files that are in those directories
        replacers = []
        for handler in underscore_directories:
            for directory, dirs, files in self.dir_helper.walk(handler.path()):
                for f in files:
                    replacers.append(
                            self.operations_factory.create_replacer(
                                handler.relative_path(directory, f),
                                handler.new_relative_path(directory, f)
                                )
                            )

        # Build list of handlers to process all files
        filelist = []
        for root, dirs, files in self.dir_helper.walk(path):
            for f in files:
                if f.endswith(".html"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                replacers,
                                self.file_helper.open_)
                            )
                if f.endswith(".js"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                [self.operations_factory.create_replacer("'_sources/'", "'sources/'")],
                                self.file_helper.open_
                                )
                            )

        return Layout(underscore_directories, filelist)

    def is_underscore_dir(self, path, directory):

        return (self.dir_helper.is_dir(self.file_helper.path_join(path, directory))
            and directory.startswith("_"))



def sphinx_extension(app, exception):
    "Wrapped up as a Sphinx Extension"

    # This code is sadly untestable in its current state
    # It would be helped if there was some function for loading extension
    # specific data on to the app object and the app object providing 
    # a file-like object for writing to standard out.
    # The former is doable, but not officially supported (as far as I know)
    # so I wouldn't know where to stash the data. 

    if app.builder.name != "html":
        return

    if not app.config.sphinx_to_github:
        if app.config.sphinx_to_github_verbose:
            print "Sphinx-to-github: Disabled, doing nothing."
        return

    if exception:
        if app.config.sphinx_to_github_verbose:
            print "Sphinx-to-github: Exception raised in main build, doing nothing."
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )
    
    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            app.config.sphinx_to_github_verbose,
            sys.stdout,
            force=True
            )

    layout = layout_factory.create_layout(app.outdir)
    layout.process()


def setup(app):
    "Setup function for Sphinx Extension"

    app.add_config_value("sphinx_to_github", True, '')
    app.add_config_value("sphinx_to_github_verbose", True, '')

    app.connect("build-finished", sphinx_extension)


def main(args):

    usage = "usage: %prog [options] <html directory>"
    parser = OptionParser(usage=usage)
    parser.add_option("-v","--verbose", action="store_true",
            dest="verbose", default=False, help="Provides verbose output")
    opts, args = parser.parse_args(args)

    try:
        path = args[0]
    except IndexError:
        sys.stderr.write(
                "Error - Expecting path to html directory:"
                "sphinx-to-github <path>\n"
                )
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )
    
    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            opts.verbose,
            sys.stdout,
            force=False
            )

    try:
        layout = layout_factory.create_layout(path)
    except NoDirectoriesError:
        sys.stderr.write(
                "Error - No top level directories starting with an underscore "
                "were found in '%s'\n" % path
                )
        return

    layout.process()
    


if __name__ == "__main__":
    main(sys.argv[1:])




########NEW FILE########
__FILENAME__ = couchdbproxy
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import urlparse

from webob import Request
from restkit.contrib.wsgi_proxy import HostProxy

import restkit
from restkit.conn import Connection
from socketpool import ConnectionPool

restkit.set_logging("debug")

pool = ConnectionPool(factory=Connection, max_size=10, backend="thread")
proxy = HostProxy("http://127.0.0.1:5984", pool=pool)


def application(environ, start_response):
    req = Request(environ)
    if 'RAW_URI' in req.environ:
        # gunicorn so we use real path non encoded
        u = urlparse.urlparse(req.environ['RAW_URI'])
        req.environ['PATH_INFO'] = u.path

    # do smth like adding oauth headers ..
    resp = req.get_response(proxy)

    # rewrite response
    # do auth ...
    return resp(environ, start_response)

########NEW FILE########
__FILENAME__ = test_eventlet
import timeit

import eventlet
eventlet.monkey_patch()

from restkit import *
from restkit.conn import Connection
from socketpool import ConnectionPool

#set_logging("debug")

pool = ConnectionPool(factory=Connection, backend="eventlet")

epool = eventlet.GreenPool()

urls = [
        "http://refuge.io",
        "http://gunicorn.org",
        "http://friendpaste.com",
        "http://benoitc.io",
        "http://couchdb.apache.org"]

allurls = []
for i in range(10):
    allurls.extend(urls)

def fetch(u):
    r = request(u, follow_redirect=True, pool=pool)
    print "RESULT: %s: %s (%s)" % (u, r.status, len(r.body_string()))

def extract():
    for url in allurls:
        epool.spawn_n(fetch, url)
    epool.waitall()

t = timeit.Timer(stmt=extract)
print "%.2f s" % t.timeit(number=1)

########NEW FILE########
__FILENAME__ = test_gevent
import timeit

from gevent import monkey; monkey.patch_all()
import gevent

from restkit import *
from restkit.conn import Connection
from socketpool import ConnectionPool

#set_logging("debug")

pool = ConnectionPool(factory=Connection, backend="gevent")

urls = [
        "http://refuge.io",
        "http://gunicorn.org",
        "http://friendpaste.com",
        "http://benoitc.io",
        "http://couchdb.apache.org"]

allurls = []
for i in range(10):
    allurls.extend(urls)

def fetch(u):
    r = request(u, follow_redirect=True, pool=pool)
    print "RESULT: %s: %s (%s)" % (u, r.status, len(r.body_string()))

def extract():

    jobs = [gevent.spawn(fetch, url) for url in allurls]
    gevent.joinall(jobs)

t = timeit.Timer(stmt=extract)
print "%.2f s" % t.timeit(number=1)

########NEW FILE########
__FILENAME__ = test_threads
import threading
import timeit
from restkit import *

#set_logging("debug")

urls = [
        "http://refuge.io",
        "http://gunicorn.org",
        "http://friendpaste.com",
        "http://benoitc.io",
        "http://couchdb.apache.org"]

allurls = []
for i in range(10):
    allurls.extend(urls)

def fetch(u):
    r = request(u, follow_redirect=True)
    print "RESULT: %s: %s (%s)" % (u, r.status, len(r.body_string()))

def spawn(u):
    t =  threading.Thread(target=fetch, args=[u])
    t.daemon = True
    t.start()
    return t

def extract():
    threads = [spawn(u) for u in allurls]
    [t.join() for t in threads]

t = timeit.Timer(stmt=extract)
print "%.2f s" % t.timeit(number=1)

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.
import base64
import errno
import logging
import os
import time
import socket
import ssl
import traceback
import types
import urlparse

try:
    from http_parser.http import (
            HttpStream, BadStatusLine, NoMoreData
    )
    from http_parser.reader import SocketReader
except ImportError:
    raise ImportError("""http-parser isn't installed or out of data.

        pip install http-parser""")

from restkit import __version__

from restkit.conn import Connection
from restkit.errors import RequestError, RequestTimeout, RedirectLimit, \
ProxyError
from restkit.session import get_session
from restkit.util import parse_netloc, rewrite_location, to_bytestring
from restkit.wrappers import Request, Response

MAX_CLIENT_TIMEOUT=300
MAX_CLIENT_CONNECTIONS = 5
MAX_CLIENT_TRIES =3
CLIENT_WAIT_TRIES = 0.3
MAX_FOLLOW_REDIRECTS = 5
USER_AGENT = "restkit/%s" % __version__

log = logging.getLogger(__name__)

class Client(object):
    """A client handle a connection at a time. A client is threadsafe,
    but an handled shouldn't be shared between threads. All connections
    are shared between threads via a pool.
    ::

        >>> from restkit import *
        >>> c = Client()
        >>> r = c.request("http://google.com")
        >>> r.status
        '301 Moved Permanently'
        >>> r.body_string()
        '<HTML><HEAD><meta http-equiv="content-type [...]'
        >>> c.follow_redirect = True
        >>> r = c.request("http://google.com")
        >>> r.status
        '200 OK'
    """

    version = (1, 1)
    response_class=Response

    def __init__(self,
            follow_redirect=False,
            force_follow_redirect=False,
            max_follow_redirect=MAX_FOLLOW_REDIRECTS,
            filters=None,
            decompress=True,
            max_status_line_garbage=None,
            max_header_count=0,
            pool=None,
            response_class=None,
            timeout=None,
            use_proxy=False,
            max_tries=3,
            wait_tries=0.3,
            pool_size=10,
            backend="thread",
            **ssl_args):
        """
        Client parameters
        ~~~~~~~~~~~~~~~~~

        - follow_redirect: follow redirection, by default False
        - max_ollow_redirect: number of redirections available
        - filters: http filters to pass
        - decompress: allows the client to decompress the response body
        - max_status_line_garbage: defines the maximum number of ignorable
          lines before we expect a HTTP response's status line. With HTTP/1.1
          persistent connections, the problem arises that broken scripts could
          return a wrong Content-Length (there are more bytes sent than
          specified).  Unfortunately, in some cases, this cannot be detected
          after the bad response, but only before the next one. So the client
          is abble to skip bad lines using this limit. 0 disable garbage
          collection, None means unlimited number of tries.
        - max_header_count:  determines the maximum HTTP header count allowed.
          by default no limit.
        - pool: the pool to use inherited from socketpool.Pool. By default we
          use the global one.
        - response_class: the response class to use
        - timeout: the default timeout of the connection (SO_TIMEOUT)
        - max_tries: the number of tries before we give up a
        connection
        - wait_tries: number of time we wait between each tries.
        - pool_size: int, default 10. Maximum number of connections we keep in
          the default pool.
        - ssl_args: named argument, see ssl module for more informations
        """
        self.follow_redirect = follow_redirect
        self.force_follow_redirect = force_follow_redirect
        self.max_follow_redirect = max_follow_redirect
        self.decompress = decompress
        self.filters = filters or []
        self.max_status_line_garbage = max_status_line_garbage
        self.max_header_count = max_header_count
        self.use_proxy = use_proxy

        self.request_filters = []
        self.response_filters = []
        self.load_filters()


        # set manager

        session_options = dict(
                retry_delay=wait_tries,
                max_size = pool_size,
                retry_max = max_tries,
                timeout = timeout)


        if pool is None:
            pool = get_session(backend, **session_options)
        self._pool = pool
        self.backend = backend

        # change default response class
        if response_class is not None:
            self.response_class = response_class

        self.max_tries = max_tries
        self.wait_tries = wait_tries
        self.pool_size = pool_size
        self.timeout = timeout

        self._nb_redirections = self.max_follow_redirect
        self._url = None
        self._initial_url = None
        self._write_cb = None
        self._headers = None
        self._sock_key = None
        self._sock = None
        self._original = None

        self.method = 'GET'
        self.body = None
        self.ssl_args = ssl_args or {}

    def load_filters(self):
        """ Populate filters from self.filters.
        Must be called each time self.filters is updated.
        """
        for f in self.filters:
            if hasattr(f, "on_request"):
                self.request_filters.append(f)
            if hasattr(f, "on_response"):
                self.response_filters.append(f)



    def get_connection(self, request):
        """ get a connection from the pool or create new one. """

        addr = parse_netloc(request.parsed_url)
        is_ssl = request.is_ssl()

        extra_headers = []
        conn = None
        if self.use_proxy:
            conn = self.proxy_connection(request,
                    addr, is_ssl)
        if not conn:
            conn = self._pool.get(host=addr[0], port=addr[1],
                    pool=self._pool, is_ssl=is_ssl,
                    extra_headers=extra_headers, **self.ssl_args)


        return conn

    def proxy_connection(self, request, req_addr, is_ssl):
        """ do the proxy connection """
        proxy_settings = os.environ.get('%s_proxy' %
                request.parsed_url.scheme)

        if proxy_settings and proxy_settings is not None:
            request.is_proxied = True

            proxy_settings, proxy_auth =  _get_proxy_auth(proxy_settings)
            addr = parse_netloc(urlparse.urlparse(proxy_settings))

            if is_ssl:
                if proxy_auth:
                    proxy_auth = 'Proxy-authorization: %s' % proxy_auth
                proxy_connect = 'CONNECT %s:%s HTTP/1.0\r\n' % req_addr

                user_agent = request.headers.iget('user_agent')
                if not user_agent:
                    user_agent = "User-Agent: restkit/%s\r\n" % __version__

                proxy_pieces = '%s%s%s\r\n' % (proxy_connect, proxy_auth,
                        user_agent)

                conn = self._pool.get(host=addr[0], port=addr[1],
                    pool=self._pool, is_ssl=is_ssl,
                    extra_headers=[], proxy_pieces=proxy_pieces, **self.ssl_args)
            else:
                headers = []
                if proxy_auth:
                    headers = [('Proxy-authorization', proxy_auth)]

                conn = self._pool.get(host=addr[0], port=addr[1],
                        pool=self._pool, is_ssl=False,
                        extra_headers=[], **self.ssl_args)
            return conn

        return

    def make_headers_string(self, request, extra_headers=None):
        """ create final header string """
        headers = request.headers.copy()
        if extra_headers is not None:
            for k, v in extra_headers:
                headers[k] = v

        if not request.body and request.method in ('POST', 'PUT',):
            headers['Content-Length'] = 0

        if self.version == (1,1):
            httpver = "HTTP/1.1"
        else:
            httpver = "HTTP/1.0"

        ua = headers.iget('user-agent')
        if not ua:
            ua = USER_AGENT
        host = request.host

        accept_encoding = headers.iget('accept-encoding')
        if not accept_encoding:
            accept_encoding = 'identity'

        if request.is_proxied:
            full_path = ("https://" if request.is_ssl() else "http://") + request.host + request.path
        else:
            full_path = request.path

        lheaders = [
            "%s %s %s\r\n" % (request.method, full_path, httpver),
            "Host: %s\r\n" % host,
            "User-Agent: %s\r\n" % ua,
            "Accept-Encoding: %s\r\n" % accept_encoding
        ]

        lheaders.extend(["%s: %s\r\n" % (k, str(v)) for k, v in \
                headers.items() if k.lower() not in \
                ('user-agent', 'host', 'accept-encoding',)])
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Send headers: %s" % lheaders)
        return "%s\r\n" % "".join(lheaders)

    def perform(self, request):
        """ perform the request. If an error happen it will first try to
        restart it """

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Start to perform request: %s %s %s" %
                    (request.host, request.method, request.path))
        tries = 0
        while True:
            conn = None
            try:
                # get or create a connection to the remote host
                conn = self.get_connection(request)

                # send headers
                msg = self.make_headers_string(request,
                        conn.extra_headers)

                # send body
                if request.body is not None:
                    chunked = request.is_chunked()
                    if request.headers.iget('content-length') is None and \
                            not chunked:
                        raise RequestError(
                                "Can't determine content length and " +
                                "Transfer-Encoding header is not chunked")


                    # handle 100-Continue status
                    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec8.html#sec8.2.3
                    hdr_expect = request.headers.iget("expect")
                    if hdr_expect is not None and \
                            hdr_expect.lower() == "100-continue":
                        conn.send(msg)
                        msg = None
                        p = HttpStream(SocketReader(conn.socket()), kind=1,
                                decompress=True)


                        if p.status_code != 100:
                            self.reset_request()
                            if log.isEnabledFor(logging.DEBUG):
                                log.debug("return response class")
                            return self.response_class(conn, request, p)

                    chunked = request.is_chunked()
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("send body (chunked: %s)" % chunked)


                    if isinstance(request.body, types.StringTypes):
                        if msg is not None:
                            conn.send(msg + to_bytestring(request.body),
                                    chunked)
                        else:
                            conn.send(to_bytestring(request.body), chunked)
                    else:
                        if msg is not None:
                            conn.send(msg)

                        if hasattr(request.body, 'read'):
                            if hasattr(request.body, 'seek'):
                                request.body.seek(0)
                            conn.sendfile(request.body, chunked)
                        else:
                            conn.sendlines(request.body, chunked)
                    if chunked:
                        conn.send_chunk("")
                else:
                    conn.send(msg)

                return self.get_response(request, conn)
            except socket.gaierror, e:
                if conn is not None:
                    conn.release(True)
                raise RequestError(str(e))
            except socket.timeout, e:
                if conn is not None:
                    conn.release(True)
                raise RequestTimeout(str(e))
            except socket.error, e:
                if log.isEnabledFor(logging.DEBUG):
                    log.debug("socket error: %s" % str(e))
                if conn is not None:
                    conn.close()

                errors = (errno.EAGAIN, errno.EPIPE, errno.EBADF,
                        errno.ECONNRESET)
                if e[0] not in errors or tries >= self.max_tries:
                    raise RequestError("socket.error: %s" % str(e))

                # should raised an exception in other cases
                request.maybe_rewind(msg=str(e))

            except NoMoreData, e:
                if conn is not None:
                    conn.release(True)

                request.maybe_rewind(msg=str(e))
                if tries >= self.max_tries:
                    raise
            except BadStatusLine:

                if conn is not None:
                    conn.release(True)

                # should raised an exception in other cases
                request.maybe_rewind(msg="bad status line")

                if tries >= self.max_tries:
                    raise
            except Exception:
                # unkown error
                log.debug("unhandled exception %s" %
                        traceback.format_exc())
                if conn is not None:
                    conn.release(True)

                raise
            tries += 1
            self._pool.backend_mod.sleep(self.wait_tries)

    def request(self, url, method='GET', body=None, headers=None):
        """ perform immediatly a new request """

        request = Request(url, method=method, body=body,
                headers=headers)

        # apply request filters
        # They are applied only once time.
        for f in self.request_filters:
            ret = f.on_request(request)
            if isinstance(ret, Response):
                # a response instance has been provided.
                # just return it. Useful for cache filters
                return ret

        # no response has been provided, do the request
        self._nb_redirections = self.max_follow_redirect
        return self.perform(request)

    def redirect(self, location, request):
        """ reset request, set new url of request and perform it """
        if self._nb_redirections <= 0:
            raise RedirectLimit("Redirection limit is reached")

        if request.initial_url is None:
            request.initial_url = self.url

        # make sure location follow rfc2616
        location = rewrite_location(request.url, location)

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Redirect to %s" % location)

        # change request url and method if needed
        request.url = location

        self._nb_redirections -= 1

        #perform a new request
        return self.perform(request)

    def get_response(self, request, connection):
        """ return final respons, it is only accessible via peform
        method """
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Start to parse response")

        p = HttpStream(SocketReader(connection.socket()), kind=1,
                decompress=self.decompress)

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Got response: %s %s" % (p.version(), p.status()))
            log.debug("headers: [%s]" % p.headers())

        location = p.headers().get('location')

        if self.follow_redirect:
            should_close = not p.should_keep_alive()
            if p.status_code() in (301, 302, 307,):

                # read full body and release the connection
                p.body_file().read()
                connection.release(should_close)

                if request.method in ('GET', 'HEAD',) or \
                        self.force_follow_redirect:
                    if hasattr(self.body, 'read'):
                        try:
                            self.body.seek(0)
                        except AttributeError:
                            raise RequestError("Can't redirect %s to %s "
                                    "because body has already been read"
                                    % (self.url, location))
                    return self.redirect(location, request)

            elif p.status_code() == 303 and self.method == "POST":
                # read full body and release the connection
                p.body_file().read()
                connection.release(should_close)

                request.method = "GET"
                request.body = None
                return self.redirect(location, request)

        # create response object
        resp = self.response_class(connection, request, p)

        # apply response filters
        for f in self.response_filters:
            f.on_response(resp, request)

        if log.isEnabledFor(logging.DEBUG):
            log.debug("return response class")

        # return final response
        return resp


def _get_proxy_auth(proxy_settings):
    proxy_username = os.environ.get('proxy-username')
    if not proxy_username:
        proxy_username = os.environ.get('proxy_username')
    proxy_password = os.environ.get('proxy-password')
    if not proxy_password:
        proxy_password = os.environ.get('proxy_password')

    proxy_password = proxy_password or ""

    if not proxy_username:
        u = urlparse.urlparse(proxy_settings)
        if u.username:
            proxy_password = u.password or proxy_password
            proxy_settings = urlparse.urlunparse((u.scheme,
                u.netloc.split("@")[-1], u.path, u.params, u.query,
                u.fragment))

    if proxy_username:
        user_auth = base64.encodestring('%s:%s' % (proxy_username,
                                    proxy_password))
        return proxy_settings, 'Basic %s\r\n' % (user_auth.strip())
    else:
        return proxy_settings, ''

########NEW FILE########
__FILENAME__ = conn
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import logging
import random
import select
import socket
import ssl
import time
import cStringIO

from socketpool import Connector
from socketpool.util import is_connected

CHUNK_SIZE = 16 * 1024
MAX_BODY = 1024 * 112
DNS_TIMEOUT = 60


class Connection(Connector):

    def __init__(self, host, port, backend_mod=None, pool=None,
            is_ssl=False, extra_headers=[], proxy_pieces=None, **ssl_args):

        # connect the socket, if we are using an SSL connection, we wrap
        # the socket.
        self._s = backend_mod.Socket(socket.AF_INET, socket.SOCK_STREAM)
        self._s.connect((host, port))
        if proxy_pieces:
            self._s.sendall(proxy_pieces)
            response = cStringIO.StringIO()
            while response.getvalue()[-4:] != '\r\n\r\n':
                response.write(self._s.recv(1))
            response.close()
        if is_ssl:
            self._s = ssl.wrap_socket(self._s, **ssl_args)

        self.extra_headers = extra_headers
        self.is_ssl = is_ssl
        self.backend_mod = backend_mod
        self.host = host
        self.port = port
        self._connected = True
        self._life =  time.time() - random.randint(0, 10)
        self._pool = pool
        self._released = False

    def matches(self, **match_options):
        target_host = match_options.get('host')
        target_port = match_options.get('port')
        return target_host == self.host and target_port == self.port

    def is_connected(self):
        if self._connected:
            return is_connected(self._s)
        return False

    def handle_exception(self, exception):
        raise

    def get_lifetime(self):
        return self._life

    def invalidate(self):
        self.close()
        self._connected = False
        self._life = -1

    def release(self, should_close=False):
        if self._pool is not None:
            if self._connected:
                if should_close:
                    self.invalidate()
                self._pool.release_connection(self)
            else:
                self._pool = None
        elif self._connected:
            self.invalidate()

    def close(self):
        if not self._s or not hasattr(self._s, "close"):
            return
        try:
            self._s.close()
        except:
            pass

    def socket(self):
        return self._s

    def send_chunk(self, data):
        chunk = "".join(("%X\r\n" % len(data), data, "\r\n"))
        self._s.sendall(chunk)

    def send(self, data, chunked=False):
        if chunked:
            return self.send_chunk(data)

        return self._s.sendall(data)

    def sendlines(self, lines, chunked=False):
        for line in list(lines):
            self.send(line, chunked=chunked)


    # TODO: add support for sendfile api
    def sendfile(self, data, chunked=False):
        """ send a data from a FileObject """

        if hasattr(data, 'seek'):
            data.seek(0)

        while True:
            binarydata = data.read(CHUNK_SIZE)
            if binarydata == '':
                break
            self.send(binarydata, chunked=chunked)


    def recv(self, size=1024):
        return self._s.recv(size)

########NEW FILE########
__FILENAME__ = console
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement
import os
import optparse as op
import sys

# import pygments if here
try:
    import pygments
    from pygments.lexers import get_lexer_for_mimetype
    from pygments.formatters import TerminalFormatter
except ImportError:
    pygments = False
    
# import json   
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = False

from restkit import __version__, request, set_logging
from restkit.util import popen3, locate_program

__usage__ = "'%prog [options] url [METHOD] [filename]'"


pretties = {
    'application/json': 'text/javascript',
    'text/plain': 'text/javascript'
}

def external(cmd, data):
    try:
        (child_stdin, child_stdout, child_stderr) = popen3(cmd)
        err = child_stderr.read()
        if err:
            return data
        return child_stdout.read()
    except:
        return data
        
def indent_xml(data):
    tidy_cmd = locate_program("tidy")
    if tidy_cmd:
        cmd = " ".join([tidy_cmd, '-qi', '-wrap', '70', '-utf8', data])
        return external(cmd, data)
    return data
    
def indent_json(data):
    if not json:
        return data
    info = json.loads(data)
    return json.dumps(info, indent=2, sort_keys=True)


common_indent = {
    'application/json': indent_json,
    'text/html': indent_xml,
    'text/xml': indent_xml,
    'application/xhtml+xml': indent_xml,
    'application/xml': indent_xml,
    'image/svg+xml': indent_xml,
    'application/rss+xml': indent_xml,
    'application/atom+xml': indent_xml,
    'application/xsl+xml': indent_xml,
    'application/xslt+xml': indent_xml
}

def indent(mimetype, data):
    if mimetype in common_indent:
        return common_indent[mimetype](data)
    return data
    
def prettify(response, cli=True):
    if not pygments or not 'content-type' in response.headers:
        return response.body_string()
        
    ctype = response.headers['content-type']
    try:
        mimetype, encoding = ctype.split(";")
    except ValueError:
        mimetype = ctype.split(";")[0]
        
    # indent body
    body = indent(mimetype, response.body_string())
    
    # get pygments mimetype
    mimetype = pretties.get(mimetype, mimetype)
    
    try:
        lexer = get_lexer_for_mimetype(mimetype)
        body = pygments.highlight(body, lexer, TerminalFormatter())
        return body
    except:
        return body

def as_bool(value):
    if value.lower() in ('true', '1'):
        return True
    return False

def update_defaults(defaults):
    config = os.path.expanduser('~/.restcli')
    if os.path.isfile(config):
        for line in open(config):
            key, value = line.split('=', 1)
            key = key.lower().strip()
            key = key.replace('-', '_')
            if key.startswith('header'):
                key = 'headers'
            value = value.strip()
            if key in defaults:
                default = defaults[key]
                if default in (True, False):
                    value = as_bool(value)
                elif isinstance(default, list):
                    default.append(value)
                    value = default
                defaults[key] = value

def options():
    """ build command lines options """

    defaults = dict(
            headers=[],
            request='GET',
            follow_redirect=False,
            server_response=False,
            prettify=False,
            log_level=None,
            input=None,
            output=None,
            )
    update_defaults(defaults)

    def opt_args(option, *help):
        help = ' '.join(help)
        help = help.strip()
        default = defaults.get(option)
        if default is not None:
            help += ' Default to %r.' % default
        return dict(default=defaults.get(option), help=help)

    return [
        op.make_option('-H', '--header', action='append', dest='headers',
                **opt_args('headers',
                           'HTTP string header in the form of Key:Value. ',
                           'For example: "Accept: application/json".')),
        op.make_option('-X', '--request', action='store', dest='method',
                       **opt_args('request', 'HTTP request method.')),
        op.make_option('--follow-redirect', action='store_true',
                       dest='follow_redirect', **opt_args('follow_redirect')),
        op.make_option('-S', '--server-response', action='store_true',
                       dest='server_response',
                       **opt_args('server_response', 'Print server response.')),
        op.make_option('-p', '--prettify', dest="prettify", action='store_true',
                       **opt_args('prettify', "Prettify display.")),
        op.make_option('--log-level', dest="log_level",
                       **opt_args('log_level',
                                  "Log level below which to silence messages.")),
        op.make_option('-i', '--input', action='store', dest='input',
                       metavar='FILE',
                       **opt_args('input', 'The name of the file to read from.')),
        op.make_option('-o', '--output', action='store', dest='output',
                       **opt_args('output', 'The name of the file to write to.')),
        op.make_option('--shell', action='store_true', dest='shell',
                       help='Open a IPython shell'),
    ]

def main():
    """ function to manage restkit command line """
    parser = op.OptionParser(usage=__usage__, option_list=options(),
                    version="%prog " + __version__)

    opts, args = parser.parse_args()
    args_len = len(args)

    if opts.shell:
        try:
            from restkit.contrib import ipython_shell as shell
            shell.main(options=opts, *args)
        except Exception, e:
            print >>sys.stderr, str(e)
            sys.exit(1)
        return

    if args_len < 1:
        return parser.error('incorrect number of arguments')

    if opts.log_level is not None:
        set_logging(opts.log_level)

    body = None
    headers = []
    if opts.input:
        if opts.input == '-':
            body = sys.stdin.read()
            headers.append(("Content-Length", str(len(body))))
        else:
            fname = os.path.normpath(os.path.join(os.getcwd(),opts.input))
            body = open(fname, 'r')
    
    if opts.headers:
        for header in opts.headers:
            try:
                k, v = header.split(':')
                headers.append((k, v))
            except ValueError:
                pass


    try:
        if len(args) == 2:
            if args[1] == "-" and not opts.input:
                body = sys.stdin.read()
                headers.append(("Content-Length", str(len(body))))

        if not opts.method and opts.input:
            method = 'POST'
        else:
            method=opts.method.upper()
            
        resp = request(args[0], method=method, body=body,
                    headers=headers, follow_redirect=opts.follow_redirect)
                        
        if opts.output and opts.output != '-':
            with open(opts.output, 'wb') as f:
                if opts.server_response:
                    f.write("Server response from %s:\n" % resp.final_url)
                    for k, v in resp.headerslist:
                        f.write( "%s: %s" % (k, v))
                else:
                    with resp.body_stream() as body:
                        for block in body:
                            f.write(block)
        else:
            if opts.server_response:
                if opts.prettify:
                    print "\n\033[0m\033[95mServer response from %s:\n\033[0m" % (
                                                                    resp.final_url)
                    for k, v in resp.headerslist:
                        print "\033[94m%s\033[0m: %s" % (k, v)
                    print "\033[0m"
                else:
                    print "Server response from %s:\n" % (resp.final_url)
                    for k, v in resp.headerslist:
                        print "%s: %s" % (k, v)
                    print ""

                if opts.output == '-':
                    if opts.prettify:
                        print prettify(resp)
                    else:
                        print resp.body_string()
            else:
                if opts.prettify:
                    print prettify(resp)
                else:
                    print resp.body_string()
        
    except Exception, e:
        sys.stderr.write("An error happened: %s" % str(e))
        sys.stderr.flush()
        sys.exit(1)

    sys.exit(0)
    

########NEW FILE########
__FILENAME__ = ipython_shell
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from StringIO import StringIO
import urlparse

try:
    from IPython.config.loader import Config
    from IPython.frontend.terminal.embed  import InteractiveShellEmbed
except ImportError:
    raise ImportError('IPython (http://pypi.python.org/pypi/ipython) >=0.11' +\
                    'is required.')
                    
try:
    import webob
except ImportError:
    raise ImportError('webob (http://pythonpaste.org/webob/) is required.')

from webob import Response as BaseResponse

from restkit import __version__
from restkit.contrib.console import common_indent, json
from restkit.contrib.webob_api import Request as BaseRequest


class Stream(StringIO):
    def __repr__(self):
        return '<Stream(%s)>' % self.len


class JSON(Stream):
    def __init__(self, value):
        self.__value = value
        if json:
            Stream.__init__(self, json.dumps(value))
        else:
            Stream.__init__(self, value)
    def __repr__(self):
        return '<JSON(%s)>' % self.__value


class Response(BaseResponse):
    def __str__(self, skip_body=True):
        if self.content_length < 200 and skip_body:
            skip_body = False
        return BaseResponse.__str__(self, skip_body=skip_body)
    def __call__(self):
        print self


class Request(BaseRequest):
    ResponseClass = Response
    def get_response(self, *args, **kwargs):
        url = self.url
        stream = None
        for a in args:
            if isinstance(a, Stream):
                stream = a
                a.seek(0)
                continue
            elif isinstance(a, basestring):
                if a.startswith('http'):
                    url = a
                elif a.startswith('/'):
                    url = a

        self.set_url(url)

        if stream:
            self.body_file = stream
            self.content_length = stream.len
        if self.method == 'GET' and kwargs:
            for k, v in kwargs.items():
                self.GET[k] = v
        elif self.method == 'POST' and kwargs:
            for k, v in kwargs.items():
                self.GET[k] = v
        return BaseRequest.get_response(self)

    def __str__(self, skip_body=True):
        if self.content_length < 200 and skip_body:
            skip_body = False
        return BaseRequest.__str__(self, skip_body=skip_body)

    def __call__(self):
        print self


class ContentTypes(object):
    _values = {}
    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, sorted(self._values))
    def __str__(self):
        return '\n'.join(['%-20.20s: %s' % h for h in \
                                            sorted(self._value.items())])


ctypes = ContentTypes()
for k in common_indent:
    attr = k.replace('/', '_').replace('+', '_')
    ctypes._values[attr] = attr
    ctypes.__dict__[attr] = k
del k, attr


class RestShell(InteractiveShellEmbed):
    def __init__(self, user_ns={}):

        cfg = Config()
        shell_config = cfg.InteractiveShellEmbed
        shell_config.prompt_in1 = '\C_Blue\#) \C_Greenrestcli\$ '

        super(RestShell, self).__init__(config = cfg,
                banner1= 'restkit shell %s' % __version__,
                exit_msg="quit restcli shell", user_ns=user_ns)
        

class ShellClient(object):
    methods = dict(
            get='[req|url|path_info], **query_string',
            post='[req|url|path_info], [Stream()|**query_string_body]',
            head='[req|url|path_info], **query_string',
            put='[req|url|path_info], stream',
            delete='[req|url|path_info]')

    def __init__(self, url='/', options=None, **kwargs):
        self.options = options
        self.url = url or '/'
        self.ns = {}
        self.shell = RestShell(user_ns=self.ns)
        self.update_ns(self.ns)
        self.help()
        self.shell(header='', global_ns={}, local_ns={})

    def update_ns(self, ns):
        for k in self.methods:
            ns[k] = self.request_meth(k)
        stream = None
        headers = {}
        if self.options:
            if self.options.input:
                stream = Stream(open(self.options.input).read())
            if self.options.headers:
                for header in self.options.headers:
                    try:
                        k, v = header.split(':')
                        headers.append((k, v))
                    except ValueError:
                        pass
        req = Request.blank('/')
        req._client = self
        del req.content_type
        if stream:
            req.body_file = stream

        req.headers = headers
        req.set_url(self.url)
        ns.update(
                  Request=Request,
                  Response=Response,
                  Stream=Stream,
                  req=req,
                  stream=stream,
                  ctypes=ctypes,
                  )
        if json:
            ns['JSON'] = JSON

    def request_meth(self, k):
        def req(*args, **kwargs):
            resp = self.request(k.upper(), *args, **kwargs)
            self.shell.user_ns.update(dict(resp=resp))

            print resp
            return resp
        req.func_name = k
        req.__name__ = k
        req.__doc__ =  """send a HTTP %s""" % k.upper()
        return req

    def request(self, meth, *args, **kwargs):
        """forward to restkit.request"""
        req = None
        for a in args:
            if isinstance(a, Request):
                req = a
                args = [a for a in args if a is not req]
                break
        if req is None:
            req = self.shell.user_ns.get('req')
            if not isinstance(req, Request):
                req = Request.blank('/')
                del req.content_type
        req.method = meth

        req.set_url(self.url)
        resp = req.get_response(*args, **kwargs)
        self.url = req.url
        return resp

    def help(self):
        ns = self.ns.copy()
        methods = ''
        for k in sorted(self.methods):
            args = self.methods[k]
            doc = '  >>> %s(%s)' % (k, args)
            methods += '%-65.65s # send a HTTP %s\n' % (doc, k)
        ns['methods'] = methods
        print HELP.strip() % ns
        print ''

    def __repr__(self):
        return '<shellclient>'


def main(*args, **kwargs):
    for a in args:
        if a.startswith('http://'):
            kwargs['url'] = a
    ShellClient(**kwargs)


HELP = """
restkit shell
=============

HTTP Methods
------------

%(methods)s
Helpers
-------

  >>> req    # request to play with. By default http methods will use this one
  %(req)r

  >>> stream # Stream() instance if you specified a -i in command line
  %(stream)r

  >>> ctypes # Content-Types helper with headers properties
  %(ctypes)r
"""

if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = webob_api
#!/usr/bin/env python
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import base64
from StringIO import StringIO
import urlparse
import urllib

try:
    from webob import Request as BaseRequest
except ImportError:
    raise ImportError('WebOb (http://pypi.python.org/pypi/WebOb) is required')

from .wsgi_proxy import Proxy

__doc__ = '''Subclasses of webob.Request who use restkit to get a
webob.Response via restkit.ext.wsgi_proxy.Proxy.

Example::

    >>> req = Request.blank('http://pypi.python.org/pypi/restkit')
    >>> resp = req.get_response()
    >>> print resp #doctest: +ELLIPSIS
    200 OK
    Date: ...
    Transfer-Encoding: chunked
    Content-Type: text/html; charset=utf-8
    Server: Apache/2...
    <BLANKLINE>
    <?xml version="1.0" encoding="UTF-8"?>
    ...
    

'''

PROXY = Proxy(allowed_methods=['GET', 'POST', 'HEAD', 'DELETE', 'PUT', 'PURGE'])

class Method(property):
    def __init__(self, name):
        self.name = name
    def __get__(self, instance, klass):
        if not instance:
            return self
        instance.method = self.name.upper()
        def req(*args, **kwargs):
            return instance.get_response(*args, **kwargs)
        return req


class Request(BaseRequest):
    get = Method('get')
    post = Method('post')
    put = Method('put')
    head = Method('head')
    delete = Method('delete')
    
    def get_response(self):
        if self.content_length < 0:
            self.content_length = 0
        if self.method in ('DELETE', 'GET'):
            self.body = ''
        elif self.method == 'POST' and self.POST:
            body = urllib.urlencode(self.POST.copy())
            stream = StringIO(body)
            stream.seek(0)
            self.body_file = stream
            self.content_length = stream.len
            if 'form' not in self.content_type:
                self.content_type = 'application/x-www-form-urlencoded'
        self.server_name = self.host
        return BaseRequest.get_response(self, PROXY)

    __call__ = get_response

    def set_url(self, url):

        path = url.lstrip('/')

        if url.startswith("http://") or url.startswith("https://"):
            u = urlparse.urlsplit(url)
            if u.username is not None:
                password = u.password or ""
                encode = base64.b64encode("%s:%s" % (u.username, password))
                self.headers['Authorization'] = 'Basic %s' %  encode

            self.scheme = u.scheme,
            self.host = u.netloc.split("@")[-1]
            self.path_info = u.path or "/"
            self.query_string = u.query
            url = urlparse.urlunsplit((u.scheme, u.netloc.split("@")[-1], 
                u.path, u.query, u.fragment))
        else:
        
            if '?' in path:
                path, self.query_string = path.split('?', 1)
            self.path_info = '/' + path
            

            url = self.url
        self.scheme, self.host, self.path_info = urlparse.urlparse(url)[0:3]


########NEW FILE########
__FILENAME__ = webob_helper
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import webob.exc

from restkit import errors

class WebobResourceError(webob.exc.WSGIHTTPException):
    """
    Wrapper to return webob exceptions instead of restkit errors. Usefull
    for those who want to build `WSGI <http://wsgi.org/wsgi/>`_ applications
    speaking directly to others via HTTP.
    
    To do it place somewhere in your application the function 
    `wrap_exceptions`::
    
        wrap_exceptions()

    It will automatically replace restkit errors by webob exceptions.
    """

    def __init__(self, msg=None, http_code=None, response=None):
        webob.exc.WSGIHTTPException.__init__(self)
        
        http_code = http_code or 500
        klass = webob.exc.status_map[http_code]
        self.code = http_code
        self.title = klass.title
        self.status = '%s %s' % (self.code, self.title)
        self.explanation = msg
        self.response = response
        # default params
        self.msg = msg

    def _status_int__get(self):
        """
        The status as an integer
        """
        return int(self.status.split()[0])
    def _status_int__set(self, value):
        self.status = value
    status_int = property(_status_int__get, _status_int__set, 
        doc=_status_int__get.__doc__)

    def _get_message(self):
        return self.explanation
    def _set_message(self, msg):
        self.explanation = msg or ''
    message = property(_get_message, _set_message)

webob_exceptions = False
def wrap_exceptions():
    """ wrap restkit exception to return WebBob exceptions"""
    global webob_exceptions
    if webob_exceptions: return
    errors.ResourceError = WebobResourceError
    webob_exceptions = True
    

########NEW FILE########
__FILENAME__ = wsgi_proxy
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from restkit.client import Client
from restkit.conn import MAX_BODY
from restkit.util import rewrite_location

ALLOWED_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']

BLOCK_SIZE = 4096 * 16

WEBOB_ERROR = ("Content-Length is set to -1. This usually mean that WebOb has "
        "already parsed the content body. You should set the Content-Length "
        "header to the correct value before forwarding your request to the "
        "proxy: ``req.content_length = str(len(req.body));`` "
        "req.get_response(proxy)")

class Proxy(object):
    """A proxy wich redirect the request to SERVER_NAME:SERVER_PORT
    and send HTTP_HOST header"""

    def __init__(self, manager=None, allowed_methods=ALLOWED_METHODS,
            strip_script_name=True,  **kwargs):
        self.allowed_methods = allowed_methods
        self.strip_script_name = strip_script_name
        self.client = Client(**kwargs)

    def extract_uri(self, environ):
        port = None
        scheme = environ['wsgi.url_scheme']
        if 'SERVER_NAME' in environ:
            host = environ['SERVER_NAME']
        else:
            host = environ['HTTP_HOST']
        if ':' in host:
            host, port = host.split(':')

        if not port:
            if 'SERVER_PORT' in environ:
                port = environ['SERVER_PORT']
            else:
                port = scheme == 'https' and '443' or '80'

        uri = '%s://%s:%s' % (scheme, host, port)
        return uri

    def __call__(self, environ, start_response):
        method = environ['REQUEST_METHOD']
        if method not in self.allowed_methods:
            start_response('403 Forbidden', ())
            return ['']

        if self.strip_script_name:
            path_info = ''
        else:
            path_info = environ['SCRIPT_NAME']
        path_info += environ['PATH_INFO']

        query_string = environ['QUERY_STRING']
        if query_string:
            path_info += '?' + query_string

        host_uri = self.extract_uri(environ)
        uri = host_uri + path_info

        new_headers = {}
        for k, v in environ.items():
            if k.startswith('HTTP_'):
                k = k[5:].replace('_', '-').title()
                new_headers[k] = v


        ctype = environ.get("CONTENT_TYPE")
        if ctype and ctype is not None:
            new_headers['Content-Type'] = ctype

        clen = environ.get('CONTENT_LENGTH')
        te =  environ.get('transfer-encoding', '').lower()
        if not clen and te != 'chunked':
            new_headers['transfer-encoding'] = 'chunked'
        elif clen:
            new_headers['Content-Length'] = clen

        if new_headers.get('Content-Length', '0') == '-1':
            raise ValueError(WEBOB_ERROR)

        response = self.client.request(uri, method, body=environ['wsgi.input'],
                headers=new_headers)

        if 'location' in response:
            if self.strip_script_name:
                prefix_path = environ['SCRIPT_NAME']

            new_location = rewrite_location(host_uri, response.location,
                    prefix_path=prefix_path)

            headers = []
            for k, v in response.headerslist:
                if k.lower() == 'location':
                    v = new_location
                headers.append((k, v))
        else:
            headers = response.headerslist

        start_response(response.status, headers)

        if method == "HEAD":
            return StringIO()

        return response.tee()

class TransparentProxy(Proxy):
    """A proxy based on HTTP_HOST environ variable"""

    def extract_uri(self, environ):
        port = None
        scheme = environ['wsgi.url_scheme']
        host = environ['HTTP_HOST']
        if ':' in host:
            host, port = host.split(':')

        if not port:
            port = scheme == 'https' and '443' or '80'

        uri = '%s://%s:%s' % (scheme, host, port)
        return uri


class HostProxy(Proxy):
    """A proxy to redirect all request to a specific uri"""

    def __init__(self, uri, **kwargs):
        super(HostProxy, self).__init__(**kwargs)
        self.uri = uri.rstrip('/')
        self.scheme, self.net_loc = urlparse.urlparse(self.uri)[0:2]

    def extract_uri(self, environ):
        environ['HTTP_HOST'] = self.net_loc
        return self.uri

def get_config(local_config):
    """parse paste config"""
    config = {}
    allowed_methods = local_config.get('allowed_methods', None)
    if allowed_methods:
        config['allowed_methods'] = [m.upper() for m in allowed_methods.split()]
    strip_script_name = local_config.get('strip_script_name', 'true')
    if strip_script_name.lower() in ('false', '0'):
        config['strip_script_name'] = False
    config['max_connections'] = int(local_config.get('max_connections', '5'))
    return config

def make_proxy(global_config, **local_config):
    """TransparentProxy entry_point"""
    config = get_config(local_config)
    return TransparentProxy(**config)

def make_host_proxy(global_config, uri=None, **local_config):
    """HostProxy entry_point"""
    uri = uri.rstrip('/')
    config = get_config(local_config)
    return HostProxy(uri, **config)

########NEW FILE########
__FILENAME__ = datastructures
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

try:
    from UserDict import DictMixin
except ImportError:    
    from collections import MutableMapping as DictMixin
 
 
class MultiDict(DictMixin):

    """
        An ordered dictionary that can have multiple values for each key.
        Adds the methods getall, getone, mixed and extend and add to the normal
        dictionary interface.
    """

    def __init__(self, *args, **kw):
        if len(args) > 1:
            raise TypeError("MultiDict can only be called with one positional argument")
        if args:
            if isinstance(args[0], MultiDict):
                items = args[0]._items
            elif hasattr(args[0], 'iteritems'):
                items = list(args[0].iteritems())
            elif hasattr(args[0], 'items'):
                items = args[0].items()
            else:
                items = list(args[0])
            self._items = items
        else:
            self._items = []
        if kw:
            self._items.extend(kw.iteritems())

    @classmethod
    def from_fieldstorage(cls, fs):
        """
        Create a dict from a cgi.FieldStorage instance
        """
        obj = cls()
        # fs.list can be None when there's nothing to parse
        for field in fs.list or ():
            if field.filename:
                obj.add(field.name, field)
            else:
                obj.add(field.name, field.value)
        return obj

    def __getitem__(self, key):
        for k, v in reversed(self._items):
            if k == key:
                return v
        raise KeyError(key)

    def __setitem__(self, key, value):
        try:
            del self[key]
        except KeyError:
            pass
        self._items.append((key, value))

    def add(self, key, value):
        """
        Add the key and value, not overwriting any previous value.
        """
        self._items.append((key, value))

    def getall(self, key):
        """
        Return a list of all values matching the key (may be an empty list)
        """
        return [v for k, v in self._items if k == key]

    def iget(self, key):
        """like get but case insensitive """
        lkey = key.lower()
        for k, v in self._items:
            if k.lower() == lkey:
                return v
        return None

    def getone(self, key):
        """
        Get one value matching the key, raising a KeyError if multiple
        values were found.
        """
        v = self.getall(key)
        if not v:
            raise KeyError('Key not found: %r' % key)
        if len(v) > 1:
            raise KeyError('Multiple values match %r: %r' % (key, v))
        return v[0]

    def mixed(self):
        """
        Returns a dictionary where the values are either single
        values, or a list of values when a key/value appears more than
        once in this dictionary.  This is similar to the kind of
        dictionary often used to represent the variables in a web
        request.
        """
        result = {}
        multi = {}
        for key, value in self.iteritems():
            if key in result:
                # We do this to not clobber any lists that are
                # *actual* values in this dictionary:
                if key in multi:
                    result[key].append(value)
                else:
                    result[key] = [result[key], value]
                    multi[key] = None
            else:
                result[key] = value
        return result

    def dict_of_lists(self):
        """
        Returns a dictionary where each key is associated with a list of values.
        """
        r = {}
        for key, val in self.iteritems():
            r.setdefault(key, []).append(val)
        return r

    def __delitem__(self, key):
        items = self._items
        found = False
        for i in range(len(items)-1, -1, -1):
            if items[i][0] == key:
                del items[i]
                found = True
        if not found:
            raise KeyError(key)

    def __contains__(self, key):
        for k, v in self._items:
            if k == key:
                return True
        return False

    has_key = __contains__

    def clear(self):
        self._items = []

    def copy(self):
        return self.__class__(self)

    def setdefault(self, key, default=None):
        for k, v in self._items:
            if key == k:
                return v
        self._items.append((key, default))
        return default

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError, "pop expected at most 2 arguments, got "\
                              + repr(1 + len(args))
        for i in range(len(self._items)):
            if self._items[i][0] == key:
                v = self._items[i][1]
                del self._items[i]
                return v
        if args:
            return args[0]
        else:
            raise KeyError(key)

    def ipop(self, key, *args):
        """ like pop but case insensitive """
        if len(args) > 1:
            raise TypeError, "pop expected at most 2 arguments, got "\
                              + repr(1 + len(args))

        lkey = key.lower()
        for i, item in enumerate(self._items):
            if item[0].lower() == lkey:
                v = self._items[i][1]
                del self._items[i]
                return v
        if args:
            return args[0]
        else:
            raise KeyError(key)

    def popitem(self):
        return self._items.pop()

    def extend(self, other=None, **kwargs):
        if other is None:
            pass
        elif hasattr(other, 'items'):
            self._items.extend(other.items())
        elif hasattr(other, 'keys'):
            for k in other.keys():
                self._items.append((k, other[k]))
        else:
            for k, v in other:
                self._items.append((k, v))
        if kwargs:
            self.update(kwargs)

    def __repr__(self):
        items = ', '.join(['(%r, %r)' % v for v in self.iteritems()])
        return '%s([%s])' % (self.__class__.__name__, items)

    def __len__(self):
        return len(self._items)

    ##
    ## All the iteration:
    ##

    def keys(self):
        return [k for k, v in self._items]

    def iterkeys(self):
        for k, v in self._items:
            yield k

    __iter__ = iterkeys

    def items(self):
        return self._items[:]

    def iteritems(self):
        return iter(self._items)

    def values(self):
        return [v for k, v in self._items]

    def itervalues(self):
        for k, v in self._items:
            yield v



########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

"""
exception classes.
"""

class ResourceError(Exception):
    """ default error class """

    status_int = None

    def __init__(self, msg=None, http_code=None, response=None):
        self.msg = msg or ''
        self.status_int = http_code or self.status_int
        self.response = response
        Exception.__init__(self)

    def _get_message(self):
        return self.msg
    def _set_message(self, msg):
        self.msg = msg or ''
    message = property(_get_message, _set_message)

    def __str__(self):
        if self.msg:
            return self.msg
        try:
            return str(self.__dict__)
        except (NameError, ValueError, KeyError), e:
            return 'Unprintable exception %s: %s' \
                % (self.__class__.__name__, str(e))


class ResourceNotFound(ResourceError):
    """Exception raised when no resource was found at the given url.
    """
    status_int = 404

class Unauthorized(ResourceError):
    """Exception raised when an authorization is required to access to
    the resource specified.
    """

class ResourceGone(ResourceError):
    """
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.11
    """
    status_int = 410

class RequestFailed(ResourceError):
    """Exception raised when an unexpected HTTP error is received in response
    to a request.


    The request failed, meaning the remote HTTP server returned a code
    other than success, unauthorized, or NotFound.

    The exception message attempts to extract the error

    You can get the status code by e.status_int, or see anything about the
    response via e.response. For example, the entire result body (which is
    probably an HTML error page) is e.response.body.
    """

class RedirectLimit(Exception):
    """Exception raised when the redirection limit is reached."""

class RequestError(Exception):
    """Exception raised when a request is malformed"""

class RequestTimeout(Exception):
    """ Exception raised on socket timeout """

class InvalidUrl(Exception):
    """
    Not a valid url for use with this software.
    """

class ResponseError(Exception):
    """ Error raised while getting response or decompressing response stream"""


class ProxyError(Exception):
    """ raised when proxy error happend"""

class BadStatusLine(Exception):
    """ Exception returned by the parser when the status line is invalid"""
    pass

class ParserError(Exception):
    """ Generic exception returned by the parser """
    pass

class UnexpectedEOF(Exception):
    """ exception raised when remote closed the connection """

class AlreadyRead(Exception):
    """ raised when a response have already been read """

class ProxyError(Exception):
    pass

#############################
# HTTP parser errors
#############################

class ParseException(Exception):
    pass

class NoMoreData(ParseException):
    def __init__(self, buf=None):
        self.buf = buf
    def __str__(self):
        return "No more data after: %r" % self.buf

class InvalidRequestLine(ParseException):
    def __init__(self, req):
        self.req = req
        self.code = 400

    def __str__(self):
        return "Invalid HTTP request line: %r" % self.req

class InvalidRequestMethod(ParseException):
    def __init__(self, method):
        self.method = method

    def __str__(self):
        return "Invalid HTTP method: %r" % self.method

class InvalidHTTPVersion(ParseException):
    def __init__(self, version):
        self.version = version

    def __str__(self):
        return "Invalid HTTP Version: %s" % self.version

class InvalidHTTPStatus(ParseException):
    def __init__(self, status):
        self.status = status

    def __str__(self):
        return "Invalid HTTP Status: %s" % self.status

class InvalidHeader(ParseException):
    def __init__(self, hdr):
        self.hdr = hdr

    def __str__(self):
        return "Invalid HTTP Header: %r" % self.hdr

class InvalidHeaderName(ParseException):
    def __init__(self, hdr):
        self.hdr = hdr

    def __str__(self):
        return "Invalid HTTP header name: %r" % self.hdr

class InvalidChunkSize(ParseException):
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return "Invalid chunk size: %r" % self.data

class ChunkMissingTerminator(ParseException):
    def __init__(self, term):
        self.term = term

    def __str__(self):
        return "Invalid chunk terminator is not '\\r\\n': %r" % self.term

class HeaderLimit(ParseException):
    """ exception raised when we gore more headers than
    max_header_count
    """

########NEW FILE########
__FILENAME__ = filters
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import base64
import re
try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl
from urlparse import urlunparse

from restkit.oauth2 import Request, SignatureMethod_HMAC_SHA1

class BasicAuth(object):
    """ Simple filter to manage basic authentification"""
    
    def __init__(self, username, password):
        self.credentials = (username, password)
    
    def on_request(self, request):
        encode = base64.b64encode("%s:%s" % self.credentials)
        request.headers['Authorization'] = 'Basic %s' %  encode

def validate_consumer(consumer):
    """ validate a consumer agains oauth2.Consumer object """
    if not hasattr(consumer, "key"):
        raise ValueError("Invalid consumer.")
    return consumer
    
def validate_token(token):
    """ validate a token agains oauth2.Token object """
    if token is not None and not hasattr(token, "key"):
        raise ValueError("Invalid token.")
    return token


class OAuthFilter(object):
    """ oauth filter """

    def __init__(self, path, consumer, token=None, method=None, 
            realm=""):
        """ Init OAuthFilter
        
        :param path: path or regexp. * mean all path on wicth oauth can be
        applied.
        :param consumer: oauth consumer, instance of oauth2.Consumer
        :param token: oauth token, instance of oauth2.Token
        :param method: oauth signature method
        
        token and method signature are optionnals. Consumer should be an 
        instance of `oauth2.Consumer`, token an  instance of `oauth2.Toke` 
        signature method an instance of `oauth2.SignatureMethod`.

        """
        
        if path.endswith('*'):
            self.match = re.compile("%s.*" % path.rsplit('*', 1)[0])
        else:
            self.match = re.compile("%s$" % path)
        self.consumer = validate_consumer(consumer)
        self.token = validate_token(token)
        self.method = method or SignatureMethod_HMAC_SHA1()
        self.realm = realm
  
    def on_path(self, request):
        path = request.parsed_url.path or "/"
        return (self.match.match(path) is not None)
        
    def on_request(self, request):
        if not self.on_path(request):
            return

        params = {}
        form = False
        parsed_url = request.parsed_url

        if request.body and request.body is not None:
            ctype = request.headers.iget('content-type')
            if ctype is not None and \
                    ctype.startswith('application/x-www-form-urlencoded'):
                # we are in a form try to get oauth params from here
                form = True
                params = dict(parse_qsl(request.body))
            
        # update params from quey parameters    
        params.update(parse_qsl(parsed_url.query))
      
        raw_url = urlunparse((parsed_url.scheme, parsed_url.netloc,
                parsed_url.path, '', '', ''))

        oauth_req = Request.from_consumer_and_token(self.consumer, 
                        token=self.token, http_method=request.method, 
                        http_url=raw_url, parameters=params,
                        is_form_encoded=form)

        oauth_req.sign_request(self.method, self.consumer, self.token)
        
        if form:
            request.body = oauth_req.to_postdata()
            
            request.headers['Content-Length'] = len(request.body)
        elif request.method in ('GET', 'HEAD'):
            request.original_url = request.url
            request.url = oauth_req.to_url()
        else:
            oauth_headers = oauth_req.to_header(realm=self.realm)
            request.headers.update(oauth_headers)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import mimetypes
import os
import re
import urllib


from restkit.util import to_bytestring, url_quote, url_encode

MIME_BOUNDARY = 'END_OF_PART'
CRLF = '\r\n'

def form_encode(obj, charset="utf8"):
    encoded = url_encode(obj, charset=charset)
    return to_bytestring(encoded)


class BoundaryItem(object):
    def __init__(self, name, value, fname=None, filetype=None, filesize=None,
                 quote=url_quote):
        self.quote = quote
        self.name = quote(name)
        if value is not None and not hasattr(value, 'read'):
            value = self.encode_unreadable_value(value)
            self.size = len(value)
        self.value = value
        if fname is not None:
            if isinstance(fname, unicode):
                fname = fname.encode("utf-8").encode("string_escape").replace('"', '\\"')
            else:
                fname = fname.encode("string_escape").replace('"', '\\"')
        self.fname = fname
        if filetype is not None:
            filetype = to_bytestring(filetype)
        self.filetype = filetype

        if isinstance(value, file) and filesize is None:
            try:
                value.flush()
            except IOError:
                pass
            self.size = int(os.fstat(value.fileno())[6])

        self._encoded_hdr = None
        self._encoded_bdr = None

    def encode_hdr(self, boundary):
        """Returns the header of the encoding of this parameter"""
        if not self._encoded_hdr or self._encoded_bdr != boundary:
            boundary = self.quote(boundary)
            self._encoded_bdr = boundary
            headers = ["--%s" % boundary]
            if self.fname:
                disposition = 'form-data; name="%s"; filename="%s"' % (self.name,
                        self.fname)
            else:
                disposition = 'form-data; name="%s"' % self.name
            headers.append("Content-Disposition: %s" % disposition)
            if self.filetype:
                filetype = self.filetype
            else:
                filetype = "text/plain; charset=utf-8"
            headers.append("Content-Type: %s" % filetype)
            headers.append("Content-Length: %i" % self.size)
            headers.append("")
            headers.append("")
            self._encoded_hdr = CRLF.join(headers)
        return self._encoded_hdr

    def encode(self, boundary):
        """Returns the string encoding of this parameter"""
        value = self.value
        if re.search("^--%s$" % re.escape(boundary), value, re.M):
            raise ValueError("boundary found in encoded string")

        return "%s%s%s" % (self.encode_hdr(boundary), value, CRLF)

    def iter_encode(self, boundary, blocksize=16384):
        if not hasattr(self.value, "read"):
            yield self.encode(boundary)
        else:
            yield self.encode_hdr(boundary)
            while True:
                block = self.value.read(blocksize)
                if not block:
                    yield CRLF
                    return
                yield block

    def encode_unreadable_value(self, value):
            return value


class MultipartForm(object):
    def __init__(self, params, boundary, headers, bitem_cls=BoundaryItem,
                 quote=url_quote):
        self.boundary = boundary
        self.tboundary = "--%s--%s" % (boundary, CRLF)
        self.boundaries = []
        self._clen = headers.get('Content-Length')

        if hasattr(params, 'items'):
            params = params.items()

        for param in params:
            name, value = param
            if hasattr(value, "read"):
                fname = getattr(value, 'name')
                if fname is not None:
                    filetype = ';'.join(filter(None, mimetypes.guess_type(fname)))
                else:
                    filetype = None
                if not isinstance(value, file) and self._clen is None:
                    value = value.read()

                boundary = bitem_cls(name, value, fname, filetype, quote=quote)
                self.boundaries.append(boundary)
            elif isinstance(value, list):
                for v in value:
                    boundary = bitem_cls(name, v, quote=quote)
                    self.boundaries.append(boundary)
            else:
                boundary = bitem_cls(name, value, quote=quote)
                self.boundaries.append(boundary)

    def get_size(self, recalc=False):
        if self._clen is None or recalc:
            self._clen = 0
            for boundary in self.boundaries:
                self._clen += boundary.size
                self._clen += len(boundary.encode_hdr(self.boundary))
                self._clen += len(CRLF)
            self._clen += len(self.tboundary)
        return int(self._clen)

    def __iter__(self):
        for boundary in self.boundaries:
            for block in boundary.iter_encode(self.boundary):
                yield block
        yield self.tboundary


def multipart_form_encode(params, headers, boundary, quote=url_quote):
    """Creates a tuple with MultipartForm instance as body and dict as headers

    params
      dict with fields for the body

    headers
      dict with fields for the header

    boundary
      string to use as boundary

    quote (default: url_quote)
      some callable expecting a string an returning a string. Use for quoting of
      boundary and form-data keys (names).
    """
    headers = headers or {}
    boundary = quote(boundary)
    body = MultipartForm(params, boundary, headers, quote=quote)
    headers['Content-Type'] = "multipart/form-data; boundary=%s" % boundary
    headers['Content-Length'] = str(body.get_size())
    return body, headers

########NEW FILE########
__FILENAME__ = oauth2
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import base64
import urllib
import time
import random
import urlparse
import hmac
import binascii

try:
    from urlparse import parse_qs, parse_qsl
except ImportError:
    from cgi import parse_qs, parse_qsl

from restkit.util import to_bytestring


try:
    from hashlib import sha1
    sha = sha1
except ImportError:
    # hashlib was added in Python 2.5
    import sha

from restkit.version import __version__

OAUTH_VERSION = '1.0'  # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class Error(RuntimeError):
    """Generic exception class."""

    def __init__(self, message='OAuth error occurred.'):
        self._message = message

    @property
    def message(self):
        """A hack to get around the deprecation errors in 2.6."""
        return self._message

    def __str__(self):
        return self._message


class MissingSignature(Error):
    pass


def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}


def build_xoauth_string(url, consumer, token=None):
    """Build an XOAUTH string for use in SMTP/IMPA authentication."""
    request = Request.from_consumer_and_token(consumer, token,
        "GET", url)

    signing_method = SignatureMethod_HMAC_SHA1()
    request.sign_request(signing_method, consumer, token)

    params = []
    for k, v in sorted(request.iteritems()):
        if v is not None:
            params.append('%s="%s"' % (k, escape(v)))

    return "%s %s %s" % ("GET", url, ','.join(params))


def to_unicode(s):
    """ Convert to unicode, raise exception with instructive error
    message if s is not unicode, ascii, or utf-8. """
    if not isinstance(s, unicode):
        if not isinstance(s, str):
            raise TypeError('You are required to pass either unicode or string here, not: %r (%s)' % (type(s), s))
        try:
            s = s.decode('utf-8')
        except UnicodeDecodeError, le:
            raise TypeError('You are required to pass either a unicode object or a utf-8 string here. You passed a Python string object which contained non-utf-8: %r. The UnicodeDecodeError that resulted from attempting to interpret it as utf-8 was: %s' % (s, le,))
    return s

def to_utf8(s):
    return to_unicode(s).encode('utf-8')

def to_unicode_if_string(s):
    if isinstance(s, basestring):
        return to_unicode(s)
    else:
        return s

def to_utf8_if_string(s):
    if isinstance(s, basestring):
        return to_utf8(s)
    else:
        return s

def to_unicode_optional_iterator(x):
    """
    Raise TypeError if x is a str containing non-utf8 bytes or if x is
    an iterable which contains such a str.
    """
    if isinstance(x, basestring):
        return to_unicode(x)

    try:
        l = list(x)
    except TypeError, e:
        assert 'is not iterable' in str(e)
        return x
    else:
        return [ to_unicode(e) for e in l ]

def to_utf8_optional_iterator(x):
    """
    Raise TypeError if x is a str or if x is an iterable which
    contains a str.
    """
    if isinstance(x, basestring):
        return to_utf8(x)

    try:
        l = list(x)
    except TypeError, e:
        assert 'is not iterable' in str(e)
        return x
    else:
        return [ to_utf8_if_string(e) for e in l ]

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s.encode('utf-8'), safe='~')

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())


def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class Consumer(object):
    """A consumer of OAuth-protected services.
 
    The OAuth consumer is a "third-party" service that wants to access
    protected resources from an OAuth service provider on behalf of an end
    user. It's kind of the OAuth client.
 
    Usually a consumer must be registered with the service provider by the
    developer of the consumer software. As part of that process, the service
    provider gives the consumer a *key* and a *secret* with which the consumer
    software can identify itself to the service. The consumer will include its
    key in each request to identify itself, but will use its secret only when
    signing requests, to prove that the request is from that particular
    registered consumer.
 
    Once registered, the consumer can then use its consumer credentials to ask
    the service provider for a request token, kicking off the OAuth
    authorization process.
    """

    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

        if self.key is None or self.secret is None:
            raise ValueError("Key and secret must be set.")

    def __str__(self):
        data = {'oauth_consumer_key': self.key,
            'oauth_consumer_secret': self.secret}

        return urllib.urlencode(data)


class Token(object):
    """An OAuth credential used to request authorization or a protected
    resource.
 
    Tokens in OAuth comprise a *key* and a *secret*. The key is included in
    requests to identify the token being used, but the secret is used only in
    the signature, to prove that the requester is who the server gave the
    token to.
 
    When first negotiating the authorization, the consumer asks for a *request
    token* that the live user authorizes with the service provider. The
    consumer then exchanges the request token for an *access token* that can
    be used to access protected resources.
    """

    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

        if self.key is None or self.secret is None:
            raise ValueError("Key and secret must be set.")

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        """Returns this token as a plain string, suitable for storage.
 
        The resulting string includes the token's secret, so you should never
        send or store this string where a third party can read it.
        """

        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }

        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    @staticmethod
    def from_string(s):
        """Deserializes a token from a string like one returned by
        `to_string()`."""

        if not len(s):
            raise ValueError("Invalid parameter string.")

        params = parse_qs(s, keep_blank_values=False)
        if not len(params):
            raise ValueError("Invalid parameter string.")

        try:
            key = params['oauth_token'][0]
        except Exception:
            raise ValueError("'oauth_token' not found in OAuth request.")

        try:
            secret = params['oauth_token_secret'][0]
        except Exception:
            raise ValueError("'oauth_token_secret' not found in " 
                "OAuth request.")

        token = Token(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass  # 1.0, no callback confirmed.
        return token

    def __str__(self):
        return self.to_string()


def setter(attr):
    name = attr.__name__
 
    def getter(self):
        try:
            return self.__dict__[name]
        except KeyError:
            raise AttributeError(name)
 
    def deleter(self):
        del self.__dict__[name]
 
    return property(getter, attr, deleter)


class Request(dict):
 
    """The parameters and information for an HTTP request, suitable for
    authorizing with OAuth credentials.
 
    When a consumer wants to access a service's protected resources, it does
    so using a signed HTTP request identifying itself (the consumer) with its
    key, and providing an access token authorized by the end user to access
    those resources.
 
    """
 
    version = OAUTH_VERSION

    def __init__(self, method=HTTP_METHOD, url=None, parameters=None,
                 body='', is_form_encoded=False):
        if url is not None:
            self.url = to_unicode(url)
        self.method = method
        if parameters is not None:
            for k, v in parameters.iteritems():
                k = to_unicode(k)
                v = to_unicode_optional_iterator(v)
                self[k] = v
        self.body = body
        self.is_form_encoded = is_form_encoded


    @setter
    def url(self, value):
        self.__dict__['url'] = value
        if value is not None:
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(value)

            # Exclude default port numbers.
            if scheme == 'http' and netloc[-3:] == ':80':
                netloc = netloc[:-3]
            elif scheme == 'https' and netloc[-4:] == ':443':
                netloc = netloc[:-4]
            if scheme not in ('http', 'https'):
                raise ValueError("Unsupported URL %s (%s)." % (value, scheme))

            # Normalized URL excludes params, query, and fragment.
            self.normalized_url = urlparse.urlunparse((scheme, netloc, path, None, None, None))
        else:
            self.normalized_url = None
            self.__dict__['url'] = None
 
    @setter
    def method(self, value):
        self.__dict__['method'] = value.upper()
 
    def _get_timestamp_nonce(self):
        return self['oauth_timestamp'], self['oauth_nonce']
 
    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        return dict([(k, v) for k, v in self.iteritems() 
                    if not k.startswith('oauth_')])
 
    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        oauth_params = ((k, v) for k, v in self.items() 
                            if k.startswith('oauth_'))
        stringy_params = ((k, escape(str(v))) for k, v in oauth_params)
        header_params = ('%s="%s"' % (k, v) for k, v in stringy_params)
        params_header = ', '.join(header_params)
 
        auth_header = 'OAuth realm="%s"' % realm
        if params_header:
            auth_header = "%s, %s" % (auth_header, params_header)
 
        return {'Authorization': auth_header}
 
    def to_postdata(self):
        """Serialize as post data for a POST request."""
        d = {}
        for k, v in self.iteritems():
            d[k.encode('utf-8')] = to_utf8_optional_iterator(v)

        # tell urlencode to deal with sequence values and map them correctly
        # to resulting querystring. for example self["k"] = ["v1", "v2"] will
        # result in 'k=v1&k=v2' and not k=%5B%27v1%27%2C+%27v2%27%5D
        return urllib.urlencode(d, True).replace('+', '%20')
 
    def to_url(self):
        """Serialize as a URL for a GET request."""
        base_url = urlparse.urlparse(self.url)
        try:
            query = base_url.query
        except AttributeError:
            # must be python <2.5
            query = base_url[4]
        query = parse_qs(query)
        for k, v in self.items():
            if isinstance(v, unicode):
                v = v.encode("utf-8")
            query.setdefault(k, []).append(v)
        
        try:
            scheme = base_url.scheme
            netloc = base_url.netloc
            path = base_url.path
            params = base_url.params
            fragment = base_url.fragment
        except AttributeError:
            # must be python <2.5
            scheme = base_url[0]
            netloc = base_url[1]
            path = base_url[2]
            params = base_url[3]
            fragment = base_url[5]
        
        url = (scheme, netloc, path, params,
               urllib.urlencode(query, True), fragment)
        return urlparse.urlunparse(url)

    def get_parameter(self, parameter):
        ret = self.get(parameter)
        if ret is None:
            raise Error('Parameter not found: %s' % parameter)

        return ret

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        items = []
        for key, value in self.iteritems():
            if key == 'oauth_signature':
                continue
            # 1.0a/9.1.1 states that kvp must be sorted by key, then by value,
            # so we unpack sequence values into multiple items for sorting.
            if isinstance(value, basestring):
                items.append((to_utf8_if_string(key), to_utf8(value)))
            else:
                try:
                    value = list(value)
                except TypeError, e:
                    assert 'is not iterable' in str(e)
                    items.append((to_utf8_if_string(key), to_utf8_if_string(value)))
                else:
                    items.extend((to_utf8_if_string(key), to_utf8_if_string(item)) for item in value)

        # Include any query string parameters from the provided URL
        query = urlparse.urlparse(self.url)[4]

        url_items = self._split_url_string(query).items()
        url_items = [(to_utf8(k), to_utf8(v)) for k, v in url_items if k != 'oauth_signature' ]
        items.extend(url_items)

        items.sort()
        encoded_str = urllib.urlencode(items)
        # Encode signature parameters per Oauth Core 1.0 protocol
        # spec draft 7, section 3.6
        # (http://tools.ietf.org/html/draft-hammer-oauth-07#section-3.6)
        # Spaces must be encoded with "%20" instead of "+"
        return encoded_str.replace('+', '%20').replace('%7E', '~')

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of sign."""

        if not self.is_form_encoded:
            # according to
            # http://oauth.googlecode.com/svn/spec/ext/body_hash/1.0/oauth-bodyhash.html
            # section 4.1.1 "OAuth Consumers MUST NOT include an
            # oauth_body_hash parameter on requests with form-encoded
            # request bodies."
            self['oauth_body_hash'] = base64.b64encode(sha(self.body).digest())

        if 'oauth_consumer_key' not in self:
            self['oauth_consumer_key'] = consumer.key

        if token and 'oauth_token' not in self:
            self['oauth_token'] = token.key

        self['oauth_signature_method'] = signature_method.name
        self['oauth_signature'] = signature_method.sign(self, consumer, token)
 
    @classmethod
    def make_timestamp(cls):
        """Get seconds since epoch (UTC)."""
        return str(int(time.time()))
 
    @classmethod
    def make_nonce(cls):
        """Generate pseudorandom number."""
        return str(random.randint(0, 100000000))
 
    @classmethod
    def from_request(cls, http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}
 
        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = cls._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise Error('Unable to parse OAuth parameters from '
                        'Authorization header.')
 
        # GET or POST query string.
        if query_string:
            query_params = cls._split_url_string(query_string)
            parameters.update(query_params)
 
        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = cls._split_url_string(param_str)
        parameters.update(url_params)
 
        if parameters:
            return cls(http_method, http_url, parameters)
 
        return None
 
    @classmethod
    def from_consumer_and_token(cls, consumer, token=None,
            http_method=HTTP_METHOD, http_url=None, parameters=None,
            body='', is_form_encoded=False):
        if not parameters:
            parameters = {}
 
        defaults = {
            'oauth_consumer_key': consumer.key,
            'oauth_timestamp': cls.make_timestamp(),
            'oauth_nonce': cls.make_nonce(),
            'oauth_version': cls.version,
        }
 
        defaults.update(parameters)
        parameters = defaults
 
        if token:
            parameters['oauth_token'] = token.key
            if token.verifier:
                parameters['oauth_verifier'] = token.verifier
 
        return Request(http_method, http_url, parameters, body=body, 
                       is_form_encoded=is_form_encoded)
 
    @classmethod
    def from_token_and_callback(cls, token, callback=None, 
        http_method=HTTP_METHOD, http_url=None, parameters=None):

        if not parameters:
            parameters = {}
 
        parameters['oauth_token'] = token.key
 
        if callback:
            parameters['oauth_callback'] = callback
 
        return cls(http_method, http_url, parameters)
 
    @staticmethod
    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
 
    @staticmethod
    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = parse_qs(param_str.encode('utf-8'), keep_blank_values=True)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters


class SignatureMethod(object):
    """A way of signing requests.
 
    The OAuth protocol lets consumers and service providers pick a way to sign
    requests. This interface shows the methods expected by the other `oauth`
    modules for signing requests. Subclass it and implement its methods to
    provide a new way to sign requests.
    """

    def signing_base(self, request, consumer, token):
        """Calculates the string that needs to be signed.

        This method returns a 2-tuple containing the starting key for the
        signing and the message to be signed. The latter may be used in error
        messages to help clients debug their software.

        """
        raise NotImplementedError

    def sign(self, request, consumer, token):
        """Returns the signature for the given request, based on the consumer
        and token also provided.

        You should use your implementation of `signing_base()` to build the
        message to sign. Otherwise it may be less useful for debugging.

        """
        raise NotImplementedError

    def check(self, request, consumer, token, signature):
        """Returns whether the given signature is the correct signature for
        the given consumer and token signing the given request."""
        built = self.sign(request, consumer, token)
        return built == signature


class SignatureMethod_HMAC_SHA1(SignatureMethod):
    name = 'HMAC-SHA1'

    def signing_base(self, request, consumer, token):
        if not hasattr(request, 'normalized_url') or request.normalized_url is None:
            raise ValueError("Base URL for request is not set.")

        sig = (
            escape(request.method),
            escape(request.normalized_url),
            escape(request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return to_bytestring(key), raw

    def sign(self, request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.signing_base(request, consumer, token)

        hashed = hmac.new(to_bytestring(key), raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class SignatureMethod_PLAINTEXT(SignatureMethod):

    name = 'PLAINTEXT'

    def signing_base(self, request, consumer, token):
        """Concatenates the consumer key and secret with the token's
        secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def sign(self, request, consumer, token):
        key, raw = self.signing_base(request, consumer, token)
        return raw

########NEW FILE########
__FILENAME__ = resource
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.


"""
restkit.resource
~~~~~~~~~~~~~~~~

This module provide a common interface for all HTTP request.
"""
from copy import copy
import urlparse

from restkit.errors import ResourceNotFound, Unauthorized, \
RequestFailed, ResourceGone
from restkit.client import Client
from restkit.filters import BasicAuth
from restkit import util
from restkit.wrappers import Response

class Resource(object):
    """A class that can be instantiated for access to a RESTful resource,
    including authentication.
    """

    charset = 'utf-8'
    encode_keys = True
    safe = "/:"
    basic_auth_url = True
    response_class = Response

    def __init__(self, uri, **client_opts):
        """Constructor for a `Resource` object.

        Resource represent an HTTP resource.

        - uri: str, full uri to the server.
        - client_opts: `restkit.client.Client` Options
        """
        client_opts = client_opts or {}

        self.initial = dict(
            uri = uri,
            client_opts = client_opts.copy()
        )

        # set default response_class
        if self.response_class is not None and \
                not 'response_class' in client_opts:
            client_opts['response_class'] = self.response_class

        self.filters = client_opts.get('filters') or []
        self.uri = uri
        if self.basic_auth_url:
            # detect credentials from url
            u = urlparse.urlparse(uri)
            if u.username:
                password = u.password or ""

                # add filters
                filters = copy(self.filters)
                filters.append(BasicAuth(u.username, password))
                client_opts['filters'] = filters

                # update uri
                self.uri = urlparse.urlunparse((u.scheme, u.netloc.split("@")[-1],
                    u.path, u.params, u.query, u.fragment))

        self.client_opts = client_opts
        self.client = Client(**self.client_opts)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.uri)

    def clone(self):
        """if you want to add a path to resource uri, you can do:

        .. code-block:: python

            resr2 = res.clone()

        """
        obj = self.__class__(self.initial['uri'],
                **self.initial['client_opts'])
        return obj

    def __call__(self, path):
        """if you want to add a path to resource uri, you can do:

        .. code-block:: python

            Resource("/path").get()
        """

        uri = self.initial['uri']

        new_uri = util.make_uri(uri, path, charset=self.charset,
                        safe=self.safe, encode_keys=self.encode_keys)

        obj = type(self)(new_uri, **self.initial['client_opts'])
        return obj

    def get(self, path=None, headers=None, params_dict=None, **params):
        """ HTTP GET

        - path: string  additionnal path to the uri
        - headers: dict, optionnal headers that will
            be added to HTTP request.
        - params: Optionnal parameterss added to the request.
        """
        return self.request("GET", path=path, headers=headers,
                params_dict=params_dict, **params)

    def head(self, path=None, headers=None, params_dict=None, **params):
        """ HTTP HEAD

        see GET for params description.
        """
        return self.request("HEAD", path=path, headers=headers,
                params_dict=params_dict, **params)

    def delete(self, path=None, headers=None, params_dict=None, **params):
        """ HTTP DELETE

        see GET for params description.
        """
        return self.request("DELETE", path=path, headers=headers,
                params_dict=params_dict, **params)

    def post(self, path=None, payload=None, headers=None,
            params_dict=None, **params):
        """ HTTP POST

        - payload: string passed to the body of the request
        - path: string  additionnal path to the uri
        - headers: dict, optionnal headers that will
            be added to HTTP request.
        - params: Optionnal parameterss added to the request
        """

        return self.request("POST", path=path, payload=payload,
                        headers=headers, params_dict=params_dict, **params)

    def put(self, path=None, payload=None, headers=None,
            params_dict=None, **params):
        """ HTTP PUT

        see POST for params description.
        """
        return self.request("PUT", path=path, payload=payload,
                        headers=headers, params_dict=params_dict, **params)

    def make_params(self, params):
        return params or {}

    def make_headers(self, headers):
        return headers or []

    def unauthorized(self, response):
        return True

    def request(self, method, path=None, payload=None, headers=None,
        params_dict=None, **params):
        """ HTTP request

        This method may be the only one you want to override when
        subclassing `restkit.rest.Resource`.

        - payload: string or File object passed to the body of the request
        - path: string  additionnal path to the uri
        - headers: dict, optionnal headers that will
            be added to HTTP request.
        :params_dict: Options parameters added to the request as a dict
        - params: Optionnal parameterss added to the request
        """

        params = params or {}
        params.update(params_dict or {})

        while True:
            uri = util.make_uri(self.uri, path, charset=self.charset,
                        safe=self.safe, encode_keys=self.encode_keys,
                        **self.make_params(params))

            # make request

            resp = self.client.request(uri, method=method, body=payload,
                        headers=self.make_headers(headers))

            if resp is None:
                # race condition
                raise ValueError("Unkown error: response object is None")

            if resp.status_int >= 400:
                if resp.status_int == 404:
                    raise ResourceNotFound(resp.body_string(),
                                response=resp)
                elif resp.status_int in (401, 403):
                    if self.unauthorized(resp):
                        raise Unauthorized(resp.body_string(),
                                http_code=resp.status_int,
                                response=resp)
                elif resp.status_int == 410:
                    raise ResourceGone(resp.body_string(), response=resp)
                else:
                    raise RequestFailed(resp.body_string(),
                                http_code=resp.status_int,
                                response=resp)
            else:
                break

        return resp

    def update_uri(self, path):
        """
        to set a new uri absolute path
        """
        self.uri = util.make_uri(self.uri, path, charset=self.charset,
                        safe=self.safe, encode_keys=self.encode_keys)
        self.initial['uri'] =  util.make_uri(self.initial['uri'], path,
                                    charset=self.charset,
                                    safe=self.safe,
                                    encode_keys=self.encode_keys)

########NEW FILE########
__FILENAME__ = session
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

from socketpool import ConnectionPool
from restkit.conn import Connection


_default_session = {}

def get_session(backend_name, **options):
    global _default_session

    if not _default_session:
        _default_session = {}
        pool = ConnectionPool(factory=Connection,
                backend=backend_name, **options)
        _default_session[backend_name] = pool
    else:
        if backend_name not in _default_session:
            pool = ConnectionPool(factory=Connection,
                backend=backend_name, **options)

            _default_session[backend_name] = pool
        else:
            pool = _default_session.get(backend_name)
    return pool

def set_session(backend_name, **options):

    global _default_session

    if not _default_session:
        _default_session = {}

    if backend_name in _default_session:
        pool = _default_session.get(backend_name)
    else:
        pool = ConnectionPool(factory=Connection,
                backend=backend_name, **options)
        _default_session[backend_name] = pool
    return pool

########NEW FILE########
__FILENAME__ = tee
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.


"""
TeeInput replace old FileInput. It use a file
if size > MAX_BODY or memory. It's now possible to rewind
read or restart etc ... It's based on TeeInput from Gunicorn.

"""
import copy
import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import tempfile

from restkit import conn

class TeeInput(object):

    CHUNK_SIZE = conn.CHUNK_SIZE

    def __init__(self, stream):
        self.buf = StringIO()
        self.eof = False

        if isinstance(stream, basestring):
            stream = StringIO(stream)
            self.tmp = StringIO()
        else:
            self.tmp = tempfile.TemporaryFile()

        self.stream = stream

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        return

    def seek(self, offset, whence=0):
        """ naive implementation of seek """
        current_size = self._tmp_size()
        diff = 0
        if whence == 0:
            diff = offset - current_size
        elif whence == 2:
            diff = (self.tmp.tell() + offset) - current_size
        elif whence == 3 and not self.eof:
            # we read until the end
            while True:
                self.tmp.seek(0, 2)
                if not self._tee(self.CHUNK_SIZE):
                    break

        if not self.eof and diff > 0:
            self._ensure_length(StringIO(), diff)
        self.tmp.seek(offset, whence)

    def flush(self):
        self.tmp.flush()

    def read(self, length=-1):
        """ read """
        if self.eof:
            return self.tmp.read(length)

        if length < 0:
            buf = StringIO()
            buf.write(self.tmp.read())
            while True:
                chunk = self._tee(self.CHUNK_SIZE)
                if not chunk:
                    break
                buf.write(chunk)
            return buf.getvalue()
        else:
            dest = StringIO()
            diff = self._tmp_size() - self.tmp.tell()
            if not diff:
                dest.write(self._tee(length))
                return self._ensure_length(dest, length)
            else:
                l = min(diff, length)
                dest.write(self.tmp.read(l))
                return self._ensure_length(dest, length)

    def readline(self, size=-1):
        if self.eof:
            return self.tmp.readline()

        orig_size = self._tmp_size()
        if self.tmp.tell() == orig_size:
            if not self._tee(self.CHUNK_SIZE):
                return ''
            self.tmp.seek(orig_size)

        # now we can get line
        line = self.tmp.readline()
        if line.find("\n") >=0:
            return line

        buf = StringIO()
        buf.write(line)
        while True:
            orig_size = self.tmp.tell()
            data = self._tee(self.CHUNK_SIZE)
            if not data:
                break
            self.tmp.seek(orig_size)
            buf.write(self.tmp.readline())
            if data.find("\n") >= 0:
                break
        return buf.getvalue()

    def readlines(self, sizehint=0):
        total = 0
        lines = []
        line = self.readline()
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline()
        return lines

    def close(self):
        if not self.eof:
            # we didn't read until the end
            self._close_unreader()
        return self.tmp.close()

    def next(self):
        r = self.readline()
        if not r:
            raise StopIteration
        return r
    __next__ = next

    def __iter__(self):
        return self

    def _tee(self, length):
        """ fetch partial body"""
        buf2 = self.buf
        buf2.seek(0, 2)
        chunk = self.stream.read(length)
        if chunk:
            self.tmp.write(chunk)
            self.tmp.flush()
            self.tmp.seek(0, 2)
            return chunk

        self._finalize()
        return ""

    def _finalize(self):
        """ here we wil fetch final trailers
        if any."""
        self.eof = True

    def _tmp_size(self):
        if hasattr(self.tmp, 'fileno'):
            return int(os.fstat(self.tmp.fileno())[6])
        else:
            return len(self.tmp.getvalue())

    def _ensure_length(self, dest, length):
        if len(dest.getvalue()) < length:
            data = self._tee(length - len(dest.getvalue()))
            dest.write(data)
        return dest.getvalue()

class ResponseTeeInput(TeeInput):

    CHUNK_SIZE = conn.CHUNK_SIZE

    def __init__(self, resp, connection, should_close=False):
        self.buf = StringIO()
        self.resp = resp
        self.stream =resp.body_stream()
        self.connection = connection
        self.should_close = should_close
        self.eof = False

        # set temporary body
        clen = int(resp.headers.get('content-length') or -1)
        if clen >= 0:
            if (clen <= conn.MAX_BODY):
                self.tmp = StringIO()
            else:
                self.tmp = tempfile.TemporaryFile()
        else:
            self.tmp = tempfile.TemporaryFile()

    def close(self):
        if not self.eof:
            # we didn't read until the end
            self._close_unreader()
        return self.tmp.close()

    def _close_unreader(self):
        if not self.eof:
            self.stream.close()
        self.connection.release(self.should_close)

    def _finalize(self):
        """ here we wil fetch final trailers
        if any."""
        self.eof = True
        self._close_unreader()

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import os
import re
import time
import urllib
import urlparse
import warnings
import Cookie

from restkit.errors import InvalidUrl

absolute_http_url_re = re.compile(r"^https?://", re.I)

try:#python 2.6, use subprocess
    import subprocess
    subprocess.Popen  # trigger ImportError early
    closefds = os.name == 'posix'
    
    def popen3(cmd, mode='t', bufsize=0):
        p = subprocess.Popen(cmd, shell=True, bufsize=bufsize,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
            close_fds=closefds)
        p.wait()
        return (p.stdin, p.stdout, p.stderr)
except ImportError:
    subprocess = None
    popen3 = os.popen3
    
def locate_program(program):
    if os.path.isabs(program):
        return program
    if os.path.dirname(program):
        program = os.path.normpath(os.path.realpath(program))
        return program
    paths = os.getenv('PATH')
    if not paths:
        return False
    for path in paths.split(os.pathsep):
        filename = os.path.join(path, program)
        if os.access(filename, os.X_OK):
            return filename
    return False

weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None,
             'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
             
def http_date(timestamp=None):
    """Return the current date and time formatted for a message header."""
    if timestamp is None:
        timestamp = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
            weekdayname[wd],
            day, monthname[month], year,
            hh, mm, ss)
    return s

def parse_netloc(uri):
    host = uri.netloc
    port = None
    i = host.rfind(':')
    j = host.rfind(']')         # ipv6 addresses have [...]
    if i > j:
        try:
            port = int(host[i+1:])
        except ValueError:
            raise InvalidUrl("nonnumeric port: '%s'" % host[i+1:])
        host = host[:i]
    else:
        # default port
        if uri.scheme == "https":
            port = 443
        else:
            port = 80
            
    if host and host[0] == '[' and host[-1] == ']':
        host = host[1:-1]
    return (host, port)

def to_bytestring(s):
    if not isinstance(s, basestring):
        raise TypeError("value should be a str or unicode")

    if isinstance(s, unicode):
        return s.encode('utf-8')
    return s
    
def url_quote(s, charset='utf-8', safe='/:'):
    """URL encode a single string with a given encoding."""
    if isinstance(s, unicode):
        s = s.encode(charset)
    elif not isinstance(s, str):
        s = str(s)
    return urllib.quote(s, safe=safe)


def url_encode(obj, charset="utf8", encode_keys=False):
    items = []
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            items.append((k, v))
    else:
        items = list(items)
        
    tmp = []
    for k, v in items:
        if encode_keys: 
            k = encode(k, charset)
        
        if not isinstance(v, (tuple, list)):
            v = [v]
            
        for v1 in v:
            if v1 is None:
                v1 = ''
            elif callable(v1):
                v1 = encode(v1(), charset)
            else:
                v1 = encode(v1, charset)
            tmp.append('%s=%s' % (urllib.quote(k), urllib.quote_plus(v1)))
    return '&'.join(tmp)
                
def encode(v, charset="utf8"):
    if isinstance(v, unicode):
        v = v.encode(charset)
    else:
        v = str(v)
    return v
    

def make_uri(base, *args, **kwargs):
    """Assemble a uri based on a base, any number of path segments, 
    and query string parameters.

    """

    # get encoding parameters
    charset = kwargs.pop("charset", "utf-8")
    safe = kwargs.pop("safe", "/:")
    encode_keys = kwargs.pop("encode_keys", True)
    
    base_trailing_slash = False
    if base and base.endswith("/"):
        base_trailing_slash = True
        base = base[:-1]
    retval = [base]
    
    # build the path
    _path = []
    trailing_slash = False       
    for s in args:
        if s is not None and isinstance(s, basestring):
            if len(s) > 1 and s.endswith('/'):
                trailing_slash = True
            else:
                trailing_slash = False
            _path.append(url_quote(s.strip('/'), charset, safe))
                   
    path_str =""
    if _path:
        path_str = "/".join([''] + _path)
        if trailing_slash:
            path_str = path_str + "/" 
    elif base_trailing_slash:
        path_str = path_str + "/" 
        
    if path_str:
        retval.append(path_str)

    params_str = url_encode(kwargs, charset, encode_keys)
    if params_str:
        retval.extend(['?', params_str])

    return ''.join(retval)


def rewrite_location(host_uri, location, prefix_path=None):
    prefix_path = prefix_path or ''
    url = urlparse.urlparse(location)
    host_url = urlparse.urlparse(host_uri)

    if not absolute_http_url_re.match(location):
        # remote server doesn't follow rfc2616
        proxy_uri = '%s%s' % (host_uri, prefix_path)
        return urlparse.urljoin(proxy_uri, location)
    elif url.scheme == host_url.scheme and url.netloc == host_url.netloc:
        return urlparse.urlunparse((host_url.scheme, host_url.netloc, 
            prefix_path + url.path, url.params, url.query, url.fragment))
    
    return location

def replace_header(name, value, headers):
    idx = -1
    for i, (k, v) in enumerate(headers):
        if k.upper() == name.upper():
            idx = i
            break
    if idx >= 0:
        headers[i] = (name.title(), value)
    else:
        headers.append((name.title(), value))
    return headers

def replace_headers(new_headers, headers):
    hdrs = {}
    for (k, v) in new_headers:
        hdrs[k.upper()] = v

    found = []
    for i, (k, v) in enumerate(headers):
        ku = k.upper()
        if ku in hdrs:
            headers[i] = (k.title(), hdrs[ku])
            found.append(ku)
        if len(found) == len(new_headers):
            return

    for k, v in new_headers.items():
        if k not in found:
            headers.append((k.title(), v))
    return headers


def parse_cookie(cookie, final_url):
    if cookie == '':
        return {}

    if not isinstance(cookie, Cookie.BaseCookie):
        try:
            c = Cookie.SimpleCookie()
            c.load(cookie)
        except Cookie.CookieError:
            # Invalid cookie
            return {}
    else:
        c = cookie
    
    cookiedict = {}

    for key in c.keys():
        cook = c.get(key)
        cookiedict[key] = cook.value
    return cookiedict
    

class deprecated_property(object):
    """
    Wraps a decorator, with a deprecation warning or error
    """
    def __init__(self, decorator, attr, message, warning=True):
        self.decorator = decorator
        self.attr = attr
        self.message = message
        self.warning = warning

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        self.warn()
        return self.decorator.__get__(obj, type)

    def __set__(self, obj, value):
        self.warn()
        self.decorator.__set__(obj, value)

    def __delete__(self, obj):
        self.warn()
        self.decorator.__delete__(obj)

    def __repr__(self):
        return '<Deprecated attribute %s: %r>' % (
            self.attr,
            self.decorator)

    def warn(self):
        if not self.warning:
            raise DeprecationWarning(
                'The attribute %s is deprecated: %s' % (self.attr, self.message))
        else:
            warnings.warn(
                'The attribute %s is deprecated: %s' % (self.attr, self.message),
                DeprecationWarning,
                stacklevel=3)
    

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

version_info = (4, 2, 2)
__version__ =  ".".join(map(str, version_info))

########NEW FILE########
__FILENAME__ = wrappers
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import cgi
import copy
import logging
import mimetypes
import os
from StringIO import StringIO
import types
import urlparse
import uuid

from restkit.datastructures import MultiDict
from restkit.errors import AlreadyRead, RequestError
from restkit.forms import multipart_form_encode, form_encode
from restkit.tee import ResponseTeeInput
from restkit.util import to_bytestring
from restkit.util import parse_cookie

log = logging.getLogger(__name__)

class Request(object):

    def __init__(self, url, method='GET', body=None, headers=None):
        headers = headers or []
        self.url = url
        self.initial_url = url
        self.method = method

        self._headers = None
        self._body = None

        self.is_proxied = False

        # set parsed uri
        self.headers = headers
        if body is not None:
            self.body = body

    def _headers__get(self):
        if not isinstance(self._headers, MultiDict):
            self._headers = MultiDict(self._headers or [])
        return self._headers
    def _headers__set(self, value):
        self._headers = MultiDict(copy.copy(value))
    headers = property(_headers__get, _headers__set, doc=_headers__get.__doc__)

    def _parsed_url(self):
        if self.url is None:
            raise ValueError("url isn't set")
        return urlparse.urlparse(self.url)
    parsed_url = property(_parsed_url, doc="parsed url")

    def _path__get(self):
        parsed_url = self.parsed_url
        path = parsed_url.path or '/'

        return urlparse.urlunparse(('','', path, parsed_url.params,
            parsed_url.query, parsed_url.fragment))
    path = property(_path__get)

    def _host__get(self):
        h = to_bytestring(self.parsed_url.netloc)
        hdr_host = self.headers.iget("host")
        if not hdr_host:
            return h
        return hdr_host
    host = property(_host__get)

    def is_chunked(self):
        te = self.headers.iget("transfer-encoding")
        return (te is not None and te.lower() == "chunked")

    def is_ssl(self):
        return self.parsed_url.scheme == "https"

    def _set_body(self, body):
        ctype = self.headers.ipop('content-type', None)
        clen = self.headers.ipop('content-length', None)

        if isinstance(body, dict):
            if ctype is not None and \
                    ctype.startswith("multipart/form-data"):
                type_, opts = cgi.parse_header(ctype)
                boundary = opts.get('boundary', uuid.uuid4().hex)
                self._body, self.headers = multipart_form_encode(body,
                                            self.headers, boundary)
                # at this point content-type is "multipart/form-data"
                # we need to set the content type according to the
                # correct boundary like
                # "multipart/form-data; boundary=%s" % boundary
                ctype = self.headers.ipop('content-type', None)
            else:
                ctype = "application/x-www-form-urlencoded; charset=utf-8"
                self._body = form_encode(body)
        elif hasattr(body, "boundary") and hasattr(body, "get_size"):
            ctype = "multipart/form-data; boundary=%s" % body.boundary
            clen = body.get_size()
            self._body = body
        else:
            self._body = body

        if not ctype:
            ctype = 'application/octet-stream'
            if hasattr(self.body, 'name'):
                ctype =  mimetypes.guess_type(body.name)[0]

        if not clen:
            if hasattr(self._body, 'fileno'):
                try:
                    self._body.flush()
                except IOError:
                    pass
                try:
                    fno = self._body.fileno()
                    clen = str(os.fstat(fno)[6])
                except  IOError:
                    if not self.is_chunked():
                        clen = len(self._body.read())
            elif hasattr(self._body, 'getvalue') and not \
                    self.is_chunked():
                clen = len(self._body.getvalue())
            elif isinstance(self._body, types.StringTypes):
                self._body = to_bytestring(self._body)
                clen = len(self._body)

        if clen is not None:
            self.headers['Content-Length'] = clen

        # TODO: maybe it's more relevant
        # to check if Content-Type is already set in self.headers
        # before overiding it
        if ctype is not None:
            self.headers['Content-Type'] = ctype

    def _get_body(self):
        return self._body
    body = property(_get_body, _set_body, doc="request body")

    def maybe_rewind(self, msg=""):
        if self.body is not None:
            if not hasattr(self.body, 'seek') and \
                    not isinstance(self.body, types.StringTypes):
                raise RequestError("error: '%s', body can't be rewind."
                        % msg)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("restart request: %s" % msg)


class BodyWrapper(object):

    def __init__(self, resp, connection):
        self.resp = resp
        self.body = resp._body
        self.connection = connection
        self._closed = False
        self.eof = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        self.close()

    def close(self):
        """ release connection """
        if self._closed:
            return

        if not self.eof:
            self.body.read()

        self.connection.release(self.resp.should_close)
        self._closed = True

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.body.next()
        except StopIteration:
            self.eof = True
            self.close()
            raise

    def read(self, n=-1):
        data = self.body.read(n)
        if not data:
            self.eof = True
            self.close()
        return data

    def readline(self, limit=-1):
        line = self.body.readline(limit)
        if not line:
            self.eof = True
            self.close()
        return line

    def readlines(self, hint=None):
        lines = self.body.readlines(hint)
        if self.body.close:
            self.eof = True
            self.close()
        return lines


class Response(object):

    charset = "utf8"
    unicode_errors = 'strict'

    def __init__(self, connection, request, resp):
        self.request = request
        self.connection = connection

        self._resp = resp

        # response infos
        self.headers = resp.headers()
        self.status = resp.status()
        self.status_int = resp.status_code()
        self.version = resp.version()
        self.headerslist = self.headers.items()
        self.location = self.headers.get('location')
        self.final_url = request.url
        self.should_close = not resp.should_keep_alive()

        # cookies
        if 'set-cookie' in self.headers:
            cookie_header = self.headers.get('set-cookie')
            self.cookies = parse_cookie(cookie_header, self.final_url)


        self._closed = False
        self._already_read = False

        if request.method == "HEAD":
            """ no body on HEAD, release the connection now """
            self.connection.release(True)
            self._body = StringIO("")
        else:
            self._body = resp.body_file()

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            pass
        return self.headers.get(key)

    def __contains__(self, key):
        return key in self.headers

    def __iter__(self):
        return self.headers.iteritems()

    def can_read(self):
        return not self._already_read

    def close(self):
        self.connection.release(True)

    def skip_body(self):
        """ skip the body and release the connection """
        if not self._already_read:
            self._body.read()
            self._already_read = True
            self.connection.release(self.should_close)

    def body_string(self, charset=None, unicode_errors="strict"):
        """ return body string, by default in bytestring """

        if not self.can_read():
            raise AlreadyRead()


        body = self._body.read()
        self._already_read = True

        self.connection.release(self.should_close)

        if charset is not None:
            try:
                body = body.decode(charset, unicode_errors)
            except UnicodeDecodeError:
                pass
        return body

    def body_stream(self):
        """ stream body """
        if not self.can_read():
            raise AlreadyRead()

        self._already_read = True

        return BodyWrapper(self, self.connection)


    def tee(self):
        """ copy response input to standard output or a file if length >
        sock.MAX_BODY. This make possible to reuse it in your
        appplication. When all the input has been read, connection is
        released """
        return ResponseTeeInput(self, self.connection,
                should_close=self.should_close)
ClientResponse = Response

########NEW FILE########
__FILENAME__ = 004-test-client
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import cgi
import imghdr
import os
import socket
import threading
import Queue
import urlparse
import sys
import tempfile
import time

import t
from restkit.filters import BasicAuth


LONG_BODY_PART = """This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client..."""

@t.client_request("/")
def test_001(u, c):
    r = c.request(u)
    t.eq(r.body_string(), "welcome")
    
@t.client_request("/unicode")
def test_002(u, c):
    r = c.request(u)
    t.eq(r.body_string(charset="utf-8"), u"éàù@")
    
@t.client_request("/éàù")
def test_003(u, c):
    r = c.request(u)
    t.eq(r.body_string(), "ok")
    t.eq(r.status_int, 200)

@t.client_request("/json")
def test_004(u, c):
    r = c.request(u, headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    r = c.request(u, headers={'Content-Type': 'text/plain'})
    t.eq(r.status_int, 400)


@t.client_request('/unkown')
def test_005(u, c):
    r = c.request(u, headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 404)
    
@t.client_request('/query?test=testing')
def test_006(u, c):
    r = c.request(u)
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), "ok")
    

@t.client_request('http://e-engura.com/images/logo.gif')
def test_007(u, c):
    r = c.request(u)
    print r.status
    t.eq(r.status_int, 200)
    fd, fname = tempfile.mkstemp(suffix='.gif')
    f = os.fdopen(fd, "wb")
    f.write(r.body_string())
    f.close()
    t.eq(imghdr.what(fname), 'gif')
    

@t.client_request('http://e-engura.com/images/logo.gif')
def test_008(u, c):
    r = c.request(u)
    t.eq(r.status_int, 200)
    fd, fname = tempfile.mkstemp(suffix='.gif')
    f = os.fdopen(fd, "wb")
    with r.body_stream() as body:
        for block in body:
            f.write(block)
    f.close()
    t.eq(imghdr.what(fname), 'gif')
    

@t.client_request('/redirect')
def test_009(u, c):
    c.follow_redirect = True
    r = c.request(u)

    complete_url = "%s/complete_redirect" % u.rsplit("/", 1)[0]
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), "ok")
    t.eq(r.final_url, complete_url)
    

@t.client_request('/')
def test_010(u, c):
    r = c.request(u, 'POST', body="test")
    t.eq(r.body_string(), "test")
    

@t.client_request('/bytestring')
def test_011(u, c):
    r = c.request(u, 'POST', body="éàù@")
    t.eq(r.body_string(), "éàù@")
    

@t.client_request('/unicode')
def test_012(u, c):
    r = c.request(u, 'POST', body=u"éàù@")
    t.eq(r.body_string(), "éàù@")
           

@t.client_request('/json')
def test_013(u, c):
    r = c.request(u, 'POST', body="test", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    
    r = c.request(u, 'POST', body="test", 
            headers={'Content-Type': 'text/plain'})
    t.eq(r.status_int, 400)
    
    
@t.client_request('/empty')
def test_014(u, c):
    r = c.request(u, 'POST', body="", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    
    r = c.request(u, 'POST', body="", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    

@t.client_request('/query?test=testing')
def test_015(u, c):
    r = c.request(u, 'POST', body="", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    

@t.client_request('/1M')
def test_016(u, c):
    fn = os.path.join(os.path.dirname(__file__), "1M")
    with open(fn, "rb") as f:
        l = int(os.fstat(f.fileno())[6])
        r = c.request(u, 'POST', body=f)
        t.eq(r.status_int, 200)
        t.eq(int(r.body_string()), l)
    

@t.client_request('/large')
def test_017(u, c):
    r = c.request(u, 'POST', body=LONG_BODY_PART)
    t.eq(r.status_int, 200)
    t.eq(int(r['content-length']), len(LONG_BODY_PART))
    t.eq(r.body_string(), LONG_BODY_PART)
       


def test_0018():
    for i in range(10):
        t.client_request('/large')(test_017)
        
@t.client_request('/')
def test_019(u, c):
    r = c.request(u, 'PUT', body="test")
    t.eq(r.body_string(), "test")
    
    
@t.client_request('/auth')
def test_020(u, c):
    c.filters = [BasicAuth("test", "test")]
    c.load_filters()
    r = c.request(u)
    t.eq(r.status_int, 200)
    
    c.filters = [BasicAuth("test", "test2")]
    c.load_filters()
    r = c.request(u)
    t.eq(r.status_int, 403)
   

@t.client_request('/list')
def test_021(u, c):
    lines = ["line 1\n", " line2\n"]
    r = c.request(u, 'POST', body=lines, 
            headers=[("Content-Length", "14")])
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), 'line 1\n line2\n')
     
@t.client_request('/chunked')
def test_022(u, c):
    lines = ["line 1\n", " line2\n"]
    r = c.request(u, 'POST', body=lines, 
            headers=[("Transfer-Encoding", "chunked")])
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), '7\r\nline 1\n\r\n7\r\n line2\n\r\n0\r\n\r\n')
    
@t.client_request("/cookie")
def test_023(u, c):
    r = c.request(u)
    t.eq(r.cookies.get('fig'), 'newton')
    t.eq(r.status_int, 200)
    

@t.client_request("/cookies")
def test_024(u, c):
    r = c.request(u)
    t.eq(r.cookies.get('fig'), 'newton')
    t.eq(r.cookies.get('sugar'), 'wafer')
    t.eq(r.status_int, 200)
    


########NEW FILE########
__FILENAME__ = 005-test-resource
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import t

from restkit.errors import RequestFailed, ResourceNotFound, \
Unauthorized
from restkit.resource import Resource
from _server_test import HOST, PORT

@t.resource_request()
def test_001(res):
    r = res.get()
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), "welcome")

@t.resource_request()
def test_002(res):
    r = res.get('/unicode')
    t.eq(r.body_string(), "éàù@")

@t.resource_request()
def test_003(res):
    r = res.get('/éàù')
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), "ok")

@t.resource_request()
def test_004(res):
    r = res.get(u'/test')
    t.eq(r.status_int, 200)
    r = res.get(u'/éàù')
    t.eq(r.status_int, 200)

@t.resource_request()
def test_005(res):
    r = res.get('/json', headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    t.raises(RequestFailed, res.get, '/json', 
        headers={'Content-Type': 'text/plain'})
        
@t.resource_request()
def test_006(res):
    t.raises(ResourceNotFound, res.get, '/unknown')

@t.resource_request()
def test_007(res):
    r = res.get('/query', test='testing')
    t.eq(r.status_int, 200)
    r = res.get('/qint', test=1)
    t.eq(r.status_int, 200)

@t.resource_request()
def test_008(res):
    r = res.post(payload="test")
    t.eq(r.body_string(), "test")

@t.resource_request()
def test_009(res):
    r = res.post('/bytestring', payload="éàù@")
    t.eq(r.body_string(), "éàù@")

@t.resource_request()
def test_010(res):
    r = res.post('/unicode', payload=u"éàù@")
    t.eq(r.body_string(), "éàù@")
    print "ok"
    r = res.post('/unicode', payload=u"éàù@")
    t.eq(r.body_string(charset="utf-8"), u"éàù@")

@t.resource_request()
def test_011(res):
    r = res.post('/json', payload="test", 
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    t.raises(RequestFailed, res.post, '/json', payload='test',
            headers={'Content-Type': 'text/plain'})

@t.resource_request()
def test_012(res):
    r = res.post('/empty', payload="",
            headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    r = res.post('/empty', headers={'Content-Type': 'application/json'})
    t.eq(r.status_int, 200)
    
@t.resource_request()
def test_013(res):
    r = res.post('/query', test="testing")
    t.eq(r.status_int, 200)

@t.resource_request()
def test_014(res):
    r = res.post('/form', payload={ "a": "a", "b": "b" })
    t.eq(r.status_int, 200)
    
@t.resource_request()
def test_015(res):
    r = res.put(payload="test")
    t.eq(r.body_string(), 'test')

@t.resource_request()
def test_016(res):
    r = res.head('/ok')
    t.eq(r.status_int, 200)

@t.resource_request()
def test_017(res):
    r = res.delete('/delete')    
    t.eq(r.status_int, 200)

@t.resource_request()
def test_018(res):
    content_length = len("test")
    import StringIO
    content = StringIO.StringIO("test")
    r = res.post('/json', payload=content,
            headers={
                'Content-Type': 'application/json',
                'Content-Length': str(content_length)
            }) 
    t.eq(r.status_int, 200)

@t.resource_request()
def test_019(res):
    import StringIO
    content = StringIO.StringIO("test")
    t.raises(RequestFailed, res.post, '/json', payload=content,
            headers={'Content-Type': 'text/plain'})
            
def test_020():
    u = "http://test:test@%s:%s/auth" % (HOST, PORT)
    res = Resource(u)
    r = res.get()
    t.eq(r.status_int, 200)
    u = "http://test:test2@%s:%s/auth" % (HOST, PORT)
    res = Resource(u)
    t.raises(Unauthorized, res.get)

@t.resource_request()
def test_021(res):
    r = res.post('/multivalueform', payload={ "a": ["a", "c"], "b": "b" })
    t.eq(r.status_int, 200)

@t.resource_request()
def test_022(res):
    import os
    fn = os.path.join(os.path.dirname(__file__), "1M")
    f = open(fn, 'rb')
    l = int(os.fstat(f.fileno())[6])
    b = {'a':'aa','b':['bb','éàù@'], 'f':f}
    h = {'content-type':"multipart/form-data"}
    r = res.post('/multipart2', payload=b, headers=h)
    t.eq(r.status_int, 200)
    t.eq(int(r.body_string()), l)

@t.resource_request()
def test_023(res):
    import os
    fn = os.path.join(os.path.dirname(__file__), "1M")
    f = open(fn, 'rb')
    l = int(os.fstat(f.fileno())[6])
    b = {'a':'aa','b':'éàù@', 'f':f}
    h = {'content-type':"multipart/form-data"}
    r = res.post('/multipart3', payload=b, headers=h)
    t.eq(r.status_int, 200)
    t.eq(int(r.body_string()), l)

@t.resource_request()
def test_024(res):
    import os
    fn = os.path.join(os.path.dirname(__file__), "1M")
    f = open(fn, 'rb')
    content = f.read()
    f.seek(0)
    b = {'a':'aa','b':'éàù@', 'f':f}
    h = {'content-type':"multipart/form-data"}
    r = res.post('/multipart4', payload=b, headers=h)
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), content)

@t.resource_request()
def test_025(res):
    import StringIO
    content = 'éàù@'
    f = StringIO.StringIO('éàù@')
    f.name = 'test.txt'
    b = {'a':'aa','b':'éàù@', 'f':f}
    h = {'content-type':"multipart/form-data"}
    r = res.post('/multipart4', payload=b, headers=h)
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), content)
########NEW FILE########
__FILENAME__ = 006-test-webob
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import unittest

import webob.exc
from restkit.contrib.webob_helper import wrap_exceptions


wrap_exceptions()

class ResourceTestCase(unittest.TestCase):
        
    def testWebobException(self):
       
        from restkit.errors import ResourceError
        self.assert_(issubclass(ResourceError, 
                webob.exc.WSGIHTTPException) == True)
        
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = 007-test-util
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


import t
from restkit import util

def test_001():
    qs = {'a': "a"}
    t.eq(util.url_encode(qs), "a=a")
    qs = {'a': 'a', 'b': 'b'}
    t.eq(util.url_encode(qs), "a=a&b=b")
    qs = {'a': 1}
    t.eq(util.url_encode(qs), "a=1")
    qs = {'a': [1, 2]}
    t.eq(util.url_encode(qs), "a=1&a=2")
    qs = {'a': [1, 2], 'b': [3, 4]}
    t.eq(util.url_encode(qs), "a=1&a=2&b=3&b=4")
    qs = {'a': lambda : 1}
    t.eq(util.url_encode(qs), "a=1")
    
def test_002():
    t.eq(util.make_uri("http://localhost", "/"), "http://localhost/")
    t.eq(util.make_uri("http://localhost/"), "http://localhost/")
    t.eq(util.make_uri("http://localhost/", "/test/echo"), 
        "http://localhost/test/echo")
    t.eq(util.make_uri("http://localhost/", "/test/echo/"), 
        "http://localhost/test/echo/")
    t.eq(util.make_uri("http://localhost", "/test/echo/"),
        "http://localhost/test/echo/")
    t.eq(util.make_uri("http://localhost", "test/echo"), 
        "http://localhost/test/echo")
    t.eq(util.make_uri("http://localhost", "test/echo/"),
        "http://localhost/test/echo/")
    
    
########NEW FILE########
__FILENAME__ = 008-test-request
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import os
import uuid
import t
from restkit import request
from restkit.forms import multipart_form_encode

from _server_test import HOST, PORT

LONG_BODY_PART = """This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client...
This is a relatively long body, that we send to the client..."""

def test_001():
    u = "http://%s:%s" % (HOST, PORT)
    r = request(u)
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), "welcome")
    
def test_002():
    u = "http://%s:%s" % (HOST, PORT)
    r = request(u, 'POST', body=LONG_BODY_PART)
    t.eq(r.status_int, 200)
    body = r.body_string()
    t.eq(len(body), len(LONG_BODY_PART))
    t.eq(body, LONG_BODY_PART)
    
def test_003():
     u = "http://test:test@%s:%s/auth" % (HOST, PORT)
     r = request(u)
     t.eq(r.status_int, 200)
     u = "http://test:test2@%s:%s/auth" % (HOST, PORT)
     r = request(u)
     t.eq(r.status_int, 403)
     
def test_004():
    u = "http://%s:%s/multipart2" % (HOST, PORT)
    fn = os.path.join(os.path.dirname(__file__), "1M")
    f = open(fn, 'rb')
    l = int(os.fstat(f.fileno())[6])
    b = {'a':'aa','b':['bb','éàù@'], 'f':f}
    h = {'content-type':"multipart/form-data"}
    body, headers = multipart_form_encode(b, h, uuid.uuid4().hex)
    r = request(u, method='POST', body=body, headers=headers)
    t.eq(r.status_int, 200)
    t.eq(int(r.body_string()), l)
    
def test_005():
    u = "http://%s:%s/multipart3" % (HOST, PORT)
    fn = os.path.join(os.path.dirname(__file__), "1M")
    f = open(fn, 'rb')
    l = int(os.fstat(f.fileno())[6])
    b = {'a':'aa','b':'éàù@', 'f':f}
    h = {'content-type':"multipart/form-data"}
    body, headers = multipart_form_encode(b, h, uuid.uuid4().hex)
    r = request(u, method='POST', body=body, headers=headers)
    t.eq(r.status_int, 200)
    t.eq(int(r.body_string()), l)
    
def test_006():
    u = "http://%s:%s/multipart4" % (HOST, PORT)
    fn = os.path.join(os.path.dirname(__file__), "1M")
    f = open(fn, 'rb')
    content = f.read()
    f.seek(0)
    b = {'a':'aa','b':'éàù@', 'f':f}
    h = {'content-type':"multipart/form-data"}
    body, headers = multipart_form_encode(b, h, uuid.uuid4().hex)
    r = request(u, method='POST', body=body, headers=headers)
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), content)

def test_007():
    import StringIO
    u = "http://%s:%s/multipart4" % (HOST, PORT)
    content = 'éàù@'
    f = StringIO.StringIO('éàù@')
    f.name = 'test.txt'
    b = {'a':'aa','b':'éàù@', 'f':f}
    h = {'content-type':"multipart/form-data"}
    body, headers = multipart_form_encode(b, h, uuid.uuid4().hex)
    r = request(u, method='POST', body=body, headers=headers)
    t.eq(r.status_int, 200)
    t.eq(r.body_string(), content)
########NEW FILE########
__FILENAME__ = 009-test-oauth_filter
# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.


# Request Token: http://oauth-sandbox.sevengoslings.net/request_token
# Auth: http://oauth-sandbox.sevengoslings.net/authorize
# Access Token: http://oauth-sandbox.sevengoslings.net/access_token
# Two-legged: http://oauth-sandbox.sevengoslings.net/two_legged
# Three-legged: http://oauth-sandbox.sevengoslings.net/three_legged
# Key: bd37aed57e15df53
# Secret: 0e9e6413a9ef49510a4f68ed02cd

try:
    from urlparse import parse_qs, parse_qsl
except ImportError:
    from cgi import parse_qs, parse_qsl
import urllib

from restkit import request, OAuthFilter
from restkit.oauth2 import Consumer
import t


class oauth_request(object):
    oauth_uris = {
        'request_token': '/request_token',
        'authorize': '/authorize',
        'access_token': '/access_token',
        'two_legged': '/two_legged',
        'three_legged': '/three_legged'
    }
    
    consumer_key = 'bd37aed57e15df53'
    consumer_secret = '0e9e6413a9ef49510a4f68ed02cd'
    host = 'http://oauth-sandbox.sevengoslings.net'
    
    def __init__(self, utype):
        self.consumer = Consumer(key=self.consumer_key,
                            secret=self.consumer_secret)
        self.body = {
            'foo': 'bar',
            'bar': 'foo',
            'multi': ['FOO','BAR'],
            'blah': 599999
        }
        self.url = "%s%s" % (self.host, self.oauth_uris[utype])
        
    def __call__(self, func):
        def run():
            o = OAuthFilter('*', self.consumer)
            func(o, self.url, urllib.urlencode(self.body))
        run.func_name = func.func_name
        return run
        
@oauth_request('request_token')
def test_001(o, u, b):
    r = request(u, filters=[o])
    t.eq(r.status_int, 200)
    
@oauth_request('request_token')
def test_002(o, u, b):
    r = request(u, "POST", filters=[o])
    t.eq(r.status_int, 200)
    f = dict(parse_qsl(r.body_string()))
    t.isin('oauth_token', f)
    t.isin('oauth_token_secret', f)
    

@oauth_request('two_legged')
def test_003(o, u, b):
    r = request(u, "POST", body=b, filters=[o],
                headers={"Content-type": "application/x-www-form-urlencoded"})
    import sys
    print >>sys.stderr, r.body_string()
    t.eq(r.status_int, 200)
    # Because this is a POST and an application/x-www-form-urlencoded, the OAuth
    # can include the OAuth parameters directly into the body of the form, however
    # it MUST NOT include the 'oauth_body_hash' parameter in these circumstances.
    t.isnotin("oauth_body_hash", r.request.body)

@oauth_request('two_legged')
def test_004(o, u, b):
    r = request(u, "GET", filters=[o])
    t.eq(r.status_int, 200)
    
    



########NEW FILE########
__FILENAME__ = 010-test-proxies
# -*- coding: utf-8 -*-
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import t
from _server_test import HOST, PORT
from restkit.contrib import wsgi_proxy

root_uri = "http://%s:%s" % (HOST, PORT)

def with_webob(func):
    def wrapper(*args, **kwargs):
        from webob import Request
        req = Request.blank('/')
        req.environ['SERVER_NAME'] = '%s:%s' % (HOST, PORT)
        return func(req)
    wrapper.func_name = func.func_name
    return wrapper

@with_webob
def test_001(req):
    req.path_info = '/query'
    proxy = wsgi_proxy.Proxy()
    resp = req.get_response(proxy)
    body = resp.body
    assert 'path: /query' in body, str(resp)

@with_webob
def test_002(req):
    req.path_info = '/json'
    req.environ['CONTENT_TYPE'] = 'application/json'
    req.method = 'POST'
    req.body = 'test post'
    proxy = wsgi_proxy.Proxy(allowed_methods=['POST'])
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.content_length == 9, str(resp)

    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'])
    resp = req.get_response(proxy)
    assert resp.status.startswith('403'), resp.status

@with_webob
def test_003(req):
    req.path_info = '/json'
    req.environ['CONTENT_TYPE'] = 'application/json'
    req.method = 'PUT'
    req.body = 'test post'
    proxy = wsgi_proxy.Proxy(allowed_methods=['PUT'])
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.content_length == 9, str(resp)

    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'])
    resp = req.get_response(proxy)
    assert resp.status.startswith('403'), resp.status

@with_webob
def test_004(req):
    req.path_info = '/ok'
    req.method = 'HEAD'
    proxy = wsgi_proxy.Proxy(allowed_methods=['HEAD'])
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.content_type == 'text/plain', str(resp)

@with_webob
def test_005(req):
    req.path_info = '/delete'
    req.method = 'DELETE'
    proxy = wsgi_proxy.Proxy(allowed_methods=['DELETE'])
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.content_type == 'text/plain', str(resp)

    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'])
    resp = req.get_response(proxy)
    assert resp.status.startswith('403'), resp.status

@with_webob
def test_006(req):
    req.path_info = '/redirect'
    req.method = 'GET'
    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'])
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.location == '%s/complete_redirect' % root_uri, str(resp)

@with_webob
def test_007(req):
    req.path_info = '/redirect_to_url'
    req.method = 'GET'
    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'])
    resp = req.get_response(proxy)
    body = resp.body

    print resp.location
    assert resp.location == '%s/complete_redirect' % root_uri, str(resp)

@with_webob
def test_008(req):
    req.path_info = '/redirect_to_url'
    req.script_name = '/name'
    req.method = 'GET'
    proxy = wsgi_proxy.Proxy(allowed_methods=['GET'], strip_script_name=True)
    resp = req.get_response(proxy)
    body = resp.body
    assert resp.location == '%s/name/complete_redirect' % root_uri, str(resp)




########NEW FILE########
__FILENAME__ = t
# -*- coding: utf-8 -
# Copyright 2009 Paul J. Davis <paul.joseph.davis@gmail.com>
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import os
from StringIO import StringIO
import tempfile

dirname = os.path.dirname(__file__)

from restkit.client import Client
from restkit.resource import Resource

from _server_test import HOST, PORT, run_server_test
run_server_test()

def data_source(fname):
    buf = StringIO()
    with open(fname) as handle:
        for line in handle:
            line = line.rstrip("\n").replace("\\r\\n", "\r\n")
            buf.write(line)
        return buf
        
        
class FakeSocket(object):
    
    def __init__(self, data):
        self.tmp = tempfile.TemporaryFile()
        if data:
            self.tmp.write(data.getvalue())
            self.tmp.flush()
            self.tmp.seek(0)

    def fileno(self):
        return self.tmp.fileno()
        
    def len(self):
        return self.tmp.len
        
    def recv(self, length=None):
        return self.tmp.read()
        
    def recv_into(self, buf, length):
        tmp_buffer = self.tmp.read(length)
        v = len(tmp_buffer)
        for i, c in enumerate(tmp_buffer):
            buf[i] = c
        return v
        
    def send(self, data):
        self.tmp.write(data)
        self.tmp.flush()
        
    def seek(self, offset, whence=0):
        self.tmp.seek(offset, whence)
                
class client_request(object):
    
    def __init__(self, path):
        if path.startswith("http://") or path.startswith("https://"):
            self.url = path
        else:
            self.url = 'http://%s:%s%s' % (HOST, PORT, path)
        
    def __call__(self, func):
        def run():
            cli = Client(timeout=300)
            func(self.url, cli)
        run.func_name = func.func_name
        return run
        
class resource_request(object):
    
    def __init__(self, url=None):
        if url is not None:
            self.url = url
        else:
            self.url = 'http://%s:%s' % (HOST, PORT)
        
    def __call__(self, func):
        def run():
            res = Resource(self.url)
            func(res)
        run.func_name = func.func_name
        return run
        
        
def eq(a, b):
    assert a == b, "%r != %r" % (a, b)

def ne(a, b):
    assert a != b, "%r == %r" % (a, b)

def lt(a, b):
    assert a < b, "%r >= %r" % (a, b)

def gt(a, b):
    assert a > b, "%r <= %r" % (a, b)

def isin(a, b):
    assert a in b, "%r is not in %r" % (a, b)

def isnotin(a, b):
    assert a not in b, "%r is in %r" % (a, b)

def has(a, b):
    assert hasattr(a, b), "%r has no attribute %r" % (a, b)

def hasnot(a, b):
    assert not hasattr(a, b), "%r has an attribute %r" % (a, b)

def raises(exctype, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exctype:
        pass
    else:
        func_name = getattr(func, "func_name", "<builtin_function>")
        raise AssertionError("Function %s did not raise %s" % (
            func_name, exctype.__name__))


########NEW FILE########
__FILENAME__ = treq
# Copyright 2009 Paul J. Davis <paul.joseph.davis@gmail.com>
#
# This file is part of the pywebmachine package released
# under the MIT license.

from __future__ import with_statement

import t

import inspect
import os
import random
from StringIO import StringIO
import urlparse

from restkit.datastructures import MultiDict 
from restkit.errors import ParseException
from restkit.http import Request, Unreader

class IterUnreader(Unreader):

    def __init__(self, iterable, **kwargs):
        self.buf = StringIO()
        self.iter = iter(iterable)
        

    def _data(self):
        if not self.iter:
            return ""
        try:
            return self.iter.next()
        except StopIteration:
            self.iter = None
            return ""
     

dirname = os.path.dirname(__file__)
random.seed()

def uri(data):
    ret = {"raw": data}
    parts = urlparse.urlparse(data)
    ret["scheme"] = parts.scheme or None
    ret["host"] = parts.netloc.rsplit(":", 1)[0] or None
    ret["port"] = parts.port or 80
    if parts.path and parts.params:
        ret["path"] = ";".join([parts.path, parts.params])
    elif parts.path:
        ret["path"] = parts.path
    elif parts.params:
        # Don't think this can happen
        ret["path"] = ";" + parts.path
    else:
        ret["path"] = None
    ret["query"] = parts.query or None
    ret["fragment"] = parts.fragment or None
    return ret

    
def load_response_py(fname):
    config = globals().copy()
    config["uri"] = uri
    execfile(fname, config)
    return config["response"]

class response(object):
    def __init__(self, fname, expect):
        self.fname = fname
        self.name = os.path.basename(fname)

        self.expect = expect
        if not isinstance(self.expect, list):
            self.expect = [self.expect]

        with open(self.fname) as handle:
            self.data = handle.read()
        self.data = self.data.replace("\n", "").replace("\\r\\n", "\r\n")
        self.data = self.data.replace("\\0", "\000")

    # Functions for sending data to the parser.
    # These functions mock out reading from a
    # socket or other data source that might
    # be used in real life.

    def send_all(self):
        yield self.data

    def send_lines(self):
        lines = self.data
        pos = lines.find("\r\n")
        while pos > 0:
            yield lines[:pos+2]
            lines = lines[pos+2:]
            pos = lines.find("\r\n")
        if len(lines):
            yield lines

    def send_bytes(self):
        for d in self.data:
            yield d
    
    def send_random(self):
        maxs = len(self.data) / 10
        read = 0
        while read < len(self.data):
            chunk = random.randint(1, maxs)
            yield self.data[read:read+chunk]
            read += chunk                

    # These functions define the sizes that the
    # read functions will read with.

    def size_all(self):
        return -1
    
    def size_bytes(self):
        return 1
    
    def size_small_random(self):
        return random.randint(0, 4)
    
    def size_random(self):
        return random.randint(1, 4096)

    # Match a body against various ways of reading
    # a message. Pass in the request, expected body
    # and one of the size functions.

    def szread(self, func, sizes):
        sz = sizes()
        data = func(sz)
        if sz >= 0 and len(data) > sz:
            raise AssertionError("Read more than %d bytes: %s" % (sz, data))
        return data

    def match_read(self, req, body, sizes):
        data = self.szread(req.body.read, sizes)
        count = 1000
        while len(body):
            if body[:len(data)] != data:
                raise AssertionError("Invalid body data read: %r != %r" % (
                                        data, body[:len(data)]))
            body = body[len(data):]
            data = self.szread(req.body.read, sizes)
            if not data:
                count -= 1
            if count <= 0:
                raise AssertionError("Unexpected apparent EOF")

        if len(body):
            raise AssertionError("Failed to read entire body: %r" % body)
        elif len(data):
            raise AssertionError("Read beyond expected body: %r" % data)        
        data = req.body.read(sizes())
        if data:
            raise AssertionError("Read after body finished: %r" % data)

    def match_readline(self, req, body, sizes):
        data = self.szread(req.body.readline, sizes)
        count = 1000
        while len(body):
            if body[:len(data)] != data:
                raise AssertionError("Invalid data read: %r" % data)
            if '\n' in data[:-1]:
                raise AssertionError("Embedded new line: %r" % data)
            body = body[len(data):]
            data = self.szread(req.body.readline, sizes)
            if not data:
                count -= 1
            if count <= 0:
                raise AssertionError("Apparent unexpected EOF")
        if len(body):
            raise AssertionError("Failed to read entire body: %r" % body)
        elif len(data):
            raise AssertionError("Read beyond expected body: %r" % data)        
        data = req.body.readline(sizes())
        if data:
            raise AssertionError("Read data after body finished: %r" % data)

    def match_readlines(self, req, body, sizes):
        """\
        This skips the sizes checks as we don't implement it.
        """
        data = req.body.readlines()
        for line in data:
            if '\n' in line[:-1]:
                raise AssertionError("Embedded new line: %r" % line)
            if line != body[:len(line)]:
                raise AssertionError("Invalid body data read: %r != %r" % (
                                                    line, body[:len(line)]))
            body = body[len(line):]
        if len(body):
            raise AssertionError("Failed to read entire body: %r" % body)
        data = req.body.readlines(sizes())
        if data:
            raise AssertionError("Read data after body finished: %r" % data)
    
    def match_iter(self, req, body, sizes):
        """\
        This skips sizes because there's its not part of the iter api.
        """
        for line in req.body:
            if '\n' in line[:-1]:
                raise AssertionError("Embedded new line: %r" % line)
            if line != body[:len(line)]:
                raise AssertionError("Invalid body data read: %r != %r" % (
                                                    line, body[:len(line)]))
            body = body[len(line):]
        if len(body):
            raise AssertionError("Failed to read entire body: %r" % body)
        try:
            data = iter(req.body).next()
            raise AssertionError("Read data after body finished: %r" % data)
        except StopIteration:
            pass

    # Construct a series of test cases from the permutations of
    # send, size, and match functions.
    
    def gen_cases(self):
        def get_funs(p):
            return [v for k, v in inspect.getmembers(self) if k.startswith(p)]
        senders = get_funs("send_")
        sizers = get_funs("size_")
        matchers = get_funs("match_")
        cfgs = [
            (mt, sz, sn)
            for mt in matchers
            for sz in sizers
            for sn in senders
        ]

        ret = []
        for (mt, sz, sn) in cfgs:
            mtn = mt.func_name[6:]
            szn = sz.func_name[5:]
            snn = sn.func_name[5:]
            def test_req(sn, sz, mt):
                self.check(sn, sz, mt)
            desc = "%s: MT: %s SZ: %s SN: %s" % (self.name, mtn, szn, snn)
            test_req.description = desc
            ret.append((test_req, sn, sz, mt))
        return ret

    def check(self, sender, sizer, matcher):
        cases = self.expect[:]

        unreader = IterUnreader(sender())
        resp = Request(unreader)
        self.same(resp, sizer, matcher, cases.pop(0))
        t.eq(len(cases), 0)

    def same(self, resp, sizer, matcher, exp):
        t.eq(resp.status, exp["status"])
        t.eq(resp.version, exp["version"])
        t.eq(resp.headers, MultiDict(exp["headers"]))
        matcher(resp, exp["body"], sizer)
        t.eq(resp.trailers, exp.get("trailers", []))

########NEW FILE########
__FILENAME__ = _server_test
# -*- coding: utf-8 -
#
# Copyright (c) 2008 (c) Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import base64
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
import os
import socket
import tempfile
import threading
import unittest
import urlparse
import Cookie

try:
    from urlparse import parse_qsl, parse_qs
except ImportError:
    from cgi import parse_qsl, parse_qs
import urllib
from restkit.util import to_bytestring

HOST = 'localhost'
PORT = (os.getpid() % 31000) + 1024

class HTTPTestHandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        self.auth = 'Basic ' + base64.encodestring('test:test')[:-1]
        self.count = 0
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        
        
    def do_GET(self):
        self.parsed_uri = urlparse.urlparse(urllib.unquote(self.path))
        self.query = {}
        for k, v in parse_qsl(self.parsed_uri[4]):
            self.query[k] = v.decode('utf-8')
        path = self.parsed_uri[2]

        if path == "/":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "welcome")

        elif path == "/unicode":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, u"éàù@")

        elif path == "/json":
            content_type = self.headers.get('content-type', 'text/plain')
            if content_type != "application/json":
                self.error_Response("bad type")
            else:
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, "ok")

        elif path == "/éàù":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "ok")

        elif path == "/test":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "ok")

        elif path == "/query":
            test = self.query.get("test", False)
            if test and test == "testing":
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
        elif path == "/qint":
            test = self.query.get("test", False)
            if test and test == "1":
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
        elif path == "/auth":
            extra_headers = [('Content-type', 'text/plain')]

            if not 'Authorization' in self.headers:
                realm = "test"
                extra_headers.append(('WWW-Authenticate', 'Basic realm="%s"' % realm))
                self._respond(401, extra_headers, "")
            else:
                auth = self.headers['Authorization'][len('Basic')+1:]
                auth = base64.b64decode(auth).split(':')
                if auth[0] == "test" and auth[1] == "test":
                    self._respond(200, extra_headers, "ok")
                else:
                    self._respond(403, extra_headers, "niet!")
        elif path == "/redirect":
            extra_headers = [('Content-type', 'text/plain'),
                ('Location', '/complete_redirect')]
            self._respond(301, extra_headers, "")

        elif path == "/complete_redirect":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "ok")

        elif path == "/redirect_to_url":
            extra_headers = [('Content-type', 'text/plain'),
                ('Location', 'http://localhost:%s/complete_redirect' % PORT)]
            self._respond(301, extra_headers, "")

        elif path == "/pool":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, "ok")
        
        elif path == "/cookie":
            c = Cookie.SimpleCookie()
            c["fig"] = "newton"
            c['fig']['path'] = "/"
            for k in c.keys():
                extra_headers = [('Set-Cookie', str(c[k].output(header='')))]
            self._respond(200, extra_headers, "ok")
        
        elif path == "/cookies":
            c = Cookie.SimpleCookie()
            c["fig"] = "newton"
            c['fig']['path'] = "/"
            c["sugar"] = "wafer"
            c['sugar']['path'] = "/"
            extra_headers = []
            for k in c.keys():
                extra_headers.append(('Set-Cookie', str(c[k].output(header=''))))
            self._respond(200, extra_headers, "ok")
        
        else:
            self._respond(404, 
                [('Content-type', 'text/plain')], "Not Found" )


    def do_POST(self):
        self.parsed_uri = urlparse.urlparse(self.path)
        self.query = {}
        for k, v in parse_qsl(self.parsed_uri[4]):
            self.query[k] = v.decode('utf-8')
        path = self.parsed_uri[2]
        extra_headers = []
        if path == "/":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', '-1'))
            body = self.rfile.read(content_length)
            self._respond(200, extra_headers, body)

        elif path == "/bytestring":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', '-1'))
            body = self.rfile.read(content_length)
            self._respond(200, extra_headers, body)

        elif path == "/unicode":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', '-1'))
            body = self.rfile.read(content_length)
            self._respond(200, extra_headers, body)

        elif path == "/json":
            content_type = self.headers.get('content-type', 'text/plain')
            if content_type != "application/json":
                self.error_Response("bad type: %s" % content_type)
            else:
                extra_headers.append(('Content-type', content_type))
                content_length = int(self.headers.get('Content-length', 0))
                body = self.rfile.read(content_length)
                self._respond(200, extra_headers, body)
        elif path == "/empty":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = self.rfile.read(content_length)
            if body == "":
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
            
        elif path == "/query":
            test = self.query.get("test", False)
            if test and test == "testing":
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
        elif path == "/form":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = self.rfile.read(content_length)
            form = parse_qs(body)
            if form['a'] == ["a"] and form["b"] == ["b"]:
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
        elif path == "/multivalueform":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = self.rfile.read(content_length)
            form = parse_qs(body)
            if form['a'] == ["a", "c"] and form["b"] == ["b"]:
                self._respond(200, extra_headers, "ok")
            else:
                self.error_Response()
        elif path == "/multipart":
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            content_length = int(self.headers.get('Content-length', 0))
            if ctype == 'multipart/form-data':
                req = cgi.parse_multipart(self.rfile, pdict)
                body = req['t'][0]
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, body)
            else:
                self.error_Response()
        elif path == "/multipart2":
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            content_length = int(self.headers.get('Content-length', 0))
            if ctype == 'multipart/form-data':
                req = cgi.parse_multipart(self.rfile, pdict)
                f = req['f'][0]
                if not req['a'] == ['aa']:
                    self.error_Response()
                if not req['b'] == ['bb','éàù@']:
                    self.error_Response()
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, str(len(f)))
            else:
                self.error_Response()
        elif path == "/multipart3":
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            content_length = int(self.headers.get('Content-length', 0))
            if ctype == 'multipart/form-data':
                req = cgi.parse_multipart(self.rfile, pdict)
                f = req['f'][0]
                if not req['a'] == ['aa']:
                    self.error_Response()
                if not req['b'] == ['éàù@']:
                    self.error_Response()
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, str(len(f)))
            else:
                self.error_Response()
        elif path == "/multipart4":
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            content_length = int(self.headers.get('Content-length', 0))
            if ctype == 'multipart/form-data':
                req = cgi.parse_multipart(self.rfile, pdict)
                f = req['f'][0]
                if not req['a'] == ['aa']:
                    self.error_Response()
                if not req['b'] == ['éàù@']:
                    self.error_Response()
                extra_headers = [('Content-type', 'text/plain')]
                self._respond(200, extra_headers, f)
            else:
                self.error_Response()
        elif path == "/1M":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = self.rfile.read(content_length)
            self._respond(200, extra_headers, str(len(body)))
        elif path == "/large":
            content_type = self.headers.get('content-type', 'text/plain')
            extra_headers.append(('Content-Type', content_type))
            content_length = int(self.headers.get('Content-length', 0))
            body = self.rfile.read(content_length)
            extra_headers.append(('Content-Length', str(len(body))))
            self._respond(200, extra_headers, body)
        elif path == "/list":
            content_length = int(self.headers.get('Content-length', 0))
            body = self.rfile.read(content_length)
            extra_headers.append(('Content-Length', str(len(body))))
            self._respond(200, extra_headers, body)
        elif path == "/chunked":
            te = (self.headers.get("transfer-encoding") == "chunked")
            if te:
                body = self.rfile.read(29)
                extra_headers.append(('Content-Length', "29"))
                self._respond(200, extra_headers, body)
            else:
                self.error_Response()
        else:
            self.error_Response('Bad path')
            
    do_PUT = do_POST

    def do_DELETE(self):
        if self.path == "/delete":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, '')
        else:
            self.error_Response()

    def do_HEAD(self):
        if self.path == "/ok":
            extra_headers = [('Content-type', 'text/plain')]
            self._respond(200, extra_headers, '')
        else:
            self.error_Response()

    def error_Response(self, message=None):
        req = [
            ('HTTP method', self.command),
            ('path', self.path),
            ]
        if message:
            req.append(('message', message))

        body_parts = ['Bad request:\r\n']
        for k, v in req:
            body_parts.append(' %s: %s\r\n' % (k, v))
        body = ''.join(body_parts)
        self._respond(400, [('Content-type', 'text/plain'),
        ('Content-Length', str(len(body)))], body)


    def _respond(self, http_code, extra_headers, body):
        self.send_response(http_code)
        keys = []
        for k, v in extra_headers:
            self.send_header(k, v)
            keys.append(k)
        if body:
            body = to_bytestring(body)
        #if body and "Content-Length" not in keys:
        #    self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
        self.wfile.close()

    def finish(self):
        if not self.wfile.closed:
            self.wfile.flush()
        self.wfile.close()
        self.rfile.close()

server_thread = None
def run_server_test():
    global server_thread
    if server_thread is not None:
        return

        
    server = HTTPServer((HOST, PORT), HTTPTestHandler)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.setDaemon(True)
    server_thread.start()

########NEW FILE########
