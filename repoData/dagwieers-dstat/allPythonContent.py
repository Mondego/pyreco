__FILENAME__ = devtest
#!/usr/bin/python

import sys
sys.path.insert(0, '/usr/share/dstat/')
import dstat, time

devices = ( 
    (  1,   0, 'ram0'),
    (  1,   1, 'ram1'),
    (  3,   1, 'hda1'),
    ( 33,   0, 'hde'),
    (  7,   0, 'loop0'),
    (  7,   1, 'loop1'),
    (  8,   0, '/dev/sda'),
    (  8,   1, '/dev/sda1'),
    (  8,  18, '/dev/sdb2'),
    (  8,  37, '/dev/sdc5'),
    (  9,   0, 'md0'),
    (  9,   1, 'md1'),
    (  9,   2, 'md2'),
    ( 74,  16, '/dev/ida/c2d1'),
    ( 77, 241, '/dev/ida/c5d15p1'),
    ( 98,   0, 'ubd/disc0/disc'),
    ( 98,  16, 'ubd/disc1/disc'),
    (104,   0, 'cciss/c0d0'),
    (104,   2, 'cciss/c0d0p2'),
    (253,   0, 'dm-0'),
    (253,   1, 'dm-1'),
)

for maj, min, device in devices:
    print device, '->', dstat.dev(maj, min)

########NEW FILE########
__FILENAME__ = dstat
../dstat
########NEW FILE########
__FILENAME__ = mmpipe
#!/usr/bin/python
import select, sys, os

def readpipe(file, tmout = 0.001):
    "Read available data from pipe"
    ret = ''
    while not select.select([file.fileno()], [], [], tmout)[0]:
        pass
    while select.select([file.fileno()], [], [], tmout)[0]:
        ret = ret + file.read(1)
    return ret.split('\n')

def dpopen(cmd):
    "Open a pipe for reuse, if already opened, return pipes"
    global pipes
    if 'pipes' not in globals().keys(): pipes = {}
    if cmd not in pipes.keys():
        try:
            import subprocess
            p = subprocess.Popen(cmd, shell=False, bufsize=0, close_fds=True,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            pipes[cmd] = (p.stdin, p.stdout, p.stderr)
        except ImportError:
            pipes[cmd] = os.popen3(cmd, 't', 0)
    return pipes[cmd]

### Unbuffered sys.stdout
sys.stdout = os.fdopen(1, 'w', 0)

### Main entrance
if __name__ == '__main__':
    try:
#        stdin, stdout, stderr = dpopen('/usr/lpp/mmfs/bin/mmpmon -p -s')
#        stdin.write('reset\n')
        stdin, stdout, stderr = dpopen('/bin/bash')
        stdin.write('uname -a\n')
        readpipe(stdout)

        while True:
#            stdin.write('io_s\n')
            stdin.write('cat /proc/stat\n')
            for line in readpipe(stdout):
                print line

    except KeyboardInterrupt, e:
        print

# vim:ts=4:sw=4

########NEW FILE########
__FILENAME__ = mstat
#!/usr/bin/python

### Example2: simple sub-second monitor (ministat)

### This is a quick example showing how to implement your own *stat utility
### If you're interested in such functionality, contact me at dag@wieers.com
import sys
sys.path.insert(0, '/usr/share/dstat/')
import dstat, time

### Set default theme
dstat.theme = dstat.set_theme()

### Allow arguments
try: delay = float(sys.argv[1])
except: delay = 0.2
try: count = int(sys.argv[2])
except: count = 10

### Load stats
stats = []
dstat.starttime = time.time()
dstat.tick = dstat.ticks()
for o in (dstat.dstat_epoch(), dstat.dstat_cpu(), dstat.dstat_mem(), dstat.dstat_load(), dstat.dstat_disk(), dstat.dstat_sys()):
    try: o.check()
    except Exception, e: print e
    else: stats.append(o)

### Make time stats sub-second
stats[0].format = ('t', 14, 0)

### Print headers
title = subtitle = ''
for o in stats:
    title = title + '  ' + o.title()
    subtitle = subtitle + '  ' + o.subtitle()
print '\n' + title + '\n' + subtitle

### Print stats
for dstat.update in range(count):
    line = ''
    for o in stats:
        o.extract()
        line = line + '  ' + o.show()
    print line + dstat.ansi['reset']
    if dstat.update != count-1: time.sleep(delay)
    dstat.tick = 1
print dstat.ansi['reset']

########NEW FILE########
__FILENAME__ = read
#!/usr/bin/python

### Example 1: Direct accessing stats
### This is a quick example showing how you can access dstat data
### If you're interested in this functionality, contact me at dag@wieers.com
import sys
sys.path.insert(0, '/usr/share/dstat/')
import dstat

### Set default theme
dstat.theme = dstat.set_theme()

clear = dstat.ansi['reset']
dstat.tick = dstat.ticks()

c = dstat.dstat_cpu()
print c.title() + '\n' + c.subtitle()
c.extract()
print c.show(), clear
print 'Percentage:', c.val['total']
print 'Raw:', c.cn2['total']
print

m = dstat.dstat_mem()
print m.title() + '\n' + m.subtitle()
m.extract()
print m.show(), clear
print 'Raw:', m.val
print

l = dstat.dstat_load()
print l.title() + '\n' + l.subtitle()
l.extract()
print l.show(), clear
print 'Raw:', l.val
print

d = dstat.dstat_disk()
print d.title() + '\n' + d.subtitle()
d.extract()
print d.show(), clear
print 'Raw:', d.val['total']
print

########NEW FILE########
__FILENAME__ = dstat_battery
### Author: Dag Wieers <dag$wieers,com>
### Author: Sven-Hendrik Haase <sh@lutzhaase.com>

class dstat_plugin(dstat):
    """
    Percentage of remaining battery power as reported by ACPI.
    """
    def __init__(self):
        self.name = 'battery'
        self.type = 'p'
        self.width = 4
        self.scale = 34
        self.battery_type = "none"

    def check(self):
        if os.path.exists('/proc/acpi/battery/'):
            self.battery_type = "procfs"
        elif glob.glob('/sys/class/power_supply/BAT*'):
            self.battery_type = "sysfs"
        else:
            raise Exception, "No ACPI battery information found."

    def vars(self):
        ret = []
        if self.battery_type == "procfs":
            for battery in os.listdir('/proc/acpi/battery/'):
                for line in dopen('/proc/acpi/battery/'+battery+'/state').readlines():
                    l = line.split()
                    if len(l) < 2: continue
                    if l[0] == 'present:' and l[1] == 'yes':
                        ret.append(battery)
        elif self.battery_type == "sysfs":
            for battery in glob.glob('/sys/class/power_supply/BAT*'):
                for line in dopen(battery+'/present').readlines():
                    if int(line[0]) == 1:
                        ret.append(os.path.basename(battery))
        ret.sort()
        return ret

    def nick(self):
        return [name.lower() for name in self.vars]

    def extract(self):
        for battery in self.vars:
            if self.battery_type == "procfs":
                for line in dopen('/proc/acpi/battery/'+battery+'/info').readlines():
                    l = line.split()
                    if len(l) < 4: continue
                    if l[0] == 'last':
                        full = int(l[3])
                        break
                for line in dopen('/proc/acpi/battery/'+battery+'/state').readlines():
                    l = line.split()
                    if len(l) < 3: continue
                    if l[0] == 'remaining':
                        current = int(l[2])
                        break
                if current:
                    self.val[battery] = current * 100.0 / full
                else:
                    self.val[battery] = -1
            elif self.battery_type == "sysfs":
                for line in dopen('/sys/class/power_supply/'+battery+'/capacity').readlines():
                    current = int(line)
                    break
                if current:
                    self.val[battery] = current
                else:
                    self.val[battery] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_battery_remain
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Remaining battery time.

    Calculated from power drain and remaining battery power. Information is
    retrieved from ACPI.
    """

    def __init__(self):
        self.name = 'remain'
        self.type = 't'
        self.width = 5
        self.scale = 0

    def vars(self):
        ret = []
        for battery in os.listdir('/proc/acpi/battery/'):
            for line in dopen('/proc/acpi/battery/'+battery+'/state').readlines():
                l = line.split()
                if len(l) < 2: continue
                if l[0] == 'present:' and l[1] == 'yes':
                    ret.append(battery)
        ret.sort()
        return ret

    def nick(self):
        return [name.lower() for name in self.vars]

    def extract(self):
        for battery in self.vars:
            for line in dopen('/proc/acpi/battery/'+battery+'/state').readlines():
                l = line.split()
                if len(l) < 3: continue
                if l[0:2] == ['remaining', 'capacity:']:
                    remaining = int(l[2])
                    continue
                elif l[0:2] == ['present', 'rate:']:
                    rate = int(l[2])
                    continue

            if rate and remaining:
                self.val[battery] = remaining * 60 / rate
            else:
                self.val[battery] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_condor_queue
### Author: <krikava$gmail,com>

### Condor queue plugin
### Display information about jobs in queue (using condor_q(1))
###
### WARNING: with many jobs in the queue, the condor_q might take quite
### some time to execute and use quite a bit of resources. Consider
### using a longer delay.

import os
import re

global condor_classad

class condor_classad:
    """
    Utility class to work with Condor ClassAds
    """

    global ATTR_VAR_PATTERN
    ATTR_VAR_PATTERN = re.compile(r'\$\((\w+)\)')

    def __init__(self, file=None, config=None):
        if file != None:
            self.attributes = condor_classad._read_from_file(file)
        elif config != None:
            self.attributes = condor_classad._parse(config)

        if self.attributes == None:
            raise Exception, 'condor_config must be initialized either using a file or config text'

        local_config_file = self['LOCAL_CONFIG_FILE']

        if local_config_file != None:
            for k,v in condor_classad._read_from_file(local_config_file).items():
                self.attributes[k] = v

    def __getitem__(self, name):
        if name in self.attributes:
            self._expand(name)
        return self.attributes[name]

    def _expand(self, var):
        if not var in self.attributes:
            return

        while True:
            m = ATTR_VAR_PATTERN.match(self.attributes[var])
            if m == None:
                break
            var_name = m.group(1)
            self.attributes[var] = ATTR_VAR_PATTERN.sub(self.attributes[var_name],
                                                          self.attributes[var])

    @staticmethod
    def _parse(text):
        attributes = {}
        for l in [l for l in text.split('\n') if not l.strip().startswith('#')]:
            l = l.split('=')
            if len(l) <= 1 or len(l[0]) == 0:
                continue
            attributes[l[0].strip()] = ''.join(l[1:]).strip()
        return attributes

    @staticmethod
    def _read_from_file(filename):
        if not os.access(filename, os.R_OK):
            raise Exception, 'Unable to read file %s' % filename
        try:
            f = open(filename)
            return condor_classad._parse((f.read()))
        finally:
            f.close()

class dstat_plugin(dstat):
    """
    Plugin for Condor queue stats
    """

    global CONDOR_Q_STAT_PATTER
    CONDOR_Q_STAT_PATTER = re.compile(r'(\d+) jobs; (\d+) idle, (\d+) running, (\d+) held')

    def __init__(self):
        self.name = 'condor queue'
        self.vars = ('jobs', 'idle', 'running', 'held')
        self.type = 'd'
        self.width = 5
        self.scale = 1
        self.condor_config = None

    def check(self):
        config_file = os.environ['CONDOR_CONFIG']
        if config_file == None:
            raise Exception, 'Environment varibale CONDOR_CONFIG is missing'
        self.condor_config = condor_classad(config_file)

        bin_dir = self.condor_config['BIN']
        if bin_dir == None:
            raise Exception, 'Unable to find BIN directory in condor config file %s' % config_file

        self.condor_status_cmd = os.path.join(bin_dir, 'condor_q')

        if not os.access(self.condor_status_cmd, os.X_OK):
            raise Exception, 'Needs %s in the path' % self.condor_status_cmd
        else:
            try:
                p = os.popen(self.condor_status_cmd+' 2>&1 /dev/null')
                ret = p.close()
                if ret:
                    raise Exception, 'Cannot interface with Condor - condor_q returned != 0?'
            except IOError:
                raise Exception, 'Unable to execute %s' % self.condor_status_cmd
            return True

    def extract(self):
        last_line = None

        try:
	    for repeats in range(3):
                for last_line in cmd_readlines(self.condor_status_cmd):
                    pass

                m = CONDOR_Q_STAT_PATTER.match(last_line)
                if m == None:
                    raise Exception, 'Invalid output from %s. Got: %s' % (cmd, last_line)

                stats = [int(s.strip()) for s in m.groups()]
                for i,j in enumerate(self.vars):
                    self.val[j] = stats[i]
        except Exception:
            for name in self.vars:
                self.val[name] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_cpufreq
### Author: dag@wieers.com

class dstat_plugin(dstat):
    """
    CPU frequency in percentage as reported by ACPI.
    """

    def __init__(self):
        self.name = 'frequency'
        self.type = 'p'
        self.width = 4
        self.scale = 34

    def check(self): 
        for cpu in glob.glob('/sys/devices/system/cpu/cpu[0-9]*'):
            if not os.access(cpu+'/cpufreq/scaling_cur_freq', os.R_OK):
                raise Exception, 'Cannot access acpi %s frequency information' % os.path.basename(cpu)

    def vars(self):
        ret = []
        for name in glob.glob('/sys/devices/system/cpu/cpu[0-9]*'):
            ret.append(os.path.basename(name))
        ret.sort()
        return ret
#       return os.listdir('/sys/devices/system/cpu/')

    def nick(self):
        return [name.lower() for name in self.vars]

    def extract(self):
        for cpu in self.vars:
            for line in dopen('/sys/devices/system/cpu/'+cpu+'/cpufreq/scaling_max_freq').readlines():
                l = line.split()
                max = int(l[0])
            for line in dopen('/sys/devices/system/cpu/'+cpu+'/cpufreq/scaling_cur_freq').readlines():
                l = line.split()
                cur = int(l[0])
            ### Need to close because of bug in sysfs (?)
            dclose('/sys/devices/system/cpu/'+cpu+'/cpufreq/scaling_cur_freq')
            self.set1[cpu] = self.set1[cpu] + cur * 100.0 / max

            if op.update:
                self.val[cpu] = self.set1[cpu] / elapsed
            else:
                self.val[cpu] = self.set1[cpu]

            if step == op.delay:
                self.set1[cpu] = 0

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_dbus
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Number of active dbus sessions.
    """
    def __init__(self):
        self.name = 'dbus'
        self.nick = ('sys', 'ses')
        self.vars = ('system', 'session')
        self.type = 'd'
        self.width = 3
        self.scale = 100

    def check(self):
#       dstat.info(1, 'The dbus module is an EXPERIMENTAL module.')
        try:
            global dbus
            import dbus
            try:
                self.sysbus = dbus.Bus(dbus.Bus.TYPE_SYSTEM).get_service('org.freedesktop.DBus').get_object('/org/freedesktop/DBus', 'org.freedesktop.DBus')
                try:
                    self.sesbus = dbus.Bus(dbus.Bus.TYPE_SESSION).get_service('org.freedesktop.DBus').get_object('/org/freedesktop/DBus', 'org.freedesktop.DBus')
                except:
                    self.sesbus = None
            except:
                raise Exception, 'Unable to connect to dbus message bus'
        except:
            raise Exception, 'Needs python-dbus module'

    def extract(self):
        self.val['system'] = len(self.sysbus.ListServices()) - 1
        try:
            self.val['session'] = len(self.sesbus.ListServices()) - 1
        except:
            self.val['session'] = -1
#       print dir(b); print dir(s); print dir(d); print d.ListServices()
#       print dir(d)
#       print d.ListServices()

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_ddwrt_cpu
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'total cpu'
        self.vars = ( 'usr', 'sys', 'idl' )
        self.type = 'p'
        self.width = 3
        self.scale = 34
        self.server = os.getenv('DSTAT_SNMPSERVER') or '192.168.1.1'
        self.community = os.getenv('DSTAT_SNMPCOMMUNITY') or 'public'

    def check(self):
        try:
            global cmdgen
            from pysnmp.entity.rfc3413.oneliner import cmdgen
        except:
            raise Exception, 'Needs pysnmp and pyasn1 modules'

    def extract(self):
        self.set2['usr'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,11,50,0)))
        self.set2['sys'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,11,52,0)))
        self.set2['idl'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,11,53,0)))
