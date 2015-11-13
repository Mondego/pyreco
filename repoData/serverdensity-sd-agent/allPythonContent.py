__FILENAME__ = agent
#!/usr/bin/env python
'''
    Server Density
    www.serverdensity.com
    ----
    Server monitoring agent for Linux, FreeBSD and Mac OS X

    Licensed under Simplified BSD License (see LICENSE)
'''

import logging

# General config
agentConfig = {}
agentConfig['logging'] = logging.INFO
agentConfig['checkFreq'] = 60

agentConfig['version'] = '1.13.2'

rawConfig = {}

# Check we're not using an old version of Python. Do this before anything else
# We need 2.4 above because some modules (like subprocess) were only introduced in 2.4.
import sys
if int(sys.version_info[1]) <= 3:
    print 'You are using an outdated version of Python. Please update to v2.4 or above (v3 is not supported). For newer OSs, you can update Python without affecting your system install. See http://blog.boxedice.com/2010/01/19/updating-python-on-rhelcentos/ If you are running RHEl 4 / CentOS 4 then you will need to compile Python manually.'
    sys.exit(1)

# Core modules
import ConfigParser
import glob
import os
import re
import sched
import time

# After the version check as this isn't available on older Python versions
# and will error before the message is shown
import subprocess

# Custom modules
from checks import checks
from daemon import Daemon

# Config handling
try:
    path = os.path.realpath(__file__)
    path = os.path.dirname(path)

    config = ConfigParser.ConfigParser()

    if os.path.exists('/etc/sd-agent/conf.d/'):
        configPath = '/etc/sd-agent/conf.d/'
    elif os.path.exists('/etc/sd-agent/config.cfg'):
        configPath = '/etc/sd-agent/config.cfg'
    else:
        configPath = path + '/config.cfg'

    if os.access(configPath, os.R_OK) == False:
        print 'Unable to read the config file at ' + configPath
        print 'Agent will now quit'
        sys.exit(1)

    if os.path.isdir(configPath):
       for configFile in glob.glob(os.path.join(configPath, "*.cfg")):
           config.read(configFile)
    else:
       config.read(configPath)

    # Core config
    agentConfig['sdUrl'] = config.get('Main', 'sd_url')

    if agentConfig['sdUrl'].endswith('/'):
        agentConfig['sdUrl'] = agentConfig['sdUrl'][:-1]

    agentConfig['agentKey'] = config.get('Main', 'agent_key')

    # Tmp path
    if os.path.exists('/var/log/sd-agent/'):
        agentConfig['tmpDirectory'] = '/var/log/sd-agent/'
    else:
        agentConfig['tmpDirectory'] = '/tmp/' # default which may be overriden in the config later

    agentConfig['pidfileDirectory'] = agentConfig['tmpDirectory']

    # Plugin config
    if config.has_option('Main', 'plugin_directory'):
        agentConfig['pluginDirectory'] = config.get('Main', 'plugin_directory')

    # Optional config
    # Also do not need to be present in the config file (case 28326).
    if config.has_option('Main', 'apache_status_url'):
        agentConfig['apacheStatusUrl'] = config.get('Main', 'apache_status_url')

    if config.has_option('Main', 'apache_status_user'):
        agentConfig['apacheStatusUser'] = config.get('Main', 'apache_status_user')

    if config.has_option('Main', 'apache_status_pass'):
        agentConfig['apacheStatusPass'] = config.get('Main', 'apache_status_pass')

    if config.has_option('Main', 'logging_level'):
        # Maps log levels from the configuration file to Python log levels
        loggingLevelMapping = {
            'debug'    : logging.DEBUG,
            'info'     : logging.INFO,
            'error'    : logging.ERROR,
            'warn'     : logging.WARN,
            'warning'  : logging.WARNING,
            'critical' : logging.CRITICAL,
            'fatal'    : logging.FATAL,
        }

        customLogging = config.get('Main', 'logging_level')

        try:
            agentConfig['logging'] = loggingLevelMapping[customLogging.lower()]

        except KeyError, ex:
            agentConfig['logging'] = logging.INFO

    if config.has_option('Main', 'mongodb_server'):
        agentConfig['MongoDBServer'] = config.get('Main', 'mongodb_server')

    if config.has_option('Main', 'mongodb_dbstats'):
        agentConfig['MongoDBDBStats'] = config.get('Main', 'mongodb_dbstats')

    if config.has_option('Main', 'mongodb_replset'):
        agentConfig['MongoDBReplSet'] = config.get('Main', 'mongodb_replset')

    if config.has_option('Main', 'mysql_server'):
        agentConfig['MySQLServer'] = config.get('Main', 'mysql_server')

    if config.has_option('Main', 'mysql_user'):
        agentConfig['MySQLUser'] = config.get('Main', 'mysql_user')

    if config.has_option('Main', 'mysql_pass'):
        agentConfig['MySQLPass'] = config.get('Main', 'mysql_pass')

    if config.has_option('Main', 'mysql_port'):
        agentConfig['MySQLPort'] = config.get('Main', 'mysql_port')

    if config.has_option('Main', 'mysql_socket'):
        agentConfig['MySQLSocket'] = config.get('Main', 'mysql_socket')

    if config.has_option('Main', 'mysql_norepl'):
        agentConfig['MySQLNoRepl'] = config.get('Main', 'mysql_norepl')

    if config.has_option('Main', 'nginx_status_url'):
        agentConfig['nginxStatusUrl'] = config.get('Main', 'nginx_status_url')

    if config.has_option('Main', 'tmp_directory'):
        agentConfig['tmpDirectory'] = config.get('Main', 'tmp_directory')

    if config.has_option('Main', 'pidfile_directory'):
        agentConfig['pidfileDirectory'] = config.get('Main', 'pidfile_directory')

    if config.has_option('Main', 'rabbitmq_status_url'):
        agentConfig['rabbitMQStatusUrl'] = config.get('Main', 'rabbitmq_status_url')

    if config.has_option('Main', 'rabbitmq_user'):
        agentConfig['rabbitMQUser'] = config.get('Main', 'rabbitmq_user')

    if config.has_option('Main', 'rabbitmq_pass'):
        agentConfig['rabbitMQPass'] = config.get('Main', 'rabbitmq_pass')

except ConfigParser.NoSectionError, e:
    print 'Config file not found or incorrectly formatted'
    print 'Agent will now quit'
    sys.exit(1)

except ConfigParser.ParsingError, e:
    print 'Config file not found or incorrectly formatted'
    print 'Agent will now quit'
    sys.exit(1)

except ConfigParser.NoOptionError, e:
    print 'There are some items missing from your config file, but nothing fatal'

# Check to make sure the default config values have been changed (only core config values)
if agentConfig['sdUrl'] == 'http://example.serverdensity.com' or agentConfig['agentKey'] == 'keyHere':
    print 'You have not modified config.cfg for your server'
    print 'Agent will now quit'
    sys.exit(1)

# Check to make sure sd_url is in correct
if (re.match('http(s)?(\:\/\/)[a-zA-Z0-9_\-]+\.(serverdensity.com)', agentConfig['sdUrl']) == None) \
   and (re.match('http(s)?(\:\/\/)[a-zA-Z0-9_\-]+\.(serverdensity.io)', agentConfig['sdUrl']) == None):
    print 'Your sd_url is incorrect. It needs to be in the form https://example.serverdensity.com or https://example.serverdensity.io'
    print 'Agent will now quit'
    sys.exit(1)

# Check apache_status_url is not empty (case 27073)
if 'apacheStatusUrl' in agentConfig and agentConfig['apacheStatusUrl'] == None:
    print 'You must provide a config value for apache_status_url. If you do not wish to use Apache monitoring, leave it as its default value - http://www.example.com/server-status/?auto'
    print 'Agent will now quit'
    sys.exit(1)

if 'nginxStatusUrl' in agentConfig and agentConfig['nginxStatusUrl'] == None:
    print 'You must provide a config value for nginx_status_url. If you do not wish to use Nginx monitoring, leave it as its default value - http://www.example.com/nginx_status'
    print 'Agent will now quit'
    sys.exit(1)

if 'MySQLServer' in agentConfig and agentConfig['MySQLServer'] != '' and 'MySQLUser' in agentConfig and agentConfig['MySQLUser'] != '' and 'MySQLPass' in agentConfig:
    try:
        import MySQLdb
    except ImportError:
        print 'You have configured MySQL for monitoring, but the MySQLdb module is not installed. For more info, see: http://www.serverdensity.com/docs/agent/mysqlstatus/'
        print 'Agent will now quit'
        sys.exit(1)

if 'MongoDBServer' in agentConfig and agentConfig['MongoDBServer'] != '':
    try:
        import pymongo
    except ImportError:
        print 'You have configured MongoDB for monitoring, but the pymongo module is not installed. For more info, see: http://www.serverdensity.com/docs/agent/mongodbstatus/'
        print 'Agent will now quit'
        sys.exit(1)

for section in config.sections():
    rawConfig[section] = {}

    for option in config.options(section):
        rawConfig[section][option] = config.get(section, option)

# Override the generic daemon class to run our checks
class agent(Daemon):

    def run(self):
        mainLogger.debug('Collecting basic system stats')

        # Get some basic system stats to post back for development/testing
        import platform
        systemStats = {'machine': platform.machine(), 'platform': sys.platform, 'processor': platform.processor(), 'pythonV': platform.python_version(), 'cpuCores': self.cpuCores()}

        if sys.platform == 'linux2':
            systemStats['nixV'] = platform.dist()

        elif sys.platform == 'darwin':
            systemStats['macV'] = platform.mac_ver()

        elif sys.platform.find('freebsd') != -1:
            version = platform.uname()[2]
            systemStats['fbsdV'] = ('freebsd', version, '') # no codename for FreeBSD

        mainLogger.info('System: ' + str(systemStats))

        mainLogger.debug('Creating checks instance')

        # Checks instance
        c = checks(agentConfig, rawConfig, mainLogger)

        # Schedule the checks
        mainLogger.info('checkFreq: %s', agentConfig['checkFreq'])
        s = sched.scheduler(time.time, time.sleep)
        c.doChecks(s, True, systemStats) # start immediately (case 28315)
        s.run()

    def cpuCores(self):
        if sys.platform == 'linux2':
            grep = subprocess.Popen(['grep', 'model name', '/proc/cpuinfo'], stdout=subprocess.PIPE, close_fds=True)
            wc = subprocess.Popen(['wc', '-l'], stdin=grep.stdout, stdout=subprocess.PIPE, close_fds=True)
            output = wc.communicate()[0]
            return int(output)

        if sys.platform == 'darwin':
            output = subprocess.Popen(['sysctl', 'hw.ncpu'], stdout=subprocess.PIPE, close_fds=True).communicate()[0].split(': ')[1]
            return int(output)

# Control of daemon
if __name__ == '__main__':

    # Logging
    logFile = os.path.join(agentConfig['tmpDirectory'], 'sd-agent.log')

    if os.access(agentConfig['tmpDirectory'], os.W_OK) == False:
        print 'Unable to write the log file at ' + logFile
        print 'Agent will now quit'
        sys.exit(1)

    handler = logging.handlers.RotatingFileHandler(logFile, maxBytes=10485760, backupCount=5) # 10MB files
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handler.setFormatter(formatter)

    mainLogger = logging.getLogger('main')
    mainLogger.setLevel(agentConfig['logging'])
    mainLogger.addHandler(handler)

    mainLogger.info('--')
    mainLogger.info('sd-agent %s started', agentConfig['version'])
    mainLogger.info('--')

    mainLogger.info('Reading config from: %s', configPath)
    mainLogger.info('sd_url: %s', agentConfig['sdUrl'])
    mainLogger.info('agent_key: %s', agentConfig['agentKey'])

    argLen = len(sys.argv)

    if argLen == 3 or argLen == 4: # needs to accept case when --clean is passed
        if sys.argv[2] == 'init':
            # This path added for newer Linux packages which run under
            # a separate sd-agent user account.
            if os.path.exists('/var/run/sd-agent/'):
                pidFile = '/var/run/sd-agent/sd-agent.pid'
            else:
                pidFile = '/var/run/sd-agent.pid'

    else:
        pidFile = os.path.join(agentConfig['pidfileDirectory'], 'sd-agent.pid')

    if os.access(agentConfig['pidfileDirectory'], os.W_OK) == False:
        print 'Unable to write the PID file at ' + pidFile
        print 'Agent will now quit'
        sys.exit(1)

    mainLogger.info('PID: %s', pidFile)

    if argLen == 4 and sys.argv[3] == '--clean':
        mainLogger.info('--clean')
        try:
            os.remove(pidFile)
        except OSError:
            # Did not find pid file
            pass

    # Daemon instance from agent class
    daemon = agent(pidFile)

    # Control options
    if argLen == 2 or argLen == 3 or argLen == 4:
        if 'start' == sys.argv[1]:
            mainLogger.info('Action: start')
            daemon.start()

        elif 'stop' == sys.argv[1]:
            mainLogger.info('Action: stop')
            daemon.stop()

        elif 'restart' == sys.argv[1]:
            mainLogger.info('Action: restart')
            daemon.restart()

        elif 'foreground' == sys.argv[1]:
            mainLogger.info('Action: foreground')
            daemon.run()

        elif 'status' == sys.argv[1]:
            mainLogger.info('Action: status')

            try:
                pf = file(pidFile,'r')
                pid = int(pf.read().strip())
                pf.close()
            except IOError:
                pid = None
            except SystemExit:
                pid = None

            if pid:
                print 'sd-agent is running as pid %s.' % pid
            else:
                print 'sd-agent is not running.'

        elif 'update' == sys.argv[1]:
            mainLogger.info('Action: update')

            if os.path.abspath(__file__) == '/usr/bin/sd-agent/agent.py':
                print 'Please use the Linux package manager that was used to install the agent to update it.'
                print 'e.g. yum install sd-agent or apt-get install sd-agent'
                sys.exit(1)

            import httplib
            import platform
            import urllib2

            print 'Checking if there is a new version';

            # Get the latest version info
            try:
                mainLogger.debug('Update: checking for update')

                request = urllib2.urlopen('http://www.serverdensity.com/agentupdate/')
                response = request.read()

            except urllib2.HTTPError, e:
                print 'Unable to get latest version info - HTTPError = ' + str(e)
                sys.exit(1)

            except urllib2.URLError, e:
                print 'Unable to get latest version info - URLError = ' + str(e)
                sys.exit(1)

            except httplib.HTTPException, e:
                print 'Unable to get latest version info - HTTPException'
                sys.exit(1)

            except Exception, e:
                import traceback
                print 'Unable to get latest version info - Exception = ' + traceback.format_exc()
                sys.exit(1)

            mainLogger.debug('Update: importing json/minjson')

            # We need to return the data using JSON. As of Python 2.6+, there is a core JSON
            # module. We have a 2.4/2.5 compatible lib included with the agent but if we're
            # on 2.6 or above, we should use the core module which will be faster
            pythonVersion = platform.python_version_tuple()

            # Decode the JSON
            if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
                import json

                mainLogger.debug('Update: decoding JSON (json)')

                try:
                    updateInfo = json.loads(response)
                except Exception, e:
                    print 'Unable to get latest version info. Try again later.'
                    sys.exit(1)

            else:
                import minjson

                mainLogger.debug('Update: decoding JSON (minjson)')

                try:
                    updateInfo = minjson.safeRead(response)
                except Exception, e:
                    print 'Unable to get latest version info. Try again later.'
                    sys.exit(1)

            # Do the version check
            if updateInfo['version'] != agentConfig['version']:
                import md5 # I know this is depreciated, but we still support Python 2.4 and hashlib is only in 2.5. Case 26918
                import urllib

                print 'A new version is available.'

                def downloadFile(agentFile, recursed = False):
                    mainLogger.debug('Update: downloading ' + agentFile['name'])
                    print 'Downloading ' + agentFile['name']

                    downloadedFile = urllib.urlretrieve('http://www.serverdensity.com/downloads/sd-agent/' + agentFile['name'])

                    # Do md5 check to make sure the file downloaded properly
                    checksum = md5.new()
                    f = file(downloadedFile[0], 'rb')

                    # Although the files are small, we can't guarantee the available memory nor that there
                    # won't be large files in the future, so read the file in small parts (1kb at time)
                    while True:
                        part = f.read(1024)

                        if not part:
                            break # end of file

                        checksum.update(part)

                    f.close()

                    # Do we have a match?
                    if checksum.hexdigest() == agentFile['md5']:
                        return downloadedFile[0]

                    else:
                        # Try once more
                        if recursed == False:
                            downloadFile(agentFile, True)

                        else:
                            print agentFile['name'] + ' did not match its checksum - it is corrupted. This may be caused by network issues so please try again in a moment.'
                            sys.exit(1)

                # Loop through the new files and call the download function
                for agentFile in updateInfo['files']:
                    agentFile['tempFile'] = downloadFile(agentFile)

                # If we got to here then everything worked out fine. However, all the files are still in temporary locations so we need to move them
                # This is to stop an update breaking a working agent if the update fails halfway through
                import os
                import shutil # Prevents [Errno 18] Invalid cross-device link (case 26878) - http://mail.python.org/pipermail/python-list/2005-February/308026.html

                for agentFile in updateInfo['files']:
                    mainLogger.debug('Update: updating ' + agentFile['name'])
                    print 'Updating ' + agentFile['name']
                    installation_path = os.path.dirname(os.path.abspath(__file__))
                    mainLogger.debug('Update: installation path: ' + installation_path)

                    try:
                        if os.path.exists(agentFile['name']):
                            os.remove(os.path.join(installation_path, agentFile['name']))

                        shutil.move(agentFile['tempFile'], os.path.join(installation_path, agentFile['name']))

                    except OSError:
                        print 'An OS level error occurred. You will need to manually re-install the agent by downloading the latest version from http://www.serverdensity.com/downloads/sd-agent.tar.gz. You can copy your config.cfg to the new install'
                        sys.exit(1)

                mainLogger.debug('Update: done')

                print 'Update completed. Please restart the agent (python agent.py restart).'

            else:
                print 'The agent is already up to date'

        else:
            print 'Unknown command'
            sys.exit(1)

        sys.exit(0)

    else:
        print 'usage: %s start|stop|restart|status|update' % sys.argv[0]
        sys.exit(1)

