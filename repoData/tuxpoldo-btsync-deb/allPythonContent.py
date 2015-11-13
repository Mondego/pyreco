__FILENAME__ = btsyncagent
# coding=utf-8
#
# Copyright 2014 Leo Moll
#
# Authors: Leo Moll and Contributors (see CREDITS)
#
# Thanks to Mark Johnson for btsyncindicator.py which gave me the
# last nudge needed to learn python and write my first linux gui
# application. Thank you!
#
# This file is part of btsync-gui. btsync-gui is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import os
import json
import time
import stat
import base64
import signal
import logging
import gettext
import argparse
import subprocess

from gettext import gettext as _

from btsyncapi import BtSyncApi
from btsyncutils import BtSingleton, BtSingleInstanceException

class BtSyncAgentException(Exception):
	def __init__(self,retcode,message):
		self.retcode = retcode
		self.message = message
	def __str__(self):
		return repr(self.message)
	def __int__(self):
		return repr(self.retcode)

class BtSyncAgent(BtSyncApi):
	# still hardcoded - this is the binary location of btsync when installing
	# the package btsync-common
	BINARY = '/usr/lib/btsync-common/btsync-core'

	def __init__(self,args):
		BtSyncApi.__init__(self)
		self.args = args
		self.uid = int(os.getuid())
		self.pid = None
		self.configpath = os.environ['HOME'] + '/.config/btsync'
		self.storagepath = os.environ['HOME'] + '/.btsync'
		self.pidfile = self.configpath + '/btsync-agent.pid'
		self.conffile = self.configpath + '/btsync-agent.conf'
		self.preffile = self.configpath + '/btsync-gui.prefs'
		self.lockfile = self.configpath + '/btsync-gui.pid'
		self.lock = None
		self.prefs = {}
		# load values from preferences
		self.load_prefs()
		# generate random credentials
		try:
			username = base64.b64encode(os.urandom(16))[:-2]
			password = base64.b64encode(os.urandom(32))[:-2]
		except NotImplementedError:
			logging.warning('No good random generator available. Using default credentials')
			username = 'btsync-ui'
			password = base64.b64encode('This is really not secure!')[:-2]
		self.username = self.get_pref('username',username)
		self.password = self.get_pref('password',password)
		self.bindui = self.get_pref('bindui','127.0.0.1')
		self.portui = self.get_pref('portui',self.uid + 8999)
		self.paused = self.get_pref('paused',False)
		self.webui = self.get_pref('webui',False)
		# process command line arguments
		if self.args.username is not None:
			self.username = self.args.username
		if self.args.password is not None:
			self.password = self.args.password
		if self.args.bindui is not None:
			self.bindui = '0.0.0.0' if self.args.bindui == 'auto' else self.args.bindui
		if self.args.port != 0:
			self.portui = self.args.port
		if self.args.webui:
			self.webui = self.args.webui
		if self.args.cleardefaults:
			# clear saved defaults
			if 'username' in self.prefs:
				del self.prefs['username']
			if 'password' in self.prefs:
				del self.prefs['password']
			if 'webui' in self.prefs:
				del self.prefs['webui']
			if 'bindui' in self.prefs:
				del self.prefs['bindui']
			if 'portui' in self.prefs:
				del self.prefs['portui']
			self.save_prefs()
			raise BtSyncAgentException(0, _('Default settings cleared.'))
		if self.args.savedefaults:
			# save new defaults
			if self.args.username is not None:
				self.set_pref('username',self.username)
#			else:
#				raise BtSyncAgentException(-1,
#					'Username must be specified when saving defaults')
			if self.args.password is not None:
				self.set_pref('password',self.password)
#			else:
#				raise BtSyncAgentException(-1,
#					'Password must be specified when saving defaults')
			if self.args.bindui is not None:
				# changed bind address for web ui
				self.set_pref('bindui',self.bindui)
			if self.args.port != 0:
				# changed bind port for web ui
				self.set_pref('portui',self.portui)
			if self.args.webui:
				self.set_pref('webui',self.args.webui)
			raise BtSyncAgentException(0, _('Default settings saved.'))
		# initialize btsync api
		self.set_connection_params(
			host = self.get_host(), port = self.get_port(),
			username = self.get_username(), password = self.get_password()
		)
		if self.is_auto():
			self.lock = BtSingleton(self.lockfile,'btsync-gui')

	def __del__(self):
		self.shutdown()

	def startup(self):
		if self.args.host == 'auto':
			# we have to handle everything
			try:
				if not os.path.isdir(self.configpath):
					os.makedirs(self.configpath)
				if not os.path.isdir(self.storagepath):
					os.makedirs(self.storagepath)

				while self.is_running():
					logging.info ('Found running btsync agent. Stopping...')
					os.kill (self.pid, signal.SIGTERM)
					time.sleep(1)
					
				if not self.is_paused():
					logging.info ('Starting btsync agent...')
					self.start_agent()
			except Exception:
				logging.critical('Failure to start btsync agent - exiting...')
				exit (-1)

	def suspend(self):
		if self.args.host == 'auto':
			if not self.paused:
				self.paused = True
				self.set_pref('paused', True)
				logging.info ('Suspending btsync agent...')
				if self.is_running():
					self.kill_agent()

	def resume(self):
		if self.args.host == 'auto':
			if self.paused:
				self.paused = False
				self.set_pref('paused', False)
				logging.info ('Resuming btsync agent...')
				if not self.is_running():
					self.start_agent()

	def shutdown(self):
		if self.is_primary() and self.is_running():
			logging.info ('Stopping btsync agent...')
			self.kill_agent()
			self.kill_config_file()

	def start_agent(self):
		if not self.is_running():
			self.make_config_file()
			subprocess.call([BtSyncAgent.BINARY, '--config', self.conffile])
			time.sleep(0.5)
			if self.is_running():
				# no guarantee that it's already running...
				self.kill_config_file()

	def kill_agent(self):
		BtSyncApi.shutdown(self,throw_exceptions=False)
		time.sleep(0.5)
		if self.is_running():
			try:
				os.kill (self.pid, signal.SIGTERM)
			except OSError:
				# ok the process has stopped before we tried to kill it...
				pass

	def set_pref(self,key,value,flush=True):
		self.prefs[key] = value
		if flush:
			self.save_prefs()

	def get_pref(self,key,default):
		return self.prefs.get(key,default)

	def load_prefs(self):
		if not os.path.isfile(self.preffile):
			self.prefs = {}
			return
		try:
			pref = open (self.preffile, 'r')
			result = json.load(pref)
			pref.close()
			if isinstance(result,dict):
				self.prefs = result
			else:
				print "Error: " +str(result)
		except Exception as e:
			logging.warning('Error while loading preferences: {0}'.format(e))
			self.prefs = {}

	def save_prefs(self):
		try:
			pref = open (self.preffile, 'w')
			os.chmod(self.preffile, stat.S_IRUSR | stat.S_IWUSR)
			json.dump(self.prefs,pref)
			pref.close()
		except Exception as e:
			logging.error('Error while saving preferences: {0}'.format(e))

	def is_auto(self):
		return self.args.host == 'auto'

	def is_primary(self):
		return self.args.host == 'auto' and isinstance(self.lock,BtSingleton)

	def is_paused(self):
		return self.paused;

	def is_local(self):
		return self.args.host == 'auto' or \
			self.args.host == 'localhost' or \
			self.args.host == '127.0.0.1'

	def is_webui(self):
		return self.webui;

	def get_lock_filename(self):
		return os.environ['HOME'] + '/.config/btsync/btsync-gui.lock'

	def get_host(self):
		return 'localhost' if self.is_auto() else self.args.host

	def get_port(self):
		return self.portui if self.is_auto() else self.args.port if self.args.port != 0 else 8888

	def get_username(self):
		return self.username if self.is_auto() else self.args.username

	def get_password(self):
		return self.password if self.is_auto() else self.args.password

	def get_debug(self):
		if self.args.host == 'auto':
			return os.path.isfile(self.storagepath + '/debug.txt')
		else:
			return False

	def set_debug(self,activate=True):
		if self.args.host == 'auto':
			if activate:
				deb = open (self.storagepath + '/debug.txt', 'w')
				deb.write('FFFF\n')
				deb.close
			else:
				os.remove (self.storagepath + '/debug.txt')

	def make_config_file(self):
		try:
			cfg = open (self.conffile, 'w')
			os.chmod(self.conffile, stat.S_IRUSR | stat.S_IWUSR)
			cfg.write('{\n')
			cfg.write('\t"pid_file" : "{0}",\n'.format(self.pidfile))
			cfg.write('\t"storage_path" : "{0}",\n'.format(self.storagepath))
			# cfg.write('\t"use_gui" : false,\n')
			cfg.write('\t"webui" : \n\t{\n')
			cfg.write('\t\t"listen" : "{0}:{1}",\n'.format(self.bindui,self.portui))
			cfg.write('\t\t"login" : "{0}",\n'.format(self.username))
			cfg.write('\t\t"password" : "{0}",\n'.format(self.password))
			cfg.write('\t\t"api_key" : "{}"\n'.format(self.get_api_key()))
			cfg.write('\t}\n')
			cfg.write('}\n')
			cfg.close()
		except Exception:
			logging.critical('Cannot create {0} - exiting...'.format(self.configpath))
			exit (-1)

	def kill_config_file(self):
		if os.path.isfile(self.conffile):
			os.remove(self.conffile)

	def read_pid(self):
		try:
			pid = open (self.pidfile, 'r')
			pidstr = pid.readline().strip('\r\n')
			pid.close()
			self.pid = int(pidstr)
		except Exception:
			self.pid = None
		return self.pid

	def is_running(self):
		self.read_pid()
		if self.pid is None:
			return False
		# very linuxish...
		if not os.path.isdir('/proc/{0}'.format(self.pid)):
			return False
		try:
			pid = open('/proc/{0}/cmdline'.format(self.pid), 'r')
			cmdline = pid.readline()
			pid.close()
			fields = cmdline.split('\0')
			if fields[0] == BtSyncAgent.BINARY:
				return True
			return False
		except Exception:
			return False

	@staticmethod
	def get_api_key():
		try:
			akf = open('/usr/lib/btsync-gui/btsync-gui.key','r')
			key = akf.readline()
			akf.close()
			return key.rstrip('\n\r')
		except IOError:
			logging.critical('API Key not found. Stopping application.')
			exit (-1)


########NEW FILE########
__FILENAME__ = btsyncapi
# coding=utf-8
#
# Copyright 2014 Leo Moll
#
# Authors: Leo Moll and Contributors (see CREDITS)
#
# Thanks to Mark Johnson for btsyncindicator.py which gave me the
# last nudge needed to learn python and write my first linux gui
# application. Thank you!
#
# This file is part of btsync-gui. btsync-gui is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import json
import logging
import requests

