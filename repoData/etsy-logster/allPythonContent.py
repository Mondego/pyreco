__FILENAME__ = logster_helper
#!/usr/bin/python

###
###  Copyright 2011, Etsy, Inc.
###
###  This file is part of Logster.
###  
###  Logster is free software: you can redistribute it and/or modify
###  it under the terms of the GNU General Public License as published by
###  the Free Software Foundation, either version 3 of the License, or
###  (at your option) any later version.
###  
###  Logster is distributed in the hope that it will be useful,
###  but WITHOUT ANY WARRANTY; without even the implied warranty of
###  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
###  GNU General Public License for more details.
###  
###  You should have received a copy of the GNU General Public License
###  along with Logster. If not, see <http://www.gnu.org/licenses/>.
###

try:
    from httplib import *
except ImportError:
    from http.client import *

import base64
import hashlib
import hmac
import sys

try:
    from urllib import urlencode, quote_plus
except ImportError:
    from urllib.parse import urlencode, quote_plus

from time import time

class MetricObject(object):
    """General representation of a metric that can be used in many contexts"""
    def __init__(self, name, value, units='', type='float', timestamp=int(time()), metric_type='g'):
        self.name = name
        self.value = value
        self.units = units
        self.type = type
        self.timestamp = timestamp
        self.metric_type = metric_type

class LogsterParser(object):
    """Base class for logster parsers"""
    def parse_line(self, line):
        """Take a line and do any parsing we need to do. Required for parsers"""
        raise RuntimeError("Implement me!")

    def get_state(self, duration):
        """Run any calculations needed and return list of metric objects"""
        raise RuntimeError("Implement me!")


class LogsterParsingException(Exception):
    """Raise this exception if the parse_line function wants to
        throw a 'recoverable' exception - i.e. you want parsing
        to continue but want to skip this line and log a failure."""
    pass

class LockingError(Exception):
    """ Exception raised for errors creating or destroying lockfiles. """
    pass

class CloudWatchException(Exception):
    """ Raise thie exception if the connection can't be established 
        with Amazon server """
    pass

class CloudWatch:
    """ Base class for Amazon CloudWatch """
    def __init__(self, key, secret_key, metric):
        """ Specify Amazon CloudWatch params """
        
        self.base_url = "monitoring.ap-northeast-1.amazonaws.com"
        self.key = key
        self.secret_key = secret_key
        self.metric = metric

    def get_instance_id(self, instance_id = None):
        """ get instance id from amazon meta data server """

        self.instance_id = instance_id

        if self.instance_id is None: 
            try:
                conn = HTTPConnection("169.254.169.254")
                conn.request("GET", "/latest/meta-data/instance-id")
            except Exception:
                raise CloudWatchException("Can't connect Amazon meta data server to get InstanceID : (%s)")

            self.instance_id = conn.getresponse().read()
        
        return self

    def set_params(self):

        params = {'Namespace': 'logster',
       'MetricData.member.1.MetricName': self.metric.name,
       'MetricData.member.1.Value': self.metric.value,
       'MetricData.member.1.Unit': self.metric.units,
       'MetricData.member.1.Dimensions.member.1.Name': 'InstanceID',
       'MetricData.member.1.Dimensions.member.1.Value': self.instance_id}       
     
        self.url_params = params
        self.url_params['AWSAccessKeyId'] = self.key
        self.url_params['Action'] = 'PutMetricData'
        self.url_params['SignatureMethod'] = 'HmacSHA256'
        self.url_params['SignatureVersion'] = '2'
        self.url_params['Version'] = '2010-08-01'
        self.url_params['Timestamp'] = self.metric.timestamp

        return self
    
    def get_signed_url(self):
        """ build signed parameters following
            http://docs.amazonwebservices.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html """
        keys = sorted(self.url_params)
        values = map(self.url_params.get, keys)
        url_string = urlencode(list(zip(keys,values)))

        string_to_sign = "GET\n%s\n/\n%s" % (self.base_url, url_string)
        try:
            if sys.version_info[:2] == (2, 5):
                signature = hmac.new( key=self.secret_key, msg=string_to_sign, digestmod=hashlib.sha256).digest()
            else:
                signature = hmac.new( key=bytes(self.secret_key), msg=bytes(string_to_sign), digestmod=hashlib.sha256).digest()
        except TypeError:
            signature = hmac.new( key=bytes(self.secret_key, "utf-8"), msg=bytes(string_to_sign, "utf-8"), digestmod=hashlib.sha256).digest()

        signature = base64.encodestring(signature).strip()
        urlencoded_signature = quote_plus(signature)
        url_string += "&Signature=%s" % urlencoded_signature

        return "/?" + url_string
 
    def put_data(self):
        signedURL = self.set_params().get_signed_url()
        try:
            conn = HTTPConnection(self.base_url)
            conn.request("GET", signedURL)
        except Exception:
            raise CloudWatchException("Can't connect Amazon CloudWatch server") 
        res = conn.getresponse()



