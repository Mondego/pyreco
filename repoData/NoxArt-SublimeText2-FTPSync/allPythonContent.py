__FILENAME__ = FTPSync
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Jiri "NoxArt" Petruzelka
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# @author Jiri "NoxArt" Petruzelka | petruzelka@noxart.cz | @NoxArt
# @copyright (c) 2012 Jiri "NoxArt" Petruzelka
# @link https://github.com/NoxArt/SublimeText2-FTPSync

# Doc comment syntax inspired by http://stackoverflow.com/a/487203/387503

# ==== Libraries ===========================================================================

# Sublime Text 2 API: see http://www.sublimetext.com/docs/2/api_reference.html
# Sublime Text 3 API: see http://www.sublimetext.com/docs/3/api_reference.html
import sublime
import sublime_plugin

# Python's built-in libraries
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import traceback
import webbrowser

# FTPSync libraries
if sys.version < '3':
	from ftpsynccommon import Types
	from ftpsyncwrapper import CreateConnection, TargetAlreadyExists
	from ftpsyncprogress import Progress
	from ftpsyncfiles import getFolders, findFile, getFiles, formatTimestamp, gatherMetafiles, replace, addLinks, fileToMetafile
	from ftpsyncworker import Worker
	from ftpsyncfilewatcher import FileWatcher
	# exceptions
	from ftpsyncexceptions import FileNotFoundException
else:
	from FTPSync.ftpsynccommon import Types
	from FTPSync.ftpsyncwrapper import CreateConnection, TargetAlreadyExists
	from FTPSync.ftpsyncprogress import Progress
	from FTPSync.ftpsyncfiles import getFolders, findFile, getFiles, formatTimestamp, gatherMetafiles, replace, addLinks, fileToMetafile
	from FTPSync.ftpsyncworker import Worker
	from FTPSync.ftpsyncfilewatcher import FileWatcher
	# exceptions
	from FTPSync.ftpsyncexceptions import FileNotFoundException

# ==== Initialization and optimization =====================================================
__dir__ = os.path.dirname(os.path.realpath(__file__))

isLoaded = False

isDebug = True
# print overly informative messages?
isDebugVerbose = True
# default config for a project
projectDefaults = {}
nested = []
index = 0
# global config key - for specifying global config in settings file
globalConfigKey = '__global'
ignore = False
# time format settings
timeFormat = ""
# delay before check of right opened file is performed, cancelled if closed in the meantime
downloadOnOpenDelay = 0

coreConfig = {}


# name of a file to be detected in the project
configName = 'ftpsync.settings'
# name of a file that is a default sheet for new configs for projects
connectionDefaultsFilename = 'ftpsync.default-settings'
# timeout for a Sublime status bar messages [ms]
messageTimeout = 250
# comment removing regexp
removeLineComment = re.compile('//.*', re.I)
# deprecated names
deprecatedNames = {
	"check_time": "overwrite_newer_prevention"
}


# connection cache pool - all connections
connections = {}
# connections currently marked as {in use}
usingConnections = []
# root check cache
rootCheckCache = {}
# individual folder config cache, file => config path
configs = {}
# scheduled delayed uploads, file_path => action id
scheduledUploads = {}
# limit of workers
workerLimit = 0
# debug workers?
debugWorkers = False
# debug json?
debugJson = False


# overwrite cancelled
overwriteCancelled = []

# last navigation
navigateLast = {
	'config_file': None,
	'connection_name': None,
	'path': None
}
displayPermissions = ''
displayTimestampFormat = ''

# last folder
re_thisFolder = re.compile("/([^/]*?)/?$", re.I)
re_parentFolder = re.compile("/([^/]*?)/[^/]*?/?$", re.I)

# watch pre-scan
preScan = {}

# temporarily remembered passwords
#
# { settings_filepath => { connection_name => password }, ... }
passwords = {}

# Overriding config for on-the-fly modifications
overridingConfig = {}

def isString(var):
	var_type = type(var)

	if sys.version[0] == '3':
		return var_type is str or var_type is bytes
	else:
		return var_type is str or var_type is unicode

def plugin_loaded():
	global coreConfig
	global debugJson
	global debugWorkers
	global displayPermissions
	global displayTimestampFormat
	global downloadOnOpenDelay
	global ignore
	global index
	global isDebug
	global isDebugVerbose
	global isLoaded
	global nested
	global projectDefaults
	global re_ignore
	global settings
	global systemNotifications
	global timeFormat
	global workerLimit

	# global config
	settings = sublime.load_settings('FTPSync.sublime-settings')

	# test settings
	if settings.get('project_defaults') is None:
		print ("="*86)
		print ("FTPSync > Error loading settings ... please restart Sublime Text after installation")
		print ("="*86)

	# print debug messages to console?
	isDebug = settings.get('debug')
	# print overly informative messages?
	isDebugVerbose = settings.get('debug_verbose')
	# default config for a project
	projectDefaults = settings.get('project_defaults')

	index = 0

	for item in projectDefaults.items():
		if type(item[1]) is dict:
			nested.append(index)
		index += 1

	# global ignore pattern
	ignore = settings.get('ignore')
	# time format settings
	timeFormat = settings.get('time_format')
	# delay before check of right opened file is performed, cancelled if closed in the meantime
	downloadOnOpenDelay = settings.get('download_on_open_delay')
	# system notifications
	systemNotifications = settings.get('system_notifications')

	# compiled global ignore pattern
	if isString(ignore):
		re_ignore = re.compile(ignore)
	else:
		re_ignore = None

	# loaded project's config will be merged with this global one
	coreConfig = {
		'ignore': ignore,
		'debug_verbose': settings.get('debug_verbose'),
		'ftp_retry_limit': settings.get('ftp_retry_limit'),
		'ftp_retry_delay': settings.get('ftp_retry_delay'),
		'connection_timeout': settings.get('connection_timeout'),
		'ascii_extensions': settings.get('ascii_extensions'),
		'binary_extensions': settings.get('binary_extensions')
	}

	# limit of workers
	workerLimit = settings.get('max_threads')
	# debug workers?
	debugWorkers = settings.get('debug_threads')
	# debug json?
	debugJson = settings.get('debug_json')

	displayPermissions = settings.get('browse_display_permission')
	displayTimestampFormat = settings.get('browse_timestamp_format')

	isLoaded = True
	if isDebug:
		print ('FTPSync > plugin async loaded')

if int(sublime.version()) < 3000:
	plugin_loaded()

# ==== Generic =============================================================================

# Dumps the exception to console
def handleException(exception):
	print ("FTPSync > Exception in user code:")
	print ('-' * 60)
	traceback.print_exc(file=sys.stdout)
	print ('-' * 60)


# Safer print of exception message
def stringifyException(exception):
	return str(exception)


# Checks whether cerain package exists
def packageExists(packageName):
	return os.path.exists(os.path.join(sublime.packages_path(), packageName))


def decode(string):
	if hasattr('x', 'decode') and callable(getattr('x', 'decode')):
		return string.decode('utf-8')
	else:
		return string


# ==== Messaging ===========================================================================

# Shows a message into Sublime's status bar
#
# @type  text: string
# @param text: message to status bar
def statusMessage(text):
	sublime.status_message(text)


# Schedules a single message to be logged/shown
#
# @type  text: string
# @param text: message to status bar
#
# @global messageTimeout
def dumpMessage(text):
	sublime.set_timeout(lambda: statusMessage(text), messageTimeout)


# Prints a special message to console and optionally to status bar
#
# @type  text: string
# @param text: message to status bar
# @type  name: string|None
# @param name: comma-separated list of connections or other auxiliary info
# @type  onlyVerbose: boolean
# @param onlyVerbose: print only if config has debug_verbose enabled
# @type  status: boolean
# @param status: show in status bar as well = true
#
# @global isDebug
# @global isDebugVerbose
def printMessage(text, name=None, onlyVerbose=False, status=False):
	message = "FTPSync"

	if name is not None:
		message += " [" + name + "]"

	message += " > "
	message += text

	if isDebug and (onlyVerbose is False or isDebugVerbose is True):
		print (message.encode('utf-8'))

	if status:
		dumpMessage(message)


# Issues a system notification for certian event
#
# @type text: string
# @param text: notification message
def systemNotify(text):
	try:
		import subprocess

		text = "FTPSync > " + text

		if sys.platform == "darwin":
		    """ Run Grown Notification """
		    cmd = '/usr/local/bin/growlnotify -a "Sublime Text 2" -t "FTPSync message" -m "'+text+'"'
		    subprocess.call(cmd,shell=True)
		elif sys.platform == "linux2":
		    subprocess.call('/usr/bin/notify-send "Sublime Text 2" "'+text+'"',shell=True)
		elif sys.platform == "win32":
		    """ Find the notifaction platform for windows if there is one"""

	except Exception as e:
		printMessage("Notification failed")
		handleExceptions(e)


# Creates a process message with progress bar (to be used in status bar)
#
# @type  stored: list<string>
# @param stored: usually list of connection names
# @type progress: Progress
# @type action: string
# @type action: action that the message reports about ("uploaded", "downloaded"...)
# @type  basename: string
# @param basename: name of a file connected with the action
#
# @return string message
def getProgressMessage(stored, progress, action, basename = None):
	base = "FTPSync [remotes: " + ",".join(stored) + "] "
	action = "> " + action + " "

	if progress is not None:
		base += " ["

		percent = progress.getPercent()

		for i in range(0, int(percent)):
			base += "="
		for i in range(int(percent), 20):
			base += "--"

		base += " " + str(progress.current) + "/" + str(progress.getTotal()) + "] "

	base += action

	if basename is not None:
		base += " {" + basename + "}"

	return base


# ==== Config =============================================================================

# Alters override config
#
# @type  config_dir_name: string
# @param config_dir_name: path to a folder of a config
# @type  property: string
# @param property: property to be modified
# @type value: mixed
# @type specificName: string
# @param specificName: use to only modify specific connection's value
#
# @global overrideConfig
def overrideConfig(config_file_path, property, value, specificName=None):
	if config_file_path is None or os.path.exists(config_file_path) is False:
		return

	config = loadConfig(config_file_path)

	if config_file_path not in overridingConfig:
		overridingConfig[config_file_path] = { 'connections': {} }

	for name in config['connections']:
		if specificName and name != specificName:
			continue

		if name not in overridingConfig[config_file_path]['connections']:
			overridingConfig[config_file_path]['connections'][name] = {}

		overridingConfig[config_file_path]['connections'][name][property] = value


# Invalidates all config cache entries belonging to a certain directory
# as long as they're empty or less nested in the filesystem
#
# @type  config_dir_name: string
# @param config_dir_name: path to a folder of a config to be invalidated
#
# @global configs
def invalidateConfigCache(config_dir_name):
	for file_path in configs:
		if file_path.startswith(config_dir_name) and (configs[file_path] is None or config_dir_name.startswith(configs[file_path])):
			configs.remove(configs[file_path])


# Finds a config file in given folders
#
# @type  folders: list<string>
# @param folders: list of paths to folders to filter
#
# @return list<string> of file paths
#
# @global configName
def findConfigFile(folders):
	return findFile(folders, configName)


# Returns configuration file for a given file
#
# @type  file_path: string
# @param file_path: file_path to the file for which we try to find a config
#
# @return file path to the config file or None
#
# @global configs
def getConfigFile(file_path):
	cacheKey = file_path
	if isString(cacheKey) is False:
		cacheKey = cacheKey.decode('utf-8')

	# try cached
	try:
		if configs[cacheKey]:
			printMessage("Loading config: cache hit (key: " + cacheKey + ")")

		return configs[cacheKey]

	# cache miss
	except KeyError:
		try:
			folders = getFolders(file_path)

			if folders is None or len(folders) == 0:
				return None

			configFolder = findConfigFile(folders)

			if configFolder is None:
				printMessage("Found no config for {" + cacheKey + "}", None, True)
				return None

			config = os.path.join(configFolder, configName)
			configs[cacheKey] = config
			return config

		except AttributeError:
			return None


# Returns hash of file_path
#
# @type  file_path: string
# @param file_path: file path to the file of which we want the hash
#
# @return hash of filepath
def getFilepathHash(file_path):
	return hashlib.md5(file_path.encode('utf-8')).hexdigest()


# Returns path of file from its config file
#
# @type  file_path: string
# @param file_path: file path to the file of which we want the hash
#
# @return string file path from settings root
def getRootPath(file_path, prefix = ''):
	return prefix + os.path.relpath(file_path, os.path.dirname(getConfigFile(file_path))).replace('\\', '/')


# Returns a file path associated with view
#
# @type  file_path: string
# @param file_path: file path to the file of which we want the hash
#
# @return string file path
def getFileName(view):
	return view.file_name()


# Gathers all entries from selected paths
#
# @type  file_path: list<string>
# @param file_path: list of file/folder paths
#
# @return list of file/folder paths
def gatherFiles(paths):
	syncFiles = []
	fileNames = []

	for target in paths:
		if os.path.isfile(target):
			if target not in fileNames:
				fileNames.append(target)
				syncFiles.append([target, getConfigFile(target)])
		elif os.path.isdir(target):
			empty = True

			for root, dirs, files in os.walk(target):
				for file_path in files:
					empty = False

					if file_path not in fileNames:
						fileNames.append(target)
						syncFiles.append([os.path.join(root, file_path), getConfigFile(os.path.join(root, file_path))])

				for folder in dirs:
					path = os.path.join(root, folder)

					if not os.listdir(path) and path not in fileNames:
						fileNames.append(path)
						syncFiles.append([path, getConfigFile(path)])


			if empty is True:
				syncFiles.append([target, getConfigFile(target)])

	return syncFiles


# Returns hash of configuration contents
#
# @type config: dict
#
# @return string
#
# @link http://stackoverflow.com/a/8714242/387503
def getObjectHash(o):
	if isinstance(o, set) or isinstance(o, tuple) or isinstance(o, list):
		return tuple([getObjectHash(e) for e in o])
	elif not isinstance(o, dict):
		return hash(o)

	new_o = copy.deepcopy(o)
	for k, v in new_o.items():
		new_o[k] = getObjectHash(v)

	return hash(tuple(frozenset(new_o.items())))


# Updates deprecated config to newer version
#
# @type config: dict
#
# @return dict (config)
#
# @global deprecatedNames
def updateConfig(config):
	for old_name in deprecatedNames:
		new_name = deprecatedNames[old_name]

		if new_name in config:
			config[old_name] = config[new_name]
		elif old_name in config:
			config[new_name] = config[old_name]

	return config


# Verifies contents of a given config object
#
# Checks that it's an object with all needed keys of a proper type
# Does not check semantic validity of the content
#
# Should be used on configs merged with the defaults
#
# @type  config: dict
# @param config: config dict
#
# @return string verification fail reason or a boolean
def verifyConfig(config):
	if type(config) is not dict:
		return "Config is not a {dict} type"

	keys = ["username", "password", "private_key", "private_key_pass", "path", "encoding", "tls", "use_tempfile", "upload_on_save", "port", "timeout", "ignore", "check_time", "download_on_open", "upload_delay", "after_save_watch", "time_offset", "set_remote_lastmodified", "default_folder_permissions", "default_local_permissions", "always_sync_local_permissions"]

	for key in keys:
		if key not in config:
			return "Config is missing a {" + key + "} key"

	if config['username'] is not None and isString(config['username']) is False:
		return "Config entry 'username' must be null or string, " + str(type(config['username'])) + " given"

	if config['password'] is not None and isString(config['password']) is False:
		return "Config entry 'password' must be null or string, " + str(type(config['password'])) + " given"

	if config['private_key'] is not None and isString(config['private_key']) is False:
		return "Config entry 'private_key' must be null or string, " + str(type(config['private_key'])) + " given"

	if config['private_key_pass'] is not None and isString(config['private_key_pass']) is False:
		return "Config entry 'private_key_pass' must be null or string, " + str(type(config['private_key_pass'])) + " given"

	if config['ignore'] is not None and isString(config['ignore']) is False:
		return "Config entry 'ignore' must be null or string, " + str(type(config['ignore'])) + " given"

	if isString(config['path']) is False:
		return "Config entry 'path' must be a string, " + str(type(config['path'])) + " given"

	if config['encoding'] is not None and isString(config['encoding']) is False:
		return "Config entry 'encoding' must be a string, " + str(type(config['encoding'])) + " given"

	if type(config['tls']) is not bool:
		return "Config entry 'tls' must be true or false, " + str(type(config['tls'])) + " given"

	if type(config['passive']) is not bool:
		return "Config entry 'passive' must be true or false, " + str(type(config['passive'])) + " given"

	if type(config['use_tempfile']) is not bool:
		return "Config entry 'use_tempfile' must be true or false, " + str(type(config['use_tempfile'])) + " given"

	if type(config['set_remote_lastmodified']) is not bool:
		return "Config entry 'set_remote_lastmodified' must be true or false, " + str(type(config['set_remote_lastmodified'])) + " given"

	if type(config['upload_on_save']) is not bool:
		return "Config entry 'upload_on_save' must be true or false, " + str(type(config['upload_on_save'])) + " given"

	if type(config['check_time']) is not bool:
		return "Config entry 'check_time' must be true or false, " + str(type(config['check_time'])) + " given"

	if type(config['download_on_open']) is not bool:
		return "Config entry 'download_on_open' must be true or false, " + str(type(config['download_on_open'])) + " given"

	if type(config['upload_delay']) is not int and type(config['upload_delay']) is not long:
		return "Config entry 'upload_delay' must be integer or long, " + str(type(config['upload_delay'])) + " given"

	if config['after_save_watch'] is not None and type(config['after_save_watch']) is not list:
		return "Config entry 'after_save_watch' must be null or list, " + str(type(config['after_save_watch'])) + " given"

	if type(config['port']) is not int and type(config['port']) is not long:
		return "Config entry 'port' must be an integer or long, " + str(type(config['port'])) + " given"

	if type(config['timeout']) is not int and type(config['timeout']) is not long:
		return "Config entry 'timeout' must be an integer or long, " + str(type(config['timeout'])) + " given"

	if type(config['time_offset']) is not int and type(config['time_offset']) is not long:
		return "Config entry 'time_offset' must be an integer or long, " + str(type(config['time_offset'])) + " given"

	return True


# Parses JSON-type file with comments stripped out (not part of a proper JSON, see http://json.org/)
#
# @type  file_path: string
#
# @return dict
#
# @global removeLineComment
def parseJson(file_path):
	contents = ""

	try:
		file = open(file_path, 'r')

		for line in file:
			contents += removeLineComment.sub('', line)
	finally:
		file.close()

	if debugJson:
		printMessage("Debug JSON:")
		print ("="*86)
		print (contents)
		print ("="*86)

	return json.loads(contents)


# Asks for passwords if missing in configuration
#
# @type config_file_path: string
# @type config: dict
# @param config: configuration object
# @type callback: callback
# @param callback: what should be done after config is filled
# @type window: Window
# @param window: SublimeText2 API Window object
#
# @global passwords
def addPasswords(config_file_path, config, callback, window):
	def setPassword(config, name, password):
		config['connections'][name]['password'] = password

		if config_file_path not in passwords:
			passwords[config_file_path] = {}

		passwords[config_file_path][name] = password

		addPasswords(config_file_path, config, callback, window)

	def ask(connectionName, host, username):
		window.show_input_panel('FTPSync > please provide password for:  ' + str(host) + ' ~ ' + str(username), "", lambda password: setPassword(config, connectionName, password), None, None)

	if type(config) is dict:
		for name in config['connections']:
			prop = config['connections'][name]

			if prop['password'] is None:
				if config_file_path in passwords and name in passwords[config_file_path] and passwords[config_file_path][name] is not None:
					config['connections'][name]['password'] = passwords[config_file_path][name]
				else:
					ask(name, prop['host'], prop['username'])
					return

	return callback()


# Fills passwords if missing in configuration
#
# @type fileList: [ [ filepath, config_file_path ], ... ]
# @type callback: callback
# @param callback: what should be done after config is filled
# @type window: Window
# @param window: SublimeText2 API Window object
#
# @global passwords
def fillPasswords(fileList, callback, window, index = 0):
	def ask():
		fillPasswords(fileList, callback, window, index + 1)

	i = 0
	length = len(fileList)

	if index >= length:
		callback(fileList)
		return

	config_files = []
	for filepath, config_file_path in fileList:
		if config_file_path not in config_files:
			config_files.append(config_file_path)

	for config_file_path in config_files:
		if i < index:
			i = i + 1
			continue

		if config_file_path is None:
			continue

		config = loadConfig(config_file_path)
		if config is not None:
			addPasswords(config_file_path, config, ask, window)
		return

	callback(fileList)


# Parses given config and adds default values to each connection entry
#
# @type  file_path: string
# @param file_path: file path to the file of which we want the hash
#
# @return config dict or None
#
# @global isLoaded
# @global coreConfig
# @global projectDefaults
def loadConfig(file_path):

	if isLoaded is False:
		printMessage("Settings not loaded (just installed?), please restart Sublime Text")
		return None

	if isString(file_path) is False:
		printMessage("LoadConfig expects string, " + str(type(file_path)) + " given")
		return None

	if os.path.exists(file_path) is False:
		return None

	# parse config
	try:
		config = parseJson(file_path)
	except Exception as e:
		printMessage("Failed parsing configuration file: {" + file_path + "} (commas problem?) [Exception: " + stringifyException(e) + "]", status=True)
		handleException(e)
		return None

	result = {}

	# merge with defaults and check
	for name in config:
		if type(config[name]) is not dict:
			printMessage("Failed using configuration: contents are not dictionaries but values", status=True)
			return None

		result[name] = dict(list(projectDefaults.items()) + list(config[name].items()))
		result[name]['file_path'] = file_path

		# fix path
		if len(result[name]['path']) > 1 and result[name]['path'][-1] != "/":
			result[name]['path'] = result[name]['path'] + "/"

		# merge nested
		for index in nested:
			list1 = list(list(projectDefaults.items())[index][1].items())
			list2 = list(result[name][list(projectDefaults.items())[index][0]].items())

			result[name][list(projectDefaults.items())[index][0]] = dict(list1 + list2)
		try:
			if result[name]['debug_extras']['dump_config_load'] is True:
				printMessage(result[name])
		except KeyError:
			pass

		# add passwords
		if file_path in passwords and name in passwords[file_path] and passwords[file_path][name] is not None:
			result[name]['password'] = passwords[file_path][name]

		result[name] = updateConfig(result[name])

		verification_result = verifyConfig(result[name])

		if verification_result is not True:
			printMessage("Invalid configuration loaded: <" + str(verification_result) + ">", status=True)

	# merge with generics
	final = dict(list(coreConfig.items()) + list({"connections": result}.items()))

	# override by overridingConfig
	if file_path in overridingConfig:
		for name in overridingConfig[file_path]['connections']:
			if name in final['connections']:
				for item in overridingConfig[file_path]['connections'][name]:
					final['connections'][name][item] = overridingConfig[file_path]['connections'][name][item]

	return final


# ==== Remote =============================================================================

# Creates a new connection
#
# @type  config: object
# @param config: configuration object
# @type  hash: string
# @param hash: connection cache hash (config filepath hash actually)
#
# @return list of descendants of AbstractConnection (ftpsyncwrapper.py)
def makeConnection(config, hash=None, handleExceptions=True):

	result = []

	# for each config
	for name in config['connections']:
		properties = config['connections'][name]

		# 1. initialize
		try:
			connection = CreateConnection(config, name)
		except Exception as e:
			if handleExceptions is False:
				raise

			printMessage("Connection initialization failed [Exception: " + stringifyException(e) + "]", name, status=True)
			handleException(e)

			return []

		# 2. connect
		try:
			connection.connect()
		except Exception as e:
			if handleExceptions is False:
				raise

			printMessage("Connection failed [Exception: " + stringifyException(e) + "]", name, status=True)
			connection.close(connections, hash)
			handleException(e)

			return []

		printMessage("Connected to: " + properties['host'] + ":" + str(properties['port']) + " (timeout: " + str(properties['timeout']) + ") (key: " + str(hash) + ")", name)

		# 3. authenticate
		try:
			if connection.authenticate():
				printMessage("Authentication processed", name)
		except Exception as e:
			if handleExceptions is False:
				raise

			printMessage("Authentication failed [Exception: " + stringifyException(e) + "]", name, status=True)
			handleException(e)

			return []

		# 4. login
		if properties['username'] is not None and properties['password'] is not None:
			try:
				connection.login()
			except Exception as e:
				printMessage("Login failed [Exception: " + stringifyException(e) + "]", name, status=True)
				handleException(e)

				if properties['file_path'] in passwords and name in passwords[properties['file_path']]:
					passwords[properties['file_path']][name] = None

				if handleExceptions is False:
					raise

				return []

			pass_present = " (using password: NO)"
			if len(properties['password']) > 0:
				pass_present = " (using password: YES)"

			printMessage("Logged in as: " + properties['username'] + pass_present, name)
		else:
			printMessage("Anonymous connection", name)

		# 5. ensure that root exists
		cacheKey = properties['host'] + ":" + properties['path']
		if cacheKey not in rootCheckCache:
			try:
				connection.ensureRoot()

				rootCheckCache[cacheKey] = True
			except Exception as e:
				if handleExceptions is False:
					raise

				printMessage("Failed ensure root exists [Exception: " + stringifyException(e) + "]", name)
				handleException(e)

				return []

		# 6. set initial directory, set name, store connection
		try:
			connection.cwd(properties['path'])
		except Exception as e:
			if handleExceptions is False:
				raise

			printMessage("Failed to set path (probably connection failed) [Exception: " + stringifyException(e) + "]", name)
			handleException(e)

			return []

		# 7. add to connections list
		present = False
		for con in result:
			if con.name == connection.name:
				present = True

		if present is False:
			result.append(connection)

	return result


# Returns connection, connects if needed
#
# @type  hash: string
# @param hash: connection cache hash (config filepath hash actually)
# @type  config: object
# @param config: configuration object
# @type  shared: bool
# @param shared: whether to use shared connection
#
# @return list of descendants of AbstractConnection (ftpsyncwrapper.py)
#
# @global connections
def getConnection(hash, config, shared=True):
	if shared is False:
		return makeConnection(config, hash)

	# try cache
	try:
		if connections[hash] and len(connections[hash]) > 0:
			printMessage("Connection cache hit (key: " + hash + ")", None, True)

		if type(connections[hash]) is not list or len(connections[hash]) < len(config['connections']):
			raise KeyError

		# has config changed?
		valid = True
		index = 0
		for name in config['connections']:
			if getObjectHash(connections[hash][index].config) != getObjectHash(config['connections'][name]):
				valid = False

			index += 1

		if valid == False:
			for connection in connections[hash]:
				connection.close(connections, hash)

			raise KeyError

		# is config truly alive
		for connection in connections[hash]:
			if connection.isAlive() is False:
				raise KeyError

		return connections[hash]

	# cache miss
	except KeyError:
		connections[hash] = makeConnection(config, hash)

		# schedule connection timeout
		def closeThisConnection():
			if hash not in usingConnections:
				closeConnection(hash)
			else:
				sublime.set_timeout(closeThisConnection, config['connection_timeout'] * 1000)

		sublime.set_timeout(closeThisConnection, config['connection_timeout'] * 1000)

		# return all connections
		return connections[hash]


# Close all connections for a given config file
#
# @type  hash: string
# @param hash: connection cache hash (config filepath hash actually)
#
# @global connections
def closeConnection(hash):
	if isString(hash) is False:
		printMessage("Error closing connection: connection hash must be a string, " + str(type(hash)) + " given")
		return

	if hash not in connections:
		return

	try:
		for connection in connections[hash]:
			connection.close(connections, hash)
			printMessage("Closed", connection.name)

		if len(connections[hash]) == 0:
			connections.pop(hash)

	except Exception as e:
		printMessage("Error when closing connection (key: " + hash + ") [Exception: " + stringifyException(e) + "]")
		handleException(e)


# Returns a new worker
def createWorker():
	queue = Worker(workerLimit, makeConnection, loadConfig)

	if debugWorkers and isDebug:
		queue.enableDebug()

	return queue


# ==== Executive functions ======================================================================

class SyncObject(object):

	def __init__(self):
		self.onFinish = []

	def addOnFinish(self, callback):
		self.onFinish.append(callback)

		return self

	def triggerFinish(self, args):
		for finish in self.onFinish:
			if finish is not None:
				finish(args)


