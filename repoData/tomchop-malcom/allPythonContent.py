__FILENAME__ = celeryconfig
__author__ = 'pyt'
import sys
import os
from datetime import timedelta

sys.path.insert(0, os.getcwd())

CELERY_SEND_EVENTS = True
CELERY_TASK_PUBLISH_RETRY = True
BROKER_HEARTBEAT = 30
BROKER_CONNECTION_RETRY = True
BROKER_CONNECTION_MAX_RETRIES = 100
BROKER_CONNECTION_TIMEOUT = 4
CELERY_CREATE_MISSING_QUEUES = True

BROKER_URL = "amqp://guest:@127.0.0.1//"

CELERY_IMPORTS = ("Malcom.tasks.zeus",
                  "Malcom.tasks.spyeye",
                  "Malcom.tasks.mdl",
                  "Malcom.tasks.other",
                  "Malcom.tasks.scheduler"
)


CELERY_RESULT_BACKEND = "amqp://guest:@127.0.0.1//"
CELERY_TIMEZONE = 'UTC'

# CELERY_ROUTES = {
#     'CeleryPaste.tasks.couchdb_tasks': {'queue': 'db'},
#     'CeleryPaste.tasks.download_tasks': {'queue': 'download'},
#     'CeleryPaste.tasks.grabers_tasks': {'queue': 'grabers'},
#     'CeleryPaste.tasks.redis_tasks': {'queue': 'db'},
# }

CELERY_CREATE_MISSING_QUEUES = True

CELERYBEAT_SCHEDULE = {
    'runs-every-60-minute': {
        'task': 'Malcom.tasks.scheduler.worker',
        'schedule': timedelta(minutes=10)
    },
}
########NEW FILE########
__FILENAME__ = integrity
from analytics import Analytics
from toolbox import debug_output
a = Analytics()


# Check if there are elements which have no created date
nocreate = a.data.find({"date_created": None}).count()
type = "error" if nocreate > 0 else "debug"
debug_output("Elements without a date_created: {}".format(nocreate), type)

# Check if there are elements which have no updated date
noupdate = a.data.find({"date_updated": None}).count()
type = "error" if noupdate > 0 else "debug"
debug_output("Elements without a date_updated: {}".format(noupdate), type)

# Check if there are urls that don't have hostnames
nohostname = a.data.find({'type': 'url', 'hostname': None}).count()
type = "error" if nohostname > 0 else "debug"
debug_output("URLs without a hostname: {}".format(nohostname), type)

emptyhostname = a.data.find({'type': 'url', 'hostname': ""}).count()
type = "error" if emptyhostname > 0 else "debug"
debug_output("URLs with empty hostname: {}".format(emptyhostname), type)



########NEW FILE########
__FILENAME__ = analytics
from flask import Flask
import dateutil, time, threading

from bson.objectid import ObjectId

from Malcom.auxiliary.toolbox import *
from Malcom.model.model import Model
from Malcom.model.datatypes import Hostname, Ip, Url, As
import Malcom

class Worker(threading.Thread):

	def __init__(self, elt, engine):
		threading.Thread.__init__(self)
		self.elt = elt
		self.engine = engine
		self.thread = None
		

	def run(self):
		
		debug_output("Started thread on %s %s" % (self.elt['type'], self.elt['value']), type='analytics')
		etype = self.elt['type']
		tags = self.elt['tags']

		new = self.elt.analytics()
		
		for n in new:
			saved = self.engine.save_element(n[1])
			#do the link
			self.engine.data.connect(self.elt, saved, n[0])
		
		# this will change updated time
		self.engine.save_element(self.elt, tags)

		self.engine.progress += 1
		self.engine.websocket_lock.acquire()
		self.engine.notify_progress(self.elt['value'])
		self.engine.websocket_lock.release()
		self.engine.max_threads.release()

class Analytics:

	def __init__(self):
		self.data = Model()
		self.max_threads = Malcom.config.get('MAX_THREADS', 4)
		self.active = False
		self.status = "Inactive"
		self.websocket = None
		self.thread = None
		self.websocket_lock = threading.Lock()
		self.stack_lock = threading.Lock()
		self.progress = 0
		self.total = 0

		self.max_threads = threading.Semaphore(self.max_threads)
		self.worker_threads = {}

	def add_text(self, text, tags=[]):
		added = []
		for t in text:
			elt = None
			if t.strip() != "":
				if is_url(t):
					elt = Url(is_url(t), [])
				elif is_hostname(t):
					elt = Hostname(is_hostname(t), [])
				elif is_ip(t):
					elt = Ip(is_ip(t), [])
				if elt:
					added.append(self.save_element(elt, tags))
					
		if len(added) == 1:
			return added[0]
		else:
			return added
		

	def save_element(self, element, tags=[], with_status=False):
		element.upgrade_tags(tags)
		return self.data.save(element, with_status=with_status)
		


	# graph function
	def add_artifacts(self, data, tags=[]):
		artifacts = find_artifacts(data)
		
		added = []
		for url in artifacts['urls']:
			added.append(self.save_element(url, tags))

		for hostname in artifacts['hostnames']:
			added.append(self.save_element(hostname, tags))

		for ip in artifacts['ips']:
			added.append(self.save_element(ip, tags))

		return added        


	# elements analytics

	def bulk_asn(self, items=1000):

		last_analysis = {'$or': [
									{ 'last_analysis': {"$lt": datetime.datetime.utcnow() - datetime.timedelta(days=7)} },
									{ 'last_analysis': None },
								]
						}

		nobgp = {"$or": [{'bgp': None}, last_analysis ]}

		total = self.data.elements.find({ "$and": [{'type': 'ip'}, nobgp]}).count()
		done = 0
		results = [r for r in self.data.elements.find({ "$and": [{'type': 'ip'}, nobgp]})[:items]]

		while len(results) > 0:
		
			ips = []
			debug_output("(getting ASNs for %s IPs - %s/%s done)" % (len(results), done, total), type='analytics')
			
			for r in results:
				ips.append(r)

			as_info = {}
			
			try:
				as_info = get_net_info_shadowserver(ips)
			except Exception, e:
				debug_output("Could not get AS for IPs: %s" % e)
			
			if as_info == {}:
				debug_output("as_info empty", 'error')
				return

			for ip in as_info:
				
				_as = as_info[ip]
				_ip = self.data.find_one({'value': ip})

				if not _ip:
					return

				del _as['ip']
				for key in _as:
					if key not in ['type', 'value', 'tags']:
						_ip[key] = _as[key]
				del _as['bgp']

				_as = As.from_dict(_as)

				# commit any changes to DB
				_as = self.save_element(_as)
				_ip['last_analysis'] = datetime.datetime.now()
				_ip = self.save_element(_ip)
			
				if _as and _ip:
					self.data.connect(_ip, _as, 'net_info')
			done += len(results)
			results = [r for r in self.data.elements.find({ "$and": [{'type': 'ip'}, nobgp]})[:items]]

	def find_neighbors(self, query, include_original=True):
		
		total_nodes = {}
		total_edges = {}
		final_query = []

		for key in query:

			if key == '_id': 
				values = [ObjectId(v) for v in query[key]]
			else:
				values = [v for v in query[key]]

			final_query.append({key: {'$in': values}})

		elts = self.data.elements.find({'$and': final_query})
		
		nodes, edges = self.data.get_neighbors_id(elts, include_original=include_original)
		for n in nodes:
			total_nodes[n['_id']] = n
		for e in edges:
			total_edges[e['_id']] = e
			
		total_nodes = [total_nodes[n] for n in total_nodes]	
		total_edges = [total_edges[e] for e in total_edges]

		# display 
		for e in total_nodes:
			e['fields'] = e.display_fields

		data = {'nodes':total_nodes, 'edges': total_edges }

		return data

	def multi_graph_find(self, query, graph_query, depth=2):
		total_nodes = {}
		total_edges = {}

		for key in query:

			for value in query[key]:
				
				if key == '_id': value = ObjectId(value)

				elt = self.data.elements.find_one({key: value})
				
				nodes, edges = self.single_graph_find(elt, graph_query, depth)
				
				for n in nodes:
					total_nodes[n['_id']] = n
				for e in edges:
					total_edges[e['_id']] = e
			
		total_nodes = [total_nodes[n] for n in total_nodes]	
		total_edges = [total_edges[e] for e in total_edges]

		data = {'nodes':total_nodes, 'edges': total_edges }

		return data


	def single_graph_find(self, elt, query, depth=2):
		chosen_nodes = []
		chosen_links = []
		
		if depth > 0:
			# get a node's neighbors
			neighbors_n, neighbors_l = self.data.get_neighbors_elt(elt, include_original=False)
			
			for i, node in enumerate(neighbors_n):
				# for each node, find evil (recursion)
				en, el = self.single_graph_find(node, query, depth=depth-1)
				
				# if we found evil nodes, add them to the chosen_nodes list
				if len(en) > 0:
					chosen_nodes += [n for n in en if n not in chosen_nodes] + [node]
					chosen_links += [l for l in el if l not in chosen_links] + [neighbors_l[i]]
		else:
			
			# if recursion ends, then search for evil neighbors
			neighbors_n, neighbors_l = self.data.get_neighbors_elt(elt, {query['key']: {'$in': [query['value']]}}, include_original=False)
			
			# return evil neighbors if found
			if len(neighbors_n) > 0:
				chosen_nodes += [n for n in neighbors_n if n not in chosen_nodes]
				chosen_links += [l for l in neighbors_l if l not in chosen_links]
				
			# if not, return nothing
			else:
				chosen_nodes = []
				chosen_links = []

		return chosen_nodes, chosen_links


	def process(self):
		if self.thread:
			if self.thread.is_alive():
				return
		self.thread = threading.Thread(None, self.process_thread, None)
		self.thread.start()
		self.thread.join() # wait for analytics to finish
		# regroup ASN analytics to make only 1 query to Cymru / Shadowserver

		self.bulk_asn()
		self.active = False
		debug_output("Finished analyzing.")
		self.notify_progress("Finished analyzing.")


	def notify_progress(self, msg=None):

		status = {'active': self.active, 'msg': msg}
		status['progress'] = '%s' % (self.progress)
		send_msg(self.websocket, status, type='analyticsstatus')

	def process_thread(self):
		
		self.active = True

		query = {'next_analysis' : {'$lt': datetime.datetime.utcnow() }}
		total = self.data.elements.find(query).count()
		results = self.data.elements.find(query)
		
		
		i = 0
		while total > 0:


			for r in results:
				debug_output("Progress: %s/%s" % (i, total), 'analytics')
				self.max_threads.acquire()
				with self.stack_lock:
				
					# start thread
					w = Worker(r, self)
					self.worker_threads[r['value']] = w
					w.start()
					i+=1
			
			for t in self.worker_threads:
				self.worker_threads[t].join()

			self.worker_threads = {}
			
			query = {'next_analysis' : {'$lt': datetime.datetime.utcnow() }}
			total = self.data.elements.find(query).count()
			results = self.data.elements.find(query)
			
			









########NEW FILE########
__FILENAME__ = toolbox
import socket, sys
import inspect
import urlparse
import re
import urllib2
import socket
import json
import datetime
import string
#from pyquery import PyQuery               # external 
#from lxml import etree
from dateutil.parser import parse
import logging
from subprocess import check_output, CalledProcessError, STDOUT
from bson.json_util import dumps

url_regex = r"""

        (
          ((?P<scheme>[\w]{2,9}):\/\/)?
          ([\S]*\:[\S]*\@)?
          (?P<hostname>(
                      ((([\w\-]+\.)+)
                      ([a-zA-Z]{2,6}))
                      |([\d+]{1,3}\.[\d+]{1,3}\.[\d+]{1,3}\.[\d+]{1,3})
                      )
          )

          (\:[\d]{1,5})?
          (?P<path>(\/[\/\~\w\-_%\.\*\#\$]*)?
            (\?[\~\w\-_%\.&=\*\#\$]*)?
            (\#[\S]*)?)
        )
    """

tlds = [u'cx', u'cy', u'cz', u'ro', u'ke', u'kg', u'kh', u'ki', u'cr', u'cs', u'cu', u'cv', u'ch', u'ci', u'kr', u'ck', u'cl', u'cm', u'cn', u'co', u'rs', u'ca', u'kz', u'cc', u'cd', u'cf', u'cg', u'zw', u'iq', u'tk', u'za', u'info', u'nz', u'ua', u'name', u'ug', u'bz', u'by', u'uz', u'je', u'post', u'bs', u'br', u'bw', u'bv', u'jm', u'bt', u'bj', u'bi', u'bh', u'bo', u'bn', u'bm', u'bb', u'ba', u'jobs', u'bg', u'bf', u'be', u'bd', u'mo', u'kp', u'eh', u'eg', u'net', u'ec', u'tj', u'et', u'eu', u'er', u'travel', u'pm', u'pl', u'ee', u'in', u'io', u'il', u'im', u'pe', u'pg', u'kw', u'pa', u'id', u'ie', u'sk', u'py', u'yt', u'tg', u'ky', u'ir', u'is', u'pw', u'am', u'tz', u'it', u'lt', u'sd', u'pf', u'rw', u'ws', u'ru', u'tw', u'arpa', u'cat', u'pro', u'sh', u'si', u'sj', u'sc', u'sl', u'sm', u'sn', u'so', u'hm', u'sa', u'sb', u'hn', u'coop', u'se', u'hk', u'sg', u'hu', u'ht', u'sz', u'tv', u'hr', u'sr', u'ss', u'st', u'su', u'sv', u'sx', u'sy', u'mobi', u'wf', u'es', u'org', u'tel', u'ye', u'om', u'vu', u'priv', u'edu', u're', u'zm', u've', u'pn', u'vc', u'va', u'vn', u'tc', u'vi', u'ph', u'int', u'fo', u'fm', u'fk', u'fj', u'fi', u'fr', u'no', u'nl', u'SH', u'ni', u'ng', u'mz', u'ne', u'nc', u'biz', u'na', u'qa', u'com', u'nu', u'tc', u'nr', u'np', u'ac', u'test', u'af', u'ag', u'ad', u'ae', u'ai', u'an', u'ao', u'al', u'yu', u'ar', u'as', u'th', u'aq', u'aw', u'at', u'au', u'az', u'ax', u'pk', u'tl', u'mv', u'mw', u'mt', u'mu', u'mr', u'ms', u'mp', u'mq', u'tp', u'tn', u'km', u'tt', u'mx', u'my', u'mg', u'md', u'me', u'tm', u'mc', u'to', u'ma', u'mn', u'asia', u'ml', u'mm', u'mk', u'mh', u'tf', u'gt', u'dk', u'dj', u'dm', u'do', u'museum', u'kn', u'uy', u'de', u'dd', u'td', u'jp', u'dz', u'ps', u'nf', u'pt', u'pr', u'mil', u'ls', u'lr', u'lu', u'gr', u'lv', u'ly', u'jo', u'gov', u'vg', u'us', u'la', u'lc', u'lb', u'tm', u'li', u'lk', u'tr', u'gd', u'ge', u'gf', u'gg', u'ga', u'gb', u'gl', u'gm', u'gn', u'gh', u'gi', u'aero', u'gu', u'gw', u'gp', u'gq', u'xxx', u'gs', u'gy', u'la', u'uk']

def list_to_str(obj):
    if isinstance(obj, list):
        return ", ".join([list_to_str(e) for e in obj])
    else:
        return str(obj)


def send_msg(ws, msg, type='msg'):
    msg = {'type':type, 'msg': msg}
    try:
        ws.send(dumps(msg))
    except Exception, e:
        debug_output("Could not send message: %s" % e)
    


def find_ips(data):
    ips = []
    for i in re.finditer("([\d+]{1,3}\.[\d+]{1,3}\.[\d+]{1,3}\.[\d+]{1,3})",data):
        # sanitize IPs to avoid leading 0s
        ip = ".".join([str(int(dot)) for dot in i.group(1).split('.')])
        ips.append(ip)
    return ips

def find_urls(data):
    urls = []
    _re = re.compile(url_regex,re.VERBOSE)

    for i in re.finditer(_re,data):
        url = i.group(1)

        h = find_hostnames(data)
        i = find_ips(data)
        
        if (len(h) > 0 or len(i) > 0) and url.find('/') != -1: # there's at least one IP or one hostname in the URL
            urls.append(url)

    return urls

def find_hostnames(data):
    # sends back an array of hostnames
    hostnames = []
    for i in re.finditer("((([\w\-]+\.)+)([a-zA-Z]{2,6}))\.?", data):
        h = string.lower(i.group(1))
        tld = h.split('.')[-1:][0]

        if tld in tlds or tld.startswith('xn--'):
            hostnames.append(h)

    return hostnames

def whois(data):
    
    try:
        response = check_output('whois %s' %data,
                shell=True,
                stderr=STDOUT)
        response = response.decode('cp1252').encode('utf-8')
    except Exception, e:
        response = "Whois resolution failed"
    
    return response


def find_emails(data):
    emails = []
    for i in re.finditer("([\w\-\.\_]+@(([\w\-]+\.)+)([a-zA-Z]{2,6}))\.?",data):
        e = string.lower(i.group(1))
        tld = e.split('.')[-1:]
        emails.append(e)
    return emails

def find_hashes(data):
    hashes = []
    for i in re.finditer("([a-fA-F0-9]{32,64})",data):
        hashes.append(string.lower(i.group(1)))
    return hashes

def find_artifacts(data):

    artifacts = {}

    as_list = []

    artifacts['urls'] = list(set(find_urls(data)))
    as_list += list(set(find_urls(data)))
    artifacts['hostnames'] = list(set(find_hostnames(data)))
    as_list += list(set(find_hostnames(data)))
    artifacts['hashes'] = list(set(find_hashes(data)))
    as_list += list(set(find_hashes(data)))
    artifacts['emails'] = list(set(find_emails(data)))
    as_list += list(set(find_emails(data)))
    artifacts['ips'] = list(set(find_ips(data)))
    as_list += list(set(find_ips(data)))

    return artifacts


def is_ip(ip):
    ip = find_ips(ip)
    if len(ip) > 0:
        return ip[0]
    else:
        return None


def is_hostname(hostname):

    hostname = find_hostnames(hostname)
    if len(hostname) > 0:
        return string.lower(hostname[0])
    else:
        return None

