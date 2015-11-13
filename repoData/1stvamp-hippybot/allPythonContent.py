__FILENAME__ = bot
#!/usr/bin/env python
import os
import sys
import codecs
import time
import traceback
import logging
from jabberbot import botcmd, JabberBot, xmpp
from ConfigParser import ConfigParser
from optparse import OptionParser
from inspect import ismethod
from lazy_reload import lazy_reload

from hippybot.hipchat import HipChatApi
from hippybot.daemon.daemon import Daemon

# List of bot commands that can't be registered, as they would conflict with
# internal HippyBot methods
RESERVED_COMMANDS = (
    'api',
)

def do_import(name):
    """Helper function to import a module given it's full path and return the
    module object.
    """
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

class HippyBot(JabberBot):
    """An XMPP/Jabber bot with specific customisations for working with the
    hipchat.com chatroom/IM service.
    """

    _content_commands = {}
    _global_commands = []
    _command_aliases = {}
    _all_msg_handlers = []
    _last_message = ''
    _last_send_time = time.time()
    _restart = False

    def __init__(self, config):
        self._config = config

        prefix = config['connection']['username'].split('_')[0]
        self._channels = [u"%s_%s@%s" % (prefix, c.strip().lower().replace(' ',
                '_'), 'conf.hipchat.com') for c in
                config['connection']['channels'].split('\n')]

        username = u"%s@chat.hipchat.com" % (config['connection']['username'],)
        # Set this here as JabberBot sets username as private
        self._username = username
        super(HippyBot, self).__init__(username=username,
                                        password=config['connection']['password'])
        # Make sure we don't timeout after 150s
        self.PING_FREQUENCY = 50

        for channel in self._channels:
            self.join_room(channel, config['connection']['nickname'])

        self._at_name = u"@%s " % (config['connection']['nickname'].replace(" ",""),)
        self._at_short_name = u"@%s " % (config['connection']['nickname']
                                        .split(' ')[0].lower(),)

        plugins = config.get('plugins', {}).get('load', [])
        if plugins:
            plugins = plugins.strip().split('\n')
        self._plugin_modules = plugins
        self._plugins = {}

        self.load_plugins()

        self.log.setLevel(logging.INFO)

    def from_bot(self, mess):
        """Helper method to test if a message was sent from this bot.
        """
        if unicode(mess.getFrom()).endswith("/%s" % (
                        self._config['connection']['nickname'],)):
            return True
        else:
            return False

    def to_bot(self, mess):
        """Helper method to test if a message was directed at this bot.
        Returns a tuple of a flag set to True if the message was to the bot,
        and the message strip without the "at" part.
        """
        respond_to_all = self._config.get('hipchat', {}).get(
            'respond_to_all', False
            )
        to = True
        if (respond_to_all and mess.startswith('@all ')):
            mess = mess[5:]
        elif mess.startswith(self._at_short_name):
            mess = mess[len(self._at_short_name):]
        elif mess.lower().startswith(self._at_name.lower()):
            mess = mess[len(self._at_name):]
        else:
            to = False
        return to, mess

    def send_message(self, mess):
        """Send an XMPP message
        Overridden from jabberbot to update _last_send_time
        """
        self._last_send_time = time.time()
        self.connect().send(mess)

    def callback_message(self, conn, mess):
        """Message handler, this is where we route messages and transform
        direct messages and message aliases into the command that will be
        matched by JabberBot.callback_message() to a registered command.
        """
        self.log.debug("Message: %s" % mess)
        message = unicode(mess.getBody()).strip()
        if not message:
            return

        at_msg, message = self.to_bot(message)

        if len(self._all_msg_handlers) > 0:
            for handler in self._all_msg_handlers:
                try:
                    handler(mess)
                except Exception, e:
                    self.log.exception(
                            'An error happened while processing '
                            'a message ("%s") from %s: %s"' %
                            (mess.getType(), mess.getFrom(),
                                traceback.format_exc(e)))

        if u' ' in message:
            cmd = message.split(u' ')[0]
        else:
            cmd = message

        if cmd in self._command_aliases:
            message = u"%s%s" % (self._command_aliases[cmd],
                                message[len(cmd):])
            cmd = self._command_aliases[cmd]

        ret = None
        if at_msg or cmd in self._global_commands:
            mess.setBody(message)
            ret = super(HippyBot, self).callback_message(conn, mess)
        self._last_message = message
        if ret:
            return ret
        for name in self._content_commands:
            cmd = self._content_commands[name]
            ret = cmd(mess)
            if ret:
                self.send_simple_reply(mess, ret)
                return ret

    def join_room(self, room, username=None, password=None):
        """Overridden from JabberBot to provide history limiting.
        """
        NS_MUC = 'http://jabber.org/protocol/muc'
        if username is None:
            username = self._username.split('@')[0]
        my_room_JID = u'/'.join((room, username))
        pres = xmpp.Presence(to=my_room_JID)
        if password is not None:
            pres.setTag('x',namespace=NS_MUC).setTagData('password',password)
        else:
            pres.setTag('x',namespace=NS_MUC)

        # Don't pull the history back from the server on joining channel
        pres.getTag('x').addChild('history', {'maxchars': '0',
                                                'maxstanzas': '0'})
        self.connect().send(pres)

    def _idle_ping(self):
        """Pings the server, calls on_ping_timeout() on no response.

        To enable set self.PING_FREQUENCY to a value higher than zero.

        Overridden from jabberbot in order to send a single space message
        to HipChat, as XMPP ping doesn't seem to cut it.
        """
        if self.PING_FREQUENCY \
            and time.time() - self._last_send_time > self.PING_FREQUENCY:
            self._last_send_time = time.time()
            self.send_message(' ')

    def rewrite_docstring(self, m):
        if m.__doc__ and m.__doc__.find("@NickName") > -1:
            m.__func__.__doc__ = m.__doc__.replace("@NickName", self._at_name)

    @botcmd(hidden=True)
    def load_plugins(self, mess=None, args=None):
        """Internal handler and bot command to dynamically load and reload
        plugin classes based on the [plugins][load] section of the config.
        """
        for path in self._plugin_modules:
            name = path.split('.')[-1]
            if name in self._plugins:
                lazy_reload(self._plugins[name])
            module = do_import(path)
            self._plugins[name] = module

            # If the module has a function matching the module/command name,
            # then just use that
            command = getattr(module, name, None)

            if not command:
                # Otherwise we're looking for a class called Plugin which
                # provides methods decorated with the @botcmd decorator.
                plugin = getattr(module, 'Plugin')()
                plugin.bot = self
                commands = [c for c in dir(plugin)]
                funcs = []
                content_funcs = []

                for command in commands:
                    m = getattr(plugin, command)
                    if ismethod(m) and getattr(m, '_jabberbot_command', False):
                        if command in RESERVED_COMMANDS:
                            self.log.error('Plugin "%s" attempted to register '
                                        'reserved command "%s", skipping..' % (
                                            plugin, command
                                        ))
                            continue
                        self.rewrite_docstring(m)
                        name = getattr(m, '_jabberbot_command_name', False)
                        self.log.info("command loaded: %s" % name)
                        funcs.append((name, m))

                    if ismethod(m) and getattr(m, '_jabberbot_content_command', False):
                        if command in RESERVED_COMMANDS:
                            self.log.error('Plugin "%s" attempted to register '
                                        'reserved command "%s", skipping..' % (
                                            plugin, command
                                        ))
                            continue
                        self.rewrite_docstring(m)
                        name = getattr(m, '_jabberbot_command_name', False)
                        self.log.info("command loaded: %s" % name)
                        content_funcs.append((name, m))

                # Check for commands that don't need to be directed at
                # hippybot, e.g. they can just be said in the channel
                self._global_commands.extend(getattr(plugin,
                                                'global_commands', []))
                # Check for "special commands", e.g. those that can't be
                # represented in a python method name
                self._command_aliases.update(getattr(plugin,
                                                'command_aliases', {}))

                # Check for handlers for all XMPP message types,
                # this can be used for low-level checking of XMPP messages
                self._all_msg_handlers.extend(getattr(plugin,
                                                'all_msg_handlers', []))
            else:
                funcs = [(name, command)]

            for command, func in funcs:
                setattr(self, command, func)
                self.commands[command] = func
            for command, func in content_funcs:
                setattr(self, command, func)
                self._content_commands[command] = func
        if mess:
            return 'Reloading plugin modules and classes..'

    _api = None
    @property
    def api(self):
        """Accessor for lazy-loaded HipChatApi instance
        """
        if self._api is None:
            auth_token = self._config.get('hipchat', {}).get(
                'api_auth_token', None)
            if auth_token is None:
                self._api = False
            else:
                self._api = HipChatApi(auth_token=auth_token)
        return self._api