class BtSyncApi(object):
	"""
	The BtSyncApi class is a light wrapper around the Bittorrent Sync API.
	Currently to use the API you will need to apply for a key. You can find out
	how to do that, and learn more about the btsync API here:

	http://www.bittorrent.com/sync/developers/api

	The docstrings of this class' methods were copied from the above site.
	"""

	def __init__(self,host='localhost',port='8888',username=None,password=None):
		"""
		Parameters
		----------
		host : str
		    IP address that the btsync api responds at.
		port : str
		    Port that the btsync api responds at.
		username : str
		    optional username to use if btsync api is protected.
		password : str
		    optional password to use if btsync api is protected.

		Notes
		-----
		The host, port, username, and password must match the config.json file.

		"""
		self.set_connection_params(host,port,username,password)
		self.response = None

	def set_connection_params(self, host='localhost', port='8888', username=None, password=None):
		if username is None or password is None:
			self.auth = None
		else:
			self.auth = (username,password)
		self.urlroot = 'http://{0}:{1}/api'.format(host,port)

	def get_folders(self,secret=None,throw_exceptions=True):
		"""
		Returns an array with folders info. If a secret is specified, will
		return info about the folder with this secret.

		[
			{
				"dir": "\\\\?\\D:\\share",
				"secret": "A54HDDMPN4T4BTBT7SPBWXDB7JVYZ2K6D",
				"size": 23762511569,
				"type": "read_write",
				"files": 3206,
				"error": 0,
				"indexing": 0
			}
		]

		http://[address]:[port]/api?method=get_folders[&secret=(secret)]

		secret (optional) - if a secret is specified, will return info about
		the folder with this secret
		"""
		params = {'method': 'get_folders'}
		if secret is not None:
			params['secret'] = secret
		return self._request(params,throw_exceptions)

	def add_folder(self,folder,secret=None,selective_sync=False,throw_exceptions=True):
		"""
		Adds a folder to Sync. If a secret is not specified, it will be
		generated automatically. The folder will have to pre-exist on the disk
		and Sync will add it into a list of syncing folders.
		Returns '0' if no errors, error code and error message otherwise.

		{ "error": 0 }

		http://[address]:[port]/api?method=add_folder&dir=(folderPath)[&secret=(secret)&selective_sync=1]

		dir (required)				- specify path to the sync folder
		secret (optional)			- specify folder secret
		selective_sync (optional)	- specify sync mode, selective - 1,
										all files (default) - 0
		"""
		params = {'method': 'add_folder', 'dir': folder }
		if secret is not None:
			params['secret'] = secret
		if selective_sync:
			params['selective_sync'] = 1
		return self._request(params,throw_exceptions)

	def remove_folder(self,secret,throw_exceptions=True):
		"""
		Removes folder from Sync while leaving actual folder and files on
		disk. It will remove a folder from the Sync list of folders and
		does not touch any files or folders on disk. Returns '0' if no error,
		'1' if there’s no folder with specified secret.

		{ "error": 0 }

		http://[address]:[port]/api?method=remove_folder&secret=(secret)

		secret (required) - specify folder secret
		"""
		params = { 'method': 'remove_folder', 'secret' : secret }
		return self._request(params,throw_exceptions)

	def get_files(self,secret,path=None,throw_exceptions=True):
		"""
		Returns list of files within the specified directory. If a directory is
		not specified, will return list of files and folders within the root
		folder. Note that the Selective Sync function is only available in the
		API at this time.

		[
			{
				"name": "images",
				"state": "created",
				"type": "folder"
			},
			{
				"have_pieces": 1,
				"name": "index.html",
				"size": 2726,
				"state": "created",
				"total_pieces": 1,
				"type": "file",
				"download": 1 // only for selective sync folders
			}
		]

		http://[address]:[port]/api?method=get_files&secret=(secret)[&path=(path)]

		secret (required) - must specify folder secret
		path (optional) - specify path to a subfolder of the sync folder.
		"""
		params = { 'method': 'get_files', 'secret' : secret }
		if path is not None:
			params['path'] = path
		return self._request(params,throw_exceptions)

	def set_file_preferences(self,secret,path,download,throw_exceptions=True):
		"""
		Selects file for download for selective sync folders. Returns file
		information with applied preferences.

		http://[address]:[port]/api?method=set_file_prefs&secret=(secret)&path=(path)&download=1

		secret (required)	- must specify folder secret
		path (required)		- specify path to a subfolder of the sync folder.
		download (required)	- specify if file should be downloaded (yes - 1, no - 0)		
		"""
		params = {
			'method': 'set_file_preferences',
			'secret': secret,
			'path': path,
			'download': download
		}
		if path is not None:
			params['path'] = path
		return self._request(params,throw_exceptions)

	def get_folder_peers(self,secret,throw_exceptions=True):
		"""
		Returns list of peers connected to the specified folder.

		[
		    {
			"id": "ARRdk5XANMb7RmQqEDfEZE-k5aI=",
			"connection": "direct", // direct or relay
			"name": "GT-I9500",
			"synced": 0, // timestamp when last sync completed
			"download": 0,
			"upload": 22455367417
		    }
		]

		http://[address]:[port]/api?method=get_folder_peers&secret=(secret)

		secret (required) - must specify folder secret
		"""
		params = { 'method': 'get_folder_peers', 'secret' : secret }
		return self._request(params,throw_exceptions)

	def get_secrets(self,secret=None,encryption=False,throw_exceptions=True):
		"""
		Generates read-write, read-only and encryption read-only secrets.
		If ‘secret’ parameter is specified, will return secrets available for
		sharing under this secret.
		The Encryption Secret is new functionality. This is a secret for a
		read-only peer with encrypted content (the peer can sync files but can
		not see their content). One example use is if a user wanted to backup
		files to an untrusted, unsecure, or public location. This is set to
		disabled by default for all users but included in the API.

		{
			"read_only": "ECK2S6MDDD7EOKKJZOQNOWDTJBEEUKGME",
			"read_write": "DPFABC4IZX33WBDRXRPPCVYA353WSC3Q6",
			"encryption": "G3PNU7KTYM63VNQZFPP3Q3GAMTPRWDEZ”
		}

		http://[address]:[port]/api?method=get_secrets[&secret=(secret)&type=encryption]

		secret (required) - must specify folder secret
		type (optional) - if type=encrypted, generate secret with support of encrypted peer
		"""
		params = { 'method': 'get_secrets' }
		if secret is not None:
			params['secret'] = secret
		if encryption:
			params['type'] = 'encryption'
		return self._request(params,throw_exceptions)

	def get_folder_prefs(self,secret,throw_exceptions=True):
		"""
		Returns preferences for the specified sync folder.

		{
			"search_lan":1,
			"use_dht":0,
			"use_hosts":0,
			"use_relay_server":1,
			"use_sync_trash":1,
			"use_tracker":1
		}

		http://[address]:[port]/api?method=get_folder_prefs&secret(secret)

		secret (required) - must specify folder secret
		"""
		params = { 'method': 'get_folder_prefs', 'secret' : secret }
		return self._request(params,throw_exceptions)

	def set_folder_prefs(self,secret,prefs_dictionary,throw_exceptions=True):
		"""
		Sets preferences for the specified sync folder. Parameters are the same
		as in ‘Get folder preferences’. Returns current settings.

		http://[address]:[port]/api?method=set_folder_prefs&secret=(secret)&param1=value1&param2=value2,...

		secret (required) - must specify folder secret
		params - { use_dht, use_hosts, search_lan, use_relay_server, use_tracker, use_sync_trash }
		"""
		params = { 'method': 'set_folder_prefs', 'secret' : secret }
		params.update (prefs_dictionary)
		return self._request(params,throw_exceptions)

	def get_folder_hosts(self,secret,throw_exceptions=True):
		"""
		Returns list of predefined hosts for the folder, or error code if a
		secret is not specified.

		{
			"hosts" : ["192.168.1.1:4567",
			"example.com:8975"]
		}

		http://[address]:[port]/api?method=get_folder_hosts&secret=(secret)

		secret (required) - must specify folder secret
		"""
		params = { 'method': 'get_folder_hosts', 'secret' : secret }
		return self._request(params,throw_exceptions)

	def set_folder_hosts(self,secret,hosts_list = [],throw_exceptions=True):
		"""
		Sets one or several predefined hosts for the specified sync folder.
		Existing list of hosts will be replaced. Hosts should be added as values
		of the ‘host’ parameter and separated by commas.
		Returns current hosts if set successfully, error code otherwise.

		http://[address]:[port]/api?method=set_folder_hosts&secret=(secret)&hosts=host1:port1,host2:port2,...

		secret (required)	- must specify folder secret
		hosts (required)	- enter list of hosts separated by comma.
								Host should be represented as “[address]:[port]”
		"""
		params = {
			'method': 'set_folder_hosts',
			'secret': secret,
			'hosts': hosts_list
		}
		return self._request(params,throw_exceptions)

	def get_prefs(self,throw_exceptions=True):
		"""
		Returns BitTorrent Sync preferences. Contains dictionary with
		advanced preferences. Please see Sync user guide for description
		of each option.

		{
			"device_name" : "iMac",
			"disk_low_priority": "true",
			"download_limit": 0,
			"folder_rescan_interval": "600",
			"lan_encrypt_data": "true",
			"lan_use_tcp": "false",
			"lang": -1,
			"listening_port": 11589,
			"max_file_size_diff_for_patching": "1000",
			"max_file_size_for_versioning": "1000",
			"rate_limit_local_peers": "false",
			"send_buf_size": "5",
			"sync_max_time_diff": "600",
			"sync_trash_ttl": "30",
			"upload_limit": 0,
			"use_upnp": 0,
			"recv_buf_size": "5"
		}
		"""
		params = {'method': 'get_prefs'}
		return self._request(params,throw_exceptions)

	def set_prefs(self,prefs_dictionary,throw_exceptions=True):
		"""
		Sets BitTorrent Sync preferences. Parameters are the same as in
		'Get preferences'. Advanced preferences are set as general
		 settings. Returns current settings.
		"""
		params = {'method': 'set_prefs'}
		params.update (prefs_dictionary)
		return self._request(params,throw_exceptions)

	def get_os(self,throw_exceptions=True):
		"""
		Returns OS name where BitTorrent Sync is running.

		{ "os": "win32" }

		http://[address]:[port]/api?method=get_os
		"""
		params = {'method': 'get_os'}
		return self._request(params,throw_exceptions)

	def get_version(self,throw_exceptions=True):
		"""
		Returns BitTorrent Sync version.

		{ "version": "1.2.48" }

		http://[address]:[port]/api?method=get_version
		"""
		params = {'method': 'get_version'}
		return self._request(params,throw_exceptions)

	def get_speed(self,throw_exceptions=True):
		"""
		Returns current upload and download speed.

		{
		    "download": 61007,
		    "upload": 0
		}

		http://[address]:[port]/api?method=get_speed
		"""
		params = {'method': 'get_speed'}
		return self._request(params,throw_exceptions)


	def shutdown(self,throw_exceptions=True):
		"""
		Gracefully stops Sync.

		{ "error" : 0 }

		http://[address]:[port]/api?method=shutdown
		"""
		params = {'method': 'shutdown'}
		return self._request(params,throw_exceptions)




	def get_status_code(self):
		"""
		Returns the HTTP status code of the last operation
		"""
		return self.response.status_code

	@staticmethod
	def fix_decode(text):
		"""
		Quick and dirty function that fixes the strange way special encoded
		strings are returned
		"""
		return text.encode('latin-1').decode('utf-8')


	@staticmethod
	def get_safe_result(result,key,default=None):
		"""
		Returns the value from a result key if existing, otherwise the supplied default
		"""
		if result is None:
			return default
		elif result.has_key(key):
			return result[key]
		else:
			return default

	@staticmethod
	def get_error_code(result):
		"""
		Returns a numerical error code for the given result
		"""
		if result is None:
			return 999
		elif result.has_key('error'):
			return result['error']
		elif result.has_key('result'):
			return result['result']
		else:
			return 0

	@staticmethod
	def get_error_message(result):
		"""
		Returns an error message for the given result
		"""
		if result is None:
			return 'Invalid result (connection error)'
		elif result.has_key('error') and result['error'] > 0:
			if result.has_key('message'):
				return result['message']
			else:
				return BtSyncApi.get_error_text(result['error'])
		elif result.has_key('result') and result['result'] > 0:
			if result.has_key('message'):
				return result['message']
			else:
				return BtSyncApi.get_error_text(result['result'])
		else:
			return 'No error'

	@staticmethod
	def get_error_text(code):
		return {
			100 : 'Can\'t open the destination folder.',
			101 : 'Don\'t have permission to write to the selected folder.'
		}.get(code, 'Error {0}'.format(code))
	

	def _request(self,params,throw_exceptions):
		"""
		Internal function that handles the communication with btsync
		"""
		if throw_exceptions:
			self.response = requests.get(self.urlroot, params=params, auth=self.auth)
			self.response.raise_for_status()
			return json.loads (self._get_response_text())

		try:
			self.response = requests.get(self.urlroot, params=params, auth=self.auth)
			self.response.raise_for_status()
			return json.loads (self._get_response_text())
		except requests.exceptions.ConnectionError:
			logging.warning("Couldn't connect to Bittorrent Sync")
			return None
		except requests.exceptions.HTTPError:
			logging.warning('Communication Error ' + str(self.response.status_code))
			return None

	def _get_response_text(self):
		"""
		Version-safe way to get the response text from a requests module response object
		Older versions use response.content instead of response.text
		"""
		return self.response.text if hasattr(self.response, "text") else self.response.content




########NEW FILE########
__FILENAME__ = btsyncapp
# coding=utf-8
#
# Copyright 2014 Leo Moll
#
# Authors: Leo Moll and Contributors (see CREDITS)
#
# Thanks to Mark Johnson for btsyncindicator.py which gave me the
# last nudge needed to learn python and write my first linux gui
# application. Thank you!
#
# This file is part of btsync-gui. btsync-gui is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import os
import md5
import gettext
import logging
import requests
import datetime

from gettext import gettext as _
from gi.repository import Gtk, Gdk, GObject, Pango

from btsyncagent import BtSyncAgent
from btsyncutils import BtInputHelper,BtMessageHelper,BtValueDescriptor,BtDynamicTimeout
from dialogs import BtSyncFolderAdd,BtSyncFolderRemove,BtSyncFolderScanQR,BtSyncFolderPrefs,BtSyncPrefsAdvanced

