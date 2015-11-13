__FILENAME__ = ganglialog
#!/usr/bin/python

import sys
import syslog
import os
import urllib
import urllib2
import base64

########################################################################
# Make sure you change base Ganglia URL
########################################################################
ganglia_events_url = "<%= @ganglia_base_url %>/api/events.php"

# Optionally set user name and password
#username = "<%= @username %>"
#password = "<%= @password %>"

if (len(sys.argv) == 1):
  print "\nPlease supply a log message. It can be any number of arguments. Exiting....\n"
  exit(1)

for index in range(1,len(sys.argv)):
    print sys.argv[index]

# Log to syslog
syslog.syslog(" ".join(sys.argv))

# Remove first argument and join the list of arguments so it can be sent
summary = " ".join(sys.argv[1:])

# Get hostname
uname=os.uname()
hostname=uname[1]

params = urllib.urlencode({'action': 'add', 'start_time': 'now',
    'host_regex': hostname, 'summary': summary})

request = urllib2.Request(ganglia_events_url+ "?%s" % params)

if 'username' in locals():
  base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
  request.add_header("Authorization", "Basic %s" % base64string)   

f = urllib2.urlopen(request)

print f.read()
########NEW FILE########
__FILENAME__ = ApacheLogtailer
# -*- coding: utf-8 -*-
###
###  This plugin for logtailer will crunch apache logs and produce these metrics:
###    * hits per second
###    * GETs per second
###    * average query processing time
###    * ninetieth percentile query processing time
###    * number of HTTP 200, 300, 400, and 500 responses per second
###
###  Note that this plugin depends on a certain apache log format, documented in
##   __init__.

import time
import threading
import re

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class ApacheLogtailer(object):
    # only used in daemon mode
    period = 30
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.reset_state()
        self.lock = threading.RLock()
        # this is what will match the apache lines
        # apache log format string:
        # %v %A %a %u %{%Y-%m-%dT%H:%M:%S}t %c %s %>s %B %D %{cookie}n \"%{Referer}i\" \"%r\" \"%{User-Agent}i\" %P
        # host.com 127.0.0.1 127.0.0.1 - 2008-05-08T07:34:44 - 200 200 371 103918 - "-" "GET /path HTTP/1.0" "-" 23794
        # match keys: server_name, local_ip, remote_ip, date, conn_status, init_retcode, final_retcode, size,
        #               req_time, cookie, referrer, request, user_agent, pid
        self.reg = re.compile('^(?P<server_name>[^ ]+) (?P<local_ip>[^ ]+) (?P<remote_ip>[^ ]+) (?P<user>[^ ]+) (?P<date>[^ ]+) (?P<conn_status>[^ ]+) (?P<init_retcode>[^ ]+) (?P<final_retcode>[^ ]+) (?P<size>[^ ]+) (?P<req_time>[^ ]+) (?P<cookie>[^ ]+) "(?P<referrer>[^"]+)" "(?P<request>[^"]+)" "(?P<user_agent>[^"]+)" (?P<pid>[^ ]+)')

        # assume we're in daemon mode unless set_check_duration gets called
        self.dur_override = False


    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        self.num_hits+=1
        try:
            regMatch = self.reg.match(line)
            if regMatch:
                linebits = regMatch.groupdict()
                # capture GETs
                if( 'GET' in linebits['request'] ):
                    self.num_gets+=1
                # capture HTTP response code
                rescode = float(linebits['init_retcode'])
                if( (rescode >= 200) and (rescode < 300) ):
                    self.num_two+=1
                elif( (rescode >= 300) and (rescode < 400) ):
                    self.num_three+=1
                elif( (rescode >= 400) and (rescode < 500) ):
                    self.num_four+=1
                elif( (rescode >= 500) and (rescode < 600) ):
                    self.num_five+=1
                # capture request duration
                dur = float(linebits['req_time'])
                # convert to seconds
                dur = dur / 1000000
                self.req_time += dur
                # store for 90th % calculation
                self.ninetieth.append(dur)
            else:
                raise LogtailerParsingException, "regmatch failed to match"
        except Exception, e:
            self.lock.release()
            raise LogtailerParsingException, "regmatch or contents failed with %s" % e
        self.lock.release()
    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        myret = dict( num_hits=self.num_hits,
                    num_gets=self.num_gets,
                    req_time=self.req_time,
                    num_two=self.num_two,
                    num_three=self.num_three,
                    num_four=self.num_four,
                    num_five=self.num_five,
                    ninetieth=self.ninetieth
                    )
        return myret
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.num_hits = 0
        self.num_gets = 0
        self.req_time = 0
        self.num_two = 0
        self.num_three = 0
        self.num_four = 0
        self.num_five = 0
        self.ninetieth = list()
        self.last_reset_time = time.time()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur 
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # crunch data to how you want to report it
        hits_per_second = mydata['num_hits'] / check_time
        gets_per_second = mydata['num_gets'] / check_time
        if (mydata['num_hits'] != 0):
             avg_req_time = mydata['req_time'] / mydata['num_hits']
        else:
             avg_req_time = 0
        two_per_second = mydata['num_two'] / check_time
        three_per_second = mydata['num_three'] / check_time
        four_per_second = mydata['num_four'] / check_time
        five_per_second = mydata['num_five'] / check_time

        # calculate 90th % request time
        ninetieth_list = mydata['ninetieth']
        ninetieth_list.sort()
        num_entries = len(ninetieth_list)
        if (num_entries != 0 ):
             ninetieth_element = ninetieth_list[int(num_entries * 0.9)]
        else:
             ninetieth_element = 0

        # package up the data you want to submit
        hps_metric = GangliaMetricObject('apache_hits', hits_per_second, units='hps')
        gps_metric = GangliaMetricObject('apache_gets', gets_per_second, units='hps')
        avgdur_metric = GangliaMetricObject('apache_avg_dur', avg_req_time, units='sec')
        ninetieth_metric = GangliaMetricObject('apache_90th_dur', ninetieth_element, units='sec')
        twops_metric = GangliaMetricObject('apache_200', two_per_second, units='hps')
        threeps_metric = GangliaMetricObject('apache_300', three_per_second, units='hps')
        fourps_metric = GangliaMetricObject('apache_400', four_per_second, units='hps')
        fiveps_metric = GangliaMetricObject('apache_500', five_per_second, units='hps')

        # return a list of metric objects
        return [ hps_metric, gps_metric, avgdur_metric, ninetieth_metric, twops_metric, threeps_metric, fourps_metric, fiveps_metric, ]




########NEW FILE########
__FILENAME__ = ApacheVHostLogtailer
###
###  This plugin for logtailer will crunch apache logs and return the following
###  metrics for each vhost that has received more than 5% of the hits in the
###  sampling period.  All other vhosts will be combined and their metrics will
###  be returned as "other".  The metrics for each vhost/other are:
###    * number of hits
###    * number of GET requests
###    * average duration of each hit
###    * 90th percentile of hit durations
###    * maximum hit duration
###    * number of HTTP 200-299 responses
###    * number of HTTP 300-399 responses
###    * number of HTTP 400-499 responses
###    * number of HTTP 500-599 responses
###

import time
import threading
import re
import copy

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class ApacheVHostLogtailer(object):
    # only used in daemon mode
    period = 30
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.reset_state()
        self.lock = threading.RLock()

        # Dict for containing stats on each vhost
        self.stats = {}

        # A vhost must receive at least this % of the hits to be broken out from 'other'
        self.percentToBeHot = 0.05

        # this is what will match the apache lines
        apacheLogFormat = '%v %P %u %{%Y-%m-%dT%H:%M:%S}t %D %s %>s %I %O %B %a \"%{X-Forwarded-For}i\" \"%r\".*'
        self.reg = re.compile(self.apacheLogToRegex(apacheLogFormat))

        # assume we're in daemon mode unless set_check_duration gets called
        self.dur_override = False


    def apacheLogToRegex(self, logFormat):
        logFormatDict = {'%v':      '(?P<server_name>[^ ]+)',
            '%h':                   '(?P<remote_host>[^ ]+)',
            '%a':                   '(?P<remote_ip>[^ ]+)',
            '%P':                   '(?P<pid>[^ ]+)',           # PID
            '%u':                   '(?P<auth_user>[^ ]+)',     # HTTP-auth username
            '%t':                   '\[(?P<date>[^\]]+)\]',     # default date format
            '%{%Y-%m-%dT%H:%M:%S}t':'(?P<date>[^ ]+)',          # custom date format
            '%D':                   '(?P<req_time>[^ ]+)',      # req time in microsec
            '%s':                   '(?P<retcode>[^ ]+)',       # initial response code
            '%>s':                  '(?P<final_retcode>[^ ]+)', # final response code
            '%b':                   '(?P<req_size_clf>[^ ]+)',  # request size in bytes in CLF
            '%B':                   '(?P<req_size>[^ ]+)',      # req size in bytes
            '%I':                   '(?P<req_size_wire>[^ ]+)', # req size in bytes on the wire (+SSL, +compression)
            '%O':                   '(?P<resp_size_wire>[^ ]+)',# response size in bytes
            '%X':                   '(?P<conn_status>[^ ]+)',   # connection status
            '\"%r\"':               '"(?P<request>[^"]+)"',     # request (GET / HTTP/1.0)
            '\"%q\"':               '"(?P<query_string>[^"]+)"',# the query string
            '\"%U\"':               '"(?P<url>[^"]+)"',         # the URL requested
            '\"%{X-Forwarded-For}i\"': '"(?P<xfwd_for>[^"]+)"', # X-Forwarded-For header
            '\"%{Referer}i\"':      '"(?P<referrer>[^"]+)"',
            '\"%{User-Agent}i\"':   '"(?P<user_agent>[^"]+)"',
            '%{cookie}n':           '(?P<cookie>[^ ]+)'}

        for (search, replace) in logFormatDict.iteritems():
            logFormat = logFormat.replace(search, replace)

        return "^%s$" % logFormat


    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        
        try:
            regMatch = self.reg.match(line)
        except Exception, e:
            self.lock.release()
            raise LogtailerParsingException, "regmatch or contents failed with %s" % e
        
        if regMatch:
            lineBits = regMatch.groupdict()

            # For brevity, pull out the servername from the line list
            server_name = lineBits['server_name']
            
            # Make this server_name a key for an empty dict if we have
            # never seen it before.
            self.stats[server_name] = \
                self.stats.get(server_name, self.getBlankStats())

            self.stats[server_name]['num_hits'] += 1

            if( 'GET' in lineBits['request'] ):
                self.stats[server_name]['num_gets'] += 1

            rescode = int(lineBits['final_retcode'])
            if( (rescode >= 200) and (rescode < 300) ):
                self.stats[server_name]['num_200'] += 1
            elif( (rescode >= 300) and (rescode < 400) ):
                self.stats[server_name]['num_300'] += 1
            elif( (rescode >= 400) and (rescode < 500) ):
                self.stats[server_name]['num_400'] += 1
            elif( (rescode >= 500) and (rescode < 600) ):
                self.stats[server_name]['num_500'] += 1
            
            # capture request duration
            req_time = float(lineBits['req_time'])
            # convert to seconds
            req_time = req_time / 1000000
            # Add up the req_time in the req_time_avg field, we'll divide later
            self.stats[server_name]['req_time_avg'] += req_time
            
            # store for 90th % calculation
            self.stats[server_name]['req_time_90th_list'].append(req_time)
        else:
            raise LogtailerParsingException, "regmatch failed to match"
        
        self.lock.release()
    

    # Returns a dict of zeroed stats
    def getBlankStats(self):
        '''This function returns a dict of all the stats we\'d want for
        a vhost, zereod out.  This helps avoid undeclared keys when
        traversing the dictionary.'''

        blankData = {'num_hits':        0,
                     'num_gets':        0,
                     'num_200':         0,
                     'num_300':         0,
                     'num_400':         0,
                     'num_500':         0,
                     'req_time_avg':    0,
                     'req_time_90th_list': [],
                     'req_time_90th':   0,
                     'req_time_max':    0}
        
        return blankData
    
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        
        self.stats = {}
        self.last_reset_time = time.time()
    
    
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur 
        self.dur_override = True
    
    
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if (self.dur_override):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    
    
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = copy.deepcopy(self.stats)
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e
        
        combined = {}       # A dict containing stats for broken out & 'other' vhosts
        results  = []       # A list for all the Ganglia Log objects

        # For each "hot" vhost, and for the rest cumulatively, we want to gather:
        # - num hits
        # - num gets
        # - request time: average, max, 90th %
        # - response codes: 200, 300, 400, 500
        
        # Create an 'other' group for non-hot-vhosts
        combined['other'] = self.getBlankStats()

        # Calculate the minimum # of hits that a vhost needs to get broken out
        # from 'other'
        totalHits = 0
        
        #print mydata
        
        for vhost, stats in mydata.iteritems():
            totalHits += stats['num_hits']
        numToBeHot = totalHits * self.percentToBeHot
        
        otherCount = 0

        for vhost, stats in mydata.iteritems():
            # see if this is a 'hot' vhost, or an 'other'
            if stats['num_hits'] >= numToBeHot:
                key = vhost
                combined[key] = self.getBlankStats()
            else:
                otherCount += 1
                key = 'other'
            
            # Calculate statistics over time & number of hits
            if check_time > 0:
                combined[key]['num_hits'] += stats['num_hits'] / check_time
                combined[key]['num_gets'] += stats['num_gets'] / check_time
                combined[key]['num_200']  += stats['num_200']  / check_time
                combined[key]['num_300']  += stats['num_300']  / check_time
                combined[key]['num_400']  += stats['num_400']  / check_time
                combined[key]['num_500']  += stats['num_500']  / check_time
            if stats['num_hits'] > 0:
                combined[key]['req_time_avg'] = stats['req_time_avg'] / stats['num_hits']

            # calculate 90th % request time
            ninetieth_list = stats['req_time_90th_list']
            ninetieth_list.sort()
            num_entries = len(ninetieth_list)
            try:
                combined[key]['req_time_90th'] += ninetieth_list[int(num_entries * 0.9)]
                # Use this check so that we get the biggest value from all 'other's
                if ninetieth_list[-1] > combined[key]['req_time_max']:
                    combined[key]['req_time_max'] = ninetieth_list[-1]
            except IndexError:
                combined[key]['req_time_90th'] = 0
                combined[key]['req_time_max'] = 0

        # The req_time_90th field for the "other" vhosts is now a sum. Need to
        # divide by the number of "other" vhosts
        if otherCount > 0:
            combined['other']['req_time_90th'] /= (otherCount * 1.0)
        else:
            combined['other']['req_time_90th'] = 0

        for vhost, stats in combined.iteritems():
            #print vhost
            #print "\t", stats

            # skip empty vhosts
            if stats['num_hits'] == 0:
                continue

            # package up the data you want to submit
            results.append(GangliaMetricObject('apache_%s_hits' % vhost, stats['num_hits'], units='hps'))
            results.append(GangliaMetricObject('apache_%s_gets' % vhost, stats['num_gets'], units='hps'))
            results.append(GangliaMetricObject('apache_%s_dur_avg' % vhost, stats['req_time_avg'], units='sec'))
            results.append(GangliaMetricObject('apache_%s_dur_90th' % vhost, stats['req_time_90th'], units='sec'))
            results.append(GangliaMetricObject('apache_%s_dur_max' % vhost, stats['req_time_max'], units='sec'))
            results.append(GangliaMetricObject('apache_%s_200' % vhost, stats['num_200'], units='hps'))
            results.append(GangliaMetricObject('apache_%s_300' % vhost, stats['num_300'], units='hps'))
            results.append(GangliaMetricObject('apache_%s_400' % vhost, stats['num_400'], units='hps'))
            results.append(GangliaMetricObject('apache_%s_500' % vhost, stats['num_500'], units='hps'))

        # return a list of metric objects
        return results

########NEW FILE########
__FILENAME__ = BindLogtailer
###
###  This plugin for logtailer crunches bind's log and produces these metrics:
###    * queries per second
###    * number of unique clients seen in the sampling period, normalized over
###      the sampling time
###    * number of requests by the client that made the most requests
###

import time
import threading
import re

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class BindLogtailer(object):
    # only used in daemon mode
    period = 30.0
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.reset_state()
        self.lock = threading.RLock()
        # this is what will match the backbone lines
        # backbone log example:
        # Sep 11 09:03:05 ns0-sfo.lindenlab.com named[577]: client 80.189.94.233#49199: query: secondlife.com IN A
        # match keys: client_ip
        self.reg = re.compile('^.*named.*client (?P<client_ip>[0-9\.]+).*query')

        # assume we're in daemon mode unless set_check_duration gets called
        self.dur_override = False


    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        try:
            regMatch = self.reg.match(line)
            if regMatch:
                linebits = regMatch.groupdict()
                self.num_hits+=1
                self.client_ip_list.append(linebits['client_ip'])
            else:
                # this occurs for every non-named query line.  Ignore them.
                #raise LogtailerParsingException, "regmatch failed to match line (%s)" % line
                pass
        except Exception, e:
            self.lock.release()
            raise LogtailerParsingException, "regmatch or contents failed with %s" % e
        self.lock.release()
    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        myret = dict( num_hits=self.num_hits,
                      client_ip_list=self.client_ip_list,
                    )
        return myret
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.num_hits = 0
        self.last_reset_time = time.time()
        self.client_ip_list = list()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur 
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # crunch data to how you want to report it
        queries_per_second = mydata['num_hits'] / check_time

        # calculate number of querying IPs and maximum number of queries per IP
        clist = mydata['client_ip_list']

        cdict = dict()
        for elem in clist:
            cdict[elem] = cdict.get(elem,0) + 1

        # number of unique clients connecting, normalized to per minute
        num_client_ips = len(cdict) / check_time
        # number of requests issued by the client making the most
        max_client_ip_count = max(cdict.values()) / check_time


        # package up the data you want to submit
        qps_metric = GangliaMetricObject('bind_queries', queries_per_second, units='qps')
        clients_metric = GangliaMetricObject('bind_num_clients', num_client_ips, units='cps')
        max_reqs_metric = GangliaMetricObject('bind_largest_volume_client', max_client_ip_count, units='qps')

        # return a list of metric objects
        return [ qps_metric, clients_metric, max_reqs_metric, ]




