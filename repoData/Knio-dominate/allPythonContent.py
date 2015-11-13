__FILENAME__ = document
__license__ = '''
This file is part of Dominate.

Dominate is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

Dominate is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with Dominate.  If not, see
<http://www.gnu.org/licenses/>.
'''

from . import tags

try:
  basestring = basestring
except NameError: # py3
  basestring = str
  unicode = str

class document(tags.html):
  tagname = 'html'
  def __init__(self, title='Dominate', doctype='<!DOCTYPE html>', request=None):
    '''
    Creates a new document instance. Accepts `title`, `doctype`, and `request` keyword arguments.
    '''
    super(document, self).__init__()
    self.doctype    = doctype
    self.head       = super(document, self).add(tags.head())
    self.body       = super(document, self).add(tags.body())
    self.title_node = self.head.add(tags.title(title))
    self._entry     = self.body

  def get_title(self):
    return self.title_node.text

  def set_title(self, title):
    if isinstance(title, basestring):
      self.title_node.text = title
    else:
      self.head.remove(self.title_node)
      self.head.add(title)
      self.title_node = title

  title = property(get_title, set_title)

  def add(self, *args):
    '''
    Adding tags to a document appends them to the <body>.
    '''
    return self._entry.add(*args)

  def render(self, *args, **kwargs):
    '''
    Creates a <title> tag if not present and renders the DOCTYPE and tag tree.
    '''
    r = []

    #Validates the tag tree and adds the doctype if one was set
    if self.doctype:
      r.append(self.doctype)
      r.append('\n')
    r.append(super(document, self).render(*args, **kwargs))

    return u''.join(r)
  __str__ = __unicode__ = render

  def __repr__(self):
    return '<dominate.document "%s">' % self.title

########NEW FILE########
__FILENAME__ = dom1core
__license__ = '''
This file is part of Dominate.

Dominate is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

Dominate is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with Dominate.  If not, see
<http://www.gnu.org/licenses/>.
'''

try:
  basestring = basestring
except NameError: # py3
  basestring = str
  unicode = str


class dom1core(object):
  '''
  Implements the Document Object Model (Core) Level 1

  http://www.w3.org/TR/1998/REC-DOM-Level-1-19981001/
  http://www.w3.org/TR/1998/REC-DOM-Level-1-19981001/level-one-core.html
  '''
  @property
  def parentNode(self):
    '''
    DOM API: Returns the parent tag of the current element.
    '''
    return self.parent

  def getElementById(self, id):
    '''
    DOM API: Returns single element with matching id value.
    '''
    results = self.get(id=id)
    if len(results) > 1:
      raise ValueError('Multiple tags with id "%s".' % id)
    elif results:
      return results[0]
    else:
      return None

  def getElementsByTagName(self, name):
    '''
    DOM API: Returns all tags that match name.
    '''
    if isinstance(name, basestring):
      return self.get(name.lower())
    else:
      return None

  def appendChild(self, obj):
    '''
    DOM API: Add an item to the end of the children list.
    '''
    self.add(obj)
    return self



########NEW FILE########
__FILENAME__ = dom_tag
__license__ = '''
This file is part of Dominate.

Dominate is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

Dominate is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with Dominate.  If not, see
<http://www.gnu.org/licenses/>.
'''

# pylint: disable=bad-indentation, bad-whitespace, missing-docstring

import copy
import numbers
from collections import defaultdict, namedtuple, Callable
from functools import wraps
import threading

try:
  basestring = basestring
except NameError: # py3
  basestring = str
  unicode = str


try:
  import greenlet
except ImportError:
  greenlet = None

def _get_thread_context():
  context = [threading.current_thread()]
  if greenlet:
    context.append(greenlet.getcurrent())
  return hash(tuple(context))