class BtSyncApp(BtInputHelper,BtMessageHelper):

	def __init__(self,agent):
		self.agent = agent

		self.builder = Gtk.Builder()
		self.builder.set_translation_domain('btsync-gui')
		self.builder.add_from_file(os.path.dirname(__file__) + "/btsyncapp.glade")
		self.builder.connect_signals (self)

		width, height = self.agent.get_pref('windowsize', (602,328))

		self.window = self.builder.get_object('btsyncapp')
		self.window.set_default_size(width, height)
		self.window.connect('delete-event',self.onDelete)
		if not self.agent.is_auto():
			title = self.window.get_title()
			self.window.set_title('{0} - ({1}:{2})'.format(
				title,
				agent.get_host(),
				agent.get_port()
			))
		self.window.show()

		self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
		self.app_status_to = BtDynamicTimeout(1000,self.refresh_app_status)
		self.dlg = None

		self.prefs = self.agent.get_prefs()

		self.init_folders_controls()
		self.init_devices_controls()
		self.init_transfers_controls()
		self.init_history_controls()
		self.init_preferences_controls()

		# TODO: Hide pages not supported by API
		notebook = self.builder.get_object('notebook1')
		transfers = notebook.get_nth_page(2)
		history = notebook.get_nth_page(3)
		transfers.hide()
		history.hide()
		# TODO: End

		self.init_transfer_status()

		self.init_folders_values()
		self.init_preferences_values()

	def close(self):
		self.app_status_to.stop()
		if self.dlg is not None:
			self.dlg.response(Gtk.ResponseType.CANCEL)

	def connect_close_signal(self,handler):
		return self.window.connect('delete-event', handler)

	def init_folders_controls(self):
		self.folders = self.builder.get_object('folders_list')
		self.folders_menu = self.builder.get_object('folders_menu')
		self.folders_menu_openfolder = self.builder.get_object('folder_menu_openfolder')
		self.folders_menu_openarchive = self.builder.get_object('folder_menu_openarchive')
		self.folders_menu_editsyncignore = self.builder.get_object('folder_menu_editsyncignore')
		self.folders_selection = self.builder.get_object('folders_selection')
		self.folders_treeview = self.builder.get_object('folders_tree_view')
		self.folders_activity_label = self.builder.get_object('folders_activity_label')
		self.folders_add = self.builder.get_object('folders_add')
		self.folders_remove = self.builder.get_object('folders_remove')
		self.folders_remove.set_sensitive(False)
		self.set_treeview_column_widths(
			self.folders_treeview,
			self.agent.get_pref('folders_columns',[300])
		)
		self.set_treeview_sort_info(
			self.folders_treeview,
			self.agent.get_pref('folders_sortinfo', [0, Gtk.SortType.ASCENDING])
		)

	def init_folders_values(self):
		try:
			self.lock()
			folders = self.agent.get_folders()
			if folders is not None:
				for index, value in enumerate(folders):
					# see in update_folder_values the insane explanation why
					# also an md5 digest has to be saved
					digest = md5.new(value['dir'].encode('latin-1')).hexdigest()
					self.folders.append ([
						self.agent.fix_decode(value['dir']),		# 0:Folder
						self.get_folder_info_string(value),			# 1:Content
						value['secret'],							# 2:Secret
						digest,										# 3:FolderTag
						Pango.EllipsizeMode.END						# 4:EllipsizeMode
					])
					self.add_device_infos(value,digest)
			self.unlock()
			self.app_status_to.start()
		except requests.exceptions.ConnectionError:
			self.unlock()
			self.onConnectionError()
		except requests.exceptions.HTTPError:
			self.unlock()
			self.onCommunicationError()

	def init_devices_controls(self):
		self.devices = self.builder.get_object('devices_list')
		self.devices_treeview = self.builder.get_object('devices_tree_view')
		self.devices_activity_label = self.builder.get_object('devices_activity_label')
		self.set_treeview_column_widths(
			self.devices_treeview,self.agent.get_pref('devices_columns',[150,300])
		) 
		self.set_treeview_sort_info(
			self.devices_treeview,
			self.agent.get_pref('devices_sortinfo', [0, Gtk.SortType.ASCENDING])
		)

	def init_transfers_controls(self):
		self.transfers = self.builder.get_object('transfers_list')
		self.transfers_treeview = self.builder.get_object('transfers_tree_view')
		self.transfers_activity_label = self.builder.get_object('transfers_activity_label')
		# TODO: remove placeholder as soon as the suitable API call permits
		#       a working implementation...
		self.transfers.append ([
			_('Cannot implement due to missing API'),	# 0:
			_('BitTorrent Inc.'),						# 1:
			'',											# 2:
			'',											# 3:
			Pango.EllipsizeMode.END						# 4:EllipsizeMode
		])
		self.set_treeview_column_widths(
			self.transfers_treeview,self.agent.get_pref('transfers_columns',[300,150,80])
		) 

	def init_history_controls(self):
		self.history = self.builder.get_object('history_list')
		self.history_treeview = self.builder.get_object('history_tree_view')
		self.history_activity_label = self.builder.get_object('history_activity_label')
		# TODO: remove placeholder as soon as the suitable API call permits
		#       a working implementation...
		self.history.append ([
			_('Now'),									# 0:
			_('Cannot implement due to missing API'),	# 1:
			Pango.EllipsizeMode.END						# 4:EllipsizeMode
		])
		self.set_treeview_column_widths(
			self.history_treeview,self.agent.get_pref('history_columns',[150])
		) 

	def refresh_app_status(self):
		try:
			self.lock()
			folders = self.agent.get_folders()
			# forward scan updates existing folders and adds new ones
			for index, value in enumerate(folders):
				# see in update_folder_values the insane explanation why
				# also an md5 digest has to be saved
				digest = md5.new(value['dir'].encode('latin-1')).hexdigest()
				if not self.update_folder_values(value):
					# it must be new (probably added via web interface) - let's add it
					self.folders.append ([
						self.agent.fix_decode(value['dir']),	# 0:Folder
						self.get_folder_info_string(value),			# 1:Content
						value['secret'],							# 2:Secret
						digest,										# 3:FolderTag
						Pango.EllipsizeMode.END						# 4:EllipsizeMode
					])
				self.update_device_infos(value,digest)
			# reverse scan deletes disappeared folders...
			for row in self.folders:
				if not self.folder_exists(folders,row):
					self.folders.remove(row.iter)
					self.remove_device_infos(row[2],row[3])
			# update transfer status
			self.update_transfer_status(self.agent.get_speed())
			# TODO: fill file list...
			#       but there is still no suitable API call...
			self.unlock()
			return True
		except requests.exceptions.ConnectionError:
			self.unlock()
			return self.onConnectionError()
		except requests.exceptions.HTTPError:
			self.unlock()
			return self.onCommunicationError()

	def init_transfer_status(self):
		self.update_transfer_status({'upload':0,'download':0})

	def update_transfer_status(self,speed):
		activity = _('{0:.1f} kB/s up, {1:.1f} kB/s down').format(speed['upload'] / 1000, speed['download'] / 1000)
		self.folders_activity_label.set_label(activity)
		self.devices_activity_label.set_label(activity)
		self.transfers_activity_label.set_label(activity)
		self.history_activity_label.set_label(activity)

	def update_folder_values(self,value):
		for row in self.folders:
			if value['secret'] == row[2]:
				# found - update information
				row[1] = self.get_folder_info_string(value)
				return True
			elif md5.new(value['dir'].encode('latin-1')).hexdigest() == row[3]:
				# comparing the md5 digests avoids casting errors due to the
				# insane encoding fix tecnique
				# found - secret was changed
				row[1] = self.get_folder_info_string(value)
				row[2] = value['secret']
				return True
		# not found
		return False

	def folder_exists(self,folders,row):
		if folders is not None:
			for index, value in enumerate(folders):
				if value['secret'] == row[2]:
					return True
				elif md5.new(value['dir'].encode('latin-1')).hexdigest() == row[3]:
					# comparing the md5 digests avoids casting errors due to the
					# insane encoding fix tecnique
					return True
		return False

	def add_device_infos(self,folder,digest):
		foldername = self.agent.fix_decode(folder['dir'])
		peers = self.agent.get_folder_peers(folder['secret'])
		for index, value in enumerate(peers):
			self.devices.append ([
				self.agent.fix_decode(value['name']),		# 0:Device
				foldername,									# 1:Folder
				self.get_device_info_string(value),			# 2:Status
				folder['secret'],							# 3:Secret
				digest,										# 4:FolderTag
				value['id'],								# 5:DeviceTag
				self.get_device_info_icon_name(value),		# 6:ConnectionIconName
				Pango.EllipsizeMode.END						# 7:EllipsizeMode
			])

	def update_device_infos(self,folder,digest):
		foldername = self.agent.fix_decode(folder['dir'])
		peers = self.agent.get_folder_peers(folder['secret'])
		# forward scan updates existing and adds new
		for index, value in enumerate(peers):
			if not self.update_device_values(folder,value,digest):
				# it must be new - let's add it
					self.devices.append ([
					self.agent.fix_decode(value['name']),		# 0:Device
					foldername,									# 1:Folder
					self.get_device_info_string(value),			# 2:Status
					folder['secret'],							# 3:Secret
					digest,										# 4:FolderTag
					value['id'],								# 5:DeviceTag
					self.get_device_info_icon_name(value),		# 6:ConnectionIconName
					Pango.EllipsizeMode.END						# 7:EllipsizeMode
				])
		# reverse scan deletes disappeared folders...
		for row in self.devices:
			if row[3] == folder['secret'] or row[4] == digest:
				# it's our folder
				if not self.device_exists(peers,row):
					self.devices.remove(row.iter)

	def update_device_values(self,folder,peer,digest):
		for row in self.devices:
			if peer['id'] == row[5] and folder['secret'] == row[3]:
				# found - update information
				row[0] = self.agent.fix_decode(peer['name'])
				row[2] = self.get_device_info_string(peer)
				row[6] = self.get_device_info_icon_name(peer)
				return True
			elif peer['id'] == row[5] and digest == row[4]:
				# found - secret probably changed...
				row[0] = self.agent.fix_decode(peer['name'])
				row[2] = self.get_device_info_string(peer)
				row[3] = folder['secret']
				row[6] = self.get_device_info_icon_name(peer)
				return True
		# not found
		return False

	def remove_device_infos(self,secret,digest=None):
		for row in self.devices:
			if secret == row[3]:
				self.devices.remove(row.iter)
			elif digest is not None and digest == row[4]:
				self.devices.remove(row.iter)

	def device_exists(self,peers,row):
		for index, value in enumerate(peers):
			if value['id'] == row[5]:
				return True
		return False

	def get_folder_info_string(self,folder):
		if folder['error'] == 0:
			if folder['indexing'] == 0:
				return _('{0} in {1} files').format(self.sizeof_fmt(folder['size']), str(folder['files']))
			else:
				return _('{0} in {1} files (indexing...)').format(self.sizeof_fmt(folder['size']), str(folder['files']))
		else:
			return self.agent.get_error_message(folder)

	def get_device_info_icon_name(self,peer):
		return {
			'direct' : 'btsync-gui-direct',
			'relay'  : 'btsync-gui-cloud'
		}.get(peer['connection'], 'btsync-gui-unknown')

	def get_device_info_string(self,peer):
		if peer['synced'] != 0:
			dt = datetime.datetime.fromtimestamp(peer['synced'])
			return _('Synched on {0}').format(dt.strftime("%x %X"))
		elif peer['download'] == 0 and peer['upload'] != 0:
			return _('⇧ {0}').format(self.sizeof_fmt(peer['upload']))
		elif peer['download'] != 0 and peer['upload'] == 0:
			return _('⇩ {0}').format(self.sizeof_fmt(peer['download']))
		elif peer['download'] != 0 and peer['upload'] != 0:
			return _('⇧ {0} - ⇩ {1}').format(self.sizeof_fmt(peer['upload']), self.sizeof_fmt(peer['download']))
		else:
			return _('Idle...')

	def init_preferences_controls(self):
		self.devname = self.builder.get_object('devname')
		self.autostart = self.builder.get_object('autostart')
		self.listeningport = self.builder.get_object('listeningport')
		self.upnp = self.builder.get_object('upnp')
		self.limitdn = self.builder.get_object('limitdn')
		self.limitdnrate = self.builder.get_object('limitdnrate')
		self.limitup = self.builder.get_object('limitup')
		self.limituprate = self.builder.get_object('limituprate')

	def init_preferences_values(self):
		self.lock()
		self.attach(self.devname,BtValueDescriptor.new_from('device_name',self.prefs['device_name']))
		# self.autostart.set_active(self.prefs[""]);
		self.autostart.set_sensitive(False)
		self.attach(self.listeningport,BtValueDescriptor.new_from('listening_port',self.prefs['listening_port']))
		self.attach(self.upnp,BtValueDescriptor.new_from('use_upnp',self.prefs['use_upnp']))
		self.attach(self.limitdnrate,BtValueDescriptor.new_from('download_limit',self.prefs['download_limit']))
		self.attach(self.limituprate,BtValueDescriptor.new_from('upload_limit',self.prefs['upload_limit']))

		self.limitdn.set_active(self.prefs['download_limit'] > 0)
		self.limitup.set_active(self.prefs['upload_limit'] > 0)
		self.unlock()

	def get_treeview_column_widths(self,treewidget):
		columns = treewidget.get_columns()
		widths = []
		for index, value in enumerate(columns):
			widths.append(value.get_width())
		return widths

	def set_treeview_column_widths(self,treewidget,widths):
		columns = treewidget.get_columns()
		for index, value in enumerate(columns):
			if index < len(widths):
				value.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
				value.set_fixed_width(max(widths[index],32))

	def get_treeview_sort_info(self,treewidget):
		treemodel = treewidget.get_model()
		column_id, sort_order = treemodel.get_sort_column_id()
		return [column_id, int(sort_order)]

	def set_treeview_sort_info(self,treewidget,sortinfo):
		if sortinfo[0] is not None:
			treemodel = treewidget.get_model()
			treemodel.set_sort_column_id(sortinfo[0],sortinfo[1])
			columns = treewidget.get_columns()
			for index, value in enumerate(columns):
				if value.get_sort_column_id() == sortinfo[0]:
					value.set_sort_order(sortinfo[1])
					value.set_sort_indicator(True)
					return

	def onDelete(self, *args):
		width, height = self.window.get_size()
		self.agent.set_pref('windowsize', (width, height))
		self.agent.set_pref('folders_columns', self.get_treeview_column_widths(self.folders_treeview))
		self.agent.set_pref('devices_columns', self.get_treeview_column_widths(self.devices_treeview))
		self.agent.set_pref('transfers_columns', self.get_treeview_column_widths(self.transfers_treeview))
		self.agent.set_pref('history_columns', self.get_treeview_column_widths(self.history_treeview))
		self.agent.set_pref('folders_sortinfo', self.get_treeview_sort_info (self.folders_treeview))
		self.agent.set_pref('devices_sortinfo', self.get_treeview_sort_info (self.devices_treeview))
		self.close()

	def onSaveEntry(self,widget,valDesc,newValue):
		try:
			self.agent.set_prefs({valDesc.Name : newValue})
			self.prefs[valDesc.Name] = newValue
		except requests.exceptions.ConnectionError:
			return self.onConnectionError()
		except requests.exceptions.HTTPError:
			return self.onCommunicationError()
		return True

	def onFoldersSelectionChanged(self,selection):
		model, tree_iter = selection.get_selected()
		self.folders_remove.set_sensitive(selection.count_selected_rows() > 0)

	def onFoldersAdd(self,widget):
		self.dlg = BtSyncFolderAdd(self.agent)
		try:
			self.dlg.create()
			result = self.dlg.run()
			if result == Gtk.ResponseType.OK:
				# all checks have already been done. let's go!
				result = self.agent.add_folder(self.dlg.folder,self.dlg.secret)
				if self.agent.get_error_code(result) > 0:
					self.show_warning(self.window,self.agent.get_error_message(result))
		except requests.exceptions.ConnectionError:
			pass
		except requests.exceptions.HTTPError:
			pass
		finally:
			self.dlg.destroy()
			self.dlg = None

	def onFoldersRemove(self,widget):
		self.dlg = BtSyncFolderRemove()
		self.dlg.create()
		result = self.dlg.run()
		self.dlg.destroy()
		if result == Gtk.ResponseType.OK:
			model, tree_iter = self.folders_selection.get_selected()
			if tree_iter is not None:
				# ok - let's delete it!
				secret = model[tree_iter][2]
				try:
					result = self.agent.remove_folder(secret)
					if self.agent.get_error_code(result) == 0:
						self.folders.remove(tree_iter)
						self.remove_device_infos(secret)
					else:
						logging.error('Failed to remove folder ' + str(secret))
				except requests.exceptions.ConnectionError:
					pass
				except requests.exceptions.HTTPError:
					pass

	def onFoldersMouseClick(self,widget,event):
		x = int(event.x)
		y = int(event.y)
		time = event.time
		pathinfo = widget.get_path_at_pos(x,y)
		if pathinfo is not None:
			if event.button == 1:
				if event.type == Gdk.EventType._2BUTTON_PRESS or event.type == Gdk.EventType._3BUTTON_PRESS:
					path, column, cellx, celly = pathinfo
					widget.grab_focus()
					widget.set_cursor(path,column,0)
					model, tree_iter = self.folders_selection.get_selected()
					if tree_iter is not None:
						if os.path.isdir(model[tree_iter][0]):
							os.system('xdg-open "{0}"'.format(model[tree_iter][0]))
							return True
			elif event.button == 3:
				path, column, cellx, celly = pathinfo
				widget.grab_focus()
				widget.set_cursor(path,column,0)
				model, tree_iter = self.folders_selection.get_selected()
				if self.agent.is_local() and tree_iter is not None:
					self.folders_menu_openfolder.set_sensitive(
						os.path.isdir(model[tree_iter][0])
					)
					self.folders_menu_openarchive.set_sensitive(
						os.path.isdir(model[tree_iter][0] + '/.SyncArchive')
					)
					self.folders_menu_editsyncignore.set_sensitive(
						os.path.isfile(model[tree_iter][0] + '/.SyncIgnore')
					)
				else:
					self.folders_menu_openfolder.set_sensitive(False)
					self.folders_menu_openarchive.set_sensitive(False)
					self.folders_menu_editsyncignore.set_sensitive(False)

				self.folders_menu.popup(None,None,None,None,event.button,time)
				return True

	def onFoldersCopySecret(self,widget):
		model, tree_iter = self.folders_selection.get_selected()
		if tree_iter is not None:
			self.clipboard.set_text(model[tree_iter][2], -1)

	def onFoldersConnectMobile(self,widget):
		model, tree_iter = self.folders_selection.get_selected()
		if tree_iter is not None:
			result = self.agent.get_secrets(model[tree_iter][2], False)
			if self.agent.get_error_code(result) == 0:
				self.dlg = BtSyncFolderScanQR(
					result['read_write'] if result.has_key('read_write') else None,
					result['read_only'],
					os.path.basename(model[tree_iter][0])
				)
				self.dlg.create()
				result = self.dlg.run()
				self.dlg.destroy()
				self.dlg = None

	def onFoldersOpenFolder(self,widget):
		model, tree_iter = self.folders_selection.get_selected()
		if tree_iter is not None:
			if os.path.isdir(model[tree_iter][0]):
				os.system('xdg-open "{0}"'.format(model[tree_iter][0]))

	def onFoldersOpenArchive(self,widget):
		model, tree_iter = self.folders_selection.get_selected()
		if tree_iter is not None:
			syncarchive = model[tree_iter][0] + '/.SyncArchive'
			if os.path.isdir(syncarchive):
				os.system('xdg-open "{0}"'.format(syncarchive))

	def onFoldersEditSyncIgnore(self,widget):
		model, tree_iter = self.folders_selection.get_selected()
		if tree_iter is not None:
			syncignore = model[tree_iter][0] + '/.SyncIgnore'
			if os.path.isfile(syncignore):
				os.system('xdg-open "{0}"'.format(syncignore))

	def onFoldersPreferences(self,widget):
		model, tree_iter = self.folders_selection.get_selected()
		if tree_iter is not None:
			self.dlg = BtSyncFolderPrefs(self.agent)
			try:
				self.dlg.create(model[tree_iter][0],model[tree_iter][2])
				self.dlg.run()
			except requests.exceptions.ConnectionError:
				pass
			except requests.exceptions.HTTPError:
				pass
			finally:
				self.dlg.destroy()
				self.dlg = None

	def onPreferencesToggledLimitDn(self,widget):
		self.limitdnrate.set_sensitive(widget.get_active())
		if not self.is_locked():
			rate = int(self.limitdnrate.get_text()) if widget.get_active() else 0
			try:
				self.agent.set_prefs({"download_limit" : rate})
				self.prefs['download_limit'] = rate
			except requests.exceptions.ConnectionError:
				return self.onConnectionError()
			except requests.exceptions.HTTPError:
				return self.onCommunicationError()


	def onPreferencesToggledLimitUp(self,widget):
		self.limituprate.set_sensitive(widget.get_active())
		if not self.is_locked():
			rate = int(self.limituprate.get_text()) if widget.get_active() else 0
			try:
				self.agent.set_prefs({"upload_limit" : rate})
				self.prefs['upload_limit'] = rate
			except requests.exceptions.ConnectionError:
				return self.onConnectionError()
			except requests.exceptions.HTTPError:
				return self.onCommunicationError()

	def onPreferencesClickedAdvanced(self,widget):
		try:
			self.dlg = BtSyncPrefsAdvanced(self.agent)
			self.dlg.run()
		except requests.exceptions.ConnectionError:
			logging.error('BtSync API Connection Error')
		except requests.exceptions.HTTPError:
			logging.error('BtSync API HTTP error: {0}'.format(self.agent.get_status_code()))
		except Exception as e:
			# this should not really happen...
			logging.error('onPreferencesClickedAdvanced: Unexpected exception caught: '+str(e))
		finally:
			if isinstance(self.dlg, BtSyncPrefsAdvanced):
				self.dlg.destroy()
			self.dlg = None

	def onConnectionError(self):
		logging.error('BtSync API Connection Error')
		self.window.destroy()
		return False

	def onCommunicationError(self):
		logging.error('BtSync API HTTP error: {0}'.format(self.agent.get_status_code()))
		self.window.destroy()
		return False


