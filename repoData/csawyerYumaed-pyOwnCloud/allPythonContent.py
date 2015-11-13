__FILENAME__ = create_csynclib
#!/usr/bin/env python2
"""Generates ctype python files for the missing versions
need python modules:
* ctypeslib
* GitPython

run it with one argument where a git clone of ocsync exists:
git://git.csync.org/users/owncloud/csync
"""

from git import Repo
from distutils.version import StrictVersion
from subprocess import call
import os
import sys

from csync.csynclib import specific_parts

#the known versions
known_versions=[ i[0] for i in specific_parts ]

#Add files that are needed to compile .h files
open('csync_version.h','a')
open('config.h','a')

#open the git repo
repo = Repo(sys.argv[1])

for tag in repo.tags:
    #only match tags, that are version tags and are higher than 0.70.0
    if not tag.name.startswith('v'):
        continue
    version = tag.name[1:]
    try:
        if StrictVersion(version) < StrictVersion('0.70.0'):
            continue
    except ValueError:
        continue

    #only new versions interessting us
    if version in known_versions:
        continue

    print version

    # get the csync.h at the version
    with open("csync"+version+".h",'w') as f:
        f.write(repo.commit(tag).tree['src/csync.h'].data_stream.read())

    #create python file out of the header file
    safe_name = tag.name.replace('.',"_")

    call(["h2xml","csync"+version+".h","-I", os.getcwd(), "-o", "csync"+version+".xml", "-q"])
    call(["xml2py", "csync"+version+".xml", "-o", safe_name+".py", "-k", "efst", "-l", "libocsync.so.0"])

########NEW FILE########
__FILENAME__ = csync
#!/usr/bin/env python

import os
import sys
import argparse
import ConfigParser
import ctypes
import re
import pprint
import copy
import getpass
import logging

logging.basicConfig(level=logging.DEBUG, format='%(name)s-%(levelname)s: %(message)s')

try:
	import keyring
except:
	logging.debug('Keyring not available')
	keyring = None

try:
	from progressbar import ProgressBar, Percentage, Bar, ETA, FileTransferSpeed
except ImportError:
	logging.debug('ProgressBar not available')
	ProgressBar = None

try:
	import csynclib
except ImportError as impError:
	logging.critical(impError.message)
	sys.exit(1)

import version


#Global variables
VERSION = version.version
PASSWORD_SAFE = '********'
DEBUG = False

def CSYNC_VERSION_INT(a, b, c):
	return ((a) << 16 | (b) << 8 | (c))

