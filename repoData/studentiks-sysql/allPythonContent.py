__FILENAME__ = ls
import io, subprocess, sqlite3, collections, datetime, re, sys, operator


def run(args, db):
 cmd = 'ls'
 table = 'ls'

 args.append('-i')
 args.append('-lU')
 args.append('-Q')
 args.extend(['--time-style', 'full-iso'])
 args.append('--indicator-style=classify')
 out_structure = """[index] permissions num [user] [group] size time_mod  filename refers_to type
                    int     text        int text   text    int  time_mod  text     text      text""".split('\n')

 class Column:
  def __init__(s, **kwargs):
   for k, v in kwargs.items():
    setattr(s, k, v)

 columns = []
 for field, type in zip(out_structure[0].split(), out_structure[1].split()):
  columns.append(Column(field=field, type=type))

 def time_mod_converter(bvalue):
  # 2013-11-24 04:05:05.498121677 +0200
  time_format = '%Y-%m-%d %H:%M:%S.%f %z'
  # only 6 digits supported by %f
  txt = re.sub(r'\.(\d{6})\d{3}\s', lambda m: '.{} '.format(m.group(1)), bvalue.decode())
  t = datetime.datetime.strptime(txt, time_format)
  return t

 sqlite3.register_converter('time_mod', time_mod_converter)

 bout = subprocess.check_output([cmd] + args)
 out_lines = bout.decode(errors='surrogate').split('\n')
 out_lines.pop(0)
 out_lines.pop()

 sql = 'CREATE TABLE {table} ({columns})'.format(table=table, columns=','.join(['{} {}'.format(col.field, col.type) for col in columns]))
 db.execute(sql)
 for line in out_lines:
  m = re.match(r'^\s*(?P<ix>\d+)\s(?P<perm>.*)\s+(?P<num>\d+)\s(?P<user>\S+)\s(?P<group>\S+)\s+(?P<size>\d+)\s(?P<mod_time>.{35})\s"(?P<filename>.*)"(?P<type>[*/=>@|]?)$', line)

  val_keys = 'ix perm num user group size mod_time filename type'.split()
  vals = list(m.groups())

  # split filename and refers_to
  ix = val_keys.index('filename')
  arr = vals[ix].split('" -> "', 1)+['']
  vals[ix] = arr[0]
  vals.insert(ix + 1, arr[1])

  assert len(vals) == len(columns), 'parsed line has {} matches instead of {}'.format(len(vals), len(columns)-1)

  q_marks = ','.join('?' * len(vals))
  db.execute('INSERT INTO {table} VALUES ({q})'.format(table=table, q=q_marks), tuple(vals))


########NEW FILE########
__FILENAME__ = lsblk
import io, subprocess, sqlite3, collections, datetime, re, sys, operator