########NEW FILE########
__FILENAME__ = DummyLogtailer
###
###   a 'metric object' is an instance of GangliaMetricObject
###       { 'name' => 'name-of-metric',
###         'value' => numerical-or-string-value,
###         'type' => 'int32',    <--- see gmetric man page for valid types
###         'units' => 'qps',     <--- label on the graph
###         }
###   This object should appear remarkably similar to the required arguments to gmetric.
###
###
###   The logtailer class must define
###     a class variable 'period'
###     an instance method set_check_duration that sets the time since last invocation (used in cron mode)
###     an instance method get_state() that returns a list of metric objects
###     an instance method parse_line(line) that takes one line of the log file and does whatever internal accounting is necessary to record its metrics
###   The logtailer class must be thread safe - a separate thread will be calling get_state() and parse_line(line)
###   parse_line(line) may raise a LogtailerParsingException to log an error and discard the current line but keep going.  Any other exception will kill the process.
###

import time
import threading

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class DummyLogtailer(object):
    # period must be defined and indicates how often the gmetric thread should call get_state() (in seconds) (in daemon mode only)
    # note that if period is shorter than it takes to run get_state() (if there's lots of complex calculation), the calling thread will automatically double period.
    # period ought to be >=5.  It should probably be >=60 (to avoid excessive load).  120 to 300 is a good range (2-5 minutes).  Take into account the need for time resolution, as well as the number of hosts reporting (6000 hosts * 15s == lots of data).
    period = 5
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.dur_override = False
        self.reset_state()
        self.lock = threading.RLock()

    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        self.num_lines+=1
        self.lock.release()
    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        return [ self.num_lines, ]
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.num_lines = 0
        self.last_reset_time = time.time()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # crunch data to how you want to report it
        lines_per_second = mydata[0] / check_time

        # package up the data you want to submit
        lps_metric = GangliaMetricObject('num_lines', lines_per_second, units='lps', type="float")
        # return a list of metric objects
        return [ lps_metric, ]




########NEW FILE########
__FILENAME__ = ganglia_logtailer_helper
#!/usr/bin/python
"""class for ganglia metric objects to be passed around"""
import re

class GangliaMetricObject(object):
    def __init__(self, name, value, units='', type='float', tmax=60, dmax=0):
        self.name = name
        self.value = value
        self.units = units
        self.type = type
        self.tmax = tmax
        self.dmax = dmax
    def set_value(self, value):
        self.value = value
    def dump_dict(self):
        """serialize this object to a dictionary"""
        return self.__dict__
    def set_from_dict(self, hashed_object):
        """recreate object from dict"""
        self.name = hashed_object["name"]
        self.value = hashed_object["value"]
        self.units = hashed_object["units"]
        self.type = hashed_object["type"]
        self.tmax = hashed_object["tmax"]
        self.dmax = hashed_object["dmax"]
    def sanitize_metric_name(self):
        """sanitize metric names by translating all non alphanumerics to underscore"""
        self.name = re.sub("[^A-Za-z0-9._-]", "_", self.name)
    def __eq__(self, other):
        """A ganglia metric object is equivalent if the name is the same."""
        return self.name == other.name

class LogtailerParsingException(Exception):
    """Raise this exception if the parse_line function wants to
        throw a 'recoverable' exception - i.e. you want parsing
        to continue but want to skip this line and log a failure."""
    pass

class LogtailerStateException(Exception):
    """Raise this exception if the get_state function has failed.  Metrics from
       this run will not be submitted (since the function did not properly
       return), but reset_state() should have been called so that the metrics
       are valid next time."""
    pass

class SavedMetricsException(Exception):
    """Raise this exception if there's a problem recovering the saved metric
        list from the statedir. This will always happen on the first run, and
        should be ignored. On subsequent runs, it probably means a config
        problem where the statedir can't be written or something."""
    pass

class LockingError(Exception):
    """ Exception raised for errors creating or destroying lockfiles. """

    def __init__(self, message):
        self.message = message



########NEW FILE########
__FILENAME__ = HAProxyLogtailer
import time
import threading
import re
import copy

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class HAProxyLogtailer(object):
    # only used in daemon mode
    period = 30
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.lock = threading.RLock()

        # example:
        # Jan 24 20:17:25 localhost haproxy[6844]: 127.0.0.1:39747 [24/Jan/2014:20:17:25.210] apps apps/app711 0/0/0/156/156 200 602 - - ---- 169/166/166/0/0 0/0 "POST /1/comm HTTP/1.0"
        # Jan 24 20:17:25 localhost haproxy[6844]: 127.0.0.1:45684 [24/Jan/2014:20:17:25.357] rails rails/rails2 0/0/3/6/10 200 900 - - ---- 168/2/2/0/0 0/0 "GET / HTTP/1.0"
        # things we're looking for:
        # global active connection count (168/169 in these examples) (min/max/avg)
        # global hit count
        # per-listener feconn and beconn (the second and third numbers in the second #/#/#/#/# stanza) (min/max/avg)
        # per-listener hit count
        # per-listener latency metrics - total connection time (Tt) metric (the last number in the first #/#/#/#/# stanza) (min/max/avg/50th/90th)
        # per-listener per-response code hit count (group hundreds, eg 4xx, 3xx)
        logformat = '^(?P<date1>... .. ..:..:..) (?P<hostname>[^ ]*) haproxy\[(?P<pid>\d+)\]: (?P<ipaddr>[0-9.]+):(?P<port>\d+) '
        logformat += '(?P<date2>[^ ]+) (?P<frontend>[^ ]+) (?P<backend>[^ ]+)/(?P<server>[^ ]+) '
        logformat += '(?P<tq>\d+)/(?P<tw>\d+)/(?P<tc>\d+)/(?P<tr>\d+)/(?P<tt>\d+) '
        logformat += '(?P<response_code>\d+) (?P<bytes>\d+) - - ---- '
        logformat += '(?P<actconn>\d+)/(?P<feconn>\d+)/(?P<beconn>\d+)/(?P<srvconn>\d+)/(?P<retries>\d+) (?P<srvqueue>\d+)/(?P<bequeue>\d+) '
        logformat += '(?P<request>.*)$'
        self.reg = re.compile(logformat)

        self.metricshash = {}
        self.global_actconn = [] #this is a list of active connections, from which we calculate min/max/avg at the end
        self.global_hits = 0
        self.listeners = {}
        self.response_codes = ['2xx', '3xx', '4xx', '5xx', 'other']
        # example substructure
        # listeners["parse.com"] = {}
        # # hit count is the length of any of these three arrays; they should all be the same
        # listeners["parse.com"]["latency"] = []
        # listeners["parse.com"]["feconn"] = []
        # listeners["parse.com"]["beconn"] = []
        # listeners["parse.com"]["responses"] = {'2xx':[], '3xx':[], '4xx':[], '5xx':[]}

        #print logformat
        # assume we're in daemon mode unless set_check_duration gets called
        self.dur_override = False
        self.reset_state()

    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()

        reg = self.reg
        try:
            regMatch = reg.match(line)
        except Exception, e:
            self.lock.release()
            # this happens a lot in this file, just return and go on to the next line.
            return

        if regMatch:
            lineBits = regMatch.groupdict()
            self.global_hits += 1
            self.global_actconn.append(int(lineBits['actconn']))

            if lineBits['response_code'].startswith('2'):
                response_code = "2xx"
            elif lineBits['response_code'].startswith('3'):
                response_code = "3xx"
            elif lineBits['response_code'].startswith('4'):
                response_code = "4xx"
            elif lineBits['response_code'].startswith('5'):
                response_code = "5xx"
            else:
                response_code = "other"

            try:
                self.listeners[lineBits['frontend']]['latency'].append(int(lineBits['tt']))
            except KeyError:
                # first time seeing this listener; create the data structure
                self.listeners[lineBits['frontend']] = {}
                self.listeners[lineBits['frontend']]["name"] = lineBits['frontend']
                self.listeners[lineBits['frontend']]["latency"] = []
                self.listeners[lineBits['frontend']]["feconn"] = []
                self.listeners[lineBits['frontend']]["beconn"] = []
                self.listeners[lineBits['frontend']]["responses"] = {}
                for code in self.response_codes:
                    self.listeners[lineBits['frontend']]["responses"][code] = 0
                # ok, now re-add the entry
                self.listeners[lineBits['frontend']]['latency'].append(int(lineBits['tt']))
            self.listeners[lineBits['frontend']]["feconn"].append(int(lineBits['feconn']))
            self.listeners[lineBits['frontend']]["beconn"].append(int(lineBits['beconn']))
            self.listeners[lineBits['frontend']]["responses"][response_code] += 1

        else:
            self.lock.release()
            return

        self.lock.release()


    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''

        self.last_reset_time = time.time()
        self.metricshash = {}
        self.global_actconn = []
        self.global_hits = 0
        self.listeners = {}


    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur
        self.dur_override = True


    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if (self.dur_override):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration


    def add_metric(self, name, val):
        self.metricshash[name] = val

    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            global_actconn = copy.deepcopy(self.global_actconn)
            global_hits = self.global_hits
            listeners = copy.deepcopy(self.listeners)
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        results  = []       # A list for all the Ganglia Log objects

        # if check_time is 0, skip this round because if there's no time, there's no stats..
        if check_time == 0:
            print "check_time is zero, which shouldn't happen.  skipping this run."
            return results

        if global_hits == 0:
            # if there are no hits, skip everything else
            self.add_metric('haproxy_total_hits', 0)
        else:
            # calculate min/max/avg for global active connections
            self.add_metric('haproxy_total_hits', float(global_hits) / check_time)
            global_actconn.sort()
            global_actconn_min = global_actconn[0]
            global_actconn_max = global_actconn[-1]
            global_actconn_avg = float(sum(global_actconn)) / global_hits

            self.add_metric('haproxy_active_connections_min', global_actconn_min)
            self.add_metric('haproxy_active_connections_max', global_actconn_max)
            self.add_metric('haproxy_active_connections_avg', global_actconn_avg)

            for name, listener in listeners.iteritems():
                self.add_metric('haproxy_%s_hits' % name, float(len(listener["latency"])) / check_time)
                # percentage of total hits from this listener 
                self.add_metric('haproxy_%s_hits_p' % name, float(len(listener["latency"])) / global_hits * 100)
                latency = listener["latency"]
                latency.sort()
                # latency is recorded in millisec; convert it to seconds
                self.add_metric('haproxy_%s_latency_%s' % (name, 'min'), float(latency[0])/1000)
                self.add_metric('haproxy_%s_latency_%s' % (name, 'max'), float(latency[-1])/1000)
                self.add_metric('haproxy_%s_latency_%s' % (name, 'avg'), float(sum(latency)) / len(latency)/1000)
                self.add_metric('haproxy_%s_latency_%s' % (name, '50th'), float(latency[int(len(latency) * 0.5)])/1000)
                self.add_metric('haproxy_%s_latency_%s' % (name, '90th'), float(latency[int(len(latency) * 0.9)])/1000)
                feconn = listener["feconn"]
                feconn.sort()
                self.add_metric('haproxy_%s_feconn_%s' % (name, 'min'), feconn[0])
                self.add_metric('haproxy_%s_feconn_%s' % (name, 'max'), feconn[-1])
                self.add_metric('haproxy_%s_feconn_%s' % (name, 'avg'), float(sum(feconn)) / len(feconn))
                beconn = listener["beconn"]
                beconn.sort()
                self.add_metric('haproxy_%s_beconn_%s' % (name, 'min'), beconn[0])
                self.add_metric('haproxy_%s_beconn_%s' % (name, 'max'), beconn[-1])
                self.add_metric('haproxy_%s_beconn_%s' % (name, 'avg'), float(sum(beconn)) / len(beconn))
                for code in self.response_codes:
                    self.add_metric('haproxy_%s_%s_hits' % (name, code), float(listener["responses"][code]) / check_time)


        for (name, val) in self.metricshash.iteritems():
            if 'hits_p' in name:
                results.append(GangliaMetricObject(name, val, units='percent'))
            elif 'hits' in name:
                results.append(GangliaMetricObject(name, val, units='hps'))
            elif 'latency' in name:
                results.append(GangliaMetricObject(name, val, units='sec'))
            else:
                results.append(GangliaMetricObject(name, val, units='connections'))

        # return a list of metric objects
        return results

########NEW FILE########
__FILENAME__ = JavaGCLogtailer
# -*- coding: utf-8 -*-
###
###  Author: Vladimir Vuksan
###  This plugin for logtailer will crunch Java GC logs (modified from PostfixLogtailer)
###    * number of minor GC events
###    * number of full GC events
###    * number of broken GC events
###    * GC time in seconds
###    * Number of garbage bytes collected

import time
import threading
import re

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class JavaGCLogtailer(object):
    # only used in daemon mode
    period = 30.0
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.reset_state()
        self.lock = threading.RLock()
        # this is what will match the Java GC lines
        # Minor GC event 
        # 1097.790: [GC 274858K->16714K(508288K), 0.0146880 secs]
	# Broken GC even
	# 4.762: [GC 98158K(5240768K), 0.0152010 secs]
	# Full GC
	# 3605.198: [Full GC 16722K->16645K(462400K), 0.1874650 secs]
        self.reg_minor_gc = re.compile('^.*: \[GC (?P<start_size>[^ ]+)K->(?P<end_size>[^ ]+)K\((?P<heap_size>[^ ]+)\), (?P<gc_time>[^ ]+) secs\]$')
        self.reg_broken_gc = re.compile('^.*: \[GC (?P<start_size>[0-9]+)K\((?P<heap_size>[^ ]+)\), (?P<gc_time>[^ ]+) secs\]$')
        self.reg_full_gc = re.compile('^.*: \[Full GC (?P<start_size>[^ ]+)K->(?P<end_size>[^ ]+)K\((?P<heap_size>[^ ]+)\), (?P<gc_time>[^ ]+) secs\]$')

        # assume we're in daemon mode unless set_check_duration gets called
        self.dur_override = False


    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        try:
            regMatch = self.reg_minor_gc.match(line)
            if regMatch:
                linebits = regMatch.groupdict()
                self.minor_gc+=1
                self.gc_time+= float(linebits['gc_time'])
                self.garbage+= int(linebits['start_size']) - int(linebits['end_size'])
            regMatch = self.reg_broken_gc.match(line)
            if regMatch:
                linebits = regMatch.groupdict()
                self.broken_gc+=1
                self.gc_time+= float(linebits['gc_time'])
            regMatch = self.reg_full_gc.match(line)
            if regMatch:
                linebits = regMatch.groupdict()
                self.full_gc+=1
                self.gc_time+= float(linebits['gc_time'])
                self.garbage+= int(linebits['start_size']) - int(linebits['end_size'])
            
        except Exception, e:
            self.lock.release()
            raise LogtailerParsingException, "regmatch or contents failed with %s" % e
        self.lock.release()
    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        myret = dict( gc_time = self.gc_time,
                    minor_gc = self.minor_gc,
                    full_gc = self.full_gc,
                    broken_gc = self.broken_gc,
                    garbage = self.garbage
                    )
        return myret
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.minor_gc = 0
        self.broken_gc = 0
        self.full_gc = 0
        self.gc_time = 0
        self.garbage = 0
        self.last_reset_time = time.time()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur 
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # crunch data to how you want to report it
        garbage = float(mydata['garbage']) * 1000

        # package up the data you want to submit
        full_gc_metric = GangliaMetricObject('gc_full', mydata['full_gc'] , units='events')
        minor_gc_metric = GangliaMetricObject('gc_minor', mydata['minor_gc'] , units='events')
        broken_gc_metric = GangliaMetricObject('gc_broken', mydata['broken_gc'] , units='events')
        gc_time_metric = GangliaMetricObject('gc_time', mydata['gc_time'] , units='seconds')
        garbage_metric = GangliaMetricObject('gc_garbage', garbage , units='bytes')

        # return a list of metric objects
        return [ full_gc_metric, minor_gc_metric, broken_gc_metric, gc_time_metric, garbage_metric ]




########NEW FILE########
__FILENAME__ = PostfixLogtailer
###
###  This plugin for logtailer will crunch postfix logs and produce the
###  following metrics:
###    * number of connections per second
###    * number of messages deliveerd per second
###    * number of bounces per second
###

import time
import threading
import re

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class PostfixLogtailer(object):
    # only used in daemon mode
    period = 30.0
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.reset_state()
        self.lock = threading.RLock()
        # this is what will match the postfix lines
        # postfix example log format string:
        # connections:
        # Sep 12 13:50:21 host postfix/smtpd[13334]: connect from unknown[1.2.3.4]
        # deliveries:
        # Sep 12 13:39:11 host postfix/local[11393]: E412470C2B8: to=<foo@host>, orig_to=<foo@bar.com>, relay=local, delay=5, delays=1.9/0/0/3.2, dsn=2.0.0, status=sent (delivered to command: /usr/local/bin/procmail)
        # bounces:
        # Sep 12 11:58:52 host postfix/local[18444]: 8D3C671C324: to=<invalid@host>, orig_to=<invalid@bar.com>, relay=local, delay=0.43, delays=0.41/0/0/0.02, dsn=5.1.1, status=bounced (unknown user: "invalid")
        self.reg_connections = re.compile('^.*postfix/smtpd.*connect from unknown.*$')
        self.reg_deliveries = re.compile('^.*postfix/local.* status=sent .*$')
        self.reg_bounces = re.compile('^.*postfix/local.* status=bounced .*$')

        # assume we're in daemon mode unless set_check_duration gets called
        self.dur_override = False


    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        try:
            regMatch = self.reg_connections.match(line)
            if regMatch:
                self.num_connections+=1
            regMatch = self.reg_deliveries.match(line)
            if regMatch:
                self.num_deliveries+=1
            regMatch = self.reg_bounces.match(line)
            if regMatch:
                self.num_bounces+=1
            
        except Exception, e:
            self.lock.release()
            raise LogtailerParsingException, "regmatch or contents failed with %s" % e
        self.lock.release()
    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        myret = dict( num_conns = self.num_connections,
                    num_deliv = self.num_deliveries,
                    num_bounc = self.num_bounces
                    )
        return myret
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.num_connections = 0
        self.num_deliveries = 0
        self.num_bounces = 0
        self.last_reset_time = time.time()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur 
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # crunch data to how you want to report it
        connections_per_second = mydata['num_conns'] / check_time
        deliveries_per_second = mydata['num_deliv'] / check_time
        bounces_per_second = mydata['num_bounc'] / check_time

        # package up the data you want to submit
        cps_metric = GangliaMetricObject('postfix_connections', connections_per_second, units='cps')
        dps_metric = GangliaMetricObject('postfix_deliveries', deliveries_per_second, units='dps')
        bps_metric = GangliaMetricObject('postfix_bounces', bounces_per_second, units='bps')

        # return a list of metric objects
        return [ cps_metric, dps_metric, bps_metric, ]




