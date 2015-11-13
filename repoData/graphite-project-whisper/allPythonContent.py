__FILENAME__ = rrd2whisper
#!/usr/bin/env python

import os
import sys
import time
import signal
import optparse

try:
  import rrdtool
except ImportError, exc:
  raise SystemExit('[ERROR] Missing dependency: %s' % str(exc))

try:
  import whisper
except ImportError:
  raise SystemExit('[ERROR] Please make sure whisper is installed properly')

# Ignore SIGPIPE
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

aggregationMethods = whisper.aggregationMethods

# RRD doesn't have a 'sum' or 'total' type
aggregationMethods.remove('sum')

option_parser = optparse.OptionParser(usage='''%prog rrd_path''')
option_parser.add_option(
    '--xFilesFactor',
    help="The xFilesFactor to use in the output file. " +
    "Defaults to the input RRD's xFilesFactor",
    default=None,
    type='float')
option_parser.add_option(
    '--aggregationMethod',
    help="The consolidation function to fetch from on input and " +
    "aggregationMethod to set on output. One of: %s" %
    ', '.join(aggregationMethods),
    default='average',
    type='string')

(options, args) = option_parser.parse_args()

if len(args) < 1:
  option_parser.print_help()
  sys.exit(1)

rrd_path = args[0]

try:
  rrd_info = rrdtool.info(rrd_path)
except rrdtool.error, exc:
  raise SystemExit('[ERROR] %s' % str(exc))

seconds_per_pdp = rrd_info['step']

# Reconcile old vs new python-rrdtool APIs (yuck)
# leave consistent 'rras' and 'datasources' lists
if 'rra' in rrd_info:
  rras = rrd_info['rra']
else:
  rra_indices = []
  for key in rrd_info:
    if key.startswith('rra['):
      index = int(key.split('[')[1].split(']')[0])
      rra_indices.append(index)

  rra_count = max(rra_indices) + 1
  rras = []
  for i in range(rra_count):
    rra_info = {}
    rra_info['pdp_per_row'] = rrd_info['rra[%d].pdp_per_row' % i]
    rra_info['rows'] = rrd_info['rra[%d].rows' % i]
    rra_info['cf'] = rrd_info['rra[%d].cf' % i]
    rra_info['xff'] = rrd_info['rra[%d].xff' % i]
    rras.append(rra_info)

datasources = []
if 'ds' in rrd_info:
  datasource_names = rrd_info['ds'].keys()
else:
  ds_keys = [key for key in rrd_info if key.startswith('ds[')]
  datasources = list(set(key[3:].split(']')[0] for key in ds_keys))

# Grab the archive configuration
relevant_rras = []
for rra in rras:
  if rra['cf'] == options.aggregationMethod.upper():
    relevant_rras.append(rra)

if not relevant_rras:
  err = "[ERROR] Unable to find any RRAs with consolidation function: %s" % \
        options.aggregationMethod.upper()
  raise SystemExit(err)

archives = []
xFilesFactor = options.xFilesFactor
for rra in relevant_rras:
  precision = rra['pdp_per_row'] * seconds_per_pdp
  points = rra['rows']
  if not xFilesFactor:
    xFilesFactor = rra['xff']
  archives.append((precision, points))

for datasource in datasources:
  now = int(time.time())
  path = rrd_path.replace('.rrd', '_%s.wsp' % datasource)
  try:
    whisper.create(path, archives, xFilesFactor=xFilesFactor)
  except whisper.InvalidConfiguration, e:
    raise SystemExit('[ERROR] %s' % str(e))
  size = os.stat(path).st_size
  archiveConfig = ','.join(["%d:%d" % ar for ar in archives])
  print "Created: %s (%d bytes) with archives: %s" % (path, size, archiveConfig)

  print "Migrating data"
  archiveNumber = len(archives) - 1
  for precision, points in reversed(archives):
    retention = precision * points
    endTime = now - now % precision
    startTime = endTime - retention
    (time_info, columns, rows) = rrdtool.fetch(
      rrd_path,
      options.aggregationMethod.upper(),
      '-r', str(precision),
      '-s', str(startTime),
      '-e', str(endTime))
    column_index = list(columns).index(datasource)
    rows.pop()  # remove the last datapoint because RRD sometimes gives funky values

    values = [row[column_index] for row in rows]
    timestamps = list(range(*time_info))
    datapoints = zip(timestamps, values)
    datapoints = filter(lambda p: p[1] is not None, datapoints)
    print ' migrating %d datapoints from archive %d' % (len(datapoints), archiveNumber)
    archiveNumber -= 1
    whisper.update_many(path, datapoints)

########NEW FILE########
__FILENAME__ = whisper-create
#!/usr/bin/env python

import os
import sys
import signal
import optparse

try:
  import whisper
except ImportError:
  raise SystemExit('[ERROR] Please make sure whisper is installed properly')

# Ignore SIGPIPE
try:
   signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except AttributeError:
   #OS=windows
   pass

option_parser = optparse.OptionParser(
    usage='''%prog path timePerPoint:timeToStore [timePerPoint:timeToStore]*

timePerPoint and timeToStore specify lengths of time, for example:

60:1440      60 seconds per datapoint, 1440 datapoints = 1 day of retention
15m:8        15 minutes per datapoint, 8 datapoints = 2 hours of retention
1h:7d        1 hour per datapoint, 7 days of retention
12h:2y       12 hours per datapoint, 2 years of retention
''')
option_parser.add_option('--xFilesFactor', default=0.5, type='float')
option_parser.add_option('--aggregationMethod', default='average',
        type='string', help="Function to use when aggregating values (%s)" %
        ', '.join(whisper.aggregationMethods))
option_parser.add_option('--overwrite', default=False, action='store_true')

(options, args) = option_parser.parse_args()

if len(args) < 2:
  option_parser.print_help()
  sys.exit(1)

path = args[0]
archives = [whisper.parseRetentionDef(retentionDef)
            for retentionDef in args[1:]]

if os.path.exists(path) and options.overwrite:
    print 'Overwriting existing file: %s' % path
    os.unlink(path)

try:
  whisper.create(path, archives, xFilesFactor=options.xFilesFactor, aggregationMethod=options.aggregationMethod)
except whisper.WhisperException, exc:
  raise SystemExit('[ERROR] %s' % str(exc))

size = os.stat(path).st_size
print 'Created: %s (%d bytes)' % (path,size)

########NEW FILE########
__FILENAME__ = whisper-dump
#!/usr/bin/env python

import os
import mmap
import struct
import signal
import optparse

try:
  import whisper
except ImportError:
  raise SystemExit('[ERROR] Please make sure whisper is installed properly')

# Ignore SIGPIPE
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

option_parser = optparse.OptionParser(usage='''%prog path''')
(options, args) = option_parser.parse_args()

if len(args) != 1:
  option_parser.error("require one input file name")
else:
  path = args[0]

def mmap_file(filename):
  fd = os.open(filename, os.O_RDONLY)
  map = mmap.mmap(fd, os.fstat(fd).st_size, prot=mmap.PROT_READ)
  os.close(fd)
  return map

def read_header(map):
  try:
    (aggregationType,maxRetention,xFilesFactor,archiveCount) = struct.unpack(whisper.metadataFormat,map[:whisper.metadataSize])
  except:
    raise CorruptWhisperFile("Unable to unpack header")

  archives = []
  archiveOffset = whisper.metadataSize

  for i in xrange(archiveCount):
    try:
      (offset, secondsPerPoint, points) = struct.unpack(whisper.archiveInfoFormat, map[archiveOffset:archiveOffset+whisper.archiveInfoSize])
    except:
      raise CorruptWhisperFile("Unable to read archive %d metadata" % i)

    archiveInfo = {
      'offset' : offset,
      'secondsPerPoint' : secondsPerPoint,
      'points' : points,
      'retention' : secondsPerPoint * points,
      'size' : points * whisper.pointSize,
    }
    archives.append(archiveInfo)
    archiveOffset += whisper.archiveInfoSize

  header = {
    'aggregationMethod' : whisper.aggregationTypeToMethod.get(aggregationType, 'average'),
    'maxRetention' : maxRetention,
    'xFilesFactor' : xFilesFactor,
    'archives' : archives,
  }
  return header

def dump_header(header):
  print 'Meta data:'
  print '  aggregation method: %s' % header['aggregationMethod']
  print '  max retention: %d' % header['maxRetention']
  print '  xFilesFactor: %g' % header['xFilesFactor']
  print
  dump_archive_headers(header['archives'])

def dump_archive_headers(archives):
  for i,archive in enumerate(archives):
    print 'Archive %d info:' % i
    print '  offset: %d' % archive['offset']
    print '  seconds per point: %d' % archive['secondsPerPoint']
    print '  points: %d' % archive['points']
    print '  retention: %d' % archive['retention']
    print '  size: %d' % archive['size']
    print

