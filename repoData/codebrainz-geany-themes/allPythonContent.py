__FILENAME__ = autobump
#!/usr/bin/env python

"""
Automatically updates a color scheme's version number when the file
is modified. Run this before committing the change(s) to the repo.
"""

import os
import sys
import hashlib

def gen_sum(fn):
  return hashlib.md5(open(fn).read()).hexdigest()

def read_log(log_file):
  entries = []
  try:
    contents = open(log_file, 'r').read()
  except IOError:
    contents = ''
  for line in [l.strip() for l in contents.split('\n') if l.strip()]:
    m,n = line.split('\t')
    entries.append((n,m))
  return entries

def write_log(log_file, entries):
  new_lines = []
  for ent in entries:
    new_lines.append('\t'.join((ent[1], ent[0])))
  open(log_file, 'w').write('\n'.join(new_lines) + '\n')

def bump_version(fn):
  contents = open(fn).read()
  lines = contents.split('\n')
  new_lines = []
  for line in lines:
    line = line.rstrip()
    if line.strip().startswith('version'):
      k,v = line.split('=')
      v = int(v.strip())
      v += 1
      new_lines.append('version=%d' % v)
      print("Bumped version of '%s' from %d to %d" % (os.path.basename(fn), v-1, v))
    else:
      new_lines.append(line)
  open(fn, 'w').write('\n'.join(new_lines))

def check_scheme(entries, scheme_fn):
  for i, ent in enumerate(entries):
    n,m = ent
    if n == os.path.basename(scheme_fn):
      msum = gen_sum(scheme_fn)
      if m != msum:
        bump_version(scheme_fn)
        entries[i] = (n, gen_sum(scheme_fn))
      break
  else:
    entries.append((os.path.basename(scheme_fn), gen_sum(scheme_fn)))
  return entries

def main(args):
  cur_dir = os.path.abspath(os.path.dirname(__file__))
  root_dir = os.path.abspath(os.path.dirname(cur_dir))
  scheme_dir = os.path.join(root_dir, 'colorschemes')
  log_file = os.path.join(cur_dir, 'versions.log')
  entries = read_log(log_file)
  for fname in os.listdir(scheme_dir):
    if not fname.endswith(".conf"): continue
    path = os.path.join(scheme_dir, fname)
    entries = check_scheme(entries, path)
  write_log(log_file, entries)
  return 0

if __name__ == "__main__": sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = colornorm
#!/usr/bin/env python

import sys
import re

RE_COLOR = re.compile(r'(#|0[xX])([a-fA-F0-9]{6}|[a-fA-F0-9]{3})')

def iter_matched_colors(input_text, normalize=False, regexp=RE_COLOR):

    def normalize_hex_color(hex_color, condense=True):

        def is_condensable(hc):
            return len(hc) == 6 and \
                hc[0] == hc[1] and hc[2] == hc[3] and hc[4] == hc[5]

        def condense_hex_color(hc):
            if not is_condensable(hc): return hc
            else: return hc[0:1] + hc[2:3] + hc[4:5]

        hex_color = hex_color.lower()
        if condense:
            hex_color = condense_hex_color(hex_color)
        return hex_color

    for match in regexp.finditer(input_text):
        hex_color = match.group(2)
        if normalize:
            hex_color = normalize_hex_color(hex_color)
        pfx = match.group(1)
        yield pfx, hex_color, match.start(0), match.end(0)

def main(args):

    if len(args) < 2:
        sys.stderr.write("error: no input file specified\n")
        return 1

    for filename in args[1:]:
        input_text = open(filename).read()
        norm_color_matches = iter_matched_colors(input_text, normalize=True)
        output_text = ''
        last_end = 0
        n_matches = 0
        for pfx, hex_color, start, end in norm_color_matches:
            output_text += input_text[last_end:start] + '#' + hex_color
            last_end = end
            n_matches += 1
        if n_matches == 0: # hack to prevent blank files when no colors match
            output_text = input_text.rstrip() + '\n'
        else:
            output_text += input_text[last_end:]
            output_text = output_text.rstrip() + '\n'
        open(filename, 'w').write(output_text)

    return 0


if __name__ == "__main__": sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = defaultify
#!/usr/bin/env python

import sys
from geanyscheme.confparse import ConfParse

def seq_get(seq, idx, default=None):
  try:
    return seq[idx]
  except IndexError:
    return default

def expand_style(style_str, defaults=('#000', '#fff', 'false', 'false')):
  fields = style_str.split(';')
  fg = seq_get(fields, 0, defaults[0])
  bg = seq_get(fields, 1, defaults[1])
  bold = seq_get(fields, 2, defaults[2])
  italic = seq_get(fields, 3, defaults[3])
  return (fg, bg, bold, italic)

