__FILENAME__ = gcdotlog_convert_relative_into_absolute_time
#!/usr/bin/python2.7

# $Id: //depot/cloud/rpms/nflx-webadmin-gcviz/root/apps/apache/htdocs/AdminGCViz/remote-data-collection/gcdotlog_convert_relative_into_absolute_time.py#2 $
# $DateTime: 2013/05/15 18:34:23 $
# $Change: 1838706 $
# $Author: mooreb $

import calendar
import fileinput
import math
import os
import sys
import time
import re

# Ugh.
sys.path.insert(0, "/apps/apache/htdocs/AdminGCViz")
import vmsgcvizutils   

def mayne():
    TMPFILE = '/tmp/gcdotlog-relative-time-tmpfile'
    numArgs = len(sys.argv) - 1
    if(2 != numArgs):
        print "Usage: %s {iso8601 combined date and time representations} outputdir" % (sys.argv[0],)
        sys.exit(1);

    bootTimeStringISO8601 = sys.argv[1]
    bootTimeSecondsSinceEpochString = vmsgcvizutils.timestamp_to_epoch(bootTimeStringISO8601)
    bootTimeSecondsSinceEpoch = float(bootTimeSecondsSinceEpochString)
    outputDir = sys.argv[2]
    bootTimeEpochFile = open(outputDir + '/jvm_boottime.epoch', 'w')
    bootTimeEpochFile.write("%s\n" % bootTimeSecondsSinceEpochString)
    bootTimeEpochFile.close()
    
    tmpFile = open(TMPFILE, 'w')
    lineStartsWithFloatingPointNumberPattern = re.compile("^([0-9]+[.][0-9]+): ")
    lastSecsSinceBoot = 0.0;
    for line in fileinput.input('-'):
        line = line.rstrip('\r\n')
        found = lineStartsWithFloatingPointNumberPattern.search(line)
        if found:
            secsSinceBootString = found.group(1)
            secsSinceBoot = float(secsSinceBootString)
            if secsSinceBoot < lastSecsSinceBoot:
                # now we need to truncate the output file, since we have
                # seen a restart; this is not the most recent JVM boot
                tmpFile.close()
                tmpFile = open(TMPFILE, 'w')
            lastSecsSinceBoot = secsSinceBoot
            timeStamp = vmsgcvizutils.convertTimeStamp(bootTimeSecondsSinceEpoch, secsSinceBoot)
            tmpFile.write("%s: %s\n" % (timeStamp, line))
        else:
            tmpFile.write("%s\n" % (line,))

    tmpFile.close()
    for line in fileinput.input(TMPFILE):
        line = line.rstrip('\r\n')
        print "%s" % (line,)

    os.unlink(TMPFILE)

if __name__ == "__main__":
    mayne()

########NEW FILE########
__FILENAME__ = parse-proc-pid-maps
#!/usr/bin/python2.7

# $Id: //depot/cloud/rpms/nflx-webadmin-gcviz/root/apps/apache/htdocs/AdminGCViz/remote-data-collection/parse-proc-pid-maps.py#2 $
# $DateTime: 2013/05/15 18:34:23 $
# $Change: 1838706 $
# $Author: mooreb $

import sys

def bytesToHumanReadable(n):
    kay = 1024
    meg = kay*1024
    gig = meg*1024
    if ((0 <= n) and (n < kay)):
        return "%d bytes" % n
    elif ((kay <= n) and (n < meg)):
        return "%.2fkb" % ((n+0.0)/kay)
    elif ((meg <= n) and (n < gig)):
        return "%.2fmb" % ((n+0.0)/meg)
    else:
        return "%.2fgb" % ((n+0.0)/gig)

def readfile(filename):
    segments = []
    numSegments=0L
    totalBytes=0L
    infile = open(filename, 'r')
    line = infile.readline()
    while line:
        line = line.rstrip()
        fields = line.split(None, 5)
        if 6 == len(fields):
            (memRange, perms, offset, dev, inode, pathname) = fields
        elif 5 == len(fields):
            (memRange, perms, offset, dev, inode) = fields
            pathname = ''
        else:
            raise Exception('cannot unpack %s' % (line,))
        (begin,end) = memRange.split('-')
        t = long(end, 16) - long(begin, 16)
        totalBytes = totalBytes + t
        numSegments = numSegments + 1
        x = (t, memRange, pathname)
        segments.append(x)
        line = infile.readline()
    print filename
    print "\tnum segments = %s" % (numSegments,)
    print "\ttotal bytes = %s (%s)" % (totalBytes, bytesToHumanReadable(totalBytes))
    for i in sorted(segments, key=lambda x: x[0], reverse=True):
        print "\t\t%12s bytes (%s) %33s %s" % (i[0], bytesToHumanReadable(i[0]), i[1], i[2])