def run(args, db):
 cmd = 'lsblk'
 table = 'lsblk'
 out_structure = \
 """KNAME       device                    text
    MAJ:MIN     device_number             text
    FSTYPE      filesystem                text
    MOUNTPOINT  mountpoint                text
    LABEL       label                     text
    UUID        uuid                      text
    MODEL       device_identifier         text
    SERIAL      disk_serial_number        text
    SIZE        size                      int
    STATE       state                     text
    OWNER       user_name                 text
    GROUP       group_name                text
    MODE        device_node_permissions   text
    TYPE        device_type               text
    TRAN        device_transport_type     text
    REV         device_revision           text
    VENDOR      device_vendor             text""".split('\n')

 class Column:
  def __init__(s, **kwargs):
   for k, v in kwargs.items():
    setattr(s, k, v)

 columns = []
 for out, field, type in map(lambda s: s.split(), out_structure):
  columns.append(Column(out=out, field=field, type=type))

 args.extend(['-o', ','.join([col.out for col in columns])])
 args.append('-b')

 bout = subprocess.check_output([cmd] + args)
 out_lines = bout.decode(errors='surrogate').split('\n')
 out_lines.pop()

 header = out_lines.pop(0)
 # finding all columns that consist of spaces:
 spaces = [ix for ix, c in enumerate(header) if c == ' ']
 for line in out_lines:
  spaces = [ix for ix in spaces if line[ix] == ' ']
 # integrating found columns as stars in header line
 header = ''.join('*' if ix in spaces and ((ix-1) not in spaces) else c for ix, c in enumerate(header))
 # appending enough spaces to header
 header += ' ' * (max(map(len, out_lines)) - len(header))
 # removing irrelevant stars
 header = re.sub('\*(\s+\*)', lambda mo: ' ' + mo.group(1), header)
 headers = header.split('*')

 assert len(headers) == len(columns), 'parsed header has {} columns instead of {}'.format(len(headers),len(columns))

 sql = 'CREATE TABLE {table} ({columns})'.format(table=table, columns=','.join(['{} {}'.format(col.field, col.type) for col in columns]))
 db.execute(sql)
 for line in out_lines:
  h_start = 0
  h_end = 0
  vals = []
  for h in headers:
   h_end += len(h)
   val = line[h_start:h_end].strip()
   vals.append(val)
   h_start = h_end + 1
   h_end = h_start
  q_marks = ','.join('?' * len(vals))
  db.execute('INSERT INTO {table} VALUES ({q})'.format(table=table, q=q_marks), tuple(vals))


########NEW FILE########
__FILENAME__ = lsof
import io, subprocess, sqlite3, collections, datetime, re, sys, operator


def run(args, db):
 cmd = 'lsof'
 table = 'lsof'

 out_structure = \
 """COMMAND   command          text
    PID       pid              int
    TID       tid              int
    USER      user             text
    FD        file_descriptor  text
    TYPE      type             text
    DEVICE    device           text
    SIZE/OFF  size             int
    NODE      node             text
    NAME      name             text""".split('\n')

 class Column:
  def __init__(s, **kwargs):
   for k, v in kwargs.items():
    setattr(s, k, v)

 columns = []
 for out, field, type in map(lambda s: s.split(), out_structure):
  columns.append(Column(out=out, field=field, type=type))

 args.append('-b')
 args.append('-w')

 bout = subprocess.check_output([cmd] + args)
 out_lines = bout.decode(errors='surrogate').split('\n')
 out_lines.pop()

 header = out_lines.pop(0)
 # finding all columns that consist of spaces:
 spaces = [ix for ix, c in enumerate(header) if c == ' ']
 for line in out_lines:
  spaces = [ix for ix in spaces if line[ix] == ' ']
 # integrating found columns as stars in header line
 header = ''.join('*' if ix in spaces and ((ix-1) not in spaces) else c for ix, c in enumerate(header))
 # appending enough spaces to header
 header += ' ' * (max(map(len, out_lines)) - len(header))
 # removing irrelevant stars
 header = re.sub('\*(\s+\*)', lambda mo: ' ' + mo.group(1), header)
 headers = header.split('*')

 # -i attribute removes TID column
 if header.find('TID') == -1:
  columns.remove(next(filter(lambda col: col.out == 'TID', columns)))

 assert len(headers) == len(columns), 'parsed header has {} columns instead of {}'.format(len(headers),len(columns))

 # print('lsblk ' + ' '.join(args))
 # print(header)
 # print('\n'.join(out_lines))

 sql = 'CREATE TABLE {table} ({columns})'.format(table=table, columns=','.join(['{} {}'.format(col.field, col.type) for col in columns]))
 db.execute(sql)
 for line in out_lines:
  h_start = 0
  h_end = 0
  vals = []
  for h in headers:
   h_end += len(h)
   val = line[h_start:h_end].strip()
   vals.append(val)
   h_start = h_end + 1
   h_end = h_start
  q_marks = ','.join('?' * len(vals))
  db.execute('INSERT INTO {table} VALUES ({q})'.format(table=table, q=q_marks), tuple(vals))