# Generic synchronization command
class SyncCommand(SyncObject):

	def __init__(self, file_path, config_file_path):
		SyncObject.__init__(self)

		if sys.version[0] == '3' and type(file_path) is bytes:
			file_path = file_path.decode('utf-8')

		self.running = True
		self.closed = False
		# has exclusive ownership of connection?
		self.ownConnection = False
		self.file_path = file_path
		self.config_file_path = config_file_path

		if isString(config_file_path) is False:
			printMessage("Cancelling " + self.getIdentification() + ": invalid config_file_path given (type: " + str(type(config_file_path)) + ")")
			self.close()
			return

		if os.path.exists(config_file_path) is False:
			printMessage("Cancelling " + self.getIdentification() + ": config_file_path: No such file")
			self.close()
			return

		self.config = loadConfig(config_file_path)
		if file_path is not None:
			self.basename = os.path.relpath(file_path, os.path.dirname(config_file_path))

		self.config_hash = getFilepathHash(self.config_file_path)
		self.connections = None
		self.worker = None

	def getIdentification(self):
		return str(self.__class__.__name__) + " [" + self.file_path + "]"

	def setWorker(self, worker):
		self.worker = worker

	def setConnection(self, connections):
		self.connections = connections
		self.ownConnection = False

	def _createConnection(self):
		if self.connections is None:
			self.connections = getConnection(self.config_hash, self.config, False)
			self.ownConnection = True

	def _localizePath(self, config, remote_path):
		path = remote_path
		if path.find(config['path']) == 0:
			path = os.path.realpath(os.path.join(os.path.dirname(self.config_file_path), remote_path[len(config['path']):]))

		return path

	def execute(self):
		raise NotImplementedError("Abstract method")

	def close(self):
		self.running = False
		self.closed = True

	def _closeConnection(self):
		closeConnection(getFilepathHash(self.config_file_path))

	def whitelistConnections(self, whitelistConnections):
		toBeRemoved = []
		for name in self.config['connections']:
			if name not in whitelistConnections:
				toBeRemoved.append(name)

		for name in toBeRemoved:
			self.config['connections'].pop(name)

		return self

	def isRunning(self):
		return self.running

	def __del__(self):
		self.running = False

		if hasattr(self, 'config_hash') and self.config_hash in usingConnections:
			usingConnections.remove(self.config_hash)

		if hasattr(self, 'ownConnection'):
			if self.ownConnection:
				for connection in self.connections:
					if isDebug:
						printMessage("Closing connection")
					connection.close()
			elif hasattr(self, 'worker') and self.worker is not None:
				self.worker = None


# Transfer-related sychronization command
class SyncCommandTransfer(SyncCommand):

	def __init__(self, file_path, config_file_path, progress=None, onSave=False, disregardIgnore=False, whitelistConnections=[], forcedSave=False):
		SyncCommand.__init__(self, file_path, config_file_path)

		self.progress = progress
		self.onSave = onSave
		self.disregardIgnore = False

		# global ignore
		if disregardIgnore is False and ignore is not None and re_ignore.search(self.file_path) is not None:
			if self._onPreConnectionRemoved():
				printMessage("File globally ignored: {" + os.path.basename(self.file_path) + "}", onlyVerbose=True)
				self.close()
				return

		toBeRemoved = []
		for name in self.config['connections']:

			# on save
			if self.config['connections'][name]['upload_on_save'] is False and onSave is True and forcedSave is False:
				toBeRemoved.append(name)
				continue

			# ignore
			if disregardIgnore is False and self.config['connections'][name]['ignore'] is not None and re.search(self.config['connections'][name]['ignore'], self.file_path):
				if self._onPreConnectionRemoved():
					toBeRemoved.append(name)

				printMessage("File ignored by rule: {" + self.basename + "}", name, True)
				continue

			# whitelist
			if len(whitelistConnections) > 0 and name not in whitelistConnections:
				toBeRemoved.append(name)
				continue

		for name in toBeRemoved:
			self.config['connections'].pop(name)

	# Code that needs to run when a connection is removed (ignored) 
	#
	# @return bool: truly remove?
	def _onPreConnectionRemoved(self):
		if self.progress is not None:
			self.progress.progress()

		return True

	# Get connections of this command that were not removed due to config, ignore etc.
	def getConnectionsApplied(self):
		return self.config['connections']

	# Creates a message when transfer is finished and sends it to console / bar / system
	def finishMessage(self, title, stored, wasFinished):
		notify = title + "ing "
		if self.progress is None or self.progress.getTotal() == 1:
			notify += "{" + self.basename + "} "
		else:
			notify += str(self.progress.getTotal()) + " files "
		notify += "finished!"

		if self.progress is not None and self.progress.isFinished() and wasFinished is False:
			dumpMessage(getProgressMessage(stored, self.progress, notify))
		else:
			dumpMessage(getProgressMessage(stored, self.progress, title + "ed ", self.basename))

		if systemNotifications and self.progress is None or (self.progress.isFinished() and wasFinished is False):
			systemNotify(notify)


# Upload command
class SyncCommandUpload(SyncCommandTransfer):

	def __init__(self, file_path, config_file_path, progress=None, onSave=False, disregardIgnore=False, whitelistConnections=[], forcedSave=False):
		self.delayed = False
		self.skip = False

		SyncCommandTransfer.__init__(self, file_path, config_file_path, progress, onSave, disregardIgnore, whitelistConnections, forcedSave)

		self.watcher = FileWatcher(self.config_file_path, self.config['connections'])
		if os.path.exists(file_path) is False:
			printMessage("Cancelling " + self.getIdentification() + ": file_path: No such file")
			self.close()
			return

	# Code that needs to run when a connection is removed (ignored)
	#
	# @return bool: truly remove?
	def _onPreConnectionRemoved(self):
		SyncCommandTransfer._onPreConnectionRemoved(self)

		# when saving and has afterwatch, don't remove completely, only skip
		# so that we at least upload those changed files
		if self._hasAfterWatch() and self.onSave:
			self.skip = True
			return False

		return True

	# Returns whether any of the config entries has after_save_watch enabled
	# Can't be in FileWatcher due to cycling dependency with config and _onPreConnectionRemoved
	def _hasAfterWatch(self):
		for name in self.config['connections']:
			if self.config['connections'][name]['after_save_watch']:
				return True

		return False

	# ???
	def setScanned(self, event, name, data):
		self.watcher.setScanned(event, name, data)

	# Executes command
	def execute(self):
		if self.closed is True:
			printMessage("Cancelling " + self.getIdentification() + ": command is closed")
			self.close()
			return

		if len(self.config['connections']) == 0:
			printMessage("Cancelling " + self.getIdentification() + ": zero connections apply")
			self.close()
			return

		self._createConnection()

		# afterwatch
		if self.onSave is True:
			try:
				self.watcher.prepare()
			except Exception as e:
				printMessage("Watching failed: {" + self.basename + "} [Exception: " + stringifyException(e) + "]", "", False, True)

		usingConnections.append(self.config_hash)
		stored = []
		index = -1

		for name in self.config['connections']:
			index += 1

			try:
				self._createConnection()

				# identification
				connection = self.connections[index]
				id = os.urandom(32)
				scheduledUploads[self.file_path] = id

				# action
				def action():
					try:

						# cancelled
						if self.file_path not in scheduledUploads or scheduledUploads[self.file_path] != id:
							return

						# process
						if self.skip is False:
							connection.put(self.file_path)

						stored.append(name)

						if self.skip is False:
							printMessage("Uploaded {" + self.basename + "}", name)
						else:
							printMessage("Ignored {" + self.basename + "}", name)

						# cleanup
						scheduledUploads.pop(self.file_path)

						if self.delayed is True:
							for change in self.watcher.getChangedFiles(name):
								if change.isSameFilepath(self.file_path):
									continue

								change = change.getPath()
								command = SyncCommandUpload(change, getConfigFile(change), None, False, True, [name])

								if self.worker is not None:
									command.setWorker(self.worker)
									self.worker.addCommand(command, self.config_file_path)
								else:
									command.execute()

							self.delayed = False
							self.__del__()

						# no need to handle progress, delay action only happens with single uploads
						self.triggerFinish(self.file_path)

					except Exception as e:
						printMessage("Upload failed: {" + self.basename + "} [Exception: " + stringifyException(e) + "]", name, False, True)
						handleException(e)

					finally:
						self.running = False

				# delayed
				if self.onSave is True and self.config['connections'][name]['upload_delay'] > 0:
					self.delayed = True
					printMessage("Delaying processing " + self.basename + " by " + str(self.config['connections'][name]['upload_delay']) + " seconds", name, onlyVerbose=True)
					sublime.set_timeout(action, self.config['connections'][name]['upload_delay'] * 1000)
				else:
					action()

			except IndexError:
				continue

			except EOFError:
				printMessage("Connection has been terminated, please retry your action", name, False, True)
				self._closeConnection()

			except Exception as e:
				printMessage("Upload failed: {" + self.basename + "} [Exception: " + stringifyException(e) + "]", name, False, True)
				handleException(e)

		if self.progress is not None:
			self.progress.progress()

		if len(stored) > 0:
			self.finishMessage("Upload", stored, True)

	def __del__(self):
		if hasattr(self, 'delayed') and self.delayed is False:
			SyncCommand.__del__(self)
		else:
			self.closed = True
			self.running = False


# Download command
class SyncCommandDownload(SyncCommandTransfer):

	def __init__(self, file_path, config_file_path, progress=None, onSave=False, disregardIgnore=False, whitelistConnections=[], forcedSave = False):
		SyncCommandTransfer.__init__(self, file_path, config_file_path, progress, onSave, disregardIgnore, whitelistConnections, forcedSave)

		self.isDir = False
		self.forced = False
		self.skip = False

	def setIsDir(self):
		self.isDir = True

		return self

	def setForced(self):
		self.forced = True

		return self

	def setSkip(self):
		self.skip = True

		return self

	def execute(self):
		self.forced = True

		if self.closed is True:
			printMessage("Cancelling " + self.getIdentification() + ": command is closed")
			self.close()
			return

		if len(self.config['connections']) == 0:
			printMessage("Cancelling " + self.getIdentification() + ": zero connections apply")
			self.close()
			return

		self._createConnection()

		usingConnections.append(self.config_hash)
		index = -1
		stored = []

		for name in self.config['connections']:
			index += 1

			try:
				if self.isDir or os.path.isdir(self.file_path):
					contents = self.connections[index].list(self.file_path)
					if type(contents) is not list:
						printMessage("List returned no entries {0}".format(self.file_path))
						continue

					if os.path.exists(self.file_path) is False:
						os.makedirs(self.file_path)

					if self.progress:
						for entry in contents:
							if entry.isDirectory() is False:
								self.progress.add([entry.getName()])

					self.running = False
					for entry in contents:
						full_name = os.path.join(self.file_path, entry.getName())

						command = SyncCommandDownload(full_name, self.config_file_path, progress=self.progress, disregardIgnore=self.disregardIgnore)

						if self.forced:
							command.setForced()

						if entry.isDirectory() is True:
							command.setIsDir()
						elif not self.forced and entry.isNewerThan(full_name) is True:
							command.setSkip()

						if self.worker is not None:
							command.setWorker(self.worker)
							self.worker.addCommand(command, self.config_file_path)
						else:
							command.execute()

				else:
					if not self.skip or self.forced:
						self.connections[index].get(self.file_path, blockCallback = lambda: dumpMessage(getProgressMessage([name], self.progress, "Downloading", self.basename)))
						printMessage("Downloaded {" + self.basename + "}", name)
						self.triggerFinish(self.file_path)
					else:
						printMessage("Skipping {" + self.basename + "}", name)

					stored.append(name)

			except IndexError:
				continue

			except FileNotFoundException:
				printMessage("Remote file not found", name, False, True)
				handleException(e)

			except EOFError:
				printMessage("Connection has been terminated, please retry your action", name, False, True)
				self._closeConnection()

			except Exception as e:
				printMessage("Download of {" + self.basename + "} failed [Exception: " + stringifyException(e) + "]", name, False, True)
				handleException(e)

			finally:
				self.running = False
				break

		wasFinished = False
		if self.progress is None or self.progress.isFinished() is False:
			wasFinished = True

		if self.progress is not None and self.isDir is not True:
			self.progress.progress()

		if len(stored) > 0:
			self.finishMessage("Download", stored, wasFinished)

			file_path = self.file_path
			def refresh():
				view = sublime.active_window().active_view()
				if view is not None and view.file_name() == file_path:
					view.run_command("revert")

			sublime.set_timeout(refresh, 1)


# Rename command
class SyncCommandRename(SyncCommand):

	def __init__(self, file_path, config_file_path, new_name):
		if os.path.exists(file_path) is False:
			printMessage("Cancelling " + self.getIdentification() + ": file_path: No such file")
			self.close()
			return

		if isString(new_name) is False:
			printMessage("Cancelling SyncCommandRename: invalid new_name given (type: " + str(type(new_name)) + ")")
			self.close()
			return

		if len(new_name) == 0:
			printMessage("Cancelling SyncCommandRename: empty new_name given")
			self.close()
			return

		self.new_name = new_name
		self.dirname = os.path.dirname(file_path)
		SyncCommand.__init__(self, file_path, config_file_path)

	def execute(self):
		if self.closed is True:
			printMessage("Cancelling " + self.getIdentification() + ": command is closed")
			self.close()
			return

		if len(self.config['connections']) == 0:
			printMessage("Cancelling " + self.getIdentification() + ": zero connections apply")
			self.close()
			return

		self._createConnection()

		usingConnections.append(self.config_hash)
		index = -1
		renamed = []

		exists = []
		remote_new_name = os.path.join( os.path.split(self.file_path)[0], self.new_name)
		for name in self.config['connections']:
			index += 1

			check = None
			try:
				check = self.connections[index].list(remote_new_name)
			except FileNotFoundException:
				pass

			if type(check) is list and len(check) > 0:
				exists.append(name)

		def action(forced=False):
			index = -1

			for name in self.config['connections']:
				index += 1

				try:
					self.connections[index].rename(self.file_path, self.new_name, forced)
					printMessage("Renamed {" + self.basename + "} -> {" + self.new_name + "}", name)
					renamed.append(name)

				except IndexError:
					continue

				except TargetAlreadyExists as e:
					printMessage(stringifyException(e))

				except EOFError:
					printMessage("Connection has been terminated, please retry your action", name, False, True)
					self._closeConnection()

				except Exception as e:
					if str(e).find("No such file or directory"):
						printMessage("Remote file not found", name, False, True)
						renamed.append(name)
					else:
						printMessage("Renaming failed: {" + self.basename + "} -> {" + self.new_name + "} [Exception: " + stringifyException(e) + "]", name, False, True)
						handleException(e)

			# message
			if len(renamed) > 0:
				# rename file
				replace(self.file_path, os.path.join(self.dirname, self.new_name))

				self.triggerFinish(self.file_path)

				printMessage("Remotely renamed {" + self.basename + "} -> {" + self.new_name + "}", "remotes: " + ','.join(renamed), status=True)


		if len(exists) == 0:
			action()
		else:
			def sync(index):
				if index is 0:
					printMessage("Renaming: overwriting target")
					action(True)
				else:
					printMessage("Renaming: keeping original")

			overwrite = []
			overwrite.append("Overwrite remote file? Already exists in:")
			for remote in exists:
				overwrite.append(remote + " [" + self.config['connections'][name]['host'] + "]")

			cancel = []
			cancel.append("Cancel renaming")
			for remote in exists:
				cancel.append("")

			sublime.set_timeout(lambda: sublime.active_window().show_quick_panel([ overwrite, cancel ], sync), 1)


# Upload command
class SyncCommandDelete(SyncCommandTransfer):

	def __init__(self, file_path, config_file_path, progress=None, onSave=False, disregardIgnore=False, whitelistConnections=[]):
		SyncCommandTransfer.__init__(self, file_path, config_file_path, progress, False, False, whitelistConnections)

	def execute(self):
		if self.closed is True:
			printMessage("Cancelling " + self.getIdentification() + ": command is closed")
			return

		if self.progress is not None:
			self.progress.progress()

		if len(self.config['connections']) == 0:
			printMessage("Cancelling " + self.getIdentification() + ": zero connections apply")
			return

		self._createConnection()
		usingConnections.append(self.config_hash)
		deleted = []
		index = -1

		for name in self.config['connections']:
			index += 1

			try:
				# identification
				connection = self.connections[index]

				# action
				try:
					# process
					connection.delete(self.file_path)
					deleted.append(name)
					printMessage("Deleted {" + self.basename + "}", name)

				except FileNotFoundException:
					deleted.append(name)
					printMessage("No remote version of {" + self.basename + "} found", name)

				except Exception as e:
					printMessage("Delete failed: {" + self.basename + "} [Exception: " + stringifyException(e) + "]", name, False, True)
					handleException(e)

			except IndexError:
				continue

			except FileNotFoundException:
				printMessage("Remote file not found", name, False, True)
				deleted.append(name)
				continue

			except EOFError:
				printMessage("Connection has been terminated, please retry your action", name, False, True)
				self._closeConnection()

			except Exception as e:
				if str(e).find("No such file or directory"):
					printMessage("Remote file not found", name, False, True)
					deleted.append(name)
				else:
					printMessage("Delete failed: {" + self.basename + "} [Exception: " + stringifyException(e) + "]", name, False, True)
					handleException(e)

		if len(deleted) > 0:
			if os.path.exists(self.file_path):
				if os.path.isdir(self.file_path):
					shutil.rmtree(self.file_path)
				else:
					os.remove(self.file_path)

			self.triggerFinish(self.file_path)

			dumpMessage(getProgressMessage(deleted, self.progress, "Deleted", self.basename))


# Rename command
class SyncCommandGetMetadata(SyncCommand):

	def execute(self):
		if self.closed is True:
			printMessage("Cancelling " + self.getIdentification() + ": command is closed")
			return

		if len(self.config['connections']) == 0:
			printMessage("Cancelling " + self.getIdentification() + ": zero connections apply")
			return

		self._createConnection()

		usingConnections.append(self.config_hash)
		index = -1
		results = []

		for name in self.config['connections']:
			index += 1

			try:
				metadata = self.connections[index].list(self.file_path)

				if type(metadata) is list and len(metadata) > 0:
					results.append({
						'connection': name,
						'metadata': metadata[0]
					})

			except IndexError:
				continue

			except FileNotFoundException:
				raise

			except EOFError:
				printMessage("Connection has been terminated, please retry your action", name, False, True)
				self._closeConnection()

			except Exception as e:
				printMessage("Getting metadata failed: {" + self.basename + "} [Exception: " + stringifyException(e) + "]", name, False, True)
				handleException(e)

		return results


def performRemoteCheck(file_path, window, forced = False, whitelistConnections=[]):
	if isString(file_path) is False:
		return

	if window is None:
		return

	basename = os.path.basename(file_path)

	printMessage("Checking {" + basename + "} if up-to-date", status=True)

	config_file_path = getConfigFile(file_path)
	if config_file_path is None:
		return printMessage("Found no config > for file: " + file_path, status=True)

	config = loadConfig(config_file_path)
	try:
		metadata = SyncCommandGetMetadata(file_path, config_file_path)
		if len(whitelistConnections) > 0:
			metadata.whitelistConnections(whitelistConnections)
		metadata = metadata.execute()
	except FileNotFoundException:
		printMessage("Remote file not found", status=True)
		return
	except Exception as e:
		printMessage("Error when getting metadata: " + stringifyException(e))
		handleException(e)
		metadata = []

	if type(metadata) is not list:
		return printMessage("Invalid metadata response, expected list, got " + str(type(metadata)))

	if len(metadata) == 0:
		return printMessage("No version of {" + basename + "} found on any server", status=True)

	newest = []
	oldest = []
	every = []

	for entry in metadata:
		if forced is False and entry['metadata'].isDifferentSizeThan(file_path) is False:
			continue

		if entry['metadata'].isNewerThan(file_path):
			newest.append(entry)
			every.append(entry)
		else:
			oldest.append(entry)

			if entry['metadata'].isDifferentSizeThan(file_path):
				every.append(entry)

	if len(every) > 0:
		every = metadata
		sorted(every, key=lambda entry: entry['metadata'].getLastModified())
		every.reverse()

		connectionCount = len(every)

		def sync(index):
			if index == connectionCount + 1:
				return RemoteSyncCall(file_path, getConfigFile(file_path), True).start()

			if index > 0:
				if isDebug:
					i = 0
					for entry in every:
						printMessage("Listing connection " + str(i) + ": " + str(entry['connection']))
						i += 1

					printMessage("Index selected: " + str(index - 1))

				return RemoteSyncDownCall(file_path, getConfigFile(file_path), True, whitelistConnections=[every[index - 1]['connection']]).start()

		filesize = os.path.getsize(file_path)
		allItems = []
		items = []
		items.append("Keep current " + os.path.basename(file_path))
		items.append("Size: " + str(round(float(os.path.getsize(file_path)) / 1024, 3)) + " kB")
		items.append("Last modified: " + formatTimestamp(os.path.getmtime(file_path)))
		allItems.append(items)
		index = 1

		for item in every:
			item_filesize = item['metadata'].getFilesize()

			if item_filesize == filesize:
				item_filesize = "same size"
			else:
				if item_filesize > filesize:
					item_filesize = str(round(item_filesize / 1024, 3)) + " kB ~ larger"
				else:
					item_filesize = str(round(item_filesize / 1024, 3)) + " kB ~ smaller"

			time = str(item['metadata'].getLastModifiedFormatted(timeFormat))

			if item in newest:
				time += " ~ newer"
			else:
				time += " ~ older"


			items = []
			items.append("Get from " + item['connection'] + " [" + config['connections'][ item['connection'] ]['host'] + "]")
			items.append("Size: " + item_filesize)
			items.append("Last modified: " + time)
			allItems.append(items)
			index += 1

		upload = []
		upload.append("Upload file " + os.path.basename(file_path))
		upload.append("Size: " + str(round(float(os.path.getsize(file_path)) / 1024, 3)) + " kB")
		upload.append("Last modified: " + formatTimestamp(os.path.getmtime(file_path)))
		allItems.append(upload)

		sublime.set_timeout(lambda: window.show_quick_panel(allItems, sync), 1)
	else:
		printMessage("All remote versions of {" + basename + "} are of same size and older", status=True)


class ShowInfo(SyncCommand):

	def execute(self, window):
		if self.closed:
			printMessage("Cancelling " + self.getIdentification() + ": command closed")
			return

		if len(self.config['connections']) == 0:
			printMessage("Cancelling " + self.getIdentification() + ": zero connections apply")
			return

		self._createConnection()

		usingConnections.append(self.config_hash)
		index = -1
		results = []

		for name in self.config['connections']:
			index += 1

			try:
				info = self.connections[index].getInfo()

				if type(info) is dict:
					results.append(info)

			except IndexError:
				continue

			except Exception as e:
				printMessage("Getting info failed [Exception: " + stringifyException(e) + "]", name, False, True)
				handleException(e)

		maxFeats = 0
		for item in results:
			if len(item['features']) > maxFeats:
				maxFeats = len(item['features'])

		output = []
		for item in results:
			if item['config']['tls']:
				encryption = "enabled"
			else:
				encryption = "disabled"

			if item['canEncrypt'] is None:
				encryption += " [unconfirmed]"
			elif item['canEncrypt'] is False:
				encryption += " [NOT SUPPORTED]"
			else:
				encryption += " [SUPPORTED]"

			entry = []
			entry.append(item['name'] + " [" + item['config']['host'] + "]")
			entry.append("Type: " + item['type'])
			entry.append("User: " + item['config']['username'])
			entry.append("Encryption: " + encryption)

			if "MFMT" in item['features']:
				entry.append("Last modified: SUPPORTED")
			else:
				entry.append("Last modified: NOT SUPPORTED")

			entry.append("")
			entry.append("Server features:")

			feats = 0
			for feat in item['features']:
				entry.append(feat)
				feats = feats + 1

			if feats < maxFeats:
				for i in range(1, maxFeats - feats):
					entry.append("")

			output.append(entry)

		sublime.set_timeout(lambda: window.show_quick_panel(output, None), 1)


class SyncNavigator(SyncCommand):

	def __init__(self, file_path, config_file_path, connection_name = None, path = None, remotePath = None):
		self.configConnection = None
		self.configName = None
		self.files = []
		self.defaultPath = path
		self.defaultRemotePath = remotePath

		SyncCommand.__init__(self, None, config_file_path)

		if connection_name is not None:
			self.selectConnection(connection_name)

	def execute(self):
		if self.closed is True:
			printMessage("Cancelling " + self.getIdentification() + ": command is closed")
			return

		if len(self.config['connections']) == 0:
			printMessage("Cancelling " + self.getIdentification() + ": zero connections apply")
			return

		usingConnections.append(self.config_hash)
		index = -1
		results = []

		if len(self.config['connections']) > 1 and self.configConnection is None:
			self.listConnections()
		else:
			if self.configConnection is None:
				for name in self.config['connections']:
					self.selectConnection(name)

			if self.defaultPath:
				self.listFiles(self.defaultPath)
			elif self.defaultRemotePath:
				self.listFiles(self.defaultRemotePath, True)

	def listConnections(self):
		connections = []
		names = []

		for name in self.config['connections']:
			connection = self.config['connections'][name]
			connections.append([ name, "Host: " + connection['host'], "Path: " + connection['path'] ])
			names.append(name)

		def handleConnectionSelection(index):
			if index == -1:
				return

			self.selectConnection(names[index])
			self.listFiles(self.defaultPath)

		sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(connections, handleConnectionSelection), 1)

	def selectConnection(self, name):
		self.configConnection = self.config['connections'][name]
		self.configName = name
		self.config['connections'] = {}
		self.config['connections'][name] = self.configConnection

	def updateNavigateLast(self, path):
		navigateLast['config_file'] = self.config_file_path
		navigateLast['connection_name'] = self.configName
		navigateLast['path'] = path

	def listFiles(self,path=None,forced=False):
		if self.closed is True:
			printMessage("Cancelling " + self.getIdentification() + ": command is closed")
			return

		self._createConnection()
		connection = self.connections[0]

		remote = True
		if path is None or path == self.defaultPath or self.defaultPath is None:
			remote = False
		if path is None:
			path = os.path.dirname(self.config_file_path)
		if forced:
			remote = True

		self.updateNavigateLast(path)

		contents = connection.list(path, remote, True)
		contents = addLinks(contents)
		contents = sorted(contents, key = lambda entry: (entry.getName() != "..", entry.isDirectory() is False, entry.getName().lower()))

		content = []
		for meta in contents:
			entry = []

			if meta.isDirectory():
				if meta.getName() == '..' and connection.getNormpath(path) == '/':
					continue

				entry.append("[ " + decode(meta.getName()) + " ]")
				entry.append("Directory")
			else:
				entry.append(decode(meta.getName()))
				entry.append("Size: " + meta.getHumanFilesize())

			entry.append("Last modified: " + meta.getLastModifiedFormatted(displayTimestampFormat))

			if displayPermissions:
				entry.append("Permissions: " + meta.getPermissions())

			entry.append("Path: " + meta.getPath())
			content.append(entry)
			self.files.append(meta)
		if len(contents) == 0:
			printMessage("No files found in remote path for local {" + str(path) + "}", status=True)

		def handleMetaSelection(index):
			if index == -1:
				return

			meta = self.files[index]
			self.files = []

			if meta.isDirectory():
				self.listFolderActions(meta)
			else:
				self.listFileActions(meta)

		sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(content, handleMetaSelection), 1)

	def listFolderActions(self, meta, action = None):
		if self.closed is True:
			printMessage("Cancelling " + self.getIdentification() + ": command is closed")
			return

		self._createConnection()
		connection = self.connections[0]
		path = meta.getPath()
		localFile = connection.getLocalPath( str(meta.getPath() + '/' + meta.getName()).replace('/.',''), os.path.dirname(self.config_file_path))
		exists = 0

		name = meta.getName()
		if name == '.':
			split = re_thisFolder.search(meta.getPath())
			if split is not None:
				name = split.group(1)
		if name == '..':
			split = re_parentFolder.search(meta.getPath())
			if split is not None:
				name = split.group(1)
			else:
				name = '/'

		actions = []
		actions.append("Open " + decode(name))
		actions.append("Back")
		actions.append("Download folder")

		if os.path.exists(localFile):
			actions.append("Upload folder")
			exists = 1

		actions.append("Remove folder")
		actions.append("Rename folder")
		actions.append("Change permissions")
		actions.append("Show details")
		actions.append("Copy path")

		def handleAction(index):
			if index == -1:
				return

			if index == 0:
				self.listFiles(meta.getPath() + '/' + meta.getName())
				return

			if index == 1:
				self.listFiles(meta.getPath())
				return

			if index == 2:
				call = RemoteSyncDownCall([[localFile, getConfigFile(localFile)]], None, False, True)
				call.setIsDir()
				call.start()
				return

			if exists and index == 3:
				RemoteSyncCall(gatherFiles([localFile]), None, False, True).start()
				return

			if index == 3 + exists:
				RemoteSyncDelete(localFile).start()
				return

			if index == 4 + exists:
				try:
					sublime.active_window().run_command("ftp_sync_rename", { "paths": [ localFile ] })
				except Exception as e:
					handleException(e)
				return

			if index == 5 + exists:
				def permissions(newPermissions):
					self._createConnection()
					connection = self.connections[0]
					connection.cwd(meta.getPath())
					connection.chmod(meta.getName(), newPermissions)

					printMessage("Properties of " + meta.getName() + " changed to " + newPermissions, status=True)

				sublime.active_window().show_input_panel('Change permissions to:', self.configConnection['default_folder_permissions'], permissions, None, None)

			if index == 6 + exists:
				info = []
				info.append(meta.getName())
				info.append("[Directory]")
				info.append("Path: " + str(meta.getPath())[len(self.configConnection['path']):] + '/' + meta.getName().replace('/./', '/'))
				info.append("Permissions: " + meta.getPermissions() + " (" + meta.getPermissionsNumeric() + ")")
				if connection.hasTrueLastModified():
					info.append("Last Modified: " + meta.getLastModifiedFormatted())
				else:
					info.append("Last upload time: " + meta.getLastModifiedFormatted())

				info.append("")
				if os.path.exists(localFile):
					info.append("[Has local version]")
					info.append("Local last modified: " + formatTimestamp(os.path.getmtime(localFile), displayTimestampFormat))
					if sublime.platform() == 'windows':
						info.append("Local created: " + formatTimestamp(os.path.getctime(localFile), displayTimestampFormat))
				else:
					info.append("[No local version]")

				sublime.set_timeout(lambda: sublime.active_window().show_quick_panel([info], None), 1)
				return

			if index == 7 + exists:
				get_path = meta.getPath()
				sublime.set_clipboard(get_path)
				return


		if action is None:
			sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(actions, handleAction), 1)
		else:
			handleAction(action)

	def listFileActions(self, meta, action = None):
		if self.closed is True:
			printMessage("Cancelling " + self.getIdentification() + ": command is closed")
			return

		path = meta.getPath() + '/' + meta.getName()
		self._createConnection()
		connection = self.connections[0]
		localFile = connection.getLocalPath(meta.getPath() + '/' + meta.getName(), os.path.dirname(self.config_file_path))

		exists = 0
		hasSidebar = packageExists("SideBarEnhancements")

		actions = []
		actions.append("Back")
		actions.append("Download file")

		if os.path.exists(localFile):
			actions.append("Upload file")
			exists = 1

		actions.append("Remove file")
		actions.append("Rename file")

		if hasSidebar:
			actions.append("Open / run")

		actions.append("Change permissions")
		actions.append("Show details")

		def handleAction(index):
			if index == -1:
				return

			if index == 0:
				self.listFiles(meta.getPath())
				return

			if index == 1:
				def dopen(args):
					try:
						sublime.set_timeout(lambda: sublime.active_window().open_file(args), 1)
					except Exception as e:
						handleException(e)

				call = RemoteSyncDownCall(localFile, getConfigFile(self.config_file_path), False, True)
				if settings.get('browse_open_on_download'):
					call.onFinish(dopen)
				call.start()
				return

			if exists and index == 2:
				RemoteSyncCall(gatherFiles([localFile]), None, True, True).start()
				return

			if index == 2 + exists:
				RemoteSyncDelete(localFile).start()
				return

			if index == 3 + exists:
				try:
					sublime.active_window().run_command("ftp_sync_rename", { "paths": [ localFile ] })
				except Exception as e:
					handleException(e)
				return

			if hasSidebar and index == 4 + exists:
				def openRun(args):
					sublime.set_timeout(lambda: sublime.active_window().run_command("side_bar_open", {"paths": [ args ]}), 1)

				# download
				call = RemoteSyncCall(gatherFiles([localFile]), None, False, True)
				call.onFinish(openRun)
				call.start()
				return

			if index == 4 + exists + int(hasSidebar):
				def permissions(newPermissions):
					self._createConnection()
					connection = self.connections[0]
					connection.cwd(meta.getPath())
					connection.chmod(meta.getName(), newPermissions)

					printMessage("Properties of " + meta.getName() + " changed to " + newPermissions, status=True)

				sublime.active_window().show_input_panel('Change permissions to:', self.configConnection['default_folder_permissions'], permissions, None, None)
				return

			if index == 5 + exists + int(hasSidebar):
				info = []
				info.append(meta.getName())
				info.append("[File]")
				info.append("Path: " + str(meta.getPath())[len(self.configConnection['path']):] + '/' + meta.getName().replace('/./', '/'))
				info.append("Size: " + str(round(meta.getFilesize()/1024,3)) + " kB")
				info.append("Permissions: " + meta.getPermissions() + " (" + meta.getPermissionsNumeric() + ")")
				if connection.hasTrueLastModified():
					info.append("Last Modified: " + meta.getLastModifiedFormatted())
				else:
					info.append("Last upload time: " + meta.getLastModifiedFormatted())

				info.append("")
				if os.path.exists(localFile):
					info.append("[Has local version]")
					info.append("Local size: " + str(round(float(os.path.getsize(localFile)) / 1024, 3)) + " kB")
					info.append("Local last modified: " + formatTimestamp(os.path.getmtime(localFile), displayTimestampFormat))
					if sublime.platform() == 'windows':
						info.append("Local created: " + formatTimestamp(os.path.getctime(localFile), displayTimestampFormat))
				else:
					info.append("[No local version]")

				sublime.set_timeout(lambda: sublime.active_window().show_quick_panel([info], None), 1)
				return

			if index == 6 + exists + int(hasSidebar):
				get_path = meta.getPath()
				sublime.set_clipboard(get_path)
				return

		if action is None:
			sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(actions, handleAction), 1)
		else:
			handleAction(actions)