class HippyDaemon(Daemon):
    config = None
    def run(self):
        try:
            bot = HippyBot(self.config._sections)
            bot.serve_forever()
        except Exception, e:
            print >> sys.stderr, "ERROR: %s" % (e,)
            print >> sys.stderr, traceback.format_exc()
            return 1
        else:
            return 0

def main():
    import logging
    logging.basicConfig()

    parser = OptionParser(usage="""usage: %prog [options]""")

    parser.add_option("-c", "--config", dest="config_path", help="Config file path")
    parser.add_option("-d", "--daemon", dest="daemonise", help="Run as a"
            " daemon process", action="store_true")
    parser.add_option("-p", "--pid", dest="pid", help="PID file location if"
            " running with --daemon")
    (options, pos_args) = parser.parse_args()

    if not options.config_path:
        print >> sys.stderr, 'ERROR: Missing config file path'
        return 1

    config = ConfigParser()
    config.readfp(codecs.open(os.path.abspath(options.config_path), "r", "utf8"))

    pid = options.pid
    if not pid:
        pid = os.path.abspath(os.path.join(os.path.dirname(
            options.config_path), 'hippybot.pid'))

    runner = HippyDaemon(pid)
    runner.config = config
    if options.daemonise:
        ret = runner.start()
        if ret is None:
            return 0
        else:
            return ret
    else:
        return runner.run()

