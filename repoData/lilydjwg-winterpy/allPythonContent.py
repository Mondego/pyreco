__FILENAME__ = cpumon
#!/usr/bin/env python3
# vim:fileencoding=utf-8

'''
监视CPU的使用，过高时自动执行命令

2010年7月17日
'''

cmd = 'echo ================== >> ~/tmpfs/cpumon && top -n 1 -b | awk \'{if($4 != 0) print}\' >> ~/tmpfs/cpumon'

import os
import time

def getCPUUsage():
  cpu_before = open('/proc/stat').readline().split()[1:]
  time.sleep(1)
  cpu_after = open('/proc/stat').readline().split()[1:]
  cpu = list(map(lambda x, y: int(y)-int(x), cpu_before, cpu_after))
  # print(cpu_before, cpu_after, sep='\n')
  # print(cpu, sum(cpu))
  return 1 - cpu[3] / sum(cpu)

def monitor(cmd=cmd, threshold=0.9):
  while True:
    usage = getCPUUsage()
    print('CPU Usage: %.2f' % usage)
    if usage > threshold:
      os.system(cmd)

if __name__ == '__main__':
  try:
    monitor(threshold=.5)
  except KeyboardInterrupt:
    print('退出')

########NEW FILE########
__FILENAME__ = fenci
#!/usr/bin/env python3
# vim:fileencoding=utf-8

'''
简单的分词算法

来源： http://scturtle.is-programmer.com/posts/26648.html
'''

class Fenci:
  def __init__(self, dictfile):
    self.d = {}
    d = self.d
    for line in open(dictfile, encoding='gb18030'):
      word, freq = line.split()
      d[word] = int(freq)

  def __call__(self, string):
    d = self.d
    l = len(string)
    p = [0] * (l+1)
    t = [1] * l
    p[l] = 0
    for i in range(l-1, -1, -1):
      for k in range(1, l-i+1):
        new = d.get(string[i:i+k], 0) + p[i+k]
        if new > p[i]:
          p[i] = new
          t[i] = k
    i = 0
    words = []
    while i < l:
      words.append(string[i:i+t[i]])
      i += t[i]
    return words

if __name__ == '__main__':
  import os
  import sys
  import readline
  print('加载数据...', end='')
  sys.stdout.flush()
  # 词库 http://download.csdn.net/source/347899
  fc = Fenci(os.path.expanduser('~/scripts/python/pydata/dict.txt'))
  print('OK.')
  try:
    while True:
      print(' '.join(fc(input('> '))))
  except (EOFError, KeyboardInterrupt):
    pass

########NEW FILE########
__FILENAME__ = gui2term
#!/usr/bin/env python3
# vim:fileencoding=utf-8

'''
为Vim的图形界面配色方案生成256色终端版定义
Generate 256-color definition for Vim's colorscheme
http://www.vim.org/scripts/script.php?script_id=2778
'''

__version__ = 3.03

import os, sys, re, io
import math
from math import *
import warnings

# Global variables {{{1
termcolor = { #{{{2
    16: '#000000',
    17: '#00005f',
    18: '#000087',
    19: '#0000af',
    20: '#0000d7',
    21: '#0000ff',
    22: '#005f00',
    23: '#005f5f',
    24: '#005f87',
    25: '#005faf',
    26: '#005fd7',
    27: '#005fff',
    28: '#008700',
    29: '#00875f',
    30: '#008787',
    31: '#0087af',
    32: '#0087d7',
    33: '#0087ff',
    34: '#00af00',
    35: '#00af5f',
    36: '#00af87',
    37: '#00afaf',
    38: '#00afd7',
    39: '#00afff',
    40: '#00d700',
    41: '#00d75f',
    42: '#00d787',
    43: '#00d7af',
    44: '#00d7d7',
    45: '#00d7ff',
    46: '#00ff00',
    47: '#00ff5f',
    48: '#00ff87',
    49: '#00ffaf',
    50: '#00ffd7',
    51: '#00ffff',
    52: '#5f0000',
    53: '#5f005f',
    54: '#5f0087',
    55: '#5f00af',
    56: '#5f00d7',
    57: '#5f00ff',
    58: '#5f5f00',
    59: '#5f5f5f',
    60: '#5f5f87',
    61: '#5f5faf',
    62: '#5f5fd7',
    63: '#5f5fff',
    64: '#5f8700',
    65: '#5f875f',
    66: '#5f8787',
    67: '#5f87af',
    68: '#5f87d7',
    69: '#5f87ff',
    70: '#5faf00',
    71: '#5faf5f',
    72: '#5faf87',
    73: '#5fafaf',
    74: '#5fafd7',
    75: '#5fafff',
    76: '#5fd700',
    77: '#5fd75f',
    78: '#5fd787',
    79: '#5fd7af',
    80: '#5fd7d7',
    81: '#5fd7ff',
    82: '#5fff00',
    83: '#5fff5f',
    84: '#5fff87',
    85: '#5fffaf',
    86: '#5fffd7',
    87: '#5fffff',
    88: '#870000',
    89: '#87005f',
    90: '#870087',
    91: '#8700af',
    92: '#8700d7',
    93: '#8700ff',
    94: '#875f00',
    95: '#875f5f',
    96: '#875f87',
    97: '#875faf',
    98: '#875fd7',
    99: '#875fff',
    100: '#878700',
    101: '#87875f',
    102: '#878787',
    103: '#8787af',
    104: '#8787d7',
    105: '#8787ff',
    106: '#87af00',
    107: '#87af5f',
    108: '#87af87',
    109: '#87afaf',
    110: '#87afd7',
    111: '#87afff',
    112: '#87d700',
    113: '#87d75f',
    114: '#87d787',
    115: '#87d7af',
    116: '#87d7d7',
    117: '#87d7ff',
    118: '#87ff00',
    119: '#87ff5f',
    120: '#87ff87',
    121: '#87ffaf',
    122: '#87ffd7',
    123: '#87ffff',
    124: '#af0000',
    125: '#af005f',
    126: '#af0087',
    127: '#af00af',
    128: '#af00d7',
    129: '#af00ff',
    130: '#af5f00',
    131: '#af5f5f',
    132: '#af5f87',
    133: '#af5faf',
    134: '#af5fd7',
    135: '#af5fff',
    136: '#af8700',
    137: '#af875f',
    138: '#af8787',
    139: '#af87af',
    140: '#af87d7',
    141: '#af87ff',
    142: '#afaf00',
    143: '#afaf5f',
    144: '#afaf87',
    145: '#afafaf',
    146: '#afafd7',
    147: '#afafff',
    148: '#afd700',
    149: '#afd75f',
    150: '#afd787',
    151: '#afd7af',
    152: '#afd7d7',
    153: '#afd7ff',
    154: '#afff00',
    155: '#afff5f',
    156: '#afff87',
    157: '#afffaf',
    158: '#afffd7',
    159: '#afffff',
    160: '#d70000',
    161: '#d7005f',
    162: '#d70087',
    163: '#d700af',
    164: '#d700d7',
    165: '#d700ff',
    166: '#d75f00',
    167: '#d75f5f',
    168: '#d75f87',
    169: '#d75faf',
    170: '#d75fd7',
    171: '#d75fff',
    172: '#d78700',
    173: '#d7875f',
    174: '#d78787',
    175: '#d787af',
    176: '#d787d7',
    177: '#d787ff',
    178: '#d7af00',
    179: '#d7af5f',
    180: '#d7af87',
    181: '#d7afaf',
    182: '#d7afd7',
    183: '#d7afff',
    184: '#d7d700',
    185: '#d7d75f',
    186: '#d7d787',
    187: '#d7d7af',
    188: '#d7d7d7',
    189: '#d7d7ff',
    190: '#d7ff00',
    191: '#d7ff5f',
    192: '#d7ff87',
    193: '#d7ffaf',
    194: '#d7ffd7',
    195: '#d7ffff',
    196: '#ff0000',
    197: '#ff005f',
    198: '#ff0087',
    199: '#ff00af',
    200: '#ff00d7',
    201: '#ff00ff',
    202: '#ff5f00',
    203: '#ff5f5f',
    204: '#ff5f87',
    205: '#ff5faf',
    206: '#ff5fd7',
    207: '#ff5fff',
    208: '#ff8700',
    209: '#ff875f',
    210: '#ff8787',
    211: '#ff87af',
    212: '#ff87d7',
    213: '#ff87ff',
    214: '#ffaf00',
    215: '#ffaf5f',
    216: '#ffaf87',
    217: '#ffafaf',
    218: '#ffafd7',
    219: '#ffafff',
    220: '#ffd700',
    221: '#ffd75f',
    222: '#ffd787',
    223: '#ffd7af',
    224: '#ffd7d7',
    225: '#ffd7ff',
    226: '#ffff00',
    227: '#ffff5f',
    228: '#ffff87',
    229: '#ffffaf',
    230: '#ffffd7',
    231: '#ffffff',
    232: '#080808',
    233: '#121212',
    234: '#1c1c1c',
    235: '#262626',
    236: '#303030',
    237: '#3a3a3a',
    238: '#444444',
    239: '#4e4e4e',
    240: '#585858',
    241: '#626262',
    242: '#6c6c6c',
    243: '#767676',
    244: '#808080',
    245: '#8a8a8a',
    246: '#949494',
    247: '#9e9e9e',
    248: '#a8a8a8',
    249: '#b2b2b2',
    250: '#bcbcbc',
    251: '#c6c6c6',
    252: '#d0d0d0',
    253: '#dadada',
    254: '#e4e4e4',
    255: '#eeeeee',
}

# regexes {{{2
highlight_word = re.compile(r"(?P<quote>')?(?(quote)[\w ]|[\w,#])+(?(quote)'|)")
re_hexcolor = re.compile('^#[0-9a-fA-F]{6}$')
re_hiline = re.compile('^\s*hi\w*\s+(?!link\b)[A-Z]\w+')

# others {{{2
name2rgb = {}
Normal = None

# Functions {{{1
def getRgbtxt(): # {{{2
  scriptdir = os.path.dirname(os.path.abspath(sys.argv[0]))
  if os.path.isfile('rgb.txt'):
    rgbfile = 'rgb.txt'
  elif os.path.isfile(os.path.join(scriptdir, 'rgb.txt')):
    rgbfile = os.path.join(scriptdir, 'rgb.txt')
  else:
    try:
      import subprocess
      rgbfile = io.StringIO(subprocess.check_output(['locate', '-b', '--regex', '-e', '^rgb\.txt$']).decode()).readline().strip()
    except:
      warnings.warn("rgb.txt not found, color names will cause errors", Warning)
      rgbfile = None
  return rgbfile

def color_norm(c): # {{{2
  return tuple(int(x, 16)/255.0 for x in (c[1:3], c[3:5], c[5:7]))

def loadRgb(): # {{{2
  rgbfile = getRgbtxt()
  if rgbfile is None:
    return
  rgbtxt = re.compile('^(\d+)\s+(\d+)\s+(\d+)\s+([\w\s]+)$')
  try:
    for l in open(rgbfile):
      if not l.startswith('!'):
        r, g, b, name = l.split(None, 3)
        name = name.strip().lower()
        if ' ' in name:
          name = "'%s'" % name
        name2rgb[name] = int(r), int(g), int(b)
  except IOError:
    print('Failed to open rgb file', rgbfile, file=sys.stderr)

def convert(infile, outfile): # {{{2
  global Normal

  infile = open(infile)
  for l in infile:
    if l.lower().find('normal') != -1:
      Normal = Group(l)
      infile.seek(0)
      break

  outfile = open(outfile, 'w')
  for l in infile:
    if re_hiline.match(l):
      outfile.write(str(Group(l)))
    else:
      outfile.write(l)

def delta_e_cie2000(color1, color2): # {{{2
  """
  Calculates the Delta E (CIE2000) of two colors.

  Stolen from colormath.color_objects
  """
  Kl = Kc = Kh = 1
  L1, a1, b1 = color1.tolab()
  L2, a2, b2 = color2.tolab()

  avg_Lp = (L1 + L2) / 2.0
  C1 = sqrt(pow(a1, 2) + pow(b1, 2))
  C2 = sqrt(pow(a2, 2) + pow(b2, 2))
  avg_C1_C2 = (C1 + C2) / 2.0

  G = 0.5 * (1 - sqrt(pow(avg_C1_C2 , 7.0) / (pow(avg_C1_C2, 7.0) + pow(25.0, 7.0))))

  a1p = (1.0 + G) * a1
  a2p = (1.0 + G) * a2
  C1p = sqrt(pow(a1p, 2) + pow(b1, 2))
  C2p = sqrt(pow(a2p, 2) + pow(b2, 2))
  avg_C1p_C2p =(C1p + C2p) / 2.0

  if degrees(atan2(b1,a1p)) >= 0:
    h1p = degrees(atan2(b1,a1p))
  else:
    h1p = degrees(atan2(b1,a1p)) + 360

  if degrees(atan2(b2,a2p)) >= 0:
    h2p = degrees(atan2(b2,a2p))
  else:
    h2p = degrees(atan2(b2,a2p)) + 360

  if fabs(h1p - h2p) > 180:
    avg_Hp = (h1p + h2p + 360) / 2.0
  else:
    avg_Hp = (h1p + h2p) / 2.0

  T = 1 - 0.17 * cos(radians(avg_Hp - 30)) + 0.24 * cos(radians(2 * avg_Hp)) + 0.32 * cos(radians(3 * avg_Hp + 6)) - 0.2  * cos(radians(4 * avg_Hp - 63))

  diff_h2p_h1p = h2p - h1p
  if fabs(diff_h2p_h1p) <= 180:
    delta_hp = diff_h2p_h1p
  elif (fabs(diff_h2p_h1p) > 180) and (h2p <= h1p):
    delta_hp = diff_h2p_h1p + 360
  else:
    delta_hp = diff_h2p_h1p - 360

  delta_Lp = L2 - L1
  delta_Cp = C2p - C1p
  delta_Hp = 2 * sqrt(C2p * C1p) * sin(radians(delta_hp) / 2.0)

  S_L = 1 + ((0.015 * pow(avg_Lp - 50, 2)) / sqrt(20 + pow(avg_Lp - 50, 2.0)))
  S_C = 1 + 0.045 * avg_C1p_C2p
  S_H = 1 + 0.015 * avg_C1p_C2p * T

  delta_ro = 30 * exp(-(pow(((avg_Hp - 275) / 25), 2.0)))
  R_C = sqrt((pow(avg_C1p_C2p, 7.0)) / (pow(avg_C1p_C2p, 7.0) + pow(25.0, 7.0)));
  R_T = -2 * R_C * sin(2 * radians(delta_ro))

  delta_E = sqrt(pow(delta_Lp /(S_L * Kl), 2) + pow(delta_Cp /(S_C * Kc), 2) + pow(delta_Hp /(S_H * Kh), 2) + R_T * (delta_Cp /(S_C * Kc)) * (delta_Hp / (S_H * Kh)))

  return delta_E

# Classes {{{1
class color: # {{{2
  def __init__(self, colorstring, g=None, b=None): # {{{3
    '''argument should be either #rrggbb or three integers'''
    if isinstance(colorstring, str):
      if re_hexcolor.match(colorstring):
        self.value = color_norm(colorstring)
      else:
        r, g, b = name2rgb[colorstring]
        self.value = r / 255, g / 255, b / 255
    else:
      r = colorstring
      self.value = r / 255, g / 255, b / 255

  @property
  def termcolor(self): # {{{3
    '''selects the nearest xterm color for a rgb value ('color' class)'''
    best_match = 0
    smallest_distance = 10000000

    for c in range(16, 256):
      d = delta_e_cie2000(color(termcolor[c]), self)

      if d < smallest_distance:
        smallest_distance = d
        best_match = c

    return best_match

  def tolab(self):
    # RGB to XYZ
    # http://www.easyrgb.com/index.php?X=MATH&H=02#text2
    r = self.value[0]
    g = self.value[1]
    b = self.value[2]

    if r > 0.04045 :
      r = ((r + 0.055) / 1.055) ** 2.4
    else:
      r = r / 12.92
    if g > 0.04045 :
      g = ((g + 0.055) / 1.055) ** 2.4
    else:
      g = g / 12.92
    if b > 0.04045 :
      b = ((b + 0.055) / 1.055) ** 2.4
    else:
      b = b / 12.92

    r = r * 100
    g = g * 100
    b = b * 100

    X = r * 0.4124 + g * 0.3576 + b * 0.1805
    Y = r * 0.2126 + g * 0.7152 + b * 0.0722
    Z = r * 0.0193 + g * 0.1192 + b * 0.9505

    # XYZ to Lab
    # http://www.easyrgb.com/index.php?X=MATH&H=07#text7
    X /=  95.047
    Y /= 100.000
    Z /= 108.883

    if (X > 0.008856):
      X = X ** (1/3)
    else:
      X = (7.787 * X) + (16 / 116)
    if (Y > 0.008856):
      Y = Y ** (1/3)
    else:
      Y = (7.787 * Y) + (16 / 116)
    if (Z > 0.008856):
      Z = Z ** (1/3)
    else:
      Z = (7.787 * Z) + (16 / 116)

    L = (116 * Y) - 16
    a = 500 * (X - Y)
    b = 200 * (Y - Z)

    return L, a, b

class Group: # {{{2
  def __init__(self, line): # {{{3
    words = tuple(highlight_word.finditer(line))
    self.name = words[1].group(0)
    self.attr = {}
    afterequals = False
    for i in words[2:]:
      if afterequals:
        self.attr[key] = i.group(0).lower()
      else:
        key = i.group(0).lower()
      afterequals = not afterequals

    self.updateterm()

  def updateterm(self): # {{{3
    gui = self.attr.get('gui')
    if gui:
      attrs = gui.split(',')
      # italic is displayed as reversed in terminal
      try:
        attrs.remove('italic')
      except ValueError:
        pass
      if attrs:
        self.attr['cterm'] = ','.join(attrs)
    elif self.name.lower() == 'cursorline':
      self.attr['cterm'] = 'none'

    guifg = self.attr.get('guifg')
    if guifg:
      if guifg in ('fg', 'foreground'):
        guifg = Normal.attr['guifg']
      elif guifg in ('bg', 'background'):
        guifg = Normal.attr['guibg']
      elif guifg == 'none':
        try:
          del self.attr['ctermfg']
        except KeyError:
          pass
      else:
        self.attr['ctermfg'] = color(guifg).termcolor
    else:
      try:
        del self.attr['ctermfg']
      except KeyError:
        pass

    guibg = self.attr.get('guibg')
    if guibg:
      if guibg in ('fg', 'foreground'):
        guibg = Normal.attr['guifg']
      elif guibg in ('bg', 'background'):
        guibg = Normal.attr['guibg']
      elif guibg == 'none':
        try:
          del self.attr['ctermbg']
        except KeyError:
          pass
      else:
        self.attr['ctermbg'] = color(guibg).termcolor
    else:
      try:
        del self.attr['ctermbg']
      except KeyError:
        pass

  def __str__(self): # {{{3
    ret = ['highlight', self.name]
    attr = self.attr
    for k in sorted(attr.keys(), reverse=True):
      # It's reported that 'none' with GVIM will cause E254
      if attr[k] == 'none':
        ret.append('%s=NONE' % k)
      else:
        ret.append('%s=%s' % (k, attr[k]))
    return ' '.join(ret) + '\n'

def test(): # {{{1
  print(Group('highlight Title guifg=#ffc0cb gui=bold ctermbg=none cterm=bold'))

if __name__ == '__main__': # {{{1
  # test()
  # sys.exit()
  if len(sys.argv) == 3:
    loadRgb()
    try:
      convert(sys.argv[1], sys.argv[2])
    except IOError:
      print('Error opening file', file=sys.stderr)
      sys.exit(2)
  else:
    print('Usage: gui2term.py SRC_FILE DEST_FILE')
    sys.exit(1)

# vim:se fdm=marker:

########NEW FILE########
__FILENAME__ = jdmb
#!/usr/bin/env python3
# fileencoding=utf-8

'''
从 fcitx码表导出文件 转换成极点五笔码表文件
'''

import os
import struct, io
from datetime import datetime

class jdmb:
  def __init__(self, infile, outfile):
    self.infname = infile
    self.outfile = open(outfile, 'wb')

  def run(self):
    self.header()
    self.header2()
    self.main()
    self.doIndex()

  def header(self):
    h = '百合五笔小企鹅输入法词库%s版 for 极点五笔UniCode版本\r\n生成日期:%s'
    h = h % (datetime.fromtimestamp(os.path.getmtime(self.infname)).strftime('%Y%m%d'),
        datetime.today().strftime('%Y-%m-%d %H:%M'))

    self.outfile.write(b'Freeime Dictionary V5.0')
    self.outfile.write(h.encode('utf-16le'))
    self.outfile.write(b'\x00'*(0xe7 - self.outfile.tell()))
    self.outfile.write(b'\x01')
    self.outfile.write(b'\x00'*(0x11f - self.outfile.tell()))
    self.outfile.write(b'\x1a')

  def header2(self):
    h = 'abcdefghijklmnopqrstuvwxyzz'.encode('utf-16le')
    h = h + (0x56 - len(h)) * b'\x00'
    self.outfile.write(h)

    h = 'p11+p21+p31+p32'.encode('utf-16le')
    h = h + (0x3e - len(h)) * b'\x00'
    self.outfile.write(h)

    self.outfile.write(b'z\x00z\x00')

  def main(self):
    '''将主体数据存到 self.maindata'''
    self.maindata = io.BytesIO()
    found = False
    index = [[['A', 0]], [['AA', 0]], [['AAA', 0]]]
    for l in open(self.infname):
      if not found:
        if l == '[数据]\n':
          found = True
        continue
      d = l.rstrip('\n').split(' ')
      # 索引用
      try:
        if d[0][0] != index[0][-1][0][0]:
          index[0].append([d[0], self.maindata.tell()])
        if d[0][1] and d[0][:2] != index[1][-1][0][:2]:
          index[1].append([d[0], self.maindata.tell()])
        if d[0][2] and d[0][:3] != index[2][-1][0][:3]:
          index[2].append([d[0], self.maindata.tell()])
      except IndexError:
        pass
      d[0] = d[0].encode('ascii')
      d[1] = d[1].encode('utf-16le')
      e = struct.pack('<3B', len(d[0]), len(d[1]), 0x64)
      self.maindata.write(e)
      self.maindata.write(d[0] + d[1])
    del index[0][0]
    del index[1][0]
    del index[2][0]
    self.index = index

  def doIndex(self):
    chars = 'abcdefghijklmnopqrstuvwxyz'
    cursor = 0
    # 单字母索引
    for i in chars:
      try:
        if self.index[0][cursor][0] == i:
          b = struct.pack('<I', self.index[0][cursor][1] + 0x1b620)
          self.outfile.write(b)
          cursor += 1
        else:
          self.outfile.write(b'\xff\xff\xff\xff')
      except IndexError:
        self.outfile.write(b'\xff\xff\xff\xff')

    bichars = [i+j for i in chars for j in chars]
    cursor = 0
    for i in bichars:
      try:
        if self.index[1][cursor][0][:2] == i:
          b = struct.pack('<I', self.index[1][cursor][1] + 0x1b620)
          self.outfile.write(b)
          cursor += 1
        else:
          self.outfile.write(b'\xff\xff\xff\xff')
      except IndexError:
        self.outfile.write(b'\xff\xff\xff\xff')

    trichars = [i+j+k for i in chars for j in chars for k in chars]
    cursor = 0
    for i in trichars:
      try:
        if self.index[2][cursor][0][:3] == i:
          b = struct.pack('<I', self.index[2][cursor][1] + 0x1b620)
          self.outfile.write(b)
          cursor += 1
        else:
          self.outfile.write(b'\xff\xff\xff\xff')
          # print(i, self.index[2][cursor][0][:3])
      except IndexError:
        self.outfile.write(b'\xff\xff\xff\xff')

    hw = 0x1b620 - self.outfile.tell()
    self.outfile.write(b'\xff'*hw)
    self.maindata.seek(0)
    b = self.maindata.read(1024)
    while b:
      self.outfile.write(b)
      b = self.maindata.read(1024)

def test():
  '''测试用'''
  a = jdmb('lily', 'freeime.mb')
  a.header()
  a.header2()
  a.main()
  a.doIndex()
  return a

if __name__ == '__main__':
  import sys
  if len(sys.argv) == 3:
    jd = jdmb(*sys.argv[1:])
    jd.run()
  else:
    print('用法： jdmb.py fcitx码表导出文件 输出文件')
    sys.exit(1)


########NEW FILE########
__FILENAME__ = mongo
#!/usr/bin/env python3

import sys
import os
from pprint import pprint
import subprocess
import datetime
import argparse

try:
  # pymongo 2.4+
  from pymongo.mongo_client import MongoClient
except ImportError:
  from pymongo import Connection as MongoClient
import pymongo.cursor

from cli import repl

host = 'localhost'
port = 27017
db = 'test'

import locale
locale.setlocale(locale.LC_ALL, '')
del locale

env = os.environ.copy()
if env['TERM'].find('256') != -1:
  env['TERM'] = env['TERM'].split('-', 1)[0]

def displayfunc(value):
  if value is None:
    v['_'] = None
    return

  if isinstance(value, pymongo.cursor.Cursor):
    p = subprocess.Popen(['colorless', '-l', 'python'], stdin=subprocess.PIPE,
                        universal_newlines=True, env=env)
    value = list(value)
    pprint(value, stream=p.stdin)
    p.stdin.close()
    p.wait()
  else:
    pprint(value)
  v['_'] = value

def main(kwargs):
  global db, conn
  conn = MongoClient(host=host, port=port, **kwargs)
  db = conn[db]

  rc = os.path.expanduser('~/.mongorc.py')
  if os.path.isfile(rc):
    exec(compile(open(rc, 'rb').read(), '.mongorc.py', 'exec'))

  global v
  v = globals().copy()
  v.update(locals())
  v['_'] = None
  del v['repl'], v['kwargs'], v['main'], v['host'], v['port']
  del v['displayfunc'], v['subprocess'], v['env']
  del v['__name__'], v['__cached__'], v['__doc__'], v['__file__'], v['__package__']
  del v['rc'], v['argparse']
  sys.displayhook = displayfunc

  repl(
    v, os.path.expanduser('~/.mongo_history'),
    banner = 'Python MongoDB console',
  )

if __name__ == '__main__':
  try:
    import setproctitle
    setproctitle.setproctitle('mongo.py')
    del setproctitle
  except ImportError:
    pass

  parser = argparse.ArgumentParser(description='MongoDB Shell in Python')
  parser.add_argument('--slaveok', action='store_true')
  parser.add_argument('dburl', nargs='?', default=None,
                      help='the database to use instead of localhost\'s test')
  args = parser.parse_args()

  kwargs = {}
  if args.dburl:
    dburl = args.dburl
    if '/' in dburl:
      host, db = dburl.split('/', 1)
      if ':' in host:
        host, port = host.split(':', 1)
        port = int(port)
    else:
      db = dburl
  if args.slaveok:
    kwargs['slave_okay'] = True

  main(kwargs)

########NEW FILE########
__FILENAME__ = procmail
#!/usr/bin/env python3
# vim:fileencoding=utf-8

import sys
import re
import io
from email import header

from simplelex import Token, Lex
from mailutils import decode_multiline_header

reply = Token(r'R[Ee]:\s?|[回答][复覆][：:]\s?', 're')
ottag = Token(r'\[OT\]\s?', 'ot', flags=re.I)
tag = Token(r'\[([\w._-]+)[^]]*\]\s?', 'tag')
lex = Lex((reply, ottag, tag))

def reformat(s):
  tokens, left = lex.parse(s)
  if not tokens:
    return

  isre = False
  tag = None
  ot = False
  usertag = []
  for tok in tokens:
    if tok.idtype == 're':
      isre = True
    elif tok.idtype == 'ot':
      ot = True
    elif tok.idtype == 'tag':
      tag_text = tok.match.group(1)
      if tag and tag_text != tag[1:-2] or tag_text.lower() == 'bug':
        usertag.append(tok.data)
      else:
        tag = '[%s] ' % tag_text
    else:
      sys.exit('error: unknown idtype: %s' % tok.idtype)

  if isre:
    ret = 'Re: '
  else:
    ret = ''
  if tag:
    ret += tag
  if ot:
    ret += '[OT]'
  ret += ''.join(usertag) + left
  if ret != s:
    return ret

def stripSeq(input):
  subject = None
  while True:
    l = next(input)
    if l.startswith('Subject: '):
      # Subject appears
      subject = l
      continue
    elif subject and l[0] in ' \t':
      # Subject continues
      subject += l
    elif subject:
      # Subject ends
      s = subject[9:]
      s = decode_multiline_header(s)
      reformatted = reformat(s)
      if not reformatted:
        yield subject
      else:
        yield 'Subject: ' + header.Header(reformatted, 'utf-8').encode() + '\n'
      subject = None
      yield l
    elif l.strip() == '':
      yield l
      # mail body
      yield from input
    else:
      yield l

if __name__ == '__main__':
  stdout = io.TextIOWrapper(sys.stdout.buffer,
                            encoding='utf-8', errors='surrogateescape')
  stdin = io.TextIOWrapper(sys.stdin.buffer,
                           encoding='utf-8', errors='surrogateescape')
  stdout.writelines(stripSeq(iter(stdin)))

########NEW FILE########
__FILENAME__ = algorithm
'''一些算法'''

def LevenshteinDistance(s, t):
  '''字符串相似度算法（Levenshtein Distance算法）
  
一个字符串可以通过增加一个字符，删除一个字符，替换一个字符得到另外一个
字符串，假设，我们把从字符串A转换成字符串B，前面3种操作所执行的最少
次数称为AB相似度

这算法是由俄国科学家Levenshtein提出的。
Step Description
1 Set n to be the length of s.
  Set m to be the length of t.
  If n = 0, return m and exit.
  If m = 0, return n and exit.
  Construct a matrix containing 0..m rows and 0..n columns.
2 Initialize the first row to 0..n.
  Initialize the first column to 0..m.
3 Examine each character of s (i from 1 to n).
4 Examine each character of t (j from 1 to m).
5 If s[i] equals t[j], the cost is 0.
  If s[i] doesn't equal t[j], the cost is 1.
6 Set cell d[i,j] of the matrix equal to the minimum of:
  a. The cell immediately above plus 1: d[i-1,j] + 1.
  b. The cell immediately to the left plus 1: d[i,j-1] + 1.
  c. The cell diagonally above and to the left plus the cost:
     d[i-1,j-1] + cost.
7 After the iteration steps (3, 4, 5, 6) are complete, the distance is
  found in cell d[n,m]. '''

  m, n = len(s), len(t)
  if not (m and n):
    return m or n

  # 构造矩阵
  matrix = [[0 for i in range(n+1)] for j in range(m+1)]
  matrix[0] = list(range(n+1))
  for i in range(m+1):
    matrix[i][0] = i

  for i in range(m):
    for j in range(n):
      cost = int(s[i] != t[j])
      # 因为 Python 的字符索引从 0 开始
      matrix[i+1][j+1] = min(
          matrix[i][j+1] + 1, # a.
          matrix[i+1][j] + 1, # b.
          matrix[i][j] + cost # c.
          )

  return matrix[m][n]

difference = LevenshteinDistance

def mprint(matrix, width=3):
  '''打印矩阵'''

  for i in matrix:
    for j in i:
      print('{0:>{1}}'.format(j, width), end='')
    print()

def primes(start, stop):
  '''生成质数'''
  if start > stop:
    start, stop = stop, start
  if start <= 1:
    start = 2
  if start == 2:
    yield 2
    start += 1

  while start <= stop:
    for i in range(3, int(start**0.5), 2):
      if start % i == 0:
        break
    else:
      yield start
    start += 2

def 分解质因数(num):
  if num < 2:
    raise ValueError('需要大于 1 的整数')

  factors = []
  for i in primes(2, num+1):
    while num % i == 0:
      num /= i
      factors.append(i)
  return factors

def nmin(s, howmany):
  '''选取 howmany 个最小项
  
来源于 Python2.6 的文档
(tutorial/stdlib2.html#tools-for-working-with-lists)'''

  from heapq import heapify, heappop
  heapify(s)        # rearrange the list into heap order
  # fetch the smallest entries
  return [heappop(s) for i in range(howmany)]

def between(seq, start, end):
  '''获取 seq 中 start 和 end 之间的项

seq 应当已经排序过，并且是递增的'''

  l = 二分搜索(seq, start)
  if l < 0:
    l = 0
  r = 二分搜索(seq, end)
  try:
    while end == seq[r]:
      r += 1
  except IndexError:
    pass
  return seq[l:r]

def 二分搜索(l, tgt, gt=None):
  '''查找 l 中不比 tgt 小的位置
  
l 应当已经排序过，并且是递增的
lt(tgt,l[i]) 当 tgt 比 l[i] 大时返回真
'''
  # tgt 在 l 中存在
  # if tgt in l:
    # return l.index(tgt)
  # 这样很耗时的

  left = 0
  right = len(l)-1
  middle = -1
  if not gt:
    # 放在这里，只需要判断一次
    while left <= right:
      middle = (left+right) // 2
      if not tgt > l[middle]:
        right = middle - 1
      else:
        left = middle + 1
    try:
      while tgt == l[middle] and middle >= 0:
        middle -= 1
    except IndexError:
      pass
  else:
    while left <= right:
      middle = (left+right) // 2
      if not gt(tgt, l[middle]):
        right = middle - 1
      else:
        left = middle + 1
    try:
      while not gt(tgt, l[middle]) and middle >= 0:
        middle -= 1
    except IndexError:
      pass
  return middle+1

def 球面坐标到直角坐标(r, alpha, beta):
  from math import cos, sin
  x = r * cos(beta) * cos(alpha)
  y = r * cos(beta) * sin(alpha)
  z = r * sin(beta)
  return (x, y, z)

def md5(string):
  '''求 string (UTF-8) 的 md5 (hex 表示)'''
  import hashlib
  m = hashlib.md5()
  m.update(string.encode('utf-8'))
  return m.hexdigest()


########NEW FILE########
__FILENAME__ = apkinfo
#!/usr/bin/env python3

import os
import sys
import tempfile
from subprocess import check_call as run
from subprocess import Popen, PIPE, CalledProcessError
from xml.etree import ElementTree as ET
from collections import namedtuple

from myutils import at_dir, firstExistentPath

VER_ATTR = '{http://schemas.android.com/apk/res/android}versionName'
ICON_ATTR = '{http://schemas.android.com/apk/res/android}icon'
NAME_ATTR = '{http://schemas.android.com/apk/res/android}label'

ApkInfo = namedtuple('ApkInfo', 'id version name icon')
class ApktoolFailed(Exception): pass

def read_string(s):
  if s and s.startswith('@string/'):
    sid = s.split('/', 1)[1]
    for d in ('values-zh-rCN', 'values-zh-rTW', 'values-zh-rHK', 'values'):
      if not os.path.isdir(d):
        continue
      strings = ET.parse(os.path.join(d, 'strings.xml')).getroot()
      val = strings.findtext('string[@name="%s"]' % sid)
      if val:
        return val
  return s

def apkinfo(apk):
  with tempfile.TemporaryDirectory('apk') as tempdir:
    try:
      run(["apktool", "d", "-f", "-s", apk, tempdir])
    except CalledProcessError:
      raise ApktoolFailed

    with at_dir(tempdir):
      manifest = ET.parse('AndroidManifest.xml').getroot()
      package_id = manifest.get('package')
      package_ver = manifest.get(VER_ATTR)

      app = manifest.find('application')
      icon = app.get(ICON_ATTR)
      name = app.get(NAME_ATTR)

      if os.path.isdir('res'):
        with at_dir('res'):
          name = read_string(name)
          package_ver = read_string(package_ver)

          if icon and icon.startswith('@'):
            dirname, iconname = icon[1:].split('/', 1)
            iconfile = firstExistentPath(
              '%s/%s.png' % (d, iconname) for d in
              (dirname + x for x in
               ('-xxhdpi', '-xhdpi', '-hdpi', '', '-nodpi'))
            )
            with open(iconfile, 'rb') as f:
              icon = f.read()

    return ApkInfo(package_id, package_ver, name, icon)

def showInfo(apks):
  for apk in apks:
    try:
      info = apkinfo(apk)
    except ApktoolFailed:
      print('E: apktool failed.')
      continue

    print('I: displaying info as image...')
    display = Popen(['display', '-'], stdin=PIPE)
    convert = Popen([
      'convert', '-alpha', 'remove',
      '-font', '文泉驿正黑', '-pointsize', '12', '-gravity', 'center',
      'label:' + info.id,
      'label:' + info.version,
      '-' if info.icon else 'label:(No Icon)',
      'label:' + (info.name or '(None)'),
      '-append', 'png:-',
    ], stdin=PIPE, stdout=display.stdin)
    if info.icon:
      convert.stdin.write(info.icon)
    convert.stdin.close()
    convert.wait()
    display.stdin.close()
    display.wait()

if __name__ == '__main__':
  showInfo(sys.argv[1:])

########NEW FILE########
__FILENAME__ = archpkg
import os
from collections import defaultdict, namedtuple
import subprocess
import re

from pkg_resources import parse_version

class PkgNameInfo(namedtuple('PkgNameInfo', 'name, version, release, arch')):
  def __lt__(self, other):
    if self.name != other.name or self.arch != other.arch:
      return NotImplemented
    if self.version != other.version:
      return parse_version(self.version) < parse_version(other.version)
    return int(self.release) < int(other.release)

  def __gt__(self, other):
    # No, try the other side please.
    return NotImplemented

  @property
  def fullversion(self):
    return '%s-%s' % (self.version, self.release)

  @classmethod
  def parseFilename(cls, filename):
    return cls(*trimext(filename, 3).rsplit('-', 3))

def trimext(name, num=1):
  for i in range(num):
    name = os.path.splitext(name)[0]
  return name

def get_pkgname_with_bash(PKGBUILD):
  script = '''\
. '%s'
echo ${pkgname[*]}''' % PKGBUILD
  # Python 3.4 has 'input' arg for check_output
  p = subprocess.Popen(['bash'], stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE)
  output = p.communicate(script.encode('latin1'))[0].decode('latin1')
  ret = p.wait()
  if ret != 0:
    raise subprocess.CalledProcessError(
      ret, ['bash'], output)
  return output.split()

def _run_bash(script):
  p = subprocess.Popen(['bash'], stdin=subprocess.PIPE)
  p.communicate(script.encode('latin1'))
  ret = p.wait()
  if ret != 0:
    raise subprocess.CalledProcessError(
      ret, ['bash'])

def get_aur_pkgbuild_with_bash(name):
  script = '''\
. /usr/lib/yaourt/util.sh
. /usr/lib/yaourt/aur.sh
init_color
aur_get_pkgbuild '%s' ''' % name
  _run_bash(script)

def get_abs_pkgbuild_with_bash(name):
  script = '''\
. /usr/lib/yaourt/util.sh
. /usr/lib/yaourt/abs.sh
init_paths
init_color
arg=$(pacman -Sp --print-format '%%r/%%n' '%s')
RSYNCOPT="$RSYNCOPT -O"
abs_get_pkgbuild "$arg" ''' % name
  _run_bash(script)

pkgfile_pat = re.compile(r'(?:^|/).+-[^-]+-\d+-(?:\w+)\.pkg\.tar\.xz$')

########NEW FILE########
__FILENAME__ = ard
'''
ard 解码

来源 http://www.wowstory.com/

2011年1月12日
'''

from ctypes import *
from myutils import loadso
import sys

_ard = loadso('_ard.so')
_ard.ard.argtypes = (c_char_p,) * 2
_ard.ard.restype = c_char_p

def ard(str1, str2):
  return _ard.ard(str1.encode('utf-8'), str2.encode('utf-8')).decode('utf-8')

if __name__ == '__main__':
  print(ard(sys.argv[1], sys.argv[2]))

########NEW FILE########
__FILENAME__ = archive
import os
import logging
import subprocess

from . import base

__all__ = ['p7zip', 'tar']

logger = logging.getLogger(__name__)

global_exclude_7z = ['-xr!' + x for x in base.global_exclude]
global_exclude_tar = ['--exclude=' + x for x in base.global_exclude]

def p7zip(name, dstfile, sources, exclude=(), opts=()):
  if isinstance(sources, str):
    sources = [sources]
  cmd = ['7z', 'u', dstfile]
  cmd.extend(global_exclude_7z)
  if exclude:
    exclude = ['-xr!' + x for x in exclude]
    cmd.extend(exclude)
  if opts:
    cmd.extend(opts)
  cmd.extend(sources)

  retcode = base.run_command(cmd)
  if retcode == 0:
    logger.info('7z job %s succeeded', base.bold(name))
  else:
    logger.error('7z job %s failed with code %d',
                 base.bold(name), retcode)
  return not retcode

def tarxz(name, dstfile, sources, sudo=True):
  '''use tar & xz to archive, mainly for system files'''
  if isinstance(sources, str):
    sources = [sources]
  if sudo:
    cmd = ['sudo']
  else:
    cmd = []
  cmd.extend(['tar', 'cvJf', dstfile])
  cmd.extend(global_exclude_tar)
  cmd.extend(sources)

  retcode = base.run_command(cmd)
  if retcode == 0:
    logger.info('tar job %s succeeded', base.bold(name))
  else:
    logger.error('tar job %s failed with code %d',
                 base.bold(name), retcode)
  return not retcode

def tar7z(name, dstfile, sources, password=None):
  '''use tar & 7z to archive, mainly for encrypted config files'''
  if isinstance(sources, str):
    sources = [sources]
  cmd = ['tar', 'cv']
  cmd.extend(global_exclude_tar)
  cmd.extend(sources)

  try:
    os.unlink(dstfile) # or 7z will throw errors
  except FileNotFoundError:
    pass
  tar = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  cmd = ['7z', 'a', dstfile, '-si', '-t7z']
  if password is not None:
    cmd.append('-p' + password)
    cmd.append('-mhe')
  p7z = subprocess.Popen(cmd, stdin=tar.stdout, stdout=subprocess.DEVNULL)
  ret1 = tar.wait()
  ret2 = p7z.wait()

  ok = ret1 == ret2 == 0
  if ok:
    logger.info('tar.7z job %s succeeded', base.bold(name))
  else:
    logger.error('tar.7z job %s failed with codes %s',
                 base.bold(name), (ret1, ret2))
  return ok

########NEW FILE########
__FILENAME__ = base
import logging
import subprocess

logger = logging.getLogger(__name__)

__all__ = ['bold', 'run_command']

global_exclude = [
  '__pycache__', '*.pyc',
  '*.swp', '*~',
]

try:
  import curses
  curses.setupterm()
  _bold = str(curses.tigetstr("bold"), "ascii")
  _reset = str(curses.tigetstr("sgr0"), "ascii")
except:
  logger.warn('curses error, plain text log expected')
  _bold = _reset = ''

def bold(text):
  if _bold:
    return _bold + text + _reset
  else:
    return text

def run_command(cmd):
  logger.debug('running command: %r', cmd)

  if cmd[0] == 'sudo':
    print('sudo password may be requested.')

  retcode = subprocess.call(cmd)
  return retcode

########NEW FILE########
__FILENAME__ = git
'''
backups based on git.

We cannot `chdir` to the working directory because we may run multiple backups
at the same time.
'''

import os
import logging

from . import base

__all__ = ['push', 'fetch']

logger = logging.getLogger(__name__)

def push(name, directory, remote='origin', branch=None, *, force=False):
  cmd = [
    'git',
    '--work-tree='+directory,
    '--git-dir='+os.path.join(directory, '.git'),
    'push',
    remote
  ]
  if branch:
    cmd.append(branch)
  if force:
    cmd.append('-f')
  retcode = base.run_command(cmd)
  if retcode == 0:
    logger.info('git job %s succeeded', base.bold(name))
  else:
    logger.error('git job %s failed with code %d', base.bold(name), retcode)
  return not retcode

def fetch(name, directory, srcdir):
  '''
  fetch from the destination

  if the `directory` does not exist, we'll clone it instead.
  '''
  if not os.path.exists(directory):
    cmd = [
      'git', 'clone',
      srcdir, directory,
    ]
    cloning = True
  else:
    cmd = [
      'git',
      '--git-dir='+os.path.join(directory, '.git'),
      '--work-tree='+directory,
      'fetch',
    ]
    cloning = False

  verb = ('cloned', 'clone') if cloning else ('fetched', 'fetch')

  retcode = base.run_command(cmd)
  if retcode == 0:
    logger.info('git job %s %s successfully', base.bold(name), verb[0])
  else:
    logger.error('git job %s failed to %s with code %d',
                 base.bold(name), verb[1], retcode)
  return not retcode

#FIXME git-pull has a problem, see http://stackoverflow.com/questions/5083224/git-pull-while-not-in-a-git-directory
# fallback to fetch
pull = fetch

########NEW FILE########
__FILENAME__ = rsync
import logging
import os

from . import base

__all__ = ['sync2win', 'sync2native']

logger = logging.getLogger(__name__)

global_exclude = ['--exclude=' + x for x in base.global_exclude]

def sync(name, src, dst, option, really, filelist, exclude=()):
  '''if src is a symlink without trailing slash, it's expanded to real path'''
  if not src.endswith('/'):
    src = os.path.realpath(src)
  if filelist:
    cmd = [
      'rsync',
      option,
      '--delete',
      '--delete-excluded',
      '-r', '--files-from='+filelist,
      src, dst
    ]
    if not os.path.exists(dst):
      os.mkdir(dst)
  else:
    cmd = [
      'rsync',
      option,
      '--delete',
      '--delete-excluded',
      src, dst
    ]
  cmd.extend(global_exclude)
  cmd.extend(['--exclude=' + x for x in exclude])
  if not really:
    cmd.append('-n')
    dry = '(DRY RUN) '
  else:
    dry = ''

  retcode = base.run_command(cmd)
  if retcode == 0:
    logger.info('rsync job %s %ssucceeded', base.bold(name), dry)
  else:
    logger.error('rsync job %s %sfailed with code %d',
                 base.bold(name), dry, retcode)
  return not retcode

def sync2native(name, src, dst, really=False, filelist=False, exclude=()):
  '''
  sync to Linux native filesystems

  `filelist` indicates `src` is a list of files to sync
  '''
  return sync(name, src, dst, '-aviHKhP', really, filelist, exclude=exclude)

def sync2win(name, src, dst, really=False, filelist=False, exclude=()):
  '''
  sync to NTFS/FAT filesystems

  `filelist` indicates `src` is a list of files to sync
  '''
  return sync(name, src, dst, '-virtOhP', really, filelist, exclude=exclude)

########NEW FILE########
__FILENAME__ = truecrypt
'''
  Truecrypt mount/unmount
  ~~~~~~~~~~~~~~~~~~~~~~~

  You can store backup files into truecrypt volume.
'''

import logging

from . import base

__all__ = ['mount', 'unmount']

logger = logging.getLogger(__name__)

def mount(source, dest, sudo=False):
  cmd = [
    'truecrypt',
    source,
    dest
  ]
  if sudo:
    cmd.insert(0, 'sudo')
  retcode = base.run_command(cmd)
  if retcode == 0:
    logging.info('mount %s at %s successfully', source, base.bold(dest))
  else:
    logging.error('mounting %s at %s failed with code %d',
                  source,
                  base.bold(dest),
                  retcode)
  return not retcode

def unmount(sudo=False):
  cmd = [
    'truecrypt',
    '-d'
  ]
  if sudo:
    cmd.insert(0, 'sudo')
  retcode = base.run_command(cmd)
  if retcode == 0:
    logging.info('unmount truecrypt volume successfully.')
  else:
    logging.error('unmounting truecrypt volume failed with code %d', retcode)

  return not retcode

########NEW FILE########
__FILENAME__ = baidumusic
import json

from htmlutils import parse_document_from_requests
from musicsites import Base, SongInfo

class BaiduMusic(Base):
  def get_songs_from_list(self, url):
    doc = parse_document_from_requests(url, self.session)
    rows = doc.xpath(
      '//*[contains(concat(" ", normalize-space(@class), " "), " song-item ")]')
    songs = []

    for tr in rows:
      try:
        a = tr.xpath('./span[@class="song-title"]/a')[0]
      except IndexError:
        # some lists contain empty items...
        # e.g. index 30 of this:
        # http://music.baidu.com/search/song?key=70%E5%90%8E&start=20&size=20
        continue
      href = a.get('href')
      sid = href.rsplit('/', 1)[-1]
      title = a.text_content()
      artists = tuple(
        a.text_content() for a in
        tr.xpath('./span[@class="singer"]/span/a'))
      try:
        album = tr.xpath('./span[@class="album-title"]/a')[0].text_content().strip()
        album = album.lstrip('《').rstrip('》')
      except IndexError:
        album = None
      song = SongInfo(sid, title, href, artists, album, None)
      songs.append(song)

    return songs

  def get_song_info(self, sid):
    '''
    其中，``songLink`` 键是歌曲下载地址，``songName`` 是歌曲名
    '''
    s = self.session
    url = 'http://music.baidu.com/data/music/fmlink?songIds=' + sid
    r = s.get(url)
    return json.loads(r.text)['data']['songList'][0]

########NEW FILE########
__FILENAME__ = charset
'''
关于字符集的相关数据和函数

2011年3月10日
'''

import myutils

全角字符 = r'！＂＃＄％＆＇（）＊＋，－．／０１２３４５６７８９：；＜＝＞？＠ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿｀ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｜｝～￠￡￢￣￤￥'
半角字符 = r'''!"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~¢£¬¯¦¥'''
数字 = '零一二三四五六七八九个十百千万'

def zhnum(num):
  '''阿拉伯数字转中文'''
  import re
  if not isinstance(num, int) and not isinstance(num, float):
    raise TypeError('目前只能处理整数和小数')
  if num >= 100000:
    raise ValueError('目前只能处理到十万以内')
  sign = num < 0 and -1 or 1
  isfloat = isinstance(num, float) and True or False
  N = abs(int(num))
  ans = []
  for k, n in enumerate(str(N)[::-1]):
    a = 数字[int(n)] + 数字[10+k]
    if a == '零十' or a == '零百':
      a = '零'
    elif a[0] == '零':
      continue
    ans.append(a)
  ret = ''.join(ans[::-1])
  ret = ret.rstrip('零')
  ret = re.sub(r'零+', '零', ret)
  if ret.endswith('个'):
    ret = ret[:-1]
  if not ret:
    ret = '零'

  if sign == -1:
    ret = '负' + ret

  if isfloat:
    ret += '点'
    l = []
    left = abs(num) - N
    left = str(left)[2:]
    for n in left:
      l.append(数字[int(n)])
    ret += ''.join(l)
  return ret

def 全角转半角(字符串, 仅字母数字=True):
  if not isinstance(字符串, str):
    raise TypeError('参数类型不匹配：需要 str 类型参数')

  返回值 = ''
  for 字符 in 字符串:
    位置 = 全角字符.find(字符)
    if 位置 == -1 or 仅字母数字 and not 半角字符[位置].isalnum():
      返回值 += 字符
    else:
      返回值 += 半角字符[位置]

  return 返回值

qjzf = 全角字符
bjzf = 半角字符
qjzbj = 全角转半角

# 0 表示未知
星座 = ['', '水瓶座', '双鱼座', '白羊座', '金牛座', '双子座',
    '巨蟹座', '狮子座', '处女座', '天秤座', '天蝎座', '人马座', '山羊宫']
Constellation = 星座

生肖 = '鼠牛虎兔龙蛇马羊猴鸡狗猪'

def strwidth_py(s, ambiwidth=2):
  '''ambiwidth: 宽度不定的字符算几个，取值为 1, 2'''
  if ambiwidth == 2:
    dwidth = 'WFA'
  elif ambiwidth == 1:
    dwidth = 'WF'
  else:
    raise ValueError('ambiwidth 取值为 1 或者 2')

  import unicodedata
  count = 0
  for i in s:
    if unicodedata.east_asian_width(i) in dwidth:
      count += 2
      continue
    count += 1
  return count

try:
  import ctypes.util
  _libc = ctypes.CDLL(ctypes.util.find_library('c'))
  _libc.wcswidth.argtypes = (ctypes.c_wchar_p, ctypes.c_size_t)
  _libc.wcswidth.restype = ctypes.c_int
  def strwidth(s, ambiwidth=1):
    '''
    ambiwidth is ignored

    quicker than `strwidth_py' in Python
    '''
    return _libc.wcswidth(s, len(s))
except (ImportError, OSError):
  strwidth = strwidth_py

def _CJK_align(字符串, 对齐宽度, 方向='左', 填充=' '):
  '''对齐字符串，考虑字符宽度，不检测是否是ASCII字符串'''
  if len(填充) != 1:
    raise ValueError('填充字符只能是一个字符')

  if 方向 == '右':
    return 填充 * round(((对齐宽度 - strwidth(字符串)) / strwidth(填充))) + 字符串
  elif 方向 == '左':
    return 字符串 + 填充 * round(((对齐宽度 - strwidth(字符串)) / strwidth(填充)))
  else:
    raise ValueError("`方向' 可选为 '左' 或者 '右'")

def CJK_align(字符串, 对齐宽度, 方向='左', 填充=' '):
  '''对齐字符串，考虑字符宽度'''
  if isascii(字符串):
    if 方向 == '右':
      return 字符串.rjust(对齐宽度, 填充)
    elif 方向 == '左':
      return 字符串.ljust(对齐宽度, 填充)
    else:
      raise ValueError("`方向' 可选为 '左' 或者 '右'")
  else:
    return _CJK_align(字符串, 对齐宽度, 方向, 填充)

def isascii(string):
  return all(ord(ch) < 256 for ch in string)

# vim:tw=78:et:sts=2:fdm=expr:fde=getline(v\:lnum)=~'\\v^\\S.*\:(\\s*#.*)?$'?'>1'\:1

########NEW FILE########
__FILENAME__ = checktime
'''
check if any file in a set has been modified or got deleted
'''

import os

class TimeChecker:
  '''
  Initialed with a set of file paths. Later ``check()`` call will return a changed file list.
  passing in another set to change the file set to be monitored.

  you can access the file set (a frozenset) by its property ``fileset``.
  '''
  def __init__(self, fileset):
    # outside may not changed this accidentally
    self.fileset = frozenset(fileset)
    self.modifyTimes = {}
    self.check()

  def check(self, newlist=None):
    result = self.updateTime()
    if newlist:
      self.modifyTimes = {}
      self.fileset = frozenset(newlist)
    return result

  def updateTime(self):
    modifyTimes = self.modifyTimes
    modified = []
    for path in self.fileset:
      try:
        modify_time = os.stat(path).st_mtime
      except OSError:
        if path in modifyTimes:
          del modifyTimes[path]
          modified.append(path)
        continue
      if path not in modifyTimes:
        modifyTimes[path] = modify_time
        continue
      if modifyTimes[path] != modify_time:
        modifyTimes[path] = modify_time
        modified.append(path)
    return modified

########NEW FILE########
__FILENAME__ = cli
# vim:fileencoding=utf-8
# This file is in the Public Domain

'''
Convenient functions for command-line use.

Python 2 & 3
'''

import os

def repl(local, histfile=None, banner=None):
  import readline
  import rlcompleter
  if 'libedit' in readline.__doc__:
    readline.parse_and_bind('bind ^I rl_complete')
  else:
    readline.parse_and_bind('tab: complete')
  if histfile is not None and os.path.exists(histfile):
    # avoid duplicate reading
    if readline.get_current_history_length() <= 0:
      readline.set_history_length(10000)
      readline.read_history_file(histfile)
  import code
  readline.set_completer(rlcompleter.Completer(local).complete)
  code.interact(local=local, banner=banner)
  if histfile is not None:
    readline.write_history_file(histfile)

def repl_reset_stdin(*args, **kwargs):
  fd = os.open('/dev/tty', os.O_RDONLY)
  os.dup2(fd, 0)
  os.close(fd)
  repl(*args, **kwargs)

def repl_py27(local, *args, **kwargs):
  '''Fix unicode display in Python 2.x by filtering through the ascii2uni program'''
  import subprocess, sys, time
  p = subprocess.Popen(['ascii2uni', '-qa7'],
                       stdin=subprocess.PIPE, preexec_fn=os.setpgrp)

  def displayfunc(value):
    if value is None:
      local['_'] = None
      return

    r = repr(value)
    if r.find(r'\x') != -1:
      p.stdin.write(r+'\n')
      time.sleep(0.01)
    else:
      print(r)
    local['_'] = value

  old_displayhook = sys.displayhook
  sys.displayhook = displayfunc
  try:
    repl(local, *args, **kwargs)
  finally:
    sys.displayhook = old_displayhook
    p.stdin.close()
    p.wait()

########NEW FILE########
__FILENAME__ = cmdutils
# vim:fileencoding=utf-8

'''
call external tools to do things.
'''

import subprocess
from functools import lru_cache

@lru_cache(maxsize=20)
def lookupip(ip, cmd='cip'):
  return subprocess.getoutput(subprocess.list2cmdline([cmd, ip])).replace('CZ88.NET', '').strip() or '-'

def check_mediafile(file):
  '''intergrity check with ffmpeg

  also return ``False`` when reading the file fails

  From http://superuser.com/a/100290/40869
  '''

  p = subprocess.Popen(
    ['ffmpeg', '-v', 'error', '-i', file, '-f', 'null', '-'],
    stderr = subprocess.PIPE)
  _, e = p.communicate()
  return not bool(e.strip())

########NEW FILE########
__FILENAME__ = colorfinder
'''
benchmark:

In [2]: %timeit colorfinder.hex2term_accurate('#434519')
100 loops, best of 3: 5.06 ms per loop

In [3]: %timeit colorfinder.hex2term_quick('#434519')
100000 loops, best of 3: 12.2 µs per loop
'''

from math import sqrt, degrees, atan2, fabs, cos, radians, sin, exp
from functools import lru_cache

def parsehex_float(c):
  return tuple(int(x, 16)/255.0 for x in (c[1:3], c[3:5], c[5:7]))

def parsehex_int(c):
  return tuple(int(x, 16) for x in (c[1:3], c[3:5], c[5:7]))

def best_match(colortuple, mapping):
  best_match = None
  smallest_distance = 10000000

  dest = rgb2lab(colortuple)
  for v, c in mapping.items():
    d = delta_e_cie2000(dest, c)

    if d < smallest_distance:
      smallest_distance = d
      best_match = (v, c)

  return best_match

def rgb2lab(colortuple):
  '''RGB to XYZ then to Lab'''
  return xyz2lab(rgb2xyz(colortuple))

def rgb2xyz(colortuple):
  '''RGB to XYZ'''
  # http://www.easyrgb.com/index.php?X=MATH&H=02#text2
  r, g, b = colortuple

  if r > 0.04045 :
    r = ((r + 0.055) / 1.055) ** 2.4
  else:
    r = r / 12.92
  if g > 0.04045 :
    g = ((g + 0.055) / 1.055) ** 2.4
  else:
    g = g / 12.92
  if b > 0.04045 :
    b = ((b + 0.055) / 1.055) ** 2.4
  else:
    b = b / 12.92

  r = r * 100
  g = g * 100
  b = b * 100

  X = r * 0.4124 + g * 0.3576 + b * 0.1805
  Y = r * 0.2126 + g * 0.7152 + b * 0.0722
  Z = r * 0.0193 + g * 0.1192 + b * 0.9505
  return X, Y, Z

def xyz2lab(xyz):
  '''XYZ to Lab'''
  # http://www.easyrgb.com/index.php?X=MATH&H=07#text7
  X, Y, Z = xyz

  X /=  95.047
  Y /= 100.000
  Z /= 108.883

  if (X > 0.008856):
    X = X ** (1/3)
  else:
    X = (7.787 * X) + (16 / 116)
  if (Y > 0.008856):
    Y = Y ** (1/3)
  else:
    Y = (7.787 * Y) + (16 / 116)
  if (Z > 0.008856):
    Z = Z ** (1/3)
  else:
    Z = (7.787 * Z) + (16 / 116)

  L = (116 * Y) - 16
  a = 500 * (X - Y)
  b = 200 * (Y - Z)

  return L, a, b

def delta_e_cie2000(color1, color2):
  """
  Calculates the Delta E (CIE2000) of two colors. Colors are given in Lab tuples.

  Stolen from colormath.color_objects
  """
  Kl = Kc = Kh = 1
  L1, a1, b1 = color1
  L2, a2, b2 = color2

  avg_Lp = (L1 + L2) / 2.0
  C1 = sqrt(pow(a1, 2) + pow(b1, 2))
  C2 = sqrt(pow(a2, 2) + pow(b2, 2))
  avg_C1_C2 = (C1 + C2) / 2.0

  G = 0.5 * (1 - sqrt(pow(avg_C1_C2 , 7.0) / (pow(avg_C1_C2, 7.0) + pow(25.0, 7.0))))

  a1p = (1.0 + G) * a1
  a2p = (1.0 + G) * a2
  C1p = sqrt(pow(a1p, 2) + pow(b1, 2))
  C2p = sqrt(pow(a2p, 2) + pow(b2, 2))
  avg_C1p_C2p =(C1p + C2p) / 2.0

  if degrees(atan2(b1,a1p)) >= 0:
    h1p = degrees(atan2(b1,a1p))
  else:
    h1p = degrees(atan2(b1,a1p)) + 360

  if degrees(atan2(b2,a2p)) >= 0:
    h2p = degrees(atan2(b2,a2p))
  else:
    h2p = degrees(atan2(b2,a2p)) + 360

  if fabs(h1p - h2p) > 180:
    avg_Hp = (h1p + h2p + 360) / 2.0
  else:
    avg_Hp = (h1p + h2p) / 2.0

  T = 1 - 0.17 * cos(radians(avg_Hp - 30)) + 0.24 * cos(radians(2 * avg_Hp)) + 0.32 * cos(radians(3 * avg_Hp + 6)) - 0.2  * cos(radians(4 * avg_Hp - 63))

  diff_h2p_h1p = h2p - h1p
  if fabs(diff_h2p_h1p) <= 180:
    delta_hp = diff_h2p_h1p
  elif (fabs(diff_h2p_h1p) > 180) and (h2p <= h1p):
    delta_hp = diff_h2p_h1p + 360
  else:
    delta_hp = diff_h2p_h1p - 360

  delta_Lp = L2 - L1
  delta_Cp = C2p - C1p
  delta_Hp = 2 * sqrt(C2p * C1p) * sin(radians(delta_hp) / 2.0)

  S_L = 1 + ((0.015 * pow(avg_Lp - 50, 2)) / sqrt(20 + pow(avg_Lp - 50, 2.0)))
  S_C = 1 + 0.045 * avg_C1p_C2p
  S_H = 1 + 0.015 * avg_C1p_C2p * T

  delta_ro = 30 * exp(-(pow(((avg_Hp - 275) / 25), 2.0)))
  R_C = sqrt((pow(avg_C1p_C2p, 7.0)) / (pow(avg_C1p_C2p, 7.0) + pow(25.0, 7.0)));
  R_T = -2 * R_C * sin(2 * radians(delta_ro))

  delta_E = sqrt(pow(delta_Lp /(S_L * Kl), 2) + pow(delta_Cp /(S_C * Kc), 2) + pow(delta_Hp /(S_H * Kh), 2) + R_T * (delta_Cp /(S_C * Kc)) * (delta_Hp / (S_H * Kh)))

  return delta_E

def prepare_map(hexrgbmap):
  return {
    k: rgb2lab(parsehex_float(v))
    for k, v in termcolors.items()
  }

@lru_cache(300)
def hex2term_accurate(color):
  global _termcolors_map
  if _termcolors_map is None:
    _termcolors_map = prepare_map(termcolors)

  return best_match(parsehex_float(color), _termcolors_map)[0]

def _hex2term_quick(red, green, blue):
  # from ruby-paint
  gray_possible = True
  sep = 42.5
  gray = False

  while gray_possible:
    if red < sep or green < sep or blue < sep:
      gray = red < sep and green < sep and blue < sep
      gray_possible = False
    sep += 42.5

  if gray:
    return 232 + (red + green + blue) // 33
  else:
    return 16 + sum(6 * x // 256 * 6 ** i
                    for i, x in enumerate((blue, green, red)))

def hex2term_quick(color):
  return _hex2term_quick(*parsehex_int(color))

def htmltest():
  from random import randrange

  print('''\
<!DOCTYPE html>
<meta charset="utf-8" />
<title>Terminal Color Approximation Test</title>
<table>
  <thead>
    <tr><th>Accurate</th><th>Orignal</th><th>Quick</th><th>Same?</th></tr>
  </thead>
  <tbody>''')
  for i in range(100):
    r = randrange(256)
    g = randrange(256)
    b = randrange(256)
    c = '#%02x%02x%02x' % (r, g, b)
    c_a = termcolors[hex2term_accurate(c)]
    c_q = termcolors[hex2term_quick(c)]
    same = c_a == c_q and '\N{HEAVY CHECK MARK}' or '\N{HEAVY BALLOT X}'
    print('''\
    <tr>
      <td style="background-color: {c_a}">{c_a}</td>
      <td style="background-color: {c}">{c}</td>
      <td style="background-color: {c_q}">{c_q}</td>
      <td>{same}</td>
    </tr>'''.format(c=c, c_a=c_a, c_q=c_q, same=same))
  print('''\
  </tbody>
</table>''')

_termcolors_map = None

termcolors = {
  16: '#000000', 17: '#00005f', 18: '#000087',
  19: '#0000af', 20: '#0000d7', 21: '#0000ff',
  22: '#005f00', 23: '#005f5f', 24: '#005f87',
  25: '#005faf', 26: '#005fd7', 27: '#005fff',
  28: '#008700', 29: '#00875f', 30: '#008787',
  31: '#0087af', 32: '#0087d7', 33: '#0087ff',
  34: '#00af00', 35: '#00af5f', 36: '#00af87',
  37: '#00afaf', 38: '#00afd7', 39: '#00afff',
  40: '#00d700', 41: '#00d75f', 42: '#00d787',
  43: '#00d7af', 44: '#00d7d7', 45: '#00d7ff',
  46: '#00ff00', 47: '#00ff5f', 48: '#00ff87',
  49: '#00ffaf', 50: '#00ffd7', 51: '#00ffff',
  52: '#5f0000', 53: '#5f005f', 54: '#5f0087',
  55: '#5f00af', 56: '#5f00d7', 57: '#5f00ff',
  58: '#5f5f00', 59: '#5f5f5f', 60: '#5f5f87',
  61: '#5f5faf', 62: '#5f5fd7', 63: '#5f5fff',
  64: '#5f8700', 65: '#5f875f', 66: '#5f8787',
  67: '#5f87af', 68: '#5f87d7', 69: '#5f87ff',
  70: '#5faf00', 71: '#5faf5f', 72: '#5faf87',
  73: '#5fafaf', 74: '#5fafd7', 75: '#5fafff',
  76: '#5fd700', 77: '#5fd75f', 78: '#5fd787',
  79: '#5fd7af', 80: '#5fd7d7', 81: '#5fd7ff',
  82: '#5fff00', 83: '#5fff5f', 84: '#5fff87',
  85: '#5fffaf', 86: '#5fffd7', 87: '#5fffff',
  88: '#870000', 89: '#87005f', 90: '#870087',
  91: '#8700af', 92: '#8700d7', 93: '#8700ff',
  94: '#875f00', 95: '#875f5f', 96: '#875f87',
  97: '#875faf', 98: '#875fd7', 99: '#875fff',
  100: '#878700', 101: '#87875f', 102: '#878787',
  103: '#8787af', 104: '#8787d7', 105: '#8787ff',
  106: '#87af00', 107: '#87af5f', 108: '#87af87',
  109: '#87afaf', 110: '#87afd7', 111: '#87afff',
  112: '#87d700', 113: '#87d75f', 114: '#87d787',
  115: '#87d7af', 116: '#87d7d7', 117: '#87d7ff',
  118: '#87ff00', 119: '#87ff5f', 120: '#87ff87',
  121: '#87ffaf', 122: '#87ffd7', 123: '#87ffff',
  124: '#af0000', 125: '#af005f', 126: '#af0087',
  127: '#af00af', 128: '#af00d7', 129: '#af00ff',
  130: '#af5f00', 131: '#af5f5f', 132: '#af5f87',
  133: '#af5faf', 134: '#af5fd7', 135: '#af5fff',
  136: '#af8700', 137: '#af875f', 138: '#af8787',
  139: '#af87af', 140: '#af87d7', 141: '#af87ff',
  142: '#afaf00', 143: '#afaf5f', 144: '#afaf87',
  145: '#afafaf', 146: '#afafd7', 147: '#afafff',
  148: '#afd700', 149: '#afd75f', 150: '#afd787',
  151: '#afd7af', 152: '#afd7d7', 153: '#afd7ff',
  154: '#afff00', 155: '#afff5f', 156: '#afff87',
  157: '#afffaf', 158: '#afffd7', 159: '#afffff',
  160: '#d70000', 161: '#d7005f', 162: '#d70087',
  163: '#d700af', 164: '#d700d7', 165: '#d700ff',
  166: '#d75f00', 167: '#d75f5f', 168: '#d75f87',
  169: '#d75faf', 170: '#d75fd7', 171: '#d75fff',
  172: '#d78700', 173: '#d7875f', 174: '#d78787',
  175: '#d787af', 176: '#d787d7', 177: '#d787ff',
  178: '#d7af00', 179: '#d7af5f', 180: '#d7af87',
  181: '#d7afaf', 182: '#d7afd7', 183: '#d7afff',
  184: '#d7d700', 185: '#d7d75f', 186: '#d7d787',
  187: '#d7d7af', 188: '#d7d7d7', 189: '#d7d7ff',
  190: '#d7ff00', 191: '#d7ff5f', 192: '#d7ff87',
  193: '#d7ffaf', 194: '#d7ffd7', 195: '#d7ffff',
  196: '#ff0000', 197: '#ff005f', 198: '#ff0087',
  199: '#ff00af', 200: '#ff00d7', 201: '#ff00ff',
  202: '#ff5f00', 203: '#ff5f5f', 204: '#ff5f87',
  205: '#ff5faf', 206: '#ff5fd7', 207: '#ff5fff',
  208: '#ff8700', 209: '#ff875f', 210: '#ff8787',
  211: '#ff87af', 212: '#ff87d7', 213: '#ff87ff',
  214: '#ffaf00', 215: '#ffaf5f', 216: '#ffaf87',
  217: '#ffafaf', 218: '#ffafd7', 219: '#ffafff',
  220: '#ffd700', 221: '#ffd75f', 222: '#ffd787',
  223: '#ffd7af', 224: '#ffd7d7', 225: '#ffd7ff',
  226: '#ffff00', 227: '#ffff5f', 228: '#ffff87',
  229: '#ffffaf', 230: '#ffffd7', 231: '#ffffff',
  232: '#080808', 233: '#121212', 234: '#1c1c1c',
  235: '#262626', 236: '#303030', 237: '#3a3a3a',
  238: '#444444', 239: '#4e4e4e', 240: '#585858',
  241: '#626262', 242: '#6c6c6c', 243: '#767676',
  244: '#808080', 245: '#8a8a8a', 246: '#949494',
  247: '#9e9e9e', 248: '#a8a8a8', 249: '#b2b2b2',
  250: '#bcbcbc', 251: '#c6c6c6', 252: '#d0d0d0',
  253: '#dadada', 254: '#e4e4e4', 255: '#eeeeee',
}

if __name__ == '__main__':
  htmltest()

########NEW FILE########
__FILENAME__ = cursesutil
import curses
import readline
import ctypes
import ctypes.util
import struct
from charset import strwidth as width

rllib_path = ctypes.util.find_library('readline')
rllib = ctypes.CDLL(rllib_path)

def getstr(win, y=None, x=None):
  _, col = win.getmaxyx()
  if x is None or y is None:
    y, x = win.getyx()
  inputbox = curses.newwin(1, col-x, y, x)
  ret = ''
  ok = False
  eof = False
  def callback(s):
    nonlocal ok, ret, eof
    if s is None:
      rllib.rl_callback_handler_remove()
      eof = True
    elif not s:
      ok = True
    else:
      ret = s.decode()
      ok = True

  cbfunc = ctypes.CFUNCTYPE(None, ctypes.c_char_p)

  rllib.rl_callback_handler_install.restype = None
  rllib.rl_callback_handler_install(ctypes.c_char_p(b""), cbfunc(callback))

  while True:
    rllib.rl_callback_read_char()
    if ok:
      break
    if eof:
      raise EOFError
    inputbox.erase()
    # 这样获取的值不对。。。
    # bbuf = ctypes.string_at(rllib.rl_line_buffer)
    buf = readline.get_line_buffer()
    bbuf = buf.encode()
    inputbox.addstr(0, 0, buf)
    rl_point = struct.unpack('I', ctypes.string_at(rllib.rl_point, 4))[0]
    w = width(bbuf[:rl_point].decode())
    inputbox.move(0, w)
    inputbox.refresh()

  del inputbox
  return ret


########NEW FILE########
__FILENAME__ = eventmodel
'''
事件驱动模型

2010年10月22日
'''

import collections

class Event:
  '''所有事件的父类

  stopLater      阻止接下来的同级事件的处理
  stopPropagate  阻止触发父类事件
  preventDefault 阻止默认的处理(与事件同名的方法)
  '''
  stopPropagate = False
  stopLater = False
  preventDefault = False
  def __str__(self):
    return self.__class__.__name__

class EventModel:
  '''事件驱动模型

  listeners  是一个字典，以事件为键，值为一列表
             列表元素为二元组：(函数, 附加的参数)
  listeners2 类似，但是会在默认事件发生之后被处理
  这两个属性通常不需要直接访问。
  '''
  listeners = collections.defaultdict(list)
  listeners2 = collections.defaultdict(list)
  def trigger(self, event):
    ec = event.__class__
    if not issubclass(ec, Event):
      raise TypeError('%s 不是事件的实例' % event)

    for e in ec.__mro__:
      for f in self.listeners[e]:
        f[0](self, event, f[1])
        if event.stopLater:
          break
      # 默认动作
      if not event.preventDefault:
        if hasattr(self, e.__name__):
          getattr(self, e.__name__)(event)
      if not event.stopLater:
        for f in self.listeners2[e]:
          f[0](self, event, f[1])
          if event.stopLater:
            break
      if event.stopPropagate:
        break

  def _checkListener(self, event, func):
    if not issubclass(event, Event):
      raise TypeError('%s 不是事件' % event.__name__)
    if not hasattr(func, '__call__'):
      raise TypeError('func 不是函数')

  def addEventListener(self, event, func, arg):
    self._checkListener(event, func)
    self.listeners[event].append((func, arg))

  def prependEventListener(self, event, func, arg):
    '''将事件添加到最前面'''
    self._checkListener(event, func)
    self.listeners[event].insert(0, (func, arg))

  def appendEventListener(self, event, func, arg):
    '''将事件添加到最后面(后于默认事件)'''
    self._checkListener(event, func)
    self.listeners2[event].append((func, arg))

  def removeEventListener(self, event, func, arg):
    '''移除指定的事件处理器*一次*'''
    self._checkListener(event, func)
    try:
      self.listeners[event].remove((func, arg))
    except ValueError:
      self.listeners2[event].remove((func, arg))


########NEW FILE########
__FILENAME__ = expect3
'''
python 版的 expect

2010年8月5日
'''

try:
  import sys, os
  import re
  import pty
  import tty
  import termios
  import struct
  import fcntl
  import resource
  import select
  import signal
  import time
except ImportError:
  print('''Someting went wrong while importing modules.
Is this a Unix-like system?''', file=sys.stderr)

class spawn:
  def __init__(self, command, executable=None, timeout=30, maxread=2000, searchwindowsize=None, logfile=None, timefile=None, cwd=None, env=None, winsize=None):
    '''
    command: list，要执行的命令
    logfile: file, 记录输出的文件
    winsize: None, 自动设置终端大小
    '''
    if executable is None:
      executable = command[0]

    self.fd = sys.stdout.fileno()

    pid, fd = pty.fork()
    if pid == 0: # 子进程
      self.parent = False

      # Do not allow child to inherit open file descriptors from parent.
      max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
      os.closerange(3, max_fd)
      if cwd is not None:
        os.chdir(cwd)
      if env is None:
        os.execvp(executable, command)
      else:
        os.execvpe(executable, command, env)
    else:
      self.parent = True
      self.ptyfd = fd
      self.readbuffer = b''

      if winsize is None:
        self.updatewinsize()
        def sigwinch_passthrough(sig, data):
          self.updatewinsize()
        signal.signal(signal.SIGWINCH, sigwinch_passthrough)
      else:
        self.setwinsize(*winsize)

      self.timeout = timeout
      self.maxread = maxread
      self.searchwindowsize = searchwindowsize
      self.logfile = logfile
      self.timefile = timefile
      if timefile:
        self.lasttime = time.time()

  def fileno(self):
    return self.ptyfd

  def expect(self, what):
    if isinstance(what, str):
      what = what.encode()

    if re.search(what, self.readbuffer):
      return

    fd = self.ptyfd
    while True:
      self._read()
      if re.search(what, self.readbuffer):
        break

    self.readbuffer = b''

  def _read(self):
    try:
      s = os.read(self.ptyfd, 1024)
    except OSError as e:
      if e.errno == 5:
        raise EOFError
      else:
        raise

    self.readbuffer += s
    if self.logfile:
      self.logfile.write(s)
      self.logfile.flush()
    if self.timefile:
      t = time.time()
      self.timefile.write('%.6f %d\n' % (t-self.lasttime, len(s)))
      self.timefile.flush()
      self.lasttime = t

  def read(self):
    '''read something to self.readbuffer'''
    rd, wd, ed = select.select([self.ptyfd], [], [], 0)
    while rd:
      self._read()
      rd, wd, ed = select.select([self.ptyfd], [], [], 0)

  def send(self, what):
    if isinstance(what, str):
      what = what.encode()
    os.write(self.ptyfd, what)

  def sendline(self, what):
    if isinstance(what, str):
      what = what.encode()
    what += b'\r'
    self.send(what)

  def interact(self):
    os.write(self.fd, self.readbuffer)
    old = termios.tcgetattr(self.fd)
    new = termios.tcgetattr(self.fd)
    new[3] = new[3] & ~termios.ECHO
    try:
      tty.setraw(self.fd)
      while True:
        try:
          rd, wd, ed = select.select([self.ptyfd, self.fd], [], [])
        except select.error as e:
          if e.args[0] == 4:
            continue
          else:
            raise
        for i in rd:
          if i == self.ptyfd:
            s = os.read(i, 1024)
            os.write(self.fd, s)
          elif i == self.fd:
            s = os.read(i, 1024)
            os.write(self.ptyfd, s)
    except OSError as e:
      if e.errno == 5:
        # 使用 print() 会导致下一个 Python 提示符位置不对
        os.write(self.fd, '已结束。\r\n'.encode())
      else:
        raise
    finally:
      termios.tcsetattr(self.fd, termios.TCSADRAIN, old)

  def setwinsize(self, columns, lines):
    s = struct.pack('HHHH', lines, columns, 0, 0)
    fcntl.ioctl(self.ptyfd, termios.TIOCSWINSZ, s)

  def updatewinsize(self):
    '''update winsize to the same as the parent'''
    s = struct.pack("HHHH", 0, 0, 0, 0)
    a = struct.unpack('hhhh', fcntl.ioctl(self.fd, termios.TIOCGWINSZ, s))
    self.setwinsize(a[1], a[0])


########NEW FILE########
__FILENAME__ = fluxbbclient
from lxml.html import fromstring

from requestsutils import RequestsBase

class FluxBB(RequestsBase):
  userAgent = 'A Python Fluxbb Client by lilydjwg'
  auto_referer = True

  def check_login(self):
    '''check if we have logged in already (by cookies)'''
    res = self.request('/')
    body = res.text
    return len(fromstring(body).xpath(
      '//div[@id="brdwelcome"]/*[@class="conl"]/li')) > 0

  def login(self, username, password):
    post = {
      'req_username': username,
      'req_password': password,
      'save_pass': '1',
      'form_sent': '1',
    }
    body = self.request('/login.php?action=in', data=post).content
    return b'http-equiv="refresh"' in body

  def delete_unverified_users(self, doc=None, *, msg=None, since=None):
    '''delete inverified users in first page

    doc can be given if you have that page's parsed content alread.
    return False if no such users are found.
    '''
    if doc is None:
      url = '/admin_users.php?find_user=&' \
          'order_by=username&direction=ASC&user_group=0&p=1'
      if since:
        url += '&registered_before=' + since.strftime('%Y-%m-%d %H:%M:%s')
      res = self.request(url)
      body = res.text
      doc = fromstring(body)
    trs = doc.xpath('//div[@id="users2"]//tbody/tr')
    if not trs:
      return False

    users = [tr.xpath('td/input[@type="checkbox"]/@name')[0][6:-1]
             for tr in trs]
    users = ','.join(users)

    post = {
      'ban_expire': '',
      'ban_users_comply': 'save',
      'ban_message': msg or 'not verified. Ask admin if you are not a spammer.',
      'ban_the_ip': '1',
      'users': users,
    }
    res = self.request('/admin_users.php', data=post)
    body = res.text

    post = {
      'delete_users_comply': 'delete',
      'delete_posts': '1',
      'users': users,
    }
    res = self.request('/admin_users.php', data=post)
    body = res.text
    return True

  def edit_post(self, post_id, body, *, subject=None, sticky=False):
    html = self.request('/viewtopic.php?pid=%s' % post_id).text
    post = fromstring(html)
    old_subject = post.xpath('//ul[@class="crumbs"]/li/strong/a')[0].text
    data = {
      'form_sent': '1',
      'req_message': body,
      'req_subject': subject or old_subject,
      'stick_topic': sticky and '1' or '0',
    }
    url = '/edit.php?id=%s&action=edit' % post_id
    res = self.request(url, data=data)
    return b'http-equiv="refresh"' in res.content


########NEW FILE########
__FILENAME__ = gbzip
"""
这是我（lilydjwg）的一个修改版，用于解压在 Windows 上创建的文件名编码为 GBxxxx
的 zip 文件。

尚未测试对 zip 文件的写是否正确。

Read and write ZIP files.

XXX references to utf-8 need further investigation.
"""
import struct, os, time, sys, shutil
import binascii, io, stat

try:
    import zlib # We may need its compression method
    crc32 = zlib.crc32
except ImportError:
    zlib = None
    crc32 = binascii.crc32

__all__ = ["BadZipfile", "error", "ZIP_STORED", "ZIP_DEFLATED", "is_zipfile",
           "ZipInfo", "ZipFile", "PyZipFile", "LargeZipFile" ]

class BadZipfile(Exception):
    pass


class LargeZipFile(Exception):
    """
    Raised when writing a zipfile, the zipfile requires ZIP64 extensions
    and those extensions are disabled.
    """

error = BadZipfile      # The exception raised by this module

ZIP64_LIMIT = (1 << 31) - 1
ZIP_FILECOUNT_LIMIT = 1 << 16
ZIP_MAX_COMMENT = (1 << 16) - 1

# constants for Zip file compression methods
ZIP_STORED = 0
ZIP_DEFLATED = 8
# Other ZIP compression methods not supported

# Below are some formats and associated data for reading/writing headers using
# the struct module.  The names and structures of headers/records are those used
# in the PKWARE description of the ZIP file format:
#     http://www.pkware.com/documents/casestudies/APPNOTE.TXT
# (URL valid as of January 2008)

# The "end of central directory" structure, magic number, size, and indices
# (section V.I in the format document)
structEndArchive = b"<4s4H2LH"
stringEndArchive = b"PK\005\006"
sizeEndCentDir = struct.calcsize(structEndArchive)

_ECD_SIGNATURE = 0
_ECD_DISK_NUMBER = 1
_ECD_DISK_START = 2
_ECD_ENTRIES_THIS_DISK = 3
_ECD_ENTRIES_TOTAL = 4
_ECD_SIZE = 5
_ECD_OFFSET = 6
_ECD_COMMENT_SIZE = 7
# These last two indices are not part of the structure as defined in the
# spec, but they are used internally by this module as a convenience
_ECD_COMMENT = 8
_ECD_LOCATION = 9

# The "central directory" structure, magic number, size, and indices
# of entries in the structure (section V.F in the format document)
structCentralDir = "<4s4B4HL2L5H2L"
stringCentralDir = b"PK\001\002"
sizeCentralDir = struct.calcsize(structCentralDir)

# indexes of entries in the central directory structure
_CD_SIGNATURE = 0
_CD_CREATE_VERSION = 1
_CD_CREATE_SYSTEM = 2
_CD_EXTRACT_VERSION = 3
_CD_EXTRACT_SYSTEM = 4
_CD_FLAG_BITS = 5
_CD_COMPRESS_TYPE = 6
_CD_TIME = 7
_CD_DATE = 8
_CD_CRC = 9
_CD_COMPRESSED_SIZE = 10
_CD_UNCOMPRESSED_SIZE = 11
_CD_FILENAME_LENGTH = 12
_CD_EXTRA_FIELD_LENGTH = 13
_CD_COMMENT_LENGTH = 14
_CD_DISK_NUMBER_START = 15
_CD_INTERNAL_FILE_ATTRIBUTES = 16
_CD_EXTERNAL_FILE_ATTRIBUTES = 17
_CD_LOCAL_HEADER_OFFSET = 18

# The "local file header" structure, magic number, size, and indices
# (section V.A in the format document)
structFileHeader = "<4s2B4HL2L2H"
stringFileHeader = b"PK\003\004"
sizeFileHeader = struct.calcsize(structFileHeader)

_FH_SIGNATURE = 0
_FH_EXTRACT_VERSION = 1
_FH_EXTRACT_SYSTEM = 2
_FH_GENERAL_PURPOSE_FLAG_BITS = 3
_FH_COMPRESSION_METHOD = 4
_FH_LAST_MOD_TIME = 5
_FH_LAST_MOD_DATE = 6
_FH_CRC = 7
_FH_COMPRESSED_SIZE = 8
_FH_UNCOMPRESSED_SIZE = 9
_FH_FILENAME_LENGTH = 10
_FH_EXTRA_FIELD_LENGTH = 11

# The "Zip64 end of central directory locator" structure, magic number, and size
structEndArchive64Locator = "<4sLQL"
stringEndArchive64Locator = b"PK\x06\x07"
sizeEndCentDir64Locator = struct.calcsize(structEndArchive64Locator)

# The "Zip64 end of central directory" record, magic number, size, and indices
# (section V.G in the format document)
structEndArchive64 = "<4sQ2H2L4Q"
stringEndArchive64 = b"PK\x06\x06"
sizeEndCentDir64 = struct.calcsize(structEndArchive64)

_CD64_SIGNATURE = 0
_CD64_DIRECTORY_RECSIZE = 1
_CD64_CREATE_VERSION = 2
_CD64_EXTRACT_VERSION = 3
_CD64_DISK_NUMBER = 4
_CD64_DISK_NUMBER_START = 5
_CD64_NUMBER_ENTRIES_THIS_DISK = 6
_CD64_NUMBER_ENTRIES_TOTAL = 7
_CD64_DIRECTORY_SIZE = 8
_CD64_OFFSET_START_CENTDIR = 9

def _check_zipfile(fp):
    try:
        if _EndRecData(fp):
            return True         # file has correct magic number
    except IOError:
        pass
    return False

def is_zipfile(filename):
    """Quickly see if a file is a ZIP file by checking the magic number.

    The filename argument may be a file or file-like object too.
    """
    result = False
    try:
        if hasattr(filename, "read"):
            result = _check_zipfile(fp=filename)
        else:
            with open(filename, "rb") as fp:
                result = _check_zipfile(fp)
    except IOError:
        pass
    return result

def _EndRecData64(fpin, offset, endrec):
    """
    Read the ZIP64 end-of-archive records and use that to update endrec
    """
    fpin.seek(offset - sizeEndCentDir64Locator, 2)
    data = fpin.read(sizeEndCentDir64Locator)
    sig, diskno, reloff, disks = struct.unpack(structEndArchive64Locator, data)
    if sig != stringEndArchive64Locator:
        return endrec

    if diskno != 0 or disks != 1:
        raise BadZipfile("zipfiles that span multiple disks are not supported")

    # Assume no 'zip64 extensible data'
    fpin.seek(offset - sizeEndCentDir64Locator - sizeEndCentDir64, 2)
    data = fpin.read(sizeEndCentDir64)
    sig, sz, create_version, read_version, disk_num, disk_dir, \
            dircount, dircount2, dirsize, diroffset = \
            struct.unpack(structEndArchive64, data)
    if sig != stringEndArchive64:
        return endrec

    # Update the original endrec using data from the ZIP64 record
    endrec[_ECD_SIGNATURE] = sig
    endrec[_ECD_DISK_NUMBER] = disk_num
    endrec[_ECD_DISK_START] = disk_dir
    endrec[_ECD_ENTRIES_THIS_DISK] = dircount
    endrec[_ECD_ENTRIES_TOTAL] = dircount2
    endrec[_ECD_SIZE] = dirsize
    endrec[_ECD_OFFSET] = diroffset
    return endrec


def _EndRecData(fpin):
    """Return data from the "End of Central Directory" record, or None.

    The data is a list of the nine items in the ZIP "End of central dir"
    record followed by a tenth item, the file seek offset of this record."""

    # Determine file size
    fpin.seek(0, 2)
    filesize = fpin.tell()

    # Check to see if this is ZIP file with no archive comment (the
    # "end of central directory" structure should be the last item in the
    # file if this is the case).
    fpin.seek(-sizeEndCentDir, 2)
    data = fpin.read()
    if data[0:4] == stringEndArchive and data[-2:] == b"\000\000":
        # the signature is correct and there's no comment, unpack structure
        endrec = struct.unpack(structEndArchive, data)
        endrec=list(endrec)

        # Append a blank comment and record start offset
        endrec.append(b"")
        endrec.append(filesize - sizeEndCentDir)

        # Try to read the "Zip64 end of central directory" structure
        return _EndRecData64(fpin, -sizeEndCentDir, endrec)

    # Either this is not a ZIP file, or it is a ZIP file with an archive
    # comment.  Search the end of the file for the "end of central directory"
    # record signature. The comment is the last item in the ZIP file and may be
    # up to 64K long.  It is assumed that the "end of central directory" magic
    # number does not appear in the comment.
    maxCommentStart = max(filesize - (1 << 16) - sizeEndCentDir, 0)
    fpin.seek(maxCommentStart, 0)
    data = fpin.read()
    start = data.rfind(stringEndArchive)
    if start >= 0:
        # found the magic number; attempt to unpack and interpret
        recData = data[start:start+sizeEndCentDir]
        endrec = list(struct.unpack(structEndArchive, recData))
        comment = data[start+sizeEndCentDir:]
        # check that comment length is correct
        if endrec[_ECD_COMMENT_SIZE] == len(comment):
            # Append the archive comment and start offset
            endrec.append(comment)
            endrec.append(maxCommentStart + start)

            # Try to read the "Zip64 end of central directory" structure
            return _EndRecData64(fpin, maxCommentStart + start - filesize,
                                 endrec)

    # Unable to find a valid end of central directory structure
    return


class ZipInfo (object):
    """Class with attributes describing each file in the ZIP archive."""

    __slots__ = (
            'orig_filename',
            'filename',
            'date_time',
            'compress_type',
            'comment',
            'extra',
            'create_system',
            'create_version',
            'extract_version',
            'reserved',
            'flag_bits',
            'volume',
            'internal_attr',
            'external_attr',
            'header_offset',
            'CRC',
            'compress_size',
            'file_size',
            '_raw_time',
        )

    def __init__(self, filename="NoName", date_time=(1980,1,1,0,0,0)):
        self.orig_filename = filename   # Original file name in archive

        # Terminate the file name at the first null byte.  Null bytes in file
        # names are used as tricks by viruses in archives.
        null_byte = filename.find(chr(0))
        if null_byte >= 0:
            filename = filename[0:null_byte]
        # This is used to ensure paths in generated ZIP files always use
        # forward slashes as the directory separator, as required by the
        # ZIP format specification.
        if os.sep != "/" and os.sep in filename:
            filename = filename.replace(os.sep, "/")

        self.filename = filename        # Normalized file name
        self.date_time = date_time      # year, month, day, hour, min, sec
        # Standard values:
        self.compress_type = ZIP_STORED # Type of compression for the file
        self.comment = b""              # Comment for each file
        self.extra = b""                # ZIP extra data
        if sys.platform == 'win32':
            self.create_system = 0          # System which created ZIP archive
        else:
            # Assume everything else is unix-y
            self.create_system = 3          # System which created ZIP archive
        self.create_version = 20        # Version which created ZIP archive
        self.extract_version = 20       # Version needed to extract archive
        self.reserved = 0               # Must be zero
        self.flag_bits = 0              # ZIP flag bits
        self.volume = 0                 # Volume number of file header
        self.internal_attr = 0          # Internal attributes
        self.external_attr = 0          # External file attributes
        # Other attributes are set by class ZipFile:
        # header_offset         Byte offset to the file header
        # CRC                   CRC-32 of the uncompressed file
        # compress_size         Size of the compressed file
        # file_size             Size of the uncompressed file

    def FileHeader(self):
        """Return the per-file header as a string."""
        dt = self.date_time
        dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
        dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
        if self.flag_bits & 0x08:
            # Set these to zero because we write them after the file data
            CRC = compress_size = file_size = 0
        else:
            CRC = self.CRC
            compress_size = self.compress_size
            file_size = self.file_size

        extra = self.extra

        if file_size > ZIP64_LIMIT or compress_size > ZIP64_LIMIT:
            # File is larger than what fits into a 4 byte integer,
            # fall back to the ZIP64 extension
            fmt = '<HHQQ'
            extra = extra + struct.pack(fmt,
                    1, struct.calcsize(fmt)-4, file_size, compress_size)
            file_size = 0xffffffff
            compress_size = 0xffffffff
            self.extract_version = max(45, self.extract_version)
            self.create_version = max(45, self.extract_version)

        filename, flag_bits = self._encodeFilenameFlags()
        header = struct.pack(structFileHeader, stringFileHeader,
                 self.extract_version, self.reserved, flag_bits,
                 self.compress_type, dostime, dosdate, CRC,
                 compress_size, file_size,
                 len(filename), len(extra))
        return header + filename + extra

    def _encodeFilenameFlags(self):
        try:
            return self.filename.encode('ascii'), self.flag_bits
        except UnicodeEncodeError:
            return self.filename.encode('gb18030'), self.flag_bits | 0x800

    def _decodeExtra(self):
        # Try to decode the extra field.
        extra = self.extra
        unpack = struct.unpack
        while extra:
            tp, ln = unpack('<HH', extra[:4])
            if tp == 1:
                if ln >= 24:
                    counts = unpack('<QQQ', extra[4:28])
                elif ln == 16:
                    counts = unpack('<QQ', extra[4:20])
                elif ln == 8:
                    counts = unpack('<Q', extra[4:12])
                elif ln == 0:
                    counts = ()
                else:
                    raise RuntimeError("Corrupt extra field %s"%(ln,))

                idx = 0

                # ZIP64 extension (large files and/or large archives)
                if self.file_size in (0xffffffffffffffff, 0xffffffff):
                    self.file_size = counts[idx]
                    idx += 1

                if self.compress_size == 0xFFFFFFFF:
                    self.compress_size = counts[idx]
                    idx += 1

                if self.header_offset == 0xffffffff:
                    old = self.header_offset
                    self.header_offset = counts[idx]
                    idx+=1

            extra = extra[ln+4:]


class _ZipDecrypter:
    """Class to handle decryption of files stored within a ZIP archive.

    ZIP supports a password-based form of encryption. Even though known
    plaintext attacks have been found against it, it is still useful
    to be able to get data out of such a file.

    Usage:
        zd = _ZipDecrypter(mypwd)
        plain_char = zd(cypher_char)
        plain_text = map(zd, cypher_text)
    """

    def _GenerateCRCTable():
        """Generate a CRC-32 table.

        ZIP encryption uses the CRC32 one-byte primitive for scrambling some
        internal keys. We noticed that a direct implementation is faster than
        relying on binascii.crc32().
        """
        poly = 0xedb88320
        table = [0] * 256
        for i in range(256):
            crc = i
            for j in range(8):
                if crc & 1:
                    crc = ((crc >> 1) & 0x7FFFFFFF) ^ poly
                else:
                    crc = ((crc >> 1) & 0x7FFFFFFF)
            table[i] = crc
        return table
    crctable = _GenerateCRCTable()

    def _crc32(self, ch, crc):
        """Compute the CRC32 primitive on one byte."""
        return ((crc >> 8) & 0xffffff) ^ self.crctable[(crc ^ ch) & 0xff]

    def __init__(self, pwd):
        self.key0 = 305419896
        self.key1 = 591751049
        self.key2 = 878082192
        for p in pwd:
            self._UpdateKeys(p)

    def _UpdateKeys(self, c):
        self.key0 = self._crc32(c, self.key0)
        self.key1 = (self.key1 + (self.key0 & 255)) & 4294967295
        self.key1 = (self.key1 * 134775813 + 1) & 4294967295
        self.key2 = self._crc32((self.key1 >> 24) & 255, self.key2)

    def __call__(self, c):
        """Decrypt a single character."""
        assert isinstance(c, int)
        k = self.key2 | 2
        c = c ^ (((k * (k^1)) >> 8) & 255)
        self._UpdateKeys(c)
        return c

class ZipExtFile:
    """File-like object for reading an archive member.
       Is returned by ZipFile.open().
    """

    def __init__(self, fileobj, zipinfo, decrypt=None):
        self.fileobj = fileobj
        self.decrypter = decrypt
        self.bytes_read = 0
        self.rawbuffer = b''
        self.readbuffer = b''
        self.linebuffer = b''
        self.eof = False
        self.univ_newlines = False
        self.nlSeps = (b"\n", )
        self.lastdiscard = b''

        self.compress_type = zipinfo.compress_type
        self.compress_size = zipinfo.compress_size

        self.closed  = False
        self.mode    = "r"
        self.name = zipinfo.filename

        # read from compressed files in 64k blocks
        self.compreadsize = 64*1024
        if self.compress_type == ZIP_DEFLATED:
            self.dc = zlib.decompressobj(-15)

    def set_univ_newlines(self, univ_newlines):
        self.univ_newlines = univ_newlines

        # pick line separator char(s) based on universal newlines flag
        self.nlSeps = (b"\n", )
        if self.univ_newlines:
            self.nlSeps = (b"\r\n", b"\r", b"\n")

    def __iter__(self):
        return self

    def __next__(self):
        nextline = self.readline()
        if not nextline:
            raise StopIteration()

        return nextline

    def close(self):
        self.closed = True

    def _checkfornewline(self):
        nl, nllen = -1, -1
        if self.linebuffer:
            # ugly check for cases where half of an \r\n pair was
            # read on the last pass, and the \r was discarded.  In this
            # case we just throw away the \n at the start of the buffer.
            if (self.lastdiscard, self.linebuffer[:1]) == (b'\r', b'\n'):
                self.linebuffer = self.linebuffer[1:]

            for sep in self.nlSeps:
                nl = self.linebuffer.find(sep)
                if nl >= 0:
                    nllen = len(sep)
                    return nl, nllen

        return nl, nllen

    def readline(self, size = -1):
        """Read a line with approx. size. If size is negative,
           read a whole line.
        """
        if size < 0:
            size = sys.maxsize
        elif size == 0:
            return b''

        # check for a newline already in buffer
        nl, nllen = self._checkfornewline()

        if nl >= 0:
            # the next line was already in the buffer
            nl = min(nl, size)
        else:
            # no line break in buffer - try to read more
            size -= len(self.linebuffer)
            while nl < 0 and size > 0:
                buf = self.read(min(size, 100))
                if not buf:
                    break
                self.linebuffer += buf
                size -= len(buf)

                # check for a newline in buffer
                nl, nllen = self._checkfornewline()

            # we either ran out of bytes in the file, or
            # met the specified size limit without finding a newline,
            # so return current buffer
            if nl < 0:
                s = self.linebuffer
                self.linebuffer = b''
                return s

        buf = self.linebuffer[:nl]
        self.lastdiscard = self.linebuffer[nl:nl + nllen]
        self.linebuffer = self.linebuffer[nl + nllen:]

        # line is always returned with \n as newline char (except possibly
        # for a final incomplete line in the file, which is handled above).
        return buf + b"\n"

    def readlines(self, sizehint = -1):
        """Return a list with all (following) lines. The sizehint parameter
        is ignored in this implementation.
        """
        result = []
        while True:
            line = self.readline()
            if not line: break
            result.append(line)
        return result

    def read(self, size = None):
        # act like file obj and return empty string if size is 0
        if size == 0:
            return b''

        # determine read size
        bytesToRead = self.compress_size - self.bytes_read

        # adjust read size for encrypted files since the first 12 bytes
        # are for the encryption/password information
        if self.decrypter is not None:
            bytesToRead -= 12

        if size is not None and size >= 0:
            if self.compress_type == ZIP_STORED:
                lr = len(self.readbuffer)
                bytesToRead = min(bytesToRead, size - lr)
            elif self.compress_type == ZIP_DEFLATED:
                if len(self.readbuffer) > size:
                    # the user has requested fewer bytes than we've already
                    # pulled through the decompressor; don't read any more
                    bytesToRead = 0
                else:
                    # user will use up the buffer, so read some more
                    lr = len(self.rawbuffer)
                    bytesToRead = min(bytesToRead, self.compreadsize - lr)

        # avoid reading past end of file contents
        if bytesToRead + self.bytes_read > self.compress_size:
            bytesToRead = self.compress_size - self.bytes_read

        # try to read from file (if necessary)
        if bytesToRead > 0:
            data = self.fileobj.read(bytesToRead)
            self.bytes_read += len(data)
            try:
                self.rawbuffer += data
            except:
                print(repr(self.fileobj), repr(self.rawbuffer),
                      repr(data))
                raise

            # handle contents of raw buffer
            if self.rawbuffer:
                newdata = self.rawbuffer
                self.rawbuffer = b''

                # decrypt new data if we were given an object to handle that
                if newdata and self.decrypter is not None:
                    newdata = bytes(map(self.decrypter, newdata))

                # decompress newly read data if necessary
                if newdata and self.compress_type == ZIP_DEFLATED:
                    newdata = self.dc.decompress(newdata)
                    self.rawbuffer = self.dc.unconsumed_tail
                    if self.eof and len(self.rawbuffer) == 0:
                        # we're out of raw bytes (both from the file and
                        # the local buffer); flush just to make sure the
                        # decompressor is done
                        newdata += self.dc.flush()
                        # prevent decompressor from being used again
                        self.dc = None

                self.readbuffer += newdata


        # return what the user asked for
        if size is None or len(self.readbuffer) <= size:
            data = self.readbuffer
            self.readbuffer = b''
        else:
            data = self.readbuffer[:size]
            self.readbuffer = self.readbuffer[size:]

        return data


class ZipFile:
    """ Class with methods to open, read, write, close, list zip files.

    z = ZipFile(file, mode="r", compression=ZIP_STORED, allowZip64=False)

    file: Either the path to the file, or a file-like object.
          If it is a path, the file will be opened and closed by ZipFile.
    mode: The mode can be either read "r", write "w" or append "a".
    compression: ZIP_STORED (no compression) or ZIP_DEFLATED (requires zlib).
    allowZip64: if True ZipFile will create files with ZIP64 extensions when
                needed, otherwise it will raise an exception when this would
                be necessary.

    """

    fp = None                   # Set here since __del__ checks it

    def __init__(self, file, mode="r", compression=ZIP_STORED, allowZip64=False):
        """Open the ZIP file with mode read "r", write "w" or append "a"."""
        if mode not in ("r", "w", "a"):
            raise RuntimeError('ZipFile() requires mode "r", "w", or "a"')

        if compression == ZIP_STORED:
            pass
        elif compression == ZIP_DEFLATED:
            if not zlib:
                raise RuntimeError(
                      "Compression requires the (missing) zlib module")
        else:
            raise RuntimeError("That compression method is not supported")

        self._allowZip64 = allowZip64
        self._didModify = False
        self.debug = 0  # Level of printing: 0 through 3
        self.NameToInfo = {}    # Find file info given name
        self.filelist = []      # List of ZipInfo instances for archive
        self.compression = compression  # Method of compression
        self.mode = key = mode.replace('b', '')[0]
        self.pwd = None
        self.comment = b''

        # Check if we were passed a file-like object
        if isinstance(file, str):
            # No, it's a filename
            self._filePassed = 0
            self.filename = file
            modeDict = {'r' : 'rb', 'w': 'wb', 'a' : 'r+b'}
            try:
                self.fp = io.open(file, modeDict[mode])
            except IOError:
                if mode == 'a':
                    mode = key = 'w'
                    self.fp = io.open(file, modeDict[mode])
                else:
                    raise
        else:
            self._filePassed = 1
            self.fp = file
            self.filename = getattr(file, 'name', None)

        if key == 'r':
            self._GetContents()
        elif key == 'w':
            pass
        elif key == 'a':
            try:                        # See if file is a zip file
                self._RealGetContents()
                # seek to start of directory and overwrite
                self.fp.seek(self.start_dir, 0)
            except BadZipfile:          # file is not a zip file, just append
                self.fp.seek(0, 2)
        else:
            if not self._filePassed:
                self.fp.close()
                self.fp = None
            raise RuntimeError('Mode must be "r", "w" or "a"')

    def _GetContents(self):
        """Read the directory, making sure we close the file if the format
        is bad."""
        try:
            self._RealGetContents()
        except BadZipfile:
            if not self._filePassed:
                self.fp.close()
                self.fp = None
            raise

    def _RealGetContents(self):
        """Read in the table of contents for the ZIP file."""
        fp = self.fp
        endrec = _EndRecData(fp)
        if not endrec:
            raise BadZipfile("File is not a zip file")
        if self.debug > 1:
            print(endrec)
        size_cd = endrec[_ECD_SIZE]             # bytes in central directory
        offset_cd = endrec[_ECD_OFFSET]         # offset of central directory
        self.comment = endrec[_ECD_COMMENT]     # archive comment

        # "concat" is zero, unless zip was concatenated to another file
        concat = endrec[_ECD_LOCATION] - size_cd - offset_cd
        if endrec[_ECD_SIGNATURE] == stringEndArchive64:
            # If Zip64 extension structures are present, account for them
            concat -= (sizeEndCentDir64 + sizeEndCentDir64Locator)

        if self.debug > 2:
            inferred = concat + offset_cd
            print("given, inferred, offset", offset_cd, inferred, concat)
        # self.start_dir:  Position of start of central directory
        self.start_dir = offset_cd + concat
        fp.seek(self.start_dir, 0)
        data = fp.read(size_cd)
        fp = io.BytesIO(data)
        total = 0
        while total < size_cd:
            centdir = fp.read(sizeCentralDir)
            if centdir[0:4] != stringCentralDir:
                raise BadZipfile("Bad magic number for central directory")
            centdir = struct.unpack(structCentralDir, centdir)
            if self.debug > 2:
                print(centdir)
            filename = fp.read(centdir[_CD_FILENAME_LENGTH])
            flags = centdir[5]
            if flags & 0x800:
                # UTF-8 file names extension
                filename = filename.decode('utf-8')
            else:
                # Historical ZIP filename encoding
                filename = filename.decode('cp936')
            # Create ZipInfo instance to store file information
            x = ZipInfo(filename)
            x.extra = fp.read(centdir[_CD_EXTRA_FIELD_LENGTH])
            x.comment = fp.read(centdir[_CD_COMMENT_LENGTH])
            x.header_offset = centdir[_CD_LOCAL_HEADER_OFFSET]
            (x.create_version, x.create_system, x.extract_version, x.reserved,
                x.flag_bits, x.compress_type, t, d,
                x.CRC, x.compress_size, x.file_size) = centdir[1:12]
            x.volume, x.internal_attr, x.external_attr = centdir[15:18]
            # Convert date/time code to (year, month, day, hour, min, sec)
            x._raw_time = t
            x.date_time = ( (d>>9)+1980, (d>>5)&0xF, d&0x1F,
                                     t>>11, (t>>5)&0x3F, (t&0x1F) * 2 )

            x._decodeExtra()
            x.header_offset = x.header_offset + concat
            self.filelist.append(x)
            self.NameToInfo[x.filename] = x

            # update total bytes read from central directory
            total = (total + sizeCentralDir + centdir[_CD_FILENAME_LENGTH]
                     + centdir[_CD_EXTRA_FIELD_LENGTH]
                     + centdir[_CD_COMMENT_LENGTH])

            if self.debug > 2:
                print("total", total)


    def namelist(self):
        """Return a list of file names in the archive."""
        l = []
        for data in self.filelist:
            l.append(data.filename)
        return l

    def infolist(self):
        """Return a list of class ZipInfo instances for files in the
        archive."""
        return self.filelist

    def printdir(self, file=None):
        """Print a table of contents for the zip file."""
        print("%-46s %19s %12s" % ("File Name", "Modified    ", "Size"),
              file=file)
        for zinfo in self.filelist:
            date = "%d-%02d-%02d %02d:%02d:%02d" % zinfo.date_time[:6]
            print("%-46s %s %12d" % (zinfo.filename, date, zinfo.file_size),
                  file=file)

    def testzip(self):
        """Read all the files and check the CRC."""
        chunk_size = 2 ** 20
        for zinfo in self.filelist:
            try:
                # Read by chunks, to avoid an OverflowError or a
                # MemoryError with very large embedded files.
                f = self.open(zinfo.filename, "r")
                while f.read(chunk_size):     # Check CRC-32
                    pass
            except BadZipfile:
                return zinfo.filename

    def getinfo(self, name):
        """Return the instance of ZipInfo given 'name'."""
        info = self.NameToInfo.get(name)
        if info is None:
            raise KeyError(
                'There is no item named %r in the archive' % name)

        return info

    def setpassword(self, pwd):
        """Set default password for encrypted files."""
        assert isinstance(pwd, bytes)
        self.pwd = pwd

    def read(self, name, pwd=None):
        """Return file bytes (as a string) for name."""
        return self.open(name, "r", pwd).read()

    def open(self, name, mode="r", pwd=None):
        """Return file-like object for 'name'."""
        if mode not in ("r", "U", "rU"):
            raise RuntimeError('open() requires mode "r", "U", or "rU"')
        if not self.fp:
            raise RuntimeError(
                  "Attempt to read ZIP archive that was already closed")

        # Only open a new file for instances where we were not
        # given a file object in the constructor
        if self._filePassed:
            zef_file = self.fp
        else:
            zef_file = io.open(self.filename, 'rb')

        # Make sure we have an info object
        if isinstance(name, ZipInfo):
            # 'name' is already an info object
            zinfo = name
        else:
            # Get info object for name
            zinfo = self.getinfo(name)

        zef_file.seek(zinfo.header_offset, 0)

        # Skip the file header:
        fheader = zef_file.read(sizeFileHeader)
        if fheader[0:4] != stringFileHeader:
            raise BadZipfile("Bad magic number for file header")

        fheader = struct.unpack(structFileHeader, fheader)
        fname = zef_file.read(fheader[_FH_FILENAME_LENGTH])
        if fheader[_FH_EXTRA_FIELD_LENGTH]:
            zef_file.read(fheader[_FH_EXTRA_FIELD_LENGTH])

        if fname != zinfo.orig_filename.encode("gb18030"):
            raise BadZipfile(
                  'File name in directory %r and header %r differ.'
                  % (zinfo.orig_filename, fname))

        # check for encrypted flag & handle password
        is_encrypted = zinfo.flag_bits & 0x1
        zd = None
        if is_encrypted:
            if not pwd:
                pwd = self.pwd
            if not pwd:
                raise RuntimeError("File %s is encrypted, "
                                   "password required for extraction" % name)

            zd = _ZipDecrypter(pwd)
            # The first 12 bytes in the cypher stream is an encryption header
            #  used to strengthen the algorithm. The first 11 bytes are
            #  completely random, while the 12th contains the MSB of the CRC,
            #  or the MSB of the file time depending on the header type
            #  and is used to check the correctness of the password.
            bytes = zef_file.read(12)
            h = list(map(zd, bytes[0:12]))
            if zinfo.flag_bits & 0x8:
                # compare against the file type from extended local headers
                check_byte = (zinfo._raw_time >> 8) & 0xff
            else:
                # compare against the CRC otherwise
                check_byte = (zinfo.CRC >> 24) & 0xff
            if h[11] != check_byte:
                raise RuntimeError("Bad password for file", name)

        # build and return a ZipExtFile
        if zd is None:
            zef = ZipExtFile(zef_file, zinfo)
        else:
            zef = ZipExtFile(zef_file, zinfo, zd)

        # set universal newlines on ZipExtFile if necessary
        if "U" in mode:
            zef.set_univ_newlines(True)
        return zef

    def extract(self, member, path=None, pwd=None):
        """Extract a member from the archive to the current working directory,
           using its full name. Its file information is extracted as accurately
           as possible. `member' may be a filename or a ZipInfo object. You can
           specify a different directory using `path'.
        """
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)

        if path is None:
            path = os.getcwd()

        return self._extract_member(member, path, pwd)

    def extractall(self, path=None, members=None, pwd=None):
        """Extract all members from the archive to the current working
           directory. `path' specifies a different directory to extract to.
           `members' is optional and must be a subset of the list returned
           by namelist().
        """
        if members is None:
            members = self.namelist()

        for zipinfo in members:
            self.extract(zipinfo, path, pwd)

    def _extract_member(self, member, targetpath, pwd):
        """Extract the ZipInfo object 'member' to a physical
           file on the path targetpath.
        """
        # build the destination pathname, replacing
        # forward slashes to platform specific separators.
        # Strip trailing path separator, unless it represents the root.
        if (targetpath[-1:] in (os.path.sep, os.path.altsep)
            and len(os.path.splitdrive(targetpath)[1]) > 1):
            targetpath = targetpath[:-1]

        # don't include leading "/" from file name if present
        if member.filename[0] == '/':
            targetpath = os.path.join(targetpath, member.filename[1:])
        else:
            targetpath = os.path.join(targetpath, member.filename)

        targetpath = os.path.normpath(targetpath)

        # Create all upper directories if necessary.
        upperdirs = os.path.dirname(targetpath)
        if upperdirs and not os.path.exists(upperdirs):
            os.makedirs(upperdirs)

        if member.filename[-1] == '/':
            if not os.path.isdir(targetpath):
                os.mkdir(targetpath)
            return targetpath

        source = self.open(member, pwd=pwd)
        target = open(targetpath, "wb")
        shutil.copyfileobj(source, target)
        source.close()
        target.close()

        return targetpath

    def _writecheck(self, zinfo):
        """Check for errors before writing a file to the archive."""
        if zinfo.filename in self.NameToInfo:
            if self.debug:      # Warning for duplicate names
                print("Duplicate name:", zinfo.filename)
        if self.mode not in ("w", "a"):
            raise RuntimeError('write() requires mode "w" or "a"')
        if not self.fp:
            raise RuntimeError(
                  "Attempt to write ZIP archive that was already closed")
        if zinfo.compress_type == ZIP_DEFLATED and not zlib:
            raise RuntimeError(
                  "Compression requires the (missing) zlib module")
        if zinfo.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
            raise RuntimeError("That compression method is not supported")
        if zinfo.file_size > ZIP64_LIMIT:
            if not self._allowZip64:
                raise LargeZipFile("Filesize would require ZIP64 extensions")
        if zinfo.header_offset > ZIP64_LIMIT:
            if not self._allowZip64:
                raise LargeZipFile(
                      "Zipfile size would require ZIP64 extensions")

    def write(self, filename, arcname=None, compress_type=None):
        """Put the bytes from filename into the archive under the name
        arcname."""
        if not self.fp:
            raise RuntimeError(
                  "Attempt to write to ZIP archive that was already closed")

        st = os.stat(filename)
        isdir = stat.S_ISDIR(st.st_mode)
        mtime = time.localtime(st.st_mtime)
        date_time = mtime[0:6]
        # Create ZipInfo instance to store file information
        if arcname is None:
            arcname = filename
        arcname = os.path.normpath(os.path.splitdrive(arcname)[1])
        while arcname[0] in (os.sep, os.altsep):
            arcname = arcname[1:]
        if isdir:
            arcname += '/'
        zinfo = ZipInfo(arcname, date_time)
        zinfo.external_attr = (st[0] & 0xFFFF) << 16      # Unix attributes
        if compress_type is None:
            zinfo.compress_type = self.compression
        else:
            zinfo.compress_type = compress_type

        zinfo.file_size = st.st_size
        zinfo.flag_bits = 0x00
        zinfo.header_offset = self.fp.tell()    # Start of header bytes

        self._writecheck(zinfo)
        self._didModify = True

        if isdir:
            zinfo.file_size = 0
            zinfo.compress_size = 0
            zinfo.CRC = 0
            self.filelist.append(zinfo)
            self.NameToInfo[zinfo.filename] = zinfo
            self.fp.write(zinfo.FileHeader())
            return

        with open(filename, "rb") as fp:
            # Must overwrite CRC and sizes with correct data later
            zinfo.CRC = CRC = 0
            zinfo.compress_size = compress_size = 0
            zinfo.file_size = file_size = 0
            self.fp.write(zinfo.FileHeader())
            if zinfo.compress_type == ZIP_DEFLATED:
                cmpr = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                     zlib.DEFLATED, -15)
            else:
                cmpr = None
            while 1:
                buf = fp.read(1024 * 8)
                if not buf:
                    break
                file_size = file_size + len(buf)
                CRC = crc32(buf, CRC) & 0xffffffff
                if cmpr:
                    buf = cmpr.compress(buf)
                    compress_size = compress_size + len(buf)
                self.fp.write(buf)
        if cmpr:
            buf = cmpr.flush()
            compress_size = compress_size + len(buf)
            self.fp.write(buf)
            zinfo.compress_size = compress_size
        else:
            zinfo.compress_size = file_size
        zinfo.CRC = CRC
        zinfo.file_size = file_size
        # Seek backwards and write CRC and file sizes
        position = self.fp.tell()       # Preserve current position in file
        self.fp.seek(zinfo.header_offset + 14, 0)
        self.fp.write(struct.pack("<LLL", zinfo.CRC, zinfo.compress_size,
              zinfo.file_size))
        self.fp.seek(position, 0)
        self.filelist.append(zinfo)
        self.NameToInfo[zinfo.filename] = zinfo

    def writestr(self, zinfo_or_arcname, data):
        """Write a file into the archive.  The contents is 'data', which
        may be either a 'str' or a 'bytes' instance; if it is a 'str',
        it is encoded as UTF-8 first.
        'zinfo_or_arcname' is either a ZipInfo instance or
        the name of the file in the archive."""
        if isinstance(data, str):
            data = data.encode("gb18030")
        if not isinstance(zinfo_or_arcname, ZipInfo):
            zinfo = ZipInfo(filename=zinfo_or_arcname,
                            date_time=time.localtime(time.time())[:6])
            zinfo.compress_type = self.compression
            zinfo.external_attr = 0o600 << 16
        else:
            zinfo = zinfo_or_arcname

        if not self.fp:
            raise RuntimeError(
                  "Attempt to write to ZIP archive that was already closed")

        zinfo.file_size = len(data)            # Uncompressed size
        zinfo.header_offset = self.fp.tell()    # Start of header data
        self._writecheck(zinfo)
        self._didModify = True
        zinfo.CRC = crc32(data) & 0xffffffff       # CRC-32 checksum
        if zinfo.compress_type == ZIP_DEFLATED:
            co = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                 zlib.DEFLATED, -15)
            data = co.compress(data) + co.flush()
            zinfo.compress_size = len(data)    # Compressed size
        else:
            zinfo.compress_size = zinfo.file_size
        zinfo.header_offset = self.fp.tell()    # Start of header data
        self.fp.write(zinfo.FileHeader())
        self.fp.write(data)
        self.fp.flush()
        if zinfo.flag_bits & 0x08:
            # Write CRC and file sizes after the file data
            self.fp.write(struct.pack("<LLL", zinfo.CRC, zinfo.compress_size,
                  zinfo.file_size))
        self.filelist.append(zinfo)
        self.NameToInfo[zinfo.filename] = zinfo

    def __del__(self):
        """Call the "close()" method in case the user forgot."""
        self.close()

    def close(self):
        """Close the file, and for mode "w" and "a" write the ending
        records."""
        if self.fp is None:
            return

        if self.mode in ("w", "a") and self._didModify: # write ending records
            count = 0
            pos1 = self.fp.tell()
            for zinfo in self.filelist:         # write central directory
                count = count + 1
                dt = zinfo.date_time
                dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
                dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
                extra = []
                if zinfo.file_size > ZIP64_LIMIT \
                        or zinfo.compress_size > ZIP64_LIMIT:
                    extra.append(zinfo.file_size)
                    extra.append(zinfo.compress_size)
                    file_size = 0xffffffff
                    compress_size = 0xffffffff
                else:
                    file_size = zinfo.file_size
                    compress_size = zinfo.compress_size

                if zinfo.header_offset > ZIP64_LIMIT:
                    extra.append(zinfo.header_offset)
                    header_offset = 0xffffffff
                else:
                    header_offset = zinfo.header_offset

                extra_data = zinfo.extra
                if extra:
                    # Append a ZIP64 field to the extra's
                    extra_data = struct.pack(
                            '<HH' + 'Q'*len(extra),
                            1, 8*len(extra), *extra) + extra_data

                    extract_version = max(45, zinfo.extract_version)
                    create_version = max(45, zinfo.create_version)
                else:
                    extract_version = zinfo.extract_version
                    create_version = zinfo.create_version

                try:
                    filename, flag_bits = zinfo._encodeFilenameFlags()
                    centdir = struct.pack(structCentralDir,
                        stringCentralDir, create_version,
                        zinfo.create_system, extract_version, zinfo.reserved,
                        flag_bits, zinfo.compress_type, dostime, dosdate,
                        zinfo.CRC, compress_size, file_size,
                        len(filename), len(extra_data), len(zinfo.comment),
                        0, zinfo.internal_attr, zinfo.external_attr,
                        header_offset)
                except DeprecationWarning:
                    print((structCentralDir, stringCentralDir, create_version,
                        zinfo.create_system, extract_version, zinfo.reserved,
                        zinfo.flag_bits, zinfo.compress_type, dostime, dosdate,
                        zinfo.CRC, compress_size, file_size,
                        len(zinfo.filename), len(extra_data), len(zinfo.comment),
                        0, zinfo.internal_attr, zinfo.external_attr,
                        header_offset), file=sys.stderr)
                    raise
                self.fp.write(centdir)
                self.fp.write(filename)
                self.fp.write(extra_data)
                self.fp.write(zinfo.comment)

            pos2 = self.fp.tell()
            # Write end-of-zip-archive record
            centDirCount = count
            centDirSize = pos2 - pos1
            centDirOffset = pos1
            if (centDirCount >= ZIP_FILECOUNT_LIMIT or
                centDirOffset > ZIP64_LIMIT or
                centDirSize > ZIP64_LIMIT):
                # Need to write the ZIP64 end-of-archive records
                zip64endrec = struct.pack(
                        structEndArchive64, stringEndArchive64,
                        44, 45, 45, 0, 0, centDirCount, centDirCount,
                        centDirSize, centDirOffset)
                self.fp.write(zip64endrec)

                zip64locrec = struct.pack(
                        structEndArchive64Locator,
                        stringEndArchive64Locator, 0, pos2, 1)
                self.fp.write(zip64locrec)
                centDirCount = min(centDirCount, 0xFFFF)
                centDirSize = min(centDirSize, 0xFFFFFFFF)
                centDirOffset = min(centDirOffset, 0xFFFFFFFF)

            # check for valid comment length
            if len(self.comment) >= ZIP_MAX_COMMENT:
                if self.debug > 0:
                    msg = 'Archive comment is too long; truncating to %d bytes' \
                          % ZIP_MAX_COMMENT
                self.comment = self.comment[:ZIP_MAX_COMMENT]

            endrec = struct.pack(structEndArchive, stringEndArchive,
                                 0, 0, centDirCount, centDirCount,
                                 centDirSize, centDirOffset, len(self.comment))
            self.fp.write(endrec)
            self.fp.write(self.comment)
            self.fp.flush()

        if not self._filePassed:
            self.fp.close()
        self.fp = None


class PyZipFile(ZipFile):
    """Class to create ZIP archives with Python library files and packages."""

    def writepy(self, pathname, basename=""):
        """Add all files from "pathname" to the ZIP archive.

        If pathname is a package directory, search the directory and
        all package subdirectories recursively for all *.py and enter
        the modules into the archive.  If pathname is a plain
        directory, listdir *.py and enter all modules.  Else, pathname
        must be a Python *.py file and the module will be put into the
        archive.  Added modules are always module.pyo or module.pyc.
        This method will compile the module.py into module.pyc if
        necessary.
        """
        dir, name = os.path.split(pathname)
        if os.path.isdir(pathname):
            initname = os.path.join(pathname, "__init__.py")
            if os.path.isfile(initname):
                # This is a package directory, add it
                if basename:
                    basename = "%s/%s" % (basename, name)
                else:
                    basename = name
                if self.debug:
                    print("Adding package in", pathname, "as", basename)
                fname, arcname = self._get_codename(initname[0:-3], basename)
                if self.debug:
                    print("Adding", arcname)
                self.write(fname, arcname)
                dirlist = os.listdir(pathname)
                dirlist.remove("__init__.py")
                # Add all *.py files and package subdirectories
                for filename in dirlist:
                    path = os.path.join(pathname, filename)
                    root, ext = os.path.splitext(filename)
                    if os.path.isdir(path):
                        if os.path.isfile(os.path.join(path, "__init__.py")):
                            # This is a package directory, add it
                            self.writepy(path, basename)  # Recursive call
                    elif ext == ".py":
                        fname, arcname = self._get_codename(path[0:-3],
                                         basename)
                        if self.debug:
                            print("Adding", arcname)
                        self.write(fname, arcname)
            else:
                # This is NOT a package directory, add its files at top level
                if self.debug:
                    print("Adding files from directory", pathname)
                for filename in os.listdir(pathname):
                    path = os.path.join(pathname, filename)
                    root, ext = os.path.splitext(filename)
                    if ext == ".py":
                        fname, arcname = self._get_codename(path[0:-3],
                                         basename)
                        if self.debug:
                            print("Adding", arcname)
                        self.write(fname, arcname)
        else:
            if pathname[-3:] != ".py":
                raise RuntimeError(
                      'Files added with writepy() must end with ".py"')
            fname, arcname = self._get_codename(pathname[0:-3], basename)
            if self.debug:
                print("Adding file", arcname)
            self.write(fname, arcname)

    def _get_codename(self, pathname, basename):
        """Return (filename, archivename) for the path.

        Given a module name path, return the correct file path and
        archive name, compiling if necessary.  For example, given
        /python/lib/string, return (/python/lib/string.pyc, string).
        """
        file_py  = pathname + ".py"
        file_pyc = pathname + ".pyc"
        file_pyo = pathname + ".pyo"
        if os.path.isfile(file_pyo) and \
                            os.stat(file_pyo).st_mtime >= os.stat(file_py).st_mtime:
            fname = file_pyo    # Use .pyo file
        elif not os.path.isfile(file_pyc) or \
             os.stat(file_pyc).st_mtime < os.stat(file_py).st_mtime:
            import py_compile
            if self.debug:
                print("Compiling", file_py)
            try:
                py_compile.compile(file_py, file_pyc, None, True)
            except py_compile.PyCompileError as err:
                print(err.msg)
            fname = file_pyc
        else:
            fname = file_pyc
        archivename = os.path.split(fname)[1]
        if basename:
            archivename = "%s/%s" % (basename, archivename)
        return (fname, archivename)


def main(args = None):
    import textwrap
    USAGE=textwrap.dedent("""\
        Usage:
            zipfile.py -l zipfile.zip        # Show listing of a zipfile
            zipfile.py -t zipfile.zip        # Test if a zipfile is valid
            zipfile.py -e zipfile.zip target # Extract zipfile into target dir
            zipfile.py -c zipfile.zip src ... # Create zipfile from sources
        """)
    if args is None:
        args = sys.argv[1:]

    if not args or args[0] not in ('-l', '-c', '-e', '-t'):
        print(USAGE)
        sys.exit(1)

    if args[0] == '-l':
        if len(args) != 2:
            print(USAGE)
            sys.exit(1)
        zf = ZipFile(args[1], 'r')
        zf.printdir()
        zf.close()

    elif args[0] == '-t':
        if len(args) != 2:
            print(USAGE)
            sys.exit(1)
        zf = ZipFile(args[1], 'r')
        zf.testzip()
        print("Done testing")

    elif args[0] == '-e':
        if len(args) != 3:
            print(USAGE)
            sys.exit(1)

        zf = ZipFile(args[1], 'r')
        out = args[2]
        for path in zf.namelist():
            if path.startswith('./'):
                tgt = os.path.join(out, path[2:])
            else:
                tgt = os.path.join(out, path)

            tgtdir = os.path.dirname(tgt)
            if not os.path.exists(tgtdir):
                os.makedirs(tgtdir)
            with open(tgt, 'wb') as fp:
                fp.write(zf.read(path))
        zf.close()

    elif args[0] == '-c':
        if len(args) < 3:
            print(USAGE)
            sys.exit(1)

        def addToZip(zf, path, zippath):
            if os.path.isfile(path):
                zf.write(path, zippath, ZIP_DEFLATED)
            elif os.path.isdir(path):
                for nm in os.listdir(path):
                    addToZip(zf,
                            os.path.join(path, nm), os.path.join(zippath, nm))
            # else: ignore

        zf = ZipFile(args[1], 'w', allowZip64=True)
        for src in args[2:]:
            addToZip(zf, src, os.path.basename(src))

        zf.close()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = gdkutils
'''
utils using GDK
'''

import mimetypes

from gi.repository import Gdk

def get_screen_size():
  screen = Gdk.Screen.get_default()
  return screen.width(), screen.height()

def get_moniter_size(n=0, screen=None):
    if screen is None:
        screen = Gdk.Screen.get_default()
    return Gdk.Screen.get_monitor_workarea(screen, n)

def screenshot(filename, rect=None, filetype=None):
  screen = Gdk.Screen.get_default()
  if rect is None:
    rect = (0, 0, screen.width(), screen.height())
  if filetype is None:
    t = mimetypes.guess_type(filename)[0]
    if t is None:
      raise ValueError('cannot guess filetype for filename: %s' % filename)
    filetype = t.split('/')[1]

  rootwin = screen.get_root_window()
  pixbuf = Gdk.pixbuf_get_from_window(rootwin, *rect)
  pixbuf.savev(filename, filetype, (), ())

########NEW FILE########
__FILENAME__ = geometrics
# vim:fileencoding=utf-8

from __future__ import division

from math import radians, sin, cos, acos, sqrt

# units: metres
EARTH_RADIUS = 6372797
EARTH_E_RADIUS = 6378137
EARTH_FLATTENING = 0.0033528

def d_from_origin(phi, a, b):
  r'''distance from origin to a point on an ellipse

  The ellipse is $\frac{x^2}{a^2} + \frac{y^2}{b^2} = 1$,
  and ``phi`` is the latitude in radians (angle from x-axis).

  The calculation:

  \frac{x^2}{a^2} + \frac{y^2}{b^2} = 1 \\
  x = d \cos \phi \\
  y = d \sin \phi \\
  b^2x^2 + a^2y^2 = a^2b^2\\
  b^2d^2\cos^2\phi + a^2d^2\sin^2\phi = a^2b^2 \\
  d = \frac{ab}{ \sqrt{b^2 + (a^2-b^2)\sin^2\phi} }
  '''
  b2 = b * b
  sinphi = sin(phi)
  return a * b / sqrt(b2 + (a*a - b2) * sinphi * sinphi)

def geoloc2xyz(longtitude, latitude, altitude=0, e_radius=EARTH_E_RADIUS, flattening=EARTH_FLATTENING):
  a, b = radians(longtitude), radians(latitude)
  p_radius = e_radius * (1 - flattening)

  d = d_from_origin(b, p_radius, e_radius) + altitude
  # x = d \cos a \cos b
  # y = d \sin a \cos b
  # z = d \sin b
  x = d * cos(a) * cos(b)
  y = d * sin(a) * cos(b)
  z = d * sin(b)
  return x, y, z

def distance_on_unit_sphere(p1, p2):
  # http://janmatuschek.de/LatitudeLongitudeBoundingCoordinates
  # dist = arccos(sin(lat1) · sin(lat2) + cos(lat1) · cos(lat2) · cos(lng1 - lng2)) · R
  #
  # Real distance is too hard to calculate:
  # http://mathworld.wolfram.com/Geodesic.html
  # And only <100m difference on Earth:
  # http://www.johndcook.com/blog/2009/03/02/what-is-the-shape-of-the-earth/
  # But Wolram|Alpha and Google Maps show bigger differences
  # should be less than 1%.
  lng1, lat1 = p1
  lng2, lat2 = p2
  return acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lng1 - lng2))

def distance_on_earth(loc1, loc2):
  p1 = [radians(x) for x in loc1]
  p2 = [radians(x) for x in loc2]
  return distance_on_unit_sphere(p1, p2) * EARTH_RADIUS

########NEW FILE########
__FILENAME__ = htmlutils
import re
import copy
from html.entities import entitydefs

from lxml import html

def _br2span_inplace(el):
  for br in el.iterchildren(tag='br'):
    sp = html.Element('span')
    sp.text = '\n'
    sp.tail = br.tail
    el.replace(br, sp)

def extractText(el):
  el = copy.copy(el)
  _br2span_inplace(el)
  return el.text_content()

def iter_text_and_br(el):
  for i in el.iterchildren():
    if i.tag == 'br':
      yield '\n'
    if i.tail:
      yield i.tail

def un_jsescape(s):
    '''%xx & %uxxxx -> char, opposite of Javascript's escape()'''
    return re.sub(
        r'%u([0-9a-fA-F]{4})|%([0-9a-fA-F]{2})',
        lambda m: chr(int(m.group(1) or m.group(2), 16)),
        s
    )

def entityunescape(string):
  '''HTML entity decode'''
  string = re.sub(r'&#[^;]+;', _sharp2uni, string)
  string = re.sub(r'&[^;]+;', lambda m: entitydefs[m.group(0)[1:-1]], string)
  return string

def entityunescape_loose(string):
  '''HTML entity decode. losse version.'''
  string = re.sub(r'&#[0-9a-fA-F]+[;；]?', _sharp2uni, string)
  string = re.sub(r'&\w+[;；]?', lambda m: entitydefs[m.group(0)[1:].rstrip(';；')], string)
  return string

def _sharp2uni(m):
  '''&#...; ==> unicode'''
  s = m.group(0)[2:].rstrip(';；')
  if s.startswith('x'):
    return chr(int('0'+s, 16))
  else:
    return chr(int(s))

def parse_document_from_requests(url, session, *, encoding=None):
  '''
  ``encoding``: override detected encoding
  '''
  r = session.get(url)
  if encoding:
    r.encoding = encoding

  # fromstring handles bytes well
  # http://stackoverflow.com/a/15305248/296473
  parser = html.HTMLParser(encoding=encoding or r.encoding)
  doc = html.fromstring(r.content, base_url=url, parser=parser)
  doc.make_links_absolute()

  return doc

def parse_html_with_encoding(data, encoding='utf-8'):
  parser = html.HTMLParser(encoding=encoding)
  return html.fromstring(data, parser=parser)

########NEW FILE########
__FILENAME__ = httpproxy2
'''
HTTP 代理服务器，允许在代理请求的过程中对数据进行读取或者修改

2010年9月18日
'''

import sys
from url import URL
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection
import socketserver

# 其中有些域还未填；放在这里只是为了使代码整洁
directError = r'''<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>Error 501</title>
</head><body>
<h1>Error 501: Server does not support this operation</h1>
<p>This server should be used as a HTTP proxy.</p>
<hr>
<address>{server_version} at {domain} Port {port}</address>
</body></html>'''

class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
  pass

class HTTPProxy(BaseHTTPRequestHandler):
  server_version = 'httpproxy/2'
  # 是否处理 HTTP 关于连接的头信息。不处理可能导致连接不关闭
  handleHeaders = True
  def do_remote(self, path, body=None, headers={}):
    '''和远程主机通讯，同时处理501错误（不是代理请求）'''
    if self.handleHeaders:
      del self.headers['Proxy-Connection']
      del self.headers['Keep-Alive']
      del self.headers['Proxy-Authorization']
      self.headers['Connection'] = 'close'

    if not path.scheme:
      self.send_response(501)
      self.send_header('Server', self.server_version)
      self.send_header('Content-Type', 'text/html; charset=utf-8')
      if self.command in ('GET', 'POST'):
        content = directError.format(server_version=self.server_version,
          domain=self.server.server_address[0],
          port=self.server.server_address[1]).encode('utf-8')
      else:
        content = 'Unknown Error'
      self.send_header('Content-Length', str(len(content)))
      self.end_headers()
      self.wfile.write(content)
      self.remoteResponse = None
      return

    client = HTTPConnection(path.netloc)
    headers = dict(headers)
    # 有些网站，比如 WebQQ，在 cookie 中插入了非 ASCII 字符
    # XXX：如果 UTF-8 不适合怎么办？
    for i in headers:
      headers[i] = headers[i].encode('utf-8')
    client.request(self.command, path.getpath(), body, headers)
    self.remoteResponse = client.getresponse()
    self.getdata = self.remoteResponse.read()

  def do_headers(self):
    '''向浏览器发送状态码和响应头
    
    这时远程请求已经完成，可以调用数据处理函数了'''
    self.handle_data()
    self.send_response(self.remoteResponse.status)
    for header in self.remoteResponse.getheaders():
      self.send_header(*header)
    self.end_headers()

  def do_HEAD(self):
    self.do_begin()
    self.url = URL(self.path)
    self.do_remote(self.url, headers=self.headers)
    if not self.remoteResponse:
      return
    self.do_headers()
    self.connection.close()

  def do_GET(self):
    self.do_begin()
    self.url = URL(self.path)
    self.do_remote(self.url, headers=self.headers)
    if not self.remoteResponse:
      return
    self.do_headers()
    self.wfile.write(self.getdata)
    self.connection.close()

  def do_POST(self):
    self.url = URL(self.path)
    self.postdata = self.rfile.read(int(self.headers['content-length']))
    self.do_begin()
    if len(self.postdata) != int(self.headers['content-length']):
        # bad request
        self.send_error(400, 'Post data has wrong length!')
        self.connection.close()
        return
    self.do_remote(self.url, self.postdata, headers=self.headers)
    if not self.remoteResponse:
      return
    self.do_headers()
    self.wfile.write(self.getdata)
    self.connection.close()

  def do_begin(self):
    '''
    开始处理请求了，path/url, command, headers, postdata 可用
    
    可用 headers 的 replace_header() 方法来更改数据，直接赋值无效
    url 是 path 的 URL类版本
    headers 是浏览器发送的头信息
    postdata 是 POST 方法所送出的数据

    handleHeaders 属性在此修改有效。不建议修改该属性。
    '''
    pass

  def handle_data(self):
    '''此时远程处理已完成
    
    可用的数据有：getdata postdata remoteResponse path headers
    可以更改的对象
    getdata 远端返回的数据
    headers 是浏览器发送的头信息
    postdata 是 POST 方法所送出的数据
    remoteResponse.msg 是远端的头信息，
    remoteResponse.status 为状态码'''
    pass

if __name__ == '__main__':
  # httpd = HTTPServer(('', 9999), Proxy)
  # 多线程
  httpd = ThreadingHTTPServer(('', 9999), HTTPProxy)
  print('Server started on 0.0.0.0, port 9999.....')

  # httpd.handle_request()

  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    print("\nKeyboard interrupt received, exiting.")
    httpd.server_close()
    sys.exit()

########NEW FILE########
__FILENAME__ = httpsession
'''
HTTP 会话，主要针对需要登录的服务
'''

import urllib.request
import http.cookiejar
from url import PostData
import os

class Session:
  '''通过 cookie 保持一个 HTTP 会话'''
  UserAgent = None
  def __init__(self, cookiefile='', UserAgent=None, proxy=True):
    '''
    proxy 为 True，使用环境变量，为 dict，作为代理，为假值，不使用代理
    默认使用环境变量
    '''
    self.cookie = http.cookiejar.MozillaCookieJar(cookiefile)
    if os.path.exists(cookiefile):
      self.cookie.load()
    if UserAgent is not None:
      self.UserAgent = UserAgent

    if proxy is True:
      self.urlopener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(self.cookie),
        urllib.request.ProxyHandler(),
      )
    elif isinstance(proxy, dict):
      self.urlopener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(self.cookie),
        urllib.request.ProxyHandler(proxy),
      )
    elif not proxy:
      self.urlopener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(self.cookie),
      )
    else:
      raise ValueError('unexpected proxy value')

  def request(self, url, data=None, timeout=None, headers={}, method=None):
    '''
    发送请求，返回 response 对象

    url 为字符串，data 会传给 PostData
    '''
    kwargs = {}
    # only Python 3.3+ support the method keyword
    if method is not None:
      kwargs['method'] = method

    if data:
      request = urllib.request.Request(url, PostData(data).data, **kwargs)
    else:
      request = urllib.request.Request(url, **kwargs)

    if self.UserAgent:
      request.add_header('User-Agent', self.UserAgent)
    for k, v in headers.items():
      request.add_header(k, v)
    if timeout is None:
      response = self.urlopener.open(request)
    else:
      response = self.urlopener.open(request, timeout=timeout)
    return response

  def __del__(self):
    try:
      self.cookie.save()
    except IOError as e:
      if e.errno != 2:
        raise

class Operation:
  '''与 Session 配合使用，说明一个会话中可能的操作'''
  def login(self, url, logindata, checkfunc):
    '''logindata 是登录字典，checkfunc 返回登录成功与否'''
    logindata = PostData(logindata).data
    response = self.request(url, logindata)
    return checkfunc(response)

  def logout(self):
    '''删除 cookie 好了'''
    os.unlink(self.cookie.filename)

def make_cookie(name, value, expires=None, domain='', path='/'):
  '''
  returns a Cookie instance that you can add to a cookiejar

  expires: the time in seconds since epoch of time
  '''
  return http.cookiejar.Cookie(
    version=0, name=name, value=value, port=None, port_specified=False,
    domain=domain, domain_specified=False, domain_initial_dot=False,
    path=path, path_specified=True, secure=False, expires=expires,
    discard=None, comment=None, comment_url=None, rest={'HttpOnly': None},
    rfc2109=False
  )

########NEW FILE########
__FILENAME__ = icmplib
import socket as _socket
import time
import struct

'''
Utilities for ICMP socket.

For the socket usage: https://lkml.org/lkml/2011/5/10/389
For the packet structure: https://bitbucket.org/delroth/python-ping
'''

ICMP_ECHO_REQUEST = 8
_d_size = struct.calcsize('d')

def pack_packet(seq, payload):
  # Header is type (8), code (8), checksum (16), id (16), sequence (16)
  # The checksum is always recomputed by the kernel, and the id is the port number
  header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0, 0, 0, seq)
  return header + payload

def parse_packet(data):
  type, code, checksum, packet_id, sequence = struct.unpack('bbHHh', data[:8])
  return sequence, data[8:]

def pack_packet_with_time(seq, packetsize=56):
  padding = (packetsize - _d_size) * b'Q'
  timeinfo = struct.pack('d', time.time())
  return pack_packet(seq, timeinfo + padding)

def parse_packet_with_time(data):
  seq, payload = parse_packet(data)
  t = struct.unpack('d', payload[:_d_size])[0]
  return seq, t

def socket():
  return _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM, _socket.IPPROTO_ICMP)

def ping(address):
  address = _socket.gethostbyname(address)
  s = socket()
  s.sendto(pack_packet_with_time(1), (address, 0))
  packet, peer = s.recvfrom(1024)
  _, t = parse_packet_with_time(packet)
  return time.time() - t

def main():
  import sys
  if len(sys.argv) != 2:
    sys.exit('where to ping?')
  t = ping(sys.argv[1])
  print('%9.3fms.' % (t * 1000))

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = ja2zh
#!/usr/bin/env python3
# vim:fileencoding=utf-8

import sys
import json
import socket
import urllib.request

from url import PostData

def translate(text, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
  post = {
    'from': 'jp',
    'to': 'zh',
    'ie': 'utf-8',
    'source': 'txt',
    'query': text,
  }
  ans = urllib.request.urlopen('http://fanyi.baidu.com/transcontent', PostData(post).data, timeout=timeout).read().decode('utf-8')
  result = json.loads(ans)
  return '\n'.join([x['dst'] for x in result['data']])

if __name__ == '__main__':
  if len(sys.argv) == 2:
    print(translate(sys.argv[1]))
  elif len(sys.argv) == 1:
    print(translate(sys.stdin.read()))
  else:
    sys.exit('what to translate?')

########NEW FILE########
__FILENAME__ = jsonprotocol
# vim:fileencoding=utf-8

try:
  import ujson as json
except ImportError:
  import json
import struct

def parse_netint(b):
  return struct.unpack('!I', b)[0]

def pack_netint(i):
  return struct.pack('!I', i)

def recvbytes(sock, length):
  got = 0
  data = []
  while got < length:
    r = sock.recv(length - got)
    if not r:
      return
    got += len(r)
    data.append(r)
  return b''.join(data)

def fromjson(s):
  return json.loads(s)

def tojson(d):
  return json.dumps(d, ensure_ascii=False)

def write_response(sock, s):
  if isinstance(s, dict):
    s = tojson(s)
  if isinstance(s, str):
    s = s.encode('utf-8')
  sock.sendall(pack_netint(len(s)) + s)

def read_response(sock):
  r = recvbytes(sock, 4)
  if not r:
    return

  length = parse_netint(r)
  data = recvbytes(sock, length).decode('utf-8')
  if data is None:
    raise Exception('client disappeared suddenly')
  return fromjson(data)


########NEW FILE########
__FILENAME__ = latin1enctrans
'''
Latin1-encoding Translations

This class uses latin1 encoding when parsing the .mo file so that we won't encounter
fatal errors (e.g. Vim's French translation).

Just import this module and the strict GNUTranslations is replaced.

>>> T = gettext.translation('vim', localedir='/usr/share/vim/vim73/lang', languages=['fr'])
'''

import gettext

class GNUTranslations(gettext.GNUTranslations):
    def _parse(self, fp):
        """Override this method to support alternative .mo formats."""
        unpack = gettext.struct.unpack
        filename = getattr(fp, 'name', '')
        # Parse the .mo file header, which consists of 5 little endian 32
        # bit words.
        self._catalog = catalog = {}
        self.plural = lambda n: int(n != 1) # germanic plural by default
        buf = fp.read()
        buflen = len(buf)
        # Are we big endian or little endian?
        magic = unpack('<I', buf[:4])[0]
        if magic == self.LE_MAGIC:
            version, msgcount, masteridx, transidx = unpack('<4I', buf[4:20])
            ii = '<II'
        elif magic == self.BE_MAGIC:
            version, msgcount, masteridx, transidx = unpack('>4I', buf[4:20])
            ii = '>II'
        else:
            raise IOError(0, 'Bad magic number', filename)
        # Now put all messages from the .mo file buffer into the catalog
        # dictionary.
        for i in range(0, msgcount):
            mlen, moff = unpack(ii, buf[masteridx:masteridx+8])
            mend = moff + mlen
            tlen, toff = unpack(ii, buf[transidx:transidx+8])
            tend = toff + tlen
            if mend < buflen and tend < buflen:
                msg = buf[moff:mend]
                tmsg = buf[toff:tend]
            else:
                raise IOError(0, 'File is corrupt', filename)
            # See if we're looking at GNU .mo conventions for metadata
            if mlen == 0:
                # Catalog description
                lastk = k = None
                for b_item in tmsg.split('\n'.encode("ascii")):
                    # use latin1 encoding so that we won't encounter fatal errors
                    item = b_item.decode('latin1').strip()
                    if not item:
                        continue
                    if ':' in item:
                        k, v = item.split(':', 1)
                        k = k.strip().lower()
                        v = v.strip()
                        self._info[k] = v
                        lastk = k
                    elif lastk:
                        self._info[lastk] += '\n' + item
                    if k == 'content-type':
                        self._charset = v.split('charset=')[1]
                    elif k == 'plural-forms':
                        v = v.split(';')
                        plural = v[1].split('plural=')[1]
                        self.plural = c2py(plural)
            # Note: we unconditionally convert both msgids and msgstrs to
            # Unicode using the character encoding specified in the charset
            # parameter of the Content-Type header.  The gettext documentation
            # strongly encourages msgids to be us-ascii, but some applications
            # require alternative encodings (e.g. Zope's ZCML and ZPT).  For
            # traditional gettext applications, the msgid conversion will
            # cause no problems since us-ascii should always be a subset of
            # the charset encoding.  We may want to fall back to 8-bit msgids
            # if the Unicode conversion fails.
            charset = self._charset or 'ascii'
            if b'\x00' in msg:
                # Plural forms
                msgid1, msgid2 = msg.split(b'\x00')
                tmsg = tmsg.split(b'\x00')
                msgid1 = str(msgid1, charset)
                for i, x in enumerate(tmsg):
                    catalog[(msgid1, i)] = str(x, charset)
            else:
                catalog[str(msg, charset)] = str(tmsg, charset)
            # advance to next entry in the seek tables
            masteridx += 8
            transidx += 8

gettext.GNUTranslations = GNUTranslations

########NEW FILE########
__FILENAME__ = lilydeco
def run_in_thread(daemon):
  import threading
  fn = None
  def run(*k, **kw):
    t = threading.Thread(target=fn, args=k, kwargs=kw)
    t.daemon = daemon
    t.start()
    return t
  if isinstance(daemon, bool):
    def wrapper(callback):
      nonlocal fn
      fn = callback
      return run
    return wrapper
  else:
    fn = daemon
    daemon = False
    return run


########NEW FILE########
__FILENAME__ = lilypath
# vim:fileencoding=utf-8

'''
更简单的路径处理

lilydjwg <lilydjwg@gmail.com>

2010年11月13日
'''

# 模仿 URL:http://www.jorendorff.com/articles/python/path ver 3.0b1

import os
import sys
from datetime import datetime

__version__ = '0.2'

class path:
  def __init__(self, string='.'):
    self.value = str(string)

  def __str__(self):
    return self.value

  def __repr__(self):
    return '%s(%r)' % (self.__class__.__name__, str(self))

  def __hash__(self):
    st = self.stat()
    return int('%d%d%02d%d' % (st.st_ino, st.st_dev,
        len(str(st.st_ino)), len(str(st.st_dev))))

  def __add__(self, more):
    return self.__class__(self).join(more)

  def __radd__(self, more):
    return self.__class__(self).head(more)

  def __eq__(self, another):
    '''是否为同一文件'''
    return os.path.samefile(self.value, str(another))

  def __contains__(self, another):
    '''another 是否在此路径下'''
    child = os.path.abspath(str(another))
    parent = self.abspath
    if parent == child:
      return True
    if child.startswith(parent) and child[len(parent)] == '/':
      return True
    else:
      return False

  def __lt__(self, another):
    return str.__lt__(str(self), str(another))

  @property
  def abspath(self):
    return os.path.abspath(self.value)

  @property
  def basename(self):
    return os.path.basename(self.value)

  @property
  def rootname(self):
    '''除去扩展名的路径名的 basename'''
    return os.path.splitext(self.basename)[0]

  @property
  def extension(self):
    '''扩展名'''
    return os.path.splitext(self.basename)[1]

  @property
  def realpath(self):
    return os.path.realpath(self.value)

  @property
  def mode(self):
    return self.stat().st_mode

  @property
  def inode(self):
    return self.stat().st_ino

  @property
  def dev(self):
    return self.stat().st_dev

  @property
  def size(self):
    '''以字节表示的文件大小'''
    return self.stat().st_size

  @property
  def atime(self):
    return datetime.fromtimestamp(self.stat().st_atime)
  @property
  def mtime(self):
    return datetime.fromtimestamp(self.stat().st_mtime)
  @property
  def ctime(self):
    return datetime.fromtimestamp(self.stat().st_ctime)
  def stat(self):
    return os.stat(self.value)
  def access(self, mode):
    return os.access(self.value, mode)
  def olderthan(self, another):
    '''比较文件的最后修改时间'''
    if not isinstance(another, path):
      raise TypeError('不能和非 path 对象比较')
    return self.mtime < another.mtime
  def newerthan(self, another):
    return another.olderthan(self)
  def readlink(self):
    return os.readlink(self.value)
  def join(self, *more):
    '''连接路径，使用正确的分隔符'''
    self.value = os.path.join(self.value, *(str(x) for x in more))
    return self

  def head(self, *more):
    '''在路径头部插入，使用正确的分隔符'''
    header = os.path.join(*(str(x) for x in more))
    self.value = os.path.join(header, self.value)
    return self

  def expanduser(self):
    self.value = os.path.expanduser(self.value)
    return self

  def expandvars(self):
    self.value = os.path.expandvars(self.value)
    return self

  def normpath(self):
    self.value = os.path.normpath(self.value)
    return self

  def expand(self):
    '''扩展所有能扩展的，也就是 expanduser 和 expandvars，然后 normpath'''
    self.expanduser().expandvars().normpath()
    return self

  def toabspath(self):
    '''转换为绝对路径'''
    self.value = os.path.abspath(self.value)
    return self

  def torealpath(self):
    '''转换为真实路径'''
    self.value = os.path.realpath(self.value)
    return self

  def islink(self):
    return os.path.islink(self.value)

  def isdir(self):
    return os.path.isdir(self.value) and not os.path.islink(self.value)

  def isfile(self):
    return os.path.isfile(self.value)

  def exists(self):
    return os.path.exists(self.value)

  def lexists(self):
    return os.path.lexists(self.value)

  def parent(self):
    '''父目录'''
    return self.__class__(self.value).join('..').normpath()

  def list(self, nameonly=False):
    '''
    路径下所有的东东，如同 os.listdir()，不包含 . 和 ..

    nameonly 指定是只返回名字还是返回 path 对象
    '''
    if nameonly:
      return os.listdir(self.value)
    else:
      return [self + self.__class__(x) for x in os.listdir(self.value)]

  def dirs(self, nameonly=False):
    '''路径下所有的目录'''
    if nameonly:
      return [x.basename for x in self.list() if x.isdir()]
    else:
      return [x for x in self.list() if x.isdir()]

  def files(self, nameonly=False):
    '''路径下所有的文件'''
    if nameonly:
      return [x.basename for x in self.list() if x.isfile()]
    else:
      return [x for x in self.list() if x.isfile()]

  def rmdir(self):
    os.rmdir(self.value)
    return self

  def unlink(self, recursive=False):
    '''删除该路径'''
    if self.isdir():
      if recursive:
        for x in self.list():
          x.unlink(True)
      os.rmdir(self.value)
    else:
      os.unlink(self.value)

    return self

  def linksto(self, target, hardlink=False):
    target = str(target)
    if hardlink:
      os.link(target, self.value)
    else:
      os.symlink(target, self.value)

  def mkdir(self, *dirs):
    '''作为目录建立该路径，自动创建上层目录；
    或者在路径下创建目录，要求此路径已经存在。'''
    if dirs:
      if self.exists():
        for d in dirs:
          (self+d).mkdir()
      else:
        raise OSError(2, os.strerror(2), str(self))
    else:
      if self.parent().isdir():
        os.mkdir(str(self))
      elif not self.parent().exists():
        self.parent().mkdir()
        os.mkdir(str(self))
      else:
        raise OSError(17, os.strerror(17), str(self.parent()))
    return self

  def rename(self, newname):
    '''文件更名，同时更新本对象所指'''
    os.rename(self.value, newname)
    self.value = newname
    return self

  def copyto(self, newpath):
    '''复制文件，同时更新本对象所指'''
    newpath = self.__class__(newpath)
    if newpath.isdir():
      newpath.join(self.basename)
    import shutil
    shutil.copy2(self.value, newpath.value)
    self.value = newpath.value

  def moveto(self, newpath):
    '''移动文件，同时更新本对象所指'''
    newpath = self.__class__(newpath)
    if newpath.isdir():
      newpath.join(self.basename)
    import shutil
    shutil.move(self.value, newpath.value)
    self.value = newpath.value

  def glob(self, pattern):
    '''返回 list'''
    import glob
    return list(map(path, glob.glob(str(self+pattern))))

  def copy(self):
    '''复制对象并返回之'''
    return self.__class__(self.value)

  def open(self, mode='r', buffering=2, encoding=None, errors=None,
      newline=None, closefd=True):
    '''打开该文件'''
    #XXX 文档说buffering默认值为 None，但事实并非如此。使用full buffering好了
    return open(self.value, mode, buffering, encoding, errors, newline, closefd)

  def traverse(self, follow_links=True):
    '''遍历目录'''
    for i in self.list():
      yield i
      if i.isdir() and (follow_links or not i.islink()):
        for j in i.traverse():
          yield j

class sha1path(path):
  '''使用 sha1 作为文件是否相同的 path'''
  def __eq__(self, another):
    # 先比较文件大小
    if self.size != another.size:
      return False
    return self.sha1() == another.sha1()
  def sha1(self, force=False):
    '''force 为真重读文件'''
    if not hasattr(self, '_sha1') or force:
      import hashlib
      s = hashlib.sha1()
      with self.open('rb') as f:
        while True:
          data = f.read(4096)
          if data:
            s.update(data)
          else:
            break
      self._sha1 = s.hexdigest()
    return self._sha1

########NEW FILE########
__FILENAME__ = mailutils
# vim:fileencoding=utf-8

import re
from email import header
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

addr_re = re.compile(r'(.*?)\s+(<[^>]+>)($|,\s*)')

def decode_multiline_header(s):
  ret = []

  for b, e in header.decode_header(re.sub(r'\n\s+', ' ', s)):
    if e:
      if e.lower() == 'gb2312':
        e = 'gb18030'
      b = b.decode(e)
    elif isinstance(b, bytes):
      b = b.decode('ascii')
    ret.append(b)

  return ''.join(ret)

def assemble_mail(subject, to, from_, html=None, text=None):
  if html is None and text is None:
    raise TypeError('no message given')

  if html:
    html = MIMEText(html, 'html', 'utf-8')
  if text:
    text = MIMEText(text, 'plain', 'utf-8')

  if html and text:
    msg = MIMEMultipart('alternative', _subparts = [text, html])
  else:
    msg = html or text

  msg['Subject'] = encode_header(subject)
  msg['From'] = encode_header_address(from_)
  msg['To'] = encode_header_address(to)

  return msg

def encode_header_address(s):
  return addr_re.sub(_addr_submatch, s)

def encode_header(s):
  return Header(s, 'utf-8').encode() if not eight_bit_clean(s) else s

def _addr_submatch(m):
  return encode_header(m.group(1)) + ' ' + m.group(2) + m.group(3)

def eight_bit_clean(s):
  return all(ord(c) < 128 for c in s)

########NEW FILE########
__FILENAME__ = mb3
#!/usr/bin/env python3
# vim:fileencoding=utf-8:sw=2

'''操作 fcitx 的码表文件（第三版，针对UTF-8版）'''
import sys
import struct
import algorithm

version = 0.3

# 测试/调试设置
# msg = True
msg = False
timeit = True

if msg and timeit:
  from datetime import datetime

class Record:
  '''一条记录'''
  def __init__(self, code, hz, hit=0, index=0, ispy=False):
    self.code = code
    self.hz = hz
    self.hit = hit
    self.index = index
    self.ispy = ispy

  def __lt__(self, x):
    return self.code < x.code

  def __eq__(self, x):
    return self.code == x.code and self.hz == x.hz

  def __le__(self, x):
    return self < x or self.code == x.code

  def __repr__(self):
    '''表示法，与输出到文本文件时一致（除了<>）'''
    if self.ispy:
      f = '<@{0.code} {0.hz} {0.hit} {0.index}>'
    else:
      f = '<{0.code} {0.hz} {0.hit} {0.index}>'
    return f.format(self)

  def __str__(self):
    return '[{0.code}:{0.hz}]'.format(self)

  def toString(self, verbose=False):
    '''输出到文本文件时用'''
    if verbose:
      f = '{0.code} {0.hz} {0.hit} {0.index}'
    else:
      f = '{0.code} {0.hz}'
    if self.ispy:
      f = '@' + f
    return f.format(self)

  def update(self, ref=None, code=None, hz=None, hit=0, index=0, ispy=False):
    '''更新数据，根据 ref 或者手动指定值'''
    if not any((code, hz, hit, index, ispy)):
      if ref:
        self.code = ref.code
        self.hz = ref.hz
        self.hit = ref.hit
        self.index = ref.index
        self.ispy = ref.ispy
      else:
        raise TypeError('参数过少。')
    else:
      if code:
        self.code = code
      if hz:
        self.hz = hz
      if hit:
        self.hit = hit
      if index:
        self.index = index
      if ispy:
        self.ispy = ispy

class mbTable:
  '''小企鹅输入法码表对象'''
  # TODO 在不用此对象时释放内存
  文件名 = None
  版本 = None
  键码 = None
  码长 = None
  规避字符 = ''
  拼音长度 = None
  组词规则 = None
  数据 = []
  编码 = set()
  modified = False

  def __getitem__(self, i):
    '''可以直接通过下标访问某个编码的数据'''
    return self.数据[i]

  def __delitem__(self, i):
    '''也可以直接通过下标来删除'''
    del self.数据[i]

  def __init__(self, file=None):
    '''初始化对象，可选从某个文件载入
或者以后手动通过 self.load 从字符串载入'''
    # 将文件全部读入。希望这个文件不会太大。
    # 如果以后逐步读取的话会更花时间
    self.文件名 = file
    if file:
      data = open(file, 'rb').read()
      self.load(data)

  def __repr__(self):
    return '<小企鹅输入法码表对象，来自文件 “%s”。>' % self.文件名

  def __str__(self):
    '''这个码表的信息'''
    return '''版本：{版本}
键码：{键码}
码长：{码长}
规避字符：{规避字符}
拼音长度：{拼音长度}
组词规则：{组词规则}
数据：{数据} 条
修改过（不一定可靠）：{modified}'''.format(版本=self.版本,
        键码=self.键码,
        码长=self.码长,
        规避字符=self.规避字符,
        拼音长度=self.拼音长度,
        组词规则=self.组词规则,
        数据=self.size(),
        modified=self.modified,
    )


  def autoCode(self, hz):
    '''自动生成词的编码'''
    # 造词一次测试用时 0.26+ 秒
    if not self.组词规则:
      raise self.autoCodeError('组词失败，因为当前码表没有组词规则可用')

    for i in self.组词规则:
      if (i[0] == 'e' and int(i[1]) == len(hz)) or (i[0] == 'a'
          and len(hz) >= int(i[1])):
        break
    else:
      raise self.autoCodeError('组词失败，因为没有找到对长度为 %d 的词的组词规则' % len(hz))

    if msg:
      print('自动造词...')
      if timeit:
        imeitstart = datetime.today()
    a = i[3:].split('+')
    c = ''
    for j in a:
      # 分析一次测试用时 0.06x 秒
      longestHere = -1
      if msg:
        print('分析组词规则...')
        if timeit:
          timeitstart = datetime.today()
      if j[0] == 'p': # 正序
        zx = True
      elif j[0] == 'n': # 逆序
        zx = False
      else:
        raise self.autoCodeError('不能识别的组词规则 %s' % i)
      if zx:
        字 = hz[int(j[1])-1]
      else:
        字 = hz[-int(j[1])]
      # 找出最长的编码；五笔有简码的
      longest = 0
      for i in self.search(字):
        length = len(self[i].code)
        if length > longest:
          longest = length
          longestHere = i
      if msg:
        print('分析完毕。')
        if timeit:
          print('用时', datetime.today() - timeitstart)
      try:
        if longestHere == -1:
          raise self.autoCodeError('组词失败，因为我没能找到“%s”的编码' % 字)
        c += self.数据[longestHere].code[int(j[2])-1]
      except IndexError:
        raise self.autoCodeError('组词失败，因为“%s”的编码太短了' % 字)

    if msg:
      print('自动造词完毕。')
      if timeit:
        print('用时', datetime.today() - imeitstart)
    return c

  def delete(self, code=None, hz=None):
    '''删除指定项，返回删除的条数'''
    count = 0

    # 按编码
    if code and not hz:
      pos = self.getpos(code)
      while self.数据[pos].code == code:
        del self.数据[pos]
        count += 1
        # pos = self.getpos(code)
      if count: self.modified = True
      return count

    # 按编码和汉字
    # 也可以用 remove，不过这样似乎快一点
    if code and hz:
      pos = self.getpos(code)
      while self.数据[pos].code == code:
        if self.数据[pos].hz == hz:
          count += 1
          del self.数据[pos]
          # 假设没有重复项
          break
        pos += 1
      if count: self.modified = True
      return count

    # 只按汉字
    if hz:
      pos = self.search(hz)
      for i in pos:
        # 删一个就少一个
        del self.数据[i-count]
        count += 1
      if count: self.modified = True
      return count

    raise self.argsError('code 和 hz 至少要指明一项')

  def get(self, record):
    '''
    获取 record 以便修改
    
    record 是 Record 对象
    '''
    pos = self.getpos(record)
    try:
      while self.数据[pos].code == record.code:
        # 注意到虽然编码排序了，但汉字部分并没有排序
        if self.数据[pos] == record:
          return self.数据[pos]
        else:
          pos += 1
    except IndexError:
      pass
    raise self.RecordNotExist(record)

  def getpos(self, record):
    '''获取 record 的位置。如果它不存在，获取它应当被插入的位置
    
record 可以是 Record 对象或者表示编码的字符串'''
    if isinstance(record, Record):
      return algorithm.二分搜索(self.数据, record)
    else:
      return algorithm.二分搜索(self.数据, record, (lambda x, y: x > y.code))

  def getbycode(self, code):
    '''获取 code 对应的数据'''
    pos = self.getpos(code)
    ret = []
    try:
      while self.数据[pos].code == code:
        ret.append(self.数据[pos])
        pos += 1
    except IndexError:
      pass

    return ret

  def gethz(self, code):
    '''获取 code 对应的汉字'''
    pos = self.getpos(code)
    ret = []
    try:
      while self.数据[pos].code == code:
        ret.append(self.数据[pos].hz)
        pos += 1
    except IndexError:
      pass

    return ret

  def getsimilar(self, code, similar=1):
    '''寻找相似的编码（相似度小于等于 similar 者）'''
    # 测试用时 (查询编码的长度).x 秒

    # 列出所有编码
    # 测试用时 0.0x 秒
    if msg:
      print('查询相似编码...')
      if timeit:
        imeitstart = datetime.today()
    if not self.编码:
      if msg:
        print('生成编码集合...')
        if timeit:
          timeitstart = datetime.today()
      for i in self.数据:
        self.编码.add(i.code)
      if msg:
        print('编码集合生成完毕。')
        if timeit:
          print('用时', datetime.today() - timeitstart)

    ret = []
    for i in self.编码:
      if algorithm.LevenshteinDistance(code, i) <= similar:
        ret.append(i)

    if msg:
      print('相似编码查询完毕。')
      if timeit:
        print('用时', datetime.today() - imeitstart)
    return ret 

  def insert(self, code, hz, hit=0, index=0, ispy=False):
    '''插入记录'''
    if not self.maybeCode(code):
      raise self.argsError('不符合当前码表编码的格式')

    t = Record(code, hz, hit, index, ispy)
    try:
      self.get(t)
      # 已经存在
      raise self.RecordExists(t)
    except self.RecordNotExist:
      self.数据.insert(self.getpos(t), t)
      self.modified = True

  def load(self, data):
    '''
    从字符串载入数据

    此字符串应该来源于码表文件
    通常不需要手动调用此方法
    '''
    start = 0

    # 载入码表属性测试用时 0.001x 秒
    # 版本号
    fmt = '<I'
    size = 4
    x = struct.unpack(fmt, data[:size])[0]
    start += size
    if x:
      self.版本 = 2
    else:
      fmt = '<B'
      size = 1
      self.版本 = struct.unpack(fmt, data[start:start+size])[0]
      start += size

    # 键码字串
    fmt = '<I'
    size = 4
    x = struct.unpack(fmt, data[start:start+size])[0]
    start += size
    fmt = '<' + str(x+1) + 's'
    size = struct.calcsize(fmt)
    self.键码 = struct.unpack(fmt, data[start:start+size])[0][:-1].decode('utf-8')
    start += size

    # 码长
    fmt = '<B'
    size = 1
    self.码长 = struct.unpack(fmt, data[start:start+size])[0]
    start += size

    # 拼音长度
    if self.版本:
      fmt = '<B'
      size = 1
      self.拼音长度 = struct.unpack(fmt, data[start:start+size])[0]
      start += size

    # 规避字符
    fmt = '<I'
    size = 4
    x = struct.unpack(fmt, data[start:start+size])[0]
    start += size
    fmt = '<' + str(x+1) + 's'
    size = struct.calcsize(fmt)
    self.规避字符 = struct.unpack(fmt, data[start:start+size])[0][:-1].decode('utf-8')
    start += size

    # 组词规则
    fmt = '<B'
    size = 1
    x = struct.unpack(fmt, data[start:start+size])[0]
    start += size
    if x: # 有组词规则
      self.组词规则 = [''] * (self.码长-1)
      for i in range(self.码长-1):
        fmt = '<BB'
        size = 2
        x = struct.unpack(fmt, data[start:start+size])
        start += size
        if x[0]:
          self.组词规则[i] = 'a'
        else:
          self.组词规则[i] = 'e'
        self.组词规则[i] += str(x[1])
        self.组词规则[i] += '='
        for j in range(self.码长):
          fmt = '<BBB'
          size = 3
          x = struct.unpack(fmt, data[start:start+size])
          start += size
          if x[0]:
            self.组词规则[i] += 'p'
          else:
            self.组词规则[i] += 'n'
          self.组词规则[i] += str(x[1])
          self.组词规则[i] += str(x[2])
          if j != self.码长 - 1:
            self.组词规则[i] += '+'

    # 词的数量
    fmt = '<I'
    size = 4
    x = struct.unpack(fmt, data[start:start+size])[0]
    start += size

    if msg:
      print('载入数据中...')
      if timeit:
        timeitstart = datetime.today()
    # 读数据了
    # 测试用时近两秒
    # XXX 如果没有 版本？
    if self.版本:
      fmt2 = '<' + str(self.拼音长度+1) + 's'
    size2 = struct.calcsize(fmt2)
    for i in range(x):
      # 键码
      fmt = fmt2
      size = size2
      x = struct.unpack(fmt, data[start:start+size])[0]
      try:
        code = x[:x.find(b'\x00')].decode('utf-8')
      except UnicodeDecodeError:
        return
      start += size
      # 汉字
      fmt = '<I'
      size = 4
      x = struct.unpack(fmt, data[start:start+size])[0]
      start += size
      fmt = '<' + str(x) + 's'
      size = struct.calcsize(fmt)
      hz = struct.unpack(fmt, data[start:start+size])[0][:-1].decode('utf-8')
      start += size

      ispy = False
      if self.版本:
        # 拼音指示
        fmt = '<B'
        size = 1
        x = struct.unpack(fmt, data[start:start+size])[0]
        start += size
        if x:
          ispy = True

      # 词频信息
      fmt = '<II'
      size = 8
      x = struct.unpack(fmt, data[start:start+size])
      start += size
      hit = x[0]
      index = x[1]

      # 添加一个记录
      self.数据.append(Record(code, hz, hit, index, ispy))
    if msg:
      print('数据载入完成。')
      if timeit:
        print('用时', datetime.today() - timeitstart)

  def loadFromTxt(self, txtfile, encoding='utf-8'):
    '''从导出的纯文本文件中导入（不建议使用！）

适用于在导出修改后的情况，这时不要载入码表文件
注意：不保证对所有情况适用
      数据部分必须排序

因C++版的程序由于算法有问题导致重复项，考虑导出修改后再导入而写'''

    import re
    with open(txtfile, encoding=encoding) as txt:
      self.版本 = int(re.search(r'0x\d{2}', txt.readline()).group(0), 16)
      l = txt.readline().rstrip()
      self.键码 = l[l.find('=')+1:]
      l = txt.readline().rstrip()
      self.码长 = int(l[l.find('=')+1:])
      txt.readline()
      l = txt.readline().rstrip()
      self.拼音长度 = int(l[l.find('=')+1:])
      l = txt.readline().rstrip()
      if l == '[组词规则]':
        self.组词规则 = []
        l = txt.readline().rstrip()
        while l != '[数据]':
          self.组词规则.append(l)
          l = txt.readline().rstrip()
      if l == '[数据]':
        l = txt.readline()
        while l:
          l = l.split(' ') # 以英文空格分隔，不含全角空格
          if l[0].startswith('@'):
            self.数据.append(Record(l[0][1:], l[1], int(l[2]), int(l[3]), True))
          else:
            self.数据.append(Record(l[0], l[1], int(l[2]), int(l[3])))
          l = txt.readline()

      self.modified = True

  def maybeCode(self, string):
    '''string 可能是合法的编码吗？'''
    if len(string) > self.码长:
      return False
    for i in string:
      if i not in self.键码:
        return False
    return True

  def print(self, 文件=None, 词频=False, 编码='utf-8'):
    '''以纯文本方式输出
    
如果词频为 False 并且编码为默认的话，所得文件与 mb2txt 程序产生的
完全一致'''

    # 不打印词频时测试用时 2.5x 秒
    # 打印词频时测试用时 2.7x 秒
    if 文件:
      f = open(文件, 'w', encoding=编码)
    else:
      f = sys.stdout

    # 打印码表属性 0.0003x 秒
    print(';fcitx 版本', '0x%02x' % self.版本, '码表文件', file=f)
    print('键码='+self.键码, file=f)
    print('码长=%d' % self.码长, file=f)
    if self.拼音长度:
      print('拼音=@', file=f)
      print('拼音长度=%d' % self.拼音长度, file=f)
    if self.规避字符:
      print('规避字符=' + self.规避字符, file=f)
    if self.组词规则:
      print('[组词规则]', file=f)
      for i in self.组词规则:
        print(i, file=f)
    if msg:
      print('打印数据...')
      if timeit:
        timeitstart = datetime.today()
    print('[数据]', file=f)
    lastcode = ''
    tmpRecords = []
    for i in self.数据 :
      if i.code == lastcode:
        tmpRecords.append(i)
      elif tmpRecords:
        tmpRecords.sort(key=lambda x: -x.index)
        for j in tmpRecords:
          print(j.toString(词频), file=f)
        lastcode = i.code
        tmpRecords = [i]
      else:
        lastcode = i.code
        tmpRecords = [i]
    if msg:
      print('打印数据完成。')
      if timeit:
        print('用时', datetime.today() - timeitstart)

  def save(self):
    '''保存到原文件'''
    self.write(self.文件名)

  def search(self, hz, 搜寻子串=False):
    '''寻找汉字，返回索引列表，搜寻子串 指示是否要准确匹配
    
返回结果总是排序过的'''
    # 精确匹配时测试用时 0.06x 秒
    # 模糊匹配时测试用时 0.1x 秒
    if msg:
      print('查询汉字...')
      if timeit:
        timeitstart = datetime.today()
    ret = []
    if not 搜寻子串:
      for i in range(len(self.数据)):
        if self.数据[i].hz == hz:
          ret.append(i)
    else:
      for i in range(len(self.数据)):
        if self.数据[i].hz.find(hz) != -1:
          ret.append(i)
    if msg:
      print('汉字查询完成。')
      if timeit:
        print('用时', datetime.today() - timeitstart)
    return ret

  def set(self, code, hz, hit=0, index=0, ispy=False):
    '''插入或设置词频信息'''
    # 这个和 insert 方法的有点重复了
    if not self.maybeCode(code):
      raise self.argsError('不符合当前码表编码的格式')

    t = Record(code, hz, hit, index, ispy)
    try:
      self.get(t).update(t)
      self.modified = True
    except self.RecordNotExist:
      # 不存在
      self.insert(code, hz, hit, index, ispy)

  def size(self):
    '''数据的条数'''
    return len(self.数据)

  __len__ = size

  def write(self, 文件, 保留词频信息=True):
    '''保存到文件'''
    # 测试用时 3.6x 秒
    f = open(文件, 'wb')

    # 写入属性测试用时 0.0006+ 秒
    # 版本号
    fmt = '<I'
    if self.版本:
      f.write(struct.pack(fmt, 0))
      fmt = '<B'
      f.write(struct.pack(fmt, self.版本))
    else:
      f.write(struct.pack(fmt, 1))

    # 键码字串
    fmt = '<I'
    x = self.键码.encode('utf-8')
    f.write(struct.pack(fmt, len(x)))
    fmt = '<' + str(len(x)) + 'sB'
    f.write(struct.pack(fmt, x, 0))

    # 码长
    fmt = '<B'
    f.write(struct.pack(fmt, self.码长))

    # 拼音长度
    if self.版本:
      fmt = '<B'
      f.write(struct.pack(fmt, self.拼音长度))

    # 规避字符
    fmt = '<I'
    x = self.规避字符.encode('utf-8')
    f.write(struct.pack(fmt, len(x)))
    fmt = '<' + str(len(x)) + 'sB'
    f.write(struct.pack(fmt, x, 0))

    # 组词规则
    if self.组词规则: # 有组词规则
      fmt = '<B'
      f.write(struct.pack(fmt, 7))
      for i in range(self.码长-1):
        if self.组词规则[i][0] == 'e':
          f.write(struct.pack(fmt, 0))
        else:
          f.write(struct.pack(fmt, 1))
        f.write(struct.pack(fmt, int(self.组词规则[i][1])))
        for j in range(self.码长):
          x = 3 + j * 4
          if self.组词规则[i][x] == 'n':
            f.write(struct.pack(fmt, 0))
          else:
            f.write(struct.pack(fmt, 1))
          f.write(struct.pack(fmt, int(self.组词规则[i][x+1])))
          f.write(struct.pack(fmt, int(self.组词规则[i][x+2])))
    else:
      f.write(struct.pack(fmt, 0))

    # 词的数量
    fmt = '<I'
    f.write(struct.pack(fmt, self.size()))

    if msg:
      print('写入数据中...')
      if timeit:
        timeitstart = datetime.today()
    # 写数据了
    if self.版本:
      size = self.拼音长度 + 1
    fmt2 = '<' + str(size) + 's'
    for i in self.数据:
      x = i.code.encode('utf-8').ljust(size, b'\x00')
      y = i.hz.encode('utf-8') + b'\x00'
      # 键码
      fmt = fmt2
      f.write(struct.pack(fmt, x))
      # 汉字
      fmt = '<I'
      f.write(struct.pack(fmt, len(y)))
      fmt = '<' + str(len(y)) + 's'
      f.write(struct.pack(fmt, y))
      # 拼音指示
      if self.版本:
        fmt = '<B'
        if i.ispy:
          f.write(struct.pack(fmt, 1))
        else:
          f.write(struct.pack(fmt, 0))
      # 词频信息
      fmt = '<II'
      f.write(struct.pack(fmt, i.hit, i.index))

    f.close()
    if msg:
      print('文件写入完成。')
      if timeit:
        print('用时', datetime.today() - timeitstart)
    self.modified = False

  class argsError(Exception):
    '''mb 的错误类：参数值不符合要求'''

    def __init__(self, value):
      self.value = value
    def __str__(self):
      return repr(self.value)

  class autoCodeError(Exception):
    '''mb 的错误类：自动生成编码失败'''

    def __init__(self, value):
      self.value = value
    def __str__(self):
      return repr(self.value)

  class RecordExists(Exception):
    '''mb 的错误类：插入时编码已经存在'''
    def __init__(self, value):
      self.value = value
    def __str__(self):
      return repr(self.value)+' 已经存在'

  class RecordNotExist(Exception):
    '''mb 的错误类：参数值不符合要求'''

    def __init__(self, value):
      self.value = value
    def __str__(self):
      return repr(self.value)+' 不存在'


########NEW FILE########
__FILENAME__ = musicsites
from collections import namedtuple

import requests

SongInfo = namedtuple(
    'SongInfo',
    'sid name href artists album extra')

class Base:
  _session = None
  userAgent = 'Mozilla/5.0 (X11; Linux x86_64; rv:25.0) ' \
          'Gecko/20100101 Firefox/25.0'

  def __init__(self, session=None):
    self._session = session

  @property
  def session(self):
    if not self._session:
      s = requests.Session()
      s.headers['User-Agent'] = self.userAgent
      self._session = s
    return self._session


########NEW FILE########
__FILENAME__ = mydns
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-27
@author: shell.xu
@modified: lilydjwg
'''
import sys, struct, random, logging, io
import socket

logger = logging.getLogger('dns')

class Meta(type):
  def __new__(cls, name, bases, attrs):
    r = {v: n for n, v in attrs.items() if n.isupper()}
    attrs['__reversed__'] = r
    return type.__new__(cls, name, bases, attrs)

class DEFINE(metaclass=Meta):
  @classmethod
  def lookup(cls, id, default='NOT FOUND'):
    return cls.__reversed__.get(id, default)

class OPCODE(DEFINE):
  QUERY = 0
  IQUERY = 1
  STATUS = 2
  NOTIFY = 4
  UPDATE = 5

# with NULL, cython can't compile this file
class TYPE(DEFINE):
  A = 1     # a host address
  NS = 2      # an authoritative name server
  MD = 3      # a mail destination (Obsolete - use MX)
  MF = 4      # a mail forwarder (Obsolete - use MX)
  CNAME = 5   # the canonical name for an alias
  SOA = 6     # marks the start of a zone of authority
  MB = 7      # a mailbox domain name (EXPERIMENTAL)
  MG = 8      # a mail group member (EXPERIMENTAL)
  MR = 9      # a mail rename domain name (EXPERIMENTAL)
  # NULL = 10     # a null RR (EXPERIMENTAL)
  WKS = 11    # a well known service description
  PTR = 12    # a domain name pointer
  HINFO = 13    # host information
  MINFO = 14    # mailbox or mail list information
  MX = 15     # mail exchange
  TXT = 16    # text strings
  AAAA = 28   # IPv6 AAAA records (RFC 1886)
  SRV = 33    # DNS RR for specifying the location of services (RFC 2782)
  SPF = 99    # TXT RR for Sender Policy Framework
  UNAME = 110
  MP = 240

class QTYPE(DEFINE):
  AXFR = 252    # A request for a transfer of an entire zone
  MAILB = 253   # A request for mailbox-related records (MB, MG or MR)
  MAILA = 254   # A request for mail agent RRs (Obsolete - see MX)
  ANY = 255   # A request for all records

class CLASS(DEFINE):
  IN = 1      # the Internet
  CS = 2      # the CSNET class (Obsolete - used only for examples in
          # some obsolete RFCs)
  CH = 3      # the CHAOS class. When someone shows me python running on
          # a Symbolics Lisp machine, I'll look at implementing this.
  HS = 4      # Hesiod [Dyer 87]
  ANY = 255   # any class

def packbit(r, bit, dt): return r << bit | (dt & (2**bit - 1))
def unpack(r, bit): return r & (2**bit - 1), r >> bit

def packflag(qr, opcode, auth, truncated, rd, ra, rcode):
  r = packbit(packbit(0, 1, qr), 4, opcode)
  r = packbit(packbit(r, 1, auth), 1, truncated)
  r = packbit(packbit(r, 1, rd), 1, ra)
  r = packbit(packbit(r, 3, 0), 4, rcode)
  return r

def unpackflag(r):
  r, qr = unpack(r, 1)
  r, opcode = unpack(r, 4)
  r, auth = unpack(r, 1)
  r, truncated = unpack(r, 1)
  r, rd = unpack(r, 1)
  r, ra = unpack(r, 1)
  r, rv = unpack(r, 3)
  r, rcode = unpack(r, 4)
  assert rv == 0
  return qr, opcode, auth, truncated, rd, ra, rcode

class Record(object):

  def __init__(self, id, qr, opcode, auth, truncated, rd, ra, rcode):
    self.id, self.qr, self.opcode, self.authans = id, qr, opcode, auth
    self.truncated, self.rd, self.ra, self.rcode = truncated, rd, ra, rcode
    self.quiz, self.ans, self.auth, self.ex = [], [], [], []

  def show(self):
    yield 'quiz'
    for q in self.quiz: yield self.showquiz(q)
    yield 'answer'
    for r in self.ans: yield self.showRR(r)
    yield 'auth'
    for r in self.auth: yield self.showRR(r)
    yield 'ex'
    for r in self.ex: yield self.showRR(r)

  def filteredRR(self, RRs, types): return (i for i in RRs if i[0] in types)

  def packname(self, name):
    return b''.join(bytes((len(i),))+i for i in name.encode('ascii').split(b'.')) + b'\x00'

  def unpackname(self, s):
    return self._unpackname(s).decode('ascii')

  def _unpackname(self, s):
    r = []
    c = ord(s.read(1))
    while c != 0:
      if c & 0xC0 == 0xC0:
        c = (c << 8) + ord(s.read(1)) & 0x3FFF
        r.append(self._unpackname(io.BytesIO(self.buf[c:])))
        break
      else: r.append(s.read(c))
      c = ord(s.read(1))
    return b'.'.join(r)

  def packquiz(self, name, qtype, cls):
    return self.packname(name) + struct.pack('>HH', qtype, cls)

  def unpackquiz(self, s):
    name, r = self.unpackname(s), struct.unpack('>HH', s.read(4))
    return name, r[0], r[1]

  def read_string(self, s, length):
    consumed = 0
    r = []
    while consumed < length:
      new_len = s.read(1)[0]
      r.append(s.read(new_len))
      consumed += new_len + 1
    return b''.join(r)

  def showquiz(self, q):
    return '\t%s\t%s\t%s' % (q[0], TYPE.lookup(q[1]), CLASS.lookup(q[2]))

  # def packRR(self, name, type, cls, ttl, res):
  #   return self.packname(name) + \
  #     struct.pack('>HHIH', type, cls, ttl, len(res)) + res

  def unpackRR(self, s):
    n = self.unpackname(s)
    r = struct.unpack('>HHIH', s.read(10))
    if r[0] == TYPE.A:
      return n, r[0], r[1], r[2], socket.inet_ntoa(s.read(r[3]))
    elif r[0] == TYPE.CNAME:
      return n, r[0], r[1], r[2], self.unpackname(s)
    elif r[0] == TYPE.MX:
      return n, r[0], r[1], r[2], \
        struct.unpack('>H', s.read(2))[0], self.unpackname(s)
    elif r[0] == TYPE.PTR:
      return n, r[0], r[1], r[2], self.unpackname(s)
    elif r[0] == TYPE.SOA:
      rr = [n, r[0], r[1], r[2], self.unpackname(s), self.unpackname(s)]
      rr.extend(struct.unpack('>IIIII', s.read(20)))
      return tuple(rr)
    elif r[0] == TYPE.TXT:
      return n, r[0], r[1], r[2], self.read_string(s, r[3])
    else: raise Exception("don't know howto handle type, %s." % str(r))

  def showRR(self, r):
    if r[1] in (TYPE.A, TYPE.CNAME, TYPE.PTR, TYPE.SOA):
      return '\t%s\t%d\t%s\t%s\t%s' % (
        r[0], r[3], CLASS.lookup(r[2]), TYPE.lookup(r[1]), r[4])
    elif r[1] == TYPE.MX:
      return '\t%s\t%d\t%s\t%s\t%s' % (
        r[0], r[3], CLASS.lookup(r[2]), TYPE.lookup(r[1]), r[5])
    else: raise Exception("don't know howto handle type, %s." % str(r))

  def pack(self):
    self.buf = struct.pack(
      '>HHHHHH', self.id, packflag(self.qr, self.opcode, self.authans,
                     self.truncated, self.rd, self.ra, self.rcode),
      len(self.quiz), len(self.ans), len(self.auth), len(self.ex))
    for i in self.quiz: self.buf += self.packquiz(*i)
    for i in self.ans: self.buf += self.packRR(*i)
    for i in self.auth: self.buf += self.packRR(*i)
    for i in self.ex: self.buf += self.packRR(*i)
    return self.buf

  @classmethod
  def unpack(cls, dt):
    s = io.BytesIO(dt)
    id, flag, lquiz, lans, lauth, lex = struct.unpack('>HHHHHH', s.read(12))
    rec = cls(id, *unpackflag(flag))
    rec.buf = dt
    rec.quiz = [rec.unpackquiz(s) for i in range(lquiz)]
    rec.ans = [rec.unpackRR(s) for i in range(lans)]
    rec.auth = [rec.unpackRR(s) for i in range(lauth)]
    rec.ex = [rec.unpackRR(s) for i in range(lex)]
    return rec

def mkquery(*ntlist):
  rec = Record(random.randint(0, 65536), 0, OPCODE.QUERY, 0, 0, 1, 0, 0)
  for name, type in ntlist: rec.quiz.append((name, type, CLASS.IN))
  return rec

def query_by_udp(q, server, port=53, sock=None):
  if sock is None: sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.sendto(q, (server, port))
  return sock.recvfrom(1024)[0]

def query_by_tcp(q, server, port=53, stream=None):
  sock = None
  if stream is None:
    sock = socket.socket()
    sock.connect((server, port))
    stream = sock.makefile()
  try:
    stream.write(struct.pack('>H', len(q)) + q)
    stream.flush()
    d = stream.read(2)
    if len(d) == 0: raise EOFError()
    reply = stream.read(struct.unpack('>H', d)[0])
    if len(reply) == 0: raise EOFError()
    return reply
  finally:
    if sock is not None: sock.close()

def query(name, type=TYPE.A, server='127.0.0.1', port=53, protocol='udp'):
  q = mkquery((name, type)).pack()
  func = globals().get('query_by_%s' % protocol)
  if not func:
    raise LookupError('protocol %r not supported' % protocol)
  return Record.unpack(func(q, server,  port))

def nslookup(name):
  r = query(name)
  return [rdata for name, type, cls, ttl, rdata in r.ans if type == TYPE.A]

########NEW FILE########
__FILENAME__ = dns
# vim:fileencoding=utf-8

import socket
from functools import partial

import tornado.ioloop

from mydns import TYPE, Record, mkquery

def query_via_udp(name, callback, type=TYPE.A, server='127.0.0.1', port=53, *, sock=None, ioloop=None):
  q = mkquery((name, type)).pack()
  if sock is None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.sendto(q, (server, port))

  if ioloop is None:
    ioloop = tornado.ioloop.IOLoop.instance()
  ioloop.add_handler(sock.fileno(),
                     partial(_recv_dns_msg, callback, ioloop, sock),
                     ioloop.READ)

def _recv_dns_msg(callback, ioloop, sock, fd, events):
  ret = Record.unpack(sock.recvfrom(1024)[0])
  ioloop.remove_handler(fd)
  callback(ret)

def test():
  import sys
  n = len(sys.argv) - 1
  ioloop = tornado.ioloop.IOLoop.instance()

  def callback(ret):
    nonlocal n
    print(ret.ans)
    n -= 1
    if n == 0:
      ioloop.stop()

  for i in sys.argv[1:]:
    query_via_udp(i, callback)
  ioloop.start()

if __name__ == '__main__':
  test()

########NEW FILE########
__FILENAME__ = fetchtitle
import re
import socket
from urllib.parse import urlsplit, urljoin
from functools import partial
from collections import namedtuple
import struct
import json
import logging
import encodings.idna
from html.parser import HTMLParser
from html.entities import entitydefs

import tornado.ioloop
import tornado.iostream

# try to import C parser then fallback in pure python parser.
try:
  from http_parser.parser import HttpParser
except ImportError:
  from http_parser.pyparser import HttpParser

UserAgent = 'FetchTitle/1.3 (https://github.com/lilydjwg/winterpy/blob/master/pylib/mytornado/fetchtitle.py)'

def get_charset_from_ctype(ctype):
  pos = ctype.find('charset=')
  if pos > 0:
    charset = ctype[pos+8:]
    if charset.lower() == 'gb2312':
      # Windows misleadingly uses gb2312 when it's gbk or gb18030
      charset = 'gb18030'
    elif charset.lower() == 'windows-31j':
      # cp932's IANA name (Windows-31J), extended shift_jis
      # https://en.wikipedia.org/wiki/Code_page_932
      charset = 'cp932'
    return charset

class HtmlTitleParser(HTMLParser):
  charset = title = None
  default_charset = 'utf-8'
  result = None
  _title_coming = False

  def __init__(self):
    # use a list to store literal bytes and escaped Unicode
    self.title = []
    super().__init__()

  def feed(self, bytesdata):
    if bytesdata:
      super().feed(bytesdata.decode('latin1'))
    else:
      self.close()

  def close(self):
    self._check_result(force=True)
    super().close()

  def handle_starttag(self, tag, attrs):
    # Google Search uses wrong meta info
    if tag == 'meta' and not self.charset:
      attrs = dict(attrs)
      if attrs.get('http-equiv', '').lower() == 'content-type':
        self.charset = get_charset_from_ctype(attrs.get('content', ''))
      elif attrs.get('charset', False):
        self.charset = attrs['charset']
    elif tag in ('body', 'p', 'div'):
      # won't be found
      self.charset = False
    elif tag == 'title':
      self._title_coming = True

    self._check_result()

  def handle_data(self, data, *, unicode=False):
    if not unicode:
      data = data.encode('latin1') # encode back
    if self._title_coming:
      self.title.append(data)

  def handle_endtag(self, tag):
    self._title_coming = False
    self._check_result()

  def handle_charref(self, name):
    if name[0] == 'x':
      x = int(name[1:], 16)
    else:
      x = int(name)
    ch = chr(x)
    self.handle_data(ch, unicode=True)

  def handle_entityref(self, name):
    try:
      ch = entitydefs[name]
    except KeyError:
      ch = '&' + name
    self.handle_data(ch, unicode=True)

  def _check_result(self, *, force=False):
    if self.result is not None:
      return

    if (force or self.charset is not None) \
       and self.title:
      self.result = ''.join(
        x if isinstance(x, str) else x.decode(
          self.charset or self.default_charset,
          errors = 'surrogateescape',
        ) for x in self.title
      )

class SingletonFactory:
  def __init__(self, name):
    self.name = name
  def __repr__(self):
    return '<%s>' % self.name

MediaType = namedtuple('MediaType', 'type size dimension')
defaultMediaType = MediaType('application/octet-stream', None, None)

ConnectionClosed = SingletonFactory('ConnectionClosed')
TooManyRedirection = SingletonFactory('TooManyRedirection')
Timeout = SingletonFactory('Timeout')

logger = logging.getLogger(__name__)

class ContentFinder:
  buf = b''
  def __init__(self, mediatype):
    self._mt = mediatype

  @classmethod
  def match_type(cls, mediatype):
    ctype = mediatype.type.split(';', 1)[0]
    if hasattr(cls, '_mime') and cls._mime == ctype:
      return cls(mediatype)
    if hasattr(cls, '_match_type') and cls._match_type(ctype):
      return cls(mediatype)
    return False

class TitleFinder(ContentFinder):
  parser = None
  pos = 0
  maxpos = 102400 # look at most around 100K

  @staticmethod
  def _match_type(ctype):
    return ctype.find('html') != -1

  def __init__(self, mediatype):
    charset = get_charset_from_ctype(mediatype.type)
    self.parser = HtmlTitleParser()
    self.parser.charset = charset

  def __call__(self, data):
    if data:
      self.pos += len(data)
    if self.pos > self.maxpos:
      # stop here
      data = b''
    self.parser.feed(data)
    if self.parser.result:
      return self.parser.result

class PNGFinder(ContentFinder):
  _mime = 'image/png'
  def __call__(self, data):
    if data is None:
      return self._mt

    self.buf += data
    if len(self.buf) < 24:
      # can't decide yet
      return
    if self.buf[:16] != b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR':
      logging.warn('Bad PNG signature and header: %r', self.buf[:16])
      return self._mt._replace(dimension='Bad PNG')
    else:
      s = struct.unpack('!II', self.buf[16:24])
      return self._mt._replace(dimension=s)

class JPEGFinder(ContentFinder):
  _mime = 'image/jpeg'
  isfirst = True
  def __call__(self, data):
    if data is None:
      return self._mt

    # http://www.64lines.com/jpeg-width-height
    if data:
      self.buf += data

    if self.isfirst is True:
      # finding header
      if len(self.buf) < 5:
        return
      if self.buf[:3] != b'\xff\xd8\xff':
        logging.warn('Bad JPEG signature: %r', self.buf[:3])
        return self._mt._replace(dimension='Bad JPEG')
      else:
        self.blocklen = self.buf[4] * 256 + self.buf[5] + 2
        self.buf = self.buf[2:]
        self.isfirst = False

    if self.isfirst is False:
      # receiving a block. 4 is for next block size
      if len(self.buf) < self.blocklen + 4:
        return
      buf = self.buf
      if buf[0] != 0xff:
        logging.warn('Bad JPEG: %r', self.buf[:self.blocklen])
        return self._mt._replace(dimension='Bad JPEG')
      if buf[1] == 0xc0 or buf[1] == 0xc2:
        s = buf[7] * 256 + buf[8], buf[5] * 256 + buf[6]
        return self._mt._replace(dimension=s)
      else:
        # not Start Of Frame, retry with next block
        self.buf = buf = buf[self.blocklen:]
        self.blocklen = buf[2] * 256 + buf[3] + 2
        return self(b'')

class GIFFinder(ContentFinder):
  _mime = 'image/gif'
  def __call__(self, data):
    if data is None:
      return self._mt

    self.buf += data
    if len(self.buf) < 10:
      # can't decide yet
      return
    if self.buf[:3] != b'GIF':
      logging.warn('Bad GIF signature: %r', self.buf[:3])
      return self._mt._replace(dimension='Bad GIF')
    else:
      s = struct.unpack('<HH', self.buf[6:10])
      return self._mt._replace(dimension=s)

class TitleFetcher:
  status_code = 0
  followed_times = 0 # 301, 302
  finder = None
  addr = None
  stream = None
  max_follows = 10
  timeout = 15
  _finished = False
  _cookie = None
  _connected = False
  _redirected_stream = None
  _content_finders = (TitleFinder, PNGFinder, JPEGFinder, GIFFinder)
  _url_finders = ()

  def __init__(self, url, callback,
               timeout=None, max_follows=None, io_loop=None,
               content_finders=None, url_finders=None, referrer=None,
               run_at_init=True,
              ):
    '''
    url: the (full) url to fetch
    callback: called with title or MediaType or an instance of SingletonFactory
    timeout: total time including redirection before giving up
    max_follows: max redirections

    may raise:
    <UnicodeError: label empty or too long> in host preparation
    '''
    self._callback = callback
    self.referrer = referrer
    if max_follows is not None:
      self.max_follows = max_follows

    if timeout is not None:
      self.timeout = timeout
    if hasattr(tornado.ioloop, 'current'):
        default_io_loop = tornado.ioloop.IOLoop.current
    else:
        default_io_loop = tornado.ioloop.IOLoop.instance
    self.io_loop = io_loop or default_io_loop()

    if content_finders is not None:
      self._content_finders = content_finders
    if url_finders is not None:
      self._url_finders = url_finders

    self.origurl = url
    self.url_visited = []
    if run_at_init:
      self.run()

  def run(self):
    if self.url_visited:
      raise Exception("can't run again")
    else:
      self.start_time = self.io_loop.time()
      self._timeout = self.io_loop.add_timeout(
        self.timeout + self.start_time,
        self.on_timeout,
      )
      try:
        self.new_url(self.origurl)
      except:
        self.io_loop.remove_timeout(self._timeout)
        raise

  def on_timeout(self):
    logger.debug('%s: request timed out', self.origurl)
    self.run_callback(Timeout)

  def parse_url(self, url):
    '''parse `url`, set self.host and return address and stream class'''
    self.url = u = urlsplit(url)
    self.host = u.netloc

    if u.scheme == 'http':
      addr = u.hostname, u.port or 80
      stream = tornado.iostream.IOStream
    elif u.scheme == 'https':
      addr = u.hostname, u.port or 443
      stream = tornado.iostream.SSLIOStream
    else:
      raise ValueError('bad url: %r' % url)

    return addr, stream

  def new_connection(self, addr, StreamClass):
    '''set self.addr, self.stream and connect to host'''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.addr = addr
    self.stream = StreamClass(s)
    logger.debug('%s: connecting to %s...', self.origurl, addr)
    self.stream.set_close_callback(self.before_connected)
    self.stream.connect(addr, self.send_request)

  def new_url(self, url):
    self.url_visited.append(url)
    self.fullurl = url

    for finder in self._url_finders:
      f = finder.match_url(url, self)
      if f:
        self.finder = f
        f()
        return

    addr, StreamClass = self.parse_url(url)
    if addr != self.addr:
      if self.stream:
        self.stream.close()
      self.new_connection(addr, StreamClass)
    else:
      logger.debug('%s: try to reuse existing connection to %s', self.origurl, self.addr)
      try:
        self.send_request(nocallback=True)
      except tornado.iostream.StreamClosedError:
        logger.debug('%s: server at %s doesn\'t like keep-alive, will reconnect.', self.origurl, self.addr)
        # The close callback should have already run
        self.stream.close()
        self.new_connection(addr, StreamClass)

  def run_callback(self, arg):
    self.io_loop.remove_timeout(self._timeout)
    self._finished = True
    if self.stream:
      self.stream.close()
    self._callback(arg, self)

  def send_request(self, nocallback=False):
    self._connected = True
    req = ['GET %s HTTP/1.1',
           'Host: %s',
           # t.co will return 200 and use js/meta to redirect using the following :-(
           # 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0',
           'User-Agent: %s' % UserAgent,
           'Accept: text/html,application/xhtml+xml;q=0.9,*/*;q=0.7',
           'Accept-Language: zh-cn,zh;q=0.7,en;q=0.3',
           'Accept-Charset: utf-8,gb18030;q=0.7,*;q=0.7',
           'Accept-Encoding: gzip, deflate',
           'Connection: keep-alive',
          ]
    if self.referrer is not None:
      req.append('Referer: ' + self.referrer.replace('%', '%%'))
    path = self.url.path or '/'
    if self.url.query:
      path += '?' + self.url.query
    req = '\r\n'.join(req) % (
      path, self._prepare_host(self.host),
    )
    if self._cookie:
      req += '\r\n' + self._cookie
    req += '\r\n\r\n'
    self.stream.write(req.encode())
    self.headers_done = False
    self.parser = HttpParser(decompress=True)
    if not nocallback:
      self.stream.read_until_close(
        # self.addr and self.stream may have been changed when close callback is run
        partial(self.on_data, close=True, addr=self.addr, stream=self.stream),
        streaming_callback=self.on_data,
      )

  def _prepare_host(self, host):
    host = encodings.idna.nameprep(host)
    return b'.'.join(encodings.idna.ToASCII(x) for x in host.split('.')).decode('ascii')

  def on_data(self, data, close=False, addr=None, stream=None):
    if close:
      logger.debug('%s: connection to %s closed.', self.origurl, addr)

    if self.stream.error:
      self.run_callback(self.stream.error)
      return

    if (close and stream and self._redirected_stream is stream) or self._finished:
      # The connection is closing, and we are being redirected or we're done.
      self._redirected_stream = None
      return

    recved = len(data)
    logger.debug('%s: received data: %d bytes', self.origurl, recved)

    p = self.parser
    nparsed = p.execute(data, recved)
    if close:
      # feed EOF
      p.execute(b'', 0)

    if not self.headers_done and p.is_headers_complete():
      if not self.on_headers_done():
        return

    if p.is_partial_body():
      chunk = p.recv_body()
      if self.finder is None:
        # redirected but has body received
        return
      t = self.feed_finder(chunk)
      if t is not None:
        self.run_callback(t)
        return

    if p.is_message_complete():
      if self.finder is None:
        # redirected but has body received
        return
      t = self.feed_finder(None)
      # if title not found, t is None
      self.run_callback(t)
    elif close:
      self.run_callback(self.stream.error or ConnectionClosed)

  def before_connected(self):
    '''check if something wrong before connected'''
    if not self._connected and not self._finished:
      self.run_callback(self.stream.error)

  def process_cookie(self):
    setcookie = self.headers.get('Set-Cookie', None)
    if not setcookie:
      return

    cookies = [c.rsplit(None, 1)[-1] for c in setcookie.split('; expires')[:-1]]
    self._cookie = 'Cookie: ' + '; '.join(cookies)

  def on_headers_done(self):
    '''returns True if should proceed, None if should stop for current chunk'''
    self.headers_done = True
    self.headers = self.parser.get_headers()

    self.status_code = self.parser.get_status_code()
    if self.status_code in (301, 302):
      self.process_cookie() # or we may be redirecting to a loop
      logger.debug('%s: redirect to %s', self.origurl, self.headers['Location'])
      self.followed_times += 1
      if self.followed_times > self.max_follows:
        self.run_callback(TooManyRedirection)
      else:
        newurl = urljoin(self.fullurl, self.headers['Location'])
        self._redirected_stream = self.stream
        self.new_url(newurl)
      return

    try:
      l = int(self.headers.get('Content-Length', None))
    except (ValueError, TypeError):
      l = None

    ctype = self.headers.get('Content-Type', 'text/html')
    mt = defaultMediaType._replace(type=ctype, size=l)
    for finder in self._content_finders:
      f = finder.match_type(mt)
      if f:
        self.finder = f
        break
    else:
      self.run_callback(mt)
      return

    return True

  def feed_finder(self, chunk):
    '''feed data to finder, return the title if found'''
    t = self.finder(chunk)
    if t is not None:
      return t

class URLFinder:
  def __init__(self, url, fetcher, match=None):
    self.fullurl = url
    self.match = match
    self.fetcher = fetcher

  @classmethod
  def match_url(cls, url, fetcher):
    if hasattr(cls, '_url_pat'):
      m = cls._url_pat.match(url)
      if m is not None:
        return cls(url, fetcher, m)
    if hasattr(cls, '_match_url') and cls._match_url(url, fetcher):
      return cls(url, fetcher)

  def done(self, info):
    self.fetcher.run_callback(info)

class GithubFinder(URLFinder):
  _url_pat = re.compile(r'https://github\.com/(?!blog/)(?P<repo_path>[^/]+/[^/]+)/?$')
  _api_pat = 'https://api.github.com/repos/{repo_path}'
  httpclient = None

  def __call__(self):
    if self.httpclient is None:
      from tornado.httpclient import AsyncHTTPClient
      httpclient = AsyncHTTPClient()
    else:
      httpclient = self.httpclient

    m = self.match
    httpclient.fetch(self._api_pat.format(**m.groupdict()), self.parse_info,
                     headers={
                       'User-Agent': UserAgent,
                     })

  def parse_info(self, res):
    repoinfo = json.loads(res.body.decode('utf-8'))
    self.response = res
    self.done(repoinfo)

class GithubUserFinder(GithubFinder):
  _url_pat = re.compile(r'https://github\.com/(?!blog(?:$|/))(?P<user>[^/]+)/?$')
  _api_pat = 'https://api.github.com/users/{user}'

def main(urls):
  class BatchFetcher:
    n = 0
    def __call__(self, title, fetcher):
      if isinstance(title, bytes):
        try:
          title = title.decode('gb18030')
        except UnicodeDecodeError:
          pass
      url = ' <- '.join(reversed(fetcher.url_visited))
      logger.info('done: [%d] %s <- %s' % (fetcher.status_code, title, url))
      self.n -= 1
      if not self.n:
        tornado.ioloop.IOLoop.instance().stop()

    def add(self, url):
      TitleFetcher(url, self, url_finders=(GithubFinder,))
      self.n += 1

  from myutils import enable_pretty_logging
  enable_pretty_logging()
  f = BatchFetcher()
  for u in urls:
    f.add(u)
  tornado.ioloop.IOLoop.instance().start()

def test():
  urls = (
    'http://lilydjwg.is-programmer.com/',
    'http://www.baidu.com',
    'https://zh.wikipedia.org', # redirection
    'http://redis.io/',
    'http://lilydjwg.is-programmer.com/2012/10/27/streaming-gzip-decompression-in-python.36130.html', # maybe timeout
    'http://img.vim-cn.com/22/cd42b4c776c588b6e69051a22e42dabf28f436', # image with length
    'https://github.com/m13253/titlebot/blob/master/titlebot.py_', # 404
    'http://lilydjwg.is-programmer.com/admin', # redirection
    'http://twitter.com', # connect timeout
    'http://www.wordpress.com', # reset
    'http://jquery-api-zh-cn.googlecode.com/svn/trunk/xml/jqueryapi.xml', # xml
    'http://lilydjwg.is-programmer.com/user_files/lilydjwg/config/avatar.png', # PNG
    'http://img01.taobaocdn.com/bao/uploaded/i1/110928240/T2okG7XaRbXXXXXXXX_!!110928240.jpg', # JPEG with Start Of Frame as the second block
    'http://file3.u148.net/2013/1/images/1357536246993.jpg', # JPEG that failed previous code
    'http://gouwu.hao123.com/', # HTML5 GBK encoding
    'https://github.com/lilydjwg/winterpy', # github url finder
    'http://github.com/lilydjwg/winterpy', # github url finder with redirect
    'http://导航.中国/', # Punycode. This should not be redirected
    'http://t.cn/zTOgr1n', # multiple redirections
    'http://www.galago-project.org/specs/notification/0.9/x408.html', # </TITLE\n>
    'http://x.co/dreamz', # redirection caused false ConnectionClosed error
    # http_parser won't decode this big gzip?
    'http://m8y.org/tmp/zipbomb/zipbomb_light_nonzero.html', # very long title
    'http://www.83wyt.com', # reversed meta attribute order
    'https://www.inoreader.com', # malformed start tag: <meta http-equiv="Content-Type" content="text/html" ; charset="UTF-8">
    'https://linuxtoy.org/archives/linux-deepin-2014-alpha-into-new-deepin-world.html', # charref outside ASCII
    'http://74.125.235.191/search?site=&source=hp&q=%E6%9C%8D%E5%8A%A1%E5%99%A8+SSD&btnG=Google+%E6%90%9C%E7%B4%A2', # right charset in HTTP, wrong in HTML
    'http://digital.sina.com.hk/news/-7-1514837/1.html', # mixed Big5 and non-Big5 escaped Unicode character
  )
  main(urls)

if __name__ == "__main__":
  import sys
  try:
    if len(sys.argv) == 1:
      sys.exit('no urls given.')
    elif sys.argv[1] == 'test':
      test()
    else:
      main(sys.argv[1:])
  except KeyboardInterrupt:
    print('Interrupted.')

########NEW FILE########
__FILENAME__ = httpserver
from __future__ import print_function

import os
import sys
import re
import datetime
import stat
import mimetypes
import threading
import email.utils
import time
import socket
try:
  import http.client as httpclient
except ImportError:
  import httplib as httpclient
import traceback
import tempfile
from functools import partial

from tornado.web import HTTPError, RequestHandler, asynchronous, GZipContentEncoding
import tornado.escape
import tornado.httpserver
from tornado.log import app_log, gen_log

from .util import FileEntry

_legal_range = re.compile(r'bytes=(\d*)-(\d*)$')

class ErrorHandlerMixin:
  '''nicer error page'''
  error_page = '''\
<!DOCTYPE html>
<meta charset="utf-8" />
<title>%(code)s %(message)s</title>
<style type="text/css">
  body { font-family: serif; }
</style>
<h1>%(code)s %(message)s</h1>
<p>%(err)s</p>
<hr/>
'''

  def write_error(self, status_code, **kwargs):
    if self.settings.get("debug") and "exc_info" in kwargs:
      # in debug mode, try to send a traceback
      self.set_header('Content-Type', 'text/plain')
      for line in traceback.format_exception(*kwargs["exc_info"]):
        self.write(line)
      self.finish()
    else:
      err_exc = kwargs.get('exc_info', '  ')[1]
      if err_exc in (None, ' '):
        err_msg = ''
      else:
        if isinstance(err_exc, HTTPError):
          err_msg = str(err_exc.log_message) + '.'
        else:
          err_msg = str(err_exc) + '.'

      self.finish(self.error_page % {
        "code": status_code,
        "message": httpclient.responses[status_code],
        "err": err_msg,
      })

  @classmethod
  def patchHandler(cls, RequestHandler):
    '''patch a RequestHandler without subclassing

    In this way we can change all ``tornado.web.RequestHandler``. Simply
subclassing and replacing won't work due to the Python 2-style ``super()``
call in its ``__init__`` method.
    '''
    RequestHandler.write_error = cls.write_error
    RequestHandler.error_page = cls.error_page

class StaticFileHandler(RequestHandler):
  """A simple handler that can serve static content from a directory.

  Why prefer this than the one in Tornado 3.1?

  1. Etag is not md5sum, so it's quick on large files;
  2. Read file chunk by chunk, so it won't eat all your memory on huge files.

  To map a path to this handler for a static data directory ``/var/www``,
  you would add a line to your application like::

    application = web.Application([
      (r"/static/(.*)", web.StaticFileHandler, {
        "path": "/var/www",
        "default_filenames": ["index.html"], #optional
        "dirindex": "dirlisting", #optional template name for directory listing
      }),
    ])

  The local root directory of the content should be passed as the ``path``
  argument to the handler.

  The `dirindex` template will receive the following parameters:
    - `url`: the requested path
    - `files`, a list of ``FileEntry``; override ``FileEntry`` attribute to
      customize (it must be comparable)
    - `decodeURIComponent`, a decoding function

  To support aggressive browser caching, if the argument ``v`` is given
  with the path, we set an infinite HTTP expiration header. So, if you
  want browsers to cache a file indefinitely, send them to, e.g.,
  ``/static/images/myimage.png?v=xxx``. Override `get_cache_time` method for
  more fine-grained cache control.
  """
  CACHE_MAX_AGE = 86400 * 365 * 10  # 10 years
  BLOCK_SIZE = 40960 # 4096 is too slow; this value works great here
  FileEntry = FileEntry

  _static_hashes = {}
  _lock = threading.Lock()  # protects _static_hashes

  def initialize(self, path=None, default_filenames=None, dirindex=None):
    if path is not None:
      self.root = os.path.abspath(path) + os.path.sep
    else:
      self.root = None
    self.default_filenames = default_filenames
    self.dirindex = dirindex

  @classmethod
  def reset(cls):
    with cls._lock:
      cls._static_hashes = {}

  def head(self, path):
    self.get(path, include_body=False)

  def get(self, path, include_body=True):
    if os.path.sep != "/":
      path = path.replace("/", os.path.sep)
    abspath = os.path.abspath(os.path.join(self.root, path))
    # os.path.abspath strips a trailing /
    # it needs to be temporarily added back for requests to root/
    if not (abspath + os.path.sep).startswith(self.root):
      raise HTTPError(403, "%s is not in root static directory", path)
    self.send_file(abspath, include_body)

  def send_file(self, abspath, include_body=True, path=None, download=False):
    '''
    send a static file to client

    ``abspath``: the absolute path of the file on disk
    ``path``: the path to use as if requested, if given
    ``download``: whether we should try to persuade the client to download the
                  file. This can be either ``True`` or the intended filename

    If you use ``send_file`` directly and want to use another file as default
    index, you should set this parameter.
    '''
    # we've found the file
    found = False
    # use @asynchronous on a seperate method so that HTTPError won't get
    # messed up
    if path is None:
      path = self.request.path
    if os.path.isdir(abspath):
      # need to look at the request.path here for when path is empty
      # but there is some prefix to the path that was already
      # trimmed by the routing
      if not path.endswith("/"):
        redir = path + '/'
        if self.request.query:
          redir += '?' + self.request.query
        self.redirect(redir, permanent=True)
        return

      # check if we have a default available
      if self.default_filenames is not None:
        for i in self.default_filenames:
          abspath_ = os.path.join(abspath, i)
          if os.path.exists(abspath_):
            abspath = abspath_
            found = True
            break

      if not found:
        # try dir listing
        if self.dirindex is not None:
          if not include_body:
            raise HTTPError(405)
          self.renderIndex(abspath)
          return
        else:
          raise HTTPError(403, "Directory Listing Not Allowed")

    if not os.path.exists(abspath):
      # failed to figure out the file to send
      raise HTTPError(404)
    if not os.path.isfile(abspath):
      raise HTTPError(403, "%s is not a file", self.request.path)

    if download is not False:
      if download is True:
        filename = os.path.split(path)[1]
      else:
        filename = download
      # See http://kb.mozillazine.org/Filenames_with_spaces_are_truncated_upon_download
      self.set_header('Content-Disposition', 'attachment; filename="%s"' % filename.replace('"', r'\"'))

    self._send_file_async(path, abspath, include_body)

  @asynchronous
  def _send_file_async(self, path, abspath, include_body=True):
    stat_result = os.stat(abspath)
    modified = datetime.datetime.fromtimestamp(stat_result[stat.ST_MTIME])
    self.set_header("Last-Modified", modified)
    set_length = True

    mime_type, encoding = mimetypes.guess_type(abspath)
    if not mime_type:
      # default is plain text
      mime_type = 'text/plain'
    self.set_header("Content-Type", mime_type)

    # make use of gzip when possible
    if self.settings.get("gzip") and \
        mime_type in GZipContentEncoding.CONTENT_TYPES:
      set_length = False

    file_length = stat_result[stat.ST_SIZE]
    if set_length:
      self.set_header("Content-Length", file_length)
      self.set_header('Accept-Ranges', 'bytes')

    cache_time = self.get_cache_time(path, modified, mime_type)

    if cache_time > 0:
      self.set_header("Expires", datetime.datetime.utcnow() +
                      datetime.timedelta(seconds=cache_time))
      self.set_header("Cache-Control", "max-age=" + str(cache_time))

    self.set_extra_headers(path)

    # Check the If-Modified-Since, and don't send the result if the
    # content has not been modified
    ims_value = self.request.headers.get("If-Modified-Since")
    if ims_value is not None:
      date_tuple = email.utils.parsedate(ims_value)
      if_since = datetime.datetime.fromtimestamp(time.mktime(date_tuple))
      if if_since >= modified:
        self.set_status(304)
        self.finish()
        return

    # Check for range requests
    ranges = None
    if set_length:
      ranges = self.request.headers.get("Range")
      if ranges:
        range_match = _legal_range.match(ranges)
        if range_match:
          start = range_match.group(1)
          start = start and int(start) or 0
          stop = range_match.group(2)
          stop = stop and int(stop) or file_length-1
          if start >= file_length:
            raise HTTPError(416)
          self.set_status(206)
          self.set_header('Content-Range', '%d-%d/%d' % (
            start, stop, file_length))

    if not include_body:
      self.finish()
      return

    file = open(abspath, "rb")
    if ranges:
      if start:
        file.seek(start, os.SEEK_SET)
      self._write_chunk(file, length=stop-start+1)
    else:
      self._write_chunk(file, length=file_length)
    self.request.connection.stream.set_close_callback(partial(self._close_on_error, file))

  def renderIndex(self, path):
    files = []
    for i in os.listdir(path):
      try:
        info = self.FileEntry(path, i)
        files.append(info)
      except OSError:
        continue

    files.sort()
    self.render(self.dirindex, files=files, url=self.request.path,
               decodeURIComponent=tornado.escape.url_unescape)

  def _write_chunk(self, file, length):
    size = min(length, self.BLOCK_SIZE)
    left = length - size
    chunk = file.read(size)
    self.write(chunk)
    if left != 0:
      cb = partial(self._write_chunk, file, length=left)
    else:
      cb = self.finish
      file.close()
    self.flush(callback=cb)

  def _close_on_error(self, file):
    gen_log.info('closing %d on connection close.', file.fileno())
    file.close()

  def set_extra_headers(self, path):
    """For subclass to add extra headers to the response"""
    pass

  def get_cache_time(self, path, modified, mime_type):
    """Override to customize cache control behavior.

    Return a positive number of seconds to make the result
    cacheable for that amount of time or 0 to mark resource as
    cacheable for an unspecified amount of time (subject to
    browser heuristics).

    By default returns cache expiry of 10 years for resources requested
    with ``v`` argument.
    """
    return self.CACHE_MAX_AGE if "v" in self.request.arguments else 0

  @classmethod
  def make_static_url(cls, settings, path):
    """Constructs a versioned url for the given path.

    This method may be overridden in subclasses (but note that it is
    a class method rather than an instance method).

    ``settings`` is the `Application.settings` dictionary.  ``path``
    is the static path being requested.  The url returned should be
    relative to the current host.
    """
    abs_path = os.path.join(settings["static_path"], path)
    with cls._lock:
      hashes = cls._static_hashes
      if abs_path not in hashes:
        try:
          f = open(abs_path, "rb")
          hashes[abs_path] = hashlib.md5(f.read()).hexdigest()
          f.close()
        except Exception:
          gen_log.error("Could not open static file %r", path)
          hashes[abs_path] = None
      hsh = hashes.get(abs_path)
    static_url_prefix = settings.get('static_url_prefix', '/static/')
    if hsh:
      return static_url_prefix + path + "?v=" + hsh[:5]
    else:
      return static_url_prefix + path

def apache_style_log(handler):
  request = handler.request
  ip = request.remote_ip
  dt = time.strftime('[%d/%b/%Y:%H:%M:%S %z]')
  req = '"%s %s %s"' % (request.method, request.uri, request.version)
  status = handler.get_status()
  if 300 <= status < 400:
    length = '-'
  else:
    length = handler._headers.get('Content-Length', '-')
  referrer = '"%s"' % request.headers.get('Referer', '-')
  ua = '"%s"' % request.headers.get('User-Agent', '-')
  f = handler.application.settings.get('log_file', sys.stderr)
  print(ip, '- -', dt, req, status, length, referrer, ua, file=f)
  f.flush()

class HTTPConnection(tornado.httpserver.HTTPConnection):
  _recv_a_time = 8192
  def _on_headers(self, data):
    try:
      data = data.decode('latin1')
      eol = data.find("\r\n")
      start_line = data[:eol]
      try:
        method, uri, version = start_line.split(" ")
      except ValueError:
        raise tornado.httpserver._BadRequestException("Malformed HTTP request line")
      if not version.startswith("HTTP/"):
        raise tornado.httpserver._BadRequestException("Malformed HTTP version in HTTP Request-Line")
      headers = tornado.httputil.HTTPHeaders.parse(data[eol:])

      # HTTPRequest wants an IP, not a full socket address
      if self.address_family in (socket.AF_INET, socket.AF_INET6):
        remote_ip = self.address[0]
      else:
        # Unix (or other) socket; fake the remote address
        remote_ip = '0.0.0.0'

      self._request = tornado.httpserver.HTTPRequest(
        connection=self, method=method, uri=uri, version=version,
        headers=headers, remote_ip=remote_ip, protocol=self.protocol)

      content_length = headers.get("Content-Length")
      if content_length:
        content_length = int(content_length)
        use_tmp_files = self._get_handler_info()
        if not use_tmp_files and content_length > self.stream.max_buffer_size:
          raise tornado.httpserver._BadRequestException("Content-Length too long")
        if headers.get("Expect") == "100-continue":
          self.stream.write(b"HTTP/1.1 100 (Continue)\r\n\r\n")
        if use_tmp_files:
          gen_log.debug('using temporary files for uploading')
          self._receive_content(content_length)
        else:
          gen_log.debug('using memory for uploading')
          self.stream.read_bytes(content_length, self._on_request_body)
        return

      self.request_callback(self._request)
    except tornado.httpserver._BadRequestException as e:
      gen_log.info("Malformed HTTP request from %s: %s",
             self.address[0], e)
      self.close()
      return

  def _receive_content(self, content_length):
    if self._request.method in ("POST", "PUT"):
      content_type = self._request.headers.get("Content-Type", "")
      if content_type.startswith("multipart/form-data"):
        self._content_length_left = content_length
        fields = content_type.split(";")
        for field in fields:
          k, sep, v = field.strip().partition("=")
          if k == "boundary" and v:
            if v.startswith('"') and v.endswith('"'):
              v = v[1:-1]
            self._boundary = b'--' + v.encode('latin1')
            self._boundary_buffer = b''
            self._boundary_len = len(self._boundary)
            break
        self.stream.read_until(b"\r\n\r\n", self._on_content_headers)
      else:
        self.stream.read_bytes(content_length, self._on_request_body)

  def _on_content_headers(self, data, buf=b''):
    self._content_length_left -= len(data)
    data = self._boundary_buffer + data
    gen_log.debug('file header is %r', data)
    self._boundary_buffer = buf
    header_data = data[self._boundary_len+2:].decode('utf-8')
    headers = tornado.httputil.HTTPHeaders.parse(header_data)
    disp_header = headers.get("Content-Disposition", "")
    disposition, disp_params = tornado.httputil._parse_header(disp_header)
    if disposition != "form-data":
      gen_log.warning("Invalid multipart/form-data")
      self._read_content_body(None)
    if not disp_params.get("name"):
      gen_log.warning("multipart/form-data value missing name")
      self._read_content_body(None)
    name = disp_params["name"]
    if disp_params.get("filename"):
      ctype = headers.get("Content-Type", "application/unknown")
      fd, tmp_filename = tempfile.mkstemp(suffix='.tmp', prefix='tornado')
      self._request.files.setdefault(name, []).append(
        tornado.httputil.HTTPFile(
          filename=disp_params['filename'],
          tmp_filename=tmp_filename,
          content_type=ctype,
        )
      )
      self._read_content_body(os.fdopen(fd, 'wb'))
    else:
      gen_log.warning("multipart/form-data is not file upload, skipping...")
      self._read_content_body(None)

  def _read_content_body(self, fp):
    self.stream.read_bytes(
      min(self._recv_a_time, self._content_length_left),
      partial(self._read_into, fp)
    )

  def _read_into(self, fp, data):
    self._content_length_left -= len(data)
    buf = self._boundary_buffer + data

    bpos = buf.find(self._boundary)
    if bpos != -1:
      if fp:
        fp.write(buf[:bpos-2])
        fp.close()
      spos = buf.find(b'\r\n\r\n', bpos)
      if spos != -1:
        self._boundary_buffer = buf[bpos:spos+4]
        self._on_content_headers(b'', buf=buf[spos+4:])
      elif self._content_length_left > 0:
        self._boundary_buffer = buf[bpos:]
        self.stream.read_until(b"\r\n\r\n", self._on_content_headers)
      else:
        del self._content_length_left
        del self._boundary_buffer
        del self._boundary_len
        del self._boundary
        self.request_callback(self._request)
        return
    else:
      splitpos = -self._boundary_len-1
      if fp:
        fp.write(buf[:splitpos])
      self._boundary_buffer = buf[splitpos:]
      self._read_content_body(fp)

  def _get_handler_info(self):
    request = self._request
    app = self.request_callback
    handlers = app._get_host_handlers(request)
    handler = None
    for spec in handlers:
      match = spec.regex.match(request.path)
      if match:
        handler = spec.handler_class(app, request, **spec.kwargs)
        if spec.regex.groups:
          # None-safe wrapper around url_unescape to handle
          # unmatched optional groups correctly
          def unquote(s):
            if s is None:
              return s
            return tornado.escape.url_unescape(s, encoding=None)
          # Pass matched groups to the handler.  Since
          # match.groups() includes both named and unnamed groups,
          # we want to use either groups or groupdict but not both.
          # Note that args are passed as bytes so the handler can
          # decide what encoding to use.

          if spec.regex.groupindex:
            kwargs = dict(
              (str(k), unquote(v))
              for (k, v) in match.groupdict().iteritems())
          else:
            args = [unquote(s) for s in match.groups()]
        break
    if handler:
      return getattr(handler, 'use_tmp_files', False)

class HTTPServer(tornado.httpserver.HTTPServer):
  '''HTTPServer that supports uploading files to temporary files'''
  def handle_stream(self, stream, address):
    HTTPConnection(stream, address, self.request_callback,
                   self.no_keep_alive, self.xheaders)

########NEW FILE########
__FILENAME__ = sinaweibo
import urllib.parse
from functools import partial

from tornado import escape
from tornado.auth import OAuth2Mixin, _auth_return_future, AuthError
from tornado.httputil import url_concat
from tornado.httpclient import AsyncHTTPClient
from tornado.concurrent import return_future

class WeiboMixin(OAuth2Mixin):
  '''Weibo OAuth 2.0 authentication'''
  _OAUTH_NO_CALLBACKS = False

  _WEIBO_BASE_URL = 'https://api.weibo.com/oauth2/'
  # for the mobile client, the following should be used
  # _OAUTH_URL_BASE = 'https://open.weibo.cn/oauth2/'

  _OAUTH_ACCESS_TOKEN_URL = _WEIBO_BASE_URL + 'access_token'
  _OAUTH_AUTHORIZE_URL = _WEIBO_BASE_URL + 'authorize'

  REQUEST_FIELDS = frozenset({
    'id', 'idstr', 'name', 'screen_name', 'province', 'city', 'location',
    'description', 'url', 'profile_image_url', 'gender', 'domain',
    'followers_count', 'friends_count', 'statuses_count', 'favourites_count',
    'created_at', 'following', 'allow_all_act_msg', 'geo_enabled', 'verified',
    'allow_all_comment', 'avatar_large', 'verified_reason', 'follow_me',
    'online_status', 'bi_followers_count',
  })

  def get_auth_http_client(self):
    return AsyncHTTPClient()

  @_auth_return_future
  def get_authenticated_user(self, redirect_uri, client_id, client_secret,
                             code, callback, extra_fields=None):
    http = self.get_auth_http_client()
    args = {
      "redirect_uri": redirect_uri,
      "code": code,
      "client_id": client_id,
      "client_secret": client_secret,
    }

    if extra_fields:
      fields = self.REQUEST_FIELDS & extra_fields
    else:
      fields = self.REQUEST_FIELDS

    http.fetch(
      self._OAUTH_ACCESS_TOKEN_URL,
      partial(
        self._on_access_token, redirect_uri, client_id,
        client_secret, callback, fields
      ),
      method = 'POST',
      body = urllib.parse.urlencode(args),
    )

  def _on_access_token(self, redirect_uri, client_id, client_secret,
                       future, fields, response):
    if response.error:
      future.set_exception(AuthError(
        'SinaWeibo auth error: %s' % str(response)))
      return

    args = escape.json_decode(response.body)
    session = {
      'access_token': args['access_token'],
      'expires_in': args['expires_in'],
      'uid': args['uid'],
    }

    weibo_request(
      path = 'users/show',
      callback = partial(
        self._on_get_user_info, future, session, fields,
      ),
      access_token = session['access_token'],
      uid = session['uid'],
      httpclient = self.get_auth_http_client(),
    )

  def _on_get_user_info(self, future, session, fields, user):
    fieldmap = {field: user.get(field) for field in fields}

    fieldmap['access_token'] = session['access_token']
    fieldmap['session_expires'] = session['expires_in']
    future.set_result(fieldmap)

@_auth_return_future
def weibo_request(path, callback, access_token=None, post_args=None,
                  httpclient=None, **args):
  url = "https://api.weibo.com/2/" + path + ".json"
  all_args = {}
  if access_token:
    all_args['access_token'] = access_token
  all_args.update(args)
  if post_args:
    all_args.update(post_args)

  header = {'Authorization': 'OAuth2 ' + access_token}
  callback = partial(_on_weibo_request, callback)
  http = httpclient or AsyncHTTPClient()

  if post_args is not None:
    http.fetch(
      url, method="POST", body=urllib.parse.urlencode(all_args),
      callback=callback, headers=header)
  else:
    if all_args:
      url = url_concat(url, all_args)
    http.fetch(url, callback=callback, headers=header)

def _on_weibo_request(future, response):
  if response.body:
    body = response.body.decode('utf-8')
  else:
    body = None

  if response.error:
    try:
      ex = WeiboError(body)
    except:
      ex = WeiboRequestError(response)
    future.set_exception(ex)
  else:
    future.set_result(escape.json_decode(body))

class WeiboRequestError(Exception):
  pass

class WeiboError(WeiboRequestError):
  def __init__(self, body):
    # doc: http://open.weibo.com/wiki/Error_code
    self._raw = body
    info = escape.json_decode(body)
    self.path = info['request']
    self.code = info['error_code']
    self.msg = info['error']

  def __repr__(self):
    return '%s(%r)' % (
      self.__class__.__name__, self._raw)

@return_future
def send_status(status, access_token, callback,
                annotations=None, httpclient=None):
  args = {
    'status': status,
  }
  if annotations:
    args['annotations'] = annotations
  weibo_request('statuses/update', callback,
                access_token = access_token,
                httpclient = httpclient, post_args = args)

########NEW FILE########
__FILENAME__ = util
import os
import stat
import datetime
import re

class FileEntry:
  '''For ``StaticFileHandler`` with directory index enabled'''
  isdir = False
  def __init__(self, path, file):
    st = os.stat(os.path.join(path, file))
    self.time = datetime.datetime.fromtimestamp(st[stat.ST_MTIME])
    self.name = file
    self.filename = file
    if stat.S_ISDIR(st[stat.ST_MODE]):
      self.isdir = True
      self.filename += '/'
    self.size = st[stat.ST_SIZE]

  def __lt__(self, another):
    if self.isdir and not another.isdir:
      return True
    if not self.isdir and another.isdir:
      return False
    return self.name < another.name

def routes_adjust_prefix(routers, prefix):
  p = re.escape(prefix)
  return [tuple([p+r] + list(args)) for r, *args in routers]

########NEW FILE########
__FILENAME__ = myutils
'''
一些常用短小的函数/类
'''

import os, sys
import datetime
from functools import lru_cache, wraps
import logging
try:
  import ipaddress
except ImportError:
  # Python 3.2-
  ipaddress = None
import contextlib
import signal
import hashlib

from nicelogger import enable_pretty_logging

def path_import(path):
  '''指定路径来 import'''
  d, f = os.path.split(path)
  if d not in sys.path:
    sys.path[0:0] = [d]
    ret = __import__(os.path.splitext(f)[0])
    del sys.path[0]
    return ret

def safe_overwrite(fname, data, *, method='write', mode='w', encoding=None):
  # FIXME: directory has no read perm
  # FIXME: symlinks and hard links
  tmpname = fname + '.tmp'
  # if not using "with", write can fail without exception
  with open(tmpname, mode, encoding=encoding) as f:
    getattr(f, method)(data)
  # if the above write failed (because disk is full etc), the old data should be kept
  os.rename(tmpname, fname)

def filesize(size):
  '''将 数字 转化为 xxKiB 的形式'''
  units = 'KMGT'
  left = abs(size)
  unit = -1
  while left > 1100 and unit < 3:
    left = left / 1024
    unit += 1
  if unit == -1:
    return '%dB' % size
  else:
    if size < 0:
      left = -left
    return '%.1f%siB' % (left, units[unit])

def humantime(t):
  '''seconds -> XhYmZs'''
  units = 'hms'
  m, s = divmod(t, 60)
  h, m = divmod(m, 60)
  ret = ''
  if h:
    ret += '%dh' % h
  if m:
    ret += '%dm' % m
  if s:
    ret += '%ds' % s
  return ret

def input_t(timeout, prompt=''):
  '''带有超时的输入，使用 select() 实现

  超时返回 None'''
  from select import select

  # 也可以用多进程/signal 实现
  # 但 signal 不能在非主线程中调用
  sys.stdout.write(prompt)
  sys.stdout.flush()
  if select([sys.stdin.fileno()], [], [], timeout)[0]:
    return input()

def _timed_read(file, timeout):
  from select import select
  if select([file], [], [], timeout)[0]:
    return file.read(1)

def getchar(prompt, hidden=False, end='\n', timeout=None):
  '''读取一个字符'''
  import termios
  sys.stdout.write(prompt)
  sys.stdout.flush()
  fd = sys.stdin.fileno()

  def _read():
    if timeout is None:
      ch = sys.stdin.read(1)
    else:
      ch = _timed_read(sys.stdin, timeout)
    return ch

  if os.isatty(fd):
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    if hidden:
      new[3] = new[3] & ~termios.ICANON & ~termios.ECHO
    else:
      new[3] = new[3] & ~termios.ICANON
    new[6][termios.VMIN] = 1
    new[6][termios.VTIME] = 0
    try:
      termios.tcsetattr(fd, termios.TCSANOW, new)
      termios.tcsendbreak(fd, 0)
      ch = _read()
    finally:
      termios.tcsetattr(fd, termios.TCSAFLUSH, old)
  else:
    ch = _read()

  sys.stdout.write(end)
  return ch

def loadso(fname):
  '''ctypes.CDLL 的 wrapper，从 sys.path 中搜索文件'''
  from ctypes import CDLL

  for d in sys.path:
    p = os.path.join(d, fname)
    if os.path.exists(p):
      return CDLL(p)
  raise ImportError('%s not found' % fname)

def restart_if_failed(func, max_tries, args=(), kwargs={}, secs=60, sleep=None):
  '''
  re-run when some exception happens, until `max_tries` in `secs`
  '''
  import time
  import traceback
  from collections import deque

  dq = deque(maxlen=max_tries)
  while True:
    dq.append(time.time())
    try:
      func(*args, **kwargs)
    except:
      traceback.print_exc()
      if len(dq) == max_tries and time.time() - dq[0] < secs:
        break
      if sleep is not None:
        time.sleep(sleep)
    else:
      break

def daterange(start, stop=datetime.date.today(), step=datetime.timedelta(days=1)):
  d = start
  while d < stop:
    yield d
    d += step

@lru_cache()
def findfont(fontname):
  from subprocess import check_output
  out = check_output(['fc-match', '-v', fontname]).decode()
  for l in out.split('\n'):
    if l.lstrip().startswith('file:'):
      return l.split('"', 2)[1]

def debugfunc(logger=logging, *, _id=[0]):
  def w(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      myid = _id[0]
      _id[0] += 1
      logger.debug('[func %d] %s(%r, %r)', myid, func.__name__, args, kwargs)
      ret = func(*args, **kwargs)
      logger.debug('[func %d] return: %r', myid, ret)
      return ret
    return wrapper
  return w

@contextlib.contextmanager
def execution_timeout(timeout):
  def timed_out(signum, sigframe):
    raise TimeoutError

  old_hdl = signal.signal(signal.SIGALRM, timed_out)
  old_itimer = signal.setitimer(signal.ITIMER_REAL, timeout, 0)
  yield
  signal.setitimer(signal.ITIMER_REAL, *old_itimer)
  signal.signal(signal.SIGALRM, old_hdl)

def find_executables(name, path=None):
  '''find all matching executables with specific name in path'''
  if path is None:
    path = os.environ['PATH'].split(os.pathsep)
  elif isinstance(path, str):
    path = path.split(os.pathsep)
  path = [p for p in path if os.path.isdir(p)]

  return [os.path.join(p, f) for p in path for f in os.listdir(p) if f == name]

# The following three are learnt from makepkg
def user_choose(prompt, timeout=None):
  # XXX: hard-coded term characters are ok?
  prompt = '\x1b[1;34m::\x1b[1;37m %s\x1b[0m ' % prompt
  return getchar(prompt, timeout=timeout)

def msg(msg):
  # XXX: hard-coded term characters are ok?
  print('\x1b[1;32m==>\x1b[1;37m %s\x1b[0m' % msg)

def msg2(msg):
  # XXX: hard-coded term characters are ok?
  print('\x1b[1;34m  ->\x1b[1;37m %s\x1b[0m' % msg)

def is_internal_ip(ip):
  if ipaddress is None:
    return False

  ip = ipaddress.ip_address(ip)
  return ip.is_loopback or ip.is_private or ip.is_reserved or ip.is_link_local

@contextlib.contextmanager
def at_dir(d):
  old_dir = os.getcwd()
  os.chdir(d)
  yield
  os.chdir(old_dir)

def firstExistentPath(paths):
  for p in paths:
    if os.path.exists(p):
      return p

def md5sum_of_file(file):
  with open(file, 'rb') as f:
    m = hashlib.md5()
    while True:
      d = f.read(8192)
      if not d:
        break
      m.update(d)
  return m.hexdigest()

########NEW FILE########
__FILENAME__ = my_class
'''
一些有用的类

2010年10月22日
'''

import datetime
import collections

class StringWithTime(str):
  '''包含时间信息的字符串'''
  def __init__(self, value, time=None):
    str.__init__(self)
    if time is None:
      time = datetime.datetime.now()
    self.time = time

  def __repr__(self):
    return '<"%s" at "%s">' % ( self, self.time.strftime('%Y/%m/%d %H:%M:%S'))

class ListBasedSet(collections.Set):
  ''' Alternate set implementation favoring space over speed
      and not requiring the set elements to be hashable. '''
  def __init__(self, iterable=()):
    self.elements = lst = []
    for value in iterable:
      if value not in lst:
        lst.append(value)
  def __iter__(self):
    return iter(self.elements)
  def __contains__(self, value):
    return value in self.elements
  def __len__(self):
    return len(self.elements)

class StrlikeList(list):
  '''多个非重复数据
  add 用于添加数据项'''

  def __init__(self, iterable, maxlength=0, formatter=None):
    '''formatter 用于输出字符串表示
    maxlength 为最大长度，0 为不限制'''
    list.__init__(self, iterable)
    if formatter is None:
      formatter = lambda x: ', '.join(x)
    self.formatter = formatter
    self.maxlength = maxlength

  def __str__(self):
    return self.formatter(self)

  def add(self, item):
    if item in self:
      self.remove(item)
    self.insert(0, item)
    ml = self.maxlength
    if ml and len(self) > ml:
      del self[ml:]


########NEW FILE########
__FILENAME__ = netservice
'''
提供网络信息获取服务
'''
from functools import lru_cache
import json
import urllib.request

import htmlutils
from url import *

def getTitle(url, headers={}, timeout=5):
  '''
  获取网页标题，url 要指定协议的

  如果字符串解码失败，返回 bytes
  如果不是网页返回 None

  可能出现的异常
    socket.error: [Errno 111] Connection refused
    socket.timeout: timed out
  '''
  # TODO 对 meta 刷新的处理
  import re
  import socket
  from httpsession import Session

  defaultheaders = {}
  defaultheaders['User-Agent'] = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.6) Gecko/20100628 Ubuntu/10.04 (lucid) Firefox/3.6.6'
  defaultheaders['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.7'
  defaultheaders['Accept-Language'] = 'zh-cn,zh;q=0.5'
  defaultheaders['Accept-Charset'] = 'utf-8,gb18030;q=0.7,*;q=0.7'
  defaultheaders.update(headers)
  headers = defaultheaders

  s = Session()
  try:
    response = s.request(url, headers=headers)
  except socket.error:
    s = Session(proxy={
      'http':  'http://localhost:8087',
      'https': 'http://localhost:8087',
    })
    response = s.request(url, headers=headers)

  contentType = response.getheader('Content-Type', default='text/html')
  type = contentType.split(';', 1)[0]
  if type.find('html') == -1 and type.find('xml') == -1:
    return None

  try:
    charset = contentType.rsplit('=', 1)[1]
  except IndexError:
    charset = None

  title = b''
  content = b''
  for i in range(300):
    content += response.read(64)
    if len(content) < 64:
      break
    m = re.search(b'<title[^>]*>([^<]*)<', content, re.IGNORECASE)
    if m:
      title = m.group(1)
      break
  response.close()

  if charset is None:
    import chardet
    title = title.decode(chardet.detect(title)['encoding'])
  else:
    if charset.lower().find('big5') != -1:
      charset = 'big5'
    elif charset.lower() == 'windows-31j':
      charset = 'cp932'
    title = title.decode(charset)
  title = htmlutils.entityunescape(title.replace('\n', '')).strip()

  return title or None

def ubuntuPaste(poster='', screenshot='', code2='',
    klass='bash', filename=None):
  '''
  paste 到 http://paste.ubuntu.org.cn/
  screenshot 是文件路径

  返回查看此帖子的 URL （字符串）
  '''
  from httpsession import Session
  paste_url = 'http://paste.ubuntu.org.cn/'
  fields = [
    ('paste',  'send'),
    ('poster', poster),
    ('code2',  code2),
    ('class',  klass),
  ]
  if screenshot:
    files = (
      ('screenshot', filename or os.path.split(screenshot)[1], open(screenshot, 'rb').read()),
    )
  else:
    files = ()

  data = encode_multipart_formdata(fields, files)
  s = Session()
  r = s.request(paste_url, data[1], headers={
    'Content-Type': data[0],
    'Expect': '100-continue',
  })
  return r.geturl()

@lru_cache(maxsize=100)
def taobaoip(ip):
  res = urllib.request.urlopen('http://ip.taobao.com/service/getIpInfo.php?ip=' + ip)
  data = json.loads(res.read().decode('utf-8'))['data']
  ret = ' '.join(data[x] for x in ("country", "region", "city", "county", "isp")).strip()
  return ret

########NEW FILE########
__FILENAME__ = nicelogger
'''
A Tornado-inspired logging formatter, with displayed time with millisecond accuracy

FYI: pyftpdlib also has a Tornado-style logger.
'''

import sys
import time
import logging

class TornadoLogFormatter(logging.Formatter):
  def __init__(self, color, *args, **kwargs):
    super().__init__(self, *args, **kwargs)
    self._color = color
    if color:
      import curses
      curses.setupterm()
      if sys.hexversion < 0x30203f0:
        fg_color = str(curses.tigetstr("setaf") or
                   curses.tigetstr("setf") or "", "ascii")
      else:
        fg_color = curses.tigetstr("setaf") or curses.tigetstr("setf") or b""
      self._colors = {
        logging.DEBUG: str(curses.tparm(fg_color, 4), # Blue
                     "ascii"),
        logging.INFO: str(curses.tparm(fg_color, 2), # Green
                    "ascii"),
        logging.WARNING: str(curses.tparm(fg_color, 3), # Yellow
                     "ascii"),
        logging.ERROR: str(curses.tparm(fg_color, 1), # Red
                     "ascii"),
        logging.CRITICAL: str(curses.tparm(fg_color, 9), # Bright Red
                     "ascii"),
      }
      self._normal = str(curses.tigetstr("sgr0"), "ascii")

  def format(self, record):
    try:
      record.message = record.getMessage()
    except Exception as e:
      record.message = "Bad message (%r): %r" % (e, record.__dict__)
    record.asctime = time.strftime(
      "%m-%d %H:%M:%S", self.converter(record.created))
    record.asctime += '.%03d' % ((record.created % 1) * 1000)
    prefix = '[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d]' % \
      record.__dict__
    if self._color:
      prefix = (self._colors.get(record.levelno, self._normal) +
            prefix + self._normal)
    formatted = prefix + " " + record.message
    if record.exc_info:
      if not record.exc_text:
        record.exc_text = self.formatException(record.exc_info)
    if record.exc_text:
      formatted = formatted.rstrip() + "\n" + record.exc_text
    return formatted.replace("\n", "\n    ")

def enable_pretty_logging(level=logging.DEBUG, handler=None, color=None):
  '''
  handler: specify a handler instead of default StreamHandler
  color:   boolean, force color to be on / off. Default to be on only when
           ``handler`` isn't specified and the term supports color
  '''
  logger = logging.getLogger()
  if handler is None:
    h = logging.StreamHandler()
  else:
    h = handler
  if color is None:
    color = False
    if handler is None and sys.stderr.isatty():
      try:
        import curses
        curses.setupterm()
        if curses.tigetnum("colors") > 0:
          color = True
      except:
        import traceback
        traceback.print_exc()
  formatter = TornadoLogFormatter(color=color)
  h.setLevel(level)
  h.setFormatter(formatter)
  logger.setLevel(level)
  logger.addHandler(h)

########NEW FILE########
__FILENAME__ = notify
'''
调用 libnotify
'''

__all__ = ["set", "show", "update", "set_timeout", "set_urgency"]

from ctypes import *
from threading import Lock
import atexit

NOTIFY_URGENCY_LOW = 0
NOTIFY_URGENCY_NORMAL = 1
NOTIFY_URGENCY_CRITICAL = 2
UrgencyLevel = {NOTIFY_URGENCY_LOW, NOTIFY_URGENCY_NORMAL, NOTIFY_URGENCY_CRITICAL}

libnotify = None
gobj = None
libnotify_lock = Lock()
libnotify_inited = False

class obj: pass
notify_st = obj()

def set(summary=None, body=None, icon_str=None):
  with libnotify_lock:
    init()

  if summary is not None:
    notify_st.summary = summary.encode()
  notify_st.body = notify_st.icon_str = None
  if body is not None:
    notify_st.body = body.encode()
  if icon_str is not None:
    notify_st.icon_str = icon_str.encode()

  libnotify.notify_notification_update(
    notify_st.notify,
    c_char_p(notify_st.summary),
    c_char_p(notify_st.body),
    c_char_p(notify_st.icon_str),
    c_void_p()
  )

def show():
  libnotify.notify_notification_show(notify_st.notify, c_void_p())

def update(summary=None, body=None, icon_str=None):
  if not any((summary, body)):
    raise TypeError('at least one argument please')

  set(summary, body, icon_str)
  show()

def set_timeout(self, timeout):
  '''set `timeout' in milliseconds'''
  libnotify.notify_notification_set_timeout(notify_st.notify, int(timeout))

def set_urgency(self, urgency):
  if urgency not in UrgencyLevel:
    raise ValueError
  libnotify.notify_notification_set_urgency(notify_st.notify, urgency)

def init():
  global libnotify_inited, libnotify, gobj
  if libnotify_inited:
    return

  try:
    libnotify = CDLL('libnotify.so')
  except OSError:
    libnotify = CDLL('libnotify.so.4')
  gobj = CDLL('libgobject-2.0.so')

  libnotify.notify_init('pynotify')
  libnotify_inited = True
  notify_st.notify = libnotify.notify_notification_new(
    c_void_p(), c_void_p(), c_void_p(),
  )
  atexit.register(uninit)

def uninit():
  global libnotify_inited
  try:
    if libnotify_inited:
      gobj.g_object_unref(notify_st.notify)
      libnotify.notify_uninit()
      libnotify_inited = False
  except AttributeError:
    # libnotify.so 已被卸载
    pass

if __name__ == '__main__':
  from time import sleep
  notify = __import__('__main__')
  notify.set('This is a test', '测试一下。')
  notify.show()
  sleep(1)
  notify.update(body='再测试一下。')

########NEW FILE########
__FILENAME__ = opencc
#!/usr/bin/env python
# vim:fileencoding=utf-8

'''
OpenCC wrapper

Tested with OpenCC version 0.4.2, 0.4.3.
Compatile with both Python 2.x and 3.x.
'''

from __future__ import print_function

from ctypes import cdll, c_char_p
import readline
import sys

if sys.version_info < (3,):
    def input(prompt=''):
        return raw_input(prompt).decode('utf-8')

    def bytes(name, encoding):
        return str(name)

__all__ = ['OpenCC']

try:
    libopencc = cdll.LoadLibrary('libopencc.so')
except OSError:
    libopencc = cdll.LoadLibrary('libopencc.so.1')
libc = cdll.LoadLibrary('libc.so.6')

class OpenCC(object):
    def __init__(self, config_file):
        self.od = libopencc.opencc_open(c_char_p(bytes(config_file, 'utf-8')))
        if self.od == -1:
            raise Exception('failed to create an OpenCC object')

    def convert(self, text):
        text = text.encode('utf-8')
        retv_c = c_char_p(libopencc.opencc_convert_utf8(self.od, text, len(text)))
        ret = retv_c.value.decode('utf-8')
        libc.free(retv_c)
        return ret

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('config file not provided.')

    converter = OpenCC(sys.argv[1])
    while True:
        try:
            l = input()
            print(converter.convert(l))
        except (EOFError, KeyboardInterrupt):
            break

########NEW FILE########
__FILENAME__ = pidfile
'''
PID 管理，在 with 语句中使用，控制进程只有一个在运行，否则抛出 AlreadyRun 异常
'''

import os
import sys
import time
import signal

class PIDFile:
  def __init__(self, pidfile):
    self.pidfile = pidfile
    try:
      pid = int(open(pidfile).read())
    except (IOError, ValueError):
      open(pidfile, 'w').write(str(os.getpid()))
      return
    else:
      try:
        os.kill(pid, 0)
      except OSError:
        open(pidfile, 'w').write(str(os.getpid()))
      else:
        raise AlreadyRun(pid)

  def __enter__(self):
    pass

  def __exit__(self, exc_type, exc_value, traceback):
    os.unlink(self.pidfile)

def wait_and_exit(pid):
  res = os.waitpid(pid, 0)[1]
  status = res & 0x7f
  if status == 0:
    status = (res & 0xff00) >> 8
  sys.stdout.flush()
  os._exit(status)

def _got_sgiusr2(signum, sigframe):
  os._exit(0)

class Daemonized(PIDFile):
  '''daemonize the process and then write its pid to file
  * fork
    * chdir("/")
    * setsid
    * fork
      * close fds
      * do_work
    * killed by SIGUSR2
    * _exit
  * waitpid
  * _exit

  This procedure is borrowed from MongoDB.
  '''
  def __init__(self, pidfile):
    pid = os.fork()
    if pid:
      wait_and_exit(pid)

    os.chdir('/')
    os.setsid()
    leader = os.getpid()
    pid_2 = os.fork()
    if pid_2:
      signal.signal(signal.SIGUSR2, _got_sgiusr2)
      wait_and_exit(pid_2)

    super().__init__(pidfile)
    fd = os.open('/dev/null', os.O_RDWR)
    os.dup2(fd, 0)
    os.dup2(fd, 1)
    os.dup2(fd, 2)
    os.close(fd)
    os.kill(leader, signal.SIGUSR2)

class AlreadyRun(Exception):
  def __init__(self, pid):
    self.pid = pid
  def __repr__(self):
    return "Process with pid %d is already running" % self.pid


########NEW FILE########
__FILENAME__ = pinyinsplit
#!/usr/bin/env python3
# vim:fileencoding=utf-8

# Author: Eric Miao <eric.mjian@gmail.com>
# Modified By: lilydjwg <lilydjwg@gmail.com>

pinyinList = ['a', 'o', 'e', 'ai', 'ei', 'ao', 'ou', 'an', 'en', 'vn', 'van', 'ang', 'eng',
              'ba', 'bo', 'bi', 'bu', 'bai', 'bei', 'bao', 'bie', 'biao', 'ban', 'ben', 'bin','bian', 'bang', 'beng', 'bing',
              'pa', 'po', 'pi', 'pu', 'pai', 'pei', 'pao', 'pou', 'pie', 'piao', 'pan', 'pen', 'pin', 'pian', 'pang', 'peng', 'ping',
              'ma', 'mo', 'me', 'mi', 'mu', 'mai', 'mei', 'mao', 'mou', 'mie', 'miao', 'miu','man', 'men', 'min', 'mian', 'mang', 'meng', 'ming',
              'fa', 'fo', 'fu', 'fei', 'nao', 'fou', 'fan', 'fen', 'fang', 'feng',
              'da', 'de', 'di', 'du', 'dai', 'dao', 'dou', 'dia', 'die', 'duo', 'diao', 'diu', 'dui', 'dan', 'den', 'din', 'dian', 'duan', 'dun', 'dang', 'deng', 'ding', 'dong',
              'ta', 'te', 'ti', 'tu', 'tai', 'tao', 'tou', 'tie', 'tuo', 'tiao', 'tui', 'tan', 'tin', 'tian', 'tuan', 'tun', 'tang', 'teng', 'ting', 'tong',
              'na', 'ne', 'ni', 'nu', 'nai', 'nei', 'nao', 'nou', 'nie', 'nuo', 'nve', 'niao', 'niu', 'nan', 'nen', 'nin', 'nian', 'nuan', 'nun', 'nang', 'neng', 'ning', 'nong', 'niang',
              'la', 'le', 'li', 'lu', 'lai', 'lei', 'lao', 'lou', 'lie', 'luo', 'lve', 'liao', 'liu', 'lan', 'len', 'lin', 'lian', 'luan', 'lun', 'lang', 'leng', 'ling', 'long', 'liang',
              'ga', 'ge', 'gu', 'gai', 'gei', 'gao', 'gou', 'gua', 'guo', 'guai', 'gui', 'gan', 'gen', 'guan', 'gun', 'gang', 'geng', 'gong', 'guang',
              'ka', 'ke', 'ku', 'kai', 'kei', 'kao', 'kou', 'kua', 'kuo', 'kuai', 'kui', 'kan', 'ken', 'kuan', 'kun', 'kang', 'keng', 'kong', 'kuang',
              'ha', 'he', 'hu', 'hai', 'hei', 'hao', 'hou', 'hua', 'huo', 'huai', 'hui', 'han', 'hen', 'huan', 'hun', 'hang', 'heng', 'hong', 'huang',
              'ju', 'jiao', 'jiu', 'jian', 'juan', 'jun', 'jing', 'jiang', 'jiong', 'jia',
              'qi', 'qu', 'qia', 'qie', 'qiao', 'qiu', 'qin', 'qian', 'quan', 'qun', 'qing','qiang', 'qiong',
              'xi', 'xu', 'xia', 'xie', 'xiao', 'xiu', 'xin', 'xian', 'xuan', 'xun', 'xing','xiang', 'xiong',
              'zha', 'zhe', 'zhi', 'zhu', 'zhai', 'zhao', 'zhou', 'zhua', 'zhuo', 'zhuai', 'zhui', 'zhan', 'zhen', 'zhuan', 'zhun', 'zhang', 'zheng', 'zhong', 'zhuang',
              'cha', 'che', 'chi', 'chu', 'chai', 'chao', 'chou', 'chuo', 'chuai', 'chui', 'chan', 'chen', 'chuan', 'chun', 'chang', 'cheng', 'chong', 'chuang',
              'sha', 'she', 'shi', 'shu', 'shai', 'shao', 'shou', 'shua', 'shuo', 'shuai', 'shui', 'shan', 'shen', 'shuan', 'shun', 'shang', 'sheng', 'shong', 'shuang',
              're', 'ri', 'ru', 'rao', 'rou', 'ruo', 'rui', 'ran', 'ren', 'ruan', 'run', 'rang', 'reng', 'rong',
              'za', 'ze', 'zi', 'zu', 'zai', 'zei', 'zao', 'zou', 'zuo', 'zui', 'zan', 'zen','zuan', 'zun', 'zang', 'zeng', 'zong',
              'ca', 'ce', 'ci', 'cu', 'cai', 'cao', 'cou', 'cuo', 'cui', 'can', 'cen', 'cuan', 'cun', 'cang', 'ceng', 'cong',
              'sa', 'se', 'si', 'su', 'sai', 'sao', 'sou', 'suo', 'sui', 'san', 'sen', 'suan', 'sun', 'sang', 'seng', 'song',
              'ya', 'yo', 'ye', 'yi', 'yu', 'yao', 'you', 'yan', 'yin', 'yuan', 'yun', 'yang', 'ying', 'yong',
              'wo', 'wu', 'wai', 'wei', 'wan', 'wen', 'wang', 'weng', 'yong', 'er']


def split_pinyin(word):
  print('=' * 12)
  print(word)
  output = False
  ps = []
  if len(word) == 0:
    return True, []

  pres = []
  for pinyin in pinyinList:
    l = len(pinyin)
    if word[:l] == pinyin:
      pres.append(pinyin)
  print(pres)

  if not pres:
    return False, []

  for pre in pres:
    r, rp = split_pinyin(word[len(pre):])
    if r:
      output = True
      ps.append(pre)
      ps.extend(rp)
      break
  return output, ps

if __name__ == '__main__':
  import sys
  print(split_pinyin(''.join(sys.argv[1:]) if len(sys.argv) > 1 else 'zheshiyigeceshi'))

########NEW FILE########
__FILENAME__ = pinyintone
#!/usr/bin/env python3
# vim:fileencoding=utf-8

# http://www.robertyu.com/wikiperdido/Pinyin%20Parser%20for%20MoinMoin

# definitions
# For the pinyin tone rules (which vowel?), see
# http://www.pinyin.info/rules/where.html
#
# map (final) constanant+tone to tone+constanant
mapConstTone2ToneConst = {'n1':  '1n',
                          'n2':  '2n',
                          'n3':  '3n',
                          'n4':  '4n',
                          'ng1': '1ng',
                          'ng2': '2ng',
                          'ng3': '3ng',
                          'ng4': '4ng',
                          'r1':  '1r',
                          'r2':  '2r',
                          'r3':  '3r',
                          'r4':  '4r'}

# map vowel+vowel+tone to vowel+tone+vowel
mapVowelVowelTone2VowelToneVowel = {'ai1': 'a1i',
                                    'ai2': 'a2i',
                                    'ai3': 'a3i',
                                    'ai4': 'a4i',
                                    'ao1': 'a1o',
                                    'ao2': 'a2o',
                                    'ao3': 'a3o',
                                    'ao4': 'a4o',
                                    'ei1': 'e1i',
                                    'ei2': 'e2i',
                                    'ei3': 'e3i',
                                    'ei4': 'e4i',
                                    'ou1': 'o1u',
                                    'ou2': 'o2u',
                                    'ou3': 'o3u',
                                    'ou4': 'o4u'}

# map vowel-number combination to unicode
mapVowelTone2Unicode = {'a1': 'ā',
                        'a2': 'á',
                        'a3': 'ǎ',
                        'a4': 'à',
                        'e1': 'ē',
                        'e2': 'é',
                        'e3': 'ě',
                        'e4': 'è',
                        'i1': 'ī',
                        'i2': 'í',
                        'i3': 'ǐ',
                        'i4': 'ì',
                        'o1': 'ō',
                        'o2': 'ó',
                        'o3': 'ǒ',
                        'o4': 'ò',
                        'u1': 'ū',
                        'u2': 'ú',
                        'u3': 'ǔ',
                        'u4': 'ù',
                        'v1': 'ǜ',
                        'v2': 'ǘ',
                        'v3': 'ǚ',
                        'v4': 'ǜ',
                       }

def ConvertPinyinToneNumbers(lineIn):
  """
  Convert pinyin text with tone numbers to pinyin with diacritical marks
  over the appropriate vowel.

  In:  input text.  Must be unicode type.
  Out:  utf-8 copy of lineIn, tone markers replaced with diacritical marks
  over the appropriate vowels

  For example:
  xiao3 long2 tang1 bao1 -> xiǎo lóng tāng bāo

  x='xiao3 long2 tang1 bao4'
  y=pinyintones.ConvertPinyinToneNumbers(x)
  """

  lineOut = lineIn

  # first transform
  for x, y in mapConstTone2ToneConst.items():
    lineOut = lineOut.replace(x, y).replace(x.upper(), y.upper())

  # second transform
  for x, y in mapVowelVowelTone2VowelToneVowel.items():
    lineOut = lineOut.replace(x, y).replace(x.upper(), y.upper())

  #
  # third transform
  for x, y in mapVowelTone2Unicode.items():
    lineOut = lineOut.replace(x, y).replace(x.upper(), y.upper())

  return lineOut.replace('v', 'ü').replace('V', 'Ü')

if __name__ == '__main__':
  import sys
  for lineIn in sys.stdin:
    lineOut = ConvertPinyinToneNumbers(lineIn)
    sys.stdout.write(lineOut)

########NEW FILE########
__FILENAME__ = python
import os

def mymodsImported(scriptfile):
  '''导入的模块哪些是通过环境变量找到的？'''
  try:
    dirs = os.getenv('PYTHONPATH').split(':')
  except AttributeError:
    return []

  if not dirs:
    return []

  from modulefinder import ModuleFinder
  finder = ModuleFinder()
  finder.run_script(scriptfile)

  def filterdir(mod):
    file = mod.__file__
    if not file:
      return False
    for i in dirs:
      if file.startswith(i):
        return True
    return False

  return [m for m in finder.modules.values() if filterdir(m)]

########NEW FILE########
__FILENAME__ = QQWry
#!/usr/bin/env python3

'''QQWry 模块，提供读取纯真IP数据库的数据的功能。

纯真数据库格式参考 http://lumaqq.linuxsir.org/article/qqwry_format_detail.html
作者 AutumnCat. 最后修改在 2008年 04月 29日
bones7456 最后修改于 2009-02-02
lilydjwg 修改于 2014-05-26
本程序遵循 GNU GENERAL PUBLIC LICENSE Version 2 (http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt)
'''

#数据文件下载地址： http://update.cz88.net/soft/qqwry.rar

from struct import unpack, pack
import sys, _socket, mmap
from collections import namedtuple

DataFileName = "/home/lilydjwg/etc/data/QQWry.Dat"

def _ip2ulong(ip):
  '''点分十进制 -> unsigned long
  '''
  return unpack('>L', _socket.inet_aton(ip))[0]

def _ulong2ip(ip):
  '''unsigned long -> 点分十进制
  '''
  return _socket.inet_ntoa(pack('>L', ip))

class ipInfo(namedtuple('ipInfo', 'sip eip country area')):
  __slots__ = ()
  def __str__(self):
    '''str(x)
    '''
    # TODO: better formatting
    return str(self[0]).ljust(16) + ' - ' + str(self[1]).rjust(16) + ' ' + self[2] + self[3]

  def normalize(self):
    '''转化ip地址成点分十进制.
    '''
    return self.__class__(
      _ulong2ip(self[0]), _ulong2ip(self[1]), self[2], self[3])

class QQWry:
  def __init__(self, dbfile = DataFileName, charset = 'gbk'):
    if isinstance(dbfile, (str, bytes)):
      dbfile = open(dbfile, 'rb')

    self.f = dbfile
    self.charset = charset
    self.f.seek(0)
    self.indexBaseOffset = unpack('<L', self.f.read(4))[0] #索引区基址
    self.Count = (unpack('<L', self.f.read(4))[0] - self.indexBaseOffset) // 7 # 索引数-1

  def Lookup(self, ip):
    '''x.Lookup(ip) -> (sip, eip, country, area) 查找 ip 所对应的位置.

    ip, sip, eip 是点分十进制记录的 ip 字符串.
    sip, eip 分别是 ip 所在 ip 段的起始 ip 与结束 ip.
    '''
    return self.nLookup(_ip2ulong(ip))

  def nLookup(self, ip):
    '''x.nLookup(ip) -> (sip, eip, country, area) 查找 ip 所对应的位置.

    ip 是 unsigned long 型 ip 地址.
    其它同 x.Lookup(ip).
    '''
    si = 0
    ei = self.Count
    if ip < self._readIndex(si)[0]:
      raise LookupError('IP NOT Found.')
    elif ip >= self._readIndex(ei)[0]:
      si = ei
    else: # keep si <= ip < ei
      while (si + 1) < ei:
        mi = (si + ei) // 2
        if self._readIndex(mi)[0] <= ip:
          si = mi
        else:
          ei = mi
    ipinfo = self[si]
    if ip > ipinfo[1]:
      raise LookupError('IP NOT Found.')
    else:
      return ipinfo

  def __str__(self):
    tmp = []
    tmp.append('RecCount:')
    tmp.append(str(len(self)))
    tmp.append('\nVersion:')
    tmp.extend(self[self.Count].normalize()[2:])
    return ''.join(tmp)

  def __len__(self):
    '''len(x)
    '''
    return self.Count + 1

  def __getitem__(self, key):
    '''x[key]

    若 key 为整数, 则返回第key条记录(从0算起, 注意与 x.nLookup(ip) 不一样).
    若 key 为点分十进制的 ip 描述串, 同 x.Lookup(key).
    '''
    if isinstance(key, int):
      if key >=0 and key <= self.Count:
        index = self._readIndex(key)
        sip = index[0]
        self.f.seek(index[1])
        eip = unpack('<L', self.f.read(4))[0]
        country, area = self._readRec()
        if area == ' CZ88.NET':
          area = ''
        return ipInfo(sip, eip, country, area)
      else:
        raise KeyError('INDEX OUT OF RANGE.')
    elif isinstance(key, str):
      return self.Lookup(key).normalize()
    else:
      raise TypeError('WRONG KEY TYPE.')

  def _read3ByteOffset(self):
    '''_read3ByteOffset() -> unsigned long 从文件 f 读入长度为3字节的偏移.
    '''
    return unpack('<L', self.f.read(3) + b'\x00')[0]

  def _readCStr(self):
    if self.f.tell() == 0:
      return 'Unknown'

    return self._read_cstring().decode(self.charset, errors='replace')

  def _read_cstring(self):
    tmp = []
    ch = self.f.read(1)
    while ch != b'\x00':
      tmp.append(ch)
      ch = self.f.read(1)
    return b''.join(tmp)

  def _readIndex(self, n):
    '''x._readIndex(n) -> (ip ,offset) 读取第n条索引.
    '''
    self.f.seek(self.indexBaseOffset + 7 * n)
    return unpack('<LL', self.f.read(7) + b'\x00')

  def _readRec(self, onlyOne=False):
    '''x._readRec() -> (country, area) 读取记录的信息.
    '''
    mode = unpack('B', self.f.read(1))[0]
    if mode == 0x01:
      rp = self._read3ByteOffset()
      bp = self.f.tell()
      self.f.seek(rp)
      result = self._readRec(onlyOne)
      self.f.seek(bp)
    elif mode == 0x02:
      rp = self._read3ByteOffset()
      bp = self.f.tell()
      self.f.seek(rp)
      result = self._readRec(True)
      self.f.seek(bp)
      if not onlyOne:
        result.append(self._readRec(True)[0])
    else: # string
      self.f.seek(-1,1)
      result = [self._readCStr()]
      if not onlyOne:
        result.append(self._readRec(True)[0])

    return result

class MQQWry(QQWry):
  '''
  将数据库放到内存
  查询速度大约快两倍.

  In [6]: %timeit t(QQWry())
  100 loops, best of 3: 4.09 ms per loop

  In [7]: %timeit t(MQQWry())
  100 loops, best of 3: 2.22 ms per loop
  '''
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.f = mmap.mmap(self.f.fileno(), 0, access = 1)

  def _read_cstring(self):
    start = self.f.tell()
    end = self.f.find(b'\x00')
    if end < 0:
      raise Exception('fail to read C string')
    self.f.seek(end + 1)
    return self.f[start:end]

if __name__ == '__main__':
  Q = QQWry()
  if len(sys.argv) == 1:
    print(Q)
  elif len(sys.argv) == 2:
    if sys.argv[1] == '-': #参数只有一个“-”时，从标准输入读取IP
      print(''.join(Q[input()][2:]))
    elif sys.argv[1] in ('all', '-a', '-all'): #遍历示例代码
      try:
        for i in Q:
          print(i.normalize())
      except IOError:
        pass
    else: #参数只有一个IP时，只输出简要的信息
      print(''.join(Q[sys.argv[1]][2:]))
  else:
    for i in sys.argv[1:]:
      print(Q[i])

########NEW FILE########
__FILENAME__ = rcfile
'''
跟踪需要备份的配置文件，以 $HOME 为基准目录
'''

import os
import sys

from lilypath import path
from yamlserializer import YAMLData
from termcolor import colored as c
from myutils import getchar
import locale
locale.setlocale(locale.LC_ALL, '')

Ignore = 'ignore'
Normal = 'normal'
Secret = 'secret'
Handled = 'handled'

def cprint(text, color=None, on_color=None, attrs=None, **kwargs):
  print((c(text, color, on_color, attrs)), **kwargs)

class rcfile(YAMLData):
  dirprompt = '%s 是目录。%s' % (c('%s', 'green', attrs=['bold']), c('加入/忽略/已处理/进入/列出文件/tree/Vim/跳过？(y/Y/n/h/e/l/t/v/s) ', 'blue'))
  fileprompt = '%s %s' % (c('%s', 'green', attrs=['bold']), c('加入/忽略/已处理/Vim/跳过？(y/Y/n/h/v/s) ', 'blue'))

  def __init__(self, conffile, readonly=False):
    super().__init__(conffile, readonly=readonly, default={})

  def filelist(self, include=Normal):
    filelist = []

    def parsedir(d, p):
      for k, v in d.items():
        pp = p + k
        if not pp.exists():
          if v != Ignore:
            print('WARNING: %s not found' % pp, file=sys.stderr)
          continue
        if isinstance(v, dict):
          parsedir(v, pp)
        else:
          if v == include:
            filelist.append(pp.value)

    parsedir(self.data, path('~').expanduser())

    return filelist

  def update(self):
    '''交互式更新未纳入管理的文件'''
    startdir = path('~').expanduser()
    oldpwd = os.getcwd()
    if self.data is None:
      self.data = {}
    try:
      self._update(startdir, self.data)
    except KeyboardInterrupt:
      print('已中止。')
    finally:
      os.chdir(oldpwd)

  def _update(self, startdir, data):
    '''implement of self.update, should only be called by it'''
    for f in startdir.list():
      key = f.basename
      if key.endswith('~'):
        continue
      ans = ''
      if isinstance(data.get(key), str):
        continue
      elif isinstance(data.get(key), dict) and data[key]:
        try:
          self._update(f, data[key])
        except OSError as e:
          print(f.value, end=': ')
          cprint(e.strerror, 'red')
        continue
      if f.isdir():
        while not ans:
          ans = getchar(self.dirprompt % f.value)
          if ans == 'y':
            data[key] = Normal
          elif ans == 'Y':
            data[key] = Secret
          elif ans == 'n':
            data[key] = Ignore
          elif ans == 'h':
            data[key] = Handled
          elif ans == 'e':
            data[key] = {}
            try:
              self._update(f, data[key])
            except OSError as e:
              cprint(e.strerror, 'red')
              ans = ''
              continue
          elif ans == 'l':
            try:
              os.chdir(f.value)
            except OSError as e:
              cprint(e.strerror, 'red')
              ans = ''
              continue
            os.system('ls --color=auto')
            ans = ''
          elif ans == 't':
            try:
              os.chdir(f.value)
            except OSError as e:
              cprint(e.strerror, 'red')
              ans = ''
              continue
            os.system('tree -C')
            ans = ''
          elif ans == 'v':
            try:
              os.chdir(f.value)
            except OSError as e:
              cprint(e.strerror, 'red')
              ans = ''
              continue
            os.system("vim .")
            ans = ''
          elif ans == 's':
            continue
          else:
            cprint('无效的选择。', 'red')
            ans = ''
      else:
        while not ans:
          ans = getchar(self.fileprompt % f.value)
          if ans == 'y':
            data[key] = Normal
          elif ans == 'Y':
            data[key] = Secret
          elif ans == 'n':
            data[key] = Ignore
          elif ans == 'h':
            data[key] = Handled
          elif ans == 'v':
            os.system("vim '%s'" % f.value)
            ans = ''
          elif ans == 's':
            continue
          else:
            cprint('无效的选择。', 'red')
            ans = ''


########NEW FILE########
__FILENAME__ = requestsutils
import os
from http.cookiejar import MozillaCookieJar
from urllib.parse import urljoin

import requests

CHUNK_SIZE = 40960

def download_into(session, url, file, process_func=None):
  r = session.get(url, stream=True)
  length = int(r.headers.get('Content-Length') or 0)
  received = 0
  for chunk in r.iter_content(CHUNK_SIZE):
    received += len(chunk)
    file.write(chunk)
    if process_func:
      process_func(received, length)
  if not length and process_func:
    process_func(received, received)

def download_into_with_progressbar(url, dest):
  import time
  from functools import partial
  from termutils import download_process, get_terminal_size

  w = get_terminal_size()[1]
  with open(dest, 'wb') as f:
    download_into(requests, url, f, partial(
      download_process, dest, time.time(), width=w))

class RequestsBase:
  _session = None
  userAgent = None
  lasturl = None
  auto_referer = False

  @property
  def session(self):
    if not self._session:
      s = requests.Session()
      if self.userAgent:
        s.headers['User-Agent'] = self.userAgent
      self._session = s
    return self._session

  def __init__(self, *, baseurl=None, cookiefile=None, session=None):
    self.baseurl = baseurl
    self._session = session

    s = self.session
    if cookiefile:
      s.cookies = MozillaCookieJar(cookiefile)
      if os.path.exists(cookiefile):
        s.cookies.load()

    self._has_cookiefile = bool(cookiefile)

  def __del__(self):
    self.session.cookies.save()

  def request(self, url, method=None, *args, **kwargs):
    if self.baseurl:
      url = urljoin(self.baseurl, url)

    if self.auto_referer and self.lasturl:
      h = kwargs.get('headers', None)
      if not h:
        h = kwargs['headers'] = {}
      h['Referer'] = self.lasturl

    if method is None:
      if 'data' in kwargs or 'files' in kwargs:
        method = 'post'
      else:
        method = 'get'

    self.lasturl = url
    return self.session.request(method, url, *args, **kwargs)

if __name__ == '__main__':
  from sys import argv, exit

  if len(argv) != 3:
    exit('URL and output file not given.')

  try:
    download_into_with_progressbar(argv[1], argv[2])
  except KeyboardInterrupt:
    exit(2)

########NEW FILE########
__FILENAME__ = serializer
import os
import abc

import pickle

class Serializer(metaclass=abc.ABCMeta):
  def __init__(self, fname, readonly=False, default=None):
    '''
    读取文件fname。readonly指定析构时不回存数据
    如果数据已加锁，将会抛出SerializerError异常
    default 指出如果文件不存在或为空时的数据

    注意：
      要正确地写回数据，需要保证此对象在需要写回时依旧存在，或者使用with语句
      将自身存入其data属性中不可行，原因未知
    '''
    self.fname = os.path.abspath(fname)
    if readonly:
      self.lock = None
    else:
      dir, file = os.path.split(self.fname)
      self.lock = os.path.join(dir, '.%s.lock' % file)
      for i in (1,):
        # 处理文件锁
        if os.path.exists(self.lock):
          try:
            pid = int(open(self.lock).read())
          except ValueError:
            break

          try:
            os.kill(pid, 0)
          except OSError:
            break
          else:
            self.lock = None
            raise SerializerError('数据已加锁')
        open(self.lock, 'w').write(str(os.getpid()))

    try:
      self.load()
    except EOFError:
      self.data = default
    except IOError as e:
      if e.errno == 2 and not readonly: #文件不存在
        self.data = default
      else:
        raise

  def __del__(self):
    '''如果需要，删除 lock，保存文件'''
    if self.lock:
      self.save()
      os.unlink(self.lock)

  def __enter__(self):
    return self.data

  def __exit__(self, exc_type, exc_value, traceback):
    pass

  @abc.abstractmethod
  def load(self):
    pass

  @abc.abstractmethod
  def save(self):
    pass

class PickledData(Serializer):
  def save(self):
    pickle.dump(self.data, open(self.fname, 'wb'))

  def load(self):
    self.data = pickle.load(open(self.fname, 'rb'))

class SerializerError(Exception): pass

if __name__ == '__main__':
  # For testing purpose
  import tempfile
  f = tempfile.mkstemp()[1]
  testData = {'sky': 1000, 'kernel': -1000}
  try:
    with PickledData(f, default=testData) as p:
      print(p)
      p['space'] = 10000
      print(p)
  finally:
    os.unlink(f)

########NEW FILE########
__FILENAME__ = simplelex
# modified version, originally from 风间星魂 <fengjianxinghun AT gmail>
# BSD Lisence

import re
from collections import UserString

_RE_Pattern = re.compile('').__class__

class Token:
  '''useful attributes: pattern, idtype'''
  def __init__(self, pat, idtype=None, flags=0):
    self.pattern = pat if isinstance(pat, _RE_Pattern) else re.compile(pat, flags)
    self.idtype = idtype

  def __repr__(self):
    return '<%s: pat=%r, idtype=%r>' % (
      self.__class__.__name__,
      self.pattern.pattern, self.idtype)

class TokenResult(UserString):
  '''useful attributes: match, token, idtype'''
  def __init__(self, string, match, token):
    self.data = string
    self.token = token
    self.match = match
    self.idtype = token.idtype

class Lex:
  '''first matching token is taken'''
  def __init__(self, tokens=()):
    self.tokens = tokens

  def parse(self, string):
    ret = []
    while len(string) > 0:
      for p in self.tokens:
        m = p.pattern.match(string)
        if m is not None:
          ret.append(TokenResult(m.group(), match=m, token=p))
          string = string[m.end():]
          break
      else:
        break
    return ret, string

def main():
  s = 'Re: [Vim-cn] Re: [Vim-cn:7166] Re: 回复：[OT] This is the subject.'
  reply = Token(r'R[Ee]:\s?|[回答]复[：:]\s?', 're')
  ottag = Token(r'\[OT\]\s?', 'ot', flags=re.I)
  tag = Token(r'\[([\w._-]+)[^]]*\]\s?', 'tag')

  lex = Lex((reply, ottag, tag))
  tokens, left = lex.parse(s)
  print('tokens:', tokens)
  print('left:', left)

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = stats
'''Tools used to calculate and show statistics'''

import math

class Stat:
  '''A class that accepts numbers and provides stats info.

  Available properties are:
  - n: number of numbers that have been added
  - sum: sum
  - avg: average or raise ZeroDivisionError if nothing has been added yet
  - min: mimimum or None if nothing has been added yet
  - max: maximum or None if nothing has been added yet
  - mdev: standard deviation or raise ZeroDivisionError if nothing has been added yet
  - sum2: square sum
  '''
  n = 0
  sum = 0
  sum2 = 0
  min = max = None

  @property
  def avg(self):
    '''average or raise ZeroDivisionError if nothing has been added yet'''
    return self.sum / self.n

  @property
  def mdev(self):
    '''standard deviation or raise ZeroDivisionError if nothing has been added yet'''
    return math.sqrt(self.sum2 / self.n - self.avg ** 2)

  def add(self, x):
    '''add a number to stats'''
    self.n += 1
    self.sum += x
    self.sum2 += x ** 2
    if self.min is None:
      self.min = self.max = x
    else:
      if x < self.min:
        self.min = x
      elif x > self.max:
        self.max = x

  def __str__(self):
    try:
      avg = self.avg
      mdev = self.mdev
      min = self.min
      max = self.max
    except ZeroDivisionError:
      avg = mdev = 0
      min = max = 0
    return 'min/avg/max/mdev = %.3f/%.3f/%.3f/%.3f' % (min, avg, max, mdev)

  def __repr__(self):
    return '<%s.%s: %s>' % (
      self.__class__.__module__,
      self.__class__.__name__,
      self.__str__(),
    )

########NEW FILE########
__FILENAME__ = subprocessio
'''利用 poll() 与子进程交互'''

import subprocess
import select
import errno
import os

PIPE = subprocess.PIPE

class Subprocess(subprocess.Popen):
  '''与子进程交互式通信

  decode 默认为 True，即自动解码。如果调用 input() 时给出的是
  bytes，则此值自动置为 False。
  bytesAtatime 是每次读取输出的大小，默认为 1024

  polls[fd] 是 select.poll 对象
  '''
  decode = True
  bytesAtatime = 1024

  def input(self, msg):
    '''将 msg 送到子进程的 stdin

    如果写操作将阻塞，抛出 IOError，errno 为 EAGAIN（EWOULDBLOCK）
    如果 stdin 未指定为 PIPE，抛出 AttributeError
    '''
    if self.stdin is None:
      raise AttributeError('stdin 不是 pipe')

    if not hasattr(self, 'polls'):
      self.polls = {}
    fd = self.stdin.fileno()
    if fd not in self.polls:
      self.polls[fd] = select.poll()
      self.polls[fd].register(fd, select.POLLOUT)

    r = self.polls[fd].poll(5)
    if not r:
      raise IOError(errno.EWOULDBLOCK, 'writing would block')

    if isinstance(msg, str):
      msg = msg.encode()
      self.decode = True
    else:
      self.decode = False

    self.stdin.write(msg)
    self.stdin.flush()

  def poll(self, fd, timeout):
    '''从文件描述符 fd 中读取尽可能多的字符，返回类型由 decode 属性决定'''
    ret = b''

    if not hasattr(self, 'polls'):
      self.polls = {}
    if fd not in self.polls:
      self.polls[fd] = select.poll()
      self.polls[fd].register(fd, select.POLLIN)

    fd = self.polls[fd].poll(timeout)
    while fd:
      r = os.read(fd[0][0], self.bytesAtatime)
      ret += r
      if len(r) < self.bytesAtatime:
        break

    if self.decode:
      return ret.decode()
    else:
      return ret

  def output(self, timeout=0.05):
    '''如果指定了 stdout=PIPE，则返回 stdout 输出，否则抛出 AttributeError 异常
    timeout 单位为秒'''
    if isinstance(timeout, int):
      timeout *= 1000
    if self.stdout is not None:
      return self.poll(self.stdout.fileno(), timeout=timeout)
    else:
      raise AttributeError('stdout 不是 pipe')

  def error(self, timeout=0.05):
    '''如果指定了 stderr=PIPE，则返回 stderr 输出，否则抛出 AttributeError 异常'''
    if self.stderr is not None:
      return self.poll(self.stderr.fileno(), timeout=timeout)
    else:
      raise AttributeError('stderr 不是 pipe')

########NEW FILE########
__FILENAME__ = system
'''
系统工具，大多是调用外部程序
'''

import subprocess

def getCPUTemp():
  status, output = subprocess.getstatusoutput('sensors')
  if status != 0:
    raise SubprocessError("failed to execute `sensors'")
  output = output.split('\n')
  for l in output:
    if l.startswith('CPU Temperature:'):
      end = l.find('°')
      return float(l[16:end])
  raise SubprocessError('CPU Temperature not available')

def setMaxCPUFreq(freq):
  cmd = ['cpufreq-set', '--max', str(freq)]
  retcode = subprocess.call(cmd)
  if retcode != 0:
    raise SubprocessError()

class SubprocessError(SystemError): pass

########NEW FILE########
__FILENAME__ = termutils
'''Utilities for CLI programming'''

import os
import sys
import time
from unicodedata import east_asian_width

from myutils import filesize, humantime

def foreach(items, callable, *, process=True, timer=True):
  '''call callable for each item and optionally show a progressbar'''
  if process and timer:
    start_t = time.time()
  n = len(items)

  for i, l in enumerate(items):
    info = callable(i, l)
    if process:
      args = [i+1, n, (i+1)/n*100]
      if info:
        fmt = '%d/%d, %d%% complete [%s]'
        args.append(info)
      else:
        fmt = '%d/%d, %d%% complete...'
      if timer:
        used = time.time() - start_t
        eta = used / (i+1) * (n-i+1)
        fmt = '[ETA: %d Elapsed: %d] ' + fmt
        args = [eta, used] + args

      s = fmt % tuple(args)
      s = '\r' + s + '\x1b[K'
      sys.stderr.write(s)

def download_process(name, startat, got, total, width=80):
  '''Progressbar: [xx%] FileName: yKiB of zMiB, Ts left, sKiB/s'''
  elapsed = time.time() - startat
  speed = got / elapsed
  if got == total:
    # complete
    s1 = 'DONE! '
    fmt2 = ': %s total, %s elapsed, %s/s'
    s2 = fmt2 % (filesize(got), humantime(elapsed), filesize(speed))
  else:
    fmt1 = '[%2d%%] '
    p = got * 100 // total

    fmt2 = ': %s'
    size1 = filesize(got)
    args2 = [size1]
    if total > 0:
      fmt2 += ' of %s'
      args2.append(filesize(total))

      fmt2 += ', %s left, %s/s'
      left = (total - got) / speed
      args2.append(humantime(left))
      args2.append(filesize(speed))

    s1 = fmt1 % p
    s2 = fmt2 % tuple(args2)

  avail = width - len(s1) - len(s2) - 1
  if avail < 0:
    # Sadly, we have too narrow a termial. Let's output something at least
    avail = 2

  name2 = ''
  for ch in name:
    w = east_asian_width(ch) in 'WF' and 2 or 1
    if avail < w:
      break
    name2 += ch
    avail -= w

  sys.stdout.write('\r' + s1 + name2 + s2 + '\x1b[K')
  if got == total:
    sys.stdout.write('\n')
  else:
    sys.stdout.flush()

def get_terminal_size(fd=1):
  """
  Returns height and width of current terminal. First tries to get
  size via termios.TIOCGWINSZ, then from environment. Defaults to 25
  lines x 80 columns if both methods fail.

  :param fd: file descriptor (default: 1=stdout)

  from: http://blog.taz.net.au/2012/04/09/getting-the-terminal-size-in-python/
  """
  try:
    import fcntl, termios, struct
    hw = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
  except Exception:
    try:
      hw = (os.environ['LINES'], os.environ['COLUMNS'])
    except Exception:
      hw = (25, 80)

  return hw

########NEW FILE########
__FILENAME__ = url
'''
一些和HTTP/HTML相关的函数/类

2010年10月22日
'''

import sys, os
from urllib.parse import urlsplit
from urllib.parse import quote as URIescape
from urllib.parse import unquote as URIunescape
from http import cookies

class URL(dict):
  '''
  URL，类似于 urllib.parse 中者，但是使用 dict 重构，允许修改数据
  '''

  def __init__(self, url):
    o = urlsplit(url)
    dict.__init__(self, {
        'scheme':   o.scheme,
        'netloc':   o.netloc,
        'path':     o.path,
        'query':    o.query,
        'fragment': o.fragment,
        'username': o.username,
        'password': o.password,
        'hostname': o.hostname,
        'port':     o.port,
        })

  def geturl(self):
    url = '//' + self['netloc']
    if self['port']:
      url = url + ':' + self['port']
    if self['scheme']:
      url = self['scheme'] + ':' + url
    url += self.getpath()
    return url

  def getpath(self):
    '''返回 URL 中域名之后的部分'''
    url = self['path']
    if self['query']:
      url = url + '?' + self['query']
    if self['fragment']:
      url = url + '#' + self['fragment']
    return url

  def __setattr__(self, name, value):
    dict.__setitem__(self, name, value)

  def __getattr__(self, name):
    return dict.__getitem__(self, name)

  def __delattr__(self, name):
    dict.__delitem__(self, name)

class Cookie(cookies.SimpleCookie):
  def __init__(self, file=None):
    self.data = {}
    if file:
      self.loadFromFile(file)
      self.file = file

  def loadFromFile(self, file):
    '''从文件载入。文件中每行一条 cookie 信息'''
    try:
      l = open(file).readlines()
      l = [i[i.find(' ')+1:].strip() for i in l]
      self.add(l)
    except IOError as e:
      if e.errno == 2:
        #文件尚未建立
        pass
      else:
        raise

  def add(self, data):
    '''加入或更新一条 cookie 信息，其格式为 name=value'''
    if isinstance(data, (list, tuple)):
      for i in data:
        self.add(i)
    else:
      name, value = data.split(';')[0].split('=')
      self[name] = value

  def addFromResponse(self, response):
    '''从 Response 对象加入/更新 Cookie'''
    self.add([i[1] for i in response.info().items() if i[0] == 'Set-Cookie'])

  def sendFormat(self):
    '''发送格式：key=value; key=value'''
    ret = ''
    for i in self.keys():
      ret += i+'='+self[i].value+'; '
    return ret[:-2]

  def __del__(self):
    '''自动保存'''
    if self.file:
      open(self.file, 'w').write(str(self))
      os.chmod(self.file, 0o600)

  def __bool__(self):
    return bool(self.data)

class PostData:
  def __init__(self, data=None):
    '''data 可为 dict, str, bytes 或 None，最终得到的为 bytes'''
    self.data = b''
    if isinstance(data, dict):
      for k, v in data.items():
        self.add(k, v)
    elif isinstance(data, bytes):
      self.data = data
    elif isinstance(data, str):
      self.data = URIescape(data).encode('utf-8')
    elif data is None:
      pass
    else:
      raise TypeError('data 类型（%s）不正确' % data.__class__.__name__)

  def add(self, key, value):
    '''添加键值对，key 和 value 要求为 str'''
    key = key.encode('utf-8')
    value = URIescape(value).encode('utf-8')
    self.data += b'&'+key+b'='+value if self.data else key+b'='+value

  def __bool__(self):
    return bool(self.data)

def encode_multipart_formdata(fields, files, boundary=None):
  """
  fields is a sequence of (name, value) elements for regular form fields.
  files is a sequence of (name, filename, value) elements for data to be
    uploaded as files
  All items can be either str or bytes

  Return (content_type, body) ready for httplib.HTTP instance, body will be
  bytes

  from: http://code.activestate.com/recipes/146306-http-client-to-post-using-multipartform-data/
  """
  BOUNDARY = boundary or '----------ThIs_Is_tHe_bouNdaRY_$'
  CRLF = b'\r\n'
  L = []
  for (key, value) in fields:
    L.append('--' + BOUNDARY)
    L.append('Content-Disposition: form-data; name="%s"' % key)
    L.append('')
    L.append(value)
  for (key, filename, value) in files:
    L.append('--' + BOUNDARY)
    L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
    L.append('Content-Type: %s' % get_content_type(filename))
    L.append('')
    L.append(value)
  L.append('--' + BOUNDARY + '--')
  L.append('')
  L = map(lambda x: x.encode('utf-8') if isinstance(x, str) else x, L)
  body = CRLF.join(L)
  content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
  return content_type, body

def get_content_type(filename):
  '''
  from: http://code.activestate.com/recipes/146306-http-client-to-post-using-multipartform-data/
  '''
  import mimetypes
  return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

########NEW FILE########
__FILENAME__ = utf7
# vim:fileencoding=utf-8

r"""
Imap folder names are encoded using a special version of utf-7 as defined in RFC
2060 section 5.1.3.

From: http://piao-tech.blogspot.com/2010/03/get-offlineimap-working-with-non-ascii.html

5.1.3.  Mailbox International Naming Convention

   By convention, international mailbox names are specified using a
   modified version of the UTF-7 encoding described in [UTF-7].  The
   purpose of these modifications is to correct the following problems
   with UTF-7:

    1) UTF-7 uses the "+" character for shifting; this conflicts with
     the common use of "+" in mailbox names, in particular USENET
     newsgroup names.

    2) UTF-7's encoding is BASE64 which uses the "/" character; this
     conflicts with the use of "/" as a popular hierarchy delimiter.

    3) UTF-7 prohibits the unencoded usage of "\"; this conflicts with
     the use of "\" as a popular hierarchy delimiter.

    4) UTF-7 prohibits the unencoded usage of "~"; this conflicts with
     the use of "~" in some servers as a home directory indicator.

    5) UTF-7 permits multiple alternate forms to represent the same
     string; in particular, printable US-ASCII chararacters can be
     represented in encoded form.

   In modified UTF-7, printable US-ASCII characters except for "&"
   represent themselves; that is, characters with octet values 0x20-0x25
   and 0x27-0x7e.  The character "&" (0x26) is represented by the two-
   octet sequence "&-".

   All other characters (octet values 0x00-0x1f, 0x7f-0xff, and all
   Unicode 16-bit octets) are represented in modified BASE64, with a
   further modification from [UTF-7] that "," is used instead of "/".
   Modified BASE64 MUST NOT be used to represent any printing US-ASCII
   character which can represent itself.

   "&" is used to shift to modified BASE64 and "-" to shift back to US-
   ASCII.  All names start in US-ASCII, and MUST end in US-ASCII (that
   is, a name that ends with a Unicode 16-bit octet MUST end with a "-
   ").

    For example, here is a mailbox name which mixes English, Japanese,
    and Chinese text: ~peter/mail/&ZeVnLIqe-/&U,BTFw-

"""

import binascii
import codecs

# encoding
def modified_base64(s):
  s = s.encode('utf-16be')
  return binascii.b2a_base64(s).rstrip(b'\n=').replace(b'/', b',').decode('ascii')

def doB64(_in, r):
  if _in:
    r.append('&%s-' % modified_base64(''.join(_in)))
    del _in[:]

def encoder(s):
  r = []
  _in = []
  for c in s:
    ordC = ord(c)
    if 0x20 <= ordC <= 0x25 or 0x27 <= ordC <= 0x7e:
      doB64(_in, r)
      r.append(c)
    elif c == '&':
      doB64(_in, r)
      r.append('&-')
    else:
      _in.append(c)
  doB64(_in, r)
  return (''.join(r).encode('ascii'), len(s))

# decoding
def modified_unbase64(s):
  b = binascii.a2b_base64(s.replace(b',', b'/') + b'===')
  return str(b, 'utf-16be')

def decoder(s):
  r = []
  decode = []
  for c in s:
    if c == b'&' and not decode:
      decode.append(b'&')
    elif c == b'-' and decode:
      if len(decode) == 1:
        r.append('&')
      else:
        r.append(modified_unbase64(b''.join(decode[1:])))
      decode = []
    elif decode:
      decode.append(c)
    else:
      r.append(c.decode('ascii'))
  if decode:
    r.append(modified_unbase64(b''.join(decode[1:])))
  bin_str = ''.join(r)
  return (bin_str, len(s))

class StreamReader(codecs.StreamReader):
  def decode(self, s, errors='strict'):
    return decoder(s)

class StreamWriter(codecs.StreamWriter):
  def decode(self, s, errors='strict'):
    return encoder(s)

def imap4_utf_7(name):
  if name == 'imap4-utf-7':
    return (encoder, decoder, StreamReader, StreamWriter)

codecs.register(imap4_utf_7)

########NEW FILE########
__FILENAME__ = vimutils
try:
  import vim
except ImportError:
  raise RuntimeError('This module should only use inside Vim')

def input(prompt='', style=None):
  if style is not None:
    vim.command('echohl %s' % style)
  ans = vim.eval("input('%s')" % prompt.replace("'", "''"))
  if style is not None:
    vim.command('echohl None')
  return ans

def print(style, text):
  #XXX: deprecated; moved to vimrc.py
  vim.command("echohl %s | echo '%s' | echohl None" % (style, text.replace("'", "''")))

########NEW FILE########
__FILENAME__ = xauto
import os
from time import sleep

from myopencv import Image
import X
import gdkutils

class XAuto:
  _screensize = None

  def __init__(self, tmp_img='/dev/shm/tmp%d.png' % os.getpid(),
    default_threshold=0.7, default_rect=None):
    self.d = X.Display()
    self.tmp_img = tmp_img
    self.default_threshold = default_threshold
    self.default_rect = default_rect

  def find_and_click(self, *args, back=False, **kwargs):
    pos = self.find(*args, **kwargs)
    if pos:
      if back:
        self.click_and_back(pos)
      else:
        self.click(pos)
    return pos

  def find_and_moveto(self, *args, **kwargs):
    pos = self.find(*args, **kwargs)
    if pos:
      self.moveto(pos)
    return pos

  def click(self, pos=None, button=X.LEFT_BUTTON):
    d = self.d
    if pos is not None:
      d.motion(pos)
    d.button(button)
    d.flush()

  def wait(self, seconds):
    sleep(seconds)

  def click_and_back(self, pos, button=X.LEFT_BUTTON):
    d = self.d
    old_pos = d.getpos()
    d.motion(pos)
    d.button(button)
    d.motion(old_pos)
    d.flush()

  def moveto(self, pos):
    d = self.d
    d.motion(pos)
    d.flush()

  def key(self, keyname):
    d = self.d
    d.key(keyname)
    d.flush()

  def find(self, img, threshold=None, rect=None, repeat=1, interval=0.2):
    if isinstance(img, str):
      img = Image(img)
    if rect is None:
      rect = self.default_rect or (0, 0) + self.screensize
    if threshold is None:
      threshold = self.default_threshold
    tmp_img = self.tmp_img

    for _ in range(repeat):
      gdkutils.screenshot(tmp_img, rect)
      sc = Image(tmp_img)
      (x, y), similarity = sc.match(img)
      if similarity > threshold:
        x += rect[0]
        y += rect[1]
        x += img.width // 2
        y += img.height // 2
        return x, y
      sleep(interval)

    return False

  @property
  def screensize(self):
    return self._screensize or gdkutils.get_screen_size()

  def __del__(self):
    try:
      os.unlink(self.tmp_img)
    except OSError:
      pass

  def monitor_size(self, *args, **kwargs):
      return gdkutils.get_moniter_size(*args, **kwargs)


########NEW FILE########
__FILENAME__ = xdgutils
from string import Template
from collections import defaultdict

class ExecTempate(Template):
  delimiter = '%'
  idpattern = '[A-Za-z%]'
  flags = 0

def prepExec(entry):
  # http://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html#exec-variables
  exec_t = ExecTempate(entry.getExec())
  d = defaultdict(lambda: '')
  d['%'] = '%'
  d['c'] = entry.getName()
  icon = entry.getIcon()
  if icon:
    d['i'] = '--icon "%s"' % icon
  d['k'] = entry.filename
  return exec_t.substitute(d).rstrip()


########NEW FILE########
__FILENAME__ = xiami
import re

from lxml.etree import fromstring

from htmlutils import parse_document_from_requests
from musicsites import Base, SongInfo

DEFAULT_BETTER_LRC_RE = re.compile(r'\[\d+:\d+[:.](?!00)\d+\]')

class Xiami(Base):
  better_lrc_re = DEFAULT_BETTER_LRC_RE

  def search(self, q):
    url = 'http://www.xiami.com/search?key=' + q
    doc = parse_document_from_requests(url, self.session)
    rows = doc.xpath('//table[@class="track_list"]//tr')[1:]
    ret = []
    for tr in rows:
      # 没有 target 属性的是用于展开的按钮
      names = tr.xpath('td[@class="song_name"]/a[@target]')
      if len(names) == 2:
        extra = names[1].text_content()
      else:
        extra = None
      name = names[0].text_content()
      href = names[0].get('href')

      # '/text()' in XPath get '.text', not '.text_content()'
      artist = tr.xpath('td[@class="song_artist"]/a')[0].text_content().strip()
      album = tr.xpath('td[@class="song_album"]/a')[0].text_content().strip()
      album = album.lstrip('《').rstrip('》')

      sid = href.rsplit('/', 1)[-1]
      song = SongInfo(sid, name, href, (artist,), album, extra)
      ret.append(song)

    return ret

  def getLyricFor(self, sid):
    url = 'http://www.xiami.com/song/playlist/id/%s/object_name/default/object_id/0' % sid
    r = self.session.get(url)
    doc = fromstring(r.content)
    try:
      lyric_url = doc.xpath('//xspf:lyric/text()',
                            namespaces={'xspf': 'http://xspf.org/ns/0/'})[0]
    except IndexError:
      return
    # pic_url = doc.xpath('//xspf:pic/text()', namespaces={'xspf': 'http://xspf.org/ns/0/'})[0]

    r = self.session.get(lyric_url)
    return r.text

  def findBestLrc(self, q):
    results = self.search(q)
    candidate = None
    r = self.better_lrc_re

    for song in results:
      lyric = self.getLyricFor(song.sid)
      if lyric and lyric.count('[') > 5:
        if r.search(lyric):
          return lyric
        elif not candidate:
          candidate = lyric

    return candidate

########NEW FILE########
__FILENAME__ = xmlutils
'''
XML 相关的小工具函数
'''

import re
from lxml.html import parse, etree, tostring, fromstring

allen = re.compile(r'^[\x20-\x7f]+$')
en = re.compile(r'[\x20-\x7f]+')

def enText(doc):
  doc.set('lang', 'zh-CN')
  for el in doc.xpath('//p|//dt|//dd|//li|//a|//span|//em|//h2|//h3|//strong'):
    if el.getparent().tag == 'pre':
      continue
    if el.getparent().get('role') == 'pre':
      continue
    text = el.text
    if text:
      text = text.strip()
      if not allen.match(text) or el.getchildren():
        ms = list(en.finditer(text))
        for i, m in enumerate(ms):
          span = etree.Element('span')
          span.set('lang', 'en')
          span.text = m.group(0)
          el.insert(i, span)
          if i == 0:
            el.text = text[:m.start()]
          try:
            span.tail = text[m.end():ms[i+1].start()]
          except IndexError:
            span.tail = text[m.end():]
      else:
        el.set('lang', 'en')

  for el in doc.xpath('//a|//span|//em|//code|//strong'):
    if el.getparent().tag == 'pre':
      continue
    text = el.tail
    if text:
      text = text.strip()
      ms = list(en.finditer(text))
      for i, m in enumerate(ms):
        span = etree.Element('span')
        span.set('lang', 'en')
        span.text = m.group(0)
        tail = el.tail
        el.addnext(span)
        # re-insert mispositioned tail; the previous one will be overwritten
        el.tail = tail
        if i == 0:
          el.tail = text[:m.start()]
        el = span
        try:
          el.tail = text[m.end():ms[i+1].start()]
        except IndexError:
          el.tail = text[m.end():]

def enText_convert(oldfile, newfile):
  doc = fromstring(open(oldfile).read())
  enText(doc)
  with open(newfile, 'w') as f:
    f.write(doc.getroottree().docinfo.doctype + '\n')
    f.write(tostring(doc, encoding=str, method='xml'))

if __name__ == '__main__':
  import sys
  if len(sys.argv) == 3:
    enText_convert(*sys.argv[1:])
  else:
    print('parameters: old_file new_file', file=sys.stderr)

########NEW FILE########
__FILENAME__ = xmppbot
import sys
import logging
from xml.etree import ElementTree as ET
from collections import defaultdict

from pyxmpp2.jid import JID
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence
from pyxmpp2.client import Client
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT, NO_CHANGE
from pyxmpp2.streamevents import AuthorizedEvent, DisconnectedEvent
from pyxmpp2.interfaces import XMPPFeatureHandler
from pyxmpp2.interfaces import presence_stanza_handler, message_stanza_handler
from pyxmpp2.ext.version import VersionProvider
from pyxmpp2.iq import Iq

class AutoAcceptMixin:
  @presence_stanza_handler("subscribe")
  def handle_presence_subscribe(self, stanza):
    logging.info("{0} requested presence subscription"
                          .format(stanza.from_jid))
    presence = Presence(to_jid = stanza.from_jid.bare(),
                          stanza_type = "subscribe")
    return [stanza.make_accept_response(), presence]

  @presence_stanza_handler("subscribed")
  def handle_presence_subscribed(self, stanza):
    logging.info("{0!r} accepted our subscription request"
                          .format(stanza.from_jid))
    return True

  @presence_stanza_handler("unsubscribe")
  def handle_presence_unsubscribe(self, stanza):
    logging.info("{0} canceled presence subscription"
                          .format(stanza.from_jid))
    presence = Presence(to_jid = stanza.from_jid.bare(),
                          stanza_type = "unsubscribe")
    return [stanza.make_accept_response(), presence]

  @presence_stanza_handler("unsubscribed")
  def handle_presence_unsubscribed(self, stanza):
    logging.info("{0!r} acknowledged our subscrption cancelation"
                          .format(stanza.from_jid))
    return True

class TracePresenceMixin:
  presence = None
  @presence_stanza_handler()
  def handle_presence_available(self, stanza):
    if stanza.stanza_type not in ('available', None):
      return False

    jid = stanza.from_jid
    plainjid = str(jid.bare())
    logging.info('%s[%s]', jid, stanza.show or 'available')

    if self.presence is None:
      self.presence = defaultdict(dict)
    self.presence[plainjid][jid.resource] = {
      'show': stanza.show,
      'status': stanza.status,
      'priority': stanza.priority,
    }

    return True

  @presence_stanza_handler('unavailable')
  def handle_presence_unavailable(self, stanza):
    jid = stanza.from_jid
    plainjid = str(jid.bare())
    if self.presence is None:
      self.presence = defaultdict(dict)
    if plainjid in self.presence and plainjid != str(self.jid):
      try:
        del self.presence[plainjid][jid.resource]
      except KeyError:
        pass
      if self.presence[plainjid]:
        logging.info('%s[unavailable] (partly)', jid)
      else:
        del self.presence[plainjid]
        logging.info('%s[unavailable] (totally)', jid)
    return True

class XMPPBot(EventHandler, XMPPFeatureHandler):
  autoReconnect = False

  def __init__(self, my_jid, settings, autoReconnect=None, main_loop=None):
    self.jid = my_jid
    self.settings = settings
    if autoReconnect is not None:
      self.autoReconnect = autoReconnect
    self.do_quit = False
    self.main_loop = main_loop

  def newclient(self):
    version_provider = VersionProvider(self.settings)
    self.client = Client(
      self.jid, [self, version_provider], self.settings,
      main_loop=self.main_loop,
    )

  def start(self):
    while not self.do_quit:
      logging.info('XMPP connecting...')
      self.connect()
      self.run()
      if not self.autoReconnect:
        self.do_quit = True

  def connect(self):
    self.newclient()
    self.client.connect()

  def run(self):
    self.client.run()

  def disconnect(self):
    self.do_quit = True
    self.client.disconnect()
    self.client.run(timeout=2)

  @property
  def roster(self):
    return self.client.roster

  @message_stanza_handler()
  def handle_message(self, stanza):
    if stanza.stanza_type and stanza.stanza_type.endswith('chat') and stanza.body:
      logging.info("%s said: %s", stanza.from_jid, stanza.body)
      self.last_chat_message = stanza
    else:
      logging.info("%s message: %s", stanza.from_jid, stanza.serialize())
    return True

  def send_message(self, receiver, msg):
    m = Message(
      stanza_type = 'chat',
      from_jid = self.client.jid,
      to_jid = receiver,
      body = msg,
    )
    self.send(m)

  def send(self, stanza):
    self.client.stream.send(stanza)

  def delayed_call(self, seconds, func, *args, **kwargs):
    self.client.main_loop.delayed_call(seconds, partial(func, *args, **kwargs))

  def get_vcard(self, jid, callback):
    '''callback is used as both result handler and error handler'''
    q = Iq(
      to_jid = jid.bare(),
      stanza_type = 'get'
    )
    vc = ET.Element("{vcard-temp}vCard")
    q.add_payload(vc)
    self.stanza_processor.set_response_handlers(q, callback, callback)
    self.send(q)

  def update_roster(self, jid, name=NO_CHANGE, groups=NO_CHANGE):
    self.client.roster_client.update_item(jid, name, groups)

  @presence_stanza_handler()
  def handle_presence_available(self, stanza):
    logging.info('%s[%s]', stanza.from_jid, stanza.show or 'available')
    return True

  @event_handler(DisconnectedEvent)
  def handle_disconnected(self, event):
    if self.do_quit:
      return QUIT
    else:
      logging.warn('XMPP disconnected. Reconnecting...')
      # We can't restart here because the stack will overflow
      return True

  @event_handler()
  def handle_all(self, event):
    """Log all events."""
    logging.info("-- {0}".format(event))

class AutoAcceptBot(AutoAcceptMixin, XMPPBot): pass

def main():
  import os
  from getpass import getpass
  import argparse
  from myutils import enable_pretty_logging
  from cli import repl

  """Parse the command-line arguments and run the bot."""
  parser = argparse.ArgumentParser(description = 'XMPP dev bot',
                  parents = [XMPPSettings.get_arg_parser()])
  parser.add_argument('jid', metavar = 'JID',
                    help = 'The bot JID')
  parser.add_argument('--debug',
            action = 'store_const', dest = 'log_level',
            const = logging.DEBUG, default = logging.INFO,
            help = 'Print debug messages')
  parser.add_argument('--quiet', const = logging.ERROR,
            action = 'store_const', dest = 'log_level',
            help = 'Print only error messages')
  parser.add_argument('--trace', action = 'store_true',
            help = 'Print XML data sent and received')

  args = parser.parse_args()
  settings = XMPPSettings({
    "software_name": "pyxmpp2 Bot"
  })
  settings.load_arguments(args)
  if args.jid.endswith('@gmail.com'):
    settings['starttls'] = True
    settings['tls_verify_peer'] = False

  if settings.get("password") is None:
    password = getpass("{0!r} password: ".format(args.jid))
    settings["password"] = password

  if args.trace:
    logging.info('enabling trace')
    for logger in ("pyxmpp2.IN", "pyxmpp2.OUT"):
      logger = logging.getLogger(logger)
      logger.setLevel(logging.DEBUG)
  enable_pretty_logging(level=args.log_level)

  bot = AutoAcceptBot(JID(args.jid), settings)

  class Q:
    def __call__(self):
      sys.exit()
    __repr__ = __call__

  q = Q()
  self = bot

  try:
    bot.connect()
    while True:
      try:
        bot.run()
      except KeyboardInterrupt:
        v = vars()
        v.update(globals())
        repl(v, os.path.expanduser('~/.xmppbot_history'))
  except SystemExit:
    bot.disconnect()
  except:
    bot.disconnect()
    import traceback
    traceback.print_exc()

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = xmpp_receipt
#
# (C) Copyright 2014 lilydjwg <lilydjwg@gmail.com>
#

"""Message Delivery Receipts

Normative reference:
  - `XEP-0184 <http://xmpp.org/extensions/xep-0184.html>`__
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import platform
import logging

from pyxmpp2.etree import ElementTree as ET

from pyxmpp2.message import Message
from pyxmpp2.interfaces import XMPPFeatureHandler, feature_uri
from pyxmpp2.interfaces import message_stanza_handler

logger = logging.getLogger(__name__)

NS = "urn:xmpp:receipts"

@feature_uri(NS)
class ReceiptSender(XMPPFeatureHandler):
    """Provides the Message Delivery Receipts (XEP-0184) response service."""
    stream = None

    @message_stanza_handler()
    def handle_receipt_request(self, stanza):
        if not self.stream:
            return

        mid = stanza.stanza_id
        if mid:
            x = stanza.get_xml()
            if x.find('{%s}request' % NS) is None:
                # not requested
                return
            response = Message(to_jid = stanza.from_jid)
            payload = ET.Element("{%s}received" % NS, {'id': mid})
            response.set_payload(payload)
            self.stream.send(response)
        # keep handling it
        return False


########NEW FILE########
__FILENAME__ = yamlserializer
from serializer import Serializer, SerializerError
from yamlutils import load, dump

class YAMLData(Serializer):
  def save(self):
    dump(self.data, open(self.fname, 'w'))

  def load(self):
    self.data = load(open(self.fname, 'r'))


########NEW FILE########
__FILENAME__ = yamlutils
import yaml
try:
  from yaml import CLoader as Loader
  from yaml import CDumper as Dumper
except ImportError:
  from yaml import Loader, Dumper

def load(src):
  return yaml.load(src, Loader=Loader)

def load_all(src):
  return yaml.load_all(src, Loader=Loader)

def dump(data, stream=None):
  return yaml.dump(data, stream=stream, Dumper=Dumper,
                   allow_unicode=True, default_flow_style=False)


########NEW FILE########
__FILENAME__ = zhnum
# coding: utf-8
# author: binux(17175297.hk@gmail.com)
# https://github.com/binux/binux-tools/blob/master/python/chinese_digit.py

numdict = {'零':0, '一':1, '二':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9, '十':10, '百':100, '千':1000, '万':10000,
        '〇':0, '亿':100000000,
        '壹':1, '贰':2, '叁':3, '肆':4, '伍':5, '陆':6, '柒':7, '捌':8, '玖':9, '拾':10, '佰':100, '仟':1000, '萬':10000,
       }

def zhnum2int(a):
  count = 0
  result = 0
  tmp = 0
  Billion = 0
  while count < len(a):
    tmpChr = a[count]
    #print tmpChr
    tmpNum = numdict.get(tmpChr, None)
    #如果等于1亿
    if tmpNum == 100000000:
      result = result + tmp
      result = result * tmpNum
      #获得亿以上的数量，将其保存在中间变量Billion中并清空result
      Billion = Billion * 100000000 + result
      result = 0
      tmp = 0
    #如果等于1万
    elif tmpNum == 10000:
      result = result + tmp
      result = result * tmpNum
      tmp = 0
    #如果等于十或者百，千
    elif tmpNum >= 10:
      if tmp == 0:
        tmp = 1
      result = result + tmpNum * tmp
      tmp = 0
    #如果是个位数
    elif tmpNum is not None:
      tmp = tmp * 10 + tmpNum
    count += 1
  result = result + tmp
  result = result + Billion
  return result

if __name__ == "__main__":
  test_map = {
    '三千五百二十三': 3523,
    '七十五亿八百零七万九千二百零八': 7508079208,
    '四万三千五百二十一': 43521,
    '三千五百二十一': 3521,
    '三千五百零八': 3508,
    '三五六零': 3560,
    '一万零三十': 10030,
    '': 0,
    #1 digit 个
    '零': 0,
    '一': 1,
    '二': 2,
    '三': 3,
    '四': 4,
    '五': 5,
    '六': 6,
    '七': 7,
    '八': 8,
    '九': 9,
    #2 digits 十
    '十': 10,
    '十一': 11,
    '二十': 20,
    '二十一': 21,
    #3 digits 百
    '一百': 100,
    '一百零一': 101,
    '一百一十': 110,
    '一百二十三': 123,
    #4 digits 千
    '一千': 1000,
    '一千零一': 1001,
    '一千零一十': 1010,
    '一千一百': 1100,
    '一千零二十三': 1023,
    '一千二百零三': 1203,
    '一千二百三十': 1230,
    #5 digits 万
    '一万': 10000,
    '一万零一': 10001,
    '一万零一十': 10010,
    '一万零一百': 10100,
    '一万一千': 11000,
    '一万零一十一': 10011,
    '一万零一百零一': 10101,
    '一万一千零一': 11001,
    '一万零一百一十': 10110,
    '一万一千零一十': 11010,
    '一万一千一百': 11100,
    '一万一千一百一十': 11110,
    '一万一千一百零一': 11101,
    '一万一千零一十一': 11011,
    '一万零一百一十一': 10111,
    '一万一千一百一十一': 11111,
    #6 digits 十万
    '十万零二千三百四十五': 102345,
    '十二万三千四百五十六': 123456,
    '十万零三百五十六': 100356,
    '十万零三千六百零九': 103609,
    #7 digits 百万
    '一百二十三万四千五百六十七': 1234567,
    '一百零一万零一百零一': 1010101,
    '一百万零一': 1000001,
    #8 digits 千万
    '一千一百二十三万四千五百六十七': 11234567,
    '一千零一十一万零一百零一': 10110101,
    '一千万零一': 10000001,
    #9 digits 亿
    '一亿一千一百二十三万四千五百六十七': 111234567,
    '一亿零一百零一万零一百零一': 101010101,
    '一亿零一': 100000001,
    #10 digits 十亿
    '十一亿一千一百二十三万四千五百六十七': 1111234567,
    #11 digits 百亿
    '一百一十一亿一千一百二十三万四千五百六十七': 11111234567,
    #12 digits 千亿
    '一千一百一十一亿一千一百二十三万四千五百六十七': 111111234567,
    #13 digits 万亿
    '一万一千一百一十一亿一千一百二十三万四千五百六十七': 1111111234567,
    #14 digits 十万亿
    '十一万一千一百一十一亿一千一百二十三万四千五百六十七': 11111111234567,
    #17 digits 亿亿
    '一亿一千一百一十一万一千一百一十一亿一千一百二十三万四千五百六十七': 11111111111234567,
  }

  for each in test_map:
    assert(test_map[each] == zhnum2int(each))

########NEW FILE########