def remove_redundant(style_fields, default_fields):
  new_style = []
  for i, field in enumerate(style_fields):
    if field == default_fields[i]:
      new_style.append('')
    else:
      new_style.append(field)
  return tuple(new_style)

def defaultify_named_styles(conf, defaults):
  for option in conf.options('named_styles'):
    if option == 'default':
      continue
    style = expand_style(conf.get('named_styles', option), defaults)
    style = remove_redundant(style, defaults)
    new_line = ';'.join(style).rstrip(';')
    conf.set('named_styles', option, new_line)

def main(args):
  if len(args) < 2:
    sys.stderr.write("error: no input file(s) specified\n")
    return 1
  for filename in args[1:]:
    conf = ConfParse(filename)
    if conf.has_option('named_styles', 'default'):
      def_line = conf.get('named_styles', 'default')
    else:
      def_line = '#000;#fff;false;false'
    def_fields = expand_style(def_line)
    defaultify_named_styles(conf, def_fields)
    #print(str(conf))
    conf.save()

  return 0

if __name__ == "__main__": sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = color
"""
A class for working with Geany Color Schemes (and other) colours.

The Color class supports two (3 actually) notations. The first is either
condensed or normal HTML/CSS-like hex colors (#ffe, #121212, etc), and the
second is a normal six digit hex string except with a `0x` prefix (0x000000,
0XeFeFeF, etc).

To create a color:

  >>> color = Color(255, 255, 255)

Or parse a color string into a color object:

  >>> color = Color.from_string('#fff')

To convert to a normalized string:

  >>> color.to_string()
  '#fff'

To get a tuple of the RGB components scaled between 0 and 1:

  >>> float_tuple = color.as_floats
  >>> round(float_tuple[0],1), round(float_tuple[0],1), round(float_tuple[0],1)
  (1.0, 1.0, 1.0)

Note: the rounding is just so the test passes without precision problems.

The color can be converted to a string

  >>> 'color: ' + str(color)
  'color: #fff'

And has a tuple-like repr:

  >>> repr(color)
  '(255, 255, 255)'

To run the tests for the Color class, just run this script with or without
the `-v` option, ex:

    $ python color.py -v

"""

class Color(object):

  def __init__(self, r=0, g=0, b=0):
    """
    >>> c = Color(1, 2, 3)
    >>> c.r, c.g, c.b
    (1, 2, 3)
    >>> c = Color(0.5, 1.2, 42.0)
    >>> c.r, c.g, c.b
    (0, 1, 42)
    >>> c = Color('abc', 33, 42)
    Traceback (most recent call last):
      ...
    ValueError: invalid literal for int() with base 10: 'abc'
    """
    self.r, self.g, self.b = int(r), int(g), int(b)

  def __str__(self):
    """
    >>> c = Color(255, 0, 0)
    >>> str(c)
    '#f00'
    """
    return self.to_string()

  def __repr__(self):
    """
    >>> c = Color(255, 0, 0)
    >>> repr(c)
    '(255, 0, 0)'
    """
    return '(%s, %s, %s)' % (self.r, self.g, self.b)

  @property
  def as_floats(self):
    """
    >>> c = Color(127, 127, 0)
    >>> float_tuple = c.as_floats
    >>> round(float_tuple[0], 1), round(float_tuple[1], 1), \
      round(float_tuple[2], 1)
    (0.5, 0.5, 0.0)
    """

    def clamp(r,g,b):
      """
      >>> clamp_tup = clamp(-1.0, 4.0, 0.5)
      >>> round(clamp_tup[0],1), round(clamp_tup[1],1), round(clamp_tup[2],1)
      (0.0, 1.0, 0.5)
      """
      rgb = [r,g,b]
      for i, c in enumerate(rgb):
        if c < 0: c = 0
        if c > 1: c = 1
        rgb[i] = c
      return tuple(rgb)

    return clamp(self.r / 255.0, self.g / 255.0, self.b / 255.0)

  def to_string(self, prefix='#'):
    """
    >>> c = Color(255, 0, 0)
    >>> c.to_string()
    '#f00'
    >>> c = Color(255, 255, 255)
    >>> c.to_string('0x')
    '0xffffff'
    >>> c.to_string('#')
    '#fff'
    """
    c = '%02x' % self.r + '%02x' % self.g + '%02x' % self.b
    if prefix == '#' and c[0] == c[1] and c[2] == c[3] and c[4] == c[5]:
      c = c[0] + c[2] + c[4]
    return str(prefix) + c

  @staticmethod
  def from_string(color_str, prefixes=['#', '0x']):
    """
    >>> c = Color.from_string('0xFf0000')
    >>> c.to_string()
    '#f00'
    >>> c.r, c.g, c.b
    (255, 0, 0)
    """
    c = str(color_str)
    if not any(c.startswith(pfx) for pfx in prefixes):
      return None
    for pfx in prefixes:
      if c.startswith(pfx):
        c = c[len(pfx):]
        break
    if len(c) != 3 and len(c) != 6:
      return None
    elif len(c) == 3:
      c = c[0] + c[0] + c[1] + c[1] + c[2] + c[2]
    r, g, b = c[0:2], c[2:4], c[4:6]
    r, g, b = int(r, 16), int(g, 16), int(b, 16)
    return Color(r=r, g=g, b=b)

