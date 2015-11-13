__FILENAME__ = fabfile
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
Fabric build/deploy script for logtools
"""

import os
import sys
import tarfile
import logging
import datetime

from fabric.api import run, env, cd
from fabric.operations import put, sudo, prompt, local
from fabric.decorators import hosts

log = logging.getLogger(__name__)

env.proj_name = 'logtools'

def dist():
    """Create distributable"""
    local('python setup.py bdist_egg')

def deploy(deploydir, virtualenv=None):
    """Deploy distributable on target machine.
    Specify 'virtualenv' as path to the virtualenv (if any),
    Specify 'deploydir' as directory to push egg file to."""
    _find_dist()
    put("dist/%s" % env.dist_fname, deploydir)
    source_me = ''
    if virtualenv:
        source_me = 'source {0}/bin/activate && '.format(virtualenv)
    run(source_me + 'easy_install -U {0}/{1}'.format(deploydir, env.dist_fname))

def _find_dist():
    """Find latest version of our distributable and point to it in env"""
    _dist_fname = local("ls -tr dist/%s*.egg | tail -n1" % env.proj_name.replace("-", "_"))
    if _dist_fname.failed == True:
        return -1
    _dist_fname = os.path.basename(_dist_fname.strip())
    env.dist_fname = _dist_fname

########NEW FILE########
__FILENAME__ = join_backends
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools.join_backends
Backends used by the logjoin API / tool
"""
import os
import re
import sys
import logging
from functools import partial
from datetime import datetime
from abc import ABCMeta, abstractmethod
import json

from _config import AttrDict

from sqlsoup import SQLSoup

__all__ = ['JoinBackend', 'SQLAlchemyJoinBackend']


class JoinBackend(object):
    """Base class for all our parsers"""
    __metaclass__ = ABCMeta

    def __init__(self, remote_fields, remote_name, 
                 remote_key, connect_str=None):
        """Initialize. Can get an optional connection
        string"""
        
    @abstractmethod
    def join(self, rows):
        """Implement a join generator"""
        
        
class SQLAlchemyJoinBackend(JoinBackend):
    """sqlalchemy-based join backend,
    allowing for arbitrary DB's based on a
    connection URL"""
    
    def __init__(self, remote_fields, remote_name, 
                 remote_key, connect_string):
        """Initialize db connection"""
        self.connect_string = connect_string
        self.remote_fields = remote_fields
        self.remote_name = remote_name
        self.remote_key = remote_key
        self.query_stmt = self._create_query_stmt()

        self.connect()
                
        
    def connect(self):
        """Connect to remote join backend (DB)"""
        self.db = SQLSoup(self.connect_string)
        
        
    def join(self, key):
        rp = self.db.bind.execute(self.query_stmt, key=key)
        for row in rp.fetchall():
            yield row # dict(zip(field_names, row))
                
                
    def _create_query_stmt(self):
        """Create valid query statement string
        to be used with interpolating bound variables.
        Unfortunately, there is inconcistency in syntax
        across different drivers"""
        connstr = self.connect_string
        if connstr.startswith("sqlite"):
            query_stmt = """SELECT {0} FROM {1} WHERE {2} = :key""".format(self.remote_fields, 
                                                self.remote_name, self.remote_key)            
        else:
            query_stmt = """SELECT {0} FROM {1} WHERE {2} = %(key)s""".format(self.remote_fields, 
                                        self.remote_name, self.remote_key)
        
        return query_stmt

########NEW FILE########
__FILENAME__ = parsers
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools.parsers
Parsers for some common log formats, e.g Common Log Format (CLF).
These parsers can be used both programmaticaly as well as by the 
logtools command-line tools to meaningfully parse log fields 
from standard formats.
"""
import os
import re
import sys
import logging
from functools import partial
from datetime import datetime
from abc import ABCMeta, abstractmethod
import json

from _config import AttrDict

__all__ = ['multikey_getter_gen', 'unescape_json', 'LogParser', 'JSONParser', 'LogLine',
           'AccessLog', 'CommonLogFormat', 'uWSGIParser']


def multikey_getter_gen(parser, keys, is_indices=False, delimiter="\t"):
    """Generator meta-function to return a function
    parsing a logline and returning multiple keys (tab-delimited)"""
    if is_indices:
        keys = map(int, keys)
        
    def multikey_getter(line, parser, keyset):
        data = parser(line.strip())
        return delimiter.join((unicode(data[k]) for k in keyset))
    
    def multiindex_getter(line, parser, keyset):
        data = parser(line.strip())
        return delimiter.join((unicode(data.by_index(idx-1, raw=True)) for idx in keys))

    if is_indices is True:
        # Field indices
        return partial(multiindex_getter, parser=parser, keyset=keys)
    else:
        # Field names
        return partial(multikey_getter, parser=parser, keyset=keys)


def unescape_json(s):
    """Unescape a string that was previously encoded into JSON.
    This unescapes forward slashes (optional in JSON standard),
    backslashes and double quotes"""
    return s.replace("\\/", '/').replace('\\"', '"').decode('string_escape')
    

class LogParser(object):
    """Base class for all our parsers"""
    __metaclass__ = ABCMeta

    def __call__(self, line):
        """Callable interface"""
        return self.parse(line)

    @abstractmethod
    def parse(self, line):
        """Parse a logline"""
        
    def set_format(self, format):
        """Set a format specifier for parser.
        Some parsers can use this to specify
        a format string"""
        
        
class LogLine(dict):
    """Instrumented dictionary that allows
    convenient access to a parsed log lines,
    using key-based lookup / index-based / raw / parsed"""
    
    def __init__(self, fieldnames=None):
        """Initialize logline. This class can be reused
        across multiple input lines by using the clear()
        method after each invocation"""
        
        self._fieldnames = None
        
        if fieldnames:
            self.fieldnames = fieldnames
            
    @property
    def fieldnames(self):
        """Getter method for the field names"""
        return self._fieldnames
            
    @fieldnames.setter
    def fieldnames(self, fieldnames):
        """Set the log format field names"""
        self._fieldnames = dict(enumerate(fieldnames))
        
    def by_index(self, i, raw=False):
        return self.by_key(self._fieldnames[i], raw=raw)
    
    def by_key(self, key, raw=False):
        """Return the i-th field parsed"""
        val = None
        
        if raw is True:
            return self[key]
        
        if key == '%t':
            val = datetime.strptime(self[key][1:-7], '%d/%b/%Y:%H:%M:%S')
        else:
            val = self[key]
        return val
        

class JSONParser(LogParser):
    """Parser implementation for JSON format logs"""
    
    def __init__(self):
        LogParser.__init__(self)
        self._logline_wrapper = LogLine()
        
    def parse(self, line):
        """Parse JSON line"""
        parsed_row = json.loads(line)
        
        data = self._logline_wrapper

        # This is called for every log line - This is because
        # JSON logs are generally schema-less and so fields
        # can change between lines.
        self._logline_wrapper.fieldnames = parsed_row.keys()
            
        data.clear()
        for k, v in parsed_row.iteritems():
            data[k] = v

        return data
    

class AccessLog(LogParser):
    """Apache access_log logfile parser. This can
    consume arbitrary Apache log field directives. see
    http://httpd.apache.org/docs/1.3/logs.html#accesslog"""

    def __init__(self, format=None):
        LogParser.__init__(self)
        
        self.fieldnames    = None
        self.fieldselector = None
        self._logline_wrapper = None
        
        if format:
            self.fieldselector = self._parse_log_format(format)
            self._logline_wrapper = LogLine(self.fieldnames)     

    def set_format(self, format):
        """Set the access_log format"""
        self.fieldselector = self._parse_log_format(format)
        self._logline_wrapper = LogLine(self.fieldnames)     
        
    def parse(self, logline):
        """
        Parse log line into structured row.
        Will raise ParseError Exception when
        parsing failed.
        """
        try:
            match = self.fieldselector.match(logline)
        except AttributeError, exc:
            raise AttributeError("%s needs a valid format string (--format)" % \
                    self.__class__.__name__ )

        if match:
            data = self._logline_wrapper
            data.clear()
            for k, v in zip(self.fieldnames, match.groups()):
                data[k] = v
            return data                
        else:
            raise ValueError("Could not parse log line: '%s'" % logline)

    def _parse_log_format(self, format):
        """This code piece is based on the apachelogs 
        python/perl projects. Raises an exception if 
        it couldn't compile the generated regex"""
        format = format.strip()
        format = re.sub('[ \t]+',' ',format)

        subpatterns = []

        findquotes = re.compile(r'^"')
        findreferreragent = re.compile('Referer|User-Agent')
        findpercent = re.compile(r'^%.*t$')
        lstripquotes = re.compile(r'^"')
        rstripquotes = re.compile(r'"$')
        self.fieldnames = []

        for element in format.split(' '):
            hasquotes = 0
            if findquotes.match(element): 
                hasquotes = 1

            if hasquotes:
                element = lstripquotes.sub('', element)
                element = rstripquotes.sub('', element)

            self.fieldnames.append(element)

            subpattern = '(\S*)'

            if hasquotes:
                if element == '%r' or findreferreragent.search(element):
                    subpattern = r'\"([^"\\]*(?:\\.[^"\\]*)*)\"'
                else:
                    subpattern = r'\"([^\"]*)\"'

            elif findpercent.search(element):
                subpattern = r'(\[[^\]]+\])'

            elif element == '%U':
                subpattern = '(.+?)'

            subpatterns.append(subpattern)

        _pattern = '^' + ' '.join(subpatterns) + '$'
        _regex = re.compile(_pattern)

        return _regex

    
class CommonLogFormat(AccessLog):
    """
    Parse the CLF Format, defined as:
    %h %l %u %t \"%r\" %>s %b
    See http://httpd.apache.org/docs/1.3/logs.html#accesslog
    """

    def __init__(self):
        AccessLog.__init__(self, format='%h %l %u %t "%r" %>s %b')


class uWSGIParser(LogParser):
    """Parser for the uWSGI log format"""

    def __init__(self):
        LogParser.__init__(self)
        self._re = re.compile(r'.* ((?:[0-9]+\.){3}[0-9]+) .* \[(.*?)\] (GET|POST) (\S+) .* generated (\d+) bytes in (\d+) msecs .*')
        self.fieldnames = ('ip', 'timestamp', 'method', 'path', 'bytes', 'processing_time')
        self._logline_wrapper = LogLine(self.fieldnames)

    def parse(self, logline):
        """Parse log line"""
        match = self._re.match(logline)
        if match:
            data = self._logline_wrapper
            data.clear()
            for k, v in zip(self.fieldnames, match.groups()):
                data[k] = v
            return data
        else:
            raise ValueError("Could not parse log line: '%s'" % logline)

########NEW FILE########
__FILENAME__ = test_logtools
#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License. 
"""Unit-test code for logtools"""

import os
import sys
import unittest
import logging
from tempfile import mkstemp
from datetime import datetime
from StringIO import StringIO
from operator import itemgetter

from logtools import (filterbots, logfilter, geoip, logsample, logsample_weighted, 
                      logparse, urlparse, logmerge, logplot, qps, sumstat)
from logtools.parsers import *
from logtools import logtools_config, interpolate_config, AttrDict


logging.basicConfig(level=logging.INFO)


class ConfigurationTestCase(unittest.TestCase):
    def testInterpolation(self):
        self.assertEqual(1, interpolate_config(1, 'bogus_sec', 'bogus_key'))
        self.assertRaises(KeyError, interpolate_config, None, 'bogus_sec', 'bogus_key')


