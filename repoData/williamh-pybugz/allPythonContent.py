__FILENAME__ = argparsers
import argparse

from bugz import __version__
from bugz.cli import PrettyBugz

def make_attach_parser(subparsers):
	attach_parser = subparsers.add_parser('attach',
		help = 'attach file to a bug')
	attach_parser.add_argument('bugid',
		help = 'the ID of the bug where the file should be attached')
	attach_parser.add_argument('filename',
		help = 'the name of the file to attach')
	attach_parser.add_argument('-c', '--content-type',
		help = 'mimetype of the file e.g. text/plain (default: auto-detect)')
	attach_parser.add_argument('-d', '--description',
		help = 'a long description of the attachment',
		dest = 'comment')
	attach_parser.add_argument('-p', '--patch',
		action = 'store_true',
		help = 'attachment is a patch',
		dest = 'is_patch')
	attach_parser.add_argument('-t', '--title',
		help = 'a short description of the attachment (default: filename).',
		dest = 'summary')
	attach_parser.set_defaults(func = PrettyBugz.attach)

def make_attachment_parser(subparsers):
	attachment_parser = subparsers.add_parser('attachment',
		help = 'get an attachment from bugzilla')
	attachment_parser.add_argument('attachid',
		help = 'the ID of the attachment')
	attachment_parser.add_argument('-v', '--view',
		action="store_true",
		default = False,
		help = 'print attachment rather than save')
	attachment_parser.set_defaults(func = PrettyBugz.attachment)

def make_get_parser(subparsers):
	get_parser = subparsers.add_parser('get',
		help = 'get a bug from bugzilla')
	get_parser.add_argument('bugid',
		help = 'the ID of the bug to retrieve.')
	get_parser.add_argument("-a", "--no-attachments",
		action="store_false",
		default = True,
		help = 'do not show attachments',
		dest = 'attachments')
	get_parser.add_argument("-n", "--no-comments",
		action="store_false",
		default = True,
		help = 'do not show comments',
		dest = 'comments')
	get_parser.set_defaults(func = PrettyBugz.get)

def make_login_parser(subparsers):
	login_parser = subparsers.add_parser('login',
		help = 'log into bugzilla')
	login_parser.set_defaults(func = PrettyBugz.login)

def make_logout_parser(subparsers):
	logout_parser = subparsers.add_parser('logout',
		help = 'log out of bugzilla')
	logout_parser.set_defaults(func = PrettyBugz.logout)

def make_modify_parser(subparsers):
	modify_parser = subparsers.add_parser('modify',
		help = 'modify a bug (eg. post a comment)')
	modify_parser.add_argument('bugid',
		help = 'the ID of the bug to modify')
	modify_parser.add_argument('--alias',
		help = 'change the alias for this bug')
	modify_parser.add_argument('-a', '--assigned-to',
		help = 'change assignee for this bug')
	modify_parser.add_argument('--add-blocked',
		action = 'append',
		help = 'add a bug to the blocked list',
		dest = 'blocks_add')
	modify_parser.add_argument('--remove-blocked',
		action = 'append',
		help = 'remove a bug from the blocked list',
		dest = 'blocks_remove')
	modify_parser.add_argument('--add-dependson',
		action = 'append',
		help = 'add a bug to the depends list',
		dest = 'depends_on_add')
	modify_parser.add_argument('--remove-dependson',
		action = 'append',
		help = 'remove a bug from the depends list',
		dest = 'depends_on_remove')
	modify_parser.add_argument('--add-cc',
		action = 'append',
		help = 'add an email to the CC list',
		dest = 'cc_add')
	modify_parser.add_argument('--remove-cc',
		action = 'append',
		help = 'remove an email from the CC list',
		dest = 'cc_remove')
	modify_parser.add_argument('-c', '--comment',
		help = 'add comment from command line')
	modify_parser.add_argument('-C', '--comment-editor',
		action='store_true',
		help = 'add comment via default editor')
	modify_parser.add_argument('-F', '--comment-from',
		help = 'add comment from file.  If -C is also specified, the editor will be opened with this file as its contents.')
	modify_parser.add_argument('--component',
		help = 'change the component for this bug')
	modify_parser.add_argument('-d', '--duplicate',
		type = int,
		default = 0,
		help = 'this bug is a duplicate',
		dest = 'dupe_of')
	modify_parser.add_argument('--add-group',
		action = 'append',
		help = 'add a group to this bug',
		dest = 'groups_add')
	modify_parser.add_argument('--remove-group',
		action = 'append',
		help = 'remove agroup from this bug',
		dest = 'groups_remove')
	modify_parser.add_argument('--set-keywords',
		action = 'append',
		help = 'set bug keywords',
		dest = 'keywords_set')
	modify_parser.add_argument('--op-sys',
		help = 'change the operating system for this bug')
	modify_parser.add_argument('--platform',
		help = 'change the hardware platform for this bug')
	modify_parser.add_argument('--priority',
		help = 'change the priority for this bug')
	modify_parser.add_argument('--product',
		help = 'change the product for this bug')
	modify_parser.add_argument('-r', '--resolution',
		help = 'set new resolution (only if status = RESOLVED)')
	modify_parser.add_argument('--add-see-also',
		action = 'append',
		help = 'add a "see also" URL to this bug',
		dest = 'see_also_add')
	modify_parser.add_argument('--remove-see-also',
		action = 'append',
		help = 'remove a"see also" URL from this bug',
		dest = 'see_also_remove')
	modify_parser.add_argument('-S', '--severity',
		help = 'set severity for this bug')
	modify_parser.add_argument('-s', '--status',
		help = 'set new status of bug (eg. RESOLVED)')
	modify_parser.add_argument('-t', '--title',
		help = 'set title of bug',
		dest = 'summary')
	modify_parser.add_argument('-U', '--url',
		help = 'set URL field of bug')
	modify_parser.add_argument('-v', '--version',
		help = 'set the version for this bug'),
	modify_parser.add_argument('-w', '--whiteboard',
		help = 'set Status whiteboard'),
	modify_parser.add_argument('--fixed',
		action='store_true',
		help = 'mark bug as RESOLVED, FIXED')
	modify_parser.add_argument('--invalid',
		action='store_true',
		help = 'mark bug as RESOLVED, INVALID')
	modify_parser.set_defaults(func = PrettyBugz.modify)