def is_subdomain(hostname):
    hostname = find_hostnames(hostname)
    if len(hostname) > 0:
        hostname = hostname[0]

        tld = hostname.split('.')[-1:][0]
        if tld in tlds:
            tld = hostname.split('.')[-2:][0]
            if tld in tlds:
                domain = ".".join(hostname.split('.')[-3:])
                if domain == hostname:
                    return False
                else:
                    return domain
            else:
                domain = ".".join(hostname.split('.')[-2:])
                if domain == hostname:
                    return False
                else:
                    return domain

    else:
        return False


def is_url(url):

    url = find_urls(url)

    if len(url) > 0:
        return url[0]
    else:
        return None

def split_url(url):
    _re = re.compile(url_regex,re.VERBOSE)
    data = re.search(_re, url)
    if data:
        path = data.group('path')
        scheme = data.group('scheme')
        hostname = data.group('hostname')
        return (path, scheme, hostname)
    return None

def dns_dig_records(hostname):

    try:
        _dig = check_output(['dig', hostname, '+noall', '+answer', 'A'])
        _dig += check_output(['dig', hostname, '+noall', '+answer', 'NS'])
        _dig += check_output(['dig', hostname, '+noall', '+answer', 'MX'])
        _dig += check_output(['dig', hostname, '+noall', '+answer', 'CNAME'])
    except CalledProcessError, e:
        _dig = e.output

    results = [r.groupdict() for r in re.finditer(re.escape(hostname)+'\..+\s+(?P<record_type>[A-Za-z]+)[\s]+([0-9]+ )?(?P<record>\S+)\n',_dig)]
    records = {}
    for r in results:
        if r['record_type'] in records:
            records[r['record_type']].append(r['record'])
        else:
            records[r['record_type']] = [r['record']]

    for r in records:
        records[r] = list(set(records[r]))
    return records

def dns_dig_reverse(ip):
    try:
        _dig = check_output(['dig', '-x', ip])
    except Exception, e:
        _dig = str(e)

    results = re.search('PTR\t+(?P<record>.+)', _dig)
    if results:
        hostname = is_hostname(results.group('record'))
    else:
        hostname = None

    return hostname



def url_get_host(url):
    hostname = split_url(url)[2]
    if hostname == "":
        return None
    else:
        return hostname
    

def url_check(url):
    try:
        result = urllib2.urlopen(url)
        return result.code
    except urllib2.HTTPError, e:
        return result.code
    except urllib2.URLError:
        return None

def get_net_info_shadowserver(ips):  
    #from shadowserver

    query = "begin origin\r\n"
    for ip in ips: query += str(ip['value']) + "\r\n"
    query +="end\r\n"

    #open('query.txt', 'w+').write(query)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("asn.shadowserver.org", 43))
    except Exception, e:
        debug_output("Failed to get AS data from asn.shadowserver.org: %s" % e)
        return None
    
    s.send(query)

    response = ''
    while True:
        data = s.recv(4096)
        response += data
        if not data: break
    s.close()

    parsed = parse_net_info_shadowserver(response)

    return parsed

    # Deal with responses like
    #
    #  IP            | AS  | BGP Prefix    | AS Name             | CC | Domain      | ISP 
    #  17.112.152.32 | 714 | 17.112.0.0/16 | APPLE-ENGINEERING   | US | APPLE.COM   | APPLE COMPUTER INC
    #

def parse_net_info_shadowserver(info):
    lines = info.split("\n")
    lines = lines[:-1]
    results = {}
    for line in lines:
        entry = {}
        columns = line.split("|")

        entry['ip'] = columns[0].lstrip().rstrip()
        entry['asn'] = columns[1].lstrip().rstrip()
        entry['bgp'] = columns[2].lstrip().rstrip()
        entry['name'] = columns[3].lstrip().rstrip().decode('latin-1')
        entry['country'] = columns[4].lstrip().rstrip()
        entry['domain'] = columns[5].lstrip().rstrip()
        entry['ISP'] = columns[6].lstrip().rstrip()
        entry['value'] = "%s (%s)" % (entry['name'], entry['asn'])

        results[entry['ip']] = entry

    return results

def get_net_info_cymru(ips):  
    #from cymru
    
    query = "begin\r\nverbose\r\n"
    for ip in ips: query += str(ip) + "\r\n"
    query +="end\r\n"

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    debug_output("Connecting to whois.cymru.com")
    try:
        s.connect(("whois.cymru.com", 43))
    except Exception, e:
        debug_output("Failed to get AS data from whois.cymru.com: %s" % e)
        return None
    
    s.send(query)

    response = ''
    while True:
        data = s.recv(4096)
        response += data
        if not data: break
    s.close()

    parsed = parse_net_info(response)

    return parsed

    # Deal with responses like
    #
    # AS      | IP               | BGP Prefix          | CC | Registry | Allocated  | AS Name
    # 16276   | 213.251.173.198  | 213.251.128.0/18    | FR | ripencc  | 2004-05-18 | OVH OVH Systems
    #
def parse_net_info_cymru(info):
    lines = info.split("\n")
    lines = lines[1:-1]
    results = {}
    for line in lines:
        entry = {}
        columns = line.split("|")

        entry['value'] = columns[0].lstrip().rstrip()
        entry['bgp'] = columns[2].lstrip().rstrip()
        entry['country'] = columns[3].lstrip().rstrip()
        entry['registry'] = columns[4].lstrip().rstrip()
        entry['allocated'] = parse(columns[5].lstrip().rstrip())
        entry['as_name'] = columns[6].lstrip().rstrip()
        
        results[entry['value']] = entry

    return results

def debug_output(text, type='debug', n=True):
    if type == 'debug':
        msg = bcolors.OKGREEN + '[DEBUG]'
    if type == 'model':
        msg = bcolors.HEADER + '[MODEL]'
    if type == 'analytics':
        msg = bcolors.OKBLUE + '[ANALYTICS]'
    if type == 'error':
        msg = bcolors.FAIL + '[ERROR]'
    if type == 'info':
        msg = bcolors.WARNING + '[INFO]'
    msg += bcolors.ENDC
    n = '\n' if n else ""
    try:
        sys.stderr.write(str("%s - %s%s" % (msg, text, n)))
    except Exception, e:
        pass
    


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''


if __name__ == "__main__":
    pass
        
########NEW FILE########
__FILENAME__ = celeryctl
__author__ = 'pyt'
from celery import Celery
from celery.utils.log import get_task_logger

celery = Celery()
celery.config_from_object('celeryconfig')
logger = get_task_logger(__name__)