########NEW FILE########
__FILENAME__ = mount
import io, subprocess, sqlite3, collections, datetime, re, sys, operator


def run(args, db):
 cmd = 'mount'
 table = 'mount'

 out_structure = 'device mountpoint type options'.split()

 class Column:
  def __init__(s, **kwargs):
   for k, v in kwargs.items():
    setattr(s, k, v)

 columns = []
 for field in out_structure:
  columns.append(Column(field=field, type='text'))

 bout = subprocess.check_output([cmd] + args)
 out_lines = bout.decode(errors='surrogate').split('\n')
 out_lines.pop()

 sql = 'CREATE TABLE {table} ({columns})'.format(table=table, columns=','.join(['{} {}'.format(col.field, col.type) for col in columns]))
 db.execute(sql)
 for line in out_lines:
  m = re.match(r'^(.*)\son\s(.*)\stype\s(.*)\s\((.*)\)$', line)
  vals = m.groups()
  assert len(vals) == len(columns), 'parsed line has {} matches instead of {}'.format(len(vals), len(columns))

  q_marks = ','.join('?' * len(vals))
  db.execute('INSERT INTO {table} VALUES ({q})'.format(table=table, q=q_marks), tuple(vals))


########NEW FILE########
__FILENAME__ = ps
import io, subprocess, sqlite3, collections, datetime, re, sys


def run(args, db):
 cmd = 'ps'
 table = 'ps'

 out_structure = \
 """pid  tname    time      etime        %cpu      sgi_p     uname     comm    args
    10   10       20        20           10        10        100       20      100500
    pid  tty_name cpu_time  elapsed_time cpu_ratio processor user_name command command_line
    int  text     cpu_time  elapsed_time float     text      text      text    text          """.split('\n')

 ps_out        = out_structure[0].split()
 ps_sizes      = out_structure[1].split()
 ps_names      = out_structure[2].split()
 ps_types      = out_structure[3].split()

 class Column:
  def __init__(s, **kwargs):
   for k, v in kwargs.items():
    setattr(s, k, v)

 columns = [Column(out=out, size=int(size), name=name, type=type) for out, size, name, type in zip(ps_out, ps_sizes, ps_names, ps_types)]

 class elapsed_time:
   # [DD-]hh:mm:ss
  def __init__(s, text):
   s.text = text

  @staticmethod
  def adapter(s):
   digits = list(map(int, list(re.findall('\d+', s.text))))
   ss = digits.pop()
   mm = digits.pop()
   hh = digits.pop() if digits else 0
   dd = digits.pop() if digits else 0
   t = datetime.timedelta(days=dd, hours=hh, minutes=mm, seconds=ss)
   return int(t.total_seconds())

  @staticmethod
  def converter(value):
   return datetime.timedelta(seconds=int(value))

 class cpu_time(elapsed_time):
  pass

 type_map = dict(int=int, float=float, text=str, bytes=bytes)
 for c in [elapsed_time, cpu_time]:
  type_map[c.__name__] = c
  sqlite3.register_adapter(c, c.adapter)
  sqlite3.register_converter(c.__name__, c.converter)

 args.extend(['-o', ','.join(['{}:{}'.format(col.out, col.size) for col in columns])])
 bout = subprocess.check_output([cmd] + args)
 out = io.StringIO(bout.decode(errors='surrogate'))
 out.readline()

 sql = 'CREATE TABLE {table} ({columns})'.format(table=table, columns=','.join(['{} {}'.format(col.name, col.type) for col in columns]))
 db.execute(sql)

 left = 0
 header = []
 for size in ps_sizes:
  right = left + int(size) + 1
  header.append([left, right])
  left = right

 for line in out:
  vals = [line[start:end].strip() for start, end in header]
  vals = [type_map[t](v) for t, v in zip(ps_types, vals)]
  db.execute('INSERT INTO {table} VALUES ({q})'.format(table=table,q=','.join('?'*len(ps_names))), tuple(vals))
########NEW FILE########