########NEW FILE########
__FILENAME__ = ErrorLogLogster
###  A logster parser file that can be used to count the number of different
###  messages in an Apache error_log
###
###  For example:
###  sudo ./logster --dry-run --output=ganglia ErrorLogLogster /var/log/httpd/error_log
###
###

import time
import re

from logster.logster_helper import MetricObject, LogsterParser
from logster.logster_helper import LogsterParsingException

class ErrorLogLogster(LogsterParser):

    def __init__(self, option_string=None):
        '''Initialize any data structures or variables needed for keeping track
        of the tasty bits we find in the log we are parsing.'''
        self.notice = 0
        self.warn = 0
        self.error = 0
        self.crit = 0
        self.other = 0
        
        # Regular expression for matching lines we are interested in, and capturing
        # fields from the line
        self.reg = re.compile('^\[[^]]+\] \[(?P<loglevel>\w+)\] .*')


    def parse_line(self, line):
        '''This function should digest the contents of one line at a time, updating
        object's state variables. Takes a single argument, the line to be parsed.'''

        try:
            # Apply regular expression to each line and extract interesting bits.
            regMatch = self.reg.match(line)

            if regMatch:
                linebits = regMatch.groupdict()
                level = linebits['loglevel']

                if (level == 'notice'):
                    self.notice += 1
                elif (level == 'warn'):
                    self.warn += 1
                elif (level == 'error'):
                    self.error += 1
                elif (level == 'crit'):
                    self.crit += 1
                else:
                    self.other += 1

            else:
                raise LogsterParsingException, "regmatch failed to match"

        except Exception, e:
            raise LogsterParsingException, "regmatch or contents failed with %s" % e


    def get_state(self, duration):
        '''Run any necessary calculations on the data collected from the logs
        and return a list of metric objects.'''
        self.duration = duration / 10

        # Return a list of metrics objects
        return [
            MetricObject("notice", (self.notice / self.duration), "Logs per 10 sec"),
            MetricObject("warn", (self.warn / self.duration), "Logs per 10 sec"),
            MetricObject("error", (self.error / self.duration), "Logs per 10 sec"),
            MetricObject("crit", (self.crit / self.duration), "Logs per 10 sec"),
            MetricObject("other", (self.other / self.duration), "Logs per 10 sec"),
        ]

########NEW FILE########
__FILENAME__ = Log4jLogster
###  Author: Mike Babineau <michael.babineau@gmail.com>, EA2D <http://ea2d.com>
###
###  A sample logster parser file that can be used to count the number
###  of events for each log level in a log4j log.
###
###  Example (note WARN,ERROR,FATAL is default):
###  sudo ./logster --output=stdout Log4jLogster /var/log/example_app/app.log --parser-options '-l WARN,ERROR,FATAL'
###
###
###  Logster copyright 2011, Etsy, Inc.
###
###  This file is part of Logster.
###
###  Logster is free software: you can redistribute it and/or modify
###  it under the terms of the GNU General Public License as published by
###  the Free Software Foundation, either version 3 of the License, or
###  (at your option) any later version.
###
###  Logster is distributed in the hope that it will be useful,
###  but WITHOUT ANY WARRANTY; without even the implied warranty of
###  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
###  GNU General Public License for more details.
###
###  You should have received a copy of the GNU General Public License
###  along with Logster. If not, see <http://www.gnu.org/licenses/>.
###