readfile(sys.argv[1])

########NEW FILE########
__FILENAME__ = prepend_epoch
#!/usr/bin/python2.7

# $Id: //depot/cloud/rpms/nflx-webadmin-gcviz/root/apps/apache/htdocs/AdminGCViz/remote-data-collection/prepend_epoch.py#2 $
# $DateTime: 2013/05/15 18:34:23 $
# $Change: 1838706 $
# $Author: mooreb $

import fileinput
import sys

# Ugh.
sys.path.insert(0, "/apps/apache/htdocs/AdminGCViz")
import vmsgcvizutils   

def mayne():
    print "secs_since_epoch"
    for line in fileinput.input('-'):
        line = line.rstrip('\r\n')
        print "%s" % (vmsgcvizutils.timestamp_to_epoch(line),)

if __name__ == "__main__":
    mayne()

########NEW FILE########
__FILENAME__ = process_vms_object_cache_stats
#!/usr/bin/python2.7

# $Id: //depot/cloud/rpms/nflx-webadmin-gcviz/root/apps/apache/htdocs/AdminGCViz/remote-data-collection/process_vms_object_cache_stats.py#2 $
# $DateTime: 2013/05/15 18:34:23 $
# $Change: 1838706 $
# $Author: mooreb $

import fileinput
import os
import re
import sys

# Ugh.
sys.path.insert(0, "/apps/apache/htdocs/AdminGCViz")
import vmsgcvizutils   

numArgs = len(sys.argv) - 1
if(2 != numArgs):
    print "Usage: %s object-cache-stats-file outputdir" % (sys.argv[0],)
    sys.exit(1);

objectCacheStatsFile = sys.argv[1]
baseOutputDir = sys.argv[2]
outputDir = baseOutputDir + os.path.sep + 'vms-object-cache-stats-by-cache'
os.mkdir(outputDir)
outputFiles = {}
rejects = open(objectCacheStatsFile + '.rejects', 'w')

timestampPattern = re.compile('^([0-9]{4}-[0-9]{2}-[0-9]{2}) ([0-9]{2}:[0-9]{2}:[0-9]{2}),([0-9]{3}) INFO (main|vms-timer-refresh) VMClientCacheManager - Processed Countries')
objectCachePattern = re.compile('objectCache\(([^)]*)\) references\(([^)]*)\) size\(([^)]*)\) ratio\(([^)]*)\) prevsize\(([^)]*)\) additions\(([^)]*)\) transfers\(([^)]*)\) hits\(([^)]*)\) orphans\(([^)]*)\)')

header="secsSinceEpoch,iso8601Timestamp,references,size,ratio,prevsize,additions,transfers,hits,orphans\n"

iso8601Timestamp = "1970-01-01T00:00:00.000+0000"
secsSinceEpoch = "0.000"
for line in fileinput.input(objectCacheStatsFile):
    line = line.rstrip('\r\n')
    foundTimestamp = timestampPattern.search(line)
    if foundTimestamp:
        ymd = foundTimestamp.group(1)
        hms = foundTimestamp.group(2)
        milliseconds = foundTimestamp.group(3)
        iso8601Timestamp = '%sT%s.%s+0000' % (ymd,hms,milliseconds)
        secsSinceEpoch = vmsgcvizutils.timestamp_to_epoch(iso8601Timestamp)
        continue

    foundObjectCache = objectCachePattern.search(line)
    if foundObjectCache:
        cacheName  = foundObjectCache.group(1)
        references = foundObjectCache.group(2)
        size       = foundObjectCache.group(3)
        ratio      = foundObjectCache.group(4)
        prevsize   = foundObjectCache.group(5)
        additions  = foundObjectCache.group(6)
        transfers  = foundObjectCache.group(7)
        hits       = foundObjectCache.group(8)
        orphans    = foundObjectCache.group(9)
        l = "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (secsSinceEpoch,iso8601Timestamp,references,size,ratio,prevsize,additions,transfers,hits,orphans)
        f = outputFiles.get(cacheName)
        if f:
            f.write(l)
        else:
            f = open(outputDir + os.path.sep + cacheName, 'w')
            f.write(header)
            f.write(l)
            outputFiles[cacheName] = f
        continue
    else:
        rejects.write("%s\n" % (line,))