if __name__ == "__main__":
  import doctest
  doctest.testmod()

########NEW FILE########
__FILENAME__ = confparse
#!/usr/bin/env python

"""
Replacement for the built-in ``configparser`` module.

See the ``confparse.test`` file for tests and examples.
"""

class ConfParse(object):
  """
  This is a less efficent (probably) and less robust ``ConfigParser`` which
  only exists because that module/class destroys whitespace and comments.
  This one is only meant to handle one file at a time and to preserve the
  original input as much as possible (ie. to make clean diffs).
  """
  def __init__(self, filename):
    self.filename = filename
    text = open(self.filename, 'r').read()
    self.lines = [l.strip() for l in text.split('\n')]

  @staticmethod
  def is_comment(line):
    line = line.strip()
    return line.startswith('#') or line.startswith(';')

  @staticmethod
  def is_group(line):
    line = line.strip()
    return line.startswith('[') and line.endswith(']')

  @staticmethod
  def is_key_value(line):
    fields = line.split('=')
    if len(fields) == 1 or not fields[0].strip() or \
      any(ch in fields[0].strip() for ch in [' ','\t']):
      return False
    return True

  def sections(self):
    sections = []
    for line in self.lines:
      if line.startswith('[') and line.endswith(']'):
        sections.append(line[1:-1])
    return sections

  def has_section(self, section):
    return section in self.sections()

  def options(self, section):
    in_section = False
    options = []
    for line in self.lines:
      if ConfParse.is_comment(line):
        continue
      if ConfParse.is_group(line):
        sect = line[1:-1]
        in_section = True if sect == section else False
        continue
      if in_section and '=' in line:
        key = line.split('=')[0].strip()
        options.append(key)
    return options

  def has_option(self, section, option):
    return option in self.options(section)

  def get(self, section, option):
    in_section = False
    for line in self.lines:
      if ConfParse.is_comment(line):
        continue
      if ConfParse.is_group(line):
        sect = line[1:-1]
        in_section = True if sect == section else False
        continue
      if in_section and '=' in line:
        parts = line.split('=')
        key = parts[0].strip()
        if key == option:
          return '='.join(parts[1:]).strip() if len(parts) > 1 else ''
    return None

  def set(self, section, option, new_value):
    self.add_section(section)
    self.add_option(section, option)
    in_section = False
    new_lines = self.lines[:]
    for i, line in enumerate(self.lines):
      if ConfParse.is_comment(line):
        continue
      if ConfParse.is_group(line):
        sect = line[1:-1]
        in_section = True if sect == section else False
        continue
      if in_section and '=' in line:
        parts = line.split('=')
        key = parts[0]
        value = '='.join(parts[1:])
        if key == option:
          new_lines[i] = '%s=%s' % (key, new_value.strip())
          self.lines = new_lines

  def add_section(self, section):
    if not self.has_section(section):
      self.lines.append('[%s]' % section)

  def add_option(self, section, option):
    self.add_section(section)
    if not self.has_option(section, option):
      for i, line in enumerate(self.lines):
        if ConfParse.is_group(line):
          group = line[1:-1]
          if group == section:
            self.lines.insert(i+1, '%s=' % option)
            break

  def to_dict(self):
    out_dict = {}
    current_group = None
    for line in self.lines:
      if ConfParse.is_comment(line):
        continue
      if ConfParse.is_group(line):
        current_group = line[1:-1]
        out_dict[current_group] = {}
        continue
      if current_group is not None and ConfParse.is_key_value(line):
        fields = line.split('=')
        if len(fields) > 0:
          key = fields[0]
          if len(fields) > 1:
            value = '='.join(fields[1:])
          else:
            value = ''
          out_dict[current_group][key] = value
    return out_dict

  def save(self):
    self.save_as(self.filename)

  def save_as(self, filename):
    open(filename, 'w').write(str(self))

  def __str__(self):
    return '\n'.join(self.lines).rstrip('\n') + '\n'

