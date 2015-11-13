__FILENAME__ = create-aggr-item
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import pyzabbix
import re

def main(args):

    zapi = pyzabbix.ZabbixAPI('http://%s' % args.zabbix_server)
    zapi.login(args.zabbix_username, args.zabbix_password)

    for host in args.host:
        process(zapi, host)

def process(zapi, host):

    print host

    metrics = { # value_type, units, is_average
        'rkB/s' : (3, 'B', False),
        'wkB/s' : (3, 'B', False),
        '%util' : (0, '', True)
    }
    process_metrics(zapi, host=host,
                    application='iostat',
                    search_key='iostat',
                    key_pattern=r'iostat\[(?P<device>[^,]+),\s*(?P<metric>[^\]]+)\]',
                    metrics=metrics,
                    name_format='All Disk %s',
                    key_format='iostat[all,%s]')

    metrics = {
        'in': (3, 'bps', False),
        'out': (3, 'bps', False)
    }
    process_metrics(zapi, host=host,
                    application='Network interfaces',
                    search_key='net.if',
                    key_pattern=r'net.if.(?P<metric>[^\[]+)\[(?P<device>[^\]]+)\]',
                    metrics=metrics,
                    name_format='All Network %s',
                    key_format='net.if.%s[all]')

def process_metrics(zapi, host, application, search_key, key_pattern, metrics, name_format, key_format):

    host = zapi.host.get(filter={'host': host})
    hostid = host[0]['hostid']

    application = zapi.application.get(hostids=hostid, filter={'name': application})
    applicationid = application[0]['applicationid']

    items = zapi.item.get(hostids=hostid,
                          search={'key_': search_key},
                          startSearch=True,
                          output=['key_', 'params'])
    devices = {}
    ptrn_device = re.compile(key_pattern)
    for item in items:
        mo = ptrn_device.match(item['key_'])
        if mo is None:
            continue
        device_name = mo.group('device')
        if device_name not in devices:
            devices[device_name] = {}
        device_info = devices[device_name]
        device_info[mo.group('metric')] = (item['itemid'], item['key_'], item['params'])

    for metric, metric_info in metrics.iteritems():
        print metric
        keys = [v[metric][1] for k, v in devices.iteritems() if k != 'all']
        params = '+'.join('last("%s")' % key for key in keys)
        if metric_info[2]:
            params = '(%s)/%d' % (params, len(keys))

        if 'all' not in devices:
            devices['all'] = {}

        if metric not in devices['all']:
            print 'create', metric, params
            zapi.item.create(hostid=hostid,
                             name=name_format % metric,
                             key_=key_format % metric,
                             type=15,
                             value_type=metric_info[0],
                             params=params,
                             units=metric_info[1],
                             delay=60,
                             applications=[applicationid])

        elif devices['all'][metric][2] != params:
            print 'update', metric, params
            zapi.item.update(itemid=devices['all'][metric][0],
                             params=params)

        else:
            print 'skip', metric


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-z', '--zabbix-server', required=True, help='e.g. zabbix.domain.com:8080')
    parser.add_argument('-u', '--zabbix-username', required=True)
    parser.add_argument('-p', '--zabbix-password', required=True)
    parser.add_argument('-s', '--host', action='append', required=True)
    main(parser.parse_args())

########NEW FILE########
__FILENAME__ = hadoop-collector
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import urllib2
import re
import subprocess
import traceback

SERVICE_UP = 1
SERVICE_DOWN = 0
PTRN_TAG = re.compile('<[^>]+>')