import time
import re
import optparse

from logster.logster_helper import MetricObject, LogsterParser
from logster.logster_helper import LogsterParsingException

class Log4jLogster(LogsterParser):
    
    def __init__(self, option_string=None):
        '''Initialize any data structures or variables needed for keeping track
        of the tasty bits we find in the log we are parsing.'''
        
        if option_string:
            options = option_string.split(' ')
        else:
            options = []
        
        optparser = optparse.OptionParser()
        optparser.add_option('--log-levels', '-l', dest='levels', default='WARN,ERROR,FATAL',
                            help='Comma-separated list of log levels to track: (default: "WARN,ERROR,FATAL")')
        
        opts, args = optparser.parse_args(args=options)
            
        self.levels = opts.levels.split(',')
        
        for level in self.levels:
            # Track counts from 0 for each log level
            setattr(self, level, 0)
        
        # Regular expression for matching lines we are interested in, and capturing
        # fields from the line (in this case, a log level such as WARN, ERROR, or FATAL).
        self.reg = re.compile('[0-9-_:\.]+ (?P<log_level>%s)' % ('|'.join(self.levels)) )
        
        
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time, updating
        object's state variables. Takes a single argument, the line to be parsed.'''
        
        try:
            # Apply regular expression to each line and extract interesting bits.
            regMatch = self.reg.match(line)
            
            if regMatch:
                linebits = regMatch.groupdict()
                log_level = linebits['log_level']
                
                if log_level in self.levels:
                    current_val = getattr(self, log_level)
                    setattr(self, log_level, current_val+1)
                    
            else:
                raise LogsterParsingException, "regmatch failed to match"
                
        except Exception, e:
            raise LogsterParsingException, "regmatch or contents failed with %s" % e
            
            
    def get_state(self, duration):
        '''Run any necessary calculations on the data collected from the logs
        and return a list of metric objects.'''
        self.duration = duration
        
        metrics = [MetricObject(level, (getattr(self, level) / self.duration)) for level in self.levels]
        return metrics
########NEW FILE########
__FILENAME__ = MetricLogster
###  Author: Mark Crossfield <mark.crossfield@tradermedia.co.uk>, Mark Crossfield <mark@markcrossfield.co.uk>
###  Rewritten and extended in collaboration with Jeff Blaine, who first contributed the MetricLogster.
###
###  Collects arbitrary metric lines and spits out aggregated
###  metric values (MetricObjects) based on the metric names
###  found in the lines. Any conforming metric, one parser. Sweet.
###  The logger indicates whether metric is a count or time by use of a marker.
###  This is enough information to work out what to push to Graphite;
###    - for counters the values are totalled
###    - for times the median and 90th percentile (configurable) are computed
###
###  Logs should contain lines such as below - these can be interleaved with other lines with no problems.
###
###    ... METRIC_TIME metric=some.metric.time value=10ms
###    ... METRIC_TIME metric=some.metric.time value=11ms
###    ... METRIC_TIME metric=some.metric.time value=20ms
###    ... METRIC_COUNT metric=some.metric.count value=1
###    ... METRIC_COUNT metric=some.metric.count value=2.2
###
###  Results:
###    some.metric.count 3.2
###    some.metric.time.mean 13.6666666667
###    some.metric.time.median 11
###    some.metric.time.90th_percentile 18.2
###
###  If the metric is a time the parser will extract the unit from the fist line it encounters for each run.
###  This means it is important for the logger to be consistent with its units.
###  Note: units are irrelevant for Graphite, as it does not support them; this functionality is to cater for Ganglia.
###
###  For example:
###  sudo ./logster --output=stdout MetricLogster /var/log/example_app/app.log --parser-options '--percentiles 25,75,90'
###
###  Based on SampleLogster which is Copyright 2011, Etsy, Inc.

