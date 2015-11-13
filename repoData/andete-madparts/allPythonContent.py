__FILENAME__ = generatesimple
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

# TODO: rework approach

import string, copy
from functools import partial

from mutil.mutil import *

def valid(varname, g, vl):
  def make_valid(c):
    if not c in (string.ascii_letters + string.digits):
      return "_%s_" % (g.next())
    else:
      return c
  varname = ''.join([make_valid(x) for x in varname])
  retname = varname
  i = 2
  while (retname in vl):
    retname = "%s_%d"  % (varname, i)
    i += 1
  return retname

def new_coffee_meta(meta):
  a = """\
#format 1.2
#name %s
#id %s
""" % (meta['name'], meta['id'])
  if meta['desc'] == None: return a
  for line in meta['desc'].splitlines():
    a = a + ("#desc %s\n" % (line))
  return a

def _add_if(x, a, varname, key, quote = False):
  if key in x:
    if type(x[key]) == type(42.1):
      if f_eq(x[key], 0.0):
        return a
    if type(x[key]) == type(1):
      if x[key] == 0:
        return a
    if not quote:
      a = a + "%s.%s = %s\n" % (varname, key, x[key])
    else:
      a = a + "%s.%s = '%s'\n" % (varname, key, x[key])
  return a

def _simple_rect(prefix, constructor, x, g, vl, ll):
  if 'name' in x:
    name = x['name']
  else:
    name = str(g.next())
  varname = valid("%s%s" % (prefix, name), g, vl)
  a = """\
%s = new %s
""" % (varname, constructor)
  a = _add_if(x, a, varname, 'dx')
  a = _add_if(x, a, varname, 'dy')
  a = _add_if(x, a, varname, 'name', True)
  a = _add_if(x, a, varname, 'rot')
  a = _add_if(x, a, varname, 'ro')
  a = _add_if(x, a, varname, 'x')
  a = _add_if(x, a, varname, 'y')
  vl.append(varname)
  ll.append(a)
  return varname

def simple_smd_rect(t, g, x, vl, ll):
  _simple_rect('smd', 'Smd', x, g, vl, ll)

def simple_pad_rect(t, g, x, vl, ll):
  name = str(g.next())
  varname = valid("pad%s" % (name), g, vl)
  dx = x['dx']
  dy = x['dy']
  drill = x['drill']
  ro = 0
  if 'ro' in x:
    ro = x['ro']
  if dx == dy:
    a = """\
%s = new SquarePad %s, %s
""" % (varname, dx, drill)
    a = _add_if(x, a, varname, 'ro')
  elif dx == 2*dy and ro == 100:
    if 'drill_dx' in x and x['drill_dx'] == -dy/2:
      a = """\
%s = new OffsetPad %s, %s
""" % (varname, dy, drill)
    else:
      a = """\
%s = new LongPad %s, %s
""" % (varname, dy, drill)
  else:
    a = """\
%s = new RectPad %s, %s, %s
""" % (varname, dx, dy, drill)
    a = _add_if(x, a, varname, 'ro')

  a = _add_if(x, a, varname, 'name', True)
  a = _add_if(x, a, varname, 'rot')
  a = _add_if(x, a, varname, 'x')
  a = _add_if(x, a, varname, 'y')
  vl.append(varname)
  ll.append(a)
    
def _simple_t_rect(t, g, x, vl, ll):
  varname = _simple_rect(t, 'Rect', x, g, vl, ll)
  a = "%s.type = '%s'\n" % (varname, t)
  ll.append(a)

def _simple_pad_disc_octagon(g, constructor, x, vl, ll):
  name = str(g.next())
  varname = valid("pad%s" % (name), g, vl)
  a = """\
%s = new %s %s, %s
""" % (varname, constructor, x['r'], x['drill'])
  a = _add_if(x, a, varname, 'drill_dx')
  a = _add_if(x, a, varname, 'name', True)
  a = _add_if(x, a, varname, 'x')
  a = _add_if(x, a, varname, 'y')
  a = _add_if(x, a, varname, 'rot')
  vl.append(varname)
  ll.append(a)

def simple_pad_disc(t, g, x, vl, ll):
  _simple_pad_disc_octagon(g, 'RoundPad', x, vl, ll)

def simple_pad_octagon(t, g, x, vl, ll):
  _simple_pad_disc_octagon(g, 'OctagonPad', x, vl, ll)

def _simple_circle(prefix, g, x):
  varname = "%s%s" % (prefix, g.next())
  a = """\
%s = new Circle %s
%s.x = %s
%s.y = %s
""" % (varname, x['w'], varname, x['x'],
       varname, x['y'])
  a = _add_if(x, a, varname, 'r')
  a = _add_if(x, a, varname, 'rx')
  a = _add_if(x, a, varname, 'ry')
  return (varname, a)

def simple_circle(t, g, x, vl, ll):
  (varname, a) = _simple_circle(t, g, x)
  if t != 'silk':
    a = a + ("%s.type = '%s'\n" % (varname, t))
  vl.append(varname)
  ll.append(a)

def _simple_line(prefix, g, x):
  varname = "%s%s" % (prefix, g.next())
  a = """\
%s = new Line %s
%s.x1 = %s
%s.y1 = %s
%s.x2 = %s
%s.y2 = %s
""" % (varname, x['w'], varname, x['x1'],
       varname, x['y1'], varname, x['x2'],
       varname, x['y2'])
  a = _add_if(x, a, varname, 'curve')
  return (varname, a)

def simple_rect(t, g, x, vl, ll):
  varname = "%s%s" % (t, g.next())
  a = """\
%s = new Rect
""" % (varname)
  a = _add_if(x, a, varname, 'x')
  a = _add_if(x, a, varname, 'y')
  a = _add_if(x, a, varname, 'dx')
  a = _add_if(x, a, varname, 'dy')
  if t != 'silk':
    a = a + ("%s.type = '%s'\n" % (varname, t))
  vl.append(varname)
  ll.append(a)

def simple_line(t, g, x, vl, ll):
  (varname, a) = _simple_line(t, g, x)
  if t != 'silk':
    a = a + ("%s.type = '%s'\n" % (varname, t))
  vl.append(varname)
  ll.append(a)

"""
  p4 = new Polygon 0.1
  p4.start 1,1
  p4.add 1,0
  p4.add 0,1
  p4.end 0
"""
def simple_polygon(t, g, x, vl, ll):
  # TODO a rectangular polygon with w == 0 is actually a rect
  varname = "%s%s" % (t, g.next())
  a = """\
%s = new Polygon %s
""" % (varname, x['w'])
  vert = x['v']
  l = len(vert)
  if l > 0:
    a = a + ("%s.start %s, %s\n" % (varname, vert[0]['x1'], vert[0]['y1']))
    for v in vert[0:l-1]:
      c = ""
      if 'curve' in v:
        if v['curve'] != 0:
          c = ", %s" % (v['curve'])
      a = a + ("%s.add %s, %s%s\n" % (varname, v['x2'], v['y2'], c))
    c = "0.0"
    if 'curve' in vert[-1]:
      if vert[-1]['curve'] != 0:
        c = "%s" % (vert[-1]['curve'])
    a = a + ("%s.end %s\n" % (varname, c))
  if t != 'silk':
    a = a + ("%s.type = '%s'\n" % (varname, t))
  vl.append(varname)
  ll.append(a)

def _simple_name_value(prefix, constructor, g, x, vl, ll):
  y = 0
  if x.has_key('y'):
    y = x['y']
  varname = "%s%s" % (prefix, g.next())
  a = """\
%s = new %s %s
""" % (varname, constructor, y)
  a = _add_if(x, a, varname, 'x')
  return (varname, a)

def _simple_silk_label(g, x, vl, ll):
  varname = "label%s" % (g.next())
  a = """\
%s = new Label '%s'
%s.x = %s
%s.y = %s
%s.dy = %s
""" % (varname, x['value'], varname, x['x'], varname, x['y'],
       varname, x['dy'])
  return (varname, a)

def simple_label(t, g, x, vl, ll):
  v = x['value']
  if not 'x' in x:
   x['x'] = 0.0
  if v == 'NAME':
    (varname, a) = _simple_name_value('name', 'Name', g, x, vl, ll)
  elif v == 'VALUE':
    (varname, a) = _simple_name_value('value', 'Value', g, x, vl, ll)
  else:
    (varname, a) = _simple_silk_label(g, x, vl, ll)
  if t != 'silk':
    a = a + "%s.type = '%s'\n" % (varname, t)
  vl.append(varname)
  ll.append(a)

def simple_special_single(t, g, x, vl, ll):
  direction = x['direction']
  if direction == 'x':
    f = 'rot_single'
  else:
    f = 'single'
  # varname selection here is not perfect; should depend on actual naming
  var = "%s1" % (x['ref'])
  num = x['num']
  e = x['e']
  a = """\
l = %s [%s], %s, %s
""" % (f, var, num, e)
  vl.remove(var)
  vl.append('l')
  ll.append(a)

def simple_special_dual(t, g, x, vl, ll):
  direction_is_x = x['direction'] == 'x'
  alt = x['alt']
  f = 'dual'
  if direction_is_x: f = 'rot_dual'
  if alt: f = 'alt_%s' % (f)
  # varname selection here is not perfect; should depend on actual naming
  var = "%s1" % (x['ref'])
  num = x['num']
  e = x['e']
  between = x['between']
  a = """\
l = %s [%s], %s, %s, %s
""" % (f, var, num, e, between)
  vl.remove(var)
  vl.append('l')
  ll.append(a)

def simple_special_quad(t, g, x, vl, ll):
  # varname selection here is not perfect; should depend on actual naming
  var = "%s1" % (x['ref'])
  num = x['num']
  e = x['e']
  between = x['between']
  a = """\
l = quad [%s], %s, %s, %s
""" % (var, num, e, between)
  vl.remove(var)
  vl.append('l')
  ll.append(a)
    
def simple_special_mod(t, g, x, vl, ll):
  x2 = copy.deepcopy(x)
  i = x2['index']
  del x2['index']
  del x2['type']
  del x2['shape']
  if 'real_shape' in x2:
    x2['shape'] = x2['real_shape']
    del x2['real_shape']
  a = ""
  for (k,v) in x2.items():
    if type(v) == type("") or k == 'name':
      a = a + "l[%s].%s = '%s'\n" % (i, k, v)
    else:
      a = a + "l[%s].%s = %s\n" % (i, k, v)
  ll.append(a)

def simple_unknown(t, g, x, vl, ll):
  varname = "unknown%s" % (g.next())
  a = "%s = new Object\n" % (varname)
  for k in x.keys():
    a = a + "%s.%s = '%s'\n" % (varname, k, x[k])
  vl.append(varname)
  ll.append(a)

# add as needed...

basic_dispatch = {
  'circle': simple_circle,
  'line': simple_line,
  'vertex': simple_line,
  'label': simple_label,
  'rect': simple_rect,
  'polygon': simple_polygon,
}

special_dispatch = {
 'smd_rect': simple_smd_rect,

 'pad_rect': simple_pad_rect,
 'pad_disc': simple_pad_disc,
 'pad_octagon': simple_pad_octagon,

 'special_single': simple_special_single,
 'special_dual': simple_special_dual,
 'special_quad': simple_special_quad,
 'special_mod': simple_special_mod,
}

def generate_coffee(interim):
  generators = {
   'smd': generate_ints(),
   'pad': generate_ints(),
   'silk': generate_ints(),
   'docu': generate_ints(),
   'restrict': generate_ints(),
   'stop': generate_ints(),
   'keepout': generate_ints(),
   'vrestrict': generate_ints(),
   'glue': generate_ints(),
   'unknown': generate_ints(),
   'special': generate_ints(),
  }
  varnames = []
  lines = []
  meta = None
  for x in interim:
    t = x['type']
    if t == 'meta': meta = new_coffee_meta(x)
    else:
      shape = x['shape']
      key = "%s_%s" % (t, shape)
      g = generators[t]
      if key in special_dispatch:
        special_dispatch.get(key)(t, g, x, varnames, lines)
      else:
        basic_dispatch.get(shape, simple_unknown)(t, g, x, varnames, lines)
  varnames.sort()
  combine = 'combine ['+ (','.join(varnames)) + ']\n'
  lines_joined = ''.join(lines)
  lines_joined = '  ' + lines_joined.replace('\n', '\n  ')
  return meta + "footprint = () ->\n" + lines_joined + combine
    

########NEW FILE########
__FILENAME__ = library
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import os, os.path, glob

import coffee.pycoffee as pycoffee

class Meta:

  def __init__(self, meta):
    if not 'desc' in meta:
      meta['desc'] = ''
    if not 'parent' in meta:
      meta['parent'] = None
    self.meta = meta
    for k in meta:
      self.__dict__[k] = meta[k]
    self.child_ids = []

class Library:

  def __init__(self, name, directory):
    self.name = name
    self.directory = directory
    self.exists = os.path.exists(self.directory)
    self.is_dir = True
    self.readonly = False
    if self.exists:
      self.is_dir = os.path.isdir(self.directory)
      self.readonly = not os.access(self.directory, os.W_OK)
    self.meta_list = []
    self.fail_list = []
    self.meta_by_id = {}
    self.scan()

  def scan(self, select_id = None):
    self.meta_list = []
    self.fail_list = []
    if not self.exists: return
    for path in glob.glob(self.directory + '/*.coffee'):
      with open(path) as f:
        code = f.read()
      meta = pycoffee.eval_coffee_meta(code)
      if not 'name' in meta or not 'id' in meta: 
        self.fail_list.append(meta)
        continue
      meta['readonly'] = not os.access(path, os.W_OK)
      meta['filename'] = path
      self.meta_list.append(meta)
    self.meta_list = [Meta(meta) for meta in self.meta_list]
    self.meta_list.sort(key=lambda x: x.name)
    self.meta_by_id = {}
    for meta in self.meta_list:
      self.meta_by_id[meta.id] = meta
    self.meta_by_name = {}
    for meta in self.meta_list:
      self.meta_by_name[meta.name] = meta
    # scan child relationships
    found_as_child = []
    for meta in self.meta_list:
      if meta.parent != None and meta.parent in self.meta_by_id:
        self.meta_by_id[meta.parent].child_ids.append(meta.id)
        found_as_child.append(meta.id)
    self.root_meta_list = filter(lambda meta: meta.id not in found_as_child, self.meta_list)

########NEW FILE########
__FILENAME__ = pycoffee
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# (c) 2013 Alex Schultz <alex@strangeautomata.com>
# License: GPL

import os.path, re, traceback
from inter import inter

from qtscriptwrapper import JsEngine
from qtscriptwrapper import JsEngineException

supported_formats = ['1.0', '1.1', '1.2']
current_format = supported_formats[-1]

js_make_js_from_coffee = None
js_make_js_ctx = None
js_ctx_cleanup_count = 0

def prepare_coffee_compiler():
  global js_make_js_from_coffee
  global js_make_js_ctx
  if js_make_js_from_coffee == None:
      js_make_js_ctx = JsEngine()
      try:
        js_make_js_from_coffee = js_make_js_ctx.evaluate("""
CoffeeScript = require('coffee-script');
(function (coffee_code) {
  js_code = CoffeeScript.compile(coffee_code, {bare:true});
  return js_code;
})
""")
      except JsEngineException as ex:
        raise ex
      finally:
        pass

# there is probably plenty of room for speeding up things here by
# re-using the generated js from ground and such, however for now it is
# still snappy enough; so let's just keep it simple
def eval_coffee_footprint(coffee):
  meta = eval_coffee_meta(coffee)
  if 'format' not in meta:
    raise Exception("Missing mandatory #format meta field")
  else:
    format = meta['format']
  if format not in supported_formats:
     raise Exception("Unsupported file format. Supported formats: %s" % (supported_formats))
  # only compile the compiler once
  global js_make_js_ctx
  global js_make_js_from_coffee
  global js_ctx_cleanup_count
  js_ctx_cleanup_count = js_ctx_cleanup_count + 1
  # HACK: occationally cleanup the context to avoid compiler slowdown
  # will need a better approach in the future
  if js_ctx_cleanup_count == 10:
    js_make_js_ctx = None
    js_make_js_from_coffee = None
    js_ctx_cleanup_count = 0
  if js_make_js_ctx == None:
    prepare_coffee_compiler()
  try:
    data_dir = os.environ['DATA_DIR']
    filename = os.path.join(data_dir, 'grind', "ground-%s.coffee" % (format))
    with open(filename) as f:
      ground = f.read()
    
    ground_js = js_make_js_from_coffee(ground)
    js = js_make_js_from_coffee(coffee + "\nreturn footprint()\n")
    
    # If the code returned is an error, raise an exception
    if ("isError" in dir(js) and js.isError()):
      raise Exception(js.toString())
    
    js_res = js_make_js_ctx.evaluate("(function() {\n" + ground_js + js + "\n}).call(this);\n")
    pl = js_res.toVariant()
    pl.append(meta)
    return pl
  finally:
    pass

# TODO: the meta stuff doesn't really belong here

def eval_coffee_meta(coffee):
  coffee = str(coffee)
  lines = coffee.replace('\r', '').split('\n')
  meta_lines = [l for l in lines if re.match('^#\w+',l)]
  meta_list = [re.split('\s',l, 1) for l in meta_lines]
  meta_list = [(l[0][1:], l[1]) for l in meta_list]
  def _collect(acc, (k,v)):
    if k in acc:
      acc[k] = acc[k] + "\n" + v
    else:
      acc[k] = v
    return acc
  return reduce(_collect, meta_list, { 'type': 'meta'})

def clone_coffee_meta(coffee, old_meta, new_id, new_name):
  cl = coffee.splitlines()
  def not_meta_except_desc(s):
    return not re.match('^#\w+',l) or re.match('^#desc \w+', l)
  no_meta_l = [l for l in coffee.splitlines() if not_meta_except_desc(l)]
  no_meta_coffee = '\n'.join(no_meta_l)
  new_meta = "#format %s\n#name %s\n#id %s\n#parent %s\n" % (current_format, new_name, new_id, old_meta['id'])
  return new_meta + no_meta_coffee

def new_coffee(new_id, new_name):
  return """\
#format %s
#name %s
#id %s
#desc TODO

footprint = () ->
  []
""" % (current_format, new_name, new_id)

def preprocess_coffee(code):
  def repl(m):
    t = m.group(2)
    i = float(m.group(1))
    if t == 'mi' or t == 'mil':
      return str(i*0.0254)
    elif t == 'in':
      return str(i*25.4)
    else:
      return m.group(0)
  return re.sub('([-+]?[0-9]*\.?[0-9]+)([mi][ni]l?)', repl, code)

def compile_coffee(code):
  try:
    preprocessed = preprocess_coffee(code)
    interim = eval_coffee_footprint(preprocessed)
    if interim != None:
      interim = inter.cleanup_js(interim)
      interim = inter.add_names(interim)
      return (None, None, interim)
    else:
      return ('internal error', 'internal error', None)
  except JsEngineException as ex:
    s = ex.getMessage()
    return ('coffee error:\n' + s, s, None)
  except Exception as ex:
    tb = traceback.format_exc()
    return ('other error:\n' + str(ex) + "\n"+tb, str(ex), None)

########NEW FILE########
__FILENAME__ = qtscriptwrapper
#!/usr/bin/python2

# (c) 2013 Alex Schultz <alex@strangeautomata.com>
# License: GPL

import os
import os.path
from PySide import QtCore
from PySide.QtCore import QObject
from PySide.QtScript import QScriptEngine
from PySide.QtScript import QScriptValue
from PySide.QtGui import QApplication
from PySide.QtCore import QCoreApplication

# This class is a QObject that gets wrapped as a javascript object, to provide
# the callback for the "require" call. See comments in JsEngine for why this
# isn't just a wrapped function instead of a QObject...
class JsEngineRequireClass(QObject):
  def __init__(self, engine):
    super(JsEngineRequireClass, self).__init__()
    self.engine = engine
  @QtCore.Slot(str, result=QScriptValue)
  def require(self, arg):
    data_dir = os.environ['DATA_DIR']
    filename = os.path.join(data_dir, 'coffeescript', "%s.js" % (arg))
    with open(filename) as f:
      file_content = f.read()
    try:
      ret = self.engine.evaluate(file_content, "%s.js" % (arg))
      return ret
    except JsEngineException as ex:
      raise ex

# Converts javascript objects to python objects. Tries to be a bit fancy and
# wrap functions. Objects that are not basic types or functions are not
# converted.
def scriptValueToPyObject(value):
  if value.isFunction():
    return lambda *x: scriptValueToPyObject(value.call(value.scope(), list(x)))
  if value.isVariant():
    pass
  elif value.isObject():
    return value
  ret = value.toVariant()
  if ("toPyObject" in dir(ret)):
    ret = ret.toPyObject()
  return ret
    
# Function to convert python objects to javascript objects. Tries to be a bit
# fancy and wrap things like functions. Things that are already javascript
# objects are left as-is, of course.
def pyObjectToScriptValue(engine, value):
  if (isinstance(value, QScriptValue)):
    return value
  if (("__call__" in dir(value)) and ("func_name" in dir(value))):
    f = lambda context,engine: pyObjectToScriptValue(engine, func(*_contextToArguments(context)))
    return engine.newFunction(f)
  if (isinstance(value, QObject)):
    return engine.newQObject(value)
  return engine.newVariant(value)

# Converts a javascript context to a list of arguments
def _contextToArguments(context):
  ret = []
  for i in range(context.argumentCount()):
    ret.append(scriptValueToPyObject(context.argument(i)))
  return ret

# Class for representing javascript engine exceptions
class JsEngineException(Exception):
  def __init__(self, result, engine):
    super(JsEngineException, self).__init__()
    self.line = engine.uncaughtExceptionLineNumber()
    self.message = result.toString()
  def __repr__(self):
    return "%s(%d, \"%s\")" % (str(self.__class__), self.line, self.message)
  def __str__(self):
    return "QtScript exception at line %d: %s" % (self.line, self.message)
  def getLine(self):
    return self.line
  def getMessage(self):
    return self.message

# Class to wrap the QScriptEngine
class JsEngine:
  def __init__(self):
    self.app = QApplication.instance()
    if self.app is None:
      self.app = QCoreApplication([])
    self.engine = QScriptEngine()
    self.globalObject = self.engine.globalObject()
    
    # There were some problems evalating javascript inside a function callback. QtSide's bindings for QScriptEngine
    # didn't seem prepared to handle it (it breaks in weird hard-to-debug ways)
    # It is however not a problem if you use a wrapped QObject for the callback instead of using engine.newFunction().
    # The workaround here is to pass a wrapped QObject, and then evaluate javascript to create a function that calls
    # a method of the wrapped QObject.
    # Also note: Wrapped QObjects passed to QtSide are not refcounted in Python! To work around this, a reference to
    #            "RequireObj" is stored in the JSEngine instance
    self.requireObj = JsEngineRequireClass(self.engine)
    self.addObject('RequireObj', self.requireObj)
    self.evaluate("""
function require(arg) {
  return RequireObj.require(arg);
}
    """)
  
  # Sets a variable in the global object
  def addObject(self, name, obj):
    wrappedObject = pyObjectToScriptValue(self.engine, obj)
    self.engine.globalObject().setProperty(name, wrappedObject)
  
  # Adds a python function to the global object, wrapping it
  def addFunction(self, name, func):
    f = lambda context,engine: pyObjectToScriptValue(engine, func(*_contextToArguments(context)))
    wrappedFunction = self.engine.newFunction(f)
    self.engine.globalObject().setProperty(name, wrappedFunction)
    
  # Adds a python function to the global object, not wrapping it (it gets passed raw context and engine arguments)
  def addRawFunction(self, name, func):
    wrappedFunction = self.engine.newFunction(func)
    self.engine.globalObject().setProperty(name, wrappedFunction)

  # Evaluate some javascript code
  def evaluate(self, code):
    result = self.engine.evaluate(code)
    if self.engine.hasUncaughtException():
      raise JsEngineException(result, self.engine)
    return scriptValueToPyObject(result)

if __name__ == '__main__':
  engine = JsEngine()
  engine.evaluate("print('Hello World');")

########NEW FILE########
__FILENAME__ = detect
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import eagle, kicad, madparts, kicad_old

MADPARTS = "madparts"
EAGLE = "eagle"
KICAD = "kicad"
KICAD_OLD = "kicad-old"

def detect(fn):
  v =  madparts.detect(fn)
  if v is not None:
    return (MADPARTS, v)
  v = eagle.detect(fn)
  if v is not None:
    return (EAGLE, v)
  v = kicad.detect(fn)
  if v is not None:
    return (KICAD, v)
  v = kicad_old.detect(fn)
  if v is not None:
    return (KICAD_OLD, v)
  raise Exception("Unknown file format")

def make_exporter_for(t, fn):
  if t == EAGLE:
    return eagle.Export(fn)
  elif t == KICAD:
    return kicad.Export(fn)
  elif t == KICAD_OLD:
    return kicad_old.Export(fn)
  else:
    raise Exception("Invalid export format")



def make_exporter(fn):
  (t,_) = detect(fn)
  return make_exporter_for(t, fn)


def make_importer(fn):  
  (t,_) = detect(fn)
  if t == EAGLE:
    return eagle.Import(fn)
  elif t == KICAD:
    return kicad.Import(fn)
  elif t == KICAD_OLD:
    return kicad_old.Import(fn)
  elif t == MADPARTS:
    return madparts.Import(fn) # for listing!
  else:
    raise Exception("Invalid export format")

########NEW FILE########
__FILENAME__ = eagle
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import uuid, re, copy, math

from bs4 import BeautifulSoup, Tag

from mutil.mutil import *

from inter import inter

# TODO: get from eagle XML isof hardcoded; 
# however in practice this is quite low prio as everybody probably
# uses the same layer numbers
def type_to_layer_number(layer):
  type_to_layer_number_dict = {
    'smd': 1,
    'pad': 17,
    'silk': 21,
    'name': 25,
    'value': 27,
    'stop': 29,
    'glue': 35,
    'keepout': 39,
    'restrict': 41,
    'vrestrict': 43,
    'docu': 51,
    }
  return type_to_layer_number_dict[layer]

def layer_number_to_type(layer):
  # assymetric
  layer_number_to_type_dict = {
    1: 'smd',
    16: 'pad',
    21: 'silk',
    25: 'silk',
    27: 'silk',
    29: 'stop',
    35: 'glue',
    39: 'keepout',
    41: 'restrict',
    43: 'vrestrict',
    51: 'docu',
    }
  return layer_number_to_type_dict[layer]

def _load_xml_file(fn):
  with open(fn) as f:
    return BeautifulSoup(f, 'xml')
  
def _save_xml_file(fn, soup):
  with open(fn, 'w+') as f:
    f.write(str(soup))

def _check_xml(soup):
  if soup.eagle == None:
    raise Exception("Unknown file format")
  v = soup.eagle.get('version')
  if v == None:
    raise Exception("Unknown file format (no eagle XML?)")
  if float(v) < 6:
    raise Exception("Eagle 6.0 or later is required.")
  return v

def check_xml_file(fn):
  soup = _load_xml_file(fn)
  v = _check_xml(soup)
  return "Eagle CAD %s library" % (v)

def detect(fn):
  try:
    soup = _load_xml_file(fn)
    return str(_check_xml(soup))
  except:
    return None

### EXPORT