########NEW FILE########
__FILENAME__ = btsyncguiapp
# coding=utf-8
#
# Copyright 2014 Leo Moll
#
# Authors: Leo Moll and Contributors (see CREDITS)
#
# Thanks to Mark Johnson for btsyncindicator.py which gave me the
# last nudge needed to learn python and write my first linux gui
# application. Thank you!
#
# This file is part of btsync-gui. btsync-gui is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import os
import sys
import dbus
import signal
import locale
import gettext
import logging
import argparse
import subprocess

from gettext import gettext as _
from gi.repository import Gtk

from btsyncagent import BtSyncAgent, BtSyncAgentException, BtSingleInstanceException
from btsyncstatus import *

class GuiApp:

	def __init__(self):
		self.agent = None
		self.indicator = None
		self._init_localisation()
		self._init_argparser()
		self._init_logger()
		try:
			# instantiate agent
			self.agent = BtSyncAgent(self.args)
			# create graceful shutdown mechanisms
			signal.signal(signal.SIGTERM, self.on_signal_term)
			self.bus = dbus.SessionBus()
			self.bus.call_on_disconnection(self.on_session_disconnect)
		except dbus.DBusException as e:
			# basically we can ignore this...
			logging.warning('Failed to connect to session bus: '+str(e))
		except BtSingleInstanceException as e:
			# we are running in auto mode and someone tries to start a
			# second instance
			logging.error(e.message)
			# exit - we cannot tollerate this!
			exit(-1)
		except BtSyncAgentException as e:
			# the agent has already finished his work...
			if e.retcode != 0:
				logging.error(e.message)
			else:
				logging.info(e.message)
				print e.message
			exit (e.retcode)
		except Exception as e:
			# this should not really happen...
			logging.critical('Unexpected exception caught: '+str(e))
			exit(-1)

	def run(self):
		try:
			self.agent.startup()
			# initialize indicator
			self.indicator = BtSyncStatus(self.agent)
			self.indicator.startup()
			# giro giro tondo...
			Gtk.main()
		except Exception as e:
			logging.critical('Unexpected exception caught: '+str(e))
		finally:
			# good night!
			self.shutdown()

	def shutdown(self,returncode=0):
		logging.info('Shutting down application...')
		if self.indicator is not None:
			self.indicator.shutdown()
		if self.agent is not None:
			self.agent.shutdown()
		logging.shutdown()
		exit(returncode)

	def on_session_disconnect(self, connection):
		logging.info('Disconnected from session bus. Shutting down...')
		self.shutdown()

	def on_signal_term(self, signum, frame):
		logging.warning('Signal {0} received. Shutting down...'.format(signum))
		self.shutdown()


	def _init_argparser(self):
		parser = argparse.ArgumentParser()

		parser.add_argument('--log',
					choices=['CRITICAL','ERROR','WARNING','INFO','DEBUG'],
					default='WARNING',
					help=_('Sets the logging level. By default the logging '\
					'level is WARNING'))
		parser.add_argument('--host',
					default='auto',
					help=_('Hostname for the connection to BitTorrent Sync. '\
					'If not specified, a local BitTorrent Sync agent will be '\
					'launched.'))
		parser.add_argument('--port', type=int,
					default=0,
					help=_('Optional port number for the connection to '\
					'BitTorrent Sync. If not specified, port 8888 is taken '\
					'for a connection to a remote BitTorrent Sync agent or '\
					'(8999 + uid) is taken when creating a locally launched '\
					'agent. This option can be made persistent for local '\
					'agents with --savedefaults'))
		parser.add_argument('--username',
					default=None,
					help=_('Optional user name for connecting to a remote '\
					'BitTorrent Sync agent or username to use when creating a '\
					'locally launched agent. This option can be made '\
					'persistent for local agents with --savedefaults'))
		parser.add_argument('--password',
					default=None,
					help=_('Optional password for connecting to a remote '\
					'BitTorrent Sync agent or password to use when creating a '\
					'locally launched agent. This option can be made '\
					'persistent for local agents with --savedefaults'))
		parser.add_argument('--bindui',
					default=None,
					help=_('Optional bind address for the Web UI of a locally '\
					'created BitTorrent Sync agent. By default the agent '\
					'binds to 127.0.0.1. If you want the Web UI of the agent '\
					'to be reachable by other computers, specify one of the '\
					'available IP addresses of this computer or "all" to bind '\
					'to all available adapters. This option can be made '\
					'persistent for local agents with --savedefaults'))
		parser.add_argument('--webui',
					default=False,
					action='store_true',
					help=_('Include the Web UI in the menu. This option can '\
					'be made persistent with --savedefaults'))
		parser.add_argument('--savedefaults',
					action='store_true',
					help=_('If specified, the optionally supplied '\
					'credentials, bind address, port information and storable '\
					'settings will be stored as default in the application '\
					'preferences and used when launching a local BitTorrent '\
					'Sync agent.'))
		parser.add_argument('--cleardefaults',
					action='store_true',
					help=_('If specified, all internally stored credentials, '\
					'bind address, port information and storable settings '\
					'will be cleared from the application preferences.'))

		self.args = parser.parse_args()

	def _init_logger(self):
		# initialize logger
		numeric_level = getattr(logging, self.args.log.upper(), None)
		if not isinstance(numeric_level, int):
			raise ValueError('Invalid log level: %s' % self.args.log)
		logging.basicConfig(level=numeric_level)
		if not os.path.isdir(os.environ['HOME'] + '/.btsync'):
			os.makedirs(os.environ['HOME'] + '/.btsync')
		fh = logging.FileHandler(filename=os.environ['HOME'] + '/.btsync/btsync-gui.log')
		ff = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
		fh.setFormatter(ff)
		logging.getLogger().addHandler(fh)
		logging.getLogger().setLevel(numeric_level)

	def _init_localisation(self):
		locale.setlocale(locale.LC_ALL, '')
		# gettext.bindtextdomain('btsync-gui','')
		gettext.textdomain('btsync-gui')




########NEW FILE########
__FILENAME__ = btsyncstatus
# coding=utf-8
#
# Copyright 2014 Leo Moll
#
# Authors: Leo Moll and Contributors (see CREDITS)
#
# Thanks to Mark Johnson for btsyncindicator.py which gave me the
# last nudge needed to learn python and write my first linux gui
# application. Thank you!
#
# This file is part of btsync-gui. btsync-gui is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import os
import urllib
import gettext
import logging
import requests
import webbrowser

from gettext import gettext as _
from gi.repository import Gtk, GObject

from trayindicator import TrayIndicator
from btsyncapp import BtSyncApp
from btsyncutils import BtDynamicTimeout

VERSION = '0.8.3'

class BtSyncStatus:
	DISCONNECTED	= 0
	CONNECTING		= 1
	CONNECTED		= 2
	PAUSED			= 3

	def __init__(self,agent):
		self.builder = Gtk.Builder()
		self.builder.set_translation_domain('btsync-gui')
		self.builder.add_from_file(os.path.dirname(__file__) + "/btsyncstatus.glade")
		self.builder.connect_signals (self)
		self.menu = self.builder.get_object('btsyncmenu')
		self.menuconnection = self.builder.get_object('connectionitem')
		self.menustatus = self.builder.get_object('statusitem')
		self.menupause = self.builder.get_object('pausesyncing')
		self.menudebug = self.builder.get_object('setdebug')
		self.menuopenweb = self.builder.get_object('openweb')
		self.menuopenapp = self.builder.get_object('openapp')
		self.about = self.builder.get_object('aboutdialog')


		self.ind = TrayIndicator (
			'btsync',
			'btsync-gui-disconnected'
		)
		if agent.is_auto():
			self.menuconnection.set_visible(False)
			self.ind.set_title(_('BitTorrent Sync'))
			self.ind.set_tooltip_text(_('BitTorrent Sync Status Indicator'))
		else:
			self.menuconnection.set_label('{0}:{1}'.format(agent.get_host(),agent.get_port()))
			self.ind.set_title(_('BitTorrent Sync {0}:{1}').format(agent.get_host(),agent.get_port()))
			self.ind.set_tooltip_text(_('BitTorrent Sync {0}:{1}').format(agent.get_host(),agent.get_port()))
		self.menuopenweb.set_visible(agent.is_webui())
		self.ind.set_menu(self.menu)
		self.ind.set_default_action(self.onActivate)

		# icon animator
		self.frame = 0
		self.rotating = False
		self.transferring = False
		self.animator_id = None

		# application window
		self.app = None

		# other variables
		self.connection = BtSyncStatus.DISCONNECTED
		self.connect_id = None
		self.status_to = BtDynamicTimeout(1000,self.btsync_refresh_status)
		self.agent = agent

	def startup(self):
		self.btsyncver = { 'version': '0.0.0' }
		# status
		if self.agent.is_auto():
			self.menupause.set_sensitive(self.agent.is_auto())
			if self.agent.is_paused():
				self.set_status(BtSyncStatus.PAUSED)
				self.menupause.set_active(True)
			else:
				self.set_status(BtSyncStatus.CONNECTING)
				self.menupause.set_active(False)
				self.connect_id = GObject.timeout_add(1000, self.btsync_connect)
		else:
			self.set_status(BtSyncStatus.CONNECTING)
			self.menupause.set_sensitive(False)
			self.menupause.set_active(False)
			self.connect_id = GObject.timeout_add(1000, self.btsync_connect)
		
	def shutdown(self):
		if self.animator_id is not None:
			GObject.source_remove(self.animator_id)
		if self.connect_id is not None:
			GObject.source_remove(self.connect_id)
		self.status_to.stop()

	def open_app(self):
		if isinstance(self.app, BtSyncApp):
			self.app.window.present()
		else:
			try:
				self.app = BtSyncApp(self.agent)
				self.app.connect_close_signal(self.onDeleteApp)
			except requests.exceptions.ConnectionError:
				return self.onConnectionError()
			except requests.exceptions.HTTPError:
				return self.onCommunicationError()

	def close_app(self,stillopen=True):
		if isinstance(self.app, BtSyncApp):
			if stillopen:
				self.app.close()
				# self.app.window.close()
				self.app.window.destroy()
			del self.app
			self.app = None

	def btsync_connect(self):
		if self.connection is BtSyncStatus.DISCONNECTED or \
			self.connection is BtSyncStatus.CONNECTING or \
			self.connection is BtSyncStatus.PAUSED:
			try:
				self.set_status(BtSyncStatus.CONNECTING)
				self.menustatus.set_label(_('Connecting...'))
				version = self.agent.get_version()
				self.btsyncver = version
				self.set_status(BtSyncStatus.CONNECTED)
				self.menustatus.set_label(_('Idle'))
				self.status_to.start()
				self.connect_id = None
				return False

			except requests.exceptions.ConnectionError:
				self.connect_id = None
				return self.onConnectionError()
			except requests.exceptions.HTTPError:
				self.connect_id = None
				return self.onCommunicationError()


		else:
			logging.info('Cannot connect since I\'m already connected')
		

	def btsync_refresh_status(self):
		if self.connection is not BtSyncStatus.CONNECTED:
			logging.info('Interrupting refresh sequence...')
			return False
		logging.info('Refresh status...')
		indexing = False
		transferring = False
		try:
			folders = self.agent.get_folders()
			for fIndex, fValue in enumerate(folders):
				if fValue['indexing'] > 0:
					indexing = True
# this takes too much resources...
#				peers = self.agent.get_folder_peers(fValue['secret'])
#				for pIndex, pValue in enumerate(peers):
#					if long(pValue['upload']) + long(pValue['download']) > 0:
#						transferring = True
#####
			speed = self.agent.get_speed()
			if transferring or speed['upload'] > 0 or speed['download'] > 0:
				# there are active transfers...
				self.set_status(BtSyncStatus.CONNECTED,True)
				self.menustatus.set_label(_('{0:.1f} kB/s up, {1:.1f} kB/s down').format(speed['upload'] / 1000, speed['download'] / 1000))
			elif indexing:
				self.set_status(BtSyncStatus.CONNECTED)
				self.menustatus.set_label(_('Indexing...'))
			else:
				self.set_status(BtSyncStatus.CONNECTED)
				self.menustatus.set_label(_('Idle'))
			return True
	
		except requests.exceptions.ConnectionError:
			return self.onConnectionError()
		except requests.exceptions.HTTPError:
			return self.onCommunicationError()

	def set_status(self,connection,transferring=False):
		if connection is BtSyncStatus.DISCONNECTED:
			self.frame = -1
			self.transferring = False
			self.ind.set_from_icon_name('btsync-gui-disconnected')
			self.menudebug.set_sensitive(False)
			self.menudebug.set_active(self.agent.get_debug())
			self.menuopenapp.set_sensitive(False)
			self.menuopenweb.set_sensitive(False)
		elif connection is BtSyncStatus.CONNECTING:
			self.frame = -1
			self.transferring = False
			self.ind.set_from_icon_name('btsync-gui-connecting')
			self.menudebug.set_sensitive(False)
			self.menudebug.set_active(self.agent.get_debug())
			self.menuopenapp.set_sensitive(False)
			self.menuopenweb.set_sensitive(False)
		elif connection is BtSyncStatus.PAUSED:
			self.frame = -1
			self.transferring = False
			self.ind.set_from_icon_name('btsync-gui-paused')
			self.menudebug.set_sensitive(self.agent.is_local())
			self.menudebug.set_active(self.agent.get_debug())
			self.menuopenapp.set_sensitive(False)
			self.menuopenweb.set_sensitive(False)
		else:
			self.menudebug.set_sensitive(self.agent.is_local())
			self.menudebug.set_active(self.agent.get_debug())
			self.menuopenapp.set_sensitive(True)
			self.menuopenweb.set_sensitive(True)
			if transferring and not self.transferring:
				if not self.rotating:
					# initialize animation
					self.transferring = True
					self.frame = 0
					self.animator_id = GObject.timeout_add(200, self.onIconRotate)
			self.transferring = transferring
			if not self.transferring:
				self.ind.set_from_icon_name('btsync-gui-0')
		self.connection = connection

	def show_status(self,statustext):
		self.menustatus.set_label(statustext)

	def is_connected(self):
		return self.connection is BtSyncStatus.CONNECTED

	def onActivate(self,widget):