class URLParseTestCase(unittest.TestCase):
    def setUp(self):
        self.rows = [
            "http://www.mydomain.com/my/path/myfile?myparam1=myval1&myparam2=myval2",
            "http://www.mydomain2.com",
            "http://www.mydomain3.com/home",
            "http://fun.com/index.php?home"
        ]
        
    def testUrlParse(self):
        i=0
        for row in urlparse(StringIO('\n'.join(self.rows)+'\n'), part='netloc'):
            i+=1
        self.assertEquals(i, len(self.rows), \
                          "Number of rows output is not equal to input size")
        
    def testMultipleQueryParams(self):
        url = "http://www.mydomain.com/my/path/myfile?myparam1=myval1&myparam2=myval2"
        for row in urlparse(StringIO(url+"\n"), part='query', query_params='myparam1,myparam2'):
            self.assertEquals(row[0], 'myval1', "Returned query param value was not as expected: %s" % \
                          row)

    
class ParsingTestCase(unittest.TestCase):
    def setUp(self):
        self.clf_rows = [
            '127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326',
            '127.0.0.2 - jay [10/Oct/2000:13:56:12 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326'
            ]
        self.json_rows = [
            '{"key1":"val1","key2":true,"key3":31337,"key4":null,"nested_key":[{"nested_key_1":"2"}]}'
        ]
        self.uwsgi_rows = [
                "[pid: 11216|app: 0|req: 2680/5864] 24.218.159.119 () {40 vars in 957 bytes} [Thu Jun 13 22:29:59 2013] GET /my/uri/path/?param_id=52&token=s61048gkje_l001z => generated 1813 bytes in 11 msecs (HTTP/1.1 200) 2 headers in 73 bytes (1 switches on core 0)",
                "[pid: 11217|app: 0|req: 3064/5865] 10.18.50.145 () {34 vars in 382 bytes} [Thu Jun 13 22:30:00 2013] GET / => generated 8264 bytes in 9 msecs (HTTP/1.1 200) 2 headers in 73 bytes (1 switches on core 0)"
        ]
        
    def testJSONParser(self):
        parser = JSONParser()
        for logrow in self.json_rows:
            parsed = parser(logrow)
            self.assertNotEquals(parsed, None, "Could not parse line: %s" % str(logrow))
        
    def testAccessLog(self):
        parser = AccessLog()
        parser.set_format(format='%h %l %u %t "%r" %>s %b')
        self.assertRaises(ValueError, parser, 'example for invalid format')
        for logrow in self.clf_rows:
            parsed = parser(logrow)
            self.assertNotEquals(parsed, None, "Could not parse line: %s" % str(logrow))
            
    def testCommonLogFormat(self):
        parser = CommonLogFormat()
        self.assertRaises(ValueError, parser, 'example for invalid format')
        for logrow in self.clf_rows:
            parsed = parser(logrow)
            self.assertNotEquals(parsed, None, "Could not parse line: %s" % str(logrow))        

    def testuWSGIParser(self):
        parser = uWSGIParser()
        for logrow in self.uwsgi_rows:
            parsed = parser(logrow)
            self.assertNotEquals(parsed, None, "Could not parse line: %s" % logrow)

    def testLogParse(self):
        options = AttrDict({'parser': 'CommonLogFormat', 'field': 4, 'header': False})
        fh = StringIO('\n'.join(self.clf_rows))
        output = [l for l in logparse(options, None, fh)]
        self.assertEquals(len(output), len(self.clf_rows), "Output size was not equal to input size!")
        
    def testMultiKeyGetter(self):
        parser = parser = CommonLogFormat()
        func = multikey_getter_gen(parser, keys=(1,2), is_indices=True)
        fh = StringIO('\n'.join(self.clf_rows))
        output = [func(l) for l in fh]
        self.assertEquals(len(output), len(self.clf_rows), "Output size was not equal to input size!")   
        
            
class FilterBotsTestCase(unittest.TestCase):
    def setUp(self):
        self.options = AttrDict({
            "reverse": False,
            "unescape": False,
            "printlines": False,
            "ip_ua_re": "^(?P<ip>.*?) - USER_AGENT:'(?P<ua>.*?)'",
            "bots_ips": StringIO("\n".join([
                "6.6.6.6"
            ]) + "\n"),
            "bots_ua": StringIO("\n".join([
                "## Example comment ##",
                "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
                "ssearch_bot/Nutch-1.0 (sSearch Crawler; http://www.semantissimo.de)",
                "r'.*crawler'",
                "s'MSIECrawler)'",
                "p'DotSpotsBot'",
                "p'Java/'"
                ]) + "\n")
        })
        self.fh = StringIO(
            "127.0.0.1 - USER_AGENT:'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)' - ...\n" \
            "255.255.255.255 - USER_AGENT:'Mozilla' - ...\n" \
            "1.1.1.1 - USER_AGENT:'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; MSIECrawler)'\n" \
            "2.2.2.2 - USER_AGENT:'Mozilla/4.0 (compatible; MSIE 6.0; Windows 98; Win 9x 4.90; .NET CLR 1.1.4322; MSIECrawler)'\n" \
            "3.3.3.3 - USER_AGENT:'DotSpotsBot/0.2 (crawler; support at dotspots.com)'\n" \
            "4.4.4.4 - USER_AGENT:'inagist.com url crawler'\n" \
            "5.5.5.5 - USER_AGENT:'Java/1.6.0_18'\n" \
            "6.6.6.6 - USER_AGENT:'ssearch_bot/Nutch-1.0 (sSearch Crawler; http://www.semantissimo.de)'\n"
        )
        self.json_fh = StringIO(
            '''{"timestamp":"2010\/09\/01 00:00:01","user_agent":"Mozilla\/5.0 (compatible; Googlebot\/2.1; +http:\/\/www.google.com\/bot.html)","user_ip":"66.249.71.108"}\n''' \
            '''{"timestamp":"2010\/10\/01 11:00:01","user_agent":"Mozilla\/5.0 (compatible; Googlebot\/2.1; +http:\/\/www.google.com\/bot.html)","user_ip":"66.249.71.109"}\n''' \
            '''{"timestamp":"2010\/09\/01 00:00:01","user_agent":"Mozilla\/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.1.11) Gecko\/20100701 Firefox\/3.5.11 (.NET CLR 3.5.30729)","user_ip":"100.100.1.100"}\n''' \
            '''{"timestamp":"2010\/10\/01 00:00:01","user_agent":"Mozilla\/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.1.11) Gecko\/20100701 Firefox\/3.5.11 (.NET CLR 3.5.30729)","user_ip":"6.6.6.6"}\n''' \
        )

    def testParserFiltering(self):
        json_options = self.options
        json_options['parser'] = 'JSONParser'
        json_options['ip_ua_fields'] = 'ua:user_agent,ip:user_ip'
        
        i=0
        for l in filterbots(fh=self.json_fh, **json_options):
            i+=1
        self.assertEquals(i, 1, "filterbots output size different than expected: %s" % str(i))
            
    def testRegExpFiltering(self):
        i=0
        for l in filterbots(fh=self.fh, **self.options): 
            i+=1
        self.assertEquals(i, 1, "filterbots output size different than expected: %s" % str(i))


class GeoIPTestCase(unittest.TestCase):
    def setUp(self):
        self.options = AttrDict({ 'ip_re': '^(.*?) -' })
        
        self.fh = StringIO(
            "127.0.0.1 - USER_AGENT:'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)' - ...\n" \
            "255.255.255.255 - USER_AGENT:'Mozilla' - ...\n" \
            "74.125.225.48 - USER_AGENT:'IE' - ...\n" \
            "65.55.175.254 - USER_AGENT:'IE' - ...\n"
        )

    def testGeoIP(self):
        try:
            import GeoIP
        except ImportError:
            print >> sys.stderr, "GeoIP Python package not available - skipping geoip unittest."
            return

        output = [(geocode, ip, line) for geocode, ip, line in geoip(fh=self.fh, **self.options)]
        self.assertEquals(len(output), 2, "Output size was different than expected: %s" % str(len(output)))
        
    def testFilter(self):
        """Test GeoIP filtering functionality"""        
        try:
            import GeoIP
        except ImportError:
            print >> sys.stderr, "GeoIP Python package not available - skipping geoip unittest."
            return        
        
        # Check positive filter
        self.options['filter'] = 'United States'
        output = [(geocode, ip, line) for geocode, ip, line in geoip(fh=self.fh, **self.options)]
        self.assertEquals(len(output), 2, "Output size was different than expected: %s" % str(len(output)))
        
        # Check negative filter
        self.options['filter'] = 'India'
        output = [(geocode, ip, line) for geocode, ip, line in geoip(fh=self.fh, **self.options)]
        self.assertEquals(len(output), 0, "Output size was different than expected: %s" % str(len(output)))
        
        
class SamplingTestCase(unittest.TestCase):
    def setUp(self):
        self.options = AttrDict({ 'num_samples': 1 })
        self.weighted_opts = AttrDict({
            'num_samples': 5,
            'field': 1,
            'delimiter': ' '
        })
        self.fh = StringIO("\n".join([
            '5 five', '1 one', '300 threehundred', '500 fivehundred',
            '0 zero', '-1 minusone', '670 sixhundredseventy', '1000 thousand',
            '22 twentytwo', '80 eighty', '3 three'
        ]))

    def testUniformSampling(self):
        output = [r for r in logsample(fh=self.fh, **self.options)]
        self.assertEquals(len(output), self.options.num_samples, 
                          "logsample output size different than expected: %s" % len(output))
        
    def testWeightedSampling(self):
        output = [(k, r) for k, r in logsample_weighted(fh=self.fh, **self.weighted_opts)]
        self.assertEquals(len(output), self.weighted_opts.num_samples, 
                          "logsample output size different than expected: %s" % len(output))        

class FilterTestCase(unittest.TestCase):
    """Unit-test for the logfilter functionality"""
    
    def setUp(self):
        self.testset = StringIO("\n".join([
            "AA word",
            "word AA word",
            "word AA",
            "AA",
            "aa word",
            "wordAA",
            "AAword",
            "wordAAword",
            "CC DD word"
            ])+"\n")
        self.exp_emitted_wb = 4
        self.exp_emitted = 1
        self.blacklist = StringIO("\n".join([
            'AA',
            'bb',
            'CC DD'
            ])+"\n")
        
    def testACWB(self):
        """Aho-Corasick-based matching with Word Boundaries"""
        lines = 0
        for l in logfilter(self.testset, blacklist=self.blacklist, field=1, delimiter="\t", 
                           with_acora=True, ignorecase=False,
                           word_boundaries=True):
            #print l
            lines += 1
        self.assertEquals(lines, self.exp_emitted_wb, "Number of lines emitted was not as expected: %s (Expected: %s)" %
                          (lines, self.exp_emitted_wb))
        
    def testAC(self):
        """Aho-Corasick-based matching"""
        lines = 0
        for l in logfilter(self.testset, blacklist=self.blacklist, field=1, delimiter="\t", 
                           with_acora=True, ignorecase=False,
                           word_boundaries=False):
            #print l
            lines += 1
        self.assertEquals(lines, self.exp_emitted, "Number of lines emitted was not as expected: %s (Expected: %s)" %
                          (lines, self.exp_emitted))        
        
    def testRE(self):
        """Regular Expression-based matching"""
        lines = 0
        for l in logfilter(self.testset, blacklist=self.blacklist, field=1, delimiter="\t", 
                           with_acora=False, ignorecase=False,
                           word_boundaries=False):
            #print l
            lines += 1
        self.assertEquals(lines, self.exp_emitted, "Number of lines emitted was not as expected: %s (Expected: %s)" %
                          (lines, self.exp_emitted))          
    
    def testREWB(self):
        """Regular Expression-based matching with Word Boundaries"""
        lines = 0
        for l in logfilter(self.testset, blacklist=self.blacklist, field=1, delimiter="\t", 
                           with_acora=False, ignorecase=False,
                           word_boundaries=True):
            #print l
            lines += 1
        self.assertEquals(lines, self.exp_emitted_wb, "Number of lines emitted was not as expected: %s (Expected: %s)" %
                          (lines, self.exp_emitted_wb))          