class Export:

  def __init__(self, fn):
    self.fn = fn
    self.soup = _load_xml_file(fn)
    _check_xml(self.soup)

  def save(self):
    _save_xml_file(self.fn, self.soup)

  def get_data(self):
   return str(self.soup)

  # remark that this pretty formatting is NOT what is used in the final
  # eagle XML as eagle does not get rid of heading and trailing \n and such
  def get_pretty_data(self):
   return str(self.soup.prettify())

  def get_pretty_footprint(self, eagle_name):
    packages = self.soup.eagle.drawing.packages('package')
    for some_package in packages:
      if some_package['name'].lower() == eagle_name.lower():
        return str(some_package.prettify())
    raise Exception("Footprint not found")
   

  def export_footprint(self, interim):
    # make a deep copy so we can make mods without harm
    interim = copy.deepcopy(interim)
    interim = self.add_ats_to_names(interim)
    interim = clean_floats(interim)
    meta = inter.get_meta(interim)
    name = eget(meta, 'name', 'Name not found')
    # make name eagle compatible
    name = re.sub(' ','_',name)
    # check if there is an existing package
    # and if so, replace it
    packages = self.soup.eagle.drawing.packages('package')
    package = None
    for some_package in packages:
      if some_package['name'].lower() == name.lower():
        package = some_package
        package.clear()
        break
    if package == None:
      package = self.soup.new_tag('package')
      self.soup.eagle.drawing.packages.append(package)
      package['name'] = name

    def pad(shape):
      pad = self.soup.new_tag('pad')
      pad['name'] = shape['name']
      # don't set layer in a pad, it is implicit
      pad['x'] = fget(shape, 'x')
      pad['y'] = fget(shape, 'y')
      drill = fget(shape, 'drill')
      pad['drill'] = drill
      pad['rot'] = "R%d" % (fget(shape, 'rot'))
      r = fget(shape, 'r')
      shape2 = 'disc' # disc is the default
      if 'shape' in shape:
        shape2 = shape['shape']
      if shape2 == 'disc':
        pad['shape'] = 'round'
        if f_neq(r, drill*1.5):
          pad['diameter'] = r*2
      elif shape2 == 'octagon':
        pad['shape'] = 'octagon'
        if f_neq(r, drill*1.5):
          pad['diameter'] = r*2
      elif shape2 == 'rect':
        ro = iget(shape, 'ro')
        if ro == 0: 
          pad['shape'] = 'square'
          if f_neq(shape['dx'], drill*1.5):
            pad['diameter'] = float(shape['dx'])
        elif 'drill_dx' in shape:
          pad['shape'] = 'offset'
          if f_neq(shape['dy'], drill*1.5):
            pad['diameter'] = float(shape['dy'])
        else:
          pad['shape'] = 'long'
          if f_neq(shape['dy'], drill*1.5):
            pad['diameter'] = float(shape['dy'])
      package.append(pad)

    def smd(shape):
      smd = self.soup.new_tag('smd')
      smd['name'] = shape['name']
      smd['x'] = fget(shape, 'x')
      smd['y'] = fget(shape, 'y')
      smd['dx'] = fget(shape, 'dx')
      smd['dy'] = fget(shape, 'dy')
      smd['roundness'] = iget(shape, 'ro')
      smd['rot'] = "R%d" % (fget(shape, 'rot'))
      smd['layer'] = type_to_layer_number('smd')
      package.append(smd)

    def hole(shape):
      hole = self.soup.new_tag('hole')
      hole['drill'] = fget(shape, 'drill')
      hole['x'] = fget(shape, 'x')
      hole['y'] = fget(shape, 'y')
      package.append(hole)

    def rect(shape, layer):
      rect = self.soup.new_tag('rectangle')
      x = fget(shape, 'x')
      y = fget(shape, 'y')
      dx = fget(shape, 'dx')
      dy = fget(shape, 'dy')
      rect['x1'] = x - dx/2
      rect['x2'] = x + dx/2
      rect['y1'] = y - dy/2
      rect['y2'] = y + dy/2
      rect['rot'] = "R%d" % (fget(shape, 'rot'))
      rect['layer'] = layer
      package.append(rect)

    def label(shape, layer):
      label = self.soup.new_tag('text')
      x = fget(shape,'x')
      y = fget(shape,'y')
      dy = fget(shape,'dy', 1)
      s = shape['value'].upper()
      if s == "NAME": 
        s = ">NAME"
        layer = type_to_layer_number('name')
      if s == "VALUE": 
        s = ">VALUE"
        layer = type_to_layer_number('value')
      label['x'] = x
      label['y'] = y
      label['size'] = dy
      label['layer'] = layer
      label['align'] = 'center'
      label.string = s
      package.append(label)
    
    # a disc is just a circle with a clever radius and width
    def disc(shape, layer):
      r = fget(shape, 'r')
      rx = fget(shape, 'rx', r)
      ry = fget(shape, 'ry', r)
      x = fget(shape,'x')
      y = fget(shape,'y')
      disc = self.soup.new_tag('circle')
      disc['x'] = x
      disc['y'] = y
      disc['radius'] = r/2
      disc['width'] = r/2
      disc['layer'] = layer
      package.append(disc)
  
    def circle(shape, layer):
      r = fget(shape, 'r')
      rx = fget(shape, 'rx', r)
      ry = fget(shape, 'ry', r)
      x = fget(shape,'x')
      y = fget(shape,'y')
      w = fget(shape,'w')
      if 'a1' in shape or 'a2' in shape:
        wire = self.soup.new_tag('wire')
        a1 = fget(shape, 'a1')
        a2 = fget(shape, 'a2')
        wire['width'] = w
        wire['curve'] = a2-a1
        a1 = a1 * math.pi / 180
        a2 = a2 * math.pi / 180
        wire['x1'] = x + r * math.cos(a1)
        wire['y1'] = y + r * math.sin(a1)
        wire['x2'] = x + r * math.cos(a2)
        wire['y2'] = y + r * math.sin(a2)
        wire['layer'] = layer
        package.append(wire)
      else:
        circle = self.soup.new_tag('circle')
        circle['x'] = x
        circle['y'] = y
        circle['radius'] = r
        circle['width'] = w
        circle['layer'] = layer
        package.append(circle)

    def line(shape, layer):
      x1 = fget(shape, 'x1')
      y1 = fget(shape, 'y1')
      x2 = fget(shape, 'x2')
      y2 = fget(shape, 'y2')
      w = fget(shape, 'w')
      line = self.soup.new_tag('wire')
      line['x1'] = x1
      line['y1'] = y1
      line['x2'] = x2
      line['y2'] = y2
      line['width'] = w
      line['layer'] = layer
      if 'curve' in shape:
        if shape['curve'] != 0.0:
          line['curve'] = fget(shape, 'curve')
      package.append(line)
  
    # eagle polygon format is somewhat wierd
    # each vertex is actually a starting point towards the next
    # where the last one is a starting point around towards the first
    #  <polygon width="0.127" layer="21">
    #  <vertex x="-1" y="-1"/>
    #  <vertex x="-1" y="1"/>
    #  <vertex x="0" y="1" curve="-90"/>
    #  <vertex x="1" y="0" curve="-90"/>
    #  <vertex x="0" y="-1"/>
    #  </polygon>
    def polygon(shape, layer):
      p = self.soup.new_tag('polygon')
      p['width'] = fget(shape, 'w')
      p['layer'] = layer
      for v in shape['v']:
        vert = self.soup.new_tag('vertex')
        vert['x'] = fget(v, 'x1')
        vert['y'] = fget(v, 'y1')
        curve = fget(v, 'curve')
        if curve != 0.0:
          vert['curve'] = fget(v, 'curve')
        p.append(vert)
      package.append(p)

    def silk(shape):
      if not 'shape' in shape: return
      layer = type_to_layer_number(shape['type'])
      s = shape['shape']
      if s == 'line' or s == 'vertex': line(shape, layer)
      elif s == 'circle': circle(shape, layer)
      elif s == 'disc': disc(shape, layer)
      elif s == 'label': label(shape, layer)
      elif s == 'rect': rect(shape, layer)
      elif s == 'polygon': polygon(shape, layer)

    def unknown(shape):
      pass

    idx = eget(meta, 'id', 'Id not found')
    desc = oget(meta, 'desc', '')
    parent_idx = oget(meta, 'parent', None)
    description = self.soup.new_tag('description')
    package.append(description)
    parent_str = ""
    if parent_idx != None:
      parent_str = " parent: %s" % parent_idx
    description.string = desc + "\n<br/><br/>\nGenerated by 'madparts'.<br/>\nId: " + idx   +"\n" + parent_str
    # TODO rework to be shape+type based ?
    for shape in interim:
      if 'type' in shape:
        {
          'pad': pad,
          'silk': silk,
          'docu': silk,
          'keepout': silk,
          'stop': silk,
          'restrict': silk,
          'vrestrict': silk,
          'smd': smd,
          'hole': hole,
          }.get(shape['type'], unknown)(shape)
    return name

  def add_ats_to_names(self, interim):
    t = {}
    for x in interim:
      if x['type'] == 'smd' or x['type'] == 'pad':
        name = x['name']
        if not name in t:
          t[name] = 0
        t[name] = t[name] + 1
    multi_names = {}
    for k in t.keys():
      if t[k] > 1:
        multi_names[k] = 1
    def adapt(x):
      if x['type'] == 'smd' or x['type'] == 'pad':
        name = re.sub(' ','_', str(x['name']))
        if name in multi_names:
          x['name'] = "%s@%d" % (name, multi_names[name])
          multi_names[name] = multi_names[name] + 1
      return x
    return [adapt(x) for x in interim]

### IMPORT

class Import:

  def __init__(self, fn):
    self.soup = _load_xml_file(fn)
    _check_xml(self.soup)

  def list_names(self):
    packages = self.soup.eagle.drawing.packages('package')
    def desc(p):
      if p.description != None: return p.description.string
      else: return None
    return [(p['name'], desc(p)) for p in packages]

  def list(self):
    names = map(lambda (a,_): a, self.list_names())
    for name in names: print name

  def import_footprint(self, name):

    packages = self.soup.eagle.drawing.packages('package')
    package = None
    for p in packages:
       if p['name'] == name:
         package = p
         break
    if package == None:
      raise Exception("footprint not found %s " % (name))
    meta = {}
    meta['type'] = 'meta'
    meta['name'] = name
    meta['id'] = uuid.uuid4().hex
    meta['desc'] = None
    l = [meta]

    def clean_name(name):
      if len(name) > 2 and name[0:1] == 'P$':
        name = name[2:]
        # this might cause name clashes :(
        # get rid of @ suffixes
      return re.sub('@\d+$', '', name)

    def text(text):
      res = {}
      res['type'] = 'silk'
      res['shape'] = 'label'
      s = text.string
      layer = int(text['layer'])
      size = float(text['size'])
      align = 'bottom-left' # eagle default
      if text.has_attr('align'):
        align = text['align']
      if align == 'center':
        x = float(text['x'])
        y = float(text['y'])
      elif align == 'bottom-left':
        x = float(text['x']) + len(s)*size/2
        y = float(text['y']) + size/2
      else:
        # TODO deal with all other cases; assuming center
        # eagle supports: bottom-left | bottom-center | bottom-right | center-left | center | center-right | top-left | top-center | top-right
        x = float(text['x']) + len(s)*size/2
        y = float(text['y']) + size/2
      res['value'] = s
      if layer == 25 and s.upper() == '>NAME':
        res['value'] = 'NAME'
      elif layer == 27 and s.upper() == '>VALUE':
        res['value'] = 'VALUE'
      if x != 0: res['x'] = x
      if y != 0: res['y'] = y
      if text.has_attr('size'):
        res['dy'] = text['size']
      return res

    def smd(smd):
      res = {}
      res['type'] = 'smd'
      res['shape'] = 'rect'
      res['name'] = clean_name(smd['name'])
      res['dx'] = float(smd['dx'])
      res['dy'] = float(smd['dy'])
      res['x'] = float(smd['x'])
      res['y'] = float(smd['y'])
      if smd.has_attr('rot'):
        res['rot'] = int(smd['rot'][1:])
      if smd.has_attr('roundness'):
        if smd['roundness'] != '0':
          res['ro'] = smd['roundness']
      return res

    def rect(rect):
      res = {}
      res['type'] = layer_number_to_type(int(rect['layer']))
      res['shape'] = 'rect'
      x1 = float(rect['x1'])
      y1 = float(rect['y1'])
      x2 = float(rect['x2'])
      y2 = float(rect['y2'])
      res['x'] = (x1+x2)/2
      res['y'] = (y1+y2)/2
      res['dx'] = abs(x1-x2)
      res['dy'] = abs(y1-y2)
      if rect.has_attr('rot'):
        res['rot'] = int(rect['rot'][1:])
      return res

    def wire(wire):
      res = {}
      res['type'] = layer_number_to_type(int(wire['layer']))
      res['shape'] = 'vertex'
      res['x1'] = float(wire['x1'])
      res['y1'] = float(wire['y1'])
      res['x2'] = float(wire['x2'])
      res['y2'] = float(wire['y2'])
      res['w'] = float(wire['width'])
      # assymetry here: an Arc exported will come back as
      # a curved vertex
      if wire.has_attr('curve'):
        res['curve'] = float(wire['curve'])
      return res

    def circle(circle):
      res = {}
      res['type'] = layer_number_to_type(int(circle['layer']))
      res['shape'] = 'circle'
      w = float(circle['width'])
      r = float(circle['radius'])
      res['x'] = float(circle['x'])
      res['y'] = float(circle['y'])
      if w == r:
        res['shape'] = 'disc'
        res['r'] = r * 2
      else:
        res['w'] = w
        res['r'] = r
      return res

    def description(desc):
      meta['desc'] = desc.string
      return None

    def pad(pad):
      res = {}
      res['type'] = 'pad'
      res['name'] = clean_name(pad['name'])
      res['x'] = float(pad['x'])
      res['y'] = float(pad['y'])
      drill = float(pad['drill'])
      res['drill'] = drill
      if pad.has_attr('diameter'):
        dia = float(pad['diameter'])
      else:
        dia = res['drill'] * 1.5
      if pad.has_attr('rot'):
        res['rot'] = int(pad['rot'][1:])
      shape = 'round'
      if pad.has_attr('shape'):
        shape = pad['shape']
      if shape == 'round':
        res['shape'] = 'disc'
        res['r'] = 0.0
        #if dia/2 > drill:
        res['r'] = dia/2
      elif shape == 'square':
        res['shape'] = 'rect'
        res['dx'] = dia
        res['dy'] = dia
      elif shape == 'long':
        res['shape'] = 'rect'
        res['ro'] = 100
        res['dx'] = 2*dia
        res['dy'] = dia
      elif shape == 'offset':
        res['shape'] = 'rect'
        res['ro'] = 100
        res['dx'] = 2*dia
        res['dy'] = dia
        res['drill_dx'] = -dia/2
      elif shape == 'octagon':
        res['shape'] = 'octagon'
        res['r'] = dia/2
      return res
     
    def hole(x):
      res = {'type':'hole', 'shape':'hole'}
      res['drill'] = float(x('drill'))
      res['x'] = float(x('x'))
      res['y'] = float(x('y'))
      return res

    def polygon(x):
      res = { 'shape':'polygon' }
      res['w'] = float(x['width'])
      res['type'] = layer_number_to_type(int(x['layer']))
      res['v'] = []
      for e in x.find_all('vertex'):
        vert = { 'shape':'vertex' }
        vert['x1'] = float(e['x'])
        vert['y1'] = float(e['y'])
        if e.has_attr('curve'):
          vert['curve'] = float(e['curve'])
        res['v'].append(vert)
      l = len(res['v'])
      for i in range(0, l):
        res['v'][i]['x2'] = res['v'][i-l+1]['x1']
        res['v'][i]['y2'] = res['v'][i-l+1]['y1']
      return res

    def unknown(x):
      res = {}
      res['type'] = 'unknown'
      res['value'] = str(x)
      res['shape'] = 'unknown'
      return res

    for x in package.contents:
      if type(x) == Tag:
        result = {
          'circle': circle,
          'description': description,
          'pad': pad,
          'smd': smd,
          'text': text,
          'wire': wire,
          'rectangle': rect,
          'polygon': polygon,
          'hole': hole,
          }.get(x.name, unknown)(x)
        if result != None: l.append(result)
    return clean_floats(l)


########NEW FILE########
__FILENAME__ = kicad
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import glob, math, os.path, uuid

import sexpdata
from sexpdata import Symbol

from mutil.mutil import *
from inter import inter

def S(v):
  return Symbol(str(v))

def type_to_layer_name(layer):
  return {
    'smd': 'F.Cu', # these two are normally
    'pad': 'F.Cu', # not used like this
    'silk': 'F.SilkS',
    'name': 'F.SilkS',
    'value': 'Dwgs.User',
    'stop': 'F.Mask',
    'glue': 'F.Adhes',
    'docu': 'Dwgs.User',
    'hole': 'Edge.Cuts',
    }.get(layer)

def layer_name_to_type(name):
   return {
    'F.SilkS': 'silk',
    'Dwgs.User': 'docu',
    'F.Mask': 'stop',
    'F.Adhes': 'glue',
    'Edge.Cuts': 'hole',
   }.get(name)


def detect(fn):
  if os.path.isdir(fn) and '.pretty' in fn:
    return "3"
  try:
    l = sexpdata.load(open(fn, 'r'))
    if (l[0] == S('module')): return "3"
    return None
  except IOError:
    # allow new .kicad_mod files!
    if '.kicad_mod' in fn: return "3"
    return None
  except:
    return None

def _convert_sexp_symbol(d):
  if ("value" in dir(d)):
    return d.value()
  else:
    return d

def _convert_sexp_symbol_to_string(d):
  return str(_convert_sexp_symbol(d))

class Export:

  def __init__(self, fn):
    self.fn = fn

  def export_footprint(self, interim):
    meta = inter.get_meta(interim)
    name = eget(meta, 'name', 'Name not found')
    idx = eget(meta, 'id', 'Id not found')
    descr = oget(meta, 'desc', '')
    parent_idx = oget(meta, 'parent', None)
    l = [
      S('module'),
      name,
      [S('layer'), S('F.Cu')],
      [S('descr'), descr],
    ]
    
    def pad(shape, smd=False):
      l = [S('pad'), S(shape['name'])]
      if smd:
        l.append(S('smd'))
      else:
        l.append(S('thru_hole'))
      shape2 = 'disc' # disc is the default
      if 'shape' in shape:
        shape2 = shape['shape']
      r = fget(shape, 'r')
      if shape2 == 'disc':
        l.append(S('circle'))
        l.append([S('size'), r, r])
      elif shape2 == 'rect':
        ro = iget(shape, 'ro')
        if ro == 0:
          l.append(S('rect'))
        else:
          l.append(S('oval'))
        l.append([S('size'), fget(shape, 'dx'), fget(shape, 'dy')])
      else:
        raise Exception("%s shaped pad not supported in kicad" % (shape2))
      l.append([S('at'), fget(shape, 'x'), -fget(shape, 'y'), iget(shape, 'rot')])
      if smd:
        l.append([S('layers'), S('F.Cu'), S('F.Paste'), S('F.Mask')])
      else:
        l.append([S('layers'), S('*.Cu'), S('*.Mask')])
      if not smd:
        l2 = [S('drill'), fget(shape, 'drill')]
        if 'drill_dx' in shape or 'drill_dy' in shape:
          l2.append([S('offset'), fget(shape, 'drill_dx'), fget(shape, 'drill_dy')])
        l.append(l2)
      return l
    
    #(fp_line (start -2.54 -1.27) (end 2.54 -1.27) (layer F.SilkS) (width 0.381))
    # (fp_arc (start 7.62 0) (end 7.62 -2.54) (angle 90) (layer F.SilkS) (width 0.15))
    def vertex(shape, layer):
      if not 'curve' in shape or shape['curve'] == 0.0:
        l = [S('fp_line')] 
        l.append([S('start'), fget(shape, 'x1'), -fget(shape, 'y1')])
        l.append([S('end'), fget(shape, 'x2'), -fget(shape, 'y2')])
        l.append([S('layer'), S(layer)])
        l.append([S('width'), fget(shape, 'w')])
      else:
        l = [S('fp_arc')] 
        # start == center point
        # end == start point of arc
        # angle == angled part in that direction
        x1 = fget(shape, 'x1')
        y1 = fget(shape, 'y1')
        x2 = fget(shape, 'x2')
        y2 = fget(shape, 'y2')
        curve =  fget(shape, 'curve')
        angle = curve*math.pi/180.0
        ((x0, y0), r, a1, a2) = calc_center_r_a1_a2((x1,y1),(x2,y2),angle)
        l.append([S('start'), fc(x0), fc(-y0)])
        l.append([S('end'), fc(x1), fc(-y1)])
        # also invert angle because of y inversion
        l.append([S('angle'), -(a2-a1)])
        l.append([S('layer'), S(layer)])
        l.append([S('width'), fget(shape, 'w')])
      return l

    # (fp_circle (center 5.08 0) (end 6.35 -1.27) (layer F.SilkS) (width 0.15))
    def circle(shape, layer):
      x = fget(shape, 'x')
      y = -fget(shape, 'y')
      r = fget(shape, 'r')
      if not 'a1' in shape and not 'a2' in shape:
        l = [S('fp_circle')] 
        l.append([S('center'),fc(x),fc(y)])
        l.append([S('end'), fc(x+(r/math.sqrt(2))), fc(y+(r/math.sqrt(2)))])
        l.append([S('layer'), S(layer)])
        l.append([S('width'), fget(shape, 'w')])
      else:
        l = [S('fp_arc')] 
        l.append([S('start'),fc(x),fc(y)])
        # start == center point
        # end == start point of arc
        # angle == angled part in that direction
        a1 = fget(shape, 'a1')
        a2 = fget(shape, 'a2')
        a1rad = a1 * math.pi/180.0
        ex = x + r*math.cos(a1rad)
        ey = y + r*math.sin(a1rad)
        l.append([S('end'), fc(ex), fc(-ey)])
        l.append([S('angle'), -(a2-a1)])
      l.append([S('layer'), S(layer)])
      l.append([S('width'), fget(shape, 'w')])
      return l

    # a disc is just a circle with a clever radius and width
    def disc(shape, layer):
      l = [S('fp_circle')] 
      x = fget(shape, 'x')
      y = -fget(shape, 'y')
      l.append([S('center'), fc(x), fc(y)])
      r = fget(shape, 'r')
      rad = r/2
      l.append([S('end'), x+(rad/math.sqrt(2)), y+(rad/math.sqrt(2))])
      l.append([S('layer'), S(layer)])
      l.append([S('width'), rad])
      return l

    def hole(shape):
      layer = type_to_layer_name(shape['type']) # aka 'hole'
      shape['r'] = shape['drill'] / 2
      return circle(shape, layer)

    # (fp_poly (pts (xy 6.7818 1.6002) (xy 6.6294 1.6002) (xy 6.6294 1.4478) (xy 6.7818 1.4478) (xy 6.7818 1.6002)) (layer F.Cu) (width 0.00254))
    # kicad doesn't do arced vertex in polygon :(
    def polygon(shape, layer):
      l = [S('fp_poly')]
      lxy = [S('pts')]
      for v in shape['v']:
        xy = [S('xy'), fc(v['x1']), fc(-v['y1'])]
        lxy.append(xy)
      xy = [S('xy'), fc(shape['v'][0]['x1']), fc(-shape['v'][0]['y1'])]
      lxy.append(xy)
      l.append(lxy)
      l.append([S('layer'), S(layer)])
      l.append([S('width'), shape['w']])
      return l

    def rect(shape, layer):
      l = [S('fp_poly')]
      x = fget(shape, 'x')
      y = - fget(shape, 'y')
      dx = fget(shape, 'dx')
      dy = fget(shape, 'dy')
      lxy = [S('pts')]
      def add(x1, y1):
        lxy.append([S('xy'), fc(x1), fc(y1)])
      add(x - dx/2, y - dy/2)
      add(x - dx/2, y + dy/2)
      add(x + dx/2, y + dy/2)
      add(x + dx/2, y - dy/2)
      add(x - dx/2, y - dy/2)
      l.append(lxy)
      l.append([S('layer'), S(layer)])
      l.append([S('width'), 0])
      return l

    # (fp_text reference MYCONN3 (at 0 -2.54) (layer F.SilkS)
    #   (effects (font (size 1.00076 1.00076) (thickness 0.25146)))
    # )
    # (fp_text value SMD (at 0 2.54) (layer F.SilkS) hide
    #   (effects (font (size 1.00076 1.00076) (thickness 0.25146)))
    # )
    def label(shape, layer):
      s = shape['value'].upper()
      t = 'user'
      if s == 'VALUE': t = 'value'
      if s == 'NAME': t = 'reference'
      l = [S('fp_text'), S(t), S(shape['value'])]
      if (('rot' in shape) and (fget(shape, 'rot') != 0.0)):
        l.append([S('at'), fget(shape, 'x'), fc(-fget(shape, 'y')), fget(shape, 'rot')])
      else:
        l.append([S('at'), fget(shape, 'x'), fc(-fget(shape, 'y'))])
      l.append([S('layer'), S(layer)])
      if s == 'VALUE':
        l.append(S('hide'))
      dy = fget(shape, 'dy', 1/1.6)
      th = fget(shape, 'w', 0.1)
      l.append([S('effects'), 
                [S('font'), [S('size'), dy, dy], [S('thickness'), th]]])
      return l

    def silk(shape):
      if not 'shape' in shape: return None
      layer = type_to_layer_name(shape['type'])
      s = shape['shape']
      if s == 'line': return vertex(shape, layer)
      if s == 'vertex': return vertex(shape, layer)
      elif s == 'circle': return circle(shape, layer)
      elif s == 'disc': return disc(shape, layer)
      elif s == 'label': return label(shape, layer)
      elif s == 'rect': return rect(shape, layer)
      elif s == 'polygon': return polygon(shape, layer)

    def unknown(shape):
      return None

    for shape in interim:
      if 'type' in shape:
        l2 = {
          'pad': pad,
          'silk': silk,
          'docu': silk,
          'keepout': unknown,
          'stop': silk,
          'glue': silk,
          'restrict': unknown,
          'vrestrict': unknown,
          'smd': lambda s: pad(s, smd=True),
          'hole': hole,
          }.get(shape['type'], unknown)(shape)
        if l2 != None:
         l.append(l2)
    self.data = l
    self.name = name
    return name

  def save(self):
    if os.path.isdir(self.fn) and '.pretty' in self.fn:
      name = self.name.replace(' ', '_')
      fn = os.path.join(self.fn, name + '.kicad_mod')
    else:
      fn = self.fn
    with open(fn, 'w+') as f:
      sexpdata.dump(self.data, f)

  def get_string(self):
    return sexpdata.dumps(self.data)

class Import:

  def __init__(self, fn):
    self.fn = fn
    if os.path.isdir(self.fn) and '.pretty' in self.fn:
      self.files = glob.glob(self.fn + '/*.kicad_mod')
    else:
      self.files = [self.fn]

  def list_names(self):
    l = []
    for f in self.files:
      s = sexpdata.load(open(f, 'r'))
      name = _convert_sexp_symbol_to_string(s[1])
      fp = self._import_footprint(s)
      desc = None
      for x in fp:
         if x['type'] == 'meta':
           if 'desc' in x:
             desc = x['desc']
             break
      l.append((name, desc))
    return l

  def list(self):
    for f in self.files:
      l = sexpdata.load(open(f, 'r'))
      print _convert_sexp_symbol_to_string(l[1])

  def import_footprint(self, name):
    s = None
    for f in self.files:
      s = sexpdata.load(open(f, 'r'))
      if _convert_sexp_symbol_to_string(s[1]) == name:
        break
    if s is None:
      raise Exception("Footprint %s not found" % (name))
    return self._import_footprint(s)

  def _import_footprint(self, s):
    meta = {}
    meta['type'] = 'meta'
    meta['name'] = _convert_sexp_symbol_to_string(s[1])
    meta['id'] = uuid.uuid4().hex
    meta['desc'] = None
    l = [meta]

    def get_sub(x, name):
      #print "X: "
      #print x
      for e in x:
        if ("__len__" not in dir(e)):
          continue # Ignore objects without length
        if (len(e) == 0):
          continue # Ignore empty
        if _convert_sexp_symbol_to_string(e[0]) == name:
          return list(map(_convert_sexp_symbol, e[1:]))
      return None

    def has_sub(x, name):
      for e in x:
        if ("__len__" not in dir(e)):
          continue # Ignore objects without length
        if (len(e) == 0):
          continue # Ignore empty
        if _convert_sexp_symbol_to_string(e[0]) == name:
          return True
      return False
      
    def get_single_element_sub(x, name, default=None):
      sub = get_sub(x, name)
      if (sub != None):
        if (len(sub) != 1):
          raise Exception("Unexpected multi-element '%s' sub: %s" % (name, str(sub)))
        return sub[0]
      return default

    def get_list_sub(x, name, default=None):
      sub = get_sub(x, name)
      if (sub != None):
        if len(sub) < 1:
          return []
        else:
          return sub
      
    def get_layer_sub(x, default=None):
      layer = get_single_element_sub(x, 'layer')
      if (layer != None):
        return layer_name_to_type(layer)
      return default
    
    def get_layers_sub(x, default=None):
      layers = get_sub(x, 'layers')
      if (layers != None):
        return list(map(layer_name_to_type, layers))
      return default

    def get_at_sub(x):
      sub = get_sub(x, 'at')
      if (sub is None):
        raise Exception("Expected 'at' element in %s" % (str(x)))
      if (len(sub) == 2):
        [x1, y1] = sub
        rot = 0
      elif (len(sub) == 3):
        [x1, y1, rot] = sub
      else:
        raise Exception("Invalid 'at' element in %s" % (str(x)))      
      return (x1, y1, rot)

    def descr(x):
      meta['desc'] = x[1]

    # (pad 1 smd rect (size 1.1 1.0) (at -0.85 -0.0 0) (layers F.Cu F.Paste F.Mask))
    # (pad 5 thru_hole circle (size 0.75 0.75) (at 1.79 3.155 0) (layers *.Cu *.Mask) (drill 1.0))
    def pad(x):
      shape = {'name': _convert_sexp_symbol_to_string(x[1]) }
      smd = (_convert_sexp_symbol_to_string(x[2]) == 'smd')
      if smd:
        shape['type'] = 'smd'
      else:
        shape['type'] = 'pad'
      s = _convert_sexp_symbol_to_string(x[3])
      [x1, y1, rot] = get_at_sub(x)
      shape['x'] = x1
      shape['y'] = -y1
      shape['rot'] = rot
      [dx, dy] = get_sub(x, 'size')
      if s == 'circle':
        shape['shape'] = 'disc'
        shape['r'] = dx/2
      elif s == 'rect':
        shape['shape'] = 'rect'
        shape['dx'] = dx
        shape['dy'] = dy
      elif s == 'oval':
        shape['shape'] = 'rect'
        shape['dx'] = dx
        shape['dy'] = dy
        shape['ro'] = 100
      else:
        raise Exception("Pad with unknown shape %s" % (str(s)))
      if not smd:
        drill = get_sub(x, 'drill')
        shape['drill'] = drill[0]
        if has_sub(drill, 'offset'):
          [drill_dx, drill_dy] = get_sub(drill, 'offset')
          shape['drill_dx'] = drill_dx
          shape['drill_dy'] = -drill_dy
      return shape

    #(fp_line (start -2.54 -1.27) (end 2.54 -1.27) (layer F.SilkS) (width 0.381))
    def fp_line(x):
      [x1, y1] = get_sub(x, 'start')
      [x2, y2] = get_sub(x, 'end')
      layer = get_layer_sub(x, 'silk')
      width = get_single_element_sub(x, 'width')
      shape = { 
        'shape': 'vertex',
        'x1': x1, 'y1': -y1, 
        'x2': x2, 'y2': -y2, 
        'type': layer, 'w': width
      }
      return shape

    # (fp_circle (center 5.08 0) (end 6.35 -1.27) (layer F.SilkS) (width 0.15))
    def fp_circle(x):
      shape = { 'shape': 'circle' }
      shape['type'] = get_layer_sub(x, 'silk')
      [x1, y1] = get_sub(x, 'center')
      shape['x'] = x1
      shape['y'] = -y1
      shape['w'] = get_single_element_sub(x, 'width')
      [ex, ey] = get_sub(x, 'end')
      dx = abs(x1 - ex)
      dy = abs(y1 - ey)
      if f_eq(dx, dy):
        shape['r'] = dx*math.sqrt(2)
        if f_eq(shape['w'], shape['r']):
          shape['type'] = 'disc'
          shape['r'] = shape['r'] * 2
          del shape['w']
        elif shape['type'] == 'hole':
          shape['shape'] = 'hole'
          shape['drill'] = shape['r'] * 2
          del shape['w']
          del shape['r']
      else:
        shape['rx'] = dx*math.sqrt(2)
        shape['ry'] = dy*math.sqrt(2)
      return shape

    # (fp_arc (start 7.62 0) (end 7.62 -2.54) (angle 90) (layer F.SilkS) (width 0.15))
    def fp_arc(x):
      # start is actually center point
      [xc, yc] = get_sub(x, 'start')
      yc = -yc
      # end is actually start point of arc
      [x1, y1] = get_sub(x, 'end')
      y1 = -y1
      [angle] = get_sub(x, 'angle')
      a = angle*math.pi/180.0
      (x2, y2) = calc_second_point((xc,yc),(x1,y1),a)
      width = get_single_element_sub(x, 'width')
      shape = { 'shape': 'vertex'}
      shape['type'] = get_layer_sub(x, 'silk')
      shape['curve'] = -angle
      shape['x1'] = x1
      shape['y1'] = y1
      shape['x2'] = x2
      shape['y2'] = y2
      width = get_single_element_sub(x, 'width')
      shape['w'] = width
      return shape

    # (fp_poly (pts (xy 6.7818 1.6002) (xy 6.6294 1.6002) (xy 6.6294 1.4478) (xy 6.7818 1.4478) (xy 6.7818 1.6002)) (layer F.Cu) (width 0.00254))
    def fp_poly(x):
      width = get_single_element_sub(x, 'width')
      shape = { 'shape': 'polygon'}
      shape['w'] = width
      shape['type'] = get_layer_sub(x, 'silk')
      shape['v'] = []
      for p in get_list_sub(x, 'pts')[0:-1]:
        v = { 'shape':'vertex' }
        v['x1'] = p[1]
        v['y1'] = -p[2]
        shape['v'].append(v)
      l = len(shape['v'])
      for i in range(0, l):
        shape['v'][i]['x2'] = shape['v'][i-l+1]['x1']
        shape['v'][i]['y2'] = shape['v'][i-l+1]['y1']
      return shape

    # (fp_text reference MYCONN3 (at 0 -2.54) (layer F.SilkS)
    #   (effects (font (size 1.00076 1.00076) (thickness 0.25146)))
    # )
    # (fp_text value SMD (at 0 2.54) (layer F.SilkS) hide
    #   (effects (font (size 1.00076 1.00076) (thickness 0.25146)))
    # )
    def fp_text(x):
      shape = { 'shape': 'label', 'type': 'silk', 'value': '' }
      shape['value'] = _convert_sexp_symbol_to_string(x[2])
      shape['type'] = get_layer_sub(x, 'silk')
      
      if (_convert_sexp_symbol_to_string(x[1]) == "reference"):
        shape['value'] = 'NAME' # Override "NAME" field text
      elif (_convert_sexp_symbol_to_string(x[1]) == "value"):
        shape['value'] = 'VALUE' # Override "VALUE" field text
      else:
        # Don't let 'user' fields have 'NAME' or 'VALUE' as text
        if ((shape['value'] == 'NAME') or (shape['value'] == 'VALUE')):
          shape['value'] = "_%s_" % (shape['value'])
      
      [x1, y1, rot] = get_at_sub(x)
      font = get_sub(get_sub(x, 'effects'), 'font')
      [dx, dy] = get_sub(font, 'size')
      w = get_sub(font, 'thickness')
      shape['x'] = x1
      shape['y'] = -y1
      shape['w'] = w
      shape['dy'] = dy
      # TODO: Add rotated text support
      shape['rot'] = rot
      return shape

    for x in s[3:]:
      #print "ELEMENT:"
      #print x
      res = {
        'descr': descr,
        'pad': pad,
        'fp_line': fp_line,
        'fp_circle': fp_circle,
        'fp_arc': fp_arc,
        'fp_text': fp_text,
        'fp_poly': fp_poly,
      }.get(_convert_sexp_symbol_to_string(x[0]), lambda a: None)(x)
      if res != None:
        l.append(res)

    return clean_floats(l)

    
    