#        self.set2['usr'] = int(snmpget(self.server, self.community, (('UCD-SNMP-MIB', 'ssCpuRawUser'), 0)))
#        self.set2['sys'] = int(snmpget(self.server, self.community, (('UCD-SNMP-MIB', 'ssCpuRawSystem'), 0)))
#        self.set2['idl'] = int(snmpget(self.server, self.community, (('UCD-SNMP-MIB', 'ssCpuRawIdle'), 0)))

        if update:
            for name in self.vars:
                if sum(self.set2.values()) > sum(self.set1.values()):
                    self.val[name] = 100.0 * (self.set2[name] - self.set1[name]) / (sum(self.set2.values()) - sum(self.set1.values()))
                else:
                    self.val[name] = 0

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_ddwrt_load
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'load avg'
        self.nick = ('1m', '5m', '15m')
        self.vars = ('load1', 'load5', 'load15')
        self.type = 'f'
        self.width = 4
        self.scale = 0.5
        self.server = os.getenv('DSTAT_SNMPSERVER') or '192.168.1.1'
        self.community = os.getenv('DSTAT_SNMPCOMMUNITY') or 'public'

    def check(self):
        try:
            global cmdgen
            from pysnmp.entity.rfc3413.oneliner import cmdgen
        except:
            raise Exception, 'Needs pysnmp and pyasn1 modules'

    def extract(self):
        map(lambda x, y: self.val.update({x: float(y)}), self.vars, snmpwalk(self.server, self.community, (1,3,6,1,4,1,2021,10,1,3)))

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_ddwrt_net
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    def __init__(self):
        self.nick = ('recv', 'send')
        self.type = 'b'
        self.cols = 2
        self.server = os.getenv('DSTAT_SNMPSERVER') or '192.168.1.1'
        self.community = os.getenv('DSTAT_SNMPCOMMUNITY') or 'public'

    def check(self):
        try:
            global cmdgen
            from pysnmp.entity.rfc3413.oneliner import cmdgen
        except:
            raise Exception, 'Needs pysnmp and pyasn1 modules'

    def name(self):
        return self.vars

    def vars(self):
        return [ str(x) for x in snmpwalk(self.server, self.community, (1,3,6,1,2,1,2,2,1,2)) ]

    def extract(self):
        map(lambda x, y, z: self.set2.update({x: (int(y), int(z))}), self.vars, snmpwalk(self.server, self.community, (1,3,6,1,2,1,2,2,1,10)), snmpwalk(self.server, self.community, (1,3,6,1,2,1,2,2,1,16)))

        if update:
            for name in self.set2.keys():
                self.val[name] = map(lambda x, y: (y - x) * 1.0 / elapsed, self.set1[name], self.set2[name])

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_disk_avgqu
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    The average queue length of the requests that were issued to the device.
    """

    def __init__(self):
        self.version = 2
        self.nick = ('avgqu',)
        self.type = 'f'
        self.width = 4
        self.scale = 10
        self.diskfilter = re.compile('^([hsv]d[a-z]+\d+|cciss/c\d+d\d+p\d+|dm-\d+|md\d+|mmcblk\d+p\d0|VxVM\d+)$')
        self.open('/proc/diskstats')
        self.cols = 1
        self.struct = dict( rq_ticks=0 )

    def discover(self, *objlist):
        ret = []
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[3:] == ['0',] * 11: continue
            name = l[2]
            ret.append(name)
        for item in objlist: ret.append(item)
        if not ret:
            raise Exception, "No suitable block devices found to monitor"
        return ret

    def vars(self):
        ret = []
        if op.disklist:
            varlist = op.disklist
        else:
            varlist = []
            blockdevices = [os.path.basename(filename) for filename in glob.glob('/sys/block/*')]
            for name in self.discover:
                if self.diskfilter.match(name): continue
                if name not in blockdevices: continue
                varlist.append(name)
            varlist.sort()
        for name in varlist:
            if name in self.discover:
                ret.append(name)
        return ret

    def name(self):
        return self.vars

    def extract(self):
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[3:] == ['0',] * 11: continue
            if l[3] == '0' and l[7] == '0': continue
            name = l[2]
            if name not in self.vars or name == 'total': continue
            self.set2[name] = dict(
                rq_ticks = long(l[13]),
            )

        for name in self.vars:
            self.val[name] = ( ( self.set2[name]['rq_ticks'] - self.set1[name]['rq_ticks'] ) * 1.0 / elapsed / 1000, )

        if step == op.delay:
            self.set1.update(self.set2)

########NEW FILE########
__FILENAME__ = dstat_disk_avgrq
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    The average size (in sectors) of the requests that were issued
    to the device.
    """

    def __init__(self):
        self.version = 2
        self.nick = ('avgrq',)
        self.type = 'f'
        self.width = 4
        self.scale = 10
        self.diskfilter = re.compile('^([hsv]d[a-z]+\d+|cciss/c\d+d\d+p\d+|dm-\d+|md\d+|mmcblk\d+p\d0|VxVM\d+)$')
        self.open('/proc/diskstats')
        self.cols = 1
        self.struct = dict( nr_ios=0, rd_sect=0, wr_sect=0 )

    def discover(self, *objlist):
        ret = []
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[3:] == ['0',] * 11: continue
            name = l[2]
            ret.append(name)
        for item in objlist: ret.append(item)
        if not ret:
            raise Exception, "No suitable block devices found to monitor"
        return ret

    def vars(self):
        ret = []
        if op.disklist:
            varlist = op.disklist
        else:
            varlist = []
            blockdevices = [os.path.basename(filename) for filename in glob.glob('/sys/block/*')]
            for name in self.discover:
                if self.diskfilter.match(name): continue
                if name not in blockdevices: continue
                varlist.append(name)
            varlist.sort()
        for name in varlist:
            if name in self.discover:
                ret.append(name)
        return ret

    def name(self):
        return self.vars

    def extract(self):
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[3:] == ['0',] * 11: continue
            if l[3] == '0' and l[7] == '0': continue
            name = l[2]
            if name not in self.vars or name == 'total': continue
            self.set2[name] = dict(
                nr_ios = long(l[3])+long(l[7]),
                rd_sect = long(l[9]),
                wr_sect = long(l[11]),
            )

        for name in self.vars:
            tput = ( self.set2[name]['nr_ios'] - self.set1[name]['nr_ios'] )
            if tput:
                ticks = self.set2[name]['rd_sect'] - self.set1[name]['rd_sect'] + \
                        self.set2[name]['wr_sect'] - self.set1[name]['wr_sect']
                self.val[name] = ( ticks * 1.0 / tput, )
            else:
                self.val[name] = ( 0.0, )

        if step == op.delay:
            self.set1.update(self.set2)

########NEW FILE########
__FILENAME__ = dstat_disk_svctm
### Author: David Nicklay <david-d$nicklay,com>
### Modified from disk-util: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    The average service time (in milliseconds) for I/O requests that were
    issued to the device.

    Warning! Do not trust this field any more.
    """

    def __init__(self):
        self.version = 2
        self.nick = ('svctm',)
        self.type = 'f'
        self.width = 4
        self.scale = 1
        self.diskfilter = re.compile('^([hsv]d[a-z]+\d+|cciss/c\d+d\d+p\d+|dm-\d+|md\d+|mmcblk\d+p\d0|VxVM\d+)$')
        self.open('/proc/diskstats')
        self.cols = 1
        self.struct = dict( nr_ios=0, tot_ticks=0 )

    def discover(self, *objlist):
        ret = []
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[3:] == ['0',] * 11: continue
            name = l[2]
            ret.append(name)
        for item in objlist: ret.append(item)
        if not ret:
            raise Exception, "No suitable block devices found to monitor"
        return ret

    def vars(self):
        ret = []
        if op.disklist:
            varlist = op.disklist
        else:
            varlist = []
            blockdevices = [os.path.basename(filename) for filename in glob.glob('/sys/block/*')]
            for name in self.discover:
                if self.diskfilter.match(name): continue
                if name not in blockdevices: continue
                varlist.append(name)
            varlist.sort()
        for name in varlist:
            if name in self.discover:
                ret.append(name)
        return ret

    def name(self):
        return self.vars

    def extract(self):
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[3:] == ['0',] * 11: continue
            if l[3] == '0' and l[7] == '0': continue
            name = l[2]
            if name not in self.vars or name == 'total': continue
            self.set2[name] = dict(
                nr_ios = long(l[3])+long(l[7]),
                tot_ticks = long(l[12]),
            )

        for name in self.vars:
            tput = ( self.set2[name]['nr_ios'] - self.set1[name]['nr_ios'] )
            if tput:
                util = ( self.set2[name]['tot_ticks'] - self.set1[name]['tot_ticks'] )
                self.val[name] = ( util * 1.0 / tput, )
            else:
                self.val[name] = ( 0.0, )

        if step == op.delay:
            self.set1.update(self.set2)

########NEW FILE########
__FILENAME__ = dstat_disk_tps
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Number of read and write transactions per device.

    Displays the number of read and write I/O transactions per device.
    """

    def __init__(self):
        self.nick = ('#read', '#writ' )
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.diskfilter = re.compile('^([hsv]d[a-z]+\d+|cciss/c\d+d\d+p\d+|dm-\d+|md\d+|mmcblk\d+p\d0|VxVM\d+)$')
        self.open('/proc/diskstats')
        self.cols = 2

    def discover(self, *objlist):
        ret = []
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[3:] == ['0',] * 11: continue
            name = l[2]
            ret.append(name)
        for item in objlist: ret.append(item)
        if not ret:
            raise Exception, "No suitable block devices found to monitor"
        return ret

    def vars(self):
        ret = []
        if op.disklist:
            varlist = op.disklist
        elif not op.full:
            varlist = ('total',)
        else:
            varlist = []
            for name in self.discover:
                if self.diskfilter.match(name): continue
                if name not in blockdevices(): continue
                varlist.append(name)
#           if len(varlist) > 2: varlist = varlist[0:2]
            varlist.sort()
        for name in varlist:
            if name in self.discover + ['total'] + op.diskset.keys():
                ret.append(name)
        return ret

    def name(self):
        return ['dsk/'+sysfs_dev(name) for name in self.vars]

    def extract(self):
        for name in self.vars: self.set2[name] = (0, 0)
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[3] == '0' and l[7] == '0': continue
            if l[3:] == ['0',] * 11: continue
            name = l[2]
            if not self.diskfilter.match(name):
                self.set2['total'] = ( self.set2['total'][0] + long(l[3]), self.set2['total'][1] + long(l[7]) )
            if name in self.vars and name != 'total':
                self.set2[name] = ( self.set2[name][0] + long(l[3]), self.set2[name][1] + long(l[7]))
            for diskset in self.vars:
                if diskset in op.diskset.keys():
                    for disk in op.diskset[diskset]:
                        if re.match('^'+disk+'$', name):
                            self.set2[diskset] = ( self.set2[diskset][0] + long(l[3]), self.set2[diskset][1] + long(l[7]) )

        for name in self.set2.keys():
            self.val[name] = map(lambda x, y: (y - x) / elapsed, self.set1[name], self.set2[name])

        if step == op.delay:
            self.set1.update(self.set2)

########NEW FILE########
__FILENAME__ = dstat_disk_util
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Percentage of bandwidth utilization for block devices.

    Displays percentage of CPU time during which I/O requests were issued
    to the device (bandwidth utilization for the device). Device saturation
    occurs when this value is close to 100%.
    """

    def __init__(self):
        self.nick = ('util', )
        self.type = 'f'
        self.width = 4
        self.scale = 34
        self.diskfilter = re.compile('^([hsv]d[a-z]+\d+|cciss/c\d+d\d+p\d+|dm-\d+|md\d+|mmcblk\d+p\d0|VxVM\d+)$')
        self.open('/proc/diskstats')
        self.cols = 1
        self.struct = dict( tot_ticks=0 )

    def discover(self, *objlist):
        ret = []
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[3:] == ['0',] * 11: continue
            name = l[2]
            ret.append(name)
        for item in objlist: ret.append(item)
        if not ret:
            raise Exception, "No suitable block devices found to monitor"
        return ret

    def basename(self, disk):
        "Strip /dev/ and convert symbolic link"
        if disk[:5] == '/dev/':
            # file or symlink
            if os.path.exists(disk):
                # e.g. /dev/disk/by-uuid/15e40cc5-85de-40ea-b8fb-cb3a2eaf872
                if os.path.islink(disk):
                    target = os.readlink(disk)
                    # convert relative pathname to absolute
                    if target[0] != '/':
                        target = os.path.join(os.path.dirname(disk), target)
                        target = os.path.normpath(target)
                    print 'dstat: symlink %s -> %s' % (disk, target)
                    disk = target
                # trim leading /dev/
                return disk[5:]
            else:
                print 'dstat: %s does not exist' % disk
        else:
            return disk

    def vars(self):
        ret = []
        if op.disklist:
            varlist = map(self.basename, op.disklist)
        else:
            varlist = []
            for name in self.discover:
                if self.diskfilter.match(name): continue
                if name not in blockdevices(): continue
                varlist.append(name)
#           if len(varlist) > 2: varlist = varlist[0:2]
            varlist.sort()
        for name in varlist:
            if name in self.discover:
                ret.append(name)
        return ret

    def name(self):
        return [sysfs_dev(name) for name in self.vars]

    def extract(self):
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[5] == '0' and l[9] == '0': continue
            if l[3:] == ['0',] * 11: continue
            name = l[2]
            if name not in self.vars: continue
            self.set2[name] = dict(
                tot_ticks = long(l[12])
            )

        for name in self.vars:
            self.val[name] = ( (self.set2[name]['tot_ticks'] - self.set1[name]['tot_ticks']) * 1.0 * hz / elapsed / 1000, )

        if step == op.delay:
            self.set1.update(self.set2)

########NEW FILE########
__FILENAME__ = dstat_disk_wait
### Author: David Nicklay <david-d$nicklay,com>
### Modified from disk-util: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Read and Write average wait times of block devices.

    Displays the average read and write wait times of block devices
    """

    def __init__(self):
        self.nick = ('rawait', 'wawait')
        self.type = 'f'
        self.width = 4
        self.scale = 1
        self.diskfilter = re.compile('^([hsv]d[a-z]+\d+|cciss/c\d+d\d+p\d+|dm-\d+|md\d+|mmcblk\d+p\d0|VxVM\d+)$')
        self.open('/proc/diskstats')
        self.cols = 1
        self.struct = dict( rd_ios=0, wr_ios=0, rd_ticks=0, wr_ticks=0 )

    def discover(self, *objlist):
        ret = []
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[3:] == ['0',] * 11: continue
            name = l[2]
            ret.append(name)
        for item in objlist: ret.append(item)
        if not ret:
            raise Exception, "No suitable block devices found to monitor"
        return ret

    def vars(self):
        ret = []
        if op.disklist:
            varlist = op.disklist
        else:
            varlist = []
            blockdevices = [os.path.basename(filename) for filename in glob.glob('/sys/block/*')]
            for name in self.discover:
                if self.diskfilter.match(name): continue
                if name not in blockdevices: continue
                varlist.append(name)
            varlist.sort()
        for name in varlist:
            if name in self.discover:
                ret.append(name)
        return ret

    def name(self):
        return self.vars

    def extract(self):
        for l in self.splitlines():
            if len(l) < 13: continue
            if l[5] == '0' and l[9] == '0': continue
            if l[3:] == ['0',] * 11: continue
            name = l[2]
            if name not in self.vars: continue
            self.set2[name] = dict(
                rd_ios = long(l[3]),
                wr_ios = long(l[7]),
                rd_ticks = long(l[6]),
                wr_ticks = long(l[10]),
            )

        for name in self.vars:
            rd_tput = self.set2[name]['rd_ios'] - self.set1[name]['rd_ios']
            wr_tput = self.set2[name]['wr_ios'] - self.set1[name]['wr_ios']
            if rd_tput:
                rd_wait = ( self.set2[name]['rd_ticks'] - self.set1[name]['rd_ticks'] ) * 1.0 / rd_tput
            else:
                rd_wait = 0
            if wr_tput:
                wr_wait = ( self.set2[name]['wr_ticks'] - self.set1[name]['wr_ticks'] ) * 1.0 / wr_tput
            else:
                wr_wait = 0
            self.val[name] = ( rd_wait, wr_wait )

        if step == op.delay:
            self.set1.update(self.set2)

########NEW FILE########
__FILENAME__ = dstat_dstat
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Provide more information related to the dstat process.

    The dstat cputime is the total cputime dstat requires per second. On a
    system with one cpu and one core, the total cputime is 1000ms. On a system
    with 2 cores the total is 2000ms. It may help to vizualise the performance
    of Dstat and its selection of plugins.
    """
    def __init__(self):
        self.name = 'dstat'
        self.vars = ('cputime', 'latency')
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.open('/proc/%s/schedstat' % ownpid)

    def extract(self):
        l = self.splitline()
#        l = linecache.getline('/proc/%s/schedstat' % self.pid, 1).split()
        self.set2['cputime'] = long(l[0])
        self.set2['latency'] = long(l[1])

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_dstat_cpu
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Provide CPU information related to the dstat process.

    This plugin shows the CPU utilization for the dstat process itself,
    including the user-space and system-space (kernel) utilization and
    a total of both. On a system with one cpu and one core, the total
    cputime is 1000ms. On a system with 2 cores the total is 2000ms.
    It may help to vizualise the performance of Dstat and its selection
    of plugins.
    """
    def __init__(self):
        self.name = 'dstat cpu'
        self.vars = ('user', 'system', 'total')
        self.nick = ('usr', 'sys', 'tot')
        self.type = 'p'
        self.width = 3
        self.scale = 100

    def extract(self):
        res = resource.getrusage(resource.RUSAGE_SELF)

        self.set2['user'] = float(res.ru_utime)
        self.set2['system'] = float(res.ru_stime)
        self.set2['total'] = float(res.ru_utime) + float(res.ru_stime)

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 100.0 / elapsed / cpunr

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_dstat_ctxt
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Provide Dstat's number of voluntary and involuntary context switches.

    This plugin provides a unique view of the number of voluntary and
    involuntary context switches of the Dstat process itself. It may help
    to vizualise the performance of Dstat and its selection of plugins.
    """
    def __init__(self):
        self.name = 'contxt sw'
        self.vars = ('voluntary', 'involuntary', 'total')
        self.type = 'd'
        self.width = 3
        self.scale = 100

    def extract(self):
        res = resource.getrusage(resource.RUSAGE_SELF)

        self.set2['voluntary'] = float(res.ru_nvcsw)
        self.set2['involuntary'] = float(res.ru_nivcsw)
        self.set2['total'] = (float(res.ru_nvcsw) + float(res.ru_nivcsw))

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_dstat_mem
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Provide memory information related to the dstat process.

    The various values provide information about the memory usage of the
    dstat process. This plugin gives you the possibility to follow memory
    usage changes of dstat over time. It may help to vizualise the
    performance of Dstat and its selection of plugins.
    """
    def __init__(self):
        self.name = 'dstat memory usage'
        self.vars = ('virtual', 'resident', 'shared', 'data')
        self.type = 'd'
        self.open('/proc/%s/statm' % ownpid)

    def extract(self):
        l = self.splitline()
#        l = linecache.getline('/proc/%s/schedstat' % self.pid, 1).split()
        self.val['virtual'] = long(l[0]) * pagesize / 1024
        self.val['resident'] = long(l[1]) * pagesize / 1024
        self.val['shared'] = long(l[2]) * pagesize / 1024