#		self.menu.popup(None,None,Gtk.StatusIcon.position_menu,widget,3,0)
		if self.is_connected():
			self.open_app()

	def onAbout(self,widget):
		self.about.set_version(_('Version {0} ({0})').format(self.btsyncver['version']))
		self.about.set_comments(_('Linux UI Version {0}').format(VERSION))
		self.about.show()
		self.about.run()
		self.about.hide()

	def onOpenApp(self,widget):
		self.open_app()

	def onOpenWeb(self,widget):
		webbrowser.open('http://{0}:{1}@{2}:{3}'.format(
			urllib.quote(self.agent.get_username(),''),
			urllib.quote(self.agent.get_password(),''),
			self.agent.get_host(),
			self.agent.get_port()
		), 2)

	def onDeleteApp(self, *args):
		self.close_app(False)

	def onSendFeedback(self,widget):
		webbrowser.open(
			'http://forum.bittorrent.com/topic/28106-linux-desktop-gui-unofficial-packages-for-bittorrent-sync/',
			2
		)

	def onOpenManual(self,widget):
		os.system('xdg-open "/usr/share/doc/btsync-common/BitTorrentSyncUserGuide.pdf.gz"')

	def onTogglePause(self,widget):
		if widget.get_active() and not self.agent.is_paused():
			logging.info('Suspending agent...')
			self.close_app();
			self.set_status(BtSyncStatus.PAUSED)
			self.agent.suspend()
		elif not widget.get_active() and self.agent.is_paused():
			logging.info('Resuming agent...')
			self.set_status(BtSyncStatus.CONNECTING)
			self.agent.resume()
			self.connect_id = GObject.timeout_add(1000, self.btsync_connect)

	def onToggleLogging(self,widget):
		if self.is_connected():
			if widget.get_active() and not self.agent.get_debug():
				logging.info('Activate logging...')
				self.agent.set_debug(True)
			elif not widget.get_active() and self.agent.get_debug():
				logging.info('Disable logging...')
				self.agent.set_debug(False)

	def onQuit(self,widget):
		Gtk.main_quit()

	def onIconRotate(self):
		if self.frame == -1:
			# immediate stop
			self.frame = 0
			self.rotating = False
			self.animator_id = None
			return False
		elif not self.transferring and self.frame % 12 == 0:
			# do not stop immediately - wait for the
			# cycle to finish.
			self.ind.set_from_icon_name('btsync-gui-0')
			self.rotating = False
			self.frame = 0
			self.animator_id = None
			return False
		else:
			self.ind.set_from_icon_name('btsync-gui-{0}'.format(self.frame % 12))
			self.rotating = True
			self.frame += 1
			return True

	def onConnectionError(self):
		self.set_status(BtSyncStatus.DISCONNECTED)
		self.menustatus.set_label(_('Disconnected'))
		self.close_app();
		logging.info('BtSync API Connection Error')
		if self.agent.is_auto() and not self.agent.is_running():
			logging.warning('BitTorrent Sync seems to be crashed. Restarting...')
			self.agent.start_agent()
			self.connect_id = GObject.timeout_add(1000, self.btsync_connect)
		else:
			self.connect_id = GObject.timeout_add(5000, self.btsync_connect)
		return False

	def onCommunicationError(self):
		self.set_status(BtSyncStatus.DISCONNECTED)
		self.menustatus.set_label(_('Disconnected: Communication Error {0}').format(self.agent.get_status_code()))
		self.close_app();
		logging.warning('BtSync API HTTP error: {0}'.format(self.agent.get_status_code()))
		self.connect_id = GObject.timeout_add(5000, self.btsync_connect)
		return False



########NEW FILE########
__FILENAME__ = btsyncutils
# coding=utf-8
#
# Copyright 2014 Leo Moll
#
# Authors: Leo Moll and Contributors (see CREDITS)
#
# Thanks to Mark Johnson for btsyncindicator.py which gave me the
# last nudge needed to learn python and write my first linux gui
# application. Thank you!
#
# This file is part of btsync-gui. btsync-gui is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import os
import time
import gettext
import logging
import exceptions

from gettext import gettext as _
from gi.repository import Gtk, GObject

class BtValueDescriptor(GObject.GObject):

	def __init__(self, Name, Type, Value, Default='', Min=None, Max=None, Allowed=None, Forbidden=None, Advanced=True):
		GObject.GObject.__init__(self)
		self.Name		= Name
		self.Type		= Type
		self.Value		= Value
		self.Default	= Default
		self.Min		= Min
		self.Max		= Max
		self.Allowed	= Allowed
		self.Forbidden	= Forbidden
		self.Advanced	= Advanced
		if self.Type == 'n' and self.Allowed is None:
			self.Allowed = '0123456789'
			if str(self.Value)[0:1] == '*':	# remove these stupid "I'm not a default value!"-stars from data
				self.Value = str(self.Value)[1:]
		elif self.Type == 'i' and self.Allowed is None:
			self.Allowed = '-0123456789'
			if str(self.Value)[0:1] == '*':	# remove these stupid "I'm not a default value!"-stars from data
				self.Value = str(self.Value)[1:]
		elif self.Type == 's' and self.Forbidden is None:
			self.Forbidden = '\'"'

	def is_changed(self,value):
		return self.Value != value

	def is_default(self,value):
		return False if self.Default is None else str(self.Default) == str(value)

	def set_default(self):
		self.Value = self.Default

	def get_display_width(self,value):
		return 400 if self.is_default(value) else 900

	def test_value(self,value):
		# boundary checks
		if self.Type == 'n' or self.Type == 'i':
			# default is always OK
			if self.Default is not None and self._to_num(self.Default) == self._to_num(value):
				return True
			# test minimum value
			if self.Min is not None and self._to_num(value) < self._to_num(self.Min):
				return False
			# test maximum value
			if self.Max is not None and self._to_num(value) > self._to_num(self.Max):
				return False
			return True
		elif self.Type == 's':
			# default is always OK
			if self.Default is not None and str(self.Default) == str(value):
				return True
			# test minimum length
			if self.Min is not None and len(newValue) < self._to_num(self.Min):
				return False
			# test maximum length
			if self.Max is not None and len(newValue) > self._to_num(self.Max):
				return False
		return True

	def filter_value(self,value):
		newValue = value
		# eliminate non allowed characters
		if self.Forbidden is not None:
			newValue = newValue.strip(self.Forbidden)
		if self.Allowed is not None:
			stripMask = newValue.strip(self.Allowed)
			newValue = newValue.strip(stripMask)
		return newValue

	@staticmethod
	def new_from(Name,Value=None):
		"""
		This method returns for the specified preferences key a
		suitable BtValueDescriptor
		"""
		return {
		'device_name'						: BtValueDescriptor (Name, 's', Value, Advanced = False), 
		'disk_low_priority'					: BtValueDescriptor (Name, 'b', Value, 1),
		'download_limit'					: BtValueDescriptor (Name, 'n', Value, 0, 0, 1000000, Advanced = False),
		'external_port'						: BtValueDescriptor (Name, 'n', Value, 0, 0, 65534),
		'folder_rescan_interval'			: BtValueDescriptor (Name, 'n', Value, 600, 10, 999999),
		'lan_encrypt_data'					: BtValueDescriptor (Name, 'b', Value, 1),
		'lan_use_tcp'						: BtValueDescriptor (Name, 'b', Value, 0),
		'lang'								: BtValueDescriptor (Name, 'e', Value, 28261, Advanced = False),
		'listening_port'					: BtValueDescriptor (Name, 'n', Value, 0, 1025, 65534, Advanced = False),
		'log_size'							: BtValueDescriptor (Name, 'n', Value, 10, 10, 999999),
		'max_file_size_diff_for_patching'	: BtValueDescriptor (Name, 'n', Value, 1000, 10, 999999),
		'max_file_size_for_versioning'		: BtValueDescriptor (Name, 'n', Value, 1000, 10, 999999),
		'rate_limit_local_peers'			: BtValueDescriptor (Name, 'b', Value, 0),
		'recv_buf_size'						: BtValueDescriptor (Name, 'n', Value, 5, 1, 100),
		'send_buf_size'						: BtValueDescriptor (Name, 'n', Value, 5, 1, 100),
		'sync_max_time_diff'				: BtValueDescriptor (Name, 'n', Value, 600, 0, 999999),
		'sync_trash_ttl'					: BtValueDescriptor (Name, 'n', Value, 30, 0, 999999),
		'upload_limit'						: BtValueDescriptor (Name, 'n', Value, 0, 0, 1000000, Advanced = False),
		'use_upnp'							: BtValueDescriptor (Name, 'b', Value, 1, Advanced = False),
		}.get(Name,BtValueDescriptor (Name, 'u', Value))

	@staticmethod
	def _to_num(value,default=0):
		try:
			return long(value)
		except exceptions.ValueError:
			return default

class BtInputHelper:
	assoc	= dict()
	locked	= False

	def __init__(self):
		self.assoc = dict()
		self.unlock()

	def lock(self):
		self.locked = True

	def unlock(self):
		self.locked = False

	def is_locked(self):
		return self.locked

	def attach(self,widget,valDesc):
		self.detach(widget)
		if valDesc.Type == 'b':
			widget.set_active(int(valDesc.Value) != 0)
			self.assoc[widget] = [
				widget.connect('notify::active',self.onChangedGtkSwitch,valDesc),
				widget.connect('notify::active',self.onSaveGtkSwitch,valDesc)
			]
		elif valDesc.Type == 's' or valDesc.Type == 'n':
			widget.set_text(str(valDesc.Value))
			self.assoc[widget] = [
				widget.connect('changed',self.onChangedGtkEntry,valDesc),
				widget.connect('icon-release',self.onSaveGtkEntry,valDesc)
			]

	def detach(self,widget):
		if widget in self.assoc:
			widget.disconnect(self.assoc[widget][0])
			widget.disconnect(self.assoc[widget][1])
			del self.assoc[widget]

	def sizeof_fmt(self,num):
		for x in [_('bytes'),_('KB'),_('MB'),_('GB')]:
			if num < 1024.0:
				return "%3.1f %s" % (num, x)
			num /= 1024.0
		return "%3.1f %s" % (num, _('TB'))

	def onChangedGtkSwitch(self,widget,unknown,valDesc):
		return

	def onSaveGtkSwitch(self,widget,unknown,valDesc):
		if not self.is_locked() and valDesc.Type == 'b':
			value = 1 if widget.get_active() else 0
			if self.onSaveEntry(widget,valDesc,value):
				valDesc.Value = value

	def onChangedGtkEntry(self,widget,valDesc):
		if not self.locked:
			self.filterEntryContent(widget,valDesc)
			self.handleEntryChanged(widget,valDesc)

	def onSaveGtkEntry(self,widget,iconposition,event,valDesc):
		if not self.is_locked() and iconposition == Gtk.EntryIconPosition.SECONDARY:
			if valDesc.Type == 'b' or valDesc.Type == 'n' or valDesc.Type == 'i':
				value = int(widget.get_text())
			elif valDesc.Type == 's':
				value = widget.get_text()
			else:
				return # unknown type - will not save
			if valDesc.test_value(value):
				if self.onSaveEntry(widget,valDesc,value):
					valDesc.Value = value
					widget.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, None)
			else:
				self.onInvalidEntry(widget,valDesc,value)

	def onSaveEntry(self,widget,valDesc,value):
		return False

	def onInvalidEntry(self,widget,valDesc,value):
		pass

	def filterEntryContent (self,widget,valDesc):
		value = widget.get_text()
		newValue = str(valDesc.filter_value(value))
		if newValue != value:
			widget.set_text(newValue)

	def handleEntryChanged(self,widget,valDesc):
		if valDesc is not None and str(valDesc.Value) != widget.get_text():
			if valDesc.test_value(widget.get_text()):
				widget.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, 'gtk-save')
			else:
				widget.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, 'gtk-dialog-error')
		else:
			widget.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, None)

## debug stuff
#
#	def _dumpDescriptor(self,valDesc):
#		print "Name:        " + valDesc.Name
#		print "  Type:      " + valDesc.Type
#		print "  Forbidden: " + str(valDesc.Forbidden)
#		print "  Allowed:   " + str(valDesc.Allowed)
#		print "  Min:       " + str(valDesc.Min)
#		print "  Max:       " + str(valDesc.Max)

class BtMessageHelper(object):
	def __init__(self):
		self.msgdlg = None

	def show_message(self,parent,messagetext,messagetype=Gtk.MessageType.INFO):
		self.msgdlg = Gtk.MessageDialog (
			parent,
			Gtk.DialogFlags.DESTROY_WITH_PARENT,
			messagetype,
			Gtk.ButtonsType.CLOSE,
			None
		)
		self.msgdlg.set_markup('<b>BitTorrent Sync</b>')
		self.msgdlg.format_secondary_markup(messagetext)
		self.msgdlg.run()
		self.msgdlg.destroy()
		self.msgdlg = None

	def show_warning(self,parent,messagetext):
		self.show_message(parent,messagetext,Gtk.MessageType.WARNING)

	def show_error(self,messagetext):
		self.show_message(parent,messagetext,Gtk.MessageType.ERROR)

class BtBaseDialog(BtMessageHelper):

	def __init__(self,gladefile,dlgname,addobjects = []):
		BtMessageHelper.__init__(self)
		self.gladefile = gladefile
		self.objects = [ dlgname ]
		self.objects.extend(addobjects)
		self.dlg = None

	def create(self):
		# create the dialog object from builder
		self.builder = Gtk.Builder()
		self.builder.set_translation_domain('btsync-gui')
		self.builder.add_objects_from_file(os.path.dirname(__file__) + '/' + self.gladefile, self.objects)
		self.builder.connect_signals (self)
		self.dlg = self.builder.get_object(self.objects[0])

	def run(self):
		response = 0
		while response >= 0:
			response = self.dlg.run()
		return response

	def response(self,response_id):
		if self.msgdlg is not None:
			self.msgdlg.response(response_id)
		if self.dlg is not None:
			self.dlg.response(response_id)

	def destroy(self):
		self.dlg.destroy()
		self.dlg = None
		del self.builder

	def show_message(self,messagetext,messagetype=Gtk.MessageType.INFO):
		BtMessageHelper.show_message(self,self.dlg,messagetext,messagetype)

	def show_warning(self,messagetext):
		self.show_message(messagetext,Gtk.MessageType.WARNING)

	def show_error(self,messagetext):
		self.show_message(messagetext,Gtk.MessageType.ERROR)


class BtSingleInstanceException(Exception):

	def __init__(self,message):
		self.message = message
	def __str__(self):
		return repr(self.message)

class BtSingleton():

	def __init__(self,lockfilename,processname):
		self.lockfilename = None
		if os.path.isfile(lockfilename):
			pid = self.readpid(lockfilename)
			if pid is not None and os.path.isfile('/proc/{0}/cmdline'.format(pid)):
				args = self.getcmdline(pid)
				for arg in args:
					if processname in arg:
						raise BtSingleInstanceException(_('Only one full btsync-gui can run at once'))
			# lock file must by a zombie...
			os.remove(lockfilename)
		self.writepid(lockfilename)

	def __del__(self):
		# print "preremove:" + str(self.lockfilename)
		if self.lockfilename and os.path.isfile(self.lockfilename):
			# print "remove:" + str(self.lockfilename)
			os.remove(self.lockfilename)

	def readpid(self,lockfilename):
		try:
			f = open(lockfilename, 'r')
			pid = f.readline().rstrip('\r\n')
			f.close()
			return pid
		except IOError:
			return None

	def writepid(self,lockfilename):
		lockdir = os.path.dirname(lockfilename)
		if lockdir and not os.path.isdir(lockdir):
			os.makedirs(lockdir)
		f = open(lockfilename, 'w')
		f.write(str(os.getpid()))
		f.close()
		self.lockfilename = lockfilename

	def getcmdline(self,pid):
		try:
			f = open('/proc/{0}/cmdline'.format(pid), 'r')
			args = f.readline().split('\0')
			args.append('')
			f.close()
			return args
		except IOError:
			return ['']


class BtDynamicTimeout:

	def __init__(self,interval,function):
		self.mini = interval
		self.last = interval
		self.best = interval
		self.func = function
		self.toid = None

	def start(self):
		if self.toid is None:
			self.toid = GObject.timeout_add(self.best, self._tofunc)

	def stop(self):
		if self.toid is not None:
			GObject.source_remove(self.toid)
			self.toid = None

	def _tofunc(self):
		start = time.time()
		result = self.func()
		if not result:
			self.toid = None
			return False
		duration = int((time.time() - start) * 1000)
		if duration < 50:
			self.best = max(1000,self.mini)
		elif duration < 100:
			self.best = max(2000,self.mini)
		elif duration < 500:
			self.best = max(4000,self.mini)
		else:
			self.best = max(duration * 10,self.mini)
		if self.best != self.last:
			logging.debug('Last cycle duration was {0} msec - Adaptive timeout changed to {1} msec to avoid API flooding'.format(duration,self.best))
			self.last = self.best
			self.toid = GObject.timeout_add(self.best, self._tofunc)
			return False
		logging.debug('Last cycle duration was {0} msec'.format(duration))
		return True


########NEW FILE########
__FILENAME__ = dialogs
# coding=utf-8
#
# Copyright 2014 Leo Moll
#
# Authors: Leo Moll and Contributors (see CREDITS)
#
# Thanks to Mark Johnson for btsyncindicator.py which gave me the
# last nudge needed to learn python and write my first linux gui
# application. Thank you!
#
# This file is part of btsync-gui. btsync-gui is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import os
import gettext
import qrencode
import requests