def make_post_parser(subparsers):
	post_parser = subparsers.add_parser('post',
		help = 'post a new bug into bugzilla')
	post_parser.add_argument('--product',
		help = 'product')
	post_parser.add_argument('--component',
		help = 'component')
	post_parser.add_argument('--version',
		help = 'version of the product')
	post_parser.add_argument('-t', '--title',
		help = 'title of bug',
		dest = 'summary')
	post_parser.add_argument('-d', '--description',
		help = 'description of the bug')
	post_parser.add_argument('--op-sys',
		help = 'set the operating system')
	post_parser.add_argument('--platform',
		help = 'set the hardware platform')
	post_parser.add_argument('--priority',
		help = 'set priority for the new bug')
	post_parser.add_argument('-S', '--severity',
		help = 'set the severity for the new bug')
	post_parser.add_argument('--alias',
		help = 'set the alias for this bug')
	post_parser.add_argument('-a', '--assigned-to',
		help = 'assign bug to someone other than the default assignee')
	post_parser.add_argument('--cc',
		help = 'add a list of emails to CC list')
	post_parser.add_argument('-U', '--url',
		help = 'set URL field of bug')
	post_parser.add_argument('-F' , '--description-from',
		help = 'description from contents of file')
	post_parser.add_argument('--append-command',
		help = 'append the output of a command to the description')
	post_parser.add_argument('--batch',
		action="store_true",
		help = 'do not prompt for any values')
	post_parser.add_argument('--default-confirm',
		choices = ['y','Y','n','N'],
		default = 'y',
		help = 'default answer to confirmation question')
	post_parser.set_defaults(func = PrettyBugz.post)

def make_search_parser(subparsers):
	search_parser = subparsers.add_parser('search',
		help = 'search for bugs in bugzilla')
	search_parser.add_argument('terms',
		nargs='*',
		help = 'strings to search for in title and/or body')
	search_parser.add_argument('--alias',
		help='The unique alias for this bug')
	search_parser.add_argument('-a', '--assigned-to',
		help = 'email the bug is assigned to')
	search_parser.add_argument('-C', '--component',
		action='append',
		help = 'restrict by component (1 or more)')
	search_parser.add_argument('-r', '--creator',
		help = 'email of the person who created the bug')
	search_parser.add_argument('-l', '--limit',
		type = int,
		help='Limit the number of records returned in a search')
	search_parser.add_argument('--offset',
		type = int,
		help='Set the start position for a search')
	search_parser.add_argument('--op-sys',
		action='append',
		help = 'restrict by Operating System (one or more)')
	search_parser.add_argument('--platform',
		action='append',
		help = 'restrict by platform (one or more)')
	search_parser.add_argument('--priority',
		action='append',
		help = 'restrict by priority (one or more)')
	search_parser.add_argument('--product',
		action='append',
		help = 'restrict by product (one or more)')
	search_parser.add_argument('--resolution',
		help = 'restrict by resolution')
	search_parser.add_argument('--severity',
		action='append',
		help = 'restrict by severity (one or more)')
	search_parser.add_argument('-s', '--status',
		action='append',
		help = 'restrict by status (one or more, use all for all statuses)')
	search_parser.add_argument('-v', '--version',
		action='append',
		help = 'restrict by version (one or more)')
	search_parser.add_argument('-w', '--whiteboard',
		help = 'status whiteboard')
	search_parser.add_argument('--show-status',
		action = 'store_true',
		help='show status of bugs')
	search_parser.set_defaults(func = PrettyBugz.search)