class MergeTestCase(unittest.TestCase):
    def setUp(self):
        self.tempfiles = [mkstemp(), mkstemp(), mkstemp()]
        self.args = [fname for fh, fname in self.tempfiles]

    def tearDown(self):
        """Cleanup temporary files created by test"""
        for fh, fname in self.tempfiles:
            os.remove(fname)
            
    def testNumericMerge(self):
        os.write(self.tempfiles[0][0], "\n".join(['1 one', '5 five', '300 threehundred', 
                                            '500 fivehundred']))
        os.write(self.tempfiles[1][0], "\n".join(['-1 minusone', '0 zero',
                                            '670 sixhundredseventy' ,'1000 thousand']))
        os.write(self.tempfiles[2][0], "\n".join(['3 three', '22 twentytwo', '80 eighty']))
        
        options = AttrDict({'delimiter': ' ', 'field': 1, 'numeric': True })
        output = [(k, l) for k, l in logmerge(options, self.args)]
        
        self.assertEquals(len(output), 11, "Output size was not equal to input size!")
        self.assertEquals(map(itemgetter(0), output), sorted(map(lambda x: int(x[0]), output)), 
                          "Output was not numerically sorted!")
        
    def testDateMerge(self):
        os.write(self.tempfiles[0][0], "\n".join(['2010/01/12 07:00:00,one', '2010/01/12 08:00:00,five', 
                                                  '2010/01/13 10:00:00,threehundred']))
        os.write(self.tempfiles[1][0], "\n".join(['2010/01/12 07:30:00,one', '2010/01/12 08:10:00,five', 
                                                  '2010/01/12 21:00:00,threehundred']))
        os.write(self.tempfiles[2][0], "\n".join(['2010/01/11 05:33:03,one', '2010/01/12 03:10:00,five', 
                                                  '2010/01/21 22:00:00,threehundred']))
        
        dateformat = '%Y/%m/%d %H:%M:%S'
        options = AttrDict({'delimiter': ',', 'field': 1, 'datetime': True, 'dateformat': dateformat })
        output = [(k, l) for k, l in logmerge(options, self.args)]
        
        self.assertEquals(len(output), 9, "Output size was not equal to input size!")
        self.assertEquals(map(itemgetter(0), output), sorted(map(itemgetter(0), output)), 
                          "Output was not time sorted!")        
        
    def testLexicalMerge(self):
        os.write(self.tempfiles[0][0], "\n".join(['1 one', '300 threehundred', '5 five', 
                                            '500 fivehundred']))
        os.write(self.tempfiles[1][0], "\n".join(['-1 minusone', '0 zero', '1000 thousand',
                                            '670 sixhundredseventy']))
        os.write(self.tempfiles[2][0], "\n".join(['22 twentytwo', '3 three', 
                                            '80 eighty']))
        
        options = AttrDict({ 'delimiter': ' ', 'field': 1, 'numeric': False })
        output = [(k, l) for k, l in logmerge(options, self.args)]
        
        self.assertEquals(len(output), 11, "Output size was not equal to input size!")
        self.assertEquals(map(itemgetter(0), output), sorted(map(itemgetter(0), output)), 
                          "Output was not lexically sorted!")
        
   
class QPSTestCase(unittest.TestCase):
    def setUp(self):
        self.options = AttrDict({
            "ignore": True,
            "dt_re": r'^\[(.*?)\]',
            "dateformat": "%d/%b/%Y:%H:%M:%S -0700",
            "window_size": 15
        })
        self.fh = StringIO(
            '[10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" \n' \
            '[10/Oct/2000:13:55:38 -0700] "GET /apache_pb.gif HTTP/1.0" \n' \
            '[10/Oct/2000:13:56:59 -0700] "GET /apache_pb.gif HTTP/1.0" \n' \
            '[10/Oct/2000:13:57:01 -0700] "GET /apache_pb.gif HTTP/1.0" \n' \
            '[11/Oct/2000:14:01:00 -0700] "GET /apache_pb.gif HTTP/1.0" \n' \
            '[11/Oct/2000:14:01:13 -0700] "GET /apache_pb.gif HTTP/1.0" \n' \
            '[11/Oct/2000:14:01:14 -0700] "GET /apache_pb.gif HTTP/1.0" \n'
        )
    def testQps(self):
        blocks=0
        qs=[]
        for q in qps(fh=self.fh, **self.options):
            blocks+=1
            qs.append(q)
        self.assertEquals(blocks, 3, "qps output size different than expected: %s" % str(blocks))
            
        
class PlotTestCase(unittest.TestCase):
    def setUp(self):
        self.fh = StringIO("\n".join([
            '5 five', '1 one', '300 threehundred', '500 fivehundred',
            '0 zero', '-1 minusone', '670 sixhundredseventy', '1000 thousand',
            '22 twentytwo', '80 eighty', '3 three'
        ]))

    def testGChart(self):
        try:
            import pygooglechart
        except ImportError:
            print >> sys.stderr, "pygooglechart Python package not available - skipping logplot gchart unittest."
            return        
        options = AttrDict({
            'backend': 'gchart',
            'output': False,
            'limit': 10,
            'field': 1,
            'delimiter': ' ',
            'legend': True,
            'width': 600,
            'height': 300
        })        
        chart = None
        for plot_type in ('pie', 'line'):
            self.fh.seek(0)
            options['type'] = plot_type
            chart = logplot(options, None, self.fh)
            self.assertNotEquals(chart, None, "logplot returned None. Expected a Plot object")
            
        # Should raise ValueError here due to fh being at EOF
        self.assertRaises(ValueError, logplot, options, None, self.fh)
        
        tmp_fh, tmp_fname = mkstemp()
        chart.download(tmp_fname)
        os.remove(tmp_fname)
    

class SumstatTestCase(unittest.TestCase):
    def setUp(self):
        self.data = StringIO('\n'.join([
            '500 val1',
            '440 val2',
            '320 val3',
            '85 val4',
            '13 val5'
            ]))
        self.avg = 271.6
        self.N = 1358
        self.M = 5
        
    def testSumstat(self):
        stat = sumstat(fh=self.data, delimiter=' ', reverse=True)
        self.assertEquals(stat['M'], self.M)
        self.assertEquals(stat['N'], self.N)
        self.assertEquals(stat['avg'], self.avg)
        
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools.utils
A few programmatic utilities / methods.
These are not exposed as command-line tools
but can be used by other methods
"""

import os
import sys
import time
	
def tail_f(fname, block=True, sleep=1):
	"""Mimic tail -f functionality on file descriptor.
	This assumes file current position is already where
	we want it (i.e seeked to end).
	
	This code is mostly adapted from the following Python Recipe:
	http://code.activestate.com/recipes/157035-tail-f-in-python/
	"""
	fh = open(fname, 'r')
	
	while 1:
		where = fh.tell()
		line = fh.readline()
		if not line:
			if block:
				time.sleep(sleep)
			else:
				yield
			fh.seek(where)
		else:
			yield line

########NEW FILE########
__FILENAME__ = _config
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._config

Interpolation of logtools parameters using file-based configuration
in /etc/logtools.cfg or ~/.logtoolsrc.
"""

import os
import sys
from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError

__all__ = ['logtools_config', 'interpolate_config', 'AttrDict']

logtools_config = SafeConfigParser() 
logtools_config.read(['/etc/logtools.cfg', os.path.expanduser('~/.logtoolsrc')])


class AttrDict(dict):
    """Helper class for simulation OptionParser options object"""
    def __getattr__(self, key):
        return self[key]

def interpolate_config(var, section, key, default=None, type=str):
    """Interpolate a parameter. if var is None,
    try extracting value from section.key in configuration file.
    If fails, can raise Exception / issue warning"""
    try:
        return var or {
            str: logtools_config.get,
            bool: logtools_config.getboolean,
            int:  logtools_config.getint,
            float: logtools_config.getfloat
        }.get(type, str)(section, key)
    except KeyError:
        raise KeyError("Invalid parameter type: '{0}'".format(type))    
    except (NoOptionError, NoSectionError):
        if default is not None:
            return default
        raise KeyError("Missing parameter: '{0}'".format(key))
    
    


########NEW FILE########
__FILENAME__ = _filter
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._filter
Filter rows based on blacklists and field matching.
"""
import re
import sys
import string
import logging
from itertools import imap
from functools import partial
from operator import and_
from optparse import OptionParser

import acora

from _config import logtools_config, interpolate_config, AttrDict
import logtools.parsers

__all__ = ['logfilter_parse_args', 'logfilter', 
           'logfilter_main']

# Used for aho-corasick style matching on word-boundaries.
# Closely mimicks the behavior of the python re module's \w
# character set, however might diverge slightly in case of locale-
# specific character sets.
_word_boundary_chars = set(string.printable)\
                     .difference(string.letters)\
                     .difference(string.digits)\
                     .difference(('_',))


def _is_blacklisted_re_wb(line, delimiter, field, blacklist, re_flags):
    val = line.split(delimiter)[field-1]
    for b in blacklist:
        if re.search(r'\b{0}\b'.format(b), val, re_flags):
            return True
    return False    

def _is_blacklisted_re(line, delimiter, field, blacklist, re_flags):
    val = line.split(delimiter)[field-1]
    for b in blacklist:
        if re.search(r'{0}'.format(b), val, re_flags):
            return True
    return False            

def _is_blacklisted_ac_wb(line, delimiter, field, transform_func, ac):
    val = line.split(delimiter)[field-1]
    L = len(val)
    matches = ac.findall(transform_func(val))
    for match in matches:
        word, pos = match
        l = len(word)
        if (pos == 0 or val[pos-1] in _word_boundary_chars) and \
           (pos+l == L or val[pos+l] in _word_boundary_chars):
            return True
    return False

def _is_blacklisted_ac(line, delimiter, field, transform_func, ac):
    val = line.split(delimiter)[field-1]
    matches = ac.findall(transform_func(val))
    if matches:
        return True
    return False            



def logfilter_parse_args():
    usage = "%prog " \
          "-b <blacklist_file> " \
          "[--reverse]"
    
    parser = OptionParser(usage=usage)

    parser.add_option("-b", "--blacklist", dest="blacklist", default=None, 
                      help="Blacklist (whitelist when in --reverse mode) file")
    parser.add_option("-I", "--ignore-case", dest="ignorecase", action="store_true",
                      help="Ignore case when matching")
    parser.add_option("-W", "--word-boundaries", dest="word_boundaries", action="store_true",
                      help="Only match on word boundaries (e.g start/end of line and/or spaces)")    
    parser.add_option("-A", '--with-acora', dest='with_acora', action="store_true",
                      help="Use Aho-Corasick multiple string pattern matching instead of regexps. Suitable for whole word matching")
    parser.add_option("-r", "--reverse", dest="reverse", action="store_true",
                      help="Reverse filtering")
    parser.add_option("-p", "--print", dest="printlines", action="store_true",
                      help="Print non-filtered lines")    
    parser.add_option("--parser", dest="parser",
                      help="Feed logs through a parser. Useful when reading encoded/escaped formats (e.g JSON) and when " \
                      "selecting parsed fields rather than matching via regular expression.")
    parser.add_option("-d", "--delimiter", dest="delimiter",
                      help="Delimiter character for field-separation (when not using a --parser)")        
    parser.add_option("-f", "--field", dest="field",
                      help="Index of field to use for filtering against")

    parser.add_option("-P", "--profile", dest="profile", default='logfilter',
                      help="Configuration profile (section in configuration file)")

    options, args = parser.parse_args()

    # Interpolate from configuration and open filehandle
    options.field  = interpolate_config(options.field, options.profile, 'field')
    options.delimiter = interpolate_config(options.delimiter, options.profile, 'delimiter', default=' ')    
    options.blacklist = open(interpolate_config(options.blacklist, 
                        options.profile, 'blacklist'), "r")
    options.parser = interpolate_config(options.parser, options.profile, 'parser', 
                                        default=False) 
    options.reverse = interpolate_config(options.reverse, 
                        options.profile, 'reverse', default=False, type=bool)
    options.ignorecase = interpolate_config(options.ignorecase, 
                        options.profile, 'ignorecase', default=False, type=bool)
    options.word_boundaries = interpolate_config(options.word_boundaries, 
                        options.profile, 'word_boundaries', default=False, type=bool)        
    options.with_acora = interpolate_config(options.with_acora, 
                        options.profile, 'with_acora', default=False, type=bool)    
    options.printlines = interpolate_config(options.printlines, 
                        options.profile, 'print', default=False, type=bool)     
    
    if options.parser and not options.field:
        parser.error("Must supply --field parameter when using parser-based matching.")

    return AttrDict(options.__dict__), args

def logfilter(fh, blacklist, field, parser=None, reverse=False, 
              delimiter=None, ignorecase=False, with_acora=False, 
              word_boundaries=False, **kwargs):
    """Filter rows from a log stream using a blacklist"""
    
    blacklist = dict.fromkeys([l.strip() for l \
                               in blacklist \
                               if l and not l.startswith('#')])
    re_flags = 0
    
    if ignorecase:
        re_flags = re.IGNORECASE
        
    _is_blacklisted=None
    if with_acora is False:
        # Regular expression based matching
        if word_boundaries:
            _is_blacklisted = partial(_is_blacklisted_re_wb, 
                delimiter=delimiter, field=field, blacklist=blacklist, re_flags=re_flags)
        else:
            _is_blacklisted = partial(_is_blacklisted_re, 
                delimiter=delimiter, field=field, blacklist=blacklist, re_flags=re_flags)                        
    else:
        # Aho-Corasick multiple string pattern matching
        # using the acora Cython library
        builder = acora.AcoraBuilder(*blacklist)
        ac = builder.build()
        _transform_func = lambda x: x
        if ignorecase:
            _transform_func = lambda x: x.lower()
        
        if word_boundaries:
            _is_blacklisted = partial(_is_blacklisted_ac_wb, 
                delimiter=delimiter, field=field, transform_func=_transform_func, ac=ac)
        else:
            _is_blacklisted = partial(_is_blacklisted_ac, 
                delimiter=delimiter, field=field, transform_func=_transform_func, ac=ac)                        
                
    _is_blacklisted_func = _is_blacklisted
    if parser:
        # Custom parser specified, use field-based matching
        parser = eval(parser, vars(logtools.parsers), {})()
        fields = field.split(',')
        is_indices = reduce(and_, (k.isdigit() for k in fields), True)
        if is_indices:
            # Field index based matching
            def _is_blacklisted_func(line):
                parsed_line = parser(line)
                for field in fields:
                    if _is_blacklisted(parsed_line.by_index(field)):
                        return True
                return False
        else:
            # Named field based matching
            def _is_blacklisted_func(line):
                parsed_line = parser(line)
                for field in fields:
                    if _is_blacklisted(parsed_line.by_index(field)):
                        return True
                return False            
            
    num_lines=0
    num_filtered=0
    num_nomatch=0
    for line in imap(lambda x: x.strip(), fh):
        try:
            is_blacklisted = _is_blacklisted_func(line)
        except (KeyError, ValueError):
            # Parsing error
            logging.warn("No match for line: %s", line)
            num_nomatch +=1
            continue
        else:
            if is_blacklisted ^ reverse:
                logging.debug("Filtering line: %s", line)
                num_filtered+=1
                continue

            num_lines+=1
            yield line

    logging.info("Number of lines after filtering: %s", num_lines)
    logging.info("Number of lines filtered: %s", num_filtered)        
    if num_nomatch:
        logging.info("Number of lines could not match on: %s", num_nomatch)

    return

def logfilter_main():
    """Console entry-point"""
    options, args = logfilter_parse_args()
    if options.printlines:
        for line in logfilter(fh=sys.stdin, *args, **options):
            print line
    else:
        for line in logfilter(fh=sys.stdin, *args, **options): 
            pass

    return 0


########NEW FILE########
__FILENAME__ = _filterbots
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._filterbots
Filter bots from logrows based on an ip/host and useragent blacklists.
"""
import re
import sys
import logging
from itertools import imap
from functools import partial
from operator import and_
from optparse import OptionParser