def dump_archives(archives):
  for i,archive in enumerate(archives):
    print 'Archive %d data:' %i
    offset = archive['offset']
    for point in xrange(archive['points']):
      (timestamp, value) = struct.unpack(whisper.pointFormat, map[offset:offset+whisper.pointSize])
      print '%d: %d, %10.35g' % (point, timestamp, value)
      offset += whisper.pointSize
    print

if not os.path.exists(path):
  raise SystemExit('[ERROR] File "%s" does not exist!' % path)

map = mmap_file(path)
header = read_header(map)
dump_header(header)
dump_archives(header['archives'])

########NEW FILE########
__FILENAME__ = whisper-fetch
#!/usr/bin/env python

import sys
import time
import signal
import optparse

try:
  import whisper
except ImportError:
  raise SystemExit('[ERROR] Please make sure whisper is installed properly')

# Ignore SIGPIPE
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

now = int( time.time() )
yesterday = now - (60 * 60 * 24)

option_parser = optparse.OptionParser(usage='''%prog [options] path''')
option_parser.add_option('--from', default=yesterday, type='int', dest='_from',
  help=("Unix epoch time of the beginning of "
        "your requested interval (default: 24 hours ago)"))
option_parser.add_option('--until', default=now, type='int',
  help="Unix epoch time of the end of your requested interval (default: now)")
option_parser.add_option('--json', default=False, action='store_true',
  help="Output results in JSON form")
option_parser.add_option('--pretty', default=False, action='store_true',
  help="Show human-readable timestamps instead of unix times")

(options, args) = option_parser.parse_args()

if len(args) != 1:
  option_parser.print_help()
  sys.exit(1)

path = args[0]

from_time = int( options._from )
until_time = int( options.until )


try:
  (timeInfo, values) = whisper.fetch(path, from_time, until_time)
except whisper.WhisperException, exc:
  raise SystemExit('[ERROR] %s' % str(exc))


(start,end,step) = timeInfo

if options.json:
  values_json = str(values).replace('None','null')
  print '''{
    "start" : %d,
    "end" : %d,
    "step" : %d,
    "values" : %s
  }''' % (start,end,step,values_json)
  sys.exit(0)

t = start
for value in values:
  if options.pretty:
    timestr = time.ctime(t)
  else:
    timestr = str(t)
  if value is None:
    valuestr = "None"
  else:
    valuestr = "%f" % value
  print "%s\t%s" % (timestr,valuestr)
  t += step

########NEW FILE########
__FILENAME__ = whisper-info
#!/usr/bin/env python

import os
import sys
import signal
import optparse

try:
  import whisper
except ImportError:
  raise SystemExit('[ERROR] Please make sure whisper is installed properly')

# Ignore SIGPIPE
try:
  signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except AttributeError:
  #OS=windows
  pass

option_parser = optparse.OptionParser(usage='''%prog path [field]''')
(options, args) = option_parser.parse_args()

if len(args) < 1:
  option_parser.print_help()
  sys.exit(1)

path = args[0]
if len(args) > 1:
  field = args[1]
else:
  field = None

try:
  info = whisper.info(path)
except whisper.WhisperException, exc:
  raise SystemExit('[ERROR] %s' % str(exc))

info['fileSize'] = os.stat(path).st_size

if field:
  if field not in info:
    print 'Unknown field "%s". Valid fields are %s' % (field, ','.join(info))
    sys.exit(1)

  print info[field]
  sys.exit(0)


archives = info.pop('archives')
for key,value in info.items():
  print '%s: %s' % (key,value)
print

for i,archive in enumerate(archives):
  print 'Archive %d' % i
  for key,value in archive.items():
    print '%s: %s' % (key,value)
  print

########NEW FILE########
__FILENAME__ = whisper-merge
#!/usr/bin/env python

import os
import sys
import signal
import optparse

try:
  import whisper
except ImportError:
  raise SystemExit('[ERROR] Please make sure whisper is installed properly')

# Ignore SIGPIPE
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

option_parser = optparse.OptionParser(
    usage='''%prog [options] from_path to_path''')

(options, args) = option_parser.parse_args()

if len(args) < 2:
  option_parser.print_help()
  sys.exit(1)

path_from = args[0]
path_to = args[1]

for filename in (path_from, path_to):
   if not os.path.exists(filename):
       raise SystemExit('[ERROR] File "%s" does not exist!' % filename)

whisper.merge(path_from, path_to)

########NEW FILE########
__FILENAME__ = whisper-resize
#!/usr/bin/env python

import os
import sys
import math
import time
import bisect
import signal
import optparse
import traceback

try:
  import whisper
except ImportError:
  raise SystemExit('[ERROR] Please make sure whisper is installed properly')

# Ignore SIGPIPE
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

now = int(time.time())

option_parser = optparse.OptionParser(
    usage='''%prog path timePerPoint:timeToStore [timePerPoint:timeToStore]*

timePerPoint and timeToStore specify lengths of time, for example:

60:1440      60 seconds per datapoint, 1440 datapoints = 1 day of retention
15m:8        15 minutes per datapoint, 8 datapoints = 2 hours of retention
1h:7d        1 hour per datapoint, 7 days of retention
12h:2y       12 hours per datapoint, 2 years of retention
''')

option_parser.add_option(
    '--xFilesFactor', default=None,
    type='float', help="Change the xFilesFactor")
option_parser.add_option(
    '--aggregationMethod', default=None,
    type='string', help="Change the aggregation function (%s)" %
    ', '.join(whisper.aggregationMethods))
option_parser.add_option(
    '--force', default=False, action='store_true',
    help="Perform a destructive change")
option_parser.add_option(
    '--newfile', default=None, action='store',
    help="Create a new database file without removing the existing one")
option_parser.add_option(
    '--nobackup', action='store_true',
    help='Delete the .bak file after successful execution')
option_parser.add_option(
    '--aggregate', action='store_true',
    help='Try to aggregate the values to fit the new archive better.'
         ' Note that this will make things slower and use more memory.')

(options, args) = option_parser.parse_args()

if len(args) < 2:
  option_parser.print_help()
  sys.exit(1)

path = args[0]

if not os.path.exists(path):
  sys.stderr.write("[ERROR] File '%s' does not exist!\n\n" % path)
  option_parser.print_help()
  sys.exit(1)

info = whisper.info(path)

new_archives = [whisper.parseRetentionDef(retentionDef)
                for retentionDef in args[1:]]

old_archives = info['archives']
# sort by precision, lowest to highest
old_archives.sort(key=lambda a: a['secondsPerPoint'], reverse=True)

if options.xFilesFactor is None:
  xff = info['xFilesFactor']
else:
  xff = options.xFilesFactor

if options.aggregationMethod is None:
  aggregationMethod = info['aggregationMethod']
else:
  aggregationMethod = options.aggregationMethod

print 'Retrieving all data from the archives'
for archive in old_archives:
  fromTime = now - archive['retention'] + archive['secondsPerPoint']
  untilTime = now
  timeinfo,values = whisper.fetch(path, fromTime, untilTime)
  archive['data'] = (timeinfo,values)

if options.newfile is None:
  tmpfile = path + '.tmp'
  if os.path.exists(tmpfile):
    print 'Removing previous temporary database file: %s' % tmpfile
    os.unlink(tmpfile)
  newfile = tmpfile
else:
  newfile = options.newfile

print 'Creating new whisper database: %s' % newfile
whisper.create(newfile, new_archives, xFilesFactor=xff, aggregationMethod=aggregationMethod)
size = os.stat(newfile).st_size
print 'Created: %s (%d bytes)' % (newfile,size)