def make_parser():
	parser = argparse.ArgumentParser(
		epilog = 'use -h after a sub-command for sub-command specific help')
	parser.add_argument('--config-file',
		help = 'read an alternate configuration file')
	parser.add_argument('--connection',
		help = 'use [connection] section of your configuration file')
	parser.add_argument('-b', '--base',
				default = 'https://bugs.gentoo.org/xmlrpc.cgi',
		help = 'base URL of Bugzilla')
	parser.add_argument('-u', '--user',
		help = 'username for commands requiring authentication')
	parser.add_argument('-p', '--password',
		help = 'password for commands requiring authentication')
	parser.add_argument('--passwordcmd',
		help = 'password command to evaluate for commands requiring authentication')
	parser.add_argument('-q', '--quiet',
		action='store_true',
		help = 'quiet mode')
	parser.add_argument('-d', '--debug',
		type=int,
		help = 'debug level (from 0 to 3)')
	parser.add_argument('--columns',
		type = int,
		help = 'maximum number of columns output should use')
	parser.add_argument('--encoding',
		help = 'output encoding (default: utf-8).')
	parser.add_argument('--skip-auth',
		action='store_true',
		help = 'skip Authentication.')
	parser.add_argument('--version',
		action='version',
		help='show program version and exit',
		version='%(prog)s ' + __version__)
	subparsers = parser.add_subparsers(help = 'help for sub-commands')
	make_attach_parser(subparsers)
	make_attachment_parser(subparsers)
	make_get_parser(subparsers)
	make_login_parser(subparsers)
	make_logout_parser(subparsers)
	make_modify_parser(subparsers)
	make_post_parser(subparsers)
	make_search_parser(subparsers)
	return parser

########NEW FILE########
__FILENAME__ = bugzilla
# Author: Mike Gilbert <floppym@gentoo.org>
# This code is released into the public domain.
# As of this writing, the Bugzilla web service is documented at the
# following URL:
# http://www.bugzilla.org/docs/4.2/en/html/api/Bugzilla/WebService.html

import cookielib
import urllib
import urllib2
import xmlrpclib

class RequestTransport(xmlrpclib.Transport):
	def __init__(self, uri, cookiejar=None, use_datetime=0):
		xmlrpclib.Transport.__init__(self, use_datetime=use_datetime)

		self.opener = urllib2.build_opener()

		# Parse auth (user:passwd) from the uri
		urltype, rest = urllib.splittype(uri)
		host, rest = urllib.splithost(rest)
		auth, host = urllib.splituser(host)
		self.uri = urltype + '://' + host + rest

		# Handle HTTP Basic authentication
		if auth is not None:
			user, passwd = urllib.splitpasswd(auth)
			passwdmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
			passwdmgr.add_password(realm=None, uri=self.uri, user=user, passwd=passwd)
			authhandler = urllib2.HTTPBasicAuthHandler(passwdmgr)
			self.opener.add_handler(authhandler)

		# Handle HTTP Cookies
		if cookiejar is not None:
			self.opener.add_handler(urllib2.HTTPCookieProcessor(cookiejar))

	def request(self, host, handler, request_body, verbose=0):
		req = urllib2.Request(self.uri)
		req.add_header('User-Agent', self.user_agent)
		req.add_header('Content-Type', 'text/xml')

		if hasattr(self, 'accept_gzip_encoding') and self.accept_gzip_encoding:
			req.add_header('Accept-Encoding', 'gzip')

		req.add_data(request_body)

		resp = self.opener.open(req)

		# In Python 2, resp is a urllib.addinfourl instance, which does not
		# have the getheader method that parse_response expects.
		if not hasattr(resp, 'getheader'):
			resp.getheader = resp.headers.getheader

		if resp.code == 200:
			self.verbose = verbose
			return self.parse_response(resp)

		resp.close()
		raise xmlrpclib.ProtocolError(self.uri, resp.status, resp.reason, resp.msg)

class BugzillaProxy(xmlrpclib.ServerProxy):
	def __init__(self, uri, encoding=None, verbose=0, allow_none=0,
			use_datetime=0, cookiejar=None):

		if cookiejar is None:
			cookiejar = cookielib.CookieJar()

		transport = RequestTransport(use_datetime=use_datetime, uri=uri,
				cookiejar=cookiejar)
		xmlrpclib.ServerProxy.__init__(self, uri=uri, transport=transport,
				encoding=encoding, verbose=verbose, allow_none=allow_none,
				use_datetime=use_datetime)

########NEW FILE########
__FILENAME__ = cli
import commands
import getpass
from cookielib import CookieJar, LWPCookieJar
import locale
import mimetypes
import os
import subprocess
import re
import sys
import tempfile
import textwrap
import xmlrpclib

try:
	import readline
except ImportError:
	readline = None

from bugz.bugzilla import BugzillaProxy
from bugz.errhandling import BugzError
from bugz.log import log_info

BUGZ_COMMENT_TEMPLATE = \
"""
BUGZ: ---------------------------------------------------
%s
BUGZ: Any line beginning with 'BUGZ:' will be ignored.
BUGZ: ---------------------------------------------------
"""

DEFAULT_COOKIE_FILE = '.bugz_cookie'
DEFAULT_NUM_COLS = 80

#
# Auxiliary functions
#

def get_content_type(filename):
	return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

def raw_input_block():
	""" Allows multiple line input until a Ctrl+D is detected.

	@rtype: string
	"""
	target = ''
	while True:
		try:
			line = raw_input()
			target += line + '\n'
		except EOFError:
			return target

