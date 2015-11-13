__FILENAME__ = bar_chart
#!/usr/bin/env python
#
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Generate an ascii bar chart for input data

http://github.com/bitly/data_hacks
"""
import sys
import math
from collections import defaultdict
from optparse import OptionParser

def load_stream(input_stream):
    for line in input_stream:
        clean_line = line.strip()
        if not clean_line:
            # skip empty lines (ie: newlines)
            continue
        if clean_line[0] in ['"', "'"]:
            clean_line = clean_line.strip('"').strip("'")
        if clean_line:
            yield clean_line

def run(input_stream, options):
    data = defaultdict(lambda:0)
    for row in input_stream:
        data[row]+=1
    
    if not data:
        print "Error: no data"
        sys.exit(1)
    
    max_length = max([len(key) for key in data.keys()])
    max_length = min(max_length, 50)
    value_characters = 80 - max_length
    max_value = max(data.values())
    scale = int(math.ceil(float(max_value) / value_characters))
    scale = max(1, scale)
    
    print "# each * represents a count of %d" % scale
    
    if options.sort_values:
        # sort by values
        data = [[value,key] for key,value in data.items()]
        if options.reverse_sort:
            data.sort(reverse=True)
        else:
            data.sort()
    else:
        data = [[key,value] for key,value in data.items()]
        data.sort(reverse=options.reverse_sort)
        data = [[value, key] for key,value in data]
    format = "%" + str(max_length) + "s [%6d] %s"
    for value,key in data:
        print format % (key[:max_length], value, (value / scale) * "*")

if __name__ == "__main__":
    parser = OptionParser()
    parser.usage = "cat data | %prog [options]"
    parser.add_option("-k", "--sort-keys", dest="sort_keys", default=True, action="store_true",
                        help="sort by the key [default]")
    parser.add_option("-v", "--sort-values", dest="sort_values", default=False, action="store_true",
                        help="sort by the frequence")
    parser.add_option("-r", "--reverse-sort", dest="reverse_sort", default=False, action="store_true",
                        help="reverse the sort")
    
    (options, args) = parser.parse_args()
    
    if sys.stdin.isatty():
        parser.print_usage()
        print "for more help use --help"
        sys.exit(1)
    run(load_stream(sys.stdin), options)


########NEW FILE########
__FILENAME__ = histogram
#!/usr/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Generate a text format histogram

This is a loose port to python of the Perl version at
http://www.pandamatak.com/people/anand/xfer/histo

http://github.com/bitly/data_hacks
"""

import sys
from decimal import Decimal
import math
from optparse import OptionParser

class MVSD(object):
    """ A class that calculates a running Mean / Variance / Standard Deviation"""
    def __init__(self):
        self.is_started = False
        self.ss = Decimal(0) # (running) sum of square deviations from mean
        self.m = Decimal(0) # (running) mean
        self.total_w = Decimal(0) # weight of items seen
        
    def add(self, x, w=1):
        """ add another datapoint to the Mean / Variance / Standard Deviation"""
        if not isinstance(x, Decimal):
            x = Decimal(x)
        if not self.is_started:
            self.m = x
            self.ss = Decimal(0)
            self.total_w = w
            self.is_started = True
        else:
            temp_w = self.total_w + w
            self.ss += (self.total_w * w * (x - self.m) * (x - self.m )) / temp_w
            self.m += (x - self.m) / temp_w 
            self.total_w = temp_w
        
        # print "added %-2d mean=%0.2f var=%0.2f std=%0.2f" % (x, self.mean(), self.var(), self.sd())
        
    def var(self):
        return self.ss / self.total_w
    
    def sd(self):
        return math.sqrt(self.var())
    
    def mean(self):
        return self.m

def test_mvsd():
    mvsd = MVSD()
    for x in range(10):
        mvsd.add(x)
    
    assert '%.2f' % mvsd.mean() == "4.50"
    assert '%.2f' % mvsd.var() == "8.25"
    assert '%.14f' % mvsd.sd() == "2.87228132326901"

def load_stream(input_stream):
    for line in input_stream:
        clean_line = line.strip()
        if not clean_line:
            # skip empty lines (ie: newlines)
            continue
        if clean_line[0] in ['"', "'"]:
            clean_line = clean_line.strip('"').strip("'")
        try:
            yield Decimal(clean_line)
        except:
            print >>sys.stderr, "invalid line %r" % line