rejects.close()
for fp in outputFiles.values():
    fp.close()

########NEW FILE########
__FILENAME__ = vms_facet_info_transform
#!/usr/bin/python2.7

# $Id: //depot/cloud/rpms/nflx-webadmin-gcviz/root/apps/apache/htdocs/AdminGCViz/remote-data-collection/vms_facet_info_transform.py#2 $
# $DateTime: 2013/05/15 18:34:23 $
# $Change: 1838706 $
# $Author: mooreb $

import fileinput
import re

# Ugh.
sys.path.insert(0, "/apps/apache/htdocs/AdminGCViz")
import vmsgcvizutils   

# Input:
# 2012-03-30 00:47:11,771 country(GF) cache(VideoImages) numItems(24189) totalTime(1397531) timeToCopyToDisc(5550) timeToFill(1391981)
# ...
#
# Output
# seconds_since_epoch,datetimestamp,country,cache,numitems,totalTime,timeToCopyToDisc,timeToFill
# 1333068431.771,2012-03-30T00:47:11.771+0000,GF,VideoImages,24189,1397531,5550,1391981
# ...

facetPattern = re.compile('^([0-9]{4}-[0-9]{2}-[0-9]{2}) ([0-9]{2}:[0-9]{2}:[0-9]{2}),([0-9]{3}) country\(([A-Z]{2})\) cache\(([^)]+)\) numItems\(([0-9]+)\) totalTime\(([0-9]+)\) timeToCopyToDisc\(([0-9]+)\) timeToFill\(([0-9]+)\)$')

print 'seconds_since_epoch,datetimestamp,country,cache,numitems,totalTime,timeToCopyToDisc,timeToFill'
for line in fileinput.input('-'):
    line = line.rstrip('\r\n')
    found = facetPattern.search(line)
    if found:
        ymd = found.group(1)
        hms = found.group(2)
        milliseconds = found.group(3)
        iso8601Timestamp = '%sT%s.%s+0000' % (ymd,hms,milliseconds)
        secsSinceEpoch = vmsgcvizutils.timestamp_to_epoch(iso8601Timestamp)
        country = found.group(4)
        cache = found.group(5)
        numItems = found.group(6)
        totalTime = found.group(7)
        timeToCopyToDisc = found.group(8)
        timeToFill = found.group(9)
        print '%s,%s,%s,%s,%s,%s,%s,%s' % (secsSinceEpoch, iso8601Timestamp, country, cache, numItems, totalTime, timeToCopyToDisc, timeToFill)
    else:
        sys.stderr.write(line)

########NEW FILE########
__FILENAME__ = visualize-facets
#!/usr/bin/python2.7

# $Id: //depot/cloud/rpms/nflx-webadmin-gcviz/root/apps/apache/htdocs/AdminGCViz/visualize-facets.py#2 $
# $DateTime: 2013/05/15 18:34:23 $
# $Change: 1838706 $
# $Author: mooreb $

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import matplotlib.lines as lines
import pylab
import sys
import os
import vmsgcvizutils
from mpl_toolkits.mplot3d import Axes3D

numArgs = len(sys.argv) - 1
if(2 != numArgs):
    print "Usage: %s now:iso8601timestamp vms-gc-report-directory" % (sys.argv[0],)
    sys.exit(1);

now = sys.argv[1]
vmsGCReportDirectory = sys.argv[2]

# seconds_since_epoch,datetimestamp,country,cache,numitems,totalTime,timeToCopyToDisc,timeToFill
# 1333073736.242,2012-03-30T02:15:36.242+0000,BS,VideoEDFulfillmentData,23242,1352,757,595
fnameFullPath = vmsGCReportDirectory + os.path.sep + 'vms-cache-refresh-facet-info.csv'
recordset = mlab.csv2rec(fnameFullPath)

countries = recordset.country
countriesDict = {}
countriesList = []
countryNum = 0
for c in countries:
    cPrime = countriesDict.get(c)
    if cPrime:
        countriesList.append(cPrime)
    else:
        countryNum = countryNum + 1
        countriesDict[c] = countryNum
        countriesList.append(countryNum)