class ownCloudSync():
	"""This handles the actual syncying with ownCloud
	cfg is a {}.  should have these things:
		user:
		pass:
		url:
		src:
	None of them are optional. :)
	optional items:
		SSLfingerPrint:
	"""
	def __init__(self, cfg = None):
		"""initialize"""
		self.auth_callback = None
		self.log_callback = None
		self.progress_callback = None
		self.logger = logging.getLogger("pyOC")
		self.cfg = cfg
		self.debug = cfg['debug']
		self._user = cfg['user']
		self._password = cfg['pass']
		self._fingerprint = cfg['sslfingerprint'].lower()
		self._keyring = cfg['use_keyring']
		self.libVersion = csynclib.csync_version(0,40,1)
		self.logger.debug('libocsync version: %s', self.libVersion)
		c = csynclib.CSYNC()
		self.ctx = ctypes.pointer(c)
		self.buildURL()
		self.logger.info('Syncing %s to %s, logging in as user: %s' , self.cfg['src'],
			self.cfg['url'],
			self._user,
			)
		if cfg.has_key('dry_run') and cfg['dry_run']:
			return
		self.sync()

	def buildURL(self):
		"""build the URL we use for owncloud"""
		url = self.cfg['url']
		if not url:
			self.logger.error('You must specify a url, use --url, or put in cfg file.')
			sys.exit(1)
		url = url.replace('https','ownclouds')
		url = url.replace('http','owncloud')
		#add / if needed
		if url[-1:] != '/':
			url = ''.join((url,'/'))
		url += self.cfg['davPath']
		#add / if needed
		if url[-1:] != '/':
			url = ''.join((url,'/'))
		url = ''.join((url, self.cfg['dst']))
		#take off any trailing slash.
		if url[-1:] == '/':
			url = url[:-1]
		self.cfg['url'] = url
		self.logger.debug('buildURL: %s', url)
		return

	def get_auth_callback(self):
		"""gives back the auth callback:
			The actual function is called out of the ownCloudSync object."""
		def auth_wrapper(prompt, buffer, bufferLength, echo, verify, userData):
			return self.authCallback(prompt, buffer, bufferLength, echo, verify, userData)
		if not self.auth_callback:
			self.auth_callback = csynclib.csync_auth_callback(auth_wrapper)
		return self.auth_callback

	def authCallback(self, prompt, buffer, bufferLength, echo, verify, userData):
		"""
		(const char *prompt, char *buf, size_t len,
			int echo, int verify, void *userdata)
		called like this:
			("Enter your username: ", buf, NE_ABUFSIZ-1, 1, 0, dav_session.userdata )
			type is 1 for username, 0 for password.
		calls functions username(), password() or ssl(fingerprint)
		"""
		self.logger.debug("authCallback: '%s', %s, %i, %i, %i, %s", prompt,  buffer,  bufferLength, echo, verify, userData)
		ret = None
		if 'username' in prompt:
			ret = self.username()
		elif 'password' in prompt:
			ret = self.password()
		elif 'SSL' in prompt:
			fingerprint = re.search("fingerprint: ([\\w\\d:]+)", prompt).group(1)
			ret = self.ssl(fingerprint)
		else:
			self.logger.warning("authCallback: unknown prompt: '%s'", prompt)
			return -1
		
		for i in range(len(ret)):
			ctypes.memset(buffer+i, ord(ret[i]), 1)
		if self.debug:
			buffString = ctypes.string_at(buffer, len(ret))
			if 'password' in prompt:
				if ret and ret in buffString:
					buffString = buffString.replace(ret, PASSWORD_SAFE)
			self.logger.debug("returning: '%s'", buffString)
		return 0



	def sync(self):
		r = csynclib.csync_create(self.ctx, self.cfg['src'], self.cfg['url'])
		if r != 0:
			self.error('csync_create', r)
		
		csynclib.csync_set_log_callback(self.ctx, self.get_log_callback())
		csynclib.csync_set_log_verbosity(self.ctx, self.cfg['verbosity_ocsync'])

		self.logger.debug('authCallback setup')
		csynclib.csync_set_auth_callback(self.ctx, self.get_auth_callback())

		if self.cfg['progress']:
			csynclib.csync_set_progress_callback(self.ctx, self.get_progress_callback())
		
		r = csynclib.csync_init(self.ctx)
		if r != 0:
			self.error('csync_init', r)
		self.logger.debug('Initialization done.')
		if (self.cfg.has_key('downloadlimit') and self.cfg['downloadlimit']) or \
			(self.cfg.has_key('uploadlimit') and self.cfg['uploadlimit']):
			if csynclib.csync_version(CSYNC_VERSION_INT(0,81,0)) is None:
				self.logger.warning('Bandwidth throttling requires ocsync version >= 0.81.0, ignoring limits')
			else:
				if self.cfg.has_key('downloadlimit') and self.cfg['downloadlimit']:
					dlimit = ctypes.c_int(int(self.cfg['downloadlimit']) * 1000)
					self.logger.debug('Download limit: %i', dlimit.value)
					csynclib.csync_set_module_property(self.ctx, 'bandwidth_limit_download', ctypes.pointer(dlimit))
				if self.cfg.has_key('uploadlimit') and self.cfg['uploadlimit']:
					ulimit = ctypes.c_int(int(self.cfg['uploadlimit']) * 1000)
					self.logger.debug('Upload limit: %i', ulimit.value)
					csynclib.csync_set_module_property(self.ctx,'bandwidth_limit_upload',ctypes.pointer(ulimit))
		r = csynclib.csync_update(self.ctx)
		if r != 0:
			self.error('csync_update', r)
		self.logger.debug('Update done.')
		r = csynclib.csync_reconcile(self.ctx)
		if r != 0:
			self.error('csync_reconcile', r)
		self.logger.debug('Reconcile done.')
		r = csynclib.csync_propagate(self.ctx)
		if r != 0:
			self.error('csync_propogate', r)
		self.logger.debug('Propogate finished, destroying.')
		r = csynclib.csync_destroy(self.ctx)
		if r != 0:
			self.error('csync_destroy', r)

	def get_progress_callback(self):
		def progress_wrapper(progress_p, userdata_p):
			if progress_p:
				progress_p = progress_p[0]
			if userdata_p:
				userdata_p = userdata_p[0]
			return self.progress(progress_p, userdata_p)
		if not self.progress_callback:
			self.progress_callback = csynclib.csync_progress_callback(progress_wrapper)
		return self.progress_callback

	def progress(self, progress, userdata):
		progress_text = {
			csynclib.CSYNC_NOTIFY_INVALID: "invalid",
			csynclib.CSYNC_NOTIFY_START_SYNC_SEQUENCE: "start syncing",
			csynclib.CSYNC_NOTIFY_START_DOWNLOAD: "start downloading",
			csynclib.CSYNC_NOTIFY_START_UPLOAD: "start uploading",
			csynclib.CSYNC_NOTIFY_PROGRESS: "progess message",
			csynclib.CSYNC_NOTIFY_FINISHED_DOWNLOAD: "finished downloading",
			csynclib.CSYNC_NOTIFY_FINISHED_UPLOAD: "finished uploading",
			csynclib.CSYNC_NOTIFY_FINISHED_SYNC_SEQUENCE: "finished sycing",
			csynclib.CSYNC_NOTIFY_START_DELETE: "start deleted",
			csynclib.CSYNC_NOTIFY_END_DELETE: "end deleted",
			csynclib.CSYNC_NOTIFY_ERROR: "error",
			}

		if progress.kind in (csynclib.CSYNC_NOTIFY_START_UPLOAD, csynclib.CSYNC_NOTIFY_START_DOWNLOAD, csynclib.CSYNC_NOTIFY_START_DELETE):
			maxval = progress.overall_file_count
			if progress.kind == csynclib.CSYNC_NOTIFY_START_UPLOAD:
				self.progress_mode = "Uploading "
			if progress.kind == csynclib.CSYNC_NOTIFY_START_DOWNLOAD:
				self.progress_mode = "Downloading "
			if progress.kind == csynclib.CSYNC_NOTIFY_START_DELETE:
				self.progress_mode = "Deleting "
				maxval = progress.overall_transmission_size

			fname = progress.path[len(self.cfg['url'])+1:]
			widgets = [self.progress_mode, fname, ' ', Percentage(), ' ', Bar(),
				' ', ETA(), ' ', FileTransferSpeed()]
			self.pbar = ProgressBar(widgets=widgets, maxval=maxval).start()
		elif progress.kind in (csynclib.CSYNC_NOTIFY_FINISHED_DOWNLOAD, csynclib.CSYNC_NOTIFY_FINISHED_UPLOAD, csynclib.CSYNC_NOTIFY_END_DELETE):
			self.pbar.finish()
			return
		elif progress.kind == csynclib.CSYNC_NOTIFY_PROGRESS:
			self.pbar.update(progress.curr_bytes)
		else:
			if progress.kind in (csynclib.CSYNC_NOTIFY_START_SYNC_SEQUENCE, csynclib.CSYNC_NOTIFY_FINISHED_SYNC_SEQUENCE):
				return
			self.logger.debug(progress_text[progress.kind])
			self.logger.debug("'%s', %i, %i, %i, %i, %i, %i", progress.path, progress.file_size, progress.curr_bytes, progress.overall_file_count, progress.current_file_no, progress.overall_transmission_size, progress.current_overall_bytes)

	def username(self):
		"""returns the username"""
		return self._user

	def password(self):
		"""returns the password"""
		ret = None
		if keyring and self._keyring:
			self.logger.debug("using password from keyring")
			ret = keyring.get_password('ownCloud', self.username())
		if ret is None:
			if not self._password:
				ret = getpass.getpass('ownCloud password:')
			else:
				ret = self._password
			if keyring and self._keyring:
				self.logger.debug("saving password to keyring")
				keyring.set_password('ownCloud', self.username(), ret)
		return ret

	def ssl(self, fingerprint):
		"""returns if fingerprint is valid (yes or no as string)"""
		if fingerprint.lower() == self._fingerprint:
			return 'yes'
		else:
			self.logger.error('SSL fingerprint: %s not accepted, aborting' , fingerprint)
			return 'no'


	def get_log_callback(self):
		def log_wrapper(ctx, verbosity, function, buffer, userdata):
			return self.log(verbosity, function, buffer, userdata)
		if not self.log_callback:
			self.log_callback = csynclib.csync_log_callback(log_wrapper)
		return self.log_callback

	def log(self, verbosity, function, buffer, userdata):
		"""Log stuff from the ocsync library."""
		v2l = {csynclib.CSYNC_LOG_PRIORITY_NOLOG: logging.CRITICAL,
			csynclib.CSYNC_LOG_PRIORITY_FATAL: logging.CRITICAL,
			csynclib.CSYNC_LOG_PRIORITY_ALERT: logging.CRITICAL,
			csynclib.CSYNC_LOG_PRIORITY_CRIT: logging.CRITICAL,
			csynclib.CSYNC_LOG_PRIORITY_ERROR: logging.ERROR,
			csynclib.CSYNC_LOG_PRIORITY_WARN: logging.WARN,
			csynclib.CSYNC_LOG_PRIORITY_NOTICE: logging.INFO,
			csynclib.CSYNC_LOG_PRIORITY_INFO: logging.INFO,
			csynclib.CSYNC_LOG_PRIORITY_DEBUG: logging.DEBUG,
			csynclib.CSYNC_LOG_PRIORITY_TRACE: logging.DEBUG,
			csynclib.CSYNC_LOG_PRIORITY_NOTSET: logging.DEBUG,
			csynclib.CSYNC_LOG_PRIORITY_UNKNOWN: logging.DEBUG,
			}

		level = logging.DEBUG
		if verbosity in v2l:
			level = v2l[verbosity]

		logging.getLogger("ocsync").log(level, buffer)

	def error(self, cmd, returnCode):
		"""handle library errors"""
		errNum = csynclib.csync_get_error(self.ctx)
		errMsg = csynclib.csync_get_error_string(self.ctx)
		if not errMsg:
			if errNum == csynclib.CSYNC_ERR_AUTH_SERVER and cmd == 'csync_update':
				errMsg = 'The user could not be authenticated with the server, check username/password combination.'
			if errNum == csynclib.CSYNC_ERR_NOT_FOUND and cmd == 'csync_update':
				errMsg = 'The remote folder "' + self.cfg['dst'] + '" could not be found, check that the remote folder exists on ownCloud.'
		self.logger.error('%s exited with %s, csync(%s) error %s: %s',
			cmd,
			returnCode,
			self.libVersion,
			errNum,
			errMsg,
			)
		sys.exit(1)

def getConfigPath():
	"""get the local configuration file path
	"""
	if sys.platform.startswith('linux'):
		cfgPath = os.path.join('~','.local','share','data','ownCloud')
		cfgPath = os.path.expanduser(cfgPath) 
	elif sys.platform == 'darwin':
		cfgPath = os.path.join('~','Library','Application Support','ownCloud')
		cfgPath = os.path.expanduser(cfgPath) 
	elif 'win' in sys.platform:
		cfgPath = os.path.join('%LOCALAPPDATA%','ownCloud')
		cfgPath = os.path.expandvars(cfgPath)
	else:
		logging.warning('Unknown/not supported platform %s, please file a bug report. ', sys.platform)
		sys.exit(1)
	logging.debug('getConfigPath: %s', cfgPath)
	return cfgPath

