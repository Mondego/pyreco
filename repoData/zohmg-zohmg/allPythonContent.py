__FILENAME__ = environment
HADOOP_HOME = '/usr/local/hadoop'
HBASE_HOME  = '/usr/local/hbase'

# jars for hadoop, hadoop streaming and hbase
# (you may need to 'ant package' in $HADOOP_HOME to build the streaming jar.)
CLASSPATH = (
#  HADOOP_HOME + '/' + 'hadoop-0.20.1-core.jar',
  HADOOP_HOME + '/' + 'build/hadoop-0.20.2-dev-core.jar',
  HADOOP_HOME + '/' + 'build/contrib/streaming/hadoop-0.20.2-dev-streaming.jar',
  HBASE_HOME  + '/' + 'build/hbase-0.20.1.jar'
)

########NEW FILE########
__FILENAME__ = apachelogparser
import calendar, time, sys, re

class ApacheLogParser:
    def __init__(self):
        # regex for the 'combined' log format.
        self.regex = re.compile(r'''
                                ^([0-9\.]+)\          # IP address
                                [^ ]+\                # ignore
                                [^ ]+\                # ignore
                                \[([^ ]+)[^\]]+\]\    # timestamp
                                "([A-Z]+)\            # method
                                ([^ ]+)[^"]+"\        # path
                                ([0-9\-]+)\           # status
                                ([0-9\-]+)\           # size
                                "([^"]+)"\            # referrer
                                "([^"]+)"             # agent
                                ''', re.VERBOSE)
        # example of log line:
        # 85.229.87.106 - - [15/Nov/2009:18:01:25 +0000]
        # "GET / HTTP/1.1" 200 883 "-"
        # "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-GB; rv:1.9.1.5)
        # Gecko/20091102 Firefox/3.5.5"

    def parse(self, line):
        """parses log line, returns dict."""
        parsed = {}
        try:
            mo = self.regex.search(line)
            parsed['host'] = mo.group(1)
            parsed['timestamp'], parsed['epoch'] = self.timestamps(mo.group(2))
            parsed['method']   = mo.group(3)
            parsed['path']     = mo.group(4)
            parsed['status']   = mo.group(5)
            parsed['size']     = mo.group(6)
            if parsed['size'] == '-':
                parsed['size'] = 0
            parsed['referrer'] = mo.group(7)
            parsed['agent']    = mo.group(8)
        except AttributeError: raise ValueError()
        return parsed

    def timestamps(self, timestamp):
        """parses timestamp of format 15/Nov/2009:18:01:25
        assumes timestamp is in UTC
        returns tuple of (formatted_timestamp, epoch)"""
        time_struct = time.strptime(timestamp, "%d/%b/%Y:%H:%M:%S")
        formatted = time.strftime("%Y-%m-%d %H:%M:%S", time_struct)
        epoch = calendar.timegm(time_struct)
        return formatted, epoch

########NEW FILE########
__FILENAME__ = useragent
import re

class UserAgent:
    browsers = [("Mozilla.*MSIE ([^;]+);.*"           , 'ie'),
                ("Opera/([^ ]+).*|.*Opera ([^ ;]+).*" , 'opera'),
                (".*Firefox/([^ ,;/()']+).*"          , 'firefox'),
                (".* Chrome/([^ ,;/()']+).*"          , 'chrome'),
                (".*Safari/([^ ,)]+).*"               , 'safari'),
                (".*AppleWebKit/([^ )]+).*"           , 'webkit'), # generic webkit
                (".*rv:([^ ;)]+)\\) Gecko/\\d+.*"     , 'gecko')]  # generic gecko
    crawlers = [("Mozilla.*Googlebot/.*", 'google'),
                ("Mozilla.*Ask Jeeves/Teoma.*", 'askjeeves'),
                ("Mozilla.*Yahoo! Slurp.*", 'yahooslurp'),
                ("facebookplatform/.*", 'facebook'),
                ("Baiduspider.*", 'baidu'),
                ("msnbot.*", 'msn')]

    def __init__(self, user_agent_string):
        self.user_agent_string = user_agent_string
        # compile regexes.
        self.browser_patterns = self.compile_patterns(self.browsers)
        self.crawler_patterns = self.compile_patterns(self.crawlers)

    def classify(self):
        for pattern, agent in self.browser_patterns + self.crawler_patterns:
            if pattern.search(self.user_agent_string): return agent
        return 'other'

    def is_browser(self):
        for pattern, agent in self.browser_patterns:
            if pattern.search(self.user_agent_string): return True
        return False

    def is_robot(self):
        for pattern, agent in self.crawler_patterns:
            if pattern.search(self.user_agent_string): return True
        return False


    def compile_patterns(self, patterns):
        compiled = []
        for p, i in patterns:
            compiled.append((re.compile(p), i))
        return compiled


########NEW FILE########
__FILENAME__ = apache
# analyze log files from the apache web server.
# log lines are in the 'combined' format.

from apachelogparser import ApacheLogParser
from useragent import UserAgent
import time

def ymd(epoch):
    """formats a unix timestamp as string of format yyyymmdd
    ymd(1258308085) => '20091115'"""
    time_tuple = time.gmtime(epoch)
    return time.strftime("%Y%m%d", time_tuple)

def map(key, logline):
    try:
        parsed = ApacheLogParser().parse(logline)
    except: return

    # timestamp of format yyyymmdd.
    timestamp = ymd(parsed['epoch'])

    # dimension attributes are strings.
    dimensions = {}
    dimensions['host']     = parsed['host']
    dimensions['method']   = parsed['method']
    dimensions['path']     = parsed['path']
    dimensions['status']   = parsed['status']
    dimensions['referrer'] = parsed['referrer']
    dimensions['agent']    = UserAgent(parsed['agent']).classify()

    # measurements are integers.
    measurements = {}
    measurements['bytes'] = int(parsed['size'])
    measurements['requests'] = 1

    yield timestamp, dimensions, measurements

########NEW FILE########
__FILENAME__ = helper
import sys
sys.path.append("../lib")
sys.path.append("../mappers")

########NEW FILE########
__FILENAME__ = test_apachelogparser
import unittest
import helper
from apachelogparser import ApacheLogParser

class TestApacheLogParser(unittest.TestCase):
    def test_parse(self):
        log = '85.229.87.106 - - [15/Nov/2009:18:01:25 +0000] '\
              '"GET / HTTP/1.1" 200 883 "-" "firefox"'
        parsed = ApacheLogParser().parse(log)
        self.assertEqual(parsed['host'], '85.229.87.106')
        self.assertEqual(parsed['timestamp'], '2009-11-15 18:01:25')
        self.assertEqual(parsed['epoch'], 1258308085)
        self.assertEqual(parsed['method'], 'GET')
        self.assertEqual(parsed['path'], '/')
        self.assertEqual(parsed['status'], '200')
        self.assertEqual(parsed['size'], '883')
        self.assertEqual(parsed['referrer'], '-')
        self.assertEqual(parsed['agent'], 'firefox')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mapper
import unittest
import helper
import apache

class TestMap(unittest.TestCase):
    def test_map(self):
        logline = '85.229.87.106 - - [15/Nov/2009:18:01:25 +0000] '\
                  '"GET / HTTP/1.1" 200 883 '\
                  '"-" "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-GB; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5"'

        ts, dimensions, measurements = apache.map(0, logline).next()

        # ts => 20091115
        # ds => {'status': '200', 'referrer': '-', 'agent': 'firefox',
        #        'host': '85.229.87.106', 'path': '/', 'method': 'GET'}
        # ms => {'requests': 1, 'bytes': 883}

        self.assertEqual(ts, "20091115")
        for d in ['host', 'method', 'path', 'status', 'referrer', 'agent']:
            self.assertTrue(d in dimensions)
        self.assertEqual(dimensions['agent'], 'firefox')
        self.assertEqual(measurements['bytes'], 883)
        self.assertEqual(measurements['requests'], 1)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_useragent
import unittest
import helper
from useragent import UserAgent

class TestUserAgent(unittest.TestCase):
    def test_classify(self):
        user_agent_string = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-GB; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5'
        ua = UserAgent(user_agent_string)
        self.assertEqual(ua.classify(), "firefox")
        self.assertTrue(ua.is_browser())
        self.assertFalse(ua.is_robot())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = environment
# path to yr hadoop directory.
HADOOP_HOME = '/home/fredrik/workspace/hadoop-0.20'

# jars for hadoop, hadoop streaming and hbase
# (you may need to 'ant package' in $HADOOP_HOME to build the streaming jar.)
CLASSPATH = (
  HADOOP_HOME + '/build/hadoop-0.20.1-dev-core.jar',
  HADOOP_HOME + '/build/contrib/streaming/hadoop-0.20.1-dev-streaming.jar',
  '/home/fredrik/workspace/hbase-trunk/build/hbase-0.20.0-dev.jar'
)

########NEW FILE########
__FILENAME__ = mapper
import time

def map(key, value):
    # split on space; make sure there are 7 parts.
    parts = value.split(' ')
    if len(parts) < 7: return

    # extract values.
    epoch = parts[0]
    clipid, producerid, length = parts[1:4]
    country, player, love      = parts[4:7]

    # format timestamp as yyyymmdd.
    ymd = "%d%02d%02d" % time.localtime(float(epoch))[0:3]

    # dimension attributes are strings.
    dimensions = {}
    dimensions['clip']     = str(clipid)
    dimensions['producer'] = str(producerid)
    dimensions['country']  = country
    dimensions['player']   = player

    # measurements are integers.
    measurements = {}
    measurements['plays']   = 1
    measurements['seconds'] = int(length)
    measurements['loves']   = int(love)

    yield ymd, dimensions, measurements

########NEW FILE########
__FILENAME__ = install
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

#!/usr/bin/env python
import os, sys, shutil

# FHS-compliant.
share_target = '/usr/local/share/zohmg'
lib_target   = '/usr/local/lib/zohmg'
doc_target   = share_target + '/doc'
egg_target   = lib_target + '/egg'
jar_target   = lib_target + '/jar'
mapred_target = lib_target + '/mapred'

targets = [share_target, doc_target, lib_target, egg_target, jar_target, mapred_target]


def clean():
    """cleans things a bit."""
    print
    print 'cleaning previous zohmg installation:'

    # remove target directories.
    for dir in targets:
        print " " + dir
        os.system("rm -rf %s" % dir)


def copy_files():
    """populate /usr/local/lib/zohmg and /usr/local/share/zohmg"""
    print
    print "populating zohmg directories:"

    # create target directories.
    for dir in targets:
        if not os.path.isdir(dir):
            os.mkdir(dir)

    # copy docs.
    docs = ['AUTHORS', 'CONTRIBUTE', 'DEPENDENCIES', 'FAQ', 'INSTALL', 'README']
    for doc in docs:
        copy_file(doc, doc, doc_target)

    # copy stuff to share
    shutil.copytree('examples', share_target + '/examples')
    shutil.copytree('graph', share_target + '/graph')
    shutil.copytree('skel-project', share_target + '/skel-project')
    # and to lib
    shutil.copytree("src/zohmg/middleware", lib_target+"/middleware")
    copy_file("bundled eggs", "lib/egg/*.egg", egg_target)
    copy_file("bundled jars", "lib/jar/*.jar", jar_target)
    copy_file("dumbo bootstrapper", "lib/mapred/import.py", mapred_target)


# assumes that setuptools is available.
def python_modules():
    print
    print "building python eggs:"

    egg_log = '/tmp/zohmg-egg-install.log'
    egg_err = '/tmp/zohmg-egg-install.err'
    redirection = ">> %s 2>> %s" % (egg_log, egg_err)
    os.system('date > %s ; date > %s' % (egg_log, egg_err)) # reset logs.

    modules = ['paste', 'pyyaml', 'simplejson']
    print '(assuming setuptools is available.)'
    print '(logging to ' + egg_log + ' and ' + egg_err + ')'
    for module in modules:
        print 'module: ' + module
        r = os.system("easy_install -maxzd %s %s %s" % (egg_target, module, redirection))
        if r != 0:
            print
            print 'trouble!'
            print 'wanted to easy_install modules but failed.'
            print 'logs are at ' + egg_log + ' and ' + egg_err
            # pause.
            print "press ENTER to continue the installation or CTRL-C to break."
            try: sys.stdin.readline()
            except KeyboardInterrupt:
                print "ok."
                sys.exit(1)
    print 'python eggs shelled in ' + egg_target


def setup():
    """calls setup.py"""
    print
    print "installing zohmg egg:"

    # install,
    log = '/tmp/zohmg-install.log'
    err = '/tmp/zohmg-install.err'
    setup_cmd = sys.executable + ' setup.py install > %s 2> %s' % (log, err)
    os.chdir('src')
    r = os.system(setup_cmd)
    if r != 0:
        # try once more immediately; usually works.
        r = os.system(setup_cmd)
        if r != 0:
            print 'trouble!'
            print 'could not install zohmg: python setup.py install'
            print 'log are at ' + log + ' and ' + err
            sys.exit(r)

    # let the user know what happened, clean up.
    os.system("egrep '(Installing|Copying) zohmg' " + log)
    os.system("rm -rf build dist zohmg.egg-info")

def test():
    print 'testing zohmg script: ',
    r = os.system('zohmg 2>&1 > /dev/null')
    if r != 0:
        # fail!
        print 'trouble!'
        print 'test run failed; it seems something is the matter with the installation :-|'
        sys.exit(r)
    print 'ok!'


# copies bundle (file) to destination, printing msg.
def copy_file(msg, file, destination):
    os.system("cp -v %s %s" % (file, destination))


if __name__ == "__main__":

    # check for rootness.
    if os.geteuid() != 0:
        print "you need to be root. please sudo."
        sys.exit(1)

    clean()
    copy_files()
    python_modules()
    setup()
    test()

    print
    print "ok, that should do it!"
    print "now try this:"
    print "$> zohmg help"
    print

########NEW FILE########
__FILENAME__ = import
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

#!/usr/bin/env python
# the script we tell dumbo to run.

from zohmg.mapper import Mapper
from zohmg.reducer import Reducer
from zohmg.combiner import Combiner

from usermapper import map

# !@#
import dumbo
dumbo.run(Mapper(map), Reducer(), Combiner())


########NEW FILE########
__FILENAME__ = environment
# path to yr hadoop directory.
HADOOP_HOME = '/opt/hadoop-0.20.0'

# jars for hadoop, hadoop streaming and hbase
# (you may need to 'ant package' in $HADOOP_HOME to build the streaming jar.)
CLASSPATH = (
  '/opt/hadoop-0.20.0/hadoop-0.20.0-core.jar',
  '/opt/hadoop-0.20.0/build/contrib/streaming/hadoop-0.20.0-streaming.jar',
  '/opt/hbase-0.20.0-alpha/hbase-0.20.0-alpha.jar'
)

########NEW FILE########
__FILENAME__ = mapper
def map(key, value):
    # you will want to analyze value, obviously.

    # timestamp is of format yyyymmdd.
    timestamp = "20090605"

    # dimension attributes are strings.
    dimensions = {'fruit': 'apple',
                  'producer': 'del monte',
                  'color': 'red',
                  'size': 'largeish'}

    # measurements are integers.
    measurements = {}
    measurements['seeds'] = 3
    measurements['weight'] = 85 # grams

    yield timestamp, dimensions, measurements

########NEW FILE########
__FILENAME__ = cmd
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# this is the command line interface.

import sys, os, getopt
from zohmg.utils import fail

# add all bundled eggs to sys.path
eggpath='/usr/local/lib/zohmg/egg'
for (dir, dirnames, files) in os.walk(eggpath):
    for file in files:
        suffix = file.split(".")[-1]
        if suffix == "egg":
            sys.path.append(dir+"/"+file)

# TODO: read version from $somewhere.
version = '0.2.3-dev'

def usage(reason = None):
    zohmg = os.path.basename(sys.argv[0])
    if reason:
        print "error: " + reason
    print "zohmg " + version
    print "usage:"
    print zohmg + " create <dir>"
    print zohmg + " setup"
    print zohmg + " import <mapper> <input-dir> [--local] [--lzo]"
    print zohmg + " server [--host=<host>] [--port=<port>]"
    print zohmg + " reset"
    print zohmg + " help"

def print_version():
    print "zohmg version " + version

def print_help():
    print "Need help?"
    print
    print "There are a few documents in /usr/local/share/zohmg/doc that might be of some help,"
    print "and there's an IRC channel -- #zohmg on freenode -- where you can ask questions."


# command line entry-point.
def zohmg():
    try:
        # read the first argument.
        cmd = sys.argv[1]
    except:
        # there was no first argument.
        usage()
        sys.exit(0)

    if   cmd == 'create' : create()
    elif cmd == 'setup'  : setup()
    elif cmd == 'import' : process()
    elif cmd == 'server' : server()
    elif cmd == 'reset'  : reset()
    elif cmd in ['version', '--version']: print_version()
    elif cmd in ['help',    '--help']:    print_help()
    else: usage()

def create():
    from zohmg.create import Create
    try:
        path = sys.argv[2]
    except:
        usage("create needs an argument.")
        sys.exit(1)

    Create(path)


def setup():
    refuse_to_act_in_nonzohmg_directory()
    from zohmg.setup import Setup
    Setup().go()

# import.
def process():
    refuse_to_act_in_nonzohmg_directory()
    from zohmg.process import Process
    try:
        # check for two arguments,
        mapper = sys.argv[2]
        # (works only with relative paths for now.)
        mapperpath = os.path.abspath(".")+"/"+mapper
        inputdir = sys.argv[3]
        dumbo_args = sys.argv[4:]
    except:
        usage("import needs two arguments.")
        sys.exit(1)

    Process().go(mapperpath, inputdir, dumbo_args)


def server():
    refuse_to_act_in_nonzohmg_directory()
    import zohmg.server
    host, port = zohmg.server.defaults()

    try:
        opts, args = getopt.getopt(sys.argv[2:], "h:p:", ["host=", "port="])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)
    
    for o, a in opts:
        if o in ("-h", "--host"):
            host=a
        elif o in ("-p", "--port"):
            port=a
        else:
            assert False, "unhandled option"

    project_dir = os.path.abspath("")
    zohmg.server.start(project_dir, host=host, port=port)


def reset():
    refuse_to_act_in_nonzohmg_directory()
    from zohmg.reset import Reset
    Reset().please()


# exits if 'zohmg' was run in a directory without the special .zohmg-file.
def refuse_to_act_in_nonzohmg_directory():
    cwd = os.getcwd()
    if not os.path.exists(cwd+"/.zohmg"):
        msg = "error: This is not a proper zohmg project."
        fail(msg)

########NEW FILE########
__FILENAME__ = combiner
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