########NEW FILE########
__FILENAME__ = kicad_old
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

# kicad old format info can be found in:
#
#  - file_formats.pdf
#  - pcbnew/legacy_plugin.cpp

import os.path
import shlex
import uuid
import math
import time
import re

import mutil.mutil as mutil
eget = mutil.eget
fget = mutil.fget
oget = mutil.oget
fc = mutil.fc

from inter import inter

def detect(fn):
  if os.path.isdir(fn): return None
  try:
    with open(fn, 'r') as f:
      l = f.readlines()
      l0 = l[0]
      l2 = l0.split()
      if (l2[0] == 'PCBNEW-LibModule-V1'): 
        return "1" # imperial only although in practice there seem to be files that do metric anyway...?!
      elif (l2[0] == 'PCBNEW-LibModule-V2'):
        return "2" # support metric also
      return None
  except:
    return None

def num_to_type(i):
  i = int(i)
  return {
    17: 'glue',
    19: 'paste',
    21: 'silk',
    23: 'stop',
    24: 'docu', # ???
    25: 'docu', # ???
    28: 'hole', # actually, 'edge'
  }.get(i)

def type_to_num(t):
  return {
    'glue': 17,
    'paste': 19,
    'silk': 21,
    'stop': 23,
    'docu': 24,
    'hole': 28,
  }.get(t, 21)

def list_names(fn):
  l = []
  with open(fn, 'r') as f:
    lines = f.readlines()
    for line in lines:
      s = shlex.split(line)
      k = s[0].lower()
      if k == '$module':
        name = s[1]
        desc = None
      elif k == 'cd' and len(s) > 1:
        desc = s[1]
      elif k == '$endmodule':
        l.append((name, desc))
  return l

class Export:

  def __init__(self, fn):
    self.fn = fn

  def export_footprint(self, interim, timestamp = None):
    if timestamp is None:
      timestamp = time.time()
    meta = inter.get_meta(interim)
    name = eget(meta, 'name', 'Name not found')
    # make name kicad compatible
    name = re.sub(' ','_',name)
    self.name = name
    idx = eget(meta, 'id', 'Id not found')
    desc = oget(meta, 'desc', '')
    parent_idx = oget(meta, 'parent', None)
    d = []
    # generate kicad-old for individual footprint
    # use metric; convert to imperial in "save" if needed
    d.append("$MODULE %s" % (name))
    d.append("Po 0 0 0 15 %x 00000000 ~~" % timestamp)
    d.append("Li %s" % (name))
    d.append("Cd %s" % (desc.replace('\n',' '))) # ugly
    # assuming Kw is optional
    d.append("Sc 0")
    # d.append("AR ") assume AR is optional
    d.append("Op 0 0 0")
    # if no T0 or T1 are specified, kicad defaults to this:
    # right now I'm assuming this is optional
    # T0 0 0 1.524 1.524 0 0.15 N V 21 N ""
    # T1 0 0 1.524 1.524 0 0.15 N V 21 N ""

    def pad(shape, smd=False):
      l = ['$PAD']
      # Sh "<pad name>" shape Xsize Ysize Xdelta Ydelta Orientation
      # octagons are not supported by kicad
      if shape['shape'] == 'disc' or shape['shape'] == 'octagon':
        sh = 'C'
        dx = shape['r']*2
        dy = dx
      elif shape['shape'] == 'rect':
        dx = shape['dx']
        dy = shape['dy']
        sh = 'R'
        # any rect with roundness >= 50 is considered kicad 'oblong'
        if 'ro' in shape:
          if shape['ro'] >= 50:
            sh = 'O'
      rot = fget(shape, 'rot')*10
      l.append("Sh \"%s\" %s %s %s %s %s %s" 
               % (shape['name'], sh, dx, dy, 0, 0, rot))
      # Dr <Pad drill> Xoffset Yoffset (round hole)
      if not smd:
        l.append("Dr %s %s %s" % (fget(shape, 'drill'), 
          fget(shape, 'drill_dx'), fc(-fget(shape, 'drill_dy'))))
      # Po <x> <y>
      l.append("Po %s %s" % (fget(shape,'x'), fc(-fget(shape,'y'))))
      # At <Pad type> N <layer mask>
      t = 'STD'
      layer_mask = '00E0FFFF'
      if smd:
        t = 'SMD'
        layer_mask = '00888000'
      l.append("At %s N %s" % (t, layer_mask))
      l.append('Ne 0 ""')
      l.append("$ENDPAD")
      return l

    # DS Xstart Ystart Xend Yend Width Layer
    # DS 6000 1500 6000 -1500 120 21
    # DA Xcentre Ycentre Xstart_point Ystart_point angle width layer
    def vertex(shape, layer):
      l = []
      x1 = fget(shape, 'x1')
      y1 = fget(shape, 'y1')
      x2 = fget(shape, 'x2')
      y2 = fget(shape, 'y2')
      w = fget(shape, 'w')
      if not 'curve' in shape or shape['curve'] == 0.0:
        line = "DS %s %s %s %s %s %s" % (x1, fc(-y1), x2, fc(-y2), w, layer)
        l.append(line)
      else:
        curve =  fget(shape, 'curve')
        angle = curve*math.pi/180.0
        ((x0, y0), r, a1, a2) = mutil.calc_center_r_a1_a2((x1,y1),(x2,y2),angle)
        arc = "DA %f %f %f %f %s %s %s" % (x0, fc(-y0), x1, fc(-y1), int(round((-10.0)*(a2-a1))), w, layer)
        l.append(arc)
      return l

    # DC Xcentre Ycentre Xpoint Ypoint Width Layer
    def circle(shape, layer):
      l = []
      x = fget(shape, 'x')
      y = fget(shape, 'y')
      r = fget(shape, 'r')
      w = fget(shape, 'w')
      if not 'a1' in shape and not 'a2' in shape:
        circle = "DC %s %s %s %s %s %s" % (x, fc(-y), fc(x+(r/math.sqrt(2))), fc(-y+(r/math.sqrt(2))), w, layer)
        l.append(circle)
      else:
        # start == center point
        # end == start point of arc
        # angle == angled part in that direction
        a1 = fget(shape, 'a1')
        a2 = fget(shape, 'a2')
        a1rad = a1 * math.pi/180.0
        ex = x + r*math.cos(a1rad)
        ey = y + r*math.sin(a1rad)
        arc = "DA %f %f %f %f %s %s %s" % (x, fc(-y), ex, fc(-ey), int(round((-10)*(a2-a1))), w, layer)
        l.append(arc)
      return l
 
    def disc(shape, layer):
      l = []
      x = fget(shape, 'x')
      y = -fget(shape, 'y')
      r = fget(shape, 'r')
      rad = r/2
      ex = x+(rad/math.sqrt(2))
      ey = y+(rad/math.sqrt(2))
      circle = "DC %s %s %s %s %s %s" % (x, fc(y), fc(ex), fc(ey), rad, layer)
      l.append(circle)
      return l

    def hole(shape):
      layer = type_to_num(shape['type'])
      shape['r'] = shape['drill'] / 2
      return circle(shape, layer)

    # T0 -79 -3307 600 600 0 120 N V 21 N "XT"
    def label(shape, layer):
      s = shape['value'].upper()
      t = 'T2'
      visible = 'V'
      if s == 'VALUE': 
        t = 'T1'
        visible = 'I'
      if s == 'NAME': 
        t = 'T0'
      dy = fget(shape, 'dy', 1/1.6)
      w = fget(shape, 'w', 0.1)
      x = fget(shape, 'x')
      y = fc(-fget(shape, 'y'))
      # T0 -7 -3 60 60 0 10 N V 21 N "XT"
      line = "%s %s %s %s %s 0 %s N %s %s N \"%s\"" % (t, x, y, dy, dy, w, visible, layer, shape['value'])
      return [line]

    def rect(shape, layer):
      l = []
      w = fget(shape,'w')
      rot = abs(fget(shape, 'rot'))
      l.append("DP 0 0 0 0 %s %s %s" % (5, w, layer))
      x = fget(shape, 'x')
      y = -fget(shape, 'y')
      dx = fget(shape, 'dx')
      dy = fget(shape, 'dy')
      if rot == 90 or rot == 270:
        (dx,dy) = (dy,dx)
      def add(x1, y1):
        l.append("Dl %f %f" % (fc(x1), fc(y1)))
      add(x - dx/2, y - dy/2)
      add(x - dx/2, y + dy/2)
      add(x + dx/2, y + dy/2)
      add(x + dx/2, y - dy/2)
      add(x - dx/2, y - dy/2)
      return l
 
    # DP 0 0 0 0 corners_count width layer
    # DP 0 0 0 0 5 0.1 24
    # Dl corner_posx corner_posy
    # Dl 0 -1
    def polygon(shape, layer):
      l = []
      n = len(shape['v'])
      w = shape['w']
      l.append("DP 0 0 0 0 %s %s %s" % (n + 1, w, layer))
      for v in shape['v']:
        l.append("Dl %g %g" % (fc(v['x1']), fc(-v['y1'])))
      l.append("Dl %g %g" % (fc(shape['v'][0]['x1']), fc(-shape['v'][0]['y1'])))
      return l

    def silk(shape):
      if not 'shape' in shape: return None
      layer = type_to_num(shape['type'])
      s = shape['shape']
      if s == 'line': return vertex(shape, layer)
      if s == 'vertex': return vertex(shape, layer)
      elif s == 'circle': return circle(shape, layer)
      elif s == 'disc': return disc(shape, layer)
      elif s == 'label': return label(shape, layer)
      elif s == 'rect': return rect(shape, layer)
      elif s == 'polygon': return polygon(shape, layer) 

    def unknown(shape):
      return None

    for shape in interim:
      if 'type' in shape:
        l = {
          'pad': pad,
          'silk': silk,
          'docu': silk,
          'keepout': unknown,
          'stop': silk,
          'glue': silk,
          'restrict': unknown,
          'vrestrict': unknown,
          'smd': lambda s: pad(s, smd=True),
          'hole': hole,
          }.get(shape['type'], unknown)(shape)
        if l != None:
         d += l
      
    d.append("$EndMODULE %s" % (name))
    self.data = d
    return name

  def get_string(self):
    s = '\n'.join(self.data)
    return s

  def _make_new_file(self):
    empty = """PCBNEW-LibModule-V1  Sat 22 Jun 2013 04:47:58 PM CEST
# encoding utf-8
Units mm
$INDEX
#$EndINDEX
$EndLIBRARY"""
    with open(self.fn, 'w+') as f:
      f.write(empty)

  def save(self):
    if os.path.isdir(self.fn):
      raise Exception("Can't save to directory")
    if not os.path.exists(self.fn):
      self._make_new_file()
    
    names = [x for (x,y) in list_names(self.fn)]
    overwrite = self.name in names
    
    with open(self.fn, 'r') as f:
      l = f.readlines()
   
    l2 = []
    n = len(l)
    pos = 0
    while pos < n:
      line = l[pos].strip()
      if not overwrite:
        if line.lower() == "$endindex":
          l2.append(self.name)
        elif line.lower() == "$endlibrary":
          # add new module definition just before endlibrary
          l2 += self.data
        l2.append(line)
        pos += 1
      else:
        s = shlex.split(line)
        if s[0].lower() == "$module" and s[1] == self.name:
          # add new module definition
          l2 += self.data
          # skip old module definition
          while s[0].lower() != "$endmodule":
            pos += 1
            line = l[pos].strip()
            s = shlex.split(line)
        else:
          l2.append(line)
          pos += 1

    with open(self.fn, 'w+') as f:
      f.write("\n".join(l2))
      
    
class Import:

  def __init__(self, fn):
    self.fn = fn

  def import_module(self, name, lines, metric):
    meta = {}
    meta['type'] = 'meta'
    meta['name'] = name
    meta['id'] = uuid.uuid4().hex
    meta['desc'] = None
    l = [meta]

    def cd(s, d): 
      if meta['desc'] == None:
        meta['desc'] = d
      else:
        meta['desc'] = meta['desc'] + "\n" + d
      return None

    def label(s, labeltype='user'):
      shape = { 'shape': 'label', 'type': 'silk' }
      shape['value'] = s[11]
      if (labeltype == 'value'):
        shape['value'] = 'VALUE'
      if (labeltype == 'reference'):
        shape['value'] = 'NAME'
      shape['x'] = float(s[1])
      shape['y'] = -float(s[2])
      shape['dy'] = float(s[3])
      shape['w'] = float(s[6])
      return shape

    def line(s):
      shape = { 'shape': 'line' }
      shape['x1'] = float(s[1])
      shape['y1'] = -float(s[2])
      shape['x2'] = float(s[3])
      shape['y2'] = -float(s[4])
      shape['w'] = float(s[5])
      shape['type'] = num_to_type(s[6])
      return shape

    # DC Xcentre Ycentre Xpoint Ypoint Width Layer
    def circle(s):
      shape = { 'shape': 'circle' }
      x = float(s[1])
      y = -float(s[2])
      shape['x'] = x
      shape['y'] = y
      ex = float(s[3])
      ey = float(s[4])
      shape['w'] = float(s[5])
      dx = abs(x - ex)
      dy = abs(y - ey)
      shape['r'] = math.sqrt(dx*dx + dy*dy)
      if mutil.f_eq(shape['w'], shape['r']):
        shape['shape'] = 'disc'
        shape['r'] = shape['r'] * 2
        del shape['w']
      shape['type'] = num_to_type(s[6])
      if shape['type'] == 'hole':
        shape['drill'] = shape['r'] * 2
        shape['shape'] = 'hole'
        del shape['w']
        del shape['r']
      return shape

    # DA Xcentre Ycentre Xstart_point Ystart_point angle width layer
    def arc(s):
      shape = { 'shape': 'vertex' }
      xc = float(s[1])
      yc = -float(s[2])
      x1 = float(s[3])
      y1 = -float(s[4])
      angle = float(s[5])/10
      a = angle*math.pi/180.0
      (x2, y2) = mutil.calc_second_point((xc,yc),(x1,y1),a)
      shape['w'] = float(s[6])
      shape['type'] = num_to_type(s[7])
      shape['curve'] = -angle
      shape['x1'] = x1
      shape['y1'] = y1
      shape['x2'] = x2
      shape['y2'] = y2
      return shape

    # DP 0 0 0 0 corners_count width layer
    # Dl corner_posx corner_posy
    def import_polygon(lines, k):
      shape = { 'shape': 'polygon'}
      s = shlex.split(lines[k])
      count = int(s[5])
      shape['w'] = float(s[6])
      shape['type'] = num_to_type(s[7])
      shape['v'] = []
      for j in range(k+1, k+count): # don't want last looping back
        s = shlex.split(lines[j])
        v = { 'shape':'vertex' }
        v['x1'] = float(s[1])
        v['y1'] = -float(s[2])
        shape['v'].append(v)
      l = len(shape['v'])
      for i in range(0, l):
        shape['v'][i]['x2'] = shape['v'][i-l+1]['x1']
        shape['v'][i]['y2'] = shape['v'][i-l+1]['y1']
      return (k+count+1, shape)

    def import_pad(lines, i):
      shape = { }
   
      def drill(s):
        # Dr <Pad drill> Xoffset Yoffset (round hole)
        if len(s) == 4:
          d = float(s[1])
          dx = float(s[2])
          dy = float(s[3])
          if d != 0.0:
            shape['drill'] = d
          if dx != 0.0:
            shape['drill_dx'] = dx
          if dy != 0.0:
            shape['drill_dy'] = dy
        # Dr <Pad drill.x> Xoffset Yoffset <Hole shape> <Pad drill.x> <Pad drill.y>
        else:
          print "oblong holes are currently not supported by madparts (converted to round)"
          d = float(s[1])
          dx = float(s[2])
          dy = float(s[3])
          if d != 0.0:
            shape['drill'] = d
          if dx != 0.0:
            shape['drill_dx'] = dx
          if dy != 0.0:
            shape['drill_dy'] = fc(-dy)

      # Sh <pad name> shape Xsize Ysize Xdelta Ydelta Orientation 
      def handle_shape(s):
        shape['name'] = s[1]
        dx = float(s[3])
        dy = float(s[4])
        # xdelta, ydelta not used?
        rot = int(s[7])/10
        if rot != 0:
          shape['rot'] = rot
        sh = s[2]
        if sh == 'C':
          shape['shape'] = 'disc'
          shape['r'] = dx/2
        elif sh == 'O':
          shape['shape'] = 'rect'
          shape['ro'] = 100
          shape['dx'] = dx
          shape['dy'] = dy
        # trapeze is converted to rect for now
        elif sh == 'R' or sh == 'T':
          shape['shape'] = 'rect'
          shape['dx'] = dx
          shape['dy'] = dy
   
      # At <Pad type> N <layer mask>
      def attributes(s):
        if s[1] == 'SMD':
          shape['type'] = 'smd'
        else:
          shape['type'] = 'pad'

      # Po <x> <y>
      def position(s):
        shape['x'] = float(s[1])
        shape['y'] = -float(s[2])

      while i < len(lines):
        s = shlex.split(lines[i])
        k = s[0].lower()
        if k == "$endpad":
          #print shape
          return (i+1, shape)
        else:
          {
            'sh': handle_shape,
            'dr': drill,
            'at': attributes,
            'po': position,
          }.get(k, lambda a: None)(s)
          i = i + 1
    
    i = 0
    while i < len(lines):
      s = shlex.split(lines[i])
      k = s[0].lower()
      if k == '$endmodule':
        break
      elif k == '$pad':
        (i, pad) = import_pad(lines, i)
        l.append(pad)
      elif k == 'dp':
        (i, poly) = import_polygon(lines, i)
        l.append(poly)
      else:
        res = {
          'cd': lambda a: cd(a, lines[i][3:]),
          't0': lambda a: label(a, 'reference'),
          't1': lambda a: label(a, 'value'),
          't2': lambda a: label(a, 'user'),
          'ds': line,
          'dc': circle,
          'da': arc,
        }.get(k, lambda a: None)(s)
        if res != None:
          l.append(res)
        i = i + 1
    if not metric:
      # convert to metric from tenths of mils
      for x in l:
        for k in x.keys():
          if type(x[k]) == type(3.14):
            x[k] = x[k] * 0.00254
    l = mutil.clean_floats(l)
    return l

  def import_footprint(self, name):
    metric = False
    with open(self.fn, 'r') as f:
      lines = f.readlines()
    for i in range(0, len(lines)):
      s = shlex.split(lines[i])
      if s[0] == 'Units' and s[1] == 'mm':
        metric = True
      if s[0] == '$MODULE' and s[1] == name:
        return self.import_module(name, lines[i+1:], metric)
    raise Exception("footprint not found %s" % (name))

  def list(self):
    with open(self.fn, 'r') as f:
      lines = f.readlines()
    for line in lines:
      s = shlex.split(line)
      if s[0] == '$MODULE':
        print s[1]

  def list_names(self):
    return list_names(self.fn)

########NEW FILE########
__FILENAME__ = madparts
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import os.path
import glob

import coffee.library

def detect(fn):
  if not os.path.isdir(fn): return None
  if len(glob.glob(fn + '/*.coffee')) > 0: return "1.0"
  return None

class Import:

  def __init__(self, fn):
    self.fn = fn


  def list(self):
    library = coffee.library.Library('library', self.fn)
    for meta in library.meta_list:
      print meta.id, meta.name

########NEW FILE########
__FILENAME__ = sexpdata
# [[[cog import cog; cog.outl('"""\n%s\n"""' % file('README.rst').read()) ]]]
"""
S-expression parser for Python
==============================

`sexpdata` is a simple S-expression parser/serializer.  It has
simple `load` and `dump` functions like `pickle`, `json` or `PyYAML`
module.

>>> from sexpdata import loads, dumps
>>> loads('("a" "b")')
['a', 'b']
>>> print(dumps(['a', 'b']))
("a" "b")


You can install `sexpdata` from PyPI_::

  pip install sexpdata


Links:

* `Documentation (at Read the Docs) <http://sexpdata.readthedocs.org/>`_
* `Repository (at GitHub) <https://github.com/tkf/sexpdata>`_
* `Issue tracker (at GitHub) <https://github.com/tkf/sexpdata/issues>`_
* `PyPI <http://pypi.python.org/pypi/sexpdata>`_
* `Travis CI <https://travis-ci.org/#!/tkf/sexpdata>`_


License
-------

`sexpdata` is licensed under the terms of the BSD 2-Clause License.
See the source code for more information.

"""
# [[[end]]]

# Copyright (c) 2012 Takafumi Arakaki
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.

# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

__version__ = '0.0.3'
__author__ = 'Takafumi Arakaki'
__license__ = 'BSD License'
__all__ = [
    # API functions:
    'load', 'loads', 'dump', 'dumps',
    # Utility functions:
    'car', 'cdr',
    # S-expression classes:
    'Symbol', 'String', 'Quoted',
]

import re
from string import whitespace
import functools

BRACKETS = {'(': ')', '[': ']'}


### Python 3 compatibility

try:
    unicode
    PY3 = False
except NameError:
    basestring = unicode = str  # Python 3
    PY3 = True


def uformat(s, *args, **kwds):
    """Alias of ``unicode(s).format(...)``."""
    return tounicode(s).format(*args, **kwds)


### Utility

def tounicode(string):
    """
    Decode `string` if it is not unicode.  Do nothing in Python 3.
    """
    if not isinstance(string, unicode):
        string = unicode(string, 'utf-8')
    return string


def return_as(converter):
    """
    Decorator to convert result of a function.

    It is just a function composition. The following two codes are
    equivalent.

    Using `@return_as`::

        @return_as(converter)
        def generator(args):
            ...

        result = generator(args)

    Manually do the same::

        def generator(args):
            ...

        result = converter(generator(args))

    Example:

    >>> @return_as(list)
    ... def f():
    ...     for i in range(3):
    ...         yield i
    ...
    >>> f()  # this gives a list, not an iterator
    [0, 1, 2]

    """
    def wrapper(generator):
        @functools.wraps(generator)
        def func(*args, **kwds):
            return converter(generator(*args, **kwds))
        return func
    return wrapper


### Interface

def load(filelike, **kwds):
    """
    Load object from S-expression stored in `filelike`.

    :arg  filelike: A text stream object.

    See :func:`loads` for valid keyword arguments.

    >>> import io
    >>> fp = io.StringIO()
    >>> sexp = [Symbol('a'), Symbol('b')]   # let's dump and load this object
    >>> dump(sexp, fp)
    >>> _ = fp.seek(0)
    >>> load(fp) == sexp
    True

    """
    return loads(filelike.read(), **kwds)


def loads(string, **kwds):
    """
    Load object from S-expression `string`.

    :arg        string: String containing an S-expression.
    :type          nil: str or None
    :keyword       nil: A symbol interpreted as an empty list.
                        Default is ``'nil'``.
    :type         true: str or None
    :keyword      true: A symbol interpreted as True.
                        Default is ``'t'``.
    :type        false: str or None
    :keyword     false: A symbol interpreted as False.
                        Default is ``None``.
    :type     line_comment: str
    :keyword  line_comment: Beginning of line comment.
                            Default is ``';'``.

    >>> loads("(a b)")
    [Symbol('a'), Symbol('b')]
    >>> loads("a")
    Symbol('a')
    >>> loads("(a 'b)")
    [Symbol('a'), Quoted(Symbol('b'))]
    >>> loads("(a '(b))")
    [Symbol('a'), Quoted([Symbol('b')])]
    >>> loads('''
    ... ;; This is a line comment.
    ... ("a" "b")  ; this is also a comment.
    ... ''')
    ['a', 'b']
    >>> loads('''
    ... # This is a line comment.
    ... ("a" "b")  # this is also a comment.
    ... ''', line_comment='#')
    ['a', 'b']

    ``nil`` is converted to an empty list by default.  You can use
    keyword argument `nil` to change what symbol must be interpreted
    as nil:

    >>> loads("nil")
    []
    >>> loads("null", nil='null')
    []
    >>> loads("nil", nil=None)
    Symbol('nil')

    ``t`` is converted to True by default.  You can use keyword
    argument `true` to change what symbol must be converted to True.:

    >>> loads("t")
    True
    >>> loads("#t", true='#t')
    True
    >>> loads("t", true=None)
    Symbol('t')

    No symbol is converted to False by default.  You can use keyword
    argument `false` to convert a symbol to False.

    >>> loads("#f")
    Symbol('#f')
    >>> loads("#f", false='#f')
    False
    >>> loads("nil", false='nil', nil=None)
    False

    """
    obj = parse(string, **kwds)
    assert len(obj) == 1  # FIXME: raise an appropriate error
    return obj[0]


def dump(obj, filelike, **kwds):
    """
    Write `obj` as an S-expression into given stream `filelike`.

    :arg       obj: A Python object.
    :arg  filelike: A text stream object.

    See :func:`dumps` for valid keyword arguments.

    >>> import io
    >>> fp = io.StringIO()
    >>> dump([Symbol('a'), Symbol('b')], fp)
    >>> print(fp.getvalue())
    (a b)

    """
    filelike.write(unicode(dumps(obj)))


def dumps(obj, **kwds):
    """
    Convert python object into an S-expression.

    :arg           obj: A Python object.
    :type       str_as: ``'symbol'`` or ``'string'``
    :keyword    str_as: How string should be interpreted.
                        Default is ``'string'``.
    :type     tuple_as: ``'list'`` or ``'array'``
    :keyword  tuple_as: How tuple should be interpreted.
                        Default is ``'list'``.
    :type      true_as: str
    :keyword   true_as: How True should be interpreted.
                        Default is ``'t'``
    :type     false_as: str
    :keyword  false_as: How False should be interpreted.
                        Default is ``'()'``
    :type      none_as: str
    :keyword   none_as: How None should be interpreted.
                        Default is ``'()'``

    Basic usage:

    >>> print(dumps(['a', 'b']))
    ("a" "b")
    >>> print(dumps(['a', 'b'], str_as='symbol'))
    (a b)
    >>> print(dumps(dict(a=1, b=2)))
    (:a 1 :b 2)
    >>> print(dumps([None, True, False, ()]))
    (() t () ())
    >>> print(dumps([None, True, False, ()],
    ...             none_as='null', true_as='#t', false_as='#f'))
    (null #t #f ())
    >>> print(dumps(('a', 'b')))
    ("a" "b")
    >>> print(dumps(('a', 'b'), tuple_as='array'))
    ["a" "b"]

    More verbose usage:

    >>> print(dumps([Symbol('a'), Symbol('b')]))
    (a b)
    >>> print(dumps(Symbol('a')))
    a
    >>> print(dumps([Symbol('a'), Quoted(Symbol('b'))]))
    (a 'b)
    >>> print(dumps([Symbol('a'), Quoted([Symbol('b')])]))
    (a '(b))

    """
    return tosexp(obj, **kwds)


def car(obj):
    """
    Alias of ``obj[0]``.

    >>> car(loads('(a . b)'))
    Symbol('a')
    >>> car(loads('(a b)'))
    Symbol('a')

    """
    return obj[0]


def cdr(obj):
    """
    `cdr`-like function.

    >>> cdr(loads('(a . b)'))
    Symbol('b')
    >>> cdr(loads('(a b)'))
    [Symbol('b')]
    >>> cdr(loads('(a . (b))'))
    [Symbol('b')]
    >>> cdr(loads('(a)'))
    []
    >>> cdr(loads('(a . nil)'))
    []

    """
    # This is very lazy implementation.  Probably the best way to do
    # it is to define `Cons` S-expression class.
    if len(obj) > 2:
        dot = obj[1]
        if isinstance(dot, Symbol) and dot.value() == '.':
            return obj[2]
    return obj[1:]


### Core

def tosexp(obj, str_as='string', tuple_as='list',
           true_as='t', false_as='()', none_as='()'):
    """
    Convert an object to an S-expression (`dumps` is just calling this).

    See this table for comparison of lispy languages, to support them
    as much as possible:
    `Lisp: Common Lisp, Scheme/Racket, Clojure, Emacs Lisp - Hyperpolyglot
    <http://hyperpolyglot.org/lisp>`_

    """
    _tosexp = lambda x: tosexp(
        x, str_as=str_as, tuple_as=tuple_as,
        true_as=true_as, false_as=false_as, none_as=none_as)
    if isinstance(obj, list):
        return Bracket(obj, '(').tosexp(_tosexp)
    elif isinstance(obj, tuple):
        if tuple_as == 'list':
            return Bracket(obj, '(').tosexp(_tosexp)
        elif tuple_as == 'array':
            return Bracket(obj, '[').tosexp(_tosexp)
        else:
            raise ValueError(uformat("tuple_as={0!r} is not valid", tuple_as))
    elif obj is True:  # must do this before ``isinstance(obj, int)``
        return true_as
    elif obj is False:
        return false_as
    elif obj is None:
        return none_as
    elif isinstance(obj, (int, float)):
        return str(obj)
    elif isinstance(obj, basestring):
        if str_as == 'symbol':
            return obj
        elif str_as == 'string':
            return String(obj).tosexp()
        else:
            raise ValueError(uformat("str_as={0!r} is not valid", str_as))
    elif isinstance(obj, dict):
        return _tosexp(dict_to_plist(obj))
    elif isinstance(obj, SExpBase):
        return obj.tosexp(_tosexp)
    else:
        raise TypeError(uformat(
            "Object of type '{0}' cannot be converted by `tosexp`. "
            "It's value is '{1!r}'", type(obj), obj))