########NEW FILE########
__FILENAME__ = checks
'''
	Server Density
	www.serverdensity.com
	----
	Server monitoring agent for Linux, FreeBSD and Mac OS X

	Licensed under Simplified BSD License (see LICENSE)
'''

# SO references
# http://stackoverflow.com/questions/446209/possible-values-from-sys-platform/446210#446210
# http://stackoverflow.com/questions/682446/splitting-out-the-output-of-ps-using-python/682464#682464
# http://stackoverflow.com/questions/1052589/how-can-i-parse-the-output-of-proc-net-dev-into-keyvalue-pairs-per-interface-us

# Core modules
import httplib # Used only for handling httplib.HTTPException (case #26701)
import logging
import logging.handlers
import os
import platform
import re
import string
import subprocess
import sys
import urllib
import urllib2
import socket

try:
    from hashlib import md5
except ImportError: # Python < 2.5
    from md5 import new as md5

# We need to return the data using JSON. As of Python 2.6+, there is a core JSON
# module. We have a 2.4/2.5 compatible lib included with the agent but if we're
# on 2.6 or above, we should use the core module which will be faster
pythonVersion = platform.python_version_tuple()
python24 = platform.python_version().startswith('2.4')

# Build the request headers
headers = {
	'User-Agent': 'Server Density Agent',
	'Content-Type': 'application/x-www-form-urlencoded',
	'Accept': 'text/html, */*',
}

if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
	import json
else:
	import minjson