########NEW FILE########
__FILENAME__ = SlapdLogtailer
###
###   a 'metric object' is an instance of GangliaMetricObject
###       { 'name' => 'name-of-metric',
###         'value' => numerical-or-string-value,
###         'type' => 'int32',    <--- see gmetric man page for valid types
###         'units' => 'qps',     <--- label on the graph
###         }
###   This object should appear remarkably similar to the required arguments to gmetric.
###
###
###   The logtailer class must define
###     a class variable 'period'
###     an instance method set_check_duration that sets the time since last invocation (used in cron mode)
###     an instance method get_state() that returns a list of metric objects
###     an instance method parse_line(line) that takes one line of the log file and does whatever internal accounting is necessary to record its metrics
###   The logtailer class must be thread safe - a separate thread will be calling get_state() and parse_line(line)
###   parse_line(line) may raise a LogtailerParsingException to log an error and discard the current line but keep going.  Any other exception will kill the process.
###

import time
import threading
import re

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class SlapdLogtailer(object):
    # period must be defined and indicates how often the gmetric thread should call get_state() (in seconds) (in daemon mode only)
    # note that if period is shorter than it takes to run get_state() (if there's lots of complex calculation), the calling thread will automatically double period.
    # period ought to be >=5.  It should probably be >=60 (to avoid excessive load).  120 to 300 is a good range (2-5 minutes).  Take into account the need for time resolution, as well as the number of hosts reporting (6000 hosts * 15s == lots of data).
    period = 300
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.reset_state()
        self.lock = threading.RLock()
        # Oct 27 13:34:30 ldap0.lindenlab.com slapd[16533]: conn=0 fd=18 ACCEPT from IP=216.82.33.42:60976 (IP=0.0.0.0:636)
        self.reg = re.compile('^.*lindenlab.com slapd\[\d+\]: .*(?P<query_status>ACCEPT from IP)')
        self.dur_override = False
        
    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        try:
            regMatch = self.reg.match(line)
            #print regMatch
            if regMatch:
                linebits = regMatch.groupdict()
                if( 'ACCEPT from IP' in linebits['query_status'] ):
                    self.num_slapdquery += 1
            else:
                pass
        except Exception, e:
            self.lock.release()
            raise LogtailerParsingException, "regmatch or contents failed with %s" % e
        self.lock.release()

    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        myret = dict(num_slapdquery = self.num_slapdquery)
        return myret
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.num_slapdquery = 0
        self.last_reset_time = time.time()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # normalize to queries per second
        slapdquery = mydata['num_slapdquery'] / check_time
        #print slapdquery

        # package up the data you want to submit
        slapdquery_metric = GangliaMetricObject('slapd_queries', slapdquery, units='qps')
        # return a list of metric objects
        return [ slapdquery_metric, ]




########NEW FILE########
__FILENAME__ = SVNLogtailer
# -*- coding: utf-8 -*-
###
###  This plugin for logtailer will crunch apache logs for SVN and produce these metrics:
###    * hits per second
###    * GET, PROPPATCH, PROPFINDs etc. per second
###    * number of HTTP 200, 300, 400, and 500 responses per second
###
###  Note that this plugin depends on a certain apache log format, documented in
##   __init__.

import time
import threading
import re

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class SVNLogtailer(object):
    # only used in daemon mode
    period = 30
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.reset_state()
        self.lock = threading.RLock()
        # this is what will match the apache lines
        # apache log format string:
	# %{X-Forwarded-For}i %l %{%Y-%m-%d-%H:%M:%S}t \"%r\" %>s %B \"%{Referer}i\" \"%{User-Agent}i\" %D
        self.reg = re.compile('(?P<remote_ip>[^ ]+) (?P<user>[^ ]+) (?P<user2>[^ ]+) \[(?P<date>[^\]]+)\] "(?P<request>[^ ]+) (?P<url>[^ ]+) (?P<http_protocol>[^ ]+)" (?P<init_retcode>[^ ]+) (?P<size>[^ ]+)')

        # assume we're in daemon mode unless set_check_duration gets called
        self.dur_override = False


    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        self.num_hits+=1
        try:
            regMatch = self.reg.match(line)
            if regMatch:
                linebits = regMatch.groupdict()
                # capture GETs
                if( 'GET' in linebits['request'] ):
                    self.num_gets+=1
                elif( 'POST' in linebits['request'] ):
                    self.num_posts+=1
                elif( 'PROPFIND' in linebits['request'] ):
                    self.num_propfind+=1
                elif( 'OPTIONS' in linebits['request'] ):
                    self.num_options+=1
                elif( 'PUT' in linebits['request'] ):
                    self.num_put+=1
                elif( 'REPORT' in linebits['request'] ):
                    self.num_report+=1
                elif( 'DELETE' in linebits['request'] ):
                    self.num_delete+=1
                elif( 'PROPPATCH' in linebits['request'] ):
                    self.num_proppatch+=1
                elif( 'CHECKOUT' in linebits['request'] ):
                    self.num_checkout+=1
                elif( 'MERGE' in linebits['request'] ):
                    self.num_merge+=1
                elif( 'MKACTIVITY' in linebits['request'] ):
                    self.num_mkactivity+=1
                elif( 'COPY' in linebits['request'] ):
                    self.num_copy+=1
                # capture HTTP response code
                rescode = float(linebits['init_retcode'])
                if( (rescode >= 200) and (rescode < 300) ):
                    self.num_two+=1
                elif( (rescode >= 300) and (rescode < 400) ):
                    self.num_three+=1
                elif( (rescode >= 400) and (rescode < 500) ):
                    self.num_four+=1
                elif( (rescode >= 500) and (rescode < 600) ):
                    self.num_five+=1
                # capture request duration
            else:
                raise LogtailerParsingException, "regmatch failed to match"
        except Exception, e:
            self.lock.release()
            raise LogtailerParsingException, "regmatch or contents failed with %s" % e
        self.lock.release()
    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        myret = dict( num_hits=self.num_hits,
		    num_gets=self.num_gets,
		    num_posts=self.num_posts,
		    num_propfind=self.num_propfind,
		    num_options=self.num_options,
		    num_put=self.num_put,
		    num_report=self.num_report,
		    num_delete=self.num_delete,
		    num_proppatch=self.num_proppatch,
		    num_checkout=self.num_checkout,
		    num_merge=self.num_merge,
		    num_mkactivity=self.num_mkactivity,
		    num_copy=self.num_copy,
                    num_two=self.num_two,
                    num_three=self.num_three,
                    num_four=self.num_four,
                    num_five=self.num_five,
                    )
        return myret
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.num_hits = 0
        self.num_gets = 0
        self.num_posts = 0
        self.num_propfind = 0
        self.num_options = 0
        self.num_put = 0
        self.num_report = 0
        self.num_delete = 0
        self.num_proppatch = 0
        self.num_checkout = 0
        self.num_merge = 0
        self.num_mkactivity = 0
        self.num_copy = 0
        self.req_time = 0
        self.num_two = 0
        self.num_three = 0
        self.num_four = 0
        self.num_five = 0
        self.ninetieth = list()
        self.last_reset_time = time.time()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur 
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # crunch data to how you want to report it
        hits_per_second = mydata['num_hits'] / check_time
        hits_gets_ps = mydata['num_gets'] / check_time 
        hits_posts_ps = mydata['num_posts'] / check_time 
        hits_propfind_ps = mydata['num_propfind'] / check_time 
        hits_options_ps = mydata['num_options'] / check_time 
        hits_put_ps = mydata['num_put'] / check_time 
        hits_report_ps = mydata['num_report'] / check_time 
        hits_delete_ps = mydata['num_delete'] / check_time 
        hits_proppatch_ps = mydata['num_proppatch'] / check_time 
        hits_checkout_ps = mydata['num_checkout'] / check_time 
        hits_merge_ps = mydata['num_merge'] / check_time 
        hits_mkactivity_ps = mydata['num_mkactivity'] / check_time 
        hits_copy_ps = mydata['num_copy'] / check_time 
        
        # 
        two_per_second = mydata['num_two'] / check_time
        three_per_second = mydata['num_three'] / check_time 
        four_per_second = mydata['num_four'] / check_time
        five_per_second = mydata['num_five'] / check_time

        # package up the data you want to submit
        hps_metric = GangliaMetricObject('svn_total', hits_per_second, units='hps')
        gets_metric = GangliaMetricObject('svn_gets', hits_gets_ps, units='hps')
        posts_metric = GangliaMetricObject('svn_posts', hits_posts_ps, units='hps')
        propfind_metric = GangliaMetricObject('svn_propfind', hits_propfind_ps, units='hps')
        options_metric = GangliaMetricObject('svn_options', hits_options_ps, units='hps')
        put_metric = GangliaMetricObject('svn_put', hits_put_ps, units='hps')
        report_metric = GangliaMetricObject('svn_report', hits_report_ps, units='hps')
        delete_metric = GangliaMetricObject('svn_delete', hits_delete_ps, units='hps')
        proppatch_metric = GangliaMetricObject('svn_proppatch', hits_proppatch_ps, units='hps')
        checkout_metric = GangliaMetricObject('svn_checkout', hits_checkout_ps, units='hps')
        merge_metric = GangliaMetricObject('svn_merge', hits_merge_ps, units='hps')
        mkactivity_metric = GangliaMetricObject('svn_mkactivity', hits_mkactivity_ps, units='hps')
        copy_metric = GangliaMetricObject('svn_copy', hits_copy_ps, units='hps')
        
        twops_metric = GangliaMetricObject('svn_200', two_per_second, units='hps')
        threeps_metric = GangliaMetricObject('svn_300', three_per_second, units='hps')
        fourps_metric = GangliaMetricObject('svn_400', four_per_second, units='hps')
        fiveps_metric = GangliaMetricObject('svn_500', five_per_second, units='hps')

        # return a list of metric objects
        return [ hps_metric, gets_metric, posts_metric, propfind_metric, options_metric, put_metric, report_metric, delete_metric, proppatch_metric, checkout_metric, merge_metric, mkactivity_metric, copy_metric, twops_metric, threeps_metric, fourps_metric, fiveps_metric, ]




########NEW FILE########
__FILENAME__ = tailnostate
#!/usr/bin/python
"""Tail a file, reopening it if it gets rotated"""

import time, os, sys, glob


class Tail(object):
    def __init__(self, filename, start_pos=0):
        self.fp = file(filename)
        self.filename = filename

        if start_pos < 0:
            self.fp.seek(-start_pos-1, 2)
            self.pos = self.fp.tell()
        else:
            self.fp.seek(start_pos)
            self.pos = start_pos

    def __iter__(self):
        """Return next line.  This function will sleep until there *is* a
        next line.  Works over log rotation."""
        counter = 0
        while True:
            line = self.next()
            if line is None:
                counter += 1
                if counter >= 5:
                    counter = 0
                    self.check_inode()
                time.sleep(1.0)
            else:
                yield line

    def check_inode(self):
        """check to see if the filename we expect to tail has the same
        inode as our currently open file.  This catches log rotation"""
        inode = os.stat(self.filename).st_ino
        old_inode = os.fstat(self.fp.fileno()).st_ino
        if inode != old_inode:
            self.fp = file(self.filename)
            self.pos = 0

    def next(self):
        """Return the next line from the file.  Returns None if there are not
        currently any lines available, at which point you should sleep before
        calling again.  Does *not* handle log rotation.  If you use next(), you
        must also use check_inode to handle log rotation"""
        where = self.fp.tell()
        line = self.fp.readline()
        if line and line[-1] == '\n':
            self.pos += len(line)
            return line
        else:
            self.fp.seek(where)
            return None

    def close(self):
        self.fp.close()



class LogTail(Tail):
    def __init__(self, filename):
        self.base_filename = filename
        super(LogTail, self).__init__(filename, -1)

    def get_file(self, inode, next=False):
        files = glob.glob('%s*' % self.base_filename)
        files = [(os.stat(f).st_mtime, f) for f in files]
        # Sort by modification time
        files.sort()

        flag = False
        for mtime, f in files:
            if flag:
                return f
            if os.stat(f).st_ino == inode:
                if next:
                    flag = True
                else:
                    return f
        else:
            return self.base_filename

    def reset(self):
        self.fp = file(self.filename)
        self.pos = 0

    def advance(self):
        self.filename = self.get_file(os.fstat(self.fp.fileno()).st_ino, True)
        self.reset()

    def check_inode(self):
        if self.filename != self.base_filename or os.stat(self.filename).st_ino != os.fstat(self.fp.fileno()).st_ino:
            self.advance()


def main():
    import sys

    t = Tail(sys.argv[1], -1)
    for line in t:
        print line


if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = TomcatLogtailer
# -*- coding: utf-8 -*-
###
###  This plugin for logtailer will crunch apache logs and produce these metrics:
###    * hits per second
###    * GETs per second
###    * average query processing time
###    * ninetieth percentile query processing time
###    * number of HTTP 200, 300, 400, and 500 responses per second
###
###  Note that this plugin depends on a certain apache log format, documented in
##   __init__.

import time
import threading
import re

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class TomcatLogtailer(object):
    # only used in daemon mode
    period = 60
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.reset_state()
        self.lock = threading.RLock()
        # this is what will match the tomcat lines
        # tomcat log format string:
        # %v %A %a %u %{%Y-%m-%dT%H:%M:%S}t %c %s %>s %B %D %{cookie}n \"%{Referer}i\" \"%r\" \"%{User-Agent}i\" %P
        # host.com 127.0.0.1 127.0.0.1 - 2008-05-08T07:34:44 - 200 200 371 103918 - "-" "GET /path HTTP/1.0" "-" 23794
        # match keys: server_name, local_ip, remote_ip, date, conn_status, init_retcode, final_retcode, size,
        #               req_time, cookie, referrer, request, user_agent, pid
        self.reg = re.compile("^INFO: \[\] webapp=(?P<webapp>[^\s]+) path=(?P<path>[^\s]+) params=(?P<params>\{[^\}]*\}) status=(?P<status>[^\s]+) QTime=(?P<qtime>[0-9]+)$")
        # assume we're in daemon mode unless set_check_duration gets called
        self.dur_override = False


    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        self.num_hits+=1
        regMatch = self.reg.match(line)
        if regMatch:
            linebits = regMatch.groupdict()
            self.num_hits += 1
            # capture request duration
            dur = int(linebits['qtime'])
            self.req_time += dur
            # store for 90th % calculation
            self.ninetieth.append(dur)
        self.lock.release()
    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        myret = dict( num_hits=self.num_hits,
                    req_time=self.req_time,
                    ninetieth=self.ninetieth
                    )
        return myret
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.num_hits = 0
        self.req_time = 0
        self.ninetieth = list()
        self.last_reset_time = time.time()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur 
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # crunch data to how you want to report it
        hits_per_second = mydata['num_hits'] / check_time
        if (mydata['num_hits'] != 0):
             avg_req_time = mydata['req_time'] / mydata['num_hits']
        else:
             avg_req_time = 0

        # calculate 90th % request time
        ninetieth_list = mydata['ninetieth']
        ninetieth_list.sort()
        num_entries = len(ninetieth_list)
        if (num_entries != 0 ):
            slowest = ninetieth_list[-1]
            ninetieth_element = ninetieth_list[int(num_entries * 0.9)]
        else:
            slowest = 0
            ninetieth_element = 0

        # package up the data you want to submit
        hps_metric = GangliaMetricObject('solr_rps', hits_per_second, units='rps')
        avgdur_metric = GangliaMetricObject('solr_avg_dur', avg_req_time, units='ms')
        ninetieth_metric = GangliaMetricObject('solr_90th_dur', ninetieth_element, units='ms')
        slowest_metric   = GangliaMetricObject('solr_slowest_dur', slowest, units='ms')
        # return a list of metric objects
        return [ hps_metric, avgdur_metric, ninetieth_metric, slowest_metric ]




########NEW FILE########
__FILENAME__ = UnboundLogtailer
###
### This logtailer plugin for ganglia-logtailer parses logs from Unbound and
### produces the following metrics:
###   * queries per second
###   * recursion requests per second
###   * cache hits per second
###

