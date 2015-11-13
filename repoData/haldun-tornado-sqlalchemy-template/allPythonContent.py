__FILENAME__ = app
# Python imports
import os

# Tornado imports
import tornado.auth
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
from tornado.web import url

# Sqlalchemy imports
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# App imports
import forms
import models
import uimodules

# Options
define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, type=bool)
define("db_path", default='sqlite:////tmp/test.db', type=str)

class Application(tornado.web.Application):
  def __init__(self):
    handlers = [
      url(r'/', IndexHandler, name='index'),
    ]
    settings = dict(
      debug=options.debug,
      static_path=os.path.join(os.path.dirname(__file__), "static"),
      template_path=os.path.join(os.path.dirname(__file__), 'templates'),
      xsrf_cookies=True,
      # TODO Change this to a random string
      cookie_secret="nzjxcjasduuqwheazmu293nsadhaslzkci9023nsadnua9sdads/Vo=",
      ui_modules=uimodules,
    )
    tornado.web.Application.__init__(self, handlers, **settings)
    engine = create_engine(options.db_path, convert_unicode=True, echo=options.debug)
    models.init_db(engine)
    self.db = scoped_session(sessionmaker(bind=engine))


class BaseHandler(tornado.web.RequestHandler):
  @property
  def db(self):
    return self.application.db


class IndexHandler(BaseHandler):
  def get(self):
    form = forms.HelloForm()
    self.render('index.html', form=form)

  def post(self):
    form = forms.HelloForm(self)
    if form.validate():
      self.write('Hello %s' % form.planet.data)
    else:
      self.render('index.html', form=form)


# Write your handlers here

def main():
  tornado.options.parse_command_line()
  http_server = tornado.httpserver.HTTPServer(Application())
  http_server.listen(options.port)
  tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = database
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:////tmp/test.db', convert_unicode=True, echo=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
  Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
  init_db()

########NEW FILE########
__FILENAME__ = forms
from wtforms import *
from wtforms.validators import *

from util import MultiValueDict

class BaseForm(Form):
  def __init__(self, handler=None, obj=None, prefix='', formdata=None, **kwargs):
    if handler:
      formdata = MultiValueDict()
      for name in handler.request.arguments.keys():
        formdata.setlist(name, handler.get_arguments(name))
    Form.__init__(self, formdata, obj=obj, prefix=prefix, **kwargs)


# TODO Put your forms here

class HelloForm(BaseForm):
  planet = TextField('name', validators=[Required()])


########NEW FILE########
__FILENAME__ = models
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def init_db(engine):
  Base.metadata.create_all(bind=engine)

# Put your models here

########NEW FILE########
__FILENAME__ = uimodules
import tornado.web

class Form(tornado.web.UIModule):
  """
  Generic form rendering module. Works with wtforms.
  Use this in your template code as:

  {% module Form(form) %}

  where `form` is a wtforms.Form object. Note that this module does not render
  <form> tag and any buttons.
  """

  def render(self, form):
    """docstring for render"""
    return self.render_string('uimodules/form.html', form=form)


# Put your uimodules here

########NEW FILE########
__FILENAME__ = util
# Copied from django with some modifications
import copy