def getConfig(parser):
	args = vars(parser.parse_args())
	if DEBUG:
		logging.debug('From args: ')
		pargs = copy.copy(args)
		if pargs['pass']:
			pargs['pass'] = PASSWORD_SAFE
		logging.debug(pprint.pformat(pargs))
	newArgs = {}
	for k, v in args.iteritems():
		if v:
			newArgs[k] = v
	args = newArgs
	cfg = {}
	cfgFile = None
	if args.has_key('config'):
		cfgFile = args['config']
	else:
		cfgPath = getConfigPath()
		if os.path.exists(os.path.join(cfgPath,'owncloud.cfg')):
			cfgFile = os.path.join(cfgPath, 'owncloud.cfg')
	if cfgFile:
		with open(cfgFile) as fd:
			"""We use the INI file format that Mirall does. we allow more
			things in the cfg file...
				pass: the password
			"""
			c = ConfigParser.SafeConfigParser()
			c.readfp(fd)
			if csynclib.csync_version(CSYNC_VERSION_INT(0,81,0)) is None:
				cfg = dict(c.items('ownCloud'))
			else:
				if c.has_section('BWLimit'):
					cfg = dict(c.items('BWLimit') + c.items('ownCloud'))
					if not cfg['useuploadlimit']:
						cfg['uploadlimit'] = None
					if not cfg['usedownloadlimit']:
						cfg['downloadlimit'] = None
				else:
					logging.debug('config file has no section [BWLimit]')
					cfg = dict(c.items('ownCloud'))
			if DEBUG:
				logging.debug('configuration info received from %s:', cfgFile)
				pcfg = copy.copy(cfg)
				if pcfg.has_key('pass'):
					pcfg['pass'] = PASSWORD_SAFE
				logging.debug(pprint.pformat(pcfg))
	cfg.setdefault('davPath', 'remote.php/webdav/')
	cfg.setdefault('sslfingerprint' '')
	cfg.setdefault('pass', None)
	cfg.setdefault('user', getpass.getuser())
	cfg.setdefault('use_keyring', False)
	cfg.setdefault('progress', False)
	if os.environ.has_key('OCPASS'):
		cfg['pass'] = os.environ['OCPASS']
		logging.debug('password coming from environment variable OCPASS')
	#cmd line arguments win out over config files.
	parser.set_defaults(**cfg)
	args = vars(parser.parse_args())
	cfg.update(args)
	if DEBUG:
		logging.debug('Finished parsing configuration file:')
		pcfg = copy.copy(cfg)
		if pcfg.has_key('pass'):
			pcfg['pass'] = PASSWORD_SAFE
		logging.debug(pprint.pformat(pcfg))
	return cfg

def startSync(parser):
	cfg = getConfig(parser)
	try:
		ownCloudSync(cfg)
	except KeyError:
		exc_type, exc_value, exc_tb = sys.exc_info()
		logging.error('This option "%s" is required, but was not found in the configuration.', exc_value)
		if DEBUG:
			raise

def main():
	parser = argparse.ArgumentParser(
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description = 'Synchronize files across machines using ownCloud DAV server.',
		epilog = """
oclient supports the ownCloud config file, which is located here:
  {cfg}
oclient only supports the 'ownCloud' section of the config.
oclient supports the following keys in the cfg  file:
	user: username on the ownCloud server
	pass: password on the ownCloud server
	url: url of the ownCloud server
	sslfingerprint: valid SSL fingerprint for the server
	src: local directory to sync against
	dst: folder on the server to sync against
complete example:
[ownCloud]
user=awesomeSauce
pass=PasswordThisIsSuperSuperSecretReallyISwearLOL
url=https://www.example.org/owncloud/
sslfingerprint=
src=/home/awesomeSauce/ownCloud
dst=clientsync

Password options:
  *) You can specify on the cmd line: -p (not very safe)
  *) In the envifonment variable: OCPASS
  *) In the owncloud.cfg file as pass = <password>
  *) Use keyring to store passwords in a keyring. (keyring package is {keyring}installed)
  *) Do none of the above, and it will prompt you for the password.
  The choice is yours, if you put it in the cfg file, be careful to
  make sure nobody but you can read the file. (0400/0600 file perms).
		""".format(cfg = os.path.join(getConfigPath(),'owncloud.cfg'), keyring="" if keyring else "NOT "),
	)
	v = "%s - repo: %s" % (VERSION.asString, VERSION.asHead)
	parser.add_argument('-v', '--version',
		action='version', 
		version = '%(prog)s ' + v)
	parser.add_argument('-c', '--config', nargs='?', default = None,
		help = "Configuration file to use.")
	parser.add_argument('-u', '--user', nargs='?', default = None,
		help = "Username on server.")
	parser.add_argument('--ssl', nargs='?', default = None,
		dest = 'sslfingerprint',
		help = "SSL fingerprint on server to accept.")
	parser.add_argument('-p', '--pass', nargs='?', default = None,
		help = "Password on server. You can also store this in environment variable OCPASS.")
	parser.add_argument('--dry-run', action = 'store_true', default = False,
		help = "Dry Run, do not actually execute command.")
	parser.add_argument('--debug', action = 'store_true', default = False,
		help = "Print debug information.")
	parser.add_argument('--verbosity-ocsync', default = csynclib.CSYNC_LOG_PRIORITY_WARN, type=int,
		help = "Verbosity for libocsync. (0=NOLOG,11=Everything)")
	parser.add_argument('-s', '--src', nargs='?',
		default =  os.path.expanduser(os.path.join('~','ownCloud')),
		help = "Local Directory to sync with.")
	parser.add_argument('-d', '--dst', nargs='?', default = 'clientsync',
		help = "Remote Directory on server to sync to.")
	parser.add_argument('--url', nargs='?', default = None,
		help = "URL of owncloud server.")
	if csynclib.csync_version(CSYNC_VERSION_INT(0,81,0)) is not None:
		parser.add_argument('--downloadlimit', nargs = '?', default = None,
			help = "Download limit in KB/s.")
		parser.add_argument('--uploadlimit', nargs = '?', default = None,
			help = "Upload limit in KB/s.")
	if keyring:
		parser.add_argument('--use-keyring', action = 'store_true', default = False,
				help = "Use keyring if available to store password safely.")
	if ProgressBar and csynclib.csync_version(CSYNC_VERSION_INT(0,90,0)) is not None:
		parser.add_argument('--progress', action = 'store_true', default = False,
				help = "Show progress while syncing.")
	args = vars(parser.parse_args())
	if args['debug']:
		global DEBUG
		DEBUG = True
		logging.debug('Turning debug on')
	else:
		logging.getLogger('').setLevel(logging.INFO)
	startSync(parser)

if __name__ == '__main__':
	import signal
	def signal_handler(signal, frame):
		logging.info('\nYou pressed Ctrl+C, aborting ...')
		sys.exit(1)
	signal.signal(signal.SIGINT, signal_handler)
	main()

# vim: noet:ts=4:sw=4:sts=4

########NEW FILE########
__FILENAME__ = post
from ctypes import *
from .pre import csynclib

STRING = c_char_p

class LP_LP_csync_s(Structure):
	pass

class csync_s(Structure):
	pass

csync_ftw_type_e = c_int # enum
csync_instructions_e = c_int # enum
csync_notify_type_e = c_int # enum
csync_error_codes_e = c_int # enum