#        self.val['text'] = long(l[3]) * pagesize / 1024
#        self.val['library'] = long(l[4]) * pagesize / 1024
        self.val['data'] = long(l[5]) * pagesize / 1024

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_fan
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Fan speed in RPM (rotations per minute) as reported by ACPI.
    """

    def __init__(self):
        self.name = 'fan'
        self.type = 'd'
        self.width = 4
        self.scale = 500
        self.open('/proc/acpi/ibm/fan')

    def vars(self):
        ret = None
        for l in self.splitlines():
            if l[0] == 'speed:':
                ret = ('speed',)
        return ret

    def check(self):
        if not os.path.exists('/proc/acpi/ibm/fan'):
            raise Exception, 'Needs kernel IBM-ACPI support'

    def extract(self):
        if os.path.exists('/proc/acpi/ibm/fan'):
            for l in self.splitlines():
                if l[0] == 'speed:':
                    self.val['speed'] = int(l[1])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_freespace
### Author: Dag Wieers <dag$wieers,com>

### FIXME: This module needs infrastructure to provide a list of mountpoints
### FIXME: Would be nice to have a total by default (half implemented)

class dstat_plugin(dstat):
    """
    Amount of used and free space per mountpoint.
    """

    def __init__(self):
        self.nick = ('used', 'free')
        self.open('/etc/mtab')
        self.cols = 2

    def vars(self):
        ret = []
        for l in self.splitlines():
            if len(l) < 6: continue
            if l[2] in ('binfmt_misc', 'devpts', 'iso9660', 'none', 'proc', 'sysfs', 'usbfs'): continue
            ### FIXME: Excluding 'none' here may not be what people want (/dev/shm)
            if l[0] in ('devpts', 'none', 'proc', 'sunrpc', 'usbfs'): continue
            name = l[1]
            res = os.statvfs(name)
            if res[0] == 0: continue ### Skip zero block filesystems
            ret.append(name)
        return ret

    def name(self):
        return ['/' + os.path.basename(name) for name in self.vars]

    def extract(self):
        self.val['total'] = (0, 0)
        for name in self.vars:
            res = os.statvfs(name)
            self.val[name] = ( (float(res.f_blocks) - float(res.f_bavail)) * long(res.f_frsize), float(res.f_bavail) * float(res.f_frsize) )
            self.val['total'] = (self.val['total'][0] + self.val[name][0], self.val['total'][1] + self.val[name][1])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_fuse
### Author: Vikas Gorur (http://github.com/vikasgorur)

class dstat_plugin(dstat):
    """
    Waiting calls on mounted FUSE filesystems

    Displays the number of waiting calls on all mounted FUSE filesystems.
    """

    def __init__(self):
        self.name = 'fuse'
        self.type = 'd'
        self.fusectl_path = "/sys/fs/fuse/connections/"
        self.dirs = []

    def check(self):
        info(1, "Module %s is still experimental." % self.filename)

        if not os.path.exists(self.fusectl_path):
            raise Exception, "%s not mounted" % self.fusectl_path
        if len(os.listdir(self.fusectl_path)) == 0:
            raise Exception, "No fuse filesystems mounted"

    def vars(self):
        self.dirs = os.listdir(self.fusectl_path)

        atleast_one_ok = False
        for d in self.dirs:
            if os.access(self.fusectl_path + d + "/waiting", os.R_OK):
                atleast_one_ok = True

        if not atleast_one_ok:
            raise Exception, "User is not root or no fuse filesystems mounted"

        return self.dirs

    def extract(self):
        for d in self.dirs:
            path = self.fusectl_path + d + "/waiting"
            if os.path.exists(path):
                line = dopen(path).readline()
                self.val[d] = long(line)
            else:
                self.val[d] = 0

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_gpfs
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Total amount of read and write throughput (in bytes) on a GPFS filesystem.
    """

    def __init__(self):
        self.name = 'gpfs i/o'
        self.nick = ('read', 'write')
        self.vars = ('_br_', '_bw_')

    def check(self):
        if os.access('/usr/lpp/mmfs/bin/mmpmon', os.X_OK):
            try:
                self.stdin, self.stdout, self.stderr = dpopen('/usr/lpp/mmfs/bin/mmpmon -p -s')
                self.stdin.write('reset\n')
                readpipe(self.stdout)
            except IOError:
                raise Exception, 'Cannot interface with gpfs mmpmon binary'
            return True
        raise Exception, 'Needs GPFS mmpmon binary'

    def extract(self):
        try:
            self.stdin.write('io_s\n')
#           readpipe(self.stderr)
            for line in readpipe(self.stdout):
                if not line: continue
                l = line.split()
                for name in self.vars:
                    self.set2[name] = long(l[l.index(name)+1])
            for name in self.vars:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed
        except IOError, e:
            if op.debug > 1: print '%s: lost pipe to mmpmon, %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1
        except Exception, e:
            if op.debug > 1: print '%s: exception %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_gpfs_ops
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Number of operations performed on a GPFS filesystem.
    """

    def __init__(self):
        self.name = 'gpfs file operations'
        self.nick = ('open', 'clos', 'read', 'writ', 'rdir', 'inod')
        self.vars = ('_oc_', '_cc_', '_rdc_', '_wc_', '_dir_', '_iu_')
        self.type = 'd'
        self.width = 5
        self.scale = 1000

    def check(self): 
        if os.access('/usr/lpp/mmfs/bin/mmpmon', os.X_OK):
            try:
                self.stdin, self.stdout, self.stderr = dpopen('/usr/lpp/mmfs/bin/mmpmon -p -s')
                self.stdin.write('reset\n')
                readpipe(self.stdout)
            except IOError:
                raise Exception, 'Cannot interface with gpfs mmpmon binary'
            return True
        raise Exception, 'Needs GPFS mmpmon binary'

    def extract(self):
        try:
            self.stdin.write('io_s\n')
#           readpipe(self.stderr)
            for line in readpipe(self.stdout):
                if not line: continue
                l = line.split()
                for name in self.vars:
                    self.set2[name] = long(l[l.index(name)+1])
            for name in self.vars:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed
        except IOError, e:
            if op.debug > 1: print '%s: lost pipe to mmpmon, %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1
        except Exception, e:
            if op.debug > 1: print '%s: exception %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_helloworld
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Example "Hello world!" output plugin for aspiring Dstat developers.
    """

    def __init__(self):
        self.name = 'plugin title'
        self.nick = ('counter',)
        self.vars = ('text',)
        self.type = 's'
        self.width = 12
        self.scale = 0

    def extract(self):
        self.val['text'] = 'Hello world!'

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_innodb_buffer
### Author: Dag Wieers <dag$wieers,com>

global mysql_options
mysql_options = os.getenv('DSTAT_MYSQL')

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'innodb pool'
        self.nick = ('crt', 'rea', 'wri')
        self.vars = ('created', 'read', 'written')
        self.type = 'f'
        self.width = 3
        self.scale = 1000

    def check(self): 
        if not os.access('/usr/bin/mysql', os.X_OK):
            raise Exception, 'Needs MySQL binary'
        try:
            self.stdin, self.stdout, self.stderr = dpopen('/usr/bin/mysql -n %s' % mysql_options)
        except IOError, e:
            raise Exception, 'Cannot interface with MySQL binary (%s)' % e

    def extract(self):
        try:
            self.stdin.write('show engine innodb status\G\n')
            line = greppipe(self.stdout, 'Pages read ')

            if line:
                l = line.split()
                self.set2['read'] = int(l[2].rstrip(','))
                self.set2['created'] = int(l[4].rstrip(','))
                self.set2['written'] = int(l[6])

            for name in self.vars:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

            if step == op.delay:
                self.set1.update(self.set2)

        except IOError, e:
            if op.debug > 1: print '%s: lost pipe to mysql, %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

        except Exception, e:
            if op.debug > 1: print '%s: exception: %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_innodb_io
### Author: Dag Wieers <dag$wieers,com>

global mysql_options
mysql_options = os.getenv('DSTAT_MYSQL')

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'innodb io ops '
        self.nick = ('rea', 'wri', 'syn')
        self.vars = ('read', 'write', 'sync')
        self.type = 'f'
        self.width = 3
        self.scale = 1000

    def check(self):
        if os.access('/usr/bin/mysql', os.X_OK):
            try:
                self.stdin, self.stdout, self.stderr = dpopen('/usr/bin/mysql -n %s' % mysql_options)
            except IOError:
                raise Exception, 'Cannot interface with MySQL binary'
            return True
        raise Exception, 'Needs MySQL binary'

    def extract(self):
        try:
            self.stdin.write('show engine innodb status\G\n')
            line = matchpipe(self.stdout, '.*OS file reads,.*')

            if line:
                l = line.split()
                self.set2['read'] = int(l[0])
                self.set2['write'] = int(l[4])
                self.set2['sync'] = int(l[8])

            for name in self.vars:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

            if step == op.delay:
                self.set1.update(self.set2)

        except IOError, e:
            if op.debug > 1: print '%s: lost pipe to mysql, %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

        except Exception, e:
            if op.debug > 1: print '%s: exception' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_innodb_ops
### Author: Dag Wieers <dag$wieers,com>

global mysql_options
mysql_options = os.getenv('DSTAT_MYSQL')

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'innodb ops'
        self.nick = ('ins', 'upd', 'del', 'rea')
        self.vars = ('inserted', 'updated', 'deleted', 'read')
        self.type = 'f'
        self.width = 3
        self.scale = 1000

    def check(self):
        if os.access('/usr/bin/mysql', os.X_OK):
            try:
                self.stdin, self.stdout, self.stderr = dpopen('/usr/bin/mysql -n %s' % mysql_options)
            except IOError:
                raise Exception, 'Cannot interface with MySQL binary'
            return True
        raise Exception, 'Needs MySQL binary'

    def extract(self):
        try:
            self.stdin.write('show engine innodb status\G\n')
            line = greppipe(self.stdout, 'Number of rows inserted')

            if line:
                l = line.split()
                self.set2['inserted'] = int(l[4].rstrip(','))
                self.set2['updated'] = int(l[6].rstrip(','))
                self.set2['deleted'] = int(l[8].rstrip(','))
                self.set2['read'] = int(l[10])

            for name in self.vars:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

            if step == op.delay:
                self.set1.update(self.set2)

        except IOError, e:
            if op.debug > 1: print '%s: lost pipe to mysql, %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

        except Exception, e:
            if op.debug > 1: print '%s: exception' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_lustre
# Author: Brock Palen <brockp@mlds-networks.com>, Kilian Vavalotti <kilian@stanford.edu>

class dstat_plugin(dstat):
    def __init__(self):
        self.nick = ('read', 'write')

    def check(self):
        if not os.path.exists('/proc/fs/lustre/llite'):
            raise Exception, 'Lustre filesystem not found'
        info(1, 'Module %s is still experimental.' % self.filename)

    def name(self):
        return [mount for mount in os.listdir('/proc/fs/lustre/llite')]

    def vars(self):
        return [mount for mount in os.listdir('/proc/fs/lustre/llite')]

    def extract(self):
        for name in self.vars:
            for l in open(os.path.join('/proc/fs/lustre/llite', name, 'stats')).splitlines():
                if len(l) < 6: continue
                if l[0] == 'read_bytes':
                    read = long(l[6])
                elif l[0] == 'write_bytes':
                    write = long(l[6])
            self.set2[name] = (read, write)

            self.val[name] = map(lambda x, y: (y - x) * 1.0 / elapsed, self.set1[name], self.set2[name])

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4

########NEW FILE########
__FILENAME__ = dstat_md_status
### Author: Bert de Bruijn <bert+dstat@debruijn.be>

class dstat_plugin(dstat):
    """
    Recovery state of software RAID rebuild.

    Prints completed recovery percentage and rebuild speed of the md device
    that is actively being recovered or resynced.

    If no devices are being rebuilt, it displays 100%, 0B. If instead
    multiple devices are being rebuilt, it displays the total progress
    and total throughput.
    """

    def __init__(self):
        self.name = 'sw raid'
        self.type = 's'
        self.scale = 0
        self.nick = ('pct speed', )
        self.width = 9
        self.vars = ('text', )
        self.open('/proc/mdstat')

    def check(self):
        if not os.path.exists('/proc/mdstat'):
            raise Exception, 'Needs kernel md support'

    def extract(self):
        pct = 0
        speed = 0
        nr = 0
        for l in self.splitlines():
            if len(l) < 2: continue
            if l[1] in ('recovery', 'reshape', 'resync'):
                nr += 1
                pct += int(l[3][0:2].strip('.%'))
                speed += int(l[6].strip('sped=K/sc')) * 1024
        if nr:
            pct = pct / nr
        else:
            pct = 100
        self.val['text'] = '%s %s' % (cprint(pct, 'p', 3, 34), cprint(speed, 'd', 5, 1024))

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_memcache_hits
### Author: Dean Wilson <dean.wilson@gmail.com>

class dstat_plugin(dstat):
    """
    Memcache hit count plugin.

    Displays the number of memcache get_hits and get_misses.
    """
    def __init__(self):
        self.name = 'Memcache Hits'
        self.nick = ('Hit', 'Miss')
        self.vars = ('get_hits', 'get_misses')
        self.type = 'd'
        self.width = 6
        self.scale = 50

    def check(self):
        try:
            global memcache
            import memcache
            self.mc = memcache.Client(['127.0.0.1:11211'], debug=0)
        except:
            raise Exception, 'Plugin needs the memcache module'

    def extract(self):
        stats = self.mc.get_stats()
        for key in self.vars:
            self.val[key] = long(stats[0][1][key])

########NEW FILE########
__FILENAME__ = dstat_mysql5_cmds
### Author: <lefred@inuits.be>

global mysql_user
mysql_user = os.getenv('DSTAT_MYSQL_USER') or os.getenv('USER')

global mysql_pwd
mysql_pwd = os.getenv('DSTAT_MYSQL_PWD')

class dstat_plugin(dstat):
    """
    Plugin for MySQL 5 commands.
    """
    def __init__(self):
        self.name = 'mysql5 cmds'
        self.nick = ('sel', 'ins','upd','del')
        self.vars = ('Com_select', 'Com_insert','Com_update','Com_delete')
        self.type = 'd'
        self.width = 5
        self.scale = 1

    def check(self): 
        global MySQLdb
        import MySQLdb
        try:
            self.db = MySQLdb.connect(user=mysql_user, passwd=mysql_pwd)
        except Exception, e:
            raise Exception, 'Cannot interface with MySQL server: %s' % e

    def extract(self):
        try:
            c = self.db.cursor()
            for name in self.vars:
                c.execute("""show global status like '%s';""" % name)
                line = c.fetchone()
                if line[0] in self.vars:
                    if line[0] + 'raw' in self.set2:
                        self.set2[line[0]] = long(line[1]) - self.set2[line[0] + 'raw']
                    self.set2[line[0] + 'raw'] = long(line[1])

            for name in self.vars:
                self.val[name] = self.set2[name] * 1.0 / elapsed

            if step == op.delay:
                self.set1.update(self.set2)

        except Exception, e:
            for name in self.vars:
                self.val[name] = -1

########NEW FILE########
__FILENAME__ = dstat_mysql5_conn
### Author: <lefred$inuits,be>

global mysql_user
mysql_user = os.getenv('DSTAT_MYSQL_USER') or os.getenv('USER')

global mysql_pwd
mysql_pwd = os.getenv('DSTAT_MYSQL_PWD')

global mysql_host
mysql_host = os.getenv('DSTAT_MYSQL_HOST')

global mysql_port
mysql_port = os.getenv('DSTAT_MYSQL_PORT')

global mysql_socket
mysql_socket = os.getenv('DSTAT_MYSQL_SOCKET')

class dstat_plugin(dstat):
    """
    Plugin for MySQL 5 connections.
    """

    def __init__(self):
        self.name = 'mysql5 conn'
        self.nick = ('ThCon', '%Con')
        self.vars = ('Threads_connected', 'Threads')
        self.type = 'f'
        self.width = 4
        self.scale = 1

    def check(self): 
        global MySQLdb
        import MySQLdb
        try:
            args = {}
            if mysql_user:
                args['user'] = mysql_user
            if mysql_pwd:
                args['passwd'] = mysql_pwd
            if mysql_host:
                args['host'] = mysql_host
            if mysql_port:
                args['port'] = mysql_port
            if mysql_socket:
                args['unix_socket'] = mysql_socket

            self.db = MySQLdb.connect(**args)
        except Exception, e:
            raise Exception, 'Cannot interface with MySQL server, %s' % e

    def extract(self):
        try:
            c = self.db.cursor()
            c.execute("""show global variables like 'max_connections';""")
            max = c.fetchone()
            c.execute("""show global status like 'Threads_connected';""")
            thread = c.fetchone()
            if thread[0] in self.vars:
                self.set2[thread[0]] = float(thread[1])
                self.set2['Threads'] = float(thread[1]) / float(max[1]) * 100.0

            for name in self.vars:
                self.val[name] = self.set2[name] * 1.0 / elapsed

            if step == op.delay:
                self.set1.update(self.set2)

        except Exception, e:
            for name in self.vars:
                self.val[name] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_mysql5_innodb
### Author: HIROSE Masaaki <hirose31 _at_ gmail.com>

global mysql_options
mysql_options = os.getenv('DSTAT_MYSQL') or ''

global target_status
global _basic_status
global _extra_status
_basic_status = (
    ('Queries'                       , 'qps'),
    ('Com_select'                    , 'sel/s'),
    ('Com_insert'                    , 'ins/s'),
    ('Com_update'                    , 'upd/s'),
    ('Com_delete'                    , 'del/s'),

    ('Connections'                   , 'con/s'),
    ('Threads_connected'             , 'thcon'),
    ('Threads_running'               , 'thrun'),
    ('Slow_queries'                  , 'slow'),
    )
_extra_status = (
    ('Innodb_rows_read'              , 'r#read'),
    ('Innodb_rows_inserted'          , 'r#ins'),
    ('Innodb_rows_updated'           , 'r#upd'),
    ('Innodb_rows_deleted'           , 'r#del'),

    ('Innodb_data_reads'               , 'rdphy'),
    ('Innodb_buffer_pool_read_requests', 'rdlgc'),
    ('Innodb_data_writes'              , 'wrdat'),
    ('Innodb_log_writes'               , 'wrlog'),

    ('innodb_buffer_pool_pages_dirty_pct', '%dirty'),
    )

global calculating_status
calculating_status = (
    'Innodb_buffer_pool_pages_total',
    'Innodb_buffer_pool_pages_dirty',
    )

global gauge
gauge = {
    'Slow_queries'                    : 1,
    'Threads_connected'               : 1,
    'Threads_running'                 : 1,
    }

class dstat_plugin(dstat):
    """
    mysql5-innodb, mysql5-innodb-basic, mysql5-innodb-extra

    display various metircs on MySQL5 and InnoDB.
    """
    def __init__(self):
        self.name = 'MySQL5 InnoDB '
        self.type = 'd'
        self.width = 5
        self.scale = 1000

    def check(self):
        if self.filename.find("basic") >= 0:
            target_status = _basic_status
            self.name += 'basic'
        elif self.filename.find("extra") >= 0:
            target_status = _extra_status
            self.name += 'extra'
        elif self.filename.find("full") >= 0:
            target_status = _basic_status + _extra_status
            self.name += 'full'
        else:
            target_status = _basic_status + _extra_status
            self.name += 'full'

        self.vars = tuple( map((lambda e: e[0]), target_status) )
        self.nick = tuple( map((lambda e: e[1]), target_status) )

        mysql_candidate = ('/usr/bin/mysql', '/usr/local/bin/mysql')
        mysql_cmd = ''
        for mc in mysql_candidate:
            if os.access(mc, os.X_OK):
                mysql_cmd = mc
                break

        if mysql_cmd:
            try:
                self.stdin, self.stdout, self.stderr = dpopen('%s -n %s' % (mysql_cmd, mysql_options))
            except IOError:
                raise Exception, 'Cannot interface with MySQL binary'
            return True
        raise Exception, 'Needs MySQL binary'

    def extract(self):
        try:
            self.stdin.write('show global status;\n')
            for line in readpipe(self.stdout):
                if line == '':
                    break
                s = line.split()
                if s[0] in self.vars:
                    self.set2[s[0]] = float(s[1])
                elif s[0] in calculating_status:
                    self.set2[s[0]] = float(s[1])

            for k in self.vars:
                if k in gauge:
                    self.val[k] = self.set2[k]
                elif k == 'innodb_buffer_pool_pages_dirty_pct':
                    self.val[k] = self.set2['Innodb_buffer_pool_pages_dirty'] / self.set2['Innodb_buffer_pool_pages_total'] * 100
                else:
                    self.val[k] = (self.set2[k] - self.set1[k]) * 1.0 / elapsed

            if step == op.delay:
                self.set1.update(self.set2)

        except IOError, e:
            if op.debug > 1: print '%s: lost pipe to mysql, %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

        except Exception, e:
            if op.debug > 1: print '%s: exception' % (self.filename, e)
            for name in self.vars: self.val[name] = -1