class dom_tag(object):
  TAB = '  '  # TODO make this a parameter to render(), and a tag.

  is_single = False  # Tag does not require matching end tag (ex. <hr/>)
  is_pretty = True   # Text inside the tag should be left as-is (ex. <pre>)
                     # otherwise, text will be escaped() and whitespace may be
                     # modified

  frame = namedtuple('frame', ['tag', 'items', 'used'])

  def __new__(_cls, *args, **kwargs):
    '''
    Check if bare tag is being used a a decorator.
    decorate the function and return
    '''
    if len(args) == 1 and isinstance(args[0], Callable) \
        and not isinstance(args[0], dom_tag) and not kwargs:
      wrapped = args[0]

      @wraps(wrapped)
      def f(*args, **kwargs):
        with _cls() as _tag:
          return wrapped(*args, **kwargs) or _tag
      return f
    return object.__new__(_cls)

  def __init__(self, *args, **kwargs):
    '''
    Creates a new tag. Child tags should be passed as aruguments and attributes
    should be passed as keyword arguments.

    There is a non-rendering attribute which controls how the tag renders:

    * `__inline` - Boolean value. If True renders all children tags on the same
                   line.
    '''

    self.attributes = {}
    self.children   = []
    self.parent     = None
    self.document   = None

    # Does not insert newlines on all children if True (recursive attribute)
    self.do_inline = kwargs.pop('__inline', False)

    #Add child elements
    if args:
      self.add(*args)

    for attr, value in kwargs.items():
      self.set_attribute(*dom_tag.clean_pair(attr, value))

    self._ctx = None
    self._add_to_ctx()

  def _add_to_ctx(self):
    ctx = dom_tag._with_contexts[_get_thread_context()]
    if ctx and ctx[-1]:
      self._ctx = ctx[-1]
      ctx[-1].items.append(self)

  # stack of (root_tag, [new_tags], set(used_tags))
  _with_contexts = defaultdict(list)

  def __enter__(self):
    ctx = dom_tag._with_contexts[_get_thread_context()]
    ctx.append(dom_tag.frame(self, [], set()))
    return self

  def __exit__(self, type, value, traceback):
    ctx = dom_tag._with_contexts[_get_thread_context()]
    slf, items, used = ctx[-1]
    ctx[-1] = None
    for item in items:
      if item in used: continue
      self.add(item)
    ctx.pop()

  def __call__(self, func):
    '''
    tag instance is being used as a decorator.
    wrap func to make a copy of this tag
    '''
    # remove decorator from its context so it doesn't
    # get added in where it was defined
    if self._ctx:
      assert False, self._ctx
      self._ctx.used.add(self)

    @wraps(func)
    def f(*args, **kwargs):
      tag = copy.deepcopy(self)
      tag._add_to_ctx()
      with tag:
        return func(*args, **kwargs) or tag
    return f

  def set_attribute(self, key, value):
    '''
    Add or update the value of an attribute.
    '''
    if isinstance(key, int):
      self.children[key] = value
    elif isinstance(key, basestring):
      self.attributes[key] = value
    else:
      raise TypeError('Only integer and string types are valid for assigning '
          'child tags and attributes, respectively.')
  __setitem__ = set_attribute

  def delete_attribute(self, key):
    if isinstance(key, int):
      del self.children[key:key+1]
    else:
      del self.attributes[key]
  __delitem__ = delete_attribute

  def setdocument(self, doc):
    '''
    Creates a reference to the parent document to allow for partial-tree
    validation.
    '''
    # assume that a document is correct in the subtree
    if self.document != doc:
      self.document = doc
      for i in self.children:
        if not isinstance(i, dom_tag): return
        i.setdocument(doc)

  def add(self, *args):
    '''
    Add new child tags.
    '''
    for obj in args:
      if isinstance(obj, numbers.Number):
        # Convert to string so we fall into next if block
        obj = str(obj)

      if isinstance(obj, basestring):
        obj = escape(obj)
        self.children.append(obj)

      elif isinstance(obj, dom_tag):
        ctx = dom_tag._with_contexts[_get_thread_context()]
        if ctx and ctx[-1]:
          ctx[-1].used.add(obj)
        self.children.append(obj)
        obj.parent = self
        obj.setdocument(self.document)

      elif isinstance(obj, dict):
        for attr, value in obj.items():
          self.set_attribute(*dom_tag.clean_pair(attr, value))

      elif hasattr(obj, '__iter__'):
        for subobj in obj:
          self.add(subobj)

      else:  # wtf is it?
        raise ValueError('%r not a tag or string.' % obj)

    if len(args) == 1:
      return args[0]

    return args

  def add_raw_string(self, s):
    self.children.append(s)

  def remove(self, obj):
    self.children.remove(obj)

  def clear(self):
    for i in self.children:
      if isinstance(i, dom_tag) and i.parent is self:
        i.parent = None
    self.children = []

  def get(self, tag=None, **kwargs):
    '''
    Recursively searches children for tags of a certain
    type with matching attributes.
    '''
    # Stupid workaround since we can not use dom_tag in the method declaration
    if tag is None: tag = dom_tag

    attrs = [(dom_tag.clean_attribute(attr), value)
        for attr, value in kwargs.items()]

    results = []
    for child in self.children:
      if (isinstance(tag, basestring) and type(child).__name__ == tag) or \
        (not isinstance(tag, basestring) and isinstance(child, tag)):

        if all(child.attributes.get(attribute) == value
            for attribute, value in attrs):
          # If the child is of correct type and has all attributes and values
          # in kwargs add as a result
          results.append(child)
      if isinstance(child, dom_tag):
        # If the child is a dom_tag extend the search down through its children
        results.extend(child.get(tag, **kwargs))
    return results

  def __getitem__(self, key):
    '''
    Returns the stored value of the specified attribute or child
    (if it exists).
    '''
    if isinstance(key, int):
      # Children are accessed using integers
      try:
        return object.__getattribute__(self, 'children')[key]
      except KeyError:
        raise IndexError('Child with index "%s" does not exist.' % key)
    elif isinstance(key, basestring):
      # Attributes are accessed using strings
      try:
        return object.__getattribute__(self, 'attributes')[key]
      except KeyError:
        raise AttributeError('Attribute "%s" does not exist.' % key)
    else:
      raise TypeError('Only integer and string types are valid for accessing '
          'child tags and attributes, respectively.')
  __getattr__ = __getitem__

  def __len__(self):
    '''
    Number of child elements.
    '''
    return len(self.children)

  def __bool__(self):
    '''
    Hack for "if x" and __len__
    '''
    return True
  __nonzero__ = __bool__

  def __iter__(self):
    '''
    Iterates over child elements.
    '''
    return self.children.__iter__()

  def __contains__(self, item):
    '''
    Checks recursively if item is in children tree.
    Accepts both a string and a class.
    '''
    return bool(self.get(item))

  def __iadd__(self, obj):
    '''
    Reflexive binary addition simply adds tag as a child.
    '''
    self.add(obj)
    return self

  def render(self, indent=1, inline=False):
    data = self._render([], indent, inline)
    return u''.join(data)

  def _render(self, rendered, indent=1, inline=False):
    '''
    Returns a well-formatted string representation of the tag and renderings
    of all its child tags.
    '''
    inline = self.do_inline or inline

    t = type(self)
    name = getattr(t, 'tagname', t.__name__)

    # Workaround for python keywords and standard classes/methods
    # (del, object, input)
    if name[-1] == '_':
      name = name[:-1]

    rendered.extend(['<', name])

    for attribute, value in sorted(self.attributes.items()):
      rendered.append(' %s="%s"' % (attribute, escape(unicode(value), True)))

    rendered.append('>')

    if not self.is_single:
      self._render_children(rendered, indent, inline)

      # if there are no children, or only 1 child that is not an html element,
      # do not add tabs and newlines
      no_children = self.is_pretty and self.children and \
          (not (len(self.children) == 1 and not isinstance(self[0], dom_tag)))

      if no_children and not inline:
        rendered.append('\n')
        rendered.append(dom_tag.TAB * (indent - 1))

      rendered.append('</')
      rendered.append(name)
      rendered.append('>')

    return rendered

  # String and unicode representations are the same as render()
  def __unicode__(self):
    return self.render()
  __str__ = __unicode__

  def _render_children(self, rendered, indent=1, inline=False):
    for child in self.children:
      if isinstance(child, dom_tag):
        if not inline and self.is_pretty:
          rendered.append('\n')
          rendered.append(dom_tag.TAB * indent)
        child._render(rendered, indent + 1, inline)
      else:
        rendered.append(unicode(child))

  def __repr__(self):
    name = '%s.%s' % (self.__module__, type(self).__name__)

    attributes_len = len(self.attributes)
    attributes = '%s attribute' % attributes_len
    if attributes_len != 1: attributes += 's'

    children_len = len(self.children)
    children = '%s child' % children_len
    if children_len != 1: children += 'ren'

    return '<%s at %x: %s, %s>' % (name, id(self), attributes, children)

  @staticmethod
  def clean_attribute(attribute):
    '''
    Since some attributes match python keywords we prepend them with
    underscores. Python also does not support colons in keywords so underscores
    mid-attribute are replaced with colons.
    '''
    # shorthand
    attribute = {
      'cls': 'class',
      'className': 'class',
      'class_name': 'class',
      'fr': 'for',
      'html_for': 'for',
      'htmlFor': 'for',
    }.get(attribute, attribute)

    # Workaround for python's reserved words
    if attribute[0] == '_': attribute = attribute[1:]

    # Workaround for inability to use colon in python keywords
    if attribute in set(['http_equiv']) or attribute.startswith('data_'):
      return attribute.replace('_', '-').lower()
    return attribute.replace('_', ':').lower()

  @classmethod
  def clean_pair(cls, attribute, value):
    '''
    This will call `clean_attribute` on the attribute and also allows for the
    creation of boolean attributes.

    Ex. input(selected=True) is equivalent to input(selected="selected")
    '''
    attribute = cls.clean_attribute(attribute)

    # Check for boolean attributes
    # (i.e. selected=True becomes selected="selected")
    if value is True:
      value = attribute

    if value is False:
      value = "false"

    return (attribute, value)


