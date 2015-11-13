__FILENAME__ = IpDbGenerate-c
#!/usr/bin/env python

#
# Generates a C-struct
#  Doesn't generate the lookup bsearch algorithm
#

import pprint
from operator import itemgetter
from socket import inet_aton
from struct import unpack
from urllib import urlopen

pp = pprint.PrettyPrinter(indent=4, width=50)
iplist = {}

#fetch remote datacenter list and convert to searchable datastructure
external_list = 'https://raw.github.com/client9/ipcat/master/datacenters.csv'
fp = urlopen(external_list)
for line in fp:
    line = line.strip()
    if not line or line[0] == '#':
        continue

    parts = line.split(",")
    newrow = {
        '_ip0': unpack("!L", inet_aton(parts[0]))[0],
        '_ip1': unpack("!L", inet_aton(parts[1]))[0],
        'owner': parts[3],
    }
    iplist[newrow['_ip0']] = newrow

#return the list of entries, sorted by the lowest ip in the range
iplist = [v for (k,v) in sorted(iplist.iteritems(), key=itemgetter(0))]

#autogenerate the class to perform lookups
print """

#include <stdint.h>

typedef struct ip_range_owner {
  uint32_t ip0;
  uint32_t ip1;
  const char* owner;
} ip_range_owner_t;

ip_range_owner_t iplist[] = {
"""

for val in iplist:
    print '{{ {0},{1},"{2}" }},'.format(val['_ip0'], val['_ip1'], val['owner'])

print "};"

print "const int iplist_len = {0};".format(len(iplist));

print "int main() { return 0; }"

########NEW FILE########
__FILENAME__ = IpDbGenerate
#!/usr/bin/env python
import pprint
from operator import itemgetter
from socket import inet_aton
from struct import unpack
from urllib import urlopen

pp = pprint.PrettyPrinter(indent=4, width=50)
iplist = {}

#fetch remote datacenter list and convert to searchable datastructure
external_list = 'https://raw.github.com/client9/ipcat/master/datacenters.csv'
fp = urlopen(external_list)
for line in fp:
    line = line.strip()
    if not line or line[0] == '#':
        continue

    parts = line.split(",")
    newrow = {
        '_ip0': unpack("!L", inet_aton(parts[0]))[0],
        '_ip1': unpack("!L", inet_aton(parts[1]))[0],
        'owner': parts[3],
    }
    iplist[newrow['_ip0']] = newrow

#return the list of entries, sorted by the lowest ip in the range
iplist = [v for (k,v) in sorted(iplist.iteritems(), key=itemgetter(0))]

#autogenerate the class to perform lookups
print """
from socket import inet_aton
from struct import unpack
from math import floor
class IpDb(object):
    iplist = %s

    @staticmethod
    def find(ipstring):
        ip = unpack("!L", inet_aton(ipstring))[0]

        high = len(IpDb.iplist)-1
        low = 0
        while high >= low:
            probe = int(floor((high+low)/2))
            if IpDb.iplist[probe]['_ip0'] > ip:
                high = probe - 1
            elif IpDb.iplist[probe]['_ip1'] < ip:
                low = probe + 1
            else:
                return IpDb.iplist[probe]
        return None
""" % (pp.pformat(iplist), )
########NEW FILE########
__FILENAME__ = IpDbGenerate-lua1
#!/usr/bin/env python

#
# Generates a C-struct
#  Doesn't generate the lookup bsearch algorithm
#

import pprint
from operator import itemgetter
from socket import inet_aton
from struct import unpack
from urllib import urlopen

pp = pprint.PrettyPrinter(indent=4, width=50)
iplist = {}

#fetch remote datacenter list and convert to searchable datastructure
external_list = 'https://raw.github.com/client9/ipcat/master/datacenters.csv'
fp = urlopen(external_list)
for line in fp:
    line = line.strip()
    if not line or line[0] == '#':
        continue

    parts = line.split(",")
    newrow = {
        '_ip0': unpack("!L", inet_aton(parts[0]))[0],
        '_ip1': unpack("!L", inet_aton(parts[1]))[0],
        'owner': parts[3],
    }
    iplist[newrow['_ip0']] = newrow

#return the list of entries, sorted by the lowest ip in the range
iplist = [v for (k,v) in sorted(iplist.iteritems(), key=itemgetter(0))]


print "local iplist = {"
for val in iplist:
    print '{{ {0},{1},"{2}" }},'.format(val['_ip0'], val['_ip1'], val['owner'])
print "};"

print """
function scan_list(x)
    local iplist = iplist;
    for i,arec in ipairs(iplist) do
        if x >= arec[1] and x <= arec[2] then
           io.write('found it');
           break;
        end
    end
end

function loopit(imax)
    for i=0,imax do
        scan_list(999999999);
    end
end

loopit(100000);

io.write("\\n");
io.write(collectgarbage('count'));
io.write("\\n");

"""