if options.aggregate:
  # This is where data will be interpolated (best effort)
  print 'Migrating data with aggregation...'
  all_datapoints = []
  for archive in old_archives:
    # Loading all datapoints into memory for fast querying
    timeinfo, values = archive['data']
    new_datapoints = zip( range(*timeinfo), values )
    if all_datapoints:
      last_timestamp = all_datapoints[-1][0]
      slice_end = 0
      for i,(timestamp,value) in enumerate(new_datapoints):
        if timestamp > last_timestamp:
          slice_end = i
          break
      all_datapoints += new_datapoints[i:]
    else:
      all_datapoints += new_datapoints

  oldtimestamps = map( lambda p: p[0], all_datapoints)
  oldvalues = map( lambda p: p[1], all_datapoints)

  print "oldtimestamps: %s" % oldtimestamps
  # Simply cleaning up some used memory
  del all_datapoints

  new_info = whisper.info(newfile)
  new_archives = new_info['archives']

  for archive in new_archives:
    step = archive['secondsPerPoint']
    fromTime = now - archive['retention'] + now % step
    untilTime = now + now % step + step
    print "(%s,%s,%s)" % (fromTime,untilTime, step)
    timepoints_to_update = range(fromTime, untilTime, step)
    print "timepoints_to_update: %s" % timepoints_to_update
    newdatapoints = []
    for tinterval in zip( timepoints_to_update[:-1], timepoints_to_update[1:] ):
      # TODO: Setting lo= parameter for 'lefti' based on righti from previous
      #       iteration. Obviously, this can only be done if
      #       timepoints_to_update is always updated. Is it?
      lefti = bisect.bisect_left(oldtimestamps, tinterval[0])
      righti = bisect.bisect_left(oldtimestamps, tinterval[1], lo=lefti)
      newvalues = oldvalues[lefti:righti]
      if newvalues:
        non_none = filter( lambda x: x is not None, newvalues)
        if 1.0*len(non_none)/len(newvalues) >= xff:
          newdatapoints.append([tinterval[0],
                                whisper.aggregate(aggregationMethod,
                                                  non_none)])
    whisper.update_many(newfile, newdatapoints)
else:
  print 'Migrating data without aggregation...'
  for archive in old_archives:
    timeinfo, values = archive['data']
    datapoints = zip( range(*timeinfo), values )
    datapoints = filter(lambda p: p[1] is not None, datapoints)
    whisper.update_many(newfile, datapoints)

if options.newfile is not None:
  sys.exit(0)

backup = path + '.bak'
print 'Renaming old database to: %s' % backup
os.rename(path, backup)

try:
  print 'Renaming new database to: %s' % path
  os.rename(tmpfile, path)
except:
  traceback.print_exc()
  print '\nOperation failed, restoring backup'
  os.rename(backup, path)
  sys.exit(1)

if options.nobackup:
  print "Unlinking backup: %s" % backup
  os.unlink(backup)

########NEW FILE########
__FILENAME__ = whisper-set-aggregation-method
#!/usr/bin/env python

import os
import sys
import signal
import optparse

try:
    import whisper
except ImportError:
    raise SystemExit('[ERROR] Please make sure whisper is installed properly')

# Ignore SIGPIPE
try:
  signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except AttributeError:
  #windows?
  pass

option_parser = optparse.OptionParser(
    usage='%%prog path <%s> [xFilesFactor]' % '|'.join(whisper.aggregationMethods))

(options, args) = option_parser.parse_args()

if len(args) < 2:
  option_parser.print_help()
  sys.exit(1)

path = args[0]
aggregationMethod = args[1]

xFilesFactor = None
if len(args) == 3:
  xFilesFactor = args[2]

try:
  oldAggregationMethod = whisper.setAggregationMethod(path, aggregationMethod, xFilesFactor)
except IOError, exc:
  sys.stderr.write("[ERROR] File '%s' does not exist!\n\n" % path)
  option_parser.print_help()
  sys.exit(1)
except whisper.WhisperException, exc:
  raise SystemExit('[ERROR] %s' % str(exc))


print 'Updated aggregation method: %s (%s -> %s)' % (path,oldAggregationMethod,aggregationMethod)

########NEW FILE########
__FILENAME__ = whisper-update
#!/usr/bin/env python

import sys
import time
import signal
import optparse

try:
  import whisper
except ImportError:
  raise SystemExit('[ERROR] Please make sure whisper is installed properly')

# Ignore SIGPIPE
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

now = int( time.time() )

option_parser = optparse.OptionParser(
    usage='''%prog [options] path timestamp:value [timestamp:value]*''')

(options, args) = option_parser.parse_args()

if len(args) < 2:
  option_parser.print_help()
  sys.exit(1)

path = args[0]
datapoint_strings = args[1:]
datapoint_strings = [point.replace('N:', '%d:' % now)
                     for point in datapoint_strings]
datapoints = [tuple(point.split(':')) for point in datapoint_strings]

try:
  if len(datapoints) == 1:
    timestamp,value = datapoints[0]
    whisper.update(path, value, timestamp)
  else:
    whisper.update_many(path, datapoints)
except whisper.WhisperException, exc:
  raise SystemExit('[ERROR] %s' % str(exc))

########NEW FILE########
__FILENAME__ = whisper-auto-resize
#!/usr/bin/env python
import sys, os, fnmatch
from subprocess import call
from optparse import OptionParser

option_parser = OptionParser(
    usage='''%prog storagePath configPath

storagePath   the Path to the directory containing whisper files (CAN NOT BE A SUBDIR, use --subdir for that)
configPath    the path to your carbon config files
''', version="%prog 0.1")

option_parser.add_option(
    '--doit', default=False, action='store_true',
    help="This is not a drill, lets do it")
option_parser.add_option(
    '-q', '--quiet', default=False, action='store_true',
    help="Display extra debugging info")
option_parser.add_option(
    '--subdir', default=None,
    type='string', help="only process a subdir of whisper files")
option_parser.add_option(
    '--carbonlib', default=None,
    type='string', help="folder where the carbon lib files are if its not in your path already")
option_parser.add_option(
    '--whisperlib', default=None,
    type='string', help="folder where the whisper lib files are if its not in your path already")
option_parser.add_option(
    '--confirm', default=False, action='store_true',
    help="ask for comfirmation prior to resizing a whisper file")
option_parser.add_option(
    '-x', '--extra_args', default='',
    type='string', help="pass any additional arguments to the whisper-resize.py script")

(options, args) = option_parser.parse_args()

if len(args) < 2:
    option_parser.print_help()
    sys.exit(1)

storagePath = args[0]
configPath  = args[1]

#check to see if we are processing a subfolder
# we need to have a seperate config option for this since
# otherwise the metric test thinks the metric is at the root
# of the storage path and can match schemas incorrectly
if options.subdir is None:
    processPath = args[0]
else:
    processPath = options.subdir

# Injecting the Whisper Lib Path if needed
if options.whisperlib is not None:
    sys.path.insert(0, options.whisperlib)

try:
    import whisper
except ImportError:
    raise SystemExit('[ERROR] Can\'t find the whisper module, try using --whisperlib to explicitly include the path')

# Injecting the Carbon Lib Path if needed
if options.carbonlib is not None:
    sys.path.insert(0, options.carbonlib)

try:
    from carbon import conf
    from carbon.conf import settings
except ImportError:
    raise SystemExit('[ERROR] Can\'t find the carbon module, try using --carbonlib to explicitly include the path')

#carbon.conf not seeing the config files so give it a nudge
settings.CONF_DIR = configPath
settings.LOCAL_DATA_DIR = storagePath

# import these once we have the settings figured out
from carbon.storage import loadStorageSchemas, loadAggregationSchemas

# Load the Defined Schemas from our config files
schemas = loadStorageSchemas()
agg_schemas = loadAggregationSchemas()

# check to see if a metric needs to be resized based on the current config
def processMetric(fullPath, schemas, agg_schemas):
    """
        method to process a given metric, and resize it if necessary

        Parameters:
            fullPath    - full path to the metric whisper file
            schemas     - carbon storage schemas loaded from config
            agg_schemas - carbon storage aggregation schemas load from confg

    """
    schema_config_args = ''
    schema_file_args   = ''
    rebuild = False
    messages = ''

    # get archive info from whisper file
    info = whisper.info(fullpath)

    # get graphite metric name from fullPath
    metric = getMetricFromPath(fullpath)

    # loop the carbon-storage schemas
    for schema in schemas:
        if schema.matches(metric):
            # returns secondsPerPoint and points for this schema in tuple format
            archive_config = [archive.getTuple() for archive in schema.archives]
            break

    # loop through the carbon-aggregation schemas
    for agg_schema in agg_schemas:
        if agg_schema.matches(metric):
            xFilesFactor, aggregationMethod = agg_schema.archives
            break

    # loop through the bucket tuples and convert to string format for resizing
    for retention in archive_config:
        current_schema = '%s:%s ' % (retention[0], retention[1])
        schema_config_args += current_schema

    # loop through the current files bucket sizes and convert to string format to compare for resizing
    for fileRetention in info['archives']:
        current_schema  = '%s:%s ' % (fileRetention['secondsPerPoint'], fileRetention['points'])
        schema_file_args += current_schema

    # check to see if the current and configured schemas are the same or rebuild
    if (schema_config_args != schema_file_args):
        rebuild = True
        messages += 'updating Retentions from: %s to: %s \n' % (schema_file_args, schema_config_args)

    # only care about the first two decimals in the comparison since there is floaty stuff going on.
    info_xFilesFactor = "{0:.2f}".format(info['xFilesFactor'])
    str_xFilesFactor =  "{0:.2f}".format(xFilesFactor)

    # check to see if the current and configured aggregationMethods are the same
    if (str_xFilesFactor != info_xFilesFactor):
        rebuild = True
        messages += '%s xFilesFactor differs real: %s should be: %s \n' % (metric, info_xFilesFactor, str_xFilesFactor)
    if (aggregationMethod != info['aggregationMethod']):
        rebuild = True
        messages += '%s aggregation schema differs real: %s should be: %s \n' % (metric, info['aggregationMethod'], aggregationMethod)

    # check to see if the current and configured xFilesFactor are the same
    if (xFilesFactor != info['xFilesFactor']):
        rebuild = True
        messages += '%s xFilesFactor differs real: %s should be: %s \n' % (metric, info['xFilesFactor'], xFilesFactor)

    # if we need to rebuild, lets do it.
    if (rebuild == True):
        cmd = 'whisper-resize.py %s %s --xFilesFactor=%s --aggregationMethod=%s %s' % (fullPath, options.extra_args, xFilesFactor, aggregationMethod, schema_config_args)
        if (options.quiet != True or options.confirm == True):
            print messages
            print cmd

        if (options.confirm == True):
            options.doit = confirm("Would you like to run this command? [y/n]: ")
            if (options.doit == False):
                print "Skipping command \n"

        if (options.doit == True):
            exitcode = call(cmd, shell=True)
            # if the command failed lets bail so we can take a look before proceeding
            if (exitcode > 0):
                print 'Error running: %s' % (cmd)
                sys.exit(1)