def attr(*args, **kwargs):
  '''
  Set attributes on the current active tag context
  '''
  ctx = dom_tag._with_contexts[_get_thread_context()]
  if ctx and ctx[-1]:
    dicts = args + (kwargs,)
    for d in dicts:
      for attr, value in d.items():
        ctx[-1].tag.set_attribute(*dom_tag.clean_pair(attr, value))
  else:
    raise ValueError('not in a tag context')


# escape() is used in render
from .util import escape

########NEW FILE########
__FILENAME__ = tags
'''
HTML tag classes.
'''
__license__ = '''
This file is part of Dominate.

Dominate is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

Dominate is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with Dominate.  If not, see
<http://www.gnu.org/licenses/>.
'''
from .dom_tag  import dom_tag, attr
from .dom1core import dom1core

try:
  basestring = basestring
except NameError: # py3
  basestring = str
  unicode = str

underscored_classes = set(['del', 'input', 'map', 'object'])

# Tag attributes
_ATTR_GLOBAL = set([
  'accesskey', 'class', 'class', 'contenteditable', 'contextmenu', 'dir',
  'draggable', 'id', 'item', 'hidden', 'lang', 'itemprop', 'spellcheck',
  'style', 'subject', 'tabindex', 'title'
])
_ATTR_EVENTS = set([
  'onabort', 'onblur', 'oncanplay', 'oncanplaythrough', 'onchange', 'onclick',
  'oncontextmenu', 'ondblclick', 'ondrag', 'ondragend', 'ondragenter',
  'ondragleave', 'ondragover', 'ondragstart', 'ondrop', 'ondurationchange',
  'onemptied', 'onended', 'onerror', 'onfocus', 'onformchange', 'onforminput',
  'oninput', 'oninvalid', 'onkeydown', 'onkeypress', 'onkeyup', 'onload',
  'onloadeddata', 'onloadedmetadata', 'onloadstart', 'onmousedown',
  'onmousemove', 'onmouseout', 'onmouseover', 'onmouseup', 'onmousewheel',
  'onpause', 'onplay', 'onplaying', 'onprogress', 'onratechange',
  'onreadystatechange', 'onscroll', 'onseeked', 'onseeking', 'onselect',
  'onshow', 'onstalled', 'onsubmit', 'onsuspend', 'ontimeupdate',
  'onvolumechange', 'onwaiting'
])


ERR_ATTRIBUTE = 'attributes'
ERR_CONTEXT = 'context'
ERR_CONTENT = 'content'


class html_tag(dom_tag, dom1core):
  def __init__(self, *args, **kwargs):
    '''
    Creates a new html tag instance.
    '''
    super(html_tag, self).__init__(*args, **kwargs)


  # def validate(self):
  #   '''
  #   Validate the tag. This will check the attributes, context, and contents and
  #   emit tuples in the form of: element, message.
  #   '''
  #   errors = []

  #   errors.extend(self.validate_attributes())
  #   errors.extend(self.validate_context())
  #   errors.extend(self.validate_content())

  #   return errors

  # def validate_attributes(self):
  #   '''
  #   Validate the tag attributes.
  #   '''
  #   return []

  # def validate_context(self):
  #   '''
  #   Validate the tag context.
  #   '''
  #   return []

  # def validate_content(self):
  #   '''
  #   Validate the content of the tag.
  #   '''
  #   return []

  # def _check_attributes(self, *attrs):
  #   valid = set([])
  #   for attr in attrs:
  #     if hasattr(attr, '__iter__'):
  #       valid |= set(attr)
  #     else:
  #       valid.add(attr)
  #   return set(list(self.attributes.iterkeys())) - valid



################################################################################
############################### Html Tag Classes ###############################
################################################################################

# Root element

class html(html_tag):
  '''
  The html element represents the root of an HTML document.
  '''
  pass
  # def validate_attributes(self):
  #   errors = []
  #   for invalid in self._check_attributes(_ATTR_GLOBAL, 'manifest'):
  #     errors.append( (self, ERR_ATTRIBUTE, 'Invalid attribute: "%s"' % invalid) )
  #   return errors

  # def validate_context(self):
  #   if self.parent is not None and not isinstance(self.parent, iframe):
  #     return [(self, ERR_CONTEXT, 'Must be root element or child of an <iframe>')]
  #   return []

  # def validate_content(self):
  #   if len(self) != 2 or not isinstance(self[0], head) or not isinstance(self[1], body):
  #     return [(self, ERR_CONTENT, 'Children must be <head> and then <body>.')]
  #   return []



# Document metadata

class head(html_tag):
  '''
  The head element represents a collection of metadata for the document.
  '''
  pass

class title(html_tag):
  '''
  The title element represents the document's title or name. Authors should use
  titles that identify their documents even when they are used out of context,
  for example in a user's history or bookmarks, or in search results. The
  document's title is often different from its first heading, since the first
  heading does not have to stand alone when taken out of context.
  '''
  def _get_text(self):
    return u''.join(self.get(basestring))
  def _set_text(self, text):
    self.clear()
    self.add(text)
  text = property(_get_text, _set_text)

class base(html_tag):
  '''
  The base element allows authors to specify the document base URL for the
  purposes of resolving relative URLs, and the name of the default browsing
  context for the purposes of following hyperlinks. The element does not
  represent any content beyond this information.
  '''
  is_single = True

class link(html_tag):
  '''
  The link element allows authors to link their document to other resources.
  '''
  is_single = True

class meta(html_tag):
  '''
  The meta element represents various kinds of metadata that cannot be
  expressed using the title, base, link, style, and script elements.
  '''
  is_single = True

class style(html_tag):
  '''
  The style element allows authors to embed style information in their
  documents. The style element is one of several inputs to the styling
  processing model. The element does not represent content for the user.
  '''
  is_pretty = False


# Scripting