CSYNC = csync_s
csync_create = csynclib.csync_create
csync_create.restype = c_int
csync_create.argtypes = [POINTER(POINTER(CSYNC)), STRING, STRING]
csync_init = csynclib.csync_init
csync_init.restype = c_int
csync_init.argtypes = [POINTER(CSYNC)]
csync_update = csynclib.csync_update
csync_update.restype = c_int
csync_update.argtypes = [POINTER(CSYNC)]
csync_reconcile = csynclib.csync_reconcile
csync_reconcile.restype = c_int
csync_reconcile.argtypes = [POINTER(CSYNC)]
csync_propagate = csynclib.csync_propagate
csync_propagate.restype = c_int
csync_propagate.argtypes = [POINTER(CSYNC)]
csync_destroy = csynclib.csync_destroy
csync_destroy.restype = c_int
csync_destroy.argtypes = [POINTER(CSYNC)]
csync_add_exclude_list = csynclib.csync_add_exclude_list
csync_add_exclude_list.restype = c_int
csync_add_exclude_list.argtypes = [POINTER(CSYNC), STRING]
csync_get_config_dir = csynclib.csync_get_config_dir
csync_get_config_dir.restype = STRING
csync_get_config_dir.argtypes = [POINTER(CSYNC)]
csync_set_config_dir = csynclib.csync_set_config_dir
csync_set_config_dir.restype = c_int
csync_set_config_dir.argtypes = [POINTER(CSYNC), STRING]
csync_enable_statedb = csynclib.csync_enable_statedb
csync_enable_statedb.restype = c_int
csync_enable_statedb.argtypes = [POINTER(CSYNC)]
csync_disable_statedb = csynclib.csync_disable_statedb
csync_disable_statedb.restype = c_int
csync_disable_statedb.argtypes = [POINTER(CSYNC)]
csync_is_statedb_disabled = csynclib.csync_is_statedb_disabled
csync_is_statedb_disabled.restype = c_int
csync_is_statedb_disabled.argtypes = [POINTER(CSYNC)]
csync_get_userdata = csynclib.csync_get_userdata
csync_get_userdata.restype = c_void_p
csync_get_userdata.argtypes = [POINTER(CSYNC)]
csync_set_userdata = csynclib.csync_set_userdata
csync_set_userdata.restype = c_int
csync_set_userdata.argtypes = [POINTER(CSYNC), c_void_p]
size_t = c_ulong
csync_auth_callback = CFUNCTYPE(c_int, STRING, c_void_p, size_t, c_int, c_int, c_void_p)
csync_get_auth_callback = csynclib.csync_get_auth_callback
csync_get_auth_callback.restype = csync_auth_callback
csync_get_auth_callback.argtypes = [POINTER(CSYNC)]
csync_set_auth_callback = csynclib.csync_set_auth_callback
csync_set_auth_callback.restype = c_int
csync_set_auth_callback.argtypes = [POINTER(CSYNC), csync_auth_callback]
csync_set_log_verbosity = csynclib.csync_set_log_verbosity
csync_set_log_verbosity.restype = c_int
csync_set_log_verbosity.argtypes = [POINTER(CSYNC), c_int]
csync_get_log_verbosity = csynclib.csync_get_log_verbosity
csync_get_log_verbosity.restype = c_int
csync_get_log_verbosity.argtypes = [POINTER(CSYNC)]
csync_log_callback = CFUNCTYPE(None, POINTER(CSYNC), c_int, STRING, STRING, c_void_p)
csync_get_log_callback = csynclib.csync_get_log_callback
csync_get_log_callback.restype = csync_log_callback
csync_get_log_callback.argtypes = [POINTER(CSYNC)]
csync_set_log_callback = csynclib.csync_set_log_callback
csync_set_log_callback.restype = c_int
csync_set_log_callback.argtypes = [POINTER(CSYNC), csync_log_callback]
csync_get_statedb_file = csynclib.csync_get_statedb_file
csync_get_statedb_file.restype = STRING
csync_get_statedb_file.argtypes = [POINTER(CSYNC)]
csync_enable_conflictcopys = csynclib.csync_enable_conflictcopys
csync_enable_conflictcopys.restype = c_int
csync_enable_conflictcopys.argtypes = [POINTER(CSYNC)]
csync_set_local_only = csynclib.csync_set_local_only
csync_set_local_only.restype = c_int
csync_set_local_only.argtypes = [POINTER(CSYNC), c_bool]
csync_get_local_only = csynclib.csync_get_local_only
csync_get_local_only.restype = c_bool
csync_get_local_only.argtypes = [POINTER(CSYNC)]
csync_get_status = csynclib.csync_get_status
csync_get_status.restype = c_int
csync_get_status.argtypes = [POINTER(CSYNC)]
csync_set_status = csynclib.csync_set_status
csync_set_status.restype = c_int
csync_set_status.argtypes = [POINTER(CSYNC), c_int]
class csync_tree_walk_file_s(Structure):
	pass
TREE_WALK_FILE = csync_tree_walk_file_s
csync_treewalk_visit_func = CFUNCTYPE(c_int, POINTER(TREE_WALK_FILE), c_void_p)
csync_walk_local_tree = csynclib.csync_walk_local_tree
csync_walk_local_tree.restype = c_int
csync_walk_local_tree.argtypes = [POINTER(CSYNC), POINTER(csync_treewalk_visit_func), c_int]
csync_walk_remote_tree = csynclib.csync_walk_remote_tree
csync_walk_remote_tree.restype = c_int
csync_walk_remote_tree.argtypes = [POINTER(CSYNC), POINTER(csync_treewalk_visit_func), c_int]
csync_set_iconv_codec = csynclib.csync_set_iconv_codec
csync_set_iconv_codec.restype = c_int
csync_set_iconv_codec.argtypes = [STRING]
class csync_progress_s(Structure):
	pass
CSYNC_PROGRESS = csync_progress_s
csync_progress_callback = CFUNCTYPE(None, POINTER(CSYNC_PROGRESS), c_void_p)
csync_set_progress_callback = csynclib.csync_set_progress_callback
csync_set_progress_callback.restype = c_int
csync_set_progress_callback.argtypes = [POINTER(CSYNC), csync_progress_callback]
csync_get_progress_callback = csynclib.csync_get_progress_callback
csync_get_progress_callback.restype = csync_progress_callback
csync_get_progress_callback.argtypes = [POINTER(CSYNC)]

CSYNC_ERROR_CODE = csync_error_codes_e
csync_get_error = csynclib.csync_get_error
csync_get_error.restype = CSYNC_ERROR_CODE
csync_get_error.argtypes = [POINTER(CSYNC)]
csync_get_error_string = csynclib.csync_get_error_string
csync_get_error_string.restype = STRING
csync_get_error_string.argtypes = [POINTER(CSYNC)]
csync_set_module_property = csynclib.csync_set_module_property
csync_set_module_property.restype = c_int
csync_set_module_property.argtypes = [POINTER(CSYNC), STRING, c_void_p]