caches = recordset.cache
cachesDict = {}
cachesList = []
cacheNum = 0
for c in caches:
    cPrime = cachesDict.get(c)
    if cPrime:
        cachesList.append(cPrime)
    else:
        cacheNum = cacheNum + 1
        cachesDict[c] = cacheNum
        cachesList.append(cacheNum)

allTimeSpentInAllFacets = 0
perFacetRecordSets = []
facetEventByCacheDir = vmsGCReportDirectory + os.path.sep + 'facet-events-by-cache'
dirList=os.listdir(facetEventByCacheDir)
for fname in dirList:
    fnameFullPath = facetEventByCacheDir + os.path.sep + fname
    r = mlab.csv2rec(fnameFullPath)
    allTimeSpentInFacet = sum(r.totaltime)
    allTimeSpentInAllFacets = allTimeSpentInAllFacets + allTimeSpentInFacet
    timeToCopyFacetToDisc = sum(r.timetocopytodisc)
    timeToFillFacet = sum(r.timetofill)
    d = {'totaltime' : allTimeSpentInFacet, 
         'copytime'  : timeToCopyFacetToDisc,
         'filltime'  : timeToFillFacet,
         'facetName' : fname, 
         'recordset' : r}
    perFacetRecordSets.append(d)
perFacetRecordSets.sort(reverse=True, key=lambda d: d['totaltime']) # sort by all time spent in facet

facetReportFileName = vmsGCReportDirectory + os.path.sep + 'facet-report.txt'
facetReportFP = open(facetReportFileName, 'w')
for r in perFacetRecordSets:
    timeThisFacet = r['totaltime']
    s = '%10s milliseconds spent in %25s (%5.2f%%) {copy: %5.2f%%; fill: %5.2f%%}' % (
        timeThisFacet, 
        r['facetName'], 
        ((timeThisFacet*100.0)/allTimeSpentInAllFacets), 
        (r['copytime']*100.0/allTimeSpentInAllFacets), 
        (r['filltime']*100.0/allTimeSpentInAllFacets),
        )
    facetReportFP.write("%s\n" % (s,))
    print s
facetReportFP.close()

# BUG
sys.exit(0)

fig = plt.figure()
ax = fig.gca(projection='3d')
ax.plot(countriesList, recordset.totaltime/1000, zs=cachesList, zdir='z', marker='o')

ax.set_xlabel('country')
ax.set_ylabel('time to fill this country/facet (seconds)')
ax.set_zlabel('facet')
ax.set_title('total time to fill each facet for each country')

# BUG: save all generated figures.

plt.show()

# sort by total time descending:
#   sort -t , -k 6 -rn vms-cache-refresh-facet-info.csv | more

########NEW FILE########
__FILENAME__ = visualize-gc
#!/usr/bin/python2.7

# $Id: //depot/cloud/rpms/nflx-webadmin-gcviz/root/apps/apache/htdocs/AdminGCViz/visualize-gc.py#6 $
# $DateTime: 2013/11/12 19:42:41 $
# $Change: 2030932 $
# $Author: mooreb $

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import matplotlib.lines as lines
import pylab
import sys
import os
import vmsgcvizutils

def isNetflixInternal():
    try:
        open("/etc/profile.d/netflix_environment.sh", "r")
        return True
    except IOError:
        return False

numArgs = len(sys.argv) - 1
if(2 != numArgs):
    print "Usage: %s now:iso8601timestamp vms-gc-report-directory" % (sys.argv[0],)
    sys.exit(1);

now = sys.argv[1]
vmsGCReportDirectory = sys.argv[2]
gcEventDirectory = vmsGCReportDirectory + os.path.sep + 'gc-events-duration-by-event'

event_to_symbol_and_color = {
"FullGC"                            : ("mD", 15),  #(stop the world)
"concurrent-mode-failure"           : ("rh", 10),  #(stop the world)
"promotion-failed"                  : ("rH", 10),  #(stop the world)
"ParNew"                            : ("ro",  5),  #(stop-the-world)
"CMS-initial-mark"                  : ("r^",  5),  #(stop-the-world)
"CMS-remark"                        : ("rs",  5),  #(stop the world)
"CMS-concurrent-mark"               : ("g,",  1),  #(concurrent includes yields to other theads)
"CMS-concurrent-abortable-preclean" : ("g,",  1),  #(concurrent)
"CMS-concurrent-preclean"           : ("g,",  1),  #(concurrent)
"CMS-concurrent-sweep"              : ("g,",  1),  #(concurrent)
"CMS-concurrent-reset"              : ("g,",  1),  #(concurrent?)
"ParallelScavengeYoungGen"          : ("ro",  5),  #(stop-the-world)
"DefNew"                            : ("ro",  5),  #(stop-the-world)
"unknown"                           : ("r*",  15), #???
}