class script(html_tag):
  '''
  The script element allows authors to include dynamic script and data blocks
  in their documents. The element does not represent content for the user.
  '''
  is_pretty = False

class noscript(html_tag):
  '''
  The noscript element represents nothing if scripting is enabled, and
  represents its children if scripting is disabled. It is used to present
  different markup to user agents that support scripting and those that don't
  support scripting, by affecting how the document is parsed.
  '''
  pass


# Sections

class body(html_tag):
  '''
  The body element represents the main content of the document.
  '''
  pass

class section(html_tag):
  '''
  The section element represents a generic section of a document or
  application. A section, in this context, is a thematic grouping of content,
  typically with a heading.
  '''
  pass

class nav(html_tag):
  '''
  The nav element represents a section of a page that links to other pages or
  to parts within the page: a section with navigation links.
  '''
  pass

class article(html_tag):
  '''
  The article element represents a self-contained composition in a document,
  page, application, or site and that is, in principle, independently
  distributable or reusable, e.g. in syndication. This could be a forum post, a
  magazine or newspaper article, a blog entry, a user-submitted comment, an
  interactive widget or gadget, or any other independent item of content.
  '''
  pass

class aside(html_tag):
  '''
  The aside element represents a section of a page that consists of content
  that is tangentially related to the content around the aside element, and
  which could be considered separate from that content. Such sections are
  often represented as sidebars in printed typography.
  '''
  pass

class h1(html_tag):
  '''
  Represents the highest ranking heading.
  '''
  pass

class h2(html_tag):
  '''
  Represents the second-highest ranking heading.
  '''
  pass

class h3(html_tag):
  '''
  Represents the third-highest ranking heading.
  '''
  pass

class h4(html_tag):
  '''
  Represents the fourth-highest ranking heading.
  '''
  pass

class h5(html_tag):
  '''
  Represents the fifth-highest ranking heading.
  '''
  pass

class h6(html_tag):
  '''
  Represents the sixth-highest ranking heading.
  '''
  pass

class hgroup(html_tag):
  '''
  The hgroup element represents the heading of a section. The element is used
  to group a set of h1-h6 elements when the heading has multiple levels, such
  as subheadings, alternative titles, or taglines.
  '''
  pass

class header(html_tag):
  '''
  The header element represents a group of introductory or navigational aids.
  '''
  pass

class footer(html_tag):
  '''
  The footer element represents a footer for its nearest ancestor sectioning
  content or sectioning root element. A footer typically contains information
  about its section such as who wrote it, links to related documents,
  copyright data, and the like.
  '''
  pass

class address(html_tag):
  '''
  The address element represents the contact information for its nearest
  article or body element ancestor. If that is the body element, then the
  contact information applies to the document as a whole.
  '''
  pass


# Grouping content

class p(html_tag):
  '''
  The p element represents a paragraph.
  '''
  pass

class hr(html_tag):
  '''
  The hr element represents a paragraph-level thematic break, e.g. a scene
  change in a story, or a transition to another topic within a section of a
  reference book.
  '''
  is_single = True

class pre(html_tag):
  '''
  The pre element represents a block of preformatted text, in which structure
  is represented by typographic conventions rather than by elements.
  '''
  is_pretty = False

class blockquote(html_tag):
  '''
  The blockquote element represents a section that is quoted from another
  source.
  '''
  pass

class ol(html_tag):
  '''
  The ol element represents a list of items, where the items have been
  intentionally ordered, such that changing the order would change the
  meaning of the document.
  '''
  pass

class ul(html_tag):
  '''
  The ul element represents a list of items, where the order of the items is
  not important - that is, where changing the order would not materially change
  the meaning of the document.
  '''
  pass

class li(html_tag):
  '''
  The li element represents a list item. If its parent element is an ol, ul, or
  menu element, then the element is an item of the parent element's list, as
  defined for those elements. Otherwise, the list item has no defined
  list-related relationship to any other li element.
  '''
  pass

class dl(html_tag):
  '''
  The dl element represents an association list consisting of zero or more
  name-value groups (a description list). Each group must consist of one or
  more names (dt elements) followed by one or more values (dd elements).
  Within a single dl element, there should not be more than one dt element for
  each name.
  '''
  pass

class dt(html_tag):
  '''
  The dt element represents the term, or name, part of a term-description group
  in a description list (dl element).
  '''
  pass

class dd(html_tag):
  '''
  The dd element represents the description, definition, or value, part of a
  term-description group in a description list (dl element).
  '''
  pass

class figure(html_tag):
  '''
  The figure element represents some flow content, optionally with a caption,
  that is self-contained and is typically referenced as a single unit from the
  main flow of the document.
  '''
  pass

class figcaption(html_tag):
  '''
  The figcaption element represents a caption or legend for the rest of the
  contents of the figcaption element's parent figure element, if any.
  '''
  pass

class div(html_tag):
  '''
  The div element has no special meaning at all. It represents its children. It
  can be used with the class, lang, and title attributes to mark up semantics
  common to a group of consecutive elements.
  '''
  pass



# Text semantics

class a(html_tag):
  '''
  If the a element has an href attribute, then it represents a hyperlink (a
  hypertext anchor).

  If the a element has no href attribute, then the element represents a
  placeholder for where a link might otherwise have been placed, if it had been
  relevant.
  '''
  pass

class em(html_tag):
  '''
  The em element represents stress emphasis of its contents.
  '''
  pass

class strong(html_tag):
  '''
  The strong element represents strong importance for its contents.
  '''
  pass

class small(html_tag):
  '''
  The small element represents side comments such as small print.
  '''
  pass

class s(html_tag):
  '''
  The s element represents contents that are no longer accurate or no longer
  relevant.
  '''
  pass

class cite(html_tag):
  '''
  The cite element represents the title of a work (e.g. a book, a paper, an
  essay, a poem, a score, a song, a script, a film, a TV show, a game, a
  sculpture, a painting, a theatre production, a play, an opera, a musical, an
  exhibition, a legal case report, etc). This can be a work that is being
  quoted or referenced in detail (i.e. a citation), or it can just be a work
  that is mentioned in passing.
  '''
  pass

class q(html_tag):
  '''
  The q element represents some phrasing content quoted from another source.
  '''
  pass

class dfn(html_tag):
  '''
  The dfn element represents the defining instance of a term. The paragraph,
  description list group, or section that is the nearest ancestor of the dfn
  element must also contain the definition(s) for the term given by the dfn
  element.
  '''
  pass

class abbr(html_tag):
  '''
  The abbr element represents an abbreviation or acronym, optionally with its
  expansion. The title attribute may be used to provide an expansion of the
  abbreviation. The attribute, if specified, must contain an expansion of the
  abbreviation, and nothing else.
  '''
  pass