def getMetricFromPath(filePath):
    """
        this method takes the full file path of a whisper file an converts it to a gaphite metric name

        Parameters:
            filePath - full file path to a whisper file

        Returns a string representing the metric name
    """
    # sanitize directory since we may get a trailing slash or not, and if we don't it creates a leading .
    data_dir = os.path.normpath(settings.LOCAL_DATA_DIR) + os.sep

    # pull the data dir off and convert to the graphite metric name
    metric_name = filePath.replace(data_dir, '')
    metric_name = metric_name.replace('.wsp', '')
    metric_name = metric_name.replace('/', '.')
    return metric_name

def confirm(question, error_response='Valid options : yes or no'):
    """
         ask the user if they would like to perform the action

         Parameters:
             question       - the question you would like to ask the user to confirm.
             error_response - the message to display if an invalid option is given.
    """
    while True:
        answer = raw_input(question).lower()
        if answer in ('y', 'yes'):
            return True
        if answer in ('n', 'no' ):
            return False
        print error_response

for root, _, files in os.walk(processPath):
    # we only want to deal with non-hidden whisper files
    for f in fnmatch.filter(files, '*.wsp'):
        fullpath = os.path.join(root, f)
        processMetric(fullpath, schemas, agg_schemas)


########NEW FILE########
__FILENAME__ = whisper-auto-update
#!/usr/bin/env python

import sys
import time
import signal
import optparse

try:
  import whisper
except ImportError:
  raise SystemExit('[ERROR] Please make sure whisper is installed properly')

# update this callback to do the logic you want.
# a future version could use a config while in which this fn is defined.

def update_value(timestamp, value):
  if value is None:
    return value
  return value*1024*1024*1024


# Ignore SIGPIPE
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

now = int( time.time() )
yesterday = now - (60 * 60 * 24)

option_parser = optparse.OptionParser(usage='''%prog [options] path''')
option_parser.add_option('--from', default=yesterday, type='int', dest='_from',
  help=("Unix epoch time of the beginning of "
        "your requested interval (default: 24 hours ago)"))
option_parser.add_option('--until', default=now, type='int',
  help="Unix epoch time of the end of your requested interval (default: now)")
option_parser.add_option('--pretty', default=False, action='store_true',
  help="Show human-readable timestamps instead of unix times")

(options, args) = option_parser.parse_args()

if len(args) < 1:
  option_parser.print_usage()
  sys.exit(1)

path = args[0]
from_time = int( options._from )
until_time = int( options.until )

try:
  (timeInfo, values_old) = whisper.fetch(path, from_time, until_time)
except whisper.WhisperException, exc:
  raise SystemExit('[ERROR] %s' % str(exc))

(start,end,step) = timeInfo
t = start
for value_old in values_old:
  value_str_old = str(value_old)
  value_new = update_value(t, value_old)
  value_str_new = str(value_new)
  if options.pretty:
    timestr = time.ctime(t)
  else:
    timestr = str(t)

  print "%s\t%s -> %s" % (timestr,value_str_old, value_str_new)
  try:
    if value_new is not None:
      whisper.update(path, value_new, t)
    t += step
  except whisper.WhisperException, exc:
    raise SystemExit('[ERROR] %s' % str(exc))


########NEW FILE########
__FILENAME__ = test_whisper
#!/usr/bin/env python

import os
import time
import random
import struct

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import whisper


class TestWhisper(unittest.TestCase):
    """
    Testing functions for whisper.
    """
    db = "db.wsp"

    @classmethod
    def setUpClass(cls):
        cls._removedb()

    @classmethod
    def _removedb(cls):
        """Remove the whisper database file"""
        try:
            if os.path.exists(cls.db):
                os.unlink(cls.db)
        except (IOError, OSError):
            pass

    def test_validate_archive_list(self):
        """blank archive config"""
        with self.assertRaises(whisper.InvalidConfiguration):
            whisper.validateArchiveList([])

    def test_duplicate(self):
        """Checking duplicates"""
        whisper.validateArchiveList([(1, 60), (60, 60)])
        with self.assertRaises(whisper.InvalidConfiguration):
            whisper.validateArchiveList([(1, 60), (60, 60), (1, 60)])

    def test_even_precision_division(self):
        """even precision division"""
        whisper.validateArchiveList([(60, 60), (6, 60)])
        with self.assertRaises(whisper.InvalidConfiguration):
            whisper.validateArchiveList([(60, 60), (7, 60)])

    def test_timespan_coverage(self):
        """timespan coverage"""
        whisper.validateArchiveList([(1, 60), (60, 60)])
        with self.assertRaises(whisper.InvalidConfiguration):
            whisper.validateArchiveList([(1, 60), (10, 1)])

    def test_number_of_points(self):
        """number of points"""
        whisper.validateArchiveList([(1, 60), (60, 60)])
        with self.assertRaises(whisper.InvalidConfiguration):
            whisper.validateArchiveList([(1, 30), (60, 60)])

    def test_aggregate(self):
        """aggregate functions"""
        # min of 1-4
        self.assertEqual(whisper.aggregate('min', [1, 2, 3, 4]), 1)
        # max of 1-4
        self.assertEqual(whisper.aggregate('max', [1, 2, 3, 4]), 4)
        # last element in the known values
        self.assertEqual(whisper.aggregate('last', [3, 2, 5, 4]), 4)
        # sum ALL THE VALUES!
        self.assertEqual(whisper.aggregate('sum', [10, 2, 3, 4]), 19)
        # average of the list elements
        self.assertEqual(whisper.aggregate('average', [1, 2, 3, 4]), 2.5)
        with self.assertRaises(whisper.InvalidAggregationMethod):
            whisper.aggregate('derp', [12, 2, 3123, 1])

    def test_create(self):
        """Create a db and use info() to validate"""
        retention = [(1, 60), (60, 60)]

        # check if invalid configuration fails successfully
        with self.assertRaises(whisper.InvalidConfiguration):
            whisper.create(self.db, [])

        # create a new db with a valid configuration
        whisper.create(self.db, retention)

        # attempt to create another db in the same file, this should fail
        with self.assertRaises(whisper.InvalidConfiguration):
            whisper.create(self.db, 0)

        info = whisper.info(self.db)

        # check header information
        self.assertEqual(info['maxRetention'],
                         max([a[0] * a[1] for a in retention]))
        self.assertEqual(info['aggregationMethod'], 'average')
        self.assertEqual(info['xFilesFactor'], 0.5)

        # check archive information
        self.assertEqual(len(info['archives']), len(retention))
        self.assertEqual(info['archives'][0]['points'], retention[0][1])
        self.assertEqual(info['archives'][0]['secondsPerPoint'],
                         retention[0][0])
        self.assertEqual(info['archives'][0]['retention'],
                         retention[0][0] * retention[0][1])
        self.assertEqual(info['archives'][1]['retention'],
                         retention[1][0] * retention[1][1])

        # remove database
        self._removedb()

    def test_merge(self):
        """test merging two databases"""
        testdb = "test-%s" % self.db
        self._removedb()

        try:
          os.unlink(testdb)
        except Exception:
          pass

        # Create 2 whisper databases and merge one into the other
        self._update()
        self._update(testdb)

        whisper.merge(self.db, testdb)

        self._removedb()
        try:
          os.unlink(testdb)
        except Exception:
          pass

    def test_fetch(self):
        """fetch info from database """

        # check a db that doesnt exist
        with self.assertRaises(Exception):
            whisper.fetch("this_db_does_not_exist", 0)

        # SECOND MINUTE HOUR DAY
        retention = [(1, 60), (60, 60), (3600, 24), (86400, 365)]
        whisper.create(self.db, retention)

        # check a db with an invalid time range
        with self.assertRaises(whisper.InvalidTimeInterval):
            whisper.fetch(self.db, time.time(), time.time()-6000)

        fetch = whisper.fetch(self.db, 0)

        # check time range
        self.assertEqual(fetch[0][1] - fetch[0][0],
                         retention[-1][0] * retention[-1][1])

        # check number of points
        self.assertEqual(len(fetch[1]), retention[-1][1])

        # check step size
        self.assertEqual(fetch[0][2], retention[-1][0])

        self._removedb()

    def _update(self, wsp=None, schema=None):
        wsp = wsp or self.db
        schema = schema or [(1, 20)]
        num_data_points = 20

        whisper.create(wsp, schema)

        # create sample data
        tn = time.time() - num_data_points
        data = []
        for i in range(num_data_points):
            data.append((tn + 1 + i, random.random() * 10))

        # test single update
        whisper.update(wsp, data[0][1], data[0][0])

        # test multi update
        whisper.update_many(wsp, data[1:])
        return data

    def test_update_single_archive(self):
        """Update with a single leveled archive"""
        retention_schema = [(1, 20)]
        data = self._update(schema=retention_schema)
        # fetch the data
        fetch = whisper.fetch(self.db, 0)   # all data
        fetch_data = fetch[1]

        for i, (timestamp, value) in enumerate(data):
            # is value in the fetched data?
            self.assertEqual(value, fetch_data[i])

        # check TimestampNotCovered
        with self.assertRaises(whisper.TimestampNotCovered):
            # in the future
            whisper.update(self.db, 1.337, time.time() + 1)
        with self.assertRaises(whisper.TimestampNotCovered):
            # before the past
            whisper.update(self.db, 1.337,
                           time.time() - retention_schema[0][1] - 1)

        self._removedb()
        
    def test_setAggregation(self):
        """Create a db, change aggregation, xFilesFactor, then use info() to validate"""
        retention = [(1, 60), (60, 60)]

        # create a new db with a valid configuration
        whisper.create(self.db, retention)

        #set setting every AggregationMethod available
        for ag in whisper.aggregationMethods:
          for xff in 0.0,0.2,0.4,0.7,0.75,1.0:
            #original xFilesFactor
            info0 = whisper.info(self.db)
            #optional xFilesFactor not passed
            whisper.setAggregationMethod(self.db, ag)

            #original value should not change
            info1 = whisper.info(self.db)
            self.assertEqual(info0['xFilesFactor'],info1['xFilesFactor'])
            #the selected aggregation method should have applied
            self.assertEqual(ag,info1['aggregationMethod'])

            #optional xFilesFactor used
            whisper.setAggregationMethod(self.db, ag, xff)
            #new info should match what we just set it to
            info2 = whisper.info(self.db)
            #packing and unpacking because
            #AssertionError: 0.20000000298023224 != 0.2
            target_xff = struct.unpack("!f", struct.pack("!f",xff))[0]
            self.assertEqual(info2['xFilesFactor'], target_xff)

            #same aggregationMethod asssertion again, but double-checking since
            #we are playing with packed values and seek()
            self.assertEqual(ag,info2['aggregationMethod'])

        self._removedb()


    @classmethod
    def tearDownClass(cls):
        cls._removedb()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = whisper
