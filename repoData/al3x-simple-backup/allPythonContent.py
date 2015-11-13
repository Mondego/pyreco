__FILENAME__ = betterhandler
import os
from google.appengine.ext import webapp

class BetterHandler(webapp.RequestHandler):
  def template_path(self, filename):
    return os.path.join(os.path.dirname(__file__), 'templates', filename)

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

import csv, logging, Simplenote, StringIO, wsgiref.handlers, yaml

from betterhandler import *
from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

class Auth(BetterHandler):
  def post(self):
    email = self.request.get('email')
    password = self.request.get('password')

    try:
      token = Simplenote.get_token(email, password)
    except Simplenote.AuthError:
      for_template = {
        'autherror': True,
      }
      return self.response.out.write(template.render(self.template_path('index.html'),
                                                     for_template))
    else:
      index = Simplenote.index(token, email)
      note_ids = []

      logging.info("index of all notes: '%s'" % index)

      for note in index:
        if note['deleted'] == False:
          note_ids.append(note['key'])

      logging.info("note_ids minus deleted notes: '%s'" % note_ids)

      for_template = {
        'note_count': len(note_ids),
        'token': token,
        'email': email,
        'note_ids': ','.join(note_ids),
      }

      return self.response.out.write(template.render(self.template_path('auth.html'),
                                                     for_template))

class Export(BetterHandler):
  def txt(self, notes):
    for_template = {
      'notes': notes
    }

    self.response.headers["Content-Type"] = "application/octet-stream"
    self.response.headers.add_header("Content-Disposition",
                                     'attachment; filename=simplenote-export.txt')
    self.response.out.write(template.render(self.template_path('txt'),
                                            for_template))

  def csv(self, notes):
    output = StringIO.StringIO()
    writer = csv.writer(output)

    for note in notes:
      row = [note['created'].strftime("%b %d %Y %H:%M:%S"),
             note['modified'].strftime("%b %d %Y %H:%M:%S"),
             note['content']]
      writer.writerow(row)

    csvout = output.getvalue()
    output.close()

    self.response.headers["Content-Type"] = "application/octet-stream"
    self.response.headers.add_header("Content-Disposition",
                                     'attachment; filename=simplenote-export.csv')
    self.response.out.write(csvout)

  def json(self, notes):
    for note in notes:
      note['created'] = note['created'].strftime("%b %d %Y %H:%M:%S")
      note['modified'] = note['modified'].strftime("%b %d %Y %H:%M:%S")

    output = simplejson.dumps(notes)

    self.response.headers["Content-Type"] = "application/octet-stream"
    self.response.headers.add_header("Content-Disposition",
                                     'attachment; filename=simplenote-export.json')
    self.response.out.write(output)

  def xml(self, notes):
    for_template = {
      'notes': notes
    }

    self.response.headers["Content-Type"] = "application/octet-stream"
    self.response.headers.add_header("Content-Disposition",
                                     'attachment; filename=simplenote-export.xml')
    self.response.out.write(template.render(self.template_path('xml'),
                                            for_template))

  def enex(self, notes):
    for_template = {
      'notes': notes
    }

    self.response.headers["Content-Type"] = "application/octet-stream"
    self.response.headers.add_header("Content-Disposition",
                                     'attachment; filename=simplenote-export.enex')
    self.response.out.write(template.render(self.template_path('enex'),
                                            for_template))

  def yaml(self, notes):
    yamlnotes = []

    for note in notes:
      d = {}

      d[str(note['key'])] = {
        'created': note['created'],
        'modified': note['modified'],
        'content': note['content']
      }

      yamlnotes.append(d)

    output = yaml.dump(yamlnotes, default_flow_style=False)

    self.response.headers["Content-Type"] = "application/octet-stream"
    self.response.headers.add_header("Content-Disposition",
                                     'attachment; filename=simplenote-export.yaml')
    self.response.out.write(output)

  def post(self):
    token = self.request.get('token')
    email = self.request.get('email')
    format = self.request.get('format')
    note_ids = self.request.get('note_ids').split(',')

    notes = []

    for key in note_ids:
      note = Simplenote.get_note(key, token, email)
      notes.append(note)

    for_template = {
      'notes': notes
    }

    logging.info("Found notes: '%s'" % notes)

    if format == 'txt':
      self.txt(notes)
    elif format == 'csv':
      self.csv(notes)
    elif format == 'json':
      self.json(notes)
    elif format == 'xml':
      self.xml(notes)
    elif format == 'yaml':
      self.yaml(notes)
    elif format == 'enex':
      self.enex(notes)

class FrontPage(BetterHandler):
  def get(self):
    return self.response.out.write(template.render(self.template_path('index.html'),
                                                   {}))


def main():
  logging.getLogger().setLevel(logging.INFO)

  application = webapp.WSGIApplication([('/', FrontPage),
                                        ('/auth', Auth),
                                        ('/export', Export)],
                                       debug=True)

  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = Simplenote
#!/usr/bin/env python

import base64, logging, urllib

from datetime import datetime
from google.appengine.api import urlfetch
from django.utils import simplejson


class MyException(Exception):
  def _get_message(self, message):
      return self._message

  def _set_message(self, message):
      self._message = message

  message = property(_get_message, _set_message)


class AuthError(MyException):
  def __init__(self, email, message):
    self.email = email
    self.message = message


class ApiError(MyException):
  def __init__(self, method, message):
    self.method = method
    self.message = message


def mkdatetime(time_str):
  return datetime.strptime(time_str.split('.')[0], "%Y-%m-%d %H:%M:%S")

def get_token(email, password):
  url = 'https://simple-note.appspot.com/api/login'

  form_fields = {
    'email': email,
    'password': password
  }

  payload = base64.b64encode(urllib.urlencode(form_fields))

  result = urlfetch.fetch(url=url,
                          method=urlfetch.POST,
                          payload=payload,
                          headers={'Content-Type': 'application/x-www-form-urlencoded'})

  if (result.status_code == 200):
    return result.content.strip()
  else:
    logging.error("Error getting token: %d %s" % (result.status_code, result.content))
    raise AuthError(email, "Could not authenticate or bad response from server.")

def index(token, email):
  email = email.replace("+", "%2B")
  url = "https://simple-note.appspot.com/api/index?auth=%s&email=%s" % (token, email)
  result = urlfetch.fetch(url=url,
                          method=urlfetch.GET)

  try:
    notes = simplejson.loads(result.content)
  except:
    logging.error("Error loading JSON from index.\nStatus: %d\nToken: %s\nBody: %s" % (result.status_code, token, result.content))
    raise ApiError('/index', "Exception loading token from body: %s" % result.content)

  if (result.status_code == 200):
    return notes
  else:
    raise ApiError('/index', "Exception retrieving notes from index.")

def search(query, token, email, max_results=10, offset_index=0):
  email = email.replace("+", "%2B")
  url = "https://simple-note.appspot.com/api/search?query=%s&results=%s&offset=%sauth=%s&email=%s" % (query, max_results, offset_index, token, email)
  result = urlfetch.fetch(url=url,
                          method=urlfetch.GET)
  notes = simplejson.loads(result.content)

  if (result.status_code == 200):
    return notes
  else:
    raise ApiError('/search', "Exception searching notes for '%s'" % query)

def get_note(key, token, email):
  email = email.replace("+", "%2B")
  url = "https://simple-note.appspot.com/api/note?key=%s&auth=%s&email=%s" % (key, token, email)
  result = urlfetch.fetch(url=url,
                          method=urlfetch.GET)

  if (result.status_code == 200):
    note = {
      'content': result.content,
      'key': key,
      'modified': mkdatetime(result.headers['note-modifydate']),
      'created': mkdatetime(result.headers['note-createdate'])
    }
    return note
  else:
    logging.error("Bad key: '%s'" % key)
    raise ApiError('/note', "Exception retrieving note with key '%s'" % key)

# also supports setting date modified; date format is not documented,
# is presumed to be GMT
def update_note(key, note_body, token, email):
  email = email.replace("+", "%2B")
  url = "https://simple-note.appspot.com/api/note?key=%s&auth=%s&email=%s" % (key, token, email)
  payload = base64.b64encode(unicode(note_body))

  result = urlfetch.fetch(url=url,
                          method=urlfetch.POST,
                          payload=payload)

  if (result.status_code == 200):
    return result.content.strip()
  else:
    raise ApiError('/note', "Exception updating note with key '%s'" % key)

def create_note(note_body, token, email):
  email = email.replace("+", "%2B")
  url = "https://simple-note.appspot.com/api/note?auth=%s&email=%s" % (token, email)
  payload = base64.b64encode(unicode(note_body))

  result = urlfetch.fetch(url=url,
                          method=urlfetch.POST,
                          payload=payload)

  if (result.status_code == 200):
    return result.content.strip()
  else:
    raise ApiError('/note', 'Exception creating note.')

def delete_note(key, token, email):
  email = email.replace("+", "%2B")
  url = "https://simple-note.appspot.com/api/delete?key=%s&auth=%s&email=%s" % (key, token, email)
  result = urlfetch.fetch(url=url,
                          method=urlfetch.GET)

  if (result.status_code == 200):
    return True
  else:
    raise ApiError('/delete', "Exception deleting note with key '%s'" % key)

########NEW FILE########
__FILENAME__ = composer

__all__ = ['Composer', 'ComposerError']

from error import MarkedYAMLError
from events import *
from nodes import *

class ComposerError(MarkedYAMLError):
    pass

class Composer(object):

    def __init__(self):
        self.anchors = {}

    def check_node(self):
        # Drop the STREAM-START event.
        if self.check_event(StreamStartEvent):
            self.get_event()

        # If there are more documents available?
        return not self.check_event(StreamEndEvent)

    def get_node(self):
        # Get the root node of the next document.
        if not self.check_event(StreamEndEvent):
            return self.compose_document()

    def get_single_node(self):
        # Drop the STREAM-START event.
        self.get_event()

        # Compose a document if the stream is not empty.
        document = None
        if not self.check_event(StreamEndEvent):
            document = self.compose_document()

        # Ensure that the stream contains no more documents.
        if not self.check_event(StreamEndEvent):
            event = self.get_event()
            raise ComposerError("expected a single document in the stream",
                    document.start_mark, "but found another document",
                    event.start_mark)

        # Drop the STREAM-END event.
        self.get_event()

        return document

    def compose_document(self):
        # Drop the DOCUMENT-START event.
        self.get_event()

        # Compose the root node.
        node = self.compose_node(None, None)

        # Drop the DOCUMENT-END event.
        self.get_event()

        self.anchors = {}
        return node

    def compose_node(self, parent, index):
        if self.check_event(AliasEvent):
            event = self.get_event()
            anchor = event.anchor
            if anchor not in self.anchors:
                raise ComposerError(None, None, "found undefined alias %r"
                        % anchor.encode('utf-8'), event.start_mark)
            return self.anchors[anchor]
        event = self.peek_event()
        anchor = event.anchor
        if anchor is not None:
            if anchor in self.anchors:
                raise ComposerError("found duplicate anchor %r; first occurence"
                        % anchor.encode('utf-8'), self.anchors[anchor].start_mark,
                        "second occurence", event.start_mark)
        self.descend_resolver(parent, index)
        if self.check_event(ScalarEvent):
            node = self.compose_scalar_node(anchor)
        elif self.check_event(SequenceStartEvent):
            node = self.compose_sequence_node(anchor)
        elif self.check_event(MappingStartEvent):
            node = self.compose_mapping_node(anchor)
        self.ascend_resolver()
        return node

    def compose_scalar_node(self, anchor):
        event = self.get_event()
        tag = event.tag
        if tag is None or tag == u'!':
            tag = self.resolve(ScalarNode, event.value, event.implicit)
        node = ScalarNode(tag, event.value,
                event.start_mark, event.end_mark, style=event.style)
        if anchor is not None:
            self.anchors[anchor] = node
        return node

    def compose_sequence_node(self, anchor):
        start_event = self.get_event()
        tag = start_event.tag
        if tag is None or tag == u'!':
            tag = self.resolve(SequenceNode, None, start_event.implicit)
        node = SequenceNode(tag, [],
                start_event.start_mark, None,
                flow_style=start_event.flow_style)
        if anchor is not None:
            self.anchors[anchor] = node
        index = 0
        while not self.check_event(SequenceEndEvent):
            node.value.append(self.compose_node(node, index))
            index += 1
        end_event = self.get_event()
        node.end_mark = end_event.end_mark
        return node

    def compose_mapping_node(self, anchor):
        start_event = self.get_event()
        tag = start_event.tag
        if tag is None or tag == u'!':
            tag = self.resolve(MappingNode, None, start_event.implicit)
        node = MappingNode(tag, [],
                start_event.start_mark, None,
                flow_style=start_event.flow_style)
        if anchor is not None:
            self.anchors[anchor] = node
        while not self.check_event(MappingEndEvent):
            #key_event = self.peek_event()
            item_key = self.compose_node(node, None)
            #if item_key in node.value:
            #    raise ComposerError("while composing a mapping", start_event.start_mark,
            #            "found duplicate key", key_event.start_mark)
            item_value = self.compose_node(node, item_key)
            #node.value[item_key] = item_value
            node.value.append((item_key, item_value))
        end_event = self.get_event()
        node.end_mark = end_event.end_mark
        return node


########NEW FILE########
__FILENAME__ = constructor

__all__ = ['BaseConstructor', 'SafeConstructor', 'Constructor',
    'ConstructorError']

from error import *
from nodes import *

import datetime

try:
    set
except NameError:
    from sets import Set as set

import binascii, re, sys, types

class ConstructorError(MarkedYAMLError):
    pass

class BaseConstructor(object):

    yaml_constructors = {}
    yaml_multi_constructors = {}

    def __init__(self):
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.state_generators = []
        self.deep_construct = False

    def check_data(self):
        # If there are more documents available?
        return self.check_node()

    def get_data(self):
        # Construct and return the next document.
        if self.check_node():
            return self.construct_document(self.get_node())

    def get_single_data(self):
        # Ensure that the stream contains a single document and construct it.
        node = self.get_single_node()
        if node is not None:
            return self.construct_document(node)
        return None

    def construct_document(self, node):
        data = self.construct_object(node)
        while self.state_generators:
            state_generators = self.state_generators
            self.state_generators = []
            for generator in state_generators:
                for dummy in generator:
                    pass
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.deep_construct = False
        return data

    def construct_object(self, node, deep=False):
        if deep:
            old_deep = self.deep_construct
            self.deep_construct = True
        if node in self.constructed_objects:
            return self.constructed_objects[node]
        if node in self.recursive_objects:
            raise ConstructorError(None, None,
                    "found unconstructable recursive node", node.start_mark)
        self.recursive_objects[node] = None
        constructor = None
        tag_suffix = None
        if node.tag in self.yaml_constructors:
            constructor = self.yaml_constructors[node.tag]
        else:
            for tag_prefix in self.yaml_multi_constructors:
                if node.tag.startswith(tag_prefix):
                    tag_suffix = node.tag[len(tag_prefix):]
                    constructor = self.yaml_multi_constructors[tag_prefix]
                    break
            else:
                if None in self.yaml_multi_constructors:
                    tag_suffix = node.tag
                    constructor = self.yaml_multi_constructors[None]
                elif None in self.yaml_constructors:
                    constructor = self.yaml_constructors[None]
                elif isinstance(node, ScalarNode):
                    constructor = self.__class__.construct_scalar
                elif isinstance(node, SequenceNode):
                    constructor = self.__class__.construct_sequence
                elif isinstance(node, MappingNode):
                    constructor = self.__class__.construct_mapping
        if tag_suffix is None:
            data = constructor(self, node)
        else:
            data = constructor(self, tag_suffix, node)
        if isinstance(data, types.GeneratorType):
            generator = data
            data = generator.next()
            if self.deep_construct:
                for dummy in generator:
                    pass
            else:
                self.state_generators.append(generator)
        self.constructed_objects[node] = data
        del self.recursive_objects[node]
        if deep:
            self.deep_construct = old_deep
        return data

    def construct_scalar(self, node):
        if not isinstance(node, ScalarNode):
            raise ConstructorError(None, None,
                    "expected a scalar node, but found %s" % node.id,
                    node.start_mark)
        return node.value

    def construct_sequence(self, node, deep=False):
        if not isinstance(node, SequenceNode):
            raise ConstructorError(None, None,
                    "expected a sequence node, but found %s" % node.id,
                    node.start_mark)
        return [self.construct_object(child, deep=deep)
                for child in node.value]

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError, exc:
                raise ConstructorError("while constructing a mapping", node.start_mark,
                        "found unacceptable key (%s)" % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

    def construct_pairs(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        pairs = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            value = self.construct_object(value_node, deep=deep)
            pairs.append((key, value))
        return pairs

    def add_constructor(cls, tag, constructor):
        if not 'yaml_constructors' in cls.__dict__:
            cls.yaml_constructors = cls.yaml_constructors.copy()
        cls.yaml_constructors[tag] = constructor
    add_constructor = classmethod(add_constructor)

    def add_multi_constructor(cls, tag_prefix, multi_constructor):
        if not 'yaml_multi_constructors' in cls.__dict__:
            cls.yaml_multi_constructors = cls.yaml_multi_constructors.copy()
        cls.yaml_multi_constructors[tag_prefix] = multi_constructor
    add_multi_constructor = classmethod(add_multi_constructor)

class SafeConstructor(BaseConstructor):

    def construct_scalar(self, node):
        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                if key_node.tag == u'tag:yaml.org,2002:value':
                    return self.construct_scalar(value_node)
        return BaseConstructor.construct_scalar(self, node)

    def flatten_mapping(self, node):
        merge = []
        index = 0
        while index < len(node.value):
            key_node, value_node = node.value[index]
            if key_node.tag == u'tag:yaml.org,2002:merge':
                del node.value[index]
                if isinstance(value_node, MappingNode):
                    self.flatten_mapping(value_node)
                    merge.extend(value_node.value)
                elif isinstance(value_node, SequenceNode):
                    submerge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, MappingNode):
                            raise ConstructorError("while constructing a mapping",
                                    node.start_mark,
                                    "expected a mapping for merging, but found %s"
                                    % subnode.id, subnode.start_mark)
                        self.flatten_mapping(subnode)
                        submerge.append(subnode.value)
                    submerge.reverse()
                    for value in submerge:
                        merge.extend(value)
                else:
                    raise ConstructorError("while constructing a mapping", node.start_mark,
                            "expected a mapping or list of mappings for merging, but found %s"
                            % value_node.id, value_node.start_mark)
            elif key_node.tag == u'tag:yaml.org,2002:value':
                key_node.tag = u'tag:yaml.org,2002:str'
                index += 1
            else:
                index += 1
        if merge:
            node.value = merge + node.value

    def construct_mapping(self, node, deep=False):
        if isinstance(node, MappingNode):
            self.flatten_mapping(node)
        return BaseConstructor.construct_mapping(self, node, deep=deep)

    def construct_yaml_null(self, node):
        self.construct_scalar(node)
        return None

    bool_values = {
        u'yes':     True,
        u'no':      False,
        u'true':    True,
        u'false':   False,
        u'on':      True,
        u'off':     False,
    }

    def construct_yaml_bool(self, node):
        value = self.construct_scalar(node)
        return self.bool_values[value.lower()]

    def construct_yaml_int(self, node):
        value = str(self.construct_scalar(node))
        value = value.replace('_', '')
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '0':
            return 0
        elif value.startswith('0b'):
            return sign*int(value[2:], 2)
        elif value.startswith('0x'):
            return sign*int(value[2:], 16)
        elif value[0] == '0':
            return sign*int(value, 8)
        elif ':' in value:
            digits = [int(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*int(value)

    inf_value = 1e300
    while inf_value != inf_value*inf_value:
        inf_value *= inf_value
    nan_value = -inf_value/inf_value   # Trying to make a quiet NaN (like C99).

    def construct_yaml_float(self, node):
        value = str(self.construct_scalar(node))
        value = value.replace('_', '').lower()
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '.inf':
            return sign*self.inf_value
        elif value == '.nan':
            return self.nan_value
        elif ':' in value:
            digits = [float(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0.0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*float(value)

    def construct_yaml_binary(self, node):
        value = self.construct_scalar(node)
        try:
            return str(value).decode('base64')
        except (binascii.Error, UnicodeEncodeError), exc:
            raise ConstructorError(None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark) 

    timestamp_regexp = re.compile(
            ur'''^(?P<year>[0-9][0-9][0-9][0-9])
                -(?P<month>[0-9][0-9]?)
                -(?P<day>[0-9][0-9]?)
                (?:(?:[Tt]|[ \t]+)
                (?P<hour>[0-9][0-9]?)
                :(?P<minute>[0-9][0-9])
                :(?P<second>[0-9][0-9])
                (?:\.(?P<fraction>[0-9]*))?
                (?:[ \t]*(?P<tz>Z|(?P<tz_sign>[-+])(?P<tz_hour>[0-9][0-9]?)
                (?::(?P<tz_minute>[0-9][0-9]))?))?)?$''', re.X)

    def construct_yaml_timestamp(self, node):
        value = self.construct_scalar(node)
        match = self.timestamp_regexp.match(node.value)
        values = match.groupdict()
        year = int(values['year'])
        month = int(values['month'])
        day = int(values['day'])
        if not values['hour']:
            return datetime.date(year, month, day)
        hour = int(values['hour'])
        minute = int(values['minute'])
        second = int(values['second'])
        fraction = 0
        if values['fraction']:
            fraction = values['fraction'][:6]
            while len(fraction) < 6:
                fraction += '0'
            fraction = int(fraction)
        delta = None
        if values['tz_sign']:
            tz_hour = int(values['tz_hour'])
            tz_minute = int(values['tz_minute'] or 0)
            delta = datetime.timedelta(hours=tz_hour, minutes=tz_minute)
            if values['tz_sign'] == '-':
                delta = -delta
        data = datetime.datetime(year, month, day, hour, minute, second, fraction)
        if delta:
            data -= delta
        return data

    def construct_yaml_omap(self, node):
        # Note: we do not check for duplicate keys, because it's too
        # CPU-expensive.
        omap = []
        yield omap
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing an ordered map", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            omap.append((key, value))

    def construct_yaml_pairs(self, node):
        # Note: the same code as `construct_yaml_omap`.
        pairs = []
        yield pairs
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing pairs", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            pairs.append((key, value))

    def construct_yaml_set(self, node):
        data = set()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_str(self, node):
        value = self.construct_scalar(node)
        try:
            return value.encode('ascii')
        except UnicodeEncodeError:
            return value

    def construct_yaml_seq(self, node):
        data = []
        yield data
        data.extend(self.construct_sequence(node))

    def construct_yaml_map(self, node):
        data = {}
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_object(self, node, cls):
        data = cls.__new__(cls)
        yield data
        if hasattr(data, '__setstate__'):
            state = self.construct_mapping(node, deep=True)
            data.__setstate__(state)
        else:
            state = self.construct_mapping(node)
            data.__dict__.update(state)

    def construct_undefined(self, node):
        raise ConstructorError(None, None,
                "could not determine a constructor for the tag %r" % node.tag.encode('utf-8'),
                node.start_mark)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:null',
        SafeConstructor.construct_yaml_null)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:bool',
        SafeConstructor.construct_yaml_bool)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:int',
        SafeConstructor.construct_yaml_int)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:float',
        SafeConstructor.construct_yaml_float)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:binary',
        SafeConstructor.construct_yaml_binary)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:timestamp',
        SafeConstructor.construct_yaml_timestamp)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:omap',
        SafeConstructor.construct_yaml_omap)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:pairs',
        SafeConstructor.construct_yaml_pairs)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:set',
        SafeConstructor.construct_yaml_set)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:str',
        SafeConstructor.construct_yaml_str)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:seq',
        SafeConstructor.construct_yaml_seq)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:map',
        SafeConstructor.construct_yaml_map)