if __name__ == '__main__':
    sys.exit(main())

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
import signal


class Daemon:
	"""
	A generic daemon class.
	
	Usage: subclass the Daemon class and override the run() method
	"""
	def __init__(self, pidfile, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull, home_dir='.', umask=022, verbose=1):
		self.stdin = stdin
		self.stdout = stdout
		self.stderr = stderr
		self.pidfile = pidfile
		self.home_dir = home_dir
		self.verbose = verbose
		self.umask = umask
		self.daemon_alive = True
	
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
		os.chdir(self.home_dir)
		os.setsid() 
		os.umask(self.umask)
	
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
			if self.stderr:
				se = file(self.stderr, 'a+', 0)
			else:
				se = so
			os.dup2(si.fileno(), sys.stdin.fileno())
			os.dup2(so.fileno(), sys.stdout.fileno())
			os.dup2(se.fileno(), sys.stderr.fileno())

		def sigtermhandler(signum, frame):
			self.daemon_alive = False
		signal.signal(signal.SIGTERM, sigtermhandler)
		signal.signal(signal.SIGINT, sigtermhandler)

		if self.verbose >= 1:
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
		
		if self.verbose >= 1:
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
		
		if self.verbose >= 1:
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
				os.kill(pid, signal.SIGTERM)
				time.sleep(0.1)
		except OSError, err:
			err = str(err)
			if err.find("No such process") > 0:
				if os.path.exists(self.pidfile):
					os.remove(self.pidfile)
			else:
				print str(err)
				sys.exit(1)
		
		if self.verbose >= 1:
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
__FILENAME__ = decorators
from functools import wraps
from jabberbot import botcmd

def directcmd(func):
    @wraps(func)
    def wrapper(self, origin, args):
        message = func(self, origin, args)
        username = unicode(origin.getFrom()).split('/')[1].replace(" ","")
        return u'@%s %s' % (username, message)
    return botcmd(wrapper)