from _config import logtools_config, interpolate_config, AttrDict
import logtools.parsers

__all__ = ['filterbots_parse_args', 'filterbots', 
           'filterbots_main', 'parse_bots_ua', 'is_bot_ua']

def filterbots_parse_args():
    usage = "%prog " \
          "-u <useragents_blacklist_file> " \
          "-i <ips_blacklist_file> " \
          "-r <ip_useragent_regexp>"
    parser = OptionParser(usage=usage)

    parser.add_option("-u", "--bots-ua", dest="bots_ua", default=None, 
                      help="Bots useragents blacklist file")
    parser.add_option("-i", "--bots-ips", dest="bots_ips", default=None, 
                      help="Bots ips blacklist file")
    parser.add_option("-r", "--ip-ua-re", dest="ip_ua_re", default=None, 
                      help="Regular expression to match IP/useragent fields." \
                      "Should have an 'ip' and 'ua' named groups")
    parser.add_option("-p", "--print", dest="printlines", action="store_true",
                      help="Print non-filtered lines")
    parser.add_option("-t", "--pattern", dest="pattern", action="store_true",
                      help="Use pattern analysis to filter bots (See documentation for details)")    
    parser.add_option("-R", "--reverse", dest="reverse", action="store_true",
                      help="Reverse filtering")
    parser.add_option("--parser", dest="parser",
                      help="Feed logs through a parser. Useful when reading encoded/escaped formats (e.g JSON) and when " \
                      "selecting parsed fields rather than matching via regular expression.")
    parser.add_option("-f", "--ip-ua-fields", dest="ip_ua_fields",
                      help="Field(s) Selector for filtering bots when using a parser (--parser). Format should be " \
                      " 'ua:<ua_field_name>,ip:<ip_field_name>'. If one of these is missing, it will not be used for filtering.")

    parser.add_option("-P", "--profile", dest="profile", default='filterbots',
                      help="Configuration profile (section in configuration file)")

    options, args = parser.parse_args()

    # Interpolate from configuration and open filehandle
    options.bots_ua  = open(interpolate_config(options.bots_ua, 
                                               options.profile, 'bots_ua'), "r")
    options.bots_ips = open(interpolate_config(options.bots_ips, 
                                               options.profile, 'bots_ips'), "r")
    options.ip_ua_re = interpolate_config(options.ip_ua_re, 
                                           options.profile, 'ip_ua_re', default=False)  
    options.parser = interpolate_config(options.parser, options.profile, 'parser', 
                                        default=False) 
    #options.format = interpolate_config(options.format, options.profile, 'format', 
    #                                    default=False) 
    options.ip_ua_fields = interpolate_config(options.ip_ua_fields, options.profile, 'ip_ua_fields', 
                                       default=False)      
    options.pattern = interpolate_config(options.pattern, 
                                           options.profile, 'pattern', default=False, type=bool)    
    options.reverse = interpolate_config(options.reverse, 
                                           options.profile, 'reverse', default=False, type=bool)
    options.printlines = interpolate_config(options.printlines, 
                                             options.profile, 'print', default=False, type=bool) 
    
    if options.parser and not options.ip_ua_fields:
        parser.error("Must supply --ip-ua-fields parameter when using parser-based matching.")

    return AttrDict(options.__dict__), args

def parse_bots_ua(bots_ua):
    """Parse the bots useragents blacklist
    and produce a dictionary for exact match
    and set of regular expressions if any"""
    bots_ua_dict = {}
    bots_ua_prefix_dict = {}
    bots_ua_suffix_dict = {}
    bots_ua_re   = []

    for line in imap(lambda x: x.strip(), bots_ua):
        if line.startswith("#"):
            # Comment line
            continue
        if line.startswith("r'"):
            # Regular expression
            bots_ua_re.append(re.compile(eval(line, {}, {})))
        elif line.startswith("p'"):
            bots_ua_prefix_dict[line[2:-1]] = True
        elif line.startswith("s'"):
            bots_ua_suffix_dict[line[2:-1]] = True
        else:
            # Exact match
            bots_ua_dict[line] = True

    return bots_ua_dict, bots_ua_prefix_dict, \
           bots_ua_suffix_dict, bots_ua_re


def is_bot_ua(useragent, bots_ua_dict, bots_ua_prefix_dict, bots_ua_suffix_dict, bots_ua_re):
    """Check if user-agent string is blacklisted as a bot, using
    given blacklist dictionaries for exact match, prefix, suffix, and regexp matches"""
    if not useragent:
        return False

    if useragent in bots_ua_dict:
        # Exact match hit for host or useragent
        return True
    else:
        # Try prefix matching on user agent
        for prefix in bots_ua_prefix_dict:
            if useragent.startswith(prefix):
                return True
        else:
            # Try suffix matching on user agent
            for suffix in bots_ua_suffix_dict:
                if useragent.endswith(suffix):
                    return True
            else:
                # Try Regular expression matching on user agent
                for ua_re in bots_ua_re:
                    if ua_re.match(useragent):
                        return True
    return False

def filterbots(fh, ip_ua_re, bots_ua, bots_ips, 
               parser=None, format=None, ip_ua_fields=None, 
               reverse=False, debug=False, **kwargs):
    """Filter bots from a log stream using
    ip/useragent blacklists"""
    bots_ua_dict, bots_ua_prefix_dict, bots_ua_suffix_dict, bots_ua_re = \
                parse_bots_ua(bots_ua)
    bots_ips = dict.fromkeys([l.strip() for l in bots_ips \
                              if not l.startswith("#")])
    is_bot_ua_func = partial(is_bot_ua, bots_ua_dict=bots_ua_dict, 
                         bots_ua_prefix_dict=bots_ua_prefix_dict, 
                         bots_ua_suffix_dict=bots_ua_suffix_dict, 
                         bots_ua_re=bots_ua_re)    
    
    _is_bot_func=None    
    if not parser:
        # Regular expression-based matching
        ua_ip_re = re.compile(ip_ua_re)
        
        def _is_bot_func(line):
            match = ua_ip_re.match(line)
            if not match:
                raise ValueError("No match for line: %s" % line)
            logging.debug("Regular expression matched line: %s", match)
    
            matchgroups = match.groupdict()
            is_bot = False
    
            ua = matchgroups.get('ua', None)
            is_bot = is_bot_ua_func(ua)        
    
            if not is_bot and matchgroups.get('ip', None) in bots_ips:
                # IP Is blacklisted
                is_bot = True
                
            return is_bot
                
    else:
        # Custom parser specified, use field-based matching
        parser = eval(parser, vars(logtools.parsers), {})()
        try:
            fields_map = dict([tuple(k.split(':')) for k in ip_ua_fields.split(',')])
        except ValueError:
            raise ValueError("Invalid format for --field parameter. Use --help for usage instructions.")
        is_indices = reduce(and_, (k.isdigit() for k in fields_map.values()), True)
        if is_indices:
            # Field index based matching
            def _is_bot_func(line):
                parsed_line = parser(line)
                is_bot = False
                if 'ua' in fields_map and parsed_line:
                    is_bot = is_bot_ua_func(parsed_line.by_index(fields_map['ua']))
                if not is_bot and 'ip' in fields_map:
                    is_bot = parsed_line.by_index(fields_map['ip']) in bots_ips
                return is_bot
        else:
            # Named field based matching
            def _is_bot_func(line):
                parsed_line = parser(line)
                is_bot = False
                if 'ua' in fields_map and parsed_line:
                    is_bot = is_bot_ua_func(parsed_line[fields_map['ua']])
                if not is_bot and 'ip' in fields_map:
                    is_bot = parsed_line[fields_map['ip']] in bots_ips
                return is_bot            
        
    num_lines=0
    num_filtered=0
    num_nomatch=0
    for line in imap(lambda x: x.strip(), fh):
        try:
            is_bot = _is_bot_func(line)
        except (KeyError, ValueError):
            # Parsing error
            logging.warn("No match for line: %s", line)
            num_nomatch +=1
            continue

        if is_bot ^ reverse:
            logging.debug("Filtering line: %s", line)
            num_filtered+=1
            continue

        num_lines+=1
        yield line

    logging.info("Number of lines after bot filtering: %s", num_lines)
    logging.info("Number of lines (bots) filtered: %s", num_filtered)        
    if num_nomatch:
        logging.info("Number of lines could not match on: %s", num_nomatch)

    return