SafeConstructor.add_constructor(None,
        SafeConstructor.construct_undefined)

class Constructor(SafeConstructor):

    def construct_python_str(self, node):
        return self.construct_scalar(node).encode('utf-8')

    def construct_python_unicode(self, node):
        return self.construct_scalar(node)

    def construct_python_long(self, node):
        return long(self.construct_yaml_int(node))

    def construct_python_complex(self, node):
       return complex(self.construct_scalar(node))

    def construct_python_tuple(self, node):
        return tuple(self.construct_sequence(node))

    def find_python_module(self, name, mark):
        if not name:
            raise ConstructorError("while constructing a Python module", mark,
                    "expected non-empty name appended to the tag", mark)
        try:
            __import__(name)
        except ImportError, exc:
            raise ConstructorError("while constructing a Python module", mark,
                    "cannot find module %r (%s)" % (name.encode('utf-8'), exc), mark)
        return sys.modules[name]

    def find_python_name(self, name, mark):
        if not name:
            raise ConstructorError("while constructing a Python object", mark,
                    "expected non-empty name appended to the tag", mark)
        if u'.' in name:
            # Python 2.4 only
            #module_name, object_name = name.rsplit('.', 1)
            items = name.split('.')
            object_name = items.pop()
            module_name = '.'.join(items)
        else:
            module_name = '__builtin__'
            object_name = name
        try:
            __import__(module_name)
        except ImportError, exc:
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find module %r (%s)" % (module_name.encode('utf-8'), exc), mark)
        module = sys.modules[module_name]
        if not hasattr(module, object_name):
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find %r in the module %r" % (object_name.encode('utf-8'),
                        module.__name__), mark)
        return getattr(module, object_name)

    def construct_python_name(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python name", node.start_mark,
                    "expected the empty value, but found %r" % value.encode('utf-8'),
                    node.start_mark)
        return self.find_python_name(suffix, node.start_mark)

    def construct_python_module(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python module", node.start_mark,
                    "expected the empty value, but found %r" % value.encode('utf-8'),
                    node.start_mark)
        return self.find_python_module(suffix, node.start_mark)

    class classobj: pass

    def make_python_instance(self, suffix, node,
            args=None, kwds=None, newobj=False):
        if not args:
            args = []
        if not kwds:
            kwds = {}
        cls = self.find_python_name(suffix, node.start_mark)
        if newobj and isinstance(cls, type(self.classobj))  \
                and not args and not kwds:
            instance = self.classobj()
            instance.__class__ = cls
            return instance
        elif newobj and isinstance(cls, type):
            return cls.__new__(cls, *args, **kwds)
        else:
            return cls(*args, **kwds)

    def set_python_instance_state(self, instance, state):
        if hasattr(instance, '__setstate__'):
            instance.__setstate__(state)
        else:
            slotstate = {}
            if isinstance(state, tuple) and len(state) == 2:
                state, slotstate = state
            if hasattr(instance, '__dict__'):
                instance.__dict__.update(state)
            elif state:
                slotstate.update(state)
            for key, value in slotstate.items():
                setattr(object, key, value)

    def construct_python_object(self, suffix, node):
        # Format:
        #   !!python/object:module.name { ... state ... }
        instance = self.make_python_instance(suffix, node, newobj=True)
        yield instance
        deep = hasattr(instance, '__setstate__')
        state = self.construct_mapping(node, deep=deep)
        self.set_python_instance_state(instance, state)

    def construct_python_object_apply(self, suffix, node, newobj=False):
        # Format:
        #   !!python/object/apply       # (or !!python/object/new)
        #   args: [ ... arguments ... ]
        #   kwds: { ... keywords ... }
        #   state: ... state ...
        #   listitems: [ ... listitems ... ]
        #   dictitems: { ... dictitems ... }
        # or short format:
        #   !!python/object/apply [ ... arguments ... ]
        # The difference between !!python/object/apply and !!python/object/new
        # is how an object is created, check make_python_instance for details.
        if isinstance(node, SequenceNode):
            args = self.construct_sequence(node, deep=True)
            kwds = {}
            state = {}
            listitems = []
            dictitems = {}
        else:
            value = self.construct_mapping(node, deep=True)
            args = value.get('args', [])
            kwds = value.get('kwds', {})
            state = value.get('state', {})
            listitems = value.get('listitems', [])
            dictitems = value.get('dictitems', {})
        instance = self.make_python_instance(suffix, node, args, kwds, newobj)
        if state:
            self.set_python_instance_state(instance, state)
        if listitems:
            instance.extend(listitems)
        if dictitems:
            for key in dictitems:
                instance[key] = dictitems[key]
        return instance

    def construct_python_object_new(self, suffix, node):
        return self.construct_python_object_apply(suffix, node, newobj=True)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/none',
    Constructor.construct_yaml_null)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/bool',
    Constructor.construct_yaml_bool)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/str',
    Constructor.construct_python_str)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/unicode',
    Constructor.construct_python_unicode)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/int',
    Constructor.construct_yaml_int)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/long',
    Constructor.construct_python_long)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/float',
    Constructor.construct_yaml_float)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/complex',
    Constructor.construct_python_complex)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/list',
    Constructor.construct_yaml_seq)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/tuple',
    Constructor.construct_python_tuple)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/dict',
    Constructor.construct_yaml_map)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/name:',
    Constructor.construct_python_name)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/module:',
    Constructor.construct_python_module)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object:',
    Constructor.construct_python_object)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object/apply:',
    Constructor.construct_python_object_apply)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object/new:',
    Constructor.construct_python_object_new)


########NEW FILE########
__FILENAME__ = cyaml

__all__ = ['CBaseLoader', 'CSafeLoader', 'CLoader',
        'CBaseDumper', 'CSafeDumper', 'CDumper']

from _yaml import CParser, CEmitter

from constructor import *

from serializer import *
from representer import *

from resolver import *