class checks:

	def __init__(self, agentConfig, rawConfig, mainLogger):
		self.agentConfig = agentConfig
		self.rawConfig = rawConfig
		self.mainLogger = mainLogger

		self.mysqlConnectionsStore = None
		self.mysqlSlowQueriesStore = None
		self.mysqlVersion = None
		self.networkTrafficStore = {}
		self.nginxRequestsStore = None
		self.mongoDBStore = None
		self.apacheTotalAccesses = None
		self.plugins = None
		self.topIndex = 0
		self.os = None
		self.linuxProcFsLocation = None

		# Set global timeout to 15 seconds for all sockets (case 31033). Should be long enough
		import socket
		socket.setdefaulttimeout(15)

	#
	# Checks
	#

	def getApacheStatus(self):
		self.mainLogger.debug('getApacheStatus: start')

		if 'apacheStatusUrl' in self.agentConfig and self.agentConfig['apacheStatusUrl'] != 'http://www.example.com/server-status/?auto':	# Don't do it if the status URL hasn't been provided
			self.mainLogger.debug('getApacheStatus: config set')

			try:
				self.mainLogger.debug('getApacheStatus: attempting urlopen')

				if 'apacheStatusUser' in self.agentConfig and 'apacheStatusPass' in self.agentConfig and self.agentConfig['apacheStatusUrl'] != '' and self.agentConfig['apacheStatusPass'] != '':
					self.mainLogger.debug('getApacheStatus: u/p config set')

					passwordMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
					passwordMgr.add_password(None, self.agentConfig['apacheStatusUrl'], self.agentConfig['apacheStatusUser'], self.agentConfig['apacheStatusPass'])

					handler = urllib2.HTTPBasicAuthHandler(passwordMgr)

					# create "opener" (OpenerDirector instance)
					opener = urllib2.build_opener(handler)

					# use the opener to fetch a URL
					opener.open(self.agentConfig['apacheStatusUrl'])

					# Install the opener.
					# Now all calls to urllib2.urlopen use our opener.
					urllib2.install_opener(opener)

				req = urllib2.Request(self.agentConfig['apacheStatusUrl'], None, headers)
				request = urllib2.urlopen(req)
				response = request.read()

			except urllib2.HTTPError, e:
				self.mainLogger.error('Unable to get Apache status - HTTPError = %s', e)
				return False

			except urllib2.URLError, e:
				self.mainLogger.error('Unable to get Apache status - URLError = %s', e)
				return False

			except httplib.HTTPException, e:
				self.mainLogger.error('Unable to get Apache status - HTTPException = %s', e)
				return False

			except Exception, e:
				import traceback
				self.mainLogger.error('Unable to get Apache status - Exception = %s', traceback.format_exc())
				return False

			self.mainLogger.debug('getApacheStatus: urlopen success, start parsing')

			# Split out each line
			lines = response.split('\n')

			# Loop over each line and get the values
			apacheStatus = {}

			self.mainLogger.debug('getApacheStatus: parsing, loop')

			# Loop through and extract the numerical values
			for line in lines:
				values = line.split(': ')

				try:
					apacheStatus[str(values[0])] = values[1]

				except IndexError:
					break

			self.mainLogger.debug('getApacheStatus: parsed')

			apacheStatusReturn = {}

			try:

				if apacheStatus['Total Accesses'] != False:

					self.mainLogger.debug('getApacheStatus: processing total accesses')

					totalAccesses = float(apacheStatus['Total Accesses'])

					if self.apacheTotalAccesses is None or self.apacheTotalAccesses <= 0 or totalAccesses <= 0:

						apacheStatusReturn['reqPerSec'] = 0.0

						self.apacheTotalAccesses = totalAccesses

						self.mainLogger.debug('getApacheStatus: no cached total accesses (or totalAccesses == 0), so storing for first time / resetting stored value')

					else:

						self.mainLogger.debug('getApacheStatus: cached data exists, so calculating per sec metrics')

						apacheStatusReturn['reqPerSec'] = (totalAccesses - self.apacheTotalAccesses) / 60

						self.apacheTotalAccesses = totalAccesses

				else:

					self.mainLogger.error('getApacheStatus: Total Accesses not present in mod_status output. Is ExtendedStatus enabled?')

			except IndexError:
				self.mainLogger.error('getApacheStatus: IndexError - Total Accesses not present in mod_status output. Is ExtendedStatus enabled?')

			except KeyError:
				self.mainLogger.error('getApacheStatus: KeyError - Total Accesses not present in mod_status output. Is ExtendedStatus enabled?')

			try:

				if apacheStatus['BusyWorkers'] != False and apacheStatus['IdleWorkers'] != False:

					apacheStatusReturn['busyWorkers'] = apacheStatus['BusyWorkers']
					apacheStatusReturn['idleWorkers'] = apacheStatus['IdleWorkers']

				else:

					self.mainLogger.error('getApacheStatus: BusyWorkers/IdleWorkers not present in mod_status output. Is the URL correct (must have ?auto at the end)?')

			except IndexError:
				self.mainLogger.error('getApacheStatus: IndexError - BusyWorkers/IdleWorkers not present in mod_status output. Is the URL correct (must have ?auto at the end)?')

			except KeyError:
				self.mainLogger.error('getApacheStatus: KeyError - BusyWorkers/IdleWorkers not present in mod_status output. Is the URL correct (must have ?auto at the end)?')

			if 'reqPerSec' in apacheStatusReturn or 'BusyWorkers' in apacheStatusReturn or 'IdleWorkers' in apacheStatusReturn:

				return apacheStatusReturn

			else:

				return False

		else:
			self.mainLogger.debug('getApacheStatus: config not set')

			return False

	def getCouchDBStatus(self):
		self.mainLogger.debug('getCouchDBStatus: start')

		if ('CouchDBServer' not in self.agentConfig or self.agentConfig['CouchDBServer'] == ''):
			self.mainLogger.debug('getCouchDBStatus: config not set')
			return False

		self.mainLogger.debug('getCouchDBStatus: config set')

		# The dictionary to be returned.
		couchdb = {'stats': None, 'databases': {}}

		# First, get overall statistics.
		endpoint = '/_stats/'

		try:
			url = '%s%s' % (self.agentConfig['CouchDBServer'], endpoint)
			self.mainLogger.debug('getCouchDBStatus: attempting urlopen')
			req = urllib2.Request(url, None, headers)

			# Do the request, log any errors
			request = urllib2.urlopen(req)
			response = request.read()
		except urllib2.HTTPError, e:
			self.mainLogger.error('Unable to get CouchDB statistics - HTTPError = %s', e)
			return False

		except urllib2.URLError, e:
			self.mainLogger.error('Unable to get CouchDB statistics - URLError = %s', e)
			return False

		except httplib.HTTPException, e:
			self.mainLogger.error('Unable to get CouchDB statistics - HTTPException = %s', e)
			return False

		except Exception, e:
			import traceback
			self.mainLogger.error('Unable to get CouchDB statistics - Exception = %s', traceback.format_exc())
			return False

		try:

			if int(pythonVersion[1]) >= 6:
				self.mainLogger.debug('getCouchDBStatus: json read')
				stats = json.loads(response)

			else:
				self.mainLogger.debug('getCouchDBStatus: minjson read')
				stats = minjson.safeRead(response)

		except Exception, e:
			import traceback
			self.mainLogger.error('Unable to load CouchDB database JSON - Exception = %s', traceback.format_exc())
			return False

		couchdb['stats'] = stats

		# Next, get all database names.
		endpoint = '/_all_dbs/'

		try:
			url = '%s%s' % (self.agentConfig['CouchDBServer'], endpoint)
			self.mainLogger.debug('getCouchDBStatus: attempting urlopen')
			req = urllib2.Request(url, None, headers)

			# Do the request, log any errors
			request = urllib2.urlopen(req)
			response = request.read()
		except urllib2.HTTPError, e:
			self.mainLogger.error('Unable to get CouchDB status - HTTPError = %s', e)
			return False

		except urllib2.URLError, e:
			self.mainLogger.error('Unable to get CouchDB status - URLError = %s', e)
			return False

		except httplib.HTTPException, e:
			self.mainLogger.error('Unable to get CouchDB status - HTTPException = %s', e)
			return False

		except Exception, e:
			import traceback
			self.mainLogger.error('Unable to get CouchDB status - Exception = %s', traceback.format_exc())
			return False

		try:

			if int(pythonVersion[1]) >= 6:
				self.mainLogger.debug('getCouchDBStatus: json read')
				databases = json.loads(response)

			else:
				self.mainLogger.debug('getCouchDBStatus: minjson read')
				databases = minjson.safeRead(response)

		except Exception, e:
			import traceback
			self.mainLogger.error('Unable to load CouchDB database JSON - Exception = %s', traceback.format_exc())
			return False

		for dbName in databases:
			endpoint = '/%s/' % dbName

			try:
				url = '%s%s' % (self.agentConfig['CouchDBServer'], endpoint)
				self.mainLogger.debug('getCouchDBStatus: attempting urlopen')
				req = urllib2.Request(url, None, headers)

				# Do the request, log any errors
				request = urllib2.urlopen(req)
				response = request.read()
			except urllib2.HTTPError, e:
				self.mainLogger.error('Unable to get CouchDB database status - HTTPError = %s', e)
				return False

			except urllib2.URLError, e:
				self.mainLogger.error('Unable to get CouchDB database status - URLError = %s', e)
				return False

			except httplib.HTTPException, e:
				self.mainLogger.error('Unable to get CouchDB database status - HTTPException = %s', e)
				return False

			except Exception, e:
				import traceback
				self.mainLogger.error('Unable to get CouchDB database status - Exception = %s', traceback.format_exc())
				return False

			try:

				if int(pythonVersion[1]) >= 6:
					self.mainLogger.debug('getCouchDBStatus: json read')
					couchdb['databases'][dbName] = json.loads(response)

				else:
					self.mainLogger.debug('getCouchDBStatus: minjson read')
					couchdb['databases'][dbName] = minjson.safeRead(response)

			except Exception, e:
				import traceback
				self.mainLogger.error('Unable to load CouchDB database JSON - Exception = %s', traceback.format_exc())
				return False

		self.mainLogger.debug('getCouchDBStatus: completed, returning')
		return couchdb

	def getCPUStats(self):
		self.mainLogger.debug('getCPUStats: start')

		cpuStats = {}

		if sys.platform == 'linux2':
			self.mainLogger.debug('getCPUStats: linux2')

			headerRegexp = re.compile(r'.*?([%][a-zA-Z0-9]+)[\s+]?')
			itemRegexp = re.compile(r'.*?\s+(\d+)[\s+]?')
			valueRegexp = re.compile(r'\d+\.\d+')
			proc = None
			try:
				proc = subprocess.Popen(['mpstat', '-P', 'ALL', '1', '1'], stdout=subprocess.PIPE, close_fds=True)
				stats = proc.communicate()[0]

				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

				stats = stats.split('\n')
				header = stats[2]
				headerNames = re.findall(headerRegexp, header)
				device = None

				for statsIndex in range(3, len(stats)):
					row = stats[statsIndex]

					if not row: # skip the averages
						break

					deviceMatch = re.match(itemRegexp, row)

					if string.find(row, 'all') is not -1:
						device = 'ALL'
					elif deviceMatch is not None:
						device = 'CPU%s' % deviceMatch.groups()[0]

					values = re.findall(valueRegexp, row.replace(',', '.'))

					cpuStats[device] = {}
					for headerIndex in range(0, len(headerNames)):
						headerName = headerNames[headerIndex]
						cpuStats[device][headerName] = values[headerIndex]

			except OSError, ex:
				# we dont have it installed return nothing
				return False

			except Exception, ex:
				if int(pythonVersion[1]) >= 6:
					try:
						if proc:
							proc.kill()
					except UnboundLocalError, e:
						self.mainLogger.debug('Process already terminated')
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

				import traceback
				self.mainLogger.error('getCPUStats: exception = %s', traceback.format_exc())
				return False
		elif sys.platform == 'darwin':
			self.mainLogger.debug('getCPUStats: darwin')

			try:
				proc = subprocess.Popen(['sar', '-u', '1', '2'], stdout=subprocess.PIPE, close_fds=True)
				stats = proc.communicate()[0]

				itemRegexp = re.compile(r'\s+(\d+)[\s+]?')
				titleRegexp = re.compile(r'.*?([%][a-zA-Z0-9]+)[\s+]?')
				titles = []
				values = []
				for line in stats.split('\n'):
					# top line with the titles in
					if '%' in line:
						titles = re.findall(titleRegexp, line)
					if line and line.startswith('Average:'):
						values = re.findall(itemRegexp, line)

				if values and titles:
					cpuStats['CPUs'] = dict(zip(titles, values))

			except Exception, ex:
				import traceback
				self.mainLogger.error('getCPUStats: exception = %s', traceback.format_exc())
				return False

		else:
			self.mainLogger.debug('getCPUStats: unsupported platform')
			return False

		self.mainLogger.debug('getCPUStats: completed, returning')
		return cpuStats

	def getDiskUsage(self):
		self.mainLogger.debug('getDiskUsage: start')

		# Get output from df
		try:
			try:
				self.mainLogger.debug('getDiskUsage: attempting Popen')

				proc = subprocess.Popen(['df', '-k'], stdout=subprocess.PIPE, close_fds=True) # -k option uses 1024 byte blocks so we can calculate into MB

				df = proc.communicate()[0]

				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

			except Exception, e:
				import traceback
				self.mainLogger.error('getDiskUsage: df -k exception = %s', traceback.format_exc())
				return False

		finally:
			if int(pythonVersion[1]) >= 6:
				try:
					proc.kill()
				except Exception, e:
					self.mainLogger.debug('Process already terminated')

		self.mainLogger.debug('getDiskUsage: Popen success, start parsing')

		# Split out each volume
		volumes = df.split('\n')

		self.mainLogger.debug('getDiskUsage: parsing, split')

		# Remove first (headings) and last (blank)
		volumes.pop(0)
		volumes.pop()

		self.mainLogger.debug('getDiskUsage: parsing, pop')

		usageData = []

		regexp = re.compile(r'([0-9]+)')

		# Set some defaults
		previousVolume = None
		volumeCount = 0

		self.mainLogger.debug('getDiskUsage: parsing, start loop')

		for volume in volumes:
			self.mainLogger.debug('getDiskUsage: parsing volume: %s', volume)

			# Split out the string
			volume = volume.split(None, 10)

			# Handle df output wrapping onto multiple lines (case 27078 and case 30997)
			# Thanks to http://github.com/sneeu
			if len(volume) == 1: # If the length is 1 then this just has the mount name
				previousVolume = volume[0] # We store it, then continue the for
				continue

			if previousVolume != None: # If the previousVolume was set (above) during the last loop
				volume.insert(0, previousVolume) # then we need to insert it into the volume
				previousVolume = None # then reset so we don't use it again

			volumeCount = volumeCount + 1

			# Sometimes the first column will have a space, which is usually a system line that isn't relevant
			# e.g. map -hosts              0         0          0   100%    /net
			# so we just get rid of it
			# Also ignores lines with no values (AGENT-189)
			if re.match(regexp, volume[1]) == None or re.match(regexp, volume[2]) == None or re.match(regexp, volume[3]) == None:

				pass

			else:
				try:
					volume[2] = int(volume[2]) / 1024 / 1024 # Used
					volume[3] = int(volume[3]) / 1024 / 1024 # Available
				except Exception, e:
					self.mainLogger.error('getDiskUsage: parsing, loop %s - Used or Available not present' % (repr(e),))

				usageData.append(volume)

		self.mainLogger.debug('getDiskUsage: completed, returning')

		return usageData

	def getDiskMetaData(self):
		disks = []
		try:
			import glob
		except:
			return False
		try:
			for device in glob.glob('/dev/disk/by-id/google*'):
				if not device or not device.startswith('/dev/disk/by-id/google-'):
					continue

				deviceName = os.path.realpath(device).split('/')[-1]
				match = re.search(r'\d+$', deviceName)

				if match:
					continue

				diskNameFull = device.split('/')[-1]
				disks.append({
					'volumeName': diskNameFull.split('-')[1], 'device' : deviceName
				})

		except Exception, ex:
			import traceback
			self.mainLogger.error('getDiskMetaData: exception = %s', traceback.format_exc())
			return False

		return disks

	def getIOStats(self):
		self.mainLogger.debug('getIOStats: start')

		ioStats = {}

		if sys.platform == 'linux2':
			self.mainLogger.debug('getIOStats: linux2')

			headerRegexp = re.compile(r'([%\\/\-\_a-zA-Z0-9]+)[\s+]?')
			itemRegexp = re.compile(r'^([a-zA-Z0-9\/]+)')
			valueRegexp = re.compile(r'\d+\.\d+')

			try:
				try:
					proc = subprocess.Popen(['iostat', '-d', '1', '2', '-x', '-k'], stdout=subprocess.PIPE, close_fds=True)

					stats = proc.communicate()[0]
					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

					recentStats = stats.split('Device:')[2].split('\n')
					header = recentStats[0]
					headerNames = re.findall(headerRegexp, header)
					device = None

					for statsIndex in range(1, len(recentStats)):
						row = recentStats[statsIndex]

						if not row:
							# Ignore blank lines.
							continue

						deviceMatch = re.match(itemRegexp, row)

						if deviceMatch is not None:
							# Sometimes device names span two lines.
							device = deviceMatch.groups()[0]

						values = re.findall(valueRegexp, row.replace(',', '.'))

						if not values:
							# Sometimes values are on the next line so we encounter
							# instances of [].
							continue

						ioStats[device] = {}

						for headerIndex in range(0, len(headerNames)):
							headerName = headerNames[headerIndex]
							ioStats[device][headerName] = values[headerIndex]

				except OSError, ex:
					# we don't have iostats installed just return false
					return False

				except Exception, ex:
					import traceback
					self.mainLogger.error('getIOStats: exception = %s', traceback.format_exc())
					return False
			finally:
				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

		elif sys.platform == 'darwin':
			self.mainLogger.debug('getIOStats: darwin')

			try:
				try:
					proc1 = subprocess.Popen(["iostat", "-d", "disk0"], stdout=subprocess.PIPE, close_fds=True)
					proc2 = subprocess.Popen(["tail", "-1"], stdin=proc1.stdout, stdout=subprocess.PIPE, close_fds=True)
					proc1.stdout.close()
					proc3 = subprocess.Popen(["awk", '\"{ print $1,$2,int($3) }\"'], stdin=proc2.stdout, stdout=subprocess.PIPE, close_fds=True)
					proc2.stdout.close()
					proc4 = subprocess.Popen(["sed", r's/ /:/g'], stdin=proc3.stdout, stdout=subprocess.PIPE, close_fds=True)
					proc3.stdout.close()

					stats = proc4.communicate()[0]

					stats = stats.split(':')

					ioStats = {}
					ioStats['disk0'] = {}
					ioStats['disk0']['KBt'] = stats[3] # kilobytes per transfer
					ioStats['disk0']['tps'] = stats[5] # transfers per second
					ioStats['disk0']['MBs'] = stats[7] # megabytes per second

					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

				except OSError, ex:
					# we don't have iostats installed just return false
					return False

				except Exception, ex:
					import traceback
					self.mainLogger.error('getIOStats: exception = %s', traceback.format_exc())
					return False
			finally:
				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

		else:
			self.mainLogger.debug('getIOStats: unsupported platform')
			return False

		self.mainLogger.debug('getIOStats: completed, returning')
		return ioStats

	def getLoadAvrgs(self):
		self.mainLogger.debug('getLoadAvrgs: start')

		# If Linux like procfs system is present and mounted we use loadavg, else we use uptime
		if sys.platform == 'linux2':

			self.mainLogger.debug('getLoadAvrgs: linux2')

			try:
				self.mainLogger.debug('getLoadAvrgs: attempting open')

				if sys.platform == 'linux2':
					loadAvrgProc = open('/proc/loadavg', 'r')
				else:
					loadAvrgProc = open(self.linuxProcFsLocation + '/loadavg', 'r')

				uptime = loadAvrgProc.readlines()

			except IOError, e:
				self.mainLogger.error('getLoadAvrgs: exceptio = %s', e)
				return False

			self.mainLogger.debug('getLoadAvrgs: open success')

			loadAvrgProc.close()

			uptime = uptime[0] # readlines() provides a list but we want a string

		elif sys.platform.find('freebsd') != -1:
			self.mainLogger.debug('getLoadAvrgs: freebsd (uptime)')

			try:
				try:
					self.mainLogger.debug('getLoadAvrgs: attempting Popen')

					proc = subprocess.Popen(['uptime'], stdout=subprocess.PIPE, close_fds=True)
					uptime = proc.communicate()[0]

					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

				except Exception, e:
					import traceback
					self.mainLogger.error('getLoadAvrgs: exception = %s', traceback.format_exc())
					return False
			finally:
				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

			self.mainLogger.debug('getLoadAvrgs: Popen success')

		elif sys.platform == 'darwin':
			self.mainLogger.debug('getLoadAvrgs: darwin')

			# Get output from uptime
			try:
				try:
					self.mainLogger.debug('getLoadAvrgs: attempting Popen')

					proc = subprocess.Popen(['uptime'], stdout=subprocess.PIPE, close_fds=True, stderr=subprocess.PIPE)
					uptime = proc.communicate()[0]

					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

				except Exception, e:
					import traceback
					self.mainLogger.error('getLoadAvrgs: exception = %s', traceback.format_exc())
					return False
			finally:
				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

			self.mainLogger.debug('getLoadAvrgs: Popen success')

		elif sys.platform.find('sunos') != -1:
			self.mainLogger.debug('getLoadAvrgs: solaris (uptime)')

			try:
				try:
					self.mainLogger.debug('getLoadAvrgs: attempting Popen')

					proc = subprocess.Popen(['uptime'], stdout=subprocess.PIPE, close_fds=True)
					uptime = proc.communicate()[0]

					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

				except Exception, e:
					import traceback
					self.mainLogger.error('getLoadAvrgs: exception = %s', traceback.format_exc())
					return False
			finally:
				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

			self.mainLogger.debug('getLoadAvrgs: Popen success')

		else:
			self.mainLogger.debug('getLoadAvrgs: other platform, returning')
			return False

		self.mainLogger.debug('getLoadAvrgs: parsing')

		# Split out the 3 load average values
		loadAvrgs = [res.replace(',', '.') for res in re.findall(r'([0-9]+[\.,]\d+)', uptime)]
		loadAvrgs = {'1': loadAvrgs[0], '5': loadAvrgs[1], '15': loadAvrgs[2]}

		self.mainLogger.debug('getLoadAvrgs: completed, returning')

		return loadAvrgs

	def getMemoryUsage(self):
		self.mainLogger.debug('getMemoryUsage: start')

		# If Linux like procfs system is present and mounted we use meminfo, else we use "native" mode (vmstat and swapinfo)
		if sys.platform == 'linux2':

			self.mainLogger.debug('getMemoryUsage: linux2')

			try:
				self.mainLogger.debug('getMemoryUsage: attempting open')

				if sys.platform == 'linux2':
					meminfoProc = open('/proc/meminfo', 'r')
				else:
					meminfoProc = open(self.linuxProcFsLocation + '/meminfo', 'r')

				lines = meminfoProc.readlines()

			except IOError, e:
				self.mainLogger.error('getMemoryUsage: exception = %s', e)
				return False

			self.mainLogger.debug('getMemoryUsage: Popen success, parsing')

			meminfoProc.close()

			self.mainLogger.debug('getMemoryUsage: open success, parsing')

			regexp = re.compile(r'([0-9]+)') # We run this several times so one-time compile now

			meminfo = {}

			self.mainLogger.debug('getMemoryUsage: parsing, looping')

			# Loop through and extract the numerical values
			for line in lines:
				values = line.split(':')

				try:
					# Picks out the key (values[0]) and makes a list with the value as the meminfo value (values[1])
					# We are only interested in the KB data so regexp that out
					match = re.search(regexp, values[1])

					if match != None:
						meminfo[str(values[0])] = match.group(0)

				except IndexError:
					break

			self.mainLogger.debug('getMemoryUsage: parsing, looped')

			memData = {}
			memData['physFree'] = 0
			memData['physUsed'] = 0
			memData['cached'] = 0
			memData['swapFree'] = 0
			memData['swapUsed'] = 0

			# Phys
			try:
				self.mainLogger.debug('getMemoryUsage: formatting (phys)')

				physTotal = int(meminfo['MemTotal'])
				physFree = int(meminfo['MemFree'])
				physUsed = physTotal - physFree

				# Convert to MB
				memData['physFree'] = physFree / 1024
				memData['physUsed'] = physUsed / 1024
				memData['cached'] = int(meminfo['Cached']) / 1024

			# Stops the agent crashing if one of the meminfo elements isn't set
			except IndexError:
				self.mainLogger.error('getMemoryUsage: formatting (phys) IndexError - Cached, MemTotal or MemFree not present')

			except KeyError:
				self.mainLogger.error('getMemoryUsage: formatting (phys) KeyError - Cached, MemTotal or MemFree not present')

			self.mainLogger.debug('getMemoryUsage: formatted (phys)')

			# Swap
			try:
				self.mainLogger.debug('getMemoryUsage: formatting (swap)')

				swapTotal = int(meminfo['SwapTotal'])
				swapFree = int(meminfo['SwapFree'])
				swapUsed = swapTotal - swapFree

				# Convert to MB
				memData['swapFree'] = swapFree / 1024
				memData['swapUsed'] = swapUsed / 1024

			# Stops the agent crashing if one of the meminfo elements isn't set
			except IndexError:
				self.mainLogger.error('getMemoryUsage: formatting (swap) IndexError - SwapTotal or SwapFree not present')

			except KeyError:
				self.mainLogger.error('getMemoryUsage: formatting (swap) KeyError - SwapTotal or SwapFree not present')

			self.mainLogger.debug('getMemoryUsage: formatted (swap), completed, returning')

			return memData

		elif sys.platform.find('freebsd') != -1:
			self.mainLogger.debug('getMemoryUsage: freebsd (native)')

			physFree = None

			try:
				try:
					self.mainLogger.debug('getMemoryUsage: attempting sysinfo')

					proc = subprocess.Popen(['sysinfo', '-v', 'mem'], stdout = subprocess.PIPE, close_fds = True)
					sysinfo = proc.communicate()[0]

					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

					sysinfo = sysinfo.split('\n')

					regexp = re.compile(r'([0-9]+)') # We run this several times so one-time compile now

					for line in sysinfo:

						parts = line.split(' ')

						if parts[0] == 'Free':

							self.mainLogger.debug('getMemoryUsage: parsing free')

							for part in parts:

								match = re.search(regexp, part)

								if match != None:
									physFree = match.group(0)
									self.mainLogger.debug('getMemoryUsage: sysinfo: found free %s', physFree)

						if parts[0] == 'Active':

							self.mainLogger.debug('getMemoryUsage: parsing used')

							for part in parts:

								match = re.search(regexp, part)

								if match != None:
									physUsed = match.group(0)
									self.mainLogger.debug('getMemoryUsage: sysinfo: found used %s', physUsed)

						if parts[0] == 'Cached':

							self.mainLogger.debug('getMemoryUsage: parsing cached')

							for part in parts:

								match = re.search(regexp, part)

								if match != None:
									cached = match.group(0)
									self.mainLogger.debug('getMemoryUsage: sysinfo: found cached %s', cached)

				except OSError, e:

					self.mainLogger.debug('getMemoryUsage: sysinfo not available')

				except Exception, e:
					import traceback
					self.mainLogger.error('getMemoryUsage: exception = %s', traceback.format_exc())
			finally:
				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

			if physFree == None:

				self.mainLogger.info('getMemoryUsage: sysinfo not installed so falling back on sysctl. sysinfo provides more accurate memory info so is recommended. http://www.freshports.org/sysutils/sysinfo')

				try:
					try:
						self.mainLogger.debug('getMemoryUsage: attempting Popen (sysctl)')

						proc = subprocess.Popen(['sysctl', '-n', 'hw.physmem'], stdout = subprocess.PIPE, close_fds = True)
						physTotal = proc.communicate()[0]

						if int(pythonVersion[1]) >= 6:
							try:
								proc.kill()
							except Exception, e:
								self.mainLogger.debug('Process already terminated')

						self.mainLogger.debug('getMemoryUsage: attempting Popen (vmstat)')
						proc = subprocess.Popen(['vmstat', '-H'], stdout = subprocess.PIPE, close_fds = True)
						vmstat = proc.communicate()[0]

						if int(pythonVersion[1]) >= 6:
							try:
								proc.kill()
							except Exception, e:
								self.mainLogger.debug('Process already terminated')

					except Exception, e:
						import traceback
						self.mainLogger.error('getMemoryUsage: exception = %s', traceback.format_exc())

						return False
				finally:
					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

				self.mainLogger.debug('getMemoryUsage: Popen success, parsing')

				# First we parse the information about the real memory
				lines = vmstat.split('\n')
				physParts = lines[2].split(' ')

				physMem = []

				# We need to loop through and capture the numerical values
				# because sometimes there will be strings and spaces
				for k, v in enumerate(physParts):

					if re.match(r'([0-9]+)', v) != None:
						physMem.append(v)

				physTotal = int(physTotal.strip()) / 1024 # physFree is returned in B, but we need KB so we convert it
				physFree = int(physMem[4])
				physUsed = int(physTotal - physFree)

				self.mainLogger.debug('getMemoryUsage: parsed vmstat')

				# Convert everything to MB
				physUsed = int(physUsed) / 1024
				physFree = int(physFree) / 1024

				cached = 'NULL'

			#
			# Swap memory details
			#

			self.mainLogger.debug('getMemoryUsage: attempting Popen (swapinfo)')

			try:
				try:
					proc = subprocess.Popen(['swapinfo', '-k'], stdout = subprocess.PIPE, close_fds = True)
					swapinfo = proc.communicate()[0]

					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

				except Exception, e:
						import traceback
						self.mainLogger.error('getMemoryUsage: exception = %s', traceback.format_exc())

						return False
			finally:
				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

			lines = swapinfo.split('\n')
			swapUsed = 0
			swapFree = 0

			for index in range(1, len(lines)):
				swapParts = re.findall(r'(\d+)', lines[index])

				if swapParts != None:
					try:
						swapUsed += int(swapParts[len(swapParts) - 3]) / 1024
						swapFree += int(swapParts[len(swapParts) - 2]) / 1024
					except IndexError, e:
						pass

			self.mainLogger.debug('getMemoryUsage: parsed swapinfo, completed, returning')

			return {'physUsed' : physUsed, 'physFree' : physFree, 'swapUsed' : swapUsed, 'swapFree' : swapFree, 'cached' : cached}

		elif sys.platform == 'darwin':
			self.mainLogger.debug('getMemoryUsage: darwin')

			try:
				try:
					self.mainLogger.debug('getMemoryUsage: attempting Popen (top)')

					proc = subprocess.Popen(['top', '-l 1'], stdout=subprocess.PIPE, close_fds=True)
					top = proc.communicate()[0]

					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

					self.mainLogger.debug('getMemoryUsage: attempting Popen (sysctl)')
					proc = subprocess.Popen(['sysctl', 'vm.swapusage'], stdout=subprocess.PIPE, close_fds=True)
					sysctl = proc.communicate()[0]

					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

				except Exception, e:
					import traceback
					self.mainLogger.error('getMemoryUsage: exception = %s', traceback.format_exc())
					return False
			finally:
				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

			self.mainLogger.debug('getMemoryUsage: Popen success, parsing')

			# Deal with top
			lines = top.split('\n')
			physParts = re.findall(r'([0-9]\d+[A-Z])', lines[self.topIndex])

			self.mainLogger.debug('getMemoryUsage: lines to parse: ' + lines[self.topIndex])
			self.mainLogger.debug('getMemoryUsage: parsed top')

			# Deal with sysctl
			swapParts = re.findall(r'([0-9]+\.\d+)', sysctl)

			# large values become G, rather than M
			finalParts = []
			for part in physParts:
				if 'G' in part:
					finalParts.append(str(int(part[:-1]) * 1024))
				else:
					finalParts.append(part[:-1])
			physParts = finalParts


			self.mainLogger.debug('getMemoryUsage: parsed sysctl, completed, returning')

			# Format changed in OSX Mavericks
			if len(physParts) > 3:
				data = {'physUsed' : physParts[3], 'physFree' : physParts[4], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2], 'cached' : 'NULL'}
			else:
				data = {'physUsed' : physParts[0], 'physFree' : physParts[2], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2], 'cached' : 'NULL'}
			return data

		else:
			self.mainLogger.debug('getMemoryUsage: other platform, returning')
			return False

	def getMongoDBStatus(self):
		self.mainLogger.debug('getMongoDBStatus: start')

		if 'MongoDBServer' not in self.agentConfig or self.agentConfig['MongoDBServer'] == '':
			self.mainLogger.debug('getMongoDBStatus: config not set')
			return False

		self.mainLogger.debug('getMongoDBStatus: config set')

		try:
			import pymongo
			from pymongo import Connection

		except ImportError:
			self.mainLogger.error('Unable to import pymongo library')
			return False

		# The dictionary to be returned.
		mongodb = {}

		try:
			import urlparse
			parsed = urlparse.urlparse(self.agentConfig['MongoDBServer'])

			mongoURI = ''

			# Can't use attributes on Python 2.4
			if parsed[0] != 'mongodb':

				mongoURI = 'mongodb://'

				if parsed[2]:

					if parsed[0]:

						mongoURI = mongoURI + parsed[0] + ':' + parsed[2]

					else:
						mongoURI = mongoURI + parsed[2]

			else:

				mongoURI = self.agentConfig['MongoDBServer']

			self.mainLogger.debug('-- mongoURI: %s', mongoURI)

			conn = Connection(mongoURI, slave_okay=True)

			self.mainLogger.debug('Connected to MongoDB')

		except Exception, ex:
			import traceback
			self.mainLogger.error('Unable to connect to MongoDB server %s - Exception = %s', mongoURI, traceback.format_exc())
			return False

		# Older versions of pymongo did not support the command()
		# method below.
		try:
			db = conn['local']

			# Server status
			statusOutput = db.command('serverStatus', recordStats=0) # Shorthand for {'serverStatus': 1}

			self.mainLogger.debug('getMongoDBStatus: executed serverStatus')

			# Setup
			import datetime
			status = {}

			# Version
			try:
				status['version'] = statusOutput['version']

				self.mainLogger.debug('getMongoDBStatus: version %s', statusOutput['version'])

			except KeyError, ex:
				self.mainLogger.error('getMongoDBStatus: version KeyError exception = %s', ex)
				pass

			# Global locks
			try:
				split_version = status['version'].split('.')
				split_version = map(lambda x: int(x), split_version)

				if (split_version[0] <= 2) and (split_version[1] < 2):

					self.mainLogger.debug('getMongoDBStatus: globalLock')

					status['globalLock'] = {}
					status['globalLock']['ratio'] = statusOutput['globalLock']['ratio']

					status['globalLock']['currentQueue'] = {}
					status['globalLock']['currentQueue']['total'] = statusOutput['globalLock']['currentQueue']['total']
					status['globalLock']['currentQueue']['readers'] = statusOutput['globalLock']['currentQueue']['readers']
					status['globalLock']['currentQueue']['writers'] = statusOutput['globalLock']['currentQueue']['writers']
				else:
					self.mainLogger.debug('getMongoDBStatus: version >= 2.2, not getting globalLock status')

			except KeyError, ex:
				self.mainLogger.error('getMongoDBStatus: globalLock KeyError exception = %s', ex)
				pass

			# Memory
			try:
				self.mainLogger.debug('getMongoDBStatus: memory')

				status['mem'] = {}
				status['mem']['resident'] = statusOutput['mem']['resident']
				status['mem']['virtual'] = statusOutput['mem']['virtual']
				status['mem']['mapped'] = statusOutput['mem']['mapped']

			except KeyError, ex:
				self.mainLogger.error('getMongoDBStatus: memory KeyError exception = %s', ex)
				pass

			# Connections
			try:
				self.mainLogger.debug('getMongoDBStatus: connections')

				status['connections'] = {}
				status['connections']['current'] = statusOutput['connections']['current']
				status['connections']['available'] = statusOutput['connections']['available']

			except KeyError, ex:
				self.mainLogger.error('getMongoDBStatus: connections KeyError exception = %s', ex)
				pass

			# Extra info (Linux only)
			try:
				self.mainLogger.debug('getMongoDBStatus: extra info')

				status['extraInfo'] = {}
				status['extraInfo']['heapUsage'] = statusOutput['extra_info']['heap_usage_bytes']
				status['extraInfo']['pageFaults'] = statusOutput['extra_info']['page_faults']

			except KeyError, ex:
				self.mainLogger.debug('getMongoDBStatus: extra info KeyError exception = %s', ex)
				pass

			# Background flushing
			try:
				self.mainLogger.debug('getMongoDBStatus: backgroundFlushing')

				status['backgroundFlushing'] = {}
				delta = datetime.datetime.utcnow() - statusOutput['backgroundFlushing']['last_finished']
				status['backgroundFlushing']['secondsSinceLastFlush'] = delta.seconds
				status['backgroundFlushing']['lastFlushLength'] = statusOutput['backgroundFlushing']['last_ms']
				status['backgroundFlushing']['flushLengthAvrg'] = statusOutput['backgroundFlushing']['average_ms']

			except KeyError, ex:
				self.mainLogger.debug('getMongoDBStatus: backgroundFlushing KeyError exception = %s', ex)
				pass

			# Per second metric calculations (opcounts and asserts)
			try:
				if self.mongoDBStore == None:
					self.mainLogger.debug('getMongoDBStatus: per second metrics no cached data, so storing for first time')
					self.setMongoDBStore(statusOutput)

				else:
					self.mainLogger.debug('getMongoDBStatus: per second metrics cached data exists')

					if (split_version[0] <= 2) and (split_version[1] < 4):

						self.mainLogger.debug("getMongoDBStatus: version < 2.4, using btree")

						accessesPS = float(statusOutput['indexCounters']['btree']['accesses'] - self.mongoDBStore['indexCounters']['btree']['accessesPS']) / 60

						if accessesPS >= 0:
							status['indexCounters'] = {}
							status['indexCounters']['btree'] = {}
							status['indexCounters']['btree']['accessesPS'] = accessesPS
							status['indexCounters']['btree']['hitsPS'] = float(statusOutput['indexCounters']['btree']['hits'] - self.mongoDBStore['indexCounters']['btree']['hitsPS']) / 60
							status['indexCounters']['btree']['missesPS'] = float(statusOutput['indexCounters']['btree']['misses'] - self.mongoDBStore['indexCounters']['btree']['missesPS']) / 60
							status['indexCounters']['btree']['missRatioPS'] = float(statusOutput['indexCounters']['btree']['missRatio'] - self.mongoDBStore['indexCounters']['btree']['missRatioPS']) / 60

							status['opcounters'] = {}
							status['opcounters']['insertPS'] = float(statusOutput['opcounters']['insert'] - self.mongoDBStore['opcounters']['insertPS']) / 60
							status['opcounters']['queryPS'] = float(statusOutput['opcounters']['query'] - self.mongoDBStore['opcounters']['queryPS']) / 60
							status['opcounters']['updatePS'] = float(statusOutput['opcounters']['update'] - self.mongoDBStore['opcounters']['updatePS']) / 60
							status['opcounters']['deletePS'] = float(statusOutput['opcounters']['delete'] - self.mongoDBStore['opcounters']['deletePS']) / 60
							status['opcounters']['getmorePS'] = float(statusOutput['opcounters']['getmore'] - self.mongoDBStore['opcounters']['getmorePS']) / 60
							status['opcounters']['commandPS'] = float(statusOutput['opcounters']['command'] - self.mongoDBStore['opcounters']['commandPS']) / 60

							status['asserts'] = {}
							status['asserts']['regularPS'] = float(statusOutput['asserts']['regular'] - self.mongoDBStore['asserts']['regularPS']) / 60
							status['asserts']['warningPS'] = float(statusOutput['asserts']['warning'] - self.mongoDBStore['asserts']['warningPS']) / 60
							status['asserts']['msgPS'] = float(statusOutput['asserts']['msg'] - self.mongoDBStore['asserts']['msgPS']) / 60
							status['asserts']['userPS'] = float(statusOutput['asserts']['user'] - self.mongoDBStore['asserts']['userPS']) / 60
							status['asserts']['rolloversPS'] = float(statusOutput['asserts']['rollovers'] - self.mongoDBStore['asserts']['rolloversPS']) / 60

							self.setMongoDBStore(statusOutput)
					elif (split_version[0] <= 2) and (split_version[1] >= 4):

						self.mainLogger.debug("getMongoDBStatus: version >= 2.4, not using btree")

						accessesPS = float(statusOutput['indexCounters']['accesses'] - self.mongoDBStore['indexCounters']['btree']['accessesPS']) / 60

						if accessesPS >= 0:
							status['indexCounters'] = {}
							status['indexCounters']['btree'] = {}
							status['indexCounters']['btree']['accessesPS'] = accessesPS
							status['indexCounters']['btree']['hitsPS'] = float(statusOutput['indexCounters']['hits'] - self.mongoDBStore['indexCounters']['btree']['hitsPS']) / 60
							status['indexCounters']['btree']['missesPS'] = float(statusOutput['indexCounters']['misses'] - self.mongoDBStore['indexCounters']['btree']['missesPS']) / 60
							status['indexCounters']['btree']['missRatioPS'] = float(statusOutput['indexCounters']['missRatio'] - self.mongoDBStore['indexCounters']['btree']['missRatioPS']) / 60

							status['opcounters'] = {}
							status['opcounters']['insertPS'] = float(statusOutput['opcounters']['insert'] - self.mongoDBStore['opcounters']['insertPS']) / 60
							status['opcounters']['queryPS'] = float(statusOutput['opcounters']['query'] - self.mongoDBStore['opcounters']['queryPS']) / 60
							status['opcounters']['updatePS'] = float(statusOutput['opcounters']['update'] - self.mongoDBStore['opcounters']['updatePS']) / 60
							status['opcounters']['deletePS'] = float(statusOutput['opcounters']['delete'] - self.mongoDBStore['opcounters']['deletePS']) / 60
							status['opcounters']['getmorePS'] = float(statusOutput['opcounters']['getmore'] - self.mongoDBStore['opcounters']['getmorePS']) / 60
							status['opcounters']['commandPS'] = float(statusOutput['opcounters']['command'] - self.mongoDBStore['opcounters']['commandPS']) / 60

							status['asserts'] = {}
							status['asserts']['regularPS'] = float(statusOutput['asserts']['regular'] - self.mongoDBStore['asserts']['regularPS']) / 60
							status['asserts']['warningPS'] = float(statusOutput['asserts']['warning'] - self.mongoDBStore['asserts']['warningPS']) / 60
							status['asserts']['msgPS'] = float(statusOutput['asserts']['msg'] - self.mongoDBStore['asserts']['msgPS']) / 60
							status['asserts']['userPS'] = float(statusOutput['asserts']['user'] - self.mongoDBStore['asserts']['userPS']) / 60
							status['asserts']['rolloversPS'] = float(statusOutput['asserts']['rollovers'] - self.mongoDBStore['asserts']['rolloversPS']) / 60

							self.setMongoDBStore(statusOutput)
					else:
						self.mainLogger.debug('getMongoDBStatus: per second metrics negative value calculated, mongod likely restarted, so clearing cache')
						self.setMongoDBStore(statusOutput)

			except KeyError, ex:
				self.mainLogger.error('getMongoDBStatus: per second metrics KeyError exception = %s', ex)
				pass

			# Cursors
			try:
				self.mainLogger.debug('getMongoDBStatus: cursors')

				status['cursors'] = {}
				status['cursors']['totalOpen'] = statusOutput['cursors']['totalOpen']

			except KeyError, ex:
				self.mainLogger.error('getMongoDBStatus: cursors KeyError exception = %s', ex)
				pass

			# Replica set status
			if 'MongoDBReplSet' in self.agentConfig and self.agentConfig['MongoDBReplSet'] == 'yes':
				self.mainLogger.debug('getMongoDBStatus: get replset status too')

				# isMaster (to get state
				isMaster = db.command('isMaster')

				self.mainLogger.debug('getMongoDBStatus: executed isMaster')

				status['replSet'] = {}
				status['replSet']['setName'] = isMaster['setName']
				status['replSet']['isMaster'] = isMaster['ismaster']
				status['replSet']['isSecondary'] = isMaster['secondary']

				if 'arbiterOnly' in isMaster:
					status['replSet']['isArbiter'] = isMaster['arbiterOnly']

				self.mainLogger.debug('getMongoDBStatus: finished isMaster')

				# rs.status()
				db = conn['admin']
				replSet = db.command('replSetGetStatus')

				self.mainLogger.debug('getMongoDBStatus: executed replSetGetStatus')

				status['replSet']['myState'] = replSet['myState']

				status['replSet']['members'] = {}

				for member in replSet['members']:

					self.mainLogger.debug('getMongoDBStatus: replSetGetStatus looping %s', member['name'])

					status['replSet']['members'][str(member['_id'])] = {}

					status['replSet']['members'][str(member['_id'])]['name'] = member['name']
					status['replSet']['members'][str(member['_id'])]['state'] = member['state']

					# Optime delta (only available from not self)
					# Calculation is from http://docs.python.org/library/datetime.html#datetime.timedelta.total_seconds
					if 'optimeDate' in member: # Only available as of 1.7.2
						deltaOptime = datetime.datetime.utcnow() - member['optimeDate']
						status['replSet']['members'][str(member['_id'])]['optimeDate'] = (deltaOptime.microseconds + (deltaOptime.seconds + deltaOptime.days * 24 * 3600) * 10**6) / 10**6

					if 'self' in member:
						status['replSet']['myId'] = member['_id']

					# Have to do it manually because total_seconds() is only available as of Python 2.7
					else:
						if 'lastHeartbeat' in member:
							deltaHeartbeat = datetime.datetime.utcnow() - member['lastHeartbeat']
							status['replSet']['members'][str(member['_id'])]['lastHeartbeat'] = (deltaHeartbeat.microseconds + (deltaHeartbeat.seconds + deltaHeartbeat.days * 24 * 3600) * 10**6) / 10**6

					if 'errmsg' in member:
						status['replSet']['members'][str(member['_id'])]['error'] = member['errmsg']

			# db.stats()
			if 'MongoDBDBStats' in self.agentConfig and self.agentConfig['MongoDBDBStats'] == 'yes':
				self.mainLogger.debug('getMongoDBStatus: db.stats() too')

				status['dbStats'] = {}

				for database in conn.database_names():

					if database != 'config' and database != 'local' and database != 'admin' and database != 'test':

						self.mainLogger.debug('getMongoDBStatus: executing db.stats() for %s', database)

						status['dbStats'][database] = conn[database].command('dbstats')
						status['dbStats'][database]['namespaces'] = conn[database]['system']['namespaces'].count()

						# Ensure all strings to prevent JSON parse errors. We typecast on the server
						for key in status['dbStats'][database].keys():

							status['dbStats'][database][key] = str(status['dbStats'][database][key])


		except Exception, ex:
			import traceback
			self.mainLogger.error('Unable to get MongoDB status - Exception = %s', traceback.format_exc())
			return False

		self.mainLogger.debug('getMongoDBStatus: completed, returning')

		return status

	def setMongoDBStore(self, statusOutput):

		split_version = statusOutput['version'].split('.')
		split_version = map(lambda x: int(x), split_version)

		if (split_version[0] <= 2) and (split_version[1] < 4):

			self.mainLogger.debug("getMongoDBStatus: version < 2.4, using btree")
			self.mongoDBStore = {}

			self.mongoDBStore['indexCounters'] = {}
			self.mongoDBStore['indexCounters']['btree'] = {}
			self.mongoDBStore['indexCounters']['btree']['accessesPS'] = statusOutput['indexCounters']['btree']['accesses']
			self.mongoDBStore['indexCounters']['btree']['hitsPS'] = statusOutput['indexCounters']['btree']['hits']
			self.mongoDBStore['indexCounters']['btree']['missesPS'] = statusOutput['indexCounters']['btree']['misses']
			self.mongoDBStore['indexCounters']['btree']['missRatioPS'] = statusOutput['indexCounters']['btree']['missRatio']

			self.mongoDBStore['opcounters'] = {}
			self.mongoDBStore['opcounters']['insertPS'] = statusOutput['opcounters']['insert']
			self.mongoDBStore['opcounters']['queryPS'] = statusOutput['opcounters']['query']
			self.mongoDBStore['opcounters']['updatePS'] = statusOutput['opcounters']['update']
			self.mongoDBStore['opcounters']['deletePS'] = statusOutput['opcounters']['delete']
			self.mongoDBStore['opcounters']['getmorePS'] = statusOutput['opcounters']['getmore']
			self.mongoDBStore['opcounters']['commandPS'] = statusOutput['opcounters']['command']

			self.mongoDBStore['asserts'] = {}
			self.mongoDBStore['asserts']['regularPS'] = statusOutput['asserts']['regular']
			self.mongoDBStore['asserts']['warningPS'] = statusOutput['asserts']['warning']
			self.mongoDBStore['asserts']['msgPS'] = statusOutput['asserts']['msg']
			self.mongoDBStore['asserts']['userPS'] = statusOutput['asserts']['user']
			self.mongoDBStore['asserts']['rolloversPS'] = statusOutput['asserts']['rollovers']

		elif (split_version[0] <= 2) and (split_version[1] >= 4):

			self.mainLogger.debug("getMongoDBStatus: version >= 2.4, not using btree")
			self.mongoDBStore = {}

			self.mongoDBStore['indexCounters'] = {}
			self.mongoDBStore['indexCounters']['btree'] = {}
			self.mongoDBStore['indexCounters']['btree']['accessesPS'] = statusOutput['indexCounters']['accesses']
			self.mongoDBStore['indexCounters']['btree']['hitsPS'] = statusOutput['indexCounters']['hits']
			self.mongoDBStore['indexCounters']['btree']['missesPS'] = statusOutput['indexCounters']['misses']
			self.mongoDBStore['indexCounters']['btree']['missRatioPS'] = statusOutput['indexCounters']['missRatio']

			self.mongoDBStore['opcounters'] = {}
			self.mongoDBStore['opcounters']['insertPS'] = statusOutput['opcounters']['insert']
			self.mongoDBStore['opcounters']['queryPS'] = statusOutput['opcounters']['query']
			self.mongoDBStore['opcounters']['updatePS'] = statusOutput['opcounters']['update']
			self.mongoDBStore['opcounters']['deletePS'] = statusOutput['opcounters']['delete']
			self.mongoDBStore['opcounters']['getmorePS'] = statusOutput['opcounters']['getmore']
			self.mongoDBStore['opcounters']['commandPS'] = statusOutput['opcounters']['command']

			self.mongoDBStore['asserts'] = {}
			self.mongoDBStore['asserts']['regularPS'] = statusOutput['asserts']['regular']
			self.mongoDBStore['asserts']['warningPS'] = statusOutput['asserts']['warning']
			self.mongoDBStore['asserts']['msgPS'] = statusOutput['asserts']['msg']
			self.mongoDBStore['asserts']['userPS'] = statusOutput['asserts']['user']
			self.mongoDBStore['asserts']['rolloversPS'] = statusOutput['asserts']['rollovers']

	def getMySQLStatus(self):
		self.mainLogger.debug('getMySQLStatus: start')

		if 'MySQLServer' in self.agentConfig and 'MySQLUser' in self.agentConfig and self.agentConfig['MySQLServer'] != '' and self.agentConfig['MySQLUser'] != '':

			self.mainLogger.debug('getMySQLStatus: config')

			# Try import MySQLdb - http://sourceforge.net/projects/mysql-python/files/
			try:
				import MySQLdb

			except ImportError, e:
				self.mainLogger.error('getMySQLStatus: unable to import MySQLdb')
				return False

			if 'MySQLPort' not in self.agentConfig:

				self.agentConfig['MySQLPort'] = 3306

			if 'MySQLSocket' not in self.agentConfig:

				# Connect
				try:
					db = MySQLdb.connect(host=self.agentConfig['MySQLServer'], user=self.agentConfig['MySQLUser'], passwd=self.agentConfig['MySQLPass'], port=int(self.agentConfig['MySQLPort']))

				except MySQLdb.OperationalError, message:

					self.mainLogger.error('getMySQLStatus: MySQL connection error (server): %s', message)
					return False

			else:

				# Connect
				try:
					db = MySQLdb.connect(host='localhost', user=self.agentConfig['MySQLUser'], passwd=self.agentConfig['MySQLPass'], port=int(self.agentConfig['MySQLPort']), unix_socket=self.agentConfig['MySQLSocket'])

				except MySQLdb.OperationalError, message:

					self.mainLogger.error('getMySQLStatus: MySQL connection error (socket): %s', message)
					return False

			self.mainLogger.debug('getMySQLStatus: connected')

			# Get MySQL version
			if self.mysqlVersion == None:

				self.mainLogger.debug('getMySQLStatus: mysqlVersion unset storing for first time')

				try:
					cursor = db.cursor()
					cursor.execute('SELECT VERSION()')
					result = cursor.fetchone()

				except MySQLdb.OperationalError, message:

					self.mainLogger.error('getMySQLStatus: MySQL query error when getting version: %s', message)

				version = result[0].split('-') # Case 31237. Might include a description e.g. 4.1.26-log. See http://dev.mysql.com/doc/refman/4.1/en/information-functions.html#function_version
				version = version[0].split('.')

				self.mysqlVersion = []

				# Make sure the version is only an int. Case 31647
				for string in version:
					number = re.match('([0-9]+)', string)
					number = number.group(0)
					self.mysqlVersion.append(number)

			self.mainLogger.debug('getMySQLStatus: getting Connections')

			# Connections
			try:
				cursor = db.cursor()
				cursor.execute('SHOW STATUS LIKE "Connections"')
				result = cursor.fetchone()

			except MySQLdb.OperationalError, message:

				self.mainLogger.error('getMySQLStatus: MySQL query error when getting Connections = %s', message)

			if self.mysqlConnectionsStore == None:

				self.mainLogger.debug('getMySQLStatus: mysqlConnectionsStore unset storing for first time')

				self.mysqlConnectionsStore = result[1]

				connections = 0

			else:

				self.mainLogger.debug('getMySQLStatus: mysqlConnectionsStore set so calculating')
				self.mainLogger.debug('getMySQLStatus: self.mysqlConnectionsStore = %s', self.mysqlConnectionsStore)
				self.mainLogger.debug('getMySQLStatus: result = %s', result[1])

				connections = float(float(result[1]) - float(self.mysqlConnectionsStore)) / 60

				# we can't have negative connections
				# causes weirdness
				# UV386
				if connections < 0:
					connections = 0

				self.mysqlConnectionsStore = result[1]

			self.mainLogger.debug('getMySQLStatus: connections  = %s', connections)

			self.mainLogger.debug('getMySQLStatus: getting Connections - done')

			self.mainLogger.debug('getMySQLStatus: getting Created_tmp_disk_tables')

			# Created_tmp_disk_tables

			# Determine query depending on version. For 5.02 and above we need the GLOBAL keyword (case 31015)
			if int(self.mysqlVersion[0]) >= 5 and int(self.mysqlVersion[2]) >= 2:
				query = 'SHOW GLOBAL STATUS LIKE "Created_tmp_disk_tables"'

			else:
				query = 'SHOW STATUS LIKE "Created_tmp_disk_tables"'

			try:
				cursor = db.cursor()
				cursor.execute(query)
				result = cursor.fetchone()

			except MySQLdb.OperationalError, message:

				self.mainLogger.error('getMySQLStatus: MySQL query error when getting Created_tmp_disk_tables = %s', message)

			createdTmpDiskTables = float(result[1])

			self.mainLogger.debug('getMySQLStatus: createdTmpDiskTables = %s', createdTmpDiskTables)

			self.mainLogger.debug('getMySQLStatus: getting Created_tmp_disk_tables - done')

			self.mainLogger.debug('getMySQLStatus: getting Max_used_connections')

			# Max_used_connections
			try:
				cursor = db.cursor()
				cursor.execute('SHOW STATUS LIKE "Max_used_connections"')
				result = cursor.fetchone()

			except MySQLdb.OperationalError, message:

				self.mainLogger.error('getMySQLStatus: MySQL query error when getting Max_used_connections = %s', message)

			maxUsedConnections = result[1]

			self.mainLogger.debug('getMySQLStatus: maxUsedConnections = %s', createdTmpDiskTables)

			self.mainLogger.debug('getMySQLStatus: getting Max_used_connections - done')

			self.mainLogger.debug('getMySQLStatus: getting Open_files')

			# Open_files
			try:
				cursor = db.cursor()
				cursor.execute('SHOW STATUS LIKE "Open_files"')
				result = cursor.fetchone()

			except MySQLdb.OperationalError, message:

				self.mainLogger.error('getMySQLStatus: MySQL query error when getting Open_files = %s', message)

			openFiles = result[1]

			self.mainLogger.debug('getMySQLStatus: openFiles = %s', openFiles)

			self.mainLogger.debug('getMySQLStatus: getting Open_files - done')

			self.mainLogger.debug('getMySQLStatus: getting Slow_queries')

			# Slow_queries

			# Determine query depending on version. For 5.02 and above we need the GLOBAL keyword (case 31015)
			if int(self.mysqlVersion[0]) >= 5 and int(self.mysqlVersion[2]) >= 2:
				query = 'SHOW GLOBAL STATUS LIKE "Slow_queries"'

			else:
				query = 'SHOW STATUS LIKE "Slow_queries"'

			try:
				cursor = db.cursor()
				cursor.execute(query)
				result = cursor.fetchone()

			except MySQLdb.OperationalError, message:

				self.mainLogger.error('getMySQLStatus: MySQL query error when getting Slow_queries = %s', message)

			if self.mysqlSlowQueriesStore == None:

				self.mainLogger.debug('getMySQLStatus: mysqlSlowQueriesStore unset so storing for first time')

				self.mysqlSlowQueriesStore = result[1]

				slowQueries = 0

			else:

				self.mainLogger.debug('getMySQLStatus: mysqlSlowQueriesStore set so calculating')
				self.mainLogger.debug('getMySQLStatus: self.mysqlSlowQueriesStore = %s', self.mysqlSlowQueriesStore)
				self.mainLogger.debug('getMySQLStatus: result = %s', result[1])

				slowQueries = float(float(result[1]) - float(self.mysqlSlowQueriesStore)) / 60

				# this can't be < 0
				if slowQueries < 0:
					slowQueries = 0

				self.mysqlSlowQueriesStore = result[1]

			self.mainLogger.debug('getMySQLStatus: slowQueries = %s', slowQueries)

			self.mainLogger.debug('getMySQLStatus: getting Slow_queries - done')

			self.mainLogger.debug('getMySQLStatus: getting Table_locks_waited')

			# Table_locks_waited
			try:
				cursor = db.cursor()
				cursor.execute('SHOW STATUS LIKE "Table_locks_waited"')
				result = cursor.fetchone()

			except MySQLdb.OperationalError, message:

				self.mainLogger.error('getMySQLStatus: MySQL query error when getting Table_locks_waited = %s', message)

			tableLocksWaited = float(result[1])

			self.mainLogger.debug('getMySQLStatus: tableLocksWaited  = %s', tableLocksWaited)

			self.mainLogger.debug('getMySQLStatus: getting Table_locks_waited - done')

			self.mainLogger.debug('getMySQLStatus: getting Threads_connected')

			# Threads_connected
			try:
				cursor = db.cursor()
				cursor.execute('SHOW STATUS LIKE "Threads_connected"')
				result = cursor.fetchone()

			except MySQLdb.OperationalError, message:

				self.mainLogger.error('getMySQLStatus: MySQL query error when getting Threads_connected = %s', message)

			threadsConnected = result[1]

			self.mainLogger.debug('getMySQLStatus: threadsConnected = %s', threadsConnected)

			self.mainLogger.debug('getMySQLStatus: getting Threads_connected - done')

			self.mainLogger.debug('getMySQLStatus: getting Seconds_Behind_Master')

			if 'MySQLNoRepl' not in self.agentConfig:
				# Seconds_Behind_Master
				try:
					cursor = db.cursor(MySQLdb.cursors.DictCursor)
					cursor.execute('SHOW SLAVE STATUS')
					result = cursor.fetchone()

				except MySQLdb.OperationalError, message:

					self.mainLogger.error('getMySQLStatus: MySQL query error when getting SHOW SLAVE STATUS = %s', message)
					result = None

				if result != None:
					try:
						# Handle the case when Seconds_Behind_Master is NULL
						if result['Seconds_Behind_Master'] is None:
							secondsBehindMaster = -1
						else:
							secondsBehindMaster = result['Seconds_Behind_Master']

						self.mainLogger.debug('getMySQLStatus: secondsBehindMaster = %s', secondsBehindMaster)

					except IndexError, e:
						secondsBehindMaster = None

						self.mainLogger.debug('getMySQLStatus: secondsBehindMaster empty. %s', e)

				else:
					secondsBehindMaster = None

					self.mainLogger.debug('getMySQLStatus: secondsBehindMaster empty. Result = None.')

				self.mainLogger.debug('getMySQLStatus: getting Seconds_Behind_Master - done')

			return {'connections' : connections, 'createdTmpDiskTables' : createdTmpDiskTables, 'maxUsedConnections' : maxUsedConnections, 'openFiles' : openFiles, 'slowQueries' : slowQueries, 'tableLocksWaited' : tableLocksWaited, 'threadsConnected' : threadsConnected, 'secondsBehindMaster' : secondsBehindMaster}

		else:

			self.mainLogger.debug('getMySQLStatus: config not set')
			return False

	def getNetworkTraffic(self):
		self.mainLogger.debug('getNetworkTraffic: start')

		if sys.platform == 'linux2':
			self.mainLogger.debug('getNetworkTraffic: linux2')

			try:
				self.mainLogger.debug('getNetworkTraffic: attempting open')

				proc = open('/proc/net/dev', 'r')
				lines = proc.readlines()

				proc.close()

			except IOError, e:
				self.mainLogger.error('getNetworkTraffic: exception = %s', e)
				return False

			self.mainLogger.debug('getNetworkTraffic: open success, parsing')

			columnLine = lines[1]
			_, receiveCols , transmitCols = columnLine.split('|')
			receiveCols = map(lambda a:'recv_' + a, receiveCols.split())
			transmitCols = map(lambda a:'trans_' + a, transmitCols.split())

			cols = receiveCols + transmitCols

			self.mainLogger.debug('getNetworkTraffic: parsing, looping')

			faces = {}
			for line in lines[2:]:
				if line.find(':') < 0: continue
				face, data = line.split(':')
				faceData = dict(zip(cols, data.split()))
				faces[face] = faceData

			self.mainLogger.debug('getNetworkTraffic: parsed, looping')

			interfaces = {}

			# Now loop through each interface
			for face in faces:
				key = face.strip()

				# We need to work out the traffic since the last check so first time we store the current value
				# then the next time we can calculate the difference
				try:
					if key in self.networkTrafficStore:
						interfaces[key] = {}
						interfaces[key]['recv_bytes'] = long(faces[face]['recv_bytes']) - long(self.networkTrafficStore[key]['recv_bytes'])
						interfaces[key]['trans_bytes'] = long(faces[face]['trans_bytes']) - long(self.networkTrafficStore[key]['trans_bytes'])

						if interfaces[key]['recv_bytes'] < 0:
							interfaces[key]['recv_bytes'] = long(faces[face]['recv_bytes'])

						if interfaces[key]['trans_bytes'] < 0:
							interfaces[key]['trans_bytes'] = long(faces[face]['trans_bytes'])

						interfaces[key]['recv_bytes'] = str(interfaces[key]['recv_bytes'])
						interfaces[key]['trans_bytes'] = str(interfaces[key]['trans_bytes'])

						# And update the stored value to subtract next time round
						self.networkTrafficStore[key]['recv_bytes'] = faces[face]['recv_bytes']
						self.networkTrafficStore[key]['trans_bytes'] = faces[face]['trans_bytes']

					else:
						self.networkTrafficStore[key] = {}
						self.networkTrafficStore[key]['recv_bytes'] = faces[face]['recv_bytes']
						self.networkTrafficStore[key]['trans_bytes'] = faces[face]['trans_bytes']

					# Logging
					self.mainLogger.debug('getNetworkTraffic: %s = %s', key, self.networkTrafficStore[key]['recv_bytes'])
					self.mainLogger.debug('getNetworkTraffic: %s = %s', key, self.networkTrafficStore[key]['trans_bytes'])

				except KeyError, ex:
					self.mainLogger.error('getNetworkTraffic: no data for %s', key)

				except ValueError, ex:
					self.mainLogger.error('getNetworkTraffic: invalid data for %s', key)

			self.mainLogger.debug('getNetworkTraffic: completed, returning')

			return interfaces

		elif sys.platform.find('freebsd') != -1 or sys.platform.find('darwin') != -1:
			self.mainLogger.debug('getNetworkTraffic: freebsd/OSX')

			try:
				try:
					self.mainLogger.debug('getNetworkTraffic: attempting Popen (netstat)')

					proc = subprocess.Popen(['netstat', '-nbid'], stdout=subprocess.PIPE, close_fds=True)
					netstat = proc.communicate()[0]

					if int(pythonVersion[1]) >= 6:
						try:
							proc.kill()
						except Exception, e:
							self.mainLogger.debug('Process already terminated')

				except Exception, e:
					import traceback
					self.mainLogger.error('getNetworkTraffic: exception = %s', traceback.format_exc())

					return False
			finally:
				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

			self.mainLogger.debug('getNetworkTraffic: open success, parsing')

			lines = netstat.split('\n')

			# Loop over available data for each inteface
			faces = {}
			rxKey = None
			txKey = None

			for line in lines:
				self.mainLogger.debug('getNetworkTraffic: %s', line)

				line = re.split(r'\s+', line)

				# Figure out which index we need
				if rxKey == None and txKey == None:
					for k, part in enumerate(line):
						self.mainLogger.debug('getNetworkTraffic: looping parts (%s)', part)

						if part == 'Ibytes':
							rxKey = k
							self.mainLogger.debug('getNetworkTraffic: found rxKey = %s', k)
						elif part == 'Obytes':
							txKey = k
							self.mainLogger.debug('getNetworkTraffic: found txKey = %s', k)

				else:
					if line[0] not in faces:
						try:
							self.mainLogger.debug('getNetworkTraffic: parsing (rx: %s = %s / tx: %s = %s)', rxKey, line[rxKey], txKey, line[txKey])
							faceData = {'recv_bytes': line[rxKey], 'trans_bytes': line[txKey]}

							face = line[0]
							faces[face] = faceData
						except IndexError, e:
							continue

			self.mainLogger.debug('getNetworkTraffic: parsed, looping')

			interfaces = {}

			# Now loop through each interface
			for face in faces:
				key = face.strip()

				try:
					# We need to work out the traffic since the last check so first time we store the current value
					# then the next time we can calculate the difference
					if key in self.networkTrafficStore:
						interfaces[key] = {}
						interfaces[key]['recv_bytes'] = long(faces[face]['recv_bytes']) - long(self.networkTrafficStore[key]['recv_bytes'])
						interfaces[key]['trans_bytes'] = long(faces[face]['trans_bytes']) - long(self.networkTrafficStore[key]['trans_bytes'])

						interfaces[key]['recv_bytes'] = str(interfaces[key]['recv_bytes'])
						interfaces[key]['trans_bytes'] = str(interfaces[key]['trans_bytes'])

						if interfaces[key]['recv_bytes'] < 0:
							interfaces[key]['recv_bytes'] = long(faces[face]['recv_bytes'])

						if interfaces[key]['trans_bytes'] < 0:
							interfaces[key]['trans_bytes'] = long(faces[face]['trans_bytes'])

						# And update the stored value to subtract next time round
						self.networkTrafficStore[key]['recv_bytes'] = faces[face]['recv_bytes']
						self.networkTrafficStore[key]['trans_bytes'] = faces[face]['trans_bytes']

					else:
						self.networkTrafficStore[key] = {}
						self.networkTrafficStore[key]['recv_bytes'] = faces[face]['recv_bytes']
						self.networkTrafficStore[key]['trans_bytes'] = faces[face]['trans_bytes']

				except KeyError, ex:
					self.mainLogger.error('getNetworkTraffic: no data for %s', key)

				except ValueError, ex:
					self.mainLogger.error('getNetworkTraffic: invalid data for %s', key)

			self.mainLogger.debug('getNetworkTraffic: completed, returning')

			return interfaces

		else:
			self.mainLogger.debug('getNetworkTraffic: other platform, returning')

			return False

	def getNginxStatus(self):
		self.mainLogger.debug('getNginxStatus: start')

		if 'nginxStatusUrl' in self.agentConfig and self.agentConfig['nginxStatusUrl'] != 'http://www.example.com/nginx_status':	# Don't do it if the status URL hasn't been provided
			self.mainLogger.debug('getNginxStatus: config set')

			try:
				self.mainLogger.debug('getNginxStatus: attempting urlopen')

				req = urllib2.Request(self.agentConfig['nginxStatusUrl'], None, headers)

				# Do the request, log any errors
				request = urllib2.urlopen(req)
				response = request.read()

			except urllib2.HTTPError, e:
				self.mainLogger.error('Unable to get Nginx status - HTTPError = %s', e)
				return False

			except urllib2.URLError, e:
				self.mainLogger.error('Unable to get Nginx status - URLError = %s', e)
				return False

			except httplib.HTTPException, e:
				self.mainLogger.error('Unable to get Nginx status - HTTPException = %s', e)
				return False

			except Exception, e:
				import traceback
				self.mainLogger.error('Unable to get Nginx status - Exception = %s', traceback.format_exc())
				return False

			self.mainLogger.debug('getNginxStatus: urlopen success, start parsing')

			# Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code

			self.mainLogger.debug('getNginxStatus: parsing connections')

			try:
				# Connections
				parsed = re.search(r'Active connections:\s+(\d+)', response)
				connections = int(parsed.group(1))

				self.mainLogger.debug('getNginxStatus: parsed connections')
				self.mainLogger.debug('getNginxStatus: parsing reqs')

				# Requests per second
				parsed = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', response)

				if not parsed:
					self.mainLogger.debug('getNginxStatus: could not parse response')
					return False

				requests = int(parsed.group(3))

				self.mainLogger.debug('getNginxStatus: parsed reqs')

				if self.nginxRequestsStore == None or self.nginxRequestsStore < 0:

					self.mainLogger.debug('getNginxStatus: no reqs so storing for first time')

					self.nginxRequestsStore = requests

					requestsPerSecond = 0

				else:

					self.mainLogger.debug('getNginxStatus: reqs stored so calculating')
					self.mainLogger.debug('getNginxStatus: self.nginxRequestsStore = %s', self.nginxRequestsStore)
					self.mainLogger.debug('getNginxStatus: requests = %s', requests)

					requestsPerSecond = float(requests - self.nginxRequestsStore) / 60

					self.mainLogger.debug('getNginxStatus: requestsPerSecond = %s', requestsPerSecond)

					self.nginxRequestsStore = requests

				if connections != None and requestsPerSecond != None:

					self.mainLogger.debug('getNginxStatus: returning with data')

					return {'connections' : connections, 'reqPerSec' : requestsPerSecond}

				else:

					self.mainLogger.debug('getNginxStatus: returning without data')

					return False

			except Exception, e:
				import traceback
				self.mainLogger.error('Unable to get Nginx status - %s - Exception = %s', response, traceback.format_exc())
				return False

		else:
			self.mainLogger.debug('getNginxStatus: config not set')

			return False

	def getProcesses(self):
		self.mainLogger.debug('getProcesses: start')

		# Get output from ps
		try:
			try:
				self.mainLogger.debug('getProcesses: attempting Popen')

				proc = subprocess.Popen(['ps', 'auxww'], stdout=subprocess.PIPE, close_fds=True)
				ps = proc.communicate()[0]

				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

				self.mainLogger.debug('getProcesses: ps result = %s', ps)

			except Exception, e:
				import traceback
				self.mainLogger.error('getProcesses: exception = %s', traceback.format_exc())
				return False
		finally:
			if int(pythonVersion[1]) >= 6:
				try:
					proc.kill()
				except Exception, e:
					self.mainLogger.debug('Process already terminated')

		self.mainLogger.debug('getProcesses: Popen success, parsing')

		try:

			# Split out each process
			processLines = ps.split('\n')

			del processLines[0] # Removes the headers
			processLines.pop() # Removes a trailing empty line

			processes = []

			self.mainLogger.debug('getProcesses: Popen success, parsing, looping')

			for line in processLines:
				self.mainLogger.debug('getProcesses: Popen success, parsing, loop...')
				line = line.replace("'", '') # These will break JSON. ZD38282
				line = line.replace('"', '')
				line = line.replace('\\', '\\\\')
				line = line.split(None, 10)
				processes.append(line)

			self.mainLogger.debug('getProcesses: completed, returning')

			return processes

		except Exception, e:
			import traceback
			self.mainLogger.error('getProcesses: exception = %s', traceback.format_exc())
			return False

	def getRabbitMQStatus(self):

		if not self.agentConfig.get('rabbitMQStatusUrl') or \
                    not self.agentConfig.get('rabbitMQUser') or \
                    not self.agentConfig.get('rabbitMQPass') or \
                    self.agentConfig['rabbitMQStatusUrl'] == 'http://www.example.com:55672/api/overview' or \
                    self.agentConfig['rabbitMQStatusUrl'] == 'http://www.example.com:55672/json':

			self.mainLogger.debug('getRabbitMQStatus: config not set')
			return False

		self.mainLogger.debug('getRabbitMQStatus: start')
		self.mainLogger.debug('getRabbitMQStatus: attempting authentication setup')

		try:
			import base64
			credentials = base64.encodestring('%s:%s' % (self.agentConfig['rabbitMQUser'], self.agentConfig['rabbitMQPass'])).replace('\n', '')
		except Exception, e:
			self.mainLogger.error('Unable to generate base64 encoding for with username and password - Error = %s', e)
			return False

		# make sure we only append for the rabbit checks
		rabbitMQHeaders = headers = {
								'User-Agent': 'Server Density Agent',
								'Content-Type': 'application/x-www-form-urlencoded',
								'Accept': 'text/html, */*',
							}
		rabbitMQHeaders["Authorization"] = "Basic %s" % (credentials,)


		self.mainLogger.debug('getRabbitMQStatus: config set')

		try:
			self.mainLogger.debug('getRabbitMQStatus: attempting urlopen')
			req = urllib2.Request(self.agentConfig['rabbitMQStatusUrl'], None, rabbitMQHeaders)

			# Do the request, log any errors
			request = urllib2.urlopen(req)
			response = request.read()

		except urllib2.HTTPError, e:
			self.mainLogger.error('Unable to get RabbitMQ status - HTTPError = %s', e)
			return False

		except urllib2.URLError, e:
			self.mainLogger.error('Unable to get RabbitMQ status - URLError = %s', e)
			return False

		except httplib.HTTPException, e:
			self.mainLogger.error('Unable to get RabbitMQ status - HTTPException = %s', e)
			return False

		except Exception, e:
			import traceback
			self.mainLogger.error('Unable to get RabbitMQ status - Exception = %s', traceback.format_exc())
			return False

		try:
			if int(pythonVersion[1]) >= 6:
				self.mainLogger.debug('getRabbitMQStatus: json read')
				status = json.loads(response)

			else:
				self.mainLogger.debug('getRabbitMQStatus: minjson read')
				status = minjson.safeRead(response)

			self.mainLogger.debug(status)

			if 'connections' not in status:
				# We are probably using the newer RabbitMQ > 2.x status plugin, so try to parse that instead.
				status = {}
				connections = {}
				queues = {}
				self.mainLogger.debug('getRabbitMQStatus: using > 2.x management plugin data')
				import urlparse

				split_url = urlparse.urlsplit(self.agentConfig['rabbitMQStatusUrl'])

				# Connections
				url = split_url[0] + '://' + split_url[1] + '/api/connections'
				self.mainLogger.debug('getRabbitMQStatus: attempting urlopen on %s', url)

				req = urllib2.Request(url, None, rabbitMQHeaders)

				# Do the request, log any errors
				request = urllib2.urlopen(req)
				response = request.read()

				if int(pythonVersion[1]) >= 6:
					self.mainLogger.debug('getRabbitMQStatus: connections json read')
					connections = json.loads(response)
				else:
					self.mainLogger.debug('getRabbitMQStatus: connections minjson read')
					connections = minjson.safeRead(response)

				status['connections'] = len(connections)
				self.mainLogger.debug('getRabbitMQStatus: connections = %s', status['connections'])

				# Queues
				url = split_url[0] + '://' + split_url[1] + '/api/queues'
				self.mainLogger.debug('getRabbitMQStatus: attempting urlopen on %s', url)
				req = urllib2.Request(url, None, rabbitMQHeaders)
				# Do the request, log any errors
				request = urllib2.urlopen(req)
				response = request.read()

				if int(pythonVersion[1]) >= 6:
					self.mainLogger.debug('getRabbitMQStatus: queues json read')
					queues = json.loads(response)
				else:
					self.mainLogger.debug('getRabbitMQStatus: queues minjson read')
					queues = minjson.safeRead(response)

				status['queues'] = queues
				self.mainLogger.debug(status['queues'])

		except Exception, e:
			import traceback
			self.mainLogger.error('Unable to load RabbitMQ status JSON - Exception = %s', traceback.format_exc())
			return False

		self.mainLogger.debug('getRabbitMQStatus: completed, returning')

		# Fix for queues with the same name (case 32788)
		for queue in status.get('queues', []):
			vhost = queue.get('vhost', '/')
			if vhost == '/':
				continue

			queue['name'] = '%s/%s' % (vhost, queue['name'])

		return status

	#
	# Plugins
	#

	def getPlugins(self):
		self.mainLogger.debug('getPlugins: start')

		if 'pluginDirectory' in self.agentConfig and self.agentConfig['pluginDirectory'] != '':

			self.mainLogger.info('getPlugins: pluginDirectory %s', self.agentConfig['pluginDirectory'])

			if os.access(self.agentConfig['pluginDirectory'], os.R_OK) == False:
				self.mainLogger.warning('getPlugins: Plugin path %s is set but not readable by agent. Skipping plugins.', self.agentConfig['pluginDirectory'])

				return False

		else:
			self.mainLogger.debug('getPlugins: pluginDirectory not set')

			return False

		# Have we already imported the plugins?
		# Only load the plugins once
		if self.plugins == None:
			self.mainLogger.debug('getPlugins: initial load from %s', self.agentConfig['pluginDirectory'])

			sys.path.append(self.agentConfig['pluginDirectory'])

			self.plugins = []
			plugins = []

			# Loop through all the plugin files
			for root, dirs, files in os.walk(self.agentConfig['pluginDirectory']):
				for name in files:
					self.mainLogger.debug('getPlugins: considering: %s', name)

					name = name.split('.', 1)

					# Only pull in .py files (ignores others, inc .pyc files)
					try:
						if name[1] == 'py':

							self.mainLogger.debug('getPlugins: ' + name[0] + '.' + name[1] + ' is a plugin')

							plugins.append(name[0])

					except IndexError, e:

						continue

			# Loop through all the found plugins, import them then create new objects
			for pluginName in plugins:
				self.mainLogger.debug('getPlugins: loading %s', pluginName)

				pluginPath = os.path.join(self.agentConfig['pluginDirectory'], '%s.py' % pluginName)

				if os.access(pluginPath, os.R_OK) == False:
					self.mainLogger.error('getPlugins: Unable to read %s so skipping this plugin.', pluginPath)
					continue

				try:
					# Import the plugin, but only from the pluginDirectory (ensures no conflicts with other module names elsehwhere in the sys.path
					import imp
					importedPlugin = imp.load_source(pluginName, pluginPath)

					self.mainLogger.debug('getPlugins: imported %s', pluginName)

					# Find out the class name and then instantiate it
					pluginClass = getattr(importedPlugin, pluginName)

					try:
						pluginObj = pluginClass(self.agentConfig, self.mainLogger, self.rawConfig)

					except TypeError:

						try:
							pluginObj = pluginClass(self.agentConfig, self.mainLogger)
						except TypeError:
							# Support older plugins.
							pluginObj = pluginClass()

					self.mainLogger.debug('getPlugins: instantiated %s', pluginName)

					# Store in class var so we can execute it again on the next cycle
					self.plugins.append(pluginObj)

				except Exception, ex:
					import traceback
					self.mainLogger.error('getPlugins (%s): exception = %s', pluginName, traceback.format_exc())

		# Now execute the objects previously created
		if self.plugins != None:
			self.mainLogger.debug('getPlugins: executing plugins')

			# Execute the plugins
			output = {}

			for plugin in self.plugins:
				self.mainLogger.info('getPlugins: executing  %s', plugin.__class__.__name__)

				try:
					output[plugin.__class__.__name__] = plugin.run()

				except Exception, ex:
					import traceback
					self.mainLogger.error('getPlugins: exception = %s', traceback.format_exc())

				self.mainLogger.debug('getPlugins: %s output: %s', plugin.__class__.__name__, output[plugin.__class__.__name__])
				self.mainLogger.info('getPlugins: executed %s', plugin.__class__.__name__)

			self.mainLogger.debug('getPlugins: returning')

			# Each plugin should output a dictionary so we can convert it to JSON later
			return output

		else:
			self.mainLogger.debug('getPlugins: no plugins, returning false')

			return False

	#
	# Postback
	#

	def doTraceroute(self):

		if self.agentConfig['logging'] != logging.DEBUG:
			return False

		self.mainLogger.debug('doTraceroute: start')

		try:
			try:
				import socket
				s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				s.connect(("serverdensity.com", 80))
				ip = s.getsockname()[0]
				s.close()

				sdUrl = string.replace(self.agentConfig['sdUrl'], 'https://', '')
				sdUrl = string.replace(sdUrl, 'http://', '')

				self.mainLogger.debug('doTraceroute: attempting mtr from %s to %s', ip, sdUrl)

				proc = subprocess.Popen(['mtr', '-c 100', '-r', '-n', sdUrl], stdout=subprocess.PIPE, close_fds=True)
				mtr = proc.communicate()[0]

				if int(pythonVersion[1]) >= 6:
					try:
						proc.kill()
					except Exception, e:
						self.mainLogger.debug('Process already terminated')

			except Exception, e:
				import traceback
				self.mainLogger.error('doTraceroute: exception = %s', traceback.format_exc())

				return False
		finally:
			if int(pythonVersion[1]) >= 6:
				try:
					proc.kill()
				except Exception, e:
					self.mainLogger.debug('Process already terminated')

		self.mainLogger.debug('doTraceroute: success, parsing')

		self.mainLogger.debug('doTraceroute: %s', mtr)

	def doPostBack(self, postBackData, retry=False):
		self.mainLogger.debug('doPostBack: start')

		try:

			try:
				self.mainLogger.info('doPostBack: attempting postback: %s', self.agentConfig['sdUrl'])

				# Build the request handler
				request = urllib2.Request(self.agentConfig['sdUrl'] + '/postback/', postBackData, headers)

				# Do the request, log any errors
				response = urllib2.urlopen(request)

				self.mainLogger.info('Postback response: %s', response.read())

			except urllib2.HTTPError, e:
				self.mainLogger.error('doPostBack: HTTPError = %s', e)

				self.doTraceroute()

				return False

			except urllib2.URLError, e:
				self.mainLogger.error('doPostBack: URLError = %s', e)

				# attempt a lookup, in case of DNS fail
				# https://github.com/serverdensity/sd-agent/issues/47
				if not retry:

					timeout = socket.getdefaulttimeout()
					socket.setdefaulttimeout(5)

					self.mainLogger.info('doPostBack: Retrying postback with DNS lookup iteration')
					try:
						[socket.gethostbyname(self.agentConfig['sdUrl']) for x in xrange(0,2)]
					except:
						# this can raise, if the dns lookup doesn't work
						pass
					socket.setdefaulttimeout(timeout)

					self.mainLogger.info("doPostBack: Executing retry")
					return self.doPostBack(postBackData, retry=True)
				else:
					# if we get here, the retry has failed, so we need to reschedule
					self.mainLogger.info("doPostBack: Retry failed, rescheduling")

					self.doTraceroute()

					return False
				return False

			except httplib.HTTPException, e: # Added for case #26701
				self.mainLogger.error('doPostBack: HTTPException = %s', e)

				self.doTraceroute()

				return False

			except Exception, e:
				import traceback
				self.mainLogger.error('doPostBack: Exception = %s', traceback.format_exc())

				self.doTraceroute()

				return False

		finally:
			if int(pythonVersion[1]) >= 6:
				try:
					if 'response' in locals():
						response.close()
				except Exception, e:
					import traceback
					self.mainLogger.error('doPostBack: Exception = %s', traceback.format_exc())
					return False

			self.mainLogger.debug('doPostBack: completed')

	def doChecks(self, sc, firstRun, systemStats=False):
		macV = None
		if sys.platform == 'darwin':
			macV = platform.mac_ver()

		if not self.topIndex: # We cache the line index from which to read from top
			# Output from top is slightly modified on OS X 10.6+ (case #28239)
			if macV and [int(v) for v in macV[0].split('.')] >= [10, 6, 0]:
				self.topIndex = 6
			else:
				self.topIndex = 5

		if not self.os:
			if macV:
				self.os = 'mac'
			elif sys.platform.find('freebsd') != -1:
				self.os = 'freebsd'
			else:
				self.os = 'linux'

		# We only need to set this if we're on FreeBSD
		if self.linuxProcFsLocation == None and self.os == 'freebsd':
			self.linuxProcFsLocation = self.getMountedLinuxProcFsLocation()
		else:
			self.linuxProcFsLocation = '/proc'

		self.mainLogger.debug('doChecks: start')

		# Do the checks
		apacheStatus = self.getApacheStatus()
		diskUsage = self.getDiskUsage()
		loadAvrgs = self.getLoadAvrgs()
		memory = self.getMemoryUsage()
		mysqlStatus = self.getMySQLStatus()
		networkTraffic = self.getNetworkTraffic()
		nginxStatus = self.getNginxStatus()
		processes = self.getProcesses()
		rabbitmq = self.getRabbitMQStatus()
		mongodb = self.getMongoDBStatus()
		couchdb = self.getCouchDBStatus()
		plugins = self.getPlugins()
		ioStats = self.getIOStats();
		cpuStats = self.getCPUStats();

		# Fetch disk info
		diskMetaData = self.getDiskMetaData();

		if processes is not False and len(processes) > 4194304:
			self.mainLogger.warn('doChecks: process list larger than 4MB limit, so it has been stripped')

			processes = []

		self.mainLogger.debug('doChecks: checks success, build payload')

		self.mainLogger.info('doChecks: agent key = %s', self.agentConfig['agentKey'])

		checksData = {}

		# Basic payload items
		checksData['os'] = self.os
		checksData['agentKey'] = self.agentConfig['agentKey']
		checksData['agentVersion'] = self.agentConfig['version']

		if diskMetaData:

			if not 'meta' in checksData.keys():
				checksData['meta'] = {}
			checksData['meta']['volumes'] = diskMetaData

		if diskUsage != False:

			checksData['diskUsage'] = diskUsage

		if loadAvrgs != False:

			checksData['loadAvrg'] = loadAvrgs['1']

		if memory != False:

			checksData['memPhysUsed'] = memory['physUsed']
			checksData['memPhysFree'] = memory['physFree']
			checksData['memSwapUsed'] = memory['swapUsed']
			checksData['memSwapFree'] = memory['swapFree']
			checksData['memCached'] = memory['cached']

		if networkTraffic != False:

			checksData['networkTraffic'] = networkTraffic

		if processes != False:

			checksData['processes'] = processes

		# Apache Status
		if apacheStatus != False:

			if 'reqPerSec' in apacheStatus:
				checksData['apacheReqPerSec'] = apacheStatus['reqPerSec']

			if 'busyWorkers' in apacheStatus:
				checksData['apacheBusyWorkers'] = apacheStatus['busyWorkers']

			if 'idleWorkers' in apacheStatus:
				checksData['apacheIdleWorkers'] = apacheStatus['idleWorkers']

			self.mainLogger.debug('doChecks: built optional payload apacheStatus')

		# MySQL Status
		if mysqlStatus != False:

			checksData['mysqlConnections'] = mysqlStatus['connections']
			checksData['mysqlCreatedTmpDiskTables'] = mysqlStatus['createdTmpDiskTables']
			checksData['mysqlMaxUsedConnections'] = mysqlStatus['maxUsedConnections']
			checksData['mysqlOpenFiles'] = mysqlStatus['openFiles']
			checksData['mysqlSlowQueries'] = mysqlStatus['slowQueries']
			checksData['mysqlTableLocksWaited'] = mysqlStatus['tableLocksWaited']
			checksData['mysqlThreadsConnected'] = mysqlStatus['threadsConnected']

			if mysqlStatus['secondsBehindMaster'] != None:
				checksData['mysqlSecondsBehindMaster'] = mysqlStatus['secondsBehindMaster']

		# Nginx Status
		if nginxStatus != False:
			checksData['nginxConnections'] = nginxStatus['connections']
			checksData['nginxReqPerSec'] = nginxStatus['reqPerSec']

		# RabbitMQ
		if rabbitmq != False:
			checksData['rabbitMQ'] = rabbitmq

		# MongoDB
		if mongodb != False:
			checksData['mongoDB'] = mongodb

		# CouchDB
		if couchdb != False:
			checksData['couchDB'] = couchdb

		# Plugins
		if plugins != False:
			checksData['plugins'] = plugins

		if ioStats != False:
			checksData['ioStats'] = ioStats

		if cpuStats != False:
			checksData['cpuStats'] = cpuStats

		# Include system stats on first postback
		if firstRun == True:
			checksData['systemStats'] = systemStats
			self.mainLogger.debug('doChecks: built optional payload systemStats')

		# Include server indentifiers
		import socket

		try:
			checksData['internalHostname'] = socket.gethostname()
			self.mainLogger.info('doChecks: hostname = %s', checksData['internalHostname'])

		except socket.error, e:
			self.mainLogger.debug('Unable to get hostname: %s', e)

		self.mainLogger.debug('doChecks: payload: %s' % checksData)
		self.mainLogger.debug('doChecks: payloads built, convert to json')

		# Post back the data
		if int(pythonVersion[1]) >= 6:
			self.mainLogger.debug('doChecks: json convert')

			try:
				payload = json.dumps(checksData, encoding='latin1').encode('utf-8')

			except Exception, e:
				import traceback
				self.mainLogger.error('doChecks: failed encoding payload to json. Exception = %s', traceback.format_exc())
				return False

		else:
			self.mainLogger.debug('doChecks: minjson convert')

			payload = minjson.write(checksData)

		self.mainLogger.debug('doChecks: json converted, hash')

		payloadHash = md5(payload).hexdigest()
		postBackData = urllib.urlencode({'payload' : payload, 'hash' : payloadHash})

		self.mainLogger.debug('doChecks: hashed, doPostBack')

		self.doPostBack(postBackData)

		self.mainLogger.debug('doChecks: posted back, reschedule')

		sc.enter(self.agentConfig['checkFreq'], 1, self.doChecks, (sc, False))

	def getMountedLinuxProcFsLocation(self):
		self.mainLogger.debug('getMountedLinuxProcFsLocation: attempting to fetch mounted partitions')

		# Lets check if the Linux like style procfs is mounted
		try:
			proc = subprocess.Popen(['mount'], stdout = subprocess.PIPE, close_fds = True)
			mountedPartitions = proc.communicate()[0]

			if int(pythonVersion[1]) >= 6:
				try:
					proc.kill()
				except Exception, e:
					self.mainLogger.debug('Process already terminated')

			location = re.search(r'linprocfs on (.*?) \(.*?\)', mountedPartitions)

		except OSError, e:
			self.mainLogger.error('getMountedLinuxProcFsLocation: OS error: %s', e)

		# Linux like procfs file system is not mounted so we return False, else we return mount point location
		if location == None:
			self.mainLogger.debug('getMountedLinuxProcFsLocation: none found so using /proc')
			return '/proc' # Can't find anything so we might as well try this

		location = location.group(1)

		self.mainLogger.debug('getMountedLinuxProcFsLocation: using %s', location)

		return location