def contentcmd(*args, **kwargs):
    """Decorator for bot commentary"""

    def decorate(func, name=None):
        setattr(func, '_jabberbot_content_command', True)
        setattr(func, '_jabberbot_command_name', name or func.__name__)
        return func

    if len(args):
        return decorate(args[0], **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)

########NEW FILE########
__FILENAME__ = hipchat
import requests
try:
    import simplejson as json
except ImportError:
    import json

GETS = {
    'rooms': (
        'history', 'list', 'show'
    ),
    'users': (
        'list', 'show'
    )
}

POSTS = {
    'rooms': (
        'create', 'delete', 'message'
    ),
    'users': (
        'create', 'delete', 'update'
    )
}

API_VERSION = '1'
BASE_URL = 'https://api.hipchat.com/v%(version)s/%(section)s/%(method)s'

class HipChatApi(object):
    """Lightweight Hipchat.com REST API wrapper
    """
    def __init__(self, auth_token, name=None, gets=GETS, posts=POSTS,
                base_url=BASE_URL, api_version=API_VERSION):
        self._auth_token = auth_token
        self._name = name
        self._gets = gets
        self._posts = posts
        self._base_url = base_url
        self._api_version = api_version

    def _request(self, method, params={}):
        if 'auth_token' not in params:
            params['auth_token'] = self._auth_token
        url = self._base_url % {
            'version': self._api_version,
            'section': self._name,
            'method': method
        }
        if method in self._gets[self._name]:
            r = requests.get(url, params=params)
        elif method in self._posts[self._name]:
            r = requests.post(url, params=params)
        return json.loads(r.content)

    def __getattr__(self, attr_name):
        if self._name is None:
            return super(HipChatApi, self).__self_class__(
                auth_token=self._auth_token,
                name=attr_name
            )
        else:
            def wrapper(*args, **kwargs):
                return self._request(attr_name, *args, **kwargs)
            return wrapper

########NEW FILE########
__FILENAME__ = hype
import random
from hippybot.decorators import botcmd

class Plugin(object):
	@botcmd
	def hype(self, mess, args, **kwargs):
		"""
		Ask NickName to get some hype up into this room.  Sick.
		Format: @NickName hype
		"""
		self.bot.log.info("hype: %s" % mess)
		return select_hype()

def select_hype():
	hype = [
		"/me pumps its fist in the air (Yeah!!)",
		"Gangnam Style!",
		"Sick!",
		"Aaaaay! You know what it is!",
		"Yoooooouuuuu!",
		"Get money!",
		"Ballllllin!",
		"Jeah!",
		"Get it!",
		"/me just popped a bottle",
		"/me is making it rain",
		"/me is getting so low right now"]
	return random.choice(hype)

########NEW FILE########
__FILENAME__ = lockbot
import os
import os.path
import sqlite3dbm
from threading import RLock
from hippybot.hipchat import HipChatApi
from hippybot.decorators import directcmd, botcmd

CONFIG_DIR = os.path.expanduser("~/.techbot")
DB = os.path.expanduser("~/.techbot/techbot.db")