@return_as(list)
def dict_to_plist(obj):
    for key in obj:
        yield Symbol(uformat(":{0}", key))
        yield obj[key]


class SExpBase(object):

    def __init__(self, val):
        self._val = val

    def __repr__(self):
        return uformat("{0}({1!r})", self.__class__.__name__, self._val)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._val == other._val
        else:
            return False

    def value(self):
        return self._val

    def tosexp(self, tosexp=tosexp):
        """
        Decode this object into an S-expression string.

        :arg tosexp: A function to be used when converting sub S-expression.

        """
        raise NotImplementedError

    @classmethod
    def quote(cls, string):
        for (s, q) in cls._lisp_quoted_specials:
            string = string.replace(s, q)
        return tounicode(string)

    @classmethod
    def unquote(cls, string):
        return cls._lisp_quoted_to_raw.get(string, string)


class Symbol(SExpBase):

    # modified for madparts: don't quote '.'
    _lisp_quoted_specials = [
        ('\\', '\\\\'),    # must come first to avoid doubly quoting "\"
        ("'", r"\'"), ("`", r"\`"), ('"', r'\"'),
        ('(', r'\('), (')', r'\)'), ('[', r'\['), (']', r'\]'),
        (' ', r'\ '), (',', r'\,'), ('?', r'\?'),
        (';', r'\;'), ('#', r'\#'),
    ]

    _lisp_quoted_to_raw = dict((q, r) for (r, q) in _lisp_quoted_specials)

    def tosexp(self, tosexp=None):
        return self.quote(self._val)


class String(SExpBase):

    _lisp_quoted_specials = [  # from Pymacs
        ('\\', '\\\\'),    # must come first to avoid doubly quoting "\"
        ('"', '\\"'), ('\b', '\\b'), ('\f', '\\f'),
        ('\n', '\\n'), ('\r', '\\r'), ('\t', '\\t')]

    _lisp_quoted_to_raw = dict((q, r) for (r, q) in _lisp_quoted_specials)

    def tosexp(self, tosexp=None):
        return uformat('"{0}"', self.quote(self._val))


class Quoted(SExpBase):

    def tosexp(self, tosexp=tosexp):
        return uformat("'{0}", tosexp(self._val))


class Bracket(SExpBase):

    def __init__(self, val, bra):
        assert bra in BRACKETS  # FIXME: raise an appropriate error
        super(Bracket, self).__init__(val)
        self._bra = bra

    def __repr__(self):
        return uformat("{0}({1!r}, {2!r})",
            self.__class__.__name__, self._val, self._bra)

    def tosexp(self, tosexp=tosexp):
        bra = self._bra
        ket = BRACKETS[self._bra]
        c = ' '.join(tosexp(v) for v in self._val)
        return uformat("{0}{1}{2}", bra, c, ket)


def bracket(val, bra):
    if bra == '(':
        return val
    else:
        return Bracket(val, bra)


class ExpectClosingBracket(Exception):

    def __init__(self, got, expect):
        super(ExpectClosingBracket, self).__init__(uformat(
            "Not enough closing brackets. "
            "Expected {0!r} to be the last letter in the sexp. "
            "Got: {1!r}", expect, got))


class ExpectNothing(Exception):

    def __init__(self, got):
        super(ExpectNothing, self).__init__(uformat(
            "Too many closing brackets. "
            "Expected no character left in the sexp. "
            "Got: {0!r}", got))


class Parser(object):

    closing_brackets = set(BRACKETS.values())
    atom_end = \
        set(BRACKETS) | set(closing_brackets) | set('"\'') | set(whitespace)
    atom_end_or_escape_re = re.compile("|".join(map(re.escape,
                                                    atom_end | set('\\'))))
    quote_or_escape_re = re.compile(r'"|\\')

    def __init__(self, string, string_to=None, nil='nil', true='t', false=None,
                 line_comment=';'):
        self.string = string
        self.nil = nil
        self.true = true
        self.false = false
        self.string_to = (lambda x: x) if string_to is None else string_to
        self.line_comment = line_comment

    def parse_str(self, i):
        string = self.string
        chars = []
        append = chars.append
        search = self.quote_or_escape_re.search

        assert string[i] == '"'  # never fail
        while True:
            i += 1
            match = search(string, i)
            end = match.start()
            append(string[i:end])
            c = match.group()
            if c == '"':
                i = end + 1
                break
            elif c == '\\':
                i = end + 1
                append(String.unquote(c + string[i]))
        else:
            raise ExpectClosingBracket('"', None)
        return (i, ''.join(chars))

    def parse_atom(self, i):
        string = self.string
        chars = []
        append = chars.append
        search = self.atom_end_or_escape_re.search
        atom_end = self.atom_end

        while True:
            match = search(string, i)
            if not match:
                append(string[i:])
                i = len(string)
                break
            end = match.start()
            append(string[i:end])
            c = match.group()
            if c in atom_end:
                i = end  # this is different from str
                break
            elif c == '\\':
                i = end + 1
                append(Symbol.unquote(c + string[i]))
            i += 1
        else:
            raise ExpectClosingBracket('"', None)
        return (i, self.atom(''.join(chars)))

    def atom(self, token):
        if token == self.nil:
            return []
        if token == self.true:
            return True
        if token == self.false:
            return False
        try:
            return int(token)
        except ValueError:
            try:
                return float(token)
            except ValueError:
                return Symbol(token)

    def parse_sexp(self, i):
        string = self.string
        len_string = len(self.string)
        sexp = []
        append = sexp.append
        while i < len_string:
            c = string[i]
            if c == '"':
                (i, subsexp) = self.parse_str(i)
                append(self.string_to(subsexp))
            elif c in whitespace:
                i += 1
                continue
            elif c in BRACKETS:
                close = BRACKETS[c]
                (i, subsexp) = self.parse_sexp(i + 1)
                append(bracket(subsexp, c))
                try:
                    nc = string[i]
                except IndexError:
                    nc = None
                if nc != close:
                    raise ExpectClosingBracket(nc, close)
                i += 1
            elif c in self.closing_brackets:
                break
            elif c == "'":
                (i, subsexp) = self.parse_sexp(i + 1)
                append(Quoted(subsexp[0]))
                sexp.extend(subsexp[1:])
            elif c == self.line_comment:
                i = string.find('\n', i) + 1
                if i <= 0:
                    i = len_string
                    break
            else:
                (i, subsexp) = self.parse_atom(i)
                append(subsexp)
        return (i, sexp)

    def parse(self):
        (i, sexp) = self.parse_sexp(0)
        if i < len(self.string):
            raise ExpectNothing(self.string[i:])
        return sexp


def parse(string, **kwds):
    """
    Parse s-expression.

    >>> parse("(a b)")
    [[Symbol('a'), Symbol('b')]]
    >>> parse("a")
    [Symbol('a')]
    >>> parse("(a 'b)")
    [[Symbol('a'), Quoted(Symbol('b'))]]
    >>> parse("(a '(b))")
    [[Symbol('a'), Quoted([Symbol('b')])]]

    """
    return Parser(string, **kwds).parse()

########NEW FILE########
__FILENAME__ = defaultsettings
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

# default values for settings

color_schemes = {}
    
color_schemes['default'] = {
  'background': (0.0, 0.0, 0.0, 1.0),
  'grid': (0.5, 0.5, 0.5, 1.0),
  'axes': (1.0, 0.0, 0.0, 1.0),
  'name': (1.0, 1.0, 1.0, 1.0),
  'value': (1.0, 1.0, 1.0, 1.0),
  'silk': (1.0, 1.0, 1.0, 1.0),
  'docu': (1.0, 1.0, 0.0, 0.7),
  'smd': (0.0, 0.0, 1.0, 1.0),
  'pad': (0.0, 1.0, 0.0, 1.0),
  'meta':  (1.0, 1.0, 1.0, 1.0),
  'restrict':  (0.0, 1.0, 0.0, 0.3),
  'stop':  (0.0, 1.0, 1.0, 0.3),
  'keepout':  (1.0, 0.0, 0.5, 0.7),
  'vrestrict':  (0.0, 1.0, 0.0, 0.4),
  'unknown':  (1.0, 0.0, 1.0, 0.7),
  'hole': (1.0, 1.0, 1.0, 0.7),
  }

def _inverse(color_scheme):
  re = {}
  for (k,(r,g,b,a)) in color_scheme.items():
    re[k] = (1.0-r, 1.0-g, 1.0-b, a)
  return re

color_schemes['inverse'] = _inverse(color_schemes['default'])

default_settings = {
  'gl/dx': '200',
  'gl/dy': '200',
  'gl/zoomfactor': '50',
  'gl/colorscheme': 'default',
  'gui/keyidle': '1500',
  'gl/autozoom': 'True',
  'gui/displaydocu': 'True',
  'gui/displayrestrict': 'False',
  'gui/displaystop': 'False',
  'gui/displaykeepout': 'False',
  'gui/autocompile': 'True',
}

########NEW FILE########
__FILENAME__ = dialogs
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import uuid
import os.path

from PySide import QtGui, QtCore

from defaultsettings import default_settings, color_schemes

import export.detect as detect

def color_scheme_combo(parent, current):
  l_combo = QtGui.QComboBox()
  for k in color_schemes.keys():
    l_combo.addItem(k, k)
    if k == current:
      l_combo.setCurrentIndex(l_combo.count()-1)
  return l_combo

def library_combo(explorer, allow_non_existing=False, allow_readonly=False):
  l_combo = QtGui.QComboBox()
  selected = explorer.selected_library
  if selected == None:
    selected = explorer.active_library.name
  for lib in explorer.coffee_lib.values():
    l_combo.addItem(lib.name, lib.directory)
    if (not lib.exists and not allow_non_existing) or (lib.readonly and not allow_readonly):
      i = l_combo.model().index(l_combo.count()-1, 0) 
      # trick to make disabled
      l_combo.model().setData(i, 0, QtCore.Qt.UserRole-1)
      # if the prefered selected is our disabled one, don't use it
      if selected == lib.name: selected = None
    elif selected == None:
      selected = lib.name
    if lib.name == selected:
      l_combo.setCurrentIndex(l_combo.count()-1)
  return l_combo

class FDFileDialog(QtGui.QFileDialog):
  def __init__(self, parent, txt):
    super(FDFileDialog, self).__init__(parent, txt)
    self.currentChanged.connect(self.current_changed)

  def current_changed(self, path):
    if os.path.isdir(path) and ".pretty" in path:
      self.setFileMode(QtGui.QFileDialog.Directory)
    else:
      self.setFileMode(QtGui.QFileDialog.ExistingFile)

def select_library(obj):
  qf = FDFileDialog(obj, 'Select Library')
  qf.setFilter("CAD Library (*.lbr *.xml *.pretty *.mod *.kicad_mod)")
  if qf.exec_() == 0: return None
  result = qf.selectedFiles()
  filename = result[0]
  if (filename == ''): return
  #try:
  (t, version) = detect.detect(filename)
  return (t, version, filename)
  #except Exception as ex:
  #  QtGui.QMessageBox.critical(obj, "error", str(ex))
  #  return None

class LibrarySelectDialog(QtGui.QDialog):

  def __init__(self, parent=None):
    super(LibrarySelectDialog, self).__init__(parent)
    self.setWindowTitle('Select Library')
    self.resize(640,160) # TODO, there must be a better way to do this
    vbox = QtGui.QVBoxLayout()
    form_layout = QtGui.QFormLayout()
    lib_widget = QtGui.QWidget()
    lib_hbox = QtGui.QHBoxLayout()
    self.lib_filename = QtGui.QLineEdit()
    self.lib_filename.setReadOnly(True)
    self.lib_filename.setPlaceholderText("press Browse")
    lib_button = QtGui.QPushButton("Browse")
    self.filename = None
    lib_button.clicked.connect(self.get_file)
    lib_hbox.addWidget(self.lib_filename)
    lib_hbox.addWidget(lib_button)
    lib_widget.setLayout(lib_hbox)
    form_layout.addRow("library", lib_widget) 
    self.lib_type = QtGui.QLineEdit()
    self.lib_type.setReadOnly(True)
    form_layout.addRow("type", self.lib_type) 
    vbox.addLayout(form_layout)
    buttons = QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
    self.button_box = QtGui.QDialogButtonBox(buttons, QtCore.Qt.Horizontal)
    self.button_box.accepted.connect(self.accept)
    self.button_box.rejected.connect(self.reject)
    self.button_box.button(QtGui.QDialogButtonBox.Ok).setDisabled(True)
    vbox.addWidget(self.button_box)
    self.setLayout(vbox)

  def get_file(self):
    result = select_library(self)
    if result == None: return
    (self.filetype, self.version, self.filename) = result
    self.lib_filename.setText(self.filename)
    self.lib_type.setText(self.filetype + " " + self.version)
    self.button_box.button(QtGui.QDialogButtonBox.Ok).setDisabled(False)
    self.button_box.button(QtGui.QDialogButtonBox.Ok).setFocus()

# Clone, New, ... are all quite simular, maybe possible to condense?

class CloneFootprintDialog(QtGui.QDialog):

  def __init__(self, parent, old_meta, old_code):
    super(CloneFootprintDialog, self).__init__(parent)
    self.new_id = uuid.uuid4().hex
    self.setWindowTitle('Clone Footprint')
    self.resize(640,160) # TODO, there must be a better way to do this
    vbox = QtGui.QVBoxLayout()
    gbox_existing = QtGui.QGroupBox("existing")
    gbox_new = QtGui.QGroupBox("new")
    existing_fl = QtGui.QFormLayout()
    existing_fl.addRow("name:", QtGui.QLabel(old_meta['name']))
    existing_fl.addRow("id:", QtGui.QLabel(old_meta['id']))
    existing_fl.addRow("library:", QtGui.QLabel(parent.active_library.name))
    gbox_existing.setLayout(existing_fl)
    vbox.addWidget(gbox_existing) 
    self.name_edit = QtGui.QLineEdit()
    self.name_edit.setText(old_meta['name']+"_"+self.new_id)
    new_fl = QtGui.QFormLayout()
    new_fl.addRow("name:", self.name_edit)
    new_fl.addRow("id:", QtGui.QLabel(self.new_id))
    self.l_combo = library_combo(parent)
    new_fl.addRow("library:", self.l_combo)
    gbox_new.setLayout(new_fl)
    vbox.addWidget(gbox_new) 
    buttons = QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
    self.button_box = QtGui.QDialogButtonBox(buttons, QtCore.Qt.Horizontal)
    self.button_box.accepted.connect(self.accept)
    self.button_box.rejected.connect(self.reject)
    vbox.addWidget(self.button_box)
    self.setLayout(vbox)

  def get_data(self):
    return (self.new_id, self.name_edit.text(), self.l_combo.currentText())

class NewFootprintDialog(QtGui.QDialog):

  def __init__(self, parent):
    super(NewFootprintDialog, self).__init__(parent)
    self.new_id = uuid.uuid4().hex
    self.setWindowTitle('New Footprint')
    self.resize(640,160) # TODO, there must be a better way to do this
    vbox = QtGui.QVBoxLayout()
    gbox_new = QtGui.QGroupBox("new")
    self.name_edit = QtGui.QLineEdit()
    self.name_edit.setText("TODO_"+self.new_id)
    new_fl = QtGui.QFormLayout()
    new_fl.addRow("name:", self.name_edit)
    new_fl.addRow("id:", QtGui.QLabel(self.new_id))
    self.l_combo = library_combo(parent)
    new_fl.addRow("library:", self.l_combo)
    gbox_new.setLayout(new_fl)
    vbox.addWidget(gbox_new) 
    buttons = QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
    self.button_box = QtGui.QDialogButtonBox(buttons, QtCore.Qt.Horizontal)
    self.button_box.accepted.connect(self.accept)
    self.button_box.rejected.connect(self.reject)
    vbox.addWidget(self.button_box)
    self.setLayout(vbox)

  def get_data(self):
    return (self.new_id, self.name_edit.text(), self.l_combo.currentText())

class MoveFootprintDialog(QtGui.QDialog):

  def __init__(self, parent, old_meta):
    super(MoveFootprintDialog, self).__init__(parent)
    self.setWindowTitle('Move Footprint')
    self.resize(640,160) # TODO, there must be a better way to do this
    vbox = QtGui.QVBoxLayout()
    gbox_from = QtGui.QGroupBox("from")
    from_fl = QtGui.QFormLayout()
    from_fl.addRow("name:", QtGui.QLabel(old_meta['name']))
    from_fl.addRow("library:", QtGui.QLabel(parent.active_library.name))
    gbox_from.setLayout(from_fl)
    vbox.addWidget(gbox_from) 
    gbox_to = QtGui.QGroupBox("to")
    to_fl = QtGui.QFormLayout()
    self.name_edit = QtGui.QLineEdit()
    self.name_edit.setText(old_meta['name'])
    to_fl.addRow("name:", self.name_edit)
    self.l_combo = library_combo(parent)
    to_fl.addRow("library:", self.l_combo)
    gbox_to.setLayout(to_fl)
    vbox.addWidget(gbox_to) 
    buttons = QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
    self.button_box = QtGui.QDialogButtonBox(buttons, QtCore.Qt.Horizontal)
    self.button_box.accepted.connect(self.accept)
    self.button_box.rejected.connect(self.reject)
    vbox.addWidget(self.button_box)
    self.setLayout(vbox)

  def get_data(self):
    return (self.name_edit.text(), self.l_combo.currentText())

class DisconnectLibraryDialog(QtGui.QDialog):

  def __init__(self, parent):
    super(DisconnectLibraryDialog, self).__init__(parent)
    self.setWindowTitle('Disconnect Library')
    self.resize(640,160) # TODO, there must be a better way to do this
    vbox = QtGui.QVBoxLayout()
    fl = QtGui.QFormLayout()
    self.l_combo = library_combo(parent, True, True)
    fl.addRow("library:", self.l_combo)
    vbox.addLayout(fl)
    buttons = QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
    button_box = QtGui.QDialogButtonBox(buttons, QtCore.Qt.Horizontal)
    button_box.accepted.connect(self.accept)
    button_box.rejected.connect(self.reject)
    vbox.addWidget(button_box)
    self.setLayout(vbox)

  def get_data(self):
    return self.l_combo.currentText()

class AddLibraryDialog(QtGui.QDialog):

  def __init__(self, parent):
    super(AddLibraryDialog, self).__init__(parent)
    self.parent = parent
    self.setWindowTitle('Add Library')
    self.resize(640,160) # TODO, there must be a better way to do this
    vbox = QtGui.QVBoxLayout()
    fl = QtGui.QFormLayout()
    self.name_edit = QtGui.QLineEdit()
    self.name_edit.textChanged.connect(self.name_changed)
    fl.addRow("name:", self.name_edit)
    self.dir_edit = QtGui.QLineEdit()
    self.dir_edit.setReadOnly(True)
    hbox = QtGui.QHBoxLayout()
    hbox.addWidget(self.dir_edit)
    lib_button = QtGui.QPushButton("Browse")
    self.filename = None
    lib_button.clicked.connect(self.get_directory)
    hbox.addWidget(lib_button)
    hbox_w = QtGui.QWidget()
    hbox_w.setLayout(hbox)
    fl.addRow("library", hbox_w)
    self.dir_error = 'select a directory'
    self.name_error = 'provide a name'
    self.name_ok = False
    self.dir_ok = False
    self.issue = QtGui.QLineEdit()
    self.issue.setReadOnly(True)
    fl.addRow('issue:', self.issue)
    vbox.addLayout(fl)
    buttons = QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
    button_box = QtGui.QDialogButtonBox(buttons, QtCore.Qt.Horizontal)
    button_box.accepted.connect(self.accept)
    button_box.rejected.connect(self.reject)
    self.ok_button = button_box.button(QtGui.QDialogButtonBox.Ok)
    self.update_ok_button()
    vbox.addWidget(button_box)
    self.setLayout(vbox)

  def get_directory(self):
    result = QtGui.QFileDialog.getExistingDirectory(self, "Select Directory")
    if result == '': return
    self.dir_edit.setText(result)
    all_dirs = [lib.directory for lib in self.parent.coffee_lib.values()]
    if result in all_dirs:
      self.dir_error = 'directory already exists as library'
      self.dir_ok = False
    else:
      self.dir_ok = True
    self.update_ok_button()

  def name_changed(self):
    name = self.name_edit.text()
    if name == '':
      self.name_error = 'please provide a name'
      self.name_ok = False
    elif name in self.parent.coffee_lib.keys():
      self.name_error = 'name is already in use'
      self.name_ok = False
    else:
      self.name_ok = True
    self.update_ok_button()

  def update_ok_button(self):
    self.ok_button.setDisabled(not (self.name_ok and self.dir_ok))
    if (not self.name_ok) and (not self.dir_ok):
      self.issue.setText(self.name_error + " and " + self.dir_error)
    elif not self.name_ok:
      self.issue.setText(self.name_error)
    elif not self.dir_ok:
      self.issue.setText(self.dir_error)
    else:
      self.issue.clear()
   

  def get_data(self):
    return (self.name_edit.text(), self.dir_edit.text())

class ImportFootprintsDialog(QtGui.QDialog):

  def __init__(self, parent):
    super(ImportFootprintsDialog, self).__init__(parent)
    self.setWindowTitle('Import Footprints')
    self.resize(640,640) # TODO, there must be a better way to do this
    vbox = QtGui.QVBoxLayout()
    form_layout = QtGui.QFormLayout()
    lib_widget = QtGui.QWidget()
    lib_hbox = QtGui.QHBoxLayout()
    self.lib_filename = QtGui.QLineEdit()
    self.lib_filename.setReadOnly(True)
    self.lib_filename.setPlaceholderText("press Browse")
    lib_button = QtGui.QPushButton("Browse")
    self.filename = None
    lib_button.clicked.connect(self.get_file)
    lib_hbox.addWidget(self.lib_filename)
    lib_hbox.addWidget(lib_button)
    lib_widget.setLayout(lib_hbox)
    form_layout.addRow("import from:", lib_widget) 
    self.lib_type = QtGui.QLineEdit()
    self.lib_type.setReadOnly(True)
    form_layout.addRow("type", self.lib_type) 
    vbox.addLayout(form_layout)
    vbox.addWidget(QtGui.QLabel("select footprint(s):"))
    tree = QtGui.QTreeView()
    tree.setModel(self.make_model())
    tree.setRootIsDecorated(False)
    tree.resizeColumnToContents(0)
    tree.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
    self.tree_selection_model = tree.selectionModel()
    self.tree_selection_model.selectionChanged.connect(self.selection_changed)
    vbox.addWidget(tree)
    form_layout2 = QtGui.QFormLayout()
    self.l_combo = library_combo(parent.explorer)
    form_layout2.addRow("import to:", self.l_combo)
    vbox.addLayout(form_layout2)
    buttons = QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
    self.button_box = QtGui.QDialogButtonBox(buttons, QtCore.Qt.Horizontal)
    self.button_box.accepted.connect(self.accept)
    self.button_box.rejected.connect(self.reject)
    self.button_box.button(QtGui.QDialogButtonBox.Ok).setDisabled(True)
    vbox.addWidget(self.button_box)
    self.setLayout(vbox)
 
  def get_file(self):
    result = select_library(self)
    if result == None: return
    (self.filetype, version, self.filename) = result
    self.lib_filename.setText(self.filename)
    self.lib_type.setText(version)
    self.populate_model()

  def make_model(self):
    self.model = QtGui.QStandardItemModel()
    self.model.setColumnCount(1)
    self.model.setHorizontalHeaderLabels(['name'])
    self.root = self.model.invisibleRootItem()
    return self.model

  def populate_model(self):
    self.root.removeRows(0, self.root.rowCount())
    self.importer = detect.make_importer(self.filename)
    name_desc_list = self.importer.list_names()
    name_desc_list = sorted(name_desc_list, lambda (n1,d1),(n2,d2): cmp(n1,n2))
    for (name, desc) in name_desc_list:
      name_item = QtGui.QStandardItem(name)
      name_item.setToolTip(desc)
      name_item.setEditable(False)
      self.root.appendRow([name_item])

  def selection_changed(self, selected, deselected):
    has = self.tree_selection_model.hasSelection()
    self.button_box.button(QtGui.QDialogButtonBox.Ok).setDisabled(not has)

  def get_data(self):
    indices = self.tree_selection_model.selectedIndexes()
    return ([self.model.data(i) for i in indices], self.importer, self.l_combo.currentText())

class PreferencesDialog(QtGui.QDialog):

  def __init__(self, parent):
    super(PreferencesDialog, self).__init__(parent)
    self.parent = parent
    vbox = QtGui.QVBoxLayout()
    form_layout = QtGui.QFormLayout()
    self.gldx = QtGui.QLineEdit(str(parent.setting('gl/dx')))
    self.gldx.setValidator(QtGui.QIntValidator(100,1000))
    form_layout.addRow("GL dx", self.gldx) 
    self.gldy = QtGui.QLineEdit(str(parent.setting('gl/dy')))
    self.gldy.setValidator(QtGui.QIntValidator(100,1000))
    form_layout.addRow("GL dy", self.gldy) 
    self.glzoomf = QtGui.QLineEdit(str(parent.setting('gl/zoomfactor')))
    self.glzoomf.setValidator(QtGui.QIntValidator(1,250))
    form_layout.addRow("zoom factor", self.glzoomf) 
    self.auto_compile = QtGui.QCheckBox("Auto Compile")
    self.auto_compile.setChecked(parent.setting('gui/autocompile')=='True')
    form_layout.addRow("auto compile", self.auto_compile) 
    self.key_idle = QtGui.QLineEdit(str(parent.setting('gui/keyidle')))
    self.key_idle.setValidator(QtGui.QDoubleValidator(0.0,5.0,2))
    form_layout.addRow("key idle", self.key_idle) 
    self.color_scheme = color_scheme_combo(self, str(parent.setting('gl/colorscheme')))
    form_layout.addRow("color scheme", self.color_scheme) 
    vbox.addLayout(form_layout)
    buttons = QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.RestoreDefaults | QtGui.QDialogButtonBox.Cancel
    button_box = QtGui.QDialogButtonBox(buttons, QtCore.Qt.Horizontal)
    rest_but = button_box.button(QtGui.QDialogButtonBox.RestoreDefaults)
    rest_but.clicked.connect(self.settings_restore_defaults)
    button_box.accepted.connect(self.settings_accepted)
    button_box.rejected.connect(self.reject)
    vbox.addWidget(button_box)
    self.setLayout(vbox)

  def settings_restore_defaults(self):
    self.gldx.setText(str(default_settings['gl/dx']))
    self.gldy.setText(str(default_settings['gl/dy']))
    self.glzoomf.setText(str(default_settings['gl/zoomfactor']))
    self.auto_compile.setChecked(default_settings['gui/autocompile'])
    self.key_idle.setText(str(default_settings['gui/keyidle']))
    default_color_scheme = str(default_settings['gui/colorscheme'])
    for i in range(0, self.color_scheme.count()):
      if self.color_scheme.itemText(i) == default_color_scheme:
        self.color_scheme.setCurrentIndex(i)
        break

  def settings_accepted(self):
    settings = self.parent.settings
    settings.setValue('gl/dx', self.gldx.text())
    settings.setValue('gl/dy', self.gldy.text())
    settings.setValue('gl/zoomfactor', self.glzoomf.text())
    settings.setValue('gui/autocompile', str(self.auto_compile.isChecked()))
    settings.setValue('gui/keyidle', self.key_idle.text())
    settings.setValue('gl/colorscheme', self.color_scheme.currentText())
    self.parent.status("Settings updated.")
    self.accept()

########NEW FILE########
__FILENAME__ = gldraw
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

from ctypes import util

from PySide.QtOpenGL import *

from OpenGL.GL import *
import OpenGL.arrays.vbo as vbo

import numpy as np
import math
import os, os.path

from mutil.mutil import *
from defaultsettings import color_schemes

import glFreeType

def make_shader(name):
  print "compiling %s shaders" % (name)
  p = QGLShaderProgram()
  data_dir = os.environ['DATA_DIR']
  vertex = os.path.join(data_dir, 'shaders', "%s.vert" % (name))
  p.addShaderFromSourceFile(QGLShader.Vertex, vertex)
  fragment = os.path.join(data_dir, 'shaders', "%s.frag" % (name))
  p.addShaderFromSourceFile(QGLShader.Fragment, fragment)
  p.link()
  print p.log()
  return p