########NEW FILE########
__FILENAME__ = daemon
'''
	***
	Modified generic daemon class
	***
	
	Author: 	http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
				www.boxedice.com
	
	License: 	http://creativecommons.org/licenses/by-sa/3.0/
	
	Changes:	23rd Jan 2009 (David Mytton <david@boxedice.com>)
				- Replaced hard coded '/dev/null in __init__ with os.devnull
				- Added OS check to conditionally remove code that doesn't work on OS X
				- Added output to console on completion
				- Tidied up formatting 
				11th Mar 2009 (David Mytton <david@boxedice.com>)
				- Fixed problem with daemon exiting on Python 2.4 (before SystemExit was part of the Exception base)
				13th Aug 2010 (David Mytton <david@boxedice.com>
				- Fixed unhandled exception if PID file is empty
'''

# Core modules
import atexit
import os
import sys
import time

from signal import SIGTERM 

class Daemon:
	"""
	A generic daemon class.
	
	Usage: subclass the Daemon class and override the run() method
	"""
	def __init__(self, pidfile, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull):
		self.stdin = stdin
		self.stdout = stdout
		self.stderr = stderr
		self.pidfile = pidfile
	
	def daemonize(self):
		"""
		Do the UNIX double-fork magic, see Stevens' "Advanced 
		Programming in the UNIX Environment" for details (ISBN 0201563177)
		http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
		"""
		try: 
			pid = os.fork() 
			if pid > 0:
				# Exit first parent
				sys.exit(0) 
		except OSError, e: 
			sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
			sys.exit(1)
		
		# Decouple from parent environment
		os.chdir("/") 
		os.setsid() 
		os.umask(0) 
	
		# Do second fork
		try: 
			pid = os.fork() 
			if pid > 0:
				# Exit from second parent
				sys.exit(0) 
		except OSError, e: 
			sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
			sys.exit(1) 
	
		if sys.platform != 'darwin': # This block breaks on OS X
			# Redirect standard file descriptors
			sys.stdout.flush()
			sys.stderr.flush()
			si = file(self.stdin, 'r')
			so = file(self.stdout, 'a+')
			se = file(self.stderr, 'a+', 0)
			os.dup2(si.fileno(), sys.stdin.fileno())
			os.dup2(so.fileno(), sys.stdout.fileno())
			os.dup2(se.fileno(), sys.stderr.fileno())
		
		print "Started"
		
		# Write pidfile
		atexit.register(self.delpid) # Make sure pid file is removed if we quit
		pid = str(os.getpid())
		file(self.pidfile,'w+').write("%s\n" % pid)
		
	def delpid(self):
		os.remove(self.pidfile)

	def start(self):
		"""
		Start the daemon
		"""
		
		print "Starting..."
		
		# Check for a pidfile to see if the daemon already runs
		try:
			pf = file(self.pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None
		except SystemExit:
			pid = None
	
		if pid:
			message = "pidfile %s already exists. Is it already running?\n"
			sys.stderr.write(message % self.pidfile)
			sys.exit(1)

		# Start the daemon
		self.daemonize()		
		self.run()

	def stop(self):
		"""
		Stop the daemon
		"""
		
		print "Stopping..."
		
		# Get the pid from the pidfile
		try:
			pf = file(self.pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None
		except ValueError:
			pid = None
	
		if not pid:
			message = "pidfile %s does not exist. Not running?\n"
			sys.stderr.write(message % self.pidfile)
			
			# Just to be sure. A ValueError might occur if the PID file is empty but does actually exist
			if os.path.exists(self.pidfile):
				os.remove(self.pidfile)
			
			return # Not an error in a restart

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
		
		print "Stopped"

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
__FILENAME__ = minjson
##############################################################################
##
##    minjson.py implements JSON reading and writing in python.
##    Copyright (c) 2005 Jim Washington and Contributors.
##
##    This library is free software; you can redistribute it and/or
##    modify it under the terms of the GNU Lesser General Public
##    License as published by the Free Software Foundation; either
##    version 2.1 of the License, or (at your option) any later version.
##
##    This library is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
##    Lesser General Public License for more details.=
##
##    You should have received a copy of the GNU Lesser General Public
##    License along with this library; if not, write to the Free Software
##    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
##
##############################################################################


# minjson.py
# use python's parser to read minimal javascript objects.
# str's objects and fixes the text to write javascript.

# Thanks to Patrick Logan for starting the json-py project and making so many
# good test cases.

# Jim Washington 7 Aug 2005.

from re import compile, sub, search, DOTALL

# set to true if transmission size is much more important than speed
# only affects writing, and makes a minimal difference in output size.
alwaysStripWhiteSpace = False

# add to this string if you wish to exclude additional math operators
# from reading.
badOperators = '*'

#################################
#      read JSON object         #
#################################

slashstarcomment = compile(r'/\*.*?\*/',DOTALL)
doubleslashcomment = compile(r'//.*\n')

def _Read(aString):
        """Use eval in a 'safe' way to turn javascript expression into
           a python expression.  Allow only True, False, and None in global
           __builtins__, and since those map as true, false, null in
           javascript, pass those as locals
        """
        try:
            result = eval(aString,
            {"__builtins__":{'True':True,'False':False,'None':None}},
            {'null':None,'true':True,'false':False})
        except NameError:
            raise ReadException, \
            "Strings must be quoted. Could not read '%s'." % aString
        except SyntaxError:
            raise ReadException, \
            "Syntax error.  Could not read '%s'." % aString
        return result

# badOperators is defined at the top of the module

# generate the regexes for math detection
regexes = {}
for operator in badOperators:
    if operator in '+*':
        # '+' and '*' need to be escaped with \ in re
        regexes[operator,'numeric operation'] \
        = compile(r"\d*\s*\%s|\%s\s*\d*" % (operator, operator))
    else:
        regexes[operator,'numeric operation'] \
        = compile(r"\d*\s*%s|%s\s*\d*" % (operator, operator))

def _getStringState(aSequence):
    """return the list of required quote closures if the end of aString needs them
    to close quotes.
    """
    state = []
    for k in aSequence:
        if k in ['"',"'"]:
            if state and k == state[-1]:
                state.pop()
            else:
                state.append(k)
    return state

def _sanityCheckMath(aString):
    """just need to check that, if there is a math operator in the
       client's JSON, it is inside a quoted string. This is mainly to
       keep client from successfully sending 'D0S'*9**9**9**9...
       Return True if OK, False otherwise
    """
    for operator in badOperators:
        #first check, is it a possible math operation?
        if regexes[(operator,'numeric operation')].search(aString) is not None:
            # OK.  possible math operation. get the operator's locations
            getlocs = regexes[(operator,'numeric operation')].finditer(aString)
            locs = [item.span() for item in getlocs]
            halfStrLen = len(aString) / 2
            #fortunately, this should be rare
            for loc in locs:
                exprStart = loc[0]
                exprEnd = loc[1]
                # We only need to know the char is within open quote
                # status.
                if exprStart <= halfStrLen:
                    teststr = aString[:exprStart]
                else:
                    teststr = list(aString[exprEnd+1:])
                    teststr.reverse()
                if not _getStringState(teststr):
                    return False
    return True

def safeRead(aString):
    """turn the js into happier python and check for bad operations
       before sending it to the interpreter
    """
    # get rid of trailing null. Konqueror appends this, and the python
    # interpreter balks when it is there.
    CHR0 = chr(0)
    while aString.endswith(CHR0):
        aString = aString[:-1]
    # strip leading and trailing whitespace
    aString = aString.strip()
    # zap /* ... */ comments
    aString = slashstarcomment.sub('',aString)
    # zap // comments
    aString = doubleslashcomment.sub('',aString)
    # here, we only check for the * operator as a DOS problem by default;
    # additional operators may be excluded by editing badOperators
    # at the top of the module
    if _sanityCheckMath(aString):
        return _Read(aString)
    else:
        raise ReadException, 'Unacceptable JSON expression: %s' % aString

read = safeRead

#################################
#   write object as JSON        #
#################################

#alwaysStripWhiteSpace is defined at the top of the module

tfnTuple = (('True','true'),('False','false'),('None','null'),)

def _replaceTrueFalseNone(aString):
    """replace True, False, and None with javascript counterparts"""
    for k in tfnTuple:
        if k[0] in aString:
            aString = aString.replace(k[0],k[1])
    return aString

def _handleCode(subStr,stripWhiteSpace):
    """replace True, False, and None with javascript counterparts if
       appropriate, remove unicode u's, fix long L's, make tuples
       lists, and strip white space if requested
    """
    if 'e' in subStr:
        #True, False, and None have 'e' in them. :)
        subStr = (_replaceTrueFalseNone(subStr))
    if stripWhiteSpace:
        # re.sub might do a better job, but takes longer.
        # Spaces are the majority of the whitespace, anyway...
        subStr = subStr.replace(' ','')
    if subStr[-1] in "uU":
        #remove unicode u's
        subStr = subStr[:-1]
    if "L" in subStr:
        #remove Ls from long ints
        subStr = subStr.replace("L",'')
    #do tuples as lists
    if "(" in subStr:
        subStr = subStr.replace("(",'[')
    if ")" in subStr:
        subStr = subStr.replace(")",']')
    return subStr

# re for a double-quoted string that has a single-quote in it
# but no double-quotes and python punctuation after:
redoublequotedstring = compile(r'"[^"]*\'[^"]*"[,\]\}:\)]')
escapedSingleQuote = r"\'"
escapedDoubleQuote = r'\"'

def doQuotesSwapping(aString):
    """rewrite doublequoted strings with single quotes as singlequoted strings with
    escaped single quotes"""
    s = []
    foundlocs = redoublequotedstring.finditer(aString)
    prevend = 0
    for loc in foundlocs:
        start,end = loc.span()
        s.append(aString[prevend:start])
        tempstr = aString[start:end]
        endchar = tempstr[-1]
        ts1 = tempstr[1:-2]
        ts1 = ts1.replace("'",escapedSingleQuote)
        ts1 = "'%s'%s" % (ts1,endchar)
        s.append(ts1)
        prevend = end
    s.append(aString[prevend:])
    return ''.join(s)

def _pyexpr2jsexpr(aString, stripWhiteSpace):
    """Take advantage of python's formatting of string representations of
    objects.  Python always uses "'" to delimit strings.  Except it doesn't when
    there is ' in the string.  Fix that, then, if we split
    on that delimiter, we have a list that alternates non-string text with
    string text.  Since string text is already properly escaped, we
    only need to replace True, False, and None in non-string text and
    remove any unicode 'u's preceding string values.

    if stripWhiteSpace is True, remove spaces, etc from the non-string
    text.
    """
    inSingleQuote = False
    inDoubleQuote = False
    #python will quote with " when there is a ' in the string,
    #so fix that first
    if redoublequotedstring.search(aString):
        aString = doQuotesSwapping(aString)
    marker = None
    if escapedSingleQuote in aString:
        #replace escaped single quotes with a marker
        marker = markerBase = '|'
        markerCount = 1
        while marker in aString:
            #if the marker is already there, make it different
            markerCount += 1
            marker = markerBase * markerCount
        aString = aString.replace(escapedSingleQuote,marker)

    #escape double-quotes
    aString = aString.replace('"',escapedDoubleQuote)
    #split the string on the real single-quotes
    splitStr = aString.split("'")
    outList = []
    alt = True
    for subStr in splitStr:
        #if alt is True, non-string; do replacements
        if alt:
            subStr = _handleCode(subStr,stripWhiteSpace)
        outList.append(subStr)
        alt = not alt
    result = '"'.join(outList)
    if marker:
        #put the escaped single-quotes back as "'"
        result = result.replace(marker,"'")
    return result

def write(obj, encoding="utf-8",stripWhiteSpace=alwaysStripWhiteSpace):
    """Represent the object as a string.  Do any necessary fix-ups
    with pyexpr2jsexpr"""
    try:
        #not really sure encode does anything here
        aString = str(obj).encode(encoding)
    except UnicodeEncodeError:
        aString = obj.encode(encoding)
    if isinstance(obj,basestring):
        if '"' in aString:
            aString = aString.replace(escapedDoubleQuote,'"')
            result = '"%s"' % aString.replace('"',escapedDoubleQuote)
        else:
            result = '"%s"' % aString
    else:
        result = _pyexpr2jsexpr(aString,stripWhiteSpace).encode(encoding)
    return result

class ReadException(Exception):
    pass

class WriteException(Exception):
    pass

########NEW FILE########
__FILENAME__ = plugins
#!/usr/bin/env python

"""
Classes for plugin download, installation, and registration.

"""


import ConfigParser
import os
import platform
import urllib, urllib2
from optparse import OptionParser
from zipfile import ZipFile


BASE_URL = 'http://plugins.serverdensity.com/'

python_version = platform.python_version_tuple()

if int(python_version[1]) >= 6:
    import json
else:
    import minjson
    json = None


class App(object):
    """
    Class for collecting arguments and options for the plugin
    download and installation process.

    """
    def __init__(self):
        usage = 'usage: %prog [options] key'
        self.parser = OptionParser(usage=usage)
        self.parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                               default=False, help='run in verbose mode')
        self.parser.add_option('-r', '--remove', action='store_true', dest='remove',
                               default=False, help='remove plugin')
        self.parser.add_option('-u', '--update', action='store_true', dest='update',
                               default=False, help='update installed plugins')

    def run(self):
        """
        Entry point to the plugin helper application.

        """
        (options, args) = self.parser.parse_args()
        if len(args) != 1:
            if options.update:
                updater = PluginUpdater(verbose=options.verbose)
                updater.start()
                return
            else:
                self.parser.error('incorrect number of arguments')
        if options.remove:
            remover = PluginRemover(key=args[0], verbose=options.verbose)
            remover.start()
        else:
            downloader = PluginDownloader(key=args[0], verbose=options.verbose)
            downloader.start()

class PluginMetadata(object):
    def __init__(self, downloader=None):
        self.downloader = downloader

    def get(self):
        raise Exception, 'sub-classes to provide implementation.'

    def json(self):
        metadata = self.get()
        if self.downloader.verbose:
            print metadata
        if json:
            return json.loads(metadata)
        else:
            return minjson.safeRead(metadata)

class FilePluginMetadata(PluginMetadata):
    """
    File-based metadata provider, for testing purposes.

    """
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'tests/plugin.json')
        if self.downloader.verbose:
            print 'reading plugin data from %s' % path
        f = open(path, 'r')
        data = f.read()
        f.close()
        return data