# ==== Watching ===========================================================================

# list of file paths to be checked on load
checksScheduled = []
# pre_save x post_save upload prevention
preventUpload = []


# File watching
class RemoteSync(sublime_plugin.EventListener):

	def on_pre_save(self, view):
		file_path = getFileName(view)
		config_file_path = getConfigFile(file_path)
		if config_file_path is None:
			return

		def pre_save(_files):
			window = view.window()
			if window is None:
				window = sublime.active_window()

			RemotePresave(file_path, fileToMetafile(file_path), config_file_path, _files, view, window, self.manual_on_post_save).start()

		fillPasswords([[ None, config_file_path ]], pre_save, sublime.active_window())

	def manual_on_post_save(self, file_path):
		config_file_path = getConfigFile(file_path)

		command = RemoteSyncCall(file_path, config_file_path, True)

		if config_file_path in preScan and preScan[config_file_path] is not None:
			command.setPreScan(preScan[config_file_path])

		command.start()

	def on_close(self, view):
		file_path = getFileName(view)

		if file_path is None:
			return

		config_file_path = getConfigFile(file_path)

		if file_path in checksScheduled:
			checksScheduled.remove(file_path)

		if config_file_path is not None:
			closeConnection(getFilepathHash(config_file_path))

	# When a file is loaded and at least 1 connection has download_on_open enabled
	# it will check those enabled if the remote version is newer and offers the newest to download
	def on_load(self, view):
		file_path = getFileName(view)

		if ignore is not None and re_ignore is not None and re_ignore.search(file_path) is not None:
			return

		if view not in checksScheduled:
			checksScheduled.append(file_path)

			def check():
				if file_path in checksScheduled:

					def execute(files):
						whitelistConnections = []

						config_file_path = getConfigFile(file_path)
						if config_file_path is None:
							return printMessage("Config not found for: " + file_path)

						config = loadConfig(config_file_path)
						for name in config['connections']:
							if config['connections'][name]['download_on_open'] is True:
								whitelistConnections.append(name)

						RemoteSyncCheck(file_path, view.window(), forced=False, whitelistConnections=whitelistConnections).start()

					fillPasswords([[ file_path, getConfigFile(file_path) ]], execute, sublime.active_window())

			sublime.set_timeout(check, downloadOnOpenDelay)


# ==== Threading ===========================================================================

def fillProgress(progress, entry):
	if len(entry) == 0:
		return

	if isString(entry[0]):
		entry = entry[0]

	if type(entry) is list:
		for item in entry:
			fillProgress(progress, item)
	else:
		progress.add([entry])


class RemoteThread(threading.Thread):

	def __init__(self):
		threading.Thread.__init__(self)
		self.preScan = None
		self._whitelistConnetions = []
		self._onFinish = None

	def setPreScan(self, preScan):
		self.preScan = preScan

	def addPreScan(self, command):
		if self.preScan is not None:
			for name in self.preScan:
				command.setScanned('before', name, self.preScan[name])

	def setWhitelistConnections(self, whitelistConnections):
		self._whitelistConnetions = whitelistConnections

	def addWhitelistConnections(self, command):
		if hasattr(self, '_whitelistConnections'):
			command.whitelistConnections(self._whitelistConnetions)

		return command

	def onFinish(self, callback):
		self._onFinish = callback

	def getOnFinish(self):
		if hasattr(self, '_onFinish'):
			return self._onFinish
		else:
			return None


class RemotePresave(RemoteThread):
	def __init__(self, file_path, metafile, config_file_path, _files, view, window, callback):
		self.file_path = file_path
		self.metafile = metafile
		self.config_file_path = config_file_path
		self._files = _files
		self.view = view
		self.window = window
		self.callback = callback
		RemoteThread.__init__(self)

	def run(self):
		_files = self._files
		file_path = self.file_path
		config_file_path = self.config_file_path
		view = self.view
		preScan[config_file_path] = {}
		root = os.path.dirname(config_file_path)
		config = loadConfig(config_file_path)
		blacklistConnections = []

		for connection in config['connections']:
			properties = config['connections'][connection]

			if properties['upload_on_save'] is False:
				blacklistConnections.append(connection)

			watch = properties['after_save_watch']
			if type(watch) is list and len(watch) > 0 and properties['upload_delay'] > 0:
				preScan[config_file_path][connection] = {}

				for folder, filepattern in watch:
					files = gatherMetafiles(filepattern, os.path.join(root, folder))
					preScan[config_file_path][connection].update(files.items())

				if properties['debug_extras']['after_save_watch']:
					printMessage("<debug> dumping pre-scan")
					print ("COUNT: " + str(len(preScan[config_file_path][connection])))
					for change in preScan[config_file_path][connection]:
						print ("Path: " + preScan[config_file_path][connection][change].getPath() + " | Name: " + preScan[config_file_path][connection][change].getName())

		if len(blacklistConnections) == len(config['connections']):
			return

		try:
			metadata = SyncCommandGetMetadata(file_path, config_file_path).execute()
		except FileNotFoundException:
			return
		except Exception as e:
			if str(e).find('No such file'):
				printMessage("No version of {" + os.path.basename(file_path) + "} found on any server", status=True)
			else:
				printMessage("Error when getting metadata: " + stringifyException(e))
				handleException(e)
			metadata = []

		newest = None
		newer = []
		index = 0

		for entry in metadata:
			properties = config['connections'][entry['connection']]

			if 'debug_overwrite_prevention' in properties['debug_extras'] and properties['debug_extras']['debug_overwrite_prevention']:
				printMessage("<debug> dumping overwrite prevention")
				print ("File [local]: " + str(file_path))
				print ("File [remote]: " + str(entry['metadata'].getPath()))
				print ("Enabled: " + str(properties['check_time'] is True))
				print ("Not in blacklist: " + str(entry['connection'] not in blacklistConnections))
				print ("Is remote newer: " + str(entry['metadata'].isNewerThan(self.metafile)))
				print ("Is size different: " + str(entry['metadata'].isDifferentSizeThan(file_path)))
				print ("In overwrite cancelled: " + str(file_path in overwriteCancelled))
				print ("+ [remote] last modified: " + str(entry['metadata'].getLastModified()))
				print ("+ [local] last modified: " + str(self.metafile.getLastModified()))
				print ("+ [remote] size: " + str(entry['metadata'].getFilesize()))
				print ("+ [local] size: " + str(os.path.getsize(file_path)))

			if (entry['connection'] not in blacklistConnections and properties['check_time'] is True and entry['metadata'].isNewerThan(self.metafile) and entry['metadata'].isDifferentSizeThan(file_path)) or file_path in overwriteCancelled:
				newer.append(entry['connection'])

				if newest is None or newest > entry['metadata'].getLastModified():
					newest = index

			index += 1

		if len(newer) > 0:
			preventUpload.append(file_path)

			def sync(index):
				if index is 0:
					printMessage("Overwrite prevention: overwriting")

					if file_path in overwriteCancelled:
						overwriteCancelled.remove(file_path)

					self.callback(self.file_path)
				else:
					printMessage("Overwrite prevention: cancelled upload")

					if file_path not in overwriteCancelled:
						overwriteCancelled.append(file_path)

			yes = []
			yes.append("Yes, overwrite newer")
			yes.append("Last modified: " + metadata[newest]['metadata'].getLastModifiedFormatted())

			for entry in newer:
				yes.append(entry + " [" + config['connections'][entry]['host'] + "]")

			no = []
			no.append("No")
			no.append("Cancel uploading")

			for entry in newer:
				no.append("")

			sublime.set_timeout(lambda: self.window.show_quick_panel([ yes, no ], sync), 1)
		else:
			self.callback(self.file_path)


class RemoteSyncCall(RemoteThread):
	def __init__(self, file_path, config, onSave, disregardIgnore=False, whitelistConnections=[], forcedSave=False):
		self.file_path = file_path
		self.config = config
		self.onSave = onSave
		self.forcedSave = forcedSave
		self.disregardIgnore = disregardIgnore
		self.whitelistConnections = whitelistConnections
		RemoteThread.__init__(self)

	def run(self):
		target = self.file_path

		if isString(target) and self.config is None:
			return False

		elif isString(target):
			command = SyncCommandUpload(target, self.config, onSave=self.onSave, disregardIgnore=self.disregardIgnore, whitelistConnections=self.whitelistConnections, forcedSave=self.forcedSave)
			command.addOnFinish(self.getOnFinish())
			self.addWhitelistConnections(command)
			self.addPreScan(command)
			command.execute()

		elif type(target) is list and len(target) > 0:
			progress = Progress()
			fillProgress(progress, target)

			queue = createWorker()

			for file_path, config in target:
				command = SyncCommandUpload(file_path, config, progress=progress, onSave=self.onSave, disregardIgnore=self.disregardIgnore, whitelistConnections=self.whitelistConnections, forcedSave=self.forcedSave)
				command.addOnFinish(self.getOnFinish())
				self.addWhitelistConnections(command)
				self.addPreScan(command)

				if workerLimit > 1:
					queue.addCommand(command, config)
				else:
					command.execute()


class RemoteSyncDownCall(RemoteThread):
	def __init__(self, file_path, config, disregardIgnore=False, forced=False, whitelistConnections=[]):
		self.file_path = file_path
		self.config = config
		self.disregardIgnore = disregardIgnore
		self.forced = forced
		self.whitelistConnections = []
		self.isDir = False
		RemoteThread.__init__(self)

	def setIsDir(self):
		self.isDir = True

	def run(self):
		target = self.file_path

		if isString(target) and self.config is None:
			return False

		elif isString(target):
			queue = createWorker()

			command = SyncCommandDownload(target, self.config, disregardIgnore=self.disregardIgnore, whitelistConnections=self.whitelistConnections)
			command.addOnFinish(self.getOnFinish())
			self.addWhitelistConnections(command)

			if self.isDir:
				command.setIsDir()

			if self.forced:
				command.setForced()

			if workerLimit > 1:
				command.setWorker(queue)
				queue.addCommand(command, self.config)
			else:
				command.execute()
		elif type(target) is list and len(target) > 0:
			total = len(target)
			progress = Progress(total)
			queue = createWorker()

			for file_path, config in target:
				if os.path.isfile(file_path):
					progress.add([file_path])

				command = SyncCommandDownload(file_path, config, disregardIgnore=self.disregardIgnore, progress=progress, whitelistConnections=self.whitelistConnections)
				command.addOnFinish(self.getOnFinish())
				self.addWhitelistConnections(command)

				if self.isDir:
					command.setIsDir()

				if self.forced:
					command.setForced()

				if workerLimit > 1:
					command.setWorker(queue)
					queue.addCommand(command, config)
				else:
					command.execute()


class RemoteSyncRename(RemoteThread):
	def __init__(self, file_path, config, new_name):
		self.file_path = file_path
		self.new_name = new_name
		self.config = config
		RemoteThread.__init__(self)

	def run(self):
		self.addWhitelistConnections(SyncCommandRename(self.file_path, self.config, self.new_name).addOnFinish(self.getOnFinish())).execute()


class RemoteSyncCheck(RemoteThread):
	def __init__(self, file_path, window, forced=False, whitelistConnections=[]):
		self.file_path = file_path
		self.window = window
		self.forced = forced
		self.whitelistConnections = whitelistConnections
		RemoteThread.__init__(self)

	def run(self):
		performRemoteCheck(self.file_path, self.window, self.forced, self.whitelistConnections)


class RemoteSyncDelete(RemoteThread):
	def __init__(self, file_paths):
		self.file_path = file_paths
		RemoteThread.__init__(self)

	def run(self):
		target = self.file_path

		if isString(target):
			self.file_path = [ target ]

		def sync(index):
			if index is 0:
				self.delete()
			else:
				printMessage("Deleting: cancelled")

		yes = []
		yes.append("Yes, delete the selected items [also remotely]")
		for entry in self.file_path:
			yes.append( getRootPath(entry, '/') )

		no = []
		no.append("No")
		no.append("Cancel deletion")

		for entry in self.file_path:
			if entry == self.file_path[0]:
				continue

			no.append("")

		sublime.set_timeout(lambda: sublime.active_window().show_quick_panel([yes, no], sync), 1)

	def delete(self):
		target = self.file_path
		progress = Progress()
		fillProgress(progress, target)

		for file_path in target:
			command = SyncCommandDelete(file_path, getConfigFile(file_path), progress=progress, onSave=False, disregardIgnore=False, whitelistConnections=[])
			self.addWhitelistConnections(command)
			command.addOnFinish(self.getOnFinish())
			command.execute()


class RemoteNavigator(RemoteThread):
	def __init__(self, config, last = False):
		self.config = config
		self.last = last
		self.command = None
		RemoteThread.__init__(self)

	def setCommand(self, command):
		self.command = command

	def run(self):
		if self.command is None:
			if self.last is True:
				command = SyncNavigator(None, navigateLast['config_file'], navigateLast['connection_name'], None, navigateLast['path'])
			else:
				command = SyncNavigator(None, self.config)
		else:
			command = self.command

		self.addWhitelistConnections(command)
		command.execute()


# ==== Commands ===========================================================================

# Sets up a config file in a directory
class FtpSyncNewSettings(sublime_plugin.WindowCommand):
	def run(self, edit = None, dirs = []):
		if len(dirs) == 0:
			if sublime.active_window() is not None and sublime.active_window().active_view() is not None:
				dirs = [os.path.dirname(sublime.active_window().active_view().file_name())]
			elif sublime.active_window() is not None:
				sublime.active_window().show_input_panel('Enter setup path', '', self.create, None, None)
				return
			else:
				printMessage("Cannot setup file - no folder path selected and no active view (opened file) detected")
				return

		self.create(dirs)

	def create(self, dirs):
		if type(dirs) is Types.text:
			dirs = [dirs]

		for file_path in dirs:
			if os.path.exists(file_path) is False:
				printMessage("Setup: file path does not exist: " + file_path)
				return

		if sublime.version()[0] >= '3':
			content = sublime.load_resource('Packages/FTPSync/ftpsync.default-settings').replace('\r\n', '\n')

			for directory in dirs:
				config = os.path.join(directory, configName)

				if os.path.exists(config) is False:
					with open(config, 'w') as configFile:
						printMessage("Settings file created in: " + config)
						configFile.write(content)

				self.window.open_file(config)
		else:
			default = os.path.join(sublime.packages_path(), 'FTPSync', connectionDefaultsFilename)
			if os.path.exists(default) is False:
				printMessage("Could not find default settings file in {" + default + "}")

				default = os.path.join(__dir__, connectionDefaultsFilename)
				printMessage("Trying filepath {" + default + "}")

			for directory in dirs:
				config = os.path.join(directory, configName)

				invalidateConfigCache(directory)

				if os.path.exists(config) is False:
					printMessage("Settings file created in: " + config)
					shutil.copyfile(default, config)

				self.window.open_file(config)


# Synchronize up selected file/directory
class FtpSyncTarget(sublime_plugin.WindowCommand):
	def run(self, edit, paths):
		def execute(files):
			RemoteSyncCall(files, None, False).start()

		files = gatherFiles(paths)
		fillPasswords(files, execute, sublime.active_window())

# Synchronize up selected file/directory with delay and watch
class FtpSyncTargetDelayed(sublime_plugin.WindowCommand):
	def run(self, edit, paths):
		def execute(files):
			RemoteSyncCall(files, None, True, forcedSave = True).start()

		files = gatherFiles(paths)
		fillPasswords(files, execute, sublime.active_window())


# Synchronize up current file
class FtpSyncCurrent(sublime_plugin.TextCommand):
	def run(self, edit):
		file_path = sublime.active_window().active_view().file_name()

		def execute(files):
			RemoteSyncCall(files[0][0], files[0][1], False).start()

		fillPasswords([[ file_path, getConfigFile(file_path) ]], execute, sublime.active_window())


# Synchronize down current file
class FtpSyncDownCurrent(sublime_plugin.TextCommand):
	def run(self, edit):
		file_path = sublime.active_window().active_view().file_name()

		def execute(files):
			RemoteSyncDownCall(files[0][0], files[0][1], True, False).start()

		fillPasswords([[ file_path, getConfigFile(file_path) ]], execute, sublime.active_window())


# Checks whether there's a different version of the file on server
class FtpSyncCheckCurrent(sublime_plugin.TextCommand):
	def run(self, edit):
		file_path = sublime.active_window().active_view().file_name()
		view = sublime.active_window()

		def execute(files):
			RemoteSyncCheck(file_path, view, True).start()

		fillPasswords([[ file_path, getConfigFile(file_path) ]], execute, sublime.active_window())

# Checks whether there's a different version of the file on server
class FtpSyncRenameCurrent(sublime_plugin.TextCommand):
	def run(self, edit):
		view = sublime.active_window()

		self.original_path = sublime.active_window().active_view().file_name()
		self.folder = os.path.dirname(self.original_path)
		self.original_name = os.path.basename(self.original_path)

		if self.original_path in checksScheduled:
			checksScheduled.remove(self.original_path)

		view.show_input_panel('Enter new name', self.original_name, self.rename, None, None)

	def rename(self, new_name):
		def action():
			def execute(files):
				RemoteSyncRename(self.original_path, getConfigFile(self.original_path), new_name).start()

			fillPasswords([[ self.original_path, getConfigFile(self.original_path) ]], execute, sublime.active_window())

		new_path = os.path.join(os.path.dirname(self.original_path), new_name)
		if os.path.exists(new_path):
			def sync(index):
				if index is 0:
					printMessage("Renaming: overwriting local target")
					action()
				else:
					printMessage("Renaming: keeping original")

			overwrite = []
			overwrite.append("Overwrite local file? Already exists in:")
			overwrite.append("Path: " + new_path)

			cancel = []
			cancel.append("Cancel renaming")

			sublime.set_timeout(lambda: sublime.active_window().show_quick_panel([ overwrite, cancel ], sync), 1)
		else:
			action()


# Synchronize down selected file/directory
class FtpSyncDownTarget(sublime_plugin.WindowCommand):
	def run(self, edit, paths, forced=False):
		filelist = []
		for path in paths:
			filelist.append( [ path, getConfigFile(path) ] )

		def execute(files):
			RemoteSyncDownCall(filelist, None, forced=forced).start()

		fillPasswords(filelist, execute, sublime.active_window())


# Renames a file on disk and in folder
class FtpSyncRename(sublime_plugin.WindowCommand):
	def run(self, edit, paths):
		self.original_path = paths[0]
		self.folder = os.path.dirname(self.original_path)
		self.original_name = os.path.basename(self.original_path)

		if self.original_path in checksScheduled:
			checksScheduled.remove(self.original_path)

		self.window.show_input_panel('Enter new name', self.original_name, self.rename, None, None)

	def rename(self, new_name):
		def action():
			def execute(files):
				RemoteSyncRename(self.original_path, getConfigFile(self.original_path), new_name).start()

			fillPasswords([[ self.original_path, getConfigFile(self.original_path) ]], execute, sublime.active_window())

		new_path = os.path.join(os.path.dirname(self.original_path), new_name)
		if os.path.exists(new_path):
			def sync(index):
				if index is 0:
					printMessage("Renaming: overwriting local target")
					action()
				else:
					printMessage("Renaming: keeping original")

			overwrite = []
			overwrite.append("Overwrite local file? Already exists in:")
			overwrite.append("Path: " + new_path)

			cancel = []
			cancel.append("Cancel renaming")
			cancel.append("")

			sublime.set_timeout(lambda: sublime.active_window().show_quick_panel([ overwrite, cancel ], sync), 1)
		else:
			action()


# Removes given file(s) or folders
class FtpSyncDelete(sublime_plugin.WindowCommand):
	def run(self, edit, paths):
		filelist = []
		for path in paths:
			filelist.append( [ path, getConfigFile(path) ] )

		def execute(files):
			RemoteSyncDelete(paths).start()

		fillPasswords(filelist, execute, sublime.active_window())

# Remote ftp navigation
class FtpSyncBrowse(sublime_plugin.WindowCommand):
	def run(self, edit):
		file_path = os.path.dirname(sublime.active_window().active_view().file_name())

		def execute(files):
			command = SyncNavigator(None, getConfigFile(file_path), None, file_path)
			call = RemoteNavigator(getConfigFile(file_path))
			call.setCommand(command)
			call.start()

		fillPasswords([[ file_path, getConfigFile(file_path) ]], execute, sublime.active_window())

# Remote ftp navigation
class FtpSyncBrowsePlace(sublime_plugin.WindowCommand):
	def run(self, edit, paths):
		if os.path.isdir(paths[0]):
			file_path = paths[0]
		else:
			file_path = os.path.dirname(paths[0])

		def execute(files):
			command = SyncNavigator(None, getConfigFile(file_path), None, file_path)
			call = RemoteNavigator(getConfigFile(file_path))
			call.setCommand(command)
			call.start()

		fillPasswords([[ file_path, getConfigFile(file_path) ]], execute, sublime.active_window())

# Remote ftp navigation from current file
class FtpSyncBrowseCurrent(sublime_plugin.TextCommand):
	def run(self, edit):
		file_path = sublime.active_window().active_view().file_name()

		def execute(files):
			command = SyncNavigator(os.path.dirname(file_path), getConfigFile(file_path), None, os.path.dirname(file_path))
			call = RemoteNavigator(getConfigFile(file_path))
			call.setCommand(command)
			call.start()

		fillPasswords([[ file_path, getConfigFile(file_path) ]], execute, sublime.active_window())

# Remote ftp navigation from last point
class FtpSyncBrowseLast(sublime_plugin.WindowCommand):
	def run(self, edit):
		if navigateLast['config_file'] is None:
			file_path = sublime.active_window().active_view().file_name()

			def execute(files):
				command = SyncNavigator(None, getConfigFile(file_path), None, file_path)
				call = RemoteNavigator(getConfigFile(file_path))
				call.setCommand(command)
				call.start()


			fillPasswords([[ file_path, getConfigFile(file_path) ]], execute, sublime.active_window())
		else:
			def execute(files):
				RemoteNavigator(None, True).start()

			fillPasswords([[ None, getConfigFile(navigateLast['config_file']) ]], execute, sublime.active_window())

# Show connection info
class FtpSyncShowInfo(sublime_plugin.WindowCommand):
	def run(self, edit, paths):
		file_path = paths[0]

		def execute(files):
			ShowInfo(None, getConfigFile(file_path)).execute(sublime.active_window())

		fillPasswords([[ file_path, getConfigFile(file_path) ]], execute, sublime.active_window())

# Open FTPSync Github page
class FtpSyncUrlReadme(sublime_plugin.WindowCommand):
	def run(self):
		webbrowser.open("https://github.com/NoxArt/SublimeText2-FTPSync", 2, True)

# Open FTPSync Github New Issue page
class FtpSyncUrlReport(sublime_plugin.WindowCommand):
	def run(self):
		webbrowser.open("https://github.com/NoxArt/SublimeText2-FTPSync/issues/new", 2, True)

# Open FTPSync Donate page
class FtpSyncUrlDonate(sublime_plugin.WindowCommand):
	def run(self):
		webbrowser.open("http://ftpsync.noxart.cz/donate.html", 2, True)

# Base class for option toggling
class FTPSyncToggleSettings(sublime_plugin.TextCommand):

	def run(self, edit):
		config_file_path = getConfigFile(self.view.file_name())
		if config_file_path is None:
			return printMessage("No config file found")

		overrideConfig(config_file_path, self.property_name, self.property_value_from)

	def is_visible(self):
		if self.view is None or self.view.file_name() is None:
			return False

		config_file_path = getConfigFile(self.view.file_name())
		if config_file_path is None:
			return False

		config = loadConfig(config_file_path)

		for name in config['connections']:
			if config['connections'][name]['upload_on_save'] is self.property_value_to:
				return True

		return False

# Alters overrideConfig to enable upload_on_save
class FtpSyncEnableUos(FTPSyncToggleSettings):
	property_name = 'upload_on_save'
	property_value_from = True
	property_value_to = False

# Alters overrideConfig to disable upload_on_save
class FtpSyncDisableUos(FTPSyncToggleSettings):
	property_name = 'upload_on_save'
	property_value_from = False
	property_value_to = True

class FtpSyncCleanup(sublime_plugin.WindowCommand):
	def run(self, edit, paths):
		self.files = []
		for path in paths:
			self.files.extend(gatherMetafiles('*.ftpsync.temp', path))

		self.prompt()

	def prompt(self):
		if len(self.files) == 0:
			printMessage("No temporary files found")
			return

		toRemove = []
		toRemove.append("Remove these temporary files?")
		for path in self.files:
			toRemove.append(os.path.join(os.path.dirname(path), os.path.basename(path)))

		cancel = []
		cancel.append("Cancel removal")
		for path in self.files:
			cancel.append("")

		sublime.set_timeout(lambda: sublime.active_window().show_quick_panel([ toRemove, cancel ], self.remove), 1)

	def remove(self, index):
		if hasattr(self, 'files') and index == 0:
			for path in self.files:
				os.remove(path)
				printMessage("Removed tempfile: " + path)