class MultiValueDict(dict):
  """
  A subclass of dictionary customized to handle multiple values for the
  same key.

  >>> d = MultiValueDict({'name': ['Adrian', 'Simon'], 'position': ['Developer']})
  >>> d['name']
  'Simon'
  >>> d.getlist('name')
  ['Adrian', 'Simon']
  >>> d.get('lastname', 'nonexistent')
  'nonexistent'
  >>> d.setlist('lastname', ['Holovaty', 'Willison'])

  This class exists to solve the irritating problem raised by cgi.parse_qs,
  which returns a list for every key, even though most Web forms submit
  single name-value pairs.
  """
  def __init__(self, key_to_list_mapping=()):
    super(MultiValueDict, self).__init__(key_to_list_mapping)

  def __repr__(self):
    return "<%s: %s>" % (self.__class__.__name__,
               super(MultiValueDict, self).__repr__())

  def __getitem__(self, key):
    """
    Returns the last data value for this key, or [] if it's an empty list;
    raises KeyError if not found.
    """
    try:
      list_ = super(MultiValueDict, self).__getitem__(key)
    except KeyError:
      raise MultiValueDictKeyError("Key %r not found in %r" % (key, self))
    try:
      return list_[-1]
    except IndexError:
      return []

  def __setitem__(self, key, value):
    super(MultiValueDict, self).__setitem__(key, [value])

  def __copy__(self):
    return self.__class__([
      (k, v[:])
      for k, v in self.lists()
    ])

  def __deepcopy__(self, memo=None):
    if memo is None:
      memo = {}
    result = self.__class__()
    memo[id(self)] = result
    for key, value in dict.items(self):
      dict.__setitem__(result, copy.deepcopy(key, memo),
               copy.deepcopy(value, memo))
    return result

  def __getstate__(self):
    obj_dict = self.__dict__.copy()
    obj_dict['_data'] = dict([(k, self.getlist(k)) for k in self])
    return obj_dict

  def __setstate__(self, obj_dict):
    data = obj_dict.pop('_data', {})
    for k, v in data.items():
      self.setlist(k, v)
    self.__dict__.update(obj_dict)

  def get(self, key, default=None):
    """
    Returns the last data value for the passed key. If key doesn't exist
    or value is an empty list, then default is returned.
    """
    try:
      val = self[key]
    except KeyError:
      return default
    if val == []:
      return default
    return val

  def getlist(self, key):
    """
    Returns the list of values for the passed key. If key doesn't exist,
    then an empty list is returned.
    """
    try:
      return super(MultiValueDict, self).__getitem__(key)
    except KeyError:
      return []

  def setlist(self, key, list_):
    super(MultiValueDict, self).__setitem__(key, list_)

  def setdefault(self, key, default=None):
    if key not in self:
      self[key] = default
    return self[key]

  def setlistdefault(self, key, default_list=()):
    if key not in self:
      self.setlist(key, default_list)
    return self.getlist(key)

  def appendlist(self, key, value):
    """Appends an item to the internal list associated with key."""
    self.setlistdefault(key, [])
    super(MultiValueDict, self).__setitem__(key, self.getlist(key) + [value])

  def items(self):
    """
    Returns a list of (key, value) pairs, where value is the last item in
    the list associated with the key.
    """
    return [(key, self[key]) for key in self.keys()]

  def iteritems(self):
    """
    Yields (key, value) pairs, where value is the last item in the list
    associated with the key.
    """
    for key in self.keys():
      yield (key, self[key])

  def lists(self):
    """Returns a list of (key, list) pairs."""
    return super(MultiValueDict, self).items()

  def iterlists(self):
    """Yields (key, list) pairs."""
    return super(MultiValueDict, self).iteritems()

  def values(self):
    """Returns a list of the last value on every key list."""
    return [self[key] for key in self.keys()]

  def itervalues(self):
    """Yield the last value on every key list."""
    for key in self.iterkeys():
      yield self[key]

  def copy(self):
    """Returns a shallow copy of this object."""
    return copy(self)

  def update(self, *args, **kwargs):
    """
    update() extends rather than replaces existing key lists.
    Also accepts keyword args.
    """
    if len(args) > 1:
      raise TypeError("update expected at most 1 arguments, got %d" % len(args))
    if args:
      other_dict = args[0]
      if isinstance(other_dict, MultiValueDict):
        for key, value_list in other_dict.lists():
          self.setlistdefault(key, []).extend(value_list)
      else:
        try:
          for key, value in other_dict.items():
            self.setlistdefault(key, []).append(value)
        except TypeError:
          raise ValueError("MultiValueDict.update() takes either a MultiValueDict or dictionary")
    for key, value in kwargs.iteritems():
      self.setlistdefault(key, []).append(value)


########NEW FILE########