def filterbots_main():
    """Console entry-point"""
    options, args = filterbots_parse_args()
    if options.printlines:
        for line in filterbots(fh=sys.stdin, *args, **options):
            print line
    else:
        for line in filterbots(fh=sys.stdin, *args, **options): 
            pass

    return 0


########NEW FILE########
__FILENAME__ = _geoip
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._geoip
GeoIP interoperability tool.
Requires the GeoIP library and Python bindings
"""
import os
import re
import sys
import logging
from itertools import imap
from optparse import OptionParser

from _config import logtools_config, interpolate_config, AttrDict

__all__ = ['geoip_parse_args', 'geoip', 'geoip_main']

def geoip_parse_args():
    parser = OptionParser()
    parser.add_option("-r", "--re", dest="ip_re", default=None, 
                    help="Regular expression to lookup IP in logrow")
    parser.add_option("-f", "--filter", dest="filter", default=None, 
                    help="Country/Area Code to filter to (e.g 'United States')")    
    parser.add_option("-p", "--print", dest="printline", default=None, action="store_true",
                    help="Print original log line with the geolocation. By default we only print <country, ip>")    

    parser.add_option("-P", "--profile", dest="profile", default='geoip',
                      help="Configuration profile (section in configuration file)")
    
    options, args = parser.parse_args()
    
    # Interpolate from configuration
    options.ip_re  = interpolate_config(options.ip_re, options.profile, 'ip_re')
    options.filter = interpolate_config(options.filter, options.profile, 'filter',
                                        default=False)
    options.printline  = interpolate_config(options.printline, options.profile, 'print', 
                                        type=bool, default=False)

    return AttrDict(options.__dict__), args

def geoip(fh, ip_re, **kwargs):
    """
    extract geo-information from logline
    based on ip address and the MaxMind GeoIP
    library.
    
    Args:
      fh - File handle (as returned by open(), or StringIO)
      ip_re - Regular expression pattern to use for locating ip in line
    """
    try:
        import GeoIP
    except ImportError:
        logging.error("GeoIP Python package must be installed to use logtools geoip command")
        sys.exit(-1)

    gi = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)
    ip_re = re.compile(ip_re)

    filter_func = lambda x: True
    if 'filter' in kwargs and kwargs['filter']:
        filter_func = lambda x: \
            True if x == kwargs['filter'] else False
    
    for line in imap(lambda x: x.strip(), fh):
        match = ip_re.match(line)
        if match: 
            ip = match.group(1)
            geocode = gi.country_name_by_addr(ip)
            if geocode is None:
                logging.debug("No Geocode for IP: %s", ip)
            elif filter_func(geocode) is False:
                # Filter out
                pass
            else:
                yield geocode, ip, line

def geoip_main():
    """Console entry-point"""
    options, args = geoip_parse_args()
    for geocode, ip, line in geoip(fh=sys.stdin, *args, **options):
        if options.printline is True:
            print "{0}\t{1}".format(geocode, line)
        else:
            print "{0}\t{1}".format(geocode, ip)
    return 0

########NEW FILE########
__FILENAME__ = _join
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._join

Perform a join between log stream and
some other arbitrary source of data.
Can be used with pluggable drivers e.g
to join against database, other files etc.
"""
import re
import sys
import logging
import unicodedata
from time import time
from itertools import imap
from datetime import datetime
from optparse import OptionParser
from urlparse import parse_qs, urlsplit

from logtools.join_backends import *
from _config import logtools_config, interpolate_config, AttrDict

__all__ = ['logjoin_parse_args', 'logjoin', 'logjoin_main']

def logjoin_parse_args():
    usage = "%prog " \
          "-f <field> " \
          "-d <delimiter_character> " \
          "-t <timestamp_format_string>"
    parser = OptionParser(usage=usage)
    
    parser.add_option("-f", "--field", dest="field", type=int,
                      help="Index of field to use as field to join on")
    parser.add_option("-d", "--delimiter", dest="delimiter",
                      help="Delimiter character for field-separation")
    parser.add_option("-b", "--backend", dest="backend",  
                      help="Backend to use for joining. Currently available backends: 'sqlalchemy'")
    
    parser.add_option("-C", "--join-connect-string", dest="join_connect_string",
                      help="Connection string (e.g sqlalchemy db URI)")
    parser.add_option("-F", "--join-remote-fields", dest="join_remote_fields",
                      help="Fields to include from right join clause")        
    parser.add_option("-N", "--join-remote-name", dest="join_remote_name",
                      help="Name of resource to join to (e.g file name, table name)")        
    parser.add_option("-K", "--join-remote-key", dest="join_remote_key",
                      help="Name of remote key field to join on (e.g table field, file column index)")        
    
    parser.add_option("-P", "--profile", dest="profile", default='qps',
                      help="Configuration profile (section in configuration file)")

    options, args = parser.parse_args()

    # Interpolate from configuration
    options.field  = interpolate_config(options.field, options.profile, 'field', type=int)
    options.delimiter = interpolate_config(options.delimiter, options.profile, 'delimiter', default=' ')
    options.backend = interpolate_config(options.backend, options.profile, 'backend')
    
    options.join_connect_string = interpolate_config(options.join_connect_string, options.profile, 'join_connect_string')
    options.join_remote_fields = interpolate_config(options.join_remote_fields, options.profile, 'join_remote_fields')
    options.join_remote_name = interpolate_config(options.join_remote_name, options.profile, 'join_remote_name')
    options.join_remote_key = interpolate_config(options.join_remote_key, options.profile, 'join_remote_key')

    return AttrDict(options.__dict__), args


def logjoin(fh, field, delimiter, backend, join_connect_string, 
            join_remote_fields, join_remote_name, join_remote_key, **kwargs):
    """Perform a join"""
    
    field = field-1
    delimiter = unicode(delimiter)
    
    backend_impl = {
        "sqlalchemy": SQLAlchemyJoinBackend
    }[backend](remote_fields=join_remote_fields, remote_name=join_remote_name, 
                       remote_key=join_remote_key, connect_string=join_connect_string)
    
    for row in imap(lambda x: x.strip(), fh):
        key = row.split(delimiter)[field]
        for join_row in backend_impl.join(key):
            yield key, unicode(row) + delimiter + delimiter.join(imap(unicode, join_row))

def logjoin_main():
    """Console entry-point"""
    options, args = logjoin_parse_args()
    for key, row in logjoin(fh=sys.stdin, *args, **options):
        print >> sys.stdout, unicodedata.normalize('NFKD', unicode(row))\
              .encode('ascii','ignore')

    return 0

########NEW FILE########
__FILENAME__ = _merge
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._merge
Logfile merging utilities.
These typically help in streaming multiple 
individually sorted input logfiles through, outputting them in
combined sorted order (typically by date field)
"""
import os
import re
import sys
import logging
from itertools import imap
from datetime import datetime
from optparse import OptionParser
from heapq import heappush, heappop, merge

from _config import logtools_config, interpolate_config, AttrDict
import logtools.parsers

__all__ = ['logmerge_parse_args', 'logmerge', 'logmerge_main']


def logmerge_parse_args():
    usage = "%prog -f <field> -d <delimiter> filename1 filename2 ..."
    parser = OptionParser(usage=usage)
    
    parser.add_option("-f", "--field", dest="field", default=None,
                    help="Field index to use as key for sorting by (1-based)")
    parser.add_option("-d", "--delimiter", dest="delimiter", default=None, 
                    help="Delimiter character for fields in logfile")
    parser.add_option("-n", "--numeric", dest="numeric", default=None, action="store_true",
                    help="Parse key field value as numeric and sort accordingly")
    parser.add_option("-t", "--datetime", dest="datetime", default=None, action="store_true",
                    help="Parse key field value as a date/time timestamp and sort accordingly")
    parser.add_option("-F", "--dateformat", dest="dateformat",
                      help="Format string for parsing date-time field (used with --datetime)")        
    parser.add_option("-p", "--parser", dest="parser", default=None, 
                    help="Log format parser (e.g 'CommonLogFormat'). See documentation for available parsers.")
    
    parser.add_option("-P", "--profile", dest="profile", default='logmerge',
                      help="Configuration profile (section in configuration file)")
    
    options, args = parser.parse_args()
    
    # Interpolate from configuration
    options.field = interpolate_config(options.field, 
                                    options.profile, 'field')
    options.delimiter = interpolate_config(options.delimiter, 
                                    options.profile, 'delimiter', default=' ')
    options.numeric = interpolate_config(options.numeric, options.profile, 
                                    'numeric', default=False, type=bool) 
    options.datetime = interpolate_config(options.datetime, options.profile, 
                                    'datetime', default=False, type=bool)     
    options.dateformat = interpolate_config(options.dateformat, 
                                    options.profile, 'dateformat', default=False)    
    options.parser = interpolate_config(options.parser, 
                                    options.profile, 'parser', default=False)    

    return AttrDict(options.__dict__), args

def logmerge(options, args):
    """Perform merge on multiple input logfiles
    and emit in sorted order using a priority queue"""
    
    delimiter = options.delimiter
    field = options.field

    key_func = None
    if options.get('parser', None):
        # Use a parser to extract field to merge/sort by
        parser = eval(options.parser, vars(logtools.parsers), {})()
        if field.isdigit():            
            extract_func = lambda x: parser(x.strip()).by_index(int(field)-1)
        else:
            extract_func = lambda x: parser(x.strip())[field]
    else:
        # No parser given, use indexed field based extraction
        extract_func = lambda x: x.strip().split(delimiter)[int(field)-1]
        
    if options.get('numeric', None):
        key_func = lambda x: (int(extract_func(x)), x)
    elif options.get('datetime', None):
        key_func = lambda x: (datetime.strptime(extract_func(x), \
                                    options.dateformat), x)            
    else:
        key_func = lambda x: (extract_func(x), x)
        
    iters = (imap(key_func, open(filename, "r")) for filename in args)
    
    for k, line in merge(*iters):
        yield k, line.strip()
    
def logmerge_main():
    """Console entry-point"""
    options, args = logmerge_parse_args()
    for key, line in logmerge(options, args):
        print line
    return 0

########NEW FILE########
__FILENAME__ = _parse
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._parse
Log format parsing programmatic and command-line utilities.
uses the logtools.parsers module
"""
import os
import re
import sys
import logging
from itertools import imap
from operator import and_
from optparse import OptionParser

import logtools.parsers
from _config import logtools_config, interpolate_config, AttrDict

__all__ = ['logparse_parse_args', 'logparse', 'logparse_main']


def logparse_parse_args():
    parser = OptionParser()
    parser.add_option("-p", "--parser", dest="parser", default=None, 
                    help="Log format parser (e.g 'CommonLogFormat'). See documentation for available parsers.")
    parser.add_option("-F", "--format", dest="format", default=None, 
                    help="Format string. Used by the parser (e.g AccessLog format specifier)")    
    parser.add_option("-f", "--field", dest="field", default=None,
                    help="Parsed Field index to output")    
    parser.add_option("-i", "--ignore", dest="ignore", default=None, action="store_true",
                    help="Ignore missing fields errors (skip lines with missing fields)")    
    parser.add_option("-H", "--header", dest="header", default=None, action="store_true",
                    help="Prepend a header describing the selected fields to output.")    
    
    parser.add_option("-P", "--profile", dest="profile", default='logparse',
                      help="Configuration profile (section in configuration file)")
    
    options, args = parser.parse_args()
    
    # Interpolate from configuration
    options.parser = interpolate_config(options.parser, options.profile, 'parser') 
    options.format = interpolate_config(options.format, options.profile, 'format', 
                                        default=False) 
    options.field = interpolate_config(options.field, options.profile, 'field')
    options.ignore = interpolate_config(options.ignore, options.profile, 'ignore', 
                                        default=False, type=bool)
    options.header = interpolate_config(options.header, options.profile, 'header', 
                                        default=False, type=bool)    

    return AttrDict(options.__dict__), args