# Copyright 2009-Present The Graphite Development Team
# Copyright 2008 Orbitz WorldWide
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# This module is an implementation of the Whisper database API
# Here is the basic layout of a whisper data file
#
# File = Header,Data
#	Header = Metadata,ArchiveInfo+
#		Metadata = aggregationType,maxRetention,xFilesFactor,archiveCount
#		ArchiveInfo = Offset,SecondsPerPoint,Points
#	Data = Archive+
#		Archive = Point+
#			Point = timestamp,value

import os, struct, time, operator, itertools

try:
  import fcntl
  CAN_LOCK = True
except ImportError:
  CAN_LOCK = False

try:
  import ctypes
  import ctypes.util
  CAN_FALLOCATE = True
except ImportError:
  CAN_FALLOCATE = False

fallocate = None

if CAN_FALLOCATE: 
  libc_name = ctypes.util.find_library('c')
  libc = ctypes.CDLL(libc_name)
  c_off64_t = ctypes.c_int64
  c_off_t = ctypes.c_int

  try:
    _fallocate = libc.posix_fallocate64
    _fallocate.restype = ctypes.c_int
    _fallocate.argtypes = [ctypes.c_int, c_off64_t, c_off64_t]
  except AttributeError, e:
    try:
      _fallocate = libc.posix_fallocate
      _fallocate.restype = ctypes.c_int
      _fallocate.argtypes = [ctypes.c_int, c_off_t, c_off_t]
    except AttributeError, e:
      CAN_FALLOCATE = False

  if CAN_FALLOCATE:
    def _py_fallocate(fd, offset, len_):
      res = _fallocate(fd.fileno(), offset, len_)
      if res != 0:
        raise IOError(res, 'fallocate')
    fallocate = _py_fallocate
  del libc
  del libc_name

LOCK = False
CACHE_HEADERS = False
AUTOFLUSH = False
__headerCache = {}

longFormat = "!L"
longSize = struct.calcsize(longFormat)
floatFormat = "!f"
floatSize = struct.calcsize(floatFormat)
valueFormat = "!d"
valueSize = struct.calcsize(valueFormat)
pointFormat = "!Ld"
pointSize = struct.calcsize(pointFormat)
metadataFormat = "!2LfL"
metadataSize = struct.calcsize(metadataFormat)
archiveInfoFormat = "!3L"
archiveInfoSize = struct.calcsize(archiveInfoFormat)

aggregationTypeToMethod = dict({
  1: 'average',
  2: 'sum',
  3: 'last',
  4: 'max',
  5: 'min'
})
aggregationMethodToType = dict([[v,k] for k,v in aggregationTypeToMethod.items()])
aggregationMethods = aggregationTypeToMethod.values()

debug = startBlock = endBlock = lambda *a,**k: None

UnitMultipliers = {
  'seconds' : 1,
  'minutes' : 60,
  'hours' : 3600,
  'days' : 86400,
  'weeks' : 86400 * 7,
  'years' : 86400 * 365
}


def getUnitString(s):
  if 'seconds'.startswith(s): return 'seconds'
  if 'minutes'.startswith(s): return 'minutes'
  if 'hours'.startswith(s): return 'hours'
  if 'days'.startswith(s): return 'days'
  if 'weeks'.startswith(s): return 'weeks'
  if 'years'.startswith(s): return 'years'
  raise ValueError("Invalid unit '%s'" % s)

def parseRetentionDef(retentionDef):
  import re
  (precision, points) = retentionDef.strip().split(':')

  if precision.isdigit():
    precision = int(precision) * UnitMultipliers[getUnitString('s')]
  else:
    precision_re = re.compile(r'^(\d+)([a-z]+)$')
    match = precision_re.match(precision)
    if match:
      precision = int(match.group(1)) * UnitMultipliers[getUnitString(match.group(2))]
    else:
      raise ValueError("Invalid precision specification '%s'" % precision)

  if points.isdigit():
    points = int(points)
  else:
    points_re = re.compile(r'^(\d+)([a-z]+)$')
    match = points_re.match(points)
    if match:
      points = int(match.group(1)) * UnitMultipliers[getUnitString(match.group(2))] / precision
    else:
      raise ValueError("Invalid retention specification '%s'" % points)

  return (precision, points)


class WhisperException(Exception):
    """Base class for whisper exceptions."""


class InvalidConfiguration(WhisperException):
    """Invalid configuration."""


class InvalidAggregationMethod(WhisperException):
    """Invalid aggregation method."""


class InvalidTimeInterval(WhisperException):
    """Invalid time interval."""


class TimestampNotCovered(WhisperException):
    """Timestamp not covered by any archives in this database."""

class CorruptWhisperFile(WhisperException):
  def __init__(self, error, path):
    Exception.__init__(self, error)
    self.error = error
    self.path = path

  def __repr__(self):
    return "<CorruptWhisperFile[%s] %s>" % (self.path, self.error)

  def __str__(self):
    return "%s (%s)" % (self.error, self.path)

