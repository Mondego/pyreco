__FILENAME__ = alerter
from copy import deepcopy

from amonone.alerts.system import system_alerts
from amonone.alerts.process import process_alerts
from amonone.mail.sender import send_mail
from amonone.sms.sender import send_sms
from amonone.web.apps.alerts.models import alerts_model
from amonone.web.apps.core.models import server_model
from amonone.log import logging

class ServerAlerter(object):

	def check(self, data=None,  alert_type=None):

		alert_type = 'server' if alert_type == 'server' else 'process'
		
		rules = alerts_model.get_alerts(type=alert_type)

		if rules:
			if alert_type == 'server':
				alerts = system_alerts.check(data, rules)
			elif alert_type == 'process':
				alerts = process_alerts.check(data, rules)
			else:
				alerts = False


			if alerts:
				alerts_model.save_occurence(alerts)
				self.send_alerts()
				
			return alerts # For the test suite


	def send_alerts(self, test=None):
		rules = alerts_model.get_all_alerts()
		alerts = []
		for rule in rules:
			history = rule.get('history', [])
			threshold = rule.get('threshold', 1)
			mute = rule.get('mute', False)

			last_trigger = rule.get('last_trigger', 1)
			trigger = True if int(last_trigger) >= int(threshold) else False

			if trigger is True:
				# Don't append rules for non exisiting servers, check if the alert is muted
				if mute == False:
					alerts.append(rule)

		if len(alerts)> 0:
			# Send emails for each alert
			for alert in alerts: 
				rule_type = alert.get("rule_type", "server") 

				if rule_type == 'process':
					title = "{0}/{1}".format(alert.get('process', ''), alert.get('check',''))
				else:
					title = alert.get('metric', 'System') 
				

				email_recepients = alert.get('email_recepients', [])

				if len(email_recepients) > 0:
					try:
						send_mail(template_data=alert, 
							recepients=email_recepients,
							subject='Amon alert - ({0})'.format(title),
							template='{0}_alert'.format(rule_type)
							)
					except Exception, e:
						logging.exception("Error sending an alert email")
				

				sms_recepients = alert.get('sms_recepients', [])
				
				if len(sms_recepients) > 0:
					try:
						send_sms(alert=alert,
							recepients=sms_recepients,
							template='{0}_alert.txt'.format(rule_type))
					except Exception, e:
						logging.exception("Error sending an alert SMS")

		return None


server_alerter = ServerAlerter()



########NEW FILE########
__FILENAME__ = process
class ProcessAlerts(object):

	def __init__(self):
		self.alerts = {}

	def check(self, data, rules=None):
		if rules:
			for rule in rules:
				try:
					process_data = data[rule['process']]
				except:
					process_data = False 
					# Can't find the process in the dictionary
	  

				if process_data != False:
					if rule['check'] == 'CPU':
						self.check_cpu(rule, process_data)
					elif rule['check'] == 'Memory':
						self.check_memory(rule, process_data)

			if len(self.alerts) > 0:
				alerts = self.alerts
				self.alerts = {} 
				return alerts
			else:
				return False

		
	def check_memory(self, rule, data):
		alert = False
		process = rule['process']

		if rule['above_below'] == 'above':
			if float(data['memory:mb']) > float(rule['metric_value']):
				alert = True

		if rule['above_below'] == 'below':
			if float(data['memory:mb']) < float(rule['metric_value']):
				alert = True

		if alert:
			alert = {'alert_on': data['memory:mb'], 'rule': str(rule['_id']), 'metric_type': 'MB'}
				
		if alert:
			try:
				len(self.alerts[process])
				self.alerts[process].append(alert)
			except:
				self.alerts[process] = [alert]
			
			return True

	def check_cpu(self, rule, data):
		alert = False
		process = rule['process']
		utilization = float(data['cpu:%'])
		

		if rule['above_below'] == 'above':
			if float(rule['metric_value']) < utilization:
				alert = True

		if rule['above_below'] == 'below':
			if float(rule['metric_value']) > utilization:
				alert = True

		if alert:
			alert = {'alert_on': utilization, 'rule': str(rule['_id']), 'metric_type': '%'}
		
		if alert:
			try:
				len(self.alerts[process])
				self.alerts[process].append(alert)
			except:
				self.alerts[process] = [alert]
			
			return True

process_alerts = ProcessAlerts()

########NEW FILE########
__FILENAME__ = system
class SystemAlerts(object):

	def __init__(self):
		self.alerts = {}

	def check(self, data=None, rules=None):
		if rules:
			for rule in rules:
				if rule['metric'] == 'CPU':
					self.check_cpu(rule, data['cpu'])
				elif rule['metric'] == 'Memory':
					self.check_memory(rule, data['memory'])
				elif rule['metric'] == 'Loadavg':
					self.check_loadavg(rule, data['loadavg'])
				elif rule['metric'] == 'Disk':
					self.check_disk(rule, data['disk'])
		
		if len(self.alerts) > 0:
			alerts = self.alerts
			self.alerts = {} 

			return alerts
		else:
			return False
			
		
	def check_memory(self, rule, data):
		last = data.get('last', None)
		if last:
			return False
		alert = False
		# Calculate rules with MB 

		memtotal = float(data['memory:total:mb'])
		memfree = float(data['memory:free:mb'])
		metric_type = rule.get('metric_type')


		if rule['metric_type'] == 'MB':
			used_memory = float(data['memory:used:mb'])
		else:
			used_memory = float(data['memory:used:%'])
		
		if rule['above_below'] == 'above':
			if used_memory > float(rule['metric_value']):
				alert = True

		if rule['above_below'] == 'below':
			if used_memory < float(rule['metric_value']):
				alert = True


		if alert:
			alert = {"alert_on": used_memory , "rule": str(rule['_id']), "metric_type": metric_type}
		if alert:
			try:
				len(self.alerts['memory'])
				self.alerts['memory'].append(alert)
			except:
				self.alerts['memory'] = [alert]
			
			return True 

	def check_cpu(self, rule, data):
		last = data.get('last', None)
		if last:
			return False
		alert = False
		# Utitlization show total cpu usage 
		utilization = float(100)-float(data['idle'])
		
		if rule['above_below'] == 'above':
			if float(rule['metric_value']) < utilization:
				alert = True

		if rule['above_below'] == 'below':
			if float(rule['metric_value']) > utilization:
				alert = True

		if alert:
			alert = {"alert_on": utilization , "rule": str(rule['_id'])}
		
		if alert:
			try:
				len(self.alerts['cpu'])
				self.alerts['cpu'].append(alert)
			except:
				self.alerts['cpu'] = [alert]
			
			return True

	def check_loadavg(self, rule, data):
		last = data.get('last', None)
		if last:
			return False
		alert = False
		value_to_compare = 0
		
		if rule['metric_options'] == 'minute':
			value_to_compare = data['minute']

		if rule['metric_options'] == 'five_minutes':
			value_to_compare = data['five_minutes']

		if rule['metric_options'] == 'fifteen_minutes':
			value_to_compare = data['fifteen_minutes']
		
		value_to_compare = float(value_to_compare)
		
		if rule['above_below'] == 'above':
			if float(rule['metric_value']) < value_to_compare:
				alert = True

		if rule['above_below'] == 'below':
			if float(rule['metric_value']) > value_to_compare:
				alert = True

		if alert:
			alert = {"alert_on": value_to_compare , "rule": str(rule['_id'])}
		
		if alert:
			try:
				len(self.alerts['loadavg'])
				self.alerts['loadavg'].append(alert)
			except:
				self.alerts['loadavg'] = [alert]
			
			return True


	# Internal - checks a single volume
	def _check_volume(self, volume_data, rule, volume):
		alert = False

		used = volume_data['percent'] if rule['metric_type'] == "%" else volume_data['used']
		metric_type = '%' if rule['metric_type'] == '%' else 'MB'
	
		# Convert the data value to MB
		if isinstance(used, str) or isinstance(used, unicode):
			if 'G' in used:
				used = used.replace('G','')
				used = float(used)*1024 
			elif 'MB' in used:
				used = used.replace('MB','')
			elif 'M' in used:
				used = used.replace('M', '')

		
		used= float(used)

		# Convert the rule value to MB if necessary
		if rule['metric_type'] == 'GB':
			metric_value = float(rule['metric_value'])*1024
		else:
			metric_value = float(rule['metric_value'])

		if rule['above_below'] == 'above':
			if metric_value < used:
				alert = True

		if rule['above_below'] == 'below':
			if metric_value > used:
				alert = True

		if alert:
			alert = {"alert_on": used , "rule": str(rule['_id']), 
					 	'metric_type': metric_type,
					 	'volume': volume}
		
		return alert

	def check_disk(self, rule, data):
		last = data.get('last', None)
		
		if last:
			return False
		
		volumes = []
		single_volume = rule.get('metric_options', None)

		if single_volume:
			volumes.append(single_volume)
		else:
			volumes = data.keys()

		if len(volumes) > 0:
			# ["sda1": {'used': '', "free": }]
			for volume in volumes:
				alert = self._check_volume(data[volume], rule, volume)
				disk_alerts = self.alerts.get('disk', [])

				if len(disk_alerts) == 0:
					self.alerts['disk'] = [alert]
				else:
					self.alerts['disk'].append(alert)
	
			return True

	

system_alerts = SystemAlerts()

########NEW FILE########
__FILENAME__ = testdata
test_system_data = {u'memory': {u'swaptotal': 563, u'memfree': 1015, u'memtotal': 2012, u'swapfree': 563, u'time': 1326974020}, 
u'loadavg': {u'fifteen_minutes': u'0.28', u'five_minutes': 
u'3.33', u'time': 1326974020, u'cores': 2, u'scheduled_processes': u'2/342', u'minute': u'2.34'}, 
u'disk': {u'sda1': {u'used': u'6.9G', u'percent': u'65', u'free': u'3.9G', u'volume': u'/dev/sda1', u'path': u'/', u'total': u'12G'}, 
u'time': 1326974020}, 
u'cpu': {u'iowait': u'0.34', u'system': u'1.97', u'idle': u'35.40', u'user': u'1.23', 
u'time': 1326974020, u'steal': u'0.00', u'nice': u'0.00'}} 

test_process_data = {u'mongo': {u'memory': u'40.0', u'cpu': u'11.90', u'time': 1327169023}} 

########NEW FILE########
__FILENAME__ = alerter_test
import unittest
from nose.tools import * 

from amonone.alerts.alerter import ServerAlerter
from amonone.web.apps.core.models import server_model
from amonone.web.apps.alerts.models import alerts_model


test_system_data = {u'memory': { u'memory:free:mb': 800, u'memory:total:mb': 2012, u'memory:used:mb': 1200}}
rule ={"rule_type" : "server", "metric_type" : "MB", 
		"metric_value" : "1000", "above_below" : "above", "metric" : "Memory", "server": ""}


class ServerAlerterTest(unittest.TestCase):

	def setUp(self):
		self.alerter = ServerAlerter()
		

	def test_check(self):
		alerts_model.collection.remove()
		server_model.collection.remove()
		server_model.collection.insert({"server_name" : "test", "key": "test_me"})
		server = server_model.collection.find_one()
		server_id = str(server['_id'])

		rule['server'] = server_id
		alerts_model.save(rule)

		check = self.alerter.check(data=test_system_data, server=server, alert_type='server')
		eq_(check['memory'][0]['rule'], str(rule['_id']))



########NEW FILE########
__FILENAME__ = process_test
from amonone.alerts.process import ProcessAlerts
from nose.tools import eq_
import unittest

class ProcessAlertsTest(unittest.TestCase):

    def setUp(self):
        self.process_alerts = ProcessAlerts()

    def check_memory_test(self):
        data = {u'memory:mb': u'40.0',  u'time': 1327169023}
        rule = {'metric_value': 39, 'above_below': 'above', 'metric_type': 'MB','process': 'test', '_id':'test'}
        alert =  self.process_alerts.check_memory(rule, data)
        eq_(alert, True)

        data = {u'memory:mb': u'39.9',  u'time': 1327169023}
        rule = {'metric_value': 40, 'above_below': 'below', 'metric_type': 'MB','process': 'test', '_id':'test'}
        alert =  self.process_alerts.check_memory(rule, data)
        eq_(alert, True)

        
    def check_cpu_test(self):
        data = {u'cpu:%': u'40.0', u'time': 1327169023}
        rule = {'metric_value': 39, 'above_below': 'above', 'metric_type': '%','process': 'test', '_id':'test'}
        alert =  self.process_alerts.check_cpu(rule, data)
        eq_(alert, True)

        data = { u'cpu:%': u'39.99', u'time': 1327169023}
        rule = {'metric_value': 40, 'above_below': 'below', 'metric_type': '%','process': 'test', '_id':'test'}
        alert =  self.process_alerts.check_cpu(rule, data)
        eq_(alert, True)



########NEW FILE########
__FILENAME__ = system_test
from amonone.alerts.system import SystemAlerts
from nose.tools import eq_
import unittest

class SystemAlertsTest(unittest.TestCase):

    def setUp(self):
        self.system_alerts = SystemAlerts()

    def check_memory_test(self):
        data = {u'memory:free:mb': 1, u'memory:total:mb': 102, u'memory:used:mb': 101}
        rule = {'metric_value': 100, 'above_below': 'above', 'metric_type': 'MB', '_id':'test'}
        alert =  self.system_alerts.check_memory(rule, data)
        eq_(alert, True)

        data = {u'memory:free:mb': 101, u'memory:total:mb': 102, u'memory:used:mb': 1}
        rule = {'metric_value': 2, 'above_below': 'below', 'metric_type': 'MB', "_id": "test"}
        alert =  self.system_alerts.check_memory(rule, data)
        eq_(alert, True)

        data = {u'memory:free:mb': 49, u'memory:total:mb': 100, u'memory:used:%': 49}
        rule = {'metric_value': 50, 'above_below': 'below', 'metric_type': '%', "_id": "test"}
        alert =  self.system_alerts.check_memory(rule, data)
        eq_(alert, True)

        data = {u'memory:free:mb': 51, u'memory:total:mb': 100,  u'memory:used:%': 51}
        rule = {'metric_value': 50, 'above_below': 'above', 'metric_type': '%', "_id": "test"}
        alert =  self.system_alerts.check_memory(rule, data)
        eq_(alert, True)

    def check_cpu_test(self):
        data = {u'idle': 89} # utilization 11.00
        rule = {'metric_value': 10, 'above_below': 'above', 'metric_type': '%', "_id": "test"}
        alert =  self.system_alerts.check_cpu(rule, data)
        eq_(alert, True)

        data = {u'idle': 91} # utilization 9.0
        rule = {'metric_value': 10, 'above_below': 'above', 'metric_type': '%', "_id": "test"}
        alert =  self.system_alerts.check_cpu(rule, data)
        eq_(alert, None)

        data = {u'idle': 89} # utilization 11.00, "_id": "test"}
        rule = {'metric_value': 10, 'above_below': 'below', 'metric_type': '%', "_id": "test"}
        alert =  self.system_alerts.check_cpu(rule, data)
        eq_(alert, None)

        data = {u'idle': 91} # utilization 9.0
        rule = {'metric_value': 10, 'above_below': 'below', 'metric_type': '%', "_id": "test"}
        alert =  self.system_alerts.check_cpu(rule, data)
        eq_(alert, True)

    def check_disk_test(self):
        data = {'sda1': {u'percent': 60, u'used': '6G'}}
        rule = {'metric_value': 55, 'above_below': 'above', 
                'metric_type': '%','metric_options': 'sda1', "_id": "test"}
        alert =  self.system_alerts.check_disk(rule, data)
        eq_(alert, True)

        data = {'sda1': {u'percent': 60, u'used': '6G'}}
        rule = {'metric_value': 61, 'above_below': 'below', 
                'metric_type': '%','metric_options': 'sda1', "_id": "test"}
        alert =  self.system_alerts.check_disk(rule, data)
        eq_(alert, True)

        data = {'sda1': {u'used': '6G'}}
        rule = {'metric_value': 5.9, 'above_below': 'above', 
                'metric_type': 'GB','metric_options': 'sda1', "_id": "test"}
        alert =  self.system_alerts.check_disk(rule, data)
        eq_(alert, True)

        data = {'sda1': {u'used': '6G'}}
        rule = {'metric_value': 6.1, 'above_below': 'below', 
                'metric_type': 'GB','metric_options': 'sda1', "_id": "test"}
        alert =  self.system_alerts.check_disk(rule, data)
        eq_(alert, True)


        data = {'sda1': {u'used': '6G'}} # 6144 MB
        rule = {'metric_value': 6143, 'above_below': 'above', 
                'metric_type': 'MB','metric_options': 'sda1', "_id": "test"}
        alert =  self.system_alerts.check_disk(rule, data)
        eq_(alert, True)

        data = {'sda1': {u'used': '6G'}} # 6144 MB
        rule = {'metric_value': 6145, 'above_below': 'below', 
                'metric_type': 'MB','metric_options': 'sda1', "_id": "test"}
        alert =  self.system_alerts.check_disk(rule, data)
        eq_(alert, True)


    def check_loadavg_test(self):
        data = {u'minute': 1}
        rule = {'metric_value': 0.9, 'above_below': 'above', 'metric_options': 'minute',"_id": "test"}
        alert =  self.system_alerts.check_loadavg(rule, data)
        eq_(alert, True)

        data = {u'minute': 1}
        rule = {'metric_value': 1.1, 'above_below': 'below', 'metric_options': 'minute',"_id": "test"}
        alert =  self.system_alerts.check_loadavg(rule, data)
        eq_(alert, True)

        data = {u'five_minutes': 1}
        rule = {'metric_value': 0.9, 'above_below': 'above', 'metric_options': 'five_minutes',"_id": "test"}
        alert =  self.system_alerts.check_loadavg(rule, data)
        eq_(alert, True)

        data = {u'five_minutes': 1}
        rule = {'metric_value': 1.1, 'above_below': 'below', 'metric_options': 'five_minutes',"_id": "test"}
        alert =  self.system_alerts.check_loadavg(rule, data)
        eq_(alert, True)

        data = {u'fifteen_minutes': 1}
        rule = {'metric_value': 0.9, 'above_below': 'above', 'metric_options': 'fifteen_minutes',"_id": "test"}
        alert =  self.system_alerts.check_loadavg(rule, data)
        eq_(alert, True)

        data = {u'fifteen_minutes': 1}
        rule = {'metric_value': 1.1, 'above_below': 'below', 'metric_options': 'fifteen_minutes',"_id": "test"}
        alert =  self.system_alerts.check_loadavg(rule, data)
        eq_(alert, True)
        

########NEW FILE########
__FILENAME__ = collector
import subprocess
import sys
import re
import os
import glob

from amonone.core.collector.utils import split_and_slugify