########NEW FILE########
__FILENAME__ = alienvault
import urllib2
from Malcom.model.datatypes import Ip 
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class AlienvaultIP(Feed):
	"""
	This gets data from https://reputation.alienvault.com/
	"""
	def __init__(self, name):
		super(AlienvaultIP, self).__init__(name, run_every="12h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("https://reputation.alienvault.com/reputation.generic").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			ip = toolbox.find_ips(line)[0]
		except Exception, e:
			# if find_ip raises an exception, it means no ip 
			# was found in the line, so we return
			return

		# Create the new ip and store it in the DB
		ip = Ip(ip=ip, tags=['alienvault'])

		ip, status = self.analytics.save_element(ip, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = cybercrimetracker
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Evil, Url
from feed import Feed

class CybercrimeTracker(Feed):

	def __init__(self, name):
		super(CybercrimeTracker, self).__init__(name, run_every="12h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://cybercrime-tracker.net/rss.xml")	#Xylitol's tracker
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False

		children = ["title", "link", "pubDate", "description"]
		main_node = "item"
		
		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
		try:
			url = toolbox.find_urls(dict['title'])[0]
		except Exception, e:
			return

		# Create the new url and store it in the DB
		url =Url(url=url, tags=['cybercrimetracker', 'malware', dict['description'].lower()])

		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1
########NEW FILE########
__FILENAME__ = dshield_as16276
import urllib2
from Malcom.model.datatypes import Ip 
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class DShield16276(Feed):
	"""
	This gets data from http://dshield.org/asdetailsascii.html?as=16276
	"""
	def __init__(self, name):
		super(DShield16276, self).__init__(name)
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://dshield.org/asdetailsascii.html?as=16276").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			ip = toolbox.find_ips(line)[0]
		except Exception, e:
			# if find_ip raises an exception, it means no ip 
			# was found in the line, so we return
			return

		# Create the new ip and store it in the DB
		ip = Ip(ip=ip, tags=['dshield'])

		ip, status = self.analytics.save_element(ip, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = dshield_as3215
import urllib2
from Malcom.model.datatypes import Ip 
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class DShield3215(Feed):
	"""
	This gets data from http://dshield.org/asdetailsascii.html?as=3215
	"""
	def __init__(self, name):
		super(DShield3215, self).__init__(name)
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://dshield.org/asdetailsascii.html?as=3215").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			ip = toolbox.find_ips(line)[0]
		except Exception, e:
			# if find_ip raises an exception, it means no ip 
			# was found in the line, so we return
			return

		# Create the new ip and store it in the DB
		ip = Ip(ip=ip, tags=['dshield'])

		ip, status = self.analytics.save_element(ip, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = dshield_suspiciousdomains_high
import urllib2
from Malcom.model.datatypes import Hostname
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class DShieldSuspiciousDomainsHigh(Feed):
	def __init__(self, name):
		super(DShieldSuspiciousDomainsHigh, self).__init__(name)
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://www.dshield.org/feeds/suspiciousdomains_High.txt").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			hostname = toolbox.find_hostnames(line)[0]
		except Exception, e:
			return

		# Create the new ip and store it in the DB
		hostname = Hostname(hostname=hostname, tags=['dshield', 'high'])

		hostname, status = self.analytics.save_element(hostname, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = dshield_suspiciousdomains_low
import urllib2
from Malcom.model.datatypes import Ip 
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class DShieldSuspiciousDomainsLow(Feed):
	def __init__(self, name):
		super(DShieldSuspiciousDomainsLow, self).__init__(name)
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://www.dshield.org/feeds/suspiciousdomains_Low.txt").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			hostname = toolbox.find_hostnames(line)[0]
		except Exception, e:
			return

		# Create the new ip and store it in the DB
		hostname = Hostname(hostname=hostname, tags=['dshield', 'low'])

		hostname, status = self.analytics.save_element(hostname, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = dshield_suspiciousdomains_medium
import urllib2
from Malcom.model.datatypes import Ip 
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class DShieldSuspiciousDomainsMedium(Feed):
	def __init__(self, name):
		super(DShieldSuspiciousDomainsMedium, self).__init__(name)
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://www.dshield.org/feeds/suspiciousdomains_Medium.txt").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			hostname = toolbox.find_hostnames(line)[0]
		except Exception, e:
			return

		# Create the new ip and store it in the DB
		hostname = Hostname(hostname=hostname, tags=['dshield', 'medium'])

		hostname, status = self.analytics.save_element(hostname, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = feed
import os, sys, threading, time
from datetime import timedelta, datetime

from Malcom.auxiliary.toolbox import debug_output
import Malcom


class Feed(object):
	"""This is a feed base class. All other feeds must inherit from this class"""
	def __init__(self, name, run_every="24h"):
		self.name = name

		# parse timedelta
		num = int(run_every[:-1])
		if run_every.endswith('s'):
			self.run_every = timedelta(seconds=num)
		if run_every.endswith('m'):
			self.run_every = timedelta(minutes=num)
		if run_every.endswith('h'):
			self.run_every = timedelta(hours=num)
		if run_every.endswith('d'):
			self.run_every = timedelta(days=num)

		self.last_run = None
		self.next_run = datetime.utcnow()
		self.running = False
		self.elements_fetched = 0
		self.status = "OK"
		self.analytics = None
		self.enabled = False

	def get_dict(self):
		return { 'name': self.name,
				 'last_run': self.last_run,
				 'next_run': self.next_run,
				 'running': self.running,
				 'elements_fetched': self.elements_fetched,
				 'status': self.status,
				 'analytics': self.analytics,
				 'enabled': self.enabled,
				}

	def update(self):
		"""
		The update() function has to be implemented in each of your feeds.
		Its role is to:
		 - Fetch data from wherever it needs to
		 - Translate this data into elements understood by Malcom (as defined in malcom.datatypes.element)
		 - Save these newly created elements to the database using the self.analytics attribute
		"""
		raise NotImplementedError("update: This method must be implemented in your feed class")

	def run(self):

		self.running = True
		self.last_run = datetime.now()
		self.next_run = self.last_run + self.run_every
		self.elements_fetched = 0

		
		self.analytics.notify_progress("Feeding")
		status = self.update()
		self.analytics.notify_progress("Inactive")
		self.running = False



class FeedEngine(threading.Thread):
	"""Feed engine. This object will load and update feeds"""
	def __init__(self, analytics):
		threading.Thread.__init__(self)
		self.a = analytics
		self.feeds = {}
		self.threads = {}
		self.global_thread = None

		# for periodic tasking
		self.period = 60
		self.run_periodically = False

	def run_feed(self, feed_name):
		if self.threads.get(feed_name):
			if self.threads[feed_name].is_alive():
				return
		self.threads[feed_name] = threading.Thread(None, self.feeds[feed_name].run, None)
		self.threads[feed_name].start()

	def run_all_feeds(self):
		debug_output("Running all feeds")
		for feed_name in [f for f in self.feeds if self.feeds[f].enabled]:
			debug_output('Starting thread for feed %s...' % feed_name)
			self.run_feed(feed_name)

		for t in self.threads:
			if self.threads[t].is_alive():
				self.threads[t].join()


	def stop_all_feeds(self):
		self.run_periodically = False
		for t in self.threads:
			if self.threads[t].is_alive():
				self.threads[t]._Thread__stop()
		
		self._Thread__stop()

	def run_scheduled_feeds(self):
		for feed_name in [f for f in self.feeds if (self.feeds[f].next_run < datetime.utcnow() and self.feeds[f].enabled)]:	
			debug_output('Starting thread for feed %s...' % feed_name)
			self.run_feed(feed_name)

		for t in self.threads:
			if self.threads[t].is_alive():
				self.threads[t].join()
		

	def run(self):
		self.run_periodically = True
		while self.run_periodically:
			time.sleep(self.period) # run a new thread every period seconds
			debug_output("Checking feeds...")
			self.run_scheduled_feeds()


	def load_feeds(self):
	
		globals_, locals_ = globals(), locals()

		feeds_dir = Malcom.config['FEEDS_DIR']
		package_name = 'feeds'

		debug_output("Loading feeds in %s" % feeds_dir)
		
		for filename in os.listdir(feeds_dir):
			export_names = []
			export_classes = []

			modulename, ext = os.path.splitext(filename)
			if modulename[0] != "_" and ext in ['.py']:
				subpackage = 'Malcom.%s.%s' % (package_name, modulename)
				
				module = __import__(subpackage, globals_, locals_, [modulename])

				modict = module.__dict__

				names = [name for name in modict if name[0] != '_']
				
				for n in names:
					if n == 'Feed':
						continue
					class_n = modict.get(n)
					try:
						if issubclass(class_n, Feed) and class_n not in globals_:
							new_feed = class_n(n) # create new feed object
							new_feed.analytics = self.a # attach analytics instance to feed
							self.feeds[n] = new_feed

							# this may be for show for now
							export_names.append(n)
							export_classes.append(class_n)
							sys.stderr.write(" + Loaded %s...\n" % n)
					except Exception, e:
						pass
						

		globals_.update((export_names[i], c) for i, c in enumerate(export_classes))

		return export_names, export_classes










########NEW FILE########
__FILENAME__ = malcode
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Evil, Url
from feed import Feed




class MalcodeBinaries(Feed):

	def __init__(self, name):
		super(MalcodeBinaries, self).__init__(name, run_every="1h")
		self.enabled = True

	def update(self):
		try:
			request = urllib2.Request("http://malc0de.com/rss/", headers={"User-agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"})
                        feed = urllib2.urlopen(request)
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		children = ["title", "description", "link"]
		main_node = "item"
		

		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
			
		# We create an Evil object. Evil objects are what Malcom uses
		# to store anything it considers evil. Malware, spam sources, etc.
		# Remember that you can create your own datatypes, if need be.

		evil = Evil()

		# We start populating the Evil() object's attributes with
		# information from the dict we parsed earlier

		evil['feed'] = "MalcodeBinaries"
		print dict['description']
		evil['url'] = toolbox.find_urls(dict['description'])[0]
		
		# description
		evil['description'] = dict['link'] + " " + dict['description'] 

		# md5 
		md5 = re.search("MD5 hash: (?P<md5>[0-9a-f]{32,32})",dict['description'])
		if md5 != None:
			evil['md5'] = md5.group('md5')
		else:
			evil['md5'] = "No MD5"
		
		# linkback
		evil['source'] = dict['link']

		# type
		evil['type'] = 'evil'

		# tags
		evil['tags'] += ['malcode', 'malware', 'MalcodeBinaries']

		# date_retreived
		evil['date_retreived'] = datetime.datetime.utcnow()

		# This is important. Values have to be unique, since it's this way that
		# Malcom will identify them in the database.
		# This is probably not the best way, but it will do for now.

		evil['value'] = "Malware"
		if md5:
			evil['value'] += " (MD5: %s)" % evil['md5']
		else:
			evil['value'] += " (URL: %s)" % evil['url']

		# Save elements to DB. The status field will contain information on 
		# whether this element already existed in the DB.

		evil, status = self.analytics.save_element(evil, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Create an URL element
		url = Url(evil['url'], ['evil', 'MalcodeBinaries'])

		# Save it to the DB.
		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Connect the URL element to the Evil element
		self.analytics.data.connect(url, evil, 'hosting')


########NEW FILE########
__FILENAME__ = MalcomBaseFeed
import urllib2
from bson.json_util import dumps, loads
from Malcom.model.datatypes import Ip, Url, Hostname, As, Evil 
from Malcom.feeds.feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class MalcomBaseFeed(Feed):
	"""
	This gets data from other Malcom Instances 
	"""
	def __init__(self, name):
		super(MalcomBaseFeed, self).__init__(name, run_every="12h")
		self.enabled = False
		self.apikey = "ENTER-YOUR-API-KEY-HERE"
		self.malcom_host = "malcom.public.instance.com"

	def update(self):
		try:
			request = urllib2.Request("http://%s/public/api" % self.malcom_host, headers={'X-Malcom-API-Key': self.apikey})
			feed = urllib2.urlopen(request).read()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		self.analyze(feed)
		return True

	def analyze(self, line):
		elements = loads(line)
		test = []
		for elt in elements:
			status = self.analytics.save_element(elt, with_status=True)
			if status['updatedExisting'] == False:
				self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = malwaredomains
import urllib2
import re
from Malcom.model.datatypes import Hostname 
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class MalwareDomains(Feed):
	def __init__(self, name):
		super(MalwareDomains, self).__init__(name)
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://mirror1.malwaredomains.com/files/domains.txt").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		splitted_mdl = re.split(r'\t+', line.lstrip('\t'))
		# 	20151201	agasi-story.info	malicious	blog.dynamoo.com	20131130	20121201	20120521	20110217

		if unicode(splitted_mdl[0]).isnumeric():
			splitted_mdl.pop(0)

		# Create the new hostname and store it in the DB
		hostname = Hostname(hostname=splitted_mdl[0], tags=['malwaredomains', splitted_mdl[1].lower(), splitted_mdl[2]])

		hostname, status = self.analytics.save_element(hostname, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = malwared_ru
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Evil, Url
from feed import Feed

class MalwaredRu(Feed):

	def __init__(self, name):
		super(MalwaredRu, self).__init__(name, run_every="1h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://malwared.ru/rss.php")
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False

	# <item><title>Solar</title><description>Mar/2014</description><link>http://...</link></item>

		children = ["title", "description", "link"]
		main_node = "item"
		
		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
		try:
			url = toolbox.find_urls(dict['link'])[0]
		except Exception, e:
			return

		# Create the new url and store it in the DB
		url =Url(url=url, tags=['Malwared.ru', 'malware', dict['title'].lower()])

		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1
########NEW FILE########
__FILENAME__ = malwarepatrol
import urllib2
from Malcom.model.datatypes import Url 
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class MalwarePatrolVX(Feed):
	"""
	This gets data from http://www.malwarepatrol.net/cgi/submit?action=list 
	"""
	def __init__(self, name):
		super(MalwarePatrolVX, self).__init__(name, run_every="1h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://www.malwarepatrol.net/cgi/submit?action=list").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			url = toolbox.find_urls(line)[0]

		except Exception, e:
			# if find_urls raises an exception, it means no ip 
			# was found in the line, so we return
			return

		# Create the new ip and store it in the DB
		url =Url(url=url, tags=['malwarepatrol'])

		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = mdlhostlist
import urllib2
from Malcom.model.datatypes import Hostname
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class MDLHosts(Feed):
	"""
	This gets data from http://www.malwaredomainlist.com/hostslist/hosts.txt
	"""
	def __init__(self, name):
		super(MDLHosts, self).__init__(name, run_every="12h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://www.malwaredomainlist.com/hostslist/hosts.txt").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			hostname = toolbox.find_hostnames(line)[0]
		except Exception, e:
			# if find_hostname raises an exception, it means no hostname
			# was found in the line, so we return
			return

		# Create the new URL and store it in the DB
		hostname = Hostname(hostname=hostname, tags=['malwaredomainlist'])

		hostname, status = self.analytics.save_element(hostname, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = mdliplist
import urllib2
from Malcom.model.datatypes import Ip 
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class MDLIpList(Feed):
	"""
	This gets data from http://www.malwaredomainlist.com/hostslist/ip.txt 
	"""
	def __init__(self, name):
		super(MDLIpList, self).__init__(name)
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://www.malwaredomainlist.com/hostslist/ip.txt").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			ip = toolbox.find_ips(line)[0]
		except Exception, e:
			# if find_ip raises an exception, it means no ip 
			# was found in the line, so we return
			return

		# Create the new ip and store it in the DB
		ip = Ip(ip=ip, tags=['mdliplist'])

		ip, status = self.analytics.save_element(ip, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = mdltracker
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Evil, Url
from feed import Feed



class MDLTracker(Feed):

	def __init__(self, name):
		super(MDLTracker, self).__init__(name, run_every="1h")
		self.enabled = True


	def update(self):
		try:
			feed = urllib2.urlopen("http://www.malwaredomainlist.com/hostslist/mdl.xml")
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		children = ["title", "description", "link"]
		main_node = "item"
		

		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
			
		# We create an Evil object. Evil objects are what Malcom uses
		# to store anything it considers evil. Malware, spam sources, etc.
		# Remember that you can create your own datatypes, if need be.

		#print dict
		#return
		mdl = Url()

		# We start populating the Evil() object's attributes with
		# information from the dict we parsed earlier

		mdl['feed'] = "MDLTracker"
		try: 
			mdl['value'] = toolbox.find_urls(dict['description'])[0]
		except Exception,e:
			return
			
		# description
		mdl['description'] = dict['title'] 

		# linkback
		mdl['source'] = dict['link']

		#tags 
		mdl['tags'] = ['ek', 'malware', 'MDLTracker', 'evil']

		# date_retreived
		mdl['date_retreived'] = datetime.datetime.utcnow()

		# Save elements to DB. The status field will contain information on 
		# whether this element already existed in the DB.

		mdl, status = self.analytics.save_element(mdl, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1


########NEW FILE########
__FILENAME__ = openbl
import urllib2
from Malcom.model.datatypes import Ip 
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class OpenblIP(Feed):
	"""
	This gets data fromhttp://www.openbl.org/lists/base.txt 
	"""
	def __init__(self, name):
		super(OpenblIP, self).__init__(name, run_every="12h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://www.openbl.org/lists/base.txt").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			ip = toolbox.find_ips(line)[0]
		except Exception, e:
			# if find_ip raises an exception, it means no ip 
			# was found in the line, so we return
			return

		# Create the new ip and store it in the DB
		ip = Ip(ip=ip, tags=['openblip'])

		ip, status = self.analytics.save_element(ip, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = palevotracker
import urllib2
from Malcom.model.datatypes import Hostname
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class PalevoTracker(Feed):
	"""
	This gets data from https://palevotracker.abuse.ch/?rssfeed
	"""
	def __init__(self, name):
		super(PalevoTracker, self).__init__(name, run_every="1h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("https://palevotracker.abuse.ch/?rssfeed").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			hostname = toolbox.find_hostnames(line)[0]
		except Exception, e:
			# if find_hostname raises an exception, it means no hostname
			# was found in the line, so we return
			return

		# Create the new URL and store it in the DB
		hostname = Hostname(hostname=hostname, tags=['palevotracker'])

		hostname, status = self.analytics.save_element(hostname, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = siri_urz
import urllib2
from Malcom.model.datatypes import Url 
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class SiriUrzVX(Feed):
	"""
	This gets data from http://vxvault.siri-urz.net/URL_List.php
	"""
	def __init__(self, name):
		super(SiriUrzVX, self).__init__(name, run_every="1h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://vxvault.siri-urz.net/URL_List.php").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			url = toolbox.find_urls(line)[0]

		except Exception, e:
			# if find_ip raises an exception, it means no ip 
			# was found in the line, so we return
			return

		# Create the new ip and store it in the DB
		url =Url(url=url, tags=['siri-urz'])

		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = spyeyebinaries
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Evil, Url
from feed import Feed



class SpyEyeBinaries(Feed):

	def __init__(self, name):
		super(SpyEyeBinaries, self).__init__(name, run_every="1h")
		self.enabled = True


	def update(self):
		try:
			feed = urllib2.urlopen("https://spyeyetracker.abuse.ch/monitor.php?rssfeed=binaryurls")
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		children = ["title", "link", "description", "guid"]
		main_node = "item"
		

		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
			
		# We create an Evil object. Evil objects are what Malcom uses
		# to store anything it considers evil. Malware, spam sources, etc.
		# Remember that you can create your own datatypes, if need be.

		evil = Evil()

		# We start populating the Evil() object's attributes with
		# information from the dict we parsed earlier

		evil['feed'] = "SpyEyeBinaries"
		evil['url'] = toolbox.find_urls(dict['description'])[0]
		
		# description
		evil['description'] = dict['link'] + " " + dict['description'] 

		# status
		if dict['description'].find("offline") != -1:
			evil['status'] = "offline"
		else:
			evil['status'] = "online"

		# md5 
		md5 = re.search("MD5 hash: (?P<md5>[0-9a-f]{32,32})",dict['description'])
		if md5 != None:
			evil['md5'] = md5.group('md5')
		else:
			evil['md5'] = "No MD5"
		
		# linkback
		evil['source'] = dict['guid']

		# type
		evil['type'] = 'evil'

		# tags
		evil['tags'] += ['spyeye', 'malware', 'SpyEyeBinaries']

		# date_retreived
		evil['date_retreived'] = datetime.datetime.utcnow()

		# This is important. Values have to be unique, since it's this way that
		# Malcom will identify them in the database.
		# This is probably not the best way, but it will do for now.

		evil['value'] = "SpyEye bot"
		if md5:
			evil['value'] += " (MD5: %s)" % evil['md5']
		else:
			evil['value'] += " (URL: %s)" % evil['url']

		# Save elements to DB. The status field will contain information on 
		# whether this element already existed in the DB.

		evil, status = self.analytics.save_element(evil, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Create an URL element
		url = Url(evil['url'], ['evil', 'SpyEyeBinaries'])

		# Save it to the DB.
		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Connect the URL element to the Evil element
		self.analytics.data.connect(url, evil, 'hosting')


########NEW FILE########
__FILENAME__ = spyeyecnc
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox

from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Hostname, Evil
from feed import Feed



class SpyEyeCnc(Feed):

	def __init__(self, name):
		super(SpyEyeCnc, self).__init__(name, run_every="1h")
		self.enabled = True


	def update(self):
		try:
			feed = urllib2.urlopen("https://spyeyetracker.abuse.ch/monitor.php?rssfeed=tracker")
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		children = ["title", "link", "description", "guid"]
		main_node = "item"
		

		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
			
		# We create an Evil object. Evil objects are what Malcom uses
		# to store anything it considers evil. Malware, spam sources, etc.
		# Remember that you can create your own datatypes, if need be.

		evil = Evil()

		# We start populating the Evil() object's attributes with
		# information from the dict we parsed earlier

		evil['feed'] = "SpyEyeConfigs"
		evil['hostname'] = toolbox.find_hostnames(dict['description'])[0]
		
		# description
		evil['description'] = dict['link'] + " " + dict['description'] 

		# status
		if dict['description'].find("offline") != -1:
			evil['status'] = "offline"
		else:
			evil['status'] = "online"

		# md5 
		md5 = re.search("MD5 hash: (?P<md5>[0-9a-f]{32,32})",dict['description'])
		if md5 != None:
			evil['md5'] = md5.group('md5')
		else:
			evil['md5'] = "No MD5"
		
		# linkback
		evil['source'] = dict['guid']

		# type
		evil['type'] = 'evil'

		# tags
		evil['tags'] += ['spyeye', 'malware', 'SpyEyeCnc']

		# date_retreived
		evil['date_retreived'] = datetime.datetime.utcnow()

		# This is important. Values have to be unique, since it's this way that
		# Malcom will identify them in the database.
		# This is probably not the best way, but it will do for now.

		evil['value'] = "SpyEye Config"
		if md5:
			evil['value'] += " (MD5: %s)" % evil['md5']
		else:
			evil['value'] += " (URL: %s)" % evil['url']

		# Save elements to DB. The status field will contain information on 
		# whether this element already existed in the DB.

		evil, status = self.analytics.save_element(evil, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Create an URL element
		hostname = Hostname(evil['hostname'], ['evil', 'SpyEyeConfigs'])

		# Save it to the DB.
		url, status = self.analytics.save_element(hostname, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Connect the URL element to the Evil element
		self.analytics.data.connect(hostname, evil, 'hosting')


########NEW FILE########
__FILENAME__ = spyeyeconfigs
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Evil, Url
from feed import Feed



class SpyEyeConfigs(Feed):

	def __init__(self, name):
		super(SpyEyeConfigs, self).__init__(name, run_every="1h")
		self.enabled = True


	def update(self):
		try:
			feed = urllib2.urlopen("https://spyeyetracker.abuse.ch/monitor.php?rssfeed=configurls")
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		children = ["title", "link", "description", "guid"]
		main_node = "item"
		

		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
			
		# We create an Evil object. Evil objects are what Malcom uses
		# to store anything it considers evil. Malware, spam sources, etc.
		# Remember that you can create your own datatypes, if need be.

		evil = Evil()

		# We start populating the Evil() object's attributes with
		# information from the dict we parsed earlier

		evil['feed'] = "SpyEyeConfigs"
		evil['url'] = toolbox.find_urls(dict['description'])[0]
		
		# description
		evil['description'] = dict['link'] + " " + dict['description'] 

		# status
		if dict['description'].find("offline") != -1:
			evil['status'] = "offline"
		else:
			evil['status'] = "online"

		# md5 
		md5 = re.search("MD5 hash: (?P<md5>[0-9a-f]{32,32})",dict['description'])
		if md5 != None:
			evil['md5'] = md5.group('md5')
		else:
			evil['md5'] = "No MD5"
		
		# linkback
		evil['source'] = dict['guid']

		# type
		evil['type'] = 'evil'

		# tags
		evil['tags'] += ['spyeye', 'malware', 'SpyEyeConfigs']

		# date_retreived
		evil['date_retreived'] = datetime.datetime.utcnow()

		# This is important. Values have to be unique, since it's this way that
		# Malcom will identify them in the database.
		# This is probably not the best way, but it will do for now.

		evil['value'] = "SpyEye Config"
		if md5:
			evil['value'] += " (MD5: %s)" % evil['md5']
		else:
			evil['value'] += " (URL: %s)" % evil['url']

		# Save elements to DB. The status field will contain information on 
		# whether this element already existed in the DB.

		evil, status = self.analytics.save_element(evil, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Create an URL element
		url = Url(evil['url'], ['evil', 'SpyEyeConfigs'])

		# Save it to the DB.
		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Connect the URL element to the Evil element
		self.analytics.data.connect(url, evil, 'hosting')


########NEW FILE########
__FILENAME__ = spyeyedropzones
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Evil, Url
from feed import Feed



class SpyEyeDropzones(Feed):

	def __init__(self, name):
		super(SpyEyeDropzones, self).__init__(name, run_every="1h")
		self.enabled = True


	def update(self):
		try:
			feed = urllib2.urlopen("https://spyeyetracker.abuse.ch/monitor.php?rssfeed=dropurls")
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		children = ["title", "link", "description", "guid"]
		main_node = "item"
		

		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
			
		# We create an Evil object. Evil objects are what Malcom uses
		# to store anything it considers evil. Malware, spam sources, etc.
		# Remember that you can create your own datatypes, if need be.

		evil = Evil()

		# We start populating the Evil() object's attributes with
		# information from the dict we parsed earlier

		evil['feed'] = "SpyEyeDropzones"
		evil['url'] = toolbox.find_urls(dict['description'])[0]
		
		# description
		evil['description'] = dict['link'] + " " + dict['description'] 

		# status
		if dict['description'].find("offline") != -1:
			evil['status'] = "offline"
		else:
			evil['status'] = "online"

                # md5 
                md5 = re.search("MD5 hash: (?P<md5>[0-9a-f]{32,32})",dict['description'])
                if md5 != None:
                        evil['md5'] = md5.group('md5')
                else:
                        evil['md5'] = "No MD5"

		# linkback
		evil['source'] = dict['guid']

		# type
		evil['type'] = 'evil'

		# tags
		evil['tags'] += ['spyeye', 'malware', 'SpyEyeDropzones']

		# date_retreived
		evil['date_retreived'] = datetime.datetime.utcnow()

		# This is important. Values have to be unique, since it's this way that
		# Malcom will identify them in the database.
		# This is probably not the best way, but it will do for now.

		evil['value'] = "SpyEye Dropzone (%s)"%evil['url']

		# Save elements to DB. The status field will contain information on 
		# whether this element already existed in the DB.

		evil, status = self.analytics.save_element(evil, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Create an URL element
		url = Url(evil['url'], ['evil', 'SpyEyeDropzones'])

		# Save it to the DB.
		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Connect the URL element to the Evil element
		self.analytics.data.connect(url, evil, 'hosting')


########NEW FILE########
__FILENAME__ = torexitnodes
import urllib2
from Malcom.model.datatypes import Ip, Evil
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class TorExitNodes(Feed):
	"""
	This gets data from https://www.dan.me.uk/tornodes
	"""
	def __init__(self, name):
		super(TorExitNodes, self).__init__(name, run_every="12h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("https://www.dan.me.uk/tornodes").read()
		
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False

		start = feed.find('<!-- __BEGIN_TOR_NODE_LIST__ //-->') + len('<!-- __BEGIN_TOR_NODE_LIST__ //-->')
		end = feed.find('<!-- __END_TOR_NODE_LIST__ //-->')

		feed=feed[start:end].replace('\n', '').replace('<br />','\n').replace('&gt;', '>').replace('&lt;', '<').split('\n')
		
		if len(feed) > 10:
			self.status = "OK"
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		fields = line.split('|')

		tornode = Evil(tags=['Tor info'])
		#
		try:
			tornode['ip'] = fields[0]
			tornode['name'] = fields[1]
			tornode['router-port'] = fields[2]
			tornode['directory-port'] = fields[3]
			tornode['flags'] = fields[4]
			tornode['uptime'] = fields[5]
			tornode['version'] = fields[6]
			tornode['contactinfo'] = fields[7]
		except Exception, e:
			return


		tornode['value'] = "Tor: %s (%s)" % (tornode['name'], tornode['ip'])

		try:
			ip = toolbox.find_ips(tornode['ip'])[0]
			ip = Ip(ip=ip, tags=['Tor Node'])
		except Exception, e:
			# if find_ip raises an exception, it means no ip 
			# was found in the line, so we return
			return

		
		# store ip in database
		ip, status = self.analytics.save_element(ip, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# store tornode in database
		tornode, status = self.analytics.save_element(tornode, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		self.analytics.data.connect(ip, tornode, 'Tor node')



########NEW FILE########
__FILENAME__ = urlquery
import urllib2
import re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from Malcom.model.datatypes import Url
from feed import Feed

class UrlQuery(Feed):

	def __init__(self, name):
		super(UrlQuery, self).__init__(name, run_every="1h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://urlquery.net/rss.php")
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False

		children = ["title", "link", "description", "pubDate"]
		main_node = "item"
		
		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)
			
			if dict['description'] != 'No alerts detected.':
			 self.analyze(dict)

		return True

	def analyze(self, dict):
		
		url_re = re.compile('URL</td><td style=\'color:black;vertical-align:top;\'>(.+)</td>')
		
		exploit_kit_re = re.compile('Detected\s(.+)\sexploit\skit', re.IGNORECASE)
		iframe_re = re.compile('iframe\sinjection', re.IGNORECASE)
		cookiebomb_re = re.compile('CookieBomb', re.IGNORECASE)
		dynamicdns_re = re.compile('Dynamic\sDNS', re.IGNORECASE)
		tds_re = re.compile('TDS\sURL', re.IGNORECASE)

		try:
			page_data = urllib2.urlopen(dict['link']).read()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False

		url = url_re.findall(page_data)
		exploit_kit = exploit_kit_re.findall(page_data)
		iframe = iframe_re.findall(page_data)
		cookiebomb = cookiebomb_re.findall(page_data)
		dynamicdns = dynamicdns_re.findall(page_data)
		tds = tds_re.findall(page_data)

		if url:
			dict["link"] = url[0]
		else:
			return False
		
		tags = ['urlquery']
		
		if exploit_kit: tags.append(exploit_kit[0])
		if iframe: tags.append('iframe infection')
		if cookiebomb: tags.append('cookiebomb')
		if dynamicdns: tags.append('dynamic dns') 
		if tds: tags.append('tds')

		# Create the new url and store it in the DB
		url =Url(url=url, tags=tags)

		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1
########NEW FILE########
__FILENAME__ = zeusconfigs
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Evil, Url
from feed import Feed



class ZeusTrackerConfigs(Feed):

	def __init__(self, name):
		super(ZeusTrackerConfigs, self).__init__(name, run_every="1h")
		self.enabled = True


	def update(self):
		try:
			feed = urllib2.urlopen("https://zeustracker.abuse.ch/monitor.php?urlfeed=configs")
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		children = ["title", "link", "description", "guid"]
		main_node = "item"
		

		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
			
		# We create an Evil object. Evil objects are what Malcom uses
		# to store anything it considers evil. Malware, spam sources, etc.
		# Remember that you can create your own datatypes, if need be.

		evil = Evil()

		# We start populating the Evil() object's attributes with
		# information from the dict we parsed earlier

		evil['feed'] = "ZeusTrackerConfigs"
		evil['url'] = toolbox.find_urls(dict['description'])[0]
		
		# description
		evil['description'] = dict['link'] + " " + dict['description'] 

		# status
		if dict['description'].find("offline") != -1:
			evil['status'] = "offline"
		else:
			evil['status'] = "online"

		# md5 
		md5 = re.search("MD5 hash: (?P<md5>[0-9a-f]{32,32})",dict['description'])
		if md5 != None:
			evil['md5'] = md5.group('md5')
		else:
			evil['md5'] = "No MD5"
		
		# linkback
		evil['source'] = dict['guid']

		# type
		evil['type'] = 'evil'

		# tags 
		evil['tags'] += ['zeus', 'malware', 'ZeusTrackerConfigs']

		# date_retreived
		evil['date_retreived'] = datetime.datetime.utcnow()

		# This is important. Values have to be unique, since it's this way that
		# Malcom will identify them in the database.
		# This is probably not the best way, but it will do for now.

		evil['value'] = "ZeuS Config"
		if md5:
			evil['value'] += " (MD5: %s)" % evil['md5']
		else:
			evil['value'] += " (URL: %s)" % evil['url']

		# Save elements to DB. The status field will contain information on 
		# whether this element already existed in the DB.

		evil, status = self.analytics.save_element(evil, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Create an URL element
		url = Url(evil['url'], ['evil', 'ZeusTrackerConfigs'])

		# Save it to the DB.
		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Connect the URL element to the Evil element
		self.analytics.data.connect(url, evil, 'hosting')


########NEW FILE########
__FILENAME__ = zeusdropzones
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Evil, Url
from feed import Feed



class ZeusTrackerDropzones(Feed):

	def __init__(self, name):
		super(ZeusTrackerDropzones, self).__init__(name, run_every="1h")
		self.enabled = True


	def update(self):
		try:
			feed = urllib2.urlopen("https://zeustracker.abuse.ch/monitor.php?urlfeed=dropzones")
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		children = ["title", "link", "description", "guid"]
		main_node = "item"
		

		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
			
		# We create an Evil object. Evil objects are what Malcom uses
		# to store anything it considers evil. Malware, spam sources, etc.
		# Remember that you can create your own datatypes, if need be.

		evil = Evil()

		# We start populating the Evil() object's attributes with
		# information from the dict we parsed earlier

		evil['feed'] = "ZeusTrackerDropzones"
		evil['url'] = toolbox.find_urls(dict['description'])[0]
		
		# description
		evil['description'] = dict['link'] + " " + dict['description'] 

		# status
		if dict['description'].find("offline") != -1:
			evil['status'] = "offline"
		else:
			evil['status'] = "online"

		# md5 
		md5 = re.search("MD5 hash: (?P<md5>[0-9a-f]{32,32})",dict['description'])
		if md5 != None:
			evil['md5'] = md5.group('md5')
		else:
			evil['md5'] = "No MD5"
		
		# linkback
		evil['source'] = dict['guid']

		# type
		evil['type'] = 'evil'

		# tags
		evil['tags'] += ['zeus', 'malware', 'ZeusTrackerDropzones']

		# date_retreived
		evil['date_retreived'] = datetime.datetime.utcnow()

		# This is important. Values have to be unique, since it's this way that
		# Malcom will identify them in the database.
		# This is probably not the best way, but it will do for now.

		evil['value'] = "ZeuS Dropzone"
		if md5:
			evil['value'] += " (MD5: %s)" % evil['md5']
		else:
			evil['value'] += " (URL: %s)" % evil['url']

		# Save elements to DB. The status field will contain information on 
		# whether this element already existed in the DB.

		evil, status = self.analytics.save_element(evil, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Create an URL element
		url = Url(evil['url'], ['evil', 'ZeusTrackerDropzones'])

		# Save it to the DB.
		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Connect the URL element to the Evil element
		self.analytics.data.connect(url, evil, 'hosting')


########NEW FILE########
__FILENAME__ = zeusgameover
import urllib2
from Malcom.model.datatypes import Hostname
from feed import Feed
import Malcom.auxiliary.toolbox as toolbox

class ZeusGameOverDomains(Feed):
	"""
	This gets data from http://virustracker.info/text/ZeuSGameover_Domains.txt
	Sensitivity level: high (for now)
	"""
	def __init__(self, name):
		super(ZeusGameOverDomains, self).__init__(name, run_every="12h")
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("http://virustracker.info/text/ZeuSGameover_Domains.txt").readlines()
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		for line in feed:	
			self.analyze(line)
		return True

	def analyze(self, line):
		if line.startswith('#') or line.startswith('\n'):
			return

		try:
			hostname = toolbox.find_hostnames(line)[0]
		except Exception, e:
			# if find_hostname raises an exception, it means no hostname
			# was found in the line, so we return
			return

		# Create the new URL and store it in the DB
		hostname = Hostname(hostname=hostname, tags=['virustracker.info', 'zeusgameover'])

		hostname, status = self.analytics.save_element(hostname, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1



########NEW FILE########
__FILENAME__ = zeustracker
import urllib2
import datetime, re
from lxml import etree
import Malcom.auxiliary.toolbox as toolbox
from bson.objectid import ObjectId
from bson.json_util import dumps
from Malcom.model.datatypes import Evil, Url
from feed import Feed




class ZeusTrackerBinaries(Feed):

	def __init__(self, name):
		super(ZeusTrackerBinaries, self).__init__(name)
		self.enabled = True

	def update(self):
		try:
			feed = urllib2.urlopen("https://zeustracker.abuse.ch/monitor.php?urlfeed=binaries")
			self.status = "OK"
		except Exception, e:
			self.status = "ERROR: " + str(e)
			return False
		
		children = ["title", "link", "description", "guid"]
		main_node = "item"
		

		tree = etree.parse(feed)
		for item in tree.findall("//%s"%main_node):
			dict = {}
			for field in children:
				dict[field] = item.findtext(field)

			self.analyze(dict)

		return True

	def analyze(self, dict):
			
		# We create an Evil object. Evil objects are what Malcom uses
		# to store anything it considers evil. Malware, spam sources, etc.
		# Remember that you can create your own datatypes, if need be.

		evil = Evil()

		# We start populating the Evil() object's attributes with
		# information from the dict we parsed earlier

		evil['feed'] = "ZeusTrackerBinaries"
		evil['url'] = toolbox.find_urls(dict['description'])[0]
		
		# description
		evil['description'] = dict['link'] + " " + dict['description'] 

		# status
		if dict['description'].find("offline") != -1:
			evil['status'] = "offline"
		else:
			evil['status'] = "online"

		# md5 
		md5 = re.search("MD5 hash: (?P<md5>[0-9a-f]{32,32})",dict['description'])
		if md5 != None:
			evil['md5'] = md5.group('md5')
		else:
			evil['md5'] = "No MD5"
		
		# linkback
		evil['source'] = dict['guid']

		# type
		evil['type'] = 'evil'

		# tags
		evil['tags'] += ['zeus', 'malware', 'ZeusTrackerBinaries']

		# date_retreived
		evil['date_retreived'] = datetime.datetime.utcnow()

		# This is important. Values have to be unique, since it's this way that
		# Malcom will identify them in the database.
		# This is probably not the best way, but it will do for now.

		evil['value'] = "ZeuS bot"
		if md5:
			evil['value'] += " (MD5: %s)" % evil['md5']
		else:
			evil['value'] += " (URL: %s)" % evil['url']

		# Save elements to DB. The status field will contain information on 
		# whether this element already existed in the DB.

		evil, status = self.analytics.save_element(evil, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Create an URL element
		url = Url(evil['url'], ['evil', 'ZeusTrackerBinaries'])

		# Save it to the DB.
		url, status = self.analytics.save_element(url, with_status=True)
		if status['updatedExisting'] == False:
			self.elements_fetched += 1

		# Connect the URL element to the Evil element
		self.analytics.data.connect(url, evil, 'hosting')


########NEW FILE########
__FILENAME__ = datatypes

import datetime, os
import pygeoip

import Malcom.auxiliary.toolbox as toolbox
from Malcom.auxiliary.toolbox import debug_output


class Element(dict):

	default_fields = [('value', "Value"), ('type', "Type"), ('tags', "Tags"), ('date_updated', 'Updated'), ('date_created', 'Created'), ('last_analysis', 'Analyzed') ]	
	
	def __init__(self):
		self['tags'] = []
		self['value'] = None
		self['type'] = None
		self['refresh_period'] = None
		# all elements have to be analysed at least once

		
	def to_dict(self):
		return self.__dict__

	def __getattr__(self, name):
		return self.get(name, None)

	def __setattr__(self, name, value):
		self[name] = value

	def upgrade_tags(self, tags):
		self['tags'].extend(tags)
		self['tags'] = list(set(self['tags']))

	def is_recent(self):
		if 'date_created' not in self:
			return False
		else:
			return (self['date_created'] - datetime.datetime.now()) < datetime.timedelta(minutes=1)


class File(Element):
	
	display_fields = Element.default_fields + [('md5', "MD5"), ('file_type', "Type")]
	default_refresh_period = None
	
	def __init__(self, value='', type='file', tags=[]):
		super(File, self).__init__()
		self['value'] = value
		self['type'] = type
		self['tags'] = tags
		self['refresh_period'] = File.default_refresh_period

	@staticmethod
	def from_dict(d):
		f = File()
		for key in d:
			f[key] = d[key]
		return f

	def analytics(self):
		self['last_analysis'] = datetime.datetime.utcnow()
		# md5
		self['md5'] = ""
		self['file_type'] = "None"
		# analysis does not change with time
		self['next_analysis'] = None
		return []



class Evil(Element):
	
	display_fields = Element.default_fields + []
	default_refresh_period = None

	def __init__(self, value='', type="evil", tags=[]):
		super(Evil, self).__init__()
		self['value'] = value
		self['type'] = type
		self['tags'] = tags + ['evil']
		self['refresh_period'] = Evil.default_refresh_period

	@staticmethod
	def from_dict(d):
		e = Evil()
		for key in d:
			e[key] = d[key]
		return e

	def analytics(self):
		self['last_analysis'] = datetime.datetime.utcnow()
		
		# analysis does not change with time
		self['next_analysis'] = None
		return []


class As(Element):
	display_fields = Element.default_fields + [
										('name', 'Name'),
										('ISP', 'ISP'),
										#('domain', 'Domain'), 
										('asn', 'ASN'),
										('country', 'Country'),
										]
	default_refresh_period = None

	def __init__(self, _as="", tags=[]):
		super(As, self).__init__()
		self['value'] = _as
		self['type'] = 'as'
		self['tags'] = tags
		self['refresh_period'] = As.default_refresh_period



	@staticmethod
	def from_dict(d):
		_as = As()
		for key in d:
			_as[key] = d[key]
		return _as

	def analytics(self):
		self['last_analysis'] = datetime.datetime.utcnow()

		# analysis does not change with time
		self['next_analysis'] = None
		return []



class Url(Element):
	display_fields = Element.default_fields + [
							('scheme', 'Scheme'),
							('hostname', 'Hostname'),
							('path', 'Path'),
							]
	default_refresh_period = None

	def __init__(self, url="", tags=[]):
		super(Url, self).__init__()
		self['value'] = url
		self['tags'] = tags
		self['type'] = 'url'
		self['refresh_period'] = Url.default_refresh_period

	@staticmethod
	def from_dict(d):
		url = Url()
		for key in d:
			url[key] = d[key]
		return url 

	def analytics(self):
		debug_output("(url analytics for %s)" % self['value'])

		new = []
		#link with hostname
		# host = toolbox.url_get_host(self['value'])
		# if host == None:
		# 	self['hostname'] = "No hostname"
		# else:
		# 	self['hostname'] = host

		# find path
		path, scheme, hostname = toolbox.split_url(self['value'])
		self['path'] = path
		self['scheme'] = scheme
		self['hostname'] = hostname

		if toolbox.is_ip(self['hostname']):
			new.append(('host', Ip(toolbox.is_ip(self['hostname']))))
		elif toolbox.is_hostname(self['hostname']):
			new.append(('host', Hostname(toolbox.is_hostname(self['hostname']))))
		else:
			debug_output("No hostname found for %s" % self['value'], type='error')
			return

		self['last_analysis'] = datetime.datetime.utcnow()

		# this information is constant and does not change through time
		# we'll have to change this when we check for URL availability
		self['next_analysis'] = None

		return new











class Ip(Element):
	
	default_refresh_period = 3*24*3600

	display_fields = Element.default_fields + [
						('city', 'City'),
						('postal_code', "ZIP code"),
						('bgp', 'BGP'),
						('ISP', 'ISP'),
						# 'region_name',
						# 'area_code',
						('time_zone', 'TZ'),
						# 'dma_code',
						# ('metro_code', 'Metro code'),
						#'country_code3',
						#'country_name',
						#'longitude',
						('country_code', 'CN'),
						#'latitude',
						#'continent',
						#'date_created',
						#'date_updated',
						#'last_analysis',
						#'_id',
						#'type',
						]

	def __init__(self, ip="", tags=[]):
		super(Ip, self).__init__()
		self['value'] = ip
		self['tags'] = tags
		self['type'] = 'ip'
		# refresh IP geolocation every 72hours
		self['refresh_period'] = Ip.default_refresh_period
			

	@staticmethod
	def from_dict(d):
		ip = Ip()
		for key in d:
			ip[key] = d[key]
		return ip
			

	def analytics(self):
		debug_output( "(ip analytics for %s)" % self['value'])

		# get geolocation info
		try:
			file = os.path.abspath(__file__)
			datatypes_directory = os.path.dirname(file)
			gi = pygeoip.GeoIP(datatypes_directory+'/../auxiliary/geoIP/GeoLiteCity.dat')
			geoinfo = gi.record_by_addr(self.value)
			for key in geoinfo:
				self[key] = geoinfo[key]
		except Exception, e:
			debug_output( "Could not get IP info for %s: %s" %(self.value, e), 'error')

		# get reverse hostname
		
		new = []
		hostname = toolbox.dns_dig_reverse(self['value'])
		
		if hostname:
			new.append(('reverse', Hostname(hostname)))

		self['last_analysis'] = datetime.datetime.utcnow()
		self['next_analysis'] = self['last_analysis'] + datetime.timedelta(seconds=self['refresh_period'])

		return new










class Hostname(Element):
	
	default_refresh_period = 6*3600
	display_fields = Element.default_fields + []

	def __init__(self, hostname="", tags=[]):
		super(Hostname, self).__init__()
		if toolbox.is_hostname(hostname) == hostname:
			self['tags'] = tags
			self['value'] = toolbox.is_hostname(hostname)
			if self['value'][-1:] == ".":
				self['value'] = self['value'][:-1]
			self['type'] = 'hostname'

			# refresh domains every 6 hours
			self['refresh_period'] = Hostname.default_refresh_period
		else:
			return None

	@staticmethod
	def from_dict(d):
		h = Hostname()
		for key in d:
			h[key] = d[key]
		return h 

		
	def analytics(self):

		debug_output( "(host analytics for %s)" % self.value)

		# this should get us a couple of IP addresses, or other hostnames
		self['dns_info'] = toolbox.dns_dig_records(self.value)
		
		new = []

		#get Whois

		self['whois'] = toolbox.whois(self['value'])


		# get DNS info
		for record in self.dns_info:
			if record in ['MX', 'A', 'NS', 'CNAME']:
				for entry in self['dns_info'][record]:
					art = toolbox.find_artifacts(entry) #do this
					for t in art:
						for findings in art[t]:
							if t == 'hostnames':
								new.append((record, Hostname(findings)))
							if t == 'urls':
								new.append((record, Url(findings)))
							if t == 'ips':
								new.append((record, Ip(findings)))

		# is _hostname a subdomain ?

		if len(self.value.split(".")) > 2:
			domain = toolbox.is_subdomain(self.value)
			if domain:
				new.append(('domain', Hostname(domain)))

		self['last_analysis'] = datetime.datetime.utcnow()
		self['next_analysis'] = self['last_analysis'] + datetime.timedelta(seconds=self['refresh_period'])

		return new

DataTypes = {
	'url': Url,
	'ip': Ip,
	'hostname': Hostname,
	'as': As,
	'evil': Evil,
}

########NEW FILE########
__FILENAME__ = model
import dateutil

import threading, os

from pymongo import MongoClient
from pymongo.son_manipulator import SONManipulator
import pygeoip

from bson.objectid import ObjectId

from Malcom.auxiliary.toolbox import *
from Malcom.model.datatypes import Hostname, Url, Ip, As, Evil, DataTypes
import Malcom


class Transform(SONManipulator):
	def transform_incoming(self, son, collection):
		for (key, value) in son.items():
			if isinstance(value, dict):
				son[key] = self.transform_incoming(value, collection)
		return son

	def transform_outgoing(self, son, collection):
		if 'type' in son:
			t = son['type']
			return DataTypes[t].from_dict(son)
		else:
			return son

class Model:

	def __init__(self):
		self._connection = MongoClient()
		self._db = self._connection.malcom
		self._db.add_son_manipulator(Transform())
		# collections
		self.elements = self._db.elements
		self.graph = self._db.graph
		self.sniffer_sessions = self._db.sniffer_sessions
		self.history = self._db.history
		self.public_api = self._db.public_api

		self.gi = pygeoip.GeoIP('Malcom/auxiliary/geoIP/GeoLiteCity.dat')
		self.db_lock = threading.Lock()

		# create indexes
		self.rebuild_indexes()

	def rebuild_indexes(self):
		# create indexes
		debug_output("Rebuliding indexes...", 'model')
		self.elements.ensure_index([('date_created', -1), ('value', 1)])
		self.elements.ensure_index('value')
		self.elements.ensure_index('tags')
		self.graph.ensure_index([('src', 1), ('dst', 1)])
		self.graph.ensure_index('src')
		self.graph.ensure_index('dst')

	def stats(self):
		stats = "DB loaded with %s elements\n" % self._db.elements.count()
		stats += "Graph has %s edges" % self._db.graph.count()
		return stats

	def find(self, query={}):
		return self.elements.find(query)

	def find_one(self, oid):
		return self.elements.find_one(oid)

	def clear_db(self):
		for c in self._db.collection_names():
			if c != "system.indexes":
				self._db[c].drop()
	
	def list_db(self):
		for e in self.elements.find():
			debug_output(e)


	def save_sniffer_session(self, session):
		dict = { 
			'name': session.name,
			'filter': session.filter,
			'intercept_tls': session.intercept_tls,
			'pcap': True,
			'packet_count': session.packet_count,
			}
		status = self.sniffer_sessions.update({'name': dict['name']}, dict, upsert=True)
		return status

	def get_sniffer_session(self, session_name):
		session = self.sniffer_sessions.find_one({'name': session_name})
		return session

	def del_sniffer_session(self, session_name):

		session = self.sniffer_sessions.find_one({'name': session_name})
			
		filename = session['name'] + ".pcap"
				
		try:
			os.remove(Malcom.config['SNIFFER_DIR'] + "/" + filename)
		except Exception, e:
			print e

		self.sniffer_sessions.remove({'name': session_name})

		return True

	def get_sniffer_sessions(self):
		return [s for s in self.sniffer_sessions.find()]
	
	def save(self, element, with_status=False):
	
		tags = []
		if 'tags' in element:
			tags = element['tags']
			del element['tags'] 	# so tags in the db do not get overwritten

		if '_id' in element:
			del element['_id']

		status = self.elements.update({'value': element['value']}, {"$set" : element, "$addToSet": {'tags' : {'$each': tags}}}, upsert=True)
		saved = self.elements.find({'value': element['value']})

		assert(saved.count() == 1) # check that elements are unique in the db
		saved = saved[0]

		if status['updatedExisting'] == True:
			debug_output("(updated %s %s)" % (saved.type, saved.value), type='model')
			assert saved.get('date_created', None) != None
		else:
			debug_output("(added %s %s)" % (saved.type, saved.value), type='model')
			saved['date_created'] = datetime.datetime.utcnow()
			saved['next_analysis'] = datetime.datetime.utcnow()

		saved['date_updated'] = datetime.datetime.utcnow()

		self.elements.save(saved)
		assert saved['date_created'] != None and saved['date_updated'] != None

		if not with_status:
			return saved
		else:
			return saved, status

	def remove(self, element_id):
		return self.elements.remove({'_id' : ObjectId(element_id)})

	def exists(self, element):
		return self.elements.find_one({ 'value': element.value })


	def connect(self, src, dst, attribs="", commit=True):

			if not src or not dst:
				return None
			
			conn = self.graph.find_one({ 'src': ObjectId(src._id), 'dst': ObjectId(dst._id) })
			if conn:
				conn['attribs'] = attribs
			else:
				conn = {}
				conn['src'] = src._id
				conn['dst'] = dst._id
				conn['attribs'] = attribs   
				debug_output("(linked %s to %s [%s])" % (str(src._id), str(dst._id), attribs), type='model')
			if commit:
				self.graph.save(conn)
			return conn

	def add_feed(self, feed):
		elts = feed.get_info()
	  
		for e in elts:
			self.malware_add(e,e['tags'])

	def get_neighbors_id(self, elts, query={}, include_original=True):

		original_ids = [e['_id'] for e in elts]

		new_edges = self.graph.find({'$or': [
				{'src': {'$in': original_ids}}, {'dst': {'$in': original_ids}}
			]})
		_new_edges = self.graph.find({'$or': [
				{'src': {'$in': original_ids}}, {'dst': {'$in': original_ids}}
			]})


		ids = {}

		for e in _new_edges:
			ids[e['src']] = e['src']
			ids[e['dst']] = e['dst']

		ids = [i for i in ids]

		if include_original:
			q = {'$and': [{'_id': {'$in': ids}}, query]}
			original = {'$or': [q, {'_id': {'$in': original_ids}}]}
			new_nodes = self.elements.find(original)
		else:
			new_nodes = self.elements.find({'$and': [{'_id': {'$in': ids}}, query]})

		new_nodes = [n for n in new_nodes]
		new_edges = [e for e in new_edges]
		
		return new_nodes, new_edges
			

	def get_neighbors_elt(self, elt, query={}, include_original=True):

		if not elt:
			return [], []

		d_new_edges = {}
		new_edges = []
		d_ids = { elt['_id']: elt['_id'] }

		# get all links to / from the required element

		for e in self.graph.find({'src': elt['_id']}):
			d_new_edges[e['_id']] = e
			d_ids[e['dst']] = e['dst']
		for e in self.graph.find({'dst': elt['_id']}):
			d_new_edges[e['_id']] = e
			d_ids[e['src']] = e['src']
		

		# get all IDs of the new nodes that have been discovered
		ids = [d_ids[i] for i in d_ids]

		# get the new node objects
		nodes = {}
		for node in self.elements.find( {'$and' : [{ "_id" : { '$in' : ids }}, query]}):
			nodes[node['_id']] = node
		
		# get incoming links (node weight)
		destinations = [d_new_edges[e]['dst'] for e in d_new_edges]
		for n in nodes:
			nodes[n]['incoming_links'] = destinations.count(nodes[n]['_id'])

		# get nodes IDs
		nodes_id = [nodes[n]['_id'] for n in nodes]
		# get links for new nodes, in case we use them
		for e in self.graph.find({'src': { '$in': nodes_id }}):
			d_new_edges[e['_id']] = e
		for e in self.graph.find({'dst': { '$in': nodes_id }}):
			d_new_edges[e['_id']] = e

		# if not include_original:
		# 	del nodes[elt['_id']]
		
		# create arrays
		new_edges = [d_new_edges[e] for e in d_new_edges]
		nodes = [nodes[n] for n in nodes]

		# display 
		for e in nodes:
			e['fields'] = e.display_fields

		return nodes, new_edges

	#Public API operations

	def add_tag_to_key(self, apikey, tag):
		k = self.public_api.find_one({'api-key': apikey})
		if not k:
			k = self.public_api.save({'api-key': apikey, 'available-tags': [tag]})
		else:
			if tag not in k['available-tags']:
				k['available-tags'].append(tag)
				self.public_api.save(k)

	def get_tags_for_key(self, apikey):
		tags = self.public_api.find_one({'api-key': apikey})
		if not tags:
			return []
		else:
			return tags.get('available-tags', [])


########NEW FILE########
__FILENAME__ = flow
from scapy.all import *
from scapy.error import Scapy_Exception
import pwd, os, sys, time, threading, string
from bson.json_util import dumps, loads
from Malcom.model.datatypes import Url, Hostname, Ip
import Malcom.auxiliary.toolbox as toolbox



class Decoder(object):

	@staticmethod
	def decode_flow(flow):
		data = None

		#if flow.src_port == 80: # probable HTTP response
		data = Decoder.HTTP_response(flow.payload)
		if data: return data
		#if flow.dst_port == 80: # probable HTTP request
		data = Decoder.HTTP_request(flow.payload)
		if data: return data
		
		if flow.tls:
			#if flow.dst_port == 443: # probabl HTTPs request
			data = Decoder.HTTP_request(flow.cleartext_payload, secure=True)
			if data: return data
			#if flow.src_port == 443: # probabl HTTPs request
			data = Decoder.HTTP_response(flow.cleartext_payload)
			if data: return data

		return False

	@staticmethod
	def HTTP_request(payload, secure=False):
		data = {}
		request = re.search(r'(?P<method>GET|HEAD|POST|PUT|DELETE|TRACE|OPTIONS|CONNECT|PATCH) (?P<URI>\S*) HTTP', payload)
		if not request:
			return False
		else:
			data['method'] = request.group("method")
			data['uri'] = request.group('URI')
			host = re.search(r'Host: (?P<host>\S+)', payload)
			data['host'] = host.group('host') if host else "N/A"
			data['flow_type'] = "http_request"
			
			if secure:
				data['scheme'] = 'https://'
				data['type'] = 'HTTP request (TLS)'
			else:
				data['scheme'] = 'http://'
				data['type'] = 'HTTP request'

			data['url'] = data['scheme'] + data['host'] + data['uri']
			data['info'] = "%s request for %s" % (data['method'], data['url'])
			
			return data

	@staticmethod
	def HTTP_response(payload):
		data = {}
		response = re.search(r'(HTTP.* (?P<status_code>\d{3,3}))', payload)
		if not response:
			return False
		else:
			data['flow_type'] = 'http_response'
			data['status'] = response.group("status_code")
			encoding = re.search(r'Transfer-Encoding: (?P<encoding>\S+)', payload)
			data['encoding'] = encoding.group('encoding') if encoding else "N/A"
			response = re.search(r'\r\n\r\n(?P<response>[\S\s]*)', payload)
			#data['response'] = response.group('response') if response else "N/A"

			data['type'] = 'HTTP response'
			data['info'] = 'Status: %s' % (data['status'])
			
			# # chunk_encoding
			# try:
			# 	if response and encoding:
			# 		if data['encoding'] == 'chunked':
			# 			decoded = ""
			# 			encoded = data['response']
			# 			cursor = 0
			# 			chunk_size = -1
			# 			while chunk_size != 0:
			# 				chunk_size = int(encoded[cursor:cursor+encoded[cursor:].find('\r\n')], 16)
			# 				cursor += encoded[cursor:].find('\r\n') + 2
			# 				decoded += encoded[cursor:chunk_size+cursor]
			# 				cursor += chunk_size + 2
			# 			data['response'] = decoded
						
			# except Exception, e:
			# 	toolbox.debug_output("Could not decode chunked HTTP response: %s" % e, "error")
			
			return data
	

class Flow(object):
	"""docstring for Flow"""
	
	@staticmethod
	def flowid(pkt):
		IP_layer = IP if IP in pkt else IPv6
		fid = "flowid--%s-%s--%s-%s" % (pkt[IP_layer].src, pkt[IP_layer].sport, pkt[IP_layer].dst, pkt[IP_layer].dport)
		return fid.replace('.','-')

	@staticmethod
	def pkt_handler(pkt, flows):
		if IP not in pkt:
			return

		flowid = Flow.flowid(pkt)
		if flowid not in flows:
			flows[flowid] = Flow(pkt)
		else:
			flows[flowid].add_pkt(pkt)

	def reverse_flowid(self):
		fid = "flowid--%s-%s--%s-%s" % (self.dst_addr, self.dst_port, self.src_addr, self.src_port)
		return fid.replace('.','-')		

	def __init__(self, pkt):
		self.packets = []
		self.tls = False # until proven otherwise
		self.cleartext_payload = ""

		# set initial timestamp
		self.timestamp = pkt.time

		# addresses
		self.src_addr = pkt[IP].src 
		self.dst_addr = pkt[IP].dst

		self.src_port = pkt[IP].sport
		self.dst_port = pkt[IP].dport
	
		if pkt.getlayer(IP).proto == 6:
			self.protocol = 'TCP'
			self.buffer = [] # buffer for out-of-order packets
		elif pkt.getlayer(IP).proto == 17:
			self.protocol = 'UDP'
		else:
			self.protocol = "???"

		# see if we need to reconstruct flow (i.e. check SEQ numbers)
		self.payload = ""
		self.decoded_flow = None
		self.data_transfered = 0
		self.packet_count = 0
		self.fid = Flow.flowid(pkt)


		self.add_pkt(pkt)

		

	def extract_elements(self):
		if self.decoded_flow and self.decoded_flow['flow_type'] == 'http_request':
			return {'url': self.decoded_flow['url'], 'host': self.decoded_flow['host'], 'method': self.decoded_flow['method']}
		else:
			return None
	
	def add_pkt(self, pkt):
		self.packet_count += 1
		if self.protocol == 'TCP' and not self.tls:
			self.reconstruct_flow(pkt)
		elif self.protocol == 'UDP':
			self.packets += pkt
			self.payload += str(pkt[UDP].payload)
			self.data_transfered += len(self.payload)
		else:
			self.packets += pkt


	def reconstruct_flow(self, pkt):
		assert TCP in pkt

		# deal with all packets or only new connections ?

		if pkt[TCP].flags & 0x02:			# SYN flag detected
			self.seq = pkt[TCP].seq
			self.initial_seq = pkt[TCP].seq

			if Raw in pkt:
				self.payload += pkt[Raw].load
				self.data_transfered += len(pkt[Raw].load)

			self.packets += pkt
			self.seq += 1

		elif len(self.packets) > 0:
			self.buffer += pkt
			while self.check_buffer():
				pass

	def check_buffer(self):
		for i, pkt in enumerate(self.buffer):
			last = self.packets[-1:][0]
			
			# calculate expected seq
			if Raw in last:
				next_seq = self.seq + len(last[Raw].load)
			else:
				next_seq = self.seq
			
			# the packet's sequence number matches
			if next_seq == pkt[TCP].seq:
				
				# pop from buffer
				self.packets += self.buffer.pop(i)
				self.seq = pkt[TCP].seq

				if Raw in pkt:
					self.payload += str(pkt[Raw].load)
					self.data_transfered += len(pkt[Raw].load)
				
				return True

		return False

	def get_statistics(self):

		update = {
				'timestamp': self.timestamp,
				'fid' : self.fid,
				'src_addr': self.src_addr,
				'src_port': self.src_port,
				'dst_addr': self.dst_addr, 
				'dst_port': self.dst_port, 
				'protocol': self.protocol,
				'packet_count': self.packet_count,
				'data_transfered': self.data_transfered,
				'tls': self.tls,
				}

		# we'll use the type and info fields
		self.decoded_flow = Decoder.decode_flow(self)
		update['decoded_flow'] = self.decoded_flow

		return update

	def get_payload(self, encoding='web'):

		if self.tls:
			payload = self.cleartext_payload
		else:
			payload = self.payload

		if encoding == 'web':
			return unicode(payload, errors='replace')
		if encoding == 'raw':
			return payload
			

	def print_statistics(self):
		print "%s:%s  ->  %s:%s (%s, %s packets, %s buff)" % (self.src_addr, self.src_port, self.dst_addr, self.dst_port, self.protocol, len(self.packets), len(self.buffer))



if __name__ == '__main__':
	
	filename = sys.argv[1]
	flows = {}
	sniff(prn=lambda x: Flow.pkt_handler(x, flows), offline=filename, store=0)

	for fid in flows:
		flows[fid].print_statistics()





########NEW FILE########
__FILENAME__ = netsniffer
from scapy.all import *
from scapy.error import Scapy_Exception
import pwd, os, sys, time, threading
from bson.json_util import dumps

from bson.objectid import ObjectId


from Malcom.networking.flow import Flow
from Malcom.auxiliary.toolbox import debug_output
from Malcom.networking.tlsproxy.tlsproxy import MalcomTLSProxy
import Malcom

types = ['hostname', 'ip', 'url', 'as', 'malware']
rr_codes = {"1": "A", "2": "NS", "5": "CNAME", "15": "MX"}

NOTROOT = "nobody"


class Sniffer(dict):

	def __init__(self, analytics, name, remote_addr, filter, intercept_tls=False, ws=None, filter_restore=None):
		
		self.analytics = analytics
		self.name = name
		self.ws = ws
		self.ifaces = Malcom.config['IFACES']
		filter_ifaces = ""
		for i in self.ifaces:
			filter_ifaces += " and not host %s " % self.ifaces[i]
		self.filter = "ip and not host 127.0.0.1 and not host %s %s" % (remote_addr, filter_ifaces)

		if filter != "":
			self.filter += " and (%s)" % filter
		self.stopSniffing = False

		if filter_restore:
			self.filter = filter_restore
		
		self.thread = None
		self.public = False
		self.pcap = False
		self.pcap_filename = self.name + '.pcap'
		self.pkts = []
		self.packet_count = 0

		# nodes, edges, their values, their IDs
		self.nodes = []
		self.edges = []
		self.nodes_ids = []
		self.nodes_values = []
		self.nodes_pk = []
		self.edges_ids = []

		# flows
		self.flows = {}
		
		self.intercept_tls = intercept_tls
		if self.intercept_tls:
			debug_output("[+] Intercepting TLS")
			self.tls_proxy = Malcom.tls_proxy
			self.tls_proxy.add_flows(self.flows)
		else:
			debug_output("[-] No TLS interception")

	def load_pcap(self):

		filename = self.pcap_filename
		debug_output("Loading PCAP from %s " % filename)
		self.pkts += self.sniff(stopper=self.stop_sniffing, filter=self.filter, prn=self.handlePacket, stopperTimeout=1, offline=Malcom.config['SNIFFER_DIR']+"/"+filename)	
		
		debug_output("Loaded %s packets from file." % len(self.pkts))

		return True

	def run(self):
		debug_output("[+] Sniffing session %s started" % self.name)
		debug_output("[+] Filter: %s" % self.filter)
		self.stopSniffing = False
		
		if self.pcap:
			self.load_pcap()
		elif not self.public:
			print self.filter
			self.pkts += self.sniff(stopper=self.stop_sniffing, filter=self.filter, prn=self.handlePacket, stopperTimeout=1)

		self.generate_pcap()
		
		debug_output("[+] Sniffing session %s stopped" % self.name)

		return 

	def update_nodes(self):
		return { 'query': {}, 'nodes': self.nodes, 'edges': self.edges }

	def flow_status(self):
		data = {}
		data['flows'] = []
		for fid in self.flows:
			data['flows'].append(self.flows[fid].get_statistics())
		data['flows'] = sorted(data['flows'], key= lambda x: x['timestamp'])
		return data

	def start(self, remote_addr, public=False):
		self.public = public
		self.thread = threading.Thread(None, self.run, None)
		self.thread.start()
		
	def stop(self):
		self.stopSniffing = True
		if self.thread:
			self.thread.join()
		time.sleep(0.5)
		return True
		

	def status(self):
		if self.thread:
			return self.thread.is_alive()
		else:
			return False

	def generate_pcap(self):
		if len (self.pkts) > 0:
			debug_output("Generating PCAP for %s (length: %s)" % (self.name, len(self.pkts)))
			filename = Malcom.config['SNIFFER_DIR'] + "/" + self.pcap_filename
			wrpcap(filename, self.pkts)
			debug_output("Saving session to DB")
			self.analytics.data.save_sniffer_session(self)
	
	def checkIP(self, pkt):

		source = {}
		dest = {}
		new_elts = []
		new_edges = []

		# get IP layer
		IP_layer = IP if IP in pkt else IPv6
		if IP_layer == IPv6: return None, None # tonight is not the night to add ipv6 support
	
		if IP_layer in pkt:	
			source['ip'] = pkt[IP_layer].src
			dest['ip'] = pkt[IP_layer].dst
		else: return None, None

		if TCP in pkt or UDP in pkt:
			source['port'] = pkt[IP_layer].sport
			dest['port'] = pkt[IP_layer].dport
		else: return None, None

		ips = [source['ip'], dest['ip']]
		ids = []
		
		for ip in ips:

			if ip not in self.nodes_values:
				ip = self.analytics.add_text([ip], ['sniffer', self.name])

				if ip == []: continue # tonight is not the night to add ipv6 support

				# do some live analysis
				new = ip.analytics()
				for n in new:
					saved = self.analytics.save_element(n[1])
					self.nodes_ids.append(saved['_id'])
					self.nodes_values.append(saved['value'])
					self.nodes.append(saved)
					new_elts.append(saved)
					
					#do the link
					conn = self.analytics.data.connect(ip, saved, n[0])
					if conn not in self.edges:
						self.edges.append(conn)
						new_edges.append(conn)

				
				self.nodes_ids.append(ip['_id'])
				self.nodes_values.append(ip['value'])
				self.nodes.append(ip)
				new_elts.append(ip)
			else:
				ip = [e for e in self.nodes if e['value'] == ip][0]

			ids.append(ip['_id'])


		# temporary "connection". IPs are only connceted because hey are communicating with each other
		oid = "$oid"
		#conn = {'attribs': '%s > %s' %(source['port'], dest['port']), 'src': ids[0], 'dst': ids[1], '_id': { oid: str(ids[0])+str(ids[1])}}
		conn = {'attribs': 'dport:%s' % dest['port'], 'src': ids[0], 'dst': ids[1], '_id': { oid: str(ids[0])+str(ids[1])}}
		
		if conn not in self.edges:
			self.edges.append(conn)
			new_edges.append(conn)
		
		return new_elts, new_edges

	def checkDNS(self, pkt):
		new_elts = []
		new_edges = []

		# intercept DNS responses (these contain names and IPs)
		IP_layer = IP if IP in pkt else IPv6
		if DNS in pkt and pkt[IP_layer].sport == 53:

			#deal with the original DNS request
			question = pkt[DNS].qd.qname

			if question not in self.nodes_values:
				_question = self.analytics.add_text([question], ['sniffer', self.name]) # log it to db (for further reference)
				if _question:
					debug_output("Caught DNS question: %s" % (_question['value']))
					self.nodes_ids.append(_question['_id'])
					self.nodes_values.append(_question['value'])
					self.nodes.append(_question)
					new_elts.append(_question)

			else:
				_question = [e for e in self.nodes if e['value'] == question][0]

			#debug_output("[+] DNS reply caught (%s answers)" % pkt[DNS].ancount)
			

			response_types = [pkt[DNS].an, pkt[DNS].ns, pkt[DNS].ar]
			response_counts = [pkt[DNS].ancount, pkt[DNS].nscount, pkt[DNS].arcount]

			for i, response in enumerate(response_types):
				if response_counts[i] == 0: continue
				
				debug_output("[+] DNS replies caught (%s answers)" % response_counts[i])			
				#for i in xrange(pkt[DNS].ancount): # cycle through responses and add records to graph

				for rr in xrange(response_counts[i]):
					if response[rr].type not in [1, 2, 5, 15]:
						debug_output('No relevant records in reply')
						continue

					rr = response[rr]

					rrname = rr.rrname
					rdata = rr.rdata
					
					# check if rrname ends with '.'
					if rrname[-1:] == ".":
						rrname = rrname[:-1]
					
					# check if we haven't seen these already
					if rrname not in self.nodes_values:
						_rrname = self.analytics.add_text([rrname], ['sniffer', self.name]) # log every discovery to db
						if _rrname != []:
							self.nodes_ids.append(_rrname['_id'])
							self.nodes_values.append(_rrname['value'])
							self.nodes.append(_rrname)
							new_elts.append(_rrname)
					else:
						_rrname = [e for e in self.nodes if e['value'] == rrname][0]

					if rdata not in self.nodes_values:
						_rdata = self.analytics.add_text([rdata], ['sniffer', self.name]) # log every discovery to db
						if _rdata != []: # avoid linking elements if only one is found
							self.nodes_ids.append(_rdata['_id'])
							self.nodes_values.append(_rdata['value'])
							self.nodes.append(_rdata)
							new_elts.append(_rdata)

							# do some live analysis
							# new = _rdata.analytics()
							# for n in new:
							# 	saved = self.analytics.save_element(n[1])
							# 	self.nodes_ids.append(saved['_id'])
							# 	self.nodes_values.append(saved['value'])
							# 	self.nodes.append(saved)
							# 	new_elts.append(saved)
								
							# 	#do the link
							# 	conn = self.analytics.data.connect(_rdata, saved, n[0])
							# 	if conn not in self.edges:
							# 		self.edges.append(conn)
							# 		new_edges.append(conn)
					else:
						_rdata = [e for e in self.nodes if e['value'] == rdata][0]

					

					# we can use a real connection here
					# conn = {'attribs': 'A', 'src': _rrname['_id'], 'dst': _rdata['_id'], '_id': { '$oid': str(_rrname['_id'])+str(_rdata['_id'])}}
					
					# if two elemnts are found, link them
					if _rrname != [] and _rdata != []:
						debug_output("Caught DNS answer: %s -> %s" % ( _rrname['value'], _rdata['value']))
						debug_output("Added %s, %s" %(rrname, rdata))
						conn = self.analytics.data.connect(_rrname, _rdata, rr_codes[str(rr.type)], True)
						if conn not in self.edges:
							self.edges.append(conn)
							new_edges.append(conn)
					else:
						debug_output("Don't know what to do with '%s' and '%s'" % (_rrname, _rdata), 'error')
						pkt.display()
						
					# conn = self.analytics.data.connect(_question, elt, "resolve", True)
					# conn = {'attribs': 'query', 'src': _question['_id'], 'dst': _rdata['_id'], '_id': { '$oid': str(_rrname['_id'])+str(_rdata['_id']) } }
					# if conn not in self.edges:
					# 		self.edges.append(conn)
					# 		new_edges.append(conn)

		return new_elts, new_edges
		
	def checkHTTP(self, flow):
		# extract elements from payloads

		new_elts = []
		new_edges = []

		http_elts = flow.extract_elements()
		
		if http_elts:

			url = self.analytics.add_text([http_elts['url']])
			if url['value'] not in self.nodes_values:
				self.nodes_ids.append(url['_id'])
				self.nodes_values.append(url['value'])
				self.nodes.append(url)
				new_elts.append(url)

			host = self.analytics.add_text([http_elts['host']])
			if host['value'] not in self.nodes_values:
				self.nodes_ids.append(host['_id'])
				self.nodes_values.append(host['value'])
				self.nodes.append(host)
				new_elts.append(host)
			
			# in this case, we can save the connection to the DB since it is not temporary
			#conn = {'attribs': http_elts['method'], 'src': host['_id'], 'dst': url['_id'], '_id': { '$oid': str(host['_id'])+str(url['_id'])}}
			conn = self.analytics.data.connect(host, url, "host")

			if conn not in self.edges:
				self.edges.append(conn)
				new_edges.append(conn)

		return new_elts, new_edges


	def handlePacket(self, pkt):

		IP_layer = IP if IP in pkt else IPv6 # add IPv6 support another night...
		if IP_layer == IPv6: return

		self.pkts.append(pkt)
		self.packet_count += 1

		elts = []
		edges = []

		# STANDARD PACKET ANALYSIS - extract IP addresses and domain names
		# the magic for extracting elements from packets happens here

		new_elts, new_edges = self.checkIP(pkt)
		if new_elts:
			elts += new_elts
		if new_edges:
			edges += new_edges

		new_elts, new_edges = self.checkDNS(pkt)
		if new_elts:
			elts += new_elts
		if new_edges:
			edges += new_edges

		
		# FLOW ANALYSIS - reconstruct TCP flow if possible
		# do flow analysis here, if necessary - this will be replaced by dpkt's magic

		if TCP in pkt or UDP in pkt:

			Flow.pkt_handler(pkt, self.flows)
			flow = self.flows[Flow.flowid(pkt)]
			self.send_flow_statistics(flow)	
			
			new_elts, new_edges = self.checkHTTP(flow)

			if new_elts:
				elts += new_elts
			if new_edges:
				edges += new_edges			

		# end flow analysis

		
		# TLS MITM - intercept TLS communications and send cleartext to malcom
		# We want to be protocol agnostic (HTTPS, FTPS, ***S). For now, we choose which 
		# connections to intercept based on destination port number
		
		# We could also catch ALL connections and MITM only those which start with
		# a TLS handshake

		tlsports = [443]
		if TCP in pkt and pkt[TCP].flags & 0x02 and pkt[TCP].dport in tlsports and not self.pcap and self.intercept_tls: # of course, interception doesn't work with pcaps
			# mark flow as tls			
			flow.tls = True

			# add host / flow tuple to the TLS connection list
			debug_output("TLS SYN to from: %s:%s -> %s:%s" % (pkt[IP].src, pkt[TCP].sport, pkt[IP].dst, pkt[TCP].dport))
			# this could actually be replaced by only flow
			self.tls_proxy.hosts[(pkt[IP].src, pkt[TCP].sport)] = (pkt[IP].dst, pkt[TCP].dport, flow.fid) 

			
		if elts != [] or edges != []:
			self.send_nodes(elts, edges)
		if self.pcap:
			time.sleep(0.1)

	def send_flow_statistics(self, flow):
		data = {}
		data['flow'] = flow.get_statistics()
		data['type'] = 'flow_statistics_update'
		if self.ws:
			try:
				self.ws.send(dumps(data))
			except Exception, e:
				debug_output("Could not send flow statistics: %s" % e)

	def send_nodes(self, elts=[], edges=[]):
		
		for e in elts:
			e['fields'] = e.display_fields

		data = { 'querya': {}, 'nodes':elts, 'edges': edges, 'type': 'nodeupdate'}
		try:
			if (len(elts) > 0 or len(edges) > 0) and self.ws:
				self.ws.send(dumps(data))
		except Exception, e:
			debug_output("Could not send nodes: %s" % e)
		
	def stop_sniffing(self):
		return self.stopSniffing

	def sniff(self, count=0, store=1, offline=None, prn = None, lfilter=None, L2socket=None, timeout=None, stopperTimeout=None, stopper = None, *arg, **karg):
		"""Sniff packets
			sniff([count=0,] [prn=None,] [store=1,] [offline=None,] [lfilter=None,] + L2ListenSocket args) -> list of packets

			  count: number of packets to capture. 0 means infinity
			  store: wether to store sniffed packets or discard them
				prn: function to apply to each packet. If something is returned,
					 it is displayed. Ex:
					 ex: prn = lambda x: x.summary()
			lfilter: python function applied to each packet to determine
					 if further action may be done
					 ex: lfilter = lambda x: x.haslayer(Padding)
			offline: pcap file to read packets from, instead of sniffing them
			timeout: stop sniffing after a given time (default: None)
			stopperTimeout: break the select to check the returned value of 
					 stopper() and stop sniffing if needed (select timeout)
			stopper: function returning true or false to stop the sniffing process
			L2socket: use the provided L2socket
		"""
		c = 0

		if offline is None:
			if L2socket is None:
				L2socket = conf.L2listen
			s = L2socket(type=ETH_P_ALL, *arg, **karg)
		else:
			s = PcapReader(offline)

		lst = []
		if timeout is not None:
			stoptime = time.time()+timeout
		remain = None

		if stopperTimeout is not None:
			stopperStoptime = time.time()+stopperTimeout
		remainStopper = None
		while 1:
			try:
				if not stopper:
					break

				if timeout is not None:
					remain = stoptime-time.time()
					if remain <= 0:
						break

				if stopperTimeout is not None:
					remainStopper = stopperStoptime-time.time()
					if remainStopper <=0:
						if stopper and stopper():
							break
						stopperStoptime = time.time()+stopperTimeout
						remainStopper = stopperStoptime-time.time()

					sel = select([s],[],[],remainStopper)
					if s not in sel[0]:
						if stopper and stopper():
							break
				else:
					sel = select([s],[],[],remain)

				if s in sel[0]:
					p = s.recv(MTU)
					if not stopper:
						break
					if p is None:
						break
					if lfilter and not lfilter(p):
						continue
					if store:
						lst.append(p)
					c += 1
					if prn:
						r = prn(p)
						if r is not None:
							print r
					if count > 0 and c >= count:
						break
			except KeyboardInterrupt:
				break
		s.close()
		return plist.PacketList(lst,"Sniffed")
########NEW FILE########
__FILENAME__ = tlsproxy
#!/usr/bin/env python
# coding: utf-8
# inspired from http://musta.sh/2012-03-04/twisted-tcp-proxy.html
 
import sys, threading
from time import sleep
from collections import deque
 
from twisted.internet import defer, ssl
from twisted.internet import protocol
from twisted.internet import reactor
 
class ProxyClientProtocol(protocol.Protocol):
	"""This is the Protocol responsible for dealing with the end host, and forwarding back data to the proxy"""
	def connectionMade(self):
		self.cli_queue = self.factory.cli_queue
		self.cli_queue.get().addCallback(self.serverDataReceived)
 
	def serverDataReceived(self, chunk):
		if chunk is False:
			self.cli_queue = None
			self.factory.continueTrying = False
			self.transport.loseConnection()
		elif self.cli_queue:
			self.transport.write(chunk)
			self.cli_queue.get().addCallback(self.serverDataReceived)
		else:
			self.factory.cli_queue.put(chunk)
 
	def dataReceived(self, chunk):
		self.factory.srv_queue.put(chunk)
 
	def connectionLost(self, why):
		if self.cli_queue:
			self.cli_queue = None
 
 
class ProxyClientFactory(protocol.ReconnectingClientFactory):
	"""This is the Factory responsible for generating connection protocols towards the destination host"""
	maxDelay = 10
	continueTrying = True
	protocol = ProxyClientProtocol
 
	def __init__(self, srv_queue, cli_queue):
		self.srv_queue = srv_queue
		self.cli_queue = cli_queue

 
class ProxyServer(protocol.Protocol):
	"""This is the "server protocols" class, which will conncect to a remote host
	and forward data to and from both endpoints (i.e. proxy)"""
	def __init__(self):
		self.clientFactory = None
		self.client_payload = ""
		self.server_payload = ""
		
	def connectionMade(self):
		self.srv_queue = defer.DeferredQueue()
		self.cli_queue = defer.DeferredQueue()
		self.srv_queue.get().addCallback(self.clientDataReceived)

		src_addr = self.transport.getPeer().host
		src_port = self.transport.getPeer().port

		tuples = self.factory.hosts.get((src_addr, src_port), False)

		# check if we've got a new tuple to connect to and
		# if we're still waiting for connections or not
		while not tuples and self.factory.proxy.running: 
			sleep(0.1)
			tuples = self.factory.hosts.get((src_addr, src_port), False)

		if tuples:
			self.dst_addr, self.dst_port, dst_fid = tuples
			self.dst_flow = self.factory.get_flow(dst_fid)
			print "Connecting to %s:%s" % (self.dst_addr, self.dst_port)
		

 	# response from server - reverse flow
	def clientDataReceived(self, chunk):
		
		self.transport.write(chunk)
		self.srv_queue.get().addCallback(self.clientDataReceived)

		# these operations must be done after data is sent so that the flow is created
		self.src_flow = self.factory.get_flow(self.dst_flow.reverse_flowid())
		self.server_payload += chunk

		self.src_flow.cleartext_payload = self.server_payload
		self.src_flow.data_transfered = len(self.server_payload)
		self.src_flow.tls = True



 	# data from client - original flow
	def dataReceived(self, chunk):
		self.client_payload += chunk

		# update flow
		self.dst_flow.cleartext_payload = self.client_payload
		self.dst_flow.data_transfered = len(self.client_payload)
		
		if self.clientFactory == None:
			self.clientFactory = ProxyClientFactory(self.srv_queue, self.cli_queue)
			reactor.connectSSL(self.dst_addr, self.dst_port, self.clientFactory, ssl.ClientContextFactory())
		
		self.cli_queue.put(chunk)
 
	def connectionLost(self, why):
		self.cli_queue.put(False)



class MalcomTLSFactory():
 	"""This is the Factory responsible for generating "server protocols" (instances of incoming connections)"""
 	def __init__(self, hosts):
 		self.hosts = hosts
 		self.protocols = []

 	def doStart(self):
 		pass

 	def buildProtocol(self, address):
 		p = self.protocol()
 		p.factory = self
 		self.protocols.append(p)
 		return p

 	def doStop(self):
 		for p in self.protocols:
 			p.transport.loseConnection()

 	def get_flow(self, fid):
 		for session_flows in self.flows:
 			if session_flows.get(fid, False):
 				return session_flows[fid]


class MalcomTLSProxy(threading.Thread):
	"""This class will handle the twisted reactor"""
	def __init__(self, port=9999):
		super(MalcomTLSProxy, self).__init__()
		self.hosts = {}
		self.factory = MalcomTLSFactory(self.hosts)
		self.factory.proxy = self
		self.factory.flows = []
		self.running = True
		self.thread = None
		self.port = port

	def run(self):
		self.factory.protocol = ProxyServer
		reactor.listenSSL(self.port, self.factory, ssl.DefaultOpenSSLContextFactory('Malcom/networking/tlsproxy/keys/server.key', 'Malcom/networking/tlsproxy/keys/server.crt'), interface="0.0.0.0")

		self.thread = threading.Thread(None, reactor.run, None, (), {'installSignalHandlers': 0})
		self.thread.start()

		try:
			while self.running:
				sleep(2)
		except KeyboardInterrupt, e:
			self.stop()
		
	def stop(self):
		self.running = False
		reactor.callFromThread(reactor.stop)
		self.thread.join()

	def add_flows(self, flows):
		self.factory.flows.append(flows)
 
if __name__ == "__main__":
	m = MalcomTLSProxy()
	m.run()
	








########NEW FILE########
__FILENAME__ = mdl
__author__ = 'pyt'

from Malcom.analytics.analytics import Analytics
from Malcom.celeryctl import celery
from Malcom.feeds.mdlhostlist import MDLHosts
from Malcom.feeds.mdliplist import MDLIpList
from Malcom.feeds.mdltracker import MDLTracker


@celery.task
def mdlhosts_tasks():
    mdl = MDLHosts("MDLHosts")
    mdl.analytics = Analytics()
    run =  mdl.update()
    if run is None:
        raise mdlhosts_tasks.retry(countdown=60)
    return run

@celery.task
def mdliplist_tasks():
    mdl = MDLIpList("MDLIpList")
    mdl.analytics = Analytics()
    run =  mdl.update()
    if run is None:
        raise mdliplist_tasks.retry(countdown=60)
    return run

@celery.task
def mdltracker_tasks():
    mdl = MDLTracker("MDLTracker")
    mdl.analytics = Analytics()
    run =  mdl.update()
    if run is None:
        raise mdliplist_tasks.retry(countdown=60)
    return run

########NEW FILE########
__FILENAME__ = other
__author__ = 'pyt'

from Malcom.feeds.alienvault import AlienvaultIP
from Malcom.feeds.dshield_as16276 import DShield16276
from Malcom.feeds.dshield_as3215 import DShield3215
from Malcom.feeds.malcode import MalcodeBinaries
from Malcom.feeds.malwarepatrol import MalwarePatrolVX
from Malcom.feeds.openbl import OpenblIP
from Malcom.feeds.palevotracker import PalevoTracker
from Malcom.feeds.siri_urz import SiriUrzVX
from Malcom.feeds.suspiciousdomains import SuspiciousDomains
from Malcom.feeds.torexitnodes import TorExitNodes
from Malcom.analytics.analytics import Analytics
from Malcom.celeryctl import celery


@celery.task
def alienvault_tasks():
    aip = AlienvaultIP("AlienvaultIP")
    aip.analytics = Analytics()
    run =  aip.update()
    if run is None:
        raise alienvault_tasks.retry(countdown=60)
    return run

@celery.task
def dshield_as16276_tasks():
    ds_as = DShield16276("DShield16276")
    ds_as.analytics = Analytics()
    run =  ds_as.update()
    if run is None:
        raise dshield_as16276_tasks.retry(countdown=60)
    return run

@celery.task
def dshield_as3215_tasks():
    ds_as = DShield3215("DShield3215")
    ds_as.analytics = Analytics()
    run =  ds_as.update()
    if run is None:
        raise dshield_as3215_tasks.retry(countdown=60)
    return run

@celery.task
def malcodebinaries_tasks():
    mb = MalcodeBinaries("MalcodeBinaries")
    mb.analytics = Analytics()
    run =  mb.update()
    if run is None:
        raise malcodebinaries_tasks.retry(countdown=60)
    return run

@celery.task
def malwarepatrolvx_tasks():
    mp = MalwarePatrolVX("MalwarePatrolVX")
    mp.analytics = Analytics()
    run =  mp.update()
    if run is None:
        raise malwarepatrolvx_tasks.retry(countdown=60)
    return run

@celery.task
def openblip_tasks():
    oblip = OpenblIP("OpenblIP")
    oblip.analytics = Analytics()
    run =  oblip.update()
    if run is None:
        raise openblip_tasks.retry(countdown=60)
    return run

@celery.task
def palevotracker_tasks():
    pt = PalevoTracker("PalevoTracker")
    pt.analytics = Analytics()
    run =  pt.update()
    if run is None:
        raise palevotracker_tasks.retry(countdown=60)
    return run

@celery.task
def siriurzvx_tasks():
    su = SiriUrzVX("SiriUrzVX")
    su.analytics = Analytics()
    run =  su.update()
    if run is None:
        raise siriurzvx_tasks.retry(countdown=60)
    return run

@celery.task
def suspiciousdomains_tasks():
    sd = SuspiciousDomains("SuspiciousDomains")
    sd.analytics = Analytics()
    run =  sd.update()
    if run is None:
        raise suspiciousdomains_tasks.retry(countdown=60)
    return run

@celery.task
def torexitnodes_tasks():
    ten = TorExitNodes("TorExitNodes")
    ten.analytics = Analytics()
    run =  ten.update()
    if run is None:
        raise torexitnodes_tasks.retry(countdown=60)
    return run



########NEW FILE########
__FILENAME__ = scheduler
__author__ = 'pyt'

from Malcom.tasks.zeus import (zeustrackerbinaries_tasks,
                               zeustrackerconfigs_tasks,
                               zeustrackergameoverdomains_tasks,
                               zeustrackerdropzones_tasks
                               )
from Malcom.tasks.spyeye import (spyeyebinaries_tasks,
                                 spyeyecnc_tasks,
                                 spyeyeconfigs_tasks,
                                 spyeyedropzones_tasks
                                 )
from Malcom.tasks.mdl import (mdlhosts_tasks,
                              mdliplist_tasks,
                              mdltracker_tasks
                              )
from Malcom.tasks.other import (alienvault_tasks,
                                dshield_as16276_tasks,
                                dshield_as3215_tasks,
                                malcodebinaries_tasks,
                                malwarepatrolvx_tasks,
                                openblip_tasks,
                                palevotracker_tasks,
                                siriurzvx_tasks,
                                suspiciousdomains_tasks,
                                torexitnodes_tasks
                                )
from Malcom.celeryctl import celery
# from celery.contrib.methods import task_method
from celery import group

# class Scheduler(object):
#     def run(self):
#         self.worker.delay()
#
#     def init(self):
#         self.init = "init"

@celery.task()
def worker():
    res_ztbt = zeustrackerbinaries_tasks.s()
    res_ztct = zeustrackerconfigs_tasks.s()
    res_ztgodt = zeustrackergameoverdomains_tasks.s()
    res_ztdzt = zeustrackerdropzones_tasks.s()
    res_seb = spyeyebinaries_tasks.s()
    res_secnc = spyeyecnc_tasks.s()
    res_sec = spyeyeconfigs_tasks.s()
    res_sedz = spyeyedropzones_tasks.s()
    res_mdlhosts = mdlhosts_tasks.s()
    res_mdlil = mdliplist_tasks.s()
    res_mdlt = mdltracker_tasks.s()
    res_av = alienvault_tasks.s()
    res_d_as16276 = dshield_as16276_tasks.s()
    res_d_as3215 = dshield_as3215_tasks.s()
    res_mb = malcodebinaries_tasks.s()
    res_mpvx = malwarepatrolvx_tasks.s()
    res_oip = openblip_tasks.s()
    res_pt = palevotracker_tasks.s()
    res_su = siriurzvx_tasks.s()
    res_sd = suspiciousdomains_tasks.s()
    res_ten = torexitnodes_tasks.s()


    g_res = group(
        res_ztbt, res_ztct, res_ztgodt, res_ztdzt,
        res_seb, res_sec, res_secnc, res_sedz,
        res_mdlhosts, res_mdlil, res_mdlt,
        res_av, res_d_as16276, res_d_as3215,
        res_mb, res_mpvx, res_oip, res_pt,
        res_su, res_sd, res_ten
    )
    g_res.apply_async()

########NEW FILE########
__FILENAME__ = spyeye
__author__ = 'pyt'

from Malcom.analytics.analytics import Analytics
from Malcom.celeryctl import celery
from Malcom.feeds.spyeyebinaries import SpyEyeBinaries
from Malcom.feeds.spyeyeconfigs import SpyEyeConfigs
from Malcom.feeds.spyeyedropzones import SpyEyeDropzones
from Malcom.feeds.spyeyecnc import SpyEyeCnc


@celery.task
def spyeyebinaries_tasks():
    se = SpyEyeBinaries("SpyEyeBinaries")
    se.analytics = Analytics()
    run =  se.update()
    if run is None:
        raise spyeyebinaries_tasks.retry(countdown=60)
    return run

@celery.task
def spyeyeconfigs_tasks():
    se = SpyEyeConfigs("SpyEyeConfigs")
    se.analytics = Analytics()
    run =  se.update()
    if run is None:
        raise spyeyeconfigs_tasks.retry(countdown=60)
    return run


@celery.task
def spyeyedropzones_tasks():
    se = SpyEyeDropzones("SpyEyeDropzones")
    se.analytics = Analytics()
    run =  se.update()
    if run is None:
        raise spyeyedropzones_tasks.retry(countdown=60)
    return run

@celery.task
def spyeyecnc_tasks():
    se = SpyEyeCnc("SpyEyeCnc")
    se.analytics = Analytics()
    run =  se.update()
    if run is None:
        raise spyeyecnc_tasks.retry(countdown=60)
    return run

########NEW FILE########
__FILENAME__ = zeus
__author__ = 'pyt'

from Malcom.analytics.analytics import Analytics
from Malcom.celeryctl import celery
from Malcom.feeds.zeustracker import ZeusTrackerBinaries
from Malcom.feeds.zeusgameover import ZeusGameOverDomains
from Malcom.feeds.zeusdropzones import ZeusTrackerDropzones
from Malcom.feeds.zeusconfigs import ZeusTrackerConfigs
from celery.contrib.methods import task_method

@celery.task
def zeustrackerbinaries_tasks():
    ztb = ZeusTrackerBinaries("ZeusTrackerBinaries")
    ztb.analytics = Analytics()
    run =  ztb.update()
    if run is None:
        raise zeustrackerbinaries_tasks.retry(countdown=60)
    return run

@celery.task
def zeustrackergameoverdomains_tasks():
    ztb = ZeusGameOverDomains("ZeusGameOverDomains")
    ztb.analytics = Analytics()
    run =  ztb.update()
    if run is None:
        raise zeustrackergameoverdomains_tasks.retry(countdown=60)
    return run

@celery.task
def zeustrackerdropzones_tasks():
    ztb = ZeusTrackerDropzones("ZeusTrackerDropzones")
    ztb.analytics = Analytics()
    run =  ztb.update()
    if run is None:
        raise zeustrackerdropzones_tasks.retry(countdown=60)
    return run


@celery.task
def zeustrackerconfigs_tasks():
    ztb = ZeusTrackerConfigs("ZeusTrackerConfigs")
    ztb.analytics = Analytics()
    run =  ztb.update()
    if run is None:
        raise zeustrackerconfigs_tasks.retry(countdown=60)
    return run


########NEW FILE########
__FILENAME__ = webserver
#!/usr/bin/python
# -*- coding: utf-8 -*-

__description__ = 'Malcom - Malware communications analyzer'
__author__ = '@tomchop_'
__version__ = '1.2 alpha'
__license__ = "GPL"


#system
import os, datetime, time, sys, signal, argparse, re
import netifaces as ni

#db 
from pymongo import MongoClient

#json / bson
from bson.objectid import ObjectId
from bson.json_util import dumps, loads

#flask stuff
from werkzeug import secure_filename
from flask import Flask, request, render_template, redirect, url_for, g, make_response, abort, flash, send_from_directory
from functools import wraps

#websockets
from geventwebsocket.handler import WebSocketHandler
from gevent.pywsgi import WSGIServer

# custom
from Malcom.auxiliary.toolbox import *
from Malcom.analytics.analytics import Analytics
from Malcom.feeds.feed import FeedEngine
from Malcom.model.datatypes import Hostname
from Malcom.networking import netsniffer
import Malcom

ALLOWED_EXTENSIONS = set(['txt', 'csv'])

app = Malcom.app
		
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.debug = True


# This enables the server to be ran behind a reverse-proxy
# Make sure you have an nginx configuraiton similar to this

# location = /malcom { rewrite ^ /malcom/; }
# location /malcom { try_files $uri @malcom; }

# # proxy
# location @malcom {
# 	proxy_pass http://127.0.0.1:8080;
# 	proxy_http_version 1.1;
# 	proxy_set_header SCRIPT_NAME /malcom;
# 	proxy_set_header Host $host;    
# 	proxy_set_header X-Scheme $scheme;
# 	proxy_set_header Upgrade $http_upgrade;
# 	proxy_set_header Connection "upgrade";
# }

def malcom_app(environ, start_response):  
	
	if environ.get('HTTP_SCRIPT_NAME'):
		# update path info 
		environ['PATH_INFO'] = environ['PATH_INFO'].replace(environ['HTTP_SCRIPT_NAME'], "")
		# declare SCRIPT_NAME
		environ['SCRIPT_NAME'] = environ['HTTP_SCRIPT_NAME']
	
	if environ.get('HTTP_X_SCHEME'):	
		# forward the scheme
		environ['wsgi.url_scheme'] = environ.get('HTTP_X_SCHEME')

	return app(environ, start_response)


@app.errorhandler(404)
def page_not_found(error):
	return 'This page does not exist', 404

@app.after_request
def after_request(response):
	origin = request.headers.get('Origin', '')
	# debug_output(origin, False)
	response.headers['Access-Control-Allow-Origin'] = origin
	response.headers['Access-Control-Allow-Credentials'] = 'true'
	return response

@app.before_request
def before_request():
	# make configuration and analytics engine available to views
	g.config = app.config
	g.a = Malcom.analytics_engine


# decorator for URLs that should not be public
def private_url(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.config['PUBLIC']:
            abort(404)
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
	return redirect(url_for('dataset'))

# feeds ========================================================

@app.route('/feeds')
def feeds():
	alpha = sorted(Malcom.feed_engine.feeds, key=lambda name: name)
	return render_template('feeds.html', feed_names=alpha, feeds=Malcom.feed_engine.feeds)

@app.route('/feeds/run/<feed_name>')
@private_url
def run_feed(feed_name):
	Malcom.feed_engine.run_feed(feed_name)
	return redirect(url_for('feeds'))


# graph operations =============================================

@app.route('/nodes/<field>/<path:value>')
def nodes(field, value):
	return render_template('dynamic_nodes.html', field=field, value=value)


@app.route('/neighbors')
def neighbors():
	a = g.a
	query = {}
	for key in request.args:
		query[key] = request.args.getlist(key)

	data = a.find_neighbors(query, include_original=True)
	return make_response(dumps(data), 200, {'Content-Type': 'application/json'})

@app.route('/evil')
def evil():
	a = g.a
	query = {}
	for key in request.args:
		query[key] = request.args.getlist(key)
	data = a.multi_graph_find(query, {'key':'tags', 'value': 'evil'})

	return (dumps(data), 200, {'Content-Type': 'application/json'})


# dataset operations ======================================================

def allowed_file(filename):
	return '.' in filename and \
		   filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/dataset/report/<field>/<path:value>/')
@app.route('/dataset/report/<field>/<path:value>/<strict>/')
def report(field, value, strict=False):
	base_elts_dict = {}
	base_elts = []

	if strict:
		result_set = g.a.data.find({field: value})
	else:
		result_set = g.a.data.find({field: re.compile(re.escape(value), re.IGNORECASE)})

	for e in result_set:
		base_elts_dict[e['_id']] = e
		base_elts.append(e)


	# get all 1st degree nodes in one dict
	all_nodes_dict = {}
	all_edges_dict = {}

	for elt in base_elts:
		nodes, edges = g.a.data.get_neighbors_elt(elt)
		for n in nodes:
			all_nodes_dict[n['_id']] = n
		for e in edges:
			all_edges_dict[e['_id']] = e

	filtered_edges_dict = {}
	for l in all_edges_dict:
		if all_nodes_dict.get(all_edges_dict[l]['src'], False):
			filtered_edges_dict[l] = all_edges_dict[l]

	# all_nodes_dict 		contains an id_dictionary with all neighboring nodes
	# filtered_edges_dict 	contains an id_dictionary of all links of which the source is in all_nodes_dict
	# all_edges_dict 		contains an id_dictionary of all 1st degree and 2nd degree links

	linked_elements = {}

	for e in filtered_edges_dict:
		e = filtered_edges_dict[e]
		
		if all_nodes_dict.get(e['dst'], False): # if edge points towards one of base_elts
			dst = all_nodes_dict[e['dst']]
			src = all_nodes_dict[e['src']]
			if e['attribs'] not in linked_elements: # if we don't have a record for this link, create an empty array
				linked_elements[e['attribs']] = []
			if dst not in linked_elements[e['attribs']]: # avoid duplicates
				print "%s -> %s" % (e['attribs'], dst['value'])
				linked_elements[e['attribs']].append((src, dst))
	
	related_elements = {}

	chrono = datetime.datetime.now()
	for n in all_nodes_dict:
		n = all_nodes_dict[n]
		if n['type'] not in related_elements: # if we don't have a record for this type, create an empty array
			related_elements[n['type']] = []
		related_elements[n['type']].append(n)

	#display fields
	base_elts[0]['fields'] = base_elts[0].display_fields
	print linked_elements
	return render_template("report.html", field=field, value=value, base_elts=base_elts, linked=linked_elements, related_elements=related_elements)

@app.route('/dataset/')
def dataset():
	return render_template("dataset.html")


@app.route('/dataset/list/') # ajax method for sarching dataset and populating dataset table
def list_data():
	a = g.a
	query = {}
	try:
		page = int(request.args['page'])
	except Exception, e:
		page = 0

	fuzzy = False if request.args['fuzzy']=='false' else True

	for key in request.args:
		if key not in  ['page', 'fuzzy']:
			if request.args[key].find(',') != -1: # split request arguments
				if fuzzy:
					query['$and'] = [{ key: re.compile(split, re.IGNORECASE)} for split in request.args[key].split(',')]
				else:
					query['$and'] = [{ key: split} for split in request.args[key].split(',')]
			else:
				if fuzzy:
					query[key] = re.compile(request.args[key], re.IGNORECASE) # {"$regex": request.args[key]}
				else:
					query[key] = request.args[key]

	per_page = 50

	chrono_query = datetime.datetime.now()
	elts = [e for e in a.data.find(query).sort('date_created', -1)[page*per_page:page*per_page+per_page]]
	chrono_query = datetime.datetime.now() - chrono_query
	debug_output("Query completed in %s" % chrono_query)
	
	
	for elt in elts:
		elt['link_value'] = url_for('nodes', field='value', value=elt['value'])
		elt['link_type'] = url_for('nodes', field='type', value=elt['type'])

	data = {}
	if len(elts) > 0:
		data['fields'] = elts[0].display_fields
		data['elements'] = elts
	else:
		data['fields'] = [('value', 'Value'), ('type', 'Type'), ('tags', 'Tags')]
		data['elements'] = []
	
	data['page'] = page
	data['per_page'] = per_page

	chrono_count = datetime.datetime.now()
	data['total_results'] = a.data.find(query).count()
	chrono_count = datetime.datetime.now() - chrono_count
	debug_output("Count completed in %s" % chrono_count)
	data['chrono_query'] = str(chrono_query)
	data['chrono_count'] = str(chrono_count)
	return dumps(data)

@app.route('/dataset/list/csv')
def dataset_csv():
	a = g.a
	filename = []
	query = {}
	fuzzy = False if request.args['fuzzy'] == 'false' else True

	for key in request.args:
		if key != '' and key not in ['fuzzy']:
			if fuzzy:
				# slow
				query[key] = re.compile(re.escape(request.args[key]), re.IGNORECASE)
			else:
				# skip regex to make it faster
				query[key] = request.args[key]
			filename.append("%s_%s" % (key, request.args[key]))
		else:
			filename.append('all')

	filename = "-".join(filename)
	results = a.data.find(query).sort('date_created', -1)
	
	if results.count() == 0:
		flash("You're about to download an empty .csv",'warning')
		return redirect(url_for('dataset'))
	else:
		response = make_response()
		response.headers['Cache-Control'] = 'no-cache'
		response.headers['Content-Type'] = 'text/csv'
		response.headers['Content-Disposition'] = 'attachment; filename='+filename+'-extract.csv'
		fields = results[0].display_fields
		data = ";".join([f[1] for f in fields ]) + "\n"
		for e in results:
			data += ";".join([list_to_str(e.get(f[0],"-")) for f in fields]) + "\n"

		response.data = data
		response.headers['Content-Length'] = len(response.data)

		return response


@app.route('/dataset/add', methods=['POST'])
@private_url
def add_data():
	
	if request.method == "POST":
		file = request.files.get('element-list')
		if file:  #we're dealing with a list of elements
			if allowed_file(file.filename):
				elements = file.read()
				elements = elements.split("\n")
			else:
				return 'filename not allowed'
		else:
			elements = [request.form['element']]

		tags = request.form.get('tags', None)
		
		if len(elements) == 0 or not tags:
			flash("You must specify an element and tags", 'warning')
			return redirect(url_for('dataset'))

		a = g.a
		tags = tags.strip().split(";")
		a.add_text(elements, tags)

		if request.form.get('analyse', None):
			a.process()

		return redirect(url_for('dataset'))

	else:
		return "Not allowed"

@app.route('/dataset/remove/<id>')
def delete(id):
	a = g.a 
	result = a.data.remove(id)
	return dumps(result)

@app.route('/dataset/clear/')
@private_url
def clear():
	g.a.data.clear_db()
	return redirect(url_for('dataset'))

@app.route('/analytics')
def analytics():
	g.a.process()
	return "Analytics: Done."

# Sniffer ============================================

@app.route('/sniffer/',  methods=['GET', 'POST'])
def sniffer():
	if request.method == 'POST':
		filter = request.form['filter']
		
		session_name = secure_filename(request.form['session_name'])
		if session_name == "":
			flash("Please specify a session name", 'warning')
			return redirect(url_for('sniffer'))

		debug_output("Creating session %s" % session_name)

		# intercept TLS?
		intercept_tls = True if request.form.get('intercept_tls', False) and Malcom.tls_proxy != None else False

		Malcom.sniffer_sessions[session_name] = netsniffer.Sniffer(Malcom.analytics_engine, session_name, str(request.remote_addr), filter, intercept_tls=intercept_tls)
		
		# this is where the data will be stored persistently
		filename = session_name + ".pcap"
		Malcom.sniffer_sessions[session_name].pcap_filename = filename
		
		pcap = None
		# if we're dealing with an uploaded PCAP file
		file = request.files.get('pcap-file')
		if file:
			# store in /sniffer folder
			with open(Malcom.config['SNIFFER_DIR'] + "/" + filename, 'wb') as f:
				f.write(file.read())
			Malcom.sniffer_sessions[session_name].pcap = True

		# start sniffing right away
		if request.form.get('startnow', None):
			Malcom.sniffer_sessions[session_name].start(str(request.remote_addr))
		
		return redirect(url_for('sniffer_session', session_name=session_name, pcap_filename=pcap))


	return render_template('sniffer_new.html')

@app.route('/sniffer/sessionlist/')
def sniffer_sessionlist():
	session_list = []
	for s in Malcom.sniffer_sessions:
		session_list.append({
								'name': s, 
								'packets': Malcom.sniffer_sessions[s].packet_count,
								'nodes': len(Malcom.sniffer_sessions[s].nodes),
								'edges': len(Malcom.sniffer_sessions[s].edges),
								'status': "Running" if Malcom.sniffer_sessions[s].status() else "Stopped"
							})
	return dumps({'session_list': session_list})


@app.route('/sniffer/<session_name>/')
def sniffer_session(session_name, pcap_filename=None):
	# check if session exists
	if session_name not in Malcom.sniffer_sessions:
		debug_output("Sniffing session '%s' does not exist" % session_name, 'error')
		flash("Sniffing session '%s' does not exist" % session_name, 'warning')
		return redirect(url_for('sniffer'))
	
	return render_template('sniffer.html', session=Malcom.sniffer_sessions[session_name], session_name=session_name)

@app.route('/sniffer/<session_name>/delete')
def sniffer_session_delete(session_name):
	if session_name not in Malcom.sniffer_sessions:
		return (dumps({'status':'Sniffer session %s does not exist' % session_name, 'success': 0}), 200, {'Content-Type': 'application/json'})
	else:
		if Malcom.sniffer_sessions[session_name].status():
			return (dumps({'status':"Can't delete session %s: session running" % session_name, 'success': 0}), 200, {'Content-Type': 'application/json'})
		g.a.data.del_sniffer_session(session_name)
		print Malcom.sniffer_sessions
		del Malcom.sniffer_sessions[session_name]
		return (dumps({'status':"Sniffer session %s has been deleted" % session_name, 'success': 1}), 200, {'Content-Type': 'application/json'})





	

@app.route('/sniffer/<session_name>/pcap')
def pcap(session_name):
	if session_name not in Malcom.sniffer_sessions:
		abort(404)
	Malcom.sniffer_sessions[session_name].generate_pcap()
	return send_from_directory(Malcom.config['SNIFFER_DIR'], Malcom.sniffer_sessions[session_name].pcap_filename, mimetype='application/vnd.tcpdump.pcap', as_attachment=True, attachment_filename='malcom_capture_'+session_name+'.pcap')


@app.route("/sniffer/<session_name>/<flowid>/raw")
def send_raw_payload(session_name, flowid):
	if session_name not in Malcom.sniffer_sessions:
		abort(404)
	if flowid not in Malcom.sniffer_sessions[session_name].flows:
		abort(404)
			
	response = make_response()
	response.headers['Cache-Control'] = 'no-cache'
	response.headers['Content-Type'] = 'application/octet-stream'
	response.headers['Content-Disposition'] = 'attachment; filename=%s_%s_dump.raw' % (session_name, flowid)
	response.data = Malcom.sniffer_sessions[session_name].flows[flowid].get_payload(encoding='raw')
	response.headers['Content-Length'] = len(response.data)

	return response

# Public API ================================================

@app.route('/public/api')
def query_public_api():
	query = {}
	for key in request.args:
		query[key] = request.args.getlist(key)

	apikey = request.headers.get('X-Malcom-API-key', False)

	#if not "X-Malcom-API-key":
	#	return dumps({})

	available_tags = g.a.data.get_tags_for_key(apikey)

	tag_filter = {'tags': {'$in': available_tags}}
	query = {'$and': [query, tag_filter]}

	db_data = g.a.data.find(query)
	data = []
	for d in db_data:
		d['tags'] = list(set(available_tags) & set(d['tags']))
		data.append(d)

	return (dumps(data), 200, {'Content-Type': 'application/json'})



# APIs (websockets) =========================================


@app.route('/api/analytics')
def analytics_api():
	debug_output("Call to analytics API")

	if request.environ.get('wsgi.websocket'):
		debug_output("Got websocket")

		ws = request.environ['wsgi.websocket']
		g.a.websocket = ws

		while True:
			try:
				message = loads(ws.receive())
				debug_output("Received: %s" % message)
			except Exception, e:
				return ""

			cmd = message['cmd']

			if cmd == 'analyticsstatus':
				g.a.notify_progress('Loaded')

	
			


@app.route('/api/sniffer')
def sniffer_api():
	debug_output("call to sniffer API")

	if request.environ.get('wsgi.websocket'):

		ws = request.environ['wsgi.websocket']

		while True:
			try:
				message = loads(ws.receive())
			except Exception, e:
				debug_output("Could not decode JSON message: %s" %e)
				return ""
			
			debug_output("Received: %s" % message)



			cmd = message['cmd']
			session_name = message['session_name']

			if session_name in Malcom.sniffer_sessions:
				session = Malcom.sniffer_sessions[session_name]
			else:
				send_msg(ws, "Session %s not foud" % session_name, type=cmd)
				continue

			session.ws = ws


			# websocket commands

			if cmd == 'sessionlist':
				session_list = [s for s in Malcom.sniffer_sessions]
				send_msg(ws, {'session_list': session_list}, type=cmd)
				continue

			if cmd == 'sniffstart':
				session.start(str(request.remote_addr), public=g.config['PUBLIC'])
				send_msg(ws, "OK", type=cmd)
				continue

			if cmd == 'sniffstop':
				if g.config['PUBLIC']:
					continue
				if session.status():
					session.stop()
					send_msg(ws, 'OK', type=cmd)
				else:
					send_msg(ws, 'Error: sniffer not running', type=cmd)
				continue

			if cmd == 'sniffstatus':
				if session.status():
					status = 'active'
					debug_output("Session %s is active" % session.name)
					send_msg(ws, {'status': 'active', 'session_name': session.name}, type=cmd)
				else:
					status = 'inactive'
					debug_output("Session %s is inactive" % session.name)
					send_msg(ws, {'status': 'inactive', 'session_name': session.name}, type=cmd)
				continue
					
			if cmd == 'sniffupdate':
				data = session.update_nodes()
				data['type'] = cmd
				if data:
					ws.send(dumps(data))
				continue

			if cmd == 'flowstatus':
				data = session.flow_status()
				data['type'] = cmd
				if data:
					ws.send(dumps(data))
				continue

			if cmd == 'get_flow_payload':
				fid = message['flowid']
				flow = session.flows[fid]
				data = {}
				data['payload'] = flow.get_payload()

				data['type'] = cmd
				ws.send(dumps(data))
				continue
		
	return ""


class MalcomWeb(object):
	"""docstring for MalcomWeb"""
	def __init__(self, public, listen_port, listen_interface):
		self.public = public
		self.listen_port = listen_port
		self.listen_interface = listen_interface
		self.start_server()

	def start_server(self):
		for key in Malcom.config:
			app.config[key] = Malcom.config[key]
		app.config['UPLOAD_DIR'] = ""
		
		sys.stderr.write("Starting webserver in %s mode...\n" % ("public" if self.public else "private"))
		try:
			http_server = WSGIServer((self.listen_interface, self.listen_port), malcom_app, handler_class=WebSocketHandler)
			sys.stderr.write("Webserver listening on %s:%s\n\n" % (self.listen_interface, self.listen_port))
			http_server.serve_forever()
		except KeyboardInterrupt:

			sys.stderr.write(" caught: Exiting gracefully\n")

			if len(Malcom.sniffer_sessions) > 0:
				debug_output('Stopping sniffing sessions...')
				for s in Malcom.sniffer_sessions:
					session = Malcom.sniffer_sessions[s]
					session.stop()


########NEW FILE########
__FILENAME__ = malcom
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__description__ = 'Malcom - Malware communications analyzer'
__author__ = '@tomchop_'
__version__ = '1.1 alpha'
__license__ = "GPL"

import os, sys, argparse, threading
import netifaces as ni
from time import sleep

from flask import Flask

from Malcom.analytics.analytics import Analytics
from Malcom.feeds.feed import FeedEngine
from Malcom.web.webserver import MalcomWeb
from Malcom.networking.tlsproxy.tlsproxy import MalcomTLSProxy
from Malcom.networking import netsniffer
import Malcom # this is the configuraiton

# this should be stored and loaded from a configuration file
Malcom.config['DEBUG'] = True
Malcom.config['VERSION'] = "1.1 alpha"
Malcom.config['LISTEN_INTERFACE'] = "0.0.0.0"
Malcom.config['LISTEN_PORT'] = 8080
Malcom.config['MAX_THREADS'] = 4
Malcom.config['PUBLIC'] = False
Malcom.config['NO_FEED'] = False
Malcom.config['TLS_PROXY_PORT'] = False
Malcom.config['BASE_PATH'] = os.getcwd() + '/Malcom'
Malcom.config['SNIFFER_DIR'] = Malcom.config['BASE_PATH'] + '/sniffer'
Malcom.config['FEEDS_DIR'] = Malcom.config['BASE_PATH'] + '/feeds'

Malcom.config['IFACES'] = {}
for i in [i for i in ni.interfaces() if i.find('eth') != -1]:
	Malcom.config['IFACES'][i] = ni.ifaddresses(i).get(2,[{'addr':'Not defined'}])[0]['addr']

if __name__ == "__main__":

	# options
	parser = argparse.ArgumentParser(description="Malcom - malware communications analyzer")
	parser.add_argument("-a", "--analytics", help="Run analytics", action="store_true", default=False)
	parser.add_argument("-f", "--feeds", help="Run feeds (use -ff to force run on all feeds)", action="count")
	parser.add_argument("-i", "--interface", help="Listen interface", default=Malcom.config['LISTEN_INTERFACE'])
	parser.add_argument("-p", "--port", help="Listen port", type=int, default=Malcom.config['LISTEN_PORT'])
	parser.add_argument("--public", help="Run a public instance (Feeds and network sniffing disabled)", action="store_true", default=Malcom.config['PUBLIC'])
	parser.add_argument("--max-threads", help="Number of threads to use (default 4)", type=int, default=Malcom.config['MAX_THREADS'])
	parser.add_argument("--tls-proxy-port", help="Port number on which to start the TLS proxy on. No proxy started if not specified.", type=int, default=Malcom.config['TLS_PROXY_PORT'])
	
	#parser.add_argument("--no-feeds", help="Disable automatic feeding", action="store_true", default=app.config['NO_FEED'])
	args = parser.parse_args()

	os.system('clear')
	Malcom.config['LISTEN_INTERFACE'] = args.interface
	Malcom.config['LISTEN_PORT'] = args.port
	Malcom.config['MAX_THREADS'] = args.max_threads
	Malcom.config['PUBLIC'] = args.public

	sys.stderr.write("===== Malcom %s - Malware Communications Analyzer =====\n\n" % Malcom.config['VERSION'])
	
	sys.stderr.write("Detected interfaces:\n")
	for iface in Malcom.config['IFACES']:
		sys.stderr.write("%s:\t%s\n" % (iface, Malcom.config['IFACES'][iface]))
	
	Malcom.analytics_engine = Analytics()

	if args.tls_proxy_port:
		Malcom.config['TLS_PROXY_PORT'] = args.tls_proxy_port
		sys.stderr.write("Starting TLS proxy on port %s\n" % args.tls_proxy_port)
		Malcom.tls_proxy = MalcomTLSProxy(args.tls_proxy_port)
		Malcom.tls_proxy.start()
	else:
		Malcom.tls_proxy = None

	sys.stderr.write("Importing feeds...\n")
	Malcom.feed_engine = FeedEngine(Malcom.analytics_engine)
	Malcom.feed_engine.load_feeds()

	sys.stderr.write("Importing packet captures...\n")
	
	for s in Malcom.analytics_engine.data.get_sniffer_sessions():
		Malcom.sniffer_sessions[s['name']] = netsniffer.Sniffer(Malcom.analytics_engine, 
																s['name'], 
																None, 
																None, 
																filter_restore=s['filter'], 
																intercept_tls=s['intercept_tls'] if args.tls_proxy_port else False)

		Malcom.sniffer_sessions[s['name']].pcap = True

	# call malcom to run feeds - this will not start the web interface
	if args.feeds >= 1:
		if args.feeds == 1:
			try:
				Malcom.feed_engine.start()
				sys.stderr.write("Starting feed scheduler...\n")
				while True:
					raw_input()
			except KeyboardInterrupt:
				sys.stderr.write("\nStopping all feeds...\n")
				Malcom.feed_engine.stop_all_feeds()
				exit(0)
			
		elif args.feeds == 2:
			Malcom.feed_engine.run_all_feeds()
		exit(0)

	elif args.analytics: # run analytics
		
		Malcom.analytics_engine.max_threads = threading.Semaphore(Malcom.config['MAX_THREADS'])

		while True:
			Malcom.analytics_engine.process()
			sleep(10) # sleep 10 seconds
		pass

	else: # run webserver
		web = MalcomWeb(Malcom.config['PUBLIC'], Malcom.config['LISTEN_PORT'], Malcom.config['LISTEN_INTERFACE'])
		try:
			Malcom.tls_proxy.stop()
		except Exception, e:
			pass
			

		exit(0)

########NEW FILE########