def logparse(options, args, fh):
    """Parse given input stream using given
    parser class and emit specified field(s)"""

    field = options.field
    
    parser = eval(options.parser, vars(logtools.parsers), {})()
    if options.get('format', None):
        parser.set_format(options.format)
        
    keyfunc = None
    keys = None
    if isinstance(options.field, int) or \
       (isinstance(options.field, basestring) and options.field.isdigit()):
        # Field given as integer (index)
        field = int(options.field) - 1
        key_func = lambda x: parser(x.strip()).by_index(field, raw=True)
        keys = [options.field]
    else:
        # Field given as string
        
        # Check how many fields are requested        
        keys = options.field.split(",")
        L = len(keys)
        if L == 1:
            key_func = lambda x: parser(x.strip())[field]
        else:
            # Multiple fields requested
            is_indices = reduce(and_, (k.isdigit() for k in keys), True)
            key_func = logtools.parsers.multikey_getter_gen(parser, keys, 
                                        is_indices=is_indices)
    
    if options.header is True:
        yield '\t'.join(keys)
        
    for line in fh:
        try:
            yield key_func(line)
        except KeyError, exc:
            # Could not find user-specified field
            logging.warn("Could not match user-specified fields: %s", exc)
        except ValueError, exc:
            # Could not parse the log line
            if options.ignore:
                logging.debug("Could not match fields for parsed line: %s", line)
                continue
            else:
                logging.error("Could not match fields for parsed line: %s", line)
                raise
    
def logparse_main():
    """Console entry-point"""
    options, args = logparse_parse_args()
    for row in logparse(options, args, fh=sys.stdin):
        if row:
            print row.encode('ascii', 'ignore')
    return 0

########NEW FILE########
__FILENAME__ = _plot
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._plot
Plotting methods for logfiles
"""

import os
import re
import sys
import locale
import logging
import unicodedata
from itertools import imap
from random import randint
from datetime import datetime
from operator import itemgetter
from optparse import OptionParser
from abc import ABCMeta, abstractmethod

from _config import logtools_config, interpolate_config, AttrDict

__all__ = ['logplot_parse_args', 'logplot', 'logplot_main']

locale.setlocale(locale.LC_ALL, "")

class PlotBackend(object):
    __metaclass__ = ABCMeta
    
    @abstractmethod
    def plot(self, options, args, fh):
        """Plot using backend implementation"""
        
class GChartBackend(PlotBackend):
    """Google Chart API plotting backend.
    uses the pygooglechart python package"""
    
    def __init__(self):
        PlotBackend.__init__(self)
        
    def plot(self, options, args, fh):
        """Plot using google charts api"""
        try:
            import pygooglechart
        except ImportError:
            logging.error("pygooglechart Python package must be installed to use the 'gchart' backend")
            sys.exit(-1)

        try:
            chart = {
                'pie': self._plot_pie,
                'line': self._plot_line,
                'timeseries': self._plot_timeseries
            }[options.type](options, args, fh)
        except KeyError:
            raise KeyError("Invalid plot type: '%s'" % options.type)
        else:
            if options.get('title', None):
                chart.set_title(options.title)
            if options.get('output', None):
                chart.download(options.output)
                
            return chart

    def _plot_line(self, options, args, fh):
        """Plot a line chart"""
        from pygooglechart import Chart, SimpleLineChart, Axis
        
        delimiter = options.delimiter
        field = options.field-1
        
        pts = []
        for l in imap(lambda x: x.strip(), fh):
            splitted_line = l.split(delimiter)
            k = float(splitted_line.pop(field))
            pts.append((k, ' '.join(splitted_line)))
        
        if options.get('limit', None):
            # Only wanna use top N samples by key, sort and truncate
            pts = sorted(pts, key=itemgetter(0), reverse=True)[:options.limit]
                      
        if not pts:
            raise ValueError("No data to plot")
                        
        max_y = int(max((v for v, label in pts)))
        chart = SimpleLineChart(options.width, options.height,y_range=[0, max_y])
        
        # Styling
        chart.set_colours(['0000FF'])
        chart.fill_linear_stripes(Chart.CHART, 0, 'CCCCCC', 0.2, 'FFFFFF', 0.2)        
        chart.set_grid(0, 25, 5, 5)
        
        data, labels = zip(*pts)
        chart.add_data(data)
        
        # Axis labels
        chart.set_axis_labels(Axis.BOTTOM, labels)
        left_axis = range(0, max_y + 1, 25)
        left_axis[0] = ''
        chart.set_axis_labels(Axis.LEFT, left_axis)
        
        return chart
        
    def _plot_pie(self, options, args, fh):
        """Plot a pie chart"""
        from pygooglechart import PieChart3D, PieChart2D

        delimiter = options.delimiter
        field = options.field-1
                
        chart = PieChart2D(options.width, options.height)
        pts = []
        for l in imap(lambda x: x.strip(), fh):
            splitted_line = l.split(delimiter)
            k = int(splitted_line.pop(field))
            pts.append((k, ' '.join(splitted_line), locale.format('%d', k, True)))
            
        if options.get('limit', None):
            # Only wanna use top N samples by key, sort and truncate
            pts = sorted(pts, key=itemgetter(0), reverse=True)[:options.limit]
            
        if not pts:
            raise ValueError("No data to plot")
        
        data, labels, legend = zip(*pts)
        chart.add_data(data)
        chart.set_pie_labels(labels)
        if options.get('legend', None) is True:
            chart.set_legend(map(str, legend))
                        
        return chart
    
    def _plot_timeseries(self, options, args, fh):
        """Plot a timeseries graph"""
        from pygooglechart import Chart, SimpleLineChart, Axis
        
        delimiter = options.delimiter
        field = options.field-1
        datefield = options.datefield-1
        
        pts = []
        for l in imap(lambda x: x.strip(), fh):
            splitted_line = l.split(delimiter)
            v = float(splitted_line[field])
            t = datetime.strptime(splitted_line[datefield], options.dateformat)
            pts.append((t, v))
        
        if options.get('limit', None):
            # Only wanna use top (earliest) N samples by key, sort and truncate
            pts = sorted(pts, key=itemgetter(0), reverse=True)[:options.limit]
                      
        if not pts:
            raise ValueError("No data to plot")
                        
        max_y = int(max((v for t, v in pts)))
        chart = SimpleLineChart(options.width, options.height,y_range=[0, max_y])
        
        # Styling
        chart.set_colours(['0000FF'])
        chart.fill_linear_stripes(Chart.CHART, 0, 'CCCCCC', 0.2, 'FFFFFF', 0.2)        
        chart.set_grid(0, 25, 5, 5)
        
        ts, vals = zip(*pts)
        chart.add_data(vals)
        
        # Axis labels
        chart.set_axis_labels(Axis.BOTTOM, ts)
        left_axis = range(0, max_y + 1, 25)
        left_axis[0] = ''
        chart.set_axis_labels(Axis.LEFT, left_axis)
        
        return chart        

        
class MatplotlibBackend(PlotBackend):
    """Use matplotlib (pylab) for rendering plots"""
    
    def __init__(self):
        PlotBackend.__init__(self)
        
    def plot(self, options, args, fh):
        """Plot using google charts api"""
        try:
            import pylab
        except ImportError:
            logging.error("matplotlib Python package must be installed to use the 'matplotlib' backend")
            sys.exit(-1)
            
        try:
            chart = {
                'hist': self._plot_hist,
                'pie': self._plot_pie,
                'line': self._plot_line,
                'timeseries': self._plot_timeseries
            }[options.type](options, args, fh)
        except KeyError:
            raise KeyError("Invalid plot type: '%s'" % options.type)
        else:
            if options.get('title', None):
                chart.get_axes()[0].set_title(options.title)
            if options.get('output', None):
                chart.savefig(options.output)
                
            return chart 
      
    def _plot_hist(self, options, args, fh):
        """Plot a histogram"""
        import pylab
        
        delimiter = options.delimiter
        field = options.field-1
         
        pts = []
        max_y = -float("inf")
        for l in imap(lambda x: x.strip(), fh):
            splitted_line = l.split(delimiter)
            k = float(splitted_line.pop(field))
            pts.append((k, ' '.join(splitted_line)))
            if k > max_y:
                max_y = k
        
        if options.get('limit', None):
            # Only wanna use top N samples by key, sort and truncate
            pts = sorted(pts, key=itemgetter(0), reverse=True)[:options.limit]
                      
        if not pts:
            raise ValueError("No data to plot")
        
        data, labels = zip(*pts)        
        normed = False
        bins = len(data)/100.
        
        f = pylab.figure()
        pylab.hist(data, bins=bins, normed=normed)
                
        return f
    
    
    def _plot_pie(self, options, args, fh):
        """Plot pie chart"""
        from pylab import figure, pie, legend
        import matplotlib as mpl
        mpl.rc('font', size=8)

        delimiter = options.delimiter
        field = options.field-1
                
        pts = []
        ttl = 0.
        for l in imap(lambda x: x.strip(), fh):
            splitted_line = l.split(delimiter)
            k = float(splitted_line.pop(field))
            ttl += k
            pts.append((k, ' '.join(splitted_line), locale.format('%d', k, True)))
        
        
        if options.get('limit', None):
            # Only wanna use top N samples by key, sort and truncate
            pts = sorted(pts, key=itemgetter(0), reverse=True)[:options.limit]
            
        if not pts or ttl==0:
            raise ValueError("No data to plot")
        
        data, labels, _legend = zip(*pts)
        data = list(data)
        # Normalize
        for idx, pt in enumerate(data):
            data[idx] /= ttl
        
        f = figure()
        pie(data, labels=labels, autopct='%1.1f%%', shadow=True)
        if options.get('legend', None) is True:        
            legend(_legend, loc=3)
        
        return f
        
    def _plot_line(self, options, args, fh):
        """Line plot using matplotlib"""
        import pylab
        
        delimiter = options.delimiter
        field = options.field-1
         
        pts = []
        max_y = -float("inf")
        for l in imap(lambda x: x.strip(), fh):
            splitted_line = l.split(delimiter)
            k = float(splitted_line.pop(field))
            label = unicodedata.normalize('NFKD', \
                        unicode(' '.join(splitted_line), 'utf-8')).encode('ascii','ignore')
            pts.append((k, label))
            if k > max_y:
                max_y = k
        
        if options.get('limit', None):
            # Only wanna use top N samples by key, sort and truncate
            pts = sorted(pts, key=itemgetter(0), reverse=True)[:options.limit]
                      
        if not pts:
            raise ValueError("No data to plot")
        
        data, labels = zip(*pts)
        
        f = pylab.figure()
        pylab.plot(xrange(len(data)), data, "*--b")
        if options.get('legend', None):
            pylab.xticks(xrange(len(labels)), labels, rotation=17)
                
        return f
    
    def _plot_timeseries(self, options, args, fh):
        """Line plot using matplotlib"""
        import pylab
        import matplotlib.ticker as ticker
        
        delimiter = options.delimiter
        field = options.field-1
        datefield = options.datefield-1
        
        pts = []
        max_y = -float("inf")
        for l in imap(lambda x: x.strip(), fh):
            splitted_line = l.split(delimiter)
            v = float(splitted_line[field])
            t = datetime.strptime(splitted_line[datefield], options.dateformat)
            pts.append((t, v))
            if v > max_y:
                max_y = v
        
        if options.get('limit', None):
            # Only use top N samples by key, sort and truncate
            pts = sorted(pts, key=itemgetter(0), reverse=True)[:options.limit]
                      
        if not pts:
            raise ValueError("No data to plot")
        
        N = len(pts)
        ts, vals = zip(*pts)
        
        def format_date(x, pos=None):
            thisind = int(max(0, min(x, N)))
            return ts[thisind].strftime(options.dateformat)

        
        f = pylab.figure()
        ax = f.add_subplot(111)
        ax.plot(xrange(len(vals)), vals, "*--b")
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_date))
        f.autofmt_xdate()
                
        return f    

    
def logplot_parse_args():
    parser = OptionParser()
    parser.add_option("-b", "--backend", dest="backend",  
                      help="Backend to use for plotting. Currently available backends: 'gchart', 'matplotlib'")
    parser.add_option("-T", "--type", dest="type",  
                      help="Chart type. Available types: 'pie', 'histogram', 'line'." \
                      "Availability might differ due to backend.")    
    parser.add_option("-f", "--field", dest="field", type=int,
                      help="Index of field to use as main input for plot")
    parser.add_option("-d", "--delimiter", dest="delimiter",
                      help="Delimiter character for field-separation")
    parser.add_option("-o", "--output", dest="output", help="Output filename")    
    parser.add_option("-W", "--width", dest="width", type=int, help="Plot Width")   
    parser.add_option("-H", "--height", dest="height", type=int, help="Plot Height")       
    parser.add_option("-L", "--limit", dest="limit", type=int, 
                      help="Only plot the top N rows, sorted decreasing by key")        
    parser.add_option("-l", "--legend", dest="legend", action="store_true", 
                      help="Render Plot Legend")
    parser.add_option("-t", "--title", dest="title",
                      help="Plot Title")
    parser.add_option("--datefield", dest="datefield", type=int,
                      help="Index of field to use as date-time source (for timeseries plots)")    
    parser.add_option("--dateformat", dest="dateformat",
                      help="Format string for parsing date-time field (for timeseries plots)")    
    
    parser.add_option("-P", "--profile", dest="profile", default='logplot',
                      help="Configuration profile (section in configuration file)")
    
    options, args = parser.parse_args()

    # Interpolate from configuration
    options.backend  = interpolate_config(options.backend, options.profile, 'backend')
    options.type = interpolate_config(options.type, options.profile, 'type')
    options.field  = interpolate_config(options.field, options.profile, 'field', type=int)
    options.delimiter = interpolate_config(options.delimiter, options.profile, 'delimiter')
    options.output = interpolate_config(options.output, options.profile, 'output', default=False)
    options.width = interpolate_config(options.width, options.profile, 'width', type=int)
    options.height = interpolate_config(options.height, options.profile, 'height', type=int)    
    options.limit = interpolate_config(options.limit, options.profile, 'limit', type=int, default=False) 
    options.legend = interpolate_config(options.legend, options.profile, 'legend', type=bool, default=False) 
    options.title = interpolate_config(options.title, options.profile, 'title', default=False)
    options.datefield = interpolate_config(options.datefield, options.profile, 'datefield', type=int, default=False)
    options.dateformat = interpolate_config(options.dateformat, options.profile, 'dateformat', default=False)

    return AttrDict(options.__dict__), args

def logplot(options, args, fh):
    """Plot some index defined over the logstream,
    using user-specified backend"""            
    return {
        "gchart":  GChartBackend(),
        "matplotlib": MatplotlibBackend()
    }[options.backend].plot(options, args, fh)

def logplot_main():
    """Console entry-point"""
    options, args = logplot_parse_args()
    logplot(options, args, fh=sys.stdin)
    return 0

########NEW FILE########
__FILENAME__ = _qps
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._qps
Compute QPS estimates based on parsing of timestamps from logs on
sliding time windows.
"""
import re
import sys
import logging
from time import time
from itertools import imap
from datetime import datetime
from optparse import OptionParser