class Plugin(object):
	"""Plugin to handle knewton locking semantics
	"""
	def __init__(self):
		self.rlock = RLock()
		self.db = self.get_db()

	def get_db(self):
		self.create_dir()
		db = sqlite3dbm.sshelve.open(DB)
		return db

	def create_dir(self):
		if not os.path.exists(CONFIG_DIR):
			os.mkdir(CONFIG_DIR)

	@botcmd
	def lock(self, mess, args, **kwargs):
		"""
		Establish a lock over a resource.
		Only you can unlock, but anyone can break.
		Format: @NickName lock <lockname> (message)
		"""
		self.bot.log.info("lock: %s" % mess)
		room, owner, lock, note = self.get_lock_fundamentals(mess)
		try:
			response = self.set_lock(lock, owner, room, note)
			return response
		except Exception, e:
			return str(e)

	@botcmd
	def locks(self, mess, args, **kwargs):
		"""
		Get a list of locks
		Format: @NickName locks (print all locks)
		"""
		self.bot.log.info("locks: %s" % mess)
		return self.get_locks()

	@botcmd
	def unlock(self, mess, args, **kwargs):
		"""
		Release a lock you have over a resource.
		Only the person who established it can unlock it, but anyone can break it.
		Format: @NickName unlock <lockname>
		"""
		self.bot.log.info("unlock: %s" % mess)
		room, owner, lock, _ = self.get_lock_fundamentals(mess)
		try:
			return self.release_lock(lock, owner)
		except Exception, e:
			return str(e)

	@botcmd(name='break')
	def break_lock(self, mess, args, **kwargs):
		"""
		Break a lock someone else has over a resource.
		This is bad, but sadly necessary.
		Format: @NickName break <lockname>
		"""
		self.bot.log.info("break: %s" % mess)
		room, owner, lock, _ = self.get_lock_fundamentals(mess)
		try:
			return self.release_lock(lock, owner, break_lock=True)
		except Exception, e:
			return str(e)

	def get_lock_fundamentals(self, mess):
		room = str(mess.getFrom()).split('/')[0]
		owner = str(mess.getFrom()).split('/')[1]
		body = mess.getBody()
		tokens = body.split(" ")
		tokens.pop(0) # lock
		lock = tokens.pop(0)
		return room, owner, lock, ' '.join(tokens)

	def kill_all_humans(self):
		# For future use
		pass

	def set_lock(self, lock, owner, room, note):
		with self.rlock:
			locks = self.db.get('lock', {})
			if locks.get(lock):
				elock, eowner, enote, eroom = locks.get(lock)
				if eowner != owner:
					raise Exception("Lock already held: \n"
						"    %s: %s (%s)" % (lock, eowner, enote))
			locks[lock] = (lock, owner, note, room)
			self.db['lock'] = locks
			return "Lock established: \n    %s: %s %s" % (
				lock, owner, note)

	def get_locks(self):
		locks = self.db.get('lock', {})
		message = ["Existing Locks:"]
		for lock, owner, note, _ in locks.values():
			message.append("    %s: %s %s" %(
				lock, owner, note))
		if len(message) == 1:
			message.append("    NONE")
		return '\n'.join(message)

	def release_lock(self, lock, owner, break_lock=False):
		with self.rlock:
			locks = self.db.get('lock', {})
			if locks.get(lock):
				elock, eowner, enote, eroom = locks.get(lock)
				if eowner == owner:
					break_lock = False
			else:
				raise Exception("Lock does not exist: \n"
					"    %s" % (lock))
			del locks[lock]
			self.db['lock'] = locks
			if break_lock:
				return "LOCK BROKEN: \n    %s: %s" % (lock, owner)
			else:
				return "Lock released: \n    %s: %s" % (lock, owner)





########NEW FILE########
__FILENAME__ = plusplusbot
import os
import os.path
import re
import sqlite3dbm
from threading import RLock
from hippybot.hipchat import HipChatApi
from hippybot.decorators import botcmd, contentcmd

CONFIG_DIR = os.path.expanduser("~/.techbot")
DB = os.path.expanduser("~/.techbot/score.db")