import time
import threading
import re

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class UnboundLogtailer(object):
    # period must be defined and indicates how often the gmetric thread should call get_state() (in seconds) (in daemon mode only)
    # note that if period is shorter than it takes to run get_state() (if there's lots of complex calculation), the calling thread will automatically double period.
    # period must be >15.  It should probably be >=60 (to avoid excessive load).  120 to 300 is a good range (2-5 minutes).  Take into account the need for time resolution, as well as the number of hosts reporting (6000 hosts * 15s == lots of data).
    period = 5
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.dur_override = False
        self.reset_state()
        self.reg = re.compile('^(?P<month>\S+)\s+(?P<day>\S+)\s+(?P<time>\S+)\s+(?P<hostname>\S+)\s+(?P<program>\S+):\s+\[(?P<pid>\d+):\d+\]\s+(?P<facility>\S+):\s+server\sstats\sfor\sthread\s(?P<thread>\d+):\s+(?P<queries>\d+)\s+\S+\s+(?P<caches>\d+)\s+\S+\s+\S+\s+\S+\s+(?P<recursions>)\d+')
        self.lock = threading.RLock()
        self.queries = [0,0,0,0]
        self.caches = [0,0,0,0]
        self.recursions = [0,0,0,0]
    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        regMatch = self.reg.match(line)
        if regMatch:
            self.num_lines+=1
            bitsdict = regMatch.groupdict()
            self.queries[int(bitsdict['thread'])] += int(bitsdict['queries'])
            self.caches[int(bitsdict['thread'])] += int(bitsdict['caches'])
            self.recursions[int(bitsdict['thread'])] += int(bitsdict['queries']) - int(bitsdict['caches'])
        self.lock.release()
    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        return [ self.num_lines, self.queries, self.caches, self.recursions ]
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.num_lines = 0
        self.queries = [0,0,0,0]
        self.caches = [0,0,0,0]
        self.recursions = [0,0,0,0]
        self.last_reset_time = time.time()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            number_of_lines, queries, caches, recursions = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # crunch data to how you want to report it
        queries_per_second = sum(queries) / check_time
        recursions_per_second = sum(recursions) / check_time
        caches_per_second = sum(caches) / check_time

        # package up the data you want to submit
        qps_metric = GangliaMetricObject('unbound_queries', queries_per_second, units='qps')
        rps_metric = GangliaMetricObject('unbound_recursions', recursions_per_second, units='rps')
        cps_metric = GangliaMetricObject('unbound_cachehits', caches_per_second, units='cps')
        # return a list of metric objects
        return [ qps_metric, rps_metric, cps_metric ]




########NEW FILE########
__FILENAME__ = VarnishLogtailer
# -*- coding: utf-8 -*-
###
###  This plugin for logtailer will crunch Varnish logs and produce these metrics:
###    * hits per second
###    * GETs per second
###    * number of HTTP 200, 300, 400, and 500 responses per second
###
###  Author: Vladimir Vuksan
###  This script is derivative off Linden Labs' ApacheLogTailer script
###
###  Note that this plugin depends on a Varnish NCSA log format, documented in
###  I am producing the Varnish log by running following command as a daemon
###  /usr/bin/varnishncsa -a -w /var/log/varnish/varnishncsa.log -D -P /var/run/varnishncsa.pid
###
###  To crunch the logs I run following command out of the cron
###
###  /opt/logtailer/ganglia-logtailer --classname VarnishLogtailer --log_file /var/log/varnish/varnishncsa.log --mode cron
##   __init__.

import time
import threading
import re

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class VarnishLogtailer(object):
    # only used in daemon mode
    period = 30
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.reset_state()
        self.lock = threading.RLock()
        # this is what will match the apache lines
        # match keys: remote_ip, http_user, http_user2, date, conn_status, init_retcode, final_retcode, size,
        #               req_time, cookie, referrer, request, user_agent, pid
        self.reg = re.compile('^(?P<remote_ip>[^ ]+) (?P<http_user>[^ ]+) (?P<http_user2>[^ ]+) (?P<req_date>[^ ]+) (?P<timezone>[^ ]+) "(?P<request>[^ ]+) (?P<url>[^ ]+) (?P<http_protocol>[^ ]+) (?P<init_retcode>[^ ]+)')
        # assume we're in daemon mode unless set_check_duration gets called
        self.dur_override = False


    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        self.num_hits+=1
        try:
            regMatch = self.reg.match(line)
            if regMatch:
                linebits = regMatch.groupdict()
                # capture GETs
                if( 'GET' in linebits['request'] ):
                    self.num_gets+=1
                # capture HTTP response code
                rescode = float(linebits['init_retcode'])

                if( (rescode >= 200) and (rescode < 300) ):
                    self.num_two+=1
                elif( (rescode >= 300) and (rescode < 400) ):
                    self.num_three+=1
                elif( (rescode >= 400) and (rescode < 500) ):
                    self.num_four+=1
                elif( (rescode >= 500) and (rescode < 600) ):
                    self.num_five+=1
            else:
                raise LogtailerParsingException, "regmatch failed to match"
        except Exception, e:
            self.lock.release()
            raise LogtailerParsingException, "regmatch or contents failed with %s" % e
        self.lock.release()
    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        myret = dict( num_hits=self.num_hits,
                    num_gets=self.num_gets,
                    req_time=self.req_time,
                    num_two=self.num_two,
                    num_three=self.num_three,
                    num_four=self.num_four,
                    num_five=self.num_five,
                    )
        return myret
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.num_hits = 0
        self.num_gets = 0
        self.req_time = 0
        self.num_two = 0
        self.num_three = 0
        self.num_four = 0
        self.num_five = 0
        self.last_reset_time = time.time()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur 
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # crunch data to how you want to report it
        hits_per_second = mydata['num_hits'] / check_time
        gets_per_second = mydata['num_gets'] / check_time
        two_per_second = mydata['num_two'] / check_time
        three_per_second = mydata['num_three'] / check_time
        four_per_second = mydata['num_four'] / check_time
        five_per_second = mydata['num_five'] / check_time

        # package up the data you want to submit
        hps_metric = GangliaMetricObject('varnish_hits', hits_per_second, units='hps')
        gps_metric = GangliaMetricObject('varnish_gets', gets_per_second, units='hps')
        twops_metric = GangliaMetricObject('varnish_200', two_per_second, units='hps')
        threeps_metric = GangliaMetricObject('varnish_300', three_per_second, units='hps')
        fourps_metric = GangliaMetricObject('varnish_400', four_per_second, units='hps')
        fiveps_metric = GangliaMetricObject('varnish_500', five_per_second, units='hps')

        # return a list of metric objects
        return [ hps_metric, gps_metric, twops_metric, threeps_metric, fourps_metric, fiveps_metric, ]

########NEW FILE########
__FILENAME__ = VarnishMemcacheLogtailer
# -*- coding: utf-8 -*-
###
###  This plugin for logtailer will crunch Varnish logs and produce these metrics:
###    * hits per second
###    * GETs per second
###    * number of HTTP 200, 300, 400, and 500 responses per second
###
###  In addition this script will insert number of requests per IP on a particular
###  web server in the particular hour
###
###  Author: Vladimir Vuksan http://twitter.com/vvuksan
###
###  Note that this plugin depends on varnishncsa producing the standard NCSA HTTP format
###  It also depends on the Python Memcached client. You can download it from
###  http://www.tummy.com/Community/software/python-memcached/
##   __init__.

import time
import threading
import re
import memcache
import socket

# local dependencies
from ganglia_logtailer_helper import GangliaMetricObject
from ganglia_logtailer_helper import LogtailerParsingException, LogtailerStateException