class SystemCollector(object):


	def get_uptime(self):

		with open('/proc/uptime', 'r') as line:
			contents = line.read().split()

		total_seconds = float(contents[0])

		MINUTE  = 60
		HOUR    = MINUTE * 60
		DAY     = HOUR * 24

		days    = int( total_seconds / DAY )
		hours   = int( ( total_seconds % DAY ) / HOUR )
		minutes = int( ( total_seconds % HOUR ) / MINUTE )
		seconds = int( total_seconds % MINUTE )

		uptime = "{0} days {1} hours {2} minutes {3} seconds".format(days, hours, minutes, seconds)

		return uptime

	def get_system_info(self):
		distro_info_file = glob.glob('/etc/*-release')
		debian_version = glob.glob('/etc/debian_version')

		debian = False
		distro_info = None
		try: 
			distro_info = subprocess.Popen(["cat"] + distro_info_file, stdout=subprocess.PIPE, close_fds=True,
				).communicate()[0]
		except:
			distro_info = subprocess.Popen(["cat"] + debian_version, stdout=subprocess.PIPE, close_fds=True,
				).communicate()[0]
			debian = True

		system_info = {}
		distro = {}
		if debian is False:
			for line in distro_info.splitlines():
				if re.search('distrib_id', line, re.IGNORECASE):
					info = line.split("=")
					if len(info) == 2:
						distro['distribution'] = info[1]
				if re.search('distrib_release', line, re.IGNORECASE):
					info = line.split("=")
					if len(info) == 2:
						distro['release'] = info[1]
		else:
			distro['distribution'] = 'Debian'
			distro['release'] = distro_info
		
		system_info["distro"] = distro

		processor_info = subprocess.Popen(["cat", '/proc/cpuinfo'], stdout=subprocess.PIPE, close_fds=True,
			).communicate()[0]

		processor = {}
		for line in processor_info.splitlines():
			parsed_line = split_and_slugify(line)
			if parsed_line and isinstance(parsed_line, dict):
				key = parsed_line.keys()[0]
				value = parsed_line.values()[0]
				processor[key] = value

		system_info["processor"] = processor
		  
		return system_info

	def get_memory_info(self):

		memory_dict = {}
		_save_to_dict = ['MemFree', 'MemTotal', 'SwapFree', 'SwapTotal', 'Buffers', 'Cached']

		regex = re.compile(r'([0-9]+)')

		with open('/proc/meminfo', 'r') as lines:

			for line in lines:
				values = line.split(':')
			
				match = re.search(regex, values[1])
				if values[0] in _save_to_dict:
					memory_dict[values[0].lower()] = int(match.group(0)) / 1024 # Convert to MB

			# Unix releases buffers and cached when needed
			buffers = memory_dict.get('buffers', 0)
			cached = memory_dict.get('cached', 0)

			memory_free = memory_dict['memfree']+buffers+cached
			memory_used = memory_dict['memtotal']-memory_free
			memory_percent_used = (float(memory_used)/float(memory_dict['memtotal'])*100)
			
			swap_total = memory_dict.get('swaptotal', 0)
			swap_free = memory_dict.get('swapfree', 0)
			swap_used = swap_total-swap_free
			swap_percent_used = 0
			
			if swap_total > 0:
				swap_percent_used = (float(swap_used)/float(swap_total) * 100)

			extracted_data = {
				"memory:total:mb": memory_dict["memtotal"],
				"memory:free:mb": memory_free,
				"memory:used:mb": memory_used,
				"memory:used:%": memory_percent_used,
				"swap:total:mb":swap_total,
				"swap:free:mb": swap_free,
				"swap:used:mb": swap_used,
				"swap:used:%": swap_percent_used
			}

			# Convert everything to int to avoid float localization problems
			for k,v in extracted_data.items():
				extracted_data[k] = int(v)
		   
			return extracted_data


	def get_disk_usage(self):
		df = subprocess.Popen(['df','-h'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]	

		volumes = df.split('\n')	
		volumes.pop(0)	# remove the header
		volumes.pop()

		data = {}

		_columns = ('volume', 'total', 'used', 'free', 'percent', 'path')	

		previous_line = None

		for volume in volumes:
			line = volume.split(None, 6)

			if len(line) == 1: # If the length is 1 then this just has the mount name
				previous_line = line[0] # We store it, then continue the for
				continue

			if previous_line != None: 
				line.insert(0, previous_line) # then we need to insert it into the volume
				previous_line = None # reset the line

			if line[0].startswith('/'):
				_volume = dict(zip(_columns, line))

				_volume['percent'] = _volume['percent'].replace("%",'') # Delete the % sign for easier calculation later

				# strip /dev/
				_name = _volume['volume'].replace('/dev/', '')

				# Encrypted directories -> /home/something/.Private
				if '.' in _name:
					_name = _name.replace('.','')

				data[_name] = _volume

		return data



	def get_network_traffic(self):

		stats = subprocess.Popen(['sar','-n','DEV','1','1'], 
			stdout=subprocess.PIPE, close_fds=True)\
				.communicate()[0]
		network_data = stats.splitlines()
		data = {}
		for line in network_data:
			if line.startswith('Average'):
				elements = line.split()
				interface = elements[1]
				
				# interface name with . 
				if '.' in interface:
					interface = interface.replace('.','-')

				if interface not in ['IFACE', 'lo']:
					# rxkB/s - Total number of kilobytes received per second  
					# txkB/s - Total number of kilobytes transmitted per second
					
					kb_received = elements[4].replace(',', '.')
					kb_received = format(float(kb_received), ".2f")

					kb_transmitted = elements[5].replace(',', '.')
					kb_transmitted = format(float(kb_transmitted), ".2f")

					data[interface] = {"kb_received": kb_received , "kb_transmitted": kb_transmitted}

		return data

	 
	def get_load_average(self):
		_loadavg_columns = ['minute','five_minutes','fifteen_minutes','scheduled_processes']


		lines = open('/proc/loadavg','r').readlines()

		load_data = lines[0].split()

		_loadavg_values = load_data[:4]

		load_dict = dict(zip(_loadavg_columns, _loadavg_values))	


		# Get cpu cores 
		cpuinfo = subprocess.Popen(['cat', '/proc/cpuinfo'], stdout=subprocess.PIPE, close_fds=True)
		grep = subprocess.Popen(['grep', 'cores'], stdin=cpuinfo.stdout, stdout=subprocess.PIPE, close_fds=True)
		sort = subprocess.Popen(['sort', '-u'], stdin=grep.stdout, stdout=subprocess.PIPE, close_fds=True)\
				.communicate()[0]

		cores = re.findall(r'\d+', sort) 

		try:
			load_dict['cores'] = int(cores[0])
		except:
			load_dict['cores'] = 1 # Don't break if can't detect the cores 

		return load_dict 


	def get_cpu_utilization(self):

		# Get the cpu stats
		mpstat = subprocess.Popen(['sar', '1','1'], 
			stdout=subprocess.PIPE, close_fds=True).communicate()[0]

		cpu_columns = []
		cpu_values = []
		header_regex = re.compile(r'.*?([%][a-zA-Z0-9]+)[\s+]?') # the header values are %idle, %wait
		# International float numbers - could be 0.00 or 0,00
		value_regex = re.compile(r'\d+[\.,]\d+') 
		stats = mpstat.split('\n')

		for value in stats:
			values = re.findall(value_regex, value)
			if len(values) > 4:
				values = map(lambda x: x.replace(',','.'), values) # Replace , with . if necessary
				cpu_values = map(lambda x: format(float(x), ".2f"), values) # Convert the values to float with 2 points precision

			header = re.findall(header_regex, value)
			if len(header) > 4:
				cpu_columns = map(lambda x: x.replace('%', ''), header) 

		cpu_dict = dict(zip(cpu_columns, cpu_values))
		
		return cpu_dict

system_info_collector = SystemCollector()


class ProcessInfoCollector(object):

	def __init__(self):
		memory = system_info_collector.get_memory_info()
		self.total_memory = memory['memory:total:mb']

	def process_list(self):
		stats = subprocess.Popen(['pidstat','-ruht'], 
			stdout=subprocess.PIPE, close_fds=True)\
				.communicate()[0]

		stats_data = stats.splitlines()
		del stats_data[0:2] # Deletes Unix system data

		converted_data = []
		for line in stats_data:
			if re.search('command', line, re.IGNORECASE): # Matches the first line
				header = line.split()
				del header[0] # Deletes the # symbol
			else:
				command = line.split()
				data_dict = dict(zip(header, command))
				
				process_memory_mb = float(self.total_memory/100) * float(data_dict["%MEM"].replace(",",".")) # Convert the % in MB
				memory = "{0:.3}".format(process_memory_mb)
				memory = memory.replace(",", ".")

				cpu = "{0:.2f}".format(float(data_dict["%CPU"].replace(",",".")))
				cpu = cpu.replace(",", ".")
				
				command = data_dict["Command"]

				if not re.search('_', command, re.IGNORECASE):
					extracted_data = {"cpu:%": cpu,
								  "memory:mb": memory,
								  "command": command}
					converted_data.append(extracted_data)

		return converted_data
	
process_info_collector = ProcessInfoCollector()

########NEW FILE########
__FILENAME__ = runner
from amonone.core.collector.collector import system_info_collector, process_info_collector
from amonone.core import settings
from amonone.utils.dates import unix_utc_now
import sys


class Runner(object):

	def system(self):

		system_info_dict = {}

		memory = system_info_collector.get_memory_info()
		cpu = system_info_collector.get_cpu_utilization()
		loadavg = system_info_collector.get_load_average()
		disk = system_info_collector.get_disk_usage()
		network = system_info_collector.get_network_traffic()
		uptime = system_info_collector.get_uptime()

		if memory != False:
			system_info_dict['memory'] = memory

		if cpu != False:
			system_info_dict['cpu'] = cpu

		if loadavg != False:
			system_info_dict['loadavg'] = loadavg

		if disk != False: 
			system_info_dict['disk'] = disk

		if network != False:
			system_info_dict['network'] = network

		if uptime != False:
			system_info_dict['uptime'] = uptime

		system_info_dict['time'] = unix_utc_now()

		return system_info_dict

	def processes(self):

		process_checks = process_info_collector.process_list()

		process_info_dict = {}
		for process in process_checks:
			command = process["command"]
			command = command.replace(".", "")
			del process["command"]
			process_info_dict[command]  = process

		process_info_dict['time'] = unix_utc_now()
		
		return process_info_dict

	def distribution_info(self):
		distribution_info = system_info_collector.get_system_info()

		return distribution_info


runner = Runner()
########NEW FILE########
__FILENAME__ = utils
import subprocess	
import sys
import calendar
import unicodedata
import re
from datetime import datetime

def get_disk_volumes():
		df = subprocess.Popen(['df','-h'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]	
		
		volumes = df.split('\n')	
		volumes.pop(0)	# remove the header
		volumes.pop()

		volumes_list = []
		
		for volume in volumes:
			line = volume.split()
			if line[0].startswith('/'):
				volumes_list.append(line[0].replace('/dev/', ''))

		return volumes_list

def get_network_interfaces():
	if sys.platform == 'darwin':
		return False

	interfaces_info = open('/proc/net/dev' , 'r').readlines()

	interfaces_list = []
	# skip the header 
	for line in interfaces_info[2:]:
		interface, data = line.split(":")
		interface = interface.strip()
		if interface != 'lo':
			interfaces_list.append(interface)

	return interfaces_list


# Used in the collector, saves all the data in UTC
def unix_utc_now():
	d = datetime.utcnow()
	_unix = calendar.timegm(d.utctimetuple())

	return _unix

def slugify(string):

	"""
	Slugify a unicode string.

	"""

	return re.sub(r'[-\s]+', '-',
			unicode(
				re.sub(r'[^\w\s-]', '',
					unicodedata.normalize('NFKD', string)
					.encode('ascii', 'ignore'))
				.strip()
				.lower()))


def split_and_slugify(string, separator=":"):
	_string = string.strip().split(separator)
	
	if len(_string) == 2: # Only key, value
		data = {}
		key = slugify(unicode(_string[0]))
		
		try:
			if len(_string[1]) > 0:
				data[key] = str(_string[1].strip())
		except:
			pass

		return data
	
	else:
		return None
########NEW FILE########
__FILENAME__ = defaults
import sys
try:
    import json
except ImportError:
    import simplejson as json

try:
    config_file = file('/etc/amonone.conf').read()
    config = json.loads(config_file)
except Exception, e:
    print "There was an error in your configuration file (/etc/amonone.conf)"
    raise e

#  Amon Defaults
MONGO = config.get('mongo', "mongodb://127.0.0.1:27017")

_web_app = config.get('web_app', {})

host = _web_app.get('host', 'http://127.0.0.1')

if not host.startswith('http'):
    host = "http://{0}".format(host)

WEB_APP = {
        'host': host,
        'port': _web_app.get('port', 2464)
        }

key = config.get('secret_key', None)

if key != None and len(key) > 0:
    SECRET_KEY = key
else:
    SECRET_KEY = 'TGJKhSSeZaPZr24W6GlByAaLVe0VKvg8qs+8O7y=' #Don't break the dashboard

# Always 
ACL = 'True'

SYSTEM_CHECK_PERIOD = config.get('system_check_period', 60)

TIMEZONE = config.get('timezone','UTC')

PROXY = config.get('proxy', None) # Relative baseurl if true
LOGFILE = config.get("logfile", '/var/log/amonone/amonone.log')
########NEW FILE########
__FILENAME__ = exceptions
class BackendError(Exception):
    """ The storage backend is not working properly """

class ImproperlyConfigured(Exception):
    """ Amon is improperly configured """ 


########NEW FILE########
__FILENAME__ = mongodb
import os
import re 

try:
	import pymongo
except ImportError:
	pymongo = None

try:
	import bson
except ImportError:
	bson = None

from amonone.core.exceptions import ImproperlyConfigured
from amonone.core import settings

class MongoBackend():


	internal_collections = ['sessions','users',]

	database = 'amonone'

	try: 
		if os.environ['AMON_TEST_ENV'] == 'True':
			database = 'amonone_test' # For the test suite
	except: 
		pass
	

	def __init__(self):
		self.pymongo = pymongo
		self.url = settings.MONGO
		self._database = None
		self._connection = None

	def get_connection(self):
		"""Connect to the MongoDB server."""
		from pymongo import MongoClient

		if self._connection is None:
			self._connection = MongoClient(host=self.url, max_pool_size=10)

		return self._connection


	def get_database(self, database=None):
		""""Get or create database  """
		database = database if database !=None else self.database
		
		if self._database is None:
			conn = self.get_connection()
			db = conn[database]
			self._database = db
		
		return self._database


	def get_collection(self, collection):
		db = self.get_database()

		collection = db[collection]

		return collection



	def store_entry(self, data=None, collection=None):
		""" Stores a system entry  """

		collection = self.get_collection(collection)

		if collection:
			collection.save(data, safe=True)	

	def index(self, collection):
		collection = self.get_collection(collection)
		collection.ensure_index([('time', pymongo.DESCENDING)])


	def get_object_id(self,id):
		return bson.objectid.ObjectId(id)

	def string_to_valid_collection_name(self, string):
		return re.sub(r'[^\w]', '', str(string)).strip().lower()

backend = MongoBackend()

########NEW FILE########
__FILENAME__ = settings
from amonone.core import defaults

class Settings(object):

    def __init__(self):
        # update this dict from the defaults dictionary (but only for ALL_CAPS settings)
        for setting in dir(defaults):
            if setting == setting.upper():
                setattr(self, setting, getattr(defaults, setting))




########NEW FILE########
__FILENAME__ = mongodb_test
import unittest
from nose.tools import eq_
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from amonone.core.mongodb import backend

class TestMongoBackend(unittest.TestCase):
	
	def test_get_database(self):
		db = backend.get_database()
		eq_(db, Database(MongoClient(u'127.0.0.1', 27017), u'amon_test'))

	def test_get_connection(self):
		connection = backend.get_connection()
		eq_(connection, MongoClient(u'127.0.0.1', 27017))


	def test_get_server_system_collection(self):
		valid_server_key = {"key": 'testserverkey'}
		collection = backend.get_server_system_collection(valid_server_key)

		eq_(collection,
			Collection(Database(MongoClient('127.0.0.1', 27017), u'amon_test'), u'testserverkey_system')
		)

	def test_get_server_process_collection(self):
		valid_server_key = {"key": 'testserverkey'}
		collection = backend.get_server_processes_collection(valid_server_key)

		eq_(collection,
			Collection(Database(MongoClient('127.0.0.1', 27017), u'amon_test'), u'testserverkey_processes')
		)


	def test_string_to_valid_collection_name(self):
		name = 'TEST123456'
		valid_name = backend.string_to_valid_collection_name(name)
		eq_(valid_name, 'test123456')


	def test_store_entry(self):
		db = backend.get_collection('logs')
		db.remove()
		
		db.insert({})

		total_entries = db.count()
		eq_(1, total_entries)

		db.insert({})
		total_entries = db.count()
		eq_(2, total_entries)


	def test_store_entries(self):
	  db = backend.get_collection('cpu')
	  db.remove()
	  
	  entries_list = {'cpu': {'time': 1313096288, 'idle': 93, 'wait': 0, 'user': 2, 'system': 5}}

	  backend.store_entries(entries_list)

	  total_entries = db.count()
	  eq_(1, total_entries)



########NEW FILE########
__FILENAME__ = log
import logging
from amonone.core import settings

logging.basicConfig(level=logging.ERROR, filename=settings.LOGFILE,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S')


########NEW FILE########
__FILENAME__ = models
from amonone.web.apps.core.basemodel import BaseModel

class EmailModel(BaseModel):

	def __init__(self):
		super(EmailModel, self).__init__()
		self.collection = self.mongo.get_collection('email_settings')


	def save_email_details(self, data=None):
		self.collection.remove()
		self.collection.insert(data)

	def get_email_details(self):
		return self.collection.find_one()


class EmailRecepientModel(BaseModel):

	def __init__(self):
		super(EmailRecepientModel, self).__init__()
		self.collection = self.mongo.get_collection('email_recepients')

email_model = EmailModel()
email_recepient_model = EmailRecepientModel()

########NEW FILE########
__FILENAME__ = sender
from os.path import join, abspath, dirname

from mailtools import SMTPMailer, ThreadedMailer
from jinja2 import Environment, FileSystemLoader
from tornado import escape

from amonone.mail.models import email_model
from amonone.utils.dates import dateformat_local


def send_mail(recepients=None, subject=None, template=None,  template_data=None):
	connection_details = email_model.get_email_details()

	port = int(connection_details['port'])
	security = connection_details['security'] if connection_details['security'] != 'None' else None

	mailer = ThreadedMailer(SMTPMailer(connection_details['address'], port, 
					username = connection_details['username'],
					password = connection_details['password'],
					transport_args = {'security': security},
					log_file = '/var/log/amonone/amonone-mailer.log',
					log_messages=False))


	EMAIL_ROOT = abspath(dirname(__file__))
	TEMPLATES_DIR =  join(EMAIL_ROOT, 'templates')

	env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
	env.filters['date_local'] = dateformat_local

	template_file = env.get_template("{0}.html".format(template))
	rendered_template = template_file.render(template_data=template_data)

	message = escape.to_unicode(rendered_template)

	subject = escape.to_unicode(subject)

	email_recepients = [x['email'] for x in recepients]

	try: 
		mailer.send_html(connection_details['from_'], email_recepients, subject, message)
	except Exception, e:
		print e
		raise e 




########NEW FILE########
__FILENAME__ = models
from amonone.web.apps.core.basemodel import BaseModel

class SMSModel(BaseModel):

	def __init__(self):
		super(SMSModel, self).__init__()
		self.collection = self.mongo.get_collection('sms_settings')

	def save(self, data=None):
		self.collection.remove()
		self.collection.insert(data)

	def get(self):
		return self.collection.find_one()

class SMSRecepientModel(BaseModel):

	def __init__(self):
		super(SMSRecepientModel, self).__init__()
		self.collection = self.mongo.get_collection('sms_recepients')

		

sms_model = SMSModel()
sms_recepient_model = SMSRecepientModel()
########NEW FILE########
__FILENAME__ = sender
from os.path import join, abspath, dirname
import threading

from twilio.rest import TwilioRestClient
from jinja2 import Environment, FileSystemLoader

from amonone.utils.dates import dateformat_local
from amonone.sms.models import sms_model


def _send_sms_in_thread(client=None, from_=None, to=None, body=None):
	try:
		client.sms.messages.create(to=to,
									 from_=from_,
									  body=body)
	except Exception, e:
		raise e
		logging.exception("Can't send SMS")



def send_test_sms(recepient=None):
	details = sms_model.get()
	client = TwilioRestClient(details['account'], details['token'])

	t = threading.Thread(target=_send_sms_in_thread, 
				kwargs={"client": client,
					"from_": details['from_'],
					"to": recepient,
					"body": "Amon alert!"
				})
	t.start()


def render_template(alert=None, template=None):

		ROOT = abspath(dirname(__file__))
		TEMPLATES_DIR =  join(ROOT, 'templates')
		
		env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
		env.filters['date_local'] = dateformat_local


		template_file = env.get_template(template)		
		rendered_template = template_file.render(alert=alert)
		
		return rendered_template


def send_sms(alert=None, recepients=None, template=None):
	details = sms_model.get()
	
	try:
		client = TwilioRestClient(details['account'], details['token'])
	except:
		client = None
	
	
	if client != None:
		body = render_template(alert=alert, template=template)

		for recepient in recepients:
			t = threading.Thread(target=_send_sms_in_thread, 
				kwargs={"client": client,
					"from_": details['from_'],
					"to": recepient['phone'],
					"body": body
				}
			)
			t.start()
########NEW FILE########
__FILENAME__ = sms_sender_test
from amonone.sms.sender import render_template
from nose.tools import *
import unittest

# class SMSRenderTest(unittest.TestCase):

# 	def render_test(self):
# 		alert = {"rule_type" : "server", "metric_type_value" : "%", "threshold" : "10",
# 				"metric_value" : "10", "metric_type" : "more_than", "metric" : "CPU",
# 				"metric_options" : "", "server_name": "test"} 
# 		result = render_template(alert=alert, template='server')
# 		eq_(result, u'test:cpu > 10% \n')
		
# 		alert = {"rule_type" : "server", "metric_type_value" : "MB", "threshold" : "10",
# 				"metric_value" : "10", "metric_type" : "more_than", "metric" : "Memory",
# 				"metric_options" : "", "server_name": "test"} 
# 	   result = render_template(alert=alert, template='server')
# 		eq_(result, u'test:memory > 10MB \n')
		
# 		alert = {"rule_type" : "server", "metric_type_value" : "GB", "threshold" : "10",
# 				"metric_value" : "10", "metric_type" : "more_than", "metric" : "Disk",
# 				"metric_options" : "sda1", "server_name": "test"} 
# 	   result = render_template(alert=alert, template='server')
# 		eq_(result, u'test:disk(sda1) > 10GB \n')
		
# 		alert = {"rule_type" : "server", "metric_type_value" : "", "threshold" : "10",
# 				"metric_value" : "10", "metric_type" : "more_than", "metric" : "Loadavg",
# 				"metric_options" : "minute", "server_name": "test"} 
# 	   result = render_template(alert=alert, template='server')
# 		eq_(result, u'test:loadavg(minute) > 10 \n')
		






########NEW FILE########
__FILENAME__ = dates
from __future__ import division
from amonone.core import settings
from datetime import datetime
import calendar
from pytz import timezone
import pytz
import time

def localtime_utc_timedelta(_timezone=None):
    _timezone = _timezone if _timezone else settings.TIMEZONE
    
    local_timezone = timezone(_timezone)
    local_time = datetime.now(local_timezone)

    is_dst = False # Check the local timezone for Daylight saving time
    if local_time.dst():
        is_dst = True

    naive_local_time = local_time.replace(tzinfo=None)

    # Return 0 for UTC
    if _timezone == 'UTC': 
        return ('positive', 0)

    # timedelta betweeen the local timezone and UTC
    td = local_timezone.utcoffset(naive_local_time, is_dst=is_dst)
    offset = (td.microseconds + (td.seconds + td.days * 24 * 3600)* 10**6 ) / 10.0**6

    if offset < 0:
        # Negative timedelta is actually an UTC+ timezone
        offset = -offset
        offset_list = ('negative', int(offset))
    else:
        offset_list = ('positive', int(offset))

    return offset_list


# Converts date strings: '31-07-2011-17:46' to an UTC datetime object using the
# timezone in the config file
# The _timezone parameter is used only in the test suite
def datestring_to_utc_datetime(datestring, format="%d-%m-%Y-%H:%M", _timezone=None):
    _timezone = _timezone if _timezone else settings.TIMEZONE
    _datetime = datetime.strptime(datestring, format)
    local_timezone = timezone(_timezone)
    
    # Adjust for Daylight savings time
    local_datetime = local_timezone.localize(_datetime)
    utc_datetime =  local_datetime.astimezone(pytz.UTC)

    return utc_datetime
    
# Internal function, always pass UTC date objects
# Converts datetime objects to unix integers
def datetime_to_unixtime(datetime):
    return int(calendar.timegm(datetime.timetuple()))

# Converts date string to unix UTC time
def datestring_to_utc_unixtime(datestring):
    datetime_object = datestring_to_utc_datetime(datestring)
    
    return datetime_to_unixtime(datetime_object)

def utc_unixtime_to_localtime(unixtime, _timezone=None):
    _timezone = _timezone if _timezone else settings.TIMEZONE
    local_timezone = timezone(_timezone)
    
    unixtime = float(unixtime)
    utc = pytz.UTC
    utc_datetime = utc.localize(datetime.utcfromtimestamp(unixtime))
    local_datetime = utc_datetime.astimezone(local_timezone)

    local_unix_datetime = datetime_to_unixtime(local_datetime)
    local_unix_datetime = int(local_unix_datetime)

    return local_unix_datetime

# Used in the collector, saves all the data in UTC
def unix_utc_now():
    d = datetime.utcnow()
    _unix = calendar.timegm(d.utctimetuple())

    return _unix

def utc_now_to_localtime(_timezone=None):
    _timezone = _timezone if _timezone else settings.TIMEZONE
    now = unix_utc_now()
    local_unix_time = utc_unixtime_to_localtime(now, _timezone)

    return local_unix_time

 
def dateformat(value, format='%d-%m-%Y-%H:%M'):
    # Converts unix time to a readable date format
    try:
        _ = datetime.utcfromtimestamp(value)
        return _.strftime(format)
    except:
        return None

# Localized unix timestamp
def dateformat_local(value, format='%d-%m-%Y-%H:%M'):
    value = utc_unixtime_to_localtime(value)

    return dateformat(value)

def timeformat(value, format='%H:%M'):
    # Converts unix time to a readable 24 hour-minute format
    _ = datetime.utcfromtimestamp(value)
    return _.strftime(format)

########NEW FILE########
__FILENAME__ = dates_test
from amonone.utils.dates import *
from nose.tools import eq_
import datetime
import pytz
from pytz import timezone
import unittest


class TestDates(unittest.TestCase):

    def test_datestring_to_utc_datetime(self):
        # UTC
        result = datestring_to_utc_datetime("25-02-2012-00:00",_timezone='Europe/London') 
        eq_(result, datetime.datetime(2012, 2, 25, 0, 0, tzinfo=pytz.UTC))

        # UTC
        result = datestring_to_utc_datetime("25-02-2012-00:00",_timezone='UTC') 
        eq_(result, datetime.datetime(2012, 2, 25, 0, 0, tzinfo=pytz.UTC))

        # +2 ( 0:00 in Sofia is 22:00 UTC )
        result = datestring_to_utc_datetime("25-02-2012-00:00", _timezone='Europe/Sofia') 
        eq_(result, datetime.datetime(2012, 2, 24, 22, 0, tzinfo=pytz.UTC))

        # -7 ( 0:00 in Edmonton is 07:00 UTC )
        result = datestring_to_utc_datetime("25-02-2012-00:00", _timezone='America/Edmonton') 
        eq_(result, datetime.datetime(2012, 2, 25, 7, 0, tzinfo=pytz.UTC))

        # +8 ( 0:00 in Hong Kong is 16:00 UTC )
        result = datestring_to_utc_datetime("25-02-2012-00:00", _timezone='Asia/Hong_Kong') 
        eq_(result, datetime.datetime(2012, 2, 24, 16, 0, tzinfo=pytz.UTC))

    def test_datetime_to_unixtime(self):
        date = datetime.datetime(2012, 2, 25, 0, 0, tzinfo=pytz.UTC) 
        result = datetime_to_unixtime(date)
        eq_(result, 1330128000)

    def test_utc_unixtime_to_localtime(self):
        # 1340000000 -> Mon, 18 Jun 2012 06:13:20 GMT 
        # UTC+3 -> Eastern Europe summer time 
        result = utc_unixtime_to_localtime(1340000000, _timezone='Europe/Sofia') 
        eq_(result, 1340010800) 

        # UTC+5  
        result = utc_unixtime_to_localtime(1340000000, _timezone='Antarctica/Mawson') 
        eq_(result, 1340018000) 
        
        # UTC-6 
        result = utc_unixtime_to_localtime(1340000000, _timezone='America/Belize') 
        eq_(result, 1339978400) 


    def test_localtime_utc_timedelta(self):
        
        # +5 ( 0:00 in Mawson is 19:00 UTC ) # NO DST changes till 2019
        result = localtime_utc_timedelta(_timezone='Antarctica/Mawson') 
        eq_(result, ('positive', 18000))

        _timezone = 'Europe/Sofia'
        tz_class = timezone(_timezone) # From pytz
        local_time = datetime.datetime.now(tz_class)

        if local_time.dst():
            # +3 ( 01:00 in Sofia is 22:00 UTC ) # DST
            result = localtime_utc_timedelta(_timezone=_timezone) 
            eq_(result, ('positive', 10800))
        else:
             # +2 ( 00:00 in Sofia is 22:00 UTC )
            result = localtime_utc_timedelta(_timezone=_timezone) 
            eq_(result, ('positive', 7200))


        _timezone = 'America/Edmonton'
        tz_class = timezone(_timezone) # From pytz
        local_time = datetime.datetime.now(tz_class)

        if local_time.dst():
            # -6 ( 0:00 in Edmonton is 06:00 UTC ) DST
            result = localtime_utc_timedelta(_timezone=_timezone) 
            eq_(result, ('negative', 21600))
        else:
            # -7 ( 0:00 in Edmonton is 07:00 UTC )
            result = localtime_utc_timedelta(_timezone=_timezone) 
            eq_(result, ('negative', 25200))

        # UTC
        result = localtime_utc_timedelta(_timezone='UTC')
        eq_(result, ('positive', 0))


    def test_utc_now_to_localtime(self):
        # +5 ( 0:00 in Mawson is 19:00 UTC )
        utc_now = unix_utc_now()
        result = utc_now_to_localtime(_timezone='Antarctica/Mawson')
        eq_(result, utc_now+18000)

        _timezone = 'Europe/Sofia'
        tz_class = timezone(_timezone) # From pytz
        local_time = datetime.datetime.now(tz_class)
        
        utc_now = unix_utc_now()
        
        if local_time.dst():
            # +3 ( 0:00 in Sofia is 22:00 UTC ) # DST
            result = utc_now_to_localtime(_timezone=_timezone)
            eq_(result, utc_now+10800)
        else: 
            # +2 ( 0:00 in Sofia is 22:00 UTC )
            result = utc_now_to_localtime(_timezone=_timezone)
            eq_(result, utc_now+7200)


    def test_unix_utc_now(self):
        result = unix_utc_now()
        assert isinstance(result, int)

########NEW FILE########
__FILENAME__ = forms
import formencode
from formencode import validators



class EditServerRuleForm(formencode.Schema):
	allow_extra_fields = True
	metric_value = formencode.All(validators.Number(not_empty=True))
	threshold = formencode.All(validators.Number(not_empty=True))

class AddServerRuleForm(formencode.Schema):
	allow_extra_fields = True
	metric = formencode.All(validators.PlainText(not_empty=True))
	metric_value = formencode.All(validators.Number(not_empty=True))
	threshold = formencode.All(validators.Number(not_empty=True))


class EditProcessRuleForm(formencode.Schema):
	allow_extra_fields = True
	metric_value = formencode.All(validators.Number(not_empty=True))
	threshold = formencode.All(validators.Number(not_empty=True))

class AddProcessRuleForm(formencode.Schema):
	allow_extra_fields = True
	process = formencode.All(validators.PlainText(not_empty=True))
	check = formencode.All(validators.PlainText(not_empty=True))
	metric_value = formencode.All(validators.Number(not_empty=True))
	threshold = formencode.All(validators.Number(not_empty=True))
########NEW FILE########
__FILENAME__ = models
from amonone.web.apps.core.basemodel import BaseModel
from amonone.sms.models import sms_recepient_model
from amonone.mail.models import email_recepient_model
from amonone.utils.dates import unix_utc_now


class AlertsModel(BaseModel):

	def __init__(self):
		super(AlertsModel, self).__init__()
		self.collection = self.mongo.get_collection('alerts')


	def save(self, data):
		self.collection.insert(data)
		self.collection.ensure_index([('rule_type', self.desc)])

	def get_by_id(self, alert_id):
		alert_id =  self.mongo.get_object_id(alert_id)
		alert = self.collection.find_one({"_id": alert_id})

		return alert

	def update(self, data, id):
		object_id =  self.mongo.get_object_id(id)

		self.collection.update({"_id": object_id}, {"$set": data}, upsert=True)

	def clear_alert_history(self, alert_id):
		alert_id =  self.mongo.get_object_id(alert_id)
		self.collection.update({"_id": alert_id}, {"$set": {"history": [], "last_trigger": 1}})

	def get_alerts(self, type=None):
		params = {"rule_type": type}
		
		
		rules = self.collection.find(params).count()

		if rules == 0:
			return None
		else:
			rules = self.collection.find(params)

			rules_list = []
			for rule in rules:
				sms_recepients = rule.get('sms_recepients', None)
				if sms_recepients:
					rule['sms_recepients'] = [sms_recepient_model.get_by_id(x) for x in sms_recepients]

				email_recepients = rule.get('email_recepients', None)
				if email_recepients:
					rule['email_recepients'] = [email_recepient_model.get_by_id(x) for x in email_recepients]
				
				rules_list.append(rule)

			return rules_list

	def delete_server_alerts(self):
		rules = self.collection.remove({'$or' : [{'rule_type':'server'}, {'rule_type':'process'}], })

	# Exclude group alerts
	def get_all_alerts(self, type=None):
		
		params = {'$or' : [{'rule_type':'server'}, {'rule_type':'process'}]}
		
		if type != None:
			params = {'$or' : [{'rule_type':type}]}

		count = self.collection.find(params).count()

		if count == 0:
			return None
		else:
			rules = self.collection.find(params)
		
			rules_list = []
			for rule in rules:
				sms_recepients = rule.get('sms_recepients', None)
				if sms_recepients:
					rule['sms_recepients'] = [sms_recepient_model.get_by_id(x) for x in sms_recepients]

				email_recepients = rule.get('email_recepients', None)
				if email_recepients:
					rule['email_recepients'] = [email_recepient_model.get_by_id(x) for x in email_recepients]
				
				rules_list.append(rule)

			return rules_list


	# System and process alerts
	def save_occurence(self, alerts):
		# Format: {'cpu': [{'alert_on': 2.6899999999999977, 'rule': '4f55da92925d75158d0001e0'}}]}
		for key, values_list in alerts.iteritems():
			for value in values_list:
				alert_on = value.get('alert_on', None)
				rule_id = value.get('rule', None)
				metric_type = value.get('metric_type', None)
			
				if alert_on is not None:
					alert_on = "{0:.2f}".format(float(alert_on)) 

				alert = self.get_by_id(rule_id)

				history = alert.get('history', [])
				threshold = alert.get('threshold', 1)
				last_trigger = alert.get('last_trigger', 1)

				trigger = True if int(last_trigger) >= int(threshold) else False
				history.append({"value": alert_on, "time": unix_utc_now(),
				 	"trigger": trigger, "metric_type": metric_type})

				# Reset the last trigger count
				if trigger is True:
					last_trigger = 1
				else:
					last_trigger = last_trigger+1

				alert_id =  self.mongo.get_object_id(rule_id)
				self.collection.update({"_id": alert_id}, {"$set": {"history": history, "last_trigger": last_trigger}})

	
	def mute(self, alert_id):
		alert_id = self.mongo.get_object_id(alert_id)
		result = self.collection.find_one({"_id": alert_id})
		current_mute = result.get('mute', None)

		toggle = False if current_mute is True else True

		self.collection.update({"_id": alert_id}, {"$set": {"mute": toggle}})


alerts_model = AlertsModel()
########NEW FILE########
__FILENAME__ = models_tests
import unittest
from nose.tools import eq_
from amonone.web.apps.alerts.models import AlertsModel, AlertGroupsModel


class AlertGroupsModelTest(unittest.TestCase):

	def setUp(self):
		self.model = AlertGroupsModel()
		self.collection = self.model.mongo.get_collection('alert_groups')
		self.servers_collection = self.model.mongo.get_collection('servers')
		self.history_collection = self.model.mongo.get_collection('alert_groups_history')
		self.alerts_collection = self.model.mongo.get_collection('alerts')


	def save_test(self):
		self.collection.remove()
		self.model.save({'name': 'group'})
		result = self.collection.find_one()

		eq_(result['name'], 'group')
		

	def get_alerts_for_group_test(self):
		self.alerts_collection.remove()

		self.alerts_collection.insert({'group': 'test', 'rule_type': 'group'})
		self.alerts_collection.insert({'group': 'test', 'rule_type': 'group'})
		
		result = self.model.get_alerts_for_group('test')

		eq_(len(result), 2)


	def save_occurence_test(self):
		self.collection.remove()
		self.history_collection.remove()
		self.model.save({'name': 'group'})
		group = self.collection.find_one()
		group_id = str(group['_id'])

		self.servers_collection.remove()
		self.servers_collection.insert({'alert_group': group_id, 'name': 'test'})

		server = self.servers_collection.find_one()

		rule = {
			"metric_value": "0.1",
			"metric": "CPU",
			"metric_type": "%",
			"threshold": "1",
			"above_below": "above",
			"rule_type": "group",
			"group": group_id,
		}

		self.alerts_collection.remove()
		self.alerts_collection.insert(rule)

		rule = self.alerts_collection.find_one()
		rule_id = str(rule['_id'])

		alerts = {'cpu': [{'alert_on': 14, 'rule': rule_id}]}
		self.model.save_occurence(alerts, server)

		alerts = {'cpu': [{'alert_on': 25, 'rule': rule_id}]}
		self.model.save_occurence(alerts, server)

		result = self.history_collection.find_one()
		
		eq_(len(result['history']), 2)
		eq_(result['server'], server['_id'])
		eq_(result['alert'], rule['_id'])


	def clear_alert_history_test(self):
		self.collection.remove()
		self.history_collection.remove()
		self.model.save({'name': 'group'})
		group = self.collection.find_one()
		group_id = str(group['_id'])

		self.servers_collection.remove()
		self.servers_collection.insert({'alert_group': group_id, 'name': 'test'})

		server = self.servers_collection.find_one()

		rule = {
			"metric_value": "0.1",
			"metric": "CPU",
			"metric_type": "%",
			"threshold": "1",
			"above_below": "above",
			"rule_type": "group",
			"group": group_id,
		}

		self.alerts_collection.remove()
		self.alerts_collection.insert(rule)

		rule = self.alerts_collection.find_one()
		rule_id = str(rule['_id'])

		alerts = {'cpu': [{'alert_on': 14, 'rule': rule_id}]}
		self.model.save_occurence(alerts, server)

		result = self.history_collection.find_one()
		
		eq_(len(result['history']), 1)


		self.model.clear_alert_history(rule['_id'], server['_id'], {})
		result = self.history_collection.find_one()
		
		eq_(result['history'], [])


	def get_history_test(self):
		self.collection.remove()
		self.history_collection.remove()
		self.model.save({'name': 'group'})
		group = self.collection.find_one()
		group_id = str(group['_id'])

		self.servers_collection.remove()
		self.servers_collection.insert({'alert_group': group_id, 'name': 'test'})

		server = self.servers_collection.find_one()

		rule = {
			"metric_value": "0.1",
			"metric": "CPU",
			"metric_type": "%",
			"threshold": "1",
			"above_below": "above",
			"rule_type": "group",
			"group": group_id,
		}

		self.alerts_collection.remove()
		self.alerts_collection.insert(rule)

		rule = self.alerts_collection.find_one()
		rule_id = str(rule['_id'])

		alerts = {'cpu': [{'alert_on': 14, 'rule': rule_id}]}
		self.model.save_occurence(alerts, server)

		history = self.model.get_history(rule['_id'], server['_id'])

		eq_(len(history), 1)


	def delete_alerts_for_group_test(self):
		self.alerts_collection.remove()
		self.collection.remove()
		self.history_collection.remove()
		self.model.save({'name': 'group'})
		group = self.collection.find_one()
		group_id = str(group['_id'])

		self.servers_collection.remove()
		self.servers_collection.insert({'alert_group': group_id, 'name': 'test'})

		server = self.servers_collection.find_one()

		rule = {
			"metric_value": "0.1",
			"metric": "CPU",
			"metric_type": "%",
			"threshold": "1",
			"above_below": "above",
			"rule_type": "group",
			"group": group_id,
		}

		self.alerts_collection.remove()
		self.alerts_collection.insert(rule)

		result = self.alerts_collection.count()
		eq_(result, 1)

		self.model.delete_alerts_for_group(group_id)

		result = self.alerts_collection.count()
		eq_(result, 0)


class AlertsModelTest(unittest.TestCase):

	def setUp(self):
		self.model = AlertsModel()
		self.collection = self.model.mongo.get_collection('alerts')
		self.server_collection = self.model.mongo.get_collection('servers')

	def save_alert_test(self):
		self.collection.remove()
		self.model.save({'rule': "test"})
		eq_(self.collection.count(), 1)

	def update_test(self):
		self.collection.remove()
		self.model.save({'rule': "test"})

		alert = self.collection.find_one()
		alert_id = str(alert['_id'])

		self.model.update({'rule': 'updated_test'}, alert_id)

		alert = self.collection.find_one()

		eq_(alert['rule'], 'updated_test')
	

	def mute_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test", "key": "test_me"})
		alert = self.collection.find_one()
		alert_id = str(alert['_id'])

		self.model.mute(alert_id)

		result = self.collection.find_one()
		eq_(result["mute"], True)

		self.model.mute(alert_id)

		result = self.collection.find_one()
		eq_(result["mute"], False)


	def get_server_alerts_test(self):
		self.collection.remove()
		self.server_collection.remove()
		self.server_collection.insert({"name" : "test", "key": "test_me"})
		server = self.server_collection.find_one()
		server_id = str(server['_id'])

		rule = { "server": server_id, "rule_type": 'server', 'metric': 2}
		self.collection.insert(rule)
		
		rule = { "server": server_id, "rule_type": 'server', 'metric': 1}
		self.collection.insert(rule)

		rules = self.model.get_alerts_for_server(type='server', server_id=server_id)

		eq_(len(rules), 2)
		self.collection.remove()


	def get_alerts_test(self):
		self.collection.remove()
		rule = { "server": 'test' , "rule_type": 'bla', 'metric': 2}
		self.collection.insert(rule)

		rules = self.model.get_all_alerts(type='bla')
		eq_(len(rules), 1)
		self.collection.remove()

	def delete_alerts_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test", "key": "test_me"})
		rule = self.collection.find_one()

		self.model.delete(rule['_id'])

		result = self.collection.count()
		eq_(result,0)


	def save_occurence_test(self):
		self.collection.remove()
		self.collection.insert({"rule_type" : "server",
			"metric_type_value" : "%", 
			"metric_value" : "10", "metric_type" : "more_than", "metric" : "CPU", "threshold": 4})
		
		rule = self.collection.find_one()
		rule_id = str(rule['_id'])

		self.model.save_occurence({'cpu': [{'alert_on': 11, 'rule': rule_id}]})

		rule = self.collection.find_one()
		eq_(len(rule['history']), 1)

		self.model.save_occurence({'cpu': [{'alert_on': 11, 'rule': rule_id}]})
		self.model.save_occurence({'cpu': [{'alert_on': 11, 'rule': rule_id}]})
		
		rule = self.collection.find_one()
		eq_(len(rule['history']), 3)
		
		# Test with unicode
		self.model.save_occurence({'cpu': [{'alert_on': u'22.0', 'rule': rule_id}]})
		rule = self.collection.find_one()
		eq_(len(rule['history']), 4)

		self.collection.remove()

		eq_(rule['history'][3]['trigger'], True)


	def get_all_alerts_test(self):
		self.collection.remove()
		self.collection.insert({"rule_type" : "server"})
		self.collection.insert({"rule_type" : "process"})

		result = self.model.get_all_alerts()
		eq_(len(result), 2)

		self.collection.remove()
	

	def delete_server_alerts_test(self):
		
		self.collection.remove()
		self.collection.insert({"rule_type" : "process", "server": "test-server"})
		self.collection.insert({"rule_type" : "server", "server": "test-server"})
		
		self.collection.insert({"rule_type" : "log", "server": "test-server"})
		self.collection.insert({"rule_type" : "dummy", "server": "test-server"})
		self.collection.insert({"rule_type" : "dummy", "server": "test-server"})

		self.model.delete_server_alerts("test-server")

		eq_(self.collection.count(), 3)
		self.collection.remove()


	def get_by_id_test(self):
		self.collection.remove()
		self.collection.insert({"rule_type" : "process", "server": "test-server"})
		alert = self.collection.find_one()

		alert_from_model = self.model.get_by_id(alert['_id'])
		eq_(alert, alert_from_model)


	def clear_alert_history_test(self):
		self.collection.remove()

		self.collection.insert({"rule_type" : "server",
			"metric_type_value" : "%", 
			"metric_value" : "10", "metric_type" : "more_than", "metric" : "CPU", "threshold": 4})
		
		rule = self.collection.find_one()
		rule_id = str(rule['_id'])

		self.model.save_occurence({'cpu': [{'alert_on': 11, 'rule': rule_id}]})
		self.model.save_occurence({'cpu': [{'alert_on': 11, 'rule': rule_id}]})
		self.model.save_occurence({'cpu': [{'alert_on': 11, 'rule': rule_id}]})

		rule = self.collection.find_one()
		eq_(len(rule['history']), 3)

		self.model.clear_alert_history(rule_id)
		
		rule = self.collection.find_one()
		eq_(len(rule['history']), 0)
		eq_(rule['last_trigger'], 1)
########NEW FILE########
__FILENAME__ = views
from tornado.web import authenticated
from amonone.web.apps.core.baseview import BaseView
from formencode.validators import Invalid as InvalidForm
from amonone.web.apps.alerts.models import alerts_model
from amonone.web.apps.core.models import server_model
from amonone.web.settings import (
	process_metrics, server_metrics, common_metrics
)
from amonone.web.apps.alerts.forms import (
	AddServerRuleForm, AddProcessRuleForm,
	EditServerRuleForm, EditProcessRuleForm,
)
from amonone.mail.models import email_recepient_model
from amonone.sms.models import sms_recepient_model


class AlertsView(BaseView):
	def initialize(self):
		self.current_page = 'alerts'
		super(AlertsView, self).initialize()

	@authenticated
	def get(self):

		system_alerts = alerts_model.get_alerts(type='server')
		process_alerts = alerts_model.get_alerts(type='process')

					
		self.render('alerts/view.html',	
				process_metrics=process_metrics,
				server_metrics=server_metrics,
				common_metrics=common_metrics,
				system_alerts=system_alerts,
				process_alerts=process_alerts	
				)

class AddSystemAlertView(BaseView):

	def initialize(self):
		self.current_page = 'alerts'
		super(AddSystemAlertView, self).initialize()

	@authenticated
	def get(self):

		server = server_model.get_one()

		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)
		email_recepients = email_recepient_model.get_all()
		sms_recepients = sms_recepient_model.get_all()

		self.delete_session_key('errors')
		self.delete_session_key('form_data')

		self.render('alerts/add_server_alert.html',
				email_recepients=email_recepients,
				sms_recepients=sms_recepients,
				process_metrics=process_metrics,
				server_metrics=server_metrics,
				common_metrics=common_metrics,
				errors=errors,
				server=server,
				form_data=form_data
		)


	@authenticated
	def post(self):
		form_data = {
				"metric" : self.get_argument('metric', None),         
				"metric_value" : self.get_argument('metric_value', None),         
				"above_below" : self.get_argument('above_below', None),         
				"metric_type": self.get_argument('metric_type', None),
				"metric_options": self.get_argument('metric_options',None),
				"threshold": self.get_argument('threshold', None),
				"email_recepients": self.get_arguments('email', None),
				"sms_recepients": self.get_arguments('sms', None),
				"rule_type": 'server'
		}
		
		try:
			AddServerRuleForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			alerts_model.save(form_data)
			self.redirect(self.reverse_url('alerts'))
		
		except InvalidForm, e:
			print e.unpack_errors()
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect(self.reverse_url('add_server_alert'))


class DeleteServerAlertView(BaseView):

	def initialize(self):
		super(DeleteServerAlertView, self).initialize()

	@authenticated
	def get(self, param=None):
		alerts_model.delete(param)
		self.redirect(self.reverse_url('alerts'))

class AddProcessAlertView(BaseView):

	def initialize(self):
		self.current_page = 'alerts'
		super(AddProcessAlertView, self).initialize()

	@authenticated
	def get(self):

		server = server_model.get_one()
		
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)
		email_recepients = email_recepient_model.get_all()
		sms_recepients = sms_recepient_model.get_all()


		self.delete_session_key('errors')
		self.delete_session_key('form_data')

		self.render('alerts/add_process_alert.html',
				email_recepients=email_recepients,
				sms_recepients=sms_recepients,
				process_metrics=process_metrics,
				errors=errors,
				form_data=form_data,
				server=server
		)


	@authenticated
	def post(self):
		form_data = {
				"process" : self.get_argument('process', None),  
				"above_below" : self.get_argument('above_below', None),  
				"check" : self.get_argument('check', None),        
				"metric_value" : self.get_argument('metric_value', None),         
				"metric_type" : self.get_argument('metric_type', None),                         
				"threshold": self.get_argument('threshold', None),
				"email_recepients": self.get_arguments('email', None),
				"sms_recepients": self.get_arguments('sms', None),
				"rule_type": 'process'
		}

		try:
			AddProcessRuleForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			alerts_model.save(form_data)
			self.redirect(self.reverse_url('alerts'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect('/alerts/process')

class DeleteProcessAlertView(BaseView):

	def initialize(self):
		super(DeleteProcessAlertView, self).initialize()

	@authenticated
	def get(self, param=None):
		alerts_model.delete(param)
		self.redirect(self.reverse_url('alerts'))


class EditServerAlertView(BaseView):

	def initialize(self):
		self.current_page = 'alerts'
		super(EditServerAlertView, self).initialize()

	@authenticated
	def get(self, alert_id):
		alert = alerts_model.get_by_id(alert_id)

		server = server_model.get_one()

	
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)
		email_recepients = email_recepient_model.get_all()
		sms_recepients = sms_recepient_model.get_all()

		self.delete_session_key('errors')
		self.delete_session_key('form_data')

		self.render('alerts/edit_server_alert.html',
				alert=alert,
				email_recepients=email_recepients,
				sms_recepients=sms_recepients,
				process_metrics=process_metrics,
				server_metrics=server_metrics,
				common_metrics=common_metrics,
				errors=errors,
				form_data=form_data,
				server=server
		)


	@authenticated
	def post(self, alert_id):
		form_data = {      
				"metric_value" : self.get_argument('metric_value', None),         
				"above_below" : self.get_argument('above_below', None),         
				"metric_type": self.get_argument('metric_type', None),
				"metric_options": self.get_argument('metric_options',None),
				"threshold": self.get_argument('threshold', None),
				"email_recepients": self.get_arguments('email', None),
				"sms_recepients": self.get_arguments('sms', None),
				"rule_type": 'server'
		}
		
		try:
			EditServerRuleForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			alerts_model.update(form_data, alert_id)
			alerts_model.clear_alert_history(alert_id)
			self.redirect(self.reverse_url('alerts'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect(self.reverse_url('edit_server_alert', alert_id))



class EditProcessAlertView(BaseView):

	def initialize(self):
		self.current_page = 'alerts'
		super(EditProcessAlertView, self).initialize()

	@authenticated
	def get(self, alert_id):
		alert = alerts_model.get_by_id(alert_id)

	
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)
		email_recepients = email_recepient_model.get_all()
		sms_recepients = sms_recepient_model.get_all()

		self.delete_session_key('errors')
		self.delete_session_key('form_data')

		self.render('alerts/edit_process_alert.html',
				alert=alert,
				email_recepients=email_recepients,
				sms_recepients=sms_recepients,
				process_metrics=process_metrics,
				server_metrics=server_metrics,
				common_metrics=common_metrics,
				errors=errors,
				form_data=form_data
		)


	@authenticated
	def post(self, alert_id):
		form_data = {      
			"metric_value" : self.get_argument('metric_value', None),         
			"above_below" : self.get_argument('above_below', None),         
			"metric_type": self.get_argument('metric_type', None),
			"metric_options": self.get_argument('metric_options',None),
			"threshold": self.get_argument('threshold', None),
			"email_recepients": self.get_arguments('email', None),
			"sms_recepients": self.get_arguments('sms', None),
			"rule_type": 'process'
		}
		
		try:
			EditProcessRuleForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
			
			alerts_model.update(form_data, alert_id)
			alerts_model.clear_alert_history(alert_id)
			self.redirect(self.reverse_url('alerts'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect(self.reverse_url('edit_process_alert', alert_id))


class MuteAlertView(BaseView):
	def initialize(self):
		self.current_page = 'alerts'
		super(MuteAlertView, self).initialize()

	@authenticated
	def get(self, rule_id=None):
		alert = alerts_model.get_by_id(rule_id)

		alert_type = alert.get('rule_type', 'server')
		alerts_model.mute(rule_id)

		redirect_url = self.reverse_url('alerts')

		self.redirect(redirect_url)


class AlertHistoryView(BaseView):
	def initialize(self):
		self.current_page = 'alerts'
		super(AlertHistoryView, self).initialize()

	@authenticated
	def get(self, alert_id):
		
		alert = alerts_model.get_by_id(alert_id)
		
		page = self.get_argument('page', 1)

		alert_history = alert.get('history', {})
		history = self.paginate(alert_history, page=page)

		self.render('alerts/history.html',
			history=history,
			alert=alert)

class ClearAlertHistoryView(BaseView):
	def initialize(self):
		self.current_page = 'alerts'
		super(ClearAlertHistoryView, self).initialize()

	@authenticated
	def get(self, alert_id):
		alerts_model.clear_alert_history(alert_id)
		self.redirect(self.reverse_url('alert_history', alert_id))
########NEW FILE########
__FILENAME__ = models
from amonone.web.apps.core.basemodel import BaseModel
from amonone.utils.dates import unix_utc_now
from amonone.alerts.alerter import server_alerter

class ApiModel(BaseModel):

	def __init__(self):
		super(ApiModel, self).__init__()

		self.server_collection = self.mongo.get_collection('server')
		self.server = self.server_collection.find_one()

		if self.server is None:
			self.server_collection.insert({})

			self.server =  self.server_collection.find_one()


	def server_update_disk_volumes(self, volumes):
		try:
			volume_data = volumes.keys()
		except:
			volume_data = False

		if volume_data:
			valid_volumes = filter(lambda x: x not in ['time','last'], volume_data)
			
			self.server_collection.update({"_id": self.server['_id']}, {"$set": {"volumes": valid_volumes}})

	
	def server_update_network_interfaces(self,  interfaces):
		try:
			interfaces_data = interfaces.keys()
		except:
			interfaces_data = False
	   
		if interfaces_data:
			valid_adapters = filter(lambda x: x not in ['time','last','lo'], interfaces_data)
			
			self.server_collection.update({"_id": self.server['_id']}, {"$set": {"network_interfaces": valid_adapters}})

	def server_update_last_check(self,  last_check):
		self.server_collection.update({"_id": self.server['_id']}, {"$set": {"last_check": last_check}})


	def server_update_processes(self, processes):
		existing_processes =  self.server.get('processes', [])
		updated_list =  list(set(existing_processes).union(processes))
		
		cleaned_list = []
		for element in updated_list:
			if element.find("/") ==-1:
				cleaned_list.append(element)

		self.server_collection.update({"_id": self.server['_id']},  {"$set": {"processes": cleaned_list}})


	def store_system_entries(self, data):

			data["time"] = unix_utc_now()

			self.server_update_disk_volumes(data.get('disk', None))
			self.server_update_network_interfaces(data.get('network', None))
			self.server_update_last_check(data['time'])
			
						
			collection = self.mongo.get_collection('system')
			collection.insert(data)
			collection.ensure_index([('time', self.desc)])

			# Check for alerts
			server_alerter.check(data=data, alert_type='server')
		

	def store_process_entries(self, data):
			
		
		self.server_update_processes(data.keys())

		collection = self.mongo.get_collection('processes')
		data["time"] = unix_utc_now()
		collection.insert(data)
		collection.ensure_index([('time', self.desc)])

		# Check for alerts
		server_alerter.check(data=data, alert_type='process')


api_model = ApiModel()

########NEW FILE########
__FILENAME__ = model_tests
import unittest
from nose.tools import eq_
from amon.web.apps.api.models import ApiModel

class ApiModelTest(unittest.TestCase):

	def setUp(self):
		self.model = ApiModel()
		self.servers_collection = self.model.mongo.get_collection('servers')


	def check_server_test(self):
		self.servers_collection.remove()
		self.servers_collection.insert({"name" : "test", "key": 'test_me'})

		result = self.model.check_server_key('test_me')
		eq_(result['key'], 'test_me')


	def update_watched_processes_test(self):
		self.servers_collection.remove()
		self.servers_collection.insert({"name" : "test", "key": 'test_me'})

		self.model.server_update_processes('test_me',['process1','process2'])

		result = self.servers_collection.find_one()
		eq_(result['processes'],['process1','process2'])

	def update_disk_volumes_test(self):
		self.servers_collection.remove()
		self.servers_collection.insert({"name" : "test", "key": 'test_me'})

		self.model.server_update_disk_volumes('test_me',{"sda1": "test", "sda2": "test", "last": 1, "time": "now"})

		result = self.servers_collection.find_one()
		eq_(result['volumes'],[u'sda2',u'sda1'])


	def update_network_interfaces_test(self):
		self.servers_collection.remove()
		self.servers_collection.insert({"name" : "test", "key": 'test_me'})

		self.model.server_update_network_interfaces('test_me',{"eth1": "test", "lo": "test", "last": 1, "time": "now"})

		result = self.servers_collection.find_one()
		eq_(result['network_interfaces'],[u'eth1'])



	def store_system_entries_test(self):
		self.servers_collection.remove()
		self.servers_collection.insert({"name" : "test", "key": 'server_key_test_me'})
		server = self.servers_collection.find_one()

		server_system_collection = self.model.mongo.get_server_system_collection(server)
		server_system_collection.remove()

		self.model.store_system_entries('server_key_test_me',{u'memory':
			{u'swaptotal': 563, u'memfree': 1015, u'memtotal': 2012, u'swapfree': 563, u'time': 1326974020},
			u'loadavg': {"test":1}, u'disk': {"test1": 1 }, u'network': {'eth1': "test", "eth6": "test"}})

		
		result = server_system_collection.count()
		eq_(result,1)
		server_system_collection.remove({'server_id': server['_id']})

		server_updated = self.servers_collection.find_one()
		eq_(server_updated['volumes'],[u'test1'])
		eq_(server_updated['network_interfaces'],[u'eth6',u'eth1'])


	def store_process_entries_test(self):
		self.servers_collection.remove()
		self.servers_collection.insert({"name" : "test", "key": 'server_key_test_me'})
		server = self.servers_collection.find_one()

		server_process_collection = self.model.mongo.get_server_processes_collection(server)
		server_process_collection.remove()

		self.model.store_process_entries('server_key_test_me',{u'process': {u'memory': u'40.0', u'cpu': u'11.90', u'time': 1327169023}})

		result = server_process_collection.count()


		eq_(result,1)
		server_process_collection.remove({'server_id': server['_id']})

		server_updated = self.servers_collection.find_one()
		eq_(server_updated['processes'],[u'process'])


########NEW FILE########
__FILENAME__ = acl
def check_permissions(id, page, user):
	if user['type'] == 'admin':
		return True
	
	# Settings, only admin users
	if page.startswith('/settings'):
			return False

	# Alerts, only admin users
	if page.startswith('/alerts'):
			return False
	
	# Parent pages - no ids
	if id == False:
		return True

	if page in ['/system','/processes']:
		servers = user.get('servers', None)
		if id in servers:
			return True
		else:
			return False


	return False

def all_servers_for_user(user):
	if user is None:
		return False

	user_type = user.get('type', None)
	
	if user_type == 'admin':
		return 'all'
	if user_type == 'readonly':
		servers = len(user['servers'])
		# Empty list
		if servers == 0:
			return False
		# List with apps
		if servers > 1:
			return user['servers']
		# Check if the user has permission for all apps
		if servers == 1 and user['servers'][0] == 'all':
			return 'all'
		# Default
		else:
			return user['servers']

	return False





########NEW FILE########
__FILENAME__ = forms
import formencode
from formencode import validators
from amonone.web.apps.auth.models import user_model

class UniqueUsername(formencode.FancyValidator):

    def _to_python(self, value, state):
        user = user_model.username_exists(value)
        if user == 1:
            raise formencode.Invalid('The username already exists', value, state)

        return value

class CreateUserForm(formencode.Schema):
    allow_extra_fields = True
    username = formencode.All(validators.String(not_empty=True, min=4),UniqueUsername())
    password = validators.String(not_empty=True, min=4)



########NEW FILE########
__FILENAME__ = models
import hashlib
from amonone.web.apps.core.basemodel import BaseModel

class UserModel(BaseModel):

    def __init__(self):
        super(UserModel, self).__init__()
        self.collection = self.mongo.get_collection('users')


    def create_user(self, userdata):
        userdata['password'] = hashlib.sha1(userdata['password']).hexdigest()
        self.collection.save(userdata)

    def check_user(self, userdata):
        userdata['password'] = hashlib.sha1(userdata['password']).hexdigest()
        result = self.collection.find_one({"username": userdata['username'],
            "password": userdata['password']})


        return result if result else {}


    def count_users(self):
        return self.collection.count()	

    def username_exists(self, username):
        result = self.collection.find({"username": username}).count()

        return result

    def get_all(self):
        return self.collection.find()
    
    def get(self, id):
        try:
            object_id =  self.mongo.get_object_id(id)
        except:
            object_id = False

        if object_id:
            return self.collection.find_one(object_id)

    def update(self, data, id):
        id = self.mongo.get_object_id(id)

        servers = data.get('servers', None)
        if servers is not None:
            self.collection.update({"_id": id},{"$set": {"servers": data['servers']}} )

        password = data.get('password', None)
        if password is not None:
            data['password'] = hashlib.sha1(data['password']).hexdigest()
            self.collection.update({"_id": id},{"$set": {"password": data['password']}})

        
    
    def delete(self, id):
        try:
            object_id =  self.mongo.get_object_id(id)
        except:
            object_id = False

        if object_id:
            self.collection.remove(object_id)

user_model = UserModel()
########NEW FILE########
__FILENAME__ = acl_test
import unittest
from amonone.web.apps.core.acl import check_permissions, all_apps_for_user, all_servers_for_user
from nose.tools import eq_

class TestACL(unittest.TestCase):

	def test_admin_user(self):
		user = {"type": "admin"}
		result = check_permissions(False,'/something', user)
		eq_(True, result)

		# Page with id
		result = check_permissions('1234','/something', user)
		eq_(True, result)

		# Settings
		result = check_permissions('/settings','/settings', user)
		eq_(True, result)

	def test_readonly_user(self):
		user = {"type": "readonly", "apps":["app1", "app2"], "servers":["server1", "server2"]}
		result = check_permissions(False,'/system', user) # Parent pages - id is False
		eq_(True, result)

		result = check_permissions(False,'/', user) # Parent pages - id is False
		eq_(True, result)

		result = check_permissions(False,'/logs', user) # Parent pages - id is False
		eq_(True, result)

		result = check_permissions(False,'/something', user) # Parent pages - id is False
		eq_(True, result)

		result = check_permissions('server1','/system', user) # Page with server id
		eq_(True, result)

		result = check_permissions('serverdummy','/system', user) # Page with invalid server id
		eq_(False, result)
		
		result = check_permissions('server2','/processes', user) # Page with server id
		eq_(True, result)

		result = check_permissions('serverdummy','/processes', user) # Page with invalid server id
		eq_(False, result)

		result = check_permissions('app1','/logs', user) # Page with app id
		eq_(True, result)

		result = check_permissions('appdummy','/logs', user) # Page with invalid app id
		eq_(False, result)
		
		result = check_permissions('app2','/exceptions', user) # Page with app id
		eq_(True, result)

		result = check_permissions('appdummy','/exceptions', user) # Page with invalid app id
		eq_(False, result)

		result = check_permissions(False,'/settings', user) # Settings module
		eq_(False, result)

		result = check_permissions(False,'/settings/servers', user) # Settings module
		eq_(False, result)

		result = check_permissions(False,'/settings/users', user) # Settings module
		eq_(False, result)


	def test_filtered_apps_for_user(self):
		
		admin_user = {'type': 'admin'}
		result = all_apps_for_user(admin_user)
		eq_('all', result)

		readonly_user = {'type': 'readonly', 'apps': ['all']}
		result = all_apps_for_user(admin_user)
		eq_('all', result)

		readonly_user = {'type': 'readonly', 'apps': [1,2]}
		result = all_apps_for_user(readonly_user)
		eq_(result,[1, 2])

		readonly_user = {'type': 'readonly', 'apps': []}
		result = all_apps_for_user(readonly_user)
		eq_(result, False)

		none = None
		result = all_apps_for_user(none)
		eq_(result, False)


	def test_filtered_servers_for_user(self):

		admin_user = {'type': 'admin'}
		result = all_servers_for_user(admin_user)
		eq_('all', result)

		readonly_user = {'type': 'readonly', 'servers': ['all']}
		result = all_servers_for_user(admin_user)
		eq_('all', result)

		readonly_user = {'type': 'readonly', 'servers': [1,2]}
		result = all_servers_for_user(readonly_user)
		eq_(result,[1, 2])

		readonly_user = {'type': 'readonly', 'servers': []}
		result = all_servers_for_user(readonly_user)
		eq_(result, False)

		none = None
		result = all_servers_for_user(none)
		eq_(result, False)

########NEW FILE########
__FILENAME__ = models_test
import unittest
from nose.tools import eq_
from amonone.web.apps.auth.models import UserModel

class TestUserModel(unittest.TestCase):

    def setUp(self):
        self.model = UserModel()


    def test_create_user(self):
        self.model.collection.remove()
        self.model.create_user({'username': "test", 'password': '1234'})
        eq_(self.model.collection.count(),1)


    def test_check_user(self):
        self.model.collection.remove()
        user_dict = {"username": "test", "password": "1234"}
        self.model.create_user(user_dict)

        result = self.model.check_user({"username": "test", "password": "1234"})

        # username, pass, _id
        eq_(len(result), 3)

        result = self.model.check_user({"username": "noname","password": ""})

        eq_(result, {})


    def test_username_exists(self):
        self.model.collection.remove()

        result = self.model.username_exists("test")
        eq_(result, 0)

        self.model.create_user({'username': "test", 'password': '1234'})

        result = self.model.username_exists("test")
        eq_(result, 1)
########NEW FILE########
__FILENAME__ = views
from amonone.web.apps.core.baseview import BaseView
from amonone.web.apps.auth.forms import CreateUserForm
from amonone.web.apps.auth.models import user_model
from formencode.validators import Invalid as InvalidForm


class LoginView(BaseView):

    def initialize(self):
        super(LoginView, self).initialize()


    def get(self):

        # Redirect if there are no users in the database
        users = user_model.count_users()
        if users == 0:
            self.redirect('/create_user')
        else:
            message =  self.session.get('message',None)
            errors =  self.session.get('errors',None)
            next = self.get_argument('next', None)

            try:
                del self.session['errors']
                del self.session['message']
            except:
                pass

            self.render('auth/login.html', message=message, errors=errors, next=next)


    def post(self):
        form_data = {
                "username": self.get_argument('username', ''),
                "password": self.get_argument('password', ''),
                }

        user = user_model.check_user(form_data)

        if len(user) == 0:
            self.session['errors'] = "Invalid login details"
            self.redirect('/login')
        else:
            apps = user.get('apps',None)
            servers = user.get('servers', None)
            self.session['user'] = {'username': user['username'],
                    'user_id': user['_id'], 'type': user['type'],
                    'apps': apps, 'servers': servers}

            next = self.get_argument('next', None)
            redirect = next if next != None else "/"
            
            self.redirect(redirect)

class LogoutView(BaseView):

    def initialize(self):
        super(LogoutView, self).initialize()


    def get(self):

        if self.acl == 'False':
            self.redirect('/')
        else:
            try:
                del self.session['user']
            except:
                pass

            self.redirect('/login')

class CreateInitialUserView(BaseView):

    def initialize(self):
        super(CreateInitialUserView, self).initialize()


    def get(self):

        errors = self.session.get('errors', None)
        form_data = self.session.get('form_data', None)

        # This page is active only when acl is enabled
        if self.acl == 'False':
            self.redirect('/')
        else:
            # This page is active only when there are no users in the system
            users = user_model.count_users()

            if users == 0:
                self.render('auth/create_user.html', errors=errors, form_data=form_data)
            else:
                self.redirect('/login')


    def post(self):
        form_data = {
                "username": self.get_argument('username', ''),
                "password": self.get_argument('password',''),
                "type": "admin",
                "servers": [],
                "apps": []
                }
        try:
            valid_data = CreateUserForm.to_python(form_data)
            user_model.create_user(valid_data)
            self.session['message'] = 'User successfuly created. You can now log in'

            try:
                del self.session['errors']
                del self.session['form_data']
            except:
                pass

            self.redirect('/login')

        except InvalidForm, e:
            self.session['errors'] = e.unpack_errors()
            self.session['form_data'] = form_data

            self.redirect('/create_user')





########NEW FILE########
__FILENAME__ = basemodel
from amonone.core.mongodb import MongoBackend
from pymongo import DESCENDING, ASCENDING

class BaseModel(object):

	def __init__(self):
		self.mongo = MongoBackend()
		self.db = self.mongo.get_database()
		
		self.desc = DESCENDING
		self.asc = ASCENDING

		self.collection = None # Defined in the child models


	# CRUD Methods
	def insert(self, data):
		self.collection.insert(data)

	def update(self, data, id):
		try:
			object_id =  self.mongo.get_object_id(id)
		except:
			object_id = False

		if object_id:
			self.collection.update({"_id": object_id}, {"$set": data}, upsert=True)

	def get_one(self):
		return self.collection.find_one()

	def get_all(self):
		return self.collection.find()

	def get_by_id(self,id):
		try:
			object_id =  self.mongo.get_object_id(id)
		except:
			object_id = False

		if object_id:
			return self.collection.find_one({"_id": object_id})

	def delete(self, id):
		try:
			object_id =  self.mongo.get_object_id(id)
		except:
			object_id = False

		if object_id:
			self.collection.remove(object_id)
########NEW FILE########
__FILENAME__ = baseview
import os
import tornado.web
from datetime import datetime
from amonone.core import settings
from amonone.web.apps.core.models import server_model
from amonone.web.libs.session import MongoDBSession
from amonone.web.template import render as jinja_render
from amonone.web.apps.auth.acl import (
		check_permissions, 
		all_servers_for_user,
		)

class BaseView(tornado.web.RequestHandler):

	def initialize(self):
		self.session = self._create_session()
		self.now = datetime.utcnow()
		self.acl = settings.ACL		


		try:
			current_page = self.current_page
		except:
			current_page = ''

		# Template variables. Passing that dictionary to Jinja
		self.template_vars = {
				"user": self.current_user,
				"url": self.request.uri,
				"current_page": current_page,
				"xsrf": self.xsrf_form_html(),
				}

		super(BaseView, self).initialize()

	# Overwrite the xsrf check for the test suite
	def check_xsrf_cookie(self):
		try:
			test = os.environ['AMON_TEST_ENV']
		except:
			super(BaseView, self).check_xsrf_cookie()

	def get_current_user(self):

		try: 
			if os.environ['AMON_TEST_ENV'] == 'True':
				return {"username": "testuser", "type": "admin"}
		except:
			pass

		# Check is the page is in the list with pages that a read-only by default
		current_page = self.request.uri.split('?')
		try:
			url = current_page[0]
		except:
			url = self.request.uri

		id = False
		list = ['/', '/system', '/processes']
		if url in list:
			try:
				url_params =  self.request.uri.split('=')
				id = url_params[-1]
				id = False if id in list else id # If there are no paramaters in the url, the page id is False
			except:
				id = False
	
		try:
			user = self.session['user']
		except KeyError:
			return None

		permissions = check_permissions(id, url, user)

		if permissions is True:
			return user

		return None
	  
	def write_error(self, status_code, **kwargs):
		error_trace = None

		if "exc_info" in kwargs:
			import traceback

		error_trace= ""
		for line in traceback.format_exception(*kwargs["exc_info"]):
			error_trace += line 

		self.render("error.html", 
				status_code=status_code,
				error_trace=error_trace,
				unread_values=None)

	def finish(self, chunk = None):
		if self.session is not None and self.session._delete_cookie:
			self.clear_cookie('amonplus_session_id')
		elif self.session is not None:
			self.session.refresh() # advance expiry time and save session
			self.set_secure_cookie('amonplus_session_id', self.session.session_id, expires_days=None, expires=self.session.expires)

		super(BaseView, self).finish(chunk = chunk)


	def _create_session(self):
		session_id = self.get_secure_cookie('amonplus_session_id')

		kw = {'security_model': [],
				'duration': self.settings['session']['duration'],
				'ip_address': self.request.remote_ip,
				'user_agent': self.request.headers.get('User-Agent'),
				'regeneration_interval': self.settings['session']['regeneration_interval']
				}

		new_session = None
		old_session = None

		old_session = MongoDBSession.load(session_id)

		if old_session is None or old_session._is_expired(): # create new session
			new_session = MongoDBSession(**kw)

		if old_session is not None:
			if old_session._should_regenerate():
				old_session.refresh(new_session_id=True)
			return old_session

		return new_session


	def get_session_key_and_delete(self, key):
		
		value = self.get_session_key(key)
		self.delete_session_key(key)

		return value

	def get_session_key(self, key):
		try:
			return self.session[key]
		except:
			return None

	def delete_session_key(self, key):
		try:
			del self.session[key]
		except:
			pass


	def paginate(self, data, page=None):
		page_size = 100
		
		page = 1 if page == None else int(page)
		page = 1 if page == 0 else page
		
		rows = len(data)
		total_pages = rows/page_size
		total_pages = 1 if total_pages == 0 else total_pages
		
		page = total_pages if page > total_pages else page

		from_ = page_size * (page - 1)
		to = from_+page_size

		result = data[from_:to]
		
		pagination = {
				"pages": total_pages, 
				"current_page": page,
				"result": result 
		}
		
		return pagination


	def render(self, template, *args, **kwargs):
		kwargs['app'] = self.template_vars
		rendered_template = jinja_render(template, *args, **kwargs)

		self.write(rendered_template)


########NEW FILE########
__FILENAME__ = models
from hashlib import sha1
from amonone.web.apps.core.basemodel import BaseModel

class ServerModel(BaseModel):

	def __init__(self):
		super(ServerModel, self).__init__()
		self.collection = self.mongo.get_collection('server')


server_model = ServerModel()

########NEW FILE########
__FILENAME__ = models_test
import unittest
from nose.tools import eq_
from amonone.web.apps.core.models import (
	ServerModel
)


class ServerModelTest(unittest.TestCase):

	def setUp(self):
		self.model = ServerModel()
		self.collection = self.model.mongo.get_collection('servers')


	def get_servers_for_group_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test", "alert_group": 'test'})

		result = self.model.get_servers_for_group('test')
		eq_(result.count(), 1)

	def check_server_exists_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test"})

		result = self.model.server_exists('test')
		eq_(result, 1)


	def update_server_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test"})
		server = self.collection.find_one()

		self.model.update({"name": "test_updated", "default": 1 }, server['_id'])

		result = self.collection.find_one()
		eq_(result['name'],'test_updated')


	def add_server_test(self):
		self.collection.remove()

		self.model.add('test', 'note','')

		result = self.collection.find_one()
		eq_(result['name'],'test')
		if result['key']:
			assert True


	def get_server_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test"})
		server = self.collection.find_one()

		result = self.model.get_by_id(server['_id'])
		eq_(result['name'],'test')
		eq_(result['_id'],server['_id'])


	def get_server_by_key_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test", "key": "test_me"})
		server = self.collection.find_one()

		result = self.model.get_server_by_key('test_me')
		eq_(result['name'],'test')
		eq_(result['key'],'test_me')
		eq_(result['_id'],server['_id'])


	def delete_server_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test", "key": "test_me"})
		server = self.collection.find_one()

		self.model.delete(server['_id'])

		result = self.collection.count()
		eq_(result,0)

	def servers_dict_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test", "key": "test_me"})
		self.collection.insert({"name" : "test2", "key": "test_me2"})

		servers = self.collection.find()
		result = self.model.get_all_dict()
		for server in servers:
			key =  unicode(server['_id'])
			if key in result.keys():
				assert True

	def get_all_servers_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test", "key": "test_me"})
		self.collection.insert({"name" : "test1", "key": "test_me_again"})

		result = self.model.get_all()
		eq_(result.count(), 2)

		self.collection.remove()

	def get_filtered_test(self):
		self.collection.remove()
		self.collection.insert({"name" : "test", "key": "test_me"})
		self.collection.insert({"name" : "test1", "key": "test_me_again"})
		self.collection.insert({"name" : "test2", "key": "test_me_one_more_time"})

		result = self.model.get_filtered(filter='all')
		eq_(result.count(), 3)

		# Get app ids
		server_ids = []
		for i in self.collection.find():
			server_ids.append(str(i['_id']))

		result = self.model.get_filtered(filter=server_ids)
		eq_(result.count(), 3)

		result = self.model.get_filtered(filter=server_ids[0:2])
		eq_(result.count(), 2)

		for r in result.clone():
			assert str(r['_id']) in server_ids[0:2]
		
		self.collection.remove()




########NEW FILE########
__FILENAME__ = template_filters_test
import unittest
from amonone.web.template import *
from nose.tools import eq_

class TestTemplateFilters(unittest.TestCase):

	def test_dateformat(self):
		date = dateformat(1319737106)
		eq_('27-10-2011-17:38', date)


	def test_timeformat(self):
		time = timeformat(1319737106)
		eq_('17:38', time)

	def test_date_to_js(self):
		date = date_to_js(1319737106)
		eq_('2011,9, 27, 17, 38', date)


	def test_to_int(self):
		_int = to_int('testme2')
		eq_(_int, 2)

	def test_clean_string(self):
		string = clean_string('24.5MB')
		eq_(string, 24.5)

	
	def test_progress_width_percent(self):
		full_container = progress_width_percent(100, container_type='full' )
		eq_(full_container, '305px')

		full_container = progress_width_percent(50, container_type='full' )
		eq_(full_container, '152px')

		full_container = progress_width_percent(0, container_type='full' )
		eq_(full_container, '0px; border:3px solid transparent; background: none;')

		container = progress_width_percent(100, container_type='medium' )
		eq_(container, '158px')

		container = progress_width_percent(50, container_type='medium')
		eq_(container, '79px')

		container = progress_width_percent(0, container_type='medium' )
		eq_(container, '0px; border:3px solid transparent; background: none;')

		container = progress_width_percent(100, container_type='small' )
		eq_(container, '100px')

		container = progress_width_percent(50, container_type='small' )
		eq_(container, '50px')

	def test_progress_width(self):
		full_container = progress_width(300, 300, container_type='full' )
		eq_(full_container, '305px')

		full_container_50 = progress_width(150, 300, container_type='full')
		eq_(full_container_50, '152px')


		full_container_0 = progress_width(0, 300, container_type='full' )
		eq_(full_container_0, '0px; border:3px solid transparent; background: none;')


		medium_container = progress_width(300, 300, container_type='medium' )
		eq_(medium_container, '158px')

		medium_container_50 = progress_width(150, 300, container_type='medium' )
		eq_(medium_container_50, '79px')

		medium_container_0 = progress_width(0, 300, container_type='medium' )
		eq_(medium_container_0, '0px; border:3px solid transparent; background: none;')


		small_container = progress_width(300, 300, container_type='small' )
		eq_(small_container, '100px')


		small_container_50 = progress_width(150, 300, container_type='small' )
		eq_(small_container_50, '50px')

		small_container_0 = progress_width(0, 300, container_type='small' )
		eq_(small_container_0, '0px; border:3px solid transparent; background: none;')

	def test_progress_width_with_zeroes(self):
		empty_container_full = progress_width(0,0, container_type='full' )
		eq_(empty_container_full, '0px; border:3px solid transparent; background: none;')


		empty_container_medium = progress_width(0,0, container_type='medium' )
		eq_(empty_container_medium, '0px; border:3px solid transparent; background: none;')


		empty_container_small = progress_width(0,0, container_type='small' )
		eq_(empty_container_small, '0px; border:3px solid transparent; background: none;')


	def test_value_bigger_than_total(self):
		container_full = progress_width(600,0, container_type='full' )
		eq_(container_full, '305px')


	def test_with_big_numbers(self):
		container_full = progress_width(12332323600,3434344, container_type='full')
		eq_(container_full, '305px') # Value bigger than total - container is 100%

		container = progress_width(9,12233332, container_type='full')
		eq_(container,'0px; border:3px solid transparent; background: none;') 

		container_full = progress_width(1232,34343, container_type='full')
		eq_(container_full, '9px') 


	def test_url(self):
		_url = url('more', 'and', 'even', 'more')
		eq_(_url, 'more/and/even/more')


	def test_base_url(self):
		_base_url = base_url()
		assert isinstance(_base_url, str)

	def test_check_additional_data(self):
		ignored_dicts = [{'occurrence': 12223323}, {'occurrence': 1212121221}]
		check_ignored_dicts = check_additional_data(ignored_dicts)
		eq_(check_ignored_dicts, None)

		true_dicts = [{'occurrence': 12223323, 'test': 'me'}, {'occurrence': 1212121221}]
		check_true_dicts = check_additional_data(true_dicts)
		eq_(check_true_dicts, True)

	def test_cleanup_string(self):
		string = '//test---/'
		clean = clean_slashes(string)
		eq_(clean, 'test')


########NEW FILE########
__FILENAME__ = views_test

########NEW FILE########
__FILENAME__ = views

from amonone.core import settings
from amonone.web.apps.core.baseview import BaseView

class AgentView(BaseView):
    
    def get(self):

        server_key = self.get_argument('server_key', 'Insert your server key here')
        host = settings.WEB_APP['host']
        port = settings.WEB_APP['port']

        full_url = "{0}:{1}".format(host, port)

        self.render('agent.sh', full_url=full_url, 
                                host=host, port=port,
                                server_key=server_key)

########NEW FILE########
__FILENAME__ = models
from amonone.web.apps.core.basemodel import BaseModel


class DashboardModel(BaseModel):

	def __init__(self):
		super(DashboardModel, self).__init__()

	def build_process_dict(self, process_check):
		cpu_list = []
		memory_list = []

		for process, values in process_check.iteritems():
			if isinstance(values, dict):
				process_cpu = values.get('cpu:%', 0)
				process_memory = values.get('memory:mb', 0)

				cpu_list.append(float(process_cpu))
				memory_list.append(float(process_memory))

		processes_data = {
			'details': process_check,
			'total_memory_usage':  sum(memory_list),
			'total_cpu_usage': sum(cpu_list)
		}

		return processes_data

	def get_system_check(self, date):
		system_check = {}

		collection = self.mongo.get_collection('system')

		params = {}
		sort = self.desc
		if date:
			params = {"time": {"$gte": date}}
			sort= self.asc
	
		try:
			system_check = collection.find(params, sort=[("time", sort)]).limit(1)[0]
		except IndexError:
			pass

		return system_check


	def get_process_check(self, date):
		processes_data = None
		collection = self.mongo.get_collection('processes')			
			
		params = {}
		sort = self.desc
		if date:
			params = {"time": {"$gte": date}}
			sort= self.asc

		try:
			process_check = collection.find(params, sort=[("time", sort)]).limit(1)[0]
		except IndexError:
			process_check = False

		if process_check:
			processes_data = self.build_process_dict(process_check)
	
		return processes_data

dashboard_model = DashboardModel()
########NEW FILE########
__FILENAME__ = models_test
import unittest
from amonone.web.apps.dashboard.models import DashboardModel
from time import time
from nose.tools import eq_

now = int(time())
minute_ago = (now-60)
two_minutes_ago = (now-120)

class TestDashboardModel(unittest.TestCase):


	def setUp(self):
		self.model = DashboardModel()


	def test_get_process_check(self):

		servers = self.model.mongo.get_collection('servers')
		servers.remove()
		servers.insert({"name" : "test", "key": "server_key_test"})
		server = servers.find_one()
	
		server_process_collection = self.model.mongo.get_server_processes_collection(server)
		server_process_collection.remove()

		server_process_collection.insert({"memory" : "10.8", "time" : two_minutes_ago, "cpu" : "0.0", "server_id": server['_id']})
		server_process_collection.insert({"memory" : "10.8", "time" : minute_ago, "cpu" : "0.0", "server_id": server['_id']})
		server_process_collection.insert({"last" : 1, "server_id": server['_id']})


		result = self.model.get_process_check(server, None)
		
		eq_(result['details']['time'], minute_ago)

		server_process_collection.remove()
		servers.remove()


	def test_get_system_check(self):


		servers = self.model.mongo.get_collection('servers')
		servers.remove()
		servers.insert({"name" : "test", "key": "server_key_test"})
		server = servers.find_one()

			
		server_system_collection = self.model.mongo.get_server_system_collection(server)
		server_system_collection.insert({"system" : "10", "time" : two_minutes_ago , "server_id": server['_id']})
		server_system_collection.insert({"system": "10", "time" : minute_ago , "server_id": server['_id']})
		server_system_collection.insert({"last" : 1, "server_id": server['_id']})

		result = self.model.get_system_check(server, None)
		eq_(result['time'], minute_ago)

		servers.remove()
		server_system_collection.remove()
########NEW FILE########
__FILENAME__ = views
from tornado.web import authenticated
from amonone.web.apps.core.baseview import BaseView
from amonone.web.apps.core.models import server_model
from amonone.web.apps.dashboard.models import dashboard_model
from amonone.utils.dates import (
		utc_now_to_localtime, 
		datestring_to_utc_datetime,
		utc_unixtime_to_localtime,
		localtime_utc_timedelta,
		datetime_to_unixtime
)

class DashboardView(BaseView):

	def initialize(self):
		self.current_page='dashboard'
		super(DashboardView, self).initialize()

	@authenticated
	def get(self):

		snapshot_param = self.get_argument('snapshot', None)
		
		snapshot = None
		if snapshot_param:
			snapshot = datestring_to_utc_datetime(snapshot_param)
			snapshot = datetime_to_unixtime(snapshot)


		system_check = dashboard_model.get_system_check(snapshot)
		process_check = dashboard_model.get_process_check(snapshot)

		# Get the max date - utc, converted to localtime
		max_date = utc_now_to_localtime() 

		self.render("dashboard.html",
				system_check=system_check,
				process_check=process_check,
				max_date=max_date,
				snapshot=snapshot_param
				)
########NEW FILE########
__FILENAME__ = models
from amonone.web.apps.core.basemodel import BaseModel

class ProcessModel(BaseModel):

	def __init__(self):
		super(ProcessModel, self).__init__()

	def get_process_data(self, processes, date_from, date_to,):

		collection = self.mongo.get_collection('processes')

		data = collection.find({"time": {"$gte": date_from,"$lte": date_to }}).sort('time', self.desc)

		filtered_data = {}
		# Create the base structure
		for process in processes:
			filtered_data[process] = {"memory": {}, "cpu": {}}

		for line in data:
			time = line['time']

			for process in processes:
				try:
					process_data = line.get(process, None)
					memory = process_data.get("memory:mb", 0)
					cpu = process_data.get("cpu:%", 0)
				except:
					memory = 0
					cpu = 0
				
				try:
					filtered_data[process]["memory"][time] = memory
					filtered_data[process]["cpu"][time] = cpu
				except:
					pass
				
		return filtered_data


process_model = ProcessModel()
########NEW FILE########
__FILENAME__ = views
from amonone.web.apps.core.baseview import BaseView
from tornado.web import authenticated
from datetime import timedelta
from amonone.web.apps.core.models import server_model
from amonone.web.apps.processes.models import process_model
from amonone.utils.dates import (
		utc_now_to_localtime, 
		datestring_to_utc_datetime,
		utc_unixtime_to_localtime,
		localtime_utc_timedelta,
		datetime_to_unixtime
)

class ProcessesView(BaseView):

	def initialize(self):
		self.current_page = 'processes'
		super(ProcessesView, self).initialize()

	@authenticated
	def get(self):
		date_from = self.get_argument('date_from', None)
		date_to = self.get_argument('date_to', None)
		daterange = self.get_argument('daterange', None)
		processes = self.get_arguments('process', None)


		 # Default 24 hours period
		day = timedelta(hours=24)
		default_to = self.now
		default_from = default_to - day

		if date_from:
			date_from = datestring_to_utc_datetime(date_from)
		else:
			date_from = default_from

		if date_to:
			date_to = datestring_to_utc_datetime(date_to)
		else:
			date_to = default_to

		date_from = datetime_to_unixtime(date_from)
		date_to = datetime_to_unixtime(date_to) 
		default_from = datetime_to_unixtime(default_from)
		default_to = datetime_to_unixtime(default_to) 

		process_data = process_model.get_process_data(processes, date_from, date_to)

		# Convert the dates to local time for display
		date_from = utc_unixtime_to_localtime(date_from)
		date_to = utc_unixtime_to_localtime(date_to)
		default_from = utc_unixtime_to_localtime(default_from)
		default_to = utc_unixtime_to_localtime(default_to)

		# Get the difference between UTC and localtime - used to display 
		# the ticks in the charts
		zone_difference = localtime_utc_timedelta()

		# Get the max date - utc, converted to localtime
		max_date = utc_now_to_localtime() 

		server = server_model.get_one()

		self.render('processes.html',	
				current_page=self.current_page,
				processes=processes,
				process_data=process_data,
				date_from=date_from,
				date_to=date_to,
				default_from=default_from,
				default_to=default_to,
				zone_difference=zone_difference,
				max_date=max_date,
				daterange=daterange,
				server=server
				)
########NEW FILE########
__FILENAME__ = forms
import formencode
from formencode import validators
from amonone.web.apps.auth.models import user_model

class ServerForm(formencode.Schema):
    allow_extra_fields = True
    name = formencode.All(validators.String(not_empty=True, min=4, max=32, strip=True))


class SMTPForm(formencode.Schema):
    allow_extra_fields = True
    address = formencode.All(validators.String(not_empty=True))
    port = formencode.All(validators.Number(not_empty=True))
    from_ = formencode.All(validators.Email(not_empty=True))

class SMSForm(formencode.Schema):
    allow_extra_fields = True
    account = formencode.All(validators.String(not_empty=True))
    token = formencode.All(validators.String(not_empty=True))
    from_ = formencode.All(validators.String(not_empty=True))

class SMSRecepientForm(formencode.Schema):
    name = formencode.All(validators.String(not_empty=True))
    phone = formencode.All(validators.String(not_empty=True))

class EmailRecepientForm(formencode.Schema):
    name = formencode.All(validators.String(not_empty=True))
    email = formencode.All(validators.Email(not_empty=True))

class DataCleanupForm(formencode.Schema):
    server = formencode.All(validators.PlainText(not_empty=True))
    date = formencode.All(validators.DateValidator(not_empty=True))

class AppCleanupForm(formencode.Schema):
    app = formencode.All(validators.PlainText(not_empty=True))
    date = formencode.All(validators.DateValidator(not_empty=True))


class UniqueUsername(formencode.FancyValidator):

	def _to_python(self, value, state):
		user = user_model.username_exists(value)
		if user == 1:
			raise formencode.Invalid('The username already exists', value, state)

		return value

class CreateUserForm(formencode.Schema):
    allow_extra_fields = True
    username = formencode.All(validators.String(not_empty=True, min=4),UniqueUsername())
    password = formencode.All(validators.String(not_empty=True, min=6))


########NEW FILE########
__FILENAME__ = models
from amonone.web.apps.core.basemodel import BaseModel
from amonone.web.utils import generate_api_key
from amonone.utils.dates import unix_utc_now
from amonone.web.apps.core.models import server_model


class DataModel(BaseModel):

	def __init__(self):
		super(DataModel, self).__init__()
		
		self.protected_collections = ['system.indexes', 'users', 
				'sessions','tags','servers',
				'unread', 'alerts', 'email_settings', 'sms_settings']
		

	def get_database_info(self):
		return self.db.command('dbstats')


	def get_server_collection_stats(self):
		all_servers = server_model.get_all()
		data = {}
		if all_servers:
			for server in all_servers:
				system_collection = self.mongo.get_server_system_collection(server)
				process_collection = self.mongo.get_server_processes_collection(server)

				system_info = self.get_collection_stats(system_collection.name)
				process_info = self.get_collection_stats(process_collection.name)

				data[server['name']] = {"system_info": system_info, 
									"process_info": process_info,
									"server_id": server['_id']
								}

		return data


	def get_collection_stats(self, collection):
		try:
			stats = self.db.command('collstats', collection)
		except:
			stats = None
		
		return stats

	def cleanup_system_collection(self, server, date):
		collection = self.mongo.get_server_system_collection(server)

		params = {}
		if date != None:
			params['time'] = {"$lte": date }

			collection.remove(params)

	def cleanup_process_collection(self, server, date):
		collection = self.mongo.get_server_processes_collection(server)

		params = {}
		if date != None:
			params['time'] = {"$lte": date }

			collection.remove(params)


	def delete_system_collection(self, server):
		system_collection = self.mongo.get_server_system_collection(server)
		self.db.drop_collection(system_collection)

	def delete_process_collection(self, server):
		process_collection = self.mongo.get_server_processes_collection(server)
		self.db.drop_collection(process_collection)


data_model = DataModel()

########NEW FILE########
__FILENAME__ = views_test
import requests
import unittest
from nose.tools import eq_
from amonone.core import settings
from amonone.web.template import base_url
from amonone.web.apps.core.models import server_model
from amonone.web.utils import generate_random_string

# class TestSettings(unittest.TestCase):

# 	def setUp(self):
# 		self.base_url = base_url()


# 	def test_server_settings(self):
# 		url = "{0}/settings/servers".format(self.base_url)
# 		server_model.collection.remove()

# 		response = requests.get(url)
# 		eq_(response.status_code, 200)


# 		# Add 
# 		server_name = generate_random_string()
# 		response = requests.post(url, {"name": server_name})

# 		server = server_model.collection.find_one()
# 		eq_(server['name'], server_name)
# 		eq_(response.status_code, 200)


# 		# Edit
# 		edit_url = "{0}/edit/{1}".format(url, server['_id'])
# 		new_server_name = generate_random_string()
		
# 		response = requests.get(edit_url)
# 		eq_(response.status_code, 200)

# 		response = requests.post(edit_url, {"name": new_server_name})
# 		server = server_model.collection.find_one()
# 		eq_(server['name'], new_server_name)
# 		eq_(response.status_code, 200)


# 		# Delete
# 		delete_url = "{0}/delete/{1}".format(url, server['_id'])
# 		response = requests.get(delete_url)
# 		eq_(response.status_code, 200)
# 		eq_(0, server_model.collection.count())



########NEW FILE########
__FILENAME__ = data
from formencode.validators import Invalid as InvalidForm
from tornado.web import authenticated
from amonone.web.apps.core.baseview import BaseView

from amonone.web.apps.settings.models import data_model
from amonone.web.apps.core.models import server_model
from amonone.utils.dates import utc_now_to_localtime, datestring_to_utc_datetime, datetime_to_unixtime
from amonone.web.apps.settings.forms import DataCleanupForm

class DataBaseView(BaseView):
	def initialize(self):
		self.current_page = 'settings:data'
		super(DataBaseView, self).initialize()

class DataView(DataBaseView):

	@authenticated
	def get(self):
		database_info = data_model.get_database_info()
		server_data = data_model.get_server_collection_stats()


		self.render('settings/data.html',
				database_info=database_info,
				server_data=server_data
				)

class DataDeleteSystemCollectionView(DataBaseView):

	@authenticated
	def get(self, server_id=None):
		server = server_model.get_by_id(server_id)
		data_model.delete_system_collection(server)

		self.redirect(self.reverse_url('settings_data'))

class DataDeleteProcessCollectionView(DataBaseView):

	@authenticated
	def get(self, server_id=None):
		server = server_model.get_by_id(server_id)
		data_model.delete_process_collection(server)

		self.redirect(self.reverse_url('settings_data'))


class DataCleanupProcessView(DataBaseView):

	@authenticated
	def get(self, server_id=None):
		errors =  self.session.get('errors',None)

		# Get the max date - utc, converted to localtime
		max_date = utc_now_to_localtime() 

		server = server_model.get_by_id(server_id)

		self.render('settings/data/process_cleanup.html',
				server=server,
				errors=errors,
				max_date=max_date)

	@authenticated
	def post(self, server_id=None):
		
		form_data = {
				"server": server_id,
				"date" : self.get_argument('date', None),         
		}

		try:
			DataCleanupForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			# Convert to unix utc
			date = datestring_to_utc_datetime(form_data['date'])
			date = datetime_to_unixtime(date)
			
			server = server_model.get_by_id(form_data['server'])

			data_model.cleanup_process_collection(server, date)

			self.redirect(self.reverse_url('settings_data'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect(self.reverse_url('cleanup_process' ,server_id))


class DataCleanupSystemView(DataBaseView):

	@authenticated
	def get(self, server_id=None):
		errors =  self.session.get('errors',None)

		# Get the max date - utc, converted to localtime
		max_date = utc_now_to_localtime() 

		server = server_model.get_by_id(server_id)

		self.render('settings/data/system_cleanup.html',
				server=server,
				errors=errors,
				max_date=max_date)
	
	@authenticated
	def post(self, server_id=None):
		
		form_data = {
				"server": server_id,
				"date" : self.get_argument('date', None),         
		}

		try:
			DataCleanupForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			# Convert to unix utc
			date = datestring_to_utc_datetime(form_data['date'])
			date = datetime_to_unixtime(date)
			
			server = server_model.get_by_id(form_data['server'])

			data_model.cleanup_system_collection(server, date)

			self.redirect(self.reverse_url('settings_data'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data

			self.redirect(self.reverse_url('cleanup_system', server_id))
########NEW FILE########
__FILENAME__ = email
from formencode.validators import Invalid as InvalidForm
from tornado.web import authenticated
from amonone.web.apps.core.baseview import BaseView

from amonone.mail.models import email_model, email_recepient_model
from amonone.mail.sender import send_mail
from amonone.web.apps.settings.forms import SMTPForm, EmailRecepientForm

class EmailBaseView(BaseView):
	def initialize(self):
		self.current_page = 'settings:email'
		super(EmailBaseView, self).initialize()

class EmailView(EmailBaseView):

	@authenticated
	def get(self, param=None):
	  
		server_details = email_model.get_email_details()
		recepients = email_recepient_model.get_all()
		self.render('settings/email/email.html',
				server_details=server_details,
				recepients=recepients)


class EmailUpdateView(EmailBaseView):

	@authenticated
	def get(self, param=None):
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)
		server_details = email_model.get_email_details()

		self.delete_session_key('errors')
		self.delete_session_key('form_data')

		self.render('settings/email/update_smtp_details.html',
					server_details=server_details,
					errors=errors,
					form_data=form_data)


	@authenticated
	def post(self):
		form_data = {
				"address": self.get_argument('address', None),
				"port" : self.get_argument('port', None),         
				"username" : self.get_argument('username', None),         
				"password" : self.get_argument('password', None),         
				"from_" : self.get_argument('from', None),      
				"security": self.get_argument('security', None)
		}

		try:
			SMTPForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			email_model.save_email_details(form_data)
			self.redirect(self.reverse_url('settings_email'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect(self.reverse_url('update_email'))

class EmailAddRecepient(EmailBaseView):

	@authenticated
	def get(self):
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)

		self.render('settings/email/add_recepient.html',
			errors=errors,
			form_data=form_data)

	@authenticated
	def post(self):
		form_data = {
				"name": self.get_argument('name', None),
				"email" : self.get_argument('email', None),         

		}

		try:
			EmailRecepientForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			email_recepient_model.insert(form_data)
			self.redirect(self.reverse_url('settings_email'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect(self.reverse_url('email_add_recepient'))


class EmailEditRecepientView(EmailBaseView):

	@authenticated
	def get(self, recepient_id=None):
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)
	  
	  	recepient = email_recepient_model.get_by_id(recepient_id)

		self.render('settings/email/edit_recepient.html',
			recepient=recepient,
			errors=errors,
			form_data=form_data)

	@authenticated
	def post(self, recepient_id):
		form_data = {
				"name": self.get_argument('name', None),
				"email" : self.get_argument('email', None),         

		}

		try:
			EmailRecepientForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			email_recepient_model.update(form_data, recepient_id)
			self.redirect(self.reverse_url('settings_email'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect(self.reverse_url('email_edit_recepient', recepient_id))

class EmailDeleteRecepientView(EmailBaseView):

	@authenticated
	def get(self, recepient_id=None):
		email_recepient_model.delete(recepient_id)
		self.redirect(self.reverse_url('settings_email'))

class EmailTestView(EmailBaseView):

	@authenticated
	def get(self):
		message = self.get_session_key_and_delete('message')

		recepients = email_recepient_model.get_all()
		self.render('settings/email/test.html',
			message=message,
			recepients=recepients)

	@authenticated
	def post(self):
		recepient_id = self.get_argument('recepient', None)

		recepient = email_recepient_model.get_by_id(recepient_id)
	
		send_mail(recepients=[recepient],
			subject='Amon test email',
			template='test')

		self.session['message'] = 'Test email sent, check your inbox({0})'.format(recepient['email'])
		self.redirect(self.reverse_url('test_email'))
########NEW FILE########
__FILENAME__ = servers
from formencode.validators import Invalid as InvalidForm
from tornado.web import authenticated
from amonone.web.apps.core.baseview import BaseView

from amonone.web.apps.alerts.models import alerts_model, alerts_group_model
from amonone.web.apps.core.models import server_model
from amonone.web.apps.settings.forms import ServerForm

class ServersBaseView(BaseView):
	def initialize(self):
		self.current_page = 'settings:servers'
		super(ServersBaseView, self).initialize()

class ServersView(ServersBaseView):

	@authenticated
	def get(self):
		errors =  self.session.get('errors',None)
		all_servers = server_model.get_all()

		servers = []
		if all_servers:
			for server in all_servers.clone():

				alert_group = server.get('alert_group', None)
				server['alert_group'] = alerts_group_model.get_by_id(alert_group)
			
				servers.append(server)

		self.render('settings/servers/view.html', 
				servers=servers)

class ServersDeleteView(ServersBaseView):

	@authenticated
	def get(self, param=None):
		server = server_model.get_by_id(param)

		alerts_model.delete_server_alerts(param)
		server_model.delete(param)
		
		self.redirect(self.reverse_url('settings_servers'))


class ServersUpdateView(ServersBaseView):


	@authenticated
	def get(self, param=None):
		errors =  self.session.get('errors',None)
		server = server_model.get_by_id(param)
		groups = alerts_group_model.get_all()

		self.delete_session_key('errors')

		self.render('settings/servers/edit.html', 
				server=server,
				groups=groups,
				errors=errors)

	@authenticated
	def post(self, param=None):
		self.check_xsrf_cookie()


		form_data = {
				"name": self.get_argument('name', ''),
				"notes": self.get_argument('notes', ''),
				"alert_group": self.get_argument('alert_group', ''),
				}

		try:
			valid_data = ServerForm.to_python(form_data)
			server_model.update(valid_data, param)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')

			self.redirect(self.reverse_url('settings_servers'))

		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data


			self.redirect(self.reverse_url('update_server', param))


class ServersAddView(ServersBaseView):

	@authenticated
	def get(self):
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)
		groups = alerts_group_model.get_all()

		self.delete_session_key('errors')

		self.render('settings/servers/add.html',
				groups=groups,
				errors=errors,
				form_data=form_data)

	@authenticated
	def post(self):
		self.check_xsrf_cookie()

		form_data = {
				"name": self.get_argument('name', ''),
				"notes": self.get_argument('notes', ''),
				"alert_group": self.get_argument('alert_group', ''),
				}

		try:
			valid_data = ServerForm.to_python(form_data)
			server_model.add(valid_data['name'],
			 	valid_data['notes'],
			  	valid_data['alert_group'])

			self.delete_session_key('errors')
			self.delete_session_key('form_data')

			self.redirect(self.reverse_url('settings_servers'))

		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data


			self.redirect(self.reverse_url('settings_servers_add'))
########NEW FILE########
__FILENAME__ = sms
from formencode.validators import Invalid as InvalidForm
from tornado.web import authenticated
from tornado import escape as tornado_escape
from amonone.web.apps.core.baseview import BaseView

from amonone.sms.models import sms_model, sms_recepient_model
from amonone.web.apps.settings.forms import SMSForm, SMSRecepientForm
from amonone.sms.sender import send_test_sms

class SMSBaseView(BaseView):
	def initialize(self):
		self.current_page = 'settings:sms'
		super(SMSBaseView, self).initialize()

class SMSView(SMSBaseView):

	@authenticated
	def get(self, param=None):
		details = sms_model.get()
		recepients = sms_recepient_model.get_all()
		self.render('settings/sms/sms.html', details=details,
			recepients=recepients)

class SMSTestView(SMSBaseView):

	@authenticated
	def get(self, param=None):
		recepients = sms_recepient_model.get_all()
		self.render('settings/sms/test.html',
			recepients=recepients)

	@authenticated
	def post(self):
		post_data = tornado_escape.json_decode(self.request.body)

		recepient_param = post_data.get('recepient')
		recepient = sms_recepient_model.get_by_id(recepient_param)
		
		response = send_test_sms(recepient=recepient['phone'])
		

		

class SMSUpdateView(SMSBaseView):

	@authenticated
	def get(self, param=None):
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)
		details = sms_model.get()

		self.delete_session_key('errors')
		self.delete_session_key('form_data')

		self.render('settings/sms/update_sms_details.html',
					details=details,
					errors=errors,
					form_data=form_data)


	@authenticated
	def post(self):
		form_data = {
				"account": self.get_argument('account', None),
				"token" : self.get_argument('token', None),
				"from_" : self.get_argument('from', None), 
		}

		try:
			SMSForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			sms_model.save(form_data)
			self.redirect(self.reverse_url('settings_sms'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect('/settings/sms/edit')


class SMSAddRecepient(SMSBaseView):

	@authenticated
	def get(self):
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)

		self.render('settings/sms/add_recepient.html',
			errors=errors,
			form_data=form_data)

	@authenticated
	def post(self):
		form_data = {
				"name": self.get_argument('name', None),
				"phone" : self.get_argument('phone', None),         

		}

		try:
			SMSRecepientForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			sms_recepient_model.insert(form_data)
			self.redirect(self.reverse_url('settings_sms'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect(self.reverse_url('sms_add_recepient'))


class SMSEditRecepientView(SMSBaseView):

	@authenticated
	def get(self, recepient_id=None):
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)
	  
	  	recepient = sms_recepient_model.get_by_id(recepient_id)

		self.render('settings/sms/edit_recepient.html',
			recepient=recepient,
			errors=errors,
			form_data=form_data)

	@authenticated
	def post(self, recepient_id):
		form_data = {
				"name": self.get_argument('name', None),
				"phone" : self.get_argument('phone', None),
		}

		try:
			SMSRecepientForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')
		
			sms_recepient_model.update(form_data, recepient_id)
			self.redirect(self.reverse_url('settings_sms'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data
			self.redirect(self.reverse_url('sms_edit_recepient', recepient_id))

class SMSDeleteRecepientView(SMSBaseView):

	@authenticated
	def get(self, recepient_id=None):
		sms_recepient_model.delete(recepient_id)
		self.redirect(self.reverse_url('settings_sms'))
########NEW FILE########
__FILENAME__ = users
from formencode.validators import Invalid as InvalidForm
from tornado.web import authenticated
from amonone.web.apps.core.baseview import BaseView

from amonone.web.apps.auth.models import user_model
from amonone.web.apps.core.models import server_model
from amonone.web.apps.settings.forms import CreateUserForm

class BaseUsersView(BaseView):
	def initialize(self):
		self.current_page = 'settings:users'
		super(BaseUsersView, self).initialize()

class UsersView(BaseUsersView):

	@authenticated
	def get(self):
		users = user_model.get_all()
	
		all_servers = server_model.get_all()
		if all_servers:
			all_servers = dict((str(record['_id']), record['name']) for record in all_servers)
		
		self.render('/settings/users/view.html', 
				users=users,
				all_servers=all_servers)


class DeleteUserView(BaseUsersView):

	@authenticated
	def get(self, id=None):
		if self.current_user['type'] == 'admin':
			user_model.delete(id)
			self.redirect(self.reverse_url('settings_users'))


class EditUserView(BaseUsersView):

	@authenticated
	def get(self, id=None):
		user = user_model.get(id)
		all_servers = server_model.get_all()
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)

		self.delete_session_key('errors')
		self.delete_session_key('form_data')

		self.render('/settings/users/edit.html', 
				user=user,
				all_servers=all_servers,
				errors=errors,
				form_data=form_data)

	@authenticated
	def post(self, id):
		
		form_data = {
				"servers": self.get_arguments('servers[]',None)
		}

		# Remove all other values if all in the list
		if len(form_data['servers']) > 0:
			form_data['servers'] = ['all'] if 'all' in form_data['servers'] else form_data['servers']

		user_model.update(form_data, id)
		self.redirect(self.reverse_url('settings_users'))

class UpdatePasswordUserView(BaseUsersView):

	@authenticated
	def post(self, id):
		
		form_data = {
				"password" : self.get_argument('password', None),
		}
		if len(form_data['password']) > 0:
			user_model.update(form_data, id)
		self.redirect(self.reverse_url('settings_users'))		

class CreateUserView(BaseUsersView):

	@authenticated
	def get(self):
		all_servers = server_model.get_all()
		errors =  self.session.get('errors',None)
		form_data =  self.session.get('form_data',None)

		self.delete_session_key('errors')
		self.delete_session_key('form_data')


		self.render('settings/users/create.html',
				all_servers=all_servers,
				errors=errors,
				form_data=form_data)
	
	@authenticated
	def post(self):
		
		form_data = {
				"username": self.get_argument('username', None),
				"password" : self.get_argument('password', None),         
				"type": self.get_argument('type', None),
				"servers": self.get_arguments('servers[]',None)
		}

		try:
			CreateUserForm.to_python(form_data)

			self.delete_session_key('errors')
			self.delete_session_key('form_data')

			user_model.create_user(form_data)
			self.redirect(self.reverse_url('settings_users'))
		
		except InvalidForm, e:
			self.session['errors'] = e.unpack_errors()
			self.session['form_data'] = form_data

			self.redirect(self.reverse_url('settings_create_user'))
########NEW FILE########
__FILENAME__ = models
from amonone.web.apps.core.basemodel import BaseModel

class SystemModel(BaseModel):

    def get_system_data(self, charts, date_from, date_to):

        collection = self.mongo.get_collection('system')

        data_dict = collection.find({"time": {"$gte": date_from,"$lte": date_to }}).sort('time', self.asc)

        filtered_data = {'memory': [], "cpu": [], "disk": [], "network": [], "loadavg": []}

        # Get data for all charts
        if len(charts) == 0:
            charts = filtered_data.keys()

        for line in data_dict:
            time = line['time']

            for element in filtered_data:
                if element in charts:
                    line[element]["time"] = time
                    filtered_data[element].append(line[element])
        
        return filtered_data 


    """
    Used in the Javascript calendar - doesn't permit checks for dates before this date
    Also used to display no data message in the system tab
    """
    def get_first_check_date(self, server=None):
        
        collection = self.mongo.get_collection('system')

        start_date = collection.find_one()

        if start_date is not None:
            start_date = start_date.get('time', 0)
        else:
            start_date = 0
        
        return start_date

system_model = SystemModel()
########NEW FILE########
__FILENAME__ = views
from tornado.web import authenticated
from datetime import timedelta
from amonone.web.apps.core.baseview import BaseView
from amonone.web.apps.core.models import server_model
from amonone.web.apps.system.models import system_model
from amonone.utils.dates import ( 
	datestring_to_utc_datetime,
	datetime_to_unixtime,
	unix_utc_now,
	utc_unixtime_to_localtime,
	localtime_utc_timedelta,
	utc_now_to_localtime
)

class SystemView(BaseView):

	def initialize(self):
		self.current_page='system'
		super(SystemView, self).initialize()

	@authenticated
	def get(self):

		date_from = self.get_argument('date_from', None)
		date_to = self.get_argument('date_to', None)
		charts = self.get_arguments('charts', None)
	   
		daterange = self.get_argument('daterange', None)

		# Default 24 hours period
		day = timedelta(hours=24)
		default_to = self.now
		default_from = default_to - day

		if date_from:
			date_from = datestring_to_utc_datetime(date_from)
		else:
			date_from = default_from

		if date_to:
			date_to = datestring_to_utc_datetime(date_to)
		else:
			date_to = default_to

		date_from = datetime_to_unixtime(date_from)
		date_to = datetime_to_unixtime(date_to) 
	 	

		checks = system_model.get_system_data(charts, date_from, date_to)
		
		active_charts = charts if len(charts) > 0 else checks.keys()
	  
		first_check_date = system_model.get_first_check_date()

		default_from = datetime_to_unixtime(default_from)
		default_to = datetime_to_unixtime(default_to) 

		# Convert the dates to local time for display
		first_check_date = utc_unixtime_to_localtime(first_check_date)
		date_from = utc_unixtime_to_localtime(date_from)
		date_to = utc_unixtime_to_localtime(date_to)
		default_from = utc_unixtime_to_localtime(default_from)
		default_to = utc_unixtime_to_localtime(default_to)

		# Get the max date - utc, converted to localtime
		max_date = utc_now_to_localtime()
		
		# Get the difference between UTC and localtime - used to display 
		# the ticks in the charts
		zone_difference = localtime_utc_timedelta()

		server = server_model.get_one()


		self.render('system.html',
				charts=charts,
				active_charts=active_charts,
				checks=checks,
				daterange=daterange,
				date_from=date_from,
				date_to=date_to,
				default_from=default_from,
				default_to=default_to,
				first_check_date=first_check_date,
				zone_difference=zone_difference,
				max_date=max_date,
				server=server
				)
########NEW FILE########
__FILENAME__ = devserver
import sys
sys.path.insert(0,'/home/martin/amonone')

from amonone.web.server import application
import tornado.ioloop
from amonone.core import settings
from tornado import autoreload

if __name__ == "__main__":
    application.listen(int(settings.WEB_APP['port']))
    ioloop = tornado.ioloop.IOLoop().instance()
    autoreload.start(ioloop)
    ioloop.start()

########NEW FILE########
__FILENAME__ = daemon
#!/usr/bin/env python
import sys, os, time, atexit
from signal import SIGTERM 

class Daemon(object):
	"""
		A generic daemon class.

		Usage: subclass the Daemon class and override the run() method
	"""

	startmsg = "started with pid %s"
	
	def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
			self.stdin = stdin
			self.stdout = stdout
			self.stderr = stderr
			self.pidfile = pidfile

	def daemonize(self):
		"""
		do the UNIX double-fork magic, see Stevens' "Advanced 
		Programming in the UNIX Environment" for details (ISBN 0201563177)
		http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
		"""
		try: 
				pid = os.fork() 
				if pid > 0:
						# exit first parent
						sys.exit(0) 
		except OSError, e: 
				sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
				sys.exit(1)

		# decouple from parent environment
		os.chdir(".") 
		os.setsid() 
		os.umask(0) 

		# do second fork
		try: 
			pid = os.fork() 
			if pid > 0:
				# exit from second parent
				sys.exit(0) 
		except OSError, e: 
			sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
			sys.exit(1) 
		
		# redirect standard file descriptors
		si = file(self.stdin, 'r')
		so = file(self.stdout, 'a+')
		se = file(self.stderr, 'a+', 0)
		
		pid = str(os.getpid())
		
		sys.stderr.write("\n%s\n" % self.startmsg % pid)
		sys.stderr.flush()

		if self.pidfile:
			file(self.pidfile,'w+').write("%s\n" % pid)
		
		atexit.register(self.delpid)
		os.dup2(si.fileno(), sys.stdin.fileno())
		os.dup2(so.fileno(), sys.stdout.fileno())
		os.dup2(se.fileno(), sys.stderr.fileno())
			
		
		

	def delpid(self):
		os.remove(self.pidfile)

	def start(self):
		"""
		Start the daemon
		"""
		# Check for a pidfile to see if the daemon already runs
		try:
			pf = file(self.pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None

		if pid:
			message = "pidfile %s already exist. Daemon already running?\n"
			sys.stderr.write(message % self.pidfile)
			sys.exit(1)

		# Start the daemon
		self.daemonize()
		self.run()

	def stop(self):
		"""
		Stop the daemon
		"""
		# Get the pid from the pidfile
		try:
				pf = file(self.pidfile,'r')
				pid = int(pf.read().strip())
				pf.close()
		except IOError:
				pid = None

		if not pid:
			message = "pidfile %s does not exist. Daemon not running?\n"
			sys.stderr.write(message % self.pidfile)
			return # not an error in a restart

		# Try killing the daemon process        
		try:
			while 1:
				os.kill(pid, SIGTERM)
				time.sleep(0.1)
		except OSError, err:
			err = str(err)
			if err.find("No such process") > 0:
				if os.path.exists(self.pidfile):
					os.remove(self.pidfile)
				else:
					print str(err)
					sys.exit(1)

	def restart(self):
		"""
		Restart the daemon
		"""
		self.stop()
		self.start()

	def run(self):
		"""
		You should override this method when you subclass Daemon. It will be called after the process has been
		daemonized by start() or restart().
		"""
	

########NEW FILE########
__FILENAME__ = jinja2htmlcompress
# -*- coding: utf-8 -*-
"""
    jinja2htmlcompress
    ~~~~~~~~~~~~~~~~~~

    A Jinja2 extension that eliminates useless whitespace at template
    compilation time without extra overhead.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import re
from jinja2.ext import Extension
from jinja2.lexer import Token, describe_token
from jinja2 import TemplateSyntaxError


_tag_re = re.compile(r'(?:<(/?)([a-zA-Z0-9_-]+)\s*|(>\s*))(?s)')
_ws_normalize_re = re.compile(r'[ \t\r\n]+')


class StreamProcessContext(object):

    def __init__(self, stream):
        self.stream = stream
        self.token = None
        self.stack = []

    def fail(self, message):
        raise TemplateSyntaxError(message, self.token.lineno,
                                  self.stream.name, self.stream.filename)


def _make_dict_from_listing(listing):
    rv = {}
    for keys, value in listing:
        for key in keys:
            rv[key] = value
    return rv


class HTMLCompress(Extension):
    isolated_elements = set(['script', 'style', 'noscript', 'textarea'])
    void_elements = set(['br', 'img', 'area', 'hr', 'param', 'input',
                         'embed', 'col'])
    block_elements = set(['div', 'p', 'form', 'ul', 'ol', 'li', 'table', 'tr',
                          'tbody', 'thead', 'tfoot', 'tr', 'td', 'th', 'dl',
                          'dt', 'dd', 'blockquote', 'h1', 'h2', 'h3', 'h4',
                          'h5', 'h6', 'pre'])
    breaking_rules = _make_dict_from_listing([
        (['p'], set(['#block'])),
        (['li'], set(['li'])),
        (['td', 'th'], set(['td', 'th', 'tr', 'tbody', 'thead', 'tfoot'])),
        (['tr'], set(['tr', 'tbody', 'thead', 'tfoot'])),
        (['thead', 'tbody', 'tfoot'], set(['thead', 'tbody', 'tfoot'])),
        (['dd', 'dt'], set(['dl', 'dt', 'dd']))
    ])

    def is_isolated(self, stack):
        for tag in reversed(stack):
            if tag in self.isolated_elements:
                return True
        return False

    def is_breaking(self, tag, other_tag):
        breaking = self.breaking_rules.get(other_tag)
        return breaking and (tag in breaking or
            ('#block' in breaking and tag in self.block_elements))

    def enter_tag(self, tag, ctx):
        while ctx.stack and self.is_breaking(tag, ctx.stack[-1]):
            self.leave_tag(ctx.stack[-1], ctx)
        if tag not in self.void_elements:
            ctx.stack.append(tag)

    def leave_tag(self, tag, ctx):
        if not ctx.stack:
            ctx.fail('Tried to leave "%s" but something closed '
                     'it already' % tag)
        if tag == ctx.stack[-1]:
            ctx.stack.pop()
            return
        for idx, other_tag in enumerate(reversed(ctx.stack)):
            if other_tag == tag:
                for num in xrange(idx + 1):
                    ctx.stack.pop()
            elif not self.breaking_rules.get(other_tag):
                break

    def normalize(self, ctx):
        pos = 0
        buffer = []
        def write_data(value):
            if not self.is_isolated(ctx.stack):
                value = _ws_normalize_re.sub(' ', value.strip())
            buffer.append(value)

        for match in _tag_re.finditer(ctx.token.value):
            closes, tag, sole = match.groups()
            preamble = ctx.token.value[pos:match.start()]
            write_data(preamble)
            if sole:
                write_data(sole)
            else:
                buffer.append(match.group())
                (closes and self.leave_tag or self.enter_tag)(tag, ctx)
            pos = match.end()

        write_data(ctx.token.value[pos:])
        return u''.join(buffer)

    def filter_stream(self, stream):
        ctx = StreamProcessContext(stream)
        for token in stream:
            if token.type != 'data':
                yield token
                continue
            ctx.token = token
            value = self.normalize(ctx)
            yield Token(token.lineno, 'data', value)


class SelectiveHTMLCompress(HTMLCompress):

    def filter_stream(self, stream):
        ctx = StreamProcessContext(stream)
        strip_depth = 0
        while 1:
            if stream.current.type == 'block_begin':
                if stream.look().test('name:strip') or \
                   stream.look().test('name:endstrip'):
                    stream.skip()
                    if stream.current.value == 'strip':
                        strip_depth += 1
                    else:
                        strip_depth -= 1
                        if strip_depth < 0:
                            ctx.fail('Unexpected tag endstrip')
                    stream.skip()
                    if stream.current.type != 'block_end':
                        ctx.fail('expected end of block, got %s' %
                                 describe_token(stream.current))
                    stream.skip()
            if strip_depth > 0 and stream.current.type == 'data':
                ctx.token = stream.current
                value = self.normalize(ctx)
                yield Token(stream.current.lineno, 'data', value)
            else:
                yield stream.current
            stream.next()


def test():
    from jinja2 import Environment
    env = Environment(extensions=[HTMLCompress])
    tmpl = env.from_string('''
        <html>
          <head>
            <title>{{ title }}</title>
          </head>
          <script type=text/javascript>
            if (foo < 42) {
              document.write('Foo < Bar');
            }
          </script>
          <body>
            <li><a href="{{ href }}">{{ title }}</a><br>Test   Foo
            <li><a href="{{ href }}">{{ title }}</a><img src=test.png>
          </body>
        </html>
    ''')
    print tmpl.render(title=42, href='index.html')

    env = Environment(extensions=[SelectiveHTMLCompress])
    tmpl = env.from_string('''
        Normal   <span>  unchanged </span> stuff
        {% strip %}Stripped <span class=foo  >   test   </span>
        <a href="foo">  test </a> {{ foo }}
        Normal <stuff>   again {{ foo }}  </stuff>
        <p>
          Foo<br>Bar
          Baz
        <p>
          Moep    <span>Test</span>    Moep
        </p>
        {% endstrip %}
    ''')
    print tmpl.render(foo=42)


if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = session
# -*- coding: utf-8 -*-

"""
Sessions module for the Tornado framework.
Milan Cermak <milan.cermak@gmail.com> 

USAGE:
======

Every session object can be handled as a dictionary:
    self.session[key] = value
    var = self.session[key]

The session data is saved automatically for you when the request
handler finishes. 

Two utility functions, invalidate() and refresh() are available to
every session object. Read their documentation to learn more.

The application provider is responsible for removing stale, expired
sessions from the storage. However, he can use the delete_expired()
function provided with every storage class except Memcached, which
knows when a session expired and removes it automatically.


SETTINGS:
=========

The session module introduces new settings available to the
application:

session_age: how long should the session be valid (applies also to cookies);
             the value can be anything an integer, long, string or datetime.timedelta;
             integer, long and string are meant to represent seconds,
             default is 900 seconds (15 mins);
             check out _expires_at for additional info

session_regeneration_interval: period in seconds, after which the session_id should be
                               regenerated; when the session creation time + period
                               exceed current time, a new session is stored
                               server-side (the sesion data remains unchanged) and
                               the client cookie is refreshed; the old session
                               is no longer valid
                               session regeneration is used to strenghten security
                               and prevent session hijacking; default interval
                               is 4 minutes
                               the setting accepts integer, string or timedelta values,
                               read _next_regeneration_at() documentation for more info

session_cookie_name: the name of the cookie, which stores the session_id;
                     default is 'session_id'

session_cookie_path: path attribute for the session cookie;
                     default is '/'

session_cookie_domain: domain attribute for the session cookie;
                       default is None

"""
import base64
import collections
import datetime
import os
import cPickle as pickle
import time
from amonone.core.mongodb import MongoBackend

class BaseSession(collections.MutableMapping):
    """The base class for the session object. Work with the session object
    is really simple, just treat is as any other dictionary:

    class Handler(tornado.web.RequestHandler):
        def get(self):
            var = self.session['key']
            self.session['another_key'] = 'value'

    Session is automatically saved on handler finish. Session expiration
    is updated with every request. If configured, session ID is
    regenerated periodically.

    The session_id attribute stores a unique, random, 64 characters long
    string serving as an indentifier.

    To create a new storage system for the sessions, subclass BaseSession
    and define save(), load() and delete(). For inspiration, check out any
    of the already available classes and documentation to aformentioned functions."""
    def __init__(self, session_id=None, data=None, security_model=[], expires=None,
                 duration=None, ip_address=None, user_agent=None,
                 regeneration_interval=None, next_regeneration=None, **kwargs):
        # if session_id is True, we're loading a previously initialized session
        if session_id:
            self.session_id = session_id
            self.data = data
            self.duration = duration
            self.expires = expires
            self.dirty = False
        else:
            self.session_id = self._generate_session_id()
            self.data = {}
            self.duration = duration
            self.expires = self._expires_at()
            self.dirty = True

        self.ip_address = ip_address
        self.user_agent = user_agent
        self.security_model = security_model
        self.regeneration_interval = regeneration_interval
        self.next_regeneration = next_regeneration or self._next_regeneration_at()
        self._delete_cookie = False

    def __repr__(self):
        return '<session id: %s data: %s>' % (self.session_id, self.data)

    def __str__(self):
        return self.session_id

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self.dirty = True

    def __delitem__(self, key):
        del self.data[key]
        self.dirty = True

    def keys(self):
        return self.data.keys()

    def __iter__(self):
        return self.data.__iter__()

    def __len__(self):
        return len(self.data.keys())

    def _generate_session_id(cls):
        return os.urandom(16).encode('hex') 

    def _is_expired(self):
        """Check if the session has expired."""
        if self.expires is None: # never expire
            return False 
        return datetime.datetime.utcnow() > self.expires

    def _expires_at(self):
        """Find out the expiration time. Returns datetime.datetime."""
        v = self.duration
        if v is None: # never expire
            return None
        elif isinstance(v, datetime.timedelta):
            pass
        elif isinstance(v, (int, long)):
            self.duration =  datetime.timedelta(seconds=v)
        elif isinstance(v, basestring):
            self.duration = datetime.timedelta(seconds=int(v))
        else:
            self.duration = datetime.timedelta(seconds=900) # 15 mins

        return datetime.datetime.utcnow() + self.duration

    def _serialize_expires(self):
        """ Determines what value of expires is stored to DB during save()."""
        if self.expires is None:
            return None
        else:
            return int(time.mktime(self.expires.timetuple()))

    def _should_regenerate(self):
        """Determine if the session_id should be regenerated."""
        if self.regeneration_interval is None: # never regenerate
            return False
        return datetime.datetime.utcnow() > self.next_regeneration

    def _next_regeneration_at(self):
        """Return a datetime object when the next session id regeneration
        should occur."""
        # convert whatever value to an timedelta (period in seconds)
        # store it in self.regeneration_interval to prevent
        # converting in later calls and return the datetime
        # of next planned regeneration
        v = self.regeneration_interval
        if v is None: # never regenerate
            return None
        elif isinstance(v, datetime.timedelta):
            pass
        elif isinstance(v, (int, long)):
            self.regeneration_interval = datetime.timedelta(seconds=v)
        elif isinstance(v, basestring):
            self.regeneration_interval = datetime.timedelta(seconds=int(v))
        else:
            self.regeneration_interval = datetime.timedelta(seconds=240) # 4 mins

        return datetime.datetime.utcnow() + self.regeneration_interval

    def invalidate(self): 
        """Destroys the session, both server-side and client-side.
        As a best practice, it should be used when the user logs out of
        the application."""
        self.delete() # remove server-side
        self._delete_cookie = True # remove client-side

    def refresh(self, duration=None, new_session_id=False): # the opposite of invalidate
        """Prolongs the session validity. You can specify for how long passing a
        value in the duration argument (the same rules as for session_age apply).
        Be aware that henceforward this particular session may have different
        expiry date, not respecting the global setting. 

        If new_session_id is True, a new session identifier will be generated.
        This should be used e.g. on user authentication for security reasons."""
        if duration:
            self.duration = duration
            self.expires = self._expires_at()
        else:
            self.expires = self._expires_at()
        if new_session_id:
            self.delete()
            self.session_id = self._generate_session_id()
            self.next_regeneration = self._next_regeneration_at()
        self.dirty = True # force save
        self.save()

    def save(self):
        """Save the session data and metadata to the backend storage
        if necessary (self.dirty == True). On successful save set
        dirty to False."""
        pass

    @staticmethod
    def load(session_id, location):
        """Load the stored session from storage backend or return
        None if the session was not found, in case of stale cookie."""
        pass

    def delete(self):
        """Remove all data representing the session from backend storage."""
        pass

    @staticmethod
    def delete_expired(file_path):
        """Deletes sessions with timestamps in the past form storage."""
        pass

    def serialize(self):
        dump = {'session_id': self.session_id,
                'data': self.data,
                'duration': self.duration,
                'expires': self.expires,
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'security_model': self.security_model,
                'regeneration_interval': self.regeneration_interval,
                'next_regeneration': self.next_regeneration}
        return base64.encodestring(pickle.dumps(dump))

    @staticmethod
    def deserialize(datastring):
        return pickle.loads(base64.decodestring(datastring))


mongo_backend = MongoBackend()
mongo = mongo_backend.get_collection('sessions') 

class MongoDBSession(BaseSession):
    """Class implementing the MongoDB based session storage.
    All sessions are stored in a collection "sessions" in the db
    you specify in the session_storage setting.

    The session document structure is following:
    'session_id': session ID
    'data': serialized session object
    'expires': a timestamp of when the session expires, in sec since epoch
    'user_agent': self-explanatory
    An index on session_id is created automatically, on application's init.

    The end_request() is called after every operation (save, load, delete),
    to return the connection back to the pool.
    """

    def __init__(self, **kwargs):
        super(MongoDBSession, self).__init__(**kwargs)

        self.db = mongo # pymongo Collection object - sessions
        if not kwargs.has_key('session_id'):
            self.save()

    def save(self):
        """Upsert a document to the tornado_sessions collection.
        The document's structure is like so:
            {'session_id': self.session_id,
                    'data': self.serialize(),
                    'expires': self._serialize_expires(),
                    'user_agent': self.user_agent}
            """
        # upsert
        self.db.update(
            {'session_id': self.session_id}, # equality criteria
            {'session_id': self.session_id,
             'data': self.serialize(),
             'expires': self._serialize_expires(),
             'user_agent': self.user_agent}, # new document
            upsert=True)
        self.db.database.connection.end_request()
        self.dirty = False

    @staticmethod
    def load(session_id):
        """Load the session from mongo."""
        try:
            data = mongo.find_one({'session_id': session_id})
            if data:
                kwargs = MongoDBSession.deserialize(data['data'])
                mongo.database.connection.end_request()
                return MongoDBSession(**kwargs)
            return None
        except:
            mongo.database.connection.end_request()
            return None

    def delete(self):
        """Remove session from mongo."""
        self.db.remove({'session_id': self.session_id})
        self.db.database.connection.end_request()

    @staticmethod
    def delete_expired(db):
        db.remove({'expires': {'$lte': int(time.time())}})



########NEW FILE########
__FILENAME__ = unicode
# Copyright (c) 2009 Lobstertech, Inc.
# Licensed MIT
import types

def smart_unicode(s, encoding='utf-8', errors='strict'):
    if type(s) in (unicode, int, long, float, types.NoneType):
        return unicode(s)
    elif type(s) is str or hasattr(s, '__unicode__'):
        return unicode(s, encoding, errors)
    else:
        return unicode(str(s), encoding, errors)

def smart_str(s, encoding='utf-8', errors='strict', from_encoding='utf-8'):
    if type(s) in (int, long, float, types.NoneType):
        return str(s)
    elif type(s) is str:
        if encoding != from_encoding:
            return s.decode(from_encoding, errors).encode(encoding, errors)
        else:
            return s
    elif type(s) is unicode:
        return s.encode(encoding, errors)
    elif hasattr(s, '__str__'):
        return smart_str(str(s), encoding, errors, from_encoding)
    elif hasattr(s, '__unicode__'):
        return smart_str(unicode(s), encoding, errors, from_encoding)
    else:
        return smart_str(str(s), encoding, errors, from_encoding)

########NEW FILE########
__FILENAME__ = server
import os.path
import tornado.web
from tornado.web import url
from amonone.web.settings import PROJECT_ROOT
from amonone.core import settings
from amonone.web.apps.dashboard.views import DashboardView
from amonone.web.apps.system.views import SystemView
from amonone.web.apps.processes.views import ProcessesView

from amonone.web.apps.alerts.views import (
	AlertsView,
	AddSystemAlertView,
	DeleteServerAlertView,
	AddProcessAlertView,
	DeleteProcessAlertView,
	MuteAlertView, 
	AlertHistoryView,
	ClearAlertHistoryView,
	EditServerAlertView,
	EditProcessAlertView
	)

from amonone.web.apps.settings.views.data import (
		DataView,
		DataDeleteSystemCollectionView,
		DataDeleteProcessCollectionView,
		DataCleanupSystemView,
		DataCleanupProcessView
)

from amonone.web.apps.settings.views.email import (
		EmailView,
		EmailUpdateView,
		EmailTestView,
		EmailAddRecepient,
		EmailEditRecepientView,
		EmailDeleteRecepientView
)

from amonone.web.apps.settings.views.users import (
		UpdatePasswordUserView
)

from amonone.web.apps.settings.views.sms import(
		SMSView,
		SMSUpdateView,
		SMSTestView,
		SMSAddRecepient,
		SMSEditRecepientView,
		SMSDeleteRecepientView
)

from amonone.web.apps.auth.views import LoginView, CreateInitialUserView, LogoutView

	
app_settings = {
	"static_path": os.path.join(PROJECT_ROOT, "media"),
	"cookie_secret": settings.SECRET_KEY,
	"login_url" : "{0}:{1}/login".format(settings.WEB_APP['host'], settings.WEB_APP['port']),
	"session": {"duration": 3600, "regeneration_interval": 240, "domain": settings.WEB_APP['host']}
}


handlers = [
	# App
	url(r"/", DashboardView, name='dashboard'),
	url(r"/system", SystemView, name='system'),
	url(r"/processes", ProcessesView, name='processes'),
	# Alerts
	url(r"^/alerts$", AlertsView, name='alerts'),
	url(r"^/alerts/system/add$", AddSystemAlertView, name='add_server_alert'),
	url(r"^/alerts/system/delete/(?P<param>\w+)$", DeleteServerAlertView, name='delete_server_alert'),
	url(r"^/alerts/process/add$", AddProcessAlertView, name='add_process_alert'),
	url(r"^/alerts/process/delete/(?P<param>\w+)$", DeleteProcessAlertView, name='delete_proces_alert'),
	url(r"^/alerts/mute/(?P<rule_id>\w+)$", MuteAlertView, name='mute_alert'),
	url(r"^/alerts/history/(?P<alert_id>\w+)$", AlertHistoryView, name='alert_history'),
	url(r"^/alerts/clear_history/(?P<alert_id>\w+)$", ClearAlertHistoryView, name='alert_clear_history'),
	url(r"^/alerts/edit/server/(?P<alert_id>\w+)$", EditServerAlertView, name='edit_server_alert'),
	url(r"^/alerts/edit/process/(?P<alert_id>\w+)$", EditProcessAlertView, name='edit_process_alert'),
	# Email settings
	url(r"^/settings/email$", EmailView, name='settings_email'),
	url(r"^/settings/email/edit$", EmailUpdateView, name='update_email'),
	url(r"^/settings/email/add_recepient$", EmailAddRecepient, name='email_add_recepient'),
	url(r"^/settings/email/recepients/edit/(?P<recepient_id>[-\w]+)$", EmailEditRecepientView, name='email_edit_recepient'),
	url(r"^/settings/email/recepients/delete/(?P<recepient_id>[-\w]+)$", EmailDeleteRecepientView, name='email_delete_recepient'),
	url(r"^/settings/email/test$", EmailTestView, name='test_email'),
	# SMS settings
	url(r"^/settings/sms$", SMSView, name='settings_sms'),
	url(r"^/settings/sms/edit$", SMSUpdateView, name='sms_update'),
	url(r"^/settings/sms/add_recepient$", SMSAddRecepient, name='sms_add_recepient'),
	url(r"^/settings/sms/recepients/edit/(?P<recepient_id>[-\w]+)$", SMSEditRecepientView, name='sms_edit_recepient'),
	url(r"^/settings/sms/recepients/delete/(?P<recepient_id>[-\w]+)$", SMSDeleteRecepientView, name='sms_delete_recepient'),
	url(r"^/settings/sms/test$", SMSTestView, name='sms_test'),
	# Data settings
	url(r"^/settings/data$", DataView, name='settings_data'),
	# Users settings
	url(r"^/settings/users/update_password/(?P<id>\w+)$", UpdatePasswordUserView, name='update_password'),
	# Auth
	url(r"/login", LoginView, name='login'),
	url(r"/logout", LogoutView, name='logout'),
	url(r"/create_user", CreateInitialUserView, name='create_user'),
	# Static
	(r"/media/(.*)", tornado.web.StaticFileHandler, {"path": app_settings['static_path']}),
]
application = tornado.web.Application(handlers, **app_settings)

########NEW FILE########
__FILENAME__ = settings
from os.path import join, abspath, dirname

PROJECT_ROOT = abspath(dirname(__file__))
TEMPLATES_DIR =  join(PROJECT_ROOT, 'templates')


server_metrics = {"1": "CPU",
                "2": "Memory",
                "3": "Loadavg",
                "5": "Disk"
                }

process_metrics = {"1": "CPU", "2": "Memory"}

common_metrics = ["KB", "MB", "GB", "%"]


########NEW FILE########
__FILENAME__ = template
from __future__ import division
from jinja2 import Environment, FileSystemLoader
from amonone.core import settings
from amonone.web.settings import TEMPLATES_DIR
from amonone import __version__
from datetime import datetime, time
from amonone.utils.dates import ( 
	utc_unixtime_to_localtime,
	dateformat_local,
	dateformat,
	timeformat
)
from amonone.web.libs.jinja2htmlcompress import SelectiveHTMLCompress
import re

try:
	import json
except:
	import simplejson as json

def age(from_date, since_date = None, target_tz=None, include_seconds=False):
	'''
	Returns the age as a string
	'''
	if since_date is None:
		since_date = datetime.now(target_tz)

	distance_in_time = since_date - from_date
	distance_in_seconds = int(round(abs(distance_in_time.days * 86400 + distance_in_time.seconds)))
	distance_in_minutes = int(round(distance_in_seconds/60))

	if distance_in_minutes <= 1:
		if include_seconds:
			for remainder in [5, 10, 20]:
				if distance_in_seconds < remainder:
					return "less than %s seconds" % remainder
			if distance_in_seconds < 40:
				return "half a minute"
			elif distance_in_seconds < 60:
				return "less than a minute"
			else:
				return "1 minute"
		else:
			if distance_in_minutes == 0:
				return "less than a minute"
			else:
				return "1 minute"
	elif distance_in_minutes < 45:
		return "%s minutes" % distance_in_minutes
	elif distance_in_minutes < 90:
		return "about 1 hour"
	elif distance_in_minutes < 1440:
		return "about %d hours" % (round(distance_in_minutes / 60.0))
	elif distance_in_minutes < 2880:
		return "1 day"
	elif distance_in_minutes < 43220:
		return "%d days" % (round(distance_in_minutes / 1440))
	elif distance_in_minutes < 86400:
		return "about 1 month"
	elif distance_in_minutes < 525600:
		return "%d months" % (round(distance_in_minutes / 43200))
	elif distance_in_minutes < 1051200:
		return "about 1 year"
	else:
		return "over %d years" % (round(distance_in_minutes / 525600))


# Custom filters
def time_in_words(value):
	'''
	Usage: {{ my_date_variable|time_in_words }}
	'''
	# if DateTimeFiled() or datetime.datetime variable
	try:
		time_ago = age(value)
	except:
		null_time = time()
		time_ago = age(datetime.combine(value, null_time))

	return time_ago


def date_to_js(value, format='%Y, %m, %d, %H, %M'):
	# Converts unixtime to a javascript Date list
	_ = datetime.utcfromtimestamp(value)
	js_time_list = _.strftime(format).split(',')
	# Substract one month in js January is 0, February is 1, etc.
	js_time_list[1] = str(int(js_time_list[1])-1) 

	return ",".join(js_time_list) 

def to_int(value):
	number = re.compile('(\d+)')

	try:
		_int = number.search(value).group(1)
	except:
		_int = 0

	return int(_int)

# TODO - write tests
def extract_days_from_unixdate(value, days):
	day = 86400 # 1 day in seconds

	return value-(day*days)

# Removes the letters from a string
# From 24.5MB -> 24.5 -> used in the progress width
def clean_string(variable):

	if isinstance(variable, int)\
	or isinstance(variable, float)\
	or isinstance(variable, long):
		
		variable = float(variable) if not isinstance(variable, float) else variable

		return variable

	else:

		value_regex = re.compile(r'\d+[\.,]\d+') 
		extracted_value = value_regex.findall(variable)

		if len(extracted_value) > 0:
			extracted_value = extracted_value[0]
			extracted_value.replace(",",".")
			extracted_value = float(extracted_value)
		else:
			extracted_value = 0

		return extracted_value


# Used in the charts, where a disk drive could be with several slashes
def clean_slashes(string):
	return re.sub('[^A-Za-z0-9]+', '', string).strip().lower()


def check_additional_data(list_with_dicts):
	valid_keys = ['occurrence']

	for dict in list_with_dicts:
		for key in dict.keys():
			if key not in valid_keys:
				return True


# Combine several parameters with /
# Used in the base_url -> {{ base_url|url('system',) -> http://host/system
def url(*args):
	http_slash = '/'
	url = http_slash.join(args)

	return url


def beautify_json(value):
	if isinstance(value, dict):
		return json.dumps(value, indent=4) # Remove the unicode symbol
	else:
		return value

# Used in the log page. Displays the expand button if the value is dictionary
def is_dict(value):
	if isinstance(value, dict):
		return True
	else:
		return False

# Used in the log page. Checks the log tag
def is_str(value):
	if isinstance(value, str) or isinstance(value, unicode):
		return True
	else:
		return False

def get_active_page(value, key):
	elements = value.split(':')

	try:
		return elements[key]
	except:
		return None


# url -> usually the base url -> http://something.com
# params_dict -> dict {"tags": ['test', 'some'], "other_param": ['test']}
def query_dict(url, params_dict, page=None):

	query_lists = []
	for dict in params_dict:
		dict_items = []
		values_list = params_dict[dict]
		if values_list:
			for value in values_list:
				dict_items.append("{0}={1}".format(dict, value))
			# Join all the values
			query_lists.append("&".join(dict_items))

	# Finally separate the different params with ?
	query_string = url

	if len(query_lists) > 0:
		query_string+='?'
		query_string+= "?".join(query_lists)
		if page != None:
			query_string+="&page={0}".format(page)
	# No params - only the page number
	else:
		if page != None:
			query_string+="?page={0}".format(page)

	return query_string


def base_url():

	if settings.PROXY is None:
		host = settings.WEB_APP['host']
		port = settings.WEB_APP['port']

		base_url = "{0}:{1}".format(host, port)

		return base_url
	else:
		return ''

# Removes the scientific notation and displays floats normally
def format_float(value):
	return format(float(value), "g")

# Converts bytes in megabytes
def to_mb(value):
	value = value/(1024*1024)

	return "{0:.2F}MB".format(float(value))

def dehumanize(value):

	values_dict = {
			"more_than": "&gt;",
			"less_than": "&lt;",
			"minute": "1 minute",
			"five_minutes": "5 minutes",
			"fifteen_minutes": "15 minutes"
			}

	try:
		_value = values_dict[value]
	except: 
		_value = ''

	return _value

# Gets the key from a dictionary, doesn't break the template
def get_key(dict, key):
	value = dict.get(key, None)
	
	return value

def render(template, *args, **kwargs):

	env = Environment(loader=FileSystemLoader(TEMPLATES_DIR),
		extensions=[SelectiveHTMLCompress])

	env.globals['base_url'] = base_url()
	env.globals['version'] = __version__

	env.filters['url'] = url

	# Used everywhere
	env.filters['time'] = timeformat
	env.filters['date_to_js'] = date_to_js
	env.filters['date'] = dateformat
	env.filters['date_local'] = dateformat_local
	env.filters['to_int'] =  to_int
	env.filters['time_in_words'] = time_in_words 
	env.filters['test_additional_data'] = check_additional_data
	env.filters['clean_slashes'] = clean_slashes
	env.filters['beautify_json'] = beautify_json
	env.filters['get_active_page'] = get_active_page # Used to mark links as active
	env.filters['extract_days_from_unixdate'] = extract_days_from_unixdate

	# Dashboard filters
	env.filters['format_float'] = format_float

	# Log filters
	env.filters['is_dict'] = is_dict
	env.filters['is_str'] = is_str
	env.filters['query_dict'] = query_dict

	# Settings
	env.filters['dehumanize'] = dehumanize
	env.filters['to_mb'] = to_mb

	# ACL

	# Utilities
	env.filters['get_key'] = get_key

	try:
		template = env.get_template(template)
	except Exception, e:
		raise

	# Global variables
	env.globals['acl'] = settings.ACL

	return template.render(*args, **kwargs)


########NEW FILE########
__FILENAME__ = utils
try:
    import json
except ImportError:
    import simplejson as json
from datetime import datetime
import calendar
import base64
import random
import string
import hashlib
import os 

def json_string_to_dict(string):

    try:
        _convert = string.replace("'", '"')	

        return json.loads(_convert)
    except:
        return	False


def json_list_to_dict(list):

    converted_list = []

    for _dict in list:
        converted_list.append(json_string_to_dict(_dict))


    return converted_list

def generate_api_key():
    key  = base64.b64encode(hashlib.sha256(str(random.getrandbits(32))).digest(), 
            random.choice(['rA','aZ','gQ','hH','hG','aR','DD'])).rstrip('==')

    return key


def generate_random_string(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))
########NEW FILE########
__FILENAME__ = generate_config
import os.path
import uuid
import base64

# Current directory
ROOT = os.path.abspath(os.path.dirname(__file__))

# Check if AmonOne is already installed 
if os.path.exists('/etc/amonone.conf'):
	config_path = '/etc/amonone.conf'	
else:
	config_path =  os.path.join(ROOT, 'amonone.conf')

try:
    import json
except ImportError:
    import simplejson as json

try:
	config_file = file(config_path).read()
	config = json.loads(config_file)
except:
	config = {}

# Change only the secret key
config['secret_key'] = base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)

# Write the config file in the same directory
generated_config_path =  os.path.join(ROOT, 'amonone.conf')

with open(generated_config_path,'w+') as f:
	config_contents = json.dumps(config, indent=4)
	f.write(config_contents)


########NEW FILE########
__FILENAME__ = pip-update
import pip
from subprocess import call

for dist in pip.get_installed_distributions():
    call("pip install --upgrade " + dist.project_name, shell=True)
########NEW FILE########
__FILENAME__ = runtests
import os
import sys
import nose
# Changes the enviroment in backends/mongodb
os.environ['AMON_TEST_ENV'] = "True"

# To test the web app ( disable auth ), in the console
# AMON_TEST_ENV="TRUE" python amon/web/devserver.py

# Example usage
# python runtests  -w amon/

if __name__ == "__main__":
	try:
		suite = eval(sys.argv[1]) # Selected tests 
	except: 
		suite = None # All tests
		
	nose.run(suite)

########NEW FILE########
__FILENAME__ = temp_collector
from amonone.core.collector.runner import runner
from amonone.web.apps.api.models import api_model

system_info = runner.system()
process_info = runner.processes()

api_model.store_system_entries(system_info)
api_model.store_process_entries(process_info)


########NEW FILE########