import re
import optparse

from logster.parsers import stats_helper

from logster.logster_helper import MetricObject, LogsterParser
from logster.logster_helper import LogsterParsingException

class MetricLogster(LogsterParser):

    def __init__(self, option_string=None):
        '''Initialize any data structures or variables needed for keeping track
        of the tasty bits we find in the log we are parsing.'''

        self.counts = {}
        self.times = {}

        if option_string:
            options = option_string.split(' ')
        else:
            options = []

        optparser = optparse.OptionParser()
        optparser.add_option('--percentiles', '-p', dest='percentiles', default='90',
                            help='Comma-separated list of integer percentiles to track: (default: "90")')

        opts, args = optparser.parse_args(args=options)

        self.percentiles = opts.percentiles.split(',')

        # General regular expressions, expecting the metric name to be included in the log file.

        self.count_reg = re.compile('.*METRIC_COUNT\smetric=(?P<count_name>[^\s]+)\s+value=(?P<count_value>[0-9.]+)[^0-9.].*')
        self.time_reg = re.compile('.*METRIC_TIME\smetric=(?P<time_name>[^\s]+)\s+value=(?P<time_value>[0-9.]+)\s*(?P<time_unit>[^\s$]*).*')

    def parse_line(self, line):
        '''This function should digest the contents of one line at a time, updating
        object's state variables. Takes a single argument, the line to be parsed.'''

        count_match = self.count_reg.match(line)
        if count_match:
            countbits = count_match.groupdict()
            count_name = countbits['count_name']
            if not self.counts.has_key(count_name):
                self.counts[count_name] = 0.0
            self.counts[count_name] += float(countbits['count_value']);

        time_match = self.time_reg.match(line)
        if time_match:
            time_name = time_match.groupdict()['time_name']
            if not self.times.has_key(time_name):
                unit = time_match.groupdict()['time_unit']
                self.times[time_name] = {'unit': unit, 'values': []};
            self.times[time_name]['values'].append(float(time_match.groupdict()['time_value']))

    def get_state(self, duration):
        '''Run any necessary calculations on the data collected from the logs
        and return a list of metric objects.'''
        metrics = []
        if duration > 0:
            metrics += [MetricObject(counter, self.counts[counter]/duration) for counter in self.counts]
        for time_name in self.times:
            values = self.times[time_name]['values']
            unit = self.times[time_name]['unit']
            metrics.append(MetricObject(time_name+'.mean', stats_helper.find_mean(values), unit))
            metrics.append(MetricObject(time_name+'.median', stats_helper.find_median(values), unit))
            metrics += [MetricObject('%s.%sth_percentile' % (time_name,percentile), stats_helper.find_percentile(values,int(percentile)), unit) for percentile in self.percentiles]

        return metrics

########NEW FILE########
__FILENAME__ = PostfixLogster
###  A logster parser file that can be used to count the number
###  of sent/deferred/bounced emails from a Postfix log, along with
### some other associated statistics.
###         
###  For example:
###  sudo ./logster --dry-run --output=ganglia PostfixParser /var/log/maillog
###            
###            
###  Copyright 2011, Bronto Software, Inc.
###               
###  This parser is free software: you can redistribute it and/or modify
###  it under the terms of the GNU General Public License as published by
###  the Free Software Foundation, either version 3 of the License, or
###  (at your option) any later version.
###
###  This parser is distributed in the hope that it will be useful,
###  but WITHOUT ANY WARRANTY; without even the implied warranty of
###  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
###  GNU General Public License for more details.
### 
        
import time
import re
        
from logster.logster_helper import MetricObject, LogsterParser
from logster.logster_helper import LogsterParsingException
        