########NEW FILE########
__FILENAME__ = ftpsynccommon
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Jiri "NoxArt" Petruzelka
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# @author Jiri "NoxArt" Petruzelka | petruzelka@noxart.cz | @NoxArt
# @copyright (c) 2012 Jiri "NoxArt" Petruzelka
# @link https://github.com/NoxArt/SublimeText2-FTPSync

from __future__ import unicode_literals

import codecs
import inspect
import sys

class Runtime(object):

	@staticmethod
	def getCaller(up = 0):
		return inspect.stack()[2 + up][3]


class Types(object):
	if sys.version < '3':
		text = unicode
		binary = str
	else:
		text = str
		binary = bytes

	@staticmethod
	def u(string):
		if sys.version < '3':
			return codecs.unicode_escape_decode(string)[0]
		else:
			return string

########NEW FILE########
__FILENAME__ = ftpsyncexceptions
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Jiri "NoxArt" Petruzelka
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# @author Jiri "NoxArt" Petruzelka | petruzelka@noxart.cz | @NoxArt
# @copyright (c) 2012 Jiri "NoxArt" Petruzelka
# @link https://github.com/NoxArt/SublimeText2-FTPSync

# Doc comment syntax inspired by http://stackoverflow.com/a/487203/387503

class FileNotFoundException(Exception):
    pass
########NEW FILE########
__FILENAME__ = ftpsyncfiles
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Jiri "NoxArt" Petruzelka
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# @author Jiri "NoxArt" Petruzelka | petruzelka@noxart.cz | @NoxArt
# @copyright (c) 2012 Jiri "NoxArt" Petruzelka
# @link https://github.com/NoxArt/SublimeText2-FTPSync

# ==== Libraries ===========================================================================

# Python's built-in libraries
import datetime
import fnmatch
import os
import re
import sys
import tempfile

# FTPSync libraries
if sys.version < '3':
    from ftpsynccommon import Types
else:
    from FTPSync.ftpsynccommon import Types


# ==== Initialization and optimization =====================================================

# limit for breaking down a filepath structure when looking for config files
nestingLimit = 30

# permission triples
triples = {
	'---': 0,
	'--x': 1,
	'--s': 1,
	'--t': 1,
	'-w-': 2,
	'-wx': 3,
	'-ws': 3,
	'-wt': 3,
	'r--': 4,
	'r-x': 5,
	'r-s': 5,
	'r-t': 5,
	'rw-': 6,
	'rwx': 7,
	'rws': 7,
	'rwt': 7,
}



# ==== Content =============================================================================

# Returns whether the variable is some form os string
def isString(var):
	var_type = type(var)

	if sys.version[0] == '3':
		return var_type is str or var_type is bytes
	else:
		return var_type is str or var_type is unicode

# A file representation with helper methods
class Metafile:

	def __init__(self, name, isDir, lastModified, filesize, path=None, permissions=None):
		self.name = name
		self.isDir = bool(isDir)
		self.lastModified = lastModified
		if self.lastModified is not None:
			self.lastModified = float(self.lastModified)

		self.filesize = filesize
		if self.filesize is not None:
			self.filesize = float(self.filesize)

		self.path = path
		self.permissions = permissions

	def getName(self):
		return self.name

	def getPath(self):
		return self.path

	def getPermissions(self):
		return self.permissions

	def getPermissionsNumeric(self):
		symbolic = self.permissions

		numeric  = "0"
		numeric += str(triples[symbolic[0:3]])
		numeric += str(triples[symbolic[3:6]])
		numeric += str(triples[symbolic[6:9]])

		return numeric

	def isDirectory(self):
		return self.isDir

	def getLastModified(self):
		return self.lastModified

	def getLastModifiedFormatted(self, format='%Y-%m-%d %H:%M'):
		return formatTimestamp(self.lastModified, format)

	def getFilesize(self):
		return self.filesize

	def getHumanFilesize(self):
		if self.filesize < 1024:
			return str(self.filesize) + " B"

		if self.filesize < 1024 * 1024:
			return str(round(self.filesize / 1024, 2)) + " kB"

		if self.filesize < 1024 * 1024 * 1024:
			return str(round(self.filesize / 1024 / 1024, 2)) + " MB"

		return str(round(self.filesize / 1024 / 1024 / 1024, 2)) + " GB"


	def isSameFilepath(self, filepath):
		return os.path.realpath(self.getPath()) == os.path.realpath(filepath)

	def isNewerThan(self, compared_file):
		if self.lastModified is None:
			return False

		if isString(compared_file):
			if os.path.exists(compared_file) is False:
				return False

			lastModified = os.path.getmtime(compared_file)
		elif isinstance(compared_file, Metafile):
			lastModified = compared_file.getLastModified()
		else:
			raise TypeError("Compared_file must be either string (file_path) or Metafile instance")

		return self.lastModified > lastModified

	def isDifferentSizeThan(self, compared_file):
		if self.filesize is None:
			return False

		if isString(compared_file):
			if os.path.exists(compared_file) is False:
				return False

			lastModified = os.path.getsize(compared_file)
		elif isinstance(compared_file, Metafile):
			lastModified = compared_file.getLastModified()
		else:
			raise TypeError("Compared_file must be either string (file_path) or Metafile instance")

		return self.filesize != os.path.getsize(compared_file)



# Detects if object is a string and if so converts to unicode, if not already
#
# @source http://farmdev.com/talks/unicode/
# @author Ivan Krstić
def to_unicode_or_bust(obj, encoding='utf-8'):
	if isinstance(obj, basestring):
		if not isinstance(obj, unicode):
			obj = unicode(obj, encoding)
	return obj



# Converts file_path to Metafile
#
# @type file_path: string
#
# @return Metafile
def fileToMetafile(file_path):
	if sys.version[0] < '3' and type(file_path) is str:
		file_path = file_path.decode('utf-8')
	elif type(file_path) is bytes:
		file_path = file_path.decode('utf-8')

	name = os.path.basename(file_path)
	path = file_path
	isDir = os.path.isdir(file_path)
	lastModified = os.path.getmtime(file_path)
	filesize = os.path.getsize(file_path)

	return Metafile(name, isDir, lastModified, filesize, path)



# Returns a timestamp formatted for humans
#
# @type timestamp: int|float
# @type format: string
# @param format: see http://docs.python.org/library/time.html#time.strftime
#
# @return string
def formatTimestamp(timestamp, format='%Y-%m-%d %H:%M'):
	if timestamp is None:
		return "-"

	return datetime.datetime.fromtimestamp(int(timestamp)).strftime(format)


# Get all folders paths from given path upwards
#
# @type  file_path: string
# @param file_path: absolute file path to return the paths from
#
# @return list<string> of file paths
#
# @global nestingLimit
def getFolders(file_path):
	if file_path is None:
		return []

	folders = [file_path]
	limit = nestingLimit

	while True:
		split = os.path.split(file_path)

		# nothing found
		if len(split) == 0:
			break

		# get filepath
		file_path = split[0]
		limit -= 1

		# nothing else remains
		if len(split[1]) == 0 or limit < 0:
			break

		folders.append(split[0])

	return folders


# Finds a real file path among given folder paths
# and returns the path or None
#
# @type  folders: list<string>
# @param folders: list of paths to folders to look into
# @type  file_name: string
# @param file_name: file name to search
#
# @return string file path or None
def findFile(folders, file_name):
	if folders is None:
		return None

	for folder in folders:
		if isString(folder) is False:
			folder = folder.decode('utf-8')

		if os.path.exists(os.path.join(folder, file_name)) is True:
			return folder

	return None


# Returns unique list of file paths with corresponding config
#
# @type  folders: list<string>
# @param folders: list of paths to folders to filter
# @type  getConfigFile: callback<file_path:string>
#
# @return list<string> of file paths
def getFiles(paths, getConfigFile):
	if paths is None:
		return []

	files = []
	fileNames = []

	for target in paths:
		if target not in fileNames:
			fileNames.append(target)
			files.append([target.encode('utf-8'), getConfigFile(target.encode('utf-8'))])

	return files


# Goes through paths using glob and returns list of Metafiles
#
# @type pattern: string
# @param pattern: glob-like filename pattern
# @type root: string
# @param root: top searched directory
#
# @return list<Metafiles>
def gatherMetafiles(pattern, root):
	if pattern is None:
		return []

	result = {}
	file_names = []

	for subroot, dirnames, filenames in os.walk(root):
		for filename in fnmatch.filter(filenames, pattern):
			target = os.path.join(subroot, filename).encode('utf-8')

			if target not in file_names:
				file_names.append(target)
				result[target] = fileToMetafile(target)

		for folder in dirnames:
			result.update(gatherMetafiles(pattern, os.path.join(root, folder)).items())

	return result



# Returns difference using lastModified between file dicts
#
# @type metafilesBefore: dict
# @type metafilesAfter: dict
#
# @return list<Metafiles>
def getChangedFiles(metafilesBefore, metafilesAfter):
	changed = []
	for file_path in metafilesAfter:
		#file_path = Types.u(file_path)

		if file_path in metafilesBefore and metafilesAfter[file_path].isNewerThan(metafilesBefore[file_path]):
			changed.append(metafilesAfter[file_path])

	return changed



# Abstraction of os.rename for replacing cases
#
# @type source: string
# @param source: source file path
# @type destination: string
# @param destination: destination file path
def replace(source, destination):
	destinationTemp = destination + '.ftpsync.bak'
	try:
		os.rename(source, destination)
	except OSError:
		os.rename(destination, destinationTemp)

		try:
			os.rename(source, destination)
			os.unlink(destinationTemp)
		except OSError as e:
			os.rename(destinationTemp, destination)
			raise



# Performing operation on temporary file and replacing it back
#
# @type operation: callback(file)
# @param operation: operation performed on temporary file
# @type permissions: int (octal)
# @type mode: string
# @param mode: file opening mode
def viaTempfile(file_path, operation, permissions, mode):
	if permissions is None:
		permissions = '0755'
	exceptionOccured = None

	directory = os.path.dirname(file_path)

	if os.path.exists(directory) is False:
		os.makedirs(directory, int(permissions, 8))

	temp = tempfile.NamedTemporaryFile(mode, suffix = '.ftpsync.temp', dir = directory, delete = False)

	try:
		operation(temp)
	except Exception as exp:
		exceptionOccured = exp
	finally:
		temp.flush()
		temp.close()

		if exceptionOccured is None:
			if os.path.exists(file_path) is False:
				created = open(file_path, 'w+')
				created.close()

			replace(temp.name, file_path)

		if os.path.exists(temp.name):
			os.unlink(temp.name)

		if exceptionOccured is not None:
			raise exceptionOccured



# Guesses whether given file is textual or not
#
# @type file_path: string
# @type asciiWhitelist: list<string>
#
# @return boolean whether it's likely textual or binary
def isTextFile(file_path, asciiWhitelist):
    fileName, fileExtension = os.path.splitext(file_path)

    if fileExtension and fileExtension[1:] in asciiWhitelist:
        return True

    return False



# Adds . and .. entries if missing in the collection
#
# @type contents: list<Metadata>
#
# @return list<metadata>
def addLinks(contents):
	hasSelf = False
	hasUp = False
	single = None

	for entry in contents:
		if entry.getName() == '.':
			hasSelf = True
		elif entry.getName() == '..':
			hasUp = True

		if hasSelf and hasUp:
			return contents
		else:
			single = entry

	if single is not None:
		if hasSelf == False:
			entrySelf = Metafile('.', True, None, None, single.getPath(), None)
			contents.append(entrySelf)

		if hasUp == False:
			entryUp = Metafile('..', True, None, None, single.getPath(), None)
			contents.append(entryUp)

	return contents


# Return a relative filepath to path either from the current directory or from an optional start directory
#
# Contains a fix for a bug #5117 not fixed in a version used by ST2
#
# @type path: string
# @param path: destination path
# @type path: string
# @param path: starting (root) path
#
# @return string relative path
def relpath(path, start):
	relpath = os.path.relpath(path, start)

	if start == '/' and relpath[0:2] == '..':
		relpath = relpath[3:]

	return relpath

########NEW FILE########
__FILENAME__ = ftpsyncfilewatcher
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Jiri "NoxArt" Petruzelka
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# @author Jiri "NoxArt" Petruzelka | petruzelka@noxart.cz | @NoxArt
# @copyright (c) 2012 Jiri "NoxArt" Petruzelka
# @link https://github.com/NoxArt/SublimeText2-FTPSync

# Doc comment syntax inspired by http://stackoverflow.com/a/487203/387503


# ==== Libraries ===========================================================================

# Python's built-in libraries
import os
import sys

# FTPSync libraries
if sys.version < '3':
    from ftpsyncfiles import gatherMetafiles, getChangedFiles
else:
    from FTPSync.ftpsyncfiles import gatherMetafiles, getChangedFiles


# ==== Exceptions ==========================================================================

class WatcherClosedException(RuntimeError):
	pass

class NotPreparedException(Exception):
	pass


# ==== Content =============================================================================

class FileWatcher(object):

	def __init__(self, config_file_path, config):
		self.config_file_path = config_file_path
		self.config = config
		self.prepared = False
		self.afterwatch = {
			'before': {},
			'after': {}
		}


	# Scans watched paths for watched files, creates metafiles
	#
	# @type event: string
	# @param event: 'before', 'after'
	# @type name: string
	# @param name: connection name
	def scanWatched(self, event, name):
		if event is 'before' and name in self.afterwatch['before'] and len(self.afterwatch['before'][name]) > 0:
			return

		root = os.path.dirname(self.config_file_path)
		properties = self.config[name]
		watch = properties['after_save_watch']
		self.afterwatch[event][name] = {}

		if type(watch) is list and len(watch) > 0 and properties['upload_delay'] > 0:
			for folder, filepattern in watch:
				# adds contents to dict
				self.afterwatch[event][name].update(gatherMetafiles(filepattern, os.path.join(root, folder)).items())


	# ???
	#
	# @type event: string
	# @param event: 'before', 'after'
	# @type name: string
	# @param name: connection name
	# @type data: ???
	# @param data: ???
	def setScanned(self, event, name, data):
		if type(self.afterwatch) is not dict:
			self.afterwatch = {}

		if event not in self.afterwatch or type(self.afterwatch[event]) is not dict:
			self.afterwatch[event] = {}

		self.afterwatch[event][name] = data


	# Goes through all connection configs and scans all the requested paths
	def prepare(self):
		if self.prepared:
			raise WatcherClosedException

		for name in self.config:
			if self.config[name]['after_save_watch']:
				self.scanWatched('before', name)

				if self.config[name]['debug_extras']['after_save_watch']:
					print ("FTPSync <debug> dumping pre-scan")
					print (self.afterwatch['before'])

		self.prepared = True


	# Returns files that got changed
	#
	# @type connectionName: string
	#
	# @return Metafile[]
	def getChangedFiles(self, connectionName):
		if self.prepared is False:
			raise NotPreparedException

		self.afterwatch['after'][connectionName] = {}
		self.scanWatched('after', connectionName)
		if self.config[connectionName]['debug_extras']['after_save_watch']:
			print ("FTPSync <debug> dumping post-scan")
			print (self.afterwatch['before'])
		changed = getChangedFiles(self.afterwatch['before'][connectionName], self.afterwatch['after'][connectionName])
		if self.config[connectionName]['debug_extras']['after_save_watch']:
			print ("FTPSync <debug> dumping changed files")
			print ("COUNT: " + str(len(changed)))
			for change in changed:
				print ("Path: " + change.getPath() + " | Name: " + change.getName())

		return changed




########NEW FILE########
__FILENAME__ = ftpsyncprogress
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Jiri "NoxArt" Petruzelka
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# @author Jiri "NoxArt" Petruzelka | petruzelka@noxart.cz | @NoxArt
# @copyright (c) 2012 Jiri "NoxArt" Petruzelka
# @link https://github.com/NoxArt/SublimeText2-FTPSync

# ==== Libraries ===========================================================================

# Python's built-in libraries
import math


# ==== Content =============================================================================

# Class implementing logic for progress bar
class Progress:
    def __init__(self, current=0):
        self.current = 0
        self.entries = []

    # Add unfinished entries to progress bar
    #
    # @type  self: Progress
    # @type  entries: list
    # @param entries: list of unfinished entries, usually strings
    def add(self, entries):
        for entry in entries:
            if entry not in self.entries:
                self.entries.append(entry)


    # Return number of items in the progress
    #
    # @type  self: Progress
    #
    # @return int
    def getTotal(self):
        return len(self.entries)


    # Marks a certain number of entries as finished
    #
    # @type  self: Progress
    # @type  by: integer
    # @param by: number of finished items
    def progress(self, by=1):
        self.current += int(by)

        if self.current > self.getTotal():
            self.current = self.getTotal()


    # Returns whether the process has been finished
    #
    # @type  self: Progress
    #
    # @return bool
    def isFinished(self):
        return self.current >= self.getTotal()


    # Get percentage of the progress bar, maybe rounded, see @return
    #
    # @type  self: Progress
    # @type  division: integer
    # @param division: rounding amount
    #
    # @return integer between 0 and 100 / division
    def getPercent(self, division=5):
        if division is 0:
            division = 1

        total = self.getTotal()
        if total is 0:
            total = self.current
        if total is 0:
            total = 1

        percent = int(math.ceil(float(self.current) / float(total) * 100))
        percent = math.ceil(percent / division)

        return percent
########NEW FILE########
__FILENAME__ = ftpsyncworker
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Jiri "NoxArt" Petruzelka
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# @author Jiri "NoxArt" Petruzelka | petruzelka@noxart.cz | @NoxArt
# @copyright (c) 2012 Jiri "NoxArt" Petruzelka
# @link https://github.com/NoxArt/SublimeText2-FTPSync

# ==== Libraries ===========================================================================

# Python's built-in libraries
import threading
import sys
from time import sleep

# FTPSync libraries
if sys.version < '3':
	from ftpsynccommon import Types
else:
	from FTPSync.ftpsynccommon import Types

# ==== Content =============================================================================

# Command thread
class RunningCommand(threading.Thread):
	def __init__(self, command, onFinish, debug, tid):
		self.command = command
		self.onFinish = onFinish
		self.debug = bool(debug)
		self.id = int(tid)
		threading.Thread.__init__(self)

	# Prints debug message if enabled
	def _debugPrint(self, message):
		if self.debug:
			print( "[command {0}]".format(self.id) + message )

	# Runs command
	def run(self):
		try:
			self._debugPrint("Executing")
			self.command.execute()
		except Exception as e:
			self._debugPrint(e)
			self._debugPrint("Retrying")

			self.command.execute()
		finally:
			self._debugPrint("Ending")
			while self.command.isRunning():
				self._debugPrint("Is running...")
				sleep(0.5)

			self.onFinish(self.command)


# Class handling concurrent commands
class Worker(object):

	def __init__(self, limit, factory, loader):
		self.limit = int(limit)

		self.connections = []
		self.commands = []
		self.waitingCommands = []
		self.threads = []
		self.index = 0
		self.threadId = 0
		self.semaphore = threading.BoundedSemaphore(self.limit)

		self.makeConnection = factory
		self.makeConfig = loader
		self.freeConnections = []

		self.debug = False

	# Prints debug message if enabled
	def _debugPrint(self, message):
		if self.debug:
			print(message)

	# Enables console dumping
	def enableDebug(self):
		self.debug = True

	# Enables console dumping
	def disableDebug(self):
		self.debug = False

	# Sets a callback used for making a connection
	def setConnectionFactory(self, factory):
		self.makeConnection = factory

	# Adds a new connection to pool
	def addConnection(self, connections):
		self.connections.append(connections)

	# Creates and adds a connection if limit allows
	def fillConnection(self, config):
		if len(self.connections) <= self.limit:
			connection = None

			try:
				connection = self.makeConnection(self.makeConfig(config), None, False)
			except Exception as e:
				if str(e).lower().find('too many connections') != -1:
					self._debugPrint("FTPSync > Too many connections...")
					sleep(1.5)
				else:
					self._debugPrint(e)
					raise

			if connection is not None and len(connection) > 0:
				self.addConnection(connection)
				self.freeConnections.append(len(self.connections))

			self._debugPrint("FTPSync > Creating new connection #{0}".format(len(self.connections)))

	# Adds a new command to worker
	def addCommand(self, command, config):
		self._debugPrint("FTPSync > Adding command " + self.__commandName(command))
		if len(self.commands) >= self.limit:
			self._debugPrint("FTPSync > Queuing command " + self.__commandName(command) + " (total: {0})".format(len(self.waitingCommands) + 1))
			self.__waitCommand(command)
		else:
			self._debugPrint("FTPSync > Running command " + self.__commandName(command) + " (total: {0})".format(len(self.commands) + 1))
			self.__run(command, config)

	# Return whether has any scheduled commands
	def isEmpty(self):
		return len(self.commands) == 0 and len(self.waitingCommands) == 0

	# Put the command to sleep
	def __waitCommand(self, command):
		self.waitingCommands.append(command)

	# Run the command
	def __run(self, command, config):
		try:
			self.semaphore.acquire()
			self.threadId += 1

			self.fillConnection(config)
			while len(self.freeConnections) == 0:
				sleep(0.1)
				self.fillConnection(config)

			index = self.freeConnections.pop()
			thread = RunningCommand(command, self.__onFinish, self.debug, self.threadId)

			self._debugPrint("FTPSync > Scheduling thread #{0}".format(self.threadId) + " " + self.__commandName(command) + " run, using connection {0}".format(index))

			command.setConnection(self.connections[index - 1])
			self.commands.append({
				'command': command,
				'config': config,
				'thread': thread,
				'index': index,
				'threadId': self.threadId
			})

			thread.start()
		except Exception as e:
			self.__onFinish(command)
			raise
		finally:
			self.semaphore.release()

	# Finish callback
	def __onFinish(self, command):
		config = None

		# Kick from running commands and free connection
		for cmd in self.commands:
			if cmd['command'] is command:
				self.freeConnections.append(cmd['index'])
				config = cmd['config']
				self.commands.remove(cmd)

				self._debugPrint("FTPSync > Removing thread #{0}".format(cmd['threadId']))

		self._debugPrint("FTPSync > Sleeping commands: {0}".format(len(self.waitingCommands)))
		
		# Woke up one sleeping command
		if len(self.waitingCommands) > 0:
			awakenCommand = self.waitingCommands.pop()
			self.__run(awakenCommand, config)

	# Returns classname of given command
	def __commandName(self, command):
		return Types.u(command.__class__.__name__)

	# Closes all connections
	def __del__(self):
		for connections in self.connections:
			for connection in connections:
				connection.close()

				self._debugPrint("FTPSync > Closing connection")

########NEW FILE########
__FILENAME__ = ftpsyncwrapper
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Jiri "NoxArt" Petruzelka
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# @author Jiri "NoxArt" Petruzelka | petruzelka@noxart.cz | @NoxArt
# @copyright (c) 2012 Jiri "NoxArt" Petruzelka
# @link https://github.com/NoxArt/SublimeText2-FTPSync

# ==== Libraries ===========================================================================

# Python's built-in libraries
import datetime
import locale
import os
import re
import sys
import time

# import FTP library
if sys.version < '3':
    import lib2.ftplib as ftplib
else:
    import FTPSync.lib3.ftplib as ftplib

try:
    import encodings.idna
except ImportError:
    print("FTPSync > Failed to import encodings.idna")

# workaround for http://www.gossamer-threads.com/lists/python/dev/755427
try:
    import _strptime
except ImportError:
    print("FTPSync > Failed to import _strptime")

# FTPSync libraries
if sys.version < '3':
    from ftpsynccommon import Runtime, Types
    from ftpsyncfiles import Metafile, isTextFile, viaTempfile, relpath
    # exceptions
    from ftpsyncexceptions import FileNotFoundException
else:
    from FTPSync.ftpsynccommon import Runtime, Types
    from FTPSync.ftpsyncfiles import Metafile, isTextFile, viaTempfile, relpath
    # exceptions
    from FTPSync.ftpsyncexceptions import FileNotFoundException


# ==== Initialization and optimization =====================================================

# storXX block size
transferBlocksize = 8192

# to extract data from FTP LIST http://stackoverflow.com/questions/2443007/ftp-list-format
re_ftpListParse = re.compile("^([d-])([rxws-]{9})\s+\d+\s+\S+\s+\S+\s+(\d+)\s+(\w{1,3}\s+\d+\s+(?:\d+:\d+|\d{2,4}))\s+(.*?)$", re.M | re.I | re.U | re.L)

# error code - first 3-digit number https://tools.ietf.org/html/rfc959#page-39
re_errorCode = re.compile("[1-5]\d\d")

# 20x ok code
re_errorOk = re.compile("2\d\d")

# trailing .
trailingDot = re.compile("/.\Z")

# trailing /
trailingSlash = re.compile("/\Z")

# whitespace
re_whitespace = re.compile("\s+")

# For FTP LIST entries with {last modified} timestamp earlier than 6 months, see http://stackoverflow.com/questions/2443007/ftp-list-format
currentYear = int(time.strftime("%Y", time.gmtime()))

# months
months = {
    'Jan': '01',
    'Feb': '02',
    'Mar': '03',
    'Apr': '04',
    'May': '05',
    'Jun': '06',
    'Jul': '07',
    'Aug': '08',
    'Sep': '09',
    'Oct': '10',
    'Nov': '11',
    'Dec': '12'
}

# List of FTP errors of interest
ftpError = {
    'dataAccepted': 150,
    'fileNotAllowed': 553,
    'fileUnavailible': 550,
    'pendingInformation': 350,
    'ok': 200,
    'passive': 227
}

ftpErrors = {
    'noFileOrDirectory': 'No such file or directory',
    'cwdNoFileOrDirectory': 'No such file or directory',
    'fileNotExist': 'Sorry, but that file doesn\'t exist',
    'permissionDenied': 'Permission denied',
    'rnfrExists': 'RNFR accepted - file exists, ready for destination',
    'rntoReady': '350 Ready for RNTO',
    'disconnected': 'An established connection was aborted by the software in your host machine',
    'timeout': 'timed out',
    'typeIsNow': 'TYPE is now',
    'switchingMode': 'Switching to'
}

# SSL issue
sslErrors = {
    'badWrite': 'error:1409F07F:SSL routines:SSL3_WRITE_PENDING:bad write retry',
    'reuseRequired': 'SSL connection failed; session reuse required',
}

# Default permissions for newly created folder
defaultFolderPermissions = "755"

# Default encoding for file paths
encoding = 'utf-8'

# FTP time format, used for example for MFMT
ftpTimeFormat = '%Y%m%d%H%M%S'



# ==== Exceptions ==========================================================================

class ConnectionClosedException(Exception):
    pass

class TargetAlreadyExists(Exception):
    pass


# ==== Content =============================================================================

# Factory function - returns and instance of a proper class based on the configuration
# currently differs between FTP(S) and SFTP
#
# SFTP currently not implemented
#
# @type config: dict
# @type name: string
# @param name: user-defined name of a connection
#
# @return AbstractConnection
def CreateConnection(config, name):
    if 'private_key' in config and config['private_key'] is not None:
        raise NotImplementedError
    else:
        return FTPSConnection(config['connections'][name], config, name)


# Base class for all connection classes
class AbstractConnection:

    # Return server path for the uploaded file relative to specified path
    #
    # @example:
    #   file_path: /user/home/NoxArt/web/index.php
    #   config['path']: /www/
    #   config['file_path']: /user/home/NoxArt/
    #
    #   result: /www/web/index.php
    #
    # @type self: AbstractConnection
    # @type file_path: string
    #
    # @return string remote file path
    def _getMappedPath(self, file_path):
        config = os.path.dirname(self.config['file_path'])
        fragment = os.path.relpath(file_path, config)
        return self._postprocessPath(os.path.join(self.config['path'], fragment))

    # Tweaks a remote path before using it
    #
    # @type self: AbstractConnection
    # @type file_path: string
    #
    # @return string remote file path
    def _postprocessPath(self, file_path):
        file_path = file_path.replace('\\\\', '\\')
        file_path = file_path.replace('\\', '/')
        file_path = file_path.replace('//','/')
        return file_path

    # Guesses if the file is ASCII file
    #
    # @type self: AbstractConnection
    # @type file_path: string
    def _isAscii(self, file_path):
        return isTextFile(file_path, self.generic_config['ascii_extensions'])