__ssize_t = c_long
ssize_t = __ssize_t
__read_chk = csynclib.__read_chk
__read_chk.restype = ssize_t
__read_chk.argtypes = [c_int, c_void_p, size_t, size_t]
read = csynclib.read
read.restype = ssize_t
read.argtypes = [c_int, c_void_p, size_t]
__off_t = c_long
__pread_chk = csynclib.__pread_chk
__pread_chk.restype = ssize_t
__pread_chk.argtypes = [c_int, c_void_p, size_t, __off_t, size_t]
__off64_t = c_long
__pread64_chk = csynclib.__pread64_chk
__pread64_chk.restype = ssize_t
__pread64_chk.argtypes = [c_int, c_void_p, size_t, __off64_t, size_t]
pread = csynclib.pread
pread.restype = ssize_t
pread.argtypes = [c_int, c_void_p, size_t, __off_t]
pread64 = csynclib.pread64
pread64.restype = ssize_t
pread64.argtypes = [c_int, c_void_p, size_t, __off64_t]
__readlink_chk = csynclib.__readlink_chk
__readlink_chk.restype = ssize_t
__readlink_chk.argtypes = [STRING, STRING, size_t, size_t]
readlink = csynclib.readlink
readlink.restype = ssize_t
readlink.argtypes = [STRING, STRING, size_t]
__readlinkat_chk = csynclib.__readlinkat_chk
__readlinkat_chk.restype = ssize_t
__readlinkat_chk.argtypes = [c_int, STRING, STRING, size_t, size_t]
readlinkat = csynclib.readlinkat
readlinkat.restype = ssize_t
readlinkat.argtypes = [c_int, STRING, STRING, size_t]
__getcwd_chk = csynclib.__getcwd_chk
__getcwd_chk.restype = STRING
__getcwd_chk.argtypes = [STRING, size_t, size_t]
getcwd = csynclib.getcwd
getcwd.restype = STRING
getcwd.argtypes = [STRING, size_t]
__getwd_chk = csynclib.__getwd_chk
__getwd_chk.restype = STRING
__getwd_chk.argtypes = [STRING, size_t]
getwd = csynclib.getwd
getwd.restype = STRING
getwd.argtypes = [STRING]
__confstr_chk = csynclib.__confstr_chk
__confstr_chk.restype = size_t
__confstr_chk.argtypes = [c_int, STRING, size_t, size_t]
confstr = csynclib.confstr
confstr.restype = size_t
confstr.argtypes = [c_int, STRING, size_t]
__gid_t = c_uint
__getgroups_chk = csynclib.__getgroups_chk
__getgroups_chk.restype = c_int
__getgroups_chk.argtypes = [c_int, POINTER(__gid_t), size_t]
getgroups = csynclib.getgroups
getgroups.restype = c_int
getgroups.argtypes = [c_int, POINTER(__gid_t)]
__ttyname_r_chk = csynclib.__ttyname_r_chk
__ttyname_r_chk.restype = c_int
__ttyname_r_chk.argtypes = [c_int, STRING, size_t, size_t]
ttyname_r = csynclib.ttyname_r
ttyname_r.restype = c_int
ttyname_r.argtypes = [c_int, STRING, size_t]
__getlogin_r_chk = csynclib.__getlogin_r_chk
__getlogin_r_chk.restype = c_int
__getlogin_r_chk.argtypes = [STRING, size_t, size_t]
getlogin_r = csynclib.getlogin_r
getlogin_r.restype = c_int
getlogin_r.argtypes = [STRING, size_t]
__gethostname_chk = csynclib.__gethostname_chk
__gethostname_chk.restype = c_int
__gethostname_chk.argtypes = [STRING, size_t, size_t]
gethostname = csynclib.gethostname
gethostname.restype = c_int
gethostname.argtypes = [STRING, size_t]
__getdomainname_chk = csynclib.__getdomainname_chk
__getdomainname_chk.restype = c_int
__getdomainname_chk.argtypes = [STRING, size_t, size_t]
getdomainname = csynclib.getdomainname
getdomainname.restype = c_int
getdomainname.argtypes = [STRING, size_t]
getopt = csynclib.getopt
getopt.restype = c_int
getopt.argtypes = [c_int, POINTER(STRING), STRING]
class fd_set(Structure):
	pass
class timeval(Structure):
	pass
select = csynclib.select
select.restype = c_int
select.argtypes = [c_int, POINTER(fd_set), POINTER(fd_set), POINTER(fd_set), POINTER(timeval)]
class timespec(Structure):
	pass
__time_t = c_long
timespec._fields_ = [
	('tv_sec', __time_t),
	('tv_nsec', c_long),
]
class __sigset_t(Structure):
	pass