class PostfixLogster(LogsterParser):
        
    def __init__(self, option_string=None):
        '''Initialize any data structures or variables needed for keeping track
        of the tasty bits we find in the log we are parsing.'''
        self.numSent = 0
        self.numDeferred = 0
        self.numBounced = 0
        self.totalDelay = 0
        self.numRbl = 0
        
        # Regular expression for matching lines we are interested in, and capturing
        # fields from the line (in this case, http_status_code).
        self.reg = re.compile('.*delay=(?P<send_delay>[^,]+),.*status=(?P<status>(sent|deferred|bounced))')
           
    def parse_line(self, line):
        '''This function should digest the contents of one line at a time, updating
        object's state variables. Takes a single argument, the line to be parsed.'''
        
        try:
            # Apply regular expression to each line and extract interesting bits.
            regMatch = self.reg.match(line)

            if regMatch:
               linebits = regMatch.groupdict()
               if (linebits['status'] == 'sent'):
                  self.totalDelay += float(linebits['send_delay'])
                  self.numSent += 1
               elif (linebits['status'] == 'deferred'):
                  self.numDeferred += 1
               elif (linebits['status'] == 'bounced'):
                  self.numBounced += 1

        except Exception, e:
            raise LogsterParsingException, "regmatch or contents failed with %s" % e


    def get_state(self, duration):
        '''Run any necessary calculations on the data collected from the logs
        and return a list of metric objects.'''
        self.duration = duration
        totalTxns = self.numSent + self.numBounced + self.numDeferred
        pctDeferred = 0.0
        pctSent = 0.0
        pctBounced = 0.0
        avgDelay = 0
        mailTxnsSec = 0
        mailSentSec = 0

        #mind divide by zero situations 
        if (totalTxns > 0):
           pctDeferred = (self.numDeferred / totalTxns) * 100
           pctSent = (self.numSent / totalTxns) * 100
           pctBounced = (self.numBounced / totalTxns ) * 100

        if (self.numSent > 0):
           avgDelay = self.totalDelay / self.numSent

        if (self.duration > 0):
           mailTxnsSec = totalTxns / self.duration
           mailSentSec = self.numSent / self.duration

        # Return a list of metrics objects
        return [
            MetricObject("numSent", self.numSent, "Total Sent"),
            MetricObject("pctSent", pctSent, "Percentage Sent"),
            MetricObject("numDeferred", self.numDeferred, "Total Deferred"),
            MetricObject("pctDeferred", pctDeferred, "Percentage Deferred"),
            MetricObject("numBounced", self.numBounced, "Total Bounced"),
            MetricObject("pctBounced", pctBounced, "Percentage Bounced"),
            MetricObject("mailTxnsSec", mailTxnsSec, "Transactions per sec"),
            MetricObject("mailSentSec", mailSentSec, "Sends per sec"),
            MetricObject("avgDelay", avgDelay, "Average Sending Delay"),
        ]      

########NEW FILE########
__FILENAME__ = SampleLogster
###  A sample logster parser file that can be used to count the number
###  of response codes found in an Apache access log.
###
###  For example:
###  sudo ./logster --dry-run --output=ganglia SampleLogster /var/log/httpd/access_log
###
###
###  Copyright 2011, Etsy, Inc.
###
###  This file is part of Logster.
###
###  Logster is free software: you can redistribute it and/or modify
###  it under the terms of the GNU General Public License as published by
###  the Free Software Foundation, either version 3 of the License, or
###  (at your option) any later version.
###
###  Logster is distributed in the hope that it will be useful,
###  but WITHOUT ANY WARRANTY; without even the implied warranty of
###  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
###  GNU General Public License for more details.
###
###  You should have received a copy of the GNU General Public License
###  along with Logster. If not, see <http://www.gnu.org/licenses/>.
###

import time
import re

from logster.logster_helper import MetricObject, LogsterParser
from logster.logster_helper import LogsterParsingException