def median(values):
    length = len(values)
    if length%2:
        median_indeces = [length/2]
    else:
        median_indeces = [length/2-1, length/2]

    values = sorted(values)
    return sum([values[i] for i in median_indeces]) / len(median_indeces)

def test_median():
    assert 6 == median([8,7,9,1,2,6,3]) # odd-sized list
    assert 4 == median([4,5,2,1,9,10]) # even-sized int list. (4+5)/2 = 4
    assert "4.50" == "%.2f" % median([4.0,5,2,1,9,10]) #even-sized float list. (4.0+5)/2 = 4.5


def histogram(stream, options):
    """
    Loop over the stream and add each entry to the dataset, printing out at the end
    
    stream yields Decimal() 
    """
    if not options.min or not options.max:
        # glob the iterator here so we can do min/max on it
        data = list(stream)
    else:
        data = stream
    bucket_scale = 1
    
    if options.min:
        min_v = Decimal(options.min)
    else:
        min_v = min(data)
    if options.max:
        max_v = Decimal(options.max)
    else:
        max_v = max(data)

    if not max_v > min_v:
        raise ValueError('max must be > min. max:%s min:%s' % (max_v, min_v))
    diff = max_v - min_v

    boundaries = []
    bucket_counts = []
    buckets = 0

    if options.custbuckets:
        bound = options.custbuckets.split(',')
        bound_sort = sorted(map(Decimal, bound))

        # if the last value is smaller than the maximum, replace it
        if bound_sort[-1] < max_v:
            bound_sort[-1] = max_v
        
        # iterate through the sorted list and append to boundaries
        for x in bound_sort:
            if x >= min_v and x <= max_v:
                boundaries.append(x)
            elif x >= max_v:
                boundaries.append(max_v)
                break

        # beware: the min_v is not included in the boundaries, so no need to do a -1!
        bucket_counts = [0 for x in range(len(boundaries))]
        buckets = len(boundaries)
    else:
        buckets = options.buckets and int(options.buckets) or 10
        if buckets <= 0:
            raise ValueError('# of buckets must be > 0')
        step = diff / buckets
        bucket_counts = [0 for x in range(buckets)]
        for x in range(buckets):
            boundaries.append(min_v + (step * (x + 1)))

    skipped = 0
    samples = 0
    mvsd = MVSD()
    accepted_data = []
    for value in data:
        samples +=1
        if options.mvsd:
            mvsd.add(value)
            accepted_data.append(value)
        # find the bucket this goes in
        if value < min_v or value > max_v:
            skipped +=1
            continue
        for bucket_postion, boundary in enumerate(boundaries):
            if value <= boundary:
                bucket_counts[bucket_postion] +=1
                break
    
    # auto-pick the hash scale
    if max(bucket_counts) > 75:
        bucket_scale = int(max(bucket_counts) / 75)
    
    print "# NumSamples = %d; Min = %0.2f; Max = %0.2f" % (samples, min_v, max_v)
    if skipped:
        print "# %d value%s outside of min/max" % (skipped, skipped > 1 and 's' or '')
    if options.mvsd:
        print "# Mean = %f; Variance = %f; SD = %f; Median %f" % (mvsd.mean(), mvsd.var(), mvsd.sd(), median(accepted_data))
    print "# each * represents a count of %d" % bucket_scale
    bucket_min = min_v
    bucket_max = min_v
    for bucket in range(buckets):
        bucket_min = bucket_max
        bucket_max = boundaries[bucket]
        bucket_count = bucket_counts[bucket]
        star_count = 0
        if bucket_count:
            star_count = bucket_count / bucket_scale
        print '%10.4f - %10.4f [%6d]: %s' % (bucket_min, bucket_max, bucket_count, '*' * star_count)
        

if __name__ == "__main__":
    parser = OptionParser()
    parser.usage = "cat data | %prog [options]"
    parser.add_option("-m", "--min", dest="min",
                        help="minimum value for graph")
    parser.add_option("-x", "--max", dest="max",
                        help="maximum value for graph")
    parser.add_option("-b", "--buckets", dest="buckets",
                        help="Number of buckets to use for the histogram")
    parser.add_option("-B", "--custom-buckets", dest="custbuckets",
                        help="Comma seperated list of bucket edges for the histogram")
    parser.add_option("--no-mvsd", dest="mvsd", action="store_false", default=True,
                        help="Dissable the calculation of Mean, Vairance and SD. (improves performance)")

    (options, args) = parser.parse_args()
    if sys.stdin.isatty():
        # if isatty() that means it's run without anything piped into it
        parser.print_usage()
        print "for more help use --help"
        sys.exit(1)
    histogram(load_stream(sys.stdin), options)