if __name__ == "__main__":
  import doctest
  doctest.testfile('confparse.test')

########NEW FILE########
__FILENAME__ = mkindex
#!/usr/bin/env python

'''
Creates a JSON index file listing information about all of the color schemes.
Note: requires Python Imaging Library (PIL), ex. 'python-imaging' Debian package.
'''

import os
import sys
import json
import ConfigParser
import hashlib
import base64
import StringIO
import Image, ImageDraw, ImageOps, ImageFilter

SCREENSHOT_BASE = 'https://raw.github.com/geany/geany-themes/master/screenshots/'
SCHEMES_BASE = 'https://raw.github.com/geany/geany-themes/master/colorschemes/'

def get_option(cp, group, key, default=None):
    try: return cp.get(group, key)
    except ConfigParser.Error: return default

def generate_thumbnail(conf_fn, screenshot_dir='screenshots'):
  base = os.path.splitext(os.path.basename(conf_fn))[0]
  png_file = os.path.join(screenshot_dir, '%s.png' % base)

  if not os.path.exists(png_file):
    png_file = os.path.join(screenshot_dir, 'screenshot-missing.png')
    img = Image.open(png_file)
    output = StringIO.StringIO()
    img.save(output, "PNG", optimize=True)
    data = base64.b64encode(output.getvalue())
    output.close()
    return data
  else:
    img = Image.open(png_file)
    img = img.crop((2,2,img.size[1]-2,img.size[1]-2))
    img.thumbnail((64,64), Image.ANTIALIAS)
#-- set to True to save thumbs into screenshots/.thumbs
    do_thumbs = False
    if do_thumbs:
      thumb_dir = os.path.join(screenshot_dir, '.thumbs')
      try:
        os.makedirs(thumb_dir)
      except OSError as e:
        if e.errno != 17: raise
      thumb_fn = os.path.join(thumb_dir, base + '.png')
      img.save(thumb_fn, "PNG", optimize=True)
#--
    output = StringIO.StringIO()
    img.save(output, "PNG", optimize=True)
    data = base64.b64encode(output.getvalue())
    output.close()

  return data

def create_index(themes_dir, screenshot_dir='screenshots'):
    data = {}

    for conf_file in os.listdir(themes_dir):

        if not conf_file.endswith('.conf'):
            continue

        conf_file = os.path.join(themes_dir, conf_file)
        cp = ConfigParser.ConfigParser()
        cp.read(conf_file)

        if not cp.has_section('theme_info'):
            continue

        scheme_name = '.'.join(os.path.basename(conf_file).split('.')[:-1])

        try:
            version = int(get_option(cp, 'theme_info', 'version', '0'))
        except:
            version = '0'

        png_file = os.path.join(screenshot_dir, scheme_name + '.png')
        if os.path.isfile(png_file):
          png_hash = hashlib.md5(open(png_file).read()).hexdigest()
        else:
          png_hash = ''

        compat = get_option(cp, 'theme_info', 'compat', '0.0.0')
        versions = []
        for ver in compat.split(';'):
          ver = [int(v) for v in ver.split('.')] + [0]*3
          ver = '.'.join([ str(v) for v in ver[0:3] ])
          versions.append(ver)

        data[scheme_name] = {
            'name': get_option(cp, 'theme_info', 'name', 'Untitled'),
            'description': get_option(cp, 'theme_info', 'description', ''),
            'version': version,
            'author': get_option(cp, 'theme_info', 'author', 'Unknown Author'),
            'screenshot': '%s%s.png' % (SCREENSHOT_BASE, scheme_name),
            'colorscheme': '%s%s.conf' % (SCHEMES_BASE, scheme_name),
            'thumbnail': generate_thumbnail(conf_file, screenshot_dir),
            'screen_hash': png_hash,
            'scheme_hash': hashlib.md5(open(conf_file).read()).hexdigest(),
            'compat': versions,
        }

    # json.dumps() leaves trailing whitespace on some lines, strip it off
    data = json.dumps(data, indent=2, sort_keys=True).rstrip()
    return '\n'.join([l.rstrip() for l in data.split('\n')]) + '\n'

if __name__ == "__main__":
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    root_dir = os.path.abspath(os.path.dirname(cur_dir))
    screen_dir = os.path.join(root_dir, 'screenshots')
    scheme_dir = os.path.join(root_dir, 'colorschemes')
    index = create_index(scheme_dir, screen_dir)
    sys.stdout.write(index)

########NEW FILE########