class Combiner(object):
    def __init__(self):
        pass

    def __call__(self, key, values):
        yield key, sum(values)

########NEW FILE########
__FILENAME__ = config
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from zohmg.utils import fail # heh.
import os, re, sys, time


# the configuration file has four parts:
#   'dataset' - string
#   'dimensions' - list of strings
#   'units' - list of strings
#   'projections' - list of lists



class ConfigNotLoaded(Exception):
    def __init__(self, value):
        self.error = value
    def __str__(self):
        return self.error



# TODO: multiple dataset files
class Config(object):
    def __init__(self, config_file=None):
        if config_file:
            self.config_file = config_file
        else:
            self.config_file = "dataset.yaml"

        self.config = {}
        self.__read_config()


    def __read_config(self):
        import yaml

        config_loaded    = False
        possible_configs = [self.config_file, "config/"+self.config_file]
        file_loaded = None

        # two error conditions can occur:
        #  A) all files missing/can't be opened. => try next file, report later.
        #  B) a file opens, but can't be parsed. => report imm.

        while (not config_loaded and len(possible_configs) > 0):
            config_file = possible_configs.pop()

            try:
                f = open(config_file, "r")
            except IOError, e:
                continue # try to open the next file.

            # we managed to open the file; will not try and open any more.
            # now, load yaml.
            try:
                self.config = yaml.load(f)
                file_loaded = config_file
            except yaml.scanner.ScannerError, e:
                # condition B.
                # report error immediately.
                sys.stderr.write("Configuration error: could not parse %s.\n" % config_file)
                sys.stderr.write("%s\n", e)
                f.close()
                sys.exit(1)

            # ok, good!
            f.close()
            config_loaded = True


        if not config_loaded:
            # condition A.
            sys.stderr.write("Configuration error: Could not read dataset configuration " \
                              "from any of these files:\n" \
                              "\n".join(possible_configs) + "\n")
            raise ConfigNotLoaded("Could not read configuration file.")

        # check contents.
        if not self.sanity_check():
            msg = "[%s] Configuration error: Could not parse configuration from %s." % (time.asctime(), file_loaded)
            fail(msg) # TODO: should maybe not use fail as it raises SystemExit.

        return self.config


    def dataset(self):
        return self.config['dataset']
    def dimensions(self):
        return self.config['dimensions']
    def units(self):
        return self.config['units']
    def projections(self):
        # turn list of strings into list of list of strings.
        # ['country', 'country-domain-useragent-usertype']
        # => [['country'], ['country', 'domain', 'useragent', 'usertype']]
        return map(lambda s : s.split('-'), self.config['projections'])

    # returns True if configuration is sane,
    # False otherwise.
    def sanity_check(self):
        sane = True # .. so far.
        try:
            # must be able to read these.
            dataset = self.dataset()
            ds = self.dimensions()
            us = self.units()
            ps = self.projections()
        except:
            # might as well return straight away; nothing else will work.
            print >>sys.stderr, "Configuration error: Missing definition of dataset, dimensions, units, projections."
            return False

        # dimensions, projections and units must be non-empty.
        if ds == None or us == None or ps == None or \
            len(ds) == 0 or len(us) == 0 or len(ps) == 0:
                print >>sys.stderr, "Configuration error: dimensions, projections and units must be non-empty."
                return False

        # also, the configuration may not reference unknown dimensions.
        for p in ps:
            for d in p:
                if d not in ds:
                    print >>sys.stderr, "Configuration error: %s is a reference to an unkown dimension." % d
                    sane = False

        # also, there must be no funny characters in the name of dimensions or units.
        # dimensions and units will feature in the columnfamily name and rowkey respectively.
        for (type, data) in [('dimension', ds), ('unit', us)]:
            for d in data:
                if re.match('^[a-zA-Z0-9]+$', d) == None:
                    print >>sys.stderr, "Configuration error: '%s' is an invalid %s name." % (d, type)
                    sane = False

        # we can be a litte less strict with dataset names since they become the table names.
        if re.match('^[a-zA-Z0-9]+[a-zA-Z0-9-_]*[a-zA-Z0-9]+$', dataset) == None:
            print >>sys.stderr, "Configuration error: '%s' is an invalid dataset name." % dataset
            sane = False

        return sane


class Environ(object):
    def __init__(self):
        self.environ = {}
        self.read_environ()

    def get(self, key):
        try:
            return self.environ[key]
        except:
            return ''

    def read_environ(self):
        # add config path so we can import from it.
        sys.path.append(".")
        sys.path.append("config")

        try:
            import environment
        except ImportError:
            msg = "[%s] Error: Could not import environment.py" % time.asctime()
            fail(msg)

        for key in dir(environment):
            self.environ[key] = environment.__dict__[key]

########NEW FILE########
__FILENAME__ = create
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os, sys, shutil
from zohmg.utils import fail

class Create(object):
    def __init__(self, path):
        self.basename = os.path.basename(path)
        self.abspath  = os.path.abspath(path)

        try:
            shutil.copytree('/usr/local/share/zohmg/skel-project', self.abspath)
            # reset access and mod times.
            os.system('cd %s; touch *; touch **/*' % self.abspath)
        except OSError, ose:
            # something went wrong. act accordingly.
            msg = "error: could not create project directory - %s" % ose.strerror
            fail(msg, ose.errno)
        print ("created project directory: %s" % self.abspath)

        # sed-replace dataset name.
        dataset_path = self.abspath + '/config/dataset.yaml'
        r0 = os.system("sed 's/DATASETNAME/%s/' %s  > /tmp/dataset.yaml" % (self.basename, dataset_path))
        r1 = os.system("mv /tmp/dataset.yaml " + dataset_path)
        if (r0 or r1):
            print 'failed to massage config/dataset.yaml :-('

########NEW FILE########
__FILENAME__ = data
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# zohmg.data, hello.

import sys
import simplejson as json

from zohmg.utils import compare_triples, strip
from zohmg.scanner import HBaseScanner


class DataNotFound(Exception):
    def __init__(self, value):
        self.error = value
    def __str__(self):
        return self.error

class NoSuitableProjection(Exception):
    def __init__(self, value):
        self.error = value
    def __str__(self):
        return self.error

class MissingArguments(Exception):
    def __init__(self, value):
        self.error = value
    def __str__(self):
        return self.error



# public interface.
def query(table, projections, params):

    # jsonp.
    try:    jsonp_method = params["jsonp"]
    except: jsonp_method = None

    # check parameters.
    querydict = {}
    try:
        querydict['t0'] = params['t0']
        querydict['t1'] = params['t1']
        querydict['d0'] = params['d0']
        querydict['d0v'] = map(strip, params['d0v'].split(',')) # => ['SE', 'DE', 'US']
        querydict['unit'] = params['unit']
    except KeyError, e:
        raise MissingArguments(str(e))

    print ""
    print "-- QUERY --"
    print "t0: " + querydict['t0']
    print "t1: " + querydict['t1']
    print "unit: " + querydict['unit']
    print "d0: " + querydict['d0']
    print "d0v: "+ str(querydict['d0v'])
    print "----------"

    filters = make_filters(params)

    data = hbase_get(table, projections, querydict, filters)
    return dump_jsonp(data, jsonp_method)


def make_filters(params):
    # TODO: there is a neater way of doing this.
    filters = {}
    for n in range(1,5):
        try:
            dim = params["d"+str(n)]
            print 'passed dim'
            val = params["d"+str(n)+"v"]
            filters[dim] = val
            print 'filter for ' + dim
        except:
            print 'no filter for ' + str(n)
            continue

    # massage the filters.
    for key in filters.copy():
        if filters[key] in ['all', '*']:
            # 'all' or '*' is equivalent to not filtering at all.
            del filters[key]
        else:
            # turn comma-delimited string into list.
            filters[key] = filters[key].split(',')

    print "filters: " + str(filters)
    return filters


# TODO: classify.

# returns jsonp which can be used in clients.
def dump_jsonp(data, jsonp_method=None):
    jsondata = json.dumps(data)

    if jsonp_method:
        # client requested data to be wrapped in a function call.
        return jsonp_method+"("+jsondata+")"
    else:
        return jsondata


# dimensions is a list of dimensions: ['country', 'usertype', 'useragent']
# values is a dictionary of lists, describing the possible values for each dimension,
# like so: {'country': ['SE', 'DE', 'IT'], 'useragent': ['*'], 'usertype': ['anon']}
#
# returns a list of list of strings that describe the column qualifiers to fetch.
def enumerate_cells(dimensions, values, target=[]):
    if dimensions == []:
        # base case.
        return target

    newtarget = []
    if target == []:
        # first time around.
        for value in values[dimensions[0]]:
            newtarget.append([value])
    else:
        for t in target:
            for value in values[dimensions[0]]:
                newtarget.append(t + [value])

    return enumerate_cells(dimensions[1:], values, newtarget)


def find_suitable_projection(projections, d0, filters):
    # pick the best-suiting projection p.
    # 1) p must contain all dimensions we specify.
    # 2) of all ps satisfying 1, the position of d0 in p must be leftmost,
    #    and p must be the shortest of the fitting candidates.

    ps = [] # projection candidates.
    wanted = set([d0] + filters.keys())

    for p in projections:
        if set(p).issuperset(wanted):
            ps.append((len(p), p.index(d0), p))

    if len(ps) == 0: return None # no suitable projections!

    # sort by length, then index; pick the first one.
    projection = sorted(ps, compare_triples)[0][2]
    return projection


# add the values of a dictionary.
def dict_addition(a, b):
    c = a.copy()
    for k in b.keys():
        c[k] = c.get(k, 0) + b[k]
    return c



def rowkey_formatter(projection, d0, d0v, filters, t0, t1):
    rowkeyarray = []
    found_stoprow = False
    for d in projection:
        rowkeyarray.append(d)
        if d == d0:
            if d0v == '' or d0v == ['']:
                rowkeyarray.append('all')
            else:
                rowkeyarray.append(d0v)
        elif d in filters.keys() and len(filters[d]) == 1:
            # filtering for a single value; append.
            rowkeyarray.append(filters[d][0])
        elif d in filters.keys():
            found_stoprow = True # corner cases be damned.
            # filtering on many values - we need to fetch them all.
            # in this case we need to FRIGGIN fetch all dates too. mngh.
            # TODO: consider doing many scans instead.
            rowkey = '-'.join(rowkeyarray)
            startrow = rowkey + '-'
            stoprow  = rowkey + '-' + "~"
            break
        else:
            # d is a dimension other than the base dimension (d0)
            # and there are no filters on it.
            rowkeyarray.append('all')

     # the common case.
    if not found_stoprow:
        rowkey = '-'.join(rowkeyarray)
        # rowkey => 'artist-97930-track-102203-20090601'
        startrow = rowkey + '-' + t0
        stoprow  = rowkey + '-' + t1 + "~"

    return startrow, stoprow
    
# rowkey => (timestamp, dimension+attribute pairs)
def rowkey_interpreter(rowkey):
    rk = rowkey.split('-')
    timestamp = rk.pop()
    it = iter(rk)
    return timestamp, dict(zip(it, it))


def scan(table, columns, startrow, stoprow, basedimension, range, filters, data):
    t0, t1 = range

    # connect to hbase.
    scanner = HBaseScanner()
    scanner.connect()
    scanner.open(table, columns, startrow, stoprow)

    numrows = 0
    while True:
        t = {}
        numrows += 1
        next = scanner.next()
        if next == []:
            break
        r = next[0]
        timestamp, ds = rowkey_interpreter(r.row)
        dval = ds.get(basedimension)
        del ds[basedimension]

        filter_accepts = True
        for k in ds.keys():
            if not k in filters: continue
            if not ds[k] in filters[k]: filter_accepts = False

        if filter_accepts and (timestamp >= t0 and timestamp <= t1):
            # read possible old values, add.
            for column in r.columns:
                t[dval] = t.get(dval, 0)
                t[dval] += int(r.columns[column].value)
            # and save.
            data[timestamp] = dict_addition(t, data.get(timestamp, {}))

    return data, numrows



# fetches data from hbase,
# returns sorted list of dictionaries suitable for json dumping.
# TODO: private.
def hbase_get(table, projections, query, filters):
# query is guaranteed to have the following keys:
#  t0, t1, unit, d0, d0v


    projection = find_suitable_projection(projections, query['d0'], filters)
    if projection == None:
        print 'could not find a suitable projection for ' + query['d0']
        raise NoSuitableProjection("could not find a suitable projection for dimension " + query['d0'])
    print "most suited projection: " + str(projection)



    # format column-family + qualifier
    cfq = 'unit:' + query['unit']

    data = {}
    rows = 0
    for val in query['d0v']:
        startrow, stoprow = rowkey_formatter(projection, query['d0'], val, filters, query['t0'], query['t1'])
        print "start: " + startrow
        print "stop:  " + stoprow
        data, r = scan(table, [cfq], startrow, stoprow, query['d0'], (query['t0'], query['t1']), filters, data)
        rows += r
    print "scanned a total of %d rows." % rows

    # returns a list of dicts sorted by timestamp.
    return [ {timestamp:data[timestamp]} for timestamp in sorted(data) ]

########NEW FILE########
__FILENAME__ = hbase
import sys
from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from hbase_thrift import Hbase
from hbase_thrift.ttypes import ColumnDescriptor
from hbase_thrift.ttypes import AlreadyExists, IOError, IllegalArgument

class ZohmgHBase:

    @classmethod
    def transport(self, host='localhost'):
        try:
            transport = TSocket.TSocket(host, 9090)
            transport = TTransport.TBufferedTransport(transport)
            protocol  = TBinaryProtocol.TBinaryProtocol(transport)
            client = Hbase.Client(protocol)
            transport.open()
            return client
        except ImportError, e:
            sys.stderr.write(str(e)+'\n')
            sys.exit(8)
        except Exception, e:
            print "e: " + str(e.__class__) + " ^ " + str(e)
            sys.stderr.write("could not setup thrift transport.\n")
            sys.stderr.write("is the thrift server switched on?\n")
            sys.exit(16)


    @classmethod
    def create_table(self, table_name, families=[], client=None):
        """."""
        if not client:
            # default to localhost.
            client = ZohmgHBase.transport("localhost")

        try:
            columns = []
            for family in families:
                column = ColumnDescriptor(family+":")
                columns.append(column)
            client.createTable(table_name, columns)

        except AlreadyExists:
            sys.stderr.write("oh noes, %s already exists.\n" % table_name)
            exit(2)
        except IOError, e:
            sys.stderr.write("bust: IOError: "+ str(e) + "\n")
            exit(3)
        except IllegalArgument, e:
            sys.stderr.write("error: " + str(e) + "\n")
            sys.stderr.write(" => bust\n")
            exit(4)

    @classmethod
    def delete_table(self, table_name, client=None):
        if not client:
            # default to localhost.
            client = ZohmgHBase.transport("localhost")
        ZohmgHBase.disable_table(table_name, client) and \
        ZohmgHBase.drop_table(table_name, client)

    @classmethod
    def disable_table(self, table_name, client=None):
        try:
            client.disableTable(table_name)
            print "%s disabled." % table_name
        except IOError, e:
            print "error: %s" % e
            raise
        return True

    @classmethod
    def drop_table(self, table_name, client=None):
        try:
            client.deleteTable(table_name)
            print "%s dropped." % table_name
        except IOError, e:
            print "IOError: %s" % e
            raise
        return True

########NEW FILE########
__FILENAME__ = constants
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#

from thrift.Thrift import *
from ttypes import *


########NEW FILE########
__FILENAME__ = Hbase
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#

from thrift.Thrift import *
from ttypes import *
from thrift.Thrift import TProcessor
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
try:
  from thrift.protocol import fastbinary
except:
  fastbinary = None