class Plugin(object):
	"""Plugin to handle knewton replacement of ++ bot in partychatapp
	"""
	def __init__(self):
		self.rlock = RLock()
		self.db = self.get_db()

	def get_db(self):
		self.create_dir()
		db = sqlite3dbm.sshelve.open(DB)
		return db

	def create_dir(self):
		if not os.path.exists(CONFIG_DIR):
			os.mkdir(CONFIG_DIR)

	@contentcmd
	def change_score(self, mess, **kwargs):
		message = mess.getBody()
		if message:
			room = str(mess.getFrom()).split("/")[0]
			user = str(mess.getFrom()).split("/")[1]
			results = []
			if message.find('++') > -1 or message.find('--') > -1:
				self.bot.log.info("plusplusbot: %s" % mess)
			if message.endswith("++") or message.endswith("--"):
				results.extend(self.process_message(message, room, user))
			for m in re.findall("\((.*?)\)", message):
				if m.endswith("++") or m.endswith("--"):
					results.extend(self.process_message(m, room, user))
			if len(results) > 0:
				return "\n".join(results)

	def process_message(self, message, room, user):
		results = []
		victim = message[:-2]
		excl = "woot!"
		plus = 1 
		if message.endswith('--'):
			excl = "ouch!"
			plus = -1
		with self.rlock:
			scores = self.db.get(room, {})
			score = scores.setdefault(victim, 0)
			score += plus
			scores[victim] = score
			self.db[room] = scores
			return ["[%s] %s [%s now at %s]" % (user, victim, excl, score)]

	@botcmd
	def scores(self, mess, args, **kwargs):
		"""
		Prints all scores from this room
		Format: @NickName scores
		"""
		self.bot.log.info("score: %s" % mess)
		room = str(mess.getFrom()).split("/")[0]
		ret = []
		with self.rlock:
			scores = self.db.get(room, {})
			for key in scores:
				ret.append("%s: %s" %(key, scores[key]))
		return '\n'.join(ret)


########NEW FILE########
__FILENAME__ = rot13
from hippybot.decorators import directcmd

class Plugin(object):
    """Plugin to return passed arguments rot13'ed, @'d to the originating user.
    """
    @directcmd
    def rot13(self, mess, args):
        """
        ROT13 the message
        Format: @NickName rot13 <message>
        """
        self.bot.log.info("rot13: %s" % mess)
        return args.encode('rot13')

########NEW FILE########
__FILENAME__ = udefine
import re
import requests
from BeautifulSoup import BeautifulSoup as Soup
from hippybot.hipchat import HipChatApi
from hippybot.decorators import directcmd
try:
    import simplejson as json
except ImportError:
    import json

UD_SEARCH_URI = "http://www.urbandictionary.com/iphone/search/define"

class Plugin(object):
    """Plugin to lookup definitions from urbandictionary.com
    """
    global_commands = ('udefine',)

    @directcmd
    def udefine(self, mess, args):
        """
        Returns the Urban Dictionary definition of the passed in word
        Format: @NickName udefine <word>
        """
        self.bot.log.info("udefine: %s" % mess)
        term = args.strip()
        req = requests.get(UD_SEARCH_URI, params={'term': term})
        data = req.content
        results = []
        if data:
            data = json.loads(data.replace(r'\r', ''))
            if data.get('result_type', '') != 'no_results' and \
               data.has_key('list') and len(data['list']) > 0:
                for datum in data['list']:
                    if datum.get('word', '') == term:
                        # Sanitization
                        definition = datum['definition']
                        re.sub(r'\s', ' ', definition)
                        definition = u''.join(Soup(definition).findAll(text=True))
                        definition = unicode(Soup(definition, convertEntities=Soup.HTML_ENTITIES))
                        results.append(definition)
        if results:
            reply = u"\n".join(results)
            return reply
        else:
            return u'No matches found for "%s"' % (term,)


########NEW FILE########
__FILENAME__ = uptime
import subprocess
from hippybot.decorators import botcmd

class Plugin(object):
	@botcmd
	def uptime(self, mess, args, **kwargs):
		"""Get current uptime information"""
		self.bot.log.info("uptime: %s" % mess)
		return subprocess.check_output('uptime')

########NEW FILE########
__FILENAME__ = wave
from collections import Counter
from hippybot.decorators import botcmd

class Plugin(object):
    """HippyBot plugin to make the bot complete a wave if 3 people in a
    row do the action "\o/".
    """
    global_commands = ['\o/', 'wave']
    command_aliases = {'\o/': 'wave'}
    counts = Counter()
    @botcmd
    def wave(self, mess, args):
        """
        If enough people \o/, techbot will too.
        Everyone loves a follower, well, techbot is here to fulfill that need
        """
        channel = unicode(mess.getFrom()).split('/')[0]
        self.bot.log.info("\o/ %s" %self.counts[channel])

        if not self.bot.from_bot(mess):
            self.counts[channel] += 1
            if self.counts[channel] == 3:
                self.counts[channel] = 0
                return r'\o/'

########NEW FILE########