class time_(html_tag):
  '''
  The time element represents either a time on a 24 hour clock, or a precise
  date in the proleptic Gregorian calendar, optionally with a time and a
  time-zone offset.
  '''
  pass
_time = time_

class code(html_tag):
  '''
  The code element represents a fragment of computer code. This could be an XML
  element name, a filename, a computer program, or any other string that a
  computer would recognize.
  '''
  pass

class var(html_tag):
  '''
  The var element represents a variable. This could be an actual variable in a
  mathematical expression or programming context, an identifier representing a
  constant, a function parameter, or just be a term used as a placeholder in
  prose.
  '''
  pass

class samp(html_tag):
  '''
  The samp element represents (sample) output from a program or computing
  system.
  '''
  pass

class kbd(html_tag):
  '''
  The kbd element represents user input (typically keyboard input, although it
  may also be used to represent other input, such as voice commands).
  '''
  pass

class sub(html_tag):
  '''
  The sub element represents a subscript.
  '''
  pass

class sup(html_tag):
  '''
  The sup element represents a superscript.
  '''
  pass

class i(html_tag):
  '''
  The i element represents a span of text in an alternate voice or mood, or
  otherwise offset from the normal prose in a manner indicating a different
  quality of text, such as a taxonomic designation, a technical term, an
  idiomatic phrase from another language, a thought, or a ship name in Western
  texts.
  '''
  pass

class b(html_tag):
  '''
  The b element represents a span of text to which attention is being drawn for
  utilitarian purposes without conveying any extra importance and with no
  implication of an alternate voice or mood, such as key words in a document
  abstract, product names in a review, actionable words in interactive
  text-driven software, or an article lede.
  '''
  pass

class u(html_tag):
  '''
  The u element represents a span of text with an unarticulated, though
  explicitly rendered, non-textual annotation, such as labeling the text as
  being a proper name in Chinese text (a Chinese proper name mark), or
  labeling the text as being misspelt.
  '''
  pass

class mark(html_tag):
  '''
  The mark element represents a run of text in one document marked or
  highlighted for reference purposes, due to its relevance in another context.
  When used in a quotation or other block of text referred to from the prose,
  it indicates a highlight that was not originally present but which has been
  added to bring the reader's attention to a part of the text that might not
  have been considered important by the original author when the block was
  originally written, but which is now under previously unexpected scrutiny.
  When used in the main prose of a document, it indicates a part of the
  document that has been highlighted due to its likely relevance to the user's
  current activity.
  '''
  pass

class ruby(html_tag):
  '''
  The ruby element allows one or more spans of phrasing content to be marked
  with ruby annotations. Ruby annotations are short runs of text presented
  alongside base text, primarily used in East Asian typography as a guide for
  pronunciation or to include other annotations. In Japanese, this form of
  typography is also known as furigana.
  '''
  pass

class rt(html_tag):
  '''
  The rt element marks the ruby text component of a ruby annotation.
  '''
  pass

class rp(html_tag):
  '''
  The rp element can be used to provide parentheses around a ruby text
  component of a ruby annotation, to be shown by user agents that don't support
  ruby annotations.
  '''
  pass

class bdi(html_tag):
  '''
  The bdi element represents a span of text that is to be isolated from its
  surroundings for the purposes of bidirectional text formatting.
  '''
  pass

class bdo(html_tag):
  '''
  The bdo element represents explicit text directionality formatting control
  for its children. It allows authors to override the Unicode bidirectional
  algorithm by explicitly specifying a direction override.
  '''
  pass

class span(html_tag):
  '''
  The span element doesn't mean anything on its own, but can be useful when
  used together with the global attributes, e.g. class, lang, or dir. It
  represents its children.
  '''
  pass

class br(html_tag):
  '''
  The br element represents a line break.
  '''
  is_single = True

class wbr(html_tag):
  '''
  The wbr element represents a line break opportunity.
  '''
  is_single = True



# Edits

class ins(html_tag):
  '''
  The ins element represents an addition to the document.
  '''
  pass

class del_(html_tag):
  '''
  The del element represents a removal from the document.
  '''
  pass


# Embedded content

class img(html_tag):
  '''
  An img element represents an image.
  '''
  is_single = True

class iframe(html_tag):
  '''
  The iframe element represents a nested browsing context.
  '''
  pass

class embed(html_tag):
  '''
  The embed element represents an integration point for an external (typically
  non-HTML) application or interactive content.
  '''
  is_single = True

class object_(html_tag):
  '''
  The object element can represent an external resource, which, depending on
  the type of the resource, will either be treated as an image, as a nested
  browsing context, or as an external resource to be processed by a plugin.
  '''
  pass
_object = object_

class param(html_tag):
  '''
  The param element defines parameters for plugins invoked by object elements.
  It does not represent anything on its own.
  '''
  is_single = True

class video(html_tag):
  '''
  A video element is used for playing videos or movies, and audio files with
  captions.
  '''
  pass

class audio(html_tag):
  '''
  An audio element represents a sound or audio stream.
  '''
  pass

class source(html_tag):
  '''
  The source element allows authors to specify multiple alternative media
  resources for media elements. It does not represent anything on its own.
  '''
  is_single = True

class track(html_tag):
  '''
  The track element allows authors to specify explicit external timed text
  tracks for media elements. It does not represent anything on its own.
  '''
  is_single = True

class canvas(html_tag):
  '''
  The canvas element provides scripts with a resolution-dependent bitmap
  canvas, which can be used for rendering graphs, game graphics, or other
  visual images on the fly.
  '''
  pass

class map_(html_tag):
  '''
  The map element, in conjunction with any area element descendants, defines an
  image map. The element represents its children.
  '''
  pass

class area(html_tag):
  '''
  The area element represents either a hyperlink with some text and a
  corresponding area on an image map, or a dead area on an image map.
  '''
  is_single = True



# Tabular data

class table(html_tag):
  '''
  The table element represents data with more than one dimension, in the form
  of a table.
  '''
  pass

class caption(html_tag):
  '''
  The caption element represents the title of the table that is its parent, if
  it has a parent and that is a table element.
  '''
  pass

class colgroup(html_tag):
  '''
  The colgroup element represents a group of one or more columns in the table
  that is its parent, if it has a parent and that is a table element.
  '''
  pass

class col(html_tag):
  '''
  If a col element has a parent and that is a colgroup element that itself has
  a parent that is a table element, then the col element represents one or more
  columns in the column group represented by that colgroup.
  '''
  is_single = True