__sigset_t._fields_ = [
	('__val', c_ulong * 16),
]
pselect = csynclib.pselect
pselect.restype = c_int
pselect.argtypes = [c_int, POINTER(fd_set), POINTER(fd_set), POINTER(fd_set), POINTER(timespec), POINTER(__sigset_t)]
gnu_dev_major = csynclib.gnu_dev_major
gnu_dev_major.restype = c_uint
gnu_dev_major.argtypes = [c_ulonglong]
gnu_dev_minor = csynclib.gnu_dev_minor
gnu_dev_minor.restype = c_uint
gnu_dev_minor.argtypes = [c_ulonglong]
gnu_dev_makedev = csynclib.gnu_dev_makedev
gnu_dev_makedev.restype = c_ulonglong
gnu_dev_makedev.argtypes = [c_uint, c_uint]
access = csynclib.access
access.restype = c_int
access.argtypes = [STRING, c_int]
euidaccess = csynclib.euidaccess
euidaccess.restype = c_int
euidaccess.argtypes = [STRING, c_int]
eaccess = csynclib.eaccess
eaccess.restype = c_int
eaccess.argtypes = [STRING, c_int]
faccessat = csynclib.faccessat
faccessat.restype = c_int
faccessat.argtypes = [c_int, STRING, c_int, c_int]
lseek = csynclib.lseek
lseek.restype = __off_t
lseek.argtypes = [c_int, __off_t, c_int]
lseek64 = csynclib.lseek64
lseek64.restype = __off64_t
lseek64.argtypes = [c_int, __off64_t, c_int]
close = csynclib.close
close.restype = c_int
close.argtypes = [c_int]
write = csynclib.write
write.restype = ssize_t
write.argtypes = [c_int, c_void_p, size_t]
pwrite = csynclib.pwrite
pwrite.restype = ssize_t
pwrite.argtypes = [c_int, c_void_p, size_t, __off_t]
pwrite64 = csynclib.pwrite64
pwrite64.restype = ssize_t
pwrite64.argtypes = [c_int, c_void_p, size_t, __off64_t]
pipe = csynclib.pipe
pipe.restype = c_int
pipe.argtypes = [POINTER(c_int)]
pipe2 = csynclib.pipe2
pipe2.restype = c_int
pipe2.argtypes = [POINTER(c_int), c_int]
alarm = csynclib.alarm
alarm.restype = c_uint
alarm.argtypes = [c_uint]
sleep = csynclib.sleep
sleep.restype = c_uint
sleep.argtypes = [c_uint]
__useconds_t = c_uint
ualarm = csynclib.ualarm
ualarm.restype = __useconds_t
ualarm.argtypes = [__useconds_t, __useconds_t]
usleep = csynclib.usleep
usleep.restype = c_int
usleep.argtypes = [__useconds_t]
pause = csynclib.pause
pause.restype = c_int
pause.argtypes = []
__uid_t = c_uint
chown = csynclib.chown
chown.restype = c_int
chown.argtypes = [STRING, __uid_t, __gid_t]
fchown = csynclib.fchown
fchown.restype = c_int
fchown.argtypes = [c_int, __uid_t, __gid_t]
lchown = csynclib.lchown
lchown.restype = c_int
lchown.argtypes = [STRING, __uid_t, __gid_t]
fchownat = csynclib.fchownat
fchownat.restype = c_int
fchownat.argtypes = [c_int, STRING, __uid_t, __gid_t, c_int]
chdir = csynclib.chdir
chdir.restype = c_int
chdir.argtypes = [STRING]
fchdir = csynclib.fchdir
fchdir.restype = c_int
fchdir.argtypes = [c_int]
get_current_dir_name = csynclib.get_current_dir_name
get_current_dir_name.restype = STRING
get_current_dir_name.argtypes = []
dup = csynclib.dup
dup.restype = c_int
dup.argtypes = [c_int]
dup2 = csynclib.dup2
dup2.restype = c_int
dup2.argtypes = [c_int, c_int]
dup3 = csynclib.dup3
dup3.restype = c_int
dup3.argtypes = [c_int, c_int, c_int]
execve = csynclib.execve
execve.restype = c_int
execve.argtypes = [STRING, POINTER(STRING), POINTER(STRING)]
fexecve = csynclib.fexecve
fexecve.restype = c_int
fexecve.argtypes = [c_int, POINTER(STRING), POINTER(STRING)]
execv = csynclib.execv
execv.restype = c_int
execv.argtypes = [STRING, POINTER(STRING)]
execle = csynclib.execle
execle.restype = c_int
execle.argtypes = [STRING, STRING]
execl = csynclib.execl
execl.restype = c_int
execl.argtypes = [STRING, STRING]
execvp = csynclib.execvp
execvp.restype = c_int
execvp.argtypes = [STRING, POINTER(STRING)]
execlp = csynclib.execlp
execlp.restype = c_int
execlp.argtypes = [STRING, STRING]
execvpe = csynclib.execvpe
execvpe.restype = c_int
execvpe.argtypes = [STRING, POINTER(STRING), POINTER(STRING)]
nice = csynclib.nice
nice.restype = c_int
nice.argtypes = [c_int]
_exit = csynclib._exit
_exit.restype = None
_exit.argtypes = [c_int]
pathconf = csynclib.pathconf
pathconf.restype = c_long
pathconf.argtypes = [STRING, c_int]
fpathconf = csynclib.fpathconf
fpathconf.restype = c_long
fpathconf.argtypes = [c_int, c_int]
sysconf = csynclib.sysconf
sysconf.restype = c_long
sysconf.argtypes = [c_int]
__pid_t = c_int
getpid = csynclib.getpid
getpid.restype = __pid_t
getpid.argtypes = []
getppid = csynclib.getppid
getppid.restype = __pid_t
getppid.argtypes = []
getpgrp = csynclib.getpgrp
getpgrp.restype = __pid_t
getpgrp.argtypes = []
__getpgid = csynclib.__getpgid
__getpgid.restype = __pid_t
__getpgid.argtypes = [__pid_t]
getpgid = csynclib.getpgid
getpgid.restype = __pid_t
getpgid.argtypes = [__pid_t]
setpgid = csynclib.setpgid
setpgid.restype = c_int
setpgid.argtypes = [__pid_t, __pid_t]
setpgrp = csynclib.setpgrp
setpgrp.restype = c_int
setpgrp.argtypes = []
setsid = csynclib.setsid
setsid.restype = __pid_t
setsid.argtypes = []
getsid = csynclib.getsid
getsid.restype = __pid_t
getsid.argtypes = [__pid_t]
getuid = csynclib.getuid
getuid.restype = __uid_t
getuid.argtypes = []
geteuid = csynclib.geteuid
geteuid.restype = __uid_t
geteuid.argtypes = []
getgid = csynclib.getgid
getgid.restype = __gid_t
getgid.argtypes = []
getegid = csynclib.getegid
getegid.restype = __gid_t
getegid.argtypes = []
group_member = csynclib.group_member
group_member.restype = c_int
group_member.argtypes = [__gid_t]
setuid = csynclib.setuid
setuid.restype = c_int
setuid.argtypes = [__uid_t]
setreuid = csynclib.setreuid
setreuid.restype = c_int
setreuid.argtypes = [__uid_t, __uid_t]
seteuid = csynclib.seteuid
seteuid.restype = c_int
seteuid.argtypes = [__uid_t]
setgid = csynclib.setgid
setgid.restype = c_int
setgid.argtypes = [__gid_t]
setregid = csynclib.setregid
setregid.restype = c_int
setregid.argtypes = [__gid_t, __gid_t]
setegid = csynclib.setegid
setegid.restype = c_int
setegid.argtypes = [__gid_t]
getresuid = csynclib.getresuid
getresuid.restype = c_int
getresuid.argtypes = [POINTER(__uid_t), POINTER(__uid_t), POINTER(__uid_t)]
getresgid = csynclib.getresgid
getresgid.restype = c_int
getresgid.argtypes = [POINTER(__gid_t), POINTER(__gid_t), POINTER(__gid_t)]
setresuid = csynclib.setresuid
setresuid.restype = c_int
setresuid.argtypes = [__uid_t, __uid_t, __uid_t]
setresgid = csynclib.setresgid
setresgid.restype = c_int
setresgid.argtypes = [__gid_t, __gid_t, __gid_t]
fork = csynclib.fork
fork.restype = __pid_t
fork.argtypes = []
vfork = csynclib.vfork
vfork.restype = __pid_t
vfork.argtypes = []
ttyname = csynclib.ttyname
ttyname.restype = STRING
ttyname.argtypes = [c_int]
isatty = csynclib.isatty
isatty.restype = c_int
isatty.argtypes = [c_int]
ttyslot = csynclib.ttyslot
ttyslot.restype = c_int
ttyslot.argtypes = []
link = csynclib.link
link.restype = c_int
link.argtypes = [STRING, STRING]
linkat = csynclib.linkat
linkat.restype = c_int
linkat.argtypes = [c_int, STRING, c_int, STRING, c_int]
symlink = csynclib.symlink
symlink.restype = c_int
symlink.argtypes = [STRING, STRING]
symlinkat = csynclib.symlinkat
symlinkat.restype = c_int
symlinkat.argtypes = [STRING, c_int, STRING]
unlink = csynclib.unlink
unlink.restype = c_int
unlink.argtypes = [STRING]
unlinkat = csynclib.unlinkat
unlinkat.restype = c_int
unlinkat.argtypes = [c_int, STRING, c_int]
rmdir = csynclib.rmdir
rmdir.restype = c_int
rmdir.argtypes = [STRING]
tcgetpgrp = csynclib.tcgetpgrp
tcgetpgrp.restype = __pid_t
tcgetpgrp.argtypes = [c_int]
tcsetpgrp = csynclib.tcsetpgrp
tcsetpgrp.restype = c_int
tcsetpgrp.argtypes = [c_int, __pid_t]
getlogin = csynclib.getlogin
getlogin.restype = STRING
getlogin.argtypes = []
setlogin = csynclib.setlogin
setlogin.restype = c_int
setlogin.argtypes = [STRING]
sethostname = csynclib.sethostname
sethostname.restype = c_int
sethostname.argtypes = [STRING, size_t]
sethostid = csynclib.sethostid
sethostid.restype = c_int
sethostid.argtypes = [c_long]
setdomainname = csynclib.setdomainname
setdomainname.restype = c_int
setdomainname.argtypes = [STRING, size_t]
vhangup = csynclib.vhangup
vhangup.restype = c_int
vhangup.argtypes = []
revoke = csynclib.revoke
revoke.restype = c_int
revoke.argtypes = [STRING]
profil = csynclib.profil
profil.restype = c_int
profil.argtypes = [POINTER(c_ushort), size_t, size_t, c_uint]
acct = csynclib.acct
acct.restype = c_int
acct.argtypes = [STRING]
getusershell = csynclib.getusershell
getusershell.restype = STRING
getusershell.argtypes = []
endusershell = csynclib.endusershell
endusershell.restype = None
endusershell.argtypes = []
setusershell = csynclib.setusershell
setusershell.restype = None
setusershell.argtypes = []
daemon = csynclib.daemon
daemon.restype = c_int
daemon.argtypes = [c_int, c_int]
chroot = csynclib.chroot
chroot.restype = c_int
chroot.argtypes = [STRING]
getpass = csynclib.getpass
getpass.restype = STRING
getpass.argtypes = [STRING]
fsync = csynclib.fsync
fsync.restype = c_int
fsync.argtypes = [c_int]
gethostid = csynclib.gethostid
gethostid.restype = c_long
gethostid.argtypes = []
sync = csynclib.sync
sync.restype = None
sync.argtypes = []
getpagesize = csynclib.getpagesize
getpagesize.restype = c_int
getpagesize.argtypes = []
getdtablesize = csynclib.getdtablesize
getdtablesize.restype = c_int
getdtablesize.argtypes = []
truncate = csynclib.truncate
truncate.restype = c_int
truncate.argtypes = [STRING, __off_t]
truncate64 = csynclib.truncate64
truncate64.restype = c_int
truncate64.argtypes = [STRING, __off64_t]
ftruncate = csynclib.ftruncate
ftruncate.restype = c_int
ftruncate.argtypes = [c_int, __off_t]
ftruncate64 = csynclib.ftruncate64
ftruncate64.restype = c_int
ftruncate64.argtypes = [c_int, __off64_t]
brk = csynclib.brk
brk.restype = c_int
brk.argtypes = [c_void_p]
intptr_t = c_long
sbrk = csynclib.sbrk
sbrk.restype = c_void_p
sbrk.argtypes = [intptr_t]
syscall = csynclib.syscall
syscall.restype = c_long
syscall.argtypes = [c_long]
lockf = csynclib.lockf
lockf.restype = c_int
lockf.argtypes = [c_int, c_int, __off_t]
lockf64 = csynclib.lockf64
lockf64.restype = c_int
lockf64.argtypes = [c_int, c_int, __off64_t]
fdatasync = csynclib.fdatasync
fdatasync.restype = c_int
fdatasync.argtypes = [c_int]
swab = csynclib.swab
swab.restype = None
swab.argtypes = [c_void_p, c_void_p, ssize_t]
ctermid = csynclib.ctermid
ctermid.restype = STRING
ctermid.argtypes = [STRING]
time_t = __time_t
uid_t = __uid_t
gid_t = __gid_t
__mode_t = c_uint
mode_t = __mode_t