class Iface:
  def enableTable(self, tableName):
    """
    Brings a table on-line (enables it)
    @param tableName name of the table
    
    Parameters:
     - tableName
    """
    pass

  def disableTable(self, tableName):
    """
    Disables a table (takes it off-line) If it is being served, the master
    will tell the servers to stop serving it.
    @param tableName name of the table
    
    Parameters:
     - tableName
    """
    pass

  def isTableEnabled(self, tableName):
    """
    @param tableName name of table to check
    @return true if table is on-line
    
    Parameters:
     - tableName
    """
    pass

  def compact(self, tableNameOrRegionName):
    """
    Parameters:
     - tableNameOrRegionName
    """
    pass

  def majorCompact(self, tableNameOrRegionName):
    """
    Parameters:
     - tableNameOrRegionName
    """
    pass

  def getTableNames(self, ):
    """
    List all the userspace tables.
    @return - returns a list of names
    """
    pass

  def getColumnDescriptors(self, tableName):
    """
    List all the column families assoicated with a table.
    @param tableName table name
    @return list of column family descriptors
    
    Parameters:
     - tableName
    """
    pass

  def getTableRegions(self, tableName):
    """
    List the regions associated with a table.
    @param tableName table name
    @return list of region descriptors
    
    Parameters:
     - tableName
    """
    pass

  def createTable(self, tableName, columnFamilies):
    """
    Create a table with the specified column families.  The name
    field for each ColumnDescriptor must be set and must end in a
    colon (:).  All other fields are optional and will get default
    values if not explicitly specified.
    
    @param tableName name of table to create
    @param columnFamilies list of column family descriptors
    
    @throws IllegalArgument if an input parameter is invalid
    @throws AlreadyExists if the table name already exists
    
    Parameters:
     - tableName
     - columnFamilies
    """
    pass

  def deleteTable(self, tableName):
    """
    Deletes a table
    @param tableName name of table to delete
    @throws IOError if table doesn't exist on server or there was some other
    problem
    
    Parameters:
     - tableName
    """
    pass

  def get(self, tableName, row, column):
    """
    Get a single TCell for the specified table, row, and column at the
    latest timestamp. Returns an empty list if no such value exists.
    
    @param tableName name of table
    @param row row key
    @param column column name
    @return value for specified row/column
    
    Parameters:
     - tableName
     - row
     - column
    """
    pass

  def getVer(self, tableName, row, column, numVersions):
    """
    Get the specified number of versions for the specified table,
    row, and column.
    
    @param tableName name of table
    @param row row key
    @param column column name
    @param numVersions number of versions to retrieve
    @return list of cells for specified row/column
    
    Parameters:
     - tableName
     - row
     - column
     - numVersions
    """
    pass

  def getVerTs(self, tableName, row, column, timestamp, numVersions):
    """
    Get the specified number of versions for the specified table,
    row, and column.  Only versions less than or equal to the specified
    timestamp will be returned.
    
    @param tableName name of table
    @param row row key
    @param column column name
    @param timestamp timestamp
    @param numVersions number of versions to retrieve
    @return list of cells for specified row/column
    
    Parameters:
     - tableName
     - row
     - column
     - timestamp
     - numVersions
    """
    pass

  def getRow(self, tableName, row):
    """
    Get all the data for the specified table and row at the latest
    timestamp. Returns an empty list if the row does not exist.
    
    @param tableName name of table
    @param row row key
    @return TRowResult containing the row and map of columns to TCells
    
    Parameters:
     - tableName
     - row
    """
    pass

  def getRowWithColumns(self, tableName, row, columns):
    """
    Get the specified columns for the specified table and row at the latest
    timestamp. Returns an empty list if the row does not exist.
    
    @param tableName name of table
    @param row row key
    @param columns List of columns to return, null for all columns
    @return TRowResult containing the row and map of columns to TCells
    
    Parameters:
     - tableName
     - row
     - columns
    """
    pass

  def getRowTs(self, tableName, row, timestamp):
    """
    Get all the data for the specified table and row at the specified
    timestamp. Returns an empty list if the row does not exist.
    
    @param tableName of table
    @param row row key
    @param timestamp timestamp
    @return TRowResult containing the row and map of columns to TCells
    
    Parameters:
     - tableName
     - row
     - timestamp
    """
    pass

  def getRowWithColumnsTs(self, tableName, row, columns, timestamp):
    """
    Get the specified columns for the specified table and row at the specified
    timestamp. Returns an empty list if the row does not exist.
    
    @param tableName name of table
    @param row row key
    @param columns List of columns to return, null for all columns
    @return TRowResult containing the row and map of columns to TCells
    
    Parameters:
     - tableName
     - row
     - columns
     - timestamp
    """
    pass

  def mutateRow(self, tableName, row, mutations):
    """
    Apply a series of mutations (updates/deletes) to a row in a
    single transaction.  If an exception is thrown, then the
    transaction is aborted.  Default current timestamp is used, and
    all entries will have an identical timestamp.
    
    @param tableName name of table
    @param row row key
    @param mutations list of mutation commands
    
    Parameters:
     - tableName
     - row
     - mutations
    """
    pass

  def mutateRowTs(self, tableName, row, mutations, timestamp):
    """
    Apply a series of mutations (updates/deletes) to a row in a
    single transaction.  If an exception is thrown, then the
    transaction is aborted.  The specified timestamp is used, and
    all entries will have an identical timestamp.
    
    @param tableName name of table
    @param row row key
    @param mutations list of mutation commands
    @param timestamp timestamp
    
    Parameters:
     - tableName
     - row
     - mutations
     - timestamp
    """
    pass

  def mutateRows(self, tableName, rowBatches):
    """
    Apply a series of batches (each a series of mutations on a single row)
    in a single transaction.  If an exception is thrown, then the
    transaction is aborted.  Default current timestamp is used, and
    all entries will have an identical timestamp.
    
    @param tableName name of table
    @param rowBatches list of row batches
    
    Parameters:
     - tableName
     - rowBatches
    """
    pass

  def mutateRowsTs(self, tableName, rowBatches, timestamp):
    """
    Apply a series of batches (each a series of mutations on a single row)
    in a single transaction.  If an exception is thrown, then the
    transaction is aborted.  The specified timestamp is used, and
    all entries will have an identical timestamp.
    
    @param tableName name of table
    @param rowBatches list of row batches
    @param timestamp timestamp
    
    Parameters:
     - tableName
     - rowBatches
     - timestamp
    """
    pass

  def atomicIncrement(self, tableName, row, column, value):
    """
    Atomically increment the column value specified.  Returns the next value post increment.
    @param tableName name of table
    @param row row to increment
    @param column name of column
    @param value amount to increment by
    
    Parameters:
     - tableName
     - row
     - column
     - value
    """
    pass

  def deleteAll(self, tableName, row, column):
    """
    Delete all cells that match the passed row and column.
    
    @param tableName name of table
    @param row Row to update
    @param column name of column whose value is to be deleted
    
    Parameters:
     - tableName
     - row
     - column
    """
    pass

  def deleteAllTs(self, tableName, row, column, timestamp):
    """
    Delete all cells that match the passed row and column and whose
    timestamp is equal-to or older than the passed timestamp.
    
    @param tableName name of table
    @param row Row to update
    @param column name of column whose value is to be deleted
    @param timestamp timestamp
    
    Parameters:
     - tableName
     - row
     - column
     - timestamp
    """
    pass

  def deleteAllRow(self, tableName, row):
    """
    Completely delete the row's cells.
    
    @param tableName name of table
    @param row key of the row to be completely deleted.
    
    Parameters:
     - tableName
     - row
    """
    pass

  def deleteAllRowTs(self, tableName, row, timestamp):
    """
    Completely delete the row's cells marked with a timestamp
    equal-to or older than the passed timestamp.
    
    @param tableName name of table
    @param row key of the row to be completely deleted.
    @param timestamp timestamp
    
    Parameters:
     - tableName
     - row
     - timestamp
    """
    pass

  def scannerOpen(self, tableName, startRow, columns):
    """
    Get a scanner on the current table starting at the specified row and
    ending at the last row in the table.  Return the specified columns.
    
    @param columns columns to scan. If column name is a column family, all
    columns of the specified column family are returned.  Its also possible
    to pass a regex in the column qualifier.
    @param tableName name of table
    @param startRow starting row in table to scan.  send "" (empty string) to
                    start at the first row.
    
    @return scanner id to be used with other scanner procedures
    
    Parameters:
     - tableName
     - startRow
     - columns
    """
    pass

  def scannerOpenWithStop(self, tableName, startRow, stopRow, columns):
    """
    Get a scanner on the current table starting and stopping at the
    specified rows.  ending at the last row in the table.  Return the
    specified columns.
    
    @param columns columns to scan. If column name is a column family, all
    columns of the specified column family are returned.  Its also possible
    to pass a regex in the column qualifier.
    @param tableName name of table
    @param startRow starting row in table to scan.  send "" (empty string) to
                    start at the first row.
    @param stopRow row to stop scanning on.  This row is *not* included in the
                   scanner's results
    
    @return scanner id to be used with other scanner procedures
    
    Parameters:
     - tableName
     - startRow
     - stopRow
     - columns
    """
    pass

  def scannerOpenWithPrefix(self, tableName, startAndPrefix, columns):
    """
    Open a scanner for a given prefix.  That is all rows will have the specified
    prefix. No other rows will be returned.
    
    @param tableName name of table
    @param startAndPrefix the prefix (and thus start row) of the keys you want
    @param columns the columns you want returned
    @return scanner id to use with other scanner calls
    
    Parameters:
     - tableName
     - startAndPrefix
     - columns
    """
    pass

  def scannerOpenTs(self, tableName, startRow, columns, timestamp):
    """
    Get a scanner on the current table starting at the specified row and
    ending at the last row in the table.  Return the specified columns.
    Only values with the specified timestamp are returned.
    
    @param columns columns to scan. If column name is a column family, all
    columns of the specified column family are returned.  Its also possible
    to pass a regex in the column qualifier.
    @param tableName name of table
    @param startRow starting row in table to scan.  send "" (empty string) to
                    start at the first row.
    @param timestamp timestamp
    
    @return scanner id to be used with other scanner procedures
    
    Parameters:
     - tableName
     - startRow
     - columns
     - timestamp
    """
    pass

  def scannerOpenWithStopTs(self, tableName, startRow, stopRow, columns, timestamp):
    """
    Get a scanner on the current table starting and stopping at the
    specified rows.  ending at the last row in the table.  Return the
    specified columns.  Only values with the specified timestamp are
    returned.
    
    @param columns columns to scan. If column name is a column family, all
    columns of the specified column family are returned.  Its also possible
    to pass a regex in the column qualifier.
    @param tableName name of table
    @param startRow starting row in table to scan.  send "" (empty string) to
                    start at the first row.
    @param stopRow row to stop scanning on.  This row is *not* included
                   in the scanner's results
    @param timestamp timestamp
    
    @return scanner id to be used with other scanner procedures
    
    Parameters:
     - tableName
     - startRow
     - stopRow
     - columns
     - timestamp
    """
    pass

  def scannerGet(self, id):
    """
    Returns the scanner's current row value and advances to the next
    row in the table.  When there are no more rows in the table, or a key
    greater-than-or-equal-to the scanner's specified stopRow is reached,
    an empty list is returned.
    
    @param id id of a scanner returned by scannerOpen
    @return a TRowResult containing the current row and a map of the columns to TCells.
    @throws IllegalArgument if ScannerID is invalid
    @throws NotFound when the scanner reaches the end
    
    Parameters:
     - id
    """
    pass

  def scannerGetList(self, id, nbRows):
    """
    Returns, starting at the scanner's current row value nbRows worth of
    rows and advances to the next row in the table.  When there are no more
    rows in the table, or a key greater-than-or-equal-to the scanner's
    specified stopRow is reached,  an empty list is returned.
    
    @param id id of a scanner returned by scannerOpen
    @param nbRows number of results to regturn
    @return a TRowResult containing the current row and a map of the columns to TCells.
    @throws IllegalArgument if ScannerID is invalid
    @throws NotFound when the scanner reaches the end
    
    Parameters:
     - id
     - nbRows
    """
    pass

  def scannerClose(self, id):
    """
    Closes the server-state associated with an open scanner.
    
    @param id id of a scanner returned by scannerOpen
    @throws IllegalArgument if ScannerID is invalid
    
    Parameters:
     - id
    """
    pass