########NEW FILE########
__FILENAME__ = dstat_mysql5_innodb_basic
dstat_mysql5_innodb.py
########NEW FILE########
__FILENAME__ = dstat_mysql5_innodb_extra
dstat_mysql5_innodb.py
########NEW FILE########
__FILENAME__ = dstat_mysql5_io
### Author: <lefred$inuits,be>

global mysql_user
mysql_user = os.getenv('DSTAT_MYSQL_USER') or os.getenv('USER')

global mysql_pwd
mysql_pwd = os.getenv('DSTAT_MYSQL_PWD')

global mysql_host
mysql_host = os.getenv('DSTAT_MYSQL_HOST')

global mysql_port
mysql_port = os.getenv('DSTAT_MYSQL_PORT')

global mysql_socket
mysql_socket = os.getenv('DSTAT_MYSQL_SOCKET')

class dstat_plugin(dstat):
    """
    Plugin for MySQL 5 I/O.
    """

    def __init__(self):
        self.name = 'mysql5 io'
        self.nick = ('recv', 'sent')
        self.vars = ('Bytes_received', 'Bytes_sent')

    def check(self): 
        global MySQLdb
        import MySQLdb
        try:
            args = {}
            if mysql_user:
                args['user'] = mysql_user
            if mysql_pwd:
                args['passwd'] = mysql_pwd
            if mysql_host:
                args['host'] = mysql_host
            if mysql_port:
                args['port'] = mysql_port
            if mysql_socket:
                args['unix_socket'] = mysql_socket

            self.db = MySQLdb.connect(**args)
        except:
            raise Exception, 'Cannot interface with MySQL server'

    def extract(self):
        try:
            c = self.db.cursor()
            c.execute("""show global status like 'Bytes_%';""")
            lines = c.fetchall()
            for line in lines:
                if len(line[1]) < 2: continue
                if line[0] in self.vars:
                    self.set2[line[0]] = float(line[1])

            for name in self.vars:
                self.val[name] = self.set2[name] * 1.0 / elapsed

            if step == op.delay:
                self.set1.update(self.set2)

        except Exception, e:
            for name in self.vars:
                self.val[name] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_mysql5_keys
### Author: <lefred$inuits,be>

global mysql_user
mysql_user = os.getenv('DSTAT_MYSQL_USER') or os.getenv('USER')

global mysql_pwd
mysql_pwd = os.getenv('DSTAT_MYSQL_PWD') 

global mysql_host
mysql_host = os.getenv('DSTAT_MYSQL_HOST')

global mysql_port
mysql_port = os.getenv('DSTAT_MYSQL_PORT')

global mysql_socket
mysql_socket = os.getenv('DSTAT_MYSQL_SOCKET')

class dstat_plugin(dstat):
    """
    Plugin for MySQL 5 Keys.
    """

    def __init__(self):
        self.name = 'mysql5 key status'
        self.nick = ('used', 'read', 'writ', 'rreq', 'wreq')
        self.vars = ('Key_blocks_used', 'Key_reads', 'Key_writes', 'Key_read_requests', 'Key_write_requests')
        self.type = 'f'
        self.width = 4
        self.scale = 1000

    def check(self): 
        global MySQLdb
        import MySQLdb
        try:
            args = {}
            if mysql_user:
                args['user'] = mysql_user
            if mysql_pwd:
                args['passwd'] = mysql_pwd
            if mysql_host:
                args['host'] = mysql_host
            if mysql_port:
                args['port'] = mysql_port
            if mysql_socket:
                args['unix_socket'] = mysql_socket

            self.db = MySQLdb.connect(**args)
        except:
            raise Exception, 'Cannot interface with MySQL server'

    def extract(self):
        try:
            c = self.db.cursor()
            c.execute("""show global status like 'Key_%';""")
            lines = c.fetchall()
            for line in lines:
                if len(line[1]) < 2: continue
                if line[0] in self.vars:
                    self.set2[line[0]] = float(line[1])

            for name in self.vars:
                self.val[name] = self.set2[name] * 1.0 / elapsed

            if step == op.delay:
                self.set1.update(self.set2)

        except Exception, e:
            for name in self.vars:
                self.val[name] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_mysql_io
global mysql_options
mysql_options = os.getenv('DSTAT_MYSQL')

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'mysql io'
        self.nick = ('recv', 'sent')
        self.vars = ('Bytes_received', 'Bytes_sent')

    def check(self): 
        if not os.access('/usr/bin/mysql', os.X_OK):
            raise Exception, 'Needs MySQL binary'
        try:
            self.stdin, self.stdout, self.stderr = dpopen('/usr/bin/mysql -n %s' % mysql_options)
        except IOError:
            raise Exception, 'Cannot interface with MySQL binary'

    def extract(self):
        try:
            self.stdin.write("show status like 'Bytes_%';\n")
            for line in readpipe(self.stdout):
                l = line.split()
                if len(l) < 2: continue
                if l[0] in self.vars:
                    self.set2[l[0]] = float(l[1])

            for name in self.vars:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

            if step == op.delay:
                self.set1.update(self.set2)

        except IOError, e:
            if op.debug > 1: print '%s: lost pipe to mysql, %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

        except Exception, e:
            if op.debug > 1: print 'dstat_innodb_buffer: exception', e
            for name in self.vars: self.val[name] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_mysql_keys
global mysql_options
mysql_options = os.getenv('DSTAT_MYSQL')

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'mysql key status'
        self.nick = ('used', 'read', 'writ', 'rreq', 'wreq')
        self.vars = ('Key_blocks_used', 'Key_reads', 'Key_writes', 'Key_read_requests', 'Key_write_requests')
        self.type = 'f'
        self.width = 4
        self.scale = 1000

    def check(self): 
        if not os.access('/usr/bin/mysql', os.X_OK):
            raise Exception, 'Needs MySQL binary'
        try:
            self.stdin, self.stdout, self.stderr = dpopen('/usr/bin/mysql -n %s' % mysql_options)
        except IOError:
            raise Exception, 'Cannot interface with MySQL binary'

    def extract(self):
        try:
            self.stdin.write("show status like 'Key_%';\n")
            for line in readpipe(self.stdout):
                l = line.split()
                if len(l) < 2: continue
                if l[0] in self.vars:
                    self.set2[l[0]] = float(l[1])

            for name in self.vars:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

            if step == op.delay:
                self.set1.update(self.set2)

        except IOError, e:
            if op.debug > 1: print '%s: lost pipe to mysql, %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1

        except Exception, e:
            if op.debug > 1: print '%s: exception' (self.filename, e)
            for name in self.vars: self.val[name] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_net_packets
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    """
    Number of packets received and send per interface.
    """

    def __init__(self):
        self.nick = ('#recv', '#send')
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.totalfilter = re.compile('^(lo|bond\d+|face|.+\.\d+)$')
        self.open('/proc/net/dev')
        self.cols = 2

    def discover(self, *objlist):
        ret = []
        for l in self.splitlines(replace=':'):
            if len(l) < 17: continue
            if l[2] == '0' and l[10] == '0': continue
            name = l[0]
            if name not in ('lo', 'face'):
                ret.append(name)
        ret.sort()
        for item in objlist: ret.append(item)
        return ret

    def vars(self):
        ret = []
        if op.netlist:
            varlist = op.netlist
        elif not op.full:
            varlist = ('total',)
        else:
            varlist = self.discover
#           if len(varlist) > 2: varlist = varlist[0:2]
            varlist.sort()
        for name in varlist:
            if name in self.discover + ['total', 'lo']:
                ret.append(name)
        if not ret:
            raise Exception, "No suitable network interfaces found to monitor"
        return ret

    def name(self):
        return ['pkt/'+name for name in self.vars]

    def extract(self):
        self.set2['total'] = [0, 0]
        for l in self.splitlines(replace=':'):
            if len(l) < 17: continue
            if l[2] == '0' and l[10] == '0': continue
            name = l[0]
            if name in self.vars :
                self.set2[name] = ( long(l[2]), long(l[10]) )
            if not self.totalfilter.match(name):
                self.set2['total'] = ( self.set2['total'][0] + long(l[2]), self.set2['total'][1] + long(l[10]))

        if update:
            for name in self.set2.keys():
                self.val[name] = map(lambda x, y: (y - x) * 1.0 / elapsed, self.set1[name], self.set2[name])

        if step == op.delay:
            self.set1.update(self.set2)

########NEW FILE########
__FILENAME__ = dstat_nfs3
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'nfs3 client'
        self.nick = ('read', 'writ', 'rdir', 'inod', 'fs', 'cmmt')
        self.vars = ('read', 'write', 'readdir', 'inode', 'filesystem', 'commit')
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.open('/proc/net/rpc/nfs')

    def check(self):
        info(1, 'Module %s is still experimental.' % self.filename)

    def extract(self):
        for l in self.splitlines():
            if not l or l[0] != 'proc3': continue
            self.set2['read'] = long(l[8])
            self.set2['write'] = long(l[9])
            self.set2['readdir'] = long(l[17]) + long(l[18])
            self.set2['inode'] = long(l[3]) + long(l[4]) + long(l[5]) + long(l[6]) + long(l[7]) + long(l[10]) + long(l[11]) + long(l[12]) + long(l[13]) + long(l[14]) + long(l[15]) + long(l[16])
            self.set2['filesystem'] = long(l[19]) + long(l[20]) + long(l[21])
            self.set2['commit'] = long(l[22])

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_nfs3_ops
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'extended nfs3 client operations'
        self.nick = ('null', 'gatr', 'satr', 'look', 'aces', 'rdln', 'read', 'writ', 'crea', 'mkdr', 'syml', 'mknd', 'rm', 'rmdr', 'ren', 'link', 'rdir', 'rdr+', 'fstt', 'fsnf', 'path', 'cmmt')
        self.vars = ('null', 'getattr', 'setattr', 'lookup', 'access', 'readlink', 'read', 'write', 'create', 'mkdir', 'symlink', 'mknod', 'remove', 'rmdir', 'rename', 'link', 'readdir', 'readdirplus', 'fsstat', 'fsinfo', 'pathconf', 'commit')
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.open('/proc/net/rpc/nfs')

    def check(self):
        info(1, 'Module %s is still experimental.' % self.filename)

    def extract(self):
        for l in self.splitlines():
            if not l or l[0] != 'proc3': continue
            for i, name in enumerate(self.vars):
                self.set2[name] = long(l[i+2])

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_nfsd3
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'nfs3 server'
        self.nick = ('read', 'writ', 'rdir', 'inod', 'fs', 'cmmt')
        self.vars = ('read', 'write', 'readdir', 'inode', 'filesystem', 'commit')
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.open('/proc/net/rpc/nfsd')

    def check(self):
        info(1, 'Module %s is still experimental.' % self.filename)

    def extract(self):
        for l in self.splitlines():
            if not l or l[0] != 'proc3': continue
            self.set2['read'] = long(l[8])
            self.set2['write'] = long(l[9])
            self.set2['readdir'] = long(l[18]) + long(l[19])
            self.set2['inode'] = long(l[3]) + long(l[4]) + long(l[5]) + long(l[6]) + long(l[7]) + long(l[10]) + long(l[11]) + long(l[12]) + long(l[13]) + long(l[14]) + long(l[15]) + long(l[16]) + long(l[17])
            self.set2['filesystem'] = long(l[20]) + long(l[21]) + long(l[22])
            self.set2['commit'] = long(l[23])

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_nfsd3_ops
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'extended nfs3 server operations'
        self.nick = ('null', 'gatr', 'satr', 'look', 'aces', 'rdln', 'read', 'writ', 'crea', 'mkdr', 'syml', 'mknd', 'rm', 'rmdr', 'ren', 'link', 'rdir', 'rdr+', 'fstt', 'fsnf', 'path', 'cmmt')
        self.vars = ('null', 'getattr', 'setattr', 'lookup', 'access', 'readlink', 'read', 'write', 'create', 'mkdir', 'symlink', 'mknod', 'remove', 'rmdir', 'rename', 'link', 'readdir', 'readdirplus', 'fsstat', 'fsinfo', 'pathconf', 'commit')
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.open('/proc/net/rpc/nfsd')

    def check(self):
        info(1, 'Module %s is still experimental.' % self.filename)

    def extract(self):
        for l in self.splitlines():
            if not l or l[0] != 'proc3': continue
            for i, name in enumerate(self.vars):
                self.set2[name] = long(l[i+2])

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_nfsd4_ops
### Author: Adam Michel <elfurbe@furbism.com>
### Based on work by: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'nfs4 server'
        # this vars/nick pair is the ones I considered relevant. Any set of the full list would work.
        self.vars = ('read','write','readdir','getattr','setattr','commit','getfh','putfh',
                'savefh','restorefh','open','open_conf','close','access','lookup','remove')
        self.nick = ('read', 'writ', 'rdir', 'gatr','satr','cmmt','gfh','pfh','sfh','rfh',
                'open','opnc','clse','accs','lkup','rem')
        # this is every possible variable for NFSv4 server if you're into that
        #self.vars4 = ('op0-unused', 'op1-unused', 'op2-future' , 'access',
        #        'close', 'commit', 'create', 'delegpurge', 'delegreturn', 'getattr', 'getfh',
        #        'link', 'lock', 'lockt', 'locku', 'lookup', 'lookup_root', 'nverify', 'open',
        #        'openattr', 'open_conf', 'open_dgrd','putfh', 'putpubfh', 'putrootfh',
        #        'read', 'readdir', 'readlink', 'remove', 'rename','renew', 'restorefh',
        #        'savefh', 'secinfo', 'setattr', 'setcltid', 'setcltidconf', 'verify', 'write',
        #        'rellockowner')
        # I separated the NFSv41 ops cause you know, completeness.
        #self.vars41 = ('bc_ctl', 'bind_conn', 'exchange_id', 'create_ses',
        #        'destroy_ses', 'free_stateid', 'getdirdeleg', 'getdevinfo', 'getdevlist',
        #        'layoutcommit', 'layoutget', 'layoutreturn', 'secinfononam', 'sequence',
        #        'set_ssv', 'test_stateid', 'want_deleg', 'destroy_clid', 'reclaim_comp')
        # Just catin' the tuples together to make the full list.
        #self.vars = self.vars4 + self.vars41
        # these are terrible shortnames for every possible variable
        #self.nick4 = ('unsd','unsd','unsd','accs','clse','comm','crt','delp','delr','gatr','gfh',
        #        'link','lock','lckt','lcku','lkup','lkpr','nver','open','opna','opnc','opnd',
        #        'pfh','ppfh','prfh','read','rdir','rlnk','rmv','ren','rnw','rfh','sfh','snfo',
        #        'satr','scid','scic','ver','wrt','rlko')
        #self.nick41 = ('bctl','bcon','eid','cses','dses','fsid',
        #        'gdd','gdi','gdl','lcmt','lget','lrtn','sinn','seq','sets','tsts','wdel','dcid',
        #        'rcmp')
        #self.nick = self.nick4 + self.nick41
        self.type = 'd'
        self.width = 5
        self.scale = 1000

    def check(self):
        # other NFS modules had this, so I left it. It seems to work.
        info(1, 'Module %s is still experimental.' % self.filename)

    def extract(self):
        # list of fields from /proc/net/rpc/nfsd, in order of output 
        # taken from include/linux/nfs4.h in kernel source
        nfsd4_names = ('label', 'fieldcount', 'op0-unused', 'op1-unused', 'op2-future' , 'access',
                'close', 'commit', 'create', 'delegpurge', 'delegreturn', 'getattr', 'getfh',
                'link', 'lock', 'lockt', 'locku', 'lookup', 'lookup_root', 'nverify', 'open',
                'openattr', 'open_conf', 'open_dgrd','putfh', 'putpubfh', 'putrootfh',
                'read', 'readdir', 'readlink', 'remove', 'rename','renew', 'restorefh',
                'savefh', 'secinfo', 'setattr', 'setcltid', 'setcltidconf', 'verify', 'write',
                'rellockowner', 'bc_ctl', 'bind_conn', 'exchange_id', 'create_ses',
                'destroy_ses', 'free_stateid', 'getdirdeleg', 'getdevinfo', 'getdevlist',
                'layoutcommit', 'layoutget', 'layoutreturn', 'secinfononam', 'sequence',
                'set_ssv', 'test_stateid', 'want_deleg', 'destroy_clid', 'reclaim_comp'
                )
        f_nfs = open("/proc/net/rpc/nfsd")
        f_nfs.seek(0)
        for line in f_nfs:
            fields = line.split()
            if fields[0] == "proc4ops": # just grab NFSv4 stats
                assert int(fields[1]) == len(fields[2:]), ("reported field count (%d) does not match actual field count (%d)" % (int(fields[1]), len(fields[2:])))
                for var in self.vars:
                    self.set2[var] = fields[nfsd4_names.index(var)]
                
        for name in self.vars:
            self.val[name] = (int(self.set2[name]) - int(self.set1[name])) * 1.0 / elapsed
        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_nfsstat4
### Author: Adam Michel <elfurbe@furbism.com>
### Based on work by: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'nfs4 client'
        # this vars/nick pair is the ones I considered relevant. Any set of the full list would work.
        self.vars = ('read', 'write', 'readdir', 'commit', 'getattr', 'create', 'link','remove')
        self.nick = ('read', 'writ', 'rdir', 'cmmt', 'gatr','crt','link','rmv')
        # this is every possible variable if you're into that
        #self.vars = ("read", "write", "commit", "open", "open_conf", "open_noat", "open_dgrd", "close", 
        #        "setattr", "fsinfo", "renew", "setclntid", "confirm", "lock", "lockt", "locku", 
        #        "access", "getattr", "lookup", "lookup_root", "remove", "rename", "link", "symlink", 
        #        "create", "pathconf", "statfs", "readlink", "readdir", "server_caps", "delegreturn", 
        #        "getacl", "setacl", "fs_locations", "rel_lkowner", "secinfo")
        # these are terrible shortnames for every possible variable
        #self.nick = ("read", "writ", "comt", "open", "opnc", "opnn", "opnd", "clse", "seta", "fnfo", 
        #        "renw", "stcd", "cnfm", "lock", "lckt", "lcku", "accs", "gatr", "lkup", "lkp_r", 
        #        "rem", "ren", "lnk", "slnk", "crte", "pthc", "stfs", "rdlk", "rdir", "scps", "delr", 
        #        "gacl", "sacl", "fslo", "relo", "seco")
        self.type = 'd'
        self.width = 5
        self.scale = 1000

    def check(self):
        # other NFS modules had this, so I left it. It seems to work.
        info(1, 'Module %s is still experimental.' % self.filename)

    def extract(self):
        # list of fields from nfsstat, in order of output from cat /proc/net/rpc/nfs 
        nfs4_names = ("version", "fieldcount", "null", "read", "write", "commit", "open", "open_conf",
                "open_noat", "open_dgrd", "close", "setattr", "fsinfo", "renew", "setclntid",
                "confirm", "lock", "lockt", "locku", "access", "getattr", "lookup", "lookup_root",
                "remove", "rename", "link", "symlink", "create", "pathconf", "statfs", "readlink",
                "readdir", "server_caps", "delegreturn", "getacl", "setacl", "fs_locations",
                "rel_lkowner", "secinfo")
        f_nfs = open("/proc/net/rpc/nfs")
        f_nfs.seek(0)
        for line in f_nfs:
            fields = line.split()
            if fields[0] == "proc4": # just grab NFSv4 stats
                assert int(fields[1]) == len(fields[2:]), ("reported field count (%d) does not match actual field count (%d)" % (int(fields[1]), len(fields[2:])))
                for var in self.vars:
                    self.set2[var] = fields[nfs4_names.index(var)]
                
        for name in self.vars:
            self.val[name] = (int(self.set2[name]) - int(self.set1[name])) * 1.0 / elapsed
        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_ntp
