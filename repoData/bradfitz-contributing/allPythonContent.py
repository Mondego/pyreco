__FILENAME__ = consumer
#!/usr/bin/python
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A sample OpenID consumer app for Google App Engine. Allows users to log into
other OpenID providers, then displays their OpenID login. Also stores and
displays the most recent logins.

Part of http://code.google.com/p/google-app-engine-samples/.

For more about OpenID, see:
  http://openid.net/
  http://openid.net/about.bml

Uses JanRain's Python OpenID library, version 2.1.1, licensed under the
Apache Software License 2.0:
  http://openidenabled.com/python-openid/

The JanRain library includes a reference OpenID provider that can be used to
test this consumer. After starting the dev_appserver with this app, unpack the
JanRain library and run these commands from its root directory:

  setenv PYTHONPATH .
  python ./examples/server.py -s localhost

Then go to http://localhost:8080/ in your browser, type in
http://localhost:8000/test as your OpenID identifier, and click Verify.
"""

import datetime
import logging
import os
import re
import sys
import urlparse
import wsgiref.handlers

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from openid import fetchers
from openid.consumer.consumer import Consumer
from openid.consumer import discover
from openid.extensions import pape, sreg
import fetcher
import store
import string
import random

import models

# Set to True if stack traces should be shown in the browser, etc.
_DEBUG = False


def GenKeyName(length=8, chars=string.letters + string.digits):
  return ''.join([random.choice(chars) for i in xrange(length)])


class Session(db.Expando):
  """An in-progress OpenID login."""
  claimed_id = db.StringProperty()
  server_url = db.LinkProperty()


class Login(db.Model):
  """A completed OpenID login."""
  status = db.StringProperty(choices=('success', 'cancel', 'failure'))
  claimed_id = db.LinkProperty()
  server_url = db.LinkProperty()
  timestamp = db.DateTimeProperty(auto_now_add=True)
  session = db.ReferenceProperty(Session)


class Handler(webapp.RequestHandler):
  """A base handler class with a couple OpenID-specific utilities."""
  consumer = None
  session = None
  session_args = None

  def __init__(self):
    self.session_args = {}

  def get_consumer(self):
    """Returns a Consumer instance.
    """
    if not self.consumer:
      fetchers.setDefaultFetcher(fetcher.UrlfetchFetcher())
      if not self.load_session():
        return
      self.consumer = Consumer(self.session_args, store.DatastoreStore())

    return self.consumer

  def args_to_dict(self):
    """Converts the URL and POST parameters to a singly-valued dictionary.

    Returns:
      dict with the URL and POST body parameters
    """
    req = self.request
    return dict([(arg, req.get(arg)) for arg in req.arguments()])

  def load_session(self):
    """Loads the current session.
    """
    if not self.session:
      id = self.request.get('session_id')
      if id:
        try:
          self.session = db.get(db.Key.from_path('Session', int(id)))
          assert self.session
        except (AssertionError, db.Error), e:
          self.report_error('Invalid session id: %d' % id)
          return None

        fields = self.session.dynamic_properties()
        self.session_args = dict((f, getattr(self.session, f)) for f in fields)

      else:
        self.session_args = {}
        self.session = Session()
        self.session.claimed_id = self.request.get('openid')

      return self.session

  def store_session(self):
    """Stores the current session.
    """
    assert self.session
    for field, value in self.session_args.items():
      setattr(self.session, field, value)
    self.session.put()

  def render(self, extra_values={}):
    """Renders the page, including the extra (optional) values.

    Args:
      template_name: string
      The template to render.

      extra_values: dict
      Template values to provide to the template.
    """
    logins = Login.gql('ORDER BY timestamp DESC').fetch(20)
    for login in logins:
      login.display_name = self.display_name(login.claimed_id)
      login.friendly_time = self.relative_time(login.timestamp)

    values = {
      'response': {},
      'openid': '',
      'logins': logins,
    }
    values.update(extra_values)
    cwd = os.path.dirname(__file__)
    path = os.path.join(cwd, 'templates', 'base.html')
    self.response.out.write(template.render(path, values, debug=_DEBUG))

  def report_error(self, message, exception=None):
    """Shows an error HTML page.

    Args:
      message: string
      A detailed error message.
    """
    if exception:
      logging.exception('Error: %s' % message)
    self.render({'error': message})

  def show_front_page(self):
    """Do an internal (non-302) redirect to the front page.

    Preserves the user agent's requested URL.
    """
    front_page = FrontPage()
    front_page.request = self.request
    front_page.response = self.response
    front_page.get()

  def relative_time(self, timestamp):
    """Returns a friendly string describing how long ago the timestamp was.

    Args:
      timestamp: a datetime

    Returns:
      string
    """
    def format_number(num):
      if num <= 9:
        return {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
                6: 'six', 7: 'seven', 8: 'eight', 9: 'nine'}[num]
      else:
        return str(num)

    delta = datetime.datetime.now() - timestamp
    minutes = delta.seconds / 60
    hours = minutes / 60

    if delta.days > 1:
      return '%s days ago' % format_number(delta.days)
    elif delta.days == 1:
      return 'yesterday'
    elif hours > 1:
      return '%s hours ago' % format_number(hours)
    elif hours == 1:
      return 'an hour ago'
    elif minutes > 25:
      return 'half an hour ago'
    elif minutes > 5:
      return '%s minutes ago' % format_number(minutes)
    else:
      return 'moments ago'

  def display_name(self, openid_url):
    """Extracts a short, representative part of an OpenID URL for display.

    For example, it returns "ryan" for:
      ryan.com
      www.ryan.com
      ryan.provider.com
      provider.com/ryan
      provider.com/id/path/ryan

    Adapted from Net::OpenID::Consumer, by Brad Fitzpatrick. See:

    http://code.sixapart.com/svn/openid/trunk/perl/Net-OpenID-Consumer/lib/Net/OpenID/VerifiedIdentity.pm

    Args:
      openid_url: string

    Returns:
      string
    """
    if not openid_url:
      return 'None'

    username_re = '[\w.+-]+'

    scheme, host, path, params, query, frag = urlparse.urlparse(openid_url)

    def sanitize(display_name):
      if '@' in display_name:
        # don't display full email addresses; use just the user name part
        display_name = display_name[:display_name.index('@')]
      return display_name

    # is the username in the params?
    match = re.search('(u|id|user|userid|user_id|profile)=(%s)' % username_re,
                      path)
    if match:
      return sanitize(match.group(2))

    # is the username in the path?
    path = path.split('/')
    if re.match(username_re, path[-1]):
      return sanitize(path[-1])

    # use the hostname
    host = host.split('.')
    if len(host) == 1:
      return host[0]

    # strip common tlds and country code tlds
    common_tlds = ('com', 'org', 'net', 'edu', 'info', 'biz', 'gov', 'mil')
    if host[-1] in common_tlds or len(host[-1]) == 2:
      host = host[:-1]
    if host[-1] == 'co':
      host = host[:-1]

    # strip www prefix
    if host[0] == 'www':
      host = host[1:]

    return sanitize('.'.join(host))


class FrontPage(Handler):
  """Show the default front page."""
  def get(self):
    self.render()


class StartHandler(Handler):
  """Handles a POST response to the OpenID login form."""

  def post(self):
    """Handles login requests."""
    logging.info(self.args_to_dict())
    openid_url = self.request.get('openid_url')
    if not openid_url:
      self.report_error('Please enter an OpenID URL.')
      return

    logging.debug('Beginning discovery for OpenID %s' % openid_url)
    try:
      consumer = self.get_consumer()
      if not consumer:
        return
      auth_request = consumer.begin(openid_url)
    except discover.DiscoveryFailure, e:
      self.report_error('Error during OpenID provider discovery.', e)
      return
    except discover.XRDSError, e:
      self.report_error('Error parsing XRDS from provider.', e)
      return

    self.session.claimed_id = auth_request.endpoint.claimed_id
    self.session.server_url = auth_request.endpoint.server_url
    self.store_session()

    sreg_request = sreg.SRegRequest(optional=['nickname', 'fullname', 'email'])
    auth_request.addExtension(sreg_request)

    pape_request = pape.Request([pape.AUTH_MULTI_FACTOR,
                                 pape.AUTH_MULTI_FACTOR_PHYSICAL,
                                 pape.AUTH_PHISHING_RESISTANT,
                                 ])
    auth_request.addExtension(pape_request)

    parts = list(urlparse.urlparse(self.request.uri))
    parts[2] = 's/finish'
    parts[4] = 'session_id=%d' % self.session.key().id()
    parts[5] = ''
    return_to = urlparse.urlunparse(parts)
    realm = urlparse.urlunparse(parts[0:2] + [''] * 4)

    redirect_url = auth_request.redirectURL(realm, return_to)
    logging.debug('Redirecting to %s' % redirect_url)
    self.response.set_status(302)
    self.response.headers['Location'] = redirect_url


class FinishHandler(Handler):
  """Handle a redirect from the provider."""
  def get(self):
    args = self.args_to_dict()
    consumer = self.get_consumer()
    if not consumer:
      return

    if self.session.login_set.get():
      self.render()
      return

    response = consumer.complete(args, self.request.uri)
    assert response.status in Login.status.choices

    if response.status == 'success':
      sreg_data = sreg.SRegResponse.fromSuccessResponse(response).items()
      pape_data = pape.Response.fromSuccessResponse(response)
      self.session.claimed_id = response.endpoint.claimed_id
      self.session.server_url = response.endpoint.server_url
    elif response.status == 'failure':
      logging.error(str(response))

    logging.debug('Login status %s for claimed_id %s' %
                  (response.status, self.session.claimed_id))

    if response.status != 'success':
      self.render(locals())
      return

    session_id = GenKeyName(length=16)

    login = Login(key_name=session_id,
                  status=response.status,
                  claimed_id=self.session.claimed_id,
                  server_url=self.session.server_url,
                  session=self.session.key())
    login.put()

    # update the login time
    user = models.User(openid_user=login.claimed_id).GetOrCreateFromDatastore()
    user.put()

    self.response.headers.add_header('Set-Cookie',
                                     'session=%s; path=/' % session_id)

    # TODO(bradfitz: redirect to proper 'next' URL
    self.redirect('/')


# Map URLs to our RequestHandler subclasses above
_URLS = [
  ('/s/openid', FrontPage),
  ('/s/startopenid', StartHandler),
  ('/s/finish', FinishHandler),
]

def main(argv):
  application = webapp.WSGIApplication(_URLS, debug=_DEBUG)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main(sys.argv)

########NEW FILE########
__FILENAME__ = ElementInclude
#
# ElementTree
# $Id: ElementInclude.py 1862 2004-06-18 07:31:02Z Fredrik $
#
# limited xinclude support for element trees
#
# history:
# 2003-08-15 fl   created
# 2003-11-14 fl   fixed default loader
#
# Copyright (c) 2003-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Limited XInclude support for the ElementTree package.
##

import copy
import ElementTree

XINCLUDE = "{http://www.w3.org/2001/XInclude}"

XINCLUDE_INCLUDE = XINCLUDE + "include"
XINCLUDE_FALLBACK = XINCLUDE + "fallback"

##
# Fatal include error.

class FatalIncludeError(SyntaxError):
    pass

##
# Default loader.  This loader reads an included resource from disk.
#
# @param href Resource reference.
# @param parse Parse mode.  Either "xml" or "text".
# @param encoding Optional text encoding.
# @return The expanded resource.  If the parse mode is "xml", this
#    is an ElementTree instance.  If the parse mode is "text", this
#    is a Unicode string.  If the loader fails, it can return None
#    or raise an IOError exception.
# @throws IOError If the loader fails to load the resource.

def default_loader(href, parse, encoding=None):
    file = open(href)
    if parse == "xml":
        data = ElementTree.parse(file).getroot()
    else:
        data = file.read()
        if encoding:
            data = data.decode(encoding)
    file.close()
    return data

##
# Expand XInclude directives.
#
# @param elem Root element.
# @param loader Optional resource loader.  If omitted, it defaults
#     to {@link default_loader}.  If given, it should be a callable
#     that implements the same interface as <b>default_loader</b>.
# @throws FatalIncludeError If the function fails to include a given
#     resource, or if the tree contains malformed XInclude elements.
# @throws IOError If the function fails to load a given resource.

def include(elem, loader=None):
    if loader is None:
        loader = default_loader
    # look for xinclude elements
    i = 0
    while i < len(elem):
        e = elem[i]
        if e.tag == XINCLUDE_INCLUDE:
            # process xinclude directive
            href = e.get("href")
            parse = e.get("parse", "xml")
            if parse == "xml":
                node = loader(href, parse)
                if node is None:
                    raise FatalIncludeError(
                        "cannot load %r as %r" % (href, parse)
                        )
                node = copy.copy(node)
                if e.tail:
                    node.tail = (node.tail or "") + e.tail
                elem[i] = node
            elif parse == "text":
                text = loader(href, parse, e.get("encoding"))
                if text is None:
                    raise FatalIncludeError(
                        "cannot load %r as %r" % (href, parse)
                        )
                if i:
                    node = elem[i-1]
                    node.tail = (node.tail or "") + text
                else:
                    elem.text = (elem.text or "") + text + (e.tail or "")
                del elem[i]
                continue
            else:
                raise FatalIncludeError(
                    "unknown parse type in xi:include tag (%r)" % parse
                )
        elif e.tag == XINCLUDE_FALLBACK:
            raise FatalIncludeError(
                "xi:fallback tag must be child of xi:include (%r)" % e.tag
                )
        else:
            include(e, loader)
        i = i + 1


########NEW FILE########
__FILENAME__ = ElementPath
#
# ElementTree
# $Id: ElementPath.py 1858 2004-06-17 21:31:41Z Fredrik $
#
# limited xpath support for element trees
#
# history:
# 2003-05-23 fl   created
# 2003-05-28 fl   added support for // etc
# 2003-08-27 fl   fixed parsing of periods in element names
#
# Copyright (c) 2003-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Implementation module for XPath support.  There's usually no reason
# to import this module directly; the <b>ElementTree</b> does this for
# you, if needed.
##

import re

xpath_tokenizer = re.compile(
    "(::|\.\.|\(\)|[/.*:\[\]\(\)@=])|((?:\{[^}]+\})?[^/:\[\]\(\)@=\s]+)|\s+"
    ).findall

class xpath_descendant_or_self:
    pass

##
# Wrapper for a compiled XPath.

class Path:

    ##
    # Create an Path instance from an XPath expression.

    def __init__(self, path):
        tokens = xpath_tokenizer(path)
        # the current version supports 'path/path'-style expressions only
        self.path = []
        self.tag = None
        if tokens and tokens[0][0] == "/":
            raise SyntaxError("cannot use absolute path on element")
        while tokens:
            op, tag = tokens.pop(0)
            if tag or op == "*":
                self.path.append(tag or op)
            elif op == ".":
                pass
            elif op == "/":
                self.path.append(xpath_descendant_or_self())
                continue
            else:
                raise SyntaxError("unsupported path syntax (%s)" % op)
            if tokens:
                op, tag = tokens.pop(0)
                if op != "/":
                    raise SyntaxError(
                        "expected path separator (%s)" % (op or tag)
                        )
        if self.path and isinstance(self.path[-1], xpath_descendant_or_self):
            raise SyntaxError("path cannot end with //")
        if len(self.path) == 1 and isinstance(self.path[0], type("")):
            self.tag = self.path[0]

    ##
    # Find first matching object.

    def find(self, element):
        tag = self.tag
        if tag is None:
            nodeset = self.findall(element)
            if not nodeset:
                return None
            return nodeset[0]
        for elem in element:
            if elem.tag == tag:
                return elem
        return None

    ##
    # Find text for first matching object.

    def findtext(self, element, default=None):
        tag = self.tag
        if tag is None:
            nodeset = self.findall(element)
            if not nodeset:
                return default
            return nodeset[0].text or ""
        for elem in element:
            if elem.tag == tag:
                return elem.text or ""
        return default

    ##
    # Find all matching objects.

    def findall(self, element):
        nodeset = [element]
        index = 0
        while 1:
            try:
                path = self.path[index]
                index = index + 1
            except IndexError:
                return nodeset
            set = []
            if isinstance(path, xpath_descendant_or_self):
                try:
                    tag = self.path[index]
                    if not isinstance(tag, type("")):
                        tag = None
                    else:
                        index = index + 1
                except IndexError:
                    tag = None # invalid path
                for node in nodeset:
                    new = list(node.getiterator(tag))
                    if new and new[0] is node:
                        set.extend(new[1:])
                    else:
                        set.extend(new)
            else:
                for node in nodeset:
                    for node in node:
                        if path == "*" or node.tag == path:
                            set.append(node)
            if not set:
                return []
            nodeset = set

_cache = {}

##
# (Internal) Compile path.

def _compile(path):
    p = _cache.get(path)
    if p is not None:
        return p
    p = Path(path)
    if len(_cache) >= 100:
        _cache.clear()
    _cache[path] = p
    return p

##
# Find first matching object.

def find(element, path):
    return _compile(path).find(element)

##
# Find text for first matching object.

def findtext(element, path, default=None):
    return _compile(path).findtext(element, default)

##
# Find all matching objects.

def findall(element, path):
    return _compile(path).findall(element)


########NEW FILE########
__FILENAME__ = ElementTree
#
# ElementTree
# $Id: ElementTree.py 2326 2005-03-17 07:45:21Z fredrik $
#
# light-weight XML support for Python 1.5.2 and later.
#
# history:
# 2001-10-20 fl   created (from various sources)
# 2001-11-01 fl   return root from parse method
# 2002-02-16 fl   sort attributes in lexical order
# 2002-04-06 fl   TreeBuilder refactoring, added PythonDoc markup
# 2002-05-01 fl   finished TreeBuilder refactoring
# 2002-07-14 fl   added basic namespace support to ElementTree.write
# 2002-07-25 fl   added QName attribute support
# 2002-10-20 fl   fixed encoding in write
# 2002-11-24 fl   changed default encoding to ascii; fixed attribute encoding
# 2002-11-27 fl   accept file objects or file names for parse/write
# 2002-12-04 fl   moved XMLTreeBuilder back to this module
# 2003-01-11 fl   fixed entity encoding glitch for us-ascii
# 2003-02-13 fl   added XML literal factory
# 2003-02-21 fl   added ProcessingInstruction/PI factory
# 2003-05-11 fl   added tostring/fromstring helpers
# 2003-05-26 fl   added ElementPath support
# 2003-07-05 fl   added makeelement factory method
# 2003-07-28 fl   added more well-known namespace prefixes
# 2003-08-15 fl   fixed typo in ElementTree.findtext (Thomas Dartsch)
# 2003-09-04 fl   fall back on emulator if ElementPath is not installed
# 2003-10-31 fl   markup updates
# 2003-11-15 fl   fixed nested namespace bug
# 2004-03-28 fl   added XMLID helper
# 2004-06-02 fl   added default support to findtext
# 2004-06-08 fl   fixed encoding of non-ascii element/attribute names
# 2004-08-23 fl   take advantage of post-2.1 expat features
# 2005-02-01 fl   added iterparse implementation
# 2005-03-02 fl   fixed iterparse support for pre-2.2 versions
#
# Copyright (c) 1999-2005 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2005 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

__all__ = [
    # public symbols
    "Comment",
    "dump",
    "Element", "ElementTree",
    "fromstring",
    "iselement", "iterparse",
    "parse",
    "PI", "ProcessingInstruction",
    "QName",
    "SubElement",
    "tostring",
    "TreeBuilder",
    "VERSION", "XML",
    "XMLTreeBuilder",
    ]

##
# The <b>Element</b> type is a flexible container object, designed to
# store hierarchical data structures in memory. The type can be
# described as a cross between a list and a dictionary.
# <p>
# Each element has a number of properties associated with it:
# <ul>
# <li>a <i>tag</i>. This is a string identifying what kind of data
# this element represents (the element type, in other words).</li>
# <li>a number of <i>attributes</i>, stored in a Python dictionary.</li>
# <li>a <i>text</i> string.</li>
# <li>an optional <i>tail</i> string.</li>
# <li>a number of <i>child elements</i>, stored in a Python sequence</li>
# </ul>
#
# To create an element instance, use the {@link #Element} or {@link
# #SubElement} factory functions.
# <p>
# The {@link #ElementTree} class can be used to wrap an element
# structure, and convert it from and to XML.
##

import string, sys, re

class _SimpleElementPath:
    # emulate pre-1.2 find/findtext/findall behaviour
    def find(self, element, tag):
        for elem in element:
            if elem.tag == tag:
                return elem
        return None
    def findtext(self, element, tag, default=None):
        for elem in element:
            if elem.tag == tag:
                return elem.text or ""
        return default
    def findall(self, element, tag):
        if tag[:3] == ".//":
            return element.getiterator(tag[3:])
        result = []
        for elem in element:
            if elem.tag == tag:
                result.append(elem)
        return result

try:
    import ElementPath
except ImportError:
    # FIXME: issue warning in this case?
    ElementPath = _SimpleElementPath()

# TODO: add support for custom namespace resolvers/default namespaces
# TODO: add improved support for incremental parsing

VERSION = "1.2.6"

##
# Internal element class.  This class defines the Element interface,
# and provides a reference implementation of this interface.
# <p>
# You should not create instances of this class directly.  Use the
# appropriate factory functions instead, such as {@link #Element}
# and {@link #SubElement}.
#
# @see Element
# @see SubElement
# @see Comment
# @see ProcessingInstruction

class _ElementInterface:
    # <tag attrib>text<child/>...</tag>tail

    ##
    # (Attribute) Element tag.

    tag = None

    ##
    # (Attribute) Element attribute dictionary.  Where possible, use
    # {@link #_ElementInterface.get},
    # {@link #_ElementInterface.set},
    # {@link #_ElementInterface.keys}, and
    # {@link #_ElementInterface.items} to access
    # element attributes.

    attrib = None

    ##
    # (Attribute) Text before first subelement.  This is either a
    # string or the value None, if there was no text.

    text = None

    ##
    # (Attribute) Text after this element's end tag, but before the
    # next sibling element's start tag.  This is either a string or
    # the value None, if there was no text.

    tail = None # text after end tag, if any

    def __init__(self, tag, attrib):
        self.tag = tag
        self.attrib = attrib
        self._children = []

    def __repr__(self):
        return "<Element %s at %x>" % (self.tag, id(self))

    ##
    # Creates a new element object of the same type as this element.
    #
    # @param tag Element tag.
    # @param attrib Element attributes, given as a dictionary.
    # @return A new element instance.

    def makeelement(self, tag, attrib):
        return Element(tag, attrib)

    ##
    # Returns the number of subelements.
    #
    # @return The number of subelements.

    def __len__(self):
        return len(self._children)

    ##
    # Returns the given subelement.
    #
    # @param index What subelement to return.
    # @return The given subelement.
    # @exception IndexError If the given element does not exist.

    def __getitem__(self, index):
        return self._children[index]

    ##
    # Replaces the given subelement.
    #
    # @param index What subelement to replace.
    # @param element The new element value.
    # @exception IndexError If the given element does not exist.
    # @exception AssertionError If element is not a valid object.

    def __setitem__(self, index, element):
        assert iselement(element)
        self._children[index] = element

    ##
    # Deletes the given subelement.
    #
    # @param index What subelement to delete.
    # @exception IndexError If the given element does not exist.

    def __delitem__(self, index):
        del self._children[index]

    ##
    # Returns a list containing subelements in the given range.
    #
    # @param start The first subelement to return.
    # @param stop The first subelement that shouldn't be returned.
    # @return A sequence object containing subelements.

    def __getslice__(self, start, stop):
        return self._children[start:stop]

    ##
    # Replaces a number of subelements with elements from a sequence.
    #
    # @param start The first subelement to replace.
    # @param stop The first subelement that shouldn't be replaced.
    # @param elements A sequence object with zero or more elements.
    # @exception AssertionError If a sequence member is not a valid object.

    def __setslice__(self, start, stop, elements):
        for element in elements:
            assert iselement(element)
        self._children[start:stop] = list(elements)

    ##
    # Deletes a number of subelements.
    #
    # @param start The first subelement to delete.
    # @param stop The first subelement to leave in there.

    def __delslice__(self, start, stop):
        del self._children[start:stop]

    ##
    # Adds a subelement to the end of this element.
    #
    # @param element The element to add.
    # @exception AssertionError If a sequence member is not a valid object.

    def append(self, element):
        assert iselement(element)
        self._children.append(element)

    ##
    # Inserts a subelement at the given position in this element.
    #
    # @param index Where to insert the new subelement.
    # @exception AssertionError If the element is not a valid object.

    def insert(self, index, element):
        assert iselement(element)
        self._children.insert(index, element)

    ##
    # Removes a matching subelement.  Unlike the <b>find</b> methods,
    # this method compares elements based on identity, not on tag
    # value or contents.
    #
    # @param element What element to remove.
    # @exception ValueError If a matching element could not be found.
    # @exception AssertionError If the element is not a valid object.

    def remove(self, element):
        assert iselement(element)
        self._children.remove(element)

    ##
    # Returns all subelements.  The elements are returned in document
    # order.
    #
    # @return A list of subelements.
    # @defreturn list of Element instances

    def getchildren(self):
        return self._children

    ##
    # Finds the first matching subelement, by tag name or path.
    #
    # @param path What element to look for.
    # @return The first matching element, or None if no element was found.
    # @defreturn Element or None

    def find(self, path):
        return ElementPath.find(self, path)

    ##
    # Finds text for the first matching subelement, by tag name or path.
    #
    # @param path What element to look for.
    # @param default What to return if the element was not found.
    # @return The text content of the first matching element, or the
    #     default value no element was found.  Note that if the element
    #     has is found, but has no text content, this method returns an
    #     empty string.
    # @defreturn string

    def findtext(self, path, default=None):
        return ElementPath.findtext(self, path, default)

    ##
    # Finds all matching subelements, by tag name or path.
    #
    # @param path What element to look for.
    # @return A list or iterator containing all matching elements,
    #    in document order.
    # @defreturn list of Element instances

    def findall(self, path):
        return ElementPath.findall(self, path)

    ##
    # Resets an element.  This function removes all subelements, clears
    # all attributes, and sets the text and tail attributes to None.

    def clear(self):
        self.attrib.clear()
        self._children = []
        self.text = self.tail = None

    ##
    # Gets an element attribute.
    #
    # @param key What attribute to look for.
    # @param default What to return if the attribute was not found.
    # @return The attribute value, or the default value, if the
    #     attribute was not found.
    # @defreturn string or None

    def get(self, key, default=None):
        return self.attrib.get(key, default)

    ##
    # Sets an element attribute.
    #
    # @param key What attribute to set.
    # @param value The attribute value.

    def set(self, key, value):
        self.attrib[key] = value

    ##
    # Gets a list of attribute names.  The names are returned in an
    # arbitrary order (just like for an ordinary Python dictionary).
    #
    # @return A list of element attribute names.
    # @defreturn list of strings

    def keys(self):
        return self.attrib.keys()

    ##
    # Gets element attributes, as a sequence.  The attributes are
    # returned in an arbitrary order.
    #
    # @return A list of (name, value) tuples for all attributes.
    # @defreturn list of (string, string) tuples

    def items(self):
        return self.attrib.items()

    ##
    # Creates a tree iterator.  The iterator loops over this element
    # and all subelements, in document order, and returns all elements
    # with a matching tag.
    # <p>
    # If the tree structure is modified during iteration, the result
    # is undefined.
    #
    # @param tag What tags to look for (default is to return all elements).
    # @return A list or iterator containing all the matching elements.
    # @defreturn list or iterator

    def getiterator(self, tag=None):
        nodes = []
        if tag == "*":
            tag = None
        if tag is None or self.tag == tag:
            nodes.append(self)
        for node in self._children:
            nodes.extend(node.getiterator(tag))
        return nodes

# compatibility
_Element = _ElementInterface

##
# Element factory.  This function returns an object implementing the
# standard Element interface.  The exact class or type of that object
# is implementation dependent, but it will always be compatible with
# the {@link #_ElementInterface} class in this module.
# <p>
# The element name, attribute names, and attribute values can be
# either 8-bit ASCII strings or Unicode strings.
#
# @param tag The element name.
# @param attrib An optional dictionary, containing element attributes.
# @param **extra Additional attributes, given as keyword arguments.
# @return An element instance.
# @defreturn Element

def Element(tag, attrib={}, **extra):
    attrib = attrib.copy()
    attrib.update(extra)
    return _ElementInterface(tag, attrib)

##
# Subelement factory.  This function creates an element instance, and
# appends it to an existing element.
# <p>
# The element name, attribute names, and attribute values can be
# either 8-bit ASCII strings or Unicode strings.
#
# @param parent The parent element.
# @param tag The subelement name.
# @param attrib An optional dictionary, containing element attributes.
# @param **extra Additional attributes, given as keyword arguments.
# @return An element instance.
# @defreturn Element

def SubElement(parent, tag, attrib={}, **extra):
    attrib = attrib.copy()
    attrib.update(extra)
    element = parent.makeelement(tag, attrib)
    parent.append(element)
    return element

##
# Comment element factory.  This factory function creates a special
# element that will be serialized as an XML comment.
# <p>
# The comment string can be either an 8-bit ASCII string or a Unicode
# string.
#
# @param text A string containing the comment string.
# @return An element instance, representing a comment.
# @defreturn Element

def Comment(text=None):
    element = Element(Comment)
    element.text = text
    return element

##
# PI element factory.  This factory function creates a special element
# that will be serialized as an XML processing instruction.
#
# @param target A string containing the PI target.
# @param text A string containing the PI contents, if any.
# @return An element instance, representing a PI.
# @defreturn Element

def ProcessingInstruction(target, text=None):
    element = Element(ProcessingInstruction)
    element.text = target
    if text:
        element.text = element.text + " " + text
    return element

PI = ProcessingInstruction

##
# QName wrapper.  This can be used to wrap a QName attribute value, in
# order to get proper namespace handling on output.
#
# @param text A string containing the QName value, in the form {uri}local,
#     or, if the tag argument is given, the URI part of a QName.
# @param tag Optional tag.  If given, the first argument is interpreted as
#     an URI, and this argument is interpreted as a local name.
# @return An opaque object, representing the QName.

class QName:
    def __init__(self, text_or_uri, tag=None):
        if tag:
            text_or_uri = "{%s}%s" % (text_or_uri, tag)
        self.text = text_or_uri
    def __str__(self):
        return self.text
    def __hash__(self):
        return hash(self.text)
    def __cmp__(self, other):
        if isinstance(other, QName):
            return cmp(self.text, other.text)
        return cmp(self.text, other)

##
# ElementTree wrapper class.  This class represents an entire element
# hierarchy, and adds some extra support for serialization to and from
# standard XML.
#
# @param element Optional root element.
# @keyparam file Optional file handle or name.  If given, the
#     tree is initialized with the contents of this XML file.

class ElementTree:

    def __init__(self, element=None, file=None):
        assert element is None or iselement(element)
        self._root = element # first node
        if file:
            self.parse(file)

    ##
    # Gets the root element for this tree.
    #
    # @return An element instance.
    # @defreturn Element

    def getroot(self):
        return self._root

    ##
    # Replaces the root element for this tree.  This discards the
    # current contents of the tree, and replaces it with the given
    # element.  Use with care.
    #
    # @param element An element instance.

    def _setroot(self, element):
        assert iselement(element)
        self._root = element

    ##
    # Loads an external XML document into this element tree.
    #
    # @param source A file name or file object.
    # @param parser An optional parser instance.  If not given, the
    #     standard {@link XMLTreeBuilder} parser is used.
    # @return The document root element.
    # @defreturn Element

    def parse(self, source, parser=None):
        if not hasattr(source, "read"):
            source = open(source, "rb")
        if not parser:
            parser = XMLTreeBuilder()
        while 1:
            data = source.read(32768)
            if not data:
                break
            parser.feed(data)
        self._root = parser.close()
        return self._root

    ##
    # Creates a tree iterator for the root element.  The iterator loops
    # over all elements in this tree, in document order.
    #
    # @param tag What tags to look for (default is to return all elements)
    # @return An iterator.
    # @defreturn iterator

    def getiterator(self, tag=None):
        assert self._root is not None
        return self._root.getiterator(tag)

    ##
    # Finds the first toplevel element with given tag.
    # Same as getroot().find(path).
    #
    # @param path What element to look for.
    # @return The first matching element, or None if no element was found.
    # @defreturn Element or None

    def find(self, path):
        assert self._root is not None
        if path[:1] == "/":
            path = "." + path
        return self._root.find(path)

    ##
    # Finds the element text for the first toplevel element with given
    # tag.  Same as getroot().findtext(path).
    #
    # @param path What toplevel element to look for.
    # @param default What to return if the element was not found.
    # @return The text content of the first matching element, or the
    #     default value no element was found.  Note that if the element
    #     has is found, but has no text content, this method returns an
    #     empty string.
    # @defreturn string

    def findtext(self, path, default=None):
        assert self._root is not None
        if path[:1] == "/":
            path = "." + path
        return self._root.findtext(path, default)

    ##
    # Finds all toplevel elements with the given tag.
    # Same as getroot().findall(path).
    #
    # @param path What element to look for.
    # @return A list or iterator containing all matching elements,
    #    in document order.
    # @defreturn list of Element instances

    def findall(self, path):
        assert self._root is not None
        if path[:1] == "/":
            path = "." + path
        return self._root.findall(path)

    ##
    # Writes the element tree to a file, as XML.
    #
    # @param file A file name, or a file object opened for writing.
    # @param encoding Optional output encoding (default is US-ASCII).

    def write(self, file, encoding="us-ascii"):
        assert self._root is not None
        if not hasattr(file, "write"):
            file = open(file, "wb")
        if not encoding:
            encoding = "us-ascii"
        elif encoding != "utf-8" and encoding != "us-ascii":
            file.write("<?xml version='1.0' encoding='%s'?>\n" % encoding)
        self._write(file, self._root, encoding, {})

    def _write(self, file, node, encoding, namespaces):
        # write XML to file
        tag = node.tag
        if tag is Comment:
            file.write("<!-- %s -->" % _escape_cdata(node.text, encoding))
        elif tag is ProcessingInstruction:
            file.write("<?%s?>" % _escape_cdata(node.text, encoding))
        else:
            items = node.items()
            xmlns_items = [] # new namespaces in this scope
            try:
                if isinstance(tag, QName) or tag[:1] == "{":
                    tag, xmlns = fixtag(tag, namespaces)
                    if xmlns: xmlns_items.append(xmlns)
            except TypeError:
                _raise_serialization_error(tag)
            file.write("<" + _encode(tag, encoding))
            if items or xmlns_items:
                items.sort() # lexical order
                for k, v in items:
                    try:
                        if isinstance(k, QName) or k[:1] == "{":
                            k, xmlns = fixtag(k, namespaces)
                            if xmlns: xmlns_items.append(xmlns)
                    except TypeError:
                        _raise_serialization_error(k)
                    try:
                        if isinstance(v, QName):
                            v, xmlns = fixtag(v, namespaces)
                            if xmlns: xmlns_items.append(xmlns)
                    except TypeError:
                        _raise_serialization_error(v)
                    file.write(" %s=\"%s\"" % (_encode(k, encoding),
                                               _escape_attrib(v, encoding)))
                for k, v in xmlns_items:
                    file.write(" %s=\"%s\"" % (_encode(k, encoding),
                                               _escape_attrib(v, encoding)))
            if node.text or len(node):
                file.write(">")
                if node.text:
                    file.write(_escape_cdata(node.text, encoding))
                for n in node:
                    self._write(file, n, encoding, namespaces)
                file.write("</" + _encode(tag, encoding) + ">")
            else:
                file.write(" />")
            for k, v in xmlns_items:
                del namespaces[v]
        if node.tail:
            file.write(_escape_cdata(node.tail, encoding))

# --------------------------------------------------------------------
# helpers

##
# Checks if an object appears to be a valid element object.
#
# @param An element instance.
# @return A true value if this is an element object.
# @defreturn flag

def iselement(element):
    # FIXME: not sure about this; might be a better idea to look
    # for tag/attrib/text attributes
    return isinstance(element, _ElementInterface) or hasattr(element, "tag")

##
# Writes an element tree or element structure to sys.stdout.  This
# function should be used for debugging only.
# <p>
# The exact output format is implementation dependent.  In this
# version, it's written as an ordinary XML file.
#
# @param elem An element tree or an individual element.

def dump(elem):
    # debugging
    if not isinstance(elem, ElementTree):
        elem = ElementTree(elem)
    elem.write(sys.stdout)
    tail = elem.getroot().tail
    if not tail or tail[-1] != "\n":
        sys.stdout.write("\n")

def _encode(s, encoding):
    try:
        return s.encode(encoding)
    except AttributeError:
        return s # 1.5.2: assume the string uses the right encoding

if sys.version[:3] == "1.5":
    _escape = re.compile(r"[&<>\"\x80-\xff]+") # 1.5.2
else:
    _escape = re.compile(eval(r'u"[&<>\"\u0080-\uffff]+"'))

_escape_map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
}

_namespace_map = {
    # "well-known" namespace prefixes
    "http://www.w3.org/XML/1998/namespace": "xml",
    "http://www.w3.org/1999/xhtml": "html",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://schemas.xmlsoap.org/wsdl/": "wsdl",
}

def _raise_serialization_error(text):
    raise TypeError(
        "cannot serialize %r (type %s)" % (text, type(text).__name__)
        )

def _encode_entity(text, pattern=_escape):
    # map reserved and non-ascii characters to numerical entities
    def escape_entities(m, map=_escape_map):
        out = []
        append = out.append
        for char in m.group():
            text = map.get(char)
            if text is None:
                text = "&#%d;" % ord(char)
            append(text)
        return string.join(out, "")
    try:
        return _encode(pattern.sub(escape_entities, text), "ascii")
    except TypeError:
        _raise_serialization_error(text)

#
# the following functions assume an ascii-compatible encoding
# (or "utf-16")

def _escape_cdata(text, encoding=None, replace=string.replace):
    # escape character data
    try:
        if encoding:
            try:
                text = _encode(text, encoding)
            except UnicodeError:
                return _encode_entity(text)
        text = replace(text, "&", "&amp;")
        text = replace(text, "<", "&lt;")
        text = replace(text, ">", "&gt;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_attrib(text, encoding=None, replace=string.replace):
    # escape attribute value
    try:
        if encoding:
            try:
                text = _encode(text, encoding)
            except UnicodeError:
                return _encode_entity(text)
        text = replace(text, "&", "&amp;")
        text = replace(text, "'", "&apos;") # FIXME: overkill
        text = replace(text, "\"", "&quot;")
        text = replace(text, "<", "&lt;")
        text = replace(text, ">", "&gt;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def fixtag(tag, namespaces):
    # given a decorated tag (of the form {uri}tag), return prefixed
    # tag and namespace declaration, if any
    if isinstance(tag, QName):
        tag = tag.text
    namespace_uri, tag = string.split(tag[1:], "}", 1)
    prefix = namespaces.get(namespace_uri)
    if prefix is None:
        prefix = _namespace_map.get(namespace_uri)
        if prefix is None:
            prefix = "ns%d" % len(namespaces)
        namespaces[namespace_uri] = prefix
        if prefix == "xml":
            xmlns = None
        else:
            xmlns = ("xmlns:%s" % prefix, namespace_uri)
    else:
        xmlns = None
    return "%s:%s" % (prefix, tag), xmlns

##
# Parses an XML document into an element tree.
#
# @param source A filename or file object containing XML data.
# @param parser An optional parser instance.  If not given, the
#     standard {@link XMLTreeBuilder} parser is used.
# @return An ElementTree instance

def parse(source, parser=None):
    tree = ElementTree()
    tree.parse(source, parser)
    return tree

##
# Parses an XML document into an element tree incrementally, and reports
# what's going on to the user.
#
# @param source A filename or file object containing XML data.
# @param events A list of events to report back.  If omitted, only "end"
#     events are reported.
# @return A (event, elem) iterator.

class iterparse:

    def __init__(self, source, events=None):
        if not hasattr(source, "read"):
            source = open(source, "rb")
        self._file = source
        self._events = []
        self._index = 0
        self.root = self._root = None
        self._parser = XMLTreeBuilder()
        # wire up the parser for event reporting
        parser = self._parser._parser
        append = self._events.append
        if events is None:
            events = ["end"]
        for event in events:
            if event == "start":
                try:
                    parser.ordered_attributes = 1
                    parser.specified_attributes = 1
                    def handler(tag, attrib_in, event=event, append=append,
                                start=self._parser._start_list):
                        append((event, start(tag, attrib_in)))
                    parser.StartElementHandler = handler
                except AttributeError:
                    def handler(tag, attrib_in, event=event, append=append,
                                start=self._parser._start):
                        append((event, start(tag, attrib_in)))
                    parser.StartElementHandler = handler
            elif event == "end":
                def handler(tag, event=event, append=append,
                            end=self._parser._end):
                    append((event, end(tag)))
                parser.EndElementHandler = handler
            elif event == "start-ns":
                def handler(prefix, uri, event=event, append=append):
                    try:
                        uri = _encode(uri, "ascii")
                    except UnicodeError:
                        pass
                    append((event, (prefix or "", uri)))
                parser.StartNamespaceDeclHandler = handler
            elif event == "end-ns":
                def handler(prefix, event=event, append=append):
                    append((event, None))
                parser.EndNamespaceDeclHandler = handler

    def next(self):
        while 1:
            try:
                item = self._events[self._index]
            except IndexError:
                if self._parser is None:
                    self.root = self._root
                    try:
                        raise StopIteration
                    except NameError:
                        raise IndexError
                # load event buffer
                del self._events[:]
                self._index = 0
                data = self._file.read(16384)
                if data:
                    self._parser.feed(data)
                else:
                    self._root = self._parser.close()
                    self._parser = None
            else:
                self._index = self._index + 1
                return item

    try:
        iter
        def __iter__(self):
            return self
    except NameError:
        def __getitem__(self, index):
            return self.next()

##
# Parses an XML document from a string constant.  This function can
# be used to embed "XML literals" in Python code.
#
# @param source A string containing XML data.
# @return An Element instance.
# @defreturn Element

def XML(text):
    parser = XMLTreeBuilder()
    parser.feed(text)
    return parser.close()

##
# Parses an XML document from a string constant, and also returns
# a dictionary which maps from element id:s to elements.
#
# @param source A string containing XML data.
# @return A tuple containing an Element instance and a dictionary.
# @defreturn (Element, dictionary)

def XMLID(text):
    parser = XMLTreeBuilder()
    parser.feed(text)
    tree = parser.close()
    ids = {}
    for elem in tree.getiterator():
        id = elem.get("id")
        if id:
            ids[id] = elem
    return tree, ids

##
# Parses an XML document from a string constant.  Same as {@link #XML}.
#
# @def fromstring(text)
# @param source A string containing XML data.
# @return An Element instance.
# @defreturn Element

fromstring = XML

##
# Generates a string representation of an XML element, including all
# subelements.
#
# @param element An Element instance.
# @return An encoded string containing the XML data.
# @defreturn string

def tostring(element, encoding=None):
    class dummy:
        pass
    data = []
    file = dummy()
    file.write = data.append
    ElementTree(element).write(file, encoding)
    return string.join(data, "")

##
# Generic element structure builder.  This builder converts a sequence
# of {@link #TreeBuilder.start}, {@link #TreeBuilder.data}, and {@link
# #TreeBuilder.end} method calls to a well-formed element structure.
# <p>
# You can use this class to build an element structure using a custom XML
# parser, or a parser for some other XML-like format.
#
# @param element_factory Optional element factory.  This factory
#    is called to create new Element instances, as necessary.

class TreeBuilder:

    def __init__(self, element_factory=None):
        self._data = [] # data collector
        self._elem = [] # element stack
        self._last = None # last element
        self._tail = None # true if we're after an end tag
        if element_factory is None:
            element_factory = _ElementInterface
        self._factory = element_factory

    ##
    # Flushes the parser buffers, and returns the toplevel documen
    # element.
    #
    # @return An Element instance.
    # @defreturn Element

    def close(self):
        assert len(self._elem) == 0, "missing end tags"
        assert self._last != None, "missing toplevel element"
        return self._last

    def _flush(self):
        if self._data:
            if self._last is not None:
                text = string.join(self._data, "")
                if self._tail:
                    assert self._last.tail is None, "internal error (tail)"
                    self._last.tail = text
                else:
                    assert self._last.text is None, "internal error (text)"
                    self._last.text = text
            self._data = []

    ##
    # Adds text to the current element.
    #
    # @param data A string.  This should be either an 8-bit string
    #    containing ASCII text, or a Unicode string.

    def data(self, data):
        self._data.append(data)

    ##
    # Opens a new element.
    #
    # @param tag The element name.
    # @param attrib A dictionary containing element attributes.
    # @return The opened element.
    # @defreturn Element

    def start(self, tag, attrs):
        self._flush()
        self._last = elem = self._factory(tag, attrs)
        if self._elem:
            self._elem[-1].append(elem)
        self._elem.append(elem)
        self._tail = 0
        return elem

    ##
    # Closes the current element.
    #
    # @param tag The element name.
    # @return The closed element.
    # @defreturn Element

    def end(self, tag):
        self._flush()
        self._last = self._elem.pop()
        assert self._last.tag == tag,\
               "end tag mismatch (expected %s, got %s)" % (
                   self._last.tag, tag)
        self._tail = 1
        return self._last

##
# Element structure builder for XML source data, based on the
# <b>expat</b> parser.
#
# @keyparam target Target object.  If omitted, the builder uses an
#     instance of the standard {@link #TreeBuilder} class.
# @keyparam html Predefine HTML entities.  This flag is not supported
#     by the current implementation.
# @see #ElementTree
# @see #TreeBuilder

class XMLTreeBuilder:

    def __init__(self, html=0, target=None):
        try:
            from xml.parsers import expat
        except ImportError:
            raise ImportError(
                "No module named expat; use SimpleXMLTreeBuilder instead"
                )
        self._parser = parser = expat.ParserCreate(None, "}")
        if target is None:
            target = TreeBuilder()
        self._target = target
        self._names = {} # name memo cache
        # callbacks
        parser.DefaultHandlerExpand = self._default
        parser.StartElementHandler = self._start
        parser.EndElementHandler = self._end
        parser.CharacterDataHandler = self._data
        # let expat do the buffering, if supported
        try:
            self._parser.buffer_text = 1
        except AttributeError:
            pass
        # use new-style attribute handling, if supported
        try:
            self._parser.ordered_attributes = 1
            self._parser.specified_attributes = 1
            parser.StartElementHandler = self._start_list
        except AttributeError:
            pass
        encoding = None
        if not parser.returns_unicode:
            encoding = "utf-8"
        # target.xml(encoding, None)
        self._doctype = None
        self.entity = {}

    def _fixtext(self, text):
        # convert text string to ascii, if possible
        try:
            return _encode(text, "ascii")
        except UnicodeError:
            return text

    def _fixname(self, key):
        # expand qname, and convert name string to ascii, if possible
        try:
            name = self._names[key]
        except KeyError:
            name = key
            if "}" in name:
                name = "{" + name
            self._names[key] = name = self._fixtext(name)
        return name

    def _start(self, tag, attrib_in):
        fixname = self._fixname
        tag = fixname(tag)
        attrib = {}
        for key, value in attrib_in.items():
            attrib[fixname(key)] = self._fixtext(value)
        return self._target.start(tag, attrib)

    def _start_list(self, tag, attrib_in):
        fixname = self._fixname
        tag = fixname(tag)
        attrib = {}
        if attrib_in:
            for i in range(0, len(attrib_in), 2):
                attrib[fixname(attrib_in[i])] = self._fixtext(attrib_in[i+1])
        return self._target.start(tag, attrib)

    def _data(self, text):
        return self._target.data(self._fixtext(text))

    def _end(self, tag):
        return self._target.end(self._fixname(tag))

    def _default(self, text):
        prefix = text[:1]
        if prefix == "&":
            # deal with undefined entities
            try:
                self._target.data(self.entity[text[1:-1]])
            except KeyError:
                from xml.parsers import expat
                raise expat.error(
                    "undefined entity %s: line %d, column %d" %
                    (text, self._parser.ErrorLineNumber,
                    self._parser.ErrorColumnNumber)
                    )
        elif prefix == "<" and text[:9] == "<!DOCTYPE":
            self._doctype = [] # inside a doctype declaration
        elif self._doctype is not None:
            # parse doctype contents
            if prefix == ">":
                self._doctype = None
                return
            text = string.strip(text)
            if not text:
                return
            self._doctype.append(text)
            n = len(self._doctype)
            if n > 2:
                type = self._doctype[1]
                if type == "PUBLIC" and n == 4:
                    name, type, pubid, system = self._doctype
                elif type == "SYSTEM" and n == 3:
                    name, type, system = self._doctype
                    pubid = None
                else:
                    return
                if pubid:
                    pubid = pubid[1:-1]
                self.doctype(name, pubid, system[1:-1])
                self._doctype = None

    ##
    # Handles a doctype declaration.
    #
    # @param name Doctype name.
    # @param pubid Public identifier.
    # @param system System identifier.

    def doctype(self, name, pubid, system):
        pass

    ##
    # Feeds data to the parser.
    #
    # @param data Encoded data.

    def feed(self, data):
        self._parser.Parse(data, 0)

    ##
    # Finishes feeding data to the parser.
    #
    # @return An element structure.
    # @defreturn Element

    def close(self):
        self._parser.Parse("", 1) # end of data
        tree = self._target.close()
        del self._target, self._parser # get rid of circular references
        return tree

########NEW FILE########
__FILENAME__ = HTMLTreeBuilder
#
# ElementTree
# $Id: HTMLTreeBuilder.py 2325 2005-03-16 15:50:43Z fredrik $
#
# a simple tree builder, for HTML input
#
# history:
# 2002-04-06 fl   created
# 2002-04-07 fl   ignore IMG and HR end tags
# 2002-04-07 fl   added support for 1.5.2 and later
# 2003-04-13 fl   added HTMLTreeBuilder alias
# 2004-12-02 fl   don't feed non-ASCII charrefs/entities as 8-bit strings
# 2004-12-05 fl   don't feed non-ASCII CDATA as 8-bit strings
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Tools to build element trees from HTML files.
##

import htmlentitydefs
import re, string, sys
import mimetools, StringIO

import ElementTree

AUTOCLOSE = "p", "li", "tr", "th", "td", "head", "body"
IGNOREEND = "img", "hr", "meta", "link", "br"

if sys.version[:3] == "1.5":
    is_not_ascii = re.compile(r"[\x80-\xff]").search # 1.5.2
else:
    is_not_ascii = re.compile(eval(r'u"[\u0080-\uffff]"')).search

try:
    from HTMLParser import HTMLParser
except ImportError:
    from sgmllib import SGMLParser
    # hack to use sgmllib's SGMLParser to emulate 2.2's HTMLParser
    class HTMLParser(SGMLParser):
        # the following only works as long as this class doesn't
        # provide any do, start, or end handlers
        def unknown_starttag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
        def unknown_endtag(self, tag):
            self.handle_endtag(tag)

##
# ElementTree builder for HTML source code.  This builder converts an
# HTML document or fragment to an ElementTree.
# <p>
# The parser is relatively picky, and requires balanced tags for most
# elements.  However, elements belonging to the following group are
# automatically closed: P, LI, TR, TH, and TD.  In addition, the
# parser automatically inserts end tags immediately after the start
# tag, and ignores any end tags for the following group: IMG, HR,
# META, and LINK.
#
# @keyparam builder Optional builder object.  If omitted, the parser
#     uses the standard <b>elementtree</b> builder.
# @keyparam encoding Optional character encoding, if known.  If omitted,
#     the parser looks for META tags inside the document.  If no tags
#     are found, the parser defaults to ISO-8859-1.  Note that if your
#     document uses a non-ASCII compatible encoding, you must decode
#     the document before parsing.
#
# @see elementtree.ElementTree

class HTMLTreeBuilder(HTMLParser):

    # FIXME: shouldn't this class be named Parser, not Builder?

    def __init__(self, builder=None, encoding=None):
        self.__stack = []
        if builder is None:
            builder = ElementTree.TreeBuilder()
        self.__builder = builder
        self.encoding = encoding or "iso-8859-1"
        HTMLParser.__init__(self)

    ##
    # Flushes parser buffers, and return the root element.
    #
    # @return An Element instance.

    def close(self):
        HTMLParser.close(self)
        return self.__builder.close()

    ##
    # (Internal) Handles start tags.

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            # look for encoding directives
            http_equiv = content = None
            for k, v in attrs:
                if k == "http-equiv":
                    http_equiv = string.lower(v)
                elif k == "content":
                    content = v
            if http_equiv == "content-type" and content:
                # use mimetools to parse the http header
                header = mimetools.Message(
                    StringIO.StringIO("%s: %s\n\n" % (http_equiv, content))
                    )
                encoding = header.getparam("charset")
                if encoding:
                    self.encoding = encoding
        if tag in AUTOCLOSE:
            if self.__stack and self.__stack[-1] == tag:
                self.handle_endtag(tag)
        self.__stack.append(tag)
        attrib = {}
        if attrs:
            for k, v in attrs:
                attrib[string.lower(k)] = v
        self.__builder.start(tag, attrib)
        if tag in IGNOREEND:
            self.__stack.pop()
            self.__builder.end(tag)

    ##
    # (Internal) Handles end tags.

    def handle_endtag(self, tag):
        if tag in IGNOREEND:
            return
        lasttag = self.__stack.pop()
        if tag != lasttag and lasttag in AUTOCLOSE:
            self.handle_endtag(lasttag)
        self.__builder.end(tag)

    ##
    # (Internal) Handles character references.

    def handle_charref(self, char):
        if char[:1] == "x":
            char = int(char[1:], 16)
        else:
            char = int(char)
        if 0 <= char < 128:
            self.__builder.data(chr(char))
        else:
            self.__builder.data(unichr(char))

    ##
    # (Internal) Handles entity references.

    def handle_entityref(self, name):
        entity = htmlentitydefs.entitydefs.get(name)
        if entity:
            if len(entity) == 1:
                entity = ord(entity)
            else:
                entity = int(entity[2:-1])
            if 0 <= entity < 128:
                self.__builder.data(chr(entity))
            else:
                self.__builder.data(unichr(entity))
        else:
            self.unknown_entityref(name)

    ##
    # (Internal) Handles character data.

    def handle_data(self, data):
        if isinstance(data, type('')) and is_not_ascii(data):
            # convert to unicode, but only if necessary
            data = unicode(data, self.encoding, "ignore")
        self.__builder.data(data)

    ##
    # (Hook) Handles unknown entity references.  The default action
    # is to ignore unknown entities.

    def unknown_entityref(self, name):
        pass # ignore by default; override if necessary

##
# An alias for the <b>HTMLTreeBuilder</b> class.

TreeBuilder = HTMLTreeBuilder

##
# Parse an HTML document or document fragment.
#
# @param source A filename or file object containing HTML data.
# @param encoding Optional character encoding, if known.  If omitted,
#     the parser looks for META tags inside the document.  If no tags
#     are found, the parser defaults to ISO-8859-1.
# @return An ElementTree instance

def parse(source, encoding=None):
    return ElementTree.parse(source, HTMLTreeBuilder(encoding=encoding))

if __name__ == "__main__":
    import sys
    ElementTree.dump(parse(open(sys.argv[1])))

########NEW FILE########
__FILENAME__ = SgmlopXMLTreeBuilder
#
# ElementTree
# $Id$
#
# A simple XML tree builder, based on the sgmlop library.
#
# Note that this version does not support namespaces.  This may be
# changed in future versions.
#
# history:
# 2004-03-28 fl   created
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Tools to build element trees from XML, based on the SGMLOP parser.
# <p>
# The current version does not support XML namespaces.
# <p>
# This tree builder requires the <b>sgmlop</b> extension module
# (available from
# <a href='http://effbot.org/downloads'>http://effbot.org/downloads</a>).
##

import ElementTree

##
# ElementTree builder for XML source data, based on the SGMLOP parser.
#
# @see elementtree.ElementTree

class TreeBuilder:

    def __init__(self, html=0):
        try:
            import sgmlop
        except ImportError:
            raise RuntimeError("sgmlop parser not available")
        self.__builder = ElementTree.TreeBuilder()
        if html:
            import htmlentitydefs
            self.entitydefs.update(htmlentitydefs.entitydefs)
        self.__parser = sgmlop.XMLParser()
        self.__parser.register(self)

    ##
    # Feeds data to the parser.
    #
    # @param data Encoded data.

    def feed(self, data):
        self.__parser.feed(data)

    ##
    # Finishes feeding data to the parser.
    #
    # @return An element structure.
    # @defreturn Element

    def close(self):
        self.__parser.close()
        self.__parser = None
        return self.__builder.close()

    def finish_starttag(self, tag, attrib):
        self.__builder.start(tag, attrib)

    def finish_endtag(self, tag):
        self.__builder.end(tag)

    def handle_data(self, data):
        self.__builder.data(data)

########NEW FILE########
__FILENAME__ = SimpleXMLTreeBuilder
#
# ElementTree
# $Id: SimpleXMLTreeBuilder.py 1862 2004-06-18 07:31:02Z Fredrik $
#
# A simple XML tree builder, based on Python's xmllib
#
# Note that due to bugs in xmllib, this builder does not fully support
# namespaces (unqualified attributes are put in the default namespace,
# instead of being left as is).  Run this module as a script to find
# out if this affects your Python version.
#
# history:
# 2001-10-20 fl   created
# 2002-05-01 fl   added namespace support for xmllib
# 2002-08-17 fl   added xmllib sanity test
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Tools to build element trees from XML files, using <b>xmllib</b>.
# This module can be used instead of the standard tree builder, for
# Python versions where "expat" is not available (such as 1.5.2).
# <p>
# Note that due to bugs in <b>xmllib</b>, the namespace support is
# not reliable (you can run the module as a script to find out exactly
# how unreliable it is on your Python version).
##

import xmllib, string

import ElementTree

##
# ElementTree builder for XML source data.
#
# @see elementtree.ElementTree

class TreeBuilder(xmllib.XMLParser):

    def __init__(self, html=0):
        self.__builder = ElementTree.TreeBuilder()
        if html:
            import htmlentitydefs
            self.entitydefs.update(htmlentitydefs.entitydefs)
        xmllib.XMLParser.__init__(self)

    ##
    # Feeds data to the parser.
    #
    # @param data Encoded data.

    def feed(self, data):
        xmllib.XMLParser.feed(self, data)

    ##
    # Finishes feeding data to the parser.
    #
    # @return An element structure.
    # @defreturn Element

    def close(self):
        xmllib.XMLParser.close(self)
        return self.__builder.close()

    def handle_data(self, data):
        self.__builder.data(data)

    handle_cdata = handle_data

    def unknown_starttag(self, tag, attrs):
        attrib = {}
        for key, value in attrs.items():
            attrib[fixname(key)] = value
        self.__builder.start(fixname(tag), attrib)

    def unknown_endtag(self, tag):
        self.__builder.end(fixname(tag))


def fixname(name, split=string.split):
    # xmllib in 2.0 and later provides limited (and slightly broken)
    # support for XML namespaces.
    if " " not in name:
        return name
    return "{%s}%s" % tuple(split(name, " ", 1))


if __name__ == "__main__":
    import sys
    # sanity check: look for known namespace bugs in xmllib
    p = TreeBuilder()
    text = """\
    <root xmlns='default'>
       <tag attribute='value' />
    </root>
    """
    p.feed(text)
    tree = p.close()
    status = []
    # check for bugs in the xmllib implementation
    tag = tree.find("{default}tag")
    if tag is None:
        status.append("namespaces not supported")
    if tag is not None and tag.get("{default}attribute"):
        status.append("default namespace applied to unqualified attribute")
    # report bugs
    if status:
        print "xmllib doesn't work properly in this Python version:"
        for bug in status:
            print "-", bug
    else:
        print "congratulations; no problems found in xmllib"


########NEW FILE########
__FILENAME__ = SimpleXMLWriter
#
# SimpleXMLWriter
# $Id: SimpleXMLWriter.py 2312 2005-03-02 18:13:39Z fredrik $
#
# a simple XML writer
#
# history:
# 2001-12-28 fl   created
# 2002-11-25 fl   fixed attribute encoding
# 2002-12-02 fl   minor fixes for 1.5.2
# 2004-06-17 fl   added pythondoc markup
# 2004-07-23 fl   added flush method (from Jay Graves)
# 2004-10-03 fl   added declaration method
#
# Copyright (c) 2001-2004 by Fredrik Lundh
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The SimpleXMLWriter module is
#
# Copyright (c) 2001-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Tools to write XML files, without having to deal with encoding
# issues, well-formedness, etc.
# <p>
# The current version does not provide built-in support for
# namespaces. To create files using namespaces, you have to provide
# "xmlns" attributes and explicitly add prefixes to tags and
# attributes.
#
# <h3>Patterns</h3>
#
# The following example generates a small XHTML document.
# <pre>
#
# from elementtree.SimpleXMLWriter import XMLWriter
# import sys
#
# w = XMLWriter(sys.stdout)
#
# html = w.start("html")
#
# w.start("head")
# w.element("title", "my document")
# w.element("meta", name="generator", value="my application 1.0")
# w.end()
#
# w.start("body")
# w.element("h1", "this is a heading")
# w.element("p", "this is a paragraph")
#
# w.start("p")
# w.data("this is ")
# w.element("b", "bold")
# w.data(" and ")
# w.element("i", "italic")
# w.data(".")
# w.end("p")
#
# w.close(html)
# </pre>
##

import re, sys, string

try:
    unicode("")
except NameError:
    def encode(s, encoding):
        # 1.5.2: application must use the right encoding
        return s
    _escape = re.compile(r"[&<>\"\x80-\xff]+") # 1.5.2
else:
    def encode(s, encoding):
        return s.encode(encoding)
    _escape = re.compile(eval(r'u"[&<>\"\u0080-\uffff]+"'))

def encode_entity(text, pattern=_escape):
    # map reserved and non-ascii characters to numerical entities
    def escape_entities(m):
        out = []
        for char in m.group():
            out.append("&#%d;" % ord(char))
        return string.join(out, "")
    return encode(pattern.sub(escape_entities, text), "ascii")

del _escape

#
# the following functions assume an ascii-compatible encoding
# (or "utf-16")

def escape_cdata(s, encoding=None, replace=string.replace):
    s = replace(s, "&", "&amp;")
    s = replace(s, "<", "&lt;")
    s = replace(s, ">", "&gt;")
    if encoding:
        try:
            return encode(s, encoding)
        except UnicodeError:
            return encode_entity(s)
    return s

def escape_attrib(s, encoding=None, replace=string.replace):
    s = replace(s, "&", "&amp;")
    s = replace(s, "'", "&apos;")
    s = replace(s, "\"", "&quot;")
    s = replace(s, "<", "&lt;")
    s = replace(s, ">", "&gt;")
    if encoding:
        try:
            return encode(s, encoding)
        except UnicodeError:
            return encode_entity(s)
    return s

##
# XML writer class.
#
# @param file A file or file-like object.  This object must implement
#    a <b>write</b> method that takes an 8-bit string.
# @param encoding Optional encoding.

class XMLWriter:

    def __init__(self, file, encoding="us-ascii"):
        if not hasattr(file, "write"):
            file = open(file, "w")
        self.__write = file.write
        if hasattr(file, "flush"):
            self.flush = file.flush
        self.__open = 0 # true if start tag is open
        self.__tags = []
        self.__data = []
        self.__encoding = encoding

    def __flush(self):
        # flush internal buffers
        if self.__open:
            self.__write(">")
            self.__open = 0
        if self.__data:
            data = string.join(self.__data, "")
            self.__write(escape_cdata(data, self.__encoding))
            self.__data = []

    ##
    # Writes an XML declaration.

    def declaration(self):
        encoding = self.__encoding
        if encoding == "us-ascii" or encoding == "utf-8":
            self.__write("<?xml version='1.0'?>\n")
        else:
            self.__write("<?xml version='1.0' encoding='%s'?>\n" % encoding)

    ##
    # Opens a new element.  Attributes can be given as keyword
    # arguments, or as a string/string dictionary. You can pass in
    # 8-bit strings or Unicode strings; the former are assumed to use
    # the encoding passed to the constructor.  The method returns an
    # opaque identifier that can be passed to the <b>close</b> method,
    # to close all open elements up to and including this one.
    #
    # @param tag Element tag.
    # @param attrib Attribute dictionary.  Alternatively, attributes
    #    can be given as keyword arguments.
    # @return An element identifier.

    def start(self, tag, attrib={}, **extra):
        self.__flush()
        tag = escape_cdata(tag, self.__encoding)
        self.__data = []
        self.__tags.append(tag)
        self.__write("<%s" % tag)
        if attrib or extra:
            attrib = attrib.copy()
            attrib.update(extra)
            attrib = attrib.items()
            attrib.sort()
            for k, v in attrib:
                k = escape_cdata(k, self.__encoding)
                v = escape_attrib(v, self.__encoding)
                self.__write(" %s=\"%s\"" % (k, v))
        self.__open = 1
        return len(self.__tags)-1

    ##
    # Adds a comment to the output stream.
    #
    # @param comment Comment text, as an 8-bit string or Unicode string.

    def comment(self, comment):
        self.__flush()
        self.__write("<!-- %s -->\n" % escape_cdata(comment, self.__encoding))

    ##
    # Adds character data to the output stream.
    #
    # @param text Character data, as an 8-bit string or Unicode string.

    def data(self, text):
        self.__data.append(text)

    ##
    # Closes the current element (opened by the most recent call to
    # <b>start</b>).
    #
    # @param tag Element tag.  If given, the tag must match the start
    #    tag.  If omitted, the current element is closed.

    def end(self, tag=None):
        if tag:
            assert self.__tags, "unbalanced end(%s)" % tag
            assert escape_cdata(tag, self.__encoding) == self.__tags[-1],\
                   "expected end(%s), got %s" % (self.__tags[-1], tag)
        else:
            assert self.__tags, "unbalanced end()"
        tag = self.__tags.pop()
        if self.__data:
            self.__flush()
        elif self.__open:
            self.__open = 0
            self.__write(" />")
            return
        self.__write("</%s>" % tag)

    ##
    # Closes open elements, up to (and including) the element identified
    # by the given identifier.
    #
    # @param id Element identifier, as returned by the <b>start</b> method.

    def close(self, id):
        while len(self.__tags) > id:
            self.end()

    ##
    # Adds an entire element.  This is the same as calling <b>start</b>,
    # <b>data</b>, and <b>end</b> in sequence. The <b>text</b> argument
    # can be omitted.

    def element(self, tag, text=None, attrib={}, **extra):
        apply(self.start, (tag, attrib), extra)
        if text:
            self.data(text)
        self.end()

    ##
    # Flushes the output stream.

    def flush(self):
        pass # replaced by the constructor

########NEW FILE########
__FILENAME__ = TidyHTMLTreeBuilder
#
# ElementTree
# $Id: TidyHTMLTreeBuilder.py 2304 2005-03-01 17:42:41Z fredrik $
#

from elementtidy.TidyHTMLTreeBuilder import *

########NEW FILE########
__FILENAME__ = TidyTools
#
# ElementTree
# $Id: TidyTools.py 1862 2004-06-18 07:31:02Z Fredrik $
#
# tools to run the "tidy" command on an HTML or XHTML file, and return
# the contents as an XHTML element tree.
#
# history:
# 2002-10-19 fl   added to ElementTree library; added getzonebody function
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#

##
# Tools to build element trees from HTML, using the external <b>tidy</b>
# utility.
##

import glob, string, os, sys

from ElementTree import ElementTree, Element

NS_XHTML = "{http://www.w3.org/1999/xhtml}"

##
# Convert an HTML or HTML-like file to XHTML, using the <b>tidy</b>
# command line utility.
#
# @param file Filename.
# @param new_inline_tags An optional list of valid but non-standard
#     inline tags.
# @return An element tree, or None if not successful.

def tidy(file, new_inline_tags=None):

    command = ["tidy", "-qn", "-asxml"]

    if new_inline_tags:
        command.append("--new-inline-tags")
        command.append(string.join(new_inline_tags, ","))

    # FIXME: support more tidy options!

    # convert
    os.system(
        "%s %s >%s.out 2>%s.err" % (string.join(command), file, file, file)
        )
    # check that the result is valid XML
    try:
        tree = ElementTree()
        tree.parse(file + ".out")
    except:
        print "*** %s:%s" % sys.exc_info()[:2]
        print ("*** %s is not valid XML "
               "(check %s.err for info)" % (file, file))
        tree = None
    else:
        if os.path.isfile(file + ".out"):
            os.remove(file + ".out")
        if os.path.isfile(file + ".err"):
            os.remove(file + ".err")

    return tree

##
# Get document body from a an HTML or HTML-like file.  This function
# uses the <b>tidy</b> function to convert HTML to XHTML, and cleans
# up the resulting XML tree.
#
# @param file Filename.
# @return A <b>body</b> element, or None if not successful.

def getbody(file, **options):
    # get clean body from text file

    # get xhtml tree
    try:
        tree = apply(tidy, (file,), options)
        if tree is None:
            return
    except IOError, v:
        print "***", v
        return None

    NS = NS_XHTML

    # remove namespace uris
    for node in tree.getiterator():
        if node.tag.startswith(NS):
            node.tag = node.tag[len(NS):]

    body = tree.getroot().find("body")

    return body

##
# Same as <b>getbody</b>, but turns plain text at the start of the
# document into an H1 tag.  This function can be used to parse zone
# documents.
#
# @param file Filename.
# @return A <b>body</b> element, or None if not successful.

def getzonebody(file, **options):

    body = getbody(file, **options)
    if body is None:
        return

    if body.text and string.strip(body.text):
        title = Element("h1")
        title.text = string.strip(body.text)
        title.tail = "\n\n"
        body.insert(0, title)

    body.text = None

    return body

if __name__ == "__main__":

    import sys
    for arg in sys.argv[1:]:
        for file in glob.glob(arg):
            print file, "...", tidy(file)

########NEW FILE########
__FILENAME__ = XMLTreeBuilder
#
# ElementTree
# $Id: XMLTreeBuilder.py 2305 2005-03-01 17:43:09Z fredrik $
#
# an XML tree builder
#
# history:
# 2001-10-20 fl   created
# 2002-05-01 fl   added namespace support for xmllib
# 2002-07-27 fl   require expat (1.5.2 code can use SimpleXMLTreeBuilder)
# 2002-08-17 fl   use tag/attribute name memo cache
# 2002-12-04 fl   moved XMLTreeBuilder to the ElementTree module
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Tools to build element trees from XML files.
##

import ElementTree

##
# (obsolete) ElementTree builder for XML source data, based on the
# <b>expat</b> parser.
# <p>
# This class is an alias for ElementTree.XMLTreeBuilder.  New code
# should use that version instead.
#
# @see elementtree.ElementTree

class TreeBuilder(ElementTree.XMLTreeBuilder):
    pass

##
# (experimental) An alternate builder that supports manipulation of
# new elements.

class FancyTreeBuilder(TreeBuilder):

    def __init__(self, html=0):
        TreeBuilder.__init__(self, html)
        self._parser.StartNamespaceDeclHandler = self._start_ns
        self._parser.EndNamespaceDeclHandler = self._end_ns
        self.namespaces = []

    def _start(self, tag, attrib_in):
        elem = TreeBuilder._start(self, tag, attrib_in)
        self.start(elem)

    def _start_list(self, tag, attrib_in):
        elem = TreeBuilder._start_list(self, tag, attrib_in)
        self.start(elem)

    def _end(self, tag):
        elem = TreeBuilder._end(self, tag)
        self.end(elem)

    def _start_ns(self, prefix, value):
        self.namespaces.insert(0, (prefix, value))

    def _end_ns(self, prefix):
        assert self.namespaces.pop(0)[0] == prefix, "implementation confused"

    ##
    # Hook method that's called when a new element has been opened.
    # May access the <b>namespaces</b> attribute.
    #
    # @param element The new element.  The tag name and attributes are,
    #     set, but it has no children, and the text and tail attributes
    #     are still empty.

    def start(self, element):
        pass

    ##
    # Hook method that's called when a new element has been closed.
    # May access the <b>namespaces</b> attribute.
    #
    # @param element The new element.

    def end(self, element):
        pass

########NEW FILE########
__FILENAME__ = fetcher
#!/usr/bin/python
#
# Copyright 2007, Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
An HTTPFetcher implementation that uses Google App Engine's urlfetch module.

HTTPFetcher is an interface defined in the top-level fetchers module in
  JanRain's OpenID python library: http://openidenabled.com/python-openid/

For more, see openid/fetchers.py in that library.
"""

import logging

from openid import fetchers
from google.appengine.api import urlfetch


class UrlfetchFetcher(fetchers.HTTPFetcher):
  """An HTTPFetcher subclass that uses Google App Engine's urlfetch module.
  """
  def fetch(self, url, body=None, headers=None):
    """
    This performs an HTTP POST or GET, following redirects along
    the way. If a body is specified, then the request will be a
    POST. Otherwise, it will be a GET.

    @param headers: HTTP headers to include with the request
    @type headers: {str:str}

    @return: An object representing the server's HTTP response. If
      there are network or protocol errors, an exception will be
      raised. HTTP error responses, like 404 or 500, do not
      cause exceptions.

    @rtype: L{HTTPResponse}

    @raise Exception: Different implementations will raise
      different errors based on the underlying HTTP library.
    """
    if not fetchers._allowedURL(url):
      raise ValueError('Bad URL scheme: %r' % (url,))

    if not headers:
      headers = {}

    if body:
      method = urlfetch.POST
      if 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    else:
      method = urlfetch.GET

    if not headers:
      headers = {}

    # follow up to 10 redirects
    for i in range(10):
      resp = urlfetch.fetch(url, body, method, headers)
      if resp.status_code in (301, 302):
        logging.debug('Following %d redirect to %s' %
                      (resp.status_code, resp.headers['location']))
        url = resp.headers['location']
      else:
        break

    return fetchers.HTTPResponse(url, resp.status_code, resp.headers,
                                 resp.content)

########NEW FILE########
__FILENAME__ = filters
import re
from google.appengine.ext import webapp

register = webapp.template.create_template_register()

def linkify(text):
  """Escape tags, add line breaks, and linkify HTTP URLs."""
  if not text:
    return ""
  text = text.replace('<', '&lt;').replace('>', '&gt;').replace("\n", '<br/>\n')
  text = re.sub(r'\b((?:https?|irc|git)://[\w\-\/\?\&\=\.\:\%\#]+)',
                lambda x: "<a href='%s'>%s</a>" % (x.group(1), x.group(1)),
                text)
  return text

register.filter(linkify)


########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#
# Copyright 2010 Brad Fitzpatrick
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


import os
import re
import logging

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

import consumer
import models
import filters

webapp.template.register_template_library('filters')


def GetCurrentUser(request):
  """Returns a User entity (OpenID or Google) or None."""
  user = users.get_current_user()
  if user:
    return models.User(google_user=user)
  session_id = request.cookies.get('session', '')
  if not session_id:
    return None
  login = consumer.Login.get_by_key_name(session_id)
  if not login:
    return None
  return models.User(openid_user=login.claimed_id)


class IndexHandler(webapp.RequestHandler):

  def get(self):
    user = GetCurrentUser(self.request)
    template_values = {
      "user": user,
    }
    self.response.out.write(template.render("index.html", template_values))


class SiteHandler(webapp.RequestHandler):

  def get(self):
    self.response.out.write("I'm a site page.")


class LoginHandler(webapp.RequestHandler):

  def get(self):
    next_url = self.request.get("next")
    if not re.match(r'^/[\w/]*$', next_url):
      next_url = '/'
    user = GetCurrentUser(self.request)
    google_login_url = users.create_login_url('/s/notelogin?next=' + next_url)
    template_values = {
      "user": user,
      "google_login_url": google_login_url,
    }
    self.response.out.write(template.render("login.html", template_values))


class NoteLoginHandler(webapp.RequestHandler):
  """Update a just-logged-in user's last_login property and send them along."""
  
  def get(self):
    next_url = self.request.get("next")
    if not re.match(r'^/[\w/]*$', next_url):
      next_url = '/'
    user = GetCurrentUser(self.request)
    if user:
      user = user.GetOrCreateFromDatastore()
      user.put()  # updates time
    self.redirect(next_url)


class LogoutHandler(webapp.RequestHandler):
  def get(self):
    next_url = self.request.get("next")
    if not re.match(r'^/[\w/]*$', next_url):
      next_url = '/'
    user = GetCurrentUser(self.request)
    if user:
      user.LogOut(self, next_url)
    else:
      self.redirect(next_url)


class UserHandler(webapp.RequestHandler):

  def get(self, user_key):
    user = GetCurrentUser(self.request)
    profile_user = models.User.get_by_key_name(user_key)
    if not profile_user:
      self.response.set_status(404)
      return
    can_edit = user and user.sha1_key == profile_user.sha1_key
    edit_mode = can_edit and (self.request.get('mode') == "edit")

    # get all the projects that this user maintains metadata for
    pquery = db.Query(models.Project, keys_only=True)
    pquery.filter('owner =', profile_user)
    projects = [key.name() for key in pquery.fetch(500)]

    url = ""
    if profile_user.openid_user:
      url = profile_user.openid_user
    elif profile_user.url:
      url = profile_user.url

    template_values = {
      "user": user,   # logged-in user, or None
      "edit_mode": edit_mode,
      "can_edit": can_edit,
      "profile_user": profile_user,
      "user_key": user_key,   # the sha1-ish thing
      "projects": projects,   # list(str), of project keys
      "url": url,
    }
    self.response.out.write(template.render("user.html", template_values))


class CreateHandler(webapp.RequestHandler):

  def get(self):
    user = GetCurrentUser(self.request)
    if not user:
      self.redirect('/s/login?next=/s/create')
      return
    template_values = {
      "user": user,
    }
    self.response.out.write(template.render("create.html", template_values))

  def post(self):
    user = GetCurrentUser(self.request)
    if not user:
      self.redirect('/s/login?next=/s/create')
      return
    def error(msg):
      self.response.out.write("Error creating project:<ul><li>%s</li></ul>." %
                              msg)
      return
    project_key = self.request.get('project')
    if not project_key:
      return error("No project specified.")
    if not re.match(r'^[a-z][a-z0-9\.\-]*[a-z0-9]$', project_key):
      return error("Project name must match regular expression " +
                   "<tt>/^[a-z][a-z0-9\.\-]*[a-z0-9]$/</tt>.")
    project = models.Project.get_by_key_name(project_key)
    if project:
      return error("Project already exists: <a href='/%s'>%s</a>" %
                   (project_key, project_key))
    user = user.GetOrCreateFromDatastore()
    project = models.Project(key_name=project_key,
                             owner=user)
    project.put()
    self.redirect("/%s" % project_key)


class ProjectHandler(webapp.RequestHandler):

  def get(self, project_key):
    user = GetCurrentUser(self.request)
    project = models.Project.get_by_key_name(project_key)
    if not project:
      self.response.set_status(404)
    can_edit = user and project and user.sha1_key == project.owner.sha1_key
    edit_mode = can_edit and (self.request.get('mode') == "edit")

    template_values = {
      "user": user,
      "project": project,
      "edit_mode": edit_mode,
      "can_edit": can_edit,
      "project_key": project_key,
    }
    self.response.out.write(template.render("project.html", template_values))


class ProjectEditHandler(webapp.RequestHandler):
  """Handles POSTs to edit a project."""

  def post(self):
    user = GetCurrentUser(self.request)
    project_key = self.request.get('project')
    logging.info("project key: %s", project_key)
    project = models.Project.get_by_key_name(project_key)
    logging.info("project: %s", project)
    if not project:
      self.response.set_status(404)
      return
    can_edit = user and user.sha1_key == project.owner.sha1_key
    if not can_edit:
      self.response.set_status(403)
      return
    project.how_to = self.request.get("how_to")
    project.code_repo = self.request.get("code_repo")
    project.home_page = self.request.get("home_page")
    project.bug_tracker = self.request.get("bug_tracker")
    project.put()
    self.redirect('/' + project_key)


class BrowseHandler(webapp.RequestHandler):

  def get(self):
    user = GetCurrentUser(self.request)

    projects = models.Project.all().order('__key__')
    if self.request.get("start"):
      projects = projects.filter('__key__ >=',
                                 db.Key.from_path(models.Project.kind(),
                                                  self.request.get("start")))
    PAGE_SIZE = 25
    projects = projects.fetch(PAGE_SIZE + 1)
    next_page_project = None
    if len(projects) > PAGE_SIZE:
      next_page_project = projects[-1]
      projects = projects[0:PAGE_SIZE]

    template_values = {
      "user": user,
      "projects": projects,
      "next_page_project": next_page_project,
    }
    self.response.out.write(template.render("browse.html", template_values))


def main():
  application = webapp.WSGIApplication([
      ('/', IndexHandler),
      ('/s/create', CreateHandler),
      ('/s/login', LoginHandler),
      ('/s/logout', LogoutHandler),
      ('/s/editproject', ProjectEditHandler),
      ('/s/notelogin', NoteLoginHandler),
      ('/s/browse/?', BrowseHandler),
      ('/s/.*', SiteHandler),
      (r'/u/([a-f0-9]{6,})', UserHandler),
      (r'/([a-z][a-z0-9\.\-]*[a-z0-9])/?', ProjectHandler),
      ],
      debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
#
# Copyright 2010 Brad Fitzpatrick
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


from google.appengine.api import users
from google.appengine.ext import db

import logging
import sha

SALT = 'Contributing!'

class User(db.Model):
  """A user's global state, not specific to a project."""
  # One of these will be set:
  google_user = db.UserProperty(indexed=True, required=False)
  openid_user = db.StringProperty(indexed=True, required=False)

  url = db.StringProperty(indexed=False)
  last_login = db.DateTimeProperty(auto_now=True)

  @property
  def last_login_short(self):
    return str(self.last_login)[0:10]

  @property
  def display_name(self):
    if self.google_user:
      return self.google_user.email
    if self.openid_user:
      return self.openid_user
    return "Unknown user type"

  @property
  def public_name(self):
    if self.google_user:
      email = self.google_user.email()
      return email[0:email.find('@')+1] + "..."
    if self.openid_user:
      return self.openid_user
    return "Unknown user type"

  @property
  def profile_page_url(self):
    return "/u/" + self.sha1_key

  @property
  def sha1_key(self):
    if self.google_user:
      return sha.sha(self.google_user.email() + SALT).hexdigest()[0:8]
    if self.openid_user:
      return sha.sha(self.openid_user + SALT).hexdigest()[0:8]
    return Exception("unknown user type")

  def LogOut(self, handler, next_url):
    if self.google_user:
      handler.redirect(users.create_logout_url(next_url))
      return
    handler.response.headers.add_header(
      'Set-Cookie', 'session=; path=/')
    handler.redirect(next_url)

  def GetOrCreateFromDatastore(self):
    return User.get_or_insert(self.sha1_key,
                              google_user=self.google_user,
                              openid_user=self.openid_user)


class Project(db.Model):
  """A project which can be contributed to, with its metadata."""
  pretty_name = db.StringProperty(required=False)
  owner = db.ReferenceProperty(User, required=True)
  last_edit = db.DateTimeProperty(auto_now=True)

  how_to = db.TextProperty(default="")
  code_repo = db.StringProperty(indexed=False, default="")
  home_page = db.StringProperty(indexed=False, default="")
  bug_tracker = db.StringProperty(indexed=False, default="")

  @property
  def name(self):
    return self.key().name()

  @property
  def display_name(self):
    if self.pretty_name:
      return self.pretty_name
    return self.name

  @property
  def last_edit_short(self):
    return str(self.last_edit)[0:10]


class Contributor(db.Model):
  """A user-project tuple."""
  user = db.ReferenceProperty(User, required=True)
  project = db.ReferenceProperty(Project, required=True)

  is_active = db.BooleanProperty()
  role = db.StringProperty()  # e.g. "Founder" freeform.
  
  

########NEW FILE########
__FILENAME__ = association
# -*- test-case-name: openid.test.test_association -*-
"""
This module contains code for dealing with associations between
consumers and servers. Associations contain a shared secret that is
used to sign C{openid.mode=id_res} messages.

Users of the library should not usually need to interact directly with
associations. The L{store<openid.store>},
L{server<openid.server.server>} and
L{consumer<openid.consumer.consumer>} objects will create and manage
the associations. The consumer and server code will make use of a
C{L{SessionNegotiator}} when managing associations, which enables
users to express a preference for what kind of associations should be
allowed, and what kind of exchange should be done to establish the
association.

@var default_negotiator: A C{L{SessionNegotiator}} that allows all
    association types that are specified by the OpenID
    specification. It prefers to use HMAC-SHA1/DH-SHA1, if it's
    available. If HMAC-SHA256 is not supported by your Python runtime,
    HMAC-SHA256 and DH-SHA256 will not be available.

@var encrypted_negotiator: A C{L{SessionNegotiator}} that
    does not support C{'no-encryption'} associations. It prefers
    HMAC-SHA1/DH-SHA1 association types if available.
"""

__all__ = [
    'default_negotiator',
    'encrypted_negotiator',
    'SessionNegotiator',
    'Association',
    ]

import time

from openid import cryptutil
from openid import kvform
from openid import oidutil
from openid.message import OPENID_NS

all_association_types = [
    'HMAC-SHA1',
    'HMAC-SHA256',
    ]

if hasattr(cryptutil, 'hmacSha256'):
    supported_association_types = list(all_association_types)

    default_association_order = [
        ('HMAC-SHA1', 'DH-SHA1'),
        ('HMAC-SHA1', 'no-encryption'),
        ('HMAC-SHA256', 'DH-SHA256'),
        ('HMAC-SHA256', 'no-encryption'),
        ]

    only_encrypted_association_order = [
        ('HMAC-SHA1', 'DH-SHA1'),
        ('HMAC-SHA256', 'DH-SHA256'),
        ]
else:
    supported_association_types = ['HMAC-SHA1']

    default_association_order = [
        ('HMAC-SHA1', 'DH-SHA1'),
        ('HMAC-SHA1', 'no-encryption'),
        ]

    only_encrypted_association_order = [
        ('HMAC-SHA1', 'DH-SHA1'),
        ]

def getSessionTypes(assoc_type):
    """Return the allowed session types for a given association type"""
    assoc_to_session = {
        'HMAC-SHA1': ['DH-SHA1', 'no-encryption'],
        'HMAC-SHA256': ['DH-SHA256', 'no-encryption'],
        }
    return assoc_to_session.get(assoc_type, [])

def checkSessionType(assoc_type, session_type):
    """Check to make sure that this pair of assoc type and session
    type are allowed"""
    if session_type not in getSessionTypes(assoc_type):
        raise ValueError(
            'Session type %r not valid for assocation type %r'
            % (session_type, assoc_type))

class SessionNegotiator(object):
    """A session negotiator controls the allowed and preferred
    association types and association session types. Both the
    C{L{Consumer<openid.consumer.consumer.Consumer>}} and
    C{L{Server<openid.server.server.Server>}} use negotiators when
    creating associations.

    You can create and use negotiators if you:

     - Do not want to do Diffie-Hellman key exchange because you use
       transport-layer encryption (e.g. SSL)

     - Want to use only SHA-256 associations

     - Do not want to support plain-text associations over a non-secure
       channel

    It is up to you to set a policy for what kinds of associations to
    accept. By default, the library will make any kind of association
    that is allowed in the OpenID 2.0 specification.

    Use of negotiators in the library
    =================================

    When a consumer makes an association request, it calls
    C{L{getAllowedType}} to get the preferred association type and
    association session type.

    The server gets a request for a particular association/session
    type and calls C{L{isAllowed}} to determine if it should
    create an association. If it is supported, negotiation is
    complete. If it is not, the server calls C{L{getAllowedType}} to
    get an allowed association type to return to the consumer.

    If the consumer gets an error response indicating that the
    requested association/session type is not supported by the server
    that contains an assocation/session type to try, it calls
    C{L{isAllowed}} to determine if it should try again with the
    given combination of association/session type.

    @ivar allowed_types: A list of association/session types that are
        allowed by the server. The order of the pairs in this list
        determines preference. If an association/session type comes
        earlier in the list, the library is more likely to use that
        type.
    @type allowed_types: [(str, str)]
    """

    def __init__(self, allowed_types):
        self.setAllowedTypes(allowed_types)

    def copy(self):
        return self.__class__(list(self.allowed_types))

    def setAllowedTypes(self, allowed_types):
        """Set the allowed association types, checking to make sure
        each combination is valid."""
        for (assoc_type, session_type) in allowed_types:
            checkSessionType(assoc_type, session_type)

        self.allowed_types = allowed_types

    def addAllowedType(self, assoc_type, session_type=None):
        """Add an association type and session type to the allowed
        types list. The assocation/session pairs are tried in the
        order that they are added."""
        if self.allowed_types is None:
            self.allowed_types = []

        if session_type is None:
            available = getSessionTypes(assoc_type)

            if not available:
                raise ValueError('No session available for association type %r'
                                 % (assoc_type,))

            for session_type in getSessionTypes(assoc_type):
                self.addAllowedType(assoc_type, session_type)
        else:
            checkSessionType(assoc_type, session_type)
            self.allowed_types.append((assoc_type, session_type))


    def isAllowed(self, assoc_type, session_type):
        """Is this combination of association type and session type allowed?"""
        assoc_good = (assoc_type, session_type) in self.allowed_types
        matches = session_type in getSessionTypes(assoc_type)
        return assoc_good and matches

    def getAllowedType(self):
        """Get a pair of assocation type and session type that are
        supported"""
        try:
            return self.allowed_types[0]
        except IndexError:
            return (None, None)

default_negotiator = SessionNegotiator(default_association_order)
encrypted_negotiator = SessionNegotiator(only_encrypted_association_order)

def getSecretSize(assoc_type):
    if assoc_type == 'HMAC-SHA1':
        return 20
    elif assoc_type == 'HMAC-SHA256':
        return 32
    else:
        raise ValueError('Unsupported association type: %r' % (assoc_type,))

class Association(object):
    """
    This class represents an association between a server and a
    consumer.  In general, users of this library will never see
    instances of this object.  The only exception is if you implement
    a custom C{L{OpenIDStore<openid.store.interface.OpenIDStore>}}.

    If you do implement such a store, it will need to store the values
    of the C{L{handle}}, C{L{secret}}, C{L{issued}}, C{L{lifetime}}, and
    C{L{assoc_type}} instance variables.

    @ivar handle: This is the handle the server gave this association.

    @type handle: C{str}


    @ivar secret: This is the shared secret the server generated for
        this association.

    @type secret: C{str}


    @ivar issued: This is the time this association was issued, in
        seconds since 00:00 GMT, January 1, 1970.  (ie, a unix
        timestamp)

    @type issued: C{int}


    @ivar lifetime: This is the amount of time this association is
        good for, measured in seconds since the association was
        issued.

    @type lifetime: C{int}


    @ivar assoc_type: This is the type of association this instance
        represents.  The only valid value of this field at this time
        is C{'HMAC-SHA1'}, but new types may be defined in the future.

    @type assoc_type: C{str}


    @sort: __init__, fromExpiresIn, getExpiresIn, __eq__, __ne__,
        handle, secret, issued, lifetime, assoc_type
    """

    # The ordering and name of keys as stored by serialize
    assoc_keys = [
        'version',
        'handle',
        'secret',
        'issued',
        'lifetime',
        'assoc_type',
        ]


    _macs = {
        'HMAC-SHA1': cryptutil.hmacSha1,
        'HMAC-SHA256': cryptutil.hmacSha256,
        }


    def fromExpiresIn(cls, expires_in, handle, secret, assoc_type):
        """
        This is an alternate constructor used by the OpenID consumer
        library to create associations.  C{L{OpenIDStore
        <openid.store.interface.OpenIDStore>}} implementations
        shouldn't use this constructor.


        @param expires_in: This is the amount of time this association
            is good for, measured in seconds since the association was
            issued.

        @type expires_in: C{int}


        @param handle: This is the handle the server gave this
            association.

        @type handle: C{str}


        @param secret: This is the shared secret the server generated
            for this association.

        @type secret: C{str}


        @param assoc_type: This is the type of association this
            instance represents.  The only valid value of this field
            at this time is C{'HMAC-SHA1'}, but new types may be
            defined in the future.

        @type assoc_type: C{str}
        """
        issued = int(time.time())
        lifetime = expires_in
        return cls(handle, secret, issued, lifetime, assoc_type)

    fromExpiresIn = classmethod(fromExpiresIn)

    def __init__(self, handle, secret, issued, lifetime, assoc_type):
        """
        This is the standard constructor for creating an association.


        @param handle: This is the handle the server gave this
            association.

        @type handle: C{str}


        @param secret: This is the shared secret the server generated
            for this association.

        @type secret: C{str}


        @param issued: This is the time this association was issued,
            in seconds since 00:00 GMT, January 1, 1970.  (ie, a unix
            timestamp)

        @type issued: C{int}


        @param lifetime: This is the amount of time this association
            is good for, measured in seconds since the association was
            issued.

        @type lifetime: C{int}


        @param assoc_type: This is the type of association this
            instance represents.  The only valid value of this field
            at this time is C{'HMAC-SHA1'}, but new types may be
            defined in the future.

        @type assoc_type: C{str}
        """
        if assoc_type not in all_association_types:
            fmt = '%r is not a supported association type'
            raise ValueError(fmt % (assoc_type,))

#         secret_size = getSecretSize(assoc_type)
#         if len(secret) != secret_size:
#             fmt = 'Wrong size secret (%s bytes) for association type %s'
#             raise ValueError(fmt % (len(secret), assoc_type))

        self.handle = handle
        self.secret = secret
        self.issued = issued
        self.lifetime = lifetime
        self.assoc_type = assoc_type

    def getExpiresIn(self, now=None):
        """
        This returns the number of seconds this association is still
        valid for, or C{0} if the association is no longer valid.


        @return: The number of seconds this association is still valid
            for, or C{0} if the association is no longer valid.

        @rtype: C{int}
        """
        if now is None:
            now = int(time.time())

        return max(0, self.issued + self.lifetime - now)

    expiresIn = property(getExpiresIn)

    def __eq__(self, other):
        """
        This checks to see if two C{L{Association}} instances
        represent the same association.


        @return: C{True} if the two instances represent the same
            association, C{False} otherwise.

        @rtype: C{bool}
        """
        return type(self) is type(other) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        """
        This checks to see if two C{L{Association}} instances
        represent different associations.


        @return: C{True} if the two instances represent different
            associations, C{False} otherwise.

        @rtype: C{bool}
        """
        return not (self == other)

    def serialize(self):
        """
        Convert an association to KV form.

        @return: String in KV form suitable for deserialization by
            deserialize.

        @rtype: str
        """
        data = {
            'version':'2',
            'handle':self.handle,
            'secret':oidutil.toBase64(self.secret),
            'issued':str(int(self.issued)),
            'lifetime':str(int(self.lifetime)),
            'assoc_type':self.assoc_type
            }

        assert len(data) == len(self.assoc_keys)
        pairs = []
        for field_name in self.assoc_keys:
            pairs.append((field_name, data[field_name]))

        return kvform.seqToKV(pairs, strict=True)

    def deserialize(cls, assoc_s):
        """
        Parse an association as stored by serialize().

        inverse of serialize


        @param assoc_s: Association as serialized by serialize()

        @type assoc_s: str


        @return: instance of this class
        """
        pairs = kvform.kvToSeq(assoc_s, strict=True)
        keys = []
        values = []
        for k, v in pairs:
            keys.append(k)
            values.append(v)

        if keys != cls.assoc_keys:
            raise ValueError('Unexpected key values: %r', keys)

        version, handle, secret, issued, lifetime, assoc_type = values
        if version != '2':
            raise ValueError('Unknown version: %r' % version)
        issued = int(issued)
        lifetime = int(lifetime)
        secret = oidutil.fromBase64(secret)
        return cls(handle, secret, issued, lifetime, assoc_type)

    deserialize = classmethod(deserialize)

    def sign(self, pairs):
        """
        Generate a signature for a sequence of (key, value) pairs


        @param pairs: The pairs to sign, in order

        @type pairs: sequence of (str, str)


        @return: The binary signature of this sequence of pairs

        @rtype: str
        """
        kv = kvform.seqToKV(pairs)

        try:
            mac = self._macs[self.assoc_type]
        except KeyError:
            raise ValueError(
                'Unknown association type: %r' % (self.assoc_type,))

        return mac(self.secret, kv)


    def getMessageSignature(self, message):
        """Return the signature of a message.

        If I am not a sign-all association, the message must have a
        signed list.

        @return: the signature, base64 encoded

        @rtype: str

        @raises ValueError: If there is no signed list and I am not a sign-all
            type of association.
        """
        pairs = self._makePairs(message)
        return oidutil.toBase64(self.sign(pairs))

    def signMessage(self, message):
        """Add a signature (and a signed list) to a message.

        @return: a new Message object with a signature
        @rtype: L{openid.message.Message}
        """
        if (message.hasKey(OPENID_NS, 'sig') or
            message.hasKey(OPENID_NS, 'signed')):
            raise ValueError('Message already has signed list or signature')

        extant_handle = message.getArg(OPENID_NS, 'assoc_handle')
        if extant_handle and extant_handle != self.handle:
            raise ValueError("Message has a different association handle")

        signed_message = message.copy()
        signed_message.setArg(OPENID_NS, 'assoc_handle', self.handle)
        message_keys = signed_message.toPostArgs().keys()
        signed_list = [k[7:] for k in message_keys
                       if k.startswith('openid.')]
        signed_list.append('signed')
        signed_list.sort()
        signed_message.setArg(OPENID_NS, 'signed', ','.join(signed_list))
        sig = self.getMessageSignature(signed_message)
        signed_message.setArg(OPENID_NS, 'sig', sig)
        return signed_message

    def checkMessageSignature(self, message):
        """Given a message with a signature, calculate a new signature
        and return whether it matches the signature in the message.

        @raises ValueError: if the message has no signature or no signature
            can be calculated for it.
        """        
        message_sig = message.getArg(OPENID_NS, 'sig')
        if not message_sig:
            raise ValueError("%s has no sig." % (message,))
        calculated_sig = self.getMessageSignature(message)
        return calculated_sig == message_sig


    def _makePairs(self, message):
        signed = message.getArg(OPENID_NS, 'signed')
        if not signed:
            raise ValueError('Message has no signed list: %s' % (message,))

        signed_list = signed.split(',')
        pairs = []
        data = message.toPostArgs()
        for field in signed_list:
            pairs.append((field, data.get('openid.' + field, '')))
        return pairs

    def __repr__(self):
        return "<%s.%s %s %s>" % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.assoc_type,
            self.handle)

########NEW FILE########
__FILENAME__ = consumer
# -*- test-case-name: openid.test.test_consumer -*-
"""OpenID support for Relying Parties (aka Consumers).

This module documents the main interface with the OpenID consumer
library.  The only part of the library which has to be used and isn't
documented in full here is the store required to create an
C{L{Consumer}} instance.  More on the abstract store type and
concrete implementations of it that are provided in the documentation
for the C{L{__init__<Consumer.__init__>}} method of the
C{L{Consumer}} class.


OVERVIEW
========

    The OpenID identity verification process most commonly uses the
    following steps, as visible to the user of this library:

        1. The user enters their OpenID into a field on the consumer's
           site, and hits a login button.

        2. The consumer site discovers the user's OpenID provider using
           the Yadis protocol.

        3. The consumer site sends the browser a redirect to the
           OpenID provider.  This is the authentication request as
           described in the OpenID specification.

        4. The OpenID provider's site sends the browser a redirect
           back to the consumer site.  This redirect contains the
           provider's response to the authentication request.

    The most important part of the flow to note is the consumer's site
    must handle two separate HTTP requests in order to perform the
    full identity check.


LIBRARY DESIGN
==============

    This consumer library is designed with that flow in mind.  The
    goal is to make it as easy as possible to perform the above steps
    securely.

    At a high level, there are two important parts in the consumer
    library.  The first important part is this module, which contains
    the interface to actually use this library.  The second is the
    C{L{openid.store.interface}} module, which describes the
    interface to use if you need to create a custom method for storing
    the state this library needs to maintain between requests.

    In general, the second part is less important for users of the
    library to know about, as several implementations are provided
    which cover a wide variety of situations in which consumers may
    use the library.

    This module contains a class, C{L{Consumer}}, with methods
    corresponding to the actions necessary in each of steps 2, 3, and
    4 described in the overview.  Use of this library should be as easy
    as creating an C{L{Consumer}} instance and calling the methods
    appropriate for the action the site wants to take.


SESSIONS, STORES, AND STATELESS MODE
====================================

    The C{L{Consumer}} object keeps track of two types of state:

        1. State of the user's current authentication attempt.  Things like
           the identity URL, the list of endpoints discovered for that
           URL, and in case where some endpoints are unreachable, the list
           of endpoints already tried.  This state needs to be held from
           Consumer.begin() to Consumer.complete(), but it is only applicable
           to a single session with a single user agent, and at the end of
           the authentication process (i.e. when an OP replies with either
           C{id_res} or C{cancel}) it may be discarded.

        2. State of relationships with servers, i.e. shared secrets
           (associations) with servers and nonces seen on signed messages.
           This information should persist from one session to the next and
           should not be bound to a particular user-agent.


    These two types of storage are reflected in the first two arguments of
    Consumer's constructor, C{session} and C{store}.  C{session} is a
    dict-like object and we hope your web framework provides you with one
    of these bound to the user agent.  C{store} is an instance of
    L{openid.store.interface.OpenIDStore}.

    Since the store does hold secrets shared between your application and the
    OpenID provider, you should be careful about how you use it in a shared
    hosting environment.  If the filesystem or database permissions of your
    web host allow strangers to read from them, do not store your data there!
    If you have no safe place to store your data, construct your consumer
    with C{None} for the store, and it will operate only in stateless mode.
    Stateless mode may be slower, put more load on the OpenID provider, and
    trusts the provider to keep you safe from replay attacks.


    Several store implementation are provided, and the interface is
    fully documented so that custom stores can be used as well.  See
    the documentation for the C{L{Consumer}} class for more
    information on the interface for stores.  The implementations that
    are provided allow the consumer site to store the necessary data
    in several different ways, including several SQL databases and
    normal files on disk.


IMMEDIATE MODE
==============

    In the flow described above, the user may need to confirm to the
    OpenID provider that it's ok to disclose his or her identity.
    The provider may draw pages asking for information from the user
    before it redirects the browser back to the consumer's site.  This
    is generally transparent to the consumer site, so it is typically
    ignored as an implementation detail.

    There can be times, however, where the consumer site wants to get
    a response immediately.  When this is the case, the consumer can
    put the library in immediate mode.  In immediate mode, there is an
    extra response possible from the server, which is essentially the
    server reporting that it doesn't have enough information to answer
    the question yet.


USING THIS LIBRARY
==================

    Integrating this library into an application is usually a
    relatively straightforward process.  The process should basically
    follow this plan:

    Add an OpenID login field somewhere on your site.  When an OpenID
    is entered in that field and the form is submitted, it should make
    a request to the your site which includes that OpenID URL.

    First, the application should L{instantiate a Consumer<Consumer.__init__>}
    with a session for per-user state and store for shared state.
    using the store of choice.

    Next, the application should call the 'C{L{begin<Consumer.begin>}}' method on the
    C{L{Consumer}} instance.  This method takes the OpenID URL.  The
    C{L{begin<Consumer.begin>}} method returns an C{L{AuthRequest}}
    object.

    Next, the application should call the
    C{L{redirectURL<AuthRequest.redirectURL>}} method on the
    C{L{AuthRequest}} object.  The parameter C{return_to} is the URL
    that the OpenID server will send the user back to after attempting
    to verify his or her identity.  The C{realm} parameter is the
    URL (or URL pattern) that identifies your web site to the user
    when he or she is authorizing it.  Send a redirect to the
    resulting URL to the user's browser.

    That's the first half of the authentication process.  The second
    half of the process is done after the user's OpenID Provider sends the
    user's browser a redirect back to your site to complete their
    login.

    When that happens, the user will contact your site at the URL
    given as the C{return_to} URL to the
    C{L{redirectURL<AuthRequest.redirectURL>}} call made
    above.  The request will have several query parameters added to
    the URL by the OpenID provider as the information necessary to
    finish the request.

    Get an C{L{Consumer}} instance with the same session and store as
    before and call its C{L{complete<Consumer.complete>}} method,
    passing in all the received query arguments.

    There are multiple possible return types possible from that
    method. These indicate the whether or not the login was
    successful, and include any additional information appropriate for
    their type.

@var SUCCESS: constant used as the status for
    L{SuccessResponse<openid.consumer.consumer.SuccessResponse>} objects.

@var FAILURE: constant used as the status for
    L{FailureResponse<openid.consumer.consumer.FailureResponse>} objects.

@var CANCEL: constant used as the status for
    L{CancelResponse<openid.consumer.consumer.CancelResponse>} objects.

@var SETUP_NEEDED: constant used as the status for
    L{SetupNeededResponse<openid.consumer.consumer.SetupNeededResponse>}
    objects.
"""

import cgi
import copy
import logging
from urlparse import urlparse, urldefrag

from openid import fetchers
from openid import oidutil

from openid.consumer.discover import discover, OpenIDServiceEndpoint, \
     DiscoveryFailure, OPENID_1_0_TYPE, OPENID_1_1_TYPE, OPENID_2_0_TYPE
from openid.message import Message, OPENID_NS, OPENID2_NS, OPENID1_NS, \
     IDENTIFIER_SELECT, no_default, BARE_NS
from openid import cryptutil
from openid import oidutil
from openid.association import Association, default_negotiator, \
     SessionNegotiator
from openid.dh import DiffieHellman
from openid.store.nonce import mkNonce, split as splitNonce
from openid.yadis.manager import Discovery


__all__ = ['AuthRequest', 'Consumer', 'SuccessResponse',
           'SetupNeededResponse', 'CancelResponse', 'FailureResponse',
           'SUCCESS', 'FAILURE', 'CANCEL', 'SETUP_NEEDED',
           ]


def appEngineLoggingFunction(message, level=0):
    # Level is unused.
    logging.info(message)


oidutil.log = appEngineLoggingFunction


def makeKVPost(request_message, server_url):
    """Make a Direct Request to an OpenID Provider and return the
    result as a Message object.

    @raises openid.fetchers.HTTPFetchingError: if an error is
        encountered in making the HTTP post.

    @rtype: L{openid.message.Message}
    """
    # XXX: TESTME
    resp = fetchers.fetch(server_url, body=request_message.toURLEncoded())

    # Process response in separate function that can be shared by async code.
    return _httpResponseToMessage(resp, server_url)


def _httpResponseToMessage(response, server_url):
    """Adapt a POST response to a Message.

    @type response: L{openid.fetchers.HTTPResponse}
    @param response: Result of a POST to an OpenID endpoint.

    @rtype: L{openid.message.Message}

    @raises openid.fetchers.HTTPFetchingError: if the server returned a
        status of other than 200 or 400.

    @raises ServerError: if the server returned an OpenID error.
    """
    # Should this function be named Message.fromHTTPResponse instead?
    response_message = Message.fromKVForm(response.body)
    if response.status == 400:
        raise ServerError.fromMessage(response_message)

    elif response.status != 200:
        fmt = 'bad status code from server %s: %s'
        error_message = fmt % (server_url, response.status)
        raise fetchers.HTTPFetchingError(error_message)

    return response_message



class Consumer(object):
    """An OpenID consumer implementation that performs discovery and
    does session management.

    @ivar consumer: an instance of an object implementing the OpenID
        protocol, but doing no discovery or session management.

    @type consumer: GenericConsumer

    @ivar session: A dictionary-like object representing the user's
        session data.  This is used for keeping state of the OpenID
        transaction when the user is redirected to the server.

    @cvar session_key_prefix: A string that is prepended to session
        keys to ensure that they are unique. This variable may be
        changed to suit your application.
    """
    session_key_prefix = "_openid_consumer_"

    _token = 'last_token'

    _discover = staticmethod(discover)

    def __init__(self, session, store, consumer_class=None):
        """Initialize a Consumer instance.

        You should create a new instance of the Consumer object with
        every HTTP request that handles OpenID transactions.

        @param session: See L{the session instance variable<openid.consumer.consumer.Consumer.session>}

        @param store: an object that implements the interface in
            C{L{openid.store.interface.OpenIDStore}}.  Several
            implementations are provided, to cover common database
            environments.

        @type store: C{L{openid.store.interface.OpenIDStore}}

        @see: L{openid.store.interface}
        @see: L{openid.store}
        """
        self.session = session
        if consumer_class is None:
            consumer_class = GenericConsumer
        self.consumer = consumer_class(store)
        self._token_key = self.session_key_prefix + self._token

    def begin(self, user_url, anonymous=False):
        """Start the OpenID authentication process. See steps 1-2 in
        the overview at the top of this file.

        @param user_url: Identity URL given by the user. This method
            performs a textual transformation of the URL to try and
            make sure it is normalized. For example, a user_url of
            example.com will be normalized to http://example.com/
            normalizing and resolving any redirects the server might
            issue.

        @type user_url: unicode

        @param anonymous: Whether to make an anonymous request of the OpenID
            provider.  Such a request does not ask for an authorization
            assertion for an OpenID identifier, but may be used with
            extensions to pass other data.  e.g. "I don't care who you are,
            but I'd like to know your time zone."

        @type anonymous: bool

        @returns: An object containing the discovered information will
            be returned, with a method for building a redirect URL to
            the server, as described in step 3 of the overview. This
            object may also be used to add extension arguments to the
            request, using its
            L{addExtensionArg<openid.consumer.consumer.AuthRequest.addExtensionArg>}
            method.

        @returntype: L{AuthRequest<openid.consumer.consumer.AuthRequest>}

        @raises openid.consumer.discover.DiscoveryFailure: when I fail to
            find an OpenID server for this URL.  If the C{yadis} package
            is available, L{openid.consumer.discover.DiscoveryFailure} is
            an alias for C{yadis.discover.DiscoveryFailure}.
        """
        disco = Discovery(self.session, user_url, self.session_key_prefix)
        try:
            service = disco.getNextService(self._discover)
        except fetchers.HTTPFetchingError, why:
            raise DiscoveryFailure(
                'Error fetching XRDS document: %s' % (why[0],), None)

        if service is None:
            raise DiscoveryFailure(
                'No usable OpenID services found for %s' % (user_url,), None)
        else:
            return self.beginWithoutDiscovery(service, anonymous)

    def beginWithoutDiscovery(self, service, anonymous=False):
        """Start OpenID verification without doing OpenID server
        discovery. This method is used internally by Consumer.begin
        after discovery is performed, and exists to provide an
        interface for library users needing to perform their own
        discovery.

        @param service: an OpenID service endpoint descriptor.  This
            object and factories for it are found in the
            L{openid.consumer.discover} module.

        @type service:
            L{OpenIDServiceEndpoint<openid.consumer.discover.OpenIDServiceEndpoint>}

        @returns: an OpenID authentication request object.

        @rtype: L{AuthRequest<openid.consumer.consumer.AuthRequest>}

        @See: Openid.consumer.consumer.Consumer.begin
        @see: openid.consumer.discover
        """
        auth_req = self.consumer.begin(service)
        self.session[self._token_key] = auth_req.endpoint

        try:
            auth_req.setAnonymous(anonymous)
        except ValueError, why:
            raise ProtocolError(str(why))

        return auth_req

    def complete(self, query, return_to):
        """Called to interpret the server's response to an OpenID
        request. It is called in step 4 of the flow described in the
        consumer overview.

        @param query: A dictionary of the query parameters for this
            HTTP request.

        @param return_to: The return URL used to invoke the
            application.  Extract the URL from your application's web
            request framework and specify it here to have it checked
            against the openid.return_to value in the response.  If
            the return_to URL check fails, the status of the
            completion will be FAILURE.

        @returns: a subclass of Response. The type of response is
            indicated by the status attribute, which will be one of
            SUCCESS, CANCEL, FAILURE, or SETUP_NEEDED.

        @see: L{SuccessResponse<openid.consumer.consumer.SuccessResponse>}
        @see: L{CancelResponse<openid.consumer.consumer.CancelResponse>}
        @see: L{SetupNeededResponse<openid.consumer.consumer.SetupNeededResponse>}
        @see: L{FailureResponse<openid.consumer.consumer.FailureResponse>}
        """

        endpoint = self.session.get(self._token_key)

        message = Message.fromPostArgs(query)
        response = self.consumer.complete(message, endpoint, return_to)

        try:
            del self.session[self._token_key]
        except KeyError:
            pass

        if (response.status in ['success', 'cancel'] and
            response.identity_url is not None):

            disco = Discovery(self.session,
                              response.identity_url,
                              self.session_key_prefix)
            # This is OK to do even if we did not do discovery in
            # the first place.
            disco.cleanup(force=True)

        return response

    def setAssociationPreference(self, association_preferences):
        """Set the order in which association types/sessions should be
        attempted. For instance, to only allow HMAC-SHA256
        associations created with a DH-SHA256 association session:

        >>> consumer.setAssociationPreference([('HMAC-SHA256', 'DH-SHA256')])

        Any association type/association type pair that is not in this
        list will not be attempted at all.

        @param association_preferences: The list of allowed
            (association type, association session type) pairs that
            should be allowed for this consumer to use, in order from
            most preferred to least preferred.
        @type association_preferences: [(str, str)]

        @returns: None

        @see: C{L{openid.association.SessionNegotiator}}
        """
        self.consumer.negotiator = SessionNegotiator(association_preferences)

class DiffieHellmanSHA1ConsumerSession(object):
    session_type = 'DH-SHA1'
    hash_func = staticmethod(cryptutil.sha1)
    secret_size = 20
    allowed_assoc_types = ['HMAC-SHA1']

    def __init__(self, dh=None):
        if dh is None:
            dh = DiffieHellman.fromDefaults()

        self.dh = dh

    def getRequest(self):
        cpub = cryptutil.longToBase64(self.dh.public)

        args = {'dh_consumer_public': cpub}

        if not self.dh.usingDefaultValues():
            args.update({
                'dh_modulus': cryptutil.longToBase64(self.dh.modulus),
                'dh_gen': cryptutil.longToBase64(self.dh.generator),
                })

        return args

    def extractSecret(self, response):
        dh_server_public64 = response.getArg(
            OPENID_NS, 'dh_server_public', no_default)
        enc_mac_key64 = response.getArg(OPENID_NS, 'enc_mac_key', no_default)
        dh_server_public = cryptutil.base64ToLong(dh_server_public64)
        enc_mac_key = oidutil.fromBase64(enc_mac_key64)
        return self.dh.xorSecret(dh_server_public, enc_mac_key, self.hash_func)

class DiffieHellmanSHA256ConsumerSession(DiffieHellmanSHA1ConsumerSession):
    session_type = 'DH-SHA256'
    hash_func = staticmethod(cryptutil.sha256)
    secret_size = 32
    allowed_assoc_types = ['HMAC-SHA256']

class PlainTextConsumerSession(object):
    session_type = 'no-encryption'
    allowed_assoc_types = ['HMAC-SHA1', 'HMAC-SHA256']

    def getRequest(self):
        return {}

    def extractSecret(self, response):
        mac_key64 = response.getArg(OPENID_NS, 'mac_key', no_default)
        return oidutil.fromBase64(mac_key64)

class SetupNeededError(Exception):
    """Internally-used exception that indicates that an immediate-mode
    request cancelled."""
    def __init__(self, user_setup_url=None):
        Exception.__init__(self, user_setup_url)
        self.user_setup_url = user_setup_url

class ProtocolError(ValueError):
    """Exception that indicates that a message violated the
    protocol. It is raised and caught internally to this file."""

class TypeURIMismatch(ProtocolError):
    """A protocol error arising from type URIs mismatching
    """

    def __init__(self, expected, endpoint):
        ProtocolError.__init__(self, expected, endpoint)
        self.expected = expected
        self.endpoint = endpoint

    def __str__(self):
        s = '<%s.%s: Required type %s not found in %s for endpoint %s>' % (
            self.__class__.__module__, self.__class__.__name__,
            self.expected, self.endpoint.type_uris, self.endpoint)
        return s



class ServerError(Exception):
    """Exception that is raised when the server returns a 400 response
    code to a direct request."""

    def __init__(self, error_text, error_code, message):
        Exception.__init__(self, error_text)
        self.error_text = error_text
        self.error_code = error_code
        self.message = message

    def fromMessage(cls, message):
        """Generate a ServerError instance, extracting the error text
        and the error code from the message."""
        error_text = message.getArg(
            OPENID_NS, 'error', '<no error message supplied>')
        error_code = message.getArg(OPENID_NS, 'error_code')
        return cls(error_text, error_code, message)

    fromMessage = classmethod(fromMessage)

class GenericConsumer(object):
    """This is the implementation of the common logic for OpenID
    consumers. It is unaware of the application in which it is
    running.

    @ivar negotiator: An object that controls the kind of associations
        that the consumer makes. It defaults to
        C{L{openid.association.default_negotiator}}. Assign a
        different negotiator to it if you have specific requirements
        for how associations are made.
    @type negotiator: C{L{openid.association.SessionNegotiator}}
    """

    # The name of the query parameter that gets added to the return_to
    # URL when using OpenID1. You can change this value if you want or
    # need a different name, but don't make it start with openid,
    # because it's not a standard protocol thing for OpenID1. For
    # OpenID2, the library will take care of the nonce using standard
    # OpenID query parameter names.
    openid1_nonce_query_arg_name = 'janrain_nonce'

    # Another query parameter that gets added to the return_to for
    # OpenID 1; if the user's session state is lost, use this claimed
    # identifier to do discovery when verifying the response.
    openid1_return_to_identifier_name = 'openid1_claimed_id'

    session_types = {
        'DH-SHA1':DiffieHellmanSHA1ConsumerSession,
        'DH-SHA256':DiffieHellmanSHA256ConsumerSession,
        'no-encryption':PlainTextConsumerSession,
        }

    _discover = staticmethod(discover)

    def __init__(self, store):
        self.store = store
        self.negotiator = default_negotiator.copy()

    def begin(self, service_endpoint):
        """Create an AuthRequest object for the specified
        service_endpoint. This method will create an association if
        necessary."""
        if self.store is None:
            assoc = None
        else:
            assoc = self._getAssociation(service_endpoint)

        request = AuthRequest(service_endpoint, assoc)
        request.return_to_args[self.openid1_nonce_query_arg_name] = mkNonce()

        if request.message.isOpenID1():
            request.return_to_args[self.openid1_return_to_identifier_name] = \
                request.endpoint.claimed_id

        return request

    def complete(self, message, endpoint, return_to):
        """Process the OpenID message, using the specified endpoint
        and return_to URL as context. This method will handle any
        OpenID message that is sent to the return_to URL.
        """
        mode = message.getArg(OPENID_NS, 'mode', '<No mode set>')

        modeMethod = getattr(self, '_complete_' + mode,
                             self._completeInvalid)

        return modeMethod(message, endpoint, return_to)

    def _complete_cancel(self, message, endpoint, _):
        return CancelResponse(endpoint)

    def _complete_error(self, message, endpoint, _):
        error = message.getArg(OPENID_NS, 'error')
        contact = message.getArg(OPENID_NS, 'contact')
        reference = message.getArg(OPENID_NS, 'reference')

        return FailureResponse(endpoint, error, contact=contact,
                               reference=reference)

    def _complete_setup_needed(self, message, endpoint, _):
        if not message.isOpenID2():
            return self._completeInvalid(message, endpoint, _)

        return SetupNeededResponse(endpoint)

    def _complete_id_res(self, message, endpoint, return_to):
        try:
            self._checkSetupNeeded(message)
        except SetupNeededError, why:
            return SetupNeededResponse(endpoint, why.user_setup_url)
        else:
            try:
                return self._doIdRes(message, endpoint, return_to)
            except (ProtocolError, DiscoveryFailure), why:
                return FailureResponse(endpoint, why[0])

    def _completeInvalid(self, message, endpoint, _):
        mode = message.getArg(OPENID_NS, 'mode', '<No mode set>')
        return FailureResponse(endpoint,
                               'Invalid openid.mode: %r' % (mode,))

    def _checkReturnTo(self, message, return_to):
        """Check an OpenID message and its openid.return_to value
        against a return_to URL from an application.  Return True on
        success, False on failure.
        """
        # Check the openid.return_to args against args in the original
        # message.
        try:
            self._verifyReturnToArgs(message.toPostArgs())
        except ProtocolError, why:
            oidutil.log("Verifying return_to arguments: %s" % (why[0],))
            return False

        # Check the return_to base URL against the one in the message.
        msg_return_to = message.getArg(OPENID_NS, 'return_to')

        # The URL scheme, authority, and path MUST be the same between
        # the two URLs.
        app_parts = urlparse(return_to)
        msg_parts = urlparse(msg_return_to)

        # (addressing scheme, network location, path) must be equal in
        # both URLs.
        for part in range(0, 3):
            if app_parts[part] != msg_parts[part]:
                return False

        return True

    _makeKVPost = staticmethod(makeKVPost)

    def _checkSetupNeeded(self, message):
        """Check an id_res message to see if it is a
        checkid_immediate cancel response.

        @raises SetupNeededError: if it is a checkid_immediate cancellation
        """
        # In OpenID 1, we check to see if this is a cancel from
        # immediate mode by the presence of the user_setup_url
        # parameter.
        if message.isOpenID1():
            user_setup_url = message.getArg(OPENID1_NS, 'user_setup_url')
            if user_setup_url is not None:
                raise SetupNeededError(user_setup_url)

    def _doIdRes(self, message, endpoint, return_to):
        """Handle id_res responses that are not cancellations of
        immediate mode requests.

        @param message: the response paramaters.
        @param endpoint: the discovered endpoint object. May be None.

        @raises ProtocolError: If the message contents are not
            well-formed according to the OpenID specification. This
            includes missing fields or not signing fields that should
            be signed.

        @raises DiscoveryFailure: If the subject of the id_res message
            does not match the supplied endpoint, and discovery on the
            identifier in the message fails (this should only happen
            when using OpenID 2)

        @returntype: L{Response}
        """
        # Checks for presence of appropriate fields (and checks
        # signed list fields)
        self._idResCheckForFields(message)

        if not self._checkReturnTo(message, return_to):
            raise ProtocolError(
                "return_to does not match return URL. Expected %r, got %r"
                % (return_to, message.getArg(OPENID_NS, 'return_to')))


        # Verify discovery information:
        endpoint = self._verifyDiscoveryResults(message, endpoint)
        oidutil.log("Received id_res response from %s using association %s" %
                    (endpoint.server_url,
                     message.getArg(OPENID_NS, 'assoc_handle')))

        self._idResCheckSignature(message, endpoint.server_url)

        # Will raise a ProtocolError if the nonce is bad
        self._idResCheckNonce(message, endpoint)

        signed_list_str = message.getArg(OPENID_NS, 'signed', no_default)
        signed_list = signed_list_str.split(',')
        signed_fields = ["openid." + s for s in signed_list]
        return SuccessResponse(endpoint, message, signed_fields)

    def _idResGetNonceOpenID1(self, message, endpoint):
        """Extract the nonce from an OpenID 1 response.  Return the
        nonce from the BARE_NS since we independently check the
        return_to arguments are the same as those in the response
        message.

        See the openid1_nonce_query_arg_name class variable

        @returns: The nonce as a string or None
        """
        return message.getArg(BARE_NS, self.openid1_nonce_query_arg_name)

    def _idResCheckNonce(self, message, endpoint):
        if message.isOpenID1():
            # This indicates that the nonce was generated by the consumer
            nonce = self._idResGetNonceOpenID1(message, endpoint)
            server_url = ''
        else:
            nonce = message.getArg(OPENID2_NS, 'response_nonce')
            server_url = endpoint.server_url

        if nonce is None:
            raise ProtocolError('Nonce missing from response')

        try:
            timestamp, salt = splitNonce(nonce)
        except ValueError, why:
            raise ProtocolError('Malformed nonce: %s' % (why[0],))

        if (self.store is not None and
            not self.store.useNonce(server_url, timestamp, salt)):
            raise ProtocolError('Nonce already used or out of range')

    def _idResCheckSignature(self, message, server_url):
        assoc_handle = message.getArg(OPENID_NS, 'assoc_handle')
        if self.store is None:
            assoc = None
        else:
            assoc = self.store.getAssociation(server_url, assoc_handle)

        if assoc:
            if assoc.getExpiresIn() <= 0:
                # XXX: It might be a good idea sometimes to re-start the
                # authentication with a new association. Doing it
                # automatically opens the possibility for
                # denial-of-service by a server that just returns expired
                # associations (or really short-lived associations)
                raise ProtocolError(
                    'Association with %s expired' % (server_url,))

            if not assoc.checkMessageSignature(message):
                raise ProtocolError('Bad signature')

        else:
            # It's not an association we know about.  Stateless mode is our
            # only possible path for recovery.
            # XXX - async framework will not want to block on this call to
            # _checkAuth.
            if not self._checkAuth(message, server_url):
                raise ProtocolError('Server denied check_authentication')

    def _idResCheckForFields(self, message):
        # XXX: this should be handled by the code that processes the
        # response (that is, if a field is missing, we should not have
        # to explicitly check that it's present, just make sure that
        # the fields are actually being used by the rest of the code
        # in tests). Although, which fields are signed does need to be
        # checked somewhere.
        basic_fields = ['return_to', 'assoc_handle', 'sig', 'signed']
        basic_sig_fields = ['return_to', 'identity']

        require_fields = {
            OPENID2_NS: basic_fields + ['op_endpoint'],
            OPENID1_NS: basic_fields + ['identity'],
            }

        require_sigs = {
            OPENID2_NS: basic_sig_fields + ['response_nonce',
                                            'claimed_id',
                                            'assoc_handle',],
            OPENID1_NS: basic_sig_fields,
            }

        for field in require_fields[message.getOpenIDNamespace()]:
            if not message.hasKey(OPENID_NS, field):
                raise ProtocolError('Missing required field %r' % (field,))

        signed_list_str = message.getArg(OPENID_NS, 'signed', no_default)
        signed_list = signed_list_str.split(',')

        for field in require_sigs[message.getOpenIDNamespace()]:
            # Field is present and not in signed list
            if message.hasKey(OPENID_NS, field) and field not in signed_list:
                raise ProtocolError('"%s" not signed' % (field,))


    def _verifyReturnToArgs(query):
        """Verify that the arguments in the return_to URL are present in this
        response.
        """
        message = Message.fromPostArgs(query)
        return_to = message.getArg(OPENID_NS, 'return_to')

        if return_to is None:
            raise ProtocolError('Response has no return_to')

        parsed_url = urlparse(return_to)
        rt_query = parsed_url[4]
        parsed_args = cgi.parse_qsl(rt_query)

        for rt_key, rt_value in parsed_args:
            try:
                value = query[rt_key]
                if rt_value != value:
                    format = ("parameter %s value %r does not match "
                              "return_to's value %r")
                    raise ProtocolError(format % (rt_key, value, rt_value))
            except KeyError:
                format = "return_to parameter %s absent from query %r"
                raise ProtocolError(format % (rt_key, query))

        # Make sure all non-OpenID arguments in the response are also
        # in the signed return_to.
        bare_args = message.getArgs(BARE_NS)
        for pair in bare_args.iteritems():
            if pair not in parsed_args:
                raise ProtocolError("Parameter %s not in return_to URL" % (pair[0],))

    _verifyReturnToArgs = staticmethod(_verifyReturnToArgs)

    def _verifyDiscoveryResults(self, resp_msg, endpoint=None):
        """
        Extract the information from an OpenID assertion message and
        verify it against the original

        @param endpoint: The endpoint that resulted from doing discovery
        @param resp_msg: The id_res message object

        @returns: the verified endpoint
        """
        if resp_msg.getOpenIDNamespace() == OPENID2_NS:
            return self._verifyDiscoveryResultsOpenID2(resp_msg, endpoint)
        else:
            return self._verifyDiscoveryResultsOpenID1(resp_msg, endpoint)


    def _verifyDiscoveryResultsOpenID2(self, resp_msg, endpoint):
        to_match = OpenIDServiceEndpoint()
        to_match.type_uris = [OPENID_2_0_TYPE]
        to_match.claimed_id = resp_msg.getArg(OPENID2_NS, 'claimed_id')
        to_match.local_id = resp_msg.getArg(OPENID2_NS, 'identity')

        # Raises a KeyError when the op_endpoint is not present
        to_match.server_url = resp_msg.getArg(
            OPENID2_NS, 'op_endpoint', no_default)

        # claimed_id and identifier must both be present or both
        # be absent
        if (to_match.claimed_id is None and
            to_match.local_id is not None):
            raise ProtocolError(
                'openid.identity is present without openid.claimed_id')

        elif (to_match.claimed_id is not None and
              to_match.local_id is None):
            raise ProtocolError(
                'openid.claimed_id is present without openid.identity')

        # This is a response without identifiers, so there's really no
        # checking that we can do, so return an endpoint that's for
        # the specified `openid.op_endpoint'
        elif to_match.claimed_id is None:
            return OpenIDServiceEndpoint.fromOPEndpointURL(to_match.server_url)

        # The claimed ID doesn't match, so we have to do discovery
        # again. This covers not using sessions, OP identifier
        # endpoints and responses that didn't match the original
        # request.
        if not endpoint:
            oidutil.log('No pre-discovered information supplied.')
            endpoint = self._discoverAndVerify(to_match)
        else:
            # The claimed ID matches, so we use the endpoint that we
            # discovered in initiation. This should be the most common
            # case.
            try:
                self._verifyDiscoverySingle(endpoint, to_match)
            except ProtocolError, e:
                oidutil.log("Error attempting to use stored discovery information: " +
                            str(e))
                oidutil.log("Attempting discovery to verify endpoint")
                endpoint = self._discoverAndVerify(to_match)

        # The endpoint we return should have the claimed ID from the
        # message we just verified, fragment and all.
        if endpoint.claimed_id != to_match.claimed_id:
            endpoint = copy.copy(endpoint)
            endpoint.claimed_id = to_match.claimed_id
        return endpoint

    def _verifyDiscoveryResultsOpenID1(self, resp_msg, endpoint):
        claimed_id = resp_msg.getArg(BARE_NS, self.openid1_return_to_identifier_name)

        if endpoint is None and claimed_id is None:
            raise RuntimeError(
                'When using OpenID 1, the claimed ID must be supplied, '
                'either by passing it through as a return_to parameter '
                'or by using a session, and supplied to the GenericConsumer '
                'as the argument to complete()')
        elif endpoint is not None and claimed_id is None:
            claimed_id = endpoint.claimed_id

        to_match = OpenIDServiceEndpoint()
        to_match.type_uris = [OPENID_1_1_TYPE]
        to_match.local_id = resp_msg.getArg(OPENID1_NS, 'identity')
        # Restore delegate information from the initiation phase
        to_match.claimed_id = claimed_id

        if to_match.local_id is None:
            raise ProtocolError('Missing required field openid.identity')

        to_match_1_0 = copy.copy(to_match)
        to_match_1_0.type_uris = [OPENID_1_0_TYPE]

        if endpoint is not None:
            try:
                try:
                    self._verifyDiscoverySingle(endpoint, to_match)
                except TypeURIMismatch:
                    self._verifyDiscoverySingle(endpoint, to_match_1_0)
            except ProtocolError, e:
                oidutil.log("Error attempting to use stored discovery information: " +
                            str(e))
                oidutil.log("Attempting discovery to verify endpoint")
            else:
                return endpoint

        # Endpoint is either bad (failed verification) or None
        try:
            return self._discoverAndVerify(to_match)
        except TypeURIMismatch:
            return self._discoverAndVerify(to_match_1_0)

    def _verifyDiscoverySingle(self, endpoint, to_match):
        """Verify that the given endpoint matches the information
        extracted from the OpenID assertion, and raise an exception if
        there is a mismatch.

        @type endpoint: openid.consumer.discover.OpenIDServiceEndpoint
        @type to_match: openid.consumer.discover.OpenIDServiceEndpoint

        @rtype: NoneType

        @raises ProtocolError: when the endpoint does not match the
            discovered information.
        """
        # Every type URI that's in the to_match endpoint has to be
        # present in the discovered endpoint.
        for type_uri in to_match.type_uris:
            if not endpoint.usesExtension(type_uri):
                raise TypeURIMismatch(type_uri, endpoint)

        # Fragments do not influence discovery, so we can't compare a
        # claimed identifier with a fragment to discovered information.
        defragged_claimed_id, _ = urldefrag(to_match.claimed_id)
        if defragged_claimed_id != endpoint.claimed_id:
            raise ProtocolError(
                'Claimed ID does not match (different subjects!), '
                'Expected %s, got %s' %
                (defragged_claimed_id, endpoint.claimed_id))

        if to_match.getLocalID() != endpoint.getLocalID():
            raise ProtocolError('local_id mismatch. Expected %s, got %s' %
                                (to_match.getLocalID(), endpoint.getLocalID()))

        # If the server URL is None, this must be an OpenID 1
        # response, because op_endpoint is a required parameter in
        # OpenID 2. In that case, we don't actually care what the
        # discovered server_url is, because signature checking or
        # check_auth should take care of that check for us.
        if to_match.server_url is None:
            assert to_match.preferredNamespace() == OPENID1_NS, (
                """The code calling this must ensure that OpenID 2
                responses have a non-none `openid.op_endpoint' and
                that it is set as the `server_url' attribute of the
                `to_match' endpoint.""")

        elif to_match.server_url != endpoint.server_url:
            raise ProtocolError('OP Endpoint mismatch. Expected %s, got %s' %
                                (to_match.server_url, endpoint.server_url))

    def _discoverAndVerify(self, to_match):
        """Given an endpoint object created from the information in an
        OpenID response, perform discovery and verify the discovery
        results, returning the matching endpoint that is the result of
        doing that discovery.

        @type to_match: openid.consumer.discover.OpenIDServiceEndpoint
        @param to_match: The endpoint whose information we're confirming

        @rtype: openid.consumer.discover.OpenIDServiceEndpoint
        @returns: The result of performing discovery on the claimed
            identifier in `to_match'

        @raises DiscoveryFailure: when discovery fails.
        """
        oidutil.log('Performing discovery on %s' % (to_match.claimed_id,))
        _, services = self._discover(to_match.claimed_id)
        if not services:
            raise DiscoveryFailure('No OpenID information found at %s' %
                                   (to_match.claimed_id,), None)
        return self._verifyDiscoveredServices(services, to_match)


    def _verifyDiscoveredServices(self, services, to_match):
        """See @L{_discoverAndVerify}"""

        # Search the services resulting from discovery to find one
        # that matches the information from the assertion
        failure_messages = []
        for endpoint in services:
            try:
                self._verifyDiscoverySingle(endpoint, to_match)
            except ProtocolError, why:
                failure_messages.append(str(why))
            else:
                # It matches, so discover verification has
                # succeeded. Return this endpoint.
                return endpoint
        else:
            oidutil.log('Discovery verification failure for %s' %
                        (to_match.claimed_id,))
            for failure_message in failure_messages:
                oidutil.log(' * Endpoint mismatch: ' + failure_message)

            raise DiscoveryFailure(
                'No matching endpoint found after discovering %s'
                % (to_match.claimed_id,), None)

    def _checkAuth(self, message, server_url):
        """Make a check_authentication request to verify this message.

        @returns: True if the request is valid.
        @rtype: bool
        """
        oidutil.log('Using OpenID check_authentication')
        request = self._createCheckAuthRequest(message)
        if request is None:
            return False
        try:
            response = self._makeKVPost(request, server_url)
        except (fetchers.HTTPFetchingError, ServerError), e:
            oidutil.log('check_authentication failed: %s' % (e[0],))
            return False
        else:
            return self._processCheckAuthResponse(response, server_url)

    def _createCheckAuthRequest(self, message):
        """Generate a check_authentication request message given an
        id_res message.
        """
        # Arguments that are always passed to the server and not
        # included in the signature.
        whitelist = ['assoc_handle', 'sig', 'signed', 'invalidate_handle']

        check_args = {}
        for k in whitelist:
            val = message.getArg(OPENID_NS, k)
            if val is not None:
                check_args[k] = val

        signed = message.getArg(OPENID_NS, 'signed')
        if signed:
            for k in signed.split(','):
                val = message.getAliasedArg(k)

                # Signed value is missing
                if val is None:
                    oidutil.log('Missing signed field %r' % (k,))
                    return None

                check_args[k] = val

        check_args['mode'] = 'check_authentication'
        return Message.fromOpenIDArgs(check_args)

    def _processCheckAuthResponse(self, response, server_url):
        """Process the response message from a check_authentication
        request, invalidating associations if requested.
        """
        is_valid = response.getArg(OPENID_NS, 'is_valid', 'false')

        invalidate_handle = response.getArg(OPENID_NS, 'invalidate_handle')
        if invalidate_handle is not None:
            oidutil.log(
                'Received "invalidate_handle" from server %s' % (server_url,))
            if self.store is None:
                oidutil.log('Unexpectedly got invalidate_handle without '
                            'a store!')
            else:
                self.store.removeAssociation(server_url, invalidate_handle)

        if is_valid == 'true':
            return True
        else:
            oidutil.log('Server responds that checkAuth call is not valid')
            return False

    def _getAssociation(self, endpoint):
        """Get an association for the endpoint's server_url.

        First try seeing if we have a good association in the
        store. If we do not, then attempt to negotiate an association
        with the server.

        If we negotiate a good association, it will get stored.

        @returns: A valid association for the endpoint's server_url or None
        @rtype: openid.association.Association or NoneType
        """
        assoc = self.store.getAssociation(endpoint.server_url)

        if assoc is None or assoc.expiresIn <= 0:
            assoc = self._negotiateAssociation(endpoint)
            if assoc is not None:
                self.store.storeAssociation(endpoint.server_url, assoc)

        return assoc

    def _negotiateAssociation(self, endpoint):
        """Make association requests to the server, attempting to
        create a new association.

        @returns: a new association object

        @rtype: L{openid.association.Association}
        """
        # Get our preferred session/association type from the negotiatior.
        assoc_type, session_type = self.negotiator.getAllowedType()

        try:
            assoc = self._requestAssociation(
                endpoint, assoc_type, session_type)
        except ServerError, why:
            supportedTypes = self._extractSupportedAssociationType(why,
                                                                   endpoint,
                                                                   assoc_type)
            if supportedTypes is not None:
                assoc_type, session_type = supportedTypes
                # Attempt to create an association from the assoc_type
                # and session_type that the server told us it
                # supported.
                try:
                    assoc = self._requestAssociation(
                        endpoint, assoc_type, session_type)
                except ServerError, why:
                    # Do not keep trying, since it rejected the
                    # association type that it told us to use.
                    oidutil.log('Server %s refused its suggested association '
                                'type: session_type=%s, assoc_type=%s'
                                % (endpoint.server_url, session_type,
                                   assoc_type))
                    return None
                else:
                    return assoc
        else:
            return assoc

    def _extractSupportedAssociationType(self, server_error, endpoint,
                                         assoc_type):
        """Handle ServerErrors resulting from association requests.

        @returns: If server replied with an C{unsupported-type} error,
            return a tuple of supported C{association_type}, C{session_type}.
            Otherwise logs the error and returns None.
        @rtype: tuple or None
        """
        # Any error message whose code is not 'unsupported-type'
        # should be considered a total failure.
        if server_error.error_code != 'unsupported-type' or \
               server_error.message.isOpenID1():
            oidutil.log(
                'Server error when requesting an association from %r: %s'
                % (endpoint.server_url, server_error.error_text))
            return None

        # The server didn't like the association/session type
        # that we sent, and it sent us back a message that
        # might tell us how to handle it.
        oidutil.log(
            'Unsupported association type %s: %s' % (assoc_type,
                                                     server_error.error_text,))

        # Extract the session_type and assoc_type from the
        # error message
        assoc_type = server_error.message.getArg(OPENID_NS, 'assoc_type')
        session_type = server_error.message.getArg(OPENID_NS, 'session_type')

        if assoc_type is None or session_type is None:
            oidutil.log('Server responded with unsupported association '
                        'session but did not supply a fallback.')
            return None
        elif not self.negotiator.isAllowed(assoc_type, session_type):
            fmt = ('Server sent unsupported session/association type: '
                   'session_type=%s, assoc_type=%s')
            oidutil.log(fmt % (session_type, assoc_type))
            return None
        else:
            return assoc_type, session_type


    def _requestAssociation(self, endpoint, assoc_type, session_type):
        """Make and process one association request to this endpoint's
        OP endpoint URL.

        @returns: An association object or None if the association
            processing failed.

        @raises ServerError: when the remote OpenID server returns an error.
        """
        assoc_session, args = self._createAssociateRequest(
            endpoint, assoc_type, session_type)

        try:
            response = self._makeKVPost(args, endpoint.server_url)
        except fetchers.HTTPFetchingError, why:
            oidutil.log('openid.associate request failed: %s' % (why[0],))
            return None

        try:
            assoc = self._extractAssociation(response, assoc_session)
        except KeyError, why:
            oidutil.log('Missing required parameter in response from %s: %s'
                        % (endpoint.server_url, why[0]))
            return None
        except ProtocolError, why:
            oidutil.log('Protocol error parsing response from %s: %s' % (
                endpoint.server_url, why[0]))
            return None
        else:
            return assoc

    def _createAssociateRequest(self, endpoint, assoc_type, session_type):
        """Create an association request for the given assoc_type and
        session_type.

        @param endpoint: The endpoint whose server_url will be
            queried. The important bit about the endpoint is whether
            it's in compatiblity mode (OpenID 1.1)

        @param assoc_type: The association type that the request
            should ask for.
        @type assoc_type: str

        @param session_type: The session type that should be used in
            the association request. The session_type is used to
            create an association session object, and that session
            object is asked for any additional fields that it needs to
            add to the request.
        @type session_type: str

        @returns: a pair of the association session object and the
            request message that will be sent to the server.
        @rtype: (association session type (depends on session_type),
                 openid.message.Message)
        """
        session_type_class = self.session_types[session_type]
        assoc_session = session_type_class()

        args = {
            'mode': 'associate',
            'assoc_type': assoc_type,
            }

        if not endpoint.compatibilityMode():
            args['ns'] = OPENID2_NS

        # Leave out the session type if we're in compatibility mode
        # *and* it's no-encryption.
        if (not endpoint.compatibilityMode() or
            assoc_session.session_type != 'no-encryption'):
            args['session_type'] = assoc_session.session_type

        args.update(assoc_session.getRequest())
        message = Message.fromOpenIDArgs(args)
        return assoc_session, message

    def _getOpenID1SessionType(self, assoc_response):
        """Given an association response message, extract the OpenID
        1.X session type.

        This function mostly takes care of the 'no-encryption' default
        behavior in OpenID 1.

        If the association type is plain-text, this function will
        return 'no-encryption'

        @returns: The association type for this message
        @rtype: str

        @raises KeyError: when the session_type field is absent.
        """
        # If it's an OpenID 1 message, allow session_type to default
        # to None (which signifies "no-encryption")
        session_type = assoc_response.getArg(OPENID1_NS, 'session_type')

        # Handle the differences between no-encryption association
        # respones in OpenID 1 and 2:

        # no-encryption is not really a valid session type for
        # OpenID 1, but we'll accept it anyway, while issuing a
        # warning.
        if session_type == 'no-encryption':
            oidutil.log('WARNING: OpenID server sent "no-encryption"'
                        'for OpenID 1.X')

        # Missing or empty session type is the way to flag a
        # 'no-encryption' response. Change the session type to
        # 'no-encryption' so that it can be handled in the same
        # way as OpenID 2 'no-encryption' respones.
        elif session_type == '' or session_type is None:
            session_type = 'no-encryption'

        return session_type

    def _extractAssociation(self, assoc_response, assoc_session):
        """Attempt to extract an association from the response, given
        the association response message and the established
        association session.

        @param assoc_response: The association response message from
            the server
        @type assoc_response: openid.message.Message

        @param assoc_session: The association session object that was
            used when making the request
        @type assoc_session: depends on the session type of the request

        @raises ProtocolError: when data is malformed
        @raises KeyError: when a field is missing

        @rtype: openid.association.Association
        """
        # Extract the common fields from the response, raising an
        # exception if they are not found
        assoc_type = assoc_response.getArg(
            OPENID_NS, 'assoc_type', no_default)
        assoc_handle = assoc_response.getArg(
            OPENID_NS, 'assoc_handle', no_default)

        # expires_in is a base-10 string. The Python parsing will
        # accept literals that have whitespace around them and will
        # accept negative values. Neither of these are really in-spec,
        # but we think it's OK to accept them.
        expires_in_str = assoc_response.getArg(
            OPENID_NS, 'expires_in', no_default)
        try:
            expires_in = int(expires_in_str)
        except ValueError, why:
            raise ProtocolError('Invalid expires_in field: %s' % (why[0],))

        # OpenID 1 has funny association session behaviour.
        if assoc_response.isOpenID1():
            session_type = self._getOpenID1SessionType(assoc_response)
        else:
            session_type = assoc_response.getArg(
                OPENID2_NS, 'session_type', no_default)

        # Session type mismatch
        if assoc_session.session_type != session_type:
            if (assoc_response.isOpenID1() and
                session_type == 'no-encryption'):
                # In OpenID 1, any association request can result in a
                # 'no-encryption' association response. Setting
                # assoc_session to a new no-encryption session should
                # make the rest of this function work properly for
                # that case.
                assoc_session = PlainTextConsumerSession()
            else:
                # Any other mismatch, regardless of protocol version
                # results in the failure of the association session
                # altogether.
                fmt = 'Session type mismatch. Expected %r, got %r'
                message = fmt % (assoc_session.session_type, session_type)
                raise ProtocolError(message)

        # Make sure assoc_type is valid for session_type
        if assoc_type not in assoc_session.allowed_assoc_types:
            fmt = 'Unsupported assoc_type for session %s returned: %s'
            raise ProtocolError(fmt % (assoc_session.session_type, assoc_type))

        # Delegate to the association session to extract the secret
        # from the response, however is appropriate for that session
        # type.
        try:
            secret = assoc_session.extractSecret(assoc_response)
        except ValueError, why:
            fmt = 'Malformed response for %s session: %s'
            raise ProtocolError(fmt % (assoc_session.session_type, why[0]))

        return Association.fromExpiresIn(
            expires_in, assoc_handle, secret, assoc_type)

class AuthRequest(object):
    """An object that holds the state necessary for generating an
    OpenID authentication request. This object holds the association
    with the server and the discovered information with which the
    request will be made.

    It is separate from the consumer because you may wish to add
    things to the request before sending it on its way to the
    server. It also has serialization options that let you encode the
    authentication request as a URL or as a form POST.
    """

    def __init__(self, endpoint, assoc):
        """
        Creates a new AuthRequest object.  This just stores each
        argument in an appropriately named field.

        Users of this library should not create instances of this
        class.  Instances of this class are created by the library
        when needed.
        """
        self.assoc = assoc
        self.endpoint = endpoint
        self.return_to_args = {}
        self.message = Message()
        self.message.setOpenIDNamespace(endpoint.preferredNamespace())
        self._anonymous = False

    def setAnonymous(self, is_anonymous):
        """Set whether this request should be made anonymously. If a
        request is anonymous, the identifier will not be sent in the
        request. This is only useful if you are making another kind of
        request with an extension in this request.

        Anonymous requests are not allowed when the request is made
        with OpenID 1.

        @raises ValueError: when attempting to set an OpenID1 request
            as anonymous
        """
        if is_anonymous and self.message.isOpenID1():
            raise ValueError('OpenID 1 requests MUST include the '
                             'identifier in the request')
        else:
            self._anonymous = is_anonymous

    def addExtension(self, extension_request):
        """Add an extension to this checkid request.

        @param extension_request: An object that implements the
            extension interface for adding arguments to an OpenID
            message.
        """
        extension_request.toMessage(self.message)

    def addExtensionArg(self, namespace, key, value):
        """Add an extension argument to this OpenID authentication
        request.

        Use caution when adding arguments, because they will be
        URL-escaped and appended to the redirect URL, which can easily
        get quite long.

        @param namespace: The namespace for the extension. For
            example, the simple registration extension uses the
            namespace C{sreg}.

        @type namespace: str

        @param key: The key within the extension namespace. For
            example, the nickname field in the simple registration
            extension's key is C{nickname}.

        @type key: str

        @param value: The value to provide to the server for this
            argument.

        @type value: str
        """
        self.message.setArg(namespace, key, value)

    def getMessage(self, realm, return_to=None, immediate=False):
        """Produce a L{openid.message.Message} representing this request.

        @param realm: The URL (or URL pattern) that identifies your
            web site to the user when she is authorizing it.

        @type realm: str

        @param return_to: The URL that the OpenID provider will send the
            user back to after attempting to verify her identity.

            Not specifying a return_to URL means that the user will not
            be returned to the site issuing the request upon its
            completion.

        @type return_to: str

        @param immediate: If True, the OpenID provider is to send back
            a response immediately, useful for behind-the-scenes
            authentication attempts.  Otherwise the OpenID provider
            may engage the user before providing a response.  This is
            the default case, as the user may need to provide
            credentials or approve the request before a positive
            response can be sent.

        @type immediate: bool

        @returntype: L{openid.message.Message}
        """
        if return_to:
            return_to = oidutil.appendArgs(return_to, self.return_to_args)
        elif immediate:
            raise ValueError(
                '"return_to" is mandatory when using "checkid_immediate"')
        elif self.message.isOpenID1():
            raise ValueError('"return_to" is mandatory for OpenID 1 requests')
        elif self.return_to_args:
            raise ValueError('extra "return_to" arguments were specified, '
                             'but no return_to was specified')

        if immediate:
            mode = 'checkid_immediate'
        else:
            mode = 'checkid_setup'

        message = self.message.copy()
        if message.isOpenID1():
            realm_key = 'trust_root'
        else:
            realm_key = 'realm'

        message.updateArgs(OPENID_NS,
            {
            realm_key:realm,
            'mode':mode,
            'return_to':return_to,
            })

        if not self._anonymous:
            if self.endpoint.isOPIdentifier():
                # This will never happen when we're in compatibility
                # mode, as long as isOPIdentifier() returns False
                # whenever preferredNamespace() returns OPENID1_NS.
                claimed_id = request_identity = IDENTIFIER_SELECT
            else:
                request_identity = self.endpoint.getLocalID()
                claimed_id = self.endpoint.claimed_id

            # This is true for both OpenID 1 and 2
            message.setArg(OPENID_NS, 'identity', request_identity)

            if message.isOpenID2():
                message.setArg(OPENID2_NS, 'claimed_id', claimed_id)

        if self.assoc:
            message.setArg(OPENID_NS, 'assoc_handle', self.assoc.handle)
            assoc_log_msg = 'with assocication %s' % (self.assoc.handle,)
        else:
            assoc_log_msg = 'using stateless mode.'

        oidutil.log("Generated %s request to %s %s" %
                    (mode, self.endpoint.server_url, assoc_log_msg))

        return message

    def redirectURL(self, realm, return_to=None, immediate=False):
        """Returns a URL with an encoded OpenID request.

        The resulting URL is the OpenID provider's endpoint URL with
        parameters appended as query arguments.  You should redirect
        the user agent to this URL.

        OpenID 2.0 endpoints also accept POST requests, see
        C{L{shouldSendRedirect}} and C{L{formMarkup}}.

        @param realm: The URL (or URL pattern) that identifies your
            web site to the user when she is authorizing it.

        @type realm: str

        @param return_to: The URL that the OpenID provider will send the
            user back to after attempting to verify her identity.

            Not specifying a return_to URL means that the user will not
            be returned to the site issuing the request upon its
            completion.

        @type return_to: str

        @param immediate: If True, the OpenID provider is to send back
            a response immediately, useful for behind-the-scenes
            authentication attempts.  Otherwise the OpenID provider
            may engage the user before providing a response.  This is
            the default case, as the user may need to provide
            credentials or approve the request before a positive
            response can be sent.

        @type immediate: bool

        @returns: The URL to redirect the user agent to.

        @returntype: str
        """
        message = self.getMessage(realm, return_to, immediate)
        return message.toURL(self.endpoint.server_url)

    def formMarkup(self, realm, return_to=None, immediate=False,
            form_tag_attrs=None):
        """Get html for a form to submit this request to the IDP.

        @param form_tag_attrs: Dictionary of attributes to be added to
            the form tag. 'accept-charset' and 'enctype' have defaults
            that can be overridden. If a value is supplied for
            'action' or 'method', it will be replaced.
        @type form_tag_attrs: {unicode: unicode}
        """
        message = self.getMessage(realm, return_to, immediate)
        return message.toFormMarkup(self.endpoint.server_url,
                    form_tag_attrs)

    def shouldSendRedirect(self):
        """Should this OpenID authentication request be sent as a HTTP
        redirect or as a POST (form submission)?

        @rtype: bool
        """
        return self.endpoint.compatibilityMode()

FAILURE = 'failure'
SUCCESS = 'success'
CANCEL = 'cancel'
SETUP_NEEDED = 'setup_needed'

class Response(object):
    status = None

    def setEndpoint(self, endpoint):
        self.endpoint = endpoint
        if endpoint is None:
            self.identity_url = None
        else:
            self.identity_url = endpoint.claimed_id

    def getDisplayIdentifier(self):
        """Return the display identifier for this response.
        """
        if self.endpoint is not None:
            return self.endpoint.getDisplayIdentifier()
        return None

class SuccessResponse(Response):
    """A response with a status of SUCCESS. Indicates that this request is a
    successful acknowledgement from the OpenID server that the
    supplied URL is, indeed controlled by the requesting agent.

    @ivar identity_url: The identity URL that has been authenticated

    @ivar endpoint: The endpoint that authenticated the identifier.  You
        may access other discovered information related to this endpoint,
        such as the CanonicalID of an XRI, through this object.
    @type endpoint: L{OpenIDServiceEndpoint<openid.consumer.discover.OpenIDServiceEndpoint>}

    @ivar signed_fields: The arguments in the server's response that
        were signed and verified.

    @cvar status: SUCCESS
    """

    status = SUCCESS

    def __init__(self, endpoint, message, signed_fields=None):
        # Don't use setEndpoint, because endpoint should never be None
        # for a successfull transaction.
        self.endpoint = endpoint
        self.identity_url = endpoint.claimed_id

        self.message = message

        if signed_fields is None:
            signed_fields = []
        self.signed_fields = signed_fields

    def isOpenID1(self):
        """Was this authentication response an OpenID 1 authentication
        response?
        """
        return self.message.isOpenID1()

    def isSigned(self, ns_uri, ns_key):
        """Return whether a particular key is signed, regardless of
        its namespace alias
        """
        return self.message.getKey(ns_uri, ns_key) in self.signed_fields

    def getSigned(self, ns_uri, ns_key, default=None):
        """Return the specified signed field if available,
        otherwise return default
        """
        if self.isSigned(ns_uri, ns_key):
            return self.message.getArg(ns_uri, ns_key, default)
        else:
            return default

    def getSignedNS(self, ns_uri):
        """Get signed arguments from the response message.  Return a
        dict of all arguments in the specified namespace.  If any of
        the arguments are not signed, return None.
        """
        msg_args = self.message.getArgs(ns_uri)

        for key in msg_args.iterkeys():
            if not self.isSigned(ns_uri, key):
                oidutil.log("SuccessResponse.getSignedNS: (%s, %s) not signed."
                            % (ns_uri, key))
                return None

        return msg_args

    def extensionResponse(self, namespace_uri, require_signed):
        """Return response arguments in the specified namespace.

        @param namespace_uri: The namespace URI of the arguments to be
        returned.

        @param require_signed: True if the arguments should be among
        those signed in the response, False if you don't care.

        If require_signed is True and the arguments are not signed,
        return None.
        """
        if require_signed:
            return self.getSignedNS(namespace_uri)
        else:
            return self.message.getArgs(namespace_uri)

    def getReturnTo(self):
        """Get the openid.return_to argument from this response.

        This is useful for verifying that this request was initiated
        by this consumer.

        @returns: The return_to URL supplied to the server on the
            initial request, or C{None} if the response did not contain
            an C{openid.return_to} argument.

        @returntype: str
        """
        return self.getSigned(OPENID_NS, 'return_to')

    def __eq__(self, other):
        return (
            (self.endpoint == other.endpoint) and
            (self.identity_url == other.identity_url) and
            (self.message == other.message) and
            (self.signed_fields == other.signed_fields) and
            (self.status == other.status))

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return '<%s.%s id=%r signed=%r>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.identity_url, self.signed_fields)


class FailureResponse(Response):
    """A response with a status of FAILURE. Indicates that the OpenID
    protocol has failed. This could be locally or remotely triggered.

    @ivar identity_url:  The identity URL for which authenitcation was
        attempted, if it can be determined. Otherwise, None.

    @ivar message: A message indicating why the request failed, if one
        is supplied. otherwise, None.

    @cvar status: FAILURE
    """

    status = FAILURE

    def __init__(self, endpoint, message=None, contact=None,
                 reference=None):
        self.setEndpoint(endpoint)
        self.message = message
        self.contact = contact
        self.reference = reference

    def __repr__(self):
        return "<%s.%s id=%r message=%r>" % (
            self.__class__.__module__, self.__class__.__name__,
            self.identity_url, self.message)


class CancelResponse(Response):
    """A response with a status of CANCEL. Indicates that the user
    cancelled the OpenID authentication request.

    @ivar identity_url: The identity URL for which authenitcation was
        attempted, if it can be determined. Otherwise, None.

    @cvar status: CANCEL
    """

    status = CANCEL

    def __init__(self, endpoint):
        self.setEndpoint(endpoint)

class SetupNeededResponse(Response):
    """A response with a status of SETUP_NEEDED. Indicates that the
    request was in immediate mode, and the server is unable to
    authenticate the user without further interaction.

    @ivar identity_url:  The identity URL for which authenitcation was
        attempted.

    @ivar setup_url: A URL that can be used to send the user to the
        server to set up for authentication. The user should be
        redirected in to the setup_url, either in the current window
        or in a new browser window.  C{None} in OpenID 2.0.

    @cvar status: SETUP_NEEDED
    """

    status = SETUP_NEEDED

    def __init__(self, endpoint, setup_url=None):
        self.setEndpoint(endpoint)
        self.setup_url = setup_url

########NEW FILE########
__FILENAME__ = discover
# -*- test-case-name: openid.test.test_discover -*-
"""Functions to discover OpenID endpoints from identifiers.
"""

__all__ = [
    'DiscoveryFailure',
    'OPENID_1_0_NS',
    'OPENID_1_0_TYPE',
    'OPENID_1_1_TYPE',
    'OPENID_2_0_TYPE',
    'OPENID_IDP_2_0_TYPE',
    'OpenIDServiceEndpoint',
    'discover',
    ]

import urlparse

from openid import oidutil, fetchers, urinorm

from openid import yadis
from openid.yadis.etxrd import nsTag, XRDSError, XRD_NS_2_0
from openid.yadis.services import applyFilter as extractServices
from openid.yadis.discover import discover as yadisDiscover
from openid.yadis.discover import DiscoveryFailure
from openid.yadis import xrires, filters
from openid.yadis import xri

from openid.consumer import html_parse

OPENID_1_0_NS = 'http://openid.net/xmlns/1.0'
OPENID_IDP_2_0_TYPE = 'http://specs.openid.net/auth/2.0/server'
OPENID_2_0_TYPE = 'http://specs.openid.net/auth/2.0/signon'
OPENID_1_1_TYPE = 'http://openid.net/signon/1.1'
OPENID_1_0_TYPE = 'http://openid.net/signon/1.0'

from openid.message import OPENID1_NS as OPENID_1_0_MESSAGE_NS
from openid.message import OPENID2_NS as OPENID_2_0_MESSAGE_NS

class OpenIDServiceEndpoint(object):
    """Object representing an OpenID service endpoint.

    @ivar identity_url: the verified identifier.
    @ivar canonicalID: For XRI, the persistent identifier.
    """

    # OpenID service type URIs, listed in order of preference.  The
    # ordering of this list affects yadis and XRI service discovery.
    openid_type_uris = [
        OPENID_IDP_2_0_TYPE,

        OPENID_2_0_TYPE,
        OPENID_1_1_TYPE,
        OPENID_1_0_TYPE,
        ]

    def __init__(self):
        self.claimed_id = None
        self.server_url = None
        self.type_uris = []
        self.local_id = None
        self.canonicalID = None
        self.used_yadis = False # whether this came from an XRDS
        self.display_identifier = None

    def usesExtension(self, extension_uri):
        return extension_uri in self.type_uris

    def preferredNamespace(self):
        if (OPENID_IDP_2_0_TYPE in self.type_uris or
            OPENID_2_0_TYPE in self.type_uris):
            return OPENID_2_0_MESSAGE_NS
        else:
            return OPENID_1_0_MESSAGE_NS

    def supportsType(self, type_uri):
        """Does this endpoint support this type?

        I consider C{/server} endpoints to implicitly support C{/signon}.
        """
        return (
            (type_uri in self.type_uris) or 
            (type_uri == OPENID_2_0_TYPE and self.isOPIdentifier())
            )

    def getDisplayIdentifier(self):
        """Return the display_identifier if set, else return the claimed_id.
        """
        if self.display_identifier is None:
            return self.claimed_id
        return self.display_identifier

    def compatibilityMode(self):
        return self.preferredNamespace() != OPENID_2_0_MESSAGE_NS

    def isOPIdentifier(self):
        return OPENID_IDP_2_0_TYPE in self.type_uris

    def parseService(self, yadis_url, uri, type_uris, service_element):
        """Set the state of this object based on the contents of the
        service element."""
        self.type_uris = type_uris
        self.server_url = uri
        self.used_yadis = True

        if not self.isOPIdentifier():
            # XXX: This has crappy implications for Service elements
            # that contain both 'server' and 'signon' Types.  But
            # that's a pathological configuration anyway, so I don't
            # think I care.
            self.local_id = findOPLocalIdentifier(service_element,
                                                  self.type_uris)
            self.claimed_id = yadis_url

    def getLocalID(self):
        """Return the identifier that should be sent as the
        openid.identity parameter to the server."""
        # I looked at this conditional and thought "ah-hah! there's the bug!"
        # but Python actually makes that one big expression somehow, i.e.
        # "x is x is x" is not the same thing as "(x is x) is x".
        # That's pretty weird, dude.  -- kmt, 1/07
        if (self.local_id is self.canonicalID is None):
            return self.claimed_id
        else:
            return self.local_id or self.canonicalID

    def fromBasicServiceEndpoint(cls, endpoint):
        """Create a new instance of this class from the endpoint
        object passed in.

        @return: None or OpenIDServiceEndpoint for this endpoint object"""
        type_uris = endpoint.matchTypes(cls.openid_type_uris)

        # If any Type URIs match and there is an endpoint URI
        # specified, then this is an OpenID endpoint
        if type_uris and endpoint.uri is not None:
            openid_endpoint = cls()
            openid_endpoint.parseService(
                endpoint.yadis_url,
                endpoint.uri,
                endpoint.type_uris,
                endpoint.service_element)
        else:
            openid_endpoint = None

        return openid_endpoint

    fromBasicServiceEndpoint = classmethod(fromBasicServiceEndpoint)

    def fromHTML(cls, uri, html):
        """Parse the given document as HTML looking for an OpenID <link
        rel=...>

        @rtype: [OpenIDServiceEndpoint]
        """
        discovery_types = [
            (OPENID_2_0_TYPE, 'openid2.provider', 'openid2.local_id'),
            (OPENID_1_1_TYPE, 'openid.server', 'openid.delegate'),
            ]

        link_attrs = html_parse.parseLinkAttrs(html)
        services = []
        for type_uri, op_endpoint_rel, local_id_rel in discovery_types:
            op_endpoint_url = html_parse.findFirstHref(
                link_attrs, op_endpoint_rel)
            if op_endpoint_url is None:
                continue

            service = cls()
            service.claimed_id = uri
            service.local_id = html_parse.findFirstHref(
                link_attrs, local_id_rel)
            service.server_url = op_endpoint_url
            service.type_uris = [type_uri]

            services.append(service)

        return services

    fromHTML = classmethod(fromHTML)


    def fromXRDS(cls, uri, xrds):
        """Parse the given document as XRDS looking for OpenID services.

        @rtype: [OpenIDServiceEndpoint]

        @raises XRDSError: When the XRDS does not parse.

        @since: 2.1.0
        """
        return extractServices(uri, xrds, cls)

    fromXRDS = classmethod(fromXRDS)


    def fromDiscoveryResult(cls, discoveryResult):
        """Create endpoints from a DiscoveryResult.

        @type discoveryResult: L{DiscoveryResult}

        @rtype: list of L{OpenIDServiceEndpoint}

        @raises XRDSError: When the XRDS does not parse.

        @since: 2.1.0
        """
        if discoveryResult.isXRDS():
            method = cls.fromXRDS
        else:
            method = cls.fromHTML
        return method(discoveryResult.normalized_uri,
                      discoveryResult.response_text)

    fromDiscoveryResult = classmethod(fromDiscoveryResult)


    def fromOPEndpointURL(cls, op_endpoint_url):
        """Construct an OP-Identifier OpenIDServiceEndpoint object for
        a given OP Endpoint URL

        @param op_endpoint_url: The URL of the endpoint
        @rtype: OpenIDServiceEndpoint
        """
        service = cls()
        service.server_url = op_endpoint_url
        service.type_uris = [OPENID_IDP_2_0_TYPE]
        return service

    fromOPEndpointURL = classmethod(fromOPEndpointURL)


    def __str__(self):
        return ("<%s.%s "
                "server_url=%r "
                "claimed_id=%r "
                "local_id=%r "
                "canonicalID=%r "
                "used_yadis=%s "
                ">"
                 % (self.__class__.__module__, self.__class__.__name__,
                    self.server_url,
                    self.claimed_id,
                    self.local_id,
                    self.canonicalID,
                    self.used_yadis))



def findOPLocalIdentifier(service_element, type_uris):
    """Find the OP-Local Identifier for this xrd:Service element.

    This considers openid:Delegate to be a synonym for xrd:LocalID if
    both OpenID 1.X and OpenID 2.0 types are present. If only OpenID
    1.X is present, it returns the value of openid:Delegate. If only
    OpenID 2.0 is present, it returns the value of xrd:LocalID. If
    there is more than one LocalID tag and the values are different,
    it raises a DiscoveryFailure. This is also triggered when the
    xrd:LocalID and openid:Delegate tags are different.

    @param service_element: The xrd:Service element
    @type service_element: ElementTree.Node

    @param type_uris: The xrd:Type values present in this service
        element. This function could extract them, but higher level
        code needs to do that anyway.
    @type type_uris: [str]

    @raises DiscoveryFailure: when discovery fails.

    @returns: The OP-Local Identifier for this service element, if one
        is present, or None otherwise.
    @rtype: str or unicode or NoneType
    """
    # XXX: Test this function on its own!

    # Build the list of tags that could contain the OP-Local Identifier
    local_id_tags = []
    if (OPENID_1_1_TYPE in type_uris or
        OPENID_1_0_TYPE in type_uris):
        local_id_tags.append(nsTag(OPENID_1_0_NS, 'Delegate'))

    if OPENID_2_0_TYPE in type_uris:
        local_id_tags.append(nsTag(XRD_NS_2_0, 'LocalID'))

    # Walk through all the matching tags and make sure that they all
    # have the same value
    local_id = None
    for local_id_tag in local_id_tags:
        for local_id_element in service_element.findall(local_id_tag):
            if local_id is None:
                local_id = local_id_element.text
            elif local_id != local_id_element.text:
                format = 'More than one %r tag found in one service element'
                message = format % (local_id_tag,)
                raise DiscoveryFailure(message, None)

    return local_id

def normalizeURL(url):
    """Normalize a URL, converting normalization failures to
    DiscoveryFailure"""
    try:
        normalized = urinorm.urinorm(url)
    except ValueError, why:
        raise DiscoveryFailure('Normalizing identifier: %s' % (why[0],), None)
    else:
        return urlparse.urldefrag(normalized)[0]

def arrangeByType(service_list, preferred_types):
    """Rearrange service_list in a new list so services are ordered by
    types listed in preferred_types.  Return the new list."""

    def enumerate(elts):
        """Return an iterable that pairs the index of an element with
        that element.

        For Python 2.2 compatibility"""
        return zip(range(len(elts)), elts)

    def bestMatchingService(service):
        """Return the index of the first matching type, or something
        higher if no type matches.

        This provides an ordering in which service elements that
        contain a type that comes earlier in the preferred types list
        come before service elements that come later. If a service
        element has more than one type, the most preferred one wins.
        """
        for i, t in enumerate(preferred_types):
            if preferred_types[i] in service.type_uris:
                return i

        return len(preferred_types)

    # Build a list with the service elements in tuples whose
    # comparison will prefer the one with the best matching service
    prio_services = [(bestMatchingService(s), orig_index, s)
                     for (orig_index, s) in enumerate(service_list)]
    prio_services.sort()

    # Now that the services are sorted by priority, remove the sort
    # keys from the list.
    for i in range(len(prio_services)):
        prio_services[i] = prio_services[i][2]

    return prio_services

def getOPOrUserServices(openid_services):
    """Extract OP Identifier services.  If none found, return the
    rest, sorted with most preferred first according to
    OpenIDServiceEndpoint.openid_type_uris.

    openid_services is a list of OpenIDServiceEndpoint objects.

    Returns a list of OpenIDServiceEndpoint objects."""

    op_services = arrangeByType(openid_services, [OPENID_IDP_2_0_TYPE])

    openid_services = arrangeByType(openid_services,
                                    OpenIDServiceEndpoint.openid_type_uris)

    return op_services or openid_services

def discoverYadis(uri):
    """Discover OpenID services for a URI. Tries Yadis and falls back
    on old-style <link rel='...'> discovery if Yadis fails.

    @param uri: normalized identity URL
    @type uri: str

    @return: (claimed_id, services)
    @rtype: (str, list(OpenIDServiceEndpoint))

    @raises DiscoveryFailure: when discovery fails.
    """
    # Might raise a yadis.discover.DiscoveryFailure if no document
    # came back for that URI at all.  I don't think falling back
    # to OpenID 1.0 discovery on the same URL will help, so don't
    # bother to catch it.
    response = yadisDiscover(uri)

    yadis_url = response.normalized_uri
    body = response.response_text
    try:
        openid_services = OpenIDServiceEndpoint.fromXRDS(yadis_url, body)
    except XRDSError:
        # Does not parse as a Yadis XRDS file
        openid_services = []

    if not openid_services:
        # Either not an XRDS or there are no OpenID services.

        if response.isXRDS():
            # if we got the Yadis content-type or followed the Yadis
            # header, re-fetch the document without following the Yadis
            # header, with no Accept header.
            return discoverNoYadis(uri)

        # Try to parse the response as HTML.
        # <link rel="...">
        openid_services = OpenIDServiceEndpoint.fromHTML(yadis_url, body)

    return (yadis_url, getOPOrUserServices(openid_services))

def discoverXRI(iname):
    endpoints = []
    try:
        canonicalID, services = xrires.ProxyResolver().query(
            iname, OpenIDServiceEndpoint.openid_type_uris)

        if canonicalID is None:
            raise XRDSError('No CanonicalID found for XRI %r' % (iname,))

        flt = filters.mkFilter(OpenIDServiceEndpoint)
        for service_element in services:
            endpoints.extend(flt.getServiceEndpoints(iname, service_element))
    except XRDSError:
        oidutil.log('xrds error on ' + iname)

    for endpoint in endpoints:
        # Is there a way to pass this through the filter to the endpoint
        # constructor instead of tacking it on after?
        endpoint.canonicalID = canonicalID
        endpoint.claimed_id = canonicalID
        endpoint.display_identifier = iname

    # FIXME: returned xri should probably be in some normal form
    return iname, getOPOrUserServices(endpoints)


def discoverNoYadis(uri):
    http_resp = fetchers.fetch(uri)
    if http_resp.status != 200:
        raise DiscoveryFailure(
            'HTTP Response status from identity URL host is not 200. '
            'Got status %r' % (http_resp.status,), http_resp)

    claimed_id = http_resp.final_url
    openid_services = OpenIDServiceEndpoint.fromHTML(
        claimed_id, http_resp.body)
    return claimed_id, openid_services

def discoverURI(uri):
    parsed = urlparse.urlparse(uri)
    if parsed[0] and parsed[1]:
        if parsed[0] not in ['http', 'https']:
            raise DiscoveryFailure('URI scheme is not HTTP or HTTPS', None)
    else:
        uri = 'http://' + uri

    uri = normalizeURL(uri)
    claimed_id, openid_services = discoverYadis(uri)
    claimed_id = normalizeURL(claimed_id)
    return claimed_id, openid_services

def discover(identifier):
    if xri.identifierScheme(identifier) == "XRI":
        return discoverXRI(identifier)
    else:
        return discoverURI(identifier)

########NEW FILE########
__FILENAME__ = html_parse
"""
This module implements a VERY limited parser that finds <link> tags in
the head of HTML or XHTML documents and parses out their attributes
according to the OpenID spec. It is a liberal parser, but it requires
these things from the data in order to work:

 - There must be an open <html> tag

 - There must be an open <head> tag inside of the <html> tag

 - Only <link>s that are found inside of the <head> tag are parsed
   (this is by design)

 - The parser follows the OpenID specification in resolving the
   attributes of the link tags. This means that the attributes DO NOT
   get resolved as they would by an XML or HTML parser. In particular,
   only certain entities get replaced, and href attributes do not get
   resolved relative to a base URL.

From http://openid.net/specs.bml#linkrel:

 - The openid.server URL MUST be an absolute URL. OpenID consumers
   MUST NOT attempt to resolve relative URLs.

 - The openid.server URL MUST NOT include entities other than &amp;,
   &lt;, &gt;, and &quot;.

The parser ignores SGML comments and <![CDATA[blocks]]>. Both kinds of
quoting are allowed for attributes.

The parser deals with invalid markup in these ways:

 - Tag names are not case-sensitive

 - The <html> tag is accepted even when it is not at the top level

 - The <head> tag is accepted even when it is not a direct child of
   the <html> tag, but a <html> tag must be an ancestor of the <head>
   tag

 - <link> tags are accepted even when they are not direct children of
   the <head> tag, but a <head> tag must be an ancestor of the <link>
   tag

 - If there is no closing tag for an open <html> or <head> tag, the
   remainder of the document is viewed as being inside of the tag. If
   there is no closing tag for a <link> tag, the link tag is treated
   as a short tag. Exceptions to this rule are that <html> closes
   <html> and <body> or <head> closes <head>

 - Attributes of the <link> tag are not required to be quoted.

 - In the case of duplicated attribute names, the attribute coming
   last in the tag will be the value returned.

 - Any text that does not parse as an attribute within a link tag will
   be ignored. (e.g. <link pumpkin rel='openid.server' /> will ignore
   pumpkin)

 - If there are more than one <html> or <head> tag, the parser only
   looks inside of the first one.

 - The contents of <script> tags are ignored entirely, except unclosed
   <script> tags. Unclosed <script> tags are ignored.

 - Any other invalid markup is ignored, including unclosed SGML
   comments and unclosed <![CDATA[blocks.
"""

__all__ = ['parseLinkAttrs']

import re

flags = ( re.DOTALL # Match newlines with '.'
        | re.IGNORECASE
        | re.VERBOSE # Allow comments and whitespace in patterns
        | re.UNICODE # Make \b respect Unicode word boundaries
        )

# Stuff to remove before we start looking for tags
removed_re = re.compile(r'''
  # Comments
  <!--.*?-->

  # CDATA blocks
| <!\[CDATA\[.*?\]\]>

  # script blocks
| <script\b

  # make sure script is not an XML namespace
  (?!:)

  [^>]*>.*?</script>

''', flags)

tag_expr = r'''
# Starts with the tag name at a word boundary, where the tag name is
# not a namespace
<%(tag_name)s\b(?!:)

# All of the stuff up to a ">", hopefully attributes.
(?P<attrs>[^>]*?)

(?: # Match a short tag
    />

|   # Match a full tag
    >

    (?P<contents>.*?)

    # Closed by
    (?: # One of the specified close tags
        </?%(closers)s\s*>

        # End of the string
    |   \Z

    )

)
'''

def tagMatcher(tag_name, *close_tags):
    if close_tags:
        options = '|'.join((tag_name,) + close_tags)
        closers = '(?:%s)' % (options,)
    else:
        closers = tag_name

    expr = tag_expr % locals()
    return re.compile(expr, flags)

# Must contain at least an open html and an open head tag
html_find = tagMatcher('html')
head_find = tagMatcher('head', 'body')
link_find = re.compile(r'<link\b(?!:)', flags)

attr_find = re.compile(r'''
# Must start with a sequence of word-characters, followed by an equals sign
(?P<attr_name>\w+)=

# Then either a quoted or unquoted attribute
(?:

 # Match everything that\'s between matching quote marks
 (?P<qopen>["\'])(?P<q_val>.*?)(?P=qopen)
|

 # If the value is not quoted, match up to whitespace
 (?P<unq_val>(?:[^\s<>/]|/(?!>))+)
)

|

(?P<end_link>[<>])
''', flags)

# Entity replacement:
replacements = {
    'amp':'&',
    'lt':'<',
    'gt':'>',
    'quot':'"',
    }

ent_replace = re.compile(r'&(%s);' % '|'.join(replacements.keys()))
def replaceEnt(mo):
    "Replace the entities that are specified by OpenID"
    return replacements.get(mo.group(1), mo.group())

def parseLinkAttrs(html):
    """Find all link tags in a string representing a HTML document and
    return a list of their attributes.

    @param html: the text to parse
    @type html: str or unicode

    @return: A list of dictionaries of attributes, one for each link tag
    @rtype: [[(type(html), type(html))]]
    """
    stripped = removed_re.sub('', html)
    html_mo = html_find.search(stripped)
    if html_mo is None or html_mo.start('contents') == -1:
        return []

    start, end = html_mo.span('contents')
    head_mo = head_find.search(stripped, start, end)
    if head_mo is None or head_mo.start('contents') == -1:
        return []

    start, end = head_mo.span('contents')
    link_mos = link_find.finditer(stripped, head_mo.start(), head_mo.end())

    matches = []
    for link_mo in link_mos:
        start = link_mo.start() + 5
        link_attrs = {}
        for attr_mo in attr_find.finditer(stripped, start):
            if attr_mo.lastgroup == 'end_link':
                break

            # Either q_val or unq_val must be present, but not both
            # unq_val is a True (non-empty) value if it is present
            attr_name, q_val, unq_val = attr_mo.group(
                'attr_name', 'q_val', 'unq_val')
            attr_val = ent_replace.sub(replaceEnt, unq_val or q_val)

            link_attrs[attr_name] = attr_val

        matches.append(link_attrs)

    return matches

def relMatches(rel_attr, target_rel):
    """Does this target_rel appear in the rel_str?"""
    # XXX: TESTME
    rels = rel_attr.strip().split()
    for rel in rels:
        rel = rel.lower()
        if rel == target_rel:
            return 1

    return 0

def linkHasRel(link_attrs, target_rel):
    """Does this link have target_rel as a relationship?"""
    # XXX: TESTME
    rel_attr = link_attrs.get('rel')
    return rel_attr and relMatches(rel_attr, target_rel)

def findLinksRel(link_attrs_list, target_rel):
    """Filter the list of link attributes on whether it has target_rel
    as a relationship."""
    # XXX: TESTME
    matchesTarget = lambda attrs: linkHasRel(attrs, target_rel)
    return filter(matchesTarget, link_attrs_list)

def findFirstHref(link_attrs_list, target_rel):
    """Return the value of the href attribute for the first link tag
    in the list that has target_rel as a relationship."""
    # XXX: TESTME
    matches = findLinksRel(link_attrs_list, target_rel)
    if not matches:
        return None
    first = matches[0]
    return first.get('href')

########NEW FILE########
__FILENAME__ = cryptutil
"""Module containing a cryptographic-quality source of randomness and
other cryptographically useful functionality

Python 2.4 needs no external support for this module, nor does Python
2.3 on a system with /dev/urandom.

Other configurations will need a quality source of random bytes and
access to a function that will convert binary strings to long
integers. This module will work with the Python Cryptography Toolkit
(pycrypto) if it is present. pycrypto can be found with a search
engine, but is currently found at:

http://www.amk.ca/python/code/crypto
"""

__all__ = [
    'base64ToLong',
    'binaryToLong',
    'hmacSha1',
    'hmacSha256',
    'longToBase64',
    'longToBinary',
    'randomString',
    'randrange',
    'sha1',
    'sha256',
    ]

import hmac
import os
import random

from openid.oidutil import toBase64, fromBase64

try:
    import hashlib
except ImportError:
    import sha as sha1_module

    try:
        from Crypto.Hash import SHA256 as sha256_module
    except ImportError:
        sha256_module = None

else:
    class HashContainer(object):
        def __init__(self, hash_constructor):
            self.new = hash_constructor

    sha1_module = HashContainer(hashlib.sha1)
    sha256_module = HashContainer(hashlib.sha256)

def hmacSha1(key, text):
    return hmac.new(key, text, sha1_module).digest()

def sha1(s):
    return sha1_module.new(s).digest()

if sha256_module is not None:
    def hmacSha256(key, text):
        return hmac.new(key, text, sha256_module).digest()

    def sha256(s):
        return sha256_module.new(s).digest()

    SHA256_AVAILABLE = True

else:
    _no_sha256 = NotImplementedError(
        'Use Python 2.5, install pycrypto or install hashlib to use SHA256')

    def hmacSha256(unused_key, unused_text):
        raise _no_sha256

    def sha256(s):
        raise _no_sha256

    SHA256_AVAILABLE = False

try:
    from Crypto.Util.number import long_to_bytes, bytes_to_long
except ImportError:
    import pickle
    try:
        # Check Python compatiblity by raising an exception on import
        # if the needed functionality is not present. Present in
        # Python >= 2.3
        pickle.encode_long
        pickle.decode_long
    except AttributeError:
        raise ImportError(
            'No functionality for serializing long integers found')

    # Present in Python >= 2.4
    try:
        reversed
    except NameError:
        def reversed(seq):
            return map(seq.__getitem__, xrange(len(seq) - 1, -1, -1))

    def longToBinary(l):
        if l == 0:
            return '\x00'

        return ''.join(reversed(pickle.encode_long(l)))

    def binaryToLong(s):
        return pickle.decode_long(''.join(reversed(s)))
else:
    # We have pycrypto

    def longToBinary(l):
        if l < 0:
            raise ValueError('This function only supports positive integers')

        bytes = long_to_bytes(l)
        if ord(bytes[0]) > 127:
            return '\x00' + bytes
        else:
            return bytes

    def binaryToLong(bytes):
        if not bytes:
            raise ValueError('Empty string passed to strToLong')

        if ord(bytes[0]) > 127:
            raise ValueError('This function only supports positive integers')

        return bytes_to_long(bytes)

# A cryptographically safe source of random bytes
try:
    getBytes = os.urandom
except AttributeError:
    try:
        from Crypto.Util.randpool import RandomPool
    except ImportError:
        # Fall back on /dev/urandom, if present. It would be nice to
        # have Windows equivalent here, but for now, require pycrypto
        # on Windows.
        try:
            _urandom = file('/dev/urandom', 'rb')
        except IOError:
            raise ImportError('No adequate source of randomness found!')
        else:
            def getBytes(n):
                bytes = []
                while n:
                    chunk = _urandom.read(n)
                    n -= len(chunk)
                    bytes.append(chunk)
                    assert n >= 0
                return ''.join(bytes)
    else:
        _pool = RandomPool()
        def getBytes(n, pool=_pool):
            if pool.entropy < n:
                pool.randomize()
            return pool.get_bytes(n)

# A randrange function that works for longs
try:
    randrange = random.SystemRandom().randrange
except AttributeError:
    # In Python 2.2's random.Random, randrange does not support
    # numbers larger than sys.maxint for randrange. For simplicity,
    # use this implementation for any Python that does not have
    # random.SystemRandom
    from math import log, ceil

    _duplicate_cache = {}
    def randrange(start, stop=None, step=1):
        if stop is None:
            stop = start
            start = 0

        r = (stop - start) // step
        try:
            (duplicate, nbytes) = _duplicate_cache[r]
        except KeyError:
            rbytes = longToBinary(r)
            if rbytes[0] == '\x00':
                nbytes = len(rbytes) - 1
            else:
                nbytes = len(rbytes)

            mxrand = (256 ** nbytes)

            # If we get a number less than this, then it is in the
            # duplicated range.
            duplicate = mxrand % r

            if len(_duplicate_cache) > 10:
                _duplicate_cache.clear()

            _duplicate_cache[r] = (duplicate, nbytes)

        while 1:
            bytes = '\x00' + getBytes(nbytes)
            n = binaryToLong(bytes)
            # Keep looping if this value is in the low duplicated range
            if n >= duplicate:
                break

        return start + (n % r) * step

def longToBase64(l):
    return toBase64(longToBinary(l))

def base64ToLong(s):
    return binaryToLong(fromBase64(s))

def randomString(length, chrs=None):
    """Produce a string of length random bytes, chosen from chrs."""
    if chrs is None:
        return getBytes(length)
    else:
        n = len(chrs)
        return ''.join([chrs[randrange(n)] for _ in xrange(length)])

########NEW FILE########
__FILENAME__ = dh
from openid import cryptutil
from openid import oidutil

def strxor(x, y):
    if len(x) != len(y):
        raise ValueError('Inputs to strxor must have the same length')

    xor = lambda (a, b): chr(ord(a) ^ ord(b))
    return "".join(map(xor, zip(x, y)))

class DiffieHellman(object):
    DEFAULT_MOD = 155172898181473697471232257763715539915724801966915404479707795314057629378541917580651227423698188993727816152646631438561595825688188889951272158842675419950341258706556549803580104870537681476726513255747040765857479291291572334510643245094715007229621094194349783925984760375594985848253359305585439638443L

    DEFAULT_GEN = 2

    def fromDefaults(cls):
        return cls(cls.DEFAULT_MOD, cls.DEFAULT_GEN)

    fromDefaults = classmethod(fromDefaults)

    def __init__(self, modulus, generator):
        self.modulus = long(modulus)
        self.generator = long(generator)

        self._setPrivate(cryptutil.randrange(1, modulus - 1))

    def _setPrivate(self, private):
        """This is here to make testing easier"""
        self.private = private
        self.public = pow(self.generator, self.private, self.modulus)

    def usingDefaultValues(self):
        return (self.modulus == self.DEFAULT_MOD and
                self.generator == self.DEFAULT_GEN)

    def getSharedSecret(self, composite):
        return pow(composite, self.private, self.modulus)

    def xorSecret(self, composite, secret, hash_func):
        dh_shared = self.getSharedSecret(composite)
        hashed_dh_shared = hash_func(cryptutil.longToBinary(dh_shared))
        return strxor(secret, hashed_dh_shared)

########NEW FILE########
__FILENAME__ = extension
from openid.message import Message

class Extension(object):
    """An interface for OpenID extensions.

    @ivar ns_uri: The namespace to which to add the arguments for this
        extension
    """
    ns_uri = None
    ns_alias = None

    def getExtensionArgs(self):
        """Get the string arguments that should be added to an OpenID
        message for this extension.
        """
        raise NotImplementedError

    def toMessage(self, message=None):
        """Add the arguments from this extension to the provided
        message, or create a new message containing only those
        arguments.

        @returns: The message with the extension arguments added
        """
        if message is None:
            message = Message()

        try:
            message.namespaces.addAlias(self.ns_uri, self.ns_alias)
        except KeyError:
            if message.namespaces.getAlias(self.ns_uri) != self.ns_alias:
                raise

        message.updateArgs(self.ns_uri, self.getExtensionArgs())
        return message

########NEW FILE########
__FILENAME__ = ax
# -*- test-case-name: openid.test.test_ax -*-
"""Implements the OpenID Attribute Exchange specification, version 1.0.

@since: 2.1.0
"""

__all__ = [
    'AttributeRequest',
    'FetchRequest',
    'FetchResponse',
    'StoreRequest',
    'StoreResponse',
    ]

from openid import extension
from openid.server.trustroot import TrustRoot
from openid.message import NamespaceMap, OPENID_NS

# Use this as the 'count' value for an attribute in a FetchRequest to
# ask for as many values as the OP can provide.
UNLIMITED_VALUES = "unlimited"

# Minimum supported alias length in characters.  Here for
# completeness.
MINIMUM_SUPPORTED_ALIAS_LENGTH = 32

def checkAlias(alias):
    """
    Check an alias for invalid characters; raise AXError if any are
    found.  Return None if the alias is valid.
    """
    if ',' in alias:
        raise AXError("Alias %r must not contain comma" % (alias,))
    if '.' in alias:
        raise AXError("Alias %r must not contain period" % (alias,))


class AXError(ValueError):
    """Results from data that does not meet the attribute exchange 1.0
    specification"""


class NotAXMessage(AXError):
    """Raised when there is no Attribute Exchange mode in the message."""

    def __repr__(self):
        return self.__class__.__name__

    def __str__(self):
        return self.__class__.__name__


class AXMessage(extension.Extension):
    """Abstract class containing common code for attribute exchange messages

    @cvar ns_alias: The preferred namespace alias for attribute
        exchange messages

    @cvar mode: The type of this attribute exchange message. This must
        be overridden in subclasses.
    """

    # This class is abstract, so it's OK that it doesn't override the
    # abstract method in Extension:
    #
    #pylint:disable-msg=W0223

    ns_alias = 'ax'
    mode = None
    ns_uri = 'http://openid.net/srv/ax/1.0'

    def _checkMode(self, ax_args):
        """Raise an exception if the mode in the attribute exchange
        arguments does not match what is expected for this class.

        @raises NotAXMessage: When there is no mode value in ax_args at all.

        @raises AXError: When mode does not match.
        """
        mode = ax_args.get('mode')
        if mode != self.mode:
            if not mode:
                raise NotAXMessage()
            else:
                raise AXError(
                    'Expected mode %r; got %r' % (self.mode, mode))

    def _newArgs(self):
        """Return a set of attribute exchange arguments containing the
        basic information that must be in every attribute exchange
        message.
        """
        return {'mode':self.mode}


class AttrInfo(object):
    """Represents a single attribute in an attribute exchange
    request. This should be added to an AXRequest object in order to
    request the attribute.

    @ivar required: Whether the attribute will be marked as required
        when presented to the subject of the attribute exchange
        request.
    @type required: bool

    @ivar count: How many values of this type to request from the
        subject. Defaults to one.
    @type count: int

    @ivar type_uri: The identifier that determines what the attribute
        represents and how it is serialized. For example, one type URI
        representing dates could represent a Unix timestamp in base 10
        and another could represent a human-readable string.
    @type type_uri: str

    @ivar alias: The name that should be given to this alias in the
        request. If it is not supplied, a generic name will be
        assigned. For example, if you want to call a Unix timestamp
        value 'tstamp', set its alias to that value. If two attributes
        in the same message request to use the same alias, the request
        will fail to be generated.
    @type alias: str or NoneType
    """

    # It's OK that this class doesn't have public methods (it's just a
    # holder for a bunch of attributes):
    #
    #pylint:disable-msg=R0903

    def __init__(self, type_uri, count=1, required=False, alias=None):
        self.required = required
        self.count = count
        self.type_uri = type_uri
        self.alias = alias

        if self.alias is not None:
            checkAlias(self.alias)

    def wantsUnlimitedValues(self):
        """
        When processing a request for this attribute, the OP should
        call this method to determine whether all available attribute
        values were requested.  If self.count == UNLIMITED_VALUES,
        this returns True.  Otherwise this returns False, in which
        case self.count is an integer.
        """
        return self.count == UNLIMITED_VALUES

def toTypeURIs(namespace_map, alias_list_s):
    """Given a namespace mapping and a string containing a
    comma-separated list of namespace aliases, return a list of type
    URIs that correspond to those aliases.

    @param namespace_map: The mapping from namespace URI to alias
    @type namespace_map: openid.message.NamespaceMap

    @param alias_list_s: The string containing the comma-separated
        list of aliases. May also be None for convenience.
    @type alias_list_s: str or NoneType

    @returns: The list of namespace URIs that corresponds to the
        supplied list of aliases. If the string was zero-length or
        None, an empty list will be returned.

    @raise KeyError: If an alias is present in the list of aliases but
        is not present in the namespace map.
    """
    uris = []

    if alias_list_s:
        for alias in alias_list_s.split(','):
            type_uri = namespace_map.getNamespaceURI(alias)
            if type_uri is None:
                raise KeyError(
                    'No type is defined for attribute name %r' % (alias,))
            else:
                uris.append(type_uri)

    return uris


class FetchRequest(AXMessage):
    """An attribute exchange 'fetch_request' message. This message is
    sent by a relying party when it wishes to obtain attributes about
    the subject of an OpenID authentication request.

    @ivar requested_attributes: The attributes that have been
        requested thus far, indexed by the type URI.
    @type requested_attributes: {str:AttrInfo}

    @ivar update_url: A URL that will accept responses for this
        attribute exchange request, even in the absence of the user
        who made this request.
    """
    mode = 'fetch_request'

    def __init__(self, update_url=None):
        AXMessage.__init__(self)
        self.requested_attributes = {}
        self.update_url = update_url

    def add(self, attribute):
        """Add an attribute to this attribute exchange request.

        @param attribute: The attribute that is being requested
        @type attribute: C{L{AttrInfo}}

        @returns: None

        @raise KeyError: when the requested attribute is already
            present in this fetch request.
        """
        if attribute.type_uri in self.requested_attributes:
            raise KeyError('The attribute %r has already been requested'
                           % (attribute.type_uri,))

        self.requested_attributes[attribute.type_uri] = attribute

    def getExtensionArgs(self):
        """Get the serialized form of this attribute fetch request.

        @returns: The fetch request message parameters
        @rtype: {unicode:unicode}
        """
        aliases = NamespaceMap()

        required = []
        if_available = []

        ax_args = self._newArgs()

        for type_uri, attribute in self.requested_attributes.iteritems():
            if attribute.alias is None:
                alias = aliases.add(type_uri)
            else:
                # This will raise an exception when the second
                # attribute with the same alias is added. I think it
                # would be better to complain at the time that the
                # attribute is added to this object so that the code
                # that is adding it is identified in the stack trace,
                # but it's more work to do so, and it won't be 100%
                # accurate anyway, since the attributes are
                # mutable. So for now, just live with the fact that
                # we'll learn about the error later.
                #
                # The other possible approach is to hide the error and
                # generate a new alias on the fly. I think that would
                # probably be bad.
                alias = aliases.addAlias(type_uri, attribute.alias)

            if attribute.required:
                required.append(alias)
            else:
                if_available.append(alias)

            if attribute.count != 1:
                ax_args['count.' + alias] = str(attribute.count)

            ax_args['type.' + alias] = type_uri

        if required:
            ax_args['required'] = ','.join(required)

        if if_available:
            ax_args['if_available'] = ','.join(if_available)

        return ax_args

    def getRequiredAttrs(self):
        """Get the type URIs for all attributes that have been marked
        as required.

        @returns: A list of the type URIs for attributes that have
            been marked as required.
        @rtype: [str]
        """
        required = []
        for type_uri, attribute in self.requested_attributes.iteritems():
            if attribute.required:
                required.append(type_uri)

        return required

    def fromOpenIDRequest(cls, openid_request):
        """Extract a FetchRequest from an OpenID message

        @param openid_request: The OpenID authentication request
            containing the attribute fetch request
        @type openid_request: C{L{openid.server.server.CheckIDRequest}}

        @rtype: C{L{FetchRequest}} or C{None}
        @returns: The FetchRequest extracted from the message or None, if
            the message contained no AX extension.

        @raises KeyError: if the AuthRequest is not consistent in its use
            of namespace aliases.

        @raises AXError: When parseExtensionArgs would raise same.

        @see: L{parseExtensionArgs}
        """
        message = openid_request.message
        ax_args = message.getArgs(cls.ns_uri)
        self = cls()
        try:
            self.parseExtensionArgs(ax_args)
        except NotAXMessage, err:
            return None

        if self.update_url:
            # Update URL must match the openid.realm of the underlying
            # OpenID 2 message.
            realm = message.getArg(OPENID_NS, 'realm',
                                   message.getArg(OPENID_NS, 'return_to'))

            if not realm:
                raise AXError(("Cannot validate update_url %r " +
                               "against absent realm") % (self.update_url,))

            tr = TrustRoot.parse(realm)
            if not tr.validateURL(self.update_url):
                raise AXError("Update URL %r failed validation against realm %r" %
                              (self.update_url, realm,))

        return self

    fromOpenIDRequest = classmethod(fromOpenIDRequest)

    def parseExtensionArgs(self, ax_args):
        """Given attribute exchange arguments, populate this FetchRequest.

        @param ax_args: Attribute Exchange arguments from the request.
            As returned from L{Message.getArgs<openid.message.Message.getArgs>}.
        @type ax_args: dict

        @raises KeyError: if the message is not consistent in its use
            of namespace aliases.

        @raises NotAXMessage: If ax_args does not include an Attribute Exchange
            mode.

        @raises AXError: If the data to be parsed does not follow the
            attribute exchange specification. At least when
            'if_available' or 'required' is not specified for a
            particular attribute type.
        """
        # Raises an exception if the mode is not the expected value
        self._checkMode(ax_args)

        aliases = NamespaceMap()

        for key, value in ax_args.iteritems():
            if key.startswith('type.'):
                alias = key[5:]
                type_uri = value
                aliases.addAlias(type_uri, alias)

                count_key = 'count.' + alias
                count_s = ax_args.get(count_key)
                if count_s:
                    try:
                        count = int(count_s)
                        if count <= 0:
                            raise AXError("Count %r must be greater than zero, got %r" % (count_key, count_s,))
                    except ValueError:
                        if count_s != UNLIMITED_VALUES:
                            raise AXError("Invalid count value for %r: %r" % (count_key, count_s,))
                        count = count_s
                else:
                    count = 1

                self.add(AttrInfo(type_uri, alias=alias, count=count))

        required = toTypeURIs(aliases, ax_args.get('required'))

        for type_uri in required:
            self.requested_attributes[type_uri].required = True

        if_available = toTypeURIs(aliases, ax_args.get('if_available'))

        all_type_uris = required + if_available

        for type_uri in aliases.iterNamespaceURIs():
            if type_uri not in all_type_uris:
                raise AXError(
                    'Type URI %r was in the request but not '
                    'present in "required" or "if_available"' % (type_uri,))

        self.update_url = ax_args.get('update_url')

    def iterAttrs(self):
        """Iterate over the AttrInfo objects that are
        contained in this fetch_request.
        """
        return self.requested_attributes.itervalues()

    def __iter__(self):
        """Iterate over the attribute type URIs in this fetch_request
        """
        return iter(self.requested_attributes)

    def has_key(self, type_uri):
        """Is the given type URI present in this fetch_request?
        """
        return type_uri in self.requested_attributes

    __contains__ = has_key


class AXKeyValueMessage(AXMessage):
    """An abstract class that implements a message that has attribute
    keys and values. It contains the common code between
    fetch_response and store_request.
    """

    # This class is abstract, so it's OK that it doesn't override the
    # abstract method in Extension:
    #
    #pylint:disable-msg=W0223

    def __init__(self):
        AXMessage.__init__(self)
        self.data = {}

    def addValue(self, type_uri, value):
        """Add a single value for the given attribute type to the
        message. If there are already values specified for this type,
        this value will be sent in addition to the values already
        specified.

        @param type_uri: The URI for the attribute

        @param value: The value to add to the response to the relying
            party for this attribute
        @type value: unicode

        @returns: None
        """
        try:
            values = self.data[type_uri]
        except KeyError:
            values = self.data[type_uri] = []

        values.append(value)

    def setValues(self, type_uri, values):
        """Set the values for the given attribute type. This replaces
        any values that have already been set for this attribute.

        @param type_uri: The URI for the attribute

        @param values: A list of values to send for this attribute.
        @type values: [unicode]
        """

        self.data[type_uri] = values

    def _getExtensionKVArgs(self, aliases=None):
        """Get the extension arguments for the key/value pairs
        contained in this message.

        @param aliases: An alias mapping. Set to None if you don't
            care about the aliases for this request.
        """
        if aliases is None:
            aliases = NamespaceMap()

        ax_args = {}

        for type_uri, values in self.data.iteritems():
            alias = aliases.add(type_uri)

            ax_args['type.' + alias] = type_uri
            ax_args['count.' + alias] = str(len(values))

            for i, value in enumerate(values):
                key = 'value.%s.%d' % (alias, i + 1)
                ax_args[key] = value

        return ax_args

    def parseExtensionArgs(self, ax_args):
        """Parse attribute exchange key/value arguments into this
        object.

        @param ax_args: The attribute exchange fetch_response
            arguments, with namespacing removed.
        @type ax_args: {unicode:unicode}

        @returns: None

        @raises ValueError: If the message has bad values for
            particular fields

        @raises KeyError: If the namespace mapping is bad or required
            arguments are missing
        """
        self._checkMode(ax_args)

        aliases = NamespaceMap()

        for key, value in ax_args.iteritems():
            if key.startswith('type.'):
                type_uri = value
                alias = key[5:]
                checkAlias(alias)
                aliases.addAlias(type_uri, alias)

        for type_uri, alias in aliases.iteritems():
            try:
                count_s = ax_args['count.' + alias]
            except KeyError:
                value = ax_args['value.' + alias]

                if value == u'':
                    values = []
                else:
                    values = [value]
            else:
                count = int(count_s)
                values = []
                for i in range(1, count + 1):
                    value_key = 'value.%s.%d' % (alias, i)
                    value = ax_args[value_key]
                    values.append(value)

            self.data[type_uri] = values

    def getSingle(self, type_uri, default=None):
        """Get a single value for an attribute. If no value was sent
        for this attribute, use the supplied default. If there is more
        than one value for this attribute, this method will fail.

        @type type_uri: str
        @param type_uri: The URI for the attribute

        @param default: The value to return if the attribute was not
            sent in the fetch_response.

        @returns: The value of the attribute in the fetch_response
            message, or the default supplied
        @rtype: unicode or NoneType

        @raises ValueError: If there is more than one value for this
            parameter in the fetch_response message.
        @raises KeyError: If the attribute was not sent in this response
        """
        values = self.data.get(type_uri)
        if not values:
            return default
        elif len(values) == 1:
            return values[0]
        else:
            raise AXError(
                'More than one value present for %r' % (type_uri,))

    def get(self, type_uri):
        """Get the list of values for this attribute in the
        fetch_response.

        XXX: what to do if the values are not present? default
        parameter? this is funny because it's always supposed to
        return a list, so the default may break that, though it's
        provided by the user's code, so it might be okay. If no
        default is supplied, should the return be None or []?

        @param type_uri: The URI of the attribute

        @returns: The list of values for this attribute in the
            response. May be an empty list.
        @rtype: [unicode]

        @raises KeyError: If the attribute was not sent in the response
        """
        return self.data[type_uri]

    def count(self, type_uri):
        """Get the number of responses for a particular attribute in
        this fetch_response message.

        @param type_uri: The URI of the attribute

        @returns: The number of values sent for this attribute

        @raises KeyError: If the attribute was not sent in the
            response. KeyError will not be raised if the number of
            values was zero.
        """
        return len(self.get(type_uri))


class FetchResponse(AXKeyValueMessage):
    """A fetch_response attribute exchange message
    """
    mode = 'fetch_response'

    def __init__(self, request=None, update_url=None):
        """
        @param request: When supplied, I will use namespace aliases
            that match those in this request.  I will also check to
            make sure I do not respond with attributes that were not
            requested.

        @type request: L{FetchRequest}

        @param update_url: By default, C{update_url} is taken from the
            request.  But if you do not supply the request, you may set
            the C{update_url} here.

        @type update_url: str
        """
        AXKeyValueMessage.__init__(self)
        self.update_url = update_url
        self.request = request

    def getExtensionArgs(self):
        """Serialize this object into arguments in the attribute
        exchange namespace

        @returns: The dictionary of unqualified attribute exchange
            arguments that represent this fetch_response.
        @rtype: {unicode;unicode}
        """

        aliases = NamespaceMap()

        zero_value_types = []

        if self.request is not None:
            # Validate the data in the context of the request (the
            # same attributes should be present in each, and the
            # counts in the response must be no more than the counts
            # in the request)

            for type_uri in self.data:
                if type_uri not in self.request:
                    raise KeyError(
                        'Response attribute not present in request: %r'
                        % (type_uri,))

            for attr_info in self.request.iterAttrs():
                # Copy the aliases from the request so that reading
                # the response in light of the request is easier
                if attr_info.alias is None:
                    aliases.add(attr_info.type_uri)
                else:
                    aliases.addAlias(attr_info.type_uri, attr_info.alias)

                try:
                    values = self.data[attr_info.type_uri]
                except KeyError:
                    values = []
                    zero_value_types.append(attr_info)

                if (attr_info.count != UNLIMITED_VALUES) and \
                       (attr_info.count < len(values)):
                    raise AXError(
                        'More than the number of requested values were '
                        'specified for %r' % (attr_info.type_uri,))

        kv_args = self._getExtensionKVArgs(aliases)

        # Add the KV args into the response with the args that are
        # unique to the fetch_response
        ax_args = self._newArgs()

        # For each requested attribute, put its type/alias and count
        # into the response even if no data were returned.
        for attr_info in zero_value_types:
            alias = aliases.getAlias(attr_info.type_uri)
            kv_args['type.' + alias] = attr_info.type_uri
            kv_args['count.' + alias] = '0'

        update_url = ((self.request and self.request.update_url)
                      or self.update_url)

        if update_url:
            ax_args['update_url'] = update_url

        ax_args.update(kv_args)

        return ax_args

    def parseExtensionArgs(self, ax_args):
        """@see: {Extension.parseExtensionArgs<openid.extension.Extension.parseExtensionArgs>}"""
        super(FetchResponse, self).parseExtensionArgs(ax_args)
        self.update_url = ax_args.get('update_url')

    def fromSuccessResponse(cls, success_response, signed=True):
        """Construct a FetchResponse object from an OpenID library
        SuccessResponse object.

        @param success_response: A successful id_res response object
        @type success_response: openid.consumer.consumer.SuccessResponse

        @param signed: Whether non-signed args should be
            processsed. If True (the default), only signed arguments
            will be processsed.
        @type signed: bool

        @returns: A FetchResponse containing the data from the OpenID
            message, or None if the SuccessResponse did not contain AX
            extension data.

        @raises AXError: when the AX data cannot be parsed.
        """
        self = cls()
        ax_args = success_response.extensionResponse(self.ns_uri, signed)

        try:
            self.parseExtensionArgs(ax_args)
        except NotAXMessage, err:
            return None
        else:
            return self

    fromSuccessResponse = classmethod(fromSuccessResponse)


class StoreRequest(AXKeyValueMessage):
    """A store request attribute exchange message representation
    """
    mode = 'store_request'

    def __init__(self, aliases=None):
        """
        @param aliases: The namespace aliases to use when making this
            store request.  Leave as None to use defaults.
        """
        super(StoreRequest, self).__init__()
        self.aliases = aliases

    def getExtensionArgs(self):
        """
        @see: L{Extension.getExtensionArgs<openid.extension.Extension.getExtensionArgs>}
        """
        ax_args = self._newArgs()
        kv_args = self._getExtensionKVArgs(self.aliases)
        ax_args.update(kv_args)
        return ax_args


class StoreResponse(AXMessage):
    """An indication that the store request was processed along with
    this OpenID transaction.
    """

    SUCCESS_MODE = 'store_response_success'
    FAILURE_MODE = 'store_response_failure'

    def __init__(self, succeeded=True, error_message=None):
        AXMessage.__init__(self)

        if succeeded and error_message is not None:
            raise AXError('An error message may only be included in a '
                             'failing fetch response')
        if succeeded:
            self.mode = self.SUCCESS_MODE
        else:
            self.mode = self.FAILURE_MODE

        self.error_message = error_message

    def succeeded(self):
        """Was this response a success response?"""
        return self.mode == self.SUCCESS_MODE

    def getExtensionArgs(self):
        """@see: {Extension.getExtensionArgs<openid.extension.Extension.getExtensionArgs>}"""
        ax_args = self._newArgs()
        if not self.succeeded() and self.error_message:
            ax_args['error'] = self.error_message

        return ax_args

########NEW FILE########
__FILENAME__ = pape
"""An implementation of the OpenID Provider Authentication Policy
Extension 1.0

@see: http://openid.net/developers/specs/

@since: 2.1.0
"""

__all__ = [
    'Request',
    'Response',
    'ns_uri',
    'AUTH_PHISHING_RESISTANT',
    'AUTH_MULTI_FACTOR',
    'AUTH_MULTI_FACTOR_PHYSICAL',
    ]

from openid.extension import Extension

ns_uri = "http://specs.openid.net/extensions/pape/1.0"

AUTH_MULTI_FACTOR_PHYSICAL = \
    'http://schemas.openid.net/pape/policies/2007/06/multi-factor-physical'
AUTH_MULTI_FACTOR = \
    'http://schemas.openid.net/pape/policies/2007/06/multi-factor'
AUTH_PHISHING_RESISTANT = \
    'http://schemas.openid.net/pape/policies/2007/06/phishing-resistant'

class Request(Extension):
    """A Provider Authentication Policy request, sent from a relying
    party to a provider

    @ivar preferred_auth_policies: The authentication policies that
        the relying party prefers
    @type preferred_auth_policies: [str]

    @ivar max_auth_age: The maximum time, in seconds, that the relying
        party wants to allow to have elapsed before the user must
        re-authenticate
    @type max_auth_age: int or NoneType
    """

    ns_alias = 'pape'

    def __init__(self, preferred_auth_policies=None, max_auth_age=None):
        super(Request, self).__init__(self)
        if not preferred_auth_policies:
            preferred_auth_policies = []

        self.preferred_auth_policies = preferred_auth_policies
        self.max_auth_age = max_auth_age

    def __nonzero__(self):
        return bool(self.preferred_auth_policies or
                    self.max_auth_age is not None)

    def addPolicyURI(self, policy_uri):
        """Add an acceptable authentication policy URI to this request

        This method is intended to be used by the relying party to add
        acceptable authentication types to the request.

        @param policy_uri: The identifier for the preferred type of
            authentication.
        @see: http://openid.net/specs/openid-provider-authentication-policy-extension-1_0-01.html#auth_policies
        """
        if policy_uri not in self.preferred_auth_policies:
            self.preferred_auth_policies.append(policy_uri)

    def getExtensionArgs(self):
        """@see: C{L{Extension.getExtensionArgs}}
        """
        ns_args = {
            'preferred_auth_policies':' '.join(self.preferred_auth_policies)
            }

        if self.max_auth_age is not None:
            ns_args['max_auth_age'] = str(self.max_auth_age)

        return ns_args

    def fromOpenIDRequest(cls, request):
        """Instantiate a Request object from the arguments in a
        C{checkid_*} OpenID message
        """
        self = cls()
        args = request.message.getArgs(self.ns_uri)

        if args == {}:
            return None

        self.parseExtensionArgs(args)
        return self

    fromOpenIDRequest = classmethod(fromOpenIDRequest)

    def parseExtensionArgs(self, args):
        """Set the state of this request to be that expressed in these
        PAPE arguments

        @param args: The PAPE arguments without a namespace

        @rtype: None

        @raises ValueError: When the max_auth_age is not parseable as
            an integer
        """

        # preferred_auth_policies is a space-separated list of policy URIs
        self.preferred_auth_policies = []

        policies_str = args.get('preferred_auth_policies')
        if policies_str:
            for uri in policies_str.split(' '):
                if uri not in self.preferred_auth_policies:
                    self.preferred_auth_policies.append(uri)

        # max_auth_age is base-10 integer number of seconds
        max_auth_age_str = args.get('max_auth_age')
        self.max_auth_age = None

        if max_auth_age_str:
            try:
                self.max_auth_age = int(max_auth_age_str)
            except ValueError:
                pass

    def preferredTypes(self, supported_types):
        """Given a list of authentication policy URIs that a provider
        supports, this method returns the subsequence of those types
        that are preferred by the relying party.

        @param supported_types: A sequence of authentication policy
            type URIs that are supported by a provider

        @returns: The sub-sequence of the supported types that are
            preferred by the relying party. This list will be ordered
            in the order that the types appear in the supported_types
            sequence, and may be empty if the provider does not prefer
            any of the supported authentication types.

        @returntype: [str]
        """
        return filter(self.preferred_auth_policies.__contains__,
                      supported_types)

Request.ns_uri = ns_uri


class Response(Extension):
    """A Provider Authentication Policy response, sent from a provider
    to a relying party
    """

    ns_alias = 'pape'

    def __init__(self, auth_policies=None, auth_age=None,
                 nist_auth_level=None):
        super(Response, self).__init__(self)
        if auth_policies:
            self.auth_policies = auth_policies
        else:
            self.auth_policies = []

        self.auth_age = auth_age
        self.nist_auth_level = nist_auth_level

    def addPolicyURI(self, policy_uri):
        """Add a authentication policy to this response

        This method is intended to be used by the provider to add a
        policy that the provider conformed to when authenticating the user.

        @param policy_uri: The identifier for the preferred type of
            authentication.
        @see: http://openid.net/specs/openid-provider-authentication-policy-extension-1_0-01.html#auth_policies
        """
        if policy_uri not in self.auth_policies:
            self.auth_policies.append(policy_uri)

    def fromSuccessResponse(cls, success_response):
        """Create a C{L{Response}} object from a successful OpenID
        library response
        (C{L{openid.consumer.consumer.SuccessResponse}}) response
        message

        @param success_response: A SuccessResponse from consumer.complete()
        @type success_response: C{L{openid.consumer.consumer.SuccessResponse}}

        @rtype: Response
        @returns: A provider authentication policy response from the
            data that was supplied with the C{id_res} response.
        """
        self = cls()

        # PAPE requires that the args be signed.
        args = success_response.getSignedNS(self.ns_uri)

        self.parseExtensionArgs(args)

        return self

    def parseExtensionArgs(self, args, strict=False):
        """Parse the provider authentication policy arguments into the
        internal state of this object

        @param args: unqualified provider authentication policy
            arguments

        @param strict: Whether to raise an exception when bad data is
            encountered

        @returns: None. The data is parsed into the internal fields of
            this object.
        """
        policies_str = args.get('auth_policies')
        if policies_str:
            self.auth_policies = policies_str.split(' ')

        nist_level_str = args.get('nist_auth_level')
        if nist_level_str:
            try:
                nist_level = int(nist_level_str)
            except ValueError:
                if strict:
                    raise ValueError('nist_auth_level must be an integer between '
                                     'zero and four, inclusive')
                else:
                    self.nist_auth_level = None
            else:
                if 0 <= nist_level < 5:
                    self.nist_auth_level = nist_level

        auth_age_str = args.get('auth_age')
        if auth_age_str:
            try:
                auth_age = int(auth_age_str)
            except ValueError:
                if strict:
                    raise
            else:
                if auth_age >= 0:
                    self.auth_age = auth_age
                elif strict:
                    raise ValueError('Auth age must be above zero')

    fromSuccessResponse = classmethod(fromSuccessResponse)

    def getExtensionArgs(self):
        """@see: C{L{Extension.getExtensionArgs}}
        """
        ns_args = {
            'auth_policies':' '.join(self.auth_policies),
            }

        if self.nist_auth_level is not None:
            if self.nist_auth_level not in range(0, 5):
                raise ValueError('nist_auth_level must be an integer between '
                                 'zero and four, inclusive')
            ns_args['nist_auth_level'] = str(self.nist_auth_level)

        if self.auth_age is not None:
            if self.auth_age < 0:
                raise ValueError('Auth age must be above zero')

            ns_args['auth_age'] = str(int(self.auth_age))

        return ns_args

Response.ns_uri = ns_uri

########NEW FILE########
__FILENAME__ = sreg
"""Simple registration request and response parsing and object representation

This module contains objects representing simple registration requests
and responses that can be used with both OpenID relying parties and
OpenID providers.

  1. The relying party creates a request object and adds it to the
     C{L{AuthRequest<openid.consumer.consumer.AuthRequest>}} object
     before making the C{checkid_} request to the OpenID provider::

      auth_request.addExtension(SRegRequest(required=['email']))

  2. The OpenID provider extracts the simple registration request from
     the OpenID request using C{L{SRegRequest.fromOpenIDRequest}},
     gets the user's approval and data, creates a C{L{SRegResponse}}
     object and adds it to the C{id_res} response::

      sreg_req = SRegRequest.fromOpenIDRequest(checkid_request)
      # [ get the user's approval and data, informing the user that
      #   the fields in sreg_response were requested ]
      sreg_resp = SRegResponse.extractResponse(sreg_req, user_data)
      sreg_resp.toMessage(openid_response.fields)

  3. The relying party uses C{L{SRegResponse.fromSuccessResponse}} to
     extract the data from the OpenID response::

      sreg_resp = SRegResponse.fromSuccessResponse(success_response)

@since: 2.0

@var sreg_data_fields: The names of the data fields that are listed in
    the sreg spec, and a description of them in English

@var sreg_uri: The preferred URI to use for the simple registration
    namespace and XRD Type value
"""

from openid.message import registerNamespaceAlias, \
     NamespaceAliasRegistrationError
from openid.extension import Extension
from openid import oidutil

try:
    basestring #pylint:disable-msg=W0104
except NameError:
    # For Python 2.2
    basestring = (str, unicode) #pylint:disable-msg=W0622

__all__ = [
    'SRegRequest',
    'SRegResponse',
    'data_fields',
    'ns_uri',
    'ns_uri_1_0',
    'ns_uri_1_1',
    'supportsSReg',
    ]

# The data fields that are listed in the sreg spec
data_fields = {
    'fullname':'Full Name',
    'nickname':'Nickname',
    'dob':'Date of Birth',
    'email':'E-mail Address',
    'gender':'Gender',
    'postcode':'Postal Code',
    'country':'Country',
    'language':'Language',
    'timezone':'Time Zone',
    }

def checkFieldName(field_name):
    """Check to see that the given value is a valid simple
    registration data field name.

    @raise ValueError: if the field name is not a valid simple
        registration data field name
    """
    if field_name not in data_fields:
        raise ValueError('%r is not a defined simple registration field' %
                         (field_name,))

# URI used in the wild for Yadis documents advertising simple
# registration support
ns_uri_1_0 = 'http://openid.net/sreg/1.0'

# URI in the draft specification for simple registration 1.1
# <http://openid.net/specs/openid-simple-registration-extension-1_1-01.html>
ns_uri_1_1 = 'http://openid.net/extensions/sreg/1.1'

# This attribute will always hold the preferred URI to use when adding
# sreg support to an XRDS file or in an OpenID namespace declaration.
ns_uri = ns_uri_1_1

try:
    registerNamespaceAlias(ns_uri_1_1, 'sreg')
except NamespaceAliasRegistrationError, e:
    oidutil.log('registerNamespaceAlias(%r, %r) failed: %s' % (ns_uri_1_1,
                                                               'sreg', str(e),))

def supportsSReg(endpoint):
    """Does the given endpoint advertise support for simple
    registration?

    @param endpoint: The endpoint object as returned by OpenID discovery
    @type endpoint: openid.consumer.discover.OpenIDEndpoint

    @returns: Whether an sreg type was advertised by the endpoint
    @rtype: bool
    """
    return (endpoint.usesExtension(ns_uri_1_1) or
            endpoint.usesExtension(ns_uri_1_0))

class SRegNamespaceError(ValueError):
    """The simple registration namespace was not found and could not
    be created using the expected name (there's another extension
    using the name 'sreg')

    This is not I{illegal}, for OpenID 2, although it probably
    indicates a problem, since it's not expected that other extensions
    will re-use the alias that is in use for OpenID 1.

    If this is an OpenID 1 request, then there is no recourse. This
    should not happen unless some code has modified the namespaces for
    the message that is being processed.
    """

def getSRegNS(message):
    """Extract the simple registration namespace URI from the given
    OpenID message. Handles OpenID 1 and 2, as well as both sreg
    namespace URIs found in the wild, as well as missing namespace
    definitions (for OpenID 1)

    @param message: The OpenID message from which to parse simple
        registration fields. This may be a request or response message.
    @type message: C{L{openid.message.Message}}

    @returns: the sreg namespace URI for the supplied message. The
        message may be modified to define a simple registration
        namespace.
    @rtype: C{str}

    @raise ValueError: when using OpenID 1 if the message defines
        the 'sreg' alias to be something other than a simple
        registration type.
    """
    # See if there exists an alias for one of the two defined simple
    # registration types.
    for sreg_ns_uri in [ns_uri_1_1, ns_uri_1_0]:
        alias = message.namespaces.getAlias(sreg_ns_uri)
        if alias is not None:
            break
    else:
        # There is no alias for either of the types, so try to add
        # one. We default to using the modern value (1.1)
        sreg_ns_uri = ns_uri_1_1
        try:
            message.namespaces.addAlias(ns_uri_1_1, 'sreg')
        except KeyError, why:
            # An alias for the string 'sreg' already exists, but it's
            # defined for something other than simple registration
            raise SRegNamespaceError(why[0])

    # we know that sreg_ns_uri defined, because it's defined in the
    # else clause of the loop as well, so disable the warning
    return sreg_ns_uri #pylint:disable-msg=W0631

class SRegRequest(Extension):
    """An object to hold the state of a simple registration request.

    @ivar required: A list of the required fields in this simple
        registration request
    @type required: [str]

    @ivar optional: A list of the optional fields in this simple
        registration request
    @type optional: [str]

    @ivar policy_url: The policy URL that was provided with the request
    @type policy_url: str or NoneType

    @group Consumer: requestField, requestFields, getExtensionArgs, addToOpenIDRequest
    @group Server: fromOpenIDRequest, parseExtensionArgs
    """

    ns_alias = 'sreg'

    def __init__(self, required=None, optional=None, policy_url=None,
                 sreg_ns_uri=ns_uri):
        """Initialize an empty simple registration request"""
        Extension.__init__(self)
        self.required = []
        self.optional = []
        self.policy_url = policy_url
        self.ns_uri = sreg_ns_uri

        if required:
            self.requestFields(required, required=True, strict=True)

        if optional:
            self.requestFields(optional, required=False, strict=True)

    # Assign getSRegNS to a static method so that it can be
    # overridden for testing.
    _getSRegNS = staticmethod(getSRegNS)

    def fromOpenIDRequest(cls, request):
        """Create a simple registration request that contains the
        fields that were requested in the OpenID request with the
        given arguments

        @param request: The OpenID request
        @type request: openid.server.CheckIDRequest

        @returns: The newly created simple registration request
        @rtype: C{L{SRegRequest}}
        """
        self = cls()

        # Since we're going to mess with namespace URI mapping, don't
        # mutate the object that was passed in.
        message = request.message.copy()

        self.ns_uri = self._getSRegNS(message)
        args = message.getArgs(self.ns_uri)
        self.parseExtensionArgs(args)

        return self

    fromOpenIDRequest = classmethod(fromOpenIDRequest)

    def parseExtensionArgs(self, args, strict=False):
        """Parse the unqualified simple registration request
        parameters and add them to this object.

        This method is essentially the inverse of
        C{L{getExtensionArgs}}. This method restores the serialized simple
        registration request fields.

        If you are extracting arguments from a standard OpenID
        checkid_* request, you probably want to use C{L{fromOpenIDRequest}},
        which will extract the sreg namespace and arguments from the
        OpenID request. This method is intended for cases where the
        OpenID server needs more control over how the arguments are
        parsed than that method provides.

        >>> args = message.getArgs(ns_uri)
        >>> request.parseExtensionArgs(args)

        @param args: The unqualified simple registration arguments
        @type args: {str:str}

        @param strict: Whether requests with fields that are not
            defined in the simple registration specification should be
            tolerated (and ignored)
        @type strict: bool

        @returns: None; updates this object
        """
        for list_name in ['required', 'optional']:
            required = (list_name == 'required')
            items = args.get(list_name)
            if items:
                for field_name in items.split(','):
                    try:
                        self.requestField(field_name, required, strict)
                    except ValueError:
                        if strict:
                            raise

        self.policy_url = args.get('policy_url')

    def allRequestedFields(self):
        """A list of all of the simple registration fields that were
        requested, whether they were required or optional.

        @rtype: [str]
        """
        return self.required + self.optional

    def wereFieldsRequested(self):
        """Have any simple registration fields been requested?

        @rtype: bool
        """
        return bool(self.allRequestedFields())

    def __contains__(self, field_name):
        """Was this field in the request?"""
        return (field_name in self.required or
                field_name in self.optional)

    def requestField(self, field_name, required=False, strict=False):
        """Request the specified field from the OpenID user

        @param field_name: the unqualified simple registration field name
        @type field_name: str

        @param required: whether the given field should be presented
            to the user as being a required to successfully complete
            the request

        @param strict: whether to raise an exception when a field is
            added to a request more than once

        @raise ValueError: when the field requested is not a simple
            registration field or strict is set and the field was
            requested more than once
        """
        checkFieldName(field_name)

        if strict:
            if field_name in self.required or field_name in self.optional:
                raise ValueError('That field has already been requested')
        else:
            if field_name in self.required:
                return

            if field_name in self.optional:
                if required:
                    self.optional.remove(field_name)
                else:
                    return

        if required:
            self.required.append(field_name)
        else:
            self.optional.append(field_name)

    def requestFields(self, field_names, required=False, strict=False):
        """Add the given list of fields to the request

        @param field_names: The simple registration data fields to request
        @type field_names: [str]

        @param required: Whether these values should be presented to
            the user as required

        @param strict: whether to raise an exception when a field is
            added to a request more than once

        @raise ValueError: when a field requested is not a simple
            registration field or strict is set and a field was
            requested more than once
        """
        if isinstance(field_names, basestring):
            raise TypeError('Fields should be passed as a list of '
                            'strings (not %r)' % (type(field_names),))

        for field_name in field_names:
            self.requestField(field_name, required, strict=strict)

    def getExtensionArgs(self):
        """Get a dictionary of unqualified simple registration
        arguments representing this request.

        This method is essentially the inverse of
        C{L{parseExtensionArgs}}. This method serializes the simple
        registration request fields.

        @rtype: {str:str}
        """
        args = {}

        if self.required:
            args['required'] = ','.join(self.required)

        if self.optional:
            args['optional'] = ','.join(self.optional)

        if self.policy_url:
            args['policy_url'] = self.policy_url

        return args

class SRegResponse(Extension):
    """Represents the data returned in a simple registration response
    inside of an OpenID C{id_res} response. This object will be
    created by the OpenID server, added to the C{id_res} response
    object, and then extracted from the C{id_res} message by the
    Consumer.

    @ivar data: The simple registration data, keyed by the unqualified
        simple registration name of the field (i.e. nickname is keyed
        by C{'nickname'})

    @ivar ns_uri: The URI under which the simple registration data was
        stored in the response message.

    @group Server: extractResponse
    @group Consumer: fromSuccessResponse
    @group Read-only dictionary interface: keys, iterkeys, items, iteritems,
        __iter__, get, __getitem__, keys, has_key
    """

    ns_alias = 'sreg'

    def __init__(self, data=None, sreg_ns_uri=ns_uri):
        Extension.__init__(self)
        if data is None:
            self.data = {}
        else:
            self.data = data

        self.ns_uri = sreg_ns_uri

    def extractResponse(cls, request, data):
        """Take a C{L{SRegRequest}} and a dictionary of simple
        registration values and create a C{L{SRegResponse}}
        object containing that data.

        @param request: The simple registration request object
        @type request: SRegRequest

        @param data: The simple registration data for this
            response, as a dictionary from unqualified simple
            registration field name to string (unicode) value. For
            instance, the nickname should be stored under the key
            'nickname'.
        @type data: {str:str}

        @returns: a simple registration response object
        @rtype: SRegResponse
        """
        self = cls()
        self.ns_uri = request.ns_uri
        for field in request.allRequestedFields():
            value = data.get(field)
            if value is not None:
                self.data[field] = value
        return self

    extractResponse = classmethod(extractResponse)

    # Assign getSRegArgs to a static method so that it can be
    # overridden for testing
    _getSRegNS = staticmethod(getSRegNS)

    def fromSuccessResponse(cls, success_response, signed_only=True):
        """Create a C{L{SRegResponse}} object from a successful OpenID
        library response
        (C{L{openid.consumer.consumer.SuccessResponse}}) response
        message

        @param success_response: A SuccessResponse from consumer.complete()
        @type success_response: C{L{openid.consumer.consumer.SuccessResponse}}

        @param signed_only: Whether to process only data that was
            signed in the id_res message from the server.
        @type signed_only: bool

        @rtype: SRegResponse
        @returns: A simple registration response containing the data
            that was supplied with the C{id_res} response.
        """
        self = cls()
        self.ns_uri = self._getSRegNS(success_response.message)
        if signed_only:
            args = success_response.getSignedNS(self.ns_uri)
        else:
            args = success_response.message.getArgs(self.ns_uri)

        for field_name in data_fields:
            if field_name in args:
                self.data[field_name] = args[field_name]

        return self

    fromSuccessResponse = classmethod(fromSuccessResponse)

    def getExtensionArgs(self):
        """Get the fields to put in the simple registration namespace
        when adding them to an id_res message.

        @see: openid.extension
        """
        return self.data

    # Read-only dictionary interface
    def get(self, field_name, default=None):
        """Like dict.get, except that it checks that the field name is
        defined by the simple registration specification"""
        checkFieldName(field_name)
        return self.data.get(field_name, default)

    def items(self):
        """All of the data values in this simple registration response
        """
        return self.data.items()

    def iteritems(self):
        return self.data.iteritems()

    def keys(self):
        return self.data.keys()

    def iterkeys(self):
        return self.data.iterkeys()

    def has_key(self, key):
        return key in self

    def __contains__(self, field_name):
        checkFieldName(field_name)
        return field_name in self.data

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, field_name):
        checkFieldName(field_name)
        return self.data[field_name]

    def __nonzero__(self):
        return bool(self.data)

########NEW FILE########
__FILENAME__ = fetchers
# -*- test-case-name: openid.test.test_fetchers -*-
"""
This module contains the HTTP fetcher interface and several implementations.
"""

__all__ = ['fetch', 'getDefaultFetcher', 'setDefaultFetcher', 'HTTPResponse',
           'HTTPFetcher', 'createHTTPFetcher', 'HTTPFetchingError',
           'HTTPError']

import urllib2
import time
import cStringIO
import sys

import openid
import openid.urinorm

# Try to import httplib2 for caching support
# http://bitworking.org/projects/httplib2/
try:
    import httplib2
except ImportError:
    # httplib2 not available
    httplib2 = None

# try to import pycurl, which will let us use CurlHTTPFetcher
try:
    import pycurl
except ImportError:
    pycurl = None

USER_AGENT = "python-openid/%s (%s)" % (openid.__version__, sys.platform)

def fetch(url, body=None, headers=None):
    """Invoke the fetch method on the default fetcher. Most users
    should need only this method.

    @raises Exception: any exceptions that may be raised by the default fetcher
    """
    fetcher = getDefaultFetcher()
    return fetcher.fetch(url, body, headers)

def createHTTPFetcher():
    """Create a default HTTP fetcher instance

    prefers Curl to urllib2."""
    if pycurl is None:
        fetcher = Urllib2Fetcher()
    else:
        fetcher = CurlHTTPFetcher()

    return fetcher

# Contains the currently set HTTP fetcher. If it is set to None, the
# library will call createHTTPFetcher() to set it. Do not access this
# variable outside of this module.
_default_fetcher = None

def getDefaultFetcher():
    """Return the default fetcher instance
    if no fetcher has been set, it will create a default fetcher.

    @return: the default fetcher
    @rtype: HTTPFetcher
    """
    global _default_fetcher

    if _default_fetcher is None:
        setDefaultFetcher(createHTTPFetcher())

    return _default_fetcher

def setDefaultFetcher(fetcher, wrap_exceptions=True):
    """Set the default fetcher

    @param fetcher: The fetcher to use as the default HTTP fetcher
    @type fetcher: HTTPFetcher

    @param wrap_exceptions: Whether to wrap exceptions thrown by the
        fetcher wil HTTPFetchingError so that they may be caught
        easier. By default, exceptions will be wrapped. In general,
        unwrapped fetchers are useful for debugging of fetching errors
        or if your fetcher raises well-known exceptions that you would
        like to catch.
    @type wrap_exceptions: bool
    """
    global _default_fetcher
    if fetcher is None or not wrap_exceptions:
        _default_fetcher = fetcher
    else:
        _default_fetcher = ExceptionWrappingFetcher(fetcher)

def usingCurl():
    """Whether the currently set HTTP fetcher is a Curl HTTP fetcher."""
    return isinstance(getDefaultFetcher(), CurlHTTPFetcher)

class HTTPResponse(object):
    """XXX document attributes"""
    headers = None
    status = None
    body = None
    final_url = None

    def __init__(self, final_url=None, status=None, headers=None, body=None):
        self.final_url = final_url
        self.status = status
        self.headers = headers
        self.body = body

    def __repr__(self):
        return "<%s status %s for %s>" % (self.__class__.__name__,
                                          self.status,
                                          self.final_url)

class HTTPFetcher(object):
    """
    This class is the interface for openid HTTP fetchers.  This
    interface is only important if you need to write a new fetcher for
    some reason.
    """

    def fetch(self, url, body=None, headers=None):
        """
        This performs an HTTP POST or GET, following redirects along
        the way. If a body is specified, then the request will be a
        POST. Otherwise, it will be a GET.


        @param headers: HTTP headers to include with the request
        @type headers: {str:str}

        @return: An object representing the server's HTTP response. If
            there are network or protocol errors, an exception will be
            raised. HTTP error responses, like 404 or 500, do not
            cause exceptions.

        @rtype: L{HTTPResponse}

        @raise Exception: Different implementations will raise
            different errors based on the underlying HTTP library.
        """
        raise NotImplementedError

def _allowedURL(url):
    return url.startswith('http://') or url.startswith('https://')

class HTTPFetchingError(Exception):
    """Exception that is wrapped around all exceptions that are raised
    by the underlying fetcher when using the ExceptionWrappingFetcher

    @ivar why: The exception that caused this exception
    """
    def __init__(self, why=None):
        Exception.__init__(self, why)
        self.why = why

class ExceptionWrappingFetcher(HTTPFetcher):
    """Fetcher that wraps another fetcher, causing all exceptions

    @cvar uncaught_exceptions: Exceptions that should be exposed to the
        user if they are raised by the fetch call
    """

    uncaught_exceptions = (SystemExit, KeyboardInterrupt, MemoryError)

    def __init__(self, fetcher):
        self.fetcher = fetcher

    def fetch(self, *args, **kwargs):
        try:
            return self.fetcher.fetch(*args, **kwargs)
        except self.uncaught_exceptions:
            raise
        except:
            import logging
            logging.exception('qwert2')
            exc_cls, exc_inst = sys.exc_info()[:2]
            if exc_inst is None:
                # string exceptions
                exc_inst = exc_cls

            raise HTTPFetchingError(why=exc_inst)

class Urllib2Fetcher(HTTPFetcher):
    """An C{L{HTTPFetcher}} that uses urllib2.
    """

    # Parameterized for the benefit of testing frameworks, see
    # http://trac.openidenabled.com/trac/ticket/85
    urlopen = staticmethod(urllib2.urlopen)

    def fetch(self, url, body=None, headers=None):
        if not _allowedURL(url):
            raise ValueError('Bad URL scheme: %r' % (url,))

        if headers is None:
            headers = {}

        headers.setdefault(
            'User-Agent',
            "%s Python-urllib/%s" % (USER_AGENT, urllib2.__version__,))

        req = urllib2.Request(url, data=body, headers=headers)
        try:
            f = self.urlopen(req)
            try:
                return self._makeResponse(f)
            finally:
                f.close()
        except urllib2.HTTPError, why:
            try:
                return self._makeResponse(why)
            finally:
                why.close()

    def _makeResponse(self, urllib2_response):
        resp = HTTPResponse()
        resp.body = urllib2_response.read()
        resp.final_url = urllib2_response.geturl()
        resp.headers = dict(urllib2_response.info().items())

        if hasattr(urllib2_response, 'code'):
            resp.status = urllib2_response.code
        else:
            resp.status = 200

        return resp

class HTTPError(HTTPFetchingError):
    """
    This exception is raised by the C{L{CurlHTTPFetcher}} when it
    encounters an exceptional situation fetching a URL.
    """
    pass

# XXX: define what we mean by paranoid, and make sure it is.
class CurlHTTPFetcher(HTTPFetcher):
    """
    An C{L{HTTPFetcher}} that uses pycurl for fetching.
    See U{http://pycurl.sourceforge.net/}.
    """
    ALLOWED_TIME = 20 # seconds

    def __init__(self):
        HTTPFetcher.__init__(self)
        if pycurl is None:
            raise RuntimeError('Cannot find pycurl library')

    def _parseHeaders(self, header_file):
        header_file.seek(0)

        # Remove the status line from the beginning of the input
        unused_http_status_line = header_file.readline()
        lines = [line.strip() for line in header_file]

        # and the blank line from the end
        empty_line = lines.pop()
        if empty_line:
            raise HTTPError("No blank line at end of headers: %r" % (line,))

        headers = {}
        for line in lines:
            try:
                name, value = line.split(':', 1)
            except ValueError:
                raise HTTPError(
                    "Malformed HTTP header line in response: %r" % (line,))

            value = value.strip()

            # HTTP headers are case-insensitive
            name = name.lower()
            headers[name] = value

        return headers

    def _checkURL(self, url):
        # XXX: document that this can be overridden to match desired policy
        # XXX: make sure url is well-formed and routeable
        return _allowedURL(url)

    def fetch(self, url, body=None, headers=None):
        stop = int(time.time()) + self.ALLOWED_TIME
        off = self.ALLOWED_TIME

        if headers is None:
            headers = {}

        headers.setdefault('User-Agent',
                           "%s %s" % (USER_AGENT, pycurl.version,))

        header_list = []
        if headers is not None:
            for header_name, header_value in headers.iteritems():
                header_list.append('%s: %s' % (header_name, header_value))

        c = pycurl.Curl()
        try:
            c.setopt(pycurl.NOSIGNAL, 1)

            if header_list:
                c.setopt(pycurl.HTTPHEADER, header_list)

            # Presence of a body indicates that we should do a POST
            if body is not None:
                c.setopt(pycurl.POST, 1)
                c.setopt(pycurl.POSTFIELDS, body)

            while off > 0:
                if not self._checkURL(url):
                    raise HTTPError("Fetching URL not allowed: %r" % (url,))

                data = cStringIO.StringIO()
                response_header_data = cStringIO.StringIO()
                c.setopt(pycurl.WRITEFUNCTION, data.write)
                c.setopt(pycurl.HEADERFUNCTION, response_header_data.write)
                c.setopt(pycurl.TIMEOUT, off)
                c.setopt(pycurl.URL, openid.urinorm.urinorm(url))

                c.perform()

                response_headers = self._parseHeaders(response_header_data)
                code = c.getinfo(pycurl.RESPONSE_CODE)
                if code in [301, 302, 303, 307]:
                    url = response_headers.get('location')
                    if url is None:
                        raise HTTPError(
                            'Redirect (%s) returned without a location' % code)

                    # Redirects are always GETs
                    c.setopt(pycurl.POST, 0)

                    # There is no way to reset POSTFIELDS to empty and
                    # reuse the connection, but we only use it once.
                else:
                    resp = HTTPResponse()
                    resp.headers = response_headers
                    resp.status = code
                    resp.final_url = url
                    resp.body = data.getvalue()
                    return resp

                off = stop - int(time.time())

            raise HTTPError("Timed out fetching: %r" % (url,))
        finally:
            c.close()

class HTTPLib2Fetcher(HTTPFetcher):
    """A fetcher that uses C{httplib2} for performing HTTP
    requests. This implementation supports HTTP caching.

    @see: http://bitworking.org/projects/httplib2/
    """

    def __init__(self, cache=None):
        """@param cache: An object suitable for use as an C{httplib2}
            cache. If a string is passed, it is assumed to be a
            directory name.
        """
        if httplib2 is None:
            raise RuntimeError('Cannot find httplib2 library. '
                               'See http://bitworking.org/projects/httplib2/')

        super(HTTPLib2Fetcher, self).__init__()

        # An instance of the httplib2 object that performs HTTP requests
        self.httplib2 = httplib2.Http(cache)

        # We want httplib2 to raise exceptions for errors, just like
        # the other fetchers.
        self.httplib2.force_exception_to_status_code = False

    def fetch(self, url, body=None, headers=None):
        """Perform an HTTP request

        @raises Exception: Any exception that can be raised by httplib2

        @see: C{L{HTTPFetcher.fetch}}
        """
        if body:
            method = 'POST'
        else:
            method = 'GET'

        # httplib2 doesn't check to make sure that the URL's scheme is
        # 'http' so we do it here.
        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError('URL is not a HTTP URL: %r' % (url,))

        httplib2_response, content = self.httplib2.request(
            url, method, body=body, headers=headers)

        # Translate the httplib2 response to our HTTP response abstraction

        # When a 400 is returned, there is no "content-location"
        # header set. This seems like a bug to me. I can't think of a
        # case where we really care about the final URL when it is an
        # error response, but being careful about it can't hurt.
        try:
            final_url = httplib2_response['content-location']
        except KeyError:
            # We're assuming that no redirects occurred
            assert not httplib2_response.previous

            # And this should never happen for a successful response
            assert httplib2_response.status != 200
            final_url = url

        return HTTPResponse(
            body=content,
            final_url=final_url,
            headers=dict(httplib2_response.items()),
            status=httplib2_response.status,
            )

########NEW FILE########
__FILENAME__ = kvform
__all__ = ['seqToKV', 'kvToSeq', 'dictToKV', 'kvToDict']

from openid import oidutil

import types

def seqToKV(seq, strict=False):
    """Represent a sequence of pairs of strings as newline-terminated
    key:value pairs. The pairs are generated in the order given.

    @param seq: The pairs
    @type seq: [(str, (unicode|str))]

    @return: A string representation of the sequence
    @rtype: str
    """
    def err(msg):
        formatted = 'seqToKV warning: %s: %r' % (msg, seq)
        if strict:
            raise ValueError(formatted)
        else:
            oidutil.log(formatted)

    lines = []
    for k, v in seq:
        if isinstance(k, types.StringType):
            k = k.decode('UTF8')
        elif not isinstance(k, types.UnicodeType):
            err('Converting key to string: %r' % k)
            k = str(k)

        if '\n' in k:
            raise ValueError(
                'Invalid input for seqToKV: key contains newline: %r' % (k,))

        if ':' in k:
            raise ValueError(
                'Invalid input for seqToKV: key contains colon: %r' % (k,))

        if k.strip() != k:
            err('Key has whitespace at beginning or end: %r' % k)

        if isinstance(v, types.StringType):
            v = v.decode('UTF8')
        elif not isinstance(v, types.UnicodeType):
            err('Converting value to string: %r' % v)
            v = str(v)

        if '\n' in v:
            raise ValueError(
                'Invalid input for seqToKV: value contains newline: %r' % (v,))

        if v.strip() != v:
            err('Value has whitespace at beginning or end: %r' % v)

        lines.append(k + ':' + v + '\n')

    return ''.join(lines).encode('UTF8')

def kvToSeq(data, strict=False):
    """

    After one parse, seqToKV and kvToSeq are inverses, with no warnings::

        seq = kvToSeq(s)
        seqToKV(kvToSeq(seq)) == seq
    """
    def err(msg):
        formatted = 'kvToSeq warning: %s: %r' % (msg, data)
        if strict:
            raise ValueError(formatted)
        else:
            oidutil.log(formatted)

    lines = data.split('\n')
    if lines[-1]:
        err('Does not end in a newline')
    else:
        del lines[-1]

    pairs = []
    line_num = 0
    for line in lines:
        line_num += 1

        # Ignore blank lines
        if not line.strip():
            continue

        pair = line.split(':', 1)
        if len(pair) == 2:
            k, v = pair
            k_s = k.strip()
            if k_s != k:
                fmt = ('In line %d, ignoring leading or trailing '
                       'whitespace in key %r')
                err(fmt % (line_num, k))

            if not k_s:
                err('In line %d, got empty key' % (line_num,))

            v_s = v.strip()
            if v_s != v:
                fmt = ('In line %d, ignoring leading or trailing '
                       'whitespace in value %r')
                err(fmt % (line_num, v))

            pairs.append((k_s.decode('UTF8'), v_s.decode('UTF8')))
        else:
            err('Line %d does not contain a colon' % line_num)

    return pairs

def dictToKV(d):
    seq = d.items()
    seq.sort()
    return seqToKV(seq)

def kvToDict(s):
    return dict(kvToSeq(s))

########NEW FILE########
__FILENAME__ = message
"""Extension argument processing code
"""
__all__ = ['Message', 'NamespaceMap', 'no_default', 'registerNamespaceAlias',
           'OPENID_NS', 'BARE_NS', 'OPENID1_NS', 'OPENID2_NS', 'SREG_URI',
           'IDENTIFIER_SELECT']

import copy
import warnings
import urllib

from openid import oidutil
from openid import kvform
try:
    ElementTree = oidutil.importElementTree()
except ImportError:
    # No elementtree found, so give up, but don't fail to import,
    # since we have fallbacks.
    ElementTree = None

# This doesn't REALLY belong here, but where is better?
IDENTIFIER_SELECT = 'http://specs.openid.net/auth/2.0/identifier_select'

# URI for Simple Registration extension, the only commonly deployed
# OpenID 1.x extension, and so a special case
SREG_URI = 'http://openid.net/sreg/1.0'

# The OpenID 1.X namespace URI
OPENID1_NS = 'http://openid.net/signon/1.0'

# The OpenID 2.0 namespace URI
OPENID2_NS = 'http://specs.openid.net/auth/2.0'

# The namespace consisting of pairs with keys that are prefixed with
# "openid."  but not in another namespace.
NULL_NAMESPACE = oidutil.Symbol('Null namespace')

# The null namespace, when it is an allowed OpenID namespace
OPENID_NS = oidutil.Symbol('OpenID namespace')

# The top-level namespace, excluding all pairs with keys that start
# with "openid."
BARE_NS = oidutil.Symbol('Bare namespace')

# Limit, in bytes, of identity provider and return_to URLs, including
# response payload.  See OpenID 1.1 specification, Appendix D.
OPENID1_URL_LIMIT = 2047

# All OpenID protocol fields.  Used to check namespace aliases.
OPENID_PROTOCOL_FIELDS = [
    'ns', 'mode', 'error', 'return_to', 'contact', 'reference',
    'signed', 'assoc_type', 'session_type', 'dh_modulus', 'dh_gen',
    'dh_consumer_public', 'claimed_id', 'identity', 'realm',
    'invalidate_handle', 'op_endpoint', 'response_nonce', 'sig',
    'assoc_handle', 'trust_root', 'openid',
    ]

class UndefinedOpenIDNamespace(ValueError):
    """Raised if the generic OpenID namespace is accessed when there
    is no OpenID namespace set for this message."""

# Sentinel used for Message implementation to indicate that getArg
# should raise an exception instead of returning a default.
no_default = object()

# Global namespace / alias registration map.  See
# registerNamespaceAlias.
registered_aliases = {}

class NamespaceAliasRegistrationError(Exception):
    """
    Raised when an alias or namespace URI has already been registered.
    """
    pass

def registerNamespaceAlias(namespace_uri, alias):
    """
    Registers a (namespace URI, alias) mapping in a global namespace
    alias map.  Raises NamespaceAliasRegistrationError if either the
    namespace URI or alias has already been registered with a
    different value.  This function is required if you want to use a
    namespace with an OpenID 1 message.
    """
    global registered_aliases

    if registered_aliases.get(alias) == namespace_uri:
        return

    if namespace_uri in registered_aliases.values():
        raise NamespaceAliasRegistrationError, \
              'Namespace uri %r already registered' % (namespace_uri,)

    if alias in registered_aliases:
        raise NamespaceAliasRegistrationError, \
              'Alias %r already registered' % (alias,)

    registered_aliases[alias] = namespace_uri

class Message(object):
    """
    In the implementation of this object, None represents the global
    namespace as well as a namespace with no key.

    @cvar namespaces: A dictionary specifying specific
        namespace-URI to alias mappings that should be used when
        generating namespace aliases.

    @ivar ns_args: two-level dictionary of the values in this message,
        grouped by namespace URI. The first level is the namespace
        URI.
    """

    allowed_openid_namespaces = [OPENID1_NS, OPENID2_NS]

    def __init__(self, openid_namespace=None):
        """Create an empty Message"""
        self.args = {}
        self.namespaces = NamespaceMap()
        if openid_namespace is None:
            self._openid_ns_uri = None
        else:
            self.setOpenIDNamespace(openid_namespace)

    def fromPostArgs(cls, args):
        """Construct a Message containing a set of POST arguments"""
        self = cls()

        # Partition into "openid." args and bare args
        openid_args = {}
        for key, value in args.iteritems():
            if isinstance(value, list):
                raise TypeError("query dict must have one value for each key, "
                                "not lists of values.  Query is %r" % (args,))


            try:
                prefix, rest = key.split('.', 1)
            except ValueError:
                prefix = None

            if prefix != 'openid':
                self.args[(BARE_NS, key)] = value
            else:
                openid_args[rest] = value

        self._fromOpenIDArgs(openid_args)

        return self

    fromPostArgs = classmethod(fromPostArgs)

    def fromOpenIDArgs(cls, openid_args):
        """Construct a Message from a parsed KVForm message"""
        self = cls()
        self._fromOpenIDArgs(openid_args)
        return self

    fromOpenIDArgs = classmethod(fromOpenIDArgs)

    def _fromOpenIDArgs(self, openid_args):
        global registered_aliases

        ns_args = []

        # Resolve namespaces
        for rest, value in openid_args.iteritems():
            try:
                ns_alias, ns_key = rest.split('.', 1)
            except ValueError:
                ns_alias = NULL_NAMESPACE
                ns_key = rest

            if ns_alias == 'ns':
                self.namespaces.addAlias(value, ns_key)
            elif ns_alias == NULL_NAMESPACE and ns_key == 'ns':
                # null namespace
                self.namespaces.addAlias(value, NULL_NAMESPACE)
            else:
                ns_args.append((ns_alias, ns_key, value))

        # Ensure that there is an OpenID namespace definition
        openid_ns_uri = self.namespaces.getNamespaceURI(NULL_NAMESPACE)
        if openid_ns_uri is None:
            openid_ns_uri = OPENID1_NS

        self.setOpenIDNamespace(openid_ns_uri)

        # Actually put the pairs into the appropriate namespaces
        for (ns_alias, ns_key, value) in ns_args:
            ns_uri = self.namespaces.getNamespaceURI(ns_alias)
            if ns_uri is None:
                # Only try to map an alias to a default if it's an
                # OpenID 1.x message.
                if openid_ns_uri == OPENID1_NS:
                    for _alias, _uri in registered_aliases.iteritems():
                        if _alias == ns_alias:
                            ns_uri = _uri
                            break

                if ns_uri is None:
                    ns_uri = openid_ns_uri
                    ns_key = '%s.%s' % (ns_alias, ns_key)
                else:
                    self.namespaces.addAlias(ns_uri, ns_alias)

            self.setArg(ns_uri, ns_key, value)

    def setOpenIDNamespace(self, openid_ns_uri):
        if openid_ns_uri not in self.allowed_openid_namespaces:
            raise ValueError('Invalid null namespace: %r' % (openid_ns_uri,))

        self.namespaces.addAlias(openid_ns_uri, NULL_NAMESPACE)
        self._openid_ns_uri = openid_ns_uri

    def getOpenIDNamespace(self):
        return self._openid_ns_uri

    def isOpenID1(self):
        return self.getOpenIDNamespace() == OPENID1_NS

    def isOpenID2(self):
        return self.getOpenIDNamespace() == OPENID2_NS

    def fromKVForm(cls, kvform_string):
        """Create a Message from a KVForm string"""
        return cls.fromOpenIDArgs(kvform.kvToDict(kvform_string))

    fromKVForm = classmethod(fromKVForm)

    def copy(self):
        return copy.deepcopy(self)

    def toPostArgs(self):
        """Return all arguments with openid. in front of namespaced arguments.
        """
        args = {}

        # Add namespace definitions to the output
        for ns_uri, alias in self.namespaces.iteritems():
            if alias == NULL_NAMESPACE:
                if ns_uri != OPENID1_NS:
                    args['openid.ns'] = ns_uri
                else:
                    # drop the default null namespace definition. This
                    # potentially changes a message since we have no
                    # way of knowing whether it was explicitly
                    # specified at the time the message was
                    # parsed. The vast majority of the time, this will
                    # be the right thing to do. Possibly this could
                    # look in the signed list.
                    pass
            else:
                if self.getOpenIDNamespace() != OPENID1_NS:
                    ns_key = 'openid.ns.' + alias
                    args[ns_key] = ns_uri

        for (ns_uri, ns_key), value in self.args.iteritems():
            key = self.getKey(ns_uri, ns_key)
            args[key] = value

        return args

    def toArgs(self):
        """Return all namespaced arguments, failing if any
        non-namespaced arguments exist."""
        # FIXME - undocumented exception
        post_args = self.toPostArgs()
        kvargs = {}
        for k, v in post_args.iteritems():
            if not k.startswith('openid.'):
                raise ValueError(
                    'This message can only be encoded as a POST, because it '
                    'contains arguments that are not prefixed with "openid."')
            else:
                kvargs[k[7:]] = v

        return kvargs

    def toFormMarkup(self, action_url, form_tag_attrs=None,
                     submit_text="Continue"):
        """Generate HTML form markup that contains the values in this
        message, to be HTTP POSTed as x-www-form-urlencoded UTF-8.

        @param action_url: The URL to which the form will be POSTed
        @type action_url: str

        @param form_tag_attrs: Dictionary of attributes to be added to
            the form tag. 'accept-charset' and 'enctype' have defaults
            that can be overridden. If a value is supplied for
            'action' or 'method', it will be replaced.
        @type form_tag_attrs: {unicode: unicode}

        @param submit_text: The text that will appear on the submit
            button for this form.
        @type submit_text: unicode

        @returns: A string containing (X)HTML markup for a form that
            encodes the values in this Message object.
        @rtype: str or unicode
        """
        if ElementTree is None:
            raise RuntimeError('This function requires ElementTree.')

        form = ElementTree.Element('form')

        if form_tag_attrs:
            for name, attr in form_tag_attrs.iteritems():
                form.attrib[name] = attr

        form.attrib['action'] = action_url
        form.attrib['method'] = 'post'
        form.attrib['accept-charset'] = 'UTF-8'
        form.attrib['enctype'] = 'application/x-www-form-urlencoded'

        for name, value in self.toPostArgs().iteritems():
            attrs = {'type': 'hidden',
                     'name': name,
                     'value': value}
            form.append(ElementTree.Element('input', attrs))

        submit = ElementTree.Element(
                'input', {'type':'submit', 'value':submit_text})
        form.append(submit)

        return ElementTree.tostring(form)

    def toURL(self, base_url):
        """Generate a GET URL with the parameters in this message
        attached as query parameters."""
        return oidutil.appendArgs(base_url, self.toPostArgs())

    def toKVForm(self):
        """Generate a KVForm string that contains the parameters in
        this message. This will fail if the message contains arguments
        outside of the 'openid.' prefix.
        """
        return kvform.dictToKV(self.toArgs())

    def toURLEncoded(self):
        """Generate an x-www-urlencoded string"""
        args = self.toPostArgs().items()
        args.sort()
        return urllib.urlencode(args)

    def _fixNS(self, namespace):
        """Convert an input value into the internally used values of
        this object

        @param namespace: The string or constant to convert
        @type namespace: str or unicode or BARE_NS or OPENID_NS
        """
        if namespace == OPENID_NS:
            if self._openid_ns_uri is None:
                raise UndefinedOpenIDNamespace('OpenID namespace not set')
            else:
                namespace = self._openid_ns_uri

        if namespace != BARE_NS and type(namespace) not in [str, unicode]:
            raise TypeError(
                "Namespace must be BARE_NS, OPENID_NS or a string. got %r"
                % (namespace,))

        if namespace != BARE_NS and ':' not in namespace:
            fmt = 'OpenID 2.0 namespace identifiers SHOULD be URIs. Got %r'
            warnings.warn(fmt % (namespace,), DeprecationWarning)

            if namespace == 'sreg':
                fmt = 'Using %r instead of "sreg" as namespace'
                warnings.warn(fmt % (SREG_URI,), DeprecationWarning,)
                return SREG_URI

        return namespace

    def hasKey(self, namespace, ns_key):
        namespace = self._fixNS(namespace)
        return (namespace, ns_key) in self.args

    def getKey(self, namespace, ns_key):
        """Get the key for a particular namespaced argument"""
        namespace = self._fixNS(namespace)
        if namespace == BARE_NS:
            return ns_key

        ns_alias = self.namespaces.getAlias(namespace)

        # No alias is defined, so no key can exist
        if ns_alias is None:
            return None

        if ns_alias == NULL_NAMESPACE:
            tail = ns_key
        else:
            tail = '%s.%s' % (ns_alias, ns_key)

        return 'openid.' + tail

    def getArg(self, namespace, key, default=None):
        """Get a value for a namespaced key.

        @param namespace: The namespace in the message for this key
        @type namespace: str

        @param key: The key to get within this namespace
        @type key: str

        @param default: The value to use if this key is absent from
            this message. Using the special value
            openid.message.no_default will result in this method
            raising a KeyError instead of returning the default.

        @rtype: str or the type of default
        @raises KeyError: if default is no_default
        @raises UndefinedOpenIDNamespace: if the message has not yet
            had an OpenID namespace set
        """
        namespace = self._fixNS(namespace)
        args_key = (namespace, key)
        try:
            return self.args[args_key]
        except KeyError:
            if default is no_default:
                raise KeyError((namespace, key))
            else:
                return default

    def getArgs(self, namespace):
        """Get the arguments that are defined for this namespace URI

        @returns: mapping from namespaced keys to values
        @returntype: dict
        """
        namespace = self._fixNS(namespace)
        return dict([
            (ns_key, value)
            for ((pair_ns, ns_key), value)
            in self.args.iteritems()
            if pair_ns == namespace
            ])

    def updateArgs(self, namespace, updates):
        """Set multiple key/value pairs in one call

        @param updates: The values to set
        @type updates: {unicode:unicode}
        """
        namespace = self._fixNS(namespace)
        for k, v in updates.iteritems():
            self.setArg(namespace, k, v)

    def setArg(self, namespace, key, value):
        """Set a single argument in this namespace"""
        assert key is not None
        assert value is not None
        namespace = self._fixNS(namespace)
        self.args[(namespace, key)] = value
        if not (namespace is BARE_NS):
            self.namespaces.add(namespace)

    def delArg(self, namespace, key):
        namespace = self._fixNS(namespace)
        del self.args[(namespace, key)]

    def __repr__(self):
        return "<%s.%s %r>" % (self.__class__.__module__,
                               self.__class__.__name__,
                               self.args)

    def __eq__(self, other):
        return self.args == other.args


    def __ne__(self, other):
        return not (self == other)


    def getAliasedArg(self, aliased_key, default=None):
        if aliased_key == 'ns':
            return self.getOpenIDNamespace()

        if aliased_key.startswith('ns.'):
            uri = self.namespaces.getNamespaceURI(aliased_key[3:])
            if uri is None:
                return default
            else:
                return uri

        try:
            alias, key = aliased_key.split('.', 1)
        except ValueError:
            # need more than x values to unpack
            ns = None
        else:
            ns = self.namespaces.getNamespaceURI(alias)

        if ns is None:
            key = aliased_key
            ns = self.getOpenIDNamespace()

        return self.getArg(ns, key, default)

class NamespaceMap(object):
    """Maintains a bijective map between namespace uris and aliases.
    """
    def __init__(self):
        self.alias_to_namespace = {}
        self.namespace_to_alias = {}

    def getAlias(self, namespace_uri):
        return self.namespace_to_alias.get(namespace_uri)

    def getNamespaceURI(self, alias):
        return self.alias_to_namespace.get(alias)

    def iterNamespaceURIs(self):
        """Return an iterator over the namespace URIs"""
        return iter(self.namespace_to_alias)

    def iterAliases(self):
        """Return an iterator over the aliases"""
        return iter(self.alias_to_namespace)

    def iteritems(self):
        """Iterate over the mapping

        @returns: iterator of (namespace_uri, alias)
        """
        return self.namespace_to_alias.iteritems()

    def addAlias(self, namespace_uri, desired_alias):
        """Add an alias from this namespace URI to the desired alias
        """
        # Check that desired_alias is not an openid protocol field as
        # per the spec.
        assert desired_alias not in OPENID_PROTOCOL_FIELDS, \
               "%r is not an allowed namespace alias" % (desired_alias,)

        # Check that desired_alias does not contain a period as per
        # the spec.
        if type(desired_alias) in [str, unicode]:
            assert '.' not in desired_alias, \
                   "%r must not contain a dot" % (desired_alias,)

        # Check that there is not a namespace already defined for
        # the desired alias
        current_namespace_uri = self.alias_to_namespace.get(desired_alias)
        if (current_namespace_uri is not None
            and current_namespace_uri != namespace_uri):

            fmt = ('Cannot map %r to alias %r. '
                   '%r is already mapped to alias %r')

            msg = fmt % (
                namespace_uri,
                desired_alias,
                current_namespace_uri,
                desired_alias)
            raise KeyError(msg)

        # Check that there is not already a (different) alias for
        # this namespace URI
        alias = self.namespace_to_alias.get(namespace_uri)
        if alias is not None and alias != desired_alias:
            fmt = ('Cannot map %r to alias %r. '
                   'It is already mapped to alias %r')
            raise KeyError(fmt % (namespace_uri, desired_alias, alias))

        assert (desired_alias == NULL_NAMESPACE or
                type(desired_alias) in [str, unicode]), repr(desired_alias)
        self.alias_to_namespace[desired_alias] = namespace_uri
        self.namespace_to_alias[namespace_uri] = desired_alias
        return desired_alias

    def add(self, namespace_uri):
        """Add this namespace URI to the mapping, without caring what
        alias it ends up with"""
        # See if this namespace is already mapped to an alias
        alias = self.namespace_to_alias.get(namespace_uri)
        if alias is not None:
            return alias

        # Fall back to generating a numerical alias
        i = 0
        while True:
            alias = 'ext' + str(i)
            try:
                self.addAlias(namespace_uri, alias)
            except KeyError:
                i += 1
            else:
                return alias

        assert False, "Not reached"

    def isDefined(self, namespace_uri):
        return namespace_uri in self.namespace_to_alias

    def __contains__(self, namespace_uri):
        return self.isDefined(namespace_uri)

########NEW FILE########
__FILENAME__ = oidutil
"""This module contains general utility code that is used throughout
the library.

For users of this library, the C{L{log}} function is probably the most
interesting.
"""

__all__ = ['log', 'appendArgs', 'toBase64', 'fromBase64']

import binascii
import sys
import urlparse

from urllib import urlencode

elementtree_modules = [
    'lxml.etree',
    'xml.etree.cElementTree',
    'xml.etree.ElementTree',
    'cElementTree',
    'elementtree.ElementTree',
    ]

def importElementTree(module_names=None):
    """Find a working ElementTree implementation, trying the standard
    places that such a thing might show up.

    >>> ElementTree = importElementTree()

    @param module_names: The names of modules to try to use as
        ElementTree. Defaults to C{L{elementtree_modules}}

    @returns: An ElementTree module
    """
    if module_names is None:
        module_names = elementtree_modules

    for mod_name in module_names:
        try:
            ElementTree = __import__(mod_name, None, None, ['unused'])
        except ImportError:
            pass
        else:
            # Make sure it can actually parse XML
            try:
                ElementTree.XML('<unused/>')
            except (SystemExit, MemoryError, AssertionError):
                raise
            except:
                why = sys.exc_info()[1]
                log('Not using ElementTree library %r because it failed to '
                    'parse a trivial document: %s' % (mod_name, why))
            else:
                return ElementTree
    else:
        raise

def log(message, level=0):
    """Handle a log message from the OpenID library.

    This implementation writes the string it to C{sys.stderr},
    followed by a newline.

    Currently, the library does not use the second parameter to this
    function, but that may change in the future.

    To install your own logging hook::

      from openid import oidutil

      def myLoggingFunction(message, level):
          ...

      oidutil.log = myLoggingFunction

    @param message: A string containing a debugging message from the
        OpenID library
    @type message: str

    @param level: The severity of the log message. This parameter is
        currently unused, but in the future, the library may indicate
        more important information with a higher level value.
    @type level: int or None

    @returns: Nothing.
    """

    sys.stderr.write(message)
    sys.stderr.write('\n')

def appendArgs(url, args):
    """Append query arguments to a HTTP(s) URL. If the URL already has
    query arguemtns, these arguments will be added, and the existing
    arguments will be preserved. Duplicate arguments will not be
    detected or collapsed (both will appear in the output).

    @param url: The url to which the arguments will be appended
    @type url: str

    @param args: The query arguments to add to the URL. If a
        dictionary is passed, the items will be sorted before
        appending them to the URL. If a sequence of pairs is passed,
        the order of the sequence will be preserved.
    @type args: A dictionary from string to string, or a sequence of
        pairs of strings.

    @returns: The URL with the parameters added
    @rtype: str
    """
    if hasattr(args, 'items'):
        args = args.items()
        args.sort()
    else:
        args = list(args)

    if len(args) == 0:
        return url

    if '?' in url:
        sep = '&'
    else:
        sep = '?'

    # Map unicode to UTF-8 if present. Do not make any assumptions
    # about the encodings of plain bytes (str).
    i = 0
    for k, v in args:
        if type(k) is not str:
            k = k.encode('UTF-8')

        if type(v) is not str:
            v = v.encode('UTF-8')

        args[i] = (k, v)
        i += 1

    return '%s%s%s' % (url, sep, urlencode(args))

def toBase64(s):
    """Represent string s as base64, omitting newlines"""
    return binascii.b2a_base64(s)[:-1]

def fromBase64(s):
    try:
        return binascii.a2b_base64(s)
    except binascii.Error, why:
        # Convert to a common exception type
        raise ValueError(why[0])

def isAbsoluteHTTPURL(url):
    """Does this URL look like a http or https URL that has a host?

    @param url: The url to check
    @type url: str

    @return: Whether the URL looks OK
    @rtype: bool
    """
    parts = urlparse.urlparse(url)
    return parts[0] in ['http', 'https'] and parts[1]

class Symbol(object):
    """This class implements an object that compares equal to others
    of the same type that have the same name. These are distict from
    str or unicode objects.
    """

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return type(self) is type(other) and self.name == other.name

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.__class__, self.name))
   
    def __repr__(self):
        return '<Symbol %s>' % (self.name,)

########NEW FILE########
__FILENAME__ = sreg
"""moved to L{openid.extensions.sreg}"""

import warnings
warnings.warn("openid.sreg has moved to openid.extensions.sreg",
              DeprecationWarning)

from openid.extensions.sreg import *

########NEW FILE########
__FILENAME__ = filestore
"""
This module contains an C{L{OpenIDStore}} implementation backed by
flat files.
"""

import string
import os
import os.path
import time

from errno import EEXIST, ENOENT

try:
    from tempfile import mkstemp
except ImportError:
    # Python < 2.3
    import warnings
    warnings.filterwarnings("ignore",
                            "tempnam is a potential security risk",
                            RuntimeWarning,
                            "openid.store.filestore")

    def mkstemp(dir):
        for _ in range(5):
            name = os.tempnam(dir)
            try:
                fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0600)
            except OSError, why:
                if why.errno != EEXIST:
                    raise
            else:
                return fd, name

        raise RuntimeError('Failed to get temp file after 5 attempts')

from openid.association import Association
from openid.store.interface import OpenIDStore
from openid.store import nonce
from openid import cryptutil, oidutil

_filename_allowed = string.ascii_letters + string.digits + '.'
try:
    # 2.4
    set
except NameError:
    try:
        # 2.3
        import sets
    except ImportError:
        # Python < 2.2
        d = {}
        for c in _filename_allowed:
            d[c] = None
        _isFilenameSafe = d.has_key
        del d
    else:
        _isFilenameSafe = sets.Set(_filename_allowed).__contains__
else:
    _isFilenameSafe = set(_filename_allowed).__contains__

def _safe64(s):
    h64 = oidutil.toBase64(cryptutil.sha1(s))
    h64 = h64.replace('+', '_')
    h64 = h64.replace('/', '.')
    h64 = h64.replace('=', '')
    return h64

def _filenameEscape(s):
    filename_chunks = []
    for c in s:
        if _isFilenameSafe(c):
            filename_chunks.append(c)
        else:
            filename_chunks.append('_%02X' % ord(c))
    return ''.join(filename_chunks)

def _removeIfPresent(filename):
    """Attempt to remove a file, returning whether the file existed at
    the time of the call.

    str -> bool
    """
    try:
        os.unlink(filename)
    except OSError, why:
        if why.errno == ENOENT:
            # Someone beat us to it, but it's gone, so that's OK
            return 0
        else:
            raise
    else:
        # File was present
        return 1

def _ensureDir(dir_name):
    """Create dir_name as a directory if it does not exist. If it
    exists, make sure that it is, in fact, a directory.

    Can raise OSError

    str -> NoneType
    """
    try:
        os.makedirs(dir_name)
    except OSError, why:
        if why.errno != EEXIST or not os.path.isdir(dir_name):
            raise

class FileOpenIDStore(OpenIDStore):
    """
    This is a filesystem-based store for OpenID associations and
    nonces.  This store should be safe for use in concurrent systems
    on both windows and unix (excluding NFS filesystems).  There are a
    couple race conditions in the system, but those failure cases have
    been set up in such a way that the worst-case behavior is someone
    having to try to log in a second time.

    Most of the methods of this class are implementation details.
    People wishing to just use this store need only pay attention to
    the C{L{__init__}} method.

    Methods of this object can raise OSError if unexpected filesystem
    conditions, such as bad permissions or missing directories, occur.
    """

    def __init__(self, directory):
        """
        Initializes a new FileOpenIDStore.  This initializes the
        nonce and association directories, which are subdirectories of
        the directory passed in.

        @param directory: This is the directory to put the store
            directories in.

        @type directory: C{str}
        """
        # Make absolute
        directory = os.path.normpath(os.path.abspath(directory))

        self.nonce_dir = os.path.join(directory, 'nonces')

        self.association_dir = os.path.join(directory, 'associations')

        # Temp dir must be on the same filesystem as the assciations
        # directory
        self.temp_dir = os.path.join(directory, 'temp')

        self.max_nonce_age = 6 * 60 * 60 # Six hours, in seconds

        self._setup()

    def _setup(self):
        """Make sure that the directories in which we store our data
        exist.

        () -> NoneType
        """
        _ensureDir(self.nonce_dir)
        _ensureDir(self.association_dir)
        _ensureDir(self.temp_dir)

    def _mktemp(self):
        """Create a temporary file on the same filesystem as
        self.association_dir.

        The temporary directory should not be cleaned if there are any
        processes using the store. If there is no active process using
        the store, it is safe to remove all of the files in the
        temporary directory.

        () -> (file, str)
        """
        fd, name = mkstemp(dir=self.temp_dir)
        try:
            file_obj = os.fdopen(fd, 'wb')
            return file_obj, name
        except:
            _removeIfPresent(name)
            raise

    def getAssociationFilename(self, server_url, handle):
        """Create a unique filename for a given server url and
        handle. This implementation does not assume anything about the
        format of the handle. The filename that is returned will
        contain the domain name from the server URL for ease of human
        inspection of the data directory.

        (str, str) -> str
        """
        if server_url.find('://') == -1:
            raise ValueError('Bad server URL: %r' % server_url)

        proto, rest = server_url.split('://', 1)
        domain = _filenameEscape(rest.split('/', 1)[0])
        url_hash = _safe64(server_url)
        if handle:
            handle_hash = _safe64(handle)
        else:
            handle_hash = ''

        filename = '%s-%s-%s-%s' % (proto, domain, url_hash, handle_hash)

        oidutil.log('filename for %s %s is %s' % (server_url, handle, filename))
        return os.path.join(self.association_dir, filename)

    def storeAssociation(self, server_url, association):
        """Store an association in the association directory.

        (str, Association) -> NoneType
        """
        association_s = association.serialize()
        filename = self.getAssociationFilename(server_url, association.handle)
        tmp_file, tmp = self._mktemp()

        try:
            try:
                tmp_file.write(association_s)
                os.fsync(tmp_file.fileno())
            finally:
                tmp_file.close()

            try:
                os.rename(tmp, filename)
            except OSError, why:
                if why.errno != EEXIST:
                    raise

                # We only expect EEXIST to happen only on Windows. It's
                # possible that we will succeed in unlinking the existing
                # file, but not in putting the temporary file in place.
                try:
                    os.unlink(filename)
                except OSError, why:
                    if why.errno == ENOENT:
                        pass
                    else:
                        raise

                # Now the target should not exist. Try renaming again,
                # giving up if it fails.
                os.rename(tmp, filename)
        except:
            # If there was an error, don't leave the temporary file
            # around.
            _removeIfPresent(tmp)
            raise

    def getAssociation(self, server_url, handle=None):
        """Retrieve an association. If no handle is specified, return
        the association with the latest expiration.

        (str, str or NoneType) -> Association or NoneType
        """
        oidutil.log('getting association %s for url %s' % (handle, server_url))
        if handle is None:
            handle = ''

        # The filename with the empty handle is a prefix of all other
        # associations for the given server URL.
        filename = self.getAssociationFilename(server_url, handle)

        if handle:
            return self._getAssociation(filename)
        else:
            association_files = os.listdir(self.association_dir)
            matching_files = []
            # strip off the path to do the comparison
            name = os.path.basename(filename)
            for association_file in association_files:
                if association_file.startswith(name):
                    matching_files.append(association_file)

            matching_associations = []
            # read the matching files and sort by time issued
            for name in matching_files:
                full_name = os.path.join(self.association_dir, name)
                association = self._getAssociation(full_name)
                if association is not None:
                    matching_associations.append(
                        (association.issued, association))

            matching_associations.sort()

            # return the most recently issued one.
            if matching_associations:
                (_, assoc) = matching_associations[-1]
                return assoc
            else:
                return None

    def _getAssociation(self, filename):
        oidutil.log('getting association from file %s' % filename)
        try:
            assoc_file = file(filename, 'rb')
        except IOError, why:
            if why.errno == ENOENT:
                # No association exists for that URL and handle
                return None
            else:
                raise
        else:
            try:
                assoc_s = assoc_file.read()
            finally:
                assoc_file.close()

            try:
                association = Association.deserialize(assoc_s)
                oidutil.log('got association %s' % association)
            except ValueError:
                _removeIfPresent(filename)
                return None

        # Clean up expired associations
        if association.getExpiresIn() == 0:
            _removeIfPresent(filename)
            oidutil.log('association expired')
            return None
        else:
            return association

    def removeAssociation(self, server_url, handle):
        """Remove an association if it exists. Do nothing if it does not.

        (str, str) -> bool
        """
        assoc = self.getAssociation(server_url, handle)
        if assoc is None:
            return 0
        else:
            filename = self.getAssociationFilename(server_url, handle)
            return _removeIfPresent(filename)

    def useNonce(self, server_url, timestamp, salt):
        """Return whether this nonce is valid.

        str -> bool
        """
        if abs(timestamp - time.time()) > nonce.SKEW:
            return False

        if server_url:
            proto, rest = server_url.split('://', 1)
        else:
            # Create empty proto / rest values for empty server_url,
            # which is part of a consumer-generated nonce.
            proto, rest = '', ''

        domain = _filenameEscape(rest.split('/', 1)[0])
        url_hash = _safe64(server_url)
        salt_hash = _safe64(salt)

        filename = '%08x-%s-%s-%s-%s' % (timestamp, proto, domain,
                                         url_hash, salt_hash)

        filename = os.path.join(self.nonce_dir, filename)
        try:
            fd = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0200)
        except OSError, why:
            if why.errno == EEXIST:
                return False
            else:
                raise
        else:
            os.close(fd)
            return True

    def _allAssocs(self):
        all_associations = []

        association_filenames = map(
            lambda filename: os.path.join(self.association_dir, filename),
            os.listdir(self.association_dir))
        for association_filename in association_filenames:
            try:
                association_file = file(association_filename, 'rb')
            except IOError, why:
                if why.errno == ENOENT:
                    oidutil.log("%s disappeared during %s._allAssocs" % (
                        association_filename, self.__class__.__name__))
                else:
                    raise
            else:
                try:
                    assoc_s = association_file.read()
                finally:
                    association_file.close()

                # Remove expired or corrupted associations
                try:
                    association = Association.deserialize(assoc_s)
                except ValueError:
                    _removeIfPresent(association_filename)
                else:
                    all_associations.append(
                        (association_filename, association))

        return all_associations

    def cleanup(self):
        """Remove expired entries from the database. This is
        potentially expensive, so only run when it is acceptable to
        take time.

        () -> NoneType
        """
        self.cleanupAssociations()
        self.cleanupNonces()

    def cleanupAssociations(self):
        removed = 0
        for assoc_filename, assoc in self._allAssocs():
            if assoc.getExpiresIn() == 0:
                _removeIfPresent(assoc_filename)
                removed += 1
        return removed

    def cleanupNonces(self):
        nonces = os.listdir(self.nonce_dir)
        now = time.time()

        removed = 0
        # Check all nonces for expiry
        for nonce_fname in nonces:
            timestamp = nonce_fname.split('-', 1)[0]
            timestamp = int(timestamp, 16)
            if abs(timestamp - now) > nonce.SKEW:
                filename = os.path.join(self.nonce_dir, nonce_fname)
                _removeIfPresent(filename)
                removed += 1
        return removed

########NEW FILE########
__FILENAME__ = interface
"""
This module contains the definition of the C{L{OpenIDStore}}
interface.
"""

class OpenIDStore(object):
    """
    This is the interface for the store objects the OpenID library
    uses.  It is a single class that provides all of the persistence
    mechanisms that the OpenID library needs, for both servers and
    consumers.

    @change: Version 2.0 removed the C{storeNonce}, C{getAuthKey}, and C{isDumb}
        methods, and changed the behavior of the C{L{useNonce}} method
        to support one-way nonces.  It added C{L{cleanupNonces}},
        C{L{cleanupAssociations}}, and C{L{cleanup}}.

    @sort: storeAssociation, getAssociation, removeAssociation,
        useNonce
    """

    def storeAssociation(self, server_url, association):
        """
        This method puts a C{L{Association
        <openid.association.Association>}} object into storage,
        retrievable by server URL and handle.


        @param server_url: The URL of the identity server that this
            association is with.  Because of the way the server
            portion of the library uses this interface, don't assume
            there are any limitations on the character set of the
            input string.  In particular, expect to see unescaped
            non-url-safe characters in the server_url field.

        @type server_url: C{str}


        @param association: The C{L{Association
            <openid.association.Association>}} to store.

        @type association: C{L{Association
            <openid.association.Association>}}


        @return: C{None}

        @rtype: C{NoneType}
        """
        raise NotImplementedError

    def getAssociation(self, server_url, handle=None):
        """
        This method returns an C{L{Association
        <openid.association.Association>}} object from storage that
        matches the server URL and, if specified, handle. It returns
        C{None} if no such association is found or if the matching
        association is expired.

        If no handle is specified, the store may return any
        association which matches the server URL.  If multiple
        associations are valid, the recommended return value for this
        method is the one most recently issued.

        This method is allowed (and encouraged) to garbage collect
        expired associations when found. This method must not return
        expired associations.


        @param server_url: The URL of the identity server to get the
            association for.  Because of the way the server portion of
            the library uses this interface, don't assume there are
            any limitations on the character set of the input string.
            In particular, expect to see unescaped non-url-safe
            characters in the server_url field.

        @type server_url: C{str}


        @param handle: This optional parameter is the handle of the
            specific association to get.  If no specific handle is
            provided, any valid association matching the server URL is
            returned.

        @type handle: C{str} or C{NoneType}


        @return: The C{L{Association
            <openid.association.Association>}} for the given identity
            server.

        @rtype: C{L{Association <openid.association.Association>}} or
            C{NoneType}
        """
        raise NotImplementedError

    def removeAssociation(self, server_url, handle):
        """
        This method removes the matching association if it's found,
        and returns whether the association was removed or not.


        @param server_url: The URL of the identity server the
            association to remove belongs to.  Because of the way the
            server portion of the library uses this interface, don't
            assume there are any limitations on the character set of
            the input string.  In particular, expect to see unescaped
            non-url-safe characters in the server_url field.

        @type server_url: C{str}


        @param handle: This is the handle of the association to
            remove.  If there isn't an association found that matches
            both the given URL and handle, then there was no matching
            handle found.

        @type handle: C{str}


        @return: Returns whether or not the given association existed.

        @rtype: C{bool} or C{int}
        """
        raise NotImplementedError

    def useNonce(self, server_url, timestamp, salt):
        """Called when using a nonce.

        This method should return C{True} if the nonce has not been
        used before, and store it for a while to make sure nobody
        tries to use the same value again.  If the nonce has already
        been used or the timestamp is not current, return C{False}.

        You may use L{openid.store.nonce.SKEW} for your timestamp window.

        @change: In earlier versions, round-trip nonces were used and
           a nonce was only valid if it had been previously stored
           with C{storeNonce}.  Version 2.0 uses one-way nonces,
           requiring a different implementation here that does not
           depend on a C{storeNonce} call.  (C{storeNonce} is no
           longer part of the interface.)

        @param server_url: The URL of the server from which the nonce
            originated.

        @type server_url: C{str}

        @param timestamp: The time that the nonce was created (to the
            nearest second), in seconds since January 1 1970 UTC.
        @type timestamp: C{int}

        @param salt: A random string that makes two nonces from the
            same server issued during the same second unique.
        @type salt: str

        @return: Whether or not the nonce was valid.

        @rtype: C{bool}
        """
        raise NotImplementedError

    def cleanupNonces(self):
        """Remove expired nonces from the store.

        Discards any nonce from storage that is old enough that its
        timestamp would not pass L{useNonce}.

        This method is not called in the normal operation of the
        library.  It provides a way for store admins to keep
        their storage from filling up with expired data.

        @return: the number of nonces expired.
        @returntype: int
        """
        raise NotImplementedError

    def cleanupAssociations(self):
        """Remove expired associations from the store.

        This method is not called in the normal operation of the
        library.  It provides a way for store admins to keep
        their storage from filling up with expired data.

        @return: the number of associations expired.
        @returntype: int
        """
        raise NotImplementedError

    def cleanup(self):
        """Shortcut for C{L{cleanupNonces}()}, C{L{cleanupAssociations}()}.

        This method is not called in the normal operation of the
        library.  It provides a way for store admins to keep
        their storage from filling up with expired data.
        """
        return self.cleanupNonces(), self.cleanupAssociations()

########NEW FILE########
__FILENAME__ = memstore
"""A simple store using only in-process memory."""

from openid.store import nonce

import copy
import time

class ServerAssocs(object):
    def __init__(self):
        self.assocs = {}

    def set(self, assoc):
        self.assocs[assoc.handle] = assoc

    def get(self, handle):
        return self.assocs.get(handle)

    def remove(self, handle):
        try:
            del self.assocs[handle]
        except KeyError:
            return False
        else:
            return True

    def best(self):
        """Returns association with the oldest issued date.

        or None if there are no associations.
        """
        best = None
        for assoc in self.assocs.values():
            if best is None or best.issued < assoc.issued:
                best = assoc
        return best

    def cleanup(self):
        """Remove expired associations.

        @return: tuple of (removed associations, remaining associations)
        """
        remove = []
        for handle, assoc in self.assocs.iteritems():
            if assoc.getExpiresIn() == 0:
                remove.append(handle)
        for handle in remove:
            del self.assocs[handle]
        return len(remove), len(self.assocs)



class MemoryStore(object):
    """In-process memory store.

    Use for single long-running processes.  No persistence supplied.
    """
    def __init__(self):
        self.server_assocs = {}
        self.nonces = {}

    def _getServerAssocs(self, server_url):
        try:
            return self.server_assocs[server_url]
        except KeyError:
            assocs = self.server_assocs[server_url] = ServerAssocs()
            return assocs

    def storeAssociation(self, server_url, assoc):
        assocs = self._getServerAssocs(server_url)
        assocs.set(copy.deepcopy(assoc))

    def getAssociation(self, server_url, handle=None):
        assocs = self._getServerAssocs(server_url)
        if handle is None:
            return assocs.best()
        else:
            return assocs.get(handle)

    def removeAssociation(self, server_url, handle):
        assocs = self._getServerAssocs(server_url)
        return assocs.remove(handle)

    def useNonce(self, server_url, timestamp, salt):
        if abs(timestamp - time.time()) > nonce.SKEW:
            return False

        anonce = (str(server_url), int(timestamp), str(salt))
        if anonce in self.nonces:
            return False
        else:
            self.nonces[anonce] = None
            return True

    def cleanupNonces(self):
        now = time.time()
        expired = []
        for anonce in self.nonces.iterkeys():
            if abs(anonce[1] - now) > nonce.SKEW:
                # removing items while iterating over the set could be bad.
                expired.append(anonce)

        for anonce in expired:
            del self.nonces[anonce]
        return len(expired)

    def cleanupAssociations(self):
        remove_urls = []
        removed_assocs = 0
        for server_url, assocs in self.server_assocs.iteritems():
            removed, remaining = assocs.cleanup()
            removed_assocs += removed
            if not remaining:
                remove_urls.append(server_url)

        # Remove entries from server_assocs that had none remaining.
        for server_url in remove_urls:
            del self.server_assocs[server_url]
        return removed_assocs

    def __eq__(self, other):
        return ((self.server_assocs == other.server_assocs) and
                (self.nonces == other.nonces))

    def __ne__(self, other):
        return not (self == other)

########NEW FILE########
__FILENAME__ = nonce
__all__ = [
    'split',
    'mkNonce',
    'checkTimestamp',
    ]

from openid import cryptutil
from time import strptime, strftime, gmtime, time
from calendar import timegm
import string

NONCE_CHARS = string.ascii_letters + string.digits

# Keep nonces for five hours (allow five hours for the combination of
# request time and clock skew). This is probably way more than is
# necessary, but there is not much overhead in storing nonces.
SKEW = 60 * 60 * 5

time_fmt = '%Y-%m-%dT%H:%M:%SZ'
time_str_len = len('0000-00-00T00:00:00Z')

def split(nonce_string):
    """Extract a timestamp from the given nonce string

    @param nonce_string: the nonce from which to extract the timestamp
    @type nonce_string: str

    @returns: A pair of a Unix timestamp and the salt characters
    @returntype: (int, str)

    @raises ValueError: if the nonce does not start with a correctly
        formatted time string
    """
    timestamp_str = nonce_string[:time_str_len]
    try:
        timestamp = timegm(strptime(timestamp_str, time_fmt))
    except AssertionError: # Python 2.2
        timestamp = -1
    if timestamp < 0:
        raise ValueError('time out of range')
    return timestamp, nonce_string[time_str_len:]

def checkTimestamp(nonce_string, allowed_skew=SKEW, now=None):
    """Is the timestamp that is part of the specified nonce string
    within the allowed clock-skew of the current time?

    @param nonce_string: The nonce that is being checked
    @type nonce_string: str

    @param allowed_skew: How many seconds should be allowed for
        completing the request, allowing for clock skew.
    @type allowed_skew: int

    @param now: The current time, as a Unix timestamp
    @type now: int

    @returntype: bool
    @returns: Whether the timestamp is correctly formatted and within
        the allowed skew of the current time.
    """
    try:
        stamp, _ = split(nonce_string)
    except ValueError:
        return False
    else:
        if now is None:
            now = time()

        # Time after which we should not use the nonce
        past = now - allowed_skew

        # Time that is too far in the future for us to allow
        future = now + allowed_skew

        # the stamp is not too far in the future and is not too far in
        # the past
        return past <= stamp <= future

def mkNonce(when=None):
    """Generate a nonce with the current timestamp

    @param when: Unix timestamp representing the issue time of the
        nonce. Defaults to the current time.
    @type when: int

    @returntype: str
    @returns: A string that should be usable as a one-way nonce

    @see: time
    """
    salt = cryptutil.randomString(6, NONCE_CHARS)
    if when is None:
        t = gmtime()
    else:
        t = gmtime(when)

    time_str = strftime(time_fmt, t)
    return time_str + salt

########NEW FILE########
__FILENAME__ = sqlstore
"""
This module contains C{L{OpenIDStore}} implementations that use
various SQL databases to back them.

Example of how to initialize a store database::

    python -c 'from openid.store import sqlstore; import pysqlite2.dbapi2; sqlstore.SQLiteStore(pysqlite2.dbapi2.connect("cstore.db")).createTables()'
"""
import re
import time

from openid.association import Association
from openid.store.interface import OpenIDStore
from openid.store import nonce

def _inTxn(func):
    def wrapped(self, *args, **kwargs):
        return self._callInTransaction(func, self, *args, **kwargs)

    if hasattr(func, '__name__'):
        try:
            wrapped.__name__ = func.__name__[4:]
        except TypeError:
            pass

    if hasattr(func, '__doc__'):
        wrapped.__doc__ = func.__doc__

    return wrapped

class SQLStore(OpenIDStore):
    """
    This is the parent class for the SQL stores, which contains the
    logic common to all of the SQL stores.

    The table names used are determined by the class variables
    C{L{settings_table}}, C{L{associations_table}}, and
    C{L{nonces_table}}.  To change the name of the tables used, pass
    new table names into the constructor.

    To create the tables with the proper schema, see the
    C{L{createTables}} method.

    This class shouldn't be used directly.  Use one of its subclasses
    instead, as those contain the code necessary to use a specific
    database.

    All methods other than C{L{__init__}} and C{L{createTables}}
    should be considered implementation details.


    @cvar settings_table: This is the default name of the table to
        keep this store's settings in.

    @cvar associations_table: This is the default name of the table to
        keep associations in

    @cvar nonces_table: This is the default name of the table to keep
        nonces in.


    @sort: __init__, createTables
    """

    settings_table = 'oid_settings'
    associations_table = 'oid_associations'
    nonces_table = 'oid_nonces'

    def __init__(self, conn, settings_table=None, associations_table=None,
                 nonces_table=None):
        """
        This creates a new SQLStore instance.  It requires an
        established database connection be given to it, and it allows
        overriding the default table names.


        @param conn: This must be an established connection to a
            database of the correct type for the SQLStore subclass
            you're using.

        @type conn: A python database API compatible connection
            object.


        @param settings_table: This is an optional parameter to
            specify the name of the table used for this store's
            settings.  The default value is specified in
            C{L{SQLStore.settings_table}}.

        @type settings_table: C{str}


        @param associations_table: This is an optional parameter to
            specify the name of the table used for storing
            associations.  The default value is specified in
            C{L{SQLStore.associations_table}}.

        @type associations_table: C{str}


        @param nonces_table: This is an optional parameter to specify
            the name of the table used for storing nonces.  The
            default value is specified in C{L{SQLStore.nonces_table}}.

        @type nonces_table: C{str}
        """
        self.conn = conn
        self.cur = None
        self._statement_cache = {}
        self._table_names = {
            'settings': settings_table or self.settings_table,
            'associations': associations_table or self.associations_table,
            'nonces': nonces_table or self.nonces_table,
            }
        self.max_nonce_age = 6 * 60 * 60 # Six hours, in seconds

        # DB API extension: search for "Connection Attributes .Error,
        # .ProgrammingError, etc." in
        # http://www.python.org/dev/peps/pep-0249/
        if (hasattr(self.conn, 'IntegrityError') and
            hasattr(self.conn, 'OperationalError')):
            self.exceptions = self.conn

        if not (hasattr(self.exceptions, 'IntegrityError') and
                hasattr(self.exceptions, 'OperationalError')):
            raise RuntimeError("Error using database connection module "
                               "(Maybe it can't be imported?)")

    def blobDecode(self, blob):
        """Convert a blob as returned by the SQL engine into a str object.

        str -> str"""
        return blob

    def blobEncode(self, s):
        """Convert a str object into the necessary object for storing
        in the database as a blob."""
        return s

    def _getSQL(self, sql_name):
        try:
            return self._statement_cache[sql_name]
        except KeyError:
            sql = getattr(self, sql_name)
            sql %= self._table_names
            self._statement_cache[sql_name] = sql
            return sql

    def _execSQL(self, sql_name, *args):
        sql = self._getSQL(sql_name)
        self.cur.execute(sql, args)

    def __getattr__(self, attr):
        # if the attribute starts with db_, use a default
        # implementation that looks up the appropriate SQL statement
        # as an attribute of this object and executes it.
        if attr[:3] == 'db_':
            sql_name = attr[3:] + '_sql'
            def func(*args):
                return self._execSQL(sql_name, *args)
            setattr(self, attr, func)
            return func
        else:
            raise AttributeError('Attribute %r not found' % (attr,))

    def _callInTransaction(self, func, *args, **kwargs):
        """Execute the given function inside of a transaction, with an
        open cursor. If no exception is raised, the transaction is
        comitted, otherwise it is rolled back."""
        # No nesting of transactions
        self.conn.rollback()

        try:
            self.cur = self.conn.cursor()
            try:
                ret = func(*args, **kwargs)
            finally:
                self.cur.close()
                self.cur = None
        except:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

        return ret

    def txn_createTables(self):
        """
        This method creates the database tables necessary for this
        store to work.  It should not be called if the tables already
        exist.
        """
        self.db_create_nonce()
        self.db_create_assoc()
        self.db_create_settings()

    createTables = _inTxn(txn_createTables)

    def txn_storeAssociation(self, server_url, association):
        """Set the association for the server URL.

        Association -> NoneType
        """
        a = association
        self.db_set_assoc(
            server_url,
            a.handle,
            self.blobEncode(a.secret),
            a.issued,
            a.lifetime,
            a.assoc_type)

    storeAssociation = _inTxn(txn_storeAssociation)

    def txn_getAssociation(self, server_url, handle=None):
        """Get the most recent association that has been set for this
        server URL and handle.

        str -> NoneType or Association
        """
        if handle is not None:
            self.db_get_assoc(server_url, handle)
        else:
            self.db_get_assocs(server_url)

        rows = self.cur.fetchall()
        if len(rows) == 0:
            return None
        else:
            associations = []
            for values in rows:
                assoc = Association(*values)
                assoc.secret = self.blobDecode(assoc.secret)
                if assoc.getExpiresIn() == 0:
                    self.txn_removeAssociation(server_url, assoc.handle)
                else:
                    associations.append((assoc.issued, assoc))

            if associations:
                associations.sort()
                return associations[-1][1]
            else:
                return None

    getAssociation = _inTxn(txn_getAssociation)

    def txn_removeAssociation(self, server_url, handle):
        """Remove the association for the given server URL and handle,
        returning whether the association existed at all.

        (str, str) -> bool
        """
        self.db_remove_assoc(server_url, handle)
        return self.cur.rowcount > 0 # -1 is undefined

    removeAssociation = _inTxn(txn_removeAssociation)

    def txn_useNonce(self, server_url, timestamp, salt):
        """Return whether this nonce is present, and if it is, then
        remove it from the set.

        str -> bool"""
        if abs(timestamp - time.time()) > nonce.SKEW:
            return False

        try:
            self.db_add_nonce(server_url, timestamp, salt)
        except self.exceptions.IntegrityError:
            # The key uniqueness check failed
            return False
        else:
            # The nonce was successfully added
            return True

    useNonce = _inTxn(txn_useNonce)

    def txn_cleanupNonces(self):
        self.db_clean_nonce(int(time.time()) - nonce.SKEW)
        return self.cur.rowcount

    cleanupNonces = _inTxn(txn_cleanupNonces)

    def txn_cleanupAssociations(self):
        self.db_clean_assoc(int(time.time()))
        return self.cur.rowcount

    cleanupAssociations = _inTxn(txn_cleanupAssociations)


class SQLiteStore(SQLStore):
    """
    This is an SQLite-based specialization of C{L{SQLStore}}.

    To create an instance, see C{L{SQLStore.__init__}}.  To create the
    tables it will use, see C{L{SQLStore.createTables}}.

    All other methods are implementation details.
    """

    create_nonce_sql = """
    CREATE TABLE %(nonces)s (
        server_url VARCHAR,
        timestamp INTEGER,
        salt CHAR(40),
        UNIQUE(server_url, timestamp, salt)
    );
    """

    create_assoc_sql = """
    CREATE TABLE %(associations)s
    (
        server_url VARCHAR(2047),
        handle VARCHAR(255),
        secret BLOB(128),
        issued INTEGER,
        lifetime INTEGER,
        assoc_type VARCHAR(64),
        PRIMARY KEY (server_url, handle)
    );
    """

    create_settings_sql = """
    CREATE TABLE %(settings)s
    (
        setting VARCHAR(128) UNIQUE PRIMARY KEY,
        value BLOB(20)
    );
    """

    set_assoc_sql = ('INSERT OR REPLACE INTO %(associations)s '
                     'VALUES (?, ?, ?, ?, ?, ?);')
    get_assocs_sql = ('SELECT handle, secret, issued, lifetime, assoc_type '
                      'FROM %(associations)s WHERE server_url = ?;')
    get_assoc_sql = (
        'SELECT handle, secret, issued, lifetime, assoc_type '
        'FROM %(associations)s WHERE server_url = ? AND handle = ?;')

    get_expired_sql = ('SELECT server_url '
                       'FROM %(associations)s WHERE issued + lifetime < ?;')

    remove_assoc_sql = ('DELETE FROM %(associations)s '
                        'WHERE server_url = ? AND handle = ?;')

    clean_assoc_sql = 'DELETE FROM %(associations)s WHERE issued + lifetime < ?;'

    add_nonce_sql = 'INSERT INTO %(nonces)s VALUES (?, ?, ?);'

    clean_nonce_sql = 'DELETE FROM %(nonces)s WHERE timestamp < ?;'

    def blobDecode(self, buf):
        return str(buf)

    def blobEncode(self, s):
        return buffer(s)

    def useNonce(self, *args, **kwargs):
        # Older versions of the sqlite wrapper do not raise
        # IntegrityError as they should, so we have to detect the
        # message from the OperationalError.
        try:
            return super(SQLiteStore, self).useNonce(*args, **kwargs)
        except self.exceptions.OperationalError, why:
            if re.match('^columns .* are not unique$', why[0]):
                return False
            else:
                raise

class MySQLStore(SQLStore):
    """
    This is a MySQL-based specialization of C{L{SQLStore}}.

    Uses InnoDB tables for transaction support.

    To create an instance, see C{L{SQLStore.__init__}}.  To create the
    tables it will use, see C{L{SQLStore.createTables}}.

    All other methods are implementation details.
    """

    try:
        import MySQLdb as exceptions
    except ImportError:
        exceptions = None

    create_nonce_sql = """
    CREATE TABLE %(nonces)s (
        server_url BLOB,
        timestamp INTEGER,
        salt CHAR(40),
        PRIMARY KEY (server_url(255), timestamp, salt)
    )
    TYPE=InnoDB;
    """

    create_assoc_sql = """
    CREATE TABLE %(associations)s
    (
        server_url BLOB,
        handle VARCHAR(255),
        secret BLOB,
        issued INTEGER,
        lifetime INTEGER,
        assoc_type VARCHAR(64),
        PRIMARY KEY (server_url(255), handle)
    )
    TYPE=InnoDB;
    """

    create_settings_sql = """
    CREATE TABLE %(settings)s
    (
        setting VARCHAR(128) UNIQUE PRIMARY KEY,
        value BLOB
    )
    TYPE=InnoDB;
    """

    set_assoc_sql = ('REPLACE INTO %(associations)s '
                     'VALUES (%%s, %%s, %%s, %%s, %%s, %%s);')
    get_assocs_sql = ('SELECT handle, secret, issued, lifetime, assoc_type'
                      ' FROM %(associations)s WHERE server_url = %%s;')
    get_expired_sql = ('SELECT server_url '
                       'FROM %(associations)s WHERE issued + lifetime < %%s;')

    get_assoc_sql = (
        'SELECT handle, secret, issued, lifetime, assoc_type'
        ' FROM %(associations)s WHERE server_url = %%s AND handle = %%s;')
    remove_assoc_sql = ('DELETE FROM %(associations)s '
                        'WHERE server_url = %%s AND handle = %%s;')

    clean_assoc_sql = 'DELETE FROM %(associations)s WHERE issued + lifetime < %%s;'

    add_nonce_sql = 'INSERT INTO %(nonces)s VALUES (%%s, %%s, %%s);'

    clean_nonce_sql = 'DELETE FROM %(nonces)s WHERE timestamp < %%s;'

    def blobDecode(self, blob):
        if type(blob) is str:
            # Versions of MySQLdb >= 1.2.2
            return blob
        else:
            # Versions of MySQLdb prior to 1.2.2 (as far as we can tell)
            return blob.tostring()

class PostgreSQLStore(SQLStore):
    """
    This is a PostgreSQL-based specialization of C{L{SQLStore}}.

    To create an instance, see C{L{SQLStore.__init__}}.  To create the
    tables it will use, see C{L{SQLStore.createTables}}.

    All other methods are implementation details.
    """

    try:
        import psycopg as exceptions
    except ImportError:
        # psycopg2 has the dbapi extension where the exception classes
        # are available on the connection object. A psycopg2
        # connection will use the correct exception classes because of
        # this, and a psycopg connection will fall through to use the
        # psycopg imported above.
        exceptions = None

    create_nonce_sql = """
    CREATE TABLE %(nonces)s (
        server_url VARCHAR(2047),
        timestamp INTEGER,
        salt CHAR(40),
        PRIMARY KEY (server_url, timestamp, salt)
    );
    """

    create_assoc_sql = """
    CREATE TABLE %(associations)s
    (
        server_url VARCHAR(2047),
        handle VARCHAR(255),
        secret BYTEA,
        issued INTEGER,
        lifetime INTEGER,
        assoc_type VARCHAR(64),
        PRIMARY KEY (server_url, handle),
        CONSTRAINT secret_length_constraint CHECK (LENGTH(secret) <= 128)
    );
    """

    create_settings_sql = """
    CREATE TABLE %(settings)s
    (
        setting VARCHAR(128) UNIQUE PRIMARY KEY,
        value BYTEA,
        CONSTRAINT value_length_constraint CHECK (LENGTH(value) <= 20)
    );
    """

    def db_set_assoc(self, server_url, handle, secret, issued, lifetime, assoc_type):
        """
        Set an association.  This is implemented as a method because
        REPLACE INTO is not supported by PostgreSQL (and is not
        standard SQL).
        """
        result = self.db_get_assoc(server_url, handle)
        rows = self.cur.fetchall()
        if len(rows):
            # Update the table since this associations already exists.
            return self.db_update_assoc(secret, issued, lifetime, assoc_type,
                                        server_url, handle)
        else:
            # Insert a new record because this association wasn't
            # found.
            return self.db_new_assoc(server_url, handle, secret, issued,
                                     lifetime, assoc_type)

    new_assoc_sql = ('INSERT INTO %(associations)s '
                     'VALUES (%%s, %%s, %%s, %%s, %%s, %%s);')
    update_assoc_sql = ('UPDATE %(associations)s SET '
                        'secret = %%s, issued = %%s, '
                        'lifetime = %%s, assoc_type = %%s '
                        'WHERE server_url = %%s AND handle = %%s;')
    get_assocs_sql = ('SELECT handle, secret, issued, lifetime, assoc_type'
                      ' FROM %(associations)s WHERE server_url = %%s;')
    get_expired_sql = ('SELECT server_url '
                       'FROM %(associations)s WHERE issued + lifetime < %%s;')

    get_assoc_sql = (
        'SELECT handle, secret, issued, lifetime, assoc_type'
        ' FROM %(associations)s WHERE server_url = %%s AND handle = %%s;')
    remove_assoc_sql = ('DELETE FROM %(associations)s '
                        'WHERE server_url = %%s AND handle = %%s;')

    clean_assoc_sql = 'DELETE FROM %(associations)s WHERE issued + lifetime < %%s;'

    add_nonce_sql = 'INSERT INTO %(nonces)s VALUES (%%s, %%s, %%s);'

    clean_nonce_sql = 'DELETE FROM %(nonces)s WHERE timestamp < %%s;'

    def blobEncode(self, blob):
        try:
            from psycopg2 import Binary
        except ImportError:
            from psycopg import Binary

        return Binary(blob)

########NEW FILE########
__FILENAME__ = urinorm
import re

# from appendix B of rfc 3986 (http://www.ietf.org/rfc/rfc3986.txt)
uri_pattern = r'^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?'
uri_re = re.compile(uri_pattern)


authority_pattern = r'^([^@]*@)?([^:]*)(:.*)?'
authority_re = re.compile(authority_pattern)


pct_encoded_pattern = r'%([0-9A-Fa-f]{2})'
pct_encoded_re = re.compile(pct_encoded_pattern)

try:
    unichr(0x10000)
except ValueError:
    # narrow python build
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        ]
else:
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        (0x10000, 0x1FFFD),
        (0x20000, 0x2FFFD),
        (0x30000, 0x3FFFD),
        (0x40000, 0x4FFFD),
        (0x50000, 0x5FFFD),
        (0x60000, 0x6FFFD),
        (0x70000, 0x7FFFD),
        (0x80000, 0x8FFFD),
        (0x90000, 0x9FFFD),
        (0xA0000, 0xAFFFD),
        (0xB0000, 0xBFFFD),
        (0xC0000, 0xCFFFD),
        (0xD0000, 0xDFFFD),
        (0xE1000, 0xEFFFD),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        (0xF0000, 0xFFFFD),
        (0x100000, 0x10FFFD),
        ]


_unreserved = [False] * 256
for _ in range(ord('A'), ord('Z') + 1): _unreserved[_] = True
for _ in range(ord('0'), ord('9') + 1): _unreserved[_] = True
for _ in range(ord('a'), ord('z') + 1): _unreserved[_] = True
_unreserved[ord('-')] = True
_unreserved[ord('.')] = True
_unreserved[ord('_')] = True
_unreserved[ord('~')] = True


_escapeme_re = re.compile('[%s]' % (''.join(
    map(lambda (m, n): u'%s-%s' % (unichr(m), unichr(n)),
        UCSCHAR + IPRIVATE)),))


def _pct_escape_unicode(char_match):
    c = char_match.group()
    return ''.join(['%%%X' % (ord(octet),) for octet in c.encode('utf-8')])


def _pct_encoded_replace_unreserved(mo):
    try:
        i = int(mo.group(1), 16)
        if _unreserved[i]:
            return chr(i)
        else:
            return mo.group().upper()

    except ValueError:
        return mo.group()


def _pct_encoded_replace(mo):
    try:
        return chr(int(mo.group(1), 16))
    except ValueError:
        return mo.group()


def remove_dot_segments(path):
    result_segments = []
    
    while path:
        if path.startswith('../'):
            path = path[3:]
        elif path.startswith('./'):
            path = path[2:]
        elif path.startswith('/./'):
            path = path[2:]
        elif path == '/.':
            path = '/'
        elif path.startswith('/../'):
            path = path[3:]
            if result_segments:
                result_segments.pop()
        elif path == '/..':
            path = '/'
            if result_segments:
                result_segments.pop()
        elif path == '..' or path == '.':
            path = ''
        else:
            i = 0
            if path[0] == '/':
                i = 1
            i = path.find('/', i)
            if i == -1:
                i = len(path)
            result_segments.append(path[:i])
            path = path[i:]
            
    return ''.join(result_segments)


def urinorm(uri):
    if isinstance(uri, unicode):
        uri = _escapeme_re.sub(_pct_escape_unicode, uri).encode('ascii')

    uri_mo = uri_re.match(uri)

    scheme = uri_mo.group(2)
    if scheme is None:
        raise ValueError('No scheme specified')

    scheme = scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError('Not an absolute HTTP or HTTPS URI: %r' % (uri,))

    authority = uri_mo.group(4)
    if authority is None:
        raise ValueError('Not an absolute URI: %r' % (uri,))

    authority_mo = authority_re.match(authority)
    if authority_mo is None:
        raise ValueError('URI does not have a valid authority: %r' % (uri,))

    userinfo, host, port = authority_mo.groups()

    if userinfo is None:
        userinfo = ''

    if '%' in host:
        host = host.lower()
        host = pct_encoded_re.sub(_pct_encoded_replace, host)
        host = unicode(host, 'utf-8').encode('idna')
    else:
        host = host.lower()

    if port:
        if (port == ':' or
            (scheme == 'http' and port == ':80') or
            (scheme == 'https' and port == ':443')):
            port = ''
    else:
        port = ''

    authority = userinfo + host + port

    path = uri_mo.group(5)
    path = pct_encoded_re.sub(_pct_encoded_replace_unreserved, path)
    path = remove_dot_segments(path)
    if not path:
        path = '/'

    query = uri_mo.group(6)
    if query is None:
        query = ''

    fragment = uri_mo.group(8)
    if fragment is None:
        fragment = ''

    return scheme + '://' + authority + path + query + fragment

########NEW FILE########
__FILENAME__ = accept
"""Functions for generating and parsing HTTP Accept: headers for
supporting server-directed content negotiation.
"""

def generateAcceptHeader(*elements):
    """Generate an accept header value

    [str or (str, float)] -> str
    """
    parts = []
    for element in elements:
        if type(element) is str:
            qs = "1.0"
            mtype = element
        else:
            mtype, q = element
            q = float(q)
            if q > 1 or q <= 0:
                raise ValueError('Invalid preference factor: %r' % q)

            qs = '%0.1f' % (q,)

        parts.append((qs, mtype))

    parts.sort()
    chunks = []
    for q, mtype in parts:
        if q == '1.0':
            chunks.append(mtype)
        else:
            chunks.append('%s; q=%s' % (mtype, q))

    return ', '.join(chunks)

def parseAcceptHeader(value):
    """Parse an accept header, ignoring any accept-extensions

    returns a list of tuples containing main MIME type, MIME subtype,
    and quality markdown.

    str -> [(str, str, float)]
    """
    chunks = [chunk.strip() for chunk in value.split(',')]
    accept = []
    for chunk in chunks:
        parts = [s.strip() for s in chunk.split(';')]

        mtype = parts.pop(0)
        if '/' not in mtype:
            # This is not a MIME type, so ignore the bad data
            continue

        main, sub = mtype.split('/', 1)

        for ext in parts:
            if '=' in ext:
                k, v = ext.split('=', 1)
                if k == 'q':
                    try:
                        q = float(v)
                        break
                    except ValueError:
                        # Ignore poorly formed q-values
                        pass
        else:
            q = 1.0

        accept.append((q, main, sub))

    accept.sort()
    accept.reverse()
    return [(main, sub, q) for (q, main, sub) in accept]

def matchTypes(accept_types, have_types):
    """Given the result of parsing an Accept: header, and the
    available MIME types, return the acceptable types with their
    quality markdowns.

    For example:

    >>> acceptable = parseAcceptHeader('text/html, text/plain; q=0.5')
    >>> matchTypes(acceptable, ['text/plain', 'text/html', 'image/jpeg'])
    [('text/html', 1.0), ('text/plain', 0.5)]


    Type signature: ([(str, str, float)], [str]) -> [(str, float)]
    """
    if not accept_types:
        # Accept all of them
        default = 1
    else:
        default = 0

    match_main = {}
    match_sub = {}
    for (main, sub, q) in accept_types:
        if main == '*':
            default = max(default, q)
            continue
        elif sub == '*':
            match_main[main] = max(match_main.get(main, 0), q)
        else:
            match_sub[(main, sub)] = max(match_sub.get((main, sub), 0), q)

    accepted_list = []
    order_maintainer = 0
    for mtype in have_types:
        main, sub = mtype.split('/')
        if (main, sub) in match_sub:
            q = match_sub[(main, sub)]
        else:
            q = match_main.get(main, default)

        if q:
            accepted_list.append((1 - q, order_maintainer, q, mtype))
            order_maintainer += 1

    accepted_list.sort()
    return [(mtype, q) for (_, _, q, mtype) in accepted_list]

def getAcceptable(accept_header, have_types):
    """Parse the accept header and return a list of available types in
    preferred order. If a type is unacceptable, it will not be in the
    resulting list.

    This is a convenience wrapper around matchTypes and
    parseAcceptHeader.

    (str, [str]) -> [str]
    """
    accepted = parseAcceptHeader(accept_header)
    preferred = matchTypes(accepted, have_types)
    return [mtype for (mtype, _) in preferred]

########NEW FILE########
__FILENAME__ = constants
__all__ = ['YADIS_HEADER_NAME', 'YADIS_CONTENT_TYPE', 'YADIS_ACCEPT_HEADER']
from openid.yadis.accept import generateAcceptHeader

YADIS_HEADER_NAME = 'X-XRDS-Location'
YADIS_CONTENT_TYPE = 'application/xrds+xml'

# A value suitable for using as an accept header when performing YADIS
# discovery, unless the application has special requirements
YADIS_ACCEPT_HEADER = generateAcceptHeader(
    ('text/html', 0.3),
    ('application/xhtml+xml', 0.5),
    (YADIS_CONTENT_TYPE, 1.0),
    )

########NEW FILE########
__FILENAME__ = discover
# -*- test-case-name: openid.test.test_yadis_discover -*-
__all__ = ['discover', 'DiscoveryResult', 'DiscoveryFailure']

from cStringIO import StringIO

from openid import fetchers

from openid.yadis.constants import \
     YADIS_HEADER_NAME, YADIS_CONTENT_TYPE, YADIS_ACCEPT_HEADER
from openid.yadis.parsehtml import MetaNotFound, findHTMLMeta

class DiscoveryFailure(Exception):
    """Raised when a YADIS protocol error occurs in the discovery process"""
    identity_url = None

    def __init__(self, message, http_response):
        Exception.__init__(self, message)
        self.http_response = http_response

class DiscoveryResult(object):
    """Contains the result of performing Yadis discovery on a URI"""

    # The URI that was passed to the fetcher
    request_uri = None

    # The result of following redirects from the request_uri
    normalized_uri = None

    # The URI from which the response text was returned (set to
    # None if there was no XRDS document found)
    xrds_uri = None

    # The content-type returned with the response_text
    content_type = None

    # The document returned from the xrds_uri
    response_text = None

    def __init__(self, request_uri):
        """Initialize the state of the object

        sets all attributes to None except the request_uri
        """
        self.request_uri = request_uri

    def usedYadisLocation(self):
        """Was the Yadis protocol's indirection used?"""
        return self.normalized_uri != self.xrds_uri

    def isXRDS(self):
        """Is the response text supposed to be an XRDS document?"""
        return (self.usedYadisLocation() or
                self.content_type == YADIS_CONTENT_TYPE)

def discover(uri):
    """Discover services for a given URI.

    @param uri: The identity URI as a well-formed http or https
        URI. The well-formedness and the protocol are not checked, but
        the results of this function are undefined if those properties
        do not hold.

    @return: DiscoveryResult object

    @raises Exception: Any exception that can be raised by fetching a URL with
        the given fetcher.
    @raises DiscoveryFailure: When the HTTP response does not have a 200 code.
    """
    result = DiscoveryResult(uri)
    resp = fetchers.fetch(uri, headers={'Accept': YADIS_ACCEPT_HEADER})
    if resp.status != 200:
        raise DiscoveryFailure(
            'HTTP Response status from identity URL host is not 200. '
            'Got status %r' % (resp.status,), resp)

    # Note the URL after following redirects
    result.normalized_uri = resp.final_url

    # Attempt to find out where to go to discover the document
    # or if we already have it
    result.content_type = resp.headers.get('content-type')

    result.xrds_uri = whereIsYadis(resp)

    if result.xrds_uri and result.usedYadisLocation():
        resp = fetchers.fetch(result.xrds_uri)
        if resp.status != 200:
            exc = DiscoveryFailure(
                'HTTP Response status from Yadis host is not 200. '
                'Got status %r' % (resp.status,), resp)
            exc.identity_url = result.normalized_uri
            raise exc
        result.content_type = resp.headers.get('content-type')

    result.response_text = resp.body
    return result



def whereIsYadis(resp):
    """Given a HTTPResponse, return the location of the Yadis document.

    May be the URL just retrieved, another URL, or None, if I can't
    find any.

    [non-blocking]

    @returns: str or None
    """
    # Attempt to find out where to go to discover the document
    # or if we already have it
    content_type = resp.headers.get('content-type')

    # According to the spec, the content-type header must be an exact
    # match, or else we have to look for an indirection.
    if (content_type and
        content_type.split(';', 1)[0].lower() == YADIS_CONTENT_TYPE):
        return resp.final_url
    else:
        # Try the header
        yadis_loc = resp.headers.get(YADIS_HEADER_NAME.lower())

        if not yadis_loc:
            # Parse as HTML if the header is missing.
            #
            # XXX: do we want to do something with content-type, like
            # have a whitelist or a blacklist (for detecting that it's
            # HTML)?
            try:
                yadis_loc = findHTMLMeta(StringIO(resp.body))
            except MetaNotFound:
                pass

        return yadis_loc


########NEW FILE########
__FILENAME__ = etxrd
# -*- test-case-name: yadis.test.test_etxrd -*-
"""
ElementTree interface to an XRD document.
"""

__all__ = [
    'nsTag',
    'mkXRDTag',
    'isXRDS',
    'parseXRDS',
    'getCanonicalID',
    'getYadisXRD',
    'getPriorityStrict',
    'getPriority',
    'prioSort',
    'iterServices',
    'expandService',
    'expandServices',
    ]

import sys
import random

from datetime import datetime
from time import strptime

from openid.oidutil import importElementTree
ElementTree = importElementTree()

# the different elementtree modules don't have a common exception
# model. We just want to be able to catch the exceptions that signify
# malformed XML data and wrap them, so that the other library code
# doesn't have to know which XML library we're using.
try:
    # Make the parser raise an exception so we can sniff out the type
    # of exceptions
    ElementTree.XML('> purposely malformed XML <')
except (SystemExit, MemoryError, AssertionError, ImportError):
    raise
except:
    XMLError = sys.exc_info()[0]

from openid.yadis import xri

class XRDSError(Exception):
    """An error with the XRDS document."""

    # The exception that triggered this exception
    reason = None



class XRDSFraud(XRDSError):
    """Raised when there's an assertion in the XRDS that it does not have
    the authority to make.
    """



def parseXRDS(text):
    """Parse the given text as an XRDS document.

    @return: ElementTree containing an XRDS document

    @raises XRDSError: When there is a parse error or the document does
        not contain an XRDS.
    """
    try:
        element = ElementTree.XML(text)
    except XMLError, why:
        exc = XRDSError('Error parsing document as XML')
        exc.reason = why
        raise exc
    else:
        tree = ElementTree.ElementTree(element)
        if not isXRDS(tree):
            raise XRDSError('Not an XRDS document')

        return tree

XRD_NS_2_0 = 'xri://$xrd*($v*2.0)'
XRDS_NS = 'xri://$xrds'

def nsTag(ns, t):
    return '{%s}%s' % (ns, t)

def mkXRDTag(t):
    """basestring -> basestring

    Create a tag name in the XRD 2.0 XML namespace suitable for using
    with ElementTree
    """
    return nsTag(XRD_NS_2_0, t)

def mkXRDSTag(t):
    """basestring -> basestring

    Create a tag name in the XRDS XML namespace suitable for using
    with ElementTree
    """
    return nsTag(XRDS_NS, t)

# Tags that are used in Yadis documents
root_tag = mkXRDSTag('XRDS')
service_tag = mkXRDTag('Service')
xrd_tag = mkXRDTag('XRD')
type_tag = mkXRDTag('Type')
uri_tag = mkXRDTag('URI')
expires_tag = mkXRDTag('Expires')

# Other XRD tags
canonicalID_tag = mkXRDTag('CanonicalID')

def isXRDS(xrd_tree):
    """Is this document an XRDS document?"""
    root = xrd_tree.getroot()
    return root.tag == root_tag

def getYadisXRD(xrd_tree):
    """Return the XRD element that should contain the Yadis services"""
    xrd = None

    # for the side-effect of assigning the last one in the list to the
    # xrd variable
    for xrd in xrd_tree.findall(xrd_tag):
        pass

    # There were no elements found, or else xrd would be set to the
    # last one
    if xrd is None:
        raise XRDSError('No XRD present in tree')

    return xrd

def getXRDExpiration(xrd_element, default=None):
    """Return the expiration date of this XRD element, or None if no
    expiration was specified.

    @type xrd_element: ElementTree node

    @param default: The value to use as the expiration if no
        expiration was specified in the XRD.

    @rtype: datetime.datetime

    @raises ValueError: If the xrd:Expires element is present, but its
        contents are not formatted according to the specification.
    """
    expires_element = xrd_element.find(expires_tag)
    if expires_element is None:
        return default
    else:
        expires_string = expires_element.text

        # Will raise ValueError if the string is not the expected format
        expires_time = strptime(expires_string, "%Y-%m-%dT%H:%M:%SZ")
        return datetime(*expires_time[0:6])

def getCanonicalID(iname, xrd_tree):
    """Return the CanonicalID from this XRDS document.

    @param iname: the XRI being resolved.
    @type iname: unicode

    @param xrd_tree: The XRDS output from the resolver.
    @type xrd_tree: ElementTree

    @returns: The XRI CanonicalID or None.
    @returntype: unicode or None
    """
    xrd_list = xrd_tree.findall(xrd_tag)
    xrd_list.reverse()

    try:
        canonicalID = xri.XRI(xrd_list[0].findall(canonicalID_tag)[-1].text)
    except IndexError:
        return None

    childID = canonicalID

    for xrd in xrd_list[1:]:
        # XXX: can't use rsplit until we require python >= 2.4.
        parent_sought = childID[:childID.rindex('!')]
        parent_list = [xri.XRI(c.text) for c in xrd.findall(canonicalID_tag)]
        if parent_sought not in parent_list:
            raise XRDSFraud("%r can not come from any of %s" % (parent_sought,
                                                                parent_list))

        childID = parent_sought

    root = xri.rootAuthority(iname)
    if not xri.providerIsAuthoritative(root, childID):
        raise XRDSFraud("%r can not come from root %r" % (childID, root))

    return canonicalID



class _Max(object):
    """Value that compares greater than any other value.

    Should only be used as a singleton. Implemented for use as a
    priority value for when a priority is not specified."""
    def __cmp__(self, other):
        if other is self:
            return 0

        return 1

Max = _Max()

def getPriorityStrict(element):
    """Get the priority of this element.

    Raises ValueError if the value of the priority is invalid. If no
    priority is specified, it returns a value that compares greater
    than any other value.
    """
    prio_str = element.get('priority')
    if prio_str is not None:
        prio_val = int(prio_str)
        if prio_val >= 0:
            return prio_val
        else:
            raise ValueError('Priority values must be non-negative integers')

    # Any errors in parsing the priority fall through to here
    return Max

def getPriority(element):
    """Get the priority of this element

    Returns Max if no priority is specified or the priority value is invalid.
    """
    try:
        return getPriorityStrict(element)
    except ValueError:
        return Max

def prioSort(elements):
    """Sort a list of elements that have priority attributes"""
    # Randomize the services before sorting so that equal priority
    # elements are load-balanced.
    random.shuffle(elements)

    prio_elems = [(getPriority(e), e) for e in elements]
    prio_elems.sort()
    sorted_elems = [s for (_, s) in prio_elems]
    return sorted_elems

def iterServices(xrd_tree):
    """Return an iterable over the Service elements in the Yadis XRD

    sorted by priority"""
    xrd = getYadisXRD(xrd_tree)
    return prioSort(xrd.findall(service_tag))

def sortedURIs(service_element):
    """Given a Service element, return a list of the contents of all
    URI tags in priority order."""
    return [uri_element.text for uri_element
            in prioSort(service_element.findall(uri_tag))]

def getTypeURIs(service_element):
    """Given a Service element, return a list of the contents of all
    Type tags"""
    return [type_element.text for type_element
            in service_element.findall(type_tag)]

def expandService(service_element):
    """Take a service element and expand it into an iterator of:
    ([type_uri], uri, service_element)
    """
    uris = sortedURIs(service_element)
    if not uris:
        uris = [None]

    expanded = []
    for uri in uris:
        type_uris = getTypeURIs(service_element)
        expanded.append((type_uris, uri, service_element))

    return expanded

def expandServices(service_elements):
    """Take a sorted iterator of service elements and expand it into a
    sorted iterator of:
    ([type_uri], uri, service_element)

    There may be more than one item in the resulting list for each
    service element if there is more than one URI or type for a
    service, but each triple will be unique.

    If there is no URI or Type for a Service element, it will not
    appear in the result.
    """
    expanded = []
    for service_element in service_elements:
        expanded.extend(expandService(service_element))

    return expanded

########NEW FILE########
__FILENAME__ = filters
"""This module contains functions and classes used for extracting
endpoint information out of a Yadis XRD file using the ElementTree XML
parser.
"""

__all__ = [
    'BasicServiceEndpoint',
    'mkFilter',
    'IFilter',
    'TransformFilterMaker',
    'CompoundFilter',
    ]

from openid.yadis.etxrd import expandService

class BasicServiceEndpoint(object):
    """Generic endpoint object that contains parsed service
    information, as well as a reference to the service element from
    which it was generated. If there is more than one xrd:Type or
    xrd:URI in the xrd:Service, this object represents just one of
    those pairs.

    This object can be used as a filter, because it implements
    fromBasicServiceEndpoint.

    The simplest kind of filter you can write implements
    fromBasicServiceEndpoint, which takes one of these objects.
    """
    def __init__(self, yadis_url, type_uris, uri, service_element):
        self.type_uris = type_uris
        self.yadis_url = yadis_url
        self.uri = uri
        self.service_element = service_element

    def matchTypes(self, type_uris):
        """Query this endpoint to see if it has any of the given type
        URIs. This is useful for implementing other endpoint classes
        that e.g. need to check for the presence of multiple versions
        of a single protocol.

        @param type_uris: The URIs that you wish to check
        @type type_uris: iterable of str

        @return: all types that are in both in type_uris and
            self.type_uris
        """
        return [uri for uri in type_uris if uri in self.type_uris]

    def fromBasicServiceEndpoint(endpoint):
        """Trivial transform from a basic endpoint to itself. This
        method exists to allow BasicServiceEndpoint to be used as a
        filter.

        If you are subclassing this object, re-implement this function.

        @param endpoint: An instance of BasicServiceEndpoint
        @return: The object that was passed in, with no processing.
        """
        return endpoint

    fromBasicServiceEndpoint = staticmethod(fromBasicServiceEndpoint)

class IFilter(object):
    """Interface for Yadis filter objects. Other filter-like things
    are convertable to this class."""

    def getServiceEndpoints(self, yadis_url, service_element):
        """Returns an iterator of endpoint objects"""
        raise NotImplementedError

class TransformFilterMaker(object):
    """Take a list of basic filters and makes a filter that transforms
    the basic filter into a top-level filter. This is mostly useful
    for the implementation of mkFilter, which should only be needed
    for special cases or internal use by this library.

    This object is useful for creating simple filters for services
    that use one URI and are specified by one Type (we expect most
    Types will fit this paradigm).

    Creates a BasicServiceEndpoint object and apply the filter
    functions to it until one of them returns a value.
    """

    def __init__(self, filter_functions):
        """Initialize the filter maker's state

        @param filter_functions: The endpoint transformer functions to
            apply to the basic endpoint. These are called in turn
            until one of them does not return None, and the result of
            that transformer is returned.
        """
        self.filter_functions = filter_functions

    def getServiceEndpoints(self, yadis_url, service_element):
        """Returns an iterator of endpoint objects produced by the
        filter functions."""
        endpoints = []

        # Do an expansion of the service element by xrd:Type and xrd:URI
        for type_uris, uri, _ in expandService(service_element):

            # Create a basic endpoint object to represent this
            # yadis_url, Service, Type, URI combination
            endpoint = BasicServiceEndpoint(
                yadis_url, type_uris, uri, service_element)

            e = self.applyFilters(endpoint)
            if e is not None:
                endpoints.append(e)

        return endpoints

    def applyFilters(self, endpoint):
        """Apply filter functions to an endpoint until one of them
        returns non-None."""
        for filter_function in self.filter_functions:
            e = filter_function(endpoint)
            if e is not None:
                # Once one of the filters has returned an
                # endpoint, do not apply any more.
                return e

        return None

class CompoundFilter(object):
    """Create a new filter that applies a set of filters to an endpoint
    and collects their results.
    """
    def __init__(self, subfilters):
        self.subfilters = subfilters

    def getServiceEndpoints(self, yadis_url, service_element):
        """Generate all endpoint objects for all of the subfilters of
        this filter and return their concatenation."""
        endpoints = []
        for subfilter in self.subfilters:
            endpoints.extend(
                subfilter.getServiceEndpoints(yadis_url, service_element))
        return endpoints

# Exception raised when something is not able to be turned into a filter
filter_type_error = TypeError(
    'Expected a filter, an endpoint, a callable or a list of any of these.')

def mkFilter(parts):
    """Convert a filter-convertable thing into a filter

    @param parts: a filter, an endpoint, a callable, or a list of any of these.
    """
    # Convert the parts into a list, and pass to mkCompoundFilter
    if parts is None:
        parts = [BasicServiceEndpoint]

    try:
        parts = list(parts)
    except TypeError:
        return mkCompoundFilter([parts])
    else:
        return mkCompoundFilter(parts)

def mkCompoundFilter(parts):
    """Create a filter out of a list of filter-like things

    Used by mkFilter

    @param parts: list of filter, endpoint, callable or list of any of these
    """
    # Separate into a list of callables and a list of filter objects
    transformers = []
    filters = []
    for subfilter in parts:
        try:
            subfilter = list(subfilter)
        except TypeError:
            # If it's not an iterable
            if hasattr(subfilter, 'getServiceEndpoints'):
                # It's a full filter
                filters.append(subfilter)
            elif hasattr(subfilter, 'fromBasicServiceEndpoint'):
                # It's an endpoint object, so put its endpoint
                # conversion attribute into the list of endpoint
                # transformers
                transformers.append(subfilter.fromBasicServiceEndpoint)
            elif callable(subfilter):
                # It's a simple callable, so add it to the list of
                # endpoint transformers
                transformers.append(subfilter)
            else:
                raise filter_type_error
        else:
            filters.append(mkCompoundFilter(subfilter))

    if transformers:
        filters.append(TransformFilterMaker(transformers))

    if len(filters) == 1:
        return filters[0]
    else:
        return CompoundFilter(filters)

########NEW FILE########
__FILENAME__ = manager
class YadisServiceManager(object):
    """Holds the state of a list of selected Yadis services, managing
    storing it in a session and iterating over the services in order."""

    def __init__(self, starting_url, yadis_url, services, session_key):
        # The URL that was used to initiate the Yadis protocol
        self.starting_url = starting_url

        # The URL after following redirects (the identifier)
        self.yadis_url = yadis_url

        # List of service elements
        self.services = list(services)

        self.session_key = session_key

        # Reference to the current service object
        self._current = None

    def __len__(self):
        """How many untried services remain?"""
        return len(self.services)

    def __iter__(self):
        return self

    def next(self):
        """Return the next service

        self.current() will continue to return that service until the
        next call to this method."""
        try:
            self._current = self.services.pop(0)
        except IndexError:
            raise StopIteration
        else:
            return self._current

    def current(self):
        """Return the current service.

        Returns None if there are no services left.
        """
        return self._current

    def forURL(self, url):
        return url in [self.starting_url, self.yadis_url]

    def started(self):
        """Has the first service been returned?"""
        return self._current is not None

    def store(self, session):
        """Store this object in the session, by its session key."""
        session[self.session_key] = self

class Discovery(object):
    """State management for discovery.

    High-level usage pattern is to call .getNextService(discover) in
    order to find the next available service for this user for this
    session. Once a request completes, call .finish() to clean up the
    session state.

    @ivar session: a dict-like object that stores state unique to the
        requesting user-agent. This object must be able to store
        serializable objects.

    @ivar url: the URL that is used to make the discovery request

    @ivar session_key_suffix: The suffix that will be used to identify
        this object in the session object.
    """

    DEFAULT_SUFFIX = 'auth'
    PREFIX = '_yadis_services_'

    def __init__(self, session, url, session_key_suffix=None):
        """Initialize a discovery object"""
        self.session = session
        self.url = url
        if session_key_suffix is None:
            session_key_suffix = self.DEFAULT_SUFFIX

        self.session_key_suffix = session_key_suffix

    def getNextService(self, discover):
        """Return the next authentication service for the pair of
        user_input and session.  This function handles fallback.


        @param discover: a callable that takes a URL and returns a
            list of services

        @type discover: str -> [service]


        @return: the next available service
        """
        manager = self.getManager()
        if manager is not None and not manager:
            self.destroyManager()

        if not manager:
            yadis_url, services = discover(self.url)
            manager = self.createManager(services, yadis_url)

        if manager:
            service = manager.next()
            manager.store(self.session)
        else:
            service = None

        return service

    def cleanup(self, force=False):
        """Clean up Yadis-related services in the session and return
        the most-recently-attempted service from the manager, if one
        exists.

        @param force: True if the manager should be deleted regardless
        of whether it's a manager for self.url.

        @return: current service endpoint object or None if there is
            no current service
        """
        manager = self.getManager(force=force)
        if manager is not None:
            service = manager.current()
            self.destroyManager(force=force)
        else:
            service = None

        return service

    ### Lower-level methods

    def getSessionKey(self):
        """Get the session key for this starting URL and suffix

        @return: The session key
        @rtype: str
        """
        return self.PREFIX + self.session_key_suffix

    def getManager(self, force=False):
        """Extract the YadisServiceManager for this object's URL and
        suffix from the session.

        @param force: True if the manager should be returned
        regardless of whether it's a manager for self.url.

        @return: The current YadisServiceManager, if it's for this
            URL, or else None
        """
        manager = self.session.get(self.getSessionKey())
        if (manager is not None and (manager.forURL(self.url) or force)):
            return manager
        else:
            return None

    def createManager(self, services, yadis_url=None):
        """Create a new YadisService Manager for this starting URL and
        suffix, and store it in the session.

        @raises KeyError: When I already have a manager.

        @return: A new YadisServiceManager or None
        """
        key = self.getSessionKey()
        if self.getManager():
            raise KeyError('There is already a %r manager for %r' %
                           (key, self.url))

        if not services:
            return None

        manager = YadisServiceManager(self.url, yadis_url, services, key)
        manager.store(self.session)
        return manager

    def destroyManager(self, force=False):
        """Delete any YadisServiceManager with this starting URL and
        suffix from the session.

        If there is no service manager or the service manager is for a
        different URL, it silently does nothing.

        @param force: True if the manager should be deleted regardless
        of whether it's a manager for self.url.
        """
        if self.getManager(force=force) is not None:
            key = self.getSessionKey()
            del self.session[key]

########NEW FILE########
__FILENAME__ = parsehtml
__all__ = ['findHTMLMeta', 'MetaNotFound']

from HTMLParser import HTMLParser, HTMLParseError
import htmlentitydefs
import re

from openid.yadis.constants import YADIS_HEADER_NAME

# Size of the chunks to search at a time (also the amount that gets
# read at a time)
CHUNK_SIZE = 1024 * 16 # 16 KB

class ParseDone(Exception):
    """Exception to hold the URI that was located when the parse is
    finished. If the parse finishes without finding the URI, set it to
    None."""

class MetaNotFound(Exception):
    """Exception to hold the content of the page if we did not find
    the appropriate <meta> tag"""

re_flags = re.IGNORECASE | re.UNICODE | re.VERBOSE
ent_pat = r'''
&

(?: \#x (?P<hex> [a-f0-9]+ )
|   \# (?P<dec> \d+ )
|   (?P<word> \w+ )
)

;'''

ent_re = re.compile(ent_pat, re_flags)

def substituteMO(mo):
    if mo.lastgroup == 'hex':
        codepoint = int(mo.group('hex'), 16)
    elif mo.lastgroup == 'dec':
        codepoint = int(mo.group('dec'))
    else:
        assert mo.lastgroup == 'word'
        codepoint = htmlentitydefs.name2codepoint.get(mo.group('word'))

    if codepoint is None:
        return mo.group()
    else:
        return unichr(codepoint)

def substituteEntities(s):
    return ent_re.sub(substituteMO, s)

class YadisHTMLParser(HTMLParser):
    """Parser that finds a meta http-equiv tag in the head of a html
    document.

    When feeding in data, if the tag is matched or it will never be
    found, the parser will raise ParseDone with the uri as the first
    attribute.

    Parsing state diagram
    =====================

    Any unlisted input does not affect the state::

                1, 2, 5                       8
               +--------------------------+  +-+
               |                          |  | |
            4  |    3       1, 2, 5, 7    v  | v
        TOP -> HTML -> HEAD ----------> TERMINATED
        | |            ^  |               ^  ^
        | | 3          |  |               |  |
        | +------------+  +-> FOUND ------+  |
        |                  6         8       |
        | 1, 2                               |
        +------------------------------------+

      1. any of </body>, </html>, </head> -> TERMINATE
      2. <body> -> TERMINATE
      3. <head> -> HEAD
      4. <html> -> HTML
      5. <html> -> TERMINATE
      6. <meta http-equiv='X-XRDS-Location'> -> FOUND
      7. <head> -> TERMINATE
      8. Any input -> TERMINATE
    """
    TOP = 0
    HTML = 1
    HEAD = 2
    FOUND = 3
    TERMINATED = 4

    def __init__(self):
        HTMLParser.__init__(self)
        self.phase = self.TOP

    def _terminate(self):
        self.phase = self.TERMINATED
        raise ParseDone(None)

    def handle_endtag(self, tag):
        # If we ever see an end of head, body, or html, bail out right away.
        # [1]
        if tag in ['head', 'body', 'html']:
            self._terminate()

    def handle_starttag(self, tag, attrs):
        # if we ever see a start body tag, bail out right away, since
        # we want to prevent the meta tag from appearing in the body
        # [2]
        if tag=='body':
            self._terminate()

        if self.phase == self.TOP:
            # At the top level, allow a html tag or a head tag to move
            # to the head or html phase
            if tag == 'head':
                # [3]
                self.phase = self.HEAD
            elif tag == 'html':
                # [4]
                self.phase = self.HTML

        elif self.phase == self.HTML:
            # if we are in the html tag, allow a head tag to move to
            # the HEAD phase. If we get another html tag, then bail
            # out
            if tag == 'head':
                # [3]
                self.phase = self.HEAD
            elif tag == 'html':
                # [5]
                self._terminate()

        elif self.phase == self.HEAD:
            # If we are in the head phase, look for the appropriate
            # meta tag. If we get a head or body tag, bail out.
            if tag == 'meta':
                attrs_d = dict(attrs)
                http_equiv = attrs_d.get('http-equiv', '').lower()
                if http_equiv == YADIS_HEADER_NAME.lower():
                    raw_attr = attrs_d.get('content')
                    yadis_loc = substituteEntities(raw_attr)
                    # [6]
                    self.phase = self.FOUND
                    raise ParseDone(yadis_loc)

            elif tag in ['head', 'html']:
                # [5], [7]
                self._terminate()

    def feed(self, chars):
        # [8]
        if self.phase in [self.TERMINATED, self.FOUND]:
            self._terminate()

        return HTMLParser.feed(self, chars)

def findHTMLMeta(stream):
    """Look for a meta http-equiv tag with the YADIS header name.

    @param stream: Source of the html text
    @type stream: Object that implements a read() method that works
        like file.read

    @return: The URI from which to fetch the XRDS document
    @rtype: str

    @raises MetaNotFound: raised with the content that was
        searched as the first parameter.
    """
    parser = YadisHTMLParser()
    chunks = []

    while 1:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            # End of file
            break

        chunks.append(chunk)
        try:
            parser.feed(chunk)
        except HTMLParseError, why:
            # HTML parse error, so bail
            chunks.append(stream.read())
            break
        except ParseDone, why:
            uri = why[0]
            if uri is None:
                # Parse finished, but we may need the rest of the file
                chunks.append(stream.read())
                break
            else:
                return uri

    content = ''.join(chunks)
    raise MetaNotFound(content)

########NEW FILE########
__FILENAME__ = services
# -*- test-case-name: openid.test.test_services -*-

from openid.yadis.filters import mkFilter
from openid.yadis.discover import discover, DiscoveryFailure
from openid.yadis.etxrd import parseXRDS, iterServices, XRDSError

def getServiceEndpoints(input_url, flt=None):
    """Perform the Yadis protocol on the input URL and return an
    iterable of resulting endpoint objects.

    @param flt: A filter object or something that is convertable to
        a filter object (using mkFilter) that will be used to generate
        endpoint objects. This defaults to generating BasicEndpoint
        objects.

    @param input_url: The URL on which to perform the Yadis protocol

    @return: The normalized identity URL and an iterable of endpoint
        objects generated by the filter function.

    @rtype: (str, [endpoint])

    @raises DiscoveryFailure: when Yadis fails to obtain an XRDS document.
    """
    result = discover(input_url)
    try:
        endpoints = applyFilter(result.normalized_uri,
                                result.response_text, flt)
    except XRDSError, err:
        raise DiscoveryFailure(str(err), None)
    return (result.normalized_uri, endpoints)

def applyFilter(normalized_uri, xrd_data, flt=None):
    """Generate an iterable of endpoint objects given this input data,
    presumably from the result of performing the Yadis protocol.

    @param normalized_uri: The input URL, after following redirects,
        as in the Yadis protocol.


    @param xrd_data: The XML text the XRDS file fetched from the
        normalized URI.
    @type xrd_data: str

    """
    flt = mkFilter(flt)
    et = parseXRDS(xrd_data)

    endpoints = []
    for service_element in iterServices(et):
        endpoints.extend(
            flt.getServiceEndpoints(normalized_uri, service_element))

    return endpoints

########NEW FILE########
__FILENAME__ = xri
# -*- test-case-name: openid.test.test_xri -*-
"""Utility functions for handling XRIs.

@see: XRI Syntax v2.0 at the U{OASIS XRI Technical Committee<http://www.oasis-open.org/committees/tc_home.php?wg_abbrev=xri>}
"""

import re

XRI_AUTHORITIES = ['!', '=', '@', '+', '$', '(']

try:
    unichr(0x10000)
except ValueError:
    # narrow python build
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        ]
else:
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        (0x10000, 0x1FFFD),
        (0x20000, 0x2FFFD),
        (0x30000, 0x3FFFD),
        (0x40000, 0x4FFFD),
        (0x50000, 0x5FFFD),
        (0x60000, 0x6FFFD),
        (0x70000, 0x7FFFD),
        (0x80000, 0x8FFFD),
        (0x90000, 0x9FFFD),
        (0xA0000, 0xAFFFD),
        (0xB0000, 0xBFFFD),
        (0xC0000, 0xCFFFD),
        (0xD0000, 0xDFFFD),
        (0xE1000, 0xEFFFD),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        (0xF0000, 0xFFFFD),
        (0x100000, 0x10FFFD),
        ]


_escapeme_re = re.compile('[%s]' % (''.join(
    map(lambda (m, n): u'%s-%s' % (unichr(m), unichr(n)),
        UCSCHAR + IPRIVATE)),))


def identifierScheme(identifier):
    """Determine if this identifier is an XRI or URI.

    @returns: C{"XRI"} or C{"URI"}
    """
    if identifier.startswith('xri://') or (
        identifier and identifier[0] in XRI_AUTHORITIES):
        return "XRI"
    else:
        return "URI"


def toIRINormal(xri):
    """Transform an XRI to IRI-normal form."""
    if not xri.startswith('xri://'):
        xri = 'xri://' + xri
    return escapeForIRI(xri)


_xref_re = re.compile('\((.*?)\)')


def _escape_xref(xref_match):
    """Escape things that need to be escaped if they're in a cross-reference.
    """
    xref = xref_match.group()
    xref = xref.replace('/', '%2F')
    xref = xref.replace('?', '%3F')
    xref = xref.replace('#', '%23')
    return xref


def escapeForIRI(xri):
    """Escape things that need to be escaped when transforming to an IRI."""
    xri = xri.replace('%', '%25')
    xri = _xref_re.sub(_escape_xref, xri)
    return xri


def toURINormal(xri):
    """Transform an XRI to URI normal form."""
    return iriToURI(toIRINormal(xri))


def _percentEscapeUnicode(char_match):
    c = char_match.group()
    return ''.join(['%%%X' % (ord(octet),) for octet in c.encode('utf-8')])


def iriToURI(iri):
    """Transform an IRI to a URI by escaping unicode."""
    # According to RFC 3987, section 3.1, "Mapping of IRIs to URIs"
    return _escapeme_re.sub(_percentEscapeUnicode, iri)


def providerIsAuthoritative(providerID, canonicalID):
    """Is this provider ID authoritative for this XRI?

    @returntype: bool
    """
    # XXX: can't use rsplit until we require python >= 2.4.
    lastbang = canonicalID.rindex('!')
    parent = canonicalID[:lastbang]
    return parent == providerID


def rootAuthority(xri):
    """Return the root authority for an XRI.

    Example::

        rootAuthority("xri://@example") == "xri://@"

    @type xri: unicode
    @returntype: unicode
    """
    if xri.startswith('xri://'):
        xri = xri[6:]
    authority = xri.split('/', 1)[0]
    if authority[0] == '(':
        # Cross-reference.
        # XXX: This is incorrect if someone nests cross-references so there
        #   is another close-paren in there.  Hopefully nobody does that
        #   before we have a real xriparse function.  Hopefully nobody does
        #   that *ever*.
        root = authority[:authority.index(')') + 1]
    elif authority[0] in XRI_AUTHORITIES:
        # Other XRI reference.
        root = authority[0]
    else:
        # IRI reference.  XXX: Can IRI authorities have segments?
        segments = authority.split('!')
        segments = reduce(list.__add__,
            map(lambda s: s.split('*'), segments))
        root = segments[0]

    return XRI(root)


def XRI(xri):
    """An XRI object allowing comparison of XRI.

    Ideally, this would do full normalization and provide comparsion
    operators as per XRI Syntax.  Right now, it just does a bit of
    canonicalization by ensuring the xri scheme is present.

    @param xri: an xri string
    @type xri: unicode
    """
    if not xri.startswith('xri://'):
        xri = 'xri://' + xri
    return xri

########NEW FILE########
__FILENAME__ = xrires
# -*- test-case-name: openid.test.test_xrires -*-
"""XRI resolution.
"""

from urllib import urlencode
from openid import fetchers
from openid.yadis import etxrd
from openid.yadis.xri import toURINormal
from openid.yadis.services import iterServices

DEFAULT_PROXY = 'http://proxy.xri.net/'

class ProxyResolver(object):
    """Python interface to a remote XRI proxy resolver.
    """
    def __init__(self, proxy_url=DEFAULT_PROXY):
        self.proxy_url = proxy_url


    def queryURL(self, xri, service_type=None):
        """Build a URL to query the proxy resolver.

        @param xri: An XRI to resolve.
        @type xri: unicode

        @param service_type: The service type to resolve, if you desire
            service endpoint selection.  A service type is a URI.
        @type service_type: str

        @returns: a URL
        @returntype: str
        """
        # Trim off the xri:// prefix.  The proxy resolver didn't accept it
        # when this code was written, but that may (or may not) change for
        # XRI Resolution 2.0 Working Draft 11.
        qxri = toURINormal(xri)[6:]
        hxri = self.proxy_url + qxri
        args = {
            # XXX: If the proxy resolver will ensure that it doesn't return
            # bogus CanonicalIDs (as per Steve's message of 15 Aug 2006
            # 11:13:42), then we could ask for application/xrd+xml instead,
            # which would give us a bit less to process.
            '_xrd_r': 'application/xrds+xml',
            }
        if service_type:
            args['_xrd_t'] = service_type
        else:
            # Don't perform service endpoint selection.
            args['_xrd_r'] += ';sep=false'
        query = _appendArgs(hxri, args)
        return query


    def query(self, xri, service_types):
        """Resolve some services for an XRI.

        Note: I don't implement any service endpoint selection beyond what
        the resolver I'm querying does, so the Services I return may well
        include Services that were not of the types you asked for.

        May raise fetchers.HTTPFetchingError or L{etxrd.XRDSError} if
        the fetching or parsing don't go so well.

        @param xri: An XRI to resolve.
        @type xri: unicode

        @param service_types: A list of services types to query for.  Service
            types are URIs.
        @type service_types: list of str

        @returns: tuple of (CanonicalID, Service elements)
        @returntype: (unicode, list of C{ElementTree.Element}s)
        """
        # FIXME: No test coverage!
        services = []
        # Make a seperate request to the proxy resolver for each service
        # type, as, if it is following Refs, it could return a different
        # XRDS for each.

        canonicalID = None

        for service_type in service_types:
            url = self.queryURL(xri, service_type)
            response = fetchers.fetch(url)
            if response.status != 200:
                # XXX: sucks to fail silently.
                # print "response not OK:", response
                continue
            et = etxrd.parseXRDS(response.body)
            canonicalID = etxrd.getCanonicalID(xri, et)
            some_services = list(iterServices(et))
            services.extend(some_services)
        # TODO:
        #  * If we do get hits for multiple service_types, we're almost
        #    certainly going to have duplicated service entries and
        #    broken priority ordering.
        return canonicalID, services


def _appendArgs(url, args):
    """Append some arguments to an HTTP query.
    """
    # to be merged with oidutil.appendArgs when we combine the projects.
    if hasattr(args, 'items'):
        args = args.items()
        args.sort()

    if len(args) == 0:
        return url

    # According to XRI Resolution section "QXRI query parameters":
    #
    # """If the original QXRI had a null query component (only a leading
    #    question mark), or a query component consisting of only question
    #    marks, one additional leading question mark MUST be added when
    #    adding any XRI resolution parameters."""

    if '?' in url.rstrip('?'):
        sep = '&'
    else:
        sep = '?'

    return '%s%s%s' % (url, sep, urlencode(args))

########NEW FILE########
__FILENAME__ = store
#!/usr/bin/python
#
# Copyright 2007, Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
An OpenIDStore implementation that uses the datastore as its backing store.
Stores associations, nonces, and authentication tokens.

OpenIDStore is an interface from JanRain's OpenID python library:
  http://openidenabled.com/python-openid/

For more, see openid/store/interface.py in that library.
"""

import datetime

from openid.association import Association as OpenIDAssociation
from openid.store.interface import OpenIDStore
from openid.store import nonce
from google.appengine.ext import db

# number of associations and nonces to clean up in a single request.
CLEANUP_BATCH_SIZE = 50


class Association(db.Model):
  """An association with another OpenID server, either a consumer or a provider.
  """
  url = db.LinkProperty()
  handle = db.StringProperty()
  association = db.TextProperty()
  created = db.DateTimeProperty(auto_now_add=True)


class UsedNonce(db.Model):
  """An OpenID nonce that has been used.
  """
  server_url = db.LinkProperty()
  timestamp = db.DateTimeProperty()
  salt = db.StringProperty()


class DatastoreStore(OpenIDStore):
  """An OpenIDStore implementation that uses the datastore. See
  openid/store/interface.py for in-depth descriptions of the methods.

  They follow the OpenID python library's style, not Google's style, since
  they override methods defined in the OpenIDStore class.
  """

  def storeAssociation(self, server_url, association):
    """
    This method puts a C{L{Association <openid.association.Association>}}
    object into storage, retrievable by server URL and handle.
    """
    assoc = Association(url=server_url,
                        handle=association.handle,
                        association=association.serialize())
    assoc.put()

  def getAssociation(self, server_url, handle=None):
    """
    This method returns an C{L{Association <openid.association.Association>}}
    object from storage that matches the server URL and, if specified, handle.
    It returns C{None} if no such association is found or if the matching
    association is expired.

    If no handle is specified, the store may return any association which
    matches the server URL. If multiple associations are valid, the
    recommended return value for this method is the one that will remain valid
    for the longest duration.
    """
    query = Association.all().filter('url', server_url)
    if handle:
      query.filter('handle', handle)

    results = query.fetch(1)
    if results:
      association = OpenIDAssociation.deserialize(results[0].association)
      if association.getExpiresIn() > 0:
        # hasn't expired yet
        return association

    return None

  def removeAssociation(self, server_url, handle):
    """
    This method removes the matching association if it's found, and returns
    whether the association was removed or not.
    """
    query = Association.gql('WHERE url = :1 AND handle = :2',
                            server_url, handle)
    return self._delete_first(query)

  def useNonce(self, server_url, timestamp, salt):
    """Called when using a nonce.

    This method should return C{True} if the nonce has not been
    used before, and store it for a while to make sure nobody
    tries to use the same value again.  If the nonce has already
    been used or the timestamp is not current, return C{False}.

    You may use L{openid.store.nonce.SKEW} for your timestamp window.

    @change: In earlier versions, round-trip nonces were used and
       a nonce was only valid if it had been previously stored
       with C{storeNonce}.  Version 2.0 uses one-way nonces,
       requiring a different implementation here that does not
       depend on a C{storeNonce} call.  (C{storeNonce} is no
       longer part of the interface.)

    @param server_url: The URL of the server from which the nonce
        originated.

    @type server_url: C{str}

    @param timestamp: The time that the nonce was created (to the
        nearest second), in seconds since January 1 1970 UTC.
    @type timestamp: C{int}

    @param salt: A random string that makes two nonces from the
        same server issued during the same second unique.
    @type salt: str

    @return: Whether or not the nonce was valid.

    @rtype: C{bool}
    """
    query = UsedNonce.gql(
      'WHERE server_url = :1 AND salt = :2 AND timestamp >= :3',
      server_url, salt, self._expiration_datetime())
    return query.fetch(1) == []

  def cleanupNonces(self):
    """Remove expired nonces from the store.

    Discards any nonce from storage that is old enough that its
    timestamp would not pass L{useNonce}.

    This method is not called in the normal operation of the
    library.  It provides a way for store admins to keep
    their storage from filling up with expired data.

    @return: the number of nonces expired.
    @returntype: int
    """
    query = UsedNonce.gql('WHERE timestamp < :1', self._expiration_datetime())
    return self._cleanup_batch(query)

  def cleanupAssociations(self):
    """Remove expired associations from the store.

    This method is not called in the normal operation of the
    library.  It provides a way for store admins to keep
    their storage from filling up with expired data.

    @return: the number of associations expired.
    @returntype: int
    """
    query = Association.gql('WHERE created < :1', self._expiration_datetime())
    return self._cleanup_batch(query)

  def cleanup(self):
    """Shortcut for C{L{cleanupNonces}()}, C{L{cleanupAssociations}()}.

    This method is not called in the normal operation of the
    library.  It provides a way for store admins to keep
    their storage from filling up with expired data.
    """
    return self.cleanupNonces(), self.cleanupAssociations()

  def _delete_first(self, query):
    """Deletes the first result for the given query.

    Returns True if an entity was deleted, false if no entity could be deleted
    or if the query returned no results.
    """
    results = query.fetch(1)

    if results:
      try:
        results[0].delete()
        return True
      except db.Error:
        return False
    else:
      return False

  def _cleanup_batch(self, query):
    """Deletes the first batch of entities that match the given query.

    Returns the number of entities that were deleted.
    """
    to_delete = list(query.fetch(CLEANUP_BATCH_SIZE))

    # can't use batch delete since they're all root entities :/
    for entity in to_delete:
      entity.delete()

    return len(to_delete)

  def _expiration_datetime(self):
    """Returns the current expiration date for nonces and associations.
    """
    return datetime.datetime.now() - datetime.timedelta(seconds=nonce.SKEW)

########NEW FILE########