csync_tree_walk_file_s._fields_ = [
	('path', STRING),
	('modtime', time_t),
	('uid', uid_t),
	('gid', gid_t),
	('mode', mode_t),
	('type', csync_ftw_type_e),
	('instruction', csync_instructions_e),
	('rename_path', STRING),
]
csync_progress_s._fields_ = [
	('kind', csync_notify_type_e),
	('path', STRING),
	("curr_bytes", c_int),
	("file_size", c_int),
	("overall_transmission_size", c_int),
	("current_overall_bytes", c_int),
	("overall_file_count", c_int),
	("current_file_no", c_int),
]
csync_s._fields_ = [
]
__suseconds_t = c_long
timeval._fields_ = [
	('tv_sec', __time_t),
	('tv_usec', __suseconds_t),
]
__fd_mask = c_long
fd_set._fields_ = [
	('fds_bits', __fd_mask * 16),
]

__all__ = ['lseek64', 'lseek',
	'csync_set_log_callback', 'seteuid',
	'isatty', 'execle', 'csync_is_statedb_disabled', 'truncate64',
	'__time_t', 'sleep', 'lockf64',
	'mode_t', '__off64_t', 'size_t', 'csync_walk_local_tree',
	'getegid', 'csync_error_codes_e', 'group_member',
	'get_current_dir_name',
	'csync_update', 'pause', 'csync_set_auth_callback',
	'csync_add_exclude_list', 'getresgid', 'sethostname',
	'fpathconf',
	'__getpgid', 'csync_set_status', 'lchown', 'setgid',
	'csync_get_error', 'getusershell',
	'getlogin',
	'csync_progress_callback', 'intptr_t',
	'csync_walk_remote_tree', 'dup3', 'dup2', 'read',
	'getppid', 'getdomainname',
	'fchown', 'getpgrp',
	'csync_get_error_string',
	'gnu_dev_minor', 'execl', 'readlinkat', 'daemon', 'fsync',
	'csync_set_module_property',
	'tcsetpgrp', 'setreuid', 'csync_destroy',
	'getpagesize', 'setlogin', 'execv', 'nice', 'gnu_dev_makedev', 'ttyname',
	'linkat', 'getlogin_r', '__ssize_t',
	'__confstr_chk',
	'csync_set_config_dir', 'sync',
	'__fd_mask', 'getresuid',
	'fchownat', '__pid_t', 'execlp', 'csync_get_userdata',
	'getgid',
	'__sigset_t',
	'csync_get_log_callback', '__useconds_t',
	'CSYNC', 'csync_get_config_dir',
	'csync_log_callback', 'access',
	'setsid', '__ttyname_r_chk', 'select', 'acct',
	'ualarm',
	'revoke', 'csync_s', '__pread64_chk', 'usleep', 'setpgid',
	'setresgid', 'getcwd', 'symlink', 'pwrite64',
	'__getgroups_chk', 'setregid',
	'fchdir', 'ftruncate', 'setegid',
	'vhangup', 'getsid', 'csync_notify_type_e',
	'symlinkat',
	'pipe2', 'sethostid',
	'fd_set',
	'csync_set_log_verbosity', '_exit', '__readlink_chk',
	'endusershell', 'confstr', 'csync_treewalk_visit_func',
	'__read_chk', '__mode_t', 'swab', 'csync_get_status',
	'getpgid', 'brk', '__off_t', 'gethostid', 'pread',
	'__readlinkat_chk', 'getdtablesize', 'ttyname_r',
	'__gid_t', 'gethostname', 'timespec',
	'faccessat', 'gnu_dev_major', 'rmdir', 'dup',
	'csync_propagate', 'fdatasync',
	'csync_reconcile', '__pread_chk', 'execvpe',
	'csync_ftw_type_e', 'eaccess', 'execvp', 'ftruncate64',
	'__getlogin_r_chk', 'link', 'uid_t',
	'csync_set_progress_callback', '__getcwd_chk', 'pselect',
	'gid_t', 'execve', 'getpass', 'chdir', '__suseconds_t', 'sbrk',
	'__getwd_chk',
	'csync_get_statedb_file', 'setresuid',
	'csync_auth_callback', 'fexecve', 'vfork', 'setuid',
	'fork', 'csync_enable_conflictcopys', 'lockf', 'sysconf',
	'syscall', 'csync_set_iconv_codec', 'getwd',
	'setdomainname', 'pread64', 'euidaccess', 'close',
	'csync_enable_statedb', 
	'csync_instructions_e', 'time_t', '__gethostname_chk',
	'chroot', 'csync_tree_walk_file_s', 'getgroups',
	'TREE_WALK_FILE', 'ssize_t', 'csync_disable_statedb',
	'setpgrp', 'timeval', 'write', 'csync_get_auth_callback', 'getopt',
	'csync_get_log_verbosity', 'pathconf',
	'csync_set_userdata', 'truncate', 
	'CSYNC_ERROR_CODE', 'getpid',
	'setusershell', 'readlink', 'unlink',
	'tcgetpgrp', 'unlinkat', '__getdomainname_chk', 'ttyslot',
	'pwrite', 'getuid', 'csync_create', 'alarm',
	'csync_get_local_only', 'csync_init', 'pipe', 'ctermid',
	'chown',
	'csync_set_local_only', '__uid_t', 'profil', 'geteuid']

# vim: noet:ts=4:sw=4:sts=4

########NEW FILE########
__FILENAME__ = pre
import sys
import os.path
import ctypes.util
import logging
from ctypes import CDLL
from ctypes import c_char_p, c_int

def getCSync():
	logger = logging.getLogger(__name__)
	if os.path.exists('/usr/lib/libocsync.so.0'):
		logger.debug('Found ocsync at %s', '/usr/lib/libocsync.so.0')
		return CDLL('/usr/lib/libocsync.so.0')
	elif os.path.exists('/usr/lib64/libocsync.so.0'):
		logger.debug('Found ocsync at %s', '/usr/lib64/libocsync.so.0')
		return CDLL('/usr/lib64/libocsync.so.0')
	else:
		path = ctypes.util.find_library('ocsync')
		if path:
			logger.debug('Found ocsync at %s', path)
			return CDLL(path)
	logger.critical('Could not find shared library libocsync')
	raise ImportError('Could not find shared library libocsync')


csynclib = getCSync()

csync_version = csynclib.csync_version
csync_version.restype = c_char_p
csync_version.argtypes = [c_int]

__all__ = ['getCSync','csynclib','csync_version']

# vim: noet:ts=4:sw=4:sts=4

########NEW FILE########
__FILENAME__ = v0_70_0

