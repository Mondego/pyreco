__FILENAME__ = config
'''
Configuration File

Setup this file according to your application Models as to map their
attributes to the equivalent atom elements.
'''

'''
gae-rest needs to import the files containing your Models since it is
unable to dynamic infer what are all the available entity kinds
(content types) in your application
Example: models = ['my_models.py', 'my_expandos.py']
'''
models = []

'''
which attribute on each Entity can be used as atom <author> element
Example: author = {'Entry': 'author'}
'''
author = {}

'''
<title>
Example: title = {'Entry': 'title'}
'''
title = {}

'''
<content>
Example: content = {'Entry': 'body_html'}
'''
content = {}

'''
<summary>
Example: summary = {'Entry': 'excerpt'}
'''
summary = {}

'''
<published>
Example: published = {'Entry': 'published'}
'''
published = {}

'''
<updated>
Example: updated = {'Entry': 'updated'}
'''
updated = {}
########NEW FILE########
__FILENAME__ = xmlbuilder
from __future__ import with_statement
from StringIO import StringIO

__author__ = ('Jonas Galvez', 'jonas@codeazur.com.br', 'http://jonasgalvez.com.br')
__license__ = "GPL"

import sys

class builder:
  def __init__(self, version, encoding):
    self.document = StringIO()
    self.document.write('<?xml version="%s" encoding="%s"?>\n' % (version, encoding))
    self.indentation = -2
  def __getattr__(self, name):
    return element(name, self)
  def __getitem__(self, name):
    return element(name, self)
  def __unicode__(self):
    return self.document.getvalue()
  def write(self, line):
    self.document.write('%s%s' % ((self.indentation * ' '), line))

class element:
  def __init__(self, name, builder):
    self.name = name
    self.builder = builder
  def __enter__(self):
    self.builder.indentation += 2
    if hasattr(self, 'attributes'):
      self.builder.write('<%s %s>\n' % (self.name, self.serialized_attrs))
    else:
      self.builder.write('<%s>\n' % self.name)
  def __exit__(self, type, value, tb):
    self.builder.write('</%s>\n' % self.name)
    self.builder.indentation -= 2
  def __call__(self, value=False, **kargs):
    if len(kargs.keys()) > 0:
      self.attributes = kargs
      self.serialized_attrs = self.serialize_attrs(kargs)
    if value == None:
      self.builder.indentation += 2
      if hasattr(self, 'attributes'):
        self.builder.write('<%s %s />\n' % (self.name, self.serialized_attrs))
      else:
        self.builder.write('<%s />\n' % self.name)
      self.builder.indentation -= 2
    elif value != False:
      self.builder.indentation += 2
      if hasattr(self, 'attributes'):
        self.builder.write('<%s %s>%s</%s>\n' % (self.name, self.serialized_attrs, value, self.name))
      else:
        self.builder.write('<%s>%s</%s>\n' % (self.name, value, self.name))
      self.builder.indentation -= 2
      return
    return self
  def serialize_attrs(self, attrs):
    serialized = []
    for attr, value in attrs.items():
      serialized.append('%s="%s"' % (attr, value))
    return ' '.join(serialized)

if __name__ == "__main__":
  xml = builder(version="1.0", encoding="utf-8")
  with xml.feed(xmlns='http://www.w3.org/2005/Atom'):
    xml.title('Example Feed')
    xml.link(None, href='http://example.org/')
    xml.updated('2003-12-13T18:30:02Z')
    with xml.author:
      xml.name('John Doe')
    xml.id('urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6')
    with xml.entry:
      xml.title('Atom-Powered Robots Run Amok')
      xml.link(None, href='http://example.org/2003/12/13/atom03')
      xml.id('urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a')
      xml.updated('2003-12-13T18:30:02Z')
      xml.summary('Some text.')
  print xml

'''
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Feed</title>
  <link href="http://example.org/" />
  <updated>2003-12-13T18:30:02Z</updated>
  <author>
    <name>John Doe</name>
  </author>
  <id>urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6</id>
  <entry>
    <title>Atom-Powered Robots Run Amok</title>
    <link href="http://example.org/2003/12/13/atom03" />
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <updated>2003-12-13T18:30:02Z</updated>
    <summary>Some text.</summary>
  </entry>
</feed>
'''
########NEW FILE########
__FILENAME__ = xn
from __future__ import with_statement
from datetime import datetime
import os, re, sys, types
sys.path += [os.path.split(os.path.abspath(__file__))[0]]
import glob, urllib2
import urllib
import wsgiref.handlers
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api.users import User
from xnquery import *
from xmlbuilder import *
import config

def expose(only=[]):
  rootdir = os.path.join(os.path.abspath(os.path.split(os.path.dirname(__file__))[0]))
  loadedfiles = []
  for model in config.models:
    pydir, pyfile = os.path.split(model)
    pydir = os.path.abspath(os.path.join(rootdir, pydir))
    sys.path += [pydir]
    pyfile = os.path.splitext(pyfile)[0]
    loadedfiles.append(pyfile)
    __import__(pyfile)
    sys.path.remove(pydir)
  return loadedfiles