def enableDebug():
  global open, debug, startBlock, endBlock
  class open(file):
    def __init__(self,*args,**kwargs):
      file.__init__(self,*args,**kwargs)
      self.writeCount = 0
      self.readCount = 0

    def write(self,data):
      self.writeCount += 1
      debug('WRITE %d bytes #%d' % (len(data),self.writeCount))
      return file.write(self,data)

    def read(self,bytes):
      self.readCount += 1
      debug('READ %d bytes #%d' % (bytes,self.readCount))
      return file.read(self,bytes)

  def debug(message):
    print 'DEBUG :: %s' % message

  __timingBlocks = {}

  def startBlock(name):
    __timingBlocks[name] = time.time()

  def endBlock(name):
    debug("%s took %.5f seconds" % (name,time.time() - __timingBlocks.pop(name)))


def __readHeader(fh):
  info = __headerCache.get(fh.name)
  if info:
    return info

  originalOffset = fh.tell()
  fh.seek(0)
  packedMetadata = fh.read(metadataSize)

  try:
    (aggregationType,maxRetention,xff,archiveCount) = struct.unpack(metadataFormat,packedMetadata)
  except:
    raise CorruptWhisperFile("Unable to read header", fh.name)

  archives = []

  for i in xrange(archiveCount):
    packedArchiveInfo = fh.read(archiveInfoSize)
    try:
      (offset,secondsPerPoint,points) = struct.unpack(archiveInfoFormat,packedArchiveInfo)
    except:
      raise CorruptWhisperFile("Unable to read archive%d metadata" % i, fh.name)

    archiveInfo = {
      'offset' : offset,
      'secondsPerPoint' : secondsPerPoint,
      'points' : points,
      'retention' : secondsPerPoint * points,
      'size' : points * pointSize,
    }
    archives.append(archiveInfo)

  fh.seek(originalOffset)
  info = {
    'aggregationMethod' : aggregationTypeToMethod.get(aggregationType, 'average'),
    'maxRetention' : maxRetention,
    'xFilesFactor' : xff,
    'archives' : archives,
  }
  if CACHE_HEADERS:
    __headerCache[fh.name] = info

  return info


def setAggregationMethod(path, aggregationMethod, xFilesFactor=None):
  """setAggregationMethod(path,aggregationMethod,xFilesFactor=None)

path is a string
aggregationMethod specifies the method to use when propagating data (see ``whisper.aggregationMethods``)
xFilesFactor specifies the fraction of data points in a propagation interval that must have known values for a propagation to occur.  If None, the existing xFilesFactor in path will not be changed
"""
  fh = None
  try:

    fh = open(path,'r+b')
    if LOCK:
      fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

    packedMetadata = fh.read(metadataSize)

    try:
      (aggregationType,maxRetention,xff,archiveCount) = struct.unpack(metadataFormat,packedMetadata)
    except:
      raise CorruptWhisperFile("Unable to read header", fh.name)

    try:
      newAggregationType = struct.pack( longFormat, aggregationMethodToType[aggregationMethod] )
    except KeyError:
      raise InvalidAggregationMethod("Unrecognized aggregation method: %s" %
            aggregationMethod)

    if xFilesFactor is not None:
        #use specified xFilesFactor
        xff = struct.pack( floatFormat, float(xFilesFactor) )
    else:
	#retain old value
        xff = struct.pack( floatFormat, xff )

    #repack the remaining header information
    maxRetention = struct.pack( longFormat, maxRetention )
    archiveCount = struct.pack(longFormat, archiveCount)

    packedMetadata = newAggregationType + maxRetention + xff + archiveCount
    fh.seek(0)
    #fh.write(newAggregationType)
    fh.write(packedMetadata)

    if AUTOFLUSH:
      fh.flush()
      os.fsync(fh.fileno())

      if CACHE_HEADERS and fh.name in __headerCache:
        del __headerCache[fh.name]

  finally:
    if fh:
      fh.close()

  return aggregationTypeToMethod.get(aggregationType, 'average')


def validateArchiveList(archiveList):
  """ Validates an archiveList.
  An ArchiveList must:
  1. Have at least one archive config. Example: (60, 86400)
  2. No archive may be a duplicate of another.
  3. Higher precision archives' precision must evenly divide all lower precision archives' precision.
  4. Lower precision archives must cover larger time intervals than higher precision archives.
  5. Each archive must have at least enough points to consolidate to the next archive

  Returns True or False
  """

  if not archiveList:
    raise InvalidConfiguration("You must specify at least one archive configuration!")

  archiveList.sort(key=lambda a: a[0]) #sort by precision (secondsPerPoint)

  for i,archive in enumerate(archiveList):
    if i == len(archiveList) - 1:
      break

    nextArchive = archiveList[i+1]
    if not archive[0] < nextArchive[0]:
      raise InvalidConfiguration("A Whisper database may not configured having"
        "two archives with the same precision (archive%d: %s, archive%d: %s)" %
        (i, archive, i + 1, nextArchive))

    if nextArchive[0] % archive[0] != 0:
      raise InvalidConfiguration("Higher precision archives' precision "
        "must evenly divide all lower precision archives' precision "
        "(archive%d: %s, archive%d: %s)" %
        (i, archive[0], i + 1, nextArchive[0]))

    retention = archive[0] * archive[1]
    nextRetention = nextArchive[0] * nextArchive[1]

    if not nextRetention > retention:
      raise InvalidConfiguration("Lower precision archives must cover "
        "larger time intervals than higher precision archives "
        "(archive%d: %s seconds, archive%d: %s seconds)" %
        (i, retention, i + 1, nextRetention))

    archivePoints = archive[1]
    pointsPerConsolidation = nextArchive[0] / archive[0]
    if not archivePoints >= pointsPerConsolidation:
      raise InvalidConfiguration("Each archive must have at least enough points "
        "to consolidate to the next archive (archive%d consolidates %d of "
        "archive%d's points but it has only %d total points)" %
        (i + 1, pointsPerConsolidation, i, archivePoints))


def create(path,archiveList,xFilesFactor=None,aggregationMethod=None,sparse=False,useFallocate=False):
  """create(path,archiveList,xFilesFactor=0.5,aggregationMethod='average')

path is a string
archiveList is a list of archives, each of which is of the form (secondsPerPoint,numberOfPoints)
xFilesFactor specifies the fraction of data points in a propagation interval that must have known values for a propagation to occur
aggregationMethod specifies the function to use when propagating data (see ``whisper.aggregationMethods``)
"""
  # Set default params
  if xFilesFactor is None:
    xFilesFactor = 0.5
  if aggregationMethod is None:
    aggregationMethod = 'average'

  #Validate archive configurations...
  validateArchiveList(archiveList)

  #Looks good, now we create the file and write the header
  if os.path.exists(path):
    raise InvalidConfiguration("File %s already exists!" % path)
  fh = None
  try:
    fh = open(path,'wb')
    if LOCK:
      fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

    aggregationType = struct.pack( longFormat, aggregationMethodToType.get(aggregationMethod, 1) )
    oldest = max([secondsPerPoint * points for secondsPerPoint,points in archiveList])
    maxRetention = struct.pack( longFormat, oldest )
    xFilesFactor = struct.pack( floatFormat, float(xFilesFactor) )
    archiveCount = struct.pack(longFormat, len(archiveList))
    packedMetadata = aggregationType + maxRetention + xFilesFactor + archiveCount
    fh.write(packedMetadata)
    headerSize = metadataSize + (archiveInfoSize * len(archiveList))
    archiveOffsetPointer = headerSize

    for secondsPerPoint,points in archiveList:
      archiveInfo = struct.pack(archiveInfoFormat, archiveOffsetPointer, secondsPerPoint, points)
      fh.write(archiveInfo)
      archiveOffsetPointer += (points * pointSize)

    #If configured to use fallocate and capable of fallocate use that, else
    #attempt sparse if configure or zero pre-allocate if sparse isn't configured.
    if CAN_FALLOCATE and useFallocate:
      remaining = archiveOffsetPointer - headerSize
      fallocate(fh, headerSize, remaining)
    elif sparse:
      fh.seek(archiveOffsetPointer - 1)
      fh.write('\x00')
    else:
      remaining = archiveOffsetPointer - headerSize
      chunksize = 16384
      zeroes = '\x00' * chunksize
      while remaining > chunksize:
        fh.write(zeroes)
        remaining -= chunksize
      fh.write(zeroes[:remaining])

    if AUTOFLUSH:
      fh.flush()
      os.fsync(fh.fileno())
  finally:
    if fh:
      fh.close()

def aggregate(aggregationMethod, knownValues):
  if aggregationMethod == 'average':
    return float(sum(knownValues)) / float(len(knownValues))
  elif aggregationMethod == 'sum':
    return float(sum(knownValues))
  elif aggregationMethod == 'last':
    return knownValues[len(knownValues)-1]
  elif aggregationMethod == 'max':
    return max(knownValues)
  elif aggregationMethod == 'min':
    return min(knownValues)
  else:
    raise InvalidAggregationMethod("Unrecognized aggregation method %s" %
            aggregationMethod)