# These markers are present in gc.log but not accounted for above as they have no duration.
# They might be interesting to visualize but we currently minimize the CMS events anyway.
#   CMS-concurrent-mark-start
#   CMS-concurrent-preclean-start
#   CMS-concurrent-sweep-start
#   CMS-concurrent-reset-start
#   CMS-concurrent-abortable-preclean-start

## Read environmental information
def getSmallEnvDict():
    try:
        fullEnvDict = vmsgcvizutils.envFileAsDictionary(vmsGCReportDirectory + os.path.sep + 'env')
    except:
        fullEnvDict = {}
    smallEnvDict = {
        'ec2PublicHostname' : fullEnvDict.get('EC2_PUBLIC_HOSTNAME', 'no-public-hostname'),
        'instanceID'        : fullEnvDict.get('EC2_INSTANCE_ID', 'no-instance-id'),
        'instanceType'      : fullEnvDict.get('EC2_INSTANCE_TYPE', 'no-instance-type'),
        'appname'           : fullEnvDict.get('NETFLIX_APP', 'unknown-app'),
        'asg'               : fullEnvDict.get('NETFLIX_AUTO_SCALE_GROUP', 'unknown-asg'),
        'env'               : fullEnvDict.get('NETFLIX_ENVIRONMENT', 'unknown-env'),
    }
    return smallEnvDict
    

## Read GC event records, one file per type.
# The gc event records have this format:
#   secs_since_epoch,datetimestamp,secs_since_jvm_boot,gc_event_type,gc_event_duration_in_seconds
# for example:
#   1333055023.424,2012-03-29T21:03:43.424+0000,11.272,ParNew,0.19
# in numpy-speak:
#   dtype=[('secs_since_epoch', '<f8'), ('datetimestamp', '|O4'), ('secs_since_jvm_boot', '<f8'), ('gc_event_type', '|S33'), ('gc_event_duration_in_seconds', '<f8')])

dirList=os.listdir(gcEventDirectory)
recordsets = []
maxGCEventDuration = 0.0
maxSTWGCEventDuration = 0.0
for fname in dirList:
    fnameFullPath = gcEventDirectory + os.path.sep + fname
    print 'Reading %s' % (fnameFullPath,)
    (color, markersize) = event_to_symbol_and_color[fname]
    recordset = mlab.csv2rec(fnameFullPath)
    thisRecordsetMax = max(recordset.gc_event_duration_in_seconds)
    maxGCEventDuration = max(maxGCEventDuration, thisRecordsetMax)
    if color.startswith('r') or color.startswith('m'):
        maxSTWGCEventDuration = max(maxSTWGCEventDuration, thisRecordsetMax)
    mpldatenums = mdates.epoch2num(recordset.secs_since_epoch)
    tuple = (fname, recordset, mpldatenums, color, markersize)
    recordsets.append(tuple)

## Plot the GC event records
# example plots in:
#   http://matplotlib.sourceforge.net/gallery.html
#
# this one is particularly good:
#   http://matplotlib.sourceforge.net/examples/pylab_examples/usetex_demo.html
# BUG: add multiple plots. example in:
#   http://matplotlib.sourceforge.net/examples/pylab_examples/anscombe.html

fig = plt.figure()
# 1x1 grid = 1 row, 1 column. 2x3 grid = 2 rows, 3 columns. The third number starts from 1 and increments row-first. See documentation of subplot() for more info.
ax = fig.add_subplot(111)
locator = mdates.AutoDateLocator()
formatter = mdates.DateFormatter('%Y-%m-%d %H:%M:%SZ')
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(formatter)

for (dataname, dataset, mpldatenums, color, markersize) in recordsets:
    ax.plot(mpldatenums, dataset.gc_event_duration_in_seconds, color, label=dataname, ms=markersize, lw=markersize)