from gettext import gettext as _
from gi.repository import Gtk, Gdk, GdkPixbuf
from cStringIO import StringIO

from btsyncagent import BtSyncAgent
from btsyncutils import BtBaseDialog,BtInputHelper,BtValueDescriptor

class BtSyncFolderRemove(BtBaseDialog):
	def __init__(self):
		BtBaseDialog.__init__(self, 'dialogs.glade', 'removefolder')

class BtSyncFolderAdd(BtBaseDialog):
	def __init__(self,agent):
		BtBaseDialog.__init__(self, 'dialogs.glade', 'addfolder')
		self.folderdlg = None
		self.agent = agent
		self.secret = ''
		self.folder = ''

	def create(self):
		BtBaseDialog.create(self)
		self.secret_w = self.builder.get_object('addfolder_secret')
		self.folder_w = self.builder.get_object('addfolder_folder')
		self.choose_b = self.builder.get_object('addfolder_choose')
		self.choose_b.set_sensitive(self.agent.is_local())

	def run(self):
		while True:
			response = BtBaseDialog.run(self)
			if response == Gtk.ResponseType.CANCEL:
				return response
			elif response == Gtk.ResponseType.DELETE_EVENT:
				return response
			elif response == Gtk.ResponseType.OK:
				self.secret = self.secret_w.get_text()
				self.folder = self.folder_w.get_text()
				# test if secret is OK
				if self.agent.get_error_code(self.agent.get_secrets(self.secret)) > 0:
					self.show_warning(_(
						'This secret is invalid.\nPlease generate a new '\
						'secret or enter your shared folder secret.'
					))
				# test if string is an absolute path and a directory
				elif len(self.folder) == 0 or self.folder[0] != '/' or not os.path.isdir(self.folder):
					self.show_warning(_('Can\'t open the destination folder.'))
				# test if the specified data is unique
				elif self.is_duplicate_folder(self.folder,self.secret):
					self.show_warning(_(
						'Selected folder is already added to BitTorrent Sync.'
					))
				# if btsync agent is local perform more tests
				elif self.agent.is_local():
					# test if the specified directory is readable and writable
					if not os.access(self.folder,os.W_OK) or not os.access(self.folder,os.R_OK):
						self.show_warning(_(
							'Don\'t have permissions to write to the selected folder.'
						))
					else:
						return response
				else:
					return response

	def response(self,result_id):
		if self.folderdlg is not None:
			self.folderdlg.response(result_id)
		BtBaseDialog.response(self,result_id)

	def is_duplicate_folder(self,folder,secret):
		folders = self.agent.get_folders()
		if folders is not None:
			for index, value in enumerate(folders):
				if value['dir'] == folder or value['secret'] == secret:
					return True
		return False;


	def onFolderAddChoose(self,widget):
		self.folderdlg = Gtk.FileChooserDialog (
			_('Please select a folder to sync'),
			self.dlg,
			Gtk.FileChooserAction.SELECT_FOLDER, (
				Gtk.STOCK_CANCEL,
				Gtk.ResponseType.CANCEL,
				Gtk.STOCK_OPEN,
				Gtk.ResponseType.OK
			)
		)
		if self.folderdlg.run() == Gtk.ResponseType.OK:
			self.folder_w.set_text(self.folderdlg.get_filename())
		self.folderdlg.destroy()
		self.folderdlg = None

	def onFolderAddGenerate(self,widget):
		secrets = self.agent.get_secrets()
		self.secret_w.set_text(secrets['read_write'])
		
class BtSyncFolderScanQR(BtBaseDialog):
	def __init__(self,rwsecret,rosecret,basename):
		BtBaseDialog.__init__(self, 'dialogs.glade', 'scanqr')
		self.rwsecret = rwsecret
		self.rosecret = rosecret
		self.basename = basename

	def create(self):
		BtBaseDialog.create(self)
		self.qrcode_image = self.builder.get_object('qrcode_image')
		self.qrcode_fullaccess = self.builder.get_object('qrcode_fullaccess')
		self.qrcode_readaccess = self.builder.get_object('qrcode_readaccess')
		version, size, image = qrencode.encode_scaled(
			'btsync://{0}?n={1}'.format(self.rosecret,self.basename),232
		)
		self.roqrcode = self.image_to_pixbuf(image)

		if self.rwsecret is None:
			self.qrcode_image.set_from_pixbuf(self.roqrcode)
			self.qrcode_readaccess.set_active(True)
			self.qrcode_readaccess.set_sensitive(False)
			self.qrcode_fullaccess.set_sensitive(False)
		else:
			version, size, image = qrencode.encode_scaled(
				'btsync://{0}?n={1}'.format(self.rwsecret,self.basename),232
			)
			self.rwqrcode = self.image_to_pixbuf(image)
			self.qrcode_image.set_from_pixbuf(self.rwqrcode)
			self.qrcode_fullaccess.set_active(True)

	def image_to_pixbuf(self,image):
		filebuf = StringIO()  
		image.save(filebuf, "ppm")  
		contents = filebuf.getvalue()  
		filebuf.close()  
		loader = GdkPixbuf.PixbufLoader.new_with_type("pnm")  
		#height, width = image.size
		#loader.set_size(width.height)
		loader.write(contents)  
		pixbuf = loader.get_pixbuf()  
		loader.close()  
		return pixbuf

	def onToggleFullAccess(self,widget):
		if widget.get_active():
			self.qrcode_image.set_from_pixbuf(self.rwqrcode)

	def onToggleReadOnly(self,widget):
		if widget.get_active():
			self.qrcode_image.set_from_pixbuf(self.roqrcode)


class BtSyncFolderPrefs(BtBaseDialog):
	def __init__(self,agent):
		BtBaseDialog.__init__(self,
			'dialogs.glade',
			'folderprefs', [
				'fp_predefined_hosts',
				'rw_secret_text',
				'ro_secret_text',
				'en_secret_text',
				'ot_secret_text'
			]
		)
		self.agent = agent
		self.hostdlg = None
		self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

	def create(self,folder,secret):
		BtBaseDialog.create(self)
		# compute secrets
		result = self.agent.get_secrets(secret)
		self.idfolder = folder
		self.idsecret = secret
		self.rwsecret = result['read_write'] if result.has_key('read_write') else None
		self.rosecret = result['read_only'] if result.has_key('read_only') else None
		self.ensecret = result['encryption'] if result.has_key('encryption') else None
		# load values
		result = self.agent.get_folder_prefs(self.idsecret)
		# initialize OK button
		self.fp_button_ok = self.builder.get_object('fp_button_ok')
		# secrets page
		self.rw_secret = self.builder.get_object('rw_secret')
		self.rw_secret_text	= self.builder.get_object('rw_secret_text')
		self.rw_secret_copy	= self.builder.get_object('rw_secret_copy')
		self.rw_secret_new	= self.builder.get_object('rw_secret_new')

		self.ro_secret = self.builder.get_object('ro_secret')
		self.ro_secret_text = self.builder.get_object('ro_secret_text')
		self.ro_secret_copy = self.builder.get_object('ro_secret_copy')
		self.ro_restore	= self.builder.get_object('ro_restore')
		self.ro_restore_label	= self.builder.get_object('ro_restore_label')

		self.en_secret = self.builder.get_object('en_secret')
		self.en_secret_text = self.builder.get_object('en_secret_text')
		self.en_secret_copy = self.builder.get_object('en_secret_copy')

		self.ot_secret = self.builder.get_object('ot_secret')
		self.ot_secret_text = self.builder.get_object('ot_secret_text')
		self.ot_secret_copy = self.builder.get_object('ot_secret_copy')
		self.ot_secret_new	= self.builder.get_object('ot_secret_new')

		# secrets page - values
		self.ro_restore.set_active(self.agent.get_safe_result(result,'overwrite_changes',0) != 0)
		if self.ensecret is None:
			self.hide_en_secret()
		else:
			self.en_secret_text.set_text(str(self.ensecret))
		if self.rosecret is None:
			self.hide_ro_secret()
			self.hide_ot_secret()
			self.ro_restore.hide()
		else:
			self.ro_secret_text.set_text(str(self.rosecret))
		if self.rwsecret is None:
			self.hide_rw_secret()
		else:
			self.rw_secret_text.set_text(str(self.rwsecret))
			self.ro_restore.hide()
			self.ro_restore_label.hide()
		# prefs page
		self.fp_use_relay = self.builder.get_object('fp_use_relay')
		self.fp_use_tracker = self.builder.get_object('fp_use_tracker')
		self.fp_search_lan = self.builder.get_object('fp_search_lan')
		self.fp_use_dht = self.builder.get_object('fp_use_dht')
		self.fp_use_syncarchive = self.builder.get_object('fp_use_syncarchive')
		self.fp_use_predefined = self.builder.get_object('fp_use_predefined')
		self.fp_predefined_tree = self.builder.get_object('fp_predefined_tree')
		self.fp_predefined_hosts = self.builder.get_object('fp_predefined_hosts')
		self.fp_predefined_selection = self.builder.get_object('fp_predefined_selection')
		self.fp_predefined_add = self.builder.get_object('fp_predefined_add')
		self.fp_predefined_remove = self.builder.get_object('fp_predefined_remove')
		self.fp_predefined_label = self.builder.get_object('fp_predefined_label')
		# prefs page - values
		self.disable_hosts()
		self.fp_use_relay.set_active(self.agent.get_safe_result(result,'use_relay_server',0) != 0)
		self.fp_use_tracker.set_active(self.agent.get_safe_result(result,'use_tracker',0) != 0)
		self.fp_search_lan.set_active(self.agent.get_safe_result(result,'search_lan',0) != 0)
		self.fp_use_dht.set_active(self.agent.get_safe_result(result,'use_dht',0) != 0)
		self.fp_use_syncarchive.set_active(self.agent.get_safe_result(result,'use_sync_trash',0) != 0)
		self.fp_use_predefined.set_active(self.agent.get_safe_result(result,'use_hosts',0) != 0)
		# fill the list of predefined hosts...
		result = self.agent.get_folder_hosts(self.idsecret)
		if self.agent.get_error_code(result) == 0:
			hosts = result.get('hosts', [])
			for index, value in enumerate(hosts):
				self.fp_predefined_hosts.append ([ value ])

		# nothing is changed now
		self.fp_button_ok.set_sensitive(False)

	def response(self,result_id):
		if self.hostdlg is not None:
			self.hostdlg.response(result_id)
		BtBaseDialog.response(self,result_id)

	def hide_rw_secret(self):
		self.rw_secret.set_sensitive(False)
		self.rw_secret_new.set_sensitive(False)
		self.rw_secret_copy.set_sensitive(False)
		self.builder.get_object('rw_secret_label').hide()
		self.builder.get_object('rw_secret_scroll').hide()
		self.builder.get_object('rw_secret_box').hide()

	def hide_ro_secret(self):
		self.ro_secret.set_sensitive(False)
		self.ro_secret_copy.set_sensitive(False)
		self.builder.get_object('ro_secret_label').hide()
		self.builder.get_object('ro_secret_scroll').hide()
		self.builder.get_object('ro_secret_box').hide()

	def hide_en_secret(self):
		self.en_secret.set_sensitive(False)
		self.en_secret_copy.set_sensitive(False)
		self.builder.get_object('en_secret_label').hide()
		self.builder.get_object('en_secret_scroll').hide()
		self.builder.get_object('en_secret_box').hide()

	def show_en_secret(self):
		self.en_secret.set_sensitive(True)
		self.en_secret_copy.set_sensitive(True)
		self.builder.get_object('en_secret_label').show()
		self.builder.get_object('en_secret_scroll').show()
		self.builder.get_object('en_secret_box').show()

	def hide_ot_secret(self):
		self.ot_secret.set_sensitive(False)
		self.ot_secret_new.set_sensitive(False)
		self.ot_secret_copy.set_sensitive(False)
		self.builder.get_object('ot_secret_label').hide()
		self.builder.get_object('ot_secret_scroll').hide()
		self.builder.get_object('ot_secret_box').hide()
		self.builder.get_object('ot_secret_buttonbox').hide()
		self.builder.get_object('ot_secret_info').hide()

	def disable_hosts(self):
		self.fp_predefined_tree.set_sensitive(False)
		self.fp_predefined_add.set_sensitive(False)
		self.fp_predefined_remove.set_sensitive(False)
		self.fp_predefined_label.set_sensitive(False)

	def enable_hosts(self):
		self.fp_predefined_tree.set_sensitive(True)
		self.fp_predefined_add.set_sensitive(True)
		self.fp_predefined_remove.set_sensitive(self.fp_predefined_selection.count_selected_rows() > 0)
		self.fp_predefined_label.set_sensitive(True)

	def save_prefs(self):
		hosts_list = []
		for row in self.fp_predefined_hosts:
			hosts_list.append(row[0])
		self.agent.set_folder_hosts(self.idsecret,hosts_list)
		prefs = {}
		prefs['overwrite_changes'] = 1 if self.ro_restore.get_active() else 0
		prefs['use_relay_server'] = 1 if self.fp_use_relay.get_active() else 0
		prefs['use_tracker'] = 1 if self.fp_use_tracker.get_active() else 0
		prefs['search_lan'] = 1 if self.fp_search_lan.get_active() else 0
		prefs['use_dht'] = 1 if self.fp_use_dht.get_active() else 0
		prefs['use_sync_trash'] = 1 if self.fp_use_syncarchive.get_active() else 0
		prefs['use_hosts'] = 1 if self.fp_use_predefined.get_active() and len(hosts_list) > 0 else 0
		result = self.agent.set_folder_prefs(self.idsecret,prefs)
		return self.agent.get_error_code(result) == 0

	def onRwSecretCopy(self,widget):
		text = self.rw_secret_text.get_text(*self.rw_secret_text.get_bounds(),include_hidden_chars=False)
		self.clipboard.set_text(text, -1)

	def onRwSecretNew(self,widget):
		result = self.agent.get_secrets()
		self.rw_secret_text.set_text(str(result['read_write']))
		# everything is now done by onSecretChanged
		# self.rwsecret = result['read_write']
		# self.rosecret = result['read_only']
		# self.rw_secret_text.set_text(str(self.rwsecret))
		# self.ro_secret_text.set_text(str(self.rosecret))

	def onRoSecretCopy(self,widget):
		text = self.ro_secret_text.get_text(*self.ro_secret_text.get_bounds(),include_hidden_chars=False)
		self.clipboard.set_text(text, -1)

	def onEnSecretCopy(self,widget):
		text = self.en_secret_text.get_text(*self.en_secret_text.get_bounds(),include_hidden_chars=False)
		self.clipboard.set_text(text, -1)

	def onOtSecretCopy(self,widget):
		text = self.ot_secret_text.get_text(*self.ot_secret_text.get_bounds(),include_hidden_chars=False)
		self.clipboard.set_text(text, -1)

	def onOtSecretNew(self,widget):
		# not implemented
		pass

	def onChanged(self,widget):
		self.fp_button_ok.set_sensitive(True)

	def onSecretChanged(self,textbuffer):
		text = self.rw_secret_text.get_text(*self.rw_secret_text.get_bounds(),include_hidden_chars=False)
		if text != self.rwsecret:
			result = self.agent.get_secrets(text,throw_exceptions=False)
			if self.agent.get_error_code(result) == 0:
				if result.has_key('read_only'):
					self.ro_secret_text.set_text(str(result['read_only']))
				else:
					self.ro_secret_text.set_text('')
				if result.has_key('encryption'):
					self.show_en_secret()
					self.en_secret_text.set_text(str(result['encryption']))
				else:
					self.hide_en_secret()
					self.en_secret_text.set_text('')
				self.onChanged(None)

	def onPredefinedToggle(self,widget):
		self.onChanged(None)
		if widget.get_active():
			self.enable_hosts()
		else:
			self.disable_hosts()

	def onPredefinedSelectionChanged(self,selection):
		self.fp_predefined_remove.set_sensitive(selection.count_selected_rows() > 0)

	def onPredefinedAdd(self,widget):
		self.hostdlg = BtSyncHostAdd()
		self.hostdlg.create()
		if self.hostdlg.run() == Gtk.ResponseType.OK:
			self.fp_predefined_hosts.append ([ '{0}:{1}'.format(
				self.hostdlg.addr,
				self.hostdlg.port
			) ])
			self.onChanged(None)
		self.hostdlg.destroy()
		self.hostdlg = None

	def onPredefinedRemove(self,widget):
		model, tree_iter = self.fp_predefined_selection.get_selected()
		if tree_iter is not None:
			model.remove(tree_iter)
			self.onChanged(None)

	def onOK(self,widget):
		if self.rwsecret is not None:
			text = self.rw_secret_text.get_text(*self.rw_secret_text.get_bounds(),include_hidden_chars=False)
			if len(text) != 33 and len(text) < 40:
				self.show_error(_(
					'Invalid secret specified.\n'\
					'Secret must have a length of 33 characters'
				))
				self.dlg.response(0)
				return False
			result = self.agent.get_secrets(text,throw_exceptions=False)
			if self.agent.get_error_code(result) != 0:
				self.show_error(_(
					'Invalid secret specified.\n'\
					'Secret must contain only alphanumeric characters'
				))
				self.dlg.response(0)
				return False
			elif self.rwsecret != text:
				# the only way I know to change the secret is
				# to delete the folder and recreate it...
				# As we say in Germany: "Augen zu und durch!"
				# If we fail, we are f*****
				result = self.agent.remove_folder(self.rwsecret)
				result = self.agent.add_folder(self.idfolder,text)
				self.idsecret = text
				self.save_prefs()
				return True

		return self.save_prefs()

