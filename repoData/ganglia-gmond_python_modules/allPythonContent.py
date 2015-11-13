__FILENAME__ = apache_status
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading
import time
import urllib2
import traceback
import re
import copy

# global to store state for "total accesses"
METRICS = {
    'time' : 0,
    'data' : {}
}

LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

#Metric prefix
NAME_PREFIX = "ap_"
SSL_NAME_PREFIX = "apssl_"

SERVER_STATUS_URL = ""

descriptors = list()
Desc_Skel   = {}
Scoreboard  = {
    NAME_PREFIX + 'waiting'         : { 'key': '_', 'desc': 'Waiting for Connection' },
    NAME_PREFIX + 'starting'        : { 'key': 'S', 'desc': 'Starting up' },
    NAME_PREFIX + 'reading_request' : { 'key': 'R', 'desc': 'Reading Request' },
    NAME_PREFIX + 'sending_reply'   : { 'key': 'W', 'desc': 'Sending Reply' },
    NAME_PREFIX + 'keepalive'       : { 'key': 'K', 'desc': 'Keepalive (read)' },
    NAME_PREFIX + 'dns_lookup'      : { 'key': 'D', 'desc': 'DNS Lookup' },
    NAME_PREFIX + 'closing'         : { 'key': 'C', 'desc': 'Closing connection' },
    NAME_PREFIX + 'logging'         : { 'key': 'L', 'desc': 'Logging' },
    NAME_PREFIX + 'gracefully_fin'  : { 'key': 'G', 'desc': 'Gracefully finishing' },
    NAME_PREFIX + 'idle'            : { 'key': 'I', 'desc': 'Idle cleanup of worker' },
    NAME_PREFIX + 'open_slot'       : { 'key': '.', 'desc': 'Open slot with no current process' },
    }
Scoreboard_bykey = dict([(v["key"],k) for (k,v) in Scoreboard.iteritems()])

SSL_REGEX = re.compile('^(cache type:) (.*)(<b>)(?P<shared_mem>[0-9]+)(</b> bytes, current sessions: <b>)(?P<current_sessions>[0-9]+)(</b><br>subcaches: <b>)(?P<num_subcaches>[0-9]+)(</b>, indexes per subcache: <b>)(?P<indexes_per_subcache>[0-9]+)(</b><br>)(.*)(<br>index usage: <b>)(?P<index_usage>[0-9]+)(%</b>, cache usage: <b>)(?P<cache_usage>[0-9]+)(%</b><br>total sessions stored since starting: <b>)(?P<sessions_stored>[0-9]+)(</b><br>total sessions expired since starting: <b>)(?P<sessions_expired>[0-9]+)(</b><br>total \(pre-expiry\) sessions scrolled out of the cache: <b>)(?P<sessions_scrolled_outof_cache>[0-9]+)(</b><br>total retrieves since starting: <b>)(?P<retrieves_hit>[0-9]+)(</b> hit, <b>)(?P<retrieves_miss>[0-9]+)(</b> miss<br>total removes since starting: <b>)(?P<removes_hit>[0-9]+)(</b> hit, <b>)(?P<removes_miss>[0-9]+)')
# Good for Apache 2.2
#SSL_REGEX = re.compile('^(cache type:) (.*)(<b>)(?P<shared_mem>[0-9]+)(</b> bytes, current sessions: <b>)(?P<current_sessions>[0-9]+)(</b><br>subcaches: <b>)(?P<num_subcaches>[0-9]+)(</b>, indexes per subcache: <b>)(?P<indexes_per_subcache>[0-9]+)(</b><br>index usage: <b>)(?P<index_usage>[0-9]+)(%</b>, cache usage: <b>)(?P<cache_usage>[0-9]+)(%</b><br>total sessions stored since starting: <b>)(?P<sessions_stored>[0-9]+)(</b><br>total sessions expired since starting: <b>)(?P<sessions_expired>[0-9]+)(</b><br>total \(pre-expiry\) sessions scrolled out of the cache: <b>)(?P<sessions_scrolled_outof_cache>[0-9]+)(</b><br>total retrieves since starting: <b>)(?P<retrieves_hit>[0-9]+)(</b> hit, <b>)(?P<retrieves_miss>[0-9]+)(</b> miss<br>total removes since starting: <b>)(?P<removes_hit>[0-9]+)(</b> hit, <b>)(?P<removes_miss>[0-9]+)')


Metric_Map = {
    'Uptime' : NAME_PREFIX + "uptime",
    'IdleWorkers' : NAME_PREFIX + "idle_workers",
    'BusyWorkers' : NAME_PREFIX + "busy_workers",
    'Total kBytes' : NAME_PREFIX + "bytes",
    'CPULoad' : NAME_PREFIX + "cpuload",
    "Total Accesses" : NAME_PREFIX + "rps"
}

def get_metrics():

    global METRICS, LAST_METRICS, SERVER_STATUS_URL, COLLECT_SSL

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

        metrics = dict( [(k, 0) for k in Scoreboard.keys()] )

        # This is the short server-status. Lacks SSL metrics
        try:
            req = urllib2.Request(SERVER_STATUS_URL + "?auto")
            
            # Download the status file
            res = urllib2.urlopen(req, None, 2)

            for line in res:
               split_line = line.rstrip().split(": ")
               long_metric_name = split_line[0]
               if long_metric_name == "Scoreboard":
                   for sck in split_line[1]:
                      metrics[ Scoreboard_bykey[sck] ] += 1
               else:
                    if long_metric_name in Metric_Map:
                       metric_name = Metric_Map[long_metric_name]
                    else:
                       metric_name = long_metric_name
                    metrics[metric_name] = split_line[1]

        except urllib2.URLError:
             traceback.print_exc()

        # If we are collecting SSL metrics we'll do
        if COLLECT_SSL:    
    
            try:
                req2 = urllib2.Request(SERVER_STATUS_URL)
                
                # Download the status file
                res = urllib2.urlopen(req2, None, 2)
                
                for line in res:
                    regMatch = SSL_REGEX.match(line)
                    if regMatch:
                        linebits = regMatch.groupdict()
                        for key in linebits:
                            #print SSL_NAME_PREFIX + key + "=" + linebits[key]
                            metrics[SSL_NAME_PREFIX + key] = linebits[key]
    
            except urllib2.URLError:
                 traceback.print_exc()


        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result

def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    # If it's ap_bytes metric multiply result by 1024
    if name == NAME_PREFIX + "bytes":
        multiplier = 1024
    else:
        multiplier = 1

    try:
      delta = multiplier * (float(curr_metrics['data'][name]) - float(last_metrics['data'][name])) /(curr_metrics['time'] - last_metrics['time'])
      if delta < 0:
	print name + " is less 0"
	delta = 0
    except KeyError:
      delta = 0.0      

    return delta


def create_desc(prop):
    d = Desc_Skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, Desc_Skel, SERVER_STATUS_URL, COLLECT_SSL

    print '[apache_status] Received the following parameters'
    print params

    if "metric_group" not in params:
        params["metric_group"] = "apache"

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_value,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'units'       : 'proc',
        'slope'       : 'both',
        'format'      : '%d',
        'description' : 'XXX',
        'groups'      : params["metric_group"],
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 15

    if "url" not in params:
        params["url"] = "http://localhost:7070/server-status"
        
    if "collect_ssl" not in params:
        params["collect_ssl"] = False

    SERVER_STATUS_URL = params["url"]
    COLLECT_SSL = params["collect_ssl"]

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    descriptors.append(create_desc({
                "name"       : NAME_PREFIX + "rps",
                "value_type" : "float",
                "units"      : "req/sec",
                "call_back"   : get_delta,                
                "format"     : "%.3f",
                "description": "request per second",
                }))

    descriptors.append(create_desc({
                "name"       : NAME_PREFIX + "bytes",
                "value_type" : "float",
                "units"      : "bytes/sec",
                "call_back"   : get_delta,                
                "format"     : "%.3f",
                "description": "bytes transferred per second",
                }))

    descriptors.append(create_desc({
                "name"       : NAME_PREFIX + "cpuload",
                "value_type" : "float",
                "units"      : "pct",
                "format"     : "%.6f",
                "call_back"   : get_value,
                "description": "Pct of time CPU utilized",
                }))

    descriptors.append(create_desc({
                "name"       : NAME_PREFIX + "busy_workers",
                "value_type" : "uint",
                "units"      : "threads",
                "format"     : "%u",
                "call_back"   : get_value,
                "description": "Busy threads",
                }))

    descriptors.append(create_desc({
                "name"       : NAME_PREFIX + "idle_workers",
                "value_type" : "uint",
                "units"      : "threads",
                "format"     : "%u",
                "call_back"   : get_value,
                "description": "Idle threads",
                }))

    descriptors.append(create_desc({
                "name"       : NAME_PREFIX + "uptime",
                "value_type" : "uint",
                "units"      : "seconds",
                "format"     : "%u",
                "call_back"   : get_value,
                "description": "Uptime",
                }))

    for k,v in Scoreboard.iteritems():
        descriptors.append(create_desc({
                    "name"        : k,
                    "call_back"   : get_value,
                    "description" : v["desc"],
                    }))
        
    ##########################################################################
    # SSL metrics
    ##########################################################################
    if params['collect_ssl']:
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "shared_mem",
                    "value_type" : "float",
                    "units"      : "bytes",
                    "format"     : "%.3f",
                    "call_back"   : get_value,
                    "description": "Shared memory",
                    }))
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "current_sessions",
                    "value_type" : "uint",
                    "units"      : "sessions",
                    "format"     : "%u",
                    "call_back"   : get_value,
                    "description": "Current sessions",
                    }))
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "num_subcaches",
                    "value_type" : "uint",
                    "units"      : "subcaches",
                    "format"     : "%u",
                    "call_back"   : get_value,
                    "description": "Number of subcaches",
                    }))
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "indexes_per_subcache",
                    "value_type" : "float",
                    "units"      : "indexes",
                    "format"     : "%.3f",
                    "call_back"   : get_value,
                    "description": "Subcaches",
                    }))
    
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "index_usage",
                    "value_type" : "float",
                    "units"      : "pct",
                    "format"     : "%.3f",
                    "call_back"   : get_value,
                    "description": "Index usage",
                    }))
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "cache_usage",
                    "value_type" : "float",
                    "units"      : "pct",
                    "format"     : "%.3f",
                    "call_back"   : get_value,
                    "description": "Cache usage",
                    }))
    
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "sessions_stored",
                    "value_type" : "float",
                    "units"      : "sessions/sec",
                    "format"     : "%.3f",
                    "call_back"   : get_delta,
                    "description": "Sessions stored",
                    }))
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "sessions_expired",
                    "value_type" : "float",
                    "units"      : "sessions/sec",
                    "format"     : "%.3f",
                    "call_back"   : get_delta,
                    "description": "Sessions expired",
                    }))
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "retrieves_hit",
                    "value_type" : "float",
                    "units"      : "retrieves/sec",
                    "format"     : "%.3f",
                    "call_back"   : get_delta,
                    "description": "Retrieves Hit",
                    }))
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "retrieves_miss",
                    "value_type" : "float",
                    "units"      : "retrieves/sec",
                    "format"     : "%.3f",
                    "call_back"   : get_delta,
                    "description": "Retrieves Miss",
                    }))
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "removes_hit",
                    "value_type" : "float",
                    "units"      : "removes/sec",
                    "format"     : "%.3f",
                    "call_back"   : get_delta,
                    "description": "Removes Hit",
                    }))
    
        descriptors.append(create_desc({
                    "name"       : SSL_NAME_PREFIX + "removes_miss",
                    "value_type" : "float",
                    "units"      : "removes/sec",
                    "format"     : "%.3f",
                    "call_back"   : get_delta,
                    "description": "Removes Miss",
                    }))

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    try:
        params = {
            'url'         : 'http://localhost:7070/server-status',
            'collect_ssl' : False
            }
        metric_init(params)
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                if d['name'] == NAME_PREFIX + "rps":
                    print 'value for %s is %.4f' % (d['name'], v)
                else:
                    print 'value for %s is %s'   % (d['name'], v)
            time.sleep(15)
    except KeyboardInterrupt:
        os._exit(1)

########NEW FILE########
__FILENAME__ = apc_status
#
#
# Module: apc_status
# Graphs the status of APC: Another PHP Cache
#
# Useage: To use this, you need to copy the apc-json.php file to your document root of the local webserver.
#         The path to the apc-json.php should be set in conf.d/apc_status.pyconf
#
# Author: Jacob V. Rasmussen (jacobvrasmussen@gmail.com)
# Site: http://blackthorne.dk
#

import urllib2
import json
import traceback

NAME_PREFIX = "apc_"

APC_STATUS_URL = ""

descriptors = list()
Desc_Skel   = {}
metric_list = {
	NAME_PREFIX + 'num_slots'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Slots', 		'desc': 'Number of slots' },
	NAME_PREFIX + 'num_hits'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Hits', 		'desc': 'Number of cache hits' },
	NAME_PREFIX + 'num_misses'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Misses', 	'desc': 'Number of cache misses' },
	NAME_PREFIX + 'num_inserts'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Inserts', 	'desc': 'Number of cache inserts' },
	NAME_PREFIX + 'expunges'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Deletes', 	'desc': 'Number of cache deletes' },
	NAME_PREFIX + 'mem_size'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Bytes', 		'desc': 'Memory size' },
	NAME_PREFIX + 'num_entries'	: { 'type': 'uint',  'format' : '%d', 'unit': 'Entries', 	'desc': 'Cached Files' },
	NAME_PREFIX + 'uptime'		: { 'type': 'uint',  'format' : '%d', 'unit': 'seconds',	'desc': 'Uptime' },
	NAME_PREFIX + 'request_rate'	: { 'type': 'float', 'format' : '%f', 'unit': 'requests/sec', 	'desc': 'Request Rate (hits, misses)' },
	NAME_PREFIX + 'hit_rate'	: { 'type': 'float', 'format' : '%f', 'unit': 'requests/sec', 	'desc': 'Hit Rate' },
	NAME_PREFIX + 'miss_rate'	: { 'type': 'float', 'format' : '%f', 'unit': 'requests/sec', 	'desc': 'Miss Rate' },
	NAME_PREFIX + 'insert_rate'	: { 'type': 'float', 'format' : '%f', 'unit': 'requests/sec', 	'desc': 'Insert Rate' },
	NAME_PREFIX + 'num_seg'		: { 'type': 'uint',  'format' : '%d', 'unit': 'fragments', 	'desc': 'Segments' },
	NAME_PREFIX + 'mem_avail'	: { 'type': 'uint',  'format' : '%d', 'unit': 'bytes', 		'desc': 'Free Memory' },
	NAME_PREFIX + 'mem_used'	: { 'type': 'uint',  'format' : '%d', 'unit': 'bytes', 		'desc': 'Used Memory' },
	}

def get_value(name):
	try:
		req = urllib2.Request(APC_STATUS_URL, None, {'user-agent':'ganglia-apc-python'})
		opener = urllib2.build_opener()
		f = opener.open(req)
		apc_stats = json.load(f)

	except urllib2.URLError:
		traceback.print_exc()

	return apc_stats[name[len(NAME_PREFIX):]]

def create_desc(prop):
	d = Desc_Skel.copy()
	for k,v in prop.iteritems():
		d[k] = v
	return d

def metric_init(params):
	global descriptors, Desc_Skel, APC_STATUS_URL

	if "metric_group" not in params:
		params["metric_group"] = "apc_cache"

	Desc_Skel = {
		'name'		: 'XXX',
		'call_back'	: get_value,
		'time_max'	: 60,
		'value_type'	: 'uint',
		'units'		: 'proc',
		'slope'		: 'both',
		'format'	: '%d',
		'description'	: 'XXX',
		'groups'	: params["metric_group"],
		}

	if "refresh_rate" not in params:
		params["refresh_rate"] = 15

	if "url" not in params:
		params["url"] = "http://localhost/apc-json.php"
	
	
	APC_STATUS_URL = params["url"]

	if "spoof_host" in params:
		Desc_Skel["spoof_host"] = params["spoof_host"]

	for k,v in metric_list.iteritems():
		descriptors.append(create_desc({
			"name"		: k,
			"call_back"	: get_value,
			"value_type"	: v["type"],
			"units"		: v["unit"],
			"format"	: v["format"],
			"description"	: v["desc"],
			}))

	return descriptors

def metric_cleanup():
	pass

if __name__ == '__main__':
	metric_init({})
	for d in descriptors:
		v = d['call_back'](d['name'])
		print 'value for %s is %s' % (d['name'], v)



########NEW FILE########
__FILENAME__ = beanstalk
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import beanstalkc

HOST='localhost'
PORT=14711
def stat_handler(name):
    bean=beanstalkc.Connection(host=HOST,port=PORT)
    return bean.stats()[name]
    
def tube_stat_handler(name):
    bean=beanstalkc.Connection(host=HOST,port=PORT)
    return bean.stats_tube(name.split('_')[0])[name.split('_')[1]]
    
def metric_init(params):
    global descriptors

    descriptors = [{'name': 'current-connections',
        'call_back': stat_handler,
        'time_max': 90,
        'value_type': 'uint',
        'units': 'connections',
        'slope': 'both',
        'format': '%u',
        'description': 'Number of Current Connections to Beanstalkd',
        'groups': 'beanstalkd'},
        {'name': 'total-jobs',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'total jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs',
            'groups': 'beanstalkd'},
        {'name': 'current-jobs-ready',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs \'ready\'',
            'groups': 'beanstalkd'},
        {'name': 'current-jobs-buried',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs \'buried\'',
            'groups': 'beanstalkd'},
        {'name': 'current-jobs-delayed',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs \'delayed\'',
            'groups': 'beanstalkd'},
        {'name': 'current-waiting',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs \'waiting\'',
            'groups': 'beanstalkd'},
        {'name': 'job-timeouts',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs Timeouts',
            'groups': 'beanstalkd'},
        {'name': 'cmd-bury',
            'call_back': stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Burries',
            'groups': 'beanstalkd'}
        ]
        
    #now get all the tubes
    bean=beanstalkc.Connection(host=HOST,port=PORT)
    tubes=bean.tubes()
    for tube in tubes:
        descriptors.append(
        {'name': tube+'_total-jobs',
            'call_back': tube_stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'total jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Number of Beanstalkd Jobs ('+tube+')',
            'groups': 'beanstalkd'})
        descriptors.append(
        {'name': tube+'_current-watching',
            'call_back': tube_stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'clients',
            'slope': 'both',
            'format': '%u',
            'description': 'Number Watchers ('+tube+')',
            'groups': 'beanstalkd'})
        descriptors.append(
        {'name': tube+'_current-jobs-buried',
            'call_back': tube_stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Current Number of Jobs Burried ('+tube+')',
            'groups': 'beanstalkd'})
        descriptors.append(
        {'name': tube+'_current-jobs-ready',
            'call_back': tube_stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'clients',
            'slope': 'both',
            'format': '%u',
            'description': 'Current Jobs Ready ('+tube+')',
            'groups': 'beanstalkd'})
        descriptors.append(
        {'name': tube+'_current-waiting',
            'call_back': tube_stat_handler,
            'time_max': 90,
            'value_type': 'uint',
            'units': 'jobs',
            'slope': 'both',
            'format': '%u',
            'description': 'Current Number of Jobs Waiting ('+tube+')',
            'groups': 'beanstalkd'})
    
    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init(None)
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s is %u' % (d['name'],  v)

########NEW FILE########
__FILENAME__ = bind_xml
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import abc
import copy
import logging
import logging.handlers
import optparse
import time
import sys

import pybindxml.reader

log = None

QUERY_TYPES = ['A', 'SOA', 'DS' 'UPDATE', 'MX', 'AAAA', 'DNSKEY', 'QUERY', 'TXT', 'PTR']

METRIC_PREFIX = 'bind_'

DESCRIPTION_SKELETON = {
    'name'        : 'XXX',
    'time_max'    : 60,
    'value_type'  : 'uint', # (string, uint, float, double)
    'format'      : '%d', #String formatting ('%s', '%d','%f')
    'units'       : 'XXX',
    'slope'       : 'both',
    'description' : 'XXX',
    'groups'      : 'bind_xml',
    'calc'        : 'scalar' # scalar
    }


METRICS = [
    {'name': 'mem_BlockSize',
     'description': '',
     'value_type': 'double',
     'format': '%f',
     'units': 'bytes'},
    {'name': 'mem_ContextSize',
     'description': '',
     'value_type': 'double',
     'format': '%f',
     'units': 'bytes'},
    {'name': 'mem_InUse',
     'description': '',
     'value_type': 'double',
     'format': '%f',
     'units': 'bytes'},
    {'name': 'mem_TotalUse',
     'description': '',
     'units': 'bytes',
     'value_type': 'double',
     'format': '%f'},
    ]


#### Data Acces

class BindStats(object):

    bind_reader = None

    stats = None
    stats_last = None
    now_ts = -1
    last_ts = -1

    def __init__(self, host, port, min_poll_seconds):
        self.host = host
        self.port = int(port)
        self.min_poll_seconds = int(min_poll_seconds)

    def short_name(self, name):
        return name.split('bind_')[1]

    def get_bind_reader(self):
        if self.bind_reader is None:
            self.bind_reader = pybindxml.reader.BindXmlReader(host=self.host, port=self.port)
        return self.bind_reader

    def should_update(self):
        return (self.now_ts == -1 or time.time() - self.now_ts  > self.min_poll_seconds)
        
    def update_stats(self):
        self.stats_last = self.stats
        self.last_ts = self.now_ts
        self.stats = {}

        self.get_bind_reader().get_stats()
        for element, value in self.get_bind_reader().stats.memory_stats.items():
            self.stats['mem_' + element] = value
        
        # Report queries as a rate of zero if none are reported
        for qtype in QUERY_TYPES:
            self.stats['query_' + qtype] = 0
        for element, value in self.get_bind_reader().stats.query_stats.items():
            self.stats['query_' + element] = value

        self.now_ts = int(time.time())


    def get_metric_value(self, name):
        if self.should_update() is True:
            self.update_stats()
        if self.stats is None or self.stats_last is None:
            log.debug('Not enough stat data has been collected yet now_ts:%r last_ts:%r' % (self.now_ts, self.last_ts))
            return None
        descriptor = NAME_2_DESCRIPTOR[name]
        if descriptor['calc'] == 'scalar':
            val = self.stats[self.short_name(name)]
        elif descriptor['calc'] == 'rate':
            val = (self.stats[self.short_name(name)] - self.stats_last[self.short_name(name)]) / (self.now_ts - self.last_ts)
        else:
            log.warn('unknokwn memtric calc type %s' % descriptor['calc'])
            return None
        log.debug('on call_back got %s = %r' % (self.short_name(name), val))
        if descriptor['value_type'] == 'uint':
            return long(val)
        else:
            return float(val)


#### module functions


def metric_init(params):
    global BIND_STATS, NAME_2_DESCRIPTOR
    if log is None:
       setup_logging('syslog', params['syslog_facility'], params['log_level'])
    log.debug('metric_init: %r' % params)
    BIND_STATS = BindStats(params['host'], params['port'], params['min_poll_seconds'])
    descriptors = []
    for qtype in QUERY_TYPES:
        METRICS.append({'name': 'query_' + qtype,
                        'description': '%s queries per second',
                        'value_type': 'double', 'format': '%f',
                        'units': 'req/s', 'calc': 'rate'})
    for metric in METRICS:
        d = copy.copy(DESCRIPTION_SKELETON)
        d.update(metric)
        d['name'] = METRIC_PREFIX + d['name']
        d['call_back'] = BIND_STATS.get_metric_value
        descriptors.append(d)
    log.debug('descriptors: %r' % descriptors)
    for d in descriptors:
        for key in ['name', 'units', 'description']:
            if d[key] == 'XXX':
                log.warn('incomplete descriptor definition: %r' % d)
        if d['value_type'] == 'uint' and d['format'] != '%d':
            log.warn('value/type format mismatch: %r' % d)
    NAME_2_DESCRIPTOR = {}
    for d in descriptors:
        NAME_2_DESCRIPTOR[d['name']] = d
    return descriptors



def metric_cleanup():
    logging.shutdown()


#### Main and Friends

def setup_logging(handlers, facility, level):
    global log

    log = logging.getLogger('gmond_python_bind_xml')
    formatter = logging.Formatter(' | '.join(['%(asctime)s', '%(name)s',  '%(levelname)s', '%(message)s']))
    if handlers in ['syslog', 'both']:
        sh = logging.handlers.SysLogHandler(address='/dev/log', facility=facility)
        sh.setFormatter(formatter)
        log.addHandler(sh)
    if handlers in ['stdout', 'both']:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log.addHandler(ch)
    lmap = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET
        }
    log.setLevel(lmap[level])


def parse_args(argv):
    parser = optparse.OptionParser()
    parser.add_option('--log',
                      action='store', dest='log', default='stdout', choices=['stdout', 'syslog', 'both'],
                      help='log to stdout and/or syslog')
    parser.add_option('--log-level',
                      action='store', dest='log_level', default='WARNING',
                      choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'],
                      help='log to stdout and/or syslog')
    parser.add_option('--log-facility',
                      action='store', dest='log_facility', default='user',
                      help='facility to use when using syslog')

    return parser.parse_args(argv)


def main(argv):
    """ used for testing """
    (opts, args) = parse_args(argv)
    setup_logging(opts.log, opts.log_facility, opts.log_level)
    params = {'min_poll_seconds': 5, 'host': 'asu101', 'port': 8053}
    descriptors = metric_init(params)
    try:
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                if v is None:
                    print 'got None for %s' % d['name']
                else:
                    print 'value for %s is %r' % (d['name'], v)
            time.sleep(5)
            print '----------------------------'
    except KeyboardInterrupt:
        log.debug('KeyboardInterrupt, shutting down...')
        metric_cleanup()

if __name__ == '__main__':
    main(sys.argv[1:])


########NEW FILE########
__FILENAME__ = blueeyes_service
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# BlueEyes gmond module for Ganglia
#
# Copyright (C) 2011 by Michael T. Conigliaro <mike [at] conigliaro [dot] org>.
# All rights reserved.
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


import json
import os
import re
import time
import copy


PARAMS = {
    'service_name'    : 'stats',
    'service_version' : 'v1'
}
PARAMS['stats_command'] = 'curl --silent http://appserver11.example.com:30040/blueeyes/services/%s/%s/health' % \
                          (PARAMS['service_name'], PARAMS['service_version'])
NAME_PREFIX = 'blueeyes_service_%s_%s_' % (PARAMS['service_name'], PARAMS['service_version'])
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_TTL = 1


def flatten(obj, pre = '', sep = '_'):
    """Flatten a dict (i.e. dict['a']['b']['c'] => dict['a_b_c'])"""

    if type(obj) == dict:
        result = {}
        for k,v in obj.items():
            if type(v) == dict:
                result.update(flatten(obj[k], '%s%s%s' % (pre, k, sep)))
            else:
                result['%s%s' % (pre, k)] = v
    else:
        result = obj

    return result


def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_TTL:

        # get raw metric data
        io = os.popen(PARAMS['stats_command'])

        # clean up
        metrics_str = ''.join(io.readlines()).strip() # convert to string
        metrics_str = re.sub('\w+\((.*)\)', r"\1", metrics_str) # remove functions

        # convert to flattened dict
        try:
            metrics = flatten(json.loads(metrics_str))
        except ValueError:
            metrics = {}

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def get_rate(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    # get delta
    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        delta = (curr_metrics['data'][name] - last_metrics['data'][name])/(curr_metrics['time'] - last_metrics['time'])
        if delta < 0:
            delta = 0
    except StandardError:
        delta = 0

    return delta


def get_requests(name):
    """Return requests per second"""

    return reduce(lambda memo,obj: memo + get_rate('%srequests_%s_count' % (NAME_PREFIX, obj)),
                 ['DELETE', 'GET', 'POST', 'PUT'], 0)


def get_errors(name):
    """Return errors per second"""

    return reduce(lambda memo,obj: memo + get_rate('%srequests_%s_errors_errorCount' % (NAME_PREFIX, obj)),
                 ['DELETE', 'GET', 'POST', 'PUT'], 0)


def metric_init(lparams):
    """Initialize metric descriptors"""

    global NAME_PREFIX, PARAMS

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]
    NAME_PREFIX = 'blueeyes_service_%s_%s_' % (PARAMS['service_name'], PARAMS['service_version'])

    # define descriptors
    time_max = 60
    groups = 'blueeyes service %s %s' % (PARAMS['service_name'], PARAMS['service_version'])
    descriptors = [
        {
            'name': NAME_PREFIX + 'requests',
            'call_back': get_requests,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Requests/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Requests',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'errors',
            'call_back': get_errors,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Errors/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Errors',
            'groups': groups
        }
    ]

    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            print (('%s = %s') % (d['name'], d['format'])) % (d['call_back'](d['name']))
        print ''
        time.sleep(METRICS_CACHE_TTL)

########NEW FILE########
__FILENAME__ = ganglia_celery
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import socket
import traceback
import json
import copy
import urllib2

descriptors = list()
Desc_Skel   = {}
Debug = False

METRICS = {
    'time' : 0,
    'data' : {}
}

LAST_METRICS = copy.deepcopy(METRICS)

METRICS_CACHE_MAX = 5

SERVER_STATUS_URL = ""

def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS, SERVER_STATUS_URL

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	try:
	    # Initialize service dictionary
	    req = urllib2.Request(SERVER_STATUS_URL)
	    res = urllib2.urlopen(req, None, 1)
	    stats = res.read()
	    metrics2 = json.loads(stats)
            metrics = metrics2[0]
            metrics['status'] = "up"

        except StandardError, e:
            print e
            metrics = dict()
            metrics['status'] = "down"

	# update last metrics
        LAST_METRICS = copy.deepcopy(METRICS)

        # update cache
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]


def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    metric_name_list = name.split("_")[1:]
    metric_name = "_".join(metric_name_list)

    try:
      delta = (float(curr_metrics['data'][metric_name]) - float(last_metrics['data'][metric_name])) /(curr_metrics['time'] - last_metrics['time'])
      # If rate is 0 counter has started from beginning
      if delta < 0:
          if Debug:
              print name + " is less 0. Setting value to 0."
          delta = 0
    except KeyError:
          if Debug:
              print "Key " + name + " can't be found."
          delta = 0.0      

    return delta

def get_value(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    metric_name_list = name.split("_")[1:]
    metric_name = "_".join(metric_name_list)
    
    try:
      value = float(curr_metrics['data'][metric_name])
    except KeyError:
      if Debug:
         print "Key " + name + " can't be found."
      value = 0.0      

    return value

def get_string(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    metric_name_list = name.split("_")[1:]
    metric_name = "_".join(metric_name_list)
    
    try:
      value = curr_metrics['data'][metric_name]
    except KeyError:
      if Debug:
         print "Key " + name + " can't be found."
      value = "down"      

    return value



def metric_init(params):
    global descriptors, Desc_Skel, URL, Debug, SERVER_STATUS_URL

    if "metrics_prefix" not in params:
      params["metrics_prefix"] = "celery"

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%f',
        'units'       : 'XXX',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'No descr',
        'groups'      : 'celery',
        }

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]
        
    if "url" not in params:
        params["url"] = "http://localhost:8989/api/worker/"

    SERVER_STATUS_URL = params["url"]
       
    descriptors.append(create_desc(Desc_Skel, {
	"name"       : params["metrics_prefix"] + "_active",
	"units"      : "jobs",
	"description": "Number of active jobs",
	"call_back"  : get_value
    }))
    
    descriptors.append(create_desc(Desc_Skel, {
	"name"       : params["metrics_prefix"] + "_processed",
	"units"      : "jobs/s",
	"description": "Number of processed jobs",
	"call_back"  : get_delta
    }))

    descriptors.append(create_desc(Desc_Skel, {
	"name"       : params["metrics_prefix"] + "_status",
	"units"      : "",
	'value_type' : 'string',
	'format'     : '%s',
	'slope'      : 'zero',
	"description": "Celery Service up/down",
	"call_back"  : get_string
    }))

	
    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

if __name__ == '__main__':
    try:
        params = {
            "url" : "http://localhost:8989/api/worker/",
            }
        metric_init(params)

        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)

########NEW FILE########
__FILENAME__ = couchdb
###  This script reports couchdb metrics to ganglia.

###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib2
import json

logging.basicConfig(level=logging.ERROR)

_Worker_Thread = None

class UpdateCouchdbThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running = False
        self.shuttingdown = False
        self.refresh_rate = int(params['refresh_rate'])
        self.metrics = {}
        self.settings = {}
        self.stats_url = params['stats_url']
        self._metrics_lock = threading.Lock()
        self._settings_lock = threading.Lock()

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        global _Lock

        self.running = True

        while not self.shuttingdown:
            time.sleep(self.refresh_rate)
            self.refresh_metrics()

        self.running = False

    @staticmethod
    def _get_couchdb_stats(url, refresh_rate):
        if refresh_rate == 60 or refresh_rate == 300 or refresh_rate == 900:
            url += '?range=' + str(refresh_rate)
        else:
            logging.warning('The specified refresh_rate of %d is invalid and has been substituted with 60!' % refresh_rate)
            url += '?range=60'

        # Set time out for urlopen to 2 seconds otherwise we run into the possibility of hosing gmond
        c = urllib2.urlopen(url, None, 2)
        json_data = c.read()
        c.close()

        data = json.loads(json_data)
        couchdb = data['couchdb']
        httpd = data['httpd']
        request_methods = data['httpd_request_methods']
        status_codes = data['httpd_status_codes']

        result = {}
        for first_level_key in data:
            for second_level_key in data[first_level_key]:
                value = data[first_level_key][second_level_key]['current']
                if value is None:
                    value = 0
                else:
                    if second_level_key in ['open_databases', 'open_os_files', 'clients_requesting_changes']:
                        print second_level_key + ': ' + str(value)
                        value = int(value)
                    else:
                        # We need to devide by the range as couchdb provides no per second values
                        value = float(value) / refresh_rate
                result['couchdb_' + first_level_key + '_' + second_level_key ] = value

        return result

    def refresh_metrics(self):
        logging.debug('refresh metrics')

        try:
            logging.debug(' opening URL: ' + str(self.stats_url))
            data = UpdateCouchdbThread._get_couchdb_stats(self.stats_url, self.refresh_rate)
        except:
            logging.warning('error refreshing metrics')
            logging.warning(traceback.print_exc(file=sys.stdout))

        try:
            self._metrics_lock.acquire()
            self.metrics = {}
            for k, v in data.items():
                self.metrics[k] = v
        except:
            logging.warning('error refreshing metrics')
            logging.warning(traceback.print_exc(file=sys.stdout))
            return False

        finally:
            self._metrics_lock.release()

        if not self.metrics:
            logging.warning('error refreshing metrics')
            return False

        logging.debug('success refreshing metrics')
        logging.debug('metrics: ' + str(self.metrics))

        return True

    def metric_of(self, name):
        logging.debug('getting metric: ' + name)

        try:
            if name in self.metrics:
                try:
                    self._metrics_lock.acquire()
                    logging.debug('metric: %s = %s' % (name, self.metrics[name]))
                    return self.metrics[name]
                finally:
                    self._metrics_lock.release()
        except:
            logging.warning('failed to fetch ' + name)
            return 0

    def setting_of(self, name):
        logging.debug('getting setting: ' + name)

        try:
            if name in self.settings:
                try:
                    self._settings_lock.acquire()
                    logging.debug('setting: %s = %s' % (name, self.settings[name]))
                    return self.settings[name]
                finally:
                    self._settings_lock.release()
        except:
            logging.warning('failed to fetch ' + name)
            return 0

def metric_init(params):
    logging.debug('init: ' + str(params))
    global _Worker_Thread

    METRIC_DEFAULTS = {
        'units': 'requests/s',
        'groups': 'couchdb',
        'slope': 'both',
        'value_type': 'float',
        'format': '%.3f',
        'description': '',
        'call_back': metric_of
    }

    descriptions = dict(
        couchdb_couchdb_auth_cache_hits={
            'units': 'hits/s',
            'description': 'Number of authentication cache hits'},
        couchdb_couchdb_auth_cache_misses={
            'units': 'misses/s',
            'description': 'Number of authentication cache misses'},
        couchdb_couchdb_database_reads={
            'units': 'reads/s',
            'description': 'Number of times a document was read from a database'},
        couchdb_couchdb_database_writes={
            'units': 'writes/s',
            'description': 'Number of times a document was changed'},
        couchdb_couchdb_open_databases={
            'value_type': 'uint',
            'format': '%d',
            'units': 'databases',
            'description': 'Number of open databases'},
        couchdb_couchdb_open_os_files={
            'value_type': 'uint',
            'format': '%d',
            'units': 'files',
            'description': 'Number of file descriptors CouchDB has open'},
        couchdb_couchdb_request_time={
            'units': 'ms',
            'description': 'Request time'},
        couchdb_httpd_bulk_requests={
            'description': 'Number of bulk requests'},
        couchdb_httpd_clients_requesting_changes={
            'value_type': 'uint',
            'format': '%d',
            'units': 'clients',
            'description': 'Number of clients for continuous _changes'},
        couchdb_httpd_requests={
            'description': 'Number of HTTP requests'},
        couchdb_httpd_temporary_view_reads={
            'units': 'reads',
            'description': 'Number of temporary view reads'},
        couchdb_httpd_view_reads={
            'description': 'Number of view reads'},
        couchdb_httpd_request_methods_COPY={
            'description': 'Number of HTTP COPY requests'},
        couchdb_httpd_request_methods_DELETE={
            'description': 'Number of HTTP DELETE requests'},
        couchdb_httpd_request_methods_GET={
            'description': 'Number of HTTP GET requests'},
        couchdb_httpd_request_methods_HEAD={
            'description': 'Number of HTTP HEAD requests'},
        couchdb_httpd_request_methods_POST={
            'description': 'Number of HTTP POST requests'},
        couchdb_httpd_request_methods_PUT={
            'description': 'Number of HTTP PUT requests'},
        couchdb_httpd_status_codes_200={
            'units': 'responses/s',
            'description': 'Number of HTTP 200 OK responses'},
        couchdb_httpd_status_codes_201={
            'units': 'responses/s',
            'description': 'Number of HTTP 201 Created responses'},
        couchdb_httpd_status_codes_202={
            'units': 'responses/s',
            'description': 'Number of HTTP 202 Accepted responses'},
        couchdb_httpd_status_codes_301={
            'units': 'responses/s',
            'description': 'Number of HTTP 301 Moved Permanently responses'},
        couchdb_httpd_status_codes_304={
            'units': 'responses/s',
            'description': 'Number of HTTP 304 Not Modified responses'},
        couchdb_httpd_status_codes_400={
            'units': 'responses/s',
            'description': 'Number of HTTP 400 Bad Request responses'},
        couchdb_httpd_status_codes_401={
            'units': 'responses/s',
            'description': 'Number of HTTP 401 Unauthorized responses'},
        couchdb_httpd_status_codes_403={
            'units': 'responses/s',
            'description': 'Number of HTTP 403 Forbidden responses'},
        couchdb_httpd_status_codes_404={
            'units': 'responses/s',
            'description': 'Number of HTTP 404 Not Found responses'},
        couchdb_httpd_status_codes_405={
            'units': 'responses/s',
            'description': 'Number of HTTP 405 Method Not Allowed responses'},
        couchdb_httpd_status_codes_409={
            'units': 'responses/s',
            'description': 'Number of HTTP 409 Conflict responses'},
        couchdb_httpd_status_codes_412={
            'units': 'responses/s',
            'description': 'Number of HTTP 412 Precondition Failed responses'},
        couchdb_httpd_status_codes_500={
            'units': 'responses/s',
            'description': 'Number of HTTP 500 Internal Server Error responses'})

    if _Worker_Thread is not None:
        raise Exception('Worker thread already exists')

    _Worker_Thread = UpdateCouchdbThread(params)
    _Worker_Thread.refresh_metrics()
    _Worker_Thread.start()

    descriptors = []

    for name, desc in descriptions.iteritems():
        d = desc.copy()
        d['name'] = str(name)
        [ d.setdefault(key, METRIC_DEFAULTS[key]) for key in METRIC_DEFAULTS.iterkeys() ]
        descriptors.append(d)

    return descriptors

def metric_of(name):
    global _Worker_Thread
    return _Worker_Thread.metric_of(name)

def setting_of(name):
    global _Worker_Thread
    return _Worker_Thread.setting_of(name)

def metric_cleanup():
    global _Worker_Thread
    if _Worker_Thread is not None:
        _Worker_Thread.shutdown()
    logging.shutdown()
    pass

if __name__ == '__main__':
    from optparse import OptionParser

    try:
        logging.debug('running from the cmd line')
        parser = OptionParser()
        parser.add_option('-u', '--URL', dest='stats_url', default='http://127.0.0.1:5984/_stats', help='URL for couchdb stats page')
        parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
        parser.add_option('-r', '--refresh-rate', dest='refresh_rate', default=60)
        parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False)

        (options, args) = parser.parse_args()

        descriptors = metric_init({
            'stats_url': options.stats_url,
            'refresh_rate': options.refresh_rate
        })

        if options.debug:
            from pprint import pprint
            pprint(descriptors)

        for d in descriptors:
            v = d['call_back'](d['name'])

            if not options.quiet:
                print ' {0}: {1} {2} [{3}]' . format(d['name'], v, d['units'], d['description'])

        os._exit(1)

    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except StandardError:
        traceback.print_exc()
        os._exit(1)
    finally:
        metric_cleanup()

########NEW FILE########
__FILENAME__ = diskfree
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Disk Free gmond module for Ganglia
#
# Copyright (C) 2011 by Michael T. Conigliaro <mike [at] conigliaro [dot] org>.
# All rights reserved.
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

import re
import os

# Minimum disk size
MIN_DISK_SIZE=1

NAME_PREFIX = 'disk_free_'
PARAMS = {
    'mounts' : '/proc/mounts'
}


def get_value(name):
    """Return a value for the requested metric"""

    # parse unit type and path from name
    name_parser = re.match("^%s(absolute|percent)_(.*)$" % NAME_PREFIX, name)
    unit_type = name_parser.group(1)
    if name_parser.group(2) == 'rootfs':
        path = '/'
    else:
        path = '/' + name_parser.group(2).replace('_', '/')

    # get fs stats
    try:
        disk = os.statvfs(path)
        if unit_type == 'percent':
            result = (float(disk.f_bavail) / float(disk.f_blocks)) * 100
        else:
            result = (disk.f_bavail * disk.f_frsize) / float(2**30) # GB

    except OSError:
        result = 0

    except ZeroDivisionError:
        result = 0

    return result


def metric_init(lparams):
    """Initialize metric descriptors"""

    global PARAMS, MIN_DISK_SIZE

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]

    # read mounts file
    try:
        f = open(PARAMS['mounts'])
    except IOError:
        f = []

    # parse mounts and create descriptors
    descriptors = []
    for line in f:
        # We only want local file systems
        if line.startswith('/') or line.startswith('tmpfs'):
            mount_info = line.split()

            # create key from path
            if mount_info[1] == '/':
                path_key = 'rootfs'
            else:
                path_key = mount_info[1][1:].replace('/', '_')
                
            # Calculate the size of the disk. We'll use it exclude small disks
            disk = os.statvfs(mount_info[1])            
            disk_size = (disk.f_blocks * disk.f_frsize) / float(2**30)

            if disk_size > MIN_DISK_SIZE and mount_info[1] != "/dev":
	      for unit_type in ['absolute', 'percent']:
		  if unit_type == 'percent': 
			  units = '%'
		  else:
			  units = 'GB'
		  descriptors.append({
		      'name': NAME_PREFIX + unit_type + '_' + path_key,
		      'call_back': get_value,
		      'time_max': 60,
		      'value_type': 'float',
		      'units': units,
		      'slope': 'both',
		      'format': '%f',
		      'description': "Disk space available (%s) on %s" % (units, mount_info[1]),
		      'groups': 'disk'
		  })

    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    for d in descriptors:
        print (('%s = %s') % (d['name'], d['format'])) % (d['call_back'](d['name']))

########NEW FILE########
__FILENAME__ = diskpart
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
import time

descriptors = list()
mount_points = list()
Desc_Skel   = {}
_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock

class UpdateMetricThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 10
        if "refresh_rate" in params:
            self.refresh_rate = int(params["refresh_rate"])
        self.metric       = {}

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            self.update_metric()
            _Lock.release()
            time.sleep(self.refresh_rate)

        self.running = False

    def update_metric(self):
        for mtp in mount_points:
            #print >>sys.stderr, "mtp: ", mtp
            st = os.statvfs(mtp)
            if mtp == "/":
                part = "diskpart-root"
            else:
                part = "diskpart-" + mtp.replace('/', '_').lstrip('_')
            #print >>sys.stderr, "%u %u %u" % (st.f_blocks, st.f_bavail, st.f_bsize)
            self.metric[ part+"-total" ] = float(st.f_blocks * st.f_bsize) / 1024/1024/1024
            self.metric[ part+"-used"  ] = float((st.f_blocks - st.f_bavail) * st.f_bsize) / 1024/1024/1024

            self.metric[ part+"-inode-total" ] = st.f_files
            self.metric[ part+"-inode-used"  ] = st.f_files - st.f_favail


    def metric_of(self, name):
        val = 0
        if name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            _Lock.release()
        return val

def is_remotefs(dev, type):
    if dev.find(":") >= 0:
        return True
    elif dev.startswith("//") and (type == "smbfs" or type == "cifs"):
        return True
    return False

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, mount_points

    print '[diskpart] diskpart'
    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_of,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.3f',
        'units'       : 'GB',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'disk',
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 10

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    f = open("/proc/mounts", "r")
    # 0         1     2    3
    # /dev/sda4 /home ext3 rw,relatime,errors=continue,data=writeback 0 0
    for l in f:
        (dev, mtp, fstype, opt) = l.split(None, 3)
        if is_remotefs(dev, fstype):
            continue
        elif opt.startswith('ro'):
            continue
        elif not dev.startswith('/dev/') \
          and not (mtp == "/" and fstype == "tmpfs"): # for netboot
            continue;

        if mtp == "/":
            part = "diskpart-root"
        else:
            part = "diskpart-" + mtp.replace('/', '_').lstrip('_')
        #print >>sys.stderr, "dev=%s mount_point=%s part=%s" % (dev, mtp, part)

        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : part + "-total",
                    "description": "total partition space",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : part + "-used",
                    "description": "partition space used",
                    }))

        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : part + "-inode-total",
                    "description": "total number of inode",
                    "value_type" : "uint",
                    "format"     : "%d",
                    "units"      : "inode",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : part + "-inode-used",
                    "description": "total number of inode used",
                    "value_type" : "uint",
                    "format"     : "%d",
                    "units"      : "inode",
                    }))

        mount_points.append(mtp)

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_of(name):
    return _Worker_Thread.metric_of(name)

def metric_cleanup():
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    try:
        params = {
            }
        metric_init(params)
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        print sys.exc_info()[0]
        raise


########NEW FILE########
__FILENAME__ = diskstat
###  This script reports disk stat metrics to ganglia.
###
###  Notes:
###    This script exposes values in /proc/diskstats and calculates
###    various statistics based on the Linux kernel 2.6. To find
###    more information on these values, look in the Linux kernel
###    documentation for "I/O statistics fields".
###
###    By default, the script would monitor any entry listed under
###    /proc/diskstats that is not containing a number. Override it by passing
###    a list of devices in the 'devices' parameter.
###
###    This script has the option of explicitly setting which devices
###    to check using the "devices" option in your configuration. If
###    you set this value, it will invalidate the MIN_DISK_SIZE and
###    IGNORE_DEV options described below. This enables you to
###    monitor specific partitions instead of the entire device.
###    Example value: "sda1 sda2".
###    Example value: "sda sdb sdc".
###
###    This script also checks for a minimum disk size in order to
###    only measure interesting devices by default.
###    [Can be overriden if "devices" is set]
###
###    This script looks for disks to check in /proc/partitions while
###    ignoring any devices present in IGNORE_DEV by default.
###    [Can be overriden if "devices" is set]
###
###  Changelog:
###    v1.0.1 - 2010-07-22
###       * Initial version
###
###    v1.0.2 - 2010-08-03
###       * Modified reads_per_sec to not calculate per second delta.
###         This enables us to generate a better graph by stacking
###         reads/writes with reads/writes merged.
###

###  Copyright Jamie Isaacs. 2010
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import subprocess
import traceback
import logging
import os
import stat

descriptors = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s")
logging.debug('starting up')

last_update = 0
cur_time = 0
stats = {}
last_val = {}

MAX_UPDATE_TIME = 15
BYTES_PER_SECTOR = 512

# 5 GB
MIN_DISK_SIZE = 5242880
# Set to None to trigger disk discovery under /proc/diskstats
# Pass a 'devices' parameter to explicitly list disks to monitor
DEVICES = None
IGNORE_DEV = 'dm-|loop|drbd'

PARTITIONS_FILE = '/proc/partitions'
DISKSTATS_FILE = '/proc/diskstats'
DMDIR = '/dev/mapper'
device_mapper = ''

PARTITIONS = []
dmnames = []
dm2pair = {}
pair2dm = {}
devnames = []
dev2pair = {}
pair2dev = {}

def build_dmblock_major_minor_tables():
	"""Returns
	1) a table of filenames that are all device mapper block special files
	2) a dict mapping each device mapper name to (major,minor)
	3) a dict mapping each (major,minor) pair to a table of devce mapper names"""

	names = []
	name2pair = {}
	pair2name = {}
	mapper_entries = []

	mapper_entries = os.listdir(DMDIR)
	for n in mapper_entries:
		s = os.lstat(DMDIR + '/' + n)
		if stat.S_ISBLK(s[stat.ST_MODE]):
			names.append(n)
			maj = str(os.major(s.st_rdev))
			min = str(os.minor(s.st_rdev))
			name2pair[n] = (maj, min)
			pair2name[(maj, min)] = n

	logging.debug('grabbed dmsetup device info')
	logging.debug('dmsetup devices: ' + str(name2pair))

	return (names, name2pair, pair2name)

def build_block_major_minor_tables():
	"""Returns
	1) a table of filenames that are all block special files
	2) a dict mapping each dev name to (major,minor)
	3) a dict mapping each (major,minor) pair to a table of dev names"""
	dnames = []
	d2p = {}
	p2d = {}

	# Get values from diskstats file
	p = subprocess.Popen("awk '{print $1,$2, $3}' " + DISKSTATS_FILE, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = p.communicate()

	logging.debug('grabbed diskstat device info')
	logging.debug('diskstat devices: ' + str(out))

	for n in out.split('\n'):
		if n:
			[maj, min, name] = n.split()
			dnames.append(name)
			d2p[name] = (maj, min)
			p2d[(maj, min)] = name

	return (dnames, d2p, p2d)

def get_devname(dev):
	"""Returns
	device mapper name converted to dev name"""

	(maj,min) = dm2pair[dev]
	name = pair2dev[(maj,min)]
	return name

def list_dmnames():
	"""Returns
	string of device names associated with device mapper names"""

	global dmnames
	global dm2pair
	global pair2dm
	global devnames
	global dev2pair
	global pair2dev
	devlist = ''

	dmnames, dm2pair, pair2dm =  build_dmblock_major_minor_tables()
	logging.debug('dmnames: ' + str(dmnames))

	devnames, dev2pair, pair2dev =  build_block_major_minor_tables()
	logging.debug('devnames: ' + str(dmnames))

	for d in dmnames:
		devlist = devlist + ' ' + str(d)

	logging.debug('devlist: ' + str(devlist))

	return devlist

def get_partitions():
	logging.debug('getting partitions')
	global PARTITIONS

	if DEVICES is not None:
		# Explicit device list has been set
		logging.debug(' DEVICES has already been set')
		out = DEVICES

	else:	
		# Load partitions
		awk_cmd = "awk 'NR > 1 && $0 !~ /" + IGNORE_DEV + "/ && $4 !~ /[0-9]$/ {ORS=\" \"; print $4}' "
		p = subprocess.Popen(awk_cmd + PARTITIONS_FILE, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = p.communicate()
		logging.debug('  result: ' + out)
		
		if p.returncode:
			logging.warning('failed getting partitions')
			return p.returncode

	for dev in out.split():
		if DEVICES is not None:
			# Explicit device list has been set
			PARTITIONS.append(dev)
		else:		
			# Load disk block size
			f = open('/sys/block/' + dev + '/size', 'r')
			c = f.read()
			f.close()

			# Make sure device is large enough to collect stats
			if (int(c) * BYTES_PER_SECTOR / 1024) > MIN_DISK_SIZE:
				PARTITIONS.append(dev)
			else:
				logging.debug(' ignoring ' + dev + ' due to size constraints')

	logging.debug('success getting partitions')
	return 0


###########################################################################
# This is the order of metrics in /proc/diskstats
# 0 major         Major number
# 1 minor         Minor number
# 2 blocks        Blocks
# 3 name          Name
# 4 reads         This is the total number of reads completed successfully.
# 5 merge_read    Reads and writes which are adjacent to each other may be merged for
#               efficiency.  Thus two 4K reads may become one 8K read before it is
#               ultimately handed to the disk, and so it will be counted (and queued)
#               as only one I/O.  This field lets you know how often this was done.
# 6 s_read        This is the total number of sectors read successfully.
# 7 ms_read       This is the total number of milliseconds spent by all reads.
# 8 writes        This is the total number of writes completed successfully.
# 9 merge_write   Reads and writes which are adjacent to each other may be merged for
#               efficiency.  Thus two 4K reads may become one 8K read before it is
#               ultimately handed to the disk, and so it will be counted (and queued)
#               as only one I/O.  This field lets you know how often this was done.
# 10 s_write       This is the total number of sectors written successfully.
# 11 ms_write      This is the total number of milliseconds spent by all writes.
# 12 ios           The only field that should go to zero. Incremented as requests are
#               given to appropriate request_queue_t and decremented as they finish.
# 13 ms_io         This field is increases so long as field 9 is nonzero.
# 14 ms_weighted   This field is incremented at each I/O start, I/O completion, I/O
###########################################################################
def update_stats():
	logging.debug('updating stats')
	global last_update, stats, last_val, cur_time
	global MAX_UPDATE_TIME
	
	cur_time = time.time()

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True

	#####
	# Update diskstats
	stats = {}

	if not PARTITIONS:
		part = get_partitions()	
		if part:
			# Fail if return is non-zero
			logging.warning('error getting partitions')
			return False

	# Get values for each disk device
	for dev in PARTITIONS:
		logging.debug(" dev: " + dev)

		# Setup storage lists
		if not dev in stats:
			stats[dev] = {}
		if not dev in last_val:
			last_val[dev] = {}

		# Convert from dmname to devname for use by awk
		if device_mapper == 'true':
			olddev = dev
			dev = get_devname(dev)

		# Get values from diskstats file
		p = subprocess.Popen("awk -v dev=" + dev + " '$3 == dev' " + DISKSTATS_FILE, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = p.communicate()
		
		vals = out.split()
		logging.debug('  vals: ' + str(vals))

 		# Reset back to orignal dev name
		if device_mapper == 'true':
			dev = olddev

		get_diff(dev, 'reads',  int(vals[3]))
		get_diff(dev, 'writes', int(vals[7]))

		get_diff(dev, 'reads_merged',  int(vals[4]))
		get_diff(dev, 'writes_merged', int(vals[8]))

		get_delta(dev, 'read_bytes_per_sec',  int(vals[5]), float(BYTES_PER_SECTOR) )
		get_delta(dev, 'write_bytes_per_sec', int(vals[9]), float(BYTES_PER_SECTOR) )

		get_delta(dev, 'read_time',  float(vals[6]), 0.001 )
		get_delta(dev, 'write_time', float(vals[10]), 0.001 )

		get_diff(dev, 'io_time', float(vals[12]), 0.001)
		get_percent_time(dev, 'percent_io_time', float(stats[dev]['io_time']))
		get_delta(dev, 'weighted_io_time', float(vals[13]), 0.001)


	logging.debug('success refreshing stats')
	logging.debug('stats: ' + str(stats))
	logging.debug('last_val: ' + str(last_val))

	last_update = cur_time
	return True

def get_delta(dev, key, val, convert=1):
	logging.debug(' get_delta for ' + dev +  '_' + key)
	global stats, last_val

	if convert == 0:
		logging.warning(' convert is zero!')

	interval = cur_time - last_update

	if key in last_val[dev] and interval > 0:

		if val < last_val[dev][key]:
			logging.debug('  fixing int32 wrap')
			val += 4294967296

		stats[dev][key] = (val - last_val[dev][key]) * float(convert) / float(interval)
	else:
		stats[dev][key] = 0

	last_val[dev][key] = int(val)

def get_percent_time(dev, key, val):
	logging.debug(' get_percent_time for ' + dev +  '_' + key)
	global stats, last_val

	interval = cur_time - last_update

	if interval > 0:
		stats[dev][key] = (val / interval) * 100
	else:
		stats[dev][key] = 0

def get_diff(dev, key, val, convert=1):
	logging.debug(' get_diff for ' + dev + '_' + key)
	global stats, last_val

	if key in last_val[dev]:
		stats[dev][key] = (val - last_val[dev][key]) * float(convert)
	else:
		stats[dev][key] = 0

        # If for some reason we have a negative diff we should assume counters reset
        # and should set it back to 0
	if stats[dev][key] < 0:
	  stats[dev][key] = 0


	last_val[dev][key] = val

def get_stat(name):
	logging.debug(' getting stat: ' + name)
	global stats

	ret = update_stats()

	if ret:
		if name.startswith('diskstat_'):
			fir = name.find('_')
			sec = name.find('_', fir + 1)

			dev = name[fir+1:sec]
			label = name[sec+1:]

			try:
				return stats[dev][label]
			except:
				logging.warning('failed to fetch [' + dev + '] ' + name)
				return 0
		else:
			label = name

			try:
				return stats[label]
			except:
				logging.warning('failed to fetch ' + name)
				return 0

	else:
		return 0

def metric_init(params):
	global descriptors, device_mapper
	global MIN_DISK_SIZE, DEVICES, IGNORE_DEV

	# Use params.get here to assure function via gmond
	if params.get('device-mapper') == 'true':
		devices = list_dmnames()
		DEVICES = devices
		IGNORE_DEV = 'loop|drbd'
 		device_mapper = 'true'
		logging.debug('dm block devices: ' + str(devices))
	else:
		DEVICES = params.get('devices')

	logging.debug('init: ' + str(params))

	time_max = 60

	descriptions = dict(
		reads = {
			'units': 'reads',
			'description': 'The number of reads completed'},

		reads_merged = {
			'units': 'reads',
			'description': 'The number of reads merged. Reads which are adjacent to each other may be merged for efficiency. Multiple reads may become one before it is handed to the disk, and it will be counted (and queued) as only one I/O.'},

		read_bytes_per_sec = {
			'units': 'bytes/sec',
			'description': 'The number of bytes read per second'},

		read_time = {
			'units': 's',
			'description': 'The time in seconds spent reading'},

		writes = {
			'units': 'writes',
			'description': 'The number of writes completed'},

		writes_merged = {
			'units': 'writes',
			'description': 'The number of writes merged. Writes which are adjacent to each other may be merged for efficiency. Multiple writes may become one before it is handed to the disk, and it will be counted (and queued) as only one I/O.'},

		write_bytes_per_sec = {
			'units': 'bytes/sec',
			'description': 'The number of bbytes written per second'},

		write_time = {
			'units': 's',
			'description': 'The time in seconds spent writing'},

		io_time = {
			'units': 's',
			'description': 'The time in seconds spent in I/O operations'},

		percent_io_time = {
			'units': 'percent',
			'value_type': 'float',
			'format': '%f',
			'description': 'The percent of disk time spent on I/O operations'},

		weighted_io_time = {
			'units': 's',
			'description': 'The weighted time in seconds spend in I/O operations. This measures each I/O start, I/O completion, I/O merge, or read of these stats by the number of I/O operations in progress times the number of seconds spent doing I/O.'}
	)

	update_stats()

	for label in descriptions:
		for dev in PARTITIONS: 
			if stats[dev].has_key(label):

				d = {
					'name': 'diskstat_' + dev + '_' + label,
					'call_back': get_stat,
					'time_max': time_max,
					'value_type': 'float',
					'units': '',
					'slope': 'both',
					'format': '%f',
					'description': label,
					'groups': 'diskstat'
				}

				# Apply metric customizations from descriptions
				d.update(descriptions[label])	

				descriptors.append(d)
			else:
				logging.error("skipped " + label)

	#logging.debug('descriptors: ' + str(descriptors))

	# For command line testing
	#time.sleep(MAX_UPDATE_TIME)
	#update_stats()

	return descriptors

def metric_cleanup():
	logging.shutdown()
	# pass

if __name__ == '__main__':
	from optparse import OptionParser
	import os

	logging.debug('running from cmd line')
	parser = OptionParser()
	parser.add_option('-d', '--devices', dest='devices', default=None, help='devices to explicitly check')
	parser.add_option('-b', '--gmetric-bin', dest='gmetric_bin', default='/usr/bin/gmetric', help='path to gmetric binary')
	parser.add_option('-c', '--gmond-conf', dest='gmond_conf', default='/etc/ganglia/gmond.conf', help='path to gmond.conf')
	parser.add_option('-g', '--gmetric', dest='gmetric', action='store_true', default=False, help='submit via gmetric')
	parser.add_option('-m', '--device-mapper', dest='device_mapper', action='store_true', default=False, help='utilize all device mapper devices if set')
	parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)

	(options, args) = parser.parse_args()

	if options.device_mapper:
		metric_init({
			'device-mapper': 'true',
		})
	else:
		metric_init({
			'devices': options.devices,
		})

	while True:
		for d in descriptors:
			v = d['call_back'](d['name'])
			if not options.quiet:
				print ' %s: %s %s [%s]' % (d['name'], v, d['units'], d['description'])
	
			if options.gmetric:
				if d['value_type'] == 'uint':
					value_type = 'uint32'
				else:
					value_type = d['value_type']
	
				cmd = "%s --conf=%s --value='%s' --units='%s' --type='%s' --name='%s' --slope='%s'" % \
					(options.gmetric_bin, options.gmond_conf, v, d['units'], value_type, d['name'], d['slope'])
				os.system(cmd)
				
		print 'Sleeping 15 seconds'
		time.sleep(15)



########NEW FILE########
__FILENAME__ = ehcache
###  This script reports jmx ehcache metrics to ganglia.
###
###  Notes:
###    This script exposes ehcache MBeans to Ganglia. The following
###    are exposed:
###      - CacheHitCount
###      - CacheMissCount
###
###  Changelog:
###    v1.0.1 - 2010-07-30
###      * Initial version taken from jmxsh.py v1.0.5

###  Copyright Jamie Isaacs. 2010
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import subprocess
import traceback, sys, re
import tempfile
import logging

descriptors = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log2')
logging.debug('starting up')

last_update = 0
stats = {}
last_val = {}

METRICS = {}
COMP = {}
HOST = 'localhost'
PORT = '8887'
NAME = PORT

MAX_UPDATE_TIME = 15
JMXSH = '/usr/share/java/jmxsh.jar'

def update_stats():
	logging.debug('updating stats')
	global last_update, stats, last_val
	
	cur_time = time.time()

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True

	#####
	# Build jmxsh script into tmpfile
	sh  = '# jmxsh\njmx_connect -h ' + HOST + ' -p ' + PORT + '\n'
	sh += 'set obj [lindex [split [jmx_list net.sf.ehcache.hibernate] =] 2]\n'
	_mbean = 'net.sf.ehcache:type=SampledCache,SampledCacheManager=${obj},name='
	for name,mbean_name in METRICS.items():
		sh += 'puts "' + name + '_hit_count: [jmx_get -m ' + _mbean + mbean_name + ' CacheHitCount]"\n'
		sh += 'puts "' + name + '_miss_count: [jmx_get -m ' + _mbean + mbean_name + ' CacheMissCount]"\n'

	#logging.debug(sh)
	
	try:
		# run jmxsh.jar with the temp file as a script
		cmd = "java -jar " + JMXSH + " -q"
		p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = p.communicate(sh)
		#logging.debug('cmd: ' + cmd + '\nout:\n' + out + '\nerr: ' + err + '\ncode: ' + str(p.returncode))

		if p.returncode:
			logging.warning('failed executing jmxsh\n' + cmd + '\n' + err)
			return False
	except:
		logging.warning('Error running jmx java\n' + traceback.print_exc(file=sys.stdout))
		return False

	# Calculate diff for each metric
	try:
		# now parse out the values
		for line in out.strip().split('\n'):
			params = line.split(': ')
			name = params[0]
			val = params[1]

			val = int(val)
			if name in last_val:
				if val > last_val[name]:
					stats[name] = val - last_val[name]
				else:
					# value was reset since last update
					stats[name] = 0
			else:
				stats[name] = 0

			last_val[name] = val

	except:
		logging.warning('Error parsing\n' + traceback.print_exc(file=sys.stdout))
		return False

	logging.debug('success refreshing stats')
	logging.debug('stats: ' + str(stats))
	logging.debug('last_val: ' + str(last_val))

	last_update = cur_time
	return True

def get_stat(name):
	logging.debug('getting stat: ' + name)

	ret = update_stats()

	if ret:
		first = 'jmx_' + NAME + '_'
		if name.startswith(first):
			label = name[len(first):]
		else:
			label = name

		try:
			return stats[label]
		except:
			logging.warning('failed to fetch ' + name)
			return 0
	else:
		return 0

def metric_init(params):
	global descriptors
	global METRICS,HOST,PORT,NAME

	logging.debug('init: ' + str(params))

	try:
		HOST = params.pop('host')
		PORT = params.pop('port')
		NAME = params.pop('name')
		
	except:
		logging.warning('Incorrect parameters')

	METRICS = params

	update_stats()

	# dynamically build our descriptors based on the first run of update_stats()
	descriptions = dict()
	for name in stats:
		descriptions[name] = {}

	time_max = 60
	for label in descriptions:
		if stats.has_key(label):

			d = {
				'name': 'jmx_' + NAME + '_' + label,
				'call_back': get_stat,
				'time_max': time_max,
				'value_type': 'uint',
				'units': '',
				'format': '%u',
				'slope': 'both',
				'description': label,
				'groups': 'jmx'
			}

			# Apply metric customizations from descriptions
			d.update(descriptions[label])

			descriptors.append(d)

		else:
			logging.error("skipped " + label)

	#logging.debug('descriptors: ' + str(descriptors))

	return descriptors

def metric_cleanup():
	logging.shutdown()
	# pass

if __name__ == '__main__':
	from optparse import OptionParser
	import os

	logging.debug('running from cmd line')
	parser = OptionParser()
	parser.add_option('-p', '--param', dest='param', default='', help='module parameters')
	parser.add_option('-v', '--value', dest='value', default='', help='module values')
	parser.add_option('-b', '--gmetric-bin', dest='gmetric_bin', default='/usr/bin/gmetric', help='path to gmetric binary')
	parser.add_option('-c', '--gmond-conf', dest='gmond_conf', default='/etc/ganglia/gmond.conf', help='path to gmond.conf')
	parser.add_option('-g', '--gmetric', dest='gmetric', action='store_true', default=False, help='submit via gmetric')
	parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
	parser.add_option('-t', '--test', dest='test', action='store_true', default=False, help='test the regex list')

	(options, args) = parser.parse_args()

	_param = options.param.split(',')
	_val = options.value.split('|')

	params = {}
	i = 0
	for name in _param:
		params[name] = _val[i]
		i += 1
	
	metric_init(params)

	if options.test:
		print('')
		print(' waiting ' + str(MAX_UPDATE_TIME) + ' seconds')
		time.sleep(MAX_UPDATE_TIME)
		update_stats()

	for d in descriptors:
		v = d['call_back'](d['name'])
		if not options.quiet:
			print ' %s: %s %s [%s]' % (d['name'], d['format'] % v, d['units'], d['description'])

		if options.gmetric:
			if d['value_type'] == 'uint':
				value_type = 'uint32'
			else:
				value_type = d['value_type']

			cmd = "%s --conf=%s --value='%s' --units='%s' --type='%s' --name='%s' --slope='%s'" % \
				(options.gmetric_bin, options.gmond_conf, v, d['units'], value_type, d['name'], d['slope'])
			os.system(cmd)


########NEW FILE########
__FILENAME__ = elasticsearch
#! /usr/bin/python

try:
    import simplejson as json
    assert json  # silence pyflakes
except ImportError:
    import json

import logging
import time
import urllib
from functools import partial

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s")
logging.debug('starting up')

# short name to full path for stats
keyToPath = dict()

# INDICES METRICS #

## CACHE
keyToPath['es_cache_field_eviction'] = "nodes.%s.indices.cache.field_evictions"
keyToPath['es_cache_field_size'] = "nodes.%s.indices.cache.field_size_in_bytes"
keyToPath['es_cache_filter_count'] = "nodes.%s.indices.cache.filter_count"
keyToPath[
    'es_cache_filter_evictions'] = "nodes.%s.indices.cache.filter_evictions"
keyToPath[
    'es_cache_filter_size'] = "nodes.%s.indices.cache.filter_size_in_bytes"

## DOCS
keyToPath['es_docs_count'] = "nodes.%s.indices.docs.count"
keyToPath['es_docs_deleted'] = "nodes.%s.indices.docs.deleted"

## FLUSH
keyToPath['es_flush_total'] = "nodes.%s.indices.flush.total"
keyToPath['es_flush_time'] = "nodes.%s.indices.flush.total_time_in_millis"

## GET
keyToPath['es_get_exists_time'] = "nodes.%s.indices.get.exists_time_in_millis"
keyToPath['es_get_exists_total'] = "nodes.%s.indices.get.exists_total"
keyToPath['es_get_time'] = "nodes.%s.indices.get.time_in_millis"
keyToPath['es_get_total'] = "nodes.%s.indices.get.total"
keyToPath[
    'es_get_missing_time'] = "nodes.%s.indices.get.missing_time_in_millis"
keyToPath['es_get_missing_total'] = "nodes.%s.indices.get.missing_total"

## INDEXING
keyToPath['es_indexing_delete_time'] = "nodes.%s.indices.indexing.delete_time_in_millis"
keyToPath[
    'es_indexing_delete_total'] = "nodes.%s.indices.indexing.delete_total"
keyToPath['es_indexing_index_time'] = "nodes.%s.indices.indexing.index_time_in_millis"
keyToPath['es_indexing_index_total'] = "nodes.%s.indices.indexing.index_total"

## MERGES
keyToPath['es_merges_current'] = "nodes.%s.indices.merges.current"
keyToPath['es_merges_current_docs'] = "nodes.%s.indices.merges.current_docs"
keyToPath['es_merges_current_size'] = "nodes.%s.indices.merges.current_size_in_bytes"
keyToPath['es_merges_total'] = "nodes.%s.indices.merges.total"
keyToPath['es_merges_total_docs'] = "nodes.%s.indices.merges.total_docs"
keyToPath[
    'es_merges_total_size'] = "nodes.%s.indices.merges.total_size_in_bytes"
keyToPath['es_merges_time'] = "nodes.%s.indices.merges.total_time_in_millis"

## REFRESH
keyToPath['es_refresh_total'] = "nodes.%s.indices.refresh.total"
keyToPath['es_refresh_time'] = "nodes.%s.indices.refresh.total_time_in_millis"

## SEARCH
keyToPath['es_query_current'] = "nodes.%s.indices.search.query_current"
keyToPath['es_query_total'] = "nodes.%s.indices.search.query_total"
keyToPath['es_query_time'] = "nodes.%s.indices.search.query_time_in_millis"
keyToPath['es_fetch_current'] = "nodes.%s.indices.search.fetch_current"
keyToPath['es_fetch_total'] = "nodes.%s.indices.search.fetch_total"
keyToPath['es_fetch_time'] = "nodes.%s.indices.search.fetch_time_in_millis"

## STORE
keyToPath['es_indices_size'] = "nodes.%s.indices.store.size_in_bytes"

# JVM METRICS #
## MEM
keyToPath['es_heap_committed'] = "nodes.%s.jvm.mem.heap_committed_in_bytes"
keyToPath['es_heap_used'] = "nodes.%s.jvm.mem.heap_used_in_bytes"
keyToPath[
    'es_non_heap_committed'] = "nodes.%s.jvm.mem.non_heap_committed_in_bytes"
keyToPath['es_non_heap_used'] = "nodes.%s.jvm.mem.non_heap_used_in_bytes"

## THREADS
keyToPath['es_threads'] = "nodes.%s.jvm.threads.count"
keyToPath['es_threads_peak'] = "nodes.%s.jvm.threads.peak_count"

## GC
keyToPath['es_gc_time'] = "nodes.%s.jvm.gc.collection_time_in_millis"
keyToPath['es_gc_count'] = "nodes.%s.jvm.gc.collection_count"

# TRANSPORT METRICS #
keyToPath['es_transport_open'] = "nodes.%s.transport.server_open"
keyToPath['es_transport_rx_count'] = "nodes.%s.transport.rx_count"
keyToPath['es_transport_rx_size'] = "nodes.%s.transport.rx_size_in_bytes"
keyToPath['es_transport_tx_count'] = "nodes.%s.transport.tx_count"
keyToPath['es_transport_tx_size'] = "nodes.%s.transport.tx_size_in_bytes"

# HTTP METRICS #
keyToPath['es_http_current_open'] = "nodes.%s.http.current_open"
keyToPath['es_http_total_open'] = "nodes.%s.http.total_opened"

# PROCESS METRICS #
keyToPath[
    'es_open_file_descriptors'] = "nodes.%s.process.open_file_descriptors"


def dig_it_up(obj, path):
    try:
        if type(path) in (str, unicode):
            path = path.split('.')
        return reduce(lambda x, y: x[y], path, obj)
    except:
        return False


def update_result(result, url):
    logging.debug('[elasticsearch] Fetching ' + url)
    result = json.load(urllib.urlopen(url))
    return result


def get_stat_index(result, url, path, name):
    result = update_result(result, url)
    val = dig_it_up(result, path)

    if not isinstance(val, bool):
        return int(val)
    else:
        return None


def getStat(result, url, name):
    result = update_result(result, url)

    node = result['nodes'].keys()[0]
    val = dig_it_up(result, keyToPath[name] % node)

    # Check to make sure we have a valid result
    # JsonPath returns False if no match found
    if not isinstance(val, bool):
        return int(val)
    else:
        return None


def create_desc(skel, prop):
    d = skel.copy()
    for k, v in prop.iteritems():
        d[k] = v
    return d


def get_indices_descriptors(index, skel, result, url):
    metric_tpl = 'es_index_{0}_{{0}}'.format(index)
    callback = partial(get_stat_index, result, url)
    _create_desc = partial(create_desc, skel)

    descriptors = [
        _create_desc({
            'call_back': partial(callback, '_all.primaries.docs.count'),
            'name': metric_tpl.format('docs_count'),
            'description': 'document count for index {0}'.format(index),
        }),
        _create_desc({
            'call_back': partial(callback, '_all.primaries.store.size_in_bytes'),
            'name': metric_tpl.format('size'),
            'description': 'size in bytes for index {0}'.format(index),
            'units': 'Bytes',
            'format': '%.0f',
            'value_type': 'double'
        })
    ]

    return descriptors


def metric_init(params):
    descriptors = []

    logging.debug('[elasticsearch] Received the following parameters')
    logging.debug(params)

    host = params.get('host', 'http://localhost:9200/')
    url_cluster = '{0}_cluster/nodes/_local/stats?all=true'.format(host)

    # First iteration - Grab statistics
    logging.debug('[elasticsearch] Fetching ' + url_cluster)
    result = json.load(urllib.urlopen(url_cluster))

    metric_group = params.get('metric_group', 'elasticsearch')

    Desc_Skel = {
        'name': 'XXX',
        'call_back': partial(getStat, result, url_cluster),
        'time_max': 60,
        'value_type': 'uint',
        'units': 'units',
        'slope': 'both',
        'format': '%d',
        'description': 'XXX',
        'groups': metric_group,
    }

    indices = params.get('indices', '*').split()
    for index in indices:
        url_indices = '{0}{1}/_stats'.format(host, index)
        logging.debug('[elasticsearch] Fetching ' + url_indices)

        r_indices = json.load(urllib.urlopen(url_indices))
        descriptors += get_indices_descriptors(index,
                                               Desc_Skel,
                                               r_indices,
                                               url_indices)

    _create_desc = partial(create_desc, Desc_Skel)

    descriptors.append(
        _create_desc({
            'name': 'es_heap_committed',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Java Heap Committed (Bytes)',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_heap_used',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Java Heap Used (Bytes)',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_non_heap_committed',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Java Non Heap Committed (Bytes)',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_non_heap_used',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Java Non Heap Used (Bytes)',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_threads',
            'units': 'threads',
            'format': '%d',
            'description': 'Threads (open)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_threads_peak',
            'units': 'threads',
            'format': '%d',
            'description': 'Threads Peak (open)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_gc_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Java GC Time (ms)'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_transport_open',
            'units': 'sockets',
            'format': '%d',
            'description': 'Transport Open (sockets)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_transport_rx_count',
            'units': 'rx',
            'format': '%d',
            'slope': 'positive',
            'description': 'RX Count'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_transport_rx_size',
            'units': 'Bytes',
            'format': '%.0f',
            'slope': 'positive',
            'description': 'RX (Bytes)',
            'value_type': 'double',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_transport_tx_count',
            'units': 'tx',
            'format': '%d',
            'slope': 'positive',
            'description': 'TX Count'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_transport_tx_size',
            'units': 'Bytes',
            'format': '%.0f',
            'slope': 'positive',
            'description': 'TX (Bytes)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_http_current_open',
            'units': 'sockets',
            'format': '%d',
            'description': 'HTTP Open (sockets)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_http_total_open',
            'units': 'sockets',
            'format': '%d',
            'description': 'HTTP Open (sockets)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_indices_size',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Index Size (Bytes)',
            'value_type': 'double',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_gc_count',
            'format': '%d',
            'slope': 'positive',
            'description': 'Java GC Count',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_current',
            'format': '%d',
            'description': 'Merges (current)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_current_docs',
            'format': '%d',
            'description': 'Merges (docs)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_total',
            'format': '%d',
            'slope': 'positive',
            'description': 'Merges (total)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_total_docs',
            'format': '%d',
            'slope': 'positive',
            'description': 'Merges (total docs)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_current_size',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Merges size (current)',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_total_size',
            'units': 'Bytes',
            'format': '%.0f',
            'slope': 'positive',
            'description': 'Merges size (total)',
            'value_type': 'double',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_merges_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Merges Time (ms)'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_refresh_total',
            'units': 'refreshes',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Refresh'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_refresh_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Refresh Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_docs_count',
            'units': 'docs',
            'format': '%.0f',
            'description': 'Number of Documents',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_docs_deleted',
            'units': 'docs',
            'format': '%.0f',
            'description': 'Number of Documents Deleted',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_open_file_descriptors',
            'units': 'files',
            'format': '%d',
            'description': 'Open File Descriptors',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_cache_field_eviction',
            'units': 'units',
            'format': '%d',
            'slope': 'positive',
            'description': 'Field Cache Evictions',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_cache_field_size',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Field Cache Size',
            'value_type': 'double',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_cache_filter_count',
            'format': '%d',
            'description': 'Filter Cache Count',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_cache_filter_evictions',
            'format': '%d',
            'slope': 'positive',
            'description': 'Filter Cache Evictions',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_cache_filter_size',
            'units': 'Bytes',
            'format': '%.0f',
            'description': 'Filter Cache Size',
            'value_type': 'double'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_query_current',
            'units': 'Queries',
            'format': '%d',
            'description': 'Current Queries',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_query_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Query Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_fetch_current',
            'units': 'fetches',
            'format': '%d',
            'description': 'Current Fetches',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_fetch_total',
            'units': 'fetches',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Fetches'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_fetch_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Fetch Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_flush_total',
            'units': 'flushes',
            'format': '%d',
            'description': 'Total Flushes',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_flush_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Flush Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_exists_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Exists Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_exists_total',
            'units': 'total',
            'format': '%d',
            'description': 'Exists Total',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Get Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_total',
            'units': 'total',
            'format': '%d',
            'description': 'Get Total',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_missing_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Missing Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_get_missing_total',
            'units': 'total',
            'format': '%d',
            'description': 'Missing Total',
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_indexing_delete_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Delete Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_indexing_delete_total',
            'units': 'docs',
            'format': '%d',
            'slope': 'positive',
            'description': 'Delete Total'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_indexing_index_time',
            'units': 'ms',
            'format': '%d',
            'slope': 'positive',
            'description': 'Indexing Time'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_indexing_index_total',
            'units': 'docs',
            'format': '%d',
            'slope': 'positive',
            'description': 'Indexing Documents Total'
        })
    )

    descriptors.append(
        _create_desc({
            'name': 'es_query_total',
            'units': 'Queries',
            'format': '%d',
            'slope': 'positive',
            'description': 'Total Queries'
        })
    )
    return descriptors


def metric_cleanup():
    pass


#This code is for debugging and unit testing
if __name__ == '__main__':
    descriptors = metric_init({})
    for d in descriptors:
        v = d['call_back'](d['name'])
        logging.debug('value for %s is %s' % (d['name'], str(v)))

########NEW FILE########
__FILENAME__ = fibrechannel
#!/usr/bin/python
# Name: fibrechannel.py
# Desc: Ganglia module for polling Brocade Fibrechannel switches via snmnp (probably work with any snmp capable device)
# Author: Evan Fraser evan.fraser@trademe.co.nz
# Date: August 2012
# Copyright: GPL
# Updated 21/03/2014 to do SNMP calls threaded.

import sys
import os
import re
import time
import threading
import pprint
from pysnmp.entity.rfc3413.oneliner import cmdgen
NIPARAMS = {}

NIMETRICS = {
    'time' : 0,
    'data' : {}
}
LAST_NIMETRICS = dict(NIMETRICS)
NIMETRICS_CACHE_MAX = 10
SNMPTABLE = {}

descriptors = list()

oidDict = {
    'ifIndex'       : (1,3,6,1,2,1,2,2,1,1),
    'ifDescr'       : (1,3,6,1,2,1,2,2,1,2),
    'ifInOctets'    : (1,3,6,1,2,1,2,2,1,10),
    'ifInUcastPkts' : (1,3,6,1,2,1,2,2,1,11),
    'ifInErrors'    : (1,3,6,1,2,1,2,2,1,14),
    'ifOutOctets'    : (1,3,6,1,2,1,2,2,1,16),
    'ifOutUcastPkts' : (1,3,6,1,2,1,2,2,1,17),
    'ifOutErrors'    : (1,3,6,1,2,1,2,2,1,20),
    }


def get_metrics():
    """Return all metrics"""

    global NIMETRICS, LAST_NIMETRICS, SNMPTABLE

    # if interval since last check > NIMETRICS_CACHE_MAX get metrics again
    if (time.time() - NIMETRICS['time']) > NIMETRICS_CACHE_MAX:
        metrics = {}
        for para in NIPARAMS.keys():
            if para.startswith('switch_'):
                ipaddr,name = NIPARAMS[para].split(':')
                #snmpTable = runSnmp(oidDict,ipaddr)
                threading.Thread(runSnmp(oidDict,ipaddr))
                snmpTable = SNMPTABLE[ipaddr]
                newmetrics = buildDict(oidDict,snmpTable,name)
                metrics = dict(newmetrics, **metrics)

        # update cache
        LAST_NIMETRICS = dict(NIMETRICS)
        NIMETRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [NIMETRICS, LAST_NIMETRICS]

def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()
    try:
        delta = float(curr_metrics['data'][name] - last_metrics['data'][name])/(curr_metrics['time'] - last_metrics['time'])
        #print delta
        if delta < 0:
            print "Less than 0"
            delta = 0
    except StandardError:
        delta = 0

    return delta

# Separate routine to perform SNMP queries and returns table (dict)
def runSnmp(oidDict,ip):
    global SNMPTABLE
    # cmdgen only takes tuples, oid strings don't work

#    'ifIndex'       : (1,3,6,1,2,1,2,2,1,1),
#    'ifDescr'       : (1,3,6,1,2,1,2,2,1,2),
#    'ifInOctets'    : (1,3,6,1,2,1,2,2,1,10),
#    'ifInUcastPkts' : (1,3,6,1,2,1,2,2,1,11),
#    'ifInErrors'    : (1,3,6,1,2,1,2,2,1,14),
#    'ifOutOctets'    : (1,3,6,1,2,1,2,2,1,16),
#    'ifOutUcastPkts' : (1,3,6,1,2,1,2,2,1,17),
#    'ifOutErrors'    : (1,3,6,1,2,1,2,2,1,20),

    #Runs the SNMP query, The order that oid's are passed determines the order in the results
    errorIndication, errorStatus, errorIndex, varBindTable = cmdgen.CommandGenerator().nextCmd(
        # SNMP v2
        cmdgen.CommunityData('test-agent', 'public'),
        cmdgen.UdpTransportTarget((ip, 161)),
        oidDict['ifIndex'],
        oidDict['ifDescr'],
        oidDict['ifInOctets'],
        oidDict['ifInErrors'],
        oidDict['ifInUcastPkts'],
        oidDict['ifOutOctets'],
        oidDict['ifOutErrors'],
        oidDict['ifOutUcastPkts'],
        )
    #pprint.pprint(varBindTable)
    # Check for SNMP errors
    if errorIndication:
        print errorIndication
    else:
        if errorStatus:
            print '%s at %s\n' % (
                errorStatus.prettyPrint(), errorIndex and varBindTable[-1][int(errorIndex)-1] or '?'
                )
        else:
            #return(varBindTable)
            SNMPTABLE[ip] = varBindTable

def buildDict(oidDict,t,switch): # passed a list of tuples, build's a dict based on the alias name
    builtdict = {}
    
    for line in t:
        #        if t[t.index(line)][2][1] != '':
        string = str(t[t.index(line)][1][1]) # this is the ifDescr 
        #print string
        match = re.search(r'FC port', string)
        if match and t[t.index(line)][0][1] != '':
            #alias = str(t[t.index(line)][0][1])
            index = str(t[t.index(line)][0][1])
            temp = str(t[t.index(line)][1][1]) #(use ifDescr)
            #lowercase the name, change spaces + '/' to '_'
            name = ((temp.lower()).replace(' ','_')).replace('/','_')
            inoct = str(t[t.index(line)][2][1])
            builtdict[switch+'_'+name+'_bitsin'] = int(inoct) * 8
            outoct = str(t[t.index(line)][5][1])
            builtdict[switch+'_'+name+'_bitsout'] = int(outoct) * 8
            inpkt = str(t[t.index(line)][4][1])
            builtdict[switch+'_'+name+'_pktsin'] = int(inpkt)
            outpkt = str(t[t.index(line)][7][1])
            builtdict[switch+'_'+name+'_pktsout'] = int(outpkt)
            inerrors = str(t[t.index(line)][3][1])
            builtdict[switch+'_'+name+'_inerrors'] = int(inerrors)
            outerrors = str(t[t.index(line)][6][1])
            builtdict[switch+'_'+name+'_outerrors'] = int(outerrors)
                         
    #pprint.pprint(builtdict)
    return builtdict

# define_metrics will run an snmp query on an ipaddr, find interfaces, build descriptors and set spoof_host
# define_metrics is called from metric_init
def define_metrics(Desc_Skel, ipaddr, switch):
    global SNMPTABLE
    snmpThread = threading.Thread(runSnmp(oidDict,ipaddr))
    snmpTable = SNMPTABLE[ipaddr]

    #snmpTable = runSnmp(oidDict,ipaddr)
    aliasdict = buildDict(oidDict,snmpTable,switch)
    spoof_string = ipaddr + ':' + switch
    #print newdict
    #pprint.pprint(aliasdict.keys())

    for key in aliasdict.keys():
        if "bitsin" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "bits/sec",
                        "description" : "received bits per sec",
                        "groups"      : "Throughput",
                        "spoof_host"  : spoof_string,
                        }))
        elif "bitsout" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "bits/sec",
                        "description" : "transmitted bits per sec",
                        "groups"      : "Throughput",
                        "spoof_host"  : spoof_string,
                        }))
        elif "pktsin" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "pkts/sec",
                        "description" : "received packets per sec",
                        "groups"      : "Packets",
                        "spoof_host"  : spoof_string,
                        }))
        elif "pktsout" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "pkts/sec",
                        "description" : "transmitted packets per sec",
                        "groups"      : "Packets",
                        "spoof_host"  : spoof_string,
                        }))
        elif "inerrors" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "errors",
                        "description" : "inbound packet errors",
                        "groups"      : "Packets",
                        "spoof_host"  : spoof_string,
                        }))
        elif "outerrors" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "errors",
                        "description" : "outbound packet errors",
                        "groups"      : "Packets",
                        "spoof_host"  : spoof_string,
                        }))


    return descriptors

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug, newdict

    print '[switch] Received the following parameters'
    print params

    #Import the params into the global NIPARAMS
    for key in params:
        NIPARAMS[key] = params[key]

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'switch',
        }  

    # Find all the switch's passed in params    
    for para in params.keys():
         if para.startswith('switch_'):
             #Get ipaddr + name of switchs from params
             ipaddr,name = params[para].split(':')
             # pass skel, ip and name to define_metrics to create descriptors
             descriptors = define_metrics(Desc_Skel, ipaddr, name)
    #Return the descriptors back to gmond
    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d


def metric_cleanup():
    '''Clean up the metric module.'''
    pass

# For CLI Debuging:
if __name__ == '__main__':
    params = {
        'switch_1' : '192.168.1.1:switch1',
        #'switch_2' : '192.168.1.2:switch2',
              }
    descriptors = metric_init(params)
    print len(descriptors)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)        
        print 'Sleeping 5 seconds'
        time.sleep(5)
#exit(0)

########NEW FILE########
__FILENAME__ = nvidia_smi
#####
# Copyright (c) 2011-2012, NVIDIA Corporation.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the NVIDIA Corporation nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF 
# THE POSSIBILITY OF SUCH DAMAGE.
#####

#
# nvidia_smi
# nvml_bindings <at> nvidia <dot> com
#
# Sample code that attempts to reproduce the output of nvidia-smi -q- x
# For many cases the output should match
#
# To Run:
# $ python
# Python 2.7 (r27:82500, Sep 16 2010, 18:02:00) 
# [GCC 4.5.1 20100907 (Red Hat 4.5.1-3)] on linux2
# Type "help", "copyright", "credits" or "license" for more information.
# >>> import nvidia_smi
# >>> print(nvidia_smi.XmlDeviceQuery())
# ...
#

from pynvml import *
import datetime

#
# Helper functions
#
def GetEccByType(handle, counterType, bitType):
    try:
        count = str(nvmlDeviceGetTotalEccErrors(handle, bitType, counterType))
    except NVMLError as err:
        count = handleError(err)
    
    try:
        detail = nvmlDeviceGetDetailedEccErrors(handle, bitType, counterType)
        deviceMemory = str(detail.deviceMemory)
        registerFile = str(detail.registerFile)
        l1Cache = str(detail.l1Cache)
        l2Cache = str(detail.l2Cache)
    except NVMLError as err:
        msg = handleError(err)
        deviceMemory = msg
        registerFile = msg
        l1Cache = msg
        l2Cache = msg
    strResult = ''
    strResult += '          <device_memory>' + deviceMemory + '</device_memory>\n'
    strResult += '          <register_file>' + registerFile + '</register_file>\n'
    strResult += '          <l1_cache>' + l1Cache + '</l1_cache>\n'
    strResult += '          <l2_cache>' + l2Cache + '</l2_cache>\n'
    strResult += '          <total>' + count + '</total>\n'
    return strResult

def GetEccByCounter(handle, counterType):
    strResult = ''
    strResult += '        <single_bit>\n'
    strResult += str(GetEccByType(handle, counterType, NVML_SINGLE_BIT_ECC))
    strResult += '        </single_bit>\n'
    strResult += '        <double_bit>\n'
    strResult += str(GetEccByType(handle, counterType, NVML_DOUBLE_BIT_ECC))
    strResult += '        </double_bit>\n'
    return strResult

def GetEccStr(handle):
    strResult = ''
    strResult += '      <volatile>\n'
    strResult += str(GetEccByCounter(handle, NVML_VOLATILE_ECC))
    strResult += '      </volatile>\n'
    strResult += '      <aggregate>\n'
    strResult += str(GetEccByCounter(handle, NVML_AGGREGATE_ECC))
    strResult += '      </aggregate>\n'
    return strResult

#
# Converts errors into string messages
#
def handleError(err):
    if (err.value == NVML_ERROR_NOT_SUPPORTED):
        return "N/A"
    else:
        return err.__str__()

#######
def XmlDeviceQuery():

    try:
        #
        # Initialize NVML
        #
        nvmlInit()
        strResult = ''

        strResult += '<?xml version="1.0" ?>\n'
        strResult += '<!DOCTYPE nvidia_smi_log SYSTEM "nvsmi_device.dtd">\n'
        strResult += '<nvidia_smi_log>\n'

        strResult += '  <timestamp>' + str(datetime.date.today()) + '</timestamp>\n'
        strResult += '  <driver_version>' + str(nvmlSystemGetDriverVersion()) + '</driver_version>\n'

        deviceCount = nvmlDeviceGetCount()
        strResult += '  <attached_gpus>' + str(deviceCount) + '</attached_gpus>\n'

        for i in range(0, deviceCount):
            handle = nvmlDeviceGetHandleByIndex(i)
            
            pciInfo = nvmlDeviceGetPciInfo(handle)    
            
            strResult += '  <gpu id="%s">\n' % pciInfo.busId
            
            strResult += '    <product_name>' + nvmlDeviceGetName(handle) + '</product_name>\n'
            
            try:
                state = ('Enabled' if (nvmlDeviceGetDisplayMode(handle) != 0) else 'Disabled')
            except NVMLError as err:
                state = handleError(err)
            
            strResult += '    <display_mode>' + state + '</display_mode>\n'

            try:
                mode = 'Enabled' if (nvmlDeviceGetPersistenceMode(handle) != 0) else 'Disabled'
            except NVMLError as err:
                mode = handleError(err)
            
            strResult += '    <persistence_mode>' + mode + '</persistence_mode>\n'
                
            strResult += '    <driver_model>\n'

            try:
                current = str(nvmlDeviceGetCurrentDriverModel(handle))
            except NVMLError as err:
                current = handleError(err)
            strResult += '      <current_dm>' + current + '</current_dm>\n'

            try:
                pending = str(nvmlDeviceGetPendingDriverModel(handle))
            except NVMLError as err:
                pending = handleError(err)

            strResult += '      <pending_dm>' + pending + '</pending_dm>\n'

            strResult += '    </driver_model>\n'

            try:
                serial = nvmlDeviceGetSerial(handle)
            except NVMLError as err:
                serial = handleError(err)

            strResult += '    <serial>' + serial + '</serial>\n'

            try:
                uuid = nvmlDeviceGetUUID(handle)
            except NVMLError as err:
                uuid = handleError(err)

            strResult += '    <uuid>' + uuid + '</uuid>\n'
            
            try:
                vbios = nvmlDeviceGetVbiosVersion(handle)
            except NVMLError as err:
                vbios = handleError(err)

            strResult += '    <vbios_version>' + vbios + '</vbios_version>\n'

            strResult += '    <inforom_version>\n'
            
            try:
                oem = nvmlDeviceGetInforomVersion(handle, NVML_INFOROM_OEM)
                if oem == '':
                    oem = 'N/A'
            except NVMLError as err:
                oem = handleError(err)
                
            strResult += '      <oem_object>' + oem + '</oem_object>\n'
            
            try:
                ecc = nvmlDeviceGetInforomVersion(handle, NVML_INFOROM_ECC)
                if ecc == '':
                    ecc = 'N/A'
            except NVMLError as err:
                ecc = handleError(err)
            
            strResult += '      <ecc_object>' + ecc + '</ecc_object>\n'
            try:
                pwr = nvmlDeviceGetInforomVersion(handle, NVML_INFOROM_POWER)
                if pwr == '':
                    pwr = 'N/A'
            except NVMLError as err:
                pwr = handleError(err)
            
            strResult += '      <pwr_object>' + pwr + '</pwr_object>\n'
            strResult += '    </inforom_version>\n'

            strResult += '    <pci>\n'
            strResult += '      <pci_bus>%02X</pci_bus>\n' % pciInfo.bus
            strResult += '      <pci_device>%02X</pci_device>\n' % pciInfo.device
            strResult += '      <pci_domain>%04X</pci_domain>\n' % pciInfo.domain
            strResult += '      <pci_device_id>%08X</pci_device_id>\n' % (pciInfo.pciDeviceId)
            strResult += '      <pci_sub_system_id>%08X</pci_sub_system_id>\n' % (pciInfo.pciSubSystemId)
            strResult += '      <pci_bus_id>' + str(pciInfo.busId) + '</pci_bus_id>\n'
            strResult += '      <pci_gpu_link_info>\n'


            strResult += '        <pcie_gen>\n'

            try:
                gen = str(nvmlDeviceGetMaxPcieLinkGeneration(handle))
            except NVMLError as err:
                gen = handleError(err)

            strResult += '          <max_link_gen>' + gen + '</max_link_gen>\n'

            try:
                gen = str(nvmlDeviceGetCurrPcieLinkGeneration(handle))
            except NVMLError as err:
                gen = handleError(err)

            strResult += '          <current_link_gen>' + gen + '</current_link_gen>\n'
            strResult += '        </pcie_gen>\n'
            strResult += '        <link_widths>\n'

            try:
                width = str(nvmlDeviceGetMaxPcieLinkWidth(handle)) + 'x'
            except NVMLError as err:
                width = handleError(err)

            strResult += '          <max_link_width>' + width + '</max_link_width>\n'

            try:
                width = str(nvmlDeviceGetCurrPcieLinkWidth(handle)) + 'x'
            except NVMLError as err:
                width = handleError(err)

            strResult += '          <current_link_width>' + width + '</current_link_width>\n'

            strResult += '        </link_widths>\n'
            strResult += '      </pci_gpu_link_info>\n'
            strResult += '    </pci>\n'

            try:
                fan = str(nvmlDeviceGetFanSpeed(handle)) + ' %'
            except NVMLError as err:
                fan = handleError(err)
            strResult += '    <fan_speed>' + fan + '</fan_speed>\n'

            try:
                memInfo = nvmlDeviceGetMemoryInfo(handle)
                mem_total = str(memInfo.total / 1024 / 1024) + ' MB'
                mem_used = str(memInfo.used / 1024 / 1024) + ' MB'
                mem_free = str(memInfo.free / 1024 / 1024) + ' MB'
            except NVMLError as err:
                error = handleError(err)
                mem_total = error
                mem_used = error
                mem_free = error

            strResult += '    <memory_usage>\n'
            strResult += '      <total>' + mem_total + '</total>\n'
            strResult += '      <used>' + mem_used + '</used>\n'
            strResult += '      <free>' + mem_free + '</free>\n'
            strResult += '    </memory_usage>\n'

            
            try:
                mode = nvmlDeviceGetComputeMode(handle)
                if mode == NVML_COMPUTEMODE_DEFAULT:
                    modeStr = 'Default'
                elif mode == NVML_COMPUTEMODE_EXCLUSIVE_THREAD:
                    modeStr = 'Exclusive Thread'
                elif mode == NVML_COMPUTEMODE_PROHIBITED:
                    modeStr = 'Prohibited'
                elif mode == NVML_COMPUTEMODE_EXCLUSIVE_PROCESS:
                    modeStr = 'Exclusive Process'
                else:
                    modeStr = 'Unknown'
            except NVMLError as err:
                modeStr = handleError(err)

            strResult += '    <compute_mode>' + modeStr + '</compute_mode>\n'

            try:
                util = nvmlDeviceGetUtilizationRates(handle)
                gpu_util = str(util.gpu)
                mem_util = str(util.memory)
            except NVMLError as err:
                error = handleError(err)
                gpu_util = error
                mem_util = error
            
            strResult += '    <utilization>\n'
            strResult += '      <gpu_util>' + gpu_util + ' %</gpu_util>\n'
            strResult += '      <memory_util>' + mem_util + ' %</memory_util>\n'
            strResult += '    </utilization>\n'
            
            try:
                (current, pending) = nvmlDeviceGetEccMode(handle)
                curr_str = 'Enabled' if (current != 0) else 'Disabled'
                pend_str = 'Enabled' if (pending != 0) else 'Disabled'
            except NVMLError as err:
                error = handleError(err)
                curr_str = error
                pend_str = error

            strResult += '    <ecc_mode>\n'
            strResult += '      <current_ecc>' + curr_str + '</current_ecc>\n'
            strResult += '      <pending_ecc>' + pend_str + '</pending_ecc>\n'
            strResult += '    </ecc_mode>\n'

            strResult += '    <ecc_errors>\n'
            strResult += GetEccStr(handle)
            strResult += '    </ecc_errors>\n'
            
            try:
                temp = str(nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)) + ' C'
            except NVMLError as err:
                temp = handleError(err)

            strResult += '    <temperature>\n'
            strResult += '      <gpu_temp>' + temp + '</gpu_temp>\n'
            strResult += '    </temperature>\n'

            strResult += '    <power_readings>\n'
            try:
                perfState = nvmlDeviceGetPowerState(handle)
            except NVMLError as err:
                perfState = handleError(err)
            strResult += '      <power_state>P%s</power_state>\n' % perfState
            try:
                powMan = nvmlDeviceGetPowerManagementMode(handle)
                powManStr = 'Supported' if powMan != 0 else 'N/A'
            except NVMLError as err:
                powManStr = handleError(err)
            strResult += '      <power_management>' + powManStr + '</power_management>\n'
            try:
                powDraw = (nvmlDeviceGetPowerUsage(handle) / 1000.0)
                powDrawStr = '%.2f W' % powDraw
            except NVMLError as err:
                powDrawStr = handleError(err)
            strResult += '      <power_draw>' + powDrawStr + '</power_draw>\n'
            try:
                powLimit = (nvmlDeviceGetPowerManagementLimit(handle) / 1000.0)
                powLimitStr = '%d W' % powLimit
            except NVMLError as err:
                powLimitStr = handleError(err)
            strResult += '      <power_limit>' + powLimitStr + '</power_limit>\n'
            strResult += '    </power_readings>\n'

            strResult += '    <clocks>\n'
            try:
                graphics = str(nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS))
            except NVMLError as err:
                graphics = handleError(err)
            strResult += '      <graphics_clock>' +graphics + ' MHz</graphics_clock>\n'
            try:
                sm = str(nvmlDeviceGetClockInfo(handle, NVML_CLOCK_SM))
            except NVMLError as err:
                sm = handleError(err)
            strResult += '      <sm_clock>' + sm + ' MHz</sm_clock>\n'
            try:
                mem = str(nvmlDeviceGetClockInfo(handle, NVML_CLOCK_MEM))
            except NVMLError as err:
                mem = handleError(err)
            strResult += '      <mem_clock>' + mem + ' MHz</mem_clock>\n'
            strResult += '    </clocks>\n'

            strResult += '    <max_clocks>\n'
            try:
                graphics = str(nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_GRAPHICS))
            except NVMLError as err:
                graphics = handleError(err)
            strResult += '      <graphics_clock>' + graphics + ' MHz</graphics_clock>\n'
            try:
                sm = str(nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_SM))
            except NVMLError as err:
                sm = handleError(err)
            strResult += '      <sm_clock>' + sm + ' MHz</sm_clock>\n'
            try:
                mem = str(nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_MEM))
            except NVMLError as err:
                mem = handleError(err)
            strResult += '      <mem_clock>' + mem + ' MHz</mem_clock>\n'
            strResult += '    </max_clocks>\n'
            
            try:
                perfState = nvmlDeviceGetPowerState(handle)
                perfStateStr = 'P%s' % perfState
            except NVMLError as err:
                perfStateStr = handleError(err)
            strResult += '    <performance_state>' + perfStateStr + '</performance_state>\n'
            
            strResult += '    <compute_processes>\n'
            
            procstr = ""
            try:
                procs = nvmlDeviceGetComputeRunningProcesses(handle)
            except NVMLError as err:
                procs = []
                procstr = handleError(err)
             
            for p in procs:
                procstr += '    <process_info>\n'
                procstr += '      <pid>%d</pid>\n' % p.pid
                try:
                    name = str(nvmlSystemGetProcessName(p.pid))
                except NVMLError as err:
                    if (err.value == NVML_ERROR_NOT_FOUND):
                        # probably went away
                        continue
                    else:
                        name = handleError(err)
                procstr += '      <process_name>' + name + '</process_name>\n'
                procstr += '      <used_memory>\n'
                if (p.usedGpuMemory == None):
                    procstr += 'N\A'
                else:
                    procstr += '%d MB\n' % (p.usedGpuMemory / 1024 / 1024)
                procstr += '</used_memory>\n'
                procstr += '    </process_info>\n'
            
            strResult += procstr
            strResult += '    </compute_processes>\n'
            strResult += '  </gpu>\n'
            
        strResult += '</nvidia_smi_log>\n'
        
    except NVMLError as err:
        strResult += 'nvidia_smi.py: ' + err.__str__() + '\n'
    
    nvmlShutdown()
    
    return strResult


########NEW FILE########
__FILENAME__ = pynvml
#####
# Copyright (c) 2011-2012, NVIDIA Corporation.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the NVIDIA Corporation nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF 
# THE POSSIBILITY OF SUCH DAMAGE.
#####

##
# Python bindings for the NVML library
##
from ctypes import *
from ctypes.util import find_library
import sys
import threading
    
## C Type mappings ##
## Enums
_nvmlEnableState_t = c_uint
NVML_FEATURE_DISABLED    = 0
NVML_FEATURE_ENABLED     = 1

_nvmlTemperatureSensors_t = c_uint
NVML_TEMPERATURE_GPU     = 0

_nvmlComputeMode_t = c_uint
NVML_COMPUTEMODE_DEFAULT           = 0
NVML_COMPUTEMODE_EXCLUSIVE_THREAD  = 1
NVML_COMPUTEMODE_PROHIBITED        = 2
NVML_COMPUTEMODE_EXCLUSIVE_PROCESS = 3

_nvmlEccBitType_t = c_uint
NVML_SINGLE_BIT_ECC    = 0
NVML_DOUBLE_BIT_ECC    = 1

_nvmlEccCounterType_t = c_uint
NVML_VOLATILE_ECC      = 0
NVML_AGGREGATE_ECC     = 1

_nvmlClockType_t = c_uint
NVML_CLOCK_GRAPHICS  = 0
NVML_CLOCK_SM        = 1
NVML_CLOCK_MEM       = 2

_nvmlDriverModel_t = c_uint
NVML_DRIVER_WDDM       = 0
NVML_DRIVER_WDM        = 1

_nvmlPstates_t = c_uint
NVML_PSTATE_0               = 0
NVML_PSTATE_1               = 1
NVML_PSTATE_2               = 2
NVML_PSTATE_3               = 3
NVML_PSTATE_4               = 4
NVML_PSTATE_5               = 5
NVML_PSTATE_6               = 6
NVML_PSTATE_7               = 7
NVML_PSTATE_8               = 8
NVML_PSTATE_9               = 9
NVML_PSTATE_10              = 10
NVML_PSTATE_11              = 11
NVML_PSTATE_12              = 12
NVML_PSTATE_13              = 13
NVML_PSTATE_14              = 14
NVML_PSTATE_15              = 15
NVML_PSTATE_UNKNOWN         = 32

_nvmlInforomObject_t = c_uint
NVML_INFOROM_OEM            = 0
NVML_INFOROM_ECC            = 1
NVML_INFOROM_POWER          = 2

_nvmlReturn_t = c_uint
NVML_SUCCESS                   = 0
NVML_ERROR_UNINITIALIZED       = 1
NVML_ERROR_INVALID_ARGUMENT    = 2
NVML_ERROR_NOT_SUPPORTED       = 3
NVML_ERROR_NO_PERMISSION       = 4
NVML_ERROR_ALREADY_INITIALIZED = 5
NVML_ERROR_NOT_FOUND           = 6
NVML_ERROR_INSUFFICIENT_SIZE   = 7
NVML_ERROR_INSUFFICIENT_POWER  = 8
NVML_ERROR_DRIVER_NOT_LOADED   = 9
NVML_ERROR_TIMEOUT             = 10,
NVML_ERROR_UNKNOWN             = 999

_nvmlFanState_t = c_uint
NVML_FAN_NORMAL             = 0
NVML_FAN_FAILED             = 1

_nvmlLedColor_t = c_uint
NVML_LED_COLOR_GREEN        = 0
NVML_LED_COLOR_AMBER        = 1

# C preprocessor defined values
nvmlFlagDefault             = 0
nvmlFlagForce               = 1

# buffer size
NVML_DEVICE_INFOROM_VERSION_BUFFER_SIZE      = 16
NVML_DEVICE_UUID_BUFFER_SIZE                 = 80
NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE       = 81
NVML_SYSTEM_NVML_VERSION_BUFFER_SIZE         = 80
NVML_DEVICE_NAME_BUFFER_SIZE                 = 64
NVML_DEVICE_SERIAL_BUFFER_SIZE               = 30
NVML_DEVICE_VBIOS_VERSION_BUFFER_SIZE        = 32

NVML_VALUE_NOT_AVAILABLE_ulonglong = c_ulonglong(-1)

## Lib loading ##
nvmlLib = None
libLoadLock = threading.Lock()

## Error Checking ##
class NVMLError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(nvmlErrorString(self.value))

def _nvmlCheckReturn(ret):
    if (ret != NVML_SUCCESS):
        raise NVMLError(ret)
    return ret

## Function access ##
def _nvmlGetFunctionPointer(name):
    global nvmlLib
    global libLoadLock
    
    libLoadLock.acquire()
    try:
        # ensure library was loaded
        if (nvmlLib == None):
            raise NVMLError(NVML_ERROR_UNINITIALIZED)
        try:
            return getattr(nvmlLib, name)
        except AttributeError as attrError:
            raise NVMLError(NVML_ERROR_NOT_SUPPORTED)
    finally:
        # lock is always freed
        libLoadLock.release()

## Alternative object
# Allows the object to be printed
# Allows mismatched types to be assigned
#  - like None when the Structure variant requires c_uint
class nvmlFriendlyObject(object):
    def __init__(self, dictionary):
        for x in dictionary:
            setattr(self, x, dictionary[x])
    def __str__(self):
        return self.__dict__.__str__()

def nvmlStructToFriendlyObject(struct):
    d = {}
    for x in struct._fields_:
        key = x[0]
        value = getattr(struct, key)
        d[key] = value
    obj = nvmlFriendlyObject(d)
    return obj

# pack the object so it can be passed to the NVML library
def nvmlFriendlyObjectToStruct(obj, model):
    for x in model._fields_:
        key = x[0]
        value = obj.__dict__[key]
        setattr(model, key, value)
    return model

## Unit structures
class struct_c_nvmlUnit_t(Structure):
    pass # opaque handle
c_nvmlUnit_t = POINTER(struct_c_nvmlUnit_t)
    
class c_nvmlUnitInfo_t(Structure):
    _fields_ = [
        ('name', c_char * 96),
        ('id', c_char * 96),
        ('serial', c_char * 96),
        ('firmwareVersion', c_char * 96),
    ]

class c_nvmlLedState_t(Structure):
    _fields_ = [
        ('cause', c_char * 256),
        ('color', _nvmlLedColor_t),
    ]

class c_nvmlPSUInfo_t(Structure):
    _fields_ = [
        ('state', c_char * 256),
        ('current', c_uint),
        ('voltage', c_uint),
        ('power', c_uint),
    ]

class c_nvmlUnitFanInfo_t(Structure):
    _fields_ = [
        ('speed', c_uint),
        ('state', _nvmlFanState_t),
    ]

class c_nvmlUnitFanSpeeds_t(Structure):
    _fields_ = [
        ('fans', c_nvmlUnitFanInfo_t * 24),
        ('count', c_uint)
    ]

## Device structures
class struct_c_nvmlDevice_t(Structure):
    pass # opaque handle
c_nvmlDevice_t = POINTER(struct_c_nvmlDevice_t)

class nvmlPciInfo_t(Structure):
    _fields_ = [
        ('busId', c_char * 16),
        ('domain', c_uint),
        ('bus', c_uint),
        ('device', c_uint),
        ('pciDeviceId', c_uint),
        
        # Added in 2.285
        ('pciSubSystemId', c_uint),
        ('reserved0', c_uint),
        ('reserved1', c_uint),
        ('reserved2', c_uint),
        ('reserved3', c_uint),
    ]

class c_nvmlMemory_t(Structure):
    _fields_ = [
        ('total', c_ulonglong),
        ('free', c_ulonglong),
        ('used', c_ulonglong),
    ]

# On Windows with the WDDM driver, usedGpuMemory is reported as None
# Code that processes this structure should check for None, I.E.
#
# if (info.usedGpuMemory == None):
#     # TODO handle the error
#     pass
# else:
#    print("Using %d MB of memory" % (info.usedGpuMemory / 1024 / 1024))
#
# See NVML documentation for more information
class c_nvmlProcessInfo_t(Structure):
    _fields_ = [
        ('pid', c_uint),
        ('usedGpuMemory', c_ulonglong),
    ]

class c_nvmlEccErrorCounts_t(Structure):
    _fields_ = [
        ('l1Cache', c_ulonglong),
        ('l2Cache', c_ulonglong),
        ('deviceMemory', c_ulonglong),
        ('registerFile', c_ulonglong),
    ]

class c_nvmlUtilization_t(Structure):
    _fields_ = [
        ('gpu', c_uint),
        ('memory', c_uint),
    ]

# Added in 2.285
class c_nvmlHwbcEntry_t(Structure):
    _fields_ = [
        ('hwbcId', c_uint),
        ('firmwareVersion', c_char * 32),
    ]

## Event structures
class struct_c_nvmlEventSet_t(Structure):
    pass # opaque handle
c_nvmlEventSet_t = POINTER(struct_c_nvmlEventSet_t)

nvmlEventTypeSingleBitEccError     = 0x0000000000000001
nvmlEventTypeDoubleBitEccError     = 0x0000000000000002
nvmlEventTypePState                = 0x0000000000000004     
nvmlEventTypeXidCriticalError      = 0x0000000000000008     
nvmlEventTypeNone                  = 0x0000000000000000  
nvmlEventTypeAll                   = (
                                        nvmlEventTypeNone |
                                        nvmlEventTypeSingleBitEccError |
                                        nvmlEventTypeDoubleBitEccError |
                                        nvmlEventTypePState |
                                        nvmlEventTypeXidCriticalError
                                     )

class c_nvmlEventData_t(Structure):
    _fields_ = [
        ('device', c_nvmlDevice_t),
        ('eventType', c_ulonglong),
        ('reserved', c_ulonglong)
    ]

## C function wrappers ##
def nvmlInit():
    global nvmlLib
    global libLoadLock
    
    #
    # Load the library if it isn't loaded already
    #
    if (nvmlLib == None):
        # lock to ensure only one caller loads the library
        libLoadLock.acquire()
        
        try:
            # ensure the library still isn't loaded
            if (nvmlLib == None):
                try:
                    if (sys.platform[:3] == "win"):
                        # cdecl calling convention
                        nvmlLib = cdll.nvml
                    else:
                        # assume linux
                        nvmlLib = CDLL("libnvidia-ml.so")
                except OSError as ose:
                    print(ose)
                    _nvmlCheckReturn(NVML_ERROR_DRIVER_NOT_LOADED)
                if (nvmlLib == None):
                    print("Failed to load NVML")
                    _nvmlCheckReturn(NVML_ERROR_DRIVER_NOT_LOADED)
        finally:
            # lock is always freed
            libLoadLock.release()
            
    #
    # Initialize the library
    #
    fn = _nvmlGetFunctionPointer("nvmlInit")
    ret = fn()
    _nvmlCheckReturn(ret)
    return None
    
def nvmlShutdown():
    #
    # Leave the library loaded, but shutdown the interface
    #
    fn = _nvmlGetFunctionPointer("nvmlShutdown")
    ret = fn()
    _nvmlCheckReturn(ret)
    return None

# Added in 2.285
def nvmlErrorString(result):
    fn = _nvmlGetFunctionPointer("nvmlErrorString")
    fn.restype = c_char_p # otherwise return is an int
    ret = fn(result)
    return ret

# Added in 2.285
def nvmlSystemGetNVMLVersion():
    c_version = create_string_buffer(NVML_SYSTEM_NVML_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlSystemGetNVMLVersion")
    ret = fn(c_version, c_uint(NVML_SYSTEM_NVML_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value

# Added in 2.285
def nvmlSystemGetProcessName(pid):
    c_name = create_string_buffer(1024)
    fn = _nvmlGetFunctionPointer("nvmlSystemGetProcessName")
    ret = fn(c_uint(pid), c_name, c_uint(1024))
    _nvmlCheckReturn(ret)
    return c_name.value

def nvmlSystemGetDriverVersion():
    c_version = create_string_buffer(NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlSystemGetDriverVersion")
    ret = fn(c_version, c_uint(NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value

# Added in 2.285
def nvmlSystemGetHicVersion():
    c_count = c_uint(0)
    hics = None
    fn = _nvmlGetFunctionPointer("nvmlSystemGetHicVersion")
    
    # get the count
    ret = fn(byref(c_count), None)
    
    # this should only fail with insufficient size
    if ((ret != NVML_SUCCESS) and
        (ret != NVML_ERROR_INSUFFICIENT_SIZE)):
        raise NVMLError(ret)
    
    # if there are no hics
    if (c_count.value == 0):
        return []
    
    hic_array = c_nvmlHwbcEntry_t * c_count.value
    hics = hic_array()
    ret = fn(byref(c_count), hics)
    _nvmlCheckReturn(ret)
    return hics

## Unit get functions
def nvmlUnitGetCount():
    c_count = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetCount")
    ret = fn(byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value

def nvmlUnitGetHandleByIndex(index):
    c_index = c_uint(index)
    unit = c_nvmlUnit_t()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetHandleByIndex")
    ret = fn(c_index, byref(unit))
    _nvmlCheckReturn(ret)
    return unit

def nvmlUnitGetUnitInfo(unit):
    c_info = c_nvmlUnitInfo_t()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetUnitInfo")
    ret = fn(unit, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info

def nvmlUnitGetLedState(unit):
    c_state =  c_nvmlLedState_t()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetLedState")
    ret = fn(unit, byref(c_state))
    _nvmlCheckReturn(ret)
    return c_state

def nvmlUnitGetPsuInfo(unit):
    c_info = c_nvmlPSUInfo_t()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetPsuInfo")
    ret = fn(unit, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info

def nvmlUnitGetTemperature(unit, type):
    c_temp = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetTemperature")
    ret = fn(unit, c_uint(type), byref(c_temp))
    _nvmlCheckReturn(ret)
    return c_temp.value

def nvmlUnitGetFanSpeedInfo(unit):
    c_speeds = c_nvmlUnitFanSpeeds_t()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetFanSpeedInfo")
    ret = fn(unit, byref(c_speeds))
    _nvmlCheckReturn(ret)
    return c_speeds
    
# added to API
def nvmlUnitGetDeviceCount(unit):
    c_count = c_uint(0)
    # query the unit to determine device count
    fn = _nvmlGetFunctionPointer("nvmlUnitGetDevices")
    ret = fn(unit, byref(c_count), None)
    if (ret == NVML_ERROR_INSUFFICIENT_SIZE):
        ret = NVML_ERROR_SUCCESS
    _nvmlCheckReturn(ret)
    return c_count.value

def nvmlUnitGetDevices(unit):
    c_count = c_uint(nvmlUnitGetDeviceCount(unit))
    device_array = c_nvmlDevice_t * c_count.value
    c_devices = device_array()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetDevices")
    ret = fn(unit, byref(c_count), c_devices)
    _nvmlCheckReturn(ret)
    return c_devices

## Device get functions
def nvmlDeviceGetCount():
    c_count = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCount")
    ret = fn(byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value

def nvmlDeviceGetHandleByIndex(index):
    c_index = c_uint(index)
    device = c_nvmlDevice_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByIndex")
    ret = fn(c_index, byref(device))
    _nvmlCheckReturn(ret)
    return device

def nvmlDeviceGetHandleBySerial(serial):
    c_serial = c_char_p(serial)
    device = c_nvmlDevice_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleBySerial")
    ret = fn(c_serial, byref(device))
    _nvmlCheckReturn(ret)
    return device

def nvmlDeviceGetHandleByUUID(uuid):
    c_uuid = c_char_p(uuid)
    device = c_nvmlDevice_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByUUID")
    ret = fn(c_uuid, byref(device))
    _nvmlCheckReturn(ret)
    return device
    
def nvmlDeviceGetHandleByPciBusId(pciBusId):
    c_busId = c_char_p(pciBusId)
    device = c_nvmlDevice_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByPciBusId")
    ret = fn(c_busId, byref(device))
    _nvmlCheckReturn(ret)
    return device

def nvmlDeviceGetName(handle):
    c_name = create_string_buffer(NVML_DEVICE_NAME_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetName")
    ret = fn(handle, c_name, c_uint(NVML_DEVICE_NAME_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_name.value
    
def nvmlDeviceGetSerial(handle):
    c_serial = create_string_buffer(NVML_DEVICE_SERIAL_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSerial")
    ret = fn(handle, c_serial, c_uint(NVML_DEVICE_SERIAL_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_serial.value
    
def nvmlDeviceGetUUID(handle):
    c_uuid = create_string_buffer(NVML_DEVICE_UUID_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetUUID")
    ret = fn(handle, c_uuid, c_uint(NVML_DEVICE_UUID_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_uuid.value
    
def nvmlDeviceGetInforomVersion(handle, infoRomObject):
    c_version = create_string_buffer(NVML_DEVICE_INFOROM_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetInforomVersion")
    ret = fn(handle, _nvmlInforomObject_t(infoRomObject),
	         c_version, c_uint(NVML_DEVICE_INFOROM_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value
    
def nvmlDeviceGetDisplayMode(handle):
    c_mode = _nvmlEnableState_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDisplayMode")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value
    
def nvmlDeviceGetPersistenceMode(handle):
    c_state = _nvmlEnableState_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPersistenceMode")
    ret = fn(handle, byref(c_state))
    _nvmlCheckReturn(ret)
    return c_state.value
    
def nvmlDeviceGetPciInfo(handle):
    c_info = nvmlPciInfo_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPciInfo_v2")
    ret = fn(handle, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info
    
def nvmlDeviceGetClockInfo(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetClockInfo")
    ret = fn(handle, _nvmlClockType_t(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value

# Added in 2.285
def nvmlDeviceGetMaxClockInfo(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMaxClockInfo")
    ret = fn(handle, _nvmlClockType_t(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value

def nvmlDeviceGetFanSpeed(handle):
    c_speed = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetFanSpeed")
    ret = fn(handle, byref(c_speed))
    _nvmlCheckReturn(ret)
    return c_speed.value
    
def nvmlDeviceGetTemperature(handle, sensor):
    c_temp = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTemperature")
    ret = fn(handle, _nvmlTemperatureSensors_t(sensor), byref(c_temp))
    _nvmlCheckReturn(ret)
    return c_temp.value

# DEPRECATED use nvmlDeviceGetPerformanceState
def nvmlDeviceGetPowerState(handle):
    c_pstate = _nvmlPstates_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerState")
    ret = fn(handle, byref(c_pstate))
    _nvmlCheckReturn(ret)
    return c_pstate.value
    
def nvmlDeviceGetPerformanceState(handle):
    c_pstate = _nvmlPstates_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPerformanceState")
    ret = fn(handle, byref(c_pstate))
    _nvmlCheckReturn(ret)
    return c_pstate.value

def nvmlDeviceGetPowerManagementMode(handle):
    c_pcapMode = _nvmlEnableState_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerManagementMode")
    ret = fn(handle, byref(c_pcapMode))
    _nvmlCheckReturn(ret)
    return c_pcapMode.value
    
def nvmlDeviceGetPowerManagementLimit(handle):
    c_limit = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerManagementLimit")
    ret = fn(handle, byref(c_limit))
    _nvmlCheckReturn(ret)
    return c_limit.value
    
def nvmlDeviceGetPowerUsage(handle):
    c_watts = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerUsage")
    ret = fn(handle, byref(c_watts))
    _nvmlCheckReturn(ret)
    return c_watts.value
    
def nvmlDeviceGetMemoryInfo(handle):
    c_memory = c_nvmlMemory_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMemoryInfo")
    ret = fn(handle, byref(c_memory))
    _nvmlCheckReturn(ret)
    return c_memory
    
def nvmlDeviceGetComputeMode(handle):
    c_mode = _nvmlComputeMode_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetComputeMode")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value
    
def nvmlDeviceGetEccMode(handle):
    c_currState = _nvmlEnableState_t()
    c_pendingState = _nvmlEnableState_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetEccMode")
    ret = fn(handle, byref(c_currState), byref(c_pendingState))
    _nvmlCheckReturn(ret)
    return [c_currState.value, c_pendingState.value]

# added to API
def nvmlDeviceGetCurrentEccMode(handle):
    return nvmlDeviceGetEccMode(handle)[0]

# added to API
def nvmlDeviceGetPendingEccMode(handle):
    return nvmlDeviceGetEccMode(handle)[1]

def nvmlDeviceGetTotalEccErrors(handle, bitType, counterType):
    c_count = c_ulonglong()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTotalEccErrors")
    ret = fn(handle, _nvmlEccBitType_t(bitType),
	         _nvmlEccCounterType_t(counterType), byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value

def nvmlDeviceGetDetailedEccErrors(handle, bitType, counterType):
    c_count = c_nvmlEccErrorCounts_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDetailedEccErrors")
    ret = fn(handle, _nvmlEccBitType_t(bitType),
	         _nvmlEccCounterType_t(counterType), byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count
    
def nvmlDeviceGetUtilizationRates(handle):
    c_util = c_nvmlUtilization_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetUtilizationRates")
    ret = fn(handle, byref(c_util))
    _nvmlCheckReturn(ret)
    return c_util

def nvmlDeviceGetDriverModel(handle):
    c_currModel = _nvmlDriverModel_t()
    c_pendingModel = _nvmlDriverModel_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDriverModel")
    ret = fn(handle, byref(c_currModel), byref(c_pendingModel))
    _nvmlCheckReturn(ret)
    return [c_currModel.value, c_pendingModel.value]

# added to API
def nvmlDeviceGetCurrentDriverModel(handle):
    return nvmlDeviceGetDriverModel(handle)[0]

# added to API
def nvmlDeviceGetPendingDriverModel(handle):
    return nvmlDeviceGetDriverModel(handle)[1]

# Added in 2.285
def nvmlDeviceGetVbiosVersion(handle):
    c_version = create_string_buffer(NVML_DEVICE_VBIOS_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetVbiosVersion")
    ret = fn(handle, c_version, c_uint(NVML_DEVICE_VBIOS_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value

# Added in 2.285
def nvmlDeviceGetComputeRunningProcesses(handle):
    # first call to get the size
    c_count = c_uint(0)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetComputeRunningProcesses")
    ret = fn(handle, byref(c_count), None)
    
    if (ret == NVML_SUCCESS):
        # special case, no running processes
        return []
    elif (ret == NVML_ERROR_INSUFFICIENT_SIZE):
        # typical case
        # oversize the array incase more processes are created
        c_count.value = c_count.value * 2 + 5
        proc_array = c_nvmlProcessInfo_t * c_count.value
        c_procs = proc_array()
        
        # make the call again
        ret = fn(handle, byref(c_count), c_procs)
        _nvmlCheckReturn(ret)
        
        procs = []
        for i in range(c_count.value):
            # use an alternative struct for this object
            obj = nvmlStructToFriendlyObject(c_procs[i])
            if (obj.usedGpuMemory == NVML_VALUE_NOT_AVAILABLE_ulonglong.value):
                # special case for WDDM on Windows, see comment above
                obj.usedGpuMemory = None
            procs.append(obj)

        return procs
    else:
        # error case
        raise NVMLError(ret)

## Set functions
def nvmlUnitSetLedState(unit, color):
    fn = _nvmlGetFunctionPointer("nvmlUnitSetLedState")
    ret = fn(unit, _nvmlLedColor_t(color))
    _nvmlCheckReturn(ret)
    return None
    
def nvmlDeviceSetPersistenceMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetPersistenceMode")
    ret = fn(handle, _nvmlEnableState_t(mode))
    _nvmlCheckReturn(ret)
    return None
    
def nvmlDeviceSetComputeMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetComputeMode")
    ret = fn(handle, _nvmlComputeMode_t(mode))
    _nvmlCheckReturn(ret)
    return None
    
def nvmlDeviceSetEccMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetEccMode")
    ret = fn(handle, _nvmlEnableState_t(mode))
    _nvmlCheckReturn(ret)
    return None

def nvmlDeviceClearEccErrorCounts(handle, counterType):
    fn = _nvmlGetFunctionPointer("nvmlDeviceClearEccErrorCounts")
    ret = fn(handle, _nvmlEccCounterType_t(counterType))
    _nvmlCheckReturn(ret)
    return None

def nvmlDeviceSetDriverModel(handle, model):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetDriverModel")
    ret = fn(handle, _nvmlDriverModel_t(model))
    _nvmlCheckReturn(ret)
    return None

# Added in 2.285
def nvmlEventSetCreate():
    fn = _nvmlGetFunctionPointer("nvmlEventSetCreate")
    eventSet = c_nvmlEventSet_t()
    ret = fn(byref(eventSet))
    _nvmlCheckReturn(ret)
    return eventSet

# Added in 2.285
def nvmlDeviceRegisterEvents(handle, eventTypes, eventSet):
    fn = _nvmlGetFunctionPointer("nvmlDeviceRegisterEvents")
    ret = fn(handle, c_ulonglong(eventTypes), eventSet)
    _nvmlCheckReturn(ret)
    return None

# Added in 2.285
def nvmlDeviceGetSupportedEventTypes(handle):
    c_eventTypes = c_ulonglong()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSupportedEventTypes")
    ret = fn(handle, byref(c_eventTypes))
    _nvmlCheckReturn(ret)
    return c_eventTypes.value

# Added in 2.285
# raises NVML_ERROR_TIMEOUT exception on timeout
def nvmlEventSetWait(eventSet, timeoutms):
    fn = _nvmlGetFunctionPointer("nvmlEventSetWait")
    data = c_nvmlEventData_t()
    ret = fn(eventSet, byref(data), c_uint(timeoutms))
    _nvmlCheckReturn(ret)
    return data

# Added in 2.285
def nvmlEventSetFree(eventSet):
    fn = _nvmlGetFunctionPointer("nvmlEventSetFree")
    ret = fn(eventSet)
    _nvmlCheckReturn(ret)
    return None

# Added in 2.285
def nvmlEventDataGetPerformanceState(data):
    fn = _nvmlGetFunctionPointer("nvmlEventDataGetPerformanceState")
    pstate = _nvmlPstates_t()
    ret = fn(byref(data), byref(pstate))
    _nvmlCheckReturn(ret)
    return pstate.value

# Added in 2.285
def nvmlEventDataGetXidCriticalError(data):
    fn = _nvmlGetFunctionPointer("nvmlEventDataGetXidCriticalError")
    xid = c_uint()
    ret = fn(byref(data), byref(xid))
    _nvmlCheckReturn(ret)
    return xid.value

# Added in 2.285
def nvmlEventDataGetEccErrorCount(data):
    fn = _nvmlGetFunctionPointer("nvmlEventDataGetEccErrorCount")
    ecc = c_ulonglong()
    ret = fn(byref(data), byref(ecc))
    _nvmlCheckReturn(ret)
    return ecc.value

# Added in 3.295
def nvmlDeviceOnSameBoard(handle1, handle2):
    fn = _nvmlGetFunctionPointer("nvmlDeviceOnSameBoard")
    onSameBoard = c_int()
    ret = fn(handle1, handle2, byref(onSameBoard))
    _nvmlCheckReturn(ret)
    return (onSameBoard.value != 0)

# Added in 3.295
def nvmlDeviceGetCurrPcieLinkGeneration(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCurrPcieLinkGeneration")
    gen = c_uint()
    ret = fn(handle, byref(gen))
    _nvmlCheckReturn(ret)
    return gen.value

# Added in 3.295
def nvmlDeviceGetMaxPcieLinkGeneration(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMaxPcieLinkGeneration")
    gen = c_uint()
    ret = fn(handle, byref(gen))
    _nvmlCheckReturn(ret)
    return gen.value

# Added in 3.295
def nvmlDeviceGetCurrPcieLinkWidth(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCurrPcieLinkWidth")
    width = c_uint()
    ret = fn(handle, byref(width))
    _nvmlCheckReturn(ret)
    return width.value

# Added in 3.295
def nvmlDeviceGetMaxPcieLinkWidth(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMaxPcieLinkWidth")
    width = c_uint()
    ret = fn(handle, byref(width))
    _nvmlCheckReturn(ret)
    return width.value




########NEW FILE########
__FILENAME__ = nvidia_smi
#####
# Copyright (c) 2011-2012, NVIDIA Corporation.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the NVIDIA Corporation nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF 
# THE POSSIBILITY OF SUCH DAMAGE.
#####

#
# nvidia_smi
# nvml_bindings <at> nvidia <dot> com
#
# Sample code that attempts to reproduce the output of nvidia-smi -q- x
# For many cases the output should match
#
# To Run:
# $ python
# Python 2.7 (r27:82500, Sep 16 2010, 18:02:00) 
# [GCC 4.5.1 20100907 (Red Hat 4.5.1-3)] on linux2
# Type "help", "copyright", "credits" or "license" for more information.
# >>> import nvidia_smi
# >>> print(nvidia_smi.XmlDeviceQuery())
# ...
#

from pynvml import *
import datetime

#
# Helper functions
#
def GetEccByType(handle, counterType, bitType):
    try:
        count = str(nvmlDeviceGetTotalEccErrors(handle, bitType, counterType))
    except NVMLError as err:
        count = handleError(err)
    
    try:
        detail = nvmlDeviceGetDetailedEccErrors(handle, bitType, counterType)
        deviceMemory = str(detail.deviceMemory)
        registerFile = str(detail.registerFile)
        l1Cache = str(detail.l1Cache)
        l2Cache = str(detail.l2Cache)
    except NVMLError as err:
        msg = handleError(err)
        deviceMemory = msg
        registerFile = msg
        l1Cache = msg
        l2Cache = msg
    strResult = ''
    strResult += '          <device_memory>' + deviceMemory + '</device_memory>\n'
    strResult += '          <register_file>' + registerFile + '</register_file>\n'
    strResult += '          <l1_cache>' + l1Cache + '</l1_cache>\n'
    strResult += '          <l2_cache>' + l2Cache + '</l2_cache>\n'
    strResult += '          <total>' + count + '</total>\n'
    return strResult

def GetEccByCounter(handle, counterType):
    strResult = ''
    strResult += '        <single_bit>\n'
    strResult += str(GetEccByType(handle, counterType, NVML_SINGLE_BIT_ECC))
    strResult += '        </single_bit>\n'
    strResult += '        <double_bit>\n'
    strResult += str(GetEccByType(handle, counterType, NVML_DOUBLE_BIT_ECC))
    strResult += '        </double_bit>\n'
    return strResult

def GetEccStr(handle):
    strResult = ''
    strResult += '      <volatile>\n'
    strResult += str(GetEccByCounter(handle, NVML_VOLATILE_ECC))
    strResult += '      </volatile>\n'
    strResult += '      <aggregate>\n'
    strResult += str(GetEccByCounter(handle, NVML_AGGREGATE_ECC))
    strResult += '      </aggregate>\n'
    return strResult

#
# Converts errors into string messages
#
def handleError(err):
    if (err.value == NVML_ERROR_NOT_SUPPORTED):
        return "N/A"
    else:
        return err.__str__()

#######
def XmlDeviceQuery():

    try:
        #
        # Initialize NVML
        #
        nvmlInit()
        strResult = ''

        strResult += '<?xml version="1.0" ?>\n'
        strResult += '<!DOCTYPE nvidia_smi_log SYSTEM "nvsmi_device.dtd">\n'
        strResult += '<nvidia_smi_log>\n'

        strResult += '  <timestamp>' + str(datetime.date.today()) + '</timestamp>\n'
        strResult += '  <driver_version>' + str(nvmlSystemGetDriverVersion()) + '</driver_version>\n'

        deviceCount = nvmlDeviceGetCount()
        strResult += '  <attached_gpus>' + str(deviceCount) + '</attached_gpus>\n'

        for i in range(0, deviceCount):
            handle = nvmlDeviceGetHandleByIndex(i)
            
            pciInfo = nvmlDeviceGetPciInfo(handle)    
            
            strResult += '  <gpu id="%s">\n' % pciInfo.busId
            
            strResult += '    <product_name>' + nvmlDeviceGetName(handle) + '</product_name>\n'
            
            try:
                state = ('Enabled' if (nvmlDeviceGetDisplayMode(handle) != 0) else 'Disabled')
            except NVMLError as err:
                state = handleError(err)
            
            strResult += '    <display_mode>' + state + '</display_mode>\n'

            try:
                mode = 'Enabled' if (nvmlDeviceGetPersistenceMode(handle) != 0) else 'Disabled'
            except NVMLError as err:
                mode = handleError(err)
            
            strResult += '    <persistence_mode>' + mode + '</persistence_mode>\n'
                
            strResult += '    <driver_model>\n'

            try:
                current = str(nvmlDeviceGetCurrentDriverModel(handle))
            except NVMLError as err:
                current = handleError(err)
            strResult += '      <current_dm>' + current + '</current_dm>\n'

            try:
                pending = str(nvmlDeviceGetPendingDriverModel(handle))
            except NVMLError as err:
                pending = handleError(err)

            strResult += '      <pending_dm>' + pending + '</pending_dm>\n'

            strResult += '    </driver_model>\n'

            try:
                serial = nvmlDeviceGetSerial(handle)
            except NVMLError as err:
                serial = handleError(err)

            strResult += '    <serial>' + serial + '</serial>\n'

            try:
                uuid = nvmlDeviceGetUUID(handle)
            except NVMLError as err:
                uuid = handleError(err)

            strResult += '    <uuid>' + uuid + '</uuid>\n'
            
            try:
                vbios = nvmlDeviceGetVbiosVersion(handle)
            except NVMLError as err:
                vbios = handleError(err)

            strResult += '    <vbios_version>' + vbios + '</vbios_version>\n'

            strResult += '    <inforom_version>\n'
            
            try:
                oem = nvmlDeviceGetInforomVersion(handle, NVML_INFOROM_OEM)
                if oem == '':
                    oem = 'N/A'
            except NVMLError as err:
                oem = handleError(err)
                
            strResult += '      <oem_object>' + oem + '</oem_object>\n'
            
            try:
                ecc = nvmlDeviceGetInforomVersion(handle, NVML_INFOROM_ECC)
                if ecc == '':
                    ecc = 'N/A'
            except NVMLError as err:
                ecc = handleError(err)
            
            strResult += '      <ecc_object>' + ecc + '</ecc_object>\n'
            try:
                pwr = nvmlDeviceGetInforomVersion(handle, NVML_INFOROM_POWER)
                if pwr == '':
                    pwr = 'N/A'
            except NVMLError as err:
                pwr = handleError(err)
            
            strResult += '      <pwr_object>' + pwr + '</pwr_object>\n'
            strResult += '    </inforom_version>\n'

            strResult += '    <pci>\n'
            strResult += '      <pci_bus>%02X</pci_bus>\n' % pciInfo.bus
            strResult += '      <pci_device>%02X</pci_device>\n' % pciInfo.device
            strResult += '      <pci_domain>%04X</pci_domain>\n' % pciInfo.domain
            strResult += '      <pci_device_id>%08X</pci_device_id>\n' % (pciInfo.pciDeviceId)
            strResult += '      <pci_sub_system_id>%08X</pci_sub_system_id>\n' % (pciInfo.pciSubSystemId)
            strResult += '      <pci_bus_id>' + str(pciInfo.busId) + '</pci_bus_id>\n'
            strResult += '      <pci_gpu_link_info>\n'


            strResult += '        <pcie_gen>\n'

            try:
                gen = str(nvmlDeviceGetMaxPcieLinkGeneration(handle))
            except NVMLError as err:
                gen = handleError(err)

            strResult += '          <max_link_gen>' + gen + '</max_link_gen>\n'

            try:
                gen = str(nvmlDeviceGetCurrPcieLinkGeneration(handle))
            except NVMLError as err:
                gen = handleError(err)

            strResult += '          <current_link_gen>' + gen + '</current_link_gen>\n'
            strResult += '        </pcie_gen>\n'
            strResult += '        <link_widths>\n'

            try:
                width = str(nvmlDeviceGetMaxPcieLinkWidth(handle)) + 'x'
            except NVMLError as err:
                width = handleError(err)

            strResult += '          <max_link_width>' + width + '</max_link_width>\n'

            try:
                width = str(nvmlDeviceGetCurrPcieLinkWidth(handle)) + 'x'
            except NVMLError as err:
                width = handleError(err)

            strResult += '          <current_link_width>' + width + '</current_link_width>\n'

            strResult += '        </link_widths>\n'
            strResult += '      </pci_gpu_link_info>\n'
            strResult += '    </pci>\n'

            try:
                fan = str(nvmlDeviceGetFanSpeed(handle)) + ' %'
            except NVMLError as err:
                fan = handleError(err)
            strResult += '    <fan_speed>' + fan + '</fan_speed>\n'

            try:
                memInfo = nvmlDeviceGetMemoryInfo(handle)
                mem_total = str(memInfo.total / 1024 / 1024) + ' MB'
                mem_used = str(memInfo.used / 1024 / 1024) + ' MB'
                mem_free = str(memInfo.free / 1024 / 1024) + ' MB'
            except NVMLError as err:
                error = handleError(err)
                mem_total = error
                mem_used = error
                mem_free = error

            strResult += '    <memory_usage>\n'
            strResult += '      <total>' + mem_total + '</total>\n'
            strResult += '      <used>' + mem_used + '</used>\n'
            strResult += '      <free>' + mem_free + '</free>\n'
            strResult += '    </memory_usage>\n'

            
            try:
                mode = nvmlDeviceGetComputeMode(handle)
                if mode == NVML_COMPUTEMODE_DEFAULT:
                    modeStr = 'Default'
                elif mode == NVML_COMPUTEMODE_EXCLUSIVE_THREAD:
                    modeStr = 'Exclusive Thread'
                elif mode == NVML_COMPUTEMODE_PROHIBITED:
                    modeStr = 'Prohibited'
                elif mode == NVML_COMPUTEMODE_EXCLUSIVE_PROCESS:
                    modeStr = 'Exclusive Process'
                else:
                    modeStr = 'Unknown'
            except NVMLError as err:
                modeStr = handleError(err)

            strResult += '    <compute_mode>' + modeStr + '</compute_mode>\n'

            try:
                util = nvmlDeviceGetUtilizationRates(handle)
                gpu_util = str(util.gpu)
                mem_util = str(util.memory)
            except NVMLError as err:
                error = handleError(err)
                gpu_util = error
                mem_util = error
            
            strResult += '    <utilization>\n'
            strResult += '      <gpu_util>' + gpu_util + ' %</gpu_util>\n'
            strResult += '      <memory_util>' + mem_util + ' %</memory_util>\n'
            strResult += '    </utilization>\n'
            
            try:
                (current, pending) = nvmlDeviceGetEccMode(handle)
                curr_str = 'Enabled' if (current != 0) else 'Disabled'
                pend_str = 'Enabled' if (pending != 0) else 'Disabled'
            except NVMLError as err:
                error = handleError(err)
                curr_str = error
                pend_str = error

            strResult += '    <ecc_mode>\n'
            strResult += '      <current_ecc>' + curr_str + '</current_ecc>\n'
            strResult += '      <pending_ecc>' + pend_str + '</pending_ecc>\n'
            strResult += '    </ecc_mode>\n'

            strResult += '    <ecc_errors>\n'
            strResult += GetEccStr(handle)
            strResult += '    </ecc_errors>\n'
            
            try:
                temp = str(nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)) + ' C'
            except NVMLError as err:
                temp = handleError(err)

            strResult += '    <temperature>\n'
            strResult += '      <gpu_temp>' + temp + '</gpu_temp>\n'
            strResult += '    </temperature>\n'

            strResult += '    <power_readings>\n'
            try:
                perfState = nvmlDeviceGetPowerState(handle)
            except NVMLError as err:
                perfState = handleError(err)
            strResult += '      <power_state>P%s</power_state>\n' % perfState
            try:
                powMan = nvmlDeviceGetPowerManagementMode(handle)
                powManStr = 'Supported' if powMan != 0 else 'N/A'
            except NVMLError as err:
                powManStr = handleError(err)
            strResult += '      <power_management>' + powManStr + '</power_management>\n'
            try:
                powDraw = (nvmlDeviceGetPowerUsage(handle) / 1000.0)
                powDrawStr = '%.2f W' % powDraw
            except NVMLError as err:
                powDrawStr = handleError(err)
            strResult += '      <power_draw>' + powDrawStr + '</power_draw>\n'
            try:
                powLimit = (nvmlDeviceGetPowerManagementLimit(handle) / 1000.0)
                powLimitStr = '%d W' % powLimit
            except NVMLError as err:
                powLimitStr = handleError(err)
            strResult += '      <power_limit>' + powLimitStr + '</power_limit>\n'
            strResult += '    </power_readings>\n'

            strResult += '    <clocks>\n'
            try:
                graphics = str(nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS))
            except NVMLError as err:
                graphics = handleError(err)
            strResult += '      <graphics_clock>' +graphics + ' MHz</graphics_clock>\n'
            try:
                sm = str(nvmlDeviceGetClockInfo(handle, NVML_CLOCK_SM))
            except NVMLError as err:
                sm = handleError(err)
            strResult += '      <sm_clock>' + sm + ' MHz</sm_clock>\n'
            try:
                mem = str(nvmlDeviceGetClockInfo(handle, NVML_CLOCK_MEM))
            except NVMLError as err:
                mem = handleError(err)
            strResult += '      <mem_clock>' + mem + ' MHz</mem_clock>\n'
            strResult += '    </clocks>\n'

            strResult += '    <max_clocks>\n'
            try:
                graphics = str(nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_GRAPHICS))
            except NVMLError as err:
                graphics = handleError(err)
            strResult += '      <graphics_clock>' + graphics + ' MHz</graphics_clock>\n'
            try:
                sm = str(nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_SM))
            except NVMLError as err:
                sm = handleError(err)
            strResult += '      <sm_clock>' + sm + ' MHz</sm_clock>\n'
            try:
                mem = str(nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_MEM))
            except NVMLError as err:
                mem = handleError(err)
            strResult += '      <mem_clock>' + mem + ' MHz</mem_clock>\n'
            strResult += '    </max_clocks>\n'
            
            try:
                perfState = nvmlDeviceGetPowerState(handle)
                perfStateStr = 'P%s' % perfState
            except NVMLError as err:
                perfStateStr = handleError(err)
            strResult += '    <performance_state>' + perfStateStr + '</performance_state>\n'
            
            strResult += '    <compute_processes>\n'
            
            procstr = ""
            try:
                procs = nvmlDeviceGetComputeRunningProcesses(handle)
            except NVMLError as err:
                procs = []
                procstr = handleError(err)
             
            for p in procs:
                procstr += '    <process_info>\n'
                procstr += '      <pid>%d</pid>\n' % p.pid
                try:
                    name = str(nvmlSystemGetProcessName(p.pid))
                except NVMLError as err:
                    if (err.value == NVML_ERROR_NOT_FOUND):
                        # probably went away
                        continue
                    else:
                        name = handleError(err)
                procstr += '      <process_name>' + name + '</process_name>\n'
                procstr += '      <used_memory>\n'
                if (p.usedGpuMemory == None):
                    procstr += 'N\A'
                else:
                    procstr += '%d MB\n' % (p.usedGpuMemory / 1024 / 1024)
                procstr += '</used_memory>\n'
                procstr += '    </process_info>\n'
            
            strResult += procstr
            strResult += '    </compute_processes>\n'
            strResult += '  </gpu>\n'
            
        strResult += '</nvidia_smi_log>\n'
        
    except NVMLError as err:
        strResult += 'nvidia_smi.py: ' + err.__str__() + '\n'
    
    nvmlShutdown()
    
    return strResult


########NEW FILE########
__FILENAME__ = pynvml
#####
# Copyright (c) 2011-2012, NVIDIA Corporation.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the NVIDIA Corporation nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF 
# THE POSSIBILITY OF SUCH DAMAGE.
#####

##
# Python bindings for the NVML library
##
from ctypes import *
from ctypes.util import find_library
import sys
import threading
    
## C Type mappings ##
## Enums
_nvmlEnableState_t = c_uint
NVML_FEATURE_DISABLED    = 0
NVML_FEATURE_ENABLED     = 1

_nvmlTemperatureSensors_t = c_uint
NVML_TEMPERATURE_GPU     = 0

_nvmlComputeMode_t = c_uint
NVML_COMPUTEMODE_DEFAULT           = 0
NVML_COMPUTEMODE_EXCLUSIVE_THREAD  = 1
NVML_COMPUTEMODE_PROHIBITED        = 2
NVML_COMPUTEMODE_EXCLUSIVE_PROCESS = 3

_nvmlEccBitType_t = c_uint
NVML_SINGLE_BIT_ECC    = 0
NVML_DOUBLE_BIT_ECC    = 1

_nvmlEccCounterType_t = c_uint
NVML_VOLATILE_ECC      = 0
NVML_AGGREGATE_ECC     = 1

_nvmlClockType_t = c_uint
NVML_CLOCK_GRAPHICS  = 0
NVML_CLOCK_SM        = 1
NVML_CLOCK_MEM       = 2

_nvmlDriverModel_t = c_uint
NVML_DRIVER_WDDM       = 0
NVML_DRIVER_WDM        = 1

_nvmlPstates_t = c_uint
NVML_PSTATE_0               = 0
NVML_PSTATE_1               = 1
NVML_PSTATE_2               = 2
NVML_PSTATE_3               = 3
NVML_PSTATE_4               = 4
NVML_PSTATE_5               = 5
NVML_PSTATE_6               = 6
NVML_PSTATE_7               = 7
NVML_PSTATE_8               = 8
NVML_PSTATE_9               = 9
NVML_PSTATE_10              = 10
NVML_PSTATE_11              = 11
NVML_PSTATE_12              = 12
NVML_PSTATE_13              = 13
NVML_PSTATE_14              = 14
NVML_PSTATE_15              = 15
NVML_PSTATE_UNKNOWN         = 32

_nvmlInforomObject_t = c_uint
NVML_INFOROM_OEM            = 0
NVML_INFOROM_ECC            = 1
NVML_INFOROM_POWER          = 2

_nvmlReturn_t = c_uint
NVML_SUCCESS                   = 0
NVML_ERROR_UNINITIALIZED       = 1
NVML_ERROR_INVALID_ARGUMENT    = 2
NVML_ERROR_NOT_SUPPORTED       = 3
NVML_ERROR_NO_PERMISSION       = 4
NVML_ERROR_ALREADY_INITIALIZED = 5
NVML_ERROR_NOT_FOUND           = 6
NVML_ERROR_INSUFFICIENT_SIZE   = 7
NVML_ERROR_INSUFFICIENT_POWER  = 8
NVML_ERROR_DRIVER_NOT_LOADED   = 9
NVML_ERROR_TIMEOUT             = 10,
NVML_ERROR_UNKNOWN             = 999

_nvmlFanState_t = c_uint
NVML_FAN_NORMAL             = 0
NVML_FAN_FAILED             = 1

_nvmlLedColor_t = c_uint
NVML_LED_COLOR_GREEN        = 0
NVML_LED_COLOR_AMBER        = 1

# C preprocessor defined values
nvmlFlagDefault             = 0
nvmlFlagForce               = 1

# buffer size
NVML_DEVICE_INFOROM_VERSION_BUFFER_SIZE      = 16
NVML_DEVICE_UUID_BUFFER_SIZE                 = 80
NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE       = 81
NVML_SYSTEM_NVML_VERSION_BUFFER_SIZE         = 80
NVML_DEVICE_NAME_BUFFER_SIZE                 = 64
NVML_DEVICE_SERIAL_BUFFER_SIZE               = 30
NVML_DEVICE_VBIOS_VERSION_BUFFER_SIZE        = 32

NVML_VALUE_NOT_AVAILABLE_ulonglong = c_ulonglong(-1)

## Lib loading ##
nvmlLib = None
libLoadLock = threading.Lock()

## Error Checking ##
class NVMLError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(nvmlErrorString(self.value))

def _nvmlCheckReturn(ret):
    if (ret != NVML_SUCCESS):
        raise NVMLError(ret)
    return ret

## Function access ##
def _nvmlGetFunctionPointer(name):
    global nvmlLib
    global libLoadLock
    
    libLoadLock.acquire()
    try:
        # ensure library was loaded
        if (nvmlLib == None):
            raise NVMLError(NVML_ERROR_UNINITIALIZED)
        try:
            return getattr(nvmlLib, name)
        except AttributeError as attrError:
            raise NVMLError(NVML_ERROR_NOT_SUPPORTED)
    finally:
        # lock is always freed
        libLoadLock.release()

## Alternative object
# Allows the object to be printed
# Allows mismatched types to be assigned
#  - like None when the Structure variant requires c_uint
class nvmlFriendlyObject(object):
    def __init__(self, dictionary):
        for x in dictionary:
            setattr(self, x, dictionary[x])
    def __str__(self):
        return self.__dict__.__str__()

def nvmlStructToFriendlyObject(struct):
    d = {}
    for x in struct._fields_:
        key = x[0]
        value = getattr(struct, key)
        d[key] = value
    obj = nvmlFriendlyObject(d)
    return obj

# pack the object so it can be passed to the NVML library
def nvmlFriendlyObjectToStruct(obj, model):
    for x in model._fields_:
        key = x[0]
        value = obj.__dict__[key]
        setattr(model, key, value)
    return model

## Unit structures
class struct_c_nvmlUnit_t(Structure):
    pass # opaque handle
c_nvmlUnit_t = POINTER(struct_c_nvmlUnit_t)
    
class c_nvmlUnitInfo_t(Structure):
    _fields_ = [
        ('name', c_char * 96),
        ('id', c_char * 96),
        ('serial', c_char * 96),
        ('firmwareVersion', c_char * 96),
    ]

class c_nvmlLedState_t(Structure):
    _fields_ = [
        ('cause', c_char * 256),
        ('color', _nvmlLedColor_t),
    ]

class c_nvmlPSUInfo_t(Structure):
    _fields_ = [
        ('state', c_char * 256),
        ('current', c_uint),
        ('voltage', c_uint),
        ('power', c_uint),
    ]

class c_nvmlUnitFanInfo_t(Structure):
    _fields_ = [
        ('speed', c_uint),
        ('state', _nvmlFanState_t),
    ]

class c_nvmlUnitFanSpeeds_t(Structure):
    _fields_ = [
        ('fans', c_nvmlUnitFanInfo_t * 24),
        ('count', c_uint)
    ]

## Device structures
class struct_c_nvmlDevice_t(Structure):
    pass # opaque handle
c_nvmlDevice_t = POINTER(struct_c_nvmlDevice_t)

class nvmlPciInfo_t(Structure):
    _fields_ = [
        ('busId', c_char * 16),
        ('domain', c_uint),
        ('bus', c_uint),
        ('device', c_uint),
        ('pciDeviceId', c_uint),
        
        # Added in 2.285
        ('pciSubSystemId', c_uint),
        ('reserved0', c_uint),
        ('reserved1', c_uint),
        ('reserved2', c_uint),
        ('reserved3', c_uint),
    ]

class c_nvmlMemory_t(Structure):
    _fields_ = [
        ('total', c_ulonglong),
        ('free', c_ulonglong),
        ('used', c_ulonglong),
    ]

# On Windows with the WDDM driver, usedGpuMemory is reported as None
# Code that processes this structure should check for None, I.E.
#
# if (info.usedGpuMemory == None):
#     # TODO handle the error
#     pass
# else:
#    print("Using %d MB of memory" % (info.usedGpuMemory / 1024 / 1024))
#
# See NVML documentation for more information
class c_nvmlProcessInfo_t(Structure):
    _fields_ = [
        ('pid', c_uint),
        ('usedGpuMemory', c_ulonglong),
    ]

class c_nvmlEccErrorCounts_t(Structure):
    _fields_ = [
        ('l1Cache', c_ulonglong),
        ('l2Cache', c_ulonglong),
        ('deviceMemory', c_ulonglong),
        ('registerFile', c_ulonglong),
    ]

class c_nvmlUtilization_t(Structure):
    _fields_ = [
        ('gpu', c_uint),
        ('memory', c_uint),
    ]

# Added in 2.285
class c_nvmlHwbcEntry_t(Structure):
    _fields_ = [
        ('hwbcId', c_uint),
        ('firmwareVersion', c_char * 32),
    ]

## Event structures
class struct_c_nvmlEventSet_t(Structure):
    pass # opaque handle
c_nvmlEventSet_t = POINTER(struct_c_nvmlEventSet_t)

nvmlEventTypeSingleBitEccError     = 0x0000000000000001
nvmlEventTypeDoubleBitEccError     = 0x0000000000000002
nvmlEventTypePState                = 0x0000000000000004     
nvmlEventTypeXidCriticalError      = 0x0000000000000008     
nvmlEventTypeNone                  = 0x0000000000000000  
nvmlEventTypeAll                   = (
                                        nvmlEventTypeNone |
                                        nvmlEventTypeSingleBitEccError |
                                        nvmlEventTypeDoubleBitEccError |
                                        nvmlEventTypePState |
                                        nvmlEventTypeXidCriticalError
                                     )

class c_nvmlEventData_t(Structure):
    _fields_ = [
        ('device', c_nvmlDevice_t),
        ('eventType', c_ulonglong),
        ('reserved', c_ulonglong)
    ]

## C function wrappers ##
def nvmlInit():
    global nvmlLib
    global libLoadLock
    
    #
    # Load the library if it isn't loaded already
    #
    if (nvmlLib == None):
        # lock to ensure only one caller loads the library
        libLoadLock.acquire()
        
        try:
            # ensure the library still isn't loaded
            if (nvmlLib == None):
                try:
                    if (sys.platform[:3] == "win"):
                        # cdecl calling convention
                        nvmlLib = cdll.nvml
                    else:
                        # assume linux
                        nvmlLib = CDLL("libnvidia-ml.so")
                except OSError as ose:
                    print(ose)
                    _nvmlCheckReturn(NVML_ERROR_DRIVER_NOT_LOADED)
                if (nvmlLib == None):
                    print("Failed to load NVML")
                    _nvmlCheckReturn(NVML_ERROR_DRIVER_NOT_LOADED)
        finally:
            # lock is always freed
            libLoadLock.release()
            
    #
    # Initialize the library
    #
    fn = _nvmlGetFunctionPointer("nvmlInit")
    ret = fn()
    _nvmlCheckReturn(ret)
    return None
    
def nvmlShutdown():
    #
    # Leave the library loaded, but shutdown the interface
    #
    fn = _nvmlGetFunctionPointer("nvmlShutdown")
    ret = fn()
    _nvmlCheckReturn(ret)
    return None

# Added in 2.285
def nvmlErrorString(result):
    fn = _nvmlGetFunctionPointer("nvmlErrorString")
    fn.restype = c_char_p # otherwise return is an int
    ret = fn(result)
    return ret

# Added in 2.285
def nvmlSystemGetNVMLVersion():
    c_version = create_string_buffer(NVML_SYSTEM_NVML_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlSystemGetNVMLVersion")
    ret = fn(c_version, c_uint(NVML_SYSTEM_NVML_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value

# Added in 2.285
def nvmlSystemGetProcessName(pid):
    c_name = create_string_buffer(1024)
    fn = _nvmlGetFunctionPointer("nvmlSystemGetProcessName")
    ret = fn(c_uint(pid), c_name, c_uint(1024))
    _nvmlCheckReturn(ret)
    return c_name.value

def nvmlSystemGetDriverVersion():
    c_version = create_string_buffer(NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlSystemGetDriverVersion")
    ret = fn(c_version, c_uint(NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value

# Added in 2.285
def nvmlSystemGetHicVersion():
    c_count = c_uint(0)
    hics = None
    fn = _nvmlGetFunctionPointer("nvmlSystemGetHicVersion")
    
    # get the count
    ret = fn(byref(c_count), None)
    
    # this should only fail with insufficient size
    if ((ret != NVML_SUCCESS) and
        (ret != NVML_ERROR_INSUFFICIENT_SIZE)):
        raise NVMLError(ret)
    
    # if there are no hics
    if (c_count.value == 0):
        return []
    
    hic_array = c_nvmlHwbcEntry_t * c_count.value
    hics = hic_array()
    ret = fn(byref(c_count), hics)
    _nvmlCheckReturn(ret)
    return hics

## Unit get functions
def nvmlUnitGetCount():
    c_count = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetCount")
    ret = fn(byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value

def nvmlUnitGetHandleByIndex(index):
    c_index = c_uint(index)
    unit = c_nvmlUnit_t()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetHandleByIndex")
    ret = fn(c_index, byref(unit))
    _nvmlCheckReturn(ret)
    return unit

def nvmlUnitGetUnitInfo(unit):
    c_info = c_nvmlUnitInfo_t()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetUnitInfo")
    ret = fn(unit, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info

def nvmlUnitGetLedState(unit):
    c_state =  c_nvmlLedState_t()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetLedState")
    ret = fn(unit, byref(c_state))
    _nvmlCheckReturn(ret)
    return c_state

def nvmlUnitGetPsuInfo(unit):
    c_info = c_nvmlPSUInfo_t()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetPsuInfo")
    ret = fn(unit, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info

def nvmlUnitGetTemperature(unit, type):
    c_temp = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetTemperature")
    ret = fn(unit, c_uint(type), byref(c_temp))
    _nvmlCheckReturn(ret)
    return c_temp.value

def nvmlUnitGetFanSpeedInfo(unit):
    c_speeds = c_nvmlUnitFanSpeeds_t()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetFanSpeedInfo")
    ret = fn(unit, byref(c_speeds))
    _nvmlCheckReturn(ret)
    return c_speeds
    
# added to API
def nvmlUnitGetDeviceCount(unit):
    c_count = c_uint(0)
    # query the unit to determine device count
    fn = _nvmlGetFunctionPointer("nvmlUnitGetDevices")
    ret = fn(unit, byref(c_count), None)
    if (ret == NVML_ERROR_INSUFFICIENT_SIZE):
        ret = NVML_ERROR_SUCCESS
    _nvmlCheckReturn(ret)
    return c_count.value

def nvmlUnitGetDevices(unit):
    c_count = c_uint(nvmlUnitGetDeviceCount(unit))
    device_array = c_nvmlDevice_t * c_count.value
    c_devices = device_array()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetDevices")
    ret = fn(unit, byref(c_count), c_devices)
    _nvmlCheckReturn(ret)
    return c_devices

## Device get functions
def nvmlDeviceGetCount():
    c_count = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCount")
    ret = fn(byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value

def nvmlDeviceGetHandleByIndex(index):
    c_index = c_uint(index)
    device = c_nvmlDevice_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByIndex")
    ret = fn(c_index, byref(device))
    _nvmlCheckReturn(ret)
    return device

def nvmlDeviceGetHandleBySerial(serial):
    c_serial = c_char_p(serial)
    device = c_nvmlDevice_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleBySerial")
    ret = fn(c_serial, byref(device))
    _nvmlCheckReturn(ret)
    return device

def nvmlDeviceGetHandleByUUID(uuid):
    c_uuid = c_char_p(uuid)
    device = c_nvmlDevice_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByUUID")
    ret = fn(c_uuid, byref(device))
    _nvmlCheckReturn(ret)
    return device
    
def nvmlDeviceGetHandleByPciBusId(pciBusId):
    c_busId = c_char_p(pciBusId)
    device = c_nvmlDevice_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByPciBusId")
    ret = fn(c_busId, byref(device))
    _nvmlCheckReturn(ret)
    return device

def nvmlDeviceGetName(handle):
    c_name = create_string_buffer(NVML_DEVICE_NAME_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetName")
    ret = fn(handle, c_name, c_uint(NVML_DEVICE_NAME_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_name.value
    
def nvmlDeviceGetSerial(handle):
    c_serial = create_string_buffer(NVML_DEVICE_SERIAL_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSerial")
    ret = fn(handle, c_serial, c_uint(NVML_DEVICE_SERIAL_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_serial.value
    
def nvmlDeviceGetUUID(handle):
    c_uuid = create_string_buffer(NVML_DEVICE_UUID_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetUUID")
    ret = fn(handle, c_uuid, c_uint(NVML_DEVICE_UUID_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_uuid.value
    
def nvmlDeviceGetInforomVersion(handle, infoRomObject):
    c_version = create_string_buffer(NVML_DEVICE_INFOROM_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetInforomVersion")
    ret = fn(handle, _nvmlInforomObject_t(infoRomObject),
	         c_version, c_uint(NVML_DEVICE_INFOROM_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value
    
def nvmlDeviceGetDisplayMode(handle):
    c_mode = _nvmlEnableState_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDisplayMode")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value
    
def nvmlDeviceGetPersistenceMode(handle):
    c_state = _nvmlEnableState_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPersistenceMode")
    ret = fn(handle, byref(c_state))
    _nvmlCheckReturn(ret)
    return c_state.value
    
def nvmlDeviceGetPciInfo(handle):
    c_info = nvmlPciInfo_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPciInfo_v2")
    ret = fn(handle, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info
    
def nvmlDeviceGetClockInfo(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetClockInfo")
    ret = fn(handle, _nvmlClockType_t(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value

# Added in 2.285
def nvmlDeviceGetMaxClockInfo(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMaxClockInfo")
    ret = fn(handle, _nvmlClockType_t(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value

def nvmlDeviceGetFanSpeed(handle):
    c_speed = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetFanSpeed")
    ret = fn(handle, byref(c_speed))
    _nvmlCheckReturn(ret)
    return c_speed.value
    
def nvmlDeviceGetTemperature(handle, sensor):
    c_temp = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTemperature")
    ret = fn(handle, _nvmlTemperatureSensors_t(sensor), byref(c_temp))
    _nvmlCheckReturn(ret)
    return c_temp.value

# DEPRECATED use nvmlDeviceGetPerformanceState
def nvmlDeviceGetPowerState(handle):
    c_pstate = _nvmlPstates_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerState")
    ret = fn(handle, byref(c_pstate))
    _nvmlCheckReturn(ret)
    return c_pstate.value
    
def nvmlDeviceGetPerformanceState(handle):
    c_pstate = _nvmlPstates_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPerformanceState")
    ret = fn(handle, byref(c_pstate))
    _nvmlCheckReturn(ret)
    return c_pstate.value

def nvmlDeviceGetPowerManagementMode(handle):
    c_pcapMode = _nvmlEnableState_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerManagementMode")
    ret = fn(handle, byref(c_pcapMode))
    _nvmlCheckReturn(ret)
    return c_pcapMode.value
    
def nvmlDeviceGetPowerManagementLimit(handle):
    c_limit = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerManagementLimit")
    ret = fn(handle, byref(c_limit))
    _nvmlCheckReturn(ret)
    return c_limit.value
    
def nvmlDeviceGetPowerUsage(handle):
    c_watts = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerUsage")
    ret = fn(handle, byref(c_watts))
    _nvmlCheckReturn(ret)
    return c_watts.value
    
def nvmlDeviceGetMemoryInfo(handle):
    c_memory = c_nvmlMemory_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMemoryInfo")
    ret = fn(handle, byref(c_memory))
    _nvmlCheckReturn(ret)
    return c_memory
    
def nvmlDeviceGetComputeMode(handle):
    c_mode = _nvmlComputeMode_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetComputeMode")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value
    
def nvmlDeviceGetEccMode(handle):
    c_currState = _nvmlEnableState_t()
    c_pendingState = _nvmlEnableState_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetEccMode")
    ret = fn(handle, byref(c_currState), byref(c_pendingState))
    _nvmlCheckReturn(ret)
    return [c_currState.value, c_pendingState.value]

# added to API
def nvmlDeviceGetCurrentEccMode(handle):
    return nvmlDeviceGetEccMode(handle)[0]

# added to API
def nvmlDeviceGetPendingEccMode(handle):
    return nvmlDeviceGetEccMode(handle)[1]

def nvmlDeviceGetTotalEccErrors(handle, bitType, counterType):
    c_count = c_ulonglong()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTotalEccErrors")
    ret = fn(handle, _nvmlEccBitType_t(bitType),
	         _nvmlEccCounterType_t(counterType), byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value

def nvmlDeviceGetDetailedEccErrors(handle, bitType, counterType):
    c_count = c_nvmlEccErrorCounts_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDetailedEccErrors")
    ret = fn(handle, _nvmlEccBitType_t(bitType),
	         _nvmlEccCounterType_t(counterType), byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count
    
def nvmlDeviceGetUtilizationRates(handle):
    c_util = c_nvmlUtilization_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetUtilizationRates")
    ret = fn(handle, byref(c_util))
    _nvmlCheckReturn(ret)
    return c_util

def nvmlDeviceGetDriverModel(handle):
    c_currModel = _nvmlDriverModel_t()
    c_pendingModel = _nvmlDriverModel_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDriverModel")
    ret = fn(handle, byref(c_currModel), byref(c_pendingModel))
    _nvmlCheckReturn(ret)
    return [c_currModel.value, c_pendingModel.value]

# added to API
def nvmlDeviceGetCurrentDriverModel(handle):
    return nvmlDeviceGetDriverModel(handle)[0]

# added to API
def nvmlDeviceGetPendingDriverModel(handle):
    return nvmlDeviceGetDriverModel(handle)[1]

# Added in 2.285
def nvmlDeviceGetVbiosVersion(handle):
    c_version = create_string_buffer(NVML_DEVICE_VBIOS_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetVbiosVersion")
    ret = fn(handle, c_version, c_uint(NVML_DEVICE_VBIOS_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value

# Added in 2.285
def nvmlDeviceGetComputeRunningProcesses(handle):
    # first call to get the size
    c_count = c_uint(0)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetComputeRunningProcesses")
    ret = fn(handle, byref(c_count), None)
    
    if (ret == NVML_SUCCESS):
        # special case, no running processes
        return []
    elif (ret == NVML_ERROR_INSUFFICIENT_SIZE):
        # typical case
        # oversize the array incase more processes are created
        c_count.value = c_count.value * 2 + 5
        proc_array = c_nvmlProcessInfo_t * c_count.value
        c_procs = proc_array()
        
        # make the call again
        ret = fn(handle, byref(c_count), c_procs)
        _nvmlCheckReturn(ret)
        
        procs = []
        for i in range(c_count.value):
            # use an alternative struct for this object
            obj = nvmlStructToFriendlyObject(c_procs[i])
            if (obj.usedGpuMemory == NVML_VALUE_NOT_AVAILABLE_ulonglong.value):
                # special case for WDDM on Windows, see comment above
                obj.usedGpuMemory = None
            procs.append(obj)

        return procs
    else:
        # error case
        raise NVMLError(ret)

## Set functions
def nvmlUnitSetLedState(unit, color):
    fn = _nvmlGetFunctionPointer("nvmlUnitSetLedState")
    ret = fn(unit, _nvmlLedColor_t(color))
    _nvmlCheckReturn(ret)
    return None
    
def nvmlDeviceSetPersistenceMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetPersistenceMode")
    ret = fn(handle, _nvmlEnableState_t(mode))
    _nvmlCheckReturn(ret)
    return None
    
def nvmlDeviceSetComputeMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetComputeMode")
    ret = fn(handle, _nvmlComputeMode_t(mode))
    _nvmlCheckReturn(ret)
    return None
    
def nvmlDeviceSetEccMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetEccMode")
    ret = fn(handle, _nvmlEnableState_t(mode))
    _nvmlCheckReturn(ret)
    return None

def nvmlDeviceClearEccErrorCounts(handle, counterType):
    fn = _nvmlGetFunctionPointer("nvmlDeviceClearEccErrorCounts")
    ret = fn(handle, _nvmlEccCounterType_t(counterType))
    _nvmlCheckReturn(ret)
    return None

def nvmlDeviceSetDriverModel(handle, model):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetDriverModel")
    ret = fn(handle, _nvmlDriverModel_t(model))
    _nvmlCheckReturn(ret)
    return None

# Added in 2.285
def nvmlEventSetCreate():
    fn = _nvmlGetFunctionPointer("nvmlEventSetCreate")
    eventSet = c_nvmlEventSet_t()
    ret = fn(byref(eventSet))
    _nvmlCheckReturn(ret)
    return eventSet

# Added in 2.285
def nvmlDeviceRegisterEvents(handle, eventTypes, eventSet):
    fn = _nvmlGetFunctionPointer("nvmlDeviceRegisterEvents")
    ret = fn(handle, c_ulonglong(eventTypes), eventSet)
    _nvmlCheckReturn(ret)
    return None

# Added in 2.285
def nvmlDeviceGetSupportedEventTypes(handle):
    c_eventTypes = c_ulonglong()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSupportedEventTypes")
    ret = fn(handle, byref(c_eventTypes))
    _nvmlCheckReturn(ret)
    return c_eventTypes.value

# Added in 2.285
# raises NVML_ERROR_TIMEOUT exception on timeout
def nvmlEventSetWait(eventSet, timeoutms):
    fn = _nvmlGetFunctionPointer("nvmlEventSetWait")
    data = c_nvmlEventData_t()
    ret = fn(eventSet, byref(data), c_uint(timeoutms))
    _nvmlCheckReturn(ret)
    return data

# Added in 2.285
def nvmlEventSetFree(eventSet):
    fn = _nvmlGetFunctionPointer("nvmlEventSetFree")
    ret = fn(eventSet)
    _nvmlCheckReturn(ret)
    return None

# Added in 2.285
def nvmlEventDataGetPerformanceState(data):
    fn = _nvmlGetFunctionPointer("nvmlEventDataGetPerformanceState")
    pstate = _nvmlPstates_t()
    ret = fn(byref(data), byref(pstate))
    _nvmlCheckReturn(ret)
    return pstate.value

# Added in 2.285
def nvmlEventDataGetXidCriticalError(data):
    fn = _nvmlGetFunctionPointer("nvmlEventDataGetXidCriticalError")
    xid = c_uint()
    ret = fn(byref(data), byref(xid))
    _nvmlCheckReturn(ret)
    return xid.value

# Added in 2.285
def nvmlEventDataGetEccErrorCount(data):
    fn = _nvmlGetFunctionPointer("nvmlEventDataGetEccErrorCount")
    ecc = c_ulonglong()
    ret = fn(byref(data), byref(ecc))
    _nvmlCheckReturn(ret)
    return ecc.value

# Added in 3.295
def nvmlDeviceOnSameBoard(handle1, handle2):
    fn = _nvmlGetFunctionPointer("nvmlDeviceOnSameBoard")
    onSameBoard = c_int()
    ret = fn(handle1, handle2, byref(onSameBoard))
    _nvmlCheckReturn(ret)
    return (onSameBoard.value != 0)

# Added in 3.295
def nvmlDeviceGetCurrPcieLinkGeneration(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCurrPcieLinkGeneration")
    gen = c_uint()
    ret = fn(handle, byref(gen))
    _nvmlCheckReturn(ret)
    return gen.value

# Added in 3.295
def nvmlDeviceGetMaxPcieLinkGeneration(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMaxPcieLinkGeneration")
    gen = c_uint()
    ret = fn(handle, byref(gen))
    _nvmlCheckReturn(ret)
    return gen.value

# Added in 3.295
def nvmlDeviceGetCurrPcieLinkWidth(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCurrPcieLinkWidth")
    width = c_uint()
    ret = fn(handle, byref(width))
    _nvmlCheckReturn(ret)
    return width.value

# Added in 3.295
def nvmlDeviceGetMaxPcieLinkWidth(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMaxPcieLinkWidth")
    width = c_uint()
    ret = fn(handle, byref(width))
    _nvmlCheckReturn(ret)
    return width.value




########NEW FILE########
__FILENAME__ = nvidia
# NVIDIA GPU metric module using the Python bindings for NVML
#
# (C)opyright 2011, 2012 Bernard Li <bernard@vanhpc.org>
# All Rights Reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
from pynvml import *

descriptors = list()

'''Return the descriptor based on the name'''
def find_descriptor(name):
    for d in descriptors:
        if d['name'] == name:
            return d

'''Build descriptor from arguments and append it to the global descriptors list if call_back does not return with error'''
def build_descriptor(name, call_back, time_max, value_type, units, slope, format, description, groups):
    d = {'name': name,
        'call_back': call_back,
        'time_max': time_max,
        'value_type': value_type,
        'units': units,
        'slope': slope,
        'format': format,
        'description': description,
        'groups': groups,
        }

    try:
        call_back(name)
        descriptors.append(d)
    except NVMLError, err:
        print "Failed to build descriptor :", name, ":", str(err)
        pass

def get_gpu_num():
    return int(nvmlDeviceGetCount())

def gpu_num_handler(name):
    return get_gpu_num()

def gpu_driver_version_handler(name):
    return nvmlSystemGetDriverVersion()

def gpu_device_handler(name):
    d = find_descriptor(name)

    (gpu, metric) = name.split('_', 1)
    gpu_id = int(gpu.split('gpu')[1])
    gpu_device = nvmlDeviceGetHandleByIndex(gpu_id)

    if (metric == 'type'):
        return nvmlDeviceGetName(gpu_device)
    elif (metric == 'uuid'):
        return nvmlDeviceGetUUID(gpu_device)
    elif (metric == 'pci_id'):
        return nvmlDeviceGetPciInfo(gpu_device).pciDeviceId
    elif (metric == 'temp'):
        return nvmlDeviceGetTemperature(gpu_device, NVML_TEMPERATURE_GPU)
    elif (metric == 'mem_total'):
        return int(nvmlDeviceGetMemoryInfo(gpu_device).total/1024)
    elif (metric == 'mem_used'):
        return int(nvmlDeviceGetMemoryInfo(gpu_device).used/1024)
    elif (metric == 'util'):
        return nvmlDeviceGetUtilizationRates(gpu_device).gpu
    elif (metric == 'mem_util'):
        return nvmlDeviceGetUtilizationRates(gpu_device).memory
    elif (metric == 'fan'):
        return nvmlDeviceGetFanSpeed(gpu_device)
    elif (metric == 'ecc_mode'):
        try:
            ecc_mode = nvmlDeviceGetPendingEccMode(gpu_device)
            if (NVML_FEATURE_DISABLED == ecc_mode):
                return "OFF"
            elif (NVML_FEATURE_ENABLED == ecc_mode):
                return "ON"
            else:
                return "UNKNOWN"
        except NVMLError, nvmlError:
            if NVML_ERROR_NOT_SUPPORTED == nvmlError.value:
                return 'N/A'
    elif (metric == 'perf_state' or metric == 'performance_state'):
        state = nvmlDeviceGetPerformanceState(gpu_device)
        try:
            int(state)
            return "P%s" % state
        except ValueError:
            return state
    elif (metric == 'graphics_speed'):
        return nvmlDeviceGetClockInfo(gpu_device, NVML_CLOCK_GRAPHICS)
    elif (metric == 'sm_speed'):
        return nvmlDeviceGetClockInfo(gpu_device, NVML_CLOCK_SM)
    elif (metric == 'mem_speed'):
        return nvmlDeviceGetClockInfo(gpu_device, NVML_CLOCK_MEM)
    elif (metric == 'max_graphics_speed'):
        return nvmlDeviceGetMaxClockInfo(gpu_device, NVML_CLOCK_GRAPHICS)
    elif (metric == 'max_sm_speed'):
        return nvmlDeviceGetMaxClockInfo(gpu_device, NVML_CLOCK_SM)
    elif (metric == 'max_mem_speed'):
        return nvmlDeviceGetMaxClockInfo(gpu_device, NVML_CLOCK_MEM)
    elif (metric == 'power_usage'):
        return nvmlDeviceGetPowerUsage(gpu_device)
    elif (metric == 'serial'):
        return nvmlDeviceGetSerial(gpu_device)
    elif (metric == 'power_man_mode'):
        pow_man_mode = nvmlDeviceGetPowerManagementMode(gpu_device)
        if (NVML_FEATURE_DISABLED == pow_man_mode):
           return "OFF"
        elif (NVML_FEATURE_ENABLED == pow_man_mode):
           return "ON"
        else:
            return "UNKNOWN"
    elif (metric == 'power_man_limit'):
        return nvmlDeviceGetPowerManagementLimit(gpu_device)
    else:
        print "Handler for %s not implemented, please fix in gpu_device_handler()" % metric
        os._exit(1)

def metric_init(params):
    global descriptors

    try:
        nvmlInit()
    except NVMLError, err:
        print "Failed to initialize NVML:", str(err)
        print "Exiting..."
        os._exit(1)

    default_time_max = 90

    build_descriptor('gpu_num', gpu_num_handler, default_time_max, 'uint', 'GPUs', 'zero', '%u', 'Total number of GPUs', 'gpu')
    build_descriptor('gpu_driver', gpu_driver_version_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU Driver Version', 'gpu')
 
    for i in range(get_gpu_num()):
        build_descriptor('gpu%s_type' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Type' % i, 'gpu')
        build_descriptor('gpu%s_graphics_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s Graphics Speed' % i, 'gpu')
        build_descriptor('gpu%s_sm_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s SM Speed' % i, 'gpu')
        build_descriptor('gpu%s_mem_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s Memory Speed' % i, 'gpu')
        build_descriptor('gpu%s_max_graphics_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'zero', '%u', 'GPU%s Max Graphics Speed' % i, 'gpu')
        build_descriptor('gpu%s_max_sm_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'zero', '%u', 'GPU%s Max SM Speed' % i, 'gpu')
        build_descriptor('gpu%s_max_mem_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'zero', '%u', 'GPU%s Max Memory Speed' % i, 'gpu')
        build_descriptor('gpu%s_uuid' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s UUID' % i, 'gpu')
        build_descriptor('gpu%s_pci_id' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s PCI ID' % i, 'gpu')
        build_descriptor('gpu%s_temp' % i, gpu_device_handler, default_time_max, 'uint', 'C', 'both', '%u', 'Temperature of GPU %s' % i, 'gpu,temp')
        build_descriptor('gpu%s_mem_total' % i, gpu_device_handler, default_time_max, 'uint', 'KB', 'zero', '%u', 'GPU%s Total Memory' %i, 'gpu')
        build_descriptor('gpu%s_mem_used' % i, gpu_device_handler, default_time_max, 'uint', 'KB', 'both', '%u', 'GPU%s Used Memory' %i, 'gpu')
        build_descriptor('gpu%s_ecc_mode' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s ECC Mode' %i, 'gpu')
        build_descriptor('gpu%s_perf_state' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Performance State' %i, 'gpu')
        build_descriptor('gpu%s_util' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Utilization' %i, 'gpu')
        build_descriptor('gpu%s_mem_util' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Memory Utilization' %i, 'gpu')
        build_descriptor('gpu%s_fan' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Fan Speed' %i, 'gpu')
        build_descriptor('gpu%s_power_usage' % i, gpu_device_handler, default_time_max, 'uint', 'watts', 'both', '%u', 'GPU%s Power Usage' % i, 'gpu')

        # Added for version 2.285
        build_descriptor('gpu%s_max_graphics_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s Max Graphics Speed' % i, 'gpu')
        build_descriptor('gpu%s_max_sm_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s Max SM Speed' % i, 'gpu')
        build_descriptor('gpu%s_max_mem_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s Max Memory Speed' % i, 'gpu')
        build_descriptor('gpu%s_serial' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Serial' % i, 'gpu')
        build_descriptor('gpu%s_power_man_mode' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Power Management' % i, 'gpu')
        build_descriptor('gpu%s_power_man_limit' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Power Management Limit' % i, 'gpu')

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    try:
        nvmlShutdown()
    except NVMLError, err:
        print "Error shutting down NVML:", str(err)
        return 1

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init({})
    for d in descriptors:
        v = d['call_back'](d['name'])
        if d['value_type'] == 'uint':
            print 'value for %s is %u %s' % (d['name'], v, d['units'])
        elif d['value_type'] == 'float' or d['value_type'] == 'double':
            print 'value for %s is %f %s' % (d['name'], v, d['units'])
        elif d['value_type'] == 'string':
            print 'value for %s is %s %s' % (d['name'], v, d['units'])

########NEW FILE########
__FILENAME__ = httpd
###  This script reports httpd metrics to ganglia.
###
###  Notes:
###    The following mod_status variables only report average values
###    over the lifetime of the running process: CPULoad, ReqPerSec,
###    BytesPerSec, and BytesPerReq. This script checks the system
###    for child process average memory usage and ignores the other
###    averages.
###
###    This script makes use of the ExtendedStatus metrics from
###    mod_status. To use these values you must enable them with the
###    "extended" option.
###
###    This script also exposes the startup values for prefork
###    variables including: StartServers, MinSpareServers,
###    MaxSpareServers, ServerLimit, MaxClients, MaxRequestsPerChild.
###    To use these values you must enable them with the "prefork"
###    option.
###
###    TODO
###       * Update avg memory usage to use Linux /proc/[pid]/statm
###       * Add scoreboard metrics?
###
###  Changelog:
###    v1.0.1 - 2010-07-21
###       * Initial version
###
###    v1.1.0 - 2010-08-03
###       * Code cleanup
###       * Removed CPU utilization
###

###  Copyright Jamie Isaacs. 2010
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import urllib
import subprocess
import traceback

import sys, re
import logging

descriptors = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
logging.debug('starting up')

last_update = 0
last_update_server = 0
httpd_stats = {}
httpd_stats_last = {}
server_stats = {}

MAX_UPDATE_TIME = 15

#SCOREBOARD_KEY = ('_', 'S', 'R', 'W', 'K', 'D', 'C', 'L', 'G', 'I', '.')

def update_stats():
	logging.debug('updating stats')
	global last_update, httpd_stats, httpd_stats_last
	
	cur_time = time.time()

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True
	else:
		last_update = cur_time

	#####
	# Update Apache stats
	try:
		httpd_stats = {}
		logging.debug(' opening URL: ' + str(STATUS_URL))
		f = urllib.urlopen(STATUS_URL, None, 2)

		for line in f.readlines():
			diff = False
			if 'Total Accesses:' in line:
				key = 'hits'
				diff = True
			elif 'Total kBytes:' in line:
				key = 'sent_kbytes'
				diff = True
			elif 'Uptime:' in line:
				key = 'uptime'
			elif 'BusyWorkers:' in line:
				key = 'busy_workers'
			elif 'IdleWorkers:' in line:
				key = 'idle_workers'
			#elif 'Scoreboard:' in line:
			#	line = line.strip().split(': ')
			#	logging.debug('  scb: ' + str(line))
			#	if len(line) == 2:
			#		scb = line[1]
			#		# Iterate over each character in scb
			#		for c in scb:
			#			print(c)
			#	continue
			else:
				continue

			line = line.strip().split(': ')
			logging.debug('  line: ' + str(line))

			if len(line) == 2:
				val = int(line[1])

				if diff:
					# Do we have an old value to calculate the delta?
					if key in httpd_stats_last:
						httpd_stats[key] = val - httpd_stats_last[key]
					else:
						httpd_stats[key] = 0

					httpd_stats_last[key] = val
				else:
					httpd_stats[key] = val

		f.close()
	except:
		logging.warning('error refreshing stats')
		logging.warning(traceback.print_exc(file=sys.stdout))
		return False

	if not httpd_stats:
		logging.warning('error refreshing stats')
		return False

	#####
	# Update Mem Utilization (avg_worker_size)
	# only measure the children, not the parent Apache process
	try:
		logging.debug(' updating avg_worker_size')
		p = subprocess.Popen("ps -u" + APACHE_USER + " -o rss,args | awk '/" + APACHE_BIN + "/ {sum+=$1; ++n} END {printf(\"%d\", sum/n)}'", shell=True, stdout=subprocess.PIPE)
		out, err = p.communicate()
		logging.debug('  result: ' + out)

		httpd_stats['avg_worker_size'] = int(out)
	except:
		logging.warning('error refreshing stats (avg_worker_size)')
		return False

	logging.debug('success refreshing stats')
	logging.debug('httpd_stats: ' + str(httpd_stats))

	return True

def update_server_stats():
	logging.debug('updating server stats')
	global last_update_server, server_stats

	# If the uptime is still greater than the last checked uptime
	# This will ensure these prefork values are only updated on apache restart
	if last_update_server != 0 and httpd_stats['uptime'] >= last_update_server:
		logging.debug(' wait until server restarts')
		return True
	else:
		if httpd_stats:
			last_update_server = httpd_stats['uptime']
		else:
			# Stats have not been loaded
			last_update_server = 0

	#####
	# Update apache version
	logging.debug(' updating server_version')
	try:
		p = subprocess.Popen(APACHE_CTL + ' -v', shell=True, stdout=subprocess.PIPE)
		out, err = p.communicate()

		for line in out.split('\n'):
			if 'Server version:' in line:
				key = 'server_version'
			else:
				continue

			line = line.split(': ')
			logging.debug('  line: ' + str(line))

			if len(line) == 2:
				server_stats[key] = line[1]
	except:
		logging.warning('error refreshing stats (server_version)')
		return False

	if REPORT_PREFORK:
		#####
		# Update prefork values
		logging.debug(' updating prefork stats')

		# Load Apache config file
		f = open(APACHE_CONF, 'r')
		c = f.read()
		f.close()

		# Find the prefork section
		m = re.search('prefork\.c>(.*?)<', c, re.DOTALL)
		if m:
			prefork = m.group(1).strip()
		else:
			logging.warning('failed updating server stats: prefork')
			return False

		# Extract the values
		for line in prefork.split('\n'):
			if 'StartServers' in line:
				key = 'start_servers'
			elif 'MinSpareServers' in line:
				key = 'min_spare_servers'
			elif 'MaxSpareServers' in line:
				key = 'max_spare_servers'
			elif 'ServerLimit' in line:
				key = 'server_limit'
			elif 'MaxClients' in line:
				key = 'max_clients'
			elif 'MaxRequestsPerChild' in line:
				key = 'max_requests_per_child'
			else:
				continue

			line = line.split()
			logging.debug('  line: ' + str(line))

			if len(line) == 2:
				server_stats[key] = int(line[1])


	logging.debug('success refreshing server stats')
	logging.debug('server_stats: ' + str(server_stats))

	return True

def get_stat(name):
	logging.debug('getting stat: ' + name)

	ret = update_stats()

	if ret:
		if name.startswith('httpd_'):
			label = name[6:]
		else:
			label = name

		try:
			return httpd_stats[label]
		except:
			logging.warning('failed to fetch ' + name)
			return 0
	else:
		return 0

def get_server_stat(name):
	logging.debug('getting server stat: ' + name)

	ret = update_server_stats()

	if ret:
		if name.startswith('httpd_'):
			label = name[6:]
		else:
			label = name

		try:
			return server_stats[label]
		except:
			logging.warning('failed to fetch: ' + name)
			return 0
	else:
		return 0

def metric_init(params):
	global descriptors

	global STATUS_URL, APACHE_CONF, APACHE_CTL, APACHE_BIN, APACHE_USER
	global REPORT_EXTENDED, REPORT_PREFORK

	STATUS_URL	= params.get('status_url')
	APACHE_CONF	= params.get('apache_conf')
	APACHE_CTL	= params.get('apache_ctl').replace('/','\/')
	APACHE_BIN	= params.get('apache_bin').replace('/','\/')
	APACHE_USER	= params.get('apache_user')
	REPORT_EXTENDED = str(params.get('get_extended', True)) == 'True'
	REPORT_PREFORK	 = str(params.get('get_prefork', True)) == 'True'

	logging.debug('init: ' + str(params))

	time_max = 60

	descriptions = dict(
		server_version = {
			'call_back': get_server_stat,
			'value_type': 'string',
			'units': '',
			'description': 'Apache version number'},

		busy_workers = {
			'units': 'workers',
			'description': 'Busy Workers'},

		idle_workers = {
			'units': 'workers',
			'description': 'Idle Workers'},

		avg_worker_size = {
			'units': 'KB',
			'description': 'Average Worker Size'},
	)

	if REPORT_EXTENDED:
		descriptions['hits'] = {
				'units': 'req',
				'description': 'The number of requests that clinets have sent to the server'}

		descriptions['sent_kbytes'] = {
				'units': 'KB',
				'description': 'The number of Kbytes sent to all clients'}

		descriptions['uptime'] = {
				'units': 'sec',
				'description': 'The number of seconds that the Apache server has been up'}

	if REPORT_PREFORK:
		descriptions['start_servers'] = {
				'call_back': get_server_stat,
				'units': 'processes',
				'slope': 'zero',
				'description': 'The number of child server processes created at startup'}

		descriptions['min_spare_servers'] = {
				'call_back': get_server_stat,
				'units': 'processes',
				'slope': 'zero',
				'description': 'The minimum number of idle child server processes'}

		descriptions['spare_servers'] = {
				'call_back': get_server_stat,
				'units': 'processes',
				'slope': 'zero',
				'description': 'The maximum number of idle child server processes'}

		descriptions['server_limit'] = {
				'call_back': get_server_stat,
				'units': 'processes',
				'slope': 'zero',
				'description': 'The upper limit on configurable number of processes'}

		descriptions['max_clients'] = {
				'call_back': get_server_stat,
				'units': 'connections',
				'slope': 'zero',
				'description': 'The maximum number of connections that will be processed simultaneously'}

		descriptions['max_requests_per_child'] = {
				'call_back': get_server_stat,
				'time_max': time_max,
				'units': 'requests',
				'slope': 'zero',
				'description': 'The maximum number of requests that an individual child server will handle during its life'}

	update_stats()
	update_server_stats()

	for label in descriptions:
		if httpd_stats.has_key(label):
			d = {
				'name': 'httpd_' + label,
				'call_back': get_stat,
				'time_max': time_max,
				'value_type': 'uint',
				'units': '',
				'slope': 'both',
				'format': '%u',
				'description': label,
				'groups': 'httpd'
			}

		elif server_stats.has_key(label):
			d = {
				'name': 'httpd_' + label,
				'call_back': get_server_stat,
				'time_max': time_max,
				'value_type': 'uint',
				'units': '',
				'slope': 'both',
				'format': '%u',
				'description': label,
				'groups': 'httpd'
			}

		else:
			logging.error("skipped " + label)
			continue

		# Apply metric customizations from descriptions
		d.update(descriptions[label])
		descriptors.append(d)

	#logging.debug('descriptors: ' + str(descriptors))

	return descriptors

def metric_cleanup():
	logging.shutdown()
	# pass

if __name__ == '__main__':
	from optparse import OptionParser
	import os

	logging.debug('running from cmd line')
	parser = OptionParser()
	parser.add_option('-U', '--URL', dest='status_url', default='http://localhost/server-status?auto', help='URL for Apache status page')
	parser.add_option('-a', '--apache-conf', dest='apache_conf', default='/etc/httpd/conf/httpd.conf', help='path to httpd.conf')
	parser.add_option('-t', '--apache-ctl', dest='apache_ctl', default='/usr/sbin/apachectl', help='path to apachectl')
	parser.add_option('-d', '--apache-bin', dest='apache_bin', default='/usr/sbin/httpd', help='path to httpd')
	parser.add_option('-u', '--apache-user', dest='apache_user', default='apache', help='username that runs httpd')        
	parser.add_option('-e', '--extended', dest='get_extended', action='store_true', default=False)
	parser.add_option('-p', '--prefork', dest='get_prefork', action='store_true', default=False)
	parser.add_option('-b', '--gmetric-bin', dest='gmetric_bin', default='/usr/bin/gmetric', help='path to gmetric binary')
	parser.add_option('-c', '--gmond-conf', dest='gmond_conf', default='/etc/ganglia/gmond.conf', help='path to gmond.conf')
	parser.add_option('-g', '--gmetric', dest='gmetric', action='store_true', default=False, help='submit via gmetric')
	parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)

	(options, args) = parser.parse_args()

	metric_init({
		'status_url': options.status_url,
		'apache_conf': options.apache_conf,
		'apache_ctl': options.apache_ctl,
		'apache_bin': options.apache_bin,
		'apache_user': options.apache_user,
		'get_extended': options.get_extended,
		'get_prefork': options.get_prefork
	})

	for d in descriptors:
		v = d['call_back'](d['name'])
		if not options.quiet:
			print ' %s: %s %s [%s]' % (d['name'], v, d['units'], d['description'])

		if options.gmetric:
			if d['value_type'] == 'uint':
				value_type = 'uint32'
			else:
				value_type = d['value_type']

			cmd = "%s --conf=%s --value='%s' --units='%s' --type='%s' --name='%s' --slope='%s'" % \
				(options.gmetric_bin, options.gmond_conf, v, d['units'], value_type, d['name'], d['slope'])
			os.system(cmd)


########NEW FILE########
__FILENAME__ = infobright
"""
The MIT License

Copyright (c) 2008 Gilad Raphaelli <gilad@raphaelli.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

###  Changelog:
###    v1.0.0 - 2012-05-18
###       * Brighthouse columnar database "Infobright" module, derived from mysqld module
###

###  Requires:
###       * yum install Infobright-python

###  Copyright Bob Webber, 2012
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import MySQLdb
import logging

descriptors = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/infobrightstats.log', filemode='w')
logging.debug('starting up')

last_update = 0
infobright_conn_opts = {}
infobright_stats = {}
infobright_stats_last = {}
delta_per_second = False

REPORT_BRIGHTHOUSE = True
REPORT_BRIGHTHOUSE_ENGINE = False
REPORT_MASTER = True
REPORT_SLAVE  = True

MAX_UPDATE_TIME = 15

def update_stats(get_brighthouse=True, get_brighthouse_engine=True, get_master=True, get_slave=True):
	"""

	"""
	logging.debug('updating stats')
	global last_update
	global infobright_stats, infobright_stats_last

	cur_time = time.time()
	time_delta = cur_time - last_update
	if time_delta <= 0:
		#we went backward in time.
		logging.debug(" system clock set backwards, probably ntp")

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True
	else:
		last_update = cur_time

	logging.debug('refreshing stats')
	infobright_stats = {}

	# Get info from DB
	try:
		conn = MySQLdb.connect(**infobright_conn_opts)

		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SELECT GET_LOCK('gmetric-infobright', 0) as ok")
		lock_stat = cursor.fetchone()
		cursor.close()

		if lock_stat['ok'] == 0:
			return False

		# infobright variables have 'brighthouse_ib_' or 'brighthouse_ini_' prefix
		cursor = conn.cursor(MySQLdb.cursors.Cursor)
		cursor.execute("SHOW VARIABLES")
		#variables = dict(((k.lower(), v) for (k,v) in cursor))
		variables = {}
		for (k,v) in cursor:
			variables[k.lower()] = v
		cursor.close()

		# infobright status values have 'bh_gdc_' or 'bh_mm_' prefix
		cursor = conn.cursor(MySQLdb.cursors.Cursor)
		# cursor.execute("SHOW /*!50002 GLOBAL */ STATUS")
		cursor.execute("SHOW GLOBAL STATUS")
		#global_status = dict(((k.lower(), v) for (k,v) in cursor))
		global_status = {}
		for (k,v) in cursor:
			# print k, v
			global_status[k.lower()] = v
		cursor.close()

		# try not to fail ?
		# BRIGHTHOUSE ENGINE status variables are pretty obscure
		get_brighthouse_engine = get_brighthouse_engine and variables.has_key('brighthouse_ini_controlmessages')
		get_master = get_master and variables['log_bin'].lower() == 'on'

		if get_brighthouse_engine:
			logging.warn('get_brighthouse_engine status not implemented')
			
		master_logs = tuple
		if get_master:
			cursor = conn.cursor(MySQLdb.cursors.Cursor)
			cursor.execute("SHOW MASTER LOGS")
			master_logs = cursor.fetchall()
			cursor.close()

		slave_status = {}
		if get_slave:
			cursor = conn.cursor(MySQLdb.cursors.DictCursor)
			cursor.execute("SHOW SLAVE STATUS")
			res = cursor.fetchone()
			if res:
				for (k,v) in res.items():
					slave_status[k.lower()] = v
			else:
				get_slave = False
			cursor.close()

		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SELECT RELEASE_LOCK('gmetric-infobright') as ok")
		cursor.close()

		conn.close()
	except MySQLdb.OperationalError, (errno, errmsg):
		logging.error('error updating stats')
		logging.error(errmsg)
		return False

	# process variables
	# http://dev.infobright.com/doc/refman/5.0/en/server-system-variables.html
	infobright_stats['version'] = variables['version']
	infobright_stats['max_connections'] = variables['max_connections']
	infobright_stats['query_cache_size'] = variables['query_cache_size']

	# process mysql status
	# http://www.infobright.com/
	interesting_mysql_status_vars = (
		'aborted_clients',
		'aborted_connects',
		'binlog_cache_disk_use',
		'binlog_cache_use',
		'bytes_received',
		'bytes_sent',
		'com_delete',
		'com_delete_multi',
		'com_insert',
		'com_insert_select',
		'com_load',
		'com_replace',
		'com_replace_select',
		'com_select',
		'com_update',
		'com_update_multi',
		'connections',
		'created_tmp_disk_tables',
		'created_tmp_files',
		'created_tmp_tables',
		'key_reads',
		'key_read_requests',
		'key_writes',
		'key_write_requests',
		'max_used_connections',
		'open_files',
		'open_tables',
		'opened_tables',
		'qcache_free_blocks',
		'qcache_free_memory',
		'qcache_hits',
		'qcache_inserts',
		'qcache_lowmem_prunes',
		'qcache_not_cached',
		'qcache_queries_in_cache',
		'qcache_total_blocks',
		'questions',
		'select_full_join',
		'select_full_range_join',
		'select_range',
		'select_range_check',
		'select_scan',
		'slave_open_temp_tables',
		'slave_retried_transactions',
		'slow_launch_threads',
		'slow_queries',
		'sort_range',
		'sort_rows',
		'sort_scan',
		'table_locks_immediate',
		'table_locks_waited',
		'threads_cached',
		'threads_connected',
		'threads_created',
		'threads_running',
		'uptime',
	)

	non_delta_mysql_status_vars = (
		'max_used_connections',
		'open_files',
		'open_tables',
		'qcache_free_blocks',
		'qcache_free_memory',
		'qcache_total_blocks',
		'slave_open_temp_tables',
		'threads_cached',
		'threads_connected',
		'threads_running',
		'uptime'
	)
	
	interesting_brighthouse_status_vars = (
		'bh_gdc_false_wakeup',
		'bh_gdc_hits',
		'bh_gdc_load_errors',
		'bh_gdc_misses',
		'bh_gdc_pack_loads',
		'bh_gdc_prefetched',
		'bh_gdc_readwait',
		'bh_gdc_read_wait_in_progress',
		'bh_gdc_redecompress',
		'bh_gdc_released',
		'bh_gdc_released',
		'bh_mm_alloc_blocs',
		'bh_mm_alloc_objs',
		'bh_mm_alloc_pack_size',
		'bh_mm_alloc_packs',
		'bh_mm_alloc_size',
		'bh_mm_alloc_temp',
		'bh_mm_alloc_temp_size',
		'bh_mm_free_blocks',
		'bh_mm_free_pack_size',
		'bh_mm_free_packs',
		'bh_mm_free_size',
		'bh_mm_free_temp',
		'bh_mm_free_temp_size',
		'bh_mm_freeable',
		'bh_mm_release1',
		'bh_mm_release2',
		'bh_mm_release3',
		'bh_mm_release4',
		'bh_mm_reloaded',
		'bh_mm_scale',
		'bh_mm_unfreeable',
		'bh_readbytes',
		'bh_readcount',
		'bh_writebytes',
		'bh_writecount',
	)
	
	non_delta_brighthouse_status_vars = (
		'bh_gdc_read_wait_in_progress',
		'bh_mm_alloc_size',
		'bh_mm_alloc_temp_size',
		'bh_mm_free_pack_size',
		'bh_mm_scale',
	)

	# don't put all of global_status in infobright_stats b/c it's so big
	all_interesting_status_vars = interesting_mysql_status_vars + interesting_brighthouse_status_vars
	all_non_delta_status_vars = non_delta_mysql_status_vars + non_delta_brighthouse_status_vars
	for key in all_interesting_status_vars:
		if key in all_non_delta_status_vars:
			infobright_stats[key] = global_status[key]
		else:
			# Calculate deltas for counters
			if time_delta <= 0:
				#systemclock was set backwards, not updating values.. to smooth over the graphs
				pass
			elif key in infobright_stats_last:
				if delta_per_second:
					infobright_stats[key] = (int(global_status[key]) - int(infobright_stats_last[key])) / time_delta
				else:
					infobright_stats[key] = int(global_status[key]) - int(infobright_stats_last[key])
			else:
				infobright_stats[key] = float(0)
			infobright_stats_last[key] = global_status[key]

	infobright_stats['open_files_used'] = int(global_status['open_files']) / int(variables['open_files_limit'])

	# process master logs
	if get_master:
		infobright_stats['binlog_count'] = len(master_logs)
		infobright_stats['binlog_space_current'] = master_logs[-1][1]
		#infobright_stats['binlog_space_total'] = sum((long(s[1]) for s in master_logs))
		infobright_stats['binlog_space_total'] = 0
		for s in master_logs:
			infobright_stats['binlog_space_total'] += int(s[1])
		infobright_stats['binlog_space_used'] = float(master_logs[-1][1]) / float(variables['max_binlog_size']) * 100

	# process slave status
	if get_slave:
		infobright_stats['slave_exec_master_log_pos'] = slave_status['exec_master_log_pos']
		#infobright_stats['slave_io'] = 1 if slave_status['slave_io_running'].lower() == "yes" else 0
		if slave_status['slave_io_running'].lower() == "yes":
			infobright_stats['slave_io'] = 1
		else:
			infobright_stats['slave_io'] = 0
		#infobright_stats['slave_sql'] = 1 if slave_status['slave_sql_running'].lower() =="yes" else 0
		if slave_status['slave_sql_running'].lower() == "yes":
			infobright_stats['slave_sql'] = 1
		else:
			infobright_stats['slave_sql'] = 0
		infobright_stats['slave_lag'] = slave_status['seconds_behind_master']
		infobright_stats['slave_relay_log_pos'] = slave_status['relay_log_pos']
		infobright_stats['slave_relay_log_space'] = slave_status['relay_log_space']


	logging.debug('success updating stats')
	logging.debug('infobright_stats: ' + str(infobright_stats))

def get_stat(name):
	logging.info("getting stat: %s" % name)
	global infobright_stats
	#logging.debug(infobright_stats)

	global REPORT_BRIGHTHOUSE
	global REPORT_BRIGHTHOUSE_ENGINE
	global REPORT_MASTER
	global REPORT_SLAVE

	ret = update_stats(REPORT_BRIGHTHOUSE, REPORT_BRIGHTHOUSE_ENGINE, REPORT_MASTER, REPORT_SLAVE)

	if ret:
		if name.startswith('infobright_'):
			# note that offset depends on length of "startswith"
			label = name[11:]
		else:
			label = name

		logging.debug("fetching %s" % name)
		try:
			return infobright_stats[label]
		except:
			logging.error("failed to fetch %s" % name)
			return 0
	else:
		return 0

def metric_init(params):
	global descriptors
	global infobright_conn_opts
	global infobright_stats
	global delta_per_second

	global REPORT_BRIGHTHOUSE
	global REPORT_BRIGHTHOUSE_ENGINE
	global REPORT_MASTER
	global REPORT_SLAVE

	REPORT_BRIGHTHOUSE = str(params.get('get_brighthouse', True)) == "True"
	REPORT_BRIGHTHOUSE_ENGINE = str(params.get('get_brighthouse_engine', True)) == "True"
	REPORT_MASTER = str(params.get('get_master', True)) == "True"
	REPORT_SLAVE  = str(params.get('get_slave', True)) == "True"

	logging.debug("init: " + str(params))

	infobright_conn_opts = dict(
		user = params.get('user'),
		passwd = params.get('passwd'),
		unix_socket = params.get('unix_socket', '/tmp/mysql-ib.sock'),
		connect_timeout = params.get('timeout', 30),
	)
	if params.get('host', '') != '':
		infobright_conn_opts['host'] = params.get('host')

	if params.get('port', 5029) != 5029:
		infobright_conn_opts['port'] = params.get('port')

	if params.get("delta_per_second", '') != '':
		delta_per_second = True

	mysql_stats_descriptions = {}
	master_stats_descriptions = {}
 	brighthouse_stats_descriptions = {}
	slave_stats_descriptions  = {}

	mysql_stats_descriptions = dict(
		aborted_clients = {
			'description': 'The number of connections that were aborted because the client died without closing the connection properly',
			'value_type': 'float',
			'units': 'clients',
		}, 

		aborted_connects = {
			'description': 'The number of failed attempts to connect to the Infobright server',
			'value_type': 'float',
			'units': 'conns',
		}, 

		binlog_cache_disk_use = {
			'description': 'The number of transactions that used the temporary binary log cache but that exceeded the value of binlog_cache_size and used a temporary file to store statements from the transaction',
			'value_type': 'float',
			'units': 'txns',
		}, 

		binlog_cache_use = {
			'description': ' The number of transactions that used the temporary binary log cache',
			'value_type': 'float',
			'units': 'txns',
		}, 

		bytes_received = {
			'description': 'The number of bytes received from all clients',
			'value_type': 'float',
			'units': 'bytes',
		}, 

		bytes_sent = {
			'description': ' The number of bytes sent to all clients',
			'value_type': 'float',
			'units': 'bytes',
		}, 

		com_delete = {
			'description': 'The number of DELETE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_delete_multi = {
			'description': 'The number of multi-table DELETE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_insert = {
			'description': 'The number of INSERT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_insert_select = {
			'description': 'The number of INSERT ... SELECT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_load = {
			'description': 'The number of LOAD statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_replace = {
			'description': 'The number of REPLACE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_replace_select = {
			'description': 'The number of REPLACE ... SELECT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_select = {
			'description': 'The number of SELECT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_update = {
			'description': 'The number of UPDATE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_update_multi = {
			'description': 'The number of multi-table UPDATE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		connections = {
			'description': 'The number of connection attempts (successful or not) to the Infobright server',
			'value_type': 'float',
			'units': 'conns',
		}, 

		created_tmp_disk_tables = {
			'description': 'The number of temporary tables on disk created automatically by the server while executing statements',
			'value_type': 'float',
			'units': 'tables',
		}, 

		created_tmp_files = {
			'description': 'The number of temporary files Infobrights mysqld has created',
			'value_type': 'float',
			'units': 'files',
		}, 

		created_tmp_tables = {
			'description': 'The number of in-memory temporary tables created automatically by the server while executing statement',
			'value_type': 'float',
			'units': 'tables',
		}, 

		#TODO in graphs: key_read_cache_miss_rate = key_reads / key_read_requests

		key_read_requests = {
			'description': 'The number of requests to read a key block from the cache',
			'value_type': 'float',
			'units': 'reqs',
		}, 

		key_reads = {
			'description': 'The number of physical reads of a key block from disk',
			'value_type': 'float',
			'units': 'reads',
		}, 

		key_write_requests = {
			'description': 'The number of requests to write a key block to the cache',
			'value_type': 'float',
			'units': 'reqs',
		}, 

		key_writes = {
			'description': 'The number of physical writes of a key block to disk',
			'value_type': 'float',
			'units': 'writes',
		}, 

		max_used_connections = {
			'description': 'The maximum number of connections that have been in use simultaneously since the server started',
			'units': 'conns',
			'slope': 'both',
		}, 

		open_files = {
			'description': 'The number of files that are open',
			'units': 'files',
			'slope': 'both',
		}, 

		open_tables = {
			'description': 'The number of tables that are open',
			'units': 'tables',
			'slope': 'both',
		}, 

		# If Opened_tables is big, your table_cache value is probably too small. 
		opened_tables = {
			'description': 'The number of tables that have been opened',
			'value_type': 'float',
			'units': 'tables',
		}, 

		qcache_free_blocks = {
			'description': 'The number of free memory blocks in the query cache',
			'units': 'blocks',
			'slope': 'both',
		}, 

		qcache_free_memory = {
			'description': 'The amount of free memory for the query cache',
			'units': 'bytes',
			'slope': 'both',
		}, 

		qcache_hits = {
			'description': 'The number of query cache hits',
			'value_type': 'float',
			'units': 'hits',
		}, 

		qcache_inserts = {
			'description': 'The number of queries added to the query cache',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_lowmem_prunes = {
			'description': 'The number of queries that were deleted from the query cache because of low memory',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_not_cached = {
			'description': 'The number of non-cached queries (not cacheable, or not cached due to the query_cache_type setting)',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_queries_in_cache = {
			'description': 'The number of queries registered in the query cache',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_total_blocks = {
			'description': 'The total number of blocks in the query cache',
			'units': 'blocks',
		}, 

		questions = {
			'description': 'The number of statements that clients have sent to the server',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		# If this value is not 0, you should carefully check the indexes of your tables.
		select_full_join = {
			'description': 'The number of joins that perform table scans because they do not use indexes',
			'value_type': 'float',
			'units': 'joins',
		}, 

		select_full_range_join = {
			'description': 'The number of joins that used a range search on a reference table',
			'value_type': 'float',
			'units': 'joins',
		}, 

		select_range = {
			'description': 'The number of joins that used ranges on the first table',
			'value_type': 'float',
			'units': 'joins',
		}, 

		# If this is not 0, you should carefully check the indexes of your tables.
		select_range_check = {
			'description': 'The number of joins without keys that check for key usage after each row',
			'value_type': 'float',
			'units': 'joins',
		}, 

		select_scan = {
			'description': 'The number of joins that did a full scan of the first table',
			'value_type': 'float',
			'units': 'joins',
		}, 

		slave_open_temp_tables = {
			'description': 'The number of temporary tables that the slave SQL thread currently has open',
			'value_type': 'float',
			'units': 'tables',
			'slope': 'both',
		}, 

		slave_retried_transactions = {
			'description': 'The total number of times since startup that the replication slave SQL thread has retried transactions',
			'value_type': 'float',
			'units': 'count',
		}, 

		slow_launch_threads = {
			'description': 'The number of threads that have taken more than slow_launch_time seconds to create',
			'value_type': 'float',
			'units': 'threads',
		}, 

		slow_queries = {
			'description': 'The number of queries that have taken more than long_query_time seconds',
			'value_type': 'float',
			'units': 'queries',
		}, 

		sort_range = {
			'description': 'The number of sorts that were done using ranges',
			'value_type': 'float',
			'units': 'sorts',
		}, 

		sort_rows = {
			'description': 'The number of sorted rows',
			'value_type': 'float',
			'units': 'rows',
		}, 

		sort_scan = {
			'description': 'The number of sorts that were done by scanning the table',
			'value_type': 'float',
			'units': 'sorts',
		}, 

		table_locks_immediate = {
			'description': 'The number of times that a request for a table lock could be granted immediately',
			'value_type': 'float',
			'units': 'count',
		}, 

		# If this is high and you have performance problems, you should first optimize your queries, and then either split your table or tables or use replication.
		table_locks_waited = {
			'description': 'The number of times that a request for a table lock could not be granted immediately and a wait was needed',
			'value_type': 'float',
			'units': 'count',
		}, 

		threads_cached = {
			'description': 'The number of threads in the thread cache',
			'units': 'threads',
			'slope': 'both',
		}, 

		threads_connected = {
			'description': 'The number of currently open connections',
			'units': 'threads',
			'slope': 'both',
		}, 

		#TODO in graphs: The cache miss rate can be calculated as Threads_created/Connections

		# Threads_created is big, you may want to increase the thread_cache_size value. 
		threads_created = {
			'description': 'The number of threads created to handle connections',
			'value_type': 'float',
			'units': 'threads',
		}, 

		threads_running = {
			'description': 'The number of threads that are not sleeping',
			'units': 'threads',
			'slope': 'both',
		}, 

		uptime = {
			'description': 'The number of seconds that the server has been up',
			'units': 'secs',
			'slope': 'both',
		}, 

		version = {
			'description': "Infobright uses MySQL Version",
			'value_type': 'string',
		    'format': '%s',
		},

		max_connections = {
			'description': "The maximum permitted number of simultaneous client connections",
			'slope': 'zero',
		},

		query_cache_size = {
			'description': "The amount of memory allocated for caching query results",
			'slope': 'zero',
		},
 	)
 	
 	brighthouse_stats_descriptions = dict(
 		bh_gdc_read_wait_in_progress = {
 			'description': "The number of current read waits in Brighthouse tables.",
 			'slope': 'zero',
 		},
 
		bh_mm_alloc_size = {
			'description': "The Brighthouse memory allocation size.",
			'slope': 'zero',
		},
		
		bh_mm_alloc_temp_size = {
			'description': "Brighthouse memory allocation temp size.",
			'slope': 'zero',
		},
		
		bh_mm_free_pack_size = {
			'description': "Brighthouse memory free pack size.",
			'slope': 'zero',
		},
		
		bh_mm_scale = {
			'description': "Brighthouse memory scale.",
			'slope': 'zero',
		},

		bh_gdc_false_wakeup = {
			'description': "BrightHouse gdc false wakeup",
			'value_type':'float',
			'units': 'fwkups',
			'slope': 'both',
		},
		bh_gdc_hits = {
			'description': "BrightHouse gdc hits",
			'value_type':'float',
			'units': 'hits',
			'slope': 'both',
		},
		bh_gdc_load_errors = {
			'description': "BrightHouse gdc load errors",
			'value_type':'float',
			'units': 'lderrs',
			'slope': 'both',
		},
		bh_gdc_misses = {
			'description': "BrightHouse gdc misses",
			'value_type':'float',
			'units': 'misses',
			'slope': 'both',
		},
		bh_gdc_pack_loads = {
			'description': "BrightHouse gdc pack loads",
			'value_type':'float',
			'units': 'pklds',
			'slope': 'both',
		},
		bh_gdc_prefetched  = {
			'description': "BrightHouse gdc prefetched",
			'value_type':'float',
			'units': 'prftchs',
			'slope': 'both',
		},
# 		bh_gdc_read_wait_in_progress = {
# 			'description': "BrightHouse gdc in read wait",
# 			'value_type':'uint',
# 			'units': 'inrdwt',
# 			'slope': 'both',
# 		},
		bh_gdc_readwait = {
			'description': "BrightHouse gdc read waits",
			'value_type':'float',
			'units': 'rdwts',
			'slope': 'both',
		},
		bh_gdc_redecompress = {
			'description': "BrightHouse gdc redecompress",
			'value_type':'float',
			'units': 'rdcmprs',
			'slope': 'both',
		},
		bh_gdc_released = {
			'description': "BrightHouse gdc released",
			'value_type':'float',
			'units': 'rlss',
			'slope': 'both',
		},
		bh_mm_alloc_blocs = {
			'description': "BrightHouse mm allocated blocks",
			'value_type':'float',
			'units': 'blocks',
			'slope': 'both',
		},
		bh_mm_alloc_objs = {
			'description': "BrightHouse mm allocated objects",
			'value_type':'float',
			'units': 'objs',
			'slope': 'both',
		},
		bh_mm_alloc_pack_size = {
			'description': "BrightHouse mm allocated pack size",
			'value_type':'float',
			'units': 'pksz',
			'slope': 'both',
		},
		bh_mm_alloc_packs = {
			'description': "BrightHouse mm allocated packs",
			'value_type':'float',
			'units': 'packs',
			'slope': 'both',
		},
		bh_mm_alloc_temp = {
			'description': "BrightHouse mm allocated temp",
			'value_type':'float',
			'units': 'temps',
			'slope': 'both',
		},
		bh_mm_free_blocks = {
			'description': "BrightHouse mm free blocks",
			'value_type':'float',
			'units': 'blocks',
			'slope': 'both',
		},
		bh_mm_free_packs = {
			'description': "BrightHouse mm free packs",
			'value_type':'float',
			'units': 'packs',
			'slope': 'both',
		},
		bh_mm_free_size = {
			'description': "BrightHouse mm free size",
			'value_type':'float',
			'units': 'szunits',
			'slope': 'both',
		},
		bh_mm_free_temp = {
			'description': "BrightHouse mm free temp",
			'value_type':'float',
			'units': 'tmps',
			'slope': 'both',
		},
		bh_mm_free_temp_size = {
			'description': "BrightHouse mm temp size",
			'value_type':'float',
			'units': 'tmpunits',
			'slope': 'both',
		},
		bh_mm_freeable = {
			'description': "BrightHouse mm freeable",
			'value_type':'float',
			'units': 'allocunits',
			'slope': 'both',
		},
		bh_mm_release1 = {
			'description': "BrightHouse mm release1",
			'value_type':'float',
			'units': 'relunits',
			'slope': 'both',
		},
		bh_mm_release2 = {
			'description': "BrightHouse mm release2",
			'value_type':'float',
			'units': 'relunits',
			'slope': 'both',
		},
		bh_mm_release3 = {
			'description': "BrightHouse mm release3",
			'value_type':'float',
			'units': 'relunits',
			'slope': 'both',
		},
		bh_mm_release4 = {
			'description': "BrightHouse mm release4",
			'value_type':'float',
			'units': 'relunits',
			'slope': 'both',
		},
		bh_mm_reloaded = {
			'description': "BrightHouse mm reloaded",
			'value_type':'float',
			'units': 'reloads',
			'slope': 'both',
		},
		bh_mm_unfreeable = {
			'description': "BrightHouse mm unfreeable",
			'value_type':'uint',
			'units': 'relunits',
			'slope': 'both',
		},
		bh_readbytes = {
			'description': "BrightHouse read bytes",
			'value_type':'uint',
			'units': 'bytes',
			'slope': 'both',
		},
		bh_readcount = {
			'description': "BrightHouse read count",
			'value_type':'uint',
			'units': 'reads',
			'slope': 'both',
		},
		bh_writebytes = {
			'description': "BrightHouse write bytes",
			'value_type':'uint',
			'units': 'bytes',
			'slope': 'both',
		},
		bh_writecount = {
			'description': "BrightHouse write count",
			'value_type':'uint',
			'units': 'writes',
			'slope': 'both',
		}
	)


	if REPORT_MASTER:
		master_stats_descriptions = dict(
			binlog_count = {
				'description': "Number of binary logs",
				'units': 'logs',
				'slope': 'both',
			},

			binlog_space_current = {
				'description': "Size of current binary log",
				'units': 'bytes',
				'slope': 'both',
			},

			binlog_space_total = {
				'description': "Total space used by binary logs",
				'units': 'bytes',
				'slope': 'both',
			},

			binlog_space_used = {
				'description': "Current binary log size / max_binlog_size",
				'value_type': 'float',
				'units': 'percent',
				'slope': 'both',
			},
		)

	if REPORT_SLAVE:
		slave_stats_descriptions = dict(
			slave_exec_master_log_pos = {
				'description': "The position of the last event executed by the SQL thread from the master's binary log",
				'units': 'bytes',
				'slope': 'both',
			},

			slave_io = {
				'description': "Whether the I/O thread is started and has connected successfully to the master",
				'value_type': 'uint8',
				'units': 'True/False',
				'slope': 'both',
			},

			slave_lag = {
				'description': "Replication Lag",
				'units': 'secs',
				'slope': 'both',
			},

			slave_relay_log_pos = {
				'description': "The position up to which the SQL thread has read and executed in the current relay log",
				'units': 'bytes',
				'slope': 'both',
			},

			slave_sql = {
				'description': "Slave SQL Running",
				'value_type': 'uint8',
				'units': 'True/False',
				'slope': 'both',
			},
		)
		
	update_stats(REPORT_BRIGHTHOUSE, REPORT_BRIGHTHOUSE_ENGINE, REPORT_MASTER, REPORT_SLAVE)

	time.sleep(MAX_UPDATE_TIME)

	update_stats(REPORT_BRIGHTHOUSE, REPORT_BRIGHTHOUSE_ENGINE, REPORT_MASTER, REPORT_SLAVE)

	for stats_descriptions in (brighthouse_stats_descriptions, master_stats_descriptions, mysql_stats_descriptions, slave_stats_descriptions):
		for label in stats_descriptions:
			if infobright_stats.has_key(label):
				format = '%u'
				if stats_descriptions[label].has_key('value_type'):
					if stats_descriptions[label]['value_type'] == "float":
						format = '%f'

				d = {
					'name': 'infobright_' + label,
					'call_back': get_stat,
					'time_max': 60,
					'value_type': "uint",
					'units': "",
					'slope': "both",
					'format': format,
					'description': "http://www.brighthouse.com",
					'groups': 'infobright',
				}

				d.update(stats_descriptions[label])

				descriptors.append(d)

			else:
				logging.error("skipped " + label)

	#logging.debug(str(descriptors))
	return descriptors

def metric_cleanup():
	logging.shutdown()
	# pass

if __name__ == '__main__':
	from optparse import OptionParser
	import os

	logging.debug('running from cmd line')
	parser = OptionParser()
	parser.add_option("-H", "--Host", dest="host", help="Host running Infobright", default="localhost")
	parser.add_option("-u", "--user", dest="user", help="user to connect as", default="")
	parser.add_option("-p", "--password", dest="passwd", help="password", default="")
	parser.add_option("-P", "--port", dest="port", help="port", default=3306, type="int")
	parser.add_option("-S", "--socket", dest="unix_socket", help="unix_socket", default="")
	parser.add_option("--no-brighthouse", dest="get_brighthouse", action="store_false", default=True)
	parser.add_option("--no-brighthouse-engine", dest="get_brighthouse_engine", action="store_false", default=False)
	parser.add_option("--no-master", dest="get_master", action="store_false", default=True)
	parser.add_option("--no-slave", dest="get_slave", action="store_false", default=True)
	parser.add_option("-b", "--gmetric-bin", dest="gmetric_bin", help="path to gmetric binary", default="/usr/bin/gmetric")
	parser.add_option("-c", "--gmond-conf", dest="gmond_conf", help="path to gmond.conf", default="/etc/ganglia/gmond.conf")
	parser.add_option("-g", "--gmetric", dest="gmetric", help="submit via gmetric", action="store_true", default=False)
	parser.add_option("-q", "--quiet", dest="quiet", action="store_true", default=False)

	(options, args) = parser.parse_args()

	metric_init({
		'host': options.host,
		'passwd': options.passwd,
		'user': options.user,
		'port': options.port,
		'get_brighthouse': options.get_brighthouse,
		'get_brighthouse_engine': options.get_brighthouse_engine,
		'get_master': options.get_master,
		'get_slave': options.get_slave,
		'unix_socket': options.unix_socket,
	})

	for d in descriptors:
		v = d['call_back'](d['name'])
		if not options.quiet:
			print ' %s: %s %s [%s]' % (d['name'], v, d['units'], d['description'])

		if options.gmetric:
			if d['value_type'] == 'uint':
				value_type = 'uint32'
			else:
				value_type = d['value_type']

			cmd = "%s --conf=%s --value='%s' --units='%s' --type='%s' --name='%s' --slope='%s'" % \
				(options.gmetric_bin, options.gmond_conf, v, d['units'], value_type, d['name'], d['slope'])
			os.system(cmd)


########NEW FILE########
__FILENAME__ = ipmi
import sys
import re
import time
import copy
import string
import subprocess

METRICS = {
    'time' : 0,
    'data' : {}
}

METRICS_CACHE_MAX = 5

stats_pos = {} 

def get_metrics():
    """Return all metrics"""

    global METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	new_metrics = {}
	units = {}

	command = [ params['timeout_bin'] , "3", params['ipmitool_bin'] , "-H", params['ipmi_ip'] , "-U" , params['username'] , '-P', params['password'] , 'sensor']	

        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE).communicate()[0][:-1]

        for i, v in enumerate(p.split("\n")):
            data = v.split("|")
            try:
                metric_name = data[0].strip().lower().replace("+", "").replace(" ", "_")
                value = data[1].strip()

                # Skip missing sensors
                if re.search("(0x)", value ) or value == 'na':
                    continue

                # Extract out a float value
                vmatch = re.search("([0-9.]+)", value)
                if not vmatch:
                    continue
                metric_value = float(vmatch.group(1))

                new_metrics[metric_name] = metric_value
                units[metric_name] = data[2].strip().replace("degrees C", "C")
		
            except ValueError:
                continue
            except IndexError:
                continue
		
	METRICS = {
            'time': time.time(),
            'data': new_metrics,
            'units': units
        }

    return [METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    try:

	metrics = get_metrics()[0]

	prefix_length = len(params['metric_prefix']) + 1
	name = name[prefix_length:] # remove prefix from name

	result = metrics['data'][name]

    except Exception:
        result = 0

    return result

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, metric_map, Desc_Skel

    descriptors = []

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_value,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.5f',
        'units'       : 'count/s',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'XXX',
        }

    metrics = get_metrics()[0]
    
    for item in metrics['data']:
	descriptors.append(create_desc(Desc_Skel, {
		"name"       	: params['metric_prefix'] + "_" + item,
		'groups'	: params['metric_prefix'],
		'units'		: metrics['units'][item]
		}))


    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    
    params = {
        "metric_prefix" : "ipmi",
	"ipmi_ip" : "10.1.2.3",
	"username"  : "ADMIN",
	"password"  : "secret"
	}
    descriptors = metric_init(params)

    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping 15 seconds'
        time.sleep(15)

########NEW FILE########
__FILENAME__ = jenkins
###  This script reports jenkins metrics to ganglia.

###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib2
import json
import base64

logging.basicConfig(level=logging.ERROR)

_Worker_Thread = None

class UpdateJenkinsThread(threading.Thread):

  def __init__(self, params):
    threading.Thread.__init__(self)
    self.running = False
    self.shuttingdown = False
    self.metrics = {}
    self.settings = {}
    self.refresh_rate = 60
    self.base_url = params['base_url']
    self.username = params['username']
    self.apitoken = params['apitoken']
    self._metrics_lock = threading.Lock()
    self._settings_lock = threading.Lock()

  def shutdown(self):
    self.shuttingdown = True
    if not self.running:
        return
    self.join()

  def run(self):
    global _Lock

    self.running = True

    while not self.shuttingdown:
        time.sleep(self.refresh_rate)
        self.refresh_metrics()

    self.running = False

  @staticmethod
  def _get_jenkins_statistics(url, username, apitoken):

    url += '/api/json'
    url += '?tree=jobs[color],overallLoad[busyExecutors[min[latest]],queueLength[min[latest]],totalExecutors[min[latest]]]'


    if username and apitoken:
      url += '&token=' + apitoken
      request = urllib2.Request(url)
      base64string = base64.encodestring('%s:%s' % (username, apitoken)).replace('\n','')
      request.add_header("Authorization", "Basic %s" % base64string)
      c = urllib2.urlopen(request, None, 2)
    else:
      c = urllib2.urlopen(url, None, 2)

    json_data = c.read()
    c.close()

    data = json.loads(json_data)

    result = {}
    result['jenkins_overallload_busy_executors'] = data['overallLoad']['busyExecutors']['min']['latest']
    result['jenkins_overallload_queue_length'] = data['overallLoad']['queueLength']['min']['latest']
    result['jenkins_overallload_total_executors'] = data['overallLoad']['totalExecutors']['min']['latest']
    result['jenkins_jobs_total'] = len(data['jobs'])
    result['jenkins_jobs_red'] = result['jenkins_jobs_yellow'] = result['jenkins_jobs_grey'] = result['jenkins_jobs_disabled'] = result['jenkins_jobs_aborted'] = result['jenkins_jobs_notbuilt'] = result['jenkins_jobs_blue'] = 0

    # Possible values: http://javadoc.jenkins-ci.org/hudson/model/BallColor.html
    colors = ['red', 'yellow', 'grey', 'disabled', 'aborted', 'notbuilt', 'blue']
    for color in colors:
      result['jenkins_jobs_' + color] = 0
    for job in data['jobs']:
      color = job['color']
      for c in colors:
        if color == c or color == c + '_anime':
          result['jenkins_jobs_' + c] += 1
    return result

  def refresh_metrics(self):
    logging.debug('refresh metrics')

    try:
      logging.debug(' opening URL: ' + str(self.base_url))
      data = UpdateJenkinsThread._get_jenkins_statistics(self.base_url, self.username, self.apitoken)
    except:
      logging.warning('error refreshing metrics')
      logging.warning(traceback.print_exc(file=sys.stdout))

    try:
      self._metrics_lock.acquire()
      self.metrics = {}
      for k, v in data.items():
          self.metrics[k] = v
    except:
      logging.warning('error refreshing metrics')
      logging.warning(traceback.print_exc(file=sys.stdout))
      return False

    finally:
      self._metrics_lock.release()

    if not self.metrics:
      logging.warning('error refreshing metrics')
      return False

    logging.debug('success refreshing metrics')
    logging.debug('metrics: ' + str(self.metrics))

    return True

  def metric_of(self, name):
    logging.debug('getting metric: ' + name)

    try:
      if name in self.metrics:
        try:
          self._metrics_lock.acquire()
          logging.debug('metric: %s = %s' % (name, self.metrics[name]))
          return self.metrics[name]
        finally:
          self._metrics_lock.release()
    except:
      logging.warning('failed to fetch ' + name)
      return 0

  def setting_of(self, name):
    logging.debug('getting setting: ' + name)

    try:
      if name in self.settings:
        try:
          self._settings_lock.acquire()
          logging.debug('setting: %s = %s' % (name, self.settings[name]))
          return self.settings[name]
        finally:
          self._settings_lock.release()
    except:
      logging.warning('failed to fetch ' + name)
      return 0

def metric_init(params):
  logging.debug('init: ' + str(params))
  global _Worker_Thread

  METRIC_DEFAULTS = {
    'units': 'jobs',
    'groups': 'jenkins',
    'slope': 'both',
    'value_type': 'uint',
    'format': '%d',
    'description': '',
    'call_back': metric_of
  }

  descriptions = dict(
    jenkins_overallload_busy_executors = {
      'value_type': 'float',
      'format': '%.3f',
      'units': 'executors',
      'description': 'Number of busy executors (master and slaves)'},
    jenkins_overallload_queue_length = {
      'value_type': 'float',
      'format': '%.3f',
      'units': 'queued items',
      'description': 'Length of the queue (master and slaves)'},
    jenkins_overallload_total_executors = {
      'value_type': 'float',
      'format': '%.3f',
      'units': 'executors',
      'description': 'Number of executors (master and slaves)'},
    jenkins_jobs_total = {
      'description': 'Total number of jobs'},
    jenkins_jobs_blue = {
      'description': 'Blue jobs'},
    jenkins_jobs_red = {
      'description': 'Red jobs'},
    jenkins_jobs_yellow = {
      'description': 'Yellow jobs'},
    jenkins_jobs_grey = {
      'description': 'Grey jobs'},
    jenkins_jobs_disabled = {
      'description': 'Disabled jobs'},
    jenkins_jobs_aborted = {
      'description': 'Aborted jobs'},
    jenkins_jobs_notbuilt = {
      'description': 'Not-built jobs'})

  if _Worker_Thread is not None:
    raise Exception('Worker thread already exists')

  _Worker_Thread = UpdateJenkinsThread(params)
  _Worker_Thread.refresh_metrics()
  _Worker_Thread.start()

  descriptors = []

  for name, desc in descriptions.iteritems():
    d = desc.copy()
    d['name'] = str(name)
    [ d.setdefault(key, METRIC_DEFAULTS[key]) for key in METRIC_DEFAULTS.iterkeys() ]
    descriptors.append(d)
  return descriptors

def metric_of(name):
  global _Worker_Thread
  return _Worker_Thread.metric_of(name)

def setting_of(name):
  global _Worker_Thread
  return _Worker_Thread.setting_of(name)

def metric_cleanup():
  global _Worker_Thread
  if _Worker_Thread is not None:
      _Worker_Thread.shutdown()
  logging.shutdown()
  pass

if __name__ == '__main__':
  from optparse import OptionParser

  try:
    logging.debug('running from the cmd line')
    parser = OptionParser()
    parser.add_option('-u', '--URL', dest='base_url', default='http://127.0.0.1:8080', help='Base-URL for jenkins api (default: http://127.0.0.1:8080)')
    parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
    parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False)
    parser.add_option('-n', '--username', dest='username', default='', help='Your Jenkins username (default: empty)')
    parser.add_option('-a', '--apitoken', dest='apitoken', default='', help='Your API token (default: empty)')

    (options, args) = parser.parse_args()

    descriptors = metric_init({
      'base_url': options.base_url,
      'username': options.username,
      'apitoken': options.apitoken,
    })

    if options.debug:
      from pprint import pprint
      pprint(descriptors)

    for d in descriptors:
      v = d['call_back'](d['name'])

      if not options.quiet:
        print ' {0}: {1} {2} [{3}]' . format(d['name'], v, d['units'], d['description'])

    os._exit(1)

  except KeyboardInterrupt:
    time.sleep(0.2)
    os._exit(1)
  except StandardError:
    traceback.print_exc()
    os._exit(1)
  finally:
    metric_cleanup()

########NEW FILE########
__FILENAME__ = jmxsh
###  This script reports jmx metrics to ganglia.
###
###  Notes:
###    This script exposes user defined MBeans to Ganglia. The
###    initial execution will attempt to determin value types based
###    on the returned values.
###
###  Changelog:
###    v0.0.1 - 2010-07-29
###      * Initial version
###
###    v1.0.1 - 2010-07-30
###      * Modified jmxsh to read from stdin
###      * Tested to work with gmond python module
###
###    v1.0.2 - 2010-08-05
###      * Added support for composite data
###
###    v1.0.3 - 2010-08-10
###      * Added support additional slope variable
###
###    v1.0.4 - 2010-08-10
###      * Removed slope variable
###      * Added delta/diff option
###        - diff will compute difference since last update
###        - delta wil compute difference per second since last update
###
###    v1.0.5 - 2010-08-11
###      * Fixed bug with value resets

###  Copyright Jamie Isaacs. 2010
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import subprocess
import traceback, sys, re
import tempfile
import logging

descriptors = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log2')
logging.debug('starting up')

last_update = 0
stats = {}
last_val = {}

METRICS = {}
COMP = {}
HOST = 'localhost'
PORT = '8887'
NAME = PORT
METRIC_GROUP = 'jmx'

MAX_UPDATE_TIME = 15
JMXSH = '/usr/share/java/jmxsh.jar'

def get_numeric(val):
	'''Try to return the numeric value of the string'''

	try:
		return float(val)
	except:
		pass

	return val

def get_gmond_format(val):
	'''Return the formatting and value_type values to use with gmond'''
	tp = type(val).__name__

	if tp == 'int':
		return ('uint', '%u')
	elif tp == 'float':
		return ('float', '%.4f')
	elif tp == 'string':
		return ('string', '%u')
	else:
		return ('string', '%u')

def update_stats():
	logging.debug('updating stats')
	global last_update, stats, last_val
	
	cur_time = time.time()

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True

	#####
	# Build jmxsh script into tmpfile
	sh  = '# jmxsh\njmx_connect -h ' + HOST + ' -p ' + PORT + '\n'
	for name,mbean in METRICS.items():
		sh += 'puts "' + name + ': [jmx_get -m ' + mbean + ']"\n'

	#logging.debug(sh)
	
	try:
		# run jmxsh.jar with the temp file as a script
		cmd = "java -jar " + JMXSH + " -q"
		p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = p.communicate(sh)
		#logging.debug('cmd: ' + cmd + '\nout: ' + out + '\nerr: ' + err + '\ncode: ' + str(p.returncode))

		if p.returncode:
			logging.warning('failed executing jmxsh\n' + cmd + '\n' + err)
			return False
	except:
		logging.warning('Error running jmx java\n' + traceback.print_exc(file=sys.stdout))
		return False

	try:
		# now parse out the values
		for line in out.strip().split('\n'):
			params = line.split(': ')
			name = params[0]
			val = params[1]

			if 'CompositeDataSupport' in val:
				# break up the composite data into separate values
				composite_contents = re.search('{(.*?)}', val, re.DOTALL)
				if composite_contents:
					for composite_vals in composite_contents.group(1).split(', '):
						_params = composite_vals.split('=')
						_name = name + '_' + _params[0]
						_val = _params[1]

						stats[_name] = get_numeric(_val)
				else:
					logging.warning('failed extracting composite values for ' + name)
					continue

				continue

			try:
				comp = COMP[name]
				if 'diff' in comp:
					val = int(val)
					if name in last_val:
						if val > last_val[name]:
							stats[name] = val - last_val[name]
						else:
							# value was reset since last update
							stats[name] = 0
					else:
						stats[name] = 0

					last_val[name] = val

				elif 'delta' in comp:
					val = float(val)
					interval = cur_time - last_update
					if name in last_val and interval > 0:
						if val > last_val[name]:
							stats[name] = (val - last_val[name]) / float(interval)
						else:
							# value was reset since last update
							stats[name] = 0.0
					else:
						stats[name] = 0.0

					last_val[name] = val

			except KeyError:
				stats[name] = get_numeric(val)

	except:
		logging.warning('Error parsing\n' + traceback.print_exc(file=sys.stdout))
		return False

	logging.debug('success refreshing stats')
	logging.debug('stats: ' + str(stats))
	logging.debug('last_val: ' + str(last_val))

	last_update = cur_time
	return True

def get_stat(name):
	logging.debug('getting stat: ' + name)

	ret = update_stats()

	if ret:
		first = 'jmx_' + NAME + '_'
		if name.startswith(first):
			label = name[len(first):]
		else:
			label = name

		try:
			return stats[label]
		except:
			logging.warning('failed to fetch ' + name)
			return 0
	else:
		return 0

def metric_init(params):
	global descriptors
	global METRICS,HOST,PORT,NAME,METRIC_GROUP

	logging.debug('init: ' + str(params))

	try:
		HOST = params.pop('host')
		PORT = params.pop('port')
		NAME = params.pop('name')
		METRIC_GROUP = params.pop('metric_group')
		
	except:
		logging.warning('Incorrect parameters')

	# Setup METRICS variable from parameters
	for name,mbean in params.items():
		val = mbean.split('##')
		METRICS[name] = val[0]

		# If optional delta/diff exists in value
		try:
			COMP[name] = val[1]
		except IndexError:
			pass

	update_stats()

	# dynamically build our descriptors based on the first run of update_stats()
	descriptions = dict()
	for name in stats:
		(value_type, format) = get_gmond_format(stats[name])
		descriptions[name] = {
			'value_type': value_type,
			'format': format
		}

	time_max = 60
	for label in descriptions:
		if stats.has_key(label):

			d = {
				'name': 'jmx_' + NAME + '_' + label,
				'call_back': get_stat,
				'time_max': time_max,
				'value_type': 'float',
				'units': '',
				'format': '%u',
				'slope': 'both',
				'description': label,
				'groups': METRIC_GROUP
			}

			# Apply metric customizations from descriptions
			d.update(descriptions[label])

			descriptors.append(d)

		else:
			logging.error("skipped " + label)

	#logging.debug('descriptors: ' + str(descriptors))

	return descriptors

def metric_cleanup():
	logging.shutdown()
	# pass

if __name__ == '__main__':
	from optparse import OptionParser
	import os

	logging.debug('running from cmd line')
	parser = OptionParser()
	parser.add_option('-p', '--param', dest='param', default='', help='module parameters')
	parser.add_option('-v', '--value', dest='value', default='', help='module values')
	parser.add_option('-b', '--gmetric-bin', dest='gmetric_bin', default='/usr/bin/gmetric', help='path to gmetric binary')
	parser.add_option('-c', '--gmond-conf', dest='gmond_conf', default='/etc/ganglia/gmond.conf', help='path to gmond.conf')
	parser.add_option('-g', '--gmetric', dest='gmetric', action='store_true', default=False, help='submit via gmetric')
	parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
	parser.add_option('-t', '--test', dest='test', action='store_true', default=False, help='test the regex list')

	(options, args) = parser.parse_args()

	_param = options.param.split(',')
	_val = options.value.split('|')

	params = {}
	i = 0
	for name in _param:
		params[name] = _val[i]
		i += 1
	
	metric_init(params)

	if options.test:
		print('')
		print(' waiting ' + str(MAX_UPDATE_TIME) + ' seconds')
		time.sleep(MAX_UPDATE_TIME)
		update_stats()

	for d in descriptors:
		v = d['call_back'](d['name'])
		if not options.quiet:
			print ' %s: %s %s [%s]' % (d['name'], d['format'] % v, d['units'], d['description'])

		if options.gmetric:
			if d['value_type'] == 'uint':
				value_type = 'uint32'
			else:
				value_type = d['value_type']

			cmd = "%s --conf=%s --value='%s' --units='%s' --type='%s' --name='%s' --slope='%s'" % \
				(options.gmetric_bin, options.gmond_conf, v, d['units'], value_type, d['name'], d['slope'])
			os.system(cmd)


########NEW FILE########
__FILENAME__ = kstats
#!/usr/bin/env python


import sys
import traceback
import os
import time
import socket
import select


descriptors = list()
PARAMS = {
    'host': '127.0.0.1',
    'port': 22133,
    'timeout': 2,
}
METRICS = {
    'time' : 0,
    'data' : {}
}
METRICS_CACHE_MAX = 5

def get_metrics():
    global METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        msg  = ''

        try:
            sock.connect((PARAMS['host'], int(PARAMS['port'])))
            sock.send('stats\r\n')

            while True:
                rfd, wfd, xfd = select.select([sock], [], [], PARAMS['timeout'])
                if not rfd:
                    print >>sys.stderr, 'ERROR: select timeout'
                    break

                for fd in rfd:
                    if fd == sock:
                        data = fd.recv(8192)
                        msg += data

                if msg.find('END') != -1:
                    break

            sock.close()
        except socket.error, e:
            print >>sys.stderr, 'ERROR: %s' % e

        _metrics = {}
        for m in msg.split('\r\n'):
            d = m.split(' ')
            if len(d) == 3 and d[0] == 'STAT':
                new_value = d[2]
                try:
                    new_value = int(d[2])
                except ValueError:
                    pass
                _metrics[PARAMS['metrix_prefix'] + '_' + d[1]] = new_value

        METRICS = {
            'time': time.time(),
            'data': _metrics
        }

    return METRICS

def metric_of(name):
    curr_metrics = get_metrics()
    if name in curr_metrics['data']:
        return curr_metrics['data'][name]
    return 0

def metric_init(lparams):
    global descriptors, PARAMS

    for key in lparams:
        PARAMS[key] = lparams[key]

    # initialize skeleton of descriptors
    skeleton = {
        'name': 'XXX',
        'call_back': metric_of,
        'time_max': 60,
        'value_type': 'uint',
        'format': '%u',
        'units': 'XXX',
        'slope': 'both', # zero|positive|negative|both
        'description': 'XXX',
        'groups': PARAMS['type'],
    }

    mp = PARAMS['metrix_prefix']
    queues = list()

    if 'queues' in PARAMS:
        queues = PARAMS['queues'].split(',')

    def create_desc(skel, prop):
        d = skel.copy()
        for k,v in prop.iteritems():
            d[k] = v
        return d

    def create_queue_descriptors(skeleton, mp, name):
        return [
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_items',
                'units': 'items',
                'description': 'current items'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_bytes',
                'units': 'bytes',
                'description': 'current bytes'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_total_items',
                'units': 'items',
                'slope': 'positive',
                'description': 'total items'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_logsize',
                'units': 'bytes',
                'description': 'size of journal file'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_expired_items',
                'units': 'items',
                'slope': 'positive',
                'description': 'total expired items'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_mem_items',
                'units': 'items',
                'description': 'current items in memory'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_mem_bytes',
                'units': 'bytes',
                'description': 'current size of items in memory'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_age',
                'units': 'milliseconds',
                'description': 'time last item was waiting'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_discarded',
                'units': 'items',
                'slope': 'positive',
                'description': 'total items discarded'
            }),
            create_desc(skeleton, {
                'name': mp + '_queue_' + name + '_waiters',
                'units': 'waiters',
                'description': 'total waiters'
            }),
        ]

    descriptors.append(create_desc(skeleton, {
        'name': mp + '_uptime',
        'units': 'seconds',
        'slope': 'positive',
        'description': 'current uptime',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_curr_items',
        'units': 'items',
        'description': 'current items stored',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_total_items',
        'units': 'items',
        'slope': 'positive',
        'description': 'total items stored',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_bytes',
        'units': 'bytes',
        'description': 'total bytes of all items waiting in queues',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_curr_connections',
        'units': 'connections',
        'description': 'current open connections',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_total_connections',
        'units': 'connections',
        'slow': 'positive',
        'description': 'total open connections',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_cmd_get',
        'units': 'commands',
        'slope': 'positive',
        'description': 'total get reqs',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_cmd_set',
        'units': 'commands',
        'slope': 'positive',
        'description': 'total set reqs',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_cmd_peek',
        'units': 'commands',
        'slope': 'positive',
        'description': 'total peek reqs',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_get_hits',
        'units': 'requests',
        'slope': 'positive',
        'description': 'total hits',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_get_misses',
        'units': 'requests',
        'slope': 'positive',
        'description': 'total misses',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_bytes_read',
        'units': 'bytes',
        'slope': 'positive',
        'description': 'total bytes read from clients',
    }))
    descriptors.append(create_desc(skeleton, {
        'name': mp + '_bytes_written',
        'units': 'bytes',
        'slope': 'positive',
        'description': 'total bytes written to clients',
    }))

    for queue in queues:
        for _qd in create_queue_descriptors(skeleton, mp, queue):
            descriptors.append(_qd)

    return descriptors

def metric_cleanup():
    pass

if __name__ == '__main__':
    try:
        params = {
            'host': '127.0.0.1',
            'port': 22133,
            'debug': True,
            'type': 'kestrel',
            'metrix_prefix': 'ks',
            'queues': 'my_queue01'
        }
        metric_init(params)

        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)
########NEW FILE########
__FILENAME__ = kumofs
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import traceback
import os
import threading
import time
import subprocess
import re

descriptors = list()
Desc_Skel   = {}
_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock
Debug = False

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "DEBUG: "+f % v

class UpdateMetricThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 20
        if "refresh_rate" in params:
            self.refresh_rate = int(params["refresh_rate"])
        self.metric       = {}
        self.timeout      = 2

        self.host         = "localhost"
        self.port         = 19800
        if "host" in params:
            self.host = params["host"]
        if "port" in params:
            self.port = params["port"]

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            self.update_metric()
            _Lock.release()
            time.sleep(self.refresh_rate)

        self.running = False

    def update_metric(self):
        cmd = ["kumostat", "%s:%s" % (self.host, self.port), "stats"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()

        for m in re.split('(?:\r\n|\n)',pout):
            dprint("%s",m)
            d = m.split(" ")
            if len(d) == 3 and d[0] == "STAT":
                self.metric["kumofs_"+d[1]] = int(d[2]) if d[2].isdigit() else d[2]

    def metric_of(self, name):
        val = 0
        if name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            _Lock.release()
        return val

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug

    print '[kumofs] kumofs protocol "stats"'
    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_of,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'format'      : '%d',
        'units'       : 'XXX',
        'slope'       : 'XXX', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'kumofs',
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 20
    if "debug" in params:
        Debug = params["debug"]
    dprint("%s", "Debug mode on")

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "kumofs_curr_items",
                "units"      : "items",
                "slope"      : "both",
                "description": "Current number of items stored",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "kumofs_cmd_get",
                "units"      : "commands",
                "slope"      : "positive",
                "description": "Cumulative number of retrieval reqs",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "kumofs_cmd_set",
                "units"      : "commands",
                "slope"      : "positive",
                "description": "Cumulative number of storage reqs",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "kumofs_cmd_delete",
                "units"      : "commands",
                "slope"      : "positive",
                "description": "Cumulative number of storage reqs",
                }))

    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_of(name):
    return _Worker_Thread.metric_of(name)

def metric_cleanup():
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    try:
        params = {
            "host"  : "s101",
            "port"  : 19800,
            "debug" : True,
            }
        metric_init(params)

  #       for d in descriptors:
  #           print '''  metric {
  #   name  = "%s"
  #   title = "%s"
  #   value_threshold = 0
  # }''' % (d["name"], d["description"])

        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)

########NEW FILE########
__FILENAME__ = memcached
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import traceback
import os
import threading
import time
import socket
import select

descriptors = list()
Desc_Skel   = {}
_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock
Debug = False

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "DEBUG: "+f % v

def floatable(str):
    try:
        float(str)
        return True
    except:
        return False

class UpdateMetricThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 15
        if "refresh_rate" in params:
            self.refresh_rate = int(params["refresh_rate"])
        self.metric       = {}
        self.last_metric       = {}
        self.timeout      = 2

        self.host         = "localhost"
        self.port         = 11211
        if "host" in params:
            self.host = params["host"]
        if "port" in params:
            self.port = int(params["port"])
        self.type    = params["type"]
        self.mp      = params["metrix_prefix"]

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        try:
            self.join()
        except:
            pass

    def run(self):
        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            self.update_metric()
            _Lock.release()
            time.sleep(self.refresh_rate)

        self.running = False

    def update_metric(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        msg  = ""
        self.last_metric = self.metric.copy()
        try:
            dprint("connect %s:%d", self.host, self.port)
            sock.connect((self.host, self.port))
            sock.send("stats\r\n")

            while True:
                rfd, wfd, xfd = select.select([sock], [], [], self.timeout)
                if not rfd:
                    print >>sys.stderr, "ERROR: select timeout"
                    break

                for fd in rfd:
                    if fd == sock:
                        data = fd.recv(8192)
                        msg += data

                if msg.find("END"):
                    break

            sock.close()
        except socket.error, e:
            print >>sys.stderr, "ERROR: %s" % e

        for m in msg.split("\r\n"):
            d = m.split(" ")
            if len(d) == 3 and d[0] == "STAT" and floatable(d[2]):
                self.metric[self.mp+"_"+d[1]] = float(d[2])

    def metric_of(self, name):
        val = 0
        mp = name.split("_")[0]
        if name.rsplit("_",1)[1] == "rate" and name.rsplit("_",1)[0] in self.metric:
            _Lock.acquire()
            name = name.rsplit("_",1)[0]
            if name in self.last_metric:
                num = self.metric[name]-self.last_metric[name]
                period = self.metric[mp+"_time"]-self.last_metric[mp+"_time"]
                try:
                    val = num/period
                except ZeroDivisionError:
                    val = 0
            _Lock.release()
        elif name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            _Lock.release()
        # Value should never be negative. If it is counters wrapper due to e.g. memcached restart
        if val < 0:
            val = 0
        return val

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug

    print '[memcached] memcached protocol "stats"'
    if "type" not in params:
        params["type"] = "memcached"

    if "metrix_prefix" not in params:
        if params["type"] == "memcached":
            params["metrix_prefix"] = "mc"
        elif params["type"] == "Tokyo Tyrant":
            params["metrix_prefix"] = "tt"

    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_of,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.0f',
        'units'       : 'XXX',
        'slope'       : 'XXX', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : params["type"],
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 15
    if "debug" in params:
        Debug = params["debug"]
    dprint("%s", "Debug mode on")

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    mp = params["metrix_prefix"]

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_curr_items",
                "units"      : "items",
                "slope"      : "both",
                "description": "Current number of items stored",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_cmd_get",
                "units"      : "commands",
                "slope"      : "positive",
                "description": "Cumulative number of retrieval reqs",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_cmd_set",
                "units"      : "commands",
                "slope"      : "positive",
                "description": "Cumulative number of storage reqs",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_bytes_read",
                "units"      : "bytes",
                "slope"      : "positive",
                "description": "Total number of bytes read by this server from network",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_bytes_written",
                "units"      : "bytes",
                "slope"      : "positive",
                "description": "Total number of bytes sent by this server to network",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_bytes",
                "units"      : "bytes",
                "slope"      : "both",
                "description": "Current number of bytes used to store items",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_limit_maxbytes",
                "units"      : "bytes",
                "slope"      : "both",
                "description": "Number of bytes this server is allowed to use for storage",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_curr_connections",
                "units"      : "connections",
                "slope"      : "both",
                "description": "Number of open connections",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_decr_hits",
                "units"      : "items",
                "slope"      : "positive",
                "description": "Number of keys that have been decremented and found present ",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_decr_misses",
                "units"      : "items",
                "slope"      : "positive",
                "description": "Number of items that have been decremented and not found",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_delete_hits",
                "units"      : "items",
                "slope"      : "positive",
                "description": "Number of keys that have been deleted and found present ",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_delete_misses",
                "units"      : "items",
                "slope"      : "positive",
                "description": "Number of items that have been deleted and not found",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_evictions",
                "units"      : "items",
                "slope"      : "both",
                "description": "Number of valid items removed from cache to free memory for new items",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_get_hits",
                "units"      : "items",
                "slope"      : "positive",
                "description": "Number of keys that have been requested and found present ",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_get_misses",
                "units"      : "items",
                "slope"      : "positive",
                "description": "Number of items that have been requested and not found",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_get_hits_rate",
                "units"      : "items",
                "slope"      : "both",
                "description": "Hits per second",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_get_misses_rate",
                "units"      : "items",
                "slope"      : "both",
                "description": "Misses per second",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_incr_hits",
                "units"      : "items",
                "slope"      : "positive",
                "description": "Number of keys that have been incremented and found present ",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_incr_misses",
                "units"      : "items",
                "slope"      : "positive",
                "description": "Number of items that have been incremented and not found",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_cmd_get_rate",
                "units"      : "commands",
                "slope"      : "both",
                "description": "Gets per second",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_cmd_set_rate",
                "units"      : "commands",
                "slope"      : "both",
                "description": "Sets per second",
                }))

    # Tokyo Tyrant
    if "type" in params and params["type"].lower().find("tokyo") == 0:
        dtmp = descriptors[:]
        for d in dtmp:
            if d["name"] in [
                mp+"_bytes_read",
                mp+"_bytes_written",
                mp+"_limit_maxbytes",
                mp+"_curr_connections",
                mp+"_evictions",
                ]:
                descriptors.remove(d)
        for d in descriptors:
            if d["name"] == mp+"_get_hits":
                d["name"] = mp+"_cmd_get_hits"
            if d["name"] == mp+"_get_misses":
                d["name"] = mp+"_cmd_get_misses"

        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : mp+"_cmd_set_hits",
                    "units"      : "items",
                    "slope"      : "positive",
                    "description": "Number of keys that have been stored and found present ",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : mp+"_cmd_set_misses",
                    "units"      : "items",
                    "slope"      : "positive",
                    "description": "Number of items that have been stored and not found",
                    }))

        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : mp+"_cmd_delete",
                    "units"      : "commands",
                    "slope"      : "positive",
                    "description": "Cumulative number of delete reqs",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : mp+"_cmd_delete_hits",
                    "units"      : "items",
                    "slope"      : "positive",
                    "description": "Number of keys that have been deleted and found present ",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"       : mp+"_cmd_delete_misses",
                    "units"      : "items",
                    "slope"      : "positive",
                    "description": "Number of items that have been deleted and not found",
                    }))


    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_of(name):
    return _Worker_Thread.metric_of(name)

def metric_cleanup():
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    try:
        params = {
            "host"  : "localhost",
            "port"  : 11211,
            # "host"  : "tt101",
            # "port"  : 1978,
            # "type"  : "Tokyo Tyrant",
            # "metrix_prefix" : "tt101",
            "debug" : True,
            }
        metric_init(params)

        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)

########NEW FILE########
__FILENAME__ = tokyotyrant
memcached.py
########NEW FILE########
__FILENAME__ = every
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Every

    Python decorator; decorated function is called on a set interval.

    :author: Ori Livneh <ori@wikimedia.org>
    :copyright: (c) 2012 Wikimedia Foundation
    :license: GPL, version 2 or later
"""
from __future__ import division
from datetime import timedelta
import signal
import sys
import threading


# pylint: disable=C0111, W0212, W0613, W0621


__all__ = ('every', )


def total_seconds(delta):
    """
    Get total seconds of timedelta object. Equivalent to
    timedelta.total_seconds(), which was introduced in Python 2.7.
    """
    us = (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10**6)
    return us / 1000000.0


def handle_sigint(signal, frame):
    """
    Attempt to kill all child threads and exit. Installing this as a sigint
    handler allows the program to run indefinitely if unmolested, but still
    terminate gracefully on Ctrl-C.
    """
    for thread in threading.enumerate():
        if thread.isAlive():
            thread._Thread__stop()
    sys.exit(0)


def every(*args, **kwargs):
    """
    Decorator; calls decorated function on a set interval. Arguments to every()
    are passed on to the constructor of datetime.timedelta(), which accepts the
    following arguments: days, seconds, microseconds, milliseconds, minutes,
    hours, weeks. This decorator is intended for functions with side effects;
    the return value is discarded.
    """
    interval = total_seconds(timedelta(*args, **kwargs))
    def decorator(func):
        def poll():
            func()
            threading.Timer(interval, poll).start()
        poll()
        return func
    return decorator


def join():
    """Pause until sigint"""
    signal.signal(signal.SIGINT, handle_sigint)
    signal.pause()


every.join = join

########NEW FILE########
__FILENAME__ = memcached
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Python Gmond Module for Memcached

    This module declares a "memcached" collection group. For more information,
    including installation instructions, see:

    http://sourceforge.net/apps/trac/ganglia/wiki/ganglia_gmond_python_modules

    When invoked as a standalone script, this module will attempt to use the
    default configuration to query memcached every 10 seconds and print out the
    results.

    Based on a suggestion from Domas Mitzuas, this module also reports the min,
    max, median and mean of the 'age' metric across slabs, as reported by the
    "stats items" memcached command.

    :copyright: (c) 2012 Wikimedia Foundation
    :author: Ori Livneh <ori@wikimedia.org>
    :license: GPL, v2 or later
"""
from __future__ import division, print_function

from threading import Timer

import logging
import os
import pprint
import sys
import telnetlib

logging.basicConfig(level=logging.DEBUG)

# Hack: load a file from the current module's directory, because gmond doesn't
# know how to work with Python packages. (To be fair, neither does Python.)
sys.path.insert(0, os.path.dirname(__file__))
from memcached_metrics import descriptors
from every import every
sys.path.pop(0)


# Default configuration
config = {
    'host' : '127.0.0.1',
    'port' : 11211,
}

stats = {}
client = telnetlib.Telnet()


def median(values):
    """Calculate median of series"""
    values = sorted(values)
    length = len(values)
    mid = length // 2
    if (length % 2):
        return values[mid]
    else:
        return (values[mid - 1] + values[mid]) / 2


def mean(values):
    """Calculate mean (average) of series"""
    return sum(values) / len(values)


def cast(value):
    """Cast value to float or int, if possible"""
    try:
        return float(value) if '.' in value else int(value)
    except ValueError:
        return value


def query(command):
    """Send `command` to memcached and stream response"""
    client.write(command.encode('ascii') + b'\n')
    while True:
        line = client.read_until(b'\r\n').decode('ascii').strip()
        if not line or line == 'END':
            break
        (_, metric, value) = line.split(None, 2)
        yield metric, cast(value)


@every(seconds=10)
def update_stats():
    """Refresh stats by polling memcached server"""
    try:
        client.open(**config)
        stats.update(query('stats'))
        ages = [v for k, v in query('stats items') if k.endswith('age')]
        if not ages:
            return {'age_min': 0, 'age_max': 0, 'age_mean': 0, 'age_median': 0}
        stats.update({
            'age_min'    : min(ages),
            'age_max'    : max(ages),
            'age_mean'   : mean(ages),
            'age_median' : median(ages)
        })
    finally:
        client.close()
    logging.info("Updated stats: %s", pprint.pformat(stats, indent=4))


#
# Gmond Interface
#

def metric_handler(name):
    """Get the value for a particular metric; part of Gmond interface"""
    return stats[name]


def metric_init(params):
    """Initialize; part of Gmond interface"""
    print('[memcached] memcached stats')
    config.update(params)
    for metric in descriptors:
        metric['call_back'] = metric_handler
    return descriptors


def metric_cleanup():
    """Teardown; part of Gmond interface"""
    client.close()


if __name__ == '__main__':
    # When invoked as standalone script, run a self-test by querying each
    # metric descriptor and printing it out.
    for metric in metric_init({}):
        value = metric['call_back'](metric['name'])
        print(( "%s => " + metric['format'] ) % ( metric['name'], value ))
    every.join()

########NEW FILE########
__FILENAME__ = memcached_metrics
#!/usr/bin/env python
# -*- coding: utf-8 -*-

descriptors = [ {
        "slope": "both",
        "time_max": 60,
        "description": "Current number of items stored by this instance",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "curr_items"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of items stored during the life of this instance",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "total_items"
    },
    {
        "slope": "both",
        "time_max": 60,
        "description": "Current number of bytes used by this server to store items",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "bytes"
    },
    {
        "slope": "both",
        "time_max": 60,
        "description": "Current number of open connections",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "curr_connections"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of connections opened since the server started running",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "total_connections"
    },
    {
        "slope": "both",
        "time_max": 60,
        "description": "Number of connection structures allocated by the server",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "connection_structures"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of retrieval requests (get operations)",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "cmd_get"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of storage requests (set operations)",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "cmd_set"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of keys that have been requested and found present",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "get_hits"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of items that have been requested and not found",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "get_misses"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of keys that have been deleted and found present",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "delete_hits"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of items that have been delete and not found",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "delete_misses"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of keys that have been incremented and found present",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "incr_hits"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of items that have been incremented and not found",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "incr_misses"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of keys that have been decremented and found present",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "decr_hits"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of items that have been decremented and not found",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "decr_misses"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of keys that have been compared and swapped and found present",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "cas_hits"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of items that have been compared and swapped and not found",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "cas_misses"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of valid items removed from cache to free memory for new items",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "evictions"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of bytes read by this server from network",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "bytes_read"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Total number of bytes sent by this server to network",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "bytes_written"
    },
    {
        "slope": "zero",
        "time_max": 60,
        "description": "Number of bytes this server is permitted to use for storage",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "limit_maxbytes"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of worker threads requested",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "threads"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Number of yields for connections",
        "format": "%d",
        "value_type": "uint",
        "groups": "memcached",
        "units": "items",
        "name": "conn_yields"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Age of the oldest item within slabs (mean)",
        "format": "%.2f",
        "value_type": "float",
        "groups": "memcached",
        "units": "items",
        "name": "age_mean"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Age of the oldest item within slabs (median)",
        "format": "%.2f",
        "value_type": "float",
        "groups": "memcached",
        "units": "items",
        "name": "age_median"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "Age of the oldest item within slabs (min)",
        "format": "%.2f",
        "value_type": "float",
        "groups": "memcached",
        "units": "items",
        "name": "age_min"
    },
    {
        "slope": "positive",
        "time_max": 60,
        "description": "The age of the oldest item within slabs (max)",
        "format": "%.2f",
        "value_type": "float",
        "groups": "memcached",
        "units": "items",
        "name": "age_max"
    }
]

########NEW FILE########
__FILENAME__ = mongodb
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# MongoDB gmond module for Ganglia
#
# Copyright (C) 2011 by Michael T. Conigliaro <mike [at] conigliaro [dot] org>.
# All rights reserved.
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

import json
import os
import re
import socket
import string
import time
import copy

NAME_PREFIX = 'mongodb_'
PARAMS = {
    'server_status' : '~/mongodb-osx-x86_64-1.8.1/bin/mongo --host mongodb04.example.com --port 27018 --quiet --eval "printjson(db.serverStatus())"',
    'rs_status'     : '~/mongodb-osx-x86_64-1.8.1/bin/mongo --host mongodb04.example.com --port 27018 --quiet --eval "printjson(rs.status())"'
}
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_TTL = 3


def flatten(d, pre = '', sep = '_'):
    """Flatten a dict (i.e. dict['a']['b']['c'] => dict['a_b_c'])"""

    new_d = {}
    for k,v in d.items():
        if type(v) == dict:
            new_d.update(flatten(d[k], '%s%s%s' % (pre, k, sep)))
        else:
            new_d['%s%s' % (pre, k)] = v
    return new_d


def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_TTL:

        metrics = {}
        for status_type in PARAMS.keys():

            # get raw metric data
            io = os.popen(PARAMS[status_type])

            # clean up
            metrics_str = ''.join(io.readlines()).strip() # convert to string
            metrics_str = re.sub('\w+\((.*)\)', r"\1", metrics_str) # remove functions

            # convert to flattened dict
            try:
                if status_type == 'server_status':
                    metrics.update(flatten(json.loads(metrics_str)))
                else:
                    metrics.update(flatten(json.loads(metrics_str), pre='%s_' % status_type))
            except ValueError:
                metrics = {}

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]


def get_value(name):
    """Return a value for the requested metric"""

     # get metrics
    metrics = get_metrics()[0]

    # get value
    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def get_rate(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    # get rate
    name = name[len(NAME_PREFIX):] # remove prefix from name

    try:
        rate = float(curr_metrics['data'][name] - last_metrics['data'][name]) / \
               float(curr_metrics['time'] - last_metrics['time'])
        if rate < 0:
            rate = float(0)
    except StandardError:
        rate = float(0)

    return rate


def get_opcounter_rate(name):
    """Return change over time for an opcounter metric"""

    master_rate = get_rate(name)
    repl_rate = get_rate(name.replace('opcounters_', 'opcountersRepl_'))

    return master_rate + repl_rate


def get_globalLock_ratio(name):
    """Return the global lock ratio"""

    try:
        result = get_rate(NAME_PREFIX + 'globalLock_lockTime') / \
                 get_rate(NAME_PREFIX + 'globalLock_totalTime') * 100
    except ZeroDivisionError:
        result = 0

    return result


def get_indexCounters_btree_miss_ratio(name):
    """Return the btree miss ratio"""

    try:
        result = get_rate(NAME_PREFIX + 'indexCounters_btree_misses') / \
                 get_rate(NAME_PREFIX + 'indexCounters_btree_accesses') * 100
    except ZeroDivisionError:
        result = 0

    return result


def get_connections_current_ratio(name):
    """Return the percentage of connections used"""

    try:
        result = float(get_value(NAME_PREFIX + 'connections_current')) / \
                 float(get_value(NAME_PREFIX + 'connections_available')) * 100
    except ZeroDivisionError:
        result = 0

    return result


def get_slave_delay(name):
    """Return the replica set slave delay"""

    # get metrics
    metrics = get_metrics()[0]

    # no point checking my optime if i'm not replicating
    if 'rs_status_myState' not in metrics['data'] or metrics['data']['rs_status_myState'] != 2:
        result = 0

    # compare my optime with the master's
    else:
        master = {}
        slave = {}
        try:
            for member in metrics['data']['rs_status_members']:
                if member['state'] == 1:
                    master = member
                if member['name'].split(':')[0] == socket.getfqdn():
                    slave = member
            result = max(0, master['optime']['t'] - slave['optime']['t']) / 1000
        except KeyError:
            result = 0

    return result


def get_asserts_total_rate(name):
    """Return the total number of asserts per second"""

    return float(reduce(lambda memo,obj: memo + get_rate('%sasserts_%s' % (NAME_PREFIX, obj)),
                       ['regular', 'warning', 'msg', 'user', 'rollovers'], 0))


def metric_init(lparams):
    """Initialize metric descriptors"""

    global PARAMS

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]

    # define descriptors
    time_max = 60
    groups = 'mongodb'
    descriptors = [
        {
            'name': NAME_PREFIX + 'opcounters_insert',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Inserts/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Inserts',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_query',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Queries/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Queries',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_update',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Updates/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Updates',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_delete',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Deletes/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Deletes',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_getmore',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Getmores/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Getmores',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'opcounters_command',
            'call_back': get_opcounter_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Commands/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Commands',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'backgroundFlushing_flushes',
            'call_back': get_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Flushes/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Flushes',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'mem_mapped',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'MB',
            'slope': 'both',
            'format': '%u',
            'description': 'Memory-mapped Data',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'mem_virtual',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'MB',
            'slope': 'both',
            'format': '%u',
            'description': 'Process Virtual Size',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'mem_resident',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'MB',
            'slope': 'both',
            'format': '%u',
            'description': 'Process Resident Size',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'extra_info_page_faults',
            'call_back': get_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Faults/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Page Faults',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_ratio',
            'call_back': get_globalLock_ratio,
            'time_max': time_max,
            'value_type': 'float',
            'units': '%',
            'slope': 'both',
            'format': '%f',
            'description': 'Global Write Lock Ratio',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'indexCounters_btree_miss_ratio',
            'call_back': get_indexCounters_btree_miss_ratio,
            'time_max': time_max,
            'value_type': 'float',
            'units': '%',
            'slope': 'both',
            'format': '%f',
            'description': 'BTree Page Miss Ratio',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_currentQueue_total',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Operations',
            'slope': 'both',
            'format': '%u',
            'description': 'Total Operations Waiting for Lock',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_currentQueue_readers',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Operations',
            'slope': 'both',
            'format': '%u',
            'description': 'Readers Waiting for Lock',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_currentQueue_writers',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Operations',
            'slope': 'both',
            'format': '%u',
            'description': 'Writers Waiting for Lock',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_activeClients_total',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Clients',
            'slope': 'both',
            'format': '%u',
            'description': 'Total Active Clients',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_activeClients_readers',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Clients',
            'slope': 'both',
            'format': '%u',
            'description': 'Active Readers',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'globalLock_activeClients_writers',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Clients',
            'slope': 'both',
            'format': '%u',
            'description': 'Active Writers',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'connections_current',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Connections',
            'slope': 'both',
            'format': '%u',
            'description': 'Open Connections',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'connections_current_ratio',
            'call_back': get_connections_current_ratio,
            'time_max': time_max,
            'value_type': 'float',
            'units': '%',
            'slope': 'both',
            'format': '%f',
            'description': 'Percentage of Connections Used',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'slave_delay',
            'call_back': get_slave_delay,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Seconds',
            'slope': 'both',
            'format': '%u',
            'description': 'Replica Set Slave Delay',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'asserts_total',
            'call_back': get_asserts_total_rate,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Asserts/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Asserts',
            'groups': groups
        }
    ]

    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            print (('%s = %s') % (d['name'], d['format'])) % (d['call_back'](d['name']))
        print ''
        time.sleep(METRICS_CACHE_TTL)

########NEW FILE########
__FILENAME__ = multi_nginx_status
#!/usr/bin/python
# Name: multi_nginx_status.py
# Desc: Ganglia python module for getting nginx stats from multiple nginx servers.
# Author: Evan Fraser (evan.fraser@trademe.co.nz) (inherited some code from existing nginx_status module)
# Date: 05/11/2012

import pprint
import time
import socket
import urllib2
import re

descriptors = list()

NIPARAMS = {}

NIMETRICS = {
    'time' : 0,
    'data' : {}
}

LAST_NIMETRICS = {}
NIMETRICS_CACHE_MAX = 10

# status_request() makes the http request to the nginx status pages
def status_request(srvname, port):
    url = 'http://' + srvname + ':' + port + '/nginx_status'
    c = urllib2.urlopen(url)
    data = c.read()
    c.close()

    matchActive = re.search(r'Active connections:\s+(\d+)', data)
    matchHistory = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', data)
    matchCurrent = re.search(r'Reading:\s*(\d+)\s*Writing:\s*(\d+)\s*'
            'Waiting:\s*(\d+)', data)
    if not matchActive or not matchHistory or not matchCurrent:
        raise Exception('Unable to parse {0}' . format(url))
    result = {}
    result[srvname + '_activeConn'] = float(matchActive.group(1))

    #These ones are accumulative and will need to have their delta calculated
    result[srvname + '_accepts'] = float(matchHistory.group(1))
    result[srvname + '_handled'] = float(matchHistory.group(2))
    result[srvname + '_requests'] = float(matchHistory.group(3))

    result[srvname + '_reading'] = float(matchCurrent.group(1))
    result[srvname + '_writing'] = float(matchCurrent.group(2))
    result[srvname + '_waiting'] = float(matchCurrent.group(3))

    return result

# get_metrics() is the callback metric handler, is called repeatedly by gmond
def get_metrics(name):
    global NIMETRICS,LAST_NIMETRICS
    # if interval since last check > NIMETRICS_CACHE_MAX get metrics again
    if (time.time() - NIMETRICS['time']) > NIMETRICS_CACHE_MAX:
        metrics = {}
        for para in NIPARAMS.keys():
            srvname,port = NIPARAMS[para].split(':')
            newmetrics = status_request(srvname,port)
            metrics = dict(newmetrics, **metrics)
                        
        LAST_NIMETRICS = dict(NIMETRICS)
        NIMETRICS = {
            'time': time.time(),
            'data': metrics
            }
    #For counter type metrics, return the delta instead:
    accumulative = ['_accepts', '_handled', '_requests']
    for m in accumulative:
        if m in name:
            try:
                delta = float(NIMETRICS['data'][name] - LAST_NIMETRICS['data'][name])/(NIMETRICS['time'] - LAST_NIMETRICS['time'])
                if delta < 0:
                    delta = 0
            except StandardError:
                delta = 0
            return delta

    return NIMETRICS['data'][name]
        
# create_desc() builds the descriptors from passed skeleton and additional properties
def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

# called by metric_init() to setup the metrics
def define_metrics(Desc_Skel, srvname, port):
    ip = socket.gethostbyname(srvname)
    spoof_str = ip + ':' + srvname
    print spoof_str
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_activeConn',
                "units"       : "connections",
                "description" : "Total number of active connections",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_accepts',
                "units"       : "connections/s",
                "description" : "Accepted connections per second",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_handled',
                "units"       : "connections/s",
                "description" : "Handled connections per second",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_requests',
                "units"       : "requests/s",
                "description" : "Requests per second",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_reading',
                "units"       : "connections",
                "description" : "Current connections in reading state",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_writing',
                "units"       : "connections",
                "description" : "Current connections in writing state",
                "spoof_host"  : spoof_str,
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"        : srvname + '_waiting',
                "units"       : "connections",
                "description" : "Current connections in waiting state",
                "spoof_host"  : spoof_str,
                }))

    return descriptors
# Called once by gmond to setup the metrics.
def metric_init(params):
    global descriptors, Desc_Skel
    print '[multinginx] Recieved the following parameters'
    print params

    for key in params:
        NIPARAMS[key] = params[key]

    Desc_Skel = {
        'name'        : 'XXX',
        #'call_back'   : 'XXX',
        'call_back'   : get_metrics,
        'time_max'    : 60,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'nginx',
        #'spoof_host'  : spoof_string
        }  

    for para in params.keys():
        if para.startswith('server_'):
            srvname,port = params[para].split(':')
            descriptors = define_metrics(Desc_Skel, srvname, port)

    return descriptors

# Below section is for debugging from the CLI.
if __name__ == '__main__':
    params = {
        #Example hostname:portnumber"
        'server_1' : 'imgsrv1:8080',
        'server_2' : 'imgsrv2:8080',
        'server_3' : 'imgsrv3:8081',
        }
    descriptors = metric_init(params)
    print len(descriptors)
    pprint.pprint(descriptors)
    while True:
         for d in descriptors:
             v = d['call_back'](d['name'])
             #print v
             print 'value for %s is %u' % (d['name'], v)
         print 'Sleeping 5 seconds'
         time.sleep(5)

########NEW FILE########
__FILENAME__ = mysql
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import threading
import time
import traceback
import MySQLdb

descriptors = list()
Desc_Skel   = {}
_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock

class UpdateMetricThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 10
        if "refresh_rate" in params:
            self.refresh_rate = int(params["refresh_rate"])
        self.metric       = {}

        self.dbuser   = "scott"
        self.dbpasswd = "tiger"
        self.dbhost   = ""
        self.read_default_file  = "/etc/my.cnf"
        self.read_default_group = "client"

        for attr in ("dbuser", "dbpasswd", "dbhost", "read_default_file", "read_default_group"):
            if attr in params:
                setattr(self, attr, params[attr])

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            self.update_metric()
            _Lock.release()
            time.sleep(self.refresh_rate)

        self.running = False

    def update_metric(self):
        conn = None
        try:
            conn = MySQLdb.connect(host=self.dbhost,
                                   user=self.dbuser, passwd=self.dbpasswd,
                                   use_unicode=True, charset="utf8",
                                   read_default_file=self.read_default_file,
                                   read_default_group=self.read_default_group,
                                   )

            my_status = {}

            conn.query("show global status")
            r = conn.store_result()
            while True:
                row = r.fetch_row(1,0)
                if not row:
                    break
                my_status[ row[0][0].lower() ] = int(row[0][1]) if row[0][1].isdigit() else row[0][1]

            conn.query("show table status from oriri like 'health'") # fixme
            r = conn.store_result()
            row = r.fetch_row(1,1)
            my_status["innodb_free"] = float(row[0]["Data_free"])

            self.metric["my_select"] = my_status["com_select"] \
                                     + my_status["qcache_hits"]     \
                                     + my_status["qcache_inserts"]  \
                                     + my_status["qcache_not_cached"]
            self.metric["my_insert"] = my_status["com_insert"] \
                                     + my_status["com_replace"]
            self.metric["my_update"] = my_status["com_update"]
            self.metric["my_delete"] = my_status["com_delete"]

            self.metric["my_qps"]          = my_status["queries"]
            self.metric["my_slow_queries"] = my_status["slow_queries"]

            self.metric["my_threads_connected"] = my_status["threads_connected"]
            self.metric["my_threads_running"]   = my_status["threads_running"]

            self.metric["my_innodb_free"] = my_status["innodb_free"]/1024/1024/1024

            self.metric["my_innodb_buffer_pool_hit"] = \
                100.0 - ( float(my_status["innodb_buffer_pool_reads"]) / float(my_status["innodb_buffer_pool_read_requests"]) * 100.0 )
            self.metric["my_innodb_buffer_pool_dirty_pages"] = \
                ( float(my_status["innodb_buffer_pool_pages_dirty"]) / float(my_status["innodb_buffer_pool_pages_data"]) * 100.0 )
            self.metric["my_innodb_buffer_pool_total"] = \
                float(my_status["innodb_buffer_pool_pages_total"]) * float(my_status["innodb_page_size"]) / 1024/1024/1024
            self.metric["my_innodb_buffer_pool_free"] = \
                float(my_status["innodb_buffer_pool_pages_free"])  * float(my_status["innodb_page_size"]) / 1024/1024/1024

            self.metric["my_qcache_free"] = int(my_status["qcache_free_memory"])

            self.metric["my_key_cache"] = \
                100 - ( float(my_status["key_reads"]) / float(my_status["key_read_requests"]) * 100 )
            self.metric["my_query_cache"] = \
                100 * ( float(my_status["qcache_hits"]) / float(my_status["qcache_inserts"] + my_status["qcache_hits"] + my_status["qcache_not_cached"]) )
            self.metric["my_table_lock_immediate"] = \
                100 * ( float(my_status["table_locks_immediate"]) / float(my_status["table_locks_immediate"] + my_status["table_locks_waited"]) )
            self.metric["my_thread_cache"] = \
                100 - ( float(my_status["threads_created"]) / float(my_status["connections"]) * 100 )
            self.metric["my_tmp_table_on_memory"] = \
                100 * ( float(my_status["created_tmp_tables"]) / float( (my_status["created_tmp_disk_tables"] + my_status["created_tmp_tables"]) or 1 ) )

        except MySQLdb.MySQLError:
            traceback.print_exc()

        finally:
            if conn:
                conn.close()

    def metric_of(self, name):
        val = 0
        if name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            #print >>sys.stderr, name, val
            _Lock.release()
        return val

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread

    print '[mysql] mysql'
    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        "name"        : "XXX",
        "call_back"   : metric_of,
        "time_max"    : 60,
        "value_type"  : "uint",
        "units"       : "XXX",
        "slope"       : "XXX", # zero|positive|negative|both
        "format"      : "%d",
        "description" : "XXX",
        "groups"      : "mysql",
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 10

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()
    _Worker_Thread.update_metric()

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    query_skel = create_desc(Desc_Skel, {
            "name"       : "XXX",
            "units"      : "query/sec",
            "slope"      : "positive",
            "format"     : "%d",
            "description": "XXX",
            })
    descriptors.append(create_desc(query_skel, {
                "name"       : "my_select",
                "description": "SELECT query", }));
    descriptors.append(create_desc(query_skel, {
                "name"       : "my_insert",
                "description": "INSERT query", }));
    descriptors.append(create_desc(query_skel, {
                "name"       : "my_update",
                "description": "UPDATE query", }));
    descriptors.append(create_desc(query_skel, {
                "name"       : "my_delete",
                "description": "DELETE query", }));

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_qps",
                "units"      : "q/s",
                "slope"      : "positive",
                "description": "queries per second", }));
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_slow_queries",
                "units"      : "queries",
                "slope"      : "both",
                "description": "total number of slow queries", }));

    threads_skel = create_desc(Desc_Skel, {
            "name"       : "XXX",
            "units"      : "threads",
            "slope"      : "both",
            "format"     : "%d",
            "description": "XXX",
            })
    descriptors.append(create_desc(threads_skel, {
                "name"       : "my_threads_connected",
                "description": "threads connected", }));
    descriptors.append(create_desc(threads_skel, {
                "name"       : "my_threads_running",
                "description": "threads running", }));

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_innodb_free",
                "value_type" : "float",
                "format"     : "%.3f",
                "units"      : "GB",
                "slope"      : "both",
                "description": "Innodb free area", }));

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_innodb_buffer_pool_hit",
                "value_type" : "float",
                "format"     : "%.2f",
                "units"      : "%",
                "slope"      : "both",
                "description": "Innodb buffer pool hit ratio", }));
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_innodb_buffer_pool_dirty_pages",
                "value_type" : "float",
                "format"     : "%.2f",
                "units"      : "%",
                "slope"      : "both",
                "description": "Innodb buffer pool dirty pages ratio", }));

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_innodb_buffer_pool_total",
                "value_type" : "float",
                "format"     : "%.3f",
                "units"      : "GB",
                "slope"      : "both",
                "description": "Innodb total size of buffer pool", }));
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_innodb_buffer_pool_free",
                "value_type" : "float",
                "format"     : "%.3f",
                "units"      : "GB",
                "slope"      : "both",
                "description": "Innodb free size of buffer pool", }));

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "my_qcache_free",
                "value_type" : "uint",
                "format"     : "%d",
                "units"      : "Bytes",
                "slope"      : "both",
                "description": "query cache free area", }));

    ratio_skel = create_desc(Desc_Skel, {
            "name"       : "XXX",
            "units"      : "%",
            "slope"      : "both",
            "value_type" : "float",
            "format"     : "%.2f",
            "description": "XXX",
            })
    descriptors.append(create_desc(ratio_skel, {
                "name"       : "my_key_cache",
                "description": "key cache hit ratio", }));
    descriptors.append(create_desc(ratio_skel, {
                "name"       : "my_query_cache",
                "description": "query cache hit ratio", }));
    descriptors.append(create_desc(ratio_skel, {
                "name"       : "my_table_lock_immediate",
                "description": "table lock immediate ratio", }));
    descriptors.append(create_desc(ratio_skel, {
                "name"       : "my_thread_cache",
                "description": "thread cache ratio", }));
    descriptors.append(create_desc(ratio_skel, {
                "name"       : "my_tmp_table_on_memory",
                "description": "tmp table on memory ratio", }));


    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_of(name):
    return _Worker_Thread.metric_of(name)

def metric_cleanup():
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    try:
        params = {
            'dbuser'      : 'health',
            'dbpasswd'    : '',
            'dbhost'      : 'localhost',
            #'spoof_host'  : '10.10.4.6:db109',
            'refresh_rate': 5,
            }
        metric_init(params)
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            print
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except StandardError:
        os._exit(1)

########NEW FILE########
__FILENAME__ = DBUtil
"""
The MIT License

Copyright (c) 2008 Gilad Raphaelli <gilad@raphaelli.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

if using < python2.5, http://code.activestate.com/recipes/523034/ works as a
pure python collections.defaultdict substitute
"""

#from collections import defaultdict
try:
    from collections import defaultdict
except:
    class defaultdict(dict):
        def __init__(self, default_factory=None, *a, **kw):
            if (default_factory is not None and
                not hasattr(default_factory, '__call__')):
                raise TypeError('first argument must be callable')
            dict.__init__(self, *a, **kw)
            self.default_factory = default_factory
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)
        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            self[key] = value = self.default_factory()
            return value
        def __reduce__(self):
            if self.default_factory is None:
                args = tuple()
            else:
                args = self.default_factory,
            return type(self), args, None, None, self.items()
        def copy(self):
            return self.__copy__()
        def __copy__(self):
            return type(self)(self.default_factory, self)
        def __deepcopy__(self, memo):
            import copy
            return type(self)(self.default_factory,
                              copy.deepcopy(self.items()))
        def __repr__(self):
            return 'defaultdict(%s, %s)' % (self.default_factory,
                                            dict.__repr__(self))

import MySQLdb

def is_hex(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False

def longish(x):
        if len(x):
                try:
                        return long(x)
                except ValueError:
                        if(x.endswith(',')):
                           return longish(x[:-1])
                        if(is_hex(x.lower()) == True):
                           return hexlongish(x)
                        #print "X==(%s)(%s)(%s)" %(x, x[:-1],hexlongish(x)), sys.exc_info()[0]
                        return longish(x[:-1])
        else:
                raise ValueError

def hexlongish(x):
	if len(x):
		try:
			return long(str(x), 16)
		except ValueError:
			return longish(x[:-1])
	else:
		raise ValueError

def parse_innodb_status(innodb_status_raw, innodb_version="1.0"):
	def sumof(status):
		def new(*idxs):
			return sum(map(lambda x: longish(status[x]), idxs))
		return new

	innodb_status = defaultdict(int)
	innodb_status['active_transactions']
	individual_buffer_pool_info = False
	
	for line in innodb_status_raw:
		istatus = line.split()

		isum = sumof(istatus)

		# SEMAPHORES
		if "Mutex spin waits" in line:
			innodb_status['spin_waits'] += longish(istatus[3])
			innodb_status['spin_rounds'] += longish(istatus[5])
			innodb_status['os_waits'] += longish(istatus[8])

		elif "RW-shared spins" in line:
			if innodb_version == 1.0:
				innodb_status['spin_waits'] += isum(2,8)
				innodb_status['os_waits'] += isum(5,11)
			elif innodb_version >= 5.5:
				innodb_status['spin_waits'] += longish(istatus[2])
				innodb_status['os_waits'] += longish(istatus[7])

		elif "RW-excl spins" in line and innodb_version >= 5.5:
			innodb_status['spin_waits'] += longish(istatus[2])
			innodb_status['os_waits'] += longish(istatus[7])

		# TRANSACTIONS
		elif "Trx id counter" in line:
			if innodb_version >= 5.6:
				innodb_status['transactions'] += longish(istatus[3])
			elif innodb_version == 5.5:
				innodb_status['transactions'] += hexlongish(istatus[3])
			else:
				innodb_status['transactions'] += isum(3,4)

		elif "Purge done for trx" in line:
			if innodb_version >= 5.6:
				innodb_status['transactions_purged'] += longish(istatus[6])
			elif innodb_version == 5.5:
				innodb_status['transactions_purged'] += hexlongish(istatus[6])
			else:
				innodb_status['transactions_purged'] += isum(6,7)

		elif "History list length" in line:
			innodb_status['history_list'] = longish(istatus[3])

		elif "---TRANSACTION" in line and innodb_status['transactions']:
			innodb_status['current_transactions'] += 1
			if "ACTIVE" in line:
				innodb_status['active_transactions'] += 1

		elif "LOCK WAIT" in line and innodb_status['transactions']:
			innodb_status['locked_transactions'] += 1

		elif 'read views open inside' in line:
			innodb_status['read_views'] = longish(istatus[0])

		# FILE I/O
		elif 'OS file reads' in line:
			innodb_status['data_reads'] = longish(istatus[0])
			innodb_status['data_writes'] = longish(istatus[4])
			innodb_status['data_fsyncs'] = longish(istatus[8])

		elif 'Pending normal aio' in line:
			innodb_status['pending_normal_aio_reads'] = longish(istatus[4])
			innodb_status['pending_normal_aio_writes'] = longish(istatus[7])

		elif 'ibuf aio reads' in line:
			innodb_status['pending_ibuf_aio_reads'] = longish(istatus[3])
			innodb_status['pending_aio_log_ios'] = longish(istatus[6])
			innodb_status['pending_aio_sync_ios'] = longish(istatus[9])

		elif 'Pending flushes (fsync)' in line:
			innodb_status['pending_log_flushes'] = longish(istatus[4])
			innodb_status['pending_buffer_pool_flushes'] = longish(istatus[7])

		# INSERT BUFFER AND ADAPTIVE HASH INDEX
		elif 'merged recs' in line and innodb_version == 1.0:
			innodb_status['ibuf_inserts'] = longish(istatus[0])
			innodb_status['ibuf_merged'] = longish(istatus[2])
			innodb_status['ibuf_merges'] = longish(istatus[5])

		elif 'Ibuf: size' in line and innodb_version >= 5.5:
			innodb_status['ibuf_merges'] = longish(istatus[10])

		elif 'merged operations' in line and innodb_version >= 5.5:
			in_merged = 1

		elif 'delete mark' in line and 'in_merged' in vars() and innodb_version >= 5.5:
			innodb_status['ibuf_inserts'] = longish(istatus[1])
			innodb_status['ibuf_merged'] = 0
			del in_merged

		# LOG
		elif "log i/o's done" in line:
			innodb_status['log_writes'] = longish(istatus[0])

		elif "pending log writes" in line:
			innodb_status['pending_log_writes'] = longish(istatus[0])
			innodb_status['pending_chkp_writes'] = longish(istatus[4])
		
		elif "Log sequence number" in line:
			if innodb_version >= 5.5:
				innodb_status['log_bytes_written'] = longish(istatus[3])
			else:
				innodb_status['log_bytes_written'] = isum(3,4)
		
		elif "Log flushed up to" in line:
			if innodb_version >= 5.5:
				innodb_status['log_bytes_flushed'] = longish(istatus[4])
			else:
				innodb_status['log_bytes_flushed'] = isum(4,5)

		# BUFFER POOL AND MEMORY
		elif "INDIVIDUAL BUFFER POOL INFO" in line:
			# individual pools section.  We only want to record the totals 
			# rather than each individual pool clobbering the totals
			individual_buffer_pool_info = True

		elif "Buffer pool size, bytes" in line and not individual_buffer_pool_info:
			innodb_status['buffer_pool_pages_bytes'] = longish(istatus[4])

		elif "Buffer pool size" in line and not individual_buffer_pool_info:
			innodb_status['buffer_pool_pages_total'] = longish(istatus[3])
		
		elif "Free buffers" in line and not individual_buffer_pool_info:
			innodb_status['buffer_pool_pages_free'] = longish(istatus[2])
		
		elif "Database pages" in line and not individual_buffer_pool_info:
			innodb_status['buffer_pool_pages_data'] = longish(istatus[2])
		
		elif "Modified db pages" in line and not individual_buffer_pool_info:
			innodb_status['buffer_pool_pages_dirty'] = longish(istatus[3])
		
		elif "Pages read" in line and "ahead" not in line and not individual_buffer_pool_info:
				innodb_status['pages_read'] = longish(istatus[2])
				innodb_status['pages_created'] = longish(istatus[4])
				innodb_status['pages_written'] = longish(istatus[6])

		# ROW OPERATIONS
		elif 'Number of rows inserted' in line:
			innodb_status['rows_inserted'] = longish(istatus[4])
			innodb_status['rows_updated'] = longish(istatus[6])
			innodb_status['rows_deleted'] = longish(istatus[8])
			innodb_status['rows_read'] = longish(istatus[10])
		
		elif "queries inside InnoDB" in line:
			innodb_status['queries_inside'] = longish(istatus[0])
			innodb_status['queries_queued'] = longish(istatus[4])

	# Some more stats
	innodb_status['transactions_unpurged'] = innodb_status['transactions'] - innodb_status['transactions_purged']
	innodb_status['log_bytes_unflushed'] = innodb_status['log_bytes_written'] - innodb_status['log_bytes_flushed']

	return innodb_status
	
if __name__ == '__main__':
	from optparse import OptionParser

	parser = OptionParser()
	parser.add_option("-H", "--Host", dest="host", help="Host running mysql", default="localhost")
	parser.add_option("-u", "--user", dest="user", help="user to connect as", default="")
	parser.add_option("-p", "--password", dest="passwd", help="password", default="")
	(options, args) = parser.parse_args()

	try:
		conn = MySQLdb.connect(user=options.user, host=options.host, passwd=options.passwd)

		cursor = conn.cursor(MySQLdb.cursors.Cursor)
		cursor.execute("SHOW /*!50000 ENGINE*/ INNODB STATUS")
		innodb_status = parse_innodb_status(cursor.fetchone()[0].split('\n'))
		cursor.close()

		conn.close()
	except MySQLdb.OperationalError, (errno, errmsg):
		raise


########NEW FILE########
__FILENAME__ = mysql
"""
The MIT License

Copyright (c) 2008 Gilad Raphaelli <gilad@raphaelli.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

###  Changelog:
###    v1.0.1 - 2010-07-21
###       * Initial version
###
###    v1.0.2 - 2010-08-04
###       * Added system variables: max_connections and query_cache_size
###       * Modified some innodb status variables to become deltas
###
###    v1.0.3 - 2011-12-02
###       * Support custom UNIX sockets
###
###  Requires:
###       * yum install MySQL-python
###       * DBUtil.py

###  Copyright Jamie Isaacs. 2010
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import MySQLdb

from DBUtil import parse_innodb_status, defaultdict

import logging

descriptors = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/mysqlstats.log', filemode='w')
logging.debug('starting up')

last_update = 0
mysql_conn_opts = {}
mysql_stats = {}
mysql_stats_last = {}
delta_per_second = False

REPORT_INNODB = True
REPORT_MASTER = True
REPORT_SLAVE  = True

MAX_UPDATE_TIME = 15

def update_stats(get_innodb=True, get_master=True, get_slave=True):
	"""

	"""
	logging.debug('updating stats')
	global last_update
	global mysql_stats, mysql_stats_last

	cur_time = time.time()
	time_delta = cur_time - last_update
	if time_delta <= 0:
		#we went backward in time.
		logging.debug(" system clock set backwards, probably ntp")

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True
	else:
		last_update = cur_time

	logging.debug('refreshing stats')
	mysql_stats = {}

	# Get info from DB
	try:
		conn = MySQLdb.connect(**mysql_conn_opts)

		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SELECT GET_LOCK('gmetric-mysql', 0) as ok")
		lock_stat = cursor.fetchone()
		cursor.close()

		if lock_stat['ok'] == 0:
			return False

		cursor = conn.cursor(MySQLdb.cursors.Cursor)
		cursor.execute("SHOW VARIABLES")
		#variables = dict(((k.lower(), v) for (k,v) in cursor))
		variables = {}
		for (k,v) in cursor:
			variables[k.lower()] = v
		cursor.close()

		cursor = conn.cursor(MySQLdb.cursors.Cursor)
		cursor.execute("SHOW /*!50002 GLOBAL */ STATUS")
		#global_status = dict(((k.lower(), v) for (k,v) in cursor))
		global_status = {}
		for (k,v) in cursor:
			global_status[k.lower()] = v
		cursor.close()
		
		cursor = conn.cursor(MySQLdb.cursors.Cursor)
		cursor.execute("SELECT PLUGIN_STATUS, PLUGIN_VERSION FROM `information_schema`.Plugins WHERE PLUGIN_NAME LIKE '%innodb%' AND PLUGIN_TYPE LIKE 'STORAGE ENGINE';")
		
		have_innodb = False
		innodb_version = 1.0
		row = cursor.fetchone()
		
		if row[0] == "ACTIVE":
			have_innodb = True
			innodb_version = row[1]
		cursor.close()

		# try not to fail ?
		get_innodb = get_innodb and have_innodb
		get_master = get_master and variables['log_bin'].lower() == 'on'

		innodb_status = defaultdict(int)
		if get_innodb:
			cursor = conn.cursor(MySQLdb.cursors.Cursor)
			cursor.execute("SHOW /*!50000 ENGINE*/ INNODB STATUS")
			innodb_status = parse_innodb_status(cursor.fetchone()[2].split('\n'), innodb_version)
			cursor.close()
			logging.debug('innodb_status: ' + str(innodb_status))

		master_logs = tuple
		if get_master:
			cursor = conn.cursor(MySQLdb.cursors.Cursor)
			cursor.execute("SHOW MASTER LOGS")
			master_logs = cursor.fetchall()
			cursor.close()

		slave_status = {}
		if get_slave:
			cursor = conn.cursor(MySQLdb.cursors.DictCursor)
			cursor.execute("SHOW SLAVE STATUS")
			res = cursor.fetchone()
			if res:
				for (k,v) in res.items():
					slave_status[k.lower()] = v
			else:
				get_slave = False
			cursor.close()

		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SELECT RELEASE_LOCK('gmetric-mysql') as ok")
		cursor.close()

		conn.close()
	except MySQLdb.OperationalError, (errno, errmsg):
		logging.error('error updating stats')
		logging.error(errmsg)
		return False

	# process variables
	# http://dev.mysql.com/doc/refman/5.0/en/server-system-variables.html
	mysql_stats['version'] = variables['version']
	mysql_stats['max_connections'] = variables['max_connections']
	mysql_stats['query_cache_size'] = variables['query_cache_size']

	# process global status
	# http://dev.mysql.com/doc/refman/5.0/en/server-status-variables.html
	interesting_global_status_vars = (
		'aborted_clients',
		'aborted_connects',
		'binlog_cache_disk_use',
		'binlog_cache_use',
		'bytes_received',
		'bytes_sent',
		'com_delete',
		'com_delete_multi',
		'com_insert',
		'com_insert_select',
		'com_load',
		'com_replace',
		'com_replace_select',
		'com_select',
		'com_update',
		'com_update_multi',
		'connections',
		'created_tmp_disk_tables',
		'created_tmp_files',
		'created_tmp_tables',
		'key_reads',
		'key_read_requests',
		'key_writes',
		'key_write_requests',
		'max_used_connections',
		'open_files',
		'open_tables',
		'opened_tables',
		'qcache_free_blocks',
		'qcache_free_memory',
		'qcache_hits',
		'qcache_inserts',
		'qcache_lowmem_prunes',
		'qcache_not_cached',
		'qcache_queries_in_cache',
		'qcache_total_blocks',
		'questions',
		'select_full_join',
		'select_full_range_join',
		'select_range',
		'select_range_check',
		'select_scan',
		'slave_open_temp_tables',
		'slave_retried_transactions',
		'slow_launch_threads',
		'slow_queries',
		'sort_range',
		'sort_rows',
		'sort_scan',
		'table_locks_immediate',
		'table_locks_waited',
		'threads_cached',
		'threads_connected',
		'threads_created',
		'threads_running',
		'uptime',
	)

	non_delta = (
		'max_used_connections',
		'open_files',
		'open_tables',
		'qcache_free_blocks',
		'qcache_free_memory',
		'qcache_total_blocks',
		'slave_open_temp_tables',
		'threads_cached',
		'threads_connected',
		'threads_running',
		'uptime'
	)

	# don't put all of global_status in mysql_stats b/c it's so big
	for key in interesting_global_status_vars:
		if key in non_delta:
			mysql_stats[key] = global_status[key]
		else:
			# Calculate deltas for counters
			if time_delta <= 0:
				#systemclock was set backwards, nog updating values.. to smooth over the graphs
				pass
			elif key in mysql_stats_last:
				if delta_per_second:
					mysql_stats[key] = (int(global_status[key]) - int(mysql_stats_last[key])) / time_delta
				else:
					mysql_stats[key] = int(global_status[key]) - int(mysql_stats_last[key])
			else:
				mysql_stats[key] = float(0)

			mysql_stats_last[key] = global_status[key]

	mysql_stats['open_files_used'] = int(global_status['open_files']) / int(variables['open_files_limit'])

	innodb_delta = (
		'data_fsyncs',
		'data_reads',
		'data_writes',
		'log_writes'
	)

	# process innodb status
	if get_innodb:
		for istat in innodb_status:
			key = 'innodb_' + istat

			if istat in innodb_delta:
				# Calculate deltas for counters
				if time_delta <= 0:
					#systemclock was set backwards, nog updating values.. to smooth over the graphs
					pass
				elif key in mysql_stats_last:
					if delta_per_second:
						mysql_stats[key] = (int(innodb_status[istat]) - int(mysql_stats_last[key])) / time_delta
					else:
						mysql_stats[key] = int(innodb_status[istat]) - int(mysql_stats_last[key])
				else:
					mysql_stats[key] = float(0)

				mysql_stats_last[key] = innodb_status[istat]

			else:
				mysql_stats[key] = innodb_status[istat]

	# process master logs
	if get_master:
		mysql_stats['binlog_count'] = len(master_logs)
		mysql_stats['binlog_space_current'] = master_logs[-1][1]
		#mysql_stats['binlog_space_total'] = sum((long(s[1]) for s in master_logs))
		mysql_stats['binlog_space_total'] = 0
		for s in master_logs:
			mysql_stats['binlog_space_total'] += int(s[1])
		mysql_stats['binlog_space_used'] = float(master_logs[-1][1]) / float(variables['max_binlog_size']) * 100

	# process slave status
	if get_slave:
		mysql_stats['slave_exec_master_log_pos'] = slave_status['exec_master_log_pos']
		#mysql_stats['slave_io'] = 1 if slave_status['slave_io_running'].lower() == "yes" else 0
		if slave_status['slave_io_running'].lower() == "yes":
			mysql_stats['slave_io'] = 1
		else:
			mysql_stats['slave_io'] = 0
		#mysql_stats['slave_sql'] = 1 if slave_status['slave_sql_running'].lower() =="yes" else 0
		if slave_status['slave_sql_running'].lower() == "yes":
			mysql_stats['slave_sql'] = 1
		else:
			mysql_stats['slave_sql'] = 0
		mysql_stats['slave_lag'] = slave_status['seconds_behind_master']
		mysql_stats['slave_relay_log_pos'] = slave_status['relay_log_pos']
		mysql_stats['slave_relay_log_space'] = slave_status['relay_log_space']


	logging.debug('success updating stats')
	logging.debug('mysql_stats: ' + str(mysql_stats))

def get_stat(name):
	logging.info("getting stat: %s" % name)
	global mysql_stats
	#logging.debug(mysql_stats)

	global REPORT_INNODB
	global REPORT_MASTER
	global REPORT_SLAVE

	ret = update_stats(REPORT_INNODB, REPORT_MASTER, REPORT_SLAVE)

	if ret:
		if name.startswith('mysql_'):
			label = name[6:]
		else:
			label = name

		logging.debug("fetching %s" % name)
		try:
			return mysql_stats[label]
		except:
			logging.error("failed to fetch %s" % name)
			return 0
	else:
		return 0

def metric_init(params):
	global descriptors
	global mysql_conn_opts
	global mysql_stats
	global delta_per_second

	global REPORT_INNODB
	global REPORT_MASTER
	global REPORT_SLAVE

	REPORT_INNODB = str(params.get('get_innodb', True)) == "True"
	REPORT_MASTER = str(params.get('get_master', True)) == "True"
	REPORT_SLAVE  = str(params.get('get_slave', True)) == "True"

	logging.debug("init: " + str(params))

	mysql_conn_opts = dict(
		host = params.get('host', 'localhost'),
		user = params.get('user'),
		passwd = params.get('passwd'),
		port = int(params.get('port', 3306)),
		connect_timeout = int(params.get('timeout', 30)),
	)
	if params.get('unix_socket', '') != '':
		mysql_conn_opts['unix_socket'] = params.get('unix_socket')

	if params.get("delta_per_second", '') != '':
		delta_per_second = True

	master_stats_descriptions = {}
	innodb_stats_descriptions = {}
	slave_stats_descriptions  = {}

	misc_stats_descriptions = dict(
		aborted_clients = {
			'description': 'The number of connections that were aborted because the client died without closing the connection properly',
			'value_type': 'float',
			'units': 'clients',
		}, 

		aborted_connects = {
			'description': 'The number of failed attempts to connect to the MySQL server',
			'value_type': 'float',
			'units': 'conns',
		}, 

		binlog_cache_disk_use = {
			'description': 'The number of transactions that used the temporary binary log cache but that exceeded the value of binlog_cache_size and used a temporary file to store statements from the transaction',
			'value_type': 'float',
			'units': 'txns',
		}, 

		binlog_cache_use = {
			'description': ' The number of transactions that used the temporary binary log cache',
			'value_type': 'float',
			'units': 'txns',
		}, 

		bytes_received = {
			'description': 'The number of bytes received from all clients',
			'value_type': 'float',
			'units': 'bytes',
		}, 

		bytes_sent = {
			'description': ' The number of bytes sent to all clients',
			'value_type': 'float',
			'units': 'bytes',
		}, 

		com_delete = {
			'description': 'The number of DELETE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_delete_multi = {
			'description': 'The number of multi-table DELETE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_insert = {
			'description': 'The number of INSERT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_insert_select = {
			'description': 'The number of INSERT ... SELECT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_load = {
			'description': 'The number of LOAD statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_replace = {
			'description': 'The number of REPLACE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_replace_select = {
			'description': 'The number of REPLACE ... SELECT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_select = {
			'description': 'The number of SELECT statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_update = {
			'description': 'The number of UPDATE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		com_update_multi = {
			'description': 'The number of multi-table UPDATE statements',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		connections = {
			'description': 'The number of connection attempts (successful or not) to the MySQL server',
			'value_type': 'float',
			'units': 'conns',
		}, 

		created_tmp_disk_tables = {
			'description': 'The number of temporary tables on disk created automatically by the server while executing statements',
			'value_type': 'float',
			'units': 'tables',
		}, 

		created_tmp_files = {
			'description': 'The number of temporary files mysqld has created',
			'value_type': 'float',
			'units': 'files',
		}, 

		created_tmp_tables = {
			'description': 'The number of in-memory temporary tables created automatically by the server while executing statement',
			'value_type': 'float',
			'units': 'tables',
		}, 

		#TODO in graphs: key_read_cache_miss_rate = key_reads / key_read_requests

		key_read_requests = {
			'description': 'The number of requests to read a key block from the cache',
			'value_type': 'float',
			'units': 'reqs',
		}, 

		key_reads = {
			'description': 'The number of physical reads of a key block from disk',
			'value_type': 'float',
			'units': 'reads',
		}, 

		key_write_requests = {
			'description': 'The number of requests to write a key block to the cache',
			'value_type': 'float',
			'units': 'reqs',
		}, 

		key_writes = {
			'description': 'The number of physical writes of a key block to disk',
			'value_type': 'float',
			'units': 'writes',
		}, 

		max_used_connections = {
			'description': 'The maximum number of connections that have been in use simultaneously since the server started',
			'units': 'conns',
			'slope': 'both',
		}, 

		open_files = {
			'description': 'The number of files that are open',
			'units': 'files',
			'slope': 'both',
		}, 

		open_tables = {
			'description': 'The number of tables that are open',
			'units': 'tables',
			'slope': 'both',
		}, 

		# If Opened_tables is big, your table_cache value is probably too small. 
		opened_tables = {
			'description': 'The number of tables that have been opened',
			'value_type': 'float',
			'units': 'tables',
		}, 

		qcache_free_blocks = {
			'description': 'The number of free memory blocks in the query cache',
			'units': 'blocks',
			'slope': 'both',
		}, 

		qcache_free_memory = {
			'description': 'The amount of free memory for the query cache',
			'units': 'bytes',
			'slope': 'both',
		}, 

		qcache_hits = {
			'description': 'The number of query cache hits',
			'value_type': 'float',
			'units': 'hits',
		}, 

		qcache_inserts = {
			'description': 'The number of queries added to the query cache',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_lowmem_prunes = {
			'description': 'The number of queries that were deleted from the query cache because of low memory',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_not_cached = {
			'description': 'The number of non-cached queries (not cacheable, or not cached due to the query_cache_type setting)',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_queries_in_cache = {
			'description': 'The number of queries registered in the query cache',
			'value_type': 'float',
			'units': 'queries',
		}, 

		qcache_total_blocks = {
			'description': 'The total number of blocks in the query cache',
			'units': 'blocks',
		}, 

		questions = {
			'description': 'The number of statements that clients have sent to the server',
			'value_type': 'float',
			'units': 'stmts',
		}, 

		# If this value is not 0, you should carefully check the indexes of your tables.
		select_full_join = {
			'description': 'The number of joins that perform table scans because they do not use indexes',
			'value_type': 'float',
			'units': 'joins',
		}, 

		select_full_range_join = {
			'description': 'The number of joins that used a range search on a reference table',
			'value_type': 'float',
			'units': 'joins',
		}, 

		select_range = {
			'description': 'The number of joins that used ranges on the first table',
			'value_type': 'float',
			'units': 'joins',
		}, 

		# If this is not 0, you should carefully check the indexes of your tables.
		select_range_check = {
			'description': 'The number of joins without keys that check for key usage after each row',
			'value_type': 'float',
			'units': 'joins',
		}, 

		select_scan = {
			'description': 'The number of joins that did a full scan of the first table',
			'value_type': 'float',
			'units': 'joins',
		}, 

		slave_open_temp_tables = {
			'description': 'The number of temporary tables that the slave SQL thread currently has open',
			'value_type': 'float',
			'units': 'tables',
			'slope': 'both',
		}, 

		slave_retried_transactions = {
			'description': 'The total number of times since startup that the replication slave SQL thread has retried transactions',
			'value_type': 'float',
			'units': 'count',
		}, 

		slow_launch_threads = {
			'description': 'The number of threads that have taken more than slow_launch_time seconds to create',
			'value_type': 'float',
			'units': 'threads',
		}, 

		slow_queries = {
			'description': 'The number of queries that have taken more than long_query_time seconds',
			'value_type': 'float',
			'units': 'queries',
		}, 

		sort_range = {
			'description': 'The number of sorts that were done using ranges',
			'value_type': 'float',
			'units': 'sorts',
		}, 

		sort_rows = {
			'description': 'The number of sorted rows',
			'value_type': 'float',
			'units': 'rows',
		}, 

		sort_scan = {
			'description': 'The number of sorts that were done by scanning the table',
			'value_type': 'float',
			'units': 'sorts',
		}, 

		table_locks_immediate = {
			'description': 'The number of times that a request for a table lock could be granted immediately',
			'value_type': 'float',
			'units': 'count',
		}, 

		# If this is high and you have performance problems, you should first optimize your queries, and then either split your table or tables or use replication.
		table_locks_waited = {
			'description': 'The number of times that a request for a table lock could not be granted immediately and a wait was needed',
			'value_type': 'float',
			'units': 'count',
		}, 

		threads_cached = {
			'description': 'The number of threads in the thread cache',
			'units': 'threads',
			'slope': 'both',
		}, 

		threads_connected = {
			'description': 'The number of currently open connections',
			'units': 'threads',
			'slope': 'both',
		}, 

		#TODO in graphs: The cache miss rate can be calculated as Threads_created/Connections

		# Threads_created is big, you may want to increase the thread_cache_size value. 
		threads_created = {
			'description': 'The number of threads created to handle connections',
			'value_type': 'float',
			'units': 'threads',
		}, 

		threads_running = {
			'description': 'The number of threads that are not sleeping',
			'units': 'threads',
			'slope': 'both',
		}, 

		uptime = {
			'description': 'The number of seconds that the server has been up',
			'units': 'secs',
			'slope': 'both',
		}, 

		version = {
			'description': "MySQL Version",
			'value_type': 'string',
		    'format': '%s',
		},

		max_connections = {
			'description': "The maximum permitted number of simultaneous client connections",
			'slope': 'zero',
		},

		query_cache_size = {
			'description': "The amount of memory allocated for caching query results",
			'slope': 'zero',
		}
	)

	if REPORT_MASTER:
		master_stats_descriptions = dict(
			binlog_count = {
				'description': "Number of binary logs",
				'units': 'logs',
				'slope': 'both',
			},

			binlog_space_current = {
				'description': "Size of current binary log",
				'units': 'bytes',
				'slope': 'both',
			},

			binlog_space_total = {
				'description': "Total space used by binary logs",
				'units': 'bytes',
				'slope': 'both',
			},

			binlog_space_used = {
				'description': "Current binary log size / max_binlog_size",
				'value_type': 'float',
				'units': 'percent',
				'slope': 'both',
			},
		)

	if REPORT_SLAVE:
		slave_stats_descriptions = dict(
			slave_exec_master_log_pos = {
				'description': "The position of the last event executed by the SQL thread from the master's binary log",
				'units': 'bytes',
				'slope': 'both',
			},

			slave_io = {
				'description': "Whether the I/O thread is started and has connected successfully to the master",
				'value_type': 'uint8',
				'units': 'True/False',
				'slope': 'both',
			},

			slave_lag = {
				'description': "Replication Lag",
				'units': 'secs',
				'slope': 'both',
			},

			slave_relay_log_pos = {
				'description': "The position up to which the SQL thread has read and executed in the current relay log",
				'units': 'bytes',
				'slope': 'both',
			},

			slave_sql = {
				'description': "Slave SQL Running",
				'value_type': 'uint8',
				'units': 'True/False',
				'slope': 'both',
			},
		)

	if REPORT_INNODB:
		innodb_stats_descriptions = dict(
			innodb_active_transactions = {
				'description': "Active InnoDB transactions",
				'value_type':'uint',
				'units': 'txns',
				'slope': 'both',
			},

			innodb_current_transactions = {
				'description': "Current InnoDB transactions",
				'value_type':'uint',
				'units': 'txns',
				'slope': 'both',
			},

			innodb_buffer_pool_pages_data = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'pages',
			},

			innodb_data_fsyncs = {
				'description': "The number of fsync() operations",
				'value_type':'float',
				'units': 'fsyncs',
			},

			innodb_data_reads = {
				'description': "The number of data reads",
				'value_type':'float',
				'units': 'reads',
			},

			innodb_data_writes = {
				'description': "The number of data writes",
				'value_type':'float',
				'units': 'writes',
			},

			innodb_buffer_pool_pages_free = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'pages',
				'slope': 'both',
			},

			innodb_history_list = {
				'description': "InnoDB",
				'units': 'length',
				'slope': 'both',
			},

			innodb_ibuf_inserts = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'inserts',
			},

			innodb_ibuf_merged = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'recs',
			},

			innodb_ibuf_merges = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'merges',
			},

			innodb_log_bytes_flushed = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'bytes',
			},

			innodb_log_bytes_unflushed = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'bytes',
				'slope': 'both',
			},

			innodb_log_bytes_written = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'bytes',
			},

			innodb_log_writes = {
				'description': "The number of physical writes to the log file",
				'value_type':'float',
				'units': 'writes',
			},

			innodb_buffer_pool_pages_dirty = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'pages',
				'slope': 'both',
			},

			innodb_os_waits = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'waits',
			},

			innodb_pages_created = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'pages',
			},

			innodb_pages_read = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'pages',
			},

			innodb_pages_written = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'pages',
			},

			innodb_pending_aio_log_ios = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'ops',
			},

			innodb_pending_aio_sync_ios = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'ops',
			},

			innodb_pending_buffer_pool_flushes = {
				'description': "The number of pending buffer pool page-flush requests",
				'value_type':'uint',
				'units': 'reqs',
				'slope': 'both',
			},

			innodb_pending_chkp_writes = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'writes',
			},

			innodb_pending_ibuf_aio_reads = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'reads',
			},

			innodb_pending_log_flushes = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'reqs',
			},

			innodb_pending_log_writes = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'writes',
			},

			innodb_pending_normal_aio_reads = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'reads',
			},

			innodb_pending_normal_aio_writes = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'writes',
			},

			innodb_buffer_pool_pages_bytes = {
				'description': "The total size of buffer pool, in bytes",
				'value_type':'uint',
				'units': 'bytes',
				'slope': 'both',
			},

			innodb_buffer_pool_pages_total = {
				'description': "The total size of buffer pool, in pages",
				'value_type':'uint',
				'units': 'pages',
				'slope': 'both',
			},

			innodb_queries_inside = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'queries',
			},

			innodb_queries_queued = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'queries',
				'slope': 'both',
			},

			innodb_read_views = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'views',
			},

			innodb_rows_deleted = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'rows',
			},

			innodb_rows_inserted = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'rows',
			},

			innodb_rows_read = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'rows',
			},

			innodb_rows_updated = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'rows',
			},

			innodb_spin_rounds = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'spins',
				'slope': 'both',
			},

			innodb_spin_waits = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'spins',
				'slope': 'both',
			},

			innodb_transactions = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'txns',
			},

			innodb_transactions_purged = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'txns',
			},

			innodb_transactions_unpurged = {
				'description': "InnoDB",
				'value_type':'uint',
				'units': 'txns',
			},
		)

	update_stats(REPORT_INNODB, REPORT_MASTER, REPORT_SLAVE)

	time.sleep(MAX_UPDATE_TIME)
	update_stats(REPORT_INNODB, REPORT_MASTER, REPORT_SLAVE)

	for stats_descriptions in (innodb_stats_descriptions, master_stats_descriptions, misc_stats_descriptions, slave_stats_descriptions):
		for label in stats_descriptions:
			if mysql_stats.has_key(label):
				format = '%u'
				if stats_descriptions[label].has_key('value_type'):
					if stats_descriptions[label]['value_type'] == "float":
						format = '%f'

				d = {
					'name': 'mysql_' + label,
					'call_back': get_stat,
					'time_max': 60,
					'value_type': "uint",
					'units': "",
					'slope': "both",
					'format': format,
					'description': "http://search.mysql.com/search?q=" + label,
					'groups': 'mysql',
				}

				d.update(stats_descriptions[label])

				descriptors.append(d)

			else:
				logging.error("skipped " + label)

	#logging.debug(str(descriptors))
	return descriptors

def metric_cleanup():
	logging.shutdown()
	# pass

if __name__ == '__main__':
	from optparse import OptionParser
	import os

	logging.debug('running from cmd line')
	parser = OptionParser()
	parser.add_option("-H", "--Host", dest="host", help="Host running mysql", default="localhost")
	parser.add_option("-u", "--user", dest="user", help="user to connect as", default="")
	parser.add_option("-p", "--password", dest="passwd", help="password", default="")
	parser.add_option("-P", "--port", dest="port", help="port", default=3306, type="int")
	parser.add_option("-S", "--socket", dest="unix_socket", help="unix_socket", default="")
	parser.add_option("--no-innodb", dest="get_innodb", action="store_false", default=True)
	parser.add_option("--no-master", dest="get_master", action="store_false", default=True)
	parser.add_option("--no-slave", dest="get_slave", action="store_false", default=True)
	parser.add_option("-b", "--gmetric-bin", dest="gmetric_bin", help="path to gmetric binary", default="/usr/bin/gmetric")
	parser.add_option("-c", "--gmond-conf", dest="gmond_conf", help="path to gmond.conf", default="/etc/ganglia/gmond.conf")
	parser.add_option("-g", "--gmetric", dest="gmetric", help="submit via gmetric", action="store_true", default=False)
	parser.add_option("-q", "--quiet", dest="quiet", action="store_true", default=False)

	(options, args) = parser.parse_args()

	metric_init({
		'host': options.host,
		'passwd': options.passwd,
		'user': options.user,
		'port': options.port,
		'get_innodb': options.get_innodb,
		'get_master': options.get_master,
		'get_slave': options.get_slave,
		'unix_socket': options.unix_socket,
	})

	for d in descriptors:
		v = d['call_back'](d['name'])
		if not options.quiet:
			print ' %s: %s %s [%s]' % (d['name'], v, d['units'], d['description'])

		if options.gmetric:
			if d['value_type'] == 'uint':
				value_type = 'uint32'
			else:
				value_type = d['value_type']

			cmd = "%s --conf=%s --value='%s' --units='%s' --type='%s' --name='%s' --slope='%s'" % \
				(options.gmetric_bin, options.gmond_conf, v, d['units'], value_type, d['name'], d['slope'])
			os.system(cmd)


########NEW FILE########
__FILENAME__ = netapp_api
#!/usr/bin/python
#Name: netapp_api.py
#Desc: Uses Netapp Data Ontap API to get per volume latency & iops metrics.  Download the managemability SDK from now.netapp.com
#Author: Evan Fraser <evan.fraser@trademe.co.nz>
#Date: 13/08/2012

import sys
import time
import pprint
import unicodedata
import os

sys.path.append("/opt/netapp/lib/python/NetApp")
from NaServer import *

descriptors = list()
params = {}
filerdict = {}
FASMETRICS = {
    'time' : 0,
    'data' : {}
}
LAST_FASMETRICS = dict(FASMETRICS)
#This is the minimum interval between querying the RPA for metrics
FASMETRICS_CACHE_MAX = 10

def get_metrics(name):
    global FASMETRICS, LAST_FASMETRICS, FASMETRICS_CACHE_MAX, params
    max_records = 10
    metrics = {}
    if (time.time() - FASMETRICS['time']) > FASMETRICS_CACHE_MAX:
        
        for filer in filerdict.keys():
            s = NaServer(filerdict[filer]['ipaddr'], 1, 3)
            out = s.set_transport_type('HTTPS')
            if (out and out.results_errno() != 0) :
                r = out.results_reason()
                print ("Connection to filer failed: " + r + "\n")
                sys.exit(2)
            
            out = s.set_style('LOGIN')
            if (out and out.results_errno() != 0) :
                r = out.results_reason()
                print ("Connection to filer failed: " + r + "\n")
                sys.exit(2)
            out = s.set_admin_user(filerdict[filer]['user'], filerdict[filer]['password'])
            perf_in = NaElement("perf-object-get-instances-iter-start")
            #Hard coding volume object for testing
            obj_name = "volume"
            perf_in.child_add_string("objectname", obj_name)
            #Create object of type counters
            counters = NaElement("counters")
            #Add counter names to the object
            counters.child_add_string("counter", "total_ops")
            counters.child_add_string("counter", "avg_latency")
            counters.child_add_string("counter", "read_ops")
            counters.child_add_string("counter", "read_latency")
            counters.child_add_string("counter", "write_ops")
            counters.child_add_string("counter", "write_latency")

            perf_in.child_add(counters)

            #Invoke API
            out = s.invoke_elem(perf_in)

            if(out.results_status() == "failed"):
                print(out.results_reason() + "\n")
                sys.exit(2)
    
            iter_tag = out.child_get_string("tag")
            num_records = 1

            filername = filerdict[filer]['name']

            while(int(num_records) != 0):
                perf_in = NaElement("perf-object-get-instances-iter-next")
                perf_in.child_add_string("tag", iter_tag)
                perf_in.child_add_string("maximum", max_records)
                out = s.invoke_elem(perf_in)

                if(out.results_status() == "failed"):
                    print(out.results_reason() + "\n")
                    sys.exit(2)

                num_records = out.child_get_int("records")
	
                if(num_records > 0) :
                    instances_list = out.child_get("instances")            
                    instances = instances_list.children_get()

                    for inst in instances:
                        inst_name = unicodedata.normalize('NFKD',inst.child_get_string("name")).encode('ascii','ignore')
                        counters_list = inst.child_get("counters")
                        counters = counters_list.children_get()

                        for counter in counters:
                            counter_name = unicodedata.normalize('NFKD',counter.child_get_string("name")).encode('ascii','ignore')         
                            counter_value = counter.child_get_string("value")
                            counter_unit = counter.child_get_string("unit")           
                            metrics[filername + '_vol_' + inst_name + '_' + counter_name] = float(counter_value)
        # update cache
        LAST_FASMETRICS = dict(FASMETRICS)
        FASMETRICS = {
            'time': time.time(),
            'data': metrics
            }


    else: 
        metrics = FASMETRICS['data']
    #print name
    #calculate change in values and return
    if 'total_ops' in name:
        try:
            delta = float(FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name])/(FASMETRICS['time'] - LAST_FASMETRICS['time'])
            if delta < 0:
                print "Less than 0"
                delta = 0
        except StandardError:
            delta = 0
        #This is the Operations per second
        return delta

    elif 'avg_latency' in name:
        try: 
            #T1 and T2
            #(T2_lat - T1_lat) / (T2_ops - T1_ops)
            #Find the metric name of the base counter
            total_ops_name = name.replace('avg_latency', 'total_ops')
            #Calculate latency in time (div 100 to change to ms)
            return float((FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name]) / (FASMETRICS['data'][total_ops_name] -LAST_FASMETRICS['data'][total_ops_name])) / 100
        except StandardError:
            return 0
    elif 'read_ops' in name:

        try:
            delta = float(FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name])/(FASMETRICS['time'] - LAST_FASMETRICS['time'])
            if delta < 0:
                print "Less than 0"
                delta = 0
        except StandardError:
            delta = 0
        return delta

    elif 'read_latency' in name:
        try: 
            read_ops_name = name.replace('read_latency', 'read_ops')
            return float((FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name]) / (FASMETRICS['data'][read_ops_name] -LAST_FASMETRICS['data'][read_ops_name])) / 100
        except StandardError:
            return 0
    elif 'write_ops' in name:
        try:
            delta = float(FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name])/(FASMETRICS['time'] - LAST_FASMETRICS['time'])
            if delta < 0:
                print "Less than 0"
                delta = 0
        except StandardError:
            delta = 0
        return delta

    elif 'write_latency' in name:
        try: 
            write_ops_name = name.replace('write_latency', 'write_ops')
            return float((FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name]) / (FASMETRICS['data'][write_ops_name] -LAST_FASMETRICS['data'][write_ops_name])) / 100
        except StandardError:
            return 0
            

    return 0    
        


def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d
    
def define_metrics(Desc_Skel,params):
    max_records = 10
    for filer in params.keys():
        s = NaServer(params[filer]['ipaddr'], 1, 3)
        out = s.set_transport_type('HTTPS')
        if (out and out.results_errno() != 0) :
            r = out.results_reason()
            print ("Connection to filer failed: " + r + "\n")
            sys.exit(2)
            
        out = s.set_style('LOGIN')
        if (out and out.results_errno() != 0) :
            r = out.results_reason()
            print ("Connection to filer failed: " + r + "\n")
            sys.exit(2)
        out = s.set_admin_user(params[filer]['user'], params[filer]['password'])
        perf_in = NaElement("perf-object-get-instances-iter-start")
        #Hard coded volume, only volume stats gathered at present
        obj_name = "volume"
        perf_in.child_add_string("objectname", obj_name)
        #Create object of type counters
        counters = NaElement("counters")
        #Add counter names to the object
        counters.child_add_string("counter", "total_ops")
        counters.child_add_string("counter", "avg_latency")
        counters.child_add_string("counter", "read_ops")
        counters.child_add_string("counter", "read_latency")
        counters.child_add_string("counter", "write_ops")
        counters.child_add_string("counter", "write_latency")

        perf_in.child_add(counters)

        #Invoke API
        out = s.invoke_elem(perf_in)

        if(out.results_status() == "failed"):
            print(out.results_reason() + "\n")
            sys.exit(2)
    
        iter_tag = out.child_get_string("tag")
        num_records = 1
        filername = params[filer]['name']

        while(int(num_records) != 0):
            perf_in = NaElement("perf-object-get-instances-iter-next")
            perf_in.child_add_string("tag", iter_tag)
            perf_in.child_add_string("maximum", max_records)
            out = s.invoke_elem(perf_in)

            if(out.results_status() == "failed"):
                print(out.results_reason() + "\n")
                sys.exit(2)

            num_records = out.child_get_int("records")
	
            if(num_records > 0) :
                instances_list = out.child_get("instances")            
                instances = instances_list.children_get()

                for inst in instances:
                    inst_name = unicodedata.normalize('NFKD',inst.child_get_string("name")).encode('ascii','ignore')
                    #print ("Instance = " + inst_name + "\n")
                    counters_list = inst.child_get("counters")
                    counters = counters_list.children_get()

                    for counter in counters:
                        counter_name = unicodedata.normalize('NFKD',counter.child_get_string("name")).encode('ascii','ignore')
                        counter_value = counter.child_get_string("value")
                        counter_unit = counter.child_get_string("unit")
                        if 'total_ops' in counter_name:
                            descriptors.append(create_desc(Desc_Skel, {
                                        "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                                        "units"       : 'iops',
                                        "description" : "volume iops",
                                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                        "groups"      : "iops"
                                        }))
                        elif 'avg_latency' in counter_name:
                            descriptors.append(create_desc(Desc_Skel, {
                                        "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                                        "units"       : 'ms',
                                        "description" : "volume avg latency",
                                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                        "groups"      : "latency"
                                        }))
                        elif 'read_ops' in counter_name:
                            descriptors.append(create_desc(Desc_Skel, {
                                        "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                                        "units"       : 'iops',
                                        "description" : "volume read iops",
                                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                        "groups"      : "iops"
                                        }))
                        elif 'read_latency' in counter_name:
                            descriptors.append(create_desc(Desc_Skel, {
                                        "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                                        "units"       : 'ms',
                                        "description" : "volume read latency",
                                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                        "groups"      : "latency"
                                        }))
                        elif 'write_ops' in counter_name:
                            descriptors.append(create_desc(Desc_Skel, {
                                        "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                                        "units"       : 'iops',
                                        "description" : "volume write iops",
                                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                        "groups"      : "iops"
                                        }))
                        elif 'write_latency' in counter_name:
                            descriptors.append(create_desc(Desc_Skel, {
                                        "name"        : filername + '_vol_' + inst_name + '_' + counter_name,
                                        "units"       : 'ms',
                                        "description" : "volume write latency",
                                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                        "groups"      : "latency"
                                        }))
                        
    return descriptors

def metric_init(params):
    global descriptors,filerdict
    print 'netapp_stats] Received the following parameters'
    pprint.pprint(params)
    params = {
        'filer1' : {
            'name' : 'filer1.localdomain',
            'ipaddr' : '192.168.1.100',
            'user' : 'root',
            'password' : 'password',
              },
        }

    filerdict = dict(params)
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_metrics,
        'time_max'    : 60,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'netiron',
        'spoof_host'  : 'XXX',
        }  

    # Run define_metrics
    descriptors = define_metrics(Desc_Skel,params)

    return descriptors

# For CLI Debugging:
if __name__ == '__main__':
    #global params
    params = {
        'filer1' : {
            'name' : 'filer1.localdomain',
            'ipaddr' : '192.168.1.100',
            'user' : 'root',
            'password' : 'password',
              },
        }
    descriptors = metric_init(params)
    pprint.pprint(descriptors)
    #print len(descriptors)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            #print v
            print 'value for %s is %.2f' % (d['name'],  v)        
        print 'Sleeping 5 seconds'
        time.sleep(5)

########NEW FILE########
__FILENAME__ = netapp_cmode_api
#!/usr/bin/python
#Name: netapp_api_cmode.py
#Desc: Uses Netapp Data Ontap API to get per volume latency & iops metrics.  Download the managemability SDK from now.netapp.com
#Author: Evan Fraser <evan.fraser@trademe.co.nz>
#Date: 13/08/2012
#Updated 26/03/2014: Now polls each filer as a separate thread and now only supports Clustered ONTAP 8.2+
#Updated 02/04/2014: Now retrieves per volume space and file(inode) metrics
#Updated 03/04/2014: Now retrieves qtree quota usage metrics

import sys
import time
import pprint
import unicodedata
import threading
import os
import time

sys.path.append("/opt/netapp/sdk/lib/python/NetApp")
from NaServer import *

descriptors = list()
params = {}
filerdict = {}
FASMETRICS = {
    'time' : 0,
    'data' : {}
}
LAST_FASMETRICS = dict(FASMETRICS)
#metrics = {}
#This is the minimum interval between querying the RPA for metrics
FASMETRICS_CACHE_MAX = 10

class GetMetricsThread(threading.Thread):
    def __init__(self, MetricName, FilerName):
        self.filer_metrics = None
        self.MetricName = MetricName
        self.FilerName = FilerName
        self.instances = None
        self.ClusterName = filerdict[self.FilerName]['name']
        self.volume_capacity_obj = None
        self.quota_obj = None
        super(GetMetricsThread, self).__init__()


    def volume_perf_metrics(self, s):
        # In class function to get volume perf metrics

        #In C-mode, perf-object-get-instances-iter-start doesn't exist
        # Also need to get list of instance names to provide to the perf-object-get-instances now.
        #Get list of volume instances
        obj_name = "volume"
        instance_in = NaElement("perf-object-instance-list-info-iter")
        instance_in.child_add_string("objectname", obj_name)
        #Invoke API
        out = s.invoke_elem(instance_in)
        if(out.results_status() == "failed"):
            print("Invoke failed: " + out.results_reason() + "\n")
            sys.exit(2)
        
        #create an object for all the instances which we will pass to the perf-object-get-instances below
        instance_obj = NaElement("instances")
        instance_list = out.child_get("attributes-list")
        instances = instance_list.children_get()
        instance_names = []
        for i in instances:
            instance_obj.child_add_string("instance", i.child_get_string("name"))

        #Get perf objects for each instance
            perf_in = NaElement("perf-object-get-instances")
            perf_in.child_add_string("objectname", obj_name)
            perf_in.child_add(instance_obj)

        #Create object of type counters
        counters = NaElement("counters")
        #Add counter names to the object
        counter_name_list = ["total_ops","avg_latency","read_ops","read_latency","write_ops","write_latency"]
        for c in counter_name_list:
            counters.child_add_string("counter", c)
            perf_in.child_add(counters)

        #Invoke API
        out = s.invoke_elem(perf_in)

        if(out.results_status() == "failed"):
            print(out.results_reason() + "\n")
            sys.exit(2)

        #self.clusterName = filerdict[filer]['name']
    
        instances_list = out.child_get("instances")            
        instances = instances_list.children_get()
        self.instances = instances

    def quota_metrics(self, s):
        na_server_obj = s

        api = NaElement("quota-report-iter")
        api.child_add_string("max-records", "999")

        out = na_server_obj.invoke_elem(api)
        if(out.results_status() == "failed"):
            print("Invoke failed: " + out.results_reason() + "\n")
            sys.exit(2)
        #pprint(out)
        num_records = out.child_get_string("num-records")

        quota_list = out.child_get("attributes-list")
        
        #Check if quota_list returned is empty, if so, skip quota metrics for this cluster
        if quota_list is None:
            return
        quotas = quota_list.children_get()
        self.quota_obj = quotas

        return

    def volume_capacity_metrics(self, s):
        # Function to perform API queries to get volume capacity metrics.
        na_server_obj = s
        #Limit the volume attributes we retrieve to the inode and space metrics
        api = NaElement("volume-get-iter")

        xi = NaElement("desired-attributes")
        api.child_add(xi)
        api.child_add_string("max-records", "999")


        xi1 = NaElement("volume-attributes")
        xi.child_add(xi1)


        xi2 = NaElement("volume-id-attributes")
        xi1.child_add(xi2)

        xi3 = NaElement("volume-space-attributes")
        xi1.child_add(xi3)

        xi4 = NaElement("volume-inode-attributes")
        xi1.child_add(xi4)

        out = na_server_obj.invoke_elem(api)
        if(out.results_status() == "failed"):
            print("Invoke failed: " + out.results_reason() + "\n")
            sys.exit(2)

        vol_list = out.child_get("attributes-list")
        volumes = vol_list.children_get()

        self.volume_capacity_obj = volumes

        return
        
    def run(self):
        self.filer_metrics = {}
        metric = self.MetricName
        filer = self.FilerName
        s = NaServer(filerdict[filer]['ipaddr'], 1, 3)
        out = s.set_transport_type('HTTPS')
        if (out and out.results_errno() != 0) :
            r = out.results_reason()
            print ("Connection to filer failed: " + r + "\n")
            sys.exit(2)
            
        out = s.set_style('LOGIN')
        if (out and out.results_errno() != 0) :
            r = out.results_reason()
            print ("Connection to filer failed: " + r + "\n")
            sys.exit(2)
        out = s.set_admin_user(filerdict[filer]['user'], filerdict[filer]['password'])

        #Get the volume performance metrics
        self.volume_perf_metrics(s)
        self.volume_capacity_metrics(s)
        self.quota_metrics(s)

    #Function within the class for updating the metrics
    def update_metrics(self):
        clustername = self.ClusterName

        for inst in self.instances:
            inst_name = unicodedata.normalize('NFKD',inst.child_get_string("name")).encode('ascii','ignore')
            counters_list = inst.child_get("counters")
            counters = counters_list.children_get()

            for counter in counters:
                counter_name = unicodedata.normalize('NFKD',counter.child_get_string("name")).encode('ascii','ignore')         
                counter_value = counter.child_get_string("value")
                counter_unit = counter.child_get_string("unit")           
                self.filer_metrics[clustername + '_vol_' + inst_name + '_' + counter_name] = float(counter_value)

        for vol in self.volume_capacity_obj:

            vol_id = vol.child_get("volume-id-attributes")
            vol_name = unicodedata.normalize('NFKD',vol_id.child_get_string("name")).encode('ascii','ignore')
            vserver_name = unicodedata.normalize('NFKD',vol_id.child_get_string("owning-vserver-name")).encode('ascii','ignore')

            vol_inode = vol.child_get("volume-inode-attributes")
            vol_files_used = unicodedata.normalize('NFKD',vol_inode.child_get_string("files-used")).encode('ascii','ignore')
            vol_files_total = unicodedata.normalize('NFKD',vol_inode.child_get_string("files-total")).encode('ascii','ignore')
            vol_files_used_percent = float(vol_files_used) / float(vol_files_total) * 100

            vol_space = vol.child_get("volume-space-attributes")
            vol_size_used = unicodedata.normalize('NFKD',vol_space.child_get_string("size-used")).encode('ascii','ignore')
            vol_size_total = unicodedata.normalize('NFKD',vol_space.child_get_string("size-total")).encode('ascii','ignore')
            vol_size_used_percent = float(vol_size_used) / float(vol_size_total) * 100

            self.filer_metrics[clustername + '_vol_' +vserver_name + '_' + vol_name + '_' + 'files_used'] = float(vol_files_used)
            self.filer_metrics[clustername + '_vol_' +vserver_name + '_' + vol_name + '_' + 'files_total'] = float(vol_files_total)
            self.filer_metrics[clustername + '_vol_' + vserver_name + '_' + vol_name + '_' + 'files_used_percent'] = vol_files_used_percent
            self.filer_metrics[clustername + '_vol_' + vserver_name + '_' + vol_name + '_' + 'size_used'] = float(vol_size_used)
            self.filer_metrics[clustername + '_vol_' + vserver_name + '_' + vol_name + '_' + 'size_total'] = float(vol_size_total)
            self.filer_metrics[clustername + '_vol_' + vserver_name + '_' + vol_name + '_' + 'size_used_percent'] = vol_size_used_percent

        
        #Only do quota metrics if cluster actually has quotas enabled
        if self.quota_obj is not None:

            for q in self.quota_obj:
                q_qtree_name = unicodedata.normalize('NFKD',unicode(q.child_get_string("tree"))).encode('ascii','ignore').replace(" ", "_")
                q_quota_used = unicodedata.normalize('NFKD',q.child_get_string("disk-used")).encode('ascii','ignore')
                q_vserver_name = unicodedata.normalize('NFKD',q.child_get_string("vserver")).encode('ascii','ignore')
                q_volume_name = unicodedata.normalize('NFKD',q.child_get_string("volume")).encode('ascii','ignore')
                self.filer_metrics[clustername + '_vol_' + q_vserver_name + '_' + q_volume_name + '_' + q_qtree_name + '_' + 'quota_used'] = float(q_quota_used)


    #Function within the class for defining the metrics for ganglia
    def define_metrics(self,Desc_Skel,params):
        
        clustername = self.ClusterName
        filer = self.FilerName
        for inst in self.instances:
            inst_name = unicodedata.normalize('NFKD',inst.child_get_string("name")).encode('ascii','ignore')
            counters_list = inst.child_get("counters")
            counters = counters_list.children_get()

            for counter in counters:
                counter_name = unicodedata.normalize('NFKD',counter.child_get_string("name")).encode('ascii','ignore')
                counter_value = counter.child_get_string("value")
                counter_unit = counter.child_get_string("unit")

                if 'total_ops' in counter_name:
                    descriptors.append(create_desc(Desc_Skel, {
                                "name"        : clustername + '_vol_' + inst_name + '_' + counter_name,
                                "units"       : 'iops',
                                "description" : "volume iops",
                                "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                "groups"      : "iops"
                                }))
                elif 'avg_latency' in counter_name:
                    descriptors.append(create_desc(Desc_Skel, {
                                "name"        : clustername + '_vol_' + inst_name + '_' + counter_name,
                                "units"       : 'ms',
                                "description" : "volume avg latency",
                                "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                "groups"      : "latency"
                                }))
                elif 'read_ops' in counter_name:
                    descriptors.append(create_desc(Desc_Skel, {
                                "name"        : clustername + '_vol_' + inst_name + '_' + counter_name,
                                "units"       : 'iops',
                                "description" : "volume read iops",
                                "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                "groups"      : "iops"
                                }))
                elif 'read_latency' in counter_name:
                    descriptors.append(create_desc(Desc_Skel, {
                                "name"        : clustername + '_vol_' + inst_name + '_' + counter_name,
                                "units"       : 'ms',
                                "description" : "volume read latency",
                                "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                "groups"      : "latency"
                                }))
                elif 'write_ops' in counter_name:
                    descriptors.append(create_desc(Desc_Skel, {
                                "name"        : clustername + '_vol_' + inst_name + '_' + counter_name,
                                "units"       : 'iops',
                                "description" : "volume write iops",
                                "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                "groups"      : "iops"
                                }))
                elif 'write_latency' in counter_name:
                    descriptors.append(create_desc(Desc_Skel, {
                                "name"        : clustername + '_vol_' + inst_name + '_' + counter_name,
                                "units"       : 'ms',
                                "description" : "volume write latency",
                                "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                                "groups"      : "latency"
                                }))


        for vol in self.volume_capacity_obj:

            vol_id = vol.child_get("volume-id-attributes")
            vol_name = unicodedata.normalize('NFKD',vol_id.child_get_string("name")).encode('ascii','ignore')
            vserver_name = unicodedata.normalize('NFKD',vol_id.child_get_string("owning-vserver-name")).encode('ascii','ignore')
            
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : clustername + '_vol_' + vserver_name + '_' + vol_name + '_' + 'files_used',
                        "units"       : 'inodes',
                        "description" : "volume files used",
                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                        "groups"      : "inodes"
                        }))
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : clustername + '_vol_' + vserver_name + '_' + vol_name + '_' + 'files_total',
                        "units"       : 'inodes',
                        "description" : "volume files total",
                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                        "groups"      : "inodes"
                        }))
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : clustername + '_vol_' + vserver_name + '_' + vol_name + '_' + 'files_used_percent',
                        "units"       : 'percent',
                        "description" : "volume inodes percent used",
                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                        "groups"      : "inodes"
                        }))
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : clustername + '_vol_' + vserver_name + '_' + vol_name + '_' + 'size_used',
                        "units"       : 'Bytes',
                        "description" : "volume bytes used",
                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                        "groups"      : "capacity"
                        }))
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : clustername + '_vol_' + vserver_name + '_' + vol_name + '_' + 'size_total',
                        "units"       : 'Bytes',
                        "description" : "volume size in bytes",
                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                        "groups"      : "capacity"
                        }))
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : clustername + '_vol_' + vserver_name + '_' + vol_name + '_' + 'size_used_percent',
                        "units"       : 'percent',
                        "description" : "volume capacity percent used",
                        "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                        "groups"      : "capacity"
                        }))
            
        if self.quota_obj is not None:
            for q in self.quota_obj:
                q_qtree_name = unicodedata.normalize('NFKD',unicode(q.child_get_string("tree"))).encode('ascii','ignore').replace(" ", "_")
                #q_quota_used = float(q.child_get_string("disk-used"))
                q_vserver_name = unicodedata.normalize('NFKD',q.child_get_string("vserver")).encode('ascii','ignore')
                q_volume_name = unicodedata.normalize('NFKD',q.child_get_string("volume")).encode('ascii','ignore')
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : clustername + '_vol_' + q_vserver_name + '_' + q_volume_name + '_' + q_qtree_name + '_' + 'quota_used',
                            "units"       : 'Bytes',
                            "description" : "quota space used",
                            "spoof_host"  : params[filer]['ipaddr'] + ':' + params[filer]['name'],
                            "groups"      : "quotas"
                            }))

            #print q_qtree_name + " ",q_quota_used, " ", q_vserver_name, " ", q_volume_name

def get_metrics(name):
    global FASMETRICS, LAST_FASMETRICS, FASMETRICS_CACHE_MAX, params
    max_records = 10
    threads = []
    metrics = {}
    if (time.time() - FASMETRICS['time']) > FASMETRICS_CACHE_MAX:
        #start = time.time()
        for filer in filerdict.keys():
            # Execute threads to gather metrics from each filer
            thread = GetMetricsThread(name,filer)
            thread.start()
            threads.append(thread)

        #Wait for the threads to return here
        for t in threads:
            t.join()
            t.update_metrics()
            metrics.update(t.filer_metrics)
        #end = time.time()
        #print "elapsed time was: ",(end - start)

        # update cache
        LAST_FASMETRICS = dict(FASMETRICS)
        FASMETRICS = {
            'time': time.time(),
            'data': metrics
            }
    else: 
        metrics = FASMETRICS['data']

    #calculate change in values and return
    if 'total_ops' in name:
        try:
            delta = float(FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name])/(FASMETRICS['time'] - LAST_FASMETRICS['time'])
            if delta < 0:
                print "Less than 0"
                delta = 0
        except StandardError:
            delta = 0
        #This is the Operations per second
        return delta

    elif 'avg_latency' in name:
        try: 
            #T1 and T2
            #(T2_lat - T1_lat) / (T2_ops - T1_ops)
            #Find the metric name of the base counter
            total_ops_name = name.replace('avg_latency', 'total_ops')
            #Calculate latency in time (div 100 to change to ms)
            return float((FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name]) / (FASMETRICS['data'][total_ops_name] -LAST_FASMETRICS['data'][total_ops_name])) / 1000
        except StandardError:
            return 0
    elif 'read_ops' in name:

        try:
            delta = float(FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name])/(FASMETRICS['time'] - LAST_FASMETRICS['time'])
            if delta < 0:
                print "Less than 0"
                delta = 0
        except StandardError:
            delta = 0
        return delta

    elif 'read_latency' in name:
        try: 
            read_ops_name = name.replace('read_latency', 'read_ops')
            return float((FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name]) / (FASMETRICS['data'][read_ops_name] -LAST_FASMETRICS['data'][read_ops_name])) / 1000
        except StandardError:
            return 0
    elif 'write_ops' in name:
        try:
            delta = float(FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name])/(FASMETRICS['time'] - LAST_FASMETRICS['time'])
            if delta < 0:
                print "Less than 0"
                delta = 0
        except StandardError:
            delta = 0
        return delta

    elif 'write_latency' in name:
        try: 
            write_ops_name = name.replace('write_latency', 'write_ops')
            return float((FASMETRICS['data'][name] - LAST_FASMETRICS['data'][name]) / (FASMETRICS['data'][write_ops_name] -LAST_FASMETRICS['data'][write_ops_name])) / 1000
        except StandardError:
            return 0

    elif 'files_used' in name:
        try:
            result = float(FASMETRICS['data'][name])
        except StandardError:
            result = 0
            
        return result
    elif 'files_total' in name:
        try:
            result = float(FASMETRICS['data'][name])
        except StandardError:
            result = 0
            
        return result
            
    elif 'size_used' in name:
         try:
             result = float(FASMETRICS['data'][name])
         except StandardError:
             result = 0
         return result

    elif 'size_total' in name:
         try:
             result = float(FASMETRICS['data'][name])
         except StandardError:
             result = 0
         return result
    elif 'quota_used' in name:
         try:
             result = float(FASMETRICS['data'][name]) * 1024
         except StandardError:
             result = 0
         return result

    return 0    
        


def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d
    

    

def define_metrics(Desc_Skel,params):
    global descriptors
    #ObjectTypeList = ["lif:vserver"]
    ObjectTypeList = ["volume"]

    threads = []
    for filer in params.keys():
        #call define_metrics_thread as separate threads for each filer
        blankname = ""
        thread = GetMetricsThread(blankname,filer)
        thread.start()
        threads.append(thread)

    for t in threads:
        t.join()
        t.define_metrics(Desc_Skel,params)
            
    return descriptors

def metric_init(params):
    global descriptors,filerdict
    print 'netapp_stats] Received the following parameters'
    params = {
        'filer1' : {
            'name' : 'cluster1.localdomain',
            'ipaddr' : '192.168.1.100',
            'user' : 'username',
            'password' : 'password',
              },
        'filer2' : {
            'name' : 'cluster2.localdomain',
            'ipaddr' : '192.168.1.200',
            'user' : 'username',
            'password' : 'password',
              },
        }

    filerdict = dict(params)
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_metrics,
        'time_max'    : 60,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'netiron',
        'spoof_host'  : 'XXX',
        }  


    descriptors = define_metrics(Desc_Skel,params)

    return descriptors

# For CLI Debugging:
if __name__ == '__main__':
    #global params
    params = {}
    descriptors = metric_init(params)
    pprint.pprint(descriptors)
    #print len(descriptors)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            #print v
            print 'value for %s is %.2f' % (d['name'],  v)        
        print 'Sleeping 5 seconds'
        time.sleep(5)

########NEW FILE########
__FILENAME__ = conntrack
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Conntrack gmond module for Ganglia
#
# Copyright (C) 2011 by Michael T. Conigliaro <mike [at] conigliaro [dot] org>.
# All rights reserved.
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
import time
import copy

NAME_PREFIX = 'conntrack_'
PARAMS = {
    'stats_command' : '/usr/sbin/conntrack -S'
}
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d


def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

        # get raw metric data
        io = os.popen(PARAMS['stats_command'])

        # convert to dict
        metrics = {}
        for line in io.readlines():
            values = line.split()[:2]
            try:
                metrics[values[0]] = int(values[1])
            except ValueError:
                metrics[values[0]] = 0

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]

def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    # get delta
    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        delta = float(curr_metrics['data'][name] - last_metrics['data'][name])/(curr_metrics['time'] - last_metrics['time'])
        if delta < 0:
            print "Less than 0"
            delta = 0
    except StandardError:
        delta = 0

    return delta


def get_cache_hit_ratio(name):
    """Return cache hit ratio"""

    try:
        result = get_delta(NAME_PREFIX + 'cache_hit') / get_delta(NAME_PREFIX + 'client_req') * 100
    except ZeroDivisionError:
        result = 0

    return result


def metric_init(lparams):
    """Initialize metric descriptors"""

    global PARAMS, Desc_Skel

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]

    # define descriptors
    time_max = 60

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : 'XXX',
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%f',
        'units'       : 'XXX',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'conntrack',
        }

    descriptors = []
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'entries',
                "call_back"  : get_value,
                "units"      : "entries",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'searched',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'found',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'new',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'invalid',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'ignore',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'delete',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'delete_list',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'insert',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'insert_failed',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'drop',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'early_drop',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'icmp_error',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'expect_new',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'expect_create',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'expect_delete',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                }))
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'search_restart',
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "",
                })) 

    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            print (('%s = %s') % (d['name'], d['format'])) % (d['call_back'](d['name']))
        print 'Sleeping 15 seconds'
        time.sleep(15)

########NEW FILE########
__FILENAME__ = iface
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import traceback
import os
import threading
import time
import socket
import select

descriptors     = list()
Desc_Skel       = {}
_Worker_Thread  = None
_Lock           = threading.Lock() # synchronization lock
Debug           = False

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "iface: " + f % v

def floatable(str):
    try:
        float(str)
        return True
    except:
        return False

class UpdateMetricThread(threading.Thread):
    def __init__(self, params):
        threading.Thread.__init__(self)

        self.running        = False
        self.shuttingdown   = False
        self.refresh_rate   = params["refresh_rate"]
        self.mp             = params["metrix_prefix"]
        self.metric         = {}
        self.last_metric    = {}

    def shutdown(self):
        self.shuttingdown = True

        if not self.running:
            return

        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            updated = self.update_metric()
            _Lock.release()

            if not updated:
                time.sleep(0.2)
            else:
                if "time" in self.last_metric:
                    dprint("metric delta period %.3f" % (self.metric['time'] - self.last_metric['time']))


        self.running = False

    def update_metric(self):
        if "time" in self.metric:
            if (time.time() - self.metric['time']) < self.refresh_rate:
                return False

        dprint("updating metrics")

        self.last_metric = self.metric.copy()

        try:
            f = open('/proc/net/dev', 'r')
        except IOError:
            dprint("unable to open /proc/net/dev")
            return False

        for line in f:
            if re.search(':', line):
                tokens  = re.split('\s+', line.strip())
                iface   = tokens[0].strip(':')

                self.metric.update({
                    'time'                                          : time.time(),
                    '%s_%s_%s' % (self.mp, iface, 'rx_bytes')       : int(tokens[1]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_packets')     : int(tokens[2]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_errs')        : int(tokens[3]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_drop')        : int(tokens[4]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_fifo')        : int(tokens[5]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_frame')       : int(tokens[6]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_compressed')  : int(tokens[7]),
                    '%s_%s_%s' % (self.mp, iface, 'rx_multicast')   : int(tokens[8]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_bytes')       : int(tokens[9]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_packets')     : int(tokens[10]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_errs')        : int(tokens[11]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_drop')        : int(tokens[12]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_fifo')        : int(tokens[13]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_frame')       : int(tokens[14]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_compressed')  : int(tokens[15]),
                    '%s_%s_%s' % (self.mp, iface, 'tx_multicast')   : int(tokens[16]),
                })

        return True

    def metric_delta(self, name):
        val = 0

        if name in self.metric and name in self.last_metric:
            _Lock.acquire()
            if self.metric['time'] - self.last_metric['time'] != 0:
                val = (self.metric[name] - self.last_metric[name]) / (self.metric['time'] - self.last_metric['time'])
            _Lock.release()

        return float(val)

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_delta,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.0f',
        'units'       : 'XXX',
        'slope'       : 'XXX', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'network'
    }

    
    params["refresh_rate"]  = params["refresh_rate"] if "refresh_rate" in params else 15
    params["metrix_prefix"] = params["metrix_prefix"] if "metrix_prefix" in params else "iface"
    Debug                   = params["debug"] if "debug" in params else False

    dprint("debugging has been turned on")

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    mp = params["metrix_prefix"]

    try:
        f = open("/proc/net/dev", 'r')
    except IOError:
        return

    for line in f:
        if re.search(':', line):
            tokens  = re.split('\s+', line.strip())
            iface   = tokens[0].strip(':')

            for way in ('tx', 'rx'):
                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'bytes'),
                    "units"      : "bytes/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s bytes per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'packets'),
                    "units"      : "packets/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s packets per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'errs'),
                    "units"      : "errs/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s errors per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'drop'),
                    "units"      : "drop/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s drop per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'fifo'),
                    "units"      : "fifo/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s fifo per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'frame'),
                    "units"      : "frame/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s frame per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'compressed'),
                    "units"      : "compressed/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s compressed per seconds' % (iface, way.upper())
                }))

                descriptors.append(create_desc(Desc_Skel, {
                    "name"       : '%s_%s_%s_%s' % (mp, iface, way, 'multicast'),
                    "units"      : "multicast/s",
                    "slope"      : "both",
                    "description": 'Interface %s %s multicast per seconds' % (iface, way.upper())
                }))

    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_delta(name):
    return _Worker_Thread.metric_delta(name)

def metric_cleanup():
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    params = {
        "debug"         : True,
        "refresh_rate"  : 15
    }

    try:
        metric_init(params)

        while True:
            time.sleep(params['refresh_rate'])
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is ' + d['format']) % (d['name'],  v)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)

########NEW FILE########
__FILENAME__ = multi_interface
import re
import time
import sys
import os
import copy

PARAMS = {}

METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

INTERFACES = []
descriptors = []

stats_tab = {
    "rx_bytes"  : 0,
    "rx_pkts"   : 1,
    "rx_errs"   : 2,
    "rx_drops"  : 3,
    "tx_bytes" : 8,
    "tx_pkts"  : 9,
    "tx_errs"  : 10,
    "tx_drops" : 11,
}

# Where to get the stats from
net_stats_file = "/proc/net/dev"

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors
    global INTERFACES
    
#    INTERFACES = params.get('interfaces')
    watch_interfaces = params.get('interfaces')
    excluded_interfaces = params.get('excluded_interfaces')
    get_interfaces(watch_interfaces,excluded_interfaces)

#    print INTERFACES
    time_max = 60

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.0f',
        'units'       : '/s',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'network',
        }


    for dev in INTERFACES:
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "rx_bytes_" + dev,
                    "units"       : "bytes/sec",
                    "description" : "received bytes per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "rx_pkts_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "received packets per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "rx_errs_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "received error packets per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "rx_drops_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "receive packets dropped per sec",
                    }))
    
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "tx_bytes_" + dev,
                    "units"       : "bytes/sec",
                    "description" : "transmitted bytes per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "tx_pkts_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "transmitted packets per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "tx_errs_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "transmitted error packets per sec",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "tx_drops_" + dev,
                    "units"       : "pkts/sec",
                    "description" : "transmitted dropped packets per sec",
                    }))

    if params['send_aggregate_bytes_packets']:
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "pkts_in",
                    "units"       : "pkts/sec",
                    "call_back"   : get_aggregates,
                    "description" : "Packets Received",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "pkts_out",
                    "units"       : "pkts/sec",
                    "call_back"   : get_aggregates,
                    "description" : "Packets Sent",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "bytes_in",
                    "units"       : "bytes/sec",
                    "call_back"   : get_aggregates,
                    "description" : "Bytes Received",
                    }))
        descriptors.append(create_desc(Desc_Skel, {
                    "name"        : "bytes_out",
                    "units"       : "bytes/sec",
                    "call_back"   : get_aggregates,
                    "description" : "Bytes Sent",
                    }))

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass
    
###################################################################################
# Build a list of interfaces
###################################################################################    
def get_interfaces(watch_interfaces, excluded_interfaces):
   global INTERFACES
   if_excluded = 0
        
   # check if particular interfaces have been specifieid. Watch only those
   if watch_interfaces != "":
      INTERFACES = watch_interfaces.split(" ")      
   else:
      if excluded_interfaces != "":
         excluded_if_list = excluded_interfaces.split(" ")
      f = open(net_stats_file, "r")
      for line in f:
         # Find only lines with :
         if re.search(":", line):
            a = line.split(":")
            dev_name = a[0].lstrip()
                    
            # Determine if interface is excluded by name or regex
            for ex in excluded_if_list:
               if re.match(ex,dev_name):
                  if_excluded = 1

            if not if_excluded:
               INTERFACES.append(dev_name)
            if_excluded = 0
   return 0


###################################################################################
# Returns aggregate values for pkts and bytes sent and received. It should be
# used to override the default Ganglia mod_net module. It will generate bytes_in
# bytes_out, pkts_in and pkts_out.
###################################################################################
def get_aggregates(name):

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()
    
    # Determine the index of metric we need
    if name == "bytes_in":
      index = stats_tab["rx_bytes"]
    elif name == "bytes_out":
      index = stats_tab["tx_bytes"]
    elif name == "pkts_out":
      index = stats_tab["tx_pkts"]
    elif name == "pkts_in":
      index = stats_tab["rx_pkts"]
    else:
      return 0

    sum = 0
    
    # Loop through the list of interfaces we care for
    for iface in INTERFACES:
      
      try:
	delta = (float(curr_metrics['data'][iface][index]) - float(last_metrics['data'][iface][index])) /(curr_metrics['time'] - last_metrics['time'])
	if delta < 0:
	  print name + " is less 0"
	  delta = 0
      except KeyError:
	delta = 0.0      
    
      sum += delta

    return sum



def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	try:
	    file = open(net_stats_file, 'r')
    
	except IOError:
	    return 0

        # convert to dict
        metrics = {}
        for line in file:
            if re.search(":", line):
                a = line.split(":")
                dev_name = a[0].lstrip()
                metrics[dev_name] = re.split("\s+", a[1].lstrip())

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]
    
def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    # Names will be in the format of tx/rx underscore metric_name underscore interface
    # e.g. tx_bytes_eth0
    parts = name.split("_")
    iface = parts[2]
    name = parts[0] + "_" + parts[1]

    index = stats_tab[name]

    try:
      delta = (float(curr_metrics['data'][iface][index]) - float(last_metrics['data'][iface][index])) /(curr_metrics['time'] - last_metrics['time'])
      if delta < 0:
	print name + " is less 0"
	delta = 0
    except KeyError:
      delta = 0.0      

    return delta


if __name__ == '__main__':
    try:
        params = {
            "interfaces": "",
            "excluded_interfaces": "dummy",
            "send_aggregate_bytes_packets": True,
            "debug"        : True,
            }
        metric_init(params)
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except StandardError:
        print sys.exc_info()[0]
        os._exit(1)

########NEW FILE########
__FILENAME__ = netiron
#!/usr/bin/python
# Name: netiron.py
# Desc: Ganglia module for polling netirons via snmnp (probably work with any snmp capable device)
# Author: Evan Fraser evan.fraser@trademe.co.nz
# Date: April 2012
# Copyright: GPL

import sys
import os
import re
import time
from pysnmp.entity.rfc3413.oneliner import cmdgen
NIPARAMS = {}

NIMETRICS = {
    'time' : 0,
    'data' : {}
}
LAST_NIMETRICS = dict(NIMETRICS)
NIMETRICS_CACHE_MAX = 5

descriptors = list()

oidDict = {
    'ifIndex'       : (1,3,6,1,2,1,2,2,1,1),
    'ifName'        : (1,3,6,1,2,1,31,1,1,1,1),
    'ifAlias'       : (1,3,6,1,2,1,31,1,1,1,18),
    'ifHCInOctets'  : (1,3,6,1,2,1,31,1,1,1,6),
    'ifHCOutOctets' : (1,3,6,1,2,1,31,1,1,1,10),
    'ifInUcastPkts' : (1,3,6,1,2,1,2,2,1,11),
    'ifOutUcastPkts' : (1,3,6,1,2,1,2,2,1,17),
    }

def get_metrics():
    """Return all metrics"""

    global NIMETRICS, LAST_NIMETRICS

    # if interval since last check > NIMETRICS_CACHE_MAX get metrics again
    if (time.time() - NIMETRICS['time']) > NIMETRICS_CACHE_MAX:
        metrics = {}
        for para in NIPARAMS.keys():
            if para.startswith('netiron_'):
                ipaddr,name = NIPARAMS[para].split(':')
                snmpTable = runSnmp(oidDict,ipaddr)
                newmetrics = buildDict(oidDict,snmpTable,name)
                metrics = dict(newmetrics, **metrics)

        # update cache
        LAST_NIMETRICS = dict(NIMETRICS)
        NIMETRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [NIMETRICS, LAST_NIMETRICS]

def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()
    try:
        delta = float(curr_metrics['data'][name] - last_metrics['data'][name])/(curr_metrics['time'] - last_metrics['time'])
        #print delta
        if delta < 0:
            print "Less than 0"
            delta = 0
    except StandardError:
        delta = 0

    return delta

# Separate routine to perform SNMP queries and returns table (dict)
def runSnmp(oidDict,ip):
    
    # cmdgen only takes tuples, oid strings don't work
#    ifIndex       = (1,3,6,1,2,1,2,2,1,1)
#    ifName        = (1,3,6,1,2,1,31,1,1,1,1)
#    ifAlias       = (1,3,6,1,2,1,31,1,1,1,18)
#    ifHCInOctets  = (1,3,6,1,2,1,31,1,1,1,6)
#    ifHCOutOctets = (1,3,6,1,2,1,31,1,1,1,10)

    #Runs the SNMP query, The order that oid's are passed determines the order in the results
    errorIndication, errorStatus, errorIndex, varBindTable = cmdgen.CommandGenerator().nextCmd(
        # SNMP v2
        cmdgen.CommunityData('test-agent', 'public'),
        cmdgen.UdpTransportTarget((ip, 161)),
        oidDict['ifAlias'],
        oidDict['ifIndex'],
        oidDict['ifName'],
        oidDict['ifHCInOctets'],
        oidDict['ifHCOutOctets'],
        oidDict['ifInUcastPkts'],
        oidDict['ifOutUcastPkts'],
        )
    # Check for SNMP errors
    if errorIndication:
        print errorIndication
    else:
        if errorStatus:
            print '%s at %s\n' % (
                errorStatus.prettyPrint(), errorIndex and varBindTable[-1][int(errorIndex)-1] or '?'
                )
        else:
            return(varBindTable)

def buildDict(oidDict,t,netiron): # passed a list of tuples, build's a dict based on the alias name
    builtdict = {}
    
    for line in t:
        #        if t[t.index(line)][2][1] != '':
        string = str(t[t.index(line)][2][1])
        match = re.search(r'ethernet', string)
        if match and t[t.index(line)][0][1] != '':
            alias = str(t[t.index(line)][0][1])
            index = str(t[t.index(line)][1][1])
            name = str(t[t.index(line)][2][1])
            hcinoct = str(t[t.index(line)][3][1])
            builtdict[netiron+'_'+alias+'_bitsin'] = int(hcinoct) * 8
            hcoutoct = str(t[t.index(line)][4][1])
            builtdict[netiron+'_'+alias+'_bitsout'] = int(hcoutoct) * 8
            hcinpkt = str(t[t.index(line)][5][1])
            builtdict[netiron+'_'+alias+'_pktsin'] = int(hcinpkt)
            hcoutpkt = str(t[t.index(line)][6][1])
            builtdict[netiron+'_'+alias+'_pktsout'] = int(hcoutpkt)
            
    return builtdict

# define_metrics will run an snmp query on an ipaddr, find interfaces, build descriptors and set spoof_host
# define_metrics is called from metric_init
def define_metrics(Desc_Skel, ipaddr, netiron):
    snmpTable = runSnmp(oidDict,ipaddr)
    aliasdict = buildDict(oidDict,snmpTable,netiron)
    spoof_string = ipaddr + ':' + netiron
    #print newdict

    for key in aliasdict.keys():
        if "bitsin" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "bits/sec",
                        "description" : "received bits per sec",
                        "groups"      : "Throughput",
                        "spoof_host"  : spoof_string,
                        }))
        elif "bitsout" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "bits/sec",
                        "description" : "transmitted bits per sec",
                        "groups"      : "Throughput",
                        "spoof_host"  : spoof_string,
                        }))
        elif "pktsin" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "pkts/sec",
                        "description" : "received packets per sec",
                        "groups"      : "Packets",
                        "spoof_host"  : spoof_string,
                        }))
        elif "pktsout" in key:
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : key,
                        "units"       : "pkts/sec",
                        "description" : "transmitted packets per sec",
                        "groups"      : "Packets",
                        "spoof_host"  : spoof_string,
                        }))


    return descriptors

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug, newdict

    print '[netiron] Received the following parameters'
    print params

    #Import the params into the global NIPARAMS
    for key in params:
        NIPARAMS[key] = params[key]

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'netiron',
        }  

    # Find all the netiron's passed in params    
    for para in params.keys():
         if para.startswith('netiron_'):
             #Get ipaddr + name of netirons from params
             ipaddr,name = params[para].split(':')
             # pass skel, ip and name to define_metrics to create descriptors
             descriptors = define_metrics(Desc_Skel, ipaddr, name)
    #Return the descriptors back to gmond
    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d


def metric_cleanup():
    '''Clean up the metric module.'''
    pass

# For CLI Debuging:
if __name__ == '__main__':
    params = {
        'netiron_1' : '192.168.1.1:switch1',
        'netiron_2' : '192.168.1.2:switch2',
              }
    descriptors = metric_init(params)
    print len(descriptors)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)        
        print 'Sleeping 5 seconds'
        time.sleep(5)
#exit(0)

########NEW FILE########
__FILENAME__ = netstats
import sys
import re
import time
import copy
import string

PARAMS = {}

METRICS = {
    'time' : 0,
    'data' : {}
}

stats_files = [ "/proc/net/netstat", "/proc/net/snmp" ]

LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

stats_pos = {} 

def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	new_metrics = {}

	for file in stats_files:
	    try:
		file = open(file, 'r')
	
	    except IOError:
		return 0
    
	    # convert to dict
	    metrics = {}
	    for line in file:
		if re.match("(.*): [0-9]", line):
		    count = 0
		    metrics = re.split("\s+", line)
		    metric_group = metrics[0].replace(":", "").lower()
		    new_metrics[metric_group] = dict()
		    for value in metrics:
			# Skip first
			if count > 0 and value >= 0 and count in stats_pos[metric_group]:
			    metric_name = stats_pos[metric_group][count]
			    new_metrics[metric_group][metric_name] = value
			count += 1

	    file.close()

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': new_metrics
        }

    return [METRICS, LAST_METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    name = name[len(NAME_PREFIX):] # remove prefix from name

    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    parts = name.split("_")
    group = parts[0]
    metric = "_".join(parts[1:])

    try:
      delta = (float(curr_metrics['data'][group][metric]) - float(last_metrics['data'][group][metric])) /(curr_metrics['time'] - last_metrics['time'])
      if delta < 0:
	print name + " is less 0"
	delta = 0
    except KeyError:
      delta = 0.0      

    return delta


def get_tcploss_percentage(name):

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    try:
      pct = 100 * (float(curr_metrics['data']['tcpext']["tcploss"]) - float(last_metrics["data"]['tcpext']["tcploss"])) / (float(curr_metrics['data']['tcp']['outsegs']) +  float(curr_metrics['data']['tcp']['insegs']) - float(last_metrics['data']['tcp']['insegs']) - float(last_metrics['data']['tcp']['outsegs']))
      if pct < 0:
	print name + " is less 0"
	pct = 0
    except Exception:
      pct = 0.0

    return pct

def get_tcpattemptfail_percentage(name):

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    try:
      pct = 100 * (float(curr_metrics['data']['tcp']["attemptfails"]) - float(last_metrics["data"]['tcp']["attemptfails"])) / (float(curr_metrics['data']['tcp']['outsegs']) +  float(curr_metrics['data']['tcp']['insegs']) - float(last_metrics['data']['tcp']['insegs']) - float(last_metrics['data']['tcp']['outsegs']))
      if pct < 0:
	print name + " is less 0"
	pct = 0
    except Exception:
      pct = 0.0

    return pct


def get_retrans_percentage(name):

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    try:
      pct = 100 * (float(curr_metrics['data']['tcp']["retranssegs"]) - float(last_metrics['data']['tcp']["retranssegs"])) / (float(curr_metrics['data']['tcp']['outsegs']) +  float(curr_metrics['data']['tcp']['insegs']) - float(last_metrics['data']['tcp']['insegs']) - float(last_metrics['data']['tcp']['outsegs']))
      if pct < 0:
	print name + " is less 0"
	pct = 0
    except Exception:
      pct = 0.0

    return pct


def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, metric_map, Desc_Skel

    descriptors = []

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.5f',
        'units'       : 'count/s',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'XXX',
        }

    ####################################################################################
    # Let's figure out what metrics are available
    #
    # Read /proc/net/netstat
    ####################################################################################
    for file in stats_files:
	try:
	    file = open(file, 'r')
    
	except IOError:
	    return 0
	
	# Find mapping
	for line in file:
	    # Lines with 
	    if not re.match("(.*): [0-9]", line):
		count = 0
		mapping = re.split("\s+", line)
		metric_group = mapping[0].replace(":", "").lower()
		stats_pos[metric_group] = dict()
		for metric in mapping:
		    # Skip first 
		    if count > 0 and metric != "":
			lowercase_metric = metric.lower()
			stats_pos[metric_group][count] = lowercase_metric
		    count += 1
    
	file.close()

    for group in stats_pos:
	for item in stats_pos[group]:
	    descriptors.append(create_desc(Desc_Skel, {
		    "name"       : group + "_" + stats_pos[group][item],
		    "description": stats_pos[group][item],
		    'groups'	 : group
		    }))

    descriptors.append(create_desc(Desc_Skel, {
	"name"       : "tcpext_tcploss_percentage",
	"call_back"  : get_tcploss_percentage,
	"description": "TCP percentage loss, tcploss / insegs + outsegs",
	"units"      : "pct",
        'groups'      : 'tcpext'
	}))

    descriptors.append(create_desc(Desc_Skel, {
	"name"       : "tcp_attemptfails_percentage",
	"call_back"  : get_tcpattemptfail_percentage,
	"description": "TCP attemptfail percentage, tcpattemptfail / insegs + outsegs",
	"units"      : "pct",
        'groups'      : 'tcp'
	}))


    descriptors.append(create_desc(Desc_Skel, {
	"name"       : "tcp_retrans_percentage",
	"call_back"  : get_retrans_percentage,
	"description": "TCP retrans percentage, retranssegs / insegs + outsegs",
	"units"      : "pct",
        'groups'      : 'tcp'
	}))

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping 15 seconds'
        time.sleep(15)

########NEW FILE########
__FILENAME__ = nfsstats
#!/usr/bin/python

import os
import stat
import re
import time
import syslog
import sys
import string

def test_proc( p_file, p_string ):
    global p_match
    """
    Check if <p_file> contains keyword <p_string> e.g. proc3, proc4
    """

    p_fd = open( p_file )

    p_contents = p_fd.read()

    p_fd.close()

    p_match = re.search(".*" + p_string + "\s.*", p_contents, flags=re.MULTILINE)

    if not p_match:
        return False
    else:
        return True

verboselevel = 0
descriptors = [ ]
old_values = { }
#  What we want ganglia to monitor, where to find it, how to extract it, ...
configtable = [
    {
        'group': 'nfs_client',
        'tests': [ 'stat.S_ISREG(os.stat("/proc/net/rpc/nfs").st_mode)', 'test_proc("/proc/net/rpc/nfs", "proc3")' ],
        'prefix': 'nfs_v3_',
        #  The next 4 lines can be at the 'group' level or the 'name' level
        'file': '/proc/net/rpc/nfs',
        'value_type': 'float',
        'units': 'calls/sec',
        'format': '%f',
        'names': {
            'total':       { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){2}(\d+.*\d)\n" },
            'getattr':     { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){2}(\S*)" },
            'setattr':     { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){3}(\S*)" },
            'lookup':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){4}(\S*)" },
            'access':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){5}(\S*)" },
            'readlink':    { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){6}(\S*)" },
            'read':        { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){7}(\S*)" },
            'write':       { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){8}(\S*)" },
            'create':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){9}(\S*)" },
            'mkdir':       { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){10}(\S*)" },
            'symlink':     { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){11}(\S*)" },
            'mknod':       { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){12}(\S*)" },
            'remove':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){13}(\S*)" },
            'rmdir':       { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){14}(\S*)" },
            'rename':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){15}(\S*)" },
            'link':        { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){16}(\S*)" },
            'readdir':     { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){17}(\S*)" },
            'readdirplus': { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){18}(\S*)" },
            'fsstat':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){19}(\S*)" },
            'fsinfo':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){20}(\S*)" },
            'pathconf':    { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){21}(\S*)" },
            'commit':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){22}(\S*)" }
        }
    },
    {
        'group': 'nfs_client_v4',
        'tests': [ 'stat.S_ISREG(os.stat("/proc/net/rpc/nfs").st_mode)', 'test_proc("/proc/net/rpc/nfs", "proc4")' ],
        'prefix': 'nfs_v4_',
        #  The next 4 lines can be at the 'group' level or the 'name' level
        'file': '/proc/net/rpc/nfs',
        'value_type': 'float',
        'units': 'calls/sec',
        'format': '%f',
        'names': {
            'total':        { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){2}(\d+.*\d)\n" },
            'read':         { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){2}(\S*)" },
            'write':        { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){3}(\S*)" },
            'commit':       { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){4}(\S*)" },
            'open':         { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){5}(\S*)" },
            'open_conf':    { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){6}(\S*)" },
            'open_noat':    { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){7}(\S*)" },
            'open_dgrd':    { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){8}(\S*)" },
            'close':        { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){9}(\S*)" },
            'setattr':      { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){10}(\S*)" },
            'renew':        { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){11}(\S*)" },
            'setclntid':    { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){12}(\S*)" },
            'confirm':      { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){13}(\S*)" },
            'lock':         { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){14}(\S*)" },
            'lockt':        { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){15}(\S*)" },
            'locku':        { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){16}(\S*)" },
            'access':       { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){17}(\S*)" },
            'getattr':      { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){18}(\S*)" },
            'lookup':       { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){19}(\S*)" },
            'lookup_root':  { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){20}(\S*)" },
            'remove':       { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){21}(\S*)" },
            'rename':       { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){22}(\S*)" },
            'link':         { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){23}(\S*)" },
            'symlink':      { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){24}(\S*)" },
            'create':       { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){25}(\S*)" },
            'pathconf':     { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){26}(\S*)" },
            'statfs':       { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){27}(\S*)" },
            'readlink':     { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){28}(\S*)" },
            'readdir':      { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){29}(\S*)" },
            'server_caps':  { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){30}(\S*)" },
            'delegreturn':  { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){31}(\S*)" },
            'getacl':       { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){32}(\S*)" },
            'setacl':       { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){33}(\S*)" },
            'fs_locations': { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){34}(\S*)" },
            'rel_lkowner':  { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){35}(\S*)" },
            'secinfo':      { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){36}(\S*)" },
            'exchange_id':  { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){37}(\S*)" },
            'create_ses':   { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){38}(\S*)" },
            'destroy_ses':  { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){39}(\S*)" },
            'sequence':     { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){40}(\S*)" },
            'get_lease_t':  { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){41}(\S*)" },
            'reclaim_comp': { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){42}(\S*)" },
            'layoutget':    { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){43}(\S*)" },
            'getdevinfo':   { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){44}(\S*)" },
            'layoutcommit': { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){45}(\S*)" },
            'layoutreturn': { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){46}(\S*)" },
            'getdevlist':   { 'description':'dummy description', 're':  ".*proc4 (?:\S*\s){47}(\S*)" }
        }
    },
    {
        'group': 'nfs_server',
        'tests': [ 'stat.S_ISREG(os.stat("/proc/net/rpc/nfsd").st_mode)', 'test_proc("/proc/net/rpc/nfsd", "proc3")' ],
        'prefix': 'nfsd_v3_',
        #  The next 4 lines can be at the 'group' level or the 'name' level
        'file': '/proc/net/rpc/nfsd',
        'value_type': 'float',
        'units': 'calls/sec',
        'format': '%f',
        'names': {
            'total':       { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){2}(\d+.*\d)\n" },
            'getattr':     { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){2}(\S*)" },
            'setattr':     { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){3}(\S*)" },
            'lookup':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){4}(\S*)" },
            'access':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){5}(\S*)" },
            'readlink':    { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){6}(\S*)" },
            'read':        { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){7}(\S*)" },
            'write':       { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){8}(\S*)" },
            'create':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){9}(\S*)" },
            'mkdir':       { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){10}(\S*)" },
            'symlink':     { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){11}(\S*)" },
            'mknod':       { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){12}(\S*)" },
            'remove':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){13}(\S*)" },
            'rmdir':       { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){14}(\S*)" },
            'rename':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){15}(\S*)" },
            'link':        { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){16}(\S*)" },
            'readdir':     { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){17}(\S*)" },
            'readdirplus': { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){18}(\S*)" },
            'fsstat':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){19}(\S*)" },
            'fsinfo':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){20}(\S*)" },
            'pathconf':    { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){21}(\S*)" },
            'commit':      { 'description':'dummy description', 're':  ".*proc3 (?:\S*\s){22}(\S*)" }
        },
    },
    {
        'group': 'nfs_server_v4',
        'tests': [ 'stat.S_ISREG(os.stat("/proc/net/rpc/nfsd").st_mode)', 'test_proc("/proc/net/rpc/nfsd", "proc4ops")' ],
        'prefix': 'nfsd_v4_',
        #  The next 4 lines can be at the 'group' level or the 'name' level
        'file': '/proc/net/rpc/nfsd',
        'value_type': 'float',
        'units': 'calls/sec',
        'format': '%f',
        'names': {
            'total':         { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){2}(\d+.*\d)\n" },
            'op0-unused':    { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){1}(\S*)" },
            'op1-unused':    { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){2}(\S*)" },
            'op2-future':    { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){3}(\S*)" },
            'access':        { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){4}(\S*)" },
            'close':         { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){5}(\S*)" },
            'commit':        { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){6}(\S*)" },
            'create':        { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){7}(\S*)" },
            'delegpurge':    { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){8}(\S*)" },
            'delegreturn':   { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){9}(\S*)" },
            'getattr':       { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){10}(\S*)" },
            'getfh':         { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){11}(\S*)" },
            'link':          { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){12}(\S*)" },
            'lock':          { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){13}(\S*)" },
            'lockt':         { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){14}(\S*)" },
            'locku':         { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){15}(\S*)" },
            'lookup':        { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){16}(\S*)" },
            'lookup_root':   { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){17}(\S*)" },
            'nverify':       { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){18}(\S*)" },
            'open':          { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){19}(\S*)" },
            'openattr':      { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){20}(\S*)" },
            'open_conf':     { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){21}(\S*)" },
            'open_dgrd':     { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){22}(\S*)" },
            'putfh':         { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){23}(\S*)" },
            'putpubfh':      { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){24}(\S*)" },
            'putrootfh':     { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){25}(\S*)" },
            'read':          { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){26}(\S*)" },
            'readdir':       { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){27}(\S*)" },
            'readlink':      { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){28}(\S*)" },
            'remove':        { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){29}(\S*)" },
            'rename':        { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){30}(\S*)" },
            'renew':         { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){31}(\S*)" },
            'restorefh':     { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){32}(\S*)" },
            'savefh':        { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){33}(\S*)" },
            'secinfo':       { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){34}(\S*)" },
            'setattr':       { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){35}(\S*)" },
            'setcltid':      { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){36}(\S*)" },
            'setcltidconf':  { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){37}(\S*)" },
            'verify':        { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){38}(\S*)" },
            'write':         { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){39}(\S*)" },
            'rellockowner':  { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){40}(\S*)" },
            'bc_ctl':        { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){41}(\S*)" },
            'bind_conn':     { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){42}(\S*)" },
            'exchange_id':   { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){43}(\S*)" },
            'create_ses':    { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){44}(\S*)" },
            'destroy_ses':   { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){45}(\S*)" },
            'free_stateid':  { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){46}(\S*)" },
            'getdirdeleg':   { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){47}(\S*)" },
            'getdevinfo':    { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){48}(\S*)" },
            'getdevlist':    { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){49}(\S*)" },
            'layoutcommit':  { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){50}(\S*)" },
            'layoutget':     { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){51}(\S*)" },
            'layoutreturn':  { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){52}(\S*)" },
            'secinfononam':  { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){53}(\S*)" },
            'sequence':      { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){54}(\S*)" },
            'set_ssv':       { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){55}(\S*)" },
            'test_stateid':  { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){56}(\S*)" },
            'want_deleg':    { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){57}(\S*)" },
            'destroy_clid':  { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){58}(\S*)" },
            'reclaim_comp':  { 'description':'dummy description', 're':  ".*proc4ops (?:\S*\s){59}(\S*)" }
        },
    }
]

#  Ganglia will call metric_init(), which should return a dictionary for each thing that it
#  should monitor, including the name of the callback function to get the current value.
def metric_init(params):
    global descriptors
    global old_values
    global configtable

    for i in range(0, len(configtable)):
        #  Don't set up dictionary for any group member if group applicability tests fail.
        tests_passed = True
        for j in range(0, len(configtable[i]['tests'])):
            try:
                if eval(configtable[i]['tests'][j]):
		    pass
                else:
                    tests_passed = False
                    break
            except:
               tests_passed = False
               break
        if not tests_passed:
            continue

        # 2nd param defines number of params that will follow (differs between NFS versions)
        max_plimit = re.split("\W+", p_match.group())[1]

        # Parse our defined params list in order to ensure list will not exceed max_plimit
        n = 0
        names_keys = configtable[i]['names'].keys()
        keys_to_remove = []
        for _tmpkey in names_keys:
            _tmplist = names_keys
            param_pos = re.split("{(\d+)\}", configtable[i]['names'][_tmpkey].values()[0])[1]
	    if int(param_pos) > int(max_plimit):
                keys_to_remove.append(_tmpkey)
            n += 1

        if len(keys_to_remove) > 0:
            for key in keys_to_remove:
                names_keys.remove(key)

        #  For each name in the group ...
        for name in names_keys:
            #  ... set up dictionary ...
            if 'format' in configtable[i]['names'][name]:
		format_str = configtable[i]['names'][name]['format']
            else:
		format_str = configtable[i]['format']
            if 'units' in configtable[i]['names'][name]:
		unit_str = configtable[i]['names'][name]['units']
            else:
		unit_str = configtable[i]['units']
            if 'value_type' in configtable[i]['names'][name]:
		value_type_str = configtable[i]['names'][name]['value_type']
            else:
		value_type_str = configtable[i]['value_type']
            if 'file' in configtable[i]['names'][name]:
		file_str = configtable[i]['names'][name]['file']
            else:
		file_str = configtable[i]['file']
		

            descriptors.append({
                'name': configtable[i]['prefix'] + name,
                'call_back': call_back,
                'time_max': 90,
                'format': format_str,
                'units': unit_str,
                'value_type': value_type_str,
                'slope': 'both',
                'description': configtable[i]['names'][name]['description'],
                'groups': configtable[i]['group'],
                #  The following are module-private data stored in a public variable
                'file': file_str,
                're': configtable[i]['names'][name]['re']
            })
            #  And get current value cached as previous value, for future comparisons.
            (ts, value) =  get_value(configtable[i]['prefix'] + name)
            old_values[configtable[i]['prefix'] + name] = { 
                'time':ts,
                'value':value
            }

    #  Pass ganglia the complete list of dictionaries.
    return descriptors

#  Ganglia will call metric_cleanup() when it exits.
def metric_cleanup():
    pass

#  metric_init() registered this as the callback function.
def call_back(name):
    global old_values

    #  Get new value
    (new_time, new_value) = get_value(name)
 
    #  Calculate rate of change 
    try:
        rate = (new_value - old_values[name]['value'])/(new_time - old_values[name]['time'])
    except ZeroDivisionError:
        rate = 0.0

    #  Stash values for comparison next time round.
    old_values[name]['value'] = new_value
    old_values[name]['time'] = new_time
    return rate

def get_value(name):
    global descriptors

    #  Search descriptors array for this name's file and extractor RE
    for i in range(0, len(descriptors)):
        if descriptors[i]['name'] == name:
            break
    contents = file(descriptors[i]['file']).read()
    m = re.search(descriptors[i]['re'], contents, flags=re.MULTILINE)

    m_value = m.group(1)

    #RB: multiple (space seperated) values: calculate sum
    if string.count( m_value, ' ' ) > 0:
        m_fields = string.split( m_value, ' ' )

        sum_value = 0

        for f in m_fields:
            sum_value = sum_value + int(f)

        m_value = sum_value
    
    #  Return time and value.
    ts = time.time()
    return (ts, int(m_value))

def debug(level, text):
    global verboselevel
    if level > verboselevel:
        return
    if sys.stderr.isatty():
        print text
    else:
        syslog.syslog(text)

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init(None)
    #  wait some time time for some real data
    time.sleep(5)
    for d in descriptors:
        v = d['call_back'](d['name'])
        debug(10, ('__main__: value for %s is %s' % (d['name'], d['format'])) % (v))

########NEW FILE########
__FILENAME__ = nginx_status
###  This script reports nginx status stub metrics to ganglia.

###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt
import logging
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import urllib2

logging.basicConfig(level=logging.ERROR)

_Worker_Thread = None

class UpdateNginxThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running = False
        self.shuttingdown = False
        self.refresh_rate = int(params['refresh_rate'])
        self.metrics = {}
        self.settings = {}
        self.status_url = params['status_url']
        self.nginx_bin = params['nginx_bin']
        self._metrics_lock = threading.Lock()
        self._settings_lock = threading.Lock()

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        global _Lock

        self.running = True

        while not self.shuttingdown:
            time.sleep(self.refresh_rate)
            self.refresh_metrics()

        self.running = False

    @staticmethod
    def _get_nginx_status_stub_response(url):
        c = urllib2.urlopen(url, None, 2)
        data = c.read()
        c.close()

        matchActive = re.search(r'Active connections:\s+(\d+)', data)
        matchHistory = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', data)
        matchCurrent = re.search(r'Reading:\s*(\d+)\s*Writing:\s*(\d+)\s*'
            'Waiting:\s*(\d+)', data)

        if not matchActive or not matchHistory or not matchCurrent:
            raise Exception('Unable to parse {0}' . format(url))

        result = {}
        result['nginx_active_connections'] = int(matchActive.group(1))

        result['nginx_accepts'] = int(matchHistory.group(1))
        result['nginx_handled'] = int(matchHistory.group(2))
        result['nginx_requests'] = int(matchHistory.group(3))

        result['nginx_reading'] = int(matchCurrent.group(1))
        result['nginx_writing'] = int(matchCurrent.group(2))
        result['nginx_waiting'] = int(matchCurrent.group(3))

        return result

    def refresh_metrics(self):
        logging.debug('refresh metrics')

        try:
            logging.debug(' opening URL: ' + str(self.status_url))

            data = UpdateNginxThread._get_nginx_status_stub_response(self.status_url)
        except:
            logging.warning('error refreshing metrics')
            logging.warning(traceback.print_exc(file=sys.stdout))

        try:
            self._metrics_lock.acquire()
            self.metrics = {}

            for k, v in data.items():
                self.metrics[k] = v
        except:
            logging.warning('error refreshing metrics')
            logging.warning(traceback.print_exc(file=sys.stdout))
            return False
        finally:
            self._metrics_lock.release()

        if not self.metrics:
            logging.warning('error refreshing metrics')
            return False

        logging.debug('success refreshing metrics')
        logging.debug('metrics: ' + str(self.metrics))

        return True

    def refresh_settings(self):
        logging.debug(' refreshing server settings')

        try:
            p = subprocess.Popen(executable=self.nginx_bin, args=[self.nginx_bin, '-v'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
        except:
            logging.warning('error refreshing settings')
            return False

        try:
            self._settings_lock.acquire()
            self.settings = {}
            for line in err.split('\n'):
                if line.startswith('nginx version:'):
                    key = "nginx_server_version"
                else:
                    continue

                logging.debug('  line: ' + str(line))

                line = line.split(': ')

                if len(line) > 1:
                    self.settings[key] = line[1]
        except:
            logging.warning('error refreshing settings')
            return False
        finally:
            self._settings_lock.release()

        logging.debug('success refreshing server settings')
        logging.debug('settings: ' + str(self.settings))

        return True

    def metric_of(self, name):
        logging.debug('getting metric: ' + name)

        try:
            if name in self.metrics:
                try:
                    self._metrics_lock.acquire()
                    logging.debug('metric: %s = %s' % (name, self.metrics[name]))
                    return self.metrics[name]
                finally:
                    self._metrics_lock.release()
        except:
            logging.warning('failed to fetch ' + name)
            return 0

    def setting_of(self, name):
        logging.debug('getting setting: ' + name)

        try:
            if name in self.settings:
                try:
                    self._settings_lock.acquire()
                    logging.debug('setting: %s = %s' % (name, self.settings[name]))
                    return self.settings[name]
                finally:
                    self._settings_lock.release()
        except:
            logging.warning('failed to fetch ' + name)
            return 0

def metric_init(params):
    logging.debug('init: ' + str(params))
    global _Worker_Thread

    METRIC_DEFAULTS = {
        'time_max': 60,
        'units': 'connections',
        'groups': 'nginx',
        'slope': 'both',
        'value_type': 'uint',
        'format': '%d',
        'description': '',
        'call_back': metric_of
    }

    descriptions = dict(
        nginx_server_version={
            'value_type': 'string',
            'units': '',
            'format': '%s',
            'slope': 'zero',
            'call_back': setting_of,
            'description': 'Nginx version number'},

        nginx_active_connections={
            'description': 'Total number of active connections'},

        nginx_accepts={
            'slope': 'positive',
            'description': 'Total number of accepted connections'},

        nginx_handled={
            'slope': 'positive',
            'description': 'Total number of handled connections'},

        nginx_requests={
            'slope': 'positive',
            'units': 'requests',
            'description': 'Total number of requests'},

        nginx_reading={
            'description': 'Current connection in the reading state'},

        nginx_writing={
            'description': 'Current connection in the writing state'},

        nginx_waiting={
            'description': 'Current connection in the waiting state'})

    if _Worker_Thread is not None:
        raise Exception('Worker thread already exists')

    _Worker_Thread = UpdateNginxThread(params)
    _Worker_Thread.refresh_metrics()
    _Worker_Thread.refresh_settings()
    _Worker_Thread.start()

    descriptors = []

    for name, desc in descriptions.iteritems():
        d = desc.copy()
        d['name'] = str(name)
        [ d.setdefault(key, METRIC_DEFAULTS[key]) for key in METRIC_DEFAULTS.iterkeys() ]
        descriptors.append(d)

    return descriptors

def metric_of(name):
    global _Worker_Thread
    return _Worker_Thread.metric_of(name)

def setting_of(name):
    global _Worker_Thread
    return _Worker_Thread.setting_of(name)

def metric_cleanup():
    global _Worker_Thread
    if _Worker_Thread is not None:
        _Worker_Thread.shutdown()
    logging.shutdown()
    # pass

if __name__ == '__main__':
    from optparse import OptionParser

    try:

        logging.debug('running from cmd line')
        parser = OptionParser()
        parser.add_option('-u', '--URL', dest='status_url', default='http://localhost/nginx_status', help='URL for Nginx status stub page')
        parser.add_option('--nginx-bin', dest='nginx_bin', default='/usr/sbin/nginx', help='path to nginx')
        parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
        parser.add_option('-r', '--refresh-rate', dest='refresh_rate', default=15)
        parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False)

        (options, args) = parser.parse_args()

        descriptors = metric_init({
            'status_url': options.status_url,
            'nginx_bin': options.nginx_bin,
            'refresh_rate': options.refresh_rate
        })

        if options.debug:
            from pprint import pprint
            pprint(descriptors)

        for d in descriptors:
            v = d['call_back'](d['name'])

            if not options.quiet:
                print ' {0}: {1} {2} [{3}]' . format(d['name'], v, d['units'], d['description'])

        os._exit(1)

    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except StandardError:
        traceback.print_exc()
        os._exit(1)
    finally:
        metric_cleanup()

########NEW FILE########
__FILENAME__ = compute-metrics
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 GridDynamics
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Ganglia module for getting latest instance count
"""

import os
import time
import threading
import traceback
import sys

from nova import flags

from nova import db
from nova import context
from nova import log as logging
from nova import utils
from nova import version
from nova.compute import manager as compute_manager

__worker__ = None
__lock__ = threading.Lock()

FLAGS = flags.FLAGS
args = ['compute-metrics']
utils.default_flagfile(args=args)
print args
flags.FLAGS(args)
print FLAGS.sql_connection


class UpdateComputeNodeStatusThread(threading.Thread):
    """Updates compute node status."""

    def __init__(self, params):
        print 'starting init'
        threading.Thread.__init__(self)
        self.manager          = compute_manager.ComputeManager()
        self.running          = False
        self.shuttingdown     = False
        self.refresh_rate     = int(params['refresh_rate'])
        self.status           = {}
        self._update_hypervisor()
        print 'finished init'

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            __lock__.acquire()
            self.update_status()
            __lock__.release()

            time.sleep(self.refresh_rate)

        self.running = False

    def update_status(self):
        print 'starting update'
        for updater in (self._update_count, self._update_status):
            try:
                print 'updating using %s' % updater
                updater()
            except:
                traceback.print_exc()
        print 'end update: %s' % self.status

    def status_of(self, name):
        val = None
        if name in self.status:
            __lock__.acquire()
            val = self.status[name]
            __lock__.release()
        return val

    def _update_count(self):
        print 'updating instances'
        self.status['nova_compute_instance_count'] = \
                len(self.manager.driver.list_instances())

    def _update_status(self):
        ctxt = context.get_admin_context()
        services = db.service_get_all_by_host(ctxt, FLAGS.host)
        up_count = 0
        compute_alive = False
        for svc in services:
            now = utils.utcnow()
            delta = now - (svc['updated_at'] or svc['created_at'])
            alive = (delta.seconds <= 15)
            compute_alive = compute_alive or svc['topic'] == 'compute'
            up_count += alive
        self.status['nova_registered_services'] = len(services)
        self.status['nova_compute_is_running'] = compute_alive and 'OK' or 'NO'
        self.status['nova_running_services'] = up_count

    def _update_hypervisor(self):
        status = type(self.manager.driver).__name__
        try:
            hyperv = self.manager.driver.get_hypervisor_type()
            status += ' with %s' % (hyperv)
        except:
            pass
        self.status['nova_compute_driver'] = status


def version_handler(name):
    return version.canonical_version_string()


def hypervisor_getter(worker):
    global _hypervisor_name
    return _hypervisor_name

def metric_init(params):
    global __worker__

    if not 'refresh_rate' in params:
        params['refresh_rate'] = 60

    __worker__ = UpdateComputeNodeStatusThread(params)
    __worker__.start()
    status_of = __worker__.status_of

    instances = {'name': 'nova_compute_instance_count',
                 'call_back': status_of,
                 'time_max': 90,
                 'value_type': 'uint',
                 'units': '',
                 'slope': 'both',
                 'format': '%d',
                 'description': 'Openstack Instance Count',
                 'groups': 'openstack-compute'}

    version = {'name': 'openstack_version',
               'call_back': version_handler,
               'time_max': 90,
               'value_type': 'string',
               'units': '',
               'slope': 'zero',
               'format': '%s',
               'description': 'Openstack Version',
               'groups': 'openstack-compute'}

    compute  = {'name': 'nova_compute_is_running',
               'call_back': status_of,
               'time_max': 90,
               'value_type': 'string',
               'units': '',
               'slope': 'zero',
               'format': '%s',
               'description': 'Openstack Nova compute is running',
               'groups': 'openstack-compute'}

    hypervisor  = {'name': 'nova_compute_driver',
               'call_back': status_of,
               'time_max': 90,
               'value_type': 'string',
               'units': '',
               'slope': 'zero',
               'format': '%s',
               'description': 'Openstack Nova compute driver',
               'groups': 'openstack-compute'}

    run_services = {'name': 'nova_running_services',
                 'call_back': status_of,
                 'time_max': 90,
                 'value_type': 'uint',
                 'units': '',
                 'slope': 'both',
                 'format': '%d',
                 'description': 'Openstack Nova running services',
                 'groups': 'openstack-compute'}

    reg_services = {'name': 'nova_registered_services',
                 'call_back': status_of,
                 'time_max': 90,
                 'value_type': 'uint',
                 'units': '',
                 'slope': 'both',
                 'format': '%d',
                 'description': 'Openstacl Nova Registered services',
                 'groups': 'openstack-compute'}

    return [instances, version, compute, hypervisor,
            run_services, reg_services]

def metric_cleanup():
    """Clean up the metric module."""
    __worker__.shutdown()


if __name__ == '__main__':
    try:
        metric_init({})
        k = 'c_instance_count'
        v = status_of(k)
        print 'value for %s is %u' % (k, v)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    finally:
        metric_cleanup()


########NEW FILE########
__FILENAME__ = passenger
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import traceback
import os
import threading
import time
import datetime
import signal
import subprocess
import re

descriptors = list()
Desc_Skel   = {}
_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock
Debug = False

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "DEBUG: "+f % v

def floatable(str):
    try:
        float(str)
        return True
    except:
        return False

class UpdateMetricThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 30
        if "refresh_rate" in params:
            self.refresh_rate = int(params["refresh_rate"])
        self.metric       = {}
        self.timeout      = 10

        self.status       = "sudo /usr/bin/passenger-status"
        self.memory_stats = "sudo /usr/bin/passenger-memory-stats"
        if "status" in params:
            self.status = params["status"]
        if "memory_stats" in params:
            self.memory_stats = params["memory_stats"]
        self.mp      = params["metrix_prefix"]
        self.status_regex   = {
          'max_pool_size':        r"^max\s+= (\d+)",
          'open_processes':       r"^count\s+= (\d+)",
          'processes_active':     r"^active\s+= (\d+)",
          'processes_inactive':   r"^inactive\s+= (\d+)",
          'global_queue_depth':   r"^Waiting on global queue: (\d+)",
          'memory_usage':         r"^### Total private dirty RSS:\s+(\d+)"
        }

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            self.update_metric()
            _Lock.release()
            time.sleep(self.refresh_rate)

        self.running = False

    def update_metric(self):
        status_output = timeout_command(self.status, self.timeout)
        status_output += timeout_command(self.memory_stats, self.timeout)[-1:] # to get last line of memory output
        dprint("%s", status_output)
        for line in status_output:
          for (name,regex) in self.status_regex.iteritems():
            result = re.search(regex,line)
            if result:
              dprint("%s = %d", name, int(result.group(1)))
              self.metric[self.mp+'_'+name] = int(result.group(1))

    def metric_of(self, name):
        val = 0
        mp = name.split("_")[0]
        if name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            _Lock.release()
        return val

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug

    if "metrix_prefix" not in params:
      params["metrix_prefix"] = "passenger"

    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_of,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'format'      : '%u',
        'units'       : 'XXX',
        'slope'       : 'XXX', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'passenger',
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 15
    if "debug" in params:
        Debug = params["debug"]
    dprint("%s", "Debug mode on")

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    mp = params["metrix_prefix"]

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_max_pool_size",
                "units"      : "processes",
                "slope"      : "both",
                "description": "Max processes in Passenger pool",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_open_processes",
                "units"      : "processes",
                "slope"      : "both",
                "description": "Number of currently open passenger processes",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_processes_active",
                "units"      : "processes",
                "slope"      : "both",
                "description": "Active processes",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_processes_inactive",
                "units"      : "processes",
                "slope"      : "both",
                "description": "Inactive processes",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_global_queue_depth",
                "units"      : "requests",
                "slope"      : "both",
                "description": "Requests waiting on a free process",
                }))
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_memory_usage",
                "units"      : "MB",
                "slope"      : "both",
                "description": "Passenger Memory usage",
                }))

    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_of(name):
    return _Worker_Thread.metric_of(name)

def metric_cleanup():
    _Worker_Thread.shutdown()

def timeout_command(command, timeout):
    """call shell-command and either return its output or kill it
    if it doesn't normally exit within timeout seconds and return None"""
    cmd = command.split(" ")
    start = datetime.datetime.now()
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while process.poll() is None:
        time.sleep(0.2)
        now = datetime.datetime.now()
        if (now - start).seconds> timeout:
            os.system("sudo kill %s" % process.pid)
            os.waitpid(-1, os.WNOHANG)
            return []
    return process.stdout.readlines()

if __name__ == '__main__':
    try:
        params = {
            "debug" : True,
            }
        metric_init(params)

        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)

########NEW FILE########
__FILENAME__ = php_fpm
###  This script reports php_fpm status metrics to ganglia.
###
###  This module can monitor multiple php-fpm pools by
###  passing in multiple ports separated by commas into
###  the ports parameter.

###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

from StringIO import StringIO
from copy import copy
from flup.client.fcgi_app import Record, FCGI_BEGIN_REQUEST, struct, \
    FCGI_BeginRequestBody, FCGI_RESPONDER, FCGI_BeginRequestBody_LEN, FCGI_STDIN, \
    FCGI_DATA, FCGI_STDOUT, FCGI_STDERR, FCGI_END_REQUEST
from pprint import pprint
import flup.client.fcgi_app
import json
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib2

logging.basicConfig(level=logging.ERROR)

class FCGIApp(flup.client.fcgi_app.FCGIApp):
    ### HACK: reduce the timeout to 2 seconds
    def _getConnection(self):
        if self._connect is not None:
            # The simple case. Create a socket and connect to the
            # application.
            if type(self._connect) is str:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(self._connect)
            return sock

    ### HACK: workaround for a php-fpm bug: http://bugs.php.net/bug.php?id=53618
    def __call__(self, environ, start_response):
        # For sanity's sake, we don't care about FCGI_MPXS_CONN
        # (connection multiplexing). For every request, we obtain a new
        # transport socket, perform the request, then discard the socket.
        # This is, I believe, how mod_fastcgi does things...

        sock = self._getConnection()

        # Since this is going to be the only request on this connection,
        # set the request ID to 1.
        requestId = 1

        # Begin the request
        rec = Record(FCGI_BEGIN_REQUEST, requestId)
        rec.contentData = struct.pack(FCGI_BeginRequestBody, FCGI_RESPONDER, 0)
        rec.contentLength = FCGI_BeginRequestBody_LEN
        rec.write(sock)

        # Filter WSGI environ and send it as FCGI_PARAMS
        if self._filterEnviron:
            params = self._defaultFilterEnviron(environ)
        else:
            params = self._lightFilterEnviron(environ)
        # TODO: Anything not from environ that needs to be sent also?
        self._fcgiParams(sock, requestId, params)
        self._fcgiParams(sock, requestId, {})

        # Transfer wsgi.input to FCGI_STDIN
        content_length = int(environ.get('CONTENT_LENGTH') or 0)
        while True:
            chunk_size = min(content_length, 4096)
            s = environ['wsgi.input'].read(chunk_size)
            content_length -= len(s)
            rec = Record(FCGI_STDIN, requestId)
            rec.contentData = s
            rec.contentLength = len(s)
            rec.write(sock)

            if not s: break

        # Empty FCGI_DATA stream
        rec = Record(FCGI_DATA, requestId)
        rec.write(sock)

        # Main loop. Process FCGI_STDOUT, FCGI_STDERR, FCGI_END_REQUEST
        # records from the application.
        result = []
        while True:
            inrec = Record()
            inrec.read(sock)
            if inrec.type == FCGI_STDOUT:
                if inrec.contentData:
                    result.append(inrec.contentData)
                else:
                    # TODO: Should probably be pedantic and no longer
                    # accept FCGI_STDOUT records?
                    pass
            elif inrec.type == FCGI_STDERR:
                # Simply forward to wsgi.errors
                environ['wsgi.errors'].write(inrec.contentData)
            elif inrec.type == FCGI_END_REQUEST:
                # TODO: Process appStatus/protocolStatus fields?
                break

        # Done with this transport socket, close it. (FCGI_KEEP_CONN was not
        # set in the FCGI_BEGIN_REQUEST record we sent above. So the
        # application is expected to do the same.)
        sock.close()

        result = ''.join(result)

        # Parse response headers from FCGI_STDOUT
        status = '200 OK'
        headers = []
        pos = 0
        while True:
            eolpos = result.find('\n', pos)
            if eolpos < 0: break
            line = result[pos:eolpos - 1]
            pos = eolpos + 1

            # strip in case of CR. NB: This will also strip other
            # whitespace...
            line = line.strip()

            # Empty line signifies end of headers
            if not line: break

            # TODO: Better error handling
            if  ':' not in line:
                continue

            header, value = line.split(':', 1)
            header = header.strip().lower()
            value = value.strip()

            if header == 'status':
                # Special handling of Status header
                status = value
                if status.find(' ') < 0:
                    # Append a dummy reason phrase if one was not provided
                    status += ' FCGIApp'
            else:
                headers.append((header, value))

        result = result[pos:]

        # Set WSGI status, headers, and return result.
        start_response(status, headers)
        return [result]

_Worker_Thread = None

class UpdatePhpFpmThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running = False
        self.shuttingdown = False
        self.refresh_rate = int(params['refresh_rate'])
        self.metrics = {}
        self.settings = {}
        self.status_path = str(params['status_path'])
        self.php_fpm_bin = str(params['php_fpm_bin'])
        self.host = str(params['host'])
        self.ports = [ int(p) for p in params['ports'].split(',') ]
        self.prefix = str(params['prefix'])
        self._metrics_lock = threading.Lock()
        self._settings_lock = threading.Lock()

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            time.sleep(self.refresh_rate)
            self.refresh_metrics()

        self.running = False

    @staticmethod
    def _get_php_fpm_status_response(status_path, host, port):
        def noop(sc, h): pass

        stat = FCGIApp(connect=(host, port), filterEnviron=False)

        env = {
            'QUERY_STRING': 'json',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_FILENAME': status_path,
            'SCRIPT_NAME': status_path,
            'wsgi.input': StringIO()
        }

        try:
            result = stat(environ=env, start_response=noop)
            logging.debug('status response: ' + str(result))
        except:
            logging.warning(traceback.print_exc(file=sys.stdout))
            raise Exception('Unable to get php_fpm status response from %s:%s %s' % (host, port, status_path))

        if len(result) <= 0:
            raise Exception('php_fpm status response is empty')

        try:
            return json.loads(result[0])
        except ValueError:
            logging.error('Could not deserialize json: ' + str(result))
            raise Exception('Could not deserialize json: ' + str(result))

    def refresh_metrics(self):
        logging.debug('refresh metrics')

        responses = {}

        for port in self.ports:
            try:
                logging.debug('opening URL: %s, host: %s, ports %s' % (self.status_path, self.host, port))
                responses[port] = UpdatePhpFpmThread._get_php_fpm_status_response(self.status_path, self.host, port)
            except:
                logging.warning('error refreshing stats for port ' + str(port))
                logging.warning(traceback.print_exc(file=sys.stdout))

        try:
            self._metrics_lock.acquire()
            self.metrics = {}
            for port, response in responses.iteritems():
                try:
                    prefix = self.prefix + (str(port) + "_" if len(self.ports) > 1 else "")

                    for k, v in response.iteritems():
                        if k == 'accepted conn':
                            self.metrics[prefix + 'accepted_connections'] = int(v)
                        elif k == 'pool':
                            self.metrics[prefix + 'pool_name'] = str(v)
                        elif k == 'process manager':
                            self.metrics[prefix + 'process_manager'] = str(v)
                        elif k == 'idle processes':
                            self.metrics[prefix + 'idle_processes'] = int(v)
                        elif k == 'active processes':
                            self.metrics[prefix + 'active_processes'] = int(v)
                        elif k == 'total processes':
                            self.metrics[prefix + 'total_processes'] = int(v)
                        else:
                            logging.warning('skipped metric: %s = %s' % (k, v))

                    logging.debug('success refreshing stats for port ' + str(port))
                    logging.debug('metrics(' + str(port) + '): ' + str(self.metrics))
                except:
                    logging.warning('error refreshing metrics for port ' + str(port))
                    logging.warning(traceback.print_exc(file=sys.stdout))
        finally:
            self._metrics_lock.release()

        if not self.metrics:
            logging.error('self.metrics is empty or invalid')
            return False

        logging.debug('success refreshing metrics')
        logging.debug('metrics: ' + str(self.metrics))

        return True

    def refresh_settings(self):
        logging.debug(' refreshing server settings')

        try:
            p = subprocess.Popen(executable=self.php_fpm_bin, args=[self.php_fpm_bin, '-v'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()

            self._settings_lock.acquire()
            self.settings = {}
            for line in out.split('\n'):
                if line.startswith('PHP '):
                    key = self.prefix + 'server_version'
                else:
                    continue

                logging.debug('  line: ' + str(line))

                self.settings[key] = line
        except:
            logging.warning('error refreshing settings')
            return False
        finally:
            self._settings_lock.release()

        logging.debug('success refreshing server settings')
        logging.debug('server_settings: ' + str(self.settings))

        return True

    def metric_of(self, name):
        logging.debug('getting metric: ' + name)

        try:
            if name in self.metrics:
                try:
                    self._metrics_lock.acquire()
                    logging.debug('metric: %s = %s' % (name, self.metrics[name]))
                    return self.metrics[name]
                finally:
                    self._metrics_lock.release()
        except:
            logging.warning('failed to fetch ' + name)
            return 0

    def setting_of(self, name):
        logging.debug('getting setting: ' + name)

        try:
            if name in self.settings:
                try:
                    self._settings_lock.acquire()
                    logging.debug('setting: %s = %s' % (name, self.settings[name]))
                    return self.settings[name]
                finally:
                    self._settings_lock.release()
        except:
            logging.warning('failed to fetch ' + name)
            return 0

def _create_descriptors(params):
    METRIC_DEFAULTS = {
        'time_max': 60,
        'units': 'processes',
        'groups': 'php_fpm',
        'slope': 'both',
        'value_type': 'uint',
        'format': '%d',
        'description': '',
        'call_back': metric_of
    }

    descriptions = dict(
        pool_name={
            'value_type': 'string',
            'format': '%s',
            'slope': 'zero',
            'units': '',
            'description': 'Pool name'},

        process_manager={
            'value_type': 'string',
            'format': '%s',
            'slope': 'zero',
            'units': '',
            'description': 'Process Manager Type'},

        accepted_connections={
            'units': 'connections',
            'slope': 'positive',
            'description': 'Total number of accepted connections'},

        active_processes={
            'description': 'Current active worker processes'},

        idle_processes={
            'description': 'Current idle worker processes'},

        total_processes={
            'description': 'Total worker processes'})

    prefix = str(params['prefix'])
    ports = params['ports'].split(',')

    descriptors = []
    for port in ports:
        for name, desc in descriptions.iteritems():
            d = copy(desc)

            # include the port as part of the prefix only if there are multiple ports
            d['name'] = prefix + (str(port) + "_" if len(ports) > 1 else "") + str(name)

            [ d.setdefault(key, METRIC_DEFAULTS[key]) for key in METRIC_DEFAULTS.iterkeys() ]
            descriptors.append(d)

    # shared settings between all ports
    descriptors.append({
        'name': prefix + "server_version",
        'value_type': 'string',
        'format': '%s',
        'slope': 'zero',
        'units': '',
        'call_back': setting_of,
        'time_max': 60,
        'groups': 'php_fpm',
        'description': 'PHP-FPM version number'})

    return descriptors

def metric_init(params):
    logging.debug('init: ' + str(params))
    global _Worker_Thread

    if _Worker_Thread is not None:
        raise Exception('Worker thread already exists')

    descriptors = _create_descriptors(params)

    _Worker_Thread = UpdatePhpFpmThread(params)
    _Worker_Thread.refresh_metrics()
    _Worker_Thread.refresh_settings()
    _Worker_Thread.start()

    return descriptors


def metric_of(name):
    global _Worker_Thread
    return _Worker_Thread.metric_of(name)

def setting_of(name):
    global _Worker_Thread
    return _Worker_Thread.setting_of(name)

def metric_cleanup():
    global _Worker_Thread
    if _Worker_Thread is not None:
        _Worker_Thread.shutdown()
    logging.shutdown()
    # pass

if __name__ == '__main__':
    from optparse import OptionParser

    try:

        logging.debug('running from cmd line')
        parser = OptionParser()
        parser.add_option('-p', '--path', dest='status_path', default='/status', help='URL for PHP-FPM status stub path')
        parser.add_option('-H', '--host', dest='host', default='localhost', help='PHP-FPM host (comma separated list)')
        parser.add_option('-P', '--ports', dest='ports', default='9000', help='PHP-FPM ports')
        parser.add_option('--php-fpm-bin', dest='php_fpm_bin', default='/usr/sbin/php5-fpm', help='path to PHP-FPM binary')
        parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
        parser.add_option('-r', '--refresh-rate', dest='refresh_rate', default=15)
        parser.add_option('--prefix', dest='prefix', default='php_fpm_')
        parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False)

        (options, args) = parser.parse_args()

        descriptors = metric_init({
            'status_path': options.status_path,
            'php_fpm_bin': options.php_fpm_bin,
            'refresh_rate': options.refresh_rate,
            'host': options.host,
            'ports': options.ports,
            'prefix': options.prefix
        })

        if options.debug:
            from pprint import pprint
            pprint(descriptors)

        for d in descriptors:
            v = d['call_back'](d['name'])

            if not options.quiet:
                print ' {0}: {1} {2} [{3}]' . format(d['name'], v, d['units'], d['description'])

        os._exit(1)

    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except StandardError:
        traceback.print_exc()
        os._exit(1)
    finally:
        metric_cleanup()

########NEW FILE########
__FILENAME__ = postgres
import psycopg2
import psycopg2.extras
import syslog
import functools
import time

# Cache for postgres query values, this prevents opening db connections for each metric_handler callback
class Cache(object):
    def __init__(self, expiry):
        self.expiry = expiry
        self.curr_time = 0
        self.last_time = 0
        self.last_value = None

    def __call__(self, func):
        @functools.wraps(func)
        def deco(*args, **kwds):
            self.curr_time = time.time()
            if self.curr_time - self.last_time > self.expiry:
                self.last_value = func(*args, **kwds)
                self.last_time = self.curr_time
            return self.last_value
        return deco

# Queries update the pg_metrics dict with their values based on cache interval
@Cache(60)
def pg_metrics_queries():
    pg_metrics = {}
    db_conn = psycopg2.connect(pgdsn)
    db_curs = db_conn.cursor()

    # single session state query avoids multiple scans of pg_stat_activity
    # state is a different column name in postgres 9.2, previous versions will have to update this query accordingly
    db_curs.execute(
        'select state, waiting, \
        extract(epoch from current_timestamp - xact_start)::int, \
        extract(epoch from current_timestamp - query_start)::int from pg_stat_activity;')
    results = db_curs.fetchall()
    active = 0
    idle = 0
    idleintxn = 0
    waiting = 0
    active_results = []
    for state, waiting, xact_start_sec, query_start_sec in results:
        if state == 'active':
            active = int(active + 1)
            # build a list of query start times where query is active
            active_results.append(query_start_sec)
        if state == 'idle':
            idle = int(idle + 1)
        if state == 'idle in transaction':
            idleintxn = int(idleintxn + 1)
        if waiting == True:
            waitingtrue = int(waitingtrue + 1)

    # determine longest transaction in seconds
    sorted_by_xact = sorted(results, key=lambda tup: tup[2], reverse=True)
    longest_xact_in_sec = (sorted_by_xact[0])[2]
    
    # determine longest active query in seconds
    sorted_by_query = sorted(active_results, reverse=True)
    longest_query_in_sec = sorted_by_query[0]

    pg_metrics.update(
        {'Pypg_idle_sessions':idle,
        'Pypg_active_sessions':active,
        'Pypg_waiting_sessions':waiting,
        'Pypg_idle_in_transaction_sessions':idleintxn,
        'Pypg_longest_xact':longest_xact_in_sec,
        'Pypg_longest_query':longest_query_in_sec})
    
    # locks query
    db_curs.execute('select mode, locktype from pg_locks;')
    results = db_curs.fetchall()
    accessexclusive = 0
    otherexclusive = 0
    shared = 0
    for mode, locktype in results:
        if (mode == 'AccessExclusiveLock' and locktype != 'virtualxid'):
            accessexclusive = int(accessexclusive + 1)
        if (mode != 'AccessExclusiveLock' and locktype != 'virtualxid'):
            if 'Exclusive' in mode:
                otherexclusive = int(otherexclusive + 1)
        if ('Share' in mode and locktype != 'virtualxid'):
            shared = int(shared + 1) 
    pg_metrics.update(
        {'Pypg_locks_accessexclusive':accessexclusive,
        'Pypg_locks_otherexclusive':otherexclusive,
        'Pypg_locks_shared':shared})

    # background writer query returns one row that needs to be parsed
    db_curs.execute(
        'select checkpoints_timed, checkpoints_req, checkpoint_write_time, \
        checkpoint_sync_time, buffers_checkpoint, buffers_clean, \
        buffers_backend, buffers_alloc from pg_stat_bgwriter;')
    results = db_curs.fetchall()
    bgwriter_values = results[0]
    checkpoints_timed = int(bgwriter_values[0])
    checkpoints_req = int(bgwriter_values[1])
    checkpoint_write_time = int(bgwriter_values[2])
    checkpoint_sync_time = int(bgwriter_values[3])
    buffers_checkpoint = int(bgwriter_values[4])
    buffers_clean = int(bgwriter_values[5])
    buffers_backend = int(bgwriter_values[6])
    buffers_alloc = int(bgwriter_values[7])
    pg_metrics.update(
        {'Pypg_bgwriter_checkpoints_timed':checkpoints_timed,
        'Pypg_bgwriter_checkpoints_req':checkpoints_req,
        'Pypg_bgwriter_checkpoint_write_time':checkpoint_write_time,
        'Pypg_bgwriter_checkpoint_sync_time':checkpoint_sync_time,
        'Pypg_bgwriter_buffers_checkpoint':buffers_checkpoint,
        'Pypg_bgwriter_buffers_clean':buffers_clean,
        'Pypg_bgwriter_buffers_backend':buffers_backend,
        'Pypg_bgwriter_buffers_alloc':buffers_alloc})

    # database statistics returns one row that needs to be parsed
    db_curs.execute(
        'select (sum(xact_commit) + sum(xact_rollback)), sum(tup_inserted), \
        sum(tup_updated), sum(tup_deleted), (sum(tup_returned) + sum(tup_fetched)), \
        sum(blks_read), sum(blks_hit) from pg_stat_database;')
    results = db_curs.fetchall()
    pg_stat_db_values = results[0]
    transactions = int(pg_stat_db_values[0])
    inserts = int(pg_stat_db_values[1])
    updates = int(pg_stat_db_values[2])
    deletes = int(pg_stat_db_values[3])
    reads = int(pg_stat_db_values[4])
    blksdisk = int(pg_stat_db_values[5])
    blksmem = int(pg_stat_db_values[6])
    pg_metrics.update(
        {'Pypg_transactions':transactions,
        'Pypg_inserts':inserts,
        'Pypg_updates':updates,
        'Pypg_deletes':deletes,
        'Pypg_reads':reads,
        'Pypg_blks_diskread':blksdisk,
        'Pypg_blks_memread':blksmem})

    # table statistics returns one row that needs to be parsed
    db_curs.execute(
        'select sum(seq_tup_read), sum(idx_tup_fetch), \
        extract(epoch from now() - min(last_vacuum))::int/60/60, \
        extract(epoch from now() - min(last_analyze))::int/60/60 \
        from pg_stat_all_tables;')
    results = db_curs.fetchall()
    pg_stat_table_values = results[0]
    seqscan = int(pg_stat_table_values[0])
    idxfetch = int(pg_stat_table_values[1])
    hours_since_vacuum = int(pg_stat_table_values[2])
    hours_since_analyze = int(pg_stat_table_values[3])
    pg_metrics.update(
        {'Pypg_tup_seqscan':seqscan,
        'Pypg_tup_idxfetch':idxfetch,
        'Pypg_hours_since_last_vacuum':hours_since_vacuum,
        'Pypg_hours_since_last_analyze':hours_since_analyze})

    db_curs.close()
    return pg_metrics

# Metric handler uses dictionary pg_metrics keys to return values from queries based on metric name
def metric_handler(name):
    pg_metrics = pg_metrics_queries()
    return int(pg_metrics[name])     

# Metric descriptors are initialized here 
def metric_init(params):
    HOST = str(params.get('host'))
    PORT = str(params.get('port'))
    DB = str(params.get('dbname'))
    USER = str(params.get('username'))
    PASSWORD = str(params.get('password'))
    
    global pgdsn
    pgdsn = "dbname=" + DB + " host=" + HOST + " user=" + USER + " port=" + PORT + " password=" + PASSWORD

    descriptors = [
        {'name':'Pypg_idle_sessions','units':'Sessions','slope':'both','description':'PG Idle Sessions'},
        {'name':'Pypg_active_sessions','units':'Sessions','slope':'both','description':'PG Active Sessions'},
        {'name':'Pypg_idle_in_transaction_sessions','units':'Sessions','slope':'both','description':'PG Idle In Transaction Sessions'},
        {'name':'Pypg_waiting_sessions','units':'Sessions','slope':'both','description':'PG Waiting Sessions Blocked'},
        {'name':'Pypg_longest_xact','units':'Seconds','slope':'both','description':'PG Longest Transaction in Seconds'},
        {'name':'Pypg_longest_query','units':'Seconds','slope':'both','description':'PG Longest Query in Seconds'},
        {'name':'Pypg_locks_accessexclusive','units':'Locks','slope':'both','description':'PG AccessExclusive Locks read write blocking'},
        {'name':'Pypg_locks_otherexclusive','units':'Locks','slope':'both','description':'PG Exclusive Locks write blocking'},
        {'name':'Pypg_locks_shared','units':'Locks','slope':'both','description':'PG Shared Locks NON blocking'},
        {'name':'Pypg_bgwriter_checkpoints_timed','units':'checkpoints','slope':'positive','description':'PG scheduled checkpoints'},
        {'name':'Pypg_bgwriter_checkpoints_req','units':'checkpoints','slope':'positive','description':'PG unscheduled checkpoints'},
        {'name':'Pypg_bgwriter_checkpoint_write_time','units':'ms','slope':'positive','description':'PG time to write checkpoints to disk'},
        {'name':'Pypg_bgwriter_checkpoint_sync_time','units':'checkpoints','slope':'positive','description':'PG time to sync checkpoints to disk'},
        {'name':'Pypg_bgwriter_buffers_checkpoint','units':'buffers','slope':'positive','description':'PG number of buffers written during checkpoint'},
        {'name':'Pypg_bgwriter_buffers_clean','units':'buffers','slope':'positive','description':'PG number of buffers written by the background writer'},
        {'name':'Pypg_bgwriter_buffers_backend','units':'buffers','slope':'positive','description':'PG number of buffers written directly by a backend'},
        {'name':'Pypg_bgwriter_buffers_alloc','units':'buffers','slope':'positive','description':'PG number of buffers allocated'},
        {'name':'Pypg_transactions','units':'xacts','slope':'positive','description':'PG Transactions'},
        {'name':'Pypg_inserts','units':'tuples','slope':'positive','description':'PG Inserts'},
        {'name':'Pypg_updates','units':'tuples','slope':'positive','description':'PG Updates'},
        {'name':'Pypg_deletes','units':'tuples','slope':'positive','description':'PG Deletes'},
        {'name':'Pypg_reads','units':'tuples','slope':'positive','description':'PG Reads'},
        {'name':'Pypg_blks_diskread','units':'blocks','slope':'positive','description':'PG Blocks Read from Disk'},
        {'name':'Pypg_blks_memread','units':'blocks','slope':'positive','description':'PG Blocks Read from Memory'},
        {'name':'Pypg_tup_seqscan','units':'tuples','slope':'positive','description':'PG Tuples sequentially scanned'},
        {'name':'Pypg_tup_idxfetch','units':'tuples','slope':'positive','description':'PG Tuples fetched from indexes'},
        {'name':'Pypg_hours_since_last_vacuum','units':'hours','slope':'both','description':'PG hours since last vacuum'},
        {'name':'Pypg_hours_since_last_analyze','units':'hours','slope':'both','description':'PG hours since last analyze'}]

    for d in descriptors:
        # Add default values to dictionary
        d.update({'call_back': metric_handler, 'time_max': 90, 'value_type': 'uint', 'format': '%d', 'groups': 'Postgres'})

    return descriptors

# ganglia requires metric cleanup
def metric_cleanup():
    '''Clean up the metric module.'''
    pass

# this code is for debugging and unit testing    
if __name__ == '__main__':
    descriptors = metric_init({"host":"hostname_goes_here","port":"port_goes_here","dbname":"database_name_goes_here","username":"username_goes_here","password":"password_goes_here"})
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)
        time.sleep(5)


########NEW FILE########
__FILENAME__ = procstat
###  This script reports process metrics to ganglia.
###
###  Notes:
###    This script exposes values for CPU and memory utilization
###    for running processes. You can retrieve the process ID from
###    either providing a pidfile or an awk regular expression.
###    Using a pidfile is the most efficient and direct method.
###
###    When using a regular expression, keep in mind that there is
###    a chance for a false positive. This script will help to avoid
###    these by only returning parent processes. This means that
###    the results are limited to processes where ppid = 1.
###
###    This script also comes with the ability to test your regular
###    expressions via command line arguments "-t".
###
###  Testing:
###   -- This is a correct examples of how to monitor apache.
###
###      $ python procstat.py -p httpd -v '/var/run/httpd.pid' -t
###       Testing httpd: /var/run/httpd.pid
###       Processes in this group:
###       PID, ARGS
###       11058 /usr/sbin/httpd
###       8817 /usr/sbin/httpd
###       9000 /usr/sbin/httpd
###       9001 /usr/sbin/httpd
###
###       waiting 2 seconds
###       procstat_httpd_mem: 202076 KB [The total memory utilization]
###       procstat_httpd_cpu: 0.3 percent [The total percent CPU utilization]
###
###   -- This example shows a regex that returns no processes with a
###      ppid of 1.
###
###      $ python procstat.py -p test -v 'wrong' -t
###       Testing test: wrong
###       failed getting pgid: no process returned
###      ps -Ao pid,ppid,pgid,args | awk 'wrong && $2 == 1 && !/awk/ && !/procstat\.py/ {print $0}'
###
###   -- This example shows a regex that returns more than one process
###      with a ppid of 1.
###
###      $ python procstat.py -p test -v '/mingetty/' -t
###       Testing test: /mingetty/
###       failed getting pgid: more than 1 result returned
###      ps -Ao pid,ppid,pgid,args | awk '/mingetty/ && $2 == 1 && !/awk/ && !/procstat\.py/ {print $0}'
###       7313     1  7313 /sbin/mingetty tty1
###       7314     1  7314 /sbin/mingetty tty2
###       7315     1  7315 /sbin/mingetty tty3
###       7316     1  7316 /sbin/mingetty tty4
###       7317     1  7317 /sbin/mingetty tty5
###       7318     1  7318 /sbin/mingetty tty6
###
###  Command Line Example:
###    $ python procstat.py -p httpd,opennms,splunk,splunk-web \
###    -v '/var/run/httpd.pid','/opt/opennms/logs/daemon/opennms.pid','/splunkd.*start/','/twistd.*SplunkWeb/'
###
###     procstat_httpd_mem: 202068 KB [The total memory utilization]
###     procstat_splunk_mem: 497848 KB [The total memory utilization]
###     procstat_splunk-web_mem: 32636 KB [The total memory utilization]
###     procstat_opennms_mem: 623112 KB [The total memory utilization]
###     procstat_httpd_cpu: 0.3 percent [The total percent CPU utilization]
###     procstat_splunk_cpu: 0.6 percent [The total percent CPU utilization]
###     procstat_splunk-web_cpu: 0.1 percent [The total percent CPU utilization]
###     procstat_opennms_cpu: 7.1 percent [The total percent CPU utilization]
###
###  Example Values:
###    httpd:      /var/run/httpd.pid or \/usr\/sbin\/httpd
###    mysqld:     /var/run/mysqld/mysqld.pid or /\/usr\/bin\/mysqld_safe/
###    postgresql: /var/run/postmaster.[port].pid or /\/usr\/bin\/postmaster.*[port]/
###    splunk:     /splunkd.*start/
###    splunk-web: /twistd.*SplunkWeb/
###    opennms:    /opt/opennms/logs/daemon/opennms.pid or java.*Dopennms
###    netflow:    /java.*NetFlow/
###    postfix:    /var/spool/postfix/pid/master.pid or /\/usr\/libexec\/postfix\/master/
###
###  Error Tests:
###    python procstat.py -p test-more,test-none,test-pidfail -v '/java/','/javaw/','java.pid' -t
###
###  Changelog:
###    v1.0.1 - 2010-07-23
###      * Initial version
###
###    v1.1.0 - 2010-07-28
###      * Modified the process regex search to find the parent
###        process and then find all processes with the same process
###        group ID (pgid). "ps" is only used for regex searching on
###        the initial lookup for the parent pid (ppid). Now all
###        subsequent calls use /proc/[pid]/stat for CPU jiffies, and
###        /proc/[pid]/statm for memory rss.
###      * Added testing switch "-t" to help troubleshoot a regex
###      * Added display switches "-s" and "-m" to format the output
###        of /proc/[pid]/stat and /proc/[pid]/statm
###

###  Copyright Jamie Isaacs. 2010
###  License to use, modify, and distribute under the GPL
###  http://www.gnu.org/licenses/gpl.txt

import time
import subprocess
import traceback, sys
import os.path
import glob
import logging

descriptors = []

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
logging.debug('starting up')

last_update = 0
stats = {}
last_val = {}
pgid_list = {}

MAX_UPDATE_TIME = 15

# clock ticks per second... jiffies (HZ)
JIFFIES_PER_SEC = os.sysconf('SC_CLK_TCK')

PAGE_SIZE=os.sysconf('SC_PAGE_SIZE')

PROCESSES = {}

def readCpu(pid):
	try:
		stat = file('/proc/' + pid + '/stat', 'rt').readline().split()
		#logging.debug(' stat (' + pid + '): ' + str(stat))
		utime = int(stat[13])
		stime = int(stat[14])
		cutime = int(stat[15])
		cstime = int(stat[16])
		return (utime + stime + cutime + cstime)
	except:
		logging.warning('failed to get (' + str(pid) + ') stats')
		return 0

def get_pgid(proc):
	logging.debug('getting pgid for process: ' + proc)
	ERROR = 0

	if pgid_list.has_key(proc) and os.path.exists('/proc/' + pgid_list[proc][0]):
		return pgid_list[proc]

	val = PROCESSES[proc]
	# Is this a pidfile? Last 4 chars are .pid
	if '.pid' in val[-4:]:
		if os.path.exists(val):
			logging.debug(' pidfile found')
			ppid = file(val, 'rt').readline().strip()
			pgid = file('/proc/' + ppid + '/stat', 'rt').readline().split()[4]
		else:
			raise Exception('pidfile (' + val + ') does not exist')

	else:
		# This is a regex, lets search for it
		regex = PROCESSES[proc]
		cmd = "ps -Ao pid,ppid,pgid,args | awk '" + regex + " && $2 == 1 && !/awk/ && !/procstat\.py/ {print $0}'"
		p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = p.communicate()

		if p.returncode:
			raise Exception('failed executing ps\n' + cmd + '\n' + err)

		result = out.strip().split('\n')
		logging.debug(' result: ' + str(result))

		if len(result) > 1:
			raise Exception('more than 1 result returned\n' + cmd + '\n' + out.strip())

		if result[0] in '':
			raise Exception('no process returned\n' + cmd)

		res = result[0].split()
		ppid = res[0]
		pgid = res[2]

	if os.path.exists('/proc/' + ppid):
		logging.debug(' ppid: ' + ppid + ' pgid: ' + pgid)
		return (ppid, pgid)
	else:
		return ERROR

def get_pgroup(ppid, pgid):
	'''Return a list of pids having the same pgid, with the first in the list being the parent pid.'''
	logging.debug('getting pids for ppid/pgid: ' + ppid + '/' + pgid)

	try:
		# Get all processes in this group
		p_list = []
		for stat_file in glob.glob('/proc/[1-9]*/stat'):
			stat = file(stat_file, 'rt').readline().split()
			if stat[4] == pgid:
				p_list.append(stat[0])

		# place pid at the top of the list
		p_list.remove(ppid)
		p_list.insert(0, ppid)

		logging.debug('p_list: ' + str(p_list))

		return p_list

	except:
		logging.warning('failed getting pids')

def get_rss(pids):
	logging.debug('getting rss for pids')

	rss = 0
	for p in pids:
		try:
			statm = open('/proc/' + p + '/statm', 'rt').readline().split()
			#logging.debug(' statm (' + p + '): ' + str(statm))
		except:
			# Process finished, ignore this mem usage
			logging.warning(' failed getting statm for pid: ' + p)
			continue

		rss += int(statm[1])

	rss *= PAGE_SIZE
	return rss

def test(params):
	global PROCESSES, MAX_UPDATE_TIME

	MAX_UPDATE_TIME = 2

	logging.debug('testing processes: ' + str(params))

	PROCESSES = params

	for proc,val in PROCESSES.items():
		print('')
		print(' Testing ' + proc + ': ' + val) 

		try:
			(ppid, pgid) = get_pgid(proc)
		except Exception, e:
			print(' failed getting pgid: ' + str(e))
			continue

		pids = get_pgroup(ppid, pgid)

		print(' Processes in this group: ')
		print(' PID, ARGS')
		for pid in pids:
			# Read from binary file containing command line arguments
			args = file('/proc/' + pid + '/cmdline', 'rt').readline().replace('\0', ' ')
			print(' ' + pid + ' ' + args)

	logging.debug('success testing')

def update_stats():
	logging.debug('updating stats')
	global last_update, stats, last_val
	
	cur_time = time.time()

	if cur_time - last_update < MAX_UPDATE_TIME:
		logging.debug(' wait ' + str(int(MAX_UPDATE_TIME - (cur_time - last_update))) + ' seconds')
		return True
	else:
		last_update = cur_time

	for proc,val in PROCESSES.items():
		logging.debug(' updating for ' + proc)

		# setup storage lists
		if not proc in stats:
			stats[proc] = {}
		if not proc in last_val:
			last_val[proc] = {}

		#####
		# Update CPU utilization
		try:
			(ppid, pgid) = get_pgid(proc)
		except Exception, e:
			logging.warning(' failed getting pgid: ' + str(e))
			stats[proc]['cpu'] = 0.0
			stats[proc]['mem'] = 0
			continue

		# save for later
		pgid_list[proc] = (ppid, pgid)

		pids = get_pgroup(ppid, pgid)

		cpu_time = time.time()
		proc_time = 0
		for p in pids:
			proc_time += readCpu(p)
		
		logging.debug(' proc_time: ' + str(proc_time) + ' cpu_time: ' + str(cpu_time))

		# do we have an old value to calculate with?
		if 'cpu_time' in last_val[proc]:
			logging.debug(' last_val: ' + str(last_val[proc]))
			logging.debug(' calc: 100 * ' + str(proc_time - last_val[proc]['proc_time']) + ' / ' + str(cpu_time - last_val[proc]['cpu_time']) + ' * ' + str(JIFFIES_PER_SEC))
			stats[proc]['cpu'] = 100 * (proc_time - last_val[proc]['proc_time']) / float((cpu_time - last_val[proc]['cpu_time']) * JIFFIES_PER_SEC)

			logging.debug(' calc: ' + str(stats[proc]['cpu']))
		else:
			stats[proc]['cpu'] = 0.0

		last_val[proc]['cpu_time'] = cpu_time
		last_val[proc]['proc_time'] = proc_time

		#####
		# Update Mem utilization	
		rss = get_rss(pids)
		stats[proc]['mem'] = rss
	
	logging.debug('success refreshing stats')
	logging.debug('stats: ' + str(stats))

	return True

def get_stat(name):
	logging.debug('getting stat: ' + name)

	ret = update_stats()

	if ret:
		if name.startswith('procstat_'):
			fir = name.find('_')
			sec = name.find('_', fir + 1)

			proc = name[fir+1:sec]
			label = name[sec+1:]

			try:
				return stats[proc][label]
			except:
				logging.warning('failed to fetch [' + proc + '] ' + name)
				return 0
		else:
			label = name

		try:
			return stats[label]
		except:
			logging.warning('failed to fetch ' + name)
			return 0
	else:
		return 0

def metric_init(params):
	global descriptors
	global PROCESSES

	logging.debug('init: ' + str(params))

	PROCESSES = params

	#for proc,regex in PROCESSES.items():
		
	update_stats()

	descriptions = dict(
		cpu = {
			'units': 'percent',
			'value_type': 'float',
			'format': '%.1f',
			'description': 'The total percent CPU utilization'},

		mem = {
			'units': 'B',
			'description': 'The total memory utilization'}
	)

	time_max = 60
	for label in descriptions:
		for proc in PROCESSES:
			if stats[proc].has_key(label):

				d = {
					'name': 'procstat_' + proc + '_' + label,
					'call_back': get_stat,
					'time_max': time_max,
					'value_type': 'uint',
					'units': '',
					'slope': 'both',
					'format': '%u',
					'description': label,
					'groups': 'procstat'
				}

				# Apply metric customizations from descriptions
				d.update(descriptions[label])

				descriptors.append(d)

			else:
				logging.error("skipped " + proc + '_' + label)

	#logging.debug('descriptors: ' + str(descriptors))

	return descriptors

def display_proc_stat(pid):
	try:
		stat = file('/proc/' + pid + '/stat', 'rt').readline().split()

		fields = [
			'pid', 'comm', 'state', 'ppid', 'pgrp', 'session',
			'tty_nr', 'tty_pgrp', 'flags', 'min_flt', 'cmin_flt', 'maj_flt',
			'cmaj_flt', 'utime', 'stime', 'cutime', 'cstime', 'priority',
			'nice', 'num_threads', 'it_real_value', 'start_time', 'vsize', 'rss',
			'rlim', 'start_code', 'end_code', 'start_stack', 'esp', 'eip',
			'pending', 'blocked', 'sigign', 'sigcatch', 'wchan', 'nswap',
			'cnswap', 'exit_signal', 'processor', 'rt_priority', 'policy'
		]

		# Display them
		i = 0
		for f in fields:
			print '%15s: %s' % (f, stat[i])
			i += 1

	except:
		print('failed to get /proc/' + pid + '/stat')
		print(traceback.print_exc(file=sys.stdout))

def display_proc_statm(pid):
	try:
		statm = file('/proc/' + pid + '/statm', 'rt').readline().split()

		fields = [
			'size', 'rss', 'share', 'trs', 'drs', 'lrs' ,'dt' 
		]

		# Display them
		i = 0
		for f in fields:
			print '%15s: %s' % (f, statm[i])
			i += 1

	except:
		print('failed to get /proc/' + pid + '/statm')
		print(traceback.print_exc(file=sys.stdout))

def metric_cleanup():
	logging.shutdown()
	# pass

if __name__ == '__main__':
	from optparse import OptionParser
	import os

	logging.debug('running from cmd line')
	parser = OptionParser()
	parser.add_option('-p', '--processes', dest='processes', default='', help='processes to explicitly check')
	parser.add_option('-v', '--value', dest='value', default='', help='regex or pidfile for each processes')
	parser.add_option('-s', '--stat', dest='stat', default='', help='display the /proc/[pid]/stat file for this pid')
	parser.add_option('-m', '--statm', dest='statm', default='', help='display the /proc/[pid]/statm file for this pid')
	parser.add_option('-b', '--gmetric-bin', dest='gmetric_bin', default='/usr/bin/gmetric', help='path to gmetric binary')
	parser.add_option('-c', '--gmond-conf', dest='gmond_conf', default='/etc/ganglia/gmond.conf', help='path to gmond.conf')
	parser.add_option('-g', '--gmetric', dest='gmetric', action='store_true', default=False, help='submit via gmetric')
	parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False)
	parser.add_option('-t', '--test', dest='test', action='store_true', default=False, help='test the regex list')

	(options, args) = parser.parse_args()

	if options.stat != '':
		display_proc_stat(options.stat)
		sys.exit(0)
	elif options.statm != '':
		display_proc_statm(options.statm)
		sys.exit(0)

	_procs = options.processes.split(',')
	_val = options.value.split(',')
	params = {}
	i = 0
	for proc in _procs:
		params[proc] = _val[i]
		i += 1
	
	if options.test:
		test(params)
		update_stats()

		print('')
		print(' waiting ' + str(MAX_UPDATE_TIME) + ' seconds')
		time.sleep(MAX_UPDATE_TIME)

	metric_init(params)

	for d in descriptors:
		v = d['call_back'](d['name'])
		if not options.quiet:
			print ' %s: %s %s [%s]' % (d['name'], d['format'] % v, d['units'], d['description'])

		if options.gmetric:
			if d['value_type'] == 'uint':
				value_type = 'uint32'
			else:
				value_type = d['value_type']

			cmd = "%s --conf=%s --value='%s' --units='%s' --type='%s' --name='%s' --slope='%s'" % \
				(options.gmetric_bin, options.gmond_conf, v, d['units'], value_type, d['name'], d['slope'])
			os.system(cmd)



########NEW FILE########
__FILENAME__ = rabbitmq
#!/usr/bin/python2.4
import sys
import os
import json
import urllib2
import time
from string import Template
import itertools
import threading

global url, descriptors, last_update, vhost, username, password, url_template, result, result_dict, keyToPath


JSON_PATH_SEPARATOR = "?"
METRIC_TOKEN_SEPARATOR = "___"
 
INTERVAL = 10
descriptors = list()
username, password = "guest", "guest"
stats = {}
keyToPath = {}
last_update = None
#last_update = {}
compiled_results = {"nodes" : None, "queues" : None, "connections" : None}
#Make initial stat test time dict
#for stat_type in ('queues', 'connections','exchanges', 'nodes'):
#    last_update[stat_type] = None

### CONFIGURATION SECTION ###
STATS = ['nodes', 'queues']

# QUEUE METRICS #
keyToPath['rmq_messages_ready'] = "%s{0}messages_ready".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_messages_unacknowledged'] = "%s{0}messages_unacknowledged".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_ack_egress_rate'] = "%s{0}backing_queue_status{0}avg_ack_egress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_ack_ingress_rate'] = "%s{0}backing_queue_status{0}avg_ack_ingress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_egress_rate'] = "%s{0}backing_queue_status{0}avg_egress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_ingress_rate'] = "%s{0}backing_queue_status{0}avg_ingress_rate".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_backing_queue_mirror_senders'] = "%s{0}backing_queue_status{0}mirror_senders".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_memory'] = "%s{0}memory".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_consumers'] = "%s{0}consumers".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_messages'] = "%s{0}messages".format(JSON_PATH_SEPARATOR)

RATE_METRICS = [
    'rmq_backing_queue_ack_egress_rate',
    'rmq_backing_queue_ack_ingress_rate',
    'rmq_backing_queue_egress_rate',
    'rmq_backing_queue_ingress_rate'
]

QUEUE_METRICS = ['rmq_messages_ready',
		'rmq_messages_unacknowledged',
		'rmq_backing_queue_ack_egress_rate',
		'rmq_backing_queue_ack_ingress_rate',
		'rmq_backing_queue_egress_rate',
		'rmq_backing_queue_ingress_rate',
		'rmq_backing_queue_mirror_senders',
		'rmq_memory',
                'rmq_consumers',
		'rmq_messages']

# NODE METRICS #
keyToPath['rmq_disk_free'] = "%s{0}disk_free".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_disk_free_alarm'] = "%s{0}disk_free_alarm".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_fd_used'] = "%s{0}fd_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_fd_used'] = "%s{0}fd_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_mem_used'] = "%s{0}mem_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_proc_used'] = "%s{0}proc_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_sockets_used'] = "%s{0}sockets_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_mem_alarm'] = "%s{0}mem_alarm".format(JSON_PATH_SEPARATOR) #Boolean
keyToPath['rmq_mem_binary'] = "%s{0}mem_binary".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_mem_code'] = "%s{0}mem_code".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_mem_proc_used'] = "%s{0}mem_proc_used".format(JSON_PATH_SEPARATOR)
keyToPath['rmq_running'] = "%s{0}running".format(JSON_PATH_SEPARATOR) #Boolean

NODE_METRICS = ['rmq_disk_free', 'rmq_mem_used', 'rmq_disk_free_alarm', 'rmq_running', 'rmq_proc_used', 'rmq_mem_proc_used', 'rmq_fd_used', 'rmq_mem_alarm', 'rmq_mem_code', 'rmq_mem_binary', 'rmq_sockets_used']
	



def metric_cleanup():
    pass

def dig_it_up(obj,path):
    try:
	path = path.split(JSON_PATH_SEPARATOR)
        return reduce(lambda x,y:x[y],path,obj)
    except:
        print "Exception"
        return False

def refreshStats(stats = ('nodes', 'queues'), vhosts = ['/']):

    global url_template
    global last_update, url, compiled_results

    now = time.time()

    if not last_update:
        diff = INTERVAL
    else:
        diff = now - last_update

    if diff >= INTERVAL or not last_update:
	print "Fetching Results after %d seconds" % INTERVAL
	last_update = now
        for stat in stats:
            for vhost in vhosts:
                if stat in ('nodes'):
                    vhost = '/'
		result_dict = {}
                urlstring = url_template.safe_substitute(stats = stat, vhost = vhost)
                print urlstring
                result = json.load(urllib2.urlopen(urlstring))
		# Rearrange results so entry is held in a dict keyed by name - queue name, host name, etc.
		if stat in ("queues", "nodes", "exchanges"):
		    for entry in result:
		        name = entry['name']
			result_dict[name] = entry
		    compiled_results[(stat, vhost)] = result_dict

    return compiled_results


def validatedResult(value):
    if not isInstance(value, bool):
        return float(value)
    else:
        return None

def list_queues(vhost):
    global compiled_results
    queues = compiled_results[('queues', vhost)].keys()
    return queues

def list_nodes():
    global compiled_results
    nodes = compiled_results[('nodes', '/')].keys()
    return nodes

def getQueueStat(name):
    refreshStats(stats = STATS, vhosts = vhosts)
    #Split a name like "rmq_backing_queue_ack_egress_rate.access"
    
    #handle queue names with . in them
    print name
    stat_name, queue_name, vhost = name.split(METRIC_TOKEN_SEPARATOR)
    
    vhost = vhost.replace('-', '/') #decoding vhost from metric name
    # Run refreshStats to get the result object
    result = compiled_results[('queues', vhost)]
    
    value = dig_it_up(result, keyToPath[stat_name] % queue_name)
    
    if zero_rates_when_idle and stat_name in RATE_METRICS  and 'idle_since' in result[queue_name].keys():
        value = 0

    #Convert Booleans
    if value is True:
        value = 1
    elif value is False:
        value = 0

    return float(value)

def getNodeStat(name):
    refreshStats(stats = STATS, vhosts = vhosts)
    #Split a name like "rmq_backing_queue_ack_egress_rate.access"
    stat_name, node_name, vhost = name.split(METRIC_TOKEN_SEPARATOR)
    vhost = vhost.replace('-', '/') #decoding vhost from metric name

    result = compiled_results[('nodes', '/')]
    value = dig_it_up(result, keyToPath[stat_name] % node_name)

    print name,value
    #Convert Booleans
    if value is True:
        value = 1
    elif value is False:
        value = 0

    return float(value)

def product(*args, **kwds):
    # replacement for itertools.product
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x+[y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)

def str2bool(string):
    if string.lower() in ("yes", "true"):
        return True
    if string.lower() in ("no", "false"):
        return False
    raise Exception("Invalid value of the 'zero_rates_when_idle' param, use one of the ('true', 'yes', 'false', 'no')")
    
def metric_init(params):
    ''' Create the metric definition object '''
    global descriptors, stats, vhost, username, password, urlstring, url_template, compiled_results, STATS, vhosts, zero_rates_when_idle
    print 'received the following params:'
    #Set this globally so we can refresh stats
    if 'host' not in params:
        params['host'], params['vhost'],params['username'],params['password'],params['port'] = "localhost", "/", "guest", "guest", "15672"
    if 'zero_rates_when_idle' not in params:
        params['zero_rates_when_idle'] = "false"

    # Set the vhosts as a list split from params
    vhosts = params['vhost'].split(',')
    username, password = params['username'], params['password']
    host = params['host']
    port = params['port']

    zero_rates_when_idle = str2bool(params['zero_rates_when_idle'])
    
    url = 'http://%s:%s/api/$stats/$vhost' % (host,port)
    base_url = 'http://%s:%s/api' % (host,port)
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, base_url, username, password)
    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    opener = urllib2.build_opener(handler)
    opener.open(base_url)
    urllib2.install_opener(opener)
    url_template = Template(url)
    print params

    refreshStats(stats = STATS, vhosts = vhosts)

    def metric_handler(name):
        if 15 < time.time() - metric_handler.timestamp:
            metric_handler.timestamp = time.time()
            return refreshStats(stats = STATS, vhosts = vhosts)

            

    def create_desc(prop):
	d = {
	    'name'        : 'XXX',
	    'call_back'   : getQueueStat,
	    'time_max'    : 60,
	    'value_type'  : 'uint',
	    'units'       : 'units',
	    'slope'       : 'both',
	    'format'      : '%d',
	    'description' : 'XXX',
	    'groups'      : params["metric_group"],
	}

	for k,v in prop.iteritems():
	    d[k] = v
	return d


    def buildQueueDescriptors():
        for vhost, metric in product(vhosts, QUEUE_METRICS):
            queues = list_queues(vhost)
            for queue in queues:
                name = "{1}{0}{2}{0}{3}".format(METRIC_TOKEN_SEPARATOR, metric, queue, vhost.replace('/', '-'))
		print name
		d1 = create_desc({'name': name.encode('ascii','ignore'),
		    'call_back': getQueueStat,
                    'value_type': 'float',
		    'units': 'N',
		    'slope': 'both',
		    'format': '%f',
		    'description': 'Queue_Metric',
		    'groups' : 'rabbitmq,queue'})
		print d1
		descriptors.append(d1)
    
    def buildNodeDescriptors():
        for metric in NODE_METRICS:
            for node in list_nodes():
                name = "{1}{0}{2}{0}-".format(METRIC_TOKEN_SEPARATOR, metric, node)
                print name
                d2 = create_desc({'name': name.encode('ascii','ignore'),
		    'call_back': getNodeStat,
                    'value_type': 'float',
		    'units': 'N',
		    'slope': 'both',
		    'format': '%f',
		    'description': 'Node_Metric',
		    'groups' : 'rabbitmq,node'}) 
                print d2
                descriptors.append(d2)

    buildQueueDescriptors()
    buildNodeDescriptors()
    # buildTestNodeStat()
	
    return descriptors

def metric_cleanup():
    pass
  

if __name__ == "__main__":
    url = 'http://%s:%s@localhost:15672/api/$stats' % (username, password)
    url_template = Template(url)
    print "url_template is ", url_template
### in config files we use '/' in vhosts names but we should convert '/' to '-' when calculating a metric
    parameters = {"vhost":"/", "username":"guest","password":"guest", "metric_group":"rabbitmq", "zero_rates_when_idle": "yes"}
    metric_init(parameters)
    result = refreshStats(stats = ('queues', 'nodes'), vhosts = ('/'))
    print '***'*20
    getQueueStat('rmq_backing_queue_ack_egress_rate___nfl_client___-')
    getNodeStat('rmq_disk_free___rmqone@inrmq01d1___-')
    getNodeStat('rmq_mem_used___rmqone@inrmq01d1___-')

########NEW FILE########
__FILENAME__ = recoverpoint
#!/usr/bin/python
# Name: recoverpoint.py
# Desc: Ganglia Python module for gathering EMC recoverpoint statistics via SSH
# Author: Evan Fraser (evan.fraser@trademe.co.nz)
# Date: 01/08/2012
# Compatibility note: Compatible with Recoverpoint version 3.5


import yaml
import warnings
import pprint
import time
import threading
import re

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import paramiko

descriptors = list()
NIMETRICS = {
    'time' : 0,
    'data' : {}
}
#This is the minimum interval between querying the RPA for metrics.
#Each ssh query takes 1.6s so we limit the interval between getting metrics to this interval.
NIMETRICS_CACHE_MAX = 10
RAWDATA = ""

ipaddr = ''

#Example of data structure:
#{'RPA statistics': {'Site 1 RPA 1': {'Compression CPU usage': '0.00%',
#                                       'Latency (ms)': 12,
#                                       'Packet loss': '0.00%',
#                                       'Traffic': {'Application': {'SAN': '0 bps',
#                                                                   'WAN': '432 bps'},
#                                                   'Application (writes)': 0,
#                                                   'Compression': 0}},

def define_metrics(Desc_Skel, statsDict):
    for rpa in statsDict['RPA statistics']:
        #pprint.pprint(statsDict['RPA statistics'][rpa])
        for metric in statsDict['RPA statistics'][rpa].keys():
            if "Latency (ms)" in metric:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : (rpa.lower()).replace(' ','_') + '_latency',
                            "units"       : "ms",
                            "description" : "latency in ms",
                            "groups"      : "Latency"
                            }))
            if "Traffic" in metric:
                #define the Appliance/[SAN|WAN] metrics
                for net in statsDict['RPA statistics'][rpa]['Traffic']['Application'].keys():
                    #print net
                    descriptors.append(create_desc(Desc_Skel, {
                                "name"        : (rpa.lower()).replace(' ','_') + '_' + net.lower(),
                                "units"       : "bits/sec",
                                "description" : net + ' traffic',
                                "groups"      : net + " Traffic",
                                }))

    #Define Consistency Group metrics this is paintfully nested in the dict.
    for group in statsDict['Group']:
        #CG SAN and Journal lag are under the policies
        for policyname in statsDict['Group'][group]['Copy stats']:
            if 'SAN traffic' in statsDict['Group'][group]['Copy stats'][policyname]:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : group + '_SAN_Traffic',
                            "units"       : 'Bits/s',
                            "description" : group + ' SAN Traffic',
                            "groups"      : 'SAN Traffic',
                            }))
            elif 'Journal' in statsDict['Group'][group]['Copy stats'][policyname]:
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : group + '_Journal_Lag',
                            "units"       : 'Bytes',
                            "description" : group + ' Journal Lag',
                            "groups"      : 'Lag',
                            }))
                #Protection window
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : group + '_Protection_Window',
                            "units"       : 'mins',
                            "description" : group + ' Protection Window',
                            "groups"      : 'Protection',
                            }))

        #CG Lag and WAN stats are in the Link stats section
        for repname in statsDict['Group'][group]['Link stats']:
            #Define CG WAN traffic metrics
            descriptors.append(create_desc(Desc_Skel, {
                        "name"        : group + '_WAN_Traffic',
                        "units"       : 'Bits/s',
                        "description" : group + ' WAN Traffic',
                        "groups"      : 'WAN Traffic',
                        }))
            
            #Define CG Lag metrics
            for lagfields in statsDict['Group'][group]['Link stats'][repname]['Replication']['Lag']:
                lagunit = ''
                if 'Writes' in lagfields:
                    lagunit = 'Writes'
                elif 'Data' in lagfields:
                    lagunit = 'Bytes'
                elif 'Time' in lagfields:
                    lagunit = 'Seconds'
                descriptors.append(create_desc(Desc_Skel, {
                            "name"        : group + '_Lag_' + lagfields,
                            "units"       : lagunit,
                            "description" : group + ' Lag ' + lagunit,
                            "groups"      : 'Lag',
                            }))
                
    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d


def run_ssh_thread(foo,bar):
    global RAWDATA
    sshcon = paramiko.SSHClient()
    sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sshcon.connect(ipaddr, username='monitor',password='monitor',look_for_keys='False')
    stdin, stdout, sterr = sshcon.exec_command("get_system_statistics;get_group_statistics")
    RAWDATA = stdout.read()
    

    
def get_metrics(name):
    global NIMETRICS,ipaddr
    # if interval since last check > NIMETRICS_CACHE_MAX get metrics again
    metrics = {}
    if (time.time() - NIMETRICS['time']) > NIMETRICS_CACHE_MAX:
        threading.Thread(run_ssh_thread(1,1))
        rawdata = RAWDATA
        #Group stats don't leave a space after the colon in some places
        rawmetrics = yaml.safe_load(rawdata.replace(':N',': N').replace("Compression","\n      Compression"))
        #Get RPA metrics
        for rpa in rawmetrics['RPA statistics']:
            for metric in rawmetrics['RPA statistics'][rpa]:
                if "Latency (ms)" in metric:
                    metrics[(rpa.lower()).replace(' ','_') + '_latency'] = rawmetrics['RPA statistics'][rpa]['Latency (ms)']
                if "Traffic" in metric:
                    #store the Application/[SAN|WAN] metrics
                    for net in rawmetrics['RPA statistics'][rpa]['Traffic']['Application'].keys():
                        traffic,junk = rawmetrics['RPA statistics'][rpa]['Traffic']['Application'][net].split()
                        metrics[(rpa.lower()).replace(' ','_') + '_' + net.lower()] = float(traffic)

        for group in rawmetrics['Group']:
            #CG SAN and Journal lag are under the policies
            for policyname in rawmetrics['Group'][group]['Copy stats']:
                #Get CG SAN metrics (Work out the unit from end + convert to float and then bits)
                if 'SAN traffic' in rawmetrics['Group'][group]['Copy stats'][policyname]:
                    cg_san_str = rawmetrics['Group'][group]['Copy stats'][policyname]['SAN traffic']['Current throughput']
                    cg_san_bw = float(cg_san_str[:-4])
                    cg_san_unit = cg_san_str[-4:]
                    if 'Mbps' in cg_san_unit:
                        cg_san_bw = cg_san_bw * 1024 * 1024
                    else:
                        cg_san_bw = cg_san_bw * 1024
                    metrics[group + '_SAN_Traffic'] = cg_san_bw


                elif 'Journal' in rawmetrics['Group'][group]['Copy stats'][policyname]:
                    datastr = rawmetrics['Group'][group]['Copy stats'][policyname]['Journal']['Journal lag']
                    amount = float(datastr[:-2])
                    unitstr = datastr[-2:]
                    if 'MB' in unitstr:
                        amount = amount * 1024 * 1024
                    elif 'KB' in unitstr:
                        amount = amount * 1024
                    elif 'GB' in unitstr:
                        amount = amount * 1024 * 1024 * 1024
                    metrics[group + '_Journal_Lag'] = amount
                    #Protection Window is in Journal section
                    prowindowstr = rawmetrics['Group'][group]['Copy stats'][policyname]['Journal']['Protection window']['Current']['Value']
                    protectmins = 0
                    protimelist = prowindowstr.split(' ')
                    if 'hr' in protimelist:
                        hrindex = protimelist.index('hr')
                        protectmins = protectmins + (int(protimelist[int(hrindex) - 1]) * 60)
                    if 'min' in protimelist:
                        minindex = protimelist.index('min')
                        protectmins = protectmins + int(protimelist[int(minindex) -1])
                    metrics[group + '_Protection_Window'] = float(protectmins)
                                                     
            #CG Lag and WAN stats are in the Link stats section
            for repname in rawmetrics['Group'][group]['Link stats']:
                #Get CG WAN metrics (Work out the unit from end + convert to float and then bits) 
                ##(remove 'Mbps' from end + convert to float and then bits)
                #metrics[group + '_WAN_Traffic'] = float(rawmetrics['Group'][group]['Link stats'][repname]['Replication']['WAN traffic'][:-4]) * 1024 * 1024
                cg_wan_str = rawmetrics['Group'][group]['Link stats'][repname]['Replication']['WAN traffic']
                cg_wan_bw = float(cg_wan_str[:-4])
                cg_wan_unit = cg_wan_str[-4:]
                if 'Mbps' in cg_wan_unit:
                    cg_wan_bw = cg_wan_bw * 1024 * 1024
                else:
                    cg_wan_bw = cg_wan_bw * 1024
                metrics[group + '_WAN_Traffic'] = cg_wan_bw

                #Get CG Lag metrics
                for lagfields in rawmetrics['Group'][group]['Link stats'][repname]['Replication']['Lag']:
                    if 'Data' in lagfields:
                        #Convert 12.34(GB|MB|KB) to bytes
                        datastr = rawmetrics['Group'][group]['Link stats'][repname]['Replication']['Lag'][lagfields]
                        #print datastr
                        amount = float(datastr[:-2])
                        unitstr = datastr[-2:]
                        if 'MB' in unitstr:
                            amount = amount * 1024 * 1024
                        elif 'KB' in unitstr:
                            amount = amount * 1024
                        elif 'GB' in unitstr:
                            amount = amount * 1024 * 1024 * 1024
                        metrics[group + '_Lag_' + lagfields] = amount
                        
                    elif 'Time' in lagfields:
                        #Strip 'sec' from value, convert to float.
                        lagtime = float(rawmetrics['Group'][group]['Link stats'][repname]['Replication']['Lag'][lagfields][:-3])
                        metrics[group + '_Lag_' + lagfields] = lagtime
                    else:
                        #Writes Lag
                        metrics[group + '_Lag_' + lagfields] = float(rawmetrics['Group'][group]['Link stats'][repname]['Replication']['Lag'][lagfields])
                        
        NIMETRICS = {
            'time': time.time(),
            'data': metrics
            }
    else:
        metrics = NIMETRICS['data']
    return metrics[name]
    
    

def metric_init(params):
    global descriptors, Desc_Skel, ipaddr, RAWDATA
    print '[recoverpoint] Recieved the following parameters'
    print params
    ipaddr = params['mgmtip']
    print ipaddr
    spoof_string = ipaddr + ':recoverpoint'
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_metrics,
        'time_max'    : 60,
        'value_type'  : 'double',
        'format'      : '%0f',
        'units'       : 'XXX',
        'slope'       : 'both',
        'description' : 'XXX',
        'groups'      : 'netiron',
        'spoof_host'  : spoof_string
        }  

    sshcon = paramiko.SSHClient()
    sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sshcon.connect(ipaddr, username='monitor',password='monitor',look_for_keys='False')
    stdin, stdout, sterr = sshcon.exec_command("get_system_statistics;get_group_statistics")
    rawdata = stdout.read()
    RAWDATA = rawdata
#    f = 
    #Group stats don't leave a space after the colon in some places
    statsDict = yaml.safe_load(rawdata.replace(':N',': N').replace("Compression","\n      Compression"))
    sshcon.close()
    descriptors = define_metrics(Desc_Skel, statsDict)

    return descriptors

# For CLI Debuging:
if __name__ == '__main__':
    params = {
        'mgmtip' : '192.168.1.100',
        
              }
    descriptors = metric_init(params)
    pprint.pprint(descriptors)
    print len(descriptors)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)        
        print 'Sleeping 5 seconds'
        time.sleep(5)
#exit(0)

########NEW FILE########
__FILENAME__ = redis-gmond
import socket
import time
#import logging

#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
#logging.debug('starting up')

def metric_handler(name):

    # Update from Redis.  Don't thrash.
    if 15 < time.time() - metric_handler.timestamp:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((metric_handler.host, metric_handler.port))
        if metric_handler.auth is not None:
            s.send("*2\r\n$4\r\nAUTH\r\n$%d\r\n%s\r\n" % (len(metric_handler.auth), metric_handler.auth))
            result = s.recv(100)
            if not 'OK' in result:
                return 0
        s.send("*1\r\n$4\r\nINFO\r\n")
        #logging.debug("sent INFO")
        info = s.recv(4096)
        #logging.debug("rcvd INFO")
        if "$" != info[0]:
            return 0
        msglen = int(info[1:info.find("\n")])
        if 4096 < msglen:
            info += s.recv(msglen - 4096)
        metric_handler.info = {}
        try:
          for line in info.splitlines()[1:]:
              #logging.debug("line is %s done" % line)
              if "" == line:
                  continue
              if "#" == line[0]:
                  continue
              n, v = line.split(":")
              if n in metric_handler.descriptors:
                  if n == "master_sync_status":
                      v = 1 if v == 'up' else 0
                  if n == "db0":
                      v = v.split('=')[1].split(',')[0]
                  if n == "used_memory":
                      v = int(int(v) / 1000)
                  if n == "total_connections_received":
                      # first run, zero out and record total connections
                      if metric_handler.prev_total_connections == 0:
                          metric_handler.prev_total_connections = int(v)
                          v = 0
                      else:
                          # calculate connections per second
                          cps = (int(v) - metric_handler.prev_total_connections) / (time.time() - metric_handler.timestamp)
                          metric_handler.prev_total_connections = int(v)
                          v = cps
                  if n == "total_commands_processed":
                      # first run, zero out and record total commands
                      if metric_handler.prev_total_commands == 0:
                          metric_handler.prev_total_commands = int(v)
                          v = 0
                      else:
                          # calculate commands per second
                          cps = (int(v) - metric_handler.prev_total_commands) / (time.time() - metric_handler.timestamp)
                          metric_handler.prev_total_commands = int(v)
                          v = cps
                  #logging.debug("submittincg metric %s is %s" % (n, int(v)))
                  metric_handler.info[n] = int(v) # TODO Use value_type.
        except Exception, e:
            #logging.debug("caught exception %s" % e)
            pass
        s.close()
        metric_handler.timestamp = time.time()

    #logging.debug("returning metric_handl: %s %s %s" % (metric_handler.info.get(name, 0), metric_handler.info, metric_handler))
    return metric_handler.info.get(name, 0)

def metric_init(params={}):
    metric_handler.host = params.get("host", "127.0.0.1")
    metric_handler.port = int(params.get("port", 6379))
    metric_handler.auth = params.get("auth", None)
    metric_handler.timestamp = 0
    metric_handler.prev_total_commands = 0
    metric_handler.prev_total_connections = 0
    metrics = {
        "connected_clients": {"units": "clients"},
        "connected_slaves": {"units": "slaves"},
        "blocked_clients": {"units": "clients"},
        "used_memory": {"units": "KB"},
        "rdb_changes_since_last_save": {"units": "changes"},
        "rdb_bgsave_in_progress": {"units": "yes/no"},
        "master_sync_in_progress": {"units": "yes/no"},
        "master_link_status": {"units": "yes/no"},
        #"aof_bgrewriteaof_in_progress": {"units": "yes/no"},
        "total_connections_received": { "units": "connections/sec" },
        "instantaneous_ops_per_sec": {"units": "ops"},
        "total_commands_processed": { "units": "commands/sec" },
        "expired_keys": {"units": "keys"},
        "pubsub_channels": {"units": "channels"},
        "pubsub_patterns": {"units": "patterns"},
        #"vm_enabled": {"units": "yes/no"},
        "master_last_io_seconds_ago": {"units": "seconds ago"},
        "db0": {"units": "keys"},
    }
    metric_handler.descriptors = {}
    for name, updates in metrics.iteritems():
        descriptor = {
            "name": name,
            "call_back": metric_handler,
            "time_max": 90,
            "value_type": "int",
            "units": "",
            "slope": "both",
            "format": "%d",
            "description": "http://code.google.com/p/redis/wiki/InfoCommand",
            "groups": "redis",
        }
        descriptor.update(updates)
        metric_handler.descriptors[name] = descriptor
    return metric_handler.descriptors.values()

def metric_cleanup():
    pass

########NEW FILE########
__FILENAME__ = riak
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
import time
import urllib2
import traceback
import json

descriptors = list()
Desc_Skel   = {}
_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock
Debug = False

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "DEBUG: "+f % v

def floatable(str):
    try:
        float(str)
        return True
    except:
        return False

class UpdateMetricThread(threading.Thread):

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 30
        if "refresh_rate" in params:
            self.refresh_rate = int(params["refresh_rate"])
        self.metric       = {}
        self.timeout      = 10

        self.url          = "http://localhost:8098/stats"
        if "url" in params:
            self.url = params["url"]
        self.mp      = params["metrix_prefix"]

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True

        while not self.shuttingdown:
            _Lock.acquire()
            self.update_metric()
            _Lock.release()
            time.sleep(self.refresh_rate)

        self.running = False

    def update_metric(self):
        try:
            req = urllib2.Request(url = self.url)
            res = urllib2.urlopen(req, None, 2)
            stats = res.read()
            dprint("%s", stats)
            json_stats = json.loads(stats)
            for (key,value) in json_stats.iteritems():
              dprint("%s = %s", key, value)
              if value == 'undefined':
                self.metric[self.mp+'_'+key] = 0
              else:
                self.metric[self.mp+'_'+key] = value
        except urllib2.URLError:
            traceback.print_exc()
        else:
            res.close()

    def metric_of(self, name):
        val = 0
        mp = name.split("_")[0]
        if name in self.metric:
            _Lock.acquire()
            val = self.metric[name]
            _Lock.release()
        return val

def metric_init(params):
    global descriptors, Desc_Skel, _Worker_Thread, Debug

    if "metrix_prefix" not in params:
      params["metrix_prefix"] = "riak"

    print params

    # initialize skeleton of descriptors
    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : metric_of,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'format'      : '%u',
        'units'       : 'XXX',
        'slope'       : 'XXX', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'riak',
        }

    if "refresh_rate" not in params:
        params["refresh_rate"] = 15
    if "debug" in params:
        Debug = params["debug"]
    dprint("%s", "Debug mode on")

    _Worker_Thread = UpdateMetricThread(params)
    _Worker_Thread.start()

    # IP:HOSTNAME
    if "spoof_host" in params:
        Desc_Skel["spoof_host"] = params["spoof_host"]

    mp = params["metrix_prefix"]

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_ring_creation_size",
                "units"      : "vnodes",
                "slope"      : "both",
                "description": mp+"_ring_creation_size",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_get_fsm_time_mean",
                "units"      : "microseconds",
                "slope"      : "both",
                "description": "Mean for riak_kv_get_fsm calls",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_pbc_active",
                "units"      : "connections",
                "slope"      : "both",
                "description": "Active pb socket connections",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_put_fsm_time_100",
                "units"      : "microseconds",
                "slope"      : "both",
                "description": "100th percentile for riak_kv_put_fsm calls",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_put_fsm_time_mean",
                "units"      : "microseconds",
                "slope"      : "both",
                "description": "Mean for riak_kv_put_fsm calls",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_get_fsm_time_95",
                "units"      : "microseconds",
                "slope"      : "both",
                "description": "95th percentile for riak_kv_get_fsm calls",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_vnode_puts",
                "units"      : "puts",
                "slope"      : "both",
                "description": "Puts handled by local vnodes in the last minute",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_puts",
                "units"      : "puts",
                "slope"      : "both",
                "description": "Puts coordinated by this node in the last minute",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_get_fsm_time_median",
                "units"      : "microseconds",
                "slope"      : "both",
                "description": "Median for riak_kv_get_fsm calls",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_sys_process_count",
                "units"      : "processes",
                "slope"      : "both",
                "description": "Erlang processes",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_put_fsm_time_median",
                "units"      : "microseconds",
                "slope"      : "both",
                "description": "Median for riak_kv_put_fsm calls",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_put_fsm_time_95",
                "units"      : "microseconds",
                "slope"      : "both",
                "description": "95th percentile for riak_kv_put_fsm calls",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_get_fsm_time_100",
                "units"      : "microseconds",
                "slope"      : "both",
                "description": "100th percentile for riak_kv_get_fsm calls",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_get_fsm_time_99",
                "units"      : "microseconds",
                "slope"      : "both",
                "description": "99th percentile for riak_kv_get_fsm calls",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_vnode_gets",
                "units"      : "gets",
                "slope"      : "both",
                "description": "Gets handled by local vnodes in the last minute",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_read_repairs",
                "units"      : "repairs",
                "slope"      : "both",
                "description": mp+"_read_repairs",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_ring_num_partitions",
                "units"      : "vnodes",
                "slope"      : "both",
                "description": mp+"_ring_num_partitions",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_mem_total",
                "units"      : "bytes",
                "format"     : "%.1f",
                'value_type'  : 'float',
                "slope"      : "both",
                "description": mp+"_mem_total",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_gets",
                "units"      : "gets",
                "slope"      : "both",
                "description": "Gets coordinated by this node in the last minute",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_mem_allocated",
                "units"      : "bytes",
                "format"     : "%.1f",
                'value_type'  : 'float',
                "slope"      : "both",
                "description": mp+"_mem_allocated",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : mp+"_node_put_fsm_time_99",
                "units"      : "microseconds",
                "slope"      : "both",
                "description": "99th percentile for riak_kv_put_fsm calls",
                }))

    return descriptors

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_of(name):
    return _Worker_Thread.metric_of(name)

def metric_cleanup():
    _Worker_Thread.shutdown()

if __name__ == '__main__':
    try:
        params = {
            "debug" : True,
            }
        metric_init(params)

        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                print ('value for %s is '+d['format']) % (d['name'],  v)
            time.sleep(5)
    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except:
        traceback.print_exc()
        os._exit(1)
########NEW FILE########
__FILENAME__ = scribe_stats
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import subprocess
import re
import time

from subprocess import Popen, PIPE, STDOUT

descriptors = list()
Debug = False

last_mps_timestamp = float(0)
last_mps_value = 0

def dprint(f, *v):
    if Debug:
        print >>sys.stderr, "DEBUG: "+f % v

def GetOverallMessagesPerSecond(name):
    dprint("%s", name)

    global last_mps_timestamp, last_mps_value

    # get the current value
    rc, output = run_cmd(["/usr/sbin/scribe_ctrl", "counters"])

    # return 0 if command fails
    if rc:
        return float(0)

    match = re.compile(r"^scribe_overall:received good: (\d+)$", re.MULTILINE).search(output)
    value = int(match.group(1))

    # save current value
    value_diff = value - last_mps_value
    last_mps_value = value

    # calculate seconds that have passed since last call
    current_time = time.time()
    elapsed = current_time - last_mps_timestamp

    # save current timestamp
    first_run = last_mps_timestamp is 0
    last_mps_timestamp = current_time

    if first_run:
        return float(0)

    return float(value_diff / elapsed)

def run_cmd(arglist):
    '''Run a command and capture output.'''

    try:
        p = Popen(arglist, stdout=PIPE, stderr=PIPE)
        output, errors = p.communicate()
    except OSError, e:
        return (1, '')

    return (p.returncode, output)

def metric_init(params):
    '''Create the metric definition dictionary object for each metric.'''

    global descriptors
    
    d1 = {
        'name': 'scribe_overall_messages_per_second',
        'call_back': GetOverallMessagesPerSecond,
        'time_max': 90,
        'value_type': 'float',
        'units': 'msg/sec',
        'slope': 'both',
        'format': '%f',
        'description': 'Average number of messages sent per second',
        'groups': 'scribe'
        }

    descriptors = [d1]
    return descriptors    

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

if __name__ == '__main__':
    metric_init({})
    
    # setup last timestamp as 10 seconds ago
    last_mps_timestamp = time.time() - 10
    
    for d in descriptors:
        v = d['call_back'](d['name'])
        print '%s: %s' % (d['name'],  v)

########NEW FILE########
__FILENAME__ = squid
"""
Copyright (c)2012 Daniel Rich <drich@employees.org>

This module will query an squid server via SNMP for metrics
"""

import sys
import os
import re

import time
#import logging
#logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/gmond.log', filemode='w')
#logging.debug('starting up')

last_update = 0
# We get counter values back, so we have to calculate deltas for some stats
squid_stats = {}
squid_stats_last = {}

MIN_UPDATE_INTERVAL = 30          # Minimum update interval in seconds

def collect_stats():
    #logging.debug('collect_stats()')
    global last_update
    global squid_stats, squid_stats_last

    now = time.time()

    if now - last_update < MIN_UPDATE_INTERVAL:
        #logging.debug(' wait ' + str(int(MIN_UPDATE_INTERVAL - (now - last_update))) + ' seconds')
        return True
    else:
        elapsed_time = now - last_update
        last_update = now

    squid_stats = {}

    # Run squidclient mgr:info to get stats
    try:
        stats = {}
        squidclient = os.popen("squidclient mgr:info")
    except IOError,e:
        #logging.error('error running squidclient')
        return False

    # Parse output, splitting everything into key/value pairs
    rawstats = {}
    for stat in squidclient.readlines():
        stat = stat.strip()
        if stat.find(':') >= 0:
            [key,value] = stat.split(':',1)
            if value:     # Toss things with no value
                value = value.lstrip()
                rawstats[key] = value
        else:
            match = re.search("(\d+)\s+(.*)$",stat) # reversed "value key" line
            if match:
                rawstats[match.group(2)] = match.group(1)

    # Use stats_descriptions to convert raw stats to real metrics
    for metric in stats_descriptions:
        if stats_descriptions[metric].has_key('key'):
            if rawstats.has_key(stats_descriptions[metric]['key']):
                rawstat = rawstats[stats_descriptions[metric]['key']]
                if stats_descriptions[metric].has_key('match'):
                    match = re.match(stats_descriptions[metric]['match'],rawstat)
                    if match:
                        rawstat = match.group(1)
                        squid_stats[metric] = rawstat
                else:
                    squid_stats[metric] = rawstat
        if squid_stats.has_key(metric): # Strip trailing non-num text
            if metric != 'cacheVersionId': # version is special case
                match = re.match('([0-9.]+)',squid_stats[metric]);
                squid_stats[metric] = float(match.group(1))
                if stats_descriptions[metric]['type'] == 'integer':
                    squid_stats[metric] = int(squid_stats[metric])

        # Calculate delta for counter stats
        if metric in squid_stats_last:
            if stats_descriptions[metric]['type'] == 'counter32':
                current = squid_stats[metric]
                squid_stats[metric] = (squid_stats[metric] - squid_stats_last[metric]) / float(elapsed_time)
                squid_stats_last[metric] = current
            else:
                squid_stats_last[metric] = squid_stats[metric]
        else:
            if metric in squid_stats:
                squid_stats_last[metric] = squid_stats[metric]

    #logging.debug('collect_stats done')
    #logging.debug('squid_stats: ' + str(squid_stats))

def get_stat(name):
    #logging.info("get_stat(%s)" % name)
    global squid_stats

    ret = collect_stats()

    if ret:
        if name.startswith('squid_'):
            label = name[6:]
        else:
            lable = name
            
            #logging.debug("fetching %s" % label)
        try:
            #logging.info("got %4.2f" % squid_stats[label])
            return squid_stats[label]
        except:
            #logging.error("failed to fetch %s" % name)
            return 0

    else:
        return 0


def metric_init(params):
    global descriptors
    global squid_stats
    global stats_descriptions   # needed for stats extraction in collect_stat()

    #logging.debug("init: " + str(params))

    stats_descriptions = dict(
        cacheVersionId = {
            'description': 'Cache Software Version',
            'units': 'N/A',
            'type': 'string',
            'key': 'Squid Object Cache',
            },
        cacheSysVMsize = {
            'description': 'Storage Mem size in KB',
            'units': 'KB',
            'type': 'integer',
            'key': 'Storage Mem size',
            },
        cacheMemUsage = {
            'description': 'Total memory accounted for KB',
            'units': 'KB',
            'type': 'integer',
            'key': 'Total accounted',
            },
        cacheSysPageFaults = {
            'description': 'Page faults with physical i/o',
            'units': 'faults/s',
            'type': 'counter32',
            'key': 'Page faults with physical i/o',
            },
        cacheCpuTime = {
            'description': 'Amount of cpu seconds consumed',
            'units': 'seconds',
            'type': 'integer',
            'key': 'CPU Time',
            },
        cacheCpuUsage = {
            'description': 'The percentage use of the CPU',
            'units': 'percent',
            'type': 'float',
            'key': 'CPU Usage',
            },
        cacheCpuUsage_5 = {
            'description': 'The percentage use of the CPU - 5 min',
            'units': 'percent',
            'type': 'float',
            'key': 'CPU Usage, 5 minute avg',
            },
        cacheCpuUsage_60 = {
            'description': 'The percentage use of the CPU - 60 min',
            'units': 'percent',
            'type': 'float',
            'key': 'CPU Usage, 60 minute avg',
            },
        cacheMaxResSize = {
            'description': 'Maximum Resident Size in KB',
            'units': 'KB',
            'type': 'integer',
            'key': 'Maximum Resident Size',
            },
        cacheNumObjCount = {
            'description': 'Number of objects stored by the cache',
            'units': 'objects',
            'type': 'integer',
            'key': 'StoreEntries',
            },
        cacheNumObjCountMemObj = {
            'description': 'Number of memobjects stored by the cache',
            'units': 'objects',
            'type': 'integer',
            'key': 'StoreEntries with MemObjects',
            },
        cacheNumObjCountHot = {
            'description': 'Number of hot objects stored by the cache',
            'units': 'objects',
            'type': 'integer',
            'key': 'Hot Object Cache Items',
            },
        cacheNumObjCountOnDisk = {
            'description': 'Number of objects stored by the cache on-disk',
            'units': 'objects',
            'type': 'integer',
            'key': 'on-disk objects',
            },
        cacheCurrentUnusedFDescrCnt = {
            'description': 'Available number of file descriptors',
            'units': 'file descriptors',
            'type': 'gauge32',
            'key': 'Maximum number of file descriptors',
            },
        cacheCurrentResFileDescrCnt = {
            'description': 'Reserved number of file descriptors',
            'units': 'file descriptors',
            'type': 'gauge32',
            'key': 'Reserved number of file descriptors',
            },
        cacheCurrentFileDescrCnt = {
            'description': 'Number of file descriptors in use',
            'units': 'file descriptors',
            'type': 'gauge32',
            'key': 'Number of file desc currently in use',
            },
        cacheCurrentFileDescrMax = {
            'description': 'Highest file descriptors in use',
            'units': 'file descriptors',
            'type': 'gauge32',
            'key': 'Largest file desc currently in use',
            },
        cacheProtoClientHttpRequests = {
            'description': 'Number of HTTP requests received',
            'units': 'requests/s',
            'type': 'counter32',
            'key': 'Number of HTTP requests received'
            },
        cacheIcpPktsSent = {
            'description': 'Number of ICP messages sent',
            'units': 'messages/s',
            'type': 'counter32',
            'key': 'Number of ICP messages sent',
            },
        cacheIcpPktsRecv = {
            'description': 'Number of ICP messages received',
            'units': 'messages/s',
            'type': 'counter32',
            'key': 'Number of ICP messages received',
            },
        cacheCurrentSwapSize = {
            'description': 'Storage Swap size',
            'units': 'KB',
            'type': 'gauge32',
            'key': 'Storage Swap size',
            },
        cacheClients = {
            'description': 'Number of clients accessing cache',
            'units': 'clients',
            'type': 'gauge32',
            'key': 'Number of clients accessing cache',
            },
        cacheHttpAllSvcTime_5 = {
            'description': 'HTTP all service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'HTTP Requests (All)',
            'match': '([0-9.]+)',
            },
        cacheHttpAllSvcTime_60 = {
            'description': 'HTTP all service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'HTTP Requests (All)',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheHttpMissSvcTime_5 = {
            'description': 'HTTP miss service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Cache Misses',
            'match': '([0-9.]+)',
            },
        cacheHttpMissSvcTime_60 = {
            'description': 'HTTP miss service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Cache Misses',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheHttpNmSvcTime_5 = {
            'description': 'HTTP hit not-modified service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Not-Modified Replies',
            'match': '([0-9.]+)',
            },
        cacheHttpNmSvcTime_60 = {
            'description': 'HTTP hit not-modified service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Not-Modified Replies',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheHttpHitSvcTime_5 = {
            'description': 'HTTP hit service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Cache Hits',
            'match': '([0-9.]+)',
            },
        cacheHttpHitSvcTime_60 = {
            'description': 'HTTP hit service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Cache Hits',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheIcpQuerySvcTime_5 = {
            'description': 'ICP query service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'ICP Queries',
            'match': '([0-9.]+)',
            },
        cacheIcpQuerySvcTime_60 = {
            'description': 'ICP query service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'ICP Queries',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheDnsSvcTime_5 = {
            'description': 'DNS service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'DNS Lookups',
            'match': '([0-9.]+)',
            },
        cacheDnsSvcTime_60 = {
            'description': 'DNS service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'DNS Lookups',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
        cacheRequestHitRatio_5 = {
            'description': 'Request Hit Ratios - 5 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Hit Ratios',
            'match': '5min: ([0-9.]+)%',
            },
        cacheRequestHitRatio_60 = {
            'description': 'Request Hit Ratios - 60 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Hit Ratios',
            'match': '5min: [0-9.]+%,\s+60min: ([0-9.]+)%',
            },
        cacheRequestByteRatio_5 = {
            'description': 'Byte Hit Ratios - 5 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Byte Hit Ratios',
            'match': '5min: ([0-9.]+)%',
            },
        cacheRequestByteRatio_60 = {
            'description': 'Byte Hit Ratios - 60 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Byte Hit Ratios',
            'match': '5min: [0-9.]+%,\s+60min: ([0-9.]+)%',
            },
        cacheRequestMemRatio_5 = {
            'description': 'Memory Hit Ratios - 5 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Memory Hit Ratios',
            'match': '5min: ([0-9.]+)%',
            },
        cacheRequestMemRatio_60 = {
            'description': 'Memory Hit Ratios - 60 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Memory Hit Ratios',
            'match': '5min: [0-9.]+%,\s+60min: ([0-9.]+)%',
            },
        cacheRequestDiskRatio_5 = {
            'description': 'Disk Hit Ratios - 5 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Disk Hit Ratios',
            'match': '5min: ([0-9.]+)%',
            },
        cacheRequestDiskRatio_60 = {
            'description': 'Disk Hit Ratios - 60 min',
            'units': 'percent',
            'type': 'float',
            'key': 'Request Disk Hit Ratios',
            'match': '5min: [0-9.]+%,\s+60min: ([0-9.]+)%',
            },
        cacheHttpNhSvcTime_5 = {
            'description': 'HTTP refresh hit service time - 5 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Near Hits',
            'match': '([0-9.]+)',
            },
        cacheHttpNhSvcTime_60 = {
            'description': 'HTTP refresh hit service time - 60 min',
            'units': 'seconds',
            'type': 'float',
            'key': 'Near Hits',
            'match': '[0-9.]+\s+([0-9.]+)',
            },
    )

    descriptors = []
    collect_stats()

    time.sleep(MIN_UPDATE_INTERVAL)
    collect_stats()

    for label in stats_descriptions:
        if squid_stats.has_key(label):
            if stats_descriptions[label]['type'] == 'string':
                d= {
                    'name': 'squid_' + label,
                    'call_back': get_stat,
                    'time_max': 60,
                    'value_type': "string",
                    'units': '',
                    'slope': "none",
                    'format': '%s',
                    'description': label,
                    'groups': 'squid',
                }
            elif stats_descriptions[label]['type'] == 'counter32':
                d= {
                    'name': 'squid_' + label,
                    'call_back': get_stat,
                    'time_max': 60,
                    'value_type': "float",
                    'units': stats_descriptions[label]['units'],
                    'slope': "positive",
                    'format': '%f',
                    'description': label,
                    'groups': 'squid',
                }
            elif stats_descriptions[label]['type'] == 'integer':
                d= {
                    'name': 'squid_' + label,
                    'call_back': get_stat,
                    'time_max': 60,
                    'value_type': "uint",
                    'units': stats_descriptions[label]['units'],
                    'slope': "both",
                    'format': '%u',
                    'description': label,
                    'groups': 'squid',
                }
            else:
                d= {
                'name': 'squid_' + label,
                'call_back': get_stat,
                'time_max': 60,
                'value_type': "float",
                'units': stats_descriptions[label]['units'],
                'slope': "both",
                'format': '%f',
                'description': label,
                'groups': 'squid',
                }
            
            d.update(stats_descriptions[label])
            
            descriptors.append(d)
            
        #else:
            #logging.error("skipped " + label)
            
    return descriptors

def metric_cleanup():
    #logging.shutdown()
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init(None)
    for d in descriptors:
        v = d['call_back'](d['name'])
        if d['value_type'] == 'string':
            print 'value for %s is %s %s' % (d['name'],  v, d['units'])
        elif d['value_type'] == 'uint':
            print 'value for %s is %d %s' % (d['name'],  v, d['units'])
        else:
            print 'value for %s is %4.2f %s' % (d['name'],  v, d['units'])


########NEW FILE########
__FILENAME__ = entropy
import sys


entropy_file = "/proc/sys/kernel/random/entropy_avail"

def metrics_handler(name):  
    try:
        f = open(entropy_file, 'r')

    except IOError:
        return 0

    for l in f:
        line = l

    return int(line)

def metric_init(params):
    global descriptors, node_id

    dict = {'name': 'entropy_avail',
        'call_back': metrics_handler,
        'time_max': 90,
        'value_type': 'uint',
        'units': 'bits',
        'slope': 'both',
        'format': '%u',
        'description': 'Entropy Available',
        'groups': 'ssl'}

    descriptors = [dict]

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init({})
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s is %u' % (d['name'],  v)
########NEW FILE########
__FILENAME__ = cpu_stats
import sys
import traceback
import os
import re
import time
import copy

METRICS = {
    'time' : 0,
    'data' : {}
}

# Got these from /proc/softirqs
softirq_pos = {
  'hi' : 1,
  'timer' : 2,
  'nettx' : 3,
  'netrx' : 4,
  'block' : 5,
  'blockiopoll' : 6,
  'tasklet' : 7,
  'sched' : 8,
  'hrtimer' : 9,
  'rcu' : 10
}

LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5



stat_file = "/proc/stat"

###############################################################################
#
###############################################################################
def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	try:
	    file = open(stat_file, 'r')
    
	except IOError:
	    return 0

        # convert to dict
        metrics = {}
        for line in file:
            parts = re.split("\s+", line)
            metrics[parts[0]] = list(parts[1:])

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    NAME_PREFIX="cpu_"

    name = name.replace(NAME_PREFIX,"") # remove prefix from name

    try:
        result = metrics['data'][name][0]
    except StandardError:
        result = 0

    return result


def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    NAME_PREFIX="cpu_"

    name = name.replace(NAME_PREFIX,"") # remove prefix from name

    if name == "procs_created":
      name = "processes"

    try:
      delta = (float(curr_metrics['data'][name][0]) - float(last_metrics['data'][name][0])) /(curr_metrics['time'] - last_metrics['time'])
      if delta < 0:
	print name + " is less 0"
	delta = 0
    except KeyError:
      delta = 0.0      

    return delta

##############################################################################
# SoftIRQ has multiple values which are defined in a dictionary at the top
##############################################################################
def get_softirq_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    NAME_PREFIX="softirq_"

    name = name[len(NAME_PREFIX):] # remove prefix from name

    index = softirq_pos[name]

    try:
      delta = (float(curr_metrics['data']['softirq'][index]) - float(last_metrics['data']['softirq'][index])) /(curr_metrics['time'] - last_metrics['time'])
      if delta < 0:
	print name + " is less 0"
	delta = 0
    except KeyError:
      delta = 0.0      

    return delta



def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, metric_map, Desc_Skel

    descriptors = []

    Desc_Skel = {
        'name'        : 'XXX',
        'orig_name'   : 'XXX',
        'call_back'   : get_delta,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.0f',
        'units'       : 'XXX',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : '',
        'groups'      : 'cpu',
        }

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "cpu_ctxt",
                "units"      : "ctxs/sec",
                "description": "Context Switches",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "procs_created",
                "units"      : "proc/sec",
                "description": "Number of processes and threads created",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "cpu_intr",
                "units"      : "intr/sec",
                "description": "Interrupts serviced",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "procs_blocked",
                "units"      : "processes",
                "call_back"   : get_value,
                "description": "Processes blocked",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq",
                "units"      : "ops/s",
                "description": "Soft IRQs",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq_hi",
                "units"      : "ops/s",
                'groups'     : 'softirq',
                "call_back"   : get_softirq_delta
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq_timer",
                "units"      : "ops/s",
                'groups'     : 'softirq',
                "call_back"   : get_softirq_delta
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq_nettx",
                "units"      : "ops/s",
                'groups'     : 'softirq',
                "call_back"   : get_softirq_delta
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq_netrx",
                "units"      : "ops/s",
                'groups'     : 'softirq',
                "call_back"   : get_softirq_delta
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq_block",
                "units"      : "ops/s",
                'groups'     : 'softirq',
                "call_back"   : get_softirq_delta
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq_blockiopoll",
                "units"      : "ops/s",
                'groups'     : 'softirq',
                "call_back"   : get_softirq_delta
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq_tasklet",
                "units"      : "ops/s",
                'groups'     : 'softirq',
                "call_back"   : get_softirq_delta
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq_sched",
                "units"      : "ops/s",
                'groups'     : 'softirq',
                "call_back"   : get_softirq_delta
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq_hrtimer",
                "units"      : "ops/s",
                'groups'     : 'softirq',
                "call_back"   : get_softirq_delta
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "softirq_rcu",
                "units"      : "ops/s",
                'groups'     : 'softirq',
                "call_back"   : get_softirq_delta
                }))


    # We need a metric_map that maps metric_name to the index in /proc/meminfo
    metric_map = {}
    
    for d in descriptors:
	metric_name = d['name']
        metric_map[metric_name] = { "name": d['orig_name'], "units": d['units'] }
        
    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init({})
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping 15 seconds'
        time.sleep(5)

########NEW FILE########
__FILENAME__ = hwmon
#!/usr/bin/env python

root = '/sys/class/hwmon'
descriptors = []
mapping = {}

import os, glob, re

def temp_finder(name):
    val = open(mapping[name]).read().strip()
    return int(val) / 1000.0

def metric_init(params):
    global descriptors

    sensors = sorted(glob.glob(os.path.join(root, 'hwmon*')))

    for s in sensors:
        temps = glob.glob(os.path.join(s, 'device/temp*_input'))
        # dict values are default labels if no label files exist
        probes = dict(zip(temps, [os.path.basename(x) for x in temps]))

        for i in probes.keys():
            try:
                fname = i.replace('input', 'label')
                fhandle = open(fname, 'r')
                probes[i] = fhandle.read().strip().replace(' ', '_').lower()
                fhandle.close()
            except (IOError, OSError):
                pass

        for i, l in probes.iteritems():
            num = re.search('\d+', i)
            device = i[num.start():num.end()]
            name = 'hwmon_dev%s_%s' % (device, l)
            item = {'name': name,
                    'call_back': temp_finder,
                    'time_max': 90,
                    'value_type': 'float',
                    'units': 'C',
                    'slope': 'both',
                    'format': '%0.2f',
                    'description': 'Temperature for hwmon probe %s' % l,
                    'groups': 'hwmon'}
            descriptors.append(item)
            mapping[name] = i

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

if __name__ == '__main__':
    metric_init(None)
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s: %s' % (d['name'],  str(v))

########NEW FILE########
__FILENAME__ = mem_fragmentation
import sys
import re
import time
import copy

PARAMS = {}

METRICS = {
    'time' : 0,
    'data' : {}
}

NAME_PREFIX = "buddy"

#Normal: 1046*4kB 529*8kB 129*16kB 36*32kB 17*64kB 5*128kB 26*256kB 40*512kB 13*1024kB 16*2048kB 94*4096kB = 471600kB

buddyinfo_file = "/proc/buddyinfo"

LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

stats_pos = {} 

stats_pos = {
  '0004k' : 4,
  '0008k' : 5,
  '0016k' : 6,
  '0032k' : 7,
  '0064k' : 8,
  '0128k' : 9,
  '0256k' : 10,
  '0512k' : 11,
  '1024k' : 12,
  '2048k' : 13,
  '4096k' : 14
}

zones = []

def get_node_zones():
    """Return all zones metrics"""

    try:
	file = open(buddyinfo_file, 'r')

    except IOError:
	return 0

    # convert to dict
    metrics = {}
    for line in file:
	metrics = re.split("\s+", line)
	node_id = metrics[1].replace(',','')
	zone = metrics[3].lower()
	zones.append("node" + node_id + "_" + zone)


def get_metrics():
    """Return all metrics"""

    global METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	try:
	    file = open(buddyinfo_file, 'r')
    
	except IOError:
	    return 0

        # convert to dict
        metrics = {}
	values = {}
        for line in file:
            metrics = re.split("\s+", line)
	    node_id = metrics[1].replace(',','')
	    zone = metrics[3].lower()
	    for item in stats_pos:
		pos = stats_pos[item]
		metric_name = "node" + node_id + "_" + zone + "_" + item
		values[metric_name] = metrics[pos]
		

	file.close
        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': values
        }
	
    return [METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    prefix_length = len(NAME_PREFIX) + 1
    name = name[prefix_length:] # remove prefix from name
    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, metric_map, Desc_Skel

    descriptors = []

    get_node_zones()

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_value,
        'time_max'    : 60,
        'value_type'  : 'uint',
        'format'      : '%d',
        'units'       : 'segments',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'mem_fragmentation',
        }

    for zone in zones:
	for item in stats_pos:
	    descriptors.append(create_desc(Desc_Skel, {
		    "name"       : NAME_PREFIX + "_" + zone + "_" + item,
		    "description": item,
		    }))

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping 15 seconds'
        time.sleep(15)

########NEW FILE########
__FILENAME__ = mem_stats
import sys
import traceback
import os
import re


###############################################################################
# Explanation of metrics in /proc/meminfo can be found here
#
# http://www.redhat.com/advice/tips/meminfo.html
# and
# http://unixfoo.blogspot.com/2008/02/know-about-procmeminfo.html
# and
# http://www.centos.org/docs/5/html/5.2/Deployment_Guide/s2-proc-meminfo.html
###############################################################################

meminfo_file = "/proc/meminfo"

def metrics_handler(name):  
    try:
        file = open(meminfo_file, 'r')

    except IOError:
        return 0

    value = 0
    for line in file:
	parts = re.split("\s+", line)
	if parts[0] == metric_map[name]['name'] + ":" :
	    # All of the measurements are in kBytes. We want to change them over
	    # to Bytes
	    if metric_map[name]['units'] == "Bytes":
		value = float(parts[1]) * 1024
	    else:
                value = parts[1]
	
    return float(value)

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, metric_map, Desc_Skel

    descriptors = []

    Desc_Skel = {
        'name'        : 'XXX',
        'orig_name'   : 'XXX',
        'call_back'   : metrics_handler,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.0f',
        'units'       : 'XXX',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'memory',
        }

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : "mem_total",
                "orig_name"  : "MemTotal",
                "units"      : "Bytes",
                "description": "Total usable ram",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_free",
                "orig_name"  : "MemFree",
                "units"      : "Bytes",
                "description": "The amount of physical RAM left unused by the system. ",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_buffers",
                "orig_name"  : "Buffers",
                "units"      : "Bytes",
                "description": "Buffers used",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_cached",
                "orig_name"  : "Cached",
                "units"      : "Bytes",
                "description": "Cached Memory",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_swap_cached",
                "orig_name"  : "SwapCached",
                "units"      : "Bytes",
                "description": "Amount of Swap used as cache memory. Memory that once was swapped out, is swapped back in, but is still in the swapfile",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_active",
                "orig_name"  : "Active",
                "units"      : "Bytes",
                "description": "Memory that has been used more recently and usually not reclaimed unless absolutely necessary.",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_inactive",
                "orig_name"  : "Inactive",
                "units"      : "Bytes",
                "description": "The total amount of buffer or page cache memory that are free and available",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_total_anon",
                "orig_name"  : "Active(anon)",
                "units"      : "Bytes",
                "description": "Active(anon)",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_inactive_anon",
                "orig_name"  : "Inactive(anon)",
                "units"      : "Bytes",
                "description": "Inactive(anon)",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_active_file",
                "orig_name"  : "Active(file)",
                "units"      : "Bytes",
                "description": "Active(file)",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_inactive_file",
                "orig_name"  : "Inactive(file)",
                "units"      : "Bytes",
                "description": "Inactive(file)",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_unevictable",
                "orig_name"  : "Unevictable",
                "units"      : "Bytes",
                "description": "Unevictable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_mlocked",
                "orig_name"  : "Mlocked",
                "units"      : "Bytes",
                "description": "Mlocked",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_swap_total",
                "orig_name"  : "SwapTotal",
                "units"      : "Bytes",
                "description": "Total amount of physical swap memory",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_swap_free",
                "orig_name"  : "SwapFree",
                "units"      : "Bytes",
                "description": "Total amount of swap memory free",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_dirty",
                "orig_name"  : "Dirty",
                "units"      : "Bytes",
                "description": "The total amount of memory waiting to be written back to the disk. ",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_writeback",
                "orig_name"  : "Writeback",
                "units"      : "Bytes",
                "description": "The total amount of memory actively being written back to the disk.",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_anonpages",
                "orig_name"  : "AnonPages",
                "units"      : "Bytes",
                "description": "AnonPages",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_mapped",
                "orig_name"  : "Mapped",
                "units"      : "Bytes",
                "description": "Mapped",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_shmem",
                "orig_name"  : "Shmem",
                "units"      : "Bytes",
                "description": "Shmem",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_slab",
                "orig_name"  : "Slab",
                "units"      : "Bytes",
                "description": "Slab",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_s_reclaimable",
                "orig_name"  : "SReclaimable",
                "units"      : "Bytes",
                "description": "SReclaimable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_s_unreclaimable",
                "orig_name"  : "SUnreclaim",
                "units"      : "Bytes",
                "description": "SUnreclaim",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_kernel_stack",
                "orig_name"  : "KernelStack",
                "units"      : "Bytes",
                "description": "KernelStack",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_page_tables",
                "orig_name"  : "PageTables",
                "units"      : "Bytes",
                "description": "PageTables",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_nfs_unstable",
                "orig_name"  : "NFS_Unstable",
                "units"      : "Bytes",
                "description": "NFS_Unstable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_bounce",
                "orig_name"  : "Bounce",
                "units"      : "Bytes",
                "description": "Bounce",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_writeback_tmp",
                "orig_name"  : "WritebackTmp",
                "units"      : "Bytes",
                "description": "WritebackTmp",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_commit_limit",
                "orig_name"  : "CommitLimit",
                "units"      : "Bytes",
                "description": "CommitLimit",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_committed_as",
                "orig_name"  : "Committed_AS",
                "units"      : "Bytes",
                "description": "Committed_AS",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_vmalloc_total",
                "orig_name"  : "VmallocTotal",
                "units"      : "Bytes",
                "description": "VmallocTotal",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_vmalloc_used",
                "orig_name"  : "VmallocUsed",
                "units"      : "Bytes",
                "description": "VmallocUsed",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_vmalloc_chunk",
                "orig_name"  : "VmallocChunk",
                "units"      : "Bytes",
                "description": "VmallocChunk",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_hardware_corrupted",
                "orig_name"  : "HardwareCorrupted",
                "units"      : "Bytes",
                "description": "HardwareCorrupted",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_hugepages_total",
                "orig_name"  : "HugePages_Total",
                "units"      : "pages",
                "description": "HugePages_Total",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_hugepages_free",
                "orig_name"  : "HugePages_Free",
                "units"      : "pages",
                "description": "HugePages_Free",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_hugepage_rsvd",
                "orig_name"  : "HugePages_Rsvd",
                "units"      : "pages",
                "description": "HugePages_Rsvd",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_hugepages_surp",
                "orig_name"  : "HugePages_Surp",
                "units"      : "pages",
                "description": "HugePages_Surp",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_hugepage_size",
                "orig_name"  : "Hugepagesize",
                "units"      : "Bytes",
                "description": "Hugepagesize",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_directmap_4k",
                "orig_name"  : "DirectMap4k",
                "units"      : "Bytes",
                "description": "DirectMap4k",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : "mem_directmap_2M",
                "orig_name"  : "DirectMap2M",
                "units"      : "Bytes",
                "description": "DirectMap2M",
                }))

    # We need a metric_map that maps metric_name to the index in /proc/meminfo
    metric_map = {}
    
    for d in descriptors:
	metric_name = d['name']
        metric_map[metric_name] = { "name": d['orig_name'], "units": d['units'] }
        
    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init({})
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s is %f' % (d['name'],  v)

########NEW FILE########
__FILENAME__ = vm_stats
import sys
import re
import time
import copy

PARAMS = {}

NAME_PREFIX = 'vm_'

METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

###############################################################################
# Explanation of metrics in /proc/meminfo can be found here
#
# http://www.redhat.com/advice/tips/meminfo.html
# and
# http://unixfoo.blogspot.com/2008/02/know-about-procmeminfo.html
# and
# http://www.centos.org/docs/5/html/5.2/Deployment_Guide/s2-proc-meminfo.html
###############################################################################
vminfo_file = "/proc/vmstat"


def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

	try:
	    file = open(vminfo_file, 'r')
    
	except IOError:
	    return 0

        # convert to dict
        metrics = {}
        for line in file:
            parts = re.split("\s+", line)
            metrics[parts[0]] = parts[1]

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]

def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    name = name[len(NAME_PREFIX):] # remove prefix from name

    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    name = name[len(NAME_PREFIX):] # remove prefix from name

    try:
      delta = (float(curr_metrics['data'][name]) - float(last_metrics['data'][name])) /(curr_metrics['time'] - last_metrics['time'])
      if delta < 0:
	print name + " is less 0"
	delta = 0
    except KeyError:
      delta = 0.0      

    return delta


# Calculate VM efficiency
# Works similar like sar -B 1
# Calculated as pgsteal / pgscan, this is a metric of the efficiency of page reclaim. If  it  is  near  100%  then
# almost  every  page coming off the tail of the inactive list is being reaped. If it gets too low (e.g. less than 30%)  
# then the virtual memory is having some difficulty.  This field is displayed as zero if no pages  have  been
# scanned during the interval of time
def get_vmeff(name):  
    # get metrics
    [curr_metrics, last_metrics] = get_metrics()
        
    try:
      pgscan_diff = float(curr_metrics['data']['pgscan_kswapd_normal']) - float(last_metrics['data']['pgscan_kswapd_normal'])
      # To avoid division by 0 errors check whether pgscan is 0
      if pgscan_diff == 0:
	return 0.0
	
      delta = 100 * (float(curr_metrics['data']['pgsteal_normal']) - float(last_metrics['data']['pgsteal_normal'])) / pgscan_diff
      if delta < 0:
        print name + " is less 0"
        delta = 0
    except KeyError:
      delta = 0.0      

    return delta
  

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d

def metric_init(params):
    global descriptors, metric_map, Desc_Skel

    descriptors = []

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : get_value,
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%.4f',
        'units'       : 'count',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'memory_vm',
        }

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_inactive_anon",
                "description": "nr_inactive_anon",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_active_anon",
                "description": "nr_active_anon",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_inactive_file",
                "description": "nr_inactive_file",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_active_file",
                "description": "nr_active_file",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_unevictable",
                "description": "nr_unevictable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_mlock",
                "description": "nr_mlock",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_anon_pages",
                "description": "nr_anon_pages",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_mapped",
                "description": "nr_mapped",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_file_pages",
                "description": "nr_file_pages",
                }))

    #
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_dirty",
                "description": "nr_dirty",
                }))

    #
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_writeback",
                "description": "nr_writeback",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_slab_reclaimable",
                "description": "nr_slab_reclaimable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_slab_unreclaimable",
                "description": "nr_slab_unreclaimable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_page_table_pages",
                "description": "nr_page_table_pages",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_kernel_stack",
                "description": "nr_kernel_stack",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_unstable",
                "description": "nr_unstable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_bounce",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "nr_bounce",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_vmscan_write",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "nr_vmscan_write",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_writeback_temp",
                "units"      : "ops/s",
                "description": "nr_writeback_temp",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_isolated_anon",
                "units"      : "ops/s",
                "description": "nr_isolated_anon",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_isolated_file",
                "units"      : "ops/s",
                "description": "nr_isolated_file",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_shmem",
                "units"      : "ops/s",
                "description": "nr_shmem",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "numa_hit",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "numa_hit",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "numa_miss",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "numa_miss",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "numa_foreign",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "numa_foreign",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "numa_interleave",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "numa_interleave",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "numa_local",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "numa_local",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "numa_other",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "numa_other",
                }))

    #
    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgpgin",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgpgin",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgpgout",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgpgout",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pswpin",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pswpin",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pswpout",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pswpout",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgalloc_dma",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgalloc_dma",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgalloc_dma32",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgalloc_dma32",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgalloc_normal",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgalloc_normal",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgalloc_movable",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgalloc_movable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgfree",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgfree",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgactivate",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgactivate",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgdeactivate",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgdeactivate",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgfault",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgfault",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgmajfault",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgmajfault",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgrefill_dma",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgrefill_dma",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgrefill_dma32",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgrefill_dma32",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgrefill_normal",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgrefill_normal",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgrefill_movable",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgrefill_movable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgsteal_dma",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgsteal_dma",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgsteal_dma32",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgsteal_dma32",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgsteal_normal",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgsteal_normal",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgsteal_movable",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgsteal_movable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgscan_kswapd_dma",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgscan_kswapd_dma",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgscan_kswapd_dma32",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgscan_kswapd_dma32",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgscan_kswapd_normal",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgscan_kswapd_normal",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgscan_kswapd_movable",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgscan_kswapd_movable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgscan_direct_dma",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgscan_direct_dma",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgscan_direct_dma32",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgscan_direct_dma32",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgscan_direct_normal",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgscan_direct_normal",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgscan_direct_movable",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgscan_direct_movable",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "zone_reclaim_failed",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "zone_reclaim_failed",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pginodesteal",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pginodesteal",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "slabs_scanned",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "slabs_scanned",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "kswapd_steal",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "kswapd_steal",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "kswapd_inodesteal",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "kswapd_inodesteal",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "kswapd_low_wmark_hit_quickly",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "kswapd_low_wmark_hit_quickly",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "kswapd_high_wmark_hit_quickly",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "kswapd_high_wmark_hit_quickly",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "kswapd_skip_congestion_wait",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "kswapd_skip_congestion_wait",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pageoutrun",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pageoutrun",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "allocstall",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "allocstall",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "pgrotated",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "pgrotated",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "unevictable_pgs_culled",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "unevictable_pgs_culled",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "unevictable_pgs_scanned",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "unevictable_pgs_scanned",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "unevictable_pgs_rescued",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "unevictable_pgs_rescued",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "unevictable_pgs_mlocked",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "unevictable_pgs_mlocked",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "unevictable_pgs_munlocked",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "unevictable_pgs_munlocked",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "unevictable_pgs_cleared",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "unevictable_pgs_cleared",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "unevictable_pgs_stranded",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "unevictable_pgs_stranded",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "unevictable_pgs_mlockfreed",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "unevictable_pgs_mlockfreed",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_dirtied",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "nr_dirtied",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_written",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "nr_written",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_anon_transparent_hugepages",
                "description": "nr_anon_transparent_hugepages",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_dirty_threshold",
                "description": "nr_dirty_threshold",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "nr_dirty_background_threshold",
                "description": "nr_dirty_background_threshold",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "compact_blocks_moved",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "compact_blocks_moved",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "compact_pages_moved",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "compact_pages_moved",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "compact_pagemigrate_failed",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "compact_pagemigrate_failed",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "compact_stall",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "compact_stall",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "compact_fail",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "compact_fail",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "compact_success",
                "call_back"  : get_delta,
                "units"      : "ops/s",
                "description": "compact_success",
                }))

    descriptors.append(create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + "vmeff",
                "description": "VM efficiency",
                'call_back'   : get_vmeff,
                'units'       : 'pct',
                }))

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print '%s = %s' % (d['name'],  v)
        print 'Sleeping 15 seconds'
        time.sleep(15)

########NEW FILE########
__FILENAME__ = tokyo_tyrant
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Tokyo Tyrant gmond module for Ganglia
#
# Copyright (C) 2011 by Michael T. Conigliaro <mike [at] conigliaro [dot] org>.
# All rights reserved.
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
import time
import copy

NAME_PREFIX = 'tokyo_tyrant_'
PARAMS = {
    'stats_command' : 'ssh legacy02.example.com /srv/tokyo/bin/tcrmgr inform -st localhost'
}
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 1


def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

        # get raw metric data
        io = os.popen(PARAMS['stats_command'])

        # convert to dict
        metrics = {}
        for line in io.readlines():
            values = line.split()
            try:
                metrics[values[0]] = float(values[1])
            except ValueError:
                metrics[values[0]] = values[1]

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]


def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    # get delta
    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        delta = (curr_metrics['data'][name] - last_metrics['data'][name])/(curr_metrics['time'] - last_metrics['time'])
        if delta < 0:
            delta = 0
    except StandardError:
        delta = 0

    return delta


def metric_init(lparams):
    """Initialize metric descriptors"""

    global PARAMS

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]

    # define descriptors
    time_max = 60
    groups = 'tokyo tyrant'
    descriptors = [
        {
            'name': NAME_PREFIX + 'rnum',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'uint',
            'units': 'Records',
            'slope': 'both',
            'format': '%u',
            'description': 'Record Number',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'size',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'double',
            'units': 'Bytes',
            'slope': 'both',
            'format': '%f',
            'description': 'File Size',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'delay',
            'call_back': get_value,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Secs',
            'slope': 'both',
            'format': '%f',
            'description': 'Replication Delay',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_put',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Put Operations',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_out',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Out Operations',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_get',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Get Operations',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_put_miss',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Put Operations Missed',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_out_miss',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Out Operations Missed',
            'groups': groups
        },
        {
            'name': NAME_PREFIX + 'cnt_get_miss',
            'call_back': get_delta,
            'time_max': time_max,
            'value_type': 'float',
            'units': 'Ops/Sec',
            'slope': 'both',
            'format': '%f',
            'description': 'Get Operations Missed',
            'groups': groups
        }
    ]

    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            print (('%s = %s') % (d['name'], d['format'])) % (d['call_back'](d['name']))
        print ''
        time.sleep(1)

########NEW FILE########
__FILENAME__ = varnish
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Varnish gmond module for Ganglia
#
# Copyright (C) 2011 by Michael T. Conigliaro <mike [at] conigliaro [dot] org>.
# All rights reserved.
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
import time
import copy

NAME_PREFIX = 'varnish_'
PARAMS = {
    'stats_command' : 'varnishstat -1'
}
METRICS = {
    'time' : 0,
    'data' : {}
}
LAST_METRICS = copy.deepcopy(METRICS)
METRICS_CACHE_MAX = 5

def create_desc(skel, prop):
    d = skel.copy()
    for k,v in prop.iteritems():
        d[k] = v
    return d


def get_metrics():
    """Return all metrics"""

    global METRICS, LAST_METRICS

    if (time.time() - METRICS['time']) > METRICS_CACHE_MAX:

        # get raw metric data
        io = os.popen(PARAMS['stats_command'])

        # convert to dict
        metrics = {}
        for line in io.readlines():
            values = line.split()[:2]
            try:
                metrics[values[0]] = int(values[1])
            except ValueError:
                metrics[values[0]] = 0

        # update cache
        LAST_METRICS = copy.deepcopy(METRICS)
        METRICS = {
            'time': time.time(),
            'data': metrics
        }

    return [METRICS, LAST_METRICS]

def get_value(name):
    """Return a value for the requested metric"""

    metrics = get_metrics()[0]

    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        result = metrics['data'][name]
    except StandardError:
        result = 0

    return result


def get_delta(name):
    """Return change over time for the requested metric"""

    # get metrics
    [curr_metrics, last_metrics] = get_metrics()

    # get delta
    name = name[len(NAME_PREFIX):] # remove prefix from name
    try:
        delta = float(curr_metrics['data'][name] - last_metrics['data'][name])/(curr_metrics['time'] - last_metrics['time'])
        if delta < 0:
            print "Less than 0"
            delta = 0
    except StandardError:
        delta = 0

    return delta


def get_cache_hit_ratio(name):
    """Return cache hit ratio"""

    try:
        result = get_delta(NAME_PREFIX + 'cache_hit') / get_delta(NAME_PREFIX + 'client_req') * 100
    except ZeroDivisionError:
        result = 0

    return result


def metric_init(lparams):
    """Initialize metric descriptors"""

    global PARAMS, Desc_Skel

    # set parameters
    for key in lparams:
        PARAMS[key] = lparams[key]

    # define descriptors
    time_max = 60

    Desc_Skel = {
        'name'        : 'XXX',
        'call_back'   : 'XXX',
        'time_max'    : 60,
        'value_type'  : 'float',
        'format'      : '%f',
        'units'       : 'XXX',
        'slope'       : 'both', # zero|positive|negative|both
        'description' : 'XXX',
        'groups'      : 'varnish',
        }

    descriptors = []

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'cache_hit_ratio',
                "call_back"  : get_cache_hit_ratio,
                "units"      : "pct",
                "description": "Cache Hit ratio",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'client_conn',
                "call_back"  : get_delta,
                "units"      : "conn/s",
                "description": "Client connections accepted",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'client_drop',
                "call_back"  : get_delta,
                "units"      : "conn/s",
                "description": "Connection dropped, no sess/wrk",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'client_req',
                "call_back"  : get_delta,
                "units"      : "req/s",
                "description": "Client requests received",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'cache_hit',
                "call_back"  : get_delta,
                "units"      : "hit/s",
                "description": "Cache hits",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'cache_hitpass',
                "call_back"  : get_delta,
                "units"      : "hit/s",
                "description": "Cache hits for pass",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'cache_miss',
                "units"      : "miss/s",
                "call_back"  : get_delta,
                "description": "Cache misses",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'backend_conn',
                "call_back"  : get_delta,
                "units"      : "conn/s",
                "description": "Backend conn. success",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'backend_unhealthy',
                "call_back"  : get_delta,
                "units"      : "conn/s",
                "description": "Backend conn. not attempted",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'backend_busy',
                "call_back"  : get_delta,
                "units"      : "busy/s",
                "description": "Backend conn. too many",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'backend_fail',
                "call_back"  : get_delta,
                "units"      : "fail/s",
                "description": "Backend conn. failures",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'backend_reuse',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Backend conn. reuses",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'backend_toolate',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Backend conn. was closed",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'backend_recycle',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Backend conn. recycles",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'backend_unused',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Backend conn. unused",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_head',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch head",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_length',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch with Length",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_chunked',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch chunked",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_eof',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch EOF",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_bad',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch had bad headers",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_close',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch wanted close",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_oldhttp',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch pre HTTP/1.1 closed",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_zero',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch zero len",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_failed',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch failed",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_sess_mem',
                "call_back"  : get_value,
                "units"      : "Bytes",
                "description": "N struct sess_mem",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_sess',
                "call_back"  : get_value,
                "units"      : "sessions",
                "description": "N struct sess",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_object',
                "call_back"  : get_value,
                "units"      : "objects",
                "description": "N struct object",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_vampireobject',
                "call_back"  : get_value,
                "units"      : "objects",
                "description": "N unresurrected objects",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_objectcore',
                "call_back"  : get_value,
                "units"      : "objects",
                "description": "N struct objectcore",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_objecthead',
                "call_back"  : get_value,
                "units"      : "objects",
                "description": "N struct objecthead",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_smf',
                "call_back"  : get_value,
                "units"      : "",
                "description": "N struct smf",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_smf_frag',
                "call_back"  : get_value,
                "units"      : "frags",
                "description": "N small free smf",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_smf_large',
                "call_back"  : get_value,
                "units"      : "frags",
                "description": "N large free smf",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_vbe_conn',
                "call_back"  : get_value,
                "units"      : "conn",
                "description": "N struct vbe_conn",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_wrk',
                "call_back"  : get_value,
                "units"      : "threads",
                "description": "N worker threads",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_wrk_create',
                "call_back"  : get_delta,
                "units"      : "threads/s",
                "description": "N worker threads created",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_wrk_failed',
                "call_back"  : get_delta,
                "units"      : "wrk/s",
                "description": "N worker threads not created",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_wrk_max',
                "call_back"  : get_delta,
                "units"      : "threads/s",
                "description": "N worker threads limited",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_wrk_queue',
                "call_back"  : get_value,
                "units"      : "req",
                "description": "N queued work requests",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_wrk_overflow',
                "call_back"  : get_delta,
                "units"      : "req/s",
                "description": "N overflowed work requests",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_wrk_drop',
                "call_back"  : get_delta,
                "units"      : "req/s",
                "description": "N dropped work requests",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_backend',
                "call_back"  : get_value,
                "units"      : "backends",
                "description": "N backends",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_expired',
                "call_back"  : get_delta,
                "units"      : "obj/s",
                "description": "N expired objects",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_lru_nuked',
                "call_back"  : get_delta,
                "units"      : "obj/s",
                "description": "N LRU nuked objects",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_lru_saved',
                "call_back"  : get_delta,
                "units"      : "obj/s",
                "description": "N LRU saved objects",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_lru_moved',
                "call_back"  : get_delta,
                "units"      : "obj/s",
                "description": "N LRU moved objects",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_deathrow',
                "call_back"  : get_delta,
                "units"      : "obj/s",
                "description": "N objects on deathrow",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'losthdr',
                "call_back"  : get_delta,
                "units"      : "hdrs/s",
                "description": "HTTP header overflows",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_objsendfile',
                "call_back"  : get_delta,
                "units"      : "obj/s",
                "description": "Objects sent with sendfile",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_objwrite',
                "call_back"  : get_delta,
                "units"      : "obj/s",
                "description": "Objects sent with write",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_objoverflow',
                "call_back"  : get_delta,
                "description": "Objects overflowing workspace",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 's_sess',
                "call_back"  : get_delta,
                "description": "Total Sessions",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 's_req',
                "call_back"  : get_delta,
                "description": "Total Requests",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 's_pipe',
                "call_back"  : get_delta,
                "description": "Total pipe",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 's_pass',
                "call_back"  : get_delta,
                "description": "Total pass",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 's_fetch',
                "call_back"  : get_delta,
                "description": "Total fetch",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 's_hdrbytes',
                "call_back"  : get_delta,
                "description": "Total header bytes",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 's_bodybytes',
                "call_back"  : get_delta,
                "units"      : "bytes/s",
                "description": "Total body bytes",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sess_closed',
                "call_back"  : get_delta,
                "units"      : "sessions/s",
                "description": "Session Closed",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sess_pipeline',
                "call_back"  : get_delta,
                "description": "Session Pipeline",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sess_readahead',
                "call_back"  : get_delta,
                "description": "Session Read Ahead",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sess_linger',
                "call_back"  : get_delta,
                "description": "Session Linger",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sess_herd',
                "call_back"  : get_delta,
                "description": "Session herd",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'shm_records',
                "call_back"  : get_delta,
                "description": "SHM records",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'shm_writes',
                "call_back"  : get_delta,
                "description": "SHM writes",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'shm_flushes',
                "call_back"  : get_delta,
                "description": "SHM flushes due to overflow",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'shm_cont',
                "call_back"  : get_delta,
                "description": "SHM MTX contention",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'shm_cycles',
                "call_back"  : get_delta,
                "description": "SHM cycles through buffer",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sm_nreq',
                "call_back"  : get_delta,
                "description": "allocator requests",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sm_nobj',
                "call_back"  : get_delta,
                "description": "outstanding allocations",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sm_balloc',
                "call_back"  : get_value,
                "description": "bytes allocated",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sm_bfree',
                "call_back"  : get_delta,
                "description": "bytes free",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sma_nreq',
                "call_back"  : get_delta,
                "description": "SMA allocator requests",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sma_nobj',
                "call_back"  : get_value,
                "units"      : "obj",
                "description": "SMA outstanding allocations",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sma_nbytes',
                "call_back"  : get_value,
                "units"      : "Bytes",
                "description": "SMA outstanding bytes",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sma_balloc',
                "call_back"  : get_delta,
                "units"      : "bytes/s",
                "description": "SMA bytes allocated",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sma_bfree',
                "call_back"  : get_delta,
                "units"      : "bytes/s",
                "description": "SMA bytes free",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sms_nreq',
                "call_back"  : get_delta,
                "units"      : "req/s",
                "description": "SMS allocator requests",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sms_nobj',
                "call_back"  : get_value,
                "units"      : "obj",
                "description": "SMS outstanding allocations",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sms_nbytes',
                "call_back"  : get_value,
                "units"      : "Bytes",
                "description": "SMS outstanding bytes",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sms_balloc',
                "call_back"  : get_delta,
                "units"      : "bytes/s",
                "description": "SMS bytes allocated",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'sms_bfree',
                "call_back"  : get_delta,
                "units"      : "Bytes/s",
                "description": "SMS bytes freed",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'backend_req',
                "call_back"  : get_delta,
                "units"      : "req/s",
                "description": "Backend requests made",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_vcl',
                "call_back"  : get_value,
                "units"      : "vcl",
                "description": "N vcl total",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_vcl_avail',
                "call_back"  : get_value,
                "units"      : "vcl",
                "description": "N vcl available",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_vcl_discard',
                "call_back"  : get_value,
                "units"      : "vcl",
                "description": "N vcl discarded",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_purge',
                "call_back"  : get_value,
                "units"      : "purges",
                "description": "N total active purges",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_purge_add',
                "call_back"  : get_delta,
                "units"      : "purges/sec",
                "description": "N new purges added",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_purge_retire',
                "call_back"  : get_delta,
                "units"      : "purges/s",
                "description": "N old purges deleted",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_purge_obj_test',
                "call_back"  : get_delta,
                "units"      : "purges/s",
                "description": "N objects tested",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_purge_re_test',
                "call_back"  : get_delta,
                "description": "N regexps tested against",
                "units"      : "purges/s",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_purge_dups',
                "call_back"  : get_delta,
                "units"      : "purges/s",
                "description": "N duplicate purges removed",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'hcb_nolock',
                "call_back"  : get_delta,
                "units"      : "locks/s",
                "description": "HCB Lookups without lock",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'hcb_lock',
                "call_back"  : get_delta,
                "units"      : "locks/s",
                "description": "HCB Lookups with lock",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'hcb_insert',
                "call_back"  : get_delta,
                "units"      : "inserts/s",
                "description": "HCB Inserts",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'esi_parse',
                "call_back"  : get_delta,
                "units"      : "obj/s",
                "description": "Objects ESI parsed (unlock)",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'esi_errors',
                "call_back"  : get_delta,
                "units"      : "err/s",
                "description": "ESI parse errors (unlock)",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'accept_fail',
                "call_back"  : get_delta,
                "units"      : "accepts/s",
                "description": "Accept failures",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'client_drop_late',
                "call_back"  : get_delta,
                "units"      : "conn/s",
                "description": "Connection dropped late",
                }))

    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'uptime',
                "call_back"  : get_value,
                "units"      : "seconds",
                "description": "Client uptime",
                }))

    ##############################################################################
    
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'backend_retry',
                "call_back"  : get_delta,
                "units"      : "retries/s",
                "description": "Backend conn. retry",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'dir_dns_cache_full',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "DNS director full dnscache",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'dir_dns_failed',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "DNS director failed lookups",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'dir_dns_hit',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "DNS director cached lookups hit",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'dir_dns_lookups',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "DNS director lookups",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'esi_warnings',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "ESI parse warnings (unlock)",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_1xx',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch no body (1xx)",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_204',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch no body (204)",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'fetch_304',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Fetch no body (304)",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N total active bans",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban_add',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N new bans added",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban_retire',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N old bans deleted",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban_obj_test',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N objects tested",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban_re_test',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N regexps tested against",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban_dups',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N duplicate bans removed",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban_add',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N new bans added",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban_dups',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N duplicate bans removed",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban_obj_test',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N objects tested",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban_re_test',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N regexps tested against",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_ban_retire',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N old bans deleted",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_gunzip',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Gunzip operations",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_gzip',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "Gzip operations",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_vbc',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N struct vbc",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_waitinglist',
                "call_back"  : get_delta,
                "units"      : "/s",
                "description": "N struct waitinglist",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_wrk_lqueue',
                "call_back"  : get_value,
                "units"      : "",
                "description": "work request queue length",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'n_wrk_queued',
                "call_back"  : get_value,
                "units"      : "req",
                "description": "N queued work requests",
                }))
    
    descriptors.append( create_desc(Desc_Skel, {
                "name"       : NAME_PREFIX + 'vmods',
                "call_back"  : get_value,
                "units"      : "vmods",
                "description": "Loaded VMODs",
                }))



    return descriptors


def metric_cleanup():
    """Cleanup"""

    pass


# the following code is for debugging and testing
if __name__ == '__main__':
    descriptors = metric_init(PARAMS)
    while True:
        for d in descriptors:
            print (('%s = %s') % (d['name'], d['format'])) % (d['call_back'](d['name']))
        print 'Sleeping 15 seconds'
        time.sleep(15)

########NEW FILE########
__FILENAME__ = xenstats
#       xenstats.py
#       
#       Copyright 2011 Marcos Amorim <marcosmamorim@gmail.com>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import libvirt
import os
import time

descriptors = list()
conn        = libvirt.openReadOnly("xen:///")
conn_info   = conn.getInfo()

def xen_vms(name):
    '''Return number of virtual is running'''
    global conn

    vm_count   = conn.numOfDomains()

    return vm_count

def xen_mem(name):
    '''Return node memory '''
    global conn
    global conn_info

    # O xen retorna o valor da memoria em MB, vamos passar por KB
    return conn_info[1] * 1024

def xen_cpu(name):
    '''Return numbers of CPU's'''
    global conn
    global conn_info

    return conn_info[2]


def xen_mem_use(name):
    '''Return total memory usage'''
    global conn

    vm_mem = 0

    for id in conn.listDomainsID():
        dom = conn.lookupByID(id)
        info = dom.info()
        vm_mem = vm_mem + info[2]

    return vm_mem

def metric_init(params):
    global descriptors

    d1 = {'name': 'xen_vms',
            'call_back': xen_vms,
            'time_max': 20,
            'value_type': 'uint',
            'units': 'Qtd',
            'slope': 'both',
            'format': '%d',
            'description': 'Total number of running vms',
            'groups': 'xen',
            }
    d2 = {'name': 'xen_cpu',
            'call_back': xen_cpu,
            'time_max': 20,
            'value_type': 'uint',
            'units': 'CPUs',
            'slope': 'both',
            'format': '%d',
            'description': 'CPUs',
            'groups': 'xen'
            }

    d3 = {'name': 'xen_mem',
            'call_back': xen_mem,
            'time_max': 20,
            'value_type': 'uint',
            'units': 'KB',
            'slope': 'both',
            'format': '%d',
            'description': 'Total memory Xen',
            'groups': 'xen'
            }

    d4 = {'name': 'xen_mem_use',
            'call_back': xen_mem_use,
            'time_max': 20,
            'value_type': 'uint',
            'units': 'KB',
            'slope': 'both',
            'format': '%d',
            'description': 'Memory Usage',
            'groups': 'xen'
            }

    descriptors = [d1,d2,d3,d4]

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    global conn
    conn.close()
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init('init')
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s is %u' % (d['name'],  v)


########NEW FILE########
__FILENAME__ = zpubmon
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
  ZeroMQ PUB Monitor for Ganglia
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  This is a gmond metric-gathering module which reports a cumulative
  count of messages published by ZeroMQ publishers.

  To test, invoke with one or more pairs of (endpoint name, endpoint
  URI) pairs specifying ZMQ publishers to poll. For example:

    $ python zpubmon.py system-events tcp://localhost:8006

  See README for more details.

  :copyright: (c) 2012 by Ori Livneh <ori@wikimedia.org>
  :license: GNU General Public Licence 2.0 or later

"""
import errno
import logging
import sys
import threading
import time

import zmq


logging.basicConfig(format='[ZMQ] %(asctime)s %(message)s', level=logging.INFO)


def zmq_pub_mon(endpoints, counter):
    """
    Measure throughput of ZeroMQ publishers.

    *endpoints* is a dict that maps human-readable endpoint names to
    endpoint URIs. The names are used as metric names in Ganglia and
    as the ZMQ_IDENTITY of the underlying socket.

    """
    ctx = zmq.Context.instance()
    poller = zmq.Poller()

    for name, uri in endpoints.iteritems():
        logging.info('Registering %s (%s).', name, uri)
        sock = ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.IDENTITY, name)
        sock.connect(uri)
        sock.setsockopt(zmq.SUBSCRIBE, '')
        poller.register(sock, zmq.POLLIN)

    while 1:
        try:
            for socket, _ in poller.poll():
                socket.recv(zmq.NOBLOCK)
                name = socket.getsockopt(zmq.IDENTITY)
                counter[name] += 1
        except zmq.ZMQError as e:
            # Calls interrupted by EINTR should be re-tried.
            if e.errno == errno.EINTR:
                continue
            raise


def metric_init(params):
    """
    Initialize metrics.

    Gmond invokes this method with a dict of arguments specified in
    zpubmon.py. If *params* contains a `groups` key, its value is used
    as the group name in Ganglia (in lieu of the default 'ZeroMQ').
    Other items are interpreted as (name: URI) pairs of ZeroMQ endpoints
    to monitor.

    `metric_init` spawns a worker thread to monitor these endpoints and
    returns a list of metric descriptors.

    """
    groups = params.pop('groups', 'ZeroMQ')
    counter = {name: 0 for name in params}

    thread = threading.Thread(target=zmq_pub_mon, args=(params, counter))
    thread.daemon = True
    thread.start()

    return [{
        'name': name,
        'value_type': 'uint',
        'format': '%d',
        'units': 'events',
        'slope': 'positive',
        'time_max': 20,
        'description': 'messages published',
        'groups': groups,
        'call_back': counter.get,
    } for name in params]


def metric_cleanup():
    """
    Clean-up handler

    Terminates any lingering threads. Gmond calls this function when
    it is shutting down.

    """
    logging.debug('Shutting down.')
    for thread in threading.enumerate():
        if thread.isAlive():
            thread._Thread__stop()  # pylint: disable=W0212


def self_test():
    """
    Perform self-test.

    Parses *argv* as a collection of (name, URI) pairs specifying ZeroMQ
    publishers to be monitored. Message counts are polled and outputted
    every five seconds.

    """
    params = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    if not params:
        print 'Usage: %s NAME URI [NAME URI, ...]' % sys.argv[0]
        print 'Example: %s my-zmq-stream tcp://localhost:8006' % sys.argv[0]
        sys.exit(1)

    descriptors = metric_init(params)

    while 1:
        for descriptor in descriptors:
            name = descriptor['name']
            call_back = descriptor['call_back']
            logging.info('%s: %s', name, call_back(name))
        time.sleep(5)


if __name__ == '__main__':
    self_test()

########NEW FILE########
__FILENAME__ = zfs_arc
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# gmond python module for collection ZFS ARC stats.  Based on the
# arcstat command line tool: http://github.com/mharsch/arcstat

import abc
import copy
import decimal
import logging
import logging.handlers
import optparse
import time
import sys

log = None

METRIC_PREFIX = 'zfs_arc_'

DESCRIPTION_SKELETON = {
    'name'        : 'XXX',
    'time_max'    : 60,
    'value_type'  : 'uint', # (string, uint, float, double)
    'format'      : '%d', #String formatting ('%s', '%d','%f')
    'units'       : 'XXX',
    'slope'       : 'both',
    'description' : 'XXX',
    'groups'      : 'zfs_arc'
    }


METRICS = [
    {'name': 'hits',
     'description': 'ARC reads per second',
     'units': 'hits/s'},
    {'name': 'misses',
     'description': 'ARC misses per second',
     'units': 'misses/s'},
    {'name': 'read',
     'description': 'Total ARC accesses per second',
     'units': 'reads/s'},
    {'name': 'hit_percent',
     'description': 'ARC Hit percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'miss_percent',
     'description': 'ARC miss percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'dhit',
     'description': 'Demand Data hits per second',
     'units': 'hits/s'},
    {'name': 'dmis',
     'description': 'Demand Data misses per second',
     'units': 'misses/s'},
    {'name': 'dh_percent',
     'description': 'Demand Data hit percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'dm_percent',
     'description': 'Demand Data miss percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'phit',
     'description': 'Prefetch hits per second',
     'units': 'hits/s'},
    {'name': 'pmis',
     'description': 'Prefetch misses per second',
     'units': 'misses/s'},
    {'name': 'ph_percent',
     'description': 'Prefetch hits percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'pm_percent',
     'description': 'Prefetch miss percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'mhit',
     'description': 'Metadata hits per second',
     'units': 'hits/s'},
    {'name': 'mmis',
     'description': 'Metadata misses per second',
     'units': 'misses/s'},
    {'name': 'mread',
     'description': 'Metadata accesses per second',
     'units': 'accesses/s'},
    {'name': 'mh_percent',
     'description': 'Metadata hit percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'mm_percent',
     'description': 'Metadata miss percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'size',
     'description': 'ARC Size',
     'units': 'bytes'},
    {'name': 'c',
     'description': 'ARC Target Size',
     'units': 'bytes'},
    {'name': 'mfu',
     'description': 'MFU List hits per second',
     'units': 'hits/s'},
    {'name': 'mru',
     'description': 'MRU List hits per second',
     'units': 'hits/s'},
    {'name': 'mfug',
     'description': 'MFU Ghost List hits per second',
     'units': 'hits/s'},
    {'name': 'mrug',
     'description': 'MRU Ghost List hits per second',
     'units': 'hits/s'},
    {'name': 'eskip',
     'description': 'evict_skip per second',
     'units': 'hits/s'},
    {'name': 'mtxmis',
     'description': 'mutex_miss per second',
     'units': 'misses/s'},
    {'name': 'rmis',
     'description': 'recycle_miss per second',
     'units': 'misses/s'},
    {'name': 'dread',
     'description': 'Demand data accesses per second',
     'units': 'accesses/s'},
    {'name': 'pread',
     'description': 'Prefetch accesses per second',
     'units': 'accesses/s'},
    {'name': 'l2hits',
     'description': 'L2ARC hits per second',
     'units': 'hits/s'},
    {'name': 'l2misses',
     'description': 'L2ARC misses per second',
     'units': 'misses/s'},
    {'name': 'l2read',
     'description': 'Total L2ARC accesses per second',
     'units': 'reads/s'},
    {'name': 'l2hit_percent',
     'description': 'L2ARC access hit percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'l2miss_percent',
     'description': 'L2ARC access miss percentage',
     'units': 'percent',
     'value_type': 'double',
     'format': '%f'},
    {'name': 'l2size',
     'description': 'Size of the L2ARC',
     'units': 'bytes'},
    {'name': 'l2asize',
     'description': 'Actual (compressed) size of the L2ARC',
     'units': 'bytes'},
    {'name': 'l2bytes',
     'description': 'bytes read per second from the L2ARC',
     'units': 'bytes/s'},
    ]


##### Data Access
class ArcStats(object):
    __metaclass__ = abc.ABCMeta
    
    kstats = None
    kstats_last = None
    now_ts = -1
    last_ts = -1
    values = {}

    def __init__(self, min_poll_seconds):
        self.min_poll_seconds = int(min_poll_seconds)

    def should_update(self):
        return (self.now_ts == -1 or time.time() - self.now_ts  > self.min_poll_seconds)

    def k_name(self, name):
        return name.split(METRIC_PREFIX)[-1]
    
    @abc.abstractmethod
    def update_kstats(self):
        raise NotImplementedError()

    # Primarily for debugging
    def _get_raw_metric_value(self, name, last=False):
        try:
            key = self.k_name(name)
            if last is False:
                return self.kstats[key]
            else:
                return self.kstats_last[key]
        except KeyError as e:
            log.warn('unable to find metric %s/%s (last:%s)' % (name, self.k_name(name), last))
            return None


    def get_metric_value(self, name):
        if self.should_update() is True:
            self.update_kstats()
            self.calculate_all()
        if self.kstats is None or self.kstats_last is None or len(self.values) == 0:
            log.debug('Not enough kstat data has been collected yet now_ts:%r  last_ts:%r' % (self.now_ts, self.last_ts))
            return None
        val = self.values[self.k_name(name)]
        log.debug('on call_back got %s = %r' % (self.k_name(name), val))
        if NAME_2_DESCRIPTOR[name]['value_type'] == 'uint':
            return long(val)
        else:
            return float(val)

    def l2exist(self):
        return self.kstats is not None and'l2_size' in self.kstats

    def calculate_all(self):
        if self.kstats is None or self.kstats_last is None:
            return None
        snap = {}
        for key in self.kstats:
            snap[key] = self._get_raw_metric_value(key) - self._get_raw_metric_value(key, last=True)
        v = dict()
        sint = self.now_ts - self.last_ts
        v["hits"] = snap["hits"] / sint
        v["misses"] = snap["misses"] / sint
        v["read"] = v["hits"] + v["misses"]
        v["hit_percent"] = 100 * v["hits"] / v["read"] if v["read"] > 0 else 0
        v["miss_percent"] = 100 - v["hit_percent"] if v["read"] > 0 else 0

        v["dhit"] = (snap["demand_data_hits"] + snap["demand_metadata_hits"]) / sint
        v["dmis"] = (snap["demand_data_misses"] + snap["demand_metadata_misses"]) / sint

        v["dread"] = v["dhit"] + v["dmis"]
        v["dh_percent"] = 100 * v["dhit"] / v["dread"] if v["dread"] > 0 else 0
        v["dm_percent"] = 100 - v["dh_percent"] if v["dread"] > 0 else 0

        v["phit"] = (snap["prefetch_data_hits"] + snap["prefetch_metadata_hits"]) / sint
        v["pmis"] = (snap["prefetch_data_misses"] +
                     snap["prefetch_metadata_misses"]) / sint

        v["pread"] = v["phit"] + v["pmis"]
        v["ph_percent"] = 100 * v["phit"] / v["pread"] if v["pread"] > 0 else 0
        v["pm_percent"] = 100 - v["ph_percent"] if v["pread"] > 0 else 0

        v["mhit"] = (snap["prefetch_metadata_hits"] +
                     snap["demand_metadata_hits"]) / sint
        v["mmis"] = (snap["prefetch_metadata_misses"] +
                     snap["demand_metadata_misses"]) / sint

        v["mread"] = v["mhit"] + v["mmis"]
        v["mh_percent"] = 100 * v["mhit"] / v["mread"] if v["mread"] > 0 else 0
        v["mm_percent"] = 100 - v["mh_percent"] if v["mread"] > 0 else 0

        v["size"] = self._get_raw_metric_value("size")
        v["c"] = self._get_raw_metric_value("c")
        v["mfu"] = snap["mfu_hits"] / sint
        v["mru"] = snap["mru_hits"] / sint
        v["mrug"] = snap["mru_ghost_hits"] / sint
        v["mfug"] = snap["mfu_ghost_hits"] / sint
        v["eskip"] = snap["evict_skip"] / sint
        v["rmis"] = snap["recycle_miss"] / sint
        v["mtxmis"] = snap["mutex_miss"] / sint

        if self.l2exist():
            v["l2hits"] = snap["l2_hits"] / sint
            v["l2misses"] = snap["l2_misses"] / sint
            v["l2read"] = v["l2hits"] + v["l2misses"]
            v["l2hit_percent"] = 100 * v["l2hits"] / v["l2read"] if v["l2read"] > 0 else 0
            
            v["l2miss_percent"] = 100 - v["l2hit_percent"] if v["l2read"] > 0 else 0
            v["l2size"] = self._get_raw_metric_value("l2_size")
            v["l2asize"] = self._get_raw_metric_value("l2_asize")
            v["l2bytes"] = snap["l2_read_bytes"] / sint
        self.values = v


class LinuxArcStats(ArcStats):

    def __init__(self,  min_poll_seconds):
        super(LinuxArcStats, self).__init__(min_poll_seconds)

    def update_kstats(self):
        self.kstats_last = self.kstats
        self.last_ts = self.now_ts
        self.kstats = {}

        with open('/proc/spl/kstat/zfs/arcstats') as f:
            k = [line.strip() for line in f]

        # header
        del k[0:2]

        for s in k:
            if not s:
                continue

            name, unused, value = s.split()
            self.kstats[name] = decimal.Decimal(value)
        self.now_ts = int(time.time())


#### module functions

def metric_init(params):
    global ARC_STATS, NAME_2_DESCRIPTOR
    if log is None:
       setup_logging('syslog', params['syslog_facility'], params['log_level'])
    log.debug('metric_init: %r' % params)
    if params['os'] == 'linux':
        ARC_STATS = LinuxArcStats(params['min_poll_seconds'])
    else:
        log.error('unsupported os type: %s' % params)
        return None
    descriptors = []
    for metric in METRICS:
        d = copy.copy(DESCRIPTION_SKELETON)
        d.update(metric)
        d['name'] = METRIC_PREFIX + d['name']
        d['call_back'] = ARC_STATS.get_metric_value
        descriptors.append(d)
        if params['force_double'] is True:
            d['value_type'] = 'double'
            d['format'] = '%f'
    log.debug('descriptors: %r' % descriptors)
    for d in descriptors:
        for key in ['name', 'units', 'description']:
            if d[key] == 'XXX':
                log.warn('incomplete descriptor definition: %r' % d)
        if d['value_type'] == 'uint' and d['format'] != '%d':
            log.warn('value/type format mismatch: %r' % d)
    NAME_2_DESCRIPTOR = {}
    for d in descriptors:
        NAME_2_DESCRIPTOR[d['name']] = d
    return descriptors


def metric_cleanup():
    logging.shutdown()


#### Main and Friends

def setup_logging(handlers, facility, level):
    global log

    log = logging.getLogger('gmond_python_zfs_arc')
    formatter = logging.Formatter(' | '.join(['%(asctime)s', '%(name)s',  '%(levelname)s', '%(message)s']))
    if handlers in ['syslog', 'both']:
        sh = logging.handlers.SysLogHandler(address='/dev/log', facility=facility)
        sh.setFormatter(formatter)
        log.addHandler(sh)
    if handlers in ['stdout', 'both']:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log.addHandler(ch)
    lmap = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET
        }
    log.setLevel(lmap[level])


def parse_args(argv):
    parser = optparse.OptionParser()
    parser.add_option('--log',
                      action='store', dest='log', default='stdout', choices=['stdout', 'syslog', 'both'],
                      help='log to stdout and/or syslog')
    parser.add_option('--log-level',
                      action='store', dest='log_level', default='WARNING',
                      choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'],
                      help='log to stdout and/or syslog')
    parser.add_option('--log-facility',
                      action='store', dest='log_facility', default='user',
                      help='facility to use when using syslog')

    return parser.parse_args(argv)


def main(argv):
    """ used for testing """
    (opts, args) = parse_args(argv)
    setup_logging(opts.log, opts.log_facility, opts.log_level)
    params = {'os': 'linux', 'min_poll_seconds': 5, 'force_double': True}
    descriptors = metric_init(params)
    try:
        while True:
            for d in descriptors:
                v = d['call_back'](d['name'])
                if v is None:
                    print 'got None for %s' % d['name']
                else:
                    print 'value for %s is %r' % (d['name'], v)
            time.sleep(5)
            print '----------------------------'
    except KeyboardInterrupt:
        log.debug('KeyboardInterrupt, shutting down...')
        metric_cleanup()

if __name__ == '__main__':
    main(sys.argv[1:])


########NEW FILE########