class tbody(html_tag):
  '''
  The tbody element represents a block of rows that consist of a body of data
  for the parent table element, if the tbody element has a parent and it is a
  table.
  '''
  pass

class thead(html_tag):
  '''
  The thead element represents the block of rows that consist of the column
  labels (headers) for the parent table element, if the thead element has a
  parent and it is a table.
  '''
  pass

class tfoot(html_tag):
  '''
  The tfoot element represents the block of rows that consist of the column
  summaries (footers) for the parent table element, if the tfoot element has a
  parent and it is a table.
  '''
  pass

class tr(html_tag):
  '''
  The tr element represents a row of cells in a table.
  '''
  pass

class td(html_tag):
  '''
  The td element represents a data cell in a table.
  '''
  pass

class th(html_tag):
  '''
  The th element represents a header cell in a table.
  '''
  pass



# Forms

class form(html_tag):
  '''
  The form element represents a collection of form-associated elements, some of
  which can represent editable values that can be submitted to a server for
  processing.
  '''
  pass

class fieldset(html_tag):
  '''
  The fieldset element represents a set of form controls optionally grouped
  under a common name.
  '''
  pass

class legend(html_tag):
  '''
  The legend element represents a caption for the rest of the contents of the
  legend element's parent fieldset element, if any.
  '''
  pass

class label(html_tag):
  '''
  The label represents a caption in a user interface. The caption can be
  associated with a specific form control, known as the label element's labeled
  control, either using for attribute, or by putting the form control inside
  the label element itself.
  '''
  pass

class input_(html_tag):
  '''
  The input element represents a typed data field, usually with a form control
  to allow the user to edit the data.
  '''
  is_single = True
input = _input = input_

class button(html_tag):
  '''
  The button element represents a button. If the element is not disabled, then
  the user agent should allow the user to activate the button.
  '''
  pass

class select(html_tag):
  '''
  The select element represents a control for selecting amongst a set of
  options.
  '''
  pass

class datalist(html_tag):
  '''
  The datalist element represents a set of option elements that represent
  predefined options for other controls. The contents of the element represents
  fallback content for legacy user agents, intermixed with option elements that
  represent the predefined options. In the rendering, the datalist element
  represents nothing and it, along with its children, should be hidden.
  '''
  pass

class optgroup(html_tag):
  '''
  The optgroup element represents a group of option elements with a common
  label.
  '''
  pass

class option(html_tag):
  '''
  The option element represents an option in a select element or as part of a
  list of suggestions in a datalist element.
  '''
  pass

class textarea(html_tag):
  '''
  The textarea element represents a multiline plain text edit control for the
  element's raw value. The contents of the control represent the control's
  default value.
  '''
  pass

class keygen(html_tag):
  '''
  The keygen element represents a key pair generator control. When the
  control's form is submitted, the private key is stored in the local keystore,
  and the public key is packaged and sent to the server.
  '''
  is_single = True

class output(html_tag):
  '''
  The output element represents the result of a calculation.
  '''
  pass

class progress(html_tag):
  '''
  The progress element represents the completion progress of a task. The
  progress is either indeterminate, indicating that progress is being made but
  that it is not clear how much more work remains to be done before the task is
  complete (e.g. because the task is waiting for a remote host to respond), or
  the progress is a number in the range zero to a maximum, giving the fraction
  of work that has so far been completed.
  '''
  pass

class meter(html_tag):
  '''
  The meter element represents a scalar measurement within a known range, or a
  fractional value; for example disk usage, the relevance of a query result, or
  the fraction of a voting population to have selected a particular candidate.
  '''
  pass


# Interactive elements

class details(html_tag):
  '''
  The details element represents a disclosure widget from which the user can
  obtain additional information or controls.
  '''
  pass

class summary(html_tag):
  '''
  The summary element represents a summary, caption, or legend for the rest of
  the contents of the summary element's parent details element, if any.
  '''
  pass

class command(html_tag):
  '''
  The command element represents a command that the user can invoke.
  '''
  is_single = True

class menu(html_tag):
  '''
  The menu element represents a list of commands.
  '''
  pass


# Additional markup

class comment(html_tag):
  '''
  Normal, one-line comment:
    >>> print comment("Hello, comments!")
    <!--Hello, comments!-->

  For IE's "if" statement comments:
    >>> print comment(p("Upgrade your browser."), condition='lt IE6')
    <!--[if lt IE6]><p>Upgrade your browser.</p><![endif]-->

  Downlevel conditional comments:
    >>> print comment(p("You are using a ", em("downlevel"), " browser."),
            condition='false', downlevel='revealed')
    <![if false]><p>You are using a <em>downlevel</em> browser.</p><![endif]>

  For more on conditional comments see:
    http://msdn.microsoft.com/en-us/library/ms537512(VS.85).aspx
  '''

  ATTRIBUTE_CONDITION = 'condition'

  # Valid values are 'hidden', 'downlevel' or 'revealed'
  ATTRIBUTE_DOWNLEVEL = 'downlevel'

  def render(self, indent=1, inline=False):
    has_condition = comment.ATTRIBUTE_CONDITION in self.attributes
    is_revealed   = comment.ATTRIBUTE_DOWNLEVEL in self.attributes and \
        self.attributes[comment.ATTRIBUTE_DOWNLEVEL] == 'revealed'

    rendered = '<!'
    if not is_revealed:
      rendered += '--'
    if has_condition:
      rendered += '[if %s]>' % self.attributes[comment.ATTRIBUTE_CONDITION]

    rendered += self._render_children(indent - 1, inline)

    # if len(self.children) > 1:
    if any(isinstance(child, dom_tag) for child in self):
      rendered += '\n'
      rendered += html_tag.TAB * (indent - 1)

    if has_condition:
      rendered += '<![endif]'
    if not is_revealed:
      rendered += '--'
    rendered += '>'

    return rendered

########NEW FILE########
__FILENAME__ = util
'''
Utility classes for creating dynamic html documents
'''

__license__ = '''
This file is part of Dominate.

Dominate is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

Dominate is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with Dominate.  If not, see
<http://www.gnu.org/licenses/>.
'''

import re
from .dom_tag import dom_tag


try:
  basestring = basestring
except NameError:
  basestring = str
  unichr = chr

def include(f):
  '''
  includes the contents of a file on disk.
  takes a filename
  '''
  fl = open(f, 'r')
  data = fl.read()
  fl.close()
  return data


def system(cmd, data=None):
  '''
  pipes the output of a program
  '''
  import subprocess
  s = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
  out, err = s.communicate(data)
  return out.decode('utf8')


