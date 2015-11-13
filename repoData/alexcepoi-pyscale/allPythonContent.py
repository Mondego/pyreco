__FILENAME__ = app
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import os.path as osp
import logging

class Configuration(object):
	def __init__(self, env='development'):
		self.env = os.environ.get('APP_ENV') or env
		self.root = osp.abspath('.')
	
	@property
	def log_level(self):
		if self.env == 'production':
			return logging.WARNING
		else:
			return logging.DEBUG

########NEW FILE########
__FILENAME__ = module
#! /usr/bin/env python
# -*- coding: utf-8 -*-

from pyscale.lib.module import BaseModule, job


class Module(BaseModule):
	""" Module Class (daemon) """

	# notifications
	def notice(self, msg):
		pass

	def alert(self, msg):
		pass

	def error(self, msg):
		pass

########NEW FILE########
__FILENAME__ = decorators
#! /usr/bin/env python
# -*- coding: utf-8 -*-

def api(method):
	""" Basic decorator for module API methods """
	method.api = True
	return method

########NEW FILE########
__FILENAME__ = errors
#! /usr/bin/env python
# -*- coding: utf-8 -*-


class PyscaleError(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg


class ReqError(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __getattr__(self, key):
		return self

	def __setattr__(self, key, name):
		if key == 'msg':
			return super(ReqError, self).__setattr__(key, name)
		return self

	def __delattr__(self, key):
		if key == 'msg':
			return super(ReqError, self).__delattr__(key, name)
		return self

	def __call__(self, *args, **kwargs):
		return self

	def __str__(self):
		return '(error: %s)' % self.msg

	def __repr__(self):
		return str(self)

	def __nonzero__(self):
		return False

########NEW FILE########
__FILENAME__ = log
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import logging.handlers
import traceback


class MyFormatter(logging.Formatter):
	def format(self, record):
		record.fname = "[%s:%s]" % (record.filename, record.lineno)
		return logging.Formatter.format(self, record)


EXCEPTION_PREFIX = '   =>  '

def log_exception(msg=None):
	""" Custom exception log helper """
	if msg is None:
		msg = traceback.format_exc()
	
	lines = msg.split('\n')
	lines = [ '%s%s' % (EXCEPTION_PREFIX, line) for line in lines if line]
	msg = '\n' + '\n'.join(lines) + '\n'

	logging.log(75, '\n%s' % msg)

def log_status(msg):
	""" Always log regardless of level """
	logging.log(100, msg)


def config_logger(stream=sys.stdout, level=logging.DEBUG):
	logger = logging.getLogger()
	logger.setLevel(level)


	# handler
	if stream in [sys.stdout, sys.stderr]:
		handler = logging.StreamHandler(stream)
	else:
		handler = logging.handlers.RotatingFileHandler(stream, maxBytes=409600, backupCount=3)
	logger.addHandler(handler)

	# formatter
	formatter = MyFormatter(
		fmt = '%(asctime)s %(levelname)-8s %(fname)-20s  %(message)s',
		datefmt = '%b %d %Y %H:%M:%S',
	)
	handler.setFormatter(formatter)
	
	# custom levels
	logging.addLevelName(75, 'EXCEPT')
	logging.exception = log_exception

	logging.addLevelName(100, 'STATUS')
	logging.status = log_status


# test
if __name__ == '__main__':
	config_logger()

	logging.warning('test')
	logging.info('test')
	logging.debug('test')
	logging.error('test')
	
	try: err_var
	except Exception as ex:
		logging.exception()

	logging.status('test')

########NEW FILE########
__FILENAME__ = module
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import inspect
import logging
import os
import os.path as osp
import sys

import gevent.monkey
gevent.monkey.patch_all()

import gevent.pool
from gevent_zeromq import zmq

# pyscale
from .log import config_logger
from ..zmq import Socket, MultiSocket, RpcServer

# project
from config.app import Configuration


def job(method):
	method.job = True
	return method


class BaseModule(object):
	""" Basic Module Class (daemon) """

	def __init__(self, context=None):
		# app config
		self.conf = Configuration()

		# module config
		self.name = osp.basename(osp.dirname(osp.abspath(sys.argv[0])))
		self.pidfile = "tmp/pids/%s.pid" % self.name
		config_logger("logs/%s.log" % self.name, self.conf.log_level)

		# zmq context
		self.context = context or zmq.Context.instance()

		# pool of greenlets
		self.jobs = gevent.pool.Group()

		# zmq REQ/REP API
		self.rpc = RpcServer(self, "ipc://tmp/sockets/rpc/%s.sock" % self.name)
		self.rpc.run()

		# spawn jobs
		bases = self.__class__.__mro__
		for base in bases:
			for func in base.__dict__.values():
				if getattr(func, 'job', None):
					method = func.__get__(self, self.__class__)
					self.jobs.spawn(method)


	def run(self):
		""" Run the current module (start greenlets) """
		# check for previous crash
		if os.access(self.pidfile, os.F_OK):
			pid = open(self.pidfile, 'r').readline()

			if osp.exists('/proc/' + pid):
				logging.warn("%s already running with pid %s" % (self.name, pid))
				return
			else:
				logging.warn("%s seems to have crashed.. deleting pidfile" % self.name)
				os.remove(self.pidfile)

		# run all jobs
		with self:
			try:
				self.jobs.join()
			except KeyboardInterrupt:
				self.jobs.kill()
				# zmq.Context.instance().term()

	def sock(self, name, _type=None):
		""" Socket convenience function """
		if _type:
			return Socket(name, _type)
		else:
			return Socket(name)

	def multisock(self, name, _type=None):
		""" MultiSocket convenince function """
		if _type:
			return MultiSocket(name, _type)
		else:
			return MultiSocket(name)

	def __enter__(self):
		logging.status("%s started" % self.name)

		# create pidfile
		open(self.pidfile, 'w').write(str(os.getpid()))

		return self

	def __exit__(self, type, value, traceback):
		logging.status("%s stopped" % self.name)

		# remove pidfile
		os.remove(self.pidfile)

		return False

	def help(self):
		methods = []
		for name in dir(self):
			obj = getattr(self, name)
			if inspect.ismethod(obj):
				if getattr(obj, 'api', False):
					# extract specs
					spec = inspect.getargspec(obj)

					# extract docstring
					doc = inspect.getdoc(obj)
					if doc: doc = doc.strip()

					methods.append((name, inspect.formatargspec(*spec), doc))
			else:
				if not name.startswith('_'):
					methods.append(name)
		return methods

	# notifications
	def notice(self, msg):
		pass

	def alert(self, msg):
		pass

	def error(self, msg):
		pass

########NEW FILE########
__FILENAME__ = console
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import glob
import os
import os.path as osp

import code
import signal

from cake.lib import puts
from cake.color import fore

from ..zmq import Socket, MultiSocket


def api(modules):
	# ensure iterable
	if isinstance(modules, Socket):
		modules = [modules]
	
	# iterate list
	for module in modules:
		puts('= ' + fore.green(module.name))
		for obj in module.help():
			if isinstance(obj, list):
				# method
				puts('  * ' + fore.yellow(obj[0]) + ' ' + fore.white(obj[1]))
				if obj[2]:
					puts('    ' + fore.blue(obj[2]))

def reinit(namespace, info=True):
	# clean sockets
	for sock in namespace.sockets:
		delattr(namespace, sock.name)

	# create sockets
	namespace.all = MultiSocket('*')
	namespace.sockets = namespace.all.objs

	for sock in namespace.sockets:
		setattr(namespace, sock.name, sock)
	
	# display info
	if info:
		puts('=== ' + fore.blue('PyScale Console') + ' =', padding='=')
		for sock in ['all'] + sorted([x.name for x in namespace.sockets]):
			puts('    ' + fore.green('>>> ') + sock)
		puts('=====================', padding='=')


def main(namespace):
	# parse args
	command = ' '.join(sys.argv[1:])

	if not command:
		# console (interactive)
		try: reinit(namespace)
		except KeyboardInterrupt:
			pass

		# ignore Ctrl-C (interferes with gevent)
		signal.signal(signal.SIGINT, lambda signum, frame: None)
	else:
		# call (non-interactive)
		reinit(namespace, info=False)

		console = code.InteractiveConsole(locals())
		console.runsource(command)

########NEW FILE########
__FILENAME__ = generators
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import os.path as osp
import pydoc
import shutil

import jinja2

import pyscale
from cake.lib import recurse_up
from cake.color import puts, fore

from ..lib import PyscaleError


def find_project():
	current = os.getcwd()
	return recurse_up(current, 'Cakefile')


def new(projname):
	""" create new project from default files """

	# find project template
	if find_project() != False:
		raise PyscaleError('Inside another project. Aborting...')
	elif osp.isdir(projname):
		raise PyscaleError('Folder already exists. Aborting...')
	else:
		project = osp.join(pyscale.__path__[0], 'files', 'project')

	# copy project template
	def ignore(dirname, names):
		common = osp.commonprefix([project, dirname])

		puts(fore.green('   init ') + osp.join(projname, dirname[len(common)+1:]))
		return []

	shutil.copytree(project, projname, ignore=ignore)


def generate(modname):
	""" generate new module """

	# check for valid name
	if modname.lower() in pydoc.Helper.keywords.keys():
		raise PyscaleError('%s is a Python keyword.' % repr(modname.lower()))

	# go to project root
	root = find_project()
	if root != False:
		os.chdir(root)
	else:
		raise PyscaleError('Pyscale project not found (missing Cakefile?)')


	# create folder
	folder = 'app/%s' % modname
	if osp.isdir(folder):
		puts(fore.yellow(' exists ') + folder)
	else:
		puts(fore.green('  mkdir ') + folder)
		os.makedirs(folder)

	
	# create file
	modfile = 'app/%s/main' % modname
	tplfile = osp.join(pyscale.__path__[0], 'files', 'module')

	if osp.exists(modfile):
		raise PyscaleError('Module already exists. Aborting...')
	else:
		with open(tplfile) as f:
			tpl = jinja2.Template(f.read())
			tpl = tpl.render(module=modname.title())

		puts(fore.green(' create ') + modfile)
		with open(modfile, 'w') as f:
			f.write(tpl)

########NEW FILE########
__FILENAME__ = logger
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re

from cake.lib import puts
from cake.color import fore, style

from ..lib.log import EXCEPTION_PREFIX

def println(line):
	# blank line
	if re.match(r'\s*$', line):
		return puts(line)

	# logfile header
	mobj = re.match(r'==> (.*) <==$', line)
	if mobj:
		return puts(style.bright(fore.black('==> ') + fore.white(mobj.group(1)) + fore.black(' <==')))
	
	# exception line
	if re.match(EXCEPTION_PREFIX, line):
		return puts(fore.red(line))

	# standard log line
	basic = r'(.*?\s+)'

	date = basic*3
	time = basic
	type = basic
	file = '(\[.*?\s+)\])'

	mobj = re.match(basic*6 + r'(.*)', line)
	if not mobj:
		# non-conventional line
		return puts(line)
	else:
		groups = list(mobj.groups())

		groups.insert(0, str(fore.cyan))
		groups.insert(4, str(fore.blue))
		groups.insert(6, str(style.bright))
		groups.insert(8, str(style.reset_all))
		groups.insert(9, str(fore.cyan))
		groups.insert(11, str(style.reset_all))

		for idx, string in enumerate(groups):
			string = re.sub(r'(STATUS)', fore.white(r'\1'), string)
			string = re.sub(r'(DEBUG)', fore.white(r'\1'), string)
			string = re.sub(r'(INFO)', fore.green(r'\1'), string)
			string = re.sub(r'(WARNING)', fore.yellow(r'\1'), string)
			string = re.sub(r'(ERROR)', fore.red(r'\1'), string)
			string = re.sub(r'(EXCEPT)', fore.red(r'\1'), string)

			groups[idx] = string


		groups[-1] = re.sub(r'\[', fore.cyan(r'['), groups[-1])
		groups[-1] = re.sub(r'\]', fore.cyan(r']'), groups[-1])

		groups[-1] = re.sub(r'~>', fore.blue(r'~>'), groups[-1])
		groups[-1] = re.sub(r'<~', fore.yellow(r'<~'), groups[-1])

		groups[-1] = re.sub(r'\(', fore.cyan(r'('), groups[-1])
		groups[-1] = re.sub(r'\)', fore.cyan(r')'), groups[-1])

		groups[-1] = re.sub(r"'", fore.cyan(r"'"), groups[-1])
		groups[-1] = re.sub(r'"', fore.cyan(r'"'), groups[-1])

		return puts(''.join(groups))


def main():
	try:
		while True:
			println(raw_input())
	except KeyboardInterrupt:
		pass

########NEW FILE########
__FILENAME__ = tasks
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import glob
import operator
import os
import os.path as osp
import subprocess as sbp
import nose
import fnmatch

from cake.lib import task, path, puts
from cake.color import fore
from cake.errors import CakeError

from ..zmq import Socket
from ..utils import command, execute
from ..lib import PyscaleError


# == Helpers ==
def python():
	return  "%s -uB" % sys.executable

def shell(cmd, exception=None):
	return command(cmd, shell=True, exception=exception)

def all_modules(regex='*'):
	mods = []
	for path in glob.iglob('app/%s/main' % regex):
		module = osp.basename(osp.dirname(path))
		mods.append((module, path))
	return mods

def running_modules(regex='*'):
	mods = []
	for pidfile in glob.iglob('tmp/pids/%s.pid' % regex):
		module = osp.splitext(osp.basename(pidfile))[0]
		pid = open(pidfile).read()
		mods.append((module, pid, pidfile))
	return mods


# == Module Management ==
@task('Starting Modules')
def start(module='*', env='development'):
	""" Start [module] """

	os.environ['APP_ENV'] = env

	for module, path in all_modules(module):
		try:
			cmd = "PYTHONPATH=. %s %s &>> logs/%s.log" % (python(), path, module)
			shell("echo '%s' | at now" % cmd, exception=PyscaleError)
		except PyscaleError as e:
			msg = str(e).strip('\n')
			msg = ' '.join(msg.split('\n'))

			puts(fore.cyan("%-10s" % module) + "(%s) scheduled" % msg)

@task('Stopping Modules')
def stop(module='*'):
	""" Stop [module] """

	for module, pid, pidfile in running_modules(module):
		shell('kill %s' % pid)
		shell('rm -f %s' % pidfile)
		shell('rm -f tmp/sockets/*/%s.sock' % module)

		puts(fore.cyan("%-10s" % module) + "(pid: %s) stopped" % fore.red(pid))

@task
def restart(module='*', env='development'):
	""" Restart [module] """

	stop(module)
	start(module, env)

@task
def clean(module='*'):
	""" Clean temp files """
	shell('rm -f logs/%s.log' % module)
	shell('rm -f tmp/pids/%s.pid' % module)
	shell('rm -f tmp/sockets/*/%s.sock' % module)

@task
def reset(module='*', env='development'):
	""" Restart [module] and clean up temp files """
	stop(module)
	clean(module)
	start(module, env)

@task
def kill(signal=9):
	""" Kill zombie (unregistered) modules """
	zombies = []
	pids = set(m[1] for m in running_modules())

	for line in shell('ps -e --no-headers -o pid,command').split('\n'):
		try: pid, name = re.match(r'\s*(\d+)\s+(.+)$', line).groups()
		except AttributeError: continue

		mob = re.search(r'app/(.*?)/main', name)
		if mob and pid not in pids:
			zombies.append((mob.group(1), pid))

	if not zombies:
		puts(fore.green('No zombies detected'))
	else:
		puts(fore.green('Killing %d zombie modules' % len(zombies)))
		for name, pid in zombies:
			puts(' * Killing %-10s (pid: %s) ...' % (fore.cyan(name), fore.red(pid)))

			try: shell('kill -s %s %s' % (signal, pid), exception=RuntimeError)
			except RuntimeError as e:
				puts(fore.magenta('   Error: ') + e.args[0])

@task
def status():
	""" View running modules """
	for module, pid, pidfile in running_modules():
		if not osp.exists("/proc/%s" % pid):
			puts(fore.red("%s (pid %s) crashed" % (module, pid)))

	pids = map(operator.itemgetter(1), running_modules())
	if pids:
		pscomm = "ps -p %s -o pid,user,command:50,pcpu,pmem,vsz,nice,start,time" % ','.join(pids)
		psinfo = shell(pscomm).split('\n')

		if len(psinfo) > 1 and psinfo[1]:
			puts(fore.green(psinfo[0]))

			for ps in psinfo[1:]:
				color = lambda mobj: re.sub(mobj.group(1), fore.cyan(mobj.group(1)), mobj.group(0))
				puts(re.sub('app/(.*?)/main', color, ps))

@task
def log(module='*', lines=10):
	""" View log for [module] """

	if not glob.glob('logs/*.log'):
		raise CakeError('No logfiles found')
	else:
		try: sbp.call("tail -n %s -f logs/%s.log | PYTHONPATH=. %s tools/logger" % (lines, module, python()), shell=True)
		except KeyboardInterrupt: pass


# == Debugging ==
@task
def run(what, *args):
	""" Run from project root """

	what = osp.join(path.current, what)
	args = ' '.join([what] + list(args))

	execute("%s %s" % (python(), args), env={'PYTHONPATH': '.'})

@task
def debug(what, *args):
	""" Run interactively from project root"""

	what = osp.join(path.current, what)
	args = ' '.join([what] + list(args))

	execute("%s -i %s" % (python(), args), env={'PYTHONPATH': '.'})

@task
def console(*args, **kwargs):
	""" Debugging Console """

	argv = list(args) + ['%s=%s' % (key, val) for key, val in kwargs.items()]
	if len(argv) > 1:
		raise CakeError('console() can receive 0 or 1 arguments')

	if argv:
		run('tools/console %s' % ' '.join(argv))
	else:
		debug('tools/console')

@task
def test(pattern='*'):
	""" Run Unit Tests """
	# recurse folder for tests
	files = []
	for root, dirs, fnames in os.walk('tests'):
		for fname in fnmatch.filter(fnames, '%s_tests.py' % pattern):
			files.append(osp.join(root, fname))

	# run tests
	nose.main(argv=[''] + files)

########NEW FILE########
__FILENAME__ = commands
#!/usr/bin/python
# -*- coding: utf-8 -*-

import subprocess as sbp
import shlex
import os
import pty

import gevent
from gevent.event import Event

from .gevsubprocess import GPopen
from ..lib.errors import PyscaleError


def command(cmd, exception=PyscaleError, sudo=False, shell=False):
	# fix unicode stuff
	cmd = str(cmd)

	# parse args
	if sudo:
		# XXX: --session-command vs --command(-c)
		# session-command seems to be better but is only available on CentOS & Co.
		# cmd = "su -c '%s'" % cmd
		cmd = "sudo -n bash -c '%s'" % cmd
	if not shell:
		cmd = shlex.split(cmd)

	# execute
	slave = None
	if sudo:
		# give su a pty
		master, slave = pty.openpty()
	
	out, err = GPopen(cmd, stdin=slave, stdout=sbp.PIPE, stderr = sbp.PIPE, shell=shell).communicate()

	# handle errors
	if not out and err:
		if exception:
			raise exception(err)
		else:
			print err

	return out


def execute(cmd, env={}):
	args = shlex.split(cmd)

	if env:
		environ = os.environ.copy()
		environ.update(env)
		os.execvpe(args[0], args,  environ)
	else:
		os.execvp(args[0], args)


# main
if __name__ == '__main__':
	print command('ls', sudo=True, shell=False)

########NEW FILE########
__FILENAME__ = pipe
import gevent
from gevent import socket
from gevent.event import Event
from gevent.queue import Queue, Empty, Full #@UnusedImport

import fcntl
import os
import sys
import errno

class PipeClosed(Exception):
    """Exception raised by :func:`Pipe.get` and :func:`Pipe.put` indicating
       the :class:`Pipe` was closed
       
    """
    pass

class Pipe(Queue):
    """A :class:`Pipe` is a :class:`gevent.queue.Queue` that can be closed."""
    
    def __init__(self, maxsize=None):
        Queue.__init__(self, maxsize)
        self._closed = Event()
        self._event_cancel = None
        
    def close(self):
        """Closes the pipe"""
        self._closed.set()
        
        # Raise PipeClosed on all waiting getters and putters
        if self.getters or self.putters:
            self._schedule_unlock()
        
    def closed(self):
        """Returns ``True`` when the pipe has been closed.
        (There might still be items available though)
        
        """
        return self._closed.is_set()
    
    def finished(self):
        """Returns ``True`` when the pipe has been closed and is empty."""
        return self.empty() and self.closed() 
        
    def wait(self, timeout=None):
        """ Wait until the pipe is closed
        """
        self._closed.wait(timeout)
        
    def waiting(self):
        return len(self.getters)>0 or len(self.putters)>0
        
    def put(self, item, block=True, timeout=None):
        """Put an item into the pipe.

        If optional arg *block* is true and *timeout* is ``None`` (the default),
        block if necessary until a free slot is available. If *timeout* is
        a positive number, it blocks at most *timeout* seconds and raises
        the :class:`Full` exception if no free slot was available within that time.
        Otherwise (*block* is false), put an item on the pipe if a free slot
        is immediately available, else raise the :class:`Full` exception (*timeout*
        is ignored in that case).
        
        :raises: :class:`PipeClosed` if the pipe is closed
        
        """
        if self.closed():
            raise PipeClosed
        
        Queue.put(self, item, block, timeout)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the pipe.

        If optional args *block* is true and *timeout* is ``None`` (the default),
        block if necessary until an item is available. If *timeout* is a positive number,
        it blocks at most *timeout* seconds and raises the :class:`Empty` exception
        if no item was available within that time. Otherwise (*block* is false), return
        an item if one is immediately available, else raise the :class:`Empty` exception
        (*timeout* is ignored in that case).

        :raises: :class:`PipeClosed` if the pipe is closed
        
        """
        if self.finished():
            raise PipeClosed
        
        return Queue.get(self, block, timeout)
    
    def _unlock(self):
        #if self.finished():
        if self.closed():
            while self.getters:
                getter = self.getters.pop()
                if getter:
                    getter.throw(PipeClosed)

            while self.putters:
                putter = self.putters.pop()
                if putter:
                    putter.throw(PipeClosed)
                        
        Queue._unlock(self)

    def next(self):
        """Iterate over the items in the pipe, until the pipe is empty and closed."""
        try:
            return self.get()

        except PipeClosed:
            raise StopIteration

def pipe_to_file(pipe, file):
    """Copy items received from *pipe* to *file*"""
    if file.closed:
        return
    
    fcntl.fcntl(file, fcntl.F_SETFL, os.O_NONBLOCK)

    fno = file.fileno()

    try: 
        socket.wait_write(fno)
    except IOError, ex:
        if ex[0] != errno.EPERM:
            raise

        sys.exc_clear()
        use_wait = False
    else:
        use_wait = True

    for chunk in pipe:
        while chunk:
            try:
                written = os.write(fno, chunk)
                chunk = chunk[written:]

            except IOError, ex:
                if ex[0] != errno.EAGAIN:
                    raise
                
                sys.exc_clear()
                
            except OSError, ex:
                if not file.closed:
                    raise
                
                sys.exc_clear()
                pipe.close()
                return
                
            if use_wait: 
                socket.wait_write(fno)
            else:
                gevent.sleep(0)

    file.close()

def file_to_pipe(file, pipe, chunksize=-1):
    """Copy contents of *file* to *pipe*. *chunksize* is passed on to file.read()
    """
    if file.closed:
        pipe.close()
        return
    
    fcntl.fcntl(file, fcntl.F_SETFL, os.O_NONBLOCK)

    fno = file.fileno()
    use_wait = True
    
    while True:
        try:
            chunk = file.read(chunksize)
            if not chunk:
                break
            pipe.put(chunk)

        except IOError, ex:
            if ex[0] != errno.EAGAIN:
                raise
        
            sys.exc_clear()
       
        try: 
            if use_wait:
                socket.wait_read(fno)
        except IOError, ex:
            if ex[0] != errno.EPERM:
                raise

            sys.exc_clear()
            use_wait = False
            
        if not use_wait:
            gevent.sleep(0)

    file.close()
    pipe.close()
        
__all__ = ['Pipe', 'pipe_to_file', 'file_to_pipe', 'PipeClosed', 'Empty', 'Full']

########NEW FILE########
__FILENAME__ = common
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re
import logging


patterns = {}
patterns['REQ'] = 'rpc'
patterns['SUB'] = 'pub'


def format_args(args=[], kwargs={}):
	args = [repr(i) for i in args]
	kwargs = ['%s=%s' % (key, repr(value)) for key, value in kwargs.items()]
	return ', '.join(args + kwargs)

def format_method(method, args=[], kwargs={}, clean=True):
	if clean:
		if method == '__getattribute__' and len(args) == 1 and not kwargs:
			return '.%s' % args[0]

		if method == '__call__':
			return '(%s)' % format_args(args, kwargs)

	return '.%s(%s)' % (method, format_args(args, kwargs))

########NEW FILE########
__FILENAME__ = multisocket
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import glob
import os.path as osp

from .common import patterns
from .socket import Socket

class MultiObject(object):
	def __init__(self, lst):
		self.objs = lst

	# accessing attributes
	def __getattr__(self, method):
		objs = map(lambda x: getattr(x, method), self.objs)
		return MultiObject(objs)

	def __setattr__(self, key, value):
		if key == 'objs':
			return super(MultiObject, self).__setattr__(key, value)

		objs = map(lambda x: setattr(x, key, value), self.objs)
		return MultiObject(objs)

	def __delattr__(self, key):
		if key == 'objs':
			return super(MultiObject, self).__setattr__(key, value)

		objs = map(lambda x: delattr(x, key), self.objs)
		return MultiObject(objs)


	# overloading
	def __call__(self, *args, **kwargs):
		objs = map(lambda x: x(*args, **kwargs), self.objs)
		return MultiObject(objs)

	def __str__(self):
		return str(self.objs)

	def __repr__(self):
		return repr(self.objs)

	def __len__(self):
		return len(self.objs)

	def __dir__(self):
		return dir(self.objs)

	def __getitem__(self, index):
		return self.objs[index]


class MultiSocket(object):
	""" ZMQ multi-client for all messaging patterns"""

	def __new__(cls, name, _type='REQ', subscription='', context=None):
		# extract (name, pattern) from sockfile
		def parse(sockfile):
			folder, name = osp.split(osp.splitext(sockfile)[0])
			pattern = osp.basename(folder)
			pattern = [item[0] for item in patterns.iteritems() if item[1] == pattern][0]

			return name, pattern

		socks = glob.glob("tmp/sockets/%s/%s.sock" % (patterns[_type], name))
		socks = map(lambda x: parse(x), socks)

		socks = [Socket(i[0], i[1], subscription, context) for i in socks]

		return MultiObject(socks)

########NEW FILE########
__FILENAME__ = rpc
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import traceback

import gevent
import gevent.pool
import gevent.queue
from gevent_zeromq import zmq

# python is great
import types
types.MethodWrapper = type(object().__getattribute__)

# library
from .common import format_method
from ..lib import PyscaleError, ReqError

# let zmq select jsonapi (for performance)
from zmq.utils import jsonapi
if jsonapi.jsonmod is None:
	raise ImportError('jsonlib{1,2}, json or simplejson library is required.')


class RpcWorker(gevent.Greenlet):
	""" zmq RPC Worker """

	def __init__(self, server):
		super(RpcWorker, self).__init__()

		self.server = server

	def _run(self):
		self.sock = self.server.context.socket(zmq.REQ)
		self.sock.connect("inproc://workers")

		self.sock.send('READY')

		# request loop
		while True:
			self._ready = True
			envelope, req = self.recv()
			self._ready = False

			if req is None:
				# kill me if you dare
				break
			else:
				# love me, i don't care
				try: reply = self.handle(req)
				except ReqError as e:
					self.send(envelope, e.msg, error=True)
				else:
					self.send(envelope, reply)

	def handle(self, requests):
		logging.debug("[zmq] <~ self%s" % ''.join([format_method(*req) for req in requests]))

		# loop request chain
		module = self.server.module
		result = module
		parsed = module.name

		for method, args, kwargs in requests:
			# parse request
			try:
				if method == '__dir':
					result = dir(result, *args, **kwargs)
				elif method == '__len':
					result = len(result, *args, **kwargs)
				elif method == '__set':
					result = setattr(result, *args, **kwargs)
				elif method == '__del':
					result = delattr(result, *args, **kwargs)
				else:
					try: result = getattr(result, method)
					except AttributeError:
						parsed += '.' + method
						raise
					else:
						parsed += format_method(method, args, kwargs)
						result = result(*args, **kwargs)
			except AttributeError:
				msg = 'AttributeError: \'%s\'' % parsed
				logging.error(msg)
				module.alert(msg)
				raise ReqError(parsed)
			except PyscaleError as ex:
				msg = ''.join(traceback.format_exception_only(type(ex), ex)).strip()
				logging.error(msg)
				module.alert(msg)
				raise ReqError(parsed)
			except Exception as ex:
				msg = traceback.format_exc()
				logging.exception(msg)
				module.error(msg)
				raise ReqError(parsed)

		return result

	def recv(self):
		envelope = self.sock.recv_multipart()
		msg = jsonapi.loads(envelope.pop())

		return envelope, msg

	def send(self, envelope, msg, error=False):
		if error:
			msg = jsonapi.dumps({'error': msg})
		else:
			# FIXME: exception handling should be better done
			# but there are too many json libraries out there
			try: msg = jsonapi.dumps({'result': msg})
			except Exception:
				msg = jsonapi.dumps({'proxy': repr(msg)})

		envelope.append(msg)
		return self.sock.send_multipart(envelope)


class RpcServer(object):
	""" zmq RPC Server featuring Router-to-Router broker (LRU queue) """

	def __init__(self, module, address, ready_workers=1, max_workers=float('inf'), context=None):
		self.module  = module
		self.address = address
		self.context = context or zmq.Context.instance()

		self.ready_workers = ready_workers
		self.max_workers   = max_workers

		self.workers = gevent.pool.Group()

	def spawn_worker(self):
		if len(self.workers) < self.max_workers:
			# we keep track of workers internally
			worker = RpcWorker(self)
			self.workers.start(worker)

			# but also register them as module jobs
			self.module.jobs.add(worker)

	@property
	def status(self):
		# for debugging purposes
		return [getattr(worker, '_ready', None) for worker in self.workers]

	def run(self):
		# spawn workers
		for i in xrange(self.ready_workers):
			self.spawn_worker()

		# create broker
		clients = self.context.socket(zmq.XREP)
		clients.bind(self.address)

		workers = self.context.socket(zmq.XREP)
		workers.bind("inproc://workers")

		# XXX: zmq devices don't work with gevent
		# zmq.device(zmq.QUEUE, clients, workers)
		self.broker = RpcBroker(clients, workers, self)


class RpcBroker(object):
	""" zmq gevent-compatible LRU Queue Device """

	def __init__(self, clients, workers, server):
		self.clients = clients
		self.workers = workers
		self.server  = server

		# here we keep track of idle workers
		self.ready = gevent.queue.Queue()

		# spawn jobs that redirect requests from clients to workers and back
		self.jobs = gevent.pool.Group()
		fwd = self.jobs.spawn(self.forward)
		bwd = self.jobs.spawn(self.backward)

		self.server.module.jobs.add(fwd)
		self.server.module.jobs.add(bwd)

	def forward(self):
		while True:
			# client request: [client][empty][req]
			msg = self.clients.recv_multipart()

			# assertions
			assert msg[1] == ''

			# spawn additional worker if none available
			if self.ready.empty():
				self.server.spawn_worker()

			# get a ready worker and pass request
			worker = self.ready.get()
			self.workers.send_multipart([worker, ''] + msg)

	def backward(self):
		while True:
			# worker response: [worker][empty][ready] or [worker][empty][client][empty][reply]
			msg = self.workers.recv_multipart()

			# assertions
			assert msg[1] == ''
			assert len(msg) == 3 or (len(msg) == 5 and msg[3] == '')

			# route reply back to client
			if msg[2] != 'READY':
				self.clients.send_multipart(msg[2:])

			# decide worker fate
			worker = msg[0]

			if self.ready.qsize() >= max(self.server.ready_workers, 1):
				# kill worker (send None as request)
				self.workers.send_multipart([worker, '', jsonapi.dumps(None)])
			else:
				# keep worker (mark as ready)
				self.ready.put(worker)

########NEW FILE########
__FILENAME__ = socket
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import glob
import os.path as osp
from contextlib import contextmanager

from gevent_zeromq import zmq
from .common import patterns, format_method
from ..lib import ReqError


class ProxySocket(object):
	reserved = ['_obj', '_parsed', '_key', '_value', '_attr', '_str']

	def __init__(self, obj, parsed=[]):
		self._obj = obj
		self._parsed = []

		self._str = None

	def __getattr__(self, key):
		self._key = key
		self._attr = 'get'
		return self._rpc()

	def __setattr__(self, key, value):
		if key in self.reserved:
			return super(ProxySocket, self).__setattr__(key, value)

		self._key = key
		self._value = value
		self._attr = 'set'
		return self._rpc()

	def __delattr__(self, key):
		if key in self.reserved:
			return super(ProxySocket, self).__delattr__(key)

		self._key = key
		self._attr = 'del'
		return self._rpc()

	def __call__(self, *args, **kwargs):
		self._attr = 'call'
		return self._rpc(*args, **kwargs)

	def _rpc(self, *args, **kwargs):
		# prepare request
		if self._attr is 'call':
			blob =  ('__call__', args, kwargs)
		elif self._attr is 'get':
			blob = ('__getattribute__', [self._key], {})
		elif self._attr is 'set':
			blob = ('__set', [self._key, self._value], {})
		elif self._attr is 'del':
			blob = ('__del', [self._key], {})
		elif self._attr is 'dir':
			blob = ('__dir', [], {})
		elif self._attr is 'len':
			blob = ('__len', [], {})
		else:
			raise ValueError('Unknown value for attr: %s' % self.attr)

		self._parsed.append(blob)

		# make request
		if self._obj._sock is not None:
			reply = self._obj._send(self._parsed)
		else:
			with self._obj:
				reply = self._obj._send(self._parsed)

		# parse response
		if 'error' in reply:
			return ReqError(reply['error'])
		elif 'proxy' in reply:
			self._str = '(proxy: %s)' % reply['proxy']
			return self
		elif 'result' in reply:
			return reply['result']
		else:
			raise ValueError('reply must be result, proxy or error')

		return result

	def __str__(self):
		if self._str is None:
			return super(ProxySocket, self).__str__()

		return str(self._str)

	def __repr__(self):
		if self._str is None:
			return super(ProxySocket, self).__repr__()

		return str(self._str)

	def __dir__(self):
		self._attr = 'dir'
		return self._rpc()

	def __len__(self):
		self._attr = 'len'
		return self._rpc()


class Socket(object):
	""" ZMQ client for all messaging patterns """
	reserved = ['_name', '_type', '_pattern', '_subscription', '_context', '_sock_file', '_sock']

	def __init__(self, name, _type='REQ', subscription='', context=None):
		self._name          = name
		self._type          = _type.upper()
		self._pattern       = patterns[self._type]
		self._subscription  = subscription
		self._context       = context or zmq.Context.instance()

		self._sock_file = "ipc://tmp/sockets/%s/%s.sock" % (self._pattern, self._name)
		self._sock = None

	def _open(self):
		if self._sock is not None:
			return

		self._sock = self._context.socket(getattr(zmq, self._type))
		self._sock.connect(self._sock_file)

		if self._pattern == 'pub':
			self._sock.setsockopt(zmq.SUBSCRIBE, self._subscription)

		return self

	def _close(self):
		if self._sock is not None:
			self._sock.close()
			self._sock = None

		return self

	def __enter__(self):
		return self._open()

	def __exit__(self, type, value, trace):
		self._close()

	def _send(self, blob):
		self._sock.send_json(blob)
		logging.debug("[zmq] ~> %s%s" % (self._name, ''.join([format_method(*req) for req in blob])))
		return self._sock.recv_json()

	# pass to proxy
	def __getattr__(self, key):
		return getattr(ProxySocket(self), key)

	def __setattr__(self, key, value):
		if key in self.reserved:
			return super(Socket, self).__setattr__(key, value)
		else:
			return setattr(ProxySocket(self), key, value)

	def __delattr__(self, key):
		if key in self.reserved:
			return super(Socket, self).__delattr__(key)
		else:
			return delattr(ProxySocket(self), key)

	def __call__(self, *args, **kwargs):
		return ProxySocket(self).__call__(*args, **kwargs)

	def __dir__(self):
		return dir(ProxySocket(self))

########NEW FILE########