# draw the most recent jvm boot time line
fp = open(vmsGCReportDirectory + os.path.sep + 'jvm_boottime.epoch')
jvmBootEpoch = fp.readline()
jvmBootEpoch = jvmBootEpoch.rstrip('\r\n')
jvmBootDays = mdates.epoch2num(long(jvmBootEpoch))
jvmBootLine = lines.Line2D([jvmBootDays,jvmBootDays], [0,maxGCEventDuration], label='jvm boot time', linewidth=2)
ax.add_line(jvmBootLine)
fp.close()
fp = open(vmsGCReportDirectory + os.path.sep + 'jvm_boottime')
jvmBootTimestamp = fp.readline()
jvmBootTimestamp = jvmBootTimestamp.rstrip('\r\n')
fp.close()

# draw the vms cache refresh event lines if we're inside netflix
def try_to_draw_vms_cache_refresh_lines():
    if(isNetflixInternal()):
        try:
            fp = open(vmsGCReportDirectory + os.path.sep + 'vms-cache-refresh-overall-events-milliseconds')
        except IOError:
            return
        for line in fp:
            line = line.rstrip('\r\n')
            try:
                (finish_time_ms_str, duration_ms_str) = line.split()
            except ValueError:
                continue
            finish_time_ms = long(finish_time_ms_str)
            duration_ms = long(duration_ms_str)
            start_time_ms = finish_time_ms - duration_ms
            start_time_secs = start_time_ms/1000.0
            start_time_days = mdates.epoch2num(start_time_secs)
            start_time_line = lines.Line2D([start_time_days,start_time_days], [0,maxGCEventDuration], color='r')
            ax.add_line(start_time_line)
            finish_time_secs = finish_time_ms/1000.0
            finish_time_days = mdates.epoch2num(finish_time_secs)
            finish_time_line = lines.Line2D([finish_time_days,finish_time_days], [0,maxGCEventDuration], color='c')
            ax.add_line(finish_time_line)
        fp.close()
        # draw some fake lines just to get them into the legend
        fake_vms_start_line = lines.Line2D([jvmBootDays,0], [jvmBootDays,0], label='VMS cache refresh start', color='r')
        fake_vms_end_line = lines.Line2D([jvmBootDays,0], [jvmBootDays,0], label='VMS cache refresh end', color='c')
        ax.add_line(fake_vms_start_line)
        ax.add_line(fake_vms_end_line)

try_to_draw_vms_cache_refresh_lines()

# various chart options
smallEnvDict = getSmallEnvDict()
ax.set_title('gc events over time for %s %s %s %s %s %s' % (smallEnvDict['appname'], smallEnvDict['env'], smallEnvDict['ec2PublicHostname'], smallEnvDict['instanceID'], smallEnvDict['instanceType'], smallEnvDict['asg']))
ax.grid(True)
ax.set_xlabel('gc event start timestamp')
ax.set_ylabel('gc event duration (seconds)')
fig.autofmt_xdate()
plt.ylim([0,maxSTWGCEventDuration])
fig.set_size_inches(21,12)
pylab.figlegend(*ax.get_legend_handles_labels(), loc='lower center', ncol=5)

# BUG: add sar charts, including but not limited to cpu, network
# BUG: plot secs since jvm start
# BUG: visualize the facet data collected in vms-cache-refresh-facet-info.csv. Maybe leave this up to visualize-instance.

savedImageBaseFileName = vmsGCReportDirectory + os.path.sep + smallEnvDict['appname'] + '-gc-events-' + now
savedIamgeFileName = savedImageBaseFileName + '.png'
plt.savefig(savedIamgeFileName)
print "output on %s" % (savedIamgeFileName,)
savedIamgeFileName = savedImageBaseFileName + '.pdf'
plt.savefig(savedIamgeFileName)
print "output on %s" % (savedIamgeFileName,)

# Potential BUG: do we want to issue the plt.show()
plt.show()


heapSizesFileName = vmsGCReportDirectory + os.path.sep + 'gc-sizes.csv'
heapSizesRecordSet = mlab.csv2rec(heapSizesFileName)
heapSizesFig = plt.figure()
heapSizesAx = heapSizesFig.add_subplot(111)
heapSizesLocator = mdates.AutoDateLocator()
heapSizesFormatter = mdates.DateFormatter('%Y-%m-%d %H:%M:%SZ')
heapSizesAx.xaxis.set_major_locator(heapSizesLocator)
heapSizesAx.xaxis.set_major_formatter(heapSizesFormatter)

ONE_K   = 1024.0
ONE_MEG = 1024.0*1024.0
ONE_GIG = 1024.0*1024.0*1024.0