class CBaseLoader(CParser, BaseConstructor, BaseResolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        BaseConstructor.__init__(self)
        BaseResolver.__init__(self)

class CSafeLoader(CParser, SafeConstructor, Resolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

class CLoader(CParser, Constructor, Resolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        Constructor.__init__(self)
        Resolver.__init__(self)

class CBaseDumper(CEmitter, BaseRepresenter, BaseResolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width, encoding=encoding,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class CSafeDumper(CEmitter, SafeRepresenter, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width, encoding=encoding,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        SafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class CDumper(CEmitter, Serializer, Representer, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width, encoding=encoding,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = dumper

__all__ = ['BaseDumper', 'SafeDumper', 'Dumper']

from emitter import *
from serializer import *
from representer import *
from resolver import *

class BaseDumper(Emitter, Serializer, BaseRepresenter, BaseResolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class SafeDumper(Emitter, Serializer, SafeRepresenter, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        SafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class Dumper(Emitter, Serializer, Representer, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = emitter

# Emitter expects events obeying the following grammar:
# stream ::= STREAM-START document* STREAM-END
# document ::= DOCUMENT-START node DOCUMENT-END
# node ::= SCALAR | sequence | mapping
# sequence ::= SEQUENCE-START node* SEQUENCE-END
# mapping ::= MAPPING-START (node node)* MAPPING-END

__all__ = ['Emitter', 'EmitterError']

from error import YAMLError
from events import *

class EmitterError(YAMLError):
    pass

class ScalarAnalysis(object):
    def __init__(self, scalar, empty, multiline,
            allow_flow_plain, allow_block_plain,
            allow_single_quoted, allow_double_quoted,
            allow_block):
        self.scalar = scalar
        self.empty = empty
        self.multiline = multiline
        self.allow_flow_plain = allow_flow_plain
        self.allow_block_plain = allow_block_plain
        self.allow_single_quoted = allow_single_quoted
        self.allow_double_quoted = allow_double_quoted
        self.allow_block = allow_block

class Emitter(object):

    DEFAULT_TAG_PREFIXES = {
        u'!' : u'!',
        u'tag:yaml.org,2002:' : u'!!',
    }

    def __init__(self, stream, canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None):

        # The stream should have the methods `write` and possibly `flush`.
        self.stream = stream

        # Encoding can be overriden by STREAM-START.
        self.encoding = None

        # Emitter is a state machine with a stack of states to handle nested
        # structures.
        self.states = []
        self.state = self.expect_stream_start

        # Current event and the event queue.
        self.events = []
        self.event = None

        # The current indentation level and the stack of previous indents.
        self.indents = []
        self.indent = None

        # Flow level.
        self.flow_level = 0

        # Contexts.
        self.root_context = False
        self.sequence_context = False
        self.mapping_context = False
        self.simple_key_context = False

        # Characteristics of the last emitted character:
        #  - current position.
        #  - is it a whitespace?
        #  - is it an indention character
        #    (indentation space, '-', '?', or ':')?
        self.line = 0
        self.column = 0
        self.whitespace = True
        self.indention = True

        # Whether the document requires an explicit document indicator
        self.open_ended = False

        # Formatting details.
        self.canonical = canonical
        self.allow_unicode = allow_unicode
        self.best_indent = 2
        if indent and 1 < indent < 10:
            self.best_indent = indent
        self.best_width = 80
        if width and width > self.best_indent*2:
            self.best_width = width
        self.best_line_break = u'\n'
        if line_break in [u'\r', u'\n', u'\r\n']:
            self.best_line_break = line_break

        # Tag prefixes.
        self.tag_prefixes = None

        # Prepared anchor and tag.
        self.prepared_anchor = None
        self.prepared_tag = None

        # Scalar analysis and style.
        self.analysis = None
        self.style = None

    def emit(self, event):
        self.events.append(event)
        while not self.need_more_events():
            self.event = self.events.pop(0)
            self.state()
            self.event = None

    # In some cases, we wait for a few next events before emitting.

    def need_more_events(self):
        if not self.events:
            return True
        event = self.events[0]
        if isinstance(event, DocumentStartEvent):
            return self.need_events(1)
        elif isinstance(event, SequenceStartEvent):
            return self.need_events(2)
        elif isinstance(event, MappingStartEvent):
            return self.need_events(3)
        else:
            return False

    def need_events(self, count):
        level = 0
        for event in self.events[1:]:
            if isinstance(event, (DocumentStartEvent, CollectionStartEvent)):
                level += 1
            elif isinstance(event, (DocumentEndEvent, CollectionEndEvent)):
                level -= 1
            elif isinstance(event, StreamEndEvent):
                level = -1
            if level < 0:
                return False
        return (len(self.events) < count+1)

    def increase_indent(self, flow=False, indentless=False):
        self.indents.append(self.indent)
        if self.indent is None:
            if flow:
                self.indent = self.best_indent
            else:
                self.indent = 0
        elif not indentless:
            self.indent += self.best_indent

    # States.

    # Stream handlers.

    def expect_stream_start(self):
        if isinstance(self.event, StreamStartEvent):
            if self.event.encoding and not getattr(self.stream, 'encoding', None):
                self.encoding = self.event.encoding
            self.write_stream_start()
            self.state = self.expect_first_document_start
        else:
            raise EmitterError("expected StreamStartEvent, but got %s"
                    % self.event)

    def expect_nothing(self):
        raise EmitterError("expected nothing, but got %s" % self.event)

    # Document handlers.

    def expect_first_document_start(self):
        return self.expect_document_start(first=True)

    def expect_document_start(self, first=False):
        if isinstance(self.event, DocumentStartEvent):
            if (self.event.version or self.event.tags) and self.open_ended:
                self.write_indicator(u'...', True)
                self.write_indent()
            if self.event.version:
                version_text = self.prepare_version(self.event.version)
                self.write_version_directive(version_text)
            self.tag_prefixes = self.DEFAULT_TAG_PREFIXES.copy()
            if self.event.tags:
                handles = self.event.tags.keys()
                handles.sort()
                for handle in handles:
                    prefix = self.event.tags[handle]
                    self.tag_prefixes[prefix] = handle
                    handle_text = self.prepare_tag_handle(handle)
                    prefix_text = self.prepare_tag_prefix(prefix)
                    self.write_tag_directive(handle_text, prefix_text)
            implicit = (first and not self.event.explicit and not self.canonical
                    and not self.event.version and not self.event.tags
                    and not self.check_empty_document())
            if not implicit:
                self.write_indent()
                self.write_indicator(u'---', True)
                if self.canonical:
                    self.write_indent()
            self.state = self.expect_document_root
        elif isinstance(self.event, StreamEndEvent):
            if self.open_ended:
                self.write_indicator(u'...', True)
                self.write_indent()
            self.write_stream_end()
            self.state = self.expect_nothing
        else:
            raise EmitterError("expected DocumentStartEvent, but got %s"
                    % self.event)

    def expect_document_end(self):
        if isinstance(self.event, DocumentEndEvent):
            self.write_indent()
            if self.event.explicit:
                self.write_indicator(u'...', True)
                self.write_indent()
            self.flush_stream()
            self.state = self.expect_document_start
        else:
            raise EmitterError("expected DocumentEndEvent, but got %s"
                    % self.event)

    def expect_document_root(self):
        self.states.append(self.expect_document_end)
        self.expect_node(root=True)

    # Node handlers.

    def expect_node(self, root=False, sequence=False, mapping=False,
            simple_key=False):
        self.root_context = root
        self.sequence_context = sequence
        self.mapping_context = mapping
        self.simple_key_context = simple_key
        if isinstance(self.event, AliasEvent):
            self.expect_alias()
        elif isinstance(self.event, (ScalarEvent, CollectionStartEvent)):
            self.process_anchor(u'&')
            self.process_tag()
            if isinstance(self.event, ScalarEvent):
                self.expect_scalar()
            elif isinstance(self.event, SequenceStartEvent):
                if self.flow_level or self.canonical or self.event.flow_style   \
                        or self.check_empty_sequence():
                    self.expect_flow_sequence()
                else:
                    self.expect_block_sequence()
            elif isinstance(self.event, MappingStartEvent):
                if self.flow_level or self.canonical or self.event.flow_style   \
                        or self.check_empty_mapping():
                    self.expect_flow_mapping()
                else:
                    self.expect_block_mapping()
        else:
            raise EmitterError("expected NodeEvent, but got %s" % self.event)

    def expect_alias(self):
        if self.event.anchor is None:
            raise EmitterError("anchor is not specified for alias")
        self.process_anchor(u'*')
        self.state = self.states.pop()

    def expect_scalar(self):
        self.increase_indent(flow=True)
        self.process_scalar()
        self.indent = self.indents.pop()
        self.state = self.states.pop()

    # Flow sequence handlers.

    def expect_flow_sequence(self):
        self.write_indicator(u'[', True, whitespace=True)
        self.flow_level += 1
        self.increase_indent(flow=True)
        self.state = self.expect_first_flow_sequence_item

    def expect_first_flow_sequence_item(self):
        if isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            self.write_indicator(u']', False)
            self.state = self.states.pop()
        else:
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            self.states.append(self.expect_flow_sequence_item)
            self.expect_node(sequence=True)

    def expect_flow_sequence_item(self):
        if isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            if self.canonical:
                self.write_indicator(u',', False)
                self.write_indent()
            self.write_indicator(u']', False)
            self.state = self.states.pop()
        else:
            self.write_indicator(u',', False)
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            self.states.append(self.expect_flow_sequence_item)
            self.expect_node(sequence=True)

    # Flow mapping handlers.

    def expect_flow_mapping(self):
        self.write_indicator(u'{', True, whitespace=True)
        self.flow_level += 1
        self.increase_indent(flow=True)
        self.state = self.expect_first_flow_mapping_key

    def expect_first_flow_mapping_key(self):
        if isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            self.write_indicator(u'}', False)
            self.state = self.states.pop()
        else:
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            if not self.canonical and self.check_simple_key():
                self.states.append(self.expect_flow_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator(u'?', True)
                self.states.append(self.expect_flow_mapping_value)
                self.expect_node(mapping=True)

    def expect_flow_mapping_key(self):
        if isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            if self.canonical:
                self.write_indicator(u',', False)
                self.write_indent()
            self.write_indicator(u'}', False)
            self.state = self.states.pop()
        else:
            self.write_indicator(u',', False)
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            if not self.canonical and self.check_simple_key():
                self.states.append(self.expect_flow_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator(u'?', True)
                self.states.append(self.expect_flow_mapping_value)
                self.expect_node(mapping=True)

    def expect_flow_mapping_simple_value(self):
        self.write_indicator(u':', False)
        self.states.append(self.expect_flow_mapping_key)
        self.expect_node(mapping=True)

    def expect_flow_mapping_value(self):
        if self.canonical or self.column > self.best_width:
            self.write_indent()
        self.write_indicator(u':', True)
        self.states.append(self.expect_flow_mapping_key)
        self.expect_node(mapping=True)

    # Block sequence handlers.

    def expect_block_sequence(self):
        indentless = (self.mapping_context and not self.indention)
        self.increase_indent(flow=False, indentless=indentless)
        self.state = self.expect_first_block_sequence_item

    def expect_first_block_sequence_item(self):
        return self.expect_block_sequence_item(first=True)

    def expect_block_sequence_item(self, first=False):
        if not first and isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.state = self.states.pop()
        else:
            self.write_indent()
            self.write_indicator(u'-', True, indention=True)
            self.states.append(self.expect_block_sequence_item)
            self.expect_node(sequence=True)

    # Block mapping handlers.

    def expect_block_mapping(self):
        self.increase_indent(flow=False)
        self.state = self.expect_first_block_mapping_key

    def expect_first_block_mapping_key(self):
        return self.expect_block_mapping_key(first=True)

    def expect_block_mapping_key(self, first=False):
        if not first and isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.state = self.states.pop()
        else:
            self.write_indent()
            if self.check_simple_key():
                self.states.append(self.expect_block_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator(u'?', True, indention=True)
                self.states.append(self.expect_block_mapping_value)
                self.expect_node(mapping=True)

    def expect_block_mapping_simple_value(self):
        self.write_indicator(u':', False)
        self.states.append(self.expect_block_mapping_key)
        self.expect_node(mapping=True)

    def expect_block_mapping_value(self):
        self.write_indent()
        self.write_indicator(u':', True, indention=True)
        self.states.append(self.expect_block_mapping_key)
        self.expect_node(mapping=True)

    # Checkers.

    def check_empty_sequence(self):
        return (isinstance(self.event, SequenceStartEvent) and self.events
                and isinstance(self.events[0], SequenceEndEvent))

    def check_empty_mapping(self):
        return (isinstance(self.event, MappingStartEvent) and self.events
                and isinstance(self.events[0], MappingEndEvent))

    def check_empty_document(self):
        if not isinstance(self.event, DocumentStartEvent) or not self.events:
            return False
        event = self.events[0]
        return (isinstance(event, ScalarEvent) and event.anchor is None
                and event.tag is None and event.implicit and event.value == u'')

    def check_simple_key(self):
        length = 0
        if isinstance(self.event, NodeEvent) and self.event.anchor is not None:
            if self.prepared_anchor is None:
                self.prepared_anchor = self.prepare_anchor(self.event.anchor)
            length += len(self.prepared_anchor)
        if isinstance(self.event, (ScalarEvent, CollectionStartEvent))  \
                and self.event.tag is not None:
            if self.prepared_tag is None:
                self.prepared_tag = self.prepare_tag(self.event.tag)
            length += len(self.prepared_tag)
        if isinstance(self.event, ScalarEvent):
            if self.analysis is None:
                self.analysis = self.analyze_scalar(self.event.value)
            length += len(self.analysis.scalar)
        return (length < 128 and (isinstance(self.event, AliasEvent)
            or (isinstance(self.event, ScalarEvent)
                    and not self.analysis.empty and not self.analysis.multiline)
            or self.check_empty_sequence() or self.check_empty_mapping()))

    # Anchor, Tag, and Scalar processors.

    def process_anchor(self, indicator):
        if self.event.anchor is None:
            self.prepared_anchor = None
            return
        if self.prepared_anchor is None:
            self.prepared_anchor = self.prepare_anchor(self.event.anchor)
        if self.prepared_anchor:
            self.write_indicator(indicator+self.prepared_anchor, True)
        self.prepared_anchor = None

    def process_tag(self):
        tag = self.event.tag
        if isinstance(self.event, ScalarEvent):
            if self.style is None:
                self.style = self.choose_scalar_style()
            if ((not self.canonical or tag is None) and
                ((self.style == '' and self.event.implicit[0])
                        or (self.style != '' and self.event.implicit[1]))):
                self.prepared_tag = None
                return
            if self.event.implicit[0] and tag is None:
                tag = u'!'
                self.prepared_tag = None
        else:
            if (not self.canonical or tag is None) and self.event.implicit:
                self.prepared_tag = None
                return
        if tag is None:
            raise EmitterError("tag is not specified")
        if self.prepared_tag is None:
            self.prepared_tag = self.prepare_tag(tag)
        if self.prepared_tag:
            self.write_indicator(self.prepared_tag, True)
        self.prepared_tag = None

    def choose_scalar_style(self):
        if self.analysis is None:
            self.analysis = self.analyze_scalar(self.event.value)
        if self.event.style == '"' or self.canonical:
            return '"'
        if not self.event.style and self.event.implicit[0]:
            if (not (self.simple_key_context and
                    (self.analysis.empty or self.analysis.multiline))
                and (self.flow_level and self.analysis.allow_flow_plain
                    or (not self.flow_level and self.analysis.allow_block_plain))):
                return ''
        if self.event.style and self.event.style in '|>':
            if (not self.flow_level and not self.simple_key_context
                    and self.analysis.allow_block):
                return self.event.style
        if not self.event.style or self.event.style == '\'':
            if (self.analysis.allow_single_quoted and
                    not (self.simple_key_context and self.analysis.multiline)):
                return '\''
        return '"'

    def process_scalar(self):
        if self.analysis is None:
            self.analysis = self.analyze_scalar(self.event.value)
        if self.style is None:
            self.style = self.choose_scalar_style()
        split = (not self.simple_key_context)
        #if self.analysis.multiline and split    \
        #        and (not self.style or self.style in '\'\"'):
        #    self.write_indent()
        if self.style == '"':
            self.write_double_quoted(self.analysis.scalar, split)
        elif self.style == '\'':
            self.write_single_quoted(self.analysis.scalar, split)
        elif self.style == '>':
            self.write_folded(self.analysis.scalar)
        elif self.style == '|':
            self.write_literal(self.analysis.scalar)
        else:
            self.write_plain(self.analysis.scalar, split)
        self.analysis = None
        self.style = None

    # Analyzers.

    def prepare_version(self, version):
        major, minor = version
        if major != 1:
            raise EmitterError("unsupported YAML version: %d.%d" % (major, minor))
        return u'%d.%d' % (major, minor)

    def prepare_tag_handle(self, handle):
        if not handle:
            raise EmitterError("tag handle must not be empty")
        if handle[0] != u'!' or handle[-1] != u'!':
            raise EmitterError("tag handle must start and end with '!': %r"
                    % (handle.encode('utf-8')))
        for ch in handle[1:-1]:
            if not (u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'  \
                    or ch in u'-_'):
                raise EmitterError("invalid character %r in the tag handle: %r"
                        % (ch.encode('utf-8'), handle.encode('utf-8')))
        return handle

    def prepare_tag_prefix(self, prefix):
        if not prefix:
            raise EmitterError("tag prefix must not be empty")
        chunks = []
        start = end = 0
        if prefix[0] == u'!':
            end = 1
        while end < len(prefix):
            ch = prefix[end]
            if u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'   \
                    or ch in u'-;/?!:@&=+$,_.~*\'()[]':
                end += 1
            else:
                if start < end:
                    chunks.append(prefix[start:end])
                start = end = end+1
                data = ch.encode('utf-8')
                for ch in data:
                    chunks.append(u'%%%02X' % ord(ch))
        if start < end:
            chunks.append(prefix[start:end])
        return u''.join(chunks)

    def prepare_tag(self, tag):
        if not tag:
            raise EmitterError("tag must not be empty")
        if tag == u'!':
            return tag
        handle = None
        suffix = tag
        for prefix in self.tag_prefixes:
            if tag.startswith(prefix)   \
                    and (prefix == u'!' or len(prefix) < len(tag)):
                handle = self.tag_prefixes[prefix]
                suffix = tag[len(prefix):]
        chunks = []
        start = end = 0
        while end < len(suffix):
            ch = suffix[end]
            if u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'   \
                    or ch in u'-;/?:@&=+$,_.~*\'()[]'   \
                    or (ch == u'!' and handle != u'!'):
                end += 1
            else:
                if start < end:
                    chunks.append(suffix[start:end])
                start = end = end+1
                data = ch.encode('utf-8')
                for ch in data:
                    chunks.append(u'%%%02X' % ord(ch))
        if start < end:
            chunks.append(suffix[start:end])
        suffix_text = u''.join(chunks)
        if handle:
            return u'%s%s' % (handle, suffix_text)
        else:
            return u'!<%s>' % suffix_text

    def prepare_anchor(self, anchor):
        if not anchor:
            raise EmitterError("anchor must not be empty")
        for ch in anchor:
            if not (u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'  \
                    or ch in u'-_'):
                raise EmitterError("invalid character %r in the anchor: %r"
                        % (ch.encode('utf-8'), anchor.encode('utf-8')))
        return anchor

    def analyze_scalar(self, scalar):

        # Empty scalar is a special case.
        if not scalar:
            return ScalarAnalysis(scalar=scalar, empty=True, multiline=False,
                    allow_flow_plain=False, allow_block_plain=True,
                    allow_single_quoted=True, allow_double_quoted=True,
                    allow_block=False)

        # Indicators and special characters.
        block_indicators = False
        flow_indicators = False
        line_breaks = False
        special_characters = False

        # Important whitespace combinations.
        leading_space = False
        leading_break = False
        trailing_space = False
        trailing_break = False
        break_space = False
        space_break = False

        # Check document indicators.
        if scalar.startswith(u'---') or scalar.startswith(u'...'):
            block_indicators = True
            flow_indicators = True

        # First character or preceded by a whitespace.
        preceeded_by_whitespace = True

        # Last character or followed by a whitespace.
        followed_by_whitespace = (len(scalar) == 1 or
                scalar[1] in u'\0 \t\r\n\x85\u2028\u2029')

        # The previous character is a space.
        previous_space = False

        # The previous character is a break.
        previous_break = False

        index = 0
        while index < len(scalar):
            ch = scalar[index]

            # Check for indicators.
            if index == 0:
                # Leading indicators are special characters.
                if ch in u'#,[]{}&*!|>\'\"%@`': 
                    flow_indicators = True
                    block_indicators = True
                if ch in u'?:':
                    flow_indicators = True
                    if followed_by_whitespace:
                        block_indicators = True
                if ch == u'-' and followed_by_whitespace:
                    flow_indicators = True
                    block_indicators = True
            else:
                # Some indicators cannot appear within a scalar as well.
                if ch in u',?[]{}':
                    flow_indicators = True
                if ch == u':':
                    flow_indicators = True
                    if followed_by_whitespace:
                        block_indicators = True
                if ch == u'#' and preceeded_by_whitespace:
                    flow_indicators = True
                    block_indicators = True

            # Check for line breaks, special, and unicode characters.
            if ch in u'\n\x85\u2028\u2029':
                line_breaks = True
            if not (ch == u'\n' or u'\x20' <= ch <= u'\x7E'):
                if (ch == u'\x85' or u'\xA0' <= ch <= u'\uD7FF'
                        or u'\uE000' <= ch <= u'\uFFFD') and ch != u'\uFEFF':
                    unicode_characters = True
                    if not self.allow_unicode:
                        special_characters = True
                else:
                    special_characters = True

            # Detect important whitespace combinations.
            if ch == u' ':
                if index == 0:
                    leading_space = True
                if index == len(scalar)-1:
                    trailing_space = True
                if previous_break:
                    break_space = True
                previous_space = True
                previous_break = False
            elif ch in u'\n\x85\u2028\u2029':
                if index == 0:
                    leading_break = True
                if index == len(scalar)-1:
                    trailing_break = True
                if previous_space:
                    space_break = True
                previous_space = False
                previous_break = True
            else:
                previous_space = False
                previous_break = False

            # Prepare for the next character.
            index += 1
            preceeded_by_whitespace = (ch in u'\0 \t\r\n\x85\u2028\u2029')
            followed_by_whitespace = (index+1 >= len(scalar) or
                    scalar[index+1] in u'\0 \t\r\n\x85\u2028\u2029')

        # Let's decide what styles are allowed.
        allow_flow_plain = True
        allow_block_plain = True
        allow_single_quoted = True
        allow_double_quoted = True
        allow_block = True

        # Leading and trailing whitespaces are bad for plain scalars.
        if (leading_space or leading_break
                or trailing_space or trailing_break):
            allow_flow_plain = allow_block_plain = False

        # We do not permit trailing spaces for block scalars.
        if trailing_space:
            allow_block = False

        # Spaces at the beginning of a new line are only acceptable for block
        # scalars.
        if break_space:
            allow_flow_plain = allow_block_plain = allow_single_quoted = False

        # Spaces followed by breaks, as well as special character are only
        # allowed for double quoted scalars.
        if space_break or special_characters:
            allow_flow_plain = allow_block_plain =  \
            allow_single_quoted = allow_block = False

        # Although the plain scalar writer supports breaks, we never emit
        # multiline plain scalars.
        if line_breaks:
            allow_flow_plain = allow_block_plain = False

        # Flow indicators are forbidden for flow plain scalars.
        if flow_indicators:
            allow_flow_plain = False

        # Block indicators are forbidden for block plain scalars.
        if block_indicators:
            allow_block_plain = False

        return ScalarAnalysis(scalar=scalar,
                empty=False, multiline=line_breaks,
                allow_flow_plain=allow_flow_plain,
                allow_block_plain=allow_block_plain,
                allow_single_quoted=allow_single_quoted,
                allow_double_quoted=allow_double_quoted,
                allow_block=allow_block)

    # Writers.

    def flush_stream(self):
        if hasattr(self.stream, 'flush'):
            self.stream.flush()

    def write_stream_start(self):
        # Write BOM if needed.
        if self.encoding and self.encoding.startswith('utf-16'):
            self.stream.write(u'\xFF\xFE'.encode(self.encoding))

    def write_stream_end(self):
        self.flush_stream()

    def write_indicator(self, indicator, need_whitespace,
            whitespace=False, indention=False):
        if self.whitespace or not need_whitespace:
            data = indicator
        else:
            data = u' '+indicator
        self.whitespace = whitespace
        self.indention = self.indention and indention
        self.column += len(data)
        self.open_ended = False
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)

    def write_indent(self):
        indent = self.indent or 0
        if not self.indention or self.column > indent   \
                or (self.column == indent and not self.whitespace):
            self.write_line_break()
        if self.column < indent:
            self.whitespace = True
            data = u' '*(indent-self.column)
            self.column = indent
            if self.encoding:
                data = data.encode(self.encoding)
            self.stream.write(data)

    def write_line_break(self, data=None):
        if data is None:
            data = self.best_line_break
        self.whitespace = True
        self.indention = True
        self.line += 1
        self.column = 0
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)

    def write_version_directive(self, version_text):
        data = u'%%YAML %s' % version_text
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)
        self.write_line_break()

    def write_tag_directive(self, handle_text, prefix_text):
        data = u'%%TAG %s %s' % (handle_text, prefix_text)
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)
        self.write_line_break()

    # Scalar streams.

    def write_single_quoted(self, text, split=True):
        self.write_indicator(u'\'', True)
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if spaces:
                if ch is None or ch != u' ':
                    if start+1 == end and self.column > self.best_width and split   \
                            and start != 0 and end != len(text):
                        self.write_indent()
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            elif breaks:
                if ch is None or ch not in u'\n\x85\u2028\u2029':
                    if text[start] == u'\n':
                        self.write_line_break()
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    self.write_indent()
                    start = end
            else:
                if ch is None or ch in u' \n\x85\u2028\u2029' or ch == u'\'':
                    if start < end:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                        start = end
            if ch == u'\'':
                data = u'\'\''
                self.column += 2
                if self.encoding:
                    data = data.encode(self.encoding)
                self.stream.write(data)
                start = end + 1
            if ch is not None:
                spaces = (ch == u' ')
                breaks = (ch in u'\n\x85\u2028\u2029')
            end += 1
        self.write_indicator(u'\'', False)

    ESCAPE_REPLACEMENTS = {
        u'\0':      u'0',
        u'\x07':    u'a',
        u'\x08':    u'b',
        u'\x09':    u't',
        u'\x0A':    u'n',
        u'\x0B':    u'v',
        u'\x0C':    u'f',
        u'\x0D':    u'r',
        u'\x1B':    u'e',
        u'\"':      u'\"',
        u'\\':      u'\\',
        u'\x85':    u'N',
        u'\xA0':    u'_',
        u'\u2028':  u'L',
        u'\u2029':  u'P',
    }

    def write_double_quoted(self, text, split=True):
        self.write_indicator(u'"', True)
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if ch is None or ch in u'"\\\x85\u2028\u2029\uFEFF' \
                    or not (u'\x20' <= ch <= u'\x7E'
                        or (self.allow_unicode
                            and (u'\xA0' <= ch <= u'\uD7FF'
                                or u'\uE000' <= ch <= u'\uFFFD'))):
                if start < end:
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end
                if ch is not None:
                    if ch in self.ESCAPE_REPLACEMENTS:
                        data = u'\\'+self.ESCAPE_REPLACEMENTS[ch]
                    elif ch <= u'\xFF':
                        data = u'\\x%02X' % ord(ch)
                    elif ch <= u'\uFFFF':
                        data = u'\\u%04X' % ord(ch)
                    else:
                        data = u'\\U%08X' % ord(ch)
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end+1
            if 0 < end < len(text)-1 and (ch == u' ' or start >= end)   \
                    and self.column+(end-start) > self.best_width and split:
                data = text[start:end]+u'\\'
                if start < end:
                    start = end
                self.column += len(data)
                if self.encoding:
                    data = data.encode(self.encoding)
                self.stream.write(data)
                self.write_indent()
                self.whitespace = False
                self.indention = False
                if text[start] == u' ':
                    data = u'\\'
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
            end += 1
        self.write_indicator(u'"', False)

    def determine_block_hints(self, text):
        hints = u''
        if text:
            if text[0] in u' \n\x85\u2028\u2029':
                hints += unicode(self.best_indent)
            if text[-1] not in u'\n\x85\u2028\u2029':
                hints += u'-'
            elif len(text) == 1 or text[-2] in u'\n\x85\u2028\u2029':
                hints += u'+'
        return hints

    def write_folded(self, text):
        hints = self.determine_block_hints(text)
        self.write_indicator(u'>'+hints, True)
        if hints[-1:] == u'+':
            self.open_ended = True
        self.write_line_break()
        leading_space = True
        spaces = False
        breaks = True
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if breaks:
                if ch is None or ch not in u'\n\x85\u2028\u2029':
                    if not leading_space and ch is not None and ch != u' '  \
                            and text[start] == u'\n':
                        self.write_line_break()
                    leading_space = (ch == u' ')
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    if ch is not None:
                        self.write_indent()
                    start = end
            elif spaces:
                if ch != u' ':
                    if start+1 == end and self.column > self.best_width:
                        self.write_indent()
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            else:
                if ch is None or ch in u' \n\x85\u2028\u2029':
                    data = text[start:end]
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    if ch is None:
                        self.write_line_break()
                    start = end
            if ch is not None:
                breaks = (ch in u'\n\x85\u2028\u2029')
                spaces = (ch == u' ')
            end += 1

    def write_literal(self, text):
        hints = self.determine_block_hints(text)
        self.write_indicator(u'|'+hints, True)
        if hints[-1:] == u'+':
            self.open_ended = True
        self.write_line_break()
        breaks = True
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if breaks:
                if ch is None or ch not in u'\n\x85\u2028\u2029':
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    if ch is not None:
                        self.write_indent()
                    start = end
            else:
                if ch is None or ch in u'\n\x85\u2028\u2029':
                    data = text[start:end]
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    if ch is None:
                        self.write_line_break()
                    start = end
            if ch is not None:
                breaks = (ch in u'\n\x85\u2028\u2029')
            end += 1

    def write_plain(self, text, split=True):
        if self.root_context:
            self.open_ended = True
        if not text:
            return
        if not self.whitespace:
            data = u' '
            self.column += len(data)
            if self.encoding:
                data = data.encode(self.encoding)
            self.stream.write(data)
        self.whitespace = False
        self.indention = False
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if spaces:
                if ch != u' ':
                    if start+1 == end and self.column > self.best_width and split:
                        self.write_indent()
                        self.whitespace = False
                        self.indention = False
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            elif breaks:
                if ch not in u'\n\x85\u2028\u2029':
                    if text[start] == u'\n':
                        self.write_line_break()
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    self.write_indent()
                    self.whitespace = False
                    self.indention = False
                    start = end
            else:
                if ch is None or ch in u' \n\x85\u2028\u2029':
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end
            if ch is not None:
                spaces = (ch == u' ')
                breaks = (ch in u'\n\x85\u2028\u2029')
            end += 1


########NEW FILE########
__FILENAME__ = error

__all__ = ['Mark', 'YAMLError', 'MarkedYAMLError']

class Mark(object):

    def __init__(self, name, index, line, column, buffer, pointer):
        self.name = name
        self.index = index
        self.line = line
        self.column = column
        self.buffer = buffer
        self.pointer = pointer

    def get_snippet(self, indent=4, max_length=75):
        if self.buffer is None:
            return None
        head = ''
        start = self.pointer
        while start > 0 and self.buffer[start-1] not in u'\0\r\n\x85\u2028\u2029':
            start -= 1
            if self.pointer-start > max_length/2-1:
                head = ' ... '
                start += 5
                break
        tail = ''
        end = self.pointer
        while end < len(self.buffer) and self.buffer[end] not in u'\0\r\n\x85\u2028\u2029':
            end += 1
            if end-self.pointer > max_length/2-1:
                tail = ' ... '
                end -= 5
                break
        snippet = self.buffer[start:end].encode('utf-8')
        return ' '*indent + head + snippet + tail + '\n'  \
                + ' '*(indent+self.pointer-start+len(head)) + '^'

    def __str__(self):
        snippet = self.get_snippet()
        where = "  in \"%s\", line %d, column %d"   \
                % (self.name, self.line+1, self.column+1)
        if snippet is not None:
            where += ":\n"+snippet
        return where

class YAMLError(Exception):
    pass

class MarkedYAMLError(YAMLError):

    def __init__(self, context=None, context_mark=None,
            problem=None, problem_mark=None, note=None):
        self.context = context
        self.context_mark = context_mark
        self.problem = problem
        self.problem_mark = problem_mark
        self.note = note

    def __str__(self):
        lines = []
        if self.context is not None:
            lines.append(self.context)
        if self.context_mark is not None  \
            and (self.problem is None or self.problem_mark is None
                    or self.context_mark.name != self.problem_mark.name
                    or self.context_mark.line != self.problem_mark.line
                    or self.context_mark.column != self.problem_mark.column):
            lines.append(str(self.context_mark))
        if self.problem is not None:
            lines.append(self.problem)
        if self.problem_mark is not None:
            lines.append(str(self.problem_mark))
        if self.note is not None:
            lines.append(self.note)
        return '\n'.join(lines)


########NEW FILE########
__FILENAME__ = events

# Abstract classes.

class Event(object):
    def __init__(self, start_mark=None, end_mark=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        attributes = [key for key in ['anchor', 'tag', 'implicit', 'value']
                if hasattr(self, key)]
        arguments = ', '.join(['%s=%r' % (key, getattr(self, key))
                for key in attributes])
        return '%s(%s)' % (self.__class__.__name__, arguments)

class NodeEvent(Event):
    def __init__(self, anchor, start_mark=None, end_mark=None):
        self.anchor = anchor
        self.start_mark = start_mark
        self.end_mark = end_mark

class CollectionStartEvent(NodeEvent):
    def __init__(self, anchor, tag, implicit, start_mark=None, end_mark=None,
            flow_style=None):
        self.anchor = anchor
        self.tag = tag
        self.implicit = implicit
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.flow_style = flow_style

class CollectionEndEvent(Event):
    pass

# Implementations.

class StreamStartEvent(Event):
    def __init__(self, start_mark=None, end_mark=None, encoding=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.encoding = encoding

class StreamEndEvent(Event):
    pass

class DocumentStartEvent(Event):
    def __init__(self, start_mark=None, end_mark=None,
            explicit=None, version=None, tags=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.explicit = explicit
        self.version = version
        self.tags = tags

class DocumentEndEvent(Event):
    def __init__(self, start_mark=None, end_mark=None,
            explicit=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.explicit = explicit

class AliasEvent(NodeEvent):
    pass

class ScalarEvent(NodeEvent):
    def __init__(self, anchor, tag, implicit, value,
            start_mark=None, end_mark=None, style=None):
        self.anchor = anchor
        self.tag = tag
        self.implicit = implicit
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style

class SequenceStartEvent(CollectionStartEvent):
    pass

class SequenceEndEvent(CollectionEndEvent):
    pass

class MappingStartEvent(CollectionStartEvent):
    pass

class MappingEndEvent(CollectionEndEvent):
    pass


########NEW FILE########
__FILENAME__ = loader

__all__ = ['BaseLoader', 'SafeLoader', 'Loader']

from reader import *
from scanner import *
from parser import *
from composer import *
from constructor import *
from resolver import *

class BaseLoader(Reader, Scanner, Parser, Composer, BaseConstructor, BaseResolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        BaseConstructor.__init__(self)
        BaseResolver.__init__(self)

class SafeLoader(Reader, Scanner, Parser, Composer, SafeConstructor, Resolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

class Loader(Reader, Scanner, Parser, Composer, Constructor, Resolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        Constructor.__init__(self)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = nodes

class Node(object):
    def __init__(self, tag, value, start_mark, end_mark):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        value = self.value
        #if isinstance(value, list):
        #    if len(value) == 0:
        #        value = '<empty>'
        #    elif len(value) == 1:
        #        value = '<1 item>'
        #    else:
        #        value = '<%d items>' % len(value)
        #else:
        #    if len(value) > 75:
        #        value = repr(value[:70]+u' ... ')
        #    else:
        #        value = repr(value)
        value = repr(value)
        return '%s(tag=%r, value=%s)' % (self.__class__.__name__, self.tag, value)

class ScalarNode(Node):
    id = 'scalar'
    def __init__(self, tag, value,
            start_mark=None, end_mark=None, style=None):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style

class CollectionNode(Node):
    def __init__(self, tag, value,
            start_mark=None, end_mark=None, flow_style=None):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.flow_style = flow_style

class SequenceNode(CollectionNode):
    id = 'sequence'

class MappingNode(CollectionNode):
    id = 'mapping'


########NEW FILE########
__FILENAME__ = parser

# The following YAML grammar is LL(1) and is parsed by a recursive descent
# parser.
#
# stream            ::= STREAM-START implicit_document? explicit_document* STREAM-END
# implicit_document ::= block_node DOCUMENT-END*
# explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*
# block_node_or_indentless_sequence ::=
#                       ALIAS
#                       | properties (block_content | indentless_block_sequence)?
#                       | block_content
#                       | indentless_block_sequence
# block_node        ::= ALIAS
#                       | properties block_content?
#                       | block_content
# flow_node         ::= ALIAS
#                       | properties flow_content?
#                       | flow_content
# properties        ::= TAG ANCHOR? | ANCHOR TAG?
# block_content     ::= block_collection | flow_collection | SCALAR
# flow_content      ::= flow_collection | SCALAR
# block_collection  ::= block_sequence | block_mapping
# flow_collection   ::= flow_sequence | flow_mapping
# block_sequence    ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END
# indentless_sequence   ::= (BLOCK-ENTRY block_node?)+
# block_mapping     ::= BLOCK-MAPPING_START
#                       ((KEY block_node_or_indentless_sequence?)?
#                       (VALUE block_node_or_indentless_sequence?)?)*
#                       BLOCK-END
# flow_sequence     ::= FLOW-SEQUENCE-START
#                       (flow_sequence_entry FLOW-ENTRY)*
#                       flow_sequence_entry?
#                       FLOW-SEQUENCE-END
# flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
# flow_mapping      ::= FLOW-MAPPING-START
#                       (flow_mapping_entry FLOW-ENTRY)*
#                       flow_mapping_entry?
#                       FLOW-MAPPING-END
# flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?
#
# FIRST sets:
#
# stream: { STREAM-START }
# explicit_document: { DIRECTIVE DOCUMENT-START }
# implicit_document: FIRST(block_node)
# block_node: { ALIAS TAG ANCHOR SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_node: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_content: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# flow_content: { FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# block_collection: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_sequence: { BLOCK-SEQUENCE-START }
# block_mapping: { BLOCK-MAPPING-START }
# block_node_or_indentless_sequence: { ALIAS ANCHOR TAG SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START BLOCK-ENTRY }
# indentless_sequence: { ENTRY }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_sequence: { FLOW-SEQUENCE-START }
# flow_mapping: { FLOW-MAPPING-START }
# flow_sequence_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }
# flow_mapping_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }

__all__ = ['Parser', 'ParserError']

from error import MarkedYAMLError
from tokens import *
from events import *
from scanner import *

class ParserError(MarkedYAMLError):
    pass

class Parser(object):
    # Since writing a recursive-descendant parser is a straightforward task, we
    # do not give many comments here.

    DEFAULT_TAGS = {
        u'!':   u'!',
        u'!!':  u'tag:yaml.org,2002:',
    }

    def __init__(self):
        self.current_event = None
        self.yaml_version = None
        self.tag_handles = {}
        self.states = []
        self.marks = []
        self.state = self.parse_stream_start

    def check_event(self, *choices):
        # Check the type of the next event.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        if self.current_event is not None:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.current_event, choice):
                    return True
        return False

    def peek_event(self):
        # Get the next event.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        return self.current_event

    def get_event(self):
        # Get the next event and proceed further.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        value = self.current_event
        self.current_event = None
        return value

    # stream    ::= STREAM-START implicit_document? explicit_document* STREAM-END
    # implicit_document ::= block_node DOCUMENT-END*
    # explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*

    def parse_stream_start(self):

        # Parse the stream start.
        token = self.get_token()
        event = StreamStartEvent(token.start_mark, token.end_mark,
                encoding=token.encoding)

        # Prepare the next state.
        self.state = self.parse_implicit_document_start

        return event

    def parse_implicit_document_start(self):

        # Parse an implicit document.
        if not self.check_token(DirectiveToken, DocumentStartToken,
                StreamEndToken):
            self.tag_handles = self.DEFAULT_TAGS
            token = self.peek_token()
            start_mark = end_mark = token.start_mark
            event = DocumentStartEvent(start_mark, end_mark,
                    explicit=False)

            # Prepare the next state.
            self.states.append(self.parse_document_end)
            self.state = self.parse_block_node

            return event

        else:
            return self.parse_document_start()

    def parse_document_start(self):

        # Parse any extra document end indicators.
        while self.check_token(DocumentEndToken):
            self.get_token()

        # Parse an explicit document.
        if not self.check_token(StreamEndToken):
            token = self.peek_token()
            start_mark = token.start_mark
            version, tags = self.process_directives()
            if not self.check_token(DocumentStartToken):
                raise ParserError(None, None,
                        "expected '<document start>', but found %r"
                        % self.peek_token().id,
                        self.peek_token().start_mark)
            token = self.get_token()
            end_mark = token.end_mark
            event = DocumentStartEvent(start_mark, end_mark,
                    explicit=True, version=version, tags=tags)
            self.states.append(self.parse_document_end)
            self.state = self.parse_document_content
        else:
            # Parse the end of the stream.
            token = self.get_token()
            event = StreamEndEvent(token.start_mark, token.end_mark)
            assert not self.states
            assert not self.marks
            self.state = None
        return event

    def parse_document_end(self):

        # Parse the document end.
        token = self.peek_token()
        start_mark = end_mark = token.start_mark
        explicit = False
        if self.check_token(DocumentEndToken):
            token = self.get_token()
            end_mark = token.end_mark
            explicit = True
        event = DocumentEndEvent(start_mark, end_mark,
                explicit=explicit)

        # Prepare the next state.
        self.state = self.parse_document_start

        return event

    def parse_document_content(self):
        if self.check_token(DirectiveToken,
                DocumentStartToken, DocumentEndToken, StreamEndToken):
            event = self.process_empty_scalar(self.peek_token().start_mark)
            self.state = self.states.pop()
            return event
        else:
            return self.parse_block_node()

    def process_directives(self):
        self.yaml_version = None
        self.tag_handles = {}
        while self.check_token(DirectiveToken):
            token = self.get_token()
            if token.name == u'YAML':
                if self.yaml_version is not None:
                    raise ParserError(None, None,
                            "found duplicate YAML directive", token.start_mark)
                major, minor = token.value
                if major != 1:
                    raise ParserError(None, None,
                            "found incompatible YAML document (version 1.* is required)",
                            token.start_mark)
                self.yaml_version = token.value
            elif token.name == u'TAG':
                handle, prefix = token.value
                if handle in self.tag_handles:
                    raise ParserError(None, None,
                            "duplicate tag handle %r" % handle.encode('utf-8'),
                            token.start_mark)
                self.tag_handles[handle] = prefix
        if self.tag_handles:
            value = self.yaml_version, self.tag_handles.copy()
        else:
            value = self.yaml_version, None
        for key in self.DEFAULT_TAGS:
            if key not in self.tag_handles:
                self.tag_handles[key] = self.DEFAULT_TAGS[key]
        return value

    # block_node_or_indentless_sequence ::= ALIAS
    #               | properties (block_content | indentless_block_sequence)?
    #               | block_content
    #               | indentless_block_sequence
    # block_node    ::= ALIAS
    #                   | properties block_content?
    #                   | block_content
    # flow_node     ::= ALIAS
    #                   | properties flow_content?
    #                   | flow_content
    # properties    ::= TAG ANCHOR? | ANCHOR TAG?
    # block_content     ::= block_collection | flow_collection | SCALAR
    # flow_content      ::= flow_collection | SCALAR
    # block_collection  ::= block_sequence | block_mapping
    # flow_collection   ::= flow_sequence | flow_mapping

    def parse_block_node(self):
        return self.parse_node(block=True)

    def parse_flow_node(self):
        return self.parse_node()

    def parse_block_node_or_indentless_sequence(self):
        return self.parse_node(block=True, indentless_sequence=True)

    def parse_node(self, block=False, indentless_sequence=False):
        if self.check_token(AliasToken):
            token = self.get_token()
            event = AliasEvent(token.value, token.start_mark, token.end_mark)
            self.state = self.states.pop()
        else:
            anchor = None
            tag = None
            start_mark = end_mark = tag_mark = None
            if self.check_token(AnchorToken):
                token = self.get_token()
                start_mark = token.start_mark
                end_mark = token.end_mark
                anchor = token.value
                if self.check_token(TagToken):
                    token = self.get_token()
                    tag_mark = token.start_mark
                    end_mark = token.end_mark
                    tag = token.value
            elif self.check_token(TagToken):
                token = self.get_token()
                start_mark = tag_mark = token.start_mark
                end_mark = token.end_mark
                tag = token.value
                if self.check_token(AnchorToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    anchor = token.value
            if tag is not None:
                handle, suffix = tag
                if handle is not None:
                    if handle not in self.tag_handles:
                        raise ParserError("while parsing a node", start_mark,
                                "found undefined tag handle %r" % handle.encode('utf-8'),
                                tag_mark)
                    tag = self.tag_handles[handle]+suffix
                else:
                    tag = suffix
            #if tag == u'!':
            #    raise ParserError("while parsing a node", start_mark,
            #            "found non-specific tag '!'", tag_mark,
            #            "Please check 'http://pyyaml.org/wiki/YAMLNonSpecificTag' and share your opinion.")
            if start_mark is None:
                start_mark = end_mark = self.peek_token().start_mark
            event = None
            implicit = (tag is None or tag == u'!')
            if indentless_sequence and self.check_token(BlockEntryToken):
                end_mark = self.peek_token().end_mark
                event = SequenceStartEvent(anchor, tag, implicit,
                        start_mark, end_mark)
                self.state = self.parse_indentless_sequence_entry
            else:
                if self.check_token(ScalarToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    if (token.plain and tag is None) or tag == u'!':
                        implicit = (True, False)
                    elif tag is None:
                        implicit = (False, True)
                    else:
                        implicit = (False, False)
                    event = ScalarEvent(anchor, tag, implicit, token.value,
                            start_mark, end_mark, style=token.style)
                    self.state = self.states.pop()
                elif self.check_token(FlowSequenceStartToken):
                    end_mark = self.peek_token().end_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    self.state = self.parse_flow_sequence_first_entry
                elif self.check_token(FlowMappingStartToken):
                    end_mark = self.peek_token().end_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    self.state = self.parse_flow_mapping_first_key
                elif block and self.check_token(BlockSequenceStartToken):
                    end_mark = self.peek_token().start_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    self.state = self.parse_block_sequence_first_entry
                elif block and self.check_token(BlockMappingStartToken):
                    end_mark = self.peek_token().start_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    self.state = self.parse_block_mapping_first_key
                elif anchor is not None or tag is not None:
                    # Empty scalars are allowed even if a tag or an anchor is
                    # specified.
                    event = ScalarEvent(anchor, tag, (implicit, False), u'',
                            start_mark, end_mark)
                    self.state = self.states.pop()
                else:
                    if block:
                        node = 'block'
                    else:
                        node = 'flow'
                    token = self.peek_token()
                    raise ParserError("while parsing a %s node" % node, start_mark,
                            "expected the node content, but found %r" % token.id,
                            token.start_mark)
        return event

    # block_sequence ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END

    def parse_block_sequence_first_entry(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_block_sequence_entry()

    def parse_block_sequence_entry(self):
        if self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken, BlockEndToken):
                self.states.append(self.parse_block_sequence_entry)
                return self.parse_block_node()
            else:
                self.state = self.parse_block_sequence_entry
                return self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while parsing a block collection", self.marks[-1],
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        event = SequenceEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    # indentless_sequence ::= (BLOCK-ENTRY block_node?)+

    def parse_indentless_sequence_entry(self):
        if self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken,
                    KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_indentless_sequence_entry)
                return self.parse_block_node()
            else:
                self.state = self.parse_indentless_sequence_entry
                return self.process_empty_scalar(token.end_mark)
        token = self.peek_token()
        event = SequenceEndEvent(token.start_mark, token.start_mark)
        self.state = self.states.pop()
        return event

    # block_mapping     ::= BLOCK-MAPPING_START
    #                       ((KEY block_node_or_indentless_sequence?)?
    #                       (VALUE block_node_or_indentless_sequence?)?)*
    #                       BLOCK-END

    def parse_block_mapping_first_key(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_block_mapping_key()

    def parse_block_mapping_key(self):
        if self.check_token(KeyToken):
            token = self.get_token()
            if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_block_mapping_value)
                return self.parse_block_node_or_indentless_sequence()
            else:
                self.state = self.parse_block_mapping_value
                return self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while parsing a block mapping", self.marks[-1],
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        event = MappingEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_block_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_block_mapping_key)
                return self.parse_block_node_or_indentless_sequence()
            else:
                self.state = self.parse_block_mapping_key
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_block_mapping_key
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    # flow_sequence     ::= FLOW-SEQUENCE-START
    #                       (flow_sequence_entry FLOW-ENTRY)*
    #                       flow_sequence_entry?
    #                       FLOW-SEQUENCE-END
    # flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
    #
    # Note that while production rules for both flow_sequence_entry and
    # flow_mapping_entry are equal, their interpretations are different.
    # For `flow_sequence_entry`, the part `KEY flow_node? (VALUE flow_node?)?`
    # generate an inline mapping (set syntax).

    def parse_flow_sequence_first_entry(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_flow_sequence_entry(first=True)

    def parse_flow_sequence_entry(self, first=False):
        if not self.check_token(FlowSequenceEndToken):
            if not first:
                if self.check_token(FlowEntryToken):
                    self.get_token()
                else:
                    token = self.peek_token()
                    raise ParserError("while parsing a flow sequence", self.marks[-1],
                            "expected ',' or ']', but got %r" % token.id, token.start_mark)
            
            if self.check_token(KeyToken):
                token = self.peek_token()
                event = MappingStartEvent(None, None, True,
                        token.start_mark, token.end_mark,
                        flow_style=True)
                self.state = self.parse_flow_sequence_entry_mapping_key
                return event
            elif not self.check_token(FlowSequenceEndToken):
                self.states.append(self.parse_flow_sequence_entry)
                return self.parse_flow_node()
        token = self.get_token()
        event = SequenceEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_flow_sequence_entry_mapping_key(self):
        token = self.get_token()
        if not self.check_token(ValueToken,
                FlowEntryToken, FlowSequenceEndToken):
            self.states.append(self.parse_flow_sequence_entry_mapping_value)
            return self.parse_flow_node()
        else:
            self.state = self.parse_flow_sequence_entry_mapping_value
            return self.process_empty_scalar(token.end_mark)

    def parse_flow_sequence_entry_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(FlowEntryToken, FlowSequenceEndToken):
                self.states.append(self.parse_flow_sequence_entry_mapping_end)
                return self.parse_flow_node()
            else:
                self.state = self.parse_flow_sequence_entry_mapping_end
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_flow_sequence_entry_mapping_end
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    def parse_flow_sequence_entry_mapping_end(self):
        self.state = self.parse_flow_sequence_entry
        token = self.peek_token()
        return MappingEndEvent(token.start_mark, token.start_mark)

    # flow_mapping  ::= FLOW-MAPPING-START
    #                   (flow_mapping_entry FLOW-ENTRY)*
    #                   flow_mapping_entry?
    #                   FLOW-MAPPING-END
    # flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?

    def parse_flow_mapping_first_key(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_flow_mapping_key(first=True)

    def parse_flow_mapping_key(self, first=False):
        if not self.check_token(FlowMappingEndToken):
            if not first:
                if self.check_token(FlowEntryToken):
                    self.get_token()
                else:
                    token = self.peek_token()
                    raise ParserError("while parsing a flow mapping", self.marks[-1],
                            "expected ',' or '}', but got %r" % token.id, token.start_mark)
            if self.check_token(KeyToken):
                token = self.get_token()
                if not self.check_token(ValueToken,
                        FlowEntryToken, FlowMappingEndToken):
                    self.states.append(self.parse_flow_mapping_value)
                    return self.parse_flow_node()
                else:
                    self.state = self.parse_flow_mapping_value
                    return self.process_empty_scalar(token.end_mark)
            elif not self.check_token(FlowMappingEndToken):
                self.states.append(self.parse_flow_mapping_empty_value)
                return self.parse_flow_node()
        token = self.get_token()
        event = MappingEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_flow_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(FlowEntryToken, FlowMappingEndToken):
                self.states.append(self.parse_flow_mapping_key)
                return self.parse_flow_node()
            else:
                self.state = self.parse_flow_mapping_key
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_flow_mapping_key
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    def parse_flow_mapping_empty_value(self):
        self.state = self.parse_flow_mapping_key
        return self.process_empty_scalar(self.peek_token().start_mark)

    def process_empty_scalar(self, mark):
        return ScalarEvent(None, None, (True, False), u'', mark, mark)


########NEW FILE########
__FILENAME__ = reader
# This module contains abstractions for the input stream. You don't have to
# looks further, there are no pretty code.
#
# We define two classes here.
#
#   Mark(source, line, column)
# It's just a record and its only use is producing nice error messages.
# Parser does not use it for any other purposes.
#
#   Reader(source, data)
# Reader determines the encoding of `data` and converts it to unicode.
# Reader provides the following methods and attributes:
#   reader.peek(length=1) - return the next `length` characters
#   reader.forward(length=1) - move the current position to `length` characters.
#   reader.index - the number of the current character.
#   reader.line, stream.column - the line and the column of the current character.

__all__ = ['Reader', 'ReaderError']

from error import YAMLError, Mark

import codecs, re

# Unfortunately, codec functions in Python 2.3 does not support the `finish`
# arguments, so we have to write our own wrappers.

try:
    codecs.utf_8_decode('', 'strict', False)
    from codecs import utf_8_decode, utf_16_le_decode, utf_16_be_decode

except TypeError:

    def utf_16_le_decode(data, errors, finish=False):
        if not finish and len(data) % 2 == 1:
            data = data[:-1]
        return codecs.utf_16_le_decode(data, errors)

    def utf_16_be_decode(data, errors, finish=False):
        if not finish and len(data) % 2 == 1:
            data = data[:-1]
        return codecs.utf_16_be_decode(data, errors)

    def utf_8_decode(data, errors, finish=False):
        if not finish:
            # We are trying to remove a possible incomplete multibyte character
            # from the suffix of the data.
            # The first byte of a multi-byte sequence is in the range 0xc0 to 0xfd.
            # All further bytes are in the range 0x80 to 0xbf.
            # UTF-8 encoded UCS characters may be up to six bytes long.
            count = 0
            while count < 5 and count < len(data)   \
                    and '\x80' <= data[-count-1] <= '\xBF':
                count -= 1
            if count < 5 and count < len(data)  \
                    and '\xC0' <= data[-count-1] <= '\xFD':
                data = data[:-count-1]
        return codecs.utf_8_decode(data, errors)

class ReaderError(YAMLError):

    def __init__(self, name, position, character, encoding, reason):
        self.name = name
        self.character = character
        self.position = position
        self.encoding = encoding
        self.reason = reason

    def __str__(self):
        if isinstance(self.character, str):
            return "'%s' codec can't decode byte #x%02x: %s\n"  \
                    "  in \"%s\", position %d"    \
                    % (self.encoding, ord(self.character), self.reason,
                            self.name, self.position)
        else:
            return "unacceptable character #x%04x: %s\n"    \
                    "  in \"%s\", position %d"    \
                    % (self.character, self.reason,
                            self.name, self.position)

class Reader(object):
    # Reader:
    # - determines the data encoding and converts it to unicode,
    # - checks if characters are in allowed range,
    # - adds '\0' to the end.

    # Reader accepts
    #  - a `str` object,
    #  - a `unicode` object,
    #  - a file-like object with its `read` method returning `str`,
    #  - a file-like object with its `read` method returning `unicode`.

    # Yeah, it's ugly and slow.

    def __init__(self, stream):
        self.name = None
        self.stream = None
        self.stream_pointer = 0
        self.eof = True
        self.buffer = u''
        self.pointer = 0
        self.raw_buffer = None
        self.raw_decode = None
        self.encoding = None
        self.index = 0
        self.line = 0
        self.column = 0
        if isinstance(stream, unicode):
            self.name = "<unicode string>"
            self.check_printable(stream)
            self.buffer = stream+u'\0'
        elif isinstance(stream, str):
            self.name = "<string>"
            self.raw_buffer = stream
            self.determine_encoding()
        else:
            self.stream = stream
            self.name = getattr(stream, 'name', "<file>")
            self.eof = False
            self.raw_buffer = ''
            self.determine_encoding()

    def peek(self, index=0):
        try:
            return self.buffer[self.pointer+index]
        except IndexError:
            self.update(index+1)
            return self.buffer[self.pointer+index]

    def prefix(self, length=1):
        if self.pointer+length >= len(self.buffer):
            self.update(length)
        return self.buffer[self.pointer:self.pointer+length]

    def forward(self, length=1):
        if self.pointer+length+1 >= len(self.buffer):
            self.update(length+1)
        while length:
            ch = self.buffer[self.pointer]
            self.pointer += 1
            self.index += 1
            if ch in u'\n\x85\u2028\u2029'  \
                    or (ch == u'\r' and self.buffer[self.pointer] != u'\n'):
                self.line += 1
                self.column = 0
            elif ch != u'\uFEFF':
                self.column += 1
            length -= 1

    def get_mark(self):
        if self.stream is None:
            return Mark(self.name, self.index, self.line, self.column,
                    self.buffer, self.pointer)
        else:
            return Mark(self.name, self.index, self.line, self.column,
                    None, None)

    def determine_encoding(self):
        while not self.eof and len(self.raw_buffer) < 2:
            self.update_raw()
        if not isinstance(self.raw_buffer, unicode):
            if self.raw_buffer.startswith(codecs.BOM_UTF16_LE):
                self.raw_decode = utf_16_le_decode
                self.encoding = 'utf-16-le'
            elif self.raw_buffer.startswith(codecs.BOM_UTF16_BE):
                self.raw_decode = utf_16_be_decode
                self.encoding = 'utf-16-be'
            else:
                self.raw_decode = utf_8_decode
                self.encoding = 'utf-8'
        self.update(1)

    NON_PRINTABLE = re.compile(u'[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD]')
    def check_printable(self, data):
        match = self.NON_PRINTABLE.search(data)
        if match:
            character = match.group()
            position = self.index+(len(self.buffer)-self.pointer)+match.start()
            raise ReaderError(self.name, position, ord(character),
                    'unicode', "special characters are not allowed")

    def update(self, length):
        if self.raw_buffer is None:
            return
        self.buffer = self.buffer[self.pointer:]
        self.pointer = 0
        while len(self.buffer) < length:
            if not self.eof:
                self.update_raw()
            if self.raw_decode is not None:
                try:
                    data, converted = self.raw_decode(self.raw_buffer,
                            'strict', self.eof)
                except UnicodeDecodeError, exc:
                    character = exc.object[exc.start]
                    if self.stream is not None:
                        position = self.stream_pointer-len(self.raw_buffer)+exc.start
                    else:
                        position = exc.start
                    raise ReaderError(self.name, position, character,
                            exc.encoding, exc.reason)
            else:
                data = self.raw_buffer
                converted = len(data)
            self.check_printable(data)
            self.buffer += data
            self.raw_buffer = self.raw_buffer[converted:]
            if self.eof:
                self.buffer += u'\0'
                self.raw_buffer = None
                break

    def update_raw(self, size=1024):
        data = self.stream.read(size)
        if data:
            self.raw_buffer += data
            self.stream_pointer += len(data)
        else:
            self.eof = True

#try:
#    import psyco
#    psyco.bind(Reader)
#except ImportError:
#    pass


########NEW FILE########
__FILENAME__ = representer

__all__ = ['BaseRepresenter', 'SafeRepresenter', 'Representer',
    'RepresenterError']

from error import *
from nodes import *

import datetime

try:
    set
except NameError:
    from sets import Set as set

import sys, copy_reg, types

class RepresenterError(YAMLError):
    pass

class BaseRepresenter(object):

    yaml_representers = {}
    yaml_multi_representers = {}

    def __init__(self, default_style=None, default_flow_style=None):
        self.default_style = default_style
        self.default_flow_style = default_flow_style
        self.represented_objects = {}
        self.object_keeper = []
        self.alias_key = None

    def represent(self, data):
        node = self.represent_data(data)
        self.serialize(node)
        self.represented_objects = {}
        self.object_keeper = []
        self.alias_key = None

    def get_classobj_bases(self, cls):
        bases = [cls]
        for base in cls.__bases__:
            bases.extend(self.get_classobj_bases(base))
        return bases

    def represent_data(self, data):
        if self.ignore_aliases(data):
            self.alias_key = None
        else:
            self.alias_key = id(data)
        if self.alias_key is not None:
            if self.alias_key in self.represented_objects:
                node = self.represented_objects[self.alias_key]
                #if node is None:
                #    raise RepresenterError("recursive objects are not allowed: %r" % data)
                return node
            #self.represented_objects[alias_key] = None
            self.object_keeper.append(data)
        data_types = type(data).__mro__
        if type(data) is types.InstanceType:
            data_types = self.get_classobj_bases(data.__class__)+list(data_types)
        if data_types[0] in self.yaml_representers:
            node = self.yaml_representers[data_types[0]](self, data)
        else:
            for data_type in data_types:
                if data_type in self.yaml_multi_representers:
                    node = self.yaml_multi_representers[data_type](self, data)
                    break
            else:
                if None in self.yaml_multi_representers:
                    node = self.yaml_multi_representers[None](self, data)
                elif None in self.yaml_representers:
                    node = self.yaml_representers[None](self, data)
                else:
                    node = ScalarNode(None, unicode(data))
        #if alias_key is not None:
        #    self.represented_objects[alias_key] = node
        return node

    def add_representer(cls, data_type, representer):
        if not 'yaml_representers' in cls.__dict__:
            cls.yaml_representers = cls.yaml_representers.copy()
        cls.yaml_representers[data_type] = representer
    add_representer = classmethod(add_representer)

    def add_multi_representer(cls, data_type, representer):
        if not 'yaml_multi_representers' in cls.__dict__:
            cls.yaml_multi_representers = cls.yaml_multi_representers.copy()
        cls.yaml_multi_representers[data_type] = representer
    add_multi_representer = classmethod(add_multi_representer)

    def represent_scalar(self, tag, value, style=None):
        if style is None:
            style = self.default_style
        node = ScalarNode(tag, value, style=style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        return node

    def represent_sequence(self, tag, sequence, flow_style=None):
        value = []
        node = SequenceNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        for item in sequence:
            node_item = self.represent_data(item)
            if not (isinstance(node_item, ScalarNode) and not node_item.style):
                best_style = False
            value.append(node_item)
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def represent_mapping(self, tag, mapping, flow_style=None):
        value = []
        node = MappingNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        if hasattr(mapping, 'items'):
            mapping = mapping.items()
            mapping.sort()
        for item_key, item_value in mapping:
            node_key = self.represent_data(item_key)
            node_value = self.represent_data(item_value)
            if not (isinstance(node_key, ScalarNode) and not node_key.style):
                best_style = False
            if not (isinstance(node_value, ScalarNode) and not node_value.style):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def ignore_aliases(self, data):
        return False

class SafeRepresenter(BaseRepresenter):

    def ignore_aliases(self, data):
        if data in [None, ()]:
            return True
        if isinstance(data, (str, unicode, bool, int, float)):
            return True

    def represent_none(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:null',
                u'null')

    def represent_str(self, data):
        tag = None
        style = None
        try:
            data = unicode(data, 'ascii')
            tag = u'tag:yaml.org,2002:str'
        except UnicodeDecodeError:
            try:
                data = unicode(data, 'utf-8')
                tag = u'tag:yaml.org,2002:str'
            except UnicodeDecodeError:
                data = data.encode('base64')
                tag = u'tag:yaml.org,2002:binary'
                style = '|'
        return self.represent_scalar(tag, data, style=style)

    def represent_unicode(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:str', data)

    def represent_bool(self, data):
        if data:
            value = u'true'
        else:
            value = u'false'
        return self.represent_scalar(u'tag:yaml.org,2002:bool', value)

    def represent_int(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:int', unicode(data))

    def represent_long(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:int', unicode(data))

    inf_value = 1e300
    while repr(inf_value) != repr(inf_value*inf_value):
        inf_value *= inf_value

    def represent_float(self, data):
        if data != data or (data == 0.0 and data == 1.0):
            value = u'.nan'
        elif data == self.inf_value:
            value = u'.inf'
        elif data == -self.inf_value:
            value = u'-.inf'
        else:
            value = unicode(repr(data)).lower()
            # Note that in some cases `repr(data)` represents a float number
            # without the decimal parts.  For instance:
            #   >>> repr(1e17)
            #   '1e17'
            # Unfortunately, this is not a valid float representation according
            # to the definition of the `!!float` tag.  We fix this by adding
            # '.0' before the 'e' symbol.
            if u'.' not in value and u'e' in value:
                value = value.replace(u'e', u'.0e', 1)
        return self.represent_scalar(u'tag:yaml.org,2002:float', value)

    def represent_list(self, data):
        #pairs = (len(data) > 0 and isinstance(data, list))
        #if pairs:
        #    for item in data:
        #        if not isinstance(item, tuple) or len(item) != 2:
        #            pairs = False
        #            break
        #if not pairs:
            return self.represent_sequence(u'tag:yaml.org,2002:seq', data)
        #value = []
        #for item_key, item_value in data:
        #    value.append(self.represent_mapping(u'tag:yaml.org,2002:map',
        #        [(item_key, item_value)]))
        #return SequenceNode(u'tag:yaml.org,2002:pairs', value)

    def represent_dict(self, data):
        return self.represent_mapping(u'tag:yaml.org,2002:map', data)

    def represent_set(self, data):
        value = {}
        for key in data:
            value[key] = None
        return self.represent_mapping(u'tag:yaml.org,2002:set', value)

    def represent_date(self, data):
        value = unicode(data.isoformat())
        return self.represent_scalar(u'tag:yaml.org,2002:timestamp', value)

    def represent_datetime(self, data):
        value = unicode(data.isoformat(' '))
        return self.represent_scalar(u'tag:yaml.org,2002:timestamp', value)

    def represent_yaml_object(self, tag, data, cls, flow_style=None):
        if hasattr(data, '__getstate__'):
            state = data.__getstate__()
        else:
            state = data.__dict__.copy()
        return self.represent_mapping(tag, state, flow_style=flow_style)

    def represent_undefined(self, data):
        raise RepresenterError("cannot represent an object: %s" % data)

SafeRepresenter.add_representer(type(None),
        SafeRepresenter.represent_none)

SafeRepresenter.add_representer(str,
        SafeRepresenter.represent_str)

SafeRepresenter.add_representer(unicode,
        SafeRepresenter.represent_unicode)

SafeRepresenter.add_representer(bool,
        SafeRepresenter.represent_bool)

SafeRepresenter.add_representer(int,
        SafeRepresenter.represent_int)

SafeRepresenter.add_representer(long,
        SafeRepresenter.represent_long)

SafeRepresenter.add_representer(float,
        SafeRepresenter.represent_float)

SafeRepresenter.add_representer(list,
        SafeRepresenter.represent_list)

SafeRepresenter.add_representer(tuple,
        SafeRepresenter.represent_list)

SafeRepresenter.add_representer(dict,
        SafeRepresenter.represent_dict)

SafeRepresenter.add_representer(set,
        SafeRepresenter.represent_set)

SafeRepresenter.add_representer(datetime.date,
        SafeRepresenter.represent_date)

SafeRepresenter.add_representer(datetime.datetime,
        SafeRepresenter.represent_datetime)

SafeRepresenter.add_representer(None,
        SafeRepresenter.represent_undefined)

class Representer(SafeRepresenter):

    def represent_str(self, data):
        tag = None
        style = None
        try:
            data = unicode(data, 'ascii')
            tag = u'tag:yaml.org,2002:str'
        except UnicodeDecodeError:
            try:
                data = unicode(data, 'utf-8')
                tag = u'tag:yaml.org,2002:python/str'
            except UnicodeDecodeError:
                data = data.encode('base64')
                tag = u'tag:yaml.org,2002:binary'
                style = '|'
        return self.represent_scalar(tag, data, style=style)

    def represent_unicode(self, data):
        tag = None
        try:
            data.encode('ascii')
            tag = u'tag:yaml.org,2002:python/unicode'
        except UnicodeEncodeError:
            tag = u'tag:yaml.org,2002:str'
        return self.represent_scalar(tag, data)

    def represent_long(self, data):
        tag = u'tag:yaml.org,2002:int'
        if int(data) is not data:
            tag = u'tag:yaml.org,2002:python/long'
        return self.represent_scalar(tag, unicode(data))

    def represent_complex(self, data):
        if data.imag == 0.0:
            data = u'%r' % data.real
        elif data.real == 0.0:
            data = u'%rj' % data.imag
        elif data.imag > 0:
            data = u'%r+%rj' % (data.real, data.imag)
        else:
            data = u'%r%rj' % (data.real, data.imag)
        return self.represent_scalar(u'tag:yaml.org,2002:python/complex', data)

    def represent_tuple(self, data):
        return self.represent_sequence(u'tag:yaml.org,2002:python/tuple', data)

    def represent_name(self, data):
        name = u'%s.%s' % (data.__module__, data.__name__)
        return self.represent_scalar(u'tag:yaml.org,2002:python/name:'+name, u'')

    def represent_module(self, data):
        return self.represent_scalar(
                u'tag:yaml.org,2002:python/module:'+data.__name__, u'')

    def represent_instance(self, data):
        # For instances of classic classes, we use __getinitargs__ and
        # __getstate__ to serialize the data.

        # If data.__getinitargs__ exists, the object must be reconstructed by
        # calling cls(**args), where args is a tuple returned by
        # __getinitargs__. Otherwise, the cls.__init__ method should never be
        # called and the class instance is created by instantiating a trivial
        # class and assigning to the instance's __class__ variable.

        # If data.__getstate__ exists, it returns the state of the object.
        # Otherwise, the state of the object is data.__dict__.

        # We produce either a !!python/object or !!python/object/new node.
        # If data.__getinitargs__ does not exist and state is a dictionary, we
        # produce a !!python/object node . Otherwise we produce a
        # !!python/object/new node.

        cls = data.__class__
        class_name = u'%s.%s' % (cls.__module__, cls.__name__)
        args = None
        state = None
        if hasattr(data, '__getinitargs__'):
            args = list(data.__getinitargs__())
        if hasattr(data, '__getstate__'):
            state = data.__getstate__()
        else:
            state = data.__dict__
        if args is None and isinstance(state, dict):
            return self.represent_mapping(
                    u'tag:yaml.org,2002:python/object:'+class_name, state)
        if isinstance(state, dict) and not state:
            return self.represent_sequence(
                    u'tag:yaml.org,2002:python/object/new:'+class_name, args)
        value = {}
        if args:
            value['args'] = args
        value['state'] = state
        return self.represent_mapping(
                u'tag:yaml.org,2002:python/object/new:'+class_name, value)

    def represent_object(self, data):
        # We use __reduce__ API to save the data. data.__reduce__ returns
        # a tuple of length 2-5:
        #   (function, args, state, listitems, dictitems)

        # For reconstructing, we calls function(*args), then set its state,
        # listitems, and dictitems if they are not None.

        # A special case is when function.__name__ == '__newobj__'. In this
        # case we create the object with args[0].__new__(*args).

        # Another special case is when __reduce__ returns a string - we don't
        # support it.

        # We produce a !!python/object, !!python/object/new or
        # !!python/object/apply node.

        cls = type(data)
        if cls in copy_reg.dispatch_table:
            reduce = copy_reg.dispatch_table[cls](data)
        elif hasattr(data, '__reduce_ex__'):
            reduce = data.__reduce_ex__(2)
        elif hasattr(data, '__reduce__'):
            reduce = data.__reduce__()
        else:
            raise RepresenterError("cannot represent object: %r" % data)
        reduce = (list(reduce)+[None]*5)[:5]
        function, args, state, listitems, dictitems = reduce
        args = list(args)
        if state is None:
            state = {}
        if listitems is not None:
            listitems = list(listitems)
        if dictitems is not None:
            dictitems = dict(dictitems)
        if function.__name__ == '__newobj__':
            function = args[0]
            args = args[1:]
            tag = u'tag:yaml.org,2002:python/object/new:'
            newobj = True
        else:
            tag = u'tag:yaml.org,2002:python/object/apply:'
            newobj = False
        function_name = u'%s.%s' % (function.__module__, function.__name__)
        if not args and not listitems and not dictitems \
                and isinstance(state, dict) and newobj:
            return self.represent_mapping(
                    u'tag:yaml.org,2002:python/object:'+function_name, state)
        if not listitems and not dictitems  \
                and isinstance(state, dict) and not state:
            return self.represent_sequence(tag+function_name, args)
        value = {}
        if args:
            value['args'] = args
        if state or not isinstance(state, dict):
            value['state'] = state
        if listitems:
            value['listitems'] = listitems
        if dictitems:
            value['dictitems'] = dictitems
        return self.represent_mapping(tag+function_name, value)

Representer.add_representer(str,
        Representer.represent_str)

Representer.add_representer(unicode,
        Representer.represent_unicode)

Representer.add_representer(long,
        Representer.represent_long)

Representer.add_representer(complex,
        Representer.represent_complex)

Representer.add_representer(tuple,
        Representer.represent_tuple)

Representer.add_representer(type,
        Representer.represent_name)

Representer.add_representer(types.ClassType,
        Representer.represent_name)

Representer.add_representer(types.FunctionType,
        Representer.represent_name)

Representer.add_representer(types.BuiltinFunctionType,
        Representer.represent_name)

Representer.add_representer(types.ModuleType,
        Representer.represent_module)

Representer.add_multi_representer(types.InstanceType,
        Representer.represent_instance)

Representer.add_multi_representer(object,
        Representer.represent_object)


########NEW FILE########
__FILENAME__ = resolver

__all__ = ['BaseResolver', 'Resolver']

from error import *
from nodes import *

import re

class ResolverError(YAMLError):
    pass

class BaseResolver(object):

    DEFAULT_SCALAR_TAG = u'tag:yaml.org,2002:str'
    DEFAULT_SEQUENCE_TAG = u'tag:yaml.org,2002:seq'
    DEFAULT_MAPPING_TAG = u'tag:yaml.org,2002:map'

    yaml_implicit_resolvers = {}
    yaml_path_resolvers = {}

    def __init__(self):
        self.resolver_exact_paths = []
        self.resolver_prefix_paths = []

    def add_implicit_resolver(cls, tag, regexp, first):
        if not 'yaml_implicit_resolvers' in cls.__dict__:
            cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()
        if first is None:
            first = [None]
        for ch in first:
            cls.yaml_implicit_resolvers.setdefault(ch, []).append((tag, regexp))
    add_implicit_resolver = classmethod(add_implicit_resolver)

    def add_path_resolver(cls, tag, path, kind=None):
        # Note: `add_path_resolver` is experimental.  The API could be changed.
        # `new_path` is a pattern that is matched against the path from the
        # root to the node that is being considered.  `node_path` elements are
        # tuples `(node_check, index_check)`.  `node_check` is a node class:
        # `ScalarNode`, `SequenceNode`, `MappingNode` or `None`.  `None`
        # matches any kind of a node.  `index_check` could be `None`, a boolean
        # value, a string value, or a number.  `None` and `False` match against
        # any _value_ of sequence and mapping nodes.  `True` matches against
        # any _key_ of a mapping node.  A string `index_check` matches against
        # a mapping value that corresponds to a scalar key which content is
        # equal to the `index_check` value.  An integer `index_check` matches
        # against a sequence value with the index equal to `index_check`.
        if not 'yaml_path_resolvers' in cls.__dict__:
            cls.yaml_path_resolvers = cls.yaml_path_resolvers.copy()
        new_path = []
        for element in path:
            if isinstance(element, (list, tuple)):
                if len(element) == 2:
                    node_check, index_check = element
                elif len(element) == 1:
                    node_check = element[0]
                    index_check = True
                else:
                    raise ResolverError("Invalid path element: %s" % element)
            else:
                node_check = None
                index_check = element
            if node_check is str:
                node_check = ScalarNode
            elif node_check is list:
                node_check = SequenceNode
            elif node_check is dict:
                node_check = MappingNode
            elif node_check not in [ScalarNode, SequenceNode, MappingNode]  \
                    and not isinstance(node_check, basestring)  \
                    and node_check is not None:
                raise ResolverError("Invalid node checker: %s" % node_check)
            if not isinstance(index_check, (basestring, int))   \
                    and index_check is not None:
                raise ResolverError("Invalid index checker: %s" % index_check)
            new_path.append((node_check, index_check))
        if kind is str:
            kind = ScalarNode
        elif kind is list:
            kind = SequenceNode
        elif kind is dict:
            kind = MappingNode
        elif kind not in [ScalarNode, SequenceNode, MappingNode]    \
                and kind is not None:
            raise ResolverError("Invalid node kind: %s" % kind)
        cls.yaml_path_resolvers[tuple(new_path), kind] = tag
    add_path_resolver = classmethod(add_path_resolver)

    def descend_resolver(self, current_node, current_index):
        if not self.yaml_path_resolvers:
            return
        exact_paths = {}
        prefix_paths = []
        if current_node:
            depth = len(self.resolver_prefix_paths)
            for path, kind in self.resolver_prefix_paths[-1]:
                if self.check_resolver_prefix(depth, path, kind,
                        current_node, current_index):
                    if len(path) > depth:
                        prefix_paths.append((path, kind))
                    else:
                        exact_paths[kind] = self.yaml_path_resolvers[path, kind]
        else:
            for path, kind in self.yaml_path_resolvers:
                if not path:
                    exact_paths[kind] = self.yaml_path_resolvers[path, kind]
                else:
                    prefix_paths.append((path, kind))
        self.resolver_exact_paths.append(exact_paths)
        self.resolver_prefix_paths.append(prefix_paths)

    def ascend_resolver(self):
        if not self.yaml_path_resolvers:
            return
        self.resolver_exact_paths.pop()
        self.resolver_prefix_paths.pop()

    def check_resolver_prefix(self, depth, path, kind,
            current_node, current_index):
        node_check, index_check = path[depth-1]
        if isinstance(node_check, basestring):
            if current_node.tag != node_check:
                return
        elif node_check is not None:
            if not isinstance(current_node, node_check):
                return
        if index_check is True and current_index is not None:
            return
        if (index_check is False or index_check is None)    \
                and current_index is None:
            return
        if isinstance(index_check, basestring):
            if not (isinstance(current_index, ScalarNode)
                    and index_check == current_index.value):
                return
        elif isinstance(index_check, int) and not isinstance(index_check, bool):
            if index_check != current_index:
                return
        return True

    def resolve(self, kind, value, implicit):
        if kind is ScalarNode and implicit[0]:
            if value == u'':
                resolvers = self.yaml_implicit_resolvers.get(u'', [])
            else:
                resolvers = self.yaml_implicit_resolvers.get(value[0], [])
            resolvers += self.yaml_implicit_resolvers.get(None, [])
            for tag, regexp in resolvers:
                if regexp.match(value):
                    return tag
            implicit = implicit[1]
        if self.yaml_path_resolvers:
            exact_paths = self.resolver_exact_paths[-1]
            if kind in exact_paths:
                return exact_paths[kind]
            if None in exact_paths:
                return exact_paths[None]
        if kind is ScalarNode:
            return self.DEFAULT_SCALAR_TAG
        elif kind is SequenceNode:
            return self.DEFAULT_SEQUENCE_TAG
        elif kind is MappingNode:
            return self.DEFAULT_MAPPING_TAG

class Resolver(BaseResolver):
    pass

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:bool',
        re.compile(ur'''^(?:yes|Yes|YES|no|No|NO
                    |true|True|TRUE|false|False|FALSE
                    |on|On|ON|off|Off|OFF)$''', re.X),
        list(u'yYnNtTfFoO'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:float',
        re.compile(ur'''^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
                    |\.[0-9_]+(?:[eE][-+][0-9]+)?
                    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
                    |[-+]?\.(?:inf|Inf|INF)
                    |\.(?:nan|NaN|NAN))$''', re.X),
        list(u'-+0123456789.'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:int',
        re.compile(ur'''^(?:[-+]?0b[0-1_]+
                    |[-+]?0[0-7_]+
                    |[-+]?(?:0|[1-9][0-9_]*)
                    |[-+]?0x[0-9a-fA-F_]+
                    |[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$''', re.X),
        list(u'-+0123456789'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:merge',
        re.compile(ur'^(?:<<)$'),
        [u'<'])

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:null',
        re.compile(ur'''^(?: ~
                    |null|Null|NULL
                    | )$''', re.X),
        [u'~', u'n', u'N', u''])

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:timestamp',
        re.compile(ur'''^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]
                    |[0-9][0-9][0-9][0-9] -[0-9][0-9]? -[0-9][0-9]?
                     (?:[Tt]|[ \t]+)[0-9][0-9]?
                     :[0-9][0-9] :[0-9][0-9] (?:\.[0-9]*)?
                     (?:[ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$''', re.X),
        list(u'0123456789'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:value',
        re.compile(ur'^(?:=)$'),
        [u'='])

# The following resolver is only for documentation purposes. It cannot work
# because plain scalars cannot start with '!', '&', or '*'.
Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:yaml',
        re.compile(ur'^(?:!|&|\*)$'),
        list(u'!&*'))


########NEW FILE########
__FILENAME__ = scanner

# Scanner produces tokens of the following types:
# STREAM-START
# STREAM-END
# DIRECTIVE(name, value)
# DOCUMENT-START
# DOCUMENT-END
# BLOCK-SEQUENCE-START
# BLOCK-MAPPING-START
# BLOCK-END
# FLOW-SEQUENCE-START
# FLOW-MAPPING-START
# FLOW-SEQUENCE-END
# FLOW-MAPPING-END
# BLOCK-ENTRY
# FLOW-ENTRY
# KEY
# VALUE
# ALIAS(value)
# ANCHOR(value)
# TAG(value)
# SCALAR(value, plain, style)
#
# Read comments in the Scanner code for more details.
#

__all__ = ['Scanner', 'ScannerError']

from error import MarkedYAMLError
from tokens import *

class ScannerError(MarkedYAMLError):
    pass

class SimpleKey(object):
    # See below simple keys treatment.

    def __init__(self, token_number, required, index, line, column, mark):
        self.token_number = token_number
        self.required = required
        self.index = index
        self.line = line
        self.column = column
        self.mark = mark

class Scanner(object):

    def __init__(self):
        """Initialize the scanner."""
        # It is assumed that Scanner and Reader will have a common descendant.
        # Reader do the dirty work of checking for BOM and converting the
        # input data to Unicode. It also adds NUL to the end.
        #
        # Reader supports the following methods
        #   self.peek(i=0)       # peek the next i-th character
        #   self.prefix(l=1)     # peek the next l characters
        #   self.forward(l=1)    # read the next l characters and move the pointer.

        # Had we reached the end of the stream?
        self.done = False

        # The number of unclosed '{' and '['. `flow_level == 0` means block
        # context.
        self.flow_level = 0

        # List of processed tokens that are not yet emitted.
        self.tokens = []

        # Add the STREAM-START token.
        self.fetch_stream_start()

        # Number of tokens that were emitted through the `get_token` method.
        self.tokens_taken = 0

        # The current indentation level.
        self.indent = -1

        # Past indentation levels.
        self.indents = []

        # Variables related to simple keys treatment.

        # A simple key is a key that is not denoted by the '?' indicator.
        # Example of simple keys:
        #   ---
        #   block simple key: value
        #   ? not a simple key:
        #   : { flow simple key: value }
        # We emit the KEY token before all keys, so when we find a potential
        # simple key, we try to locate the corresponding ':' indicator.
        # Simple keys should be limited to a single line and 1024 characters.

        # Can a simple key start at the current position? A simple key may
        # start:
        # - at the beginning of the line, not counting indentation spaces
        #       (in block context),
        # - after '{', '[', ',' (in the flow context),
        # - after '?', ':', '-' (in the block context).
        # In the block context, this flag also signifies if a block collection
        # may start at the current position.
        self.allow_simple_key = True

        # Keep track of possible simple keys. This is a dictionary. The key
        # is `flow_level`; there can be no more that one possible simple key
        # for each level. The value is a SimpleKey record:
        #   (token_number, required, index, line, column, mark)
        # A simple key may start with ALIAS, ANCHOR, TAG, SCALAR(flow),
        # '[', or '{' tokens.
        self.possible_simple_keys = {}

    # Public methods.

    def check_token(self, *choices):
        # Check if the next token is one of the given types.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.tokens[0], choice):
                    return True
        return False

    def peek_token(self):
        # Return the next token, but do not delete if from the queue.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            return self.tokens[0]

    def get_token(self):
        # Return the next token.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            self.tokens_taken += 1
            return self.tokens.pop(0)

    # Private methods.

    def need_more_tokens(self):
        if self.done:
            return False
        if not self.tokens:
            return True
        # The current token may be a potential simple key, so we
        # need to look further.
        self.stale_possible_simple_keys()
        if self.next_possible_simple_key() == self.tokens_taken:
            return True

    def fetch_more_tokens(self):

        # Eat whitespaces and comments until we reach the next token.
        self.scan_to_next_token()

        # Remove obsolete possible simple keys.
        self.stale_possible_simple_keys()

        # Compare the current indentation and column. It may add some tokens
        # and decrease the current indentation level.
        self.unwind_indent(self.column)

        # Peek the next character.
        ch = self.peek()

        # Is it the end of stream?
        if ch == u'\0':
            return self.fetch_stream_end()

        # Is it a directive?
        if ch == u'%' and self.check_directive():
            return self.fetch_directive()

        # Is it the document start?
        if ch == u'-' and self.check_document_start():
            return self.fetch_document_start()

        # Is it the document end?
        if ch == u'.' and self.check_document_end():
            return self.fetch_document_end()

        # TODO: support for BOM within a stream.
        #if ch == u'\uFEFF':
        #    return self.fetch_bom()    <-- issue BOMToken

        # Note: the order of the following checks is NOT significant.

        # Is it the flow sequence start indicator?
        if ch == u'[':
            return self.fetch_flow_sequence_start()

        # Is it the flow mapping start indicator?
        if ch == u'{':
            return self.fetch_flow_mapping_start()

        # Is it the flow sequence end indicator?
        if ch == u']':
            return self.fetch_flow_sequence_end()

        # Is it the flow mapping end indicator?
        if ch == u'}':
            return self.fetch_flow_mapping_end()

        # Is it the flow entry indicator?
        if ch == u',':
            return self.fetch_flow_entry()

        # Is it the block entry indicator?
        if ch == u'-' and self.check_block_entry():
            return self.fetch_block_entry()

        # Is it the key indicator?
        if ch == u'?' and self.check_key():
            return self.fetch_key()

        # Is it the value indicator?
        if ch == u':' and self.check_value():
            return self.fetch_value()

        # Is it an alias?
        if ch == u'*':
            return self.fetch_alias()

        # Is it an anchor?
        if ch == u'&':
            return self.fetch_anchor()

        # Is it a tag?
        if ch == u'!':
            return self.fetch_tag()

        # Is it a literal scalar?
        if ch == u'|' and not self.flow_level:
            return self.fetch_literal()

        # Is it a folded scalar?
        if ch == u'>' and not self.flow_level:
            return self.fetch_folded()

        # Is it a single quoted scalar?
        if ch == u'\'':
            return self.fetch_single()

        # Is it a double quoted scalar?
        if ch == u'\"':
            return self.fetch_double()

        # It must be a plain scalar then.
        if self.check_plain():
            return self.fetch_plain()

        # No? It's an error. Let's produce a nice error message.
        raise ScannerError("while scanning for the next token", None,
                "found character %r that cannot start any token"
                % ch.encode('utf-8'), self.get_mark())

    # Simple keys treatment.

    def next_possible_simple_key(self):
        # Return the number of the nearest possible simple key. Actually we
        # don't need to loop through the whole dictionary. We may replace it
        # with the following code:
        #   if not self.possible_simple_keys:
        #       return None
        #   return self.possible_simple_keys[
        #           min(self.possible_simple_keys.keys())].token_number
        min_token_number = None
        for level in self.possible_simple_keys:
            key = self.possible_simple_keys[level]
            if min_token_number is None or key.token_number < min_token_number:
                min_token_number = key.token_number
        return min_token_number

    def stale_possible_simple_keys(self):
        # Remove entries that are no longer possible simple keys. According to
        # the YAML specification, simple keys
        # - should be limited to a single line,
        # - should be no longer than 1024 characters.
        # Disabling this procedure will allow simple keys of any length and
        # height (may cause problems if indentation is broken though).
        for level in self.possible_simple_keys.keys():
            key = self.possible_simple_keys[level]
            if key.line != self.line  \
                    or self.index-key.index > 1024:
                if key.required:
                    raise ScannerError("while scanning a simple key", key.mark,
                            "could not found expected ':'", self.get_mark())
                del self.possible_simple_keys[level]

    def save_possible_simple_key(self):
        # The next token may start a simple key. We check if it's possible
        # and save its position. This function is called for
        #   ALIAS, ANCHOR, TAG, SCALAR(flow), '[', and '{'.

        # Check if a simple key is required at the current position.
        required = not self.flow_level and self.indent == self.column

        # A simple key is required only if it is the first token in the current
        # line. Therefore it is always allowed.
        assert self.allow_simple_key or not required

        # The next token might be a simple key. Let's save it's number and
        # position.
        if self.allow_simple_key:
            self.remove_possible_simple_key()
            token_number = self.tokens_taken+len(self.tokens)
            key = SimpleKey(token_number, required,
                    self.index, self.line, self.column, self.get_mark())
            self.possible_simple_keys[self.flow_level] = key

    def remove_possible_simple_key(self):
        # Remove the saved possible key position at the current flow level.
        if self.flow_level in self.possible_simple_keys:
            key = self.possible_simple_keys[self.flow_level]
            
            if key.required:
                raise ScannerError("while scanning a simple key", key.mark,
                        "could not found expected ':'", self.get_mark())

            del self.possible_simple_keys[self.flow_level]

    # Indentation functions.

    def unwind_indent(self, column):

        ## In flow context, tokens should respect indentation.
        ## Actually the condition should be `self.indent >= column` according to
        ## the spec. But this condition will prohibit intuitively correct
        ## constructions such as
        ## key : {
        ## }
        #if self.flow_level and self.indent > column:
        #    raise ScannerError(None, None,
        #            "invalid intendation or unclosed '[' or '{'",
        #            self.get_mark())

        # In the flow context, indentation is ignored. We make the scanner less
        # restrictive then specification requires.
        if self.flow_level:
            return

        # In block context, we may need to issue the BLOCK-END tokens.
        while self.indent > column:
            mark = self.get_mark()
            self.indent = self.indents.pop()
            self.tokens.append(BlockEndToken(mark, mark))

    def add_indent(self, column):
        # Check if we need to increase indentation.
        if self.indent < column:
            self.indents.append(self.indent)
            self.indent = column
            return True
        return False

    # Fetchers.

    def fetch_stream_start(self):
        # We always add STREAM-START as the first token and STREAM-END as the
        # last token.

        # Read the token.
        mark = self.get_mark()
        
        # Add STREAM-START.
        self.tokens.append(StreamStartToken(mark, mark,
            encoding=self.encoding))
        

    def fetch_stream_end(self):

        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset everything (not really needed).
        self.allow_simple_key = False
        self.possible_simple_keys = {}

        # Read the token.
        mark = self.get_mark()
        
        # Add STREAM-END.
        self.tokens.append(StreamEndToken(mark, mark))

        # The steam is finished.
        self.done = True

    def fetch_directive(self):
        
        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset simple keys.
        self.remove_possible_simple_key()
        self.allow_simple_key = False

        # Scan and add DIRECTIVE.
        self.tokens.append(self.scan_directive())

    def fetch_document_start(self):
        self.fetch_document_indicator(DocumentStartToken)

    def fetch_document_end(self):
        self.fetch_document_indicator(DocumentEndToken)

    def fetch_document_indicator(self, TokenClass):

        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset simple keys. Note that there could not be a block collection
        # after '---'.
        self.remove_possible_simple_key()
        self.allow_simple_key = False

        # Add DOCUMENT-START or DOCUMENT-END.
        start_mark = self.get_mark()
        self.forward(3)
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_sequence_start(self):
        self.fetch_flow_collection_start(FlowSequenceStartToken)

    def fetch_flow_mapping_start(self):
        self.fetch_flow_collection_start(FlowMappingStartToken)

    def fetch_flow_collection_start(self, TokenClass):

        # '[' and '{' may start a simple key.
        self.save_possible_simple_key()

        # Increase the flow level.
        self.flow_level += 1

        # Simple keys are allowed after '[' and '{'.
        self.allow_simple_key = True

        # Add FLOW-SEQUENCE-START or FLOW-MAPPING-START.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_sequence_end(self):
        self.fetch_flow_collection_end(FlowSequenceEndToken)

    def fetch_flow_mapping_end(self):
        self.fetch_flow_collection_end(FlowMappingEndToken)

    def fetch_flow_collection_end(self, TokenClass):

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Decrease the flow level.
        self.flow_level -= 1

        # No simple keys after ']' or '}'.
        self.allow_simple_key = False

        # Add FLOW-SEQUENCE-END or FLOW-MAPPING-END.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_entry(self):

        # Simple keys are allowed after ','.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add FLOW-ENTRY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(FlowEntryToken(start_mark, end_mark))

    def fetch_block_entry(self):

        # Block context needs additional checks.
        if not self.flow_level:

            # Are we allowed to start a new entry?
            if not self.allow_simple_key:
                raise ScannerError(None, None,
                        "sequence entries are not allowed here",
                        self.get_mark())

            # We may need to add BLOCK-SEQUENCE-START.
            if self.add_indent(self.column):
                mark = self.get_mark()
                self.tokens.append(BlockSequenceStartToken(mark, mark))

        # It's an error for the block entry to occur in the flow context,
        # but we let the parser detect this.
        else:
            pass

        # Simple keys are allowed after '-'.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add BLOCK-ENTRY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(BlockEntryToken(start_mark, end_mark))

    def fetch_key(self):
        
        # Block context needs additional checks.
        if not self.flow_level:

            # Are we allowed to start a key (not nessesary a simple)?
            if not self.allow_simple_key:
                raise ScannerError(None, None,
                        "mapping keys are not allowed here",
                        self.get_mark())

            # We may need to add BLOCK-MAPPING-START.
            if self.add_indent(self.column):
                mark = self.get_mark()
                self.tokens.append(BlockMappingStartToken(mark, mark))

        # Simple keys are allowed after '?' in the block context.
        self.allow_simple_key = not self.flow_level

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add KEY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(KeyToken(start_mark, end_mark))

    def fetch_value(self):

        # Do we determine a simple key?
        if self.flow_level in self.possible_simple_keys:

            # Add KEY.
            key = self.possible_simple_keys[self.flow_level]
            del self.possible_simple_keys[self.flow_level]
            self.tokens.insert(key.token_number-self.tokens_taken,
                    KeyToken(key.mark, key.mark))

            # If this key starts a new block mapping, we need to add
            # BLOCK-MAPPING-START.
            if not self.flow_level:
                if self.add_indent(key.column):
                    self.tokens.insert(key.token_number-self.tokens_taken,
                            BlockMappingStartToken(key.mark, key.mark))

            # There cannot be two simple keys one after another.
            self.allow_simple_key = False

        # It must be a part of a complex key.
        else:
            
            # Block context needs additional checks.
            # (Do we really need them? They will be catched by the parser
            # anyway.)
            if not self.flow_level:

                # We are allowed to start a complex value if and only if
                # we can start a simple key.
                if not self.allow_simple_key:
                    raise ScannerError(None, None,
                            "mapping values are not allowed here",
                            self.get_mark())

            # If this value starts a new block mapping, we need to add
            # BLOCK-MAPPING-START.  It will be detected as an error later by
            # the parser.
            if not self.flow_level:
                if self.add_indent(self.column):
                    mark = self.get_mark()
                    self.tokens.append(BlockMappingStartToken(mark, mark))

            # Simple keys are allowed after ':' in the block context.
            self.allow_simple_key = not self.flow_level

            # Reset possible simple key on the current level.
            self.remove_possible_simple_key()

        # Add VALUE.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(ValueToken(start_mark, end_mark))

    def fetch_alias(self):

        # ALIAS could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after ALIAS.
        self.allow_simple_key = False

        # Scan and add ALIAS.
        self.tokens.append(self.scan_anchor(AliasToken))

    def fetch_anchor(self):

        # ANCHOR could start a simple key.
        self.save_possible_simple_key()

        # No simple keys after ANCHOR.
        self.allow_simple_key = False

        # Scan and add ANCHOR.
        self.tokens.append(self.scan_anchor(AnchorToken))

    def fetch_tag(self):

        # TAG could start a simple key.
        self.save_possible_simple_key()

        # No simple keys after TAG.
        self.allow_simple_key = False

        # Scan and add TAG.
        self.tokens.append(self.scan_tag())

    def fetch_literal(self):
        self.fetch_block_scalar(style='|')

    def fetch_folded(self):
        self.fetch_block_scalar(style='>')

    def fetch_block_scalar(self, style):

        # A simple key may follow a block scalar.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Scan and add SCALAR.
        self.tokens.append(self.scan_block_scalar(style))

    def fetch_single(self):
        self.fetch_flow_scalar(style='\'')

    def fetch_double(self):
        self.fetch_flow_scalar(style='"')

    def fetch_flow_scalar(self, style):

        # A flow scalar could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after flow scalars.
        self.allow_simple_key = False

        # Scan and add SCALAR.
        self.tokens.append(self.scan_flow_scalar(style))

    def fetch_plain(self):

        # A plain scalar could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after plain scalars. But note that `scan_plain` will
        # change this flag if the scan is finished at the beginning of the
        # line.
        self.allow_simple_key = False

        # Scan and add SCALAR. May change `allow_simple_key`.
        self.tokens.append(self.scan_plain())

    # Checkers.

    def check_directive(self):

        # DIRECTIVE:        ^ '%' ...
        # The '%' indicator is already checked.
        if self.column == 0:
            return True

    def check_document_start(self):

        # DOCUMENT-START:   ^ '---' (' '|'\n')
        if self.column == 0:
            if self.prefix(3) == u'---'  \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                return True

    def check_document_end(self):

        # DOCUMENT-END:     ^ '...' (' '|'\n')
        if self.column == 0:
            if self.prefix(3) == u'...'  \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                return True

    def check_block_entry(self):

        # BLOCK-ENTRY:      '-' (' '|'\n')
        return self.peek(1) in u'\0 \t\r\n\x85\u2028\u2029'

    def check_key(self):

        # KEY(flow context):    '?'
        if self.flow_level:
            return True

        # KEY(block context):   '?' (' '|'\n')
        else:
            return self.peek(1) in u'\0 \t\r\n\x85\u2028\u2029'

    def check_value(self):

        # VALUE(flow context):  ':'
        if self.flow_level:
            return True

        # VALUE(block context): ':' (' '|'\n')
        else:
            return self.peek(1) in u'\0 \t\r\n\x85\u2028\u2029'

    def check_plain(self):

        # A plain scalar may start with any non-space character except:
        #   '-', '?', ':', ',', '[', ']', '{', '}',
        #   '#', '&', '*', '!', '|', '>', '\'', '\"',
        #   '%', '@', '`'.
        #
        # It may also start with
        #   '-', '?', ':'
        # if it is followed by a non-space character.
        #
        # Note that we limit the last rule to the block context (except the
        # '-' character) because we want the flow context to be space
        # independent.
        ch = self.peek()
        return ch not in u'\0 \t\r\n\x85\u2028\u2029-?:,[]{}#&*!|>\'\"%@`'  \
                or (self.peek(1) not in u'\0 \t\r\n\x85\u2028\u2029'
                        and (ch == u'-' or (not self.flow_level and ch in u'?:')))

    # Scanners.

    def scan_to_next_token(self):
        # We ignore spaces, line breaks and comments.
        # If we find a line break in the block context, we set the flag
        # `allow_simple_key` on.
        # The byte order mark is stripped if it's the first character in the
        # stream. We do not yet support BOM inside the stream as the
        # specification requires. Any such mark will be considered as a part
        # of the document.
        #
        # TODO: We need to make tab handling rules more sane. A good rule is
        #   Tabs cannot precede tokens
        #   BLOCK-SEQUENCE-START, BLOCK-MAPPING-START, BLOCK-END,
        #   KEY(block), VALUE(block), BLOCK-ENTRY
        # So the checking code is
        #   if <TAB>:
        #       self.allow_simple_keys = False
        # We also need to add the check for `allow_simple_keys == True` to
        # `unwind_indent` before issuing BLOCK-END.
        # Scanners for block, flow, and plain scalars need to be modified.

        if self.index == 0 and self.peek() == u'\uFEFF':
            self.forward()
        found = False
        while not found:
            while self.peek() == u' ':
                self.forward()
            if self.peek() == u'#':
                while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                    self.forward()
            if self.scan_line_break():
                if not self.flow_level:
                    self.allow_simple_key = True
            else:
                found = True

    def scan_directive(self):
        # See the specification for details.
        start_mark = self.get_mark()
        self.forward()
        name = self.scan_directive_name(start_mark)
        value = None
        if name == u'YAML':
            value = self.scan_yaml_directive_value(start_mark)
            end_mark = self.get_mark()
        elif name == u'TAG':
            value = self.scan_tag_directive_value(start_mark)
            end_mark = self.get_mark()
        else:
            end_mark = self.get_mark()
            while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                self.forward()
        self.scan_directive_ignored_line(start_mark)
        return DirectiveToken(name, value, start_mark, end_mark)

    def scan_directive_name(self, start_mark):
        # See the specification for details.
        length = 0
        ch = self.peek(length)
        while u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'    \
                or ch in u'-_':
            length += 1
            ch = self.peek(length)
        if not length:
            raise ScannerError("while scanning a directive", start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        value = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        return value

    def scan_yaml_directive_value(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        major = self.scan_yaml_directive_number(start_mark)
        if self.peek() != '.':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit or '.', but found %r"
                    % self.peek().encode('utf-8'),
                    self.get_mark())
        self.forward()
        minor = self.scan_yaml_directive_number(start_mark)
        if self.peek() not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit or ' ', but found %r"
                    % self.peek().encode('utf-8'),
                    self.get_mark())
        return (major, minor)

    def scan_yaml_directive_number(self, start_mark):
        # See the specification for details.
        ch = self.peek()
        if not (u'0' <= ch <= u'9'):
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit, but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        length = 0
        while u'0' <= self.peek(length) <= u'9':
            length += 1
        value = int(self.prefix(length))
        self.forward(length)
        return value

    def scan_tag_directive_value(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        handle = self.scan_tag_directive_handle(start_mark)
        while self.peek() == u' ':
            self.forward()
        prefix = self.scan_tag_directive_prefix(start_mark)
        return (handle, prefix)

    def scan_tag_directive_handle(self, start_mark):
        # See the specification for details.
        value = self.scan_tag_handle('directive', start_mark)
        ch = self.peek()
        if ch != u' ':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected ' ', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        return value

    def scan_tag_directive_prefix(self, start_mark):
        # See the specification for details.
        value = self.scan_tag_uri('directive', start_mark)
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected ' ', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        return value

    def scan_directive_ignored_line(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        if self.peek() == u'#':
            while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                self.forward()
        ch = self.peek()
        if ch not in u'\0\r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a comment or a line break, but found %r"
                        % ch.encode('utf-8'), self.get_mark())
        self.scan_line_break()

    def scan_anchor(self, TokenClass):
        # The specification does not restrict characters for anchors and
        # aliases. This may lead to problems, for instance, the document:
        #   [ *alias, value ]
        # can be interpteted in two ways, as
        #   [ "value" ]
        # and
        #   [ *alias , "value" ]
        # Therefore we restrict aliases to numbers and ASCII letters.
        start_mark = self.get_mark()
        indicator = self.peek()
        if indicator == u'*':
            name = 'alias'
        else:
            name = 'anchor'
        self.forward()
        length = 0
        ch = self.peek(length)
        while u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'    \
                or ch in u'-_':
            length += 1
            ch = self.peek(length)
        if not length:
            raise ScannerError("while scanning an %s" % name, start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        value = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch not in u'\0 \t\r\n\x85\u2028\u2029?:,]}%@`':
            raise ScannerError("while scanning an %s" % name, start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        end_mark = self.get_mark()
        return TokenClass(value, start_mark, end_mark)

    def scan_tag(self):
        # See the specification for details.
        start_mark = self.get_mark()
        ch = self.peek(1)
        if ch == u'<':
            handle = None
            self.forward(2)
            suffix = self.scan_tag_uri('tag', start_mark)
            if self.peek() != u'>':
                raise ScannerError("while parsing a tag", start_mark,
                        "expected '>', but found %r" % self.peek().encode('utf-8'),
                        self.get_mark())
            self.forward()
        elif ch in u'\0 \t\r\n\x85\u2028\u2029':
            handle = None
            suffix = u'!'
            self.forward()
        else:
            length = 1
            use_handle = False
            while ch not in u'\0 \r\n\x85\u2028\u2029':
                if ch == u'!':
                    use_handle = True
                    break
                length += 1
                ch = self.peek(length)
            handle = u'!'
            if use_handle:
                handle = self.scan_tag_handle('tag', start_mark)
            else:
                handle = u'!'
                self.forward()
            suffix = self.scan_tag_uri('tag', start_mark)
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a tag", start_mark,
                    "expected ' ', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        value = (handle, suffix)
        end_mark = self.get_mark()
        return TagToken(value, start_mark, end_mark)

    def scan_block_scalar(self, style):
        # See the specification for details.

        if style == '>':
            folded = True
        else:
            folded = False

        chunks = []
        start_mark = self.get_mark()

        # Scan the header.
        self.forward()
        chomping, increment = self.scan_block_scalar_indicators(start_mark)
        self.scan_block_scalar_ignored_line(start_mark)

        # Determine the indentation level and go to the first non-empty line.
        min_indent = self.indent+1
        if min_indent < 1:
            min_indent = 1
        if increment is None:
            breaks, max_indent, end_mark = self.scan_block_scalar_indentation()
            indent = max(min_indent, max_indent)
        else:
            indent = min_indent+increment-1
            breaks, end_mark = self.scan_block_scalar_breaks(indent)
        line_break = u''

        # Scan the inner part of the block scalar.
        while self.column == indent and self.peek() != u'\0':
            chunks.extend(breaks)
            leading_non_space = self.peek() not in u' \t'
            length = 0
            while self.peek(length) not in u'\0\r\n\x85\u2028\u2029':
                length += 1
            chunks.append(self.prefix(length))
            self.forward(length)
            line_break = self.scan_line_break()
            breaks, end_mark = self.scan_block_scalar_breaks(indent)
            if self.column == indent and self.peek() != u'\0':

                # Unfortunately, folding rules are ambiguous.
                #
                # This is the folding according to the specification:
                
                if folded and line_break == u'\n'   \
                        and leading_non_space and self.peek() not in u' \t':
                    if not breaks:
                        chunks.append(u' ')
                else:
                    chunks.append(line_break)
                
                # This is Clark Evans's interpretation (also in the spec
                # examples):
                #
                #if folded and line_break == u'\n':
                #    if not breaks:
                #        if self.peek() not in ' \t':
                #            chunks.append(u' ')
                #        else:
                #            chunks.append(line_break)
                #else:
                #    chunks.append(line_break)
            else:
                break

        # Chomp the tail.
        if chomping is not False:
            chunks.append(line_break)
        if chomping is True:
            chunks.extend(breaks)

        # We are done.
        return ScalarToken(u''.join(chunks), False, start_mark, end_mark,
                style)

    def scan_block_scalar_indicators(self, start_mark):
        # See the specification for details.
        chomping = None
        increment = None
        ch = self.peek()
        if ch in u'+-':
            if ch == '+':
                chomping = True
            else:
                chomping = False
            self.forward()
            ch = self.peek()
            if ch in u'0123456789':
                increment = int(ch)
                if increment == 0:
                    raise ScannerError("while scanning a block scalar", start_mark,
                            "expected indentation indicator in the range 1-9, but found 0",
                            self.get_mark())
                self.forward()
        elif ch in u'0123456789':
            increment = int(ch)
            if increment == 0:
                raise ScannerError("while scanning a block scalar", start_mark,
                        "expected indentation indicator in the range 1-9, but found 0",
                        self.get_mark())
            self.forward()
            ch = self.peek()
            if ch in u'+-':
                if ch == '+':
                    chomping = True
                else:
                    chomping = False
                self.forward()
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a block scalar", start_mark,
                    "expected chomping or indentation indicators, but found %r"
                        % ch.encode('utf-8'), self.get_mark())
        return chomping, increment

    def scan_block_scalar_ignored_line(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        if self.peek() == u'#':
            while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                self.forward()
        ch = self.peek()
        if ch not in u'\0\r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a block scalar", start_mark,
                    "expected a comment or a line break, but found %r"
                        % ch.encode('utf-8'), self.get_mark())
        self.scan_line_break()

    def scan_block_scalar_indentation(self):
        # See the specification for details.
        chunks = []
        max_indent = 0
        end_mark = self.get_mark()
        while self.peek() in u' \r\n\x85\u2028\u2029':
            if self.peek() != u' ':
                chunks.append(self.scan_line_break())
                end_mark = self.get_mark()
            else:
                self.forward()
                if self.column > max_indent:
                    max_indent = self.column
        return chunks, max_indent, end_mark

    def scan_block_scalar_breaks(self, indent):
        # See the specification for details.
        chunks = []
        end_mark = self.get_mark()
        while self.column < indent and self.peek() == u' ':
            self.forward()
        while self.peek() in u'\r\n\x85\u2028\u2029':
            chunks.append(self.scan_line_break())
            end_mark = self.get_mark()
            while self.column < indent and self.peek() == u' ':
                self.forward()
        return chunks, end_mark

    def scan_flow_scalar(self, style):
        # See the specification for details.
        # Note that we loose indentation rules for quoted scalars. Quoted
        # scalars don't need to adhere indentation because " and ' clearly
        # mark the beginning and the end of them. Therefore we are less
        # restrictive then the specification requires. We only need to check
        # that document separators are not included in scalars.
        if style == '"':
            double = True
        else:
            double = False
        chunks = []
        start_mark = self.get_mark()
        quote = self.peek()
        self.forward()
        chunks.extend(self.scan_flow_scalar_non_spaces(double, start_mark))
        while self.peek() != quote:
            chunks.extend(self.scan_flow_scalar_spaces(double, start_mark))
            chunks.extend(self.scan_flow_scalar_non_spaces(double, start_mark))
        self.forward()
        end_mark = self.get_mark()
        return ScalarToken(u''.join(chunks), False, start_mark, end_mark,
                style)

    ESCAPE_REPLACEMENTS = {
        u'0':   u'\0',
        u'a':   u'\x07',
        u'b':   u'\x08',
        u't':   u'\x09',
        u'\t':  u'\x09',
        u'n':   u'\x0A',
        u'v':   u'\x0B',
        u'f':   u'\x0C',
        u'r':   u'\x0D',
        u'e':   u'\x1B',
        u' ':   u'\x20',
        u'\"':  u'\"',
        u'\\':  u'\\',
        u'N':   u'\x85',
        u'_':   u'\xA0',
        u'L':   u'\u2028',
        u'P':   u'\u2029',
    }

    ESCAPE_CODES = {
        u'x':   2,
        u'u':   4,
        u'U':   8,
    }

    def scan_flow_scalar_non_spaces(self, double, start_mark):
        # See the specification for details.
        chunks = []
        while True:
            length = 0
            while self.peek(length) not in u'\'\"\\\0 \t\r\n\x85\u2028\u2029':
                length += 1
            if length:
                chunks.append(self.prefix(length))
                self.forward(length)
            ch = self.peek()
            if not double and ch == u'\'' and self.peek(1) == u'\'':
                chunks.append(u'\'')
                self.forward(2)
            elif (double and ch == u'\'') or (not double and ch in u'\"\\'):
                chunks.append(ch)
                self.forward()
            elif double and ch == u'\\':
                self.forward()
                ch = self.peek()
                if ch in self.ESCAPE_REPLACEMENTS:
                    chunks.append(self.ESCAPE_REPLACEMENTS[ch])
                    self.forward()
                elif ch in self.ESCAPE_CODES:
                    length = self.ESCAPE_CODES[ch]
                    self.forward()
                    for k in range(length):
                        if self.peek(k) not in u'0123456789ABCDEFabcdef':
                            raise ScannerError("while scanning a double-quoted scalar", start_mark,
                                    "expected escape sequence of %d hexdecimal numbers, but found %r" %
                                        (length, self.peek(k).encode('utf-8')), self.get_mark())
                    code = int(self.prefix(length), 16)
                    chunks.append(unichr(code))
                    self.forward(length)
                elif ch in u'\r\n\x85\u2028\u2029':
                    self.scan_line_break()
                    chunks.extend(self.scan_flow_scalar_breaks(double, start_mark))
                else:
                    raise ScannerError("while scanning a double-quoted scalar", start_mark,
                            "found unknown escape character %r" % ch.encode('utf-8'), self.get_mark())
            else:
                return chunks

    def scan_flow_scalar_spaces(self, double, start_mark):
        # See the specification for details.
        chunks = []
        length = 0
        while self.peek(length) in u' \t':
            length += 1
        whitespaces = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch == u'\0':
            raise ScannerError("while scanning a quoted scalar", start_mark,
                    "found unexpected end of stream", self.get_mark())
        elif ch in u'\r\n\x85\u2028\u2029':
            line_break = self.scan_line_break()
            breaks = self.scan_flow_scalar_breaks(double, start_mark)
            if line_break != u'\n':
                chunks.append(line_break)
            elif not breaks:
                chunks.append(u' ')
            chunks.extend(breaks)
        else:
            chunks.append(whitespaces)
        return chunks

    def scan_flow_scalar_breaks(self, double, start_mark):
        # See the specification for details.
        chunks = []
        while True:
            # Instead of checking indentation, we check for document
            # separators.
            prefix = self.prefix(3)
            if (prefix == u'---' or prefix == u'...')   \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                raise ScannerError("while scanning a quoted scalar", start_mark,
                        "found unexpected document separator", self.get_mark())
            while self.peek() in u' \t':
                self.forward()
            if self.peek() in u'\r\n\x85\u2028\u2029':
                chunks.append(self.scan_line_break())
            else:
                return chunks

    def scan_plain(self):
        # See the specification for details.
        # We add an additional restriction for the flow context:
        #   plain scalars in the flow context cannot contain ',', ':' and '?'.
        # We also keep track of the `allow_simple_key` flag here.
        # Indentation rules are loosed for the flow context.
        chunks = []
        start_mark = self.get_mark()
        end_mark = start_mark
        indent = self.indent+1
        # We allow zero indentation for scalars, but then we need to check for
        # document separators at the beginning of the line.
        #if indent == 0:
        #    indent = 1
        spaces = []
        while True:
            length = 0
            if self.peek() == u'#':
                break
            while True:
                ch = self.peek(length)
                if ch in u'\0 \t\r\n\x85\u2028\u2029'   \
                        or (not self.flow_level and ch == u':' and
                                self.peek(length+1) in u'\0 \t\r\n\x85\u2028\u2029') \
                        or (self.flow_level and ch in u',:?[]{}'):
                    break
                length += 1
            # It's not clear what we should do with ':' in the flow context.
            if (self.flow_level and ch == u':'
                    and self.peek(length+1) not in u'\0 \t\r\n\x85\u2028\u2029,[]{}'):
                self.forward(length)
                raise ScannerError("while scanning a plain scalar", start_mark,
                    "found unexpected ':'", self.get_mark(),
                    "Please check http://pyyaml.org/wiki/YAMLColonInFlowContext for details.")
            if length == 0:
                break
            self.allow_simple_key = False
            chunks.extend(spaces)
            chunks.append(self.prefix(length))
            self.forward(length)
            end_mark = self.get_mark()
            spaces = self.scan_plain_spaces(indent, start_mark)
            if not spaces or self.peek() == u'#' \
                    or (not self.flow_level and self.column < indent):
                break
        return ScalarToken(u''.join(chunks), True, start_mark, end_mark)

    def scan_plain_spaces(self, indent, start_mark):
        # See the specification for details.
        # The specification is really confusing about tabs in plain scalars.
        # We just forbid them completely. Do not use tabs in YAML!
        chunks = []
        length = 0
        while self.peek(length) in u' ':
            length += 1
        whitespaces = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch in u'\r\n\x85\u2028\u2029':
            line_break = self.scan_line_break()
            self.allow_simple_key = True
            prefix = self.prefix(3)
            if (prefix == u'---' or prefix == u'...')   \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                return
            breaks = []
            while self.peek() in u' \r\n\x85\u2028\u2029':
                if self.peek() == ' ':
                    self.forward()
                else:
                    breaks.append(self.scan_line_break())
                    prefix = self.prefix(3)
                    if (prefix == u'---' or prefix == u'...')   \
                            and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                        return
            if line_break != u'\n':
                chunks.append(line_break)
            elif not breaks:
                chunks.append(u' ')
            chunks.extend(breaks)
        elif whitespaces:
            chunks.append(whitespaces)
        return chunks

    def scan_tag_handle(self, name, start_mark):
        # See the specification for details.
        # For some strange reasons, the specification does not allow '_' in
        # tag handles. I have allowed it anyway.
        ch = self.peek()
        if ch != u'!':
            raise ScannerError("while scanning a %s" % name, start_mark,
                    "expected '!', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        length = 1
        ch = self.peek(length)
        if ch != u' ':
            while u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'    \
                    or ch in u'-_':
                length += 1
                ch = self.peek(length)
            if ch != u'!':
                self.forward(length)
                raise ScannerError("while scanning a %s" % name, start_mark,
                        "expected '!', but found %r" % ch.encode('utf-8'),
                        self.get_mark())
            length += 1
        value = self.prefix(length)
        self.forward(length)
        return value

    def scan_tag_uri(self, name, start_mark):
        # See the specification for details.
        # Note: we do not check if URI is well-formed.
        chunks = []
        length = 0
        ch = self.peek(length)
        while u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'    \
                or ch in u'-;/?:@&=+$,_.!~*\'()[]%':
            if ch == u'%':
                chunks.append(self.prefix(length))
                self.forward(length)
                length = 0
                chunks.append(self.scan_uri_escapes(name, start_mark))
            else:
                length += 1
            ch = self.peek(length)
        if length:
            chunks.append(self.prefix(length))
            self.forward(length)
            length = 0
        if not chunks:
            raise ScannerError("while parsing a %s" % name, start_mark,
                    "expected URI, but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        return u''.join(chunks)

    def scan_uri_escapes(self, name, start_mark):
        # See the specification for details.
        bytes = []
        mark = self.get_mark()
        while self.peek() == u'%':
            self.forward()
            for k in range(2):
                if self.peek(k) not in u'0123456789ABCDEFabcdef':
                    raise ScannerError("while scanning a %s" % name, start_mark,
                            "expected URI escape sequence of 2 hexdecimal numbers, but found %r" %
                                (self.peek(k).encode('utf-8')), self.get_mark())
            bytes.append(chr(int(self.prefix(2), 16)))
            self.forward(2)
        try:
            value = unicode(''.join(bytes), 'utf-8')
        except UnicodeDecodeError, exc:
            raise ScannerError("while scanning a %s" % name, start_mark, str(exc), mark)
        return value

    def scan_line_break(self):
        # Transforms:
        #   '\r\n'      :   '\n'
        #   '\r'        :   '\n'
        #   '\n'        :   '\n'
        #   '\x85'      :   '\n'
        #   '\u2028'    :   '\u2028'
        #   '\u2029     :   '\u2029'
        #   default     :   ''
        ch = self.peek()
        if ch in u'\r\n\x85':
            if self.prefix(2) == u'\r\n':
                self.forward(2)
            else:
                self.forward()
            return u'\n'
        elif ch in u'\u2028\u2029':
            self.forward()
            return ch
        return u''

#try:
#    import psyco
#    psyco.bind(Scanner)
#except ImportError:
#    pass


########NEW FILE########
__FILENAME__ = serializer

__all__ = ['Serializer', 'SerializerError']

from error import YAMLError
from events import *
from nodes import *

class SerializerError(YAMLError):
    pass

class Serializer(object):

    ANCHOR_TEMPLATE = u'id%03d'

    def __init__(self, encoding=None,
            explicit_start=None, explicit_end=None, version=None, tags=None):
        self.use_encoding = encoding
        self.use_explicit_start = explicit_start
        self.use_explicit_end = explicit_end
        self.use_version = version
        self.use_tags = tags
        self.serialized_nodes = {}
        self.anchors = {}
        self.last_anchor_id = 0
        self.closed = None

    def open(self):
        if self.closed is None:
            self.emit(StreamStartEvent(encoding=self.use_encoding))
            self.closed = False
        elif self.closed:
            raise SerializerError("serializer is closed")
        else:
            raise SerializerError("serializer is already opened")

    def close(self):
        if self.closed is None:
            raise SerializerError("serializer is not opened")
        elif not self.closed:
            self.emit(StreamEndEvent())
            self.closed = True

    #def __del__(self):
    #    self.close()

    def serialize(self, node):
        if self.closed is None:
            raise SerializerError("serializer is not opened")
        elif self.closed:
            raise SerializerError("serializer is closed")
        self.emit(DocumentStartEvent(explicit=self.use_explicit_start,
            version=self.use_version, tags=self.use_tags))
        self.anchor_node(node)
        self.serialize_node(node, None, None)
        self.emit(DocumentEndEvent(explicit=self.use_explicit_end))
        self.serialized_nodes = {}
        self.anchors = {}
        self.last_anchor_id = 0

    def anchor_node(self, node):
        if node in self.anchors:
            if self.anchors[node] is None:
                self.anchors[node] = self.generate_anchor(node)
        else:
            self.anchors[node] = None
            if isinstance(node, SequenceNode):
                for item in node.value:
                    self.anchor_node(item)
            elif isinstance(node, MappingNode):
                for key, value in node.value:
                    self.anchor_node(key)
                    self.anchor_node(value)

    def generate_anchor(self, node):
        self.last_anchor_id += 1
        return self.ANCHOR_TEMPLATE % self.last_anchor_id

    def serialize_node(self, node, parent, index):
        alias = self.anchors[node]
        if node in self.serialized_nodes:
            self.emit(AliasEvent(alias))
        else:
            self.serialized_nodes[node] = True
            self.descend_resolver(parent, index)
            if isinstance(node, ScalarNode):
                detected_tag = self.resolve(ScalarNode, node.value, (True, False))
                default_tag = self.resolve(ScalarNode, node.value, (False, True))
                implicit = (node.tag == detected_tag), (node.tag == default_tag)
                self.emit(ScalarEvent(alias, node.tag, implicit, node.value,
                    style=node.style))
            elif isinstance(node, SequenceNode):
                implicit = (node.tag
                            == self.resolve(SequenceNode, node.value, True))
                self.emit(SequenceStartEvent(alias, node.tag, implicit,
                    flow_style=node.flow_style))
                index = 0
                for item in node.value:
                    self.serialize_node(item, node, index)
                    index += 1
                self.emit(SequenceEndEvent())
            elif isinstance(node, MappingNode):
                implicit = (node.tag
                            == self.resolve(MappingNode, node.value, True))
                self.emit(MappingStartEvent(alias, node.tag, implicit,
                    flow_style=node.flow_style))
                for key, value in node.value:
                    self.serialize_node(key, node, None)
                    self.serialize_node(value, node, key)
                self.emit(MappingEndEvent())
            self.ascend_resolver()


########NEW FILE########
__FILENAME__ = tokens

class Token(object):
    def __init__(self, start_mark, end_mark):
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        attributes = [key for key in self.__dict__
                if not key.endswith('_mark')]
        attributes.sort()
        arguments = ', '.join(['%s=%r' % (key, getattr(self, key))
                for key in attributes])
        return '%s(%s)' % (self.__class__.__name__, arguments)

#class BOMToken(Token):
#    id = '<byte order mark>'

class DirectiveToken(Token):
    id = '<directive>'
    def __init__(self, name, value, start_mark, end_mark):
        self.name = name
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class DocumentStartToken(Token):
    id = '<document start>'

class DocumentEndToken(Token):
    id = '<document end>'

class StreamStartToken(Token):
    id = '<stream start>'
    def __init__(self, start_mark=None, end_mark=None,
            encoding=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.encoding = encoding

class StreamEndToken(Token):
    id = '<stream end>'

class BlockSequenceStartToken(Token):
    id = '<block sequence start>'

class BlockMappingStartToken(Token):
    id = '<block mapping start>'

class BlockEndToken(Token):
    id = '<block end>'

class FlowSequenceStartToken(Token):
    id = '['

class FlowMappingStartToken(Token):
    id = '{'

class FlowSequenceEndToken(Token):
    id = ']'

class FlowMappingEndToken(Token):
    id = '}'

class KeyToken(Token):
    id = '?'

class ValueToken(Token):
    id = ':'

class BlockEntryToken(Token):
    id = '-'

class FlowEntryToken(Token):
    id = ','

class AliasToken(Token):
    id = '<alias>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class AnchorToken(Token):
    id = '<anchor>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class TagToken(Token):
    id = '<tag>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class ScalarToken(Token):
    id = '<scalar>'
    def __init__(self, value, plain, start_mark, end_mark, style=None):
        self.value = value
        self.plain = plain
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style


########NEW FILE########