expose()

class XNQueryHandler(webapp.RequestHandler):
  def get(self, format, version, query):
    xnquery = XNQueryParser(query, os.environ['QUERY_STRING'])
    # if the query is content(id='...'), do not use GQLQueryBuilder
    if 'id' in xnquery.resources.content.selectors:
      entity_ref = db.Key(xnquery.resources.content.selectors.id.rightside)
      objects = [db.get(entity_ref)]
      if len(objects) > 0: kind = entity_ref.kind()
    else:
      gqlquery = GQLQueryBuilder(xnquery)
      objects = db.GqlQuery(str(gqlquery))
      kind = xnquery.resources.content.selectors.type.rightside
    self.response.headers['Content-Type'] = 'application/atom+xml'
    atom = AtomBuilder(kind, objects)
    self.response.out.write(unicode(atom))

class AtomBuilder:
  FEED_NS = {
    'xmlns': 'http://www.w3.org/2005/Atom',
    'xmlns:xn': 'http://www.ning.com/atom/1.0'
  }
  HANDLERS = {
    'title': lambda value: value,
    'content': lambda value: value.replace('<','&lt;'),
    'summary': lambda value: value.replace('<','&lt;'),
    'published': lambda value: '%sZ' % value.isoformat(),
    'updated': lambda value: '%sZ' % value.isoformat(),
    'author': 'process_author'
  }
  def __init__(self, kind, objects):
    xml = builder(version='1.0', encoding='utf-8')
    self.xml = xml
    self.kind = kind
    with xml.feed(**self.FEED_NS):
      xml.title("GAE-REST Test Atom Feed")
      for object in objects:
        with xml.entry:
          xml.id(object.key())
          properties = object.properties()
          self.process_known_elements(object, properties)
          for property in properties:
            value = getattr(object, property)
            if type(value) == list:
              xml["xn:%s" % property](' '.join(value))
            else:
              xml["xn:%s" % property](unicode(value).replace('<','&lt;'))
    self.xml = xml
  def process_author(self, value):
    with self.xml.author:
      if type(value) == User:
        self.xml.name(value.nickname())
        self.xml.email(value.email())
      else:
        self.xml.name(value)
  def process_known_elements(self, object, properties):
    used_properties = {}
    for element in AtomBuilder.HANDLERS.keys():
      m_element = getattr(config, element).get(self.kind, None)
      if m_element != None:
        if type(AtomBuilder.HANDLERS[element]) != str:
          self.xml[element](AtomBuilder.HANDLERS[element](getattr(object, m_element)))
        else:
          getattr(self, AtomBuilder.HANDLERS[element])(getattr(object, m_element))
        used_properties[m_element] = True
    for property_name in used_properties.keys():
      del properties[property_name]
  def __str__(self):
    return unicode(self.xml)

