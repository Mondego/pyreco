__FILENAME__ = gunicorn_ext
import os
import inspect
import gunicorn.config as guncfg

HEAD = """
.. _settings:

Settings
========

This is an exhaustive list of settings for Gunicorn. Some settings are only
able to be set from a configuration file. The setting name is what should be
used in the configuration file. The command line arguments are listed as well
for reference on setting at the command line.

"""

def format_settings(app):
    settings_file = os.path.join(app.srcdir, "settings.rst")
    ret = []
    for i, s in enumerate(guncfg.KNOWN_SETTINGS):
        if i == 0 or s.section != guncfg.KNOWN_SETTINGS[i - 1].section:
            ret.append("%s\n%s\n\n" % (s.section, "-" * len(s.section)))
        ret.append(fmt_setting(s))

    with open(settings_file, 'w') as settings:
        settings.write(HEAD)
        settings.write(''.join(ret))

def fmt_setting(s):
    if callable(s.default):
        val = inspect.getsource(s.default)
        val = "\n".join("    %s" % l for l in val.splitlines())
        val = " ::\n\n" + val
    else:
        val = "``%s``" % s.default

    if s.cli and s.meta:
        args = ["%s %s" % (arg, s.meta) for arg in s.cli]
        cli = ', '.join(args)
    elif s.cli:
        cli = ", ".join(s.cli)

    out = []
    out.append("%s" % s.name)
    out.append("~" * len(s.name))
    out.append("")
    if s.cli:
        out.append("* ``%s``" % cli)
    out.append("* %s" % val)
    out.append("")
    out.append(s.desc)
    out.append("")
    out.append("")
    return "\n".join(out)

def setup(app):
    app.connect('builder-inited', format_settings)

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
import hashlib
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

# Maximum number of urls in each sitemap, before next Sitemap is created
MAXURLS_PER_SITEMAP = 50000

# Suffix on a Sitemap index file
SITEINDEX_SUFFIX = '_index.xml'

# Regular expressions tried for extracting URLs from access logs.
ACCESSLOG_CLF_PATTERN = re.compile(
  r'.+\s+"([^\s]+)\s+([^\s]+)\s+HTTP/\d+\.\d+"\s+200\s+.*'
  )

# Match patterns for lastmod attributes
LASTMOD_PATTERNS = map(re.compile, [
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
SITEINDEX_HEADER   = \
  '<?xml version="1.0" encoding="UTF-8"?>\n' \
  '<sitemapindex\n' \
  '  xmlns="http://www.google.com/schemas/sitemap/0.84"\n' \
  '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n' \
  '  xsi:schemaLocation="http://www.google.com/schemas/sitemap/0.84\n' \
  '                      http://www.google.com/schemas/sitemap/0.84/' \
  'siteindex.xsd">\n'
SITEINDEX_FOOTER   = '</sitemapindex>\n'
SITEINDEX_ENTRY    = \
  ' <sitemap>\n' \
  '  <loc>%(loc)s</loc>\n' \
  '  <lastmod>%(lastmod)s</lastmod>\n' \
  ' </sitemap>\n'
SITEMAP_HEADER     = \
  '<?xml version="1.0" encoding="UTF-8"?>\n' \
  '<urlset\n' \
  '  xmlns="http://www.google.com/schemas/sitemap/0.84"\n' \
  '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n' \
  '  xsi:schemaLocation="http://www.google.com/schemas/sitemap/0.84\n' \
  '                      http://www.google.com/schemas/sitemap/0.84/' \
  'sitemap.xsd">\n'
SITEMAP_FOOTER     = '</urlset>\n'
SITEURL_XML_PREFIX = ' <url>\n'
SITEURL_XML_SUFFIX = ' </url>\n'

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
  ('http', 'www.google.com', 'webmasters/sitemaps/ping', {}, '', 'sitemap')
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
      hash = hashlib.md5(text).hexdigest()
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
      hash = hashlib.md5(text).hexdigest()
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
      match = False
      self.lastmod = self.lastmod.upper()
      for pattern in LASTMOD_PATTERNS:
        match = pattern.match(self.lastmod)
        if match:
          break
      if not match:
        output.Warn('Lastmod "%s" does not appear to be in ISO8601 format on '
                    'URL: %s' % (self.lastmod, self.loc))
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
      return hashlib.md5(self.loc[:-1]).hexdigest()
    return hashlib.md5(self.loc).hexdigest()
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


class InputDirectory:
  """
  Each Input class knows how to yield a set of URLs from a data source.

  This one handles a directory that acts as base for walking the filesystem.
  """

  def __init__(self, attributes, base_url):
    self._path         = None               # The directory
    self._url          = None               # The URL equivelant
    self._default_file = None

    if not ValidateAttributes('DIRECTORY', attributes, ('path', 'url',
                                                           'default_file')):
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

    self._path         = path
    self._url          = url
    self._default_file = file
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


class InputSitemap(xml.sax.handler.ContentHandler):

  """
  Each Input class knows how to yield a set of URLs from a data source.

  This one handles Sitemap files and Sitemap index files.  For the sake
  of simplicity in design (and simplicity in interfacing with the SAX
  package), we do not handle these at the same time, recursively.  Instead
  we read an index file completely and make a list of Sitemap files, then
  go back and process each Sitemap.
  """

  class _ContextBase(object):
    
    """Base class for context handlers in our SAX processing.  A context
    handler is a class that is responsible for understanding one level of
    depth in the XML schema.  The class knows what sub-tags are allowed,
    and doing any processing specific for the tag we're in.

    This base class is the API filled in by specific context handlers,
    all defined below.
    """
    
    def __init__(self, subtags):
      """Initialize with a sequence of the sub-tags that would be valid in
      this context."""
      self._allowed_tags = subtags          # Sequence of sub-tags we can have
      self._last_tag     = None             # Most recent seen sub-tag
    #end def __init__

    def AcceptTag(self, tag):
      """Returns True iff opening a sub-tag is valid in this context."""
      valid = tag in self._allowed_tags
      if valid:
        self._last_tag = tag
      else:
        self._last_tag = None
      return valid
    #end def AcceptTag

    def AcceptText(self, text):
      """Returns True iff a blurb of text is valid in this context."""
      return False
    #end def AcceptText

    def Open(self):
      """The context is opening.  Do initialization."""
      pass
    #end def Open

    def Close(self):
      """The context is closing.  Return our result, if any."""
      pass
    #end def Close

    def Return(self, result):
      """We're returning to this context after handling a sub-tag.  This
      method is called with the result data from the sub-tag that just
      closed.  Here in _ContextBase, if we ever see a result it means
      the derived child class forgot to override this method."""
      if result:
        raise NotImplementedError
    #end def Return
  #end class _ContextBase

  class _ContextUrlSet(_ContextBase):
    
    """Context handler for the document node in a Sitemap."""
    
    def __init__(self):
      InputSitemap._ContextBase.__init__(self, ('url',))
    #end def __init__
  #end class _ContextUrlSet

  class _ContextUrl(_ContextBase):
    
    """Context handler for a URL node in a Sitemap."""
    
    def __init__(self, consumer):
      """Initialize this context handler with the callable consumer that
      wants our URLs."""
      InputSitemap._ContextBase.__init__(self, URL.__slots__)
      self._url          = None            # The URL object we're building
      self._consumer     = consumer        # Who wants to consume it
    #end def __init__

    def Open(self):
      """Initialize the URL."""
      assert not self._url
      self._url = URL()
    #end def Open

    def Close(self):
      """Pass the URL to the consumer and reset it to None."""
      assert self._url
      self._consumer(self._url, False)
      self._url = None
    #end def Close
  
    def Return(self, result):
      """A value context has closed, absorb the data it gave us."""
      assert self._url
      if result:
        self._url.TrySetAttribute(self._last_tag, result)
    #end def Return
  #end class _ContextUrl

  class _ContextSitemapIndex(_ContextBase):
    
    """Context handler for the document node in an index file."""
    
    def __init__(self):
      InputSitemap._ContextBase.__init__(self, ('sitemap',))
      self._loclist = []                    # List of accumulated Sitemap URLs
    #end def __init__

    def Open(self):
      """Just a quick verify of state."""
      assert not self._loclist
    #end def Open

    def Close(self):
      """Return our list of accumulated URLs."""
      if self._loclist:
        temp = self._loclist
        self._loclist = []
        return temp
    #end def Close
  
    def Return(self, result):
      """Getting a new loc URL, add it to the collection."""
      if result:
        self._loclist.append(result)
    #end def Return
  #end class _ContextSitemapIndex

  class _ContextSitemap(_ContextBase):
    
    """Context handler for a Sitemap entry in an index file."""
    
    def __init__(self):
      InputSitemap._ContextBase.__init__(self, ('loc', 'lastmod'))
      self._loc = None                      # The URL to the Sitemap
    #end def __init__

    def Open(self):
      """Just a quick verify of state."""
      assert not self._loc
    #end def Open

    def Close(self):
      """Return our URL to our parent."""
      if self._loc:
        temp = self._loc
        self._loc = None
        return temp
      output.Warn('In the Sitemap index file, a "sitemap" entry had no "loc".')
    #end def Close

    def Return(self, result):
      """A value has closed.  If it was a 'loc', absorb it."""
      if result and (self._last_tag == 'loc'):
        self._loc = result
    #end def Return
  #end class _ContextSitemap

  class _ContextValue(_ContextBase):
    
    """Context handler for a single value.  We return just the value.  The
    higher level context has to remember what tag led into us."""
    
    def __init__(self):
      InputSitemap._ContextBase.__init__(self, ())
      self._text        = None
    #end def __init__

    def AcceptText(self, text):
      """Allow all text, adding it to our buffer."""
      if self._text:
        self._text = self._text + text
      else:
        self._text = text
      return True
    #end def AcceptText

    def Open(self):
      """Initialize our buffer."""
      self._text = None
    #end def Open

    def Close(self):
      """Return what's in our buffer."""
      text = self._text
      self._text = None
      if text:
        text = text.strip()
      return text
    #end def Close
  #end class _ContextValue

  def __init__(self, attributes):
    """Initialize with a dictionary of attributes from our entry in the
    config file."""
    xml.sax.handler.ContentHandler.__init__(self)
    self._pathlist      = None              # A list of files
    self._current       = -1                # Current context in _contexts
    self._contexts      = None              # The stack of contexts we allow
    self._contexts_idx  = None              # ...contexts for index files
    self._contexts_stm  = None              # ...contexts for Sitemap files

    if not ValidateAttributes('SITEMAP', attributes, ['path']):
      return
    
    # Init the first file path
    path = attributes.get('path')
    if path:
      path = encoder.MaybeNarrowPath(path)
      if os.path.isfile(path):
        output.Log('Input: From SITEMAP "%s"' % path, 2)
        self._pathlist = [path]
      else:
        output.Error('Can not locate file "%s"' % path)
    else:
      output.Error('Sitemap entries must have a "path" attribute.')
  #end def __init__

  def ProduceURLs(self, consumer):
    """In general: Produces URLs from our data source, hand them to the
    callable consumer.

    In specific: Iterate over our list of paths and delegate the actual
    processing to helper methods.  This is a complexity no other data source
    needs to suffer.  We are unique in that we can have files that tell us
    to bring in other files.

    Note the decision to allow an index file or not is made in this method.
    If we call our parser with (self._contexts == None) the parser will
    grab whichever context stack can handle the file.  IE: index is allowed.
    If instead we set (self._contexts = ...) before parsing, the parser
    will only use the stack we specify.  IE: index not allowed.
    """
    # Set up two stacks of contexts
    self._contexts_idx = [InputSitemap._ContextSitemapIndex(),
                          InputSitemap._ContextSitemap(),
                          InputSitemap._ContextValue()]
    
    self._contexts_stm = [InputSitemap._ContextUrlSet(),
                          InputSitemap._ContextUrl(consumer),
                          InputSitemap._ContextValue()]

    # Process the first file
    assert self._pathlist
    path = self._pathlist[0]
    self._contexts = None                # We allow an index file here
    self._ProcessFile(path)

    # Iterate over remaining files
    self._contexts = self._contexts_stm  # No index files allowed
    for path in self._pathlist[1:]:
      self._ProcessFile(path)
  #end def ProduceURLs

  def _ProcessFile(self, path):
    """Do per-file reading/parsing/consuming for the file path passed in."""
    assert path
    
    # Open our file
    (frame, file) = OpenFileForRead(path, 'SITEMAP')
    if not file:
      return

    # Rev up the SAX engine
    try:
      self._current = -1
      xml.sax.parse(file, self)
    except SchemaError:
      output.Error('An error in file "%s" made us abort reading the Sitemap.'
                   % path)
    except IOError:
      output.Error('Cannot read from file "%s"' % path)
    except xml.sax._exceptions.SAXParseException, e:
      output.Error('XML error in the file "%s" (line %d, column %d): %s' %
                   (path, e._linenum, e._colnum, e.getMessage()))

    # Clean up
    file.close()
    if frame:
      frame.close()
  #end def _ProcessFile

  def _MungeLocationListIntoFiles(self, urllist):
    """Given a list of URLs, munge them into our self._pathlist property.
    We do this by assuming all the files live in the same directory as
    the first file in the existing pathlist.  That is, we assume a
    Sitemap index points to Sitemaps only in the same directory.  This
    is not true in general, but will be true for any output produced
    by this script.
    """
    assert self._pathlist
    path = self._pathlist[0]
    path = os.path.normpath(path)
    dir  = os.path.dirname(path)
    wide = False
    if type(path) == types.UnicodeType:
      wide = True

    for url in urllist:
      url = URL.Canonicalize(url)
      output.Log('Index points to Sitemap file at: %s' % url, 2)
      (scheme, netloc, path, query, frag) = urlparse.urlsplit(url)
      file = os.path.basename(path)
      file = urllib.unquote(file)
      if wide:
        file = encoder.WidenText(file)
      if dir:
        file = dir + os.sep + file
      if file:
        self._pathlist.append(file)
        output.Log('Will attempt to read Sitemap file: %s' % file, 1)
  #end def _MungeLocationListIntoFiles

  def startElement(self, tag, attributes):
    """SAX processing, called per node in the config stream.
    As long as the new tag is legal in our current context, this
    becomes an Open call on one context deeper.
    """
    # If this is the document node, we may have to look for a context stack
    if (self._current < 0) and not self._contexts:
      assert self._contexts_idx and self._contexts_stm
      if tag == 'urlset':
        self._contexts = self._contexts_stm
      elif tag == 'sitemapindex':
        self._contexts = self._contexts_idx
        output.Log('File is a Sitemap index.', 2)
      else:
        output.Error('The document appears to be neither a Sitemap nor a '
                     'Sitemap index.')
        raise SchemaError

    # Display a kinder error on a common mistake
    if (self._current < 0) and (self._contexts == self._contexts_stm) and (
      tag == 'sitemapindex'):
      output.Error('A Sitemap index can not refer to another Sitemap index.')
      raise SchemaError

    # Verify no unexpected attributes
    if attributes:
      text = ''
      for attr in attributes.keys():
        # The document node will probably have namespaces
        if self._current < 0:
          if attr.find('xmlns') >= 0:
            continue
          if attr.find('xsi') >= 0:
            continue
        if text:
          text = text + ', '
        text = text + attr
      if text:
        output.Warn('Did not expect any attributes on any tag, instead tag '
                     '"%s" had attributes: %s' % (tag, text))

    # Switch contexts
    if (self._current < 0) or (self._contexts[self._current].AcceptTag(tag)):
      self._current = self._current + 1
      assert self._current < len(self._contexts)
      self._contexts[self._current].Open()
    else:
      output.Error('Can not accept tag "%s" where it appears.' % tag)
      raise SchemaError
  #end def startElement

  def endElement(self, tag):
    """SAX processing, called per node in the config stream.
    This becomes a call to Close on one context followed by a call
    to Return on the previous.
    """
    tag = tag  # Avoid warning on unused argument
    assert self._current >= 0
    retval = self._contexts[self._current].Close()
    self._current = self._current - 1
    if self._current >= 0:
      self._contexts[self._current].Return(retval)
    elif retval and (self._contexts == self._contexts_idx):
      self._MungeLocationListIntoFiles(retval)
  #end def endElement

  def characters(self, text):
    """SAX processing, called when text values are read.  Important to
    note that one single text value may be split across multiple calls
    of this method.
    """
    if (self._current < 0) or (
      not self._contexts[self._current].AcceptText(text)):
      if text.strip():
        output.Error('Can not accept text "%s" where it appears.' % text)
        raise SchemaError
  #end def characters
#end class InputSitemap


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

      file.write(SITEMAP_HEADER)
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

    # Make a lastmod time
    lastmod = TimestampISO8601(time.time())

    # Write to it
    try:
      fd = open(filename, 'wt')
      fd.write(SITEINDEX_HEADER)

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
      output.Log('Notifying: %s' % ping[1], 1)
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
           'suppress_search_engine_notify')):
          return

        verbose           = attributes.get('verbose', 0)
        if verbose:
          output.SetVerbose(verbose)

        self._default_enc = attributes.get('default_encoding')
        self._base_url    = attributes.get('base_url')
        self._store_into  = attributes.get('store_into')
        if not self._suppress:
          self._suppress  = attributes.get('suppress_search_engine_notify',
                                            False)
        self.ValidateBasicConfig()

    elif tag == 'filter':
      self._filters.append(Filter(attributes))

    elif tag == 'url':
      self._inputs.append(InputURL(attributes))

    elif tag == 'urllist':
      for attributeset in ExpandPathAttribute(attributes, 'path'):
        self._inputs.append(InputURLList(attributeset))

    elif tag == 'directory':
      self._inputs.append(InputDirectory(attributes, self._base_url))

    elif tag == 'accesslog':
      for attributeset in ExpandPathAttribute(attributes, 'path'):
        self._inputs.append(InputAccessLog(attributeset))

    elif tag == 'sitemap':
      for attributeset in ExpandPathAttribute(attributes, 'path'):
        self._inputs.append(InputSitemap(attributeset))

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
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Gunicorn documentation build configuration file
#
import sys, os

DOCS_DIR = os.path.abspath(os.path.dirname(__file__))

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

# for gunicorn_ext.py
sys.path.append(os.path.join(DOCS_DIR, os.pardir))
sys.path.insert(0, os.path.join(DOCS_DIR, os.pardir, os.pardir))

extensions = ['gunicorn_ext']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

# General information about the project.
project = u'Gunicorn'
copyright = u'2012, Benoit Chesneau'
# gunicorn version
import gunicorn
release = version = gunicorn.__version__

exclude_patterns = []
pygments_style = 'sphinx'


# -- Options for HTML output ---------------------------------------------------

if not on_rtd:  # only import and set the theme if we're building docs locally
    try:
        import sphinx_rtd_theme
    except ImportError:
        html_theme = 'default'
    else:
        html_theme = 'sphinx_rtd_theme'
        html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
else:
    html_theme = 'default'

html_static_path = ['_static']
htmlhelp_basename = 'Gunicorndoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {

}

latex_documents = [
  ('index', 'Gunicorn.tex', u'Gunicorn Documentation',
   u'Benoit Chesneau', 'manual'),
]


# -- Options for manual page output --------------------------------------------
man_pages = [
    ('index', 'gunicorn', u'Gunicorn Documentation',
     [u'Benoit Chesneau'], 1)
]

texinfo_documents = [
  ('index', 'Gunicorn', u'Gunicorn Documentation',
   u'Benoit Chesneau', 'Gunicorn', 'One line description of project.',
   'Miscellaneous'),
]


########NEW FILE########
__FILENAME__ = alt_spec
# -*- coding: utf-8 -
#
# An example of how to pass information from the command line to
# a WSGI app. Only applies to the native WSGI workers used by
# Gunicorn sync (default) workers.
#
#   $ gunicorn 'alt_spec:load(arg)'
#
# Single quoting is generally necessary for shell escape semantics.
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

def load(arg):
    def app(environ, start_response):
        data = 'Hello, %s!\n' % arg
        status = '200 OK'
        response_headers = [
            ('Content-type','text/plain'),
            ('Content-Length', str(len(data)))
        ]
        start_response(status, response_headers)
        return iter([data])
    return app


########NEW FILE########
__FILENAME__ = bad
import tempfile
files = []
def app(environ, start_response):
    files.append(tempfile.mkstemp())
    start_response('200 OK', [('Content-type', 'text/plain'), ('Content-length', '2')])
    return ['ok']

########NEW FILE########
__FILENAME__ = boot_fail

raise RuntimeError("Bad app!")

def app(environ, start_response):
    assert 1 == 2, "Shouldn't get here."

########NEW FILE########
__FILENAME__ = example_config
# Sample Gunicorn configuration file.

#
# Server socket
#
#   bind - The socket to bind.
#
#       A string of the form: 'HOST', 'HOST:PORT', 'unix:PATH'.
#       An IP is a valid HOST.
#
#   backlog - The number of pending connections. This refers
#       to the number of clients that can be waiting to be
#       served. Exceeding this number results in the client
#       getting an error when attempting to connect. It should
#       only affect servers under significant load.
#
#       Must be a positive integer. Generally set in the 64-2048
#       range.
#

bind = '127.0.0.1:8000'
backlog = 2048

#
# Worker processes
#
#   workers - The number of worker processes that this server
#       should keep alive for handling requests.
#
#       A positive integer generally in the 2-4 x $(NUM_CORES)
#       range. You'll want to vary this a bit to find the best
#       for your particular application's work load.
#
#   worker_class - The type of workers to use. The default
#       async class should handle most 'normal' types of work
#       loads. You'll want to read http://gunicorn/deployment.hml
#       for information on when you might want to choose one
#       of the other worker classes.
#
#       An string referring to a 'gunicorn.workers' entry point
#       or a python path to a subclass of
#       gunicorn.workers.base.Worker. The default provided values
#       are:
#
#           egg:gunicorn#sync
#           egg:gunicorn#eventlet   - Requires eventlet >= 0.9.7
#           egg:gunicorn#gevent     - Requires gevent >= 0.12.2 (?)
#           egg:gunicorn#tornado    - Requires tornado >= 0.2
#
#   worker_connections - For the eventlet and gevent worker classes
#       this limits the maximum number of simultaneous clients that
#       a single process can handle.
#
#       A positive integer generally set to around 1000.
#
#   timeout - If a worker does not notify the master process in this
#       number of seconds it is killed and a new worker is spawned
#       to replace it.
#
#       Generally set to thirty seconds. Only set this noticeably
#       higher if you're sure of the repercussions for sync workers.
#       For the non sync workers it just means that the worker
#       process is still communicating and is not tied to the length
#       of time required to handle a single request.
#
#   keepalive - The number of seconds to wait for the next request
#       on a Keep-Alive HTTP connection.
#
#       A positive integer. Generally set in the 1-5 seconds range.
#

workers = 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

#
# Debugging
#
#   debug - Turn on debugging in the server. This limits the number of
#       worker processes to 1 and changes some error handling that's
#       sent to clients.
#
#       True or False
#
#   spew - Install a trace function that spews every line of Python
#       that is executed when running the server. This is the
#       nuclear option.
#
#       True or False
#

debug = False
spew = False

#
# Server mechanics
#
#   daemon - Detach the main Gunicorn process from the controlling
#       terminal with a standard fork/fork sequence.
#
#       True or False
#
#   pidfile - The path to a pid file to write
#
#       A path string or None to not write a pid file.
#
#   user - Switch worker processes to run as this user.
#
#       A valid user id (as an integer) or the name of a user that
#       can be retrieved with a call to pwd.getpwnam(value) or None
#       to not change the worker process user.
#
#   group - Switch worker process to run as this group.
#
#       A valid group id (as an integer) or the name of a user that
#       can be retrieved with a call to pwd.getgrnam(value) or None
#       to change the worker processes group.
#
#   umask - A mask for file permissions written by Gunicorn. Note that
#       this affects unix socket permissions.
#
#       A valid value for the os.umask(mode) call or a string
#       compatible with int(value, 0) (0 means Python guesses
#       the base, so values like "0", "0xFF", "0022" are valid
#       for decimal, hex, and octal representations)
#
#   tmp_upload_dir - A directory to store temporary request data when
#       requests are read. This will most likely be disappearing soon.
#
#       A path to a directory where the process owner can write. Or
#       None to signal that Python should choose one on its own.
#

daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

#
#   Logging
#
#   logfile - The path to a log file to write to.
#
#       A path string. "-" means log to stdout.
#
#   loglevel - The granularity of log output
#
#       A string of "debug", "info", "warning", "error", "critical"
#

errorlog = '-'
loglevel = 'info'
accesslog = '-'

#
# Process naming
#
#   proc_name - A base to use with setproctitle to change the way
#       that Gunicorn processes are reported in the system process
#       table. This affects things like 'ps' and 'top'. If you're
#       going to be running more than one instance of Gunicorn you'll
#       probably want to set a name to tell them apart. This requires
#       that you install the setproctitle module.
#
#       A string or None to choose a default of something like 'gunicorn'.
#

proc_name = None

#
# Server hooks
#
#   post_fork - Called just after a worker has been forked.
#
#       A callable that takes a server and worker instance
#       as arguments.
#
#   pre_fork - Called just prior to forking the worker subprocess.
#
#       A callable that accepts the same arguments as after_fork
#
#   pre_exec - Called just prior to forking off a secondary
#       master process during things like config reloading.
#
#       A callable that takes a server instance as the sole argument.
#

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    pass

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spwawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or TERM signal")

    ## get traceback info
    import threading, sys, traceback
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name.get(threadId,""),
            threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename,
                lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    worker.log.debug("\n".join(code))

########NEW FILE########
__FILENAME__ = cherryapp
import cherrypy

cherrypy.config.update({'environment': 'embedded'})

class Root(object):
    def index(self):
        return 'Hello World!'
    index.exposed = True

app = cherrypy.Application(Root(), script_name=None, config=None)

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
# Django settings for djangotest project.

import platform
PRODUCTION_MODE = platform.node().startswith('http')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('benoitc', 'bchesneau@gmail.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
    }
}

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True

USE_L10N = True

MEDIA_ROOT = ''

MEDIA_URL = ''

STATIC_ROOT = ''

STATIC_URL = '/static/'

ADMIN_MEDIA_PREFIX = '/static/admin/'

STATICFILES_DIRS = (
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SECRET_KEY = 'c-u@jrg$dy)g7%)=jg)c40d0)4z0b%mltvtu)85l1&*(zwau(f'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)


FILE_UPLOAD_HANDLERS = (
        "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)

ROOT_URLCONF = 'djangotest.urls'

TEMPLATE_DIRS = ()


SOME_VALUE = "hello world"

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djangotest.testing',
    'gunicorn',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^acsv$', 'testing.views.acsv'),
    url(r'^$', 'testing.views.home'),
    
)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

import csv
import os
from django import forms
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
import tempfile

class MsgForm(forms.Form):
    subject = forms.CharField(max_length=100)
    message = forms.CharField()
    f = forms.FileField()


def home(request):
    from django.conf import settings
    print(settings.SOME_VALUE)
    subject = None
    message = None
    size = 0
    print(request.META)
    if request.POST:
        form = MsgForm(request.POST, request.FILES)
        print(request.FILES)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            f = request.FILES['f']
            size = int(os.fstat(f.fileno())[6])
    else:
        form = MsgForm()


    return render_to_response('home.html', {
        'form': form,
        'subject': subject,
        'message': message,
        'size': size
    }, RequestContext(request))


def acsv(request):
    rows = [
        {'a': 1, 'b': 2},
        {'a': 3, 'b': 3}
    ]

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report.csv'

    writer = csv.writer(response)
    writer.writerow(['a', 'b'])

    for r in rows:
        writer.writerow([r['a'], r['b']])

    return response

########NEW FILE########
__FILENAME__ = urls

from django.conf.urls.defaults import patterns,include

urlpatterns = patterns('',
    (r'^', include("testing.urls")),
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testing.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = middleware
from multiprocessing import Process, Queue
import requests
import gevent

def child_process(queue):
    while True:
        print(queue.get())
        requests.get('http://requestb.in/15s95oz1')

class GunicornSubProcessTestMiddleware(object):
    def __init__(self):
        super(GunicornSubProcessTestMiddleware, self).__init__()
        self.queue = Queue()
        self.process = Process(target=child_process, args=(self.queue,))
        self.process.start()

    def process_request(self, request):
        self.queue.put(('REQUEST',))

    def process_response(self, request, response):
        self.queue.put(('RESPONSE',response.status_code))
        return response

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^acsv$', 'testing.apps.someapp.views.acsv'),
    url(r'^$', 'testing.apps.someapp.views.home'),

)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

import csv
import io
import os
from django import forms
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
import tempfile

class MsgForm(forms.Form):
    subject = forms.CharField(max_length=100)
    message = forms.CharField()
    f = forms.FileField()


def home(request):
    from django.conf import settings
    print(settings.SOME_VALUE)
    subject = None
    message = None
    size = 0
    print(request.META)
    if request.POST:
        form = MsgForm(request.POST, request.FILES)
        print(request.FILES)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            f = request.FILES['f']


            if not hasattr(f, "fileno"):
                size = len(f.read())
            else:
                try:
                    size = int(os.fstat(f.fileno())[6])
                except io.UnsupportedOperation:
                    size = len(f.read())
    else:
        form = MsgForm()


    return render_to_response('home.html', {
        'form': form,
        'subject': subject,
        'message': message,
        'size': size
    }, RequestContext(request))


def acsv(request):
    rows = [
        {'a': 1, 'b': 2},
        {'a': 3, 'b': 3}
    ]

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report.csv'

    writer = csv.writer(response)
    writer.writerow(['a', 'b'])

    for r in rows:
        writer.writerow([r['a'], r['b']])

    return response

########NEW FILE########
__FILENAME__ = settings
# Django settings for testing project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'testdb.sql',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '0!jubm9ho=s_32kac4wt#$9+hb#qzsg6c7+%83hqujcdfw%5*-'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # uncomment the next line to test multiprocessing
    #'testing.apps.someapp.middleware.GunicornSubProcessTestMiddleware',
)

ROOT_URLCONF = 'testing.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'testing.wsgi.application'

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
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'testing.apps.someapp',
    'gunicorn'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

SOME_VALUE="test on reload"

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testing.views.home', name='home'),
    # url(r'^testing/', include('testing.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    (r'^', include("testing.apps.someapp.urls")),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for testing project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os
import sys

# make sure the current project is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                "..")))

# set the environment settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testing.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = flaskapp
# Run with:
#
#   $ gunicorn flaskapp:app
#

from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

########NEW FILE########
__FILENAME__ = flask_sendfile
import io

from flask import Flask, send_file

app = Flask(__name__)

@app.route('/')
def index():
    buf = io.BytesIO()
    buf.write('hello world')
    buf.seek(0)
    return send_file(buf,
                     attachment_filename="testing.txt",
                     as_attachment=True)

########NEW FILE########
__FILENAME__ = ittyapp
# Run with:
#
#   $ python ittyapp.py
#

from itty import *

@get('/')
def index(request):
    return 'Hello World!'

run_itty(server='gunicorn')

########NEW FILE########
__FILENAME__ = environment
"""Pylons environment configuration"""
import os

from mako.lookup import TemplateLookup
from pylons import config
from pylons.error import handle_mako_error

import pylonstest.lib.app_globals as app_globals
import pylonstest.lib.helpers
from pylonstest.config.routing import make_map

def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config``
    object
    """
    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='pylonstest', paths=paths)

    config['routes.map'] = make_map()
    config['pylons.app_globals'] = app_globals.Globals()
    config['pylons.h'] = pylonstest.lib.helpers

    # Create the Mako TemplateLookup, with the default auto-escaping
    config['pylons.app_globals'].mako_lookup = TemplateLookup(
        directories=paths['templates'],
        error_handler=handle_mako_error,
        module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
        input_encoding='utf-8', default_filters=['escape'],
        imports=['from webhelpers.html import escape'])

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)

########NEW FILE########
__FILENAME__ = middleware
"""Pylons middleware initialization"""
from beaker.middleware import CacheMiddleware, SessionMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from pylons import config
from pylons.middleware import ErrorHandler, StatusCodeRedirect
from pylons.wsgiapp import PylonsApp
from routes.middleware import RoutesMiddleware

from pylonstest.config.environment import load_environment

def make_app(global_conf, full_stack=True, static_files=True, **app_conf):
    """Create a Pylons WSGI application and return it

    ``global_conf``
        The inherited configuration for this application. Normally from
        the [DEFAULT] section of the Paste ini file.

    ``full_stack``
        Whether this application provides a full WSGI stack (by default,
        meaning it handles its own exceptions and errors). Disable
        full_stack when this application is "managed" by another WSGI
        middleware.

    ``static_files``
        Whether this application serves its own static files; disable
        when another web server is responsible for serving them.

    ``app_conf``
        The application's local configuration. Normally specified in
        the [app:<name>] section of the Paste ini file (where <name>
        defaults to main).

    """
    # Configure the Pylons environment
    load_environment(global_conf, app_conf)

    # The Pylons WSGI app
    app = PylonsApp()

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'])
    app = SessionMiddleware(app, config)
    app = CacheMiddleware(app, config)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)

    if asbool(full_stack):
        # Handle Python exceptions
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app)
        else:
            app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])

    # Establish the Registry for this application
    app = RegistryManager(app)

    if asbool(static_files):
        # Serve static files
        static_app = StaticURLParser(config['pylons.paths']['static_files'])
        app = Cascade([static_app, app])

    return app

########NEW FILE########
__FILENAME__ = routing
"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from pylons import config
from routes import Mapper

def make_map():
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    # CUSTOM ROUTES HERE

    map.connect('/{controller}/{action}')
    map.connect('/{controller}/{action}/{id}')

    return map

########NEW FILE########
__FILENAME__ = error
import cgi

from paste.urlparser import PkgResourcesParser
from pylons import request
from pylons.controllers.util import forward
from pylons.middleware import error_document_template
from webhelpers.html.builder import literal

from pylonstest.lib.base import BaseController

class ErrorController(BaseController):

    """Generates error documents as and when they are required.

    The ErrorDocuments middleware forwards to ErrorController when error
    related status codes are returned from the application.

    This behaviour can be altered by changing the parameters to the
    ErrorDocuments middleware in your config/middleware.py file.

    """

    def document(self):
        """Render the error document"""
        resp = request.environ.get('pylons.original_response')
        content = literal(resp.body) or cgi.escape(request.GET.get('message', ''))
        page = error_document_template % \
            dict(prefix=request.environ.get('SCRIPT_NAME', ''),
                 code=cgi.escape(request.GET.get('code', str(resp.status_int))),
                 message=content)
        return page

    def img(self, id):
        """Serve Pylons' stock images"""
        return self._serve_file('/'.join(['media/img', id]))

    def style(self, id):
        """Serve Pylons' stock stylesheets"""
        return self._serve_file('/'.join(['media/style', id]))

    def _serve_file(self, path):
        """Call Paste's FileApp (a WSGI application) to serve the file
        at the specified path
        """
        request.environ['PATH_INFO'] = '/%s' % path
        return forward(PkgResourcesParser('pylons', 'pylons'))

########NEW FILE########
__FILENAME__ = hello
import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort

from pylonstest.lib.base import BaseController, render

log = logging.getLogger(__name__)

class HelloController(BaseController):

    def index(self):
        # Return a rendered template
        #return render('/hello.mako')
        # or, return a response
        return 'Hello World'

########NEW FILE########
__FILENAME__ = app_globals
"""The application's Globals object"""

class Globals(object):

    """Globals acts as a container for objects available throughout the
    life of the application

    """

    def __init__(self):
        """One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable

        """

########NEW FILE########
__FILENAME__ = base
"""The base Controller API

Provides the BaseController class for subclassing.
"""
from pylons.controllers import WSGIController
from pylons.templating import render_mako as render

class BaseController(WSGIController):

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']
        return WSGIController.__call__(self, environ, start_response)

########NEW FILE########
__FILENAME__ = helpers
"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
# Import helpers as desired, or define your own, ie:
#from webhelpers.html.tags import checkbox, password

########NEW FILE########
__FILENAME__ = test_hello
from pylonstest.tests import *

class TestHelloController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='hello', action='index'))
        # Test response...

########NEW FILE########
__FILENAME__ = test_models

########NEW FILE########
__FILENAME__ = pyramidapp
from pyramid.config import Configurator
from pyramid.response import Response

def hello_world(request):
    return Response('Hello world!')

def goodbye_world(request):
    return Response('Goodbye world!')

config = Configurator()
config.add_view(hello_world)
config.add_view(goodbye_world, name='goodbye')
app = config.make_wsgi_app()

########NEW FILE########
__FILENAME__ = tornadoapp
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.
#
# Run with:
#
#   $ gunicorn -k egg:gunicorn#tornado tornadoapp:app
#

from datetime import timedelta

from tornado.web import Application, RequestHandler, asynchronous
from tornado.ioloop import IOLoop

class MainHandler(RequestHandler):
    def get(self):
        self.write("Hello, world")

class LongPollHandler(RequestHandler):
    @asynchronous
    def get(self):
        lines = ['line 1\n', 'line 2\n']

        def send():
            try:
                self.write(lines.pop(0))
                self.flush()
            except:
                self.finish()
            else:
                IOLoop.instance().add_timeout(timedelta(0, 20), send)
        send()

app = Application([
    (r"/", MainHandler),
    (r"/longpoll", LongPollHandler)
])


########NEW FILE########
__FILENAME__ = log_app
import logging

log = logging.getLogger(__name__)

log.addHandler(logging.StreamHandler())

def app_factory(global_options, **local_options):
    return app

def app(environ, start_response):
    start_response("200 OK", [])
    log.debug("Hello Debug!")
    log.info("Hello Info!")
    log.warn("Hello Warn!")
    log.error("Hello Error!")
    return ["Hello World!\n"]

########NEW FILE########
__FILENAME__ = longpoll
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.


import sys
import time

class TestIter(object):

    def __iter__(self):
        lines = ['line 1\n', 'line 2\n']
        for line in lines:
            yield line
            time.sleep(20)

def app(environ, start_response):
    """Application which cooperatively pauses 20 seconds (needed to surpass normal timeouts) before responding"""
    data = b'Hello, World!\n'
    status = '200 OK'
    response_headers = [
        ('Content-type','text/plain'),
        ('Transfer-Encoding', "chunked"),
    ]
    sys.stdout.write('request received')
    sys.stdout.flush()
    start_response(status, response_headers)
    return TestIter()

########NEW FILE########
__FILENAME__ = multiapp
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.
#
# Run this application with:
#
#   $ gunicorn multiapp:app
#
# And then visit:
#
#   http://127.0.0.1:8000/app1url
#   http://127.0.0.1:8000/app2url
#   http://127.0.0.1:8000/this_is_a_404
#

try:
    from routes import Mapper
except:
    print("This example requires Routes to be installed")

# Obviously you'd import your app callables
# from different places...
from test import app as app1
from test import app as app2


class Application(object):
    def __init__(self):
        self.map = Mapper()
        self.map.connect('app1', '/app1url', app=app1)
        self.map.connect('app2', '/app2url', app=app2)

    def __call__(self, environ, start_response):
        match = self.map.routematch(environ=environ)
        if not match:
            return self.error404(environ, start_response)
        return match[0]['app'](environ, start_response)

    def error404(self, environ, start_response):
        html = b"""\
        <html>
          <head>
            <title>404 - Not Found</title>
          </head>
          <body>
            <h1>404 - Not Found</h1>
          </body>
        </html>
        """
        headers = [
            ('Content-Type', 'text/html'),
            ('Content-Length', str(len(html)))
        ]
        start_response('404 Not Found', headers)
        return [html]

app = Application()

########NEW FILE########
__FILENAME__ = multidomainapp
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import re

class SubDomainApp:
    """WSGI application to delegate requests based on domain name.
"""
    def __init__(self, mapping):
        self.mapping = mapping

    def __call__(self, environ, start_response):
        host = environ.get("HTTP_HOST", "")
        host = host.split(":")[0] # strip port

        for pattern, app in self.mapping:
            if re.match("^" + pattern + "$", host):
                return app(environ, start_response)
        else:
            start_response("404 Not Found", [])
            return [b""]

def hello(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Hello, world\n"]

def bye(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Goodbye!\n"]

app = SubDomainApp([
    ("localhost", hello),
    (".*", bye)
])

########NEW FILE########
__FILENAME__ = sendfile
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.
#
# Example code from Eventlet sources

import os
from wsgiref.validate import validator

#@validator
def app(environ, start_response):
    """Simplest possible application object"""
    status = '200 OK'
    fname = os.path.join(os.path.dirname(__file__), "hello.txt")
    f = open(fname, 'rb')

    response_headers = [
        ('Content-type','text/plain'),
    ]
    start_response(status, response_headers)

    return environ['wsgi.file_wrapper'](f)

########NEW FILE########
__FILENAME__ = slowclient
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import sys
import time


def app(environ, start_response):
    """Application which cooperatively pauses 10 seconds before responding"""
    data = b'Hello, World!\n'
    status = '200 OK'
    response_headers = [
        ('Content-type','text/plain'),
        ('Content-Length', str(len(data)))    ]
    sys.stdout.write('request received, pausing 10 seconds')
    sys.stdout.flush()
    time.sleep(10)
    start_response(status, response_headers)
    return iter([data])

########NEW FILE########
__FILENAME__ = standalone_app
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# An example of a standalone application using the internal API of Gunicorn.
#
#   $ python standalone_app.py
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import gunicorn
import gunicorn.app.base
import multiprocessing

def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1


def handler_app(environ, start_response):
    response_body = 'Works fine'
    status = '200 OK'

    response_headers = [
        ('Content-Type', 'text/plain'),
        ('Content-Lenfth', str(len(response_body))),
    ]

    start_response(status, response_headers)

    return [response_body]


class StandaloneApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = dict(options or {})
        self.application = app
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        tmp_config = map(
            lambda item: (item[0].lower(), item[1]),
            self.options.iteritems()
        )

        config = dict(
            (key, value)
            for key, value in tmp_config
            if key in self.cfg.settings and value is not None
        )

        for key, value in config.iteritems():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == '__main__':
    options = {
        'bind': '%s:%s' % ('127.0.0.1', '8080'),
        'workers': number_of_workers(),
    }
    StandaloneApplication(handler_app, options).run()

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.
#
# Example code from Eventlet sources

import os
import pprint
from wsgiref.validate import validator
import sys

from gunicorn import __version__
#@validator
def app(environ, start_response):
    """Simplest possible application object"""

    errors = environ['wsgi.errors']
    pprint.pprint(('ENVIRON', environ), stream=errors)

    data = b'Hello, World!\n'
    status = '200 OK'

    response_headers = [
        ('Content-type','text/plain'),
        ('Content-Length', str(len(data))),
        ('X-Gunicorn-Version', __version__),
        ("Test", "test тест"),
    ]
    start_response(status, response_headers)
    return iter([data])

########NEW FILE########
__FILENAME__ = gevent_websocket

import collections
import errno
import re
from hashlib import md5, sha1
import base64
from base64 import b64encode, b64decode
import socket
import struct
import logging
from socket import error as SocketError

import gevent
from gunicorn.workers.async import ALREADY_HANDLED

logger = logging.getLogger(__name__)

WS_KEY = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class WebSocketWSGI(object):
    def __init__(self, handler):
        self.handler = handler

    def verify_client(self, ws):
        pass

    def _get_key_value(self, key_value):
        if not key_value:
            return
        key_number = int(re.sub("\\D", "", key_value))
        spaces = re.subn(" ", "", key_value)[1]
        if key_number % spaces != 0:
            return
        part = key_number / spaces
        return part

    def __call__(self, environ, start_response):
        if not (environ.get('HTTP_CONNECTION').find('Upgrade') != -1 and
            environ['HTTP_UPGRADE'].lower() == 'websocket'):
            # need to check a few more things here for true compliance
            start_response('400 Bad Request', [('Connection','close')])
            return []

        sock = environ['gunicorn.socket']

        version = environ.get('HTTP_SEC_WEBSOCKET_VERSION')

        ws = WebSocket(sock, environ, version)

        handshake_reply = ("HTTP/1.1 101 Switching Protocols\r\n"
                   "Upgrade: websocket\r\n"
                   "Connection: Upgrade\r\n")

        key = environ.get('HTTP_SEC_WEBSOCKET_KEY')
        if key:
            ws_key = base64.b64decode(key)
            if len(ws_key) != 16:
                start_response('400 Bad Request', [('Connection','close')])
                return []

            protocols = []
            subprotocols = environ.get('HTTP_SEC_WEBSOCKET_PROTOCOL')
            ws_protocols = []
            if subprotocols:
                for s in subprotocols.split(','):
                    s = s.strip()
                    if s in protocols:
                        ws_protocols.append(s)
            if ws_protocols:
                handshake_reply += 'Sec-WebSocket-Protocol: %s\r\n' % ', '.join(ws_protocols)

            exts = []
            extensions = environ.get('HTTP_SEC_WEBSOCKET_EXTENSIONS')
            ws_extensions = []
            if extensions:
                for ext in extensions.split(','):
                    ext = ext.strip()
                    if ext in exts:
                        ws_extensions.append(ext)
            if ws_extensions:
                handshake_reply += 'Sec-WebSocket-Extensions: %s\r\n' % ', '.join(ws_extensions)

            handshake_reply +=  (
                "Sec-WebSocket-Origin: %s\r\n"
                "Sec-WebSocket-Location: ws://%s%s\r\n"
                "Sec-WebSocket-Version: %s\r\n"
                "Sec-WebSocket-Accept: %s\r\n\r\n"
                 % (
                    environ.get('HTTP_ORIGIN'),
                    environ.get('HTTP_HOST'),
                    ws.path,
                    version,
                    base64.b64encode(sha1(key + WS_KEY).digest())
                ))

        else:

            handshake_reply += (
                       "WebSocket-Origin: %s\r\n"
                       "WebSocket-Location: ws://%s%s\r\n\r\n" % (
                            environ.get('HTTP_ORIGIN'),
                            environ.get('HTTP_HOST'),
                            ws.path))

        sock.sendall(handshake_reply)

        try:
            self.handler(ws)
        except socket.error, e:
            if e[0] != errno.EPIPE:
                raise
        # use this undocumented feature of grainbows to ensure that it
        # doesn't barf on the fact that we didn't call start_response
        return ALREADY_HANDLED

class WebSocket(object):
    """A websocket object that handles the details of
    serialization/deserialization to the socket.

    The primary way to interact with a :class:`WebSocket` object is to
    call :meth:`send` and :meth:`wait` in order to pass messages back
    and forth with the browser.  Also available are the following
    properties:

    path
        The path value of the request.  This is the same as the WSGI PATH_INFO variable, but more convenient.
    protocol
        The value of the Websocket-Protocol header.
    origin
        The value of the 'Origin' header.
    environ
        The full WSGI environment for this request.

    """
    def __init__(self, sock, environ, version=76):
        """
        :param socket: The eventlet socket
        :type socket: :class:`eventlet.greenio.GreenSocket`
        :param environ: The wsgi environment
        :param version: The WebSocket spec version to follow (default is 76)
        """
        self.socket = sock
        self.origin = environ.get('HTTP_ORIGIN')
        self.protocol = environ.get('HTTP_WEBSOCKET_PROTOCOL')
        self.path = environ.get('PATH_INFO')
        self.environ = environ
        self.version = version
        self.websocket_closed = False
        self._buf = ""
        self._msgs = collections.deque()
        #self._sendlock = semaphore.Semaphore()

    @staticmethod
    def encode_hybi(buf, opcode, base64=False):
        """ Encode a HyBi style WebSocket frame.
        Optional opcode:
            0x0 - continuation
            0x1 - text frame (base64 encode buf)
            0x2 - binary frame (use raw buf)
            0x8 - connection close
            0x9 - ping
            0xA - pong
        """
        if base64:
            buf = b64encode(buf)

        b1 = 0x80 | (opcode & 0x0f) # FIN + opcode
        payload_len = len(buf)
        if payload_len <= 125:
            header = struct.pack('>BB', b1, payload_len)
        elif payload_len > 125 and payload_len < 65536:
            header = struct.pack('>BBH', b1, 126, payload_len)
        elif payload_len >= 65536:
            header = struct.pack('>BBQ', b1, 127, payload_len)

        #print("Encoded: %s" % repr(header + buf))

        return header + buf, len(header), 0

    @staticmethod
    def decode_hybi(buf, base64=False):
        """ Decode HyBi style WebSocket packets.
        Returns:
            {'fin'          : 0_or_1,
             'opcode'       : number,
             'mask'         : 32_bit_number,
             'hlen'         : header_bytes_number,
             'length'       : payload_bytes_number,
             'payload'      : decoded_buffer,
             'left'         : bytes_left_number,
             'close_code'   : number,
             'close_reason' : string}
        """

        f = {'fin'          : 0,
             'opcode'       : 0,
             'mask'         : 0,
             'hlen'         : 2,
             'length'       : 0,
             'payload'      : None,
             'left'         : 0,
             'close_code'   : None,
             'close_reason' : None}

        blen = len(buf)
        f['left'] = blen

        if blen < f['hlen']:
            return f # Incomplete frame header

        b1, b2 = struct.unpack_from(">BB", buf)
        f['opcode'] = b1 & 0x0f
        f['fin'] = (b1 & 0x80) >> 7
        has_mask = (b2 & 0x80) >> 7

        f['length'] = b2 & 0x7f

        if f['length'] == 126:
            f['hlen'] = 4
            if blen < f['hlen']:
                return f # Incomplete frame header
            (f['length'],) = struct.unpack_from('>xxH', buf)
        elif f['length'] == 127:
            f['hlen'] = 10
            if blen < f['hlen']:
                return f # Incomplete frame header
            (f['length'],) = struct.unpack_from('>xxQ', buf)

        full_len = f['hlen'] + has_mask * 4 + f['length']

        if blen < full_len: # Incomplete frame
            return f # Incomplete frame header

        # Number of bytes that are part of the next frame(s)
        f['left'] = blen - full_len

        # Process 1 frame
        if has_mask:
            # unmask payload
            f['mask'] = buf[f['hlen']:f['hlen']+4]
            b = c = ''
            if f['length'] >= 4:
                data = struct.unpack('<I', buf[f['hlen']:f['hlen']+4])[0]
                of1 = f['hlen']+4
                b = ''
                for i in xrange(0, int(f['length']/4)):
                    mask = struct.unpack('<I', buf[of1+4*i:of1+4*(i+1)])[0]
                    b += struct.pack('I', data ^ mask)

            if f['length'] % 4:
                l = f['length'] % 4
                of1 = f['hlen']
                of2 = full_len - l
                c = ''
                for i in range(0, l):
                    mask = struct.unpack('B', buf[of1 + i])[0]
                    data = struct.unpack('B', buf[of2 + i])[0]
                    c += chr(data ^ mask)

            f['payload'] = b + c
        else:
            print("Unmasked frame: %s" % repr(buf))
            f['payload'] = buf[(f['hlen'] + has_mask * 4):full_len]

        if base64 and f['opcode'] in [1, 2]:
            try:
                f['payload'] = b64decode(f['payload'])
            except:
                print("Exception while b64decoding buffer: %s" %
                        repr(buf))
                raise

        if f['opcode'] == 0x08:
            if f['length'] >= 2:
                f['close_code'] = struct.unpack_from(">H", f['payload'])
            if f['length'] > 3:
                f['close_reason'] = f['payload'][2:]

        return f


    @staticmethod
    def _pack_message(message):
        """Pack the message inside ``00`` and ``FF``

        As per the dataframing section (5.3) for the websocket spec
        """
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        elif not isinstance(message, str):
            message = str(message)
        packed = "\x00%s\xFF" % message
        return packed

    def _parse_messages(self):
        """ Parses for messages in the buffer *buf*.  It is assumed that
        the buffer contains the start character for a message, but that it
        may contain only part of the rest of the message.

        Returns an array of messages, and the buffer remainder that
        didn't contain any full messages."""
        msgs = []
        end_idx = 0
        buf = self._buf
        while buf:
            if self.version in ['7', '8', '13']:
                frame = self.decode_hybi(buf, base64=False)
                #print("Received buf: %s, frame: %s" % (repr(buf), frame))

                if frame['payload'] == None:
                    break
                else:
                    if frame['opcode'] == 0x8: # connection close
                        self.websocket_closed = True
                        break
                    #elif frame['opcode'] == 0x1:
                    else:
                        msgs.append(frame['payload']);
                        #msgs.append(frame['payload'].decode('utf-8', 'replace'));
                        #buf = buf[-frame['left']:]
                        if frame['left']:
                            buf = buf[-frame['left']:]
                        else:
                            buf = ''


            else:
                frame_type = ord(buf[0])
                if frame_type == 0:
                    # Normal message.
                    end_idx = buf.find("\xFF")
                    if end_idx == -1: #pragma NO COVER
                        break
                    msgs.append(buf[1:end_idx].decode('utf-8', 'replace'))
                    buf = buf[end_idx+1:]
                elif frame_type == 255:
                    # Closing handshake.
                    assert ord(buf[1]) == 0, "Unexpected closing handshake: %r" % buf
                    self.websocket_closed = True
                    break
                else:
                    raise ValueError("Don't understand how to parse this type of message: %r" % buf)
        self._buf = buf
        return msgs

    def send(self, message):
        """Send a message to the browser.

        *message* should be convertable to a string; unicode objects should be
        encodable as utf-8.  Raises socket.error with errno of 32
        (broken pipe) if the socket has already been closed by the client."""
        if self.version in ['7', '8', '13']:
            packed, lenhead, lentail = self.encode_hybi(message, opcode=0x01, base64=False)
        else:
            packed = self._pack_message(message)
        # if two greenthreads are trying to send at the same time
        # on the same socket, sendlock prevents interleaving and corruption
        #self._sendlock.acquire()
        try:
            self.socket.sendall(packed)
        finally:
            pass
            #self._sendlock.release()

    def wait(self):
        """Waits for and deserializes messages.

        Returns a single message; the oldest not yet processed. If the client
        has already closed the connection, returns None.  This is different
        from normal socket behavior because the empty string is a valid
        websocket message."""
        while not self._msgs:
            # Websocket might be closed already.
            if self.websocket_closed:
                return None
            # no parsed messages, must mean buf needs more data
            delta = self.socket.recv(8096)
            if delta == '':
                return None
            self._buf += delta
            msgs = self._parse_messages()
            self._msgs.extend(msgs)
        return self._msgs.popleft()

    def _send_closing_frame(self, ignore_send_errors=False):
        """Sends the closing frame to the client, if required."""
        if self.version in ['7', '8', '13'] and not self.websocket_closed:
            msg = ''
            #if code != None:
            #    msg = struct.pack(">H%ds" % (len(reason)), code)

            buf, h, t = self.encode_hybi(msg, opcode=0x08, base64=False)
            self.socket.sendall(buf)
            self.websocket_closed = True

        elif self.version == 76 and not self.websocket_closed:
            try:
                self.socket.sendall("\xff\x00")
            except SocketError:
                # Sometimes, like when the remote side cuts off the connection,
                # we don't care about this.
                if not ignore_send_errors: #pragma NO COVER
                    raise
            self.websocket_closed = True

    def close(self):
        """Forcibly close the websocket; generally it is preferable to
        return from the handler method."""
        self._send_closing_frame()
        self.socket.shutdown(True)
        self.socket.close()


# demo app
import os
import random
def handle(ws):
    """  This is the websocket handler function.  Note that we
    can dispatch based on path in here, too."""
    if ws.path == '/echo':
        while True:
            m = ws.wait()
            if m is None:
                break
            ws.send(m)

    elif ws.path == '/data':
        for i in xrange(10000):
            ws.send("0 %s %s\n" % (i, random.random()))
            gevent.sleep(0.1)

wsapp = WebSocketWSGI(handle)
def app(environ, start_response):
    """ This resolves to the web page or the websocket depending on
    the path."""
    if environ['PATH_INFO'] == '/' or environ['PATH_INFO'] == "":
        data = open(os.path.join(
                     os.path.dirname(__file__),
                     'websocket.html')).read()
        data = data % environ
        start_response('200 OK', [('Content-Type', 'text/html'),
                                 ('Content-Length', len(data))])
        return [data]
    else:
        return wsapp(environ, start_response)

########NEW FILE########
__FILENAME__ = websocket

import collections
import errno
import re
from hashlib import md5, sha1
import base64
from base64 import b64encode, b64decode
import socket
import struct
import logging
from socket import error as SocketError

import eventlet
from gunicorn.workers.async import ALREADY_HANDLED
from eventlet import pools

logger = logging.getLogger(__name__)

WS_KEY = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class WebSocketWSGI(object):
    def __init__(self, handler):
        self.handler = handler

    def verify_client(self, ws):
        pass

    def _get_key_value(self, key_value):
        if not key_value:
            return
        key_number = int(re.sub("\\D", "", key_value))
        spaces = re.subn(" ", "", key_value)[1]
        if key_number % spaces != 0:
            return
        part = key_number / spaces
        return part

    def __call__(self, environ, start_response):
        if not (environ.get('HTTP_CONNECTION').find('Upgrade') != -1 and
            environ['HTTP_UPGRADE'].lower() == 'websocket'):
            # need to check a few more things here for true compliance
            start_response('400 Bad Request', [('Connection','close')])
            return []

        sock = environ['gunicorn.socket']

        version = environ.get('HTTP_SEC_WEBSOCKET_VERSION')

        ws = WebSocket(sock, environ, version)

        handshake_reply = ("HTTP/1.1 101 Switching Protocols\r\n"
                   "Upgrade: websocket\r\n"
                   "Connection: Upgrade\r\n")

        key = environ.get('HTTP_SEC_WEBSOCKET_KEY')
        if key:
            ws_key = base64.b64decode(key)
            if len(ws_key) != 16:
                start_response('400 Bad Request', [('Connection','close')])
                return []

            protocols = []
            subprotocols = environ.get('HTTP_SEC_WEBSOCKET_PROTOCOL')
            ws_protocols = []
            if subprotocols:
                for s in subprotocols.split(','):
                    s = s.strip()
                    if s in protocols:
                        ws_protocols.append(s)
            if ws_protocols:
                handshake_reply += 'Sec-WebSocket-Protocol: %s\r\n' % ', '.join(ws_protocols)

            exts = []
            extensions = environ.get('HTTP_SEC_WEBSOCKET_EXTENSIONS')
            ws_extensions = []
            if extensions:
                for ext in extensions.split(','):
                    ext = ext.strip()
                    if ext in exts:
                        ws_extensions.append(ext)
            if ws_extensions:
                handshake_reply += 'Sec-WebSocket-Extensions: %s\r\n' % ', '.join(ws_extensions)

            handshake_reply +=  (
                "Sec-WebSocket-Origin: %s\r\n"
                "Sec-WebSocket-Location: ws://%s%s\r\n"
                "Sec-WebSocket-Version: %s\r\n"
                "Sec-WebSocket-Accept: %s\r\n\r\n"
                 % (
                    environ.get('HTTP_ORIGIN'), 
                    environ.get('HTTP_HOST'), 
                    ws.path,
                    version,
                    base64.b64encode(sha1(key + WS_KEY).digest())
                ))

        else:

            handshake_reply += (
                       "WebSocket-Origin: %s\r\n"
                       "WebSocket-Location: ws://%s%s\r\n\r\n" % (
                            environ.get('HTTP_ORIGIN'), 
                            environ.get('HTTP_HOST'), 
                            ws.path))

        sock.sendall(handshake_reply)

        try:
            self.handler(ws)
        except socket.error, e:
            if e[0] != errno.EPIPE:
                raise
        # use this undocumented feature of grainbows to ensure that it
        # doesn't barf on the fact that we didn't call start_response
        return ALREADY_HANDLED

class WebSocket(object):
    """A websocket object that handles the details of
    serialization/deserialization to the socket.

    The primary way to interact with a :class:`WebSocket` object is to
    call :meth:`send` and :meth:`wait` in order to pass messages back
    and forth with the browser.  Also available are the following
    properties:

    path
        The path value of the request.  This is the same as the WSGI PATH_INFO variable, but more convenient.
    protocol
        The value of the Websocket-Protocol header.
    origin
        The value of the 'Origin' header.
    environ
        The full WSGI environment for this request.

    """
    def __init__(self, sock, environ, version=76):
        """
        :param socket: The eventlet socket
        :type socket: :class:`eventlet.greenio.GreenSocket`
        :param environ: The wsgi environment
        :param version: The WebSocket spec version to follow (default is 76)
        """
        self.socket = sock
        self.origin = environ.get('HTTP_ORIGIN')
        self.protocol = environ.get('HTTP_WEBSOCKET_PROTOCOL')
        self.path = environ.get('PATH_INFO')
        self.environ = environ
        self.version = version
        self.websocket_closed = False
        self._buf = ""
        self._msgs = collections.deque()
        self._sendlock = pools.TokenPool(1)

    @staticmethod
    def encode_hybi(buf, opcode, base64=False):
        """ Encode a HyBi style WebSocket frame.
        Optional opcode:
            0x0 - continuation
            0x1 - text frame (base64 encode buf)
            0x2 - binary frame (use raw buf)
            0x8 - connection close
            0x9 - ping
            0xA - pong
        """
        if base64:
            buf = b64encode(buf)

        b1 = 0x80 | (opcode & 0x0f) # FIN + opcode
        payload_len = len(buf)
        if payload_len <= 125:
            header = struct.pack('>BB', b1, payload_len)
        elif payload_len > 125 and payload_len < 65536:
            header = struct.pack('>BBH', b1, 126, payload_len)
        elif payload_len >= 65536:
            header = struct.pack('>BBQ', b1, 127, payload_len)

        #print("Encoded: %s" % repr(header + buf))

        return header + buf, len(header), 0

    @staticmethod
    def decode_hybi(buf, base64=False):
        """ Decode HyBi style WebSocket packets.
        Returns:
            {'fin'          : 0_or_1,
             'opcode'       : number,
             'mask'         : 32_bit_number,
             'hlen'         : header_bytes_number,
             'length'       : payload_bytes_number,
             'payload'      : decoded_buffer,
             'left'         : bytes_left_number,
             'close_code'   : number,
             'close_reason' : string}
        """

        f = {'fin'          : 0,
             'opcode'       : 0,   
             'mask'         : 0,
             'hlen'         : 2,
             'length'       : 0,
             'payload'      : None,
             'left'         : 0,
             'close_code'   : None,
             'close_reason' : None}

        blen = len(buf)
        f['left'] = blen

        if blen < f['hlen']:
            return f # Incomplete frame header

        b1, b2 = struct.unpack_from(">BB", buf)
        f['opcode'] = b1 & 0x0f
        f['fin'] = (b1 & 0x80) >> 7
        has_mask = (b2 & 0x80) >> 7

        f['length'] = b2 & 0x7f

        if f['length'] == 126:
            f['hlen'] = 4
            if blen < f['hlen']:
                return f # Incomplete frame header
            (f['length'],) = struct.unpack_from('>xxH', buf)
        elif f['length'] == 127:
            f['hlen'] = 10
            if blen < f['hlen']:
                return f # Incomplete frame header
            (f['length'],) = struct.unpack_from('>xxQ', buf)

        full_len = f['hlen'] + has_mask * 4 + f['length']

        if blen < full_len: # Incomplete frame
            return f # Incomplete frame header

        # Number of bytes that are part of the next frame(s)
        f['left'] = blen - full_len

        # Process 1 frame
        if has_mask:
            # unmask payload
            f['mask'] = buf[f['hlen']:f['hlen']+4]
            b = c = ''
            if f['length'] >= 4:
                data = struct.unpack('<I', buf[f['hlen']:f['hlen']+4])[0]
                of1 = f['hlen']+4
                b = ''
                for i in xrange(0, int(f['length']/4)):
                    mask = struct.unpack('<I', buf[of1+4*i:of1+4*(i+1)])[0]
                    b += struct.pack('I', data ^ mask)

            if f['length'] % 4:
                l = f['length'] % 4
                of1 = f['hlen']
                of2 = full_len - l
                c = ''
                for i in range(0, l):
                    mask = struct.unpack('B', buf[of1 + i])[0]
                    data = struct.unpack('B', buf[of2 + i])[0]
                    c += chr(data ^ mask)

            f['payload'] = b + c
        else:
            print("Unmasked frame: %s" % repr(buf))
            f['payload'] = buf[(f['hlen'] + has_mask * 4):full_len]

        if base64 and f['opcode'] in [1, 2]:
            try:
                f['payload'] = b64decode(f['payload'])
            except:
                print("Exception while b64decoding buffer: %s" %
                        repr(buf))
                raise

        if f['opcode'] == 0x08:
            if f['length'] >= 2:
                f['close_code'] = struct.unpack_from(">H", f['payload'])
            if f['length'] > 3:
                f['close_reason'] = f['payload'][2:]

        return f


    @staticmethod
    def _pack_message(message):
        """Pack the message inside ``00`` and ``FF``

        As per the dataframing section (5.3) for the websocket spec
        """
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        elif not isinstance(message, str):
            message = str(message)
        packed = "\x00%s\xFF" % message
        return packed

    def _parse_messages(self):
        """ Parses for messages in the buffer *buf*.  It is assumed that
        the buffer contains the start character for a message, but that it
        may contain only part of the rest of the message.

        Returns an array of messages, and the buffer remainder that
        didn't contain any full messages."""
        msgs = []
        end_idx = 0
        buf = self._buf
        while buf:
            if self.version in ['7', '8', '13']:
                frame = self.decode_hybi(buf, base64=False)
                #print("Received buf: %s, frame: %s" % (repr(buf), frame))

                if frame['payload'] == None:
                    break
                else:
                    if frame['opcode'] == 0x8: # connection close
                        self.websocket_closed = True
                        break
                    #elif frame['opcode'] == 0x1:
                    else:
                        msgs.append(frame['payload']);
                        #msgs.append(frame['payload'].decode('utf-8', 'replace'));
                        #buf = buf[-frame['left']:]
                        if frame['left']:
                            buf = buf[-frame['left']:]
                        else:
                            buf = ''


            else:
                frame_type = ord(buf[0])
                if frame_type == 0:
                    # Normal message.
                    end_idx = buf.find("\xFF")
                    if end_idx == -1: #pragma NO COVER
                        break
                    msgs.append(buf[1:end_idx].decode('utf-8', 'replace'))
                    buf = buf[end_idx+1:]
                elif frame_type == 255:
                    # Closing handshake.
                    assert ord(buf[1]) == 0, "Unexpected closing handshake: %r" % buf
                    self.websocket_closed = True
                    break
                else:
                    raise ValueError("Don't understand how to parse this type of message: %r" % buf)
        self._buf = buf
        return msgs
    
    def send(self, message):
        """Send a message to the browser.  
        
        *message* should be convertable to a string; unicode objects should be
        encodable as utf-8.  Raises socket.error with errno of 32
        (broken pipe) if the socket has already been closed by the client."""
        if self.version in ['7', '8', '13']:
            packed, lenhead, lentail = self.encode_hybi(message, opcode=0x01, base64=False)
        else:
            packed = self._pack_message(message)
        # if two greenthreads are trying to send at the same time
        # on the same socket, sendlock prevents interleaving and corruption
        #self._sendlock.acquire()
        t = self._sendlock.get()
        try:
            self.socket.sendall(packed)
        finally:
            self._sendlock.put(t)

    def wait(self):
        """Waits for and deserializes messages. 
        
        Returns a single message; the oldest not yet processed. If the client
        has already closed the connection, returns None.  This is different
        from normal socket behavior because the empty string is a valid
        websocket message."""
        while not self._msgs:
            # Websocket might be closed already.
            if self.websocket_closed:
                return None
            # no parsed messages, must mean buf needs more data
            delta = self.socket.recv(8096)
            if delta == '':
                return None
            self._buf += delta
            msgs = self._parse_messages()
            self._msgs.extend(msgs)
        return self._msgs.popleft()

    def _send_closing_frame(self, ignore_send_errors=False):
        """Sends the closing frame to the client, if required."""
        if self.version in ['7', '8', '13'] and not self.websocket_closed:
            msg = ''
            #if code != None:
            #    msg = struct.pack(">H%ds" % (len(reason)), code)

            buf, h, t = self.encode_hybi(msg, opcode=0x08, base64=False)
            self.socket.sendall(buf)
            self.websocket_closed = True

        elif self.version == 76 and not self.websocket_closed:
            try:
                self.socket.sendall("\xff\x00")
            except SocketError:
                # Sometimes, like when the remote side cuts off the connection,
                # we don't care about this.
                if not ignore_send_errors: #pragma NO COVER
                    raise
            self.websocket_closed = True

    def close(self):
        """Forcibly close the websocket; generally it is preferable to
        return from the handler method."""
        self._send_closing_frame()
        self.socket.shutdown(True)
        self.socket.close()

# demo app
import os
import random
def handle(ws):
    """  This is the websocket handler function.  Note that we 
    can dispatch based on path in here, too."""
    if ws.path == '/echo':
        while True:
            m = ws.wait()
            if m is None:
                break
            ws.send(m)
            
    elif ws.path == '/data':
        for i in xrange(10000):
            ws.send("0 %s %s\n" % (i, random.random()))
            eventlet.sleep(0.1)
                            
wsapp = WebSocketWSGI(handle)
def app(environ, start_response):
    """ This resolves to the web page or the websocket depending on
    the path."""
    if environ['PATH_INFO'] == '/' or environ['PATH_INFO'] == "":
        data = open(os.path.join(
                     os.path.dirname(__file__), 
                     'websocket.html')).read()
        data = data % environ
        start_response('200 OK', [('Content-Type', 'text/html'),
                                 ('Content-Length', len(data))])
        return [data]
    else:
        return wsapp(environ, start_response)


########NEW FILE########
__FILENAME__ = when_ready.conf
import signal
import commands
import threading
import time

max_mem = 100000

class MemoryWatch(threading.Thread):
    
    def __init__(self, server, max_mem):
        super(MemoryWatch, self).__init__()
        self.daemon = True
        self.server = server
        self.max_mem = max_mem
        self.timeout = server.timeout / 2

    def memory_usage(self, pid):
        try:
            out = commands.getoutput("ps -o rss -p %s" % pid)
        except IOError:
            return -1
        used_mem = sum(int(x) for x in out.split('\n')[1:])
        return used_mem
    
        
    def run(self):
        while True:
            for (pid, worker) in list(self.server.WORKERS.items()):
                if self.memory_usage(pid) > self.max_mem:
                    self.server.log.info("Pid %s killed (memory usage > %s)", 
                        pid, self.max_mem)
                    self.server.kill_worker(pid, signal.SIGQUIT)
            time.sleep(self.timeout)
            

def when_ready(server):
    mw = MemoryWatch(server, max_mem)
    mw.start()

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import os
import sys
import traceback

from gunicorn import util
from gunicorn.arbiter import Arbiter
from gunicorn.config import Config, get_default_config_file
from gunicorn import debug
from gunicorn.six import execfile_

class BaseApplication(object):
    """
    An application interface for configuring and loading
    the various necessities for any given web framework.
    """
    def __init__(self, usage=None, prog=None):
        self.usage = usage
        self.cfg = None
        self.callable = None
        self.prog = prog
        self.logger = None
        self.do_load_config()

    def do_load_config(self):
        """
        Loads the configuration
        """
        try:
            self.load_default_config()
            self.load_config()
        except Exception as e:
            sys.stderr.write("\nError: %s\n" % str(e))
            sys.stderr.flush()
            sys.exit(1)

    def load_default_config(self):
        # init configuration
        self.cfg = Config(self.usage, prog=self.prog)

    def init(self, parser, opts, args):
        raise NotImplementedError

    def load(self):
        raise NotImplementedError

    def load_config(self):
        """
        This method is used to load the configuration from one or several input(s).
        Custom Command line, configuration file.
        You have to override this method in your class.
        """
        raise NotImplementedError

    def reload(self):
        self.do_load_config()
        if self.cfg.spew:
            debug.spew()

    def wsgi(self):
        if self.callable is None:
            self.callable = self.load()
        return self.callable

    def run(self):
        try:
            Arbiter(self).run()
        except RuntimeError as e:
            sys.stderr.write("\nError: %s\n\n" % e)
            sys.stderr.flush()
            sys.exit(1)

class Application(BaseApplication):
    def load_config_from_file(self, filename):
        """
        Loads the configuration file: the file is a python file, otherwise raise an RuntimeError
        Exception or stop the process if the configuration file contains a syntax error.
        """
        if not os.path.exists(filename):
            raise RuntimeError("%r doesn't exist" % filename)

        cfg = {
            "__builtins__": __builtins__,
            "__name__": "__config__",
            "__file__": filename,
            "__doc__": None,
            "__package__": None
        }
        try:
            execfile_(filename, cfg, cfg)
        except Exception:
            print("Failed to read config file: %s" % filename)
            traceback.print_exc()
            sys.exit(1)

        for k, v in cfg.items():
            # Ignore unknown names
            if k not in self.cfg.settings:
                continue
            try:
                self.cfg.set(k.lower(), v)
            except:
                sys.stderr.write("Invalid value for %s: %s\n\n" % (k, v))
                raise

        return cfg

    def load_config(self):
        # parse console args
        parser = self.cfg.parser()
        args = parser.parse_args()

        # optional settings from apps
        cfg = self.init(parser, args, args.args)

        # Load up the any app specific configuration
        if cfg and cfg is not None:
            for k, v in cfg.items():
                self.cfg.set(k.lower(), v)

        if args.config:
            self.load_config_from_file(args.config)
        else:
            default_config = get_default_config_file()
            if default_config is not None:
                self.load_config_from_file(default_config)

        # Lastly, update the configuration with any command line
        # settings.
        for k, v in args.__dict__.items():
            if v is None:
                continue
            if k == "args":
                continue
            self.cfg.set(k.lower(), v)

    def run(self):
        if self.cfg.check_config:
            try:
                self.load()
            except:
                sys.stderr.write("\nError while loading the application:\n\n")
                traceback.print_exc()
                sys.stderr.flush()
                sys.exit(1)
            sys.exit(0)

        if self.cfg.spew:
            debug.spew()

        if self.cfg.daemon:
            util.daemonize(self.cfg.enable_stdio_inheritance)

        # set python paths
        if self.cfg.pythonpath and self.cfg.pythonpath is not None:
            paths = self.cfg.pythonpath.split(",")
            for path in paths:
                pythonpath = os.path.abspath(path)
                if pythonpath not in sys.path:
                    sys.path.insert(0, pythonpath)

        super(Application, self).run()

########NEW FILE########
__FILENAME__ = djangoapp
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import os
import sys

from gunicorn.app.base import Application
from gunicorn import util


def is_setting_mod(path):
    return (os.path.isfile(os.path.join(path, "settings.py")) or
            os.path.isfile(os.path.join(path, "settings.pyc")))


def find_settings_module(path):
    path = os.path.abspath(path)
    project_path = None
    settings_name = "settings"

    if os.path.isdir(path):
        project_path = None
        if not is_setting_mod(path):
            for d in os.listdir(path):
                if d in ('..', '.'):
                    continue

                root = os.path.join(path, d)
                if is_setting_mod(root):
                    project_path = root
                    break
        else:
            project_path = path
    elif os.path.isfile(path):
        project_path = os.path.dirname(path)
        settings_name, _ = os.path.splitext(os.path.basename(path))

    return project_path, settings_name


def make_default_env(cfg):
    if cfg.django_settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = cfg.django_settings

    if cfg.pythonpath and cfg.pythonpath is not None:
        paths = cfg.pythonpath.split(",")
        for path in paths:
            pythonpath = os.path.abspath(cfg.pythonpath)
            if pythonpath not in sys.path:
                sys.path.insert(0, pythonpath)

    try:
        os.environ['DJANGO_SETTINGS_MODULE']
    except KeyError:
        # not settings env set, try to build one.
        cwd = util.getcwd()
        project_path, settings_name = find_settings_module(cwd)

        if not project_path:
            raise RuntimeError("django project not found")

        pythonpath, project_name = os.path.split(project_path)
        os.environ['DJANGO_SETTINGS_MODULE'] = "%s.%s" % (project_name,
                settings_name)
        if pythonpath not in sys.path:
            sys.path.insert(0, pythonpath)

        if project_path not in sys.path:
            sys.path.insert(0, project_path)


class DjangoApplication(Application):

    def init(self, parser, opts, args):
        if args:
            if ("." in args[0] and not (os.path.isfile(args[0])
                    or os.path.isdir(args[0]))):
                self.cfg.set("django_settings", args[0])
            else:
                # not settings env set, try to build one.
                project_path, settings_name = find_settings_module(
                        os.path.abspath(args[0]))
                if project_path not in sys.path:
                    sys.path.insert(0, project_path)

                if not project_path:
                    raise RuntimeError("django project not found")

                pythonpath, project_name = os.path.split(project_path)
                self.cfg.set("django_settings", "%s.%s" % (project_name,
                        settings_name))
                self.cfg.set("pythonpath", pythonpath)

    def load(self):
        # chdir to the configured path before loading,
        # default is the current dir
        os.chdir(self.cfg.chdir)

        # set settings
        make_default_env(self.cfg)

        # load wsgi application and return it.
        mod = util.import_module("gunicorn.app.django_wsgi")
        return mod.make_wsgi_application()


class DjangoApplicationCommand(Application):

    def __init__(self, options, admin_media_path):
        self.usage = None
        self.prog = None
        self.cfg = None
        self.config_file = options.get("config") or ""
        self.options = options
        self.admin_media_path = admin_media_path
        self.callable = None
        self.project_path = None
        self.do_load_config()

    def init(self, *args):
        if 'settings' in self.options:
            self.options['django_settings'] = self.options.pop('settings')

        cfg = {}
        for k, v in self.options.items():
            if k.lower() in self.cfg.settings and v is not None:
                cfg[k.lower()] = v
        return cfg

    def load(self):
        # chdir to the configured path before loading,
        # default is the current dir
        os.chdir(self.cfg.chdir)

        # set settings
        make_default_env(self.cfg)

        # load wsgi application and return it.
        mod = util.import_module("gunicorn.app.django_wsgi")
        return mod.make_command_wsgi_application(self.admin_media_path)


def run():
    """\
    The ``gunicorn_django`` command line runner for launching Django
    applications.
    """
    util.warn("""This command is deprecated.

    You should now run your application with the WSGI interface
    installed with your project. Ex.:

        gunicorn myproject.wsgi:application

    See https://docs.djangoproject.com/en/1.5/howto/deployment/wsgi/gunicorn/
    for more info.""")
    from gunicorn.app.djangoapp import DjangoApplication
    DjangoApplication("%(prog)s [OPTIONS] [SETTINGS_PATH]").run()

########NEW FILE########
__FILENAME__ = django_wsgi
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

""" module used to build the django wsgi application """

import os
import re
import sys
import time
try:
    from StringIO import StringIO
except:
    from io import StringIO
    from imp import reload


from django.conf import settings
from django.core.management.validation import get_validation_errors
from django.utils import translation

try:
    from django.core.servers.basehttp import get_internal_wsgi_application
    django14 = True
except ImportError:
    from django.core.handlers.wsgi import WSGIHandler
    django14 = False

from gunicorn import util


def make_wsgi_application():
    # validate models
    s = StringIO()
    if get_validation_errors(s):
        s.seek(0)
        error = s.read()
        sys.stderr.write("One or more models did not validate:\n%s" % error)
        sys.stderr.flush()

        sys.exit(1)

    translation.activate(settings.LANGUAGE_CODE)
    if django14:
        return get_internal_wsgi_application()
    return WSGIHandler()


def reload_django_settings():
        mod = util.import_module(os.environ['DJANGO_SETTINGS_MODULE'])

        # reload module
        reload(mod)

        # reload settings.
        # USe code from django.settings.Settings module.

        # Settings that should be converted into tuples if they're mistakenly entered
        # as strings.
        tuple_settings = ("INSTALLED_APPS", "TEMPLATE_DIRS")

        for setting in dir(mod):
            if setting == setting.upper():
                setting_value = getattr(mod, setting)
                if setting in tuple_settings and type(setting_value) == str:
                    setting_value = (setting_value,)  # In case the user forgot the comma.
                setattr(settings, setting, setting_value)

        # Expand entries in INSTALLED_APPS like "django.contrib.*" to a list
        # of all those apps.
        new_installed_apps = []
        for app in settings.INSTALLED_APPS:
            if app.endswith('.*'):
                app_mod = util.import_module(app[:-2])
                appdir = os.path.dirname(app_mod.__file__)
                app_subdirs = os.listdir(appdir)
                name_pattern = re.compile(r'[a-zA-Z]\w*')
                for d in sorted(app_subdirs):
                    if (name_pattern.match(d) and
                            os.path.isdir(os.path.join(appdir, d))):
                        new_installed_apps.append('%s.%s' % (app[:-2], d))
            else:
                new_installed_apps.append(app)
        setattr(settings, "INSTALLED_APPS", new_installed_apps)

        if hasattr(time, 'tzset') and settings.TIME_ZONE:
            # When we can, attempt to validate the timezone. If we can't find
            # this file, no check happens and it's harmless.
            zoneinfo_root = '/usr/share/zoneinfo'
            if (os.path.exists(zoneinfo_root) and not
                    os.path.exists(os.path.join(zoneinfo_root,
                        *(settings.TIME_ZONE.split('/'))))):
                raise ValueError("Incorrect timezone setting: %s" %
                        settings.TIME_ZONE)
            # Move the time zone info into os.environ. See ticket #2315 for why
            # we don't do this unconditionally (breaks Windows).
            os.environ['TZ'] = settings.TIME_ZONE
            time.tzset()

        # Settings are configured, so we can set up the logger if required
        if getattr(settings, 'LOGGING_CONFIG', False):
            # First find the logging configuration function ...
            logging_config_path, logging_config_func_name = settings.LOGGING_CONFIG.rsplit('.', 1)
            logging_config_module = util.import_module(logging_config_path)
            logging_config_func = getattr(logging_config_module, logging_config_func_name)

            # ... then invoke it with the logging settings
            logging_config_func(settings.LOGGING)


def make_command_wsgi_application(admin_mediapath):
    reload_django_settings()

    try:
        from django.core.servers.basehttp import AdminMediaHandler
        return AdminMediaHandler(make_wsgi_application(), admin_mediapath)
    except ImportError:
        return make_wsgi_application()

########NEW FILE########
__FILENAME__ = pasterapp
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import os
import pkg_resources
import sys

try:
    import configparser as ConfigParser
except ImportError:
    import ConfigParser

from paste.deploy import loadapp, loadwsgi
SERVER = loadwsgi.SERVER

from gunicorn.app.base import Application
from gunicorn.config import Config, get_default_config_file
from gunicorn import util


def paste_config(gconfig, config_url, relative_to, global_conf=None):
    # add entry to pkg_resources
    sys.path.insert(0, relative_to)
    pkg_resources.working_set.add_entry(relative_to)

    config_url = config_url.split('#')[0]
    cx = loadwsgi.loadcontext(SERVER, config_url, relative_to=relative_to,
            global_conf=global_conf)
    gc, lc = cx.global_conf.copy(), cx.local_conf.copy()
    cfg = {}

    host, port = lc.pop('host', ''), lc.pop('port', '')
    if host and port:
        cfg['bind'] = '%s:%s' % (host, port)
    elif host:
        cfg['bind'] = host.split(',')

    cfg['workers'] = int(lc.get('workers', 1))
    cfg['umask'] = int(lc.get('umask', 0))
    cfg['default_proc_name'] = gc.get('__file__')

    for k, v in gc.items():
        if k not in gconfig.settings:
            continue
        cfg[k] = v

    for k, v in lc.items():
        if k not in gconfig.settings:
            continue
        cfg[k] = v

    return cfg


def load_pasteapp(config_url, relative_to, global_conf=None):
    return loadapp(config_url, relative_to=relative_to,
            global_conf=global_conf)

class PasterBaseApplication(Application):
    gcfg = None

    def app_config(self):
        return paste_config(self.cfg, self.cfgurl, self.relpath,
                global_conf=self.gcfg)

    def load_config(self):
        super(PasterBaseApplication, self).load_config()

        # reload logging conf
        if hasattr(self, "cfgfname"):
            parser = ConfigParser.ConfigParser()
            parser.read([self.cfgfname])
            if parser.has_section('loggers'):
                from logging.config import fileConfig
                config_file = os.path.abspath(self.cfgfname)
                fileConfig(config_file, dict(__file__=config_file,
                                             here=os.path.dirname(config_file)))


class PasterApplication(PasterBaseApplication):

    def init(self, parser, opts, args):
        if len(args) != 1:
            parser.error("No application name specified.")

        cwd = util.getcwd()
        cfgfname = os.path.normpath(os.path.join(cwd, args[0]))
        cfgfname = os.path.abspath(cfgfname)
        if not os.path.exists(cfgfname):
            parser.error("Config file not found: %s" % cfgfname)

        self.cfgurl = 'config:%s' % cfgfname
        self.relpath = os.path.dirname(cfgfname)
        self.cfgfname = cfgfname

        sys.path.insert(0, self.relpath)
        pkg_resources.working_set.add_entry(self.relpath)

        return self.app_config()

    def load(self):
        # chdir to the configured path before loading,
        # default is the current dir
        os.chdir(self.cfg.chdir)

        return load_pasteapp(self.cfgurl, self.relpath, global_conf=self.gcfg)


class PasterServerApplication(PasterBaseApplication):

    def __init__(self, app, gcfg=None, host="127.0.0.1", port=None, *args, **kwargs):
        self.cfg = Config()
        self.gcfg = gcfg # need to hold this for app_config
        self.app = app
        self.callable = None

        gcfg = gcfg or {}
        cfgfname = gcfg.get("__file__")
        if cfgfname is not None:
            self.cfgurl = 'config:%s' % cfgfname
            self.relpath = os.path.dirname(cfgfname)
            self.cfgfname = cfgfname

        cfg = kwargs.copy()

        if port and not host.startswith("unix:"):
            bind = "%s:%s" % (host, port)
        else:
            bind = host
        cfg["bind"] = bind.split(',')

        if gcfg:
            for k, v in gcfg.items():
                cfg[k] = v
            cfg["default_proc_name"] = cfg['__file__']

        try:
            for k, v in cfg.items():
                if k.lower() in self.cfg.settings and v is not None:
                    self.cfg.set(k.lower(), v)
        except Exception as e:
            sys.stderr.write("\nConfig error: %s\n" % str(e))
            sys.stderr.flush()
            sys.exit(1)

        if cfg.get("config"):
            self.load_config_from_file(cfg["config"])
        else:
            default_config = get_default_config_file()
            if default_config is not None:
                self.load_config_from_file(default_config)

    def load(self):
        # chdir to the configured path before loading,
        # default is the current dir
        os.chdir(self.cfg.chdir)

        return self.app


def run():
    """\
    The ``gunicorn_paster`` command for launching Paster compatible
    applications like Pylons or Turbogears2
    """
    util.warn("""This command is deprecated.

    You should now use the `--paste` option. Ex.:

        gunicorn --paste development.ini
    """)

    from gunicorn.app.pasterapp import PasterApplication
    PasterApplication("%(prog)s [OPTIONS] pasteconfig.ini").run()


def paste_server(app, gcfg=None, host="127.0.0.1", port=None, *args, **kwargs):
    """\
    A paster server.

    Then entry point in your paster ini file should looks like this:

    [server:main]
    use = egg:gunicorn#main
    host = 127.0.0.1
    port = 5000

    """

    util.warn("""This command is deprecated.

    You should now use the `--paste` option. Ex.:

        gunicorn --paste development.ini
    """)

    from gunicorn.app.pasterapp import PasterServerApplication
    PasterServerApplication(app, gcfg=gcfg, host=host, port=port, *args, **kwargs).run()

########NEW FILE########
__FILENAME__ = wsgiapp
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import os
import sys

from gunicorn.errors import ConfigError
from gunicorn.app.base import Application
from gunicorn import util


class WSGIApplication(Application):
    def init(self, parser, opts, args):
        if opts.paste and opts.paste is not None:
            app_name = 'main'
            path = opts.paste
            if '#' in path:
                path, app_name = path.split('#')
            path = os.path.abspath(os.path.normpath(
                os.path.join(util.getcwd(), path)))

            if not os.path.exists(path):
                raise ConfigError("%r not found" % path)

            # paste application, load the config
            self.cfgurl = 'config:%s#%s' % (path, app_name)
            self.relpath = os.path.dirname(path)

            from .pasterapp import paste_config
            return paste_config(self.cfg, self.cfgurl, self.relpath)

        if len(args) != 1:
            parser.error("No application module specified.")

        self.cfg.set("default_proc_name", args[0])
        self.app_uri = args[0]

    def chdir(self):
        # chdir to the configured path before loading,
        # default is the current dir
        os.chdir(self.cfg.chdir)

        # add the path to sys.path
        sys.path.insert(0, self.cfg.chdir)

    def load_wsgiapp(self):
        self.chdir()

        # load the app
        return util.import_app(self.app_uri)

    def load_pasteapp(self):
        self.chdir()

        # load the paste app
        from .pasterapp import load_pasteapp
        return load_pasteapp(self.cfgurl, self.relpath, global_conf=None)

    def load(self):
        if self.cfg.paste is not None:
            return self.load_pasteapp()
        else:
            return self.load_wsgiapp()


def run():
    """\
    The ``gunicorn`` command line runner for launching Gunicorn with
    generic WSGI applications.
    """
    from gunicorn.app.wsgiapp import WSGIApplication
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()


if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = arbiter
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import errno
import os
import random
import select
import signal
import sys
import time
import traceback

from gunicorn.errors import HaltServer, AppImportError
from gunicorn.pidfile import Pidfile
from gunicorn.sock import create_sockets
from gunicorn import util

from gunicorn import __version__, SERVER_SOFTWARE


class Arbiter(object):
    """
    Arbiter maintain the workers processes alive. It launches or
    kills them if needed. It also manages application reloading
    via SIGHUP/USR2.
    """

    # A flag indicating if a worker failed to
    # to boot. If a worker process exist with
    # this error code, the arbiter will terminate.
    WORKER_BOOT_ERROR = 3

    # A flag indicating if an application failed to be loaded
    APP_LOAD_ERROR = 4

    START_CTX = {}

    LISTENERS = []
    WORKERS = {}
    PIPE = []

    # I love dynamic languages
    SIG_QUEUE = []
    SIGNALS = [getattr(signal, "SIG%s" % x) \
            for x in "HUP QUIT INT TERM TTIN TTOU USR1 USR2 WINCH".split()]
    SIG_NAMES = dict(
        (getattr(signal, name), name[3:].lower()) for name in dir(signal)
        if name[:3] == "SIG" and name[3] != "_"
    )

    def __init__(self, app):
        os.environ["SERVER_SOFTWARE"] = SERVER_SOFTWARE

        self._num_workers = None
        self.setup(app)

        self.pidfile = None
        self.worker_age = 0
        self.reexec_pid = 0
        self.master_name = "Master"

        cwd = util.getcwd()

        args = sys.argv[:]
        args.insert(0, sys.executable)

        # init start context
        self.START_CTX = {
            "args": args,
            "cwd": cwd,
            0: sys.executable
        }

    def _get_num_workers(self):
        return self._num_workers

    def _set_num_workers(self, value):
        old_value = self._num_workers
        self._num_workers = value
        self.cfg.nworkers_changed(self, value, old_value)
    num_workers = property(_get_num_workers, _set_num_workers)

    def setup(self, app):
        self.app = app
        self.cfg = app.cfg
        self.log = self.cfg.logger_class(app.cfg)

        # reopen files
        if 'GUNICORN_FD' in os.environ:
            self.log.reopen_files()

        self.worker_class = self.cfg.worker_class
        self.address = self.cfg.address
        self.num_workers = self.cfg.workers
        self.timeout = self.cfg.timeout
        self.proc_name = self.cfg.proc_name

        self.log.debug('Current configuration:\n{0}'.format(
            '\n'.join(
                '  {0}: {1}'.format(config, value.value)
                for config, value
                in sorted(self.cfg.settings.items(),
                          key=lambda setting: setting[1]))))

        # set enviroment' variables
        if self.cfg.env:
            for k, v in self.cfg.env.items():
                os.environ[k] = v

        if self.cfg.preload_app:
            self.app.wsgi()

    def start(self):
        """\
        Initialize the arbiter. Start listening and set pidfile if needed.
        """
        self.log.info("Starting gunicorn %s", __version__)

        self.pid = os.getpid()
        if self.cfg.pidfile is not None:
            self.pidfile = Pidfile(self.cfg.pidfile)
            self.pidfile.create(self.pid)
        self.cfg.on_starting(self)

        self.init_signals()
        if not self.LISTENERS:
            self.LISTENERS = create_sockets(self.cfg, self.log)

        listeners_str = ",".join([str(l) for l in self.LISTENERS])
        self.log.debug("Arbiter booted")
        self.log.info("Listening at: %s (%s)", listeners_str, self.pid)
        self.log.info("Using worker: %s",
                self.cfg.settings['worker_class'].get())

        self.cfg.when_ready(self)

    def init_signals(self):
        """\
        Initialize master signal handling. Most of the signals
        are queued. Child signals only wake up the master.
        """
        # close old PIPE
        if self.PIPE:
            [os.close(p) for p in self.PIPE]

        # initialize the pipe
        self.PIPE = pair = os.pipe()
        for p in pair:
            util.set_non_blocking(p)
            util.close_on_exec(p)

        self.log.close_on_exec()

        # initialize all signals
        [signal.signal(s, self.signal) for s in self.SIGNALS]
        signal.signal(signal.SIGCHLD, self.handle_chld)

    def signal(self, sig, frame):
        if len(self.SIG_QUEUE) < 5:
            self.SIG_QUEUE.append(sig)
            self.wakeup()

    def run(self):
        "Main master loop."
        self.start()
        util._setproctitle("master [%s]" % self.proc_name)

        self.manage_workers()
        while True:
            try:
                sig = self.SIG_QUEUE.pop(0) if len(self.SIG_QUEUE) else None
                if sig is None:
                    self.sleep()
                    self.murder_workers()
                    self.manage_workers()
                    continue

                if sig not in self.SIG_NAMES:
                    self.log.info("Ignoring unknown signal: %s", sig)
                    continue

                signame = self.SIG_NAMES.get(sig)
                handler = getattr(self, "handle_%s" % signame, None)
                if not handler:
                    self.log.error("Unhandled signal: %s", signame)
                    continue
                self.log.info("Handling signal: %s", signame)
                handler()
                self.wakeup()
            except StopIteration:
                self.halt()
            except KeyboardInterrupt:
                self.halt()
            except HaltServer as inst:
                self.halt(reason=inst.reason, exit_status=inst.exit_status)
            except SystemExit:
                raise
            except Exception:
                self.log.info("Unhandled exception in main loop:\n%s",
                            traceback.format_exc())
                self.stop(False)
                if self.pidfile is not None:
                    self.pidfile.unlink()
                sys.exit(-1)

    def handle_chld(self, sig, frame):
        "SIGCHLD handling"
        self.reap_workers()
        self.wakeup()

    def handle_hup(self):
        """\
        HUP handling.
        - Reload configuration
        - Start the new worker processes with a new configuration
        - Gracefully shutdown the old worker processes
        """
        self.log.info("Hang up: %s", self.master_name)
        self.reload()

    def handle_term(self):
        "SIGTERM handling"
        raise StopIteration

    def handle_int(self):
        "SIGINT handling"
        self.stop(False)
        raise StopIteration

    def handle_quit(self):
        "SIGTERM handling"
        self.stop(False)
        raise StopIteration

    def handle_ttin(self):
        """\
        SIGTTIN handling.
        Increases the number of workers by one.
        """
        self.num_workers += 1
        self.manage_workers()

    def handle_ttou(self):
        """\
        SIGTTOU handling.
        Decreases the number of workers by one.
        """
        if self.num_workers <= 1:
            return
        self.num_workers -= 1
        self.manage_workers()

    def handle_usr1(self):
        """\
        SIGUSR1 handling.
        Kill all workers by sending them a SIGUSR1
        """
        self.kill_workers(signal.SIGUSR1)
        self.log.reopen_files()

    def handle_usr2(self):
        """\
        SIGUSR2 handling.
        Creates a new master/worker set as a slave of the current
        master without affecting old workers. Use this to do live
        deployment with the ability to backout a change.
        """
        self.reexec()

    def handle_winch(self):
        "SIGWINCH handling"
        if self.cfg.daemon:
            self.log.info("graceful stop of workers")
            self.num_workers = 0
            self.kill_workers(signal.SIGQUIT)
        else:
            self.log.debug("SIGWINCH ignored. Not daemonized")

    def wakeup(self):
        """\
        Wake up the arbiter by writing to the PIPE
        """
        try:
            os.write(self.PIPE[1], b'.')
        except IOError as e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise

    def halt(self, reason=None, exit_status=0):
        """ halt arbiter """
        self.stop()
        self.log.info("Shutting down: %s", self.master_name)
        if reason is not None:
            self.log.info("Reason: %s", reason)
        if self.pidfile is not None:
            self.pidfile.unlink()
        sys.exit(exit_status)

    def sleep(self):
        """\
        Sleep until PIPE is readable or we timeout.
        A readable PIPE means a signal occurred.
        """
        if self.WORKERS:
            worker_values = list(self.WORKERS.values())
            oldest = min(w.tmp.last_update() for w in worker_values)
            timeout = self.timeout - (time.time() - oldest)
            # The timeout can be reached, so don't wait for a negative value
            timeout = max(timeout, 1.0)
        else:
            timeout = 1.0
        try:
            ready = select.select([self.PIPE[0]], [], [], timeout)
            if not ready[0]:
                return
            while os.read(self.PIPE[0], 1):
                pass
        except select.error as e:
            if e.args[0] not in [errno.EAGAIN, errno.EINTR]:
                raise
        except OSError as e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise
        except KeyboardInterrupt:
            sys.exit()

    def stop(self, graceful=True):
        """\
        Stop workers

        :attr graceful: boolean, If True (the default) workers will be
        killed gracefully  (ie. trying to wait for the current connection)
        """
        self.LISTENERS = []
        sig = signal.SIGTERM
        if not graceful:
            sig = signal.SIGQUIT
        limit = time.time() + self.cfg.graceful_timeout
        while self.WORKERS and time.time() < limit:
            self.kill_workers(sig)
            time.sleep(0.1)
        self.kill_workers(signal.SIGKILL)

    def reexec(self):
        """\
        Relaunch the master and workers.
        """
        if self.pidfile is not None:
            self.pidfile.rename("%s.oldbin" % self.pidfile.fname)

        self.reexec_pid = os.fork()
        if self.reexec_pid != 0:
            self.master_name = "Old Master"
            return

        environ = self.cfg.env_orig.copy()
        fds = [l.fileno() for l in self.LISTENERS]
        environ['GUNICORN_FD'] = ",".join([str(fd) for fd in fds])

        os.chdir(self.START_CTX['cwd'])
        self.cfg.pre_exec(self)

        # exec the process using the original environnement
        os.execvpe(self.START_CTX[0], self.START_CTX['args'], environ)

    def reload(self):
        old_address = self.cfg.address

        # reset old environement
        for k in self.cfg.env:
            if k in self.cfg.env_orig:
                # reset the key to the value it had before
                # we launched gunicorn
                os.environ[k] = self.cfg.env_orig[k]
            else:
                # delete the value set by gunicorn
                try:
                    del os.environ[k]
                except KeyError:
                    pass

        # reload conf
        self.app.reload()
        self.setup(self.app)

        # reopen log files
        self.log.reopen_files()

        # do we need to change listener ?
        if old_address != self.cfg.address:
            # close all listeners
            [l.close() for l in self.LISTENERS]
            # init new listeners
            self.LISTENERS = create_sockets(self.cfg, self.log)
            self.log.info("Listening at: %s", ",".join(str(self.LISTENERS)))

        # do some actions on reload
        self.cfg.on_reload(self)

        # unlink pidfile
        if self.pidfile is not None:
            self.pidfile.unlink()

        # create new pidfile
        if self.cfg.pidfile is not None:
            self.pidfile = Pidfile(self.cfg.pidfile)
            self.pidfile.create(self.pid)

        # set new proc_name
        util._setproctitle("master [%s]" % self.proc_name)

        # spawn new workers
        for i in range(self.cfg.workers):
            self.spawn_worker()

        # manage workers
        self.manage_workers()

    def murder_workers(self):
        """\
        Kill unused/idle workers
        """
        if not self.timeout:
            return
        workers = list(self.WORKERS.items())
        for (pid, worker) in workers:
            try:
                if time.time() - worker.tmp.last_update() <= self.timeout:
                    continue
            except ValueError:
                continue

            self.log.critical("WORKER TIMEOUT (pid:%s)", pid)
            self.kill_worker(pid, signal.SIGKILL)

    def reap_workers(self):
        """\
        Reap workers to avoid zombie processes
        """
        try:
            while True:
                wpid, status = os.waitpid(-1, os.WNOHANG)
                if not wpid:
                    break
                if self.reexec_pid == wpid:
                    self.reexec_pid = 0
                else:
                    # A worker said it cannot boot. We'll shutdown
                    # to avoid infinite start/stop cycles.
                    exitcode = status >> 8
                    if exitcode == self.WORKER_BOOT_ERROR:
                        reason = "Worker failed to boot."
                        raise HaltServer(reason, self.WORKER_BOOT_ERROR)
                    if exitcode == self.APP_LOAD_ERROR:
                        reason = "App failed to load."
                        raise HaltServer(reason, self.APP_LOAD_ERROR)
                    worker = self.WORKERS.pop(wpid, None)
                    if not worker:
                        continue
                    worker.tmp.close()
        except OSError as e:
            if e.errno != errno.ECHILD:
                raise

    def manage_workers(self):
        """\
        Maintain the number of workers by spawning or killing
        as required.
        """
        if len(self.WORKERS.keys()) < self.num_workers:
            self.spawn_workers()

        workers = self.WORKERS.items()
        workers = sorted(workers, key=lambda w: w[1].age)
        while len(workers) > self.num_workers:
            (pid, _) = workers.pop(0)
            self.kill_worker(pid, signal.SIGQUIT)

    def spawn_worker(self):
        self.worker_age += 1
        worker = self.worker_class(self.worker_age, self.pid, self.LISTENERS,
                                    self.app, self.timeout / 2.0,
                                    self.cfg, self.log)
        self.cfg.pre_fork(self, worker)
        pid = os.fork()
        if pid != 0:
            self.WORKERS[pid] = worker
            return pid

        # Process Child
        worker_pid = os.getpid()
        try:
            util._setproctitle("worker [%s]" % self.proc_name)
            self.log.info("Booting worker with pid: %s", worker_pid)
            self.cfg.post_fork(self, worker)
            worker.init_process()
            sys.exit(0)
        except SystemExit:
            raise
        except AppImportError as e:
            self.log.debug("Exception while loading the application: \n%s",
                    traceback.format_exc())

            sys.stderr.write("%s\n" % e)
            sys.stderr.flush()
            sys.exit(self.APP_LOAD_ERROR)
        except:
            self.log.exception("Exception in worker process:\n%s",
                    traceback.format_exc())
            if not worker.booted:
                sys.exit(self.WORKER_BOOT_ERROR)
            sys.exit(-1)
        finally:
            self.log.info("Worker exiting (pid: %s)", worker_pid)
            try:
                worker.tmp.close()
                self.cfg.worker_exit(self, worker)
            except:
                pass

    def spawn_workers(self):
        """\
        Spawn new workers as needed.

        This is where a worker process leaves the main loop
        of the master process.
        """

        for i in range(self.num_workers - len(self.WORKERS.keys())):
            self.spawn_worker()
            time.sleep(0.1 * random.random())

    def kill_workers(self, sig):
        """\
        Kill all workers with the signal `sig`
        :attr sig: `signal.SIG*` value
        """
        worker_pids = list(self.WORKERS.keys())
        for pid in worker_pids:
            self.kill_worker(pid, sig)

    def kill_worker(self, pid, sig):
        """\
        Kill a worker

        :attr pid: int, worker pid
        :attr sig: `signal.SIG*` value
         """
        try:
            os.kill(pid, sig)
        except OSError as e:
            if e.errno == errno.ESRCH:
                try:
                    worker = self.WORKERS.pop(pid)
                    worker.tmp.close()
                    self.cfg.worker_exit(self, worker)
                    return
                except (KeyError, OSError):
                    return
            raise

########NEW FILE########
__FILENAME__ = argparse_compat
# Author: Steven J. Bethard <steven.bethard@gmail.com>.

"""Command-line parsing library

This module is an optparse-inspired command-line parsing library that:

    - handles both optional and positional arguments
    - produces highly informative usage messages
    - supports parsers that dispatch to sub-parsers

The following is a simple usage example that sums integers from the
command-line and writes the result to a file::

    parser = argparse.ArgumentParser(
        description='sum the integers at the command line')
    parser.add_argument(
        'integers', metavar='int', nargs='+', type=int,
        help='an integer to be summed')
    parser.add_argument(
        '--log', default=sys.stdout, type=argparse.FileType('w'),
        help='the file where the sum should be written')
    args = parser.parse_args()
    args.log.write('%s' % sum(args.integers))
    args.log.close()

The module contains the following public classes:

    - ArgumentParser -- The main entry point for command-line parsing. As the
        example above shows, the add_argument() method is used to populate
        the parser with actions for optional and positional arguments. Then
        the parse_args() method is invoked to convert the args at the
        command-line into an object with attributes.

    - ArgumentError -- The exception raised by ArgumentParser objects when
        there are errors with the parser's actions. Errors raised while
        parsing the command-line are caught by ArgumentParser and emitted
        as command-line messages.

    - FileType -- A factory for defining types of files to be created. As the
        example above shows, instances of FileType are typically passed as
        the type= argument of add_argument() calls.

    - Action -- The base class for parser actions. Typically actions are
        selected by passing strings like 'store_true' or 'append_const' to
        the action= argument of add_argument(). However, for greater
        customization of ArgumentParser actions, subclasses of Action may
        be defined and passed as the action= argument.

    - HelpFormatter, RawDescriptionHelpFormatter, RawTextHelpFormatter,
        ArgumentDefaultsHelpFormatter -- Formatter classes which
        may be passed as the formatter_class= argument to the
        ArgumentParser constructor. HelpFormatter is the default,
        RawDescriptionHelpFormatter and RawTextHelpFormatter tell the parser
        not to change the formatting for help text, and
        ArgumentDefaultsHelpFormatter adds information about argument defaults
        to the help.

All other classes in this module are considered implementation details.
(Also note that HelpFormatter and RawDescriptionHelpFormatter are only
considered public as object names -- the API of the formatter objects is
still considered an implementation detail.)
"""

__version__ = '1.2.1'
__all__ = [
    'ArgumentParser',
    'ArgumentError',
    'ArgumentTypeError',
    'FileType',
    'HelpFormatter',
    'ArgumentDefaultsHelpFormatter',
    'RawDescriptionHelpFormatter',
    'RawTextHelpFormatter',
    'Namespace',
    'Action',
    'ONE_OR_MORE',
    'OPTIONAL',
    'PARSER',
    'REMAINDER',
    'SUPPRESS',
    'ZERO_OR_MORE',
]


import copy as _copy
import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

from gettext import gettext as _

try:
    set
except NameError:
    # for python < 2.4 compatibility (sets module is there since 2.3):
    from sets import Set as set

try:
    basestring
except NameError:
    basestring = str

try:
    sorted
except NameError:
    # for python < 2.4 compatibility:
    def sorted(iterable, reverse=False):
        result = list(iterable)
        result.sort()
        if reverse:
            result.reverse()
        return result


def _callable(obj):
    return hasattr(obj, '__call__') or hasattr(obj, '__bases__')


SUPPRESS = '==SUPPRESS=='

OPTIONAL = '?'
ZERO_OR_MORE = '*'
ONE_OR_MORE = '+'
PARSER = 'A...'
REMAINDER = '...'
_UNRECOGNIZED_ARGS_ATTR = '_unrecognized_args'

# =============================
# Utility functions and classes
# =============================

class _AttributeHolder(object):
    """Abstract base class that provides __repr__.

    The __repr__ method returns a string in the format::
        ClassName(attr=name, attr=name, ...)
    The attributes are determined either by a class-level attribute,
    '_kwarg_names', or by inspecting the instance __dict__.
    """

    def __repr__(self):
        type_name = type(self).__name__
        arg_strings = []
        for arg in self._get_args():
            arg_strings.append(repr(arg))
        for name, value in self._get_kwargs():
            arg_strings.append('%s=%r' % (name, value))
        return '%s(%s)' % (type_name, ', '.join(arg_strings))

    def _get_kwargs(self):
        return sorted(self.__dict__.items())

    def _get_args(self):
        return []


def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)


# ===============
# Formatting Help
# ===============

class HelpFormatter(object):
    """Formatter for generating usage messages and argument help strings.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def __init__(self,
                 prog,
                 indent_increment=2,
                 max_help_position=24,
                 width=None):

        # default setting for width
        if width is None:
            try:
                width = int(_os.environ['COLUMNS'])
            except (KeyError, ValueError):
                width = 80
            width -= 2

        self._prog = prog
        self._indent_increment = indent_increment
        self._max_help_position = max_help_position
        self._width = width

        self._current_indent = 0
        self._level = 0
        self._action_max_length = 0

        self._root_section = self._Section(self, None)
        self._current_section = self._root_section

        self._whitespace_matcher = _re.compile(r'\s+')
        self._long_break_matcher = _re.compile(r'\n\n\n+')

    # ===============================
    # Section and indentation methods
    # ===============================
    def _indent(self):
        self._current_indent += self._indent_increment
        self._level += 1

    def _dedent(self):
        self._current_indent -= self._indent_increment
        assert self._current_indent >= 0, 'Indent decreased below 0.'
        self._level -= 1

    class _Section(object):

        def __init__(self, formatter, parent, heading=None):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items = []

        def format_help(self):
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            for func, args in self.items:
                func(*args)
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ''

            # add the heading if the section was non-empty
            if self.heading is not SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                heading = '%*s%s:\n' % (current_indent, '', self.heading)
            else:
                heading = ''

            # join the section-initial newline, the heading and the help
            return join(['\n', heading, item_help, '\n'])

    def _add_item(self, func, args):
        self._current_section.items.append((func, args))

    # ========================
    # Message building methods
    # ========================
    def start_section(self, heading):
        self._indent()
        section = self._Section(self, self._current_section, heading)
        self._add_item(section.format_help, [])
        self._current_section = section

    def end_section(self):
        self._current_section = self._current_section.parent
        self._dedent()

    def add_text(self, text):
        if text is not SUPPRESS and text is not None:
            self._add_item(self._format_text, [text])

    def add_usage(self, usage, actions, groups, prefix=None):
        if usage is not SUPPRESS:
            args = usage, actions, groups, prefix
            self._add_item(self._format_usage, args)

    def add_argument(self, action):
        if action.help is not SUPPRESS:

            # find all invocations
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            for subaction in self._iter_indented_subactions(action):
                invocations.append(get_invocation(subaction))

            # update the maximum item length
            invocation_length = max([len(s) for s in invocations])
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length,
                                          action_length)

            # add the item to the list
            self._add_item(self._format_action, [action])

    def add_arguments(self, actions):
        for action in actions:
            self.add_argument(action)

    # =======================
    # Help-formatting methods
    # =======================
    def format_help(self):
        help = self._root_section.format_help()
        if help:
            help = self._long_break_matcher.sub('\n\n', help)
            help = help.strip('\n') + '\n'
        return help

    def _join_parts(self, part_strings):
        return ''.join([part
                        for part in part_strings
                        if part and part is not SUPPRESS])

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = _('usage: ')

        # if usage is specified, use that
        if usage is not None:
            usage = usage % dict(prog=self._prog)

        # if no optionals or positionals are available, usage is just prog
        elif usage is None and not actions:
            usage = '%(prog)s' % dict(prog=self._prog)

        # if optionals and positionals are available, calculate usage
        elif usage is None:
            prog = '%(prog)s' % dict(prog=self._prog)

            # split optionals from positionals
            optionals = []
            positionals = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)

            # build full usage string
            format = self._format_actions_usage
            action_usage = format(optionals + positionals, groups)
            usage = ' '.join([s for s in [prog, action_usage] if s])

            # wrap the usage parts if it's too long
            text_width = self._width - self._current_indent
            if len(prefix) + len(usage) > text_width:

                # break usage into wrappable parts
                part_regexp = r'\(.*?\)+|\[.*?\]+|\S+'
                opt_usage = format(optionals, groups)
                pos_usage = format(positionals, groups)
                opt_parts = _re.findall(part_regexp, opt_usage)
                pos_parts = _re.findall(part_regexp, pos_usage)
                assert ' '.join(opt_parts) == opt_usage
                assert ' '.join(pos_parts) == pos_usage

                # helper for wrapping lines
                def get_lines(parts, indent, prefix=None):
                    lines = []
                    line = []
                    if prefix is not None:
                        line_len = len(prefix) - 1
                    else:
                        line_len = len(indent) - 1
                    for part in parts:
                        if line_len + 1 + len(part) > text_width:
                            lines.append(indent + ' '.join(line))
                            line = []
                            line_len = len(indent) - 1
                        line.append(part)
                        line_len += len(part) + 1
                    if line:
                        lines.append(indent + ' '.join(line))
                    if prefix is not None:
                        lines[0] = lines[0][len(indent):]
                    return lines

                # if prog is short, follow it with optionals or positionals
                if len(prefix) + len(prog) <= 0.75 * text_width:
                    indent = ' ' * (len(prefix) + len(prog) + 1)
                    if opt_parts:
                        lines = get_lines([prog] + opt_parts, indent, prefix)
                        lines.extend(get_lines(pos_parts, indent))
                    elif pos_parts:
                        lines = get_lines([prog] + pos_parts, indent, prefix)
                    else:
                        lines = [prog]

                # if prog is long, put it on its own line
                else:
                    indent = ' ' * len(prefix)
                    parts = opt_parts + pos_parts
                    lines = get_lines(parts, indent)
                    if len(lines) > 1:
                        lines = []
                        lines.extend(get_lines(opt_parts, indent))
                        lines.extend(get_lines(pos_parts, indent))
                    lines = [prog] + lines

                # join lines into usage
                usage = '\n'.join(lines)

        # prefix with 'usage:'
        return '%s%s\n\n' % (prefix, usage)

    def _format_actions_usage(self, actions, groups):
        # find group indices and identify actions in groups
        group_actions = set()
        inserts = {}
        for group in groups:
            try:
                start = actions.index(group._group_actions[0])
            except ValueError:
                continue
            else:
                end = start + len(group._group_actions)
                if actions[start:end] == group._group_actions:
                    for action in group._group_actions:
                        group_actions.add(action)
                    if not group.required:
                        if start in inserts:
                            inserts[start] += ' ['
                        else:
                            inserts[start] = '['
                        inserts[end] = ']'
                    else:
                        if start in inserts:
                            inserts[start] += ' ('
                        else:
                            inserts[start] = '('
                        inserts[end] = ')'
                    for i in range(start + 1, end):
                        inserts[i] = '|'

        # collect all actions format strings
        parts = []
        for i, action in enumerate(actions):

            # suppressed arguments are marked with None
            # remove | separators for suppressed arguments
            if action.help is SUPPRESS:
                parts.append(None)
                if inserts.get(i) == '|':
                    inserts.pop(i)
                elif inserts.get(i + 1) == '|':
                    inserts.pop(i + 1)

            # produce all arg strings
            elif not action.option_strings:
                part = self._format_args(action, action.dest)

                # if it's in a group, strip the outer []
                if action in group_actions:
                    if part[0] == '[' and part[-1] == ']':
                        part = part[1:-1]

                # add the action string to the list
                parts.append(part)

            # produce the first way to invoke the option in brackets
            else:
                option_string = action.option_strings[0]

                # if the Optional doesn't take a value, format is:
                #    -s or --long
                if action.nargs == 0:
                    part = '%s' % option_string

                # if the Optional takes a value, format is:
                #    -s ARGS or --long ARGS
                else:
                    default = action.dest.upper()
                    args_string = self._format_args(action, default)
                    part = '%s %s' % (option_string, args_string)

                # make it look optional if it's not required or in a group
                if not action.required and action not in group_actions:
                    part = '[%s]' % part

                # add the action string to the list
                parts.append(part)

        # insert things at the necessary indices
        for i in sorted(inserts, reverse=True):
            parts[i:i] = [inserts[i]]

        # join all the action items with spaces
        text = ' '.join([item for item in parts if item is not None])

        # clean up separators for mutually exclusive groups
        open = r'[\[(]'
        close = r'[\])]'
        text = _re.sub(r'(%s) ' % open, r'\1', text)
        text = _re.sub(r' (%s)' % close, r'\1', text)
        text = _re.sub(r'%s *%s' % (open, close), r'', text)
        text = _re.sub(r'\(([^|]*)\)', r'\1', text)
        text = text.strip()

        # return the text
        return text

    def _format_text(self, text):
        if '%(prog)' in text:
            text = text % dict(prog=self._prog)
        text_width = self._width - self._current_indent
        indent = ' ' * self._current_indent
        return self._fill_text(text, text_width, indent) + '\n\n'

    def _format_action(self, action):
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = self._width - help_position
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)

        # ho nelp; start on same line and add a final newline
        if not action.help:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup

        # short action name; start on the same line and pad two spaces
        elif len(action_header) <= action_width:
            tup = self._current_indent, '', action_width, action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0

        # long action name; start on the next line
        else:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        # if there was help for the action, add lines of help text
        if action.help:
            help_text = self._expand_help(action)
            help_lines = self._split_lines(help_text, help_width)
            parts.append('%*s%s\n' % (indent_first, '', help_lines[0]))
            for line in help_lines[1:]:
                parts.append('%*s%s\n' % (help_position, '', line))

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith('\n'):
            parts.append('\n')

        # if there are any sub-actions, add their help as well
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar

        else:
            parts = []

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    parts.append('%s %s' % (option_string, args_string))

            return ', '.join(parts)

    def _metavar_formatter(self, action, default_metavar):
        if action.metavar is not None:
            result = action.metavar
        elif action.choices is not None:
            choice_strs = [str(choice) for choice in action.choices]
            result = '{%s}' % ','.join(choice_strs)
        else:
            result = default_metavar

        def format(tuple_size):
            if isinstance(result, tuple):
                return result
            else:
                return (result, ) * tuple_size
        return format

    def _format_args(self, action, default_metavar):
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs is None:
            result = '%s' % get_metavar(1)
        elif action.nargs == OPTIONAL:
            result = '[%s]' % get_metavar(1)
        elif action.nargs == ZERO_OR_MORE:
            result = '[%s [%s ...]]' % get_metavar(2)
        elif action.nargs == ONE_OR_MORE:
            result = '%s [%s ...]' % get_metavar(2)
        elif action.nargs == REMAINDER:
            result = '...'
        elif action.nargs == PARSER:
            result = '%s ...' % get_metavar(1)
        else:
            formats = ['%s' for _ in range(action.nargs)]
            result = ' '.join(formats) % get_metavar(action.nargs)
        return result

    def _expand_help(self, action):
        params = dict(vars(action), prog=self._prog)
        for name in list(params):
            if params[name] is SUPPRESS:
                del params[name]
        for name in list(params):
            if hasattr(params[name], '__name__'):
                params[name] = params[name].__name__
        if params.get('choices') is not None:
            choices_str = ', '.join([str(c) for c in params['choices']])
            params['choices'] = choices_str
        return self._get_help_string(action) % params

    def _iter_indented_subactions(self, action):
        try:
            get_subactions = action._get_subactions
        except AttributeError:
            pass
        else:
            self._indent()
            for subaction in get_subactions():
                yield subaction
            self._dedent()

    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.wrap(text, width)

    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.fill(text, width, initial_indent=indent,
                                           subsequent_indent=indent)

    def _get_help_string(self, action):
        return action.help


class RawDescriptionHelpFormatter(HelpFormatter):
    """Help message formatter which retains any formatting in descriptions.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _fill_text(self, text, width, indent):
        return ''.join([indent + line for line in text.splitlines(True)])


class RawTextHelpFormatter(RawDescriptionHelpFormatter):
    """Help message formatter which retains formatting of all help text.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _split_lines(self, text, width):
        return text.splitlines()


class ArgumentDefaultsHelpFormatter(HelpFormatter):
    """Help message formatter which adds default values to argument help.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help:
            if action.default is not SUPPRESS:
                defaulting_nargs = [OPTIONAL, ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help


# =====================
# Options and Arguments
# =====================

def _get_action_name(argument):
    if argument is None:
        return None
    elif argument.option_strings:
        return  '/'.join(argument.option_strings)
    elif argument.metavar not in (None, SUPPRESS):
        return argument.metavar
    elif argument.dest not in (None, SUPPRESS):
        return argument.dest
    else:
        return None


class ArgumentError(Exception):
    """An error from creating or using an argument (optional or positional).

    The string value of this exception is the message, augmented with
    information about the argument that caused it.
    """

    def __init__(self, argument, message):
        self.argument_name = _get_action_name(argument)
        self.message = message

    def __str__(self):
        if self.argument_name is None:
            format = '%(message)s'
        else:
            format = 'argument %(argument_name)s: %(message)s'
        return format % dict(message=self.message,
                             argument_name=self.argument_name)


class ArgumentTypeError(Exception):
    """An error from trying to convert a command line string to a type."""
    pass


# ==============
# Action classes
# ==============

class Action(_AttributeHolder):
    """Information about how to convert command line strings to Python objects.

    Action objects are used by an ArgumentParser to represent the information
    needed to parse a single argument from one or more strings from the
    command line. The keyword arguments to the Action constructor are also
    all attributes of Action instances.

    Keyword Arguments:

        - option_strings -- A list of command-line option strings which
            should be associated with this action.

        - dest -- The name of the attribute to hold the created object(s)

        - nargs -- The number of command-line arguments that should be
            consumed. By default, one argument will be consumed and a single
            value will be produced.  Other values include:
                - N (an integer) consumes N arguments (and produces a list)
                - '?' consumes zero or one arguments
                - '*' consumes zero or more arguments (and produces a list)
                - '+' consumes one or more arguments (and produces a list)
            Note that the difference between the default and nargs=1 is that
            with the default, a single value will be produced, while with
            nargs=1, a list containing a single value will be produced.

        - const -- The value to be produced if the option is specified and the
            option uses an action that takes no values.

        - default -- The value to be produced if the option is not specified.

        - type -- The type which the command-line arguments should be converted
            to, should be one of 'string', 'int', 'float', 'complex' or a
            callable object that accepts a single string argument. If None,
            'string' is assumed.

        - choices -- A container of values that should be allowed. If not None,
            after a command-line argument has been converted to the appropriate
            type, an exception will be raised if it is not a member of this
            collection.

        - required -- True if the action must always be specified at the
            command line. This is only meaningful for optional command-line
            arguments.

        - help -- The help string describing the argument.

        - metavar -- The name to be used for the option's argument with the
            help string. If None, the 'dest' value will be used as the name.
    """

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        self.option_strings = option_strings
        self.dest = dest
        self.nargs = nargs
        self.const = const
        self.default = default
        self.type = type
        self.choices = choices
        self.required = required
        self.help = help
        self.metavar = metavar

    def _get_kwargs(self):
        names = [
            'option_strings',
            'dest',
            'nargs',
            'const',
            'default',
            'type',
            'choices',
            'help',
            'metavar',
        ]
        return [(name, getattr(self, name)) for name in names]

    def __call__(self, parser, namespace, values, option_string=None):
        raise NotImplementedError(_('.__call__() not defined'))


class _StoreAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs for store actions must be > 0; if you '
                             'have nothing to store, actions such as store '
                             'true or store const may be more appropriate')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(_StoreAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class _StoreConstAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(_StoreConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, self.const)


class _StoreTrueAction(_StoreConstAction):

    def __init__(self,
                 option_strings,
                 dest,
                 default=False,
                 required=False,
                 help=None):
        super(_StoreTrueAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=True,
            default=default,
            required=required,
            help=help)


class _StoreFalseAction(_StoreConstAction):

    def __init__(self,
                 option_strings,
                 dest,
                 default=True,
                 required=False,
                 help=None):
        super(_StoreFalseAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=False,
            default=default,
            required=required,
            help=help)


class _AppendAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs for append actions must be > 0; if arg '
                             'strings are not supplying the value to append, '
                             'the append const action may be more appropriate')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(_AppendAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(values)
        setattr(namespace, self.dest, items)


class _AppendConstAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(_AppendConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(self.const)
        setattr(namespace, self.dest, items)


class _CountAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 required=False,
                 help=None):
        super(_CountAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = _ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


class _HelpAction(Action):

    def __init__(self,
                 option_strings,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help=None):
        super(_HelpAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        parser.exit()


class _VersionAction(Action):

    def __init__(self,
                 option_strings,
                 version=None,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help="show program's version number and exit"):
        super(_VersionAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)
        self.version = version

    def __call__(self, parser, namespace, values, option_string=None):
        version = self.version
        if version is None:
            version = parser.version
        formatter = parser._get_formatter()
        formatter.add_text(version)
        parser.exit(message=formatter.format_help())


class _SubParsersAction(Action):

    class _ChoicesPseudoAction(Action):

        def __init__(self, name, help):
            sup = super(_SubParsersAction._ChoicesPseudoAction, self)
            sup.__init__(option_strings=[], dest=name, help=help)

    def __init__(self,
                 option_strings,
                 prog,
                 parser_class,
                 dest=SUPPRESS,
                 help=None,
                 metavar=None):

        self._prog_prefix = prog
        self._parser_class = parser_class
        self._name_parser_map = {}
        self._choices_actions = []

        super(_SubParsersAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=PARSER,
            choices=self._name_parser_map,
            help=help,
            metavar=metavar)

    def add_parser(self, name, **kwargs):
        # set prog from the existing prefix
        if kwargs.get('prog') is None:
            kwargs['prog'] = '%s %s' % (self._prog_prefix, name)

        # create a pseudo-action to hold the choice help
        if 'help' in kwargs:
            help = kwargs.pop('help')
            choice_action = self._ChoicesPseudoAction(name, help)
            self._choices_actions.append(choice_action)

        # create the parser and add it to the map
        parser = self._parser_class(**kwargs)
        self._name_parser_map[name] = parser
        return parser

    def _get_subactions(self):
        return self._choices_actions

    def __call__(self, parser, namespace, values, option_string=None):
        parser_name = values[0]
        arg_strings = values[1:]

        # set the parser name if requested
        if self.dest is not SUPPRESS:
            setattr(namespace, self.dest, parser_name)

        # select the parser
        try:
            parser = self._name_parser_map[parser_name]
        except KeyError:
            tup = parser_name, ', '.join(self._name_parser_map)
            msg = _('unknown parser %r (choices: %s)' % tup)
            raise ArgumentError(self, msg)

        # parse all the remaining options into the namespace
        # store any unrecognized options on the object, so that the top
        # level parser can decide what to do with them
        namespace, arg_strings = parser.parse_known_args(arg_strings, namespace)
        if arg_strings:
            vars(namespace).setdefault(_UNRECOGNIZED_ARGS_ATTR, [])
            getattr(namespace, _UNRECOGNIZED_ARGS_ATTR).extend(arg_strings)


# ==============
# Type classes
# ==============

class FileType(object):
    """Factory for creating file object types

    Instances of FileType are typically passed as type= arguments to the
    ArgumentParser add_argument() method.

    Keyword Arguments:
        - mode -- A string indicating how the file is to be opened. Accepts the
            same values as the builtin open() function.
        - bufsize -- The file's desired buffer size. Accepts the same values as
            the builtin open() function.
    """

    def __init__(self, mode='r', bufsize=None):
        self._mode = mode
        self._bufsize = bufsize

    def __call__(self, string):
        # the special argument "-" means sys.std{in,out}
        if string == '-':
            if 'r' in self._mode:
                return _sys.stdin
            elif 'w' in self._mode:
                return _sys.stdout
            else:
                msg = _('argument "-" with mode %r' % self._mode)
                raise ValueError(msg)

        # all other arguments are used as file names
        if self._bufsize:
            return open(string, self._mode, self._bufsize)
        else:
            return open(string, self._mode)

    def __repr__(self):
        args = [self._mode, self._bufsize]
        args_str = ', '.join([repr(arg) for arg in args if arg is not None])
        return '%s(%s)' % (type(self).__name__, args_str)

# ===========================
# Optional and Positional Parsing
# ===========================

class Namespace(_AttributeHolder):
    """Simple object for storing attributes.

    Implements equality by attribute names and values, and provides a simple
    string representation.
    """

    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])

    __hash__ = None

    def __eq__(self, other):
        return vars(self) == vars(other)

    def __ne__(self, other):
        return not (self == other)

    def __contains__(self, key):
        return key in self.__dict__


class _ActionsContainer(object):

    def __init__(self,
                 description,
                 prefix_chars,
                 argument_default,
                 conflict_handler):
        super(_ActionsContainer, self).__init__()

        self.description = description
        self.argument_default = argument_default
        self.prefix_chars = prefix_chars
        self.conflict_handler = conflict_handler

        # set up registries
        self._registries = {}

        # register actions
        self.register('action', None, _StoreAction)
        self.register('action', 'store', _StoreAction)
        self.register('action', 'store_const', _StoreConstAction)
        self.register('action', 'store_true', _StoreTrueAction)
        self.register('action', 'store_false', _StoreFalseAction)
        self.register('action', 'append', _AppendAction)
        self.register('action', 'append_const', _AppendConstAction)
        self.register('action', 'count', _CountAction)
        self.register('action', 'help', _HelpAction)
        self.register('action', 'version', _VersionAction)
        self.register('action', 'parsers', _SubParsersAction)

        # raise an exception if the conflict handler is invalid
        self._get_handler()

        # action storage
        self._actions = []
        self._option_string_actions = {}

        # groups
        self._action_groups = []
        self._mutually_exclusive_groups = []

        # defaults storage
        self._defaults = {}

        # determines whether an "option" looks like a negative number
        self._negative_number_matcher = _re.compile(r'^-\d+$|^-\d*\.\d+$')

        # whether or not there are any optionals that look like negative
        # numbers -- uses a list so it can be shared and edited
        self._has_negative_number_optionals = []

    # ====================
    # Registration methods
    # ====================
    def register(self, registry_name, value, object):
        registry = self._registries.setdefault(registry_name, {})
        registry[value] = object

    def _registry_get(self, registry_name, value, default=None):
        return self._registries[registry_name].get(value, default)

    # ==================================
    # Namespace default accessor methods
    # ==================================
    def set_defaults(self, **kwargs):
        self._defaults.update(kwargs)

        # if these defaults match any existing arguments, replace
        # the previous default on the object with the new one
        for action in self._actions:
            if action.dest in kwargs:
                action.default = kwargs[action.dest]

    def get_default(self, dest):
        for action in self._actions:
            if action.dest == dest and action.default is not None:
                return action.default
        return self._defaults.get(dest, None)


    # =======================
    # Adding argument actions
    # =======================
    def add_argument(self, *args, **kwargs):
        """
        add_argument(dest, ..., name=value, ...)
        add_argument(option_string, option_string, ..., name=value, ...)
        """

        # if no positional args are supplied or only one is supplied and
        # it doesn't look like an option string, parse a positional
        # argument
        chars = self.prefix_chars
        if not args or len(args) == 1 and args[0][0] not in chars:
            if args and 'dest' in kwargs:
                raise ValueError('dest supplied twice for positional argument')
            kwargs = self._get_positional_kwargs(*args, **kwargs)

        # otherwise, we're adding an optional argument
        else:
            kwargs = self._get_optional_kwargs(*args, **kwargs)

        # if no default was supplied, use the parser-level default
        if 'default' not in kwargs:
            dest = kwargs['dest']
            if dest in self._defaults:
                kwargs['default'] = self._defaults[dest]
            elif self.argument_default is not None:
                kwargs['default'] = self.argument_default

        # create the action object, and add it to the parser
        action_class = self._pop_action_class(kwargs)
        if not _callable(action_class):
            raise ValueError('unknown action "%s"' % action_class)
        action = action_class(**kwargs)

        # raise an error if the action type is not callable
        type_func = self._registry_get('type', action.type, action.type)
        if not _callable(type_func):
            raise ValueError('%r is not callable' % type_func)

        return self._add_action(action)

    def add_argument_group(self, *args, **kwargs):
        group = _ArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def add_mutually_exclusive_group(self, **kwargs):
        group = _MutuallyExclusiveGroup(self, **kwargs)
        self._mutually_exclusive_groups.append(group)
        return group

    def _add_action(self, action):
        # resolve any conflicts
        self._check_conflict(action)

        # add to actions list
        self._actions.append(action)
        action.container = self

        # index the action by any option strings it has
        for option_string in action.option_strings:
            self._option_string_actions[option_string] = action

        # set the flag if any option strings look like negative numbers
        for option_string in action.option_strings:
            if self._negative_number_matcher.match(option_string):
                if not self._has_negative_number_optionals:
                    self._has_negative_number_optionals.append(True)

        # return the created action
        return action

    def _remove_action(self, action):
        self._actions.remove(action)

    def _add_container_actions(self, container):
        # collect groups by titles
        title_group_map = {}
        for group in self._action_groups:
            if group.title in title_group_map:
                msg = _('cannot merge actions - two groups are named %r')
                raise ValueError(msg % (group.title))
            title_group_map[group.title] = group

        # map each action to its group
        group_map = {}
        for group in container._action_groups:

            # if a group with the title exists, use that, otherwise
            # create a new group matching the container's group
            if group.title not in title_group_map:
                title_group_map[group.title] = self.add_argument_group(
                    title=group.title,
                    description=group.description,
                    conflict_handler=group.conflict_handler)

            # map the actions to their new group
            for action in group._group_actions:
                group_map[action] = title_group_map[group.title]

        # add container's mutually exclusive groups
        # NOTE: if add_mutually_exclusive_group ever gains title= and
        # description= then this code will need to be expanded as above
        for group in container._mutually_exclusive_groups:
            mutex_group = self.add_mutually_exclusive_group(
                required=group.required)

            # map the actions to their new mutex group
            for action in group._group_actions:
                group_map[action] = mutex_group

        # add all actions to this container or their group
        for action in container._actions:
            group_map.get(action, self)._add_action(action)

    def _get_positional_kwargs(self, dest, **kwargs):
        # make sure required is not specified
        if 'required' in kwargs:
            msg = _("'required' is an invalid argument for positionals")
            raise TypeError(msg)

        # mark positional arguments as required if at least one is
        # always required
        if kwargs.get('nargs') not in [OPTIONAL, ZERO_OR_MORE]:
            kwargs['required'] = True
        if kwargs.get('nargs') == ZERO_OR_MORE and 'default' not in kwargs:
            kwargs['required'] = True

        # return the keyword arguments with no option strings
        return dict(kwargs, dest=dest, option_strings=[])

    def _get_optional_kwargs(self, *args, **kwargs):
        # determine short and long option strings
        option_strings = []
        long_option_strings = []
        for option_string in args:
            # error on strings that don't start with an appropriate prefix
            if not option_string[0] in self.prefix_chars:
                msg = _('invalid option string %r: '
                        'must start with a character %r')
                tup = option_string, self.prefix_chars
                raise ValueError(msg % tup)

            # strings starting with two prefix characters are long options
            option_strings.append(option_string)
            if option_string[0] in self.prefix_chars:
                if len(option_string) > 1:
                    if option_string[1] in self.prefix_chars:
                        long_option_strings.append(option_string)

        # infer destination, '--foo-bar' -> 'foo_bar' and '-x' -> 'x'
        dest = kwargs.pop('dest', None)
        if dest is None:
            if long_option_strings:
                dest_option_string = long_option_strings[0]
            else:
                dest_option_string = option_strings[0]
            dest = dest_option_string.lstrip(self.prefix_chars)
            if not dest:
                msg = _('dest= is required for options like %r')
                raise ValueError(msg % option_string)
            dest = dest.replace('-', '_')

        # return the updated keyword arguments
        return dict(kwargs, dest=dest, option_strings=option_strings)

    def _pop_action_class(self, kwargs, default=None):
        action = kwargs.pop('action', default)
        return self._registry_get('action', action, action)

    def _get_handler(self):
        # determine function from conflict handler string
        handler_func_name = '_handle_conflict_%s' % self.conflict_handler
        try:
            return getattr(self, handler_func_name)
        except AttributeError:
            msg = _('invalid conflict_resolution value: %r')
            raise ValueError(msg % self.conflict_handler)

    def _check_conflict(self, action):

        # find all options that conflict with this option
        confl_optionals = []
        for option_string in action.option_strings:
            if option_string in self._option_string_actions:
                confl_optional = self._option_string_actions[option_string]
                confl_optionals.append((option_string, confl_optional))

        # resolve any conflicts
        if confl_optionals:
            conflict_handler = self._get_handler()
            conflict_handler(action, confl_optionals)

    def _handle_conflict_error(self, action, conflicting_actions):
        message = _('conflicting option string(s): %s')
        conflict_string = ', '.join([option_string
                                     for option_string, action
                                     in conflicting_actions])
        raise ArgumentError(action, message % conflict_string)

    def _handle_conflict_resolve(self, action, conflicting_actions):

        # remove all conflicting options
        for option_string, action in conflicting_actions:

            # remove the conflicting option
            action.option_strings.remove(option_string)
            self._option_string_actions.pop(option_string, None)

            # if the option now has no option string, remove it from the
            # container holding it
            if not action.option_strings:
                action.container._remove_action(action)


class _ArgumentGroup(_ActionsContainer):

    def __init__(self, container, title=None, description=None, **kwargs):
        # add any missing keyword arguments by checking the container
        update = kwargs.setdefault
        update('conflict_handler', container.conflict_handler)
        update('prefix_chars', container.prefix_chars)
        update('argument_default', container.argument_default)
        super_init = super(_ArgumentGroup, self).__init__
        super_init(description=description, **kwargs)

        # group attributes
        self.title = title
        self._group_actions = []

        # share most attributes with the container
        self._registries = container._registries
        self._actions = container._actions
        self._option_string_actions = container._option_string_actions
        self._defaults = container._defaults
        self._has_negative_number_optionals = \
            container._has_negative_number_optionals

    def _add_action(self, action):
        action = super(_ArgumentGroup, self)._add_action(action)
        self._group_actions.append(action)
        return action

    def _remove_action(self, action):
        super(_ArgumentGroup, self)._remove_action(action)
        self._group_actions.remove(action)


class _MutuallyExclusiveGroup(_ArgumentGroup):

    def __init__(self, container, required=False):
        super(_MutuallyExclusiveGroup, self).__init__(container)
        self.required = required
        self._container = container

    def _add_action(self, action):
        if action.required:
            msg = _('mutually exclusive arguments must be optional')
            raise ValueError(msg)
        action = self._container._add_action(action)
        self._group_actions.append(action)
        return action

    def _remove_action(self, action):
        self._container._remove_action(action)
        self._group_actions.remove(action)


class ArgumentParser(_AttributeHolder, _ActionsContainer):
    """Object for parsing command line strings into Python objects.

    Keyword Arguments:
        - prog -- The name of the program (default: sys.argv[0])
        - usage -- A usage message (default: auto-generated from arguments)
        - description -- A description of what the program does
        - epilog -- Text following the argument descriptions
        - parents -- Parsers whose arguments should be copied into this one
        - formatter_class -- HelpFormatter class for printing help messages
        - prefix_chars -- Characters that prefix optional arguments
        - fromfile_prefix_chars -- Characters that prefix files containing
            additional arguments
        - argument_default -- The default value for all arguments
        - conflict_handler -- String indicating how to handle conflicts
        - add_help -- Add a -h/-help option
    """

    def __init__(self,
                 prog=None,
                 usage=None,
                 description=None,
                 epilog=None,
                 version=None,
                 parents=[],
                 formatter_class=HelpFormatter,
                 prefix_chars='-',
                 fromfile_prefix_chars=None,
                 argument_default=None,
                 conflict_handler='error',
                 add_help=True):

        if version is not None:
            import warnings
            warnings.warn(
                """The "version" argument to ArgumentParser is deprecated. """
                """Please use """
                """"add_argument(..., action='version', version="N", ...)" """
                """instead""", DeprecationWarning)

        superinit = super(ArgumentParser, self).__init__
        superinit(description=description,
                  prefix_chars=prefix_chars,
                  argument_default=argument_default,
                  conflict_handler=conflict_handler)

        # default setting for prog
        if prog is None:
            prog = _os.path.basename(_sys.argv[0])

        self.prog = prog
        self.usage = usage
        self.epilog = epilog
        self.version = version
        self.formatter_class = formatter_class
        self.fromfile_prefix_chars = fromfile_prefix_chars
        self.add_help = add_help

        add_group = self.add_argument_group
        self._positionals = add_group(_('positional arguments'))
        self._optionals = add_group(_('optional arguments'))
        self._subparsers = None

        # register types
        def identity(string):
            return string
        self.register('type', None, identity)

        # add help and version arguments if necessary
        # (using explicit default to override global argument_default)
        if '-' in prefix_chars:
            default_prefix = '-'
        else:
            default_prefix = prefix_chars[0]
        if self.add_help:
            self.add_argument(
                default_prefix+'h', default_prefix*2+'help',
                action='help', default=SUPPRESS,
                help=_('show this help message and exit'))
        if self.version:
            self.add_argument(
                default_prefix+'v', default_prefix*2+'version',
                action='version', default=SUPPRESS,
                version=self.version,
                help=_("show program's version number and exit"))

        # add parent arguments and defaults
        for parent in parents:
            self._add_container_actions(parent)
            try:
                defaults = parent._defaults
            except AttributeError:
                pass
            else:
                self._defaults.update(defaults)

    # =======================
    # Pretty __repr__ methods
    # =======================
    def _get_kwargs(self):
        names = [
            'prog',
            'usage',
            'description',
            'version',
            'formatter_class',
            'conflict_handler',
            'add_help',
        ]
        return [(name, getattr(self, name)) for name in names]

    # ==================================
    # Optional/Positional adding methods
    # ==================================
    def add_subparsers(self, **kwargs):
        if self._subparsers is not None:
            self.error(_('cannot have multiple subparser arguments'))

        # add the parser class to the arguments if it's not present
        kwargs.setdefault('parser_class', type(self))

        if 'title' in kwargs or 'description' in kwargs:
            title = _(kwargs.pop('title', 'subcommands'))
            description = _(kwargs.pop('description', None))
            self._subparsers = self.add_argument_group(title, description)
        else:
            self._subparsers = self._positionals

        # prog defaults to the usage message of this parser, skipping
        # optional arguments and with no "usage:" prefix
        if kwargs.get('prog') is None:
            formatter = self._get_formatter()
            positionals = self._get_positional_actions()
            groups = self._mutually_exclusive_groups
            formatter.add_usage(self.usage, positionals, groups, '')
            kwargs['prog'] = formatter.format_help().strip()

        # create the parsers action and add it to the positionals list
        parsers_class = self._pop_action_class(kwargs, 'parsers')
        action = parsers_class(option_strings=[], **kwargs)
        self._subparsers._add_action(action)

        # return the created parsers action
        return action

    def _add_action(self, action):
        if action.option_strings:
            self._optionals._add_action(action)
        else:
            self._positionals._add_action(action)
        return action

    def _get_optional_actions(self):
        return [action
                for action in self._actions
                if action.option_strings]

    def _get_positional_actions(self):
        return [action
                for action in self._actions
                if not action.option_strings]

    # =====================================
    # Command line argument parsing methods
    # =====================================
    def parse_args(self, args=None, namespace=None):
        args, argv = self.parse_known_args(args, namespace)
        if argv:
            msg = _('unrecognized arguments: %s')
            self.error(msg % ' '.join(argv))
        return args

    def parse_known_args(self, args=None, namespace=None):
        # args default to the system args
        if args is None:
            args = _sys.argv[1:]

        # default Namespace built from parser defaults
        if namespace is None:
            namespace = Namespace()

        # add any action defaults that aren't present
        for action in self._actions:
            if action.dest is not SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not SUPPRESS:
                        default = action.default
                        if isinstance(action.default, basestring):
                            default = self._get_value(action, default)
                        setattr(namespace, action.dest, default)

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, self._defaults[dest])

        # parse the arguments and exit if there are any errors
        try:
            namespace, args = self._parse_known_args(args, namespace)
            if hasattr(namespace, _UNRECOGNIZED_ARGS_ATTR):
                args.extend(getattr(namespace, _UNRECOGNIZED_ARGS_ATTR))
                delattr(namespace, _UNRECOGNIZED_ARGS_ATTR)
            return namespace, args
        except ArgumentError:
            err = _sys.exc_info()[1]
            self.error(str(err))

    def _parse_known_args(self, arg_strings, namespace):
        # replace arg strings that are file references
        if self.fromfile_prefix_chars is not None:
            arg_strings = self._read_args_from_files(arg_strings)

        # map all mutually exclusive arguments to the other arguments
        # they can't occur with
        action_conflicts = {}
        for mutex_group in self._mutually_exclusive_groups:
            group_actions = mutex_group._group_actions
            for i, mutex_action in enumerate(mutex_group._group_actions):
                conflicts = action_conflicts.setdefault(mutex_action, [])
                conflicts.extend(group_actions[:i])
                conflicts.extend(group_actions[i + 1:])

        # find all option indices, and determine the arg_string_pattern
        # which has an 'O' if there is an option at an index,
        # an 'A' if there is an argument, or a '-' if there is a '--'
        option_string_indices = {}
        arg_string_pattern_parts = []
        arg_strings_iter = iter(arg_strings)
        for i, arg_string in enumerate(arg_strings_iter):

            # all args after -- are non-options
            if arg_string == '--':
                arg_string_pattern_parts.append('-')
                for arg_string in arg_strings_iter:
                    arg_string_pattern_parts.append('A')

            # otherwise, add the arg to the arg strings
            # and note the index if it was an option
            else:
                option_tuple = self._parse_optional(arg_string)
                if option_tuple is None:
                    pattern = 'A'
                else:
                    option_string_indices[i] = option_tuple
                    pattern = 'O'
                arg_string_pattern_parts.append(pattern)

        # join the pieces together to form the pattern
        arg_strings_pattern = ''.join(arg_string_pattern_parts)

        # converts arg strings to the appropriate and then takes the action
        seen_actions = set()
        seen_non_default_actions = set()

        def take_action(action, argument_strings, option_string=None):
            seen_actions.add(action)
            argument_values = self._get_values(action, argument_strings)

            # error if this argument is not allowed with other previously
            # seen arguments, assuming that actions that use the default
            # value don't really count as "present"
            if argument_values is not action.default:
                seen_non_default_actions.add(action)
                for conflict_action in action_conflicts.get(action, []):
                    if conflict_action in seen_non_default_actions:
                        msg = _('not allowed with argument %s')
                        action_name = _get_action_name(conflict_action)
                        raise ArgumentError(action, msg % action_name)

            # take the action if we didn't receive a SUPPRESS value
            # (e.g. from a default)
            if argument_values is not SUPPRESS:
                action(self, namespace, argument_values, option_string)

        # function to convert arg_strings into an optional action
        def consume_optional(start_index):

            # get the optional identified at this index
            option_tuple = option_string_indices[start_index]
            action, option_string, explicit_arg = option_tuple

            # identify additional optionals in the same arg string
            # (e.g. -xyz is the same as -x -y -z if no args are required)
            match_argument = self._match_argument
            action_tuples = []
            while True:

                # if we found no optional action, skip it
                if action is None:
                    extras.append(arg_strings[start_index])
                    return start_index + 1

                # if there is an explicit argument, try to match the
                # optional's string arguments to only this
                if explicit_arg is not None:
                    arg_count = match_argument(action, 'A')

                    # if the action is a single-dash option and takes no
                    # arguments, try to parse more single-dash options out
                    # of the tail of the option string
                    chars = self.prefix_chars
                    if arg_count == 0 and option_string[1] not in chars:
                        action_tuples.append((action, [], option_string))
                        char = option_string[0]
                        option_string = char + explicit_arg[0]
                        new_explicit_arg = explicit_arg[1:] or None
                        optionals_map = self._option_string_actions
                        if option_string in optionals_map:
                            action = optionals_map[option_string]
                            explicit_arg = new_explicit_arg
                        else:
                            msg = _('ignored explicit argument %r')
                            raise ArgumentError(action, msg % explicit_arg)

                    # if the action expect exactly one argument, we've
                    # successfully matched the option; exit the loop
                    elif arg_count == 1:
                        stop = start_index + 1
                        args = [explicit_arg]
                        action_tuples.append((action, args, option_string))
                        break

                    # error if a double-dash option did not use the
                    # explicit argument
                    else:
                        msg = _('ignored explicit argument %r')
                        raise ArgumentError(action, msg % explicit_arg)

                # if there is no explicit argument, try to match the
                # optional's string arguments with the following strings
                # if successful, exit the loop
                else:
                    start = start_index + 1
                    selected_patterns = arg_strings_pattern[start:]
                    arg_count = match_argument(action, selected_patterns)
                    stop = start + arg_count
                    args = arg_strings[start:stop]
                    action_tuples.append((action, args, option_string))
                    break

            # add the Optional to the list and return the index at which
            # the Optional's string args stopped
            assert action_tuples
            for action, args, option_string in action_tuples:
                take_action(action, args, option_string)
            return stop

        # the list of Positionals left to be parsed; this is modified
        # by consume_positionals()
        positionals = self._get_positional_actions()

        # function to convert arg_strings into positional actions
        def consume_positionals(start_index):
            # match as many Positionals as possible
            match_partial = self._match_arguments_partial
            selected_pattern = arg_strings_pattern[start_index:]
            arg_counts = match_partial(positionals, selected_pattern)

            # slice off the appropriate arg strings for each Positional
            # and add the Positional and its args to the list
            for action, arg_count in zip(positionals, arg_counts):
                args = arg_strings[start_index: start_index + arg_count]
                start_index += arg_count
                take_action(action, args)

            # slice off the Positionals that we just parsed and return the
            # index at which the Positionals' string args stopped
            positionals[:] = positionals[len(arg_counts):]
            return start_index

        # consume Positionals and Optionals alternately, until we have
        # passed the last option string
        extras = []
        start_index = 0
        if option_string_indices:
            max_option_string_index = max(option_string_indices)
        else:
            max_option_string_index = -1
        while start_index <= max_option_string_index:

            # consume any Positionals preceding the next option
            next_option_string_index = min([
                index
                for index in option_string_indices
                if index >= start_index])
            if start_index != next_option_string_index:
                positionals_end_index = consume_positionals(start_index)

                # only try to parse the next optional if we didn't consume
                # the option string during the positionals parsing
                if positionals_end_index > start_index:
                    start_index = positionals_end_index
                    continue
                else:
                    start_index = positionals_end_index

            # if we consumed all the positionals we could and we're not
            # at the index of an option string, there were extra arguments
            if start_index not in option_string_indices:
                strings = arg_strings[start_index:next_option_string_index]
                extras.extend(strings)
                start_index = next_option_string_index

            # consume the next optional and any arguments for it
            start_index = consume_optional(start_index)

        # consume any positionals following the last Optional
        stop_index = consume_positionals(start_index)

        # if we didn't consume all the argument strings, there were extras
        extras.extend(arg_strings[stop_index:])

        # if we didn't use all the Positional objects, there were too few
        # arg strings supplied.
        if positionals:
            self.error(_('too few arguments'))

        # make sure all required actions were present
        for action in self._actions:
            if action.required:
                if action not in seen_actions:
                    name = _get_action_name(action)
                    self.error(_('argument %s is required') % name)

        # make sure all required groups had one option present
        for group in self._mutually_exclusive_groups:
            if group.required:
                for action in group._group_actions:
                    if action in seen_non_default_actions:
                        break

                # if no actions were used, report the error
                else:
                    names = [_get_action_name(action)
                             for action in group._group_actions
                             if action.help is not SUPPRESS]
                    msg = _('one of the arguments %s is required')
                    self.error(msg % ' '.join(names))

        # return the updated namespace and the extra arguments
        return namespace, extras

    def _read_args_from_files(self, arg_strings):
        # expand arguments referencing files
        new_arg_strings = []
        for arg_string in arg_strings:

            # for regular arguments, just add them back into the list
            if arg_string[0] not in self.fromfile_prefix_chars:
                new_arg_strings.append(arg_string)

            # replace arguments referencing files with the file content
            else:
                try:
                    args_file = open(arg_string[1:])
                    try:
                        arg_strings = []
                        for arg_line in args_file.read().splitlines():
                            for arg in self.convert_arg_line_to_args(arg_line):
                                arg_strings.append(arg)
                        arg_strings = self._read_args_from_files(arg_strings)
                        new_arg_strings.extend(arg_strings)
                    finally:
                        args_file.close()
                except IOError:
                    err = _sys.exc_info()[1]
                    self.error(str(err))

        # return the modified argument list
        return new_arg_strings

    def convert_arg_line_to_args(self, arg_line):
        return [arg_line]

    def _match_argument(self, action, arg_strings_pattern):
        # match the pattern for this action to the arg strings
        nargs_pattern = self._get_nargs_pattern(action)
        match = _re.match(nargs_pattern, arg_strings_pattern)

        # raise an exception if we weren't able to find a match
        if match is None:
            nargs_errors = {
                None: _('expected one argument'),
                OPTIONAL: _('expected at most one argument'),
                ONE_OR_MORE: _('expected at least one argument'),
            }
            default = _('expected %s argument(s)') % action.nargs
            msg = nargs_errors.get(action.nargs, default)
            raise ArgumentError(action, msg)

        # return the number of arguments matched
        return len(match.group(1))

    def _match_arguments_partial(self, actions, arg_strings_pattern):
        # progressively shorten the actions list by slicing off the
        # final actions until we find a match
        result = []
        for i in range(len(actions), 0, -1):
            actions_slice = actions[:i]
            pattern = ''.join([self._get_nargs_pattern(action)
                               for action in actions_slice])
            match = _re.match(pattern, arg_strings_pattern)
            if match is not None:
                result.extend([len(string) for string in match.groups()])
                break

        # return the list of arg string counts
        return result

    def _parse_optional(self, arg_string):
        # if it's an empty string, it was meant to be a positional
        if not arg_string:
            return None

        # if it doesn't start with a prefix, it was meant to be positional
        if not arg_string[0] in self.prefix_chars:
            return None

        # if the option string is present in the parser, return the action
        if arg_string in self._option_string_actions:
            action = self._option_string_actions[arg_string]
            return action, arg_string, None

        # if it's just a single character, it was meant to be positional
        if len(arg_string) == 1:
            return None

        # if the option string before the "=" is present, return the action
        if '=' in arg_string:
            option_string, explicit_arg = arg_string.split('=', 1)
            if option_string in self._option_string_actions:
                action = self._option_string_actions[option_string]
                return action, option_string, explicit_arg

        # search through all possible prefixes of the option string
        # and all actions in the parser for possible interpretations
        option_tuples = self._get_option_tuples(arg_string)

        # if multiple actions match, the option string was ambiguous
        if len(option_tuples) > 1:
            options = ', '.join([option_string
                for action, option_string, explicit_arg in option_tuples])
            tup = arg_string, options
            self.error(_('ambiguous option: %s could match %s') % tup)

        # if exactly one action matched, this segmentation is good,
        # so return the parsed action
        elif len(option_tuples) == 1:
            option_tuple, = option_tuples
            return option_tuple

        # if it was not found as an option, but it looks like a negative
        # number, it was meant to be positional
        # unless there are negative-number-like options
        if self._negative_number_matcher.match(arg_string):
            if not self._has_negative_number_optionals:
                return None

        # if it contains a space, it was meant to be a positional
        if ' ' in arg_string:
            return None

        # it was meant to be an optional but there is no such option
        # in this parser (though it might be a valid option in a subparser)
        return None, arg_string, None

    def _get_option_tuples(self, option_string):
        result = []

        # option strings starting with two prefix characters are only
        # split at the '='
        chars = self.prefix_chars
        if option_string[0] in chars and option_string[1] in chars:
            if '=' in option_string:
                option_prefix, explicit_arg = option_string.split('=', 1)
            else:
                option_prefix = option_string
                explicit_arg = None
            for option_string in self._option_string_actions:
                if option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # single character options can be concatenated with their arguments
        # but multiple character options always have to have their argument
        # separate
        elif option_string[0] in chars and option_string[1] not in chars:
            option_prefix = option_string
            explicit_arg = None
            short_option_prefix = option_string[:2]
            short_explicit_arg = option_string[2:]

            for option_string in self._option_string_actions:
                if option_string == short_option_prefix:
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, short_explicit_arg
                    result.append(tup)
                elif option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # shouldn't ever get here
        else:
            self.error(_('unexpected option string: %s') % option_string)

        # return the collected option tuples
        return result

    def _get_nargs_pattern(self, action):
        # in all examples below, we have to allow for '--' args
        # which are represented as '-' in the pattern
        nargs = action.nargs

        # the default (None) is assumed to be a single argument
        if nargs is None:
            nargs_pattern = '(-*A-*)'

        # allow zero or one arguments
        elif nargs == OPTIONAL:
            nargs_pattern = '(-*A?-*)'

        # allow zero or more arguments
        elif nargs == ZERO_OR_MORE:
            nargs_pattern = '(-*[A-]*)'

        # allow one or more arguments
        elif nargs == ONE_OR_MORE:
            nargs_pattern = '(-*A[A-]*)'

        # allow any number of options or arguments
        elif nargs == REMAINDER:
            nargs_pattern = '([-AO]*)'

        # allow one argument followed by any number of options or arguments
        elif nargs == PARSER:
            nargs_pattern = '(-*A[-AO]*)'

        # all others should be integers
        else:
            nargs_pattern = '(-*%s-*)' % '-*'.join('A' * nargs)

        # if this is an optional action, -- is not allowed
        if action.option_strings:
            nargs_pattern = nargs_pattern.replace('-*', '')
            nargs_pattern = nargs_pattern.replace('-', '')

        # return the pattern
        return nargs_pattern

    # ========================
    # Value conversion methods
    # ========================
    def _get_values(self, action, arg_strings):
        # for everything but PARSER args, strip out '--'
        if action.nargs not in [PARSER, REMAINDER]:
            arg_strings = [s for s in arg_strings if s != '--']

        # optional argument produces a default when not present
        if not arg_strings and action.nargs == OPTIONAL:
            if action.option_strings:
                value = action.const
            else:
                value = action.default
            if isinstance(value, basestring):
                value = self._get_value(action, value)
                self._check_value(action, value)

        # when nargs='*' on a positional, if there were no command-line
        # args, use the default if it is anything other than None
        elif (not arg_strings and action.nargs == ZERO_OR_MORE and
              not action.option_strings):
            if action.default is not None:
                value = action.default
            else:
                value = arg_strings
            self._check_value(action, value)

        # single argument or optional argument produces a single value
        elif len(arg_strings) == 1 and action.nargs in [None, OPTIONAL]:
            arg_string, = arg_strings
            value = self._get_value(action, arg_string)
            self._check_value(action, value)

        # REMAINDER arguments convert all values, checking none
        elif action.nargs == REMAINDER:
            value = [self._get_value(action, v) for v in arg_strings]

        # PARSER arguments convert all values, but check only the first
        elif action.nargs == PARSER:
            value = [self._get_value(action, v) for v in arg_strings]
            self._check_value(action, value[0])

        # all other types of nargs produce a list
        else:
            value = [self._get_value(action, v) for v in arg_strings]
            for v in value:
                self._check_value(action, v)

        # return the converted value
        return value

    def _get_value(self, action, arg_string):
        type_func = self._registry_get('type', action.type, action.type)
        if not _callable(type_func):
            msg = _('%r is not callable')
            raise ArgumentError(action, msg % type_func)

        # convert the value to the appropriate type
        try:
            result = type_func(arg_string)

        # ArgumentTypeErrors indicate errors
        except ArgumentTypeError:
            name = getattr(action.type, '__name__', repr(action.type))
            msg = str(_sys.exc_info()[1])
            raise ArgumentError(action, msg)

        # TypeErrors or ValueErrors also indicate errors
        except (TypeError, ValueError):
            name = getattr(action.type, '__name__', repr(action.type))
            msg = _('invalid %s value: %r')
            raise ArgumentError(action, msg % (name, arg_string))

        # return the converted value
        return result

    def _check_value(self, action, value):
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            tup = value, ', '.join(map(repr, action.choices))
            msg = _('invalid choice: %r (choose from %s)') % tup
            raise ArgumentError(action, msg)

    # =======================
    # Help-formatting methods
    # =======================
    def format_usage(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)
        return formatter.format_help()

    def format_help(self):
        formatter = self._get_formatter()

        # usage
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)

        # description
        formatter.add_text(self.description)

        # positionals, optionals and user-defined groups
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def format_version(self):
        import warnings
        warnings.warn(
            'The format_version method is deprecated -- the "version" '
            'argument to ArgumentParser is no longer supported.',
            DeprecationWarning)
        formatter = self._get_formatter()
        formatter.add_text(self.version)
        return formatter.format_help()

    def _get_formatter(self):
        return self.formatter_class(prog=self.prog)

    # =====================
    # Help-printing methods
    # =====================
    def print_usage(self, file=None):
        if file is None:
            file = _sys.stdout
        self._print_message(self.format_usage(), file)

    def print_help(self, file=None):
        if file is None:
            file = _sys.stdout
        self._print_message(self.format_help(), file)

    def print_version(self, file=None):
        import warnings
        warnings.warn(
            'The print_version method is deprecated -- the "version" '
            'argument to ArgumentParser is no longer supported.',
            DeprecationWarning)
        self._print_message(self.format_version(), file)

    def _print_message(self, message, file=None):
        if message:
            if file is None:
                file = _sys.stderr
            file.write(message)

    # ===============
    # Exiting methods
    # ===============
    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, _sys.stderr)
        _sys.exit(status)

    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage(_sys.stderr)
        self.exit(2, _('%s: error: %s\n') % (self.prog, message))

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import copy
import grp
import inspect
try:
    import argparse
except ImportError: # python 2.6
    from . import argparse_compat as argparse
import os
import pwd
import ssl
import sys
import textwrap

from gunicorn import __version__
from gunicorn.errors import ConfigError
from gunicorn import six
from gunicorn import util

KNOWN_SETTINGS = []
PLATFORM = sys.platform


def wrap_method(func):
    def _wrapped(instance, *args, **kwargs):
        return func(*args, **kwargs)
    return _wrapped


def make_settings(ignore=None):
    settings = {}
    ignore = ignore or ()
    for s in KNOWN_SETTINGS:
        setting = s()
        if setting.name in ignore:
            continue
        settings[setting.name] = setting.copy()
    return settings


class Config(object):

    def __init__(self, usage=None, prog=None):
        self.settings = make_settings()
        self.usage = usage
        self.prog = prog or os.path.basename(sys.argv[0])
        self.env_orig = os.environ.copy()

    def __getattr__(self, name):
        if name not in self.settings:
            raise AttributeError("No configuration setting for: %s" % name)
        return self.settings[name].get()

    def __setattr__(self, name, value):
        if name != "settings" and name in self.settings:
            raise AttributeError("Invalid access!")
        super(Config, self).__setattr__(name, value)

    def set(self, name, value):
        if name not in self.settings:
            raise AttributeError("No configuration setting for: %s" % name)
        self.settings[name].set(value)

    def parser(self):
        kwargs = {
            "usage": self.usage,
            "prog": self.prog
        }
        parser = argparse.ArgumentParser(**kwargs)
        parser.add_argument("-v", "--version",
                action="version", default=argparse.SUPPRESS,
                version="%(prog)s (version " +  __version__ + ")\n",
                help="show program's version number and exit")
        parser.add_argument("args", nargs="*", help=argparse.SUPPRESS)

        keys = sorted(self.settings, key=self.settings.__getitem__)
        for k in keys:
            self.settings[k].add_option(parser)

        return parser

    @property
    def worker_class(self):
        uri = self.settings['worker_class'].get()
        worker_class = util.load_class(uri)
        if hasattr(worker_class, "setup"):
            worker_class.setup()
        return worker_class

    @property
    def workers(self):
        return self.settings['workers'].get()

    @property
    def address(self):
        s = self.settings['bind'].get()
        return [util.parse_address(six.bytes_to_str(bind)) for bind in s]

    @property
    def uid(self):
        return self.settings['user'].get()

    @property
    def gid(self):
        return self.settings['group'].get()

    @property
    def proc_name(self):
        pn = self.settings['proc_name'].get()
        if pn is not None:
            return pn
        else:
            return self.settings['default_proc_name'].get()

    @property
    def logger_class(self):
        uri = self.settings['logger_class'].get()
        if uri == "simple":
            # support the default
            uri = "gunicorn.glogging.Logger"

        logger_class = util.load_class(uri,
                default="gunicorn.glogging.Logger",
                section="gunicorn.loggers")

        if hasattr(logger_class, "install"):
            logger_class.install()
        return logger_class

    @property
    def is_ssl(self):
        return self.certfile or self.keyfile

    @property
    def ssl_options(self):
        opts = {}
        for name, value in self.settings.items():
            if value.section == 'Ssl':
                opts[name] = value.get()
        return opts

    @property
    def env(self):
        raw_env = self.settings['raw_env'].get()
        env = {}

        if not raw_env:
            return env

        for e in raw_env:
            s = six.bytes_to_str(e)
            try:
                k, v = s.split('=', 1)
            except ValueError:
                raise RuntimeError("environment setting %r invalid" % s)

            env[k] = v

        return env


class SettingMeta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(SettingMeta, cls).__new__
        parents = [b for b in bases if isinstance(b, SettingMeta)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        attrs["order"] = len(KNOWN_SETTINGS)
        attrs["validator"] = wrap_method(attrs["validator"])

        new_class = super_new(cls, name, bases, attrs)
        new_class.fmt_desc(attrs.get("desc", ""))
        KNOWN_SETTINGS.append(new_class)
        return new_class

    def fmt_desc(cls, desc):
        desc = textwrap.dedent(desc).strip()
        setattr(cls, "desc", desc)
        setattr(cls, "short", desc.splitlines()[0])


class Setting(object):
    name = None
    value = None
    section = None
    cli = None
    validator = None
    type = None
    meta = None
    action = None
    default = None
    short = None
    desc = None
    nargs = None
    const = None



    def __init__(self):
        if self.default is not None:
            self.set(self.default)

    def add_option(self, parser):
        if not self.cli:
            return
        args = tuple(self.cli)

        help_txt = "%s [%s]" % (self.short, self.default)
        help_txt = help_txt.replace("%", "%%")

        kwargs = {
            "dest": self.name,
            "action": self.action or "store",
            "type": self.type or str,
            "default": None,
            "help": help_txt
        }

        if self.meta is not None:
            kwargs['metavar'] = self.meta

        if kwargs["action"] != "store":
            kwargs.pop("type")

        if self.nargs is not None:
            kwargs["nargs"] = self.nargs

        if self.const is not None:
            kwargs["const"] = self.const

        parser.add_argument(*args, **kwargs)

    def copy(self):
        return copy.copy(self)

    def get(self):
        return self.value

    def set(self, val):
        assert six.callable(self.validator), "Invalid validator: %s" % self.name
        self.value = self.validator(val)

    def __lt__(self, other):
        return (self.section == other.section and
                self.order < other.order)
    __cmp__ = __lt__

Setting = SettingMeta('Setting', (Setting,), {})


def validate_bool(val):
    if isinstance(val, bool):
        return val
    if not isinstance(val, six.string_types):
        raise TypeError("Invalid type for casting: %s" % val)
    if val.lower().strip() == "true":
        return True
    elif val.lower().strip() == "false":
        return False
    else:
        raise ValueError("Invalid boolean: %s" % val)


def validate_dict(val):
    if not isinstance(val, dict):
        raise TypeError("Value is not a dictionary: %s " % val)
    return val


def validate_pos_int(val):
    if not isinstance(val, six.integer_types):
        val = int(val, 0)
    else:
        # Booleans are ints!
        val = int(val)
    if val < 0:
        raise ValueError("Value must be positive: %s" % val)
    return val


def validate_string(val):
    if val is None:
        return None
    if not isinstance(val, six.string_types):
        raise TypeError("Not a string: %s" % val)
    return val.strip()


def validate_list_string(val):
    if not val:
        return []

    # legacy syntax
    if isinstance(val, six.string_types):
        val = [val]

    return [validate_string(v) for v in val]


def validate_string_to_list(val):
    val = validate_string(val)

    if not val:
        return []

    return [v.strip() for v in val.split(",") if v]


def validate_class(val):
    if inspect.isfunction(val) or inspect.ismethod(val):
        val = val()
    if inspect.isclass(val):
        return val
    return validate_string(val)


def validate_callable(arity):
    def _validate_callable(val):
        if isinstance(val, six.string_types):
            try:
                mod_name, obj_name = val.rsplit(".", 1)
            except ValueError:
                raise TypeError("Value '%s' is not import string. "
                                "Format: module[.submodules...].object" % val)
            try:
                mod = __import__(mod_name, fromlist=[obj_name])
                val = getattr(mod, obj_name)
            except ImportError as e:
                raise TypeError(str(e))
            except AttributeError:
                raise TypeError("Can not load '%s' from '%s'"
                    "" % (obj_name, mod_name))
        if not six.callable(val):
            raise TypeError("Value is not six.callable: %s" % val)
        if arity != -1 and arity != len(inspect.getargspec(val)[0]):
            raise TypeError("Value must have an arity of: %s" % arity)
        return val
    return _validate_callable


def validate_user(val):
    if val is None:
        return os.geteuid()
    if isinstance(val, int):
        return val
    elif val.isdigit():
        return int(val)
    else:
        try:
            return pwd.getpwnam(val).pw_uid
        except KeyError:
            raise ConfigError("No such user: '%s'" % val)


def validate_group(val):
    if val is None:
        return os.getegid()

    if isinstance(val, int):
        return val
    elif val.isdigit():
        return int(val)
    else:
        try:
            return grp.getgrnam(val).gr_gid
        except KeyError:
            raise ConfigError("No such group: '%s'" % val)


def validate_post_request(val):
    val = validate_callable(-1)(val)

    largs = len(inspect.getargspec(val)[0])
    if largs == 4:
        return val
    elif largs == 3:
        return lambda worker, req, env, _r: val(worker, req, env)
    elif largs == 2:
        return lambda worker, req, _e, _r: val(worker, req)
    else:
        raise TypeError("Value must have an arity of: 4")


def validate_chdir(val):
    # valid if the value is a string
    val = validate_string(val)

    # transform relative paths
    path = os.path.abspath(os.path.normpath(os.path.join(util.getcwd(), val)))

    # test if the path exists
    if not os.path.exists(path):
        raise ConfigError("can't chdir to %r" % val)

    return path


def validate_file(val):
    if val is None:
        return None

    # valid if the value is a string
    val = validate_string(val)

     # transform relative paths
    path = os.path.abspath(os.path.normpath(os.path.join(util.getcwd(), val)))

    # test if the path exists
    if not os.path.exists(path):
        raise ConfigError("%r not found" % val)

    return path


def get_default_config_file():
    config_path = os.path.join(os.path.abspath(os.getcwd()),
            'gunicorn.conf.py')
    if os.path.exists(config_path):
        return config_path
    return None


# Please remember to run "make html" in docs/ after update "desc" attributes.
class ConfigFile(Setting):
    name = "config"
    section = "Config File"
    cli = ["-c", "--config"]
    meta = "FILE"
    validator = validate_string
    default = None
    desc = """\
        The path to a Gunicorn config file.

        Only has an effect when specified on the command line or as part of an
        application specific configuration.
        """

class Bind(Setting):
    name = "bind"
    action = "append"
    section = "Server Socket"
    cli = ["-b", "--bind"]
    meta = "ADDRESS"
    validator = validate_list_string

    if 'PORT' in os.environ:
        default = ['0.0.0.0:{0}'.format(os.environ.get('PORT'))]
    else:
        default = ['127.0.0.1:8000']

    desc = """\
        The socket to bind.

        A string of the form: 'HOST', 'HOST:PORT', 'unix:PATH'. An IP is a valid
        HOST.

        Multiple addresses can be bound. ex.::

            $ gunicorn -b 127.0.0.1:8000 -b [::1]:8000 test:app

        will bind the `test:app` application on localhost both on ipv6
        and ipv4 interfaces.
        """


class Backlog(Setting):
    name = "backlog"
    section = "Server Socket"
    cli = ["--backlog"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = 2048
    desc = """\
        The maximum number of pending connections.

        This refers to the number of clients that can be waiting to be served.
        Exceeding this number results in the client getting an error when
        attempting to connect. It should only affect servers under significant
        load.

        Must be a positive integer. Generally set in the 64-2048 range.
        """


class Workers(Setting):
    name = "workers"
    section = "Worker Processes"
    cli = ["-w", "--workers"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = int(os.environ.get('WEB_CONCURRENCY', 1))
    desc = """\
        The number of worker process for handling requests.

        A positive integer generally in the 2-4 x $(NUM_CORES) range. You'll
        want to vary this a bit to find the best for your particular
        application's work load.

        By default, the value of the WEB_CONCURRENCY environment variable. If
        it is not defined, the default is 1.
        """


class WorkerClass(Setting):
    name = "worker_class"
    section = "Worker Processes"
    cli = ["-k", "--worker-class"]
    meta = "STRING"
    validator = validate_class
    default = "sync"
    desc = """\
        The type of workers to use.

        The default class (sync) should handle most 'normal' types of
        workloads.  You'll want to read
        http://docs.gunicorn.org/en/latest/design.html for information
        on when you might want to choose one of the other worker
        classes.

        A string referring to one of the following bundled classes:

        * ``sync``
        * ``eventlet`` - Requires eventlet >= 0.9.7
        * ``gevent``   - Requires gevent >= 0.13
        * ``tornado``  - Requires tornado >= 0.2

        Optionally, you can provide your own worker by giving gunicorn a
        python path to a subclass of gunicorn.workers.base.Worker. This
        alternative syntax will load the gevent class:
        ``gunicorn.workers.ggevent.GeventWorker``. Alternatively the syntax
        can also load the gevent class with ``egg:gunicorn#gevent``
        """


class WorkerConnections(Setting):
    name = "worker_connections"
    section = "Worker Processes"
    cli = ["--worker-connections"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = 1000
    desc = """\
        The maximum number of simultaneous clients.

        This setting only affects the Eventlet and Gevent worker types.
        """


class MaxRequests(Setting):
    name = "max_requests"
    section = "Worker Processes"
    cli = ["--max-requests"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = 0
    desc = """\
        The maximum number of requests a worker will process before restarting.

        Any value greater than zero will limit the number of requests a work
        will process before automatically restarting. This is a simple method
        to help limit the damage of memory leaks.

        If this is set to zero (the default) then the automatic worker
        restarts are disabled.
        """


class Timeout(Setting):
    name = "timeout"
    section = "Worker Processes"
    cli = ["-t", "--timeout"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = 30
    desc = """\
        Workers silent for more than this many seconds are killed and restarted.

        Generally set to thirty seconds. Only set this noticeably higher if
        you're sure of the repercussions for sync workers. For the non sync
        workers it just means that the worker process is still communicating and
        is not tied to the length of time required to handle a single request.
        """


class GracefulTimeout(Setting):
    name = "graceful_timeout"
    section = "Worker Processes"
    cli = ["--graceful-timeout"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = 30
    desc = """\
        Timeout for graceful workers restart.

        Generally set to thirty seconds. How max time worker can handle
        request after got restart signal. If the time is up worker will
        be force killed.
        """


class Keepalive(Setting):
    name = "keepalive"
    section = "Worker Processes"
    cli = ["--keep-alive"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = 2
    desc = """\
        The number of seconds to wait for requests on a Keep-Alive connection.

        Generally set in the 1-5 seconds range.
        """


class LimitRequestLine(Setting):
    name = "limit_request_line"
    section = "Security"
    cli = ["--limit-request-line"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = 4094
    desc = """\
        The maximum size of HTTP request line in bytes.

        This parameter is used to limit the allowed size of a client's
        HTTP request-line. Since the request-line consists of the HTTP
        method, URI, and protocol version, this directive places a
        restriction on the length of a request-URI allowed for a request
        on the server. A server needs this value to be large enough to
        hold any of its resource names, including any information that
        might be passed in the query part of a GET request. Value is a number
        from 0 (unlimited) to 8190.

        This parameter can be used to prevent any DDOS attack.
        """


class LimitRequestFields(Setting):
    name = "limit_request_fields"
    section = "Security"
    cli = ["--limit-request-fields"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = 100
    desc = """\
        Limit the number of HTTP headers fields in a request.

        This parameter is used to limit the number of headers in a request to
        prevent DDOS attack. Used with the `limit_request_field_size` it allows
        more safety. By default this value is 100 and can't be larger than
        32768.
        """


class LimitRequestFieldSize(Setting):
    name = "limit_request_field_size"
    section = "Security"
    cli = ["--limit-request-field_size"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = 8190
    desc = """\
        Limit the allowed size of an HTTP request header field.

        Value is a number from 0 (unlimited) to 8190. to set the limit
        on the allowed size of an HTTP request header field.
        """


class Debug(Setting):
    name = "debug"
    section = "Debugging"
    cli = ["--debug"]
    validator = validate_bool
    action = "store_true"
    default = False
    desc = """\
        Turn on debugging in the server.

        **DEPRECATED**: This no functionality was removed after v18.0.
        This option is now a no-op.
        """


class Reload(Setting):
    name = "reload"
    section = 'Debugging'
    cli = ['--reload']
    validator = validate_bool
    action = 'store_true'
    default = False
    desc = '''\
        Restart workers when code changes.

        This setting is intended for development. It will cause workers to be
        restarted whenever application code changes.

        The reloader is incompatible with application preloading. When using a
        paste configuration be sure that the server block does not import any
        application code or the reload will not work as designed.
        '''


class Spew(Setting):
    name = "spew"
    section = "Debugging"
    cli = ["--spew"]
    validator = validate_bool
    action = "store_true"
    default = False
    desc = """\
        Install a trace function that spews every line executed by the server.

        This is the nuclear option.
        """


class ConfigCheck(Setting):
    name = "check_config"
    section = "Debugging"
    cli = ["--check-config", ]
    validator = validate_bool
    action = "store_true"
    default = False
    desc = """\
        Check the configuration..
        """


class PreloadApp(Setting):
    name = "preload_app"
    section = "Server Mechanics"
    cli = ["--preload"]
    validator = validate_bool
    action = "store_true"
    default = False
    desc = """\
        Load application code before the worker processes are forked.

        By preloading an application you can save some RAM resources as well as
        speed up server boot times. Although, if you defer application loading
        to each worker process, you can reload your application code easily by
        restarting workers.
        """


class Chdir(Setting):
    name = "chdir"
    section = "Server Mechanics"
    cli = ["--chdir"]
    validator = validate_chdir
    default = util.getcwd()
    desc = """\
        Chdir to specified directory before apps loading.
        """


class Daemon(Setting):
    name = "daemon"
    section = "Server Mechanics"
    cli = ["-D", "--daemon"]
    validator = validate_bool
    action = "store_true"
    default = False
    desc = """\
        Daemonize the Gunicorn process.

        Detaches the server from the controlling terminal and enters the
        background.
        """

class Env(Setting):
    name = "raw_env"
    action = "append"
    section = "Server Mechanics"
    cli = ["-e", "--env"]
    meta = "ENV"
    validator = validate_list_string
    default = []

    desc = """\
        Set environment variable (key=value).

        Pass variables to the execution environment. Ex.::

            $ gunicorn -b 127.0.0.1:8000 --env FOO=1 test:app

        and test for the foo variable environment in your application.
        """


class Pidfile(Setting):
    name = "pidfile"
    section = "Server Mechanics"
    cli = ["-p", "--pid"]
    meta = "FILE"
    validator = validate_string
    default = None
    desc = """\
        A filename to use for the PID file.

        If not set, no PID file will be written.
        """

class WorkerTmpDir(Setting):
    name = "worker_tmp_dir"
    section = "Server Mechanics"
    cli = ["--worker-tmp-dir"]
    meta = "DIR"
    validator = validate_string
    default = None
    desc = """\
        A directory to use for the worker heartbeat temporary file.

        If not set, the default temporary directory will be used.
        """

class User(Setting):
    name = "user"
    section = "Server Mechanics"
    cli = ["-u", "--user"]
    meta = "USER"
    validator = validate_user
    default = os.geteuid()
    desc = """\
        Switch worker processes to run as this user.

        A valid user id (as an integer) or the name of a user that can be
        retrieved with a call to pwd.getpwnam(value) or None to not change
        the worker process user.
        """


class Group(Setting):
    name = "group"
    section = "Server Mechanics"
    cli = ["-g", "--group"]
    meta = "GROUP"
    validator = validate_group
    default = os.getegid()
    desc = """\
        Switch worker process to run as this group.

        A valid group id (as an integer) or the name of a user that can be
        retrieved with a call to pwd.getgrnam(value) or None to not change
        the worker processes group.
        """


class Umask(Setting):
    name = "umask"
    section = "Server Mechanics"
    cli = ["-m", "--umask"]
    meta = "INT"
    validator = validate_pos_int
    type = int
    default = 0
    desc = """\
        A bit mask for the file mode on files written by Gunicorn.

        Note that this affects unix socket permissions.

        A valid value for the os.umask(mode) call or a string compatible with
        int(value, 0) (0 means Python guesses the base, so values like "0",
        "0xFF", "0022" are valid for decimal, hex, and octal representations)
        """


class TmpUploadDir(Setting):
    name = "tmp_upload_dir"
    section = "Server Mechanics"
    meta = "DIR"
    validator = validate_string
    default = None
    desc = """\
        Directory to store temporary request data as they are read.

        This may disappear in the near future.

        This path should be writable by the process permissions set for Gunicorn
        workers. If not specified, Gunicorn will choose a system generated
        temporary directory.
        """


class SecureSchemeHeader(Setting):
    name = "secure_scheme_headers"
    section = "Server Mechanics"
    validator = validate_dict
    default = {
        "X-FORWARDED-PROTOCOL": "ssl",
        "X-FORWARDED-PROTO": "https",
        "X-FORWARDED-SSL": "on"
    }
    desc = """\

        A dictionary containing headers and values that the front-end proxy
        uses to indicate HTTPS requests. These tell gunicorn to set
        wsgi.url_scheme to "https", so your application can tell that the
        request is secure.

        The dictionary should map upper-case header names to exact string
        values. The value comparisons are case-sensitive, unlike the header
        names, so make sure they're exactly what your front-end proxy sends
        when handling HTTPS requests.

        It is important that your front-end proxy configuration ensures that
        the headers defined here can not be passed directly from the client.
        """


class ForwardedAllowIPS(Setting):
    name = "forwarded_allow_ips"
    section = "Server Mechanics"
    cli = ["--forwarded-allow-ips"]
    meta = "STRING"
    validator = validate_string_to_list
    default = "127.0.0.1"
    desc = """\
        Front-end's IPs from which allowed to handle set secure headers.
        (comma separate).

        Set to "*" to disable checking of Front-end IPs (useful for setups
        where you don't know in advance the IP address of Front-end, but
        you still trust the environment)
        """


class AccessLog(Setting):
    name = "accesslog"
    section = "Logging"
    cli = ["--access-logfile"]
    meta = "FILE"
    validator = validate_string
    default = None
    desc = """\
        The Access log file to write to.

        "-" means log to stderr.
        """


class AccessLogFormat(Setting):
    name = "access_log_format"
    section = "Logging"
    cli = ["--access-logformat"]
    meta = "STRING"
    validator = validate_string
    default = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
    desc = """\
        The access log format.

        ==========  ===========
        Identifier  Description
        ==========  ===========
        h           remote address
        l           '-'
        u           currently '-', may be user name in future releases
        t           date of the request
        r           status line (e.g. ``GET / HTTP/1.1``)
        s           status
        b           response length or '-'
        f           referer
        a           user agent
        T           request time in seconds
        D           request time in microseconds
        L           request time in decimal seconds
        p           process ID
        {Header}i   request header
        {Header}o   response header
        ==========  ===========
        """


class ErrorLog(Setting):
    name = "errorlog"
    section = "Logging"
    cli = ["--error-logfile", "--log-file"]
    meta = "FILE"
    validator = validate_string
    default = None
    desc = """\
        The Error log file to write to.

        "-" means log to stderr.
        """


class Loglevel(Setting):
    name = "loglevel"
    section = "Logging"
    cli = ["--log-level"]
    meta = "LEVEL"
    validator = validate_string
    default = "info"
    desc = """\
        The granularity of Error log outputs.

        Valid level names are:

        * debug
        * info
        * warning
        * error
        * critical
        """


class LoggerClass(Setting):
    name = "logger_class"
    section = "Logging"
    cli = ["--logger-class"]
    meta = "STRING"
    validator = validate_class
    default = "gunicorn.glogging.Logger"
    desc = """\
        The logger you want to use to log events in gunicorn.

        The default class (``gunicorn.glogging.Logger``) handle most of
        normal usages in logging. It provides error and access logging.

        You can provide your own worker by giving gunicorn a
        python path to a subclass like gunicorn.glogging.Logger.
        Alternatively the syntax can also load the Logger class
        with `egg:gunicorn#simple`
        """


class LogConfig(Setting):
    name = "logconfig"
    section = "Logging"
    cli = ["--log-config"]
    meta = "FILE"
    validator = validate_string
    default = None
    desc = """\
    The log config file to use.
    Gunicorn uses the standard Python logging module's Configuration
    file format.
    """


class SyslogTo(Setting):
    name = "syslog_addr"
    section = "Logging"
    cli = ["--log-syslog-to"]
    meta = "SYSLOG_ADDR"
    validator = validate_string

    if PLATFORM == "darwin":
        default = "unix:///var/run/syslog"
    elif PLATFORM in ('freebsd', 'dragonfly', ):
        default = "unix:///var/run/log"
    elif PLATFORM == "openbsd":
        default = "unix:///dev/log"
    else:
        default = "udp://localhost:514"

    desc = """\
    Address to send syslog messages.

    Address is a string of the form:

    * 'unix://PATH#TYPE' : for unix domain socket. TYPE can be 'stream'
      for the stream driver or 'dgram' for the dgram driver.
      'stream' is the default.
    * 'udp://HOST:PORT' : for UDP sockets
    * 'tcp://HOST:PORT' : for TCP sockets

    """


class Syslog(Setting):
    name = "syslog"
    section = "Logging"
    cli = ["--log-syslog"]
    validator = validate_bool
    action = 'store_true'
    default = False
    desc = """\
    Send *Gunicorn* logs to syslog.
    """


class SyslogPrefix(Setting):
    name = "syslog_prefix"
    section = "Logging"
    cli = ["--log-syslog-prefix"]
    meta = "SYSLOG_PREFIX"
    validator = validate_string
    default = None
    desc = """\
    makes gunicorn use the parameter as program-name in the syslog entries.

    All entries will be prefixed by gunicorn.<prefix>. By default the program
    name is the name of the process.
    """


class SyslogFacility(Setting):
    name = "syslog_facility"
    section = "Logging"
    cli = ["--log-syslog-facility"]
    meta = "SYSLOG_FACILITY"
    validator = validate_string
    default = "user"
    desc = """\
    Syslog facility name
    """


class EnableStdioInheritance(Setting):
    name = "enable_stdio_inheritance"
    section = "Logging"
    cli = ["-R", "--enable-stdio-inheritance"]
    validator = validate_bool
    default = False
    action = "store_true"
    desc = """\
    Enable stdio inheritance

    Enable inheritance for stdio file descriptors in daemon mode.

    Note: To disable the python stdout buffering, you can to set the user
    environment variable ``PYTHONUNBUFFERED`` .
    """


class Procname(Setting):
    name = "proc_name"
    section = "Process Naming"
    cli = ["-n", "--name"]
    meta = "STRING"
    validator = validate_string
    default = None
    desc = """\
        A base to use with setproctitle for process naming.

        This affects things like ``ps`` and ``top``. If you're going to be
        running more than one instance of Gunicorn you'll probably want to set a
        name to tell them apart. This requires that you install the setproctitle
        module.

        It defaults to 'gunicorn'.
        """


class DefaultProcName(Setting):
    name = "default_proc_name"
    section = "Process Naming"
    validator = validate_string
    default = "gunicorn"
    desc = """\
        Internal setting that is adjusted for each type of application.
        """


class DjangoSettings(Setting):
    name = "django_settings"
    section = "Django"
    cli = ["--settings"]
    meta = "STRING"
    validator = validate_string
    default = None
    desc = """\
        The Python path to a Django settings module. (deprecated)

        e.g. 'myproject.settings.main'. If this isn't provided, the
        DJANGO_SETTINGS_MODULE environment variable will be used.

        **DEPRECATED**: use the --env argument instead.
        """


class PythonPath(Setting):
    name = "pythonpath"
    section = "Server Mechanics"
    cli = ["--pythonpath"]
    meta = "STRING"
    validator = validate_string
    default = None
    desc = """\
        A directory to add to the Python path.

        e.g.
        '/home/djangoprojects/myproject'.
        """


class Paste(Setting):
    name = "paste"
    section = "Server Mechanics"
    cli = ["--paste", "--paster"]
    meta = "STRING"
    validator = validate_string
    default = None
    desc = """\
        Load a paste.deploy config file. The argument may contain a "#" symbol
        followed by the name of an app section from the config file, e.g.
        "production.ini#admin".

        At this time, using alternate server blocks is not supported. Use the
        command line arguments to control server configuration instead.
        """


class OnStarting(Setting):
    name = "on_starting"
    section = "Server Hooks"
    validator = validate_callable(1)
    type = six.callable

    def on_starting(server):
        pass
    default = staticmethod(on_starting)
    desc = """\
        Called just before the master process is initialized.

        The callable needs to accept a single instance variable for the Arbiter.
        """


class OnReload(Setting):
    name = "on_reload"
    section = "Server Hooks"
    validator = validate_callable(1)
    type = six.callable

    def on_reload(server):
        pass
    default = staticmethod(on_reload)
    desc = """\
        Called to recycle workers during a reload via SIGHUP.

        The callable needs to accept a single instance variable for the Arbiter.
        """


class WhenReady(Setting):
    name = "when_ready"
    section = "Server Hooks"
    validator = validate_callable(1)
    type = six.callable

    def when_ready(server):
        pass
    default = staticmethod(when_ready)
    desc = """\
        Called just after the server is started.

        The callable needs to accept a single instance variable for the Arbiter.
        """


class Prefork(Setting):
    name = "pre_fork"
    section = "Server Hooks"
    validator = validate_callable(2)
    type = six.callable

    def pre_fork(server, worker):
        pass
    default = staticmethod(pre_fork)
    desc = """\
        Called just before a worker is forked.

        The callable needs to accept two instance variables for the Arbiter and
        new Worker.
        """


class Postfork(Setting):
    name = "post_fork"
    section = "Server Hooks"
    validator = validate_callable(2)
    type = six.callable

    def post_fork(server, worker):
        pass
    default = staticmethod(post_fork)
    desc = """\
        Called just after a worker has been forked.

        The callable needs to accept two instance variables for the Arbiter and
        new Worker.
        """


class PostWorkerInit(Setting):
    name = "post_worker_init"
    section = "Server Hooks"
    validator = validate_callable(1)
    type = six.callable

    def post_worker_init(worker):
        pass

    default = staticmethod(post_worker_init)
    desc = """\
        Called just after a worker has initialized the application.

        The callable needs to accept one instance variable for the initialized
        Worker.
        """

class WorkerInt(Setting):
    name = "worker_int"
    section = "Server Hooks"
    validator = validate_callable(1)
    type = six.callable

    def worker_int(worker):
        pass

    default = staticmethod(worker_int)
    desc = """\
        Called just after a worker exited on SIGINT or SIGTERM.

        The callable needs to accept one instance variable for the initialized
        Worker.
        """


class PreExec(Setting):
    name = "pre_exec"
    section = "Server Hooks"
    validator = validate_callable(1)
    type = six.callable

    def pre_exec(server):
        pass
    default = staticmethod(pre_exec)
    desc = """\
        Called just before a new master process is forked.

        The callable needs to accept a single instance variable for the Arbiter.
        """


class PreRequest(Setting):
    name = "pre_request"
    section = "Server Hooks"
    validator = validate_callable(2)
    type = six.callable

    def pre_request(worker, req):
        worker.log.debug("%s %s" % (req.method, req.path))
    default = staticmethod(pre_request)
    desc = """\
        Called just before a worker processes the request.

        The callable needs to accept two instance variables for the Worker and
        the Request.
        """


class PostRequest(Setting):
    name = "post_request"
    section = "Server Hooks"
    validator = validate_post_request
    type = six.callable

    def post_request(worker, req, environ, resp):
        pass
    default = staticmethod(post_request)
    desc = """\
        Called after a worker processes the request.

        The callable needs to accept two instance variables for the Worker and
        the Request.
        """


class WorkerExit(Setting):
    name = "worker_exit"
    section = "Server Hooks"
    validator = validate_callable(2)
    type = six.callable

    def worker_exit(server, worker):
        pass
    default = staticmethod(worker_exit)
    desc = """\
        Called just after a worker has been exited.

        The callable needs to accept two instance variables for the Arbiter and
        the just-exited Worker.
        """


class NumWorkersChanged(Setting):
    name = "nworkers_changed"
    section = "Server Hooks"
    validator = validate_callable(3)
    type = six.callable

    def nworkers_changed(server, new_value, old_value):
        pass
    default = staticmethod(nworkers_changed)
    desc = """\
        Called just after num_workers has been changed.

        The callable needs to accept an instance variable of the Arbiter and
        two integers of number of workers after and before change.

        If the number of workers is set for the first time, old_value would be
        None.
        """


class ProxyProtocol(Setting):
    name = "proxy_protocol"
    section = "Server Mechanics"
    cli = ["--proxy-protocol"]
    validator = validate_bool
    default = False
    action = "store_true"
    desc = """\
        Enable detect PROXY protocol (PROXY mode).

        Allow using Http and Proxy together. It's may be useful for work with
        stunnel as https frondend and gunicorn as http server.

        PROXY protocol: http://haproxy.1wt.eu/download/1.5/doc/proxy-protocol.txt

        Example for stunnel config::

            [https]
            protocol = proxy
            accept  = 443
            connect = 80
            cert = /etc/ssl/certs/stunnel.pem
            key = /etc/ssl/certs/stunnel.key
        """


class ProxyAllowFrom(Setting):
    name = "proxy_allow_ips"
    section = "Server Mechanics"
    cli = ["--proxy-allow-from"]
    validator = validate_string_to_list
    default = "127.0.0.1"
    desc = """\
        Front-end's IPs from which allowed accept proxy requests (comma separate).

        Set to "*" to disable checking of Front-end IPs (useful for setups
        where you don't know in advance the IP address of Front-end, but
        you still trust the environment)
        """


class KeyFile(Setting):
    name = "keyfile"
    section = "Ssl"
    cli = ["--keyfile"]
    meta = "FILE"
    validator = validate_string
    default = None
    desc = """\
    SSL key file
    """


class CertFile(Setting):
    name = "certfile"
    section = "Ssl"
    cli = ["--certfile"]
    meta = "FILE"
    validator = validate_string
    default = None
    desc = """\
    SSL certificate file
    """

class SSLVersion(Setting):
    name = "ssl_version"
    section = "Ssl"
    cli = ["--ssl-version"]
    validator = validate_pos_int
    default = ssl.PROTOCOL_TLSv1
    desc = """\
    SSL version to use (see stdlib ssl module's)
    """

class CertReqs(Setting):
    name = "cert_reqs"
    section = "Ssl"
    cli = ["--cert-reqs"]
    validator = validate_pos_int
    default = ssl.CERT_NONE
    desc = """\
    Whether client certificate is required (see stdlib ssl module's)
    """

class CACerts(Setting):
    name = "ca_certs"
    section = "Ssl"
    cli = ["--ca-certs"]
    meta = "FILE"
    validator = validate_string
    default = None
    desc = """\
    CA certificates file
    """

class SuppressRaggedEOFs(Setting):
    name = "suppress_ragged_eofs"
    section = "Ssl"
    cli = ["--suppress-ragged-eofs"]
    action = "store_true"
    default = True
    validator = validate_bool
    desc = """\
    Suppress ragged EOFs (see stdlib ssl module's)
    """

class DoHandshakeOnConnect(Setting):
    name = "do_handshake_on_connect"
    section = "Ssl"
    cli = ["--do-handshake-on-connect"]
    validator = validate_bool
    action = "store_true"
    default = False
    desc = """\
    Whether to perform SSL handshake on socket connect (see stdlib ssl module's)
    """

if sys.version_info >= (2, 7):
    class Ciphers(Setting):
        name = "ciphers"
        section = "Ssl"
        cli = ["--ciphers"]
        validator = validate_string
        default = 'TLSv1'
        desc = """\
        Ciphers to use (see stdlib ssl module's)
        """

########NEW FILE########
__FILENAME__ = debug
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

"""The debug module contains utilities and functions for better
debugging Gunicorn."""

import sys
import linecache
import re
import inspect

__all__ = ['spew', 'unspew']

_token_spliter = re.compile('\W+')


class Spew(object):
    """
    """
    def __init__(self, trace_names=None, show_values=True):
        self.trace_names = trace_names
        self.show_values = show_values

    def __call__(self, frame, event, arg):
        if event == 'line':
            lineno = frame.f_lineno
            if '__file__' in frame.f_globals:
                filename = frame.f_globals['__file__']
                if (filename.endswith('.pyc') or
                    filename.endswith('.pyo')):
                    filename = filename[:-1]
                name = frame.f_globals['__name__']
                line = linecache.getline(filename, lineno)
            else:
                name = '[unknown]'
                try:
                    src = inspect.getsourcelines(frame)
                    line = src[lineno]
                except IOError:
                    line = 'Unknown code named [%s].  VM instruction #%d' % (
                        frame.f_code.co_name, frame.f_lasti)
            if self.trace_names is None or name in self.trace_names:
                print('%s:%s: %s' % (name, lineno, line.rstrip()))
                if not self.show_values:
                    return self
                details = []
                tokens = _token_spliter.split(line)
                for tok in tokens:
                    if tok in frame.f_globals:
                        details.append('%s=%r' % (tok, frame.f_globals[tok]))
                    if tok in frame.f_locals:
                        details.append('%s=%r' % (tok, frame.f_locals[tok]))
                if details:
                    print("\t%s" % ' '.join(details))
        return self


def spew(trace_names=None, show_values=False):
    """Install a trace hook which writes incredibly detailed logs
    about what code is being executed to stdout.
    """
    sys.settrace(Spew(trace_names, show_values))


def unspew():
    """Remove the trace hook installed by spew.
    """
    sys.settrace(None)

########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.


class HaltServer(BaseException):
    def __init__(self, reason, exit_status=1):
        self.reason = reason
        self.exit_status = exit_status

    def __str__(self):
        return "<HaltServer %r %d>" % (self.reason, self.exit_status)


class ConfigError(BaseException):
    """ Exception raised on config error """


class AppImportError(Exception):
    """ Exception raised when loading an application """

########NEW FILE########
__FILENAME__ = glogging
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import time
import logging
logging.Logger.manager.emittedNoHandlerWarning = 1
from logging.config import fileConfig
import os
import socket
import sys
import traceback

from gunicorn import util
from gunicorn.six import string_types


# syslog facility codes
SYSLOG_FACILITIES = {
        "auth":     4,
        "authpriv": 10,
        "cron":     9,
        "daemon":   3,
        "ftp":      11,
        "kern":     0,
        "lpr":      6,
        "mail":     2,
        "news":     7,
        "security": 4,  #  DEPRECATED
        "syslog":   5,
        "user":     1,
        "uucp":     8,
        "local0":   16,
        "local1":   17,
        "local2":   18,
        "local3":   19,
        "local4":   20,
        "local5":   21,
        "local6":   22,
        "local7":   23
        }


CONFIG_DEFAULTS = dict(
        version=1,
        disable_existing_loggers=False,

        loggers={
            "root": {"level": "INFO", "handlers": ["console"]},
            "gunicorn.error": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": True,
                "qualname": "gunicorn.error"
            }
        },
        handlers={
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "generic",
                "stream": "sys.stdout"
            }
        },
        formatters={
            "generic": {
                "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "class": "logging.Formatter"
            }
        }
)


def loggers():
    """ get list of all loggers """
    root = logging.root
    existing = root.manager.loggerDict.keys()
    return [logging.getLogger(name) for name in existing]


class SafeAtoms(dict):

    def __init__(self, atoms):
        dict.__init__(self)
        for key, value in atoms.items():
            if isinstance(value, string_types):
                self[key] = value.replace('"', '\\"')
            else:
                self[key] = value

    def __getitem__(self, k):
        if k.startswith("{"):
            kl = k.lower()
            if kl in self:
                return super(SafeAtoms, self).__getitem__(kl)
            else:
                return "-"
        if k in self:
            return super(SafeAtoms, self).__getitem__(k)
        else:
            return '-'


def parse_syslog_address(addr):

    if addr.startswith("unix://"):
        sock_type = socket.SOCK_STREAM

        # are we using a different socket type?
        parts = addr.split("#", 1)
        if len(parts) == 2:
            addr = parts[0]
            if parts[1] == "dgram":
                sock_type = socket.SOCK_DGRAM

        return (sock_type, addr.split("unix://")[1])

    if addr.startswith("udp://"):
        addr = addr.split("udp://")[1]
        socktype = socket.SOCK_DGRAM
    elif addr.startswith("tcp://"):
        addr = addr.split("tcp://")[1]
        socktype = socket.SOCK_STREAM
    else:
        raise RuntimeError("invalid syslog address")

    if '[' in addr and ']' in addr:
        host = addr.split(']')[0][1:].lower()
    elif ':' in addr:
        host = addr.split(':')[0].lower()
    elif addr == "":
        host = "localhost"
    else:
        host = addr.lower()

    addr = addr.split(']')[-1]
    if ":" in addr:
        port = addr.split(':', 1)[1]
        if not port.isdigit():
            raise RuntimeError("%r is not a valid port number." % port)
        port = int(port)
    else:
        port = 514

    return (socktype, (host, port))


class Logger(object):

    LOG_LEVELS = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG
    }

    error_fmt = r"%(asctime)s [%(process)d] [%(levelname)s] %(message)s"
    datefmt = r"%Y-%m-%d %H:%M:%S"

    access_fmt = "%(message)s"
    syslog_fmt = "[%(process)d] %(message)s"

    atoms_wrapper_class = SafeAtoms

    def __init__(self, cfg):
        self.error_log = logging.getLogger("gunicorn.error")
        self.error_log.propagate = False
        self.access_log = logging.getLogger("gunicorn.access")
        self.access_log.propagate = False
        self.error_handlers = []
        self.access_handlers = []
        self.cfg = cfg
        self.setup(cfg)

    def setup(self, cfg):
        loglevel = self.LOG_LEVELS.get(cfg.loglevel.lower(), logging.INFO)
        self.error_log.setLevel(loglevel)
        self.access_log.setLevel(logging.INFO)

        # set gunicorn.error handler
        self._set_handler(self.error_log, cfg.errorlog,
                logging.Formatter(self.error_fmt, self.datefmt))

        # set gunicorn.access handler
        if cfg.accesslog is not None:
            self._set_handler(self.access_log, cfg.accesslog,
                fmt=logging.Formatter(self.access_fmt))

        # set syslog handler
        if cfg.syslog:
            self._set_syslog_handler(
                self.error_log, cfg, self.syslog_fmt, "error"
            )
            self._set_syslog_handler(
                self.access_log, cfg, self.syslog_fmt, "access"
            )

        if cfg.logconfig:
            if os.path.exists(cfg.logconfig):
                fileConfig(cfg.logconfig, defaults=CONFIG_DEFAULTS,
                        disable_existing_loggers=False)
            else:
                raise RuntimeError("Error: log config '%s' not found" %
                        cfg.logconfig)

    def critical(self, msg, *args, **kwargs):
        self.error_log.critical(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.error_log.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.error_log.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.error_log.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.error_log.debug(msg, *args, **kwargs)

    def exception(self, msg, *args):
        self.error_log.exception(msg, *args)

    def log(self, lvl, msg, *args, **kwargs):
        if isinstance(lvl, string_types):
            lvl = self.LOG_LEVELS.get(lvl.lower(), logging.INFO)
        self.error_log.log(lvl, msg, *args, **kwargs)

    def atoms(self, resp, req, environ, request_time):
        """ Gets atoms for log formating.
        """
        status = resp.status.split(None, 1)[0]
        atoms = {
            'h': environ.get('REMOTE_ADDR', '-'),
            'l': '-',
            'u': '-',  # would be cool to get username from basic auth header
            't': self.now(),
            'r': "%s %s %s" % (environ['REQUEST_METHOD'],
                environ['RAW_URI'], environ["SERVER_PROTOCOL"]),
            's': status,
            'b': resp.response_length and str(resp.response_length) or '-',
            'f': environ.get('HTTP_REFERER', '-'),
            'a': environ.get('HTTP_USER_AGENT', '-'),
            'T': request_time.seconds,
            'D': (request_time.seconds*1000000) + request_time.microseconds,
            'L': "%d.%06d" % (request_time.seconds, request_time.microseconds),
            'p': "<%s>" % os.getpid()
        }

        # add request headers
        if hasattr(req, 'headers'):
            req_headers = req.headers
        else:
            req_headers = req

        atoms.update(dict([("{%s}i" % k.lower(), v) for k, v in req_headers]))

        # add response headers
        atoms.update(dict([("{%s}o" % k.lower(), v) for k, v in resp.headers]))

        return atoms

    def access(self, resp, req, environ, request_time):
        """ See http://httpd.apache.org/docs/2.0/logs.html#combined
        for format details
        """

        if not self.cfg.accesslog and not self.cfg.logconfig:
            return

        # wrap atoms:
        # - make sure atoms will be test case insensitively
        # - if atom doesn't exist replace it by '-'
        safe_atoms = self.atoms_wrapper_class(self.atoms(resp, req, environ,
            request_time))

        try:
            self.access_log.info(self.cfg.access_log_format % safe_atoms)
        except:
            self.error(traceback.format_exc())

    def now(self):
        """ return date in Apache Common Log Format """
        return time.strftime('[%d/%b/%Y:%H:%M:%S %z]')

    def reopen_files(self):
        for log in loggers():
            for handler in log.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.acquire()
                    try:
                        if handler.stream:
                            handler.stream.close()
                            handler.stream = open(handler.baseFilename,
                                    handler.mode)
                    finally:
                        handler.release()

    def close_on_exec(self):
        for log in loggers():
            for handler in log.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.acquire()
                    try:
                        if handler.stream:
                            util.close_on_exec(handler.stream.fileno())
                    finally:
                        handler.release()

    def _get_gunicorn_handler(self, log):
        for h in log.handlers:
            if getattr(h, "_gunicorn", False) == True:
                return h

    def _set_handler(self, log, output, fmt):
        # remove previous gunicorn log handler
        h = self._get_gunicorn_handler(log)
        if h:
            log.handlers.remove(h)

        if output is not None:
            if output == "-":
                h = logging.StreamHandler()
            else:
                util.check_is_writeable(output)
                h = logging.FileHandler(output)

            h.setFormatter(fmt)
            h._gunicorn = True
            log.addHandler(h)

    def _set_syslog_handler(self, log, cfg, fmt, name):
        # setup format
        if not cfg.syslog_prefix:
            prefix = cfg.proc_name.replace(":", ".")
        else:
            prefix = cfg.syslog_prefix

        prefix = "gunicorn.%s.%s" % (prefix, name)

        # set format
        fmt = logging.Formatter(r"%s: %s" % (prefix, fmt))

        # syslog facility
        try:
            facility = SYSLOG_FACILITIES[cfg.syslog_facility.lower()]
        except KeyError:
            raise RuntimeError("unknown facility name")

        # parse syslog address
        socktype, addr = parse_syslog_address(cfg.syslog_addr)

        # finally setup the syslog handler
        if sys.version_info >= (2, 7):
            h = logging.handlers.SysLogHandler(address=addr,
                    facility=facility, socktype=socktype)
        else:
            # socktype is only supported in 2.7 and sup
            # fix issue #541
            h = logging.handlers.SysLogHandler(address=addr,
                    facility=facility)

        h.setFormatter(fmt)
        h._gunicorn = True
        log.addHandler(h)

########NEW FILE########
__FILENAME__ = body
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

from gunicorn.http.errors import (NoMoreData, ChunkMissingTerminator,
        InvalidChunkSize)
from gunicorn import six


class ChunkedReader(object):
    def __init__(self, req, unreader):
        self.req = req
        self.parser = self.parse_chunked(unreader)
        self.buf = six.BytesIO()

    def read(self, size):
        if not isinstance(size, six.integer_types):
            raise TypeError("size must be an integral type")
        if size < 0:
            raise ValueError("Size must be positive.")
        if size == 0:
            return b""

        if self.parser:
            while self.buf.tell() < size:
                try:
                    self.buf.write(six.next(self.parser))
                except StopIteration:
                    self.parser = None
                    break

        data = self.buf.getvalue()
        ret, rest = data[:size], data[size:]
        self.buf = six.BytesIO()
        self.buf.write(rest)
        return ret

    def parse_trailers(self, unreader, data):
        buf = six.BytesIO()
        buf.write(data)

        idx = buf.getvalue().find(b"\r\n\r\n")
        done = buf.getvalue()[:2] == b"\r\n"
        while idx < 0 and not done:
            self.get_data(unreader, buf)
            idx = buf.getvalue().find(b"\r\n\r\n")
            done = buf.getvalue()[:2] == b"\r\n"
        if done:
            unreader.unread(buf.getvalue()[2:])
            return b""
        self.req.trailers = self.req.parse_headers(buf.getvalue()[:idx])
        unreader.unread(buf.getvalue()[idx + 4:])

    def parse_chunked(self, unreader):
        (size, rest) = self.parse_chunk_size(unreader)
        while size > 0:
            while size > len(rest):
                size -= len(rest)
                yield rest
                rest = unreader.read()
                if not rest:
                    raise NoMoreData()
            yield rest[:size]
            # Remove \r\n after chunk
            rest = rest[size:]
            while len(rest) < 2:
                rest += unreader.read()
            if rest[:2] != b'\r\n':
                raise ChunkMissingTerminator(rest[:2])
            (size, rest) = self.parse_chunk_size(unreader, data=rest[2:])

    def parse_chunk_size(self, unreader, data=None):
        buf = six.BytesIO()
        if data is not None:
            buf.write(data)

        idx = buf.getvalue().find(b"\r\n")
        while idx < 0:
            self.get_data(unreader, buf)
            idx = buf.getvalue().find(b"\r\n")

        data = buf.getvalue()
        line, rest_chunk = data[:idx], data[idx + 2:]

        chunk_size = line.split(b";", 1)[0].strip()
        try:
            chunk_size = int(chunk_size, 16)
        except ValueError:
            raise InvalidChunkSize(chunk_size)

        if chunk_size == 0:
            try:
                self.parse_trailers(unreader, rest_chunk)
            except NoMoreData:
                pass
            return (0, None)
        return (chunk_size, rest_chunk)

    def get_data(self, unreader, buf):
        data = unreader.read()
        if not data:
            raise NoMoreData()
        buf.write(data)


class LengthReader(object):
    def __init__(self, unreader, length):
        self.unreader = unreader
        self.length = length

    def read(self, size):
        if not isinstance(size, six.integer_types):
            raise TypeError("size must be an integral type")

        size = min(self.length, size)
        if size < 0:
            raise ValueError("Size must be positive.")
        if size == 0:
            return b""

        buf = six.BytesIO()
        data = self.unreader.read()
        while data:
            buf.write(data)
            if buf.tell() >= size:
                break
            data = self.unreader.read()

        buf = buf.getvalue()
        ret, rest = buf[:size], buf[size:]
        self.unreader.unread(rest)
        self.length -= size
        return ret


class EOFReader(object):
    def __init__(self, unreader):
        self.unreader = unreader
        self.buf = six.BytesIO()
        self.finished = False

    def read(self, size):
        if not isinstance(size, six.integer_types):
            raise TypeError("size must be an integral type")
        if size < 0:
            raise ValueError("Size must be positive.")
        if size == 0:
            return b""

        if self.finished:
            data = self.buf.getvalue()
            ret, rest = data[:size], data[size:]
            self.buf = six.BytesIO()
            self.buf.write(rest)
            return ret

        data = self.unreader.read()
        while data:
            self.buf.write(data)
            if self.buf.tell() > size:
                break
            data = self.unreader.read()

        if not data:
            self.finished = True

        data = self.buf.getvalue()
        ret, rest = data[:size], data[size:]
        self.buf = six.BytesIO()
        self.buf.write(rest)
        return ret


class Body(object):
    def __init__(self, reader):
        self.reader = reader
        self.buf = six.BytesIO()

    def __iter__(self):
        return self

    def __next__(self):
        ret = self.readline()
        if not ret:
            raise StopIteration()
        return ret
    next = __next__

    def getsize(self, size):
        if size is None:
            return six.MAXSIZE
        elif not isinstance(size, six.integer_types):
            raise TypeError("size must be an integral type")
        elif size < 0:
            return six.MAXSIZE
        return size

    def read(self, size=None):
        size = self.getsize(size)
        if size == 0:
            return b""

        if size < self.buf.tell():
            data = self.buf.getvalue()
            ret, rest = data[:size], data[size:]
            self.buf = six.BytesIO()
            self.buf.write(rest)
            return ret

        while size > self.buf.tell():
            data = self.reader.read(1024)
            if not len(data):
                break
            self.buf.write(data)

        data = self.buf.getvalue()
        ret, rest = data[:size], data[size:]
        self.buf = six.BytesIO()
        self.buf.write(rest)
        return ret

    def readline(self, size=None):
        size = self.getsize(size)
        if size == 0:
            return b""

        data = self.buf.getvalue()
        self.buf = six.BytesIO()

        ret = []
        while 1:
            idx = data.find(b"\n", 0, size)
            idx = idx + 1 if idx >= 0 else size if len(data) >= size else 0
            if idx:
                ret.append(data[:idx])
                self.buf.write(data[idx:])
                break

            ret.append(data)
            size -= len(data)
            data = self.reader.read(min(1024, size))
            if not data:
                break

        return b"".join(ret)

    def readlines(self, size=None):
        ret = []
        data = self.read()
        while len(data):
            pos = data.find(b"\n")
            if pos < 0:
                ret.append(data)
                data = b""
            else:
                line, data = data[:pos + 1], data[pos + 1:]
                ret.append(line)
        return ret

########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.


class ParseException(Exception):
    pass


class NoMoreData(IOError):
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
        return "Invalid HTTP Version: %r" % self.version


class InvalidHeader(ParseException):
    def __init__(self, hdr, req=None):
        self.hdr = hdr
        self.req = req

    def __str__(self):
        return "Invalid HTTP Header: %r" % self.hdr


class InvalidHeaderName(ParseException):
    def __init__(self, hdr):
        self.hdr = hdr

    def __str__(self):
        return "Invalid HTTP header name: %r" % self.hdr


class InvalidChunkSize(IOError):
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return "Invalid chunk size: %r" % self.data


class ChunkMissingTerminator(IOError):
    def __init__(self, term):
        self.term = term

    def __str__(self):
        return "Invalid chunk terminator is not '\\r\\n': %r" % self.term


class LimitRequestLine(ParseException):
    def __init__(self, size, max_size):
        self.size = size
        self.max_size = max_size

    def __str__(self):
        return "Request Line is too large (%s > %s)" % (self.size, self.max_size)


class LimitRequestHeaders(ParseException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class InvalidProxyLine(ParseException):
    def __init__(self, line):
        self.line = line
        self.code = 400

    def __str__(self):
        return "Invalid PROXY line: %r" % self.line


class ForbiddenProxyRequest(ParseException):
    def __init__(self, host):
        self.host = host
        self.code = 403

    def __str__(self):
        return "Proxy request from %r not allowed" % self.host

########NEW FILE########
__FILENAME__ = message
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import re
import socket
from errno import ENOTCONN

from gunicorn.http.unreader import SocketUnreader
from gunicorn.http.body import ChunkedReader, LengthReader, EOFReader, Body
from gunicorn.http.errors import (InvalidHeader, InvalidHeaderName, NoMoreData,
    InvalidRequestLine, InvalidRequestMethod, InvalidHTTPVersion,
    LimitRequestLine, LimitRequestHeaders)
from gunicorn.http.errors import InvalidProxyLine, ForbiddenProxyRequest
from gunicorn.six import BytesIO, urlsplit, bytes_to_str

MAX_REQUEST_LINE = 8190
MAX_HEADERS = 32768
MAX_HEADERFIELD_SIZE = 8190

HEADER_RE = re.compile("[\x00-\x1F\x7F()<>@,;:\[\]={} \t\\\\\"]")
METH_RE = re.compile(r"[A-Z0-9$-_.]{3,20}")
VERSION_RE = re.compile(r"HTTP/(\d+).(\d+)")


class Message(object):
    def __init__(self, cfg, unreader):
        self.cfg = cfg
        self.unreader = unreader
        self.version = None
        self.headers = []
        self.trailers = []
        self.body = None

        # set headers limits
        self.limit_request_fields = cfg.limit_request_fields
        if (self.limit_request_fields <= 0
            or self.limit_request_fields > MAX_HEADERS):
            self.limit_request_fields = MAX_HEADERS
        self.limit_request_field_size = cfg.limit_request_field_size
        if (self.limit_request_field_size < 0
            or self.limit_request_field_size > MAX_HEADERFIELD_SIZE):
            self.limit_request_field_size = MAX_HEADERFIELD_SIZE

        # set max header buffer size
        max_header_field_size = self.limit_request_field_size or MAX_HEADERFIELD_SIZE
        self.max_buffer_headers = self.limit_request_fields * \
            (max_header_field_size + 2) + 4

        unused = self.parse(self.unreader)
        self.unreader.unread(unused)
        self.set_body_reader()

    def parse(self):
        raise NotImplementedError()

    def parse_headers(self, data):
        headers = []

        # Split lines on \r\n keeping the \r\n on each line
        lines = [bytes_to_str(line) + "\r\n" for line in data.split(b"\r\n")]

        # Parse headers into key/value pairs paying attention
        # to continuation lines.
        while len(lines):
            if len(headers) >= self.limit_request_fields:
                raise LimitRequestHeaders("limit request headers fields")

            # Parse initial header name : value pair.
            curr = lines.pop(0)
            header_length = len(curr)
            if curr.find(":") < 0:
                raise InvalidHeader(curr.strip())
            name, value = curr.split(":", 1)
            name = name.rstrip(" \t").upper()
            if HEADER_RE.search(name):
                raise InvalidHeaderName(name)

            name, value = name.strip(), [value.lstrip()]

            # Consume value continuation lines
            while len(lines) and lines[0].startswith((" ", "\t")):
                curr = lines.pop(0)
                header_length += len(curr)
                if header_length > self.limit_request_field_size > 0:
                    raise LimitRequestHeaders("limit request headers "
                            + "fields size")
                value.append(curr)
            value = ''.join(value).rstrip()

            if header_length > self.limit_request_field_size > 0:
                raise LimitRequestHeaders("limit request headers fields size")
            headers.append((name, value))
        return headers

    def set_body_reader(self):
        chunked = False
        content_length = None
        for (name, value) in self.headers:
            if name == "CONTENT-LENGTH":
                content_length = value
            elif name == "TRANSFER-ENCODING":
                chunked = value.lower() == "chunked"
            elif name == "SEC-WEBSOCKET-KEY1":
                content_length = 8

        if chunked:
            self.body = Body(ChunkedReader(self, self.unreader))
        elif content_length is not None:
            try:
                content_length = int(content_length)
            except ValueError:
                raise InvalidHeader("CONTENT-LENGTH", req=self)

            if content_length < 0:
                raise InvalidHeader("CONTENT-LENGTH", req=self)

            self.body = Body(LengthReader(self.unreader, content_length))
        else:
            self.body = Body(EOFReader(self.unreader))

    def should_close(self):
        for (h, v) in self.headers:
            if h == "CONNECTION":
                v = v.lower().strip()
                if v == "close":
                    return True
                elif v == "keep-alive":
                    return False
                break
        return self.version <= (1, 0)


class Request(Message):
    def __init__(self, cfg, unreader, req_number=1):
        self.method = None
        self.uri = None
        self.path = None
        self.query = None
        self.fragment = None

        # get max request line size
        self.limit_request_line = cfg.limit_request_line
        if (self.limit_request_line < 0
            or self.limit_request_line >= MAX_REQUEST_LINE):
            self.limit_request_line = MAX_REQUEST_LINE

        self.req_number = req_number
        self.proxy_protocol_info = None
        super(Request, self).__init__(cfg, unreader)

    def get_data(self, unreader, buf, stop=False):
        data = unreader.read()
        if not data:
            if stop:
                raise StopIteration()
            raise NoMoreData(buf.getvalue())
        buf.write(data)

    def parse(self, unreader):
        buf = BytesIO()
        self.get_data(unreader, buf, stop=True)

        # get request line
        line, rbuf = self.read_line(unreader, buf, self.limit_request_line)

        # proxy protocol
        if self.proxy_protocol(bytes_to_str(line)):
            # get next request line
            buf = BytesIO()
            buf.write(rbuf)
            line, rbuf = self.read_line(unreader, buf, self.limit_request_line)

        self.parse_request_line(bytes_to_str(line))
        buf = BytesIO()
        buf.write(rbuf)

        # Headers
        data = buf.getvalue()
        idx = data.find(b"\r\n\r\n")

        done = data[:2] == b"\r\n"
        while True:
            idx = data.find(b"\r\n\r\n")
            done = data[:2] == b"\r\n"

            if idx < 0 and not done:
                self.get_data(unreader, buf)
                data = buf.getvalue()
                if len(data) > self.max_buffer_headers:
                    raise LimitRequestHeaders("max buffer headers")
            else:
                break

        if done:
            self.unreader.unread(data[2:])
            return b""

        self.headers = self.parse_headers(data[:idx])

        ret = data[idx + 4:]
        buf = BytesIO()
        return ret

    def read_line(self, unreader, buf, limit=0):
        data = buf.getvalue()

        while True:
            idx = data.find(b"\r\n")
            if idx >= 0:
                # check if the request line is too large
                if idx > limit > 0:
                    raise LimitRequestLine(idx, limit)
                break
            elif len(data) - 2 > limit > 0:
                raise LimitRequestLine(len(data), limit)
            self.get_data(unreader, buf)
            data = buf.getvalue()

        return (data[:idx],  # request line,
                data[idx + 2:])  # residue in the buffer, skip \r\n

    def proxy_protocol(self, line):
        """\
        Detect, check and parse proxy protocol.

        :raises: ForbiddenProxyRequest, InvalidProxyLine.
        :return: True for proxy protocol line else False
        """
        if not self.cfg.proxy_protocol:
            return False

        if self.req_number != 1:
            return False

        if not line.startswith("PROXY"):
            return False

        self.proxy_protocol_access_check()
        self.parse_proxy_protocol(line)

        return True

    def proxy_protocol_access_check(self):
        # check in allow list
        if isinstance(self.unreader, SocketUnreader):
            try:
                remote_host = self.unreader.sock.getpeername()[0]
            except socket.error as e:
                if e.args[0] == ENOTCONN:
                    raise ForbiddenProxyRequest("UNKNOW")
                raise
            if ("*" not in self.cfg.proxy_allow_ips and
                    remote_host not in self.cfg.proxy_allow_ips):
                raise ForbiddenProxyRequest(remote_host)

    def parse_proxy_protocol(self, line):
        bits = line.split()

        if len(bits) != 6:
            raise InvalidProxyLine(line)

        # Extract data
        proto = bits[1]
        s_addr = bits[2]
        d_addr = bits[3]

        # Validation
        if proto not in ["TCP4", "TCP6"]:
            raise InvalidProxyLine("protocol '%s' not supported" % proto)
        if proto == "TCP4":
            try:
                socket.inet_pton(socket.AF_INET, s_addr)
                socket.inet_pton(socket.AF_INET, d_addr)
            except socket.error:
                raise InvalidProxyLine(line)
        elif proto == "TCP6":
            try:
                socket.inet_pton(socket.AF_INET6, s_addr)
                socket.inet_pton(socket.AF_INET6, d_addr)
            except socket.error:
                raise InvalidProxyLine(line)

        try:
            s_port = int(bits[4])
            d_port = int(bits[5])
        except ValueError:
            raise InvalidProxyLine("invalid port %s" % line)

        if not ((0 <= s_port <= 65535) and (0 <= d_port <= 65535)):
            raise InvalidProxyLine("invalid port %s" % line)

        # Set data
        self.proxy_protocol_info = {
            "proxy_protocol": proto,
            "client_addr": s_addr,
            "client_port": s_port,
            "proxy_addr": d_addr,
            "proxy_port": d_port
        }

    def parse_request_line(self, line):
        bits = line.split(None, 2)
        if len(bits) != 3:
            raise InvalidRequestLine(line)

        # Method
        if not METH_RE.match(bits[0]):
            raise InvalidRequestMethod(bits[0])
        self.method = bits[0].upper()

        # URI
        # When the path starts with //, urlsplit considers it as a
        # relative uri while the RDF says it shouldnt
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
        # considers it as an absolute url.
        # fix issue #297
        if bits[1].startswith("//"):
            self.uri = bits[1][1:]
        else:
            self.uri = bits[1]

        parts = urlsplit(self.uri)
        self.path = parts.path or ""
        self.query = parts.query or ""
        self.fragment = parts.fragment or ""

        # Version
        match = VERSION_RE.match(bits[2])
        if match is None:
            raise InvalidHTTPVersion(bits[2])
        self.version = (int(match.group(1)), int(match.group(2)))

    def set_body_reader(self):
        super(Request, self).set_body_reader()
        if isinstance(self.body.reader, EOFReader):
            self.body = Body(LengthReader(self.unreader, 0))

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

from gunicorn.http.message import Request
from gunicorn.http.unreader import SocketUnreader, IterUnreader


class Parser(object):
    def __init__(self, mesg_class, cfg, source):
        self.mesg_class = mesg_class
        self.cfg = cfg
        if hasattr(source, "recv"):
            self.unreader = SocketUnreader(source)
        else:
            self.unreader = IterUnreader(source)
        self.mesg = None

        # request counter (for keepalive connetions)
        self.req_count = 0

    def __iter__(self):
        return self

    def __next__(self):
        # Stop if HTTP dictates a stop.
        if self.mesg and self.mesg.should_close():
            raise StopIteration()

        # Discard any unread body of the previous message
        if self.mesg:
            data = self.mesg.body.read(8192)
            while data:
                data = self.mesg.body.read(8192)

        # Parse the next request
        self.req_count += 1
        self.mesg = self.mesg_class(self.cfg, self.unreader, self.req_count)
        if not self.mesg:
            raise StopIteration()
        return self.mesg

    next = __next__


class RequestParser(Parser):
    def __init__(self, *args, **kwargs):
        super(RequestParser, self).__init__(Request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = unreader
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import os

from gunicorn import six

# Classes that can undo reading data from
# a given type of data source.


class Unreader(object):
    def __init__(self):
        self.buf = six.BytesIO()

    def chunk(self):
        raise NotImplementedError()

    def read(self, size=None):
        if size is not None and not isinstance(size, six.integer_types):
            raise TypeError("size parameter must be an int or long.")

        if size is not None:
            if size == 0:
                return b""
            if size < 0:
                size = None

        self.buf.seek(0, os.SEEK_END)

        if size is None and self.buf.tell():
            ret = self.buf.getvalue()
            self.buf = six.BytesIO()
            return ret
        if size is None:
            d = self.chunk()
            return d

        while self.buf.tell() < size:
            chunk = self.chunk()
            if not len(chunk):
                ret = self.buf.getvalue()
                self.buf = six.BytesIO()
                return ret
            self.buf.write(chunk)
        data = self.buf.getvalue()
        self.buf = six.BytesIO()
        self.buf.write(data[size:])
        return data[:size]

    def unread(self, data):
        self.buf.seek(0, os.SEEK_END)
        self.buf.write(data)


class SocketUnreader(Unreader):
    def __init__(self, sock, max_chunk=8192):
        super(SocketUnreader, self).__init__()
        self.sock = sock
        self.mxchunk = max_chunk

    def chunk(self):
        return self.sock.recv(self.mxchunk)


class IterUnreader(Unreader):
    def __init__(self, iterable):
        super(IterUnreader, self).__init__()
        self.iter = iter(iterable)

    def chunk(self):
        if not self.iter:
            return b""
        try:
            return six.next(self.iter)
        except StopIteration:
            self.iter = None
            return b""

########NEW FILE########
__FILENAME__ = wsgi
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import io
import logging
import os
import re
import sys

from gunicorn.six import unquote_to_wsgi_str, string_types, binary_type, reraise
from gunicorn import SERVER_SOFTWARE
import gunicorn.six as six
import gunicorn.util as util

try:
    # Python 3.3 has os.sendfile().
    from os import sendfile
except ImportError:
    try:
        from ._sendfile import sendfile
    except ImportError:
        sendfile = None

NORMALIZE_SPACE = re.compile(r'(?:\r\n)?[ \t]+')

log = logging.getLogger(__name__)


class FileWrapper(object):

    def __init__(self, filelike, blksize=8192):
        self.filelike = filelike
        self.blksize = blksize
        if hasattr(filelike, 'close'):
            self.close = filelike.close

    def __getitem__(self, key):
        data = self.filelike.read(self.blksize)
        if data:
            return data
        raise IndexError


class WSGIErrorsWraper(io.RawIOBase):

    def __init__(self, cfg):
        errorlog = logging.getLogger("gunicorn.error")
        handlers = errorlog.handlers
        self.streams = []

        if cfg.errorlog == "-":
            self.streams.append(sys.stderr)
            handlers = handlers[1:]

        for h in handlers:
            if hasattr(h, "stream"):
                self.streams.append(h.stream)

    def write(self, data):
        for stream in self.streams:
            try:
                stream.write(data)
            except UnicodeError:
                stream.write(data.encode("UTF-8"))
            stream.flush()


def base_environ(cfg):
    return {
        "wsgi.errors": WSGIErrorsWraper(cfg),
        "wsgi.version": (1, 0),
        "wsgi.multithread": False,
        "wsgi.multiprocess": (cfg.workers > 1),
        "wsgi.run_once": False,
        "wsgi.file_wrapper": FileWrapper,
        "SERVER_SOFTWARE": SERVER_SOFTWARE,
    }


def default_environ(req, sock, cfg):
    env = base_environ(cfg)
    env.update({
        "wsgi.input": req.body,
        "gunicorn.socket": sock,
        "REQUEST_METHOD": req.method,
        "QUERY_STRING": req.query,
        "RAW_URI": req.uri,
        "SERVER_PROTOCOL": "HTTP/%s" % ".".join([str(v) for v in req.version])
    })
    return env


def proxy_environ(req):
    info = req.proxy_protocol_info

    if not info:
        return {}

    return {
        "PROXY_PROTOCOL": info["proxy_protocol"],
        "REMOTE_ADDR": info["client_addr"],
        "REMOTE_PORT":  str(info["client_port"]),
        "PROXY_ADDR": info["proxy_addr"],
        "PROXY_PORT": str(info["proxy_port"]),
    }


def create(req, sock, client, server, cfg):
    resp = Response(req, sock, cfg)

    # set initial environ
    environ = default_environ(req, sock, cfg)

    # default variables
    host = None
    url_scheme = "https" if cfg.is_ssl else "http"
    script_name = os.environ.get("SCRIPT_NAME", "")

    # set secure_headers
    secure_headers = cfg.secure_scheme_headers
    if client and not isinstance(client, string_types):
        if ('*' not in cfg.forwarded_allow_ips
                and client[0] not in cfg.forwarded_allow_ips):
            secure_headers = {}

    # add the headers tot the environ
    for hdr_name, hdr_value in req.headers:
        if hdr_name == "EXPECT":
            # handle expect
            if hdr_value.lower() == "100-continue":
                sock.send(b"HTTP/1.1 100 Continue\r\n\r\n")
        elif secure_headers and (hdr_name in secure_headers and
              hdr_value == secure_headers[hdr_name]):
            url_scheme = "https"
        elif hdr_name == 'HOST':
            host = hdr_value
        elif hdr_name == "SCRIPT_NAME":
            script_name = hdr_value
        elif hdr_name == "CONTENT-TYPE":
            environ['CONTENT_TYPE'] = hdr_value
            continue
        elif hdr_name == "CONTENT-LENGTH":
            environ['CONTENT_LENGTH'] = hdr_value
            continue

        key = 'HTTP_' + hdr_name.replace('-', '_')
        if key in environ:
            hdr_value = "%s,%s" % (environ[key], hdr_value)
        environ[key] = hdr_value

    # set the url schejeme
    environ['wsgi.url_scheme'] = url_scheme

    # set the REMOTE_* keys in environ
    # authors should be aware that REMOTE_HOST and REMOTE_ADDR
    # may not qualify the remote addr:
    # http://www.ietf.org/rfc/rfc3875
    if isinstance(client, string_types):
        environ['REMOTE_ADDR'] = client
    else:
        environ['REMOTE_ADDR'] = client[0]
        environ['REMOTE_PORT'] = str(client[1])

    # handle the SERVER_*
    # Normally only the application should use the Host header but since the
    # WSGI spec doesn't support unix sockets, we are using it to create
    # viable SERVER_* if possible.
    if isinstance(server, string_types):
        server = server.split(":")
        if len(server) == 1:
            # unix socket
            if host and host is not None:
                server = host.split(':')
                if len(server) == 1:
                    if url_scheme == "http":
                        server.append(80),
                    elif url_scheme == "https":
                        server.append(443)
                    else:
                        server.append('')
            else:
                # no host header given which means that we are not behind a
                # proxy, so append an empty port.
                server.append('')
    environ['SERVER_NAME'] = server[0]
    environ['SERVER_PORT'] = str(server[1])

    # set the path and script name
    path_info = req.path
    if script_name:
        path_info = path_info.split(script_name, 1)[1]
    environ['PATH_INFO'] = unquote_to_wsgi_str(path_info)
    environ['SCRIPT_NAME'] = script_name

    # override the environ with the correct remote and server address if
    # we are behind a proxy using the proxy protocol.
    environ.update(proxy_environ(req))
    return resp, environ


class Response(object):

    def __init__(self, req, sock, cfg):
        self.req = req
        self.sock = sock
        self.version = SERVER_SOFTWARE
        self.status = None
        self.chunked = False
        self.must_close = False
        self.headers = []
        self.headers_sent = False
        self.response_length = None
        self.sent = 0
        self.upgrade = False
        self.cfg = cfg

    def force_close(self):
        self.must_close = True

    def should_close(self):
        if self.must_close or self.req.should_close():
            return True
        if self.response_length is not None or self.chunked:
            return False
        if self.status_code < 200 or self.status_code in (204, 304):
            return False
        return True

    def start_response(self, status, headers, exc_info=None):
        if exc_info:
            try:
                if self.status and self.headers_sent:
                    reraise(exc_info[0], exc_info[1], exc_info[2])
            finally:
                exc_info = None
        elif self.status is not None:
            raise AssertionError("Response headers already set!")

        self.status = status

        # get the status code from the response here so we can use it to check
        # the need for the connection header later without parsing the string
        # each time.
        try:
            self.status_code = int(self.status.split()[0])
        except ValueError:
            self.status_code = None

        self.process_headers(headers)
        self.chunked = self.is_chunked()
        return self.write

    def process_headers(self, headers):
        for name, value in headers:
            assert isinstance(name, string_types), "%r is not a string" % name

            value = str(value).strip()
            lname = name.lower().strip()
            if lname == "content-length":
                self.response_length = int(value)
            elif util.is_hoppish(name):
                if lname == "connection":
                    # handle websocket
                    if value.lower().strip() == "upgrade":
                        self.upgrade = True
                elif lname == "upgrade":
                    if value.lower().strip() == "websocket":
                        self.headers.append((name.strip(), value))

                # ignore hopbyhop headers
                continue
            self.headers.append((name.strip(), value))

    def is_chunked(self):
        # Only use chunked responses when the client is
        # speaking HTTP/1.1 or newer and there was
        # no Content-Length header set.
        if self.response_length is not None:
            return False
        elif self.req.version <= (1, 0):
            return False
        elif self.status_code in (204, 304):
            # Do not use chunked responses when the response is guaranteed to
            # not have a response body.
            return False
        return True

    def default_headers(self):
        # set the connection header
        if self.upgrade:
            connection = "upgrade"
        elif self.should_close():
            connection = "close"
        else:
            connection = "keep-alive"

        headers = [
            "HTTP/%s.%s %s\r\n" % (self.req.version[0],
                self.req.version[1], self.status),
            "Server: %s\r\n" % self.version,
            "Date: %s\r\n" % util.http_date(),
            "Connection: %s\r\n" % connection
        ]
        if self.chunked:
            headers.append("Transfer-Encoding: chunked\r\n")
        return headers

    def send_headers(self):
        if self.headers_sent:
            return
        tosend = self.default_headers()
        tosend.extend(["%s: %s\r\n" % (k, v) for k, v in self.headers])

        header_str = "%s\r\n" % "".join(tosend)
        util.write(self.sock, util.to_bytestring(header_str))
        self.headers_sent = True

    def write(self, arg):
        self.send_headers()

        assert isinstance(arg, binary_type), "%r is not a byte." % arg

        arglen = len(arg)
        tosend = arglen
        if self.response_length is not None:
            if self.sent >= self.response_length:
                # Never write more than self.response_length bytes
                return

            tosend = min(self.response_length - self.sent, tosend)
            if tosend < arglen:
                arg = arg[:tosend]

        # Sending an empty chunk signals the end of the
        # response and prematurely closes the response
        if self.chunked and tosend == 0:
            return

        self.sent += tosend
        util.write(self.sock, arg, self.chunked)

    def sendfile_all(self, fileno, sockno, offset, nbytes):
        # Send file in at most 1GB blocks as some operating
        # systems can have problems with sending files in blocks
        # over 2GB.

        BLKSIZE = 0x3FFFFFFF

        if nbytes > BLKSIZE:
            for m in range(0, nbytes, BLKSIZE):
                self.sendfile_all(fileno, sockno, offset, min(nbytes, BLKSIZE))
                offset += BLKSIZE
                nbytes -= BLKSIZE
        else:
            sent = 0
            sent += sendfile(sockno, fileno, offset + sent, nbytes - sent)
            while sent != nbytes:
                sent += sendfile(sockno, fileno, offset + sent, nbytes - sent)

    def sendfile_use_send(self, fileno, fo_offset, nbytes):

        # send file in blocks of 8182 bytes
        BLKSIZE = 8192

        sent = 0
        while sent != nbytes:
            data = os.read(fileno, BLKSIZE)
            if not data:
                break

            sent += len(data)
            if sent > nbytes:
                data = data[:nbytes-sent]

            util.write(self.sock, data, self.chunked)

    def write_file(self, respiter):
        if sendfile is not None and util.is_fileobject(respiter.filelike):
            # sometimes the fileno isn't a callable
            if six.callable(respiter.filelike.fileno):
                fileno = respiter.filelike.fileno()
            else:
                fileno = respiter.filelike.fileno

            fd_offset = os.lseek(fileno, 0, os.SEEK_CUR)
            fo_offset = respiter.filelike.tell()
            nbytes = max(os.fstat(fileno).st_size - fo_offset, 0)

            if self.response_length:
                nbytes = min(nbytes, self.response_length)

            if nbytes == 0:
                return

            self.send_headers()

            if self.cfg.is_ssl:
                self.sendfile_use_send(fileno, fo_offset, nbytes)
            else:
                if self.is_chunked():
                    chunk_size = "%X\r\n" % nbytes
                    self.sock.sendall(chunk_size.encode('utf-8'))

                self.sendfile_all(fileno, self.sock.fileno(), fo_offset, nbytes)

                if self.is_chunked():
                    self.sock.sendall(b"\r\n")

            os.lseek(fileno, fd_offset, os.SEEK_SET)
        else:
            for item in respiter:
                self.write(item)

    def close(self):
        if not self.headers_sent:
            self.send_headers()
        if self.chunked:
            util.write_chunk(self.sock, b"")

########NEW FILE########
__FILENAME__ = _sendfile
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import errno
import os
import sys

try:
    import ctypes
    import ctypes.util
except MemoryError:
    # selinux execmem denial
    # https://bugzilla.redhat.com/show_bug.cgi?id=488396
    raise ImportError

SUPPORTED_PLATFORMS = (
        'darwin',
        'freebsd',
        'dragonfly',
        'linux2')

if sys.version_info < (2, 6) or \
        sys.platform not in SUPPORTED_PLATFORMS:
    raise ImportError("sendfile isn't supported on this platform")

_libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
_sendfile = _libc.sendfile


def sendfile(fdout, fdin, offset, nbytes):
    if sys.platform == 'darwin':
        _sendfile.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                              ctypes.POINTER(ctypes.c_uint64), ctypes.c_voidp,
                              ctypes.c_int]
        _nbytes = ctypes.c_uint64(nbytes)
        result = _sendfile(fdin, fdout, offset, _nbytes, None, 0)

        if result == -1:
            e = ctypes.get_errno()
            if e == errno.EAGAIN and _nbytes.value is not None:
                return _nbytes.value
            raise OSError(e, os.strerror(e))
        return _nbytes.value
    elif sys.platform in ('freebsd', 'dragonfly',):
        _sendfile.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                              ctypes.c_uint64, ctypes.c_voidp,
                              ctypes.POINTER(ctypes.c_uint64), ctypes.c_int]
        _sbytes = ctypes.c_uint64()
        result = _sendfile(fdin, fdout, offset, nbytes, None, _sbytes, 0)
        if result == -1:
            e = ctypes.get_errno()
            if e == errno.EAGAIN and _sbytes.value is not None:
                return _sbytes.value
            raise OSError(e, os.strerror(e))
        return _sbytes.value

    else:
        _sendfile.argtypes = [ctypes.c_int, ctypes.c_int,
                ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t]

        _offset = ctypes.c_uint64(offset)
        sent = _sendfile(fdout, fdin, _offset, nbytes)
        if sent == -1:
            e = ctypes.get_errno()
            raise OSError(e, os.strerror(e))
        return sent

########NEW FILE########
__FILENAME__ = run_gunicorn
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

from optparse import make_option
import sys

from django.core.management.base import BaseCommand, CommandError

from gunicorn.app.djangoapp import DjangoApplicationCommand
from gunicorn.config import make_settings
from gunicorn import util


# monkey patch django.
# This patch make sure that we use real threads to get the ident which
# is going to happen if we are using gevent or eventlet.
try:
    from django.db.backends import BaseDatabaseWrapper, DatabaseError

    if "validate_thread_sharing" in BaseDatabaseWrapper.__dict__:
        import thread
        _get_ident = thread.get_ident

        __old__init__ = BaseDatabaseWrapper.__init__

        def _init(self, *args, **kwargs):
            __old__init__(self, *args, **kwargs)
            self._thread_ident = _get_ident()

        def _validate_thread_sharing(self):
            if (not self.allow_thread_sharing
                and self._thread_ident != _get_ident()):
                    raise DatabaseError("DatabaseWrapper objects created in a "
                        "thread can only be used in that same thread. The object "
                        "with alias '%s' was created in thread id %s and this is "
                        "thread id %s."
                        % (self.alias, self._thread_ident, _get_ident()))

        BaseDatabaseWrapper.__init__ = _init
        BaseDatabaseWrapper.validate_thread_sharing = _validate_thread_sharing
except ImportError:
    pass


def make_options():
    opts = [
        make_option('--adminmedia', dest='admin_media_path', default='',
        help='Specifies the directory from which to serve admin media.')
    ]

    g_settings = make_settings(ignore=("version"))
    keys = g_settings.keys()
    for k in keys:
        if k in ('pythonpath', 'django_settings',):
            continue

        setting = g_settings[k]
        if not setting.cli:
            continue

        args = tuple(setting.cli)

        kwargs = {
            "dest": setting.name,
            "metavar": setting.meta or None,
            "action": setting.action or "store",
            "type": setting.type or "string",
            "default": None,
            "help": "%s [%s]" % (setting.short, setting.default)
        }
        if kwargs["action"] != "store":
            kwargs.pop("type")

        opts.append(make_option(*args, **kwargs))

    return tuple(opts)

GUNICORN_OPTIONS = make_options()


class Command(BaseCommand):
    option_list = BaseCommand.option_list + GUNICORN_OPTIONS
    help = "Starts a fully-functional Web server using gunicorn."
    args = '[optional port number, or ipaddr:port or unix:/path/to/sockfile]'

    # Validation is called explicitly each time the server is reloaded.
    requires_model_validation = False

    def handle(self, addrport=None, *args, **options):

        # deprecation warning to announce future deletion in R21
        util.warn("""This command is deprecated.

        You should now run your application with the WSGI interface
        installed with your project. Ex.:

            gunicorn myproject.wsgi:application

        See https://docs.djangoproject.com/en/1.5/howto/deployment/wsgi/gunicorn/
        for more info.""")

        if args:
            raise CommandError('Usage is run_gunicorn %s' % self.args)

        if addrport:
            sys.argv = sys.argv[:-1]
            options['bind'] = addrport

        admin_media_path = options.pop('admin_media_path', '')

        DjangoApplicationCommand(options, admin_media_path).run()

########NEW FILE########
__FILENAME__ = pidfile
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import errno
import os
import tempfile


class Pidfile(object):
    """\
    Manage a PID file. If a specific name is provided
    it and '"%s.oldpid" % name' will be used. Otherwise
    we create a temp file using os.mkstemp.
    """

    def __init__(self, fname):
        self.fname = fname
        self.pid = None

    def create(self, pid):
        oldpid = self.validate()
        if oldpid:
            if oldpid == os.getpid():
                return
            raise RuntimeError("Already running on PID %s " \
                "(or pid file '%s' is stale)" % (os.getpid(), self.fname))

        self.pid = pid

        # Write pidfile
        fdir = os.path.dirname(self.fname)
        if fdir and not os.path.isdir(fdir):
            raise RuntimeError("%s doesn't exist. Can't create pidfile." % fdir)
        fd, fname = tempfile.mkstemp(dir=fdir)
        os.write(fd, ("%s\n" % self.pid).encode('utf-8'))
        if self.fname:
            os.rename(fname, self.fname)
        else:
            self.fname = fname
        os.close(fd)

        # set permissions to -rw-r--r--
        os.chmod(self.fname, 420)

    def rename(self, path):
        self.unlink()
        self.fname = path
        self.create(self.pid)

    def unlink(self):
        """ delete pidfile"""
        try:
            with open(self.fname, "r") as f:
                pid1 = int(f.read() or 0)

            if pid1 == self.pid:
                os.unlink(self.fname)
        except:
            pass

    def validate(self):
        """ Validate pidfile and make it stale if needed"""
        if not self.fname:
            return
        try:
            with open(self.fname, "r") as f:
                wpid = int(f.read() or 0)

                if wpid <= 0:
                    return

                try:
                    os.kill(wpid, 0)
                    return wpid
                except OSError as e:
                    if e.args[0] == errno.ESRCH:
                        return
                    raise
        except IOError as e:
            if e.args[0] == errno.ENOENT:
                return
            raise

########NEW FILE########
__FILENAME__ = reloader
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import os
import re
import sys
import time
import threading


class Reloader(threading.Thread):
    def __init__(self, extra_files=None, interval=1, callback=None):
        super(Reloader, self).__init__()
        self.setDaemon(True)
        self._extra_files = set(extra_files or ())
        self._extra_files_lock = threading.RLock()
        self._interval = interval
        self._callback = callback

    def add_extra_file(self, filename):
        with self._extra_files_lock:
            self._extra_files.add(filename)

    def get_files(self):
        fnames = [
            re.sub('py[co]$', 'py', module.__file__)
            for module in sys.modules.values()
            if hasattr(module, '__file__')
        ]

        with self._extra_files_lock:
            fnames.extend(self._extra_files)

        return fnames

    def run(self):
        mtimes = {}
        while True:
            for filename in self.get_files():
                try:
                    mtime = os.stat(filename).st_mtime
                except OSError:
                    continue
                old_time = mtimes.get(filename)
                if old_time is None:
                    mtimes[filename] = mtime
                    continue
                elif mtime > old_time:
                    if self._callback:
                        self._callback(filename)
            time.sleep(self._interval)

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.2.0"


# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform == "java":
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
            del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules["gunicorn.six.moves"] = _MovedItems("moves")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_code = "__code__"
    _func_defaults = "__defaults__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_code = "func_code"
    _func_defaults = "func_defaults"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


if PY3:
    def get_unbound_function(unbound):
        return unbound

    Iterator = object

    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)())

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)())

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)())


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    int2byte = chr
    import cStringIO
    def StringIO(buf=''):
        sio = cStringIO.StringIO()
        if buf:
            sio.write(buf)
            sio.seek(0)
        return sio
    BytesIO = StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


def _check_if_pyc(fname):
    """ Returns True if the extension is .pyc, False if .py and None if otherwise """
    from imp import find_module
    from os.path import realpath, dirname, basename, splitext

    # Normalize the file-path for the find_module()
    filepath = realpath(fname)
    dirpath = dirname(filepath)
    module_name = splitext(basename(filepath))[0]

    # Validate and fetch
    try:
        fileobj, fullpath, (_, _, pytype) = find_module(module_name, [ dirpath ])

    except ImportError:
        raise IOError("Cannot find config file. Path maybe incorrect! : {0}".format(filepath))

    return (pytype, fileobj, fullpath)


def _get_codeobj(pyfile):
    """ Returns the code object, given a python file """
    from imp import PY_COMPILED, PY_SOURCE

    result, fileobj, fullpath = _check_if_pyc(pyfile)

    # WARNING:
    # fp.read() can blowup if the module is extremely large file.
    # Lookout for overflow errors.
    try:
        data = fileobj.read()
    finally:
        fileobj.close()

    # This is a .pyc file. Treat accordingly.
    if result is PY_COMPILED:
        # .pyc format is as follows:
        # 0 - 4 bytes: Magic number, which changes with each create of .pyc file.
        #              First 2 bytes change with each marshal of .pyc file. Last 2 bytes is "\r\n".
        # 4 - 8 bytes: Datetime value, when the .py was last changed.
        # 8 - EOF: Marshalled code object data.
        # So to get code object, just read the 8th byte onwards till EOF, and UN-marshal it.
        import marshal
        code_obj = marshal.loads(data[8:])

    elif result is PY_SOURCE:
        # This is a .py file.
        code_obj = compile(data, fullpath, 'exec')

    else:
        # Unsupported extension
        raise Exception("Input file is unknown format: {0}".format(fullpath))

    # Return code object
    return code_obj


if PY3:

    import builtins
    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")

    def execfile_(fname, *args):
        return exec_(_get_codeobj(fname), *args)


    del builtins

else:
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

    def execfile_(fname, *args):
        """ Overriding PY2 execfile() implementation to support .pyc files """
        return exec_(_get_codeobj(fname), *args)


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})


# specific to gunicorn
if PY3:
    def bytes_to_str(b):
        if isinstance(b, text_type):
            return b
        return str(b, 'latin1')

    import urllib.parse

    def unquote_to_wsgi_str(string):
        return _unquote_to_bytes(string).decode('latin-1')

    _unquote_to_bytes = urllib.parse.unquote_to_bytes
    urlsplit = urllib.parse.urlsplit
    urlparse = urllib.parse.urlparse

else:
    def bytes_to_str(s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    import urlparse as orig_urlparse
    urlsplit = orig_urlparse.urlsplit
    urlparse = orig_urlparse.urlparse

    import urllib
    unquote_to_wsgi_str = urllib.unquote

########NEW FILE########
__FILENAME__ = sock
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import errno
import os
import socket
import stat
import sys
import time

from gunicorn import util
from gunicorn.six import string_types

SD_LISTEN_FDS_START = 3


class BaseSocket(object):

    def __init__(self, address, conf, log, fd=None):
        self.log = log
        self.conf = conf

        self.cfg_addr = address
        if fd is None:
            sock = socket.socket(self.FAMILY, socket.SOCK_STREAM)
        else:
            sock = socket.fromfd(fd, self.FAMILY, socket.SOCK_STREAM)

        self.sock = self.set_options(sock, bound=(fd is not None))

    def __str__(self, name):
        return "<socket %d>" % self.sock.fileno()

    def __getattr__(self, name):
        return getattr(self.sock, name)

    def set_options(self, sock, bound=False):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if not bound:
            self.bind(sock)
        sock.setblocking(0)
        sock.listen(self.conf.backlog)
        return sock

    def bind(self, sock):
        sock.bind(self.cfg_addr)

    def close(self):
        try:
            self.sock.close()
        except socket.error as e:
            self.log.info("Error while closing socket %s", str(e))
        time.sleep(0.3)
        del self.sock


class TCPSocket(BaseSocket):

    FAMILY = socket.AF_INET

    def __str__(self):
        if self.conf.is_ssl:
            scheme = "https"
        else:
            scheme = "http"

        addr = self.sock.getsockname()
        return "%s://%s:%d" % (scheme, addr[0], addr[1])

    def set_options(self, sock, bound=False):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return super(TCPSocket, self).set_options(sock, bound=bound)


class TCP6Socket(TCPSocket):

    FAMILY = socket.AF_INET6

    def __str__(self):
        (host, port, fl, sc) = self.sock.getsockname()
        return "http://[%s]:%d" % (host, port)


class UnixSocket(BaseSocket):

    FAMILY = socket.AF_UNIX

    def __init__(self, addr, conf, log, fd=None):
        if fd is None:
            try:
                st = os.stat(addr)
            except OSError as e:
                if e.args[0] != errno.ENOENT:
                    raise
            else:
                if stat.S_ISSOCK(st.st_mode):
                    os.remove(addr)
                else:
                    raise ValueError("%r is not a socket" % addr)
        super(UnixSocket, self).__init__(addr, conf, log, fd=fd)

    def __str__(self):
        return "unix:%s" % self.cfg_addr

    def bind(self, sock):
        old_umask = os.umask(self.conf.umask)
        sock.bind(self.cfg_addr)
        util.chown(self.cfg_addr, self.conf.uid, self.conf.gid)
        os.umask(old_umask)

    def close(self):
        super(UnixSocket, self).close()
        os.unlink(self.cfg_addr)


def _sock_type(addr):
    if isinstance(addr, tuple):
        if util.is_ipv6(addr[0]):
            sock_type = TCP6Socket
        else:
            sock_type = TCPSocket
    elif isinstance(addr, string_types):
        sock_type = UnixSocket
    else:
        raise TypeError("Unable to create socket from: %r" % addr)
    return sock_type


def create_sockets(conf, log):
    """
    Create a new socket for the given address. If the
    address is a tuple, a TCP socket is created. If it
    is a string, a Unix socket is created. Otherwise
    a TypeError is raised.
    """

    # Systemd support, use the sockets managed by systemd and passed to
    # gunicorn.
    # http://www.freedesktop.org/software/systemd/man/systemd.socket.html
    listeners = []
    if ('LISTEN_PID' in os.environ
            and int(os.environ.get('LISTEN_PID')) == os.getpid()):
        for i in range(int(os.environ.get('LISTEN_FDS', 0))):
            fd = i + SD_LISTEN_FDS_START
            try:
                sock = socket.fromfd(fd, socket.AF_UNIX, socket.SOCK_STREAM)
                sockname = sock.getsockname()
                if isinstance(sockname, str) and sockname.startswith('/'):
                    listeners.append(UnixSocket(sockname, conf, log, fd=fd))
                elif len(sockname) == 2 and '.' in sockname[0]:
                    listeners.append(TCPSocket("%s:%s" % sockname, conf, log,
                        fd=fd))
                elif len(sockname) == 4 and ':' in sockname[0]:
                    listeners.append(TCP6Socket("[%s]:%s" % sockname[:2], conf,
                        log, fd=fd))
            except socket.error:
                pass
        del os.environ['LISTEN_PID'], os.environ['LISTEN_FDS']

        if listeners:
            log.debug('Socket activation sockets: %s',
                    ",".join([str(l) for l in listeners]))
            return listeners

    # get it only once
    laddr = conf.address

    # check ssl config early to raise the error on startup
    # only the certfile is needed since it can contains the keyfile
    if conf.certfile and not os.path.exists(conf.certfile):
        raise ValueError('certfile "%s" does not exist' % conf.certfile)

    if conf.keyfile and not os.path.exists(conf.keyfile):
        raise ValueError('keyfile "%s" does not exist' % conf.keyfile)

    # sockets are already bound
    if 'GUNICORN_FD' in os.environ:
        fds = os.environ.pop('GUNICORN_FD').split(',')
        for i, fd in enumerate(fds):
            fd = int(fd)
            addr = laddr[i]
            sock_type = _sock_type(addr)

            try:
                listeners.append(sock_type(addr, conf, log, fd=fd))
            except socket.error as e:
                if e.args[0] == errno.ENOTCONN:
                    log.error("GUNICORN_FD should refer to an open socket.")
                else:
                    raise
        return listeners

    # no sockets is bound, first initialization of gunicorn in this env.
    for addr in laddr:
        sock_type = _sock_type(addr)

        # If we fail to create a socket from GUNICORN_FD
        # we fall through and try and open the socket
        # normally.
        sock = None
        for i in range(5):
            try:
                sock = sock_type(addr, conf, log)
            except socket.error as e:
                if e.args[0] == errno.EADDRINUSE:
                    log.error("Connection in use: %s", str(addr))
                if e.args[0] == errno.EADDRNOTAVAIL:
                    log.error("Invalid address: %s", str(addr))
                    sys.exit(1)
                if i < 5:
                    log.error("Retrying in 1 second.")
                    time.sleep(1)
            else:
                break

        if sock is None:
            log.error("Can't connect to %s", str(addr))
            sys.exit(1)

        listeners.append(sock)

    return listeners

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.


import email.utils
import fcntl
import io
import os
import pkg_resources
import random
import resource
import socket
import sys
import textwrap
import time
import traceback
import inspect
import errno
import warnings
import cgi

from gunicorn.errors import AppImportError
from gunicorn.six import text_type
from gunicorn.workers import SUPPORTED_WORKERS


MAXFD = 1024
REDIRECT_TO = getattr(os, 'devnull', '/dev/null')

timeout_default = object()

CHUNK_SIZE = (16 * 1024)

MAX_BODY = 1024 * 132

# Server and Date aren't technically hop-by-hop
# headers, but they are in the purview of the
# origin server which the WSGI spec says we should
# act like. So we drop them and add our own.
#
# In the future, concatenation server header values
# might be better, but nothing else does it and
# dropping them is easier.
hop_headers = set("""
    connection keep-alive proxy-authenticate proxy-authorization
    te trailers transfer-encoding upgrade
    server date
    """.split())

try:
    from setproctitle import setproctitle
    def _setproctitle(title):
        setproctitle("gunicorn: %s" % title)
except ImportError:
    def _setproctitle(title):
        return


try:
    from importlib import import_module
except ImportError:
    def _resolve_name(name, package, level):
        """Return the absolute name of the module to be imported."""
        if not hasattr(package, 'rindex'):
            raise ValueError("'package' not set to a string")
        dot = len(package)
        for x in range(level, 1, -1):
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


def load_class(uri, default="gunicorn.workers.sync.SyncWorker",
        section="gunicorn.workers"):
    if inspect.isclass(uri):
        return uri
    if uri.startswith("egg:"):
        # uses entry points
        entry_str = uri.split("egg:")[1]
        try:
            dist, name = entry_str.rsplit("#", 1)
        except ValueError:
            dist = entry_str
            name = default

        try:
            return pkg_resources.load_entry_point(dist, section, name)
        except:
            exc = traceback.format_exc()
            raise RuntimeError("class uri %r invalid or not found: \n\n[%s]" % (uri,
                exc))
    else:
        components = uri.split('.')
        if len(components) == 1:
            while True:
                if uri.startswith("#"):
                    uri = uri[1:]

                if uri in SUPPORTED_WORKERS:
                    components = SUPPORTED_WORKERS[uri].split(".")
                    break

                try:
                    return pkg_resources.load_entry_point("gunicorn",
                                section, uri)
                except:
                    exc = traceback.format_exc()
                    raise RuntimeError("class uri %r invalid or not found: \n\n[%s]" % (uri,
                        exc))

        klass = components.pop(-1)

        try:
            mod = import_module('.'.join(components))
        except:
            exc = traceback.format_exc()
            raise RuntimeError(
                    "class uri %r invalid or not found: \n\n[%s]" %
                    (uri, exc))
        return getattr(mod, klass)


def set_owner_process(uid, gid):
    """ set user and group of workers processes """
    if gid:
        # versions of python < 2.6.2 don't manage unsigned int for
        # groups like on osx or fedora
        gid = abs(gid) & 0x7FFFFFFF
        os.setgid(gid)
    if uid:
        os.setuid(uid)


def chown(path, uid, gid):
    gid = abs(gid) & 0x7FFFFFFF  # see note above.
    os.chown(path, uid, gid)


if sys.platform.startswith("win"):
    def _waitfor(func, pathname, waitall=False):
        # Peform the operation
        func(pathname)
        # Now setup the wait loop
        if waitall:
            dirname = pathname
        else:
            dirname, name = os.path.split(pathname)
            dirname = dirname or '.'
        # Check for `pathname` to be removed from the filesystem.
        # The exponential backoff of the timeout amounts to a total
        # of ~1 second after which the deletion is probably an error
        # anyway.
        # Testing on a i7@4.3GHz shows that usually only 1 iteration is
        # required when contention occurs.
        timeout = 0.001
        while timeout < 1.0:
            # Note we are only testing for the existance of the file(s) in
            # the contents of the directory regardless of any security or
            # access rights.  If we have made it this far, we have sufficient
            # permissions to do that much using Python's equivalent of the
            # Windows API FindFirstFile.
            # Other Windows APIs can fail or give incorrect results when
            # dealing with files that are pending deletion.
            L = os.listdir(dirname)
            if not (L if waitall else name in L):
                return
            # Increase the timeout and try again
            time.sleep(timeout)
            timeout *= 2
        warnings.warn('tests may fail, delete still pending for ' + pathname,
                      RuntimeWarning, stacklevel=4)

    def _unlink(filename):
        _waitfor(os.unlink, filename)
else:
    _unlink = os.unlink


def unlink(filename):
    try:
        _unlink(filename)
    except OSError as error:
        # The filename need not exist.
        if error.errno not in (errno.ENOENT, errno.ENOTDIR):
            raise


def is_ipv6(addr):
    try:
        socket.inet_pton(socket.AF_INET6, addr)
    except socket.error:  # not a valid address
        return False
    except ValueError: # ipv6 not supported on this platform
        return False
    return True


def parse_address(netloc, default_port=8000):
    if netloc.startswith("unix://"):
        return netloc.split("unix://")[1]

    if netloc.startswith("unix:"):
        return netloc.split("unix:")[1]

    if netloc.startswith("tcp://"):
        netloc = netloc.split("tcp://")[1]


    # get host
    if '[' in netloc and ']' in netloc:
        host = netloc.split(']')[0][1:].lower()
    elif ':' in netloc:
        host = netloc.split(':')[0].lower()
    elif netloc == "":
        host = "0.0.0.0"
    else:
        host = netloc.lower()

    #get port
    netloc = netloc.split(']')[-1]
    if ":" in netloc:
        port = netloc.split(':', 1)[1]
        if not port.isdigit():
            raise RuntimeError("%r is not a valid port number." % port)
        port = int(port)
    else:
        port = default_port
    return (host, port)

def get_maxfd():
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if (maxfd == resource.RLIM_INFINITY):
        maxfd = MAXFD
    return maxfd


def close_on_exec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)


def set_non_blocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)


def close(sock):
    try:
        sock.close()
    except socket.error:
        pass

try:
    from os import closerange
except ImportError:
    def closerange(fd_low, fd_high):
        # Iterate through and close all file descriptors.
        for fd in range(fd_low, fd_high):
            try:
                os.close(fd)
            except OSError:  # ERROR, fd wasn't open to begin with (ignored)
                pass


def write_chunk(sock, data):
    if isinstance(data, text_type):
        data = data.encode('utf-8')
    chunk_size = "%X\r\n" % len(data)
    chunk = b"".join([chunk_size.encode('utf-8'), data, b"\r\n"])
    sock.sendall(chunk)


def write(sock, data, chunked=False):
    if chunked:
        return write_chunk(sock, data)
    sock.sendall(data)


def write_nonblock(sock, data, chunked=False):
    timeout = sock.gettimeout()
    if timeout != 0.0:
        try:
            sock.setblocking(0)
            return write(sock, data, chunked)
        finally:
            sock.setblocking(1)
    else:
        return write(sock, data, chunked)


def writelines(sock, lines, chunked=False):
    for line in list(lines):
        write(sock, line, chunked)


def write_error(sock, status_int, reason, mesg):
    html = textwrap.dedent("""\
    <html>
      <head>
        <title>%(reason)s</title>
      </head>
      <body>
        <h1><p>%(reason)s</p></h1>
        %(mesg)s
      </body>
    </html>
    """) % {"reason": reason, "mesg": cgi.escape(mesg)}

    http = textwrap.dedent("""\
    HTTP/1.1 %s %s\r
    Connection: close\r
    Content-Type: text/html\r
    Content-Length: %d\r
    \r
    %s
    """) % (str(status_int), reason, len(html), html)
    write_nonblock(sock, http.encode('latin1'))


def normalize_name(name):
    return "-".join([w.lower().capitalize() for w in name.split("-")])


def import_app(module):
    parts = module.split(":", 1)
    if len(parts) == 1:
        module, obj = module, "application"
    else:
        module, obj = parts[0], parts[1]

    try:
        __import__(module)
    except ImportError:
        if module.endswith(".py") and os.path.exists(module):
            raise ImportError("Failed to find application, did "
                "you mean '%s:%s'?" % (module.rsplit(".", 1)[0], obj))
        else:
            raise

    mod = sys.modules[module]

    try:
        app = eval(obj, mod.__dict__)
    except NameError:
        raise AppImportError("Failed to find application: %r" % module)

    if app is None:
        raise AppImportError("Failed to find application object: %r" % obj)

    if not callable(app):
        raise AppImportError("Application object must be callable.")
    return app


def getcwd():
    # get current path, try to use PWD env first
    try:
        a = os.stat(os.environ['PWD'])
        b = os.stat(os.getcwd())
        if a.st_ino == b.st_ino and a.st_dev == b.st_dev:
            cwd = os.environ['PWD']
        else:
            cwd = os.getcwd()
    except:
        cwd = os.getcwd()
    return cwd


def http_date(timestamp=None):
    """Return the current date and time formatted for a message header."""
    if timestamp is None:
        timestamp = time.time()
    s = email.utils.formatdate(timestamp, localtime=False, usegmt=True)
    return s


def is_hoppish(header):
    return header.lower().strip() in hop_headers


def daemonize(enable_stdio_inheritance=False):
    """\
    Standard daemonization of a process.
    http://www.svbug.com/documentation/comp.unix.programmer-FAQ/faq_2.html#SEC16
    """
    if not 'GUNICORN_FD' in os.environ:
        if os.fork():
            os._exit(0)
        os.setsid()

        if os.fork():
            os._exit(0)

        os.umask(0)

        # In both the following any file descriptors above stdin
        # stdout and stderr are left untouched. The inheritence
        # option simply allows one to have output go to a file
        # specified by way of shell redirection when not wanting
        # to use --error-log option.

        if not enable_stdio_inheritance:
            # Remap all of stdin, stdout and stderr on to
            # /dev/null. The expectation is that users have
            # specified the --error-log option.

            closerange(0, 3)

            fd_null = os.open(REDIRECT_TO, os.O_RDWR)

            if fd_null != 0:
                os.dup2(fd_null, 0)

            os.dup2(fd_null, 1)
            os.dup2(fd_null, 2)

        else:
            fd_null = os.open(REDIRECT_TO, os.O_RDWR)

            # Always redirect stdin to /dev/null as we would
            # never expect to need to read interactive input.

            if fd_null != 0:
                os.close(0)
                os.dup2(fd_null, 0)

            # If stdout and stderr are still connected to
            # their original file descriptors we check to see
            # if they are associated with terminal devices.
            # When they are we map them to /dev/null so that
            # are still detached from any controlling terminal
            # properly. If not we preserve them as they are.
            #
            # If stdin and stdout were not hooked up to the
            # original file descriptors, then all bets are
            # off and all we can really do is leave them as
            # they were.
            #
            # This will allow 'gunicorn ... > output.log 2>&1'
            # to work with stdout/stderr going to the file
            # as expected.
            #
            # Note that if using --error-log option, the log
            # file specified through shell redirection will
            # only be used up until the log file specified
            # by the option takes over. As it replaces stdout
            # and stderr at the file descriptor level, then
            # anything using stdout or stderr, including having
            # cached a reference to them, will still work.

            def redirect(stream, fd_expect):
                try:
                    fd = stream.fileno()
                    if fd == fd_expect and stream.isatty():
                        os.close(fd)
                        os.dup2(fd_null, fd)
                except AttributeError:
                    pass

            redirect(sys.stdout, 1)
            redirect(sys.stderr, 2)


def seed():
    try:
        random.seed(os.urandom(64))
    except NotImplementedError:
        random.seed('%s.%s' % (time.time(), os.getpid()))


def check_is_writeable(path):
    try:
        f = open(path, 'a')
    except IOError as e:
        raise RuntimeError("Error: '%s' isn't writable [%r]" % (path, e))
    f.close()


def to_bytestring(value):
    """Converts a string argument to a byte string"""
    if isinstance(value, bytes):
        return value
    assert isinstance(value, text_type)
    return value.encode("utf-8")


def is_fileobject(obj):
    if not hasattr(obj, "tell") or not hasattr(obj, "fileno"):
        return False

    # check BytesIO case and maybe others
    try:
        obj.fileno()
    except io.UnsupportedOperation:
        return False

    return True


def warn(msg):
    sys.stderr.write("!!!\n")

    lines = msg.splitlines()
    for i, line in enumerate(lines):
        if i == 0:
            line = "WARNING: %s" % line
        sys.stderr.write("!!! %s\n" % line)

    sys.stderr.write("!!!\n\n")
    sys.stderr.flush()

########NEW FILE########
__FILENAME__ = async
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

from datetime import datetime
import errno
import socket
import ssl
import sys

import gunicorn.http as http
import gunicorn.http.wsgi as wsgi
import gunicorn.util as util
import gunicorn.workers.base as base
from gunicorn import six

ALREADY_HANDLED = object()


class AsyncWorker(base.Worker):

    def __init__(self, *args, **kwargs):
        super(AsyncWorker, self).__init__(*args, **kwargs)
        self.worker_connections = self.cfg.worker_connections

    def timeout_ctx(self):
        raise NotImplementedError()

    def handle(self, listener, client, addr):
        req = None
        try:
            parser = http.RequestParser(self.cfg, client)
            try:
                if not self.cfg.keepalive:
                    req = six.next(parser)
                    self.handle_request(listener, req, client, addr)
                else:
                    # keepalive loop
                    while True:
                        req = None
                        with self.timeout_ctx():
                            req = six.next(parser)
                        if not req:
                            break
                        self.handle_request(listener, req, client, addr)
            except http.errors.NoMoreData as e:
                self.log.debug("Ignored premature client disconnection. %s", e)
            except StopIteration as e:
                self.log.debug("Closing connection. %s", e)
            except ssl.SSLError:
                exc_info = sys.exc_info()
                # pass to next try-except level
                six.reraise(exc_info[0], exc_info[1], exc_info[2])
            except socket.error:
                exc_info = sys.exc_info()
                # pass to next try-except level
                six.reraise(exc_info[0], exc_info[1], exc_info[2])
            except Exception as e:
                self.handle_error(req, client, addr, e)
        except ssl.SSLError as e:
            if e.args[0] == ssl.SSL_ERROR_EOF:
                self.log.debug("ssl connection closed")
                client.close()
            else:
                self.log.debug("Error processing SSL request.")
                self.handle_error(req, client, addr, e)
        except socket.error as e:
            if e.args[0] not in (errno.EPIPE, errno.ECONNRESET):
                self.log.exception("Socket error processing request.")
            else:
                if e.args[0] == errno.ECONNRESET:
                    self.log.debug("Ignoring connection reset")
                else:
                    self.log.debug("Ignoring EPIPE")
        except Exception as e:
            self.handle_error(req, client, addr, e)
        finally:
            util.close(client)

    def handle_request(self, listener, req, sock, addr):
        request_start = datetime.now()
        environ = {}
        resp = None
        try:
            self.cfg.pre_request(self, req)
            resp, environ = wsgi.create(req, sock, addr,
                    listener.getsockname(), self.cfg)
            environ["wsgi.multithread"] = True
            self.nr += 1
            if self.alive and self.nr >= self.max_requests:
                self.log.info("Autorestarting worker after current request.")
                resp.force_close()
                self.alive = False

            if not self.cfg.keepalive:
                resp.force_close()

            respiter = self.wsgi(environ, resp.start_response)
            if respiter == ALREADY_HANDLED:
                return False
            try:
                if isinstance(respiter, environ['wsgi.file_wrapper']):
                    resp.write_file(respiter)
                else:
                    for item in respiter:
                        resp.write(item)
                resp.close()
                request_time = datetime.now() - request_start
                self.log.access(resp, req, environ, request_time)
            finally:
                if hasattr(respiter, "close"):
                    respiter.close()
            if resp.should_close():
                raise StopIteration()
        except Exception:
            if resp and resp.headers_sent:
                # If the requests have already been sent, we should close the
                # connection to indicate the error.
                self.log.exception("Error handling request")
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                except socket.error:
                    pass
                raise StopIteration()
            raise
        finally:
            try:
                self.cfg.post_request(self, req, environ, resp)
            except Exception:
                self.log.exception("Exception in post_request hook")
        return True

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

from datetime import datetime
import os
import signal
import sys


from gunicorn import util
from gunicorn.workers.workertmp import WorkerTmp
from gunicorn.reloader import Reloader
from gunicorn.http.errors import InvalidHeader, InvalidHeaderName, \
InvalidRequestLine, InvalidRequestMethod, InvalidHTTPVersion, \
LimitRequestLine, LimitRequestHeaders
from gunicorn.http.errors import InvalidProxyLine, ForbiddenProxyRequest
from gunicorn.http.wsgi import default_environ, Response
from gunicorn.six import MAXSIZE


class Worker(object):

    SIGNALS = [getattr(signal, "SIG%s" % x) \
            for x in "HUP QUIT INT TERM USR1 USR2 WINCH CHLD".split()]

    PIPE = []

    def __init__(self, age, ppid, sockets, app, timeout, cfg, log):
        """\
        This is called pre-fork so it shouldn't do anything to the
        current process. If there's a need to make process wide
        changes you'll want to do that in ``self.init_process()``.
        """
        self.age = age
        self.ppid = ppid
        self.sockets = sockets
        self.app = app
        self.timeout = timeout
        self.cfg = cfg
        self.booted = False

        self.nr = 0
        self.max_requests = cfg.max_requests or MAXSIZE
        self.alive = True
        self.log = log
        self.tmp = WorkerTmp(cfg)

    def __str__(self):
        return "<Worker %s>" % self.pid

    @property
    def pid(self):
        return os.getpid()

    def notify(self):
        """\
        Your worker subclass must arrange to have this method called
        once every ``self.timeout`` seconds. If you fail in accomplishing
        this task, the master process will murder your workers.
        """
        self.tmp.notify()

    def run(self):
        """\
        This is the mainloop of a worker process. You should override
        this method in a subclass to provide the intended behaviour
        for your particular evil schemes.
        """
        raise NotImplementedError()

    def init_process(self):
        """\
        If you override this method in a subclass, the last statement
        in the function should be to call this method with
        super(MyWorkerClass, self).init_process() so that the ``run()``
        loop is initiated.
        """

        # start the reloader
        if self.cfg.reload:
            def changed(fname):
                self.log.info("Worker reloading: %s modified", fname)
                os.kill(self.pid, signal.SIGTERM)
                raise SystemExit()
            Reloader(callback=changed).start()

        # set environment' variables
        if self.cfg.env:
            for k, v in self.cfg.env.items():
                os.environ[k] = v

        util.set_owner_process(self.cfg.uid, self.cfg.gid)

        # Reseed the random number generator
        util.seed()

        # For waking ourselves up
        self.PIPE = os.pipe()
        for p in self.PIPE:
            util.set_non_blocking(p)
            util.close_on_exec(p)

        # Prevent fd inheritance
        [util.close_on_exec(s) for s in self.sockets]
        util.close_on_exec(self.tmp.fileno())

        self.log.close_on_exec()

        self.init_signals()

        self.wsgi = self.app.wsgi()

        self.cfg.post_worker_init(self)

        # Enter main run loop
        self.booted = True
        self.run()

    def init_signals(self):
        # reset signaling
        [signal.signal(s, signal.SIG_DFL) for s in self.SIGNALS]
        # init new signaling
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_exit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGWINCH, self.handle_winch)
        signal.signal(signal.SIGUSR1, self.handle_usr1)
        # Don't let SIGQUIT and SIGUSR1 disturb active requests
        # by interrupting system calls
        if hasattr(signal, 'siginterrupt'):  # python >= 2.6
            signal.siginterrupt(signal.SIGQUIT, False)
            signal.siginterrupt(signal.SIGUSR1, False)

    def handle_usr1(self, sig, frame):
        self.log.reopen_files()

    def handle_exit(self, sig, frame):
        self.alive = False
        # worker_int callback
        self.cfg.worker_int(self)

    def handle_quit(self, sig, frame):
        self.alive = False
        sys.exit(0)

    def handle_error(self, req, client, addr, exc):
        request_start = datetime.now()
        addr = addr or ('', -1)  # unix socket case
        if isinstance(exc, (InvalidRequestLine, InvalidRequestMethod,
            InvalidHTTPVersion, InvalidHeader, InvalidHeaderName,
            LimitRequestLine, LimitRequestHeaders,
            InvalidProxyLine, ForbiddenProxyRequest,)):

            status_int = 400
            reason = "Bad Request"

            if isinstance(exc, InvalidRequestLine):
                mesg = "Invalid Request Line '%s'" % str(exc)
            elif isinstance(exc, InvalidRequestMethod):
                mesg = "Invalid Method '%s'" % str(exc)
            elif isinstance(exc, InvalidHTTPVersion):
                mesg = "Invalid HTTP Version '%s'" % str(exc)
            elif isinstance(exc, (InvalidHeaderName, InvalidHeader,)):
                mesg = "%s" % str(exc)
                if not req and hasattr(exc, "req"):
                    req = exc.req  # for access log
            elif isinstance(exc, LimitRequestLine):
                mesg = "%s" % str(exc)
            elif isinstance(exc, LimitRequestHeaders):
                mesg = "Error parsing headers: '%s'" % str(exc)
            elif isinstance(exc, InvalidProxyLine):
                mesg = "'%s'" % str(exc)
            elif isinstance(exc, ForbiddenProxyRequest):
                reason = "Forbidden"
                mesg = "Request forbidden"
                status_int = 403

            self.log.debug("Invalid request from ip={ip}: {error}"\
                           "".format(ip=addr[0],
                                     error=str(exc),
                                    )
                          )
        else:
            self.log.exception("Error handling request")

            status_int = 500
            reason = "Internal Server Error"
            mesg = ""

        if req is not None:
            request_time = datetime.now() - request_start
            environ = default_environ(req, client, self.cfg)
            environ['REMOTE_ADDR'] = addr[0]
            environ['REMOTE_PORT'] = str(addr[1])
            resp = Response(req, client, self.cfg)
            resp.status = "%s %s" % (status_int, reason)
            resp.response_length = len(mesg)
            self.log.access(resp, req, environ, request_time)

        try:
            util.write_error(client, status_int, reason, mesg)
        except:
            self.log.debug("Failed to send error message.")

    def handle_winch(self, sig, fname):
        # Ignore SIGWINCH in worker. Fixes a crash on OpenBSD.
        return

########NEW FILE########
__FILENAME__ = geventlet
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

from functools import partial
import errno

try:
    import eventlet
except ImportError:
    raise RuntimeError("You need eventlet installed to use this worker.")

# validate the eventlet version
if eventlet.version_info < (0, 9, 7):
    raise RuntimeError("You need eventlet >= 0.9.7")


from eventlet import hubs
from eventlet.greenio import GreenSocket
from eventlet.hubs import trampoline

from gunicorn.http.wsgi import sendfile as o_sendfile
from gunicorn.workers.async import AsyncWorker

def _eventlet_sendfile(fdout, fdin, offset, nbytes):
    while True:
        try:
            return o_sendfile(fdout, fdin, offset, nbytes)
        except OSError as e:
            if e.args[0] == errno.EAGAIN:
                trampoline(fdout, write=True)
            else:
                raise

def patch_sendfile():
    from gunicorn.http import wsgi

    if o_sendfile is not None:
        setattr(wsgi, "sendfile", _eventlet_sendfile)

class EventletWorker(AsyncWorker):

    def patch(self):
        eventlet.monkey_patch(os=False)
        patch_sendfile()

    def init_process(self):
        hubs.use_hub()
        self.patch()
        super(EventletWorker, self).init_process()

    def timeout_ctx(self):
        return eventlet.Timeout(self.cfg.keepalive or None, False)

    def handle(self, listener, client, addr):
        if self.cfg.is_ssl:
            client = eventlet.wrap_ssl(client, server_side=True,
                **self.cfg.ssl_options)

        super(EventletWorker, self).handle(listener, client, addr)

        if not self.alive:
            raise eventlet.StopServe()

    def run(self):
        acceptors = []
        for sock in self.sockets:
            sock = GreenSocket(sock)
            sock.setblocking(1)
            hfun = partial(self.handle, sock)
            acceptor = eventlet.spawn(eventlet.serve, sock, hfun,
                    self.worker_connections)

            acceptors.append(acceptor)
            eventlet.sleep(0.0)

        while self.alive:
            self.notify()
            eventlet.sleep(1.0)

        self.notify()
        try:
            with eventlet.Timeout(self.cfg.graceful_timeout) as t:
                [a.wait() for a in acceptors]
        except eventlet.Timeout as te:
            if te != t:
                raise
            [a.kill() for a in acceptors]

########NEW FILE########
__FILENAME__ = ggevent
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import errno
import os
import sys
from datetime import datetime
from functools import partial
import time

_socket = __import__("socket")

# workaround on osx, disable kqueue
if sys.platform == "darwin":
    os.environ['EVENT_NOKQUEUE'] = "1"

try:
    import gevent
except ImportError:
    raise RuntimeError("You need gevent installed to use this worker.")
from gevent.pool import Pool
from gevent.server import StreamServer
from gevent.socket import wait_write, socket
from gevent import pywsgi

import gunicorn
from gunicorn.http.wsgi import base_environ
from gunicorn.workers.async import AsyncWorker
from gunicorn.http.wsgi import sendfile as o_sendfile

VERSION = "gevent/%s gunicorn/%s" % (gevent.__version__, gunicorn.__version__)

def _gevent_sendfile(fdout, fdin, offset, nbytes):
    while True:
        try:
            return o_sendfile(fdout, fdin, offset, nbytes)
        except OSError as e:
            if e.args[0] == errno.EAGAIN:
                wait_write(fdout)
            else:
                raise

def patch_sendfile():
    from gunicorn.http import wsgi

    if o_sendfile is not None:
        setattr(wsgi, "sendfile", _gevent_sendfile)


class GeventWorker(AsyncWorker):

    server_class = None
    wsgi_handler = None

    def patch(self):
        from gevent import monkey
        monkey.noisy = False

        # if the new version is used make sure to patch subprocess
        if gevent.version_info[0] == 0:
            monkey.patch_all()
        else:
            monkey.patch_all(subprocess=True)

        # monkey patch sendfile to make it none blocking
        patch_sendfile()

        # patch sockets
        sockets = []
        for s in self.sockets:
            sockets.append(socket(s.FAMILY, _socket.SOCK_STREAM,
                _sock=s))
        self.sockets = sockets


    def notify(self):
        super(GeventWorker, self).notify()
        if self.ppid != os.getppid():
            self.log.info("Parent changed, shutting down: %s", self)
            sys.exit(0)

    def timeout_ctx(self):
        return gevent.Timeout(self.cfg.keepalive, False)

    def run(self):
        servers = []
        ssl_args = {}

        if self.cfg.is_ssl:
            ssl_args = dict(server_side=True, **self.cfg.ssl_options)

        for s in self.sockets:
            s.setblocking(1)
            pool = Pool(self.worker_connections)
            if self.server_class is not None:
                environ = base_environ(self.cfg)
                environ.update({
                    "wsgi.multithread": True,
                    "SERVER_SOFTWARE": VERSION,
                })
                server = self.server_class(
                    s, application=self.wsgi, spawn=pool, log=self.log,
                    handler_class=self.wsgi_handler, environ=environ,
                    **ssl_args)
            else:
                hfun = partial(self.handle, s)
                server = StreamServer(s, handle=hfun, spawn=pool, **ssl_args)

            server.start()
            servers.append(server)

        try:
            while self.alive:
                self.notify()
                gevent.sleep(1.0)

        except KeyboardInterrupt:
            pass
        except:
            for server in servers:
                try:
                    server.stop()
                except:
                    pass
            raise

        try:
            # Stop accepting requests
            for server in servers:
                if hasattr(server, 'close'): # gevent 1.0
                    server.close()
                if hasattr(server, 'kill'):  # gevent < 1.0
                    server.kill()

            # Handle current requests until graceful_timeout
            ts = time.time()
            while time.time() - ts <= self.cfg.graceful_timeout:
                accepting = 0
                for server in servers:
                    if server.pool.free_count() != server.pool.size:
                        accepting += 1

                # if no server is accepting a connection, we can exit
                if not accepting:
                    return

                self.notify()
                gevent.sleep(1.0)

            # Force kill all active the handlers
            self.log.warning("Worker graceful timeout (pid:%s)" % self.pid)
            [server.stop(timeout=1) for server in servers]
        except:
            pass

    def handle_request(self, *args):
        try:
            super(GeventWorker, self).handle_request(*args)
        except gevent.GreenletExit:
            pass
        except SystemExit:
            pass

    if gevent.version_info[0] == 0:

        def init_process(self):
            # monkey patch here
            self.patch()

            # reinit the hub
            import gevent.core
            gevent.core.reinit()

            #gevent 0.13 and older doesn't reinitialize dns for us after forking
            #here's the workaround
            gevent.core.dns_shutdown(fail_requests=1)
            gevent.core.dns_init()
            super(GeventWorker, self).init_process()

    else:

        def init_process(self):
            # monkey patch here
            self.patch()

            # reinit the hub
            from gevent import hub
            hub.reinit()

            # then initialize the process
            super(GeventWorker, self).init_process()


class GeventResponse(object):

    status = None
    headers = None
    response_length = None

    def __init__(self, status, headers, clength):
        self.status = status
        self.headers = headers
        self.response_length = clength


class PyWSGIHandler(pywsgi.WSGIHandler):

    def log_request(self):
        start = datetime.fromtimestamp(self.time_start)
        finish = datetime.fromtimestamp(self.time_finish)
        response_time = finish - start
        resp_headers = getattr(self, 'response_headers', {})
        resp = GeventResponse(self.status, resp_headers, self.response_length)
        if hasattr(self, 'headers'):
            req_headers = [h.split(":", 1) for h in self.headers.headers]
        else:
            req_headers = []
        self.server.log.access(resp, req_headers, self.environ, response_time)

    def get_environ(self):
        env = super(PyWSGIHandler, self).get_environ()
        env['gunicorn.sock'] = self.socket
        env['RAW_URI'] = self.path
        return env


class PyWSGIServer(pywsgi.WSGIServer):
    pass


class GeventPyWSGIWorker(GeventWorker):
    "The Gevent StreamServer based workers."
    server_class = PyWSGIServer
    wsgi_handler = PyWSGIHandler

########NEW FILE########
__FILENAME__ = gtornado
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import os
import sys

try:
    import tornado.web
except ImportError:
    raise RuntimeError("You need tornado installed to use this worker.")
import tornado.httpserver
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.wsgi import WSGIContainer
from gunicorn.workers.base import Worker
from gunicorn import __version__ as gversion


class TornadoWorker(Worker):

    @classmethod
    def setup(cls):
        web = sys.modules.pop("tornado.web")
        old_clear = web.RequestHandler.clear

        def clear(self):
            old_clear(self)
            self._headers["Server"] += " (Gunicorn/%s)" % gversion
        web.RequestHandler.clear = clear
        sys.modules["tornado.web"] = web

    def handle_exit(self, sig, frame):
        if self.alive:
            super(TornadoWorker, self).handle_exit(sig, frame)
            self.stop()

    def handle_request(self):
        self.nr += 1
        if self.alive and self.nr >= self.max_requests:
            self.alive = False
            self.log.info("Autorestarting worker after current request.")
            self.stop()

    def watchdog(self):
        if self.alive:
            self.notify()

        if self.ppid != os.getppid():
            self.log.info("Parent changed, shutting down: %s", self)
            self.stop()

    def run(self):
        self.ioloop = IOLoop.instance()
        self.alive = True
        PeriodicCallback(self.watchdog, 1000, io_loop=self.ioloop).start()

        # Assume the app is a WSGI callable if its not an
        # instance of tornado.web.Application or is an
        # instance of tornado.wsgi.WSGIApplication
        app = self.wsgi
        if not isinstance(app, tornado.web.Application) or \
           isinstance(app, tornado.wsgi.WSGIApplication):
            app = WSGIContainer(app)

        # Monkey-patching HTTPConnection.finish to count the
        # number of requests being handled by Tornado. This
        # will help gunicorn shutdown the worker if max_requests
        # is exceeded.
        httpserver = sys.modules["tornado.httpserver"]
        old_connection_finish = httpserver.HTTPConnection.finish

        def finish(other):
            self.handle_request()
            old_connection_finish(other)
        httpserver.HTTPConnection.finish = finish
        sys.modules["tornado.httpserver"] = httpserver

        if self.cfg.is_ssl:
            server = tornado.httpserver.HTTPServer(app, io_loop=self.ioloop,
                    ssl_options=self.cfg.ssl_options)
        else:
            server = tornado.httpserver.HTTPServer(app,
                    io_loop=self.ioloop)

        self.server = server

        for s in self.sockets:
            s.setblocking(0)
            if hasattr(server, "add_socket"):  # tornado > 2.0
                server.add_socket(s)
            elif hasattr(server, "_sockets"):  # tornado 2.0
                server._sockets[s.fileno()] = s

        server.no_keep_alive = self.cfg.keepalive <= 0
        server.xheaders = bool(self.cfg.x_forwarded_for_header)
        server.start(num_processes=1)

        self.ioloop.start()

    def stop(self):
        if hasattr(self, 'server'):
            try:
                self.server.stop()
            except Exception:
                pass
        PeriodicCallback(self.stop_ioloop, 1000, io_loop=self.ioloop).start()

    def stop_ioloop(self):
        if not self.ioloop._callbacks and len(self.ioloop._timeouts) <= 1:
            self.ioloop.stop()

########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.
#

from datetime import datetime
import errno
import os
import select
import socket
import ssl
import sys

import gunicorn.http as http
import gunicorn.http.wsgi as wsgi
import gunicorn.util as util
import gunicorn.workers.base as base
from gunicorn import six


class SyncWorker(base.Worker):

    def run(self):
        # self.socket appears to lose its blocking status after
        # we fork in the arbiter. Reset it here.
        for s in self.sockets:
            s.setblocking(0)

        ready = self.sockets
        while self.alive:
            self.notify()

            # Accept a connection. If we get an error telling us
            # that no connection is waiting we fall down to the
            # select which is where we'll wait for a bit for new
            # workers to come give us some love.

            for sock in ready:
                try:
                    client, addr = sock.accept()
                    client.setblocking(1)
                    util.close_on_exec(client)
                    self.handle(sock, client, addr)

                    # Keep processing clients until no one is waiting. This
                    # prevents the need to select() for every client that we
                    # process.
                    continue

                except socket.error as e:
                    if e.args[0] not in (errno.EAGAIN, errno.ECONNABORTED,
                            errno.EWOULDBLOCK):
                        raise

            # If our parent changed then we shut down.
            if self.ppid != os.getppid():
                self.log.info("Parent changed, shutting down: %s", self)
                return

            try:
                self.notify()

                # if no timeout is given the worker will never wait and will
                # use the CPU for nothing. This minimal timeout prevent it.
                timeout = self.timeout or 0.5

                ret = select.select(self.sockets, [], self.PIPE, timeout)
                if ret[0]:
                    ready = ret[0]
                    continue
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    ready = self.sockets
                    continue
                if e.args[0] == errno.EBADF:
                    if self.nr < 0:
                        ready = self.sockets
                        continue
                    else:
                        return
                raise

    def handle(self, listener, client, addr):
        req = None
        try:
            if self.cfg.is_ssl:
                client = ssl.wrap_socket(client, server_side=True,
                    **self.cfg.ssl_options)

            parser = http.RequestParser(self.cfg, client)
            req = six.next(parser)
            self.handle_request(listener, req, client, addr)
        except http.errors.NoMoreData as e:
            self.log.debug("Ignored premature client disconnection. %s", e)
        except StopIteration as e:
            self.log.debug("Closing connection. %s", e)
        except ssl.SSLError as e:
            if e.args[0] == ssl.SSL_ERROR_EOF:
                self.log.debug("ssl connection closed")
                client.close()
            else:
                self.log.debug("Error processing SSL request.")
                self.handle_error(req, client, addr, e)
        except socket.error as e:
            if e.args[0] not in (errno.EPIPE, errno.ECONNRESET):
                self.log.exception("Socket error processing request.")
            else:
                if e.args[0] == errno.ECONNRESET:
                    self.log.debug("Ignoring connection reset")
                else:
                    self.log.debug("Ignoring EPIPE")
        except Exception as e:
            self.handle_error(req, client, addr, e)
        finally:
            util.close(client)

    def handle_request(self, listener, req, client, addr):
        environ = {}
        resp = None
        try:
            self.cfg.pre_request(self, req)
            request_start = datetime.now()
            resp, environ = wsgi.create(req, client, addr,
                    listener.getsockname(), self.cfg)
            # Force the connection closed until someone shows
            # a buffering proxy that supports Keep-Alive to
            # the backend.
            resp.force_close()
            self.nr += 1
            if self.nr >= self.max_requests:
                self.log.info("Autorestarting worker after current request.")
                self.alive = False
            respiter = self.wsgi(environ, resp.start_response)
            try:
                if isinstance(respiter, environ['wsgi.file_wrapper']):
                    resp.write_file(respiter)
                else:
                    for item in respiter:
                        resp.write(item)
                resp.close()
                request_time = datetime.now() - request_start
                self.log.access(resp, req, environ, request_time)
            finally:
                if hasattr(respiter, "close"):
                    respiter.close()
        except socket.error:
            exc_info = sys.exc_info()
            # pass to next try-except level
            six.reraise(exc_info[0], exc_info[1], exc_info[2])
        except Exception:
            if resp and resp.headers_sent:
                # If the requests have already been sent, we should close the
                # connection to indicate the error.
                self.log.exception("Error handling request")
                try:
                    client.shutdown(socket.SHUT_RDWR)
                    client.close()
                except socket.error:
                    pass
                raise StopIteration()
            raise
        finally:
            try:
                self.cfg.post_request(self, req, environ, resp)
            except Exception:
                self.log.exception("Exception in post_request hook")

########NEW FILE########
__FILENAME__ = workertmp
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import os
import platform
import tempfile

from gunicorn import util

PLATFORM = platform.system()
IS_CYGWIN = PLATFORM.startswith('CYGWIN')


class WorkerTmp(object):

    def __init__(self, cfg):
        old_umask = os.umask(cfg.umask)
        fdir = cfg.worker_tmp_dir
        if fdir and not os.path.isdir(fdir):
            raise RuntimeError("%s doesn't exist. Can't create workertmp." % fdir)
        fd, name = tempfile.mkstemp(prefix="wgunicorn-", dir=fdir)

        # allows the process to write to the file
        util.chown(name, cfg.uid, cfg.gid)
        os.umask(old_umask)

        # unlink the file so we don't leak tempory files
        try:
            if not IS_CYGWIN:
                util.unlink(name)
            self._tmp = os.fdopen(fd, 'w+b', 1)
        except:
            os.close(fd)
            raise

        self.spinner = 0

    def notify(self):
        try:
            self.spinner = (self.spinner + 1) % 2
            os.fchmod(self._tmp.fileno(), self.spinner)
        except AttributeError:
            # python < 2.6
            self._tmp.truncate(0)
            os.write(self._tmp.fileno(), b"X")

    def last_update(self):
        return os.fstat(self._tmp.fileno()).st_ctime

    def fileno(self):
        return self._tmp.fileno()

    def close(self):
        return self._tmp.close()

########NEW FILE########
__FILENAME__ = test_cfg
bind = "unix:/tmp/bar/baz"
workers = 3
proc_name = "fooey"
default_proc_name = "blurgh"
########NEW FILE########
__FILENAME__ = 001
from gunicorn.http.errors import NoMoreData
request = NoMoreData
########NEW FILE########
__FILENAME__ = 002
from gunicorn.http.errors import InvalidRequestLine
request = InvalidRequestLine

########NEW FILE########
__FILENAME__ = 003
from gunicorn.http.errors import InvalidRequestMethod
request = InvalidRequestMethod
########NEW FILE########
__FILENAME__ = 004
from gunicorn.http.errors import InvalidHTTPVersion
request = InvalidHTTPVersion
########NEW FILE########
__FILENAME__ = 005
from gunicorn.http.errors import InvalidHeaderName
request = InvalidHeaderName
########NEW FILE########
__FILENAME__ = 006
from gunicorn.http.errors import LimitRequestLine
request = LimitRequestLine

########NEW FILE########
__FILENAME__ = 007
from gunicorn.http.errors import LimitRequestHeaders
request = LimitRequestHeaders

########NEW FILE########
__FILENAME__ = 008
from gunicorn.http.errors import LimitRequestHeaders
request = LimitRequestHeaders

########NEW FILE########
__FILENAME__ = 009
from gunicorn.http.errors import LimitRequestHeaders
request = LimitRequestHeaders

########NEW FILE########
__FILENAME__ = 010
from gunicorn.config import Config
from gunicorn.http.errors import LimitRequestHeaders

request = LimitRequestHeaders
cfg = Config()
cfg.set('limit_request_field_size', 10)

########NEW FILE########
__FILENAME__ = 011
from gunicorn.config import Config
from gunicorn.http.errors import LimitRequestHeaders

request = LimitRequestHeaders
cfg = Config()
cfg.set('limit_request_fields', 2)

########NEW FILE########
__FILENAME__ = 012
from gunicorn.config import Config
from gunicorn.http.errors import LimitRequestHeaders

request = LimitRequestHeaders
cfg = Config()
cfg.set('limit_request_field_size', 98)

########NEW FILE########
__FILENAME__ = 013
from gunicorn.config import Config
from gunicorn.http.errors import LimitRequestHeaders

request = LimitRequestHeaders
cfg = Config()
cfg.set('limit_request_field_size', 14)

########NEW FILE########
__FILENAME__ = 014
from gunicorn.http.errors import InvalidHeader

request = InvalidHeader

########NEW FILE########
__FILENAME__ = 015
from gunicorn.http.errors import InvalidHeader

request = InvalidHeader

########NEW FILE########
__FILENAME__ = pp_01
from gunicorn.config import Config
from gunicorn.http.errors import InvalidProxyLine

cfg = Config()
cfg.set("proxy_protocol", True)

request = InvalidProxyLine

########NEW FILE########
__FILENAME__ = pp_02
from gunicorn.config import Config
from gunicorn.http.errors import InvalidProxyLine

cfg = Config()
cfg.set('proxy_protocol', True)

request = InvalidProxyLine

########NEW FILE########
__FILENAME__ = 001
request = {
    "method": "PUT",
    "uri": uri("/stuff/here?foo=bar"),
    "version": (1, 0),
    "headers": [
        ("SERVER", "http://127.0.0.1:5984"),
        ("CONTENT-TYPE", "application/json"),
        ("CONTENT-LENGTH", "14")
    ],
    "body": b'{"nom": "nom"}'
}

########NEW FILE########
__FILENAME__ = 002
request = {
    "method": "GET",
    "uri": uri("/test"),
    "version": (1, 1),
    "headers": [
        ("USER-AGENT", "curl/7.18.0 (i486-pc-linux-gnu) libcurl/7.18.0 OpenSSL/0.9.8g zlib/1.2.3.3 libidn/1.1"),
        ("HOST", "0.0.0.0=5000"),
        ("ACCEPT", "*/*")
    ],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 003
request = {
    "method": "GET",
    "uri": uri("/favicon.ico"),
    "version": (1, 1),
    "headers": [
        ("HOST", "0.0.0.0=5000"),
        ("USER-AGENT", "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9) Gecko/2008061015 Firefox/3.0"),
        ("ACCEPT", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("ACCEPT-LANGUAGE", "en-us,en;q=0.5"),
        ("ACCEPT-ENCODING", "gzip,deflate"),
        ("ACCEPT-CHARSET", "ISO-8859-1,utf-8;q=0.7,*;q=0.7"),
        ("KEEP-ALIVE", "300"),
        ("CONNECTION", "keep-alive")
    ],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 004
request = {
    "method": "GET",
    "uri": uri("/silly"),
    "version": (1, 1),
    "headers": [
        ("AAAAAAAAAAAAA", "++++++++++")
    ],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 005
request = {
    "method": "GET",
    "uri": uri("/forums/1/topics/2375?page=1#posts-17408"),
    "version": (1, 1),
    "headers": [],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 006
request = {
    "method": "GET",
    "uri": uri("/get_no_headers_no_body/world"),
    "version": (1, 1),
    "headers": [],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 007
request = {
    "method": "GET",
    "uri": uri("/get_one_header_no_body"),
    "version": (1, 1),
    "headers": [
        ("ACCEPT", "*/*")
    ],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 008
request = {
    "method": "GET",
    "uri": uri("/unusual_content_length"),
    "version": (1, 0),
    "headers": [
        ("CONTENT-LENGTH", "5")
    ],
    "body": b"HELLO"
}

########NEW FILE########
__FILENAME__ = 009
request = {
    "method": "POST",
    "uri": uri("/post_identity_body_world?q=search#hey"),
    "version": (1, 1),
    "headers": [
        ("ACCEPT", "*/*"),
        ("TRANSFER-ENCODING", "identity"),
        ("CONTENT-LENGTH", "5")
    ],
    "body": b"World"
}

########NEW FILE########
__FILENAME__ = 010
request = {
    "method": "POST",
    "uri": uri("/post_chunked_all_your_base"),
    "version": (1, 1),
    "headers": [
        ("TRANSFER-ENCODING", "chunked"),
    ],
    "body": b"all your base are belong to us"
}

########NEW FILE########
__FILENAME__ = 011
request = {
    "method": "POST",
    "uri": uri("/two_chunks_mult_zero_end"),
    "version": (1, 1),
    "headers": [
        ("TRANSFER-ENCODING", "chunked")
    ],
    "body": b"hello world"
}

########NEW FILE########
__FILENAME__ = 012
request = {
    "method": "POST",
    "uri": uri("/chunked_w_trailing_headers"),
    "version": (1, 1),
    "headers": [
        ("TRANSFER-ENCODING", "chunked")
    ],
    "body": b"hello world",
    "trailers": [
        ("VARY", "*"),
        ("CONTENT-TYPE", "text/plain")
    ]
}

########NEW FILE########
__FILENAME__ = 013
request = {
    "method": "POST",
    "uri": uri("/chunked_w_extensions"),
    "version": (1, 1),
    "headers": [
        ("TRANSFER-ENCODING", "chunked")
    ],
    "body": b"hello world"
}

########NEW FILE########
__FILENAME__ = 014
request = {
    "method": "GET",
    "uri": uri('/with_"quotes"?foo="bar"'),
    "version": (1, 1),
    "headers": [],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 015
request = {
    "method": "GET",
    "uri": uri("/test"),
    "version": (1, 0),
    "headers": [
        ("HOST", "0.0.0.0:5000"),
        ("USER-AGENT", "ApacheBench/2.3"),
        ("ACCEPT", "*/*")
    ],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 016
certificate = """-----BEGIN CERTIFICATE-----\r\n
    MIIFbTCCBFWgAwIBAgICH4cwDQYJKoZIhvcNAQEFBQAwcDELMAkGA1UEBhMCVUsx\r\n
    ETAPBgNVBAoTCGVTY2llbmNlMRIwEAYDVQQLEwlBdXRob3JpdHkxCzAJBgNVBAMT\r\n
    AkNBMS0wKwYJKoZIhvcNAQkBFh5jYS1vcGVyYXRvckBncmlkLXN1cHBvcnQuYWMu\r\n
    dWswHhcNMDYwNzI3MTQxMzI4WhcNMDcwNzI3MTQxMzI4WjBbMQswCQYDVQQGEwJV\r\n
    SzERMA8GA1UEChMIZVNjaWVuY2UxEzARBgNVBAsTCk1hbmNoZXN0ZXIxCzAJBgNV\r\n
    BAcTmrsogriqMWLAk1DMRcwFQYDVQQDEw5taWNoYWVsIHBhcmQYJKoZIhvcNAQEB\r\n
    BQADggEPADCCAQoCggEBANPEQBgl1IaKdSS1TbhF3hEXSl72G9J+WC/1R64fAcEF\r\n
    W51rEyFYiIeZGx/BVzwXbeBoNUK41OK65sxGuflMo5gLflbwJtHBRIEKAfVVp3YR\r\n
    gW7cMA/s/XKgL1GEC7rQw8lIZT8RApukCGqOVHSi/F1SiFlPDxuDfmdiNzL31+sL\r\n
    0iwHDdNkGjy5pyBSB8Y79dsSJtCW/iaLB0/n8Sj7HgvvZJ7x0fr+RQjYOUUfrePP\r\n
    u2MSpFyf+9BbC/aXgaZuiCvSR+8Snv3xApQY+fULK/xY8h8Ua51iXoQ5jrgu2SqR\r\n
    wgA7BUi3G8LFzMBl8FRCDYGUDy7M6QaHXx1ZWIPWNKsCAwEAAaOCAiQwggIgMAwG\r\n
    1UdEwEB/wQCMAAwEQYJYIZIAYb4QgHTTPAQDAgWgMA4GA1UdDwEB/wQEAwID6DAs\r\n
    BglghkgBhvhCAQ0EHxYdVUsgZS1TY2llbmNlIFVzZXIgQ2VydGlmaWNhdGUwHQYD\r\n
    VR0OBBYEFDTt/sf9PeMaZDHkUIldrDYMNTBZMIGaBgNVHSMEgZIwgY+AFAI4qxGj\r\n
    loCLDdMVKwiljjDastqooXSkcjBwMQswCQYDVQQGEwJVSzERMA8GA1UEChMIZVNj\r\n
    aWVuY2UxEjAQBgNVBAsTCUF1dGhvcml0eTELMAkGA1UEAxMCQ0ExLTArBgkqhkiG\r\n
    9w0BCQEWHmNhLW9wZXJhdG9yQGdyaWQtc3VwcG9ydC5hYy51a4IBADApBgNVHRIE\r\n
    IjAggR5jYS1vcGVyYXRvckBncmlkLXN1cHBvcnQuYWMudWswGQYDVR0gBBIwEDAO\r\n
    BgwrBgEEAdkvAQEBAQYwPQYJYIZIAYb4QgEEBDAWLmh0dHA6Ly9jYS5ncmlkLXN1\r\n
    cHBvcnQuYWMudmT4sopwqlBWsvcHViL2NybC9jYWNybC5jcmwwPQYJYIZIAYb4Qg\r\n
    EDBDAWLmh0dHA6Ly9jYS5ncmlkLXN1cHBvcnQuYWMudWsvcHViL2NybC9jYWNybC\r\n
    5jcmwwPwYDVR0fBDgwNjA0oDKgMIYuaHR0cDovL2NhLmdyaWQt5hYy51ay9wdWIv\r\n
    Y3JsL2NhY3JsLmNybDANBgkqhkiG9w0BAQUFAAOCAQEAS/U4iiooBENGW/Hwmmd3\r\n
    XCy6Zrt08YjKCzGNjorT98g8uGsqYjSxv/hmi0qlnlHs+k/3Iobc3LjS5AMYr5L8\r\n
    UO7OSkgFFlLHQyC9JzPfmLCAugvzEbyv4Olnsr8hbxF1MbKZoQxUZtMVu29wjfXk\r\n
    hTeApBv7eaKCWpSp7MCbvgzm74izKhu3vlDk9w6qVrxePfGgpKPqfHiOoGhFnbTK\r\n
    wTC6o2xq5y0qZ03JonF7OJspEd3I5zKY3E+ov7/ZhW6DqT8UFvsAdjvQbXyhV8Eu\r\n
    Yhixw1aKEPzNjNowuIseVogKOLXxWI5vAi5HgXdS0/ES5gDGsABo4fqovUKlgop3\r\n
    RA==\r\n
    -----END CERTIFICATE-----""".replace("\n\n", "\n")

request = {
    "method": "GET",
    "uri": uri("/"),
    "version": (1, 1),
    "headers": [("X-SSL-CERT", certificate)],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 017
request = {
    "method": "GET",
    "uri": uri("/stuff/here?foo=bar"),
    "version": (1, 0),
    "headers": [
        ("IF-MATCH", "bazinga!"),
        ("IF-MATCH", "large-sound")
    ],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 018
req1 = {
    "method": "GET",
    "uri": uri("/first"),
    "version": (1, 1),
    "headers": [],
    "body": b""
}

req2 = {
    "method": "GET",
    "uri": uri("/second"),
    "version": (1, 1),
    "headers": [],
    "body": b""
}

request = [req1, req2]

########NEW FILE########
__FILENAME__ = 019
request = {
    "method": "GET",
    "uri": uri("/first"),
    "version": (1, 0),
    "headers": [],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 020
request = {
    "method": "GET",
    "uri": uri("/first"),
    "version": (1, 0),
    "headers": [('CONTENT-LENGTH', '24')],
    "body": b"GET /second HTTP/1.1\r\n\r\n"
}

########NEW FILE########
__FILENAME__ = 021
request = {
    "method": "GET",
    "uri": uri("/first"),
    "version": (1, 1),
    "headers": [("CONNECTION", "Close")],
    "body": b""
}

########NEW FILE########
__FILENAME__ = 022
req1 = {
    "method": "GET",
    "uri": uri("/first"),
    "version": (1, 0),
    "headers": [("CONNECTION", "Keep-Alive")],
    "body": b""
}

req2 = {
    "method": "GET",
    "uri": uri("/second"),
    "version": (1, 1),
    "headers": [],
    "body": b""
}

request = [req1, req2]

########NEW FILE########
__FILENAME__ = 023
req1 = {
    "method": "POST",
    "uri": uri("/two_chunks_mult_zero_end"),
    "version": (1, 1),
    "headers": [
        ("TRANSFER-ENCODING", "chunked")
    ],
    "body": b"hello world"
}

req2 = {
    "method": "GET",
    "uri": uri("/second"),
    "version": (1, 1),
    "headers": [],
    "body": b""
}

request = [req1, req2]

########NEW FILE########
__FILENAME__ = 024
from gunicorn.config import Config
from gunicorn.http.errors import LimitRequestHeaders

cfg = Config()
cfg.set('limit_request_line', 0)
cfg.set('limit_request_field_size', 0)
request = {
    "method": "PUT",
    "uri":
    uri("/q=08aP8931Ltyl9nqyJvjMaRCOgDV3uONtAdHABjoZUG6KAP6h3Vh97O3GJjjovXYgNdrhxc7TriXoAmeehZMJx88EyhcPXO0f09Nvd128SZnxZ2r5jFDELkn26reKRysODSLBZLfjU3vxLzLXKWeFOFJKcZYRH9V7hC98DDS4ZsS7weUksBuK6m86aLNHHHB0Xbyxv1TiDbOWYIzKxV0eZKyk0CaDLDiR0CRuMOf4rwBeuHoMrumzafrFI5iL72ANQZmOvKdk1qQeXkRqEG11YU0kF7f1hSlmgiIgg5maWiBsA9sAg36IIXZMWwJF63zpMgAyjTT8l4pQhSBfhY2xbGAWmLGpyd1rlBm0O5LCoKpnQuTACm2azi0x6a1Qbry9flQBO4jHge2dXiD1si6Gh5q8fZu8ZQ7LLWii2u4rGB7E4XlhnClrCHg5vJmjYf2AItYPA0ogsiIdEEQGpzMJPqrp8Icn5kAAimWF1aCYaDjcdSgWI48PnoxlzIHX50EPFcPOSLecjkstD9z66H554sUXfWn3Mk9lnOUlse6nx0u1YClFK4UFXp98ru9eBBr7pkAsfZ34yPskayGyXPPyzWyBfVd28UuvdEG47SMdyqEpX0rFdk67fAYij0PWMK79mDmGAS37O821o18XUbu0GQjsqAGVMN9LDIAliD9QqtlwdEnplKkUyyZ7GAFJCFffgzppU9CjA2FbPX6ZjTOi4sPoYEyhyeQKVqAe9keYeDpU2qDwq83XEDQUKvP0w48GyavSmdBcrMXjUsu0PfdYpSaKwarrUB3i93HgoQB3ZJIR4lW6iPRTmm28OEKq2MIJGAoTXxCZYM5UacRldlqQOj6JkYz6y7ppWOjJ9yiCUEenuvfcItgmw9HIgGA59JxO8NDLEZLSONfuIgiV7wjsJnxuTOlU4vkjV7fTuOeU91xez7UKhaTqqEW3XBUSLjhKi3IkZg7ukrGZTWPhijFv2EZwEWDAyLlHvZB4X738zGJUlEX1k52EHwrKVKdLfePcaOjAGKsongHBFYxYC8vBBLuKm9RWexKCT14M25pCGloJXZ4OpBRfDQA2kobLUcEXEpzqRBPGN2JdNSBOFlUtUxWKnnPBM6r9S356l3k1o9zTIPeoIitWRjASs4A0iwYc8p5vv5Kt8KtsmW7Xv8dlU8HbZHsy3LI7O9BpUH8cJubqdEhooKABkx71pdcsZGhZb6epyTiPyvOhdJ7tNtFy3KQOameqTgGyd53Z42eZ0AjaOEvnzermi2E0xo3MMHFhB74TFtNAI3ppxxyqknc1mzUqZ49Wi8YPBg9ids6IgZvddBQYvwEozkmyGAkatQtt9TD4LjU3TyyUlhNG21q7CzEEl8NNsVrV6QyHsfw7E5w7XcoT7OQkBYoZwHIAjfekehnpc2llRtRY5m43fPVasmsVazOR36DRSLZJPHAqUDO0LInu9mgP57Mnz9CgylEmdE2aaYs426rnTFR3G3CfjLofHfjaLOkAegr4W3jx6MNMMOMZw2u46YTCnlfbBK6ZA1UYeAH1DIQJykcSQESinC8HpYIJt9A8g7UT0awzRP1F9nHa3wDnaAHndQYKMrjzlWo8ejQ0XHWgHhqnWHgW4h9sOnJckH00CYK1fHUKASJ3D8kOKax6uplexfz6BCvAoL9zm5TjeB1yxrpLp9NjjTWSKG2HOZhPkGpdEqU4mjnN2AkUVACPGos5YLBmTnSrdOEGZJDlAvJOUt800Mu3BYc1MiDIB6LMSSV5RsIUDFOzNletGQoq4G3yHZmx78uEse5vUTPFF3KT8LCrssqdIU9H97Npgf6N5j8arQ7ykLzN459jJaUzpGIo6uowPnUSatDf9GAvAmWNvsVTz6bYiAV71C7QF0C7UolYIQY6DHJEHejgX2YMEovWNLPL50eeC51h4DdPNv5G4ZdNtQTRVybYBZMpetGDiFmXN0JKa1sKHOSZxdrhKjxDIhrYVyCcRUMQ0sjGGHFuOcRszr6E5igEMtsebHQ3KYiGd5B27LikpUHhk61rgZlulHdMoS6YgQs6SV6UMVNku6sCw529xhUciDwRMhsbAjDlahYbrGa3NryxyV5LrXONGGKCchCqv7vDMdAtPrVr8M2vL5MySQAC3g90iugGQcLH3hCf9f1Kn5X0hM4KZTfwOPJhlfJsMRNhssiDoXaycUvOUS58266yPDlitPIAzO03XClm4EDPXGIwcwiFr7FcDo3tQIMZVy87i48Zb80s3zAYRiBIS0vO3RKGx3OGN5zid2B7MfnfLzvpvgZoirHhAqXffnym5abpZNzGuo5GowTRA2Ptk4Ve2JFoHACWpD6HiGnRZ9QVOmPICoQrSUQw45Jlk9onKJz5Erhnx0943Uno6tMJ5jbrWBNiIO7i04xzRBgujeiAJvuQkVDX2QLKRxZ7s6rhdfOaq6R6uL108gEzzlXOLqTTJXgM63rcUWNbE7wsIXcCFSF59LLJ7G5Qea33suxdDX6DcK4a0VMZoxmWPtCi1dAT9ggJqc2Sh7mkAqizaB16RXZvSydchpdVj6s4qn4ivr0HKHdAstX0XZ0FFU6lOiNmU3vasMg2uaVG8tyuG8N8VsuXIOQs7xtFxDhilYb8MQ9vES9pWfWPSXFlJAq4XKPY8a0JOIx57EQuWHo3uWgRTIRThvZP9YYzSnjGIHwjS8JeppICHofADXZhJ0uDQaQs7MiXEALpGmT3W6w0G3tBdZcuTDkWx1HsT5jd9jQeJpgD2VxdKh8U4Q3vANTAuwBXLJ2P0stS8Q72JWgNPwKYTY9cPoaGZlUFGgVsq8CdEFH9yW0c27G5s5sfHsyep6t4VxIHHMOX2GmMRyGxDI33am1J7ZmJ1NyXiwkHxtPH5QBpU2PMu2Guf3xIxlk3snMkMAsGO0vYfqO9tdIgdxMYO3HZTYv99OXaHcNQ5u0pRZZyVrNOIPurkEOdJy0nowPemIgUuHWh8vQCuDZav1m35AOl6ftSFuChSm5KstEWnC7q8mJ0juJEBkCRmQphP3V1pqiDjz6YA90qEe7MA3nzT0nHG8A1hWlqcPVPNz4qWNF6Fq1ub4075aXO0H7Krb6rhWGb3ZRPjpb4BKN8jGFQrBUMZprtjAJ67BnfmYgE0mmGLV2QP10gYS1T06kBRyrtp7he6wsPiBPJ7wxPLHNUN2SGQHBTSKagndM99fuaga5Sw9OT8Fzdo7xUJXfhJ97gUnNDrknal0B00NMNvajZeQQTJyBsVSwBZtZ45ZCcq1idc7GWC0MITSk58cIVkSPXbrERUaygyY13dPeEVzjVi9aVJwUF6eJu1s8u3FCJqp2GoWIItwvZO69asX75fekFkmFpNavxM0X0dZC01TTPpV6E6PJoIfW8C06CKNHV7Gk2mkTWGSwUG4xD2L3G3XarodHDcmumFJX9Xviv0rvm38SCtin6OpjH8MHYDrj1OxTJbC2VclJxv73z2BDBquosKOik0fmgbPZN0FUTmjBEwHTvqd5QHTwb3nOpEz3X6YCF0lrcrQc0uhyr7gBGBs86nUBWFRp1LKjIRVTVXDipajqNDTQGNZtzvR9MUf1yJJV07inbrlPOENd7rHpKCrJtoZXOkDqInaIqoMCG3DVd353BGmZNJEKOa3DnL7fb9zwuHlvHAfCco7ZS4wAV87trWkp6skXux9v5WhkumbUyGq4ia6DM1PuqqnFfBTAWDzJsnggAJrzr8O7JbDtaXwcW9sqaOb0S6NvnUDZqiNdDQPMDOKvXRJJJQdf1FSrPCCSPEEWO1SeVwictj7rTbpWGRoukwhgJALys95pGGOQxCPzRGrtVFnGcsLN1CwI3wLbmDnNKUv3KpOLEOPRxQXeXuJRIiYCFum44c0wNr731DvHn3YEJMH4iwFONl1rolEL4w6KFUOCq7ekrE5iyUt1V32PNtuUshXRjOYjBval29JMH5GoqZlGhCczzHMA61cmuzqdFwiPCB9yzqvJTg8TqMNvwKJztFIQK4mc5Ev5rRVSozD796AVRKT8rZF39IA1kmCLdXqz7CCC8x4QjjDpxjKCXP5HkWf9mp2FNBjE3pAeaEc6Vk2ENLlW8WVCe08aP8931Ltyl9nqyJvjMaRCOgDV3uONtAdHABjoZUG6KAP6h3Vh97O3GJjjovXYgNdrhxc7TriXoAmeehZMJx88EyhcPXO0f09Nvd128SZnxZ2r5jFDELkn26reKRysODSLBZLfjU3vxLzLXKWeFOFJKcZYRH9V7hC98DDS4ZsS7weUksBuK6m86aLNHHHB0Xbyxv1TiDbOWYIzKxV0eZKyk0CaDLDiR0CRuMOf4rwBeuHoMrumzafrFI5iL72ANQZmOvKdk1qQeXkRqEG11YU0kF7f1hSlmgiIgg5maWiBsA9sAg36IIXZMWwJF63zpMgAyjTT8l4pQhSBfhY2xbGAWmLGpyd1rlBm0O5LCoKpnQuTACm2azi0x6a1Qbry9flQBO4jHge2dXiD1si6Gh5q8fZu8ZQ7LLWii2u4rGB7E4XlhnClrCHg5vJmjYf2AItYPA0ogsiIdEEQGpzMJPqrp8Icn5kAAimWF1aCYaDjcdSgWI48PnoxlzIHX50EPFcPOSLecjkstD9z66H554sUXfWn3Mk9lnOUlse6nx0u1YClFK4UFXp98ru9eBBr7pkAsfZ34yPskayGyXPPyzWyBfVd28UuvdEG47SMdyqEpX0rFdk67fAYij0PWMK79mDmGAS37O821o18XUbu0GQjsqAGVMN9LDIAliD9QqtlwdEnplKkUyyZ7GAFJCFffgzppU9CjA2FbPX6ZjTOi4sPoYEyhyeQKVqAe9keYeDpU2qDwq83XEDQUKvP0w48GyavSmdBcrMXjUsu0PfdYpSaKwarrUB3i93HgoQB3ZJIR4lW6iPRTmm28OEKq2MIJGAoTXxCZYM5UacRldlqQOj6JkYz6y7ppWOjJ9yiCUEenuvfcItgmw9HIgGA59JxO8NDLEZLSONfuIgiV7wjsJnxuTOlU4vkjV7fTuOeU91xez7UKhaTqqEW3XBUSLjhKi3IkZg7ukrGZTWPhijFv2EZwEWDAyLlHvZB4X738zGJUlEX1k52EHwrKVKdLfePcaOjAGKsongHBFYxYC8vBBLuKm9RWexKCT14M25pCGloJXZ4OpBRfDQA2kobLUcEXEpzqRBPGN2JdNSBOFlUtUxWKnnPBM6r9S356l3k1o9zTIPeoIitWRjASs4A0iwYc8p5vv5Kt8KtsmW7Xv8dlU8HbZHsy3LI7O9BpUH8cJubqdEhooKABkx71pdcsZGhZb6epyTiPyvOhdJ7tNtFy3KQOameqTgGyd53Z42eZ0AjaOEvnzermi2E0xo3MMHFhB74TFtNAI3ppxxyqknc1mzUqZ49Wi8YPBg9ids6IgZvddBQYvwEozkmyGAkatQtt9TD4LjU3TyyUlhNG21q7CzEEl8NNsVrV6QyHsfw7E5w7XcoT7OQkBYoZwHIAjfekehnpc2llRtRY5m43fPVasmsVazOR36DRSLZJPHAqUDO0LInu9mgP57Mnz9CgylEmdE2aaYs426rnTFR3G3CfjLofHfjaLOkAegr4W3jx6MNMMOMZw2u46YTCnlfbBK6ZA1UYeAH1DIQJykcSQESinC8HpYIJt9A8g7UT0awzRP1F9nHa3wDnaAHndQYKMrjzlWo8ejQ0XHWgHhqnWHgW4h9sOnJckH00CYK1fHUKASJ3D8kOKax6uplexfz6BCvAoL9zm5TjeB1yxrpLp9NjjTWSKG2HOZhPkGpdEqU4mjnN2AkUVACPGos5YLBmTnSrdOEGZJDlAvJOUt800Mu3BYc1MiDIB6LMSSV5RsIUDFOzNletGQoq4G3yHZmx78uEse5vUTPFF3KT8LCrssqdIU9H97Npgf6N5j8arQ7ykLzN459jJaUzpGIo6uowPnUSatDf9GAvAmWNvsVTz6bYiAV71C7QF0C7UolYIQY6DHJEHejgX2YMEovWNLPL50eeC51h4DdPNv5G4ZdNtQTRVybYBZMpetGDiFmXN0JKa1sKHOSZxdrhKjxDIhrYVyCcRUMQ0sjGGHFuOcRszr6E5igEMtsebHQ3KYiGd5B27LikpUHhk61rgZlulHdMoS6YgQs6SV6UMVNku6sCw529xhUciDwRMhsbAjDlahYbrGa3NryxyV5LrXONGGKCchCqv7vDMdAtPrVr8M2vL5MySQAC3g90iugGQcLH3hCf9f1Kn5X0hM4KZTfwOPJhlfJsMRNhssiDoXaycUvOUS58266yPDlitPIAzO03XClm4EDPXGIwcwiFr7FcDo3tQIMZVy87i48Zb80s3zAYRiBIS0vO3RKGx3OGN5zid2B7MfnfLzvpvgZoirHhAqXffnym5abpZNzGuo5GowTRA2Ptk4Ve2JFoHACWpD6HiGnRZ9QVOmPICoQrSUQw45Jlk9onKJz5Erhnx0943Uno6tMJ5jbrWBNiIO7i04xzRBgujeiAJvuQkVDX2QLKRxZ7s6rhdfOaq6R6uL108gEzzlXOLqTTJXgM63rcUWNbE7wsIXcCFSF59LLJ7G5Qea33suxdDX6DcK4a0VMZoxmWPtCi1dAT9ggJqc2Sh7mkAqizaB16RXZvSydchpdVj6s4qn4ivr0HKHdAstX0XZ0FFU6lOiNmU3vasMg2uaVG8tyuG8N8VsuXIOQs7xtFxDhilYb8MQ9vES9pWfWPSXFlJAq4XKPY8a0JOIx57EQuWHo3uWgRTIRThvZP9YYzSnjGIHwjS8JeppICHofADXZhJ0uDQaQs7MiXEALpGmT3W6w0G3tBdZcuTDkWx1HsT5jd9jQeJpgD2VxdKh8U4Q3vANTAuwBXLJ2P0stS8Q72JWgNPwKYTY9cPoaGZlUFGgVsq8CdEFH9yW0c27G5s5sfHsyep6t4VxIHHMOX2GmMRyGxDI33am1J7ZmJ1NyXiwkHxtPH5QBpU2PMu2Guf3xIxlk3snMkMAsGO0vYfqO9tdIgdxMYO3HZTYv99OXaHcNQ5u0pRZZyVrNOIPurkEOdJy0nowPemIgUuHWh8vQCuDZav1m35AOl6ftSFuChSm5KstEWnC7q8mJ0juJEBkCRmQphP3V1pqiDjz6YA90qEe7MA3nzT0nHG8A1hWlqcPVPNz4qWNF6Fq1ub4075aXO0H7Krb6rhWGb3ZRPjpb4BKN8jGFQrBUMZprtjAJ67BnfmYgE0mmGLV2QP10gYS1T06kBRyrtp7he6wsPiBPJ7wxPLHNUN2SGQHBTSKagndM99fuaga5Sw9OT8Fzdo7xUJXfhJ97gUnNDrknal0B00NMNvajZeQQTJyBsVSwBZtZ45ZCcq1idc7GWC0MITSk58cIVkSPXbrERUaygyY13dPeEVzjVi9aVJwUF6eJu1s8u3FCJqp2GoWIItwvZO69asX75fekFkmFpNavxM0X0dZC01TTPpV6E6PJoIfW8C06CKNHV7Gk2mkTWGSwUG4xD2L3G3XarodHDcmumFJX9Xviv0rvm38SCtin6OpjH8MHYDrj1OxTJbC2VclJxv73z2BDBquosKOik0fmgbPZN0FUTmjBEwHTvqd5QHTwb3nOpEz3X6YCF0lrcrQc0uhyr7gBGBs86nUBWFRp1LKjIRVTVXDipajqNDTQGNZtzvR9MUf1yJJV07inbrlPOENd7rHpKCrJtoZXOkDqInaIqoMCG3DVd353BGmZNJEKOa3DnL7fb9zwuHlvHAfCco7ZS4wAV87trWkp6skXux9v5WhkumbUyGq4ia6DM1PuqqnFfBTAWDzJsnggAJrzr8O7JbDtaXwcW9sqaOb0S6NvnUDZqiNdDQPMDOKvXRJJJQdf1FSrPCCSPEEWO1SeVwictj7rTbpWGRoukwhgJALys95pGGOQxCPzRGrtVFnGcsLN1CwI3wLbmDnNKUv3KpOLEOPRxQXeXuJRIiYCFum44c0wNr731DvHn3YEJMH4iwFONl1rolEL4w6KFUOCq7ekrE5iyUt1V32PNtuUshXRjOYjBval29JMH5GoqZlGhCczzHMA61cmuzqdFwiPCB9yzqvJTg8TqMNvwKJztFIQK4mc5Ev5rRVSozD796AVRKT8rZF39IA1kmCLdXqz7CCC8x4QjjDpxjKCXP5HkWf9mp2FNjE62a"),
    "version": (1, 0),
    "headers": [
        ("SOMEHEADER", "0X0VfvRJPKiUBYDUS0Vbdm9Rv6pQ1giLdvXeG1SbOwwEjzKceTxd5RKlt9KHVdQkZPqnZ3jLsuj67otzLqX0Q1dY1EsBI1InsyGc2Dxdr5o7W5DsBGYV0SDMyta3V9bmBJXJQ6g8R9qPtNrED4eIPvVmFY7aokhFb4TILl5UnL8qI6qqiyniYDaPVMxDlZaoCNkDbukO34fOUJD6ZN541qmjWEq1rvtAYDI77mkzWSx5zOkYd62RFmY7YKrQC5gtIVq8SBLp09Ao53S3895ABRcxjrg99lfbgLQFYwbM4FQ6ab1Ll2uybZyEU8MHPt5Czst0cRsoG819SBphxygWcCNwB93KGLi1K9eiCuAgx6Ove165KObLrvfA1rDI5hiv83Gql0UohgKtHeRmtqM0McnCO1VWAnFxpi1hxIAlBrR4w35EcaryGEKKcL34QyzD1zlF4mkQkr1EAOTgIMKoLipGUgykz7UFN1cCuWyo3CkdZvukBS3IGtEfxFuFCcnp70WTIjZxXxU4owMbWW1ER5Gsx0ilET0mzekZL0ngCikNP2BRQikRdlVBQ3eiLzDjq27UAm7ufQ9MJla8Yxd6Ea37un9DMltQwGmnmeG5pET54STq72qfY4HCerWHbCX1qwHTErMfEfIWcYldDfytUTOj7NcWRga3xW7JYpPZHdlkb24evup3lI4arY6j5a12ZcX9zVI02IJG0QD9T4zSHEV0pdVFZ8xwOlSWKuZ9VZMmRyOwmfhIPA7fDV5SP8weRlSnSCSN4YBAfzFVNfPTyeoSfVpXsxIABhXEQTg12YvAAn9390wFhEhMsT9FWIiIs7oH63tQyjdEAZSJcZ0nSQfapvi4BDsQSMv3W2DofSzxwOPrVQWRMyvP0UV0J660Gc4iZ2Tixe3DSeqg9VuNvij09aCbkBdwJh9r4UWmM1Hp1ZDF5Rr14nKtFAgjVlGlfZi4bWQKTzOlqaVbWBvxdKsJ27eelyDnasIPqo17yY5lg10Lb8nyu60Wn7l7Xb0Ndp334B5am4Vh1foctvkkhNFeIejtnjPYmWjS77rJ1aL0zJka4Xog5Oparvc93Pddf9CzCxgle00BTKNj0syVo5uqvX5PVzdhAnigU4jdPbJbcPpbpJRU4UDqIswRNJOlGfpdLnCvnPIRB2a7btjFTaE0tne0TjedGbePje1Li21rPXPX7t5LICWl1SRyqQ9x9woGEv1sI5VgpRoKtS6oxWgMERjP3LcEez3XqLiSwv0rWMlDiJhxEopz8Mklx8ZygQLiwIYx2pNq0JhKB8K1lZ8dYE5d3nRWhXwG4gFTUg2JYjnjL81WGRmjXnZEVLwYfYBUkRlqWAYHi1E6wF85BfcwvkgnEeBTiQSlfu6xwCYaW2OEogq7tbdinvlpeEPij1qQivpcs573HPHpkXrEeXC9P2gZhmV1Rvn69NAN2lOXSVe8XotSyCG5fHFsTDYlOvYW8EBrAdWuZrwU753xwjk3QCp2ODetYze98voig4lfYHrrWT43VXcHt8J5z7U3kt5O460buwESBhgkALZdrFYyy4YQcmnAeSCw5OoLArDEmzaI4JkFBCDqQxTE9BTYA112r9ymuOo5MGkTDYZlvtvopG4ekorfLoIa13Z9L6ZilXT1cg55dvNlOrbTSHpQTYRJfJ6x71IpDFyvdbZbOHQYMm98fcN9CLqFErkpcN4JO26GIhSodGGTSnzyUxBYueawFNlGxCMTa6JseX9c7Xlo8NRaZHBPvG7Z4gUCkOdUSEW0RRTs3TSSdjEKnJ6u9RdDqqyvN8cJ7gliTd04mSyVnkmxdqVU8DrdIrkSCfVQNoFgdydDHS3wMLU6QGTGBzK5pd9EfsDEeYXtIb3CkRupM4SERGMTN8TyIxqqIyWmgjBmSGLTFOB5tsPhkVydVQNf7jBkDy6THfBy0uALVUkm2jLeTFXjajyeL4ms5Lgx0eLoz0XWN6WulXSA20zV3ObSCHbBeVUgKmPxHq5qPmAi04VFIvCOJ0rBQJh9ZHJMwvhI3VEBF6EmXOiRCn0XOhm3pfHlmaCAWrOSGuQs3NCNlFRjwmVRPY5FJrKYjH3FrLrLdU07zdViAix8C4LxVrRrMB6ligZC3CoDhFA4vMjiPU5SBRqRW4lwVnvMZEZbf0AYbBc2ymnKAOWbQwt2ldiI2qL0aLoL6YtSFUhpwMOR3LP1feUq6XRO5xc9V02nEt9MRQsl5MgmKMcXap4HqAN0yATpjAGRnWqEnE7E1XZg95cEl2gO4HXejKzR0kiTUudcw6P4t1RYLRx7isZNJxiq1JZz6FpEe7QhwGbhPySNMbXJtmYuhAaTpfGdGKMxvHHB9LmELOChdyfjHMwMZ2B0xgU2eJgJimCwLH3UEmExgAwJDD4GSCqevYAMK4P9FKPl0dku0KZ7uOJ8oNloEsrbvMuhuKFDuO1PNvxtdCcgASzNVzdueOtUm1giZIDqbb6j11nqi9NoFeck1zZi2kfGF7OeUp4vYszuhQNi4vd03QeVAduM9h9v36Nz1YobRxB2CjTp6qdKdW9IYBp8aExZpipnJIbfD2hTWE44kIu7Q17f4C9kycGjsLwAWkVbfTRmBMU8SbVKV1EJTrN1gGqGX7quSwg1Vp4qslKAk6EIkoReIl5DuzuH8Rbvrkp5LFFAhNhb1hvXvVWcibtDjQSradNtuYzGf2AAduhxOTnZjzbsceGYhQA5a5NtqxE2GBlW8CPoPzIyfMfPjdAIUmAcns7Fkp44nju2htwhryUyidEzDVyTwevquARjt5a7eu8qIKfPrYgbOAlPgA1JHNi55ivTNpDuQ8drNiafZIntA43HI447WtITYYvLxFRG8OWvJRwI0N7dvHYO8H8lYI1OwatfvLKlJqjtdJBBvMWXdT4SbxHUdNTDUQmqFGZaLx1AvYPnJTYRzrqn5ZnXyWQ1ZCwtvZK209TxoezJ2sGorE46C7Zyki6EcXlX2A8upUUh9IhqLYTzidIRrAPE5mZmosyDyShjnRiN5CLXZAI21eV4v3a6WXI8TKkUk3fhhajOgPXshlyCEfDAyESpz1J8RECu6vQs81E1ZNE5ha5UGw2wk3Ea8oSTfqTiu0OeisV2a6bfldvW4x0OL8PS57uuY0v0OZPSUPWmPQgnmJRVw8vmh62bpFekMnUH7y31fXU6MIyZaiBs1FEu7qF6irBszHt2ARy50SjgGwQZWcecgvB8gB874g3ES9mZer3diYGF3Wssmsm6XRdsNcuNn3yzuoi52cRrBYUOISegTBVApn4zfuCC9Y4AAfe6wmmiuN8hL6KJeOjrdK5EFQHGyrzeuIMaT3B2nKz1PNONVQ0udbqCQebz3cq7NPe6kGKFLiE6euWjdoMuAbuu8rTkAa42ensXz4a1Yo450ZVgYypaDtepDQWFkJyTHDW1HTVZfCok0tp7STRiQ8n3NKxOUSL9veuTsDs1FaV2rbzR3DvkEJrhJ10Rm0pvLgui5GUDKyWLnrqcNVtOIzFaj9K5pwMfnREm1VIs84ePX0GsMjirfOfubzDoYjavbiCtTB86nKx0tfCKtl0yUQ5PWSBqdGASY3mr5hZcFZ9bA6uXXGTNqMpUH3gqxCoF6t2yAim93t77jYkiFt3OBlBRVQzRsPbgEKRXbX3bWQj6NpDzNCQPYTs45HsQB967f4yByzLH8X289YAZJhJJyFTMCLbpdKFuMBX5Msyr4d15sBa1h5bI13dqU14WBnMKD12LkHMjHiyde6xf5EELf082sUfiAZaROFuDCDnA89p6y6oYEUgF1L9yQElZO4R6IrkJsEFN9hvARf3CH4ENqbYxtUN9gsB9CLCGKMy2R4wGKU3Dkyea27YCR4QHCdqX3HqOpy12uxBANvbrfEro9q5NJrGK7WVq3nNabN05x4TmIZk3asc8ehvDyhSgQLY0wwyvrkcYqNiETybJ57RjwVg1YE0IZEBfyAUNXE4goc2jtbZbHfcpTzt08pSJQZTAzuxrdQLS4EnaFHPpMdPh1YXUdclj6g2sjYbhoTYcV97bVDAUztMZ4EarUcv6tgQOvK66RmJCF2zVEpFDBS6AVZJWzrVlnuiweXpH0L9eY2Wy2EuAHi7gL4o0i0AkOapqY1TPUWUwBaVrKQzkL8QQbczgc97pMvSnGYMlcSdzlamFtUmRoOPmhBGMpVqmcxnstnqJ0TXMV65zbRN2hk3YVF5HwPjuWJmfkVYnyazuqKuaaohrQIe7YOOSAmD7C2vDnI50y1oScQqIPb87QAmguFz7jfNBSPymjPJ7UrToaJen7LEQr8S2b69ayZYNIyWbcpaW5ACUqdyT5AeHYhdENORnWS2B17qnBPtyvb4WujJCafLmsMFhQbcGonDZkHEOAnOcwRwJ4KIPr4MlQLRKsdnurPDDEmpCtCnFg8vPObOPHoHgICb9j35pG1YNhAAGIGTZ4g3JTJzFvTcW7GDRxREPZffKOuQTJoMYYaaPwnE0SainEpCFAukJbDy1ss5cZt60nqTw1asLzwMKJu5PHpU9sB9YN7J2cPhIbfb4387zSmSvqbt3I8NFjDbuYEhe6nZ7gRT5Th0W0MoyzHlmy4MSXbaAfUJNsLQJmdhdVKDsqMz0aXKIVNsXtn88owrhw0yqxU0K3IfTothafhpQ8daRUnbjzULViWRvUz7dI1N3GgylRzaEXQPgbj0DQ7RujNTcJoSp7I1ELjFFSBZDm4Jx5eXq0aS2SKJPFX7XmFfkkR99wRiHx4ByVTL5umojRhY5j8vg3l3yfliJbeOTXckaYiezrucuHaiVFWR2kjk9PUm57bDpvtSFMic652iDufj4hqpy5MH5r2lg67T6Bbb3fcq49cVJ3hkN2GfRqVhoPxmHyvotu5koheVh7oHDaLaf4VvcQMd5MF8sicaX3GXfoLjlfFZwfJBpXNbbVemD7XghpIEwuFjA1USU8yJnTdvCJ2bFmPNWFeWsBVDyl7XUsbgB3K2zz806xODZT639dqiqhGXQNbgYtShikQhiHhZF4wf4IY588LE4EO2bdXBb2Wezm8Gl2J5GAfqnx5Z6NF7h1gGkM27hpnmKNylKZjqTNANj0CRU4awpdVrYGX7hT0u452Y5bXpVl7cLuK7j2k7VG93NXPsXADhQA8R9WDcpU0PLzFWFq1omoQ9ZRSlvh8R4pRp4vHIYf4A5uQEmv5Owr4pFQcWdp5GAdkpBaSHvUhvMxOSpsqVB2LHvvs1RiOUHHhHdZEKpX25mK9moud8pKT4efru1SlRRSsxdz87hTJMUrueydHDPXbo9AvExctdqxuCk03Fy8cB57qrkQQ50oGNuTNPColMrwVfmuTt81uSZremLbINILnCVXEnvTugRQfFYMnprqMB4mVJfZfh6XVLdOyW4BPaFrBsZGFy7udoWJwE8ACx4UpJW6m1ltckofzA6AUxzXprXDCCL118m8bBB2hzDKmqeLk5ZYKsLROkTqRAxmJjBSZSo2XBroO5rVvkOZrOZRe8NgaHFMLPn0I6hsqwA7VdKlpbqknax84iWrtBe8ErxgPIQeYhELyK1deW1YWBagD21MBTc2h5LliIlglZg41H8Zl3GvUv0XNZegR5bx1kiM9WFGV9Yt37iQQGquWAMKCAb6AqpkCtKs7sXKaEAVsbh32tlkAg4ngspjwzYHTPYKUuigPX5K8siUfaAW9WJl7r8dc4ju97osWETOcBENLsfwB66TvsttORtOedylnErplZP3hjt7o39JllXDobj3l10bSr4B09eYVWi2DLGavYktKSKj1PrqzuGUaqcFxqoebpuDEAx5vl8ZmSYrmS2RBJ1n2s3lkKdaVWTmfIXlyMMT7Ac3lCXpGNnpf8ccTffv3E0fBrpCSpVc48dM5e5iTpRPrfWxAjrud9jSrqVBXsw3pqUvhuVmBpmwoKAfQGxHrauna3f48AFefGDozxXXjpdM9ZDWHsRUBTFNzDs8tUATtegSzZfNJCS9k0p5q2cueyU1mtwMJIdf0FrsVGiAyX7PFkWvLHi29fpprZQd0gbMMw2Bt10ZbZCsjPX261cXmVa6ZPnkVQm2w1ory3uWejuq20oQCyXTYyv1Ki4tbdPxoNn04Je7uS3QHDCsUl4i9zKNhBJ3g55bhIZWfwmLi3S7oY16gImdC6vvjsMKkCPzXv4pPaVhHH7o4f0mWEz30k4o7GQNOUy8LPM3NmlZF7QaIBdRfozG86jwQkC3jTNR357pdPjOqMERtIS4WEJBgbaeUCu5MOhsNdaD91iCeghIpOECFyTdEkUCGPPCIAtuAOKBdhPu40UxHx30dELMTK3azHOuOnLTsdiM4KJ9yF4Ab2eiz5j2T95sDx3aiEJDVDPCa55hO0XTBM9OSNtdzjdTdZT19XrwD0wPWZcBhfJ66X1uNM2eud1btzglqZP52qqYU7BK2M3BBZKKjy7P6YzmgaPHWnFGHZdwdz3Yq6e3N76Cjkfl8Sy0mkwd6pt0geDM1jNNZrcT8dUfLLaiUqcZm1KRVdpZaBrboDSuCxfWYlxqgsldwlGL4C06ceFUDXX8PzxzWEgOd8OU4F22pcNJOnwJGo6rYA3tvhAuq2WKVg6tgFCb1p7dzF4Ke3J0dv3IneMSNnHG4hkvxW6VzIykDUtYEjMQO35tdnEA0vMVLXIahpJpz4HGs5wwRgoZx1e1zD1pXi7KmEVTlfattgcGFlKjZJ60fEdloZEmiXodxT63CzuJHnjHDOL8qcMzTxHb8OCainga4w1fk4uILLAWqmTFpDcFGSF5lbOFUwhvtMK6knIWZ8ZApZvTGBt1qv3xKUJqPcWiweI4kk57zgyTPZku2mg4fJWDKSfiRSi7LvtpKkdqjein9lP7LMv5lKutprVzjmvHBPjunXGqakWx39xYH8RD6qF3Fw2BnIIesiicZsDv69Ggbu9Y334UeFPNIJ3LGp2I8xcUxlP5dJAh4V05p1HvIZ5Fhk0oCWlvNXdLqzbVsbfW9jWyQTaZXzw7WT3rqFQc7wvw4ayp5eKmUclqB1yOvrI14XGhmH7QMaAYNTIE2RHjYXVgvbmFRi0oB1v4nDEeSTn3KHBRQD8TilCagKg0XYPj2eAgWs12ZRYzlGyCvYZ1pol5wAwc9AFFGwsTJ9UYkbxlZv7wKDx7nFzlUSMC1kMvS2ECwvHzSycqHPRwCGipvG6kWz0mGvASXeKjm47iMROoY0MRK0uvgNdTTOTdxkMgOuCDIlxfit5QKjyzaVAg2kDwENfSd6XPMgSprTSLuNDXdg5NHCwUvDbEHVxpMgOItZymPZtPweOrnPdlEB4UwLZ8jqtShi5oDYvhkh85FwwT25OHFvDUWTTCV5n73pQ8kLo8zsB3mbWfGwg62guj3C50Dh42fAZEPBRSHDRTg3r0z39Vyj490lk2UpZeNyylwuEKmuIqEkbE3BRT2YEjTM8a2PU5grCuzculibcoRUpb1sIQiMRTf4wrtT1CnKcoUJ1T28DC04dTJVRcm3w3WzNLdrnovkX6NahblTzDvq5eXkoEaZv6HClmGuho4FH6s6i0OdmmW8qkNOnk7BhexiyAd3UYERlFwvZ6LP55tFOc3vnlhyylx1rTTgu1NFljRNs7rGiT7SnGFaFK7GITEZFEYI7DmOEUZXxDSHjYuOVN0YAJP2cZFgagyMwGJdrpH8S7cewYPMKz2Go2GBKl1OA6pJ8T91tUdEcGVg9JCMQUA4sBtlIuRTVV3cduIhsLCTi2ewItkh9MRP1kevVa9WcXejQQKreZmq5EZtzThW71r7E2tcvwFeqiwv3JZnV16bZ7NwZT6uvSrOnIFUyMsxhh8xCkVY82VLTAZhPXB8t6CbyjZ5stos6WmNZgoEsD8GU8pmzSTubAqQXkTbiODF2pePe6S9uQ9HngGGBnOjY4QUcAcScDsfflyXVqyxgTelGD4vXoba6qRWCqc9LKpyk4jCKYvLX9tzXusO7bhT2KRvF4MObDqdE4KnCCIF3zeVD0vImR20MmRTBHRCNm3s6GfyeTYEAlW3L2igZJ7Myj5zGLccMt2EohGc38HfWZ4mlvXRLHKB233PyKALYifqlAxTXaWUk13o6nACQDvN7DxSCA0daJeuznK1Dr52bC4IXCTahK1An6LkQMfsXb7Qus6ey241Vb4wTgFHqsdCx7qPxeAghmsTOHRVl")
    ],
    "body": ''
}

########NEW FILE########
__FILENAME__ = 025
req1 = {
    "method": "POST",
    "uri": uri("/chunked_cont_h_at_first"),
    "version": (1, 1),
    "headers": [
        ("CONTENT-LENGTH", "-1"),
        ("TRANSFER-ENCODING", "chunked")
    ],
    "body": b"hello world"
}

req2 = {
    "method": "PUT",
    "uri": uri("/chunked_cont_h_at_last"),
    "version": (1, 1),
    "headers": [
        ("TRANSFER-ENCODING", "chunked"),
        ("CONTENT-LENGTH", "-1"),
    ],
    "body": b"hello world"
}

request = [req1, req2]

########NEW FILE########
__FILENAME__ = 099
request = {
    "method": "POST",
    "uri": uri("/test-form"),
    "version": (1, 1),
    "headers": [
        ("HOST", "0.0.0.0:5000"),
        ("USER-AGENT", "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:25.0) Gecko/20100101 Firefox/25.0"),
        ("ACCEPT", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("ACCEPT-LANGUAGE", "en-us,en;q=0.7,el;q=0.3"),
        ("ACCEPT-ENCODING", "gzip, deflate"),
        ("COOKIE", "csrftoken=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX; sessionid=YYYYYYYYYYYYYYYYYYYYYYYYYYYY"),
        ("CONNECTION", "keep-alive"),
        ("CONTENT-TYPE", "multipart/form-data; boundary=---------------------------320761477111544"),
        ("CONTENT-LENGTH", "17914"),
    ],
    "body": b"""-----------------------------320761477111544
Content-Disposition: form-data; name="csrfmiddlewaretoken"

XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
-----------------------------320761477111544
Content-Disposition: form-data; name="_save"

Save
-----------------------------320761477111544
Content-Disposition: form-data; name="name"

test.example.org
-----------------------------320761477111544
Content-Disposition: form-data; name="type"

NATIVE
-----------------------------320761477111544
Content-Disposition: form-data; name="master"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_dynamiczone_domain-TOTAL_FORMS"

1
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_dynamiczone_domain-INITIAL_FORMS"

1
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_dynamiczone_domain-MAX_NUM_FORMS"

1
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_dynamiczone_domain-0-is_dynamic"

on
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_dynamiczone_domain-0-id"

1
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_dynamiczone_domain-0-domain"

2
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_dynamiczone_domain-__prefix__-id"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_dynamiczone_domain-__prefix__-domain"

2
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-TOTAL_FORMS"

1
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-INITIAL_FORMS"

1
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-MAX_NUM_FORMS"

1
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-0-ttl"

3600
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-0-primary"

ns.example.org
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-0-hostmaster"

hostmaster.test.example.org
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-0-serial"

2013121701
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-0-refresh"

10800
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-0-retry"

3600
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-0-expire"

604800
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-0-default_ttl"

3600
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-0-id"

16
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-0-domain"

2
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-__prefix__-ttl"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-__prefix__-primary"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-__prefix__-hostmaster"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-__prefix__-serial"

1
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-__prefix__-refresh"

10800
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-__prefix__-retry"

3600
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-__prefix__-expire"

604800
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-__prefix__-default_ttl"

3600
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-__prefix__-id"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-__prefix__-domain"

2
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-2-TOTAL_FORMS"

0
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-2-INITIAL_FORMS"

0
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-2-MAX_NUM_FORMS"

1000
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-2-__prefix__-id"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-2-__prefix__-domain"

2
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-2-__prefix__-name"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-2-__prefix__-ttl"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-2-__prefix__-content"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-3-TOTAL_FORMS"

0
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-3-INITIAL_FORMS"

0
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-3-MAX_NUM_FORMS"

1000
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-3-__prefix__-id"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-3-__prefix__-domain"

2
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-3-__prefix__-name"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-3-__prefix__-ttl"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-3-__prefix__-prio"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-3-__prefix__-content"


-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-4-TOTAL_FORMS"

0
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-4-INITIAL_FORMS"

0
---------------------
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-5-TOTAL_FORMS"

0
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-5-INITIAL_FORMS"

0
---------------------
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-6-TOTAL_FORMS"

0
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-6-INITIAL_FORMS"

0
---------------------
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-7-TOTAL_FORMS"

0
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-7-INITIAL_FORMS"

0
---------------------
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-8-TOTAL_FORMS"

0
-----------------------------320761477111544
Content-Disposition: form-data; name="foobar_manager_record_domain-8-INITIAL_FORMS"

0
---------------------
""".decode('utf-8').replace('\n', '\r\n').encode('utf-8'),
}

########NEW FILE########
__FILENAME__ = pp_01
from gunicorn.config import Config

cfg = Config()
cfg.set('proxy_protocol', True)

request = {
    "method": "GET",
    "uri": uri("/stuff/here?foo=bar"),
    "version": (1, 0),
    "headers": [
        ("SERVER", "http://127.0.0.1:5984"),
        ("CONTENT-TYPE", "application/json"),
        ("CONTENT-LENGTH", "14")
    ],
    "body": b'{"nom": "nom"}'
}

########NEW FILE########
__FILENAME__ = pp_02
from gunicorn.config import Config

cfg = Config()
cfg.set("proxy_protocol", True)

req1 = {
    "method": "GET",
    "uri": uri("/stuff/here?foo=bar"),
    "version": (1, 1),
    "headers": [
        ("SERVER", "http://127.0.0.1:5984"),
        ("CONTENT-TYPE", "application/json"),
        ("CONTENT-LENGTH", "14"),
        ("CONNECTION", "keep-alive")
    ],
    "body": b'{"nom": "nom"}'
}


req2 = {
    "method": "POST",
    "uri": uri("/post_chunked_all_your_base"),
    "version": (1, 1),
    "headers": [
        ("TRANSFER-ENCODING", "chunked"),
        ],
    "body": b"all your base are belong to us"
}

request = [req1, req2]

########NEW FILE########
__FILENAME__ = t
# -*- coding: utf-8 -
# Copyright 2009 Paul J. Davis <paul.joseph.davis@gmail.com>
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import array
import os
import tempfile

dirname = os.path.dirname(__file__)

from gunicorn.http.parser import RequestParser
from gunicorn.config import Config
from gunicorn.six import BytesIO

def data_source(fname):
    buf = BytesIO()
    with open(fname) as handle:
        for line in handle:
            line = line.rstrip("\n").replace("\\r\\n", "\r\n")
            buf.write(line.encode('latin1'))
        return buf

class request(object):
    def __init__(self, name):
        self.fname = os.path.join(dirname, "requests", name)

    def __call__(self, func):
        def run():
            src = data_source(self.fname)
            func(src, RequestParser(src))
        run.func_name = func.func_name
        return run


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


class http_request(object):
    def __init__(self, name):
        self.fname = os.path.join(dirname, "requests", name)

    def __call__(self, func):
        def run():
            fsock = FakeSocket(data_source(self.fname))
            req = Request(Config(), fsock, ('127.0.0.1', 6000), ('127.0.0.1', 8000))
            func(req)
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

def istype(a, b):
    assert isinstance(a, b), "%r is not an instance of %r" % (a, b)

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
__FILENAME__ = test_001-valid-requests
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import t
import treq

import glob
import os
dirname = os.path.dirname(__file__)

from py.test import skip
reqdir = os.path.join(dirname, "requests", "valid")

def a_case(fname):
    env = treq.load_py(os.path.splitext(fname)[0] + ".py")
    expect = env['request']
    cfg = env['cfg']
    req = treq.request(fname, expect)
    for case in req.gen_cases(cfg):
        case[0](*case[1:])

def test_http_parser():
    for fname in glob.glob(os.path.join(reqdir, "*.http")):
        if os.getenv("GUNS_BLAZING"):
            env = treq.load_py(os.path.splitext(fname)[0] + ".py")
            expect = env['request']
            cfg = env['cfg']
            req = treq.request(fname, expect)
            for case in req.gen_cases(cfg):
                yield case
        else:
            yield (a_case, fname)

########NEW FILE########
__FILENAME__ = test_002-invalid-requests
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import t
import treq

import glob
import os

import pytest

dirname = os.path.dirname(__file__)
reqdir = os.path.join(dirname, "requests", "invalid")


def test_http_parser():
    for fname in glob.glob(os.path.join(reqdir, "*.http")):
        env = treq.load_py(os.path.splitext(fname)[0] + ".py")

        expect = env['request']
        cfg = env['cfg']
        req = treq.badrequest(fname)

        with pytest.raises(expect):
            def f(fname):
                return req.check(cfg)
            f(fname)

########NEW FILE########
__FILENAME__ = test_003-config
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import t

import functools
import os
import sys

from gunicorn import config
from gunicorn.app.base import Application
from gunicorn.workers.sync import SyncWorker

dirname = os.path.dirname(__file__)
def cfg_file():
    return os.path.join(dirname, "config", "test_cfg.py")
def paster_ini():
    return os.path.join(dirname, "..", "examples", "frameworks", "pylonstest", "nose.ini")

class AltArgs(object):
    def __init__(self, args=None):
        self.args = args or []
        self.orig = sys.argv

    def __enter__(self):
        sys.argv = self.args

    def __exit__(self, exc_type, exc_inst, traceback):
        sys.argv = self.orig

class NoConfigApp(Application):
    def __init__(self):
        super(NoConfigApp, self).__init__("no_usage", prog="gunicorn_test")

    def init(self, parser, opts, args):
        pass

    def load(self):
        pass


def test_defaults():
    c = config.Config()
    for s in config.KNOWN_SETTINGS:
        t.eq(c.settings[s.name].validator(s.default),
             c.settings[s.name].get())

def test_property_access():
    c = config.Config()
    for s in config.KNOWN_SETTINGS:
        getattr(c, s.name)

    # Class was loaded
    t.eq(c.worker_class, SyncWorker)

    # Workers defaults to 1
    t.eq(c.workers, 1)
    c.set("workers", 3)
    t.eq(c.workers, 3)

    # Address is parsed
    t.eq(c.address, [("127.0.0.1", 8000)])

    # User and group defaults
    t.eq(os.geteuid(), c.uid)
    t.eq(os.getegid(), c.gid)

    # Proc name
    t.eq("gunicorn", c.proc_name)

    # Not a config property
    t.raises(AttributeError, getattr, c, "foo")
    # Force to be not an error
    class Baz(object):
        def get(self):
            return 3.14
    c.settings["foo"] = Baz()
    t.eq(c.foo, 3.14)

    # Attempt to set a cfg not via c.set
    t.raises(AttributeError, setattr, c, "proc_name", "baz")

    # No setting for name
    t.raises(AttributeError, c.set, "baz", "bar")

def test_bool_validation():
    c = config.Config()
    t.eq(c.preload_app, False)
    c.set("preload_app", True)
    t.eq(c.preload_app, True)
    c.set("preload_app", "true")
    t.eq(c.preload_app, True)
    c.set("preload_app", "false")
    t.eq(c.preload_app, False)
    t.raises(ValueError, c.set, "preload_app", "zilch")
    t.raises(TypeError, c.set, "preload_app", 4)

def test_pos_int_validation():
    c = config.Config()
    t.eq(c.workers, 1)
    c.set("workers", 4)
    t.eq(c.workers, 4)
    c.set("workers", "5")
    t.eq(c.workers, 5)
    c.set("workers", "0xFF")
    t.eq(c.workers, 255)
    c.set("workers", True)
    t.eq(c.workers, 1) # Yes. That's right...
    t.raises(ValueError, c.set, "workers", -21)
    t.raises(TypeError, c.set, "workers", c)

def test_str_validation():
    c = config.Config()
    t.eq(c.proc_name, "gunicorn")
    c.set("proc_name", " foo ")
    t.eq(c.proc_name, "foo")
    t.raises(TypeError, c.set, "proc_name", 2)

def test_str_to_list_validation():
    c = config.Config()
    t.eq(c.forwarded_allow_ips, ["127.0.0.1"])
    c.set("forwarded_allow_ips", "127.0.0.1,192.168.0.1")
    t.eq(c.forwarded_allow_ips, ["127.0.0.1", "192.168.0.1"])
    c.set("forwarded_allow_ips", "")
    t.eq(c.forwarded_allow_ips, [])
    c.set("forwarded_allow_ips", None)
    t.eq(c.forwarded_allow_ips, [])
    t.raises(TypeError, c.set, "forwarded_allow_ips", 1)

def test_callable_validation():
    c = config.Config()
    def func(a, b):
        pass
    c.set("pre_fork", func)
    t.eq(c.pre_fork, func)
    t.raises(TypeError, c.set, "pre_fork", 1)
    t.raises(TypeError, c.set, "pre_fork", lambda x: True)

def test_callable_validation_for_string():
    from os.path import isdir as testfunc
    t.eq(
        config.validate_callable(-1)("os.path.isdir"),
        testfunc
    )

    # invalid values tests
    t.raises(
        TypeError,
        config.validate_callable(-1), ""
    )
    t.raises(
        TypeError,
        config.validate_callable(-1), "os.path.not_found_func"
    )
    t.raises(
        TypeError,
        config.validate_callable(-1), "notfoundmodule.func"
    )


def test_cmd_line():
    with AltArgs(["prog_name", "-b", "blargh"]):
        app = NoConfigApp()
        t.eq(app.cfg.bind, ["blargh"])
    with AltArgs(["prog_name", "-w", "3"]):
        app = NoConfigApp()
        t.eq(app.cfg.workers, 3)
    with AltArgs(["prog_name", "--preload"]):
        app = NoConfigApp()
        t.eq(app.cfg.preload_app, True)

def test_app_config():
    with AltArgs():
        app = NoConfigApp()
    for s in config.KNOWN_SETTINGS:
        t.eq(app.cfg.settings[s.name].validator(s.default),
             app.cfg.settings[s.name].get())

def test_load_config():
    with AltArgs(["prog_name", "-c", cfg_file()]):
        app = NoConfigApp()
    t.eq(app.cfg.bind, ["unix:/tmp/bar/baz"])
    t.eq(app.cfg.workers, 3)
    t.eq(app.cfg.proc_name, "fooey")

def test_cli_overrides_config():
    with AltArgs(["prog_name", "-c", cfg_file(), "-b", "blarney"]):
        app = NoConfigApp()
        t.eq(app.cfg.bind, ["blarney"])
        t.eq(app.cfg.proc_name, "fooey")

def test_default_config_file():
    default_config = os.path.join(os.path.abspath(os.getcwd()), 
                                                  'gunicorn.conf.py')
    with open(default_config, 'w+') as default:
        default.write("bind='0.0.0.0:9090'")
    
    t.eq(config.get_default_config_file(), default_config)

    with AltArgs(["prog_name"]):
        app = NoConfigApp()
        t.eq(app.cfg.bind, ["0.0.0.0:9090"])

    os.unlink(default_config)

def test_post_request():
    c = config.Config()

    def post_request_4(worker, req, environ, resp):
        return 4

    def post_request_3(worker, req, environ):
        return 3

    def post_request_2(worker, req):
        return 2

    c.set("post_request", post_request_4)
    t.eq(4, c.post_request(1, 2, 3, 4))

    c.set("post_request", post_request_3)
    t.eq(3, c.post_request(1, 2, 3, 4))

    c.set("post_request", post_request_2)
    t.eq(2, c.post_request(1, 2, 3, 4))


def test_nworkers_changed():
    c = config.Config()
    def nworkers_changed_3(server, new_value, old_value):
        return 3

    c.set("nworkers_changed", nworkers_changed_3)
    t.eq(3, c.nworkers_changed(1, 2, 3))

########NEW FILE########
__FILENAME__ = test_004-http-body
import t
from gunicorn.http.body import Body
from gunicorn.six import BytesIO


def assert_readline(payload, size, expected):
    body = Body(BytesIO(payload))
    t.eq(body.readline(size), expected)


def test_readline_empty_body():
    assert_readline(b"", None, b"")
    assert_readline(b"", 1, b"")


def test_readline_zero_size():
    assert_readline(b"abc", 0, b"")
    assert_readline(b"\n", 0, b"")


def test_readline_new_line_before_size():
    body = Body(BytesIO(b"abc\ndef"))
    t.eq(body.readline(4), b"abc\n")
    t.eq(body.readline(), b"def")


def test_readline_new_line_after_size():
    body = Body(BytesIO(b"abc\ndef"))
    t.eq(body.readline(2), b"ab")
    t.eq(body.readline(), b"c\n")


def test_readline_no_new_line():
    body = Body(BytesIO(b"abcdef"))
    t.eq(body.readline(), b"abcdef")
    body = Body(BytesIO(b"abcdef"))
    t.eq(body.readline(2), b"ab")
    t.eq(body.readline(2), b"cd")
    t.eq(body.readline(2), b"ef")


def test_readline_buffer_loaded():
    reader = BytesIO(b"abc\ndef")
    body = Body(reader)
    body.read(1) # load internal buffer
    reader.write(b"g\nhi")
    reader.seek(7)
    print(reader.getvalue())
    t.eq(body.readline(), b"bc\n")
    t.eq(body.readline(), b"defg\n")
    t.eq(body.readline(), b"hi")


def test_readline_buffer_loaded_with_size():
    body = Body(BytesIO(b"abc\ndef"))
    body.read(1) # load internal buffer
    t.eq(body.readline(2), b"bc")
    t.eq(body.readline(2), b"\n")
    t.eq(body.readline(2), b"de")
    t.eq(body.readline(2), b"f")


########NEW FILE########
__FILENAME__ = test_006-logger
import datetime

import t

from gunicorn.config import Config
from gunicorn.glogging import Logger


class Mock():
    def __init__(self, **kwargs):
        for attr in kwargs:
            setattr(self, attr, kwargs[attr])


def test_atoms_defaults():
    response = Mock(status='200', response_length=1024,
        headers=(('Content-Type', 'application/json'), ))
    request = Mock(headers=(('Accept', 'application/json'), ))
    environ = {'REQUEST_METHOD': 'GET', 'RAW_URI': 'http://my.uri',
        'SERVER_PROTOCOL': 'HTTP/1.1'}
    logger = Logger(Config())
    atoms = logger.atoms(response, request, environ,
        datetime.timedelta(seconds=1))
    t.istype(atoms, dict)
    t.eq(atoms['r'], 'GET http://my.uri HTTP/1.1')
    t.eq(atoms['{accept}i'], 'application/json')
    t.eq(atoms['{content-type}o'], 'application/json')

########NEW FILE########
__FILENAME__ = test_007-ssl
# -*- coding: utf-8 -

# Copyright 2013 Dariusz Suchojad <dsuch at zato.io>
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

# stdlib
import inspect
import ssl
import sys
from unittest import TestCase

# gunicorn
from gunicorn.config import KeyFile, CertFile, SSLVersion, CACerts, \
     SuppressRaggedEOFs, DoHandshakeOnConnect, Setting, validate_bool, validate_string, \
     validate_pos_int

if sys.version_info >= (2, 7):
    from gunicorn.config import Ciphers

class SSLTestCase(TestCase):
    def test_settings_classes(self):
        """ Tests all settings options and their defaults.
        """
        self.assertTrue(issubclass(KeyFile, Setting))
        self.assertEquals(KeyFile.name, 'keyfile')
        self.assertEquals(KeyFile.section, 'Ssl')
        self.assertEquals(KeyFile.cli, ['--keyfile'])
        self.assertEquals(KeyFile.meta, 'FILE')
        self.assertEquals(KeyFile.default, None)

        self.assertTrue(issubclass(CertFile, Setting))
        self.assertEquals(CertFile.name, 'certfile')
        self.assertEquals(CertFile.section, 'Ssl')
        self.assertEquals(CertFile.cli, ['--certfile'])
        self.assertEquals(CertFile.default, None)
        
        self.assertTrue(issubclass(SSLVersion, Setting))
        self.assertEquals(SSLVersion.name, 'ssl_version')
        self.assertEquals(SSLVersion.section, 'Ssl')
        self.assertEquals(SSLVersion.cli, ['--ssl-version'])
        self.assertEquals(SSLVersion.default, ssl.PROTOCOL_TLSv1)
        
        self.assertTrue(issubclass(CACerts, Setting))
        self.assertEquals(CACerts.name, 'ca_certs')
        self.assertEquals(CACerts.section, 'Ssl')
        self.assertEquals(CACerts.cli, ['--ca-certs'])
        self.assertEquals(CACerts.meta, 'FILE')
        self.assertEquals(CACerts.default, None)

        self.assertTrue(issubclass(SuppressRaggedEOFs, Setting))
        self.assertEquals(SuppressRaggedEOFs.name, 'suppress_ragged_eofs')
        self.assertEquals(SuppressRaggedEOFs.section, 'Ssl')
        self.assertEquals(SuppressRaggedEOFs.cli, ['--suppress-ragged-eofs'])
        self.assertEquals(SuppressRaggedEOFs.action, 'store_true')
        self.assertEquals(SuppressRaggedEOFs.default, True)
        
        self.assertTrue(issubclass(DoHandshakeOnConnect, Setting))
        self.assertEquals(DoHandshakeOnConnect.name, 'do_handshake_on_connect')
        self.assertEquals(DoHandshakeOnConnect.section, 'Ssl')
        self.assertEquals(DoHandshakeOnConnect.cli, ['--do-handshake-on-connect'])
        self.assertEquals(DoHandshakeOnConnect.action, 'store_true')
        self.assertEquals(DoHandshakeOnConnect.default, False)


        if sys.version_info >= (2, 7):
            self.assertTrue(issubclass(Ciphers, Setting))        
            self.assertEquals(Ciphers.name, 'ciphers')
            self.assertEquals(Ciphers.section, 'Ssl')
            self.assertEquals(Ciphers.cli, ['--ciphers'])
            self.assertEquals(Ciphers.default, 'TLSv1')

########NEW FILE########
__FILENAME__ = test_008-arbiter-env
# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import t
import os
from gunicorn.app.base import BaseApplication
import gunicorn.arbiter


class PreloadedAppWithEnvSettings(BaseApplication):
    """
    Simple application that makes use of the 'preload' feature to
    start the application before spawning worker processes and sets
    environmental variable configuration settings.
    """

    def init(self, parser, opts, args):
        """No-op"""
        pass

    def load(self):
        """No-op"""
        pass

    def load_config(self):
        """Set the 'preload_app' and 'raw_env' settings in order to verify their
        interaction below.
        """
        self.cfg.set('raw_env', [
            'SOME_PATH=/tmp/something', 'OTHER_PATH=/tmp/something/else'])
        self.cfg.set('preload_app', True)

    def wsgi(self):
        """Assert that the expected environmental variables are set when
        the main entry point of this application is called as part of a
        'preloaded' application.
        """
        verify_env_vars()
        return super(PreloadedAppWithEnvSettings, self).wsgi()


def verify_env_vars():
    t.eq(os.getenv('SOME_PATH'), '/tmp/something')
    t.eq(os.getenv('OTHER_PATH'), '/tmp/something/else')


def test_env_vars_available_during_preload():
    """Ensure that configured environmental variables are set during the
    initial set up of the application (called from the .setup() method of
    the Arbiter) such that they are available during the initial loading
    of the WSGI application.
    """
    # Note that we aren't making any assertions here, they are made in the
    # dummy application object being loaded here instead.
    gunicorn.arbiter.Arbiter(PreloadedAppWithEnvSettings())

########NEW FILE########
__FILENAME__ = treq
# Copyright 2009 Paul J. Davis <paul.joseph.davis@gmail.com>
#
# This file is part of the pywebmachine package released
# under the MIT license.

import t

import inspect
import os
import random

from gunicorn.config import Config
from gunicorn.http.errors import ParseException
from gunicorn.http.parser import RequestParser
from gunicorn.six import urlparse, execfile_
from gunicorn import six

dirname = os.path.dirname(__file__)
random.seed()

def uri(data):
    ret = {"raw": data}
    parts = urlparse(data)
    ret["scheme"] = parts.scheme or ''
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
        ret["path"] = ''
    ret["query"] = parts.query or ''
    ret["fragment"] = parts.fragment or ''
    return ret

def load_py(fname):
    config = globals().copy()
    config["uri"] = uri
    config["cfg"] = Config()
    execfile_(fname, config)
    return config

class request(object):
    def __init__(self, fname, expect):
        self.fname = fname
        self.name = os.path.basename(fname)

        self.expect = expect
        if not isinstance(self.expect, list):
            self.expect = [self.expect]

        with open(self.fname, 'rb') as handle:
            self.data = handle.read()
        self.data = self.data.replace(b"\n", b"").replace(b"\\r\\n", b"\r\n")
        self.data = self.data.replace(b"\\0", b"\000")

    # Functions for sending data to the parser.
    # These functions mock out reading from a
    # socket or other data source that might
    # be used in real life.

    def send_all(self):
        yield self.data

    def send_lines(self):
        lines = self.data
        pos = lines.find(b"\r\n")
        while pos > 0:
            yield lines[:pos+2]
            lines = lines[pos+2:]
            pos = lines.find(b"\r\n")
        if len(lines):
            yield lines

    def send_bytes(self):
        for d in str(self.data.decode("latin1")):
            yield bytes(d.encode("latin1"))

    def send_random(self):
        maxs = round(len(self.data) / 10)
        read = 0
        while read < len(self.data):
            chunk = random.randint(1, maxs)
            yield self.data[read:read+chunk]
            read += chunk

    def send_special_chunks(self):
        """Meant to test the request line length check.

        Sends the request data in two chunks, one having a
        length of 1 byte, which ensures that no CRLF is included,
        and a second chunk containing the rest of the request data.

        If the request line length check is not done properly,
        testing the ``tests/requests/valid/099.http`` request
        fails with a ``LimitRequestLine`` exception.

        """
        chunk = self.data[:1]
        read = 0
        while read < len(self.data):
            yield self.data[read:read+len(chunk)]
            read += len(chunk)
            chunk = self.data[read:]

    # These functions define the sizes that the
    # read functions will read with.

    def size_all(self):
        return -1

    def size_bytes(self):
        return 1

    def size_small_random(self):
        return random.randint(1, 4)

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
            if b'\n' in data[:-1]:
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
            if b'\n' in line[:-1]:
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
            if b'\n' in line[:-1]:
                raise AssertionError("Embedded new line: %r" % line)
            if line != body[:len(line)]:
                raise AssertionError("Invalid body data read: %r != %r" % (
                                                    line, body[:len(line)]))
            body = body[len(line):]
        if len(body):
            raise AssertionError("Failed to read entire body: %r" % body)
        try:
            data = six.next(iter(req.body))
            raise AssertionError("Read data after body finished: %r" % data)
        except StopIteration:
            pass

    # Construct a series of test cases from the permutations of
    # send, size, and match functions.

    def gen_cases(self, cfg):
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
            if hasattr(mt, 'funcname'):
                mtn = mt.func_name[6:]
                szn = sz.func_name[5:]
                snn = sn.func_name[5:]
            else:
                mtn = mt.__name__[6:]
                szn = sz.__name__[5:]
                snn = sn.__name__[5:]

            def test_req(sn, sz, mt):
                self.check(cfg, sn, sz, mt)
            desc = "%s: MT: %s SZ: %s SN: %s" % (self.name, mtn, szn, snn)
            test_req.description = desc
            ret.append((test_req, sn, sz, mt))
        return ret

    def check(self, cfg, sender, sizer, matcher):
        cases = self.expect[:]
        p = RequestParser(cfg, sender())
        for req in p:
            self.same(req, sizer, matcher, cases.pop(0))
        t.eq(len(cases), 0)

    def same(self, req, sizer, matcher, exp):
        t.eq(req.method, exp["method"])
        t.eq(req.uri, exp["uri"]["raw"])
        t.eq(req.path, exp["uri"]["path"])
        t.eq(req.query, exp["uri"]["query"])
        t.eq(req.fragment, exp["uri"]["fragment"])
        t.eq(req.version, exp["version"])
        t.eq(req.headers, exp["headers"])
        matcher(req, exp["body"], sizer)
        t.eq(req.trailers, exp.get("trailers", []))

class badrequest(object):
    def __init__(self, fname):
        self.fname = fname
        self.name = os.path.basename(fname)

        with open(self.fname) as handle:
            self.data = handle.read()
        self.data = self.data.replace("\n", "").replace("\\r\\n", "\r\n")
        self.data = self.data.replace("\\0", "\000")
        self.data = self.data.encode('latin1')

    def send(self):
        maxs = round(len(self.data) / 10)
        read = 0
        while read < len(self.data):
            chunk = random.randint(1, maxs)
            yield self.data[read:read+chunk]
            read += chunk

    def check(self, cfg):
        p = RequestParser(cfg, self.send())
        six.next(p)

########NEW FILE########