class GLDraw:

  def __init__(self, glw, font, colorscheme):
    self.glw = glw
    self.font = font
    self.color = colorscheme

    self.circle_shader = make_shader("circle")
    self.circle_move_loc = self.circle_shader.uniformLocation("move")
    self.circle_radius_loc = self.circle_shader.uniformLocation("radius")
    self.circle_inner_loc = self.circle_shader.uniformLocation("inner")
    self.circle_drill_loc = self.circle_shader.uniformLocation("drill")
    self.circle_drill_offset_loc = self.circle_shader.uniformLocation("drill_offset")
    self.circle_angles_loc = self.circle_shader.uniformLocation("angles")

    self.rect_shader = make_shader("rect")
    self.rect_size_loc = self.rect_shader.uniformLocation("size")
    self.rect_move_loc = self.rect_shader.uniformLocation("move")
    self.rect_round_loc = self.rect_shader.uniformLocation("round")
    self.rect_drill_loc = self.rect_shader.uniformLocation("drill")
    self.rect_drill_offset_loc = self.rect_shader.uniformLocation("drill_offset")

    self.octagon_shader = make_shader("octagon")
    self.octagon_size_loc = self.octagon_shader.uniformLocation("size")
    self.octagon_move_loc = self.octagon_shader.uniformLocation("move")
    self.octagon_drill_loc = self.octagon_shader.uniformLocation("drill")
    self.octagon_drill_offset_loc = self.octagon_shader.uniformLocation("drill_offset")

    self.hole_shader = make_shader("hole")
    self.hole_move_loc = self.hole_shader.uniformLocation("move")
    self.hole_radius_loc = self.hole_shader.uniformLocation("radius")

    self.square_data = np.array([[-0.5,0.5],[-0.5,-0.5],[0.5,-0.5],[0.5,0.5]], dtype=np.float32)
    self.square_data_vbo = vbo.VBO(self.square_data)

  def set_color(self, t):
    (r,g,b,a) = self.color.get(t, self.color['unknown'])
    glColor4f(r,g,b,a)

  def zoom(self):
    return float(self.glw.zoomfactor)

  def _txt(self, shape, dx, dy, x, y, on_pad=False):
    if 'name' in shape:
      s = str(shape['name'])
    elif 'value' in shape:
      s = str(shape['value'])
    else: return
    if not on_pad:
      self.set_color(shape['type'])
    else:
      self.set_color('silk')
    if (len(s) == 0):
      return # Do nothing if there's no text
    dxp = dx * self.zoom() # dx in pixels
    dyp = dy * self.zoom() # dy in pixels
    (fdx, fdy) = self.font.ft.getsize(s)
    scale = 1.6*min(dxp / fdx, dyp / fdy)
    sdx = -scale*fdx/2
    sdy = -scale*fdy/2
    glEnable(GL_TEXTURE_2D) # Enables texture mapping
    glPushMatrix()
    glLoadIdentity()
    self.font.glPrint(x*self.zoom()+sdx, y*self.zoom()+sdy, s, scale)
    glPopMatrix ()
    glDisable(GL_TEXTURE_2D)

  def label(self, shape, labels):
    x = fget(shape,'x')
    y = fget(shape,'y')
    dy = fget(shape,'dy', 1)
    dx = fget(shape,'dx', 100.0) # arbitrary large number
    self._txt(shape, dx, dy, x, y)
    return labels

  def _disc(self, x, y, rx, ry, drill, drill_dx, drill_dy, irx = 0.0, iry = 0.0, a1 = 0.0, a2 = 360.0):
    self.circle_shader.bind()
    self.circle_shader.setUniformValue(self.circle_move_loc, x, y)
    self.square_data_vbo.bind()
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(2, GL_FLOAT, 0, self.square_data_vbo)
    self.circle_shader.setUniformValue(self.circle_radius_loc, rx, ry)
    self.circle_shader.setUniformValue(self.circle_inner_loc, irx, iry)
    self.circle_shader.setUniformValue(self.circle_drill_loc, drill, 0.0)
    self.circle_shader.setUniformValue(self.circle_drill_offset_loc, drill_dx, drill_dy)
    a1 = (a1 % 361) * math.pi / 180.0
    a2 = (a2 % 361) * math.pi / 180.0
    self.circle_shader.setUniformValue(self.circle_angles_loc, a1, a2)
    glDrawArrays(GL_QUADS, 0, 4)
    self.circle_shader.release() 

  def _hole(self, x, y, rx, ry):
    self.set_color('hole')
    self.hole_shader.bind()
    self.hole_shader.setUniformValue(self.hole_move_loc, x, y)
    self.square_data_vbo.bind()
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(2, GL_FLOAT, 0, self.square_data_vbo)
    self.hole_shader.setUniformValue(self.hole_radius_loc, rx, ry)
    glDrawArrays(GL_QUADS, 0, 4)
    self.hole_shader.release() 

  def disc(self, shape, labels):
    r = fget(shape, 'r')
    rx = fget(shape, 'rx', r)
    ry = fget(shape, 'ry', r)
    x = fget(shape,'x')
    y = fget(shape,'y')
    drill = fget(shape,'drill')
    drill_dx = fget(shape,'drill_dx')
    drill_dy = fget(shape,'drill_dy')
 
    self._disc(x, y, rx, ry, drill, drill_dx, drill_dy)
    if drill > 0.0:
      self._hole(x,y, drill/2, drill/2)
    if 'name' in shape:
      labels.append(lambda: self._txt(shape, max(rx*1.5, drill), max(ry*1.5, drill), x, y, True))
    return labels

  def hole(self, shape, labels):
    x = fget(shape,'x')
    y = fget(shape,'y')
    drill = fget(shape,'drill')
    if drill > 0.0:
      self._hole(x,y, drill/2, drill/2)
    return labels

  def circle(self, shape, labels):
    r = fget(shape, 'r')
    rx = fget(shape, 'rx', r)
    ry = fget(shape, 'ry', r)
    x = fget(shape,'x')
    y = fget(shape,'y')
    w = fget(shape,'w')
    irx = fget(shape, 'irx', rx)
    rx = rx + w/2
    irx = irx - w/2
    iry = fget(shape, 'iry', ry)
    ry = ry + w/2
    iry = iry - w/2
    a1 = fget(shape, 'a1', 0.0)
    a2 = fget(shape, 'a2', 360.0)
    self._disc(x, y, rx, ry, 0.0, 0.0, 0.0, irx, iry, a1, a2)
    if 'name' in shape:
      labels.append(lambda: self._txt(shape, rx*1.5, ry*1.5, x, y, True))
    if abs(a1 - a2) > 0.25:
      x1 = r * math.cos(a1*math.pi/180)
      y1 = r * math.sin(a1*math.pi/180)
      x2 = r * math.cos(a2*math.pi/180)
      y2 = r * math.sin(a2*math.pi/180)
      self._disc(x1, y1, w/2, w/2, 0.0, 0.0, 0.0)
      self._disc(x2, y2, w/2, w/2, 0.0, 0.0, 0.0)
    return labels

  def _octagon(self, x, y, dx, dy, drill, drill_dx, drill_dy):
    self.octagon_shader.bind()
    self.octagon_shader.setUniformValue(self.octagon_move_loc, x, y)
    self.square_data_vbo.bind()
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(2, GL_FLOAT, 0, self.square_data_vbo)
    self.octagon_shader.setUniformValue(self.octagon_size_loc, dx, dy)
    self.octagon_shader.setUniformValue(self.octagon_drill_loc, drill, 0.0)
    self.octagon_shader.setUniformValue(self.octagon_drill_offset_loc, drill_dx, drill_dy)
    glDrawArrays(GL_QUADS, 0, 4)
    self.octagon_shader.release() 

  def octagon(self, shape, labels):
    r = fget(shape, 'r', 0.0)
    dx = fget(shape, 'dx', r*2)
    dy = fget(shape, 'dy', r*2)
    x = fget(shape,'x')
    y = fget(shape,'y')
    drill = fget(shape,'drill')
    drill_dx = fget(shape,'drill_dx')
    drill_dy = fget(shape,'drill_dy')
 
    self._octagon(x, y, dx, dy, drill, drill_dx, drill_dy)
    if drill > 0.0:
      self._hole(x,y, drill/2, drill/2)
    if 'name' in shape:
      labels.append(lambda: self._txt(shape, dx/1.5, dy/1.5, x, y, True))
    return labels

  def rect(self, shape, labels):
    x = fget(shape, 'x')
    y = fget(shape, 'y')
    dx = fget(shape, 'dx')
    dy = fget(shape, 'dy')
    ro = fget(shape, 'ro') / 100.0
    rot = fget(shape, 'rot')
    drill = fget(shape, 'drill')
    drill_dx = fget(shape, 'drill_dx')
    drill_dy = fget(shape, 'drill_dy')
    if rot not in [0, 90, 180, 270]:
      raise Exception("only 0, 90, 180, 270 rotation supported for now")
    if rot in [90, 270]:
      (dx, dy) = (dy, dx)
    if rot == 90:
      (drill_dx, drill_dy) = (drill_dy, drill_dx)
    if rot == 180:
      (drill_dx, drill_dy) = (-drill_dx, drill_dy)
    if rot == 270:
      (drill_dx, drill_dy) = (-drill_dy, -drill_dx)
    self.rect_shader.bind()
    self.rect_shader.setUniformValue(self.rect_size_loc, dx, dy)
    self.rect_shader.setUniformValue(self.rect_move_loc, x, y)
    self.rect_shader.setUniformValue(self.rect_round_loc, ro, 0)
    self.rect_shader.setUniformValue(self.rect_drill_loc, drill, 0)
    self.rect_shader.setUniformValue(self.rect_drill_offset_loc, drill_dx, drill_dy)
    self.square_data_vbo.bind()
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(2, GL_FLOAT, 0, self.square_data_vbo)
    glDrawArrays(GL_QUADS, 0, 4)
    self.rect_shader.release()
    if drill > 0.0:
      self._hole(x,y, drill/2, drill/2)
    if 'name' in shape:
      m = min(dx, dy)/1.5
      labels.append(lambda: self._txt(shape ,m, m, x, y, True))
    return labels

  def vertex(self, shape, labels):
    x1 = fget(shape, 'x1')
    y1 = fget(shape, 'y1')
    x2 = fget(shape, 'x2')
    y2 = fget(shape, 'y2')
    w = fget(shape, 'w')
    curve = fget(shape, 'curve', 0.0)
    angle = curve*math.pi/180.0
    r = w/2

    dx = x2-x1
    dy = y2-y1
    l = math.sqrt(dx*dx + dy*dy)
    if l == 0.0:
      return labels
    if angle == 0.0:
      px = dy * r / l # trigoniometrics
      py = dx * r / l # trigoniometrics
      glBegin(GL_QUADS)
      glVertex3f(x1-px, y1+py, 0)
      glVertex3f(x1+px, y1-py, 0)
      glVertex3f(x2+px, y2-py, 0)
      glVertex3f(x2-px, y2+py, 0)
      glEnd()
    else:
      ((x0, y0), rc, a1, a2) = calc_center_r_a1_a2((x1,y1),(x2,y2),angle)
      self._disc(x0, y0, rc+r, rc+r, 0.0, 0.0, 0.0, rc-r, rc-r, a1, a2)
    self._disc(x1, y1, r, r, 0.0, 0.0, 0.0)
    self._disc(x2, y2, r, r, 0.0, 0.0, 0.0)
    return labels
 
  def polygon(self, shape, labels):
    w = fget(shape, 'w')
    vert= shape['v']
    for x in vert:
      x['w'] = w
      labels = self.vertex(x, labels)
    return labels

  def skip(self, shape, labels):
    return labels
   
  def draw(self, shapes):
    labels = []
    for shape in shapes:
      self.set_color(shape['type'])
      if 'shape' in shape:
        dispatch = {
          'circle': self.circle,
          'disc': self.disc,
          'label': self.label,
          'line': self.vertex,
          'vertex': self.vertex,
          'octagon': self.octagon,
          'rect': self.rect,
          'polygon': self.polygon,
          'hole': self.hole,
        }
        labels = dispatch.get(shape['shape'], self.skip)(shape, labels)
    for draw_label in labels:
      draw_label()

class JYDGLWidget(QGLWidget):

  def __init__(self, parent):
    super(JYDGLWidget, self).__init__(parent)
    self.parent = parent
    self.colorscheme = color_schemes[str(parent.setting('gl/colorscheme'))]
    start_zoomfactor = int(parent.setting('gl/zoomfactor'))
    self.zoomfactor = start_zoomfactor
    self.zoom_changed = False
    self.auto_zoom = bool(parent.setting('gl/autozoom'))
    data_dir = os.environ['DATA_DIR']
    self.font_file = os.path.join(data_dir, 'gui', 'FreeMonoBold.ttf')
    self.shapes = []
    self.make_dot_field()
    self.called_by_me = False

  def make_dot_field(self):
    gldx = int(self.parent.setting('gl/dx'))
    gldy = int(self.parent.setting('gl/dy'))
    self.dot_field_data = np.array(
      [[x,y] for x in range(-gldx/2, gldx/2) for y in range(-gldy/2, gldy/2)],
      dtype=np.float32)

  def make_dot_field_vbo(self):
    self.dot_field_vbo = vbo.VBO(self.dot_field_data)

  def initializeGL(self):
    self.glversion = glGetString(GL_VERSION)
    self.glversion = self.glversion.split()[0] # take numeric part
    self.glversion = self.glversion.split('.') # split on dots
    if len(self.glversion) < 2:
      raise Exception("Error parsing openGL version")
    self.glversion = float("%s.%s" % (self.glversion[0], self.glversion[1]))
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    #glEnable(GL_TEXTURE_2D) # Enables texture mapping
    glEnable(GL_LINE_SMOOTH)
    self.font = glFreeType.font_data(self.font_file, 64)
    #glEnable(GL_POLYGON_STIPPLE)
    #pattern=np.fromfunction(lambda x,y: 0xAA, (32,32), dtype=uint1)
    #glPolygonStipple(pattern)
    (r,g,b,a) = self.colorscheme['background']
    glClearColor(r, g, b, a)
    self.make_dot_field_vbo()
    self.gldraw = GLDraw(self, self.font, self.colorscheme)

  def paintGL(self):
    new_colorscheme = color_schemes[str(self.parent.setting('gl/colorscheme'))]
    if new_colorscheme != self.colorscheme:
      (r,g,b,a) = new_colorscheme['background']
      glClearColor(r, g, b, a)
    self.colorscheme = new_colorscheme
    self.gldraw.color = self.colorscheme

    if self.zoom_changed:
      self.zoom_changed = False
      self.called_by_me = True
      self.resizeGL(self.width(), self.height())
      self.called_by_me = False

    glClear(GL_COLOR_BUFFER_BIT)
    (r, g, b, a) = self.colorscheme['grid']
    glColor4f(r, g, b, a)
    self.dot_field_vbo.bind() # make this vbo the active one
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(2, GL_FLOAT, 0, self.dot_field_vbo)
    gldx = int(self.parent.setting('gl/dx'))
    gldy = int(self.parent.setting('gl/dy'))
    glDrawArrays(GL_POINTS, 0, gldx * gldy)

    (r, g, b, a) = self.colorscheme['axes']
    glColor4f(r, g, b, a)
    glLineWidth(1)
    glBegin(GL_LINES)
    glVertex3f(-100, 0, 0)
    glVertex3f(100, 0, 0)
    glEnd()
    glBegin(GL_LINES)
    glVertex3f(0, -100, 0)
    glVertex3f(0, 100, 0)
    glEnd()
        
    if self.shapes != None: self.gldraw.draw(self.shapes)

  def resizeGL(self, w, h):
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # every 'zoomfactor' pixels is one mm
    mm_visible_x = float(w)/self.zoomfactor
    if mm_visible_x < 1: mm_visible_x = 1.0
    mm_visible_y = float(h)/self.zoomfactor
    if mm_visible_y < 1: mm_visible_y = 1.0
    glOrtho(-mm_visible_x/2, mm_visible_x/2, -mm_visible_y/2, mm_visible_y/2, -1, 1)
    glViewport(0, 0, w, h)
    if not self.called_by_me:
      self.parent.compile()

  def set_shapes(self, s):
    self.shapes = s
    self.update()

  def wheelEvent(self, event):
    if (event.delta() != 0.0):
      if event.delta() < 0.0:
        if self.zoomfactor > 5:
          self.zoomfactor = self.zoomfactor - 5
          self.parent.zoom_selector.setText(str(self.zoomfactor))
          self.zoom_changed = True
          self.update()
      else:
        if self.zoomfactor < 245:
          self.zoomfactor = self.zoomfactor + 5
          self.parent.zoom_selector.setText(str(self.zoomfactor))
          self.zoom_changed = True
          self.update()
    event.ignore()

########NEW FILE########
__FILENAME__ = glFreeType
#    A quick and simple opengl font library that uses GNU freetype2, written
#    and distributed as part of a tutorial for nehe.gamedev.net.
#    Sven Olsen, 2003
#    Translated to PyOpenGL by Brian Leair, 2004
# 

# import freetype
# We are going to use Python Image Library's font handling
# From PIL 1.1.4:

import sys

if sys.platform == 'win32':
  # we're using pillow 2.0 on win32
  from PIL import ImageFont
else:
  import ImageFont
  
from OpenGL.GL import *

def is_font_available (ft, facename):
    """ Returns true if FreeType can find the requested face name 
        Pass the basname of the font e.g. "arial" or "times new roman"
    """
    if (facename in ft.available_fonts ()):
        return True
    return False


def next_p2 (num):
    """ If num isn't a power of 2, will return the next higher power of two """
    rval = 1
    while (rval<num):
        rval <<= 1
    return rval



def make_dlist (ft, ch, list_base, tex_base_list):
    """ Given an integer char code, build a GL texture into texture_array,
        build a GL display list for display list number display_list_base + ch.
        Populate the glTexture for the integer ch and construct a display
        list that renders the texture for ch.
        Note, that display_list_base and texture_base are supposed
        to be preallocated for 128 consecutive display lists and and 
        array of textures.
    """

    # //The first thing we do is get FreeType to render our character
    # //into a bitmap.  This actually requires a couple of FreeType commands:
    # //Load the Glyph for our character.
    # //Move the face's glyph into a Glyph object.
    # //Convert the glyph to a bitmap.
    # //This reference will make accessing the bitmap easier
    # - This is the 2 dimensional Numeric array

    # Use our helper function to get the widths of
    # the bitmap data that we will need in order to create
    # our texture.
    glyph = ft.getmask (chr (ch))
    glyph_width, glyph_height = glyph.size 
    # We are using PIL's wrapping for FreeType. As a result, we don't have 
    # direct access to glyph.advance or other attributes, so we add a 1 pixel pad.
    width = next_p2 (glyph_width + 1)
    height = next_p2 (glyph_height + 1)


    # python GL will accept lists of integers or strings, but not Numeric arrays
    # so, we buildup a string for our glyph's texture from the Numeric bitmap 

    # Here we fill in the data for the expanded bitmap.
    # Notice that we are using two channel bitmap (one for
    # luminocity and one for alpha), but we assign
    # both luminocity and alpha to the value that we
    # find in the FreeType bitmap. 
    # We use the ?: operator so that value which we use
    # will be 0 if we are in the padding zone, and whatever
    # is the the Freetype bitmap otherwise.
    expanded_data = ""
    for j in xrange (height):
        for i in xrange (width):
            if (i >= glyph_width) or (j >= glyph_height):
                value = chr (0)
                expanded_data += value
                expanded_data += value
            else:
                value = chr (glyph.getpixel ((i, j)))
                expanded_data += value
                expanded_data += value

    # -------------- Build the gl texture ------------

    # Now we just setup some texture paramaters.
    ID = glGenTextures (1)
    tex_base_list [ch] = ID
    glBindTexture (GL_TEXTURE_2D, ID)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

    border = 0
    # Here we actually create the texture itself, notice
    # that we are using GL_LUMINANCE_ALPHA to indicate that
    # we are using 2 channel data.
    glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA, width, height,
        border, GL_LUMINANCE_ALPHA, GL_UNSIGNED_BYTE, expanded_data )

    # With the texture created, we don't need to expanded data anymore
    expanded_data = None



    # --- Build the gl display list that draws the texture for this character ---

    # So now we can create the display list
    glNewList (list_base + ch, GL_COMPILE)

    if (ch == ord (" ")):
        glyph_advance = glyph_width
        glTranslatef(glyph_advance, 0, 0)
        glEndList()
    else:

        glBindTexture (GL_TEXTURE_2D, ID)

        glPushMatrix()

        # // first we need to move over a little so that
        # // the character has the right amount of space
        # // between it and the one before it.
        # glyph_left = glyph.bbox [0]
        # glTranslatef(glyph_left, 0, 0)

        # // Now we move down a little in the case that the
        # // bitmap extends past the bottom of the line 
        # // this is only true for characters like 'g' or 'y'.
        # glyph_descent = glyph.decent
        # glTranslatef(0, glyph_descent, 0)

        # //Now we need to account for the fact that many of
        # //our textures are filled with empty padding space.
        # //We figure what portion of the texture is used by 
        # //the actual character and store that information in 
        # //the x and y variables, then when we draw the
        # //quad, we will only reference the parts of the texture
        # //that we contain the character itself.
        x=float (glyph_width) / float (width)
        y=float (glyph_height) / float (height)

        # //Here we draw the texturemaped quads.
        # //The bitmap that we got from FreeType was not 
        # //oriented quite like we would like it to be,
        # //so we need to link the texture to the quad
        # //so that the result will be properly aligned.
        glBegin(GL_QUADS)
        glTexCoord2f(0,0), glVertex2f(0,glyph_height)
        glTexCoord2f(0,y), glVertex2f(0,0)
        glTexCoord2f(x,y), glVertex2f(glyph_width,0)
        glTexCoord2f(x,0), glVertex2f(glyph_width, glyph_height)
        glEnd()
        glPopMatrix()

        # Note, PIL's FreeType interface hides the advance from us.
        # Normal PIL clients are rendering an entire string through FreeType, not
        # a single character at a time like we are doing here.
        # Because the advance value is hidden from we will advance
        # the "pen" based upon the rendered glyph's width. This is imperfect.
        glTranslatef(glyph_width + 0.75, 0, 0)

        # //increment the raster position as if we were a bitmap font.
        # //(only needed if you want to calculate text length)
        # //glBitmap(0,0,0,0,face->glyph->advance.x >> 6,0,NULL)

        # //Finnish the display list
        glEndList()

    return

# /// A fairly straight forward function that pushes
# /// a projection matrix that will make object world 
# /// coordinates identical to window coordinates.
def pushScreenCoordinateMatrix():
    glPushAttrib(GL_TRANSFORM_BIT)
    [left,bottom,right,top] = glGetIntegerv(GL_VIEWPORT)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    dx = (right-left)/2
    dy = (top-bottom)/2
    glOrtho( -dx, +dx, -dy, +dy, -1,+1)
    glPopAttrib()
    return


# Pops the projection matrix without changing the current
# MatrixMode.
def pop_projection_matrix():
    glPushAttrib(GL_TRANSFORM_BIT)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glPopAttrib()
    return


class font_data:
    def __init__ (self, facename, pixel_height):
        # We haven't yet allocated textures or display lists
        self.m_allocated = False
        self.m_font_height = pixel_height
        self.m_facename = facename

        # Try to obtain the FreeType font
        try:
            self.ft = ImageFont.truetype (facename, pixel_height)
        except:
            raise ValueError, "Unable to locate true type font '%s'" % (facename)

        # Here we ask opengl to allocate resources for
        # all the textures and displays lists which we
        # are about to create.  
        self.m_list_base = glGenLists (128)

        # Consturct a list of 128 elements. This
        # list will be assigned the texture IDs we create for each glyph
        self.textures = [None] * 128

        # This is where we actually create each of the fonts display lists.
        for i in xrange (128):
            make_dlist (self.ft, i, self.m_list_base, self.textures);

        self.m_allocated = True

        return

    def glPrint (self, x, y, string, scale):
        """
        # ///Much like Nehe's glPrint function, but modified to work
        # ///with freetype fonts.
        """
        # We want a coordinate system where things coresponding to window pixels.
        pushScreenCoordinateMatrix()
    
        # //We make the height about 1.5* that of
        h = float (self.m_font_height) / 0.63        
    
        # If There's No Text
        # Do Nothing
        if (string == None):
            pop_projection_matrix()
            return
        if (string == ""):
            pop_projection_matrix()
            return

        # //Here is some code to split the text that we have been
        # //given into a set of lines.  
        # //This could be made much neater by using
        # //a regular expression library such as the one avliable from
        # //boost.org (I've only done it out by hand to avoid complicating
        # //this tutorial with unnecessary library dependencies).
        # //Note: python string object has convenience method for this :)
        lines = string.split ("\n")

        glPushAttrib(GL_LIST_BIT | GL_CURRENT_BIT  | GL_ENABLE_BIT | GL_TRANSFORM_BIT)
        glMatrixMode(GL_MODELVIEW)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glListBase(self.m_list_base)
        modelview_matrix = glGetFloatv(GL_MODELVIEW_MATRIX)

        # //This is where the text display actually happens.
        # //For each line of text we reset the modelview matrix
        # //so that the line's text will start in the correct position.
        # //Notice that we need to reset the matrix, rather than just translating
        # //down by h. This is because when each character is
        # //draw it modifies the current matrix so that the next character
        # //will be drawn immediatly after it.  
        for i in xrange (len (lines)):
            line = lines [i]
            glPushMatrix ()
            glLoadIdentity ()
            glTranslatef (x,y-h*i,0)
            glScalef (scale, scale, 0)
            glMultMatrixf (modelview_matrix)

            # //  The commented out raster position stuff can be useful if you need to
            # //  know the length of the text that you are creating.
            # //  If you decide to use it make sure to also uncomment the glBitmap command
            # //  in make_dlist().
            # //    glRasterPos2f(0,0);
            glCallLists (line)
            # //    rpos = glGetFloatv (GL_CURRENT_RASTER_POSITION)
            # //    float len=x-rpos[0];
            glPopMatrix()

        glPopAttrib()
        pop_projection_matrix()
        return

    def release (self):
        """ Release the gl resources for this Face.
            (This provides the functionality of KillFont () and font_data::clean ()
        """
        if (self.m_allocated):
            # Free up the glTextures and the display lists for our face
            glDeleteLists ( self.m_list_base, 128);
            for ID in self.textures:
                glDeleteTextures (ID);
            # Extra defensive. Clients that continue to try and use this object
            # will now trigger exceptions.
            self.list_base = None
            self.m_allocated = False
        return

    def __del__ (self):
        """ Python destructor for when no more refs to this Face object """
        self.release ()
        return


# Unit Test harness if this python module is run directly.
if __name__ == "__main__":
    print "testing availability of freetype font arial\n"
    ft = ImageFont.truetype ("arial.ttf", 15)
    if ft:
        print "Found the TrueType font 'arial.ttf'"
    else:
        print "faild to find the TrueTYpe font 'arial'\n"

########NEW FILE########
__FILENAME__ = library
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import traceback

from PySide import QtGui, QtCore
from PySide.QtCore import Qt

import coffee.pycoffee as pycoffee
import coffee.library
from mutil.mutil import *
from gui.dialogs import *
import sys, os

class Explorer(QtGui.QTreeView):

  def __init__(self, parent):
    super(Explorer, self).__init__()
    self.parent = parent
    self.coffee_lib = {}
    self.active_footprint = None
    self.active_library = None
    self.selected_library = None

  def has_footprint(self):
    return self.active_footprint is not None

  def initialize_libraries(self, settings):

    def load_libraries():
      size = settings.beginReadArray('library')
      for i in range(size):
        settings.setArrayIndex(i)
        name = settings.value('name')
        filen = settings.value('file')
        library = coffee.library.Library(name, filen)
        self.coffee_lib[name] = library
      settings.endArray()

    if not 'library' in settings.childGroups():
      if sys.platform == 'darwin':
        # TODO: retest and modify under darwin
        example_lib = QtCore.QDir('share/madparts/examples').absolutePath()
      else:
        data_dir = os.environ['DATA_DIR']
        
        example_lib = QtCore.QDir(os.path.join(data_dir, 'examples')).absolutePath()
      library = coffee.library.Library('Examples', example_lib)
      self.coffee_lib = { 'Examples': library }
      self.save_libraries(settings)
    else:
      self.coffee_lib = {}
      load_libraries()

  def save_libraries(self, settings):
    l = self.coffee_lib.values()
    settings.beginWriteArray('library')
    for i in range(len(l)):
      settings.setArrayIndex(i)
      settings.setValue('name', l[i].name)
      settings.setValue('file', l[i].directory)
    settings.endArray()

  def active_footprint_file(self):
   if self.active_footprint is None: return None
   return self.active_footprint.filename

  def _selection_model(self):
    return self.selection_model

  def _make_model(self):
    self.model = QtGui.QStandardItemModel()
    self.selection_model = QtGui.QItemSelectionModel(self.model, self)
    self.model.setColumnCount(2)
    self.model.setHorizontalHeaderLabels(['name','id'])
    parentItem = self.model.invisibleRootItem()
    first = True
    first_foot_meta = None
    first_foot_lib = None
    for coffee_lib in self.coffee_lib.values():
      guilib = Library(self._selection_model, coffee_lib)
      parentItem.appendRow(guilib)
      if first:
        first_foot_meta = guilib.first_foot_meta
        first_foot_lib = guilib
        first = first_foot_meta is None
    return (first_foot_lib, first_foot_meta)

  def populate(self):
    (first_foot_lib, first_foot_meta) = self._make_model()
    self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
    self.setModel(self.model)
    self.setSelectionModel(self.selection_model)
    self._selection_model().currentRowChanged.connect(self.row_changed)
    self.setRootIsDecorated(False)
    self.expandAll()
    self.setItemsExpandable(False)
    self.resizeColumnToContents(0)
    self.doubleClicked.connect(self.parent.show_footprint_tab)
    self.active_footprint = None
    self.active_library = None
    if first_foot_lib is not None:
      #print "selected", first_foot_lib.name