class SampleLogster(LogsterParser):

    def __init__(self, option_string=None):
        '''Initialize any data structures or variables needed for keeping track
        of the tasty bits we find in the log we are parsing.'''
        self.http_1xx = 0
        self.http_2xx = 0
        self.http_3xx = 0
        self.http_4xx = 0
        self.http_5xx = 0
        
        # Regular expression for matching lines we are interested in, and capturing
        # fields from the line (in this case, http_status_code).
        self.reg = re.compile('.*HTTP/1.\d\" (?P<http_status_code>\d{3}) .*')


    def parse_line(self, line):
        '''This function should digest the contents of one line at a time, updating
        object's state variables. Takes a single argument, the line to be parsed.'''

        try:
            # Apply regular expression to each line and extract interesting bits.
            regMatch = self.reg.match(line)

            if regMatch:
                linebits = regMatch.groupdict()
                status = int(linebits['http_status_code'])

                if (status < 200):
                    self.http_1xx += 1
                elif (status < 300):
                    self.http_2xx += 1
                elif (status < 400):
                    self.http_3xx += 1
                elif (status < 500):
                    self.http_4xx += 1
                else:
                    self.http_5xx += 1

            else:
                raise LogsterParsingException, "regmatch failed to match"

        except Exception, e:
            raise LogsterParsingException, "regmatch or contents failed with %s" % e


    def get_state(self, duration):
        '''Run any necessary calculations on the data collected from the logs
        and return a list of metric objects.'''
        self.duration = duration

        # Return a list of metrics objects
        return [
            MetricObject("http_1xx", (self.http_1xx / self.duration), "Responses per sec"),
            MetricObject("http_2xx", (self.http_2xx / self.duration), "Responses per sec"),
            MetricObject("http_3xx", (self.http_3xx / self.duration), "Responses per sec"),
            MetricObject("http_4xx", (self.http_4xx / self.duration), "Responses per sec"),
            MetricObject("http_5xx", (self.http_5xx / self.duration), "Responses per sec"),
        ]

########NEW FILE########
__FILENAME__ = SquidLogster
###  A sample logster parser file that can be used to count the number
###  of responses and object size in the squid access.log
###
###  For example:
###  sudo ./logster --dry-run --output=ganglia SquidLogster /var/log/squid/access.log
###
###
###  Copyright 2011, Etsy, Inc.
###
###  This file is part of Logster.
###
###  Logster is free software: you can redistribute it and/or modify
###  it under the terms of the GNU General Public License as published by
###  the Free Software Foundation, either version 3 of the License, or
###  (at your option) any later version.
###
###  Logster is distributed in the hope that it will be useful,
###  but WITHOUT ANY WARRANTY; without even the implied warranty of
###  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
###  GNU General Public License for more details.
###
###  You should have received a copy of the GNU General Public License
###  along with Logster. If not, see <http://www.gnu.org/licenses/>.
###

import time
import re

from logster.logster_helper import MetricObject, LogsterParser
from logster.logster_helper import LogsterParsingException