# FTP(S) connection
#
# uses Python's ftplib
#
# because of FTP_TLS added in v2.7 FTPSync uses imported library from v2.7.1
# shipped with the plugin
class FTPSConnection(AbstractConnection):

    canEncrypt = {}

    # Constructor
    #
    # @type self: FTPSConnection
    # @type config: dict
    # @param config: only the connection part of config
    # @type name: string
    # @param name: connection name from config
    def __init__(self, config, generic_config, name):
        self.config = config
        self.generic_config = generic_config
        self.name = name
        self.isClosed = False
        self.feat = None

        if self.config['tls'] is True:
            self.connection = ftplib.FTP_TLS()
        else:
            self.connection = ftplib.FTP()

        if self.config['host'] not in FTPSConnection.canEncrypt:
            FTPSConnection.canEncrypt[self.config['host']] = None


    # Destructor, closes connection
    #
    # @type self: FTPSConnection
    def __del__(self):
        if hasattr(self, 'connection'):
            self.close()


    # Calls a method on FTP driver
    #
    # @type self: FTPSConnection
    # @type command: string
    # @type args: list
    def retryingCommand(self, command, args = []):
        if hasattr(self.connection, command):
            def call():
                return getattr(self.connection, command)(*args)

            retries = self.generic_config['ftp_retry_limit']
            exception = None
            while retries > 0:
                try:
                    result = call()
                    if retries < self.generic_config['ftp_retry_limit'] and self.generic_config['debug_verbose']:
                        print ("FTPSync > Retry of " + command + " succeeded")
                    return result
                except Exception as e:
                    if (sys.version >= '3' and type(e) is TimeoutError) or str(e).find('imeout') >= 0 or str(e).find('imed out') >= 0:
                        print ("FTPSync > Command " + command + " timed out, retrying (" + str(retries) + " remaining)...")
                        retries -= 1
                        time.sleep(self.generic_config['ftp_retry_delay'])
                        exception = e
                        continue

                    raise
            
            if retries == 0:
                print ("FTPSync > Retrying failed: " + str(e))
                raise e
        else:
            raise Exception("FTPSync: No command " + command + " available")


    # Connects to remote server
    #
    # @type self: FTPSConnection
    def connect(self):
        self.retryingCommand('connect', [ self.config['host'], int(self.config['port']), int(self.config['timeout']) ])
        self.retryingCommand('set_pasv', [ self.config['passive'] ])


    # Sets passive connection if configured to do so
    #
    # @type self: FTPSConnection
    def _makePassive(self):
        if self.config['passive']:
            self.retryingCommand('voidcmd', ["PASV"])


    # Authenticates if necessary
    #
    # @type self: FTPSConnection
    #
    # @return bool whether the authentication happened or not
    def authenticate(self):
        if self.config['tls'] is True:
            self.retryingCommand('auth')
            self.retryingCommand('prot_p')
            return True

        return False


    # Logs into the remote server
    #
    # @type self: FTPSConnection
    def login(self):
        self.retryingCommand('login', [ self.config['username'], self.config['password'] ])


    # Send an empty/keep-alive message to server
    #
    # @type self: FTPSConnection
    def keepAlive(self):
        self.retryingCommand('voidcmd', ["NOOP"])


    # Returns whether the connection is active
    #
    # @type self: FTPSConnection
    #
    # @return bool
    def isAlive(self):
        return self.isClosed is False and self.connection.sock is not None and self.connection.file is not None


    # Returns whether the remote server supports simple encryption
    # None = do not know
    #
    # @type self: FTPSConnection
    #
    # @return bool|None
    def encryptionSupported(self):
        if self.config['host'] in FTPSConnection.canEncrypt:
            return FTPSConnection.canEncrypt[self.config['host']]
        else:
            return None


    # Returns connection info
    #
    # @type self: FTPSConnection
    #
    # @return dic{str}
    def getInfo(self):
        self.__loadFeat()

        info = {
            'type': 'FTP',
            'name': self.name,
            'config': self.config,
            'canEncrypt': self.encryptionSupported(),
            'features': self.feat
        }

        return info


    # Uploads a file to remote server
    #
    # @type self: FTPSConnection
    # @type file_path: string
    # @type new_name: string
    # @param new_name: uploads a file under a different name
    # @type failed: bool
    # @param failed: retry flag
    # @type blockCallback: callback
    # @param blockCallback: callback called on every block transferred
    def put(self, file_path, new_name = None, failed = False, blockCallback = None):

        def action():
            remote_file = file_path
            if new_name is not None:
                remote_file = self._postprocessPath(os.path.join(os.path.split(file_path)[0], new_name))

            path = self._getMappedPath(remote_file)

            if os.path.isdir(file_path):
                return self.__ensurePath(path, True)

            command = "STOR " + path
            uploaded = open(file_path, "rb")

            def perBlock(data):
                if blockCallback is not None:
                    blockCallback()

            try:
                #self.connection.storbinary(command, uploaded, callback = perBlock)
                self.retryingCommand('storbinary', [command, uploaded, transferBlocksize, perBlock])

                if self.config['default_upload_permissions'] is not None:
                    try:
                        self.chmod(path, self.config['default_upload_permissions'])
                    except Exception as e:
                        print("FTPSync > failed to set default permissions")
            except Exception as e:
                if self.__isErrorCode(e, ['ok', 'passive', 'dataAccepted']) is True:
                    pass
                elif self.__isErrorCode(e, 'fileUnavailible') and failed is False:
                    self.__ensurePath(path)
                    self.put(file_path, new_name, True)
                elif self.__isErrorCode(e, 'fileNotAllowed') and failed is False:
                    self.__ensurePath(path)
                    self.put(file_path, new_name, True)
                else:
                    raise
            finally:
                uploaded.close()

            if self.config['set_remote_lastmodified'] and self.__hasFeat("MFMT") :
                try:
                    if self.config['debug_extras']['debug_mfmt']:
                        print("FTPSync <debug> MFMT:")
                        print("getmtime: " + str(os.path.getmtime(file_path)))
                        print("encoded: "  + self.__encodeTime(os.path.getmtime(file_path)))
                        print("---")

                    self.voidcmd("MFMT " + self.__encodeTime(os.path.getmtime(file_path)) + " " + path)
                except Exception as e:
                    if self.__isDebug():
                        try:
                            print ("Failed to set lastModified <Exception: " + str(e) + ">")
                        except:
                            pass

        return self.__execute(action)


    # Downloads a file from remote server
    #
    # @type self: FTPSConnection
    # @type file_path: string
    # @type blockCallback: callback
    # @type blockCallback: callback called on every block transferred
    def get(self, file_path, blockCallback):

        def action():
            path = self._getMappedPath(file_path)
            command = "RETR " + self.__encode(path)

            if self.config['debug_extras']['debug_remote_paths']:
                print ("FTPSync <debug> get path " + file_path + " => " + str(self.__encode(path)))

            isAscii = self._isAscii(file_path)
            isAscii = False
            action = 'retrbinary'
            mode = 'wb'
            if isAscii:
                action = 'retrlines'

            def download(tempfile):

                def perBlock(data):
                    if sys.version[0] == '2' or type(data) is bytes:
                        tempfile.write(data)
                    else:
                        tempfile.write(data.encode('utf-8'))

                    if isAscii:
                        # intentional, \n will be converted to os.linesep
                        if sys.version[0] == '2':
                            tempfile.write("\n")
                        else:
                            tempfile.write("\n".encode('utf-8'))

                    if blockCallback is not None:
                        blockCallback()

                try:
                    self.retryingCommand(action, [command, perBlock])
                except Exception as e:
                    if self.__isErrorCode(e, ['ok', 'passive']) or str(e).find(ftpErrors['typeIsNow']) != -1:
                        self.retryingCommand(action, [command, perBlock])
                    elif self.__isErrorCode(e, 'fileUnavailible'):
                        raise FileNotFoundException
                    else:
                        raise

            existsLocally = os.path.exists(file_path)

            if self.config['use_tempfile']:
                viaTempfile(file_path, download, self.config['default_folder_permissions'], mode)
            else:
                with open(file_path, mode) as destination:
                    download(destination)

            if existsLocally is False or self.config['always_sync_local_permissions']:
                try:
                    if self.config['default_local_permissions'] is not None and sys.platform != 'win32' and sys.platform != 'cygwin':
                        if self.config['default_local_permissions'] == "auto":
                            metadata = self.list(file_path)

                            if type(metadata) is list and len(metadata) > 0:
                                os.chmod(file_path, int(metadata[0].getPermissionsNumeric(),8))
                        else:
                            os.chmod(file_path, int(self.config['default_local_permissions'], 8))
                except Exception as e:
                    print ("FTPSync > Error setting local chmod [Exception: " + str(e) + "]")

        return self.__execute(action)



    # Deletes a file from remote server
    #
    # @type self: FTPSConnection
    # @type file_path: string
    def delete(self, file_path, remote=False):

        def action():
            isDir = os.path.isdir(file_path)
            dirname = os.path.dirname(file_path)

            if remote is False:
                path = self._getMappedPath(dirname)
            else:
                path = dirname

            path = trailingDot.sub("", path)
            base = os.path.basename(file_path)

            try:
                if isDir:
                    for entry in self.list(file_path):
                        self.__delete(path + '/' + base, entry)

                    self.cwd(path)
                    self.voidcmd("RMD " + base)
                else:
                    self.cwd(path)
                    self.voidcmd("DELE " + base)
            except Exception as e:
                if str(e).find('No such file'):
                    raise FileNotFoundException
                else:
                    raise

        return self.__execute(action)



    # Deletes a file purely from remote server
    #
    # @type self: FTPSConnection
    # @type file_path: string
    def __delete(self, root, metafile):
        if metafile is None:
            return

        name = self.__basename(metafile.getName())
        if name is None:
            return

        if type(name) is not str:
            name = name.decode('utf-8')

        path = root + '/' + name

        if metafile.isDirectory():
            self.cwd(path)
            for entry in self.list(path, True):
                self.__delete(path, entry)

            self.cwd(root)
            try:
                self.voidcmd("RMD " + name)
            except Exception as e:
                if self.__isErrorCode(e, 'fileUnavailible'):
                    return False
                else:
                    raise
        else:
            self.voidcmd("DELE " + name)



    # Renames a file on remote server
    #
    # @type self: FTPSConnection
    # @type file_path: string
    # @type new_name: string
    #
    # @global ftpErrors
    def rename(self, file_path, new_name, forced=False):

        try:
            is_dir = os.path.isdir(file_path)
            dirname = os.path.dirname(file_path)
            path = self._getMappedPath(dirname)
            base = os.path.basename(file_path)

            try:
                self.cwd(path)
            except Exception as e:
                if self.__isErrorCode(e, 'fileUnavailible'):
                    self.__ensurePath(path)
                else:
                    raise

            if not forced and self.fileExists(new_name):
                raise TargetAlreadyExists("Remote target {" + new_name + "} already exists")

            try:
                self.voidcmd("RNFR " + base)
            except Exception as e:
                if self.__isError(e, 'rnfrExists') or self.__isError(e, 'rntoReady'):
                    self.voidcmd("RNTO " + new_name)
                    return
                elif self.__isError(e, 'cwdNoFileOrDirectory') or self.__isError(e, 'fileNotExist'):
                    if is_dir:
                        self.__ensurePath( path + '/' + new_name, True )
                    else:
                        self.put(file_path, new_name)
                    return
                else:
                    raise

            try:
                self.voidcmd("RNFR " + base)
            except Exception as e:
                if (self.__isError(e, 'rnfrExists') and str(e).find('Aborting previous')) or self.__isError(e, 'rntoReady'):
                    self.voidcmd("RNTO " + new_name)
                    return
                else:
                    raise

            self.voidcmd("RNTO " + new_name)

        except Exception as e:

            # disconnected - close itself to be refreshed
            if self.__isError(e, 'disconnected') is True:
                self.close()
                raise
            # other exception
            else:
                raise


    # Aborts command and calls on{Command}Abort if available
    #
    # @type self: FTPSConnection
    # @type command: string|None
    # @type args: mixed
    def abort(self, command = None, args = None):
        self.retryingCommand('abort')

        if command is None:
            return

        method = 'on' + command[0].upper() + command[1:] + 'Abort'
        if hasattr(self, method):
            getattr(self, method)(args)


    # Changes a current path on remote server
    #
    # @type self: FTPSConnection
    # @type path: string
    def cwd(self, path):
        self._makePassive()
        self.retryingCommand('cwd', [path])


    # Returns whether it provides true last modified mechanism
    def hasTrueLastModified(self):
        return self.__hasFeat("MFMT")


    # Void command without return
    #
    # Passivates if configured to do so
    #
    # @type self: FTPSConnection
    # @type path: string
    def voidcmd(self, command):
        self._makePassive()
        self.retryingCommand('voidcmd', [self.__encode(command)])


    # Plain command with return
    #
    # Passivates if configured to do so
    #
    # @type self: FTPSConnection
    # @type path: string
    def sendcmd(self, command):
        self._makePassive()
        return self.retryingCommand('sendcmd', [self.__encode(command)])


    # Returns whether file or folder info
    #
    # @type self: FTPSConnection
    # @type path: string
    def fileExists(self, path):
        try:
            self._makePassive()
            self.retryingCommand('voidcmd', ["SIZE " + path])

            return True
        except Exception as e:
            if self.__isErrorCode(e, 'fileUnavailible'):
                return False
            else:
                raise


    # Returns a list of content of a given path
    #
    # @type self: FTPSConnection
    # @type file_path: string
    # @type mapped: bool
    # @param mapped: whether it's remote path (True) or not
    # @type all: bool
    # @param all: whether include . and ..
    #
    # @return list<Metafile>|False
    def list(self, file_path, mapped=False,all=False):

        def action():
            if mapped:
                path = file_path
            else:
                path = self._getMappedPath(file_path)

            path = self.__encode(path)

            if self.config['debug_extras']['debug_remote_paths']:
                print ("FTPSync <debug> list path " + file_path + " => " + str(path))

            contents = []
            result = []

            try:
                self.retryingCommand('retrlines', ["LIST -a " + path, lambda data: contents.append(data)])
            except Exception as e:
                if self.__isErrorCode(e, ['ok', 'passive']) or str(e).find(ftpErrors['typeIsNow']) != -1:
                    self.retryingCommand('retrlines', ["LIST -a " + path, lambda data: contents.append(data)])
                elif str(e).find('No such file'):
                    raise FileNotFoundException
                else:
                    try:
                        self.retryingCommand('dir', [path, lambda data: contents.append(data)])
                    except Exception as e:
                        if self.__isErrorCode(e, ['ok', 'passive']) or str(e).find(ftpErrors['typeIsNow']) != -1:
                            self.retryingCommand('retrlines', ["LIST -a " + path, lambda data: contents.append(data)])
                        elif str(e).find('No such file'):
                            raise FileNotFoundException
                        else:
                            raise

            for content in contents:
                try:
                    if self.config['debug_extras']['print_list_result'] is True:
                        print ("FTPSync <debug> LIST line: " + Types.u(content))
                except KeyError:
                    pass

                split = re_ftpListParse.search(content)

                if split is None:
                    continue

                isDir = split.group(1) == 'd'
                permissions = split.group(2)
                filesize = split.group(3)
                lastModified = split.group(4)
                name = split.group(5)

                if all is True or (name != "." and name != ".."):
                    data = Metafile(name, isDir, self.__parseTime(lastModified) + int(self.config['time_offset']), filesize, os.path.normpath(path).replace('\\', '/'), permissions)
                    result.append(data)

            return result

        return self.__execute(action)


    # Closes a connection
    #
    # @type self: FTPSConnection
    # @type connections: dict<hash => list<connection>
    # @type hash: string
    def close(self, connections=[], hash=None):
        try:
            self.retryingCommand('quit')
        except:
            self.retryingCommand('close')
        finally:
            self.isClosed = True

        if len(connections) > 0 and hash is not None:
            try:
                connections[hash].remove(self)
            except ValueError:
                return


    # Changes permissions for a remote file
    #
    # @type self: FTPSConnection
    # @type filename: string
    # @type permissions: string
    def chmod(self, filename, permissions):
        command = "SITE CHMOD " + str(permissions) + " " + str(filename)

        self.voidcmd(command)


    # Returns local path for given remote path
    def getLocalPath(self, remotePath, localRoot):
        originalRemotePath = remotePath
        if remotePath[-1] == '.':
            remotePath = remotePath[0:-1]
        remotePath = remotePath.replace('//', '/')

        path = os.path.join(localRoot, relpath(remotePath, self.config['path']))
        normpath = os.path.normpath(path)

        if self.config['debug_extras']['debug_get_local_path']:
            print("FTPSync <debug> getLocalPath:")
            print("originalRemotePath: " + originalRemotePath)
            print("remotePath: " + remotePath)
            print("localRoot: " + localRoot)
            print("remoteRoot: " + self.config['path'])
            print("path: " + path)
            print("normpath: " + normpath)
            print("</debug>")

        return normpath


    # Returns normalized path in unix style
    def getNormpath(self, path):
        return os.path.normpath(path).replace('\\', '/').replace('//', '/')


    # Encodes a (usually filename) string
    #
    # @type self: FTPSConnection
    # @type filename: string
    #
    # @return encoded string
    def __encode(self, string):
        if sys.version[0] == '3':
            if hasattr(string, 'decode'):
                return string.decode('utf-8')
            else:
                return string

        if self.config['encoding'].lower() == 'auto':
            if self.__hasFeat("UTF8"):
                return string.encode('utf-8')
            else:
                return string
        else:
            return string.encode(self.config['encoding'])


    # Loads availible features
    #
    # @type self: FTPSConnection
    def __loadFeat(self):
        try:
            feats = self.retryingCommand('sendcmd', ["FEAT"]).split("\n")
            self.feat = []
            for feat in feats:
                if feat[0] != '2':
                    self.feat.append( feat.strip() )
        except Exception as e:
            self.feat = []


    # Returns whether server supports a certain feature
    #
    # @type self: FTPSConnection
    def __hasFeat(self, feat):
        if self.feat is None:
            self.__loadFeat()

        return (feat in self.feat)


    # Executes an action while handling common errors
    #
    # @type self: FTPSConnection
    # @type callback: callback
    #
    # @return unknown
    def __execute(self, callback):
        def checkEncrypt():
            if self.config['tls'] and FTPSConnection.canEncrypt[self.config['host']] is None:
                if Runtime.getCaller(1) in ['get', 'put', 'delete']:
                    FTPSConnection.canEncrypt[self.config['host']] = True

        result = None
        try:
            result = callback()
            checkEncrypt()
            return result
        except Exception as e:

            # type is now
            if str(e).find(ftpErrors['typeIsNow']) != -1 or str(e).find(ftpErrors['switchingMode']) != -1:
                return callback()
            # bad write - repeat command
            elif re_errorOk.search(str(e)) is not None:
                print ("FTPSync > " + str(e))
                return result
            elif str(e).find(sslErrors['badWrite']) != -1:
                return callback()
            # disconnected - close itself to be refreshed
            elif self.__isError(e, 'disconnected') is True:
                self.close()
                raise
            # timeout - retry
            elif self.__isError(e, 'timeout') is True:
                return callback()
            # SSL not enabled
            elif str(e).find(sslErrors['reuseRequired']) != -1:
                FTPSConnection.canEncrypt[self.config['host']] = False
                raise
            # other exception
            else:
                checkEncrypt()
                raise


    # Throws exception if closed
    #
    # @type self: FTPSConnection
    def __checkClosed(self):
        if self.isClosed is True:
            raise ConnectionClosedException


    # Parses string time
    #
    # @see http://stackoverflow.com/questions/2443007/ftp-list-format
    #
    # @type self: FTPSConnection
    # @type: time_val: string
    #
    # @return unix timestamp
    def __parseTime(self, time_val):
        for month in months:
            time_val = time_val.replace(month, months[month])

        if time_val.find(':') is -1:
            time_val = time_val + str(" 00:00")
            time_val = re_whitespace.sub(" ", time_val)
            struct = time.strptime(time_val, "%m %d %Y %H:%M")
        else:
            time_val = str(currentYear) + " " + time_val
            time_val = re_whitespace.sub(" ", time_val)
            struct = time.strptime(time_val, "%Y %m %d %H:%M")

        return time.mktime(struct)


    # Unix timestamp to FTP time
    #
    # @type self: FTPSConnection
    # @type: timestamp: integer
    #
    # @return formatted time
    def __encodeTime(self, timestamp):
        time = datetime.datetime.fromtimestamp(timestamp)
        return time.strftime(ftpTimeFormat)


    # Integer code error comparison
    #
    # @type self: FTPSConnection
    # @type exception: Exception
    # @type error: string
    # @param error: key of ftpError dict
    #
    # @return boolean
    #
    # @global ftpError
    # @global re_errorCode
    def __isErrorCode(self, exception, error):
        code = re_errorCode.search(str(exception))

        if code is None:
            return False

        if type(error) is list:
            for err in error:
                if int(code.group(0)) == ftpError[err]:
                    return True
            return False
        else:
            return int(code.group(0)) == ftpError[error]


    # Textual error comparison
    #
    # @type self: FTPSConnection
    # @type exception: Exception
    # @type error: string
    # @param error: key of ftpErrors dict
    #
    # @return boolean
    #
    # @global ftpErrors
    def __isError(self, exception, error):
        return str(exception).find(ftpErrors[error]) != -1


    # Whether in debug mode
    #
    # @type self: FTPSConnection
    #
    # @return boolean
    def __isDebug(self):
        return True


    # Returns base name
    #
    # @type self: FTPSConnection
    # @type remote_path: string
    # @param remote_path: remote file path
    #
    # @return string
    #
    # @global trailingSlash
    def __basename(self, remote_path):
        if remote_path is None:
            return

        return trailingSlash.sub("", remote_path).split("/")[-1]


    # Ensures the root path is existing and accessible
    #
    # @type self: FTPSConnection
    # @type path: string
    def ensureRoot(self):
        if len(self.config['path']) > 1:
            self.__ensurePath(self.config['path'], True, '/')


    # Ensures the given path is existing and accessible
    #
    # @type self: FTPSConnection
    # @type path: string
    def __ensurePath(self, path, isFolder=False, root=None):
        if root is None:
            root = self.config['path']
            self.retryingCommand('cwd', [root])
            relative = os.path.relpath(path, root)
        else:
            relative = root + '/' + path
        
        relative = self._postprocessPath(relative)

        folders = list(filter(None, relative.split("/")))
        if 'debug_extras' in self.config and 'print_ensure_folders' in self.config['debug_extras'] and self.config['debug_extras']['print_ensure_folders'] is True:
            print (relative, folders)

        index = 0
        for folder in folders:
            index += 1

            try:
                if index < len(folders) or (isFolder and index <= len(folders)):
                    self.cwd(folder)
            except Exception as e:
                if self.__isErrorCode(e, 'fileUnavailible'):

                    try:
                        # create folder
                        self.retryingCommand('mkd', [self.__encode(folder)])
                    except Exception as e:
                        if self.__isErrorCode(e, 'fileUnavailible'):
                            # not proper permissions
                            self.chmod(folder, self.config['default_folder_permissions'])
                        else:
                            raise

                    # move down
                    self.cwd(folder)
                else:
                    raise

        self.cwd(self.config['path'])


########NEW FILE########
__FILENAME__ = ftplib
"""An FTP client class and some helper functions.

Based on RFC 959: File Transfer Protocol (FTP), by J. Postel and J. Reynolds

Example:

>>> from ftplib import FTP
>>> ftp = FTP('ftp.python.org') # connect to host, default port
>>> ftp.login() # default, i.e.: user anonymous, passwd anonymous@
'230 Guest login ok, access restrictions apply.'
>>> ftp.retrlines('LIST') # list directory contents
total 9
drwxr-xr-x   8 root     wheel        1024 Jan  3  1994 .
drwxr-xr-x   8 root     wheel        1024 Jan  3  1994 ..
drwxr-xr-x   2 root     wheel        1024 Jan  3  1994 bin
drwxr-xr-x   2 root     wheel        1024 Jan  3  1994 etc
d-wxrwxr-x   2 ftp      wheel        1024 Sep  5 13:43 incoming
drwxr-xr-x   2 root     wheel        1024 Nov 17  1993 lib
drwxr-xr-x   6 1094     wheel        1024 Sep 13 19:07 pub
drwxr-xr-x   3 root     wheel        1024 Jan  3  1994 usr
-rw-r--r--   1 root     root          312 Aug  1  1994 welcome.msg
'226 Transfer complete.'
>>> ftp.quit()
'221 Goodbye.'
>>>

A nice test that reveals some of the network dialogue would be:
python ftplib.py -d localhost -l -p -l
"""

#
# Changes and improvements suggested by Steve Majewski.
# Modified by Jack to work on the mac.
# Modified by Siebren to support docstrings and PASV.
# Modified by Phil Schwartz to add storbinary and storlines callbacks.
# Modified by Giampaolo Rodola' to add TLS support.
#

import os
import sys

# Import SOCKS module if it exists, else standard socket module socket
try:
    import SOCKS; socket = SOCKS; del SOCKS # import SOCKS as socket
    from socket import getfqdn; socket.getfqdn = getfqdn; del getfqdn
except ImportError:
    import socket
from socket import _GLOBAL_DEFAULT_TIMEOUT

__all__ = ["FTP","Netrc"]

# Magic number from <socket.h>
MSG_OOB = 0x1                           # Process data out of band


# The standard FTP server control port
FTP_PORT = 21


# Exception raised when an error or invalid response is received
class Error(Exception): pass
class error_reply(Error): pass          # unexpected [123]xx reply
class error_temp(Error): pass           # 4xx errors
class error_perm(Error): pass           # 5xx errors
class error_proto(Error): pass          # response does not begin with [1-5]


# All exceptions (hopefully) that may be raised here and that aren't
# (always) programming errors on our side
all_errors = (Error, IOError, EOFError)


# Line terminators (we always output CRLF, but accept any of CRLF, CR, LF)
CRLF = '\r\n'