class Client(Iface):
  def __init__(self, iprot, oprot=None):
    self._iprot = self._oprot = iprot
    if oprot != None:
      self._oprot = oprot
    self._seqid = 0

  def enableTable(self, tableName):
    """
    Brings a table on-line (enables it)
    @param tableName name of the table
    
    Parameters:
     - tableName
    """
    self.send_enableTable(tableName)
    self.recv_enableTable()

  def send_enableTable(self, tableName):
    self._oprot.writeMessageBegin('enableTable', TMessageType.CALL, self._seqid)
    args = enableTable_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_enableTable(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = enableTable_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def disableTable(self, tableName):
    """
    Disables a table (takes it off-line) If it is being served, the master
    will tell the servers to stop serving it.
    @param tableName name of the table
    
    Parameters:
     - tableName
    """
    self.send_disableTable(tableName)
    self.recv_disableTable()

  def send_disableTable(self, tableName):
    self._oprot.writeMessageBegin('disableTable', TMessageType.CALL, self._seqid)
    args = disableTable_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_disableTable(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = disableTable_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def isTableEnabled(self, tableName):
    """
    @param tableName name of table to check
    @return true if table is on-line
    
    Parameters:
     - tableName
    """
    self.send_isTableEnabled(tableName)
    return self.recv_isTableEnabled()

  def send_isTableEnabled(self, tableName):
    self._oprot.writeMessageBegin('isTableEnabled', TMessageType.CALL, self._seqid)
    args = isTableEnabled_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_isTableEnabled(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = isTableEnabled_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "isTableEnabled failed: unknown result");

  def compact(self, tableNameOrRegionName):
    """
    Parameters:
     - tableNameOrRegionName
    """
    self.send_compact(tableNameOrRegionName)
    self.recv_compact()

  def send_compact(self, tableNameOrRegionName):
    self._oprot.writeMessageBegin('compact', TMessageType.CALL, self._seqid)
    args = compact_args()
    args.tableNameOrRegionName = tableNameOrRegionName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_compact(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = compact_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def majorCompact(self, tableNameOrRegionName):
    """
    Parameters:
     - tableNameOrRegionName
    """
    self.send_majorCompact(tableNameOrRegionName)
    self.recv_majorCompact()

  def send_majorCompact(self, tableNameOrRegionName):
    self._oprot.writeMessageBegin('majorCompact', TMessageType.CALL, self._seqid)
    args = majorCompact_args()
    args.tableNameOrRegionName = tableNameOrRegionName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_majorCompact(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = majorCompact_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def getTableNames(self, ):
    """
    List all the userspace tables.
    @return - returns a list of names
    """
    self.send_getTableNames()
    return self.recv_getTableNames()

  def send_getTableNames(self, ):
    self._oprot.writeMessageBegin('getTableNames', TMessageType.CALL, self._seqid)
    args = getTableNames_args()
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getTableNames(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getTableNames_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getTableNames failed: unknown result");

  def getColumnDescriptors(self, tableName):
    """
    List all the column families assoicated with a table.
    @param tableName table name
    @return list of column family descriptors
    
    Parameters:
     - tableName
    """
    self.send_getColumnDescriptors(tableName)
    return self.recv_getColumnDescriptors()

  def send_getColumnDescriptors(self, tableName):
    self._oprot.writeMessageBegin('getColumnDescriptors', TMessageType.CALL, self._seqid)
    args = getColumnDescriptors_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getColumnDescriptors(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getColumnDescriptors_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getColumnDescriptors failed: unknown result");

  def getTableRegions(self, tableName):
    """
    List the regions associated with a table.
    @param tableName table name
    @return list of region descriptors
    
    Parameters:
     - tableName
    """
    self.send_getTableRegions(tableName)
    return self.recv_getTableRegions()

  def send_getTableRegions(self, tableName):
    self._oprot.writeMessageBegin('getTableRegions', TMessageType.CALL, self._seqid)
    args = getTableRegions_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getTableRegions(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getTableRegions_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getTableRegions failed: unknown result");

  def createTable(self, tableName, columnFamilies):
    """
    Create a table with the specified column families.  The name
    field for each ColumnDescriptor must be set and must end in a
    colon (:).  All other fields are optional and will get default
    values if not explicitly specified.
    
    @param tableName name of table to create
    @param columnFamilies list of column family descriptors
    
    @throws IllegalArgument if an input parameter is invalid
    @throws AlreadyExists if the table name already exists
    
    Parameters:
     - tableName
     - columnFamilies
    """
    self.send_createTable(tableName, columnFamilies)
    self.recv_createTable()

  def send_createTable(self, tableName, columnFamilies):
    self._oprot.writeMessageBegin('createTable', TMessageType.CALL, self._seqid)
    args = createTable_args()
    args.tableName = tableName
    args.columnFamilies = columnFamilies
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_createTable(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = createTable_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    if result.exist != None:
      raise result.exist
    return

  def deleteTable(self, tableName):
    """
    Deletes a table
    @param tableName name of table to delete
    @throws IOError if table doesn't exist on server or there was some other
    problem
    
    Parameters:
     - tableName
    """
    self.send_deleteTable(tableName)
    self.recv_deleteTable()

  def send_deleteTable(self, tableName):
    self._oprot.writeMessageBegin('deleteTable', TMessageType.CALL, self._seqid)
    args = deleteTable_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_deleteTable(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = deleteTable_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def get(self, tableName, row, column):
    """
    Get a single TCell for the specified table, row, and column at the
    latest timestamp. Returns an empty list if no such value exists.
    
    @param tableName name of table
    @param row row key
    @param column column name
    @return value for specified row/column
    
    Parameters:
     - tableName
     - row
     - column
    """
    self.send_get(tableName, row, column)
    return self.recv_get()

  def send_get(self, tableName, row, column):
    self._oprot.writeMessageBegin('get', TMessageType.CALL, self._seqid)
    args = get_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_get(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = get_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "get failed: unknown result");

  def getVer(self, tableName, row, column, numVersions):
    """
    Get the specified number of versions for the specified table,
    row, and column.
    
    @param tableName name of table
    @param row row key
    @param column column name
    @param numVersions number of versions to retrieve
    @return list of cells for specified row/column
    
    Parameters:
     - tableName
     - row
     - column
     - numVersions
    """
    self.send_getVer(tableName, row, column, numVersions)
    return self.recv_getVer()

  def send_getVer(self, tableName, row, column, numVersions):
    self._oprot.writeMessageBegin('getVer', TMessageType.CALL, self._seqid)
    args = getVer_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.numVersions = numVersions
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getVer(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getVer_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getVer failed: unknown result");

  def getVerTs(self, tableName, row, column, timestamp, numVersions):
    """
    Get the specified number of versions for the specified table,
    row, and column.  Only versions less than or equal to the specified
    timestamp will be returned.
    
    @param tableName name of table
    @param row row key
    @param column column name
    @param timestamp timestamp
    @param numVersions number of versions to retrieve
    @return list of cells for specified row/column
    
    Parameters:
     - tableName
     - row
     - column
     - timestamp
     - numVersions
    """
    self.send_getVerTs(tableName, row, column, timestamp, numVersions)
    return self.recv_getVerTs()

  def send_getVerTs(self, tableName, row, column, timestamp, numVersions):
    self._oprot.writeMessageBegin('getVerTs', TMessageType.CALL, self._seqid)
    args = getVerTs_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.timestamp = timestamp
    args.numVersions = numVersions
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getVerTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getVerTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getVerTs failed: unknown result");

  def getRow(self, tableName, row):
    """
    Get all the data for the specified table and row at the latest
    timestamp. Returns an empty list if the row does not exist.
    
    @param tableName name of table
    @param row row key
    @return TRowResult containing the row and map of columns to TCells
    
    Parameters:
     - tableName
     - row
    """
    self.send_getRow(tableName, row)
    return self.recv_getRow()

  def send_getRow(self, tableName, row):
    self._oprot.writeMessageBegin('getRow', TMessageType.CALL, self._seqid)
    args = getRow_args()
    args.tableName = tableName
    args.row = row
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getRow(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getRow_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getRow failed: unknown result");

  def getRowWithColumns(self, tableName, row, columns):
    """
    Get the specified columns for the specified table and row at the latest
    timestamp. Returns an empty list if the row does not exist.
    
    @param tableName name of table
    @param row row key
    @param columns List of columns to return, null for all columns
    @return TRowResult containing the row and map of columns to TCells
    
    Parameters:
     - tableName
     - row
     - columns
    """
    self.send_getRowWithColumns(tableName, row, columns)
    return self.recv_getRowWithColumns()

  def send_getRowWithColumns(self, tableName, row, columns):
    self._oprot.writeMessageBegin('getRowWithColumns', TMessageType.CALL, self._seqid)
    args = getRowWithColumns_args()
    args.tableName = tableName
    args.row = row
    args.columns = columns
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getRowWithColumns(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getRowWithColumns_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getRowWithColumns failed: unknown result");

  def getRowTs(self, tableName, row, timestamp):
    """
    Get all the data for the specified table and row at the specified
    timestamp. Returns an empty list if the row does not exist.
    
    @param tableName of table
    @param row row key
    @param timestamp timestamp
    @return TRowResult containing the row and map of columns to TCells
    
    Parameters:
     - tableName
     - row
     - timestamp
    """
    self.send_getRowTs(tableName, row, timestamp)
    return self.recv_getRowTs()

  def send_getRowTs(self, tableName, row, timestamp):
    self._oprot.writeMessageBegin('getRowTs', TMessageType.CALL, self._seqid)
    args = getRowTs_args()
    args.tableName = tableName
    args.row = row
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getRowTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getRowTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getRowTs failed: unknown result");

  def getRowWithColumnsTs(self, tableName, row, columns, timestamp):
    """
    Get the specified columns for the specified table and row at the specified
    timestamp. Returns an empty list if the row does not exist.
    
    @param tableName name of table
    @param row row key
    @param columns List of columns to return, null for all columns
    @return TRowResult containing the row and map of columns to TCells
    
    Parameters:
     - tableName
     - row
     - columns
     - timestamp
    """
    self.send_getRowWithColumnsTs(tableName, row, columns, timestamp)
    return self.recv_getRowWithColumnsTs()

  def send_getRowWithColumnsTs(self, tableName, row, columns, timestamp):
    self._oprot.writeMessageBegin('getRowWithColumnsTs', TMessageType.CALL, self._seqid)
    args = getRowWithColumnsTs_args()
    args.tableName = tableName
    args.row = row
    args.columns = columns
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getRowWithColumnsTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getRowWithColumnsTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getRowWithColumnsTs failed: unknown result");

  def mutateRow(self, tableName, row, mutations):
    """
    Apply a series of mutations (updates/deletes) to a row in a
    single transaction.  If an exception is thrown, then the
    transaction is aborted.  Default current timestamp is used, and
    all entries will have an identical timestamp.
    
    @param tableName name of table
    @param row row key
    @param mutations list of mutation commands
    
    Parameters:
     - tableName
     - row
     - mutations
    """
    self.send_mutateRow(tableName, row, mutations)
    self.recv_mutateRow()

  def send_mutateRow(self, tableName, row, mutations):
    self._oprot.writeMessageBegin('mutateRow', TMessageType.CALL, self._seqid)
    args = mutateRow_args()
    args.tableName = tableName
    args.row = row
    args.mutations = mutations
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_mutateRow(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = mutateRow_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    return

  def mutateRowTs(self, tableName, row, mutations, timestamp):
    """
    Apply a series of mutations (updates/deletes) to a row in a
    single transaction.  If an exception is thrown, then the
    transaction is aborted.  The specified timestamp is used, and
    all entries will have an identical timestamp.
    
    @param tableName name of table
    @param row row key
    @param mutations list of mutation commands
    @param timestamp timestamp
    
    Parameters:
     - tableName
     - row
     - mutations
     - timestamp
    """
    self.send_mutateRowTs(tableName, row, mutations, timestamp)
    self.recv_mutateRowTs()

  def send_mutateRowTs(self, tableName, row, mutations, timestamp):
    self._oprot.writeMessageBegin('mutateRowTs', TMessageType.CALL, self._seqid)
    args = mutateRowTs_args()
    args.tableName = tableName
    args.row = row
    args.mutations = mutations
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_mutateRowTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = mutateRowTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    return

  def mutateRows(self, tableName, rowBatches):
    """
    Apply a series of batches (each a series of mutations on a single row)
    in a single transaction.  If an exception is thrown, then the
    transaction is aborted.  Default current timestamp is used, and
    all entries will have an identical timestamp.
    
    @param tableName name of table
    @param rowBatches list of row batches
    
    Parameters:
     - tableName
     - rowBatches
    """
    self.send_mutateRows(tableName, rowBatches)
    self.recv_mutateRows()

  def send_mutateRows(self, tableName, rowBatches):
    self._oprot.writeMessageBegin('mutateRows', TMessageType.CALL, self._seqid)
    args = mutateRows_args()
    args.tableName = tableName
    args.rowBatches = rowBatches
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_mutateRows(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = mutateRows_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    return

  def mutateRowsTs(self, tableName, rowBatches, timestamp):
    """
    Apply a series of batches (each a series of mutations on a single row)
    in a single transaction.  If an exception is thrown, then the
    transaction is aborted.  The specified timestamp is used, and
    all entries will have an identical timestamp.
    
    @param tableName name of table
    @param rowBatches list of row batches
    @param timestamp timestamp
    
    Parameters:
     - tableName
     - rowBatches
     - timestamp
    """
    self.send_mutateRowsTs(tableName, rowBatches, timestamp)
    self.recv_mutateRowsTs()

  def send_mutateRowsTs(self, tableName, rowBatches, timestamp):
    self._oprot.writeMessageBegin('mutateRowsTs', TMessageType.CALL, self._seqid)
    args = mutateRowsTs_args()
    args.tableName = tableName
    args.rowBatches = rowBatches
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_mutateRowsTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = mutateRowsTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    return

  def atomicIncrement(self, tableName, row, column, value):
    """
    Atomically increment the column value specified.  Returns the next value post increment.
    @param tableName name of table
    @param row row to increment
    @param column name of column
    @param value amount to increment by
    
    Parameters:
     - tableName
     - row
     - column
     - value
    """
    self.send_atomicIncrement(tableName, row, column, value)
    return self.recv_atomicIncrement()

  def send_atomicIncrement(self, tableName, row, column, value):
    self._oprot.writeMessageBegin('atomicIncrement', TMessageType.CALL, self._seqid)
    args = atomicIncrement_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.value = value
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_atomicIncrement(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = atomicIncrement_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    raise TApplicationException(TApplicationException.MISSING_RESULT, "atomicIncrement failed: unknown result");

  def deleteAll(self, tableName, row, column):
    """
    Delete all cells that match the passed row and column.
    
    @param tableName name of table
    @param row Row to update
    @param column name of column whose value is to be deleted
    
    Parameters:
     - tableName
     - row
     - column
    """
    self.send_deleteAll(tableName, row, column)
    self.recv_deleteAll()

  def send_deleteAll(self, tableName, row, column):
    self._oprot.writeMessageBegin('deleteAll', TMessageType.CALL, self._seqid)
    args = deleteAll_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_deleteAll(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = deleteAll_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def deleteAllTs(self, tableName, row, column, timestamp):
    """
    Delete all cells that match the passed row and column and whose
    timestamp is equal-to or older than the passed timestamp.
    
    @param tableName name of table
    @param row Row to update
    @param column name of column whose value is to be deleted
    @param timestamp timestamp
    
    Parameters:
     - tableName
     - row
     - column
     - timestamp
    """
    self.send_deleteAllTs(tableName, row, column, timestamp)
    self.recv_deleteAllTs()

  def send_deleteAllTs(self, tableName, row, column, timestamp):
    self._oprot.writeMessageBegin('deleteAllTs', TMessageType.CALL, self._seqid)
    args = deleteAllTs_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_deleteAllTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = deleteAllTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def deleteAllRow(self, tableName, row):
    """
    Completely delete the row's cells.
    
    @param tableName name of table
    @param row key of the row to be completely deleted.
    
    Parameters:
     - tableName
     - row
    """
    self.send_deleteAllRow(tableName, row)
    self.recv_deleteAllRow()

  def send_deleteAllRow(self, tableName, row):
    self._oprot.writeMessageBegin('deleteAllRow', TMessageType.CALL, self._seqid)
    args = deleteAllRow_args()
    args.tableName = tableName
    args.row = row
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_deleteAllRow(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = deleteAllRow_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def deleteAllRowTs(self, tableName, row, timestamp):
    """
    Completely delete the row's cells marked with a timestamp
    equal-to or older than the passed timestamp.
    
    @param tableName name of table
    @param row key of the row to be completely deleted.
    @param timestamp timestamp
    
    Parameters:
     - tableName
     - row
     - timestamp
    """
    self.send_deleteAllRowTs(tableName, row, timestamp)
    self.recv_deleteAllRowTs()

  def send_deleteAllRowTs(self, tableName, row, timestamp):
    self._oprot.writeMessageBegin('deleteAllRowTs', TMessageType.CALL, self._seqid)
    args = deleteAllRowTs_args()
    args.tableName = tableName
    args.row = row
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_deleteAllRowTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = deleteAllRowTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def scannerOpen(self, tableName, startRow, columns):
    """
    Get a scanner on the current table starting at the specified row and
    ending at the last row in the table.  Return the specified columns.
    
    @param columns columns to scan. If column name is a column family, all
    columns of the specified column family are returned.  Its also possible
    to pass a regex in the column qualifier.
    @param tableName name of table
    @param startRow starting row in table to scan.  send "" (empty string) to
                    start at the first row.
    
    @return scanner id to be used with other scanner procedures
    
    Parameters:
     - tableName
     - startRow
     - columns
    """
    self.send_scannerOpen(tableName, startRow, columns)
    return self.recv_scannerOpen()

  def send_scannerOpen(self, tableName, startRow, columns):
    self._oprot.writeMessageBegin('scannerOpen', TMessageType.CALL, self._seqid)
    args = scannerOpen_args()
    args.tableName = tableName
    args.startRow = startRow
    args.columns = columns
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerOpen(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerOpen_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerOpen failed: unknown result");

  def scannerOpenWithStop(self, tableName, startRow, stopRow, columns):
    """
    Get a scanner on the current table starting and stopping at the
    specified rows.  ending at the last row in the table.  Return the
    specified columns.
    
    @param columns columns to scan. If column name is a column family, all
    columns of the specified column family are returned.  Its also possible
    to pass a regex in the column qualifier.
    @param tableName name of table
    @param startRow starting row in table to scan.  send "" (empty string) to
                    start at the first row.
    @param stopRow row to stop scanning on.  This row is *not* included in the
                   scanner's results
    
    @return scanner id to be used with other scanner procedures
    
    Parameters:
     - tableName
     - startRow
     - stopRow
     - columns
    """
    self.send_scannerOpenWithStop(tableName, startRow, stopRow, columns)
    return self.recv_scannerOpenWithStop()

  def send_scannerOpenWithStop(self, tableName, startRow, stopRow, columns):
    self._oprot.writeMessageBegin('scannerOpenWithStop', TMessageType.CALL, self._seqid)
    args = scannerOpenWithStop_args()
    args.tableName = tableName
    args.startRow = startRow
    args.stopRow = stopRow
    args.columns = columns
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerOpenWithStop(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerOpenWithStop_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerOpenWithStop failed: unknown result");

  def scannerOpenWithPrefix(self, tableName, startAndPrefix, columns):
    """
    Open a scanner for a given prefix.  That is all rows will have the specified
    prefix. No other rows will be returned.
    
    @param tableName name of table
    @param startAndPrefix the prefix (and thus start row) of the keys you want
    @param columns the columns you want returned
    @return scanner id to use with other scanner calls
    
    Parameters:
     - tableName
     - startAndPrefix
     - columns
    """
    self.send_scannerOpenWithPrefix(tableName, startAndPrefix, columns)
    return self.recv_scannerOpenWithPrefix()

  def send_scannerOpenWithPrefix(self, tableName, startAndPrefix, columns):
    self._oprot.writeMessageBegin('scannerOpenWithPrefix', TMessageType.CALL, self._seqid)
    args = scannerOpenWithPrefix_args()
    args.tableName = tableName
    args.startAndPrefix = startAndPrefix
    args.columns = columns
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerOpenWithPrefix(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerOpenWithPrefix_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerOpenWithPrefix failed: unknown result");

  def scannerOpenTs(self, tableName, startRow, columns, timestamp):
    """
    Get a scanner on the current table starting at the specified row and
    ending at the last row in the table.  Return the specified columns.
    Only values with the specified timestamp are returned.
    
    @param columns columns to scan. If column name is a column family, all
    columns of the specified column family are returned.  Its also possible
    to pass a regex in the column qualifier.
    @param tableName name of table
    @param startRow starting row in table to scan.  send "" (empty string) to
                    start at the first row.
    @param timestamp timestamp
    
    @return scanner id to be used with other scanner procedures
    
    Parameters:
     - tableName
     - startRow
     - columns
     - timestamp
    """
    self.send_scannerOpenTs(tableName, startRow, columns, timestamp)
    return self.recv_scannerOpenTs()

  def send_scannerOpenTs(self, tableName, startRow, columns, timestamp):
    self._oprot.writeMessageBegin('scannerOpenTs', TMessageType.CALL, self._seqid)
    args = scannerOpenTs_args()
    args.tableName = tableName
    args.startRow = startRow
    args.columns = columns
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerOpenTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerOpenTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerOpenTs failed: unknown result");

  def scannerOpenWithStopTs(self, tableName, startRow, stopRow, columns, timestamp):
    """
    Get a scanner on the current table starting and stopping at the
    specified rows.  ending at the last row in the table.  Return the
    specified columns.  Only values with the specified timestamp are
    returned.
    
    @param columns columns to scan. If column name is a column family, all
    columns of the specified column family are returned.  Its also possible
    to pass a regex in the column qualifier.
    @param tableName name of table
    @param startRow starting row in table to scan.  send "" (empty string) to
                    start at the first row.
    @param stopRow row to stop scanning on.  This row is *not* included
                   in the scanner's results
    @param timestamp timestamp
    
    @return scanner id to be used with other scanner procedures
    
    Parameters:
     - tableName
     - startRow
     - stopRow
     - columns
     - timestamp
    """
    self.send_scannerOpenWithStopTs(tableName, startRow, stopRow, columns, timestamp)
    return self.recv_scannerOpenWithStopTs()

  def send_scannerOpenWithStopTs(self, tableName, startRow, stopRow, columns, timestamp):
    self._oprot.writeMessageBegin('scannerOpenWithStopTs', TMessageType.CALL, self._seqid)
    args = scannerOpenWithStopTs_args()
    args.tableName = tableName
    args.startRow = startRow
    args.stopRow = stopRow
    args.columns = columns
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerOpenWithStopTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerOpenWithStopTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerOpenWithStopTs failed: unknown result");

  def scannerGet(self, id):
    """
    Returns the scanner's current row value and advances to the next
    row in the table.  When there are no more rows in the table, or a key
    greater-than-or-equal-to the scanner's specified stopRow is reached,
    an empty list is returned.
    
    @param id id of a scanner returned by scannerOpen
    @return a TRowResult containing the current row and a map of the columns to TCells.
    @throws IllegalArgument if ScannerID is invalid
    @throws NotFound when the scanner reaches the end
    
    Parameters:
     - id
    """
    self.send_scannerGet(id)
    return self.recv_scannerGet()

  def send_scannerGet(self, id):
    self._oprot.writeMessageBegin('scannerGet', TMessageType.CALL, self._seqid)
    args = scannerGet_args()
    args.id = id
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerGet(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerGet_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerGet failed: unknown result");

  def scannerGetList(self, id, nbRows):
    """
    Returns, starting at the scanner's current row value nbRows worth of
    rows and advances to the next row in the table.  When there are no more
    rows in the table, or a key greater-than-or-equal-to the scanner's
    specified stopRow is reached,  an empty list is returned.
    
    @param id id of a scanner returned by scannerOpen
    @param nbRows number of results to regturn
    @return a TRowResult containing the current row and a map of the columns to TCells.
    @throws IllegalArgument if ScannerID is invalid
    @throws NotFound when the scanner reaches the end
    
    Parameters:
     - id
     - nbRows
    """
    self.send_scannerGetList(id, nbRows)
    return self.recv_scannerGetList()

  def send_scannerGetList(self, id, nbRows):
    self._oprot.writeMessageBegin('scannerGetList', TMessageType.CALL, self._seqid)
    args = scannerGetList_args()
    args.id = id
    args.nbRows = nbRows
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerGetList(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerGetList_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerGetList failed: unknown result");

  def scannerClose(self, id):
    """
    Closes the server-state associated with an open scanner.
    
    @param id id of a scanner returned by scannerOpen
    @throws IllegalArgument if ScannerID is invalid
    
    Parameters:
     - id
    """
    self.send_scannerClose(id)
    self.recv_scannerClose()

  def send_scannerClose(self, id):
    self._oprot.writeMessageBegin('scannerClose', TMessageType.CALL, self._seqid)
    args = scannerClose_args()
    args.id = id
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerClose(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerClose_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    return


class Processor(Iface, TProcessor):
  def __init__(self, handler):
    self._handler = handler
    self._processMap = {}
    self._processMap["enableTable"] = Processor.process_enableTable
    self._processMap["disableTable"] = Processor.process_disableTable
    self._processMap["isTableEnabled"] = Processor.process_isTableEnabled
    self._processMap["compact"] = Processor.process_compact
    self._processMap["majorCompact"] = Processor.process_majorCompact
    self._processMap["getTableNames"] = Processor.process_getTableNames
    self._processMap["getColumnDescriptors"] = Processor.process_getColumnDescriptors
    self._processMap["getTableRegions"] = Processor.process_getTableRegions
    self._processMap["createTable"] = Processor.process_createTable
    self._processMap["deleteTable"] = Processor.process_deleteTable
    self._processMap["get"] = Processor.process_get
    self._processMap["getVer"] = Processor.process_getVer
    self._processMap["getVerTs"] = Processor.process_getVerTs
    self._processMap["getRow"] = Processor.process_getRow
    self._processMap["getRowWithColumns"] = Processor.process_getRowWithColumns
    self._processMap["getRowTs"] = Processor.process_getRowTs
    self._processMap["getRowWithColumnsTs"] = Processor.process_getRowWithColumnsTs
    self._processMap["mutateRow"] = Processor.process_mutateRow
    self._processMap["mutateRowTs"] = Processor.process_mutateRowTs
    self._processMap["mutateRows"] = Processor.process_mutateRows
    self._processMap["mutateRowsTs"] = Processor.process_mutateRowsTs
    self._processMap["atomicIncrement"] = Processor.process_atomicIncrement
    self._processMap["deleteAll"] = Processor.process_deleteAll
    self._processMap["deleteAllTs"] = Processor.process_deleteAllTs
    self._processMap["deleteAllRow"] = Processor.process_deleteAllRow
    self._processMap["deleteAllRowTs"] = Processor.process_deleteAllRowTs
    self._processMap["scannerOpen"] = Processor.process_scannerOpen
    self._processMap["scannerOpenWithStop"] = Processor.process_scannerOpenWithStop
    self._processMap["scannerOpenWithPrefix"] = Processor.process_scannerOpenWithPrefix
    self._processMap["scannerOpenTs"] = Processor.process_scannerOpenTs
    self._processMap["scannerOpenWithStopTs"] = Processor.process_scannerOpenWithStopTs
    self._processMap["scannerGet"] = Processor.process_scannerGet
    self._processMap["scannerGetList"] = Processor.process_scannerGetList
    self._processMap["scannerClose"] = Processor.process_scannerClose

  def process(self, iprot, oprot):
    (name, type, seqid) = iprot.readMessageBegin()
    if name not in self._processMap:
      iprot.skip(TType.STRUCT)
      iprot.readMessageEnd()
      x = TApplicationException(TApplicationException.UNKNOWN_METHOD, 'Unknown function %s' % (name))
      oprot.writeMessageBegin(name, TMessageType.EXCEPTION, seqid)
      x.write(oprot)
      oprot.writeMessageEnd()
      oprot.trans.flush()
      return
    else:
      self._processMap[name](self, seqid, iprot, oprot)
    return True

  def process_enableTable(self, seqid, iprot, oprot):
    args = enableTable_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = enableTable_result()
    try:
      self._handler.enableTable(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("enableTable", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_disableTable(self, seqid, iprot, oprot):
    args = disableTable_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = disableTable_result()
    try:
      self._handler.disableTable(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("disableTable", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_isTableEnabled(self, seqid, iprot, oprot):
    args = isTableEnabled_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = isTableEnabled_result()
    try:
      result.success = self._handler.isTableEnabled(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("isTableEnabled", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_compact(self, seqid, iprot, oprot):
    args = compact_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = compact_result()
    try:
      self._handler.compact(args.tableNameOrRegionName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("compact", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_majorCompact(self, seqid, iprot, oprot):
    args = majorCompact_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = majorCompact_result()
    try:
      self._handler.majorCompact(args.tableNameOrRegionName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("majorCompact", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getTableNames(self, seqid, iprot, oprot):
    args = getTableNames_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getTableNames_result()
    try:
      result.success = self._handler.getTableNames()
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getTableNames", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getColumnDescriptors(self, seqid, iprot, oprot):
    args = getColumnDescriptors_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getColumnDescriptors_result()
    try:
      result.success = self._handler.getColumnDescriptors(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getColumnDescriptors", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getTableRegions(self, seqid, iprot, oprot):
    args = getTableRegions_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getTableRegions_result()
    try:
      result.success = self._handler.getTableRegions(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getTableRegions", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_createTable(self, seqid, iprot, oprot):
    args = createTable_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = createTable_result()
    try:
      self._handler.createTable(args.tableName, args.columnFamilies)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    except AlreadyExists, exist:
      result.exist = exist
    oprot.writeMessageBegin("createTable", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_deleteTable(self, seqid, iprot, oprot):
    args = deleteTable_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = deleteTable_result()
    try:
      self._handler.deleteTable(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("deleteTable", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_get(self, seqid, iprot, oprot):
    args = get_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = get_result()
    try:
      result.success = self._handler.get(args.tableName, args.row, args.column)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("get", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getVer(self, seqid, iprot, oprot):
    args = getVer_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getVer_result()
    try:
      result.success = self._handler.getVer(args.tableName, args.row, args.column, args.numVersions)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getVer", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getVerTs(self, seqid, iprot, oprot):
    args = getVerTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getVerTs_result()
    try:
      result.success = self._handler.getVerTs(args.tableName, args.row, args.column, args.timestamp, args.numVersions)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getVerTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getRow(self, seqid, iprot, oprot):
    args = getRow_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getRow_result()
    try:
      result.success = self._handler.getRow(args.tableName, args.row)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getRow", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getRowWithColumns(self, seqid, iprot, oprot):
    args = getRowWithColumns_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getRowWithColumns_result()
    try:
      result.success = self._handler.getRowWithColumns(args.tableName, args.row, args.columns)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getRowWithColumns", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getRowTs(self, seqid, iprot, oprot):
    args = getRowTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getRowTs_result()
    try:
      result.success = self._handler.getRowTs(args.tableName, args.row, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getRowTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getRowWithColumnsTs(self, seqid, iprot, oprot):
    args = getRowWithColumnsTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getRowWithColumnsTs_result()
    try:
      result.success = self._handler.getRowWithColumnsTs(args.tableName, args.row, args.columns, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getRowWithColumnsTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_mutateRow(self, seqid, iprot, oprot):
    args = mutateRow_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = mutateRow_result()
    try:
      self._handler.mutateRow(args.tableName, args.row, args.mutations)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("mutateRow", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_mutateRowTs(self, seqid, iprot, oprot):
    args = mutateRowTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = mutateRowTs_result()
    try:
      self._handler.mutateRowTs(args.tableName, args.row, args.mutations, args.timestamp)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("mutateRowTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_mutateRows(self, seqid, iprot, oprot):
    args = mutateRows_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = mutateRows_result()
    try:
      self._handler.mutateRows(args.tableName, args.rowBatches)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("mutateRows", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_mutateRowsTs(self, seqid, iprot, oprot):
    args = mutateRowsTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = mutateRowsTs_result()
    try:
      self._handler.mutateRowsTs(args.tableName, args.rowBatches, args.timestamp)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("mutateRowsTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_atomicIncrement(self, seqid, iprot, oprot):
    args = atomicIncrement_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = atomicIncrement_result()
    try:
      result.success = self._handler.atomicIncrement(args.tableName, args.row, args.column, args.value)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("atomicIncrement", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_deleteAll(self, seqid, iprot, oprot):
    args = deleteAll_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = deleteAll_result()
    try:
      self._handler.deleteAll(args.tableName, args.row, args.column)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("deleteAll", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_deleteAllTs(self, seqid, iprot, oprot):
    args = deleteAllTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = deleteAllTs_result()
    try:
      self._handler.deleteAllTs(args.tableName, args.row, args.column, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("deleteAllTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_deleteAllRow(self, seqid, iprot, oprot):
    args = deleteAllRow_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = deleteAllRow_result()
    try:
      self._handler.deleteAllRow(args.tableName, args.row)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("deleteAllRow", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_deleteAllRowTs(self, seqid, iprot, oprot):
    args = deleteAllRowTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = deleteAllRowTs_result()
    try:
      self._handler.deleteAllRowTs(args.tableName, args.row, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("deleteAllRowTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerOpen(self, seqid, iprot, oprot):
    args = scannerOpen_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerOpen_result()
    try:
      result.success = self._handler.scannerOpen(args.tableName, args.startRow, args.columns)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("scannerOpen", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerOpenWithStop(self, seqid, iprot, oprot):
    args = scannerOpenWithStop_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerOpenWithStop_result()
    try:
      result.success = self._handler.scannerOpenWithStop(args.tableName, args.startRow, args.stopRow, args.columns)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("scannerOpenWithStop", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerOpenWithPrefix(self, seqid, iprot, oprot):
    args = scannerOpenWithPrefix_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerOpenWithPrefix_result()
    try:
      result.success = self._handler.scannerOpenWithPrefix(args.tableName, args.startAndPrefix, args.columns)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("scannerOpenWithPrefix", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerOpenTs(self, seqid, iprot, oprot):
    args = scannerOpenTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerOpenTs_result()
    try:
      result.success = self._handler.scannerOpenTs(args.tableName, args.startRow, args.columns, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("scannerOpenTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerOpenWithStopTs(self, seqid, iprot, oprot):
    args = scannerOpenWithStopTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerOpenWithStopTs_result()
    try:
      result.success = self._handler.scannerOpenWithStopTs(args.tableName, args.startRow, args.stopRow, args.columns, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("scannerOpenWithStopTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerGet(self, seqid, iprot, oprot):
    args = scannerGet_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerGet_result()
    try:
      result.success = self._handler.scannerGet(args.id)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("scannerGet", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerGetList(self, seqid, iprot, oprot):
    args = scannerGetList_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerGetList_result()
    try:
      result.success = self._handler.scannerGetList(args.id, args.nbRows)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("scannerGetList", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerClose(self, seqid, iprot, oprot):
    args = scannerClose_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerClose_result()
    try:
      self._handler.scannerClose(args.id)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("scannerClose", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()


# HELPER FUNCTIONS AND STRUCTURES

class enableTable_args(object):
  """
  Attributes:
   - tableName
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('enableTable_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class enableTable_result(object):
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('enableTable_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class disableTable_args(object):
  """
  Attributes:
   - tableName
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('disableTable_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class disableTable_result(object):
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('disableTable_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class isTableEnabled_args(object):
  """
  Attributes:
   - tableName
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('isTableEnabled_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class isTableEnabled_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.BOOL, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.BOOL:
          self.success = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('isTableEnabled_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.BOOL, 0)
      oprot.writeBool(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class compact_args(object):
  """
  Attributes:
   - tableNameOrRegionName
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableNameOrRegionName', None, None, ), # 1
  )

  def __init__(self, tableNameOrRegionName=None,):
    self.tableNameOrRegionName = tableNameOrRegionName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableNameOrRegionName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('compact_args')
    if self.tableNameOrRegionName != None:
      oprot.writeFieldBegin('tableNameOrRegionName', TType.STRING, 1)
      oprot.writeString(self.tableNameOrRegionName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class compact_result(object):
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('compact_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class majorCompact_args(object):
  """
  Attributes:
   - tableNameOrRegionName
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableNameOrRegionName', None, None, ), # 1
  )

  def __init__(self, tableNameOrRegionName=None,):
    self.tableNameOrRegionName = tableNameOrRegionName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableNameOrRegionName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('majorCompact_args')
    if self.tableNameOrRegionName != None:
      oprot.writeFieldBegin('tableNameOrRegionName', TType.STRING, 1)
      oprot.writeString(self.tableNameOrRegionName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class majorCompact_result(object):
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('majorCompact_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getTableNames_args(object):

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getTableNames_args')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getTableNames_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRING,None), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype19, _size16) = iprot.readListBegin()
          for _i20 in xrange(_size16):
            _elem21 = iprot.readString();
            self.success.append(_elem21)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getTableNames_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRING, len(self.success))
      for iter22 in self.success:
        oprot.writeString(iter22)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getColumnDescriptors_args(object):
  """
  Attributes:
   - tableName
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getColumnDescriptors_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getColumnDescriptors_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.MAP, 'success', (TType.STRING,None,TType.STRUCT,(ColumnDescriptor, ColumnDescriptor.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.MAP:
          self.success = {}
          (_ktype24, _vtype25, _size23 ) = iprot.readMapBegin() 
          for _i27 in xrange(_size23):
            _key28 = iprot.readString();
            _val29 = ColumnDescriptor()
            _val29.read(iprot)
            self.success[_key28] = _val29
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getColumnDescriptors_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.MAP, 0)
      oprot.writeMapBegin(TType.STRING, TType.STRUCT, len(self.success))
      for kiter30,viter31 in self.success.items():
        oprot.writeString(kiter30)
        viter31.write(oprot)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getTableRegions_args(object):
  """
  Attributes:
   - tableName
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getTableRegions_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getTableRegions_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRegionInfo, TRegionInfo.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype35, _size32) = iprot.readListBegin()
          for _i36 in xrange(_size32):
            _elem37 = TRegionInfo()
            _elem37.read(iprot)
            self.success.append(_elem37)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getTableRegions_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter38 in self.success:
        iter38.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class createTable_args(object):
  """
  Attributes:
   - tableName
   - columnFamilies
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.LIST, 'columnFamilies', (TType.STRUCT,(ColumnDescriptor, ColumnDescriptor.thrift_spec)), None, ), # 2
  )

  def __init__(self, tableName=None, columnFamilies=None,):
    self.tableName = tableName
    self.columnFamilies = columnFamilies

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.columnFamilies = []
          (_etype42, _size39) = iprot.readListBegin()
          for _i43 in xrange(_size39):
            _elem44 = ColumnDescriptor()
            _elem44.read(iprot)
            self.columnFamilies.append(_elem44)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('createTable_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.columnFamilies != None:
      oprot.writeFieldBegin('columnFamilies', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.columnFamilies))
      for iter45 in self.columnFamilies:
        iter45.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class createTable_result(object):
  """
  Attributes:
   - io
   - ia
   - exist
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'exist', (AlreadyExists, AlreadyExists.thrift_spec), None, ), # 3
  )

  def __init__(self, io=None, ia=None, exist=None,):
    self.io = io
    self.ia = ia
    self.exist = exist

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.exist = AlreadyExists()
          self.exist.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('createTable_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    if self.exist != None:
      oprot.writeFieldBegin('exist', TType.STRUCT, 3)
      self.exist.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteTable_args(object):
  """
  Attributes:
   - tableName
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteTable_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteTable_result(object):
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteTable_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_args(object):
  """
  Attributes:
   - tableName
   - row
   - column
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
  )

  def __init__(self, tableName=None, row=None, column=None,):
    self.tableName = tableName
    self.row = row
    self.column = column

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TCell, TCell.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype49, _size46) = iprot.readListBegin()
          for _i50 in xrange(_size46):
            _elem51 = TCell()
            _elem51.read(iprot)
            self.success.append(_elem51)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter52 in self.success:
        iter52.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getVer_args(object):
  """
  Attributes:
   - tableName
   - row
   - column
   - numVersions
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
    (4, TType.I32, 'numVersions', None, None, ), # 4
  )

  def __init__(self, tableName=None, row=None, column=None, numVersions=None,):
    self.tableName = tableName
    self.row = row
    self.column = column
    self.numVersions = numVersions

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.numVersions = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getVer_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    if self.numVersions != None:
      oprot.writeFieldBegin('numVersions', TType.I32, 4)
      oprot.writeI32(self.numVersions)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getVer_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TCell, TCell.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype56, _size53) = iprot.readListBegin()
          for _i57 in xrange(_size53):
            _elem58 = TCell()
            _elem58.read(iprot)
            self.success.append(_elem58)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getVer_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter59 in self.success:
        iter59.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getVerTs_args(object):
  """
  Attributes:
   - tableName
   - row
   - column
   - timestamp
   - numVersions
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
    (4, TType.I64, 'timestamp', None, None, ), # 4
    (5, TType.I32, 'numVersions', None, None, ), # 5
  )

  def __init__(self, tableName=None, row=None, column=None, timestamp=None, numVersions=None,):
    self.tableName = tableName
    self.row = row
    self.column = column
    self.timestamp = timestamp
    self.numVersions = numVersions

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.I32:
          self.numVersions = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getVerTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 4)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    if self.numVersions != None:
      oprot.writeFieldBegin('numVersions', TType.I32, 5)
      oprot.writeI32(self.numVersions)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getVerTs_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TCell, TCell.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype63, _size60) = iprot.readListBegin()
          for _i64 in xrange(_size60):
            _elem65 = TCell()
            _elem65.read(iprot)
            self.success.append(_elem65)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getVerTs_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter66 in self.success:
        iter66.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRow_args(object):
  """
  Attributes:
   - tableName
   - row
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
  )

  def __init__(self, tableName=None, row=None,):
    self.tableName = tableName
    self.row = row

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRow_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRow_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype70, _size67) = iprot.readListBegin()
          for _i71 in xrange(_size67):
            _elem72 = TRowResult()
            _elem72.read(iprot)
            self.success.append(_elem72)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRow_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter73 in self.success:
        iter73.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowWithColumns_args(object):
  """
  Attributes:
   - tableName
   - row
   - columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.LIST, 'columns', (TType.STRING,None), None, ), # 3
  )

  def __init__(self, tableName=None, row=None, columns=None,):
    self.tableName = tableName
    self.row = row
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.columns = []
          (_etype77, _size74) = iprot.readListBegin()
          for _i78 in xrange(_size74):
            _elem79 = iprot.readString();
            self.columns.append(_elem79)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowWithColumns_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter80 in self.columns:
        oprot.writeString(iter80)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowWithColumns_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype84, _size81) = iprot.readListBegin()
          for _i85 in xrange(_size81):
            _elem86 = TRowResult()
            _elem86.read(iprot)
            self.success.append(_elem86)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowWithColumns_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter87 in self.success:
        iter87.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowTs_args(object):
  """
  Attributes:
   - tableName
   - row
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.I64, 'timestamp', None, None, ), # 3
  )

  def __init__(self, tableName=None, row=None, timestamp=None,):
    self.tableName = tableName
    self.row = row
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 3)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowTs_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype91, _size88) = iprot.readListBegin()
          for _i92 in xrange(_size88):
            _elem93 = TRowResult()
            _elem93.read(iprot)
            self.success.append(_elem93)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowTs_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter94 in self.success:
        iter94.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowWithColumnsTs_args(object):
  """
  Attributes:
   - tableName
   - row
   - columns
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.LIST, 'columns', (TType.STRING,None), None, ), # 3
    (4, TType.I64, 'timestamp', None, None, ), # 4
  )

  def __init__(self, tableName=None, row=None, columns=None, timestamp=None,):
    self.tableName = tableName
    self.row = row
    self.columns = columns
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.columns = []
          (_etype98, _size95) = iprot.readListBegin()
          for _i99 in xrange(_size95):
            _elem100 = iprot.readString();
            self.columns.append(_elem100)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowWithColumnsTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter101 in self.columns:
        oprot.writeString(iter101)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 4)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowWithColumnsTs_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype105, _size102) = iprot.readListBegin()
          for _i106 in xrange(_size102):
            _elem107 = TRowResult()
            _elem107.read(iprot)
            self.success.append(_elem107)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowWithColumnsTs_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter108 in self.success:
        iter108.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRow_args(object):
  """
  Attributes:
   - tableName
   - row
   - mutations
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.LIST, 'mutations', (TType.STRUCT,(Mutation, Mutation.thrift_spec)), None, ), # 3
  )

  def __init__(self, tableName=None, row=None, mutations=None,):
    self.tableName = tableName
    self.row = row
    self.mutations = mutations

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.mutations = []
          (_etype112, _size109) = iprot.readListBegin()
          for _i113 in xrange(_size109):
            _elem114 = Mutation()
            _elem114.read(iprot)
            self.mutations.append(_elem114)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRow_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.mutations != None:
      oprot.writeFieldBegin('mutations', TType.LIST, 3)
      oprot.writeListBegin(TType.STRUCT, len(self.mutations))
      for iter115 in self.mutations:
        iter115.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRow_result(object):
  """
  Attributes:
   - io
   - ia
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, io=None, ia=None,):
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRow_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRowTs_args(object):
  """
  Attributes:
   - tableName
   - row
   - mutations
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.LIST, 'mutations', (TType.STRUCT,(Mutation, Mutation.thrift_spec)), None, ), # 3
    (4, TType.I64, 'timestamp', None, None, ), # 4
  )

  def __init__(self, tableName=None, row=None, mutations=None, timestamp=None,):
    self.tableName = tableName
    self.row = row
    self.mutations = mutations
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.mutations = []
          (_etype119, _size116) = iprot.readListBegin()
          for _i120 in xrange(_size116):
            _elem121 = Mutation()
            _elem121.read(iprot)
            self.mutations.append(_elem121)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRowTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.mutations != None:
      oprot.writeFieldBegin('mutations', TType.LIST, 3)
      oprot.writeListBegin(TType.STRUCT, len(self.mutations))
      for iter122 in self.mutations:
        iter122.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 4)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRowTs_result(object):
  """
  Attributes:
   - io
   - ia
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, io=None, ia=None,):
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRowTs_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRows_args(object):
  """
  Attributes:
   - tableName
   - rowBatches
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.LIST, 'rowBatches', (TType.STRUCT,(BatchMutation, BatchMutation.thrift_spec)), None, ), # 2
  )

  def __init__(self, tableName=None, rowBatches=None,):
    self.tableName = tableName
    self.rowBatches = rowBatches

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.rowBatches = []
          (_etype126, _size123) = iprot.readListBegin()
          for _i127 in xrange(_size123):
            _elem128 = BatchMutation()
            _elem128.read(iprot)
            self.rowBatches.append(_elem128)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRows_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.rowBatches != None:
      oprot.writeFieldBegin('rowBatches', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.rowBatches))
      for iter129 in self.rowBatches:
        iter129.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRows_result(object):
  """
  Attributes:
   - io
   - ia
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, io=None, ia=None,):
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRows_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRowsTs_args(object):
  """
  Attributes:
   - tableName
   - rowBatches
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.LIST, 'rowBatches', (TType.STRUCT,(BatchMutation, BatchMutation.thrift_spec)), None, ), # 2
    (3, TType.I64, 'timestamp', None, None, ), # 3
  )

  def __init__(self, tableName=None, rowBatches=None, timestamp=None,):
    self.tableName = tableName
    self.rowBatches = rowBatches
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.rowBatches = []
          (_etype133, _size130) = iprot.readListBegin()
          for _i134 in xrange(_size130):
            _elem135 = BatchMutation()
            _elem135.read(iprot)
            self.rowBatches.append(_elem135)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRowsTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.rowBatches != None:
      oprot.writeFieldBegin('rowBatches', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.rowBatches))
      for iter136 in self.rowBatches:
        iter136.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 3)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRowsTs_result(object):
  """
  Attributes:
   - io
   - ia
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, io=None, ia=None,):
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRowsTs_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class atomicIncrement_args(object):
  """
  Attributes:
   - tableName
   - row
   - column
   - value
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
    (4, TType.I64, 'value', None, None, ), # 4
  )

  def __init__(self, tableName=None, row=None, column=None, value=None,):
    self.tableName = tableName
    self.row = row
    self.column = column
    self.value = value

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.value = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('atomicIncrement_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    if self.value != None:
      oprot.writeFieldBegin('value', TType.I64, 4)
      oprot.writeI64(self.value)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class atomicIncrement_result(object):
  """
  Attributes:
   - success
   - io
   - ia
  """

  thrift_spec = (
    (0, TType.I64, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, io=None, ia=None,):
    self.success = success
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I64:
          self.success = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('atomicIncrement_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I64, 0)
      oprot.writeI64(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAll_args(object):
  """
  Attributes:
   - tableName
   - row
   - column
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
  )

  def __init__(self, tableName=None, row=None, column=None,):
    self.tableName = tableName
    self.row = row
    self.column = column

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAll_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAll_result(object):
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAll_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllTs_args(object):
  """
  Attributes:
   - tableName
   - row
   - column
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
    (4, TType.I64, 'timestamp', None, None, ), # 4
  )

  def __init__(self, tableName=None, row=None, column=None, timestamp=None,):
    self.tableName = tableName
    self.row = row
    self.column = column
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 4)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllTs_result(object):
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllTs_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllRow_args(object):
  """
  Attributes:
   - tableName
   - row
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
  )

  def __init__(self, tableName=None, row=None,):
    self.tableName = tableName
    self.row = row

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllRow_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllRow_result(object):
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllRow_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllRowTs_args(object):
  """
  Attributes:
   - tableName
   - row
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.I64, 'timestamp', None, None, ), # 3
  )

  def __init__(self, tableName=None, row=None, timestamp=None,):
    self.tableName = tableName
    self.row = row
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllRowTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 3)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllRowTs_result(object):
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllRowTs_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpen_args(object):
  """
  Attributes:
   - tableName
   - startRow
   - columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'startRow', None, None, ), # 2
    (3, TType.LIST, 'columns', (TType.STRING,None), None, ), # 3
  )

  def __init__(self, tableName=None, startRow=None, columns=None,):
    self.tableName = tableName
    self.startRow = startRow
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.startRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.columns = []
          (_etype140, _size137) = iprot.readListBegin()
          for _i141 in xrange(_size137):
            _elem142 = iprot.readString();
            self.columns.append(_elem142)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpen_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.startRow != None:
      oprot.writeFieldBegin('startRow', TType.STRING, 2)
      oprot.writeString(self.startRow)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter143 in self.columns:
        oprot.writeString(iter143)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpen_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpen_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithStop_args(object):
  """
  Attributes:
   - tableName
   - startRow
   - stopRow
   - columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'startRow', None, None, ), # 2
    (3, TType.STRING, 'stopRow', None, None, ), # 3
    (4, TType.LIST, 'columns', (TType.STRING,None), None, ), # 4
  )

  def __init__(self, tableName=None, startRow=None, stopRow=None, columns=None,):
    self.tableName = tableName
    self.startRow = startRow
    self.stopRow = stopRow
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.startRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.stopRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.LIST:
          self.columns = []
          (_etype147, _size144) = iprot.readListBegin()
          for _i148 in xrange(_size144):
            _elem149 = iprot.readString();
            self.columns.append(_elem149)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithStop_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.startRow != None:
      oprot.writeFieldBegin('startRow', TType.STRING, 2)
      oprot.writeString(self.startRow)
      oprot.writeFieldEnd()
    if self.stopRow != None:
      oprot.writeFieldBegin('stopRow', TType.STRING, 3)
      oprot.writeString(self.stopRow)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 4)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter150 in self.columns:
        oprot.writeString(iter150)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithStop_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithStop_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithPrefix_args(object):
  """
  Attributes:
   - tableName
   - startAndPrefix
   - columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'startAndPrefix', None, None, ), # 2
    (3, TType.LIST, 'columns', (TType.STRING,None), None, ), # 3
  )

  def __init__(self, tableName=None, startAndPrefix=None, columns=None,):
    self.tableName = tableName
    self.startAndPrefix = startAndPrefix
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.startAndPrefix = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.columns = []
          (_etype154, _size151) = iprot.readListBegin()
          for _i155 in xrange(_size151):
            _elem156 = iprot.readString();
            self.columns.append(_elem156)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithPrefix_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.startAndPrefix != None:
      oprot.writeFieldBegin('startAndPrefix', TType.STRING, 2)
      oprot.writeString(self.startAndPrefix)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter157 in self.columns:
        oprot.writeString(iter157)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithPrefix_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithPrefix_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenTs_args(object):
  """
  Attributes:
   - tableName
   - startRow
   - columns
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'startRow', None, None, ), # 2
    (3, TType.LIST, 'columns', (TType.STRING,None), None, ), # 3
    (4, TType.I64, 'timestamp', None, None, ), # 4
  )

  def __init__(self, tableName=None, startRow=None, columns=None, timestamp=None,):
    self.tableName = tableName
    self.startRow = startRow
    self.columns = columns
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.startRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.columns = []
          (_etype161, _size158) = iprot.readListBegin()
          for _i162 in xrange(_size158):
            _elem163 = iprot.readString();
            self.columns.append(_elem163)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.startRow != None:
      oprot.writeFieldBegin('startRow', TType.STRING, 2)
      oprot.writeString(self.startRow)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter164 in self.columns:
        oprot.writeString(iter164)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 4)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenTs_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenTs_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithStopTs_args(object):
  """
  Attributes:
   - tableName
   - startRow
   - stopRow
   - columns
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'startRow', None, None, ), # 2
    (3, TType.STRING, 'stopRow', None, None, ), # 3
    (4, TType.LIST, 'columns', (TType.STRING,None), None, ), # 4
    (5, TType.I64, 'timestamp', None, None, ), # 5
  )

  def __init__(self, tableName=None, startRow=None, stopRow=None, columns=None, timestamp=None,):
    self.tableName = tableName
    self.startRow = startRow
    self.stopRow = stopRow
    self.columns = columns
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.startRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.stopRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.LIST:
          self.columns = []
          (_etype168, _size165) = iprot.readListBegin()
          for _i169 in xrange(_size165):
            _elem170 = iprot.readString();
            self.columns.append(_elem170)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithStopTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.startRow != None:
      oprot.writeFieldBegin('startRow', TType.STRING, 2)
      oprot.writeString(self.startRow)
      oprot.writeFieldEnd()
    if self.stopRow != None:
      oprot.writeFieldBegin('stopRow', TType.STRING, 3)
      oprot.writeString(self.stopRow)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 4)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter171 in self.columns:
        oprot.writeString(iter171)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 5)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithStopTs_result(object):
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithStopTs_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerGet_args(object):
  """
  Attributes:
   - id
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'id', None, None, ), # 1
  )

  def __init__(self, id=None,):
    self.id = id

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.id = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerGet_args')
    if self.id != None:
      oprot.writeFieldBegin('id', TType.I32, 1)
      oprot.writeI32(self.id)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerGet_result(object):
  """
  Attributes:
   - success
   - io
   - ia
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, io=None, ia=None,):
    self.success = success
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype175, _size172) = iprot.readListBegin()
          for _i176 in xrange(_size172):
            _elem177 = TRowResult()
            _elem177.read(iprot)
            self.success.append(_elem177)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerGet_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter178 in self.success:
        iter178.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerGetList_args(object):
  """
  Attributes:
   - id
   - nbRows
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'id', None, None, ), # 1
    (2, TType.I32, 'nbRows', None, None, ), # 2
  )

  def __init__(self, id=None, nbRows=None,):
    self.id = id
    self.nbRows = nbRows

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.id = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.nbRows = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerGetList_args')
    if self.id != None:
      oprot.writeFieldBegin('id', TType.I32, 1)
      oprot.writeI32(self.id)
      oprot.writeFieldEnd()
    if self.nbRows != None:
      oprot.writeFieldBegin('nbRows', TType.I32, 2)
      oprot.writeI32(self.nbRows)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerGetList_result(object):
  """
  Attributes:
   - success
   - io
   - ia
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, io=None, ia=None,):
    self.success = success
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype182, _size179) = iprot.readListBegin()
          for _i183 in xrange(_size179):
            _elem184 = TRowResult()
            _elem184.read(iprot)
            self.success.append(_elem184)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerGetList_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter185 in self.success:
        iter185.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerClose_args(object):
  """
  Attributes:
   - id
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'id', None, None, ), # 1
  )

  def __init__(self, id=None,):
    self.id = id

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.id = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerClose_args')
    if self.id != None:
      oprot.writeFieldBegin('id', TType.I32, 1)
      oprot.writeI32(self.id)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerClose_result(object):
  """
  Attributes:
   - io
   - ia
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, io=None, ia=None,):
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerClose_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)



########NEW FILE########
__FILENAME__ = ttypes
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#

from thrift.Thrift import *

from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
try:
  from thrift.protocol import fastbinary
except:
  fastbinary = None


class TCell(object):
  """
  TCell - Used to transport a cell value (byte[]) and the timestamp it was
  stored with together as a result for get and getRow methods. This promotes
  the timestamp of a cell to a first-class value, making it easy to take
  note of temporal data. Cell is used all the way from HStore up to HTable.
  
  Attributes:
   - value
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'value', None, None, ), # 1
    (2, TType.I64, 'timestamp', None, None, ), # 2
  )

  def __init__(self, value=None, timestamp=None,):
    self.value = value
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.value = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('TCell')
    if self.value != None:
      oprot.writeFieldBegin('value', TType.STRING, 1)
      oprot.writeString(self.value)
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 2)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class ColumnDescriptor(object):
  """
  An HColumnDescriptor contains information about a column family
  such as the number of versions, compression settings, etc. It is
  used as input when creating a table or adding a column.
  
  Attributes:
   - name
   - maxVersions
   - compression
   - inMemory
   - bloomFilterType
   - bloomFilterVectorSize
   - bloomFilterNbHashes
   - blockCacheEnabled
   - timeToLive
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'name', None, None, ), # 1
    (2, TType.I32, 'maxVersions', None, 3, ), # 2
    (3, TType.STRING, 'compression', None, "NONE", ), # 3
    (4, TType.BOOL, 'inMemory', None, False, ), # 4
    (5, TType.STRING, 'bloomFilterType', None, "NONE", ), # 5
    (6, TType.I32, 'bloomFilterVectorSize', None, 0, ), # 6
    (7, TType.I32, 'bloomFilterNbHashes', None, 0, ), # 7
    (8, TType.BOOL, 'blockCacheEnabled', None, False, ), # 8
    (9, TType.I32, 'timeToLive', None, -1, ), # 9
  )

  def __init__(self, name=None, maxVersions=thrift_spec[2][4], compression=thrift_spec[3][4], inMemory=thrift_spec[4][4], bloomFilterType=thrift_spec[5][4], bloomFilterVectorSize=thrift_spec[6][4], bloomFilterNbHashes=thrift_spec[7][4], blockCacheEnabled=thrift_spec[8][4], timeToLive=thrift_spec[9][4],):
    self.name = name
    self.maxVersions = maxVersions
    self.compression = compression
    self.inMemory = inMemory
    self.bloomFilterType = bloomFilterType
    self.bloomFilterVectorSize = bloomFilterVectorSize
    self.bloomFilterNbHashes = bloomFilterNbHashes
    self.blockCacheEnabled = blockCacheEnabled
    self.timeToLive = timeToLive

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.maxVersions = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.compression = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.BOOL:
          self.inMemory = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.STRING:
          self.bloomFilterType = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 6:
        if ftype == TType.I32:
          self.bloomFilterVectorSize = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 7:
        if ftype == TType.I32:
          self.bloomFilterNbHashes = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 8:
        if ftype == TType.BOOL:
          self.blockCacheEnabled = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 9:
        if ftype == TType.I32:
          self.timeToLive = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('ColumnDescriptor')
    if self.name != None:
      oprot.writeFieldBegin('name', TType.STRING, 1)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.maxVersions != None:
      oprot.writeFieldBegin('maxVersions', TType.I32, 2)
      oprot.writeI32(self.maxVersions)
      oprot.writeFieldEnd()
    if self.compression != None:
      oprot.writeFieldBegin('compression', TType.STRING, 3)
      oprot.writeString(self.compression)
      oprot.writeFieldEnd()
    if self.inMemory != None:
      oprot.writeFieldBegin('inMemory', TType.BOOL, 4)
      oprot.writeBool(self.inMemory)
      oprot.writeFieldEnd()
    if self.bloomFilterType != None:
      oprot.writeFieldBegin('bloomFilterType', TType.STRING, 5)
      oprot.writeString(self.bloomFilterType)
      oprot.writeFieldEnd()
    if self.bloomFilterVectorSize != None:
      oprot.writeFieldBegin('bloomFilterVectorSize', TType.I32, 6)
      oprot.writeI32(self.bloomFilterVectorSize)
      oprot.writeFieldEnd()
    if self.bloomFilterNbHashes != None:
      oprot.writeFieldBegin('bloomFilterNbHashes', TType.I32, 7)
      oprot.writeI32(self.bloomFilterNbHashes)
      oprot.writeFieldEnd()
    if self.blockCacheEnabled != None:
      oprot.writeFieldBegin('blockCacheEnabled', TType.BOOL, 8)
      oprot.writeBool(self.blockCacheEnabled)
      oprot.writeFieldEnd()
    if self.timeToLive != None:
      oprot.writeFieldBegin('timeToLive', TType.I32, 9)
      oprot.writeI32(self.timeToLive)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class TRegionInfo(object):
  """
  A TRegionInfo contains information about an HTable region.
  
  Attributes:
   - startKey
   - endKey
   - id
   - name
   - version
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'startKey', None, None, ), # 1
    (2, TType.STRING, 'endKey', None, None, ), # 2
    (3, TType.I64, 'id', None, None, ), # 3
    (4, TType.STRING, 'name', None, None, ), # 4
    (5, TType.BYTE, 'version', None, None, ), # 5
  )

  def __init__(self, startKey=None, endKey=None, id=None, name=None, version=None,):
    self.startKey = startKey
    self.endKey = endKey
    self.id = id
    self.name = name
    self.version = version

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.startKey = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.endKey = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.id = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.BYTE:
          self.version = iprot.readByte();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('TRegionInfo')
    if self.startKey != None:
      oprot.writeFieldBegin('startKey', TType.STRING, 1)
      oprot.writeString(self.startKey)
      oprot.writeFieldEnd()
    if self.endKey != None:
      oprot.writeFieldBegin('endKey', TType.STRING, 2)
      oprot.writeString(self.endKey)
      oprot.writeFieldEnd()
    if self.id != None:
      oprot.writeFieldBegin('id', TType.I64, 3)
      oprot.writeI64(self.id)
      oprot.writeFieldEnd()
    if self.name != None:
      oprot.writeFieldBegin('name', TType.STRING, 4)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.version != None:
      oprot.writeFieldBegin('version', TType.BYTE, 5)
      oprot.writeByte(self.version)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class Mutation(object):
  """
  A Mutation object is used to either update or delete a column-value.
  
  Attributes:
   - isDelete
   - column
   - value
  """

  thrift_spec = (
    None, # 0
    (1, TType.BOOL, 'isDelete', None, False, ), # 1
    (2, TType.STRING, 'column', None, None, ), # 2
    (3, TType.STRING, 'value', None, None, ), # 3
  )

  def __init__(self, isDelete=thrift_spec[1][4], column=None, value=None,):
    self.isDelete = isDelete
    self.column = column
    self.value = value

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.BOOL:
          self.isDelete = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.value = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('Mutation')
    if self.isDelete != None:
      oprot.writeFieldBegin('isDelete', TType.BOOL, 1)
      oprot.writeBool(self.isDelete)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 2)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    if self.value != None:
      oprot.writeFieldBegin('value', TType.STRING, 3)
      oprot.writeString(self.value)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class BatchMutation(object):
  """
  A BatchMutation object is used to apply a number of Mutations to a single row.
  
  Attributes:
   - row
   - mutations
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'row', None, None, ), # 1
    (2, TType.LIST, 'mutations', (TType.STRUCT,(Mutation, Mutation.thrift_spec)), None, ), # 2
  )

  def __init__(self, row=None, mutations=None,):
    self.row = row
    self.mutations = mutations

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.mutations = []
          (_etype3, _size0) = iprot.readListBegin()
          for _i4 in xrange(_size0):
            _elem5 = Mutation()
            _elem5.read(iprot)
            self.mutations.append(_elem5)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('BatchMutation')
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 1)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.mutations != None:
      oprot.writeFieldBegin('mutations', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.mutations))
      for iter6 in self.mutations:
        iter6.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class TRowResult(object):
  """
  Holds row name and then a map of columns to cells.
  
  Attributes:
   - row
   - columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'row', None, None, ), # 1
    (2, TType.MAP, 'columns', (TType.STRING,None,TType.STRUCT,(TCell, TCell.thrift_spec)), None, ), # 2
  )

  def __init__(self, row=None, columns=None,):
    self.row = row
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.MAP:
          self.columns = {}
          (_ktype8, _vtype9, _size7 ) = iprot.readMapBegin() 
          for _i11 in xrange(_size7):
            _key12 = iprot.readString();
            _val13 = TCell()
            _val13.read(iprot)
            self.columns[_key12] = _val13
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('TRowResult')
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 1)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.MAP, 2)
      oprot.writeMapBegin(TType.STRING, TType.STRUCT, len(self.columns))
      for kiter14,viter15 in self.columns.items():
        oprot.writeString(kiter14)
        viter15.write(oprot)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class IOError(Exception):
  """
  An IOError exception signals that an error occurred communicating
  to the Hbase master or an Hbase region server.  Also used to return
  more general Hbase error conditions.
  
  Attributes:
   - message
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'message', None, None, ), # 1
  )

  def __init__(self, message=None,):
    self.message = message

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.message = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('IOError')
    if self.message != None:
      oprot.writeFieldBegin('message', TType.STRING, 1)
      oprot.writeString(self.message)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class IllegalArgument(Exception):
  """
  An IllegalArgument exception indicates an illegal or invalid
  argument was passed into a procedure.
  
  Attributes:
   - message
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'message', None, None, ), # 1
  )

  def __init__(self, message=None,):
    self.message = message

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.message = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('IllegalArgument')
    if self.message != None:
      oprot.writeFieldBegin('message', TType.STRING, 1)
      oprot.writeString(self.message)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class AlreadyExists(Exception):
  """
  An AlreadyExists exceptions signals that a table with the specified
  name already exists
  
  Attributes:
   - message
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'message', None, None, ), # 1
  )

  def __init__(self, message=None,):
    self.message = message

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.message = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('AlreadyExists')
    if self.message != None:
      oprot.writeFieldBegin('message', TType.STRING, 1)
      oprot.writeString(self.message)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)


########NEW FILE########
__FILENAME__ = mapper
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from zohmg.config import Config

# exploding mapper!
# every emitted record from the usermapper is expanded
# to len(projections) * len(units) * 2^len(reduced) records.
#
# the usermapper yields tuples of the form (ts, dimensions, units).
# this mapper wrapper turns them into tuples of the form:
# ((ts, p, permut, unit), value).  er, read the code please.
class Mapper(object):
    def __init__(self, usermapper, projections=None):
        self.usermapper = usermapper
        if projections == None:
            projections = Config().projections()
        self.projections = projections

    # helper for generating (per)mutations of a dictionary.
    # returns a list of 2**len(input) number of dicts, like so:
    # {'a':'x', 'b':'y'} => [{'a':'x', 'b':'y'}, {'a':'x', 'b':'all'},
    #                        {'a':'all', 'b':'y'}, {'a':'all', 'b':'all'}]
    def dict_permutations(self, dict_):
        dict = dict_.copy()

        # base case.
        if len(dict) == 1:
            all_dict = {dict.keys()[0] : 'all'}
            # dict     => {'agent': 'firefox'}
            # all_dict => {'agent': 'all'}
            return [dict, all_dict]


        # pop head, recurse on tail.
        x  = dict.popitem()
        xs = self.dict_permutations(dict)

        # combine x and xs into a list.
        permuts = []
        for k,v in [x, (x[0], 'all')]:
            # k => 'agent'
            # v => 'firefox' andor 'all'
            for b in xs:
                # b => {'http-status': '200', 'country': 'SE'}
                # add {'agent':'firefox'} andor {'agent':'all'} to b.
                b[k] = v
                permuts.append(b.copy())
        return permuts

    # wrapper around the user's mapper.
    def __call__(self, key, value):
        # from the usermapper: a timestamp, a point in n-space, units and their values.
        for (timestamp, dimensions, units) in self.usermapper(key, value):
            for projection in self.projections:
                # for example, if projection => ('user', 'artist')
                # and dimensions => {'user':100, 'artist':2002, 'track':822010}
                # then reduced => {'user':100, 'artist':2002}
                reduced = {}
                for d in projection:  # dimensionality reduction.
                    reduced[d] = dimensions[d]
                for unit in units:
                    value = units[unit]
                    permutations = self.dict_permutations(reduced)
                    # if reduced => {'user':100, 'artist':2002}
                    # then permutations => [{'user':100, 'artist':2002},
                    #                        {'user':100, 'artist':'all'},
                    #                        {'user':'all', 'artist':2002},
                    #                        {'user':'all', 'artist':'all'}]
                    for permut in permutations:
                        yield (timestamp, projection, permut, unit), value

########NEW FILE########
__FILENAME__ = data
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# MIDDLEWARE DATA HELLO.

import os, sys, time
import simplejson as json

from paste.request import parse_formvars

import zohmg.data
from zohmg.config import Config

def json_of(error_msg='wha?', status_code=400, callback=None):
    structure = {'error_msg': error_msg, 'status_code': status_code}
    jsondata = json.dumps(structure)
    if callback:
        return callback+"("+jsondata+")"
    else:
        return jsondata

# data application serving at /data.
class data(object):
    def __init__(self, dataset=None, projections=None):
        if dataset == None or projections == None:
            config = Config()

        if dataset == None:
            self.table = config.dataset()
        else:
            self.table = dataset

        if projections == None:
            self.projections = config.projections()
        else:
            self.projections = projections

    # answer query.
    def __call__(self, environ, start_response):
        mime_type = 'text/plain' # under what type we serve json.
        content_type = [('content-type', mime_type)]

        # TODO: check that table exists, exit gracefully if not.

        # interpret the environment.
        params = parse_formvars(environ)

        # error callback?
        # (hm! can not do json error callbacks on error codes other than 200.)
        try:    errorcallback = params['jsonperror']
        except: errorcallback = None

        try:
            # hbase query.
            start = time.time()
            json = zohmg.data.query(self.table, self.projections, params)

        except zohmg.data.DataNotFound, (instance):
            print >>sys.stderr, "Data not found: ", instance.error
            start_response('200 OK', content_type)
            return json_of("data not found: " + instance.error, 200, errorcallback)

        except zohmg.data.MissingArguments, (instance):
            print >>sys.stderr, "400 Bad Request: missing arguments."
            #start_response('400 Bad Request', content_type)
            start_response('200 OK', content_type)
            return json_of("Query is missing arguments: " + instance.error, 400, errorcallback)
            # TODO: print list of required arguments.

        except zohmg.data.NoSuitableProjection, (instance):
            print >>sys.stderr, "400 Bad Request: No suitable projection. ", instance.error
            #start_response('400 Bad Request', content_type)
            start_response('200 OK', content_type)
            return json_of(" " + instance.error, 400, errorcallback)

        except Exception, e:
            print >>sys.stderr, "Error: ", e
            #start_response('500 Internal Server Error', content_type)
            start_response('200 OK', content_type)
            return json_of("egads!, I failed in serving you: " + str(e), 500, errorcallback)

        elapsed = (time.time() - start)
        sys.stderr.write("hbase query+prep: %s\n\n" % elapsed)

        # serve output.
        start_response('200 OK', content_type) # or text/x-json
        return json

########NEW FILE########
__FILENAME__ = graph
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import time

class graph(object):
    """
    This application serves static files from the 'graph' directory in share.
    """
    def __call__(self, environ, start_response):
        from paste.urlparser import make_static
        # TODO: all hardcoded paths *will* break eventually.
        graph_dir = '/usr/local/share/zohmg/graph'
        graph = make_static({}, graph_dir)
        return graph(environ, start_response)

########NEW FILE########
__FILENAME__ = static
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import time

class static(object):
    """
    Application that serves static files from the 'static' directory in the
    project directory.
    """
    def __call__(self, environ, start_response):
        from paste.urlparser import make_static
        project_dir = environ['zohmg_project_dir']
        static = make_static({}, project_dir + '/static')
        return static(environ, start_response)

########NEW FILE########
__FILENAME__ = transform
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os, sys, time
import simplejson as json
from zohmg.config import Config

# add middleware dir and import data_utils.
sys.path.append(os.path.dirname(__file__))
import data_utils

# TODO: use this.
class transform(object):
    def __init__(self):
        self.config = Config()
        self.table = self.config.dataset()
        self.projections = self.config.projections()

    def __call__(self,environ,start_response):
        project_dir = environ["zohmg_project_dir"]
        url_parts = environ["PATH_INFO"][1:-1].split("/") # trim pre- and appending /

        print "[%s] Transform, serving from %s." % (time.asctime(),project_dir)

        if len(url_parts) > 1:
            start_response("404 Not Found",[("Content-type","text/html")])
            return "Too many levels in path: %s." % environ["PATH_INFO"]
        else:
            # import user transformer.
            sys.path.append(project_dir) # add cwd so we can import from there.
            usertransformer = __import__("transformers/"+url_parts[0])
            transform = usertransformer.transform

        payload = data_utils.hbase_get(self.table,self.projections,environ)
        if payload:
            start_response("200 OK",[("Content-type","text/html")])
            return data_utils.dump_jsonp(transform(payload))
        else:
            start_response("404 Not Found",[("Content-type","text/html")])
            return "Bad query or no data found."

########NEW FILE########
__FILENAME__ = process
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from zohmg.config import Config, Environ
from zohmg.utils import fail
import sys, os, re

class Process(object):
    def go(self, mapper, input, for_dumbo):
        local_mode = False # default: run jobs on Hadoop.
        local_output_path = '/tmp/zohmg-output' # TODO: make user configurable.

        table = Config().dataset()
        jobname = "%s %s" % (table, input) # overrides any name specified on cli.

        resolver = 'fm.last.darling.hbase.HBaseIdentifierResolver'
        outputformat = 'org.apache.hadoop.hbase.mapreduce.TableOutputFormat'

        opts = [('jobconf', "hbase.mapred.outputtable=" + table),
                ('jobconf', 'stream.io.identifier.resolver.class=' + resolver),
                ('streamoutput', 'hbase'), # resolved by identifier.resolver
                ('outputformat', outputformat),
                ('input', input),
                ('file', 'lib/usermapper.py'), # TODO: handle this more betterer.
                ('name', jobname)
               ]

        # add zohmg-*.egg
        zohmg_egg = [z for z in sys.path if "zohmg" in z][0]
        opts.append(('libegg', zohmg_egg))

        # add files to the jobjar from these paths
        jar_path = '/usr/local/lib/zohmg/jar'
        egg_path = '/usr/local/lib/zohmg/egg'
        directories = ["config", "lib", jar_path, egg_path]
        file_opts = self.__add_files(directories)
        opts.extend(file_opts)

        ## check extra arguments.
        # TODO: allow for any order of extra elements.
        #       as it stands, --local must be specified before --lzo.
        # first, check for '--local'
        if len(for_dumbo) > 0 and for_dumbo[0] == '--local':
            local_mode = True
            for_dumbo.pop(0) # remove '--local'.
        # check for '--lzo' as first extra argument.
        if len(for_dumbo) > 0 and for_dumbo[0] == '--lzo':
            print 'lzo mode: enabled.'
            opts.append(('inputformat', 'org.apache.hadoop.mapred.LzoTextInputFormat'))
            for_dumbo.pop(0) # remove '--lzo'.

        env = Environ()

        if local_mode:
            print 'local mode: enabled.'
            opts.append(('output', local_output_path))
        else:
            print 'hadoop mode: enabled.'
            hadoop_home = env.get("HADOOP_HOME")
            if not os.path.isdir(hadoop_home):
                msg = "error: HADOOP_HOME in config/environment.py is not a directory."
                fail(msg)
            opts.append(('output', '/tmp/does-not-matter'))
            opts.append(('hadoop', hadoop_home))

        # add jars defined in config/environment.py to jobjar.
        classpath = env.get("CLASSPATH")
        if classpath is not None:
            for jar in classpath:
                if not os.path.isfile(jar):
                    msg = "error: jar defined in config/environment is not a file: %s." % jar
                    fail(msg)
                else:
                    print 'import: adding %s to jobjar.' % jar
                    opts.append(('libjar', jar))
        else:
            msg = "error: CLASSPATH in config/environment is empty."
            fail(msg)

        # stringify arguments.
        opts_args = ' '.join("-%s '%s'" % (k, v) for (k, v) in opts)
        more_args = ' '.join(for_dumbo) # TODO: is this necessary?
        dumboargs = "%s %s" % (opts_args, more_args)
        print "giving dumbo these args: " + dumboargs

        # link-magic for usermapper.
        usermapper = os.path.abspath(".") + "/lib/usermapper.py"
        if os.path.isfile(usermapper):
            # TODO: need to be *very* certain we're not unlinking the wrong file.
            os.unlink(usermapper)
        # TODO: SECURITY, need to be certain that we symlink correct file.
        # TODO: borks if lib directory does not exist.
        os.symlink(mapper, usermapper)

        # let the user know what will happen.
        if local_mode:
            print 'doing local run.'
            print 'data will not be imported to hbase.'
            print 'output is at ' + local_output_path

        # dispatch.
        # PYTHONPATH is added because dumbo makes a local run before
        # engaging with hadoop.
        os.system("PYTHONPATH=lib dumbo start /usr/local/lib/zohmg/mapred/import.py " + dumboargs)


    # reads directories and returns list of tuples of
    # file/libegg/libjar options for dumbo.
    def __add_files(self,dirs):
        opts = []
        # TODO: optimize? this is now O(dirs*entries*files).
        for dir in dirs:
            for entry in os.walk(dir):
                dir,dirnames,files = entry
                # for each file add it with correct option.
                for file in files:
                    if not os.path.isfile(dir+"/"+file):
                        msg = "error: File not found, %s." % file
                        fail(msg)

                    suffix = file.split(".")[-1]
                    option = None
                    if   suffix == "egg":  option = "libegg"
                    elif suffix == "jar":  option = "libjar"
                    elif suffix == "py":   option = "file"
                    elif suffix == "yaml": option = "file"

                    if option:
                        print 'import: adding %s to jobjar.' % file
                        opts.append((option, dir+"/"+file))
                    else:
                        print "import: ignoring " + dir+'/'+file
        return opts

########NEW FILE########
__FILENAME__ = reducer
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from zohmg.config import Config
import simplejson as json

# the output of this reducer is interpreted by HBaseOutputReader.
class Reducer(object):
    def __init__(self):
        self.config = Config()

    def __call__(self, key, values):
        timestamp, projection, dimensions, unit = key
        value = sum(values)

        if value == 0:
            return

        # encode dimensions and their attributes in the rowkey.
        # (it's important that we get the ordering right.)
        rowkeyarray = []
        for d in projection:
            rowkeyarray.append(d)
            rowkeyarray.append(dimensions[d])
        rowkeyarray.append(str(timestamp))
        rowkey = '-'.join(rowkeyarray)
        # rowkey => 'artist-97930-track-102203-20090601'

        columnfamily = "unit:"
        cfq = columnfamily + unit
        # cfq => 'unit:scrobbles'

        json_payload = json.dumps({cfq : {'value': value}})
        # json_payload => '{"unit:scrobbles": {"value": 1338}}'

        yield rowkey, json_payload

########NEW FILE########
__FILENAME__ = reset
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import sys
from zohmg.setup import Setup
from zohmg.config import Config
from zohmg.hbase import ZohmgHBase
from hbase_thrift.ttypes import IOError

class Reset(object):
    def please(self):
        host = 'localhost'
        table = Config().dataset()

        # confirm.
        print "reset will *wipe all data* in dataset '%s'." % table
        print "ARE YOU QUITE SURE? ('yes' to confirm.)"

        try:
            response = sys.stdin.readline().strip()
            if response.lower() not in ["yes", "yes!"]:
                print 'phew!'
                sys.exit(0)
        except KeyboardInterrupt:
            print 'hyorgh!'
            sys.exit(0)

        # disable+drop.
        try:
            print "ok, wiping!"
            ZohmgHBase.delete_table(table)
            # recreate.
            print
            print "recreating."
            Setup().go()
        except Exception, e:
            print 'reset failed :-('
            print 'error: ' + str(e)
            sys.exit(1)

        print
        print "%s reset'd" % table


########NEW FILE########
__FILENAME__ = scanner
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# lfm.data.hbase

from hbase import Hbase
from hbase.ttypes import *

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol  import TBinaryProtocol


# the default behaviour is to scan over all rows
# and return all column families.

class HBaseScanner(object):
#
# Public interface
#

    def __init__(self, h="localhost", p=9090):
        self.host  = h
        self.port  = p
        # these are private
        self.__transport = None
        self.__client    = None
        self.__scannerid = None
        self.__next_row  = None


    def connect(self):
        self.__transport = TSocket.TSocket(self.host, self.port)
        self.__transport = TTransport.TBufferedTransport(self.__transport)
        protocol = TBinaryProtocol.TBinaryProtocol(self.__transport)
        self.__client = Hbase.Client(protocol)
        self.__transport.open()


    def disconnect(self):
        self.__transport.close()


    # opens a scanner and pre-fetches the first row.
    # arguments:
    #   table: the only mandatory argument.
    #   columns: list of column families with optional qualifier.
    #            also accepts a string argument defining a single cfq.
    #   startrow: string defining where to start the scan. will scan all rows if omitted.
    #   stoprow: row key to stop at. the row matching this will be excluded from scan.
    #            will scan to end of table if omitted.
    def open(self, table, columns=[], startrow="", stoprow=""):
        # if columns argument is a string, make into one-element list.
        if columns.__class__ == str:
            columns = [columns]

        # TODO: why does this not work?
        # match all CF's with a regexp, like so:
        #if columns == [] or columns == "":
        #    columns = ["/*/:"] # match all column families.

        try:
            if stoprow == "":
                self.__scannerid = self.__client.scannerOpen(table, startrow, columns)
            else:
                self.__scannerid = self.__client.scannerOpenWithStop(table, startrow, stoprow, columns)
        except IOError:
            # TODO: describe what went wrong, if possible.
            raise ScannerError

        # pre-fetch the first row.
        self.__fetch_row()


    def scanner_ready(self):
        return self.__scannerid != None


    # next/has_next iterator style interface.
    def has_next(self):
        return self.__next_row != None


    def next(self):
        if (not self.scanner_ready()) or (not self.has_next()):
            raise StopIteration
        r = self.__next_row
        self.__fetch_row()
        return r


    # TODO: Make this work.
    # Exception based generator style interface.
    def scan(self):
        try:
            while 1:
                r = self.__next_row
                self.__fetch_row()
                yield r
        except StopIteration:
            raise # No more rows.



#
# Private interface
#

    # only used internally since HBaseScanner raises StopIteration when done.
    def __fetch_row(self):
        try:
            # TODO: scannerGetList() for caching.
            self.__next_row = self.__client.scannerGet(self.__scannerid)
        except IOError:
            raise RowFetchError
        # TODO:
        # the new API returns a list; the empty list implies the old NotFound exception.
        except NotFound:
            # scanner finished, presumably.
            self.__scannerid  = None
            self.__next_row = None
            # TODO: Leaving this out for now.
            #raise StopIteration


#
# Exceptions
#
class RowFetchError(Exception):
    def __init__(self,value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

class ScannerError(Exception):
    pass

########NEW FILE########
__FILENAME__ = server
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import time


# There are three points of servitude:
#  /data
#  /static
#  /transformers (soon)
#
# Each of them are served by a class in +middleware_dir+.
# 


# TODO: middleware app directory is hard wired.
# TODO: why must we read files from file system? why not import the classes we need?
class Dispatch(object):
    def __init__(self, project_dir):
        from paste.urlparser import make_url_parser
        self.project_dir = project_dir
        self.middleware_dir = "/usr/local/lib/zohmg/middleware"
        self.dispatch = make_url_parser({}, self.middleware_dir, "")
        print "[%s] Initialized dispatcher. Serving from %s." % (time.asctime(), project_dir)

    def __call__(self, environ, start_response):
        environ["zohmg_project_dir"] = self.project_dir
        return self.dispatch(environ, start_response)

# returns a tuple of the default values.
def defaults():
    # host, port.
    return ('localhost', 8086)

# entry point.
def start(project_dir, host="localhost", port=8086):
    from paste import httpserver
    app = Dispatch(project_dir)
    httpserver.serve(app, host=host, port=port)

########NEW FILE########
__FILENAME__ = utils
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import string, sys, time
from random import Random

def random_string(size):
    # subopt for larger sizes.
    if size > len(string.letters):
        return random_string(size/2)+random_string(size/2)
    return ''.join(Random().sample(string.letters, size))


def timing(func):
    def wrapper(*arg):
        t0 = time.time()
        r = func(*arg)
        elapsed = time.time() - t0
        return (elapsed*1000.00)
    return wrapper


def timing_p(func):
    def wrapper(*arg):
        t0 = time.time()
        r = func(*arg)
        elapsed = (time.time() - t0) * 1000.00
        print "=> %.2f ms" % elapsed
        return elapsed
    return wrapper

#
# General helpers
#
def compare_triples(p, q):
    """
    p and q are triples, like so: (4, 2, ..)
    sort by first the element, then by the second. don't care about the third element.
    return 1, 0, or -1 if p is larger than, equal to, or less than q, respectively.
    """
    a, b, dontcare = p
    x, y, dontcare = q
    if a > x: return  1
    if a < x: return -1
    if b > y: return  1
    if b < y: return -1
    return 0


def fail(msg,errno=1):
    print >>sys.stderr, msg
    exit(errno)


# strip whitespaces.
def strip(str):
    return str.strip()

########NEW FILE########
__FILENAME__ = moretestdata
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

#!/usr/bin/python
from random import random
from hbase.ttypes import *


def setup_transport(host):
  from thrift import Thrift
  from thrift.transport import TSocket
  from thrift.transport import TTransport
  from thrift.protocol import TBinaryProtocol
  from hbase import Hbase
  transport = TSocket.TSocket(host, 9090)
  transport = TTransport.TBufferedTransport(transport)
  protocol = TBinaryProtocol.TBinaryProtocol(transport)
  client = Hbase.Client(protocol)
  transport.open()
  return client, transport


# set up some test data. should be quick.

table = 'webmetrics'

units = ['bytes', 'pageviews']
scaling = {'bytes': 1000, 'pageviews': 5}

countries = ['US', 'SE', 'DE', 'ES', 'GB', 'FR', 'IT', 'DK', 'all']
usertypes = ['anon', 'user', 'all']
agents = ['ff', 'ie', 'safari', 'opera', 'all']

hashes = {} # pre-compute country hashes.
for c in countries: hashes[c] = hash(c) % 255

client, transport = setup_transport('localhost')

for year in range(2009, 2010):
    year = str(year)
    for month in range(1,13):
        month = "%02d" % month
        for day in range(1,31):
            ymd = year + month + "%02d" % day
            for unit in units:
                rk = unit + "-" + ymd
                mutations = []
                # no sparseness here!
                for c in countries:
                    for u in usertypes:
                        for a in agents:
                            m = {}
                            q = '-'.join([c,u,a])
                            m['column'] = "country-usertype-useragent:"+q
                            extra_scaling = 1
                            if 'all' in [c,u,a]: extra_scaling = 20
                            m['value']  = str(int(random() * hashes[c] * scaling[unit] * extra_scaling))
                            mutations.append(Mutation(m))
                print rk + " +> " + str(len(mutations)) + " mutations."
                client.mutateRow(table, rk, mutations)

transport.close()

########NEW FILE########
__FILENAME__ = testdata-500k
#!/usr/bin/env python
# these here programming codes are licensed under the gnu fearsome dude license.

# 1: hbase(main):001:0> create '500k-test', 'unit:'
# 2: $> hbase thrift start
# 3: $> python testdata-500k.py (~500 seconds on my hackintosh)

from random import random

from hbase import Hbase
from hbase.ttypes import *

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

def setup_thrift_transport(host):
  transport = TSocket.TSocket(host, 9090)
  transport = TTransport.TBufferedTransport(transport)
  protocol = TBinaryProtocol.TBinaryProtocol(transport)
  client = Hbase.Client(protocol)
  transport.open()
  return client, transport

def write_data(client, table, n):
    """writes n rows."""
    rowkey_base = "artist-100-track-"
    ymd = '20090618'
    for trackid in range(0, n+1):
        trackid_padded = "%08d" % trackid
        rowkey = rowkey_base + trackid_padded + '-' + ymd
        mutations = []
        m = {}
        m['column'] = 'unit:' + 'scrobbles'
        m['value']  = str(int(random() * 120))
        mutations.append(Mutation(m))
        if (trackid % 1000 == 0):
            print '=> ' + rowkey
        client.mutateRow(table, rowkey, mutations)

if __name__ == '__main__':
    client, transport = setup_thrift_transport('localhost')
    write_data(client, '500k-test', 500000)
    transport.close()

########NEW FILE########
__FILENAME__ = testdata-submissions
#!/usr/bin/env python
# these here programming codes are licensed under the gnu fearsome dude license.

from random import random

from hbase import Hbase
from hbase.ttypes import *

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

def setup_thrift_transport(host):
  transport = TSocket.TSocket(host, 9090)
  transport = TTransport.TBufferedTransport(transport)
  protocol = TBinaryProtocol.TBinaryProtocol(transport)
  client = Hbase.Client(protocol)
  transport.open()
  return client, transport


table = 'submissions-test'

units = ['scrobbles', 'loves']
scaling = {'scrobbles': 100, 'loves': 2}

dimensions  = ['user', 'artist', 'track', 'album']
projections = [('user'), ('artist', 'track'), ('user','artist','track','album')]

year="2009"
months = range(0, 12)
days   = range(0, 30)


# possible attribute values.
attrs = {'users':   [120, 240, 360],
         'artists': [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008],
         'track':   range(0,512),
         'album':   range(0,64)}



def random_attribute_of(dimension):
    try:
        possible = attrs[dimension]
    except:
        print 'oh noes.'
        return '0.'
    r = int(random(len(possible)))
    attr = possible[r]
    return attr
        

def magic_precomputation():
    # so as to not make the distribution entirely random.
    hashes = {}
    for dimension in attrs.keys():
        hashes[dimension] = {}
        for attr in attrs[dimension]:
            hashes[dimension][attr] = hash(attr) % 255
    return hashes

def magic_computation(unit, dimension):
    return random() * hashes[dimension] * scaling[unit]

def generate_data(client):
    for month in months:
        month = "%02d" % (month+1)
        for day in days:
            ymd = year + month + "%02d" % day
            for projection in projections:
                rowkeyarray = []
                for dimension in projection:
                    rowkeyarray.append(dimension)
                    rowkeyarray.append(random_attribute_of(dimension)) # random.
                    rowkeyarray.append(ymd)
                    rowkey = '-'.join(rowkeyarray)
                    print 'rocknroll, know what im sayin: ' + rowkey

                    mutations = []
                    for unit in units:
                        m = {}
                        m['column'] = "unit:" + unit
                        m['value']  = str(int(magic_computation(unit, dimension)))
                        mutations.append(Mutation(m))
                    print rowkey + " +> " + str(len(mutations)) + " mutations."
                    #client.mutateRow(table, rowkey, mutations)


if __name__ == '__main__':
    client, transport = setup_thrift_transport('localhost')

    hashes = magic_precomputation()
    generate_data(client)

    transport.close()

########NEW FILE########
__FILENAME__ = testdata
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

#!/usr/bin/python
from random import random
from hbase.ttypes import *


def setup_transport(host):
  from thrift import Thrift
  from thrift.transport import TSocket
  from thrift.transport import TTransport
  from thrift.protocol import TBinaryProtocol
  from hbase import Hbase
  transport = TSocket.TSocket(host, 9090)
  transport = TTransport.TBufferedTransport(transport)
  protocol = TBinaryProtocol.TBinaryProtocol(transport)
  client = Hbase.Client(protocol)
  transport.open()
  return client, transport


# set up some test data. should be quick.

table = 'webmetrics'

units = ['bytes', 'pageviews']
scaling = {'bytes': 1000, 'pageviews': 5}

countries = ['US', 'SE', 'DE', 'ES', 'GB', 'FR', 'IT', 'DK']
hashes = {} # pre-compute country hashes.
for c in countries:
    hashes[c] = hash(c) % 255

client, transport = setup_transport('localhost')

def magic_computation(unit, dimension):
    return random() * hashes[dimension] * scaling[unit]



year="2009"
for month in range(1,13):
    month = "%02d" % month
    for day in range(1,31):
        ymd = year + month + "%02d" % day
        for unit in units:    
            rk = unit + "-" + ymd
            mutations = []
            for country in countries:
                m = {}
                m['column'] = "country:" + country
                m['value']  = str(int(magic_computation(unit, country)))
                mutations.append(Mutation(m))
            print rk + " +> " + str(len(mutations)) + " mutations."
            client.mutateRow(table, rk, mutations)

transport.close()

########NEW FILE########
__FILENAME__ = test_config
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import unittest
from zohmg.config import Config

class TestConfig(unittest.TestCase):
    def test_sanity_check(self):
        # a few broken configurations,
        for x in ['a','b', 'c']:
            dataset = 'tests/fixtures/dataset-broken-%s.yaml' % x
            self.assertRaises(SystemExit, Config, dataset)
        # and a good one.
        dataset = 'tests/fixtures/dataset-ok.yaml'
        c = Config(dataset)
        self.assertEqual(c.sanity_check(), True)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_data
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import unittest
import zohmg.data

class TestData(unittest.TestCase):
    def test_find_suitable_projection(self):
        projections = [['user'], ['user','artist'], ['artist', 'user']]

        ## find_suitable_projection() should:

        # find the correct projection when there's a single matching projection.
        p = zohmg.data.find_suitable_projection(projections, 'user', {})
        self.assertEqual(p, ['user'])

        # get the ordering right - both ['user','artist'] and ['artist', 'user']
        # satisfy a query for 'artist', but the latter is more efficient to read from.
        p = zohmg.data.find_suitable_projection(projections, 'artist', {})
        self.assertEqual(p, ['artist', 'user'])

        # return None if there is no match.
        p = zohmg.data.find_suitable_projection(projections, 'non-existant', {})
        self.assertEqual(p, None)

    def test_dump_jsonp(self):
        json = zohmg.data.dump_jsonp([{'a':'x', 'something':700}])
        expected = '[{"a": "x", "something": 700}]'
        self.assertEquals(json, expected)

    def test_query(self):
        # call query() with no arguments.
        from zohmg.data import MissingArguments
        self.assertRaises(MissingArguments, zohmg.data.query, 'no-table', [], {})

        # TODO:
        # query servers json.
        # sometimes jsonp.


    def test_scan(self):
        # TODO: mock scanner, assert correctness of scan().
        pass


    def test_hbase_get(self):
        table = 'test' # must there be test data, then?
        projections = [['user']]
        params = {}


        #        r = zohmg.data.hbase_get(table, projections, params)
        #        self.assert_equal(r, 'wha?')



    def test_rowkey_formatter(self):
        projection = ['user']
        d0 = 'user'
        d0v = ['']
        filters = {}
        t0 = "20090601"
        t1 = "20090631"

        expected_startrow = "user-all-20090601"
        expected_stoprow  = "user-all-20090631~"

        startrow, stoprow = zohmg.data.rowkey_formatter(projection, d0, d0v, filters, t0, t1)

        self.assertEquals(startrow, expected_startrow)
        self.assertEquals(stoprow, expected_stoprow)

    def test_rowkey_interpreter(self):
        rowkey = 'artist-97930-track-102203-20090601'
        expected = ('20090601', {'artist': '97930', 'track': '102203'})
        self.assertEqual(expected, zohmg.data.rowkey_interpreter(rowkey))

        rowkey = 'artist-97930-track-102203-20090601223000'
        expected = ('20090601223000', {'artist': '97930', 'track': '102203'})
        self.assertEqual(expected, zohmg.data.rowkey_interpreter(rowkey))


    def test_dict_addition(self):
        a = {'x': 1, 'y': 1}; aprim = a.copy()
        b = {'x': 2, 'z': 1}; bprim = b.copy()
        expected = {'x': 3, 'y': 1, 'z': 1}

        self.assertEquals(expected, zohmg.data.dict_addition(a,b))
        # make sure nothing was changed.
        self.assertEquals(a, aprim)
        self.assertEquals(b, bprim)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mapper
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import unittest
from zohmg.mapper import Mapper

# void usermapper.
def m(key, value):
    pass

# mock of usermapper.
def mock_mapper(k, v):
    ymd = '20090618'
    yield (ymd, {'agent':'firefox', 'path':'/about'}, {'hit':1})

class TestMapper(unittest.TestCase):
    def test_dict_permutations(self):
        mapper = Mapper(m, []) # setup with void mapper and empty projection list.

        p = mapper.dict_permutations({'agent': 'firefox'})
        self.assertEqual(p, [{'agent': 'firefox'}, {'agent': 'all'}])

        p = mapper.dict_permutations({'a':'x', 'b':'y'})
        expected = [{'a':'x', 'b':'y'}, {'a':'x', 'b':'all'}, {'a':'all', 'b':'y'}, {'a':'all', 'b':'all'}]
        self.assertEqual(p, expected)

        p = mapper.dict_permutations({'agent' : 'firefox', 'country' : 'SE', 'http-status' : '200', 'path':'/'})
        expected = [{'http-status': '200', 'path': '/', 'agent': 'firefox', 'country': 'SE'}, {'http-status': '200', 'path': '/', 'agent': 'all', 'country': 'SE'}, {'http-status': '200', 'path': 'all', 'agent': 'firefox', 'country': 'SE'}, {'http-status': '200', 'path': 'all', 'agent': 'all', 'country': 'SE'}, {'http-status': '200', 'path': '/', 'agent': 'firefox', 'country': 'all'}, {'http-status': '200', 'path': '/', 'agent': 'all', 'country': 'all'}, {'http-status': '200', 'path': 'all', 'agent': 'firefox', 'country': 'all'}, {'http-status': '200', 'path': 'all', 'agent': 'all', 'country': 'all'}, {'http-status': 'all', 'path': '/', 'agent': 'firefox', 'country': 'SE'}, {'http-status': 'all', 'path': '/', 'agent': 'all', 'country': 'SE'}, {'http-status': 'all', 'path': 'all', 'agent': 'firefox', 'country': 'SE'}, {'http-status': 'all', 'path': 'all', 'agent': 'all', 'country': 'SE'}, {'http-status': 'all', 'path': '/', 'agent': 'firefox', 'country': 'all'}, {'http-status': 'all', 'path': '/', 'agent': 'all', 'country': 'all'}, {'http-status': 'all', 'path': 'all', 'agent': 'firefox', 'country': 'all'}, {'http-status': 'all', 'path': 'all', 'agent': 'all', 'country': 'all'}]
        self.assertEqual(p, expected)

    def test_mapper(self):
        mapper = Mapper(mock_mapper, [['agent']])
        output = list(mapper(0, 'bogus value'))
        expected  = []
        expected += [(('20090618', ['agent'], {'agent': 'firefox'}, 'hit'), 1)]
        expected += [(('20090618', ['agent'], {'agent': 'all'}, 'hit'), 1)]
        self.assertEqual(output, expected)

        mapper = Mapper(mock_mapper, [['agent','path'], ['path'], ['agent']])
        output = list(mapper(0, 'bogus value'))
        expected  = []
        expected += [(('20090618', ['agent', 'path'], {'path': '/about', 'agent': 'firefox'}, 'hit'), 1)]
        expected += [(('20090618', ['agent', 'path'], {'path': '/about', 'agent': 'all'}, 'hit'), 1)]
        expected += [(('20090618', ['agent', 'path'], {'path': 'all', 'agent': 'firefox'}, 'hit'), 1)]
        expected += [(('20090618', ['agent', 'path'], {'path': 'all', 'agent': 'all'}, 'hit'), 1)]
        expected += [(('20090618', ['path'], {'path': '/about'}, 'hit'), 1)]
        expected += [(('20090618', ['path'], {'path': 'all'}, 'hit'), 1)]
        expected += [(('20090618', ['agent'], {'agent': 'firefox'}, 'hit'), 1)]
        expected += [(('20090618', ['agent'], {'agent': 'all'}, 'hit'), 1)]
        self.assertEqual(output, expected)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_middleware_data
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import unittest
import zohmg.middleware.data

class TestMiddlewareData(unittest.TestCase):
    def test_request(self):
        d = zohmg.middleware.data.data('egads', [])
        pass


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utils
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import unittest
from zohmg.utils import compare_triples

class TestUtils(unittest.TestCase):
    def test_tuplecompare(self):
        k = (10, 2, 'whatever')
        l = (10, 1, 'whatever')
        m = (0, 200, 'whatever')

        self.assertEqual(compare_triples(k, k), 0)
        self.assertEqual(compare_triples(k, l), 1)
        self.assertEqual(compare_triples(l, k), -1)
        self.assertEqual(compare_triples(k, m), 1)
        self.assertEqual(compare_triples(m, k), -1)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