class Job(object):

    def __init__(self, args):
        self.args = args

    def run(self):
        try:
            getattr(self, 'collect_%s' % self.args.type)()
        except Exception:
            traceback.print_exc()
            print SERVICE_DOWN
        else:
            print SERVICE_UP

    def collect_namenode(self):

        f = urllib2.urlopen('http://%s:%d/dfshealth.jsp' % \
                            (self.args.namenode_host, self.args.namenode_port))
        content = f.read()
        f.close()

        result = {}

        mo = re.search('([0-9]+) files and directories, ([0-9]+) blocks', content)
        result['file_count'] = mo.group(1)
        result['block_count'] = mo.group(2)

        mo = re.search('Heap Size is ([0-9.]+ [KMGTP]?B) / ([0-9.]+ [KMGTP]?B)', content)
        result['heap_used'] = self.regulate_size(mo.group(1))
        result['heap_total'] = self.regulate_size(mo.group(2))

        for dfstable in content.split('\n'):
            if 'Configured Capacity' in dfstable:
                break

        dfstable = re.sub('<tr[^>]*>', '\n', dfstable)
        dfstable = PTRN_TAG.sub('', dfstable)
        dfsmap = {}
        for line in dfstable.split('\n'):
            try:
                k, v = line.split(':')
                dfsmap[k.strip()] = v.strip()
            except ValueError:
                pass

        result['dfs_capacity'] = self.regulate_size(dfsmap['Configured Capacity'])
        result['dfs_used'] = self.regulate_size(dfsmap['DFS Used'])
        result['dfs_used_other'] = self.regulate_size(dfsmap['Non DFS Used'])
        result['dfs_remaining'] = self.regulate_size(dfsmap['DFS Remaining'])
        result['node_alive'] = dfsmap['Live Nodes']
        result['node_dead'] = dfsmap['Dead Nodes']
        result['node_decom'] = dfsmap['Decommissioning Nodes']
        result['block_under'] = dfsmap['Number of Under-Replicated Blocks']

        self.send_result(result)

    def collect_jobtracker(self):

        f = urllib2.urlopen('http://%s:%d/jobtracker.jsp' % \
                            (self.args.jobtracker_host, self.args.jobtracker_port))
        content = f.read()
        f.close()

        result = {}

        mo = re.search('Heap Size is ([0-9.]+ [KMGTP]?B)/([0-9.]+ [KMGTP]?B)', content)
        result['heap_used'] = self.regulate_size(mo.group(1))
        result['heap_total'] = self.regulate_size(mo.group(2))

        lines = iter(content.split('\n'))
        for jthead in lines:
            if 'Running Map Tasks' in jthead:
                jtbody = lines.next()
                break

        iter_head = re.finditer('<th[^>]*>(.*?)</th>', jthead)
        iter_body = re.finditer('<td[^>]*>(.*?)</td>', jtbody)

        jtmap = {}
        for mo_head in iter_head:
            mo_body = iter_body.next()
            jtmap[mo_head.group(1).strip()] = PTRN_TAG.sub('', mo_body.group(1)).strip()

        result['map_running'] = jtmap['Running Map Tasks']
        result['map_occupied'] = jtmap['Occupied Map Slots']
        result['map_reserved'] = jtmap['Reserved Map Slots']
        result['map_capacity'] = jtmap['Map Task Capacity']

        result['reduce_running'] = jtmap['Running Reduce Tasks']
        result['reduce_occupied'] = jtmap['Occupied Reduce Slots']
        result['reduce_reserved'] = jtmap['Reserved Reduce Slots']
        result['reduce_capacity'] = jtmap['Reduce Task Capacity']

        result['node_count'] = jtmap['Nodes']
        result['node_black'] = jtmap['Blacklisted Nodes']
        result['node_gray'] = jtmap['Graylisted Nodes']
        result['node_excluded'] = jtmap['Excluded Nodes']

        result['submission_total'] = jtmap['Total Submissions']

        for line in lines:
            if 'Running Jobs' in line:
                break

        job_running = 0
        for line in lines:
            if 'Completed Jobs' in line:
                break
            if 'id="job_' in line:
                job_running += 1

        result['job_running'] = job_running

        for line in lines:
            if 'Failed Jobs' in line:
                break

        job_failed = 0
        for line in lines:
            if 'Retired Jobs' in line:
                break
            if 'id="job_' in line:
                job_failed += 1

        result['job_failed'] = job_failed

        self.send_result(result)

    def collect_tasktracker(self):

        f = urllib2.urlopen('http://%s:%d/machines.jsp?type=active' % \
                            (self.args.jobtracker_host, self.args.jobtracker_port))
        content = f.read()
        f.close()

        lines = iter(content.split('\n'))
        jthead = None
        for line in lines:
            if line.startswith('<tr><td><b>Name'):
                jthead = line
            elif jthead is not None:
                jthead += line
                if '</tr>' in line:
                    break

        jtbody = None
        for line in lines:
            if line.startswith('<tr>') \
                    and self.args.host in line:
                jtbody = line
            elif jtbody is not None:
                jtbody += line
                if '</tr>' in line:
                    break

        iter_head = re.finditer('<td[^>]*>(.*?)</td>', jthead)
        iter_body = re.finditer('<td[^>]*>(.*?)</td>', jtbody)
        jtmap = {}
        for mo_head in iter_head:
            mo_body = iter_body.next()
            jtmap[PTRN_TAG.sub('', mo_head.group(1)).strip()] = \
                    PTRN_TAG.sub('', mo_body.group(1)).strip()

        result = {}
        result['task_running'] = jtmap['# running tasks']
        result['task_capacity'] = int(jtmap['Max Map Tasks']) + int(jtmap['Max Reduce Tasks'])
        result['task_failed'] = jtmap['Failures']
        result['task_total'] = jtmap['Total Tasks Since Start']
        result['task_succeeded'] = jtmap['Succeeded Tasks Since Start']

        self.send_result(result)

    def collect_datanode(self):

        f = urllib2.urlopen('http://%s:%d/dfsnodelist.jsp?whatNodes=LIVE' % \
                            (self.args.namenode_host, self.args.namenode_port))
        content = f.read()
        f.close()

        lines = iter(content.split('\n'))
        for line in lines:
            if line.startswith('<tr class="headerRow">'):
                break
        jthead = line

        for line in lines:
            if line.startswith('<tr') \
                    and self.args.host in line:
                break
        jtbody = re.sub('<table[^>]*>.*?</table>', '', line)

        iter_head = re.finditer('<th[^>]*>(.*?)(?=<th|$)', jthead)
        iter_body = re.finditer('<td[^>]*>(.*?)(?=<td|$)', jtbody)
        jtmap = {}
        ptrn_quote = re.compile(r'\((.*?)\)')
        for mo_head in iter_head:
            mo_body = iter_body.next()

            k = PTRN_TAG.sub('', mo_head.group(1))
            if '(%)' in k:
                continue

            mo = ptrn_quote.search(k)
            k = ptrn_quote.sub('', k).strip()
            v = PTRN_TAG.sub('', mo_body.group(1)).strip()

            if mo is not None:
                jtmap[k] = '%s %s' % (v, mo.group(1))
            else:
                jtmap[k] = v

        result = {}
        result['dfs_capacity'] = self.regulate_size(jtmap['Configured Capacity'])
        result['dfs_used'] = self.regulate_size(jtmap['Used'])
        result['dfs_used_other'] = self.regulate_size(jtmap['Non DFS Used'])
        result['dfs_remaining'] = self.regulate_size(jtmap['Remaining'])
        result['block_count'] = jtmap['Blocks']

        self.send_result(result)

    def send_result(self, result):

        result = self.format_result(result)

        self.log('Sending:')
        self.log(result)

        cmd = ['%s/bin/zabbix_sender' % self.args.zabbix_home]
        cmd.extend(['-c', '%s/etc/zabbix_agentd.conf' % self.args.zabbix_home])
        cmd.extend(['-s', self.args.host])
        cmd.extend(['-i', '-'])

        p = subprocess.Popen((str(s) for s in cmd),
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        self.log('Result:')
        self.log(p.communicate(result)[0])

    def format_result(self, result):
        lines = []
        for k, v in result.iteritems():
            lines.append('- hadoop.%s.%s %s' % (self.args.type, k, v))
        return '\n'.join(lines)

    def regulate_size(self, size):

        try:
            size, unit = size.split()
            size = float(size)
        except ValueError:
            return 0

        if unit == 'KB':
            size = size * 1024
        elif unit == 'MB':
            size = size * 1024 ** 2
        elif unit == 'GB':
            size = size * 1024 ** 3
        elif unit == 'TB':
            size = size * 1024 ** 4
        elif unit == 'PB':
            size = size * 1024 ** 5

        return int(round(size))

    def log(self, msg):
        sys.stderr.write(msg)
        sys.stderr.write('\n')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Hadoop metrics collector for Zabbix.')

    parser.add_argument('-t', '--type', required=True, help='collector type',
                        choices=['namenode', 'datanode', 'jobtracker', 'tasktracker'])

    parser.add_argument('--namenode-host', default='127.0.0.1')
    parser.add_argument('--namenode-port', type=int, default=50070)

    parser.add_argument('--jobtracker-host', default='127.0.0.1')
    parser.add_argument('--jobtracker-port', type=int, default=50030)

    parser.add_argument('-z', '--zabbix-home', default='/usr/local/zabbix-agent-ops')
    parser.add_argument('-s', '--host', required=True, help='hostname recognized by zabbix')

    args = parser.parse_args()

    Job(args).run()

########NEW FILE########