########NEW FILE########
__FILENAME__ = v0_90_0
# values for enumeration 'csync_error_codes_e'
(CSYNC_ERR_NONE,
CSYNC_ERR_LOG,
CSYNC_ERR_LOCK,
CSYNC_ERR_STATEDB_LOAD,
CSYNC_ERR_STATEDB_WRITE,
CSYNC_ERR_MODULE,
CSYNC_ERR_TIMESKEW,
CSYNC_ERR_FILESYSTEM,
CSYNC_ERR_TREE,
CSYNC_ERR_MEM,
CSYNC_ERR_PARAM,
CSYNC_ERR_UPDATE,
CSYNC_ERR_RECONCILE,
CSYNC_ERR_PROPAGATE,
CSYNC_ERR_ACCESS_FAILED,
CSYNC_ERR_REMOTE_CREATE,
CSYNC_ERR_REMOTE_STAT,
CSYNC_ERR_LOCAL_CREATE,
CSYNC_ERR_LOCAL_STAT,
CSYNC_ERR_PROXY,
CSYNC_ERR_LOOKUP,
CSYNC_ERR_AUTH_SERVER,
CSYNC_ERR_AUTH_PROXY,
CSYNC_ERR_CONNECT,
CSYNC_ERR_TIMEOUT,
CSYNC_ERR_HTTP,
CSYNC_ERR_PERM,
CSYNC_ERR_NOT_FOUND,
CSYNC_ERR_EXISTS,
CSYNC_ERR_NOSPC,
CSYNC_ERR_QUOTA,
CSYNC_ERR_SERVICE_UNAVAILABLE,
CSYNC_ERR_FILE_TOO_BIG,
CSYNC_ERR_ABORTED,
CSYNC_ERR_UNSPEC,) =  xrange(35)

# values for enumeration 'csync_ftw_type_e'
(CSYNC_FTW_TYPE_FILE,
CSYNC_FTW_TYPE_SLINK,
CSYNC_FTW_TYPE_DIR,
CSYNC_FTW_TYPE_SKIP,) = xrange(4)

# values for enumeration 'csync_instructions_e'
CSYNC_INSTRUCTION_NONE = 0
CSYNC_INSTRUCTION_EVAL = 1
CSYNC_INSTRUCTION_REMOVE = 2
CSYNC_INSTRUCTION_RENAME = 4
CSYNC_INSTRUCTION_NEW = 8
CSYNC_INSTRUCTION_CONFLICT = 16
CSYNC_INSTRUCTION_IGNORE = 32
CSYNC_INSTRUCTION_SYNC = 64
CSYNC_INSTRUCTION_STAT_ERROR = 128
CSYNC_INSTRUCTION_ERROR = 256
CSYNC_INSTRUCTION_DELETED = 512
CSYNC_INSTRUCTION_UPDATED = 1024

# values for enumeration 'csync_notify_type_e'
(CSYNC_NOTIFY_INVALID,
CSYNC_NOTIFY_START_SYNC_SEQUENCE,
CSYNC_NOTIFY_START_DOWNLOAD,
CSYNC_NOTIFY_START_UPLOAD,
CSYNC_NOTIFY_PROGRESS,
CSYNC_NOTIFY_FINISHED_DOWNLOAD,
CSYNC_NOTIFY_FINISHED_UPLOAD,
CSYNC_NOTIFY_FINISHED_SYNC_SEQUENCE,
CSYNC_NOTIFY_START_DELETE,
CSYNC_NOTIFY_END_DELETE,
CSYNC_NOTIFY_ERROR,) = xrange(11)

(CSYNC_LOG_PRIORITY_NOLOG,
CSYNC_LOG_PRIORITY_FATAL,
CSYNC_LOG_PRIORITY_ALERT,
CSYNC_LOG_PRIORITY_CRIT,
CSYNC_LOG_PRIORITY_ERROR,
CSYNC_LOG_PRIORITY_WARN,
CSYNC_LOG_PRIORITY_NOTICE,
CSYNC_LOG_PRIORITY_INFO,
CSYNC_LOG_PRIORITY_DEBUG,
CSYNC_LOG_PRIORITY_TRACE,
CSYNC_LOG_PRIORITY_NOTSET,
CSYNC_LOG_PRIORITY_UNKNOWN,) = xrange(12)

########NEW FILE########
__FILENAME__ = version
import subprocess
import json
import os
import pkg_resources

verfile = pkg_resources.resource_filename(__name__, 'version.dat')

class ver(object):
	def __init__(self, verfile='version.dat'):
		self.verfile = verfile
		self.loadVersion()
		self.setup()
	def setup(self):
		"""sublass this to do something useful for yourself"""
		pass
	@property
	def asFloat(self):
		return self.version['float']
	@property
	def asString(self):
		return self.version['string']
	@property
	def asHead(self):
		return self.version['head']
	def makeString(self):
		s = str(self.asFloat)
		#s = s.replace('.','_')
		return s
	def makeNpackd(self):
		s = "%.2f" % (self.asFloat)
		return s
	def makeFloat(self, s):
		s = str(s)
		s = s.replace('_', '.')
		f = float(s)
		return f
	def bumpVersion(self, amt=.1):
		newVersion = self.asFloat + amt
		self.setVersion(newVersion)
	def setVersion(self, ver):
		ver = str(ver)
		self.version['float'] = self.makeFloat(ver)
		self.version['string'] = self.makeString()
		self.asNpackd = self.makeNpackd()
		self.saveVersion()
	def loadVersion(self):
		try:
			#ver = open(self.verfile,'r').read()
			ver = json.load(open(self.verfile,'r'))
		except IOError:
			ver = {'float': 0.0, 'string': '0.0' }
		self.version = ver
		#self.asFloat = self.makeFloat(ver['version'])
		#self.asString = self.makeString()
		self.asNpackd = self.makeNpackd()
		return ver
	def saveVersion(self):
		json.dump(self.version,open(self.verfile,'w'))
		#open(self.verfile,'w').write(str(self.asFloat))
		return self.verfile

class hgVersion(ver):
	def getHeadVersion(self):
		"""if hg is around, return the current version and save it
		otherwise return the saved copy, or 00 if not already saved.
		"""
		cmd = "hg heads".split()
		try:
			out = subprocess.check_output(cmd)
		except:
			out = '\n'
		out = out.split('\n',1)
		if 'changeset' in out[0]:
			out = out[0].split()
			ver = out[1]
			self.version['head'] = ver
			self.saveVersion()
		else:
			if self.version.has_key('head'):
				ver = self.version['head']
			else:
				ver = '00'
		return ver
	def setup(self):
		self.getHeadVersion()
	@property
	def asHead(self):
		return self.getHeadVersion()

class gitVersion(ver):
	def getHeadVersion(self):
		"""if git is around, return the current version and save it.
		otherwise return the saved copy, or 00 if not already saved.
		"""
		gitdir = os.path.join(os.path.dirname(os.path.abspath(self.verfile)),'..','.git')
		if not os.path.exists(gitdir):
			if self.version.has_key('head'):
				return self.version['head']
			return '00'
		cmd = 'git rev-parse --verify HEAD'.split()
		try:
			out = subprocess.check_output(cmd)
		except:
			out = '\n'
		out = out.split('\n',1)
		if len(out[0]) > 1:
			ver = out[0]
			self.version['head'] = ver
			self.saveVersion()
		else:
			if self.version.has_key('head'):
				ver = self.version['head']
			else:
				ver = '00'
		return ver
	def setup(self):
		self.getHeadVersion()
	@property
	def asHead(self):
		return self.getHeadVersion()

#BASE_DIR = os.path.abspath(os.path.dirname(__file__))
#if os.path.exists(os.path.join(BASE_DIR, 'devel')):
#    version = gitVersion(os.path.join(BASE_DIR, 'version.dat'))
#else:
#    version = ver(os.path.join(BASE_DIR, 'version.dat'))

version = ver(verfile)

if __name__ == '__main__':
	print 'Testing version.'
	v = hgVersion()
	print 'dict:', v.version
	print 'string:', v.asString
	print 'float:', v.asFloat
	print 'hghead', v.asHead

########NEW FILE########