### Author: Dag Wieers <dag@wieers.com>

global socket
import socket

global struct
import struct

### FIXME: Implement millisecond granularity as well
### FIXME: Interrupts socket if data is overdue (more than 250ms ?)

class dstat_plugin(dstat):
    """
    Time from an NTP server.

    BEWARE: this dstat plugin typically takes a lot longer to run than
    system plugins and for that reason it is important to use an NTP server
    located nearby as well as make sure that it does not impact your other
    counters too much.
    """

    def __init__(self):
        self.name = 'ntp'
        self.nick = ('date/time',)
        self.vars = ('time',)
        self.timefmt = os.getenv('DSTAT_TIMEFMT') or '%d-%m %H:%M:%S'
        self.ntpserver = os.getenv('DSTAT_NTPSERVER') or '0.fedora.pool.ntp.org'
        self.type = 's'
        self.width = len(time.strftime(self.timefmt, time.localtime()))
        self.scale = 0
        self.epoch = 2208988800L
#        socket.setdefaulttimeout(0.25)
        self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        self.socket.settimeout(0.25)

    def gettime(self):
        self.socket.sendto( '\x1b' + 47 * '\0', ( self.ntpserver, 123 ))
        data, address = self.socket.recvfrom(1024)
        return struct.unpack( '!12I', data )[10] - self.epoch

    def check(self):
        try:
            self.gettime()
        except socket.gaierror:
            raise Exception, 'Failed to connect to NTP server %s.' % self.ntpserver
        except socket.error:
            raise Exception, 'Error connecting to NTP server %s.' % self.ntpserver

    def extract(self):
        try:
            self.val['time'] = time.strftime(self.timefmt, time.localtime(self.gettime()))
        except:
            self.val['time'] = theme['error'] + '-'.rjust(self.width-1) + ' '

    def showcsv(self):
        return time.strftime(self.timefmt, time.localtime(self.gettime()))

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_postfix
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'postfix'
        self.nick = ('inco', 'actv', 'dfrd', 'bnce', 'defr')
        self.vars = ('incoming', 'active', 'deferred', 'bounce', 'defer')
        self.type = 'd'
        self.width = 4
        self.scale = 100

    def check(self):
        if not os.access('/var/spool/postfix/active', os.R_OK):
            raise Exception, 'Cannot access postfix queues'

    def extract(self):
        for item in self.vars:
            self.val[item] = len(glob.glob('/var/spool/postfix/'+item+'/*/*'))

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_power
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    """
    Power usage information from ACPI.

    Displays the power usage in watt per hour of your system's battery using
    ACPI information. This information is only available when the battery is
    being used (or being charged).
    """

    def __init__(self):
        self.name = 'power'
        self.nick = ( 'usage', )
        self.vars = ( 'rate', )
        self.type = 'f'
        self.width = 5
        self.scale = 1
        self.rate = 0
        self.batteries = []
        for battery in os.listdir('/proc/acpi/battery/'):
            for line in dopen('/proc/acpi/battery/'+battery+'/state').readlines():
                l = line.split()
                if len(l) < 2: continue
                self.batteries.append(battery)
                break

    def check(self):
        if not self.batteries:
            raise Exception, 'No battery information found, no power usage statistics'

    def extract(self):
        amperes_drawn = 0
        voltage = 0
        watts_drawn = 0
        for battery in self.batteries:
            for line in dopen('/proc/acpi/battery/'+battery+'/state').readlines():
                l = line.split()
                if len(l) < 3: continue
                if l[0] == 'present:' and l[1] != 'yes': continue
                if l[0:2] == ['charging','state:'] and l[2] != 'discharging':
                    voltage = 0
                    break
                if l[0:2] == ['present','voltage:']:
                    voltage = int(l[2]) / 1000.0
                elif l[0:2] == ['present','rate:'] and l[3] == 'mW':
                    watts_drawn = int(l[2]) / 1000.0
                elif l[0:2] == ['present','rate:'] and l[3] == 'mA':
                    amperes_drawn = int(l[2]) / 1000.0

            self.rate = self.rate + watts_drawn + voltage * amperes_drawn

        ### Return error if we found no information
        if self.rate == 0:
            self.rate = -1

        if op.update:
            self.val['rate'] = self.rate / elapsed
        else:
            self.val['rate'] = self.rate

        if step == op.delay:
            self.rate = 0

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_proc_count
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    """
    Total Number of processes on this system.
    """
    def __init__(self):
        self.name = 'procs'
        self.vars = ('total',)
        self.type = 'd'
        self.width = 4
        self.scale = 10

    def extract(self):
        self.val['total'] = len([pid for pid in proc_pidlist()])

########NEW FILE########
__FILENAME__ = dstat_qmail
### Author: Tom Van Looy <tom$ctors,net>

class dstat_plugin(dstat):
    """
    port of qmail_qstat to dstat
    """
    def __init__(self):
        self.name = 'qmail'
        self.nick = ('in_queue', 'not_prep')
        self.vars = ('mess', 'todo')
        self.type = 'd'
        self.width = 4
        self.scale = 100

    def check(self):
        for item in self.vars:
            if not os.access('/var/qmail/queue/'+item, os.R_OK):
                raise Exception, 'Cannot access qmail queues'

    def extract(self):
        for item in self.vars:
            self.val[item] = len(glob.glob('/var/qmail/queue/'+item+'/*/*'))

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_redis
### Author: Jihyun Yu <yjh0502@gmail.com>

global redis_host 
redis_host = os.getenv('DSTAT_REDIS_HOST') or "127.0.0.1"

global redis_port
redis_port = os.getenv('DSTAT_REDIS_PORT') or "6379"

class dstat_plugin(dstat):
    def __init__(self):
        self.type = 'd'
        self.width = 7
        self.scale = 10000
        self.name = 'redis'
        self.nick = ('tps',)
        self.vars = ('tps',)
        self.cmdInfo = '*1\r\n$4\r\ninfo\r\n'

    def get_info(self):
        global socket
        import socket

        global redis_host
        global redis_port

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(0.1)
            s.connect((redis_host, int(redis_port)))
            s.send(self.cmdInfo)
            dict = {};
            for line in s.recv(1024*1024).split('\r\n'):
                if line == "" or line[0] == '#' or line[0] == '*' or line[0] == '$':
                    continue
                pair = line.split(':', 2)
                dict[pair[0]] = pair[1]
            return dict
        except:
            return {}
        finally:
            try:
                s.close()
            except:
                pass

    def extract(self):
        key = "instantaneous_ops_per_sec"
        dic = self.get_info()
        if key in dic:
            self.val['tps'] = int(dic[key])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_rpc
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'rpc client'
        self.nick = ('call', 'retr', 'refr')
        self.vars = ('calls', 'retransmits', 'autorefreshes')
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.open('/proc/net/rpc/nfs')

    def extract(self):
        for l in self.splitlines():
            if not l or l[0] != 'rpc': continue
            for i, name in enumerate(self.vars):
                self.set2[name] = long(l[i+1])

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_rpcd
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'rpc server'
        self.nick = ('call', 'erca', 'erau', 'ercl', 'xdrc')
        self.vars = ('calls', 'badcalls', 'badauth', 'badclnt', 'xdrcall')
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.open('/proc/net/rpc/nfsd')

    def extract(self):
        for l in self.splitlines():
            if not l or l[0] != 'rpc': continue
            for i, name in enumerate(self.vars):
                self.set2[name] = long(l[i+1])

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_sendmail
### Author: Dag Wieers <dag@wieers.com>

### FIXME: Should read /var/log/mail/statistics or /etc/mail/statistics (format ?)

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'sendmail'
        self.vars = ('queue',)
        self.type = 'd'
        self.width = 4
        self.scale = 100

    def check(self):
        if not os.access('/var/spool/mqueue', os.R_OK):
            raise Exception, 'Cannot access sendmail queue'

    def extract(self):
        self.val['queue'] = len(glob.glob('/var/spool/mqueue/qf*'))

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_snmp_cpu
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'total cpu'
        self.vars = ( 'usr', 'sys', 'idl' )
        self.type = 'p'
        self.width = 3
        self.scale = 34
        self.server = os.getenv('DSTAT_SNMPSERVER') or '192.168.1.1'
        self.community = os.getenv('DSTAT_SNMPCOMMUNITY') or 'public'

    def check(self):
        try:
            global cmdgen
            from pysnmp.entity.rfc3413.oneliner import cmdgen
        except:
            raise Exception, 'Needs pysnmp and pyasn1 modules'

    def extract(self):
        self.set2['usr'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,11,50,0)))
        self.set2['sys'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,11,52,0)))
        self.set2['idl'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,11,53,0)))
#        self.set2['usr'] = int(snmpget(self.server, self.community, (('UCD-SNMP-MIB', 'ssCpuRawUser'), 0)))
#        self.set2['sys'] = int(snmpget(self.server, self.community, (('UCD-SNMP-MIB', 'ssCpuRawSystem'), 0)))
#        self.set2['idl'] = int(snmpget(self.server, self.community, (('UCD-SNMP-MIB', 'ssCpuRawIdle'), 0)))

        if update:
            for name in self.vars:
                if sum(self.set2.values()) > sum(self.set1.values()):
                    self.val[name] = 100.0 * (self.set2[name] - self.set1[name]) / (sum(self.set2.values()) - sum(self.set1.values()))
                else:
                    self.val[name] = 0

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_snmp_load
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'load avg'
        self.nick = ('1m', '5m', '15m')
        self.vars = ('load1', 'load5', 'load15')
        self.type = 'f'
        self.width = 4
        self.scale = 0.5
        self.server = os.getenv('DSTAT_SNMPSERVER') or '192.168.1.1'
        self.community = os.getenv('DSTAT_SNMPCOMMUNITY') or 'public'

    def check(self):
        try:
            global cmdgen
            from pysnmp.entity.rfc3413.oneliner import cmdgen
        except:
            raise Exception, 'Needs pysnmp and pyasn1 modules'

    def extract(self):
        map(lambda x, y: self.val.update({x: float(y)}), self.vars, snmpwalk(self.server, self.community, (1,3,6,1,4,1,2021,10,1,3)))

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_snmp_mem
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'memory usage'
        self.nick = ('used', 'buff', 'cach', 'free')
        self.vars = ('MemUsed', 'Buffers', 'Cached', 'MemFree')
        self.server = os.getenv('DSTAT_SNMPSERVER') or '192.168.1.1'
        self.community = os.getenv('DSTAT_SNMPCOMMUNITY') or 'public'

    def check(self):
        try:
            global cmdgen
            from pysnmp.entity.rfc3413.oneliner import cmdgen
        except:
            raise Exception, 'Needs pysnmp and pyasn1 modules'

    def extract(self):
        self.val['MemTotal'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,4,5,0))) * 1024
        self.val['MemFree'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,4,11,0))) * 1024
#        self.val['Shared'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,4,13,0))) * 1024
        self.val['Buffers'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,4,14,0))) * 1024
        self.val['Cached'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,4,15,0))) * 1024

        self.val['MemUsed'] = self.val['MemTotal'] - self.val['MemFree']

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_snmp_net
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    def __init__(self):
        self.nick = ('recv', 'send')
        self.type = 'b'
        self.cols = 2
        self.server = os.getenv('DSTAT_SNMPSERVER') or '192.168.1.1'
        self.community = os.getenv('DSTAT_SNMPCOMMUNITY') or 'public'

    def check(self):
        try:
            global cmdgen
            from pysnmp.entity.rfc3413.oneliner import cmdgen
        except:
            raise Exception, 'Needs pysnmp and pyasn1 modules'

    def name(self):
        return self.vars

    def vars(self):
        return [ str(x) for x in snmpwalk(self.server, self.community, (1,3,6,1,2,1,2,2,1,2)) ]

    def extract(self):
        map(lambda x, y, z: self.set2.update({x: (int(y), int(z))}), self.vars, snmpwalk(self.server, self.community, (1,3,6,1,2,1,2,2,1,10)), snmpwalk(self.server, self.community, (1,3,6,1,2,1,2,2,1,16)))

        if update:
            for name in self.set2.keys():
                self.val[name] = map(lambda x, y: (y - x) * 1.0 / elapsed, self.set1[name], self.set2[name])

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_snmp_net_err
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    def __init__(self):
        self.nick = ('error', )
        self.type = 'b'
        self.cols = 1
        self.server = os.getenv('DSTAT_SNMPSERVER') or '192.168.1.1'
        self.community = os.getenv('DSTAT_SNMPCOMMUNITY') or 'public'

    def check(self):
        try:
            global cmdgen
            from pysnmp.entity.rfc3413.oneliner import cmdgen
        except:
            raise Exception, 'Needs pysnmp and pyasn1 modules'

    def name(self):
        return self.vars

    def vars(self):
        return [ str(x) for x in snmpwalk(self.server, self.community, (1,3,6,1,2,1,2,2,1,2)) ]

    def extract(self):
        map(lambda x, y: self.set2.update({x: (int(y), )}), self.vars, snmpwalk(self.server, self.community, (1,3,6,1,2,1,2,2,1,20)))

        if update:
            for name in self.set2.keys():
#                self.val[name] = map(lambda x, y: (y - x) * 1.0 / elapsed, self.set1[name], self.set2[name])
                self.val[name] = map(lambda x, y: (y - x) * 1.0, self.set1[name], self.set2[name])

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_snmp_sys
### Author: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'system'
        self.nick = ('int', 'csw')
        self.vars = ('intr', 'ctxt')
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.server = os.getenv('DSTAT_SNMPSERVER') or '192.168.1.1'
        self.community = os.getenv('DSTAT_SNMPCOMMUNITY') or 'public'

    def check(self):
        try:
            global cmdgen
            from pysnmp.entity.rfc3413.oneliner import cmdgen
        except:
            raise Exception, 'Needs pysnmp and pyasn1 modules'

    def extract(self):
        self.set2['intr'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,11,59,0)))
        self.set2['ctxt'] = int(snmpget(self.server, self.community, (1,3,6,1,4,1,2021,11,60,0)))

        if update:
            for name in self.vars:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_snooze
class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'snooze'
        self.vars = ('snooze',)
        self.type = 's'
        self.width = 6
        self.scale = 0
        self.before = time.time()

    def extract(self):
        now = time.time()
        if loop != 0:
            self.val['snooze'] = now - self.before
        else:
            self.val['snooze'] = self.before
        if step == op.delay:
            self.before = now

    def show(self):
        if self.val['snooze'] > step + 1:
            return ansi['default'] + '     -'

        if op.blackonwhite:
            textcolor = 'black'
            if step != op.delay:
                textcolor = 'darkgray'
        else:
            textcolor = 'white'
            if step != op.delay:
                textcolor = 'gray'

        snoze, c = fchg(self.val['snooze'], 6, 1000)

        return color[textcolor] + snoze

########NEW FILE########
__FILENAME__ = dstat_squid
### Authority: Jason Friedland <thesuperjason@gmail.com>

# This plugin has been tested with:
# - Dstat 0.6.7
# - CentOS release 5.4 (Final)
# - Python 2.4.3
# - Squid 2.6 and 2.7
 
global squidclient_options
squidclient_options = os.getenv('DSTAT_SQUID_OPTS') # -p 8080
 
class dstat_plugin(dstat):
    '''
    Provides various Squid statistics.
    '''
    def __init__(self):
        self.name = 'squid status'
        self.type = 's'
        self.width = 5
        self.scale = 1000
        self.vars = ('Number of file desc currently in use',
            'CPU Usage, 5 minute avg',
            'Total accounted',
            'Number of clients accessing cache',
            'Mean Object Size')
        self.nick = ('fdesc',
            'cpu5',
            'mem',
            'clnts',
            'objsz')

    def check(self):
        if not os.access('/usr/sbin/squidclient', os.X_OK):
            raise Exception, 'Needs squidclient binary'
        cmd_test('/usr/sbin/squidclient %s mgr:info' % squidclient_options)
        return True
 
    def extract(self):
        try:
            for l in cmd_splitlines('/usr/sbin/squidclient %s mgr:info' % squidclient_options, ':'):
                if l[0].strip() in self.vars:
                    self.val[l[0].strip()] = l[1].strip()
                    break
        except IOError, e:
            if op.debug > 1: print '%s: lost pipe to squidclient, %s' % (self.filename, e)
            for name in self.vars: self.val[name] = -1
        except Exception, e:
            if op.debug > 1: print '%s: exception' (self.filename, e)
            for name in self.vars: self.val[name] = -1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_test
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    '''
    Provides a test playground to test syntax and structure.
    '''
    def __init__(self):
        self.name = 'test'
        self.nick = ( 'f1', 'f2' )
        self.vars = ( 'f1', 'f2' )
#        self.type = 'd'
#        self.width = 4
#        self.scale = 20
        self.type = 's'
        self.width = 4
        self.scale = 0

    def extract(self):
#        Self.val = { 'f1': -1, 'f2': -1 }
        self.val = { 'f1': 'test', 'f2': 'test' }

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_thermal
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'thermal'
        self.type = 'd'
        self.width = 3
        self.scale = 20

        if os.path.exists('/sys/bus/acpi/devices/LNXTHERM:01/thermal_zone/'):
            self.vars = os.listdir('/sys/bus/acpi/devices/LNXTHERM:01/thermal_zone/')
            self.nick = []
            for name in self.vars:
                self.nick.append(name.lower())

        elif os.path.exists('/proc/acpi/ibm/thermal'):
            self.namelist = ['cpu', 'pci', 'hdd', 'cpu', 'ba0', 'unk', 'ba1', 'unk']
            self.nick = []
            for line in dopen('/proc/acpi/ibm/thermal'):
                l = line.split()
                for i, name in enumerate(self.namelist):
                    if int(l[i+1]) > 0:
                        self.nick.append(name)
            self.vars = self.nick

        elif os.path.exists('/proc/acpi/thermal_zone/'):
            self.vars = os.listdir('/proc/acpi/thermal_zone/')