class VarnishMemcacheLogtailer(object):
    # only used in daemon mode
    period = 30
    def __init__(self):
        '''This function should initialize any data structures or variables
        needed for the internal state of the line parser.'''
        self.reset_state()
        self.lock = threading.RLock()
        self.reg = re.compile('^(?P<remote_ip>[^ ]+) (?P<http_user>[^ ]+) (?P<http_user2>[^ ]+) \[(?P<req_date>[^ ]+) (?P<timezone>[^ ]+) "(?P<request>[^ ]+) (?P<url>[^ ]+) (?P<http_protocol>[^ ]+) (?P<init_retcode>[^ ]+)')
        # assume we're in daemon mode unless set_check_duration gets called
        self.dur_override = False

        # IMPORTANT IMPORTANT IMPORTANT IMPORTANT IMPORTANT IMPORTANT
        # Set the memcache server to your memcache server
        self.mc = memcache.Client(['localhost:11211'], debug=0)

        hostName = socket.gethostname()
        self.instance = hostName.split('.')[0]

        # I have to do this because python 2.4 doesn't support strptime. It is used
        # to convert the date ie. 02/Apr/2010 to 20100402. I didn't want to introduce
        # any dependencies
        self.months_dict = {
          'Jan' : '01', 'Feb' : '02', 'Mar' : '03', 'Apr' : '04', 'May' : '05', 'Jun' : '06',
          'Jul' : '07', 'Aug' : '08', 'Sep' : '09', 'Oct' : '10', 'Nov' : '11', 'Dec' : '12'
        }


    # example function for parse line
    # takes one argument (text) line to be parsed
    # returns nothing
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time,
        updating the internal state variables.'''
        self.lock.acquire()
        self.num_hits+=1
        try:
            regMatch = self.reg.match(line)
            if regMatch:
                linebits = regMatch.groupdict()
                # capture GETs
                if( 'GET' in linebits['request'] ):
                    self.num_gets+=1
                # capture HTTP response code
                rescode = float(linebits['init_retcode'])

                if( (rescode >= 200) and (rescode < 300) ):
                    self.num_two+=1
                elif( (rescode >= 300) and (rescode < 400) ):
                    self.num_three+=1
                elif( (rescode >= 400) and (rescode < 500) ):
                    self.num_four+=1
                elif( (rescode >= 500) and (rescode < 600) ):
                    self.num_five+=1

                full_date = linebits['req_date']
                # This is not my proudest code however due to lack of strptime in Python 2.4
                # we have to resort to these kinds of craziness
                date_time_pieces = full_date.split(':')
                date = date_time_pieces[0]
                split_date = date.split('/')
                day = split_date[0]
                month = split_date[1]
                year = split_date[2]
                month = self.months_dict[month]
                hour = date_time_pieces[1]
                minute = date_time_pieces[2]

                date_and_hour = year + month + day + hour
                MC_TTL = 43200
                
                ##########################################################################################
                # Memcache has an ADD command which only succeeds if a key is not present. We'll construct
                # a key that contains the webserver that client is on and date and hour ie.
                # ip-web22-2010033022-1.2.3.4
                mc_key = "ip-" + self.instance + "-" + date_and_hour + "-" + linebits['remote_ip'] 
                return_code = self.mc.add(mc_key , "1", MC_TTL) 

                # If add fails it means that the key exists and we should increment it
                if ( return_code == 0 ):
                   incr_code = self.mc.incr(mc_key)
                # If the key doesn't exist ie. add succeeded we should append the IP to 
                # the list of IPs that have seen. We'll then end up with a key called
                # ipsarray-web22-2010033022 which is a comma delimited list of IPs
                else:
                   # Try to add the key. If it's already there use append to append to the end of the list
                   mc_key = "ipsarray-" + self.instance + "-" + date_and_hour
                   return_code = self.mc.add(mc_key , linebits['remote_ip'], MC_TTL)                 
                   if ( return_code == 0 ):
                      self.mc.append(mc_key, "," + linebits['remote_ip'] , MC_TTL)

            else:
                raise LogtailerParsingException, "regmatch failed to match"
        except Exception, e:
            self.lock.release()
            raise LogtailerParsingException, "regmatch or contents failed with %s" % e
        self.lock.release()
    # example function for deep copy
    # takes no arguments
    # returns one object
    def deep_copy(self):
        '''This function should return a copy of the data structure used to
        maintain state.  This copy should different from the object that is
        currently being modified so that the other thread can deal with it
        without fear of it changing out from under it.  The format of this
        object is internal to the plugin.'''
        myret = dict( num_hits=self.num_hits,
                    num_gets=self.num_gets,
                    req_time=self.req_time,
                    num_two=self.num_two,
                    num_three=self.num_three,
                    num_four=self.num_four,
                    num_five=self.num_five,
                    )
        return myret
    # example function for reset_state
    # takes no arguments
    # returns nothing
    def reset_state(self):
        '''This function resets the internal data structure to 0 (saving
        whatever state it needs).  This function should be called
        immediately after deep copy with a lock in place so the internal
        data structures can't be modified in between the two calls.  If the
        time between calls to get_state is necessary to calculate metrics,
        reset_state should store now() each time it's called, and get_state
        will use the time since that now() to do its calculations'''
        self.num_hits = 0
        self.num_gets = 0
        self.req_time = 0
        self.num_two = 0
        self.num_three = 0
        self.num_four = 0
        self.num_five = 0
        self.last_reset_time = time.time()
    # example for keeping track of runtimes
    # takes no arguments
    # returns float number of seconds for this run
    def set_check_duration(self, dur):
        '''This function only used if logtailer is in cron mode.  If it is
        invoked, get_check_duration should use this value instead of calculating
        it.'''
        self.duration = dur 
        self.dur_override = True
    def get_check_duration(self):
        '''This function should return the time since the last check.  If called
        from cron mode, this must be set using set_check_duration().  If in
        daemon mode, it should be calculated internally.'''
        if( self.dur_override ):
            duration = self.duration
        else:
            cur_time = time.time()
            duration = cur_time - self.last_reset_time
            # the duration should be within 10% of period
            acceptable_duration_min = self.period - (self.period / 10.0)
            acceptable_duration_max = self.period + (self.period / 10.0)
            if (duration < acceptable_duration_min or duration > acceptable_duration_max):
                raise LogtailerStateException, "time calculation problem - duration (%s) > 10%% away from period (%s)" % (duration, self.period)
        return duration
    # example function for get_state
    # takes no arguments
    # returns a dictionary of (metric => metric_object) pairs
    def get_state(self):
        '''This function should acquire a lock, call deep copy, get the
        current time if necessary, call reset_state, then do its
        calculations.  It should return a list of metric objects.'''
        # get the data to work with
        self.lock.acquire()
        try:
            mydata = self.deep_copy()
            check_time = self.get_check_duration()
            self.reset_state()
            self.lock.release()
        except LogtailerStateException, e:
            # if something went wrong with deep_copy or the duration, reset and continue
            self.reset_state()
            self.lock.release()
            raise e

        # crunch data to how you want to report it
        hits_per_second = mydata['num_hits'] / check_time
        gets_per_second = mydata['num_gets'] / check_time
        two_per_second = mydata['num_two'] / check_time
        three_per_second = mydata['num_three'] / check_time
        four_per_second = mydata['num_four'] / check_time
        five_per_second = mydata['num_five'] / check_time

        # package up the data you want to submit
        hps_metric = GangliaMetricObject('varnish_hits', hits_per_second, units='hps')
        gps_metric = GangliaMetricObject('varnish_gets', gets_per_second, units='hps')
        twops_metric = GangliaMetricObject('varnish_200', two_per_second, units='hps')
        threeps_metric = GangliaMetricObject('varnish_300', three_per_second, units='hps')
        fourps_metric = GangliaMetricObject('varnish_400', four_per_second, units='hps')
        fiveps_metric = GangliaMetricObject('varnish_500', five_per_second, units='hps')

        # return a list of metric objects
        return [ hps_metric, gps_metric, twops_metric, threeps_metric, fourps_metric, fiveps_metric, ]




########NEW FILE########
__FILENAME__ = aggregator
import os
import re
from sets import Set
import socket
import xml.parsers.expat

# the aggregator was written to be used from within chef, generating the
# list of clusters and metrics to be aggregated from attributes in other
# chef recipes. It can, however, be used standalone by manually configuring
# the clusters at the bottom of the file.
#
# In this file you'll find both examples of chef attributes to set as well
# as how to set the hashes directly.


# reads chef attributes indicating metrics to aggregate across a group
# reports the aggregated metrics spoofed to a host named all_$groupname
#
# Options to include in the chef attributes:
#    name: the name of the metric to aggregate
#    pattern: (optional) a regex to use to identify the source metrics
#              if absent, the 'name' field is used instead
#              it's a good idea to include ^ and $ to bound your pattern
#    aggregator: the operation to use to aggregate metrics
#                can be AVG, MAX, MIN, or SUM
#    units: the label to put on the Y axis of the generated graph
#
# Example attributes
#   {
#           "name" => "nginx_total_90th",
#           "aggregator" => "AVG",
#           "units" => "eps"
#   },
#   {
#           "name" => 'haproxy_\\1_hits',
#           "pattern" => '^haproxy_(.+)_hits$',
#           "aggregator" => "SUM",
#           "units" => "hits/sec"
#   },


class GangliaAggregator:
    AVG = 'AVG'
    SUM = 'SUM'
    MAX = 'MAX'
    MIN = 'MIN'
    def __init__(self, metrics, cluster_map):
        """Creates a ganglia aggregator that uses cluster_map to find the ports
          of the collector for a cluster and aggregates the metrics provided
          in metrics.  metrics is a dictionay of cluster name to an array of
          [<metric_name>, AVG | SUM | MAX | MIN, <units>, <metric pattern>]."""
        self._cluster_map = cluster_map
        self._tracked_metrics = metrics
        # Compile the regular expressions in each metric
        for cluster in self._tracked_metrics:
            for metric in self._tracked_metrics[cluster]:
                metric[3] = re.compile(metric[3])

        # a name like foo_\1 might turn into several foo_bar metrics. this
        # is a reverse index of foo_bar -> foo_\1
        self._expanded_names = {}

        # This is a tmp variable that is used to accumulate the data
        # while we are parsing the xml.  The key is the metric_pattern
        # and the value will be an array of the raw data points.
        self._accumulated_values = {}
        self._metric_units = {}

    def grab_xml(self, cluster):
        """Grabs the xml of the metrics for a given cluster."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', self._cluster_map[cluster]))
        full_data = ''
        data = s.recv(1024)
        while data:
            full_data += data
            data = s.recv(1024)
        s.close()
        return full_data


    # Any time the name includes "\x" where x is a digit, we will replace
    # replace that part of the name with the value from the regex caputure
    # (matches are 0-indexed; in this example \1 matches (\[a-zA-Z]+)), not \d+
    # i.e. name: push_expansion_trace_\1_duration_avg
    #      pattern: push_expansion_\d+_trace_(\[a-zA-Z]+)_duration_avg
    #      wil match push_expansion_1_trace_YieldDevice_duration_avg and
    #      aggregate it in push_expansion_trace_YieldDevice_duration_avg
    def metric_name(self, name, re_match):
        captures = re_match.groups(())
        for n in xrange(len(captures)):
            name = name.replace('\\%i' % (n + 1), captures[n])
        return name

    def handle_start(self, cluster, name, attrs):
        """Handles a start tag for a given cluster.  name is the name of the
           tag (the only one that we care about is METRIC).  attrs is the
           attributes for the tag."""
        if not name == 'METRIC':
            return
        metric_name = attrs['NAME']
        tracked_metrics = self._tracked_metrics[cluster]
        keys_to_update = []
        for x in tracked_metrics:
            match = x[3].match(metric_name)
            if match:
                expanded_name = self.metric_name(x[0], match)
                if x[0] not in self._expanded_names:
                    self._expanded_names[x[0]] = []
                if expanded_name not in self._expanded_names[x[0]]:
                    self._expanded_names[x[0]].append(expanded_name)
                keys_to_update.append(expanded_name)

        if len(keys_to_update) == 0:
            return

        value = float(attrs['VAL'])
        for key in Set(keys_to_update):
            if key not in self._accumulated_values:
              self._accumulated_values[key] = []
            self._accumulated_values[key].append(value)
            self._metric_units[key] = attrs['UNITS']


    def parse_xml(self, cluster, xmlstring):
        """Parses the given xmlstring for a cluster and compute the aggregate
           the metrics."""
        parser = xml.parsers.expat.ParserCreate()
        parser.StartElementHandler = (
                lambda name, attrs: self.handle_start(cluster, name, attrs))
        parser.Parse(xmlstring)

    def proccess_cluster(self, cluster):
        """Process the metrics for a given cluster."""
        if not self._tracked_metrics.has_key(cluster):
            print 'Skipping %s because no metrics are needed' % cluster
            return
        if not self._cluster_map.has_key(cluster):
            print 'Unknown cluster %s' % cluster
            return
        self._accumulated_values = {}
        self._metric_units = {}

        xml_string = self.grab_xml(cluster)
        self.parse_xml(cluster, xml_string)

        config_file = '/etc/ganglia/gmond_collector_%s.conf' % cluster
        tracked_metrics = self._tracked_metrics[cluster]
        for base_name, aggregator, units, pattern in tracked_metrics:
            if base_name not in self._expanded_names:
                continue
            for expanded_name in self._expanded_names[base_name]:
                try:
                    values = self._accumulated_values[expanded_name]
                except KeyError:
                    values = [0] 
                total = sum(values)
                if aggregator == GangliaAggregator.AVG and len(values) > 0:
                    total = total / len(values)
                elif aggregator == GangliaAggregator.MAX and len(values) > 0:
                    total = max(values)
                elif aggregator == GangliaAggregator.MIN and len(values) > 0:
                    total = min(values)
                metric_name = '%s_%s' % (expanded_name, aggregator)
                try:
                    if self._metric_units[expanded_name] != "":
                        units = self._metric_units[expanded_name]
                except KeyError:
                    #use the existing value for units
                    pass

                values = {
                    'config' : config_file,
                    'value' : total,
                    'name' : metric_name,
                    'units' : units,
                    'type' : 'float',
                    'spoof' : 'all_%s:all_%s' %(cluster, cluster)
                }
                command = "gmetric -c %(config)s -n '%(name)s' -v %(value)f " % values
                command += "-u %(units)s -S %(spoof)s -t %(type)s" % values
                os.system(command)

    def process_all(self):
        for key in self._tracked_metrics.keys():
            self.proccess_cluster(key)

cluster_map = {
    # format is 'cluster_name' : port
    'default' : 8649
}
metrics = {
    'default' : [
        # format is ['new_metric_name', 'op', 'y axis label', 'metric regex to match']
        # new_metric_name will have op appended eg load_one_SUM
        ['load_one', 'SUM', 'load', '^load_one$'],
        ['cpu_user', 'AVG', '%', '^cpu_user$']
        ]
}

# Uncomment the following to use this from within chef.
# cluster_map = {
#     <% @clusters.each do |name, port| %>
#     '<%= name %>' : <%= port %>,
#     <% end %>
# }
# metrics = {
#     <% @metrics.each do |cluster, values| %>
#     '<%= cluster %>' : [ <% values.each do |metric| %>
#             [r'<%= metric[0] %>', '<%= metric[1] %>', '<%= metric[2] %>', '<%= metric[3] %>'],<% end %>
#             ],
#     <% end %>
# }

aggregator = GangliaAggregator(metrics, cluster_map)
aggregator.process_all()

########NEW FILE########
__FILENAME__ = gmetadXmlChecker
#!/usr/local/bin/python

import socket, os, sys, logging
from optparse import OptionParser

usage = 'usage: %prog [options] arg1 arg2'
parser = OptionParser(usage="%prog [-r] [-q] [-h]", version="%prog 1.0")
parser.add_option("-v", "--verbose",
     action="store_true", dest="verbose", default=False,
     help="make lots of noise [default]")
parser.add_option("-q", "--quiet",
     action="store_false", dest="verbose", default=True,
     help="be vewwy quiet (I'm hunting wabbits)")
parser.add_option("-r", "--restart",
     action="store_true", dest="restart", default=False,
     help="Should I actually restart gmetad")
(options, args) = parser.parse_args()

LOG_FILENAME = '/var/logs/gmetad.log'
logging.basicConfig(filename=LOG_FILENAME, level=logging.NOTSET)

def restartGmetad():
    cmd = 'service gmetad restart'
    pipe = os.popen(cmd)
    results = [l for l in pipe.readlines() if l.find('OK') != -1]
    if results:
        return True
    else:
        return False

def gmetadXmlChecker(port):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(("localhost", port))
        data = client_socket.recv(512)
        if  len(data) < 512:
            logging.critical('We didn\'t recieve any output from gmetad running on port: %d' % port)
            if options.verbose:
                print "We didn\'t recieve any output from gmetad running in port: %d" % port
            client_socket.close()
	    return False
        else:
            #print "RECIEVED:" , data
            client_socket.close()
	    return True
    except Exception as e:
        logging.critical('Gmetad does not seem to be running on this port')
        if options.verbose:
            print "Cannot connect to host"
 	return False


def main():
    try:
        gmetad_confs = os.listdir('/etc/gmetad')
    except:
        logging.critical('Directory does not exist')
        if options.verbose:
            print 'Directory does not exist'
        exit()
    xml_ports = []
    for conf in gmetad_confs:
        for line in open('/etc/gmetad/' + conf):
            if 'xml_port' in line:
                xml_ports.append(int(line.split(' ')[1].rstrip('\n')))

    for port in xml_ports:
        if gmetadXmlChecker(port) == True:
            logging.info('gmetad on port: %d is running correctly, exiting' % port)
            if options.verbose:
                print "gmetad on port: %d is running correctly, exiting" % port
        else:
            logging.critical('gmetad on port: %d  is not responding, restarting' % port)
            if options.verbose:
                print "gmetad on port: %d  is not responding, restarting" % port
            if options.restart:
                restartGmetad()
                exit()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = gmetric
#!/usr/bin/env python

# This is the MIT License
# http://www.opensource.org/licenses/mit-license.php
#
# Copyright (c) 2007,2008 Nick Galbreath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

#
# Version 1.0 - 21-Apr-2007
#   initial
# Version 2.0 - 16-Nov-2008
#   made class Gmetric thread safe
#   made gmetrix xdr writers _and readers_
#   Now this only works for gmond 2.X packets, not tested with 3.X
#
# Version 3.0 - 09-Jan-2011 Author: Vladimir Vuksan
#   Made it work with the Ganglia 3.1 data format
#
# Version 3.1 - 30-Apr-2011 Author: Adam Tygart
#   Added Spoofing support


from xdrlib import Packer, Unpacker
import socket, re

slope_str2int = {'zero':0,
                 'positive':1,
                 'negative':2,
                 'both':3,
                 'unspecified':4}

# could be autogenerated from previous but whatever
slope_int2str = {0: 'zero',
                 1: 'positive',
                 2: 'negative',
                 3: 'both',
                 4: 'unspecified'}


class Gmetric:
    """
    Class to send gmetric/gmond 2.X packets

    Thread safe
    """

    type = ('', 'string', 'uint16', 'int16', 'uint32', 'int32', 'float',
            'double', 'timestamp')
    protocol = ('udp', 'multicast')

    def __init__(self, host, port, protocol):
        if protocol not in self.protocol:
            raise ValueError("Protocol must be one of: " + str(self.protocol))

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if protocol == 'multicast':
            self.socket.setsockopt(socket.IPPROTO_IP,
                                   socket.IP_MULTICAST_TTL, 20)
        self.hostport = (host, int(port))
        #self.socket.connect(self.hostport)

    def send(self, NAME, VAL, TYPE='', UNITS='', SLOPE='both',
             TMAX=60, DMAX=0, GROUP="", SPOOF=""):
        if SLOPE not in slope_str2int:
            raise ValueError("Slope must be one of: " + str(self.slope.keys()))
        if TYPE not in self.type:
            raise ValueError("Type must be one of: " + str(self.type))
        if len(NAME) == 0:
            raise ValueError("Name must be non-empty")

        ( meta_msg, data_msg )  = gmetric_write(NAME, VAL, TYPE, UNITS, SLOPE, TMAX, DMAX, GROUP, SPOOF)
        # print msg

        self.socket.sendto(meta_msg, self.hostport)
        self.socket.sendto(data_msg, self.hostport)

def gmetric_write(NAME, VAL, TYPE, UNITS, SLOPE, TMAX, DMAX, GROUP, SPOOF):
    """
    Arguments are in all upper-case to match XML
    """
    packer = Packer()
    HOSTNAME="test"
    if SPOOF == "":
        SPOOFENABLED=0
    else :
        SPOOFENABLED=1
    # Meta data about a metric
    packer.pack_int(128)
    if SPOOFENABLED == 1:
        packer.pack_string(SPOOF)
    else:
        packer.pack_string(HOSTNAME)
    packer.pack_string(NAME)
    packer.pack_int(SPOOFENABLED)
    packer.pack_string(TYPE)
    packer.pack_string(NAME)
    packer.pack_string(UNITS)
    packer.pack_int(slope_str2int[SLOPE]) # map slope string to int
    packer.pack_uint(int(TMAX))
    packer.pack_uint(int(DMAX))
    # Magic number. Indicates number of entries to follow. Put in 1 for GROUP
    if GROUP == "":
        packer.pack_int(0)
    else:
        packer.pack_int(1)
        packer.pack_string("GROUP")
        packer.pack_string(GROUP)

    # Actual data sent in a separate packet
    data = Packer()
    data.pack_int(128+5)
    if SPOOFENABLED == 1:
        data.pack_string(SPOOF)
    else:
        data.pack_string(HOSTNAME)
    data.pack_string(NAME)
    data.pack_int(SPOOFENABLED)
    data.pack_string("%s")
    data.pack_string(str(VAL))

    return ( packer.get_buffer() ,  data.get_buffer() )

def gmetric_read(msg):
    unpacker = Unpacker(msg)
    values = dict()
    unpacker.unpack_int()
    values['TYPE'] = unpacker.unpack_string()
    values['NAME'] = unpacker.unpack_string()
    values['VAL'] = unpacker.unpack_string()
    values['UNITS'] = unpacker.unpack_string()
    values['SLOPE'] = slope_int2str[unpacker.unpack_int()]
    values['TMAX'] = unpacker.unpack_uint()
    values['DMAX'] = unpacker.unpack_uint()
    unpacker.done()
    return values

def get_gmetrics(path):
    data = open(path).read()
    start = 0
    out = []
    while True:
        m = re.search('udp_send_channel +\{([^}]+)\}', data[start:], re.M)
        if not m:
            break
        start += m.end()
        tokens = re.split('\s+', m.group(1).strip())
        host = tokens[tokens.index('host')+2]
        port = int(tokens[tokens.index('port')+2])
        out.append(Gmetric(host, port, 'udp'))
    return out



if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("", "--protocol", dest="protocol", default="udp",
                      help="The gmetric internet protocol, either udp or multicast, default udp")
    parser.add_option("", "--host",  dest="host",  default="127.0.0.1",
                      help="GMond aggregator hostname to send data to")
    parser.add_option("", "--port",  dest="port",  default="8649",
                      help="GMond aggregator port to send data to")
    parser.add_option("", "--name",  dest="name",  default="",
                      help="The name of the metric")
    parser.add_option("", "--value", dest="value", default="",
                      help="The value of the metric")
    parser.add_option("", "--units", dest="units", default="",
                      help="The units for the value, e.g. 'kb/sec'")
    parser.add_option("", "--slope", dest="slope", default="both",
                      help="The sign of the derivative of the value over time, one of zero, positive, negative, both, default both")
    parser.add_option("", "--type",  dest="type",  default="",
                      help="The value data type, one of string, int8, uint8, int16, uint16, int32, uint32, float, double")
    parser.add_option("", "--tmax",  dest="tmax",  default="60",
                      help="The maximum time in seconds between gmetric calls, default 60")
    parser.add_option("", "--dmax",  dest="dmax",  default="0",
                      help="The lifetime in seconds of this metric, default=0, meaning unlimited")
    parser.add_option("", "--group",  dest="group",  default="",
                      help="Group metric belongs to. If not specified Ganglia will show it as no_group")
    parser.add_option("", "--spoof",  dest="spoof",  default="",
                      help="the address to spoof (ip:host). If not specified the metric will not be spoofed")
    (options,args) = parser.parse_args()

    g = Gmetric(options.host, options.port, options.protocol)
    g.send(options.name, options.value, options.type, options.units,
           options.slope, options.tmax, options.dmax, options.group, options.spoof)

########NEW FILE########
__FILENAME__ = carbon_plugin
#/*******************************************************************************
#* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS IS''
#* AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#* IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#* ARE DISCLAIMED. IN NO EVENT SHALL Novell, Inc. OR THE CONTRIBUTORS
#* BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#* CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#* SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#* INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#* CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#* ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#* POSSIBILITY OF SUCH DAMAGE.
#*
#* Authors: Avishai Ish-Shalom (avishai AT fewbytes.com)
#*
#* This is a gmetad-python plugin for sending metrics to carbon-cache.
#******************************************************************************/

import logging
import socket
import pickle
import struct
import string

from Gmetad.gmetad_plugin import GmetadPlugin
from Gmetad.gmetad_config import getConfig, GmetadConfig

def get_plugin():
    ''' All plugins are required to implement this method.  It is used as the factory
        function that instanciates a new plugin instance. '''
    # The plugin configuration ID that is passed in must match the section name 
    #  in the configuration file.
    return CarbonPlugin('carbon-writer')

class CarbonPlugin(GmetadPlugin):
    ''' This class implements a carbon plugin which sends metrics to carbon-cache via line reciever'''
    
    _strucFormat = '!I'
    MAX_METRICS_PER_OP = 20
    _tr_table = string.maketrans(" .", "__")

    def __init__(self, cfgid):
        logging.debug("Initializing carbon-writer plugin")
        self.cfg = None
        self.carbon_socket = None
        self._resetConfig()
        
        logging.debug("Initialized carbon writer plugin")
        # The call to the parent class __init__ must be last
        GmetadPlugin.__init__(self, cfgid)

    def _resetConfig(self):
        self.sendMetrics = self._sendTextMetrics
        self.carbon_host = None
        self.carbon_port = None

    def _parseConfig(self, cfgdata):
        logging.debug("Parsing configdata %s" % cfgdata)
        for kw, args in cfgdata:
            if hasattr(self, '_cfg_' + kw):
                getattr(self, '_cfg_' + kw)(args)
            else:
                raise Exception('Wrong configuration directive %s' % kw)

    def _cfg_host(self, host):
        if ":" in host:
            host, port = host.split(":", 1)
            self._cfg_port(port)
        self.carbon_host = host

    def _cfg_port(self, port):
        self.carbon_port = int(port)

    def _cfg_protocol(self, protocol):
        protocol = protocol.lower().strip()
        if protocol == "pickle":
            self.sendMetrics = self._sendPickledMetrics
        elif protocol == "text" or protocol == "line" or protocol == "plain":
            self.sendMetrics = self._sendTextMetrics
        else:
            raise Exception("Unknown protocol type %s" % protocol)

    @classmethod
    def _carbonEscape(cls, s):
        if type(s) is not str: s = str(s)
        return s.translate(cls._tr_table)

    def _connectCarbon(self):
        self._closeConnection()
        logging.debug("Connecting to carbon at %s:%d" % (self.carbon_host, self.carbon_port))
        if self.carbon_host is None or self.carbon_port is None:
            logging.warn("can't connect. carbon host: %s, port %d" % (self.carbon_host, self.carbon_port))
            return
        try:
            self.carbon_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            self.carbon_socket.connect((self.carbon_host, self.carbon_port))
        except socket.error as e:
            if not e.errno == 106:
                raise e
        logging.debug("Connected to carbon at %s:%d" % (self.carbon_host, self.carbon_port))

    def _closeConnection(self):
        if self.carbon_socket:
            logging.debug("Closing connection to carbon")
            self.carbon_socket.shutdown(socket.SHUT_RDWR)
            self.carbon_socket.close()
            self.carbon_socket = None

    def _sendPickledMetrics(self, metrics):
        # the pickle protocol used by carbon works by packing metrics into a list/tuple, each item packed as:
        # (metric_name, (timstamp, value))
        try:
            # we use sendall because we trust items won't be unpickled if something bad happens. worse case we lose entire metrics batch.
            logging.info("Sending pickled data to carbon")
            logging.debug("Metrics (dump):\n%s" % metrics)
            data = pickle.dumps(
                    # convert metrics to (metric_name, (timestamp, value)) format
                    [(metric_name, (timestamp, value)) for (metric_name, timestamp, value) in metrics],
                    protocol=-1
                    )
            data = struct.pack(self._strucFormat, len(data)) + data
            total_sent_bytes = 0
            while total_sent_bytes < len(data):
                sent_bytes = self.carbon_socket.send(data[total_sent_bytes:])
                if sent_bytes == 0: raise Exception("Zero bytes sent, connection error?")
                logging.debug("Sent %d bytes to carbon" % sent_bytes)
                total_sent_bytes += sent_bytes
            logging.debug("Done sending pickled data to carbon")

        except Exception as e:
           logging.error("Failed to send metrics to carbon:\n%s" % e)
           self._connectCarbon()
    
    def _sendTextMetrics(self, metrics):
        for metric in metrics:
            try:
                logging.debug("Sending text data to carbon")
                self.carbon_socket.sendall(" ".join(metric))
            except Exception as e:
                logging.error("Failed to send metrics to carbon:\n%s" % e)
                self._connectCarbon()

    def start(self):
        '''Called by the engine during initialization to get the plugin going.'''
        logging.debug("Starting plugin carbon-writer")
        self._connectCarbon()
    
    def stop(self):
        '''Called by the engine during shutdown to allow the plugin to shutdown.'''
        logging.debug("Stopping plugin carbon-writer")
        self._closeConnection()

    def notify(self, clusterNode):
        '''Called by the engine when the internal data source has changed.'''
        # Get the current configuration
        if 'GRID' == clusterNode.id:
            # we don't need aggregation by GRID, this can be easily done in grpahite
            return
        gmetadConfig = getConfig()
        # Find the data source configuration entry that matches the cluster name
        for ds in gmetadConfig[GmetadConfig.DATA_SOURCE]:
            if ds.name == clusterNode.getAttr('name'):
                break
        if ds is None:
            logging.info('No matching data source for %s'%clusterNode.getAttr('name'))
            return
        try:
            if clusterNode.getAttr('status') == 'down':
                return
        except AttributeError:
            pass

        # Update metrics for each host in the cluster
        self.sendMetrics([
                (".".join(
                    ("ganglia", self._carbonEscape(clusterNode.getAttr('name')),
                        self._carbonEscape(hostNode.getAttr('name')),
                        metricNode.getAttr('name'))
                        ), # metric name
                    int(hostNode.getAttr('REPORTED')) + int(metricNode.getAttr('TN')), float(metricNode.getAttr('VAL')))
                    for hostNode in clusterNode
                    for metricNode in hostNode
                if metricNode.getAttr('type') not in ('string', 'timestamp' )
                ]
        )


########NEW FILE########
__FILENAME__ = daemon
#
# This is the MIT License
# http://www.opensource.org/licenses/mit-license.php
#
# Copyright (c) 2007,2008 Nick Galbreath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import os
import sys

#http://www.noah.org/wiki/Daemonize_Python
def daemonize (stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
  
    # Do first fork.
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)   # Exit first parent.
    except OSError, e:
        sys.stderr.write ("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror) )
        sys.exit(1)
 
    # Decouple from parent environment.
    os.chdir("/")
    os.umask(0)
    os.setsid()
 
    # Do second fork.
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)   # Exit second parent.
    except OSError, e:
        sys.stderr.write ("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror) )
        sys.exit(1)
 
    # Now I am a daemon!
 
    # Redirect standard file descriptors.
    si = open(stdin, 'r')
    so = open(stdout, 'a+')
    se = open(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


def drop_privileges(uid_name='nobody', gid_name='nogroup'):
    import pwd, grp

    starting_uid = os.getuid()
    starting_gid = os.getgid()

    starting_uid_name = pwd.getpwuid(starting_uid)[0]

    if os.getuid() != 0:
        # We're not root so, like, whatever dude
        return

    if starting_uid == 0:

        # Get the uid/gid from the name
        running_uid = pwd.getpwnam(uid_name)[2]
        #running_gid = grp.getgrnam(gid_name)[2]

        # Try setting the new uid/gid
        #os.setgid(running_gid)
        os.setuid(running_uid)

        new_umask = 077
        old_umask = os.umask(new_umask)
        sys.stderr.write('drop_privileges: Old umask: %s, new umask: %s\n' % \
                             (oct(old_umask), oct(new_umask)))
        
    final_uid = os.getuid()
    final_gid = os.getgid()
    sys.stderr.write('drop_privileges: running as %s/%s\n' % \
                         (pwd.getpwuid(final_uid)[0],
                          grp.getgrgid(final_gid)[0]))


########NEW FILE########
__FILENAME__ = ggraph
#!/usr/bin/env python

import urllib2
import os.path
import os
import time

import rrdtool
from lxml import etree

def make_graph_load(dir, imgdir, host, duration, width='400'):
    """
    Specialized fform for Load Graphs
    """

    print "HOST = " + host
    # this oculd be imporved by just reusing the 1-m load
    # instead of using 1,5,15 metrics, but whatever
    
    f = host + '-load-' + str(duration) + '-' + str(width) + '.png' 
    imgfile = os.path.join(imgdir, f)

    # if less than X seconds old, just return imgfile
    
    load1_rrdfile = os.path.join(dir, host, "load_one.rrd")
    load5_rrdfile = os.path.join(dir, host, "load_five.rrd")
    load15_rrdfile = os.path.join(dir, host, "load_fifteen.rrd")
    
    rrdtool.graph(imgfile,
                  '--end', 'now',
                  '--start', 'end-' + str(duration),
                  '--width', str(width),
                  '--imgformat', 'PNG',
                  '--lower-limit', '0',
                  '--title', 'Load',
                  'DEF:l1=' + load1_rrdfile + ':load_one:AVERAGE',
                  'DEF:l5=' + load5_rrdfile + ':load_five:AVERAGE',
                  'DEF:l15=' + load15_rrdfile + ':load_fifteen:AVERAGE',
                  'AREA:l1#0000FF:load 1',
                  'LINE3:l1#000000',
                  'LINE3:l5#00FF00:load 5',
                  'LINE3:l15#FF0000:load 15'
                  )
    
    return imgfile

def make_graph_cpu(dir, imgdir, host, duration, width='400'):
    """
    Specialized form for CPU graphs
    """
    
    f = host + '-cpu-' + duration + '-' + str(width) + '.png' 
    imgfile = os.path.join(imgdir, f)
    
    sys_rrdfile = os.path.join(dir, host, "cpu_system.rrd")
    user_rrdfile = os.path.join(dir, host, "cpu_user.rrd")
    nice_rrdfile = os.path.join(dir, host,  "cpu_nice.rrd")
    
    rrdtool.graph(imgfile,
                  '--end', 'now',
                  '--start', 'end-' + duration,
                  '--width', str(width),
                  '--imgformat', 'PNG',
                  '--lower-limit', '0',
                  '--upper-limit', '100',
                  '--title', 'CPU Usage',
                  'DEF:sys=' + sys_rrdfile + ':cpu_system:AVERAGE',
                  'DEF:user=' + user_rrdfile + ':cpu_user:AVERAGE',
                  'DEF:nice=' + nice_rrdfile + ':cpu_nice:AVERAGE',
                  'AREA:sys#0000FF:"cpu system"',
                  'AREA:user#00FF00:"cpu user":STACK',
                  'AREA:nice#FF0000:"cpu nice":STACK'
                  )
    return imgfile

def make_graph_network(dir, imgdir, host, duration, width='400'):
    """
    Specialized form for network graphs
    """
    
    f = host + '-network-' + duration + '-' + str(width) + '.png' 
    imgfile = os.path.join(imgdir, f)
    
    bytesin_rrdfile = os.path.join(dir, host, "bytes_in.rrd")
    bytesout_rrdfile = os.path.join(dir, host,  "bytes_out.rrd")
    print bytesin_rrdfile
    
    rrdtool.graph(imgfile,
                  '--end', 'now',
                  '--start', 'end-' + duration,
                  '--width', str(width),
                  '--imgformat', 'PNG',
                  '--lower-limit', '0',
                  '--title', 'Network Bytes',
                  'DEF:bi=' + bytesin_rrdfile + ':bytes_in:AVERAGE',
                  'DEF:bo=' + bytesout_rrdfile + ':bytes_out:AVERAGE',
                  'LINE1:bi#0000FF:bytes in',
                  'LINE1:bo#FF0000:bytes out'
                  )
    return imgfile

def make_graph_memory(dir, imgdir, host, duration, width='400'):
    """
    Specialized form for CPU graphs
    """
    
    f = host + '-memory-' + duration + '-' + str(width) + '.png' 
    imgfile = os.path.join(imgdir, f)
    
    mem_rrdfile = os.path.join(dir, host, "mem_used_percent.rrd")
    swap_rrdfile = os.path.join(dir, host, "swap_used_percent.rrd")
    disk_rrdfile = os.path.join(dir, host, "disk_used_percent.rrd")
    
    rrdtool.graph(imgfile,
                  '--end', 'now',
                  '--start', 'end-' + duration,
                  '--width', str(width),
                  '--imgformat', 'PNG',
                  '--lower-limit', '0',
                  '--upper-limit', '100',
                  
                  '--title', '% of Memory,Swap,Disk Used',
                  'DEF:bi=' + mem_rrdfile + ':mem_used_percent:AVERAGE',
                  'DEF:bo=' + swap_rrdfile + ':swap_used_percent:AVERAGE',
                  'DEF:disk=' + disk_rrdfile + ':disk_used_percent:AVERAGE',
                  'LINE1:bi#0000FF:memory used',
                  'LINE1:bo#FF0000:swap used',
                  'LINE1:disk#00FF00:disk used'
                  )
    return imgfile

def make_graph(dir, imgdir, host, metric, duration, width='400'):
    #--end now --start end-120000s --width 400
    
    if metric == 'cpu':
        return make_graph_cpu(dir,imgdir,host,duration,width)
    if metric == 'network':
        return make_graph_network(dir,imgdir,host,duration,width)
    if metric == 'memory':
        return make_graph_memory(dir,imgdir,host,duration,width)
    if metric == 'load':
        return make_graph_load(dir,imgdir,host,duration,width)
    
    f = str(host) + '-' + metric + '-' + str(duration) + '-' + str(width) + '.png'
    
    imgfile = os.path.join(imgdir, f)
    rrdfile = os.path.join(dir,  host, metric + ".rrd")
    print rrdfile
    rrdtool.graph(imgfile,
                  '--end', 'now',
                  '--start', 'end-' + duration,
                  '--width', '400',
                  '--imgformat', 'PNG',
                  '--title', metric,
                  'DEF:ds0a=' + rrdfile + ':' + metric + ':AVERAGE',
                  'LINE1:ds0a#0000FF:"default resolution\l"'
                  )
    return imgfile

if __name__ == '__main__':

    host = '172.16.70.128'
    rrddir = '/tmp'
    imgdir = '/tmp'
    
    make_graph(rrddir, imgdir, host, 'cpu_idle', '300s')
    make_graph_cpu(rrddir, imgdir, host, '300s')
    make_graph_load(rrddir, imgdir, host, '300s')
    make_graph_network(rrddir, imgdir, host, '300s')
    make_graph_memory(rrddir, imgdir, host, '300s')

    

########NEW FILE########
__FILENAME__ = gimport
#!/usr/bin/env python

# SYSTEM
import urllib2
import os.path
import os
import time
import sys
import logging    

# 3RD PARTY
import rrdtool
from lxml import etree

# LOCAL
import gparse

def rrd_update(rrdfile, name, value, slope):

    # fix annoying unicode issues
    rrdfile = str(rrdfile)
    
    dstype = 'GAUGE'
    if slope == 'zero':
        dstype = 'ABSOLUTE'
        # for now don't care about invariants
        return
    elif slope == 'both':
        dstype = 'GAUGE'
    elif slope == 'positive':
        dstype = 'COUNTER'
        
    token = 'DS:' + name + ':' + dstype + ':60:U:U'
    if not os.path.exists(rrdfile):
        logging.info("Creating %s\n", rrdfile)
        # 1440 is minutes per day
        # 300 minutes = 5 hours
        # 30 hours = 1800 minutes
        rrdtool.create(rrdfile, '--step=20', token,
                       # 1 point at 20s, 900 of them 300m, 5 hours
                       'RRA:AVERAGE:0.5:1:900',
                       # 3 points @ 20s = 60s = 1m, 30 hours
                       'RRA:AVERAGE:0.5:3:1800'
                       )
        # no else
    svalue = str(value)
    logging.debug("Updating '%s' with value of '%s'", rrdfile, svalue)
    rrdtool.update(rrdfile, 'N:' + svalue)

def make_standard_rrds(hosts, dir):
    """
    walks the host mappings and makes
    specialized graphs for various metrics
    """
    for host, metrics in hosts.iteritems():
        path = os.path.join(dir, host)
        if not os.path.isdir(path):
            os.mkdir(path)

        for mname, val in metrics.iteritems():
            # stuff we don't care about
            if mname in ('boottime', 'gexec', 'machine_type', 'os_name',
                         'os_release'):
                continue
            if mname.startswith('multicpu_') or mname.startswith('pkts_'):
                continue

            # these are handled differently
            if mname.startswith('mem_') or \
                   mname.startswith('swap_') or \
                   mname.startswith('disk_'):
                continue
            
            rrdfile = os.path.join(path, mname + ".rrd")
            #print "Adding %s = %s" % (mname, val)
            rrd_update(rrdfile, mname, val, 'both')

        # gmond reports "total" and "used" (absolute numbers)
        #   making rrds of both isn't very useful
        # so I merge them and make a consolidated version
        # of "% of total used" which is normally more interesting
            
        mem_total = float(metrics['mem_total'])
        mem_free = float(metrics['mem_free'])
        name = 'mem_used_percent'
        rrdfile = os.path.join(path, name + ".rrd")
        rrd_update(rrdfile, name, 100.0 *
                   (1.0 - mem_free / mem_total), 'both')
        
        swap_total = float(metrics['swap_total'])
        swap_free  = float(metrics['swap_free'])
        name = 'swap_used_percent'
        rrdfile = os.path.join(path, name + ".rrd")
        rrd_update(rrdfile, name, 100.0 *
                   (1.0 - swap_free / swap_total), 'both')
        
        disk_total = float(metrics['disk_total'])
        disk_free  = float(metrics['disk_free'])
        name = 'disk_used_percent'
        rrdfile = os.path.join(path, name + ".rrd")
        rrd_update(rrdfile, name, 100.0 *
                   (1.0 - disk_free / disk_total), 'both')


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("", "--host", dest="host",
                      help="host", default="localhost");    
    parser.add_option("-p", "--port", dest="port",
                      help="port", default=8649);
    parser.add_option("-d", "--dir", dest="dir", default='/tmp',
                      help="directory to write RRD files")
    parser.add_option("-s", "--sleep", dest="sleep", default=20,
                      help="seconds to sleep between intervals")
    parser.add_option("-l", "--log", dest="log", default='warning',
                      help="log level: [ debug | info | warn | error ]")
    options, args = parser.parse_args()

    host = options.host
    port = int(options.port)
    dir = options.dir
    sleep = int(options.sleep)
    log = options.log.lower()
    if log == 'debug':
        loglevel = logging.DEBUG
    elif log == 'info':
        loglevel = logging.INFO
    elif log == 'warn' or log == 'warning':
        loglevel = logging.WARNING
    elif log == 'err' or log == 'error':
        loglevel = logging.ERROR

    logging.basicConfig(level=loglevel)
    
    logging.info("Using %s:%d and directory %s" % (host,port,dir))

    # now do checks

    # is dir a directory
    if not os.path.isdir(dir):
        logging.error("Directory '%s' does not exist. Exiting", dir)
        sys.exit(1)

    # can we write to it?
    # this is the LAME way of doing this
    try:
        tmpfile = os.path.join(dir, 'tmp')
        f = open(tmpfile, 'w')
        f.close()
        os.remove(tmpfile)
    except:
        logging.error("Directory '%s' is not writable. Exiting", dir)
        sys.exit(1)
        
    try:
        xml = gparse.read(host, port)
    except Exception,e:
        logging.error("Read of %s:%d failed -- is gmond running?  Exiting",
                      host, port)
        sys.exit(1)

    while True:
        try:
            logging.debug("Reading from %s:%d", host, port)
            t0 = time.time()
            xml = gparse.read(host, port)
            secs = time.time() - t0;
            logging.debug("Reading took %fs", secs)
            logging.debug("Parsing XML")
            t0 = time.time()
            hosts = gparse.parse(xml)
            secs = time.time() - t0;
            logging.debug("Parsing took %fs", secs)

            logging.debug("Inserting...")
            t0 = time.time()
            make_standard_rrds(hosts, dir)
            secs = time.time() - t0;
            logging.debug("Inserts took %fs", secs)
        except Exception,e:
            logging.error("Exception!: %s", str(e))

        logging.debug("Sleeping for %ds....\n", sleep)
        time.sleep(sleep)


########NEW FILE########
__FILENAME__ = gmetric
#!/usr/bin/env python

# This is the MIT License
# http://www.opensource.org/licenses/mit-license.php
#
# Copyright (c) 2007,2008 Nick Galbreath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

#
# Version 1.0 - 21-Apr-2007
#   initial
# Version 2.0 - 16-Nov-2008
#   made class Gmetric thread safe
#   made gmetrix xdr writers _and readers_
#   Now this only works for gmond 2.X packets, not tested with 3.X
#
# Version 3.0 - 09-Jan-2011 Author: Vladimir Vuksan
#   Made it work with the Ganglia 3.1 data format
#
# Version 3.1 - 30-Apr-2011 Author: Adam Tygart
#   Added Spoofing support


from xdrlib import Packer, Unpacker
import socket

slope_str2int = {'zero':0,
                 'positive':1,
                 'negative':2,
                 'both':3,
                 'unspecified':4}

# could be autogenerated from previous but whatever
slope_int2str = {0: 'zero',
                 1: 'positive',
                 2: 'negative',
                 3: 'both',
                 4: 'unspecified'}


class Gmetric:
    """
    Class to send gmetric/gmond 2.X packets

    Thread safe
    """

    type = ('', 'string', 'uint16', 'int16', 'uint32', 'int32', 'float',
            'double', 'timestamp')
    protocol = ('udp', 'multicast')

    def __init__(self, host, port, protocol):
        if protocol not in self.protocol:
            raise ValueError("Protocol must be one of: " + str(self.protocol))

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if protocol == 'multicast':
            self.socket.setsockopt(socket.IPPROTO_IP,
                                   socket.IP_MULTICAST_TTL, 20)
        self.hostport = (host, int(port))
        #self.socket.connect(self.hostport)

    def send(self, NAME, VAL, TYPE='', UNITS='', SLOPE='both',
             TMAX=60, DMAX=0, GROUP="", SPOOF=""):
        if SLOPE not in slope_str2int:
            raise ValueError("Slope must be one of: " + str(self.slope.keys()))
        if TYPE not in self.type:
            raise ValueError("Type must be one of: " + str(self.type))
        if len(NAME) == 0:
            raise ValueError("Name must be non-empty")

        ( meta_msg, data_msg )  = gmetric_write(NAME, VAL, TYPE, UNITS, SLOPE, TMAX, DMAX, GROUP, SPOOF)
        # print msg

        self.socket.sendto(meta_msg, self.hostport)
        self.socket.sendto(data_msg, self.hostport)

def gmetric_write(NAME, VAL, TYPE, UNITS, SLOPE, TMAX, DMAX, GROUP, SPOOF):
    """
    Arguments are in all upper-case to match XML
    """
    packer = Packer()
    HOSTNAME="test"
    if SPOOF == "":
        SPOOFENABLED=0
    else :
        SPOOFENABLED=1
    # Meta data about a metric
    packer.pack_int(128)
    if SPOOFENABLED == 1:
        packer.pack_string(SPOOF)
    else:
        packer.pack_string(HOSTNAME)
    packer.pack_string(NAME)
    packer.pack_int(SPOOFENABLED)
    packer.pack_string(TYPE)
    packer.pack_string(NAME)
    packer.pack_string(UNITS)
    packer.pack_int(slope_str2int[SLOPE]) # map slope string to int
    packer.pack_uint(int(TMAX))
    packer.pack_uint(int(DMAX))
    # Magic number. Indicates number of entries to follow. Put in 1 for GROUP
    if GROUP == "":
        packer.pack_int(0)
    else:
        packer.pack_int(1)
        packer.pack_string("GROUP")
        packer.pack_string(GROUP)

    # Actual data sent in a separate packet
    data = Packer()
    data.pack_int(128+5)
    if SPOOFENABLED == 1:
        data.pack_string(SPOOF)
    else:
        data.pack_string(HOSTNAME)
    data.pack_string(NAME)
    data.pack_int(SPOOFENABLED)
    data.pack_string("%s")
    data.pack_string(str(VAL))

    return ( packer.get_buffer() ,  data.get_buffer() )

def gmetric_read(msg):
    unpacker = Unpacker(msg)
    values = dict()
    unpacker.unpack_int()
    values['TYPE'] = unpacker.unpack_string()
    values['NAME'] = unpacker.unpack_string()
    values['VAL'] = unpacker.unpack_string()
    values['UNITS'] = unpacker.unpack_string()
    values['SLOPE'] = slope_int2str[unpacker.unpack_int()]
    values['TMAX'] = unpacker.unpack_uint()
    values['DMAX'] = unpacker.unpack_uint()
    unpacker.done()
    return values


if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("", "--protocol", dest="protocol", default="udp",
                      help="The gmetric internet protocol, either udp or multicast, default udp")
    parser.add_option("", "--host",  dest="host",  default="127.0.0.1",
                      help="GMond aggregator hostname to send data to")
    parser.add_option("", "--port",  dest="port",  default="8649",
                      help="GMond aggregator port to send data to")
    parser.add_option("", "--name",  dest="name",  default="",
                      help="The name of the metric")
    parser.add_option("", "--value", dest="value", default="",
                      help="The value of the metric")
    parser.add_option("", "--units", dest="units", default="",
                      help="The units for the value, e.g. 'kb/sec'")
    parser.add_option("", "--slope", dest="slope", default="both",
                      help="The sign of the derivative of the value over time, one of zero, positive, negative, both, default both")
    parser.add_option("", "--type",  dest="type",  default="",
                      help="The value data type, one of string, int8, uint8, int16, uint16, int32, uint32, float, double")
    parser.add_option("", "--tmax",  dest="tmax",  default="60",
                      help="The maximum time in seconds between gmetric calls, default 60")
    parser.add_option("", "--dmax",  dest="dmax",  default="0",
                      help="The lifetime in seconds of this metric, default=0, meaning unlimited")
    parser.add_option("", "--group",  dest="group",  default="",
                      help="Group metric belongs to. If not specified Ganglia will show it as no_group")
    parser.add_option("", "--spoof",  dest="spoof",  default="",
                      help="the address to spoof (ip:host). If not specified the metric will not be spoofed")
    (options,args) = parser.parse_args()

    g = Gmetric(options.host, options.port, options.protocol)
    g.send(options.name, options.value, options.type, options.units,
           options.slope, options.tmax, options.dmax, options.group, options.spoof)
########NEW FILE########
__FILENAME__ = gparse
#!/usr/bin/env python

# This is the MIT License
# http://www.opensource.org/licenses/mit-license.php
#
# Copyright (c) 2009 Nick Galbreath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import socket
from lxml import etree

def parse(s):
    hosts = {}
    root = etree.XML(s)
    # newer versions could do:
    #for host in root.iter('HOST'):    
    for host in root.findall('HOST'):
        name = host.get('NAME')
        hosts[name] = {}
        metrics = hosts[name]
        # new versions of lxml could do
        #for m in host.iter('METRIC'):
        for m in host.findall('METRIC'):
            metrics[m.get('NAME')] = m.attrib.get("VAL")
    return hosts
        
def read(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    data = ""
    while True:
        bytes = s.recv(4096)
        if len(bytes) == 0:
            break;
        data += bytes
    s.close()
    return data

if __name__ == '__main__':

    s = read('localhost', 8649)
    hosts = parse(s)
    for h in hosts:
        print h
        keys = sorted(hosts[h])
        for k in keys:
            print "   %s = %s" % (k,hosts[h][k])
            


########NEW FILE########
__FILENAME__ = gweb
#!/usr/bin/env python

#
# SUPER LOW LEVEL WEBSERVER
# Sorta like CGI if anyone remembers that
#
#
from wsgiref.simple_server import make_server
from wsgiref.util import FileWrapper
from wsgiref.util import shift_path_info
import cgi
import mimetypes
import os.path
import glob
import os.path
import gparse
import ggraph

static_root = '.'
rrd_root = '/tmp'
img_root = '/tmp'

def sendfile(fname, start_response):
    status =  "200 OK"
    mtype = 'text/plain'
    try:
        f = open(fname, 'r'); data = f.read(); f.close()
        m = mimetypes.guess_type(fname)
        if m[0] is not None: mtype = m[0]
    except IOError,e:
        data = str(e) + '\n'
        status = "404 Not Found"
    start_response(status, [('Content-Type', mtype)])
    return [ data ]

def static(environ, start_response):
    # shift PATH_INFO /static/foo ----> /foo
    # then skip first '/'
    # and merge with static_root
    shift_path_info(environ)
    filename = os.path.abspath(os.path.join(static_root,
                                            environ['PATH_INFO'][1:]))
    return sendfile(fname, start_response)

def overview(environ, start_response):
    qs = cgi.parse_qs(environ['QUERY_STRING'])
    host     = qs['host'][0]
    duration = qs['duration'][0]
    width    = qs['width'][0]
    status = '200 OK'
    headers = [('Content-type', 'text/html')]
    start_response(status, headers)
    html = ["<html><head><title>%s</title></head><body><ul>" % host]
    for metric in ('cpu', 'memory', 'load', 'network'):
        html.append('<img src="/rrd?host=%s&metric=%s&duration=%s&width=%s" />' % (host, metric, duration, width))
    html.append("</body></html>")
    return html

def hostlist(environ, start_response):
    # just get everyfile underneath 'rrd_root' and see
    #   if they are a directorya
    hosts = []
    files = glob.glob(rrd_root + '/*')
    for f in files:
        if os.path.isdir(f):
            hosts.append(os.path.basename(f))
    status = '200 OK'
    headers = [('Content-type', 'text/html')]
    start_response(status, headers)
    html = ["<html><head><title>HOSTS</title></head><body><ul>"]
    for h in hosts:
        html.append('<li><a href="/overview?host=%s&width=400&duration=1800s">%s</a></li>\n' % (h,h))
    html.append("""</ul></body></html>""")
    return html
    
def rrd(environ, start_response):
    shift_path_info(environ)
    filename = os.path.abspath(os.path.join(static_root,
                                            environ['PATH_INFO'][1:]))
    qs = cgi.parse_qs(environ['QUERY_STRING'])
    host = qs['host'][0]
    metric = qs['metric'][0]
    duration = qs['duration'][0]
    
    # optional
    width = 400
    if 'width' in qs:
        width = int(qs['width'][0])

    fname = ggraph.make_graph(rrd_root, img_root, host, metric, duration, width)
    
    return sendfile(fname, start_response)

# just for debugging
def echo(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    start_response(status, headers)
    text = []
    keys = sorted(environ.keys())
    for k in keys:
        text.append("%s = %s\n" % (k,environ[k]))
    return text

def dispatch(environ, start_response):
    path = environ['PATH_INFO']
    if path == '/':
        return hostlist(environ, start_response)
    if path == '/overview':
        return overview(environ, start_response)
    if path == '/echo':
        return echo(environ, start_response)
    if path == '/rrd':
        return rrd(environ, start_response)

    # remap common webby things into the static directory
    if path == '/favicon.txt' or path == '/robots.txt':
        path = '/static' + path
        environ['PATH_INFO'] = path
    if path.startswith('/static'):
        return static(environ, start_response)

    # nothing matched, do 404
    status = "404 Not Found"
    start_response(status, [('Content-Type', 'text/plain')])
    return [ "%s not found" % path ]


if __name__ == '__main__':
    httpd = make_server('', 8000, dispatch)
    print "Serving on port 8000..."

    # Serve until process is killed
    httpd.serve_forever()

########NEW FILE########
__FILENAME__ = metric
# This is the MIT License
# http://www.opensource.org/licenses/mit-license.php
#
# Copyright (c) 2007,2008 Nick Galbreath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import traceback
import sys

class metric(object):
    def __init__(self):
        self.tree = None

    def addMetric(self, values):
        self.tree.addMetric(values)

    def register(self, s, tree):
        if self.tree is None:
            self.tree = tree

        self.gather(tree)
        s.enter(self.interval(), 1, self.register, [s, tree])

    def startup(self):
        pass

    def interval(self):
        return 15

    def gather(self):
        pass

    def shutdown(self):
        pass


########NEW FILE########
__FILENAME__ = metrics_darwin
# This is the MIT License
# http://www.opensource.org/licenses/mit-license.php
#
# Copyright (c) 2007,2008 Nick Galbreath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

"""
Core metrics for Darwin (uhhh Mac OS X).

Tested on Mac OSX 10.5
"""

from subprocess import Popen, PIPE
from time import time

from metric import metric

class metric_proc(metric):

    def interval(self):
        return 80

    def gather(self, tree):
        p = Popen(['ps', '-ax'],  stdout=PIPE)    
        lines = p.stdout.read().split('\n')
        self.addMetric({'NAME':'proc_total', 'VAL':len(lines) -1,
                        'TYPE':'uint32', 'UNITS':'', 'TMAX':950,
                        'DMAX':0, 'SLOPE':'zero'})    
        
class metric_sys_clock(metric):
    def interval(self):
        return 1200

    def gather(self, tree):
        self.addMetric({'NAME':'sys_clock', 'VAL':int(time()),
                        'TYPE':'timestamp', 'UNITS':'s', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero'})    

class metric_cpu(metric):
    def interval(self):
        return 20

    def gather(self, tree):
        sysctls = [ 'sysctl',
                    'hw.ncpu',
                    'hw.cpufrequency',
                    'hw.memsize',
                    'kern.boottime',
                    'kern.ostype',
                    'kern.osrelease',
                    'hw.machine'
                    ]
        p = Popen(sysctls, stdout=PIPE)
        lines = p.stdout.read().split('\n')

        val = lines[0].split(' ')[1]
        self.addMetric({'NAME':'cpu_num', 'VAL':val,
                        'TYPE':'uint16', 'UNITS':'', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero'})

        val = lines[1].split(' ')[1]
        self.addMetric({'NAME':'cpu_speed', 'VAL': int(val) / 1000000,
                        'TYPE':'uint32', 'UNITS':'MHz', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero'})

        val = lines[2].split(' ')[1]
        self.addMetric({'NAME':'mem_total', 'VAL': int(val) / 1024,
                        'TYPE':'uint32', 'UNITS':'KB', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero'})
        
        val = lines[3].split(' ')[4].strip(',')
        self.addMetric({'NAME':'boottime', 'VAL': int(val),
                        'TYPE':'uint32', 'UNITS':'KB', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero'})

        val = lines[4].split(' ')[1]
        self.addMetric({'NAME':'os_name', 'VAL':val,
                        'TYPE':'string', 'UNITS':'', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero'})

        val = lines[5].split(' ')[1]
        self.addMetric({'NAME':'os_release', 'VAL':val,
                        'TYPE':'string', 'UNITS':'', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})

        val = lines[6].split(' ')[1]
        self.addMetric({'NAME':'machine_type', 'VAL':val,
                        'TYPE':'string', 'UNITS':'', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})


class metric_net(metric):
    last_time = time()
    last_out = -1
    last_in = -1

    def interval(self):
        return 40

    def gather(self, tree):
        now = time()
        interval = self.last_time - now

        p = Popen(['sysctl',
                   'net.inet.tcp.out_sw_cksum_bytes',
                   'net.inet.udp.out_sw_cksum_bytes',
                   'net.inet.tcp.in_sw_cksum_bytes',
                   'net.inet.udp.in_sw_cksum_bytes'], stdout=PIPE)

        lines = p.stdout.read().split('\n')
        tcp_out = int(lines[0].split(' ')[1])
        udp_out = int(lines[1].split(' ')[1])
        tcp_in = int(lines[2].split(' ')[1])
        udp_in = int(lines[3].split(' ')[1])
        
        total_out = tcp_out + udp_out
        total_in  = tcp_in + udp_in


        # Ideally you'd just return total_out and total_in
        # and let RRD figure out bytes/sec using a COUNTER

        # BUT, oddly  "official" gmond returns bytes per second 
        # which seems odd.  So sadly, we have do all this nonsense
        if self.last_out == -1:
            self.last_out  = total_out
            self.last_in  = total_in
            return
        
        out_bps = float(total_out - self.last_out) / interval
        in_bps = float(total_in - self.last_in) / interval
        self.last_time = time()
        self.last_out = total_out
        self.last_in = total_in

        self.addMetric({'NAME':'bytes_in', 'VAL':in_bps,
                        'TYPE':'float', 'UNITS':'bytes/sec',
                        'TMAX':300, 'DMAX': 0, 'SLOPE':'both',
                        'SOURCE':'gmond'})

        self.addMetric({'NAME':'bytes_out', 'VAL':out_bps,
                        'TYPE':'float', 'UNITS':'bytes/sec',
                        'TMAX':300, 'DMAX': 0, 'SLOPE':'both',
                        'SOURCE':'gmond'})

class metric_mem(metric):
    """
    parser output of 'vm_stat' (not 'vmstat' ;-) which is like this:

$ vm_stat
Mach Virtual Memory Statistics: (page size of 4096 bytes)
Pages free:                   138536.
Pages active:                  93700.
Pages inactive:                45617.
Pages wired down:             244883.
"Translation faults":      642439019.
Pages copy-on-write:        11321212.
Pages zero filled:         244573300.
Pages reactivated:            498124.
Pageins:                      484456.
Pageouts:                     278246.
"""
    def interval(self):
        return 60

    def gather(self, tree):
        p = Popen(['vm_stat'], stdout=PIPE)
        lines = p.stdout.read().split('\n')
        mem_free = int(lines[1].strip(',').split(':')[1].strip('.').strip()) * 4
        self.addMetric({'NAME':'mem_free', 
                        'VAL' : mem_free,
                        'TYPE':'uint32', 'UNITS':'KB', 'TMAX':180,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        sysctls = ['sysctl', 'vm.swapusage']

        p = Popen(sysctls, stdout=PIPE)
        lines = p.stdout.read().split(' ')

        # lines is now the list:
        # ['vm.swapusage:', 'total', '=', '1024.00M', '',
        #     'used', '=', '590.66M', '', 'free', '=', '433.34M',
        #      '', '(encrypted)\n']

        swap_total = float(lines[3].strip('M')) * 1024
        swap_free  = float(lines[11].strip('M')) * 1024

        self.addMetric({'NAME':'swap_total', 'VAL':int(swap_total),
                        'TYPE':'uint32', 'UNITS':'KB', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})

        self.addMetric({'NAME':'swap_free', 'VAL':int(swap_free),
                        'TYPE':'uint32', 'UNITS':'KB', 'TMAX':180,
                        'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})

        # Bonus - not part of gmond
        #self.addMetric({'NAME':'swap_used', 'VAL':val,
        #                'TYPE':'uint32', 'UNITS':'KB', 'TMAX':180,
        #                'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})


class metric_disk(metric):
    def interval(self):
        return 40

    def gather(self, tree):
        p = Popen(['df', '-m', '/'], stdout=PIPE)
        lines = p.stdout.read().split('\n')
        values = filter(lambda x: len(x), lines[1].split(' '))
        # volume name, size in MB, used in MB, free in MB, %used, mount
        # ['/dev/disk0s2', '111', '89', '22', '81%', '/']
        self.addMetric({'NAME':'disk_total', 
                        'VAL' :float(values[1]) /  1048576.0,
                        'TYPE':'double', 'UNITS':'GB', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

        self.addMetric({'NAME':'disk_free', 
                        'VAL' :float(values[3]) /  1048576.0,
                        'TYPE':'double', 'UNITS':'GB', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})


class metric_iostat(metric):
    def interval(self):
        return 20

    def gather(self, tree):
        p = Popen(['iostat', '-n', '1' '-C'], stdout=PIPE)
        lines = p.stdout.read().split('\n')
        values = filter(lambda x: len(x), lines[2].split(' '))

        self.addMetric({'NAME':'cpu_user', 'VAL':values[3],
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        self.addMetric({'NAME':'cpu_system', 'VAL':values[4],
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        self.addMetric({'NAME':'cpu_idle', 'VAL':values[5],
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        self.addMetric({'NAME':'load_one', 'VAL':values[6],
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        self.addMetric({'NAME':'load_five', 'VAL':values[7],
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        self.addMetric({'NAME':'load_fifteen', 'VAL':values[8],
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})



########NEW FILE########
__FILENAME__ = metrics_linux
#
# This is the MIT License
# http://www.opensource.org/licenses/mit-license.php
#
# Copyright (c) 2007,2008 Nick Galbreath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


"""
Core metrics for Linux

Tested on  Linux Kernel 2.6.27.7.11, Ubuntu 8.10
"""

from subprocess import Popen, PIPE
from time import time

from metric import metric

class metric_proc(metric):
    def interval(self):
        return 80

    def gather(self, tree):
        # slow'n'dumb way of doing this
        # an alternate would be to list /proc
        # and count number of "files' that are "numbers"
        p = Popen(['ps', 'ax'],  stdout=PIPE)    
        lines = p.stdout.read().split('\n')
        self.addMetric({'NAME':'proc_total', 'VAL':len(lines) -1,
                        'TYPE':'uint32', 'UNITS':'', 'TMAX':950,
                        'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})    
        
        # now get running processes
        f = open('/proc/stat', 'rb')
        line = f.read().split('\n')
        f.close()

        proc_run = -1
        for line in lines:
            if line.startswith('procs_running'):
                proc_run = int(line.split()[1])
                break
        if proc_run != -1:
            self.addMetric({'NAME':'proc_run', 'VAL':proc_run,
                            'TYPE':'uint32', 'UNITS':'', 'TMAX':950,
                            'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

class metric_sys_clock(metric):
    def interval(self):
        return 1200

    def gather(self, tree):
        self.addMetric({'NAME':'sys_clock', 'VAL':int(time()),
                        'TYPE':'timestamp', 'UNITS':'s', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})    

class metric_cpu(metric):
    def interval(self):
        return 20

    def gather(self, tree):
        sysctls = [ 'sysctl',
                    'kernel.ostype',
                    'kernel.osrelease',
                    ]
        p = Popen(sysctls, stdout=PIPE)
        lines = p.stdout.read().split('\n')
        os_name = lines[0].split(' ')[1]
        os_release = lines[1].split(' ')[2]
        self.addMetric({'NAME':'os_name', 'VAL':os_name,
                        'TYPE':'string', 'UNITS':'', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})

        self.addMetric({'NAME':'os_release', 'VAL':os_release,
                        'TYPE':'string', 'UNITS':'', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})


        f = open('/proc/uptime', 'rb')
        lines = f.read()
        f.close()
        boottime = int(time() - float(lines.split(' ')[0]))
        self.addMetric({'NAME':'boottime', 'VAL': boottime,
                        'TYPE':'uint32', 'UNITS':'KB', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})

        f = open('/proc/cpuinfo', 'rb')
        lines = f.read().split('\n')
        f.close()

        cpu_num = 0
        cpu_speed = 0
        for line in lines:
            pos = line.find(':')
            if pos != -1:
                k = line[0:pos].strip()
                v = line[pos+1:]
                if k.startswith('processor'):
                    cpu_num += 1
                elif k.startswith('cpu MHz'):
                    # for whatever reason CPUs frequently aren't
                    # nice whole numbers.
                    # use round so you don't have a CPU of 2599
                    cpu_speed = int(round(float(v.strip())))

        if cpu_num > 0:
            self.addMetric({'NAME':'cpu_num', 'VAL': cpu_num,
                            'TYPE':'uint32', 'UNITS':'', 'TMAX':1200,
                            'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})        
        if cpu_speed > 0:
            self.addMetric({'NAME':'cpu_speed', 'VAL': cpu_speed,
                            'TYPE':'uint32', 'UNITS':'MHz', 'TMAX':1200,
                            'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})
            
        # machine type.  gmond hardwires stuff at compile time with
        # a few types.  This is more dynamic
        p = Popen(['uname', '-m'], stdout=PIPE)
        line = p.stdout.read()
        machine_type = line.strip()
        self.addMetric({'NAME':'machine_type', 'VAL':machine_type,
                        'TYPE':'string', 'UNITS':'', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'zero', 'SOURCE':'gmond'})
         
class metric_net(metric):
    last_time = -1

    def interval(self):
        return 40

    def gather(self, tree):
        now = time()
        interval = now - self.last_time

        f = open('/proc/net/dev', 'rb')
        lines = f.read().split('\n')
        f.close()

        bytes_out = 0
        packets_out = 0
        bytes_in = 0
        packets_in = 0

        for line in lines[2:]:
            if not len(line):
                continue
            interface = line[0:7]
            if interface == 'lo':
                # skip loopback interface?
                continue

            fields = line[7:].split()
            bytes_in     += int(fields[0])
            packets_in   += int(fields[1])
            bytes_out    += int(fields[8])
            packets_out  += int(fields[9])
        
        # Ideally you'd just return total_out and total_in
        # and let RRD figure out bytes/sec using a COUNTER
        # and call it a day

        # BUT, oddly  "official" gmond returns bytes per second 
        # which seems odd.  So sadly, we have do all this nonsense
        if self.last_time == -1:
            self.last_time        = now
            self.last_bytes_out   = bytes_out
            self.last_bytes_in    = bytes_in
            self.last_packets_out = packets_out
            self.last_packets_in  = packets_in
            return
        
        bytes_out_bps   = float(bytes_out   - self.last_bytes_out)   / interval
        bytes_in_bps    = float(bytes_in    - self.last_bytes_in)    / interval
        packets_out_bps = float(packets_out - self.last_packets_out) / interval
        packets_in_bps  = float(packets_in  - self.last_packets_in)  / interval

        self.last_time = now
        self.last_bytes_out   = bytes_out
        self.last_bytes_in    = bytes_in
        self.last_packets_out = packets_out
        self.last_packets_in  = packets_in

        self.addMetric({'NAME':'bytes_in', 'VAL':bytes_in_bps,
                        'TYPE':'float', 'UNITS':'bytes/sec',
                        'TMAX':300, 'DMAX': 0, 'SLOPE':'both',
                        'SOURCE':'gmond'})
        self.addMetric({'NAME':'bytes_out', 'VAL':bytes_out_bps,
                        'TYPE':'float', 'UNITS':'bytes/sec',
                        'TMAX':300, 'DMAX': 0, 'SLOPE':'both',
                        'SOURCE':'gmond'})
        self.addMetric({'NAME':'pkts_in', 'VAL':packets_in_bps,
                        'TYPE':'float', 'UNITS':'bytes/sec',
                        'TMAX':300, 'DMAX': 0, 'SLOPE':'both',
                        'SOURCE':'gmond'})
        self.addMetric({'NAME':'pkts_out', 'VAL':packets_out_bps,
                        'TYPE':'float', 'UNITS':'bytes/sec',
                        'TMAX':300, 'DMAX': 0, 'SLOPE':'both',
                        'SOURCE':'gmond'})

class metric_mem(metric):
    """
    boh
    """

    def interval(self):
        return 60

    def gather(self, tree):

        f = open('/proc/meminfo', 'rb')
        lines = f.read().split('\n')
        f.close()
        swap_total  = -1
        swap_free   = -1
        mem_total   = -1
        mem_cached  = -1
        mem_buffers = -1
        mem_free    = -1

        # tbd
        mem_shared  = -1

        for line in lines:
            if line.startswith('SwapTotal'):
                swap_total = int(line.split()[1])
            elif line.startswith('SwapFree'):
                swap_free = int(line.split()[1])
            elif line.startswith('MemTotal'):
                mem_total = int(line.split()[1])
            elif line.startswith('MemFree'):
                mem_free  = int(line.split()[1])
            elif line.startswith('Cached'):
                mem_cached = int(line.split()[1])
            elif line.startswith("Buffers"):
                mem_buffers = int(line.split()[1])

        if swap_total != -1:
            self.addMetric({'NAME':'swap_total','VAL' : swap_total,
                            'TYPE':'uint32', 'UNITS':'KB', 'TMAX':180,
                            'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

        if swap_free != -1:
            self.addMetric({'NAME':'swap_free', 'VAL' : swap_free,
                            'TYPE':'uint32', 'UNITS':'KB', 'TMAX':180,
                            'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

        if mem_cached != -1:
            self.addMetric({'NAME':'mem_cached', 'VAL' : mem_cached,
                            'TYPE':'uint32', 'UNITS':'KB', 'TMAX':180,
                            'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

        if mem_total != -1:
            self.addMetric({'NAME':'mem_total', 'VAL' : mem_total,
                            'TYPE':'uint32', 'UNITS':'KB', 'TMAX':180,
                            'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

        if mem_free != -1:
            self.addMetric({'NAME':'mem_free', 'VAL' : mem_free,
                            'TYPE':'uint32', 'UNITS':'KB', 'TMAX':180,
                            'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

        if mem_buffers != -1:
            self.addMetric({'NAME':'mem_buffers', 'VAL' : mem_buffers,
                            'TYPE':'uint32', 'UNITS':'KB', 'TMAX':180,
                            'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

        if mem_shared != -1:
            self.addMetric({'NAME':'mem_shared', 'VAL' : mem_shared,
                            'TYPE':'uint32', 'UNITS':'KB', 'TMAX':180,
                            'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

class metric_disk(metric):
    def interval(self):
        return 40

    def gather(self, tree):
        """
        Only reads FIRST disk right now...
        """

        p = Popen(['df', '-m', '/'], stdout=PIPE)
        lines = p.stdout.read().split('\n')

        fields = lines[1].split()
        disk_total = float(fields[1]) /  1024.0
        disk_free  = float(fields[3]) /  1024.0

        self.addMetric({'NAME':'disk_total', 'VAL' : disk_total,
                        'TYPE':'double', 'UNITS':'GB', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

        self.addMetric({'NAME':'disk_free', 'VAL' : disk_free,
                        'TYPE':'double', 'UNITS':'GB', 'TMAX':1200,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

class metric_iostat(metric):
    last_time = -1
    cpus = []

    def interval(self):
        return 20

    def gather(self, tree):
        f = open('/proc/stat', 'rb')
        line = f.readline()
        f.close()

        fields = line.split()
        cpus = [int(fields[1]), int(fields[2]), int(fields[3]),int(fields[4])]

        if self.last_time == -1:
            self.last_time = time()
            self.cpus = cpus
            return

        # convert to zip
        cpu_diff = [float(cpus[i] - self.cpus[i]) for i in range(4)]
        cpu_sum = float(sum(cpu_diff))
        cpu_percent = [ 100.0* cpu_diff[i]/ cpu_sum for i in range(4) ]
        self.addMetric({'NAME':'cpu_user', 'VAL': cpu_percent[0],
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        self.addMetric({'NAME':'cpu_nice', 'VAL': cpu_percent[1],
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        self.addMetric({'NAME':'cpu_system', 'VAL':cpu_percent[2],
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        self.addMetric({'NAME':'cpu_idle', 'VAL':cpu_percent[3],
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})

        f = open('/proc/loadavg', 'rb')
        line = f.read().split(' ')
        f.close()

        load_one = float(line[0])
        load_five = float(line[1])
        load_fifteen = float(line[2])

        self.addMetric({'NAME':'load_one', 'VAL':load_one,
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        self.addMetric({'NAME':'load_five', 'VAL':load_five,
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})
        self.addMetric({'NAME':'load_fifteen', 'VAL':load_fifteen,
                        'TYPE':'float', 'UNITS':'%', 'TMAX':90,
                        'DMAX':0, 'SLOPE':'both', 'SOURCE':'gmond'})



########NEW FILE########
__FILENAME__ = pmond
#!/usr/bin/env python

# This is the MIT License
# http://www.opensource.org/licenses/mit-license.php
#
# Copyright (c) 2007,2008 Nick Galbreath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
from gmetric import Gmetric
import metric
import logging
from os import uname
ostype = uname()[0]
if ostype == 'Linux':
    from metrics_linux import *
elif ostype == 'Darwin':
    from metrics_darwin import *
else:
    print "whoops"
    sys.exit(1)

keep_processing = True

class consumer(object):
    """
    collection of "metric collectors"
    """
    def __init__(self):
        self.ary = []
    def addMetric(self, values, host=None):
        for a in self.ary:
            a.addMetric(values, host)
    def addConsumer(self, o):
        self.ary.append(o)

class emitter(object):
    """
    A consumer of metrics that sends via gmetric
    """
    def __init__(self, host, port, protocol):
        self.g = Gmetric(host, port, protocol)

    def addMetric(self, values, host=None):
        logging.debug("sending %s = %s", values['NAME'], values['VAL'])
        logging.debug("DICT = %s", str(values))
        self.g.send(values['NAME'], values['VAL'],  values['TYPE'],
                    values['UNITS'], values['SLOPE'], values['TMAX'],
                    values['DMAX'])

from subprocess import Popen, PIPE
import sched
from time import time, sleep
import sys
import socket

from collections import defaultdict
from gmetric import gmetric_read
from socket import gethostname


class monitortree(object):
    """
    A consumer of metrics that stores things in a xml tree
    """
    def __init__(self):
        self.hosts = defaultdict(dict)
        self.hostname = gethostname()

    def addMetric(self, values, host=None):
        # HOST -> METRICS -> VALUES

        # add timestamp to figureout node expiration
        values['_now'] = time()

        # TBD: replace with defaultdict
        if host is None:
            host = self.hostname

        metrics = self.hosts[host]
        name = values['NAME']
        metrics[name] = values

    def xml(self):
        parts = []

        # TBD: look at Ganglia 3
        parts.append('<GANGLIA_XML VERSION="2.5.7" SOURCE="gmond">\n')
        for host,metrics in self.hosts.iteritems():
            parts.append('<HOST name="%s">\n' % host)
            zap = []
            for name, values in metrics.iteritems():

                # figure out if this node "expired"
                expires = 0
                if '_now' in values and 'TMAX' in values:
                    now = time()
                    tmax = float(values['TMAX'])
                    if tmax > 0:
                        expires = float(values['_now']) + float(values['TMAX'])
                if expires and expires < now:
                    zap.append(values['NAME'])
                    continue
                
                # print the node
                parts.append('<METRIC NAME="' + values['NAME'] + '"')
                for k,v in values.iteritems():
                    if k != '_now' and k != 'NAME':
                        parts.append(' ' + k + '="' + str(v) + '"')
                parts.append('/>\n')

            # delete the expired nodes
            for name in zap:
                del metrics[name]

            parts.append('\n</HOST>\n')
        parts.append('</GANGLIA_XML>\n')
        return ''.join(parts)


# THREE THREADS
#  * writers
#  * receiver
#  * monitor
#
#
import threading
class Monitor(threading.Thread):
    def __init__(self, tree):
        threading.Thread.__init__(self)
        self.tree = tree

    def run(self):
        # MACHINE 
        s = sched.scheduler(time, sleep)

        for m in [metric_cpu(),
                  metric_iostat(),
                  metric_mem(),
                  metric_disk(),
                  metric_proc(),
                  metric_sys_clock(),
                  metric_net() ]:
            m.register(s, self.tree)

        s.run()

class Reader(threading.Thread):
    """
    Accepts UDP XDR gmetric packets
    """
    def __init__(self, tree):
        threading.Thread.__init__(self)
        self.tree = tree

    def run(self):
        tree = self.tree

        serversocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        serversocket.bind(('', 4001))
        #serversocket.listen(5)
        serversocket.setblocking(1)
        serversocket.settimeout(None)
        while keep_processing:
            try:
                print "loop"
                data, address = serversocket.recvfrom(512)
                tree.addMetric(gmetric_read(data))
            except KeyboardInterrupt:
                print "got intertupe"
            except socket.timeout:
                print "udp timeout"
                
class Writer(threading.Thread):
    """
    Writes out metrics tree as XML
    """
    def __init__(self, tree):
        threading.Thread.__init__(self)
        self.tree = tree

    def run(self):
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.settimeout(None)
        serversocket.bind(('', 4000))
        serversocket.listen(5)
        while keep_processing:
            try:
                clientsocket, address = serversocket.accept()
                clientsocket.send(self.tree.xml())
                clientsocket.close()
            except KeyboardInterrupt:
                print "got intertupe"

            except socket.timeout:
                print "got timeout"

def main():

    tree =  monitortree()

    r = Reader(tree)
    w = Writer(tree)

    c = consumer()
    e = emitter('172.16.70.128', 8649, 'udp')
    c.addConsumer(e)
    c.addConsumer(tree)

    m = Monitor(c)
    r.start()
    w.start()
    m.start()


    m.join()

    while m.isAlive():
        try:
            m.join(1000)
        except KeyboardInterrupt:
            print "Exit on main"
            sys.exit(1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    #from daemon import *
    #drop_privileges()
    #daemonize()
    main()

########NEW FILE########
__FILENAME__ = pref_test
#!/usr/bin/env python

import psyco
psyco.full()

from gmetric import Gmetric

if __name__ == '__main__':
    g = Gmetric('localhost', 4001, 'udp')
    for i in xrange(100000):
        g.send('foo', 'bar')

########NEW FILE########