class WebPluginMetadata(PluginMetadata):
    """
    Web-based metadata provider.

    """
    def __init__(self, downloader=None, agent_key=None):
        super(WebPluginMetadata, self).__init__(downloader=downloader)
        self.agent_key = agent_key

    def get(self):
        url = '%sinstall/' % BASE_URL
        data = {
            'installId': self.downloader.key,
            'agentKey': self.agent_key
        }
        if self.downloader.verbose:
            print 'sending %s to %s' % (data, url)
        request = urllib2.urlopen(url, urllib.urlencode(data))
        response = request.read()
        return response

class Action(object):
    def __init__(self, key=None, verbose=True):
        self.key = key
        self.verbose = verbose

    def start(self):
        raise Exception, 'sub-classes to provide implementation.'

class PluginUpdater(Action):
    def __init__(self, verbose=True):
        super(PluginUpdater, self).__init__(verbose=verbose)

    def __get_installs(self):
        url = '%supdate/' % BASE_URL
        data = {
            'agentKey': self.config.agent_key
        }
        request = urllib2.urlopen(url, urllib.urlencode(data))
        response = request.read()
        if json:
            return json.loads(response)
        else:
            return minjson.safeRead(response)

    def start(self):
        self.config = AgentConfig(action=self)
        if self.verbose:
            print 'updating plugins'
        installs = self.__get_installs()
        for install_id in installs['installIds']:
            PluginDownloader(key=install_id, verbose=self.verbose).start()