def __propagate(fh,header,timestamp,higher,lower):
  aggregationMethod = header['aggregationMethod']
  xff = header['xFilesFactor']

  lowerIntervalStart = timestamp - (timestamp % lower['secondsPerPoint'])
  lowerIntervalEnd = lowerIntervalStart + lower['secondsPerPoint']

  fh.seek(higher['offset'])
  packedPoint = fh.read(pointSize)
  (higherBaseInterval,higherBaseValue) = struct.unpack(pointFormat,packedPoint)

  if higherBaseInterval == 0:
    higherFirstOffset = higher['offset']
  else:
    timeDistance = lowerIntervalStart - higherBaseInterval
    pointDistance = timeDistance / higher['secondsPerPoint']
    byteDistance = pointDistance * pointSize
    higherFirstOffset = higher['offset'] + (byteDistance % higher['size'])

  higherPoints = lower['secondsPerPoint'] / higher['secondsPerPoint']
  higherSize = higherPoints * pointSize
  relativeFirstOffset = higherFirstOffset - higher['offset']
  relativeLastOffset = (relativeFirstOffset + higherSize) % higher['size']
  higherLastOffset = relativeLastOffset + higher['offset']
  fh.seek(higherFirstOffset)

  if higherFirstOffset < higherLastOffset: #we don't wrap the archive
    seriesString = fh.read(higherLastOffset - higherFirstOffset)
  else: #We do wrap the archive
    higherEnd = higher['offset'] + higher['size']
    seriesString = fh.read(higherEnd - higherFirstOffset)
    fh.seek(higher['offset'])
    seriesString += fh.read(higherLastOffset - higher['offset'])

  #Now we unpack the series data we just read
  byteOrder,pointTypes = pointFormat[0],pointFormat[1:]
  points = len(seriesString) / pointSize
  seriesFormat = byteOrder + (pointTypes * points)
  unpackedSeries = struct.unpack(seriesFormat, seriesString)

  #And finally we construct a list of values
  neighborValues = [None] * points
  currentInterval = lowerIntervalStart
  step = higher['secondsPerPoint']

  for i in xrange(0,len(unpackedSeries),2):
    pointTime = unpackedSeries[i]
    if pointTime == currentInterval:
      neighborValues[i/2] = unpackedSeries[i+1]
    currentInterval += step

  #Propagate aggregateValue to propagate from neighborValues if we have enough known points
  knownValues = [v for v in neighborValues if v is not None]
  if not knownValues:
    return False

  knownPercent = float(len(knownValues)) / float(len(neighborValues))
  if knownPercent >= xff: #we have enough data to propagate a value!
    aggregateValue = aggregate(aggregationMethod, knownValues)
    myPackedPoint = struct.pack(pointFormat,lowerIntervalStart,aggregateValue)
    fh.seek(lower['offset'])
    packedPoint = fh.read(pointSize)
    (lowerBaseInterval,lowerBaseValue) = struct.unpack(pointFormat,packedPoint)

    if lowerBaseInterval == 0: #First propagated update to this lower archive
      fh.seek(lower['offset'])
      fh.write(myPackedPoint)
    else: #Not our first propagated update to this lower archive
      timeDistance = lowerIntervalStart - lowerBaseInterval
      pointDistance = timeDistance / lower['secondsPerPoint']
      byteDistance = pointDistance * pointSize
      lowerOffset = lower['offset'] + (byteDistance % lower['size'])
      fh.seek(lowerOffset)
      fh.write(myPackedPoint)

    return True

  else:
    return False


def update(path,value,timestamp=None):
  """update(path,value,timestamp=None)

path is a string
value is a float
timestamp is either an int or float
"""
  value = float(value)
  fh = None
  try:
    fh = open(path,'r+b')
    return file_update(fh, value, timestamp)
  finally:
    if fh:
      fh.close()

def file_update(fh, value, timestamp):
  if LOCK:
    fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

  header = __readHeader(fh)
  now = int( time.time() )
  if timestamp is None:
    timestamp = now

  timestamp = int(timestamp)
  diff = now - timestamp
  if not ((diff < header['maxRetention']) and diff >= 0):
    raise TimestampNotCovered("Timestamp not covered by any archives in "
      "this database.")

  for i,archive in enumerate(header['archives']): #Find the highest-precision archive that covers timestamp
    if archive['retention'] < diff: continue
    lowerArchives = header['archives'][i+1:] #We'll pass on the update to these lower precision archives later
    break

  #First we update the highest-precision archive
  myInterval = timestamp - (timestamp % archive['secondsPerPoint'])
  myPackedPoint = struct.pack(pointFormat,myInterval,value)
  fh.seek(archive['offset'])
  packedPoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedPoint)

  if baseInterval == 0: #This file's first update
    fh.seek(archive['offset'])
    fh.write(myPackedPoint)
    baseInterval,baseValue = myInterval,value
  else: #Not our first update
    timeDistance = myInterval - baseInterval
    pointDistance = timeDistance / archive['secondsPerPoint']
    byteDistance = pointDistance * pointSize
    myOffset = archive['offset'] + (byteDistance % archive['size'])
    fh.seek(myOffset)
    fh.write(myPackedPoint)

  #Now we propagate the update to lower-precision archives
  higher = archive
  for lower in lowerArchives:
    if not __propagate(fh, header, myInterval, higher, lower):
      break
    higher = lower

  if AUTOFLUSH:
    fh.flush()
    os.fsync(fh.fileno())



def update_many(path,points):
  """update_many(path,points)

path is a string
points is a list of (timestamp,value) points
"""
  if not points: return
  points = [ (int(t),float(v)) for (t,v) in points]
  points.sort(key=lambda p: p[0],reverse=True) #order points by timestamp, newest first
  fh = None
  try:
    fh = open(path,'r+b')
    return file_update_many(fh, points)
  finally:
    if fh:
      fh.close()


def file_update_many(fh, points):
  if LOCK:
    fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

  header = __readHeader(fh)
  now = int( time.time() )
  archives = iter( header['archives'] )
  currentArchive = archives.next()
  currentPoints = []

  for point in points:
    age = now - point[0]

    while currentArchive['retention'] < age: #we can't fit any more points in this archive
      if currentPoints: #commit all the points we've found that it can fit
        currentPoints.reverse() #put points in chronological order
        __archive_update_many(fh,header,currentArchive,currentPoints)
        currentPoints = []
      try:
        currentArchive = archives.next()
      except StopIteration:
        currentArchive = None
        break

    if not currentArchive:
      break #drop remaining points that don't fit in the database

    currentPoints.append(point)

  if currentArchive and currentPoints: #don't forget to commit after we've checked all the archives
    currentPoints.reverse()
    __archive_update_many(fh,header,currentArchive,currentPoints)

  if AUTOFLUSH:
    fh.flush()
    os.fsync(fh.fileno())



def __archive_update_many(fh,header,archive,points):
  step = archive['secondsPerPoint']
  alignedPoints = [ (timestamp - (timestamp % step), value)
                    for (timestamp,value) in points ]
  alignedPoints = dict(alignedPoints).items() # Take the last val of duplicates
  #Create a packed string for each contiguous sequence of points
  packedStrings = []
  previousInterval = None
  currentString = ""
  for (interval,value) in alignedPoints:
    if (not previousInterval) or (interval == previousInterval + step):
      currentString += struct.pack(pointFormat,interval,value)
      previousInterval = interval
    else:
      numberOfPoints = len(currentString) / pointSize
      startInterval = previousInterval - (step * (numberOfPoints-1))
      packedStrings.append( (startInterval,currentString) )
      currentString = struct.pack(pointFormat,interval,value)
      previousInterval = interval
  if currentString:
    numberOfPoints = len(currentString) / pointSize
    startInterval = previousInterval - (step * (numberOfPoints-1))
    packedStrings.append( (startInterval,currentString) )

  #Read base point and determine where our writes will start
  fh.seek(archive['offset'])
  packedBasePoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedBasePoint)
  if baseInterval == 0: #This file's first update
    baseInterval = packedStrings[0][0] #use our first string as the base, so we start at the start

  #Write all of our packed strings in locations determined by the baseInterval
  for (interval,packedString) in packedStrings:
    timeDistance = interval - baseInterval
    pointDistance = timeDistance / step
    byteDistance = pointDistance * pointSize
    myOffset = archive['offset'] + (byteDistance % archive['size'])
    fh.seek(myOffset)
    archiveEnd = archive['offset'] + archive['size']
    bytesBeyond = (myOffset + len(packedString)) - archiveEnd

    if bytesBeyond > 0:
      fh.write( packedString[:-bytesBeyond] )
      assert fh.tell() == archiveEnd, "archiveEnd=%d fh.tell=%d bytesBeyond=%d len(packedString)=%d" % (archiveEnd,fh.tell(),bytesBeyond,len(packedString))
      fh.seek( archive['offset'] )
      fh.write( packedString[-bytesBeyond:] ) #safe because it can't exceed the archive (retention checking logic above)
    else:
      fh.write(packedString)

  #Now we propagate the updates to lower-precision archives
  higher = archive
  lowerArchives = [arc for arc in header['archives'] if arc['secondsPerPoint'] > archive['secondsPerPoint']]

  for lower in lowerArchives:
    fit = lambda i: i - (i % lower['secondsPerPoint'])
    lowerIntervals = [fit(p[0]) for p in alignedPoints]
    uniqueLowerIntervals = set(lowerIntervals)
    propagateFurther = False
    for interval in uniqueLowerIntervals:
      if __propagate(fh, header, interval, higher, lower):
        propagateFurther = True

    if not propagateFurther:
      break
    higher = lower