def escape(data, quote=True):  # stoled from std lib cgi
  '''
  Escapes special characters into their html entities
  Replace special characters "&", "<" and ">" to HTML-safe sequences.
  If the optional flag quote is true, the quotation mark character (")
  is also translated.

  This is used to escape content that appears in the body of an HTML cocument
  '''
  data = data.replace("&", "&amp;")  # Must be done first!
  data = data.replace("<", "&lt;")
  data = data.replace(">", "&gt;")
  if quote:
    data = data.replace('"', "&quot;")
  return data


_unescape = {
  'quot': 34,
  'amp':  38,
  'lt':   60,
  'gt':   62,
  'nbsp': 32,
  # more here
  # http://www.w3.org/TR/html4/sgml/entities.html
  'yuml': 255,
}


def unescape(data):
  '''
  unescapes html entities. the opposite of escape.
  '''
  cc = re.compile('&(?:(?:#(\d+))|([^;]+));')

  result = []
  m = cc.search(data)
  while m:
    result.append(data[0:m.start()])
    d = m.group(1)
    if d:
      d = int(d)
      result.append(unichr(d))
    else:
      d = _unescape.get(m.group(2), ord('?'))
      result.append(unichr(d))

    data = data[m.end():]
    m = cc.search(data)

  result.append(data)
  return ''.join(result)


_reserved = ";/?:@&=+$, "
_replace_map = dict((c, '%%%2X' % ord(c)) for c in _reserved)


def url_escape(data):
  return ''.join(_replace_map.get(c, c) for c in data)


def url_unescape(data):
  return re.sub('%([0-9a-fA-F]{2})',
    lambda m: unichr(int(m.group(1), 16)), data)


class lazy(dom_tag):
  '''
  delays function execution until rendered
  '''
  def __new__(_cls, *args, **kwargs):
    '''
    Need to reset this special method or else
    dom_tag will think it's being used as a dectorator.

    This means lazy() can't be used as a dectorator, but
    thinking about when you might want that just confuses me.
    '''
    return object.__new__(_cls)

  def __init__(self, func, *args, **kwargs):
    super(lazy, self).__init__()
    self.func   = func
    self.args   = args
    self.kwargs = kwargs


  def _render(self, rendered, indent=1, inline=False):
    r = self.func(*self.args, **self.kwargs)
    rendered.append(str(r))


# TODO rename this to raw?
class text(dom_tag):
  '''
  Just a string. useful for inside context managers
  Note: this will not escape HTML, it is a raw passthrough
  '''
  def __init__(self, _text, escape=True):
    super(text, self).__init__()
    if escape:
      from . import util
      self.text = util.escape(_text)
    else:
      self.text = _text

  def _render(self, rendered, indent, inline):
    rendered.append(self.text)
    return rendered

def raw(s):
  '''
  Inserts a raw string into the DOM. Unsafe.
  '''
  return text(s, escape=False)

########NEW FILE########
__FILENAME__ = _version
__version__ = '2.1.10'

########NEW FILE########
__FILENAME__ = attributes
__license__ = '''
This file is part of pyy.

pyy is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

pyy is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with pyy. If not, see
<http://www.gnu.org/licenses/>.
'''

import unittest
from pyy.html.tags import *
from pyy.html.util import *


class AttributeTests(unittest.TestCase):
  def testAddViaDict(self):
    i = img()
    i['src'] = 'test.png'
    self.assertEqual(str(i), '<img src="test.png">')

  def testAddViaKeywordArg(self):
    i = img(src='test.png')
    self.assertEqual(str(i), '<img src="test.png">')

  def testBooleanAttribute(self):
    i = img(test=True)
    self.assertEqual(str(i), '<img test="test">')

  def testUtils(self):
    d = div()
    d += system('echo hi')
    self.assertEqual(str(d), '<div>hi\n</div>')


########NEW FILE########
__FILENAME__ = rendering
__license__ = '''
This file is part of pyy.

pyy is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

pyy is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General
Public License along with pyy. If not, see
<http://www.gnu.org/licenses/>.
'''

import unittest
from pyy.html.document import document
from pyy.html.tags     import body, h1, p, comment
from pyy.html.util     import *


class RenderingTests(unittest.TestCase):
  def testInline(self):
    self.assertEqual(str(p(h1(), __inline=True)), '<p><h1></h1></p>')

  def testIndented(self):
    self.assertEqual(str(p(h1())), '<p>\n\t<h1></h1>\n</p>')

  def testIndentedChildren(self):
    self.assertEqual(str(body(p(), p())), '<body>\n\t<p></p>\n\t<p></p>\n</body>')

  def testComment(self):
    self.assertEqual(str(comment('test')), '<!--test-->')

  def testCommentWithTags(self):
    self.assertEqual(str(body(p(), comment(p()))), '<body>\n\t<p></p>\n\t<!--\n\t<p></p>\n\t-->\n</body>')

  def testConditionalComment(self):
    self.assertEqual(str(comment(p(), condition='lt IE 7')), '<!--[if lt IE 7]>\n<p></p>\n<![endif]-->')

  def testIndentedConditionalComment(self):
    self.assertEqual(str(body(p(), comment(p(), condition='lt IE 7'))), '<body>\n\t<p></p>\n\t<!--[if lt IE 7]>\n\t<p></p>\n\t<![endif]-->\n</body>')

  def testDocumentTitleUpdate(self):
    d1 = document()
    rd1 = d1.render()
    d1.title = "test"
    rd1 = d1.render()
    d2 = document(title="test")
    rd2 = d2.render()
    self.assertEqual(rd1, rd2)

  def testEscape(self):
    self.assertEqual(str(p('Hi & There')), '<p>Hi &amp; There</p>')
    self.assertEqual(str(p(escape('Hi & There'))), '<p>Hi &amp;amp; There</p>')
    self.assertEqual(str(p(unescape('Hi &amp; There'))), '<p>Hi &amp; There</p>')



########NEW FILE########
__FILENAME__ = test_document
from dominate import document
from dominate.tags import *

def test_doc():
  d = document()
  assert d.render() == \
'''<!DOCTYPE html>
<html>
  <head>
    <title>Dominate</title>
  </head>
  <body></body>
</html>'''


def test_decorator():
  @document()
  def foo():
    p('Hello World')

  f = foo()
  assert f.render() == \
'''<!DOCTYPE html>
<html>
  <head>
    <title>Dominate</title>
  </head>
  <body>
    <p>Hello World</p>
  </body>
</html>'''


def test_bare_decorator():
  @document
  def foo():
    p('Hello World')

  assert foo().render() == \
'''<!DOCTYPE html>
<html>
  <head>
    <title>Dominate</title>
  </head>
  <body>
    <p>Hello World</p>
  </body>
</html>'''