#      if first_foot_lib.select_first_foot():
        #print "selected", first_foot_meta.id
        self.active_footprint = first_foot_meta
        self.active_library = first_foot_lib.coffee_lib
        self._footprint_selected()

  def row_changed(self, current, previous):
    x = current.data(QtCore.Qt.UserRole)
    if x == None: return
    (t,x) = x
    if t == 'library':
      self.selected_library = x
      self._library_selected()
      return
    # it is a footprint
    self.selected_library = None
    (lib_name, fpid) = x
    directory = self.coffee_lib[lib_name].directory
    meta = self.coffee_lib[lib_name].meta_by_id[fpid]
    fn = meta.filename
    #ffn = QtCore.QDir(directory).filePath(fn)
    self.active_footprint = meta
    self.active_library = self.coffee_lib[lib_name]
    self._footprint_selected()
    with open(fn) as f:
      self.parent.update_text(f.read())
    #self.parent.set_code_textedit_readonly(meta.readonly)


  def _footprint_selected(self):
    for action in self.actions():
      self.removeAction(action)
    def _add(text, slot = None):
      action = QtGui.QAction(text, self)
      self.addAction(action)
      if slot != None: action.triggered.connect(slot)
      else: action.setDisabled(True)
    if self.active_library.readonly:
      _add('&Remove')
    else:
      _add('&Remove', self.remove_footprint)
    _add('&Clone', self.clone_footprint)
    _add('&Move', self.move_footprint)
    _add('&Export previous', self.parent.export_previous)
    _add('E&xport', self.parent.export_footprint)
    _add('&Print')
    _add('&Reload', self.parent.reload_footprint)
    self.parent.set_library_readonly(self.active_library.readonly)

  def _library_selected(self):
    for action in self.actions():
      self.removeAction(action)
    def _add(text, slot = None):
      action = QtGui.QAction(text, self)
      self.addAction(action)
      if slot != None: action.triggered.connect(slot)
      else: action.setDisabled(True)
    _add('&Disconnect', self.disconnect_library)
    lib = self.coffee_lib[self.selected_library]
    if lib.readonly or not lib.exists:
      _add('&Import')
      _add('&New')
    else:
      _add('&Import', self.parent.import_footprints)
      _add('&New', self.new_footprint)
    _add('&Reload', self.reload_library)
    self.parent.set_library_readonly(lib.readonly or not lib.exists)

  def remove_footprint(self):
    directory = self.active_library.directory
    fn = self.active_footprint.filename
    QtCore.QDir(directory).remove(fn)
    # fall back to first_foot in library, if any
    library = self.rescan_library(self.active_library.name)
    if library.select_first_foot():
      self.active_footprint = library.first_foot_meta
      self.active_library = library.coffee_lib
    # else fall back to any first foot...
    else:
      root = self.model.invisibleRootItem()
      for row_index in range(0, root.rowCount()):
        library = root.child(row_index)
        if library.select_first_foot():
          self.active_footprint_id = library.first_foot.id
          self.active_library = library
    directory = self.active_library.directory
    fn = self.active_footprint.id + '.coffee'
    ffn = QtCore.QDir(directory).filePath(fn)
    with open(ffn) as f:
       self.parent.update_text(f.read())
    # else... ?
    # TODO we don't support being completely footless now

  def clone_footprint(self):    
    if self.parent.executed_footprint == []:
      s = "Can't clone if footprint doesn't compile."
      QtGui.QMessageBox.warning(self, "warning", s)
      self.parent.status(s) 
      return
    old_code = self.parent.code_textedit.toPlainText()
    old_meta = pycoffee.eval_coffee_meta(old_code)
    dialog = CloneFootprintDialog(self, old_meta, old_code)
    if dialog.exec_() != QtGui.QDialog.Accepted: return
    (new_id, new_name, new_lib) = dialog.get_data()
    new_code = pycoffee.clone_coffee_meta(old_code, old_meta, new_id, new_name)
    lib_dir = QtCore.QDir(self.coffee_lib[new_lib].directory)
    new_file_name = lib_dir.filePath("%s.coffee" % (new_id))
    with open(new_file_name, 'w+') as f:
      f.write(new_code)
    s = "%s/%s cloned to %s/%s." % (self.active_library.name, old_meta['name'], new_lib, new_name)
    self.active_library = self.rescan_library(new_lib, new_id)
    self.active_footprint = self.active_library.meta_by_id(new_id)
    self.parent.update_text(new_code)
    self.parent.show_footprint_tab()
    self.parent.status(s)

  def new_footprint(self):
    dialog = NewFootprintDialog(self)
    if dialog.exec_() != QtGui.QDialog.Accepted: return
    (new_id, new_name, new_lib) = dialog.get_data()
    new_code = pycoffee.new_coffee(new_id, new_name)
    lib_dir = QtCore.QDir(self.coffee_lib[new_lib].directory)
    new_file_name = lib_dir.filePath("%s.coffee" % (new_id))
    with open(new_file_name, 'w+') as f:
      f.write(new_code)
    self.parent.update_text(new_code)
    self.active_library = self.rescan_library(new_lib, new_id)
    self.active_footprint = self.active_library.meta_by_id(new_id)
    self.parent.show_footprint_tab()
    self.parent.status("%s/%s created." % (new_lib, new_name))

  def move_footprint(self):
    old_code = self.parent.code_textedit.toPlainText()
    old_meta = pycoffee.eval_coffee_meta(old_code)
    dialog = MoveFootprintDialog(self, old_meta)
    if dialog.exec_() != QtGui.QDialog.Accepted: return
    (new_name, new_lib) = dialog.get_data()
    old_name = old_meta['name']
    my_id = self.active_footprint.id
    fn = my_id + '.coffee'
    old_lib = self.active_library
    new_code = old_code.replace("#name %s" % (old_name), "#name %s" % (new_name))
    new_lib_dir = QtCore.QDir(self.coffee_lib[new_lib].directory)
    new_file_name = new_lib_dir.filePath(fn)
    with open(new_file_name, 'w+') as f:
      f.write(new_code)
    status_str = "moved %s/%s to %s/%s." % (old_lib.name, old_name, new_lib, new_name)
    self.parent.status(status_str)
    if old_lib.name == new_lib: 
      self.rescan_library(old_lib.name, my_id) # just to update the nameq
    else:
      full_fn = os.path.join(old_lib.directory, fn)
      os.unlink(full_fn)
      self.rescan_library(old_lib.name)
      self.active_library = self.rescan_library(new_lib, my_id)

  def add_library(self):
    dialog = AddLibraryDialog(self)
    if dialog.exec_() != QtGui.QDialog.Accepted: return
    (name, directory) = dialog.get_data()
    lib = coffee.library.Library(name, directory)
    self.coffee_lib[name] = lib
    self.save_libraries(self.parent.settings)
    root = self.model.invisibleRootItem()
    guilib = Library(self.selectionModel, lib)
    root.appendRow(guilib)
    self.expandAll()  

  def disconnect_library(self):
    dialog = DisconnectLibraryDialog(self)
    if dialog.exec_() != QtGui.QDialog.Accepted: return
    lib_name = dialog.get_data()
    del self.coffee_lib[lib_name]
    self.save_libraries(self.parent.settings)
    root = self.model.invisibleRootItem()
    for row_index in range(0, root.rowCount()):
      library = root.child(row_index)
      if library.name == lib_name: break
    root.removeRow(row_index)
    if lib_name != self.active_library: return
    # select first foot of the first library which contains foots
    for row_index in range(0, root.rowCount()):
      library = root.child(row_index)
      if library.select_first_foot():
        self.active_footprint = library.first_foot_meta
        self.active_library = library.coffee_lib
        fn = self.active_footprint.filename
        with open(fn) as f:
          self.parent.update_text(f.read())
        return

  def rescan_library(self, name, select_id = None):
    root = self.model.invisibleRootItem()
    for row_index in range(0, root.rowCount()):
      library = root.child(row_index)
      if library.name == name:
        library.scan()
        if select_id is not None:
          select_meta = self.coffee_lib[name].meta_by_id[select_id]
          library.select(select_meta)
        self.expandAll()
        return library
    return None

  def reload_library(self):
    if self.selected_library != None:
      lib = self.selected_library
    else:
      lib = self.active_library.name
    self.rescan_library(lib)
    self.parent.status("%s reloaded." % (lib))


class Library(QtGui.QStandardItem):

  def __init__(self, selection_model, coffee_lib):
    self.selection_model = selection_model
    self.coffee_lib = coffee_lib
    name = coffee_lib.name
    self.name = name
    super(Library, self).__init__(name)
    print "making %s" % (name)
    self.setData(('library', name), Qt.UserRole)
    self.directory = coffee_lib.directory
    self.selected_foot = None
    self.setEditable(False)
    self.items = {}
    self.id_items = {}
    self.first_foot_meta = None
    self.scan()

  def meta_by_id(self, id):
    return self.coffee_lib.meta_by_id[id]

  def select(self, meta):
    id = meta.id
    print "%s/%s selected." % (meta.filename, meta.name)
    item = self.items[id]
    id_item = self.id_items[id]
    self.selection_model().select(item.index(), QtGui.QItemSelectionModel.ClearAndSelect)
    self.selection_model().select(id_item.index(), QtGui.QItemSelectionModel.Select)

  def select_first_foot(self):
    if self.first_foot_meta is not None:
      self.select(self.first_foot_meta)
      return True
    return False

  def append(self, parent, meta):
    # print "adding %s to %s" % (self.name, parent.data(Qt.UserRole))
    name_item = QtGui.QStandardItem(meta.name)
    identify = ('footprint', (self.name, meta.id))
    name_item.setData(identify, Qt.UserRole)
    name_item.setToolTip(meta.desc)
    id_item   = QtGui.QStandardItem(meta.id)
    id_item.setData(identify, Qt.UserRole)
    id_item.setToolTip(meta.desc)
    name_item.setEditable(False) # you edit them in the code
    id_item.setEditable(False)
    if meta.readonly:
      name_item.setForeground(QtGui.QBrush(Qt.gray))
      id_item.setForeground(QtGui.QBrush(Qt.gray))
    parent.appendRow([name_item, id_item])
    self.items[meta.id] = name_item
    self.id_items[meta.id] = id_item
    return name_item

  def scan(self):
    self.coffee_lib.scan()
    self.items = {}
    self.id_items = {}
    self.selected_foot = None
    self.removeRows(0, self.rowCount())
    self.row_data = []
    self.footprints = []
    self.first_foot_meta = None
    if not self.coffee_lib.exists:
      self.setForeground(QtGui.QBrush(Qt.red))
      return
    if self.coffee_lib.readonly:
      self.setForeground(QtGui.QBrush(Qt.gray))

    def _add(parent, meta_list):
      if meta_list == []: return
      for meta in meta_list:
        new_item = self.append(parent, meta)
        _add(new_item, map(lambda id: self.coffee_lib.meta_by_id[id], meta.child_ids))
       
    _add(self, self.coffee_lib.root_meta_list)
    if self.coffee_lib.root_meta_list != []:
      self.first_foot_meta = self.coffee_lib.root_meta_list[0]

########NEW FILE########
__FILENAME__ = inter
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL
#
# functions that operate on the intermediate format

import copy
from mutil.mutil import *

def cleanup_js(inter):
  def _remove_constructor(item):
    if 'constructor' in item:
      del item['constructor']
    return item
  return filter(_remove_constructor, inter)

def add_names(inter):
  def generate_ints():
    for i in xrange(1, 10000):
      yield i
  g = generate_ints()
  def _c(x):
    if 'type' in x:
      if x['type'] in ['smd', 'pad']:
        if not 'name' in x:
          x['name'] = str(g.next())
    else:
      x['type'] = 'silk' # default type
    return x
  return [_c(x) for x in inter]

def get_meta(inter):
  for shape in inter:
    if shape['type'] == 'meta':
      return shape
  return None

def prepare_for_display(inter, filter_out):
  inter = filter(lambda x: x['type'] not in filter_out, inter)
  h = {
    'silk': 4,
    'docu': 3,
    'smd': 2,
    'pad': 1,
  }
  def _sort(x1, x2):
    t1 = h.get(x1['type'], 0)
    t2 = h.get(x2['type'], 0)
    return cmp(t1, t2)
  sinter = sorted(inter, _sort)
  def convert(x):
    if 'shape' in x and x['shape'] == 'rect':
      if 'x1' in x and 'x2' in x and 'y1' in x and 'y2' in x:
        x['x'] = (x['x1'] + x['x2'])/2
        x['y'] = (x['y1'] + x['y2'])/2
        x['dx'] = abs(x['x1'] - x['x2'])
        x['dy'] = abs(x['y1'] - x['y2'])
    return x
  return map(convert, sinter)

# this method has a bunch of code duplication of gldraw...
def bounding_box(inter):
  def oget(m, k, d):
    if k in m: return m[k]
    return d
  def fget(m, k, d = 0.0):
    try:
      return float(oget(m, k, d))
    except TypeError:
      return d
  def circle(shape):
    r = fget(shape, 'r')
    rx = fget(shape, 'rx', r)
    ry = fget(shape, 'ry', r)
    x = fget(shape,'x')
    y = fget(shape,'y')
    w = fget(shape,'w')
    x1 = x - rx - w/2
    x2 = x + rx + w/2
    y1 = y - ry - w/2
    y2 = y + ry + w/2
    return (x1, y1, x2, y2)

  def disc(shape):
    r = fget(shape, 'r')
    rx = fget(shape, 'rx', r)
    ry = fget(shape, 'ry', r)
    x = fget(shape,'x')
    y = fget(shape,'y')
    x1 = x - rx
    x2 = x + rx
    y1 = y - ry
    y2 = y + ry
    return (x1, y1, x2, y2)
    
  def label(shape):
    x = fget(shape,'x')
    y = fget(shape,'y')
    dy = fget(shape,'dy', 1)
    dx = dy * len(shape['value'])
    x1 = x - dx/2
    x2 = x + dx/2
    y1 = y - dy/2
    y2 = y + dy/2
    return (x1, y1, x2, y2)
    
  def vertex(shape):
    x1 = fget(shape, 'x1')
    y1 = fget(shape, 'y1')
    x2 = fget(shape, 'x2')
    y2 = fget(shape, 'y2')
    w = fget(shape, 'w')
    x1a = min(x1, x2) - w/2
    x2a = max(x1, x2) + w/2
    y1a = min(y1, y2) - w/2
    y2a = max(y1, y2) + w/2
    return (x1a, y1a, x2a, y2a)

  def polygon(shape):
    w = fget(shape, 'w')
    vert= shape['v']
    if vert == []: return None
    fst = vert[0]
    fst['w'] = w
    (x1,y1,x2,y2) = vertex(fst)
    for x in vert[1:]:
      x['w'] = w
      (x1a,y1a,x2a,y2a) = vertex(x)
      x1 = min(x1, x1a)
      y1 = min(y1, y1a)
      x2 = max(x2, x2a)
      y2 = max(y2, y2a)
    return (x1, y1, x2, y2)
    

  def octagon(shape):
    r = fget(shape, 'r', 0.0)
    dx = fget(shape, 'dx', r*2)
    dy = fget(shape, 'dy', r*2)
    x = fget(shape,'x')
    y = fget(shape,'y')
    x1 = x - dx/2
    x2 = x + dx/2
    y1 = y - dy/2
    y2 = y + dy/2
    return (x1, y1, x2, y2)

  def rect(shape):
    x = fget(shape, 'x')
    y = fget(shape, 'y')
    dx = fget(shape, 'dx')
    dy = fget(shape, 'dy')
    x1 = x - dx/2
    x2 = x + dx/2
    y1 = y - dy/2
    y2 = y + dy/2
    return (x1, y1, x2, y2)

  def unknown(shape):
    return (0,0,0,0)

  x1 = 0
  y1 = 0
  x2 = 0
  y2 = 0
  dispatch = {
    'circle': circle,
    'disc': disc,
    'label': label,
    'line': vertex,
    'vertex': vertex,
    'polygon': polygon,
    'octagon': octagon,
    'rect': rect,
  }
  if inter == None or inter == []: return (-1,-1,1,1)
  for x in inter:
    if 'shape' in x:
       res = dispatch.get(x['shape'], unknown)(x)
       if res != None:
         (xx1, xy1, xx2, xy2) = res
         x1 = min(x1, xx1)
         y1 = min(y1, xy1)
         x2 = max(x2, xx2)
         y2 = max(y2, xy2)
  return (x1,y1,x2,y2)

def size(inter):
  if inter == None or inter == []:
    return (1, 1, 0, 0, 0, 0)
  (x1,y1,x2,y2) = bounding_box(inter)
  dx = 2*max(abs(x2),abs(x1)) 
  dy = 2*max(abs(y2),abs(y1))
  return (dx, dy, x1, y1, x2, y2)

def sort_by_type(inter):
  h = {
    'silk': 1,
    'docu': 2,
    'smd': 3,
    'pad': 4,
    'restrict': 5,
    'stop': 6,
  }
  def _sort(x1, x2):
    t1 = h.get(x1['type'], 0)
    t2 = h.get(x2['type'], 0)
    return cmp(t1, t2)
  return sorted(inter, _sort)

def _count_num_values(pads, param):
  res = {}
  for pad in pads:
    v = pad[param]
    if not v in res:
      res[v] = 1
    else:
      res[v] = res[v] + 1
  i = len(res.keys())
  return (i, res)

def _equidistant(pads, direction):
  if len(pads) < 2: return False
  expected = abs(pads[1][direction] - pads[0][direction])
  prev = pads[1][direction]
  for item in pads[2:]:
    cur = item[direction]
    if f_neq(abs(cur - prev), expected):
      return False
    prev = cur
  return True

def _all_equal(pads, direction):
  first = pads[0][direction]
  return reduce(lambda a, p: a and f_eq(p[direction], first), pads, True)

def _sort_by_field(pads, field, reverse=False):
  def _sort_by(a, b):
    return cmp(a[field], b[field])
  return sorted(pads, cmp=_sort_by, reverse=reverse)

def _clone_pad(pad_in, remove):
  pad = copy.deepcopy(pad_in)
  for x in remove:
    if x in pad: del pad[x]
  if 'name' in pad: del pad['name']
  return pad

def _make_mods(skip, pad, pads):
  l = []
  for (item, i) in zip(pads, range(len(pads))):
    mod = {}
    #print "investigating", i, item
    for (k,v) in item.items():
      if k in skip: continue
      if k == 'name' and str(i+1) == v: continue
      #print 'testing', k, v
      if k not in pad:
        mod[k] = v
      elif pad[k] != v:
        mod[k] = v
    if mod != {}:
      mod['type'] = 'special'
      if 'shape' in mod:
        mod['real_shape'] = mod['shape']
      mod['shape'] = 'mod'
      mod['index'] = i
      #print "adding mod", mod
      l.append(mod)
  return l

def _check_single(orig_pads, horizontal):
  if horizontal:
    equal_direction = 'y'
    diff_direction = 'x'
    reverse = False
  else:
    equal_direction = 'x'
    diff_direction = 'y'
    reverse = True
  # sort pads by decreasing in other direction
  pads = _sort_by_field(orig_pads, diff_direction, reverse)
  # check if the distance is uniform
  if not _equidistant(pads, diff_direction):
    #print "not equidistant", diff_direction
    return orig_pads
  # check if all x coordinates are equal
  if not _all_equal(pads, equal_direction):
    #print "not all equal", equal_direction
    return orig_pads
  # create a pad based on the second pad
  # the first one might be special...
  pad = _clone_pad(pads[1], [diff_direction])
  pad_type = pad['type']
  # create a special pseudo entry
  special = {}
  special['type'] = 'special'
  special['shape'] = 'single'
  special['direction'] = diff_direction
  special['ref'] = pad_type
  special['num'] = len(pads)
  special['e'] = abs(pads[0][diff_direction] - pads[1][diff_direction])
  l = [pad, special]
  # check if there are mods needed
  mods = _make_mods([diff_direction], pad, pads)
  return l + mods

def _split_dual(pads, direction):
  r1 = []
  r2 = []
  for pad in pads:
    # we assume the dual rows are centered around (0,0)
    if pad[direction] < 0:
      r1.append(pad)
    else:
      r2.append(pad)
  return (r1, r2)

def _one_by_one_equal(r1, r2, direction):
  for (p1, p2) in zip(r1, r2):  
    if f_neq(p1[direction], p2[direction]):
      return False
  return True

def _check_dual_alt(r1, r2):
  i = 1
  for (p1, p2) in zip(r1, r2):
    n1 = int(p1['name'])
    n2 = int(p2['name'])
    #print i, n1, n2
    if not (n1 == i and n2 == i+1):
      return False
    i = i + 2
  return True

def _check_dual(orig_pads, horizontal):
  if horizontal:
    split_direction = 'y'
    diff_direction = 'x'
    #print 'dual horizontal?'
  else:
    split_direction = 'x'
    diff_direction = 'y'
    #print 'dual vertical?'
  # split in two rows
  (r1, r2) = _split_dual(orig_pads, split_direction)
  # sort pads in 2 rows
  r1 = _sort_by_field(r1, diff_direction)
  r2 = _sort_by_field(r2, diff_direction)
  # check if the distance is uniform
  if not _equidistant(r1, diff_direction):
    #print "r1 not equidistant", diff_direction
    return orig_pads
  if not _equidistant(r2, diff_direction):
    #print "r2 not equidistant", diff_direction
    return orig_pads
  # check if all coordinates are equal in split_direction
  if not _all_equal(r1, split_direction):
    #print "r1 not all equal", split_direction
    return orig_pads
  if not _all_equal(r2, split_direction):
    #print "r2 not all equal", split_direction
    return orig_pads
  # check that the two rows are one by one equal
  if not _one_by_one_equal(r1, r2, diff_direction):
    #print "r1,r2 not one by one equal", diff_direction
    return orig_pads
  # normal: 1 6 alt: 1 2
  #         2 5      3 4
  #         3 4      5 6
  # check if the pad order is normal or alt
  # if it is not pure alt we assume normal and if needed
  # set other names via mods
  is_alt = _check_dual_alt(r1, r2)
  between = abs(r1[0][split_direction] - r2[0][split_direction])
  # create a pad based on the second pad
  # the first one might be special...
  pad = _clone_pad(r1[1], ['x','y'])
  pad_type = pad['type']
  # create a special pseudo entry
  special = {}
  special['type'] = 'special'
  special['shape'] = 'dual'
  special['alt'] = is_alt
  special['direction'] = diff_direction
  special['ref'] = pad_type
  special['num'] = len(orig_pads)
  special['between'] = between
  special['e'] = abs(r1[0][diff_direction] - r1[1][diff_direction])
  if not is_alt:
    if diff_direction == 'y':
      sort_pads = r1 + r2
    else:
      r2.reverse()
    sort_pads = r1 + r2
  else:
    sort_pads = list_combine(map(lambda (a,b): [a,b], zip(r1, r2)))
  mods = _make_mods(['x','y'], pad, sort_pads)
  rot = 0
  if 'rot' in pad: rot = pad['rot']
  if diff_direction == 'x': 
    rot = rot - 90 # will be rotated again while drawing
  if rot < 0 : rot = rot + 360
  pad['rot'] = rot
  if rot == 0:
    del pad['rot']
  return [pad, special] + mods

def _split_quad(pads):
  minx = reduce(lambda a,x: min(a, x['x']) , pads, 0)
  maxx = reduce(lambda a,x: max(a, x['x']) , pads, 0)
  miny = reduce(lambda a,x: min(a, x['y']) , pads, 0)
  maxy = reduce(lambda a,x: max(a, x['y']) , pads, 0)
  h = {
    'minx': [],
    'maxx': [],
    'miny': [],
    'maxy': []
  }
  for pad in pads:
    if pad['x'] == minx: h['minx'].append(pad)
    if pad['x'] == maxx: h['maxx'].append(pad)
    if pad['y'] == miny: h['miny'].append(pad)
    if pad['y'] == maxy: h['maxy'].append(pad)
  h['minx'] = sorted(h['minx'], lambda a,b: cmp(a['y'], b['y']), reverse=True)
  h['maxx'] = sorted(h['maxx'], lambda a,b: cmp(a['y'], b['y']))
  h['miny'] = sorted(h['miny'], lambda a,b: cmp(a['x'], b['x']))
  h['maxy'] = sorted(h['maxy'], lambda a,b: cmp(a['x'], b['x']), reverse=True)
  return (h['minx'], h['miny'], h['maxx'], h['maxy']) 


def _check_quad(orig_pads):
  n = len(orig_pads)
  if not (n % 4 == 0):
    #print 'quad: n not dividable by 4'
    return orig_pads
  (left_x, down_y, right_x, up_y) = _split_quad(orig_pads)
  if len(left_x) != n/4 or len(down_y) != n/4 or len(right_x) != n/4 or len(up_y) != n/4:
    #print 'quad: some row is not n/4 length'
    return origpads
  dx = right_x[0]['x'] - left_x[0]['x']
  dy = up_y[0]['y'] - down_y[0]['y']
  if f_neq(dx, dy):
    #print 'quad: distance not equal between x and y rows', dx, dy
    return orig_pads
  between = dx   
  if not _equidistant(left_x, 'y'):
    #print 'quad: left row not equidistant'
    return orig_pads
  if not _equidistant(right_x, 'y'):
    #print 'quad: right row not equidistant'
    return orig_pads
  if not _equidistant(up_y, 'x'):
    #print 'quad: up row not equidistant'
    return orig_pads
  if not _equidistant(down_y, 'x'):
    #print 'quad: down row not equidistant'
    return orig_pads
  # we have a quad!
  # create a pad based on the second pad
  # the first one might be special...
  pad = _clone_pad(left_x[1], ['x','y'])
  pad_type = pad['type']
  # create a special pseudo entry
  special = {}
  special['type'] = 'special'
  special['shape'] = 'quad'
  special['ref'] = pad_type
  special['num'] = len(orig_pads)
  special['between'] = between
  special['e'] = abs(left_x[0]['y'] - left_x[1]['y'])
  sort_pads = left_x + down_y + right_x + up_y
  # skipping dx and dy is not entirely correct but deals with
  # footprints that don't use rotate but swap dx and dy instead
  mods = _make_mods(['x','y', 'rot', 'dx', 'dy'], pad, sort_pads)
  return [pad, special] + mods

def _check_sequential(pads):
  for (i, pad) in zip(range(0, len(pads)), pads):
    #print i, pad
    if 'name' in pad:
      if pad['name'] == str(i):
         del pad['name']
      else:
         return pads
  return pads

def _find_pad_patterns(pads):
  n = len(pads)
  if n == 1:
    if 'name' in pads[0]:
      if pads[0]['name'] == '1':
        del pads[0]['name']
    return pads

  (x_diff, _z) = _count_num_values(pads, 'x')
  #print 'x diff ', x_diff
  (y_diff, _z) = _count_num_values(pads, 'y')
  #print 'y diff ', y_diff

  # possibly single row
  if x_diff == 1 and y_diff == n:
    return _check_single(pads, horizontal=False)
  if x_diff == n and y_diff == 1:
    return _check_single(pads, horizontal=True)

  # possibly dual row
  if x_diff == 2 and y_diff == n/2:
    return _check_dual(pads, horizontal=False)
  if x_diff == n/2 and y_diff == 2:
    return _check_dual(pads, horizontal=True)

  # possibly a quad
  if x_diff == (n/4)+2 and y_diff == (n/4)+2:
    return _check_quad(pads)

  return pads

def find_pad_patterns(inter):
  pads = filter(lambda x: x['type'] == 'pad', inter)
  no_pads = filter(lambda x: x['type'] != 'pad', inter)
  if len(pads) > 0:
    pads = _find_pad_patterns(pads)
    inter = pads + no_pads

  smds = filter(lambda x: x['type'] == 'smd', inter)
  no_smds = filter(lambda x: x['type'] != 'smd', inter)
  if len(smds) > 0:
    smds = _find_pad_patterns(smds)
    inter = smds + no_smds
  return inter

def import_footprint(importer, footprint_name):
  interim = importer.import_footprint(footprint_name) 
  #print interim
  interim = sort_by_type(interim)
  return find_pad_patterns(interim)

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
#
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import argparse, sys, traceback

import coffee.pycoffee as pycoffee
import coffee.generatesimple as generatesimple
from inter import inter
import export.detect as detect

def export_footprint(remaining):
  parser = argparse.ArgumentParser(prog=sys.argv[0] + ' export')
  parser.add_argument('footprint', help='footprint file')
  parser.add_argument('library', help='library file')
  args = parser.parse_args(remaining)
  with open(args.footprint, 'r') as f:
    code = f.read()
  (error_txt, status_txt, interim) = pycoffee.compile_coffee(code)
  if interim == None:
    print >> sys.stderr, error_txt
    return 1
  meta = filter(lambda x: x['type'] == 'meta', interim)[0]
  name = meta['name']
  print name, 'compiled.'
  try:
    exporter = detect.make_exporter(args.library)
  except Exception as ex:
    print >> sys.stderr, str(ex)
    return 1
  exporter.export_footprint(interim)
  exporter.save()
  print "Exported to "+args.library+"."
  return 0

def import_footprint(remaining):
  parser = argparse.ArgumentParser(prog=sys.argv[0] + ' import')
  parser.add_argument('library', help='library file')
  parser.add_argument('footprint', help='footprint name', nargs='?')
  args = parser.parse_args(remaining)
  try:
    importer = detect.make_importer(args.library)
  except Exception as ex:
    print >> sys.stderr, str(ex)
    return 1
  names = map(lambda (a,_): a, importer.list_names())
  if args.footprint is None:
    if len(names) == 1:
      args.footprint = names[0]
    else:
      print >> sys.stderr, "Please specify the footprint name as more then one were found in %s." % (args.library)
      return 1
  elif not args.footprint in names:
    print >> sys.stderr, "Footprint %s not found in %s." % (args.footprint, args.library)
    return 1
  interim = inter.import_footprint(importer, args.footprint) 
  try:
    coffee = generatesimple.generate_coffee(interim)
  except Exception as ex:
    tb = traceback.format_exc()
    print >> sys.stderr, "Footprint %s\nerror: %s" % (args.footprint, str(ex) + '\n' + tb)
    return 1
  meta = pycoffee.eval_coffee_meta(coffee)
  new_file_name = "%s.coffee" % (meta['id'])
  with open(new_file_name, 'w+') as f:
    f.write(coffee)
  print "%s/%s written to %s." % (args.library, args.footprint, new_file_name)
  return 0

def list_library(remaining):
  parser = argparse.ArgumentParser(prog=sys.argv[0] + ' ls')
  parser.add_argument('library', help='library file', nargs='?', default='.')
  args = parser.parse_args(remaining)
  try:
    detect.make_importer(args.library).list()
  except Exception as ex:
    print >> sys.stderr, str(ex)
    return 1
  return 0

def cli_main():
  parser = argparse.ArgumentParser()
  parser.add_argument('command', help='command to execute', 
    choices=['import','export', 'ls'])
  (args, remaining) = parser.parse_known_args()
  if args.command == 'import':
    return import_footprint(remaining)
  elif args.command == 'export':
    return export_footprint(remaining)
  else:
    return list_library(remaining)

if __name__ == '__main__':
  sys.exit(cli_main())

########NEW FILE########
__FILENAME__ = madparts
#!/usr/bin/env python
#
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import time, traceback, os.path

from PySide import QtGui, QtCore
from PySide.QtCore import Qt

from gui.dialogs import *
import gui.gldraw, gui.library

import coffee.pycoffee as pycoffee
import coffee.generatesimple as generatesimple

from inter import inter

from syntax.jssyntax import JSHighlighter
from syntax.coffeesyntax import CoffeeHighlighter

import export.detect