#           self.nick = [name.lower() for name in self.vars]
            self.nick = []
            for name in self.vars:
                self.nick.append(name.lower())

        else:
            raise Exception, 'Needs kernel ACPI or IBM-ACPI support'

    def check(self):
        if not os.path.exists('/proc/acpi/ibm/thermal') and \
           not os.path.exists('/proc/acpi/thermal_zone/') and \
           not os.path.exists('/sys/bus/acpi/devices/LNXTHERM:00/thermal_zone/'):
            raise Exception, 'Needs kernel ACPI or IBM-ACPI support'

    def extract(self):
        if os.path.exists('/sys/bus/acpi/devices/LNXTHERM:01/thermal_zone/'):
            for zone in self.vars:
                if os.path.isdir('/sys/bus/acpi/devices/LNXTHERM:01/thermal_zone/'+zone) == False:
                    for line in dopen('/sys/bus/acpi/devices/LNXTHERM:01/thermal_zone/'+zone).readlines():
                        l = line.split()
                        if l[0].isdigit() == True:
                            self.val[zone] = int(l[0])
                        else:
                            self.val[zone] = 0
        elif os.path.exists('/proc/acpi/ibm/thermal'):
            for line in dopen('/proc/acpi/ibm/thermal'):
                l = line.split()
                for i, name in enumerate(self.namelist):
                    if int(l[i+1]) > 0:
                        self.val[name] = int(l[i+1])
        elif os.path.exists('/proc/acpi/thermal_zone/'):
            for zone in self.vars:
                for line in dopen('/proc/acpi/thermal_zone/'+zone+'/temperature').readlines():
                    l = line.split()
                    self.val[zone] = int(l[1])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_bio
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    """
    Top most expensive block I/O process.

    Displays the name of the most expensive block I/O process.
    """
    def __init__(self):
        self.name = 'most expensive'
        self.vars = ('block i/o process',)
        self.type = 's'
        self.width = 22
        self.scale = 0
        self.pidset1 = {}

    def check(self):
        if not os.access('/proc/self/io', os.R_OK):
            raise Exception, 'Kernel has no per-process I/O accounting [CONFIG_TASK_IO_ACCOUNTING], use at least 2.6.20'

    def extract(self):
        self.output = ''
        self.pidset2 = {}
        self.val['usage'] = 0.0
        for pid in proc_pidlist():
            try:
                ### Reset values
                if not self.pidset2.has_key(pid):
                    self.pidset2[pid] = {'read_bytes:': 0, 'write_bytes:': 0}
                if not self.pidset1.has_key(pid):
                    self.pidset1[pid] = {'read_bytes:': 0, 'write_bytes:': 0}

                ### Extract name
                name = proc_splitline('/proc/%s/stat' % pid)[1][1:-1]

                ### Extract counters
                for l in proc_splitlines('/proc/%s/io' % pid):
                    if len(l) != 2: continue
                    self.pidset2[pid][l[0]] = int(l[1])
            except IOError:
                continue
            except IndexError:
                continue

            read_usage = (self.pidset2[pid]['read_bytes:'] - self.pidset1[pid]['read_bytes:']) * 1.0 / elapsed
            write_usage = (self.pidset2[pid]['write_bytes:'] - self.pidset1[pid]['write_bytes:']) * 1.0 / elapsed
            usage = read_usage + write_usage

            ### Get the process that spends the most jiffies
            if usage > self.val['usage']:
                self.val['usage'] = usage
                self.val['read_usage'] = read_usage
                self.val['write_usage'] = write_usage
                self.val['pid'] = pid
                self.val['name'] = getnamebypid(pid, name)
#                st = os.stat("/proc/%s" % pid)

        if step == op.delay:
            self.pidset1 = self.pidset2

        if self.val['usage'] != 0.0:
            self.output = '%-*s%s %s' % (self.width-11, self.val['name'][0:self.width-11], cprint(self.val['read_usage'], 'd', 5, 1024), cprint(self.val['write_usage'], 'd', 5, 1024))

        ### Debug (show PID)