#
# This function was lifted from Bazaar 1.9.
#
def terminal_width():
	"""Return estimated terminal width."""
	if sys.platform == 'win32':
		return win32utils.get_console_size()[0]
	width = DEFAULT_NUM_COLS
	try:
		import struct, fcntl, termios
		s = struct.pack('HHHH', 0, 0, 0, 0)
		x = fcntl.ioctl(1, termios.TIOCGWINSZ, s)
		width = struct.unpack('HHHH', x)[1]
	except IOError:
		pass
	if width <= 0:
		try:
			width = int(os.environ['COLUMNS'])
		except:
			pass
	if width <= 0:
		width = DEFAULT_NUM_COLS

	return width

def launch_editor(initial_text, comment_from = '',comment_prefix = 'BUGZ:'):
	"""Launch an editor with some default text.

	Lifted from Mercurial 0.9.
	@rtype: string
	"""
	(fd, name) = tempfile.mkstemp("bugz")
	f = os.fdopen(fd, "w")
	f.write(comment_from)
	f.write(initial_text)
	f.close()

	editor = (os.environ.get("BUGZ_EDITOR") or
			os.environ.get("EDITOR"))
	if editor:
		result = os.system("%s \"%s\"" % (editor, name))
		if result != 0:
			raise RuntimeError('Unable to launch editor: %s' % editor)

		new_text = open(name).read()
		new_text = re.sub('(?m)^%s.*\n' % comment_prefix, '', new_text)
		os.unlink(name)
		return new_text

	return ''

def block_edit(comment, comment_from = ''):
	editor = (os.environ.get('BUGZ_EDITOR') or
			os.environ.get('EDITOR'))

	if not editor:
		print comment + ': (Press Ctrl+D to end)'
		new_text = raw_input_block()
		return new_text

	initial_text = '\n'.join(['BUGZ: %s'%line for line in comment.split('\n')])
	new_text = launch_editor(BUGZ_COMMENT_TEMPLATE % initial_text, comment_from)

	if new_text.strip():
		return new_text
	else:
		return ''