class BtSyncHostAdd(BtBaseDialog):
	def __init__(self):
		BtBaseDialog.__init__(self, 'dialogs.glade', 'newhost')
		self.addr = ''
		self.port = ''

	def create(self):
		BtBaseDialog.create(self)
		self.dlg.add_buttons(
			Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_OK, Gtk.ResponseType.OK
		)
		self.addr_w = self.builder.get_object('ph_addr')
		self.port_w = self.builder.get_object('ph_port')

	def run(self):
		self.dlg.set_default_response(Gtk.ResponseType.OK)
		while True:
			response = BtBaseDialog.run(self)
			if response == Gtk.ResponseType.CANCEL:
				return response
			elif response == Gtk.ResponseType.DELETE_EVENT:
				return response
			elif response == Gtk.ResponseType.OK:
				self.addr = self.addr_w.get_text()
				self.port = self.port_w.get_text()
				# test if a hostname is specified
				if len(self.addr) == 0:
					self.show_warning(_(
						'A hostname or IP address must be specified'
					))
				# test if port is OK
				elif len(self.port) == 0 or int(self.port) < 1 or int(self.port) > 65534:
					self.show_warning(_(
						'The specified port must be a number between 1 and 65534'
					))
				else:
					return response

class BtSyncPrefsAdvanced(BtBaseDialog,BtInputHelper):

	def __init__(self,agent):
		BtBaseDialog.__init__(self,
			'dialogs.glade',
			'prefsadvanced', [
				'advancedprefs'
			]
		)
		BtInputHelper.__init__(self)
		self.agent = agent
		self.prefs = self.agent.get_prefs()
		self.create()

	def create(self):
		BtBaseDialog.create(self)
		# get the editing widgets
		self.advancedprefs = self.builder.get_object('advancedprefs')
		self.ap_tree_prefs = self.builder.get_object('ap_tree_prefs')
		self.ap_label_value = self.builder.get_object('ap_label_value')
		self.ap_switch_value = self.builder.get_object('ap_switch_value')
		self.ap_entry_value = self.builder.get_object('ap_entry_value')
		self.ap_reset_value = self.builder.get_object('ap_reset_value')
		# initialize content
		self.init_editor()
		self.init_values()

	def init_values(self):
		self.lock()
		# fill with current values and specifications
		self.advancedprefs.clear()
		for key, value in self.prefs.items():
			valDesc = BtValueDescriptor.new_from(key,value)
			if valDesc.Advanced:
				self.advancedprefs.append([
					str(key), str(value),
					400 if valDesc.is_default(value) else 900,
					valDesc
				]);
		self.unlock()

	def init_editor(self,valDesc=None):
		self.lock()
		if valDesc == None:
			self.detach(self.ap_entry_value)
			self.detach(self.ap_switch_value)
			self.ap_label_value.hide()
			self.ap_switch_value.hide()
			self.ap_entry_value.hide()
			self.ap_reset_value.hide()
		else:
			if valDesc.Type == 'b':
				self.attach(self.ap_switch_value,valDesc)
				self.ap_label_value.show()
				self.ap_switch_value.show()
				self.ap_entry_value.hide()
				self.ap_reset_value.show()
			elif valDesc.Type == 'n' or valDesc.Type == 's':
				self.attach(self.ap_entry_value,valDesc)
				self.ap_label_value.show()
				self.ap_switch_value.hide()
				self.ap_entry_value.show()
				self.ap_reset_value.show()
			else:
				self.ap_label_value.hide()
				self.ap_switch_value.hide()
				self.ap_entry_value.hide()
				self.ap_reset_value.hide()
		self.unlock()

	def onSelectionChanged(self,selection):
		model, tree_iter = selection.get_selected()
		self.init_editor(None if tree_iter is None else model[tree_iter][3])

	def onSaveEntry(self,widget,valDesc,newValue):
		try:
			self.agent.set_prefs({valDesc.Name : newValue})
			# GtkListStore has no search function. BAD!!! Maybe I'm too stupid?
			for row in self.advancedprefs:
				if row[0] == valDesc.Name:
					row[1] = str(newValue)
					row[2] = valDesc.get_display_width(newValue)
			return True
		except requests.exceptions.ConnectionError:
			return self.onConnectionError()
		except requests.exceptions.HTTPError:
			return self.onCommunicationError()

	def onPrefsAdvancedResetValue(self,widget):
		selection = self.ap_tree_prefs.get_selection()
		model, tree_iter = selection.get_selected()
		if tree_iter is not None:
			# reset to default
			valDesc = model[tree_iter][3]
			self.onSaveEntry(widget,valDesc,valDesc.Default)
			valDesc.set_default()
			self.init_editor(valDesc)

	def onConnectionError(self):
		self.response(Gtk.ResponseType.CANCEL)
		self.dlg.destroy()

	def onCommunicationError(self):
		self.response(Gtk.ResponseType.CANCEL)
		self.dlg.destroy()



########NEW FILE########
__FILENAME__ = trayindicator
# coding=utf-8
#
# Copyright 2014 Leo Moll
#
# Authors: Leo Moll and Contributors (see CREDITS)
#
# Thanks to Mark Johnson for btsyncindicator.py which gave me the
# last nudge needed to learn python and write my first linux gui
# application. Thank you!
#
# This file is part of btsync-gui. btsync-gui is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import logging

from gi.repository import Gtk, GObject

try:
	from gi.repository import AppIndicator3 as AppIndicator
except ImportError:
	logging.warning('Ignore the previous error: using Gtk.TrayIcon instead. Everything is fine!') 

class TrayIndicator:
	"""
	This class provides an abstraction of application indicator functionality
	based Gtk.StatusIcon or libindicator3 if the distribution/desktop requires
	it (like Ubuntu with Unity)

	The bindings to libindicator3 are provided by installing the package
	gir1.2-appindicator3-0.1 - the package python-appindicator unfortunately
	provides only PyGtk bindings for Gtk2
	"""
	def __init__(self,name,icon_name,attention_icon_name=None):
		try:
			self.indicator = AppIndicator.Indicator.new (
				name,
				icon_name,
				AppIndicator.IndicatorCategory.APPLICATION_STATUS
			)
			if attention_icon_name is None:
				self.indicator.set_attention_icon(icon_name)
			else:
				self.indicator.set_attention_icon(attention_icon_name)
			self.indicator.set_status (AppIndicator.IndicatorStatus.ACTIVE)
			self.statusicn = None
		except NameError:
			self.statusicn = Gtk.StatusIcon()
			self.statusicn.set_name(name)
			self.statusicn.set_from_icon_name(icon_name)
			self.indicator = None
			
	def set_title(self,title):
		if self.indicator is None:
			self.statusicn.set_title(title)

	def	set_tooltip_text(self,text):
		if self.indicator is None:
			self.statusicn.set_tooltip_text(text)

	def set_from_icon_name(self,icon_name):
		if self.indicator is None:
			self.statusicn.set_from_icon_name(icon_name)
		else:
			self.indicator.set_icon(icon_name)

	def set_menu(self,menu):
		self.menu = menu
		if self.indicator is None:
			self.menu = menu
			self.statusicn.connect('popup-menu', self.onContextMenu)
		else:
			self.indicator.set_menu(self.menu)

	def set_default_action(self,handler):
		if self.indicator is None:
			self.statusicn.connect('activate', handler)


	def onContextMenu(self,widget,button,activate_time):
		self.menu.popup(None,None,Gtk.StatusIcon.position_menu,widget,button,activate_time)


########NEW FILE########
__FILENAME__ = btsyncindicator
#!/usr/bin/env python
# coding=utf-8
#
# Copyright 2013 Mark Johnson
#
# Authors: Mark Johnson and Contributors (see CREDITS)
#
# Based on the PyGTK Application Indicators example by Jono Bacon
# and Neil Jagdish Patel
# http://developer.ubuntu.com/resources/technologies/application-indicators/
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the applicable version of the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License version 3 along with this program.  If not, see
# <http://www.gnu.org/licenses/>
#
import gobject
import gtk
import appindicator

import urllib

"""
    Requests is not installed by default
    If it's missing, display instructions to install with apt or pip
"""
try:
    import requests
except ImportError:
    print "requests library not found."
    print "To install, try:"
    print "sudo apt-get install python-requests"
    print "If python-requests isn't found, try:"
    print "sudo apt-get install python-pip && sudo pip install requests"
    print "If apt-get isn't available, use your system's package manager or install pip manually:"
    print "http://www.pip-installer.org/en/latest/installing.html"
    exit(1)

import time
import sys
import re
import json
import os
import argparse
import webbrowser
import logging
import subprocess
from contextlib import contextmanager

VERSION = '0.15'
TIMEOUT = 2 # seconds

@contextmanager
def file_lock(lock_file):
    runningpids = subprocess.check_output("ps aux | grep btsyncindicator | grep -v grep | awk '{print $2}'", shell=True).split()
    if os.path.exists(lock_file):
        # is it a zombie?
        f = open(lock_file, 'r')
        pid = f.read()
        f.close()
        if pid not in runningpids:
            os.remove(lock_file)
        else:
            print 'Only one indicator can run at once. '\
                  'Indicator is locked with %s' % lock_file
            sys.exit(-1)

    open(lock_file, 'w').write(str(os.getpid()))
    try:
        yield
    finally:
        os.remove(lock_file)


class BtSyncConfig:
    def __init__(self):
        self.load_config()

    def load_config(self):
        """
        Open the config file specified in args load into self.config
	Removes commented lines starting in //, or multi-line comments
	wrapped in /* */
        """
        logging.info('Opening config file '+args.config)
        config = ""
        for line in open(args.config, 'r'):
            if line.find('//') == -1:
                config += line
        config = re.sub("/\*(.|[\r\n])*?\*/", "", config)
        self.config = json.loads(config)
        logging.info('Config loaded')