def main():
  application = webapp.WSGIApplication([('/xn/(.*)/(.*)/(.*)', XNQueryHandler)], debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()
########NEW FILE########
__FILENAME__ = xnquery
__author__ = ('Jonas Galvez', 'jonas@codeazur.com.br', 'http://jonasgalvez.com.br')

import re
import urllib2
import unittest

class InvalidResource(Exception): pass
class InvalidSelectorOperator(Exception): pass

# Storage helper class comes from web.py, props to Aaron Swartz
class Storage(dict):
  def __getattr__(self, key):
    try: return self[key]
    except KeyError, k: raise AttributeError, k
  def __setattr__(self, key, value):
    self[key] = value
  def __delattr__(self, key):
    try: del self[key]
    except KeyError, k: raise AttributeError, k
  def __repr__(self):
    return '<Storage ' + dict.__repr__(self) + '>'

# TO-DO: add code to determine type (string, int etc)
class XNSelector(Storage):
  SPECIAL_SELECTORS = {'order': 'XNOrder'}
  BASIC_OPERATORS = ('<>', '<=', '>=', '<', '>', '=')
  CONDITION = re.compile("""^[^=><]*(.*?)['"]*$""")
  LINE_STRIP_QUOTES = re.compile("""^['"]*(.*?)['"]*$""")
  FIELD = re.compile("""^[A-Za-z][_.A-Z-a-z\d]+""")
  def __init__(self, operator, leftside, rightside):
    self.operator = operator
    self.leftside = leftside
    quote_stripped = XNSelector.LINE_STRIP_QUOTES.match(rightside)
    if quote_stripped: self.rightside = quote_stripped.group(1)
    else: self.rightside = rightside
    self.rightside_raw = rightside
    self.parse_right_side()
  def parse_right_side(self):
    is_field = XNSelector.FIELD.match(self.rightside_raw)
    if is_field:
      self.field = is_field.group()
      self.field = re.sub('^my\.', '', self.field)
  @staticmethod
  def parse(fromstring):
    for op in XNSelector.BASIC_OPERATORS:
      operands = fromstring.split(op)
      if len(operands) > 1:
        for field, selector in XNSelector.SPECIAL_SELECTORS.items():
          if operands[0].strip() == field:
            return globals()[selector](op, *map(str.strip, operands))
        return XNSelector(op, *map(str.strip, operands))
    return fromstring

class XNOrder(XNSelector):
  def __init__(self, *args, **kargs):
    XNSelector.__init__(self, *args, **kargs)
    order_raw = self.rightside.split('@')
    if len(order_raw) > 1:
      field, order = order_raw
      self.order = {'A': 'ASC', 'D': 'DESC'}[order]
    else:
      self.order = 'ASC'

class XNQueryParser:
  RESOURCE_AND_SELECTORS = re.compile("""([^(]+)(?:\((.*)\))?""")
  def __init__(self, resources, ordering):
    self.resources = Storage()
    self.ordering = Storage()
    self._parse_resources(urllib2.unquote(urllib2.unquote(resources))) # bizarre, figure out why
    self._parse_selectors(self.ordering, urllib2.unquote(ordering or ''))
  def _parse_resources(self, resources):
    resources = resources.split('/')
    for resource in resources:
      m = XNQueryParser.RESOURCE_AND_SELECTORS.match(resource)
      if m:
        resource_name = m.group(1)
        self.resources[resource_name] = Storage()
        resource_obj = self.resources[resource_name]
        selectors = m.group(2)
        if selectors:
          resource_obj.selectors = Storage()
          self._parse_selectors(resource_obj.selectors, selectors)
  def _parse_selectors(self, obj, selectors):
    if selectors == None:
      return None
    for selector in selectors.split('&'):
      xnsel = XNSelector.parse(selector)
      if xnsel: obj[xnsel.leftside] = xnsel

class GQLQueryBuilder:
  KNOWN_RESOURCES = ('content',)
  def __init__(self, xnquery):
    self.resources = xnquery.resources
    self.ordering = xnquery.ordering
    self.gql_query = ['SELECT']
    self.process_known_resources()
    self.process_ordering_conditions()
  def process_known_resources(self):
    for res in GQLQueryBuilder.KNOWN_RESOURCES:
      self.__dict__[res] = None
      getattr(self, 'process_%s' % res)()
  def process_content(self):
    if 'content' in self.resources:
      self.content = self.resources['content']
      self.entity = self.content.selectors['type'].rightside
      self.gql_query += ['*', 'FROM', self.entity]
      if len(self.content.selectors.keys()) > 1:
        self.gql_query += ['WHERE']
        for name, selector in self.content.selectors.items():
          if name == 'type': continue # TO-DO: make it so that you don't have to do this
          self.gql_query += [selector.leftside, selector.operator, selector.rightside_raw]
  def process_ordering_conditions(self):
    order = self.ordering.get('order', None)
    if order != None:
      self.gql_query += ['ORDER BY', order.field, order.order]
    _from = self.ordering.get('from', None)
    _to = self.ordering.get('to', None)
    if _from != None and _to != None:
      _from, _to = int(_from.rightside), int(_to.rightside)
      self.gql_query += ['LIMIT', '%s, %s' % (int(_from), (_to-_from))]

  def __str__(self):
    return ' '.join(self.gql_query)

class XNQueryTester(unittest.TestCase):
  queries = (
    ("profile(id='david')", None),
    ("content(type='User'&author='david')", None),
    ("content", "order=published@D"),
    ("content(type='Photo')", "order=my.viewCount@D&from=20&to=30"),
    ("content(type='Topic'&my.xg_forum_commentCount>1)", "order=my.xg_forum_commentCount@D&from=0&to=5")
  )
  def test_author_is_david(self):
    sample_query = self.queries[1]
    xnquery = XNQueryParser(sample_query[0], sample_query[1])
    assert xnquery.resources['content'].selectors['author'].rightside == 'david'
  def test_order_parsing(self):
    sample_query = self.queries[3]
    xnquery = XNQueryParser(sample_query[0], sample_query[1])
    assert xnquery.ordering['order'].rightside == 'my.viewCount@D'
    assert xnquery.ordering['order'].field == 'viewCount'
    assert xnquery.ordering['order'].order == 'DESC'
  def test_simple_gql_query(self):
    sample_query = self.queries[1]
    xnquery = XNQueryParser(sample_query[0], sample_query[1])
    gqlquery = GQLQueryBuilder(xnquery)
    assert str(gqlquery) == """SELECT * FROM User WHERE author = 'david'"""
  def test_gql_query_with_order(self):
    sample_query = self.queries[3]
    xnquery = XNQueryParser(sample_query[0], sample_query[1])
    gqlquery = GQLQueryBuilder(xnquery)
    assert str(gqlquery) == """SELECT * FROM Photo ORDER BY viewCount DESC LIMIT 20, 10"""

if __name__ == '__main__':
  unittest.main()
  # helpful for debugging
  # sample_query = ("content(type='Photo')", "order=my.viewCount@D&from=20&to=30")
  # xnquery = XNQueryParser(sample_query[0], sample_query[1])
  # gqlquery = GQLQueryBuilder(xnquery)
  # print str(gqlquery)
########NEW FILE########