# The class itself
class FTP:

    '''An FTP client class.

    To create a connection, call the class using these arguments:
            host, user, passwd, acct, timeout

    The first four arguments are all strings, and have default value ''.
    timeout must be numeric and defaults to None if not passed,
    meaning that no timeout will be set on any ftp socket(s)
    If a timeout is passed, then this is now the default timeout for all ftp
    socket operations for this instance.

    Then use self.connect() with optional host and port argument.

    To download a file, use ftp.retrlines('RETR ' + filename),
    or ftp.retrbinary() with slightly different arguments.
    To upload a file, use ftp.storlines() or ftp.storbinary(),
    which have an open file as argument (see their definitions
    below for details).
    The download/upload functions first issue appropriate TYPE
    and PORT or PASV commands.
'''

    debugging = 0
    host = ''
    port = FTP_PORT
    sock = None
    file = None
    welcome = None
    passiveserver = 1

    # Initialization method (called by class instantiation).
    # Initialize host to localhost, port to standard ftp port
    # Optional arguments are host (for connect()),
    # and user, passwd, acct (for login())
    def __init__(self, host='', user='', passwd='', acct='',
                 timeout=_GLOBAL_DEFAULT_TIMEOUT):
        self.timeout = timeout
        if host:
            self.connect(host)
            if user:
                self.login(user, passwd, acct)

    def connect(self, host='', port=0, timeout=-999):
        '''Connect to host.  Arguments are:
         - host: hostname to connect to (string, default previous host)
         - port: port to connect to (integer, default previous port)
        '''
        if host != '':
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        self.sock = socket.create_connection((self.host, self.port), self.timeout)
        self.af = self.sock.family
        self.file = self.sock.makefile('rb')
        self.welcome = self.getresp()
        return self.welcome

    def getwelcome(self):
        '''Get the welcome message from the server.
        (this is read and squirreled away by connect())'''
        if self.debugging:
            print ('*welcome*', self.sanitize(self.welcome))
        return self.welcome

    def set_debuglevel(self, level):
        '''Set the debugging level.
        The required argument level means:
        0: no debugging output (default)
        1: print commands and responses but not body text etc.
        2: also print raw lines read and sent before stripping CR/LF'''
        self.debugging = level
    debug = set_debuglevel

    def set_pasv(self, val):
        '''Use passive or active mode for data transfers.
        With a false argument, use the normal PORT mode,
        With a true argument, use the PASV command.'''
        self.passiveserver = val

    # Internal: "sanitize" a string for printing
    def sanitize(self, s):
        if s[:5] == 'pass ' or s[:5] == 'PASS ':
            i = len(s)
            while i > 5 and s[i-1] in '\r\n':
                i = i-1
            s = s[:5] + '*'*(i-5) + s[i:]
        return repr(s)

    # Internal: send one line to the server, appending CRLF
    def putline(self, line):
        line = line + CRLF
        if self.debugging > 1: print ('*put*', self.sanitize(line))
        self.sock.sendall(line)

    # Internal: send one command to the server (through putline())
    def putcmd(self, line):
        if self.debugging: print ('*cmd*', self.sanitize(line))
        self.putline(line)

    # Internal: return one line from the server, stripping CRLF.
    # Raise EOFError if the connection is closed
    def getline(self):
        line = self.file.readline()
        if self.debugging > 1:
            print ('*get*', self.sanitize(line))
        if not line: raise EOFError
        if line[-2:] == CRLF: line = line[:-2]
        elif line[-1:] in CRLF: line = line[:-1]
        return line

    # Internal: get a response from the server, which may possibly
    # consist of multiple lines.  Return a single string with no
    # trailing CRLF.  If the response consists of multiple lines,
    # these are separated by '\n' characters in the string
    def getmultiline(self):
        line = self.getline()
        if line[3:4] == '-':
            code = line[:3]
            while 1:
                nextline = self.getline()
                line = line + ('\n' + nextline)
                if nextline[:3] == code and \
                        nextline[3:4] != '-':
                    break
        return line

    # Internal: get a response from the server.
    # Raise various errors if the response indicates an error
    def getresp(self):
        resp = self.getmultiline()
        if self.debugging: print ('*resp*', self.sanitize(resp))
        self.lastresp = resp[:3]
        c = resp[:1]
        if c in ('1', '2', '3'):
            return resp
        if c == '4':
            raise error_temp(resp)
        if c == '5':
            raise error_perm(resp)
        raise error_proto(resp)

    def voidresp(self):
        """Expect a response beginning with '2'."""
        resp = self.getresp()
        if resp[:1] != '2':
            raise error_reply( resp)
        return resp

    def abort(self):
        '''Abort a file transfer.  Uses out-of-band data.
        This does not follow the procedure from the RFC to send Telnet
        IP and Synch; that doesn't seem to work with the servers I've
        tried.  Instead, just send the ABOR command as OOB data.'''
        line = 'ABOR' + CRLF
        if self.debugging > 1: print ('*put urgent*', self.sanitize(line))
        self.sock.sendall(line, MSG_OOB)
        resp = self.getmultiline()
        if resp[:3] not in ('426', '225', '226'):
            raise error_proto(resp)

    def sendcmd(self, cmd):
        '''Send a command and return the response.'''
        self.putcmd(cmd)
        return self.getresp()

    def voidcmd(self, cmd):
        """Send a command and expect a response beginning with '2'."""
        self.putcmd(cmd)
        return self.voidresp()

    def sendport(self, host, port):
        '''Send a PORT command with the current host and the given
        port number.
        '''
        hbytes = host.split('.')
        pbytes = [repr(port//256), repr(port%256)]
        bytes = hbytes + pbytes
        cmd = 'PORT ' + ','.join(bytes)
        return self.voidcmd(cmd)

    def sendeprt(self, host, port):
        '''Send a EPRT command with the current host and the given port number.'''
        af = 0
        if self.af == socket.AF_INET:
            af = 1
        if self.af == socket.AF_INET6:
            af = 2
        if af == 0:
            raise error_proto('unsupported address family')
        fields = ['', repr(af), host, repr(port), '']
        cmd = 'EPRT ' + '|'.join(fields)
        return self.voidcmd(cmd)

    def makeport(self):
        '''Create a new socket and send a PORT command for it.'''
        msg = "getaddrinfo returns an empty list"
        sock = None
        for res in socket.getaddrinfo(None, 0, self.af, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                sock = socket.socket(af, socktype, proto)
                sock.bind(sa)
            except socket.error as msg:
                if sock:
                    sock.close()
                sock = None
                continue
            break
        if not sock:
            raise socket.error(msg)
        sock.listen(1)
        port = sock.getsockname()[1] # Get proper port
        host = self.sock.getsockname()[0] # Get proper host
        if self.af == socket.AF_INET:
            resp = self.sendport(host, port)
        else:
            resp = self.sendeprt(host, port)
        if self.timeout is not _GLOBAL_DEFAULT_TIMEOUT:
            sock.settimeout(self.timeout)
        return sock

    def makepasv(self):
        if self.af == socket.AF_INET:
            host, port = parse227(self.sendcmd('PASV'))
        else:
            host, port = parse229(self.sendcmd('EPSV'), self.sock.getpeername())
        return host, port

    def ntransfercmd(self, cmd, rest=None):
        """Initiate a transfer over the data connection.

        If the transfer is active, send a port command and the
        transfer command, and accept the connection.  If the server is
        passive, send a pasv command, connect to it, and start the
        transfer command.  Either way, return the socket for the
        connection and the expected size of the transfer.  The
        expected size may be None if it could not be determined.

        Optional `rest' argument can be a string that is sent as the
        argument to a REST command.  This is essentially a server
        marker used to tell the server to skip over any data up to the
        given marker.
        """
        size = None
        if self.passiveserver:
            host, port = self.makepasv()
            conn = socket.create_connection((host, port), self.timeout)
            try:
                if rest is not None:
                    self.sendcmd("REST %s" % rest)
                resp = self.sendcmd(cmd)
                # Some servers apparently send a 200 reply to
                # a LIST or STOR command, before the 150 reply
                # (and way before the 226 reply). This seems to
                # be in violation of the protocol (which only allows
                # 1xx or error messages for LIST), so we just discard
                # this response.
                if resp[0] == '2':
                    resp = self.getresp()
                if resp[0] != '1':
                    raise error_reply(resp)
            except:
                conn.close()
                raise
        else:
            sock = self.makeport()
            try:
                if rest is not None:
                    self.sendcmd("REST %s" % rest)
                resp = self.sendcmd(cmd)
                # See above.
                if resp[0] == '2':
                    resp = self.getresp()
                if resp[0] != '1':
                    raise error_reply(resp)
                conn, sockaddr = sock.accept()
                if self.timeout is not _GLOBAL_DEFAULT_TIMEOUT:
                    conn.settimeout(self.timeout)
            finally:
                sock.close()
        if resp[:3] == '150':
            # this is conditional in case we received a 125
            size = parse150(resp)
        return conn, size

    def transfercmd(self, cmd, rest=None):
        """Like ntransfercmd() but returns only the socket."""
        return self.ntransfercmd(cmd, rest)[0]

    def login(self, user = '', passwd = '', acct = ''):
        '''Login, default anonymous.'''
        if not user: user = 'anonymous'
        if not passwd: passwd = ''
        if not acct: acct = ''
        if user == 'anonymous' and passwd in ('', '-'):
            # If there is no anonymous ftp password specified
            # then we'll just use anonymous@
            # We don't send any other thing because:
            # - We want to remain anonymous
            # - We want to stop SPAM
            # - We don't want to let ftp sites to discriminate by the user,
            #   host or country.
            passwd = passwd + 'anonymous@'
        resp = self.sendcmd('USER ' + user)
        if resp[0] == '3': resp = self.sendcmd('PASS ' + passwd)
        if resp[0] == '3': resp = self.sendcmd('ACCT ' + acct)
        if resp[0] != '2':
            raise error_reply(resp)
        return resp

    def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
        """Retrieve data in binary mode.  A new port is created for you.

        Args:
          cmd: A RETR command.
          callback: A single parameter callable to be called on each
                    block of data read.
          blocksize: The maximum number of bytes to read from the
                     socket at one time.  [default: 8192]
          rest: Passed to transfercmd().  [default: None]

        Returns:
          The response code.
        """
        self.voidcmd('TYPE I')
        conn = self.transfercmd(cmd, rest)
        while 1:
            data = conn.recv(blocksize)
            if not data:
                break
            callback(data)
        conn.close()
        return self.voidresp()

    def retrlines(self, cmd, callback = None):
        """Retrieve data in line mode.  A new port is created for you.

        Args:
          cmd: A RETR, LIST, NLST, or MLSD command.
          callback: An optional single parameter callable that is called
                    for each line with the trailing CRLF stripped.
                    [default: print_line()]

        Returns:
          The response code.
        """
        if callback is None: callback = print_line
        resp = self.sendcmd('TYPE A')
        conn = self.transfercmd(cmd)
        fp = conn.makefile('rb')
        while 1:
            line = fp.readline()
            if self.debugging > 2: print ('*retr*', repr(line))
            if not line:
                break
            if line[-2:] == CRLF:
                line = line[:-2]
            elif line[-1:] == '\n':
                line = line[:-1]
            callback(line)
        fp.close()
        conn.close()
        return self.voidresp()

    def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
        """Store a file in binary mode.  A new port is created for you.

        Args:
          cmd: A STOR command.
          fp: A file-like object with a read(num_bytes) method.
          blocksize: The maximum data size to read from fp and send over
                     the connection at once.  [default: 8192]
          callback: An optional single parameter callable that is called on
                    on each block of data after it is sent.  [default: None]
          rest: Passed to transfercmd().  [default: None]

        Returns:
          The response code.
        """
        self.voidcmd('TYPE I')
        conn = self.transfercmd(cmd, rest)
        while 1:
            buf = fp.read(blocksize)
            if not buf: break
            conn.sendall(buf)
            if callback: callback(buf)
        conn.close()
        return self.voidresp()

    def storlines(self, cmd, fp, callback=None):
        """Store a file in line mode.  A new port is created for you.

        Args:
          cmd: A STOR command.
          fp: A file-like object with a readline() method.
          callback: An optional single parameter callable that is called on
                    on each line after it is sent.  [default: None]

        Returns:
          The response code.
        """
        self.voidcmd('TYPE A')
        conn = self.transfercmd(cmd)
        while 1:
            buf = fp.readline()
            if not buf: break
            if buf[-2:] != CRLF:
                if buf[-1] in CRLF: buf = buf[:-1]
                buf = buf + CRLF
            conn.sendall(buf)
            if callback: callback(buf)
        conn.close()
        return self.voidresp()

    def acct(self, password):
        '''Send new account name.'''
        cmd = 'ACCT ' + password
        return self.voidcmd(cmd)

    def nlst(self, *args):
        '''Return a list of files in a given directory (default the current).'''
        cmd = 'NLST'
        for arg in args:
            cmd = cmd + (' ' + arg)
        files = []
        self.retrlines(cmd, files.append)
        return files

    def dir(self, *args):
        '''List a directory in long form.
        By default list current directory to stdout.
        Optional last argument is callback function; all
        non-empty arguments before it are concatenated to the
        LIST command.  (This *should* only be used for a pathname.)'''
        cmd = 'LIST'
        func = None
        if args[-1:] and type(args[-1]) != type(''):
            args, func = args[:-1], args[-1]
        for arg in args:
            if arg:
                cmd = cmd + (' ' + arg)
        self.retrlines(cmd, func)

    def rename(self, fromname, toname):
        '''Rename a file.'''
        resp = self.sendcmd('RNFR ' + fromname)
        if resp[0] != '3':
            raise error_reply(resp)
        return self.voidcmd('RNTO ' + toname)

    def delete(self, filename):
        '''Delete a file.'''
        resp = self.sendcmd('DELE ' + filename)
        if resp[:3] in ('250', '200'):
            return resp
        else:
            raise error_reply(resp)

    def cwd(self, dirname):
        '''Change to a directory.'''
        if dirname == '..':
            try:
                return self.voidcmd('CDUP')
            except error_perm as msg:
                if msg.args[0][:3] != '500':
                    raise
        elif dirname == '':
            dirname = '.'  # does nothing, but could return error
        cmd = 'CWD ' + dirname
        return self.voidcmd(cmd)

    def size(self, filename):
        '''Retrieve the size of a file.'''
        # The SIZE command is defined in RFC-3659
        resp = self.sendcmd('SIZE ' + filename)
        if resp[:3] == '213':
            s = resp[3:].strip()
            try:
                return int(s)
            except (OverflowError, ValueError):
                return long(s)

    def mkd(self, dirname):
        '''Make a directory, return its full pathname.'''
        resp = self.sendcmd('MKD ' + dirname)
        return parse257(resp)

    def rmd(self, dirname):
        '''Remove a directory.'''
        return self.voidcmd('RMD ' + dirname)

    def pwd(self):
        '''Return current working directory.'''
        resp = self.sendcmd('PWD')
        return parse257(resp)

    def quit(self):
        '''Quit, and close the connection.'''
        resp = self.voidcmd('QUIT')
        self.close()
        return resp

    def close(self):
        '''Close the connection without assuming anything about it.'''
        if self.file is not None:
            self.file.close()
        if self.sock is not None:
            self.sock.close()
        self.file = self.sock = None

sslImported = False
try:
    import ssl
    sslImported = True
except ImportError:
    try:
        import lib2.ssl as ssl
        sslImported = True
    except ImportError:
        print("SSL module import failed")

if sslImported:
    class FTP_TLS(FTP):
        '''A FTP subclass which adds TLS support to FTP as described
        in RFC-4217.

        Connect as usual to port 21 implicitly securing the FTP control
        connection before authenticating.

        Securing the data connection requires user to explicitly ask
        for it by calling prot_p() method.

        Usage example:
        >>> from ftplib import FTP_TLS
        >>> ftps = FTP_TLS('ftp.python.org')
        >>> ftps.login()  # login anonymously previously securing control channel
        '230 Guest login ok, access restrictions apply.'
        >>> ftps.prot_p()  # switch to secure data connection
        '200 Protection level set to P'
        >>> ftps.retrlines('LIST')  # list directory content securely
        total 9
        drwxr-xr-x   8 root     wheel        1024 Jan  3  1994 .
        drwxr-xr-x   8 root     wheel        1024 Jan  3  1994 ..
        drwxr-xr-x   2 root     wheel        1024 Jan  3  1994 bin
        drwxr-xr-x   2 root     wheel        1024 Jan  3  1994 etc
        d-wxrwxr-x   2 ftp      wheel        1024 Sep  5 13:43 incoming
        drwxr-xr-x   2 root     wheel        1024 Nov 17  1993 lib
        drwxr-xr-x   6 1094     wheel        1024 Sep 13 19:07 pub
        drwxr-xr-x   3 root     wheel        1024 Jan  3  1994 usr
        -rw-r--r--   1 root     root          312 Aug  1  1994 welcome.msg
        '226 Transfer complete.'
        >>> ftps.quit()
        '221 Goodbye.'
        >>>
        '''
        ssl_version = ssl.PROTOCOL_TLSv1

        def __init__(self, host='', user='', passwd='', acct='', keyfile=None,
                     certfile=None, timeout=_GLOBAL_DEFAULT_TIMEOUT):
            self.keyfile = keyfile
            self.certfile = certfile
            self._prot_p = False
            FTP.__init__(self, host, user, passwd, acct, timeout)

        def login(self, user='', passwd='', acct='', secure=True):
            if secure and not isinstance(self.sock, ssl.SSLSocket):
                self.auth()
            return FTP.login(self, user, passwd, acct)

        def auth(self):
            '''Set up secure control connection by using TLS/SSL.'''
            if isinstance(self.sock, ssl.SSLSocket):
                raise ValueError("Already using TLS")
            if self.ssl_version == ssl.PROTOCOL_TLSv1:
                resp = self.voidcmd('AUTH TLS')
            else:
                resp = self.voidcmd('AUTH SSL')
            self.sock = ssl.wrap_socket(self.sock, self.keyfile, self.certfile,
                                        ssl_version=self.ssl_version)
            self.file = self.sock.makefile(mode='rb')
            return resp

        def prot_p(self):
            '''Set up secure data connection.'''
            # PROT defines whether or not the data channel is to be protected.
            # Though RFC-2228 defines four possible protection levels,
            # RFC-4217 only recommends two, Clear and Private.
            # Clear (PROT C) means that no security is to be used on the
            # data-channel, Private (PROT P) means that the data-channel
            # should be protected by TLS.
            # PBSZ command MUST still be issued, but must have a parameter of
            # '0' to indicate that no buffering is taking place and the data
            # connection should not be encapsulated.
            self.voidcmd('PBSZ 0')
            resp = self.voidcmd('PROT P')
            self._prot_p = True
            return resp

        def prot_c(self):
            '''Set up clear text data connection.'''
            resp = self.voidcmd('PROT C')
            self._prot_p = False
            return resp

        # --- Overridden FTP methods

        def ntransfercmd(self, cmd, rest=None):
            conn, size = FTP.ntransfercmd(self, cmd, rest)
            if self._prot_p:
                conn = ssl.wrap_socket(conn, self.keyfile, self.certfile,
                                       ssl_version=self.ssl_version)
            return conn, size

        def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
            self.voidcmd('TYPE I')
            conn = self.transfercmd(cmd, rest)
            try:
                while 1:
                    data = conn.recv(blocksize)
                    if not data:
                        break
                    callback(data)
                # shutdown ssl layer
                if isinstance(conn, ssl.SSLSocket):
                    conn.unwrap()
            finally:
                conn.close()
            return self.voidresp()

        def retrlines(self, cmd, callback = None):
            if callback is None: callback = print_line
            resp = self.sendcmd('TYPE A')
            conn = self.transfercmd(cmd)
            fp = conn.makefile('rb')
            try:
                while 1:
                    line = fp.readline()
                    if self.debugging > 2: print ('*retr*', repr(line))
                    if not line:
                        break
                    if line[-2:] == CRLF:
                        line = line[:-2]
                    elif line[-1:] == '\n':
                        line = line[:-1]
                    callback(line)
                # shutdown ssl layer
                if isinstance(conn, ssl.SSLSocket):
                    conn.unwrap()
            finally:
                fp.close()
                conn.close()
            return self.voidresp()

        def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
            self.voidcmd('TYPE I')
            conn = self.transfercmd(cmd, rest)
            try:
                while 1:
                    buf = fp.read(blocksize)
                    if not buf: break
                    conn.sendall(buf)
                    if callback: callback(buf)
                # shutdown ssl layer
                if isinstance(conn, ssl.SSLSocket):
                    conn.unwrap()
            finally:
                conn.close()
            return self.voidresp()

        def storlines(self, cmd, fp, callback=None):
            self.voidcmd('TYPE A')
            conn = self.transfercmd(cmd)
            try:
                while 1:
                    buf = fp.readline()
                    if not buf: break
                    if buf[-2:] != CRLF:
                        if buf[-1] in CRLF: buf = buf[:-1]
                        buf = buf + CRLF
                    conn.sendall(buf)
                    if callback: callback(buf)
                # shutdown ssl layer
                if isinstance(conn, ssl.SSLSocket):
                    conn.unwrap()
            finally:
                conn.close()
            return self.voidresp()

    __all__.append('FTP_TLS')
    all_errors = (Error, IOError, EOFError, ssl.SSLError)


_150_re = None

def parse150(resp):
    '''Parse the '150' response for a RETR request.
    Returns the expected transfer size or None; size is not guaranteed to
    be present in the 150 message.
    '''
    if resp[:3] != '150':
        raise error_reply (resp)
    global _150_re
    if _150_re is None:
        import re
        _150_re = re.compile("150 .* \((\d+) bytes\)", re.IGNORECASE)
    m = _150_re.match(resp)
    if not m:
        return None
    s = m.group(1)
    try:
        return int(s)
    except (OverflowError, ValueError):
        return long(s)


_227_re = None

def parse227(resp):
    '''Parse the '227' response for a PASV request.
    Raises error_proto if it does not contain '(h1,h2,h3,h4,p1,p2)'
    Return ('host.addr.as.numbers', port#) tuple.'''

    if resp[:3] != '227':
        raise error_reply(resp)
    global _227_re
    if _227_re is None:
        import re
        _227_re = re.compile(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)')
    m = _227_re.search(resp)
    if not m:
        raise error_proto(resp)
    numbers = m.groups()
    host = '.'.join(numbers[:4])
    port = (int(numbers[4]) << 8) + int(numbers[5])
    return host, port


def parse229(resp, peer):
    '''Parse the '229' response for a EPSV request.
    Raises error_proto if it does not contain '(|||port|)'
    Return ('host.addr.as.numbers', port#) tuple.'''

    if resp[:3] != '229':
        raise error_reply(resp)
    left = resp.find('(')
    if left < 0: raise error_proto(resp)
    right = resp.find(')', left + 1)
    if right < 0:
        raise error_proto(resp) # should contain '(|||port|)'
    if resp[left + 1] != resp[right - 1]:
        raise error_proto(resp)
    parts = resp[left + 1:right].split(resp[left+1])
    if len(parts) != 5:
        raise error_proto(resp)
    host = peer[0]
    port = int(parts[3])
    return host, port


def parse257(resp):
    '''Parse the '257' response for a MKD or PWD request.
    This is a response to a MKD or PWD request: a directory name.
    Returns the directoryname in the 257 reply.'''

    if resp[:3] != '257':
        raise error_reply(resp)
    if resp[3:5] != ' "':
        return '' # Not compliant to RFC 959, but UNIX ftpd does this
    dirname = ''
    i = 5
    n = len(resp)
    while i < n:
        c = resp[i]
        i = i+1
        if c == '"':
            if i >= n or resp[i] != '"':
                break
            i = i+1
        dirname = dirname + c
    return dirname


def print_line(line):
    '''Default retrlines callback to print a line.'''
    print (line)


def ftpcp(source, sourcename, target, targetname = '', type = 'I'):
    '''Copy file from one FTP-instance to another.'''
    if not targetname: targetname = sourcename
    type = 'TYPE ' + type
    source.voidcmd(type)
    target.voidcmd(type)
    sourcehost, sourceport = parse227(source.sendcmd('PASV'))
    target.sendport(sourcehost, sourceport)
    # RFC 959: the user must "listen" [...] BEFORE sending the
    # transfer request.
    # So: STOR before RETR, because here the target is a "user".
    treply = target.sendcmd('STOR ' + targetname)
    if treply[:3] not in ('125', '150'): raise error_proto  # RFC 959
    sreply = source.sendcmd('RETR ' + sourcename)
    if sreply[:3] not in ('125', '150'): raise error_proto  # RFC 959
    source.voidresp()
    target.voidresp()


class Netrc:
    """Class to parse & provide access to 'netrc' format files.

    See the netrc(4) man page for information on the file format.

    WARNING: This class is obsolete -- use module netrc instead.

    """
    __defuser = None
    __defpasswd = None
    __defacct = None

    def __init__(self, filename=None):
        if filename is None:
            if "HOME" in os.environ:
                filename = os.path.join(os.environ["HOME"],
                                        ".netrc")
            else:
                raise IOError("specify file to load or set $HOME")
        self.__hosts = {}
        self.__macros = {}
        fp = open(filename, "r")
        in_macro = 0
        while 1:
            line = fp.readline()
            if not line: break
            if in_macro and line.strip():
                macro_lines.append(line)
                continue
            elif in_macro:
                self.__macros[macro_name] = tuple(macro_lines)
                in_macro = 0
            words = line.split()
            host = user = passwd = acct = None
            default = 0
            i = 0
            while i < len(words):
                w1 = words[i]
                if i+1 < len(words):
                    w2 = words[i + 1]
                else:
                    w2 = None
                if w1 == 'default':
                    default = 1
                elif w1 == 'machine' and w2:
                    host = w2.lower()
                    i = i + 1
                elif w1 == 'login' and w2:
                    user = w2
                    i = i + 1
                elif w1 == 'password' and w2:
                    passwd = w2
                    i = i + 1
                elif w1 == 'account' and w2:
                    acct = w2
                    i = i + 1
                elif w1 == 'macdef' and w2:
                    macro_name = w2
                    macro_lines = []
                    in_macro = 1
                    break
                i = i + 1
            if default:
                self.__defuser = user or self.__defuser
                self.__defpasswd = passwd or self.__defpasswd
                self.__defacct = acct or self.__defacct
            if host:
                if host in self.__hosts:
                    ouser, opasswd, oacct = \
                           self.__hosts[host]
                    user = user or ouser
                    passwd = passwd or opasswd
                    acct = acct or oacct
                self.__hosts[host] = user, passwd, acct
        fp.close()

    def get_hosts(self):
        """Return a list of hosts mentioned in the .netrc file."""
        return self.__hosts.keys()

    def get_account(self, host):
        """Returns login information for the named host.

        The return value is a triple containing userid,
        password, and the accounting field.

        """
        host = host.lower()
        user = passwd = acct = None
        if host in self.__hosts:
            user, passwd, acct = self.__hosts[host]
        user = user or self.__defuser
        passwd = passwd or self.__defpasswd
        acct = acct or self.__defacct
        return user, passwd, acct

    def get_macros(self):
        """Return a list of all defined macro names."""
        return self.__macros.keys()

    def get_macro(self, macro):
        """Return a sequence of lines which define a named macro."""
        return self.__macros[macro]



def test():
    '''Test program.
    Usage: ftp [-d] [-r[file]] host [-l[dir]] [-d[dir]] [-p] [file] ...

    -d dir
    -l list
    -p password
    '''

    if len(sys.argv) < 2:
        print (test.__doc__)
        sys.exit(0)

    debugging = 0
    rcfile = None
    while sys.argv[1] == '-d':
        debugging = debugging+1
        del sys.argv[1]
    if sys.argv[1][:2] == '-r':
        # get name of alternate ~/.netrc file:
        rcfile = sys.argv[1][2:]
        del sys.argv[1]
    host = sys.argv[1]
    ftp = FTP(host)
    ftp.set_debuglevel(debugging)
    userid = passwd = acct = ''
    try:
        netrc = Netrc(rcfile)
    except IOError:
        if rcfile is not None:
            sys.stderr.write("Could not open account file"
                             " -- using anonymous login.")
    else:
        try:
            userid, passwd, acct = netrc.get_account(host)
        except KeyError:
            # no account for host
            sys.stderr.write(
                    "No account -- using anonymous login.")
    ftp.login(userid, passwd, acct)
    for file in sys.argv[2:]:
        if file[:2] == '-l':
            ftp.dir(file[2:])
        elif file[:2] == '-d':
            cmd = 'CWD'
            if file[2:]: cmd = cmd + ' ' + file[2:]
            resp = ftp.sendcmd(cmd)
        elif file == '-p':
            ftp.set_pasv(not ftp.passiveserver)
        else:
            ftp.retrbinary('RETR ' + file, \
                           sys.stdout.write, 1024)
    ftp.quit()


if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = ssl
# Wrapper module for _ssl, providing some additional facilities
# implemented in Python.  Written by Bill Janssen.

"""\
This module provides some more Pythonic support for SSL.

Object types:

  SSLSocket -- subtype of socket.socket which does SSL over the socket

Exceptions:

  SSLError -- exception raised for I/O errors

Functions:

  cert_time_to_seconds -- convert time string used for certificate
                          notBefore and notAfter functions to integer
                          seconds past the Epoch (the time values
                          returned from time.time())

  fetch_server_certificate (HOST, PORT) -- fetch the certificate provided
                          by the server running on HOST at port PORT.  No
                          validation of the certificate is performed.

Integer constants:

SSL_ERROR_ZERO_RETURN
SSL_ERROR_WANT_READ
SSL_ERROR_WANT_WRITE
SSL_ERROR_WANT_X509_LOOKUP
SSL_ERROR_SYSCALL
SSL_ERROR_SSL
SSL_ERROR_WANT_CONNECT

SSL_ERROR_EOF
SSL_ERROR_INVALID_ERROR_CODE

The following group define certificate requirements that one side is
allowing/requiring from the other side:

CERT_NONE - no certificates from the other side are required (or will
            be looked at if provided)
CERT_OPTIONAL - certificates are not required, but if provided will be
                validated, and if validation fails, the connection will
                also fail
CERT_REQUIRED - certificates are required, and will be validated, and
                if validation fails, the connection will also fail

The following constants identify various SSL protocol variants:

PROTOCOL_SSLv2
PROTOCOL_SSLv3
PROTOCOL_SSLv23
PROTOCOL_TLSv1
"""

import textwrap

import _ssl             # if we can't import it, let the error propagate

from _ssl import SSLError
from _ssl import CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED
from _ssl import PROTOCOL_SSLv2, PROTOCOL_SSLv3, PROTOCOL_SSLv23, PROTOCOL_TLSv1
from _ssl import RAND_status, RAND_egd, RAND_add
from _ssl import \
     SSL_ERROR_ZERO_RETURN, \
     SSL_ERROR_WANT_READ, \
     SSL_ERROR_WANT_WRITE, \
     SSL_ERROR_WANT_X509_LOOKUP, \
     SSL_ERROR_SYSCALL, \
     SSL_ERROR_SSL, \
     SSL_ERROR_WANT_CONNECT, \
     SSL_ERROR_EOF, \
     SSL_ERROR_INVALID_ERROR_CODE

from socket import socket, _fileobject, _delegate_methods
from socket import error as socket_error
from socket import getnameinfo as _getnameinfo
import base64        # for DER-to-PEM translation
import errno

class SSLSocket(socket):

    """This class implements a subtype of socket.socket that wraps
    the underlying OS socket in an SSL context when necessary, and
    provides read and write methods over that channel."""

    def __init__(self, sock, keyfile=None, certfile=None,
                 server_side=False, cert_reqs=CERT_NONE,
                 ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                 do_handshake_on_connect=True,
                 suppress_ragged_eofs=True):
        socket.__init__(self, _sock=sock._sock)
        # The initializer for socket overrides the methods send(), recv(), etc.
        # in the instancce, which we don't need -- but we want to provide the
        # methods defined in SSLSocket.
        for attr in _delegate_methods:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

        if certfile and not keyfile:
            keyfile = certfile
        # see if it's connected
        try:
            socket.getpeername(self)
        except socket_error, e:
            if e.errno != errno.ENOTCONN:
                raise
            # no, no connection yet
            self._sslobj = None
        else:
            # yes, create the SSL object
            self._sslobj = _ssl.sslwrap(self._sock, server_side,
                                        keyfile, certfile,
                                        cert_reqs, ssl_version, ca_certs)
            if do_handshake_on_connect:
                self.do_handshake()
        self.keyfile = keyfile
        self.certfile = certfile
        self.cert_reqs = cert_reqs
        self.ssl_version = ssl_version
        self.ca_certs = ca_certs
        self.do_handshake_on_connect = do_handshake_on_connect
        self.suppress_ragged_eofs = suppress_ragged_eofs
        self._makefile_refs = 0

    def read(self, len=1024):

        """Read up to LEN bytes and return them.
        Return zero-length string on EOF."""

        try:
            return self._sslobj.read(len)
        except SSLError, x:
            if x.args[0] == SSL_ERROR_EOF and self.suppress_ragged_eofs:
                return ''
            else:
                raise

    def write(self, data):

        """Write DATA to the underlying SSL channel.  Returns
        number of bytes of DATA actually transmitted."""

        return self._sslobj.write(data)

    def getpeercert(self, binary_form=False):

        """Returns a formatted version of the data in the
        certificate provided by the other end of the SSL channel.
        Return None if no certificate was provided, {} if a
        certificate was provided, but not validated."""

        return self._sslobj.peer_certificate(binary_form)

    def cipher(self):

        if not self._sslobj:
            return None
        else:
            return self._sslobj.cipher()

    def send(self, data, flags=0):
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to send() on %s" %
                    self.__class__)
            while True:
                try:
                    v = self._sslobj.write(data)
                except SSLError, x:
                    if x.args[0] == SSL_ERROR_WANT_READ:
                        return 0
                    elif x.args[0] == SSL_ERROR_WANT_WRITE:
                        return 0
                    else:
                        raise
                else:
                    return v
        else:
            return socket.send(self, data, flags)

    def sendto(self, data, addr, flags=0):
        if self._sslobj:
            raise ValueError("sendto not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.sendto(self, data, addr, flags)

    def sendall(self, data, flags=0):
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to sendall() on %s" %
                    self.__class__)
            amount = len(data)
            count = 0
            while (count < amount):
                v = self.send(data[count:])
                count += v
            return amount
        else:
            return socket.sendall(self, data, flags)

    def recv(self, buflen=1024, flags=0):
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to recv() on %s" %
                    self.__class__)
            return self.read(buflen)
        else:
            return socket.recv(self, buflen, flags)

    def recv_into(self, buffer, nbytes=None, flags=0):
        if buffer and (nbytes is None):
            nbytes = len(buffer)
        elif nbytes is None:
            nbytes = 1024
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                  "non-zero flags not allowed in calls to recv_into() on %s" %
                  self.__class__)
            tmp_buffer = self.read(nbytes)
            v = len(tmp_buffer)
            buffer[:v] = tmp_buffer
            return v
        else:
            return socket.recv_into(self, buffer, nbytes, flags)

    def recvfrom(self, addr, buflen=1024, flags=0):
        if self._sslobj:
            raise ValueError("recvfrom not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.recvfrom(self, addr, buflen, flags)

    def recvfrom_into(self, buffer, nbytes=None, flags=0):
        if self._sslobj:
            raise ValueError("recvfrom_into not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.recvfrom_into(self, buffer, nbytes, flags)

    def pending(self):
        if self._sslobj:
            return self._sslobj.pending()
        else:
            return 0

    def unwrap(self):
        if self._sslobj:
            s = self._sslobj.shutdown()
            self._sslobj = None
            return s
        else:
            raise ValueError("No SSL wrapper around " + str(self))

    def shutdown(self, how):
        self._sslobj = None
        socket.shutdown(self, how)

    def close(self):
        if self._makefile_refs < 1:
            self._sslobj = None
            socket.close(self)
        else:
            self._makefile_refs -= 1

    def do_handshake(self):

        """Perform a TLS/SSL handshake."""

        self._sslobj.do_handshake()

    def connect(self, addr):

        """Connects to remote ADDR, and then wraps the connection in
        an SSL channel."""

        # Here we assume that the socket is client-side, and not
        # connected at the time of the call.  We connect it, then wrap it.
        if self._sslobj:
            raise ValueError("attempt to connect already-connected SSLSocket!")
        socket.connect(self, addr)
        self._sslobj = _ssl.sslwrap(self._sock, False, self.keyfile, self.certfile,
                                    self.cert_reqs, self.ssl_version,
                                    self.ca_certs)
        if self.do_handshake_on_connect:
            self.do_handshake()

    def accept(self):

        """Accepts a new connection from a remote client, and returns
        a tuple containing that new connection wrapped with a server-side
        SSL channel, and the address of the remote client."""

        newsock, addr = socket.accept(self)
        return (SSLSocket(newsock,
                          keyfile=self.keyfile,
                          certfile=self.certfile,
                          server_side=True,
                          cert_reqs=self.cert_reqs,
                          ssl_version=self.ssl_version,
                          ca_certs=self.ca_certs,
                          do_handshake_on_connect=self.do_handshake_on_connect,
                          suppress_ragged_eofs=self.suppress_ragged_eofs),
                addr)

    def makefile(self, mode='r', bufsize=-1):

        """Make and return a file-like object that
        works with the SSL connection.  Just use the code
        from the socket module."""

        self._makefile_refs += 1
        # close=True so as to decrement the reference count when done with
        # the file-like object.
        return _fileobject(self, mode, bufsize, close=True)



def wrap_socket(sock, keyfile=None, certfile=None,
                server_side=False, cert_reqs=CERT_NONE,
                ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                do_handshake_on_connect=True,
                suppress_ragged_eofs=True):

    return SSLSocket(sock, keyfile=keyfile, certfile=certfile,
                     server_side=server_side, cert_reqs=cert_reqs,
                     ssl_version=ssl_version, ca_certs=ca_certs,
                     do_handshake_on_connect=do_handshake_on_connect,
                     suppress_ragged_eofs=suppress_ragged_eofs)


# some utility functions

def cert_time_to_seconds(cert_time):

    """Takes a date-time string in standard ASN1_print form
    ("MON DAY 24HOUR:MINUTE:SEC YEAR TIMEZONE") and return
    a Python time value in seconds past the epoch."""

    import time
    return time.mktime(time.strptime(cert_time, "%b %d %H:%M:%S %Y GMT"))

PEM_HEADER = "-----BEGIN CERTIFICATE-----"
PEM_FOOTER = "-----END CERTIFICATE-----"

def DER_cert_to_PEM_cert(der_cert_bytes):

    """Takes a certificate in binary DER format and returns the
    PEM version of it as a string."""

    if hasattr(base64, 'standard_b64encode'):
        # preferred because older API gets line-length wrong
        f = base64.standard_b64encode(der_cert_bytes)
        return (PEM_HEADER + '\n' +
                textwrap.fill(f, 64) + '\n' +
                PEM_FOOTER + '\n')
    else:
        return (PEM_HEADER + '\n' +
                base64.encodestring(der_cert_bytes) +
                PEM_FOOTER + '\n')

def PEM_cert_to_DER_cert(pem_cert_string):

    """Takes a certificate in ASCII PEM format and returns the
    DER-encoded version of it as a byte sequence"""

    if not pem_cert_string.startswith(PEM_HEADER):
        raise ValueError("Invalid PEM encoding; must start with %s"
                         % PEM_HEADER)
    if not pem_cert_string.strip().endswith(PEM_FOOTER):
        raise ValueError("Invalid PEM encoding; must end with %s"
                         % PEM_FOOTER)
    d = pem_cert_string.strip()[len(PEM_HEADER):-len(PEM_FOOTER)]
    return base64.decodestring(d)

def get_server_certificate(addr, ssl_version=PROTOCOL_SSLv3, ca_certs=None):

    """Retrieve the certificate from the server at the specified address,
    and return it as a PEM-encoded string.
    If 'ca_certs' is specified, validate the server cert against it.
    If 'ssl_version' is specified, use it in the connection attempt."""

    host, port = addr
    if (ca_certs is not None):
        cert_reqs = CERT_REQUIRED
    else:
        cert_reqs = CERT_NONE
    s = wrap_socket(socket(), ssl_version=ssl_version,
                    cert_reqs=cert_reqs, ca_certs=ca_certs)
    s.connect(addr)
    dercert = s.getpeercert(True)
    s.close()
    return DER_cert_to_PEM_cert(dercert)

def get_protocol_name(protocol_code):
    if protocol_code == PROTOCOL_TLSv1:
        return "TLSv1"
    elif protocol_code == PROTOCOL_SSLv23:
        return "SSLv23"
    elif protocol_code == PROTOCOL_SSLv2:
        return "SSLv2"
    elif protocol_code == PROTOCOL_SSLv3:
        return "SSLv3"
    else:
        return "<unknown>"


# a replacement for the old socket.ssl function

def sslwrap_simple(sock, keyfile=None, certfile=None):

    """A replacement for the old socket.ssl function.  Designed
    for compability with Python 2.5 and earlier.  Will disappear in
    Python 3.0."""

    if hasattr(sock, "_sock"):
        sock = sock._sock

    ssl_sock = _ssl.sslwrap(sock, 0, keyfile, certfile, CERT_NONE,
                            PROTOCOL_SSLv23, None)
    try:
        sock.getpeername()
    except:
        # no, no connection yet
        pass
    else:
        # yes, do the handshake
        ssl_sock.do_handshake()

    return ssl_sock

########NEW FILE########
__FILENAME__ = ftplib
"""An FTP client class and some helper functions.

Based on RFC 959: File Transfer Protocol (FTP), by J. Postel and J. Reynolds

Example:

>>> from ftplib import FTP
>>> ftp = FTP('ftp.python.org') # connect to host, default port
>>> ftp.login() # default, i.e.: user anonymous, passwd anonymous@
'230 Guest login ok, access restrictions apply.'
>>> ftp.retrlines('LIST') # list directory contents
total 9
drwxr-xr-x   8 root     wheel        1024 Jan  3  1994 .
drwxr-xr-x   8 root     wheel        1024 Jan  3  1994 ..
drwxr-xr-x   2 root     wheel        1024 Jan  3  1994 bin
drwxr-xr-x   2 root     wheel        1024 Jan  3  1994 etc
d-wxrwxr-x   2 ftp      wheel        1024 Sep  5 13:43 incoming
drwxr-xr-x   2 root     wheel        1024 Nov 17  1993 lib
drwxr-xr-x   6 1094     wheel        1024 Sep 13 19:07 pub
drwxr-xr-x   3 root     wheel        1024 Jan  3  1994 usr
-rw-r--r--   1 root     root          312 Aug  1  1994 welcome.msg
'226 Transfer complete.'
>>> ftp.quit()
'221 Goodbye.'
>>>

A nice test that reveals some of the network dialogue would be:
python ftplib.py -d localhost -l -p -l
"""

#
# Changes and improvements suggested by Steve Majewski.
# Modified by Jack to work on the mac.
# Modified by Siebren to support docstrings and PASV.
# Modified by Phil Schwartz to add storbinary and storlines callbacks.
# Modified by Giampaolo Rodola' to add TLS support.
#

import os
import sys
import socket
from socket import _GLOBAL_DEFAULT_TIMEOUT

__all__ = ["FTP","Netrc"]

# Magic number from <socket.h>
MSG_OOB = 0x1                           # Process data out of band


# The standard FTP server control port
FTP_PORT = 21


# Exception raised when an error or invalid response is received
class Error(Exception): pass
class error_reply(Error): pass          # unexpected [123]xx reply
class error_temp(Error): pass           # 4xx errors
class error_perm(Error): pass           # 5xx errors
class error_proto(Error): pass          # response does not begin with [1-5]


# All exceptions (hopefully) that may be raised here and that aren't
# (always) programming errors on our side
all_errors = (Error, IOError, EOFError)


# Line terminators (we always output CRLF, but accept any of CRLF, CR, LF)
CRLF = '\r\n'
B_CRLF = b'\r\n'

# The class itself
class FTP:

    '''An FTP client class.

    To create a connection, call the class using these arguments:
            host, user, passwd, acct, timeout

    The first four arguments are all strings, and have default value ''.
    timeout must be numeric and defaults to None if not passed,
    meaning that no timeout will be set on any ftp socket(s)
    If a timeout is passed, then this is now the default timeout for all ftp
    socket operations for this instance.

    Then use self.connect() with optional host and port argument.

    To download a file, use ftp.retrlines('RETR ' + filename),
    or ftp.retrbinary() with slightly different arguments.
    To upload a file, use ftp.storlines() or ftp.storbinary(),
    which have an open file as argument (see their definitions
    below for details).
    The download/upload functions first issue appropriate TYPE
    and PORT or PASV commands.
    '''

    debugging = 0
    host = ''
    port = FTP_PORT
    sock = None
    file = None
    welcome = None
    passiveserver = 1
    encoding = "latin-1"

    # Initialization method (called by class instantiation).
    # Initialize host to localhost, port to standard ftp port
    # Optional arguments are host (for connect()),
    # and user, passwd, acct (for login())
    def __init__(self, host='', user='', passwd='', acct='',
                 timeout=_GLOBAL_DEFAULT_TIMEOUT, source_address=None):
        self.source_address = source_address
        self.timeout = timeout
        if host:
            self.connect(host)
            if user:
                self.login(user, passwd, acct)

    def __enter__(self):
        return self

    # Context management protocol: try to quit() if active
    def __exit__(self, *args):
        if self.sock is not None:
            try:
                self.quit()
            except (socket.error, EOFError):
                pass
            finally:
                if self.sock is not None:
                    self.close()

    def connect(self, host='', port=0, timeout=-999, source_address=None):
        '''Connect to host.  Arguments are:
         - host: hostname to connect to (string, default previous host)
         - port: port to connect to (integer, default previous port)
         - source_address: a 2-tuple (host, port) for the socket to bind
           to as its source address before connecting.
        '''
        if host != '':
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        if source_address is not None:
            self.source_address = source_address
        self.sock = socket.create_connection((self.host, self.port), self.timeout,
                                             source_address=self.source_address)
        self.af = self.sock.family
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

    def getwelcome(self):
        '''Get the welcome message from the server.
        (this is read and squirreled away by connect())'''
        if self.debugging:
            print('*welcome*', self.sanitize(self.welcome))
        return self.welcome

    def set_debuglevel(self, level):
        '''Set the debugging level.
        The required argument level means:
        0: no debugging output (default)
        1: print commands and responses but not body text etc.
        2: also print raw lines read and sent before stripping CR/LF'''
        self.debugging = level
    debug = set_debuglevel

    def set_pasv(self, val):
        '''Use passive or active mode for data transfers.
        With a false argument, use the normal PORT mode,
        With a true argument, use the PASV command.'''
        self.passiveserver = val

    # Internal: "sanitize" a string for printing
    def sanitize(self, s):
        if s[:5] in {'pass ', 'PASS '}:
            i = len(s.rstrip('\r\n'))
            s = s[:5] + '*'*(i-5) + s[i:]
        return repr(s)

    # Internal: send one line to the server, appending CRLF
    def putline(self, line):
        line = line + CRLF
        if self.debugging > 1: print('*put*', self.sanitize(line))
        self.sock.sendall(line.encode(self.encoding))

    # Internal: send one command to the server (through putline())
    def putcmd(self, line):
        if self.debugging: print('*cmd*', self.sanitize(line))
        self.putline(line)

    # Internal: return one line from the server, stripping CRLF.
    # Raise EOFError if the connection is closed
    def getline(self):
        line = self.file.readline()
        if self.debugging > 1:
            print('*get*', self.sanitize(line))
        if not line: raise EOFError
        if line[-2:] == CRLF: line = line[:-2]
        elif line[-1:] in CRLF: line = line[:-1]
        return line

    # Internal: get a response from the server, which may possibly
    # consist of multiple lines.  Return a single string with no
    # trailing CRLF.  If the response consists of multiple lines,
    # these are separated by '\n' characters in the string
    def getmultiline(self):
        line = self.getline()
        if line[3:4] == '-':
            code = line[:3]
            while 1:
                nextline = self.getline()
                line = line + ('\n' + nextline)
                if nextline[:3] == code and \
                        nextline[3:4] != '-':
                    break
        return line

    # Internal: get a response from the server.
    # Raise various errors if the response indicates an error
    def getresp(self):
        resp = self.getmultiline()
        if self.debugging: print('*resp*', self.sanitize(resp))
        self.lastresp = resp[:3]
        c = resp[:1]
        if c in {'1', '2', '3'}:
            return resp
        if c == '4':
            raise error_temp(resp)
        if c == '5':
            raise error_perm(resp)
        raise error_proto(resp)

    def voidresp(self):
        """Expect a response beginning with '2'."""
        resp = self.getresp()
        if resp[:1] != '2':
            raise error_reply(resp)
        return resp

    def abort(self):
        '''Abort a file transfer.  Uses out-of-band data.
        This does not follow the procedure from the RFC to send Telnet
        IP and Synch; that doesn't seem to work with the servers I've
        tried.  Instead, just send the ABOR command as OOB data.'''
        line = b'ABOR' + B_CRLF
        if self.debugging > 1: print('*put urgent*', self.sanitize(line))
        self.sock.sendall(line, MSG_OOB)
        resp = self.getmultiline()
        if resp[:3] not in {'426', '225', '226'}:
            raise error_proto(resp)
        return resp

    def sendcmd(self, cmd):
        '''Send a command and return the response.'''
        self.putcmd(cmd)
        return self.getresp()

    def voidcmd(self, cmd):
        """Send a command and expect a response beginning with '2'."""
        self.putcmd(cmd)
        return self.voidresp()

    def sendport(self, host, port):
        '''Send a PORT command with the current host and the given
        port number.
        '''
        hbytes = host.split('.')
        pbytes = [repr(port//256), repr(port%256)]
        bytes = hbytes + pbytes
        cmd = 'PORT ' + ','.join(bytes)
        return self.voidcmd(cmd)

    def sendeprt(self, host, port):
        '''Send a EPRT command with the current host and the given port number.'''
        af = 0
        if self.af == socket.AF_INET:
            af = 1
        if self.af == socket.AF_INET6:
            af = 2
        if af == 0:
            raise error_proto('unsupported address family')
        fields = ['', repr(af), host, repr(port), '']
        cmd = 'EPRT ' + '|'.join(fields)
        return self.voidcmd(cmd)

    def makeport(self):
        '''Create a new socket and send a PORT command for it.'''
        err = None
        sock = None
        for res in socket.getaddrinfo(None, 0, self.af, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                sock = socket.socket(af, socktype, proto)
                sock.bind(sa)
            except socket.error as _:
                err = _
                if sock:
                    sock.close()
                sock = None
                continue
            break
        if sock is None:
            if err is not None:
                raise err
            else:
                raise socket.error("getaddrinfo returns an empty list")
            raise socket.error(msg)
        sock.listen(1)
        port = sock.getsockname()[1] # Get proper port
        host = self.sock.getsockname()[0] # Get proper host
        if self.af == socket.AF_INET:
            resp = self.sendport(host, port)
        else:
            resp = self.sendeprt(host, port)
        if self.timeout is not _GLOBAL_DEFAULT_TIMEOUT:
            sock.settimeout(self.timeout)
        return sock

    def makepasv(self):
        if self.af == socket.AF_INET:
            host, port = parse227(self.sendcmd('PASV'))
        else:
            host, port = parse229(self.sendcmd('EPSV'), self.sock.getpeername())
        return host, port

    def ntransfercmd(self, cmd, rest=None):
        """Initiate a transfer over the data connection.

        If the transfer is active, send a port command and the
        transfer command, and accept the connection.  If the server is
        passive, send a pasv command, connect to it, and start the
        transfer command.  Either way, return the socket for the
        connection and the expected size of the transfer.  The
        expected size may be None if it could not be determined.

        Optional `rest' argument can be a string that is sent as the
        argument to a REST command.  This is essentially a server
        marker used to tell the server to skip over any data up to the
        given marker.
        """
        size = None
        if self.passiveserver:
            host, port = self.makepasv()
            conn = socket.create_connection((host, port), self.timeout,
                                            source_address=self.source_address)
            try:
                if rest is not None:
                    self.sendcmd("REST %s" % rest)
                resp = self.sendcmd(cmd)
                # Some servers apparently send a 200 reply to
                # a LIST or STOR command, before the 150 reply
                # (and way before the 226 reply). This seems to
                # be in violation of the protocol (which only allows
                # 1xx or error messages for LIST), so we just discard
                # this response.
                if resp[0] == '2':
                    resp = self.getresp()
                if resp[0] != '1':
                    raise error_reply(resp)
            except:
                conn.close()
                raise
        else:
            with self.makeport() as sock:
                if rest is not None:
                    self.sendcmd("REST %s" % rest)
                resp = self.sendcmd(cmd)
                # See above.
                if resp[0] == '2':
                    resp = self.getresp()
                if resp[0] != '1':
                    raise error_reply(resp)
                conn, sockaddr = sock.accept()
                if self.timeout is not _GLOBAL_DEFAULT_TIMEOUT:
                    conn.settimeout(self.timeout)
        if resp[:3] == '150':
            # this is conditional in case we received a 125
            size = parse150(resp)
        return conn, size

    def transfercmd(self, cmd, rest=None):
        """Like ntransfercmd() but returns only the socket."""
        return self.ntransfercmd(cmd, rest)[0]

    def login(self, user = '', passwd = '', acct = ''):
        '''Login, default anonymous.'''
        if not user: user = 'anonymous'
        if not passwd: passwd = ''
        if not acct: acct = ''
        if user == 'anonymous' and passwd in {'', '-'}:
            # If there is no anonymous ftp password specified
            # then we'll just use anonymous@
            # We don't send any other thing because:
            # - We want to remain anonymous
            # - We want to stop SPAM
            # - We don't want to let ftp sites to discriminate by the user,
            #   host or country.
            passwd = passwd + 'anonymous@'
        resp = self.sendcmd('USER ' + user)
        if resp[0] == '3': resp = self.sendcmd('PASS ' + passwd)
        if resp[0] == '3': resp = self.sendcmd('ACCT ' + acct)
        if resp[0] != '2':
            raise error_reply(resp)
        return resp

    def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
        """Retrieve data in binary mode.  A new port is created for you.

        Args:
          cmd: A RETR command.
          callback: A single parameter callable to be called on each
                    block of data read.
          blocksize: The maximum number of bytes to read from the
                     socket at one time.  [default: 8192]
          rest: Passed to transfercmd().  [default: None]

        Returns:
          The response code.
        """
        self.voidcmd('TYPE I')
        with self.transfercmd(cmd, rest) as conn:
            while 1:
                data = conn.recv(blocksize)
                if not data:
                    break
                callback(data)
        return self.voidresp()

    def retrlines(self, cmd, callback = None):
        """Retrieve data in line mode.  A new port is created for you.

        Args:
          cmd: A RETR, LIST, or NLST command.
          callback: An optional single parameter callable that is called
                    for each line with the trailing CRLF stripped.
                    [default: print_line()]

        Returns:
          The response code.
        """
        if callback is None: callback = print_line
        resp = self.sendcmd('TYPE A')
        with self.transfercmd(cmd) as conn, \
                 conn.makefile('r', encoding=self.encoding) as fp:
            while 1:
                line = fp.readline()
                if self.debugging > 2: print('*retr*', repr(line))
                if not line:
                    break
                if line[-2:] == CRLF:
                    line = line[:-2]
                elif line[-1:] == '\n':
                    line = line[:-1]
                callback(line)
        return self.voidresp()

    def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
        """Store a file in binary mode.  A new port is created for you.

        Args:
          cmd: A STOR command.
          fp: A file-like object with a read(num_bytes) method.
          blocksize: The maximum data size to read from fp and send over
                     the connection at once.  [default: 8192]
          callback: An optional single parameter callable that is called on
                    each block of data after it is sent.  [default: None]
          rest: Passed to transfercmd().  [default: None]

        Returns:
          The response code.
        """
        self.voidcmd('TYPE I')
        with self.transfercmd(cmd, rest) as conn:
            while 1:
                buf = fp.read(blocksize)
                if not buf: break
                conn.sendall(buf)
                if callback: callback(buf)
        return self.voidresp()

    def storlines(self, cmd, fp, callback=None):
        """Store a file in line mode.  A new port is created for you.

        Args:
          cmd: A STOR command.
          fp: A file-like object with a readline() method.
          callback: An optional single parameter callable that is called on
                    each line after it is sent.  [default: None]

        Returns:
          The response code.
        """
        self.voidcmd('TYPE A')
        with self.transfercmd(cmd) as conn:
            while 1:
                buf = fp.readline()
                if not buf: break
                if buf[-2:] != B_CRLF:
                    if buf[-1] in B_CRLF: buf = buf[:-1]
                    buf = buf + B_CRLF
                conn.sendall(buf)
                if callback: callback(buf)
        return self.voidresp()

    def acct(self, password):
        '''Send new account name.'''
        cmd = 'ACCT ' + password
        return self.voidcmd(cmd)

    def nlst(self, *args):
        '''Return a list of files in a given directory (default the current).'''
        cmd = 'NLST'
        for arg in args:
            cmd = cmd + (' ' + arg)
        files = []
        self.retrlines(cmd, files.append)
        return files

    def dir(self, *args):
        '''List a directory in long form.
        By default list current directory to stdout.
        Optional last argument is callback function; all
        non-empty arguments before it are concatenated to the
        LIST command.  (This *should* only be used for a pathname.)'''
        cmd = 'LIST'
        func = None
        if args[-1:] and type(args[-1]) != type(''):
            args, func = args[:-1], args[-1]
        for arg in args:
            if arg:
                cmd = cmd + (' ' + arg)
        self.retrlines(cmd, func)

    def mlsd(self, path="", facts=[]):
        '''List a directory in a standardized format by using MLSD
        command (RFC-3659). If path is omitted the current directory
        is assumed. "facts" is a list of strings representing the type
        of information desired (e.g. ["type", "size", "perm"]).

        Return a generator object yielding a tuple of two elements
        for every file found in path.
        First element is the file name, the second one is a dictionary
        including a variable number of "facts" depending on the server
        and whether "facts" argument has been provided.
        '''
        if facts:
            self.sendcmd("OPTS MLST " + ";".join(facts) + ";")
        if path:
            cmd = "MLSD %s" % path
        else:
            cmd = "MLSD"
        lines = []
        self.retrlines(cmd, lines.append)
        for line in lines:
            facts_found, _, name = line.rstrip(CRLF).partition(' ')
            entry = {}
            for fact in facts_found[:-1].split(";"):
                key, _, value = fact.partition("=")
                entry[key.lower()] = value
            yield (name, entry)

    def rename(self, fromname, toname):
        '''Rename a file.'''
        resp = self.sendcmd('RNFR ' + fromname)
        if resp[0] != '3':
            raise error_reply(resp)
        return self.voidcmd('RNTO ' + toname)

    def delete(self, filename):
        '''Delete a file.'''
        resp = self.sendcmd('DELE ' + filename)
        if resp[:3] in {'250', '200'}:
            return resp
        else:
            raise error_reply(resp)

    def cwd(self, dirname):
        '''Change to a directory.'''
        if dirname == '..':
            try:
                return self.voidcmd('CDUP')
            except error_perm as msg:
                if msg.args[0][:3] != '500':
                    raise
        elif dirname == '':
            dirname = '.'  # does nothing, but could return error
        cmd = 'CWD ' + dirname
        return self.voidcmd(cmd)

    def size(self, filename):
        '''Retrieve the size of a file.'''
        # The SIZE command is defined in RFC-3659
        resp = self.sendcmd('SIZE ' + filename)
        if resp[:3] == '213':
            s = resp[3:].strip()
            return int(s)

    def mkd(self, dirname):
        '''Make a directory, return its full pathname.'''
        resp = self.voidcmd('MKD ' + dirname)
        # fix around non-compliant implementations such as IIS shipped
        # with Windows server 2003
        if not resp.startswith('257'):
            return ''
        return parse257(resp)

    def rmd(self, dirname):
        '''Remove a directory.'''
        return self.voidcmd('RMD ' + dirname)

    def pwd(self):
        '''Return current working directory.'''
        resp = self.voidcmd('PWD')
        # fix around non-compliant implementations such as IIS shipped
        # with Windows server 2003
        if not resp.startswith('257'):
            return ''
        return parse257(resp)

    def quit(self):
        '''Quit, and close the connection.'''
        resp = self.voidcmd('QUIT')
        self.close()
        return resp

    def close(self):
        '''Close the connection without assuming anything about it.'''
        if self.file is not None:
            self.file.close()
        if self.sock is not None:
            self.sock.close()
        self.file = self.sock = None

sslImported = False
try:
    import ssl
    sslImported = True
except ImportError:
    try:
        import FTPSync.lib3.ssl as ssl
        sslImported = True
    except ImportError:
        print("SSL module import failed")

if sslImported:
    class FTP_TLS(FTP):
        '''A FTP subclass which adds TLS support to FTP as described
        in RFC-4217.

        Connect as usual to port 21 implicitly securing the FTP control
        connection before authenticating.

        Securing the data connection requires user to explicitly ask
        for it by calling prot_p() method.

        Usage example:
        >>> from ftplib import FTP_TLS
        >>> ftps = FTP_TLS('ftp.python.org')
        >>> ftps.login()  # login anonymously previously securing control channel
        '230 Guest login ok, access restrictions apply.'
        >>> ftps.prot_p()  # switch to secure data connection
        '200 Protection level set to P'
        >>> ftps.retrlines('LIST')  # list directory content securely
        total 9
        drwxr-xr-x   8 root     wheel        1024 Jan  3  1994 .
        drwxr-xr-x   8 root     wheel        1024 Jan  3  1994 ..
        drwxr-xr-x   2 root     wheel        1024 Jan  3  1994 bin
        drwxr-xr-x   2 root     wheel        1024 Jan  3  1994 etc
        d-wxrwxr-x   2 ftp      wheel        1024 Sep  5 13:43 incoming
        drwxr-xr-x   2 root     wheel        1024 Nov 17  1993 lib
        drwxr-xr-x   6 1094     wheel        1024 Sep 13 19:07 pub
        drwxr-xr-x   3 root     wheel        1024 Jan  3  1994 usr
        -rw-r--r--   1 root     root          312 Aug  1  1994 welcome.msg
        '226 Transfer complete.'
        >>> ftps.quit()
        '221 Goodbye.'
        >>>
        '''
        ssl_version = ssl.PROTOCOL_TLSv1

        def __init__(self, host='', user='', passwd='', acct='', keyfile=None,
                     certfile=None, context=None,
                     timeout=_GLOBAL_DEFAULT_TIMEOUT, source_address=None):
            if context is not None and keyfile is not None:
                raise ValueError("context and keyfile arguments are mutually "
                                 "exclusive")
            if context is not None and certfile is not None:
                raise ValueError("context and certfile arguments are mutually "
                                 "exclusive")
            self.keyfile = keyfile
            self.certfile = certfile
            self.context = context
            self._prot_p = False
            FTP.__init__(self, host, user, passwd, acct, timeout, source_address)

        def login(self, user='', passwd='', acct='', secure=True):
            if secure and not isinstance(self.sock, ssl.SSLSocket):
                self.auth()
            return FTP.login(self, user, passwd, acct)

        def auth(self):
            '''Set up secure control connection by using TLS/SSL.'''
            if isinstance(self.sock, ssl.SSLSocket):
                raise ValueError("Already using TLS")
            if self.ssl_version == ssl.PROTOCOL_TLSv1:
                resp = self.voidcmd('AUTH TLS')
            else:
                resp = self.voidcmd('AUTH SSL')
            if self.context is not None:
                self.sock = self.context.wrap_socket(self.sock)
            else:
                self.sock = ssl.wrap_socket(self.sock, self.keyfile,
                                            self.certfile,
                                            ssl_version=self.ssl_version)
            self.file = self.sock.makefile(mode='r', encoding=self.encoding)
            return resp

        def ccc(self):
            '''Switch back to a clear-text control connection.'''
            if not isinstance(self.sock, ssl.SSLSocket):
                raise ValueError("not using TLS")
            resp = self.voidcmd('CCC')
            self.sock = self.sock.unwrap()
            return resp

        def prot_p(self):
            '''Set up secure data connection.'''
            # PROT defines whether or not the data channel is to be protected.
            # Though RFC-2228 defines four possible protection levels,
            # RFC-4217 only recommends two, Clear and Private.
            # Clear (PROT C) means that no security is to be used on the
            # data-channel, Private (PROT P) means that the data-channel
            # should be protected by TLS.
            # PBSZ command MUST still be issued, but must have a parameter of
            # '0' to indicate that no buffering is taking place and the data
            # connection should not be encapsulated.
            self.voidcmd('PBSZ 0')
            resp = self.voidcmd('PROT P')
            self._prot_p = True
            return resp

        def prot_c(self):
            '''Set up clear text data connection.'''
            resp = self.voidcmd('PROT C')
            self._prot_p = False
            return resp

        # --- Overridden FTP methods

        def ntransfercmd(self, cmd, rest=None):
            conn, size = FTP.ntransfercmd(self, cmd, rest)
            if self._prot_p:
                if self.context is not None:
                    conn = self.context.wrap_socket(conn)
                else:
                    conn = ssl.wrap_socket(conn, self.keyfile, self.certfile,
                                           ssl_version=self.ssl_version)
            return conn, size

        def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
            self.voidcmd('TYPE I')
            with self.transfercmd(cmd, rest) as conn:
                while 1:
                    data = conn.recv(blocksize)
                    if not data:
                        break
                    callback(data)
                # shutdown ssl layer
                if isinstance(conn, ssl.SSLSocket):
                    conn.unwrap()
            return self.voidresp()

        def retrlines(self, cmd, callback = None):
            if callback is None: callback = print_line
            resp = self.sendcmd('TYPE A')
            conn = self.transfercmd(cmd)
            fp = conn.makefile('r', encoding=self.encoding)
            with fp, conn:
                while 1:
                    line = fp.readline()
                    if self.debugging > 2: print('*retr*', repr(line))
                    if not line:
                        break
                    if line[-2:] == CRLF:
                        line = line[:-2]
                    elif line[-1:] == '\n':
                        line = line[:-1]
                    callback(line)
                # shutdown ssl layer
                if isinstance(conn, ssl.SSLSocket):
                    conn.unwrap()
            return self.voidresp()

        def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
            self.voidcmd('TYPE I')
            with self.transfercmd(cmd, rest) as conn:
                while 1:
                    buf = fp.read(blocksize)
                    if not buf: break
                    conn.sendall(buf)
                    if callback: callback(buf)
                # shutdown ssl layer
                if isinstance(conn, ssl.SSLSocket):
                    conn.unwrap()
            return self.voidresp()

        def storlines(self, cmd, fp, callback=None):
            self.voidcmd('TYPE A')
            with self.transfercmd(cmd) as conn:
                while 1:
                    buf = fp.readline()
                    if not buf: break
                    if buf[-2:] != B_CRLF:
                        if buf[-1] in B_CRLF: buf = buf[:-1]
                        buf = buf + B_CRLF
                    conn.sendall(buf)
                    if callback: callback(buf)
                # shutdown ssl layer
                if isinstance(conn, ssl.SSLSocket):
                    conn.unwrap()
            return self.voidresp()

        def abort(self):
            # overridden as we can't pass MSG_OOB flag to sendall()
            line = b'ABOR' + B_CRLF
            self.sock.sendall(line)
            resp = self.getmultiline()
            if resp[:3] not in {'426', '225', '226'}:
                raise error_proto(resp)
            return resp

    __all__.append('FTP_TLS')
    all_errors = (Error, IOError, EOFError, ssl.SSLError)


_150_re = None

def parse150(resp):
    '''Parse the '150' response for a RETR request.
    Returns the expected transfer size or None; size is not guaranteed to
    be present in the 150 message.
    '''
    if resp[:3] != '150':
        raise error_reply(resp)
    global _150_re
    if _150_re is None:
        import re
        _150_re = re.compile(
            "150 .* \((\d+) bytes\)", re.IGNORECASE | re.ASCII)
    m = _150_re.match(resp)
    if not m:
        return None
    return int(m.group(1))


_227_re = None

def parse227(resp):
    '''Parse the '227' response for a PASV request.
    Raises error_proto if it does not contain '(h1,h2,h3,h4,p1,p2)'
    Return ('host.addr.as.numbers', port#) tuple.'''

    if resp[:3] != '227':
        raise error_reply(resp)
    global _227_re
    if _227_re is None:
        import re
        _227_re = re.compile(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', re.ASCII)
    m = _227_re.search(resp)
    if not m:
        raise error_proto(resp)
    numbers = m.groups()
    host = '.'.join(numbers[:4])
    port = (int(numbers[4]) << 8) + int(numbers[5])
    return host, port


def parse229(resp, peer):
    '''Parse the '229' response for a EPSV request.
    Raises error_proto if it does not contain '(|||port|)'
    Return ('host.addr.as.numbers', port#) tuple.'''

    if resp[:3] != '229':
        raise error_reply(resp)
    left = resp.find('(')
    if left < 0: raise error_proto(resp)
    right = resp.find(')', left + 1)
    if right < 0:
        raise error_proto(resp) # should contain '(|||port|)'
    if resp[left + 1] != resp[right - 1]:
        raise error_proto(resp)
    parts = resp[left + 1:right].split(resp[left+1])
    if len(parts) != 5:
        raise error_proto(resp)
    host = peer[0]
    port = int(parts[3])
    return host, port


def parse257(resp):
    '''Parse the '257' response for a MKD or PWD request.
    This is a response to a MKD or PWD request: a directory name.
    Returns the directoryname in the 257 reply.'''

    if resp[:3] != '257':
        raise error_reply(resp)
    if resp[3:5] != ' "':
        return '' # Not compliant to RFC 959, but UNIX ftpd does this
    dirname = ''
    i = 5
    n = len(resp)
    while i < n:
        c = resp[i]
        i = i+1
        if c == '"':
            if i >= n or resp[i] != '"':
                break
            i = i+1
        dirname = dirname + c
    return dirname


def print_line(line):
    '''Default retrlines callback to print a line.'''
    print(line)


def ftpcp(source, sourcename, target, targetname = '', type = 'I'):
    '''Copy file from one FTP-instance to another.'''
    if not targetname: targetname = sourcename
    type = 'TYPE ' + type
    source.voidcmd(type)
    target.voidcmd(type)
    sourcehost, sourceport = parse227(source.sendcmd('PASV'))
    target.sendport(sourcehost, sourceport)
    # RFC 959: the user must "listen" [...] BEFORE sending the
    # transfer request.
    # So: STOR before RETR, because here the target is a "user".
    treply = target.sendcmd('STOR ' + targetname)
    if treply[:3] not in {'125', '150'}: raise error_proto  # RFC 959
    sreply = source.sendcmd('RETR ' + sourcename)
    if sreply[:3] not in {'125', '150'}: raise error_proto  # RFC 959
    source.voidresp()
    target.voidresp()


class Netrc:
    """Class to parse & provide access to 'netrc' format files.

    See the netrc(4) man page for information on the file format.

    WARNING: This class is obsolete -- use module netrc instead.

    """
    __defuser = None
    __defpasswd = None
    __defacct = None

    def __init__(self, filename=None):
        if filename is None:
            if "HOME" in os.environ:
                filename = os.path.join(os.environ["HOME"],
                                        ".netrc")
            else:
                raise IOError("specify file to load or set $HOME")
        self.__hosts = {}
        self.__macros = {}
        fp = open(filename, "r")
        in_macro = 0
        while 1:
            line = fp.readline()
            if not line: break
            if in_macro and line.strip():
                macro_lines.append(line)
                continue
            elif in_macro:
                self.__macros[macro_name] = tuple(macro_lines)
                in_macro = 0
            words = line.split()
            host = user = passwd = acct = None
            default = 0
            i = 0
            while i < len(words):
                w1 = words[i]
                if i+1 < len(words):
                    w2 = words[i + 1]
                else:
                    w2 = None
                if w1 == 'default':
                    default = 1
                elif w1 == 'machine' and w2:
                    host = w2.lower()
                    i = i + 1
                elif w1 == 'login' and w2:
                    user = w2
                    i = i + 1
                elif w1 == 'password' and w2:
                    passwd = w2
                    i = i + 1
                elif w1 == 'account' and w2:
                    acct = w2
                    i = i + 1
                elif w1 == 'macdef' and w2:
                    macro_name = w2
                    macro_lines = []
                    in_macro = 1
                    break
                i = i + 1
            if default:
                self.__defuser = user or self.__defuser
                self.__defpasswd = passwd or self.__defpasswd
                self.__defacct = acct or self.__defacct
            if host:
                if host in self.__hosts:
                    ouser, opasswd, oacct = \
                           self.__hosts[host]
                    user = user or ouser
                    passwd = passwd or opasswd
                    acct = acct or oacct
                self.__hosts[host] = user, passwd, acct
        fp.close()

    def get_hosts(self):
        """Return a list of hosts mentioned in the .netrc file."""
        return self.__hosts.keys()

    def get_account(self, host):
        """Returns login information for the named host.

        The return value is a triple containing userid,
        password, and the accounting field.

        """
        host = host.lower()
        user = passwd = acct = None
        if host in self.__hosts:
            user, passwd, acct = self.__hosts[host]
        user = user or self.__defuser
        passwd = passwd or self.__defpasswd
        acct = acct or self.__defacct
        return user, passwd, acct

    def get_macros(self):
        """Return a list of all defined macro names."""
        return self.__macros.keys()

    def get_macro(self, macro):
        """Return a sequence of lines which define a named macro."""
        return self.__macros[macro]



def test():
    '''Test program.
    Usage: ftp [-d] [-r[file]] host [-l[dir]] [-d[dir]] [-p] [file] ...

    -d dir
    -l list
    -p password
    '''

    if len(sys.argv) < 2:
        print(test.__doc__)
        sys.exit(0)

    debugging = 0
    rcfile = None
    while sys.argv[1] == '-d':
        debugging = debugging+1
        del sys.argv[1]
    if sys.argv[1][:2] == '-r':
        # get name of alternate ~/.netrc file:
        rcfile = sys.argv[1][2:]
        del sys.argv[1]
    host = sys.argv[1]
    ftp = FTP(host)
    ftp.set_debuglevel(debugging)
    userid = passwd = acct = ''
    try:
        netrc = Netrc(rcfile)
    except IOError:
        if rcfile is not None:
            sys.stderr.write("Could not open account file"
                             " -- using anonymous login.")
    else:
        try:
            userid, passwd, acct = netrc.get_account(host)
        except KeyError:
            # no account for host
            sys.stderr.write(
                    "No account -- using anonymous login.")
    ftp.login(userid, passwd, acct)
    for file in sys.argv[2:]:
        if file[:2] == '-l':
            ftp.dir(file[2:])
        elif file[:2] == '-d':
            cmd = 'CWD'
            if file[2:]: cmd = cmd + ' ' + file[2:]
            resp = ftp.sendcmd(cmd)
        elif file == '-p':
            ftp.set_pasv(not ftp.passiveserver)
        else:
            ftp.retrbinary('RETR ' + file, \
                           sys.stdout.write, 1024)
    ftp.quit()


if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = ssl
# Wrapper module for _ssl, providing some additional facilities
# implemented in Python.  Written by Bill Janssen.

"""This module provides some more Pythonic support for SSL.

Object types:

  SSLSocket -- subtype of socket.socket which does SSL over the socket

Exceptions:

  SSLError -- exception raised for I/O errors

Functions:

  cert_time_to_seconds -- convert time string used for certificate
                          notBefore and notAfter functions to integer
                          seconds past the Epoch (the time values
                          returned from time.time())

  fetch_server_certificate (HOST, PORT) -- fetch the certificate provided
                          by the server running on HOST at port PORT.  No
                          validation of the certificate is performed.

Integer constants:

SSL_ERROR_ZERO_RETURN
SSL_ERROR_WANT_READ
SSL_ERROR_WANT_WRITE
SSL_ERROR_WANT_X509_LOOKUP
SSL_ERROR_SYSCALL
SSL_ERROR_SSL
SSL_ERROR_WANT_CONNECT

SSL_ERROR_EOF
SSL_ERROR_INVALID_ERROR_CODE

The following group define certificate requirements that one side is
allowing/requiring from the other side:

CERT_NONE - no certificates from the other side are required (or will
            be looked at if provided)
CERT_OPTIONAL - certificates are not required, but if provided will be
                validated, and if validation fails, the connection will
                also fail
CERT_REQUIRED - certificates are required, and will be validated, and
                if validation fails, the connection will also fail

The following constants identify various SSL protocol variants:

PROTOCOL_SSLv2
PROTOCOL_SSLv3
PROTOCOL_SSLv23
PROTOCOL_TLSv1
"""

import textwrap
import re

import _ssl             # if we can't import it, let the error propagate

from _ssl import OPENSSL_VERSION_NUMBER, OPENSSL_VERSION_INFO, OPENSSL_VERSION
from _ssl import _SSLContext, SSLError
from _ssl import CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED
from _ssl import (PROTOCOL_SSLv2, PROTOCOL_SSLv3, PROTOCOL_SSLv23,
                  PROTOCOL_TLSv1)
from _ssl import OP_ALL, OP_NO_SSLv2, OP_NO_SSLv3, OP_NO_TLSv1
from _ssl import RAND_status, RAND_egd, RAND_add
from _ssl import (
    SSL_ERROR_ZERO_RETURN,
    SSL_ERROR_WANT_READ,
    SSL_ERROR_WANT_WRITE,
    SSL_ERROR_WANT_X509_LOOKUP,
    SSL_ERROR_SYSCALL,
    SSL_ERROR_SSL,
    SSL_ERROR_WANT_CONNECT,
    SSL_ERROR_EOF,
    SSL_ERROR_INVALID_ERROR_CODE,
    )
from _ssl import HAS_SNI

from socket import getnameinfo as _getnameinfo
from socket import error as socket_error
from socket import socket, AF_INET, SOCK_STREAM
import base64        # for DER-to-PEM translation
import traceback
import errno


class CertificateError(ValueError):
    pass


def _dnsname_to_pat(dn):
    pats = []
    for frag in dn.split(r'.'):
        if frag == '*':
            # When '*' is a fragment by itself, it matches a non-empty dotless
            # fragment.
            pats.append('[^.]+')
        else:
            # Otherwise, '*' matches any dotless fragment.
            frag = re.escape(frag)
            pats.append(frag.replace(r'\*', '[^.]*'))
    return re.compile(r'\A' + r'\.'.join(pats) + r'\Z', re.IGNORECASE)


def match_hostname(cert, hostname):
    """Verify that *cert* (in decoded format as returned by
    SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 rules
    are mostly followed, but IP addresses are not accepted for *hostname*.

    CertificateError is raised on failure. On success, the function
    returns nothing.
    """
    if not cert:
        raise ValueError("empty or no certificate")
    dnsnames = []
    san = cert.get('subjectAltName', ())
    for key, value in san:
        if key == 'DNS':
            if _dnsname_to_pat(value).match(hostname):
                return
            dnsnames.append(value)
    if not san:
        # The subject is only checked when subjectAltName is empty
        for sub in cert.get('subject', ()):
            for key, value in sub:
                # XXX according to RFC 2818, the most specific Common Name
                # must be used.
                if key == 'commonName':
                    if _dnsname_to_pat(value).match(hostname):
                        return
                    dnsnames.append(value)
    if len(dnsnames) > 1:
        raise CertificateError("hostname %r "
            "doesn't match either of %s"
            % (hostname, ', '.join(map(repr, dnsnames))))
    elif len(dnsnames) == 1:
        raise CertificateError("hostname %r "
            "doesn't match %r"
            % (hostname, dnsnames[0]))
    else:
        raise CertificateError("no appropriate commonName or "
            "subjectAltName fields were found")


class SSLContext(_SSLContext):
    """An SSLContext holds various SSL-related configuration options and
    data, such as certificates and possibly a private key."""

    __slots__ = ('protocol',)

    def __new__(cls, protocol, *args, **kwargs):
        return _SSLContext.__new__(cls, protocol)

    def __init__(self, protocol):
        self.protocol = protocol

    def wrap_socket(self, sock, server_side=False,
                    do_handshake_on_connect=True,
                    suppress_ragged_eofs=True,
                    server_hostname=None):
        return SSLSocket(sock=sock, server_side=server_side,
                         do_handshake_on_connect=do_handshake_on_connect,
                         suppress_ragged_eofs=suppress_ragged_eofs,
                         server_hostname=server_hostname,
                         _context=self)


class SSLSocket(socket):
    """This class implements a subtype of socket.socket that wraps
    the underlying OS socket in an SSL context when necessary, and
    provides read and write methods over that channel."""

    def __init__(self, sock=None, keyfile=None, certfile=None,
                 server_side=False, cert_reqs=CERT_NONE,
                 ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                 do_handshake_on_connect=True,
                 family=AF_INET, type=SOCK_STREAM, proto=0, fileno=None,
                 suppress_ragged_eofs=True, ciphers=None,
                 server_hostname=None,
                 _context=None):

        if _context:
            self.context = _context
        else:
            if server_side and not certfile:
                raise ValueError("certfile must be specified for server-side "
                                 "operations")
            if keyfile and not certfile:
                raise ValueError("certfile must be specified")
            if certfile and not keyfile:
                keyfile = certfile
            self.context = SSLContext(ssl_version)
            self.context.verify_mode = cert_reqs
            if ca_certs:
                self.context.load_verify_locations(ca_certs)
            if certfile:
                self.context.load_cert_chain(certfile, keyfile)
            if ciphers:
                self.context.set_ciphers(ciphers)
            self.keyfile = keyfile
            self.certfile = certfile
            self.cert_reqs = cert_reqs
            self.ssl_version = ssl_version
            self.ca_certs = ca_certs
            self.ciphers = ciphers
        if server_side and server_hostname:
            raise ValueError("server_hostname can only be specified "
                             "in client mode")
        self.server_side = server_side
        self.server_hostname = server_hostname
        self.do_handshake_on_connect = do_handshake_on_connect
        self.suppress_ragged_eofs = suppress_ragged_eofs
        connected = False
        if sock is not None:
            socket.__init__(self,
                            family=sock.family,
                            type=sock.type,
                            proto=sock.proto,
                            fileno=sock.fileno())
            self.settimeout(sock.gettimeout())
            # see if it's connected
            try:
                sock.getpeername()
            except socket_error as e:
                if e.errno != errno.ENOTCONN:
                    raise
            else:
                connected = True
            sock.detach()
        elif fileno is not None:
            socket.__init__(self, fileno=fileno)
        else:
            socket.__init__(self, family=family, type=type, proto=proto)

        self._closed = False
        self._sslobj = None
        self._connected = connected
        if connected:
            # create the SSL object
            try:
                self._sslobj = self.context._wrap_socket(self, server_side,
                                                         server_hostname)
                if do_handshake_on_connect:
                    timeout = self.gettimeout()
                    if timeout == 0.0:
                        # non-blocking
                        raise ValueError("do_handshake_on_connect should not be specified for non-blocking sockets")
                    self.do_handshake()

            except socket_error as x:
                self.close()
                raise x

    def dup(self):
        raise NotImplemented("Can't dup() %s instances" %
                             self.__class__.__name__)

    def _checkClosed(self, msg=None):
        # raise an exception here if you wish to check for spurious closes
        pass

    def read(self, len=0, buffer=None):
        """Read up to LEN bytes and return them.
        Return zero-length string on EOF."""

        self._checkClosed()
        try:
            if buffer is not None:
                v = self._sslobj.read(len, buffer)
            else:
                v = self._sslobj.read(len or 1024)
            return v
        except SSLError as x:
            if x.args[0] == SSL_ERROR_EOF and self.suppress_ragged_eofs:
                if buffer is not None:
                    return 0
                else:
                    return b''
            else:
                raise

    def write(self, data):
        """Write DATA to the underlying SSL channel.  Returns
        number of bytes of DATA actually transmitted."""

        self._checkClosed()
        return self._sslobj.write(data)

    def getpeercert(self, binary_form=False):
        """Returns a formatted version of the data in the
        certificate provided by the other end of the SSL channel.
        Return None if no certificate was provided, {} if a
        certificate was provided, but not validated."""

        self._checkClosed()
        return self._sslobj.peer_certificate(binary_form)

    def cipher(self):
        self._checkClosed()
        if not self._sslobj:
            return None
        else:
            return self._sslobj.cipher()

    def send(self, data, flags=0):
        self._checkClosed()
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to send() on %s" %
                    self.__class__)
            while True:
                try:
                    v = self._sslobj.write(data)
                except SSLError as x:
                    if x.args[0] == SSL_ERROR_WANT_READ:
                        return 0
                    elif x.args[0] == SSL_ERROR_WANT_WRITE:
                        return 0
                    else:
                        raise
                else:
                    return v
        else:
            return socket.send(self, data, flags)

    def sendto(self, data, flags_or_addr, addr=None):
        self._checkClosed()
        if self._sslobj:
            raise ValueError("sendto not allowed on instances of %s" %
                             self.__class__)
        elif addr is None:
            return socket.sendto(self, data, flags_or_addr)
        else:
            return socket.sendto(self, data, flags_or_addr, addr)

    def sendall(self, data, flags=0):
        self._checkClosed()
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to sendall() on %s" %
                    self.__class__)
            amount = len(data)
            count = 0
            while (count < amount):
                v = self.send(data[count:])
                count += v
            return amount
        else:
            return socket.sendall(self, data, flags)

    def recv(self, buflen=1024, flags=0):
        self._checkClosed()
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to recv() on %s" %
                    self.__class__)
            return self.read(buflen)
        else:
            return socket.recv(self, buflen, flags)

    def recv_into(self, buffer, nbytes=None, flags=0):
        self._checkClosed()
        if buffer and (nbytes is None):
            nbytes = len(buffer)
        elif nbytes is None:
            nbytes = 1024
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                  "non-zero flags not allowed in calls to recv_into() on %s" %
                  self.__class__)
            return self.read(nbytes, buffer)
        else:
            return socket.recv_into(self, buffer, nbytes, flags)

    def recvfrom(self, buflen=1024, flags=0):
        self._checkClosed()
        if self._sslobj:
            raise ValueError("recvfrom not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.recvfrom(self, buflen, flags)

    def recvfrom_into(self, buffer, nbytes=None, flags=0):
        self._checkClosed()
        if self._sslobj:
            raise ValueError("recvfrom_into not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.recvfrom_into(self, buffer, nbytes, flags)

    def pending(self):
        self._checkClosed()
        if self._sslobj:
            return self._sslobj.pending()
        else:
            return 0

    def shutdown(self, how):
        self._checkClosed()
        self._sslobj = None
        socket.shutdown(self, how)

    def unwrap(self):
        if self._sslobj:
            s = self._sslobj.shutdown()
            self._sslobj = None
            return s
        else:
            raise ValueError("No SSL wrapper around " + str(self))

    def _real_close(self):
        self._sslobj = None
        # self._closed = True
        socket._real_close(self)

    def do_handshake(self, block=False):
        """Perform a TLS/SSL handshake."""

        timeout = self.gettimeout()
        try:
            if timeout == 0.0 and block:
                self.settimeout(None)
            self._sslobj.do_handshake()
        finally:
            self.settimeout(timeout)

    def _real_connect(self, addr, return_errno):
        if self.server_side:
            raise ValueError("can't connect in server-side mode")
        # Here we assume that the socket is client-side, and not
        # connected at the time of the call.  We connect it, then wrap it.
        if self._connected:
            raise ValueError("attempt to connect already-connected SSLSocket!")
        self._sslobj = self.context._wrap_socket(self, False, self.server_hostname)
        try:
            socket.connect(self, addr)
            if self.do_handshake_on_connect:
                self.do_handshake()
        except socket_error as e:
            if return_errno:
                return e.errno
            else:
                self._sslobj = None
                raise e
        self._connected = True
        return 0

    def connect(self, addr):
        """Connects to remote ADDR, and then wraps the connection in
        an SSL channel."""
        self._real_connect(addr, False)

    def connect_ex(self, addr):
        """Connects to remote ADDR, and then wraps the connection in
        an SSL channel."""
        return self._real_connect(addr, True)

    def accept(self):
        """Accepts a new connection from a remote client, and returns
        a tuple containing that new connection wrapped with a server-side
        SSL channel, and the address of the remote client."""

        newsock, addr = socket.accept(self)
        return (SSLSocket(sock=newsock,
                          keyfile=self.keyfile, certfile=self.certfile,
                          server_side=True,
                          cert_reqs=self.cert_reqs,
                          ssl_version=self.ssl_version,
                          ca_certs=self.ca_certs,
                          ciphers=self.ciphers,
                          do_handshake_on_connect=
                              self.do_handshake_on_connect),
                addr)

    def __del__(self):
        # sys.stderr.write("__del__ on %s\n" % repr(self))
        self._real_close()


def wrap_socket(sock, keyfile=None, certfile=None,
                server_side=False, cert_reqs=CERT_NONE,
                ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                do_handshake_on_connect=True,
                suppress_ragged_eofs=True, ciphers=None):

    return SSLSocket(sock=sock, keyfile=keyfile, certfile=certfile,
                     server_side=server_side, cert_reqs=cert_reqs,
                     ssl_version=ssl_version, ca_certs=ca_certs,
                     do_handshake_on_connect=do_handshake_on_connect,
                     suppress_ragged_eofs=suppress_ragged_eofs,
                     ciphers=ciphers)

# some utility functions

def cert_time_to_seconds(cert_time):
    """Takes a date-time string in standard ASN1_print form
    ("MON DAY 24HOUR:MINUTE:SEC YEAR TIMEZONE") and return
    a Python time value in seconds past the epoch."""

    import time
    return time.mktime(time.strptime(cert_time, "%b %d %H:%M:%S %Y GMT"))

PEM_HEADER = "-----BEGIN CERTIFICATE-----"
PEM_FOOTER = "-----END CERTIFICATE-----"

def DER_cert_to_PEM_cert(der_cert_bytes):
    """Takes a certificate in binary DER format and returns the
    PEM version of it as a string."""

    f = str(base64.standard_b64encode(der_cert_bytes), 'ASCII', 'strict')
    return (PEM_HEADER + '\n' +
            textwrap.fill(f, 64) + '\n' +
            PEM_FOOTER + '\n')

def PEM_cert_to_DER_cert(pem_cert_string):
    """Takes a certificate in ASCII PEM format and returns the
    DER-encoded version of it as a byte sequence"""

    if not pem_cert_string.startswith(PEM_HEADER):
        raise ValueError("Invalid PEM encoding; must start with %s"
                         % PEM_HEADER)
    if not pem_cert_string.strip().endswith(PEM_FOOTER):
        raise ValueError("Invalid PEM encoding; must end with %s"
                         % PEM_FOOTER)
    d = pem_cert_string.strip()[len(PEM_HEADER):-len(PEM_FOOTER)]
    return base64.decodebytes(d.encode('ASCII', 'strict'))

def get_server_certificate(addr, ssl_version=PROTOCOL_SSLv3, ca_certs=None):
    """Retrieve the certificate from the server at the specified address,
    and return it as a PEM-encoded string.
    If 'ca_certs' is specified, validate the server cert against it.
    If 'ssl_version' is specified, use it in the connection attempt."""

    host, port = addr
    if (ca_certs is not None):
        cert_reqs = CERT_REQUIRED
    else:
        cert_reqs = CERT_NONE
    s = wrap_socket(socket(), ssl_version=ssl_version,
                    cert_reqs=cert_reqs, ca_certs=ca_certs)
    s.connect(addr)
    dercert = s.getpeercert(True)
    s.close()
    return DER_cert_to_PEM_cert(dercert)

def get_protocol_name(protocol_code):
    if protocol_code == PROTOCOL_TLSv1:
        return "TLSv1"
    elif protocol_code == PROTOCOL_SSLv23:
        return "SSLv23"
    elif protocol_code == PROTOCOL_SSLv2:
        return "SSLv2"
    elif protocol_code == PROTOCOL_SSLv3:
        return "SSLv3"
    else:
        return "<unknown>"

########NEW FILE########