#        self.output = '%*s %-*s%s %s' % (5, self.val['pid'], self.width-17, self.val['name'][0:self.width-17], cprint(self.val['read_usage'], 'd', 5, 1024), cprint(self.val['write_usage'], 'd', 5, 1024))

    def showcsv(self):
        return '%s / %d:%d' % (self.val['name'], self.val['read_usage'], self.val['write_usage'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_bio_adv
### Dstat all I/O process plugin
### Displays all processes' I/O read/write stats and CPU usage
###
### Authority: Guillermo Cantu Luna

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'most expensive block i/o process'
        self.vars = ('process              pid  read write cpu',)
        self.type = 's'
        self.width = 40
        self.scale = 0
        self.pidset1 = {}

    def check(self):
        if not os.access('/proc/self/io', os.R_OK):
            raise Exception, 'Kernel has no per-process I/O accounting [CONFIG_TASK_IO_ACCOUNTING], use at least 2.6.20'
        return True

    def extract(self):
        self.output = ''
        self.pidset2 = {}
        self.val['usage'] = 0.0
        for pid in proc_pidlist():
            try:
                ### Reset values
                if not self.pidset2.has_key(pid):
                    self.pidset2[pid] = {'read_bytes:': 0, 'write_bytes:': 0, 'cputime:': 0, 'cpuper:': 0}
                if not self.pidset1.has_key(pid):
                    self.pidset1[pid] = {'read_bytes:': 0, 'write_bytes:': 0, 'cputime:': 0, 'cpuper:': 0}

                ### Extract name
                name = proc_splitline('/proc/%s/stat' % pid)[1][1:-1]

                ### Extract counters
                for l in proc_splitlines('/proc/%s/io' % pid):
                    if len(l) != 2: continue
                    self.pidset2[pid][l[0]] = int(l[1])

                ### Get CPU usage
                l = proc_splitline('/proc/%s/stat' % pid)
                if len(l) < 15:
                    cpu_usage = 0
                else:
                    self.pidset2[pid]['cputime:'] = int(l[13]) + int(l[14])
                    cpu_usage = (self.pidset2[pid]['cputime:'] - self.pidset1[pid]['cputime:']) * 1.0 / elapsed / cpunr

            except ValueError:
                continue
            except IOError:
                continue
            except IndexError:
                continue

            read_usage = (self.pidset2[pid]['read_bytes:'] - self.pidset1[pid]['read_bytes:']) * 1.0 / elapsed
            write_usage = (self.pidset2[pid]['write_bytes:'] - self.pidset1[pid]['write_bytes:']) * 1.0 / elapsed
            usage = read_usage + write_usage

            ### Get the process that spends the most jiffies
            if usage > self.val['usage']:
                self.val['usage'] = usage
                self.val['read_usage'] = read_usage
                self.val['write_usage'] = write_usage
                self.val['pid'] = pid
                self.val['name'] = getnamebypid(pid, name)
                self.val['cpu_usage'] = cpu_usage

        if step == op.delay:
            self.pidset1 = self.pidset2

        if self.val['usage'] != 0.0:
            self.output = '%-*s%s%-5s%s%s%s%s%%' % (self.width-14-len(pid), self.val['name'][0:self.width-14-len(pid)], color['darkblue'], self.val['pid'], cprint(self.val['read_usage'], 'd', 5, 1024), cprint(self.val['write_usage'], 'd', 5, 1024), cprint(self.val['cpu_usage'], 'f', 3, 34), color['darkgray'])

    def showcsv(self):
        return 'Top: %s\t%s\t%s\t%s' % (self.val['name'][0:self.width-20], self.val['read_usage'], self.val['write_usage'], self.val['cpu_usage'])

########NEW FILE########
__FILENAME__ = dstat_top_childwait
### Dstat most expensive process plugin
### Displays the name of the most expensive process
###
### Authority: dag@wieers.com

global cpunr

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'most waiting for'
        self.vars = ('child process',)
        self.type = 's'
        self.width = 16
        self.scale = 0

    def extract(self):
        self.set2 = {}
        self.val['max'] = 0.0
        for pid in proc_pidlist():
            try:
                ### Using dopen() will cause too many open files
                l = proc_splitline('/proc/%s/stat' % pid)
            except IOError:
                continue

            if len(l) < 15: continue

            ### Reset previous value if it doesn't exist
            if not self.set1.has_key(pid):
                self.set1[pid] = 0

            self.set2[pid] = int(l[15]) + int(l[16])
            usage = (self.set2[pid] - self.set1[pid]) * 1.0 / elapsed / cpunr

            ### Is it a new topper ?
            if usage <= self.val['max']: continue

            self.val['max'] = usage
            self.val['name'] = getnamebypid(pid, l[1][1:-1])
            self.val['pid'] = pid

        ### Debug (show PID)
#       self.val['process'] = '%*s %-*s' % (5, self.val['pid'], self.width-6, self.val['name'])

        if step == op.delay:
            self.set1 = self.set2

    def show(self):
        if self.val['max'] == 0.0:
            return '%-*s' % (self.width, '')
        else:
            return '%s%-*s%s' % (theme['default'], self.width-3, self.val['name'][0:self.width-3], cprint(self.val['max'], 'p', 3, 34))

    def showcsv(self):
        return '%s / %d%%' % (self.val['name'], self.val['max'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_cpu
### Authority: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    """
    Most expensive CPU process.

    Displays the process that uses the CPU the most during the monitored
    interval. The value displayed is the percentage of CPU time for the total
    amount of CPU processing power. Based on per process CPU information.
    """
    def __init__(self):
        self.name = 'most expensive'
        self.vars = ('cpu process',)
        self.type = 's'
        self.width = 16
        self.scale = 0
        self.pidset1 = {}

    def extract(self):
        self.output = ''
        self.pidset2 = {}
        self.val['max'] = 0.0
        for pid in proc_pidlist():
            try:
                ### Using dopen() will cause too many open files
                l = proc_splitline('/proc/%s/stat' % pid)
            except IOError:
                continue

            if len(l) < 15: continue

            ### Reset previous value if it doesn't exist
            if not self.pidset1.has_key(pid):
                self.pidset1[pid] = 0

            self.pidset2[pid] = long(l[13]) + long(l[14])
            usage = (self.pidset2[pid] - self.pidset1[pid]) * 1.0 / elapsed / cpunr

            ### Is it a new topper ?
            if usage < self.val['max']: continue

            name = l[1][1:-1]

            self.val['max'] = usage
            self.val['pid'] = pid
            self.val['name'] = getnamebypid(pid, name)
#            self.val['name'] = name

        if self.val['max'] != 0.0:
            self.output = '%-*s%s' % (self.width-3, self.val['name'][0:self.width-3], cprint(self.val['max'], 'f', 3, 34))

        ### Debug (show PID)
#        self.output = '%*s %-*s' % (5, self.val['pid'], self.width-6, self.val['name'])

        if step == op.delay:
            self.pidset1 = self.pidset2

    def showcsv(self):
        return '%s / %d%%' % (self.val['name'], self.val['max'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_cputime
### Authority: dag@wieers.com

### For more information, see:
###     http://eaglet.rain.com/rick/linux/schedstat/

class dstat_plugin(dstat):
    """
    Name and total amount of CPU time consumed in milliseconds of the process
    that has the highest total amount of cputime for the measured timeframe.

    On a system with one CPU and one core, the total cputime is 1000ms. On a
    system with two cores the total cputime is 2000ms.
    """

    def __init__(self):
        self.name = 'highest total'
        self.vars = ('cputime process',)
        self.type = 's'
        self.width = 17
        self.scale = 0
        self.pidset1 = {}

    def check(self):
        if not os.access('/proc/self/schedstat', os.R_OK):
            raise Exception, 'Kernel has no scheduler statistics [CONFIG_SCHEDSTATS], use at least 2.6.12'

    def extract(self):
        self.output = ''
        self.pidset2 = {}
        self.val['result'] = 0
        for pid in proc_pidlist():
            try:
                ### Reset values
                if not self.pidset1.has_key(pid):
                    self.pidset1[pid] = {'run_ticks': 0}

                ### Extract name
                name = proc_splitline('/proc/%s/stat' % pid)[1][1:-1]

                ### Extract counters
                l = proc_splitline('/proc/%s/schedstat' % pid)
            except IOError:
                continue
            except IndexError:
                continue

            if len(l) != 3: continue

            self.pidset2[pid] = {'run_ticks': long(l[0])}

            totrun = (self.pidset2[pid]['run_ticks'] - self.pidset1[pid]['run_ticks']) * 1.0 / elapsed

            ### Get the process that spends the most jiffies
            if totrun > self.val['result']:
                self.val['result'] = totrun
                self.val['pid'] = pid
                self.val['name'] = getnamebypid(pid, name)

        if step == op.delay:
            self.pidset1 = self.pidset2

        if self.val['result'] != 0.0:
            self.output = '%-*s%s' % (self.width-4, self.val['name'][0:self.width-4], cprint(self.val['result'], 'd', 4, 100))

        ### Debug (show PID)
#       self.output = '%*s %-*s' % (5, self.val['pid'], self.width-6, self.val['name'])

    def showcsv(self):
        return '%s / %.4f' % (self.val['name'], self.val['result'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_cputime_avg
### Authority: dag@wieers.com

### For more information, see:
###     http://eaglet.rain.com/rick/linux/schedstat/

class dstat_plugin(dstat):
    """
    Name and average amount of CPU time consumed in milliseconds of the process
    that has the highest average amount of cputime for the different slices for
    the measured timeframe.

    On a system with one CPU and one core, the total cputime is 1000ms. On a
    system with two cores the total cputime is 2000ms.
    """

    def __init__(self):
        self.name = 'highest average'
        self.vars = ('cputime process',)
        self.type = 's'
        self.width = 17
        self.scale = 0
        self.pidset1 = {}

    def check(self):
        if not os.access('/proc/self/schedstat', os.R_OK):
            raise Exception, 'Kernel has no scheduler statistics [CONFIG_SCHEDSTATS], use at least 2.6.12'

    def extract(self):
        self.output = ''
        self.pidset2 = {}
        self.val['result'] = 0
        for pid in proc_pidlist():
            try:
                ### Reset values
                if not self.pidset1.has_key(pid):
                    self.pidset1[pid] = {'run_ticks': 0, 'ran': 0}

                ### Extract name
                name = proc_splitline('/proc/%s/stat' % pid)[1][1:-1]

                ### Extract counters
                l = proc_splitline('/proc/%s/schedstat' % pid)
            except IOError:
                continue
            except IndexError:
                continue

            if len(l) != 3: continue

            self.pidset2[pid] = {'run_ticks': long(l[0]), 'ran': long(l[2])}

            if self.pidset2[pid]['ran'] - self.pidset1[pid]['ran'] > 0:
                avgrun = (self.pidset2[pid]['run_ticks'] - self.pidset1[pid]['run_ticks']) * 1.0 / (self.pidset2[pid]['ran'] - self.pidset1[pid]['ran']) / elapsed
            else:
                avgrun = 0

            ### Get the process that spends the most jiffies
            if avgrun > self.val['result']:
                self.val['result'] = avgrun
                self.val['pid'] = pid
                self.val['name'] = getnamebypid(pid, name)

        if step == op.delay:
            self.pidset1 = self.pidset2

        if self.val['result'] != 0.0:
            self.output = '%-*s%s' % (self.width-4, self.val['name'][0:self.width-4], cprint(self.val['result'], 'f', 4, 100))

        ### Debug (show PID)
#       self.output = '%*s %-*s' % (5, self.val['pid'], self.width-6, self.val['name'])

    def showcsv(self):
        return '%s / %.4f' % (self.val['name'], self.val['result'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_cpu_adv
### Dstat all I/O process plugin
### Displays all processes' I/O read/write stats and CPU usage
###
### Authority: Guillermo Cantu Luna

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'most expensive cpu process'
        self.vars = ('process              pid  cpu read write',)
        self.type = 's'
        self.width = 40
        self.scale = 0
        self.pidset1 = {}

    def check(self):
        if not os.access('/proc/self/io', os.R_OK):
            raise Exception, 'Kernel has no per-process I/O accounting [CONFIG_TASK_IO_ACCOUNTING], use at least 2.6.20'
        return True

    def extract(self):
        self.output = ''
        self.pidset2 = {}
        self.val['cpu_usage'] = 0
        for pid in proc_pidlist():
            try:
                ### Reset values
                if not self.pidset2.has_key(pid):
                    self.pidset2[pid] = {'rchar:': 0, 'wchar:': 0, 'cputime:': 0, 'cpuper:': 0}
                if not self.pidset1.has_key(pid):
                    self.pidset1[pid] = {'rchar:': 0, 'wchar:': 0, 'cputime:': 0, 'cpuper:': 0}

                ### Extract name
                name = proc_splitline('/proc/%s/stat' % pid)[1][1:-1]

                ### Extract counters
                for l in proc_splitlines('/proc/%s/io' % pid):
                    if len(l) != 2: continue
                    self.pidset2[pid][l[0]] = int(l[1])

                ### Get CPU usage
                l = proc_splitline('/proc/%s/stat' % pid)
                if len(l) < 15:
                    cpu_usage = 0.0
                else:
                    self.pidset2[pid]['cputime:'] = int(l[13]) + int(l[14])
                    cpu_usage = (self.pidset2[pid]['cputime:'] - self.pidset1[pid]['cputime:']) * 1.0 / elapsed / cpunr

            except ValueError:
                continue
            except IOError:
                continue
            except IndexError:
                continue

            read_usage = (self.pidset2[pid]['rchar:'] - self.pidset1[pid]['rchar:']) * 1.0 / elapsed
            write_usage = (self.pidset2[pid]['wchar:'] - self.pidset1[pid]['wchar:']) * 1.0 / elapsed

            ### Get the process that spends the most jiffies
            if cpu_usage > self.val['cpu_usage']:
                self.val['read_usage'] = read_usage
                self.val['write_usage'] = write_usage
                self.val['pid'] = pid
                self.val['name'] = getnamebypid(pid, name)
                self.val['cpu_usage'] = cpu_usage

        if step == op.delay:
            self.pidset1 = self.pidset2

        if self.val['cpu_usage'] != 0.0:
            self.output = '%-*s%s%-5s%s%s%%%s%s' % (self.width-14-len(pid), self.val['name'][0:self.width-14-len(pid)], color['darkblue'], self.val['pid'], cprint(self.val['cpu_usage'], 'f', 3, 34), color['darkgray'],cprint(self.val['read_usage'], 'd', 5, 1024), cprint(self.val['write_usage'], 'd', 5, 1024))


    def showcsv(self):
        return 'Top: %s\t%s\t%s\t%s' % (self.val['name'][0:self.width-20], self.val['cpu_usage'], self.val['read_usage'], self.val['write_usage'])

########NEW FILE########
__FILENAME__ = dstat_top_int
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    """
    Top interrupt

    Displays the name of the most frequent interrupt
    """
    def __init__(self):
        self.name = 'most frequent'
        self.vars = ('interrupt',)
        self.type = 's'
        self.width = 20
        self.scale = 0
        self.intset1 = [ 0 ] * 1024
        self.open('/proc/stat')
        self.names = self.names()

    def names(self):
        ret = {}
        for line in dopen('/proc/interrupts'):
            l = line.split()
            if len(l) <= cpunr: continue
            l1 = l[0].split(':')[0]
            ### Cleanup possible names from /proc/interrupts
            l2 = ' '.join(l[cpunr+2:])
            l2 = l2.replace('_hcd:', '/')
            l2 = re.sub('@pci[:\d+\.]+', '', l2)
            ret[l1] = l2
        return ret

    def extract(self):
        self.output = ''
        self.val['total'] = 0.0
        for line in self.splitlines():
            if line[0] == 'intr':
                self.intset2 = [ long(int) for int in line[3:] ]

        for i in range(len(self.intset2)):
            total = (self.intset2[i] - self.intset1[i]) * 1.0 / elapsed

            ### Put the highest value in self.val
            if total > self.val['total']:
                if str(i+1) in self.names.keys():
                    self.val['name'] = self.names[str(i+1)]
                else:
                    self.val['name'] = 'int ' + str(i+1)
                self.val['total'] = total

        if step == op.delay:
            self.intset1 = self.intset2

        if self.val['total'] != 0.0:
            self.output = '%-15s%s' % (self.val['name'], cprint(self.val['total'], 'd', 5, 1000))

    def showcsv(self):
        return '%s / %f' % (self.val['name'], self.val['total'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_io
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    """
    Top most expensive I/O process

    Displays the name of the most expensive I/O process
    """
    def __init__(self):
        self.name = 'most expensive'
        self.vars = ('i/o process',)
        self.type = 's'
        self.width = 22
        self.scale = 0
        self.pidset1 = {}

    def check(self):
        if not os.access('/proc/self/io', os.R_OK):
            raise Exception, 'Kernel has no per-process I/O accounting [CONFIG_TASK_IO_ACCOUNTING], use at least 2.6.20'

    def extract(self):
        self.output = ''
        self.pidset2 = {}
        self.val['usage'] = 0.0
        for pid in proc_pidlist():
            try:
                ### Reset values
                if not self.pidset2.has_key(pid):
                    self.pidset2[pid] = {'rchar:': 0, 'wchar:': 0}
                if not self.pidset1.has_key(pid):
                    self.pidset1[pid] = {'rchar:': 0, 'wchar:': 0}

                ### Extract name
                name = proc_splitline('/proc/%s/stat' % pid)[1][1:-1]

                ### Extract counters
                for l in proc_splitlines('/proc/%s/io' % pid):
                    if len(l) != 2: continue
                    self.pidset2[pid][l[0]] = int(l[1])
            except IOError:
                continue
            except IndexError:
                continue

            read_usage = (self.pidset2[pid]['rchar:'] - self.pidset1[pid]['rchar:']) * 1.0 / elapsed
            write_usage = (self.pidset2[pid]['wchar:'] - self.pidset1[pid]['wchar:']) * 1.0 / elapsed
            usage = read_usage + write_usage
#            if usage > 0.0:
#                print '%s %s:%s' % (pid, read_usage, write_usage)

            ### Get the process that spends the most jiffies
            if usage > self.val['usage']:
                self.val['usage'] = usage
                self.val['read_usage'] = read_usage
                self.val['write_usage'] = write_usage
                self.val['pid'] = pid
                self.val['name'] = getnamebypid(pid, name)

        if step == op.delay:
            self.pidset1 = self.pidset2

        if self.val['usage'] != 0.0:
            self.output = '%-*s%s %s' % (self.width-11, self.val['name'][0:self.width-11], cprint(self.val['read_usage'], 'd', 5, 1024), cprint(self.val['write_usage'], 'd', 5, 1024))

        ### Debug (show PID)
#        self.output = '%*s %-*s%s %s' % (5, self.val['pid'], self.width-17, self.val['name'][0:self.width-17], cprint(self.val['read_usage'], 'd', 5, 1024), cprint(self.val['write_usage'], 'd', 5, 1024))

    def showcsv(self):
        return '%s / %d:%d' % (self.val['name'], self.val['read_usage'], self.val['write_usage'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_io_adv
### Dstat all I/O process plugin
### Displays all processes' I/O read/write stats and CPU usage
###
### Authority: Guillermo Cantu Luna

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'most expensive i/o process'
        self.vars = ('process              pid  read write cpu',)
        self.type = 's'
        self.width = 40
        self.scale = 0
        self.pidset1 = {}

    def check(self):
        if not os.access('/proc/self/io', os.R_OK):
            raise Exception, 'Kernel has no per-process I/O accounting [CONFIG_TASK_IO_ACCOUNTING], use at least 2.6.20'
        return True

    def extract(self):
        self.output = ''
        self.pidset2 = {}
        self.val['usage'] = 0.0
        for pid in proc_pidlist():
            try:
                ### Reset values
                if not self.pidset2.has_key(pid):
                    self.pidset2[pid] = {'rchar:': 0, 'wchar:': 0, 'cputime:': 0, 'cpuper:': 0}
                if not self.pidset1.has_key(pid):
                    self.pidset1[pid] = {'rchar:': 0, 'wchar:': 0, 'cputime:': 0, 'cpuper:': 0}

                ### Extract name
                name = proc_splitline('/proc/%s/stat' % pid)[1][1:-1]

                ### Extract counters
                for l in proc_splitlines('/proc/%s/io' % pid):
                    if len(l) != 2: continue
                    self.pidset2[pid][l[0]] = int(l[1])

                ### Get CPU usage
                l = proc_splitline('/proc/%s/stat' % pid)
                if len(l) < 15:
                    cpu_usage = 0
                else:
                    self.pidset2[pid]['cputime:'] = int(l[13]) + int(l[14])
                    cpu_usage = (self.pidset2[pid]['cputime:'] - self.pidset1[pid]['cputime:']) * 1.0 / elapsed / cpunr

            except ValueError:
                continue
            except IOError:
                continue
            except IndexError:
                continue

            read_usage = (self.pidset2[pid]['rchar:'] - self.pidset1[pid]['rchar:']) * 1.0 / elapsed
            write_usage = (self.pidset2[pid]['wchar:'] - self.pidset1[pid]['wchar:']) * 1.0 / elapsed
            usage = read_usage + write_usage

            ### Get the process that spends the most jiffies
            if usage > self.val['usage']:
                self.val['usage'] = usage
                self.val['read_usage'] = read_usage
                self.val['write_usage'] = write_usage
                self.val['pid'] = pid
                self.val['name'] = getnamebypid(pid, name)
                self.val['cpu_usage'] = cpu_usage

        if step == op.delay:
            self.pidset1 = self.pidset2

        if self.val['usage'] != 0.0:
            self.output = '%-*s%s%-5s%s%s%s%s%%' % (self.width-14-len(pid), self.val['name'][0:self.width-14-len(pid)], color['darkblue'], self.val['pid'], cprint(self.val['read_usage'], 'd', 5, 1024), cprint(self.val['write_usage'], 'd', 5, 1024), cprint(self.val['cpu_usage'], 'f', 3, 34), color['darkgray'])

    def showcsv(self):
        return 'Top: %s\t%s\t%s\t%s' % (self.val['name'][0:self.width-20], self.val['read_usage'], self.val['write_usage'], self.val['cpu_usage'])

########NEW FILE########
__FILENAME__ = dstat_top_latency
### Authority: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Top process with highest total latency.

    Displays name and total amount of CPU time waited in milliseconds of
    the process that has the highest total amount waited for the measured
    timeframe.

    For more information see:

        http://eaglet.rain.com/rick/linux/schedstat/
    """

    def __init__(self):
        self.name = 'highest total'
        self.vars = ('latency process',)
        self.type = 's'
        self.width = 17
        self.scale = 0
        self.pidset1 = {}

    def check(self):
        if not os.access('/proc/self/schedstat', os.R_OK):
            raise Exception, 'Kernel has no scheduler statistics [CONFIG_SCHEDSTATS], use at least 2.6.12'

    def extract(self):
        self.output = ''
        self.pidset2 = {}
        self.val['result'] = 0
        for pid in proc_pidlist():
            try:
                ### Reset values
                if not self.pidset1.has_key(pid):
                    self.pidset1[pid] = {'wait_ticks': 0}

                ### Extract name
                name = proc_splitline('/proc/%s/stat' % pid)[1][1:-1]

                ### Extract counters
                l = proc_splitline('/proc/%s/schedstat' % pid)
            except IOError:
                continue
            except IndexError:
                continue

            if len(l) != 3: continue

            self.pidset2[pid] = {'wait_ticks': long(l[1])}

            totwait = (self.pidset2[pid]['wait_ticks'] - self.pidset1[pid]['wait_ticks']) * 1.0 / elapsed

            ### Get the process that spends the most jiffies
            if totwait > self.val['result']:
                self.val['result'] = totwait
                self.val['pid'] = pid
                self.val['name'] = getnamebypid(pid, name)

        if step == op.delay:
            self.pidset1 = self.pidset2

        if self.val['result'] != 0.0:
            self.output = '%-*s%s' % (self.width-4, self.val['name'][0:self.width-4], cprint(self.val['result'], 'd', 4, 100))

        ### Debug (show PID)
#       self.output = '%*s %-*s' % (5, self.val['pid'], self.width-6, self.val['name'])

    def showcsv(self):
        return '%s / %.4f' % (self.val['name'], self.val['result'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_latency_avg
### Dstat most expensive I/O process plugin
### Displays the name of the most expensive I/O process
###
### Authority: dag@wieers.com

### For more information, see:
###     http://eaglet.rain.com/rick/linux/schedstat/

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'highest average'
        self.vars = ('latency process',)
        self.type = 's'
        self.width = 17
        self.scale = 0
        self.pidset1 = {}

    def check(self):
        if not os.access('/proc/self/schedstat', os.R_OK):
            raise Exception, 'Kernel has no scheduler statistics [CONFIG_SCHEDSTATS], use at least 2.6.12'

    def extract(self):
        self.output = ''
        self.pidset2 = {}
        self.val['result'] = 0
        for pid in proc_pidlist():
            try:
                ### Reset values
                if not self.pidset1.has_key(pid):
                    self.pidset1[pid] = {'wait_ticks': 0, 'ran': 0}

                ### Extract name
                name = proc_splitline('/proc/%s/stat' % pid)[1][1:-1]

                ### Extract counters
                l = proc_splitline('/proc/%s/schedstat' % pid)
            except IOError:
                continue
            except IndexError:
                continue

            if len(l) != 3: continue

            self.pidset2[pid] = {'wait_ticks': long(l[1]), 'ran': long(l[2])}

            if self.pidset2[pid]['ran'] - self.pidset1[pid]['ran'] > 0:
                avgwait = (self.pidset2[pid]['wait_ticks'] - self.pidset1[pid]['wait_ticks']) * 1.0 / (self.pidset2[pid]['ran'] - self.pidset1[pid]['ran']) / elapsed
            else:
                avgwait = 0

            ### Get the process that spends the most jiffies
            if avgwait > self.val['result']:
                self.val['result'] = avgwait
                self.val['pid'] = pid
                self.val['name'] = getnamebypid(pid, name)

        if step == op.delay:
            self.pidset1 = self.pidset2

        if self.val['result'] != 0.0:
            self.output = '%-*s%s' % (self.width-4, self.val['name'][0:self.width-4], cprint(self.val['result'], 'f', 4, 100))

        ### Debug (show PID)
#       self.output = '%*s %-*s' % (5, self.val['pid'], self.width-6, self.val['name'])

    def showcsv(self):
        return '%s / %.4f' % (self.val['name'], self.val['result'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_mem
### Authority: Dag Wieers <dag$wieers,com>

class dstat_plugin(dstat):
    """
    Most expensive CPU process.

    Displays the process that uses the CPU the most during the monitored
    interval. The value displayed is the percentage of CPU time for the total
    amount of CPU processing power. Based on per process CPU information.
    """
    def __init__(self):
        self.name = 'most expensive'
        self.vars = ('memory process',)
        self.type = 's'
        self.width = 17
        self.scale = 0

    def extract(self):
        self.val['max'] = 0.0
        for pid in proc_pidlist():
            try:
                ### Using dopen() will cause too many open files
                l = proc_splitline('/proc/%s/stat' % pid)
            except IOError:
                continue

            if len(l) < 23: continue
            usage = int(l[23]) * pagesize

            ### Is it a new topper ?
            if usage <= self.val['max']: continue

            self.val['max'] = usage
            self.val['name'] = getnamebypid(pid, l[1][1:-1])
            self.val['pid'] = pid

        self.output = '%-*s%s' % (self.width-5, self.val['name'][0:self.width-5], cprint(self.val['max'], 'f', 5, 1024))

        ### Debug (show PID)
#       self.val['memory process'] = '%*s %-*s' % (5, self.val['pid'], self.width-6, self.val['name'])

    def showcsv(self):
        return '%s / %d%%' % (self.val['name'], self.val['max'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_top_oom
### Author: Dag Wieers <dag@wieers.com>

### Dstat most expensive process plugin
### Displays the name of the most expensive process

### More information:
###    http://lwn.net/Articles/317814/

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'out of memory'
        self.vars = ('kill score',)
        self.type = 's'
        self.width = 18
        self.scale = 0

    def check(self):
        if not os.access('/proc/self/oom_score', os.R_OK):
            raise Exception, 'Kernel does not support /proc/pid/oom_score, use at least 2.6.11.'

    def extract(self):
        self.output = ''
        self.val['max'] = 0.0
        for pid in proc_pidlist():
            try:
                ### Extract name
                name = proc_splitline('/proc/%s/stat' % pid)[1][1:-1]

                ### Using dopen() will cause too many open files
                l = proc_splitline('/proc/%s/oom_score' % pid)
            except IOError:
                continue
            except IndexError:
                continue

            if len(l) < 1: continue
            oom_score = int(l[0])

            ### Is it a new topper ?
            if oom_score <= self.val['max']: continue

            self.val['max'] = oom_score
            self.val['name'] = getnamebypid(pid, name)
            self.val['pid'] = pid

        if self.val['max'] != 0.0:
            self.output = '%-*s%s' % (self.width-4, self.val['name'][0:self.width-4], cprint(self.val['max'], 'f', 4, 1000))

        ### Debug (show PID)
#       self.output = '%*s %-*s' % (5, self.val['pid'], self.width-6, self.val['name'])

    def showcsv(self):
        return '%s / %d%%' % (self.val['name'], self.val['max'])

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_utmp
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'utmp'
        self.nick = ('ses', 'usr', 'adm' )
        self.vars = ('sessions', 'users', 'root')
        self.type = 'd'
        self.width = 3
        self.scale = 10

    def check(self): 
        try:
            global utmp
            import utmp
        except:
            raise Exception, 'Needs python-utmp module'

    def extract(self):
        for name in self.vars: self.val[name] = 0
        for u in utmp.UtmpRecord():
#           print '# type:%s pid:%s line:%s id:%s user:%s host:%s session:%s' % (i.ut_type, i.ut_pid, i.ut_line, i.ut_id, i.ut_user, i.ut_host, i.ut_session)
            if u.ut_type == utmp.USER_PROCESS:
                self.val['users'] = self.val['users'] + 1
                if u.ut_user == 'root':
                    self.val['root'] = self.val['root'] + 1
            self.val['sessions'] = self.val['sessions'] + 1

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_vmk_hba
### Author: Bert de Bruijn <bert+dstat$debruijn,be>

### VMware ESX kernel vmhba stats
### Displays kernel vmhba statistics on VMware ESX servers

# NOTE TO USERS: command-line plugin configuration is not yet possible, so I've
# "borrowed" the -D argument. 
# EXAMPLES:
# # dstat --vmkhba -D vmhba1,vmhba2,total
# # dstat --vmkhba -D vmhba0
# You can even combine the Linux and VMkernel diskstats (but the "total" argument
# will be used by both).
# # dstat --vmkhba -d -D sda,vmhba1

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'vmkhba'
        self.nick = ('read', 'writ')
        self.cols = 2

    def discover(self, *list):
    # discover will list all vmhba's found.
    # we might want to filter out the unused vmhba's (read stats, compare with ['0', ] * 13)
        ret = []
        try:
            list = os.listdir('/proc/vmware/scsi/')
        except:
            raise Exception, 'Needs VMware ESX'
        for name in list:
            for line in dopen('/proc/vmware/scsi/%s/stats' % name).readlines():
                l = line.split()
                if len(l) < 13: continue
                if l[0] == 'cmds': continue
                if l == ['0', ] * 13: continue
                ret.append(name)
        return ret

    def vars(self):
    # vars will take the argument list - when implemented - , use total, or will use discover + total
        ret = []
        if op.disklist:
            list = op.disklist
        #elif not op.full:
        #   list = ('total', )
        else:
            list = self.discover
            list.sort()
        for name in list:
            if name in self.discover + ['total']:
                ret.append(name)
        return ret

    def check(self): 
        try:
            os.listdir('/proc/vmware')
        except:
            raise Exception, 'Needs VMware ESX'
        info(1, 'The vmkhba module is an EXPERIMENTAL module.')

    def extract(self):
        self.set2['total'] = (0, 0)
        for name in self.vars:
            self.set2[name] = (0, 0)
        for name in os.listdir('/proc/vmware/scsi/'):
            for line in dopen('/proc/vmware/scsi/%s/stats' % name).readlines():
                l = line.split()
                if len(l) < 13: continue
                if l[0] == 'cmds': continue
                if l[2] == '0' and l[4] == '0': continue
                if l == ['0', ] * 13: continue
                self.set2['total'] = ( self.set2['total'][0] + long(l[2]), self.set2['total'][1] + long(l[4]) )
                if name in self.vars and name != 'total':
                    self.set2[name] = ( long(l[2]), long(l[4]) )

            for name in self.set2.keys():
                self.val[name] = map(lambda x, y: (y - x) * 1024.0 / elapsed, self.set1[name], self.set2[name])

        if step == op.delay:
            self.set1.update(self.set2)

########NEW FILE########
__FILENAME__ = dstat_vmk_int
### Author: Bert de Bruijn <bert+dstat$debruijn,be>

### VMware ESX kernel interrupt stats
### Displays kernel interrupt statistics on VMware ESX servers

# NOTE TO USERS: command-line plugin configuration is not yet possible, so I've
# "borrowed" the -I argument. 
# EXAMPLES:
# # dstat --vmkint -I 0x46,0x5a
# You can even combine the Linux and VMkernel interrupt stats
# # dstat --vmkint -i -I 14,0x5a
# Look at /proc/vmware/interrupts to see which interrupt is linked to which function

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'vmkint'
        self.type = 'd'
        self.width = 4
        self.scale = 1000
        self.open('/proc/vmware/interrupts')
#       self.intmap = self.intmap()

#   def intmap(self):
#       ret = {}
#       for line in dopen('/proc/vmware/interrupts').readlines():
#           l = line.split()
#           if len(l) <= self.vmkcpunr: continue
#           l1 = l[0].split(':')[0]
#           l2 = ' '.join(l[vmkcpunr()+1:]).split(',')
#           ret[l1] = l1
#           for name in l2:
#               ret[name.strip().lower()] = l1
#           return ret

    def vmkcpunr(self):
        #the service console sees only one CPU, so cpunr == 1, only the vmkernel sees all CPUs
        ret = []
        # default cpu number is 2
        ret = 2
        for l in self.fd[0].splitlines():
            if l[0] == 'Vector': 
                ret = int( int( l[-1] ) + 1 )
        return ret

    def discover(self):
        #interrupt names are not decimal numbers, but rather hexadecimal numbers like 0x7e
        ret = []
        self.fd[0].seek(0)
        for line in self.fd[0].readlines():
            l = line.split()
            if l[0] == 'Vector': continue
            if len(l) < self.vmkcpunr()+1: continue
            name = l[0].split(':')[0]
            amount = 0
            for i in l[1:1+self.vmkcpunr()]:
                amount = amount + long(i)
            if amount > 20: ret.append(str(name))
        return ret

    def vars(self):
        ret = []
        if op.intlist:
            list = op.intlist
        else:
            list = self.discover
#           len(list) > 5: list = list[-5:]
        for name in list:
            if name in self.discover:
                ret.append(name)
#           elif name.lower() in self.intmap.keys():
#               ret.append(self.intmap[name.lower()])
        return ret

    def check(self): 
        try:
            os.listdir('/proc/vmware')
        except:
            raise Exception, 'Needs VMware ESX'
        info(1, 'The vmkint module is an EXPERIMENTAL module.')

    def extract(self):
        self.fd[0].seek(0)
        for line in self.fd[0].readlines():
            l = line.split()
            if len(l) < self.vmkcpunr()+1: continue
            name = l[0].split(':')[0]
            if name in self.vars:
                self.set2[name] = 0
                for i in l[1:1+self.vmkcpunr()]:
                    self.set2[name] = self.set2[name] + long(i)

        for name in self.set2.keys():
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4

########NEW FILE########
__FILENAME__ = dstat_vmk_nic
### Author: Bert de Bruijn <bert+dstat$debruijn,be>

### VMware ESX kernel vmknic stats
### Displays VMkernel port statistics on VMware ESX servers

# NOTE TO USERS: command-line plugin configuration is not yet possible, so I've
# "borrowed" the -N argument.
# EXAMPLES:
# # dstat --vmknic -N vmk1
# You can even combine the Linux and VMkernel network stats (just don't just "total").
# # dstat --vmknic -n -N vmk0,vswif0
# NB Data comes from /proc/vmware/net/tcpip/ifconfig

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'vmknic'
        self.nick = ('recv', 'send')
        self.open('/proc/vmware/net/tcpip/ifconfig')
        self.cols = 2

    def check(self):
        try:
            os.listdir('/proc/vmware')
        except:
            raise Exception, 'Needs VMware ESX'
        info(1, 'The vmknic module is an EXPERIMENTAL module.')

    def discover(self, *list):
        ret = []
        for l in self.fd[0].splitlines(replace=' /', delim='/'):
            if len(l) != 12: continue
            if l[2][:5] == '<Link': continue
            if ','.join(l) == 'Name,Mtu/TSO,Network,Address,Ipkts,Ierrs,Ibytes,Opkts,Oerrs,Obytes,Coll,Time': continue
            if l[0] == 'lo0': continue
            if l[0] == 'Usage:': continue
            ret.append(l[0])
        ret.sort()
        for item in list: ret.append(item)
        return ret

    def vars(self):
        ret = []
        if op.netlist:
            list = op.netlist
        else:
            list = self.discover
            list.sort()
        for name in list:
            if name in self.discover + ['total']:
                ret.append(name)
        return ret

    def name(self):
        return ['net/'+name for name in self.vars]

    def extract(self):
        self.set2['total'] = [0, 0]
        for line in self.fd[0].readlines():
            l = line.replace(' /','/').split()
            if len(l) != 12: continue
            if l[2][:5] == '<Link': continue
            if ','.join(l) == 'Name,Mtu/TSO,Network,Address,Ipkts,Ierrs,Ibytes,Opkts,Oerrs,Obytes,Coll,Time': continue
            if l[0] == 'Usage:': continue
            name = l[0]
            if name in self.vars:
                self.set2[name] = ( long(l[6]), long(l[9]) )
            if name != 'lo0':
                self.set2['total'] = ( self.set2['total'][0] + long(l[6]), self.set2['total'][1] + long(l[9]) )

        if update:
            for name in self.set2.keys():
                self.val[name] = map(lambda x, y: (y - x) * 1.0 / elapsed, self.set1[name], self.set2[name])

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4

########NEW FILE########
__FILENAME__ = dstat_vm_cpu
### Author: Bert de Bruijn <bert+dstat$debruijn,be>

### VMware cpu stats
### Displays CPU stats coming from the hypervisor inside VMware VMs.
### The vmGuestLib API from VMware Tools needs to be installed

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'vm cpu'
        self.vars = ('used', 'stolen', 'elapsed')
        self.nick = ('usd', 'stl')
        self.type = 'p'
        self.width = 3
        self.scale = 100
        self.cpunr = getcpunr()

    def check(self):
        try:
            global vmguestlib
            import vmguestlib

            self.gl = vmguestlib.VMGuestLib()
        except:
            raise Exception, 'Needs python-vmguestlib module'

    def extract(self):
        self.gl.UpdateInfo()
        self.set2['elapsed'] = self.gl.GetElapsedMs()
        self.set2['stolen'] = self.gl.GetCpuStolenMs()
        self.set2['used'] = self.gl.GetCpuUsedMs()

        for name in ('stolen', 'used'):
            self.val[name] = (self.set2[name] - self.set1[name]) * 100 / (self.set2['elapsed'] - self.set1['elapsed']) / self.cpunr

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4
########NEW FILE########
__FILENAME__ = dstat_vm_mem
### Author: Bert de Bruijn <bert+dstat$debruijn,be>

### VMware memory stats
### Displays memory stats coming from the hypervisor inside VMware VMs.
### The vmGuestLib API from VMware Tools needs to be installed

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'vmware memory'
        self.vars = ('active', 'ballooned', 'mapped',  'swapped', 'used')
        self.nick = ('active', 'balln', 'mappd', 'swapd', 'used')
        self.type = 'd'
        self.width = 5
        self.scale = 1024

    def check(self):
        try:
            global vmguestlib
            import vmguestlib

            self.gl = vmguestlib.VMGuestLib()
        except:
            raise Exception, 'Needs python-vmguestlib module'

    def extract(self):
        self.gl.UpdateInfo()
        self.val['active'] = self.gl.GetMemActiveMB() * 1024 ** 2
        self.val['ballooned'] = self.gl.GetMemBalloonedMB() * 1024 ** 2
        self.val['mapped'] = self.gl.GetMemMappedMB() * 1024 ** 2
        self.val['swapped'] = self.gl.GetMemSwappedMB() * 1024 ** 2
        self.val['used'] = self.gl.GetMemUsedMB() * 1024 ** 2

# vim:ts=4:sw=4
########NEW FILE########
__FILENAME__ = dstat_vm_mem_adv
### Author: Bert de Bruijn <bert+dstat$debruijn,be>

### VMware advanced memory stats
### Displays memory stats coming from the hypervisor inside VMware VMs.
### The vmGuestLib API from VMware Tools needs to be installed

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'vmware advanced memory'
        self.vars = ('active', 'ballooned', 'mapped', 'overhead', 'saved', 'shared', 'swapped', 'targetsize', 'used')
        self.nick = ('active', 'balln', 'mappd', 'ovrhd', 'saved', 'shard', 'swapd', 'targt', 'used')
        self.type = 'd'
        self.width = 5
        self.scale = 1024

    def check(self):
        try:
            global vmguestlib
            import vmguestlib

            self.gl = vmguestlib.VMGuestLib()
        except:
            raise Exception, 'Needs python-vmguestlib module'

    def extract(self):
        self.gl.UpdateInfo()
        self.val['active'] = self.gl.GetMemActiveMB() * 1024 ** 2
        self.val['ballooned'] = self.gl.GetMemBalloonedMB() * 1024 ** 2
        self.val['mapped'] = self.gl.GetMemMappedMB() * 1024 ** 2
        self.val['overhead'] = self.gl.GetMemOverheadMB() * 1024 ** 2
        self.val['saved'] = self.gl.GetMemSharedSavedMB() * 1024 ** 2
        self.val['shared'] = self.gl.GetMemSharedMB() * 1024 ** 2
        self.val['swapped'] = self.gl.GetMemSwappedMB() * 1024 ** 2
        self.val['targetsize'] = self.gl.GetMemTargetSizeMB() * 1024 ** 2
        self.val['used'] = self.gl.GetMemUsedMB() * 1024 ** 2

# vim:ts=4:sw=4
########NEW FILE########
__FILENAME__ = dstat_vz_cpu
### Author: Dag Wieers <dag@wieers.com>

#Version: 2.2
#VEID   user    nice    system   uptime     idle             strv   uptime          used           maxlat  totlat  numsched
#302    142926  0       10252    152896388  852779112954062  0      427034187248480 1048603937010  0       0       0
#301    27188   0       7896     152899846  853267000490282  0      427043845492614 701812592320   0       0       0

class dstat_plugin(dstat):
    def __init__(self):
        self.nick = ('usr', 'sys', 'idl', 'nic')
        self.type = 'p'
        self.width = 3
        self.scale = 34
        self.open('/proc/vz/vestat')
        self.cols = 4

    def check(self):
        info(1, 'Module %s is still experimental.' % self.filename)

    def discover(self, *list):
        ret = []
        for l in self.splitlines():
            if len(l) < 6 or l[0] == 'VEID': continue
            ret.append(l[0])
        ret.sort()
        for item in list: ret.append(item)
        return ret

    def name(self):
        ret = []
        for name in self.vars:
            if name == 'total':
                ret.append('total ve usage')
            else:
                ret.append('ve ' + name + ' usage')
        return ret

    def vars(self):
        ret = []
        if not op.full:
            list = ('total', )
        else: 
            list = self.discover
        for name in list: 
            if name in self.discover + ['total']:
                ret.append(name)
        return ret

    def extract(self):
        self.set2['total'] = [0, 0, 0, 0]
        for l in self.splitlines():
            if len(l) < 6 or l[0] == 'VEID': continue
            name = l[0]
            self.set2[name] = ( long(l[1]), long(l[3]), long(l[4]) - long(l[1]) - long(l[2]) - long(l[3]), long(l[2]) )
            self.set2['total'] = ( self.set2['total'][0] + long(l[1]), self.set2['total'][1] + long(l[3]), self.set2['total'][2] + long(l[4]) - long(l[1]) - long(l[2]) - long(l[3]), self.set2['total'][3] + long(l[2]) )

        for name in self.vars:
            for i in range(self.cols):
                self.val[name][i] = 100.0 * (self.set2[name][i] - self.set1[name][i]) / (sum(self.set2[name]) - sum(self.set1[name]))

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_vz_io
### Author: Dag Wieers <dag@wieers.com>

### Example content for /proc/bc/<veid>/ioacct
#       read                         2773011640320
#       write                        2095707136000
#       dirty                        4500342390784
#       cancel                       4080624041984
#       missed                                   0
#       syncs_total                              2
#       fsyncs_total                       1730732
#       fdatasyncs_total                      3266
#       range_syncs_total                        0
#       syncs_active                             0
#       fsyncs_active                            0
#       fdatasyncs_active                        0
#       range_syncs_active                       0
#       vfs_reads                       3717331387
#       vfs_read_chars         3559144863185798078
#       vfs_writes                       901216138
#       vfs_write_chars          23864660931174682
#       io_pbs                                  16

class dstat_plugin(dstat):
    def __init__(self):
        self.nick = ['read', 'write', 'dirty', 'cancel', 'missed']
        self.cols = len(self.nick)

    def check(self):
        if not os.path.exists('/proc/vz'):
            raise Exception, 'System does not have OpenVZ support'
        elif not os.path.exists('/proc/bc'):
            raise Exception, 'System does not have (new) OpenVZ beancounter support'
        elif not glob.glob('/proc/bc/*/ioacct'):
            raise Exception, 'System does not have any OpenVZ containers'
        info(1, 'Module %s is still experimental.' % self.filename)

    def name(self):
        return ['ve/'+name for name in self.vars]

    def vars(self):
        ret = []
        if not op.full:
            varlist = ['total',]
        else:
            varlist = [os.path.basename(veid) for veid in glob.glob('/proc/vz/*')]
        ret = varlist
        return ret

    def extract(self):
        for name in self.vars:
            self.set2['total'] = {}
            for line in dopen('/proc/bc/%s/ioacct' % name).readlines():
                l = line.split()
                if len(l) != 2: continue
                if l[0] not in self.nick: continue
                index = self.nick.index(l[0])
                self.set2[name][index] = long(l[1])
                self.set2['total'][index] = self.set2['total'][index] + long(l[1])
#            print name, self.val[name], self.set2[name][0], self.set2[name][1]
#            print name, self.val[name], self.set1[name][0], self.set1[name][1]

            self.val[name] = map(lambda x, y: (y - x) / elapsed, self.set1[name], self.set2[name])

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_vz_ubc
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.nick = ('fcnt', )
        self.type = 'd'
        self.width = 5
        self.scale = 1000
        self.open('/proc/user_beancounters')
        self.cols = 1 ### Is this correct ?

    def check(self):
        info(1, 'Module %s is still experimental.' % self.filename)

    def discover(self, *list):
        ret = []
        for l in self.splitlines():
            if len(l) < 7 or l[0] in ('uid', '0:'): continue
            ret.append(l[0][0:-1])
        ret.sort()
        for item in list: ret.append(item)
        return ret

    def name(self):
        ret = []
        for name in self.vars:
            if name == 'total':
                ret.append('total failcnt')
            else:
                ret.append(name)
        return ret

    def vars(self):
        ret = []
        if not op.full:
            list = ('total', )
        else: 
            list = self.discover
        for name in list: 
            if name in self.discover + ['total']:
                ret.append(name)
        return ret

    def extract(self):
        for name in self.vars + ['total']:
            self.set2[name] = 0
        for l in self.splitlines():
            if len(l) < 6 or l[0] == 'uid':
                continue
            elif len(l) == 7:
                name = l[0][0:-1]
                if name in self.vars:
                    self.set2[name] = self.set2[name] + long(l[6])
                self.set2['total'] = self.set2['total'] + long(l[6])
            elif name == '0':
                continue
            else:
                if name in self.vars:
                    self.set2[name] = self.set2[name] + long(l[5])
                self.set2['total'] = self.set2['total'] + long(l[5])

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_wifi
### Author: Dag Wieers <dag@wieers.com>

class dstat_plugin(dstat):
    def __init__(self):
        self.name = 'wifi'
        self.nick = ('lnk', 's/n')
        self.type = 'd'
        self.width = 3
        self.scale = 34
        self.cols = 2

    def check(self):
        global iwlibs
        from pythonwifi import iwlibs

    def vars(self):
        return iwlibs.getNICnames()

    def extract(self):
        for name in self.vars:
            wifi = iwlibs.Wireless(name)
            stat, qual, discard, missed_beacon = wifi.getStatistics()
#           print qual.quality, qual.signallevel, qual.noiselevel
            if qual.quality == 0 or qual.signallevel == -101 or qual.noiselevel == -101 or qual.signallevel == -256 or qual.noiselevel == -256:
                self.val[name] = ( -1, -1 )
            else:
                self.val[name] = ( qual.quality, qual.signallevel * 100 / qual.noiselevel )

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_zfs_arc
class dstat_plugin(dstat):
    """
    ZFS on Linux ARC (Adjustable Replacement Cache)

    Data is extracted from /proc/spl/kstat/zfs/arcstats
    """
    def __init__(self):
        self.name = 'ZFS ARC'
        self.nick = ('mem', 'hit', 'miss', 'reads', 'hit%')
        self.vars = ('size', 'hits', 'misses', 'total', 'hit_rate')
        self.types = ('b', 'd', 'd', 'd', 'p')
        self.scales = (1024, 1000, 1000, 1000, 1000)
        self.counter = (False, True, True, False, False)
        self.open('/proc/spl/kstat/zfs/arcstats')

    def extract(self):
        for l in self.splitlines():
            if len(l) < 2: continue
            l[0].split()
            name = l[0]
            if name in self.vars:
                self.set2[name] = long(l[2])

        for i, name in enumerate (self.vars):
            if self.counter[i]:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed
            else:
                self.val[name] = self.set2[name]

        self.val['total'] = self.val['hits'] + self.val['misses']

	if self.val['total'] > 0 :
            self.val['hit_rate'] = self.val['hits'] / self.val['total'] * 100.0
	else:
            self.val['hit_rate'] = 0

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_zfs_l2arc
class dstat_plugin(dstat):
    """
    ZFS on Linux L2ARC (Level 2 Adjustable Replacement Cache)

    Data is extracted from /proc/spl/kstat/zfs/arcstats
    """
    def __init__(self):
        self.name = 'ZFS L2ARC'
        self.nick = ('size', 'hit', 'miss', 'hit%', 'read', 'write')
        self.vars = ('l2_size', 'l2_hits', 'l2_misses', 'hit_rate', 'l2_read_bytes', 'l2_write_bytes')
        self.types = ('b', 'd', 'd', 'p', 'b', 'b')
        self.scales = (1024, 1000, 1000, 1000, 1024, 1024)
        self.counter = (False, True, True, False, True, True)
        self.open('/proc/spl/kstat/zfs/arcstats')

    def extract(self):
        for l in self.splitlines():
            if len(l) < 2: continue
            l[0].split()
            name = l[0]
            if name in self.vars:
                self.set2[name] = long(l[2])

        for i, name in enumerate (self.vars):
            if self.counter[i]:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed
            else:
                self.val[name] = self.set2[name]

        probes = self.val['l2_hits'] + self.val['l2_misses']

	if probes > 0 :
            self.val['hit_rate'] = self.val['l2_hits'] / probes * 100.0
	else:
            self.val['hit_rate'] = 0

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = dstat_zfs_zil
class dstat_plugin(dstat):
    """
    ZFS on Linux ZIL (ZFS Intent Log)

    Data is extracted from /proc/spl/kstat/zfs/zil
    """
    def __init__(self):
        self.name = 'ZFS ZIL'
        self.nick = ('count', 'bytes')
        self.vars = ('zil_itx_metaslab_slog_count', 'zil_itx_metaslab_slog_bytes')
        self.types = ('d', 'b')
        self.scales = (1000, 1024)
        self.counter = (True, True)
        self.open('/proc/spl/kstat/zfs/zil')

    def extract(self):
        for l in self.splitlines():
            if len(l) < 2: continue
            l[0].split()
            name = l[0]
            if name in self.vars:
                self.set2[name] = long(l[2])

        for i, name in enumerate (self.vars):
            if self.counter[i]:
                self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed
            else:
                self.val[name] = self.set2[name]

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et

########NEW FILE########
