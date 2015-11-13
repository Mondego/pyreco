__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for djangotestapp project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'r04y1gw5-^%1)@(gbh$oa#wajdpa2yzij7eqj$gzs1hjb^-jbu'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'djangotestapp.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^djangotestapp/', include('djangotestapp.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = django_factory
# Copyright (c) 2008, Donovan Preston
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import inspect
import os
import django.core.handlers.wsgi

import spawning.util

def config_factory(args):
    args['django_settings_module'] = args.get('args', [None])[0]
    args['app_factory'] = 'spawning.django_factory.app_factory'

    ## TODO More directories
    ## INSTALLED_APPS (list of quals)
    ## ROOT_URL_CONF (qual)
    ## MIDDLEWARE_CLASSES (list of quals)
    ## TEMPLATE_CONTEXT_PROCESSORS (list of quals)
    settings_module = spawning.util.named(args['django_settings_module'])

    dirs = [os.path.split(
        inspect.getfile(
            inspect.getmodule(
                settings_module)))[0]]
    args['source_directories'] = dirs

    return args


def app_factory(config):
    os.environ['DJANGO_SETTINGS_MODULE'] = config['django_settings_module']

    app = django.core.handlers.wsgi.WSGIHandler()

    return app


########NEW FILE########
__FILENAME__ = memory_watcher
# Copyright (c) 2008, Donovan Preston
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import commands
import os
import optparse
import signal
import sys
import time


MEMORY_WATCH_INTERVAL = 60


def watch_memory(controller_pid, max_memory, max_age):
    if max_age:
        end_time = time.time() + max_age
    else:
        end_time = None

    process_group = os.getpgrp()
    while True:
        if max_age:
            now = time.time()
            if now + MEMORY_WATCH_INTERVAL > end_time:
                time.sleep(end_time - now)
                print "(%s) *** watcher restarting processes! Time limit exceeded." % (
                    os.getpid(), )
                os.kill(controller_pid, signal.SIGHUP)
                end_time = time.time() + max_age
                continue

        time.sleep(MEMORY_WATCH_INTERVAL)
        if max_memory:
            out = commands.getoutput('ps -o rss -g %s' % (process_group, ))
            used_mem = sum(int(x) for x in out.split('\n')[1:])
            if used_mem > max_memory:
                print "(%s) *** memory watcher restarting processes! Memory usage of %s exceeded %s." % (
                    os.getpid(), used_mem, max_memory)
                os.kill(controller_pid, signal.SIGHUP)


if __name__ == '__main__':
    parser = optparse.OptionParser(
        description="Watch all the processes in the process group"
        " and if the total memory used goes over a configurable amount, send a SIGHUP"
        " to a given pid.")
    parser.add_option('-a', '--max-age', dest='max_age', type='int',
        help='If given, the maximum amount of time (in seconds) to run before sending a  '
            'SIGHUP to the given pid.')

    options, positional_args = parser.parse_args()

    if len(positional_args) < 2:
        parser.error("Usage: %s controller_pid max_memory_in_megabytes")

    controller_pid = int(positional_args[0])
    max_memory = int(positional_args[1])
    if max_memory:
        info = 'memory to %s' % (max_memory, )
    else:
        info = ''

    if options.max_age:
        if info:
            info += ' and'
        info = " time to %s" % (options.max_age, )

    print "(%s) watcher starting up, limiting%s." % (
        os.getpid(), info)

    try:
        watch_memory(controller_pid, max_memory, options.max_age)
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = paste_factory
# Copyright (c) 2008, Donovan Preston
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import sys

from paste.deploy import loadwsgi

from spawning import spawning_controller


def config_factory(args):
    if 'config_url' in args:
        config_url = args['config_url']
        relative_to = args['relative_to']
        global_conf = args['global_conf']
    else:
        config_file = os.path.abspath(args['args'][0])
        config_url = 'config:%s' % (os.path.basename(config_file), )
        relative_to = os.path.dirname(config_file)
        global_conf = {}
        for arg in args['args'][1:]:
            key, value = arg.split('=')
            global_conf[key] = value

    ctx = loadwsgi.loadcontext(
        loadwsgi.SERVER,
        config_url,
        relative_to=relative_to,
        global_conf=global_conf)

    watch = args.get('watch', None)
    if watch is None:
        watch = []
    if ctx.global_conf['__file__'] not in watch:
        watch.append(ctx.global_conf['__file__'])
    args['watch'] = watch

    args['app_factory'] = 'spawning.paste_factory.app_factory'
    args['config_url'] = config_url
    args['relative_to'] = relative_to
    args['source_directories'] = [relative_to]
    args['global_conf'] = ctx.global_conf

    debug = ctx.global_conf.get('debug', None)
    if debug is not None:
        args['dev'] = (debug == 'true')
    host = ctx.local_conf.get('host', None)
    if host is not None:
        args['host'] = host
    port = ctx.local_conf.get('port', None)
    if port is not None:
        args['port'] = int(port)
    num_processes = ctx.local_conf.get('num_processes', None)
    if num_processes is not None:
        args['num_processes'] = int(num_processes)
    threadpool_workers = ctx.local_conf.get('threadpool_workers', None)
    if threadpool_workers is not None:
        args['threadpool_workers'] = int(threadpool_workers)

    return args


def app_factory(config):
    return loadwsgi.loadapp(
        config['config_url'],
        relative_to=config['relative_to'],
        global_conf=config['global_conf'])


def server_factory(global_conf, host, port, *args, **kw):
    config_url = 'config:' + os.path.split(global_conf['__file__'])[1]
    relative_to = global_conf['here']

    def run(app):
        args = spawning_controller.DEFAULTS.copy()
        args.update(
            {'config_url': config_url, 'relative_to': relative_to, 'global_conf': global_conf})

        spawning_controller.run_controller(
            'spawning.paste_factory.config_factory', args)

    return run

########NEW FILE########
__FILENAME__ = reloader_dev
# Copyright (c) 2008, Donovan Preston
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Watch files and send a SIGHUP signal to another process
if any of the files change.
"""

try:
	set
except NameError:
	import sets
	set = sets.Set

import optparse, os, signal, sys, tempfile, time
from os.path import join
from distutils import sysconfig

import eventlet

try:
    from procname import setprocname
except ImportError, e:
    setprocname = lambda n: None

def watch_forever(pid, interval, files=None):
    """
    """
    limiter = eventlet.GreenPool()
    module_mtimes = {}
    last_changed_time = None
    while True:
        uniques = set()

        uniques.add(join(sysconfig.get_python_lib(), 'easy-install.pth'))
        uniques.update(list(get_sys_modules_files()))

        if files:
            uniques.update(files)
        ##print uniques
        changed = False
        for filename in uniques:
            try:
                stat = os.stat(filename)
                if stat:
                    mtime = stat.st_mtime
                else:
                    mtime = 0
            except (OSError, IOError):
                continue
            if filename.endswith('.pyc') and os.path.exists(filename[:-1]):
                mtime = max(os.stat(filename[:-1]).st_mtime, mtime)
            if not module_mtimes.has_key(filename):
                module_mtimes[filename] = mtime
            elif module_mtimes[filename] < mtime:
                changed = True
                last_changed_time = mtime
                module_mtimes[filename] = mtime
                print "(%s) * File %r changed" % (os.getpid(), filename)

        if not changed and last_changed_time is not None:
            last_changed_time = None
            if pid:
                print "(%s) ** Sending SIGHUP to %s at %s" % (
                    os.getpid(), pid, time.asctime())
                os.kill(pid, signal.SIGHUP)
                return ## this process is going to die now, no need to keep watching
            else:
                print "EXIT??!!!"
                os._exit(5)

        eventlet.sleep(interval)


def get_sys_modules_files():
    for module in sys.modules.values():
        fn = getattr(module, '__file__', None)
        if fn is not None:
            yield os.path.abspath(fn)


def main():
    parser = optparse.OptionParser()
    parser.add_option("-p", "--pid",
        type="int", dest="pid",
        help="A pid to SIGHUP when a monitored file changes. "
        "If not given, just print a message to stdout and kill this process instead.")
    parser.add_option("-i", "--interval",
        type="int", dest="interval",
        help="The time to wait between scans, in seconds.", default=1)
    options, args = parser.parse_args()

    try:
        watch_forever(options.pid, options.interval)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = reloader_svn
# Copyright (c) 2008, Donovan Preston
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Watch the svn revision returned from svn info and send a SIGHUP
to a process when the revision changes.
"""


import commands, optparse, os, signal, sys, tempfile, time

try:
    from procname import setprocname
except ImportError, e:
    setprocname = lambda n: None


def get_revision(directory):
    cmd = 'svn info'
    if directory is not None:
        cmd = '%s %s' % (cmd, directory)

    try:
        out = commands.getoutput(cmd).split('\n')
    except IOError:
        return

    for line in out:
        if line.startswith('Revision: '):
            return int(line[len('Revision: '):])


def watch_forever(directories, pid, interval):
    setprocname("spawn: svn reloader")
    if directories is None:
        directories = ['.']
    ## Look for externals
    all_svn_repos = set(directories)

    def visit(parent, subdirname, children):
        if '.svn' in children:
            children.remove('.svn')
        status, out = commands.getstatusoutput('svn propget svn:externals %s' % (subdirname, ))
        if status:
            return

        for line in out.split('\n'):
            line = line.strip()
            if not line:
                continue
            name, _external_url = line.split()
            fulldir = os.path.join(parent, subdirname, name)
            ## Don't keep going into the external in the walk()
            try:
                children.remove(name)
            except ValueError:
                print "*** An entry in svn externals doesn't exist, ignoring:", name
            else:
                directories.append(fulldir)
                all_svn_repos.add(fulldir)

    while directories:
        dirname = directories.pop(0)
        os.path.walk(dirname, visit, dirname)

    revisions = {}
    for dirname in all_svn_repos:
        revisions[dirname] = get_revision(dirname)

    print "(%s) svn watcher watching directories: %s" % (
        os.getpid(), list(all_svn_repos))

    while True:
        if pid:
            ## Check to see if our controller is still alive; if not, just exit.
            try:
                os.getpgid(pid)
            except OSError:
                print "(%s) reloader_svn is orphaned; controller %s no longer running. Exiting." % (
                    os.getpid(), pid)
                os._exit(0)

        for dirname in all_svn_repos:
            new_revision = get_revision(dirname)

            if new_revision is not None and new_revision != revisions[dirname]:
                revisions[dirname] = new_revision
                if pid:
                    print "(%s) * SVN revision changed on %s to %s; Sending SIGHUP to %s at %s" % (
                        os.getpid(), dirname, new_revision, pid, time.asctime())
                    os.kill(pid, signal.SIGHUP)
                    os._exit(0)
                else:
                    print "(%s) Revision changed, dying at %s" % (
                        os.getpid(), time.asctime())
                    os._exit(5)

        time.sleep(interval)


def main():
    parser = optparse.OptionParser()
    parser.add_option("-d", "--dir", dest='dirs', action="append",
        help="The directories to do svn info in. If not given, use cwd.")
    parser.add_option("-p", "--pid",
        type="int", dest="pid",
        help="A pid to SIGHUP when the svn revision changes. "
        "If not given, just print a message to stdout and kill this process instead.")
    parser.add_option("-i", "--interval",
        type="int", dest="interval",
        help="The time to wait between scans, in seconds.", default=10)
    options, args = parser.parse_args()

    print "(%s) svn watcher running, controller pid %s" % (os.getpid(), options.pid)
    if options.pid is None:
        options.pid = os.getpid()
    try:
        watch_forever(options.dirs, int(options.pid), options.interval)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = spawning_child
#!/usr/bin/env python
# Copyright (c) 2008, Donovan Preston
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""spawning_child.py
"""

import eventlet
import eventlet.event
import eventlet.greenio
import eventlet.greenthread
import eventlet.hubs
import eventlet.wsgi

import errno
import optparse
import os
import signal
import socket
import sys
import time

import spawning.util
from spawning import setproctitle, reloader_dev

try:
    import simplejson as json
except ImportError:
    import json


class URLInterceptor(object):
    """
    Intercepts one or more paths.
    """

    paths = []

    def __init__(self, app, paths=[]):
        """
        Creates an instance.

        :Parameters:
           - `app`: Application to fall through to
        """
        self.app = app

    def _intercept(self, env, start_response):
        """
        Executes business logic.

        :Parameters:
           - `env`: environment information
           - `start_response`: wsgi response function
        """
        raise NotImplementedError('_intercept must be overridden')

    def __call__(self, env, start_response):
        """
        Dispatches input to the proper method.

        :Parameters:
           - `env`: environment information
           - `start_response`: wsgi response function
        """
        if env['PATH_INFO'] in self.paths:
            return self._intercept(env, start_response)
        return self.app(env, start_response)


class FigleafCoverage(URLInterceptor):

    paths = ['/_coverage']

    def __init__(self, app):
        URLInterceptor.__init__(self, app)
        import figleaf
        figleaf.start()

    def _intercept(self, env, start_response):
        import figleaf
        try:
            import cPickle as pickle
        except ImportError:
            import pickle

        coverage = figleaf.get_info()
        s = pickle.dumps(coverage)
        start_response("200 OK", [('Content-type', 'application/x-pickle')])
        return [s]


class SystemInfo(URLInterceptor):
    """
    Intercepts /_sysinfo path and returns json data.
    """

    paths = ['/_sysinfo']

    def _intercept(self, env, start_response):
        """
        Executes business logic.

        :Parameters:
           - `env`: environment information
           - `start_response`: wsgi response function
        """
        import spawning.util.system
        start_response("200 OK", [('Content-type', 'application/json')])
        return [json.dumps(spawning.util.system.System())]


class ExitChild(Exception):
    pass

class ChildStatus(object):
    def __init__(self, controller_port):
        self.controller_url =  "http://127.0.0.1:%s/" % controller_port
        self.server = None
        
    def send_status_to_controller(self):
        try:
            child_status = {'pid':os.getpid()}
            if self.server: 
                child_status['concurrent_requests'] = \
                    self.server.outstanding_requests
            else:
                child_status['error'] = 'Starting...'
            body = json.dumps(child_status)
            import urllib2
            urllib2.urlopen(self.controller_url, body)
        except (KeyboardInterrupt, SystemExit,
             eventlet.greenthread.greenlet.GreenletExit):
            raise
        except Exception, e:  
            # we really don't want exceptions here to stop read_pipe_and_die
            pass

_g_status = None
def init_statusobj(status_port):
    global _g_status
    if status_port:
        _g_status = ChildStatus(status_port)
def get_statusobj():
    return _g_status


def read_pipe_and_die(the_pipe, server_coro):
    dying = False
    try:
        while True:
            eventlet.hubs.trampoline(the_pipe, read=True)
            c = os.read(the_pipe, 1)
            # this is how the controller tells the child to send a status update
            if c == 's' and get_statusobj():
                get_statusobj().send_status_to_controller()
            elif not dying:
                dying = True  # only send ExitChild once
                eventlet.greenthread.kill(server_coro, ExitChild)
                # continue to listen for status pings while dying
    except socket.error:
        pass
    # if here, perhaps the controller's process went down; we should die too if
    # we aren't already
    if not dying:
        eventlet.greenthread.kill(server_coro, KeyboardInterrupt)


def deadman_timeout(signum, frame):
    print "(%s) !!! Deadman timer expired, killing self with extreme prejudice" % (
        os.getpid(), )
    os.kill(os.getpid(), signal.SIGKILL)

def tpool_wsgi(app):
    from eventlet import tpool
    def tpooled_application(e, s):
        result = tpool.execute(app, e, s)
        # return builtins directly
        if isinstance(result, (basestring, list, tuple)):
            return result
        else:
            # iterators might execute code when iterating over them,
            # so we wrap them in a Proxy object so every call to
            # next() goes through tpool
            return tpool.Proxy(result)
    return tpooled_application


def warn_controller_of_imminent_death(controller_pid):
    # The controller responds to a SIGUSR1 by kicking off a new child process.
    try:
        os.kill(controller_pid, signal.SIGUSR1)
    except OSError, e:
        if not e.errno == errno.ESRCH:
            raise


def serve_from_child(sock, config, controller_pid):
    threads = config.get('threadpool_workers', 0)
    wsgi_application = spawning.util.named(config['app_factory'])(config)

    if config.get('coverage'):
        wsgi_application = FigleafCoverage(wsgi_application)
    if config.get('sysinfo'):
        wsgi_application = SystemInfo(wsgi_application)

    if threads >= 1:
        # proxy calls of the application through tpool
        wsgi_application = tpool_wsgi(wsgi_application)
    elif threads != 1:
        print "(%s) not using threads, installing eventlet cooperation monkeypatching" % (
            os.getpid(), )
        eventlet.patcher.monkey_patch(all=False, socket=True)

    host, port = sock.getsockname()

    access_log_file = config.get('access_log_file')
    if access_log_file is not None:
        access_log_file = open(access_log_file, 'a')

    max_age = 0
    if config.get('max_age'):
        max_age = int(config.get('max_age'))

    server_event = eventlet.event.Event()
    # the status object wants to have a reference to the server object
    if config.get('status_port'):
        def send_server_to_status(server_event):
            server = server_event.wait()
            get_statusobj().server = server
        eventlet.spawn(send_server_to_status, server_event)

    http_version = config.get('no_keepalive') and 'HTTP/1.0' or 'HTTP/1.1'
    try:
        wsgi_args = (sock, wsgi_application)
        wsgi_kwargs = {'log' : access_log_file, 'server_event' : server_event, 'max_http_version' : http_version}
        if config.get('no_keepalive'):
            wsgi_kwargs.update({'keepalive' : False})
        if max_age:
            wsgi_kwargs.update({'timeout_value' : True})
            eventlet.with_timeout(max_age, eventlet.wsgi.server, *wsgi_args,
                    **wsgi_kwargs)
            warn_controller_of_imminent_death(controller_pid)
        else:
            eventlet.wsgi.server(*wsgi_args, **wsgi_kwargs)
    except KeyboardInterrupt:
        # controller probably doesn't know that we got killed by a SIGINT
        warn_controller_of_imminent_death(controller_pid)
    except ExitChild:
        pass  # parent killed us, it already knows we're dying

    ## Set a deadman timer to violently kill the process if it doesn't die after
    ## some long timeout.
    signal.signal(signal.SIGALRM, deadman_timeout)
    signal.alarm(config['deadman_timeout'])

    ## Once we get here, we just need to handle outstanding sockets, not
    ## accept any new sockets, so we should close the server socket.
    sock.close()
    
    server = server_event.wait()

    last_outstanding = None
    while server.outstanding_requests:
        if last_outstanding != server.outstanding_requests:
            print "(%s) %s requests remaining, waiting... (timeout after %s)" % (
                os.getpid(), server.outstanding_requests, config['deadman_timeout'])
        last_outstanding = server.outstanding_requests
        eventlet.sleep(0.1)

    print "(%s) *** Child exiting: all requests completed at %s" % (
        os.getpid(), time.asctime())


def child_sighup(*args, **kwargs):
    exit(0)


def main():
    parser = optparse.OptionParser()
    parser.add_option("-r", "--reload",
        action='store_true', dest='reload',
        help='If --reload is passed, reload the server any time '
        'a loaded module changes.')

    options, args = parser.parse_args()

    if len(args) != 5:
        print "Usage: %s controller_pid httpd_fd death_fd factory_qual factory_args" % (
            sys.argv[0], )
        sys.exit(1)

    controller_pid, httpd_fd, death_fd, factory_qual, factory_args = args
    controller_pid = int(controller_pid)
    config = spawning.util.named(factory_qual)(json.loads(factory_args))

    setproctitle("spawn: child (%s)" % ", ".join(config.get("args")))
    
    ## Set up status reporter, if requested
    init_statusobj(config.get('status_port'))

    ## Set up the reloader
    if config.get('reload'):
        watch = config.get('watch', None)
        if watch:
            watching = ' and %s' % watch
        else:
            watching = ''
        print "(%s) reloader watching sys.modules%s" % (os.getpid(), watching)
        eventlet.spawn(
            reloader_dev.watch_forever, controller_pid, 1, watch)

    ## The parent will catch sigint and tell us to shut down
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    ## Expect a SIGHUP when we want the child to die
    signal.signal(signal.SIGHUP, child_sighup)
    eventlet.spawn(read_pipe_and_die, int(death_fd), eventlet.getcurrent())

    ## Make the socket object from the fd given to us by the controller
    sock = eventlet.greenio.GreenSocket(
        socket.fromfd(int(httpd_fd), socket.AF_INET, socket.SOCK_STREAM))

    serve_from_child(
        sock, config, controller_pid)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = spawning_controller
#!/usr/bin/env python
# Copyright (c) 2008, Donovan Preston
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from __future__ import with_statement

import eventlet
eventlet.monkey_patch()

import commands
import datetime
import errno
import logging
import optparse
import pprint
import signal
import socket
import sys
import time
import traceback

try:
    import simplejson as json
except ImportError:
    import json


import eventlet.backdoor
from eventlet.green import os

import spawning
import spawning.util

KEEP_GOING = True
RESTART_CONTROLLER = False
PANIC = False


DEFAULTS = {
    'num_processes': 4,
    'threadpool_workers': 4,
    'watch': [],
    'dev': True,
    'host': '',
    'port': 8080,
    'deadman_timeout': 10,
    'max_memory': None,
}

def print_exc(msg="Exception occured!"):
    print >>sys.stderr, "(%d) %s" % (os.getpid(), msg)
    traceback.print_exc()

def environ():
    env = os.environ.copy()
    # to avoid duplicates in the new sys.path
    revised_paths = set()
    new_path = list()
    for path in sys.path:
        if os.path.exists(path) and path not in revised_paths:
            revised_paths.add(path)
            new_path.append(path)
    current_directory = os.path.realpath('.')
    if current_directory not in revised_paths:
        new_path.append(current_directory)

    env['PYTHONPATH'] = ':'.join(new_path)
    return env

class Child(object):
    def __init__(self, pid, kill_pipe):
        self.pid = pid
        self.kill_pipe = kill_pipe
        self.active = True
        self.forked_at = datetime.datetime.now()

class Controller(object):
    sock = None
    factory = None
    args = None
    config = None
    children = None
    keep_going = True
    panic = False
    log = None
    controller_pid = None
    num_processes = 0

    def __init__(self, sock, factory, args, **kwargs):
        self.sock = sock
        self.factory = factory
        self.config = spawning.util.named(factory)(args)
        self.args = args
        self.children = {}
        self.log = logging.getLogger('Spawning')
        if not kwargs.get('log_handler'):
            self.log.addHandler(logging.StreamHandler())
        self.log.setLevel(logging.DEBUG)
        self.controller_pid = os.getpid()
        self.num_processes = int(self.config.get('num_processes', 0))
        self.started_at = datetime.datetime.now()

    def spawn_children(self, number=1):
        parent_pid = os.getpid()

        for i in range(number):
            child_side, parent_side = os.pipe()
            try:
                child_pid = os.fork()
            except:
                print_exc('Could not fork child! Panic!')
                ### TODO: restart

            if not child_pid:      # child process
                os.close(parent_side)
                command = [sys.executable, '-c',
                    'import sys; from spawning import spawning_child; spawning_child.main()',
                    str(parent_pid),
                    str(self.sock.fileno()),
                    str(child_side),
                    self.factory,
                    json.dumps(self.args)]
                if self.args['reload'] == 'dev':
                    command.append('--reload')
                env = environ()
                tpool_size = int(self.config.get('threadpool_workers', 0))
                assert tpool_size >= 0, (tpool_size, 'Cannot have a negative --threads argument')
                if not tpool_size in (0, 1):
                    env['EVENTLET_THREADPOOL_SIZE'] = str(tpool_size)
                os.execve(sys.executable, command, env)

            # controller process
            os.close(child_side)
            self.children[child_pid] = Child(child_pid, parent_side)

    def children_count(self):
        return len(self.children)

    def runloop(self):
        while self.keep_going:
            eventlet.sleep(0.1)
            ## Only start the number of children we need
            number = self.num_processes - self.children_count()
            if number > 0:
                self.log.debug('Should start %d new children', number)
                self.spawn_children(number=number)
                continue

            if not self.children:
                ## If we don't yet have children, let's loop
                continue

            pid, result = None, None
            try:
                pid, result = os.wait()
            except OSError, e:
                if e.errno != errno.EINTR:
                    raise

            if pid and self.children.get(pid):
                try:
                    child = self.children.pop(pid)
                    os.close(child.kill_pipe)
                except (IOError, OSError):
                    pass

            if result:
                signum = os.WTERMSIG(result)
                exitcode = os.WEXITSTATUS(result)
                self.log.info('(%s) Child died from signal %s with code %s',
                              pid, signum, exitcode)

    def handle_sighup(self, *args, **kwargs):
        ''' Pass `no_restart` to prevent restarting the run loop '''
        self.kill_children()
        self.spawn_children(number=self.num_processes)
        # TODO: nothing seems to use no_restart, can it be removed?
        if not kwargs.get('no_restart', True):
            self.runloop()

    def kill_children(self):
        for pid, child in self.children.items():
            try:
                os.write(child.kill_pipe, 'k')
                child.active = False
                # all maintenance of children's membership happens in runloop()
                # as children die and os.wait() gets results
            except OSError, e:
                if e.errno != errno.EPIPE:
                    raise

    def handle_deadlychild(self, *args, **kwargs):
        """
            SIGUSR1 handler, will spin up an extra child to handle the load
            left over after a previously running child stops taking connections
            and "dies" gracefully
        """
        if self.keep_going:
            self.spawn_children(number=1)

    def run(self):
        self.log.info('(%s) *** Controller starting at %s' % (self.controller_pid,
                time.asctime()))

        if self.config.get('pidfile'):
            with open(self.config.get('pidfile'), 'w') as fd:
                fd.write('%s\n' % self.controller_pid)

        spawning.setproctitle("spawn: controller " + self.args.get('argv_str', ''))

        if self.sock is None:
            self.sock = bind_socket(self.config)

        signal.signal(signal.SIGHUP, self.handle_sighup)
        signal.signal(signal.SIGUSR1, self.handle_deadlychild)

        if self.config.get('status_port'):
            from spawning.util import status
            eventlet.spawn(status.Server, self,
                self.config['status_host'], self.config['status_port'])

        try:
            self.runloop()
        except KeyboardInterrupt:
            self.keep_going = False
            self.kill_children()
        self.log.info('(%s) *** Controller exiting' % (self.controller_pid))

def bind_socket(config):
    sleeptime = 0.5
    host = config.get('host', '')
    port = config.get('port', 8080)
    for x in range(8):
        try:
            sock = eventlet.listen((host, port))
            break
        except socket.error, e:
            if e[0] != errno.EADDRINUSE:
                raise
            print "(%s) socket %s:%s already in use, retrying after %s seconds..." % (
                os.getpid(), host, port, sleeptime)
            eventlet.sleep(sleeptime)
            sleeptime *= 2
    else:
        print "(%s) could not bind socket %s:%s, dying." % (
            os.getpid(), host, port)
        sys.exit(1)
    return sock

def set_process_owner(spec):
    import pwd, grp
    if ":" in spec:
        user, group = spec.split(":", 1)
    else:
        user, group = spec, None
    if group:
        os.setgid(grp.getgrnam(group).gr_gid)
    if user:
        os.setuid(pwd.getpwnam(user).pw_uid)
    return user, group

def start_controller(sock, factory, factory_args):
    c = Controller(sock, factory, factory_args)
    installGlobal(c)
    c.run()

def main():
    current_directory = os.path.realpath('.')
    if current_directory not in sys.path:
        sys.path.append(current_directory)

    parser = optparse.OptionParser(description="Spawning is an easy-to-use and flexible wsgi server. It supports graceful restarting so that your site finishes serving any old requests while starting new processes to handle new requests with the new code. For the simplest usage, simply pass the dotted path to your wsgi application: 'spawn my_module.my_wsgi_app'", version=spawning.__version__)
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true', help='Display verbose configuration '
        'information when starting up or restarting.')
    parser.add_option("-f", "--factory", dest='factory', default='spawning.wsgi_factory.config_factory',
        help="""Dotted path (eg mypackage.mymodule.myfunc) to a callable which takes a dictionary containing the command line arguments and figures out what needs to be done to start the wsgi application. Current valid values are: spawning.wsgi_factory.config_factory, spawning.paste_factory.config_factory, and spawning.django_factory.config_factory. The factory used determines what the required positional command line arguments will be. See the spawning.wsgi_factory module for documentation on how to write a new factory.
        """)
    parser.add_option("-i", "--host",
        dest='host', default=DEFAULTS['host'],
        help='The local ip address to bind.')
    parser.add_option("-p", "--port",
        dest='port', type='int', default=DEFAULTS['port'],
        help='The local port address to bind.')
    parser.add_option("-s", "--processes",
        dest='processes', type='int', default=DEFAULTS['num_processes'],
        help='The number of unix processes to start to use for handling web i/o.')
    parser.add_option("-t", "--threads",
        dest='threads', type='int', default=DEFAULTS['threadpool_workers'],
        help="The number of posix threads to use for handling web requests. "
            "If threads is 0, do not use threads but instead use eventlet's cooperative "
            "greenlet-based microthreads, monkeypatching the socket and pipe operations which normally block "
            "to cooperate instead. Note that most blocking database api modules will not "
            "automatically cooperate.")
    parser.add_option('-d', '--daemonize', dest='daemonize', action='store_true',
        help="Daemonize after starting children.")
    parser.add_option('-u', '--chuid', dest='chuid', metavar="ID",
        help="Change user ID in daemon mode (and group ID if given, "
             "separate with colon.)")
    parser.add_option('--pidfile', dest='pidfile', metavar="FILE",
        help="Write own process ID to FILE in daemon mode.")
    parser.add_option('--stdout', dest='stdout', metavar="FILE",
        help="Redirect stdout to FILE in daemon mode.")
    parser.add_option('--stderr', dest='stderr', metavar="FILE",
        help="Redirect stderr to FILE in daemon mode.")
    parser.add_option('-w', '--watch', dest='watch', action='append',
        help="Watch the given file's modification time. If the file changes, the web server will "
            'restart gracefully, allowing old requests to complete in the old processes '
            'while starting new processes with the latest code or configuration.')
    ## TODO Hook up the svn reloader again
    parser.add_option("-r", "--reload",
        type='str', dest='reload',
        help='If --reload=dev is passed, reload any time '
        'a loaded module or configuration file changes.')
    parser.add_option("--deadman", "--deadman_timeout",
        type='int', dest='deadman_timeout', default=DEFAULTS['deadman_timeout'],
        help='When killing an old i/o process because the code has changed, don\'t wait '
        'any longer than the deadman timeout value for the process to gracefully exit. '
        'If all requests have not completed by the deadman timeout, the process will be mercilessly killed.')
    parser.add_option('-l', '--access-log-file', dest='access_log_file', default=None,
        help='The file to log access log lines to. If not given, log to stdout. Pass /dev/null to discard logs.')
    parser.add_option('-c', '--coverage', dest='coverage', action='store_true',
        help='If given, gather coverage data from the running program and make the '
            'coverage report available from the /_coverage url. See the figleaf docs '
            'for more info: http://darcs.idyll.org/~t/projects/figleaf/doc/')
    parser.add_option('--sysinfo', dest='sysinfo', action='store_true',
        help='If given, gather system information data and make the '
            'report available from the /_sysinfo url.')
    parser.add_option('-m', '--max-memory', dest='max_memory', type='int', default=0,
        help='If given, the maximum amount of memory this instance of Spawning '
            'is allowed to use. If all of the processes started by this Spawning controller '
            'use more than this amount of memory, send a SIGHUP to the controller '
            'to get the children to restart.')
    parser.add_option('--backdoor', dest='backdoor', action='store_true',
            help='Start a backdoor bound to localhost:3000')
    parser.add_option('-a', '--max-age', dest='max_age', type='int',
        help='If given, the maximum amount of time (in seconds) an instance of spawning_child '
            'is allowed to run. Once this time limit has expired the child will'
            'gracefully kill itself while the server starts a replacement.')
    parser.add_option('--no-keepalive', dest='no_keepalive', action='store_true',
            help='Disable HTTP/1.1 KeepAlive')
    parser.add_option('-z', '--z-restart-args', dest='restart_args',
        help='For internal use only')
    parser.add_option('--status-port', dest='status_port', type='int', default=0,
        help='If given, hosts a server status page at that port.  Two pages are served: a human-readable HTML version at http://host:status_port/status, and a machine-readable version at http://host:status_port/status.json')
    parser.add_option('--status-host', dest='status_host', type='string', default='',
        help='If given, binds the server status page to the specified local ip address.  Defaults to the same value as --host.  If --status-port is not supplied, the status page will not be activated.')

    options, positional_args = parser.parse_args()

    if len(positional_args) < 1 and not options.restart_args:
        parser.error("At least one argument is required. "
            "For the default factory, it is the dotted path to the wsgi application "
            "(eg my_package.my_module.my_wsgi_application). For the paste factory, it "
            "is the ini file to load. Pass --help for detailed information about available options.")

    if options.backdoor:
        try:
            eventlet.spawn(eventlet.backdoor.backdoor_server, eventlet.listen(('localhost', 3000)))
        except Exception, ex:
            sys.stderr.write('**> Error opening backdoor: %s\n' % ex)

    sock = None

    if options.restart_args:
        restart_args = json.loads(options.restart_args)
        factory = restart_args['factory']
        factory_args = restart_args['factory_args']

        start_delay = restart_args.get('start_delay')
        if start_delay is not None:
            factory_args['start_delay'] = start_delay
            print "(%s) delaying startup by %s" % (os.getpid(), start_delay)
            time.sleep(start_delay)

        fd = restart_args.get('fd')
        if fd is not None:
            sock = socket.fromfd(restart_args['fd'], socket.AF_INET, socket.SOCK_STREAM)
            ## socket.fromfd doesn't result in a socket object that has the same fd.
            ## The old fd is still open however, so we close it so we don't leak.
            os.close(restart_args['fd'])
        return start_controller(sock, factory, factory_args)

    ## We're starting up for the first time.
    if options.daemonize:
        # Do the daemon dance. Note that this isn't what is considered good
        # daemonization, because frankly it's convenient to keep the file
        # descriptiors open (especially when there are prints scattered all
        # over the codebase.)
        # What we do instead is fork off, create a new session, fork again.
        # This leaves the process group in a state without a session
        # leader.
        pid = os.fork()
        if not pid:
            os.setsid()
            pid = os.fork()
            if pid:
                os._exit(0)
        else:
            os._exit(0)
        print "(%s) now daemonized" % (os.getpid(),)
        # Close _all_ open (and othewise!) files.
        import resource
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if maxfd == resource.RLIM_INFINITY:
            maxfd = 4096
        for fdnum in xrange(maxfd):
            try:
                os.close(fdnum)
            except OSError, e:
                if e.errno != errno.EBADF:
                    raise
        # Remap std{in,out,err}
        devnull = os.open(os.path.devnull, os.O_RDWR)
        oflags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if devnull != 0:  # stdin
            os.dup2(devnull, 0)
        if options.stdout:
            stdout_fd = os.open(options.stdout, oflags)
            if stdout_fd != 1:
                os.dup2(stdout_fd, 1)
                os.close(stdout_fd)
        else:
            os.dup2(devnull, 1)
        if options.stderr:
            stderr_fd = os.open(options.stderr, oflags)
            if stderr_fd != 2:
                os.dup2(stderr_fd, 2)
                os.close(stderr_fd)
        else:
            os.dup2(devnull, 2)
        # Change user & group ID.
        if options.chuid:
            user, group = set_process_owner(options.chuid)
            print "(%s) set user=%s group=%s" % (os.getpid(), user, group)
    else:
        # Become a process group leader only if not daemonizing.
        os.setpgrp()

    ## Fork off the thing that watches memory for this process group.
    controller_pid = os.getpid()
    if options.max_memory and not os.fork():
        env = environ()
        from spawning import memory_watcher
        basedir, cmdname = os.path.split(memory_watcher.__file__)
        if cmdname.endswith('.pyc'):
            cmdname = cmdname[:-1]

        os.chdir(basedir)
        command = [
            sys.executable,
            cmdname,
            '--max-age', str(options.max_age),
            str(controller_pid),
            str(options.max_memory)]
        os.execve(sys.executable, command, env)

    factory = options.factory

    # If you tell me to watch something, I'm going to reload then
    if options.watch:
        options.reload = True

    if options.status_port == options.port:
        options.status_port = None
        sys.stderr.write('**> Status port cannot be the same as the service port, disabling status.\n')


    factory_args = {
        'verbose': options.verbose,
        'host': options.host,
        'port': options.port,
        'num_processes': options.processes,
        'threadpool_workers': options.threads,
        'watch': options.watch,
        'reload': options.reload,
        'deadman_timeout': options.deadman_timeout,
        'access_log_file': options.access_log_file,
        'pidfile': options.pidfile,
        'coverage': options.coverage,
        'sysinfo': options.sysinfo,
        'no_keepalive' : options.no_keepalive,
        'max_age' : options.max_age,
        'argv_str': " ".join(sys.argv[1:]),
        'args': positional_args,
        'status_port': options.status_port,
        'status_host': options.status_host or options.host
    }
    start_controller(sock, factory, factory_args)

_global_attr_name_ = '_spawning_controller_'
def installGlobal(controller):
    setattr(sys, _global_attr_name_, controller)

def globalController():
    return getattr(sys, _global_attr_name_, None)


if __name__ == '__main__':
    main()




########NEW FILE########
__FILENAME__ = log_parser
import time
from datetime import datetime, timedelta
import sys
import optparse
import re

__all__ = ['parse_line', 'parse_lines', 'parse_casual_time',
    'group_parsed_lines', 'select_timerange']

month_names = {'Jan': 1, 'Feb': 2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6, 'Jul':7, 
    'Aug':8,  'Sep': 9, 'Oct':10, 'Nov': 11, 'Dec': 12}


def parse_line(line):
    """ Parses a Spawning log line into a dictionary of fields.
    
    Returns the following fields: 
    * client_ip : The remote IP address.
    * date : datetime object representing when the request completed
    * method : HTTP method
    * path : url path
    * version : HTTP version
    * status_code : HTTP status code
    * size : length of the body
    * duration : time in seconds to complete the request
    """
    # note that a split-based version of the function is faster than
    # a regexp-based version
    segs = line.split()
    if len(segs) != 11:
        return None
    retval = {}
    try:
        retval['client_ip'] = segs[0]
        if segs[1] != '-' or segs[2] != '-':
            return None
        if segs[3][0] != '[' or segs[4][-1] != ']':
            return None
        # time parsing by explicitly poking at string slices is much faster 
        # than strptime, but it won't work in non-English locales because of 
        # the month names
        d = segs[3]
        t = segs[4]
        retval['date'] = datetime(
            int(d[8:12]),         # year
            month_names[d[4:7]],  # month
            int(d[1:3]),          # day
            int(t[0:2]),          # hour
            int(t[3:5]),          # minute
            int(t[6:8]))          # second
        if segs[5][0] != '"' or segs[7][-1] != '"':
            return None
        retval['method'] = segs[5][1:]
        retval['path'] = segs[6]
        retval['version'] = segs[7][:-1]
        retval['status_code'] = int(segs[8])
        retval['size'] = int(segs[9])
        retval['duration'] = float(segs[10])
    except (IndexError, ValueError):
        return None
    return retval
    
    
def parse_lines(fd):
    """Generator function that accepts an iterable file-like object and 
    yields all the parseable lines found in it.
    """
    for line in fd:
        parsed = parse_line(line)
        if parsed is not None:
            yield parsed


time_intervals = {"sec":1, "min":60, "hr":3600, "day": 86400,
                  "second":1, "minute":60, "hour":3600,
                  "s":1, "m":60, "h":3600, "d":86400}
for k,v in time_intervals.items():  # pluralize
    time_intervals[k + "s"] = v
    
    
def parse_casual_time(timestr, relative_to):
    """Lenient relative time parser.  Returns a datetime object if it can.
    
    Accepts such human-friendly times as "-1 hour", "-30s", "15min", "2d", "now".
    Any such relative time is interpreted as a delta applied to the relative_to
    argument, which should be a datetime.
    """
    timestr = timestr.lower()
    try:
        return datetime(*(time.strptime(timestr)[0:6]))
    except ValueError:
        pass
    if timestr == "now":
        return datetime.now()
    # match stuff like "-1 hour", "-30s"
    m = re.match(r'([-0-9.]+)\s*(\w+)?', timestr)
    if m:
        intervalsz = 1
        if len(m.groups()) > 1 and m.group(2) in time_intervals:
            intervalsz = time_intervals[m.group(2)]
        relseconds = float(m.group(1)) * intervalsz
        return relative_to + timedelta(seconds=relseconds)

def group_parsed_lines(lines, field):
    """Aggregates the parsed log lines by a field.  Counts
    the log lines in each group and their average duration.  The return
    value is a dict, where the keys are the unique field values, and the values
    are dicts of count, avg_duration, and the key.
    """
    grouped = {}
    for parsed in lines:
        key = parsed[field]
        summary = grouped.setdefault(key, {'count':0, 'total_duration':0.0})
        summary[field] = key
        summary['count'] += 1
        summary['total_duration'] += parsed['duration']
    # average dat up
    for summary in grouped.values():
        summary['avg_duration'] = summary['total_duration']/summary['count']
        del summary['total_duration']
    return grouped

def select_timerange(lines, earliest=None, latest=None):
    """ Generator that accepts an iterable of parsed log lines and yields
    the log lines that are between the earliest and latest dates.  If
    either earliest or latest is None, it is ignored."""
    for parsed in lines:
        if earliest and parsed['date'] < earliest:
            continue
        if latest and parsed['date'] > latest:
            continue
        yield parsed


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option('--earliest', dest='earliest', default=None,
        help='Earliest date to count, either as a full date or a relative time \
such as "-1 hour".  Relative to --latest, so you generally want to\
specify a negative relative.')
    parser.add_option('--latest', dest='latest', default=None,
        help='Latest date to count, either as a full date or a relative time\
such as "-30s".  Relative to now.')
    parser.add_option('--group-by', dest='group_by', default='path',
        help='Compute counts and aggregates for log lines grouped by this\
attribute.  Good values include "status_code", "method", and\
"path" (the default).')
    opts, args = parser.parse_args()

    if opts.latest:
        opts.latest = parse_casual_time(opts.latest, datetime.now())
    if opts.earliest:
        opts.earliest = parse_casual_time(opts.earliest, 
                                            opts.latest or datetime.now())
    if opts.earliest or opts.latest:
        print "Including dates between", \
            opts.earliest or "the beginning of time", "and", opts.latest or "now"
    
    parsed_lines = parse_lines(sys.stdin)
    grouped = group_parsed_lines(
        select_timerange(parsed_lines, opts.earliest, opts.latest),
        opts.group_by)
    
    flat = grouped.values()
    flat.sort(key=lambda x: x['count'])
    flat.reverse()
    print "Count\tAvg Dur\t%s" % opts.group_by
    for summary in flat:
        print "%d\t%.4f\t%s" % (summary['count'], 
            summary['avg_duration'], summary[opts.group_by])


########NEW FILE########
__FILENAME__ = status
import datetime
try:
    import json
except ImportError:
    import simplejson as json

import eventlet
from eventlet import event
from eventlet import wsgi
from eventlet.green import os

class Server(object):
    def __init__(self, controller, host, port):
        self.controller = controller
        self.host = host
        self.port = port
        self.status_waiter = None
        self.child_events = {}
        socket = eventlet.listen((host, port))
        wsgi.server(socket, self.application)

    def get_status_data(self):
        # using a waiter because we only want one child collection ping
        # happening at a time; if there are multiple concurrent status requests,
        # they all simply share the same set of data results
        if self.status_waiter is None:
            self.status_waiter = eventlet.spawn(self._collect_status_data)
        return self.status_waiter.wait()
    
    def _collect_status_data(self):
        try:
            now = datetime.datetime.now()
            children = self.controller.children.values()
            status_data = {
                'active_children_count':len([c 
                    for c in children
                    if c.active]),
                'killed_children_count':len([c 
                    for c in children
                    if not c.active]),
                'configured_children_count':self.controller.num_processes,
                'now':now.ctime(),
                'pid':os.getpid(),
                'uptime':format_timedelta(now - self.controller.started_at),
                'started_at':self.controller.started_at.ctime(),
                'config':self.controller.config}
            # fire up a few greenthreads to wait on children's responses
            p = eventlet.GreenPile()
            for child in self.controller.children.values():
                p.spawn(self.collect_child_status, child)
            status_data['children'] = dict([pid_cd for pid_cd in p])
            
            # total concurrent connections
            status_data['concurrent_requests'] = sum([
                child.get('concurrent_requests', 0)
                for child in status_data['children'].values()])
        finally:
            # wipe out the waiter so that subsequent requests create new ones
            self.status_waiter = None
        return status_data

    def collect_child_status(self, child):
        self.child_events[child.pid] = event.Event()
        try:
            try:
                # tell the child to POST its status to us, we handle it in the
                # wsgi application below
                eventlet.hubs.trampoline(child.kill_pipe, write=True)
                os.write(child.kill_pipe, 's')
                t = eventlet.Timeout(1)
                results = self.child_events[child.pid].wait()
                t.cancel()
            except (OSError, IOError), e:
                results = {'error': "%s %s" % (type(e), e)}
            except eventlet.Timeout:
                results = {'error':'Timed out'}
        finally:
            self.child_events.pop(child.pid, None)
            
        results.update({
            'pid':child.pid, 
            'active':child.active,
            'uptime':format_timedelta(datetime.datetime.now() - child.forked_at),
            'forked_at':child.forked_at.ctime()})
        return child.pid, results

    def application(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'GET':
            status_data = self.get_status_data()
            if environ['PATH_INFO'] == '/status':
                start_response('200 OK', [('content-type', 'text/html')])
                return [fill_template(status_data)]
            elif environ['PATH_INFO'] == '/status.json':
                start_response('200 OK', [('content-type', 'application/json')])
                return [json.dumps(status_data, indent=2)]
                
        elif environ['REQUEST_METHOD'] == 'POST':
            # it's a client posting its stats to us
            body = environ['wsgi.input'].read()
            child_status = json.loads(body)
            pid = child_status['pid']
            if pid in self.child_events:
                self.child_events[pid].send(child_status)
                start_response('200 OK', [('content-type', 'application/json')])
            else:
                start_response('500 Internal Server Error', 
                               [('content-type', 'text/plain')])
                print "Don't know about child pid %s" % pid
            return [""]
        
        # fallthrough case
        start_response('404 Not Found', [('content-type', 'text/plain')])
        return [""]

def format_timedelta(t):
    """Based on how HAProxy's status page shows dates.
    10d 14h
    3h 20m
    1h 0m
    12m
    15s
    """
    seconds = t.seconds
    if t.days > 0:
        return "%sd %sh" % (t.days, int(seconds/3600))
    else:
        if seconds > 3600:
            hours = int(seconds/3600)
            seconds -= hours*3600
            return "%sh %sm" % (hours, int(seconds/60))
        else:
            if seconds > 60:
                return "%sm" % int(seconds/60)
            else:
                return "%ss" % seconds

class Tag(object):
    """Yeah, there's a templating DSL in this status module.  Deal with it."""
    def __init__(self, name, *children, **attrs):
        self.name = name
        self.attrs = attrs
        self.children = list(children)

    def __str__(self):
        al = []
        for name, val in self.attrs.iteritems():
            if name == 'cls':
                name = "class"
            if isinstance(val, (list, tuple)):
                val = " ".join(val)
            else:
                val = str(val)
            al.append('%s="%s"' % (name, val))
        if al:
            attrstr = " " + " ".join(al) + " "
        else:
            attrstr = ""
        cl = []
        for child in self.children:
            cl.append(str(child))
        if cl:
            childstr = "\n" + "\n".join(cl) + "\n"
        else:
            childstr = ""
        return "<%s%s>%s</%s>" % (self.name, attrstr, childstr, self.name)

def make_tag(name):
    return lambda *c, **a: Tag(name, *c, **a)
p = make_tag('p')
div = make_tag('div')
table = make_tag('table')
tr = make_tag('tr')
th = make_tag('th')
td = make_tag('td')
h2 = make_tag('h2')
span = make_tag('span')

def fill_template(status_data):
    # controller status
    cont_div = table(id='controller')
    cont_div.children.append(tr(th("PID:", title="Controller Process ID"), 
        td(status_data['pid'])))
    cont_div.children.append(tr(th("Uptime:", title="Time since launch"), 
        td(status_data['uptime'])))
    cont_div.children.append(tr(th("Host:", title="Host and port server is listening on, all means all interfaces."), 
        td("%s:%s" % (status_data['config']['host'] or "all",
            status_data['config']['port']))))
    cont_div.children.append(tr(th("Threads:", title="Threads per child"), 
        td(status_data['config']['threadpool_workers'])))
    cont_div = div(cont_div)
    
    # children headers and summaries
    child_div = div(h2("Child Processes"))
    count_td = td(status_data['active_children_count'], "/", 
                  status_data['configured_children_count'])
    if status_data['active_children_count'] < \
       status_data['configured_children_count']:
        count_td.attrs['cls'] = "error"
        count_td.children.append(
            span("(", status_data['killed_children_count'], ")"))
    children_table = table(
      tr(
        th('PID', title="Process ID"), 
        th('Active', title="Accepting New Requests"), 
        th('Uptime', title="Uptime"), 
        th('Concurrent', title="Concurrent Requests")),
      tr(
        td("Total"),
        count_td,
        td(),  # no way to "total" uptime
        td(status_data['concurrent_requests'])),
      id="children")
    child_div.children.append(children_table)
    
    # children themselves
    odd = True
    for pid in sorted(status_data['children'].keys()):
        child = status_data['children'][pid]
        row = tr(td(pid), cls=['child'])
        if odd:
            row.attrs['cls'].append('odd')
        odd = not odd
        
        # active handling
        row.children.append(td({True:'Y', False:'N'}[child['active']]))
        if not child['active']:
            row.attrs['cls'].append('dying')
            
        # errors
        if child.get('error'):
            row.attrs['cls'].append('error')
            row.children.append(td(child['error'], colspan=2))
        else:
            # no errors
            row.children.append(td(child['uptime']))
            row.children.append(td(child['concurrent_requests']))
            
        children_table.children.append(row)
        
    # config dump
    config_div = div(
        h2("Configuration"),
        table(*[tr(th(key),  td(status_data['config'][key]))
            for key in sorted(status_data['config'].keys())]), 
        id='config')
        
    to_format = {'cont_div': cont_div, 'child_div':child_div,
                 'config_div':config_div}
    to_format.update(status_data)
    return HTML_SHELL % to_format

HTML_SHELL = """
<!DOCTYPE html>
<html><head>
<title>Spawning Status</title>
<style type="text/css">
html, p, div, table, h1, h2, input, form {
	margin: 0;
	padding: 0;
	border: 0;
	outline: 0;
	font-size: 12px;
	font-family: Helvetica, Arial, sans-serif;
	vertical-align: baseline;
}
body {
	line-height: 1.2;
	color: black;
	background: white;
	margin: 3em;
}
table {
	border-collapse: separate;
	border-spacing: 0;
}
th, td {
	text-align: center;
	padding: .1em;
    padding-right: .4em;
}
#controller td, #controller th {
    text-align: left;
}
#config td, #config th {
    text-align: left;
}
#children {
    clear: both;
}
#options {
    float: right;
    border: 1px solid #dfdfdf;
    padding:.5em;
}
h1,h2 {
    margin: .5em;
    margin-left: 0em;
    font-size: 130%%;  
}
h2 {
    font-size: 115%%;  
}
tr.odd {
    background: #dfdfdf;
}
input {
    border: 1px solid grey;
}
#refresh form {
    display: inline;
}
tr.child.dying {
    font-style: italic;
    color: #444444;
}
.error {
    background: #ff4444;
}

/* Cut out the fat for mobile devices */
@media screen and (max-width: 400px) {
    body {
        margin-left: .2em;
        margin-right: .2em;
    }
    #options {
        float: none;
    }
}
</style>
</head><body>
<h1>Spawning Status</h1>
<div id="options">
<p>%(now)s</p>
<div id="refresh">
<a href="">Refresh</a> (<form>
  <input type="checkbox" /> every
  <input type="text" value="5" size=2 />s
</form>)
</div>
<a href="status.json">JSON</a>
</div>
%(cont_div)s
%(child_div)s
%(config_div)s
<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js"></script>
<script type="text/javascript">
$(document).ready(function() {
    var timer;
    var arrangeTimeout = function () {
        clearTimeout(timer);
        if($('#refresh input[type=checkbox]').attr('checked')) {
            timer = setTimeout(
                function() {window.location.reload();},
                $('#refresh input[type=text]').val() * 1000);
        }
        if($(this).is('form')) {
            return false;
        }
    };
    $('#refresh input[type=checkbox]').click(arrangeTimeout);
    $('#refresh form').submit(arrangeTimeout).submit();
});
</script>
</body></html>
"""

########NEW FILE########
__FILENAME__ = system
# Copyright (c) 2010, Steve 'Ashcrow' MIlner
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
Platform related items.
"""

import os
import platform
import sys
import tempfile


class System(dict):
    """
    Class to make finding out system information all in one place.

    **Note**: You can not add attributes to an instance of this class.
    """

    def __init__(self):
        dict.__init__(self, {
            'architecture': platform.architecture(),
            'max_int': sys.maxint,
            'max_size': sys.maxsize,
            'max_unicode': sys.maxunicode,
            'name': platform.node(),
            'path_seperator': os.path.sep,
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'python_branch': platform.python_branch(),
            'python_build': platform.python_build(),
            'python_compiler': platform.python_compiler(),
            'python_implementation': platform.python_implementation(),
            'python_revision': platform.python_revision(),
            'python_version_tuple': platform.python_version_tuple(),
            'python_path': sys.path,
            'login': os.getlogin(),
            'system': platform.system(),
            'temp_directory': tempfile.gettempdir(),
            'uname': platform.uname(),
    })

    def __getattr__(self, name):
        """
        Looks in the dictionary for items **only**.

        :Parameters:
           - 'name': name of the attribute to get.
        """
        data = dict(self).get(name)
        if data == None:
            raise AttributeError("'%s' has no attribute '%s'" % (
                self.__class__.__name__, name))
        return data

    def __setattr__(self, key, value):
        """
        Setting attributes is **not** allowed.

        :Parameters:
           - `key`: attribute name to set.
           - `value`: value to set attribute to.
        """
        raise AttributeError("can't set attribute")

    def __repr__(self):
        """
        Nice object representation.
        """
        return unicode(
            "<Platform: system='%s', name='%s', arch=%s, processor='%s'>" % (
            self.system, self.name, self.architecture, self.processor))

    # Method aliases
    __str__ = __repr__
    __unicode__ = __repr__
    __setitem__ = __setattr__

########NEW FILE########
__FILENAME__ = wsgi_factory
# Copyright (c) 2008, Donovan Preston
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""The config_factory takes a dictionary containing the command line arguments
and should return the same dictionary after modifying any of the settings it wishes.
At the very least the config_factory must set the 'app_factory' key in the returned
argument dictionary, which should be the dotted path to the function which will be
called to actually return the wsgi application which will be served.  Also, the
config_factory can look at the 'args' key for any additional positional command-line
arguments that were passed to spawn, and modify the configuration dictionary
based on it's contents.

Return value of config_factory should be a dict containing:
    app_factory: The dotted path to the wsgi application factory.
        Will be called with the result of factory_qual as the argument.
    host: The local ip to bind to.
    port: The local port to bind to.
    num_processes: The number of processes to spawn.
    num_threads: The number of threads to use in the threadpool in each process.
        If 0, install the eventlet monkeypatching and do not use the threadpool.
        Code which blocks instead of cooperating will block the process, possibly
        causing stalls. (TODO sigalrm?)
    dev: If True, watch all files in sys.modules, easy-install.pth, and any additional
        file paths in the 'watch' list for changes and restart child
        processes on change. If False, only reload if the svn revision of the
        current directory changes.
    watch: List of additional files to watch for changes and reload when changed.
"""
import inspect
import os
import time

import spawning.util

def config_factory(args):
    args['app_factory'] = 'spawning.wsgi_factory.app_factory'
    args['app'] = args['args'][0]
    args['middleware'] = args['args'][1:]

    args['source_directories'] = [os.path.split(
        inspect.getfile(
            inspect.getmodule(
                spawning.util.named(args['app']))))[0]]
    return args


def app_factory(config):
    app = spawning.util.named(config['app'])
    for mid in config['middleware']:
        app = spawning.util.named(mid)(app)
    return app


def hello_world(env, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['Hello, World!\r\n']


def really_long(env, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    time.sleep(180)
    return ['Goodbye, World!\r\n']


########NEW FILE########