########NEW FILE########
__FILENAME__ = ninety_five_percent
#!/usr/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Calculate the 95% time from a list of times given on stdin

http://github.com/bitly/data_hacks
"""

import sys
import os
from decimal import Decimal

def run():
    count = 0
    data = {}
    for line in sys.stdin:
        line = line.strip()
        if not line:
            # skip empty lines (ie: newlines)
            continue
        try:
            t = Decimal(line)
        except:
            print >>sys.stderr, "invalid line %r" % line
        count +=1
        data[t] = data.get(t, 0) + 1
    print calc_95(data, count)
        
def calc_95(data, count):
    # find the time it took for x entry, where x is the threshold
    threshold = Decimal(count) * Decimal('.95')
    start = Decimal(0)
    times = data.keys()
    times.sort()
    for t in times:
        # increment our count by the # of items in this time bucket
        start += data[t]
        if start > threshold:
            return t

if __name__ == "__main__":
    if sys.stdin.isatty() or '--help' in sys.argv or '-h' in sys.argv:
        print "Usage: cat data | %s" % os.path.basename(sys.argv[0])
        sys.exit(1)
    run()

########NEW FILE########
__FILENAME__ = run_for
#!/usr/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Pass through data for a specified amount of time

http://github.com/bitly/data_hacks
"""

import time
import sys
import os

def getruntime(arg):
    if not arg:
        return
    suffix = arg[-1]
    base = int(arg[:-1])
    if suffix == "s":
        return base
    elif suffix == "m":
        return base * 60
    elif suffix == "h":
        return base * 60 * 60
    elif suffix == "d":
        return base * 60 * 60 * 24
    else:
        print >>sys.stderr, "invalid time suffix %r. must be one of s,m,h,d" % arg

def run(runtime):
    end = time.time() + runtime
    for line in sys.stdin:
        sys.stdout.write(line)
        if time.time() > end:
            return

if __name__ == "__main__":
    usage = "Usage: tail -f access.log | %s [time] | ..." % os.path.basename(sys.argv[0])
    help = "time can be in the format 10s, 10m, 10h, etc"
    if sys.stdin.isatty():
        print usage
        print help
        sys.exit(1)

    runtime = getruntime(sys.argv[-1])
    if not runtime:
        print usage
        sys.exit(1)
    run(runtime)

########NEW FILE########
__FILENAME__ = sample
#!/usr/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Pass through a sampled percentage of data

http://github.com/bitly/data_hacks
"""

import sys
import random
from optparse import OptionParser
from decimal import Decimal

def run(sample_rate):
    input_stream = sys.stdin
    for line in input_stream:
        if random.randint(1,100) <= sample_rate:
            sys.stdout.write(line)

def get_sample_rate(rate_string):
    """ return a rate as a percentage"""
    if rate_string.endswith("%"):
        rate = int(rate_string[:-1])
    elif '/' in rate_string:
        x, y  = rate_string.split('/')
        rate = Decimal(x) / (Decimal(y) * Decimal('1.0'))
        rate = int(rate * 100)
    else:
        raise ValueError("rate %r is invalid rate format must be '10%%' or '1/10'" % rate_string)
    if rate < 1 or rate > 100:
        raise ValueError('rate %r must be 1%% <= rate <= 100%% ' % rate_string)
    return rate

if __name__ == "__main__":
    parser = OptionParser(usage="cat data | %prog [options] [sample_rate]")
    parser.add_option("--verbose", dest="verbose", default=False, action="store_true")
    (options, args) = parser.parse_args()
    
    if not args or sys.stdin.isatty():
        parser.print_usage()
        sys.exit(1)
    
    try:
        sample_rate = get_sample_rate(sys.argv[-1])
    except ValueError, e:
        print >>sys.stderr, e
        parser.print_usage()
        sys.exit(1)
    if options.verbose:
        print >>sys.stderr, "Sample rate is %d%%" % sample_rate 
    run(sample_rate)

########NEW FILE########