class MainWin(QtGui.QMainWindow):

  def __init__(self):
    super(MainWin, self).__init__()

    self.explorer = gui.library.Explorer(self)

    self.settings = QtCore.QSettings()

    menuBar = self.menuBar()
    fileMenu = menuBar.addMenu('&File')
    self.add_action(fileMenu, '&Quit', self.close, 'Ctrl+Q')

    editMenu = menuBar.addMenu('&Edit')
    self.add_action(editMenu, '&Preferences', self.preferences)

    footprintMenu = menuBar.addMenu('&Footprint')
    self.add_action(footprintMenu, '&Clone', self.explorer.clone_footprint, 'Ctrl+Alt+C')
    self.add_action(footprintMenu, '&Delete', self.explorer.remove_footprint, 'Ctrl+Alt+D')
    self.ac_new = self.add_action(footprintMenu, '&New', self.explorer.new_footprint, 'Ctrl+Alt+N')
    self.ac_move = self.add_action(footprintMenu, '&Move', self.explorer.move_footprint, 'Ctrl+Alt+M')
    self.add_action(footprintMenu, '&Export previous', self.export_previous, 'Ctrl+E')
    self.add_action(footprintMenu, '&Export', self.export_footprint, 'Ctrl+Alt+X')
    self.add_action(footprintMenu, '&Print', None, 'Ctrl+P')
    self.add_action(footprintMenu, '&Reload', self.reload_footprint, 'Ctrl+R')
    footprintMenu.addSeparator()

    self.display_docu = self.setting('gui/displaydocu') == 'True'
    self.display_restrict = self.setting('gui/displayrestrict') == 'True'
    self.display_stop = self.setting('gui/displaystop') == 'True'
    self.display_keepout = self.setting('gui/displaykeepout') == 'True'
    self.docu_action = self.add_action(footprintMenu, "&Display Docu", self.docu_changed, checkable=True, checked=self.display_docu)
    self.restrict_action = self.add_action(footprintMenu, "&Display Restrict", self.restrict_changed, checkable=True, checked=self.display_restrict)
    self.stop_action = self.add_action(footprintMenu, "&Display Stop", self.stop_changed, checkable=True, checked=self.display_stop)
    self.keepout_action = self.add_action(footprintMenu, "&Display Keepout", self.keepout_changed, checkable=True, checked=self.display_keepout)

    footprintMenu.addSeparator()
    self.add_action(footprintMenu, '&Force Compile', self.compile, 'Ctrl+F')

    libraryMenu = menuBar.addMenu('&Library')
    self.add_action(libraryMenu, '&Add', self.explorer.add_library)
    self.add_action(libraryMenu, '&Disconnect', self.explorer.disconnect_library)
    self.add_action(libraryMenu, '&Import', self.import_footprints, 'Ctrl+Alt+I')
    self.add_action(libraryMenu, '&Reload', self.explorer.reload_library, 'Ctrl+Alt+R')

    helpMenu = menuBar.addMenu('&Help')
    self.add_action(helpMenu, '&About', self.about)

    self.explorer.initialize_libraries(self.settings)

    splitter = QtGui.QSplitter(self, QtCore.Qt.Horizontal)
    splitter.addWidget(self._left_part())
    splitter.addWidget(self._right_part())
    self.setCentralWidget(splitter)

    self.last_time = time.time() - 10.0
    self.first_keypress = False
    self.timer = QtCore.QTimer()
    self.timer.setSingleShot(True)
    self.timer.timeout.connect(self.key_idle_timer_timeout)

    self.executed_footprint = []
    self.export_library_filename = ""
    self.export_library_filetype = ""
    self.gl_dx = 0
    self.gl_dy = 0
    self.gl_w = 0
    self.gl_h = 0

    self.is_fresh_file = False

    self.statusBar().showMessage("Ready.")

  ### GUI HELPERS

  def set_code_textedit_readonly(self, readonly):
    self.code_textedit.setReadOnly(readonly)
    pal = self.code_textedit.palette()
    if not self.explorer.has_footprint(): 
      pal.setColor(QtGui.QPalette.Base, Qt.darkGray)
    elif self.explorer.active_footprint.readonly:
      pal.setColor(QtGui.QPalette.Base, Qt.lightGray)
    else:
      pal.setColor(QtGui.QPalette.Base, Qt.white)
    self.code_textedit.setPalette(pal)

  def set_library_readonly(self, readonly):
    self.ac_new.setDisabled(readonly)
    self.ac_move.setDisabled(readonly)

  def _footprint(self):
    lsplitter = QtGui.QSplitter(QtCore.Qt.Vertical)
    self.code_textedit = QtGui.QTextEdit()
    self.code_textedit.setAcceptRichText(False)
    if self.explorer.has_footprint():
      with open(self.explorer.active_footprint_file()) as f:
        self.update_text(f.read())
      self.set_code_textedit_readonly(self.explorer.active_footprint.readonly)
    else:
      self.set_code_textedit_readonly(True)
    self.highlighter1 = CoffeeHighlighter(self.code_textedit.document())
    self.code_textedit.textChanged.connect(self.editor_text_changed)
    self.result_textedit = QtGui.QTextEdit()
    self.result_textedit.setReadOnly(True)
    self.highlighter2 = JSHighlighter(self.result_textedit.document())
    lsplitter.addWidget(self.code_textedit)
    lsplitter.addWidget(self.result_textedit)
    self.lsplitter = lsplitter
    [s1, s2] = lsplitter.sizes()
    lsplitter.setSizes([min(s1+s2-150, 150), 150])
    return lsplitter  

  def _left_part(self):
    lqtab = QtGui.QTabWidget()
    self.explorer.populate()
    lqtab.addTab(self.explorer, "library")
    lqtab.addTab(self._footprint(), "footprint")
    lqtab.setCurrentIndex(1)
    self.left_qtab = lqtab
    return lqtab

  def _right_part(self):
    rvbox = QtGui.QVBoxLayout()
    rhbox = QtGui.QHBoxLayout()
    self.glw = gui.gldraw.JYDGLWidget(self)
    self.zoom_selector = QtGui.QLineEdit(str(self.glw.zoomfactor))
    self.zoom_selector.setValidator(QtGui.QIntValidator(1, 250))
    self.zoom_selector.editingFinished.connect(self.zoom)
    self.zoom_selector.returnPressed.connect(self.zoom)
    rhbox.addWidget(QtGui.QLabel("Zoom: "))
    rhbox.addWidget(self.zoom_selector)
    self.auto_zoom = QtGui.QCheckBox("Auto")
    self.auto_zoom.setChecked(self.setting('gl/autozoom') == 'True')
    self.auto_zoom.stateChanged.connect(self.zoom)
    self.auto_zoom.stateChanged.connect(self.auto_zoom_changed)
    rhbox.addWidget(self.auto_zoom)
    rvbox.addLayout(rhbox)
    rvbox.addWidget(self.glw)

    right = QtGui.QWidget(self)
    right.setLayout(rvbox)
    return right

  def about(self):
    a = """
<p align="center"><b>madparts</b><br/>the functional footprint editor</p>
<p align="center">(c) 2013 Joost Yervante Damad &lt;joost@damad.be&gt;</p>
<p align="center">Additional Contributors:</p>
<p align="center">Alex Schultz &lt;alex@strangeautomata.com&gt;</p>
<p align="center"><a href="http://madparts.org">http://madparts.org</a></p>
"""
    QtGui.QMessageBox.about(self, "about madparts", a)

  def add_action(self, menu, text, slot, shortcut=None, checkable=False, checked=False):
    action = QtGui.QAction(text, self)
    if checkable:
      action.setCheckable(True)
      if checked:
        action.setChecked(True)
    menu.addAction(action)
    if slot == None:
      action.setDisabled(True)
    else:
      action.triggered.connect(slot)
    if shortcut != None: action.setShortcut(shortcut)
    return action

  ### GUI SLOTS

  def preferences(self):
    dialog = PreferencesDialog(self)
    dialog.exec_()

  def reload_footprint(self):
    with open(self.explorer.active_footprint_file(), 'r') as f:
      self.update_text(f.read())
    self.status("%s reloaded." % (self.explorer.active_footprint_file()))

  def editor_text_changed(self): 
    if self.is_fresh_file:
      self.is_fresh_file = False
      self.compile()
      return
    key_idle = self.setting("gui/keyidle")
    if key_idle > 0:
      t = time.time()
      if (t - self.last_time < float(key_idle)/1000.0):
        self.timer.stop()
        self.timer.start(float(key_idle))
        return
      self.last_time = t
      if self.first_keypress:
        self.first_keypress = False
        self.timer.stop()
        self.timer.start(float(key_idle))
        return
    self.first_keypress = True
    if self.setting('gui/autocompile') == 'True':
      self.compile()

  def key_idle_timer_timeout(self): 
    self.editor_text_changed()

  def export_previous(self):
    if self.export_library_filename == "":
      self.export_footprint()
    else:
      self._export_footprint()

  def export_footprint(self):
     dialog = LibrarySelectDialog(self)
     if dialog.exec_() != QtGui.QDialog.Accepted: return
     self.export_library_filename = dialog.filename
     self.export_library_filetype = dialog.filetype
     self.export_library_version = dialog.version
     self._export_footprint()

  def show_footprint_tab(self):
    self.left_qtab.setCurrentIndex(1)

  def close(self):
    QtGui.qApp.quit()

  def zoom(self):
    self.glw.zoomfactor = int(self.zoom_selector.text())
    self.glw.zoom_changed = True
    self.glw.auto_zoom = self.auto_zoom.isChecked()
    if self.glw.auto_zoom:
      (dx, dy, x1, y1, x2, y2) = inter.size(self.executed_footprint)
      self.update_zoom(dx, dy, x1, y1, x2, y2, True)
    self.glw.updateGL()

  def auto_zoom_changed(self):
    self.settings.setValue('gl/autozoom', str(self.auto_zoom.isChecked()))

  def import_footprints(self):
    dialog = ImportFootprintsDialog(self)
    if dialog.exec_() != QtGui.QDialog.Accepted: return
    (footprint_names, importer, selected_library) = dialog.get_data()
    lib_dir = QtCore.QDir(self.explorer.coffee_lib[selected_library].directory)
    l = []
    for footprint_name in footprint_names:
      interim = inter.import_footprint(importer, footprint_name) 
      l.append((footprint_name, interim))
    cl = []
    for (footprint_name, interim) in l:
      try:
       coffee = generatesimple.generate_coffee(interim)
       cl.append((footprint_name, coffee))
      except Exception as ex:
        tb = traceback.format_exc()
        s = "warning: skipping footprint %s\nerror: %s" % (footprint_name, str(ex) + '\n' + tb)
        QtGui.QMessageBox.warning(self, "warning", s)
    for (footprint_name, coffee) in cl:
      meta = pycoffee.eval_coffee_meta(coffee)
      new_file_name = lib_dir.filePath("%s.coffee" % (meta['id']))
      with open(new_file_name, 'w+') as f:
        f.write(coffee)
    self.explorer.rescan_library(selected_library)
    self.status('Importing done.')

  def docu_changed(self):
    self.display_docu = self.docu_action.isChecked()
    self.settings.setValue('gui/displaydocu', str(self.display_docu))
    self.compile()

  def restrict_changed(self):
    self.display_restrict = self.restrict_action.isChecked()
    self.settings.setValue('gui/displayrestrict', str(self.display_restrict))
    self.compile()

  def stop_changed(self):
    self.display_stop = self.stop_action.isChecked()
    self.settings.setValue('gui/displaystop', str(self.display_stop))
    self.compile()

  def keepout_changed(self):
    self.display_keepout = self.keepout_action.isChecked()
    self.settings.setValue('gui/displaykeepout', str(self.display_keepout))
    self.compile()

  ### OTHER METHODS

  def update_text(self, new_text):
    self.is_fresh_file = True
    self.code_textedit.setPlainText(new_text)

  def setting(self, key):
    return self.settings.value(key, default_settings[key])

  def status(self, s):
    self.statusBar().showMessage(s)

  def update_zoom(self, dx, dy, x1, y1, x2, y2, force=False):
    # TODO: keep x1, y1, x2, y2 in account
    w = self.glw.width()
    h = self.glw.height()
    if dx == self.gl_dx and dy == self.gl_dy and w == self.gl_w and h == self.gl_h:
      if not force: return
    self.gl_dx = dx
    self.gl_dy = dy
    self.gl_w = w
    self.gl_h = h
    zoomx = 0.0
    zoomy = 0.0
    if dx > 0.0:
      zoomx = float(w) / dx
    if dy > 0.0:
      zoomy = float(h) / dy
    if zoomx == 0.0 and zoomy == 0.0:
      zoomx = 42 
      zoomy = 42
    zoom = int(min(zoomx, zoomy))
    self.zoom_selector.setText(str(zoom))
    self.glw.zoomfactor = zoom
    self.glw.zoom_changed = True

  def compile(self):
    code = self.code_textedit.toPlainText()
    if code == "": return
    compilation_failed_last_time = self.executed_footprint == []
    self.executed_footprint = []
    (error_txt, status_txt, interim) = pycoffee.compile_coffee(code)
    if interim != None:
      self.executed_footprint = interim
      self.result_textedit.setPlainText(str(interim))
      if self.auto_zoom.isChecked():
        (dx, dy, x1, y1, x2, y2) = inter.size(interim)
        self.update_zoom(dx, dy, x1, y1, x2, y2)
      filter_out = []
      if not self.display_docu: filter_out.append('docu')
      if not self.display_restrict: filter_out.append('restrict')
      if not self.display_stop: filter_out.append('stop')
      if not self.display_keepout: filter_out.append('keepout')
      self.glw.set_shapes(inter.prepare_for_display(interim, filter_out))
      if not self.explorer.active_footprint.readonly:
        with open(self.explorer.active_footprint_file(), "w+") as f:
          f.write(code)
      if compilation_failed_last_time:
        self.status("Compilation successful.")
      [s1, s2] = self.lsplitter.sizes()
      self.lsplitter.setSizes([s1+s2, 0])
    else:
      self.executed_footprint = []
      self.result_textedit.setPlainText(error_txt)
      self.status(status_txt)
      [s1, s2] = self.lsplitter.sizes()
      self.lsplitter.setSizes([s1+s2-150, 150])
  
  def _export_footprint(self):
    if self.export_library_filename == "": return
    if self.executed_footprint == []:
      s = "Can't export if footprint doesn't compile."
      QtGui.QMessageBox.warning(self, "warning", s)
      self.status(s) 
      return
    try:
      exporter = export.detect.make_exporter_for(self.export_library_filetype, self.export_library_filename)
      exporter.export_footprint(self.executed_footprint)
      exporter.save()
      self.status("Exported to "+self.export_library_filename+".")
    except Exception as ex:
      tb = traceback.format_exc()
      s = "export failure: %s" % (tb)
      QtGui.QMessageBox.warning(self, "warning", s)
      self.status(s)

def gui_main():
  QtCore.QCoreApplication.setOrganizationName("madparts")
  QtCore.QCoreApplication.setOrganizationDomain("madparts.org")
  QtCore.QCoreApplication.setApplicationName("madparts")
  app = QtGui.QApplication(["madparts"])
  widget = MainWin()
  widget.show()
  if widget.glw.glversion < 2.1:
    s = """\
OpenGL 2.1 or better is required (%s found)
(or use software openGL like mesa)""" % (widget.glw.glversion)
    QtGui.QMessageBox.critical(widget, "error", s)
    return 1
  return app.exec_()

########NEW FILE########
__FILENAME__ = mutil
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import math

def oget(m, k, d):
  if k in m: return m[k]
  return d

def fget(m, k, d = 0.0):
  f = float(oget(m, k, d))
  if str(f)=='-0.0':
    return -f
  return f

def iget(m, k, d = 0.0):
  return int(oget(m, k, d))

def eget(m, k, e):
  if k in m: return m[k]
  raise Exception(e)

def generate_ints():
  for i in xrange(1, 10000):
    yield i

def f_eq(a, b):
  return abs(a-b) < 1E-8

def f_neq(a, b):
  return not f_eq(a, b)

def list_combine(l):
  l2 = []
  for x in l: l2 = l2 + x
  return l2

# angle is expected in radians
def calc_center_r_a1_a2(p, q, angle):
  (x1, y1) = p
  (x2, y2) = q
  dx = x2-x1
  dy = y2-y1
  # l: distance between p and q
  l = math.sqrt(dx*dx + dy*dy)
  angle_for_sin = abs(angle)
  if angle_for_sin > math.pi:
    angle_for_sin = -(2*math.pi-angle)
  # rc: radius of circle containing p and q and arcing through it
  #     with 'angle'
  rc = l / (2 * math.sin(angle_for_sin/2))
  # a: distance from center point to point in between p and q
  a = math.sqrt((rc * rc) - ((l/2)*(l/2)))
  # (ndx, ndy): unit vector pointing from p to q
  (ndx, ndy) = (dx / l, dy / l)
  # (pdx, pdy): perpendicular unit vector
  (pdx, pdy) = (-ndy, ndx)
  # (x3, y3): point between p and q
  (x3,y3) = ((x1+x2)/2, (y1+y2)/2) 
  # (fx, fy): (x3, y3) vector with length a
  # fix sign of (fx, fy) if needed
  (fx, fy) = (a*pdx, a*pdy)
  if rc > 0:
     (fx, fy) = (-fx, -fy)
  if angle > 0:
     (fx, fy) = (-fx, -fy)
  # (x0, y0): center point of circle aka 'c'
  (x0, y0) = (x3 + fx, y3 + fy)
  # (cpx, cpy): vector from c to p
  (cpx, cpy) = (x1-x0, y1-y0)
  # (cqx, cqy): vector from c to q
  (cqx, cqy) = (x2-x0, y2-y0)
  # calculate angles
  a1 = math.acos(cpx/rc)
  a1s = math.asin(cpy/rc)
  a2 = math.acos(cqx/rc)
  a2s = math.asin(cqy/rc)
  if a1s < 0:
    a1 = 2*math.pi - a1
  if a2s < 0:
    a2 = 2*math.pi - a2
  a1 = a1 * 180 / math.pi
  a2 = a2 * 180 / math.pi
  if angle < 0:
    (a1, a2) = (a2, a1)
  return ((x0, y0), rc, a1, a2)

def calc_second_point(c, s, a):
   (xc, yc) = c
   (x1, y1) = s
   dx = x1-xc
   dy = y1-yc
   r = math.sqrt(dx*dx + dy*dy)
   a1 = math.acos(dx/r)
   if math.asin(dy/r) < 0:
     a1 = 2*math.pi - a1
   a2 = a1 - a
   x2 = xc + r*math.cos(a2)
   y2 = yc + r*math.sin(a2)
   return (x2, y2)

def fc(f):
  if str(f)=='-0.0':
    return -f
  return f

def clean_floats(l):
  def clean_one(h):
    for k in h.keys():
      v = h[k]
      if k == 'v':
        h[k] = clean_floats(v)
      if type(v) == type(42.3):
        if str(v)=='-0.0':
          h[k] = -v
    return h
  return [clean_one(x) for x in l]

########NEW FILE########
__FILENAME__ = coffeesyntax
# based on the pyside C++ syntax highlighting example
# that in itself is based on the C++ example
# see http://qt.gitorious.org/pyside/pyside-examples/blobs/9edeedb37163e71a0040417169ca9aae9e7e6e83/examples/richtext/syntaxhighlighter.py
# inspiration gotten from coffee.vim 
# http://www.vim.org/scripts/script.php?script_id=3590

from PySide import QtGui, QtCore

class CoffeeHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(CoffeeHighlighter, self).__init__(parent)
        # keywords
        keywordFormat = QtGui.QTextCharFormat()
        keywordFormat.setForeground(QtCore.Qt.darkCyan)
        keywordPatterns = [

            # repeat
            "for",
            "while", 
            "until",
            "loop",

            # conditional
            "if", 
            "else",
            "switch",
            "unless"
            "when",
            "then",

            # exception
            "try",
            "catch",
            "finally",

            # keyword
            "new",
            "in",
            "of",
            "by",
            "and",
            "or",
            "not",
            "is",
            "isnt",
            "class",
            "extends",
            "super",
            "do", 
  
            # own; special case: TODO
            "own",

            # operator
            "instanceof",
            "typeof",
            "delete",
 
            # boolean
            "true",
            "on",
            "yes",
            "false",
            "off",
            "no",

            # global
            "null",
            "undefined",

            # special vars
            "this",
            "prototype",
            "arguments",

            # TODO
            "TODO", 
            "FIXME", 
            "XXX",
            "TBD",
            ]
        self.highlightingRules = [(QtCore.QRegExp("\\b"+pattern+"\\b"), keywordFormat) for pattern in keywordPatterns]
        opFormat = QtGui.QTextCharFormat()
        opFormat.setForeground(QtCore.Qt.blue)
        self.highlightingRules = self.highlightingRules + [(QtCore.QRegExp(pattern), opFormat) for pattern in ['\(', '\)', '\[', '\]', '\{', '\}']]
        
        # statements
        statementFormat = QtGui.QTextCharFormat()
        statementFormat.setForeground(QtCore.Qt.darkRed)
        statementFormat.setFontWeight(QtGui.QFont.Bold)
        statementPatterns = [
               "return",
               "break",
               "continue",
               "throw",
            ] 
        self.highlightingRules = self.highlightingRules +  [(QtCore.QRegExp("\\b"+pattern+"\\b"), statementFormat) for pattern in statementPatterns]
        # types
        typeFormat = QtGui.QTextCharFormat()
        typeFormat.setForeground(QtCore.Qt.darkGreen)
        typeFormat.setFontWeight(QtGui.QFont.Bold)
        typePatterns = [
               "Array",
               "Boolean",
               "Date",
               "Function",
               "Number",
               "Object",
               "String",
               "RegExp",
            ] 
        self.highlightingRules = self.highlightingRules +  [(QtCore.QRegExp("\\b"+pattern+"\\b"), typeFormat) for pattern in typePatterns]
        # class
        classFormat = QtGui.QTextCharFormat()
        classFormat.setFontWeight(QtGui.QFont.Bold)
        classFormat.setForeground(QtCore.Qt.darkGreen)
        self.highlightingRules.append((QtCore.QRegExp("\\bQ[A-Za-z]+\\b"),
                classFormat))
        # # comment
        singleLineCommentFormat = QtGui.QTextCharFormat()
        singleLineCommentFormat.setForeground(QtCore.Qt.red)
        self.highlightingRules.append((QtCore.QRegExp("#[^\n]*"),
                singleLineCommentFormat))

        #footprint special meta
        specialMetaFormat = QtGui.QTextCharFormat()
        specialMetaFormat.setForeground(QtCore.Qt.darkGreen)
        specialMetaFormat.setFontWeight(QtGui.QFont.Bold)
        specialMeta = [
            '#format',
            '#name',
            '#id',
            '#parent',
            '#desc',
            ]
        self.highlightingRules = self.highlightingRules +  [(QtCore.QRegExp("^"+pattern+"\\b[^\n]*"), specialMetaFormat) for pattern in specialMeta]


        # quotation
        quotationFormat = QtGui.QTextCharFormat()
        quotationFormat.setForeground(QtCore.Qt.magenta)
        m1 = QtCore.QRegExp("\"[^\"]*\"")
        self.highlightingRules.append((m1, quotationFormat))
        m2 = QtCore.QRegExp("\'[^\']*\'")
        self.highlightingRules.append((m2, quotationFormat))
        # function
        # functionFormat = QtGui.QTextCharFormat()
        # functionFormat.setFontItalic(True)
        # functionFormat.setForeground(QtCore.Qt.blue)
        # self.highlightingRules.append((QtCore.QRegExp("\\b[A-Za-z0-9_]+(?=\\()"),
        #         functionFormat))
        # /* comment */
        self.multiLineCommentFormat = QtGui.QTextCharFormat()
        self.multiLineCommentFormat.setForeground(QtCore.Qt.red)
        self.commentStartExpression = QtCore.QRegExp("/\\*")
        self.commentEndExpression = QtCore.QRegExp("\\*/")

    def highlightBlock(self, text):
        # first apply basic rules
        for pattern, format in self.highlightingRules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        # then do special stuff for multiline
        self.setCurrentBlockState(0)
        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = self.commentStartExpression.indexIn(text)
        while startIndex >= 0:
            endIndex = self.commentEndExpression.indexIn(text, startIndex)
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = text.length() - startIndex
            else:
                commentLength = endIndex - startIndex + self.commentEndExpression.matchedLength()
            self.setFormat(startIndex, commentLength,
                    self.multiLineCommentFormat)
            startIndex = self.commentStartExpression.indexIn(text,
                    startIndex + commentLength);

########NEW FILE########
__FILENAME__ = jssyntax
# based on the pyside C++ syntax highlighting example
# that in itself is based on the C++ example
# see http://qt.gitorious.org/pyside/pyside-examples/blobs/9edeedb37163e71a0040417169ca9aae9e7e6e83/examples/richtext/syntaxhighlighter.py

from PySide import QtGui, QtCore

class JSHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(JSHighlighter, self).__init__(parent)
        # keywords
        keywordFormat = QtGui.QTextCharFormat()
        keywordFormat.setForeground(QtCore.Qt.darkCyan)
        keywordPatterns = [
            "TODO", 
            "FIXME", 
            "XXX",
            "TBD",
            "if", 
            "else",
            "switch",
            "while", 
            "for", 
            "do", 
            "in",
            "break",
            "continue", 
            "new",
            "delete",
            "instanceof", 
            "typeof",
            "return",
            "with",
            "true",
            "false",
            "null", 
            "undefined",
            "arguments",
            "case",
            "default",
            "try",
            "finally",
            "throw",
            "alert",
            "confirm",
            "prompt",
            "status",
            "document",
            "event",
            "location",
            "function",
            "var",
            "let",
            "this",
            ]
        self.highlightingRules = [(QtCore.QRegExp("\\b"+pattern+"\\b"), keywordFormat) for pattern in keywordPatterns]
        # statements
        statementFormat = QtGui.QTextCharFormat()
        statementFormat.setForeground(QtCore.Qt.darkRed)
        statementFormat.setFontWeight(QtGui.QFont.Bold)
        statementPatterns = [
               "return",
               "with",
            ] 

        opFormat = QtGui.QTextCharFormat()
        opFormat.setForeground(QtCore.Qt.blue)
        self.highlightingRules = self.highlightingRules + [(QtCore.QRegExp(pattern), opFormat) for pattern in ['\[', '\]', '\{', '\}']]

        self.highlightingRules = self.highlightingRules +  [(QtCore.QRegExp("\\b"+pattern+"\\b"), statementFormat) for pattern in statementPatterns]
        # types
        typeFormat = QtGui.QTextCharFormat()
        typeFormat.setForeground(QtCore.Qt.darkGreen)
        typeFormat.setFontWeight(QtGui.QFont.Bold)
        typePatterns = [
               "Array",
               "Boolean",
               "Date",
               "Function",
               "Number",
               "Object",
               "String",
               "RegExp",
            ] 
        self.highlightingRules = self.highlightingRules +  [(QtCore.QRegExp("\\b"+pattern+"\\b"), typeFormat) for pattern in typePatterns]
        # class
        classFormat = QtGui.QTextCharFormat()
        classFormat.setFontWeight(QtGui.QFont.Bold)
        classFormat.setForeground(QtCore.Qt.darkGreen)
        self.highlightingRules.append((QtCore.QRegExp("\\bQ[A-Za-z]+\\b"),
                classFormat))
        # // comment
        singleLineCommentFormat = QtGui.QTextCharFormat()
        singleLineCommentFormat.setForeground(QtCore.Qt.red)
        self.highlightingRules.append((QtCore.QRegExp("//[^\n]*"),
                singleLineCommentFormat))

        # quotation
        quotationFormat = QtGui.QTextCharFormat()
        quotationFormat.setForeground(QtCore.Qt.magenta)
        m1 = QtCore.QRegExp("\"[^\"]*\"")
        self.highlightingRules.append((m1, quotationFormat))
        m2 = QtCore.QRegExp("\'[^\']*\'")
        self.highlightingRules.append((m2, quotationFormat))
        # function
        # functionFormat = QtGui.QTextCharFormat()
        # functionFormat.setFontItalic(True)
        # functionFormat.setForeground(QtCore.Qt.blue)
        # self.highlightingRules.append((QtCore.QRegExp("\\b[A-Za-z0-9_]+(?=\\()"),
        #         functionFormat))
        # /* comment */
        self.multiLineCommentFormat = QtGui.QTextCharFormat()
        self.multiLineCommentFormat.setForeground(QtCore.Qt.red)
        self.commentStartExpression = QtCore.QRegExp("/\\*")
        self.commentEndExpression = QtCore.QRegExp("\\*/")

    def highlightBlock(self, text):
        # first apply basic rules
        for pattern, format in self.highlightingRules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        # then do special stuff for multiline
        self.setCurrentBlockState(0)
        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = self.commentStartExpression.indexIn(text)
        while startIndex >= 0:
            endIndex = self.commentEndExpression.indexIn(text, startIndex)
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = text.length() - startIndex
            else:
                commentLength = endIndex - startIndex + self.commentEndExpression.matchedLength()
            self.setFormat(startIndex, commentLength,
                    self.multiLineCommentFormat)
            startIndex = self.commentStartExpression.indexIn(text,
                    startIndex + commentLength);

########NEW FILE########
__FILENAME__ = madparts_test
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

from nose.tools import *
from functools import partial
import copy, shutil, os, time

from bs4 import BeautifulSoup

import coffee.pycoffee as pycoffee
import coffee.generatesimple as generatesimple
from inter import inter
import export.eagle
import export.kicad
import export.kicad_old

assert_multi_line_equal.im_class.maxDiff = None

def _export_eagle(code, expected):
  eagle_lib = 'test/eagle_empty.lbr'
  (error_txt, status_txt, interim) = pycoffee.compile_coffee(code)
  assert interim != None
  version = export.eagle.check_xml_file(eagle_lib)
  assert version == 'Eagle CAD 6.4 library'
  exporter = export.eagle.Export(eagle_lib)
  exporter.export_footprint(interim)
  data = exporter.get_pretty_data()
  assert_multi_line_equal(expected, data)

def _export_eagle_package(code, expected_name, expected):
  eagle_lib = 'test/eagle_empty.lbr'
  (error_txt, status_txt, interim) = pycoffee.compile_coffee(code)
  assert interim != None
  version = export.eagle.check_xml_file(eagle_lib)
  assert version == 'Eagle CAD 6.4 library'
  exporter = export.eagle.Export(eagle_lib)
  eagle_name = exporter.export_footprint(interim)
  assert eagle_name == expected_name
  data = exporter.get_pretty_footprint(eagle_name)
  # print data
  assert_multi_line_equal(expected, data)
  # print code, expected
  return data

def _assert_equal_no_meta(expected, actual):
  a2 = '\n'.join(filter(lambda l: len(l) > 0 and l[0] != '#', actual.splitlines()))
  e2 = '\n'.join(filter(lambda l: len(l) > 0 and l[0] != '#', expected.splitlines()))
  assert_multi_line_equal(e2, a2)

def _import_eagle_package(eagle_package_xml, import_name, expected):
  eagle_lib = 'test/foo.lbr'
  shutil.copyfile('test/eagle_empty.lbr', eagle_lib)
  try:
    importer = export.eagle.Import(eagle_lib)
    # trick to get our package xml into the empty eagle library
    package_soup = BeautifulSoup(eagle_package_xml, 'xml')
    package_soup.is_xml = False
    importer.soup.drawing.packages.append(package_soup)
    with open(eagle_lib, 'w+') as f:
      f.write(str(importer.soup))
    importer = export.eagle.Import(eagle_lib)
    interim = inter.import_footprint(importer, import_name) 
    assert interim != None
    coffee = generatesimple.generate_coffee(interim)
    # print coffee
    _assert_equal_no_meta(expected, coffee)
  finally:
    os.unlink(eagle_lib)

def _export_kicad_package(code, expected_name, expected):
  (error_txt, status_txt, interim) = pycoffee.compile_coffee(code)
  assert interim != None
  exporter = export.kicad.Export("dummy.kicad_mod")
  kicad_name = exporter.export_footprint(interim)
  assert kicad_name == expected_name
  assert_multi_line_equal(expected, exporter.get_string())

def _import_kicad_package(kicad_s, import_name, expected_coffee):
  try:
    kicad_lib = 'test/foo.kicad_mod'
    with open(kicad_lib, "w+") as f:
      f.write(kicad_s)
    importer = export.kicad.Import(kicad_lib)
    interim = inter.import_footprint(importer, import_name) 
    coffee = generatesimple.generate_coffee(interim)
    _assert_equal_no_meta(expected_coffee, coffee)
  finally:
    os.unlink(kicad_lib)

def _export_kicad_old_package(code, expected_name, expected, timestamp):
  (error_txt, status_txt, interim) = pycoffee.compile_coffee(code)
  assert interim != None
  exporter = export.kicad_old.Export("dummy.mod")
  kicad_name = exporter.export_footprint(interim, timestamp)
  assert kicad_name == expected_name
  assert_multi_line_equal(expected, exporter.get_string())

def _import_kicad_old_package(kicad_s, import_name, expected_coffee):
  try:
    kicad_lib = 'test/foo.mod'
    with open(kicad_lib, "w+") as f:
      f.write(kicad_s)
    importer = export.kicad_old.Import(kicad_lib)
    interim = inter.import_footprint(importer, import_name) 
    coffee = generatesimple.generate_coffee(interim)
    # print coffee
    _assert_equal_no_meta(expected_coffee, coffee)
  finally:
    os.unlink(kicad_lib)