class SquidLogster(LogsterParser):

    def __init__(self, option_string=None):
        '''Initialize any data structures or variables needed for keeping track
        of the tasty bits we find in the log we are parsing.'''
        self.size_transferred = 0
        self.squid_codes = {
                'TCP_MISS': 0,
                'TCP_DENIED': 0,
                'TCP_HIT': 0,
                'TCP_MEM_HIT': 0,
                'OTHER': 0,
                }
        self.http_1xx = 0
        self.http_2xx = 0
        self.http_3xx = 0
        self.http_4xx = 0
        self.http_5xx = 0

        # Regular expression for matching lines we are interested in, and capturing
        # fields from the line (in this case, http_status_code, size and squid_code).
        self.reg = re.compile('^[0-9.]+ +(?P<size>[0-9]+) .*(?P<squid_code>(TCP|UDP|NONE)_[A-Z_]+)/(?P<http_status_code>\d{3}) .*')


    def parse_line(self, line):
        '''This function should digest the contents of one line at a time, updating
        object's state variables. Takes a single argument, the line to be parsed.'''

        try:
            # Apply regular expression to each line and extract interesting bits.
            regMatch = self.reg.match(line)

            if regMatch:
                linebits = regMatch.groupdict()
                status = int(linebits['http_status_code'])
                squid_code = linebits['squid_code']
                size = int(linebits['size'])

                if (status < 200):
                    self.http_1xx += 1
                elif (status < 300):
                    self.http_2xx += 1
                elif (status < 400):
                    self.http_3xx += 1
                elif (status < 500):
                    self.http_4xx += 1
                else:
                    self.http_5xx += 1

                if self.squid_codes.has_key(squid_code):
                    self.squid_codes[squid_code] += 1
                else:
                    self.squid_codes['OTHER'] += 1

                self.size_transferred += size

            else:
                raise LogsterParsingException, "regmatch failed to match"

        except Exception, e:
            raise LogsterParsingException, "regmatch or contents failed with %s" % e


    def get_state(self, duration):
        '''Run any necessary calculations on the data collected from the logs
        and return a list of metric objects.'''
        self.duration = duration

        # Return a list of metrics objects
        return_array = [
            MetricObject("http_1xx", (self.http_1xx / self.duration), "Responses per sec"),
            MetricObject("http_2xx", (self.http_2xx / self.duration), "Responses per sec"),
            MetricObject("http_3xx", (self.http_3xx / self.duration), "Responses per sec"),
            MetricObject("http_4xx", (self.http_4xx / self.duration), "Responses per sec"),
            MetricObject("http_5xx", (self.http_5xx / self.duration), "Responses per sec"),
            MetricObject("size", (self.size_transferred / self.duration), "Size per sec")
        ]
        for squid_code in self.squid_codes:
            return_array.append(MetricObject("squid_" + squid_code, (self.squid_codes[squid_code]/self.duration), "Squid code per sec"))

        return return_array

########NEW FILE########
__FILENAME__ = stats_helper
###  Author: Mark Crossfield <mark.crossfield@tradermedia.co.uk>, Mark Crossfield <mark@markcrossfield.co.uk>
###
###  A helper to assist with the calculation of statistical functions. This has probably been done better elsewhere but I wanted an easy import.
###
###  Percentiles are calculated with linear interpolation between points.

def find_median(numbers):
    return find_percentile(numbers,50)


def find_percentile(numbers,percentile):
    numbers.sort()
    if len(numbers) == 0:
        return None
    if len(numbers) == 1:
        return numbers[0];
    elif (float(percentile) / float(100))*float(len(numbers)-1) %1 != 0:
        left_index = int(percentile * (len(numbers) - 1) / 100)
        number_one = numbers[left_index ]
        number_two = numbers[left_index + 1]
        return number_one + ( number_two - number_one) * (((float(percentile)/100)*(len(numbers)-1)%1))
    else:
        return numbers[int(percentile*(len(numbers)-1)/100)]

def find_mean(numbers):
    if len(numbers) == 0:
        return None
    else:
        return sum(numbers,0.0) / len(numbers)

########NEW FILE########
__FILENAME__ = test_cloudwatch
from logster.logster_helper import CloudWatch, MetricObject
from time import time, strftime, gmtime
import unittest

class TestCloudWatch(unittest.TestCase):

    def setUp(self):

        self.metric = MetricObject("ERROR", 1, None)
        self.metric.timestamp = strftime("%Y%m%dT%H:%M:00Z", gmtime(self.metric.timestamp))

        self.cw = CloudWatch("key", "secretkey", self.metric)
        self.cw.get_instance_id("myserverID").set_params().get_signed_url()

    def test_params(self):

        self.assertEqual(self.cw.base_url, "monitoring.ap-northeast-1.amazonaws.com")
        self.assertEqual(self.cw.key, "key")
        self.assertEqual(self.cw.secret_key, "secretkey")
        self.assertEqual(self.cw.url_params['Namespace'], "logster")
        self.assertEqual(self.cw.url_params['MetricData.member.1.MetricName'], "ERROR")
        self.assertEqual(self.cw.url_params['MetricData.member.1.Value'], 1)
        self.assertEqual(self.cw.url_params['MetricData.member.1.Unit'], None)
        self.assertEqual(self.cw.url_params['MetricData.member.1.Dimensions.member.1.Name'], "InstanceID")
        self.assertEqual(self.cw.url_params['MetricData.member.1.Dimensions.member.1.Value'], "myserverID")
        self.assertEqual(self.cw.url_params['AWSAccessKeyId'], "key")
        self.assertEqual(self.cw.url_params['Timestamp'], self.metric.timestamp)
        self.assertEqual(self.cw.url_params['Action'], 'PutMetricData')
        self.assertEqual(self.cw.url_params['SignatureMethod'], 'HmacSHA256')
        self.assertEqual(self.cw.url_params['SignatureVersion'], '2')
        self.assertEqual(self.cw.url_params['Version'], '2010-08-01')

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_stats_helper
from logster.parsers import stats_helper
import unittest