whole_heap_end_k_max = heapSizesRecordSet.whole_heap_end_k.max()
whole_heap_end_bytes_max = whole_heap_end_k_max* 1024.0

if (whole_heap_end_bytes_max < ONE_MEG):
    heap_end_units = "kilobytes"
    whole_heap_end = heapSizesRecordSet.whole_heap_end_k
elif ((ONE_MEG <= whole_heap_end_bytes_max) and (whole_heap_end_bytes_max < ONE_GIG)):
    heap_end_units = "megabytes"
    whole_heap_end = heapSizesRecordSet.whole_heap_end_k / ONE_K
elif (ONE_GIG <= whole_heap_end_bytes_max):
    heap_end_units = "gigabytes"
    whole_heap_end = heapSizesRecordSet.whole_heap_end_k / ONE_MEG
else:
    raise Exception("did not expect to get here")

heapSizesAx.plot(mdates.epoch2num(heapSizesRecordSet.secs_since_epoch), whole_heap_end, 'o')
heapSizesFig.autofmt_xdate()
heapSizesAx.set_title('heap size over time for %s %s %s %s %s %s' % (smallEnvDict['appname'], smallEnvDict['env'], smallEnvDict['ec2PublicHostname'], smallEnvDict['instanceID'], smallEnvDict['instanceType'], smallEnvDict['asg']))
heapSizesAx.grid(True)
heapSizesAx.set_xlabel('time')
heapSizesAx.set_ylabel('Total Heap Size After Collection (%s)' % (heap_end_units,))

heapSizesFig.set_size_inches(21,12)
heapSizesSavedImageBaseName = vmsGCReportDirectory + os.path.sep + smallEnvDict['appname'] + '-heap-size-' + now
fname = heapSizesSavedImageBaseName + '.png'
plt.savefig(fname)
print 'output on ' + fname
fname = heapSizesSavedImageBaseName + '.pdf'
plt.savefig(fname)
print 'output on ' + fname
plt.show()

########NEW FILE########
__FILENAME__ = vmsgcvizutils
#!/usr/bin/python2.7

# $Id: //depot/cloud/rpms/nflx-webadmin-gcviz/root/apps/apache/htdocs/AdminGCViz/vmsgcvizutils.py#3 $
# $DateTime: 2013/11/12 19:42:41 $
# $Change: 2030932 $
# $Author: mooreb $

import calendar
import math
import time
import re

def timestamp_to_epoch(timeStringISO8601):
    # Potential BUG: +0000 is hardcoded. I'd like to use %z but
    # cannot, as it's not supported by time.strptime and there's no
    # easy workaround: http://wiki.python.org/moin/WorkingWithTime
    secondFractionPattern = re.compile('([.][0-9]+)[+]0000')
    match = secondFractionPattern.search(timeStringISO8601)
    if match:
        fraction = match.group(1)
    else:
        fraction = ""
    timeStringISO8601 = timeStringISO8601.replace(fraction, '')
    # Potential BUG: +0000 is hardcoded. I'd like to use %z but
    # cannot, as it's not supported by time.strptime and there's no
    # easy workaround: http://wiki.python.org/moin/WorkingWithTime
    bootTimeTuple = time.strptime(timeStringISO8601, "%Y-%m-%dT%H:%M:%S+0000")
    bootTimeSecondsSinceEpoch = "%s" % calendar.timegm(bootTimeTuple)
    return (bootTimeSecondsSinceEpoch + fraction)

def convertTimeStamp(absoluteBaselineTime, secondsAfterBaseline):
    offsetTime = absoluteBaselineTime + secondsAfterBaseline
    offsetTimeTuple = time.gmtime(offsetTime)
    # Potential BUG: +0000 is hardcoded. I'd like to use %z but
    # cannot, as it's not supported by time.strptime and there's no
    # easy workaround: http://wiki.python.org/moin/WorkingWithTime
    offsetTimeString = time.strftime("%Y-%m-%dT%H:%M:%S+0000", offsetTimeTuple)
    fractionSecondsString = '%.3f' % (secondsAfterBaseline - math.floor(secondsAfterBaseline))
    retval = offsetTimeString.replace('+', fractionSecondsString[1:] + '+')
    return retval


def envFileAsDictionary(fname):
    retval = {}
    fp = open(fname, 'r')
    for line in fp:
        line = line.rstrip('\r\n')
        try:
            (k, v) = line.split('=', 1)
        except ValueError:
            continue
        retval[k] = v
    return retval

########NEW FILE########