class PrettyBugz:
	def __init__(self, args):
		self.columns = args.columns or terminal_width()
		self.user = args.user
		self.password = args.password
		self.passwordcmd = args.passwordcmd
		self.skip_auth = args.skip_auth

		cookie_file = os.path.join(os.environ['HOME'], DEFAULT_COOKIE_FILE)
		self.cookiejar = LWPCookieJar(cookie_file)

		try:
			self.cookiejar.load()
		except IOError:
			pass

		if getattr(args, 'encoding'):
			self.enc = args.encoding
		else:
			try:
				self.enc = locale.getdefaultlocale()[1]
			except:
				self.enc = 'utf-8'
			if not self.enc:
				self.enc = 'utf-8'

		log_info("Using %s " % args.base)
		self.bz = BugzillaProxy(args.base, cookiejar=self.cookiejar)

	def get_input(self, prompt):
		return raw_input(prompt)

	def bzcall(self, method, *args):
		"""Attempt to call method with args. Log in if authentication is required.
		"""
		try:
			return method(*args)
		except xmlrpclib.Fault, fault:
			# Fault code 410 means login required
			if fault.faultCode == 410 and not self.skip_auth:
				self.login()
				return method(*args)
			raise

	def login(self, args=None):
		"""Authenticate a session.
		"""
		# prompt for username if we were not supplied with it
		if not self.user:
			log_info('No username given.')
			self.user = self.get_input('Username: ')

		# prompt for password if we were not supplied with it
		if not self.password:
			if not self.passwordcmd:
				log_info('No password given.')
				self.password = getpass.getpass()
			else:
				process = subprocess.Popen(self.passwordcmd.split(), shell=False,
					stdout=subprocess.PIPE)
				self.password, _ = process.communicate()

		# perform login
		params = {}
		params['login'] = self.user
		params['password'] = self.password
		if args is not None:
			params['remember'] = True
		log_info('Logging in')
		try:
			self.bz.User.login(params)
		except xmlrpclib.Fault as fault:
			raise BugzError("Can't login: " + fault.faultString)

		if args is not None:
			self.cookiejar.save()
			os.chmod(self.cookiejar.filename, 0600)

	def logout(self, args):
		log_info('logging out')
		try:
			self.bz.User.logout()
		except xmlrpclib.Fault as fault:
			raise BugzError("Failed to logout: " + fault.faultString)

	def search(self, args):
		"""Performs a search on the bugzilla database with the keywords given on the title (or the body if specified).
		"""
		valid_keys = ['alias', 'assigned_to', 'component', 'creator',
			'limit', 'offset', 'op_sys', 'platform',
			'priority', 'product', 'resolution',
			'severity', 'status', 'version', 'whiteboard']

		search_opts = sorted([(opt, val) for opt, val in args.__dict__.items()
			if val is not None and opt in valid_keys])

		params = {}
		for key in args.__dict__.keys():
			if key in valid_keys and getattr(args, key) is not None:
				params[key] = getattr(args, key)
		if getattr(args, 'terms'):
			params['summary'] = args.terms

		search_term = ' '.join(args.terms).strip()

		if not (params or search_term):
			raise BugzError('Please give search terms or options.')

		if search_term:
			log_msg = 'Searching for \'%s\' ' % search_term
		else:
			log_msg = 'Searching for bugs '

		if search_opts:
			log_info(log_msg + 'with the following options:')
			for opt, val in search_opts:
				log_info('   %-20s = %s' % (opt, val))
		else:
			log_info(log_msg)

		if not 'status' in params.keys():
			params['status'] = ['CONFIRMED', 'IN_PROGRESS', 'UNCONFIRMED']
		elif 'ALL' in params['status']:
			del params['status']

		result = self.bzcall(self.bz.Bug.search, params)['bugs']

		if not len(result):
			log_info('No bugs found.')
		else:
			self.listbugs(result, args.show_status)

	def get(self, args):
		""" Fetch bug details given the bug id """
		log_info('Getting bug %s ..' % args.bugid)
		try:
			result = self.bzcall(self.bz.Bug.get, {'ids':[args.bugid]})
		except xmlrpclib.Fault as fault:
			raise BugzError("Can't get bug #" + str(args.bugid) + ": " \
					+ fault.faultString)

		for bug in result['bugs']:
			self.showbuginfo(bug, args.attachments, args.comments)

	def post(self, args):
		"""Post a new bug"""

		# load description from file if possible
		if args.description_from is not None:
			try:
					if args.description_from == '-':
						args.description = sys.stdin.read()
					else:
						args.description = open( args.description_from, 'r').read()
			except IOError, e:
				raise BugzError('Unable to read from file: %s: %s' %
					(args.description_from, e))

		if not args.batch:
			log_info('Press Ctrl+C at any time to abort.')

			#
			#  Check all bug fields.
			#  XXX: We use "if not <field>" for mandatory fields
			#       and "if <field> is None" for optional ones.
			#

			# check for product
			if not args.product:
				while not args.product or len(args.product) < 1:
					args.product = self.get_input('Enter product: ')
			else:
				log_info('Enter product: %s' % args.product)

			# check for component
			if not args.component:
				while not args.component or len(args.component) < 1:
					args.component = self.get_input('Enter component: ')
			else:
				log_info('Enter component: %s' % args.component)

			# check for version
			# FIXME: This default behaviour is not too nice.
			if not args.version:
				line = self.get_input('Enter version (default: unspecified): ')
				if len(line):
					args.version = line
				else:
					args.version = 'unspecified'
			else:
				log_info('Enter version: %s' % args.version)

			# check for title
			if not args.summary:
				while not args.summary or len(args.summary) < 1:
					args.summary = self.get_input('Enter title: ')
			else:
				log_info('Enter title: %s' % args.summary)

			# check for description
			if not args.description:
				line = block_edit('Enter bug description: ')
				if len(line):
					args.description = line
			else:
				log_info('Enter bug description: %s' % args.description)

			# check for operating system
			if not args.op_sys:
				op_sys_msg = 'Enter operating system where this bug occurs: '
				line = self.get_input(op_sys_msg)
				if len(line):
					args.op_sys = line
			else:
				log_info('Enter operating system: %s' % args.op_sys)

			# check for platform
			if not args.platform:
				platform_msg = 'Enter hardware platform where this bug occurs: '
				line = self.get_input(platform_msg)
				if len(line):
					args.platform = line
			else:
				log_info('Enter hardware platform: %s' % args.platform)

			# check for default priority
			if args.priority is None:
				priority_msg ='Enter priority (eg. Normal) (optional): '
				line = self.get_input(priority_msg)
				if len(line):
					args.priority = line
			else:
				log_info('Enter priority (optional): %s' % args.priority)

			# check for default severity
			if args.severity is None:
				severity_msg ='Enter severity (eg. normal) (optional): '
				line = self.get_input(severity_msg)
				if len(line):
					args.severity = line
			else:
				log_info('Enter severity (optional): %s' % args.severity)

			# check for default alias
			if args.alias is None:
				alias_msg ='Enter an alias for this bug (optional): '
				line = self.get_input(alias_msg)
				if len(line):
					args.alias = line
			else:
				log_info('Enter alias (optional): %s' % args.alias)

			# check for default assignee
			if args.assigned_to is None:
				assign_msg ='Enter assignee (eg. liquidx@gentoo.org) (optional): '
				line = self.get_input(assign_msg)
				if len(line):
					args.assigned_to = line
			else:
				log_info('Enter assignee (optional): %s' % args.assigned_to)

			# check for CC list
			if args.cc is None:
				cc_msg = 'Enter a CC list (comma separated) (optional): '
				line = self.get_input(cc_msg)
				if len(line):
					args.cc = line.split(', ')
			else:
				log_info('Enter a CC list (optional): %s' % args.cc)

			# check for URL
			if args.url is None:
				url_msg = 'Enter a URL (optional): '
				line = self.get_input(url_msg)
				if len(line):
					args.url = line
			else:
				log_info('Enter a URL (optional): %s' % args.url)

			# fixme: groups

			# fixme: status

			# fixme: milestone

			if args.append_command is None:
				args.append_command = self.get_input('Append the output of the following command (leave blank for none): ')
			else:
				log_info('Append command (optional): %s' % args.append_command)

		# raise an exception if mandatory fields are not specified.
		if args.product is None:
			raise RuntimeError('Product not specified')
		if args.component is None:
			raise RuntimeError('Component not specified')
		if args.summary is None:
			raise RuntimeError('Title not specified')
		if args.description is None:
			raise RuntimeError('Description not specified')

		if not args.version:
			args.version = 'unspecified'

		# append the output from append_command to the description
		if args.append_command is not None and args.append_command != '':
			append_command_output = commands.getoutput(args.append_command)
			args.description = args.description + '\n\n' + '$ ' + args.append_command + '\n' +  append_command_output

		# print submission confirmation
		print '-' * (self.columns - 1)
		print '%-12s: %s' % ('Product', args.product)
		print '%-12s: %s' %('Component', args.component)
		print '%-12s: %s' % ('Title', args.summary)
		print '%-12s: %s' % ('Version', args.version)
		print '%-12s: %s' % ('Description', args.description)
		print '%-12s: %s' % ('Operating System', args.op_sys)
		print '%-12s: %s' % ('Platform', args.platform)
		print '%-12s: %s' % ('Priority', args.priority)
		print '%-12s: %s' % ('Severity', args.severity)
		print '%-12s: %s' % ('Alias', args.alias)
		print '%-12s: %s' % ('Assigned to', args.assigned_to)
		print '%-12s: %s' % ('CC', args.cc)
		print '%-12s: %s' % ('URL', args.url)
		# fixme: groups
		# fixme: status
		# fixme: Milestone
		print '-' * (self.columns - 1)

		if not args.batch:
			if args.default_confirm in ['Y','y']:
				confirm = raw_input('Confirm bug submission (Y/n)? ')
			else:
				confirm = raw_input('Confirm bug submission (y/N)? ')
			if len(confirm) < 1:
				confirm = args.default_confirm
			if confirm[0] not in ('y', 'Y'):
				log_info('Submission aborted')
				return

		params={}
		params['product'] = args.product
		params['component'] = args.component
		params['version'] = args.version
		params['summary'] = args.summary
		if args.description is not None:
			params['description'] = args.description
		if args.op_sys is not None:
			params['op_sys'] = args.op_sys
		if args.platform is not None:
			params['platform'] = args.platform
		if args.priority is not None:
			params['priority'] = args.priority
		if args.severity is not None:
			params['severity'] = args.severity
		if args.alias is not None:
			params['alias'] = args.alias
		if args.assigned_to is not None:
			params['assigned_to'] = args.assigned_to
		if args.cc is not None:
			params['cc'] = args.cc
		if args.url is not None:
			params['url'] = args.url

		result = self.bzcall(self.bz.Bug.create, params)
		log_info('Bug %d submitted' % result['id'])

	def modify(self, args):
		"""Modify an existing bug (eg. adding a comment or changing resolution.)"""
		if args.comment_from:
			try:
				if args.comment_from == '-':
					args.comment = sys.stdin.read()
				else:
					args.comment = open(args.comment_from, 'r').read()
			except IOError, e:
				raise BugzError('unable to read file: %s: %s' % \
					(args.comment_from, e))

		if args.comment_editor:
			args.comment = block_edit('Enter comment:')

		params = {}
		if args.blocks_add is not None or args.blocks_remove is not None:
			params['blocks'] = {}
		if args.depends_on_add is not None \
			or args.depends_on_remove is not None:
			params['depends_on'] = {}
		if args.cc_add is not None or args.cc_remove is not None:
			params['cc'] = {}
		if args.comment is not None:
			params['comment'] = {}
		if args.groups_add is not None or args.groups_remove is not None:
			params['groups'] = {}
		if args.keywords_set is not None:
			params['keywords'] = {}
		if args.see_also_add is not None or args.see_also_remove is not None:
			params['see_also'] = {}

		params['ids'] = [args.bugid]
		if args.alias is not None:
			params['alias'] = args.alias
		if args.assigned_to is not None:
			params['assigned_to'] = args.assigned_to
		if args.blocks_add is not None:
			params['blocks']['add'] = args.blocks_add
		if args.blocks_remove is not None:
			params['blocks']['remove'] = args.blocks_remove
		if args.depends_on_add is not None:
			params['depends_on']['add'] = args.depends_on_add
		if args.depends_on_remove is not None:
			params['depends_on']['remove'] = args.depends_on_remove
		if args.cc_add is not None:
			params['cc']['add'] = args.cc_add
		if args.cc_remove is not None:
			params['cc']['remove'] = args.cc_remove
		if args.comment is not None:
			params['comment']['body'] = args.comment
		if args.component is not None:
			params['component'] = args.component
		if args.dupe_of:
			params['dupe_of'] = args.dupe_of
			args.status = None
			args.resolution = None
		if args.groups_add is not None:
			params['groups']['add'] = args.groups_add
		if args.groups_remove is not None:
			params['groups']['remove'] = args.groups_remove
		if args.keywords_set is not None:
			params['keywords']['set'] = args.keywords_set
		if args.op_sys is not None:
			params['op_sys'] = args.op_sys
		if args.platform is not None:
			params['platform'] = args.platform
		if args.priority is not None:
			params['priority'] = args.priority
		if args.product is not None:
			params['product'] = args.product
		if args.resolution is not None:
			params['resolution'] = args.resolution
		if args.see_also_add is not None:
			params['see_also']['add'] = args.see_also_add
		if args.see_also_remove is not None:
			params['see_also']['remove'] = args.see_also_remove
		if args.severity is not None:
			params['severity'] = args.severity
		if args.status is not None:
			params['status'] = args.status
		if args.summary is not None:
			params['summary'] = args.summary
		if args.url is not None:
			params['url'] = args.url
		if args.version is not None:
			params['version'] = args.version
		if args.whiteboard is not None:
			params['whiteboard'] = args.whiteboard

		if args.fixed:
			params['status'] = 'RESOLVED'
			params['resolution'] = 'FIXED'

		if args.invalid:
			params['status'] = 'RESOLVED'
			params['resolution'] = 'INVALID'

		if len(params) < 2:
			raise BugzError('No changes were specified')
		result = self.bzcall(self.bz.Bug.update, params)
		for bug in result['bugs']:
			changes = bug['changes']
			if not len(changes):
				log_info('Added comment to bug %s' % bug['id'])
			else:
				log_info('Modified the following fields in bug %s' % bug['id'])
				for key in changes.keys():
					log_info('%-12s: removed %s' %(key, changes[key]['removed']))
					log_info('%-12s: added %s' %(key, changes[key]['added']))

	def attachment(self, args):
		""" Download or view an attachment given the id."""
		log_info('Getting attachment %s' % args.attachid)

		params = {}
		params['attachment_ids'] = [args.attachid]
		result = self.bzcall(self.bz.Bug.attachments, params)
		result = result['attachments'][args.attachid]

		action = {True:'Viewing', False:'Saving'}
		log_info('%s attachment: "%s"' %
			(action[args.view], result['file_name']))
		safe_filename = os.path.basename(re.sub(r'\.\.', '',
												result['file_name']))

		if args.view:
			print result['data'].data
		else:
			if os.path.exists(result['file_name']):
				raise RuntimeError('Filename already exists')

			fd = open(safe_filename, 'wb')
			fd.write(result['data'].data)
			fd.close()

	def attach(self, args):
		""" Attach a file to a bug given a filename. """
		filename = args.filename
		content_type = args.content_type
		bugid = args.bugid
		summary = args.summary
		is_patch = args.is_patch
		comment = args.comment

		if not os.path.exists(filename):
			raise BugzError('File not found: %s' % filename)

		if content_type is None:
			content_type = get_content_type(filename)

		if comment is None:
			comment = block_edit('Enter optional long description of attachment')

		if summary is None:
			summary = os.path.basename(filename)

		params = {}
		params['ids'] = [bugid]

		fd = open(filename, 'rb')
		params['data'] = xmlrpclib.Binary(fd.read())
		fd.close()

		params['file_name'] = os.path.basename(filename)
		params['summary'] = summary
		if not is_patch:
			params['content_type'] = content_type;
		params['comment'] = comment
		params['is_patch'] = is_patch
		result =  self.bzcall(self.bz.Bug.add_attachment, params)
		log_info("'%s' has been attached to bug %s" % (filename, bugid))

	def listbugs(self, buglist, show_status=False):
		for bug in buglist:
			bugid = bug['id']
			status = bug['status']
			assignee = bug['assigned_to'].split('@')[0]
			desc = bug['summary']
			line = '%s' % (bugid)
			if show_status:
				line = '%s %-12s' % (line, status)
			line = '%s %-20s' % (line, assignee)
			line = '%s %s' % (line, desc)

			try:
				print line.encode(self.enc)[:self.columns]
			except UnicodeDecodeError:
				print line[:self.columns]

		log_info("%i bug(s) found." % len(buglist))

	def showbuginfo(self, bug, show_attachments, show_comments):
		FIELDS = (
			('summary', 'Title'),
			('assigned_to', 'Assignee'),
			('creation_time', 'Reported'),
			('last_change_time', 'Updated'),
			('status', 'Status'),
			('resolution', 'Resolution'),
			('url', 'URL'),
			('severity', 'Severity'),
			('priority', 'Priority'),
			('creator', 'Reporter'),
		)

		MORE_FIELDS = (
			('product', 'Product'),
			('component', 'Component'),
			('whiteboard', 'Whiteboard'),
		)

		for field, name in FIELDS + MORE_FIELDS:
			try:
				value = bug[field]
				if value is None or value == '':
						continue
			except AttributeError:
				continue
			print '%-12s: %s' % (name, value)

		# print keywords
		k = ', '.join(bug['keywords'])
		if k:
			print '%-12s: %s' % ('Keywords', k)

		# Print out the cc'ed people
		cced = bug['cc']
		for cc in cced:
			print '%-12s: %s' %  ('CC', cc)

		# print out depends
		dependson = ', '.join(["%s" % x for x in bug['depends_on']])
		if dependson:
			print '%-12s: %s' % ('DependsOn', dependson)
		blocked = ', '.join(["%s" % x for x in bug['blocks']])
		if blocked:
			print '%-12s: %s' % ('Blocked', blocked)

		bug_comments = self.bzcall(self.bz.Bug.comments, {'ids':[bug['id']]})
		bug_comments = bug_comments['bugs']['%s' % bug['id']]['comments']
		print '%-12s: %d' % ('Comments', len(bug_comments))

		bug_attachments = self.bzcall(self.bz.Bug.attachments, {'ids':[bug['id']]})
		bug_attachments = bug_attachments['bugs']['%s' % bug['id']]
		print '%-12s: %d' % ('Attachments', len(bug_attachments))
		print

		if show_attachments:
			for attachment in bug_attachments:
				aid = attachment['id']
				desc = attachment['summary']
				when = attachment['creation_time']
				print '[Attachment] [%s] [%s]' % (aid, desc.encode(self.enc))

		if show_comments:
			i = 0
			wrapper = textwrap.TextWrapper(width = self.columns,
				break_long_words = False,
				break_on_hyphens = False)
			for comment in bug_comments:
				who = comment['creator']
				when = comment['time']
				what = comment['text']
				print '\n[Comment #%d] %s : %s' % (i, who, when)
				print '-' * (self.columns - 1)

				if what is None:
					what = ''

				# print wrapped version
				for line in what.split('\n'):
					if len(line) < self.columns:
						print line.encode(self.enc)
					else:
						for shortline in wrapper.wrap(line):
							print shortline.encode(self.enc)
				i += 1
			print