class PluginRemover(Action):
    """
    Class for removing a plugin.

    """
    def __init__(self, key=None, verbose=True):
        super(PluginRemover, self).__init__(key=key, verbose=verbose)

    def __send_removal(self):
        url = '%suninstall/' % BASE_URL
        data = {
            'installId': self.key,
            'agentKey': self.config.agent_key
        }
        request = urllib2.urlopen(url, urllib.urlencode(data))
        response = request.read()
        if json:
            return json.loads(response)
        else:
            return minjson.safeRead(response)

    def __remove_file(self, name):
        name = '%s.py' % name
        path = os.path.join(self.config.plugin_path, name)
        if self.verbose:
            print 'removing %s' % path
        os.remove(path)

    def start(self):
        self.config = AgentConfig(action=self)
        if self.verbose:
            print 'removing plugin with install key:', self.key
        response = self.__send_removal()
        if self.verbose:
            print 'retrieved remove response.'
        assert 'status' in response, 'response is not valid.'
        if 'status' in response and response['status'] == 'error':
            raise Exception, response['msg']
        self.__remove_file(response['name'])
        print 'plugin removed successfully.'

class PluginDownloader(Action):
    """
    Class for downloading a plugin.

    """
    def __init__(self, key=None, verbose=True):
        super(PluginDownloader, self).__init__(key=key, verbose=verbose)

    def __prepare_plugin_directory(self):
        if not os.path.exists(self.config.plugin_path):
            if self.verbose:
                print '%s does not exist, creating' % self.config.plugin_path
            os.mkdir(self.config.plugin_path)
            if self.verbose:
                print '%s created' % self.config.plugin_path
        elif self.verbose:
            print '%s exists' % self.config.plugin_path

    def __download(self):
        self.url = '%sdownload/%s/%s/' % (BASE_URL, self.key, self.config.agent_key)
        if self.verbose:
            print 'downloading for agent %s: %s' % (self.config.agent_key, self.url)
        request = urllib2.urlopen(self.url)
        data = request.read()
        path = os.path.join(self.config.plugin_path, '%s.zip' % self.key)
        f = open(path, 'w')
        f.write(data)
        f.close()
        z = ZipFile(path, 'r')
        
        try:
            if json:
                if self.verbose:
                    print 'extract all: %s' % (os.path.dirname(path))
                z.extractall(os.path.dirname(path))
            else:
                for name in z.namelist():
                    if self.verbose:
                        print 'extract loop: %s' % (os.path.join(os.path.dirname(path), name))
                    data = z.read(name)
                    f = open(os.path.join(os.path.dirname(path), name), 'w')
                    f.write(data)
                    f.close()
        
        except Exception, ex:
            print ex

        z.close()
        os.remove(path)

    def start(self):
        self.config = AgentConfig(action=self)
        metadata = WebPluginMetadata(self, agent_key=self.config.agent_key).json()
        if self.verbose:
            print 'retrieved metadata.'
        assert 'configKeys' in metadata or 'status' in metadata, 'metadata is not valid.'
        if 'status' in metadata and metadata['status'] == 'error':
            raise Exception, metadata['msg']
        self.__prepare_plugin_directory()
        self.__download()
        self.config.prompt(metadata['configKeys'])
        print 'plugin installed; please restart your agent'