from _config import logtools_config, interpolate_config, AttrDict

__all__ = ['qps_parse_args', 'qps', 'qps_main']

def qps_parse_args():
    usage = "%prog " \
          "-r <datetime_regexp_mask> " \
          "-F <timestamp_format_string> " \
          "-W <sliding_window_interval_seconds>" \
          "-i <ignore_missing_datefield_errors>"

    parser = OptionParser(usage=usage)
    
    parser.add_option("-r", "--re", dest="dt_re", default=None, 
                    help="Regular expression to lookup datetime in logrow")
    parser.add_option("-F", "--dateformat", dest="dateformat",
                      help="Format string for parsing date-time field (used with --datetime)")        
    parser.add_option("-W", '--window-size', dest="window_size", type=int, default=None, 
                      help="Sliding window interval (in seconds)")
    parser.add_option("-i", "--ignore", dest="ignore", default=None, action="store_true",
                    help="Ignore missing datefield errors (skip lines with missing/unparse-able datefield)")      

    parser.add_option("-P", "--profile", dest="profile", default='qps',
                      help="Configuration profile (section in configuration file)")

    options, args = parser.parse_args()

    # Interpolate from configuration and open filehandle
    options.dt_re  = interpolate_config(options.dt_re, options.profile, 're')    
    options.dateformat = interpolate_config(options.dateformat, 
                                            options.profile, 'dateformat', default=False)    
    options.window_size = interpolate_config(options.window_size, 
                                            options.profile, 'window_size', type=int)
    options.ignore = interpolate_config(options.ignore, options.profile, 'ignore', 
                                        default=False, type=bool)    

    return AttrDict(options.__dict__), args

def qps(fh, dt_re, dateformat, window_size, ignore, **kwargs):
    """Calculate QPS from input stream based on
    parsing of timestamps and using a sliding time window"""
    
    _re = re.compile(dt_re)
    t0=None
    samples=[]

    # Populate with first value
    while not t0:
        line = fh.readline()
        if not line:
            return
        try:
            t = datetime.strptime(_re.match(line).groups()[0], dateformat)
        except (AttributeError, KeyError, TypeError, ValueError):
            if ignore:
                logging.debug("Could not match datefield for parsed line: %s", line)
                continue
            else:
                logging.error("Could not match datefield for parsed line: %s", line)
                raise            
        else:
            t0 = t
            samples.append(t0)
    
    # Run over rest of input stream
    for line in imap(lambda x: x.strip(), fh):
        try:
            t = datetime.strptime(_re.match(line).groups()[0], dateformat)
        except (AttributeError, KeyError, TypeError, ValueError):
            if ignore:
                logging.debug("Could not match datefield for parsed line: %s", line)
                continue
            else:
                logging.error("Could not match datefield for parsed line: %s", line)
                raise            
        else:
            dt = t-t0
            if dt.seconds > window_size or dt.days:
                if samples:
                    num_samples = len(samples)
                    yield {
                        "qps": float(num_samples)/window_size,
                        "start_time": samples[0],
                        "end_time": samples[-1],
                        "num_samples": num_samples
                    }
                t0=t
                samples=[]
            samples.append(t)
            
    # Emit any remaining values
    if samples:
        num_samples = len(samples)
        yield {
            "qps": float(num_samples)/window_size,
            "start_time": samples[0],
            "end_time": samples[-1],
            "num_samples": num_samples
        }        

def qps_main():
    """Console entry-point"""
    options, args = qps_parse_args()
    for qps_info in qps(fh=sys.stdin, *args, **options):
        print >> sys.stdout, "{start_time}\t{end_time}\t{num_samples}\t{qps:.2f}".format(**qps_info)

    return 0

########NEW FILE########
__FILENAME__ = _sample
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._sample
Sampling tools for logfiles
"""

import os
import re
import sys
import logging
from itertools import imap
from random import randint, random
from optparse import OptionParser
from heapq import heappush, heappop, heapreplace

from _config import logtools_config, interpolate_config, AttrDict

__all__ = ['logsample_parse_args', 'logsample', 'logsample_weighted', 'logsample_main']

def logsample_parse_args():
    parser = OptionParser()
    parser.add_option("-n", "--num-samples", dest="num_samples", type=int, 
                      help="Number of samples to produce")
    parser.add_option("-w", "--weighted", dest="weighted", action="store_true",
                      help="Use Weighted Reservoir Sampling (needs -f and -d parameters)")
    parser.add_option("-f", "--field", dest="field", type=int,
                      help="Index of field to use as weight for weighted sampling (-w)")
    parser.add_option("-d", "--delimiter", dest="delimiter",
                      help="Delimiter character for field-separation used by weighted sampling (-w)")

    parser.add_option("-P", "--profile", dest="profile", default='logsample',
                      help="Configuration profile (section in configuration file)")
    
    options, args = parser.parse_args()

    # Interpolate from configuration
    options.num_samples  = interpolate_config(options.num_samples, 
                                options.profile, 'num_samples', type=int)
    options.weighted  = interpolate_config(options.weighted, 
                                options.profile, 'weighted', type=bool, default=False)
    options.field  = interpolate_config(options.field, options.profile, 
                                        'field', type=int, default=False)
    options.delimiter = interpolate_config(options.delimiter, options.profile, 
                                           'delimiter', default=' ')    

    return AttrDict(options.__dict__), args

def logsample(fh, num_samples, **kwargs):
    """Use a Reservoir Sampling algorithm
    to sample uniformly random lines from input stream."""
    R = []
    N = num_samples
    
    for i, k in enumerate(fh):
        if i < N:
            R.append(k)
        else:
            r = randint(0,i)
            if r < N:
                R[r] = k

    # Emit output
    for record in R:
        yield record.strip()

def logsample_weighted(fh, num_samples, field, delimiter, **kwargs):
    """Implemented Weighted Reservoir Sampling, assuming integer weights.
    See Weighted random sampling with a reservoir, Efraimidis et al."""
    
    N = num_samples
    delimiter = delimiter
    # NOTE: Convert to 0-based indexing since we expose as 1-based
    field = field-1
    
    R = []
    min_val = float("inf")
    i = 0
    
    for line in fh:
        w = int(line.split(delimiter)[field])
        if w < 1: 
            continue
        
        r = random()
        k = r ** (1./w)            
        
        if i < N:
            heappush(R, (k, line))
            if k < min_val:
                min_val = k
        else:
            if k > min_val:
                # Replace smallest item in record list
                heapreplace(R, (k, line))
        i+=1
                
    # Emit output
    for key, record in R:
        yield key, record.strip()

        
def logsample_main():
    """Console entry-point"""
    options, args = logsample_parse_args()
    
    if options.weighted is True:
        for k, r in logsample_weighted(fh=sys.stdin, *args, **options):
            print r
    else:
        for r in logsample(fh=sys.stdin, *args, **options):
            print r
        
    return 0


########NEW FILE########
__FILENAME__ = _serve
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._serve

Miniature web server for delivering real-time OLAP-style log stats.
"""

import os
import re
import sys
import logging
import wsgiref
from itertools import imap
from random import randint
from threading import Thread
from operator import itemgetter
from optparse import OptionParser
from abc import ABCMeta, abstractmethod

from _config import logtools_config, interpolate_config, AttrDict

__all__ = ['logserve_parse_args', 'logserve', 'logserve_main']

class WSGIAppThread(Thread):
    """Thread implementation used for
    the actual WSGI web server"""
    
def logserve_parse_args():
    pass

def logserve(options, args, fh):
    app_thread = WSGIAppThread()

def logserve_main():
    """Console entry-point"""
    options, args = logserve_parse_args()
    logserve(options, args, fh=sys.stdin)
    return 0

########NEW FILE########
__FILENAME__ = _sumstat
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._sumstat

Generates summary statistics
for a given logfile of the form:

<count> <value>