class TestStatsHelper(unittest.TestCase):

    def test_median_of_1(self):
        self.assertEqual(stats_helper.find_median([0]), 0)
        self.assertEqual(stats_helper.find_median([1]), 1)
        self.assertEqual(stats_helper.find_median([1,2]), 1.5)
        self.assertEqual(stats_helper.find_median([1,2,3]), 2)
        self.assertEqual(stats_helper.find_median([1,-1]), 0)
        self.assertEqual(stats_helper.find_median([1,999999]), 500000)

    def test_median_floats(self):
        self.assertEqual(stats_helper.find_median([float(1.1),float(2.3),float(0.4)]), 1.1)

    def test_max_0(self):
        self.assertEqual(stats_helper.find_percentile([0],100), 0)
    def test_max_0_to_1(self):
        self.assertEqual(stats_helper.find_percentile([0,1],100), 1)
    def test_max_0_to_3(self):
        self.assertEqual(stats_helper.find_percentile([0,1,2,3],100), 3)
    def test_max_0_to_5(self):
        self.assertEqual(stats_helper.find_percentile([0,1,2,3,4,5],100), 5)
    def test_max_0_to_6(self):
        self.assertEqual(stats_helper.find_percentile([0,1,2,3,4,5,6],100), 6)
    def test_max_0_to_10(self):
        self.assertEqual(stats_helper.find_percentile([0,1,2,3,4,5,6,7,8,9,10],100), 10)
    def test_max_0_to_11(self):
        self.assertEqual(stats_helper.find_percentile([0,1,2,3,4,5,6,7,8,9,10,11],100), 11)
    def test_max_floats(self):
        self.assertEqual(stats_helper.find_percentile([0,0.1,1.5,100],100), 100)

    def test_10th_0_to_10(self):
        self.assertEqual(stats_helper.find_percentile([0,1,2,3,4,5,6,7,8,9,10],10), 1)

    def test_10th_1_to_3(self):
        self.assertEqual(stats_helper.find_percentile([1,2,3],10), 1.2)

    def test_12th_0_to_9(self):
        self.assertEqual(stats_helper.find_percentile([0,1,2,3,4,5,6,7,8,9],12), 1.08)

    def test_90th_0(self):
        self.assertEqual(stats_helper.find_percentile([0],90), 0)

    def test_90th_1(self):
        self.assertEqual(stats_helper.find_percentile([1],90), 1)

    def test_90th_1_2(self):
        self.assertEqual(stats_helper.find_percentile([1,2],90), 1.9)

    def test_90th_1_2_3(self):
        self.assertEqual(stats_helper.find_percentile([1,2,3],90), 2.8)

    def test_90th_1_minus1(self):
        self.assertEqual(stats_helper.find_percentile([1,-1],90), 0.8)

    def test_90th_1_to_10(self):
        self.assertEqual(stats_helper.find_percentile([1,2,3,4,5,6,7,8,9,10],90), 9.1)

    def test_90th_1_to_11(self):
        self.assertEqual(stats_helper.find_percentile([1,2,3,4,5,6,7,8,9,10,11],90), 10)

    def test_90th_1_to_15_noncontiguous(self):
        self.assertAlmostEqual(stats_helper.find_percentile([1,2,3,4,5,6,7,8,9,15],90), 9.6)

########NEW FILE########