class AgentConfig(object):
    """
    Class for writing new config options to sd-agent config.

    """
    def __init__(self, action=None):
        self.action = action
        self.path = self.__get_config_path()
        assert self.path, 'no config path found.'
        self.config = self.__parse()
        if self.config.get('Main', 'plugin_directory'):
            self.plugin_path = self.config.get('Main', 'plugin_directory')
        self.agent_key = self.config.get('Main', 'agent_key')
        assert self.agent_key, 'no agent key.'

    def __get_config_path(self):
        paths = (
            '/etc/sd-agent/config.cfg',
            os.path.join(os.path.dirname(__file__), 'config.cfg')
        )
        for path in paths:
            if os.path.exists(path):
                if self.action.verbose:
                    print 'found config at %s' % path
                return path

    def __parse(self):
        if os.access(self.path, os.R_OK) == False:
            if self.action.verbose:
                print 'cannot access config'
            raise Exception, 'cannot access config'
        if self.action.verbose:
            print 'found config, parsing'
        config = ConfigParser.ConfigParser()
        config.read(self.path)
        if self.action.verbose:
            print 'parsed config'
        return config

    def __write(self, values):
        for key in values.keys():   
            self.config.set('Main', key, values[key])
        try:
            f = open(self.path, 'w')
            self.config.write(f)
            f.close()
        except Exception, ex:
            print ex
            sys.exit(1)

    def prompt(self, options):
        if not options:
            return
        values = {}
        for option in options:
            if not self.config.has_option('Main', option):
                values[option] = raw_input('value for %s: ' % option)
        self.__write(values)