class BtSyncIndicator:
    def __init__(self,btconf):
        """
        Initialise the indicator, load the config file,
        intialise some properties and set up the basic
        menu
        """

        self.ind = appindicator.Indicator ("btsync-indicator",
                                          "btsync",
                                          appindicator.CATEGORY_APPLICATION_STATUS,
                                          args.iconpath)
        self.ind.set_status (appindicator.STATUS_ACTIVE)
        self.ind.set_attention_icon ("btsync-attention")

        self.config = btconf.config
        self.detect_btsync_user()
        
        if 'login' in self.config['webui']:
            login = self.config['webui']['login']
            password = self.config['webui']['password']
            self.webui = 'http://'+login+':'+password+'@'+self.config['webui']['listen'] if self.btsync_user else 'http://'+self.config['webui']['listen']
            self.auth = (login, password)
        else:
            self.webui = 'http://'+self.config['webui']['listen']
            self.auth = None

        self.urlroot = 'http://'+self.config['webui']['listen']+'/gui/'
        self.folderitems = {}
        self.info = {}
        self.clipboard = gtk.Clipboard()
        self.animate = None
        self.error_item = None
        self.frame = 0
        self.status = None
        self.count = 0

        self.menu_setup()
        self.ind.set_menu(self.menu)

    def detect_btsync_user(self):
        # If we have dpkg in $PATH, Determine whether the script was installed with 
	# the btsync-user package if it is, we can use the packages btsync management
	# scripts for some extra features
        try:
            have_dpkg = False
            for p in os.environ["PATH"].split(os.pathsep):
                if os.path.exists(os.path.join(p, 'dpkg')):
                    have_dpkg = True

            if have_dpkg:
                output = subprocess.check_output(["dpkg", "-S", os.path.abspath(__file__)])
            else:
                output = ""

            if (output.find("btsync-user") > -1):
                self.btsync_user = True
            else:
                self.btsync_user = False
        except subprocess.CalledProcessError, e:
            self.btsync_user = False
        return self.btsync_user

    def menu_setup(self):
        """
        Create the menu with some basic items
        """
        logging.info('Creating menu')
        # create a menu
        self.menu = gtk.Menu()

        self.sep1 = gtk.SeparatorMenuItem()
        self.sep1.show()
        self.menu.append(self.sep1)

        if self.btsync_user:
            filepath = self.config['storage_path']+'/paused'
            self.pause_item = gtk.CheckMenuItem("Pause Syncing")
            self.pause_item.set_active(os.path.isfile(filepath))
            self.pause_item_handler = self.pause_item.connect("activate", self.toggle_pause)
            self.pause_item.show()
            self.menu.append(self.pause_item)

	self.webui_item = gtk.MenuItem("Open Web Interface")
	self.webui_item.connect("activate", self.open_webui)
	self.webui_item.show()
	self.menu.append(self.webui_item)
                    
        self.sep2 = gtk.SeparatorMenuItem()
        self.sep2.show()
        self.menu.append(self.sep2)

        filepath = self.config['storage_path']+'/debug.txt'
	self.debug_item = gtk.CheckMenuItem("Enable Debug Logging")
	self.debug_item.set_active(os.path.isfile(filepath))
	self.debug_item_handler = self.debug_item.connect("activate", self.toggle_debugging)
	self.debug_item.show()
	self.menu.append(self.debug_item)

        if self.btsync_user:
            buf = "Quit BitTorrent Sync"
        else:
            buf = "Quit"
        self.quit_item = gtk.MenuItem(buf)
        self.quit_item.connect("activate", self.quit)
        self.quit_item.show()
        self.menu.append(self.quit_item)
        logging.info('Menu initalisation complete')

    def setup_session(self):
        """
        Attempt to setup the session with the btsync server
        * Calls token.html, stores the token and cookie
        * Calls various actions called by the web interface on init and stores results
        * Initialises check_status loop
        If the server cannot be contacted, waits 5 seconds and retries.
        """
        if self.btsync_user:
            filepath = self.config['storage_path']+'/paused'
            if (os.path.isfile(filepath)):
                logging.info('BitTorrent Sync is paused. Skipping session setup')
                self.show_error("BitTorrent Sync is paused")
                return True

        try:
            tokenparams = {'t': time.time()}
            tokenurl = self.urlroot+'token.html'
            logging.info('Requesting Token from ' + tokenurl)
            response = requests.post(tokenurl, params=tokenparams, auth=self.auth)
            response.raise_for_status()
            logging.info('Token response ' + str(response))
            regex = re.compile("<html><div[^>]+>([^<]+)</div></html>")
            html = self.get_response_text(response)
            logging.info('HTML Response ' + html)
            r = regex.search(html)
            self.token = r.group(1)
            self.cookies = response.cookies
            logging.info('Token '+self.token+' Retrieved')

            actions = [
                  'license', 
                  'getostype', 
                  'getsettings', 
                  'getversion', 
                  'getdir', 
                  'checknewversion', 
                  'getuserlang', 
                  'iswebuilanguageset']


            for a in actions:
               params = {'token': self.token, 'action': a}
               response = requests.get(self.urlroot, params=params, cookies=self.cookies, auth=self.auth)
               response.raise_for_status()
               self.info[a] = self.get_response_json(response)

            self.clear_error()

            logging.info('Session setup complete, initialising check_status loop')

            self.status = { 'folders': [] }

            gtk.timeout_add(TIMEOUT * 1000, self.check_status)
            return False

        except requests.exceptions.ConnectionError:
            logging.warning('Connection Error caught, displaying error message')
            self.show_error("Couldn't connect to Bittorrent Sync at "+self.urlroot)
            return True
        except requests.exceptions.HTTPError:
            logging.warning('Communication Error caught, displaying error message')
            self.show_error("Communication Error "+str(response.status_code))
            return True

    def check_status(self):
        """
        Gets the current status of btsync and updates the menu accordingly
        Shows each shared folder with connected peer and any transfer activity 
        with it.  Also retrieves the secrets for each folder.
        If the server cannot be contacted, stops polling and attempts calls setup_session
        to establish a new session.
        """
        """
        Since some state information from the btsync-agent may be changed from outside,
        we should keep it also up to date in the menu...
        """
        filepath = self.config['storage_path']+'/debug.txt'
        self.debug_item.disconnect(self.debug_item_handler)
	self.debug_item.set_active(os.path.isfile(filepath))
	self.debug_item_handler = self.debug_item.connect("activate", self.toggle_debugging)

	if self.btsync_user:
            filepath = self.config['storage_path']+'/paused'
            self.pause_item.disconnect(self.pause_item_handler)
            self.pause_item.set_active(os.path.isfile(filepath))
            self.pause_item_handler = self.pause_item.connect("activate", self.toggle_pause)
            if (os.path.isfile(filepath)):
                logging.info('BitTorrent Sync is paused. Cleaning menu')
                self.show_error("BitTorrent Sync is paused")
                self.folderitems = {}
                self.status = { 'folders': [] }
                gtk.timeout_add(5000, self.setup_session)
                return False

        try:
            logging.info('Requesting status')
            params = {'token': self.token, 'action': 'getsyncfolders'}
            response = requests.get(self.urlroot, params=params, cookies=self.cookies, auth=self.auth)
            response.raise_for_status()

            self.clear_error()

            status = self.get_response_json(response)

            for folder in status['folders']:
               folder['name'] = self.fix_encoding(folder['name'])
               for peer in folder['peers']:
                   peer['status'] = self.fix_encoding(peer['status'])

            self.check_activity(status['folders'])

            curfoldernames = [ folder['name'] for folder in self.status['folders'] ]
            newfoldernames = [ folder['name'] for folder in status['folders'] ]

            updatefolders = [ folder for folder in status['folders'] if folder['name'] in curfoldernames ]
            newfolders = [ folder for folder in status['folders'] if folder['name'] not in curfoldernames ]
            oldfolders = [ folder for folder in self.status['folders'] if folder['name'] not in newfoldernames ]
            
            for folder in newfolders:
                name = folder['name']
                menuitem = gtk.MenuItem(name)
                self.menu.prepend(menuitem)
                menuitem.show()
                folderitem = {'menuitem': menuitem, 'sizeitem': {}, 'peeritems': {}}
                self.folderitems[name] = folderitem
                submenu = self.build_folder_menu(folder)
                menuitem.set_submenu(submenu)

            for folder in updatefolders:
                self.update_folder_menu(folder)

            for folder in oldfolders:
                name = folder['name']
                self.menu.remove(self.folderitems[name]['menuitem'])
                del self.folderitems[name]

            self.status = status
            return True

        except requests.exceptions.ConnectionError:
            logging.warning('Status request failed, attempting to re-initialise session')
            self.show_error("Lost connection to Bittorrent Sync")
            self.folderitems = {}
            self.status = { 'folders': [] }
            gtk.timeout_add(5000, self.setup_session)
            return False
        except requests.exceptions.HTTPError:
            logging.warning('Communication Error caught, displaying error message')
            self.show_error("Communication Error "+str(response.status_code))
            self.folderitems = {}
            self.status = { 'folders': [] }
            gtk.timeout_add(5000, self.setup_session)
            return True

    def check_activity(self, folders):
        """
        Given the current folder list from the server, determines
        whether there is any network activity and sets a flag in
        self.active
        """
        isactive = False
        active_folder_names = set()
        for folder in folders:
            for peer in folder['peers']:
                if peer['status'].find('<div') != -1:
                    logging.info('Sync activity detected')
                    isactive = True
                    active_folder_names.add(folder['name'])
                    break

        self.active = isactive
        self.active_folder_names = active_folder_names

        if self.active:
            if self.animate == None:
                logging.info('Starting animation loop')
                gtk.timeout_add(1000, self.animate_icon)

    def format_status(self, peer):
        """
        Formats the peer status information for display.
        Substitues HTML tags with appropriate unicode characters and 
        returns name followed by status.
        """
        name = peer['name']
        status = peer['status'].replace("<div class='uparrow' />", "⇧")
        status = status.replace("<div class='downarrow' />", "⇩")
        return name+': '+status

    def build_folder_menu(self, folder):
	"""
	Build a submenu for the specified folder,
	including items to show the size, open the folder in
	the file manager, show each connected peer, and to 
	copy the secrets to the clipboard.

	Stores references to the size and peer items so they
	can easily be updated.
	"""
	menu = gtk.Menu()

	folderitem = self.folderitems[folder['name']]
	folderitem['sizeitem'] = gtk.MenuItem(folder['size'])
	folderitem['sizeitem'].set_sensitive(False)
	folderitem['sizeitem'].show()
	openfolder = gtk.MenuItem('Open in File Browser')
	openfolder.connect("activate", self.open_fm, folder['name'])
	openfolder.show()

	menu.append(folderitem['sizeitem'])
	menu.append(openfolder)

	if len(folder['peers']) > 0:
	    sep = gtk.SeparatorMenuItem()
	    sep.show()
	    menu.append(sep)
            folderitem['topsepitem'] = sep
	    for peer in folder['peers']:
		buf = self.format_status(peer)
		img = gtk.Image()
		if peer['direct']:
			img.set_from_file(args.iconpath+'/btsync-direct.png')
		else:
			img.set_from_file(args.iconpath+'/btsync-relay.png')
		peeritem = gtk.ImageMenuItem(gtk.STOCK_NEW, buf)
		peeritem.set_image(img)
                peeritem.set_always_show_image(True)
		peeritem.set_sensitive(False)
		peeritem.show()
		folderitem['peeritems'][peer['name']] = peeritem
		menu.append(peeritem)
        else:
            folderitem['topsepitem'] = None

        sep = gtk.SeparatorMenuItem()
	sep.show()
	menu.append(sep)
        folderitem['bottomsepitem'] = sep

        readonlysecret = folder['secret']
        if folder['iswritable']:
                readonlysecret = folder['readonlysecret']
                readwrite = gtk.MenuItem('Get Full Access Secret')
                readwrite.connect("activate", self.copy_secret, folder['secret'])

                readwrite.show()
                menu.append(readwrite)

        readonly = gtk.MenuItem('Get Read Only Secret')
        readonly.connect("activate", self.copy_secret, readonlysecret)

        readonly.show()
        menu.append(readonly)

	return menu
    
    def update_folder_menu(self, folder):
        """
        Updates the submenu for the given folder with the current size
        and updates each peer.
        """
        
        folderitem = self.folderitems[folder['name']]
        folderitem['sizeitem'].set_label(folder['size'])

        menuitem = folderitem['menuitem']

        # we build up this set during check_activity
        # it contains the names of any folders with active peers
        # we display these in the menu with a different icon so that users
        # can see at a glance which of the peers is responsible for a busy icon
        if folder['name'] in self.active_folder_names:
            menuitem.set_label('⇅\t' + folder['name'])
        else:
            menuitem.set_label('―\t' + folder['name'])
        
        menu = menuitem.get_submenu()

        curfolder = [ f for f in self.status['folders'] if folder['name'] == f['name'] ].pop()
        curpeernames = [ peer['name'] for peer in curfolder['peers'] ]
        newpeernames = [ peer['name'] for peer in folder['peers'] ]

        updatepeers = [ peer for peer in folder['peers'] if peer['name'] in curpeernames ]
        newpeers = [ peer for peer in folder['peers'] if peer['name'] not in curpeernames ]
        oldpeers = [ peer for peer in curfolder['peers'] if peer['name'] not in newpeernames ]


        for peer in newpeers:
            bottomseppos = menu.get_children().index(folderitem['bottomsepitem'])
            buf = self.format_status(peer)
            peeritem = gtk.MenuItem(buf)
            peeritem.set_sensitive(False)
            peeritem.show()
            folderitem['peeritems'][peer['name']] = peeritem

            pos = bottomseppos

            if (folderitem['topsepitem'] == None):
                sep = gtk.SeparatorMenuItem()
                sep.show()
                menu.insert(sep, pos)
                folderitem['topsepitem'] = sep
                pos = pos+1

            menu.insert(peeritem, pos)

        for peer in updatepeers:
            buf = self.format_status(peer)
            folderitem['peeritems'][peer['name']].set_label(buf)

        for peer in oldpeers:
            menu.remove(folderitem['peeritems'][peer['name']])
            topseppos = menu.get_children().index(folderitem['topsepitem'])
            bottomseppos = menu.get_children().index(folderitem['bottomsepitem'])
            if (topseppos == bottomseppos-1):
                menu.remove(folderitem['topsepitem'])
                folderitem['topsepitem'] = None


    def show_error(self, message):
        """
        Removes all items from the menu (except quit) and displays an error
        message in their place. Also changes the icon to an error icon.
        """
        self.active = False
        if self.error_item == None:                    
            self.set_icon('-error')

            for child in self.menu.get_children():
                if child == self.sep1:
                    pass
                elif child == self.pause_item:
                    pass
                elif child == self.webui_item:
                    self.webui_item.set_sensitive(False)
                elif child == self.sep2:
                    pass
                elif child == self.debug_item:
                    pass
                elif child == self.quit_item:
                    pass
                else:
                    self.menu.remove(child)

            self.error_item = gtk.MenuItem(message)
            self.error_item.set_sensitive(False)
            self.menu.prepend(self.error_item)
            self.error_item.show()

    def clear_error(self):
        """
        Removes the error message from the menu and changes the icon back
        to normal
        """
        self.webui_item.set_sensitive(True)
        if self.error_item != None:
            self.menu.remove(self.error_item)
            self.error_item = None
            self.set_icon('')

    def copy_secret(self, menuitem, secret):
        """
        Copies the supplied secret to the clipboard
        """
    	self.clipboard.set_text(secret)
        logging.info('Secret copied to clipboard')
        logging.debug(secret)
    	return True

    def animate_icon(self):
        """
        Cycles the icon through 3 frames to indicate network activity
        """
        if self.active == False:
            logging.info('Terminating animation loop; Resetting icon')
            self.animate = None
            self.set_icon('')
            self.frame = 0
            return False
        else:
            self.animate = True
            logging.debug('Setting animation frame to {}'.format(self.frame % 3))
            self.set_icon('-active-{}'.format(self.frame % 3))
            self.frame += 1
            return True
        
    def set_icon(self, variant):
        """
        Changes the icon to the given variant
        """
        logging.debug('Setting icon to '+args.iconpath+'/btsync'+variant)
        self.ind.set_icon('btsync'+variant)
        return False

    def open_webui(self, widget):
        """
        Opens a browser to the address of the WebUI indicated in the config file
        """
        logging.info('Opening Web Browser to http://'+self.config['webui']['listen'])
	webbrowser.open(self.webui, 2)
	return True

    def open_fm(self, widget, path):
        logging.info('Opening File manager to '+path)
	if os.path.isdir(path):
	    subprocess.call(['xdg-open', path])

    def toggle_debugging(self, widget):
        """
        Creates or clears the debugging flags for btsync
        """
	filepath = self.config['storage_path']+'/debug.txt'
	if (os.path.isfile(filepath)):
	    os.unlink(filepath)
            logging.info('Bittorrent Sync debugging disabled')
	else:
	    f = open(filepath, 'w')
	    f.write('FFFF')
            logging.info('Bittorrent Sync debugging enabled')
	return True

    def toggle_pause(self, widget):
        """
        handles the pause/resume feature
        """
        btsyncmanager = "/usr/bin/btsync"
        if (os.path.exists(btsyncmanager)):
            try:
                filepath = self.config['storage_path']+'/paused'
                if (os.path.isfile(filepath)):
                    logging.info('Calling '+btsyncmanager+ ' resume')
                    subprocess.check_call([btsyncmanager, 'resume'])
	            logging.info('Bittorrent Sync resumed')
                else:
                    logging.info('Calling '+btsyncmanager+ ' pause')
                    subprocess.check_call([btsyncmanager, 'pause'])
	            logging.info('Bittorrent Sync paused')
            except subprocess.CalledProcessError, e:
                logging.warning('btsync manager failed with status '+e.returncode)
                logging.warning(e.output)
        else:
            logging.error("Could not find BitTorrent Sync Manager at "+btsyncmanager)
        return True

    def get_response_text(self, response):
        """
        Version-safe way to get the response text from a requests module response object
        Older versions use response.content instead of response.text
        """
        return response.text if hasattr(response, "text") else response.content

    def get_response_json(self, response):
	"""
	Version-safe way to parse json from request module response object
	The version in the Ubuntu 12.04 LTS repositories doesnt have .json() 
	"""
	try:
	    response_json = response.json()
	except AttributeError:
	    response_json = json.loads(self.get_response_text(response))
	except TypeError:
	    response_json = json.loads(self.get_response_text(response))
	return response_json

    def fix_encoding(self, text):
        return text.encode('latin-1').decode('utf-8')

    def main(self):
        gtk.timeout_add(TIMEOUT * 1000, self.setup_session)
        gtk.main()

    def quit(self, widget):
        logging.info('Exiting')
        
        if self.btsync_user:
            logging.info('Running btsync-stopper before exit')
            try:
                stopper = os.path.dirname(os.path.realpath(__file__))+"/btsync-stopper"
                if (os.path.exists(stopper)):
                    logging.info('Calling '+stopper)
                    subprocess.check_call(stopper)
                else:
                    logging.error("Cant find btsync-stopper at "+stopper)
            except subprocess.CalledProcessError, e:
                logging.warning('btsync-stopper failed with status '+e.returncode)
                logging.warning(e.output)
                print "Cannot exit BitTorrent Sync: "+e.output
                print "Please exit BitTorrent Sync manually"

        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', 
                        default=os.environ['HOME']+'/.btsync.conf',
                        help="Location of BitTorrent Sync config file")
    parser.add_argument('--iconpath', 
                        default=os.path.dirname(os.path.realpath(__file__))+"/icons",
                        help="Path to icon theme folder")
    parser.add_argument('-v', '--version',
			action='store_true',
                        help="Print version information and exit")
    parser.add_argument('--log',
                        default='WARNING',
                        help="Set logging level")
    args = parser.parse_args()

    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log)

    logging.basicConfig(level=numeric_level)

    if (args.version):
	print os.path.basename(__file__)+" Version "+VERSION
	exit()

    btconf = BtSyncConfig()

    with file_lock(btconf.config['storage_path'] + '/indicator.lock'):
        indicator = BtSyncIndicator(btconf)
        indicator.main()


########NEW FILE########