def info(path):
  """info(path)

path is a string
"""
  fh = None
  try:
    fh = open(path,'rb')
    return __readHeader(fh)
  finally:
    if fh:
      fh.close()
  return None

def fetch(path,fromTime,untilTime=None,now=None):
  """fetch(path,fromTime,untilTime=None)

path is a string
fromTime is an epoch time
untilTime is also an epoch time, but defaults to now.

Returns a tuple of (timeInfo, valueList)
where timeInfo is itself a tuple of (fromTime, untilTime, step)

Returns None if no data can be returned
"""
  fh = None
  try:
    fh = open(path,'rb')
    return file_fetch(fh, fromTime, untilTime, now)
  finally:
    if fh:
      fh.close()

def file_fetch(fh, fromTime, untilTime, now = None):
  header = __readHeader(fh)
  if now is None:
    now = int( time.time() )
  if untilTime is None:
    untilTime = now
  fromTime = int(fromTime)
  untilTime = int(untilTime)

  # Here we try and be flexible and return as much data as we can.
  # If the range of data is from too far in the past or fully in the future, we
  # return nothing
  if (fromTime > untilTime):
    raise InvalidTimeInterval("Invalid time interval: from time '%s' is after until time '%s'" % (fromTime, untilTime))

  oldestTime = now - header['maxRetention']
  # Range is in the future
  if fromTime > now:
    return None
  # Range is beyond retention
  if untilTime < oldestTime:
    return None
  # Range requested is partially beyond retention, adjust
  if fromTime < oldestTime:
    fromTime = oldestTime
  # Range is partially in the future, adjust
  if untilTime > now:
    untilTime = now

  diff = now - fromTime
  for archive in header['archives']:
    if archive['retention'] >= diff:
      break

  return __archive_fetch(fh, archive, fromTime, untilTime)

def __archive_fetch(fh, archive, fromTime, untilTime):
  """
Fetch data from a single archive. Note that checks for validity of the time
period requested happen above this level so it's possible to wrap around the
archive on a read and request data older than the archive's retention
"""
  fromInterval = int( fromTime - (fromTime % archive['secondsPerPoint']) ) + archive['secondsPerPoint']
  untilInterval = int( untilTime - (untilTime % archive['secondsPerPoint']) ) + archive['secondsPerPoint']
  fh.seek(archive['offset'])
  packedPoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedPoint)

  if baseInterval == 0:
    step = archive['secondsPerPoint']
    points = (untilInterval - fromInterval) / step
    timeInfo = (fromInterval,untilInterval,step)
    valueList = [None] * points
    return (timeInfo,valueList)

  #Determine fromOffset
  timeDistance = fromInterval - baseInterval
  pointDistance = timeDistance / archive['secondsPerPoint']
  byteDistance = pointDistance * pointSize
  fromOffset = archive['offset'] + (byteDistance % archive['size'])

  #Determine untilOffset
  timeDistance = untilInterval - baseInterval
  pointDistance = timeDistance / archive['secondsPerPoint']
  byteDistance = pointDistance * pointSize
  untilOffset = archive['offset'] + (byteDistance % archive['size'])

  #Read all the points in the interval
  fh.seek(fromOffset)
  if fromOffset < untilOffset: #If we don't wrap around the archive
    seriesString = fh.read(untilOffset - fromOffset)
  else: #We do wrap around the archive, so we need two reads
    archiveEnd = archive['offset'] + archive['size']
    seriesString = fh.read(archiveEnd - fromOffset)
    fh.seek(archive['offset'])
    seriesString += fh.read(untilOffset - archive['offset'])

  #Now we unpack the series data we just read (anything faster than unpack?)
  byteOrder,pointTypes = pointFormat[0],pointFormat[1:]
  points = len(seriesString) / pointSize
  seriesFormat = byteOrder + (pointTypes * points)
  unpackedSeries = struct.unpack(seriesFormat, seriesString)

  #And finally we construct a list of values (optimize this!)
  valueList = [None] * points #pre-allocate entire list for speed
  currentInterval = fromInterval
  step = archive['secondsPerPoint']

  for i in xrange(0,len(unpackedSeries),2):
    pointTime = unpackedSeries[i]
    if pointTime == currentInterval:
      pointValue = unpackedSeries[i+1]
      valueList[i/2] = pointValue #in-place reassignment is faster than append()
    currentInterval += step

  timeInfo = (fromInterval,untilInterval,step)
  return (timeInfo,valueList)

def merge(path_from, path_to):
  """ Merges the data from one whisper file into another. Each file must have
  the same archive configuration
"""
  fh_from = open(path_from, 'rb')
  fh_to = open(path_to, 'rb+')
  return file_merge(fh_from, fh_to)

def file_merge(fh_from, fh_to):
  headerFrom = __readHeader(fh_from)
  headerTo = __readHeader(fh_to)

  if headerFrom['archives'] != headerTo['archives']:
    raise NotImplementedError("%s and %s archive configurations are unalike. " \
    "Resize the input before merging" % (fh_from.name, fh_to.name))

  archives = headerFrom['archives']
  archives.sort(key=operator.itemgetter('retention'))

  now = int(time.time())
  untilTime = now
  for archive in archives:
    fromTime = now - archive['retention']
    (timeInfo, values) = __archive_fetch(fh_from, archive, fromTime, untilTime)
    (start, end, archive_step) = timeInfo
    pointsToWrite = list(itertools.ifilter(
      lambda points: points[1] is not None,
      itertools.izip(xrange(start, end, archive_step), values)))
    __archive_update_many(fh_to, headerTo, archive, pointsToWrite)
    untilTime = fromTime
  fh_from.close()
  fh_to.close()

def diff(path_from, path_to, ignore_empty = False):
  """ Compare two whisper databases. Each file must have the same archive configuration """
  fh_from = open(path_from, 'rb')
  fh_to = open(path_to, 'rb')
  diffs = file_diff(fh_from, fh_to, ignore_empty)
  fh_to.close()
  fh_from.close()
  return diffs

def file_diff(fh_from, fh_to, ignore_empty = False):
  headerFrom = __readHeader(fh_from)
  headerTo = __readHeader(fh_to)

  if headerFrom['archives'] != headerTo['archives']:
    # TODO: Add specific whisper-resize commands to right size things
    raise NotImplementedError("%s and %s archive configurations are unalike. " \
                                "Resize the input before diffing" % (fh_from.name, fh_to.name))

  archives = headerFrom['archives']
  archives.sort(key=operator.itemgetter('retention'))

  archive_diffs = []

  now = int(time.time())
  untilTime = now
  for archive_number, archive in enumerate(archives):
    diffs = []
    startTime = now - archive['retention']
    (fromTimeInfo, fromValues) = __archive_fetch(fh_from, archive, startTime, untilTime)
    (toTimeInfo, toValues) = __archive_fetch(fh_to, archive, startTime, untilTime)
    (start, end, archive_step) = ( min(fromTimeInfo[0],toTimeInfo[0]), max(fromTimeInfo[1],toTimeInfo[1]), min(fromTimeInfo[2],toTimeInfo[2]) )

    points = map(lambda s: (s * archive_step + start,fromValues[s],toValues[s]), range(0,(end - start) / archive_step))
    if ignore_empty:
      points = [p for p in points if p[1] != None and p[2] != None]
    else:
      points = [p for p in points if p[1] != None or p[2] != None]

    diffs = [p for p in points if p[1] != p[2]]

    archive_diffs.append( (archive_number, diffs, points.__len__()) )
    untilTime = startTime
  return archive_diffs

########NEW FILE########