logfile is expected to be sorted by count
"""

import re
import sys
import locale
import logging

from time import time
from itertools import imap
from datetime import datetime
from optparse import OptionParser
from urlparse import parse_qs, urlsplit

from prettytable import PrettyTable

from _config import logtools_config, interpolate_config, AttrDict

__all__ = ['sumstat_parse_args', 'sumstat', 'sumstat_main']

locale.setlocale(locale.LC_ALL, "")

def arith_mean(values):
    """Computes the arithmetic mean of a list of numbers"""
    return sum(values, 0.0) / len(values)

def sumstat_parse_args():
    usage = "%prog -d <delimiter> [--reverse]"
    parser = OptionParser(usage=usage)
    parser.add_option("-r", "--reverse", dest="reverse", action="store_true",
                      help="Reverse ordering of entries (toggle between increasing/decreasing sort order")
    parser.add_option("-d", "--delimiter", dest="delimiter",
                      help="Delimiter character for field-separation")    

    parser.add_option("-P", "--profile", dest="profile", default='qps',
                      help="Configuration profile (section in configuration file)")

    options, args = parser.parse_args()
    
    options.delimiter = interpolate_config(options.delimiter, options.profile, 'delimiter')
    options.reverse = interpolate_config(options.reverse, options.profile, 'reverse', type=bool, default=False)

    return AttrDict(options.__dict__), args


def sumstat(fh, delimiter, reverse=False, **kwargs):
    counts = []
    N, M = 0, 0

    for line in imap(lambda x: x.strip(), fh):
        try:
            count, val = line.split(delimiter)[:2]
        except ValueError:
            logging.error("Exception while trying to parse log line: '%s', skipping", line)
        else:
            count = int(count)
            counts.append(count)
            M += 1
            N += count
            
    if reverse is True:
        logging.info("Reversing row ordering")
        counts.reverse()
    
    avg = arith_mean(counts)
    minv, maxv = min(counts), max(counts)
    
    
    # Percentiles
    percentiles_idx = [M/10, M/4, M/2, 3*M/4, 9*M/10, 95*M/100, 99*M/100, 999*M/1000]
    percentiles = map(lambda x: "%d (Idx: %s)" % \
                      (counts[x], locale.format('%d', x, True)), 
                      percentiles_idx)
    
    S10th, S25th, S40th, S50th, S75th, S90th = None, None, None, None, None, None
    accum = 0.
    for idx, c in enumerate(reversed(counts)):
        accum += c
        if not S10th and accum/N >= 0.1:
            S10th = idx+1            
        elif not S25th and accum/N >= 0.25:
            S25th = idx+1       
        elif not S40th and accum/N >= 0.4:
            S40th = idx+1                 
        elif not S50th and accum/N >= 0.5:
            S50th = idx+1
        elif not S75th and accum/N >= 0.75:
            S75th = idx+1            
        elif not S90th and accum/N >= 0.9:
            S90th = idx+1
            
    return {
        "M": M,
        "N": N,
        "avg": avg,
        "min": minv,
        "max": maxv,
        "percentiles": percentiles,
        "cover": [S10th, S25th, S40th, S50th, S75th, S90th]
        }
    

def sumstat_main():
    """Console entry-point"""
    options, args = sumstat_parse_args()
    stat_dict = sumstat(fh=sys.stdin, *args, **options)
    
    table = PrettyTable()
    table.set_field_names([
        "Num. Samples (N)",
        "Num. Values (M)",
        "Min. Value",
        "Max. Value",
        "Average Value",
        "10th Percentile",
        "25th Percentile",
        "50th Percentile",
        "75th Percentile",
        "90th Percentile",
        "95th Percentile",
        "99th Percentile",
        "99.9th Percentile"
    ])            
    table.add_row(
        map(lambda x: locale.format('%d', x, True), [stat_dict['N'], stat_dict['M']]) + \
        [stat_dict['min'], stat_dict['max'], stat_dict['avg']] + \
        stat_dict['percentiles']
    )
    table.printt()

    S10th, S25th, S40th, S50th, S75th, S90th = stat_dict['cover']
    M = stat_dict['M']
    print "10%% of Sample Volume is encompassed within the top %s (%.4f%%) sample values" % \
          (locale.format("%d", S10th, True), 100.*S10th/M)
    print "25%% of Sample Volume is encompassed within the top %s (%.4f%%) sample values" % \
          (locale.format("%d", S25th, True), 100.*S25th/M)
    print "40%% of Sample Volume is encompassed within the top %s (%.4f%%) sample values" % \
          (locale.format("%d", S40th, True), 100.*S40th/M)    
    print "50%% of Sample Volume is encompassed within the top %s (%.4f%%) sample values" % \
          (locale.format("%d", S50th, True), 100.*S50th/M)
    print "75%% of Sample Volume is encompassed within the top %s (%.4f%%) sample values" % \
          (locale.format("%d", S75th, True), 100.*S75th/M)
    print "90%% of Sample Volume is encompassed within the top %s (%.4f%%) sample values" % \
          (locale.format("%d", S90th, True), 100.*S90th/M)
    
    return 0

########NEW FILE########
__FILENAME__ = _tail
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._tail
A tail-like utility that allows tailing via time-frames and more complex
expressions.
"""
import re
import sys
import string
import logging
from itertools import imap
from functools import partial
from operator import and_
from datetime import datetime
from optparse import OptionParser

import dateutil.parser

from _config import logtools_config, interpolate_config, AttrDict
import logtools.parsers

__all__ = ['logtail_parse_args', 'logtail', 
           'logtail_main']

def _is_match_full(val, date_format, dt_start):
    """Perform filtering on line"""
    dt = datetime.strptime(val, date_format)
    if dt >= dt_start:
        return True
    return False    


def logtail_parse_args():
    usage = "%prog " \
          "--date-format <date_format>" \
          "--start-date <start_date> "

    
    parser = OptionParser(usage=usage)

    parser.add_option("--date-format", dest="date_format",
            help="Date format (Using date utility notation, e.g '%Y-%m-%d')")
    parser.add_option("--start-date", dest="start_date",
            help="Start date expression (e.g '120 minutes ago')")

    parser.add_option("--parser", dest="parser",
                      help="Feed logs through a parser. Useful when reading encoded/escaped formats (e.g JSON) and when " \
                      "selecting parsed fields rather than matching via regular expression.")
    parser.add_option("-d", "--delimiter", dest="delimiter",
                      help="Delimiter character for field-separation (when not using a --parser)")        
    parser.add_option("-f", "--field", dest="field",
                      help="Index of field to use for filtering against")
    parser.add_option("-p", "--print", dest="printlines", action="store_true",
                      help="Print non-filtered lines")    

    parser.add_option("-P", "--profile", dest="profile", default='logtail',
                      help="Configuration profile (section in configuration file)")

    options, args = parser.parse_args()

    # Interpolate from configuration and open filehandle
    options.date_format  = interpolate_config(options.date_format, options.profile, 'date_format')
    options.start_date  = interpolate_config(options.start_date, options.profile, 'start_date')
    options.field  = interpolate_config(options.field, options.profile, 'field')
    options.delimiter = interpolate_config(options.delimiter, options.profile, 'delimiter', default=' ')    
    options.parser = interpolate_config(options.parser, options.profile, 'parser', 
                                        default=False) 
    options.printlines = interpolate_config(options.printlines, 
                        options.profile, 'print', default=False, type=bool)     
    
    if options.parser and not options.field:
        parser.error("Must supply --field parameter when using parser-based matching.")

    return AttrDict(options.__dict__), args

def logtail(fh, date_format, start_date, field, parser=None, delimiter=None,
            **kwargs):
    """Tail rows from logfile, based on complex expressions such as a
    date range."""
            
    dt_start = dateutil.parser.parse(start_date)
    _is_match = partial(_is_match_full, date_format=date_format, dt_start=dt_start)
   
    _is_match_func = _is_match
    if parser:
        # Custom parser specified, use field-based matching
        parser = eval(parser, vars(logtools.parsers), {})()
        is_indices = field.isdigit()
        if is_indices:
            # Field index based matching
            def _is_match_func(line):
                parsed_line = parser(line)
                return _is_match(parsed_line.by_index(field))
        else:
            # Named field based matching
            def _is_match_func(line):
                parsed_line = parser(line)
                return _is_match(parsed_line.by_index(field))
    else:
        # No custom parser, field/delimiter-based extraction
        def _is_match_func(line):
            val = line.split(delimiter)[int(field)-1]
            return _is_match(val)
                
    num_lines=0
    num_filtered=0
    num_nomatch=0
    for line in imap(lambda x: x.strip(), fh):
        try:
             is_match = _is_match_func(line)
        except (KeyError, ValueError):
            # Parsing error
            logging.warn("No match for line: %s", line)
            num_nomatch +=1
            continue
        else:
            if not is_match:
                logging.debug("Filtering line: %s", line)
                num_filtered += 1
                continue

            num_lines+=1
            yield line

    logging.info("Number of lines after filtering: %s", num_lines)
    logging.info("Number of lines filtered: %s", num_filtered)        
    if num_nomatch:
        logging.info("Number of lines could not match on: %s", num_nomatch)

    return

def logtail_main():
    """Console entry-point"""
    options, args = logtail_parse_args()
    if options.printlines:
        for line in logtail(fh=sys.stdin, *args, **options):
            print line
    else:
        for line in logtail(fh=sys.stdin, *args, **options): 
            pass

    return 0


########NEW FILE########
__FILENAME__ = _urlparse
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License"); 
#  you may not use this file except in compliance with the License. 
#  You may obtain a copy of the License at 
#  
#      http://www.apache.org/licenses/LICENSE-2.0 
#     
#  Unless required by applicable law or agreed to in writing, software 
#  distributed under the License is distributed on an "AS IS" BASIS, 
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
#  See the License for the specific language governing permissions and 
#  limitations under the License. 
"""
logtools._urlparse

Parses URLs, Decodes query parameters,
and allows some selection on URL parts.
"""
import re
import sys
import logging
from time import time
from itertools import imap
from datetime import datetime
from urllib import unquote_plus
from optparse import OptionParser
from urlparse import parse_qs, urlsplit

from _config import logtools_config, interpolate_config, AttrDict

__all__ = ['urlparse_parse_args', 'urlparse', 'urlparse_main']

def urlparse_parse_args():
    usage = "%prog -p <url_part>"
    parser = OptionParser(usage=usage)
    
    parser.add_option("-p", "--part", dest="part", default=None, 
                    help="Part of URL to print out. Valid values: scheme, domain, netloc, path, query")
    parser.add_option("-q", "--query-params", dest="query_params", default=None,
                      help="Query parameters to print. Used in conjunction with '-p query'. Can specify multiple ones seperated by comma")
    parser.add_option("-d", "--decode", dest="decode", action="store_true",
                      help="Decode mode - Unquote input text, translating %xx characters and '+' into spaces")

    parser.add_option("-P", "--profile", dest="profile", default='qps',
                      help="Configuration profile (section in configuration file)")

    options, args = parser.parse_args()

    if not options.decode and not options.part:
        parser.error("Must supply -p (part) when not working in decode (-d) mode. See --help for usage instructions.")
        
    # Interpolate from configuration and open filehandle
    options.part  = interpolate_config(options.part, options.profile, 'part', default=False)    
    options.query_params = interpolate_config(options.query_params, options.profile, 'query_params', default=False)  
    options.decode = interpolate_config(options.decode, options.profile, 'decode', default=False) 

    return AttrDict(options.__dict__), args

def urlparse(fh, part=None, query_params=None, decode=False, **kwargs):
    """URLParse"""
    
    _yield_func = lambda x: x
    if query_params and part == 'query':
        if query_params.find(',') == -1:
            _yield_func = lambda x: val.get(query_params, (None,))[0]
        else:
            # Multiple query params specified on command line
            query_params = query_params.split(",")
            _yield_func = lambda x: \
                    [val.get(p, (None,))[0] for p in query_params]
    
    if decode is True:
        for line in imap(lambda x: x.strip(), fh):
            yield unquote_plus(line)
    else:
        for line in imap(lambda x: x.strip(), fh):
            url = urlsplit(line)
            val = {
                "scheme": url.scheme,
                "domain": url.netloc,
                "netloc": url.netloc,
                "path":   url.path,
                "query":  parse_qs(url.query)
            }[part]
            
            yield _yield_func(val)


def urlparse_main():
    """Console entry-point"""
    options, args = urlparse_parse_args()
    for parsed_url in urlparse(fh=sys.stdin, *args, **options):
        if parsed_url:
            if hasattr(parsed_url, '__iter__'):
                # Format as tab-delimited for output
                parsed_url = "\t".join(parsed_url)
            print parsed_url
        else:
            # Lines where we couldnt get any match (e.g when using -q)
            print ''

    return 0

########NEW FILE########