if __name__ == '__main__':
    try:
        app = App()
        app.run()
    except Exception, ex:
        print 'error: %s' % ex

########NEW FILE########
__FILENAME__ = sd-deploy
'''
	Server Density
	www.serverdensity.com
	----
	Server monitoring agent for Linux, FreeBSD and Mac OS X

	Licensed under Simplified BSD License (see LICENSE)
'''

#
# Why are you using this?
#
import time
print 'Note: This script is for automating deployments and is not the normal way to install the SD agent. See http://www.serverdensity.com/docs/agent/installation/'
print 'Continuing in 4 seconds...'
time.sleep(4)

#
# Argument checks
#
import sys

if len(sys.argv) < 5:
	print 'Usage: python sd-deploy.py [API URL] [SD URL] [username] [password] [[init]]'
	sys.exit(2)	

#
# Get server details
#

import socket	

# IP
try:
	serverIp = socket.gethostbyname(socket.gethostname())
	
except socket.error, e:
	print 'Unable to get server IP: ' + str(e)
	sys.exit(2)
	
# Hostname
try:
	serverHostname = hostname = socket.getfqdn()
	
except socket.error, e:
	print 'Unable to get server hostname: ' + str(e)
	sys.exit(2)

#
# Get latest agent version
#

print '1/4: Downloading latest agent version';
		
import httplib
import urllib2

# Request details
try: 
	requestAgent = urllib2.urlopen('http://www.serverdensity.com/agentupdate/')
	responseAgent = requestAgent.read()
	
except urllib2.HTTPError, e:
	print 'Unable to get latest version info - HTTPError = ' + str(e)
	sys.exit(2)
	
except urllib2.URLError, e:
	print 'Unable to get latest version info - URLError = ' + str(e)
	sys.exit(2)
	
except httplib.HTTPException, e:
	print 'Unable to get latest version info - HTTPException'
	sys.exit(2)
	
except Exception, e:
	import traceback
	print 'Unable to get latest version info - Exception = ' + traceback.format_exc()
	sys.exit(2)

#
# Define downloader function
#

import md5 # I know this is depreciated, but we still support Python 2.4 and hashlib is only in 2.5. Case 26918
import urllib

def downloadFile(agentFile, recursed = False):
	print 'Downloading ' + agentFile['name']
	
	downloadedFile = urllib.urlretrieve('http://www.serverdensity.com/downloads/sd-agent/' + agentFile['name'])
	
	# Do md5 check to make sure the file downloaded properly
	checksum = md5.new()
	f = file(downloadedFile[0], 'rb')
	
	# Although the files are small, we can't guarantee the available memory nor that there
	# won't be large files in the future, so read the file in small parts (1kb at time)
	while True:
		part = f.read(1024)
		
		if not part: 
			break # end of file
	
		checksum.update(part)
		
	f.close()
	
	# Do we have a match?
	if checksum.hexdigest() == agentFile['md5']:
		return downloadedFile[0]
		
	else:
		# Try once more
		if recursed == False:
			downloadFile(agentFile, True)
		
		else:
			print agentFile['name'] + ' did not match its checksum - it is corrupted. This may be caused by network issues so please try again in a moment.'
			sys.exit(2)

#
# Install the agent files
#

# We need to return the data using JSON. As of Python 2.6+, there is a core JSON
# module. We have a 2.4/2.5 compatible lib included with the agent but if we're
# on 2.6 or above, we should use the core module which will be faster
import platform

pythonVersion = platform.python_version_tuple()

# Decode the JSON
if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
	import json
	
	try:
		updateInfo = json.loads(responseAgent)
	except Exception, e:
		print 'Unable to get latest version info. Try again later.'
		sys.exit(2)
	
else:
	import minjson
	
	try:
		updateInfo = minjson.safeRead(responseAgent)
	except Exception, e:
		print 'Unable to get latest version info. Try again later.'
		sys.exit(2)

# Loop through the new files and call the download function
for agentFile in updateInfo['files']:
	agentFile['tempFile'] = downloadFile(agentFile)			

# If we got to here then everything worked out fine. However, all the files are still in temporary locations so we need to move them
import os
import shutil # Prevents [Errno 18] Invalid cross-device link (case 26878) - http://mail.python.org/pipermail/python-list/2005-February/308026.html

# Make sure doesn't exist already
if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')

os.mkdir('sd-agent')

for agentFile in updateInfo['files']:
	print 'Installing ' + agentFile['name']
	
	if agentFile['name'] != 'config.cfg':
		shutil.move(agentFile['tempFile'], 'sd-agent/' + agentFile['name'])
	
print 'Agent files downloaded'

#
# Call API to add new server
#

print '2/4: Adding new server'

# Build API payload
import time
timestamp = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())

postData = urllib.urlencode({'name' : serverHostname, 'ip' : serverIp, 'notes' : 'Added by sd-deploy: ' + timestamp })

# Send request
try: 	
	# Password manager
	mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
	mgr.add_password(None, sys.argv[1] + '/1.0/', sys.argv[3], sys.argv[4])
	opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(mgr), urllib2.HTTPDigestAuthHandler(mgr))
	
	urllib2.install_opener(opener)
	
	# Build the request handler
	requestAdd = urllib2.Request(sys.argv[1] + '/1.0/?account=' + sys.argv[2] + '&c=servers/add', postData, { 'User-Agent' : 'Server Density Deploy' })
	
	# Do the request, log any errors
	responseAdd = urllib2.urlopen(requestAdd)
	
	readAdd = responseAdd.read()
		
except urllib2.HTTPError, e:
	print 'HTTPError = ' + str(e)
	
	if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')
	
except urllib2.URLError, e:
	print 'URLError = ' + str(e)
	
	if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')
	
except httplib.HTTPException, e: # Added for case #26701
	print 'HTTPException' + str(e)
	
	if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')
		
except Exception, e:
	import traceback
	print 'Exception = ' + traceback.format_exc()
	
	if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')

# Decode the JSON
if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
	import json
	
	try:
		serverInfo = json.loads(readAdd)
	except Exception, e:
		print 'Unable to add server.'
		
		if os.path.exists('sd-agent/'):
			shutil.rmtree('sd-agent/')
		
		sys.exit(2)
	
else:
	import minjson
	
	try:
		serverInfo = minjson.safeRead(readAdd)
	except Exception, e:
		print 'Unable to add server.'
		
		if os.path.exists('sd-agent/'):
			shutil.rmtree('sd-agent/')
		
		sys.exit(2)
		
print 'Server added - ID: ' + str(serverInfo['data']['serverId'])

#
# Write config file
#

print '3/4: Writing config file'

configCfg = '[Main]\nsd_url: http://' + sys.argv[2] + '\nagent_key: ' + serverInfo['data']['agentKey'] + '\napache_status_url: http://www.example.com/server-status/?auto'

try:
	f = open('sd-agent/config.cfg', 'w')
	f.write(configCfg)
	f.close()

except Exception, e:
	import traceback
	print 'Exception = ' + traceback.format_exc()
	
	if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')

print 'Config file written'

#
# Install init.d
#

if len(sys.argv) == 6:
	
	print '4/4: Installing init.d script'
	
	shutil.copy('sd-agent/sd-agent.init', '/etc/init.d/sd-agent')
	
	import subprocess
	
	print 'Setting permissions'
	
	df = subprocess.Popen(['chmod', '0755', '/etc/init.d/sd-agent'], stdout=subprocess.PIPE).communicate()[0]
	
	print 'chkconfig'
	
	df = subprocess.Popen(['chkconfig', '--add', 'sd-agent'], stdout=subprocess.PIPE).communicate()[0]
	
	print 'Setting paths'
	
	path = os.path.realpath(__file__)
	path = os.path.dirname(path)
	
	df = subprocess.Popen(['ln', '-s', path + '/sd-agent/', '/usr/bin/sd-agent'], stdout=subprocess.PIPE).communicate()[0]
	
	print 'Install completed'
	
	print 'Launch: /etc/init.d/sd-agent start'
	
else:
	
	print '4/4: Not installing init.d script'
	print 'Install completed'
	
	path = os.path.realpath(__file__)
	path = os.path.dirname(path)
	
	print 'Launch: python ' + path + '/sd-agent/agent.py start'
########NEW FILE########