########NEW FILE########
__FILENAME__ = IpDbGenerate-lua2
#!/usr/bin/env python

#
# Generates a C-struct
#  Doesn't generate the lookup bsearch algorithm
#

import pprint
from operator import itemgetter
from socket import inet_aton
from struct import unpack
from urllib import urlopen

pp = pprint.PrettyPrinter(indent=4, width=50)
iplist = {}

#fetch remote datacenter list and convert to searchable datastructure
external_list = 'https://raw.github.com/client9/ipcat/master/datacenters.csv'
fp = urlopen(external_list)
for line in fp:
    line = line.strip()
    if not line or line[0] == '#':
        continue

    parts = line.split(",")
    newrow = {
        '_ip0': unpack("!L", inet_aton(parts[0]))[0],
        '_ip1': unpack("!L", inet_aton(parts[1]))[0],
        'owner': parts[3],
    }
    iplist[newrow['_ip0']] = newrow

#return the list of entries, sorted by the lowest ip in the range
iplist = [v for (k,v) in sorted(iplist.iteritems(), key=itemgetter(0))]


print "local iplist = {"
for val in iplist:
    print '{{ ip0={0},ip1={1},owner="{2}" }},'.format(val['_ip0'], val['_ip1'], val['owner'])
print "};"

print """
function scan_list(x)
    local iplist = iplist;
    for i,arec in ipairs(iplist) do
        if x >= arec.ip0 and x <= arec.ip1 then
           io.write('found it');
           break;
        end
    end
end

function loopit(imax)
    for i=0,imax do
        scan_list(999999999);
    end
end

loopit(100000);

io.write("\\n");
io.write(collectgarbage('count'));
io.write("\\n");

"""

########NEW FILE########
__FILENAME__ = makestats
#!/usr/bin/env python
"""
validates file and produces the README.md file with stats, or pops an exception
"""

import sys
import socket
import struct
from collections import Counter

def ip2int(ip):
    return struct.unpack('>I',socket.inet_aton(ip))[0]

rows = 0
counts = Counter()
total = 0
lastip0 = 0
lastip1 = 0
for line in sys.stdin:
    line = line.strip()
    if len(line) == 0 or line[0] == '#':
        continue
    rows += 1
    parts = line.split(',')
    if len(parts) != 4:
        raise Exception("Line %d has more than 4 entries: %s" % (rows, line))

    (dots0,dots1,name,url) = parts
    ip0 = ip2int(dots0)
    ip1 = ip2int(dots1)
    if ip0 > ip1:
        raise Exception("Line %d has starting IP > ending IP: %s" % (row, line))

    if ip0 <= lastip1:
        raise Exception("Line %d is not sorted: %s" % (row, line))

    # we are correct
    lastip0 = ip0
    lastip1 = ip1

    sz = ip1 - ip0
    total += sz
    counts[name] += sz

print("""ipcat: datasets for categorizing IP addresses.

The first release "datacenters.csv" is focusing
on IPv4 address that correspond to datacenters, co-location centers,
shared and virtual webhosting providers.  In other words, ip addresses
that end web consumers should not be using.

Licensing -- GPL v3
------------------------

The data is licensed under GPL v3, see COPYING for details.

Relaxations and commericial licensing are gladly available by request.
The use of GPL is to prevent commercial data providers from scooping up
this data without compensation or attribution.

This may be changed to another less restrictive license later.

Statistics
------------------------

<table>
<tr><th>IPs</th><td>%d</td></tr>
<tr><th>Records</th><td>%d</td></tr>
<tr><th>ISPs</th><td>%d</td></tr>
</table>

What is the file format?
-------------------------

Standard CSV with ip-start, ip-end (inclusive, in dot-notation), name of provider, url
of provider.  IP ranges are non-overlapping, and in sorted order.

Why is hosting provider XXX is missing?
---------------------------------------

It might not be.  Many providers are resellers of another and will be
included under another name or ip range.

Also, as of 16-Oct-2011, many locations from Africa, Latin
America, Korea and Japan are missing.

Or, it might just be missing.  Please let us know!

Why GitHub + CSV?
-------------------------

The goal of the file format and the use of github was designed to make
it really easy for other to send patches or additions.  It also provides
and easy way of keeping track of changes.

How is this generated?
-------------------------

Manually from users like you, and automatically via proprietary
discovery algorithms.

Who made this?
-------------------------

Nick Galbreath.  See more at http://www.client9.com/

""" % (total, rows, len(counts)))




########NEW FILE########
