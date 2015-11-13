__FILENAME__ = operational-print
#!/usr/bin/env python

import os
import sys
import time

# When the parent dies we are seeing continual newlines, so we only access so many before stopping
counter = 0

while True:
	try:
		line = sys.stdin.readline().strip()
		if line == "":
			counter += 1
			if counter > 100:
				break
			continue

		counter = 0

		send = '\n%s %s %s\n' % ( '-'*10, line, '-'*10 )
		print >> sys.stderr, send
		sys.stderr.flush()
	except KeyboardInterrupt:
		pass
	except IOError:
		# most likely a signal during readline
		pass

########NEW FILE########
__FILENAME__ = operational-send
#!/usr/bin/env python

import os
import sys
import time

# When the parent dies we are seeing continual newlines, so we only access so many before stopping
counter = 1

# sleep a little bit or we will never see the asm in the configuration file
# and the message received just before we go to the established loop will be printed twice
time.sleep(1)

print 'operational rpcq afi ipv4 safi unicast sequence %d' % counter
print 'operational rpcp afi ipv4 safi unicast sequence %d counter 200' % counter
time.sleep(1)

counter += 1

print 'operational apcq afi ipv4 safi unicast sequence %d' % counter
print 'operational apcp afi ipv4 safi unicast sequence %d counter 150' % counter
time.sleep(1)

counter += 1

print 'operational lpcq afi ipv4 safi unicast sequence %d' % counter
print 'operational lpcp afi ipv4 safi unicast sequence %d counter 250' % counter
time.sleep(1)

while True:
	try:
		time.sleep(1)
		if counter % 2:
			print 'operational adm afi ipv4 safi unicast advisory "this is dynamic message #%d"' % counter
			sys.stdout.flush()
		else:
			print 'operational asm afi ipv4 safi unicast advisory "we SHOULD not send asm from the API"'
			sys.stdout.flush()

		counter += 1
	except KeyboardInterrupt:
		pass
	except IOError:
		break

########NEW FILE########
__FILENAME__ = pyprof2calltree
#!/usr/bin/env python

# Copyright (c) 2006-2008, David Allouche, Jp Calderone, Itamar Shtull-Trauring,
# Johan Dahlin, Olivier Grisel <olivier.grisel@ensta.org>
#
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
"""pyprof2calltree: profiling output which is readable by kcachegrind

This script can either take raw cProfile.Profile.getstats() log entries or
take a previously recorded instance of the pstats.Stats class.
"""

import cProfile
import pstats
import optparse
import os
import sys
import tempfile

__all__ = ['convert', 'visualize', 'CalltreeConverter']

class Code(object):
    pass

class Entry(object):
    pass

def pstats2entries(data):
    """Helper to convert serialized pstats back to a list of raw entries

    Converse opperation of cProfile.Profile.snapshot_stats()
    """
    entries = dict()
    allcallers = dict()

    # first pass over stats to build the list of entry instances
    for code_info, call_info in data.stats.items():
        # build a fake code object
        code = Code()
        code.co_filename, code.co_firstlineno, code.co_name = code_info

        # build a fake entry object
        cc, nc, tt, ct, callers = call_info
        entry = Entry()
        entry.code = code
        entry.callcount = cc
        entry.reccallcount = nc - cc
        entry.inlinetime = tt
        entry.totaltime = ct

        # to be filled during the second pass over stats
        entry.calls = list()

        # collect the new entry
        entries[code_info] = entry
        allcallers[code_info] = callers.items()

    # second pass of stats to plug callees into callers
    for entry in entries.itervalues():
        entry_label = cProfile.label(entry.code)
        entry_callers = allcallers.get(entry_label, [])
        for entry_caller, call_info in entry_callers:
            entries[entry_caller].calls.append((entry, call_info))

    return entries.values()

class CalltreeConverter(object):
    """Convert raw cProfile or pstats data to the calltree format"""

    kcachegrind_command = "kcachegrind %s"

    def __init__(self, profiling_data):
        if isinstance(profiling_data, basestring):
            # treat profiling_data as a filename of pstats serialized data
            self.entries = pstats2entries(pstats.Stats(profiling_data))
        elif isinstance(profiling_data, pstats.Stats):
            # convert pstats data to cProfile list of entries
            self.entries = pstats2entries(profiling_data)
        else:
            # assume this are direct cProfile entries
            self.entries = profiling_data
        self.out_file = None

    def output(self, out_file):
        """Write the converted entries to out_file"""
        self.out_file = out_file
        print >> out_file, 'events: Ticks'
        self._print_summary()
        for entry in self.entries:
            self._entry(entry)

    def visualize(self):
        """Launch kcachegrind on the converted entries

        kcachegrind must be present in the system path
        """

        if self.out_file is None:
            _, outfile = tempfile.mkstemp(".log", "pyprof2calltree")
            f = file(outfile, "wb")
            self.output(f)
            use_temp_file = True
        else:
            use_temp_file = False

        try:
            os.system(self.kcachegrind_command % self.out_file.name)
        finally:
            # clean the temporary file
            if use_temp_file:
                f.close()
                os.remove(outfile)
                self.out_file = None

    def _print_summary(self):
        max_cost = 0
        for entry in self.entries:
            totaltime = int(entry.totaltime * 1000)
            max_cost = max(max_cost, totaltime)
        print >> self.out_file, 'summary: %d' % (max_cost,)

    def _entry(self, entry):
        out_file = self.out_file

        code = entry.code
        #print >> out_file, 'ob=%s' % (code.co_filename,)

        co_filename, co_firstlineno, co_name = cProfile.label(code)
        print >> out_file, 'fi=%s' % (co_filename,)
        print >> out_file, 'fn=%s %s:%d' % (
            co_name, co_filename, co_firstlineno)

        inlinetime = int(entry.inlinetime * 1000)
        if isinstance(code, str):
            print >> out_file, '0 ', inlinetime
        else:
            print >> out_file, '%d %d' % (code.co_firstlineno, inlinetime)

        # recursive calls are counted in entry.calls
        if entry.calls:
            calls = entry.calls
        else:
            calls = []

        if isinstance(code, str):
            lineno = 0
        else:
            lineno = code.co_firstlineno

        for subentry, call_info in calls:
            self._subentry(lineno, subentry, call_info)
        print >> out_file

    def _subentry(self, lineno, subentry, call_info):
        out_file = self.out_file
        code = subentry.code
        #print >> out_file, 'cob=%s' % (code.co_filename,)
        co_filename, co_firstlineno, co_name = cProfile.label(code)
        print >> out_file, 'cfn=%s %s:%d' % (
            co_name, co_filename, co_firstlineno)
        print >> out_file, 'cfi=%s' % (co_filename,)
        print >> out_file, 'calls=%d %d' % (call_info[0], co_firstlineno)

        totaltime = int(call_info[3] * 1000)
        print >> out_file, '%d %d' % (lineno, totaltime)

def main():
    """Execute the converter using parameters provided on the command line"""

    usage = "%s [-k] [-o output_file_path] [-i input_file_path] [-r scriptfile [args]]"
    parser = optparse.OptionParser(usage=usage % sys.argv[0])
    parser.allow_interspersed_args = False
    parser.add_option('-o', '--outfile', dest="outfile",
                      help="Save calltree stats to <outfile>", default=None)
    parser.add_option('-i', '--infile', dest="infile",
                      help="Read python stats from <infile>", default=None)
    parser.add_option('-r', '--run-script', dest="script",
                      help="Name of the python script to run to collect"
                      " profiling data", default=None)
    parser.add_option('-k', '--kcachegrind', dest="kcachegrind",
                      help="Run the kcachegrind tool on the converted data",
                      action="store_true")
    options, args = parser.parse_args()


    outfile = options.outfile

    if options.script is not None:
        # collect profiling data by running the given script

        sys.argv[:] = [options.script] + args
        if not options.outfile:
            outfile = '%s.log' % os.path.basename(options.script)

        prof = cProfile.Profile()
        try:
            try:
                prof = prof.run('execfile(%r)' % (sys.argv[0],))
            except SystemExit:
                pass
        finally:
            kg = CalltreeConverter(prof.getstats())

    elif options.infile is not None:
        # use the profiling data from some input file
        if not options.outfile:
            outfile = '%s.log' % os.path.basename(options.infile)

        if options.infile == outfile:
            # prevent name collisions by appending another extension
            outfile += ".log"

        kg = CalltreeConverter(pstats.Stats(options.infile))

    else:
        # at least an input file or a script to run is required
        parser.print_usage()
        sys.exit(2)

    if options.outfile is not None or not options.kcachegrind:
        # user either explicitely required output file or requested by not
        # explicitely asking to launch kcachegrind
        print "writing converted data to: " + outfile
        kg.output(file(outfile, 'wb'))

    if options.kcachegrind:
        print "launching kcachegrind"
        kg.visualize()


def visualize(profiling_data):
    """launch the kcachegrind on `profiling_data`

    `profiling_data` can either be:
        - a pstats.Stats instance
        - the filename of a pstats.Stats dump
        - the result of a call to cProfile.Profile.getstats()
    """
    converter = CalltreeConverter(profiling_data)
    converter.visualize()

def convert(profiling_data, outputfile):
    """convert `profiling_data` to calltree format and dump it to `outputfile`

    `profiling_data` can either be:
        - a pstats.Stats instance
        - the filename of a pstats.Stats dump
        - the result of a call to cProfile.Profile.getstats()

    `outputfile` can either be:
        - a file() instance open in write mode
        - a filename
    """
    converter = CalltreeConverter(profiling_data)
    if isinstance(outputfile, basestring):
        f = file(outputfile, "wb")
        try:
            converter.output(f)
        finally:
            f.close()
    else:
        converter.output(outputfile)


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = api-internet
#!/usr/bin/env python

import sys
import time

def write (data):
	sys.stdout.write(data + '\n')
	sys.stdout.flush()

def main ():
	msg = 'announce attribute next-hop 1.2.3.4 med 100 as-path [ 100 101 102 103 104 105 106 107 108 109 110 ] nlri %s'
	write(msg % ' '.join('%d.0.0.0/8' % ip for ip in range(0,224)))
	write(msg % ' '.join('10.%d.0.0/16' % ip for ip in range(0,256)))

	time.sleep(2)

	write('withdraw attribute next-hop 1.2.3.4 med 100 as-path [ 100 101 102 103 104 105 106 107 108 109 110 ] nlri 0.0.0.0/8 1.0.0.0/8')

	time.sleep(10000)

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

########NEW FILE########
__FILENAME__ = api-internet
#!/usr/bin/env python

import sys
import time
import random

def write (data):
	sys.stdout.write(data + '\n')
	sys.stdout.flush()

def main ():
	count = 0

	ip = {}
	nexthop="1.2.3.4"

	for ip1 in range(0,223):
		generated = '%d.0.0.0/8' % (ip1)
		ip[generated] = nexthop

	for ip1 in range(0,223):
		for ip2 in range(0,256):
			generated = '%d.%d.0.0/16' % (ip1,ip2)
			ip[generated] = nexthop

	# initial table dump
	for k,v in ip.iteritems():
		count += 1
		write('announce route %s next-hop %s med 100 as-path [ 100 101 102 103 104 105 106 107 108 109 110 ]' % (k,v))
		if count % 100 == 0:
			sys.stderr.write('initial : announced %d\n' % count)

	count &= 0xFFFFFFFe
	time.sleep(10000)

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

########NEW FILE########
__FILENAME__ = dump-all
#!/usr/bin/env python

import sys

count = 0

while True:
	line = sys.stdin.readline()
	sys.stderr.write(line)
	sys.stderr.flush()

########NEW FILE########
__FILENAME__ = dump-number
#!/usr/bin/env python

import sys

count = 0

while True:
	line = sys.stdin.readline()
	if ' route' in line:
		count += 1
		if count % 100 == 0:
			sys.stderr.write('received %-10d\n' % count)
			sys.stderr.flush()

########NEW FILE########
__FILENAME__ = dump-to-screen
#!/usr/bin/env python

import sys

count = 0

while True:
	line = sys.stdin.readline()
	if ' route' in line:
		count += 1
		if count % 100 == 0:
			sys.stderr.write('received %-10d\n' % count)
			sys.stderr.flush()

########NEW FILE########
__FILENAME__ = api-internet
#!/usr/bin/env python

import sys
import time
import random

def write (data):
	sys.stdout.write(data + '\n')
	sys.stdout.flush()

def main ():
	if len(sys.argv) < 2:
		print "%s <number of routes> <updates per second thereafter>"
		sys.exit(1)

	initial = sys.argv[1]
	thereafter = sys.argv[2]

	if not initial.isdigit() or not thereafter.isdigit():
		write('please give valid numbers')
		sys.exit(1)

	# Limit to sane numbers :-)
	number = int(initial) & 0x00FFFFFF
	after = int(thereafter) & 0x0000FFFF

	range1 = (number >> 16) & 0xFF
	range2 = (number >>  8) & 0xFF
	range3 = (number      ) & 0xFF

	ip = {}
	nexthop = ['%d.%d.%d.%d' % (random.randint(1,200),random.randint(0,255),random.randint(0,255),random.randint(0,255)) for _ in range(200)]

	for ip1 in range(0,range1):
		for ip2 in range(0,256):
			for ip3 in range(0,256):
				generated = '%d.%d.%d.%d' % (random.randint(1,200),ip1,ip2,ip3)
				ip[generated] = random.choice(nexthop)

	for ip2 in range (0,range2):
		for ip3 in range (0,256):
			generated = '%d.%d.%d.%d' % (random.randint(1,200),range1,ip2,ip3)
			ip[generated] = random.choice(nexthop)

	for ip3 in range (0,range3):
		generated = '%d.%d.%d.%d' % (random.randint(1,200),range1,range2,ip3)
		ip[generated] = random.choice(nexthop)

	count = 0

	# initial table dump
	for k,v in ip.iteritems():
		count += 1
		write('announce route %s next-hop %s med 1%02d as-path [ 100 101 102 103 104 105 106 107 108 109 110 ]' % (k,v,len(k)))
		if count % 100 == 0:
			sys.stderr.write('initial : announced %d\n' % count)

	count &= 0xFFFFFFFe

	# modify routes forever
	while True:
		now = time.time()
		changed = {}

		for k,v in ip.iteritems():
			changed[k] = v
			if not random.randint(0,after):
				break

		for k,v in changed.iteritems():
			count += 2
			write('withdraw route %s next-hop %s med 1%02d as-path [ 100 101 102 103 104 105 106 107 108 109 110 ]' % (k,v,len(k)))
			ip[k] = random.choice(nexthop)
			write('announce route %s next-hop %s med 1%02d as-path [ 100 101 102 103 104 105 106 107 108 109 110 ]' % (k,ip[k],len(k)))
			if count % 100 == 0:
				sys.stderr.write('updates : announced %d\n' % count)


		time.sleep(time.time()-now+1.0)

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

########NEW FILE########
__FILENAME__ = dump-all
#!/usr/bin/env python

import sys

count = 0

while True:
	line = sys.stdin.readline()
	sys.stderr.write(line)
	sys.stderr.flush()

########NEW FILE########
__FILENAME__ = dump-number
#!/usr/bin/env python

import sys

count = 0

while True:
	line = sys.stdin.readline()
	if ' route' in line:
		count += 1
		if count % 100 == 0:
			sys.stderr.write('received %-10d\n' % count)
			sys.stderr.flush()

########NEW FILE########
__FILENAME__ = dump-to-screen
#!/usr/bin/env python

import sys

count = 0

while True:
	line = sys.stdin.readline()
	if ' route' in line:
		count += 1
		if count % 100 == 0:
			sys.stderr.write('received %-10d\n' % count)
			sys.stderr.flush()

########NEW FILE########
__FILENAME__ = re-ask
#!/usr/bin/env python

import sys
import signal

class TimeError (Exception): pass

def handler(signum, frame):
	raise TimeError()

count = 0

while True:
	try:
		signal.signal(signal.SIGALRM, handler)
		signal.alarm(4)

		line = sys.stdin.readline()
		sys.stderr.write('received %s\n' % line.strip())
		sys.stderr.flush()
	except TimeError:
		print 'announce route-refresh ipv4 unicast'
		sys.stdout.flush()
		print >> sys.stderr, 'announce route-refresh ipv4 unicast'
		sys.stderr.flush()

########NEW FILE########
__FILENAME__ = log-syslog
#!/usr/bin/env python

import os
import sys
import time
import syslog

def _prefixed (level,message):
	now = time.strftime('%a, %d %b %Y %H:%M:%S',time.localtime())
	return "%s %-8s %-6d %s" % (now,level,os.getpid(),message)

syslog.openlog("ExaBGP")

# When the parent dies we are seeing continual newlines, so we only access so many before stopping
counter = 0

while True:
	try:
		line = sys.stdin.readline().strip()
		if line == "":
			counter += 1
			if counter > 100:
				break
			continue

		counter = 0

		syslog.syslog(syslog.LOG_ALERT, _prefixed('INFO',line))
	except KeyboardInterrupt:
		pass
	except IOError:
		# most likely a signal during readline
		pass

########NEW FILE########
__FILENAME__ = configuration
#!/usr/bin/env python
# encoding: utf-8
"""
configuration.py

Created by Thomas Mangin on 2009-08-25.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import unittest

from exabgp.configuration.environment import environment
env = environment.setup('')

from exabgp.configuration.file import Configuration


class TestConfiguration (unittest.TestCase):
	def setUp(self):
		pass

	def test_valid (self):
		for config in self.valid:
			configuration = Configuration(config,True)
			try:
				self.assertEqual(configuration.reload(),True,configuration.error)
			except:
				print
				print config
				print
				print configuration.error
				print
				raise
#		for ip in self.configuration.neighbor:
#			print self.configuration.neighbor[ip]

	def test_reload (self):
		configuration = Configuration(self.valid[0],True)
		configuration.reload()

	valid = [
"""\
neighbor 192.168.127.128 {
	description "a quagga test peer";
	router-id 192.168.127.1;
	local-address 192.168.127.1;
	local-as 65000;
	peer-as 65000;

	static {
		route 10.0.1.0/24 {
			next-hop 10.0.255.1;
		}
		route 10.0.2.0/24 {
			next-hop 10.0.255.2;
			community 30740:30740;
		}
		route 10.0.3.0/24 {
			next-hop 10.0.255.3;
			community [ 30740:30740 30740:0 ];
		}
		route 10.0.4.0/24 {
			next-hop 10.0.255.4;
			local-preference 200;
		}
		route 10.0.5.0/24 next-hop 10.0.255.5 local-preference 200;
		route 10.0.6.0/24 next-hop 10.0.255.6 community 30740:30740;
		route 10.0.7.0/24 next-hop 10.0.255.7 local-preference 200 community 30740:30740;
		route 10.0.8.0/24 next-hop 10.0.255.8 community 30740:30740 local-preference 200;
		route 10.0.9.0/24 next-hop 10.0.255.9 local-preference 200 community [30740:0 30740:30740];
		route 10.0.10.0/24 next-hop 10.0.255.10 community [30740:0 30740:30740] local-preference 200;
	}
}
"""
,
"""\
neighbor 192.168.127.128 {
	description "Configuration One";
	router-id 192.168.127.2;
	local-address 192.168.127.1;
	local-as 65001;
	peer-as 65000;

	static {
		route 10.0.1.0/24 {
			next-hop 10.0.255.1;
		}
		route 10.0.2.0/24 {
			next-hop 10.0.255.2;
			community 30740:30740;
		}
		route 10.0.3.0/24 {
			next-hop 10.0.255.3;
			community [ 30740:30740 30740:0 ];
		}
		route 10.0.4.0/24 {
			next-hop 10.0.255.4;
			local-preference 200;
		}
	}
}
neighbor 10.0.0.10 {
	description "Configuration Two";
	local-address 10.0.0.2;
	local-as 65001;
	peer-as 65001;

	static {
		route 10.0.5.0/24 next-hop 10.0.255.5 local-preference 200;
		route 10.0.6.0/24 next-hop 10.0.255.6 community 30740:30740;
		route 10.0.7.0/24 next-hop 10.0.255.7 local-preference 200 community 30740:30740;
		route 10.0.8.0/24 next-hop 10.0.255.8 community 30740:30740 local-preference 200;
		route 10.0.9.0/24 next-hop 10.0.255.9 local-preference 200 community [30740:0 30740:30740];
		route 10.0.10.0/24 next-hop 10.0.255.10 community [30740:0 30740:30740] local-preference 200;
	}
}
"""
]

	def test_faults (self):
		for config,error in self._faults.iteritems():
			configuration = Configuration(config,True)

			try:
				self.assertEqual(configuration.reload(),False)
				self.assertEqual(config + ' '*10 + configuration.error,config + ' '*10 + error)
			except AssertionError:
				print
				print config
				print
				print configuration.error
				print
				raise



	_faults = {
"""\
	neighbor A {
	}
""" : 'syntax error in section neighbor\nline 1 : neighbor a {\n"a" is not a valid IP address'
,
"""\
neighbor 10.0.0.10 {
	invalid-command value ;
}
""": 'syntax error in section neighbor\nline 2 : invalid-command value ;\ninvalid keyword "invalid-command"'
,
"""\
neighbor 10.0.0.10 {
	description A non quoted description;
}
""" : 'syntax error in section neighbor\nline 2 : description a non quoted description ;\nsyntax: description "<description>"'
,
"""\
neighbor 10.0.0.10 {
	description "A quoted description with "quotes" inside";
}
""" : 'syntax error in section neighbor\nline 2 : description "a quoted description with "quotes" inside" ;\nsyntax: description "<description>"'
,
"""\
neighbor 10.0.0.10 {
	local-address A;
}
""" : 'syntax error in section neighbor\nline 2 : local-address a ;\n"a" is an invalid IP address'
,
"""\
neighbor 10.0.0.10 {
	local-as A;
}
""" : 'syntax error in section neighbor\nline 2 : local-as a ;\n"a" is an invalid ASN'
,
"""\
neighbor 10.0.0.10 {
	peer-as A;
}
""" : 'syntax error in section neighbor\nline 2 : peer-as a ;\n"a" is an invalid ASN'
,
"""\
neighbor 10.0.0.10 {
	router-id A;
}
""" : 'syntax error in section neighbor\nline 2 : router-id a ;\n"a" is an invalid IP address'
,
"""\
neighbor 10.0.0.10 {
	static {
		route A/24 next-hop 10.0.255.5;
	}
}
""" : 'syntax error in section static\nline 3 : route a/24 next-hop 10.0.255.5 ;\n' + Configuration._str_route_error
,
"""\
neighbor 10.0.0.10 {
	static {
		route 10.0.5.0/A next-hop 10.0.255.5;
	}
}
""" : 'syntax error in section static\nline 3 : route 10.0.5.0/a next-hop 10.0.255.5 ;\n' + Configuration._str_route_error
,
"""\
neighbor 10.0.0.10 {
	static {
		route A next-hop 10.0.255.5;
	}
}
""" : 'syntax error in section static\nline 3 : route a next-hop 10.0.255.5 ;\n' + Configuration._str_route_error
,
"""\
neighbor 10.0.0.10 {
	static {
		route 10.0.5.0/24 next-hop A;
	}
}
""" : 'syntax error in section static\nline 3 : route 10.0.5.0/24 next-hop a ;\n' + Configuration._str_route_error
,
"""\
neighbor 10.0.0.10 {
	static {
		route 10.0.5.0/24 next-hop 10.0.255.5 local-preference A;
	}
}
""" : 'syntax error in section static\nline 3 : route 10.0.5.0/24 next-hop 10.0.255.5 local-preference a ;\n' + Configuration._str_route_error
,
"""\
neighbor 10.0.0.10 {
	static {
		route 10.0.5.0/24 next-hop 10.0.255.5 community a;
	}
}
""" : 'syntax error in section static\nline 3 : route 10.0.5.0/24 next-hop 10.0.255.5 community a ;\n' + Configuration._str_route_error
,
"""\
neighbor 10.0.0.10 {
	static {
		route 10.0.5.0/24 next-hop 10.0.255.5 community [ A B ];
	}
}
""" : 'syntax error in section static\nline 3 : route 10.0.5.0/24 next-hop 10.0.255.5 community [ a b ] ;\n' + Configuration._str_route_error
,
"""\
neighbor 192.168.127.128 {
	local-address 192.168.127.1;
	local-as 65000;
	peer-as 65000;
	static {
		route 10.0.1.0/24 {
		}
	}
}
""" : 'syntax error in section static\nline 7 : }\nsyntax: route IP/MASK { next-hop IP; }'
,
"""\
neighbor 192.168.127.128 {
	static {
		route 10.0.1.0/24 {
			next-hop A;
		}
	}
}
""" : 'syntax error in section route\nline 4 : next-hop a ;\n' + Configuration._str_route_error
,
"""\
neighbor 192.168.127.128 {
	static {
		route 10.0.1.0/24 {
			next-hop 10.0.255.5;
			local-preference A;
		}
	}
}
""" : 'syntax error in section route\nline 5 : local-preference a ;\n' + Configuration._str_route_error
,
"""\
neighbor 192.168.127.128 {
	static {
		route 10.0.1.0/24 {
			next-hop 10.0.255.5;
			community A;
		}
	}
}
""" : 'syntax error in section route\nline 5 : community a ;\n' + Configuration._str_route_error
,
"""\
neighbor 192.168.127.128 {
	static {
		route 10.0.1.0/24 {
			next-hop 10.0.255.5;
			community [ A B ];
		}
	}
}
""" : 'syntax error in section route\nline 5 : community [ a b ] ;\n' + Configuration._str_route_error
,
"""\
neighbor 192.168.127.128 {
	local-address 192.168.127.1;
	local-as 65000;
	peer-as 65000;

	static {
		route 10.0.1.0/24 {
			next-hop 10.0.255.1;
		}
	}
""" : 'syntax error in section neighbor\nline 10 : }\nconfiguration file incomplete (most likely missing })'
,

}


if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = decode-route
#!/usr/bin/env python

from exabgp.configuration.environment import environment
env = environment.setup('')

header = [
	0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, # marker
	0x1, 0x37, # len 311 (body is 296 - 296 + 19 = 315 !!)
	0x2, # type Update
]

body = [
	0x0, 0x0, #len withdrawn routes
	# No routes to remove
	# Attributes
	0x0, 0x30, # len attributes (48)
		0x40, # Flag Transitive
		0x1, # Code : AttributeID Origin
		0x1, # len
			0x0, # Origin : IGP
		0x50, # Flag Transitive + extended length
		0x2, # Code : AS Path
		0x0, 0x16, # len 22
			0x2, # Type (AS_Sequence)
			0x5, # length (in ASes as every asn is 0x0 0x0 prefixed ASN4 must have been negotiated)
				0x0, 0x0, 0xfe, 0xb0,		# ASN 65200
				0x0, 0x0, 0x78, 0x14,		# ASN 30740
				0x0, 0x0, 0x19, 0x35,		# ASN 6453
				0x0, 0x0, 0xb, 0x62,		# ASN 2914
				0x0, 0x0, 0x9, 0xd7,		# ASN 2519
		0x40, # Flag Transitive
		0x3, # Code: Next HOP
		0x4, # len
			0x7f, 0x0, 0x0, 0x1, # 127.0.0.1
		0xc0, # 0x40 + 0x80 (Transitive Optional)
		0x8, # Community
		0x8, # Size 8
			0x78, 0x14, 0x19, 0x35, # 30740:6453
			0x78, 0x14, 0xfd, 0xeb, # 30740:65003
	# routes :
		0x18, 0x1, 0x0, 0x19, # 1.0.25.0/24
		0x10, 0xde, 0xe6, # 222.330.0.0/16
		0x11, 0xde, 0xe5, 0x80,
		0x12, 0xde, 0xe5, 0x0,
		0x10, 0xde, 0xe4,
		0x11, 0xdc, 0xf7, 0x0,
		0x11, 0xdc, 0x9e, 0x0,
		0x18, 0xdb, 0x79, 0xff,
		0x18, 0xdb, 0x79, 0xf9,
		0x16, 0xd8, 0xb3, 0xcc,
		0x18, 0xd8, 0xb3, 0xb6,
		0x17, 0xd8, 0xb3, 0xb4,
		0x16, 0xd8, 0xb3, 0xb0,
		0x18, 0xd8, 0xb3, 0x99,
		0x12, 0xd2, 0xaa, 0x0,
		0x11, 0xd2, 0x92, 0x80,
		0x11, 0xd2, 0x83, 0x80,
		0x13, 0xcb, 0x8c, 0x20,
		0x18, 0xca, 0xf5, 0xfe,
		0x18, 0xca, 0xf5, 0x8e,
		0x18, 0xca, 0xf3, 0xba,
		0x18, 0xca, 0xf0, 0x8d,
		0x12, 0xca, 0xef, 0xc0,
		0x12, 0xca, 0xe7, 0x40,
		0x10, 0xca, 0xd7,
		0x18, 0xca, 0xd2, 0x8,
		0x13, 0xca, 0xbd, 0xc0,
		0x14, 0xca, 0x58, 0x30,
		0x18, 0xca, 0x22, 0xbf,
		0x17, 0xca, 0x22, 0x96,
		0x18, 0xc0, 0x32, 0x6e,
		0x10, 0xb7, 0xb4,
		0x11, 0xb7, 0xb1, 0x80,
		0x10, 0xa3, 0x8b,
		0x11, 0x9d, 0x78, 0x80,
		0x15, 0x7c, 0xf1, 0x78,
		0x10, 0x7c, 0x6e,
		0x10, 0x7a, 0x67,
		0x10, 0x78, 0x33,
		0x10, 0x74, 0x5b,
		0x15, 0x73, 0xbb, 0x48,
		0x16, 0x73, 0xbb, 0x44,
		0x10, 0x73, 0xb3,
		0x11, 0x72, 0x45, 0x0,
		0x14, 0x71, 0x34, 0xf0,
		0x15, 0x70, 0x6d, 0x18,
		0x18, 0x67, 0xf6, 0xb3,
		0x17, 0x67, 0xb, 0x6,
		0x18, 0x67, 0x5, 0x75,
		0x18, 0x67, 0x5, 0x74,
		0x18, 0x67, 0x3, 0x10,
		0x13, 0x65, 0x37, 0xc0,
		0x11, 0x65, 0x32, 0x80,
		0x18, 0x65, 0x0, 0x1f,
		0x18, 0x65, 0x0, 0x1e,
		0x18, 0x65, 0x0, 0x1d,
		0x18, 0x65, 0x0, 0x1c,
		0xf, 0x24, 0x2,
		0x11, 0x1b, 0x79, 0x80,
		0x13, 0x1b, 0x60, 0x20,
		0x15, 0x1b, 0x60, 0x10,
		0x10, 0x1, 0x15,
		0x16, 0x1, 0x0, 0x1c,
		0x17, 0x1, 0x0, 0x1a
]


header = [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x1, 0x22, 0x2]

body = [
	0x0, 0x0,
	0x0, 0x38,
	0x40,
		0x1,
		0x1,
			0x0,
	0x50,
		0x2,
		0x0, 0x12,
			0x2,
			0x4,
				0x0, 0x0, 0xc7, 0x9d,
				0x0, 0x0, 0x9b, 0xbd,
				0x0, 0x0, 0xb, 0x62,
				0x0, 0x0, 0x9, 0xd7,
	0x40,
		0x3,
		0x4,
			0xb2, 0xd9, 0x76, 0x1,
	0xc0,
		0x8,
		0x14,
			0xb, 0x62, 0x1, 0x9a,
			0xb, 0x62, 0x5, 0x7b,
			0xb, 0x62, 0x9, 0x61,
			0xb, 0x62, 0xd, 0x48,
			0x9b, 0xbd, 0x1d, 0x1a,
	0x18, 0x1, 0x0, 0x19,
	0x10, 0xde, 0xe6,
	0x11, 0xde, 0xe5, 0x80,
	0x12, 0xde, 0xe5, 0x0,
	0x18, 0xdb, 0x79, 0xff,
	0x18, 0xdb, 0x79, 0xf9,
	0x16, 0xd8, 0xb3, 0xcc,
	0x18, 0xd8, 0xb3, 0xb6,
	0x17, 0xd8, 0xb3, 0xb4,
	0x16, 0xd8, 0xb3, 0xb0,
	0x18, 0xd8, 0xb3, 0x99,
	0x12, 0xd2, 0xaa, 0x0,
	0x11, 0xd2, 0x92, 0x80,
	0x11, 0xd2, 0x83, 0x80,
	0x13, 0xcb, 0x8c, 0x20,
	0x18, 0xca, 0xf5, 0xfe,
	0x18, 0xca, 0xf5, 0x8e,
	0x18, 0xca, 0xf3, 0xba,
	0x18, 0xca, 0xf0, 0x8d,
	0x12, 0xca, 0xef, 0xc0,
	0x12, 0xca, 0xe7, 0x40,
	0x18, 0xca, 0xd2, 0x8,
	0x13, 0xca, 0xbd, 0xc0,
	0x14, 0xca, 0x58, 0x30,
	0x18, 0xca, 0x22, 0xbf,
	0x17, 0xca, 0x22, 0x96,
	0x18, 0xc0, 0x32, 0x6e,
	0x10, 0xb7, 0xb4,
	0x11, 0x9d, 0x78, 0x80,
	0x15, 0x7c, 0xf1, 0x78,
	0x10, 0x7a, 0x67,
	0x15, 0x73, 0xbb, 0x48,
	0x16, 0x73, 0xbb, 0x44,
	0x11, 0x72, 0x45, 0x0,
	0x14, 0x71, 0x34, 0xf0,
	0x15, 0x70, 0x6d, 0x18,
	0x18, 0x67, 0xf6, 0xb3,
	0x17, 0x67, 0xb, 0x6,
	0x18, 0x67, 0x5, 0x75,
	0x18, 0x67, 0x5, 0x74,
	0x18, 0x67, 0x3, 0x10,
	0x13, 0x65, 0x37, 0xc0,
	0x11, 0x65, 0x32, 0x80,
	0x18, 0x65, 0x0, 0x1f,
	0x18, 0x65, 0x0, 0x1e,
	0x18, 0x65, 0x0, 0x1d,
	0x18, 0x65, 0x0, 0x1c,
	0xf, 0x24, 0x2,
	0x11, 0x1b, 0x79, 0x80,
	0x13, 0x1b, 0x60, 0x20,
	0x15, 0x1b, 0x60, 0x10,
	0x10, 0x1, 0x15,
	0x16, 0x1, 0x0, 0x1c,
	0x17, 0x1, 0x0, 0x1a
]

route = header + body

from StringIO import StringIO
from exabgp.reactor.protocol import Protocol
from exabgp.reactor.peer import Peer
from exabgp.bgp.neighbor import Neighbor

class Connection (StringIO):
	def pending (self,**argv):
		return True

cnx = Connection(''.join([chr(_) for _ in route]))
neibor = Neighbor()
peer = Peer(neibor,None)

#import pdb
#pdb.set_trace()

proto = Protocol(peer,cnx)
proto._asn4 = True
print proto.UpdateFactory(body)

########NEW FILE########
__FILENAME__ = delta
#!/usr/bin/env python
# encoding: utf-8
"""
protocol.py

Created by Thomas Mangin on 2009-08-27.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import unittest

from exabgp.configuration.environment import environment
env = environment.setup('')

from exabgp.bgp.message.open import Open,Capabilities,new_Open
from exabgp.bgp.message.notification import Notification
from exabgp.bgp.message.keepalive import KeepAlive,new_KeepAlive
from exabgp.bgp.message.update import Update,Attributes

from exabgp.rib.table import Table
from exabgp.rib.delta import Delta
from exabgp.reactor.protocol import Protocol
from exabgp.bgp.neighbor import Neighbor

from StringIO import StringIO

class Network (StringIO):
	def pending (self):
		return True

route1 = Update([],[to_NLRI('10.0.0.1','32')],Attributes())
route1.next_hop = '10.0.0.254'

route2 = Update([],[to_NLRI('10.0.1.1','32')],Attributes())
route2.next_hop = '10.0.0.254'

route3 = Update([],[to_NLRI('10.0.2.1','32')],Attributes())
route3.next_hop = '10.0.0.254'

routes = [route1,route2,route3]
routes.sort()

class TestProtocol (unittest.TestCase):

	def setUp(self):
		self.table = Table()
		self.table.update(routes)
		self.neighbor = Neighbor()
		self.neighbor.local_as = ASN(65000)
		self.neighbor.peer_as = ASN(65000)
		self.neighbor.peer_address = InetIP('1.2.3.4')
		self.neighbor.local_address = InetIP('5.6.7.8')

	def test_4_selfparse_update_announce (self):
		o = Open(4,65000,'1.2.3.4',Capabilities().default(),30).message()
		k = KeepAlive().message()
		u = Delta(self.table).announce(65000,65000)
		network = Network(o+k+ ''.join(u))
		bgp = Protocol(self.neighbor,network)
		bgp.follow = False

		self.assertEqual(bgp.read_message().TYPE,Open.TYPE)
		self.assertEqual(bgp.read_message().TYPE,KeepAlive.TYPE)
		updates = bgp.read_message()
		self.assertEqual(updates.TYPE,Update.TYPE)
		self.assertEqual(str(updates.added()[0]),'10.0.0.1/32 next-hop 10.0.0.254')
		updates = bgp.read_message()
		self.assertEqual(updates.TYPE,Update.TYPE)
		self.assertEqual(str(updates.added()[0]),'10.0.2.1/32 next-hop 10.0.0.254')
		updates = bgp.read_message()
		self.assertEqual(updates.TYPE,Update.TYPE)
		self.assertEqual(str(updates.added()[0]),'10.0.1.1/32 next-hop 10.0.0.254')

	def test_5_selfparse_update_announce_multi (self):
		o = Open(4,65000,'1.2.3.4',Capabilities().default(),30).message()
		k = KeepAlive().message()
		d = Delta(self.table)
		a = d.announce(65000,65000)
		self.table.update(routes[:-1])
		u = d.update(65000,65000)

		network = Network(o+k+''.join(u))
		bgp = Protocol(self.neighbor,network)
		bgp.follow = False

		self.assertEqual(bgp.read_message().TYPE,Open.TYPE)
		self.assertEqual(bgp.read_message().TYPE,KeepAlive.TYPE)
		updates = bgp.read_message()
		self.assertEqual(updates.TYPE,Update.TYPE)
		self.assertEqual(str(updates.added()[0]),'10.0.2.1/32')

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = flow
#!/usr/bin/env python
# encoding: utf-8
"""
flow.py

Created by Thomas Mangin on 2010-01-14.
Copyright (c) 2009-2013  Exa Networks. All rights reserved.
"""

import unittest

from exabgp.configuration.environment import environment
env = environment.setup('')

from exabgp.bgp.message.update.nlri.flow import *
from exabgp.protocol.ip.inet import *
from exabgp.bgp.message.update.attribute.communities import *


class TestFlow (unittest.TestCase):

	def setUp(self):
		pass

	def test_rule (self):
		components = {
			'destination': Destination("192.0.2.0",24),
			'source'     : Source("10.1.2.0",24),
			'anyport_1'  : AnyPort(NumericOperator.EQ,25),
		}
		messages = {
			'destination': [0x01, 0x18, 0xc0, 0x00, 0x02],
			'source'     : [0x02, 0x18, 0x0a, 0x01, 0x02],
			'anyport_1'  : [0x04, 0x01, 0x19],
		}

		for key in components.keys():
			component = components[key].pack()
			message   = ''.join((chr(_) for _ in messages[key]))
			if component != message:
				self.fail('failed test %s\n%s\n%s\n' % (key, [hex(ord(_)) for _ in component], [hex(ord(_)) for _ in message]))

	def test_rule_and (self):
		components = {
			'destination': Destination("192.0.2.0",24),
			'source'     : Source("10.1.2.0",24),
			'anyport_1'  : AnyPort(NumericOperator.EQ|NumericOperator.GT,25),
			'anyport_2'  : AnyPort(NumericOperator.EQ|NumericOperator.LT,80),
		}
		messages = {
			'destination': [0x01, 0x18, 0xc0, 0x00, 0x02],
			'source'     : [0x02, 0x18, 0x0a, 0x01, 0x02],
			'anyport_1'  : [0x04, 0x43, 0x19],
			'anyport_2'  : [0x04, 0x85, 0x50],
		}

		policy = Policy()
		message = ""
		for key in ['destination','source','anyport_1','anyport_2']:
			policy.add_and(components[key])
			message += ''.join([chr(_) for _ in messages[key]])
		message = chr(len(message)) + message
		policy.add(to_FlowAction(65000,False,False))
		flow = policy.flow().pack()
		#print [hex(ord(_)) for _ in flow]

	def test_nlri (self):
		components = {
			'destination': Destination("192.0.2.0",24),
			'source'     : Source("10.1.2.0",24),
			'anyport_1'  : AnyPort(NumericOperator.EQ|NumericOperator.GT,25),
			'anyport_2'  : AnyPort(NumericOperator.EQ|NumericOperator.LT,80),
		}
		messages = {
			'destination': [0x01, 0x18, 0xc0, 0x00, 0x02],
			'source'     : [0x02, 0x18, 0x0a, 0x01, 0x02],
			'anyport_1'  : [0x04, 0x43, 0x19],
			'anyport_2'  : [0x85, 0x50],
		}

		policy = Policy()
		message = ""
		for key in ['destination','source','anyport_1','anyport_2']:
			policy.add_and(components[key])
			message += ''.join([chr(_) for _ in messages[key]])
		message = chr(len(message)) + message
		policy.add(to_FlowAction(65000,False,False))
		flow = policy.flow().pack()
		if message[0] != flow[0]:
			self.fail('size mismatch %s %s\n' % (ord(flow[0]),ord(message[0])))
		if len(flow) != ord(flow[0]) + 1:
			self.fail('invalid size for message')
		if message[1:] != flow[1:]:
			self.fail('content mismatch\n%s\n%s' % ( [hex(ord(_)) for _ in flow]  , [hex(ord(_)) for _ in message] ))

#	def test_update (self):
#		components = {
#			'source_dest_port' : [Destination("192.0.2.0",24), Source("10.1.2.0",24), AnyPort(NumericOperator.EQ,25)],
#		}
#
#		messages = {
#			'source_dest_port' : [0x0f, 0x01, 0x04, 0x18, 0xc0, 0x00, 0x02, 0x02, 0x04, 0x18, 0x0a, 0x01, 0x02, 0x04, 0x81, 0x19],
#		}
#
#		for key in components.keys():
#			policy = Policy()
#			for component in components[key]:
#				policy.add_and(component)
#			policy.add(to_FlowAction(65000,False,False))
#			update = policy.flow().update().announce(0,0)
#			message   = ''.join((chr(_) for _ in messages[key]))
#			if update != message:
#				self.fail('failed test %s\n%s\n%s\n' % (key, [hex(ord(_)) for _ in update], [hex(ord(_)) for _ in message]))

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = loader
#!/usr/bin/env python
# encoding: utf-8
"""
table.py

Created by Thomas Mangin on 2009-08-25.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import os
import glob
import unittest

from exabgp.configuration.environment import environment
env = environment.setup('')

from exabgp.configuration.loader import read
#from exabgp.configuration.loader import InvalidFormat

class TestLoader (unittest.TestCase):

	def setUp(self):
		self.folder = os.path.abspath(os.path.join(os.path.abspath(__file__),'..','..','configuration'))

	def test_loader (self):
		for exaname in glob.glob('%s/*.exa' % self.folder):
			jsonname = '%s.json' % exaname[:-4]
			exa = read(exaname)
			jsn = read(jsonname)
			if not exa or not jsn:
				self.fail('parsing of %s or %s did not return a valid dictionary' % (exaname,jsonname))

			# import json
			# print json.dumps(exa, sort_keys=True,indent=3,separators=(',', ': '))
			# print

			if exa != jsn:
				self.fail('parsing of %s and/or %s did not return the expect result' % (exaname,jsonname))

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = open
#!/usr/bin/env python
# encoding: utf-8
"""
update.py

Created by Thomas Mangin on 2009-09-06.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import unittest

from exabgp.configuration.environment import environment
env = environment.setup('')

from exabgp.bgp.message.open import *

class TestData (unittest.TestCase):

	def test_1_open (self):
		header = ''.join([chr(c) for c in [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x0, 0x3d, 0x1]])
		message = ''.join([chr(c) for c in [0x4, 0xff, 0xfe, 0x0, 0xb4, 0x0, 0x0, 0x0, 0x0, 0x20, 0x2, 0x6, 0x1, 0x4, 0x0, 0x1, 0x0, 0x1, 0x2, 0x6, 0x1, 0x4, 0x0, 0x2, 0x0, 0x1, 0x2, 0x2, 0x80, 0x0, 0x2, 0x2, 0x2, 0x0, 0x2, 0x6, 0x41, 0x4, 0x0, 0x0, 0xff, 0xfe]])
		o  = new_Open(message)
		self.assertEqual(o.version,4)
		self.assertEqual(o.asn,65534)
		self.assertEqual(o.router_id,'0.0.0.0')
		self.assertEqual(o.hold_time,180)
		self.assertEqual(o.capabilities, {128: [], 1: [(1, 1), (2, 1)], 2: [], 65: 65534})

	def test_2_open (self):
		o = Open(4,65500,'127.0.0.1',Capabilities().default(False),180)
		self.assertEqual(o.version,4)
		self.assertEqual(o.asn,65500)
		self.assertEqual(o.router_id,'127.0.0.1')
		self.assertEqual(o.hold_time,180)
		self.assertEqual(o.capabilities, {64: {(1, 1): 128, (2, 1): 128}, 1: [(1, 1), (2, 1)]})

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = protocol
#!/usr/bin/env python
# encoding: utf-8
"""
protocol.py

Created by Thomas Mangin on 2009-08-27.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import unittest

from exabgp.configuration.environment import environment
env = environment.setup('')

from exabgp.bgp.message.open import Open,Capabilities,new_Open
from exabgp.bgp.message.notification import Notification
from exabgp.bgp.message.keepalive import KeepAlive,new_KeepAlive
from exabgp.bgp.message.update import Update,Attributes,new_Update

from exabgp.reactor.protocol import Protocol
from exabgp.bgp.neighbor import Neighbor

from StringIO import StringIO

class Network (StringIO):
	def pending (self):
		return True

route1 = Update([],[to_NLRI('10.0.0.1','32')],Attributes())
route1.next_hop = '10.0.0.254'

route2 = Update([],[to_NLRI('10.0.1.1','32')],Attributes())
route2.next_hop = '10.0.0.254'

route3 = Update([],[to_NLRI('10.0.2.1','32')],Attributes())
route3.next_hop = '10.0.0.254'

routes = [route1,route2,route3]
routes.sort()

class TestProtocol (unittest.TestCase):

	def setUp(self):
		self.neighbor = Neighbor()
		self.neighbor.local_as = ASN(65000)
		self.neighbor.peer_as = ASN(65000)
		self.neighbor.peer_address = InetIP('1.2.3.4')
		self.neighbor.local_address = InetIP('5.6.7.8')

	def test_1_selfparse_open (self):
		ds = Open(4,65000,'1.2.3.4',Capabilities().default(),30)

		txt = ds.message()
		network = Network(txt)
		#print [hex(ord(c)) for c in txt]
		bgp = Protocol(self.neighbor,network)
		bgp.follow = False

		o = bgp.read_open('127.0.0.1')
		self.assertEqual(o.version,4)
		self.assertEqual(o.asn,65000)
		self.assertEqual(o.hold_time,30)
		self.assertEqual(str(o.router_id),'1.2.3.4')

	def test_2_selfparse_KeepAlive (self):
		ds = KeepAlive()

		txt = ds.message()
		network = Network(txt)
		bgp = Protocol(self.neighbor,network)

		message = bgp.read_message()
		self.assertEqual(message.TYPE,KeepAlive.TYPE)

	def test_3_parse_update (self):
		txt = ''.join([chr(c) for c in [0x0, 0x0, 0x0, 0x1c, 0x40, 0x1, 0x1, 0x2, 0x40, 0x2, 0x0, 0x40, 0x3, 0x4, 0xc0, 0x0, 0x2, 0xfe, 0x80, 0x4, 0x4, 0x0, 0x0, 0x0, 0x0, 0x40, 0x5, 0x4, 0x0, 0x0, 0x1, 0x23, 0x20, 0x52, 0xdb, 0x0, 0x7, 0x20, 0x52, 0xdb, 0x0, 0x45, 0x20, 0x52, 0xdb, 0x0, 0x47]])
		updates = new_Update(txt)

		routes = [str(route) for route in updates.added()]
		routes.sort()
		self.assertEqual(routes[0],'82.219.0.69/32 next-hop 192.0.2.254')
		self.assertEqual(routes[1],'82.219.0.7/32 next-hop 192.0.2.254')
		self.assertEqual(routes[2],'82.219.0.71/32 next-hop 192.0.2.254')

	def test_4_parse_update (self):
		txt = ''.join([chr(c) for c in [0x0, 0x0, 0x0, 0x12, 0x40, 0x1, 0x1, 0x0, 0x40, 0x2, 0x4, 0x2, 0x1, 0x78, 0x14, 0x40, 0x3, 0x4, 0x52, 0xdb, 0x2, 0xb5, 0x0]])
		updates = new_Update(txt)
		self.assertEqual(str(updates.added()[0]),'0.0.0.0/0 next-hop 82.219.2.181')

	def test_6_holdtime (self):
		class MyPeer(Network):
			_data = StringIO(Open(4,65000,'1.2.3.4',Capabilities().default(),90).message())
			def read (self,l):
				return self._data.read(l)

		network = MyPeer('')

		bgp = Protocol(self.neighbor,network)
		bgp.follow = False

		before = bgp.neighbor.hold_time
		bgp.new_open()
		bgp.read_open('127.0.0.1')
		after = bgp.neighbor.hold_time

		self.assertEqual(after,min(before,90))

#	def test_7_message (self):
#		txt = ''.join([chr(_) for _ in [0x0, 0x0, 0x0, 0x30, 0x40, 0x1, 0x1, 0x0, 0x50, 0x2, 0x0, 0x4, 0x2, 0x1, 0xff, 0xfe, 0x80, 0x4, 0x4, 0x0, 0x0, 0x0, 0x0, 0x80, 0xe, 0x1a, 0x0, 0x2, 0x1, 0x10, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x20, 0x12, 0x34, 0x56, 0x78]])
#		updates = new_Update(txt)
#		print updates
#		self.assertEqual(str(updates.added()[0]),'1234:5678::/32 next-hop ::')

#	def test_7_ipv6 (self):
#		txt = ''.join([chr(_) for _ in [0x0, 0x0, 0x0, 0x25, 0x40, 0x1, 0x1, 0x0, 0x40, 0x2, 0x4, 0x2, 0x1, 0xfd, 0xe8, 0xc0, 0x8, 0x8, 0x78, 0x14, 0x0, 0x0, 0x78, 0x14, 0x78, 0x14, 0x40, 0xf, 0xc, 0x0, 0x2, 0x1, 0x40, 0x2a, 0x2, 0xb, 0x80, 0x0, 0x0, 0x0, 0x1]])
#		updates = new_Update(txt)

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = structure
#!/usr/bin/env python
# encoding: utf-8
"""
data.py

Created by Thomas Mangin on 2009-09-06.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import unittest

from exabgp.configuration.environment import environment
env = environment.setup('')

from exabgp.protocol.family import AFI,SAFI
from exabgp.protocol.ip.inet import *

class TestData (unittest.TestCase):
	def test_1_nlri_1 (self):
		self.assertEqual(''.join([chr(c) for c in [32,1,2,3,4]]),to_NLRI('1.2.3.4','32').pack())
	def test_1_nlri_2 (self):
		self.assertEqual(''.join([chr(c) for c in [24,1,2,3]]),to_NLRI('1.2.3.4','24').pack())
	def test_1_nlri_3 (self):
		self.assertEqual(''.join([chr(c) for c in [20,1,2,3]]),to_NLRI('1.2.3.4','20').pack())

	def test_2_ip_2 (self):
		self.assertEqual(str(InetIP('::ffff:192.168.1.26')),'::ffff:192.168.1.26/128')
		self.assertEqual(str(InetIP('::ffff:192.168.1.26').ip),'::ffff:192.168.1.26')

	def test_3_ipv6_1 (self):
		default = InetIP('::')
		self.assertEqual(str(default),'::/128')
		self.assertEqual(default.ip,'::')
		self.assertEqual(default.packedip(),'\0'*16)

	def test_3_ipv6_2 (self):
		default = InetIP('1234:5678::')
		self.assertEqual(str(default),'1234:5678::/128')
		self.assertEqual(default.ip,'1234:5678::')
		self.assertEqual(default.packedip(),'\x12\x34\x56\x78'+'\0'*12)

	def test_3_ipv6_3 (self):
		default = InetIP('1234:5678::1')
		self.assertEqual(str(default),'1234:5678::1/128')
		self.assertEqual(default.ip,'1234:5678::1')
		self.assertEqual(default.packedip(),'\x12\x34\x56\x78'+'\0'*11 + '\x01')

	def test_xxx (self):
		ip = "192.0.2.0"
		net  = chr (192) + chr(0) + chr(2) +chr(0)
		bnt = chr(24) + chr (192) + chr(0) + chr(2)

		pfx = Prefix(AFI.ipv4,ip,24)
		bgp = BGPNLRI(AFI.ipv4,bnt)

		self.assertEqual(str(pfx),"%s/24" % ip)
		self.assertEqual(str(afi),"%s/24" % ip)
		self.assertEqual(str(bgp),"%s/24" % ip)

		self.assertEqual(pfx.pack(),bnt)
		self.assertEqual(afi.pack(),bnt)
		self.assertEqual(bgp.pack(),bnt)

		# README: NEED To add ASN test
		# README: NEED To add NLRI test

if __name__ == '__main__':
	unittest.main()


########NEW FILE########
__FILENAME__ = supervisor
#!/usr/bin/env python
# encoding: utf-8
"""
peer.py

Created by Thomas Mangin on 2009-08-30.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import unittest

from exabgp.configuration.environment import environment
env = environment.setup('')

from exabgp.configuration.file import Configuration
from exabgp.reactor import Reactor

class TestPeer (unittest.TestCase):
	text_configuration = """\
neighbor 192.0.2.181 {
	description "a quagga test peer";
	router-id 192.0.2.92;
	local-address 192.0.2.92;
	local-as 65000;
	peer-as 65000;

	static {
		route 10.0.5.0/24 next-hop 192.0.2.92 local-preference 10 community [ 0x87654321 ];
	}
}
"""

	def setUp(self):
		self.configuration = Configuration(self.text_configuration,True)
		self.assertEqual(self.configuration.reload(),True,"could not read the configuration, run the configuration unittest")

	def test_connection (self):
		reactor = Reactor(self.configuration)
		reactor.run()
		#self.failIf()

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = table
#!/usr/bin/env python
# encoding: utf-8
"""
table.py

Created by Thomas Mangin on 2009-08-25.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import unittest

from exabgp.configuration.environment import environment
env = environment.setup('')

import time

from exabgp.bgp.message.update import Route
from exabgp.rib.table import Table

route1 = Update(to_NLRI('10.0.0.1','32'))
route1.next_hop = '10.0.0.254'

route2 = Update(to_NLRI('10.0.1.1','32'))
route2.next_hop = '10.0.0.254'

route3 = Update(to_NLRI('10.0.2.1','32'))
route3.next_hop = '10.0.0.254'

routes = [route1,route2,route3]
routes.sort()


class TestTable (unittest.TestCase):

	def setUp(self):
		self.now = time.time()

	def test_1_add (self):
		self.table = Table()
		self.table.update(routes)
		changed = [(t,r) for (t,r) in self.table.changed(self.now) if t]
		self.failIf(('+',routes[0]) not in changed)
		self.failIf(('+',routes[1]) not in changed)
		self.failIf('-' in [t for t,r in self.table.changed(self.now) if t])

	def test_2_del_all_but_1 (self):
		self.table = Table()

		self.table.update(routes)
		changed = [(t,r) for (t,r) in self.table.changed(self.now) if t]
		self.failIf(('+',routes[0]) not in changed)
		self.failIf(('+',routes[1]) not in changed)

		self.table.update([routes[1]])
		self.failIf(('-',routes[0]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])
		self.failIf(('+',routes[1]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])
		self.failIf(('-',routes[2]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])


	def test_3_del_all (self):
		self.table = Table()

		self.table.update(routes)
		changed = [(t,r) for (t,r) in self.table.changed(self.now) if t]
		self.failIf(('+',routes[0]) not in changed)
		self.failIf(('+',routes[1]) not in changed)

		self.table.update([])
		self.failIf('+' in [t for (t,r) in self.table.changed(self.now) if t])
		self.failIf(('-',routes[0]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])
		self.failIf(('-',routes[1]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])
		self.failIf(('-',routes[2]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])

	def test_4_multichanges (self):
		self.table = Table()

		self.table.update(routes)
		changed = [(t,r) for (t,r) in self.table.changed(self.now) if t]
		self.failIf(('+',routes[0]) not in changed)
		self.failIf(('+',routes[1]) not in changed)

		self.table.update([routes[1]])
		print '-------------------------'
		print
		print [(t,r) for (t,r) in self.table.changed(self.now) if t]
		print
		self.failIf(('-',routes[0]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])
		self.failIf(('+',routes[1]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])
		self.failIf(('-',routes[2]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])

		self.table.update(routes)
		changed = [(t,r) for (t,r) in self.table.changed(self.now) if t]
		self.failIf(('+',routes[0]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])
		self.failIf(('+',routes[1]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])
		self.failIf(('+',routes[2]) not in [(t,r) for (t,r) in self.table.changed(self.now) if t])

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = update
#!/usr/bin/env python
# encoding: utf-8
"""
update.py

Created by Thomas Mangin on 2009-09-06.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import unittest

from exabgp.configuration.environment import environment
env = environment.setup('')

from exabgp.bgp.message.update.update import *
from exabgp.bgp.message.update.attribute.communities import to_Community, Community, Communities

class TestData (unittest.TestCase):
	def test_2_prefix (self):
		self.assertEqual(str(to_NLRI('10.0.0.0','24')),'10.0.0.0/24')
	def test_6_prefix (self):
		self.assertEqual(to_NLRI('1.2.3.4','0').pack(),''.join([chr(c) for c in [0,]]))
	def test_7_prefix (self):
		self.assertEqual(to_NLRI('1.2.3.4','8').pack(),''.join([chr(c) for c in [8,1,]]))
	def test_8_prefix (self):
		self.assertEqual(to_NLRI('1.2.3.4','16').pack(),''.join([chr(c) for c in [16,1,2]]))
	def test_9_prefix (self):
		self.assertEqual(to_NLRI('1.2.3.4','24').pack(),''.join([chr(c) for c in [24,1,2,3]]))
	def test_10_prefix (self):
		self.assertEqual(to_NLRI('1.2.3.4','32').pack(),''.join([chr(c) for c in [32,1,2,3,4]]))

	def test_1_community (self):
		self.assertEqual(Community(256),256)
	def test_2_community (self):
		self.assertEqual(to_Community('0x100'),256)
	def test_3_community (self):
		self.assertEqual(to_Community('1:1'),65537)
	def test_4_community (self):
		communities = Communities()
		community = to_Community('1:1')
		communities.add(community)
		self.assertEqual(communities.pack(),''.join([chr(c) for c in [0xc0,0x08,0x04,0x00,0x01,0x00,0x01]]))

	def test_1_ipv4 (self):
		header = ''.join([chr(c) for c in [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x0, 0x22, 0x2]])
		message = ''.join([chr(c) for c in [0x0, 0x0, 0x0, 0xb, 0x40, 0x1, 0x1, 0x0, 0x40, 0x2, 0x4, 0x2, 0x1, 0xfd, 0xe8, 0x18, 0xa, 0x0, 0x1]])
		update  = new_Update(message)
		self.assertEqual(str(update.nlri[0]),'10.0.1.0/24')

	def test_1_ipv6_1 (self):
		header = ''.join([chr(c) for c in [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x0, 0x47, 0x2]])
		message = ''.join([chr(c) for c in [0x0, 0x0, 0x0, 0x30, 0x40, 0x1, 0x1, 0x0, 0x50, 0x2, 0x0, 0x4, 0x2, 0x1, 0xff, 0xfe, 0x80, 0x4, 0x4, 0x0, 0x0, 0x0, 0x0, 0x80, 0xe, 0x1a, 0x0, 0x2, 0x1, 0x10, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x20, 0x12, 0x34, 0x56, 0x78]])
		update  = to_Update([],[to_NLRI('1234:5678::',32)])
		self.assertEqual(str(update.nlri[0]),'1234:5678::/32')

	def test_1_ipv6_2 (self):
		route = RouteIP('1234:5678::',64)
		route.next_hop = '8765:4321::1'
		announced = route.announce(1,1)
		message = announced[19:]
		update = new_Update(message)
		print update.nlri
		print update.withdraw
		print update.attributes[MPRNLRI.ID][0]


#	def test_2_ipv4_broken (self):
#		header = ''.join([chr(c) for c in h])
#		message = ''.join([chr(c) for c in m])
#		message = ''.join([chr(c) for c in [0x0, 0x0, 0x0, 0xf, 0x40, 0x1, 0x1, 0x0, 0x40, 0x2, 0x4, 0x2, 0x1, 0xfd, 0xe8, 0x0, 0x0, 0x0, 0x0, 0x18, 0xa, 0x0, 0x1]])
#		update  = new_Update(message)

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = configuration-validation
#!/usr/bin/env python
# encoding: utf-8
"""
protocol.py

Created by Thomas Mangin on 2013-03-23.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import unittest
import tempfile
import os
import cProfile

head = """\
#syntax: simplejson
{
	_: "every key starting with an _ is ignored, but kept"
	_0: "it can be useful to add comment in the configuration file"
	_1: "keep in mind that the configuration has no ordering"
	# to make it easier, the simplejson format allows lines of comments too
	exabgp: 3

	neighbor {
"""

neighbor = """\
 {
			_: "will pass received routes to the program"
			tcp {
				bind: "82.219.212.34"
				connect: "195.8.215.15"
				ttl-security: false
				md5: "secret"
				passive: false
			}
			api {
				syslog-text: [ "receive-routes" ]
				syslog-json: [ "neighbor-changes","send-packets","receive-packets","receive-routes" ]
			}
			session {
				router-id: "82.219.212.34"
				hold-time: 180
				asn {
					local: 65500
					peer: 65500
				}
				capability {
					family {
						ipv4: ["unicast","multicast","nlri-mpls","mpls-vpn","flow-vpn","flow"]
						ipv6: ["unicast"]
						_inet: ["unicast","flow"]
						_alias: "all"
						_alias: "minimal"
					}
					asn4: true
					route-refresh: true
					graceful-restart: false
					multi-session: false
					add-path: false
				}
			}
			announce: [
				"local-routes"
				"off-goes-the-ddos"
			]
		}
"""

tail = """ \
	}

	api {
		_: "the names defined here can be used in the neighbors"
		syslog-json {
			encoder: "json"
			program: "etc/exabgp/processes/syslog-1.py"
		}
		_: "be careful to not loose comment if you use multiple _"
		syslog-text {
			encoder: "text"
			program: "etc/exabgp/processes/syslog-2.py"
		}
	}

	attribute {
		normal-ebgp-attributes {
			origin: "igp"
			as-path: [ 3356, 1239, 38040, 9737 ]
			local-preference: 500
			aggregator: "10.0.0.1"
			atomic-aggregate: false
			originator-id: "10.0.0.1"
			med: 10
			community: [[3356,2], [3356,22], [3356,86], [3356,500], [3356,666], [3356,2064], "no-export"]
			cluster-list: []
			extended-community: []
		}
		simple-attributes {
			next-hop: "212.73.207.153"
			origin: "igp"
			as-path: [ 3356, 1239, 38040, 9737 ]
			local-preference: 500
			aggregator: "10.0.0.1"
			atomic-aggregate: false
			originator-id: "10.0.0.1"
			med: 10
			community: [[3356,2], [3356,22], [3356,86], [3356,500], [3356,666], [3356,2064]]
			cluster-list: []
			extended-community: []
		}
	}

	flow {
		filtering-condition {
			simple-ddos {
				source: "10.0.0.1/32"
				destination: "192.168.0.1/32"
				port: [[["=",80]]]
				protocol: "tcp"
			}
			port-block {
				port: [ [["=",80 ]],[["=",8080]] ]
				destination-port: [ [[">",8080],["<",8088]], [["=",3128]] ]
				source-port: [[[">",1024]]]
				protocol: [ "tcp", "udp" ]
			}
			complex-attack {
				packet-length: [ [[">",200],["<",300]], [[">",400],["<",500]] ]
				_fragment: ["not-a-fragment"]
				fragment: ["first-fragment","last-fragment" ]
				_icmp-type: [ "unreachable", "echo-request", "echo-reply" ]
				icmp-code: [ "host-unreachable", "network-unreachable" ]
				tcp-flags: [ "urgent", "rst" ]
				dscp: [ 10, 20 ]
			}
		}

		filtering-action {
			make-it-slow {
					rate-limit: 9600
			}
			drop-it {
					discard: true
			}
			send-it-elsewhere {
					redirect: "65500:12345"
			}
			send-it-community {
				redirect: "1.2.3.4:5678"
				community: [[30740,0], [30740,30740]]
			}
		}
	}

	update {
		prefix {
			local-routes {
				normal-ebgp-attributes {
					192.168.0.0/24 {
						next-hop: "192.0.2.1"
					}
					192.168.0.0/24 {
						next-hop: "192.0.2.2"
					}
				}
				simple-attributes {
					_: "it is possible to overwrite some previously defined attributes"
					192.168.1.0/24 {
						next-hop: "192.0.2.1"
					}
					192.168.2.0/24 {
					}
				}
			}
			remote-routes {
				simple-attributes {
					10.0.0.0/16 {
						_: "those three can be defined everywhere too, but require the right capability"
						label: [0, 1]
						path-information: 0
						route-distinguisher: "1:0.0.0.0"
						split: 24
					}
				}
			}
		}
		flow {
			off-goes-the-ddos {
				simple-ddos: "make-it-slow"
				port-block: "drop-it"
			}
			saved_just_in_case {
				complex-attack: "send-it-elsewhere"
			}
		}
	}
}
"""

def _make_config(nb_neighbor):
	name = tempfile.mkstemp(suffix='.exa')[1]
	print 'creating configuration file with %d peers : %s' % (nb_neighbor,name),
	try:
		with open(name,'w') as f:
			f.write(head)
			for _ in xrange(nb_neighbor):
				neighbor_name = '\t\tn-%d' % _
				f.write(neighbor_name)
				f.write(neighbor)
			f.write(tail)
		print 'done'
	except Exception:
		print 'failed'
		return ''
	return name

from exabgp.configuration.validation import validation,ValidationError
from exabgp.configuration.loader import load

from exabgp.memory.profiler import profile
@profile
def size(data):
	pass

def test (nb_neighbor):
	print 'testing with %d neighbors' % nb_neighbor

	name = _make_config(nb_neighbor)
	if not name:
		return False,'could not create temporary file'

	try:
		json = load(name)
	except ValidationError,e:
		os.remove(name)
		return False,'configuration parsing failed (parse) %s' % str(e)
	try:
		validation(json)
	except ValidationError,e:
		return False,'configuration parsing failed (validation) %s' % str(e)

	try:
		os.remove(name)
		print 'deleted %s' % name
	except:
		return False,'could not delete temp file'

	return True,json

def profiled (nb_neighbor):
	ok , returned = test(nb_neighbor)
	if ok:
		try:
			size(returned)
		except ValidationError,e:
			print 'configuration parsing failed (size) %s' % str(e)
		return ''
	else:
		print 'profiling failed'

class TestData (unittest.TestCase):

	def test_1 (self):
		if not os.environ.get('profile',False):
			ok, reason = test(2)
			if not ok: self.fail(reason)

	def test_2 (self):
		if not not os.environ.get('profile',False):
			cProfile.run('profiled(20000)')

if __name__ == '__main__':
	unittest.main()


	# import cProfile
	# print 'profiling'
	# cProfile.run('unittest.main()','profile.info')

########NEW FILE########
__FILENAME__ = connection
#!/usr/bin/env python
# encoding: utf-8
"""
connection.py

Created by Thomas Mangin on 2013-07-13.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import os
import sys
import unittest

from exabgp.util.od import od

def test ():
	OPEN = ''.join([chr(int(_,16)) for _ in "FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF 00 1D 01 04 78 14 00 5A 52 DB 00 45 00".split()])
	KEEP = ''.join([chr(int(_,16)) for _ in "FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF 00 00 04".split()])

	from exabgp.reactor.network.outgoing import Outgoing
	connection = Outgoing(1,'82.219.0.5','82.219.212.34')
	writer=connection._writer(OPEN)
	while writer() == False:
		pass
	writer=connection._writer(KEEP)
	while writer() == False:
		pass

	reader=connection.reader()

	for size,kind,header,body in reader:
		if size: print od(header+body)
		else: sys.stdout.write('-')

	reader=connection.reader()

	for size,kind,header,body in reader:
		if size: print od(header+body)
		else: sys.stdout.write('+')

	connection.close()

class TestData (unittest.TestCase):

	def test_1 (self):
		if not os.environ.get('profile',False):
			result = test()
			if result: self.fail(result)

	def test_2 (self):
		if not not os.environ.get('profile',False):
			cProfile.run('test()')

if __name__ == '__main__':
	unittest.main()


	# import cProfile
	# print 'profiling'
	# cProfile.run('unittest.main()','profile.info')

########NEW FILE########
__FILENAME__ = json-parser
#!/usr/bin/env python
# encoding: utf-8
"""
protocol.py

Created by Thomas Mangin on 2013-03-23.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import unittest
import tempfile
import os
import cProfile

configuration = """
{
	"_": "every key starting with an _ is ignored, but kept",
  "_0": "it can be useful to add comment in the configuration file",
	"_1": "keep in mind that the configuration has no ordering",
	"exabgp": 3,
	"neighbor": {
		"n-0": {
			"_": "will pass received routes to the program",
			"tcp": {
				"local": "127.0.0.1",
				"peer": "127.0.0.1",
				"ttl-security": false,
				"md5": "secret"
			},
			"api": {
				"syslog-text": [ "receive-routes" ],
				"syslog-json": [ "neighbor-changes","send-packets","receive-packets","receive-routes" ]
			},
			"session": {
				"router-id": "127.0.0.1",
				"hold-time": 180,
				"asn": {
					"local": 65500,
					"peer": 65500
				},
				"capability": {
					"family": {
						"ipv4": ["unicast","multicast","nlri-mpls","mpls-vpn","flow-vpn","flow"],
						"ipv6": ["unicast"],
						"_ip": ["unicast","flow"],
						"_alias": "all",
						"_alias": "minimal"
					},
					"asn4": true,
					"route-refresh": true,
					"graceful-restart": false,
					"multi-session": false,
					"add-path": false
				}
			},
			"announce": [
				"local-routes",
				"off-goes-the-ddos"
			]
		}
	},
	"api": {
		"_": "the names defined here can be used in the neighbors",
		"syslog-json": {
			"encoder": "json",
			"program": "etc/exabgp/processes/syslog-1.py"
		},
		"_": "be careful to not loose comment if you use multiple _",
		"syslog-text": {
			"encoder": "text",
			"program": "etc/exabgp/processes/syslog-2.py"
		}
	},
	"attribute": {
		"normal-ebgp-attributes": {
			"origin": "igp",
			"as-path": [ 3356, 1239, 38040, 9737 ],
			"local-preference": 500,
			"aggregator": "10.0.0.1",
			"atomic-aggregate": false,
			"originator-id": "10.0.0.1",
			"med": 10,
			"community": [[3356,2], [3356,22], [3356,86], [3356,500], [3356,666], [3356,2064], "no-export"],
			"cluster-list": [],
			"extended-community": []
		},
		"simple-attributes": {
			"next-hop": "212.73.207.153",
			"origin": "igp",
			"as-path": [ 3356, 1239, 38040, 9737 ],
			"local-preference": 500,
			"aggregator": "10.0.0.1",
			"atomic-aggregate": false,
			"originator-id": "10.0.0.1",
			"med": 10,
			"community": [[3356,2], [3356,22], [3356,86], [3356,500], [3356,666], [3356,2064]],
			"cluster-list": [],
			"extended-community": []
		}
	},
	"flow": {
		"filtering-condition": {
			"simple-ddos": {
				"source": "10.0.0.1/32",
				"destination": "192.168.0.1/32",
				"port": [[["=",80]]],
				"protocol": "tcp"
			},
			"port-block": {
				"port": [ [["=",80 ]],[["=",8080]] ],
				"destination-port": [ [[">",8080],["<",8088]], [["=",3128]] ],
				"source-port": [[[">",1024]]],
				"protocol": [ "tcp", "udp" ]
			},
			"complex-attack": {
				"packet-length": [ [[">",200],["<",300]], [[">",400],["<",500]] ],
				"_fragment": ["not-a-fragment"],
				"fragment": ["first-fragment","last-fragment" ],
				"_icmp-type": [ "unreachable", "echo-request", "echo-reply" ],
				"icmp-code": [ "host-unreachable", "network-unreachable" ],
				"tcp-flags": [ "urgent", "rst" ],
				"dscp": [ 10, 20 ]
			}
		},
		"filtering-action": {
			"make-it-slow": {
					"rate-limit": 9600
			},
			"drop-it": {
					"discard": true
			},
			"send-it-elsewhere": {
					"redirect": "65500:12345"
			},
			"send-it-community": {
				"redirect": "1.2.3.4:5678",
				"community": [[30740,0], [30740,30740]]
			}
		}
	},
	"update": {
		"prefix": {
			"local-routes": {
				"normal-ebgp-attributes": {
					"192.168.0.0/24": {
						"next-hop": "192.0.2.1"
					},
					"192.168.0.0/24": {
						"next-hop": "192.0.2.2"
					}
				},
				"simple-attributes": {
					"_": "it is possible to overwrite some previously defined attributes",
					"192.168.1.0/24": {
						"next-hop": "192.0.2.1"
					},
					"192.168.2.0/24": {
					}
				}
			},
			"remote-routes": {
				"simple-attributes": {
					"10.0.0.0/16": {
						"_": "those three can be defined everywhere too, but require the right capability",
						"label": [0, 1],
						"path-information": 0,
						"route-distinguisher": "1:0.0.0.0",
						"split": 24
					}
				}
			}
		},
		"flow": {
			"off-goes-the-ddos": {
				"simple-ddos": "make-it-slow",
				"port-block": "drop-it"
			},
			"saved_just_in_case": {
				"complex-attack": "send-it-elsewhere"
			}
		}
	}
}
"""

def _make_config ():
	name = tempfile.mkstemp(suffix='.exa')[1]
	print 'creating configuration file %s' % name
	with open(name,'w') as f:
		f.write(configuration)
	print 'created'
	return name


def test ():
	from exabgp.configuration.json import load,JSONError

	try:
		name = _make_config()
	except:
		return 'could not create temp file'

	try:
		json = load(name)
	except JSONError,e:
		os.remove(name)
		return 'configuration parsing file: %s' % str(e)

	del json

class TestData (unittest.TestCase):

	def test_1 (self):
		if not os.environ.get('profile',False):
			result = test()
			if result: self.fail(result)

	def test_2 (self):
		if not not os.environ.get('profile',False):
			cProfile.run('test()')

if __name__ == '__main__':
	unittest.main()


	# import cProfile
	# print 'profiling'
	# cProfile.run('unittest.main()','profile.info')

########NEW FILE########
__FILENAME__ = healthcheck
#!/usr/bin/env python

"""Healthchecker for exabgp.

This program is to be used as a process for exabgp. It will announce
some VIP depending on the state of a check whose a third-party program
wrapped by this program.

To use, declare this program as a process in your
:file:`/etc/exabgp/exabgp.conf`::

    neighbor 192.0.2.1 {
       router-id 192.0.2.2;
       local-as 64496;
       peer-as 64497;
    }
    process watch-haproxy {
       run /etc/exabgp/processes/healthcheck.py --cmd "curl -sf http://127.0.0.1/healthcheck";
    }

Use :option:`--help` to get options accepted by this program. A
configuration file is also possible. Such a configuration file looks
like this::

     debug
     name = haproxy
     interval = 10
     fast-interval = 1
     command = curl -sf http://127.0.0.1/healthcheck

The left-part of each line is the corresponding long option.
"""

from __future__ import print_function
from __future__ import unicode_literals

import string
import sys
import os
import subprocess
import re
import logging
import logging.handlers
import argparse
import signal
import errno
import time
import collections
try:
    # Python 3.3+
    from ipaddress import ip_address
except ImportError:
    # Python 2.6, 2.7, 3.2
    from ipaddr import IPAddress as ip_address
try:
    # Python 3.4+
    from enum import Enum
except ImportError:
    # Other versions. This is not really an enum but this is OK for
    # what we want to do.
    def Enum(*sequential):
        return type(str("Enum"), (), dict(zip(sequential, sequential)))

logger = logging.getLogger("healthcheck")

def parse():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    g = parser.add_mutually_exclusive_group()
    g.add_argument("--debug", "-d", action="store_true",
                   default=False,
                   help="enable debugging")
    g.add_argument("--silent", "-s", action="store_true",
                   default=False,
                   help="don't log to console")
    g.add_argument("--syslog-facility", "-sF", metavar="FACILITY",
                   nargs='?',
                   const="daemon",
                   default="daemon",
                   help="log to syslog using FACILITY, default FACILITY is daemon")
    g.add_argument("--no-syslog", action="store_true",
                   help="disable syslog logging")
    parser.add_argument("--name", "-n", metavar="NAME",
                        help="name for this healthchecker")
    parser.add_argument("--config", "-F", metavar="FILE", type=open,
                        help="read configuration from a file")
    parser.add_argument("--pid", "-p", metavar="FILE", type=argparse.FileType('w'),
                        help="write PID to the provided file")

    g = parser.add_argument_group("checking healthiness")
    g.add_argument("--interval", "-i", metavar='N',
                   default=5,
                   type=float,
                   help="wait N seconds between each healthcheck")
    g.add_argument("--fast-interval", "-f", metavar='N',
                   default=1,
                   type=float, dest="fast",
                   help="when a state change is about to occur, wait N seconds between each healthcheck")
    g.add_argument("--timeout", "-t", metavar='N',
                   default=5,
                   type=int,
                   help="wait N seconds for the check command to execute")
    g.add_argument("--rise", metavar='N',
                   default=3,
                   type=int,
                   help="check N times before considering the service up")
    g.add_argument("--fall", metavar='N',
                   default=3,
                   type=int,
                   help="check N times before considering the service down")
    g.add_argument("--disable", metavar='FILE',
                   type=str,
                   help="if FILE exists, the service is considered disabled")
    g.add_argument("--command", "--cmd", "-c", metavar='CMD',
                   type=str,
                   help="command to use for healthcheck")

    g = parser.add_argument_group("advertising options")
    g.add_argument("--next-hop", "-N", metavar='IP',
                   type=ip_address,
                   help="self IP address to use as next hop")
    g.add_argument("--ip", metavar='IP',
                   type=ip_address, dest="ips", action="append",
                   help="advertise this IP address")
    g.add_argument("--no-ip-setup",
                   action="store_false", dest="ip_setup",
                   help="don't setup missing IP addresses")
    g.add_argument("--start-ip", metavar='N',
                   type=int, default=0,
                   help="index of the first IP in the list of IP addresses")
    g.add_argument("--up-metric", metavar='M',
                   type=int, default=100,
                   help="first IP get the metric M when the service is up")
    g.add_argument("--down-metric", metavar='M',
                   type=int, default=1000,
                   help="first IP get the metric M when the service is down")
    g.add_argument("--disabled-metric", metavar='M',
                   type=int, default=500,
                   help="first IP get the metric M when the service is disabled")
    g.add_argument("--increase", metavar='M',
                   type=int, default=1,
                   help="for each additional IP address increase metric value by W")
    g.add_argument("--community", metavar="COMMUNITY",
                   type=str, default=None,
                   help="announce IPs with the supplied community")
    g.add_argument("--withdraw-on-down", action="store_true",
                   help="Instead of increasing the metric on health failure, withdraw the route")

    g = parser.add_argument_group("reporting")
    g.add_argument("--execute", metavar='CMD',
                   type=str, action="append",
                   help="execute CMD on state change")
    g.add_argument("--up-execute", metavar='CMD',
                   type=str, action="append",
                   help="execute CMD when the service becomes available")
    g.add_argument("--down-execute", metavar='CMD',
                   type=str, action="append",
                   help="execute CMD when the service becomes unavailable")
    g.add_argument("--disabled-execute", metavar='CMD',
                   type=str, action="append",
                   help="execute CMD when the service is disabled")

    options = parser.parse_args()
    if options.config is not None:
        # A configuration file has been provided. Read each line and
        # build an equivalent command line.
        args = sum([ "--{0}".format(l.strip()).split("=", 1)
                     for l in options.config.readlines()
                     if not l.strip().startswith("#") and l.strip() ], [])
        args = [ x.strip() for x in args ]
        args.extend(sys.argv[1:])
        options = parser.parse_args(args)
    return options

def setup_logging(debug, silent, name, syslog_facility, syslog):
    """Setup logger"""
    logger.setLevel(debug and logging.DEBUG or logging.INFO)
    enable_syslog = syslog and not debug
    # To syslog
    if enable_syslog:
        facility = getattr(logging.handlers.SysLogHandler,
                           "LOG_{0}".format(string.upper(syslog_facility)))
        sh = logging.handlers.SysLogHandler(address=str("/dev/log"),
                                            facility=facility)
        if name:
            healthcheck_name = "healthcheck-{0}".format(name)
        else:
            healthcheck_name = "healthcheck"
        sh.setFormatter(logging.Formatter(
            "{0}[{1}]: %(message)s".format(healthcheck_name,
                                                    os.getpid())))
        logger.addHandler(sh)
    # To console
    if sys.stderr.isatty() and not silent:
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(
            "%(levelname)s[%(name)s] %(message)s"))
        logger.addHandler(ch)

def loopback_ips():
    """Retrieve loopback IP addresses"""
    logger.debug("Retrieve loopback IP addresses")
    addresses = []

    if sys.platform.startswith("linux"):
        # Use "ip" (ifconfig is not able to see all addresses)
        ipre = re.compile(r"^(?P<index>\d+):\s+(?P<name>\S+)\s+inet6?\s+(?P<ip>[\da-f.:]+)/(?P<netmask>\d+)\s+.*")
        cmd = subprocess.Popen("/sbin/ip -o address show dev lo".split(), shell=False, stdout=subprocess.PIPE)
    else:
        # Try with ifconfig
        ipre = re.compile(r"^\s+inet6?\s+(?P<ip>[\da-f.:]+)\s+(?:netmask 0x(?P<netmask>[0-9a-f]+)|prefixlen (?P<mask>\d+)).*")
        cmd = subprocess.Popen("/sbin/ifconfig lo0".split(), shell=False, stdout=subprocess.PIPE)
    for line in cmd.stdout:
        line = line.decode("ascii", "ignore").strip()
        mo = ipre.match(line)
        if not mo:
            continue
        ip = ip_address(mo.group("ip"))
        if not ip.is_loopback:
            addresses.append(ip)
    if not addresses:
        raise RuntimeError("No loopback IP found")
    logger.debug("Loopback addresses: {0}".format(addresses))
    return addresses

def setup_ips(ips):
    """Setup missing IP on loopback interface"""
    existing = set(loopback_ips())
    toadd = set(ips) - existing
    for ip in toadd:
        logger.debug("Setup loopback IP address {0}".format(ip))
        with open(os.devnull, "w") as fnull:
            subprocess.check_call(["ip", "address", "add", str(ip), "dev", "lo"],
                                  stdout = fnull, stderr = fnull)

def check(cmd, timeout):
    """Check the return code of the given command.

    :param cmd: command to execute. If :keyword:`None`, no command is executed.
    :param timeout: how much time we should wait for command completion.
    :return: :keyword:`True` if the command was successful or
             :keyword:`False` if not or if the timeout was triggered.
    """
    if cmd is None:
        return True
    class Alarm(Exception):
        pass
    def alarm_handler(signum, frame):
        raise Alarm()
    logger.debug("Checking command {0}".format(repr(cmd)))
    p = subprocess.Popen(cmd, shell = True,
                         stdout = subprocess.PIPE,
                         stderr = subprocess.STDOUT)
    if timeout:
        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(timeout)
    try:
        stdout = None
        stdout, _ = p.communicate()
        if timeout:
            signal.alarm(0)
        if p.returncode != 0:
            logger.warn("Check command was unsuccessful: {0}".format(p.returncode))
            if stdout.strip():
                logger.info("Output of check command: {0}".format(stdout))
            return False
        logger.debug("Command was executed successfully {0} {1}".format(p.returncode, stdout))
        return True
    except Alarm:
        logger.warn("Timeout ({0}) while running check command".format(timeout, cmd))
        p.kill()
        return False

def loop(options):

    """Main loop."""
    states = Enum(
        "INIT",                 # Initial state
        "DISABLED",             # Disabled state
        "RISING",               # Checks are currently succeeding.
        "FALLING",              # Checks are currently failing.
        "UP",                   # Service is considered as up.
        "DOWN",                 # Service is considered as down.
    )
    state = states.INIT

    def exabgp(target):
        """Communicate new state to ExaBGP"""
        if target not in (states.UP, states.DOWN, states.DISABLED):
            return
        logger.info("send announces for {0} state to ExaBGP".format(target))
        metric = vars(options).get("{0}_metric".format(str(target).lower()))
        for ip in options.ips:
            announce = "route {0}/{1} next-hop {2} med {3}".format(str(ip),
                                                               ip.max_prefixlen,
                                                               options.next_hop or "self",
                                                               metric)
            if options.community:
                announce = "{0} community [ {1} ]".format(announce, options.community)
            logger.debug("exabgp: {0}".format(announce))
            if options.withdraw_on_down:
                command = "announce" if target is states.UP else "withdraw"
            else:
                command = "announce"
            print("{0} {1}".format(command, announce))
            metric += options.increase
        sys.stdout.flush()

    def trigger(target):
        """Trigger a state change and execute the appropriate commands"""
        # Shortcut for RISING->UP and FALLING->UP
        if target == states.RISING and options.rise <= 1:
            target = states.UP
        elif target == states.FALLING and options.fall <= 1:
            target = states.DOWN

        # Log and execute commands
        logger.debug("Transition to {0}".format(str(target)))
        cmds = []
        cmds.extend(vars(options).get("{0}_execute".format(str(target).lower()), []) or [])
        cmds.extend(vars(options).get("execute", []) or [])
        for cmd in cmds:
            logger.debug("Transition to {0}, execute `{1}`".format(str(target), cmd))
            env = os.environ.copy()
            env.update({ "STATE": str(target) })
            with open(os.devnull, "w") as fnull:
                subprocess.call(cmd, shell = True, stdout = fnull, stderr = fnull,
                                env = env)

        return target

    checks = 0
    while True:
        disabled = options.disable is not None and os.path.exists(options.disable)
        successful = disabled or check(options.command, options.timeout)
        # FSM
        if state != states.DISABLED and disabled:
            state = trigger(states.DISABLED)
        elif state == states.INIT:
            if successful and options.rise <= 1:
                state = trigger(states.UP)
            elif successful:
                state = trigger(states.RISING)
                checks = 1
            else:
                state = trigger(states.FALLING)
                checks = 1
        elif state == states.DISABLED:
            if not disabled:
                state = trigger(states.INIT)
        elif state == states.RISING:
            if successful:
                checks += 1
                if checks >= options.rise:
                    state = trigger(states.UP)
            else:
                state = trigger(states.FALLING)
                checks = 1
        elif state == states.FALLING:
            if not successful:
                checks += 1
                if checks >= options.fall:
                    state = trigger(states.DOWN)
            else:
                state = trigger(states.RISING)
                checks = 1
        elif state == states.UP:
            if not successful:
                state = trigger(states.FALLING)
                checks = 1
        elif state == states.DOWN:
            if successful:
                state = trigger(states.RISING)
                checks = 1
        else:
            raise ValueError("Unhandled state: {0}".format(str(state)))

        # Send announces. We announce them on a regular basis in case
        # we lose connection with a peer.
        exabgp(state)

        # How much we should sleep?
        if state in (states.FALLING, states.RISING):
            time.sleep(options.fast)
        else:
            time.sleep(options.interval)

if __name__ == "__main__":
    options = parse()
    setup_logging(options.debug, options.silent, options.name,
                  options.syslog_facility, not options.no_syslog)
    if options.pid:
        options.pid.write("{0}\n".format(os.getpid()))
        options.pid.close()
    try:
        # Setup IP to use
        options.ips = options.ips or loopback_ips()
        if options.ip_setup:
            setup_ips(options.ips)
        options.ips = collections.deque(options.ips)
        options.ips.rotate(-options.start_ip)
        options.ips = list(options.ips)
        # Main loop
        loop(options)
    except Exception as e:
        logger.exception("Uncatched exception: %s", e)

########NEW FILE########
__FILENAME__ = read-write
#!/usr/bin/env python

import os
import sys
import errno
import fcntl
import select

errno_block = set((
	errno.EINPROGRESS, errno.EALREADY,
	errno.EAGAIN, errno.EWOULDBLOCK,
	errno.EINTR, errno.EDEADLK,
	errno.EBUSY, errno.ENOBUFS,
	errno.ENOMEM,
))

errno_fatal = set((
	errno.ECONNABORTED, errno.EPIPE,
	errno.ECONNREFUSED, errno.EBADF,
	errno.ESHUTDOWN, errno.ENOTCONN,
	errno.ECONNRESET, errno.ETIMEDOUT,
	errno.EINVAL,
))

errno_unavailable = set((
	errno.ECONNREFUSED, errno.EHOSTUNREACH,
))

def async (fd):
	try:
		fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
		return True
	except IOError:
		return False

def sync (fd):
	try:
		fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NDELAY)
		return True
	except IOError:
		return False

if not async(sys.stdin):
	print >> sys.stderr, "could not set stdin/stdout non blocking"
	sys.stderr.flush()
	sys.exit(1)

def _reader ():
	received = ''

	while True:
		try:
			data = sys.stdin.read(4096)
		except IOError,e:
			if e.args[0] in errno_block:
				yield ''
				continue
			elif e.args[0] in errno_fatal:
				print >> sys.stderr, "fatal error while reading on stdin : %s" % str(e)
				sys.exit(1)


		received += data
		if '\n' in received:
			line,received = received.split('\n',1)
			yield line + '\n'
		else:
			yield ''

reader = _reader().next


def write (data='',left=''):
	left += data
	try:
		if left:
			number = sys.stdout.write(left)
			left = left[number:]
			sys.stdout.flush()
	except IOError,e:
		if e.args[0] in errno_block:
			return not not left
		elif e.args[0] in errno_fatal:
			# this may not send anything ...
			print >> sys.stderr, "fatal error while reading on stdin : %s" % str(e)
			sys.stderr.flush()
			sys.exit(1)

	return not not left

def read (timeout):
	try:
		r, w, x = select.select([sys.stdin], [], [sys.stdin,], timeout)
	except IOError, e:
		if e.args[0] in errno_block:
			return ''
		elif e.args[0] in errno_fatal:
			# this may not send anything ...
			print >> sys.stderr, "fatal error during select : %s" % str(e)
			sys.stderr.flush()
			sys.exit(1)
		else:
			# this may not send anything ...
			print >> sys.stderr, "unexpected error during select : %s" % str(e)
			sys.stderr.flush()
			sys.exit(1)

	if not r:
		return ''

	line = reader()
	if not line:
		return ''

	return line


announce = ['announce route 192.0.2.%d next-hop 10.0.0.1\n' % ip for ip in range(1,255)]

leftover  = False
try:
	while True:
		received = read(1.0)  # wait for a maximum of one second
		if received:
			# do something with the data received
			pass

		more,announce = announce[:10],announce[10:]

		if more:
			leftover = write(''.join(more))
		elif leftover:
			# echo back what we got
			leftover = write()
except Exception,e:
	sync(sys.stdin)

########NEW FILE########
__FILENAME__ = syslog-1
#!/usr/bin/env python

import os
import sys
import time
import syslog

def _prefixed (level,message):
	now = time.strftime('%a, %d %b %Y %H:%M:%S',time.localtime())
	return "%s %-8s %-6d %s" % (now,level,os.getpid(),message)

syslog.openlog("ExaBGP")

# When the parent dies we are seeing continual newlines, so we only access so many before stopping
counter = 0

while True:
	try:
		line = sys.stdin.readline().strip()
		if line == "":
			counter += 1
			if counter > 100:
				break
			continue

		counter = 0

		syslog.syslog(syslog.LOG_ALERT, _prefixed('INFO',line))
	except KeyboardInterrupt:
		pass
	except IOError:
		# most likely a signal during readline
		pass

########NEW FILE########
__FILENAME__ = bgp
# encoding: utf-8
"""
exabgp.py

Created by Thomas Mangin on 2009-08-30.
Copyright (c) 2009 Exa Networks. All rights reserved.
"""

import os
import sys
import syslog
import argparse

from exabgp.version import version
# import before the fork to improve copy on write memory savings
from exabgp.reactor import Reactor

import string

def is_hex (s):
	return all(c in string.hexdigits or c == ':' for c in s)

def __exit(memory,code):
	if memory:
		from exabgp.memory import objgraph
		print "memory utilisation"
		print
		print objgraph.show_most_common_types(limit=20)
		print
		print
		print "generating memory utilisation graph"
		print
		obj = objgraph.by_type('Reactor')
		objgraph.show_backrefs([obj], max_depth=10)
	sys.exit(code)


def main ():
	main = int(sys.version[0])
	secondary = int(sys.version[2])

	if main != 2 or secondary < 5:
		sys.exit('This program can not work (is not tested) with your python version (< 2.5 or >= 3.0)')

	parser = argparse.ArgumentParser(
		prog='exabgp',
		description='The BGP swiss army knife of networking',
		add_help=False,
		epilog="""
ExaBGP will automatically look for its configuration file (in windows ini format)
 - in the etc/exabgp folder located within the extracted tar.gz
 - in /etc/exabgp/exabgp.env

Individual configuration options can be set using environment variables, such as :
   > env exabgp.daemon.daemonize=true ./sbin/exabgp
or > env exabgp.daemon.daemonize=true ./sbin/exabgp
or > export exabgp.daemon.daemonize=true; ./sbin/exabgp

Multiple environment values can be set
and the order of preference is :
 - 1 : command line environment value using dot separated notation
 - 2 : exported value from the shell using dot separated notation
 - 3 : command line environment value using underscore separated notation
 - 4 : exported value from the shell using underscore separated notation
 - 5 : the value in the ini configuration file
 - 6 : the built-in defaults

For example :
> env exabgp.profile.enable=true \\
      exabgp.profile.file=~/profile.log  \\
      exabgp.log.packets=true \\
      exabgp.log.destination=host:127.0.0.1 \\
      exabgp.daemon.user=wheel \\
      exabgp.daemon.daemonize=true \\
      exabgp.daemon.pid=/var/run/exabpg.pid \\
   ./bin/exabgp ./etc/bgp/configuration.txt

The program configuration can be controlled using signals:
 - SIGLARM : restart ExaBGP
 - SIGUSR1 : reload the configuration
 - SIGUSR2 : reload the configuration and the forked processes
 - SIGTERM : terminate ExaBGP
 - SIGHUP  : terminate ExaBGP (does NOT reload the configuration anymore)
""",
		formatter_class=argparse.RawTextHelpFormatter
	)

	g = parser.add_mutually_exclusive_group()
	g.add_argument(
		"--help", "-h",
		action="store_true", default=False,
		help="exabgp manual page"
	)

	parser.add_argument(
		'configuration',
		nargs='*',
		help='peer and route configuration file'
	)

	parser.add_argument(
		"--version", "-v",
		action="store_true", default=False,
		help="shows ExaBGP version"
	)
	parser.add_argument(
		"--folder", "-f",
		help="configuration folder"
	)
	parser.add_argument(
		"--env", "-e",
		default='exabgp.env',
		help="environment configuration file"
	)

	g = parser.add_mutually_exclusive_group()
	g.add_argument(
		"--diff-env", "-de",
		action="store_true", default=False,
		help="display non-default configurations values using the env format"
	)
	g.add_argument(
		"--full-env", "-fe",
		action="store_true", default=False,
		help="display the configuration using the env format"
	)
	g.add_argument(
		"--full-ini", "-fi",
		action="store_true", default=False,
		help="display the configuration using the ini format"
	)
	g.add_argument(
		"--diff-ini", "-di",
		action="store_true", default=False,
		help="display non-default configurations values using the ini format"
	)

	g = parser.add_argument_group("debugging")
	g.add_argument(
		"--debug", "-d",
		action="store_true", default=False,
		help="start the python debugger on serious logging and on SIGTERM\n"
		"shortcut for exabgp.log.all=true exabgp.log.level=DEBUG"
	)
	g.add_argument(
		"--once", "-1",
		action="store_true", default=False,
		help="only perform one attempt to connect to peers (used for debugging)"
	)
	g.add_argument(
		"--pdb", "-p",
		action="store_true", default=False,
		help="fire the debugger on critical logging, SIGTERM, and exceptions\n"
		"shortcut for exabgp.pdb.enable=true\n"
	)
	g.add_argument(
		"--memory", '-s',  # can not be -m it conflict with python -m for modules
		action="store_true", default=False,
		help="display memory usage information on exit"
	)
	g.add_argument(
		"--profile",
		metavar="PROFILE",
		help="enable profiling\n"
		"shortcut for exabgp.profile.enable=true exabgp.profle=file=<file>"
	)
	g.add_argument(
		"--test", "-t",
		action="store_true", default=False,
		help="perform a configuration validity check only"
	)
	g.add_argument(
		"--decode", "-x",  # can not be -d it conflicts with --debug
		metavar="HEX_MESSAGE",
		nargs='+',
		help="decode a raw route packet in hexadecimal string"
	)

	options = parser.parse_args()

	if options.version:
		sys.stdout.write(version)
		sys.exit(0)

	if options.decode:
		decode = ''.join(options.decode).replace(':','')
		if not is_hex(decode):
			parser.print_help()
			print "\n\n" \
					"The BGP message must be an hexadecimal string." \
					"all colon or spaces are ignored, here is one example ie:\n" \
					" --decode 001E0200000007900F0003000101\n" \
					" --decode 001E:02:0000:0007:900F:0003:0001:01\n" \
					" --deocde FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF001E0200000007900F0003000101\n" \
					" --decode FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:001E:02:0000:0007:900F:0003:0001:01\n" \
					" --decode 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF 001E02 00000007900F0003000101'\n"
			sys.exit(1)
	else:
		decode = ''

	if options.folder:
		etc = os.path.realpath(os.path.normpath(options.folder))
	else:
		etc = os.path.realpath(os.path.normpath(os.environ.get('ETC','etc')))
	os.environ['ETC'] = etc

	if not options.env.startswith('/'):
		envfile = '%s/%s' % (etc,options.env)
	else:
		envfile = options.env

	from exabgp.configuration.environment import environment

	environment.application = 'exabgp'
	environment.configuration = {
		'profile' : {
			'enable'        : (environment.boolean,environment.lower,'false',    'toggle profiling of the code'),
			'file'          : (environment.unquote,environment.quote,'',         'profiling result file, none means stdout, no overwriting'),
		},
		'pdb' : {
			'enable'        : (environment.boolean,environment.lower,'false',    'on program fault, start pdb the python interactive debugger'),
		},
		'daemon' : {
	#		'identifier'    : (environment.unquote,environment.nop,'ExaBGP',     'a name for the log (to diferenciate multiple instances more easily)'),
			'pid'           : (environment.unquote,environment.quote,'',         'where to save the pid if we manage it'),
			'user'          : (environment.user,environment.quote,'nobody',      'user to run as'),
			'daemonize'     : (environment.boolean,environment.lower,'false',    'should we run in the background'),
		},
		'log' : {
			'enable'        : (environment.boolean,environment.lower,'true',     'enable logging'),
			'level'         : (environment.syslog_value,environment.syslog_name,'INFO', 'log message with at least the priority SYSLOG.<level>'),
			'destination'   : (environment.unquote,environment.quote,'stdout', 'where logging should log\n' \
			                  '                                  syslog (or no setting) sends the data to the local syslog syslog\n' \
			                  '                                  host:<location> sends the data to a remote syslog server\n' \
			                  '                                  stdout sends the data to stdout\n' \
			                  '                                  stderr sends the data to stderr\n' \
			                  '                                  <filename> send the data to a file' \
			),
			'all'           : (environment.boolean,environment.lower,'false',    'report debug information for everything'),
			'configuration' : (environment.boolean,environment.lower,'true',     'report command parsing'),
			'reactor'       : (environment.boolean,environment.lower,'true',     'report signal received, command reload'),
			'daemon'        : (environment.boolean,environment.lower,'true',     'report pid change, forking, ...'),
			'processes'     : (environment.boolean,environment.lower,'true',     'report handling of forked processes'),
			'network'       : (environment.boolean,environment.lower,'true',     'report networking information (TCP/IP, network state,...)'),
			'packets'       : (environment.boolean,environment.lower,'false',    'report BGP packets sent and received'),
			'rib'           : (environment.boolean,environment.lower,'false',    'report change in locally configured routes'),
			'message'       : (environment.boolean,environment.lower,'false',    'report changes in route announcement on config reload'),
			'timers'        : (environment.boolean,environment.lower,'false',    'report keepalives timers'),
			'routes'        : (environment.boolean,environment.lower,'false',    'report received routes'),
			'parser'        : (environment.boolean,environment.lower,'false',    'report BGP message parsing details'),
			'short'         : (environment.boolean,environment.lower,'false',    'use short log format (not prepended with time,level,pid and source)'),
		},
		'tcp' : {
			'timeout' : (environment.integer,environment.nop,'1',   'time we will wait on select (can help with unstable BGP multihop)\n'
			                                                        '%sVERY dangerous use only if you understand BGP very well.' % (' '* 34)),
			'once': (environment.boolean,environment.lower,'false', 'only one tcp connection attempt per peer (for debuging scripts)'),
			'delay': (environment.integer,environment.nop,'0',      'start to announce route when the minutes in the hours is a modulo of this number'),
			'bind': (environment.optional_ip,environment.quote,'', 'IP to bind on when listening (no ip to disable)'),
			'port': (environment.integer,environment.nop,'179', 'port to bind on when listening'),
			'acl': (environment.boolean,environment.lower,'', '(experimental) unimplemented'),
		},
		'bgp' : {
			'openwait': (environment.integer,environment.nop,'60','how many second we wait for an open once the TCP session is established'),
		},
		'cache' : {
			'attributes'  :  (environment.boolean,environment.lower,'true', 'cache routes attributes (configuration and wire) for faster parsing'),
			'nexthops'    :  (environment.boolean,environment.lower,'true', 'cache routes next-hops'),
		},
		'api' : {
			'encoder'  :  (environment.api,environment.lower,'text', '(experimental) encoder to use with with external API (text or json)'),
		},
		'reactor' : {
			'speed' : (environment.real,environment.nop,'1.0', 'time of one reactor loop\n'
			                                                   '%suse only if you understand the code.' % (' '* 34)),
		},
		# Here for internal use
		'internal' : {
			'name'    : (environment.nop,environment.nop,'ExaBGP', 'name'),
			'version' : (environment.nop,environment.nop,version,  'version'),
		},
		# Here for internal use
		'debug' : {
			'pdb' : (environment.boolean,environment.lower,'false','enable python debugger on errors'),
			'memory' : (environment.boolean,environment.lower,'false','command line option --memory'),
			'configuration' : (environment.boolean,environment.lower,'false','undocumented option: raise when parsing configuration errors'),
			'selfcheck' : (environment.boolean,environment.lower,'false','does a self check on the configuration file'),
			'route' : (environment.unquote,environment.quote,'','decode the route using the configuration'),
			'defensive' : (environment.boolean,environment.lower,'false', 'generate random fault in the code in purpose'),
		},
	}

	try:
		env = environment.setup(envfile)
	except environment.Error,e:
		parser.print_help()
		print '\nconfiguration issue,', str(e)
		sys.exit(1)

	if options.help:
		parser.print_help()
		print '\n\nEnvironment values are:\n' + '\n'.join(' - %s' % _ for _ in environment.default())
		sys.exit(0)

	if options.decode:
		env.log.parser = True
		env.debug.route = decode
		env.tcp.bind = ''

	if options.profile:
		env.profile.enable = True
		if options.profile.lower() in ['1','true']:
			env.profile.file = True
		elif options.profile.lower() in ['0','false']:
			env.profile.file = False
		else:
			env.profile.file = options.profile

	if envfile and not os.path.isfile(envfile):
		comment = 'environment file missing\ngenerate it using "exabgp -fi > %s"' % envfile
	else:
		comment = ''

	if options.full_ini:
		for line in environment.iter_ini():
			print line
		sys.exit(0)

	if options.full_env:
		print
		for line in environment.iter_env():
			print line
		sys.exit(0)

	if options.diff_ini:
		for line in environment.iter_ini(True):
			print line
		sys.exit(0)

	if options.diff_env:
		for line in environment.iter_env(True):
			print line
		sys.exit(0)

	if options.once:
		env.tcp.once = True

	if options.debug:
		env.log.all = True
		env.log.level=syslog.LOG_DEBUG

	if options.pdb:
		# The following may fail on old version of python (but is required for debug.py)
		os.environ['PDB'] = 'true'
		env.debug.pdb = True

	if options.test:
		env.debug.selfcheck = True
		env.log.parser = True

	if options.memory:
		env.debug.memory = True


	configurations = []
	# check the file only once that we have parsed all the command line options and allowed them to run
	if options.configuration:
		for f in options.configuration:
			configurations.append(os.path.realpath(os.path.normpath(f)))
	else:
		parser.print_help()
		print '\nno configuration file provided'
		sys.exit(1)

	for configuration in configurations:
		if not os.path.isfile(configuration):
			from exabgp.logger import Logger
			logger = Logger()
			logger.configuration('the argument passed as configuration is not a file','error')
			sys.exit(1)

	from exabgp.bgp.message.update.attribute.nexthop import NextHop
	NextHop.caching = env.cache.nexthops

	from exabgp.bgp.message.update.attribute.communities import Community
	Community.caching = env.cache.attributes

	if len(configurations) == 1:
		run(env,comment,configuration)

	if not (env.log.destination in ('syslog','stdout','stderr') or env.log.destination.startswith('host:')):
		from exabgp.logger import Logger
		logger = Logger()
		logger.configuration('can not log to files when running multiple configuration (as we fork)','error')
		sys.exit(1)

	try:
		# run each configuration in its own process
		pids = []
		for configuration in configurations:
			pid = os.fork()
			if pid == 0:
				run(env,comment,configuration,os.getpid())
			else:
				pids.append(pid)

		# If we get a ^C / SIGTERM, ignore just continue waiting for our child process
		import signal
		signal.signal(signal.SIGINT, signal.SIG_IGN)

		# wait for the forked processes
		for pid in pids:
			os.waitpid(pid,0)
	except OSError, e:
		from exabgp.logger import Logger
		logger = Logger()
		logger.reactor('Can not fork, errno %d : %s' % (e.errno,e.strerror),'critical')

def run (env,comment,configuration,pid=0):
	from exabgp.logger import Logger
	logger = Logger()

	if comment:
		logger.configuration(comment)

	if not env.profile.enable:
		Reactor(configuration).run()
		__exit(env.debug.memory,0)

	try:
		import cProfile as profile
	except:
		import profile

	if not env.profile.file or env.profile.file == 'stdout':
		profile.run('Reactor(configuration).run()')
		__exit(env.debug.memory,0)

	if pid:
		profile_name = "%s-pid-%d" % (env.profile.file,pid)
	else:
		profile_name = env.profile.file

	notice = ''
	if os.path.isdir(profile_name):
		notice = 'profile can not use this filename as outpout, it is not a directory (%s)' % profile_name
	if os.path.exists(profile_name):
		notice = 'profile can not use this filename as outpout, it already exists (%s)' % profile_name

	if not notice:
		logger.profile('profiling ....')
		profile.run('Reactor(configuration).run()',filename=profile_name)
		__exit(env.debug.memory,0)
	else:
		logger.profile("-"*len(notice))
		logger.profile(notice)
		logger.profile("-"*len(notice))
		Reactor(configuration).run()
		__exit(env.debug.memory,0)


if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = bmp
#!/usr/bin/env python
# encoding: utf-8
"""
peer.py

Created by Thomas Mangin on 2013-02-20.
Copyright (c) 2009-2012 Exa Networks. All rights reserved.
"""

import os
import sys

import pwd
import socket
import select
import asyncore

from struct import unpack

from exabgp.version import version
from exabgp.reactor.network.error import error
from exabgp.reactor.api.encoding import JSON
from exabgp.bgp.message.update.factory import UpdateFactory

from exabgp.bmp.header import Header
from exabgp.bmp.message import Message
from exabgp.bmp.negotiated import FakeNegotiated

class BMPHandler (asyncore.dispatcher_with_send):
	wire = False
	update = True

	def announce (self,*args):
		print >> self.fd, self.ip, self.port, ' '.join(str(_) for _ in args) if len(args) > 1 else args[0]

	def setup (self,env,ip,port):
		self.handle = {
			Message.ROUTE_MONITORING : self._route,
			Message.STATISTICS_REPORT : self._statistics,
			Message.PEER_DOWN_NOTIFICATION : self._peer,
		}
		self.asn4 = env.bmp.asn4
		self.use_json = env.bmp.json
		self.fd = env.fd
		self.ip = ip
		self.port = port
		self.json = JSON('3.0')
		return self

	def _read_data (self,number):
		header = ''
		left = number
		while left:
			try:
				r,_,_ = select.select([self], [], [], 1.0)
			except select.error,e:
				return None

			if not r:
				continue

			try:
				data = self.recv(left)
			except socket.error, e:
				if e.args[0] in error.block:
					continue
				print "problem reading on socket", str(e)
				return None

			left -= len(data)
			header += data

			if left and not data:
				# the TCP session is gone.
				print "TCP connection closed"
				self.close()
				return None
		return header

	def handle_read (self):
		data = self._read_data(44)
		if data is None:
			self.close()
			return
		header = Header(data)
		if not header.validate():
			print "closeing tcp connection following an invalid header"
			self.close()

		self.handle[header.message](header)

	def _route (self,header):
		bgp_header = self._read_data(19)
		if bgp_header is None:
			self.close()
			return
		length = unpack('!H',bgp_header[16:18])[0] - 19
		bgp_body = self._read_data(length)
		if bgp_body is None:
			self.close()
			return

		negotiated = FakeNegotiated(header,self.asn4)
		update = UpdateFactory(negotiated,bgp_body)
		if self.use_json:
			print >> self.fd, self.json.bmp(self.ip,update)
		else:
			for route in update.routes:
				print >> self.fd, route.extensive()

	def _statistics (self,header):
		pass

	def _peer (self,header):
		pass

class BMPServer(asyncore.dispatcher):
	def __init__(self, env):
		self.env = env
		host = env.bmp.host
		port = env.bmp.port
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind((host, port))
		self.listen(5)

	def handle_accept(self):
		pair = self.accept()
		if pair is not None:
			sock, addr = pair
			print "new BGP connection from", addr
			handler = BMPHandler(sock).setup(self.env,*addr)

def drop ():
	uid = os.getuid()
	gid = os.getgid()

	if uid and gid:
		return

	for name in ['nobody',]:
		try:
			user = pwd.getpwnam(name)
			nuid = int(user.pw_uid)
			ngid = int(user.pw_uid)
		except KeyError:
			pass

	if not gid:
		os.setgid(ngid)
	if not uid:
		os.setuid(nuid)


from exabgp.configuration.environment import environment

environment.application = 'exabmp'
environment.configuration = {
	'pdb' : {
		'enable'        : (environment.boolean,environment.lower,'false',    'on program fault, start pdb the python interactive debugger'),
	},
	'bmp' : {
		'host' : (environment.nop,environment.nop,'localhost', 'port for the daemon to listen on'),
		'port' : (environment.integer,environment.nop,'1790',  'port for the daemon to listen on'),
		'asn4' : (environment.boolean,environment.lower,'true', 'are the route received by bmp in RFC4893 format'),
		'json' : (environment.boolean,environment.lower,'true', 'use json encoding of parsed route'),
	},
# 	'daemon' : {
# #		'identifier'    : (environment.unquote,environment.nop,'ExaBGP',     'a name for the log (to diferenciate multiple instances more easily)'),
# 		'pid'           : (environment.unquote,environment.quote,'',         'where to save the pid if we manage it'),
# 		'user'          : (environment.user,environment.quote,'nobody',      'user to run as'),
# 		'daemonize'     : (environment.boolean,environment.lower,'false',    'should we run in the background'),
# 	},
	'log' : {
		'enable'        : (environment.boolean,environment.lower,'true',     'enable logging'),
		'level'         : (environment.syslog_value,environment.syslog_name,'INFO', 'log message with at least the priority SYSLOG.<level>'),
		'destination'   : (environment.unquote,environment.quote,'stdout', 'where logging should log\n' \
		                  '                                  syslog (or no setting) sends the data to the local syslog syslog\n' \
		                  '                                  host:<location> sends the data to a remote syslog server\n' \
		                  '                                  stdout sends the data to stdout\n' \
		                  '                                  stderr sends the data to stderr\n' \
		                  '                                  <filename> send the data to a file' \
		),
		'all'           : (environment.boolean,environment.lower,'false',    'report debug information for everything'),
		'configuration' : (environment.boolean,environment.lower,'false',    'report command parsing'),
		'reactor'       : (environment.boolean,environment.lower,'true',     'report signal received, command reload'),
		'daemon'        : (environment.boolean,environment.lower,'true',     'report pid change, forking, ...'),
		'processes'     : (environment.boolean,environment.lower,'true',     'report handling of forked processes'),
		'network'       : (environment.boolean,environment.lower,'true',     'report networking information (TCP/IP, network state,...)'),
		'packets'       : (environment.boolean,environment.lower,'false',    'report BGP packets sent and received'),
		'rib'           : (environment.boolean,environment.lower,'false',    'report change in locally configured routes'),
		'message'       : (environment.boolean,environment.lower,'false',    'report changes in route announcement on config reload'),
		'timers'        : (environment.boolean,environment.lower,'false',    'report keepalives timers'),
		'routes'        : (environment.boolean,environment.lower,'false',    'report received routes'),
		'parser'        : (environment.boolean,environment.lower,'false',    'report BGP message parsing details'),
		'short'         : (environment.boolean,environment.lower,'false',    'use short log format (not prepended with time,level,pid and source)'),
	},
	'cache' : {
		'attributes'  :  (environment.boolean,environment.lower,'true', 'cache routes attributes (configuration and wire) for faster parsing'),
		'nexthops'    :  (environment.boolean,environment.lower,'true', 'cache routes next-hops'),
	},
	# 'api' : {
	# 	'encoder'  :  (environment.api,environment.lower,'text', '(experimental) encoder to use with with external API (text or json)'),
	# },
	# Here for internal use
	'internal' : {
		'name'    : (environment.nop,environment.nop,'ExaBMP', 'name'),
		'version' : (environment.nop,environment.nop,version,  'version'),
	},
	# # Here for internal use
	# 'debug' : {
	# 	'memory' : (environment.boolean,environment.lower,'false','command line option --memory'),
	# },
}

env = environment.setup('')

try:
	os.dup2(2,3)
	env.fd = os.fdopen(3, "w+")
except:
	print "can not setup a descriptor of FD 3 for route display"
	sys.exit(1)

server = BMPServer(env)
drop()

try:
	asyncore.loop()
except:
	pass

########NEW FILE########
__FILENAME__ = direction
# encoding: utf-8
"""
direction.py

Created by Thomas Mangin on 2013-08-07.
Copyright (c) 2009-2013  Exa Networks. All rights reserved.
"""

from exabgp.util.enumeration import Enumeration

OUT = Enumeration ('announce','withdraw')
IN  = Enumeration ('announced','withdrawn')

########NEW FILE########
__FILENAME__ = keepalive
# encoding: utf-8
"""
keepalive.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message import Message

# =================================================================== KeepAlive

class KeepAlive (Message):
	TYPE = chr(Message.Type.KEEPALIVE)

	def message (self):
		return self._message('')

	def __str__ (self):
		return "KEEPALIVE"

########NEW FILE########
__FILENAME__ = nop
# encoding: utf-8
"""
nop.py

Created by Thomas Mangin on 2009-11-06.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message import Message

class NOP (Message):
	TYPE = chr(Message.Type.NOP)

	def message (self):
		return self._message(self.data)

	def __str__ (self):
		return "NOP"

def NOPFactory (self):
	return NOP()

_NOP = NOP()

########NEW FILE########
__FILENAME__ = notification
# encoding: utf-8
"""
notification.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message import Message

# =================================================================== Notification
# A Notification received from our peer.
# RFC 4271 Section 4.5

# 0                   1                   2                   3
# 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# | Error code    | Error subcode |   Data (variable)             |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


class Notification (Message):
	TYPE = chr(Message.Type.NOTIFICATION)

	_str_code = {
		1 : "Message header error",
		2 : "OPEN message error",
		3 : "UPDATE message error",
		4 : "Hold timer expired",
		5 : "State machine error",
		6 : "Cease"
	}

	_str_subcode = {
		(1,0) : "Unspecific.",
		(1,1) : "Connection Not Synchronized.",
		(1,2) : "Bad Message Length.",
		(1,3) : "Bad Message Type.",

		(2,0) : "Unspecific.",
		(2,1) : "Unsupported Version Number.",
		(2,2) : "Bad Peer AS.",
		(2,3) : "Bad BGP Identifier.",
		(2,4) : "Unsupported Optional Parameter.",
		(2,5) : "Authentication Notification (Deprecated).",
		(2,6) : "Unacceptable Hold Time.",
		# RFC 5492
		(2,7) : "Unsupported Capability",

		# draft-ietf-idr-bgp-multisession-06
		(2,8) : "Grouping Conflict",
		(2,9) : "Grouping Required",
		(2,10) : "Capability Value Mismatch",

		(3,0) : "Unspecific.",
		(3,1) : "Malformed Attribute List.",
		(3,2) : "Unrecognized Well-known Attribute.",
		(3,3) : "Missing Well-known Attribute.",
		(3,4) : "Attribute Flags Error.",
		(3,5) : "Attribute Length Error.",
		(3,6) : "Invalid ORIGIN Attribute.",
		(3,7) : "AS Routing Loop.",
		(3,8) : "Invalid NEXT_HOP Attribute.",
		(3,9) : "Optional Attribute Error.",
		(3,10) : "Invalid Network Field.",
		(3,11) : "Malformed AS_PATH.",

		(4,0) : "Unspecific.",

		(5,0) : "Unspecific.",
		# RFC 6608
		(5,1) : "Receive Unexpected Message in OpenSent State.",
		(5,2) : "Receive Unexpected Message in OpenConfirm State.",
		(5,3) : "Receive Unexpected Message in Established State.",

		(6,0) : "Unspecific.",
		# RFC 4486
		(6,1) : "Maximum Number of Prefixes Reached",
		(6,2) : "Administrative Shutdown",
		(6,3) : "Peer De-configured",
		(6,4) : "Administrative Reset",
		(6,5) : "Connection Rejected",
		(6,6) : "Other Configuration Change",
		(6,7) : "Connection Collision Resolution",
		(6,8) : "Out of Resources",
		# draft-keyur-bgp-enhanced-route-refresh-00
		(7,1) : "Invalid Message Length",
		(7,2) : "Malformed Message Subtype",
	}

	def __init__ (self,code,subcode,data=''):
		self.code = code
		self.subcode = subcode
		self.data = data

	def __str__ (self):
		return "%s / %s%s" % (
			self._str_code.get(self.code,'unknown error'),
			self._str_subcode.get((self.code,self.subcode),'unknow reason'),
			'%s' % ('/ %s' % self.data if self.data else '')
		)


def NotificationFactory (data):
	return Notification(ord(data[0]),ord(data[1]),data[2:])



# =================================================================== Notify
# A Notification we need to inform our peer of.

class Notify (Notification):
	def __init__ (self,code,subcode,data=None):
		if data is None:
			data = self._str_subcode.get((code,subcode),'unknown notification type')
		Notification.__init__(self,code,subcode,data)

	def message (self):
		return self._message("%s%s%s" % (
			chr(self.code),
			chr(self.subcode),
			self.data
		))

########NEW FILE########
__FILENAME__ = asn
# encoding: utf-8
"""
asn.py

Created by Thomas Mangin on 2010-01-15.
Copyright (c) 2009-2013  Exa Networks. All rights reserved.
"""


from struct import pack

# =================================================================== ASN

class ASN (long):
	def asn4 (self):
		return self > pow(2,16)

	def pack (self,asn4=None):
		if asn4 is None:
			asn4 = self.asn4()
		if asn4:
			return pack('!L',self)
		return pack('!H',self)

	def __len__ (self):
		if self.asn4():
			return 4
		return 2

	def extract (self):
		return [pack('!L',self)]

	def trans (self):
		if self.asn4():
			return AS_TRANS.pack()
		return self.pack()

AS_TRANS = ASN(23456)

########NEW FILE########
__FILENAME__ = addpath
# encoding: utf-8
"""
addpath.py

Created by Thomas Mangin on 2012-07-17.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import pack

# =================================================================== AddPath

class AddPath (dict):
	string = {
		0 : 'disabled',
		1 : 'receive',
		2 : 'send',
		3 : 'send/receive',
	}

	def __init__ (self,families=[],send_receive=0):
		for afi,safi in families:
			self.add_path(afi,safi,send_receive)

	def add_path (self,afi,safi,send_receive):
		self[(afi,safi)] = send_receive

	def __str__ (self):
		return 'AddPath(' + ','.join(["%s %s %s" % (self.string[self[aafi]],xafi,xsafi) for (aafi,xafi,xsafi) in [((afi,safi),str(afi),str(safi)) for (afi,safi) in self]]) + ')'

	def extract (self):
		rs = []
		for v in self:
			if self[v]:
				rs.append(v[0].pack() +v[1].pack() + pack('!B',self[v]))
		return rs

########NEW FILE########
__FILENAME__ = graceful
# encoding: utf-8
"""
graceful.py

Created by Thomas Mangin on 2012-07-17.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import pack

# =================================================================== Graceful (Restart)
# RFC 4727

class Graceful (dict):
	TIME_MASK     = 0x0FFF
	FLAG_MASK     = 0xF000

	# 0x8 is binary 1000
	RESTART_STATE = 0x08
	FORWARDING_STATE = 0x80

	def __init__ (self,restart_flag,restart_time,protos):
		dict.__init__(self)
		self.restart_flag = restart_flag
		self.restart_time = restart_time & Graceful.TIME_MASK
		for afi,safi,family_flag in protos:
			self[(afi,safi)] = family_flag & Graceful.FORWARDING_STATE

	def extract (self):
		restart  = pack('!H',((self.restart_flag << 12) | (self.restart_time & Graceful.TIME_MASK)))
		families = [(afi.pack(),safi.pack(),chr(self[(afi,safi)])) for (afi,safi) in self.keys()]
		sfamilies = ''.join(["%s%s%s" % (pafi,psafi,family) for (pafi,psafi,family) in families])
		return ["%s%s" % (restart,sfamilies)]

	def __str__ (self):
		families = [(str(afi),str(safi),hex(self[(afi,safi)])) for (afi,safi) in self.keys()]
		sfamilies = ' '.join(["%s/%s=%s" % (afi,safi,family) for (afi,safi,family) in families])
		return "Graceful Restart Flags %s Time %d %s" % (hex(self.restart_flag),self.restart_time,sfamilies)

	def families (self):
		return self.keys()

########NEW FILE########
__FILENAME__ = id
# encoding: utf-8
"""
id.py

Created by Thomas Mangin on 2012-07-17.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

class CapabilityID (object):
	RESERVED                 = 0x00  # [RFC5492]
	MULTIPROTOCOL_EXTENSIONS = 0x01  # [RFC2858]
	ROUTE_REFRESH            = 0x02  # [RFC2918]
	OUTBOUND_ROUTE_FILTERING = 0x03  # [RFC5291]
	MULTIPLE_ROUTES          = 0x04  # [RFC3107]
	EXTENDED_NEXT_HOP        = 0x05  # [RFC5549]
	#6-63      Unassigned
	GRACEFUL_RESTART         = 0x40  # [RFC4724]
	FOUR_BYTES_ASN           = 0x41  # [RFC4893]
	# 66 Deprecated
	DYNAMIC_CAPABILITY       = 0x43  # [Chen]
	MULTISESSION_BGP_RFC     = 0x44  # [draft-ietf-idr-bgp-multisession]
	ADD_PATH                 = 0x45  # [draft-ietf-idr-add-paths]
	ENHANCED_ROUTE_REFRESH   = 0x46  # [draft-ietf-idr-bgp-enhanced-route-refresh]
	OPERATIONAL              = 0x47  # ExaBGP only ...
	# 70-127    Unassigned
	CISCO_ROUTE_REFRESH      = 0x80  # I Can only find reference to this in the router logs
	# 128-255   Reserved for Private Use [RFC5492]
	MULTISESSION_BGP         = 0x83  # What Cisco really use for Multisession (yes this is a reserved range in prod !)

	EXTENDED_MESSAGE         = -1    # No yet defined by draft http://tools.ietf.org/html/draft-ietf-idr-extended-messages-02.txt

	unassigned = range(70,128)
	reserved = range(128,256)

from exabgp.util.enumeration import Enumeration
REFRESH = Enumeration ('absent','normal','enhanced')

########NEW FILE########
__FILENAME__ = mp
# encoding: utf-8
"""
mp.py

Created by Thomas Mangin on 2012-07-17.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import pack

# =================================================================== MultiProtocol

class MultiProtocol (list):
	def __str__ (self):
		return 'Multiprotocol(' + ','.join(["%s %s" % (str(afi),str(safi)) for (afi,safi) in self]) + ')'

	def extract (self):
		rs = []
		for v in self:
			rs.append(pack('!H',v[0]) + pack('!H',v[1]))
		return rs

########NEW FILE########
__FILENAME__ = ms
# encoding: utf-8
"""
ms.py

Created by Thomas Mangin on 2012-07-17.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

# =================================================================== MultiSession

class MultiSession (list):
	def __str__ (self):
		return 'Multisession %s' % ' '.join([str(capa) for capa in self])

	def extract (self):
		rs = [chr(0),]
		for v in self:
			rs.append(chr(v))
		return rs

########NEW FILE########
__FILENAME__ = negotiated
# encoding: utf-8
"""
negotiated.py

Created by Thomas Mangin on 2012-07-19.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message.open.asn import ASN,AS_TRANS
from exabgp.bgp.message.open.holdtime import HoldTime
from exabgp.bgp.message.open.capability.id import CapabilityID as CID,REFRESH
from exabgp.bgp.message.open.routerid import RouterID

class Negotiated (object):
	def __init__ (self,neighbor):
		self.neighbor = neighbor

		self.sent_open = None
		self.received_open = None

		self.holdtime = HoldTime(0)
		self.local_as = ASN(0)
		self.peer_as = ASN(0)
		self.families = []
		self.asn4 = False
		self.addpath = RequirePath()
		self.multisession = False
		self.msg_size = 4096
		self.operational = False
		self.refresh = REFRESH.absent
		self.aigp = None

	def sent (self,sent_open):
		self.sent_open = sent_open
		if self.received_open:
			self._negociate()

	def received (self,received_open):
		self.received_open = received_open
		if self.sent_open:
			self._negociate()
		#else:
		#	import pdb; pdb.set_trace()

	def _negociate (self):
		sent_capa = self.sent_open.capabilities
		recv_capa = self.received_open.capabilities

		self.holdtime = HoldTime(min(self.sent_open.hold_time,self.received_open.hold_time))

		self.addpath.setup(self.sent_open,self.received_open)
		self.asn4 = sent_capa.announced(CID.FOUR_BYTES_ASN) and recv_capa.announced(CID.FOUR_BYTES_ASN)
		self.operational = sent_capa.announced(CID.OPERATIONAL) and recv_capa.announced(CID.OPERATIONAL)

		self.local_as = self.sent_open.asn
		self.peer_as = self.received_open.asn
		if self.received_open.asn == AS_TRANS:
			self.peer_as = recv_capa[CID.FOUR_BYTES_ASN]

		self.families = []
		if recv_capa.announced(CID.MULTIPROTOCOL_EXTENSIONS) \
		and sent_capa.announced(CID.MULTIPROTOCOL_EXTENSIONS):
			for family in recv_capa[CID.MULTIPROTOCOL_EXTENSIONS]:
				if family in sent_capa[CID.MULTIPROTOCOL_EXTENSIONS]:
					self.families.append(family)

		if recv_capa.announced(CID.ENHANCED_ROUTE_REFRESH) and sent_capa.announced(CID.ENHANCED_ROUTE_REFRESH):
			self.refresh=REFRESH.enhanced
		elif recv_capa.announced(CID.ROUTE_REFRESH) and sent_capa.announced(CID.ROUTE_REFRESH):
			self.refresh=REFRESH.normal

		self.multisession = sent_capa.announced(CID.MULTISESSION_BGP) and recv_capa.announced(CID.MULTISESSION_BGP)

		if self.multisession:
			sent_ms_capa = set(sent_capa[CID.MULTISESSION_BGP])
			recv_ms_capa = set(recv_capa[CID.MULTISESSION_BGP])

			if sent_ms_capa == set([]):
				sent_ms_capa = set([CID.MULTIPROTOCOL_EXTENSIONS])
			if recv_ms_capa == set([]):
				recv_ms_capa = set([CID.MULTIPROTOCOL_EXTENSIONS])

			if sent_ms_capa != recv_ms_capa:
				self.multisession = (2,8,'multisession, our peer did not reply with the same sessionid')

			# The way we implement MS-BGP, we only send one MP per session
			# therefore we can not collide due to the way we generate the configuration

			for capa in sent_ms_capa:
				# no need to check that the capability exists, we generated it
				# checked it is what we sent and only send MULTIPROTOCOL_EXTENSIONS
				if sent_capa[capa] != recv_capa[capa]:
					self.multisession = (2,8,'when checking session id, capability %s did not match' % str(capa))
					break

		elif sent_capa.announced(CID.MULTISESSION_BGP):
			self.multisession = (2,9,'multisession is mandatory with this peer')

		# XXX: Does not work as the capa is not yet defined
		#if received_open.capabilities.announced(CID.EXTENDED_MESSAGE) \
		#and sent_open.capabilities.announced(CID.EXTENDED_MESSAGE):
		#	if self.peer.bgp.received_open_size:
		#		self.received_open_size = self.peer.bgp.received_open_size - 19

	def validate (self,neighbor):
		if not self.asn4:
			if neighbor.local_as.asn4():
				return (2,0,'peer does not speak ASN4, we are stuck')
			else:
				# we will use RFC 4893 to convey new ASN to the peer
				self.asn4

		if self.peer_as != neighbor.peer_as:
			return (2,2,'ASN in OPEN (%d) did not match ASN expected (%d)' % (self.received_open.asn,neighbor.peer_as))

		# RFC 6286 : http://tools.ietf.org/html/rfc6286
		#if message.router_id == RouterID('0.0.0.0'):
		#	message.router_id = RouterID(ip)
		if self.received_open.router_id == RouterID('0.0.0.0'):
			return (2,3,'0.0.0.0 is an invalid router_id')

		if self.received_open.asn == neighbor.local_as:
			# router-id must be unique within an ASN
			if self.received_open.router_id == neighbor.router_id:
				return (2,3,'BGP Indendifier collision, same router-id (%s) on both side of this IBGP session' % self.received_open.router_id)

		if self.received_open.hold_time and self.received_open.hold_time < 3:
			return (2,6,'Hold Time is invalid (%d)' % self.received_open.hold_time)

		if self.multisession not in (True,False):
			# XXX: FIXME: should we not use a string and perform a split like we do elswhere ?
			# XXX: FIXME: or should we use this trick in the other case ?
			return self.multisession

		return None

# =================================================================== RequirePath

class RequirePath (object):
	REFUSE = 0
	ACCEPT = 1
	ANNOUNCE = 2

	def __init__ (self):
		self._send = {}
		self._receive = {}

	def setup (self,received_open,sent_open):
		# A Dict always returning False
		class FalseDict (dict):
			def __getitem__(self,key):
				return False

		receive = received_open.capabilities.get(CID.ADD_PATH,FalseDict())
		send = sent_open.capabilities.get(CID.ADD_PATH,FalseDict())

		# python 2.4 compatibility mean no simple union but using sets.Set
		union = []
		union.extend(send.keys())
		union.extend([k for k in receive.keys() if k not in send.keys()])

		for k in union:
			self._send[k] = bool(receive.get(k,self.REFUSE) & self.ANNOUNCE and send.get(k,self.REFUSE) & self.ACCEPT)
			self._receive[k] = bool(receive.get(k,self.REFUSE) & self.ACCEPT and send.get(k,self.REFUSE) & self.ANNOUNCE)

	def send (self,afi,safi):
		return self._send.get((afi,safi),False)

	def receive (self,afi,safi):
		return self._receive.get((afi,safi),False)

########NEW FILE########
__FILENAME__ = operational
# encoding: utf-8
"""
operational.py

Created by Thomas Mangin on 2013-09-01.
Copyright (c) 2013-2013 Exa Networks. All rights reserved.
"""

# =================================================================== Operational

class Operational (list):
	def __str__ (self):
		return 'Operational'

	def extract (self):
		return ['']

########NEW FILE########
__FILENAME__ = refresh
# encoding: utf-8
"""
refresh.py

Created by Thomas Mangin on 2012-07-17.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

# =================================================================== RouteRefresh

class RouteRefresh (object):
	def __str__ (self):
		return 'Route Refresh'

	def extract (self):
		return ['']

class EnhancedRouteRefresh (object):
	def __str__ (self):
		return 'Enhanced Route Refresh'

	def extract (self):
		return ['']

########NEW FILE########
__FILENAME__ = holdtime
# encoding: utf-8
"""
holdtime.py

Created by Thomas Mangin on 2012-07-17.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import pack

# =================================================================== HoldTime

class HoldTime (int):
	def pack (self):
		return pack('!H',self)

	def keepalive (self):
		return int(self/3)

	def __len__ (self):
		return 2

########NEW FILE########
__FILENAME__ = routerid
# encoding: utf-8
"""
routerid.py

Created by Thomas Mangin on 2012-07-17.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.protocol.ip.inet import Inet,inet
from exabgp.protocol.family import AFI

# =================================================================== RouterID

class RouterID (Inet):
	def __init__ (self,ipv4):
		Inet.__init__(self,*inet(ipv4))
		if self.afi != AFI.ipv4:
			raise ValueError('RouterID must be an IPv4 address')

########NEW FILE########
__FILENAME__ = version
# encoding: utf-8
"""
version.py

Created by Thomas Mangin on 2012-07-17.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

# =================================================================== Version

class Version (int):
	def pack (self):
		return chr(self)

########NEW FILE########
__FILENAME__ = operational
# encoding: utf-8
"""
operational/__init__.py

Created by Thomas Mangin on 2013-09-01.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import pack,unpack

from exabgp.protocol.family import AFI,SAFI
from exabgp.bgp.message.open.routerid import RouterID
from exabgp.bgp.message import Message

# =================================================================== Operational

MAX_ADVISORY = 2048  # 2K

class Type (int):
	def pack (self):
		return pack('!H',self)

	def extract (self):
		return [pack('!H',self)]

	def __len__ (self):
		return 2

	def __str__ (self):
		pass

class OperationalType:
	# ADVISE
	ADM  = 0x01  # 01: Advisory Demand Message
	ASM  = 0x02  # 02: Advisory Static Message
	# STATE
	RPCQ = 0x03  # 03: Reachable Prefix Count Request
	RPCP = 0x04  # 04: Reachable Prefix Count Reply
	APCQ = 0x05  # 05: Adj-Rib-Out Prefix Count Request
	APCP = 0x06  # 06: Adj-Rib-Out Prefix Count Reply
	LPCQ = 0x07  # 07: BGP Loc-Rib Prefix Count Request
	LPCP = 0x08  # 08: BGP Loc-Rib Prefix Count Reply
	SSQ  = 0x09  # 09: Simple State Request
	# DUMP
	DUP  = 0x0A  # 10: Dropped Update Prefixes
	MUP  = 0x0B  # 11: Malformed Update Prefixes
	MUD  = 0x0C  # 12: Malformed Update Dump
	SSP  = 0x0D  # 13: Simple State Response
	# CONTROL
	MP   = 0xFFFE  # 65534: Max Permitted
	NS   = 0xFFFF  # 65535: Not Satisfied

class Operational (Message):
	TYPE = chr(0x06)  # next free Message Type, as IANA did not assign one yet.
	has_family = False
	has_routerid = False
	is_fault = False

	def __init__ (self,what):
		Message.__init__(self)
		self.what = Type(what)

	def _message (self,data):
		return Message._message(self,"%s%s%s" % (
			self.what.pack(),
			pack('!H',len(data)),
			data
		))

	def __str__ (self):
		return self.extensive()

	def extensive (self):
		return 'operational %s' % self.name

class OperationalFamily (Operational):
	has_family = True

	def __init__ (self,what,afi,safi,data=''):
		Operational.__init__(self,what)
		self.afi = AFI(afi)
		self.safi = SAFI(afi)
		self.data = data

	def family (self):
		return (self.afi,self.safi)

	def _message (self,data):
		return Operational._message(self,"%s%s%s" % (
			self.afi.pack(),
			self.safi.pack(),
			data
		))

	def message (self,negotiated):
		return self._message(self.data)


class SequencedOperationalFamily (OperationalFamily):
	__sequence_number = {}
	has_routerid = True

	def __init__ (self,what,afi,safi,routerid,sequence,data=''):
		OperationalFamily.__init__(self,what,afi,safi,data)
		self.routerid = routerid if routerid else None
		self.sequence = sequence if sequence else None
		self._sequence = self.sequence
		self._routerid = self.routerid

	def message (self,negotiated):
		self.sent_routerid = self.routerid if self.routerid else negotiated.sent_open.router_id
		if self.sequence is None:
			self.sent_sequence = (self.__sequence_number.setdefault(self.routerid,0) + 1) % 0xFFFFFFFF
			self.__sequence_number[self.sent_routerid] = self.sent_sequence
		else:
			self.sent_sequence = self.sequence

		return self._message("%s%s%s" % (
			self.sent_routerid.pack(),pack('!L',self.sent_sequence),
			self.data
		))


class NS:
	MALFORMED   = 0x01  # Request TLV Malformed
	UNSUPPORTED = 0x02  # TLV Unsupported for this neighbor
	MAXIMUM     = 0x03  # Max query frequency exceeded
	PROHIBITED  = 0x04  # Administratively prohibited
	BUSY        = 0x05  # Busy
	NOTFOUND    = 0x06  # Not Found

	class _NS (OperationalFamily):
		is_fault = True

		def __init__ (self,afi,safi,sequence):
			OperationalFamily.__init__(
				self,
				OperationalType.NS,
				afi,safi,
				'%s%s' % (sequence,self.ERROR_SUBCODE)
			)

		def extensive (self):
			return 'operational NS %s %s/%s' % (self.name,self.afi,self.safi)


	class Malformed (_NS):
		name = 'NS malformed'
		ERROR_SUBCODE = '\x00\x01'  # pack('!H',MALFORMED)

	class Unsupported (_NS):
		name = 'NS unsupported'
		ERROR_SUBCODE = '\x00\x02'  # pack('!H',UNSUPPORTED)

	class Maximum (_NS):
		name = 'NS maximum'
		ERROR_SUBCODE = '\x00\x03'  # pack('!H',MAXIMUM)

	class Prohibited (_NS):
		name = 'NS prohibited'
		ERROR_SUBCODE = '\x00\x04'  # pack('!H',PROHIBITED)

	class Busy (_NS):
		name = 'NS busy'
		ERROR_SUBCODE = '\x00\x05'  # pack('!H',BUSY)

	class NotFound (_NS):
		name = 'NS notfound'
		ERROR_SUBCODE = '\x00\x06'  # pack('!H',NOTFOUND)


class Advisory:
	class _Advisory (OperationalFamily):
		def extensive (self):
			return 'operational %s afi %s safi %s "%s"' % (self.name,self.afi,self.safi,self.data)

	class ADM (_Advisory):
		name = 'ADM'

		def __init__ (self,afi,safi,advisory,routerid=None):
			utf8 = advisory.encode('utf-8')
			if len(utf8) > MAX_ADVISORY:
				utf8 = utf8[:MAX_ADVISORY-3] + '...'.encode('utf-8')
			OperationalFamily.__init__(
				self,OperationalType.ADM,
				afi,safi,
				utf8
			)

	class ASM (_Advisory):
		name = 'ASM'

		def __init__ (self,afi,safi,advisory,routerid=None):
			utf8 = advisory.encode('utf-8')
			if len(utf8) > MAX_ADVISORY:
				utf8 = utf8[:MAX_ADVISORY-3] + '...'.encode('utf-8')
			OperationalFamily.__init__(
				self,OperationalType.ASM,
				afi,safi,
				utf8
			)

# a = Advisory.ADM(1,1,'string 1')
# print a.extensive()
# b = Advisory.ASM(1,1,'string 2')
# print b.extensive()


class Query:
	class _Query (SequencedOperationalFamily):
		name = None
		code = None

		def __init__ (self,afi,safi,routerid,sequence):
			SequencedOperationalFamily.__init__(
				self,self.code,
				afi,safi,
				routerid,sequence
			)

		def extensive (self):
			if self._routerid and self._sequence:
				return 'operational %s afi %s safi %s router-id %s sequence %d' % (
					self.name,
					self.afi,self.safi,
					self._routerid,self._sequence,
				)
			return 'operational %s afi %s safi %s' % (self.name,self.afi,self.safi)

	class RPCQ (_Query):
		name = 'RPCQ'
		code = OperationalType.RPCQ

	class APCQ (_Query):
		name = 'APCQ'
		code = OperationalType.APCQ

	class LPCQ (_Query):
		name = 'LPCQ'
		code = OperationalType.LPCQ

class Response:
	class _Counter (SequencedOperationalFamily):
		def __init__ (self,afi,safi,routerid,sequence,counter):
			self.counter = counter
			SequencedOperationalFamily.__init__(
				self,self.code,
				afi,safi,
				routerid,sequence,
				pack('!L',counter)
			)

		def extensive (self):
			if self._routerid and self._sequence:
				return 'operational %s afi %s safi %s router-id %s sequence %d counter %d' % (
					self.name,
					self.afi,self.safi,
					self._routerid,self._sequence,
					self.counter
				)
			return 'operational %s afi %s safi %s counter %d' % (self.name,self.afi,self.safi,self.counter)

	class RPCP (_Counter):
		name = 'RPCP'
		code = OperationalType.RPCP

	class APCP (_Counter):
		name = 'APCP'
		code = OperationalType.APCP

	class LPCP (_Counter):
		name = 'LPCP'
		code = OperationalType.LPCP

# c = State.RPCQ(1,1,'82.219.0.1',10)
# print c.extensive()
# d = State.RPCP(1,1,'82.219.0.1',10,10000)
# print d.extensive()

class Dump:
	pass

OperationalGroup = {
	OperationalType.ADM: ('advisory', Advisory.ADM),
	OperationalType.ASM: ('advisory', Advisory.ASM),

	OperationalType.RPCQ: ('query', Query.RPCQ),
	OperationalType.RPCP: ('counter', Response.RPCP),

	OperationalType.APCQ: ('query', Query.APCQ),
	OperationalType.APCP: ('counter', Response.APCP),

	OperationalType.LPCQ: ('query', Query.LPCQ),
	OperationalType.LPCP: ('counter', Response.LPCP),
}

def OperationalFactory (data):
	what = Type(unpack('!H',data[0:2])[0])
	length = unpack('!H',data[2:4])[0]

	decode,klass = OperationalGroup.get(what,('unknown',None))

	if decode == 'advisory':
		afi = unpack('!H',data[4:6])[0]
		safi = ord(data[6])
		data = data[7:length+4]
		return klass(afi,safi,data)
	elif decode == 'query':
		afi = unpack('!H',data[4:6])[0]
		safi = ord(data[6])
		routerid = RouterID('.'.join(str(ord(_)) for _ in data[7:11]))
		sequence = unpack('!L',data[11:15])[0]
		return klass(afi,safi,routerid,sequence)
	elif decode == 'counter':
		afi = unpack('!H',data[4:6])[0]
		safi = ord(data[6])
		routerid = RouterID('.'.join(str(ord(_)) for _ in data[7:11]))
		sequence = unpack('!L',data[11:15])[0]
		counter = unpack('!L',data[15:19])[0]
		return klass(afi,safi,routerid,sequence,counter)
	else:
		print 'ignoring ATM this kind of message'

########NEW FILE########
__FILENAME__ = refresh
# encoding: utf-8
"""
refresh.py

Created by Thomas Mangin on 2012-07-19.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import unpack,error

from exabgp.protocol.family import AFI,SAFI
from exabgp.bgp.message import Message
from exabgp.bgp.message.notification import Notify

# =================================================================== Notification
# A Notification received from our peer.
# RFC 4271 Section 4.5

class Reserved (int):
	def __str__ (self):
		if self == 0: return 'query'
		if self == 1: return 'begin'
		if self == 2: return 'end'
		return 'invalid'

class RouteRefresh (Message):
	TYPE = chr(Message.Type.ROUTE_REFRESH)

	request = 0
	start = 1
	end = 2

	def __init__ (self,afi,safi,reserved=0):
		self.afi = AFI(afi)
		self.safi = SAFI(safi)
		self.reserved = Reserved(reserved)

	def messages (self,negotitated):
		return [self._message('%s%s%s' % (self.afi.pack(),chr(self.reserved),self.safi.pack())),]

	def __str__ (self):
		return "REFRESH"

	def extensive (self):
		return 'route refresh %s/%d/%s' % (self.afi,self.reserved,self.safi)

	def families (self):
		return self._families[:]

def RouteRefreshFactory (data):
	try:
		afi,reserved,safi = unpack('!HBB',data)
	except error:
		raise Notify(7,1,'invalid route-refresh message')
	if reserved not in (0,1,2):
		raise Notify(7,2,'invalid route-refresh message subtype')
	return RouteRefresh(afi,safi,reserved)

########NEW FILE########
__FILENAME__ = unknown
# encoding: utf-8
"""
unknown.py

Created by Thomas Mangin on 2013-07-20.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message import Message

class UnknownMessage (Message):
	# Make sure we have a value, which is not defined in any RFC !

	def __init__ (self,code,data=''):
		self.TYPE = code
		self.data = data

	def message (self):
		return self._message(self.data)

	def __str__ (self):
		return "UNKNOWN"

def UnknownMessageFactory (data):
	return UnknownMessage(0xFF,data)

########NEW FILE########
__FILENAME__ = aggregator
# encoding: utf-8
"""
aggregator.py

Created by Thomas Mangin on 2012-07-14.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.protocol.family import AFI,SAFI
from exabgp.bgp.message.open.asn import ASN
from exabgp.protocol.ip.inet import Inet

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== AGGREGATOR (7)

class Aggregator (Attribute):
	ID = AttributeID.AGGREGATOR
	FLAG = Flag.TRANSITIVE|Flag.OPTIONAL
	MULTIPLE = False

	def __init__ (self,aggregator):
		asn = 0
		for value in (ord(_) for _ in aggregator[:-4]):
			asn = (asn << 8) + value
		self.asn=ASN(asn)
		self.speaker=Inet(AFI.ipv4,SAFI.unicast,aggregator[-4:])
		self._str = '%s:%s' % (self.asn,self.speaker)

	def pack (self,asn4,as4agg=False):
		if as4agg:
			backup = self.ID
			self.ID = AttributeID.AS4_AGGREGATOR
			packed = self._attribute(self.asn.pack(True)+self.speaker.pack())
			self.ID = backup
			return packed
		elif asn4:
			return self._attribute(self.asn.pack(True)+self.speaker.pack())
		elif not self.asn.asn4():
			return self._attribute(self.asn.pack(False)+self.speaker.pack())
		else:
			return self._attribute(self.asn.trans()+self.speaker.pack()) + self.pack(True,True)


	def __len__ (self):
		raise RuntimeError('size can be 6 or 8 - we can not say')

	def __str__ (self):
		return self._str

########NEW FILE########
__FILENAME__ = aigp
# encoding: utf-8
"""
aigp.py

Created by Thomas Mangin on 2013-09-24.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import pack,unpack

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== AIGP (26)

# 0                   1                   2                   3
# 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# |     Type      |         Length                |               |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+               |
# ~                                                               ~
# |                           Value                               |
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+..........................

# Length: Two octets encoding the length in octets of the TLV,
# including the type and length fields.

class TLV (object):
	def __init__(self,type,value):
		self.type = type
		self.value = value


def _TLVFactory (data):
	while data:
		t = ord(data[0])
		l = unpack('!H',data[1:3])[0]
		v,data = data[3:l],data[l:]
		yield TLV(t,v)

def TLVFactory (data):
	return list(_TLVFactory(data))

def pack_tlv (tlvs):
	return ''.join('%s%s%s' % (chr(tlv.type),pack('!H',len(tlv.value)+3),tlv.value) for tlv in tlvs)

class AIGP (Attribute):
	ID = AttributeID.AIGP
	FLAG = Flag.OPTIONAL
	MULTIPLE = False
	TYPES = [1,]

	def __init__ (self,value):
		self.aigp = unpack('!Q',TLVFactory(value)[0].value)[0]
		self.packed = self._attribute(value)

	def pack (self,asn4=None):
		return self.packed

	def __str__ (self):
		return str(self.aigp)

########NEW FILE########
__FILENAME__ = aspath
# encoding: utf-8
"""
aspath.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

from exabgp.bgp.message.open.asn import AS_TRANS

# =================================================================== ASPath (2)

class ASPath (Attribute):
	AS_SET      = 0x01
	AS_SEQUENCE = 0x02

	ID = AttributeID.AS_PATH
	FLAG = Flag.TRANSITIVE
	MULTIPLE = False

	def __init__ (self,as_sequence,as_set,index=None):
		self.as_seq = as_sequence
		self.as_set = as_set
		self.segments = ''
		self.packed = {True:'',False:''}
		self.index = index  # the original packed data, use for indexing
		self._str = ''
		self._json = {}

	def _segment (self,seg_type,values,asn4):
		l = len(values)
		if l:
			if l>255:
				return self._segment(seg_type,values[:255]) + self._segment(seg_type,values[255:])
			return "%s%s%s" % (chr(seg_type),chr(len(values)),''.join([v.pack(asn4) for v in values]))
		return ""

	def _segments (self,asn4):
		segments = ''
		if self.as_seq:
			segments = self._segment(self.AS_SEQUENCE,self.as_seq,asn4)
		if self.as_set:
			segments += self._segment(self.AS_SET,self.as_set,asn4)
		return segments

	def _pack (self,asn4):
		if not self.packed[asn4]:
			self.packed[asn4] = self._attribute(self._segments(asn4))
		return self.packed[asn4]

	def pack (self,asn4):
		# if the peer does not understand ASN4, we need to build a transitive AS4_PATH
		if asn4:
			return self._pack(True)

		as2_seq = [_ if not _.asn4() else AS_TRANS for _ in self.as_seq]
		as2_set = [_ if not _.asn4() else AS_TRANS for _ in self.as_set]

		message = ASPath(as2_seq,as2_set)._pack(False)
		if AS_TRANS in as2_seq or AS_TRANS in as2_set:
			message += AS4Path(self.as_seq,self.as_set)._pack()
		return message

	def __len__ (self):
		raise RuntimeError('it makes no sense to ask for the size of this object')

	def __str__ (self):
		if not self._str:
			lseq = len(self.as_seq)
			lset = len(self.as_set)
			if lseq == 1:
				if not lset:
					string = '%d' % self.as_seq[0]
				else:
					string = '[ %s %s]' % (self.as_seq[0],'( %s ) ' % (' '.join([str(_) for _ in self.as_set])))
			elif lseq > 1 :
				if lset:
					string = '[ %s %s]' % ((' '.join([str(_) for _ in self.as_seq])),'( %s ) ' % (' '.join([str(_) for _ in self.as_set])))
				else:
					string = '[ %s ]' % ' '.join([str(_) for _ in self.as_seq])
			else:  # lseq == 0
				string = '[ ]'
			self._str = string
		return self._str

	def json (self,name):
		if name not in self._json:
			if name == 'as-path':
				if self.as_seq:
					self._json[name] = '[ %s ]' % ', '.join([str(_) for _ in self.as_seq])
				else:
					self._json[name] = '[]'
			elif name == 'as-set':
				if self.as_set:
					self._json[name] = '[ %s ]' % ', '.join([str(_) for _ in self.as_set])
				else:
					self._json[name] = ''
			else:
				# very wrong ,,,,
				return "[ 'bug in ExaBGP\'s code' ]"
		return self._json[name]


class AS4Path (ASPath):
	ID = AttributeID.AS4_PATH
	FLAG = Flag.TRANSITIVE|Flag.OPTIONAL

	def pack (self,asn4=None):
		ASPath.pack(self,True)

########NEW FILE########
__FILENAME__ = atomicaggregate
# encoding: utf-8
"""
atomicaggregate.py

Created by Thomas Mangin on 2012-07-14.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== AtomicAggregate (6)

class AtomicAggregate (Attribute):
	ID = AttributeID.ATOMIC_AGGREGATE
	FLAG = Flag.TRANSITIVE
	MULTIPLE = False

	def pack (self,asn4=None):
		return self._attribute('')

	def __len__ (self):
		return 0

	def __str__ (self):
		return ''

########NEW FILE########
__FILENAME__ = clusterlist
# encoding: utf-8
"""
clusterlist.py

Created by Thomas Mangin on 2012-07-07.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.protocol.family import AFI,SAFI
from exabgp.protocol.ip.inet import Inet
from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# ===================================================================

class ClusterID (Inet):
	def __init__ (self,cluster_id):
		Inet.__init__(self,AFI.ipv4,SAFI.unicast_multicast,cluster_id)


class ClusterList (Attribute):
	ID = AttributeID.CLUSTER_LIST
	FLAG = Flag.OPTIONAL
	MULTIPLE = False

	def __init__ (self,cluster_ids):
		self.clusters = []
		while cluster_ids:
			self.clusters.append(ClusterID(cluster_ids[:4]))
			cluster_ids = cluster_ids[4:]
		self._len = len(self.clusters)*4
		# XXX: are we doing the work for nothing ?
		self.packed = self._attribute(''.join([_.pack() for _ in self.clusters]))

	def pack (self,asn4=None):
		return self.packed

	def __len__ (self):
		return self._len

	def __str__ (self):
		if self._len != 1:
			return '[ %s ]' % ' '.join([str(_) for _ in self.clusters])
		return '%s' % self.clusters[0]

	def json (self):
		return '[ %s ]' % ', '.join(['"%s"' % str(_) for _ in self.clusters])

########NEW FILE########
__FILENAME__ = communities
# encoding: utf-8
"""
community.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import pack,unpack

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== Community

class Community (object):
	NO_EXPORT           = pack('!L',0xFFFFFF01)
	NO_ADVERTISE        = pack('!L',0xFFFFFF02)
	NO_EXPORT_SUBCONFED = pack('!L',0xFFFFFF03)
	NO_PEER             = pack('!L',0xFFFFFF04)

	cache = {}
	caching = False

	def __init__ (self,community):
		self.community = community
		if community == self.NO_EXPORT:
			self._str = 'no-export'
		elif community == self.NO_ADVERTISE:
			self._str = 'no-advertise'
		elif community == self.NO_EXPORT_SUBCONFED:
			self._str = 'no-export-subconfed'
		else:
			self._str = "%d:%d" % unpack('!HH',self.community)

	def json (self):
		return "[ %d, %d ]" % unpack('!HH',self.community)

	def pack (self,asn4=None):
		return self.community

	def __str__ (self):
		return self._str

	def __len__ (self):
		return 4

	def __eq__ (self,other):
		return self.community == other.community

	def __ne__ (self,other):
		return self.community != other.community

def cachedCommunity (community):
	if community in Community.cache:
		return Community.cache[community]
	instance = Community(community)
	if Community.caching:
		Community.cache[community] = instance
	return instance

# Always cache well-known communities, they will be used a lot
if not Community.cache:
	Community.cache[Community.NO_EXPORT] = Community(Community.NO_EXPORT)
	Community.cache[Community.NO_ADVERTISE] = Community(Community.NO_ADVERTISE)
	Community.cache[Community.NO_EXPORT_SUBCONFED] = Community(Community.NO_EXPORT_SUBCONFED)
	Community.cache[Community.NO_PEER] = Community(Community.NO_PEER)


# =================================================================== Communities (8)

class Communities (Attribute):
	ID = AttributeID.COMMUNITY
	FLAG = Flag.TRANSITIVE|Flag.OPTIONAL
	MULTIPLE = False

	def __init__ (self,communities=None):
		# Must be None as = param is only evaluated once
		if communities:
			self.communities = communities
		else:
			self.communities = []

	def add(self,data):
		return self.communities.append(data)

	def pack (self,asn4=None):
		if len(self.communities):
			return self._attribute(''.join([c.pack() for c in self.communities]))
		return ''

	def __str__ (self):
		l = len(self.communities)
		if l > 1:
			return "[ %s ]" % " ".join(str(community) for community in self.communities)
		if l == 1:
			return str(self.communities[0])
		return ""

	def json (self):
		return "[ %s ]" % ", ".join(community.json() for community in self.communities)

# =================================================================== ECommunity

# http://www.iana.org/assignments/bgp-extended-communities

# MUST ONLY raise ValueError
def to_ExtendedCommunity (data):
	nb_separators = data.count(':')
	if nb_separators == 2:
		command,ga,la = data.split(':')
	elif nb_separators == 1:
		command = 'target'
		ga,la = data.split(':')
	else:
		raise ValueError('invalid extended community %s (only origin or target are supported) ' % command)


	header = chr(0x00)
	if command == 'origin':
		subtype = chr(0x03)
	elif command == 'target':
		subtype = chr(0x02)
	else:
		raise ValueError('invalid extended community %s (only origin or target are supported) ' % command)

	if '.' in ga or '.' in la:
		gc = ga.count('.')
		lc = la.count('.')
		if gc == 0 and lc == 3:
			# ASN first, IP second
			global_admin = pack('!H',int(ga))
			local_admin = pack('!BBBB',*[int(_) for _ in la.split('.')])
		elif gc == 3 and lc == 0:
			# IP first, ASN second
			global_admin = pack('!BBBB',*[int(_) for _ in ga.split('.')])
			local_admin = pack('!H',int(la))
		else:
			raise ValueError('invalid extended community %s ' % data)
	else:
		if command == 'target':
			global_admin = pack('!H',int(ga))
			local_admin = pack('!I',int(la))
		elif command == 'origin':
			global_admin = pack('!I',int(ga))
			local_admin = pack('!H',int(la))
		else:
			raise ValueError('invalid extended community %s (only origin or target are supported) ' % command)

	return ECommunity(header+subtype+global_admin+local_admin)

class ECommunity (object):
	ID = AttributeID.EXTENDED_COMMUNITY
	FLAG = Flag.TRANSITIVE|Flag.OPTIONAL
	MULTIPLE = False

	# size of value for data (boolean: is extended)
	length_value = {False:7, True:6}
	name = {False: 'regular', True: 'extended'}

	def __init__ (self,community):
		# Two top bits are iana and transitive bits
		self.community = community

	def iana (self):
		return not not (self.community[0] & 0x80)

	def transitive (self):
		return not not (self.community[0] & 0x40)

	def pack (self,asn4=None):
		return self.community

	def json (self):
		return '[ %s, %s, %s, %s, %s, %s, %s, %s ]' % unpack('!BBBBBBBB',self.community)

	def __str__ (self):
		# 30/02/12 Quagga communities for soo and rt are not transitive when 4360 says they must be, hence the & 0x0F
		community_type = ord(self.community[0]) & 0x0F
		community_stype = ord(self.community[1])
		# Target
		if community_stype == 0x02:
			if community_type in (0x00,0x02):
				asn = unpack('!H',self.community[2:4])[0]
				ip = ip = '%s.%s.%s.%s' % unpack('!BBBB',self.community[4:])
				return "target:%d:%s" % (asn,ip)
			if community_type == 0x01:
				ip = '%s.%s.%s.%s' % unpack('!BBBB',self.community[2:6])
				asn = unpack('!H',self.community[6:])[0]
				return "target:%s:%d" % (ip,asn)
		# Origin
		if community_stype == 0x03:
			if community_type in (0x00,0x02):
				asn = unpack('!H',self.community[2:4])[0]
				ip = unpack('!L',self.community[4:])[0]
				return "origin:%d:%s" % (asn,ip)
			if community_type == 0x01:
				ip = '%s.%s.%s.%s' % unpack('!BBBB',self.community[2:6])
				asn = unpack('!H',self.community[6:])[0]
				return "origin:%s:%d" % (ip,asn)

		# Traffic rate
		if self.community.startswith('\x80\x06'):
			speed = unpack('!f',self.community[4:])[0]
			if speed == 0.0:
				return 'discard'
			return 'rate-limit %d' % speed
		# redirect
		elif self.community.startswith('\x80\x07'):
			actions = []
			value = ord(self.community[-1])
			if value & 0x2:
				actions.append('sample')
			if value & 0x1:
				actions.append('terminal')
			return 'action %s' % '-'.join(actions)
		elif self.community.startswith('\x80\x08'):
			return 'redirect %d:%d' % (unpack('!H',self.community[2:4])[0],unpack('!L',self.community[4:])[0])
		elif self.community.startswith('\x80\x09'):
			return 'mark %d' % ord(self.community[-1])
		elif self.community.startswith('\x80\x00'):
			if self.community[-1] == '\x00':
				return 'redirect-to-nexthop'
			return 'copy-to-nexthop'
		else:
			h = 0x00
			for byte in self.community:
				h <<= 8
				h += ord(byte)
			return "0x%016X" % h

	def __len__ (self):
		return 8

	def __cmp__ (self,other):
		return cmp(self.pack(),other.pack())

# =================================================================== ECommunities (16)

#def new_ECommunities (data):
#	communities = ECommunities()
#	while data:
#		ECommunity = unpack(data[:8])
#		data = data[8:]
#		communities.add(ECommunity(ECommunity))
#	return communities

class ECommunities (Communities):
	ID = AttributeID.EXTENDED_COMMUNITY

# =================================================================== FlowSpec Defined Extended Communities

def _to_FlowCommunity (action,data):
	return ECommunity(pack('!H',action) + data[:6])

# rate is bytes/seconds
def to_FlowTrafficRate (asn,rate):
	return _to_FlowCommunity (0x8006,pack('!H',asn) + pack('!f',rate))

def to_FlowTrafficAction (sample,terminal):
	number = 0
	if terminal: number += 0x1
	if sample: number += 0x2
	return _to_FlowCommunity (0x8007,'\x00\x00\x00\x00\x00' + chr(number))

def to_FlowRedirect (copy):
	payload = '\x00\x00\x00\x00\x00\x01' if copy else '\x00\x00\x00\x00\x00\x00'
	return _to_FlowCommunity (0x8000,payload)

def to_FlowRedirectVRFASN (asn,number):
	return _to_FlowCommunity (0x8008,pack('!H',asn) + pack('!L',number))

def to_FlowRedirectVRFIP (ip,number):
	return _to_FlowCommunity (0x8008,pack('!L',ip) + pack('!H',number))

def to_FlowTrafficMark (dscp):
	return _to_FlowCommunity (0x8009,'\x00\x00\x00\x00\x00' + chr(dscp))

def to_RouteOriginCommunity (asn,number,hightype=0x01):
	return ECommunity(chr(hightype) + chr(0x03) + pack('!H',asn) + pack('!L',number))

# VRF is ASN:Long
def to_RouteTargetCommunity_00 (asn,number):
	return ECommunity(chr(0x00) + chr(0x02) + pack('!H',asn) + pack('!L',number))

# VRF is A.B.C.D:Short
def to_RouteTargetCommunity_01 (ipn,number):
	return ECommunity(chr(0x01) + chr(0x02) + pack('!L',ipn) + pack('!H',number))

#def to_ASCommunity (subtype,asn,data,transitive):
#	r = chr(0x00)
#	if transitive: r += chr(0x40)
#	return ECommunity(r + chr(subtype) + pack('!H',asn) + ''.join([chr(c) for c in data[:4]]))
#
#import socket
#def toIPv4Community (subtype,data,transitive):
#	r = chr(0x01)
#	if transitive: r += chr(0x40)
#	return ECommunity(r + chr(subtype) + socket.inet_pton(socket.AF_INET,ipv4) + ''.join([chr(c) for c in data[:2]]))
#
#def to_OpaqueCommunity (subtype,data,transitive):
#	r = chr(0x03)
#	if transitive: r += chr(0x40)
#	return ECommunity(r + chr(subtype) + ''.join([chr(c) for c in data[:6]]))

# See RFC4360
# 0x00, 0x02 Number is administrated by a global authority
# Format is asn:route_target (2 bytes:4 bytes)
# 0x01, Number is administered by the ASN owner
# Format is ip:route_target  (4 bytes:2 bytes)
# 0x02 and 0x03 .. read the RFC :)

########NEW FILE########
__FILENAME__ = flag
# encoding: utf-8
"""
flag.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

# =================================================================== Flag

class Flag (int):
	EXTENDED_LENGTH = 0x10  # .  16
	PARTIAL         = 0x20  # .  32
	TRANSITIVE      = 0x40  # .  64
	OPTIONAL        = 0x80  # . 128

	def __str__ (self):
		r = []
		v = int(self)
		if v & 0x10:
			r.append("EXTENDED_LENGTH")
			v -= 0x10
		if v & 0x20:
			r.append("PARTIAL")
			v -= 0x20
		if v & 0x40:
			r.append("TRANSITIVE")
			v -= 0x40
		if v & 0x80:
			r.append("OPTIONAL")
			v -= 0x80
		if v:
			r.append("UNKNOWN %s" % hex(v))
		return " ".join(r)

	def matches (self,value):
		return self | 0x10 == value | 0x10

########NEW FILE########
__FILENAME__ = id
# encoding: utf-8
"""
id.py

Created by Thomas Mangin on 2012-07-17.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

class AttributeID (int):
	# This should move within the classes and not be here
	# RFC 4271
	ORIGIN             = 0x01
	AS_PATH            = 0x02
	NEXT_HOP           = 0x03
	MED                = 0x04
	LOCAL_PREF         = 0x05
	ATOMIC_AGGREGATE   = 0x06
	AGGREGATOR         = 0x07
	# RFC 1997
	COMMUNITY          = 0x08
	# RFC 4456
	ORIGINATOR_ID      = 0x09
	CLUSTER_LIST       = 0x0A  # 10
	# RFC 4760
	MP_REACH_NLRI      = 0x0E  # 14
	MP_UNREACH_NLRI    = 0x0F  # 15
	# RFC 4360
	EXTENDED_COMMUNITY = 0x10  # 16
	# RFC 4893
	AS4_PATH           = 0x11  # 17
	AS4_AGGREGATOR     = 0x12  # 18
	AIGP               = 0x1A  # 26

	INTERNAL_WITHDRAW  = 0xFFFD
	INTERNAL_WATCHDOG  = 0xFFFE
	INTERNAL_SPLIT     = 0xFFFF

	_str = {
		0x01: 'origin',
		0x02: 'as-path',
		0x03: 'next-hop',
		0x04: 'med',
#		0x04: 'multi-exit-disc',
		0x05: 'local-preference',
		0x06: 'atomic-aggregate',
		0x07: 'aggregator',
		0x08: 'community',
		0x09: 'originator-id',
		0x0a: 'cluster-list',
		0x0e: 'mp-reach-nlri',
		0x0f: 'mp-unreach-nlri',
#		0x0e: 'multi-protocol reacheable nlri'
#		0x0f: 'multi-protocol unreacheable nlri'
		0x10: 'extended-community',
		0x11: 'as4-path',
		0x12: 'as4-aggregator',
		0x1a: 'aigp',
		0xfffd: 'internal-withdraw',
		0xfffe: 'internal-watchdog',
		0xffff: 'internal-split',
	}

	def __str__ (self):
		return self._str.get(self,'unknown-attribute-%s' % hex(self))

########NEW FILE########
__FILENAME__ = localpref
# encoding: utf-8
"""
attributes.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import unpack

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== Local Preference (5)

class LocalPreference (Attribute):
	ID = AttributeID.LOCAL_PREF
	FLAG = Flag.TRANSITIVE
	MULTIPLE = False

	def __init__ (self,localpref):
		self.localpref = self._attribute(localpref)
		self._str = str(unpack('!L',localpref)[0])

	def pack (self,asn4=None):
		return self.localpref

	def __len__ (self):
		return 4

	def __str__ (self):
		return self._str

########NEW FILE########
__FILENAME__ = med
# encoding: utf-8
"""
med.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import unpack

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== MED (4)

class MED (Attribute):
	ID = AttributeID.MED
	FLAG = Flag.OPTIONAL
	MULTIPLE = False

	def __init__ (self,med):
		self.med = self._attribute(med)
		self._str = str(unpack('!L',med)[0])

	def pack (self,asn4=None):
		return self.med

	def __len__ (self):
		return 4

	def __str__ (self):
		return self._str

########NEW FILE########
__FILENAME__ = mprnlri
# encoding: utf-8
"""
mprnlri.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== MP Unreacheable NLRI (15)

class MPRNLRI (Attribute):
	FLAG = Flag.OPTIONAL
	ID = AttributeID.MP_REACH_NLRI
	MULTIPLE = True

	def __init__ (self,nlris):
		# all the routes must have the same next-hop
		self.nlris = nlris


	def packed_attributes (self,addpath):
		if not self.nlris:
			return

		mpnlri = {}
		for nlri in self.nlris:
			if nlri.nexthop:
				# .packed and not .pack()
				# we do not want a next_hop attribute packed (with the _attribute()) but just the next_hop itself
				if nlri.safi.has_rd():
					nexthop = chr(0)*8 + nlri.nexthop.packed
				else:
					nexthop = nlri.nexthop.packed
			else:
				# EOR fo not and Flow may not have any next_hop
				nexthop = ''

			# mpunli[afi,safi][nexthop] = nlri
			mpnlri.setdefault((nlri.afi.pack(),nlri.safi.pack()),{}).setdefault(nexthop,[]).append(nlri.pack(addpath))

		for (pafi,psafi),data in mpnlri.iteritems():
			for nexthop,nlris in data.iteritems():
				yield self._attribute(
					pafi + psafi +
					chr(len(nexthop)) + nexthop +
					chr(0) + ''.join(nlris)
				)

	def pack (self,addpath):
		return ''.join(self.packed_attributes(addpath))

	def __len__ (self):
		return len(self.pack())

	def __str__ (self):
		return "MP_REACH_NLRI %d NLRI(s)" % len(self.nlris)

########NEW FILE########
__FILENAME__ = mpurnlri
# encoding: utf-8
"""
mprnlri.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== MP NLRI (14)

class MPURNLRI (Attribute):
	FLAG = Flag.OPTIONAL
	ID = AttributeID.MP_UNREACH_NLRI
	MULTIPLE = True

	def __init__ (self,nlris):
		self.nlris = nlris

	def packed_attributes (self,addpath):
		if not self.nlris:
			return

		mpurnlri = {}
		for nlri in self.nlris:
			mpurnlri.setdefault((nlri.afi.pack(),nlri.safi.pack()),[]).append(nlri.pack(addpath))

		for (pafi,psafi),nlris in mpurnlri.iteritems():
			yield self._attribute(pafi + psafi + ''.join(nlris))

	def pack (self,addpath):
		return ''.join(self.packed_attributes(addpath))

	def __len__ (self):
		return len(self.pack())

	def __str__ (self):
		return "MP_UNREACH_NLRI %d NLRI(s)" % len(self.nlris)

########NEW FILE########
__FILENAME__ = nexthop
# encoding: utf-8
"""
nexthop.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.protocol.ip.inet import Inet,rawinet
from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== NextHop (3)

# from struct import pack
# def cachedNextHop (afi,safi,packed):
# 	cache = pack('HB%ss' % len(packed),afi,safi,packed)
# 	if cache in NextHop.cache:
# 		return NextHop.cache[cache]
# 	instance = NextHop(afi,safi,packed)
# 	if NextHop.caching:
# 		NextHop.cache[cache] = instance
# 	return instance

def cachedNextHop (packed):
	if not packed:
		return packed

	if packed in NextHop.cache:
		return NextHop.cache[packed]
	instance = NextHop(packed)

	if NextHop.caching:
		NextHop.cache[packed] = instance
	return instance

class NextHop (Attribute,Inet):
	ID = AttributeID.NEXT_HOP
	FLAG = Flag.TRANSITIVE
	MULTIPLE = False

	cache = {}
	caching = False

	def __init__ (self,packed):
		Inet.__init__(self,*rawinet(packed))

	def pack (self,asn4=None):
		return self._attribute(self.packed)

########NEW FILE########
__FILENAME__ = origin
# encoding: utf-8
"""
attributes.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== Origin (1)

class Origin (Attribute):
	ID = AttributeID.ORIGIN
	FLAG = Flag.TRANSITIVE
	MULTIPLE = False

	IGP        = 0x00
	EGP        = 0x01
	INCOMPLETE = 0x02

	def __init__ (self,origin):
		self.origin = origin

	def pack (self,asn4=None):
		return self._attribute(chr(self.origin))

	def __len__ (self):
		return len(self.pack())

	def __str__ (self):
		if self.origin == 0x00: return 'igp'
		if self.origin == 0x01: return 'egp'
		if self.origin == 0x02: return 'incomplete'
		return 'invalid'

########NEW FILE########
__FILENAME__ = originatorid
# encoding: utf-8
"""
originatorid.py

Created by Thomas Mangin on 2012-07-07.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.protocol.ip.inet import Inet
from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag,Attribute

# =================================================================== OriginatorID (3)

class OriginatorID (Attribute,Inet):
	ID = AttributeID.ORIGINATOR_ID
	FLAG = Flag.OPTIONAL
	MULTIPLE = False

	# Take an IP as value
	def __init__ (self,afi,safi,packed):
		Inet.__init__(self,afi,safi,packed)
		# This override Inet.pack too.
		self.packed = self._attribute(Inet.pack(self))

	def pack (self,asn4=None):
		return Inet.pack(self)

	def __str__ (self):
		return Inet.__str__(self)

########NEW FILE########
__FILENAME__ = unknown
# encoding: utf-8
"""
unknown.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message.update.attribute import Attribute

# =================================================================== MED (4)

class UnknownAttribute (Attribute):
	MULTIPLE = False

	def __init__ (self,code,flag,data):
		self.ID = code
		self.FLAG = flag
		self.data = data
		self.index = ''

	def pack (self,asn4=None):
		return self._attribute(self.data)

	def __len__ (self):
		return len(self.data)

	def __str__ (self):
		return '0x' + ''.join('%02x' % ord(_) for _ in self.data)

########NEW FILE########
__FILENAME__ = factory
# encoding: utf-8
"""
factory.py

Created by Thomas Mangin on 2010-01-16.
Copyright (c) 2009-2013  Exa Networks. All rights reserved.
"""

from exabgp.bgp.message.update.attributes import Attributes
from exabgp.bgp.message.update.attribute.id import AttributeID as AID
from exabgp.bgp.message.notification import Notify

def AttributesFactory (nlriFactory,negotiated,data):
	try:
		# caching and checking the last attribute parsed as nice implementation group them :-)
		if Attributes.cached and Attributes.cached.cacheable and data.startswith(Attributes.cached.prefix):
			attributes = Attributes.cached
			data = data[len(attributes.prefix):]
		else:
			attributes = Attributes()
			Attributes.cached = attributes

		# XXX: hackish for now
		attributes.mp_announce = []
		attributes.mp_withdraw = []

		attributes.negotiated = negotiated
		attributes.nlriFactory = nlriFactory
		attributes.factory(data)
		if AID.AS_PATH in attributes and AID.AS4_PATH in attributes:
			attributes.merge_attributes()
		return attributes
	except IndexError:
		raise Notify(3,2,data)

########NEW FILE########
__FILENAME__ = eor
# encoding: utf-8
"""
eor.py

Created by Thomas Mangin on 2010-01-16.
Copyright (c) 2009-2013  Exa Networks. All rights reserved.
"""
from struct import unpack

from exabgp.protocol.family import AFI,SAFI

from exabgp.bgp.message import Message
from exabgp.bgp.message.direction import IN,OUT
from exabgp.bgp.message.update.nlri.eor import NLRIEOR
from exabgp.bgp.message.update.attributes import Attributes

# =================================================================== End-Of-RIB
# not technically a different message type but easier to treat as one

def _short (data):
	return unpack('!H',data[:2])[0]

class EOR (Message):
	TYPE = chr(0x02)  # it is an update
	MP = NLRIEOR.PREFIX

	def __init__ (self,afi,safi,action=OUT.announce):
		self.nlris = [NLRIEOR(afi,safi,action),]
		self.attributes = Attributes()

	def message (self):
		return self._message(
			self.nlris[0].pack()
		)

	def __str__ (self):
		return 'EOR'

# default IPv4 unicast
def EORFactory (data='\x00\x01\x02'):
	afi  = _short(data[-3:-1])
	safi = ord(data[-1])
	return EOR(afi,safi,IN.announced)

########NEW FILE########
__FILENAME__ = factory
# encoding: utf-8
"""
factory.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.protocol.family import AFI,SAFI

from exabgp.bgp.message import defix
from exabgp.bgp.message.direction import IN

from exabgp.bgp.message.update.attribute.id import AttributeID as AID

from exabgp.bgp.message.update import Update
#from exabgp.bgp.message.update.nlri.route import Route
from exabgp.bgp.message.notification import Notify

from exabgp.bgp.message.update.nlri.factory import NLRIFactory
from exabgp.bgp.message.update.attributes.factory import AttributesFactory

from exabgp.util.od import od
from exabgp.logger import Logger,LazyFormat

# XXX: FIXME: this can raise ValueError. IndexError,TypeError, struct.error (unpack) = check it is well intercepted
def UpdateFactory (negotiated,data):
	logger = Logger()

	length = len(data)

	lw,withdrawn,data = defix(data)

	if len(withdrawn) != lw:
		raise Notify(3,1,'invalid withdrawn routes length, not enough data available')

	la,attribute,announced = defix(data)

	if len(attribute) != la:
		raise Notify(3,1,'invalid total path attribute length, not enough data available')

	if 2 + lw + 2+ la + len(announced) != length:
		raise Notify(3,1,'error in BGP message length, not enough data for the size announced')

	attributes = AttributesFactory(NLRIFactory,negotiated,attribute)

	# Is the peer going to send us some Path Information with the route (AddPath)
	addpath = negotiated.addpath.receive(AFI(AFI.ipv4),SAFI(SAFI.unicast))
	nho = attributes.get(AID.NEXT_HOP,None)
	nh = nho.packed if nho else None

	if not withdrawn:
		logger.parser(LazyFormat("parsed no withdraw nlri",od,''))

	nlris = []
	while withdrawn:
		length,nlri = NLRIFactory(AFI.ipv4,SAFI.unicast_multicast,withdrawn,addpath,nh,IN.withdrawn)
		logger.parser(LazyFormat("parsed withdraw nlri %s payload " % nlri,od,withdrawn[:len(nlri)]))
		withdrawn = withdrawn[length:]
		nlris.append(nlri)

	if not announced:
		logger.parser(LazyFormat("parsed no announced nlri",od,''))

	while announced:
		length,nlri = NLRIFactory(AFI.ipv4,SAFI.unicast_multicast,announced,addpath,nh,IN.announced)
		logger.parser(LazyFormat("parsed announce nlri %s payload " % nlri,od,announced[:len(nlri)]))
		announced = announced[length:]
		nlris.append(nlri)

	for nlri in attributes.mp_withdraw:
		nlris.append(nlri)

	for nlri in attributes.mp_announce:
		nlris.append(nlri)

	return Update(nlris,attributes)

########NEW FILE########
__FILENAME__ = bgp
# encoding: utf-8
"""
bgp.py

Created by Thomas Mangin on 2012-07-08.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import pack,unpack
from exabgp.protocol.family import AFI,SAFI

from exabgp.bgp.message.update.nlri.prefix import mask_to_bytes,Prefix

class PathInfo (object):
	def __init__ (self,integer=None,ip=None,packed=None):
		if packed:
			self.path_info = packed
		elif ip:
			self.path_info = ''.join([chr(int(_)) for _ in ip.split('.')])
		elif integer:
			self.path_info = ''.join([chr((integer>>offset) & 0xff) for offset in [24,16,8,0]])
		else:
			self.path_info = ''
		#sum(int(a)<<offset for (a,offset) in zip(ip.split('.'), range(24, -8, -8)))

	def __len__ (self):
		return len(self.path_info)

	def json (self):
		return '"path-information": "%s"' % '.'.join([str(ord(_)) for _ in self.path_info])

	def __str__ (self):
		if self.path_info:
			return ' path-information %s' % '.'.join([str(ord(_)) for _ in self.path_info])
		return ''

	def pack (self):
		if self.path_info:
			return self.path_info
		return '\x00\x00\x00\x00'

_NoPathInfo = PathInfo()


class Labels (object):
	biggest = pow(2,20)

	def __init__ (self,labels):
		self.labels = labels
		packed = []
		for label in labels:
			# shift to 20 bits of the label to be at the top of three bytes and then truncate.
			packed.append(pack('!L',label << 4)[1:])
		# Mark the bottom of stack with the bit
		if packed:
			packed.pop()
			packed.append(pack('!L',(label << 4)|1)[1:])
		self.packed = ''.join(packed)
		self._len = len(self.packed)

	def pack (self):
		return self.packed

	def __len__ (self):
		return self._len

	def json (self):
		if self._len > 1:
			return '"label": [ %s ]' % ', '.join([str(_) for _ in self.labels])
		else:
			return ''

	def __str__ (self):
		if self._len > 1:
			return ' label [ %s ]' % ' '.join([str(_) for _ in self.labels])
		elif self._len == 1:
			return ' label %s' % self.labels[0]
		else:
			return ''

_NoLabels = Labels([])

class RouteDistinguisher (object):
	def __init__ (self,rd):
		self.rd = rd
		self._len = len(self.rd)

	def pack (self):
		return self.rd

	def __len__ (self):
		return self._len

	def _str (self):
		t,c1,c2,c3 = unpack('!HHHH',self.rd)
		if t == 0:
			rd = '%d:%d' % (c1,(c2<<16)+c3)
		elif t == 1:
			rd = '%d.%d.%d.%d:%d' % (c1>>8,c1&0xFF,c2>>8,c2&0xFF,c3)
		elif t == 2:
			rd = '%d:%d' % ((c1<<16)+c2,c3)
		else:
			rd = str(self.rd)
		return rd

	def json (self):
		if not self.rd:
			return ''
		return '"route-distinguisher": "%s"' % self._str()

	def __str__ (self):
		if not self.rd:
			return ''
		return ' route-distinguisher %s' % self._str()

_NoRD = RouteDistinguisher('')


class NLRI (Prefix):
	def __init__(self,afi,safi,packed,mask,nexthop,action):
		self.path_info = _NoPathInfo
		self.labels = _NoLabels
		self.rd = _NoRD
		self.nexthop = nexthop
		self.action = action

		Prefix.__init__(self,afi,safi,packed,mask)

	def has_label (self):
		if self.afi == AFI.ipv4 and self.safi in (SAFI.nlri_mpls,SAFI.mpls_vpn):
			return True
		if self.afi == AFI.ipv6 and self.safi == SAFI.mpls_vpn:
			return True
		return False

	def nlri (self):
		return "%s%s%s%s" % (self.prefix(),str(self.labels),str(self.path_info),str(self.rd))

	def __len__ (self):
		prefix_len = len(self.path_info) + len(self.labels) + len(self.rd)
		return 1 + prefix_len + mask_to_bytes[self.mask]

	def __str__ (self):
		nexthop = ' next-hop %s' % self.nexthop.inet() if self.nexthop else ''
		return "%s%s" % (self.nlri(),nexthop)

	def __eq__ (self,other):
		return str(self) == str(other)

	def __ne__ (self,other):
		return not self.__eq__(other)

	def json (self,announced=True):
		label = self.labels.json()
		pinfo = self.path_info.json()
		rdist = self.rd.json()

		r = []
		if announced:
			if self.labels: r.append(label)
			if self.rd: r.append(rdist)
		if self.path_info: r.append(pinfo)
		return '"%s": { %s }' % (self.prefix(),", ".join(r))

	def pack (self,addpath):
		if addpath:
			path_info = self.path_info.pack()
		else:
			path_info = ''

		if self.has_label():
			length = len(self.labels)*8 + len(self.rd)*8 + self.mask
			return path_info + chr(length) + self.labels.pack() + self.rd.pack() + self.packed[:mask_to_bytes[self.mask]]
		else:
			return path_info + Prefix.pack(self)

	def index (self):
		return self.pack(True)+self.rd.rd+self.path_info.path_info

########NEW FILE########
__FILENAME__ = eor
#!/usr/bin/env python
# encoding: utf-8
"""
eor.py

Created by Thomas Mangin on 2012-07-20.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.protocol.family import AFI,SAFI
from exabgp.protocol.ip.address import Address

class NLRIEOR (Address):
	PREFIX = '\x00\x00\x00\x07\x90\x0f\x00\x03'

	nexthop = None

	def __init__ (self,afi,safi,action):
		Address.__init__(self,afi,safi)
		self.action = action

	def nlri (self):
		return 'eor %d/%d' % (self.afi,self.safi)

	def pack (self):
		if self.afi == AFI.ipv4 and self.safi == SAFI.unicast:
			return '\x00\x00\x00\x00'
		return self.PREFIX + self.afi.pack() + self.safi.pack()

	def __str__ (self):
		return self.extensive()

	def extensive (self):
		return 'eor %d/%d (%s %s)' % (self.afi,self.safi,self.afi,self.safi)

	def json (self):
		return '"eor": { "afi" : "%s", "safi" : "%s" }' % (self.afi,self.safi)

########NEW FILE########
__FILENAME__ = factory
# encoding: utf-8
"""
generic.py

Created by Thomas Mangin on 2012-07-08.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message.notification import Notify

from struct import unpack
from exabgp.protocol.family import AFI,SAFI
from exabgp.bgp.message.update.nlri.bgp import NLRI,PathInfo,Labels,RouteDistinguisher,mask_to_bytes
from exabgp.bgp.message.update.nlri.flow import FlowNLRI,decode,factory,CommonOperator
from exabgp.bgp.message.update.attribute.nexthop import cachedNextHop

from exabgp.bgp.message.direction import IN

from exabgp.util.od import od
from exabgp.logger import Logger,LazyFormat

def NLRIFactory (afi,safi,bgp,has_multiple_path,nexthop,action):
	if safi in (133,134):
		return _FlowNLRIFactory(afi,safi,nexthop,bgp,action)
	else:
		return _NLRIFactory(afi,safi,bgp,has_multiple_path,nexthop,action)

def _nlrifactory (afi,safi,bgp,action):
	labels = []
	rd = ''

	mask = ord(bgp[0])
	bgp = bgp[1:]

	if SAFI(safi).has_label():
		while bgp and mask >= 8:
			label = int(unpack('!L',chr(0) + bgp[:3])[0])
			bgp = bgp[3:]
			mask -= 24  # 3 bytes
			# The last 4 bits are the bottom of Stack
			# The last bit is set for the last label
			labels.append(label>>4)
			# This is a route withdrawal
			if label == 0x800000 and action == IN.withdrawn:
				break
			# This is a next-hop
			if label == 0x000000:
				break
			if label & 1:
				break

	if SAFI(safi).has_rd():
		mask -= 8*8  # the 8 bytes of the route distinguisher
		rd = bgp[:8]
		bgp = bgp[8:]

	if mask < 0:
		raise Notify(3,10,'invalid length in NLRI prefix')

	if not bgp and mask:
		raise Notify(3,10,'not enough data for the mask provided to decode the NLRI')

	size = mask_to_bytes.get(mask,None)
	if size is None:
		raise Notify(3,10,'invalid netmask found when decoding NLRI')

	if len(bgp) < size:
		raise Notify(3,10,'could not decode route with AFI %d sand SAFI %d' % (afi,safi))

	network,bgp = bgp[:size],bgp[size:]
	padding = '\0'*(NLRI.length[afi]-size)
	prefix = network + padding

	return labels,rd,mask,size,prefix,bgp

def _FlowNLRIFactory (afi,safi,nexthop,bgp,action):
	logger = Logger()
	logger.parser(LazyFormat("parsing flow nlri payload ",od,bgp))

	total = len(bgp)
	length,bgp = ord(bgp[0]),bgp[1:]

	if length & 0xF0 == 0xF0:  # bigger than 240
		extra,bgp = ord(bgp[0]),bgp[1:]
		length = ((length & 0x0F) << 16) + extra

	if length > len(bgp):
		raise Notify(3,10,'invalid length at the start of the the flow')

	bgp = bgp[:length]
	nlri = FlowNLRI(afi,safi)
	nlri.action = action

	if nexthop:
		nlri.nexthop = cachedNextHop(nexthop)

	if safi == SAFI.flow_vpn:
		nlri.rd = RouteDistinguisher(bgp[:8])
		bgp = bgp[8:]

	seen = []

	while bgp:
		what,bgp = ord(bgp[0]),bgp[1:]

		if what not in decode.get(afi,{}):
			raise Notify(3,10,'unknown flowspec component received for address family %d' % what)

		seen.append(what)
		if sorted(seen) != seen:
			raise Notify(3,10,'components are not sent in the right order %s' % seen)

		decoder = decode[afi][what]
		klass = factory[afi][what]

		if decoder == 'prefix':
			if afi == AFI.ipv4:
				_,rd,mask,size,prefix,left = _nlrifactory(afi,safi,bgp,action)
				adding = klass(prefix,mask)
				if not nlri.add(adding):
					raise Notify(3,10,'components are incompatible (two sources, two destinations, mix ipv4/ipv6) %s' % seen)
				logger.parser(LazyFormat("added flow %s (%s) payload " % (klass.NAME,adding),od,bgp[:-len(left)]))
				bgp = left
			else:
				byte,bgp = bgp[1],bgp[0]+bgp[2:]
				offset = ord(byte)
				_,rd,mask,size,prefix,left = _nlrifactory(afi,safi,bgp,action)
				adding = klass(prefix,mask,offset)
				if not nlri.add(adding):
					raise Notify(3,10,'components are incompatible (two sources, two destinations, mix ipv4/ipv6) %s' % seen)
				logger.parser(LazyFormat("added flow %s (%s) payload " % (klass.NAME,adding),od,bgp[:-len(left)]))
				bgp = left
		else:
			end = False
			while not end:
				byte,bgp = ord(bgp[0]),bgp[1:]
				end = CommonOperator.eol(byte)
				operator = CommonOperator.operator(byte)
				length = CommonOperator.length(byte)
				value,bgp = bgp[:length],bgp[length:]
				adding = klass.decoder(value)
				nlri.add(klass(operator,adding))
				logger.parser(LazyFormat("added flow %s (%s) operator %d len %d payload " % (klass.NAME,adding,byte,length),od,value))

	return total-len(bgp),nlri

def _NLRIFactory (afi,safi,bgp,has_multiple_path,nexthop,action):
	if has_multiple_path:
		path_identifier = bgp[:4]
		bgp = bgp[4:]
		length = 4
	else:
		path_identifier = ''
		length = 0

	labels,rd,mask,size,prefix,left = _nlrifactory(afi,safi,bgp,action)

	nlri = NLRI(afi,safi,prefix,mask,cachedNextHop(nexthop),action)

	if path_identifier:
		nlri.path_info = PathInfo(packed=path_identifier)
	if labels:
		nlri.labels = Labels(labels)
	if rd:
		nlri.rd = RouteDistinguisher(rd)

	return length + len(bgp) - len(left),nlri

########NEW FILE########
__FILENAME__ = flow
# encoding: utf-8
"""
flow.py

Created by Thomas Mangin on 2010-01-14.
Copyright (c) 2009-2013  Exa Networks. All rights reserved.
"""

from struct import pack,unpack

from exabgp.protocol.family import AFI,SAFI
from exabgp.protocol.ip.address import Address
from exabgp.bgp.message.direction import OUT
from exabgp.bgp.message.update.nlri.prefix import Prefix
from exabgp.bgp.message.notification import Notify

from exabgp.protocol import Protocol,NamedProtocol
from exabgp.protocol.ip.icmp import ICMPType,ICMPCode,NamedICMPType,NamedICMPCode
from exabgp.protocol.ip.fragment import Fragment,NamedFragment
from exabgp.protocol.ip.tcp.flag import TCPFlag,NamedTCPFlag

# =================================================================== Flow Components

class IComponent (object):
	# all have ID
	# should have an interface for serialisation and put it here
	pass

class CommonOperator (object):
	# power (2,x) is the same as 1 << x which is what the RFC say the len is
	power = {0:1, 1:2, 2:4, 3:8,}
	rewop = {1:0, 2:1, 4:2, 8:3,}
	len_position = 0x30

	EOL       = 0x80  # 0b10000000
	AND       = 0x40  # 0b01000000
	LEN       = 0x30  # 0b00110000
	NOP       = 0x00

	OPERATOR  = 0xFF ^ (EOL | LEN)

	@staticmethod
	def eol (data):
		return data & CommonOperator.EOL

	@staticmethod
	def operator (data):
		return data & CommonOperator.OPERATOR

	@staticmethod
	def length (data):
		return 1 << ((data & CommonOperator.LEN) >> 4)

class NumericOperator (CommonOperator):
#	reserved  = 0x08  # 0b00001000
	LT        = 0x04  # 0b00000100
	GT        = 0x02  # 0b00000010
	EQ        = 0x01  # 0b00000001

class BinaryOperator (CommonOperator):
#	reserved  = 0x0C  # 0b00001100
	NOT       = 0x02  # 0b00000010
	MATCH     = 0x01  # 0b00000001

def _len_to_bit (value):
	return NumericOperator.rewop[value] << 4

def _bit_to_len (value):
	return NumericOperator.power[(value & CommonOperator.len_position) >> 4]

def _number (string):
	value = 0
	for c in string:
		value = (value << 8) + ord(c)
	return value

# def short (value):
# 	return (ord(value[0]) << 8) + ord(value[1])

# Interface ..................

class IPv4 (object):
	afi = AFI.ipv4

class IPv6 (object):
	afi = AFI.ipv6

class IPrefix (object):
	pass

# Prococol

class IPrefix4 (IPrefix,IComponent,IPv4):
	# not used, just present for simplying the nlri generation
	operations = 0x0
	# NAME

	def __init__ (self,raw,netmask):
		self.nlri = Prefix(self.afi,SAFI.flow_ip,raw,netmask)

	def pack (self):
		raw = self.nlri.pack()
		return "%s%s" % (chr(self.ID),raw)

	def __str__ (self):
		return str(self.nlri)

class IPrefix6 (IPrefix,IComponent,IPv6):
	# not used, just present for simplying the nlri generation
	operations = 0x0
	# NAME

	def __init__ (self,raw,netmask,offset):
		self.nlri = Prefix(self.afi,SAFI.flow_ip,raw,netmask)
		self.offset = offset

	def pack (self):
		raw = self.nlri.packed_ip()
		return "%s%s%s%s" % (chr(self.ID),chr(self.nlri.mask),chr(self.offset),raw)

	def __str__ (self):
		return "%s/%s" % (self.nlri,self.offset)


class IOperation (IComponent):
	# need to implement encode which encode the value of the operator

	def __init__ (self,operations,value):
		self.operations = operations
		self.value = value
		self.first = None  # handled by pack/str

	def pack (self):
		l,v = self.encode(self.value)
		op = self.operations | _len_to_bit(l)
		return "%s%s" % (chr(op),v)

	def encode (self,value):
		raise NotImplemented('this method must be implemented by subclasses')

	def decode (self,value):
		raise NotImplemented('this method must be implemented by subclasses')

#class IOperationIPv4 (IOperation):
#	def encode (self,value):
#		return 4, socket.pton(socket.AF_INET,value)

class IOperationByte (IOperation):
	def encode (self,value):
		return 1,chr(value)

	def decode (self,bgp):
		return ord(bgp[0]),bgp[1:]

class IOperationByteShort (IOperation):
	def encode (self,value):
		if value < (1<<8):
			return 1,chr(value)
		return 2,pack('!H',value)

	def decode (self,bgp):
		return unpack('!H',bgp[:2])[0],bgp[2:]

# String representation for Numeric and Binary Tests

class NumericString (object):
	_string = {
		NumericOperator.LT   : '<',
		NumericOperator.GT   : '>',
		NumericOperator.EQ   : '=',
		NumericOperator.LT|NumericOperator.EQ : '<=',
		NumericOperator.GT|NumericOperator.EQ : '>=',

		NumericOperator.AND|NumericOperator.LT   : '&<',
		NumericOperator.AND|NumericOperator.GT   : '&>',
		NumericOperator.AND|NumericOperator.EQ   : '&=',
		NumericOperator.AND|NumericOperator.LT|NumericOperator.EQ : '&<=',
		NumericOperator.AND|NumericOperator.GT|NumericOperator.EQ : '&>=',
	}

	def __str__ (self):
		return "%s%s" % (self._string[self.operations & (CommonOperator.EOL ^ 0xFF)], self.value)


class BinaryString (object):
	_string = {
		BinaryOperator.NOT   : '!',
		BinaryOperator.MATCH : '=',
		BinaryOperator.AND|BinaryOperator.NOT   : '&!',
		BinaryOperator.AND|BinaryOperator.MATCH : '&=',
	}

	def __str__ (self):
		return "%s%s" % (self._string[self.operations & (CommonOperator.EOL ^ 0xFF)], self.value)

# Components ..............................

def converter (function,klass=int):
	def _integer (value):
		try:
			return klass(value)
		except ValueError:
			return function(value)
	return _integer

def decoder (function,klass=int):
	def _inner (value):
		return klass(function(value))
	return _inner

def PacketLength (data):
	_str_bad_length = "cloudflare already found that invalid max-packet length for for you .."
	number = int(data)
	if number > 0xFFFF:
		raise ValueError(_str_bad_length)
	return number

def PortValue (data):
	_str_bad_port = "you tried to set an invalid port number .."
	number = int(data)
	if number < 0 or number > 0xFFFF:
		raise ValueError(_str_bad_port)
	return number

def DSCPValue (data):
	_str_bad_dscp = "you tried to filter a flow using an invalid dscp for a component .."
	number = int(data)
	if number < 0 or number > 0xFFFF:
		raise ValueError(_str_bad_dscp)
	return number

def ClassValue (data):
	_str_bad_class = "you tried to filter a flow using an invalid traffic class for a component .."
	number = int(data)
	if number < 0 or number > 0xFFFF:
		raise ValueError(_str_bad_class)
	return number

def LabelValue (data):
	_str_bad_label = "you tried to filter a flow using an invalid traffic label for a component .."
	number = int(data)
	if number < 0 or number > 0xFFFFF:  # 20 bits 5 bytes
		raise ValueError(_str_bad_label)
	return number

# Protocol Shared

class FlowDestination (object):
	ID = 0x01
	NAME = 'destination'

class FlowSource (object):
	ID = 0x02
	NAME = 'source'

# Prefix
class Flow4Destination (IPrefix4,FlowDestination):
	pass

# Prefix
class Flow4Source (IPrefix4,FlowSource):
	pass

# Prefix
class Flow6Destination (IPrefix6,FlowDestination):
	pass

# Prefix
class Flow6Source (IPrefix6,FlowSource):
	pass

class FlowIPProtocol (IOperationByte,NumericString,IPv4):
	ID  = 0x03
	NAME = 'protocol'
	converter = staticmethod(converter(NamedProtocol,Protocol))
	decoder = staticmethod(decoder(ord,Protocol))

class FlowNextHeader (IOperationByte,NumericString,IPv6):
	ID  = 0x03
	NAME = 'next-header'
	converter = staticmethod(converter(NamedProtocol,Protocol))
	decoder = staticmethod(decoder(ord,Protocol))

class FlowAnyPort (IOperationByteShort,NumericString,IPv4,IPv6):
	ID  = 0x04
	NAME = 'port'
	converter = staticmethod(converter(PortValue))
	decoder = staticmethod(_number)

class FlowDestinationPort (IOperationByteShort,NumericString,IPv4,IPv6):
	ID  = 0x05
	NAME = 'destination-port'
	converter = staticmethod(converter(PortValue))
	decoder = staticmethod(_number)

class FlowSourcePort (IOperationByteShort,NumericString,IPv4,IPv6):
	ID  = 0x06
	NAME = 'source-port'
	converter = staticmethod(converter(PortValue))
	decoder = staticmethod(_number)

class FlowICMPType (IOperationByte,BinaryString,IPv4,IPv6):
	ID = 0x07
	NAME = 'icmp-type'
	converter = staticmethod(converter(NamedICMPType))
	decoder = staticmethod(decoder(_number,ICMPType))

class FlowICMPCode (IOperationByte,BinaryString,IPv4,IPv6):
	ID = 0x08
	NAME = 'icmp-code'
	converter = staticmethod(converter(NamedICMPCode))
	decoder = staticmethod(decoder(_number,ICMPCode))

class FlowTCPFlag (IOperationByte,BinaryString,IPv4,IPv6):
	ID = 0x09
	NAME = 'tcp-flags'
	converter = staticmethod(converter(NamedTCPFlag))
	decoder = staticmethod(decoder(ord,TCPFlag))

class FlowPacketLength (IOperationByteShort,NumericString,IPv4,IPv6):
	ID = 0x0A
	NAME = 'packet-length'
	converter = staticmethod(converter(PacketLength))
	decoder = staticmethod(_number)

# RFC2474
class FlowDSCP (IOperationByteShort,NumericString,IPv4):
	ID = 0x0B
	NAME = 'dscp'
	converter = staticmethod(converter(DSCPValue))
	decoder = staticmethod(_number)

# RFC2460
class FlowTrafficClass (IOperationByte,NumericString,IPv6):
	ID = 0x0B
	NAME = 'traffic-class'
	converter = staticmethod(converter(ClassValue))
	decoder = staticmethod(_number)

# BinaryOperator
class FlowFragment (IOperationByteShort,NumericString,IPv4):
	ID = 0x0C
	NAME = 'fragment'
	converter = staticmethod(converter(NamedFragment))
	decoder = staticmethod(decoder(ord,Fragment))

# draft-raszuk-idr-flow-spec-v6-01
class FlowFlowLabel (IOperationByteShort,NumericString,IPv6):
	ID = 0x0D
	NAME = 'flow-label'
	converter = staticmethod(converter(LabelValue))
	decoder = staticmethod(_number)


# ..........................................................

decode = {AFI.ipv4: {}, AFI.ipv6: {}}
factory = {AFI.ipv4: {}, AFI.ipv6: {}}

for content in dir():
	klass = globals().get(content,None)
	if not isinstance(klass,type(IComponent)):
		continue
	if not issubclass(klass,IComponent):
		continue
	if issubclass(klass,IPv4):
		afi = AFI.ipv4
	elif issubclass(klass,IPv6):
		afi = AFI.ipv6
	else:
		continue
	ID = getattr(klass,'ID',None)
	if not ID:
		continue
	factory[afi][ID] = klass
	name = getattr(klass,'NAME')

	if issubclass(klass, IOperation):
		if issubclass(klass, BinaryString):
			decode[afi][ID] = 'binary'
		elif issubclass(klass, NumericString):
			decode[afi][ID] = 'numeric'
		else:
			raise RuntimeError('invalid class defined (string)')
	elif issubclass(klass, IPrefix):
		decode[afi][ID] = 'prefix'
	else:
		raise RuntimeError('unvalid class defined (type)')

# ..........................................................

def _unique ():
	value = 0
	while True:
		yield value
		value += 1

unique = _unique()

class FlowNLRI (Address):
	def __init__ (self,afi=AFI.ipv4,safi=SAFI.flow_ip,rd=None):
		Address.__init__(self,afi,safi)
		self.rules = {}
		self.action = OUT.announce
		self.nexthop = None
		self.rd = rd

	def __len__ (self):
		return len(self.pack())

	def add (self,rule):
		ID = rule.ID
		if ID in (FlowDestination.ID,FlowSource.ID):
			if ID in self.rules:
				return False
			if ID == FlowDestination.ID:
				pair = self.rules.get(FlowSource.ID,[])
			else:
				pair = self.rules.get(FlowDestination.ID,[])
			if pair:
				if rule.afi != pair[0].afi:
					return False
		self.rules.setdefault(ID,[]).append(rule)
		return True

	# The API requires addpath, but it is irrelevant here.
	def pack (self,addpath=None):
		ordered_rules = []
		# the order is a RFC requirement
		for ID in sorted(self.rules.keys()):
			rules = self.rules[ID]
			# for each component get all the operation to do
			# the format use does not prevent two opposing rules meaning that no packet can ever match
			for rule in rules:
				rule.operations &= (CommonOperator.EOL ^ 0xFF)
			rules[-1].operations |= CommonOperator.EOL
			# and add it to the last rule
			if ID not in (FlowDestination.ID,FlowSource.ID):
				ordered_rules.append(chr(ID))
			ordered_rules.append(''.join(rule.pack() for rule in rules))

		components = ''.join(ordered_rules)

		if self.safi == SAFI.flow_vpn:
			components = self.rd.pack() + components

		l = len(components)
		if l < 0xF0:
			data = "%s%s" % (chr(l),components)
		elif l < 0x0FFF:
			data = "%s%s" % (pack('!H',l | 0xF000),components)
		else:
			raise Notify("rule too big for NLRI - how to handle this - does this work ?")
			data = "%s" % chr(0)

		return data

	def extensive (self):
		string = []
		for index in sorted(self.rules):
			rules = self.rules[index]
			s = []
			for idx,rule in enumerate(rules):
				# only add ' ' after the first element
				if idx and not rule.operations & NumericOperator.AND:
					s.append(' ')
				s.append(rule)
			string.append(' %s %s' % (rules[0].NAME,''.join(str(_) for _ in s)))
		nexthop = ' next-hop %s' % self.nexthop if self.nexthop else ''
		rd = str(self.rd) if self.rd else ''
		return 'flow' + rd + ''.join(string) + nexthop

	def __str__ (self):
		return self.extensive()

	def json (self):
		# this is a stop gap so flow route parsing does not crash exabgp
		# delete unique when this is fixed
		return '"flow-%d": { "string": "%s" }' % (unique.next(),str(self),)

	def index (self):
		return self.pack()


def _next_index ():
	value = 0
	while True:
		yield str(value)
		value += 1

next_index = _next_index()

########NEW FILE########
__FILENAME__ = prefix
# encoding: utf-8
"""
prefix.py

Created by Thomas Mangin on 2013-08-07.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import math
from exabgp.protocol.ip.inet import Inet

mask_to_bytes = {}
for netmask in range(0,129):
	mask_to_bytes[netmask] = int(math.ceil(float(netmask)/8))


class Prefix (Inet):
	# have a .raw for the ip
	# have a .mask for the mask
	# have a .bgp with the bgp wire format of the prefix

	def __init__(self,afi,safi,packed,mask):
		self.mask = mask
		Inet.__init__(self,afi,safi,packed)

	def __str__ (self):
		return self.prefix()

	def prefix (self):
		return "%s/%s" % (self.ip,self.mask)

	def pack (self):
		return chr(self.mask) + self.packed[:mask_to_bytes[self.mask]]

	def packed_ip(self):
		return self.packed[:mask_to_bytes[self.mask]]

	def __len__ (self):
		return mask_to_bytes[self.mask] + 1

########NEW FILE########
__FILENAME__ = neighbor
# encoding: utf-8
"""
neighbor.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from collections import deque

from exabgp.protocol.family import AFI

from exabgp.bgp.message.open.holdtime import HoldTime
from exabgp.bgp.message.open.capability import AddPath

from exabgp.reactor.api.encoding import APIOptions

from exabgp.rib import RIB

# The definition of a neighbor (from reading the configuration)
class Neighbor (object):
	def __init__ (self):
		# self.logger should not be used here as long as we do use deepcopy as it contains a Lock
		self.description = ''
		self.router_id = None
		self.local_address = None
		self.peer_address = None
		self.peer_as = None
		self.local_as = None
		self.hold_time = HoldTime(180)
		self.asn4 = None
		self.add_path = 0
		self.md5 = None
		self.ttl = None
		self.group_updates = None
		self.flush = None
		self.adjribout = None

		self.api = APIOptions()

		self.passive = False

		# capability
		self.route_refresh = False
		self.graceful_restart = False
		self.multisession = None
		self.add_path = None
		self.aigp = None

		self._families = []
		self.rib = None

		self.operational = None
		self.asm = dict()

		self.messages = deque()
		self.refresh = deque()

	def make_rib (self):
		self.rib = RIB(self.name(),self.adjribout,self._families)

	# will resend all the routes once we reconnect
	def reset_rib (self):
		self.rib.reset()
		self.messages = deque()
		self.refresh = deque()

	# back to square one, all the routes are removed
	def clear_rib (self):
		self.rib.clear()
		self.messages = deque()
		self.refresh = deque()

	def name (self):
		if self.multisession:
			session = '/'.join("%s-%s" % (afi.name(),safi.name()) for (afi,safi) in self.families())
		else:
			session = 'in-open'
		return "neighbor %s local-ip %s local-as %s peer-as %s router-id %s family-allowed %s" % (self.peer_address,self.local_address,self.local_as,self.peer_as,self.router_id,session)

	def families (self):
		# this list() is important .. as we use the function to modify self._families
		return list(self._families)

	def add_family (self,family):
		# the families MUST be sorted for neighbor indexing name to be predictable for API users
		if not family in self.families():
			afi,safi = family
			d = dict()
			d[afi] = [safi,]
			for afi,safi in self._families:
				d.setdefault(afi,[]).append(safi)
			self._families = [(afi,safi) for afi in sorted(d) for safi in sorted(d[afi])]

	def remove_family (self,family):
		if family in self.families():
			self._families.remove(family)

	def missing (self):
		if self.local_address is None: return 'local-address'
		if self.peer_address is None: return 'peer-address'
		if self.local_as is None: return 'local-as'
		if self.peer_as is None: return 'peer-as'
		if self.peer_address.afi == AFI.ipv6 and not self.router_id: return 'router-id'
		return ''

	# This function only compares the neighbor BUT NOT ITS ROUTES
	def __eq__ (self,other):
		return \
			self.router_id == other.router_id and \
			self.local_address == other.local_address and \
			self.local_as == other.local_as and \
			self.peer_address == other.peer_address and \
			self.peer_as == other.peer_as and \
			self.passive == other.passive and \
			self.hold_time == other.hold_time and \
			self.md5 == other.md5 and \
			self.ttl == other.ttl and \
			self.route_refresh == other.route_refresh and \
			self.graceful_restart == other.graceful_restart and \
			self.multisession == other.multisession and \
			self.add_path == other.add_path and \
			self.operational == other.operational and \
			self.group_updates == other.group_updates and \
			self.flush == other.flush and \
			self.adjribout == other.adjribout and \
			self.families() == other.families()

	def __ne__(self, other):
		return not self.__eq__(other)

	def pprint (self,with_changes=True):
		changes=''
		if with_changes:
			changes += '\nstatic { '
			for changes in self.rib.incoming.queued_changes():
				changes += '\n    %s' % changes.extensive()
			changes += '\n}'

		families = ''
		for afi,safi in self.families():
			families += '\n    %s %s;' % (afi.name(),safi.name())

		_api  = []
		_api.extend(['    neighbor-changes;\n',]    if self.api.neighbor_changes else [])
		_api.extend(['    receive-packets;\n',]     if self.api.receive_packets else [])
		_api.extend(['    send-packets;\n',]        if self.api.send_packets else [])
		_api.extend(['    receive-routes;\n',]      if self.api.receive_routes else [])
		_api.extend(['    receive-operational;\n',] if self.api.receive_operational else [])
		api = ''.join(_api)

		return """\
neighbor %s {
  description "%s";
  router-id %s;
  local-address %s;
  local-as %s;
  peer-as %s;%s
  hold-time %s;
%s%s%s%s%s
  capability {
%s%s%s%s%s%s%s  }
  family {%s
  }
  process {
%s  }%s
}""" % (
	self.peer_address,
	self.description,
	self.router_id,
	self.local_address,
	self.local_as,
	self.peer_as,
	'\n  passive;\n' if self.passive else '',
	self.hold_time,
	'  group-updates: %s;\n' % self.group_updates if self.group_updates else '',
	'  auto-flush: %s;\n' % 'true' if self.flush else 'false',
	'  adj-rib-out: %s;\n' % 'true' if self.adjribout else 'false',
	'  md5: %d;\n' % self.ttl if self.ttl else '',
	'  ttl-security: %d;\n' % self.ttl if self.ttl else '',
	'    asn4 enable;\n' if self.asn4 else '    asn4 disable;\n',
	'    route-refresh;\n' if self.route_refresh else '',
	'    graceful-restart %s;\n' % self.graceful_restart if self.graceful_restart else '',
	'    add-path %s;\n' % AddPath.string[self.add_path] if self.add_path else '',
	'    multi-session;\n' if self.multisession else '',
	'    operational;\n' if self.operational else '',
	'    aigp;\n' if self.aigp else '',
	families,
	api,
	changes
)

	def __str__ (self):
		return self.pprint(False)

########NEW FILE########
__FILENAME__ = timer
# encoding: utf-8
"""
timer.py

Created by Thomas Mangin on 2012-07-21.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import time

from exabgp.logger import Logger
from exabgp.bgp.message.nop import _NOP
from exabgp.bgp.message.keepalive import KeepAlive
from exabgp.bgp.message.notification import Notify

# Track the time for keepalive updates

class Timer (object):
	def __init__ (self,me,holdtime,code,subcode,message=''):
		self.logger = Logger()

		self.me = me

		self.code = code
		self.subcode = subcode
		self.message = message

		self.holdtime = holdtime
		self.last_read = time.time()
		self.last_sent = time.time()

	def tick (self,message=_NOP,ignore=_NOP.TYPE):
		if message.TYPE != ignore:
			self.last_read = time.time()
		if self.holdtime:
			left = int(self.last_read  + self.holdtime - time.time())
			self.logger.timers(self.me('Receive Timer %d second(s) left' % left))
			if left <= 0:
				raise Notify(self.code,self.subcode,self.message)
		elif message.TYPE == KeepAlive.TYPE:
			raise Notify(2,6,'Negotiated holdtime was zero, it was invalid to send us a keepalive messages')

	def keepalive (self):
		if not self.holdtime:
			return False

		left = int(self.last_sent + self.holdtime.keepalive() - time.time())
		self.logger.timers(self.me('Send Timer %d second(s) left' % left))

		if left <= 0:
			self.last_sent = time.time()
			return True
		return False

########NEW FILE########
__FILENAME__ = header
# encoding: utf-8
"""
message.py

Created by Thomas Mangin on 2013-02-26.
Copyright (c) 2009-2012 Exa Networks. All rights reserved.
"""

from struct import unpack
from exabgp.bmp.peer import Peer
from exabgp.bmp.message import Message

class Header (object):
	def __init__ (self,data):
		self.version = ord(data[0])
		self.message = Message(ord(data[1]))
		self.peer = Peer(data)

		self.time_sec = unpack('!L',data[36:40])[0]
		self.time_micro_sec = unpack('!L',data[40:44])[0]

	def validate (self):
		if self.version != 1: return False
		if not self.message.validate(): return False
		if not self.peer.validate(): return False
		return True

	def json (self):
		return "{}"

########NEW FILE########
__FILENAME__ = message
# encoding: utf-8
"""
message.py

Created by Thomas Mangin on 2013-02-26.
Copyright (c) 2009-2012 Exa Networks. All rights reserved.
"""

class Message (int):
	ROUTE_MONITORING = 0
	STATISTICS_REPORT = 1
	PEER_DOWN_NOTIFICATION = 2

	_str = {
		0 : 'route monitoring',
		1 : 'statistics report',
		2 : 'peer down notification',
	}

	def __str__ (self):
		return self._str.get(self,'unknow %d' % self)

	def validate (self):
		return self in (0,1,2)

stat = {
	0: "prefixes rejected by inbound policy",
	1: "(known) duplicate prefix advertisements",
	2: "(known) duplicate withdraws",
	3: "updates invalidated due to CLUSTER_LIST loop",
	4: "updates invalidated due to AS_PATH loop",
}

peer = {
	1: "Local system closed session, notification sent",
	2: "Local system closed session, no notification",
	3: "Remote system closed session, notification sent",
	4: "Remote system closed session, no notification",
}

########NEW FILE########
__FILENAME__ = negotiated
# encoding: utf-8
"""
message.py

Created by Thomas Mangin on 2013-02-26.
Copyright (c) 2009-2012 Exa Networks. All rights reserved.
"""

class FakeAddPath (object):
	def send (self,afi,safi):
		return False

	def receive (self,afi,safi):
		return False

class FakeNegotiated (object):
	def __init__ (self,header,asn4):
		self.asn4 = asn4
		self.addpath = FakeAddPath()

########NEW FILE########
__FILENAME__ = peer
# encoding: utf-8
"""
peer.py

Created by Thomas Mangin on 2013-02-26.
Copyright (c) 2009-2012 Exa Networks. All rights reserved.
"""

from struct import unpack
from socket import inet_ntop, AF_INET, AF_INET6

class PeerType (int):
	_str = {
		0 : 'global',
		1 : 'L3 VPN',
	}

	def __str__ (self):
		return self._str.get(self,'unknow %d' % self)

class PeerFlag (int):
	_v4v6 = 0b10000000

	def ipv4 (self):
		return not self & self._v4v6

	def ipv6 (self):
		return bool(self & self._v4v6)

class Peer (object):
	def __init__ (self,data):
		self.type = PeerType(ord(data[2]))
		self.flag = PeerFlag(ord(data[3]))
		self.distinguisher = unpack('!L',data[4:8])[0]
		self.asn = unpack('!L',data[28:32])[0]
		self.id = inet_ntop(AF_INET, data[32:36])

		if self.flag.ipv4(): self.peer_address = inet_ntop(AF_INET, data[24:28])
		if self.flag.ipv6(): self.peer_address = inet_ntop(AF_INET6, data[12:28])

	def validate (self):
		return self.type in (0,1)

########NEW FILE########
__FILENAME__ = ipaddress
# Copyright 2007 Google Inc.
#  Licensed to PSF under a Contributor Agreement.

"""A fast, lightweight IPv4/IPv6 manipulation library in Python.

This library is used to create/poke/manipulate IPv4 and IPv6 addresses
and networks.

"""

__version__ = '1.0'


import functools

IPV4LENGTH = 32
IPV6LENGTH = 128

class AddressValueError(ValueError):
    """A Value Error related to the address."""


class NetmaskValueError(ValueError):
    """A Value Error related to the netmask."""


def ip_address(address):
    """Take an IP string/int and return an object of the correct type.

    Args:
        address: A string or integer, the IP address.  Either IPv4 or
          IPv6 addresses may be supplied; integers less than 2**32 will
          be considered to be IPv4 by default.

    Returns:
        An IPv4Address or IPv6Address object.

    Raises:
        ValueError: if the *address* passed isn't either a v4 or a v6
          address

    """
    try:
        return IPv4Address(address)
    except (AddressValueError, NetmaskValueError):
        pass

    try:
        return IPv6Address(address)
    except (AddressValueError, NetmaskValueError):
        pass

    raise ValueError('%r does not appear to be an IPv4 or IPv6 address' %
                     address)


def ip_network(address, strict=True):
    """Take an IP string/int and return an object of the correct type.

    Args:
        address: A string or integer, the IP network.  Either IPv4 or
          IPv6 networks may be supplied; integers less than 2**32 will
          be considered to be IPv4 by default.

    Returns:
        An IPv4Network or IPv6Network object.

    Raises:
        ValueError: if the string passed isn't either a v4 or a v6
          address. Or if the network has host bits set.

    """
    try:
        return IPv4Network(address, strict)
    except (AddressValueError, NetmaskValueError):
        pass

    try:
        return IPv6Network(address, strict)
    except (AddressValueError, NetmaskValueError):
        pass

    raise ValueError('%r does not appear to be an IPv4 or IPv6 network' %
                     address)


def ip_interface(address):
    """Take an IP string/int and return an object of the correct type.

    Args:
        address: A string or integer, the IP address.  Either IPv4 or
          IPv6 addresses may be supplied; integers less than 2**32 will
          be considered to be IPv4 by default.

    Returns:
        An IPv4Interface or IPv6Interface object.

    Raises:
        ValueError: if the string passed isn't either a v4 or a v6
          address.

    Notes:
        The IPv?Interface classes describe an Address on a particular
        Network, so they're basically a combination of both the Address
        and Network classes.

    """
    try:
        return IPv4Interface(address)
    except (AddressValueError, NetmaskValueError):
        pass

    try:
        return IPv6Interface(address)
    except (AddressValueError, NetmaskValueError):
        pass

    raise ValueError('%r does not appear to be an IPv4 or IPv6 interface' %
                     address)


def v4_int_to_packed(address):
    """Represent an address as 4 packed bytes in network (big-endian) order.

    Args:
        address: An integer representation of an IPv4 IP address.

    Returns:
        The integer address packed as 4 bytes in network (big-endian) order.

    Raises:
        ValueError: If the integer is negative or too large to be an
          IPv4 IP address.

    """
    try:
        return address.to_bytes(4, 'big')
    except:
        raise ValueError("Address negative or too large for IPv4")


def v6_int_to_packed(address):
    """Represent an address as 16 packed bytes in network (big-endian) order.

    Args:
        address: An integer representation of an IPv6 IP address.

    Returns:
        The integer address packed as 16 bytes in network (big-endian) order.

    """
    try:
        return address.to_bytes(16, 'big')
    except:
        raise ValueError("Address negative or too large for IPv6")


def _split_optional_netmask(address):
    """Helper to split the netmask and raise AddressValueError if needed"""
    addr = str(address).split('/')
    if len(addr) > 2:
        raise AddressValueError("Only one '/' permitted in %r" % address)
    return addr


def _find_address_range(addresses):
    """Find a sequence of IPv#Address.

    Args:
        addresses: a list of IPv#Address objects.

    Returns:
        A tuple containing the first and last IP addresses in the sequence.

    """
    first = last = addresses[0]
    for ip in addresses[1:]:
        if ip._ip == last._ip + 1:
            last = ip
        else:
            break
    return (first, last)


def _count_righthand_zero_bits(number, bits):
    """Count the number of zero bits on the right hand side.

    Args:
        number: an integer.
        bits: maximum number of bits to count.

    Returns:
        The number of zero bits on the right hand side of the number.

    """
    if number == 0:
        return bits
    for i in range(bits):
        if (number >> i) & 1:
            return i
    # All bits of interest were zero, even if there are more in the number
    return bits


def summarize_address_range(first, last):
    """Summarize a network range given the first and last IP addresses.

    Example:
        >>> list(summarize_address_range(IPv4Address('192.0.2.0'),
        ...                              IPv4Address('192.0.2.130')))
        ...                                #doctest: +NORMALIZE_WHITESPACE
        [IPv4Network('192.0.2.0/25'), IPv4Network('192.0.2.128/31'),
         IPv4Network('192.0.2.130/32')]

    Args:
        first: the first IPv4Address or IPv6Address in the range.
        last: the last IPv4Address or IPv6Address in the range.

    Returns:
        An iterator of the summarized IPv(4|6) network objects.

    Raise:
        TypeError:
            If the first and last objects are not IP addresses.
            If the first and last objects are not the same version.
        ValueError:
            If the last object is not greater than the first.
            If the version of the first address is not 4 or 6.

    """
    if (not (isinstance(first, _BaseAddress) and
             isinstance(last, _BaseAddress))):
        raise TypeError('first and last must be IP addresses, not networks')
    if first.version != last.version:
        raise TypeError("%s and %s are not of the same version" % (
                         first, last))
    if first > last:
        raise ValueError('last IP address must be greater than first')

    if first.version == 4:
        ip = IPv4Network
    elif first.version == 6:
        ip = IPv6Network
    else:
        raise ValueError('unknown IP version')

    ip_bits = first._max_prefixlen
    first_int = first._ip
    last_int = last._ip
    while first_int <= last_int:
        nbits = min(_count_righthand_zero_bits(first_int, ip_bits),
                    (last_int - first_int + 1).bit_length() - 1)
        net = ip('%s/%d' % (first, ip_bits - nbits))
        yield net
        first_int += 1 << nbits
        if first_int - 1 == ip._ALL_ONES:
            break
        first = first.__class__(first_int)


def _collapse_addresses_recursive(addresses):
    """Loops through the addresses, collapsing concurrent netblocks.

    Example:

        ip1 = IPv4Network('192.0.2.0/26')
        ip2 = IPv4Network('192.0.2.64/26')
        ip3 = IPv4Network('192.0.2.128/26')
        ip4 = IPv4Network('192.0.2.192/26')

        _collapse_addresses_recursive([ip1, ip2, ip3, ip4]) ->
          [IPv4Network('192.0.2.0/24')]

        This shouldn't be called directly; it is called via
          collapse_addresses([]).

    Args:
        addresses: A list of IPv4Network's or IPv6Network's

    Returns:
        A list of IPv4Network's or IPv6Network's depending on what we were
        passed.

    """
    while True:
        last_addr = None
        ret_array = []
        optimized = False

        for cur_addr in addresses:
            if not ret_array:
                last_addr = cur_addr
                ret_array.append(cur_addr)
            elif (cur_addr.network_address >= last_addr.network_address and
                cur_addr.broadcast_address <= last_addr.broadcast_address):
                optimized = True
            elif cur_addr == list(last_addr.supernet().subnets())[1]:
                ret_array[-1] = last_addr = last_addr.supernet()
                optimized = True
            else:
                last_addr = cur_addr
                ret_array.append(cur_addr)

        addresses = ret_array
        if not optimized:
            return addresses


def collapse_addresses(addresses):
    """Collapse a list of IP objects.

    Example:
        collapse_addresses([IPv4Network('192.0.2.0/25'),
                            IPv4Network('192.0.2.128/25')]) ->
                           [IPv4Network('192.0.2.0/24')]

    Args:
        addresses: An iterator of IPv4Network or IPv6Network objects.

    Returns:
        An iterator of the collapsed IPv(4|6)Network objects.

    Raises:
        TypeError: If passed a list of mixed version objects.

    """
    i = 0
    addrs = []
    ips = []
    nets = []

    # split IP addresses and networks
    for ip in addresses:
        if isinstance(ip, _BaseAddress):
            if ips and ips[-1]._version != ip._version:
                raise TypeError("%s and %s are not of the same version" % (
                                 ip, ips[-1]))
            ips.append(ip)
        elif ip._prefixlen == ip._max_prefixlen:
            if ips and ips[-1]._version != ip._version:
                raise TypeError("%s and %s are not of the same version" % (
                                 ip, ips[-1]))
            try:
                ips.append(ip.ip)
            except AttributeError:
                ips.append(ip.network_address)
        else:
            if nets and nets[-1]._version != ip._version:
                raise TypeError("%s and %s are not of the same version" % (
                                 ip, nets[-1]))
            nets.append(ip)

    # sort and dedup
    ips = sorted(set(ips))
    nets = sorted(set(nets))

    while i < len(ips):
        (first, last) = _find_address_range(ips[i:])
        i = ips.index(last) + 1
        addrs.extend(summarize_address_range(first, last))

    return iter(_collapse_addresses_recursive(sorted(
        addrs + nets, key=_BaseNetwork._get_networks_key)))


def get_mixed_type_key(obj):
    """Return a key suitable for sorting between networks and addresses.

    Address and Network objects are not sortable by default; they're
    fundamentally different so the expression

        IPv4Address('192.0.2.0') <= IPv4Network('192.0.2.0/24')

    doesn't make any sense.  There are some times however, where you may wish
    to have ipaddress sort these for you anyway. If you need to do this, you
    can use this function as the key= argument to sorted().

    Args:
      obj: either a Network or Address object.
    Returns:
      appropriate key.

    """
    if isinstance(obj, _BaseNetwork):
        return obj._get_networks_key()
    elif isinstance(obj, _BaseAddress):
        return obj._get_address_key()
    return NotImplemented


class _TotalOrderingMixin:
    # Helper that derives the other comparison operations from
    # __lt__ and __eq__
    # We avoid functools.total_ordering because it doesn't handle
    # NotImplemented correctly yet (http://bugs.python.org/issue10042)
    def __eq__(self, other):
        raise NotImplementedError
    def __ne__(self, other):
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal
    def __lt__(self, other):
        raise NotImplementedError
    def __le__(self, other):
        less = self.__lt__(other)
        if less is NotImplemented or not less:
            return self.__eq__(other)
        return less
    def __gt__(self, other):
        less = self.__lt__(other)
        if less is NotImplemented:
            return NotImplemented
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not (less or equal)
    def __ge__(self, other):
        less = self.__lt__(other)
        if less is NotImplemented:
            return NotImplemented
        return not less

class _IPAddressBase(_TotalOrderingMixin):

    """The mother class."""

    @property
    def exploded(self):
        """Return the longhand version of the IP address as a string."""
        return self._explode_shorthand_ip_string()

    @property
    def compressed(self):
        """Return the shorthand version of the IP address as a string."""
        return str(self)

    @property
    def version(self):
        msg = '%200s has no version specified' % (type(self),)
        raise NotImplementedError(msg)

    def _check_int_address(self, address):
        if address < 0:
            msg = "%d (< 0) is not permitted as an IPv%d address"
            raise AddressValueError(msg % (address, self._version))
        if address > self._ALL_ONES:
            msg = "%d (>= 2**%d) is not permitted as an IPv%d address"
            raise AddressValueError(msg % (address, self._max_prefixlen,
                                           self._version))

    def _check_packed_address(self, address, expected_len):
        address_len = len(address)
        if address_len != expected_len:
            msg = "%r (len %d != %d) is not permitted as an IPv%d address"
            raise AddressValueError(msg % (address, address_len,
                                           expected_len, self._version))

    def _ip_int_from_prefix(self, prefixlen=None):
        """Turn the prefix length netmask into a int for comparison.

        Args:
            prefixlen: An integer, the prefix length.

        Returns:
            An integer.

        """
        if prefixlen is None:
            prefixlen = self._prefixlen
        return self._ALL_ONES ^ (self._ALL_ONES >> prefixlen)

    def _prefix_from_ip_int(self, ip_int, mask=32):
        """Return prefix length from the decimal netmask.

        Args:
            ip_int: An integer, the IP address.
            mask: The netmask.  Defaults to 32.

        Returns:
            An integer, the prefix length.

        """
        return mask - _count_righthand_zero_bits(ip_int, mask)

    def _ip_string_from_prefix(self, prefixlen=None):
        """Turn a prefix length into a dotted decimal string.

        Args:
            prefixlen: An integer, the netmask prefix length.

        Returns:
            A string, the dotted decimal netmask string.

        """
        if not prefixlen:
            prefixlen = self._prefixlen
        return self._string_from_ip_int(self._ip_int_from_prefix(prefixlen))


class _BaseAddress(_IPAddressBase):

    """A generic IP object.

    This IP class contains the version independent methods which are
    used by single IP addresses.

    """

    def __init__(self, address):
        if (not isinstance(address, bytes)
            and '/' in str(address)):
            raise AddressValueError("Unexpected '/' in %r" % address)

    def __int__(self):
        return self._ip

    def __eq__(self, other):
        try:
            return (self._ip == other._ip
                    and self._version == other._version)
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (
                             self, other))
        if not isinstance(other, _BaseAddress):
            raise TypeError('%s and %s are not of the same type' % (
                             self, other))
        if self._ip != other._ip:
            return self._ip < other._ip
        return False

    # Shorthand for Integer addition and subtraction. This is not
    # meant to ever support addition/subtraction of addresses.
    def __add__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return self.__class__(int(self) + other)

    def __sub__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return self.__class__(int(self) - other)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __str__(self):
        return str(self._string_from_ip_int(self._ip))

    def __hash__(self):
        return hash(hex(int(self._ip)))

    def _get_address_key(self):
        return (self._version, self)


class _BaseNetwork(_IPAddressBase):

    """A generic IP network object.

    This IP class contains the version independent methods which are
    used by networks.

    """
    def __init__(self, address):
        self._cache = {}

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __str__(self):
        return '%s/%d' % (self.network_address, self.prefixlen)

    def hosts(self):
        """Generate Iterator over usable hosts in a network.

        This is like __iter__ except it doesn't return the network
        or broadcast addresses.

        """
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        for x in range(network + 1, broadcast):
            yield self._address_class(x)

    def __iter__(self):
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        for x in range(network, broadcast + 1):
            yield self._address_class(x)

    def __getitem__(self, n):
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        if n >= 0:
            if network + n > broadcast:
                raise IndexError
            return self._address_class(network + n)
        else:
            n += 1
            if broadcast + n < network:
                raise IndexError
            return self._address_class(broadcast + n)

    def __lt__(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (
                             self, other))
        if not isinstance(other, _BaseNetwork):
            raise TypeError('%s and %s are not of the same type' % (
                             self, other))
        if self.network_address != other.network_address:
            return self.network_address < other.network_address
        if self.netmask != other.netmask:
            return self.netmask < other.netmask
        return False

    def __eq__(self, other):
        try:
            return (self._version == other._version and
                    self.network_address == other.network_address and
                    int(self.netmask) == int(other.netmask))
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return hash(int(self.network_address) ^ int(self.netmask))

    def __contains__(self, other):
        # always false if one is v4 and the other is v6.
        if self._version != other._version:
            return False
        # dealing with another network.
        if isinstance(other, _BaseNetwork):
            return False
        # dealing with another address
        else:
            # address
            return (int(self.network_address) <= int(other._ip) <=
                    int(self.broadcast_address))

    def overlaps(self, other):
        """Tell if self is partly contained in other."""
        return self.network_address in other or (
            self.broadcast_address in other or (
                other.network_address in self or (
                    other.broadcast_address in self)))

    @property
    def broadcast_address(self):
        x = self._cache.get('broadcast_address')
        if x is None:
            x = self._address_class(int(self.network_address) |
                                    int(self.hostmask))
            self._cache['broadcast_address'] = x
        return x

    @property
    def hostmask(self):
        x = self._cache.get('hostmask')
        if x is None:
            x = self._address_class(int(self.netmask) ^ self._ALL_ONES)
            self._cache['hostmask'] = x
        return x

    @property
    def with_prefixlen(self):
        return '%s/%d' % (self.network_address, self._prefixlen)

    @property
    def with_netmask(self):
        return '%s/%s' % (self.network_address, self.netmask)

    @property
    def with_hostmask(self):
        return '%s/%s' % (self.network_address, self.hostmask)

    @property
    def num_addresses(self):
        """Number of hosts in the current subnet."""
        return int(self.broadcast_address) - int(self.network_address) + 1

    @property
    def _address_class(self):
        # Returning bare address objects (rather than interfaces) allows for
        # more consistent behaviour across the network address, broadcast
        # address and individual host addresses.
        msg = '%200s has no associated address class' % (type(self),)
        raise NotImplementedError(msg)

    @property
    def prefixlen(self):
        return self._prefixlen

    def address_exclude(self, other):
        """Remove an address from a larger block.

        For example:

            addr1 = ip_network('192.0.2.0/28')
            addr2 = ip_network('192.0.2.1/32')
            addr1.address_exclude(addr2) =
                [IPv4Network('192.0.2.0/32'), IPv4Network('192.0.2.2/31'),
                IPv4Network('192.0.2.4/30'), IPv4Network('192.0.2.8/29')]

        or IPv6:

            addr1 = ip_network('2001:db8::1/32')
            addr2 = ip_network('2001:db8::1/128')
            addr1.address_exclude(addr2) =
                [ip_network('2001:db8::1/128'),
                ip_network('2001:db8::2/127'),
                ip_network('2001:db8::4/126'),
                ip_network('2001:db8::8/125'),
                ...
                ip_network('2001:db8:8000::/33')]

        Args:
            other: An IPv4Network or IPv6Network object of the same type.

        Returns:
            An iterator of the the IPv(4|6)Network objects which is self
            minus other.

        Raises:
            TypeError: If self and other are of difffering address
              versions, or if other is not a network object.
            ValueError: If other is not completely contained by self.

        """
        if not self._version == other._version:
            raise TypeError("%s and %s are not of the same version" % (
                             self, other))

        if not isinstance(other, _BaseNetwork):
            raise TypeError("%s is not a network object" % other)

        if not (other.network_address >= self.network_address and
                other.broadcast_address <= self.broadcast_address):
            raise ValueError('%s not contained in %s' % (other, self))
        if other == self:
            raise StopIteration

        # Make sure we're comparing the network of other.
        other = other.__class__('%s/%s' % (other.network_address,
                                           other.prefixlen))

        s1, s2 = self.subnets()
        while s1 != other and s2 != other:
            if (other.network_address >= s1.network_address and
                other.broadcast_address <= s1.broadcast_address):
                yield s2
                s1, s2 = s1.subnets()
            elif (other.network_address >= s2.network_address and
                  other.broadcast_address <= s2.broadcast_address):
                yield s1
                s1, s2 = s2.subnets()
            else:
                # If we got here, there's a bug somewhere.
                raise AssertionError('Error performing exclusion: '
                                     's1: %s s2: %s other: %s' %
                                     (s1, s2, other))
        if s1 == other:
            yield s2
        elif s2 == other:
            yield s1
        else:
            # If we got here, there's a bug somewhere.
            raise AssertionError('Error performing exclusion: '
                                 's1: %s s2: %s other: %s' %
                                 (s1, s2, other))

    def compare_networks(self, other):
        """Compare two IP objects.

        This is only concerned about the comparison of the integer
        representation of the network addresses.  This means that the
        host bits aren't considered at all in this method.  If you want
        to compare host bits, you can easily enough do a
        'HostA._ip < HostB._ip'

        Args:
            other: An IP object.

        Returns:
            If the IP versions of self and other are the same, returns:

            -1 if self < other:
              eg: IPv4Network('192.0.2.0/25') < IPv4Network('192.0.2.128/25')
              IPv6Network('2001:db8::1000/124') <
                  IPv6Network('2001:db8::2000/124')
            0 if self == other
              eg: IPv4Network('192.0.2.0/24') == IPv4Network('192.0.2.0/24')
              IPv6Network('2001:db8::1000/124') ==
                  IPv6Network('2001:db8::1000/124')
            1 if self > other
              eg: IPv4Network('192.0.2.128/25') > IPv4Network('192.0.2.0/25')
                  IPv6Network('2001:db8::2000/124') >
                      IPv6Network('2001:db8::1000/124')

          Raises:
              TypeError if the IP versions are different.

        """
        # does this need to raise a ValueError?
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same type' % (
                             self, other))
        # self._version == other._version below here:
        if self.network_address < other.network_address:
            return -1
        if self.network_address > other.network_address:
            return 1
        # self.network_address == other.network_address below here:
        if self.netmask < other.netmask:
            return -1
        if self.netmask > other.netmask:
            return 1
        return 0

    def _get_networks_key(self):
        """Network-only key function.

        Returns an object that identifies this address' network and
        netmask. This function is a suitable "key" argument for sorted()
        and list.sort().

        """
        return (self._version, self.network_address, self.netmask)

    def subnets(self, prefixlen_diff=1, new_prefix=None):
        """The subnets which join to make the current subnet.

        In the case that self contains only one IP
        (self._prefixlen == 32 for IPv4 or self._prefixlen == 128
        for IPv6), yield an iterator with just ourself.

        Args:
            prefixlen_diff: An integer, the amount the prefix length
              should be increased by. This should not be set if
              new_prefix is also set.
            new_prefix: The desired new prefix length. This must be a
              larger number (smaller prefix) than the existing prefix.
              This should not be set if prefixlen_diff is also set.

        Returns:
            An iterator of IPv(4|6) objects.

        Raises:
            ValueError: The prefixlen_diff is too small or too large.
                OR
            prefixlen_diff and new_prefix are both set or new_prefix
              is a smaller number than the current prefix (smaller
              number means a larger network)

        """
        if self._prefixlen == self._max_prefixlen:
            yield self
            return

        if new_prefix is not None:
            if new_prefix < self._prefixlen:
                raise ValueError('new prefix must be longer')
            if prefixlen_diff != 1:
                raise ValueError('cannot set prefixlen_diff and new_prefix')
            prefixlen_diff = new_prefix - self._prefixlen

        if prefixlen_diff < 0:
            raise ValueError('prefix length diff must be > 0')
        new_prefixlen = self._prefixlen + prefixlen_diff

        if not self._is_valid_netmask(str(new_prefixlen)):
            raise ValueError(
                'prefix length diff %d is invalid for netblock %s' % (
                    new_prefixlen, self))

        first = self.__class__('%s/%s' %
                                 (self.network_address,
                                  self._prefixlen + prefixlen_diff))

        yield first
        current = first
        while True:
            broadcast = current.broadcast_address
            if broadcast == self.broadcast_address:
                return
            new_addr = self._address_class(int(broadcast) + 1)
            current = self.__class__('%s/%s' % (new_addr,
                                                new_prefixlen))

            yield current

    def supernet(self, prefixlen_diff=1, new_prefix=None):
        """The supernet containing the current network.

        Args:
            prefixlen_diff: An integer, the amount the prefix length of
              the network should be decreased by.  For example, given a
              /24 network and a prefixlen_diff of 3, a supernet with a
              /21 netmask is returned.

        Returns:
            An IPv4 network object.

        Raises:
            ValueError: If self.prefixlen - prefixlen_diff < 0. I.e., you have
              a negative prefix length.
                OR
            If prefixlen_diff and new_prefix are both set or new_prefix is a
              larger number than the current prefix (larger number means a
              smaller network)

        """
        if self._prefixlen == 0:
            return self

        if new_prefix is not None:
            if new_prefix > self._prefixlen:
                raise ValueError('new prefix must be shorter')
            if prefixlen_diff != 1:
                raise ValueError('cannot set prefixlen_diff and new_prefix')
            prefixlen_diff = self._prefixlen - new_prefix

        if self.prefixlen - prefixlen_diff < 0:
            raise ValueError(
                'current prefixlen is %d, cannot have a prefixlen_diff of %d' %
                (self.prefixlen, prefixlen_diff))
        # TODO (pmoody): optimize this.
        t = self.__class__('%s/%d' % (self.network_address,
                                      self.prefixlen - prefixlen_diff),
                                     strict=False)
        return t.__class__('%s/%d' % (t.network_address, t.prefixlen))

    @property
    def is_multicast(self):
        """Test if the address is reserved for multicast use.

        Returns:
            A boolean, True if the address is a multicast address.
            See RFC 2373 2.7 for details.

        """
        return (self.network_address.is_multicast and
                self.broadcast_address.is_multicast)

    @property
    def is_reserved(self):
        """Test if the address is otherwise IETF reserved.

        Returns:
            A boolean, True if the address is within one of the
            reserved IPv6 Network ranges.

        """
        return (self.network_address.is_reserved and
                self.broadcast_address.is_reserved)

    @property
    def is_link_local(self):
        """Test if the address is reserved for link-local.

        Returns:
            A boolean, True if the address is reserved per RFC 4291.

        """
        return (self.network_address.is_link_local and
                self.broadcast_address.is_link_local)

    @property
    def is_private(self):
        """Test if this address is allocated for private networks.

        Returns:
            A boolean, True if the address is reserved per RFC 4193.

        """
        return (self.network_address.is_private and
                self.broadcast_address.is_private)

    @property
    def is_unspecified(self):
        """Test if the address is unspecified.

        Returns:
            A boolean, True if this is the unspecified address as defined in
            RFC 2373 2.5.2.

        """
        return (self.network_address.is_unspecified and
                self.broadcast_address.is_unspecified)

    @property
    def is_loopback(self):
        """Test if the address is a loopback address.

        Returns:
            A boolean, True if the address is a loopback address as defined in
            RFC 2373 2.5.3.

        """
        return (self.network_address.is_loopback and
                self.broadcast_address.is_loopback)


class _BaseV4:

    """Base IPv4 object.

    The following methods are used by IPv4 objects in both single IP
    addresses and networks.

    """

    # Equivalent to 255.255.255.255 or 32 bits of 1's.
    _ALL_ONES = (2**IPV4LENGTH) - 1
    _DECIMAL_DIGITS = frozenset('0123456789')

    # the valid octets for host and netmasks. only useful for IPv4.
    _valid_mask_octets = frozenset((255, 254, 252, 248, 240, 224, 192, 128, 0))

    def __init__(self, address):
        self._version = 4
        self._max_prefixlen = IPV4LENGTH

    def _explode_shorthand_ip_string(self):
        return str(self)

    def _ip_int_from_string(self, ip_str):
        """Turn the given IP string into an integer for comparison.

        Args:
            ip_str: A string, the IP ip_str.

        Returns:
            The IP ip_str as an integer.

        Raises:
            AddressValueError: if ip_str isn't a valid IPv4 Address.

        """
        if not ip_str:
            raise AddressValueError('Address cannot be empty')

        octets = ip_str.split('.')
        if len(octets) != 4:
            raise AddressValueError("Expected 4 octets in %r" % ip_str)

        try:
            return int.from_bytes(map(self._parse_octet, octets), 'big')
        except ValueError as exc:
            raise AddressValueError("%s in %r" % (exc, ip_str))

    def _parse_octet(self, octet_str):
        """Convert a decimal octet into an integer.

        Args:
            octet_str: A string, the number to parse.

        Returns:
            The octet as an integer.

        Raises:
            ValueError: if the octet isn't strictly a decimal from [0..255].

        """
        if not octet_str:
            raise ValueError("Empty octet not permitted")
        # Whitelist the characters, since int() allows a lot of bizarre stuff.
        if not self._DECIMAL_DIGITS.issuperset(octet_str):
            msg = "Only decimal digits permitted in %r"
            raise ValueError(msg % octet_str)
        # We do the length check second, since the invalid character error
        # is likely to be more informative for the user
        if len(octet_str) > 3:
            msg = "At most 3 characters permitted in %r"
            raise ValueError(msg % octet_str)
        # Convert to integer (we know digits are legal)
        octet_int = int(octet_str, 10)
        # Any octets that look like they *might* be written in octal,
        # and which don't look exactly the same in both octal and
        # decimal are rejected as ambiguous
        if octet_int > 7 and octet_str[0] == '0':
            msg = "Ambiguous (octal/decimal) value in %r not permitted"
            raise ValueError(msg % octet_str)
        if octet_int > 255:
            raise ValueError("Octet %d (> 255) not permitted" % octet_int)
        return octet_int

    def _string_from_ip_int(self, ip_int):
        """Turns a 32-bit integer into dotted decimal notation.

        Args:
            ip_int: An integer, the IP address.

        Returns:
            The IP address as a string in dotted decimal notation.

        """
        return '.'.join(map(str, ip_int.to_bytes(4, 'big')))

    def _is_valid_netmask(self, netmask):
        """Verify that the netmask is valid.

        Args:
            netmask: A string, either a prefix or dotted decimal
              netmask.

        Returns:
            A boolean, True if the prefix represents a valid IPv4
            netmask.

        """
        mask = netmask.split('.')
        if len(mask) == 4:
            try:
                for x in mask:
                    if int(x) not in self._valid_mask_octets:
                        return False
            except ValueError:
                # Found something that isn't an integer or isn't valid
                return False
            for idx, y in enumerate(mask):
                if idx > 0 and y > mask[idx - 1]:
                    return False
            return True
        try:
            netmask = int(netmask)
        except ValueError:
            return False
        return 0 <= netmask <= self._max_prefixlen

    def _is_hostmask(self, ip_str):
        """Test if the IP string is a hostmask (rather than a netmask).

        Args:
            ip_str: A string, the potential hostmask.

        Returns:
            A boolean, True if the IP string is a hostmask.

        """
        bits = ip_str.split('.')
        try:
            parts = [x for x in map(int, bits) if x in self._valid_mask_octets]
        except ValueError:
            return False
        if len(parts) != len(bits):
            return False
        if parts[0] < parts[-1]:
            return True
        return False

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def version(self):
        return self._version


class IPv4Address(_BaseV4, _BaseAddress):

    """Represent and manipulate single IPv4 Addresses."""

    def __init__(self, address):

        """
        Args:
            address: A string or integer representing the IP

              Additionally, an integer can be passed, so
              IPv4Address('192.0.2.1') == IPv4Address(3221225985).
              or, more generally
              IPv4Address(int(IPv4Address('192.0.2.1'))) ==
                IPv4Address('192.0.2.1')

        Raises:
            AddressValueError: If ipaddress isn't a valid IPv4 address.

        """
        _BaseAddress.__init__(self, address)
        _BaseV4.__init__(self, address)

        # Efficient constructor from integer.
        if isinstance(address, int):
            self._check_int_address(address)
            self._ip = address
            return

        # Constructing from a packed address
        if isinstance(address, bytes):
            self._check_packed_address(address, 4)
            self._ip = int.from_bytes(address, 'big')
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP string.
        addr_str = str(address)
        self._ip = self._ip_int_from_string(addr_str)

    @property
    def packed(self):
        """The binary representation of this address."""
        return v4_int_to_packed(self._ip)

    @property
    def is_reserved(self):
        """Test if the address is otherwise IETF reserved.

         Returns:
             A boolean, True if the address is within the
             reserved IPv4 Network range.

        """
        reserved_network = IPv4Network('240.0.0.0/4')
        return self in reserved_network

    @property
    def is_private(self):
        """Test if this address is allocated for private networks.

        Returns:
            A boolean, True if the address is reserved per RFC 1918.

        """
        private_10 = IPv4Network('10.0.0.0/8')
        private_172 = IPv4Network('172.16.0.0/12')
        private_192 = IPv4Network('192.168.0.0/16')
        return (self in private_10 or
                self in private_172 or
                self in private_192)

    @property
    def is_multicast(self):
        """Test if the address is reserved for multicast use.

        Returns:
            A boolean, True if the address is multicast.
            See RFC 3171 for details.

        """
        multicast_network = IPv4Network('224.0.0.0/4')
        return self in multicast_network

    @property
    def is_unspecified(self):
        """Test if the address is unspecified.

        Returns:
            A boolean, True if this is the unspecified address as defined in
            RFC 5735 3.

        """
        unspecified_address = IPv4Address('0.0.0.0')
        return self == unspecified_address

    @property
    def is_loopback(self):
        """Test if the address is a loopback address.

        Returns:
            A boolean, True if the address is a loopback per RFC 3330.

        """
        loopback_network = IPv4Network('127.0.0.0/8')
        return self in loopback_network

    @property
    def is_link_local(self):
        """Test if the address is reserved for link-local.

        Returns:
            A boolean, True if the address is link-local per RFC 3927.

        """
        linklocal_network = IPv4Network('169.254.0.0/16')
        return self in linklocal_network


class IPv4Interface(IPv4Address):

    def __init__(self, address):
        if isinstance(address, (bytes, int)):
            IPv4Address.__init__(self, address)
            self.network = IPv4Network(self._ip)
            self._prefixlen = self._max_prefixlen
            return

        addr = _split_optional_netmask(address)
        IPv4Address.__init__(self, addr[0])

        self.network = IPv4Network(address, strict=False)
        self._prefixlen = self.network._prefixlen

        self.netmask = self.network.netmask
        self.hostmask = self.network.hostmask

    def __str__(self):
        return '%s/%d' % (self._string_from_ip_int(self._ip),
                          self.network.prefixlen)

    def __eq__(self, other):
        address_equal = IPv4Address.__eq__(self, other)
        if not address_equal or address_equal is NotImplemented:
            return address_equal
        try:
            return self.network == other.network
        except AttributeError:
            # An interface with an associated network is NOT the
            # same as an unassociated address. That's why the hash
            # takes the extra info into account.
            return False

    def __lt__(self, other):
        address_less = IPv4Address.__lt__(self, other)
        if address_less is NotImplemented:
            return NotImplemented
        try:
            return self.network < other.network
        except AttributeError:
            # We *do* allow addresses and interfaces to be sorted. The
            # unassociated address is considered less than all interfaces.
            return False

    def __hash__(self):
        return self._ip ^ self._prefixlen ^ int(self.network.network_address)

    @property
    def ip(self):
        return IPv4Address(self._ip)

    @property
    def with_prefixlen(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip),
                          self._prefixlen)

    @property
    def with_netmask(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip),
                          self.netmask)

    @property
    def with_hostmask(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip),
                          self.hostmask)


class IPv4Network(_BaseV4, _BaseNetwork):

    """This class represents and manipulates 32-bit IPv4 network + addresses..

    Attributes: [examples for IPv4Network('192.0.2.0/27')]
        .network_address: IPv4Address('192.0.2.0')
        .hostmask: IPv4Address('0.0.0.31')
        .broadcast_address: IPv4Address('192.0.2.32')
        .netmask: IPv4Address('255.255.255.224')
        .prefixlen: 27

    """
    # Class to use when creating address objects
    _address_class = IPv4Address

    def __init__(self, address, strict=True):

        """Instantiate a new IPv4 network object.

        Args:
            address: A string or integer representing the IP [& network].
              '192.0.2.0/24'
              '192.0.2.0/255.255.255.0'
              '192.0.0.2/0.0.0.255'
              are all functionally the same in IPv4. Similarly,
              '192.0.2.1'
              '192.0.2.1/255.255.255.255'
              '192.0.2.1/32'
              are also functionaly equivalent. That is to say, failing to
              provide a subnetmask will create an object with a mask of /32.

              If the mask (portion after the / in the argument) is given in
              dotted quad form, it is treated as a netmask if it starts with a
              non-zero field (e.g. /255.0.0.0 == /8) and as a hostmask if it
              starts with a zero field (e.g. 0.255.255.255 == /8), with the
              single exception of an all-zero mask which is treated as a
              netmask == /0. If no mask is given, a default of /32 is used.

              Additionally, an integer can be passed, so
              IPv4Network('192.0.2.1') == IPv4Network(3221225985)
              or, more generally
              IPv4Interface(int(IPv4Interface('192.0.2.1'))) ==
                IPv4Interface('192.0.2.1')

        Raises:
            AddressValueError: If ipaddress isn't a valid IPv4 address.
            NetmaskValueError: If the netmask isn't valid for
              an IPv4 address.
            ValueError: If strict is True and a network address is not
              supplied.

        """

        _BaseV4.__init__(self, address)
        _BaseNetwork.__init__(self, address)

        # Constructing from a packed address
        if isinstance(address, bytes):
            self.network_address = IPv4Address(address)
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv4Address(self._ALL_ONES)
            #fixme: address/network test here
            return

        # Efficient constructor from integer.
        if isinstance(address, int):
            self.network_address = IPv4Address(address)
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv4Address(self._ALL_ONES)
            #fixme: address/network test here.
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP prefix string.
        addr = _split_optional_netmask(address)
        self.network_address = IPv4Address(self._ip_int_from_string(addr[0]))

        if len(addr) == 2:
            mask = addr[1].split('.')

            if len(mask) == 4:
                # We have dotted decimal netmask.
                if self._is_valid_netmask(addr[1]):
                    self.netmask = IPv4Address(self._ip_int_from_string(
                            addr[1]))
                elif self._is_hostmask(addr[1]):
                    self.netmask = IPv4Address(
                        self._ip_int_from_string(addr[1]) ^ self._ALL_ONES)
                else:
                    raise NetmaskValueError('%r is not a valid netmask'
                                                     % addr[1])

                self._prefixlen = self._prefix_from_ip_int(int(self.netmask))
            else:
                # We have a netmask in prefix length form.
                if not self._is_valid_netmask(addr[1]):
                    raise NetmaskValueError('%r is not a valid netmask'
                                                     % addr[1])
                self._prefixlen = int(addr[1])
                self.netmask = IPv4Address(self._ip_int_from_prefix(
                    self._prefixlen))
        else:
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv4Address(self._ip_int_from_prefix(
                self._prefixlen))

        if strict:
            if (IPv4Address(int(self.network_address) & int(self.netmask)) !=
                self.network_address):
                raise ValueError('%s has host bits set' % self)
        self.network_address = IPv4Address(int(self.network_address) &
                                           int(self.netmask))

        if self._prefixlen == (self._max_prefixlen - 1):
            self.hosts = self.__iter__


class _BaseV6:

    """Base IPv6 object.

    The following methods are used by IPv6 objects in both single IP
    addresses and networks.

    """

    _ALL_ONES = (2**IPV6LENGTH) - 1
    _HEXTET_COUNT = 8
    _HEX_DIGITS = frozenset('0123456789ABCDEFabcdef')

    def __init__(self, address):
        self._version = 6
        self._max_prefixlen = IPV6LENGTH

    def _ip_int_from_string(self, ip_str):
        """Turn an IPv6 ip_str into an integer.

        Args:
            ip_str: A string, the IPv6 ip_str.

        Returns:
            An int, the IPv6 address

        Raises:
            AddressValueError: if ip_str isn't a valid IPv6 Address.

        """
        if not ip_str:
            raise AddressValueError('Address cannot be empty')

        parts = ip_str.split(':')

        # An IPv6 address needs at least 2 colons (3 parts).
        _min_parts = 3
        if len(parts) < _min_parts:
            msg = "At least %d parts expected in %r" % (_min_parts, ip_str)
            raise AddressValueError(msg)

        # If the address has an IPv4-style suffix, convert it to hexadecimal.
        if '.' in parts[-1]:
            try:
                ipv4_int = IPv4Address(parts.pop())._ip
            except AddressValueError as exc:
                raise AddressValueError("%s in %r" % (exc, ip_str))
            parts.append('%x' % ((ipv4_int >> 16) & 0xFFFF))
            parts.append('%x' % (ipv4_int & 0xFFFF))

        # An IPv6 address can't have more than 8 colons (9 parts).
        # The extra colon comes from using the "::" notation for a single
        # leading or trailing zero part.
        _max_parts = self._HEXTET_COUNT + 1
        if len(parts) > _max_parts:
            msg = "At most %d colons permitted in %r" % (_max_parts-1, ip_str)
            raise AddressValueError(msg)

        # Disregarding the endpoints, find '::' with nothing in between.
        # This indicates that a run of zeroes has been skipped.
        skip_index = None
        for i in range(1, len(parts) - 1):
            if not parts[i]:
                if skip_index is not None:
                    # Can't have more than one '::'
                    msg = "At most one '::' permitted in %r" % ip_str
                    raise AddressValueError(msg)
                skip_index = i

        # parts_hi is the number of parts to copy from above/before the '::'
        # parts_lo is the number of parts to copy from below/after the '::'
        if skip_index is not None:
            # If we found a '::', then check if it also covers the endpoints.
            parts_hi = skip_index
            parts_lo = len(parts) - skip_index - 1
            if not parts[0]:
                parts_hi -= 1
                if parts_hi:
                    msg = "Leading ':' only permitted as part of '::' in %r"
                    raise AddressValueError(msg % ip_str)  # ^: requires ^::
            if not parts[-1]:
                parts_lo -= 1
                if parts_lo:
                    msg = "Trailing ':' only permitted as part of '::' in %r"
                    raise AddressValueError(msg % ip_str)  # :$ requires ::$
            parts_skipped = self._HEXTET_COUNT - (parts_hi + parts_lo)
            if parts_skipped < 1:
                msg = "Expected at most %d other parts with '::' in %r"
                raise AddressValueError(msg % (self._HEXTET_COUNT-1, ip_str))
        else:
            # Otherwise, allocate the entire address to parts_hi.  The
            # endpoints could still be empty, but _parse_hextet() will check
            # for that.
            if len(parts) != self._HEXTET_COUNT:
                msg = "Exactly %d parts expected without '::' in %r"
                raise AddressValueError(msg % (self._HEXTET_COUNT, ip_str))
            if not parts[0]:
                msg = "Leading ':' only permitted as part of '::' in %r"
                raise AddressValueError(msg % ip_str)  # ^: requires ^::
            if not parts[-1]:
                msg = "Trailing ':' only permitted as part of '::' in %r"
                raise AddressValueError(msg % ip_str)  # :$ requires ::$
            parts_hi = len(parts)
            parts_lo = 0
            parts_skipped = 0

        try:
            # Now, parse the hextets into a 128-bit integer.
            ip_int = 0
            for i in range(parts_hi):
                ip_int <<= 16
                ip_int |= self._parse_hextet(parts[i])
            ip_int <<= 16 * parts_skipped
            for i in range(-parts_lo, 0):
                ip_int <<= 16
                ip_int |= self._parse_hextet(parts[i])
            return ip_int
        except ValueError as exc:
            raise AddressValueError("%s in %r" % (exc, ip_str))

    def _parse_hextet(self, hextet_str):
        """Convert an IPv6 hextet string into an integer.

        Args:
            hextet_str: A string, the number to parse.

        Returns:
            The hextet as an integer.

        Raises:
            ValueError: if the input isn't strictly a hex number from
              [0..FFFF].

        """
        # Whitelist the characters, since int() allows a lot of bizarre stuff.
        if not self._HEX_DIGITS.issuperset(hextet_str):
            raise ValueError("Only hex digits permitted in %r" % hextet_str)
        # We do the length check second, since the invalid character error
        # is likely to be more informative for the user
        if len(hextet_str) > 4:
            msg = "At most 4 characters permitted in %r"
            raise ValueError(msg % hextet_str)
        # Length check means we can skip checking the integer value
        return int(hextet_str, 16)

    def _compress_hextets(self, hextets):
        """Compresses a list of hextets.

        Compresses a list of strings, replacing the longest continuous
        sequence of "0" in the list with "" and adding empty strings at
        the beginning or at the end of the string such that subsequently
        calling ":".join(hextets) will produce the compressed version of
        the IPv6 address.

        Args:
            hextets: A list of strings, the hextets to compress.

        Returns:
            A list of strings.

        """
        best_doublecolon_start = -1
        best_doublecolon_len = 0
        doublecolon_start = -1
        doublecolon_len = 0
        for index, hextet in enumerate(hextets):
            if hextet == '0':
                doublecolon_len += 1
                if doublecolon_start == -1:
                    # Start of a sequence of zeros.
                    doublecolon_start = index
                if doublecolon_len > best_doublecolon_len:
                    # This is the longest sequence of zeros so far.
                    best_doublecolon_len = doublecolon_len
                    best_doublecolon_start = doublecolon_start
            else:
                doublecolon_len = 0
                doublecolon_start = -1

        if best_doublecolon_len > 1:
            best_doublecolon_end = (best_doublecolon_start +
                                    best_doublecolon_len)
            # For zeros at the end of the address.
            if best_doublecolon_end == len(hextets):
                hextets += ['']
            hextets[best_doublecolon_start:best_doublecolon_end] = ['']
            # For zeros at the beginning of the address.
            if best_doublecolon_start == 0:
                hextets = [''] + hextets

        return hextets

    def _string_from_ip_int(self, ip_int=None):
        """Turns a 128-bit integer into hexadecimal notation.

        Args:
            ip_int: An integer, the IP address.

        Returns:
            A string, the hexadecimal representation of the address.

        Raises:
            ValueError: The address is bigger than 128 bits of all ones.

        """
        if ip_int is None:
            ip_int = int(self._ip)

        if ip_int > self._ALL_ONES:
            raise ValueError('IPv6 address is too large')

        hex_str = '%032x' % ip_int
        hextets = ['%x' % int(hex_str[x:x+4], 16) for x in range(0, 32, 4)]

        hextets = self._compress_hextets(hextets)
        return ':'.join(hextets)

    def _explode_shorthand_ip_string(self):
        """Expand a shortened IPv6 address.

        Args:
            ip_str: A string, the IPv6 address.

        Returns:
            A string, the expanded IPv6 address.

        """
        if isinstance(self, IPv6Network):
            ip_str = str(self.network_address)
        elif isinstance(self, IPv6Interface):
            ip_str = str(self.ip)
        else:
            ip_str = str(self)

        ip_int = self._ip_int_from_string(ip_str)
        hex_str = '%032x' % ip_int
        parts = [hex_str[x:x+4] for x in range(0, 32, 4)]
        if isinstance(self, (_BaseNetwork, IPv6Interface)):
            return '%s/%d' % (':'.join(parts), self._prefixlen)
        return ':'.join(parts)

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def version(self):
        return self._version


class IPv6Address(_BaseV6, _BaseAddress):

    """Represent and manipulate single IPv6 Addresses."""

    def __init__(self, address):
        """Instantiate a new IPv6 address object.

        Args:
            address: A string or integer representing the IP

              Additionally, an integer can be passed, so
              IPv6Address('2001:db8::') ==
                IPv6Address(42540766411282592856903984951653826560)
              or, more generally
              IPv6Address(int(IPv6Address('2001:db8::'))) ==
                IPv6Address('2001:db8::')

        Raises:
            AddressValueError: If address isn't a valid IPv6 address.

        """
        _BaseAddress.__init__(self, address)
        _BaseV6.__init__(self, address)

        # Efficient constructor from integer.
        if isinstance(address, int):
            self._check_int_address(address)
            self._ip = address
            return

        # Constructing from a packed address
        if isinstance(address, bytes):
            self._check_packed_address(address, 16)
            self._ip = int.from_bytes(address, 'big')
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP string.
        addr_str = str(address)
        self._ip = self._ip_int_from_string(addr_str)

    @property
    def packed(self):
        """The binary representation of this address."""
        return v6_int_to_packed(self._ip)

    @property
    def is_multicast(self):
        """Test if the address is reserved for multicast use.

        Returns:
            A boolean, True if the address is a multicast address.
            See RFC 2373 2.7 for details.

        """
        multicast_network = IPv6Network('ff00::/8')
        return self in multicast_network

    @property
    def is_reserved(self):
        """Test if the address is otherwise IETF reserved.

        Returns:
            A boolean, True if the address is within one of the
            reserved IPv6 Network ranges.

        """
        reserved_networks = [IPv6Network('::/8'), IPv6Network('100::/8'),
                             IPv6Network('200::/7'), IPv6Network('400::/6'),
                             IPv6Network('800::/5'), IPv6Network('1000::/4'),
                             IPv6Network('4000::/3'), IPv6Network('6000::/3'),
                             IPv6Network('8000::/3'), IPv6Network('A000::/3'),
                             IPv6Network('C000::/3'), IPv6Network('E000::/4'),
                             IPv6Network('F000::/5'), IPv6Network('F800::/6'),
                             IPv6Network('FE00::/9')]

        return any(self in x for x in reserved_networks)

    @property
    def is_link_local(self):
        """Test if the address is reserved for link-local.

        Returns:
            A boolean, True if the address is reserved per RFC 4291.

        """
        linklocal_network = IPv6Network('fe80::/10')
        return self in linklocal_network

    @property
    def is_site_local(self):
        """Test if the address is reserved for site-local.

        Note that the site-local address space has been deprecated by RFC 3879.
        Use is_private to test if this address is in the space of unique local
        addresses as defined by RFC 4193.

        Returns:
            A boolean, True if the address is reserved per RFC 3513 2.5.6.

        """
        sitelocal_network = IPv6Network('fec0::/10')
        return self in sitelocal_network

    @property
    def is_private(self):
        """Test if this address is allocated for private networks.

        Returns:
            A boolean, True if the address is reserved per RFC 4193.

        """
        private_network = IPv6Network('fc00::/7')
        return self in private_network

    @property
    def is_unspecified(self):
        """Test if the address is unspecified.

        Returns:
            A boolean, True if this is the unspecified address as defined in
            RFC 2373 2.5.2.

        """
        return self._ip == 0

    @property
    def is_loopback(self):
        """Test if the address is a loopback address.

        Returns:
            A boolean, True if the address is a loopback address as defined in
            RFC 2373 2.5.3.

        """
        return self._ip == 1

    @property
    def ipv4_mapped(self):
        """Return the IPv4 mapped address.

        Returns:
            If the IPv6 address is a v4 mapped address, return the
            IPv4 mapped address. Return None otherwise.

        """
        if (self._ip >> 32) != 0xFFFF:
            return None
        return IPv4Address(self._ip & 0xFFFFFFFF)

    @property
    def teredo(self):
        """Tuple of embedded teredo IPs.

        Returns:
            Tuple of the (server, client) IPs or None if the address
            doesn't appear to be a teredo address (doesn't start with
            2001::/32)

        """
        if (self._ip >> 96) != 0x20010000:
            return None
        return (IPv4Address((self._ip >> 64) & 0xFFFFFFFF),
                IPv4Address(~self._ip & 0xFFFFFFFF))

    @property
    def sixtofour(self):
        """Return the IPv4 6to4 embedded address.

        Returns:
            The IPv4 6to4-embedded address if present or None if the
            address doesn't appear to contain a 6to4 embedded address.

        """
        if (self._ip >> 112) != 0x2002:
            return None
        return IPv4Address((self._ip >> 80) & 0xFFFFFFFF)


class IPv6Interface(IPv6Address):

    def __init__(self, address):
        if isinstance(address, (bytes, int)):
            IPv6Address.__init__(self, address)
            self.network = IPv6Network(self._ip)
            self._prefixlen = self._max_prefixlen
            return

        addr = _split_optional_netmask(address)
        IPv6Address.__init__(self, addr[0])
        self.network = IPv6Network(address, strict=False)
        self.netmask = self.network.netmask
        self._prefixlen = self.network._prefixlen
        self.hostmask = self.network.hostmask

    def __str__(self):
        return '%s/%d' % (self._string_from_ip_int(self._ip),
                          self.network.prefixlen)

    def __eq__(self, other):
        address_equal = IPv6Address.__eq__(self, other)
        if not address_equal or address_equal is NotImplemented:
            return address_equal
        try:
            return self.network == other.network
        except AttributeError:
            # An interface with an associated network is NOT the
            # same as an unassociated address. That's why the hash
            # takes the extra info into account.
            return False

    def __lt__(self, other):
        address_less = IPv6Address.__lt__(self, other)
        if address_less is NotImplemented:
            return NotImplemented
        try:
            return self.network < other.network
        except AttributeError:
            # We *do* allow addresses and interfaces to be sorted. The
            # unassociated address is considered less than all interfaces.
            return False

    def __hash__(self):
        return self._ip ^ self._prefixlen ^ int(self.network.network_address)

    @property
    def ip(self):
        return IPv6Address(self._ip)

    @property
    def with_prefixlen(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip),
                          self._prefixlen)

    @property
    def with_netmask(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip),
                          self.netmask)

    @property
    def with_hostmask(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip),
                          self.hostmask)

    @property
    def is_unspecified(self):
        return self._ip == 0 and self.network.is_unspecified

    @property
    def is_loopback(self):
        return self._ip == 1 and self.network.is_loopback


class IPv6Network(_BaseV6, _BaseNetwork):

    """This class represents and manipulates 128-bit IPv6 networks.

    Attributes: [examples for IPv6('2001:db8::1000/124')]
        .network_address: IPv6Address('2001:db8::1000')
        .hostmask: IPv6Address('::f')
        .broadcast_address: IPv6Address('2001:db8::100f')
        .netmask: IPv6Address('ffff:ffff:ffff:ffff:ffff:ffff:ffff:fff0')
        .prefixlen: 124

    """

    # Class to use when creating address objects
    _address_class = IPv6Address

    def __init__(self, address, strict=True):
        """Instantiate a new IPv6 Network object.

        Args:
            address: A string or integer representing the IPv6 network or the
              IP and prefix/netmask.
              '2001:db8::/128'
              '2001:db8:0000:0000:0000:0000:0000:0000/128'
              '2001:db8::'
              are all functionally the same in IPv6.  That is to say,
              failing to provide a subnetmask will create an object with
              a mask of /128.

              Additionally, an integer can be passed, so
              IPv6Network('2001:db8::') ==
                IPv6Network(42540766411282592856903984951653826560)
              or, more generally
              IPv6Network(int(IPv6Network('2001:db8::'))) ==
                IPv6Network('2001:db8::')

            strict: A boolean. If true, ensure that we have been passed
              A true network address, eg, 2001:db8::1000/124 and not an
              IP address on a network, eg, 2001:db8::1/124.

        Raises:
            AddressValueError: If address isn't a valid IPv6 address.
            NetmaskValueError: If the netmask isn't valid for
              an IPv6 address.
            ValueError: If strict was True and a network address was not
              supplied.

        """
        _BaseV6.__init__(self, address)
        _BaseNetwork.__init__(self, address)

        # Efficient constructor from integer.
        if isinstance(address, int):
            self.network_address = IPv6Address(address)
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv6Address(self._ALL_ONES)
            return

        # Constructing from a packed address
        if isinstance(address, bytes):
            self.network_address = IPv6Address(address)
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv6Address(self._ALL_ONES)
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP prefix string.
        addr = _split_optional_netmask(address)

        self.network_address = IPv6Address(self._ip_int_from_string(addr[0]))

        if len(addr) == 2:
            if self._is_valid_netmask(addr[1]):
                self._prefixlen = int(addr[1])
            else:
                raise NetmaskValueError('%r is not a valid netmask'
                                                     % addr[1])
        else:
            self._prefixlen = self._max_prefixlen

        self.netmask = IPv6Address(self._ip_int_from_prefix(self._prefixlen))
        if strict:
            if (IPv6Address(int(self.network_address) & int(self.netmask)) !=
                self.network_address):
                raise ValueError('%s has host bits set' % self)
        self.network_address = IPv6Address(int(self.network_address) &
                                           int(self.netmask))

        if self._prefixlen == (self._max_prefixlen - 1):
            self.hosts = self.__iter__

    def _is_valid_netmask(self, prefixlen):
        """Verify that the netmask/prefixlen is valid.

        Args:
            prefixlen: A string, the netmask in prefix length format.

        Returns:
            A boolean, True if the prefix represents a valid IPv6
            netmask.

        """
        try:
            prefixlen = int(prefixlen)
        except ValueError:
            return False
        return 0 <= prefixlen <= self._max_prefixlen

    @property
    def is_site_local(self):
        """Test if the address is reserved for site-local.

        Note that the site-local address space has been deprecated by RFC 3879.
        Use is_private to test if this address is in the space of unique local
        addresses as defined by RFC 4193.

        Returns:
            A boolean, True if the address is reserved per RFC 3513 2.5.6.

        """
        return (self.network_address.is_site_local and
                self.broadcast_address.is_site_local)

########NEW FILE########
__FILENAME__ = ordereddict
# encoding: utf-8
'''
ordereddict.py

Created by Thomas Mangin on 2013-03-18.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
'''

# This is only an hack until we drop support for python version < 2.7

class OrderedDict (dict):
	def __init__(self, args):
		dict.__init__(self, args)
		self._order = [_ for _,__ in args]

	def __setitem__(self, key, value):
		dict.__setitem__(self, key, value)
		if key in self._order:
			self._order.remove(key)
		self._order.append(key)

	def __delitem__(self, key):
		dict.__delitem__(self, key)
		self._order.remove(key)

	def keys (self):
		return self._order

	def __iter__ (self):
		return self.__next__()

	def __next__ (self):
		for k in self._order:
			yield k

if __name__ == '__main__':
	d = OrderedDict(((10,'ten'),(8,'eight'),(6,'six'),(4,'four'),(2,'two'),(0,'boom')))
	for k in d:
		print k

########NEW FILE########
__FILENAME__ = environment
# encoding: utf-8
"""
environment.py

Created by Thomas Mangin on 2011-11-29.
Copyright (c) 2011 Exa Networks. All rights reserved.
"""

# XXX: raised exception not caught
# XXX: reloading mid-program not possible
# XXX: validation for path, file, etc not correctly test (ie surely buggy)

import os
import sys
import pwd
import syslog

from exabgp.util.ip import isip

class NoneDict (dict):
	def __getitem__ (self,name):
		return None
nonedict = NoneDict()

class environment (object):
	# class returned on issues
	class Error (Exception):
		pass

	application = 'unset'

	# the configuration to be set by the program
	configuration = {}

	# the final parsed settings
	_settings = None

	location = os.path.normpath(sys.argv[0]) if sys.argv[0].startswith('/') else os.path.normpath(os.path.join(os.getcwd(),sys.argv[0]))
	log_levels = ['EMERG', 'ALERT', 'CRIT', 'CRITICAL', 'ERR', 'ERROR', 'WARNING', 'NOTICE', 'INFO', 'DEBUG']

	@staticmethod
	def setup (conf):
		if environment._settings:
			raise RuntimeError('You already initialised the environment')
		environment._settings = _env(conf)
		return environment._settings

	@staticmethod
	def settings ():
		if not environment._settings:
			raise RuntimeError('You can not have an import using settings() before main() initialised environment')
		return environment._settings

	@staticmethod
	def root (path):
		roots = environment.location.split(os.sep)
		location = []
		for index in range(len(roots)-1,-1,-1):
			if roots[index] == 'lib':
				if index:
					location = roots[:index]
				break
		root = os.path.join(*location)
		paths = [
			os.path.normpath(os.path.join(os.path.join(os.sep,root,path))),
			os.path.normpath(os.path.expanduser(environment.unquote(path))),
			os.path.normpath(os.path.join('/',path)),
		]
		return paths

	@staticmethod
	def integer (_):
		return int(_)

	@staticmethod
	def real (_):
		return float(_)

	@staticmethod
	def lowunquote (_):
		return _.strip().strip('\'"').lower()

	@staticmethod
	def unquote (_):
		return _.strip().strip('\'"')

	@staticmethod
	def quote (_):
		return "'%s'" % str(_)

	@staticmethod
	def nop (_):
		return _

	@staticmethod
	def boolean (_):
		return _.lower() in ('1','yes','on','enable','true')

	@staticmethod
	def api (_):
		encoder = _.lower()
		if encoder not in ('text','json'):
			raise TypeError('invalid encoder')
		return encoder

	@staticmethod
	def methods (_):
		return _.upper().split()

	@staticmethod
	def list (_):
		return "'%s'" % ' '.join(_)

	@staticmethod
	def lower (_):
		return str(_).lower()

	@staticmethod
	def ip (_):
		if isip(_): return _
		raise TypeError('ip %s is invalid' % _)

	@staticmethod
	def optional_ip (_):
		if not _ or isip(_): return _
		raise TypeError('ip %s is invalid' % _)

	@staticmethod
	def user (_):
		# XXX: incomplete
		try:
			pwd.getpwnam(_)
			# uid = answer[2]
		except KeyError:
			raise TypeError('user %s is not found on this system' % _)
		return _

	@staticmethod
	def folder(path):
		paths = environment.root(path)
		options = [path for path in paths if os.path.exists(path)]
		if not options: raise TypeError('%s does not exists' % path)
		first = options[0]
		if not first: raise TypeError('%s does not exists' % first)
		return first

	@staticmethod
	def path (path):
		split = sys.argv[0].split('lib/exabgp')
		if len(split) > 1:
			prefix = os.sep.join(split[:1])
			if prefix and path.startswith(prefix):
				path = path[len(prefix):]
		home = os.path.expanduser('~')
		if path.startswith(home):
			return "'~%s'" % path[len(home):]
		return "'%s'" % path

	@staticmethod
	def conf(path):
		first = environment.folder(path)
		if not os.path.isfile(first): raise TypeError('%s is not a file' % path)
		return first

	@staticmethod
	def exe (path):
		first = environment.conf(path)
		if not os.access(first, os.X_OK): raise TypeError('%s is not an executable' % first)
		return first

	@staticmethod
	def syslog (path):
		path = environment.unquote(path)
		if path in ('stdout','stderr'):
			return path
		if path.startswith('host:'):
			return path
		return path

	@staticmethod
	def redirector (name):
		if name == 'url' or name.startswith('icap://'):
			return name
		raise TypeError('invalid redirector protocol %s, options are url or header' % name)

	@staticmethod
	def syslog_value (log):
		if log not in environment.log_levels:
			if log == 'CRITICAL': log = 'CRIT'
			if log == 'ERROR': log = 'ERR'
			raise TypeError('invalid log level %s' % log)
		return getattr(syslog,'LOG_%s'%log)

	@staticmethod
	def syslog_name (log):
		for name in environment.log_levels:
			if name == 'CRITICAL': name = 'CRIT'
			if name == 'ERROR': name = 'ERR'
			if getattr(syslog,'LOG_%s'%name) == log:
				return name
		raise TypeError('invalid log level %s' % log)

	@staticmethod
	def default ():
		for section in sorted(environment.configuration):
			if section in ('internal','debug'):
				continue
			for option in sorted(environment.configuration[section]):
				values = environment.configuration[section][option]
				default = "'%s'" % values[2] if values[1] in (environment.list,environment.path,environment.quote,environment.syslog) else values[2]
				yield '%s.%s.%s %s: %s. default (%s)' % (environment.application,section,option,' '*(20-len(section)-len(option)),values[3],default)

	@staticmethod
	def iter_ini (diff=False):
		for section in sorted(environment._settings):
			if section in ('internal','debug'):
				continue
			header = '\n[%s.%s]' % (environment.application,section)
			for k in sorted(environment._settings[section]):
				v = environment._settings[section][k]
				if diff and environment.configuration[section][k][0](environment.configuration[section][k][2]) == v:
					continue
				if header:
					yield header
					header = ''
				yield '%s = %s' % (k,environment.configuration[section][k][1](v))

	@staticmethod
	def iter_env (diff=False):
		for section,values in environment._settings.items():
			if section in ('internal','debug'):
				continue
			for k,v in values.items():
				if diff and environment.configuration[section][k][0](environment.configuration[section][k][2]) == v:
					continue
				if environment.configuration[section][k][1] == environment.quote:
					yield "%s.%s.%s='%s'" % (environment.application,section,k,v)
					continue
				yield "%s.%s.%s=%s" % (environment.application,section,k,environment.configuration[section][k][1](v))


	# Compatibility with 2.0.x
	@staticmethod
	def _compatibility (env):
		profile = os.environ.get('PROFILE','')
		if profile:
			env.profile.enable=True
		if profile and profile.lower() not in ['1','true','yes','on','enable']:
			env.profile.file=profile

		# PDB : still compatible as a side effect of the code structure

		syslog = os.environ.get('SYSLOG','')
		if syslog != '':
			env.log.destination=syslog

		if os.environ.get('DEBUG_SUPERVISOR','').lower() in ['1','yes']:
			env.log.reactor = True
		if os.environ.get('DEBUG_DAEMON','').lower() in ['1','yes']:
			env.log.daemon = True
		if os.environ.get('DEBUG_PROCESSES','').lower() in ['1','yes']:
			env.log.processes = True
		if os.environ.get('DEBUG_CONFIGURATION','').lower() in ['1','yes']:
			env.log.configuration = True
		if os.environ.get('DEBUG_WIRE','').lower() in ['1','yes']:
			env.log.network = True
			env.log.packets = True
		if os.environ.get('DEBUG_MESSAGE','').lower() in ['1','yes']:
			env.log.message = True
		if os.environ.get('DEBUG_RIB','').lower() in ['1','yes']:
			env.log.rib = True
		if os.environ.get('DEBUG_TIMER','').lower() in ['1','yes']:
			env.log.timers = True
		if os.environ.get('DEBUG_PARSER','').lower() in ['1','yes']:
			env.log.parser = True
		if os.environ.get('DEBUG_ROUTE','').lower() in ['1','yes']:
			env.log.routes = True
		if os.environ.get('DEBUG_ROUTES','').lower() in ['1','yes']:  # DEPRECATED even in 2.0.x
			env.log.routes = True
		if os.environ.get('DEBUG_ALL','').lower() in ['1','yes']:
			env.log.all = True
		if os.environ.get('DEBUG_CORE','').lower() in ['1','yes']:
			env.log.reactor = True
			env.log.daemon = True
			env.log.processes = True
			env.log.message = True
			env.log.timer = True
			env.log.routes = True
			env.log.parser = False

		pid = os.environ.get('PID','')
		if pid:
			env.daemon.pid = pid

		import pwd

		try:
			me = pwd.getpwuid(os.getuid()).pw_name
			user = os.environ.get('USER','')
			if user and user != 'root' and user != me and env.daemon.user == 'nobody':
				env.daemon.user = user
		except KeyError:
			pass

		daemon = os.environ.get('DAEMONIZE','').lower() in ['1','yes']
		if daemon:
			env.daemon.daemonize = True
			env.log.enable = False

		return env


import ConfigParser

class Store (dict):
	def __getitem__ (self,key):
		return dict.__getitem__(self,key.replace('_','-'))

	def __setitem__ (self,key,value):
		return dict.__setitem__(self,key.replace('_','-'),value)

	def __getattr__ (self,key):
		return dict.__getitem__(self,key.replace('_','-'))

	def __setattr__ (self,key,value):
		return dict.__setitem__(self,key.replace('_','-'),value)


def _env (conf):
	here = os.path.join(os.sep,*os.path.join(environment.location.split(os.sep)))

	location, directory = os.path.split(here)
	while directory:
		if directory == 'lib':
			location = os.path.join(location,'lib')
			break
		location, directory = os.path.split(location)
	# we did not break - ie, we did not find the location in the normal path.
	else:
		# let's try to see if we are running from the QA folder (for unittesting)
		location, directory = os.path.split(here)
		while directory:
			if directory == 'dev':
				location = os.path.join(location,'lib')
				break
			location, directory = os.path.split(location)
		else:
			# oh ! bad, let set the path to something ...
			location = '/lib'

	_conf_paths = []
	if conf:
		_conf_paths.append(os.path.abspath(os.path.normpath(conf)))
	if location:
		_conf_paths.append(os.path.normpath(os.path.join(location,'etc',environment.application,'%s.env' % environment.application)))
	_conf_paths.append(os.path.normpath(os.path.join('/','etc',environment.application,'%s.env' % environment.application)))

	env = Store()
	ini = ConfigParser.ConfigParser()

	ini_files = [path for path in _conf_paths if os.path.exists(path)]
	if ini_files:
		ini.read(ini_files[0])

	for section in environment.configuration:
		default = environment.configuration[section]

		for option in default:
			convert = default[option][0]
			try:
				proxy_section = '%s.%s' % (environment.application,section)
				env_name = '%s.%s' % (proxy_section,option)
				rep_name = env_name.replace('.','_')

				if env_name in os.environ:
					conf = os.environ.get(env_name)
				elif rep_name in os.environ:
					conf = os.environ.get(rep_name)
				else:
					conf = environment.unquote(ini.get(proxy_section,option,nonedict))
					# name without an = or : in the configuration and no value
					if conf == None:
						conf = default[option][2]
			except (ConfigParser.NoSectionError,ConfigParser.NoOptionError):
				conf = default[option][2]
			try:
				env.setdefault(section,Store())[option] = convert(conf)
			except TypeError:
				raise environment.Error('invalid value for %s.%s : %s' % (section,option,conf))

	return environment._compatibility(env)

########NEW FILE########
__FILENAME__ = file
# encoding: utf-8
"""
configuration.py

Created by Thomas Mangin on 2009-08-25.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import os
import sys
import stat
import time
import socket
import shlex

from pprint import pformat
from copy import deepcopy
from struct import pack,unpack

from exabgp.util.ip import isipv4

from exabgp.configuration.environment import environment

from exabgp.protocol.family import AFI,SAFI,known_families

from exabgp.bgp.neighbor import Neighbor

from exabgp.protocol.ip.inet import Inet,inet,pton
from exabgp.bgp.message.direction import OUT

from exabgp.bgp.message.open.asn import ASN
from exabgp.bgp.message.open.holdtime import HoldTime
from exabgp.bgp.message.open.routerid import RouterID

from exabgp.bgp.message.update.nlri.prefix import Prefix
from exabgp.bgp.message.update.nlri.bgp import NLRI,PathInfo,Labels,RouteDistinguisher
from exabgp.bgp.message.update.nlri.flow import BinaryOperator,NumericOperator,FlowNLRI,Flow4Source,Flow4Destination,Flow6Source,Flow6Destination,FlowSourcePort,FlowDestinationPort,FlowAnyPort,FlowIPProtocol,FlowNextHeader,FlowTCPFlag,FlowFragment,FlowPacketLength,FlowICMPType,FlowICMPCode,FlowDSCP,FlowTrafficClass,FlowFlowLabel

from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute.origin import Origin
from exabgp.bgp.message.update.attribute.nexthop import cachedNextHop
from exabgp.bgp.message.update.attribute.aspath import ASPath
from exabgp.bgp.message.update.attribute.med import MED
from exabgp.bgp.message.update.attribute.localpref import LocalPreference
from exabgp.bgp.message.update.attribute.atomicaggregate import AtomicAggregate
from exabgp.bgp.message.update.attribute.aggregator import Aggregator
from exabgp.bgp.message.update.attribute.communities import Community,cachedCommunity,Communities,ECommunity,ECommunities,to_ExtendedCommunity,to_FlowTrafficRate,to_FlowRedirectVRFASN,to_FlowRedirectVRFIP,to_FlowRedirect,to_FlowTrafficMark,to_FlowTrafficAction
from exabgp.bgp.message.update.attribute.originatorid import OriginatorID
from exabgp.bgp.message.update.attribute.clusterlist import ClusterList
from exabgp.bgp.message.update.attribute.aigp import AIGP
from exabgp.bgp.message.update.attribute.unknown import UnknownAttribute

from exabgp.bgp.message.operational import MAX_ADVISORY,Advisory,Query,Response

from exabgp.bgp.message.update.attributes import Attributes

from exabgp.rib.change import Change
from exabgp.bgp.message.refresh import RouteRefresh

from exabgp.logger import Logger

# Duck class, faking part of the Attribute interface
# We add this to routes when when need o split a route in smaller route
# The value stored is the longer netmask we want to use
# As this is not a real BGP attribute this stays in the configuration file

class Split (int):
	ID = AttributeID.INTERNAL_SPLIT
	MULTIPLE = False


class Watchdog (str):
	ID = AttributeID.INTERNAL_WATCHDOG
	MULTIPLE = False

class Withdrawn (object):
	ID = AttributeID.INTERNAL_WITHDRAW
	MULTIPLE = False


# Take an integer an created it networked packed representation for the right family (ipv4/ipv6)
def pack_int (afi,integer,mask):
	return ''.join([chr((integer>>(offset*8)) & 0xff) for offset in range(Inet.length[afi]-1,-1,-1)])

def formated (line):
	changed_line = '#'
	new_line = line.strip().replace('\t',' ').replace(']',' ]').replace('[','[ ').replace(')',' )').replace('(','( ').replace(',',' , ')
	while new_line != changed_line:
		changed_line = new_line
		new_line = new_line.replace('  ',' ')
	return new_line


class Configuration (object):
	TTL_SECURITY = 255

#	'  hold-time 180;\n' \

	_str_bad_flow = "you tried to filter a flow using an invalid port for a component .."

	_str_route_error = \
	'community, extended-communities and as-path can take a single community as parameter.\n' \
	'only next-hop is mandatory\n' \
	'\n' \
	'syntax:\n' \
	'route 10.0.0.1/22 {\n' \
	'  path-information 0.0.0.1;\n' \
	'  route-distinguisher|rd 255.255.255.255:65535|65535:65536|65536:65535' \
	'  next-hop 192.0.1.254;\n' \
	'  origin IGP|EGP|INCOMPLETE;\n' \
	'  as-path [ AS-SEQUENCE-ASN1 AS-SEQUENCE-ASN2 ( AS-SET-ASN3 )] ;\n' \
	'  med 100;\n' \
	'  local-preference 100;\n' \
	'  atomic-aggregate;\n' \
	'  community [ 65000 65001 65002 ];\n' \
	'  extended-community [ target:1234:5.6.7.8 target:1.2.3.4:5678 origin:1234:5.6.7.8 origin:1.2.3.4:5678 0x0002FDE800000001 ]\n' \
	'  originator-id 10.0.0.10;\n' \
	'  cluster-list [ 10.10.0.1 10.10.0.2 ];\n' \
	'  label [ 100 200 ];\n' \
	'  aggregator ( 65000:10.0.0.10 )\n' \
	'  aigp 100;\n' \
	'  split /24\n' \
	'  watchdog watchdog-name\n' \
	'  withdraw\n' \
	'}\n' \
	'\n' \
	'syntax:\n' \
	'route 10.0.0.1/22' \
	' path-information 0.0.0.1' \
	' route-distinguisher|rd 255.255.255.255:65535|65535:65536|65536:65535' \
	' next-hop 192.0.2.1' \
	' origin IGP|EGP|INCOMPLETE' \
	' as-path AS-SEQUENCE-ASN' \
	' med 100' \
	' local-preference 100' \
	' atomic-aggregate' \
	' community 65000' \
	' extended-community target:1234:5.6.7.8' \
	' originator-id 10.0.0.10' \
	' cluster-list 10.10.0.1' \
	' label 150' \
	' aggregator ( 65000:10.0.0.10 )' \
	' aigp 100' \
	' split /24' \
	' watchdog watchdog-name' \
	' withdraw' \
	';\n' \

	_str_flow_error = \
	'syntax: flow {\n' \
	'   route give-me-a-name\n' \
	'      route-distinguisher|rd 255.255.255.255:65535|65535:65536|65536:65535; (optional)\n' \
	'      next-hop 1.2.3.4; (to use with redirect-to-nexthop)\n' \
	'      match {\n' \
	'         source 10.0.0.0/24;\n' \
	'         source ::1/128/0;\n' \
	'         destination 10.0.1.0/24;\n' \
	'         port 25;\n' \
	'         source-port >1024\n' \
	'         destination-port =80 =3128 >8080&<8088;\n' \
	'         protocol [ udp tcp ];  (ipv4 only)\n' \
	'         next-header [ udp tcp ]; (ipv6 only)\n' \
	'         fragment [ not-a-fragment dont-fragment is-fragment first-fragment last-fragment ]; (ipv4 only)\n' \
	'         packet-length >200&<300 >400&<500;\n' \
	'         flow-label >100&<2000; (ipv6 only)\n' \
	'      }\n' \
	'      then {\n' \
	'         accept;\n' \
	'         discard;\n' \
	'         rate-limit 9600;\n' \
	'         redirect 30740:12345;\n' \
	'         redirect 1.2.3.4:5678;\n' \
	'         redirect 1.2.3.4;\n' \
	'         redirect-next-hop;\n' \
	'         copy 1.2.3.4;\n' \
	'         mark 123;\n' \
	'         action sample|terminal|sample-terminal;\n' \
	'      }\n' \
	'   }\n' \
	'}\n\n' \
	'one or more match term, one action\n' \
	'fragment code is totally untested\n' \

	_str_process_error = \
	'syntax: process name-of-process {\n' \
	'          run /path/to/command with its args;\n' \
	'        }\n\n' \

	_str_family_error = \
	'syntax: family {\n' \
	'          all;       # default if not family block is present, announce all we know\n' \
	'          minimal    # use the AFI/SAFI required to announce the routes in the configuration\n' \
	'          \n' \
	'          ipv4 unicast;\n' \
	'          ipv4 multicast;\n' \
	'          ipv4 nlri-mpls;\n' \
	'          ipv4 mpls-vpn;\n' \
	'          ipv4 flow;\n' \
	'          ipv4 flow-vpn;\n' \
	'          ipv6 unicast;\n' \
	'          ipv6 flow;\n' \
	'          ipv6 flow-vpn;\n' \
	'        }\n'

	_str_capa_error = \
	'syntax: capability {\n' \
	'          graceful-restart <time in second>;\n' \
	'          asn4 enable|disable;\n' \
	'          add-path disable|send|receive|send/receive;\n' \
	'          multi-session enable|disable;\n' \
	'          operational enable|disable;\n' \
	'        }\n'

	def __init__ (self,fname,text=False):
		self.debug = environment.settings().debug.configuration
		self.api_encoder = environment.settings().api.encoder

		self.logger = Logger()
		self._text = text
		self._fname = fname
		self._clear()

	def _clear (self):
		self.process = {}
		self.neighbor = {}
		self.error = ''
		self._neighbor = {}
		self._scope = []
		self._location = ['root']
		self._line = []
		self._error = ''
		self._number = 1
		self._flow_state = 'out'
		self._nexthopself = None

	# Public Interface

	def reload (self):
		try:
			return self._reload()
		except KeyboardInterrupt:
			self.error = 'configuration reload aborted by ^C or SIGINT'
			return False

	def _reload (self):
		if self._text:
			self._tokens = self._tokenise(self._fname.split('\n'))
		else:
			try:
				f = open(self._fname,'r')
				self._tokens = self._tokenise(f)
				f.close()
			except IOError,e:
				error = str(e)
				if error.count(']'):
					self.error = error.split(']')[1].strip()
				else:
					self.error = error
				if self.debug: raise
				return False

		self._clear()

		r = False
		while not self.finished():
			r = self._dispatch(self._scope,'configuration',['group','neighbor'],[])
			if r is False: break

		if r not in [True,None]:
			self.error = "\nsyntax error in section %s\nline %d : %s\n\n%s" % (self._location[-1],self.number(),self.line(),self._error)
			return False

		self.neighbor = self._neighbor

		if environment.settings().debug.route:
			self.decode(environment.settings().debug.route)
			sys.exit(0)

		if environment.settings().debug.selfcheck:
			self.selfcheck()
			sys.exit(0)

		return True

	def parse_api_route (self,command,peers,action):
		tokens = formated(command).split(' ')[1:]
		if len(tokens) < 4:
			return False
		if tokens[0] != 'route':
			return False
		changes = []
		if 'self' in command:
			for peer,nexthop in peers.iteritems():
				scope = [{}]
				self._nexthopself = nexthop
				if not self._single_static_route(scope,tokens[1:]):
					self._nexthopself = None
					return False
				for change in scope[0]['announce']:
					changes.append((peer,change))
			self._nexthopself = None
		else:
			scope = [{}]
			if not self._single_static_route(scope,tokens[1:]):
				return False
			for peer in peers:
				for change in scope[0]['announce']:
					changes.append((peer,change))
		if action == 'withdraw':
			for (peer,change) in changes:
				change.nlri.action = OUT.withdraw
		return changes


	def parse_api_attribute (self,command,peers,action):
		# This is a quick solution which does not support next-hop self
		attribute,nlris = command.split('nlri')
		route = '%s route 0.0.0.0/0 %s' % (action, ' '.join(attribute.split()[2:]))
		parsed = self.parse_api_route(route,peers,action)
		if parsed in (True,False,None):
			return parsed
		attributes = parsed[0][1].attributes
		nexthop = parsed[0][1].nlri.nexthop
		changes = []
		for nlri in nlris.split():
			ip,mask = nlri.split('/')
			change = Change(NLRI(*inet(ip),mask=int(mask),nexthop=nexthop,action=action),attributes)
			if action == 'withdraw':
				change.nlri.action = OUT.withdraw
			else:
				change.nlri.action = OUT.announce
			changes.append((peers.keys(),change))
		return changes

	def parse_api_flow (self,command,action):
		self._tokens = self._tokenise(' '.join(formated(command).split(' ')[2:]).split('\\n'))
		scope = [{}]
		if not self._dispatch(scope,'flow',['route',],[]):
			return False
		if not self._check_flow_route(scope):
			return False
		changes = scope[0]['announce']
		if action == 'withdraw':
			for change in changes:
				change.nlri.action = OUT.withdraw
		return changes

	def parse_api_refresh (self,command):
		tokens = formated(command).split(' ')[2:]
		if len(tokens) != 2:
			return False
		afi = AFI.value(tokens.pop(0))
		safi = SAFI.value(tokens.pop(0))
		if afi is None or safi is None:
			return False
		return RouteRefresh(afi,safi)

	# operational

	def parse_api_operational (self,command):
		tokens = formated(command).split(' ',2)
		scope = [{}]

		if len(tokens) != 3:
			return False

		operational = tokens[0].lower()
		what = tokens[1].lower()

		if operational != 'operational':
			return False

		if what == 'asm':
			if not self._single_operational(Advisory.ASM,scope,['afi','safi','advisory'],tokens[2]):
				return False
		elif what == 'adm':
			if not self._single_operational(Advisory.ADM,scope,['afi','safi','advisory'],tokens[2]):
				return False
		elif what == 'rpcq':
			if not self._single_operational(Query.RPCQ,scope,['afi','safi','sequence'],tokens[2]):
				return False
		elif what == 'rpcp':
			if not self._single_operational(Response.RPCP,scope,['afi','safi','sequence','counter'],tokens[2]):
				return False
		elif what == 'apcq':
			if not self._single_operational(Query.APCQ,scope,['afi','safi','sequence'],tokens[2]):
				return False
		elif what == 'apcp':
			if not self._single_operational(Response.APCP,scope,['afi','safi','sequence','counter'],tokens[2]):
				return False
		elif what == 'lpcq':
			if not self._single_operational(Query.LPCQ,scope,['afi','safi','sequence'],tokens[2]):
				return False
		elif what == 'lpcp':
			if not self._single_operational(Response.LPCP,scope,['afi','safi','sequence','counter'],tokens[2]):
				return False
		else:
			return False

		operational = scope[0]['operational'][0]
		return operational

	# XXX: FIXME: move this from here to the reactor (or whatever will manage command from user later)
	def change_to_peers (self,change,peers):
		result = True
		for neighbor in self.neighbor:
			if neighbor in peers:
				if change.nlri.family() in self.neighbor[neighbor].families():
					self.neighbor[neighbor].rib.outgoing.insert_announced(change)
				else:
					self.logger.configuration('the route family is not configured on neighbor','error')
					result = False
		return result

	# XXX: FIXME: move this from here to the reactor (or whatever will manage command from user later)
	def operational_to_peers (self,operational,peers):
		result = True
		for neighbor in self.neighbor:
			if neighbor in peers:
				if operational.family() in self.neighbor[neighbor].families():
					if operational.name == 'ASM':
						self.neighbor[neighbor].asm[operational.family()] = operational
					self.neighbor[neighbor].messages.append(operational)
				else:
					self.logger.configuration('the route family is not configured on neighbor','error')
					result = False
		return result

	# XXX: FIXME: move this from here to the reactor (or whatever will manage command from user later)
	def refresh_to_peers (self,refresh,peers):
		result = True
		for neighbor in self.neighbor:
			if neighbor in peers:
				family = (refresh.afi,refresh.safi)
				if family in self.neighbor[neighbor].families():
					self.neighbor[neighbor].refresh.append(refresh.__class__(refresh.afi,refresh.safi))
				else:
					result = False
		return result

	# Tokenisation

	def _tokenise (self,text):
		r = []
		config = ''
		for line in text:
			self.logger.configuration('loading | %s' % line.rstrip())
			replaced = formated(line)
			config += line
			if not replaced:
				continue
			if replaced.startswith('#'):
				continue
			command = replaced[:3]
			if command in ('md5','asm'):
				string = line.strip()[3:].strip()
				if string[-1] == ';':
					string = string[:-1]
				r.append([command,string,';'])
			elif replaced[:3] == 'run':
				r.append([t for t in replaced[:-1].split(' ',1) if t] + [replaced[-1]])
			else:
				r.append([t.lower() for t in replaced[:-1].split(' ') if t] + [replaced[-1]])
		self.logger.config(config)
		return r

	def tokens (self):
		self._number += 1
		self._line = self._tokens.pop(0)
		return self._line

	def number (self):
		return self._number

	def line (self):
		return ' '.join(self._line)

	def finished (self):
		return len(self._tokens) == 0

	# Flow control ......................

	# name is not used yet but will come really handy if we have name collision :D
	def _dispatch (self,scope,name,multi,single):
		try:
			tokens = self.tokens()
		except IndexError:
			self._error = 'configuration file incomplete (most likely missing })'
			if self.debug: raise
			return False
		self.logger.configuration('analysing tokens %s ' % str(tokens))
		self.logger.configuration('  valid block options %s' % str(multi))
		self.logger.configuration('  valid parameters    %s' % str(single))
		end = tokens[-1]
		if multi and end == '{':
			self._location.append(tokens[0])
			return self._multi_line(scope,name,tokens[:-1],multi)
		if single and end == ';':
			return self._single_line(scope,name,tokens[:-1],single)
		if end == '}':
			if len(self._location) == 1:
				self._error = 'closing too many parenthesis'
				if self.debug: raise
				return False
			self._location.pop(-1)
			return None
		return False

	def _multi_line (self,scope,name,tokens,valid):
		command = tokens[0]

		if valid and command not in valid:
			self._error = 'option %s in not valid here' % command
			if self.debug: raise
			return False

		if name == 'configuration':
			if command == 'neighbor':
				if self._multi_neighbor(scope,tokens[1:]):
					return self._make_neighbor(scope)
				return False
			if command == 'group':
				if len(tokens) != 2:
					self._error = 'syntax: group <name> { <options> }'
					if self.debug: raise
					return False
				return self._multi_group(scope,tokens[1])

		if name == 'group':
			if command == 'neighbor':
				if self._multi_neighbor(scope,tokens[1:]):
					return self._make_neighbor(scope)
				return False
			if command == 'static': return self._multi_static(scope,tokens[1:])
			if command == 'flow': return self._multi_flow(scope,tokens[1:])
			if command == 'process': return self._multi_process(scope,tokens[1:])
			if command == 'family': return self._multi_family(scope,tokens[1:])
			if command == 'capability': return self._multi_capability(scope,tokens[1:])
			if command == 'operational': return self._multi_operational(scope,tokens[1:])

		if name == 'neighbor':
			if command == 'static': return self._multi_static(scope,tokens[1:])
			if command == 'flow': return self._multi_flow(scope,tokens[1:])
			if command == 'process': return self._multi_process(scope,tokens[1:])
			if command == 'family': return self._multi_family(scope,tokens[1:])
			if command == 'capability': return self._multi_capability(scope,tokens[1:])
			if command == 'operational': return self._multi_operational(scope,tokens[1:])

		if name == 'static':
			if command == 'route':
				if self._multi_static_route(scope,tokens[1:]):
					return self._check_static_route(scope)
				return False

		if name == 'flow':
			if command == 'route':
				if self._multi_flow_route(scope,tokens[1:]):
					return self._check_flow_route(scope)
				return False

		if name == 'flow-route':
			if command == 'match':
				if self._multi_match(scope,tokens[1:]):
					return True
				return False
			if command == 'then':
				if self._multi_then(scope,tokens[1:]):
					return True
				return False
		return False

	def _single_line (self,scope,name,tokens,valid):
		command = tokens[0]
		if valid and command not in valid:
			self._error = 'invalid keyword "%s"' % command
			if self.debug: raise
			return False

		elif name == 'route':
			if command == 'origin': return self._route_origin(scope,tokens[1:])
			if command == 'as-path': return self._route_aspath(scope,tokens[1:])
			# For legacy with version 2.0.x
			if command == 'as-sequence': return self._route_aspath(scope,tokens[1:])
			if command == 'med': return self._route_med(scope,tokens[1:])
			if command == 'aigp': return self._route_aigp(scope,tokens[1:])
			if command == 'next-hop': return self._route_next_hop(scope,tokens[1:])
			if command == 'local-preference': return self._route_local_preference(scope,tokens[1:])
			if command == 'atomic-aggregate': return self._route_atomic_aggregate(scope,tokens[1:])
			if command == 'aggregator': return self._route_aggregator(scope,tokens[1:])
			if command == 'path-information': return self._route_path_information(scope,tokens[1:])
			if command == 'originator-id': return self._route_originator_id(scope,tokens[1:])
			if command == 'cluster-list': return self._route_cluster_list(scope,tokens[1:])
			if command == 'split': return self._route_split(scope,tokens[1:])
			if command == 'label': return self._route_label(scope,tokens[1:])
			if command in ('rd','route-distinguisher'): return self._route_rd(scope,tokens[1:],SAFI.mpls_vpn)
			if command == 'watchdog': return self._route_watchdog(scope,tokens[1:])
			# withdrawn is here to not break legacy code
			if command in ('withdraw','withdrawn'): return self._route_withdraw(scope,tokens[1:])

			if command == 'community': return self._route_community(scope,tokens[1:])
			if command == 'extended-community': return self._route_extended_community(scope,tokens[1:])
			if command == 'attribute': self._route_generic_attribute(scope,tokens[1:])

		elif name == 'flow-route':
			if command in ('rd','route-distinguisher'): return self._route_rd(scope,tokens[1:],SAFI.flow_vpn)
			if command == 'next-hop': return self._flow_route_next_hop(scope,tokens[1:])

		elif name == 'flow-match':
			if command == 'source': return self._flow_source(scope,tokens[1:])
			if command == 'destination': return self._flow_destination(scope,tokens[1:])
			if command == 'port': return self._flow_route_anyport(scope,tokens[1:])
			if command == 'source-port': return self._flow_route_source_port(scope,tokens[1:])
			if command == 'destination-port': return self._flow_route_destination_port(scope,tokens[1:])
			if command == 'protocol': return self._flow_route_protocol(scope,tokens[1:])
			if command == 'next-header': return self._flow_route_next_header(scope,tokens[1:])
			if command == 'tcp-flags': return self._flow_route_tcp_flags(scope,tokens[1:])
			if command == 'icmp-type': return self._flow_route_icmp_type(scope,tokens[1:])
			if command == 'icmp-code': return self._flow_route_icmp_code(scope,tokens[1:])
			if command == 'fragment': return self._flow_route_fragment(scope,tokens[1:])
			if command == 'dscp': return self._flow_route_dscp(scope,tokens[1:])
			if command == 'traffic-class': return self._flow_route_traffic_class(scope,tokens[1:])
			if command == 'packet-length': return self._flow_route_packet_length(scope,tokens[1:])
			if command == 'flow-label': return self._flow_route_flow_label(scope,tokens[1:])

		elif name == 'flow-then':
			if command == 'accept': return self._flow_route_accept(scope,tokens[1:])
			if command == 'discard': return self._flow_route_discard(scope,tokens[1:])
			if command == 'rate-limit': return self._flow_route_rate_limit(scope,tokens[1:])
			if command == 'redirect': return self._flow_route_redirect(scope,tokens[1:])
			if command == 'redirect-to-nexthop': return self._flow_route_redirect_next_hop(scope,tokens[1:])
			if command == 'copy': return self._flow_route_copy(scope,tokens[1:])
			if command == 'mark': return self._flow_route_mark(scope,tokens[1:])
			if command == 'action': return self._flow_route_action(scope,tokens[1:])

			if command == 'community': return self._route_community(scope,tokens[1:])
			if command == 'extended-community': return self._route_extended_community(scope,tokens[1:])

		if name in ('neighbor','group'):
			if command == 'description': return self._set_description(scope,tokens[1:])
			if command == 'router-id': return self._set_router_id(scope,'router-id',tokens[1:])
			if command == 'local-address': return self._set_ip(scope,'local-address',tokens[1:])
			if command == 'local-as': return self._set_asn(scope,'local-as',tokens[1:])
			if command == 'peer-as': return self._set_asn(scope,'peer-as',tokens[1:])
			if command == 'passive': return self._set_passive(scope,'passive',tokens[1:])
			if command == 'hold-time': return self._set_holdtime(scope,'hold-time',tokens[1:])
			if command == 'md5': return self._set_md5(scope,'md5',tokens[1:])
			if command == 'ttl-security': return self._set_ttl(scope,'ttl-security',tokens[1:])
			if command == 'group-updates': return self._set_boolean(scope,'group-updates',tokens[1:],'true')
			if command == 'aigp': return self._set_boolean(scope,'aigp',tokens[1:],'false')
			# deprecated
			if command == 'route-refresh': return self._set_boolean(scope,'route-refresh',tokens[1:])
			if command == 'graceful-restart': return self._set_gracefulrestart(scope,'graceful-restart',tokens[1:])
			if command == 'multi-session': return self._set_boolean(scope,'multi-session',tokens[1:])
			if command == 'add-path': return self._set_addpath(scope,'add-path',tokens[1:])
			if command == 'auto-flush': return self._set_boolean(scope,'auto-flush',tokens[1:])
			if command == 'adj-rib-out': return self._set_boolean(scope,'adj-rib-out',tokens[1:])

		elif name == 'family':
			if command == 'inet': return self._set_family_inet4(scope,tokens[1:])
			if command == 'inet4': return self._set_family_inet4(scope,tokens[1:])
			if command == 'inet6': return self._set_family_inet6(scope,tokens[1:])
			if command == 'ipv4': return self._set_family_ipv4(scope,tokens[1:])
			if command == 'ipv6': return self._set_family_ipv6(scope,tokens[1:])
			if command == 'minimal': return self._set_family_minimal(scope,tokens[1:])
			if command == 'all': return self._set_family_all(scope,tokens[1:])

		elif name == 'capability':
			if command == 'route-refresh': return self._set_boolean(scope,'route-refresh',tokens[1:])
			if command == 'graceful-restart': return self._set_gracefulrestart(scope,'graceful-restart',tokens[1:])
			if command == 'multi-session': return self._set_boolean(scope,'multi-session',tokens[1:])
			if command == 'operational': return self._set_boolean(scope,'capa-operational',tokens[1:])
			if command == 'add-path': return self._set_addpath(scope,'add-path',tokens[1:])
			if command == 'asn4': return self._set_asn4(scope,'asn4',tokens[1:])
			if command == 'aigp': return self._set_boolean(scope,'aigp',tokens[1:],'false')

		elif name == 'process':
			if command == 'run': return self._set_process_run(scope,'process-run',tokens[1:])
			# legacy ...
			if command == 'parse-routes':
				self._set_process_command(scope,'neighbor-changes',tokens[1:])
				self._set_process_command(scope,'receive-routes',tokens[1:])
				return True
			# legacy ...
			if command == 'peer-updates':
				self._set_process_command(scope,'neighbor-changes',tokens[1:])
				self._set_process_command(scope,'receive-routes',tokens[1:])
				return True
			# new interface
			if command == 'encoder': return self._set_process_encoder(scope,'encoder',tokens[1:])
			if command == 'receive-packets': return self._set_process_command(scope,'receive-packets',tokens[1:])
			if command == 'send-packets': return self._set_process_command(scope,'send-packets',tokens[1:])
			if command == 'receive-routes': return self._set_process_command(scope,'receive-routes',tokens[1:])
			if command == 'neighbor-changes': return self._set_process_command(scope,'neighbor-changes',tokens[1:])
			if command == 'receive-operational': return self._set_process_command(scope,'receive-operational',tokens[1:])

		elif name == 'static':
			if command == 'route': return self._single_static_route(scope,tokens[1:])

		elif name == 'operational':
			if command == 'asm': return self._single_operational_asm(scope,tokens[1])
			# it does not make sense to have adm

		return False

	# Programs used to control exabgp

	def _multi_process (self,scope,tokens):
		while True:
			r = self._dispatch(scope,'process',[],['run','encoder','receive-packets','send-packets','receive-routes','receive-operational','neighbor-changes',  'peer-updates','parse-routes'])
			if r is False: return False
			if r is None: break

		name = tokens[0] if len(tokens) >= 1 else 'conf-only-%s' % str(time.time())[-6:]
		self.process.setdefault(name,{})['neighbor'] = scope[-1]['peer-address'] if 'peer-address' in scope[-1] else '*'

		run = scope[-1].pop('process-run','')
		if run:
			if len(tokens) != 1:
				self._error = self._str_process_error
				if self.debug: raise
				return False
			self.process[name]['encoder'] = scope[-1].get('encoder','') or self.api_encoder
			self.process[name]['run'] = run
			return True
		elif len(tokens):
			self._error = self._str_process_error
			if self.debug: raise
			return False

	def _set_process_command (self,scope,command,value):
		scope[-1][command] = True
		return True

	def _set_process_encoder (self,scope,command,value):
		if value and value[0] in ('text','json'):
			scope[-1][command] = value[0]
			return True

		self._error = self._str_process_error
		if self.debug: raise
		return False

	def _set_process_run (self,scope,command,value):
		line = ' '.join(value).strip()
		if len(line) > 2 and line[0] == line[-1] and line[0] in ['"',"'"]:
			line = line[1:-1]
		if ' ' in line:
			args = shlex.split(line,' ')
			prg,args = args[0],args[1:]
		else:
			prg = line
			args = ''

		if not prg:
			self._error = 'prg requires the program to prg as an argument (quoted or unquoted)'
			if self.debug: raise
			return False
		if prg[0] != '/':
			if prg.startswith('etc/exabgp'):
				parts = prg.split('/')
				path = [os.environ.get('ETC','etc'),] + parts[2:]
				prg = os.path.join(*path)
			else:
				prg = os.path.abspath(os.path.join(os.path.dirname(self._fname),prg))
		if not os.path.exists(prg):
			self._error = 'can not locate the the program "%s"' % prg
			if self.debug: raise
			return False

		# XXX: Yep, race conditions are possible, those are sanity checks not security ones ...
		s = os.stat(prg)

		if stat.S_ISDIR(s.st_mode):
			self._error = 'can not execute directories "%s"' % prg
			if self.debug: raise
			return False

		if s.st_mode & stat.S_ISUID:
			self._error = 'refusing to run setuid programs "%s"' % prg
			if self.debug: raise
			return False

		check = stat.S_IXOTH
		if s.st_uid == os.getuid():
			check |= stat.S_IXUSR
		if s.st_gid == os.getgid():
			check |= stat.S_IXGRP

		if not check & s.st_mode:
			self._error = 'exabgp will not be able to run this program "%s"' % prg
			if self.debug: raise
			return False

		if args:
			scope[-1][command] = [prg] + args
		else:
			scope[-1][command] = [prg,]
		return True

	# Limit the AFI/SAFI pair announced to peers

	def _multi_family (self,scope,tokens):
		# we know all the families we should use
		self._family = False
		scope[-1]['families'] = []
		while True:
			r = self._dispatch(scope,'family',[],['inet','inet4','inet6','ipv4','ipv6','minimal','all'])
			if r is False: return False
			if r is None: break
		self._family = False
		return True

	def _set_family_inet4 (self,scope,tokens):
		self.logger.configuration("the word inet4 is deprecated, please use ipv4 instead",'error')
		return self._set_family_ipv4 (scope,tokens)

	def _set_family_ipv4 (self,scope,tokens):
		if self._family:
			self._error = 'ipv4 can not be used with all or minimal'
			if self.debug: raise
			return False

		try:
			safi = tokens.pop(0)
		except IndexError:
			self._error = 'missing family safi'
			if self.debug: raise
			return False

		if safi == 'unicast':
			scope[-1]['families'].append((AFI(AFI.ipv4),SAFI(SAFI.unicast)))
		elif safi == 'multicast':
			scope[-1]['families'].append((AFI(AFI.ipv4),SAFI(SAFI.multicast)))
		elif safi == 'nlri-mpls':
			scope[-1]['families'].append((AFI(AFI.ipv4),SAFI(SAFI.nlri_mpls)))
		elif safi == 'mpls-vpn':
			scope[-1]['families'].append((AFI(AFI.ipv4),SAFI(SAFI.mpls_vpn)))
		elif safi in ('flow'):
			scope[-1]['families'].append((AFI(AFI.ipv4),SAFI(SAFI.flow_ip)))
		elif safi == 'flow-vpn':
			scope[-1]['families'].append((AFI(AFI.ipv4),SAFI(SAFI.flow_vpn)))
		else:
			return False
		return True

	def _set_family_inet6 (self,scope,tokens):
		self.logger.configuration("the word inet6 is deprecated, please use ipv6 instead",'error')
		return self._set_family_ipv6 (scope,tokens)

	def _set_family_ipv6 (self,scope,tokens):
		try:
			if self._family:
				self._error = 'ipv6 can not be used with all or minimal'
				if self.debug: raise
				return False

			safi = tokens.pop(0)
			if safi == 'unicast':
				scope[-1]['families'].append((AFI(AFI.ipv6),SAFI(SAFI.unicast)))
			elif safi == 'mpls-vpn':
				scope[-1]['families'].append((AFI(AFI.ipv6),SAFI(SAFI.mpls_vpn)))
			elif safi in ('flow'):
				scope[-1]['families'].append((AFI(AFI.ipv6),SAFI(SAFI.flow_ip)))
			elif safi == 'flow-vpn':
				scope[-1]['families'].append((AFI(AFI.ipv6),SAFI(SAFI.flow_vpn)))
			else:
				return False
			return True
		except (IndexError,ValueError):
			self._error = 'missing safi'
			if self.debug: raise
			return False

	def _set_family_minimal (self,scope,tokens):
		if scope[-1]['families']:
			self._error = 'minimal can not be used with any other options'
			if self.debug: raise
			return False
		scope[-1]['families'] = 'minimal'
		self._family = True
		return True

	def _set_family_all (self,scope,tokens):
		if scope[-1]['families']:
			self._error = 'all can not be used with any other options'
			if self.debug: raise
			return False
		scope[-1]['families'] = 'all'
		self._family = True
		return True

	# capacity

	def _multi_capability (self,scope,tokens):
		# we know all the families we should use
		self._capability = False
		while True:
			r = self._dispatch(scope,'capability',[],['route-refresh','graceful-restart','multi-session','operational','add-path','asn4','aigp'])
			if r is False: return False
			if r is None: break
		return True

	def _set_gracefulrestart (self,scope,command,value):
		if not len(value):
			scope[-1][command] = None
			return True
		try:
			# README: Should it be a subclass of int ?
			grace = int(value[0])
			if grace < 0:
				raise ValueError('graceful-restart can not be negative')
			if grace >= pow(2,16):
				raise ValueError('graceful-restart must be smaller than %d' % pow(2,16))
			scope[-1][command] = grace
			return True
		except ValueError:
			self._error = '"%s" is an invalid graceful-restart time' % ' '.join(value)
			if self.debug: raise
			return False
		return True

	def _set_addpath (self,scope,command,value):
		try:
			ap = value[0].lower()
			apv = 0
			if ap.endswith('receive'):
				apv += 1
			if ap.startswith('send'):
				apv += 2
			if not apv and ap not in ('disable','disabled'):
				raise ValueError('invalid add-path')
			scope[-1][command] = apv
			return True
		except (ValueError,IndexError):
			self._error = '"%s" is an invalid add-path' % ' '.join(value) + '\n' + self._str_capa_error
			if self.debug: raise
			return False

	def _set_boolean (self,scope,command,value,default='true'):
		try:
			boolean = value[0].lower() if value else default
			if boolean in ('true','enable','enabled'):
				scope[-1][command] = True
			elif boolean in ('false','disable','disabled'):
				scope[-1][command] = False
			elif boolean in ('unset',):
				scope[-1][command] = None
			else:
				raise ValueError()
			return True
		except (ValueError,IndexError):
			self._error = 'invalid %s command (valid options are true or false)' % command
			if self.debug: raise
			return False

	def _set_asn4 (self,scope,command,value):
		try:
			if not value:
				scope[-1][command] = True
				return True
			asn4 = value[0].lower()
			if asn4 in ('disable','disabled'):
				scope[-1][command] = False
				return True
			if asn4 in ('enable','enabled'):
				scope[-1][command] = True
				return True
			self._error = '"%s" is an invalid asn4 parameter options are enable (default) and disable)' % ' '.join(value)
			return False
		except ValueError:
			self._error = '"%s" is an invalid asn4 parameter options are enable (default) and disable)' % ' '.join(value)
			if self.debug: raise
			return False

	# route grouping with watchdog

	def _route_watchdog (self,scope,tokens):
		try:
			w = tokens.pop(0)
			if w.lower() in ['announce','withdraw']:
				raise ValueError('invalid watchdog name %s' % w)
		except IndexError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

		try:
			scope[-1]['announce'][-1].attributes.add(Watchdog(w))
			return True
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _route_withdraw (self,scope,tokens):
		try:
			scope[-1]['announce'][-1].attributes.add(Withdrawn())
			return True
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

	# Group Neighbor

	def _multi_group (self,scope,address):
		scope.append({})
		while True:
			r = self._dispatch(scope,'group',['static','flow','neighbor','process','family','capability','operational'],['description','router-id','local-address','local-as','peer-as','passive','hold-time','add-path','graceful-restart','md5','ttl-security','multi-session','group-updates','route-refresh','asn4','aigp','auto-flush','adj-rib-out'])
			if r is False:
				return False
			if r is None:
				scope.pop(-1)
				return True

	def _make_neighbor (self,scope):
		# we have local_scope[-2] as the group template and local_scope[-1] as the peer specific
		if len(scope) > 1:
			for key,content in scope[-2].iteritems():
				if key not in scope[-1]:
					scope[-1][key] = deepcopy(content)
				elif key == 'announce':
					scope[-1][key].extend(scope[-2][key])

		self.logger.configuration("\nPeer configuration complete :")
		for _key in scope[-1].keys():
			stored = scope[-1][_key]
			if hasattr(stored,'__iter__'):
				for category in scope[-1][_key]:
					for _line in pformat(str(category),3,3,3).split('\n'):
						self.logger.configuration("   %s: %s" %(_key,_line))
			else:
				for _line in pformat(str(stored),3,3,3).split('\n'):
					self.logger.configuration("   %s: %s" %(_key,_line))
		self.logger.configuration("\n")

		neighbor = Neighbor()
		for local_scope in scope:
			v = local_scope.get('router-id','')
			if v: neighbor.router_id = v
			v = local_scope.get('peer-address','')
			if v: neighbor.peer_address = v
			v = local_scope.get('local-address','')
			if v: neighbor.local_address = v
			v = local_scope.get('local-as','')
			if v: neighbor.local_as = v
			v = local_scope.get('peer-as','')
			if v: neighbor.peer_as = v
			v = local_scope.get('passive',False)
			if v: neighbor.passive = v
			v = local_scope.get('hold-time','')
			if v: neighbor.hold_time = v

			changes = local_scope.get('announce',[])
			messages = local_scope.get('operational',[])

		for local_scope in (scope[0],scope[-1]):
			neighbor.api.receive_packets |= local_scope.get('receive-packets',False)
			neighbor.api.send_packets |= local_scope.get('send-packets',False)
			neighbor.api.receive_routes |= local_scope.get('receive-routes',False)
			neighbor.api.receive_operational |= local_scope.get('receive-operational',False)
			neighbor.api.neighbor_changes |= local_scope.get('neighbor-changes',False)

		if not neighbor.router_id:
			neighbor.router_id = neighbor.local_address

		local_scope = scope[-1]
		neighbor.description = local_scope.get('description','')

		neighbor.md5 = local_scope.get('md5',None)
		neighbor.ttl = local_scope.get('ttl-security',None)
		neighbor.group_updates = local_scope.get('group-updates',None)

		neighbor.route_refresh = local_scope.get('route-refresh',0)
		neighbor.graceful_restart = local_scope.get('graceful-restart',0)
		if neighbor.graceful_restart is None:
			# README: Should it be a subclass of int ?
			neighbor.graceful_restart = int(neighbor.hold_time)
		neighbor.multisession = local_scope.get('multi-session',False)
		neighbor.operational = local_scope.get('capa-operational',False)
		neighbor.add_path = local_scope.get('add-path',0)
		neighbor.flush = local_scope.get('auto-flush',True)
		neighbor.adjribout = local_scope.get('adj-rib-out',True)
		neighbor.asn4 = local_scope.get('asn4',True)
		neighbor.aigp = local_scope.get('aigp',None)

		if neighbor.route_refresh and not neighbor.adjribout:
			self._error = 'incomplete option route-refresh and no adj-rib-out'
			if self.debug: raise
			return False

		missing = neighbor.missing()
		if missing:
			self._error = 'incomplete neighbor, missing %s' % missing
			if self.debug: raise
			return False
		if neighbor.local_address.afi != neighbor.peer_address.afi:
			self._error = 'local-address and peer-address must be of the same family'
			if self.debug: raise
			return False
		if neighbor.peer_address.ip in self._neighbor:
			self._error = 'duplicate peer definition %s' % neighbor.peer_address.ip
			if self.debug: raise
			return False

		openfamilies = local_scope.get('families','everything')
		# announce every family we known
		if neighbor.multisession and openfamilies == 'everything':
			# announce what is needed, and no more, no need to have lots of TCP session doing nothing
			families = neighbor.families()
		elif openfamilies in ('all','everything'):
			families = known_families()
		# only announce what you have as routes
		elif openfamilies == 'minimal':
			families = neighbor.families()
		else:
			families = openfamilies

		# check we are not trying to announce routes without the right MP announcement
		for family in neighbor.families():
			if family not in families:
				afi,safi = family
				self._error = 'Trying to announce a route of type %s,%s when we are not announcing the family to our peer' % (afi,safi)
				if self.debug: raise
				return False

		# add the families to the list of families known
		initial_families = list(neighbor.families())
		for family in families:
			if family not in initial_families	:
				# we are modifying the data used by .families() here
				neighbor.add_family(family)

		if neighbor.group_updates is None:
			neighbor.group_updates = False
			self.logger.configuration('-'*80,'warning')
			self.logger.configuration('group-updates not enabled for peer %s, it surely should, the default will change to true soon' % neighbor.peer_address,'warning')
			self.logger.configuration('-'*80,'warning')

		# create one neighbor object per family for multisession
		if neighbor.multisession:
			for family in neighbor.families():
				# XXX: FIXME: Ok, it works but it takes LOTS of memory ..
				m_neighbor = deepcopy(neighbor)
				for f in neighbor.families():
					if f == family:
						continue
					m_neighbor.rib.outgoing.remove_family(f)

				m_neighbor.make_rib()

				families = neighbor.families()
				for change in changes:
					if change.nlri.family() in families:
						# This add the family to neighbor.families()
						neighbor.rib.outgoing.insert_announced_watchdog(change)
				for message in messages:
					if message.family() in families:
						if message.name == 'ASM':
							neighbor.asm[message.family()] = message
						else:
							neighbor.messages.append(message)
				self._neighbor[m_neighbor.name()] = m_neighbor
		else:
			neighbor.make_rib()
			families = neighbor.families()
			for change in changes:
				if change.nlri.family() in families:
					# This add the family to neighbor.families()
					neighbor.rib.outgoing.insert_announced_watchdog(change)
			for message in messages:
				if message.family() in families:
					if message.name == 'ASM':
						neighbor.asm[message.family()] = message
					else:
						neighbor.messages.append(message)
			self._neighbor[neighbor.name()] = neighbor

		for line in str(neighbor).split('\n'):
			self.logger.configuration(line)
		self.logger.configuration("\n")

		scope.pop(-1)
		return True


	def _multi_neighbor (self,scope,tokens):
		if len(tokens) != 1:
			self._error = 'syntax: neighbor <ip> { <options> }'
			if self.debug: raise
			return False

		address = tokens[0]
		scope.append({})
		try:
			scope[-1]['peer-address'] = Inet(*inet(address))
		except (IndexError,ValueError,socket.error):
			self._error = '"%s" is not a valid IP address' % address
			if self.debug: raise
			return False
		while True:
			r = self._dispatch(scope,'neighbor',['static','flow','process','family','capability','operational'],['description','router-id','local-address','local-as','peer-as','passive','hold-time','add-path','graceful-restart','md5','ttl-security','multi-session','group-updates','asn4','aigp','auto-flush','adj-rib-out'])
			if r is False: return False
			if r is None: return True

	# Command Neighbor

	def _set_router_id (self,scope,command,value):
		try:
			ip = RouterID(value[0])
		except (IndexError,ValueError):
			self._error = '"%s" is an invalid IP address' % ' '.join(value)
			if self.debug: raise
			return False
		scope[-1][command] = ip
		return True

	def _set_description (self,scope,tokens):
		text = ' '.join(tokens)
		if len(text) < 2 or text[0] != '"' or text[-1] != '"' or text[1:-1].count('"'):
			self._error = 'syntax: description "<description>"'
			if self.debug: raise
			return False
		scope[-1]['description'] = text[1:-1]
		return True

	# will raise ValueError if the ASN is not correct
	def _newASN (self,value):
		if value.count('.'):
			high,low = value.split('.',1)
			asn = (int(high) << 16) + int(low)
		else:
			asn = int(value)
		return ASN(asn)

	def _set_asn (self,scope,command,value):
		try:
			scope[-1][command] = self._newASN(value[0])
			return True
		except ValueError:
			self._error = '"%s" is an invalid ASN' % ' '.join(value)
			if self.debug: raise
			return False

	def _set_ip (self,scope,command,value):
		try:
			ip = Inet(*inet(value[0]))
		except (IndexError,ValueError,socket.error):
			self._error = '"%s" is an invalid IP address' % ' '.join(value)
			if self.debug: raise
			return False
		scope[-1][command] = ip
		return True

	def _set_passive (self,scope,command,value):
		if value:
			self._error = '"%s" is an invalid for passive' % ' '.join(value)
			if self.debug: raise
			return False

		scope[-1][command] = True
		return True

	def _set_holdtime (self,scope,command,value):
		try:
			holdtime = HoldTime(value[0])
			if holdtime < 3 and holdtime != 0:
				raise ValueError('holdtime must be zero or at least three seconds')
			if holdtime >= pow(2,16):
				raise ValueError('holdtime must be smaller than %d' % pow(2,16))
			scope[-1][command] = holdtime
			return True
		except ValueError:
			self._error = '"%s" is an invalid hold-time' % ' '.join(value)
			if self.debug: raise
			return False

	def _set_md5 (self,scope,command,value):
		md5 = value[0]
		if len(md5) > 2 and md5[0] == md5[-1] and md5[0] in ['"',"'"]:
			md5 = md5[1:-1]
		if len(md5) > 80:
			self._error = 'md5 password must be no larger than 80 characters'
			if self.debug: raise
			return False
		if not md5:
			self._error = 'md5 requires the md5 password as an argument (quoted or unquoted).  FreeBSD users should use "kernel" as the argument.'
			if self.debug: raise
			return False
		scope[-1][command] = md5
		return True

	def _set_ttl (self,scope,command,value):
		if not len(value):
			scope[-1][command] = self.TTL_SECURITY
			return True
		try:
			# README: Should it be a subclass of int ?
			ttl = int(value[0])
			if ttl < 0:
				raise ValueError('ttl-security can not be negative')
			if ttl >= 255:
				raise ValueError('ttl must be smaller than 256')
			scope[-1][command] = ttl
			return True
		except ValueError:
			self._error = '"%s" is an invalid ttl-security' % ' '.join(value)
			if self.debug: raise
			return False
		return True

	#  Group Static ................

	def _multi_static (self,scope,tokens):
		if len(tokens) != 0:
			self._error = 'syntax: static { route; route; ... }'
			if self.debug: raise
			return False
		while True:
			r = self._dispatch(scope,'static',['route',],['route',])
			if r is False: return False
			if r is None: return True

	# Group Route  ........

	def _split_last_route (self,scope):
		# if the route does not need to be broken in smaller routes, return
		change = scope[-1]['announce'][-1]
		if not AttributeID.INTERNAL_SPLIT in change.attributes:
			return True

		# ignore if the request is for an aggregate, or the same size
		mask = change.nlri.mask
		split = change.attributes[AttributeID.INTERNAL_SPLIT]
		if mask >= split:
			return True

		# get a local copy of the route
		change = scope[-1]['announce'].pop(-1)

		# calculate the number of IP in the /<size> of the new route
		increment = pow(2,(len(change.nlri.packed)*8) - split)
		# how many new routes are we going to create from the initial one
		number = pow(2,split - change.nlri.mask)

		# convert the IP into a integer/long
		ip = 0
		for c in change.nlri.packed:
			ip = ip << 8
			ip += ord(c)

		afi = change.nlri.afi
		safi = change.nlri.safi
		# Really ugly
		labels = change.nlri.labels
		rd = change.nlri.rd
		path_info = change.nlri.path_info
		nexthop = change.nlri.nexthop

		change.mask = split
		change.nlri = None
		# generate the new routes
		for _ in range(number):
			# update ip to the next route, this recalculate the "ip" field of the Inet class
			nlri = NLRI(afi,safi,pack_int(afi,ip,split),split,nexthop,OUT.announce)
			nlri.labels = labels
			nlri.rd = rd
			nlri.path_info = path_info
			# next ip
			ip += increment
			# save route
			scope[-1]['announce'].append(Change(nlri,change.attributes))

		return True

	def _insert_static_route (self,scope,tokens):
		try:
			ip = tokens.pop(0)
		except IndexError:
			self._error = self._str_route_error
			if self.debug: raise
			return False
		try:
			ip,mask = ip.split('/')
			mask = int(mask)
		except ValueError:
			mask = 32
		try:
			# nexthop must be false and its str return nothing .. an empty string does that
			update = Change(NLRI(*inet(ip),mask=mask,nexthop=None,action=OUT.announce),Attributes())

			if len(Prefix.pack(update.nlri)) != len(update.nlri):
				self._error = 'invalid mask for this prefix %s' % str(update.nlri)
				if self.debug: raise
				return False
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

		if 'announce' not in scope[-1]:
			scope[-1]['announce'] = []

		scope[-1]['announce'].append(update)
		return True

	def _check_static_route (self,scope):
		update = scope[-1]['announce'][-1]
		if not update.nlri.nexthop:
			self._error = 'syntax: route <ip>/<mask> { next-hop <ip>; }'
			if self.debug: raise
			return False
		return True

	def _multi_static_route (self,scope,tokens):
		if len(tokens) != 1:
			self._error = self._str_route_error
			if self.debug: raise
			return False

		if not self._insert_static_route(scope,tokens):
			return False

		while True:
			r = self._dispatch(scope,'route',[],['next-hop','origin','as-path','as-sequence','med','aigp','local-preference','atomic-aggregate','aggregator','path-information','community','originator-id','cluster-list','extended-community','split','label','rd','route-distinguisher','watchdog','withdraw'])
			if r is False: return False
			if r is None: return self._split_last_route(scope)

	def _single_static_route (self,scope,tokens):
		if len(tokens) <3:
			return False

		if not self._insert_static_route(scope,tokens):
			return False

		while len(tokens):
			command = tokens.pop(0)
			if command == 'withdraw':
				if self._route_withdraw(scope,tokens):
					continue
				return False

			if len(tokens) < 1:
				return False

			if command == 'next-hop':
				if self._route_next_hop(scope,tokens):
					continue
				return False
			if command == 'origin':
				if self._route_origin(scope,tokens):
					continue
				return False
			if command == 'as-path':
				if self._route_aspath(scope,tokens):
					continue
				return False
			if command == 'as-sequence':
				if self._route_aspath(scope,tokens):
					continue
				return False
			if command == 'med':
				if self._route_med(scope,tokens):
					continue
				return False
			if command == 'aigp':
				if self._route_aigp(scope,tokens):
					continue
				return False
			if command == 'local-preference':
				if self._route_local_preference(scope,tokens):
					continue
				return False
			if command == 'atomic-aggregate':
				if self._route_atomic_aggregate(scope,tokens):
					continue
				return False
			if command == 'aggregator':
				if self._route_aggregator(scope,tokens):
					continue
				return False
			if command == 'path-information':
				if self._route_path_information(scope,tokens):
					continue
				return False
			if command == 'community':
				if self._route_community(scope,tokens):
					continue
				return False
			if command == 'originator-id':
				if self._route_originator_id(scope,tokens):
					continue
				return False
			if command == 'cluster-list':
				if self._route_cluster_list(scope,tokens):
					continue
				return False
			if command == 'extended-community':
				if self._route_extended_community(scope,tokens):
					continue
				return False
			if command == 'split':
				if self._route_split(scope,tokens):
					continue
				return False
			if command == 'label':
				if self._route_label(scope,tokens):
					continue
				return False
			if command in ('rd','route-distinguisher'):
				if self._route_rd(scope,tokens,SAFI.mpls_vpn):
					continue
				return False
			if command == 'watchdog':
				if self._route_watchdog(scope,tokens):
					continue
				return False
			if command == 'attribute':
				if self._route_generic_attribute(scope,tokens):
					continue
				return False
			return False

		if not self._check_static_route(scope):
			return False

		return self._split_last_route(scope)

	# Command Route

	def _route_generic_attribute (self,scope,tokens):
		try:
			start = tokens.pop(0)
			code = tokens.pop(0).lower()
			flag = tokens.pop(0).lower()
			data = tokens.pop(0).lower()
			end = tokens.pop(0)

			if (start,end) != ('[',']'):
				self._error = self._str_route_error
				if self.debug: raise
				return False

			if not code.startswith('0x'):
				self._error = self._str_route_error
				if self.debug: raise
				return False
			code = int(code[2:],16)

			if not flag.startswith('0x'):
				self._error = self._str_route_error
				if self.debug: raise
				return False
			flag = int(flag[2:],16)

			if not data.startswith('0x'):
				self._error = self._str_route_error
				if self.debug: raise
				return False
			raw = ''
			for i in range(2,len(data),2):
				raw += chr(int(data[i:i+2],16))

			for (ID,klass) in Attributes.lookup.iteritems():
				if code == ID and flag == klass.FLAG:
					scope[-1]['announce'][-1].attributes.add(klass(raw))
					return True

			scope[-1]['announce'][-1].attributes.add(UnknownAttribute(code,flag,raw))
			return True
		except (IndexError,ValueError):
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _route_next_hop (self,scope,tokens):
		if scope[-1]['announce'][-1].attributes.has(AttributeID.NEXT_HOP):
			self._error = self._str_route_error
			if self.debug: raise
			return False

		try:
			# next-hop self is unsupported
			ip = tokens.pop(0)
			if ip.lower() == 'self':
				if 'local-address' in scope[-1]:
					la = scope[-1]['local-address']
				elif self._nexthopself:
					la = self._nexthopself
				else:
					self._error = 'next-hop self can only be specified with a neighbor'
					if self.debug: raise ValueError(self._error)
					return False
				nh = la.pack()
			else:
				nh = pton(ip)

			change = scope[-1]['announce'][-1]
			nlri = change.nlri
			afi = nlri.afi
			safi = nlri.safi

			nlri.nexthop = cachedNextHop(nh)

			if afi == AFI.ipv4 and safi in (SAFI.unicast,SAFI.multicast):
				change.attributes.add(cachedNextHop(nh))

			return True
		except:
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _route_origin (self,scope,tokens):
		try:
			data = tokens.pop(0).lower()
			if data == 'igp':
				scope[-1]['announce'][-1].attributes.add(Origin(Origin.IGP))
				return True
			if data == 'egp':
				scope[-1]['announce'][-1].attributes.add(Origin(Origin.EGP))
				return True
			if data == 'incomplete':
				scope[-1]['announce'][-1].attributes.add(Origin(Origin.INCOMPLETE))
				return True
			self._error = self._str_route_error
			if self.debug: raise
			return False
		except IndexError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _route_aspath (self,scope,tokens):
		as_seq = []
		as_set = []
		asn = tokens.pop(0)
		inset = False
		try:
			if asn == '[':
				while True:
					try:
						asn = tokens.pop(0)
					except IndexError:
						self._error = self._str_route_error
						if self.debug: raise
						return False
					if asn == ',':
						continue
					if asn in ('(','['):
						inset = True
						while True:
							try:
								asn = tokens.pop(0)
							except IndexError:
								self._error = self._str_route_error
								if self.debug: raise
								return False
							if asn == ')':
								break
							as_set.append(self._newASN(asn))
					if asn == ')':
						inset = False
						continue
					if asn == ']':
						if inset:
							inset = False
							continue
						break
					as_seq.append(self._newASN(asn))
			else:
				as_seq.append(self._newASN(asn))
		except (IndexError,ValueError):
			self._error = self._str_route_error
			if self.debug: raise
			return False
		scope[-1]['announce'][-1].attributes.add(ASPath(as_seq,as_set))
		return True

	def _route_med (self,scope,tokens):
		try:
			scope[-1]['announce'][-1].attributes.add(MED(pack('!L',int(tokens.pop(0)))))
			return True
		except (IndexError,ValueError):
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _route_aigp (self,scope,tokens):
		try:
			scope[-1]['announce'][-1].attributes.add(AIGP('\x01\x00\x0b' + pack('!Q',int(tokens.pop(0)))))
			return True
		except (IndexError,ValueError):
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _route_local_preference (self,scope,tokens):
		try:
			scope[-1]['announce'][-1].attributes.add(LocalPreference(pack('!L',int(tokens.pop(0)))))
			return True
		except (IndexError,ValueError):
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _route_atomic_aggregate (self,scope,tokens):
		try:
			scope[-1]['announce'][-1].attributes.add(AtomicAggregate())
			return True
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _route_aggregator (self,scope,tokens):
		try:
			if tokens:
				if tokens.pop(0) != '(':
					raise ValueError('invalid aggregator syntax')
				asn,address = tokens.pop(0).split(':')
				if tokens.pop(0) != ')':
					raise ValueError('invalid aggregator syntax')
				local_as = ASN(asn)
				local_address = RouterID(address)
			else:
				local_as = scope[-1]['local-as']
				local_address = scope[-1]['local-address']
		except (ValueError,IndexError):
			self._error = self._str_route_error
			if self.debug: raise
			return False
		except KeyError:
			self._error = 'local-as and/or local-address missing from neighbor/group to make aggregator'
			if self.debug: raise
			return False
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

		scope[-1]['announce'][-1].attributes.add(Aggregator(local_as.pack(True)+local_address.pack()))
		return True

	def _route_path_information (self,scope,tokens):
		try:
			pi = tokens.pop(0)
			if pi.isdigit():
				scope[-1]['announce'][-1].nlri.path_info = PathInfo(integer=int(pi))
			else:
				scope[-1]['announce'][-1].nlri.path_info = PathInfo(ip=pi)
			return True
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _parse_community (self,scope,data):
		separator = data.find(':')
		if separator > 0:
			prefix = int(data[:separator])
			suffix = int(data[separator+1:])
			if prefix >= pow(2,16):
				raise ValueError('invalid community %s (prefix too large)' % data)
			if suffix >= pow(2,16):
				raise ValueError('invalid community %s (suffix too large)' % data)
			return cachedCommunity(pack('!L',(prefix<<16) + suffix))
		elif len(data) >=2 and data[1] in 'xX':
			value = long(data,16)
			if value >= pow(2,32):
				raise ValueError('invalid community %s (too large)' % data)
			return cachedCommunity(pack('!L',value))
		else:
			low = data.lower()
			if low == 'no-export':
				return cachedCommunity(Community.NO_EXPORT)
			elif low == 'no-advertise':
				return cachedCommunity(Community.NO_ADVERTISE)
			elif low == 'no-export-subconfed':
				return cachedCommunity(Community.NO_EXPORT_SUBCONFED)
			# no-peer is not a correct syntax but I am sure someone will make the mistake :)
			elif low == 'nopeer' or low == 'no-peer':
				return cachedCommunity(Community.NO_PEER)
			elif data.isdigit():
				value = unpack('!L',data)[0]
				if value >= pow(2,32):
					raise ValueError('invalid community %s (too large)' % data)
					return cachedCommunity(pack('!L',value))
			else:
				raise ValueError('invalid community name %s' % data)

	def _route_originator_id (self,scope,tokens):
		try:
			scope[-1]['announce'][-1].attributes.add(OriginatorID(*inet(tokens.pop(0))))
			return True
		except:
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _route_cluster_list (self,scope,tokens):
		_list = ''
		clusterid = tokens.pop(0)
		try:
			if clusterid == '[':
				while True:
					try:
						clusterid = tokens.pop(0)
					except IndexError:
						self._error = self._str_route_error
						if self.debug: raise
						return False
					if clusterid == ']':
						break
					_list += ''.join([chr(int(_)) for _ in clusterid.split('.')])
			else:
				_list = ''.join([chr(int(_)) for _ in clusterid.split('.')])
			if not _list:
				raise ValueError('no cluster-id in the cluster-list')
			clusterlist = ClusterList(_list)
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False
		scope[-1]['announce'][-1].attributes.add(clusterlist)
		return True

	def _route_community (self,scope,tokens):
		communities = Communities()
		community = tokens.pop(0)
		try:
			if community == '[':
				while True:
					try:
						community = tokens.pop(0)
					except IndexError:
						self._error = self._str_route_error
						if self.debug: raise
						return False
					if community == ']':
						break
					communities.add(self._parse_community(scope,community))
			else:
				communities.add(self._parse_community(scope,community))
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False
		scope[-1]['announce'][-1].attributes.add(communities)
		return True

	def _parse_extended_community (self,scope,data):
		if data[:2].lower() == '0x':
			try:
				raw = ''
				for i in range(2,len(data),2):
					raw += chr(int(data[i:i+2],16))
			except ValueError:
				raise ValueError('invalid extended community %s' % data)
			if len(raw) != 8:
				raise ValueError('invalid extended community %s' % data)
			return ECommunity(raw)
		elif data.count(':'):
			return to_ExtendedCommunity(data)
		else:
			raise ValueError('invalid extended community %s - lc+gc' % data)

	def _route_extended_community (self,scope,tokens):
		extended_communities = ECommunities()
		extended_community = tokens.pop(0)
		try:
			if extended_community == '[':
				while True:
					try:
						extended_community = tokens.pop(0)
					except IndexError:
						self._error = self._str_route_error
						if self.debug: raise
						return False
					if extended_community == ']':
						break
					extended_communities.add(self._parse_extended_community(scope,extended_community))
			else:
				extended_communities.add(self._parse_extended_community(scope,extended_community))
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False
		scope[-1]['announce'][-1].attributes.add(extended_communities)
		return True


	def _route_split (self,scope,tokens):
		try:
			size = tokens.pop(0)
			if not size or size[0] != '/':
				raise ValueError('route "as" require a CIDR')
			scope[-1]['announce'][-1].attributes.add(Split(int(size[1:])))
			return True
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _route_label (self,scope,tokens):
		labels = []
		label = tokens.pop(0)
		try:
			if label == '[':
				while True:
					try:
						label = tokens.pop(0)
					except IndexError:
						self._error = self._str_route_error
						if self.debug: raise
						return False
					if label == ']':
						break
					labels.append(int(label))
			else:
				labels.append(int(label))
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

		nlri = scope[-1]['announce'][-1].nlri
		if not nlri.safi.has_label():
			nlri.safi = SAFI(SAFI.nlri_mpls)
		nlri.labels = Labels(labels)
		return True

	def _route_rd (self,scope,tokens,safi):
		try:
			try:
				data = tokens.pop(0)
			except IndexError:
				self._error = self._str_route_error
				if self.debug: raise
				return False

			separator = data.find(':')
			if separator > 0:
				prefix = data[:separator]
				suffix = int(data[separator+1:])

			if '.' in prefix:
				bytes = [chr(0),chr(1)]
				bytes.extend([chr(int(_)) for _ in prefix.split('.')])
				bytes.extend([chr(suffix>>8),chr(suffix&0xFF)])
				rd = ''.join(bytes)
			else:
				number = int(prefix)
				if number < pow(2,16) and suffix < pow(2,32):
					rd = chr(0) + chr(0) + pack('!H',number) + pack('!L',suffix)
				elif number < pow(2,32) and suffix < pow(2,16):
					rd = chr(0) + chr(2) + pack('!L',number) + pack('!H',suffix)
				else:
					raise ValueError('invalid route-distinguisher %s' % data)

			nlri = scope[-1]['announce'][-1].nlri
			# overwrite nlri-mpls
			nlri.safi = SAFI(safi)
			nlri.rd = RouteDistinguisher(rd)
			return True
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False


	# Group Flow  ........

	def _multi_flow (self,scope,tokens):
		if len(tokens) != 0:
			self._error = self._str_flow_error
			if self.debug: raise
			return False

		while True:
			r = self._dispatch(scope,'flow',['route',],[])
			if r is False: return False
			if r is None: break
		return True

	def _insert_flow_route (self,scope,tokens=None):
		if self._flow_state != 'out':
			self._error = self._str_flow_error
			if self.debug: raise
			return False

		self._flow_state = 'match'

		try:
			attributes = Attributes()
			attributes[AttributeID.EXTENDED_COMMUNITY] = ECommunities()
			flow = Change(FlowNLRI(),attributes)
		except ValueError:
			self._error = self._str_flow_error
			if self.debug: raise
			return False

		if 'announce' not in scope[-1]:
			scope[-1]['announce'] = []

		scope[-1]['announce'].append(flow)
		return True

	def _check_flow_route (self,scope):
		self.logger.configuration('warning: no check on flows are implemented')
		return True

	def _multi_flow_route (self,scope,tokens):
		if len(tokens) > 1:
			self._error = self._str_flow_error
			if self.debug: raise
			return False

		if not self._insert_flow_route(scope):
			return False

		while True:
			r = self._dispatch(scope,'flow-route',['match','then'],['rd','route-distinguisher','next-hop'])
			if r is False: return False
			if r is None: break

		if self._flow_state != 'out':
			self._error = self._str_flow_error
			if self.debug: raise
			return False

		return True

	# ..........................................

	def _multi_match (self,scope,tokens):
		if len(tokens) != 0:
			self._error = self._str_flow_error
			if self.debug: raise
			return False

		if self._flow_state != 'match':
			self._error = self._str_flow_error
			if self.debug: raise
			return False

		self._flow_state = 'then'

		while True:
			r = self._dispatch(scope,'flow-match',[],['source','destination','port','source-port','destination-port','protocol','next-header','tcp-flags','icmp-type','icmp-code','fragment','dscp','traffic-class','packet-length','flow-label'])
			if r is False: return False
			if r is None: break
		return True

	def _multi_then (self,scope,tokens):
		if len(tokens) != 0:
			self._error = self._str_flow_error
			if self.debug: raise
			return False

		if self._flow_state != 'then':
			self._error = self._str_flow_error
			if self.debug: raise
			return False

		self._flow_state = 'out'

		while True:
			r = self._dispatch(scope,'flow-then',[],['accept','discard','rate-limit','redirect','copy','redirect-to-nexthop','mark','action','community'])
			if r is False: return False
			if r is None: break
		return True

	# Command Flow

	def _flow_source (self,scope,tokens):
		try:
			data = tokens.pop(0)
			if data.count('/') == 1:
				ip,netmask = data.split('/')
				raw = ''.join(chr(int(_)) for _ in ip.split('.'))

				if not scope[-1]['announce'][-1].nlri.add(Flow4Source(raw,int(netmask))):
					self._error = 'Flow can only have one destination'
					if self.debug: raise ValueError(self._error)
					return False

			else:
				ip,netmask,offset = data.split('/')
				afi,safi,raw = inet(ip)
				change = scope[-1]['announce'][-1]
				# XXX: This is ugly
				change.nlri.afi = AFI(AFI.ipv6)
				if not change.nlri.add(Flow6Source(raw,int(netmask),int(offset))):
					self._error = 'Flow can only have one destination'
					if self.debug: raise ValueError(self._error)
					return False
			return True

		except (IndexError,ValueError):
			self._error = self._str_flow_error
			if self.debug: raise
			return False


	def _flow_destination (self,scope,tokens):
		try:
			data = tokens.pop(0)
			if data.count('/') == 1:
				ip,netmask = data.split('/')
				raw = ''.join(chr(int(_)) for _ in ip.split('.'))

				if not scope[-1]['announce'][-1].nlri.add(Flow4Destination(raw,int(netmask))):
					self._error = 'Flow can only have one destination'
					if self.debug: raise ValueError(self._error)
					return False

			else:
				ip,netmask,offset = data.split('/')
				afi,safi,raw = inet(ip)
				change = scope[-1]['announce'][-1]
				# XXX: This is ugly
				change.nlri.afi = AFI(AFI.ipv6)
				if not change.nlri.add(Flow6Destination(raw,int(netmask),int(offset))):
					self._error = 'Flow can only have one destination'
					if self.debug: raise ValueError(self._error)
					return False
			return True

		except (IndexError,ValueError):
			self._error = self._str_flow_error
			if self.debug: raise
			return False


	# to parse the port configuration of flow

	def _operator (self,string):
		try:
			if string[0] == '=':
				return NumericOperator.EQ,string[1:]
			elif string[0] == '>':
				operator = NumericOperator.GT
			elif string[0] == '<':
				operator = NumericOperator.LT
			else:
				raise ValueError('Invalid operator in test %s' % string)
			if string[1] == '=':
				operator += NumericOperator.EQ
				return operator,string[2:]
			else:
				return operator,string[1:]
		except IndexError:
			raise('Invalid expression (too short) %s' % string)

	def _value (self,string):
		l = 0
		for c in string:
			if c not in ['&',]:
				l += 1
				continue
			break
		return string[:l],string[l:]

	# parse =80 or >80 or <25 or &>10<20
	def _flow_generic_expression (self,scope,tokens,klass):
		try:
			for test in tokens:
				AND = BinaryOperator.NOP
				while test:
					operator,_ = self._operator(test)
					value,test = self._value(_)
					nlri = scope[-1]['announce'][-1].nlri
					# XXX : should do a check that the rule is valid for the family
					nlri.add(klass(AND|operator,klass.converter(value)))
					if test:
						if test[0] == '&':
							AND = BinaryOperator.AND
							test = test[1:]
							if not test:
								raise ValueError("Can not finish an expresion on an &")
						else:
							raise ValueError("Unknown binary operator %s" % test[0])
			return True
		except ValueError,e:
			self._error = self._str_route_error + str(e)
			if self.debug: raise
			return False

	# parse [ content1 content2 content3 ]
	def _flow_generic_list (self,scope,tokens,klass):
		try:
			name = tokens.pop(0)
			AND = BinaryOperator.NOP
			if name == '[':
				while True:
					name = tokens.pop(0)
					if name == ']':
						break
					try:
						nlri = scope[-1]['announce'][-1].nlri
						# XXX : should do a check that the rule is valid for the family
						nlri.add(klass(NumericOperator.EQ|AND,klass.converter(name)))
					except IndexError:
						self._error = self._str_flow_error
						if self.debug: raise
						return False
			else:
				scope[-1]['announce'][-1].nlri.add(klass(NumericOperator.EQ|AND,klass.converter(name)))
		except (IndexError,ValueError):
			self._error = self._str_flow_error
			if self.debug: raise
			return False
		return True

	def _flow_generic_condition (self,scope,tokens,klass):
		if tokens[0][0] in ['=','>','<']:
			return self._flow_generic_expression(scope,tokens,klass)
		return self._flow_generic_list(scope,tokens,klass)

	def _flow_route_anyport (self,scope,tokens):
		return self._flow_generic_condition(scope,tokens,FlowAnyPort)

	def _flow_route_source_port (self,scope,tokens):
		return self._flow_generic_condition(scope,tokens,FlowSourcePort)

	def _flow_route_destination_port (self,scope,tokens):
		return self._flow_generic_condition(scope,tokens,FlowDestinationPort)

	def _flow_route_packet_length (self,scope,tokens):
		return self._flow_generic_condition(scope,tokens,FlowPacketLength)

	def _flow_route_tcp_flags (self,scope,tokens):
		return self._flow_generic_list(scope,tokens,FlowTCPFlag)

	def _flow_route_protocol (self,scope,tokens):
		return self._flow_generic_list(scope,tokens,FlowIPProtocol)

	def _flow_route_next_header (self,scope,tokens):
		return self._flow_generic_list(scope,tokens,FlowNextHeader)

	def _flow_route_icmp_type (self,scope,tokens):
		return self._flow_generic_list(scope,tokens,FlowICMPType)

	def _flow_route_icmp_code (self,scope,tokens):
		return self._flow_generic_list(scope,tokens,FlowICMPCode)

	def _flow_route_fragment (self,scope,tokens):
		return self._flow_generic_list(scope,tokens,FlowFragment)

	def _flow_route_dscp (self,scope,tokens):
		return self._flow_generic_condition(scope,tokens,FlowDSCP)

	def _flow_route_traffic_class (self,scope,tokens):
		return self._flow_generic_condition(scope,tokens,FlowTrafficClass)

	def _flow_route_flow_label (self,scope,tokens):
		return self._flow_generic_condition(scope,tokens,FlowFlowLabel)

	def _flow_route_next_hop (self,scope,tokens):
		try:
			change = scope[-1]['announce'][-1]

			if change.nlri.nexthop:
				self._error = self._str_flow_error
				if self.debug: raise
				return False

			ip = tokens.pop(0)
			nh = pton(ip)
			change.nlri.nexthop = cachedNextHop(nh)
			return True

		except (IndexError,ValueError):
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _flow_route_accept (self,scope,tokens):
		return True

	def _flow_route_discard (self,scope,tokens):
		# README: We are setting the ASN as zero as that what Juniper (and Arbor) did when we created a local flow route
		try:
			scope[-1]['announce'][-1].attributes[AttributeID.EXTENDED_COMMUNITY].add(to_FlowTrafficRate(ASN(0),0))
			return True
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _flow_route_rate_limit (self,scope,tokens):
		# README: We are setting the ASN as zero as that what Juniper (and Arbor) did when we created a local flow route
		try:
			speed = int(tokens[0])
			if speed < 9600 and speed != 0:
				self.logger.configuration("rate-limiting flow under 9600 bytes per seconds may not work",'warning')
			if speed > 1000000000000:
				speed = 1000000000000
				self.logger.configuration("rate-limiting changed for 1 000 000 000 000 bytes from %s" % tokens[0],'warning')
			scope[-1]['announce'][-1].attributes[AttributeID.EXTENDED_COMMUNITY].add(to_FlowTrafficRate(ASN(0),speed))
			return True
		except ValueError:
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _flow_route_redirect (self,scope,tokens):
		try:
			if tokens[0].count(':') == 1:
				prefix,suffix=tokens[0].split(':',1)
				if prefix.count('.'):
					ip = prefix.split('.')
					if len(ip) != 4:
						raise ValueError('invalid IP %s' % prefix)
					ipn = 0
					while ip:
						ipn <<= 8
						ipn += int(ip.pop(0))
					number = int(suffix)
					if number >= pow(2,16):
						raise ValueError('number is too large, max 16 bits %s' % number)
					scope[-1]['announce'][-1].attributes[AttributeID.EXTENDED_COMMUNITY].add(to_FlowRedirectVRFIP(ipn,number))
					return True
				else:
					asn = int(prefix)
					route_target = int(suffix)
					if asn >= pow(2,16):
						raise ValueError('asn is a 32 bits number, it can only be 16 bit %s' % route_target)
					if route_target >= pow(2,32):
						raise ValueError('route target is a 32 bits number, value too large %s' % route_target)
					scope[-1]['announce'][-1].attributes[AttributeID.EXTENDED_COMMUNITY].add(to_FlowRedirectVRFASN(asn,route_target))
					return True
			else:
				change = scope[-1]['announce'][-1]
				if change.nlri.nexthop:
					self._error = self._str_flow_error
					if self.debug: raise
					return False

				ip = tokens.pop(0)
				nh = pton(ip)
				change.nlri.nexthop = cachedNextHop(nh)
				change.attributes[AttributeID.EXTENDED_COMMUNITY].add(to_FlowRedirect(False))
				return True

		except (IndexError,ValueError):
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _flow_route_redirect_next_hop (self,scope,tokens):
		try:
			change = scope[-1]['announce'][-1]

			if not change.nlri.nexthop:
				self._error = self._str_flow_error
				if self.debug: raise
				return False

			change.attributes[AttributeID.EXTENDED_COMMUNITY].add(to_FlowRedirect(False))
			return True

		except (IndexError,ValueError):
			self._error = self._str_route_error
			if self.debug: raise
			return False

	def _flow_route_copy (self,scope,tokens):
		# README: We are setting the ASN as zero as that what Juniper (and Arbor) did when we created a local flow route
		try:
			if scope[-1]['announce'][-1].attributes.has(AttributeID.NEXT_HOP):
				self._error = self._str_flow_error
				if self.debug: raise
				return False

			ip = tokens.pop(0)
			nh = pton(ip)
			change = scope[-1]['announce'][-1]
			change.nlri.nexthop = cachedNextHop(nh)
			change.attributes[AttributeID.EXTENDED_COMMUNITY].add(to_FlowRedirect(True))
			return True

		except (IndexError,ValueError):
			self._error = self._str_flow_error
			if self.debug: raise
			return False

	def _flow_route_mark (self,scope,tokens):
		try:
			dscp = int(tokens.pop(0))

			if dscp < 0 or dscp > 0b111111:
				self._error = self._str_flow_error
				if self.debug: raise
				return False

			change = scope[-1]['announce'][-1]
			change.attributes[AttributeID.EXTENDED_COMMUNITY].add(to_FlowTrafficMark(dscp))
			return True

		except (IndexError,ValueError):
			self._error = self._str_flow_error
			if self.debug: raise
			return False

	def _flow_route_action (self,scope,tokens):
		try:
			action = tokens.pop(0)
			sample = 'sample' in action
			terminal = 'terminal' in action

			if not sample and not terminal:
				self._error = self._str_flow_error
				if self.debug: raise
				return False

			change = scope[-1]['announce'][-1]
			change.attributes[AttributeID.EXTENDED_COMMUNITY].add(to_FlowTrafficAction(sample,terminal))
			return True
		except (IndexError,ValueError):
			self._error = self._str_flow_error
			if self.debug: raise
			return False

	#  Group Operational ................

	def _multi_operational (self,scope,tokens):
		if len(tokens) != 0:
			self._error = 'syntax: operational { command; command; ... }'
			if self.debug: raise
			return False
		while True:
			r = self._dispatch(scope,'operational',[],['asm',])
			if r is False: return False
			if r is None: return True


	def _single_operational_asm (self,scope,value):
		#return self._single_advisory(Advisory.ASM,scope,value)
		return self._single_operational(Advisory.ASM,scope,['afi','safi','advisory'],value)

	def _single_operational (self,klass,scope,parameters,value):
		def utf8 (string): return string.encode('utf-8')[1:-1]

		convert = {
			'afi': AFI.value,
			'safi': SAFI.value,
			'sequence': int,
			'counter': long,
			'advisory': utf8
		}

		def valid    (_): return True
		def u32      (_): return int(_) <= 0xFFFFFFFF
		def u64      (_): return long(_) <= 0xFFFFFFFFFFFFFFFF
		def advisory (_): return len(_.encode('utf-8')) <= MAX_ADVISORY + 2  # the two quotes

		validate = {
			'afi': AFI.value,
			'safi': SAFI.value,
			'sequence': u32,
			'counter': u64,
		}

		number = len(parameters)*2
		tokens = formated(value).split(' ',number-1)
		if len(tokens) != number:
			self._error = 'invalid operational syntax, wrong number of arguments'
			return False

		data = {}

		while tokens and parameters:
			command = tokens.pop(0).lower()
			value = tokens.pop(0)

			if command == 'router-id':
				if isipv4(value):
					data['routerid'] = RouterID(value)
				else:
					self._error = 'invalid operational value for %s' % command
					return False
				continue

			expected = parameters.pop(0)

			if command != expected:
				self._error = 'invalid operational syntax, unknown argument %s' % command
				return False
			if not validate.get(command,valid)(value):
				self._error = 'invalid operational value for %s' % command
				return False

			data[command] = convert[command](value)

		if tokens or parameters:
			self._error = 'invalid advisory syntax, missing argument(s) %s' % ', '.join(parameters)
			return False

		if 'routerid' not in data:
			data['routerid'] = None

		if 'operational' not in scope[-1]:
			scope[-1]['operational'] = []

		# iterate on each family for the peer if multiprotocol is set.
		scope[-1]['operational'].append(klass(**data))
		return True


	# ..............................

	def decode (self,update):
		# self check to see if we can decode what we encode
		import sys
		from exabgp.bgp.message.update.factory import UpdateFactory
		from exabgp.bgp.message.open import Open
		from exabgp.bgp.message.open.capability import Capabilities
		from exabgp.bgp.message.open.capability.negotiated import Negotiated
		from exabgp.bgp.message.open.capability.id import CapabilityID
		from exabgp.bgp.message.notification import Notify
		from exabgp.reactor.api.encoding import JSON

		self.logger._parser = True

		self.logger.parser('\ndecoding routes in configuration')

		n = self.neighbor[self.neighbor.keys()[0]]

		path = {}
		for f in known_families():
			if n.add_path:
				path[f] = n.add_path

		capa = Capabilities().new(n,False)
		capa[CapabilityID.ADD_PATH] = path
		capa[CapabilityID.MULTIPROTOCOL_EXTENSIONS] = n.families()

		o1 = Open(4,n.local_as,str(n.local_address),capa,180)
		o2 = Open(4,n.peer_as,str(n.peer_address),capa,180)
		negotiated = Negotiated(n)
		negotiated.sent(o1)
		negotiated.received(o2)
		#grouped = False

		raw = ''.join(chr(int(_,16)) for _ in (update[i*2:(i*2)+2] for i in range(len(update)/2)))

		while raw:
			if raw.startswith('\xff'*16):
				kind = ord(raw[18])
				size = (ord(raw[16]) << 16) + (ord(raw[17]))

				injected,raw = raw[19:size],raw[size:]

				if kind == 2:
					self.logger.parser('the message is an update')
					factory = UpdateFactory
					decoding = 'update'
				else:
					self.logger.parser('the message is not an update (%d) - aborting' % kind)
					sys.exit(1)
			else:
				self.logger.parser('header missing, assuming this message is ONE update')
				factory = UpdateFactory
				decoding = 'update'
				injected,raw = raw,''

			try:
				# This does not take the BGP header - let's assume we will not break that :)
				update = factory(negotiated,injected)
			except KeyboardInterrupt:
				raise
			except Notify,e:
				self.logger.parser('could not parse the message')
				self.logger.parser(str(e))
				sys.exit(1)
			except Exception,e:
				self.logger.parser('could not parse the message')
				self.logger.parser(str(e))
				sys.exit(1)

			self.logger.parser('')  # new line
			for number in range(len(update.nlris)):
				change = Change(update.nlris[number],update.attributes)
				self.logger.parser('decoded %s %s %s' % (decoding,change.nlri.action,change.extensive()))
			self.logger.parser('update json %s' % JSON('1.0').update(str(n.peer_address),update))
		import sys
		sys.exit(0)


# ASN4 merge test
#		injected = ['0x0', '0x0', '0x0', '0x2e', '0x40', '0x1', '0x1', '0x0', '0x40', '0x2', '0x8', '0x2', '0x3', '0x78', '0x14', '0xab', '0xe9', '0x5b', '0xa0', '0x40', '0x3', '0x4', '0x52', '0xdb', '0x0', '0x4f', '0xc0', '0x8', '0x8', '0x78', '0x14', '0xc9', '0x46', '0x78', '0x14', '0xfd', '0xea', '0xe0', '0x11', '0xa', '0x2', '0x2', '0x0', '0x0', '0xab', '0xe9', '0x0', '0x3', '0x5', '0x54', '0x17', '0x9f', '0x65', '0x9e', '0x15', '0x9f', '0x65', '0x80', '0x18', '0x9f', '0x65', '0x9f']
# EOR
#		injected = '\x00\x00\x00\x07\x90\x0f\x00\x03\x00\x02\x01'

	def selfcheck (self):
		import sys
		# self check to see if we can decode what we encode
		from exabgp.util.od import od
		from exabgp.bgp.message.update import Update
		from exabgp.bgp.message.update.factory import UpdateFactory
		from exabgp.bgp.message.open import Open
		from exabgp.bgp.message.open.capability import Capabilities
		from exabgp.bgp.message.open.capability.negotiated import Negotiated
		from exabgp.bgp.message.open.capability.id import CapabilityID
		from exabgp.bgp.message.notification import Notify

		from exabgp.rib.change import Change

		self.logger._parser = True

		self.logger.parser('\ndecoding routes in configuration')

		n = self.neighbor[self.neighbor.keys()[0]]

		path = {}
		for f in known_families():
			if n.add_path:
				path[f] = n.add_path

		capa = Capabilities().new(n,False)
		capa[CapabilityID.ADD_PATH] = path
		capa[CapabilityID.MULTIPROTOCOL_EXTENSIONS] = n.families()

		o1 = Open(4,n.local_as,str(n.local_address),capa,180)
		o2 = Open(4,n.peer_as,str(n.peer_address),capa,180)
		negotiated = Negotiated(n)
		negotiated.sent(o1)
		negotiated.received(o2)
		#grouped = False

		for nei in self.neighbor.keys():
			for message in self.neighbor[nei].rib.outgoing.updates(False):
				pass

			for change1 in self.neighbor[nei].rib.outgoing.sent_changes():
				str1 = change1.extensive()
				packed = list(Update([change1.nlri],change1.attributes).messages(negotiated))
				pack1 = packed[0]

				self.logger.parser('parsed route requires %d updates' % len(packed))
				self.logger.parser('update size is %d' % len(pack1))

				self.logger.parser('parsed  route %s' % str1)
				self.logger.parser('parsed  hex   %s' % od(pack1))

				# This does not take the BGP header - let's assume we will not break that :)
				try:
					self.logger.parser('')  # new line

					pack1s = pack1[19:] if pack1.startswith('\xFF'*16) else pack1
					update = UpdateFactory(negotiated,pack1s)

					change2 = Change(update.nlris[0],update.attributes)
					str2 = change2.extensive()
					pack2 = list(Update([update.nlris[0]],update.attributes).messages(negotiated))[0]

					self.logger.parser('recoded route %s' % str2)
					self.logger.parser('recoded hex   %s' % od(pack2))

					str1r = str1.replace(' med 100','').replace(' local-preference 100','').replace(' origin igp','')
					str2r = str2.replace(' med 100','').replace(' local-preference 100','').replace(' origin igp','')

					skip = False

					if str1r != str2r:
						if 'attribute [' in str1r and ' 0x00 ' in str1r:
							# we do not decode non-transitive attributes
							self.logger.parser('skipping string check on udpate with non-transitive attribute(s)')
							skip = True
						else:
							self.logger.parser('strings are different:')
							self.logger.parser('[%s]'%str1r)
							self.logger.parser('[%s]'%str2r)
							sys.exit(1)
					else:
							self.logger.parser('strings are fine')

					if skip:
						self.logger.parser('skipping encoding for update with non-transitive attribute(s)')
					elif pack1 != pack2:
						self.logger.parser('encoding are different')
						self.logger.parser('[%s]'%od(pack1))
						self.logger.parser('[%s]'%od(pack2))
						sys.exit(1)
					else:
						self.logger.parser('encoding is fine')
						self.logger.parser('----------------------------------------')

				except Notify,e:
					print 'failed due to notification'
					print str(e)
					sys.exit(1)

		import sys
		sys.exit(0)

########NEW FILE########
__FILENAME__ = json
# encoding: utf-8
"""
json.py

Created by Thomas Mangin on 2013-07-01.
Copyright (c) 2009-2012 Exa Networks. All rights reserved.
"""

from decimal import Decimal

from exabgp.util import coroutine

class JSONError(Exception):
	pass

class UnexpectedData(JSONError):
	def __init__(self, line, position, token):
		super(UnexpectedData, self).__init__('Unexpected data at line %d position %d : "%s"' % (line,position,token))

@coroutine.join
def unescape(s):
	start = 0
	while start < len(s):
		pos = s.find('\\', start)
		if pos == -1:
			yield s[start:]
			break
		yield s[start:pos]
		pos += 1
		esc = s[pos]
		if esc == 'b':
			yield '\b'
		elif esc == 'f':
			yield '\f'
		elif esc == 'n':
			yield '\n'
		elif esc == 'r':
			yield '\r'
		elif esc == 't':
			yield '\t'
		elif esc == 'u':
			yield chr(int(s[pos + 1:pos + 5], 16))
			pos += 4
		else:
			yield esc
		start = pos + 1

@coroutine.each
def tokens (stream):
	spaces = [' ', '\t', '\r', '\n']
	strings = ['"', "'"]
	syntax = [',','[',']','{','}']
	nb_lines = 0
	for line in stream:
		nb_lines += 1
		nb_chars = 0
		quoted = ''
		word = ''
		for char in line:
			if char in spaces:
				if quoted:
					word += char
				elif word:
					yield nb_lines,nb_chars,word
					nb_chars += len(word)
					word = ''
				nb_chars += 1

			elif char in strings:
				word += char
				if quoted == char:
					quoted = ''
					yield nb_lines,nb_chars,word
					nb_chars += len(word) + 1
					word = ''
				else:
					quoted = char
					nb_chars += 1

			elif char in syntax:
				if quoted:
					word += char
				else:
					if word:
						yield nb_lines,nb_chars,word
						nb_chars += len(word)
						word = ''
					yield nb_lines,nb_chars,char
				nb_chars += 1

			else:
				word += char
				nb_chars += 1

def parser (tokeniser,container):
	# Yes, you can add attributes to function ...
	tokeniser.path = []

	def content(next):
		try:
			while True:
				line,position,token = next()

				if token == '{':
					klass = container(next.path)
					d = klass()
					for key,value in iterate_dict(next):
						d[key] = value
					return d
				elif token == '[':
					l = []
					for element in iterate_list(next):
						l.append(element)
					return l
				elif token[0] == '"':
					return unescape(token[1:-1])
				elif token == 'true':
					return True
				elif token == 'false':
					return False
				elif token == 'null':
					return None
				elif token == ']':  # required for parsing arrays
					return ']'
				else:
					# can raise ValueError
					return Decimal(token) if '.' in token else int(token)
		except ValueError:
			raise UnexpectedData(line,position,token)
		except StopIteration:
			return ''

	def iterate_dict(next):
		line,position,key = next()
		if key != '}':
			while True:
				if key[0] != '"':
					raise UnexpectedData(line,position,key)

				line,position,colon = next()
				if colon != ':':
					raise UnexpectedData(line,position,colon)

				next.path.append(key)
				yield key[1:-1],content(next)
				next.path.pop()

				line,position,separator = next()
				if separator == '}':
					break
				if separator != ',':
					raise UnexpectedData(line,position,separator)
				line,position,key = next()

	def iterate_list(next):
		value = content(next)
		if value != ']':
			while True:
				yield value

				line,position,separator = next()
				if separator == ']':
					break
				if separator != ',':
					raise UnexpectedData(line,position,separator)

				value = content(next)

	return content(tokeniser)


def load (stream,container=lambda _:dict):
	return parser(tokens(stream),container)

__all__ = [load,JSONError,UnexpectedData]

########NEW FILE########
__FILENAME__ = loader
# encoding: utf-8
"""
configuration.py

Created by Thomas Mangin on 2013-03-15.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.configuration import json

class InvalidFormat (Exception):
	"Raised when the configuration can not be parsed"
	pass


class Format (object):
	"""
	Store class used to convert the configuration format to json
	Every configuration file must start with the line "#syntax: <format>\n"
	where <format> is one of the class defined within format (simplejson or json)
	"""

	class simplejson (object):
		"""
		the new format, which is a json bastard
		* single line (no non-json nesting), the parser does not handle it
		* keyword do not need to be quoted
		(ie: key: "value" as a shortcut for "key": "value")
		* the dictionary do not need a
		(ie: storage { } as a shortcut for "storage" : { })
		* comma between lines will be automatically added
		* will ignore every line which first non-space (or tab) character is #
		"""

		@staticmethod
		def skip (current):
			striped = current.strip()
			return striped == '' or striped[0] == '#'

		@staticmethod
		def read (last,current):
			_last = last.strip()
			_current = current.strip()
			prefix = '\n'

			# do not allow nesting
			if '{' in current and (current.count('{') > 1 or not '{\n' in current):
				raise InvalidFormat('You can not write "%s", only one { per name is allowed' % _current)

			# automatically add the comma
			if last:
				if _current == '}' or _current == ']':
					pass
				elif not _last.endswith('{') and not _last.endswith('['):
					prefix = ',\n'

			# handle the non-quoted keys
			if ':' in _current:
				position = current.find(_current)
				key = _current.split(':',1)[0]
				if '"' not in key:
					return prefix + current[:position] + '"%s"' % key + current[position+len(key):].rstrip()
			# handle the simple dictionary
			elif _current.endswith('{') and not _current.startswith('{'):
				position = current.find(_current)
				section = _current.split()[0]
				if '"' not in section:
					return prefix + current[:position] + '"%s":' % section + current[position+len(section):].rstrip()
			# nothing to change
			else:
				return prefix + current.rstrip()

	class json (object):
		"""
		raw json reader without any modification to allow easier scripting
		"""
		@staticmethod
		def skip (current):
			return False

		@staticmethod
		def read (last,current):
			return current


class Reader (object):
	"""
	A file-like object providing a read() method which will convert
	the configuration in JSON following the format information set at
	the start of the file with the "#syntax: <format>"
	"""
	def __init__ (self,fname):
		self.file = open(fname,'rb')
		self.last = ''      # the last line we read from the file
		self.formated = ''  # the formated data we have already converted

		name = ''.join(self.file.readline().split())
		if not name.startswith('#syntax:'):
			name = '#syntax:json'
			self.file.close()
			self.file = open(fname,'rb')

		klass = getattr(Format,name[8:],None)
		if not klass:
			raise InvalidFormat('unknown configuration format')

		self.format = klass.read
		self.skip = klass.skip

	def __del__(self):
		if self.file:
			self.file.close()
			self.file = None

	def __enter__ (self):
		return self

	def __exit__(self, type, value, tb):
		if self.file:
			self.file.close()
			self.file = None

	def read (self,number=0):
		# we already done the work, just return the small chunks
		if number and len(self.formated) >= number:
			returned, self.formated = self.formated[:number], self.formated[number:]
			return returned

		data = bytearray()

		try:
			# restore / init the last line seen
			last = self.last

			# reading up to number bytes or until EOF which will raise StopIteration
			while not number or len(data) < number:
				new = self.file.next()
				if self.skip(new):
					continue
				data += self.format(last,new)
				last = new

			# save the last line seen for the next call
			self.last = last

			if number:
				complete = self.formated + bytes(data)
				returned, self.formated = complete[:number], complete[number:]
				return returned

			return bytes(data)
		except StopIteration:
			# we can come here twice : on EOF and again
			# to empty self.formated when its len becomes smaller than number
			complete = self.formated + bytes(data)
			if number:
				returned, self.formated = complete[:number], complete[number:]
				return returned
			else:
				self.formated = ''
				return complete

	def readline (self, limit=-1):
		returned = bytearray()
		while limit < 0 or len(returned) < limit:
			byte = self.read(1)
			if not byte:
				break
			returned += byte
			if returned.endswith(b'\n'):
				break
		return bytes(returned)

	def __iter__ (self):
		if not self.file:
			raise ValueError("I/O operation on closed file.")
		return self

	def next (self):
		line = self.readline()
		if not line:
			raise StopIteration
		return line

	__next__ = next

def load (fname):
	"""
	Convert a exa configuration format to its dictionary representation
	Can raise InvalidFormat and all file related exceptions such as IOError
	"""
	with Reader(fname) as reader:
		return json.load(reader)

def parse (fname):
	"""
	Convert a exa configuration format to its json representation
	Can raise InvalidFormat and all file related exceptions such as IOError
	"""
	with Reader(fname) as reader:
		return reader.read()

__all__ = [load,parse,InvalidFormat]

########NEW FILE########
__FILENAME__ = validation
# encoding: utf-8
'''
validation.py

Created by Thomas Mangin on 2013-03-18.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
'''

__all__ = ["validation", "ValidationError"]

FORMAT = 3
DEBUG = False

from collections import deque, OrderedDict

from exabgp.data import check

TYPE=check.TYPE
PRESENCE=check.PRESENCE

class ValidationError (Exception):
	internal_error = 'invalid configuration definition (internal error)'
	mandatory_error = 'missing mandatory configuration field'
	type_error = 'the data for this configuration option is not what was expected'
	configuration_error = 'the configuration is missing this information'
	conflicting_error = 'the configuration has conflicting information'

	def __init__ (self,location,message):
		self.location = location
		self.message = message

	def __str__ (self):
		location = ','.join(self.location) if self.location else 'root'
		return 'location ' + location + ' : ' + self.message

_attributes = OrderedDict((
	('next-hop', (TYPE.string, PRESENCE.optional, '', check.ipv4)),
	('origin' , (TYPE.string, PRESENCE.optional, '', ['igp','egp','incomplete'])),
	('as-path' , (TYPE.array, PRESENCE.optional, '', check.aspath)),
	('as-sequence' , (TYPE.array, PRESENCE.optional, '', check.assequence)),
	('local-preference', (TYPE.integer, PRESENCE.optional, '', check.localpreference)),
	('med', (TYPE.integer, PRESENCE.optional, '', check.med)),
	('aggregator' , (TYPE.string , PRESENCE.optional, '', check.ipv4)),
	('aggregator-id' , (TYPE.string , PRESENCE.optional, '', check.ipv4)),
	('atomic-aggregate' , (TYPE.boolean , PRESENCE.optional, '', check.nop)),
	('community' , (TYPE.array , PRESENCE.optional, '', check.community)),
	('extended-community' , (TYPE.array , PRESENCE.optional, '', check.extendedcommunity)),
	('aigp', (TYPE.integer, PRESENCE.optional, '', check.aigp)),
	('label' , (TYPE.array , PRESENCE.optional, '', check.label)),
	('cluster-list' , (TYPE.array , PRESENCE.optional, '', check.clusterlist)),
	('originator-id' , (TYPE.string , PRESENCE.optional, '', check.originator)),
	('path-information' , (TYPE.string|TYPE.integer , PRESENCE.optional, '', check.pathinformation)),
	('route-distinguisher' , (TYPE.string , PRESENCE.optional, '', check.distinguisher)),
	('split' , (TYPE.integer , PRESENCE.optional, '', check.split)),
	('watchdog' , (TYPE.string , PRESENCE.optional, '', check.watchdog)),
	('withdrawn' , (TYPE.boolean , PRESENCE.optional, '', check.nop)),
))

_definition = (TYPE.object, PRESENCE.mandatory, '', OrderedDict((
	('exabgp' , (TYPE.integer, PRESENCE.mandatory, '', [FORMAT,])),
	('neighbor' , (TYPE.object, PRESENCE.mandatory, '', OrderedDict((
		('<*>' , (TYPE.object, PRESENCE.mandatory, '', OrderedDict((
			('tcp' , (TYPE.object, PRESENCE.mandatory, '', OrderedDict((
				('bind' , (TYPE.string, PRESENCE.mandatory, '', check.ip)),
				('connect' , (TYPE.string, PRESENCE.mandatory, '', check.ip)),
				('ttl-security' , (TYPE.integer, PRESENCE.optional, '', check.uint8)),
				('md5' , (TYPE.string, PRESENCE.optional, '', check.md5)),
				('passive' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
			)))),
			('api' , (TYPE.object, PRESENCE.optional, 'api', OrderedDict((
				('<*>' , (TYPE.array, PRESENCE.mandatory, '', ['neighbor-changes','send-packets','receive-packets','receive-routes'])),
			)))),
			('session' , (TYPE.object, PRESENCE.mandatory, '', OrderedDict((
				('router-id' , (TYPE.string, PRESENCE.mandatory, '', check.ipv4)),
				('hold-time' , (TYPE.integer, PRESENCE.mandatory, '', check.uint16)),
				('asn' , (TYPE.object, PRESENCE.mandatory, '', OrderedDict((
					('local' , (TYPE.integer, PRESENCE.mandatory, '', check.uint32)),
					('peer' , (TYPE.integer, PRESENCE.mandatory, '', check.uint32)),
				)))),
				('feature' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
					('updates' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
						('group' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
						('flush' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
					)))),
					('rib' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
						('adj-rib-out' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
					)))),
				)))),
				('capability' , (TYPE.object, PRESENCE.mandatory, '', OrderedDict((
					('family' , (TYPE.object, PRESENCE.mandatory, '', OrderedDict((
						('ipv4' , (TYPE.array, PRESENCE.optional, '', ['unicast','multicast','nlri-mpls','mpls-vpn','flow-vpn','flow'])),
						('ipv6' , (TYPE.array, PRESENCE.optional, '', ['unicast','flow'])),
						('alias' , (TYPE.string, PRESENCE.optional, '', ['all','minimal'])),
					)))),
					('asn4' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
					('route-refresh' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
					('graceful-restart' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
					('multi-session' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
					('add-path' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
					('aigp' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
				)))),
			)))),
			('announce' , (TYPE.array, PRESENCE.optional, ['update,prefix','update,flow'], check.string)),
		)))),
	)))),
	('api' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
		('<*>' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
			('encoder' , (TYPE.string, PRESENCE.optional, '', ['json','text'])),
			('program' , (TYPE.string, PRESENCE.mandatory, '', check.nop)),
		)))),
	)))),
	('attribute' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
		('<*>' , (TYPE.object, PRESENCE.optional, '', _attributes)),
	)))),
	('flow' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
		('filtering-condition' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
			('<*>' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
				('source' , (TYPE.array|TYPE.string, PRESENCE.optional, '', check.flow_ipv4_range)),
				('destination' , (TYPE.array|TYPE.string, PRESENCE.optional, '', check.flow_ipv4_range)),
				('port' , (TYPE.array, PRESENCE.optional, '', check.flow_port)),
				('source-port' , (TYPE.array, PRESENCE.optional, '', check.flow_port)),
				('destination-port' , (TYPE.array, PRESENCE.optional, '', check.flow_port)),
				('protocol' , (TYPE.array|TYPE.string, PRESENCE.optional, '', ['udp','tcp'])),  # and value of protocols ...
				('packet-length' , (TYPE.array, PRESENCE.optional, '', check.flow_length)),
				('packet-fragment' , (TYPE.array|TYPE.string, PRESENCE.optional, '', ['not-a-fragment', 'dont-fragment', 'is-fragment', 'first-fragment', 'last-fragment'])),
				('icmp-type' , (TYPE.array|TYPE.string, PRESENCE.optional, '', ['unreachable', 'echo-request', 'echo-reply'])),
				# TODO : missing type
				('icmp-code' , (TYPE.array|TYPE.string, PRESENCE.optional, '', ['host-unreachable', 'network-unreachable'])),
				# TODO : missing  code
				('tcp-flags' , (TYPE.array|TYPE.string, PRESENCE.optional, '', ['fin', 'syn', 'rst', 'push', 'ack', 'urgent'])),
				('dscp' , (TYPE.array|TYPE.integer, PRESENCE.optional, '', check.dscp)),
				# TODO: MISSING SOME MORE ?
			)))),
		)))),
		('filtering-action' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
			('<*>' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
				('rate-limit' , (TYPE.integer, PRESENCE.optional, '', check.float)),
				('discard' , (TYPE.boolean, PRESENCE.optional, '', check.nop)),
				('redirect' , (TYPE.string, PRESENCE.optional, '', check.redirect)),
				('community' , (TYPE.array , PRESENCE.optional, '', check.community)),
				('extended-community' , (TYPE.array , PRESENCE.optional, '', check.extendedcommunity)),
			)))),
		)))),
	)))),
	('update' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
		('prefix' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
			('<*>' , (TYPE.object, PRESENCE.optional, 'attribute', OrderedDict((  # name of route
				('<*>' , (TYPE.object, PRESENCE.mandatory, '', OrderedDict((  # name of attributes referenced
					('<*>' , (TYPE.object, PRESENCE.optional, '', _attributes)),  # prefix
				)))),
			)))),
		)))),
		('flow' , (TYPE.object, PRESENCE.optional, '', OrderedDict((
			('<*>' , (TYPE.object, PRESENCE.optional, 'flow,filtering-condition', OrderedDict((  # name of the dos
				('<*>' , (TYPE.string, PRESENCE.mandatory, 'flow,filtering-action', check.nop)),
			)))),
		)))),
	)))),
)))


# Lookup in the definition all the keyword we used to make sure that users can not use them
# This allows us to be able to index on those words and to be sure of the underlying data

_reserved_keywords = set()
def _reserved (reserved_keywords,definition):
	kind,_,_,od = definition

	if kind & TYPE.object:
		for key in od:
			reserved_keywords.update([key])
			_reserved(reserved_keywords,od[key])
_reserved(_reserved_keywords,_definition)

# Name are are long string and cause high memory usage use integer instead
# regenreate the _definition with indexes

_indexes_byname = dict()
_indexes_byid = dict()
for index,name in enumerate(_reserved_keywords):
	_indexes_byname[name] = index
	_indexes_byid[id] = name


# TODO: Now need to rewrite the whole definiton to use the indexes
# TODO: and update the reference to do to the lookup in _indexes_by...

# check that the configuration has the reference

def _reference (root,references,json,location):
	if not references:
		return

	ref = references if check.array(references) else [references,]
	jsn = json if check.array(json) else json.keys() if check.object(json) else [json,]

	valid = []
	for reference in ref:
		compare = root
		for path in reference.split(','):
			compare = compare.get(path,{})
		# prevent name conflict where we can not resolve which object is referenced.
		add = compare.keys()
		for k in add:
			if k in valid:
				raise ValidationError(location, "duplicate reference in " % ', '.join(references))

				return False
		valid.extend(add)

	for option in jsn:
		if not option in valid:
			destination = ' or '.join(references) if type(references) == type ([]) else references
			raise ValidationError(location, "the referenced data in %s is not present" % destination)

	return True

def _validate (root,json,definition,location=[]):
	kind,presence,references,contextual = definition

	# ignore missing optional elements
	if not json:
		if presence == PRESENCE.mandatory:
			raise ValidationError(location, ValidationError.mandatory_error)
		return

	# check that the value of the right type
	if not check.kind(kind,json):
		raise ValidationError(location, ValidationError.type_error)

	# for object check all the elements inside
	if kind & TYPE.object and check.object(json):
		subdefinition = contextual
		keys = deque(subdefinition.keys())

		while keys:
			key = keys.popleft()
			if DEBUG: print "  "*len(location) + key

			if key.startswith('_'):
				continue

			if type(json) != type({}):
				raise ValidationError(location, ValidationError.type_error)

			if key == '<*>':
				keys.extendleft(json.keys())
				continue

			_reference (root,references,json,location)

			star = subdefinition.get('<*>',None)
			subtest = subdefinition.get(key,star)
			if subtest is None:
				raise ValidationError(location, ValidationError.configuration_error)
			_validate(root,json.get(key,None),subtest,location + [key])

	# for list check all the element inside
	elif kind & TYPE.array and check.array(json):
		test = contextual
		# This is a function
		if hasattr(test, '__call__'):
			for data in json:
				if not test(data):
					raise ValidationError(location, ValidationError.type_error)
		# This is a list of valid option
		elif type(test) == type([]):
			for data in json:
				if not data in test:
					raise ValidationError(location, ValidationError.type_error)
		# no idea what the data is - so something is wrong with the program
		else:
			raise ValidationError(location,ValidationError.internal_error)

	# for non container object check the value
	else:
		test = contextual
		# check that the value of the data
		if hasattr(test, '__call__'):
			if not test(json):
				raise ValidationError(location, ValidationError.type_error)
		# a list of valid option
		elif type(test) == type([]):
			if not json in test:
				raise ValidationError(location, ValidationError.type_error)
		else:
			raise ValidationError(location,ValidationError.internal_error)

	_reference (root,references,json,location)

def _inet (json):
	conflicts = {
		'alias': ['inet','inet4','inet6'],
		'inet': ['inet4','inet6']
	}
	for name in json['neighbor']:
		inet = [_ for _ in json['neighbor'][name]['session']['capability']['family'].keys() if not _.startswith('_')]
		for conflict in conflicts:
			if conflict in inet:
				raise ValidationError(['neighbor',name,'session','capability','family'], ValidationError.conflicting_error)

def validation (json):
	_validate(json,json,_definition)
	_inet(json)

########NEW FILE########
__FILENAME__ = check
# encoding: utf-8
'''
check.py

Created by Thomas Mangin on 2013-03-18.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
'''

from exabgp.util.enumeration import Enumeration

TYPE = Enumeration (
	'null',     # -  1
	'boolean',  # -  2
	'integer',  # -  4
	'string',   # -  8
	'array',    # - 16
	'object',   # - 32
)

PRESENCE = Enumeration(
	'optional',   # -  1
	'mandatory',  # -  2
)

# TYPE CHECK
def null (data):
	return type(data) == type(None)
def boolean (data):
	return type(data) == type(True)
def integer (data):
	return type(data) == type(0)
def string (data):
	return type(data) == type(u'') or type(data) == type('')
def array (data):
	return type(data) == type([])
def object (data):
	return type(data) == type({})
# XXX: Not very good to redefine the keyword object, but this class uses no OO ...

CHECK_TYPE = {
	TYPE.null : null,
	TYPE.boolean : boolean,
	TYPE.integer : integer,
	TYPE.string : string,
	TYPE.array : array,
	TYPE.object : object,
}

def kind (kind,data):
	for t in CHECK_TYPE:
		if kind & t:
			if CHECK_TYPE[t](data):
				return True
	return False

# DATA CHECK
def nop (data):
	return True

def uint8 (data):
	return data >= 0 and data < pow(2,8)
def uint16 (data):
	return data >= 0 and data < pow(2,16)
def uint32 (data):
	return data >= 0 and data < pow(2,32)
def float (data):
	return data >=0 and data < 3.4 * pow(10,38)  # approximation of max from wikipedia

def ip (data,):
	return ipv4(data) or ipv6(data)

def ipv4 (data):  # XXX: improve
	return string(data) and data.count('.') == 3
def ipv6 (data):  # XXX: improve
	return string(data) and ':' in data

def range4 (data):
	return data > 0 and data <= 32
def range6 (data):
	return data > 0 and data <= 128

def ipv4_range (data):
	if not data.count('/') == 1:
		return False
	ip,r = data.split('/')
	if not ipv4(ip):
		return False
	if not r.isdigit():
		return False
	if not range4(int(r)):
		return False
	return True

def port (data):
	return data >= 0 and data < pow(2,16)

def asn16 (data):
	return data >= 1 and data < pow(2,16)
def asn32 (data):
	return data >= 1 and data < pow(2,32)
asn = asn32

def md5 (data):
	return len(data) <= 18

def localpreference (data):
	return uint32(data)

def med (data):
	return uint32(data)

def aigp (data):
	return uint32(data)

def originator (data):
	return ipv4(data)

def distinguisher (data):
	parts = data.split(':')
	if len(parts) != 2:
		return False
	_,__ = parts
	return (_.isdigit() and asn16(int(_)) and ipv4(__)) or (ipv4(_) and __.isdigit() and asn16(int(__)))

def pathinformation (data):
	if integer(data):
		return uint32(data)
	if string(data):
		return ipv4(data)
	return False

def watchdog (data):
	return ' ' not in data  # TODO: improve

def split (data):
	return range6(data)


# LIST DATA CHECK
# Those function need to perform type checks before using the data


def aspath (data):
	return integer(data) and data < pow(2,32)

def assequence (data):
	return integer(data) and data < pow(2,32)

def community (data):
	if integer(data):
		return uint32(data)
	if string(data) and data.lower() in ('no-export', 'no-advertise', 'no-export-subconfed', 'nopeer', 'no-peer'):
		return True
	return array(data) and len(data) == 2 and \
		integer(data[0]) and integer(data[1]) and \
		asn16(data[0]) and uint16(data[1])

def extendedcommunity (data):  # TODO: improve, incomplete see http://tools.ietf.org/rfc/rfc4360.txt
	if integer(data):
		return True
	if string(data) and data.count(':') == 2:
		_,__,___ = data.split(':')
		if _.lower() not in ('origin','target'):
			return False
		return (__.isdigit() and asn16(__) and ipv4(___)) or (ipv4(__) and ___.isdigit() and asn16(___))
	return False

def label (data):
	return integer(data) and \
		data >= 0 and data < pow(2,20)  # XXX: SHOULD be taken from Label class

def clusterlist (data):
	return integer(data) and uint8(data)

def aggregator (data):
	if not array(data):
		return False
	if len(data) == 0:
		return True
	if len(data) == 2:
		return \
			integer(data[0]) and string(data[1]) and \
			asn(data[0]) and ipv4(data[1])
	return False

def dscp (data):
	return integer(data) and uint8(data)


# FLOW DATA CHECK
#


def flow_ipv4_range (data):
	if array(data):
		for r in data:
			if not ipv4_range(r):
				return False
	if string(data):
		return ipv4_range(data)
	return False


def _flow_numeric (data,check):
	if not array(data):
		return False
	for et in data:
		if not (array(et) and len(et) == 2 and et[0] in ('>', '<', '=','>=', '<=') and integer(et[1]) and check(et[1])):
			return False
	return True

def flow_port (data):
	return _flow_numeric(data,port)

def _length (data):
	return uint16(data)

def flow_length (data):
	return _flow_numeric(data,_length)

def redirect (data):  # TODO: check that we are not too restrictive with our asn() calls
	parts = data.split(':')
	if len(parts) != 2:
		return False
	_,__ = parts
	if not __.isdigit() and asn16(int(__)):
		return False
	return ipv4(_) or (_.isdigit() and asn16(int(_)))


########NEW FILE########
__FILENAME__ = debug
# encoding: utf-8
"""
debug.py

Created by Thomas Mangin on 2011-03-29.
Copyright (c) 2009-2012 Exa Networks. All rights reserved.
"""
try:
	import os
	import sys

	def bug_report (type, value, trace):
		import traceback
		from exabgp.logger import Logger
		logger = Logger()

		print
		print
		print "-"*80
		print "-- Please provide the information below on :"
		print "-- https://github.com/Exa-Networks/exabgp/issues"
		print "-"*80
		print
		print
		print '-- Version'
		print
		print
		print sys.version
		print
		print
		print "-- Configuration"
		print
		print
		print logger.config()
		print
		print
		print "-- Logging History"
		print
		print
		print logger.history()
		print
		print
		print "-- Traceback"
		print
		print
		traceback.print_exception(type,value,trace)
		print
		print
		print "-"*80
		print "-- Please provide the information above on :"
		print "-- https://github.com/Exa-Networks/exabgp/issues"
		print "-"*80
		print
		print

		#print >> sys.stderr, 'the program failed with message :', value

	def intercept (type, value, trace):
		bug_report(type, value, trace)
		if os.environ.get('PDB',None) not in [None,'0','']:
			import pdb
			pdb.pm()

	sys.excepthook = intercept

	del sys.argv[0]

	if sys.argv:
		__file__ = os.path.abspath(sys.argv[0])
		__name__ = '__main__'
		execfile(sys.argv[0])
except KeyboardInterrupt:
	sys.exit(1)

########NEW FILE########
__FILENAME__ = logger
# encoding: utf-8
"""
utils.py

Created by Thomas Mangin on 2009-09-06.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import os
import sys
import stat
import time
import syslog
import logging
import logging.handlers

from exabgp.configuration.environment import environment

_short = {
	'CRITICAL': 'CRIT',
	'ERROR': 'ERR'
}

def short (name):
	return _short.get(name.upper(),name.upper())

class LazyFormat (object):
	def __init__ (self,prefix,format,message):
		self.prefix = prefix
		self.format = format
		self.message = message

	def __str__ (self):
		if self.format:
			return self.prefix + self.format(self.message)
		return self.prefix + self.message

	def split (self,c):
		return str(self).split(c)

class _Logger (object):
	_instance = None
	_syslog = None

	_history = []
	_max_history = 20

	_config = ''
	_pid = os.getpid()
	_cwd = os.getcwd()

	# we use os.pid everytime as we may fork and the class is instance before it

	def pdb (self,level):
		if self._pdb and level in ['CRITICAL','critical']:
			import pdb
			pdb.set_trace()

	def config (self,config=None):
		if config is not None:
			self._config = config
		return self._config

	def history (self):
		return "\n".join(self._format(*_) for _ in self._history)

	def _record (self,timestamp,level,source,message):
		if len(self._history) > self._max_history:
			self._history.pop(0)
		self._history.append((timestamp,level,source,message))

	def _format (self,timestamp,level,source,message):
		if self.short: return message
		now = time.strftime('%a, %d %b %Y %H:%M:%S',timestamp)
		return "%s | %-8s | %-6d | %-13s | %s" % (now,level,self._pid,source,message)

	def _prefixed (self,level,source,message):
		ts = time.localtime()
		self._record(ts,level,source,message)
		return self._format(ts,level,source,message)

	def __init__ (self):
		command = environment.settings()
		self.short = command.log.short
		self.level = command.log.level

		self._pdb = command.debug.pdb

		self._reactor       = command.log.enable and (command.log.all or command.log.reactor)
		self._daemon        = command.log.enable and (command.log.all or command.log.daemon)
		self._processes     = command.log.enable and (command.log.all or command.log.processes)
		self._configuration = command.log.enable and (command.log.all or command.log.configuration)
		self._network       = command.log.enable and (command.log.all or command.log.network)
		self._wire          = command.log.enable and (command.log.all or command.log.packets)
		self._message       = command.log.enable and (command.log.all or command.log.message)
		self._rib           = command.log.enable and (command.log.all or command.log.rib)
		self._timer         = command.log.enable and (command.log.all or command.log.timers)
		self._routes        = command.log.enable and (command.log.all or command.log.routes)
		self._parser        = command.log.enable and (command.log.all or command.log.parser)

		if not command.log.enable:
			return

		self.destination = command.log.destination

		self.restart(True)

	def _can_write (self,location):
		try:
			s  = os.stat(os.path.dirname(location))
		except OSError:
			return None
		mode = s[stat.ST_MODE]
		uid  = os.geteuid()
		gid  = os.getegid()

		return not not (
			((s[stat.ST_UID] == uid) and (mode & stat.S_IWUSR)) or
			((s[stat.ST_GID] == gid) and (mode & stat.S_IWGRP)) or
			(mode & stat.S_IWOTH)
		)

	def restart (self,first=False):
		destination = 'stderr' if first else self.destination

		try:
			if destination in ('','syslog'):
				if sys.platform == "darwin":
					address = '/var/run/syslog'
				else:
					address = '/dev/log'
				if not os.path.exists(address):
					address = ('localhost', 514)
				handler = logging.handlers.SysLogHandler(address)

				self._syslog = logging.getLogger()
				self._syslog.setLevel(logging.DEBUG)
				self._syslog.addHandler(handler)
				return True

			if destination.lower().startswith('host:'):
				# If the address is invalid, each syslog call will print an error.
				# See how it can be avoided, as the socket error is encapsulated and not returned
				address = (destination[5:].strip(), 514)
				handler = logging.handlers.SysLogHandler(address)

				self._syslog = logging.getLogger()
				self._syslog.setLevel(logging.DEBUG)
				self._syslog.addHandler(handler)
				return True

			if destination.lower() == 'stdout':
				handler = logging.StreamHandler(sys.stdout)

				self._syslog = logging.getLogger()
				self._syslog.setLevel(logging.DEBUG)
				self._syslog.addHandler(handler)
				return True

			if destination.lower() == 'stderr':
				handler = logging.StreamHandler(sys.stderr)

				self._syslog = logging.getLogger()
				self._syslog.setLevel(logging.DEBUG)
				self._syslog.addHandler(handler)
				return True

			# folder
			logfile = os.path.realpath(os.path.normpath(os.path.join(self._cwd,destination)))
			can = self._can_write(logfile)
			if can is True:
				handler = logging.handlers.RotatingFileHandler(logfile, maxBytes=5*1024*1024, backupCount=5)
			elif can is None:
				self.critical('ExaBGP can not access (perhaps as it does not exist) the log folder provided','logger')
				return False
			else:
				self.critical('ExaBGP does not have the right to write in the requested log directory','logger')
				return False

			self._syslog = logging.getLogger()
			self._syslog.setLevel(logging.DEBUG)
			self._syslog.addHandler(handler)
			return True

		except IOError:
			self.critical('Can not set logging (are stdout/stderr closed?)','logger')
			return False

	def debug (self,message,source='',level='DEBUG'):
		for line in message.split('\n'):
			if self._syslog:
				self._syslog.debug(self._prefixed(level,source,line))
			else:
				print self._prefixed(level,source,line)
				sys.stdout.flush()

	def info (self,message,source='',level='INFO'):
		for line in message.split('\n'):
			if self._syslog:
				self._syslog.info(self._prefixed(level,source,line))
			else:
				print self._prefixed(level,source,line)
				sys.stdout.flush()

	def warning (self,message,source='',level='WARNING'):
		for line in message.split('\n'):
			if self._syslog:
				self._syslog.warning(self._prefixed(level,source,line))
			else:
				print self._prefixed(level,source,line)
				sys.stdout.flush()

	def error (self,message,source='',level='ERROR'):
		for line in message.split('\n'):
			if self._syslog:
				self._syslog.error(self._prefixed(level,source,line))
			else:
				print self._prefixed(level,source,line)
				sys.stdout.flush()

	def critical (self,message,source='',level='CRITICAL'):
		for line in message.split('\n'):
			if self._syslog:
				self._syslog.critical(self._prefixed(level,source,line))
			else:
				print self._prefixed(level,source,line)
				sys.stdout.flush()
		self.pdb(level)

	# show the message on the wire
	def network (self,message,recorder='info'):
		up = short(recorder)
		if self._network and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'network')
		else:
			self._record(time.localtime(),'network',recorder,message)
		self.pdb(recorder)

	# show the message on the wire
	def wire (self,message,recorder='debug'):
		up = short(recorder)
		if self._wire and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'wire')
		else:
			self._record(time.localtime(),'wire',recorder,message)
		self.pdb(recorder)

	# show the exchange of message between peers
	def message (self,message,recorder='info'):
		up = short(recorder)
		if self._message and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'message')
		else:
			self._record(time.localtime(),'message',recorder,message)
		self.pdb(recorder)

	# show the parsing of the configuration
	def configuration (self,message,recorder='info'):
		up = short(recorder)
		if self._configuration and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'configuration')
		else:
			self._record(time.localtime(),'configuration',recorder,message)
		self.pdb(recorder)

	# show the exchange of message generated by the reactor (^C and signal received)
	def reactor (self,message,recorder='info'):
		up = short(recorder)
		if self._reactor and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'reactor')
		else:
			self._record(time.localtime(),'reactor',recorder,message)
		self.pdb(recorder)

	# show the change of rib table
	def rib (self,message,recorder='info'):
		up = short(recorder)
		if self._rib and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'rib')
		else:
			self._record(time.localtime(),'rib',recorder,message)
		self.pdb(recorder)

	# show the change of rib table
	def timers (self,message,recorder='debug'):
		up = short(recorder)
		if self._timer and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'timers')
		else:
			self._record(time.localtime(),'timers',recorder,message)
		self.pdb(recorder)

	# show the exchange of message generated by the daemon feature (change pid, fork, ...)
	def daemon (self,message,recorder='info'):
		up = short(recorder)
		if self._daemon and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'daemon')
		else:
			self._record(time.localtime(),'daemon',recorder,message)
		self.pdb(recorder)

	# show the exchange of message generated by the forked processes
	def processes (self,message,recorder='info'):
		up = short(recorder)
		if self._processes and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'processes')
		else:
			self._record(time.localtime(),'processes',recorder,message)
		self.pdb(recorder)

	# show the exchange of message generated by the routes received
	def routes (self,message,recorder='info'):
		up = short(recorder)
		if self._routes and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'routes')
		else:
			self._record(time.localtime(),'routes',recorder,message)
		self.pdb(recorder)

	# show how the message received are parsed
	def parser (self,message,recorder='info'):
		up = short(recorder)
		if self._parser and getattr(syslog,'LOG_%s' % up) <= self.level:
			getattr(self,recorder.lower())(message,'parser')
		self.pdb(recorder)

def Logger ():
	if _Logger._instance is not None:
		return _Logger._instance
	instance = _Logger()
	_Logger._instance = instance
	return instance

class FakeLogger:
	def __getattr__ (self,name):
		return lambda data,_=None: sys.stdout.write('Fake logger [%s]\n' % str(data))

if __name__ == '__main__':
	logger = Logger()
	logger.wire('wire packet content')
	logger.message('message exchanged')
	logger.debug('debug test')

########NEW FILE########
__FILENAME__ = gcdump
# http://teethgrinder.co.uk/perm.php?a=Python-memory-leak-detector
import gc
import inspect

def dump():
	# force collection
	print "\nCollecting GARBAGE:"
	gc.collect()
	# prove they have been collected
	print "\nCollecting GARBAGE:"
	gc.collect()

	print "\nGARBAGE OBJECTS:"
	for x in gc.garbage:
		s = str(x)
		if len(s) > 80: s = "%s..." % s[:80]

		print "::", s
		print "		type:", type(x)
		print "   referrers:", len(gc.get_referrers(x))
		try:
			print "	is class:", inspect.isclass(type(x))
			print "	  module:", inspect.getmodule(x)

			lines, line_num = inspect.getsourcelines(type(x))
			print "	line num:", line_num
			for l in lines:
				print "		line:", l.rstrip("\n")
		except:
			pass

		print

########NEW FILE########
__FILENAME__ = objgraph
"""
Ad-hoc tools for drawing Python object reference graphs with graphviz.

This module is more useful as a repository of sample code and ideas, than
as a finished product.  For documentation and background, read

	http://mg.pov.lt/blog/hunting-python-memleaks.html
	http://mg.pov.lt/blog/python-object-graphs.html
	http://mg.pov.lt/blog/object-graphs-with-graphviz.html

in that order.  Then use pydoc to read the docstrings, as there were
improvements made since those blog posts.

Copyright (c) 2008 Marius Gedminas <marius@pov.lt>

Released under the MIT licence.


Changes
=======

1.1dev (2008-09-05)
-------------------

New function: show_refs() for showing forward references.

New functions: typestats() and show_most_common_types().

Object boxes are less crammed with useless information (such as IDs).

Spawns xdot if it is available.
"""
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

__author__ = "Marius Gedminas (marius@gedmin.as)"
__copyright__ = "Copyright (c) 2008 Marius Gedminas"
__license__ = "MIT"
__version__ = "1.1dev"
__date__ = "2008-09-05"


import gc
import inspect
import types
import weakref
import operator
import os


def count(typename):
	"""Count objects tracked by the garbage collector with a given class name.

	Example:

		>>> count('dict')
		42
		>>> count('MyClass')
		3

	Note that the GC does not track simple objects like int or str.
	"""
	return sum(1 for o in gc.get_objects() if type(o).__name__ == typename)


def typestats():
	"""Count the number of instances for each type tracked by the GC.

	Note that the GC does not track simple objects like int or str.

	Note that classes with the same name but defined in different modules
	will be lumped together.
	"""
	stats = {}
	for o in gc.get_objects():
		stats.setdefault(type(o).__name__, 0)
		stats[type(o).__name__] += 1
	return stats


def show_most_common_types(limit=10):
	"""Count the names of types with the most instances.

	Note that the GC does not track simple objects like int or str.

	Note that classes with the same name but defined in different modules
	will be lumped together.
	"""
	stats = sorted(typestats().items(), key=operator.itemgetter(1), reverse=True)
	if limit:
		stats = stats[:limit]
	width = max(len(name) for name, count in stats)
	for name, count in stats[:limit]:
		print name.ljust(width), count


def by_type(typename):
	"""Return objects tracked by the garbage collector with a given class name.

	Example:

		>>> by_type('MyClass')
		[<mymodule.MyClass object at 0x...>]

	Note that the GC does not track simple objects like int or str.
	"""
	return [o for o in gc.get_objects() if type(o).__name__ == typename]


def at(addr):
	"""Return an object at a given memory address.

	The reverse of id(obj):

		>>> at(id(obj)) is obj
		True

	Note that this function does not work on objects that are not tracked by
	the GC (e.g. ints or strings).
	"""
	for o in gc.get_objects():
		if id(o) == addr:
			return o
	return None


def find_backref_chain(obj, predicate, max_depth=20, extra_ignore=()):
	"""Find a shortest chain of references leading to obj.

	The start of the chain will be some object that matches your predicate.

	``max_depth`` limits the search depth.

	``extra_ignore`` can be a list of object IDs to exclude those objects from
	your search.

	Example:

		>>> find_backref_chain(obj, inspect.ismodule)
		[<module ...>, ..., obj]

	Returns None if such a chain could not be found.
	"""
	queue = [obj]
	depth = {id(obj): 0}
	parent = {id(obj): None}
	ignore = set(extra_ignore)
	ignore.add(id(extra_ignore))
	ignore.add(id(queue))
	ignore.add(id(depth))
	ignore.add(id(parent))
	ignore.add(id(ignore))
	gc.collect()
	while queue:
		target = queue.pop(0)
		if predicate(target):
			chain = [target]
			while parent[id(target)] is not None:
				target = parent[id(target)]
				chain.append(target)
			return chain
		tdepth = depth[id(target)]
		if tdepth < max_depth:
			referrers = gc.get_referrers(target)
			ignore.add(id(referrers))
			for source in referrers:
				if inspect.isframe(source) or id(source) in ignore:
					continue
				if id(source) not in depth:
					depth[id(source)] = tdepth + 1
					parent[id(source)] = target
					queue.append(source)
	return None  # not found


def show_backrefs(objs, max_depth=3, extra_ignore=(), filter=None, too_many=10,
					highlight=None):
	"""Generate an object reference graph ending at ``objs``

	The graph will show you what objects refer to ``objs``, directly and
	indirectly.

	``objs`` can be a single object, or it can be a list of objects.

	Produces a Graphviz .dot file and spawns a viewer (xdot) if one is
	installed, otherwise converts the graph to a .png image.

	Use ``max_depth`` and ``too_many`` to limit the depth and breadth of the
	graph.

	Use ``filter`` (a predicate) and ``extra_ignore`` (a list of object IDs) to
	remove undesired objects from the graph.

	Use ``highlight`` (a predicate) to highlight certain graph nodes in blue.

	Examples:

		>>> show_backrefs(obj)
		>>> show_backrefs([obj1, obj2])
		>>> show_backrefs(obj, max_depth=5)
		>>> show_backrefs(obj, filter=lambda x: not inspect.isclass(x))
		>>> show_backrefs(obj, highlight=inspect.isclass)
		>>> show_backrefs(obj, extra_ignore=[id(locals())])

	"""
	show_graph(objs, max_depth=max_depth, extra_ignore=extra_ignore,
				filter=filter, too_many=too_many, highlight=highlight,
				edge_func=gc.get_referrers, swap_source_target=False)


def show_refs(objs, max_depth=3, extra_ignore=(), filter=None, too_many=10,
				highlight=None):
	"""Generate an object reference graph starting at ``objs``

	The graph will show you what objects are reachable from ``objs``, directly
	and indirectly.

	``objs`` can be a single object, or it can be a list of objects.

	Produces a Graphviz .dot file and spawns a viewer (xdot) if one is
	installed, otherwise converts the graph to a .png image.

	Use ``max_depth`` and ``too_many`` to limit the depth and breadth of the
	graph.

	Use ``filter`` (a predicate) and ``extra_ignore`` (a list of object IDs) to
	remove undesired objects from the graph.

	Use ``highlight`` (a predicate) to highlight certain graph nodes in blue.

	Examples:

		>>> show_refs(obj)
		>>> show_refs([obj1, obj2])
		>>> show_refs(obj, max_depth=5)
		>>> show_refs(obj, filter=lambda x: not inspect.isclass(x))
		>>> show_refs(obj, highlight=inspect.isclass)
		>>> show_refs(obj, extra_ignore=[id(locals())])

	"""
	show_graph(objs, max_depth=max_depth, extra_ignore=extra_ignore,
				filter=filter, too_many=too_many, highlight=highlight,
				edge_func=gc.get_referents, swap_source_target=True)

#
# Internal helpers
#

def show_graph(objs, edge_func, swap_source_target,
				max_depth=3, extra_ignore=(), filter=None, too_many=10,
				highlight=None):
	if not isinstance(objs, (list, tuple)):
		objs = [objs]
	f = file('objects.dot', 'w')
	print >> f, 'digraph ObjectGraph {'
	print >> f, '  node[shape=box, style=filled, fillcolor=white];'
	queue = []
	depth = {}
	ignore = set(extra_ignore)
	ignore.add(id(objs))
	ignore.add(id(extra_ignore))
	ignore.add(id(queue))
	ignore.add(id(depth))
	ignore.add(id(ignore))
	for obj in objs:
		print >> f, '  %s[fontcolor=red];' % (obj_node_id(obj))
		depth[id(obj)] = 0
		queue.append(obj)
	gc.collect()
	nodes = 0
	while queue:
		nodes += 1
		target = queue.pop(0)
		tdepth = depth[id(target)]
		print >> f, '  %s[label="%s"];' % (obj_node_id(target), obj_label(target, tdepth))
		h, s, v = gradient((0, 0, 1), (0, 0, .3), tdepth, max_depth)
		if inspect.ismodule(target):
			h = .3
			s = 1
		if highlight and highlight(target):
			h = .6
			s = .6
			v = 0.5 + v * 0.5
		print >> f, '  %s[fillcolor="%g,%g,%g"];' % (obj_node_id(target), h, s, v)
		if v < 0.5:
			print >> f, '  %s[fontcolor=white];' % (obj_node_id(target))
		if inspect.ismodule(target) or tdepth >= max_depth:
			continue
		neighbours = edge_func(target)
		ignore.add(id(neighbours))
		n = 0
		for source in neighbours:
			if inspect.isframe(source) or id(source) in ignore:
				continue
			if filter and not filter(source):
				continue
			if swap_source_target:
				srcnode, tgtnode = target, source
			else:
				srcnode, tgtnode = source, target
			elabel = edge_label(srcnode, tgtnode)
			print >> f, '  %s -> %s%s;' % (obj_node_id(srcnode), obj_node_id(tgtnode), elabel)
			if id(source) not in depth:
				depth[id(source)] = tdepth + 1
				queue.append(source)
			n += 1
			if n >= too_many:
				print >> f, '  %s[color=red];' % obj_node_id(target)
				break
	print >> f, "}"
	f.close()
	print "Graph written to objects.dot (%d nodes)" % nodes
	if os.system('which xdot >/dev/null') == 0:
		print "Spawning graph viewer (xdot)"
		os.system("xdot objects.dot &")
	else:
		os.system("dot -Tpng objects.dot > objects.png")
		print "Image generated as objects.png"


def obj_node_id(obj):
	if isinstance(obj, weakref.ref):
		return 'all_weakrefs_are_one'
	return ('o%d' % id(obj)).replace('-', '_')


def obj_label(obj, depth):
	return quote(type(obj).__name__ + ':\n' + safe_repr(obj))


def quote(s):
	return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")


def safe_repr(obj):
	try:
		return short_repr(obj)
	except:
		return '(unrepresentable)'


def short_repr(obj):
	if isinstance(obj, (type, types.ModuleType, types.BuiltinMethodType,
						types.BuiltinFunctionType)):
		return obj.__name__
	if isinstance(obj, types.MethodType):
		if obj.im_self is not None:
			return obj.im_func.__name__ + ' (bound)'
		else:
			return obj.im_func.__name__
	if isinstance(obj, (tuple, list, dict, set)):
		return '%d items' % len(obj)
	if isinstance(obj, weakref.ref):
		return 'all_weakrefs_are_one'
	return repr(obj)[:40]


def gradient(start_color, end_color, depth, max_depth):
	if max_depth == 0:
		# avoid division by zero
		return start_color
	h1, s1, v1 = start_color
	h2, s2, v2 = end_color
	f = float(depth) / max_depth
	h = h1 * (1-f) + h2 * f
	s = s1 * (1-f) + s2 * f
	v = v1 * (1-f) + v2 * f
	return h, s, v


def edge_label(source, target):
	if isinstance(target, dict) and target is getattr(source, '__dict__', None):
		return ' [label="__dict__",weight=10]'
	elif isinstance(source, dict):
		for k, v in source.iteritems():
			if v is target:
				if isinstance(k, basestring) and k:
					return ' [label="%s",weight=2]' % quote(k)
				else:
					return ' [label="%s"]' % quote(safe_repr(k))
	return ''

########NEW FILE########
__FILENAME__ = profiler
"""Profile the memory usage of a Python program"""

__version__ = '0.24'

_CMD_USAGE = "python -m memory_profiler script_file.py"

import time, sys, os, pdb
import warnings
import linecache
import inspect


# TODO: provide alternative when multprocessing is not available
try:
    from multiprocessing import Process, Pipe
except ImportError:
    from multiprocessing.dummy import Process, Pipe


try:
    import psutil

    def _get_memory(pid):
        process = psutil.Process(pid)
        try:
            mem = float(process.get_memory_info()[0]) / (1024 ** 2)
        except psutil.AccessDenied:
            mem = -1
        return mem


except ImportError:

    warnings.warn("psutil module not found. memory_profiler will be slow")

    import subprocess
    if os.name == 'posix':
        def _get_memory(pid):
            # ..
            # .. memory usage in MB ..
            # .. this should work on both Mac and Linux ..
            # .. subprocess.check_output appeared in 2.7, using Popen ..
            # .. for backwards compatibility ..
            out = subprocess.Popen(['ps', 'v', '-p', str(pid)],
                  stdout=subprocess.PIPE).communicate()[0].split(b'\n')
            try:
                vsz_index = out[0].split().index(b'RSS')
                return float(out[1].split()[vsz_index]) / 1024
            except:
                return -1
    else:
        raise NotImplementedError('The psutil module is required for non-unix '
                                  'platforms')


class Timer(Process):
    """
    Fetch memory consumption from over a time interval
    """

    def __init__(self, monitor_pid, interval, pipe, *args, **kw):
        self.monitor_pid = monitor_pid
        self.interval = interval
        self.pipe = pipe
        self.cont = True
        super(Timer, self).__init__(*args, **kw)

    def run(self):
        m = _get_memory(self.monitor_pid)
        timings = [m]
        self.pipe.send(0)  # we're ready
        while not self.pipe.poll(self.interval):
            m = _get_memory(self.monitor_pid)
            timings.append(m)
        self.pipe.send(timings)


def memory_usage(proc=-1, interval=.1, timeout=None):
    """
    Return the memory usage of a process or piece of code

    Parameters
    ----------
    proc : {int, string, tuple}, optional
        The process to monitor. Can be given by an integer
        representing a PID or by a tuple representing a Python
        function. The tuple contains three values (f, args, kw) and
        specifies to run the function f(*args, **kw).  Set to -1
        (default) for current process.

    interval : float, optional
        Interval at which measurements are collected.

    timeout : float, optional
        Maximum amount of time (in seconds) to wait before returning.

    Returns
    -------
    mem_usage : list of floating-poing values
        memory usage, in MB. It's length is always < timeout / interval
    """
    ret = []

    if timeout is not None:
        max_iter = int(timeout / interval)
    elif isinstance(proc, int):
        # external process and no timeout
        max_iter = 1
    else:
        # for a Python function wait until it finishes
        max_iter = float('inf')

    if isinstance(proc, (list, tuple)):

        if len(proc) == 1:
            f, args, kw = (proc[0], (), {})
        elif len(proc) == 2:
            f, args, kw = (proc[0], proc[1], {})
        elif len(proc) == 3:
            f, args, kw = (proc[0], proc[1], proc[2])
        else:
            raise ValueError

        aspec = inspect.getargspec(f)
        n_args = len(aspec.args)
        if aspec.defaults is not None:
            n_args -= len(aspec.defaults)
        if n_args != len(args):
            raise ValueError(
            'Function expects %s value(s) but %s where given'
            % (n_args, len(args)))

        child_conn, parent_conn = Pipe()  # this will store Timer's results
        p = Timer(os.getpid(), interval, child_conn)
        p.start()
        parent_conn.recv()  # wait until we start getting memory
        f(*args, **kw)
        parent_conn.send(0)  # finish timing
        ret = parent_conn.recv()
        p.join(5 * interval)
    else:
        # external process
        if proc == -1:
            proc = os.getpid()
        if max_iter == -1:
            max_iter = 1
        counter = 0
        while counter < max_iter:
            counter += 1
            ret.append(_get_memory(proc))
            time.sleep(interval)
    return ret

# ..
# .. utility functions for line-by-line ..

def _find_script(script_name):
    """ Find the script.

    If the input is not a file, then $PATH will be searched.
    """
    if os.path.isfile(script_name):
        return script_name
    path = os.getenv('PATH', os.defpath).split(os.pathsep)
    for folder in path:
        if folder == '':
            continue
        fn = os.path.join(folder, script_name)
        if os.path.isfile(fn):
            return fn

    sys.stderr.write('Could not find script {0}\n'.format(script_name))
    raise SystemExit(1)


class LineProfiler:
    """ A profiler that records the amount of memory for each line """

    def __init__(self, **kw):
        self.functions = list()
        self.code_map = {}
        self.enable_count = 0
        self.max_mem = kw.get('max_mem', None)

    def __call__(self, func):
        self.add_function(func)
        f = self.wrap_function(func)
        f.__module__ = func.__module__
        f.__name__ = func.__name__
        f.__doc__ = func.__doc__
        f.__dict__.update(getattr(func, '__dict__', {}))
        return f

    def add_function(self, func):
        """ Record line profiling information for the given Python function.
        """
        try:
            # func_code does not exist in Python3
            code = func.__code__
        except AttributeError:
            import warnings
            warnings.warn("Could not extract a code object for the object %r"
                          % (func,))
            return
        if code not in self.code_map:
            self.code_map[code] = {}
            self.functions.append(func)

    def wrap_function(self, func):
        """ Wrap a function to profile it.
        """

        def f(*args, **kwds):
            self.enable_by_count()
            try:
                result = func(*args, **kwds)
            finally:
                self.disable_by_count()
            return result
        return f

    def run(self, cmd):
        """ Profile a single executable statment in the main namespace.
        """
        import __main__
        main_dict = __main__.__dict__
        return self.runctx(cmd, main_dict, main_dict)

    def runctx(self, cmd, globals, locals):
        """ Profile a single executable statement in the given namespaces.
        """
        self.enable_by_count()
        try:
            exec(cmd, globals, locals)
        finally:
            self.disable_by_count()
        return self

    def runcall(self, func, *args, **kw):
        """ Profile a single function call.
        """
        # XXX where is this used ? can be removed ?
        self.enable_by_count()
        try:
            return func(*args, **kw)
        finally:
            self.disable_by_count()

    def enable_by_count(self):
        """ Enable the profiler if it hasn't been enabled before.
        """
        if self.enable_count == 0:
            self.enable()
        self.enable_count += 1

    def disable_by_count(self):
        """ Disable the profiler if the number of disable requests matches the
        number of enable requests.
        """
        if self.enable_count > 0:
            self.enable_count -= 1
            if self.enable_count == 0:
                self.disable()

    def trace_memory_usage(self, frame, event, arg):
        """Callback for sys.settrace"""
        if event in ('line', 'return') and frame.f_code in self.code_map:
            lineno = frame.f_lineno
            if event == 'return':
                lineno += 1
            entry = self.code_map[frame.f_code].setdefault(lineno, [])
            entry.append(_get_memory(os.getpid()))

        return self.trace_memory_usage

    def trace_max_mem(self, frame, event, arg):
        # run into PDB as soon as memory is higher than MAX_MEM
        if event in ('line', 'return') and frame.f_code in self.code_map:
            c = _get_memory(os.getpid())
            if c >= self.max_mem:
                t = 'Current memory {0:.2f} MB exceeded the maximum '.format(c) + \
                    'of {0:.2f} MB\n'.format(self.max_mem)
                sys.stdout.write(t)
                sys.stdout.write('Stepping into the debugger \n')
                frame.f_lineno -= 2
                p = pdb.Pdb()
                p.quitting = False
                p.stopframe = frame
                p.returnframe = None
                p.stoplineno = frame.f_lineno - 3
                p.botframe = None
                return p.trace_dispatch

        return self.trace_max_mem

    def __enter__(self):
        self.enable_by_count()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disable_by_count()

    def enable(self):
        if self.max_mem is not None:
            sys.settrace(self.trace_max_mem)
        else:
            sys.settrace(self.trace_memory_usage)

    def disable(self):
        self.last_time = {}
        sys.settrace(None)


def show_results(prof, stream=None, precision=3):
    if stream is None:
        stream = sys.stdout
    template = '{0:>6} {1:>12} {2:>12}   {3:<}'

    for code in prof.code_map:
        lines = prof.code_map[code]
        if not lines:
            # .. measurements are empty ..
            continue
        filename = code.co_filename
        if filename.endswith((".pyc", ".pyo")):
            filename = filename[:-1]
        stream.write('Filename: ' + filename + '\n\n')
        if not os.path.exists(filename):
            stream.write('ERROR: Could not find file ' + filename + '\n')
            if filename.startswith("ipython-input") or filename.startswith("<ipython-input"):
                print("NOTE: %mprun can only be used on functions defined in "
                      "physical files, and not in the IPython environment.")
            continue
        all_lines = linecache.getlines(filename)
        sub_lines = inspect.getblock(all_lines[code.co_firstlineno - 1:])
        linenos = range(code.co_firstlineno, code.co_firstlineno +
                        len(sub_lines))
        lines_normalized = {}

        header = template.format('Line #', 'Mem usage', 'Increment',
                                 'Line Contents')
        stream.write(header + '\n')
        stream.write('=' * len(header) + '\n')
        # move everything one frame up
        keys = sorted(lines.keys())

        k_old = keys[0] - 1
        lines_normalized[keys[0] - 1] = lines[keys[0]]
        for i in range(1, len(lines_normalized[keys[0] - 1])):
            lines_normalized[keys[0] - 1][i] = -1.
        k = keys.pop(0)
        while keys:
            lines_normalized[k] = lines[keys[0]]
            for i in range(len(lines_normalized[k_old]),
                           len(lines_normalized[k])):
                lines_normalized[k][i] = -1.
            k_old = k
            k = keys.pop(0)

        first_line = sorted(lines_normalized.keys())[0]
        mem_old = max(lines_normalized[first_line])
        precision = int(precision)
        template_mem = '{{0:{0}.{1}'.format(precision + 6, precision) + 'f} MB'
        for i, l in enumerate(linenos):
            mem = ''
            inc = ''
            if l in lines_normalized:
                mem = max(lines_normalized[l])
                inc = mem - mem_old
                mem_old = mem
                mem = template_mem.format(mem)
                inc = template_mem.format(inc)
            stream.write(template.format(l, mem, inc, sub_lines[i]))
        stream.write('\n\n')


# A lprun-style %mprun magic for IPython.
def magic_mprun(self, parameter_s=''):
    """ Execute a statement under the line-by-line memory profiler from the
    memory_profilser module.

    Usage:
      %mprun -f func1 -f func2 <statement>

    The given statement (which doesn't require quote marks) is run via the
    LineProfiler. Profiling is enabled for the functions specified by the -f
    options. The statistics will be shown side-by-side with the code through
    the pager once the statement has completed.

    Options:

    -f <function>: LineProfiler only profiles functions and methods it is told
    to profile.  This option tells the profiler about these functions. Multiple
    -f options may be used. The argument may be any expression that gives
    a Python function or method object. However, one must be careful to avoid
    spaces that may confuse the option parser. Additionally, functions defined
    in the interpreter at the In[] prompt or via %run currently cannot be
    displayed.  Write these functions out to a separate file and import them.

    One or more -f options are required to get any useful results.

    -T <filename>: dump the text-formatted statistics with the code
    side-by-side out to a text file.

    -r: return the LineProfiler object after it has completed profiling.
    """
    try:
        from StringIO import StringIO
    except ImportError: # Python 3.x
        from io import StringIO

    # Local imports to avoid hard dependency.
    from distutils.version import LooseVersion
    import IPython
    ipython_version = LooseVersion(IPython.__version__)
    if ipython_version < '0.11':
        from IPython.genutils import page
        from IPython.ipstruct import Struct
        from IPython.ipapi import UsageError
    else:
        from IPython.core.page import page
        from IPython.utils.ipstruct import Struct
        from IPython.core.error import UsageError

    # Escape quote markers.
    opts_def = Struct(T=[''], f=[])
    parameter_s = parameter_s.replace('"', r'\"').replace("'", r"\'")
    opts, arg_str = self.parse_options(parameter_s, 'rf:T:', list_all=True)
    opts.merge(opts_def)
    global_ns = self.shell.user_global_ns
    local_ns = self.shell.user_ns

    # Get the requested functions.
    funcs = []
    for name in opts.f:
        try:
            funcs.append(eval(name, global_ns, local_ns))
        except Exception as e:
            raise UsageError('Could not find function %r.\n%s: %s' % (name,
                e.__class__.__name__, e))

    profile = LineProfiler()
    for func in funcs:
        profile(func)

    # Add the profiler to the builtins for @profile.
    try:
        import builtins
    except ImportError:  # Python 3x
        import __builtin__ as builtins

    if 'profile' in builtins.__dict__:
        had_profile = True
        old_profile = builtins.__dict__['profile']
    else:
        had_profile = False
        old_profile = None
    builtins.__dict__['profile'] = profile

    try:
        try:
            profile.runctx(arg_str, global_ns, local_ns)
            message = ''
        except SystemExit:
            message = "*** SystemExit exception caught in code being profiled."
        except KeyboardInterrupt:
            message = ("*** KeyboardInterrupt exception caught in code being "
                "profiled.")
    finally:
        if had_profile:
            builtins.__dict__['profile'] = old_profile

    # Trap text output.
    stdout_trap = StringIO()
    show_results(profile, stdout_trap)
    output = stdout_trap.getvalue()
    output = output.rstrip()

    if ipython_version < '0.11':
        page(output, screen_lines=self.shell.rc.screen_length)
    else:
        page(output)
    print(message,)

    text_file = opts.T[0]
    if text_file:
        with open(text_file, 'w') as pfile:
            pfile.write(output)
        print('\n*** Profile printout saved to text file %s. %s' % (text_file,
                                                                    message))

    return_value = None
    if 'r' in opts:
        return_value = profile

    return return_value


def _func_exec(stmt, ns):
    # helper for magic_memit, just a function proxy for the exec
    # statement
    exec(stmt, ns)

# a timeit-style %memit magic for IPython
def magic_memit(self, line=''):
    """Measure memory usage of a Python statement

    Usage, in line mode:
      %memit [-ir<R>t<T>] statement

    Options:
    -r<R>: repeat the loop iteration <R> times and take the best result.
    Default: 1

    -t<T>: timeout after <T> seconds. Unused if `-i` is active. Default: None

    Examples
    --------
    ::

      In [1]: import numpy as np

      In [2]: %memit np.zeros(1e7)
      maximum of 1: 76.402344 MB per loop

      In [3]: %memit np.ones(1e6)
      maximum of 1: 7.820312 MB per loop

      In [4]: %memit -r 10 np.empty(1e8)
      maximum of 10: 0.101562 MB per loop

      In [5]: memit -t 3 while True: pass;
      Subprocess timed out.
      Subprocess timed out.
      Subprocess timed out.
      ERROR: all subprocesses exited unsuccessfully. Try again with the `-i`
      option.
      maximum of 1: -inf MB per loop

    """
    opts, stmt = self.parse_options(line, 'r:t:i', posix=False, strict=False)
    repeat = int(getattr(opts, 'r', 1))
    if repeat < 1:
        repeat == 1
    timeout = int(getattr(opts, 't', 0))
    if timeout <= 0:
        timeout = None

    mem_usage = memory_usage((_func_exec, (stmt, self.shell.user_ns)), timeout=timeout)

    if mem_usage:
        print('maximum of %d: %f MB per loop' % (repeat, max(mem_usage)))
    else:
        print('ERROR: could not read memory usage, try with a lower interval or more iterations')


def load_ipython_extension(ip):
    """This is called to load the module as an IPython extension."""
    ip.define_magic('mprun', magic_mprun)
    ip.define_magic('memit', magic_memit)


def profile(func, stream=None):
    """
    Decorator that will run the function and print a line-by-line profile
    """
    def wrapper(*args, **kwargs):
        prof = LineProfiler()
        val = prof(func)(*args, **kwargs)
        show_results(prof, stream=stream)
        return val
    return wrapper


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser(usage=_CMD_USAGE, version=__version__)
    parser.disable_interspersed_args()
    parser.add_option("--pdb-mmem", dest="max_mem", metavar="MAXMEM",
        type="float", action="store",
        help="step into the debugger when memory exceeds MAXMEM")
    parser.add_option('--precision', dest="precision", type="int",
        action="store", default=3,
        help="precision of memory output in number of significant digits")

    if not sys.argv[1:]:
        parser.print_help()
        sys.exit(2)

    (options, args) = parser.parse_args()

    prof = LineProfiler(max_mem=options.max_mem)
    __file__ = _find_script(args[0])
    try:
        if sys.version_info[0] < 3:
            import __builtin__
            __builtin__.__dict__['profile'] = prof
            ns = locals()
            ns['profile'] = prof # shadow the profile decorator defined above
            execfile(__file__, ns, ns)
        else:
            import builtins
            builtins.__dict__['profile'] = prof
            ns = locals()
            ns['profile'] = prof # shadow the profile decorator defined above
            exec(compile(open(__file__).read(), __file__, 'exec'), ns,
                                                                   globals())
    finally:
        show_results(prof, precision=options.precision)

########NEW FILE########
__FILENAME__ = family
# encoding: utf-8
"""
address.py

Created by Thomas Mangin on 2010-01-19.
Copyright (c) 2009-2013  Exa Networks. All rights reserved.
"""

from struct import pack

# =================================================================== AFI

# http://www.iana.org/assignments/address-family-numbers/
class AFI (int):
	ipv4 = 0x01
	ipv6 = 0x02

	Family = {
		ipv4 : 0x02,  # socket.AF_INET,
		ipv6 : 0x30,  # socket.AF_INET6,
	}

	def __str__ (self):
		if self == 0x01: return "ipv4"
		if self == 0x02: return "ipv6"
		return "unknown afi"

	def name (self):
		if self == 0x01: return "inet4"
		if self == 0x02: return "inet6"
		return "unknown afi"

	def pack (self):
		return pack('!H',self)

	@staticmethod
	def value (name):
		if name == "ipv4": return AFI.ipv4
		if name == "ipv6": return AFI.ipv6
		return None

# =================================================================== SAFI

# http://www.iana.org/assignments/safi-namespace
class SAFI (int):
	unicast_multicast = 0       # internal
	unicast = 1                 # [RFC4760]
	multicast = 2               # [RFC4760]
#	deprecated = 3              # [RFC4760]
	nlri_mpls = 4               # [RFC3107]
#	mcast_vpn = 5               # [draft-ietf-l3vpn-2547bis-mcast-bgp] (TEMPORARY - Expires 2008-06-19)
#	pseudowire = 6              # [draft-ietf-pwe3-dynamic-ms-pw] (TEMPORARY - Expires 2008-08-23) Dynamic Placement of Multi-Segment Pseudowires
#	encapsulation = 7           # [RFC5512]
#
#	tunel = 64                  # [Nalawade]
#	vpls = 65                   # [RFC4761]
#	bgp_mdt = 66                # [Nalawade]
#	bgp_4over6 = 67             # [Cui]
#	bgp_6over4 = 67             # [Cui]
#	vpn_adi = 69                # [RFC-ietf-l1vpn-bgp-auto-discovery-05.txt]
#
	mpls_vpn = 128              # [RFC4364]
#	mcast_bgp_mpls_vpn = 129    # [RFC2547]
#	rt = 132                    # [RFC4684]
	flow_ip = 133               # [RFC5575]
	flow_vpn = 134              # [RFC5575]
#
#	vpn_ad = 140                # [draft-ietf-l3vpn-bgpvpn-auto]
#
#	private = [_ for _ in range(241,254)]   # [RFC4760]
#	unassigned = [_ for _ in range(8,64)] + [_ for _ in range(70,128)]
#	reverved = [0,3] + [130,131] + [_ for _ in range(135,140)] + [_ for _ in range(141,241)] + [255,]    # [RFC4760]

	def name (self):
		if self == 0x01: return "unicast"
		if self == 0x02: return "multicast"
		if self == 0x04: return "nlri-mpls"
		if self == 0x80: return "mpls-vpn"
		if self == 0x85: return "flow"
		if self == 0x86: return "flow-vpn"
		return "unknown safi"

	def __str__ (self):
		return self.name()

	def pack (self):
		return chr(self)

	def has_label (self):
		return self in (self.nlri_mpls,self.mpls_vpn)

	def has_rd (self):
		return self in (self.mpls_vpn,)  # technically self.flow_vpn has an RD but it is not an NLRI

	@staticmethod
	def value (name):
		if name == "unicast"  : return 0x01
		if name == "multicast": return 0x02
		if name == "nlri-mpls": return 0x04
		if name == "mpls-vpn" : return 0x80
		if name == "flow"     : return 0x85
		if name == "flow-vpn" : return 0x86
		return None

def known_families ():
	# it can not be a generator
	families = []
	families.append((AFI(AFI.ipv4),SAFI(SAFI.unicast)))
	families.append((AFI(AFI.ipv4),SAFI(SAFI.multicast)))
	families.append((AFI(AFI.ipv4),SAFI(SAFI.nlri_mpls)))
	families.append((AFI(AFI.ipv4),SAFI(SAFI.mpls_vpn)))
	families.append((AFI(AFI.ipv4),SAFI(SAFI.flow_ip)))
	families.append((AFI(AFI.ipv4),SAFI(SAFI.flow_vpn)))
	families.append((AFI(AFI.ipv6),SAFI(SAFI.unicast)))
	families.append((AFI(AFI.ipv6),SAFI(SAFI.mpls_vpn)))
	families.append((AFI(AFI.ipv6),SAFI(SAFI.flow_ip)))
	families.append((AFI(AFI.ipv6),SAFI(SAFI.flow_vpn)))
	return families

########NEW FILE########
__FILENAME__ = address
# encoding: utf-8
"""
address.py

Created by Thomas Mangin on 2012-07-16.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.protocol.family import AFI,SAFI

## =================================================================== Address

class Address (object):
	def __init__ (self,afi,safi):
		self.afi = AFI(afi)
		self.safi = SAFI(safi)

	def family (self):
		return (self.afi,self.safi)

	def address (self):
		return "%s %s" % (str(self.afi),str(self.safi))

	def __str__ (self):
		return self.address()

########NEW FILE########
__FILENAME__ = fragment
# encoding: utf-8
"""
fragment.py

Created by Thomas Mangin on 2010-02-04.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

# =================================================================== Fragment

class Fragment (int):
#	reserved  = 0xF0
	DONT      = 0x08
	IS        = 0x40
	FIRST     = 0x20
	LAST      = 0x10

	def __str__ (self):
		if self == 0x00:       return 'not-a-fragment'
		if self == self.DONT:  return 'dont-fragment'
		if self == self.IS:    return 'is-fragment'
		if self == self.FIRST: return 'first-fragment'
		if self == self.LAST:  return 'last-fragment'
		return 'unknown fragment value %d' % int(self)

def NamedFragment (name):
	fragment = name.lower()
	if fragment == 'not-a-fragment': return Fragment(0x00)
	if fragment == 'dont-fragment':  return Fragment(Fragment.DONT)
	if fragment == 'is-fragment':    return Fragment(Fragment.IS)
	if fragment == 'first-fragment': return Fragment(Fragment.FIRST)
	if fragment == 'last-fragment':  return Fragment(Fragment.LAST)
	raise ValueError('invalid fragment name %s' % fragment)

########NEW FILE########
__FILENAME__ = icmp
# encoding: utf-8
"""
icmp.py

Created by Thomas Mangin on 2010-01-15.
Copyright (c) 2009-2013  Exa Networks. All rights reserved.
"""

# =================================================================== ICMP Code Field

# http://www.iana.org/assignments/icmp-parameters
class ICMPType (int):
	ECHO_REPLY               = 0x00
	DESTINATION_UNREACHEABLE = 0x03
	SOURCE_QUENCH            = 0x04
	REDIRECT                 = 0x05
	ECHO_REQUEST             = 0x08
	ROUTER_ADVERTISEMENT     = 0x09
	ROUTER_SOLICIT           = 0x0A
	TIME_EXCEEDED            = 0x0B
	PARAMETER_PROBLEM        = 0x0C
	TIMESTAMP_REQUEST        = 0x0D  # wonder why junos call all the other ones _REQUEST but not this one
	TIMESTAMP_REPLY          = 0x0E
	INFO_REQUEST             = 0x0F
	INFO_REPLY               = 0x10
	MASK_REQUEST             = 0x11
	MASK_REPLY               = 0x12
	TRACEROUTE               = 0x1E

	def __str__ (self):
		if self == ICMPType.ECHO_REPLY:               return 'echo-reply'
		if self == ICMPType.ECHO_REQUEST:             return 'echo-request'
		if self == ICMPType.INFO_REPLY:               return 'info-reply'
		if self == ICMPType.INFO_REQUEST:             return 'info-request'
		if self == ICMPType.MASK_REPLY:               return 'mask-reply'
		if self == ICMPType.MASK_REQUEST:             return 'mask-request'
		if self == ICMPType.PARAMETER_PROBLEM:        return 'parameter-problem'
		if self == ICMPType.REDIRECT:                 return 'redirect'
		if self == ICMPType.ROUTER_ADVERTISEMENT:     return 'router-advertisement'
		if self == ICMPType.ROUTER_SOLICIT:           return 'router-solicit'
		if self == ICMPType.SOURCE_QUENCH:            return 'source-quench'
		if self == ICMPType.TIME_EXCEEDED:            return 'time-exceeded'
		if self == ICMPType.TIMESTAMP_REQUEST:        return 'timestamp'
		if self == ICMPType.TIMESTAMP_REPLY:          return 'timestamp-reply'
		if self == ICMPType.DESTINATION_UNREACHEABLE: return 'unreachable'
		return 'invalid icmp type %d' % int(self)

def NamedICMPType (name):
	icmp = name.lower()
	if icmp == 'echo-reply':          return ICMPType.ECHO_REPLY
	if icmp == 'echo-request':        return ICMPType.ECHO_REQUEST
	if icmp == 'info-reply':          return ICMPType.INFO_REPLY
	if icmp == 'info-request':        return ICMPType.INFO_REQUEST
	if icmp == 'mask-reply':          return ICMPType.MASK_REPLY
	if icmp == 'mask-request':        return ICMPType.MASK_REQUEST
	if icmp == 'parameter-problem':   return ICMPType.PARAMETER_PROBLEM
	if icmp == 'redirect':            return ICMPType.REDIRECT
	if icmp == 'router-advertisement':return ICMPType.ROUTER_ADVERTISEMENT
	if icmp == 'router-solicit':      return ICMPType.ROUTER_SOLICIT
	if icmp == 'source-quench':       return ICMPType.SOURCE_QUENCH
	if icmp == 'time-exceeded':       return ICMPType.TIME_EXCEEDED
	if icmp == 'timestamp':           return ICMPType.TIMESTAMP_REQUEST
	if icmp == 'timestamp-reply':     return ICMPType.TIMESTAMP_REPLY
	if icmp == 'unreachable':         return ICMPType.DESTINATION_UNREACHEABLE
	raise ValueError('unknow icmp type %s' % icmp)


# http://www.iana.org/assignments/icmp-parameters
class ICMPCode (int):
	# Destination Unreacheable (type 3)
	NETWORK_UNREACHABLE                   = 0x0
	HOST_UNREACHABLE                      = 0x1
	PROTOCOL_UNREACHABLE                  = 0x2
	PORT_UNREACHABLE                      = 0x3
	FRAGMENTATION_NEEDED                  = 0x4
	SOURCE_ROUTE_FAILED                   = 0x5
	DESTINATION_NETWORK_UNKNOWN           = 0x6
	DESTINATION_HOST_UNKNOWN              = 0x7
	SOURCE_HOST_ISOLATED                  = 0x8
	DESTINATION_NETWORK_PROHIBITED        = 0x9
	DESTINATION_HOST_PROHIBITED           = 0xA
	NETWORK_UNREACHABLE_FOR_TOS           = 0xB
	HOST_UNREACHABLE_FOR_TOS              = 0xC
	COMMUNICATION_PROHIBITED_BY_FILTERING = 0xD
	HOST_PRECEDENCE_VIOLATION             = 0xE
	PRECEDENCE_CUTOFF_IN_EFFECT           = 0xF

	# Redirect (Type 5)
	REDIRECT_FOR_NETWORK                  = 0x0
	REDIRECT_FOR_HOST                     = 0x1
	REDIRECT_FOR_TOS_AND_NET              = 0x2
	REDIRECT_FOR_TOS_AND_HOST             = 0x3

	# Time Exceeded (Type 11)
	TTL_EQ_ZERO_DURING_TRANSIT            = 0x0
	TTL_EQ_ZERO_DURING_REASSEMBLY         = 0x1

	# parameter Problem (Type 12)
	REQUIRED_OPTION_MISSING               = 0x1
	IP_HEADER_BAD                         = 0x2

	def __str__ (self):
		return 'icmp code %d' % int(self)

def NamedICMPCode (name):
	icmp = name.lower()
	if icmp == 'communication-prohibited-by-filtering': return ICMPCode.COMMUNICATION_PROHIBITED_BY_FILTERING
	if icmp == 'destination-host-prohibited':           return ICMPCode.DESTINATION_HOST_PROHIBITED
	if icmp == 'destination-host-unknown':              return ICMPCode.DESTINATION_HOST_UNKNOWN
	if icmp == 'destination-network-prohibited':        return ICMPCode.DESTINATION_NETWORK_PROHIBITED
	if icmp == 'destination-network-unknown':           return ICMPCode.DESTINATION_NETWORK_UNKNOWN
	if icmp == 'fragmentation-needed':                  return ICMPCode.FRAGMENTATION_NEEDED
	if icmp == 'host-precedence-violation':             return ICMPCode.HOST_PRECEDENCE_VIOLATION
	if icmp == 'host-unreachable':                      return ICMPCode.HOST_UNREACHABLE
	if icmp == 'host-unreachable-for-tos':              return ICMPCode.HOST_UNREACHABLE_FOR_TOS
	if icmp == 'ip-header-bad':                         return ICMPCode.IP_HEADER_BAD
	if icmp == 'network-unreachable':                   return ICMPCode.NETWORK_UNREACHABLE
	if icmp == 'network-unreachable-for-tos':           return ICMPCode.NETWORK_UNREACHABLE_FOR_TOS
	if icmp == 'port-unreachable':                      return ICMPCode.PORT_UNREACHABLE
	if icmp == 'precedence-cutoff-in-effect':           return ICMPCode.PRECEDENCE_CUTOFF_IN_EFFECT
	if icmp == 'protocol-unreachable':                  return ICMPCode.PROTOCOL_UNREACHABLE
	if icmp == 'redirect-for-host':                     return ICMPCode.REDIRECT_FOR_HOST
	if icmp == 'redirect-for-network':                  return ICMPCode.REDIRECT_FOR_NETWORK
	if icmp == 'redirect-for-tos-and-host':             return ICMPCode.REDIRECT_FOR_TOS_AND_HOST
	if icmp == 'redirect-for-tos-and-net':              return ICMPCode.REDIRECT_FOR_TOS_AND_NET
	if icmp == 'required-option-missing':               return ICMPCode.REQUIRED_OPTION_MISSING
	if icmp == 'source-host-isolated':                  return ICMPCode.SOURCE_HOST_ISOLATED
	if icmp == 'source-route-failed':                   return ICMPCode.SOURCE_ROUTE_FAILED
	if icmp == 'ttl-eq-zero-during-reassembly':         return ICMPCode.TTL_EQ_ZERO_DURING_REASSEMBLY
	if icmp == 'ttl-eq-zero-during-transit':            return ICMPCode.TTL_EQ_ZERO_DURING_TRANSIT
	raise ValueError('unknow icmp-code %s' % icmp)

########NEW FILE########
__FILENAME__ = inet
# encoding: utf-8
"""
ip.py

Created by Thomas Mangin on 2010-01-15.
Copyright (c) 2009-2013  Exa Networks. All rights reserved.
"""

import socket

from exabgp.protocol.family import AFI,SAFI
from exabgp.protocol.ip.address import Address

def _detect_afi(ip):
	if ip.count(':'):
		return AFI.ipv6
	return AFI.ipv4

def _detect_safi (ip):
	if '.' in ip and int(ip.split('.')[0]) in Inet._multicast_range:
		return SAFI.multicast
	else:
		return SAFI.unicast

def inet (ip):
	afi = _detect_afi(ip)
	safi = _detect_safi(ip)
	return afi,safi,socket.inet_pton(Inet._af[afi],ip)

def pton (ip):
	afi = _detect_afi(ip)
	return socket.inet_pton(Inet._af[afi],ip)

def rawinet (packed):
	afi = AFI.ipv4 if len(packed) == 4 else AFI.ipv6
	safi = SAFI.multicast if ord(packed[0]) in Inet._multicast_range else SAFI.unicast
	return afi,safi,packed

class Inet (Address):
	_UNICAST = SAFI(SAFI.unicast)
	_MULTICAST = SAFI(SAFI.multicast)

	_multicast_range = set(range(224,240))  # 239 is last

	"""An IP in the 4 bytes format"""
	# README: yep, we should surely change this _ name here
	_af = {
		AFI.ipv4: socket.AF_INET,
		AFI.ipv6: socket.AF_INET6,
	}

	_afi = {
		socket.AF_INET : AFI.ipv4,
		socket.AF_INET6: AFI.ipv6,
	}

	length = {
		AFI.ipv4:  4,
		AFI.ipv6: 16,
	}

	def __init__ (self,afi,safi,packed):
		if safi:  # XXX: FIXME: we use a constant which is zero - reference it explicitly
			Address.__init__(self,afi,safi)
		elif ord(packed[0]) in self._multicast_range:
			Address.__init__(self,afi,self._MULTICAST)
		else:
			Address.__init__(self,afi,self._UNICAST)

		self.packed = packed
		self.ip = socket.inet_ntop(self._af[self.afi],self.packed)

	def pack (self):
		return self.packed

	def __len__ (self):
		return len(self.packed)

	def inet (self):
		return self.ip

	def __str__ (self):
		return self.inet()

	def __cmp__ (self,other):
		if self.packed == other.packed:
			return 0
		if self.packed < other.packed:
			return -1
		return 1

	def __repr__ (self):
		return "<%s value %s>" % (str(self.__class__).split("'")[1].split('.')[-1],str(self))

########NEW FILE########
__FILENAME__ = flag
# encoding: utf-8
"""
tcpflags.py

Created by Thomas Mangin on 2010-02-04.
Copyright (c) 2009-2013  Exa Networks. All rights reserved.
"""

# http://www.iana.org/assignments/tcp-header-flags
class TCPFlag (int):
	FIN    = 0x1
	SYN    = 0x2
	RST  = 0x4
	PUSH   = 0x8
	ACK    = 0x10
	URGENT = 0x20

	def __str__ (self):
		if self == self.FIN:    return 'fin'
		if self == self.SYN:    return 'syn'
		if self == self.RST:    return 'rst'
		if self == self.PUSH:   return 'push'
		if self == self.ACK:    return 'ack'
		if self == self.URGENT: return 'urgent'
		return 'invalid tcp flag %d' % int(self)

def NamedTCPFlag (name):
	flag = name.lower()
	if flag == 'fin':    return TCPFlag(TCPFlag.FIN)
	if flag == 'syn':    return TCPFlag(TCPFlag.SYN)
	if flag == 'rst':    return TCPFlag(TCPFlag.RST)
	if flag == 'push':   return TCPFlag(TCPFlag.PUSH)
	if flag == 'ack':    return TCPFlag(TCPFlag.ACK)
	if flag == 'urgent': return TCPFlag(TCPFlag.URGENT)
	raise ValueError('invalid flag name %s' % flag)

########NEW FILE########
__FILENAME__ = encoding
#!/usr/bin/env python
# encoding: utf-8
"""
api.py

Created by Thomas Mangin on 2012-12-30.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import time

from exabgp.bgp.message.direction import IN

class APIOptions (object):
	def __init__ (self):
		self.neighbor_changes = False
		self.receive_packets = False
		self.send_packets = False
		self.receive_routes = False
		self.receive_operational = False

def hexstring (value):
	def spaced (value):
		for v in value:
			yield '%02X' % ord(v)
	return ''.join(spaced(value))


class Text (object):
	def __init__ (self,version):
		self.version = version

	def up (self,neighbor):
		return 'neighbor %s up\n' % neighbor

	def connected (self,neighbor):
		return 'neighbor %s connected\n' % neighbor

	def down (self,neighbor,reason=''):
		return 'neighbor %s down - %s\n' % (neighbor,reason)

	def shutdown (self):
		return 'shutdown'

	def receive (self,neighbor,category,header,body):
		return 'neighbor %s received %d header %s body %s\n' % (neighbor,category,hexstring(header),hexstring(body))

	def send (self,neighbor,category,header,body):
		return 'neighbor %s sent %d header %s body %s\n' % (neighbor,category,hexstring(header),hexstring(body))

	def update (self,neighbor,update):
		r = 'neighbor %s update start\n' % neighbor
		attributes = str(update.attributes)
		for nlri in update.nlris:
			if nlri.action == IN.announced:
				if nlri.nexthop:
					r += 'neighbor %s announced route %s next-hop %s%s\n' % (neighbor,nlri.nlri(),nlri.nexthop.inet(),attributes)
				else:
					# This is an EOR
					r += 'neighbor %s announced %s %s\n' % (neighbor,nlri.nlri(),attributes)
			else:
				r += 'neighbor %s withdrawn route %s\n' % (neighbor,nlri.nlri())
		r += 'neighbor %s update end\n' % neighbor
		return r

	def refresh (self,neighbor,refresh):
		return 'neighbor %s route-refresh afi %s safi %s %s' % (
			neighbor,refresh.afi,refresh.safi,refresh.reserved
		)

	def _operational_advisory (self,neighbor,operational):
		return 'neighbor %s operational %s afi %s safi %s advisory "%s"' % (
			neighbor,operational.name,operational.afi,operational.safi,operational.data
		)

	def _operational_query (self,neighbor,operational):
		return 'neighbor %s operational %s afi %s safi %s' % (
			neighbor,operational.name,operational.afi,operational.safi
		)

	def _operational_counter (self,neighbor,operational):
		return 'neighbor %s operational %s afi %s safi %s router-id %s sequence %d counter %d' % (
			neighbor,operational.name,operational.afi,operational.safi,operational.routerid,operational.sequence,operational.counter
		)

	def operational (self,neighbor,what,operational):
		if what == 'advisory':
			return self._operational_advisory(neighbor,operational)
		elif what == 'query':
			return self._operational_query(neighbor,operational)
		elif what == 'counter':
			return self._operational_counter(neighbor,operational)
		elif what == 'interface':
			return self._operational_interface(neighbor,operational)
		else:
			raise RuntimeError('the code is broken, we are trying to print a unknown type of operational message')

class JSON (object):
	def __init__ (self,version):
		self.version = version

	def _string (self,_):
		return '%s' % _ if issubclass(_.__class__,int) or issubclass(_.__class__,long) else '"%s"' %_

	def _header (self,content):
		return \
		'{ '\
			'"exabgp": "%s", '\
			'"time": %s, ' \
			'%s' \
		'}' % (self.version,time.time(),content)

	def _neighbor (self,neighbor,content):
		return \
		'"neighbor": { ' \
			'"ip": "%s", ' \
			'%s' \
		'} '% (neighbor,content)

	def _bmp (self,neighbor,content):
		return \
		'"bmp": { ' \
			'"ip": "%s", ' \
			'%s' \
		'} '% (neighbor,content)

	def _kv (self,extra):
		return ", ".join('"%s": %s' % (_,self._string(__)) for (_,__) in extra.iteritems()) + ' '

	def _minimalkv (self,extra):
		return ", ".join('"%s": %s' % (_,self._string(__)) for (_,__) in extra.iteritems() if __) + ' '

	def up (self,neighbor):
		return self._header(self._neighbor(neighbor,self._kv({'state':'up'})))

	def connected (self,neighbor):
		return self._header(self._neighbor(neighbor,self._kv({'state':'connected'})))

	def down (self,neighbor,reason=''):
		return self._header(self._neighbor(neighbor,self._kv({'state':'down','reason':reason})))

	def shutdown (self):
		return self._header(self._kv({'notification':'shutdown'}))

	def receive (self,neighbor,category,header,body):
		return self._header(self._neighbor(neighbor,'"message": { %s } ' % self._minimalkv({'received':category,'header':hexstring(header),'body':hexstring(body)})))

	def send (self,neighbor,category,header,body):
		return self._header(self._neighbor(neighbor,'"message": { %s } ' % self._minimalkv({'sent':category,'header':hexstring(header),'body':hexstring(body)})))

	def _update (self,update):
		plus = {}
		minus = {}

		# all the next-hops should be the same but let's not assume it

		for nlri in update.nlris:
			nexthop = nlri.nexthop.inet() if nlri.nexthop else 'null'
			if nlri.action == IN.announced:
				plus.setdefault(nlri.family(),{}).setdefault(nexthop,[]).append(nlri)
			if nlri.action == IN.withdrawn:
				minus.setdefault(nlri.family(),[]).append(nlri)

		add = []
		for family in plus:
			s  = '"%s %s": { ' % family
			m = ''
			for nexthop in plus[family]:
				nlris = plus[family][nexthop]
				m += '"%s" : { ' % nexthop
				m += ', '.join('%s' % nlri.json() for nlri in nlris)
				m += ' }, '
			s = m[:-2]
			add.append(s)

		remove = []
		for family in minus:
			nlris = minus[family]
			s  = '"%s %s": { ' % family
			s += ', '.join('%s' % nlri.json() for nlri in nlris)
			s += ' }'
			remove.append(s)

		nlri = ''
		if add: nlri += '"announce": { %s }' % ', '.join(add)
		if add and remove: nlri += ', '
		if remove: nlri+= '"withdraw": { %s }' % ', '.join(remove)

		attributes = '' if not update.attributes else '"attribute": { %s }' % update.attributes.json()
		if not attributes or not nlri:
			return '"update": { %s%s } ' % (attributes,nlri)
		return '"update": { %s, %s } ' % (attributes,nlri)

	def update (self,neighbor,update):
		return self._header(self._neighbor(neighbor,self._update(update)))

	def refresh (self,neighbor,refresh):
		return self._header(
			self._neighbor(
				neighbor,
				'"route-refresh": { "afi": "%s", "safi": "%s", "subtype": "%s"' % (
					refresh.afi,refresh.safi,refresh.reserved
				)
			)
		)

	def bmp (self,bmp,update):
		return self._header(self._bmp(bmp,self._update(update)))

	def _operational_advisory (self,neighbor,operational):
		return self._header(
			self._neighbor(
				neighbor,
				'"operational": { "name": "%s", "afi": "%s", "safi": "%s", "advisory": "%s"' % (
					operational.name,operational.afi,operational.safi,operational.data
				)
			)
		)

	def _operational_query (self,neighbor,operational):
		return self._header(
			self._neighbor(
				neighbor,
				'"operational": { "name": "%s", "afi": "%s", "safi": "%s"' % (
					operational.name,operational.afi,operational.safi
				)
			)
		)

	def _operational_counter (self,neighbor,operational):
		return self._header(
			self._neighbor(
				neighbor,
				'"operational": { "name": "%s", "afi": "%s", "safi": "%s", "router-id": "%s", "sequence": %d, "counter": %d' % (
					operational.name,operational.afi,operational.safi,operational.routerid,operational.sequence,operational.counter
				)
			)
		)

	def operational (self,neighbor,what,operational):
		if what == 'advisory':
			return self._operational_advisory(neighbor,operational)
		elif what == 'query':
			return self._operational_query(neighbor,operational)
		elif what == 'counter':
			return self._operational_counter(neighbor,operational)
		elif what == 'interface':
			return self._operational_interface(neighbor,operational)
		else:
			raise RuntimeError('the code is broken, we are trying to print a unknown type of operational message')

########NEW FILE########
__FILENAME__ = processes
"""
process.py

Created by Thomas Mangin on 2011-05-02.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import os
import errno
import time
import subprocess
import select
import fcntl

from exabgp.util.errstr import errstr

from exabgp.reactor.api.encoding import Text,JSON
from exabgp.configuration.file import formated
from exabgp.logger import Logger

class ProcessError (Exception):
	pass

def preexec_helper ():
	# make this process a new process group
	#os.setsid()
	# This prevent the signal to be sent to the children (and create a new process group)
	os.setpgrp()
	#signal.signal(signal.SIGINT, signal.SIG_IGN)

class Processes (object):
	# how many time can a process can respawn in the time interval
	respawn_number = 5
	respawn_timemask = 0xFFFFFF - pow(2,6) + 1  # '0b111111111111111111000000' (around a minute, 63 seconds)

	def __init__ (self,reactor):
		self.logger = Logger()
		self.reactor = reactor
		self.clean()
		self.silence = False

	def clean (self):
		self._process = {}
		self._api = {}
		self._api_encoder = {}
		self._neighbor_process = {}
		self._broken = []
		self._respawning = {}

	def _terminate (self,process):
		self.logger.processes("Terminating process %s" % process)
		self._process[process].terminate()
		self._process[process].wait()
		del self._process[process]

	def terminate (self):
		for process in list(self._process):
			if not self.silence:
				try:
					self.write(process,self._api_encoder[process].shutdown())
				except ProcessError:
					pass
		self.silence = True
		time.sleep(0.1)
		for process in list(self._process):
			try:
				self._terminate(process)
			except OSError:
				# we most likely received a SIGTERM signal and our child is already dead
				self.logger.processes("child process %s was already dead" % process)
				pass
		self.clean()

	def _start (self,process):
		try:
			if process in self._process:
				self.logger.processes("process already running")
				return
			if not process in self.reactor.configuration.process:
				self.logger.processes("Can not start process, no configuration for it (anymore ?)")
				return

			# Prevent some weird termcap data to be created at the start of the PIPE
			# \x1b[?1034h (no-eol) (esc)
			os.environ['TERM']='dumb'

			run = self.reactor.configuration.process[process].get('run','')
			if run:
				api = self.reactor.configuration.process[process]['encoder']
				self._api_encoder[process] = JSON('3.3.2') if api == 'json' else Text('3.3.2')

				self._process[process] = subprocess.Popen(run,
					stdin=subprocess.PIPE,
					stdout=subprocess.PIPE,
					preexec_fn=preexec_helper
					# This flags exists for python 2.7.3 in the documentation but on on my MAC
					# creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
				)
				fcntl.fcntl(self._process[process].stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)

				self.logger.processes("Forked process %s" % process)

				around_now = int(time.time()) & self.respawn_timemask
				if process in self._respawning:
					if around_now in self._respawning[process]:
						self._respawning[process][around_now] += 1
						# we are respawning too fast
						if self._respawning[process][around_now] > self.respawn_number:
							self.logger.processes("Too many respawn for %s (%d) terminating program" % (process,self.respawn_number),'critical')
							raise ProcessError()
					else:
						# reset long time since last respawn
						self._respawning[process] = {around_now: 1}
				else:
					# record respawing
					self._respawning[process] = {around_now: 1}

			neighbor = self.reactor.configuration.process[process]['neighbor']
			self._neighbor_process.setdefault(neighbor,[]).append(process)
		except (subprocess.CalledProcessError,OSError,ValueError),e:
			self._broken.append(process)
			self.logger.processes("Could not start process %s" % process)
			self.logger.processes("reason: %s" % str(e))

	def start (self,restart=False):
		for process in self.reactor.configuration.process:
			if restart:
				self._terminate(process)
			self._start(process)
		for process in list(self._process):
			if not process in self.reactor.configuration.process:
				self._terminate(process)

	def broken (self,neighbor):
		if self._broken:
			if '*' in self._broken:
				return True
			for process in self._neighbor_process.get(neighbor,[]):
				if process in self._broken:
					return True
		return False

	def fds (self):
		return [self._process[process].stdout for process in self._process]

	def received (self):
		for process in list(self._process):
			try:
				proc = self._process[process]
				r,_,_ = select.select([proc.stdout,],[],[],0)
				if r:
					try:
						for line in proc.stdout:
							line = line.rstrip()
							if line:
								self.logger.processes("Command from process %s : %s " % (process,line))
								yield (process,formated(line))
							else:
								self.logger.processes("The process died, trying to respawn it")
								self._terminate(process)
								self._start(process)
								break
					except IOError,e:
						if e.errno == errno.EINTR:  # call interrupted
							pass  # we most likely have data, we will try to read them a the next loop iteration
						elif e.errno != errno.EAGAIN:  # no more data
							self.logger.processes("unexpected errno received from forked process (%s)" % errstr(e))
			except (subprocess.CalledProcessError,OSError,ValueError):
				self.logger.processes("Issue with the process, terminating it and restarting it")
				self._terminate(process)
				self._start(process)

	def write (self,process,string):
		while True:
			try:
				self._process[process].stdin.write('%s\n' % string)
			except IOError,e:
				self._broken.append(process)
				if e.errno == errno.EPIPE:
					self._broken.append(process)
					self.logger.processes("Issue while sending data to our helper program")
					raise ProcessError()
				else:
					# Could it have been caused by a signal ? What to do.
					self.logger.processes("Error received while SENDING data to helper program, retrying (%s)" % errstr(e))
					continue
			break

		try:
			self._process[process].stdin.flush()
		except IOError,e:
			# AFAIK, the buffer should be flushed at the next attempt.
			self.logger.processes("Error received while FLUSHING data to helper program, retrying (%s)" % errstr(e))

		return True

	def _notify (self,neighbor,event):
		for process in self._neighbor_process.get(neighbor,[]):
			if process in self._process:
				yield process
		for process in self._neighbor_process.get('*',[]):
			if process in self._process:
				yield process

	def up (self,neighbor):
		if self.silence: return
		for process in self._notify(neighbor,'neighbor-changes'):
			self.write(process,self._api_encoder[process].up(neighbor))

	def connected (self,neighbor):
		if self.silence: return
		for process in self._notify(neighbor,'neighbor-changes'):
			self.write(process,self._api_encoder[process].connected(neighbor))

	def down (self,neighbor,reason=''):
		if self.silence: return
		for process in self._notify(neighbor,'neighbor-changes'):
			self.write(process,self._api_encoder[process].down(neighbor))

	def receive (self,neighbor,category,header,body):
		if self.silence: return
		for process in self._notify(neighbor,'receive-packets'):
			self.write(process,self._api_encoder[process].receive(neighbor,category,header,body))

	def send (self,neighbor,category,header,body):
		if self.silence: return
		for process in self._notify(neighbor,'send-packets'):
			self.write(process,self._api_encoder[process].send(neighbor,category,header,body))

	def update (self,neighbor,update):
		if self.silence: return
		for process in self._notify(neighbor,'receive-routes'):
			self.write(process,self._api_encoder[process].update(neighbor,update))

	def refresh (self,neighbor,refresh):
		if self.silence: return
		for process in self._notify(neighbor,'receive-routes'):
			self.write(process,self._api_encoder[process].refresh(neighbor,refresh))

	def operational (self,neighbor,what,operational):
		if self.silence: return
		for process in self._notify(neighbor,'receive-operational'):
			self.write(process,self._api_encoder[process].operational(neighbor,what,operational))

########NEW FILE########
__FILENAME__ = daemon
# encoding: utf-8
"""
daemon.py

Created by Thomas Mangin on 2011-05-02.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import os
import sys
import pwd
import errno
import socket

from exabgp.configuration.environment import environment

from exabgp.logger import Logger

MAXFD = 2048

class Daemon (object):

	def __init__ (self,reactor):
		self.pid = environment.settings().daemon.pid
		self.user = environment.settings().daemon.user
		self.daemonize = environment.settings().daemon.daemonize

		self.logger = Logger()

		self.reactor = reactor

		os.chdir('/')
		#os.umask(0)
		os.umask(0137)

	def savepid (self):
		self._saved_pid = False

		if not self.pid:
			return True

		ownid = os.getpid()

		flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
		mode = ((os.R_OK | os.W_OK) << 6) | (os.R_OK << 3) | os.R_OK

		try:
			fd = os.open(self.pid,flags,mode)
		except OSError:
			self.logger.daemon("PIDfile already exists, not updated %s" % self.pid)
			return False

		try:
			f = os.fdopen(fd,'w')
			line = "%d\n" % ownid
			f.write(line)
			f.close()
			self._saved_pid = True
		except IOError:
			self.logger.daemon("Can not create PIDfile %s" % self.pid,'warning')
			return False
		self.logger.daemon("Created PIDfile %s with value %d" % (self.pid,ownid),'warning')
		return True

	def removepid (self):
		if not self.pid or not self._saved_pid:
			return
		try:
			os.remove(self.pid)
		except OSError, e:
			if e.errno == errno.ENOENT:
				pass
			else:
				self.logger.daemon("Can not remove PIDfile %s" % self.pid,'error')
				return
		self.logger.daemon("Removed PIDfile %s" % self.pid)

	def drop_privileges (self):
		"""returns true if we are left with insecure privileges"""
		# os.name can be ['posix', 'nt', 'os2', 'ce', 'java', 'riscos']
		if os.name not in ['posix',]:
			return True

		uid = os.getuid()
		gid = os.getgid()

		if uid and gid:
			return True

		try:
			user = pwd.getpwnam(self.user)
			nuid = int(user.pw_uid)
			ngid = int(user.pw_gid)
		except KeyError:
			return False

		# not sure you can change your gid if you do not have a pid of zero
		try:
			# we must change the GID first otherwise it may fail after change UID
			if not gid:
				os.setgid(ngid)
			if not uid:
				os.setuid(nuid)

			cuid = os.getuid()
			ceid = os.geteuid()
			cgid = os.getgid()

			if cuid < 0:
				cuid = (1<<32) + cuid

			if cgid < 0:
				cgid = (1<<32) + cgid

			if ceid < 0:
				ceid = (1<<32) + ceid

			if nuid != cuid or nuid != ceid or ngid != cgid:
				return False

		except OSError:
			return False

		return True

	def _is_socket (self,fd):
		try:
			s = socket.fromfd(fd, socket.AF_INET, socket.SOCK_RAW)
		except ValueError,e:
			# The file descriptor is closed
			return False
		try:
			s.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
		except socket.error, e:
			# It is look like one but it is not a socket ...
			if e.args[0] == errno.ENOTSOCK:
				return False
		return True

	def daemonise (self):
		if not self.daemonize:
			return

		log = environment.settings().log
		if log.enable and log.destination.lower() in ('stdout','stderr'):
			self.logger.daemon('ExaBGP can not fork when logs are going to %s' % log.destination.lower(),'critical')
			return

		def fork_exit ():
			try:
				pid = os.fork()
				if pid > 0:
					os._exit(0)
			except OSError, e:
				self.logger.reactor('Can not fork, errno %d : %s' % (e.errno,e.strerror),'critical')

		# do not detach if we are already supervised or run by init like process
		if self._is_socket(sys.__stdin__.fileno()) or os.getppid() == 1:
			return

		fork_exit()
		os.setsid()
		fork_exit()
		self.silence()

	def silence (self):
		# closing more would close the log file too if open
		maxfd = 3

		for fd in range(0, maxfd):
			try:
				os.close(fd)
			except OSError:
				pass
		os.open("/dev/null", os.O_RDWR)
		os.dup2(0, 1)
		os.dup2(0, 2)

#		import resource
#		if 'linux' in sys.platform:
#			nofile = resource.RLIMIT_NOFILE
#		elif 'bsd' in sys.platform:
#			nofile = resource.RLIMIT_OFILE
#		else:
#			self.logger.daemon("For platform %s, can not close FDS before forking" % sys.platform)
#			nofile = None
#		if nofile:
#			maxfd = resource.getrlimit(nofile)[1]
#			if (maxfd == resource.RLIM_INFINITY):
#				maxfd = MAXFD
#		else:
#			maxfd = MAXFD

########NEW FILE########
__FILENAME__ = listener
# encoding: utf-8
"""
listen.py

Created by Thomas Mangin on 2013-07-11.
Copyright (c) 2013-2013 Exa Networks. All rights reserved.
"""

import socket

from exabgp.util.errstr import errstr

from exabgp.protocol.family import AFI
#from exabgp.util.coroutine import each
from exabgp.util.ip import isipv4,isipv6
from exabgp.reactor.network.error import error,errno,NetworkError,BindingError,AcceptError
from exabgp.reactor.network.incoming import Incoming
#from exabgp.bgp.message.open import Open
#from exabgp.bgp.message.notification import Notify

from exabgp.logger import Logger


class Listener (object):
	def __init__ (self,hosts,port,backlog=200):
		self._hosts = hosts
		self._port = port
		self._backlog = backlog

		self.serving = False
		self._sockets = {}
		#self._connected = {}
		self.logger = Logger()

	def _bind (self,ip,port):
		try:
			if isipv6(ip):
				s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
				try:
					s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				except (socket.error,AttributeError):
					pass
				s.bind((ip,port,0,0))
			elif isipv4(ip):
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
				try:
					s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				except (socket.error,AttributeError):
					pass
				s.bind((ip,port))
			else:
				return None
			s.setblocking(0)
			##s.settimeout(0.0)
			s.listen(self._backlog)
			return s
		except socket.error, e:
			if e.args[0] == errno.EADDRINUSE:
				raise BindingError('could not listen on %s:%d, the port already in use by another application' % (ip,self._port))
			elif e.args[0] == errno.EADDRNOTAVAIL:
				raise BindingError('could not listen on %s:%d, this is an invalid address' % (ip,self._port))
			else:
				raise BindingError('could not listen on %s:%d (%s)' % (ip,self._port,errstr(e)))

	def start (self):
		try:
			for host in self._hosts:
				if (host,self._port) not in self._sockets:
					s = self._bind(host,self._port)
					self._sockets[s] = (host,self._port)
			self.serving = True
		except NetworkError,e:
				self.logger.network(str(e),'critical')
				raise e
		self.serving = True

	# @each
	def connected (self):
		if not self.serving:
			return

		try:
			for sock,(host,_) in self._sockets.items():
				try:
					io, _ = sock.accept()
					local_ip,local_port = io.getpeername()
					remote_ip,remote_port = io.getsockname()
					yield Incoming(AFI.ipv4,remote_ip,local_ip,io)
					break
				except socket.error, e:
					if e.errno in error.block:
						continue
					raise AcceptError('could not accept a new connection (%s)' % errstr(e))
		except NetworkError,e:
			self.logger.network(str(e),'critical')
			raise e

	def stop (self):
		if not self.serving:
			return

		for sock,(ip,port) in self._sockets.items():
			sock.close()
			self.logger.network('stopped listening on %s:%d' % (ip,port),'info')

		self._sockets = {}
		self.serving = False

########NEW FILE########
__FILENAME__ = connection
# encoding: utf-8
"""
network.py

Created by Thomas Mangin on 2009-09-06.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import time
import random
import socket
import select
from struct import unpack

from exabgp.configuration.environment import environment

from exabgp.util.od import od
from exabgp.util.errstr import errstr

from exabgp.logger import Logger,FakeLogger,LazyFormat

from exabgp.bgp.message import Message

from exabgp.reactor.network.error import error,errno,NetworkError,TooSlowError,NotConnected,LostConnection,NotifyError

from .error import *

class Connection (object):
	direction = 'undefined'
	identifier = 0

	def __init__ (self,afi,peer,local):
		# peer and local are strings of the IP

		# If the OS tells us we have data on the socket, we should never have to wait more than read_timeout to be able to read it.
		# However real life says that on some OS we do ... So let the user control this value
		try:
			self.read_timeout = environment.settings().tcp.timeout
			self.defensive = environment.settings().debug.defensive
			self.logger = Logger()
		except RuntimeError:
			self.read_timeout = 1
			self.defensive = True
			self.logger = FakeLogger()

		self.afi = afi
		self.peer = peer
		self.local = local

		self._reading = None
		self._writing = None
		self._buffer = ''
		self.io = None
		self.established = False

		self.identifier += 1
		self.id = self.identifier

	# Just in case ..
	def __del__ (self):
		if self.io:
			self.logger.network("%s connection to %s closed" % (self.name(),self.peer),'info')
			self.close()

	def name (self):
		return "session %d %s" % (self.id,self.direction)

	def close (self):
		try:
			self.logger.wire("%s, closing connection from %s to %s" % (self.name(),self.local,self.peer))
			if self.io:
				self.io.close()
				self.io = None
		except KeyboardInterrupt,e:
			raise e
		except:
			pass

	def reading (self):
		while True:
			try:
				r,_,_ = select.select([self.io,],[],[],0)
			except select.error,e:
				if e.args[0] not in error.block:
					self.close()
					self.logger.wire("%s %s errno %s on socket" % (self.name(),self.peer,errno.errorcode[e.args[0]]))
					raise NetworkError('errno %s on socket' % errno.errorcode[e.args[0]])
				return False

			if r:
				self._reading = time.time()
			return r != []

	def writing (self):
		while True:
			try:
				_,w,_ = select.select([],[self.io,],[],0)
			except select.error,e:
				if e.args[0] not in error.block:
					self.close()
					self.logger.wire("%s %s errno %s on socket" % (self.name(),self.peer,errno.errorcode[e.args[0]]))
					raise NetworkError('errno %s on socket' % errno.errorcode[e.args[0]])
				return False

			if w:
				self._writing = time.time()
			return w != []

	def _reader (self,number):
		# The function must not be called if it does not return with no data with a smaller size as parameter
		if not self.io:
			self.close()
			raise NotConnected('Trying to read on a close TCP conncetion')
		if number == 0:
			yield ''
			return
		# XXX: one of the socket option is to recover the size of the buffer
		# XXX: we could use it to not have to put together the string with multiple reads
		# XXX: and get rid of the self.read_timeout option
		while not self.reading():
			yield ''
		data = ''
		while True:
			try:
				while True:
					if self._reading is None:
						self._reading = time.time()
					elif time.time() > self._reading + self.read_timeout:
						self.close()
						self.logger.wire("%s %s peer is too slow (we were told there was data on the socket but we can not read up to what should be there)" % (self.name(),self.peer))
						raise TooSlowError('Waited to read for data on a socket for more than %d second(s)' % self.read_timeout)

					if self.defensive and random.randint(0,2):
						raise socket.error(errno.EAGAIN,'raising network error in purpose')

					read = self.io.recv(number)
					if not read:
						self.close()
						self.logger.wire("%s %s lost TCP session with peer" % (self.name(),self.peer))
						raise LostConnection('the TCP connection was closed by the remote end')

					data += read
					number -= len(read)
					if not number:
						self.logger.wire(LazyFormat("%s %-32s RECEIVED " % (self.name(),'%s / %s' % (self.local,self.peer)),od,read))
						self._reading = None
						yield data
						return
			except socket.timeout,e:
				self.close()
				self.logger.wire("%s %s peer is too slow" % (self.name(),self.peer))
				raise TooSlowError('Timeout while reading data from the network (%s)' % errstr(e))
			except socket.error,e:
				if e.args[0] in error.block:
					self.logger.wire("%s %s blocking io problem mid-way through reading a message %s, trying to complete" % (self.name(),self.peer,errstr(e)),'debug')
				elif e.args[0] in error.fatal:
					self.close()
					raise LostConnection('issue reading on the socket: %s' % errstr(e))
				# what error could it be !
				else:
					self.logger.wire("%s %s undefined error reading on socket" % (self.name(),self.peer))
					raise NetworkError('Problem while reading data from the network (%s)' % errstr(e))

	def writer (self,data):
		if not self.io:
			# XXX: FIXME: Make sure it does not hold the cleanup during the closing of the peering session
			yield True
			return
		while not self.writing():
			yield False
		self.logger.wire(LazyFormat("%s %-32s SENDING " % (self.name(),'%s / %s' % (self.local,self.peer)),od,data))
		# The first while is here to setup the try/catch block once as it is very expensive
		while True:
			try:
				while True:
					if self._writing is None:
						self._writing = time.time()
					elif time.time() > self._writing + self.read_timeout:
						self.close()
						self.logger.wire("%s %s peer is too slow" % (self.name(),self.peer))
						raise TooSlowError('Waited to write for data on a socket for more than %d second(s)' % self.read_timeout)

					if self.defensive and random.randint(0,2):
						raise socket.error(errno.EAGAIN,'raising network error in purpose')

					# we can not use sendall as in case of network buffer filling
					# it does raise and does not let you know how much was sent
					nb = self.io.send(data)
					if not nb:
						self.close()
						self.logger.wire("%s %s lost TCP connection with peer" % (self.name(),self.peer))
						raise LostConnection('lost the TCP connection')

					data = data[nb:]
					if not data:
						self._writing = None
						yield True
						return
					yield False
			except socket.error,e:
				if e.args[0] in error.block:
					self.logger.wire("%s %s blocking io problem mid-way through writing a message %s, trying to complete" % (self.name(),self.peer,errstr(e)),'debug')
					yield False
				elif e.errno == errno.EPIPE:
					# The TCP connection is gone.
					self.close()
					raise NetworkError('Broken TCP connection')
				elif e.args[0] in error.fatal:
					self.close()
					self.logger.wire("%s %s problem sending message (%s)" % (self.name(),self.peer,errstr(e)))
					raise NetworkError('Problem while writing data to the network (%s)' % errstr(e))
				# what error could it be !
				else:
					self.logger.wire("%s %s undefined error writing on socket" % (self.name(),self.peer))
					yield False

	def reader (self):
		# _reader returns the whole number requested or nothing and then stops
		for header in self._reader(Message.HEADER_LEN):
			if not header:
				yield 0,0,'','',None

		if not header.startswith(Message.MARKER):
			yield 0,0,header,'',NotifyError(1,1,'The packet received does not contain a BGP marker')
			return

		msg = ord(header[18])
		length = unpack('!H',header[16:18])[0]

		if length < Message.HEADER_LEN or length > Message.MAX_LEN:
			yield length,0,header,'',NotifyError(1,2,'%s has an invalid message length of %d' %(Message().name(msg),length))
			return

		validator = Message.Length.get(msg,lambda _ : _ >= 19)
		if not validator(length):
			# MUST send the faulty msg_length back
			yield length,0,header,'',NotifyError(1,2,'%s has an invalid message length of %d' %(Message().name(msg),msg_length))
			return

		number = length - Message.HEADER_LEN

		if not number:
			yield length,msg,header,'',None
			return

		for body in self._reader(number):
			if not body:
				yield 0,0,'','',None

		yield length,msg,header,body,None

########NEW FILE########
__FILENAME__ = error
# encoding: utf-8
"""
error.py

Created by Thomas Mangin on 2013-07-11.
Copyright (c) 2013-2013 Exa Networks. All rights reserved.
"""

import errno

class error:
	block = set((
		errno.EINPROGRESS, errno.EALREADY,
		errno.EAGAIN, errno.EWOULDBLOCK,
		errno.EINTR, errno.EDEADLK,
		errno.EBUSY, errno.ENOBUFS,
		errno.ENOMEM,
	))

	fatal = set((
		errno.ECONNABORTED, errno.EPIPE,
		errno.ECONNREFUSED, errno.EBADF,
		errno.ESHUTDOWN, errno.ENOTCONN,
		errno.ECONNRESET, errno.ETIMEDOUT,
		errno.EINVAL,
	))

	unavailable = set((
		errno.ECONNREFUSED, errno.EHOSTUNREACH,
	))

class NetworkError   (Exception): pass
class BindingError   (NetworkError): pass
class AcceptError    (NetworkError): pass
class NotConnected   (NetworkError): pass
class LostConnection (NetworkError): pass
class MD5Error       (NetworkError): pass
class NagleError     (NetworkError): pass
class TTLError       (NetworkError): pass
class AsyncError     (NetworkError): pass
class TooSlowError   (NetworkError): pass
class SizeError      (NetworkError): pass  # not used atm - can not generate message due to size

class NotifyError    (Exception):
	def __init__ (self,code,subcode,msg):
		self.code = code
		self.subcode = subcode
		Exception.__init__(self,msg)

########NEW FILE########
__FILENAME__ = incoming
from exabgp.util.errstr import errstr

from .connection import Connection
from .tcp import nagle,async
from .error import NetworkError,NotConnected

from exabgp.bgp.message.notification import Notify

class Incoming (Connection):
	direction = 'incoming'

	def __init__ (self,afi,peer,local,io):
		Connection.__init__(self,afi,peer,local)

		self.logger.wire("Connection from %s" % self.peer)

		try:
			self.io = io
			async(self.io,peer)
			nagle(self.io,peer)
		except NetworkError,e:
			self.close()
			raise NotConnected(errstr(e))

	def notification (self,code,subcode,message):
		try:
			notification = Notify(code,subcode,message).message()
			for boolean in self.writer(notification):
				yield False
			self.logger.message(self.me('>> NOTIFICATION (%d,%d,"%s")' % (notification.code,notification.subcode,notification.data)),'error')
			yield True
		except NetworkError:
			pass  # This is only be used when closing session due to unconfigured peers - so issues do not matter

########NEW FILE########
__FILENAME__ = outgoing
from .connection import Connection
from .tcp import create,bind,connect,MD5,nagle,TTL,async,ready
from .error import NetworkError

class Outgoing (Connection):
	direction = 'outgoing'

	def __init__ (self,afi,peer,local,port=179,md5='',ttl=None):
		Connection.__init__(self,afi,peer,local)

		self.logger.wire("Attempting connection to %s" % self.peer)

		self.peer = peer
		self.ttl = ttl
		self.afi = afi
		self.md5 = md5
		self.port = port

		try:
			self.io = create(afi)
			MD5(self.io,peer,port,afi,md5)
			bind(self.io,local,afi)
			async(self.io,peer)
			connect(self.io,peer,port,afi,md5)
			self.init = True
		except NetworkError:
			self.init = False
			self.close()

	def establish (self):
		if not self.init:
			yield False
			return

		try:
			generator = ready(self.io)
			while True:
				connected = generator.next()
				if not connected:
					yield False
					continue
				yield True
				return
		except StopIteration:
			# self.io MUST NOT be closed here, it is closed by the caller
			yield False
			return

		nagle(self.io,self.peer)
		TTL(self.io,self.peer,self.ttl)
		yield True

########NEW FILE########
__FILENAME__ = tcp
# encoding: utf-8
"""
setup.py

Created by Thomas Mangin on 2013-07-13.
Copyright (c) 2013-2013 Exa Networks. All rights reserved.
"""

import time
import struct
import socket
import select
import platform

from exabgp.util.errstr import errstr

from exabgp.protocol.family import AFI
from exabgp.reactor.network.error import errno,error

from .error import NotConnected,BindingError,MD5Error,NagleError,TTLError,AsyncError

from exabgp.logger import Logger

def create (afi):
	try:
		if afi == AFI.ipv4:
			io = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		if afi == AFI.ipv6:
			io = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		try:
			io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		except (socket.error,AttributeError):
			pass
		try:
			io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
		except (socket.error,AttributeError):
			pass
	except socket.error:
		raise NotConnected('Could not create socket')
	return io

def bind (io,ip,afi):
	try:
		if afi == AFI.ipv4:
			io.bind((ip,0))
		if afi == AFI.ipv6:
			io.bind((ip,0,0,0))
	except socket.error,e:
		raise BindingError('Could not bind to local ip %s - %s' % (ip,str(e)))

def connect (io,ip,port,afi,md5):
	try:
		if afi == AFI.ipv4:
			io.connect((ip,port))
		if afi == AFI.ipv6:
			io.connect((ip,port,0,0))
	except socket.error, e:
		if e.errno == errno.EINPROGRESS:
			return
		if md5:
			raise NotConnected('Could not connect to peer %s:%d, check your MD5 password (%s)' % (ip,port,errstr(e)))
		raise NotConnected('Could not connect to peer %s:%d (%s)' % (ip,port,errstr(e)))


def MD5 (io,ip,port,afi,md5):
	if md5:
		os = platform.system()
		if os == 'FreeBSD':
			if md5 != 'kernel':
				raise MD5Error(
					'FreeBSD requires that you set your MD5 key via ipsec.conf.\n'
					'Something like:\n'
					'flush;\n'
					'add <local ip> <peer ip> tcp 0x1000 -A tcp-md5 "password";'
					)
			try:
				TCP_MD5SIG = 0x10
				io.setsockopt(socket.IPPROTO_TCP, TCP_MD5SIG, 1)
			except socket.error,e:
				raise MD5Error(
					'FreeBSD requires that you rebuild your kernel to enable TCP MD5 Signatures:\n'
					'options         IPSEC\n'
					'options         TCP_SIGNATURE\n'
					'device          crypto\n'
				)
		elif os == 'Linux':
			try:
				TCP_MD5SIG = 14
				TCP_MD5SIG_MAXKEYLEN = 80

				n_port = socket.htons(port)
				if afi == AFI.ipv4:
					SS_PADSIZE = 120
					n_addr = socket.inet_pton(socket.AF_INET, ip)
					tcp_md5sig = 'HH4s%dx2xH4x%ds' % (SS_PADSIZE, TCP_MD5SIG_MAXKEYLEN)
					md5sig = struct.pack(tcp_md5sig, socket.AF_INET, n_port, n_addr, len(md5), md5)
				if afi == AFI.ipv6:
					SS_PADSIZE = 100
					SIN6_FLOWINFO = 0
					SIN6_SCOPE_ID = 0
					n_addr = socket.inet_pton(socket.AF_INET6, ip)
					tcp_md5sig = 'HHI16sI%dx2xH4x%ds' % (SS_PADSIZE, TCP_MD5SIG_MAXKEYLEN)
					md5sig = struct.pack(tcp_md5sig, socket.AF_INET6, n_port, SIN6_FLOWINFO, n_addr, SIN6_SCOPE_ID, len(md5), md5)
				io.setsockopt(socket.IPPROTO_TCP, TCP_MD5SIG, md5sig)
			except socket.error,e:
				raise MD5Error('This linux machine does not support TCP_MD5SIG, you can not use MD5 (%s)' % errstr(e))
		else:
			raise MD5Error('ExaBGP has no MD5 support for %s' % os)

def nagle (io,ip):
	try:
		# diable Nagle's algorithm (no grouping of packets)
		io.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
	except (socket.error,AttributeError):
		raise NagleError("Could not disable nagle's algorithm for %s" % ip)

def TTL (io,ip,ttl):
	# None (ttl-security unset) or zero (maximum TTL) is the same thing
	if ttl:
		try:
			io.setsockopt(socket.IPPROTO_IP,socket.IP_TTL, 20)
		except socket.error,e:
			raise TTLError('This OS does not support IP_TTL (ttl-security) for %s (%s)' % (ip,errstr(e)))

def async (io,ip):
	try:
		io.setblocking(0)
	except socket.error, e:
		raise AsyncError('could not set socket non-blocking for %s (%s)' % (ip,errstr(e)))

def ready (io):
	logger = Logger()
	warned = False
	start = time.time()

	while True:
		try:
			_,w,_ = select.select([],[io,],[],0)
			if not w:
				if not warned and time.time()-start > 1.0:
					logger.network('attempting to accept connections, socket not ready','warning')
					warned = True
				yield False
				continue
			err = io.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
			if not err:
				if warned:
					logger.network('incoming socket ready','warning')
				yield True
				return
			elif err in error.block:
				logger.network('connect attempt failed, retrying, reason %s' % errno.errorcode[err],'warning')
				yield False
			else:
				yield False
				return
		except select.error:
			yield False
			return

# try:
# 	try:
# 		# Linux / Windows
# 		self.message_size = io.getsockopt(socket.SOL_SOCKET, socket.SO_MAX_MSG_SIZE)
# 	except AttributeError:
# 		# BSD
# 		self.message_size = io.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
# except socket.error, e:
# 	self.message_size = None

########NEW FILE########
__FILENAME__ = peer
# encoding: utf-8
"""
peer.py

Created by Thomas Mangin on 2009-08-25.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import time
#import traceback

from exabgp.bgp.timer import Timer
from exabgp.bgp.message import Message
from exabgp.bgp.message.open.capability.id import CapabilityID,REFRESH
from exabgp.bgp.message.nop import NOP
from exabgp.bgp.message.keepalive import KeepAlive
from exabgp.bgp.message.update import Update
from exabgp.bgp.message.refresh import RouteRefresh
from exabgp.bgp.message.notification import Notification, Notify
from exabgp.reactor.protocol import Protocol
from exabgp.reactor.network.error import NetworkError
from exabgp.reactor.api.processes import ProcessError

from exabgp.rib.change import Change

from exabgp.configuration.environment import environment
from exabgp.logger import Logger,FakeLogger,LazyFormat

from exabgp.util.counter import Counter
from exabgp.util.trace import trace

from exabgp.util.enumeration import Enumeration

STATE = Enumeration (
	'idle',
	'active',
	'connect',
	'opensent',
	'openconfirm',
	'established',
)

ACTION = Enumeration (
	'close',
	'later',
	'immediate',
	)

SEND = Enumeration (
	'done',
	'normal',
	'refresh',
)

# As we can not know if this is our first start or not, this flag is used to
# always make the program act like it was recovering from a failure
# If set to FALSE, no EOR and OPEN Flags set for Restart will be set in the
# OPEN Graceful Restart Capability
FORCE_GRACEFUL = True

class Interrupted (Exception): pass

# Present a File like interface to socket.socket

class Peer (object):
	def __init__ (self,neighbor,reactor):
		try:
			self.logger = Logger()
			# We only to try to connect via TCP once
			self.once = environment.settings().tcp.once
			self.bind = True if environment.settings().tcp.bind else False
		except RuntimeError:
			self.logger = FakeLogger()
			self.once = True

		self.reactor = reactor
		self.neighbor = neighbor
		# The next restart neighbor definition
		self._neighbor = None

		# The peer should restart after a stop
		self._restart = True
		# The peer was restarted (to know what kind of open to send for graceful restart)
		self._restarted = FORCE_GRACEFUL
		self._reset_skip()

		# We want to send all the known routes
		self._resend_routes = SEND.done
		# We have new routes for the peers
		self._have_routes = True

		# We have been asked to teardown the session with this code
		self._teardown = None

		self._ = {'in':{},'out':{}}

		self._['in']['state'] = STATE.idle
		self._['out']['state'] = STATE.idle

		# value to reset 'generator' to
		self._['in']['enabled'] = False
		self._['out']['enabled'] = None if not self.neighbor.passive else False

		# the networking code
		self._['out']['proto'] = None
		self._['in']['proto'] = None

		# the networking code
		self._['out']['code'] = self._connect
		self._['in']['code'] = self._accept

		# the generator used by the main code
		# * False, the generator for this direction is down
		# * Generator, the code to run to connect or accept the connection
		# * None, the generator must be re-created
		self._['in']['generator'] = self._['in']['enabled']
		self._['out']['generator'] = self._['out']['enabled']

		self._generator_keepalive = None

	def _reset (self,direction,message='',error=''):
		self._[direction]['state'] = STATE.idle

		if self._restart:
			if self._[direction]['proto']:
				self._[direction]['proto'].close('%s loop reset %s %s' % (direction,message,str(error)))
			self._[direction]['proto'] = None
			self._[direction]['generator'] = self._[direction]['enabled']
			self._teardown = None
			self._more_skip(direction)
			self.neighbor.rib.reset()

			# If we are restarting, and the neighbor definition is different, update the neighbor
			if self._neighbor:
				self.neighbor = self._neighbor
				self._neighbor = None
		else:
			self._[direction]['generator'] = False
			self._[direction]['proto'] = None

	def _stop (self,direction,message):
		self._[direction]['generator'] = False
		self._[direction]['proto'].close('%s loop stop %s' % (direction,message))
		self._[direction]['proto'] = None

	# connection delay

	def _reset_skip (self):
		# We are currently not skipping connection attempts
		self._skip_time = time.time()
		# when we can not connect to a peer how many time (in loop) should we back-off
		self._next_skip = 0

	def _more_skip (self,direction):
		if direction != 'out':
			return
		self._skip_time = time.time() + self._next_skip
		self._next_skip = int(1+ self._next_skip*1.2)
		if self._next_skip > 60:
			self._next_skip = 60

	# logging

	def me (self,message):
		return "peer %s ASN %-7s %s" % (self.neighbor.peer_address,self.neighbor.peer_as,message)

	def _output (self,direction,message):
		return "%s %s" % (self._[direction]['proto'].connection.name(),self.me(message))

	def _log (self,direction):
		def inner (message):
			return self._output(direction,message)
		return inner

	# control

	def stop (self):
		self._teardown = 3
		self._restart = False
		self._restarted = False
		self._reset_skip()

	def resend (self):
		self._resend_routes = SEND.normal
		self._reset_skip()

	def send_new (self,changes=None,update=None):
		if changes:
			self.neighbor.rib.outgoing.update(changes)
		self._have_routes = self.neighbor.flush if update is None else update

	def restart (self,restart_neighbor=None):
		# we want to tear down the session and re-establish it
		self._teardown = 3
		self._restart = True
		self._restarted = True
		self._resend_routes = SEND.normal
		self._neighbor = restart_neighbor
		self._reset_skip()

	def teardown (self,code,restart=True):
		self._restart = restart
		self._teardown = code
		self._reset_skip()

	# sockets we must monitor

	def sockets (self):
		ios = []
		for direction in ['in','out']:
			proto = self._[direction]['proto']
			if proto and proto.connection and proto.connection.io:
				ios.append(proto.connection.io)
		return ios

	def incoming (self,connection):
		# if the other side fails, we go back to idle
		if self._['in']['proto'] not in (True,False,None):
			self.logger.network('we already have a peer at this address')
			return False

		self._['in']['proto'] = Protocol(self).accept(connection)
		# Let's make sure we do some work with this connection
		self._['in']['generator'] = None
		self._['in']['state'] = STATE.connect
		return True

	def established (self):
		return self._['in']['state'] == STATE.established or self._['out']['state'] == STATE.established

	def _accept (self):
		# we can do this as Protocol is a mutable object
		proto = self._['in']['proto']

		# send OPEN
		for message in proto.new_open(self._restarted):
			if ord(message.TYPE) == Message.Type.NOP:
				yield ACTION.immediate

		proto.negotiated.sent(message)

		self._['in']['state'] = STATE.opensent

		# Read OPEN
		wait = environment.settings().bgp.openwait
		opentimer = Timer(self._log('in'),wait,1,1,'waited for open too long, we do not like stuck in active')
		# Only yield if we have not the open, otherwise the reactor can run the other connection
		# which would be bad as we need to do the collission check without going to the other peer
		for message in proto.read_open(self.neighbor.peer_address.ip):
			opentimer.tick(message)
			if ord(message.TYPE) == Message.Type.NOP:
				yield ACTION.later

		self._['in']['state'] = STATE.openconfirm
		proto.negotiated.received(message)
		proto.validate_open()

		if self._['out']['state'] == STATE.openconfirm:
			self.logger.network('incoming connection finds the outgoing connection is in openconfirm')
			local_id = self.neighbor.router_id.packed
			remote_id = proto.negotiated.received_open.router_id.packed

			if local_id < remote_id:
				self.logger.network('closing the outgoing connection')
				self._stop('out','collision local id < remote id')
				yield ACTION.later
			else:
				self.logger.network('aborting the incoming connection')
				stop = Interrupted()
				stop.direction = 'in'
				raise stop

		# Send KEEPALIVE
		for message in self._['in']['proto'].new_keepalive('OPENCONFIRM'):
			yield ACTION.immediate

		# Start keeping keepalive timer
		self.timer = Timer(self._log('in'),proto.negotiated.holdtime,4,0)
		# Read KEEPALIVE
		for message in proto.read_keepalive('ESTABLISHED'):
			self.timer.tick(message)
			yield ACTION.later

		self._['in']['state'] = STATE.established
		# let the caller know that we were sucesfull
		yield ACTION.immediate

	def _connect (self):
		# try to establish the outgoing connection

		proto = Protocol(self)
		generator = proto.connect()

		connected = False
		try:
			while not connected:
				connected = generator.next()
				# we want to come back as soon as possible
				yield ACTION.immediate
		except StopIteration:
			# Connection failed
			if not connected:
				proto.close('connection to peer failed')
			# A connection arrived before we could establish !
			if not connected or self._['in']['proto']:
				stop = Interrupted()
				stop.direction = 'out'
				raise stop

		self._['out']['state'] = STATE.connect
		self._['out']['proto'] = proto

		# send OPEN
		# Only yield if we have not the open, otherwise the reactor can run the other connection
		# which would be bad as we need to set the state without going to the other peer
		for message in proto.new_open(self._restarted):
			if ord(message.TYPE) == Message.Type.NOP:
				yield ACTION.immediate

		proto.negotiated.sent(message)

		self._['out']['state'] = STATE.opensent

		# Read OPEN
		wait = environment.settings().bgp.openwait
		opentimer = Timer(self._log('out'),wait,1,1,'waited for open too long, we do not like stuck in active')
		for message in self._['out']['proto'].read_open(self.neighbor.peer_address.ip):
			opentimer.tick(message)
			# XXX: FIXME: change the whole code to use the ord and not the chr version
			# Only yield if we have not the open, otherwise the reactor can run the other connection
			# which would be bad as we need to do the collission check
			if ord(message.TYPE) == Message.Type.NOP:
				yield ACTION.later

		self._['out']['state'] = STATE.openconfirm
		proto.negotiated.received(message)
		proto.validate_open()

		if self._['in']['state'] == STATE.openconfirm:
			self.logger.network('outgoing connection finds the incoming connection is in openconfirm')
			local_id = self.neighbor.router_id.packed
			remote_id = proto.negotiated.received_open.router_id.packed

			if local_id < remote_id:
				self.logger.network('aborting the outgoing connection')
				stop = Interrupted()
				stop.direction = 'out'
				raise stop
			else:
				self.logger.network('closing the incoming connection')
				self._stop('in','collision local id < remote id')
				yield ACTION.later

		# Send KEEPALIVE
		for message in proto.new_keepalive('OPENCONFIRM'):
			yield ACTION.immediate

		# Start keeping keepalive timer
		self.timer = Timer(self._log('out'),self._['out']['proto'].negotiated.holdtime,4,0)
		# Read KEEPALIVE
		for message in self._['out']['proto'].read_keepalive('ESTABLISHED'):
			self.timer.tick(message)
			yield ACTION.immediate

		self._['out']['state'] = STATE.established
		# let the caller know that we were sucesfull
		yield ACTION.immediate

	def _keepalive (self,direction):
		# yield :
		#  True  if we just sent the keepalive
		#  None  if we are working as we should
		#  False if something went wrong

		yield 'ready'

		need_keepalive = False
		generator = None
		last = NOP

		while not self._teardown:
			# SEND KEEPALIVES
			need_keepalive |= self.timer.keepalive()

			if need_keepalive and not generator:
				proto = self._[direction]['proto']
				if not proto:
					yield False
					break
				generator = proto.new_keepalive()
				need_keepalive = False

			if generator:
				try:
					last = generator.next()
					if last.TYPE == KeepAlive.TYPE:
						# close the generator and rasie a StopIteration
						generator.next()
					yield None
				except (NetworkError,ProcessError):
					yield False
					break
				except StopIteration:
					generator = None
					if last.TYPE != KeepAlive.TYPE:
						self._generator_keepalive = False
						yield False
						break
					yield True
			else:
				yield None

	def keepalive (self):
		generator = self._generator_keepalive
		if generator:
			# XXX: CRITICAL : this code needs the same exception than the one protecting the main loop
			try:
				return generator.next()
			except StopIteration:
				pass
		return self._generator_keepalive is None

	def _main (self,direction):
		"yield True if we want to come back to it asap, None if nothing urgent, and False if stopped"

		if self._teardown:
			raise Notify(6,3)

		proto = self._[direction]['proto']

		# Initialise the keepalive
		self._generator_keepalive = self._keepalive(direction)

		# Announce to the process BGP is up
		self.logger.network('Connected to peer %s (%s)' % (self.neighbor.name(),direction))
		if self.neighbor.api.neighbor_changes:
			try:
				self.reactor.processes.up(self.neighbor.peer_address)
			except ProcessError:
				# Can not find any better error code than 6,0 !
				# XXX: We can not restart the program so this will come back again and again - FIX
				# XXX: In the main loop we do exit on this kind of error
				raise Notify(6,0,'ExaBGP Internal error, sorry.')

		send_eor = True
		new_routes = None
		self._resend_routes = SEND.normal
		send_families = []

		# Every last asm message should be re-announced on restart
		for family in self.neighbor.asm:
			if family in self.neighbor.families():
				self.neighbor.messages.appendleft(self.neighbor.asm[family])

		counter = Counter(self.logger,self._log(direction))
		operational = None
		refresh = None

		while not self._teardown:
			for message in proto.read_message():
				# Update timer
				self.timer.tick(message)

				# Give information on the number of routes seen
				counter.display()

				# Received update
				if message.TYPE == Update.TYPE:
					counter.increment(len(message.nlris))

					for nlri in message.nlris:
						self.neighbor.rib.incoming.insert_received(Change(nlri,message.attributes))
						self.logger.routes(LazyFormat(self.me(''),str,nlri))
				elif message.TYPE == RouteRefresh.TYPE:
					if message.reserved == RouteRefresh.request:
						self._resend_routes = SEND.refresh
						send_families.append((message.afi,message.safi))

				# SEND OPERATIONAL
				if self.neighbor.operational:
					if not operational:
						new_operational = self.neighbor.messages.popleft() if self.neighbor.messages else None
						if new_operational:
							operational = proto.new_operational(new_operational,proto.negotiated)

					if operational:
						try:
							operational.next()
						except StopIteration:
							operational = None

				# SEND REFRESH
				if self.neighbor.route_refresh:
					if not refresh:
						new_refresh = self.neighbor.refresh.popleft() if self.neighbor.refresh else None
						if new_refresh:
							enhanced_negotiated = True if proto.negotiated.refresh == REFRESH.enhanced else False
							refresh = proto.new_refresh(new_refresh,enhanced_negotiated)

					if refresh:
						try:
							refresh.next()
						except StopIteration:
							refresh = None

				# Take the routes already sent to that peer and resend them
				if self._resend_routes != SEND.done:
					enhanced_refresh = True if self._resend_routes == SEND.refresh and proto.negotiated.refresh == REFRESH.enhanced else False
					self._resend_routes = SEND.done
					self.neighbor.rib.outgoing.resend(send_families,enhanced_refresh)
					self._have_routes = True
					send_families = []

				# Need to send update
				if self._have_routes and not new_routes:
					self._have_routes = False
					# XXX: in proto really. hum to think about ?
					new_routes = proto.new_update()

				if new_routes:
					try:
						count = 20
						while count:
							# This can raise a NetworkError
							new_routes.next()
							count -= 1
					except StopIteration:
						new_routes = None

				elif send_eor:
					send_eor = False
					for eor in proto.new_eors():
						yield ACTION.immediate
					self.logger.message(self.me('>> EOR(s)'))

				# Go to other Peers
				yield ACTION.immediate if new_routes or message.TYPE != NOP.TYPE or self.neighbor.messages else ACTION.later

				# read_message will loop until new message arrives with NOP
				if self._teardown:
					break

		# If graceful restart, silent shutdown
		if self.neighbor.graceful_restart and proto.negotiated.sent_open.capabilities.announced(CapabilityID.GRACEFUL_RESTART):
			self.logger.network('Closing the session without notification','error')
			proto.close('graceful restarted negotiated, closing without sending any notification')
			raise NetworkError('closing')

		# notify our peer of the shutdown
		raise Notify(6,self._teardown)

	def _run (self,direction):
		"yield True if we want the reactor to give us back the hand with the same peer loop, None if we do not have any more work to do"
		try:
			for action in self._[direction]['code']():
				yield action

			for action in self._main(direction):
				yield action

		# CONNECTION FAILURE
		except NetworkError, e:
			self._reset(direction,'closing connection',e)

			# we tried to connect once, it failed, we stop
			if self.once:
				self.logger.network('only one attempt to connect is allowed, stopping the peer')
				self.stop()
			return

		# NOTIFY THE PEER OF AN ERROR
		except Notify, n:
			for direction in ['in','out']:
				if self._[direction]['proto']:
					try:
						generator = self._[direction]['proto'].new_notification(n)
						try:
							maximum = 20
							while maximum:
								generator.next()
								maximum -= 1
								yield ACTION.immediate if maximum > 10 else ACTION.later
						except StopIteration:
							pass
					except (NetworkError,ProcessError):
						self.logger.network(self._output(direction,'NOTIFICATION NOT SENT'),'error')
						pass
					self._reset(direction,'notification sent (%d,%d)' % (n.code,n.subcode),n)
				else:
					self._reset(direction)
			return

		# THE PEER NOTIFIED US OF AN ERROR
		except Notification, n:
			self._reset(direction,'notification received (%d,%d)' % (n.code,n.subcode),n)
			return

		# RECEIVED a Message TYPE we did not expect
		except Message, m:
			self._reset(direction,'unexpected message received',m)
			return

		# PROBLEM WRITING TO OUR FORKED PROCESSES
		except ProcessError, e:
			self._reset(direction,'process problem',e)
			return

		# ....
		except Interrupted, i:
			self._reset(i.direction)
			return

		# UNHANDLED PROBLEMS
		except Exception, e:
			# Those messages can not be filtered in purpose
			self.logger.error(self.me('UNHANDLED PROBLEM, please report'),'reactor')
			self.logger.error(self.me(str(type(e))),'reactor')
			self.logger.error(self.me(str(e)),'reactor')
			self.logger.error(trace())

			self._reset(direction)
			return
	# loop

	def run (self):
		if self.reactor.processes.broken(self.neighbor.peer_address):
			# XXX: we should perhaps try to restart the process ??
			self.logger.processes('ExaBGP lost the helper process for this peer - stopping','error')
			self.stop()
			return True

		back = ACTION.later if self._restart else ACTION.close

		for direction in ['in','out']:
			opposite = 'out' if direction == 'in' else 'in'

			generator = self._[direction]['generator']
			if generator:
				try:
					# This generator only stops when it raises
					r = generator.next()

					if r is ACTION.immediate: status = 'immediate callback'
					elif r is ACTION.later:   status = 'when possible'
					elif r is ACTION.close:   status = 'stop'
					else: status = 'buggy'
					self.logger.network('%s loop %18s, state is %s' % (direction,status,self._[direction]['state']),'debug')

					if r == ACTION.immediate:
						back = ACTION.immediate
					elif r == ACTION.later:
						back == ACTION.later if back != ACTION.immediate else ACTION.immediate
				except StopIteration:
					# Trying to run a closed loop, no point continuing
					self._[direction]['generator'] = self._[direction]['enabled']

			elif generator is None:
				if self._[opposite]['state'] in [STATE.openconfirm,STATE.established]:
					self.logger.network('%s loop, stopping, other one is established' % direction,'debug')
					self._[direction]['generator'] = False
					continue
				if direction == 'out' and self._skip_time > time.time():
					self.logger.network('%s loop, skipping, not time yet' % direction,'debug')
					back = ACTION.later
					continue
				if self._restart:
					self.logger.network('%s loop, intialising' % direction,'debug')
					self._[direction]['generator'] = self._run(direction)
					back = ACTION.immediate

		return back

########NEW FILE########
__FILENAME__ = protocol
# encoding: utf-8
"""
protocol.py

Created by Thomas Mangin on 2009-08-25.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import os

from exabgp.reactor.network.outgoing import Outgoing
from exabgp.reactor.network.error import NotifyError

from exabgp.bgp.message import Message
from exabgp.bgp.message.nop import NOP,_NOP
from exabgp.bgp.message.unknown import UnknownMessageFactory
from exabgp.bgp.message.open import Open,OpenFactory
from exabgp.bgp.message.open.capability import Capabilities
from exabgp.bgp.message.open.capability.id import REFRESH
from exabgp.bgp.message.open.capability.negotiated import Negotiated
from exabgp.bgp.message.update import Update
from exabgp.bgp.message.update.eor import EOR,EORFactory
from exabgp.bgp.message.keepalive import KeepAlive
from exabgp.bgp.message.notification import NotificationFactory, Notify
from exabgp.bgp.message.refresh import RouteRefresh,RouteRefreshFactory
from exabgp.bgp.message.update.factory import UpdateFactory
from exabgp.bgp.message.operational import Operational,OperationalFactory,OperationalGroup

from exabgp.reactor.api.processes import ProcessError

from exabgp.logger import Logger,FakeLogger

# This is the number of chuncked message we are willing to buffer, not the number of routes
MAX_BACKLOG = 15000

_UPDATE = Update([],'')
_OPERATIONAL = Operational(0x00)

class Protocol (object):
	decode = True

	def __init__ (self,peer):
		try:
			self.logger = Logger()
		except RuntimeError:
			self.logger = FakeLogger()
		self.peer = peer
		self.neighbor = peer.neighbor
		self.negotiated = Negotiated(self.neighbor)
		self.connection = None
		port = os.environ.get('exabgp.tcp.port','')
		self.port = int(port) if port.isdigit() else 179

		# XXX: FIXME: check the the -19 is correct (but it is harmless)
		# The message size is the whole BGP message _without_ headers
		self.message_size = Message.MAX_LEN-Message.HEADER_LEN

	# XXX: we use self.peer.neighbor.peer_address when we could use self.neighbor.peer_address

	def __del__ (self):
		self.close('automatic protocol cleanup')

	def me (self,message):
		return "Peer %15s ASN %-7s %s" % (self.peer.neighbor.peer_address,self.peer.neighbor.peer_as,message)

	def accept (self,incoming):
		self.connection = incoming

		if self.peer.neighbor.api.neighbor_changes:
			self.peer.reactor.processes.connected(self.peer.neighbor.peer_address)

		# very important - as we use this function on __init__
		return self

	def connect (self):
		# allows to test the protocol code using modified StringIO with a extra 'pending' function
		if not self.connection:
			peer = self.neighbor.peer_address
			local = self.neighbor.local_address
			md5 = self.neighbor.md5
			ttl = self.neighbor.ttl
			self.connection = Outgoing(peer.afi,peer.ip,local.ip,self.port,md5,ttl)

			connected = False
			try:
				generator = self.connection.establish()
				while True:
					connected = generator.next()
					if not connected:
						yield False
						continue
					if self.peer.neighbor.api.neighbor_changes:
						self.peer.reactor.processes.connected(self.peer.neighbor.peer_address)
					yield True
					return
			except StopIteration:
				# close called by the caller
				# self.close('could not connect to remote end')
				yield False
				return

	def close (self,reason='protocol closed, reason unspecified'):
		if self.connection:
			self.logger.network(self.me(reason))

			# must be first otherwise we could have a loop caused by the raise in the below
			self.connection.close()
			self.connection = None

			try:
				if self.peer.neighbor.api.neighbor_changes:
					self.peer.reactor.processes.down(self.peer.neighbor.peer_address,reason)
			except ProcessError:
				self.logger.message(self.me('could not send notification of neighbor close to API'))


	def write (self,message):
		if self.neighbor.api.send_packets:
			self.peer.reactor.processes.send(self.peer.neighbor.peer_address,ord(message[18]),message[:19],message[19:])
		for boolean in self.connection.writer(message):
			yield boolean

	# Read from network .......................................................

	def read_message (self,comment=''):
		for length,msg,header,body,notify in self.connection.reader():
			if notify:
				if self.neighbor.api.receive_packets:
					self.peer.reactor.processes.receive(self.peer.neighbor.peer_address,msg,header,body)
				raise Notify(notify.code,notify.subcode,str(notify))
			if not length:
				yield _NOP

		if self.neighbor.api.receive_packets:
			self.peer.reactor.processes.receive(self.peer.neighbor.peer_address,msg,header,body)

		if msg == Message.Type.UPDATE:
			self.logger.message(self.me('<< UPDATE'))

			# This could be speed up massively by changing the order of the IF
			if length == 23:
				update = EORFactory()
				if self.neighbor.api.receive_routes:
					self.peer.reactor.processes.update(self.peer.neighbor.peer_address,update)
			elif length == 30 and body.startswith(EOR.MP):
				update = EORFactory(body)
				if self.neighbor.api.receive_routes:
					self.peer.reactor.processes.update(self.peer.neighbor.peer_address,update)
			elif self.neighbor.api.receive_routes:
				update = UpdateFactory(self.negotiated,body)
				if self.neighbor.api.receive_routes:
					self.peer.reactor.processes.update(self.peer.neighbor.peer_address,update)
			else:
				update = _UPDATE
			yield update

		elif msg == Message.Type.KEEPALIVE:
			self.logger.message(self.me('<< KEEPALIVE%s' % (' (%s)' % comment if comment else '')))
			yield KeepAlive()

		elif msg == Message.Type.NOTIFICATION:
			self.logger.message(self.me('<< NOTIFICATION'))
			yield NotificationFactory(body)

		elif msg == Message.Type.ROUTE_REFRESH:
			if self.negotiated.refresh != REFRESH.absent:
				self.logger.message(self.me('<< ROUTE-REFRESH'))
				refresh = RouteRefreshFactory(body)
				if self.neighbor.api.receive_routes:
					if refresh.reserved in (RouteRefresh.start,RouteRefresh.end):
						self.peer.reactor.processes.refresh(self.peer.neighbor.peer_address,refresh)
			else:
				# XXX: FIXME: really should raise, we are too nice
				self.logger.message(self.me('<< NOP (un-negotiated type %d)' % msg))
				refresh = UnknownMessageFactory(body)
			yield refresh

		elif msg == Message.Type.OPERATIONAL:
			if self.peer.neighbor.operational:
				operational = OperationalFactory(body)
				what = OperationalGroup[operational.what][0]
				self.peer.reactor.processes.operational(self.peer.neighbor.peer_address,what,operational)
			else:
				operational = _OPERATIONAL
			yield operational

		elif msg == Message.Type.OPEN:
			yield OpenFactory(body)

		else:
			# XXX: FIXME: really should raise, we are too nice
			self.logger.message(self.me('<< NOP (unknow type %d)' % msg))
			yield UnknownMessageFactory(msg)

	def validate_open (self):
		error = self.negotiated.validate(self.neighbor)
		if error is not None:
			raise Notify(*error)

	def read_open (self,ip):
		for received_open in self.read_message():
			if received_open.TYPE == NOP.TYPE:
				yield received_open
			else:
				break

		if received_open.TYPE != Open.TYPE:
			raise Notify(5,1,'The first packet recevied is not an open message (%s)' % received_open)

		self.logger.message(self.me('<< %s' % received_open))
		yield received_open

	def read_keepalive (self,comment=''):
		for message in self.read_message(comment):
			if message.TYPE == NOP.TYPE:
				yield message
			else:
				break

		if message.TYPE != KeepAlive.TYPE:
			raise Notify(5,2)

		yield message

	#
	# Sending message to peer
	#

	def new_open (self,restarted):
		sent_open = Open(
			4,
			self.neighbor.local_as,
			self.neighbor.router_id.ip,
			Capabilities().new(self.neighbor,restarted),
			self.neighbor.hold_time
		)

		# we do not buffer open message in purpose
		for _ in self.write(sent_open.message()):
			yield _NOP

		self.logger.message(self.me('>> %s' % sent_open))
		yield sent_open

	def new_keepalive (self,comment=''):
		keepalive = KeepAlive()

		for _ in self.write(keepalive.message()):
			yield _NOP

		self.logger.message(self.me('>> KEEPALIVE%s' % (' (%s)' % comment if comment else '')))

		yield keepalive

	def new_notification (self,notification):
		for _ in self.write(notification.message()):
			yield _NOP
		self.logger.message(self.me('>> NOTIFICATION (%d,%d,"%s")' % (notification.code,notification.subcode,notification.data)))
		yield notification

	def new_update (self):
		updates = self.neighbor.rib.outgoing.updates(self.neighbor.group_updates)
		number = 0
		for update in updates:
			for message in update.messages(self.negotiated):
				number += 1
				for boolean in self.write(message):
					# boolean is a transient network error we already announced
					yield _NOP
		if number:
			self.logger.message(self.me('>> %d UPDATE(s)' % number))
		yield _UPDATE

	def new_eors (self):
		# Send EOR to let our peer know he can perform a RIB update
		if self.negotiated.families:
			for afi,safi in self.negotiated.families:
				eor = EOR(afi,safi).message()
				for _ in self.write(eor):
					yield _NOP
				yield _UPDATE
		else:
			# If we are not sending an EOR, send a keepalive as soon as when finished
			# So the other routers knows that we have no (more) routes to send ...
			# (is that behaviour documented somewhere ??)
			for eor in self.new_keepalive('EOR'):
				yield _NOP
			yield _UPDATE

	def new_operational (self,operational,negotiated):
		for _ in self.write(operational.message(negotiated)):
			yield _NOP
		self.logger.message(self.me('>> OPERATIONAL %s' % str(operational)))
		yield operational

	def new_refresh (self,refresh,negotiated):
		for refresh in refresh.messages(negotiated):
			for _ in self.write(refresh):
				yield _NOP
			self.logger.message(self.me('>> REFRESH %s' % str(refresh)))
			yield refresh

########NEW FILE########
__FILENAME__ = change
# encoding: utf-8
"""
change.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

class Change (object):
	def __init__ (self,nlri,attributes):
		self.nlri = nlri
		self.attributes = attributes

	def index (self):
		return self.nlri.index()

	def __eq__ (self,other):
		return self.nlri == other.nlri and self.attributes == other.attributes

	def __ne__ (self,other):
		return self.nlri != other.nlri or self.attributes != other.attributes

	def extensive (self):
		# If you change this you must change as well extensive in Update
		return "%s%s" % (str(self.nlri),str(self.attributes))

	def __str__ (self):
		return self.extensive()

########NEW FILE########
__FILENAME__ = store
# encoding: utf-8
"""
store.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from exabgp.bgp.message.direction import IN,OUT
from exabgp.bgp.message.update import Update
from exabgp.bgp.message.refresh import RouteRefresh

# XXX: FIXME: we would not have to use so many setdefault if we pre-filled the dicts with the families

class Store (object):
	def __init__ (self,families):
		# XXX: FIXME: we can decide to not cache the routes we seen and let the backend do it for us and save the memory
		self._watchdog = {}
		self.cache = False
		self.families = families
		self.clear()

	# will resend all the routes once we reconnect
	def reset (self):
		# WARNING : this function can run while we are in the updates() loop too !
		self._enhanced_refresh_start = []
		self._enhanced_refresh_delay = []
		for update in self.updates(False): pass

	# back to square one, all the routes are removed
	def clear (self):
		self._cache_attribute = {}
		self._seen = {}
		self._modify_nlri = {}
		self._modify_sorted = {}
		self._changes = None
		self.reset()

	def sent_changes (self,families=None):
		# families can be None or []
		requested_families = self.families if not families else set(families).intersection(self.families)

		# we use list() to make a snapshot of the data at the time we run the command
		for family in requested_families:
			for change in self._seen.get(family,{}).values():
				if change.nlri.action == OUT.announce:
					yield change

	def resend (self,families,enhanced_refresh):
		# families can be None or []
		requested_families = self.families if not families else set(families).intersection(self.families)

		def _announced (family):
			for change in self._seen.get(family,{}).values():
				if change.nlri.action == OUT.announce:
					yield change
			self._seen[family] = {}

		if enhanced_refresh:
			for family in requested_families:
				if family not in self._enhanced_refresh_start:
					self._enhanced_refresh_start.append(family)
					for change in _announced(family):
						self.insert_announced(change,True)
		else:
			for family in requested_families:
				for change in _announced(family):
					self.insert_announced(change,True)

	# def dump (self):
	# 	# This function returns a hash and not a list as "in" tests are O(n) with lists and O(1) with hash
	# 	# and with ten thousands routes this makes an enormous difference (60 seconds to 2)
	# 	changes = {}
	# 	for family in self._seen.keys():
	# 		for change in self._seen[family].values():
	# 			if change.nlri.action == OUT.announce:
	# 				changes[change.index()] = change
	# 	return changes

	def queued_changes (self):
		for change in self._modify_nlri.values():
			yield change

	def update (self,changes):
		self._changes = changes

	def insert_announced_watchdog (self,change):
		watchdog = change.attributes.watchdog()
		withdraw = change.attributes.withdraw()
		if watchdog:
			if withdraw:
				self._watchdog.setdefault(watchdog,{}).setdefault('-',{})[change.nlri.index()] = change
				return True
			self._watchdog.setdefault(watchdog,{}).setdefault('+',{})[change.nlri.index()] = change
		self.insert_announced(change)
		return True

	def announce_watchdog (self,watchdog):
		if watchdog in self._watchdog:
			for change in self._watchdog[watchdog].get('-',{}).values():
				change.nlri.action = OUT.announce
				self.insert_announced(change)
				self._watchdog[watchdog].setdefault('+',{})[change.nlri.index()] = change
				self._watchdog[watchdog]['-'].pop(change.nlri.index())

	def withdraw_watchdog (self,watchdog):
		if watchdog in self._watchdog:
			for change in self._watchdog[watchdog].get('+',{}).values():
				change.nlri.action = OUT.withdraw
				self.insert_announced(change)
				self._watchdog[watchdog].setdefault('-',{})[change.nlri.index()] = change
				self._watchdog[watchdog]['+'].pop(change.nlri.index())

	def insert_received (self,change):
		if not self.cache:
			return
		elif change.nlri.action == IN.announced:
			self._seen[change.nlri.index()] = change
		else:
			self._seen.pop(change.nlri.index(),None)

	def insert_announced (self,change,force=False):
		# WARNING : this function can run while we are in the updates() loop

		# self._seen[family][nlri-index] = change

		# XXX: FIXME: if we fear a conflict of nlri-index between family (very very unlikely)
		# XXX: FIXME: then we should preprend the index() with the AFI and SAFI

		# self._modify_nlri[nlri-index] = change : we are modifying this nlri
		# self._modify_sorted[attr-index][nlri-index] = change : add or remove the nlri
		# self._cache_attribute[attr-index] = change
		# and it allow to overwrite change easily :-)

		# import traceback
		# traceback.print_stack()
		# print "inserting", change.extensive()

		if not force and self._enhanced_refresh_start:
			self._enhanced_refresh_delay.append(change)
			return

		change_nlri_index = change.nlri.index()
		change_attr_index = change.attributes.index()

		dict_sorted = self._modify_sorted
		dict_nlri = self._modify_nlri
		dict_attr = self._cache_attribute

		# removing a route befone we had time to announe it ?
		if change_nlri_index in dict_nlri:
			old_attr_index = dict_nlri[change_nlri_index].attributes.index()
			# pop removes the entry
			old_change = dict_nlri.pop(change_nlri_index)
			# do not delete dict_attr, other routes may use it
			del dict_sorted[old_attr_index][change_nlri_index]
			if not dict_sorted[old_attr_index]:
				del dict_sorted[old_attr_index]
			# route removed before announcement, all goo
			if old_change.nlri.action == OUT.announce and change.nlri.action == OUT.withdraw:
				# if we cache sent NLRI and this NLRI was never sent before, we do not need to send a withdrawal
				if self.cache and change_nlri_index not in self._seen.get(change.nlri.family(),{}):
					return

		# add the route to the list to be announced
		dict_sorted.setdefault(change_attr_index,{})[change_nlri_index] = change
		dict_nlri[change_nlri_index] = change
		if change_attr_index not in dict_attr:
			dict_attr[change_attr_index] = change


	def updates (self,grouped):
		if self._changes:
			dict_nlri = self._modify_nlri

			for family in self._seen:
				for change in self._seen[family].itervalues():
					if change.index() not in self._modify_nlri:
						change.nlri.action = OUT.withdraw
						self.insert_announced(change,True)

			for new in self._changes:
				self.insert_announced(new,True)
			self._changes = None
		# end of changes

		rr_announced = []

		for afi,safi in self._enhanced_refresh_start:
			rr_announced.append((afi,safi))
			yield RouteRefresh(afi,safi,RouteRefresh.start)

		dict_sorted = self._modify_sorted
		dict_nlri = self._modify_nlri
		dict_attr = self._cache_attribute

		for attr_index,full_dict_change in dict_sorted.items():
			if self.cache:
				dict_change = {}
				for nlri_index,change in full_dict_change.iteritems():
					family = change.nlri.family()
					announced = self._seen.get(family,{})
					if change.nlri.action == OUT.announce:
						if nlri_index in announced:
							old_change = announced[nlri_index]
							# it is a duplicate route
							if old_change.attributes.index() == change.attributes.index():
								continue
					elif change.nlri.action == OUT.withdraw:
						if nlri_index not in announced:
							if dict_nlri[nlri_index].nlri.action == OUT.announce:
								continue
					dict_change[nlri_index] = change
			else:
				dict_change = full_dict_change

			if not dict_change:
				continue

			attributes = dict_attr[attr_index].attributes

			# we NEED the copy provided by list() here as insert_announced can be called while we iterate
			changed = list(dict_change.itervalues())

			if grouped:
				update = Update([dict_nlri[nlri_index].nlri for nlri_index in dict_change],attributes)
				for change in changed:
					nlri_index = change.nlri.index()
					del dict_sorted[attr_index][nlri_index]
					del dict_nlri[nlri_index]
				# only yield once we have a consistent state, otherwise it will go wrong
				# as we will try to modify things we are using
				yield update
			else:
				updates = []
				for change in changed:
					updates.append(Update([change.nlri,],attributes))
					nlri_index = change.nlri.index()
					del dict_sorted[attr_index][nlri_index]
					del dict_nlri[nlri_index]
				# only yield once we have a consistent state, otherwise it will go wrong
				# as we will try to modify things we are using
				for update in updates:
					yield update

			if self.cache:
				announced = self._seen
				for change in changed:
					if change.nlri.action == OUT.announce:
						announced.setdefault(change.nlri.family(),{})[change.nlri.index()] = change
					else:
						family = change.nlri.family()
						if family in announced:
							announced[family].pop(change.nlri.index(),None)

		if rr_announced:
			for afi,safi in rr_announced:
				self._enhanced_refresh_start.remove((afi,safi))
				yield RouteRefresh(afi,safi,RouteRefresh.end)

			for change in self._enhanced_refresh_delay:
				self.insert_announced(change,True)
			self.enhanced_refresh_delay = []

			for update in self.updates(grouped):
				yield update

########NEW FILE########
__FILENAME__ = cache
# encoding: utf-8
"""
cache.py

Created by David Farrar on 2012-12-27.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""


import time

class Cache (dict):
	def __init__ (self, min_items=10, max_items=2000, cache_life=3600):
		dict.__init__(self)
		self.ordered = []
		self.min_items = min_items
		self.max_items = max_items
		self.cache_life = cache_life
		self.last_accessed = int(time.time())

	def cache (self, key, value):
		now = int(time.time())

		if now - self.last_accessed >= self.cache_life:
			self.truncate(self.min_items)

		elif len(self) >= self.max_items:
			self.truncate(self.max_items/2)

		if key not in self:
			self.ordered.append(key)

		self.last_accessed = now
		self[key] = value

		return value

	def retrieve (self, key):
		now = int(time.time())
		res = self[key]

		if now - self.last_accessed >= self.cache_life:
			self.truncate(self.min_items)

			# only update the access time if we modified the cache
			self.last_accessed = now

		return res

	def truncate (self, pos):
		pos = len(self.ordered) - pos
		expiring = self.ordered[:pos]
		self.ordered = self.ordered[pos:]

		for _key in expiring:
			self.pop(_key)

if __name__ == '__main__':
	class klass1:
		def __init__ (self, data):
			pass

	class klass2 (object):
		def __init__ (self, data):
			pass

	class klass3:
		def __init__ (self, data):
			self.a = data[0]
			self.b = data[1]
			self.c = data[2]
			self.d = data[3]
			self.e = data[4]

	class klass4:
		def __init__ (self, data):
			self.a = data[0]
			self.b = data[1]
			self.c = data[2]
			self.d = data[3]
			self.e = data[4]

	class _kparent1:
		def __init__ (self, data):
			self.a = data[0]
			self.b = data[1]

	class _kparent2 (object):
		def __init__ (self, data):
			self.a = data[0]
			self.b = data[1]

	class klass5 (_kparent1):
		def __init__ (self, data):
			_kparent1.__init__(self,data)
			self.c = data[2]
			self.d = data[3]
			self.e = data[4]

	class klass6 (_kparent2):
		def __init__ (self, data):
			_kparent2.__init__(self,data)
			self.c = data[2]
			self.d = data[3]
			self.e = data[4]

	class klass7 (klass6):
		pass

	class klass8 (klass6):
		def __init__ (self, data):
			klass6.__init__(self,data)
			self.s = self.a + self.b + self.c + self.d + self.e

	class klass9 (klass6):
		def __init__ (self, data):
			klass6.__init__(self,data)
			self.s1 = self.a + self.b + self.c + self.d + self.e
			self.s2 = self.b + self.c + self.d + self.e
			self.s3 = self.c + self.d + self.e
			self.s4 = self.d + self.e
			self.s5 = self.a + self.b + self.c + self.d
			self.s6 = self.a + self.b + self.c
			self.s7 = self.a + self.b

	COUNT = 100000
	UNIQUE = 5000

	samples = set()
	chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:"|;<>?,./[]{}-=_+!@£$%^&*()'

	from random import choice

	while len(samples) != UNIQUE:
		samples.add(choice(chars)+choice(chars)+choice(chars)+choice(chars)+choice(chars))

	samples = list(samples)

	for klass in [klass1,klass2,klass3,klass4,klass5,klass6,klass7,klass8,klass9]:
		cache = {}

		start = time.time()
		for val in xrange(COUNT):
			val = val % UNIQUE
			_ = klass(samples[val])
		end = time.time()
		time1 = end-start

		print COUNT,'iterations of',klass.__name__,'with',UNIQUE,'uniques classes'
		print "time instance %d" % time1

		cache = Cache()
		start = time.time()
		for val in xrange(COUNT):
			val = val % UNIQUE

			if val in cache:
				_ = cache.retrieve(val)
			else:
				_ = cache.cache(val, klass(samples[val]))

		end = time.time()
		time2 = end-start

		print "time cached  %d" % time2
		print "speedup %.3f" % (time1/time2)
		print

########NEW FILE########
__FILENAME__ = coroutine
# encoding: utf-8
"""
coroutine.py

Created by Thomas Mangin on 2013-07-01.
Copyright (c) 2009-2012 Exa Networks. All rights reserved.
"""

from functools import wraps

def each(function):
	@wraps(function)
	def start(*args, **kwargs):
		generator = function(*args, **kwargs)
		return lambda: generator.next()
	return start

def join (function):
	@wraps(function)
	def start (*args, **kwargs):
		return ''.join(function(*args, **kwargs))
	return start

########NEW FILE########
__FILENAME__ = counter
# encoding: utf-8
"""
counter.py

Created by Thomas Mangin on 2013-07-11.
Copyright (c) 2013-2013 Exa Networks. All rights reserved.
"""

import time

# reporting the number of routes we saw
class Counter (object):
	def __init__ (self,logger,me,interval=3):
		self.logger = logger

		self.me = me
		self.interval = interval
		self.last_update = time.time()
		self.count = 0
		self.last_count = 0

	def display (self):
		left = int(self.last_update  + self.interval - time.time())
		if left <=0:
			self.last_update = time.time()
			if self.count > self.last_count:
				self.last_count = self.count
				self.logger.reactor(self.me('processed %d routes' % self.count))

	def increment (self,count):
		self.count += count

########NEW FILE########
__FILENAME__ = enumeration
# encoding: utf-8
'''
Enumeration.py

Created by Thomas Mangin on 2013-03-18.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
'''

# int are immutable once created: can not set ._str in __init__
class _integer (int):
	def __str__ (self):
		return self._str

class Enumeration (object):
	def __init__(self, *names):
		for number, name in enumerate(names):
			# doing the .parent thing here instead
			number = _integer(pow(2,number))
			number._str = name
			setattr(self, name, number)

########NEW FILE########
__FILENAME__ = errstr
# encoding: utf-8
"""
errstr.py

Created by Thomas Mangin on 2011-03-29.
Copyright (c) 2009-2012 Exa Networks. All rights reserved.
"""

import errno

def errstr (e):
	return '[errno %s], %s' % (errno.errorcode[e.args[0]],str(e))

########NEW FILE########
__FILENAME__ = ip
# encoding: utf-8
"""
od.py

Created by Thomas Mangin on 2009-09-12.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import socket

def isipv4(address):
	try:
		socket.inet_pton(socket.AF_INET, address)
		return True
	except socket.error:
		return False

def isipv6(address):
	try:
		socket.inet_pton(socket.AF_INET6, address)
		return True
	except socket.error:
		return False

def isip(address):
	return isipv4(address) or isipv6(address)

########NEW FILE########
__FILENAME__ = od
# encoding: utf-8
"""
od.py

Created by Thomas Mangin on 2009-09-06.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

def od (value):
	def spaced (value):
		even = None
		for v in value:
			if even is False:
				yield ' '
			yield '%02X' % ord(v)
			even = not even
	return ''.join(spaced(value))

########NEW FILE########
__FILENAME__ = trace
# encoding: utf-8
"""
trace.py

Created by Thomas Mangin on 2009-09-06.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import StringIO
import traceback

def trace ():
	buff = StringIO.StringIO()
	traceback.print_exc(file=buff)
	r = buff.getvalue()
	buff.close()
	return r

########NEW FILE########
__FILENAME__ = usage
# encoding: utf-8
"""
usage.py

Created by Thomas Mangin on 2009-09-06.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

import sys
import resource

if sys.platform == 'darwin':
	# darwin returns bytes
	divisor = 1024.0*1024.0
else:
	# other OS (AFAIK) return a number of pages
	divisor = 1024.0*1024.0/resource.getpagesize()

def usage (label='usage'):
	usage=resource.getrusage(resource.RUSAGE_SELF)
	return '%s: usertime=%s systime=%s mem=%s mb' % (label,usage.ru_utime,usage.ru_stime,(usage.ru_maxrss/divisor))

########NEW FILE########
__FILENAME__ = version
version="3.3.2"

# Do not change the first line as it is parsed by scripts

if __name__ == '__main__':
	import sys
	sys.stdout.write(version)

########NEW FILE########
__FILENAME__ = route
#!/usr/bin/python

# based on netlink.py at ....
# https://gforge.inria.fr/scm/viewvc.php/canso/trunk/tools/netlink.py?view=markup&revision=1360&root=mehani&pathrev=1360
# http://www.linuxjournal.com/article/7356?page=0,1
# http://smacked.org/docs/netlink.pdf
# RFC 3549

import socket
from struct import pack,unpack,calcsize
from collections import namedtuple

class GlobalError (Exception):
	pass

class NetLinkError (GlobalError):
	pass

class _Sequence (object):
	instance = None

	def __init__ (self):
		self._next = 0

	def next (self):
		# XXX: should protect this code with a Mutex
		self._next += 1
		return self._next

def Sequence ():
	# XXX: should protect this code with a Mutex
	if not _Sequence.instance:
		_Sequence.instance = _Sequence()
	return _Sequence.instance

class NetLinkRoute (object):
	_IGNORE_SEQ_FAULTS = True

	NETLINK_ROUTE = 0

	format = namedtuple('Message','type flags seq pid data')
	pid = 0 # os.getpid()

	class Header (object):
		## linux/netlink.h
		PACK  = 'IHHII'
		LEN = calcsize(PACK)

	class Command (object):
		NLMSG_NOOP    = 0x01
		NLMSG_ERROR   = 0x02
		NLMSG_DONE    = 0x03
		NLMSG_OVERRUN = 0x04

	class Flags (object):
		NLM_F_REQUEST = 0x01 # It is query message.
		NLM_F_MULTI   = 0x02 # Multipart message, terminated by NLMSG_DONE
		NLM_F_ACK     = 0x04 # Reply with ack, with zero or error code
		NLM_F_ECHO    = 0x08 # Echo this query

		# Modifiers to GET query
		NLM_F_ROOT   = 0x100 # specify tree root
		NLM_F_MATCH  = 0x200 # return all matching
		NLM_F_DUMP   = NLM_F_ROOT | NLM_F_MATCH
		NLM_F_ATOMIC = 0x400 # atomic GET

		# Modifiers to NEW query
		NLM_F_REPLACE = 0x100 # Override existing
		NLM_F_EXCL    = 0x200 # Do not touch, if it exists
		NLM_F_CREATE  = 0x400 # Create, if it does not exist
		NLM_F_APPEND  = 0x800 # Add to end of list

	errors = {
		Command.NLMSG_ERROR : 'netlink error',
		Command.NLMSG_OVERRUN : 'netlink overrun',
	}

	def __init__ (self):
		self.socket = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, self.NETLINK_ROUTE)
		self.sequence = Sequence()

	def encode (self, type, seq, flags, body, attributes):
		attrs = Attributes().encode(attributes)
		length = self.Header.LEN + len(attrs) + len(body)
		return pack(self.Header.PACK, length, type, flags, seq, self.pid) + body + attrs

	def decode (self,data):
		while data:
			length, ntype, flags, seq, pid = unpack(self.Header.PACK,data[:self.Header.LEN])
			if len(data) < length:
				raise NetLinkError("Buffer underrun")
			yield self.format(ntype, flags, seq, pid, data[self.Header.LEN:length])
			data = data[length:]

	def query (self, type, family=socket.AF_UNSPEC):
		sequence = self.sequence.next()

		message = self.encode(
			type,
			sequence,
			self.Flags.NLM_F_REQUEST | self.Flags.NLM_F_DUMP,
            		pack('Bxxx', family),
			{}
		)

		self.socket.send(message)

		while True:
			data = self.socket.recv(640000)
			for mtype, flags, seq, pid, data in self.decode(data):
				if seq != sequence:
					if self._IGNORE_SEQ_FAULTS:
						continue
					raise NetLinkError("netlink seq mismatch")
            			if mtype == self.Command.NLMSG_DONE:
					raise StopIteration()
				elif type in self.errors:
					raise NetLinkError(self.errors[mtype])
				else:
					yield data

	def change (self, type, family=socket.AF_UNSPEC):
		sequence = self.sequence.next()

		message = self.encode(
			type,
			self.Flags.NLM_F_REQUEST | self.Flags.NLM_F_CREATE,
            		pack('Bxxx', family)
		)

		self.socket.send(message)

		while True:
			data = self.socket.recv(640000)
			for mtype, flags, seq, pid, data in self.decode(data):
				if seq != sequence:
					if self._IGNORE_SEQ_FAULTS:
						continue
					raise NetLinkError("netlink seq mismatch")
            			if mtype == self.Command.NLMSG_DONE:
					raise StopIteration()
				elif type in self.errors:
					raise NetLinkError(self.errors[mtype])
				else:
					yield data


class AttributesError (GlobalError):
	pass

class Attributes (object):
	class Header (object):
		PACK = 'HH'
		LEN = calcsize(PACK)

	class Type (object):
		IFA_UNSPEC     = 0x00
		IFA_ADDRESS    = 0x01
		IFA_LOCAL      = 0x02
		IFA_LABEL      = 0x03
		IFA_BROADCAST  = 0x04
		IFA_ANYCAST    = 0x05
		IFA_CACHEINFO  = 0x06
		IFA_MULTICAST  = 0x07

	def pad (self,len,to=4):
		return (len+to-1) & ~(to-1)

	def decode (self,data):
		while data:
			length, atype, = unpack(self.Header.PACK,data[:self.Header.LEN])
			if len(data) < length:
				raise AttributesError("Buffer underrun %d < %d" % (len(data),length))
			payload = data[self.Header.LEN:length]
			yield atype, payload
			data = data[int((length + 3) / 4) * 4:]

	def _encode (self,atype,payload):
		len = self.Header.LEN + len(payload)
		raw = pack(self.Header.PACK,len,atype) + payload
		pad = self.pad(len) - len(raw)
		if pad: raw += '\0'*pad
		return raw

	def encode (self,attributes):
		return ''.join([self._encode(k,v) for (k,v) in attributes.items()])

class _InfoMessage (object):
	def __init__ (self,route):
		self.route = route

	def decode (self,data):
    		extracted = list(unpack(self.Header.PACK,data[:self.Header.LEN]))
		attributes = Attributes().decode(data[self.Header.LEN:])
		extracted.append(dict(attributes))
    		return self.format(*extracted)

	def extract (self,type):
		for data in self.route.query(type):
			yield self.decode(data)


# 0                   1                   2                   3
# 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|   Family    |   Reserved  |          Device Type              |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                     Interface Index                           |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                      Device Flags                             |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                      Change Mask                              |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

class Link(_InfoMessage):
	class Header (object):
		PACK = 'BxHiII'
		LEN = calcsize(PACK)

	## linux/if_link.h
	format = namedtuple('Info', 'family type index flags change attributes')

	class Command (object):
		## linux/rtnetlink.h
		RTM_NEWLINK = 0x10  # Create a new network interface
		RTM_DELLINK = 0x11  # Destroy a network interface
		RTM_GETLINK = 0x12  # Retrieve information about a network interface (ifinfomsg)
		RTM_SETLINK = 0x13  #

	class Type (object):
		class Family (object):
			AF_INET  = socket.AF_INET
			AF_INET6 = socket.AF_INET6

		class Device (object):
			IFF_UP            = 0x0001 # Interface is administratively up.
			IFF_BROADCAST     = 0x0002 # Valid broadcast address set.
			IFF_DEBUG         = 0x0004 # Internal debugging flag.
			IFF_LOOPBACK      = 0x0008 # Interface is a loopback interface.
			IFF_POINTOPOINT   = 0x0010 # Interface is a point-to-point link.
			IFF_NOTRAILERS    = 0x0020 # Avoid use of trailers.
			IFF_RUNNING       = 0x0040 # Interface is operationally up.
			IFF_NOARP         = 0x0080 # No ARP protocol needed for this interface.
			IFF_PROMISC       = 0x0100 # Interface is in promiscuous mode.
			IFF_ALLMULTI      = 0x0200 # Receive all multicast packets.
			IFF_MASTER        = 0x0400 # Master of a load balancing bundle.
			IFF_SLAVE         = 0x0800 # Slave of a load balancing bundle.
			IFF_MULTICAST     = 0x1000 # Supports multicast.

			IFF_PORTSEL       = 0x2000 # Is able to select media type via ifmap.
			IFF_AUTOMEDIA     = 0x4000 # Auto media selection active.
			IFF_DYNAMIC       = 0x8000 # Interface was dynamically created.

			IFF_LOWER_UP      = 0x10000 # driver signals L1 up
			IFF_DORMANT       = 0x20000 # driver signals dormant
			IFF_ECHO          = 0x40000 # echo sent packet

		class Attribute (object):
			IFLA_UNSPEC      = 0x00
			IFLA_ADDRESS     = 0x01
			IFLA_BROADCAST   = 0x02
			IFLA_IFNAME      = 0x03
			IFLA_MTU         = 0x04
			IFLA_LINK        = 0x05
		        IFLA_QDISC       = 0x06
			IFLA_STATS       = 0x07

	def getLinks (self):
		return self.extract(self.Command.RTM_GETLINK)


#0                   1                   2                   3
#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|   Family    |     Length    |     Flags     |    Scope      |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                     Interface Index                         |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

class Address (_InfoMessage):
	class Header (object):
		PACK = '4Bi'
		LEN = calcsize(PACK)

	format = namedtuple('Address', 'family prefixlen flags scope index attributes')

	class Command (object):
		RTM_NEWADDR = 0x14
		RTM_DELADDR = 0x15
		RTM_GETADDR = 0x16

	class Type (object):
		class Family (object):
			AF_INET  = socket.AF_INET
			AF_INET6 = socket.AF_INET6

		class Flag (object):
			IFA_F_SECONDARY  = 0x00 # For secondary address (alias interface)
			IFA_F_PERMANENT  = 0x00 # For a permanent address set by the user.  When this is not set, it means the address was dynamically created (e.g., by stateless autoconfiguration).
			IFA_F_DEPRECATED = 0x00 # Defines deprecated (IPV4) address
			IFA_F_TENTATIVE  = 0x00 # Defines tentative (IPV4) address (duplicate address detection is still in progress)

		class Scope (object):
			RT_SCOPE_UNIVERSE = 0x00 # Global route
			RT_SCOPE_SITE     = 0x00 # Interior route in the local autonomous system
			RT_SCOPE_LINK     = 0x00 # Route on this link
			RT_SCOPE_HOST     = 0x00 # Route on the local host
			RT_SCOPE_NOWHERE  = 0x00 # Destination does not exist

		class Attribute (object):
			IFLA_UNSPEC      = 0x00
			IFLA_ADDRESS     = 0x01
			IFLA_BROADCAST   = 0x02
			IFLA_IFNAME      = 0x03
			IFLA_MTU         = 0x04
			IFLA_LINK        = 0x05
		        IFLA_QDISC       = 0x06
			IFLA_STATS       = 0x07
			IFLA_COST        = 0x08
			IFLA_PRIORITY    = 0x09
			IFLA_MASTER      = 0x0A
		        IFLA_WIRELESS    = 0x0B
			IFLA_PROTINFO    = 0x0C
			IFLA_TXQLEN      = 0x0D
			IFLA_MAP         = 0x0E
			IFLA_WEIGHT      = 0x0F
		        IFLA_OPERSTATE   = 0x10
			IFLA_LINKMODE    = 0x11
			IFLA_LINKINFO    = 0x12
			IFLA_NET_NS_PID  = 0x13
		        IFLA_IFALIAS     = 0x14
			IFLA_NUM_VF      = 0x15
			IFLA_VFINFO_LIST = 0x16
			IFLA_STATS64     = 0x17
		        IFLA_VF_PORTS    = 0x18
			IFLA_PORT_SELF   = 0x19

	def getAddresses (self):
		return self.extract(self.Command.RTM_GETADDR)

#0                   1                   2                   3
#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|   Family    |    Reserved1  |           Reserved2           |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                     Interface Index                         |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|           State             |     Flags     |     Type      |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

class Neighbor (_InfoMessage):
	class Header (object):
		## linux/if_addr.h
		PACK = 'BxxxiHBB'
		LEN = calcsize(PACK)

	format = namedtuple('Neighbor', 'family index state flags type attributes')

	class Command (object):
		RTM_NEWNEIGH = 0x1C
		RTM_DELNEIGH = 0x1D
		RTM_GETNEIGH = 0x1E

	class Type (object):
		class Family (object):
			AF_INET  = socket.AF_INET
			AF_INET6 = socket.AF_INET6

		class State (object):
			NUD_INCOMPLETE = 0x01 # Still attempting to resolve
			NUD_REACHABLE  = 0x02 # A confirmed working cache entry
			NUD_STALE      = 0x04 # an expired cache entry
			NUD_DELAY      = 0x08 # Neighbor no longer reachable.  Traffic sent, waiting for confirmatio.
			NUD_PROBE      = 0x10 # A cache entry that is currently being re-solicited
			NUD_FAILED     = 0x20 # An invalid cache entry
			# Dummy states
			NUD_NOARP      = 0x40 # A device which does not do neighbor discovery (ARP)
			NUD_PERMANENT  = 0x80 # A static entry
			NUD_NONE       = 0x00

		class Flag (object):
			NTF_USE        = 0x01
			NTF_PROXY      = 0x08 # A proxy ARP entry
			NTF_ROUTER     = 0x80 # An IPv6 router

		class Attribute (object):
			# XXX : Not sure - starts at zero or one ... ??
			NDA_UNSPEC     = 0x00 # Unknown type
			NDA_DST        = 0x01 # A neighbour cache network. layer destination address
			NDA_LLADDR     = 0x02 # A neighbor cache link layer address.
			NDA_CACHEINFO  = 0x03 # Cache statistics
			NDA_PROBES     = 0x04

	def getNeighbors (self):
		return self.extract(self.Command.RTM_GETNEIGH)


#0                   1                   2                   3
#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|   Family    |  Src length   |  Dest length  |     TOS       |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|  Table ID   |   Protocol    |     Scope     |     Type      |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                          Flags                              |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
class Network (_InfoMessage):
	class Header (object):
		## linux/if_addr.h
		PACK = '8BI' # or is it 8Bi ?
		LEN = calcsize(PACK)

	format = namedtuple('Neighbor', 'family src_len dst_len tos table proto scope type flags attributes')

	class Command (object):
		RTM_NEWROUTE = 0x18
		RTM_DELROUTE = 0x19
		RTM_GETROUTE = 0x1A

	class Type (object):
		class Table (object):
			RT_TABLE_UNSPEC   = 0x00 # An unspecified routing table
			RT_TABLE_DEFAULT  = 0xFD # The default table
			RT_TABLE_MAIN     = 0xFE # The main table
			RT_TABLE_LOCAL    = 0xFF # The local table

		class Protocol (object):
			RTPROT_UNSPEC     = 0x00 # Identifies what/who added the route
			RTPROT_REDIRECT   = 0x01 # By an ICMP redirect
			RTPROT_KERNEL     = 0x02 # By the kernel
			RTPROT_BOOT       = 0x03 # During bootup
			RTPROT_STATIC     = 0x04 # By the administrator
			RTPROT_GATED      = 0x08 # GateD
			RTPROT_RA         = 0x09 # RDISC/ND router advertissements
			RTPROT_MRT        = 0x0A # Merit MRT
			RTPROT_ZEBRA      = 0x0B # ZEBRA
			RTPROT_BIRD       = 0x0C # BIRD
			RTPROT_DNROUTED   = 0x0D # DECnet routing daemon
			RTPROT_XORP       = 0x0E # XORP
			RTPROT_NTK        = 0x0F # Netsukuku
			RTPROT_DHCP       = 0x10 # DHCP client
			# YES WE CAN !
			RTPROT_EXABGP     = 0x11 # Exa Networks ExaBGP

		class Scope (object):
			RT_SCOPE_UNIVERSE = 0x00 # Global route
			RT_SCOPE_SITE     = 0xC8 # Interior route in the local autonomous system
			RT_SCOPE_LINK     = 0xFD # Route on this link
			RT_SCOPE_HOST     = 0xFE # Route on the local host
			RT_SCOPE_NOWHERE  = 0xFF # Destination does not exist

		class Type (object):
			RTN_UNSPEC        = 0x00 # Unknown route.
			RTN_UNICAST       = 0x01 # A gateway or direct route.
			RTN_LOCAL         = 0x02 # A local interface route.
			RTN_BROADCAST     = 0x03 # A local broadcast route (sent as a broadcast).
			RTN_ANYCAST       = 0x04 # An anycast route.
			RTN_MULTICAST     = 0x05 # A multicast route.
			RTN_BLACKHOLE     = 0x06 # A silent packet dropping route.
			RTN_UNREACHABLE   = 0x07 # An unreachable destination.  Packets dropped and host unreachable ICMPs are sent to the originator.
			RTN_PROHIBIT      = 0x08 # A packet rejection route.  Packets are dropped and communication prohibited ICMPs are sent to the originator.
			RTN_THROW         = 0x09 # When used with policy routing, continue routing lookup in another table.  Under normal routing, packets are dropped and net unreachable ICMPs are sent to the originator.
			RTN_NAT           = 0x0A # A network address translation rule.
			RTN_XRESOLVE      = 0x0B # Refer to an external resolver (not implemented).

		class Flag (object):
			RTM_F_NOTIFY      = 0x100 # If the route changes, notify the user
			RTM_F_CLONED      = 0x200 # Route is cloned from another route
			RTM_F_EQUALIZE    = 0x400 # Allow randomization of next hop path in multi-path routing (currently not implemented)
			RTM_F_PREFIX      = 0x800 # Prefix Address

		class Attribute (object):
			RTA_UNSPEC        = 0x00 # Ignored.
			RTA_DST           = 0x01 # Protocol address for route destination address.
			RTA_SRC           = 0x02 # Protocol address for route source address.
			RTA_IIF           = 0x03 # Input interface index.
			RTA_OIF           = 0x04 # Output interface index.
			RTA_GATEWAY       = 0x05 # Protocol address for the gateway of the route
			RTA_PRIORITY      = 0x06 # Priority of route.
			RTA_PREFSRC       = 0x07 # Preferred source address in cases where more than one source address could be used.
			RTA_METRICS       = 0x08 # Route metrics attributed to route and associated protocols (e.g., RTT, initial TCP window, etc.).
			RTA_MULTIPATH     = 0x09 # Multipath route next hop's attributes.
#			RTA_PROTOINFO     = 0x0A # Firewall based policy routing attribute.
			RTA_FLOW          = 0x0B # Route realm.
			RTA_CACHEINFO     = 0x0C # Cached route information.
#			RTA_SESSION       = 0x0D
#			RTA_MP_ALGO       = 0x0E
			RTA_TABLE         = 0x0F

	def getRoutes (self):
		return self.extract(self.Command.RTM_GETROUTE)


#0                   1                   2                   3
#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|   Family    |  Reserved1    |         Reserved2             |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                     Interface Index                         |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                      Qdisc handle                           |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                     Parent Qdisc                            |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                        TCM Info                             |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


class TC (_InfoMessage):
	class Header (object):
		PACK = "BxxxiIII"
		LEN = calcsize(PACK)

	class Command (object):
		RTM_NEWQDISC = 36
		RTM_DELQDISC = 37
		RTM_GETQDISC = 38

	class Type (object):
		class Attribute (object):
			TCA_UNSPEC  = 0x00
			TCA_KIND    = 0x01
			TCA_OPTIONS = 0x02
			TCA_STATS   = 0x03
			TCA_XSTATS  = 0x04
			TCA_RATE    = 0x05
			TCA_FCNT    = 0x06
			TCA_STATS2  = 0x07


#0                   1                   2                   3
#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|   Mode    |    Reserved1  |           Reserved2             |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#|                         Range                               |
#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


#   0                   1                   2                   3
#   0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                       Packet ID                             |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                          Mark                               |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                       timestamp_m                           |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                       timestamp_u                           |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                          hook                               |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                       indev_name                            |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                       outdev_name                           |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |           hw_protocol       |        hw_type                |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |         hw_addrlen          |           Reserved            |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                       hw_addr                               |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                       data_len                              |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                      Payload . . .                          |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


class Firewall (_InfoMessage):
	class Header (object):
		PACK = "BxxxI"
		LEN = calcsize(PACK)

	class Packet (object):
		class Header (object):
			PACK = "IIIIIIIHHHHII"
			LEN = calcsize(PACK)


########NEW FILE########
__FILENAME__ = get
#!/usr/bin/python

from netlink.route import *

def main():
	netlink = NetLinkRoute()

	links = {}
	for ifi in Link(netlink).getLinks():
		links[ifi.index] = ifi

	addresses = {}
	for ifa in Address(netlink).getAddresses():
		addresses.setdefault(ifa.index,[]).append(ifa)

	neighbors = {}
	for neighbor in Neighbor(netlink).getNeighbors():
		neighbors.setdefault(neighbor.index,[]).append(neighbor)

	for index, ifi in links.items():
		hwaddr = '<no addr>'
		if Address.Type.Attribute.IFLA_ADDRESS in ifi.attributes:
			hwaddr = ':'.join(x.encode('hex') for x in ifi.attributes[Address.Type.Attribute.IFLA_ADDRESS])
		print "%d: %s %s" % (ifi.index,ifi.attributes[Address.Type.Attribute.IFLA_IFNAME][:-1],hwaddr)

		for ifa in addresses.get(ifi.index,{}):
			address = ifa.attributes.get(Attributes.Type.IFA_ADDRESS)
			if not address:
				continue

			if ifa.family == socket.AF_INET:
				print '  %s %s' % ('inet ', socket.inet_ntop(ifa.family, address))
			elif ifa.family == socket.AF_INET6:
				print '  %s %s' % ('inet6', socket.inet_ntop(ifa.family, address))
			else:
				print '  %d %s' % (ifa.family, address.encode('hex'))

		for neighbor in neighbors.get(ifi.index,{}):
			if neighbor.state == Neighbor.Type.State.NUD_REACHABLE:
				address = neighbor.attributes.get(Neighbor.Type.Flag.NTF_USE,'\0\0\0\0')
				if ifa.family == socket.AF_INET:
					print '  %s %s' % ('inet ', socket.inet_ntop(neighbor.family, address)),
				elif ifa.family == socket.AF_INET6:
					print '  %s %s' % ('inet ', socket.inet_ntop(neighbor.family, address)),
				else:
					print '  %d %s' % (ifa.family, address.encode('hex'))
				print 'mac',':'.join(_.encode('hex') for _ in neighbor.attributes[Neighbor.Type.State.NUD_REACHABLE])


if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = route
#!/usr/bin/python

from netlink.route import *

netmask = {
	32 : '255.255.255.255',
	31 : '255.255.255.254',
	30 : '255.255.255.252',
	29 : '255.255.255.248',
	28 : '255.255.255.240',
	27 : '255.255.255.224',
	26 : '255.255.255.192',
	25 : '255.255.255.128',
	24 : '255.255.255.0',
	23 : '255.255.254.0',
	22 : '255.255.252.0',
	21 : '255.255.248.0',
	20 : '255.255.240.0',
	19 : '255.255.224.0',
	8 : '255.255.192.0',
	17 : '255.255.128.0',
	16 : '255.255.0.0',
	15 : '255.254.0.0',
	14 : '255.252.0.0',
	13 : '255.248.0.0',
	12 : '255.240.0.0',
	11 : '255.224.0.0',
	10 : '255.192.0.0',
	 9 : '255.128.0.0',
	 8 : '255.0.0.0',
	 7 : '254.0.0.0',
	 6 : '252.0.0.0',
	 5 : '248.0.0.0',
	 4 : '240.0.0.0',
	 3 : '224.0.0.0',
	 2 : '192.0.0.0',
	 1 : '128.0.0.0',
	 0 : '0.0.0.0',
}

def main():
	netlink = NetLinkRoute()

	links = {}
	for ifi in Link(netlink).getLinks():
		links[ifi.index] = ifi.attributes.get(Link.Type.Attribute.IFLA_IFNAME).strip('\0')

	print 'Kernel IP routing table'
	print '%-18s %-18s %-18s %-7s %s' % ('Destination','Genmask','Gateway','Metric','Iface')

	for route in Network(netlink).getRoutes():
		if route.family != socket.AF_INET:
			continue

		if not route.type in (Network.Type.Type.RTN_LOCAL,Network.Type.Type.RTN_UNICAST):
			continue

		if route.src_len == 32:
			continue

		destination = route.attributes.get(Network.Type.Attribute.RTA_DST)
		gateway = route.attributes.get(Network.Type.Attribute.RTA_GATEWAY)

		oif = ord(route.attributes.get(Network.Type.Attribute.RTA_OIF)[0])
		metric = ord(route.attributes.get(Network.Type.Attribute.RTA_PRIORITY,'\0')[0])

		dst = '%s' % socket.inet_ntop(route.family, destination) if destination else ''
		gw  = '%s' % socket.inet_ntop(route.family, gateway) if gateway else '0.0.0.0'
		mask = netmask[route.src_len]
		iface = links[oif]

		print '%-18s %-18s %-18s %-7d %-s' % (dst or '0.0.0.0',mask,gw,metric,iface)
		#if gateway: print route


if __name__ == '__main__':
	main()


########NEW FILE########