def test_title():
  d = document()
  assert d.title == 'Dominate'

  d = document(title='foobar')
  assert d.title == 'foobar'

  d.title = 'baz'
  assert d.title == 'baz'

  d.title = title('bar')
  assert d.title == 'bar'

  assert d.render() == \
'''<!DOCTYPE html>
<html>
  <head>
    <title>bar</title>
  </head>
  <body></body>
</html>'''


if __name__ == '__main__':
  # test_doc()
  test_decorator()

########NEW FILE########
__FILENAME__ = test_dom1core
from dominate.tags import *

def test_dom():
  container = div()
  with container.add(div(id='base')) as dom:
    s1 = span('Hello', id='span1')
    s2 = span('World', id='span2')
  
  s3 = span('foobar', id='span3')
  dom.appendChild(s3)

  assert container.getElementById('base') is dom  
  assert container.getElementById('span1') is s1
  assert container.getElementById('span3') is s3
  assert container.getElementsByTagName('span') == [s1, s2, s3]
  assert container.getElementsByTagName('SPAN') == [s1, s2, s3]

########NEW FILE########
__FILENAME__ = test_html
from dominate.tags import *
import pytest

try:
  xrange = xrange
except NameError:
  xrange = range

def test_version():
  import dominate
  version = '2.1.10'
  assert dominate.version == version
  assert dominate.__version__ == version


def test_arguments():
  assert html(body(h1('Hello, pyy!'))).render() == \
'''<html>
  <body>
    <h1>Hello, pyy!</h1>
  </body>
</html>'''


def test_kwargs():
  assert div(
    id=4, 
    checked=True, 
    cls="mydiv", 
    data_name='foo', 
    onclick='alert(1);').render() == \
'''<div checked="checked" class="mydiv" data-name="foo" id="4" onclick="alert(1);"></div>'''


def test_repr():
  import re
  d = div()
  assert repr(d).startswith('<dominate.tags.div at ')
  assert repr(d).endswith(' 0 attributes, 0 children>')
  d += [1, {'id':'foo'}]
  assert repr(d).startswith('<dominate.tags.div at ')
  assert repr(d).endswith(' 1 attribute, 1 child>')


def test_add():
  d = div()
  with pytest.raises(ValueError):
    d += None
  d += 1
  d += xrange(2,3)
  d += {'id': 'foo'}
  assert d.render() == '<div id="foo">12\n</div>'
  assert len(d) == 2
  assert d
  with pytest.raises(IndexError):
    d[2]
  
  with pytest.raises(TypeError):
    d[None]

  del d[0]
  assert len(d) == 1


def test_iadd():
  list = ul()
  for item in range(4):
    list += li('Item #', item)

  # 2 children so doesn't render inline
  assert list.render() == \
'''<ul>
  <li>Item #0
  </li>
  <li>Item #1
  </li>
  <li>Item #2
  </li>
  <li>Item #3
  </li>
</ul>'''


# copy rest of examples here


def test_context_manager():
  h = ul()
  with h:
    li('One')
    li('Two')
    li('Three')

  assert h.render() == \
'''<ul>
  <li>One</li>
  <li>Two</li>
  <li>Three</li>
</ul>'''


def test_decorator():
  @div
  def f():
    p('Hello')

  assert f().render() == \
'''<div>
  <p>Hello</p>
</div>'''

  d = div()
  @d
  def f2():
    p('Hello')

  assert f2().render() == \
'''<div>
  <p>Hello</p>
</div>'''

  @div(cls='three')
  def f3():
    p('Hello')
  assert f3().render() == \
'''<div class="three">
  <p>Hello</p>
</div>'''


def test_nested_decorator():
  @div
  def f1():
    p('hello')

  d = div()
  with d:
    f1()

  assert d.render() == \
'''<div>
  <div>
    <p>hello</p>
  </div>
</div>'''

  @div()
  def f2():
    p('hello')

  d = div()
  with d:
    f2()

  assert d.render() == \
'''<div>
  <div>
    <p>hello</p>
  </div>
</div>'''


def test_text():
  from dominate.util import text
  d = div()
  with d:
    text('Hello World')

  assert d.render() == \
  '''<div>
  Hello World
</div>'''

  assert div(text('<>', escape=False)).render() == '''\
<div>
  <>
</div>'''

  assert div(text('<>')).render() == '''\
<div>
  &lt;&gt;
</div>'''


def test_raw():
  from dominate.util import raw
  d = div()
  with d:
    raw('Hello World<br />')

  assert d.render() == \
  '''<div>
  Hello World<br />
</div>'''


def test_escape():
  assert pre('<>').render() == '''\
<pre>&lt;&gt;</pre>'''


def test_attributes():
  d = div()
  d['id'] = 'foo'
  assert d['id'] == 'foo'
  del d['id']
  with pytest.raises(KeyError):
    del d['id']
  with pytest.raises(AttributeError):
    x = d['id']
  with d:
    attr(data_test=False)
  assert d['data-test'] == 'false'

  with pytest.raises(ValueError):
    attr(id='moo')


def test_lazy():
  from dominate import util
  executed = [False]
  def _lazy():
    executed[0] = True
    return span('Hi')

  d = div()
  s = util.lazy(_lazy)
  d += s

  assert executed[0] == False
  assert d.render() == '<div>\n  <span>Hi</span>\n</div>'
  assert executed[0] == True


def test_keyword_attributes():
  expected = '<div class="foo" for="bar"></div>'
  assert div(cls='foo', fr='bar').render() == expected
  assert div(_class='foo', _for='bar').render() == expected
  assert div(className='foo', htmlFor='bar').render() == expected
  assert div(class_name='foo', html_for='bar').render() == expected



########NEW FILE########
__FILENAME__ = test_utils
from dominate.tags import *
from dominate import util

def test_include():
  import os
  try:
    f = open('_test_include.deleteme', 'w')
    f.write('Hello World')
    f.close()

    d = div()
    d += util.include('_test_include.deleteme')
    assert d.render() == '<div>Hello World</div>'

  finally:
    try:
      os.remove('_test_include.deleteme')
    except:
      pass

def test_system():
  d = div()
  d += util.system('echo Hello World')
  assert d.render().replace('\r\n', '\n') == '<div>Hello World\n</div>'


def test_unescape():
  assert util.unescape('&amp;&lt;&gt;&#32;') == '&<> '

def test_url():
  assert util.url_escape('hi there?') == 'hi%20there%3F'
  assert util.url_unescape('hi%20there%3f') == 'hi there?'
########NEW FILE########