########NEW FILE########
__FILENAME__ = configfile
import ConfigParser
import os
import sys

from bugz.log import log_error

DEFAULT_CONFIG_FILE = '~/.bugzrc'

def config_option(parser, get, section, option):
	if parser.has_option(section, option):
		try:
			if get(section, option) != '':
				return get(section, option)
			else:
				log_error("Error: "+option+" is not set")
				sys.exit(1)
		except ValueError, e:
			log_error("Error: option "+option+
					" is not in the right format: "+str(e))
			sys.exit(1)

def fill_config_option(args, parser, get, section, option):
	value = config_option(parser, get, section, option)
	if value is not None:
		setattr(args, option, value)

def fill_config(args, parser, section):
	fill_config_option(args, parser, parser.get, section, 'base')
	fill_config_option(args, parser, parser.get, section, 'user')
	fill_config_option(args, parser, parser.get, section, 'password')
	fill_config_option(args, parser, parser.get, section, 'passwordcmd')
	fill_config_option(args, parser, parser.getint, section, 'columns')
	fill_config_option(args, parser, parser.get, section, 'encoding')
	fill_config_option(args, parser, parser.getboolean, section, 'quiet')

def get_config(args):
	config_file = getattr(args, 'config_file')
	if config_file is None:
			config_file = DEFAULT_CONFIG_FILE
	section = getattr(args, 'connection')
	parser = ConfigParser.ConfigParser()
	config_file_name = os.path.expanduser(config_file)

	# try to open config file
	try:
		file = open(config_file_name)
	except IOError:
		if getattr(args, 'config_file') is not None:
			log_error("Error: Can't find user configuration file: "
					+config_file_name)
			sys.exit(1)
		else:
			return

	# try to parse config file
	try:
		parser.readfp(file)
		sections = parser.sections()
	except ConfigParser.ParsingError, e:
		log_error("Error: Can't parse user configuration file: "+str(e))
		sys.exit(1)

	# parse the default section first
	if "default" in sections:
		fill_config(args, parser, "default")
	if section is None:
		section = config_option(parser, parser.get, "default", "connection")

	# parse a specific section
	if section in sections:
		fill_config(args, parser, section)
	elif section is not None:
		log_error("Error: Can't find section ["+section
			+"] in configuration file")
		sys.exit(1)