def test_export_eagle_full_lib():
   code = """\
#format 1.1
#name DIL16
#id 2ba395a2e67a49bd9defdf961b264e9f
#parent 5162a77450f545079d5716a7c67b2b42
footprint = () ->
 
  n = 16
  e = 2.54
  between = 7.62
  diameter = 1.2
  drill = 0.8
  line_width = 0.3
  outer_y = n*e/4
  half = between/2

  name = new Name outer_y+e/3
  value = new Value -outer_y-e/3

  pad = new LongPad diameter, drill
  l = dual [pad], n, e, between

  # make first pad round
  l[1-1].shape = 'disc'
  l[1-1].r = diameter*3/4

  silk1 = new Line line_width
  silk1.x1 = half-diameter-0.5
  silk1.y1 = outer_y
  silk1.x2 = half-diameter-0.5
  silk1.y2 = -outer_y

  silk2 = rotate180 clone silk1

  silk3 = new Line line_width
  silk3.y1 = outer_y
  silk3.x1 = half-diameter-0.5
  silk3.y2 = outer_y
  silk3.x2 = -half+diameter+0.5

  silk4 = rotate180 clone silk3

  silks = [silk1, silk2, silk3, silk4]

  combine [l,name,silks,value]
"""

   expected = """\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE eagle SYSTEM "eagle.dtd">
<eagle version="6.4">
 <drawing>
  <settings>
   <setting alwaysvectorfont="no"/>
   <setting verticaltext="up"/>
  </settings>
  <grid altdistance="0.01" altunit="inch" altunitdist="inch" display="no" distance="0.1" multiple="1" style="lines" unit="inch" unitdist="inch"/>
  <layers>
   <layer active="yes" color="4" fill="1" name="Top" number="1" visible="yes"/>
   <layer active="yes" color="1" fill="3" name="Route2" number="2" visible="no"/>
   <layer active="yes" color="4" fill="3" name="Route3" number="3" visible="no"/>
   <layer active="yes" color="1" fill="4" name="Route4" number="4" visible="no"/>
   <layer active="yes" color="4" fill="4" name="Route5" number="5" visible="no"/>
   <layer active="yes" color="1" fill="8" name="Route6" number="6" visible="no"/>
   <layer active="yes" color="4" fill="8" name="Route7" number="7" visible="no"/>
   <layer active="yes" color="1" fill="2" name="Route8" number="8" visible="no"/>
   <layer active="yes" color="4" fill="2" name="Route9" number="9" visible="no"/>
   <layer active="yes" color="1" fill="7" name="Route10" number="10" visible="no"/>
   <layer active="yes" color="4" fill="7" name="Route11" number="11" visible="no"/>
   <layer active="yes" color="1" fill="5" name="Route12" number="12" visible="no"/>
   <layer active="yes" color="4" fill="5" name="Route13" number="13" visible="no"/>
   <layer active="yes" color="1" fill="6" name="Route14" number="14" visible="no"/>
   <layer active="yes" color="4" fill="6" name="Route15" number="15" visible="no"/>
   <layer active="yes" color="1" fill="1" name="Bottom" number="16" visible="yes"/>
   <layer active="yes" color="2" fill="1" name="Pads" number="17" visible="yes"/>
   <layer active="yes" color="2" fill="1" name="Vias" number="18" visible="yes"/>
   <layer active="yes" color="6" fill="1" name="Unrouted" number="19" visible="yes"/>
   <layer active="yes" color="15" fill="1" name="Dimension" number="20" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="tPlace" number="21" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="bPlace" number="22" visible="yes"/>
   <layer active="yes" color="15" fill="1" name="tOrigins" number="23" visible="yes"/>
   <layer active="yes" color="15" fill="1" name="bOrigins" number="24" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="tNames" number="25" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="bNames" number="26" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="tValues" number="27" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="bValues" number="28" visible="yes"/>
   <layer active="yes" color="7" fill="3" name="tStop" number="29" visible="no"/>
   <layer active="yes" color="7" fill="6" name="bStop" number="30" visible="no"/>
   <layer active="yes" color="7" fill="4" name="tCream" number="31" visible="no"/>
   <layer active="yes" color="7" fill="5" name="bCream" number="32" visible="no"/>
   <layer active="yes" color="6" fill="3" name="tFinish" number="33" visible="no"/>
   <layer active="yes" color="6" fill="6" name="bFinish" number="34" visible="no"/>
   <layer active="yes" color="7" fill="4" name="tGlue" number="35" visible="no"/>
   <layer active="yes" color="7" fill="5" name="bGlue" number="36" visible="no"/>
   <layer active="yes" color="7" fill="1" name="tTest" number="37" visible="no"/>
   <layer active="yes" color="7" fill="1" name="bTest" number="38" visible="no"/>
   <layer active="yes" color="4" fill="11" name="tKeepout" number="39" visible="yes"/>
   <layer active="yes" color="1" fill="11" name="bKeepout" number="40" visible="yes"/>
   <layer active="yes" color="4" fill="10" name="tRestrict" number="41" visible="yes"/>
   <layer active="yes" color="1" fill="10" name="bRestrict" number="42" visible="yes"/>
   <layer active="yes" color="2" fill="10" name="vRestrict" number="43" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="Drills" number="44" visible="no"/>
   <layer active="yes" color="7" fill="1" name="Holes" number="45" visible="no"/>
   <layer active="yes" color="3" fill="1" name="Milling" number="46" visible="no"/>
   <layer active="yes" color="7" fill="1" name="Measures" number="47" visible="no"/>
   <layer active="yes" color="7" fill="1" name="Document" number="48" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="Reference" number="49" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="tDocu" number="51" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="bDocu" number="52" visible="yes"/>
   <layer active="yes" color="2" fill="1" name="Nets" number="91" visible="yes"/>
   <layer active="yes" color="1" fill="1" name="Busses" number="92" visible="yes"/>
   <layer active="yes" color="2" fill="1" name="Pins" number="93" visible="no"/>
   <layer active="yes" color="4" fill="1" name="Symbols" number="94" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="Names" number="95" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="Values" number="96" visible="yes"/>
   <layer active="yes" color="7" fill="1" name="Info" number="97" visible="yes"/>
   <layer active="yes" color="6" fill="1" name="Guide" number="98" visible="yes"/>
  </layers>
  <library>
   <packages>
    <package name="DIL16">
     <description>
      &lt;br/&gt;&lt;br/&gt;
Generated by 'madparts'.&lt;br/&gt;
Id: 2ba395a2e67a49bd9defdf961b264e9f
 parent: 5162a77450f545079d5716a7c67b2b42
     </description>
     <pad diameter="1.8" drill="0.8" name="1" rot="R180" shape="round" x="-3.81" y="8.89"/>
     <pad drill="0.8" name="2" rot="R180" shape="long" x="-3.81" y="6.35"/>
     <pad drill="0.8" name="3" rot="R180" shape="long" x="-3.81" y="3.81"/>
     <pad drill="0.8" name="4" rot="R180" shape="long" x="-3.81" y="1.27"/>
     <pad drill="0.8" name="5" rot="R180" shape="long" x="-3.81" y="-1.27"/>
     <pad drill="0.8" name="6" rot="R180" shape="long" x="-3.81" y="-3.81"/>
     <pad drill="0.8" name="7" rot="R180" shape="long" x="-3.81" y="-6.35"/>
     <pad drill="0.8" name="8" rot="R180" shape="long" x="-3.81" y="-8.89"/>
     <pad drill="0.8" name="9" rot="R0" shape="long" x="3.81" y="-8.89"/>
     <pad drill="0.8" name="10" rot="R0" shape="long" x="3.81" y="-6.35"/>
     <pad drill="0.8" name="11" rot="R0" shape="long" x="3.81" y="-3.81"/>
     <pad drill="0.8" name="12" rot="R0" shape="long" x="3.81" y="-1.27"/>
     <pad drill="0.8" name="13" rot="R0" shape="long" x="3.81" y="1.27"/>
     <pad drill="0.8" name="14" rot="R0" shape="long" x="3.81" y="3.81"/>
     <pad drill="0.8" name="15" rot="R0" shape="long" x="3.81" y="6.35"/>
     <pad drill="0.8" name="16" rot="R0" shape="long" x="3.81" y="8.89"/>
     <text align="center" layer="25" size="1.0" x="0.0" y="11.0066666667">
      &gt;NAME
     </text>
     <wire layer="21" width="0.3" x1="2.11" x2="2.11" y1="10.16" y2="-10.16"/>
     <wire layer="21" width="0.3" x1="-2.11" x2="-2.11" y1="-10.16" y2="10.16"/>
     <wire layer="21" width="0.3" x1="2.11" x2="-2.11" y1="10.16" y2="10.16"/>
     <wire layer="21" width="0.3" x1="-2.11" x2="2.11" y1="-10.16" y2="-10.16"/>
     <text align="center" layer="27" size="1.0" x="0.0" y="-11.0066666667">
      &gt;VALUE
     </text>
    </package>
   </packages>
   <symbols>
   </symbols>
   <devicesets>
   </devicesets>
  </library>
 </drawing>
</eagle>"""

   _export_eagle(code, expected)

def test_eagle_footprint1():
  code = """\
#format 1.1
#name PIN 1X2
#id 708e13cc5f4e43f7833af53070ba5078
#desc 2 pin pinheader
footprint = () ->

  d = 2.54
  drill = 1
  w = 0.15
  pad_r = (d-0.34)/2
  n = 2

  name = new Name (n*d/2+1)
  value = new Value (-n*d/2-1)
  
  pad = new RoundPad pad_r, drill

  silk1 = new Line w
  silk1.x1 = d/2
  silk1.y1 = -d/4
  silk1.x2 = d/2
  silk1.y2 = d/4
  silk2 = rotate90 clone silk1
  silk3 = rotate90 clone silk2
  silk4 = rotate90 clone silk3

  silk5 = new Line w
  silk5.y1 = d/4
  silk5.x1 = d/2
  silk5.y2 = d/2
  silk5.x2 = d/4
  silk6 = rotate90 clone silk5
  silk7 = rotate90 clone silk6
  silk8 = rotate90 clone silk7

  unit = [pad, silk1, silk2, silk3, silk4, silk5, silk6, silk7, silk8]

  units = single unit, n, d

  combine [name,value, units]
"""
  expected = """\
<package name="PIN_1X2">
 <description>
  2 pin pinheader
&lt;br/&gt;&lt;br/&gt;
Generated by 'madparts'.&lt;br/&gt;
Id: 708e13cc5f4e43f7833af53070ba5078
 </description>
 <text align="center" layer="25" size="1.0" x="0.0" y="3.54">
  &gt;NAME
 </text>
 <text align="center" layer="27" size="1.0" x="0.0" y="-3.54">
  &gt;VALUE
 </text>
 <pad diameter="2.2" drill="1.0" name="1" rot="R0" shape="round" x="0.0" y="1.27"/>
 <wire layer="21" width="0.15" x1="1.27" x2="1.27" y1="0.635" y2="1.905"/>
 <wire layer="21" width="0.15" x1="0.635" x2="-0.635" y1="2.54" y2="2.54"/>
 <wire layer="21" width="0.15" x1="-1.27" x2="-1.27" y1="1.905" y2="0.635"/>
 <wire layer="21" width="0.15" x1="-0.635" x2="0.635" y1="0.0" y2="0.0"/>
 <wire layer="21" width="0.15" x1="1.27" x2="0.635" y1="1.905" y2="2.54"/>
 <wire layer="21" width="0.15" x1="-0.635" x2="-1.27" y1="2.54" y2="1.905"/>
 <wire layer="21" width="0.15" x1="-1.27" x2="-0.635" y1="0.635" y2="0.0"/>
 <wire layer="21" width="0.15" x1="0.635" x2="1.27" y1="0.0" y2="0.635"/>
 <pad diameter="2.2" drill="1.0" name="2" rot="R0" shape="round" x="0.0" y="-1.27"/>
 <wire layer="21" width="0.15" x1="1.27" x2="1.27" y1="-1.905" y2="-0.635"/>
 <wire layer="21" width="0.15" x1="0.635" x2="-0.635" y1="0.0" y2="0.0"/>
 <wire layer="21" width="0.15" x1="-1.27" x2="-1.27" y1="-0.635" y2="-1.905"/>
 <wire layer="21" width="0.15" x1="-0.635" x2="0.635" y1="-2.54" y2="-2.54"/>
 <wire layer="21" width="0.15" x1="1.27" x2="0.635" y1="-0.635" y2="0.0"/>
 <wire layer="21" width="0.15" x1="-0.635" x2="-1.27" y1="0.0" y2="-0.635"/>
 <wire layer="21" width="0.15" x1="-1.27" x2="-0.635" y1="-1.905" y2="-2.54"/>
 <wire layer="21" width="0.15" x1="0.635" x2="1.27" y1="-2.54" y2="-1.905"/>
</package>"""
  _export_eagle_package(code, 'PIN_1X2', expected)

_one_coffee = """\
#format 1.1
#name TEST_EAGLE
#id 708e13cc5f4e43f7833af53070ba5078
#desc eagle test
footprint = () ->
  %s = new %s
  combine [%s]
"""

_one_coffee_eagle = """\
<package name="TEST_EAGLE">
 <description>
  eagle test
&lt;br/&gt;&lt;br/&gt;
Generated by 'madparts'.&lt;br/&gt;
Id: 708e13cc5f4e43f7833af53070ba5078
 </description>
 %s
</package>"""

def _eagle_pad(diameter, drill, rot, shape, x, y):
  return """<pad diameter="%s" drill="%s" name="1" rot="R%s" shape="%s" x="%s" y="%s"/>""" % (diameter, drill, rot, shape, x, y)

def _eagle_smd(dx, dy, rot, roundness, x, y):
  return """<smd dx="%s" dy="%s" layer="1" name="1" rot="R%s" roundness="%s" x="%s" y="%s"/>""" % (dx, dy, rot, roundness, x, y)

def _code_pad(t, args, mods):
  if t == 'Smd':
    varname = 'smd1'
  else:
    varname = 'pad1'
  sargs = map(lambda a: str(a), args)
  if len(sargs) == 0:
    v = t
  else:
    v = "%s %s" % (t, ', '.join(sargs)) 
  smods = sorted(mods, cmp=lambda (a,b),(c,d): cmp(a,c))
  for mod in smods:
    v = v + ("\n  %s" % (varname)) + (".%s = %s" % mod)
  return v

_one_coffee_tests = [
 ([_code_pad, 'RoundPad', [0.5, 0.5], []], 
  [_eagle_pad, 1.0, 0.5, 0, 'round', 0.0, 0.0]),

 ([_code_pad, 'SquarePad', [1.0, 0.5], []], 
  [_eagle_pad, 1.0, 0.5, 0, 'square', 0.0, 0.0]), 

 ([_code_pad, 'LongPad', [1.0, 0.5], []],  
  [_eagle_pad, 1.0, 0.5, 0, 'long', 0.0, 0.0]),

 ([_code_pad, 'OctagonPad', [0.5, 0.5], []],  
  [_eagle_pad, 1.0, 0.5, 0, 'octagon', 0.0, 0.0]),

 ([_code_pad, 'LongPad', [1.0, 0.5], []],  
  [_eagle_pad, 1.0, 0.5, 0, 'long', 0.0, 0.0]),

 ([_code_pad, 'OffsetPad', [1.0, 0.5], []],  
  [_eagle_pad, 1.0, 0.5, 0, 'offset', 0.0, 0.0]),

 ([_code_pad, 'Smd', [], [('dx',1.0),('dy', 0.3)]], 
  [_eagle_smd, 1.0, 0.3, 0, 0, 0.0, 0.0]),
]

def _no_mod(a,b):
  return (a,b)

def _mod_x(code, eagle):
  code[3].append(('x', 7.3))
  eagle[5] = 7.3
  return (code, eagle)

def _mod_y(code, eagle):
  code[3].append(('y', -4.2))
  eagle[6] = -4.2
  return (code, eagle) 

def _mod_rotate(rot, code, eagle):
  code[3].append(('rot', rot))
  eagle[3] = rot
  return (code, eagle)

def test_eagle_export_one():
  def _eagle_do(d, mod):
    (code_list, item_list) = mod(*d)
    code_func = code_list[0]
    code_args = code_list[1:]
    code_text = code_func(*code_args)
    if code_args[0] == 'Smd':
      varname = 'smd1'
    else:
      varname = 'pad1'
    code = _one_coffee % (varname, code_text, varname)
    item_func = item_list[0]
    item_args = item_list[1:]
    item_text = item_func(*item_args)
    expected = _one_coffee_eagle % (item_text)
    data = _export_eagle_package(code, 'TEST_EAGLE', expected)
  mods = [
    _no_mod, _mod_x, _mod_y, 
    partial(_mod_rotate, 90), partial(_mod_rotate, 180),
    partial(_mod_rotate, 270)
    ]
  for mod in mods:
    for d in _one_coffee_tests:
      d2 = copy.deepcopy(d)
      yield _eagle_do, d2, mod

reimported_coffee_polygon = """\
footprint = () ->
  silk1 = new Line 0.2
  silk1.x1 = 1.41421356237
  silk1.y1 = 1.41421356237
  silk1.x2 = -1.41421356237
  silk1.y2 = -1.41421356237
  silk1.curve = 180.0
  silk2 = new Polygon 0.1
  silk2.start 1.0, -4.0
  silk2.add -1.0, -4.0
  silk2.add -1.0, -3.0
  silk2.add 0.0, -2.0, -90.0
  silk2.end -70.0
  silk3 = new Polygon 0.05
  silk3.start 1.1, 1.2
  silk3.add 1.1, 0.2
  silk3.add 0.1, 1.2
  silk3.end 0.0
  silk4 = new Line 0.075
  silk4.x1 = 2.0
  silk4.y1 = -1.0
  silk4.x2 = 1.0
  silk4.y2 = -0.5
  silk4.curve = 30.0
  docu1 = new Polygon 0.1
  docu1.start 0.0, 1.0
  docu1.add -1.0, 0.0, 180.0
  docu1.add 0.0, -1.0, 180.0
  docu1.add 1.0, 0.0, -10.0
  docu1.end -10.0
  docu1.type = 'docu'
  docu2 = new Polygon 0.05
  docu2.start 1.0, 0.0
  docu2.add 3.0, 2.0, 40.0
  docu2.add 4.0, 0.0, -45.0
  docu2.add 3.0, -2.0, -40.0
  docu2.end 40.0
  docu2.type = 'docu'
  combine [docu1,docu2,silk1,silk2,silk3,silk4]
"""

reimported_coffee_polygon_kicad = """\
footprint = () ->
  silk1 = new Line 0.2
  silk1.x1 = 1.41421356237
  silk1.y1 = 1.41421356237
  silk1.x2 = -1.41421356237
  silk1.y2 = -1.41421356237
  silk1.curve = 180.0
  silk2 = new Polygon 0.1
  silk2.start 1, -4
  silk2.add -1, -4
  silk2.add -1, -3
  silk2.add 0.0, -2
  silk2.end 0.0
  silk3 = new Polygon 0.05
  silk3.start 1.1, 1.2
  silk3.add 1.1, 0.2
  silk3.add 0.1, 1.2
  silk3.end 0.0
  silk4 = new Line 0.075
  silk4.x1 = 2.0
  silk4.y1 = -1.0
  silk4.x2 = 1.0
  silk4.y2 = -0.5
  silk4.curve = 30.0
  docu1 = new Polygon 0.1
  docu1.start 0, 1
  docu1.add -1, 0
  docu1.add 0, -1
  docu1.add 1, 0
  docu1.end 0.0
  docu1.type = 'docu'
  docu2 = new Polygon 0.05
  docu2.start 1, 0
  docu2.add 3, 2
  docu2.add 4, 0
  docu2.add 3, -2
  docu2.end 0.0
  docu2.type = 'docu'
  combine [docu1,docu2,silk1,silk2,silk3,silk4]
"""

eagle_polygon = """\
<package name="Polygon">
 <description>
  a simple polygon example
&lt;br/&gt;&lt;br/&gt;
Generated by 'madparts'.&lt;br/&gt;
Id: 0aa9e2e2188f4b66a94f7e0f4b6bdded
 </description>
 <polygon layer="51" width="0.1">
  <vertex curve="180.0" x="0.0" y="1.0"/>
  <vertex curve="180.0" x="-1.0" y="0.0"/>
  <vertex curve="-10.0" x="0.0" y="-1.0"/>
  <vertex curve="-10.0" x="1.0" y="0.0"/>
 </polygon>
 <wire curve="180.0" layer="21" width="0.2" x1="1.41421356237" x2="-1.41421356237" y1="1.41421356237" y2="-1.41421356237"/>
 <polygon layer="51" width="0.05">
  <vertex curve="40.0" x="1.0" y="0.0"/>
  <vertex curve="-45.0" x="3.0" y="2.0"/>
  <vertex curve="-40.0" x="4.0" y="0.0"/>
  <vertex curve="40.0" x="3.0" y="-2.0"/>
 </polygon>
 <polygon layer="21" width="0.1">
  <vertex x="1.0" y="-4.0"/>
  <vertex x="-1.0" y="-4.0"/>
  <vertex curve="-90.0" x="-1.0" y="-3.0"/>
  <vertex curve="-70.0" x="0.0" y="-2.0"/>
 </polygon>
 <polygon layer="21" width="0.05">
  <vertex x="1.1" y="1.2"/>
  <vertex x="1.1" y="0.2"/>
  <vertex x="0.1" y="1.2"/>
 </polygon>
 <wire curve="30.0" layer="21" width="0.075" x1="2.0" x2="1.0" y1="-1.0" y2="-0.5"/>
</package>"""
def test_eagle_export_polygon():
  with open('examples/0aa9e2e2188f4b66a94f7e0f4b6bdded.coffee') as f:
    hl_coffee = f.read()
  _export_eagle_package(hl_coffee, 'Polygon', eagle_polygon)

def test_eagle_import_one():
  def _eagle_do(d, mod):
    (code_list, item_list) = mod(*d)
    code_func = code_list[0]
    code_args = code_list[1:]
    code_text = code_func(*code_args)
    if code_args[0] == 'Smd':
      varname = 'smd1'
    else:
      varname = 'pad1'
    code = _one_coffee % (varname, code_text, varname)
    expected_code = _one_coffee % (varname, code_text, varname)
    item_func = item_list[0]
    item_args = item_list[1:]
    item_text = item_func(*item_args)
    eagle_xml = _one_coffee_eagle % (item_text)
    generated_code = _import_eagle_package(eagle_xml, 'TEST_EAGLE', expected_code)
  mods = [
    _no_mod, _mod_x, _mod_y, 
    partial(_mod_rotate, 90), partial(_mod_rotate, 180),
    partial(_mod_rotate, 270)
    ]
  # only do one test, as it fails currently anyway
  for mod in mods:
    for d in _one_coffee_tests:
      d2 = copy.deepcopy(d)
      yield _eagle_do, d2, mod

def test_eagle_import_polygon():
  expected_code = reimported_coffee_polygon
  _import_eagle_package(eagle_polygon, 'Polygon', expected_code)

empty_coffee = """\
#format 1.1
#name TEST_EMPTY
#id 708e13cc5f4e43f7833af53070ba5078
#desc coffee test
footprint = () ->
  combine []
"""

def test_eagle_export_empty():
  coffee = empty_coffee
  eagle = """\
<package name="TEST_EMPTY">
 <description>
  coffee test
&lt;br/&gt;&lt;br/&gt;
Generated by 'madparts'.&lt;br/&gt;
Id: 708e13cc5f4e43f7833af53070ba5078
 </description>
</package>"""
  _export_eagle_package(coffee, 'TEST_EMPTY', eagle)

def test_kicad_export_empty():
  coffee = empty_coffee
  kicad = "(module TEST_EMPTY (layer F.Cu) (descr \"coffee test\"))"
  _export_kicad_package(coffee, 'TEST_EMPTY', kicad)

kicad_empty = """(module TEST_EMPTY (layer F.Cu) (descr "coffee test"))"""

def test_kicad_import_empty():
  _import_kicad_package(kicad_empty, "TEST_EMPTY", empty_coffee)

kicad_polygon = """\
(module Polygon (layer F.Cu) (descr "a simple polygon example") (fp_poly (pts (xy 0 -1) (xy -1 0) (xy 0 1) (xy 1 0) (xy 0 -1)) (layer Dwgs.User) (width 0.1)) (fp_arc (start 0.0 0.0) (end 1.41421356237 -1.41421356237) (angle -180.0) (layer F.SilkS) (width 0.2)) (fp_poly (pts (xy 1 0) (xy 3 -2) (xy 4 0) (xy 3 2) (xy 1 0)) (layer Dwgs.User) (width 0.05)) (fp_poly (pts (xy 1 4) (xy -1 4) (xy -1 3) (xy 0.0 2) (xy 1 4)) (layer F.SilkS) (width 0.1)) (fp_poly (pts (xy 1.1 -1.2) (xy 1.1 -0.2) (xy 0.1 -1.2) (xy 1.1 -1.2)) (layer F.SilkS) (width 0.05)) (fp_arc (start 0.566987298108 2.61602540378) (end 2.0 1.0) (angle -30.0) (layer F.SilkS) (width 0.075)))\
"""

def test_kicad_export_polygon():
  with open('examples/0aa9e2e2188f4b66a94f7e0f4b6bdded.coffee') as f:
    _export_kicad_package(f.read(), 'Polygon', kicad_polygon)

def test_kicad_import_polygon():
  expected_code = reimported_coffee_polygon_kicad
  _import_kicad_package(kicad_polygon, 'Polygon', expected_code)

kicad_old_empty = """\
PCBNEW-LibModule-V1  Sat 22 Jun 2013 04:47:58 PM CEST
# encoding utf-8
Units mm
$INDEX
TEST_EMPTY
$EndINDEX
$MODULE TEST_EMPTY
Po 0 0 0 15 51C5B8A8 00000000 ~~
Li TEST_EMPTY
Cd coffee test
Sc 0
Op 0 0 0
$EndMODULE TEST_EMPTY
$EndLIBRARY
"""

def kicad_old_just_empty(timestamp):
  return """\
$MODULE TEST_EMPTY
Po 0 0 0 15 %x 00000000 ~~
Li TEST_EMPTY
Cd coffee test
Sc 0
Op 0 0 0
$EndMODULE TEST_EMPTY""" % (timestamp)

# made by exporting to kicad_new and saving as .mod in kicad
kicad_old_polygon = """\
PCBNEW-LibModule-V1  Sun 28 Jul 2013 12:02:51 PM CEST
# encoding utf-8
Units mm
$INDEX
Polygon
$EndINDEX
$MODULE Polygon
Po 0 0 0 15 51F4CCE7 00000000 ~~
Li Polygon
Cd a simple polygon example
Sc 0
AR 
Op 0 0 0
T0 0 0 1.524 1.524 0 0.15 N V 21 N ""
T1 0 0 1.524 1.524 0 0.15 N V 21 N ""
DP 0 0 0 0 5 0.1 24
Dl 0 -1
Dl -1 0
Dl 0 1
Dl 1 0
Dl 0 -1
DA 0 0 1.414214 -1.414214 -1800 0.2 21
DP 0 0 0 0 5 0.05 24
Dl 1 0
Dl 3 -2
Dl 4 0
Dl 3 2
Dl 1 0
DP 0 0 0 0 5 0.1 21
Dl 1 4
Dl -1 4
Dl -1 3
Dl 0 2
Dl 1 4
DP 0 0 0 0 4 0.05 21
Dl 1.1 -1.2
Dl 1.1 -0.2
Dl 0.1 -1.2
Dl 1.1 -1.2
DA 0.566987 2.616025 2.0 1.0 -300 0.075 21
$EndMODULE Polygon
$EndLIBRARY
"""

def kicad_old_just_polygon(timestamp):
  return """\
$MODULE Polygon
Po 0 0 0 15 %x 00000000 ~~
Li Polygon
Cd a simple polygon example
Sc 0
Op 0 0 0
DP 0 0 0 0 5 0.1 24
Dl 0 -1
Dl -1 0
Dl 0 1
Dl 1 0
Dl 0 -1
DA 0.000000 0.000000 1.414214 -1.414214 -1800 0.2 21
DP 0 0 0 0 5 0.05 24
Dl 1 0
Dl 3 -2
Dl 4 0
Dl 3 2
Dl 1 0
DP 0 0 0 0 5 0.1 21
Dl 1 4
Dl -1 4
Dl -1 3
Dl 0 2
Dl 1 4
DP 0 0 0 0 4 0.05 21
Dl 1.1 -1.2
Dl 1.1 -0.2
Dl 0.1 -1.2
Dl 1.1 -1.2
DA 0.566987 2.616025 2.000000 1.000000 -300 0.075 21
$EndMODULE Polygon""" % (timestamp)

# slightly different from kicad new.. less precision for float
# always name and value
reimported_coffee_polygon_kicad_old = """\
footprint = () ->
  name1 = new Name 0.0
  value2 = new Value 0.0
  silk3 = new Line 0.2
  silk3.x1 = 1.414214
  silk3.y1 = 1.414214
  silk3.x2 = -1.414214
  silk3.y2 = -1.414214
  silk3.curve = 180.0
  silk4 = new Polygon 0.1
  silk4.start 1.0, -4.0
  silk4.add -1.0, -4.0
  silk4.add -1.0, -3.0
  silk4.add 0.0, -2.0
  silk4.end 0.0
  silk5 = new Polygon 0.05
  silk5.start 1.1, 1.2
  silk5.add 1.1, 0.2
  silk5.add 0.1, 1.2
  silk5.end 0.0
  silk6 = new Line 0.075
  silk6.x1 = 2.0
  silk6.y1 = -1.0
  silk6.x2 = 1.00000016195
  silk6.y2 = -0.499999796849
  silk6.curve = 30.0
  docu1 = new Polygon 0.1
  docu1.start 0.0, 1.0
  docu1.add -1.0, 0.0
  docu1.add 0.0, -1.0
  docu1.add 1.0, 0.0
  docu1.end 0.0
  docu1.type = 'docu'
  docu2 = new Polygon 0.05
  docu2.start 1.0, 0.0
  docu2.add 3.0, 2.0
  docu2.add 4.0, 0.0
  docu2.add 3.0, -2.0
  docu2.end 0.0
  docu2.type = 'docu'
  combine [docu1,docu2,name1,silk3,silk4,silk5,silk6,value2]
"""


def test_kicad_old_import_empty():
  _import_kicad_old_package(kicad_old_empty, "TEST_EMPTY", empty_coffee)

def test_kicad_old_import_polygon():
  expected_code = reimported_coffee_polygon_kicad_old
  _import_kicad_old_package(kicad_old_polygon, 'Polygon', expected_code)

def test_kicad_old_export_empty():
  timestamp = time.time()
  coffee = empty_coffee
  kicad_old = kicad_old_just_empty(timestamp)
  _export_kicad_old_package(coffee, 'TEST_EMPTY', kicad_old, timestamp)

def test_kicad_old_export_polygon():
  timestamp = time.time()
  with open('examples/0aa9e2e2188f4b66a94f7e0f4b6bdded.coffee') as f:
    _export_kicad_old_package(f.read(), 'Polygon', kicad_old_just_polygon(timestamp), timestamp)

########NEW FILE########