########NEW FILE########
__FILENAME__ = errhandling
#
# Bugz specific exceptions
#

class BugzError(Exception):
	pass

########NEW FILE########
__FILENAME__ = log
#This module contains a set of common routines for logging messages.
# TODO: use the python's  'logging' feature?

debugLevel = 0
quiet = False

LogSettings = {
	'W' : {
		'sym' : '!',
		'word' : 'Warn',
	},
	'E' : {
		'sym' : '#',
		'word' : 'Error',
	},
	'D' : {
		'sym' : '~',
		'word' : 'Dbg',
	},
	'I' : {
		'sym' : '*',
		'word' : 'Info',
	},
	'!' : {
		'sym' : '!',
		'word' : 'UNKNWN',
	},
}

def log_setQuiet(newQuiet):
	global quiet
	quiet = newQuiet

def log_setDebugLevel(newLevel):
	global debugLevel
	if not newLevel:
		return
	if newLevel > 3:
		log_warn("bad debug level '{0}', using '3'".format(str(newLevel)))
		debugLevel = 3
	else:
		debugLevel = newLevel

def formatOut(msg, id='!'):
	lines = str(msg).split('\n')
	start = True
	sym=LogSettings[id]['sym']
	word=LogSettings[id]['word'] + ":"

	for line in lines:
		print ' ' + sym + ' ' + line

def log_error(string):
	formatOut(string, 'E')
	return

def log_warn(string):
	formatOut(string, 'W')
	return

def log_info(string):
	# debug implies info
	if not quiet or debugLevel:
		formatOut(string, 'I')
	return

def log_debug(string, msgLevel=1):
	if debugLevel >= msgLevel:
		formatOut(string, 'D')
	return

########NEW FILE########
